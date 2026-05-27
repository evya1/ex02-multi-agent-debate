"""
AgentDebateSDK — clean programmatic interface for the debate system.

Why a dedicated SDK class on top of DebateRunner?
  - Provides method-level documentation and discoverable API.
  - Adds utility methods (load_transcript, validate_config, list_skills,
    validate_skills) that are useful in scripts and integrations but are
    out of scope for DebateRunner.
  - Decouples the public API from implementation details; internal
    refactors don't break callers.

Usage:
    from debate.sdk import AgentDebateSDK

    sdk = AgentDebateSDK()
    transcript, verdict = sdk.run_debate("AI will help humanity", rounds=3)
    print(verdict.summary())

    skills = sdk.list_skills()
    ok = sdk.validate_skills()
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AgentDebateSDK:
    """
    High-level Python API for running debates, inspecting skills, and
    managing configuration — no CLI required.

    Args:
        config_path:  Path to debate.yaml (default: config/debate.yaml).
        models_path:  Path to models.yaml (default: config/models.yaml).
        use_mock:     Use offline mock providers (no ANTHROPIC_API_KEY needed).
    """

    def __init__(
        self,
        config_path: str | Path | None = None,
        models_path: str | Path | None = None,
        *,
        use_mock: bool = False,
    ) -> None:
        from debate.models.config import AppConfig

        self._use_mock = use_mock

        if config_path is not None or models_path is not None:
            dp = Path(config_path) if config_path else Path("config/debate.yaml")
            mp = Path(models_path) if models_path else Path("config/models.yaml")
            self._config = AppConfig.from_yaml_files(str(dp), str(mp))
        else:
            try:
                self._config = AppConfig.from_yaml_files()
            except Exception:
                # Fallback minimal config for mock-only / validation use
                from debate.models.config import (
                    AgentModelConfig,
                    DebateParameters,
                    GatekeeperSettings,
                    LogSettings,
                    TimeoutSettings,
                    WatchdogSettings,
                )
                _agent = AgentModelConfig(model="claude-haiku-4-5-20251001", max_tokens=512)
                self._config = AppConfig(
                    debate=DebateParameters(topic="AI will benefit humanity", rounds=3),
                    judge=_agent, pro=_agent, con=_agent,
                    gatekeeper=GatekeeperSettings(max_budget_usd=2.0, max_calls_per_minute=30),
                    timeouts=TimeoutSettings(agent_call_seconds=120, evidence_search_seconds=30),
                    watchdog=WatchdogSettings(enabled=False),
                    logging=LogSettings(console=False),
                )

    # ── core debate ────────────────────────────────────────────────────────────

    def run_debate(
        self,
        topic: str | None = None,
        rounds: int | None = None,
        *,
        use_mock: bool | None = None,
    ):
        """
        Run a complete debate and return (transcript, verdict).

        Args:
            topic:    Override the debate topic (default: from config).
            rounds:   Override the number of rounds (default: from config).
            use_mock: Override mock mode (default: SDK-level setting).

        Returns:
            tuple[list[DebateMessage], Verdict]
        """
        from debate.runner import DebateRunner

        cfg = self._config.model_copy(deep=True)
        if topic:
            cfg.debate.topic = topic
        if rounds is not None:
            cfg.debate.rounds = rounds

        mock = self._use_mock if use_mock is None else use_mock
        runner = DebateRunner(cfg, use_mock=mock)
        return runner.run()

    # ── transcript I/O ─────────────────────────────────────────────────────────

    def load_transcript(self, path: str | Path) -> list[Any]:
        """
        Load a JSONL debate log and return a list of DebateMessage objects.

        Silently skips event-only lines (e.g. debate_start, debate_end).
        """
        from debate.models.message import DebateMessage

        messages = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "role" in data and "content" in data:
                        messages.append(DebateMessage.model_validate(data))
                except Exception as exc:
                    logger.debug("Skipping non-message log line: %s", exc)
        return messages

    # ── config validation ──────────────────────────────────────────────────────

    def validate_config(self, path: str | Path | None = None) -> bool:
        """
        Validate a debate config file.  Returns True if valid.

        Args:
            path: Path to debate.yaml (defaults to config/debate.yaml).
        """
        from debate.models.config import AppConfig

        target = Path(path) if path else Path("config/debate.yaml")
        if not target.exists():
            logger.warning("validate_config: file not found: %s", target)
            return False
        try:
            AppConfig.from_yaml_files(str(target))
            return True
        except Exception as exc:
            logger.warning("validate_config: invalid config: %s", exc)
            return False

    # ── skill inspection ───────────────────────────────────────────────────────

    def list_skills(self) -> list[Any]:
        """Return all registered SkillDefinition objects."""
        from debate.skills.definitions import build_registry
        return list(build_registry().all())

    def validate_skills(self) -> dict[str, bool]:
        """
        Validate that every skill has a corresponding filesystem directory
        with SKILL.md and prompt.md.

        Returns:
            dict mapping skill_name → True/False (True = valid).
        """
        skills_root = Path(__file__).parent.parent.parent.parent / "skills"
        results: dict[str, bool] = {}
        for skill in self.list_skills():
            skill_dir = skills_root / skill.name
            ok = (
                skill_dir.is_dir()
                and (skill_dir / "SKILL.md").is_file()
                and (skill_dir / "prompt.md").is_file()
            )
            results[skill.name] = ok
            if not ok:
                logger.warning(
                    "validate_skills: skill '%s' missing filesystem docs at %s",
                    skill.name, skill_dir,
                )
        return results
