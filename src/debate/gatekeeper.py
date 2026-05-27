"""
Gatekeeper — the single point of contact with all external services.

Every LLM call and every search passes through here.
The Gatekeeper enforces budget, rate limits, and timeouts by delegating to
RateLimiter; it focuses on call dispatch and timeout wrapping.

Provider-agnostic since Phase 07:
  No direct imports of anthropic or duckduckgo_search. Accepts any
  AbstractLLMProvider / AbstractSearchProvider at construction time.
"""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from debate.models.config import AppConfig
from debate.providers.base import (
    AbstractLLMProvider,
    AbstractSearchProvider,
    LLMResponse,
    SearchResult,
)
from debate.rate_limiter import BudgetExceededError, RateLimiter  # noqa: F401 — re-export

logger = logging.getLogger(__name__)


class Gatekeeper:
    """
    Wraps every external call with budget accounting, rate limiting, and timeouts.
    Agents call `call_llm` and `call_search`; they never touch providers directly.

    Args:
        config:           Full application config (budget, rate, pricing, timeouts).
        llm_provider:     Concrete LLM back-end (AnthropicProvider, MockLLMProvider, …).
        search_provider:  Concrete search back-end (DuckDuckGoProvider, MockSearch, …).
    """

    def __init__(
        self,
        config: AppConfig,
        llm_provider: AbstractLLMProvider,
        search_provider: AbstractSearchProvider,
    ) -> None:
        self._llm = llm_provider
        self._search = search_provider
        self._timeouts = config.timeouts
        self._rate_limiter = RateLimiter(config.gatekeeper, config.pricing)

    # ── public API ─────────────────────────────────────────────────────────────

    def call_llm(
        self,
        *,
        messages: list[dict],
        system: str,
        model: str,
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> Any:  # returns LLMResponse (provider-agnostic)
        """Call the configured LLM with budget + rate + timeout guards."""
        self._rate_limiter.check_budget()
        self._rate_limiter.throttle()

        call_id = str(uuid.uuid4())[:8]
        logger.debug(
            "LLM call %s → provider=%s model=%s tokens=%d",
            call_id,
            self._llm.name(),
            model,
            max_tokens,
        )

        response: LLMResponse = self._run_with_timeout(
            lambda: self._llm.complete(
                model=model,
                system=system,
                messages=messages,
                max_tokens=max_tokens,
                tools=tools,
            ),
            timeout=self._timeouts.agent_call_seconds,
            label=f"LLM call {call_id}",
        )

        self._rate_limiter.record_cost(model, response.input_tokens, response.output_tokens)
        logger.debug(
            "LLM call %s done — stop_reason=%s, cost_so_far=$%.4f",
            call_id,
            response.stop_reason,
            self._rate_limiter.total_cost,
        )
        return response

    def call_search(self, query: str) -> list[dict]:
        """Search via the configured search provider; returns up to 5 results as dicts."""
        logger.debug("Evidence search via %s: %r", self._search.name(), query)
        results: list[SearchResult] = self._run_with_timeout(
            lambda: self._search.search(query, max_results=5),
            timeout=self._timeouts.evidence_search_seconds,
            label=f"search({query[:40]})",
        )
        return [{"source": r.source, "quote": r.quote, "url": r.url} for r in (results or [])]

    @property
    def total_cost(self) -> float:
        return self._rate_limiter.total_cost

    @property
    def llm_provider_name(self) -> str:
        return self._llm.name()

    @property
    def search_provider_name(self) -> str:
        return self._search.name()

    # ── internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _run_with_timeout(fn, timeout: float, label: str):
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(fn)
            try:
                return future.result(timeout=timeout)
            except FutureTimeoutError as exc:
                raise TimeoutError(f"{label} timed out after {timeout}s") from exc
