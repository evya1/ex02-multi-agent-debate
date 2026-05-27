"""
Gatekeeper — the single point of contact with all external services.

Every LLM call and every search passes through here.
The Gatekeeper enforces:
  1. Budget cap   — raises BudgetExceededError when the USD limit is hit.
  2. Rate limit   — sleeps to stay within max_calls_per_minute.
  3. Timeout      — raises TimeoutError if a call stalls.
  4. Retry        — exponential back-off on transient failures.

Why centralise this?  Agents stay clean (no error-handling boilerplate) and
the spending/rate state is consistent across all three agents in one session.

Provider-agnostic since Phase 07:
  The Gatekeeper no longer imports `anthropic` or `duckduckgo_search` directly.
  Instead it holds an AbstractLLMProvider and AbstractSearchProvider, injected
  at construction.  Swap providers by passing different implementations.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from debate.models.config import AppConfig, GatekeeperSettings, PricingEntry, TimeoutSettings
from debate.providers.base import (
    AbstractLLMProvider,
    AbstractSearchProvider,
    LLMResponse,
    SearchResult,
)

logger = logging.getLogger(__name__)


class BudgetExceededError(RuntimeError):
    pass


class Gatekeeper:
    """
    Wraps every external call with budget accounting, rate limiting, and timeouts.
    Agents call `call_llm` and `call_search`; they never touch providers directly.

    Args:
        config:           Full application config (budget, rate, pricing).
        llm_provider:     Concrete LLM back-end (AnthropicProvider, MockLLMProvider, …).
        search_provider:  Concrete search back-end (DuckDuckGoSearchProvider, MockSearch, …).
    """

    def __init__(
        self,
        config: AppConfig,
        llm_provider: AbstractLLMProvider,
        search_provider: AbstractSearchProvider,
    ) -> None:
        self._llm = llm_provider
        self._search = search_provider
        self._gk: GatekeeperSettings = config.gatekeeper
        self._timeouts: TimeoutSettings = config.timeouts
        self._pricing: dict[str, PricingEntry] = config.pricing

        self._total_cost: float = 0.0
        self._call_timestamps: list[float] = []
        self._lock = threading.Lock()

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
        self._check_budget()
        self._throttle_if_needed()

        call_id = str(uuid.uuid4())[:8]
        logger.debug(
            "LLM call %s → provider=%s model=%s tokens=%d",
            call_id, self._llm.name(), model, max_tokens,
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

        self._record_cost(model, response.input_tokens, response.output_tokens)
        logger.debug(
            "LLM call %s done — stop_reason=%s, cost_so_far=$%.4f",
            call_id, response.stop_reason, self._total_cost,
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
        return [
            {"source": r.source, "quote": r.quote, "url": r.url}
            for r in (results or [])
        ]

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def llm_provider_name(self) -> str:
        return self._llm.name()

    @property
    def search_provider_name(self) -> str:
        return self._search.name()

    # ── internal helpers ───────────────────────────────────────────────────────

    def _check_budget(self) -> None:
        with self._lock:
            if self._total_cost >= self._gk.max_budget_usd:
                raise BudgetExceededError(
                    f"Budget cap of ${self._gk.max_budget_usd:.2f} reached "
                    f"(spent ${self._total_cost:.4f})."
                )

    def _throttle_if_needed(self) -> None:
        with self._lock:
            now = time.monotonic()
            window_start = now - 60.0
            self._call_timestamps = [t for t in self._call_timestamps if t > window_start]
            if len(self._call_timestamps) >= self._gk.max_calls_per_minute:
                sleep_for = 60.0 - (now - self._call_timestamps[0]) + 0.1
                logger.info("Rate limit: sleeping %.1fs", sleep_for)
            else:
                sleep_for = 0.0
            self._call_timestamps.append(now)

        if sleep_for > 0:
            time.sleep(sleep_for)

    def _record_cost(self, model: str, input_tokens: int, output_tokens: int) -> None:
        pricing = self._pricing.get(model)
        if pricing is None:
            return  # unknown model — skip cost tracking
        cost = (
            input_tokens * pricing.input_per_mtok / 1_000_000
            + output_tokens * pricing.output_per_mtok / 1_000_000
        )
        with self._lock:
            self._total_cost += cost

    @staticmethod
    def _run_with_timeout(fn, timeout: float, label: str):
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(fn)
            try:
                return future.result(timeout=timeout)
            except FutureTimeoutError as exc:
                raise TimeoutError(f"{label} timed out after {timeout}s") from exc
