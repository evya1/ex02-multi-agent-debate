"""
Debater skills: pro argument, con argument, and rebuttal.

These three skills govern how Pro and Con agents construct their opening
arguments and responses across debate rounds.
"""

from __future__ import annotations

from debate.models.skill import SkillDefinition

# ── 1. Pro argument ────────────────────────────────────────────────────────────

PRO_ARGUMENT_SKILL = SkillDefinition(
    name="pro_argument_skill",
    description="Construct well-structured, persuasive arguments in favour of the debate topic.",
    intended_agents=["pro"],
    trigger="When presenting an opening argument or advancing a new claim (round 1, or after a rebuttal).",  # noqa: E501
    instructions="""
Your arguments must follow this structure:
  1. Claim   — state your position clearly.
  2. Reason  — explain the logic behind the claim.
  3. Evidence — cite a real source (use the retrieve_evidence tool).
  4. Impact  — explain why this matters for the debate.

Rules:
- Be persuasive, not just factual; aim to shift the judge's perspective.
- 200–350 words per argument.
- Never repeat an argument you have already made.
""",
    input_schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "round": {"type": "integer"},
        },
        "required": ["topic", "round"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "message_type": {"const": "argument"},
            "content": {"type": "string"},
            "evidence": {"type": "array"},
        },
        "required": ["message_type", "content", "evidence"],
    },
)

# ── 2. Con argument ────────────────────────────────────────────────────────────

CON_ARGUMENT_SKILL = SkillDefinition(
    name="con_argument_skill",
    description="Construct well-structured, persuasive arguments against the debate topic.",
    intended_agents=["con"],
    trigger="When presenting an opening argument or advancing a new claim (round 1, or after a rebuttal).",  # noqa: E501
    instructions="""
Your arguments must follow this structure:
  1. Claim   — state your counter-position clearly.
  2. Reason  — expose the flaw in the PRO's logic or provide a superior alternative.
  3. Evidence — cite a real source (use the retrieve_evidence tool).
  4. Impact  — explain why this undermines the PRO case.

Rules:
- Challenge the PRO's strongest point, not a strawman.
- Be persuasive, not just factual.
- 200–350 words per argument.
- Never repeat an argument you have already made.
""",
    input_schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "round": {"type": "integer"},
        },
        "required": ["topic", "round"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "message_type": {"const": "argument"},
            "content": {"type": "string"},
            "evidence": {"type": "array"},
        },
        "required": ["message_type", "content", "evidence"],
    },
)

# ── 3. Rebuttal ────────────────────────────────────────────────────────────────

REBUTTAL_SKILL = SkillDefinition(
    name="rebuttal_skill",
    description="Directly address and counter the opponent's most recent argument.",
    intended_agents=["pro", "con"],
    trigger="In rounds 2+, when the agent must respond to the opponent's previous message.",
    instructions="""
A strong rebuttal has four parts:
  1. Steelman — briefly acknowledge the strongest point your opponent made.
  2. Counter  — identify and attack the weakest link in their reasoning.
  3. Evidence — support your counter with a retrieved source.
  4. Pivot    — redirect to reinforce your own position.

A rebuttal that ignores what the opponent said will score poorly.
Never simply repeat your previous argument.
""",
    input_schema={
        "type": "object",
        "properties": {
            "opponent_argument": {"type": "string"},
            "round": {"type": "integer"},
        },
        "required": ["opponent_argument", "round"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "message_type": {"const": "rebuttal"},
            "content": {"type": "string"},
            "evidence": {"type": "array"},
        },
        "required": ["message_type", "content"],
    },
)
