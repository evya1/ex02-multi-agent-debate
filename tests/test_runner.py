"""
Integration-level tests for DebateRunner.

The full chain (Runner → Judge → Pro/Con → Gatekeeper) is exercised with
all external calls mocked, producing a complete 1-round debate without
any real API or network access.

We use pytest-mock's `mocker` fixture rather than class-level `@patch` stacks
to avoid parameter-order confusion that arises when multiple decorators are applied.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from debate.models.message import Role
from debate.runner import DebateRunner


def _make_fake_llm_response() -> MagicMock:
    """A minimal Anthropic Message mock that ends normally with a JSON argument."""
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    text = MagicMock()
    text.type = "text"
    text.text = (
        '{"message_type":"argument","role":"pro","round":1,'
        '"content":"AI has immense benefits.","evidence":['
        '{"source":"Reuters","quote":"AI saves lives.","url":"https://reuters.com"}]}'
    )
    resp.content = [text]
    resp.usage = MagicMock(input_tokens=200, output_tokens=80)
    return resp


def _patch_externals(mocker):
    """Mock all three external surfaces: API key, Anthropic client, DuckDuckGo."""
    mocker.patch(
        "debate.gatekeeper.Gatekeeper._require_api_key",
        return_value="fake-key",
    )
    mock_anthropic = mocker.patch("debate.gatekeeper.anthropic.Anthropic")
    mock_anthropic.return_value.messages.create.return_value = _make_fake_llm_response()

    mock_ddgs_inst = MagicMock()
    mock_ddgs_inst.__enter__ = lambda s: s
    mock_ddgs_inst.__exit__ = MagicMock(return_value=False)
    mock_ddgs_inst.text.return_value = [
        {"title": "Reuters", "body": "AI saves lives.", "href": "https://reuters.com"}
    ]
    mocker.patch("debate.gatekeeper.DDGS", return_value=mock_ddgs_inst)

    return mock_anthropic, mock_ddgs_inst


class TestDebateRunner:
    def test_run_returns_non_empty_transcript(
        self, mocker, minimal_config, tmp_path
    ):
        _patch_externals(mocker)
        minimal_config.logging.file = tmp_path / "test.jsonl"

        runner = DebateRunner(minimal_config)
        transcript, verdict = runner.run()

        assert len(transcript) >= 3  # at least: opening, pro arg, con arg

    def test_run_produces_verdict_with_winner(
        self, mocker, minimal_config, tmp_path
    ):
        _patch_externals(mocker)
        minimal_config.logging.file = tmp_path / "test.jsonl"

        runner = DebateRunner(minimal_config)
        _, verdict = runner.run()

        assert verdict.winner in (Role.PRO, Role.CON)
        assert verdict.winner != Role.JUDGE

    def test_log_file_is_created(self, mocker, minimal_config, tmp_path):
        _patch_externals(mocker)
        log_path = tmp_path / "test.jsonl"
        minimal_config.logging.file = log_path

        runner = DebateRunner(minimal_config)
        runner.run()

        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) > 0  # at least the debate_start event

    def test_no_direct_agent_communication(
        self, mocker, minimal_config, tmp_path, skill_registry
    ):
        """
        Routing invariant: ProAgent and ConAgent have no reference to each other.
        All routing goes through JudgeAgent.
        """
        _patch_externals(mocker)
        mocker.patch(
            "debate.gatekeeper.Gatekeeper._require_api_key",
            return_value="fake-key",
        )
        minimal_config.logging.file = tmp_path / "test.jsonl"

        from debate.agents.judge import JudgeAgent
        from debate.gatekeeper import Gatekeeper

        gk = Gatekeeper(minimal_config)
        judge = JudgeAgent(minimal_config, skill_registry, gk)

        # Pro has no reference to Con; Con has no reference to Pro.
        assert not hasattr(judge._pro, "_con")
        assert not hasattr(judge._con, "_pro")

    def test_pro_and_con_never_share_history(
        self, mocker, minimal_config, tmp_path
    ):
        """
        Each agent maintains its own private conversation history.
        Confirms that no shared mutable state exists between debaters.
        """
        _patch_externals(mocker)
        minimal_config.logging.file = tmp_path / "test.jsonl"

        from debate.agents.judge import JudgeAgent
        from debate.gatekeeper import Gatekeeper
        from debate.skills.definitions import build_registry

        gk = Gatekeeper(minimal_config)
        judge = JudgeAgent(minimal_config, build_registry(), gk)

        assert judge._pro._history is not judge._con._history
        assert judge._pro._history is not judge._history
