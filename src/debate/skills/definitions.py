"""
The seven mandatory skills that govern agent behaviour.

Each SkillDefinition bundles:
  - Machine-readable metadata (name, intended_agents, schemas)
  - Human-readable documentation (description, trigger)
  - The actual prompt text injected into the agent's system prompt (instructions)

Why hard-code skills here rather than load from YAML?
  - Skills contain multi-line prompt text that is awkward to manage in YAML.
  - Python gives us string formatting, constants, and IDE support.
  - config/skills.yaml still documents the assignment for ops/docs purposes.
"""
from __future__ import annotations

from debate.models.skill import SkillDefinition
from debate.skills.registry import SkillRegistry

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

# ── 2. Pro argument ────────────────────────────────────────────────────────────

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

# ── 3. Con argument ────────────────────────────────────────────────────────────

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

# ── 4. Evidence retrieval ──────────────────────────────────────────────────────

EVIDENCE_RETRIEVAL_SKILL = SkillDefinition(
    name="evidence_retrieval_skill",
    description="Search the web for real, citable evidence to support an argument.",
    intended_agents=["pro", "con"],
    trigger=(
        "Whenever an argument or rebuttal needs factual backing. "
        "Always retrieve at least one piece of evidence per message."
    ),
    instructions="""
To back every claim with real evidence:
  1. Identify the specific claim that needs a source.
  2. Formulate a precise search query (include year or domain if relevant).
  3. Call the `retrieve_evidence` tool with that query.
  4. From the results, select the most credible and relevant snippet.
  5. Quote the snippet exactly — never paraphrase a quote as if it were verbatim.
  6. Include the source name and URL in your evidence list.

Prefer: peer-reviewed research, government data, reputable news organisations.
Avoid: anonymous sources, opinion pieces presented as fact.
""",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
        },
        "required": ["query"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "quote": {"type": "string"},
            "url": {"type": "string"},
        },
        "required": ["source", "quote"],
    },
)

# ── 5. Rebuttal ────────────────────────────────────────────────────────────────

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

# ── 6. Verdict ─────────────────────────────────────────────────────────────────

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
            "message_type", "winner", "total_pro_score",
            "total_con_score", "reasoning", "key_turning_point",
        ],
    },
)

# ── 7. JSON protocol ───────────────────────────────────────────────────────────

JSON_PROTOCOL_SKILL = SkillDefinition(
    name="json_protocol_skill",
    description="Enforce structured JSON as the only output format for all agents.",
    intended_agents=["judge", "pro", "con"],
    trigger="For every single message produced by any agent.",
    instructions="""
CRITICAL: Every response you produce must be a raw JSON object.
Never include plain text, markdown, or code fences outside the JSON.

Required envelope:
{
  "message_type": "<argument|rebuttal|moderation|verdict>",
  "role": "<pro|con|judge>",
  "round": <integer>,
  "content": "<your main argument or message text>",
  "evidence": [
    {
      "source": "<publication name or domain>",
      "quote": "<exact verbatim quote>",
      "url": "<URL or null>"
    }
  ]
}

Rules:
  - `content` must never be empty or null.
  - `evidence` must be present (use [] if no evidence applies).
  - Return the JSON object only — no leading or trailing text.
""",
    input_schema={
        "type": "object",
        "properties": {
            "role": {"type": "string"},
            "round": {"type": "integer"},
            "message_type": {"type": "string"},
        },
        "required": ["role", "round", "message_type"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "message_type": {"type": "string"},
            "role": {"type": "string"},
            "round": {"type": "integer"},
            "content": {"type": "string"},
            "evidence": {"type": "array"},
        },
        "required": ["message_type", "role", "round", "content", "evidence"],
    },
)

# ── Registry builder ───────────────────────────────────────────────────────────

ALL_SKILLS = [
    JUDGE_MODERATION_SKILL,
    PRO_ARGUMENT_SKILL,
    CON_ARGUMENT_SKILL,
    EVIDENCE_RETRIEVAL_SKILL,
    REBUTTAL_SKILL,
    VERDICT_SKILL,
    JSON_PROTOCOL_SKILL,
]


def build_registry() -> SkillRegistry:
    """Construct and return a registry pre-loaded with all seven skills."""
    registry = SkillRegistry()
    for skill in ALL_SKILLS:
        registry.register(skill)
    return registry
