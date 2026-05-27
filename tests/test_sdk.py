"""
Tests for AgentDebateSDK — the high-level Python API.
Uses mock providers so no API key is needed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from debate.sdk import AgentDebateSDK


@pytest.fixture()
def sdk():
    return AgentDebateSDK(use_mock=True)


class TestSDKRunDebate:
    def test_run_debate_returns_transcript_and_verdict(self, sdk):
        transcript, verdict = sdk.run_debate("AI is beneficial", rounds=1)
        assert len(transcript) > 0

    def test_run_debate_verdict_has_winner(self, sdk):
        from debate.models.message import Role
        _, verdict = sdk.run_debate("AI will help humanity", rounds=1)
        assert verdict.winner in (Role.PRO, Role.CON)

    def test_run_debate_topic_override(self, sdk):
        transcript, _ = sdk.run_debate(topic="Custom debate topic", rounds=1)
        assert len(transcript) > 0

    def test_run_debate_mock_override(self, sdk):
        """Explicitly passing use_mock=True on run_debate works even if SDK not mock."""
        transcript, verdict = sdk.run_debate("AI", rounds=1, use_mock=True)
        assert len(transcript) > 0


class TestSDKLoadTranscript:
    def test_load_empty_jsonl(self, tmp_path):
        p = tmp_path / "debate.jsonl"
        p.write_text("")
        sdk = AgentDebateSDK(use_mock=True)
        msgs = sdk.load_transcript(p)
        assert msgs == []

    def test_load_event_lines_skipped(self, tmp_path):
        import json
        p = tmp_path / "debate.jsonl"
        lines = [
            json.dumps({"event": "debate_start", "topic": "AI", "rounds": 1}),
            json.dumps({"role": "judge", "round": 1, "message_type": "moderation",
                        "content": "Welcome.", "evidence": [],
                        "id": "abc", "debate_id": "", "skill_id_used": "",
                        "ping_index": None,
                        "timestamp": "2026-01-01T00:00:00+00:00", "in_reply_to": None}),
            json.dumps({"event": "debate_end", "winner": "pro"}),
        ]
        p.write_text("\n".join(lines))
        sdk = AgentDebateSDK(use_mock=True)
        msgs = sdk.load_transcript(p)
        assert len(msgs) == 1
        assert msgs[0].role.value == "judge"


class TestSDKValidateConfig:
    def test_valid_config_returns_true(self):
        sdk = AgentDebateSDK(use_mock=True)
        assert sdk.validate_config(Path("config/debate.yaml"))

    def test_missing_file_returns_false(self):
        sdk = AgentDebateSDK(use_mock=True)
        assert sdk.validate_config("/nonexistent/path.yaml") is False


class TestSDKSkills:
    def test_list_skills_returns_seven(self, sdk):
        skills = sdk.list_skills()
        assert len(skills) == 7

    def test_list_skills_names(self, sdk):
        names = {s.name for s in sdk.list_skills()}
        assert "judge_moderation_skill" in names
        assert "verdict_skill" in names
        assert "pro_argument_skill" in names

    def test_validate_skills_all_present(self, sdk):
        results = sdk.validate_skills()
        assert len(results) == 7
        for name, ok in results.items():
            assert ok, f"Skill '{name}' failed validation"

    def test_validate_skills_returns_dict(self, sdk):
        results = sdk.validate_skills()
        assert isinstance(results, dict)
        assert all(isinstance(v, bool) for v in results.values())
