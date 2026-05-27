"""Tests for Pydantic data models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from debate.models.message import DebateMessage, Evidence, MessageType, Role
from debate.models.verdict import RoundScore, Verdict


class TestDebateMessage:
    def test_creates_with_required_fields(self):
        msg = DebateMessage(
            round=1,
            role=Role.PRO,
            message_type=MessageType.ARGUMENT,
            content="AI will cure diseases.",
        )
        assert msg.role == Role.PRO
        assert msg.evidence == []
        assert msg.id  # auto-generated UUID

    def test_unique_ids(self):
        a = DebateMessage(round=1, role=Role.PRO, message_type=MessageType.ARGUMENT, content="a")
        b = DebateMessage(round=1, role=Role.PRO, message_type=MessageType.ARGUMENT, content="b")
        assert a.id != b.id

    def test_to_context_string_includes_evidence(self):
        msg = DebateMessage(
            round=2,
            role=Role.CON,
            message_type=MessageType.REBUTTAL,
            content="AI has risks.",
            evidence=[Evidence(source="IEEE", quote="Bias in models", url=None)],
        )
        ctx = msg.to_context_string()
        assert "Round 2" in ctx
        assert "CON" in ctx
        assert "IEEE" in ctx
        assert "Bias in models" in ctx

    def test_to_log_entry_is_serialisable(self):
        import json
        msg = DebateMessage(
            round=1, role=Role.JUDGE, message_type=MessageType.MODERATION, content="Welcome."
        )
        entry = msg.to_log_entry()
        # must round-trip through JSON without error
        json.dumps(entry)
        assert entry["role"] == "judge"


class TestEvidence:
    def test_url_is_optional(self):
        ev = Evidence(source="Nature", quote="AI works well.")
        assert ev.url is None

    def test_quote_required(self):
        with pytest.raises(ValidationError):
            Evidence(source="Nature")  # type: ignore[call-arg]


class TestVerdict:
    def _sample_verdict(self, winner: Role) -> Verdict:
        return Verdict(
            winner=winner,
            total_pro_score=30.0,
            total_con_score=25.0,
            round_scores=[
                RoundScore(round=1, pro_score=6.0, con_score=5.0, reasoning="Pro was stronger.")
            ],
            reasoning="Pro presented clearer evidence.",
            key_turning_point="Round 1 medical AI argument.",
        )

    def test_pro_wins(self):
        v = self._sample_verdict(Role.PRO)
        assert "PRO wins" in v.summary()

    def test_con_wins(self):
        v = Verdict(
            winner=Role.CON,
            total_pro_score=20.0,
            total_con_score=35.0,
            round_scores=[],
            reasoning="Con was superior.",
            key_turning_point="Round 2.",
        )
        assert "CON wins" in v.summary()

    def test_judge_cannot_win(self):
        with pytest.raises(ValidationError):
            self._sample_verdict(Role.JUDGE)
