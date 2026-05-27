"""
JudgeAgent — the parent agent that owns and orchestrates the entire debate.

Responsibilities:
  1. Spawns ProAgent and ConAgent on initialisation (they are its children).
  2. Routes every message: Pro sees only what Judge passes; same for Con.
     Pro and Con never hold references to each other.
  3. Moderates each round (intro, summary) via its own LLM calls.
  4. After all rounds, renders a scored Verdict.  Ties are structurally
     forbidden: the verdict_skill instructs Claude to always pick a winner.

Owned skills (injected into system prompt):
  - judge_moderation_skill   neutral moderation, round intros and summaries
  - verdict_skill            final scored judgment with no ties allowed
  - json_protocol_skill      enforces JSON-only output
"""

from __future__ import annotations

import logging
from uuid import uuid4

from debate.agents.base import BaseAgent
from debate.agents.con import ConAgent
from debate.agents.pro import ProAgent
from debate.gatekeeper import Gatekeeper
from debate.models.config import AppConfig
from debate.models.message import DebateMessage, MessageType, Role
from debate.models.verdict import RoundScore, Verdict
from debate.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class JudgeAgent(BaseAgent):
    """
    Parent entity.  Creates and supervises the two child agents.
    All debate communication is mediated by this class.
    """

    role = Role.JUDGE

    def __init__(
        self,
        config: AppConfig,
        skill_registry: SkillRegistry,
        gatekeeper: Gatekeeper,
    ) -> None:
        # Set topic and rounds BEFORE super().__init__(), because BaseAgent.__init__
        # immediately calls self._build_system_prompt(), which references these attrs.
        self._topic = config.debate.topic
        self._total_rounds = config.debate.rounds

        super().__init__(config.judge, skill_registry, gatekeeper)

        # Judge spawns the child agents — they are owned here.
        self._pro = ProAgent(config.pro, skill_registry, gatekeeper)
        self._con = ConAgent(config.con, skill_registry, gatekeeper)

    def _build_system_prompt(self) -> str:
        return (
            "You are the JUDGE and moderator of a structured AI debate.\n"
            "You are completely neutral — your role is to facilitate fair discourse\n"
            "and ultimately declare a winner based on argument quality alone.\n\n"
            f"Debate topic: {self._topic}\n\n" + self._skill_prompt_blocks()
        )

    # ── public debate interface ────────────────────────────────────────────────

    def run_debate(self) -> tuple[list[DebateMessage], Verdict]:
        """
        Execute the full debate and return (transcript, verdict).

        Communication flow each round:
          Judge intro → Pro generates → Judge routes to Con → Con generates
          → Judge summarises
        Pro and Con never interact directly.
        """
        self._debate_id = str(uuid4())[:12]  # shared across all messages this session
        transcript: list[DebateMessage] = []

        opening = self._open_debate()
        transcript.append(opening)
        logger.info("Debate opened: %s", self._topic)

        last_con_message: DebateMessage | None = None

        for round_num in range(1, self._total_rounds + 1):
            logger.info("=== Round %d / %d ===", round_num, self._total_rounds)

            # Judge introduces the round and invites Pro to speak.
            moderation = self._introduce_round(round_num)
            transcript.append(moderation)

            # Pro receives the judge's intro (+ Con's last argument from round 2 on).
            pro_context = self._build_pro_context(moderation, last_con_message)
            pro_msg = self._pro.generate_argument(pro_context, round_num, debate_id=self._debate_id)
            transcript.append(pro_msg)
            logger.info("Pro argued (round %d, %d chars)", round_num, len(pro_msg.content))

            # Judge routes Pro's argument to Con.
            con_context = self._build_con_context(moderation, pro_msg)
            con_msg = self._con.generate_argument(con_context, round_num, debate_id=self._debate_id)
            transcript.append(con_msg)
            logger.info("Con argued (round %d, %d chars)", round_num, len(con_msg.content))

            # Judge summarises the clash.
            summary = self._summarise_round(round_num, pro_msg, con_msg)
            transcript.append(summary)

            last_con_message = con_msg

        verdict = self._render_verdict(transcript)
        transcript.append(
            DebateMessage(
                round=self._total_rounds + 1,
                role=Role.JUDGE,
                message_type=MessageType.VERDICT,
                content=verdict.reasoning,
                debate_id=self._debate_id,
                skill_id_used="verdict_skill",
            )
        )

        logger.info(
            "Verdict: %s wins (PRO %.1f — CON %.1f)",
            verdict.winner.value,
            verdict.total_pro_score,
            verdict.total_con_score,
        )
        return transcript, verdict

    # ── private judge actions ──────────────────────────────────────────────────

    def _open_debate(self) -> DebateMessage:
        raw = self._call_llm(
            f'Open the debate on the topic: "{self._topic}".\n'
            f"Introduce the format: {self._total_rounds} rounds, one side speaks at a time.\n"
            "Remind both sides to be respectful and to cite evidence."
        )
        data = self._parse_json(raw)
        return DebateMessage(
            round=0,
            role=Role.JUDGE,
            message_type=MessageType.MODERATION,
            content=data.get("content", raw),
            debate_id=self._debate_id,
            skill_id_used="judge_moderation_skill",
        )

    def _introduce_round(self, round_num: int) -> DebateMessage:
        raw = self._call_llm(
            f"Introduce round {round_num} of {self._total_rounds}. "
            "State the rules briefly and invite the PRO side to speak."
        )
        data = self._parse_json(raw)
        return DebateMessage(
            round=round_num,
            role=Role.JUDGE,
            message_type=MessageType.MODERATION,
            content=data.get("content", raw),
            debate_id=self._debate_id,
            skill_id_used="judge_moderation_skill",
        )

    def _summarise_round(
        self, round_num: int, pro: DebateMessage, con: DebateMessage
    ) -> DebateMessage:
        raw = self._call_llm(
            f"Summarise round {round_num}.\n\n"
            f"PRO argued:\n{pro.content[:600]}\n\n"
            f"CON argued:\n{con.content[:600]}\n\n"
            "Identify the key clash and what each side must address next round."
        )
        data = self._parse_json(raw)
        return DebateMessage(
            round=round_num,
            role=Role.JUDGE,
            message_type=MessageType.MODERATION,
            content=data.get("content", raw),
            debate_id=self._debate_id,
            skill_id_used="judge_moderation_skill",
        )

    def _render_verdict(self, transcript: list[DebateMessage]) -> Verdict:
        """
        Ask Claude (as judge) to score each round and declare a winner.
        Parses the structured JSON verdict and validates it into a Verdict model.
        """
        transcript_text = "\n\n".join(m.to_context_string() for m in transcript)

        raw = self._call_llm(
            f"The debate has concluded ({self._total_rounds} rounds).\n\n"
            f"Full transcript:\n{transcript_text}\n\n"
            "Score each round (0–10 per side), declare a winner (PRO or CON — no ties), "
            "and identify the single key turning point."
        )
        data = self._parse_json(raw)
        return self._build_verdict(data)

    # ── context builders (routing logic) ──────────────────────────────────────

    @staticmethod
    def _build_pro_context(moderation: DebateMessage, last_con: DebateMessage | None) -> str:
        if last_con is None:
            return moderation.content
        return f"{moderation.content}\n\n{last_con.to_context_string()}"

    @staticmethod
    def _build_con_context(moderation: DebateMessage, pro: DebateMessage) -> str:
        return f"{moderation.content}\n\n{pro.to_context_string()}"

    # ── verdict parsing ────────────────────────────────────────────────────────

    @staticmethod
    def _build_verdict(data: dict) -> Verdict:
        raw_winner = data.get("winner", "pro").lower().strip()
        winner = Role.PRO if raw_winner != "con" else Role.CON

        round_scores = [
            RoundScore(
                round=rs.get("round", i + 1),
                pro_score=float(rs.get("pro_score", 5.0)),
                con_score=float(rs.get("con_score", 5.0)),
                reasoning=rs.get("reasoning", ""),
            )
            for i, rs in enumerate(data.get("round_scores", []))
        ]

        total_pro = float(data.get("total_pro_score", sum(r.pro_score for r in round_scores)))
        total_con = float(data.get("total_con_score", sum(r.con_score for r in round_scores)))

        # If totals are equal, grant the win to the declared winner anyway
        # (the verdict_skill instructs Claude to handle this via momentum).
        return Verdict(
            winner=winner,
            total_pro_score=total_pro,
            total_con_score=total_con,
            round_scores=round_scores,
            reasoning=data.get("reasoning", "No reasoning provided."),
            key_turning_point=data.get("key_turning_point", "Not specified."),
        )
