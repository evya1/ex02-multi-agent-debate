"""
AppConfig and its sub-configs are loaded from YAML files at startup.

Two files are merged:
  config/debate.yaml  — debate parameters, gatekeeper, watchdog, logging
  config/models.yaml  — per-agent model name, tokens, temperature

Why Pydantic instead of plain dicts?  Field validation, IDE completion,
and clean error messages if a config key is missing or the wrong type.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel


class AgentModelConfig(BaseModel):
    model: str
    max_tokens: int = 1024
    temperature: float = 0.7


class DebateParameters(BaseModel):
    topic: str
    rounds: int = 5
    mode: str = "budget"


class GatekeeperSettings(BaseModel):
    max_budget_usd: float = 2.0
    max_calls_per_minute: int = 20
    max_retries: int = 3
    retry_backoff_factor: float = 2.0


class TimeoutSettings(BaseModel):
    agent_call_seconds: float = 90.0
    evidence_search_seconds: float = 15.0


class WatchdogSettings(BaseModel):
    enabled: bool = True
    stall_threshold_seconds: float = 120.0
    check_interval_seconds: float = 10.0


class LogSettings(BaseModel):
    level: str = "INFO"
    file: Path = Path("logs/debate.jsonl")
    console: bool = True


class PricingEntry(BaseModel):
    input_per_mtok: float
    output_per_mtok: float


class AppConfig(BaseModel):
    debate: DebateParameters
    judge: AgentModelConfig
    pro: AgentModelConfig
    con: AgentModelConfig
    gatekeeper: GatekeeperSettings = GatekeeperSettings()
    timeouts: TimeoutSettings = TimeoutSettings()
    watchdog: WatchdogSettings = WatchdogSettings()
    logging: LogSettings = LogSettings()
    pricing: dict[str, PricingEntry] = {}

    @classmethod
    def from_yaml_files(
        cls,
        debate_path: Path = Path("config/debate.yaml"),
        models_path: Path = Path("config/models.yaml"),
    ) -> AppConfig:
        with open(debate_path) as f:
            debate_data = yaml.safe_load(f)
        with open(models_path) as f:
            models_data = yaml.safe_load(f)

        # Environment variables take precedence over YAML values.
        debate_section = debate_data["debate"]
        if os.getenv("DEBATE_TOPIC"):
            debate_section["topic"] = os.environ["DEBATE_TOPIC"]
        if os.getenv("DEBATE_ROUNDS"):
            debate_section["rounds"] = int(os.environ["DEBATE_ROUNDS"])

        pricing = {
            model: PricingEntry(**prices)
            for model, prices in models_data.get("pricing", {}).items()
        }

        return cls(
            debate=DebateParameters(**debate_section),
            judge=AgentModelConfig(**models_data["agents"]["judge"]),
            pro=AgentModelConfig(**models_data["agents"]["pro"]),
            con=AgentModelConfig(**models_data["agents"]["con"]),
            gatekeeper=GatekeeperSettings(**debate_data.get("gatekeeper", {})),
            timeouts=TimeoutSettings(**debate_data.get("timeouts", {})),
            watchdog=WatchdogSettings(**debate_data.get("watchdog", {})),
            logging=LogSettings(**debate_data.get("logging", {})),
            pricing=pricing,
        )
