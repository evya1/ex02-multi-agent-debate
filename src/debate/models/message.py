"""
DebateMessage is the universal unit of communication in the debate.
Every exchange — argument, rebuttal, moderation, verdict — travels as a DebateMessage.

Why a shared envelope?  It lets the logger, CLI, and tests handle all message
types uniformly without type-switching on the sender.
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
    round: int
    role: Role
    message_type: MessageType
    content: str
    evidence: list[Evidence] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    in_reply_to: str | None = None

    def to_context_string(self) -> str:
        """Human-readable summary passed to the opposing agent as context."""
        header = f"[Round {self.round} — {self.role.value.upper()}]"
        body = self.content
        if self.evidence:
            citations = "\n".join(
                f"  [{i + 1}] {e.source}: \"{e.quote}\""
                for i, e in enumerate(self.evidence)
            )
            body += f"\n\nEvidence:\n{citations}"
        return f"{header}\n{body}"

    def to_log_entry(self) -> dict:
        return self.model_dump(mode="json")
