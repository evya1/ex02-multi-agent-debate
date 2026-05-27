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

Skills are grouped by responsibility across three sub-modules:
  - judge_skills      — moderation + verdict (judge only)
  - debater_skills    — pro argument, con argument, rebuttal
  - protocol_skills   — evidence retrieval + JSON protocol (cross-cutting)
"""

from __future__ import annotations

from debate.skills.debater_skills import CON_ARGUMENT_SKILL, PRO_ARGUMENT_SKILL, REBUTTAL_SKILL
from debate.skills.judge_skills import JUDGE_MODERATION_SKILL, VERDICT_SKILL
from debate.skills.protocol_skills import EVIDENCE_RETRIEVAL_SKILL, JSON_PROTOCOL_SKILL
from debate.skills.registry import SkillRegistry

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
