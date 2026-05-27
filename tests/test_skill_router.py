"""Tests for SkillRouter — maps agent actions to the correct skill."""
from __future__ import annotations

import pytest

from debate.models.message import MessageType, Role
from debate.skills.definitions import build_registry
from debate.skills.router import SkillRouter


@pytest.fixture()
def router():
    return SkillRouter(build_registry())


class TestSkillRouterRoute:
    def test_judge_moderation_round_1(self, router):
        skill = router.route(Role.JUDGE, round_num=1)
        assert skill.name == "judge_moderation_skill"

    def test_judge_moderation_round_n(self, router):
        skill = router.route(Role.JUDGE, round_num=5)
        assert skill.name == "judge_moderation_skill"

    def test_judge_verdict(self, router):
        skill = router.route(Role.JUDGE, is_verdict=True)
        assert skill.name == "verdict_skill"

    def test_pro_argument_round_1(self, router):
        skill = router.route(Role.PRO, round_num=1)
        assert skill.name == "pro_argument_skill"

    def test_pro_rebuttal_round_2(self, router):
        skill = router.route(Role.PRO, round_num=2)
        assert skill.name == "rebuttal_skill"

    def test_pro_rebuttal_round_5(self, router):
        skill = router.route(Role.PRO, round_num=5)
        assert skill.name == "rebuttal_skill"

    def test_con_argument_round_1(self, router):
        skill = router.route(Role.CON, round_num=1)
        assert skill.name == "con_argument_skill"

    def test_con_rebuttal_round_3(self, router):
        skill = router.route(Role.CON, round_num=3)
        assert skill.name == "rebuttal_skill"

    def test_returns_skill_definition(self, router):
        from debate.models.skill import SkillDefinition
        skill = router.route(Role.PRO, round_num=1)
        assert isinstance(skill, SkillDefinition)

    def test_raises_on_unknown_role(self, router):
        with pytest.raises((ValueError, AttributeError)):
            router.route("unknown_role")  # type: ignore[arg-type]


class TestSkillRouterSkillId:
    def test_judge_moderation_id(self, router):
        sid = router.skill_id_for(Role.JUDGE, MessageType.MODERATION)
        assert sid == "judge_moderation_skill"

    def test_judge_verdict_id(self, router):
        sid = router.skill_id_for(Role.JUDGE, MessageType.VERDICT)
        assert sid == "verdict_skill"

    def test_pro_argument_id(self, router):
        sid = router.skill_id_for(Role.PRO, MessageType.ARGUMENT)
        assert sid == "pro_argument_skill"

    def test_pro_rebuttal_id(self, router):
        sid = router.skill_id_for(Role.PRO, MessageType.REBUTTAL)
        assert sid == "rebuttal_skill"

    def test_con_argument_id(self, router):
        sid = router.skill_id_for(Role.CON, MessageType.ARGUMENT)
        assert sid == "con_argument_skill"

    def test_con_rebuttal_id(self, router):
        sid = router.skill_id_for(Role.CON, MessageType.REBUTTAL)
        assert sid == "rebuttal_skill"
