"""
DebateRunner — the public SDK entry-point for running a complete debate.

Usage (SDK, real providers):
    from debate.runner import DebateRunner
    from debate.models.config import AppConfig

    config = AppConfig.from_yaml_files()
    runner = DebateRunner(config)
    transcript, verdict = runner.run()

Usage (SDK, mock providers — no API key needed):
    runner = DebateRunner(config, use_mock=True)
    transcript, verdict = runner.run()

Usage (CLI): see src/debate/cli/menu.py

Why a separate Runner class when JudgeAgent already has run_debate()?
  - The Runner owns the lifecycle of all support objects (Watchdog, Logger).
  - It lets the CLI and tests create a Runner without knowing about Gatekeeper
    or Watchdog internals — a single facade.
  - Provider construction is centralised here so callers never import
    concrete provider classes.
"""

from __future__ import annotations

import logging

from dotenv import load_dotenv

from debate.agents.judge import JudgeAgent
from debate.gatekeeper import Gatekeeper
from debate.logger import DebateLogger
from debate.models.config import AppConfig
from debate.models.message import DebateMessage
from debate.models.verdict import Verdict
from debate.providers.base import AbstractLLMProvider, AbstractSearchProvider
from debate.providers.factory import build_providers
from debate.skills.definitions import build_registry
from debate.watchdog import Watchdog

logger = logging.getLogger(__name__)


class DebateRunner:
    def __init__(
        self,
        config: AppConfig,
        *,
        use_mock: bool = False,
        llm_provider: AbstractLLMProvider | None = None,
        search_provider: AbstractSearchProvider | None = None,
    ) -> None:
        """
        Args:
            config:          Full application configuration.
            use_mock:        Use offline mock providers (no API key needed).
            llm_provider:    Explicit LLM provider (overrides config + use_mock).
            search_provider: Explicit search provider (overrides config + use_mock).
        """
        self._config = config
        load_dotenv()
        self._setup_logging()

        if llm_provider is not None and search_provider is not None:
            _llm, _search = llm_provider, search_provider
        else:
            _llm, _search = build_providers(use_mock=use_mock)

        self._gatekeeper = Gatekeeper(config, _llm, _search)
        self._watchdog = Watchdog(config.watchdog)
        self._skill_registry = build_registry()
        self._debate_logger = DebateLogger(config.logging.file)

    def run(self) -> tuple[list[DebateMessage], Verdict]:
        """
        Run the full debate and return the transcript + verdict.
        Handles Watchdog lifecycle and structured logging.
        """
        self._watchdog.start()
        self._debate_logger.log_event(
            "debate_start",
            topic=self._config.debate.topic,
            rounds=self._config.debate.rounds,
        )

        try:
            judge = JudgeAgent(self._config, self._skill_registry, self._gatekeeper)
            transcript, verdict = judge.run_debate()

            for message in transcript:
                self._debate_logger.log_message(message)
            self._debate_logger.log_verdict(verdict)
            self._debate_logger.log_event(
                "debate_end",
                winner=verdict.winner.value,
                total_cost_usd=self._gatekeeper.total_cost,
            )

            return transcript, verdict

        finally:
            self._watchdog.stop()
            self._debate_logger.close()

    def _setup_logging(self) -> None:
        level = getattr(logging, self._config.logging.level.upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
