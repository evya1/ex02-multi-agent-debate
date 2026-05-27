"""
Provider factory — builds the correct LLM and search providers based on
the provider_config.json setting (or an explicit override).

Why a factory?
  - DebateRunner and tests both need to construct providers; centralising
    the logic avoids repetition and makes it easy to add new providers.
  - The `use_mock` flag gives tests and CLI `--mock` mode a single toggle.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from debate.providers.base import AbstractLLMProvider, AbstractSearchProvider

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = Path(__file__).parent.parent.parent.parent / "config" / "provider_config.json"


def load_provider_config(path: Path | None = None) -> dict:
    """Load config/provider_config.json; return defaults if file is missing."""
    target = path or _DEFAULT_CONFIG
    if target.exists():
        with open(target) as f:
            return json.load(f)
    logger.warning("provider_config.json not found at %s; using defaults.", target)
    return {"llm_provider": "anthropic", "search_provider": "duckduckgo"}


def build_llm_provider(provider_name: str = "anthropic") -> AbstractLLMProvider:
    """Instantiate the named LLM provider."""
    if provider_name == "anthropic":
        from debate.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if provider_name == "mock":
        from debate.providers.mock_llm import MockLLMProvider
        return MockLLMProvider()
    raise ValueError(f"Unknown LLM provider: {provider_name!r}")


def build_search_provider(provider_name: str = "duckduckgo") -> AbstractSearchProvider:
    """Instantiate the named search provider."""
    if provider_name in ("duckduckgo", "ddgs"):
        from debate.providers.anthropic_provider import DuckDuckGoSearchProvider
        return DuckDuckGoSearchProvider()
    if provider_name == "mock":
        from debate.providers.mock_search import MockSearchProvider
        return MockSearchProvider()
    raise ValueError(f"Unknown search provider: {provider_name!r}")


def build_providers(
    *,
    use_mock: bool = False,
    config_path: Path | None = None,
) -> tuple[AbstractLLMProvider, AbstractSearchProvider]:
    """
    Return (llm_provider, search_provider) ready to pass to Gatekeeper.

    Args:
        use_mock:    Force mock providers (CLI --mock, test mode).
        config_path: Override path to provider_config.json.
    """
    if use_mock:
        logger.info("Provider mode: mock (offline)")
        from debate.providers.mock_llm import MockLLMProvider
        from debate.providers.mock_search import MockSearchProvider
        return MockLLMProvider(), MockSearchProvider()

    cfg = load_provider_config(config_path)
    llm_name = cfg.get("llm_provider", "anthropic")
    search_name = cfg.get("search_provider", "duckduckgo")
    logger.info("Provider mode: llm=%s search=%s", llm_name, search_name)
    return build_llm_provider(llm_name), build_search_provider(search_name)
