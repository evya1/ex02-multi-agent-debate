"""
JudgeModerationMixin — the three round-level LLM calls the judge makes,
plus the context-routing helpers that control what each agent sees.

Extracted from JudgeAgent so the round mechanics (open, introduce, summarise)
and routing (what to pass to Pro, what to pass to Con) are isolated from
the top-level debate orchestration in judge.py.

The mixin assumes it is mixed into a BaseAgent subclass that provides
_call_llm(), _parse_json(), and the instance attributes _debate_id and
_total_rounds.
"""

from __future__ import annotations

from debate.models.message import DebateMessage, MessageType, Role


class JudgeModerationMixin:
    """Mixin providing round moderation actions and context routing for JudgeAgent."""

    # ── round-level LLM calls ──────────────────────────────────────────────────

    def _open_debate(self) -> DebateMessage:
        raw = self._call_llm(  # type: ignore[attr-defined]
            f'Open the debate on the topic: "{self._topic}".\n'  # type: ignore[attr-defined]
            f"Introduce the format: {self._total_rounds} rounds, "  # type: ignore[attr-defined]
            "one side speaks at a time.\n"
            "Remind both sides to be respectful and to cite evidence."
        )
        data = self._parse_json(raw)  # type: ignore[attr-defined]
        return DebateMessage(
            round=0,
            role=Role.JUDGE,
            message_type=MessageType.MODERATION,
            content=data.get("content", raw),
            debate_id=self._debate_id,  # type: ignore[attr-defined]
            skill_id_used="judge_moderation_skill",
        )

    def _introduce_round(self, round_num: int) -> DebateMessage:
        raw = self._call_llm(  # type: ignore[attr-defined]
            f"Introduce round {round_num} of {self._total_rounds}. "  # type: ignore[attr-defined]
            "State the rules briefly and invite the PRO side to speak."
        )
        data = self._parse_json(raw)  # type: ignore[attr-defined]
        return DebateMessage(
            round=round_num,
            role=Role.JUDGE,
            message_type=MessageType.MODERATION,
            content=data.get("content", raw),
            debate_id=self._debate_id,  # type: ignore[attr-defined]
            skill_id_used="judge_moderation_skill",
        )

    def _summarise_round(
        self, round_num: int, pro: DebateMessage, con: DebateMessage
    ) -> DebateMessage:
        raw = self._call_llm(  # type: ignore[attr-defined]
            f"Summarise round {round_num}.\n\n"
            f"PRO argued:\n{pro.content[:600]}\n\n"
            f"CON argued:\n{con.content[:600]}\n\n"
            "Identify the key clash and what each side must address next round."
        )
        data = self._parse_json(raw)  # type: ignore[attr-defined]
        return DebateMessage(
            round=round_num,
            role=Role.JUDGE,
            message_type=MessageType.MODERATION,
            content=data.get("content", raw),
            debate_id=self._debate_id,  # type: ignore[attr-defined]
            skill_id_used="judge_moderation_skill",
        )

    # ── context routing ────────────────────────────────────────────────────────

    @staticmethod
    def _build_pro_context(moderation: DebateMessage, last_con: DebateMessage | None) -> str:
        """Build the context string passed to Pro each round."""
        if last_con is None:
            return moderation.content
        return f"{moderation.content}\n\n{last_con.to_context_string()}"

    @staticmethod
    def _build_con_context(moderation: DebateMessage, pro: DebateMessage) -> str:
        """Build the context string passed to Con each round."""
        return f"{moderation.content}\n\n{pro.to_context_string()}"
