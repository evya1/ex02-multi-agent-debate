"""
SkillDefinition — a first-class object that packages all metadata for one agent skill.

Why a Pydantic model instead of a plain dict?
  - Schema validation on load catches malformed skill definitions early.
  - `as_system_prompt_block()` lets every skill inject itself consistently.
  - Documentation fields (description, trigger, schemas) are machine-readable,
    making it straightforward to auto-generate docs/PROMPTS.md content.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SkillDefinition(BaseModel):
    name: str
    description: str
    intended_agents: list[str]  # "judge" | "pro" | "con"
    trigger: str                # when/why this skill activates
    instructions: str           # the actual prompt text injected into the agent
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]

    def as_system_prompt_block(self) -> str:
        """Format for injection into an agent's system prompt."""
        return (
            f"### Skill: {self.name}\n"
            f"**Activate when**: {self.trigger}\n\n"
            f"{self.instructions}"
        )
