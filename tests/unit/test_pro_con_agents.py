"""
Tests for ProAgent and ConAgent.

All Gatekeeper calls are mocked so no real API keys or network access
are required.  Validates argument generation, skill assignment, and
debate_id propagation.
"""

from __future__ import annotations

from debate.agents.con import ConAgent
from debate.agents.pro import ProAgent
from debate.models.message import MessageType, Role


class TestProAgent:
    def test_generates_argument_round_1(self, minimal_config, skill_registry, mock_gatekeeper):
        pro = ProAgent(minimal_config.pro, skill_registry, mock_gatekeeper)
        msg = pro.generate_argument("Judge says: welcome, round 1", round_num=1)
        assert msg.role == Role.PRO
        assert msg.message_type == MessageType.ARGUMENT
        assert msg.content
        assert isinstance(msg.evidence, list)

    def test_generates_rebuttal_round_2(self, minimal_config, skill_registry, mock_gatekeeper):
        pro = ProAgent(minimal_config.pro, skill_registry, mock_gatekeeper)
        msg = pro.generate_argument("Con argued: AI has risks.", round_num=2)
        assert msg.message_type == MessageType.REBUTTAL

    def test_skill_id_used_argument(self, minimal_config, skill_registry, mock_gatekeeper):
        pro = ProAgent(minimal_config.pro, skill_registry, mock_gatekeeper)
        msg = pro.generate_argument("Judge: round 1", round_num=1)
        assert msg.skill_id_used == "pro_argument_skill"

    def test_skill_id_used_rebuttal(self, minimal_config, skill_registry, mock_gatekeeper):
        pro = ProAgent(minimal_config.pro, skill_registry, mock_gatekeeper)
        msg = pro.generate_argument("Con argued something.", round_num=3)
        assert msg.skill_id_used == "rebuttal_skill"

    def test_debate_id_propagated(self, minimal_config, skill_registry, mock_gatekeeper):
        pro = ProAgent(minimal_config.pro, skill_registry, mock_gatekeeper)
        msg = pro.generate_argument("context", round_num=1, debate_id="test-debate-001")
        assert msg.debate_id == "test-debate-001"

    def test_system_prompt_contains_pro_skills(
        self, minimal_config, skill_registry, mock_gatekeeper
    ):
        pro = ProAgent(minimal_config.pro, skill_registry, mock_gatekeeper)
        prompt = pro._system_prompt
        assert "PRO debater" in prompt
        assert "pro_argument_skill" in prompt

    def test_uses_evidence_tool(self, minimal_config, skill_registry):
        pro = ProAgent.__new__(ProAgent)
        pro.role = Role.PRO
        tools = ProAgent._tools_for_role(pro)
        assert tools is not None
        assert any(t["name"] == "retrieve_evidence" for t in tools)


class TestConAgent:
    def test_generates_argument_round_1(self, minimal_config, skill_registry, mock_gatekeeper):
        con = ConAgent(minimal_config.con, skill_registry, mock_gatekeeper)
        msg = con.generate_argument("Pro argued: AI cures diseases.", round_num=1)
        assert msg.role == Role.CON
        assert msg.message_type == MessageType.ARGUMENT

    def test_generates_rebuttal_round_2(self, minimal_config, skill_registry, mock_gatekeeper):
        con = ConAgent(minimal_config.con, skill_registry, mock_gatekeeper)
        msg = con.generate_argument("Pro argued again.", round_num=3)
        assert msg.message_type == MessageType.REBUTTAL

    def test_system_prompt_contains_con_skills(
        self, minimal_config, skill_registry, mock_gatekeeper
    ):
        con = ConAgent(minimal_config.con, skill_registry, mock_gatekeeper)
        assert "CON debater" in con._system_prompt
        assert "con_argument_skill" in con._system_prompt

    def test_skill_id_used_con_argument(self, minimal_config, skill_registry, mock_gatekeeper):
        con = ConAgent(minimal_config.con, skill_registry, mock_gatekeeper)
        msg = con.generate_argument("Pro argued.", round_num=1)
        assert msg.skill_id_used == "con_argument_skill"

    def test_skill_id_used_con_rebuttal(self, minimal_config, skill_registry, mock_gatekeeper):
        con = ConAgent(minimal_config.con, skill_registry, mock_gatekeeper)
        msg = con.generate_argument("Pro argued again.", round_num=2)
        assert msg.skill_id_used == "rebuttal_skill"
