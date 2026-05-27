"""
Tests for the Gatekeeper's budget accounting, rate limiting, and timeout logic.

Uses MockLLMProvider and MockSearchProvider so no real API calls are made.
"""

from __future__ import annotations

import time

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
from debate.providers.mock_llm import MockLLMProvider
from debate.providers.mock_search import MockSearchProvider

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


def _make_gatekeeper(
    max_budget: float = 10.0,
    max_rpm: int = 60,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> Gatekeeper:
    """Build a Gatekeeper with a mock LLM provider reporting specific token counts."""
    llm = MockLLMProvider()
    original_complete = llm.complete

    def complete_with_tokens(**kwargs):
        r = original_complete(**kwargs)
        r.input_tokens = input_tokens
        r.output_tokens = output_tokens
        return r

    llm.complete = complete_with_tokens  # type: ignore[method-assign]
    return Gatekeeper(_make_config(max_budget, max_rpm), llm, MockSearchProvider())


def _llm_kwargs() -> dict:
    return dict(
        messages=[{"role": "user", "content": "hi"}],
        system="s",
        model=_MODEL,
        max_tokens=256,
    )


class TestGatekeeperBudget:
    def test_tracks_cost_after_call(self):
        gk = _make_gatekeeper(input_tokens=100, output_tokens=50)
        gk.call_llm(**_llm_kwargs())
        expected = (100 * 0.8 + 50 * 4.0) / 1_000_000
        assert abs(gk.total_cost - expected) < 1e-9

    def test_raises_when_budget_exceeded(self):
        gk = _make_gatekeeper(max_budget=0.0, input_tokens=1_000_000, output_tokens=1_000_000)
        with pytest.raises(BudgetExceededError):
            gk.call_llm(**_llm_kwargs())


class TestGatekeeperTimeout:
    def test_raises_on_slow_llm_call(self, minimal_config):
        class SlowProvider(MockLLMProvider):
            def complete(self, **kwargs):
                time.sleep(10)
                return super().complete(**kwargs)

        gk = Gatekeeper(minimal_config, SlowProvider(), MockSearchProvider())
        gk._timeouts.agent_call_seconds = 0.1

        with pytest.raises(TimeoutError):
            gk.call_llm(**_llm_kwargs())


class TestGatekeeperSearch:
    def test_search_returns_results(self, minimal_config, mock_search_provider):
        gk = Gatekeeper(minimal_config, MockLLMProvider(), mock_search_provider)
        results = gk.call_search("AI benefits")
        assert len(results) >= 1
        assert "source" in results[0]
        assert "quote" in results[0]

    def test_search_result_shape(self, minimal_config, mock_search_provider):
        gk = Gatekeeper(minimal_config, MockLLMProvider(), mock_search_provider)
        results = gk.call_search("test query")
        for r in results:
            assert "source" in r
            assert "quote" in r
            assert "url" in r

    def test_provider_names_exposed(self, minimal_config):
        llm = MockLLMProvider()
        search = MockSearchProvider()
        gk = Gatekeeper(minimal_config, llm, search)
        assert gk.llm_provider_name == "mock"
        assert gk.search_provider_name == "mock_search"
