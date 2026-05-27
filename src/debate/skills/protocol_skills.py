"""
Protocol skills: evidence retrieval and JSON output protocol.

These two skills are cross-cutting — evidence retrieval applies to both
Pro and Con, and the JSON protocol applies to every agent in every message.
"""

from __future__ import annotations

from debate.models.skill import SkillDefinition

# ── 1. Evidence retrieval ──────────────────────────────────────────────────────

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

# ── 2. JSON protocol ───────────────────────────────────────────────────────────

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
