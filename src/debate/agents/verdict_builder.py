"""
Verdict construction from LLM-parsed JSON.

Extracted from JudgeAgent so the data-mapping concern (raw dict → typed
Verdict model) lives in its own module, independently testable.
"""

from __future__ import annotations

from debate.models.message import Role
from debate.models.verdict import RoundScore, Verdict


def build_verdict(data: dict) -> Verdict:
    """
    Convert a parsed JSON verdict dict into a typed Verdict model.

    Args:
        data:  Dict from the judge's LLM response (winner, round_scores,
               total scores, reasoning, key_turning_point).

    Returns:
        A validated Verdict instance.  Defaults are applied for any missing
        fields so a slightly under-specified response still produces a result.
    """
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
