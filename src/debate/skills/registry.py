"""
SkillRegistry — the single source of truth for all loaded skills.

Why a registry instead of importing definitions directly?
  - Agents receive the registry as a dependency, making them unit-testable
    by injecting a registry populated with stub skills.
  - New skills can be added without changing any agent code.
"""
from __future__ import annotations

from debate.models.skill import SkillDefinition


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillDefinition:
        if name not in self._skills:
            raise KeyError(f"Skill '{name}' not found in registry")
        return self._skills[name]

    def get_for_agent(self, agent_role: str) -> list[SkillDefinition]:
        """Return all skills whose `intended_agents` list includes the given role."""
        return [s for s in self._skills.values() if agent_role in s.intended_agents]

    def all(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def __len__(self) -> int:
        return len(self._skills)
