"""
Judge skills: moderation and verdict.

These two skills govern the judge agent's behaviour for all round-level
moderation (intros, summaries) and the final scored verdict.
"""

from __future__ import annotations

from debate.models.skill import SkillDefinition

# ── 1. Judge moderation ────────────────────────────────────────────────────────

JUDGE_MODERATION_SKILL = SkillDefinition(
    name="judge_moderation_skill",
    description="Neutral moderation of debate flow, rule enforcement, and round summaries.",
    intended_agents=["judge"],
    trigger="Before each round begins and when summarising after a round ends.",
    instructions="""
You are a neutral debate moderator. Your responsibilities:
- Introduce each round with its number and a reminder of the topic.
- Enforce the rules: one side speaks at a time; arguments must be respectful and evidence-backed.
- At the end of each round, summarise what each side argued and identify the key clash.
- Never express a personal opinion on the topic during moderation.
- Keep moderation messages concise (under 150 words).
""",
    input_schema={
        "type": "object",
        "properties": {
            "round": {"type": "integer"},
            "topic": {"type": "string"},
            "previous_summary": {"type": "string"},
        },
        "required": ["round", "topic"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "message_type": {"const": "moderation"},
            "content": {"type": "string"},
            "addressed_to": {"type": "string", "enum": ["pro", "con", "both"]},
        },
        "required": ["message_type", "content"],
    },
)

# ── 2. Verdict ─────────────────────────────────────────────────────────────────

VERDICT_SKILL = SkillDefinition(
    name="verdict_skill",
    description="Render a definitive, scored verdict after the full debate. Ties are forbidden.",
    intended_agents=["judge"],
    trigger="After all debate rounds are complete.",
    instructions="""
Score each round 0–10 per side on these four criteria:
  1. Argument quality  (logic and structure)
  2. Persuasiveness    (did they move the debate, not just state facts?)
  3. Evidence use      (credibility and relevance of sources)
  4. Responsiveness    (did they genuinely engage with the opponent?)

Rules:
  - You MUST declare a winner: PRO or CON. Ties are forbidden.
  - If total scores are equal, award victory to the side with better momentum
    (whose arguments improved most across rounds).
  - Identify the single key turning point — the argument that shifted the debate.
  - Keep your reasoning under 300 words, but make it specific and substantive.
""",
    input_schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "full_transcript": {"type": "array"},
            "total_rounds": {"type": "integer"},
        },
        "required": ["topic", "full_transcript", "total_rounds"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "message_type": {"const": "verdict"},
            "winner": {"type": "string", "enum": ["pro", "con"]},
            "total_pro_score": {"type": "number"},
            "total_con_score": {"type": "number"},
            "round_scores": {"type": "array"},
            "reasoning": {"type": "string"},
            "key_turning_point": {"type": "string"},
        },
        "required": [
            "message_type",
            "winner",
            "total_pro_score",
            "total_con_score",
            "reasoning",
            "key_turning_point",
        ],
    },
)
