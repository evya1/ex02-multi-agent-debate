"""
Tests for Pro, Con, and Judge agents.

All Gatekeeper calls are mocked so no real API keys or network access
are required.  Tests validate JSON parsing, message structure, routing
logic, and verdict building.
"""
from __future__ import annotations

from debate.agents.base import BaseAgent
from debate.agents.con import ConAgent
from debate.agents.judge import JudgeAgent
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


class TestJudgeAgent:
    def test_spawns_child_agents(self, minimal_config, skill_registry, mock_gatekeeper):
        judge = JudgeAgent(minimal_config, skill_registry, mock_gatekeeper)
        assert isinstance(judge._pro, ProAgent)
        assert isinstance(judge._con, ConAgent)

    def test_run_debate_returns_transcript_and_verdict(
        self, minimal_config, skill_registry, mock_gatekeeper
    ):
        judge = JudgeAgent(minimal_config, skill_registry, mock_gatekeeper)
        transcript, verdict = judge.run_debate()
        assert len(transcript) > 0
        assert verdict.winner in (Role.PRO, Role.CON)

    def test_pro_context_round_1_has_no_con_message(self):
        from debate.agents.judge import JudgeAgent
        from debate.models.message import DebateMessage, MessageType, Role

        mod = DebateMessage(
            round=1, role=Role.JUDGE, message_type=MessageType.MODERATION, content="Go!"
        )
        ctx = JudgeAgent._build_pro_context(mod, last_con=None)
        assert ctx == "Go!"

    def test_pro_context_round_2_includes_con_message(self):
        from debate.agents.judge import JudgeAgent
        from debate.models.message import DebateMessage, MessageType, Role

        mod = DebateMessage(
            round=2, role=Role.JUDGE, message_type=MessageType.MODERATION, content="Round 2."
        )
        con_msg = DebateMessage(
            round=1, role=Role.CON, message_type=MessageType.REBUTTAL, content="AI is harmful."
        )
        ctx = JudgeAgent._build_pro_context(mod, last_con=con_msg)
        assert "Round 2." in ctx
        assert "CON" in ctx

    def test_con_always_receives_pro_argument(self):
        from debate.agents.judge import JudgeAgent
        from debate.models.message import DebateMessage, MessageType, Role

        mod = DebateMessage(
            round=1, role=Role.JUDGE, message_type=MessageType.MODERATION, content="Go!"
        )
        pro_msg = DebateMessage(
            round=1, role=Role.PRO, message_type=MessageType.ARGUMENT, content="AI helps."
        )
        ctx = JudgeAgent._build_con_context(mod, pro_msg)
        assert "PRO" in ctx
        assert "AI helps." in ctx

    def test_verdict_winner_cannot_be_judge(self, minimal_config, skill_registry, mock_gatekeeper):
        judge = JudgeAgent(minimal_config, skill_registry, mock_gatekeeper)
        _, verdict = judge.run_debate()
        assert verdict.winner != Role.JUDGE


class TestBaseAgentJsonParsing:
    """Validate the layered JSON extraction logic in BaseAgent."""

    def test_parses_clean_json(self):
        result = BaseAgent._parse_json('{"content": "hello", "evidence": []}')
        assert result["content"] == "hello"

    def test_parses_fenced_json(self):
        result = BaseAgent._parse_json('```json\n{"content": "hi", "evidence": []}\n```')
        assert result["content"] == "hi"

    def test_parses_embedded_json(self):
        result = BaseAgent._parse_json('Some text {"content": "embedded"} more text')
        assert result["content"] == "embedded"

    def test_falls_back_to_plain_text(self):
        result = BaseAgent._parse_json("This is not JSON at all.")
        assert result["content"] == "This is not JSON at all."
        assert result["evidence"] == []
