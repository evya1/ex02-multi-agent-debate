"""
SkillRouter — maps an agent action to the correct SkillDefinition at runtime.

Why a router?
  Agents select skills based on context (role, round number, whether opponent
  has spoken).  Centralising this logic makes it testable and easy to extend
  (e.g. adding a new role or a new round-specific skill).

Routing rules:
  - Judge always uses judge_moderation_skill for intros/summaries.
  - Judge uses verdict_skill for the final verdict.
  - Pro/Con round 1 → argument skill (pro_argument_skill / con_argument_skill).
  - Pro/Con round 2+ → rebuttal_skill.
  - Evidence retrieval is not routed here — it is always available to Pro/Con
    as a tool-use capability, not a turn-level skill.
"""

from __future__ import annotations

from debate.models.message import MessageType, Role
from debate.models.skill import SkillDefinition
from debate.skills.registry import SkillRegistry


class SkillRouter:
    """
    Routes an (agent_role, round_num, context) tuple to a SkillDefinition.

    Usage:
        router = SkillRouter(skill_registry)
        skill = router.route(Role.PRO, round_num=1)
        # → pro_argument_skill

        skill = router.route(Role.PRO, round_num=2)
        # → rebuttal_skill

        skill = router.route(Role.JUDGE, round_num=1, is_verdict=False)
        # → judge_moderation_skill

        skill = router.route(Role.JUDGE, is_verdict=True)
        # → verdict_skill
    """

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def route(
        self,
        role: Role,
        *,
        round_num: int = 1,
        is_verdict: bool = False,
    ) -> SkillDefinition:
        """
        Return the appropriate skill for the given agent action.

        Args:
            role:       The agent's role (JUDGE, PRO, or CON).
            round_num:  Current debate round (1 = opening, 2+ = rebuttal).
            is_verdict: True when the judge is rendering the final verdict.
        """
        if role == Role.JUDGE:
            skill_name = "verdict_skill" if is_verdict else "judge_moderation_skill"
        elif role == Role.PRO:
            skill_name = "pro_argument_skill" if round_num == 1 else "rebuttal_skill"
        elif role == Role.CON:
            skill_name = "con_argument_skill" if round_num == 1 else "rebuttal_skill"
        else:
            raise ValueError(f"Unknown role: {role!r}")

        skill = self._registry.get(skill_name)
        if skill is None:
            raise KeyError(
                f"SkillRouter: skill '{skill_name}' not found in registry. "
                "Ensure build_registry() has been called."
            )
        return skill

    def skill_id_for(
        self,
        role: Role,
        message_type: MessageType,
    ) -> str:
        """
        Convenience method: return the skill_id string (not the SkillDefinition)
        for a given (role, message_type) pair.  Used to stamp skill_id_used on
        DebateMessage without needing the full registry lookup.
        """
        if role == Role.JUDGE:
            return (
                "verdict_skill" if message_type == MessageType.VERDICT else "judge_moderation_skill"
            )
        if role == Role.PRO:
            return (
                "pro_argument_skill" if message_type == MessageType.ARGUMENT else "rebuttal_skill"
            )
        if role == Role.CON:
            return (
                "con_argument_skill" if message_type == MessageType.ARGUMENT else "rebuttal_skill"
            )
        return ""
