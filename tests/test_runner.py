"""
Integration-level tests for DebateRunner.

The full chain (Runner → Judge → Pro/Con → Gatekeeper) is exercised
using MockLLMProvider and MockSearchProvider — no real API or network
access is required.
"""

from __future__ import annotations

from debate.models.message import Role
from debate.runner import DebateRunner


class TestDebateRunner:
    def test_run_returns_non_empty_transcript(self, minimal_config, tmp_path):
        minimal_config.logging.file = tmp_path / "test.jsonl"
        runner = DebateRunner(minimal_config, use_mock=True)
        transcript, verdict = runner.run()
        assert len(transcript) >= 3  # at least: opening, pro arg, con arg

    def test_run_produces_verdict_with_winner(self, minimal_config, tmp_path):
        minimal_config.logging.file = tmp_path / "test.jsonl"
        runner = DebateRunner(minimal_config, use_mock=True)
        _, verdict = runner.run()
        assert verdict.winner in (Role.PRO, Role.CON)
        assert verdict.winner != Role.JUDGE

    def test_log_file_is_created(self, minimal_config, tmp_path):
        log_path = tmp_path / "test.jsonl"
        minimal_config.logging.file = log_path
        runner = DebateRunner(minimal_config, use_mock=True)
        runner.run()
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) > 0

    def test_no_direct_agent_communication(self, minimal_config, tmp_path, skill_registry):
        """Routing invariant: Pro and Con have no reference to each other."""
        minimal_config.logging.file = tmp_path / "test.jsonl"

        from debate.agents.judge import JudgeAgent
        from debate.gatekeeper import Gatekeeper
        from debate.providers.mock_llm import MockLLMProvider
        from debate.providers.mock_search import MockSearchProvider

        gk = Gatekeeper(minimal_config, MockLLMProvider(), MockSearchProvider())
        judge = JudgeAgent(minimal_config, skill_registry, gk)

        assert not hasattr(judge._pro, "_con")
        assert not hasattr(judge._con, "_pro")

    def test_pro_and_con_never_share_history(self, minimal_config, tmp_path):
        """Each agent maintains its own private conversation history."""
        minimal_config.logging.file = tmp_path / "test.jsonl"

        from debate.agents.judge import JudgeAgent
        from debate.gatekeeper import Gatekeeper
        from debate.providers.mock_llm import MockLLMProvider
        from debate.providers.mock_search import MockSearchProvider
        from debate.skills.definitions import build_registry

        gk = Gatekeeper(minimal_config, MockLLMProvider(), MockSearchProvider())
        judge = JudgeAgent(minimal_config, build_registry(), gk)

        assert judge._pro._history is not judge._con._history
        assert judge._pro._history is not judge._history

    def test_explicit_provider_injection(self, minimal_config, tmp_path):
        """Providers can be injected explicitly (for advanced test scenarios)."""
        from debate.providers.mock_llm import MockLLMProvider
        from debate.providers.mock_search import MockSearchProvider

        minimal_config.logging.file = tmp_path / "test.jsonl"
        runner = DebateRunner(
            minimal_config,
            llm_provider=MockLLMProvider(),
            search_provider=MockSearchProvider(),
        )
        transcript, verdict = runner.run()
        assert verdict.winner in (Role.PRO, Role.CON)
