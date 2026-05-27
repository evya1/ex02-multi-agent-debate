"""
Tests for JudgeAgent and BaseAgent utilities (root-level copy — see tests/unit/).
"""

from __future__ import annotations

from debate.agents.base import BaseAgent
from debate.agents.con import ConAgent
from debate.agents.judge import JudgeAgent
from debate.agents.pro import ProAgent
from debate.models.message import DebateMessage, MessageType, Role


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
        mod = DebateMessage(
            round=1, role=Role.JUDGE, message_type=MessageType.MODERATION, content="Go!"
        )
        ctx = JudgeAgent._build_pro_context(mod, last_con=None)
        assert ctx == "Go!"

    def test_pro_context_round_2_includes_con_message(self):
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
