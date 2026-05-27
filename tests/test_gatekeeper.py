"""
Tests for the Gatekeeper's budget accounting, rate limiting, and timeout logic.

The Anthropic client and DuckDuckGo are mocked to avoid real network calls.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from debate.gatekeeper import BudgetExceededError, Gatekeeper
from debate.models.config import (
    AgentModelConfig,
    AppConfig,
    DebateParameters,
    GatekeeperSettings,
    LogSettings,
    PricingEntry,
    TimeoutSettings,
    WatchdogSettings,
)

_MODEL = "claude-haiku-4-5-20251001"
_PRICING = {_MODEL: PricingEntry(input_per_mtok=0.8, output_per_mtok=4.0)}


def _make_config(max_budget: float = 10.0, max_rpm: int = 60) -> AppConfig:
    agent = AgentModelConfig(model=_MODEL, max_tokens=256)
    return AppConfig(
        debate=DebateParameters(topic="Test", rounds=1),
        judge=agent,
        pro=agent,
        con=agent,
        gatekeeper=GatekeeperSettings(max_budget_usd=max_budget, max_calls_per_minute=max_rpm),
        timeouts=TimeoutSettings(agent_call_seconds=5, evidence_search_seconds=2),
        watchdog=WatchdogSettings(enabled=False),
        logging=LogSettings(console=False),
        pricing=_PRICING,
    )


def _fake_response(input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    text = MagicMock()
    text.type = "text"
    text.text = '{"content": "test", "evidence": []}'
    resp.content = [text]
    resp.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return resp


def _llm_kwargs() -> dict:
    return dict(
        messages=[{"role": "user", "content": "hi"}],
        system="s",
        model=_MODEL,
        max_tokens=256,
    )


@patch("debate.gatekeeper.Gatekeeper._require_api_key", return_value="fake-key")
@patch("debate.gatekeeper.anthropic.Anthropic")
class TestGatekeeperBudget:
    def test_tracks_cost_after_call(self, mock_anthropic, _mock_key):
        mock_anthropic.return_value.messages.create.return_value = _fake_response(100, 50)
        gk = Gatekeeper(_make_config())
        gk.call_llm(**_llm_kwargs())
        expected = (100 * 0.8 + 50 * 4.0) / 1_000_000
        assert abs(gk.total_cost - expected) < 1e-9

    def test_raises_when_budget_exceeded(self, mock_anthropic, _mock_key):
        big = _fake_response(1_000_000, 1_000_000)
        mock_anthropic.return_value.messages.create.return_value = big
        gk = Gatekeeper(_make_config(max_budget=0.0001))
        with pytest.raises(BudgetExceededError):
            gk.call_llm(**_llm_kwargs())
            gk.call_llm(**_llm_kwargs())


@patch("debate.gatekeeper.Gatekeeper._require_api_key", return_value="fake-key")
@patch("debate.gatekeeper.anthropic.Anthropic")
class TestGatekeeperTimeout:
    def test_raises_on_slow_llm_call(self, mock_anthropic, _mock_key):
        def slow(*args, **kwargs):
            time.sleep(10)
            return _fake_response()

        mock_anthropic.return_value.messages.create.side_effect = slow
        gk = Gatekeeper(_make_config())
        gk._timeouts.agent_call_seconds = 0.1

        with pytest.raises(TimeoutError):
            gk.call_llm(**_llm_kwargs())


@patch("debate.gatekeeper.Gatekeeper._require_api_key", return_value="fake-key")
@patch("debate.gatekeeper.DDGS")
@patch("debate.gatekeeper.anthropic.Anthropic")
class TestGatekeeperSearch:
    def test_search_returns_results(self, mock_anthropic, mock_ddgs, _mock_key):  # noqa: ARG002
        ddgs_inst = MagicMock()
        ddgs_inst.__enter__ = lambda s: s
        ddgs_inst.__exit__ = MagicMock(return_value=False)
        ddgs_inst.text.return_value = [
            {"title": "BBC", "body": "AI is great.", "href": "https://bbc.com"}
        ]
        mock_ddgs.return_value = ddgs_inst

        gk = Gatekeeper(_make_config())
        results = gk.call_search("AI benefits")
        assert len(results) == 1
        assert results[0]["source"] == "BBC"
