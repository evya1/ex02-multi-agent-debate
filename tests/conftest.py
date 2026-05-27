"""
Shared pytest fixtures.

All fixtures use mock providers so tests run offline without any API key.
The debate config is set to 1 round to keep test execution fast.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from debate.gatekeeper import Gatekeeper
from debate.models.config import (
    AgentModelConfig,
    AppConfig,
    DebateParameters,
    GatekeeperSettings,
    LogSettings,
    TimeoutSettings,
    WatchdogSettings,
)
from debate.providers.mock_llm import MockLLMProvider
from debate.providers.mock_search import MockSearchProvider
from debate.skills.definitions import build_registry


@pytest.fixture()
def minimal_config() -> AppConfig:
    """One-round debate config with no real API keys required."""
    agent = AgentModelConfig(model="claude-haiku-4-5-20251001", max_tokens=256)
    return AppConfig(
        debate=DebateParameters(topic="Test topic", rounds=1),
        judge=agent,
        pro=agent,
        con=agent,
        gatekeeper=GatekeeperSettings(max_budget_usd=10.0, max_calls_per_minute=60),
        timeouts=TimeoutSettings(agent_call_seconds=30, evidence_search_seconds=5),
        watchdog=WatchdogSettings(enabled=False),
        logging=LogSettings(file=Path("logs/test.jsonl"), console=False),
    )


@pytest.fixture()
def skill_registry():
    return build_registry()


@pytest.fixture()
def mock_llm_provider():
    """A deterministic MockLLMProvider that never makes real API calls."""
    return MockLLMProvider()


@pytest.fixture()
def mock_search_provider():
    """A deterministic MockSearchProvider that never hits the web."""
    return MockSearchProvider()


@pytest.fixture()
def mock_gatekeeper(minimal_config, mock_llm_provider, mock_search_provider):
    """
    A real Gatekeeper wired to mock providers.
    Agents can call it normally; no real network access occurs.
    """
    return Gatekeeper(minimal_config, mock_llm_provider, mock_search_provider)
