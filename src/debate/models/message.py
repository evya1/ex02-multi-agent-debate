"""
DebateMessage is the universal unit of communication in the debate.
Every exchange — argument, rebuttal, moderation, verdict — travels as a DebateMessage.

Why a shared envelope?  It lets the logger, CLI, and tests handle all message
types uniformly without type-switching on the sender.

Phase 08 additions:
  - skill_id_used: every message records which skill produced it (auditability).
  - debate_id: ties all messages in one session together (multi-session logging).
  - ping_index: for mock/ping mode — which ping produced this message.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class Role(StrEnum):
    JUDGE = "judge"
    PRO = "pro"
    CON = "con"


class MessageType(StrEnum):
    ARGUMENT = "argument"
    REBUTTAL = "rebuttal"
    MODERATION = "moderation"
    VERDICT = "verdict"


class Evidence(BaseModel):
    """One piece of supporting evidence with mandatory source attribution."""

    source: str
    quote: str
    url: str | None = None


class DebateMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    debate_id: str = ""  # set by JudgeAgent for the whole session
    round: int
    role: Role
    message_type: MessageType
    content: str
    evidence: list[Evidence] = Field(default_factory=list)
    skill_id_used: str = ""  # which skill produced this message
    ping_index: int | None = None  # only set in ping/mock mode
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    in_reply_to: str | None = None

    def to_context_string(self) -> str:
        """Human-readable summary passed to the opposing agent as context."""
        header = f"[Round {self.round} — {self.role.value.upper()}]"
        body = self.content
        if self.evidence:
            citations = "\n".join(
                f'  [{i + 1}] {e.source}: "{e.quote}"' for i, e in enumerate(self.evidence)
            )
            body += f"\n\nEvidence:\n{citations}"
        return f"{header}\n{body}"

    def to_log_entry(self) -> dict:
        return self.model_dump(mode="json")
