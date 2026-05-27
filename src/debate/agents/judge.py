"""
JudgeAgent — the parent agent that owns and orchestrates the entire debate.

Responsibilities:
  1. Spawns ProAgent and ConAgent on initialisation (they are its children).
  2. Routes every message: Pro sees only what Judge passes; same for Con.
     Pro and Con never hold references to each other.
  3. Delegates round moderation to JudgeModerationMixin (_open_debate,
     _introduce_round, _summarise_round, context builders).
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
from debate.agents.judge_moderation import JudgeModerationMixin
from debate.agents.pro import ProAgent
from debate.agents.verdict_builder import build_verdict
from debate.gatekeeper import Gatekeeper
from debate.models.config import AppConfig
from debate.models.message import DebateMessage, MessageType, Role
from debate.models.verdict import Verdict
from debate.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class JudgeAgent(JudgeModerationMixin, BaseAgent):
    """
    Parent entity.  Creates and supervises the two child agents.
    All debate communication is mediated by this class.
    Inherits moderation actions from JudgeModerationMixin.
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
          → Judge summarises.
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

            moderation = self._introduce_round(round_num)
            transcript.append(moderation)

            pro_context = self._build_pro_context(moderation, last_con_message)
            pro_msg = self._pro.generate_argument(
                pro_context, round_num, debate_id=self._debate_id
            )
            transcript.append(pro_msg)
            logger.info("Pro argued (round %d, %d chars)", round_num, len(pro_msg.content))

            con_context = self._build_con_context(moderation, pro_msg)
            con_msg = self._con.generate_argument(
                con_context, round_num, debate_id=self._debate_id
            )
            transcript.append(con_msg)
            logger.info("Con argued (round %d, %d chars)", round_num, len(con_msg.content))

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

    # ── verdict rendering ──────────────────────────────────────────────────────

    def _render_verdict(self, transcript: list[DebateMessage]) -> Verdict:
        """Ask the LLM (as judge) to score and declare a winner."""
        transcript_text = "\n\n".join(m.to_context_string() for m in transcript)
        raw = self._call_llm(
            f"The debate has concluded ({self._total_rounds} rounds).\n\n"
            f"Full transcript:\n{transcript_text}\n\n"
            "Score each round (0–10 per side), declare a winner (PRO or CON — no ties), "
            "and identify the single key turning point."
        )
        return build_verdict(self._parse_json(raw))
