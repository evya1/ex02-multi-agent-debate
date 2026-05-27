"""
Config loading helper for AgentDebateSDK.

Provides ``load_sdk_config()``: loads AppConfig from YAML files and falls
back to a minimal in-memory config when the files are absent or invalid.
The fallback is only used for mock-only / validation mode (no real debates).
"""

from __future__ import annotations

from pathlib import Path

from debate.models.config import AppConfig


def load_sdk_config(
    config_path: str | Path | None = None,
    models_path: str | Path | None = None,
) -> AppConfig:
    """
    Load AppConfig from YAML, falling back to a minimal default on failure.

    Args:
        config_path:  Path to debate.yaml  (default: config/debate.yaml).
        models_path:  Path to models.yaml  (default: config/models.yaml).

    Returns:
        A validated AppConfig instance.
    """
    if config_path is not None or models_path is not None:
        dp = Path(config_path) if config_path else Path("config/debate.yaml")
        mp = Path(models_path) if models_path else Path("config/models.yaml")
        return AppConfig.from_yaml_files(str(dp), str(mp))

    try:
        return AppConfig.from_yaml_files()
    except Exception:
        return _minimal_fallback_config()


def _minimal_fallback_config() -> AppConfig:
    """Build the smallest valid AppConfig for mock-only / validation use."""
    from debate.models.config import (
        AgentModelConfig,
        DebateParameters,
        GatekeeperSettings,
        LogSettings,
        TimeoutSettings,
        WatchdogSettings,
    )

    _agent = AgentModelConfig(model="claude-haiku-4-5-20251001", max_tokens=512)
    return AppConfig(
        debate=DebateParameters(topic="AI will benefit humanity", rounds=3),
        judge=_agent,
        pro=_agent,
        con=_agent,
        gatekeeper=GatekeeperSettings(max_budget_usd=2.0, max_calls_per_minute=30),
        timeouts=TimeoutSettings(agent_call_seconds=120, evidence_search_seconds=30),
        watchdog=WatchdogSettings(enabled=False),
        logging=LogSettings(console=False),
    )
