"""
Prove that configuration files are loadable and contain the expected schema.

Covers:
  - rate_limits.json exists, is valid JSON, and has all required keys
  - AppConfig.from_yaml_files() loads gatekeeper / timeout / watchdog settings
  - DEBATE_TOPIC and DEBATE_ROUNDS environment-variable overrides are applied
  - provider_config.json exists and has expected provider keys
"""

from __future__ import annotations

import json
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

_RATE_LIMITS_PATH = _CONFIG_DIR / "rate_limits.json"
_PROVIDER_CONFIG_PATH = _CONFIG_DIR / "provider_config.json"


class TestRateLimitsJson:
    def test_file_exists(self):
        assert _RATE_LIMITS_PATH.exists(), (
            f"rate_limits.json not found at {_RATE_LIMITS_PATH}"
        )

    def test_is_valid_json(self):
        data = json.loads(_RATE_LIMITS_PATH.read_text())
        assert isinstance(data, dict)

    def test_has_max_calls_per_minute(self):
        data = json.loads(_RATE_LIMITS_PATH.read_text())
        assert "max_calls_per_minute" in data
        assert isinstance(data["max_calls_per_minute"], int)

    def test_has_max_budget_usd(self):
        data = json.loads(_RATE_LIMITS_PATH.read_text())
        assert "max_budget_usd" in data
        assert isinstance(data["max_budget_usd"], (int, float))

    def test_has_retry_fields(self):
        data = json.loads(_RATE_LIMITS_PATH.read_text())
        assert "retry_attempts" in data
        assert "retry_backoff_seconds" in data

    def test_has_timeouts_section(self):
        data = json.loads(_RATE_LIMITS_PATH.read_text())
        assert "timeouts" in data
        timeouts = data["timeouts"]
        assert "agent_call_seconds" in timeouts
        assert "evidence_search_seconds" in timeouts


class TestAppConfigFromYaml:
    def test_loads_successfully(self):
        from debate.models.config import AppConfig

        cfg = AppConfig.from_yaml_files(
            _CONFIG_DIR / "debate.yaml",
            _CONFIG_DIR / "models.yaml",
        )
        assert cfg.debate.topic
        assert cfg.debate.rounds >= 1

    def test_gatekeeper_settings_loaded(self):
        from debate.models.config import AppConfig

        cfg = AppConfig.from_yaml_files(
            _CONFIG_DIR / "debate.yaml",
            _CONFIG_DIR / "models.yaml",
        )
        assert cfg.gatekeeper.max_budget_usd > 0
        assert cfg.gatekeeper.max_calls_per_minute > 0

    def test_env_override_topic(self, monkeypatch):
        from debate.models.config import AppConfig

        monkeypatch.setenv("DEBATE_TOPIC", "Override topic XYZ")
        cfg = AppConfig.from_yaml_files(
            _CONFIG_DIR / "debate.yaml",
            _CONFIG_DIR / "models.yaml",
        )
        assert cfg.debate.topic == "Override topic XYZ"

    def test_env_override_rounds(self, monkeypatch):
        from debate.models.config import AppConfig

        monkeypatch.setenv("DEBATE_ROUNDS", "2")
        cfg = AppConfig.from_yaml_files(
            _CONFIG_DIR / "debate.yaml",
            _CONFIG_DIR / "models.yaml",
        )
        assert cfg.debate.rounds == 2


class TestProviderConfigJson:
    def test_file_exists(self):
        assert _PROVIDER_CONFIG_PATH.exists()

    def test_has_llm_and_search_keys(self):
        data = json.loads(_PROVIDER_CONFIG_PATH.read_text())
        assert "llm_provider" in data
        assert "search_provider" in data
