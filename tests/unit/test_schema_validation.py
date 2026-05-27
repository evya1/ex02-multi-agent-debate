"""
Schema validation tests — Pydantic models must reject invalid input.

Covers:
  - Verdict.winner cannot be Role.JUDGE (field_validator enforced)
  - DebateMessage requires valid Role and non-empty content
  - Evidence requires a quote field
  - build_verdict() applies sensible defaults and enforces valid winner role
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from debate.agents.verdict_builder import build_verdict
from debate.models.message import DebateMessage, Evidence, MessageType, Role
from debate.models.verdict import Verdict


class TestVerdictSchemaValidation:
    def test_judge_as_winner_raises(self):
        with pytest.raises(ValidationError):
            Verdict(
                winner=Role.JUDGE,
                total_pro_score=5.0,
                total_con_score=5.0,
                round_scores=[],
                reasoning="test",
                key_turning_point="none",
            )

    def test_missing_required_field_raises(self):
        with pytest.raises((ValidationError, TypeError)):
            Verdict(  # type: ignore[call-arg]
                winner=Role.PRO,
                total_pro_score=5.0,
                # total_con_score intentionally omitted
                round_scores=[],
                reasoning="r",
                key_turning_point="k",
            )

    def test_valid_pro_winner_accepted(self):
        v = Verdict(
            winner=Role.PRO,
            total_pro_score=7.0,
            total_con_score=3.0,
            round_scores=[],
            reasoning="pro was better",
            key_turning_point="round 1",
        )
        assert v.winner == Role.PRO

    def test_build_verdict_defaults_winner_on_missing_key(self):
        """build_verdict must not crash when 'winner' key is absent."""
        data = {"reasoning": "unclear", "key_turning_point": "none"}
        verdict = build_verdict(data)
        assert verdict.winner in (Role.PRO, Role.CON)

    def test_build_verdict_con_winner(self):
        data = {
            "winner": "con",
            "total_pro_score": 20.0,
            "total_con_score": 30.0,
            "round_scores": [],
            "reasoning": "con won",
            "key_turning_point": "r2",
        }
        v = build_verdict(data)
        assert v.winner == Role.CON


class TestDebateMessageSchemaValidation:
    def test_valid_message_accepted(self):
        msg = DebateMessage(
            round=1,
            role=Role.PRO,
            message_type=MessageType.ARGUMENT,
            content="AI is beneficial.",
        )
        assert msg.content == "AI is beneficial."

    def test_invalid_role_string_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            DebateMessage(
                round=1,
                role="not_a_real_role",  # type: ignore[arg-type]
                message_type=MessageType.ARGUMENT,
                content="x",
            )

    def test_missing_content_field_raises(self):
        with pytest.raises((ValidationError, TypeError)):
            DebateMessage(  # type: ignore[call-arg]
                round=1,
                role=Role.PRO,
                message_type=MessageType.ARGUMENT,
                # content missing
            )


class TestEvidenceSchemaValidation:
    def test_url_is_optional(self):
        ev = Evidence(source="src", quote="q")
        assert ev.url is None

    def test_missing_quote_raises(self):
        with pytest.raises((ValidationError, TypeError)):
            Evidence(source="src")  # type: ignore[call-arg]
