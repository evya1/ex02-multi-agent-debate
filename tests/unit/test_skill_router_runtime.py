"""
Prove that SkillRouter's routing contract is honoured in runtime output.

A full debate is run with mock providers (1 round, offline).  Every
DebateMessage in the transcript is then cross-checked: the skill_id_used
field must equal what SkillRouter.skill_id_for(role, message_type) returns.

This guards against the two codes drifting apart — if an agent hard-codes
a wrong skill name, or if SkillRouter changes its mapping, this test fails.
"""

from __future__ import annotations

import pytest

from debate.agents.judge import JudgeAgent
from debate.models.message import MessageType, Role
from debate.skills.definitions import build_registry
from debate.skills.router import SkillRouter


@pytest.fixture()
def two_round_config(minimal_config):
    """Config overridden to run 2 rounds so rebuttal skill is exercised."""
    minimal_config.debate.rounds = 2
    return minimal_config


class TestSkillRouterRuntimeOrchestration:
    """Verify that every message in a live debate maps to SkillRouter's contract."""

    def test_skill_ids_match_router_contract(
        self, two_round_config, mock_gatekeeper
    ):
        registry = build_registry()
        router = SkillRouter(registry)
        judge = JudgeAgent(two_round_config, registry, mock_gatekeeper)
        transcript, _ = judge.run_debate()

        skill_bearing = [
            m for m in transcript if m.skill_id_used
        ]
        assert skill_bearing, "Expected at least some messages to carry skill_id_used"

        for msg in skill_bearing:
            if msg.role == Role.JUDGE and msg.message_type == MessageType.MODERATION:
                continue  # opening/closing moderation — no skill_id required
            expected = router.skill_id_for(msg.role, msg.message_type)
            if expected:  # skip empty (e.g. unknown combos)
                assert msg.skill_id_used == expected, (
                    f"Round {msg.round} {msg.role.value} {msg.message_type.value}: "
                    f"skill_id_used={msg.skill_id_used!r}, expected={expected!r}"
                )

    def test_round_1_pro_uses_argument_skill(
        self, minimal_config, skill_registry, mock_gatekeeper
    ):
        judge = JudgeAgent(minimal_config, skill_registry, mock_gatekeeper)
        transcript, _ = judge.run_debate()
        pro_round1 = next(
            (m for m in transcript if m.role == Role.PRO and m.round == 1), None
        )
        assert pro_round1 is not None
        assert pro_round1.skill_id_used == "pro_argument_skill"

    def test_round_2_pro_uses_rebuttal_skill(
        self, two_round_config, mock_gatekeeper
    ):
        registry = build_registry()
        judge = JudgeAgent(two_round_config, registry, mock_gatekeeper)
        transcript, _ = judge.run_debate()
        pro_round2 = next(
            (m for m in transcript if m.role == Role.PRO and m.round == 2), None
        )
        assert pro_round2 is not None
        assert pro_round2.skill_id_used == "rebuttal_skill"

    def test_round_1_con_uses_argument_skill(
        self, minimal_config, skill_registry, mock_gatekeeper
    ):
        judge = JudgeAgent(minimal_config, skill_registry, mock_gatekeeper)
        transcript, _ = judge.run_debate()
        con_round1 = next(
            (m for m in transcript if m.role == Role.CON and m.round == 1), None
        )
        assert con_round1 is not None
        assert con_round1.skill_id_used == "con_argument_skill"

    def test_verdict_uses_verdict_skill(
        self, minimal_config, skill_registry, mock_gatekeeper
    ):
        judge = JudgeAgent(minimal_config, skill_registry, mock_gatekeeper)
        transcript, _ = judge.run_debate()
        verdict_msg = next(
            (m for m in transcript if m.message_type == MessageType.VERDICT), None
        )
        assert verdict_msg is not None
        assert verdict_msg.skill_id_used == "verdict_skill"
