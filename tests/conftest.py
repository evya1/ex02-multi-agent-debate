"""
Shared pytest fixtures.

All fixtures that touch the Anthropic API use mocks so tests run
offline without any API key.  The debate config is set to 1 round
to keep test execution fast.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from debate.models.config import (
    AgentModelConfig,
    AppConfig,
    DebateParameters,
    GatekeeperSettings,
    LogSettings,
    TimeoutSettings,
    WatchdogSettings,
)
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
def mock_gatekeeper(minimal_config):
    """
    A Gatekeeper whose call_llm returns a valid JSON DebateMessage and
    whose call_search returns two fake search hits.
    Prevents any real network calls during tests.
    """
    gk = MagicMock()
    gk.total_cost = 0.0

    def fake_llm(**kwargs):
        msg = MagicMock()
        msg.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = (
            '{"message_type": "argument", "role": "pro", "round": 1, '
            '"content": "AI benefits humanity.", "evidence": ['
            '{"source": "Nature", "quote": "AI aids diagnostics.", "url": "https://example.com"}]}'
        )
        msg.content = [text_block]
        return msg

    def fake_search(query: str):
        return [
            {"source": "BBC News", "quote": "AI transforms healthcare.", "url": "https://bbc.com"},
            {"source": "MIT", "quote": "AI increases productivity.", "url": "https://mit.edu"},
        ]

    gk.call_llm.side_effect = fake_llm
    gk.call_search.side_effect = fake_search
    return gk
