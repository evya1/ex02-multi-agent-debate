"""
Verdict is the judge's final ruling after all rounds complete.

Design choice: a tie is structurally impossible — `winner` can only be
Role.PRO or Role.CON.  If Claude returns equal total scores, the verdict
skill instructs it to award momentum-based victory instead.
"""
from __future__ import annotations

from pydantic import BaseModel, field_validator

from .message import Role


class RoundScore(BaseModel):
    round: int
    pro_score: float  # 0 – 10
    con_score: float  # 0 – 10
    reasoning: str


class Verdict(BaseModel):
    winner: Role
    total_pro_score: float
    total_con_score: float
    round_scores: list[RoundScore]
    reasoning: str
    key_turning_point: str

    @field_validator("winner")
    @classmethod
    def winner_must_be_debater(cls, v: Role) -> Role:
        if v == Role.JUDGE:
            raise ValueError("The judge cannot win the debate.")
        return v

    def summary(self) -> str:
        badge = "🏆 PRO wins" if self.winner == Role.PRO else "🏆 CON wins"
        return (
            f"{badge}  (PRO {self.total_pro_score:.1f} — CON {self.total_con_score:.1f})\n"
            f"Key turning point: {self.key_turning_point}\n\n"
            f"{self.reasoning}"
        )
