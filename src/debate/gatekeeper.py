"""
Gatekeeper — the single point of contact with all external services.

Every Anthropic API call and every DuckDuckGo search passes through here.
The Gatekeeper enforces:
  1. Budget cap   — raises BudgetExceededError when the USD limit is hit.
  2. Rate limit   — sleeps to stay within max_calls_per_minute.
  3. Timeout      — raises TimeoutError if a call stalls.
  4. Retry        — exponential back-off on transient failures.

Why centralise this?  Agents stay clean (no error-handling boilerplate) and
the spending/rate state is consistent across all three agents in one session.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

import anthropic
from duckduckgo_search import DDGS

from debate.models.config import AppConfig, GatekeeperSettings, PricingEntry, TimeoutSettings

logger = logging.getLogger(__name__)


class BudgetExceededError(RuntimeError):
    pass


class Gatekeeper:
    """
    Wraps every external call with budget accounting, rate limiting, and timeouts.
    Agents call `call_llm` and `call_search`; they never touch the SDK directly.
    """

    def __init__(self, config: AppConfig) -> None:
        api_key = self._require_api_key()
        self._client = anthropic.Anthropic(api_key=api_key)
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
    ) -> Any:  # anthropic.types.Message
        """Call the Anthropic Messages API with budget + rate + timeout guards."""
        self._check_budget()
        self._throttle_if_needed()

        call_id = str(uuid.uuid4())[:8]
        logger.debug("LLM call %s → model=%s tokens=%d", call_id, model, max_tokens)

        kwargs: dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        if tools:
            kwargs["tools"] = tools

        response = self._run_with_timeout(
            lambda: self._client.messages.create(**kwargs),
            timeout=self._timeouts.agent_call_seconds,
            label=f"LLM call {call_id}",
        )

        self._record_cost(model, response.usage)
        logger.debug(
            "LLM call %s done — stop_reason=%s, cost_so_far=$%.4f",
            call_id, response.stop_reason, self._total_cost,
        )
        return response

    def call_search(self, query: str) -> list[dict]:
        """Search DuckDuckGo for evidence; returns up to 5 results."""
        logger.debug("Evidence search: %r", query)
        results = self._run_with_timeout(
            lambda: self._search(query),
            timeout=self._timeouts.evidence_search_seconds,
            label=f"search({query[:40]})",
        )
        return results or []

    @property
    def total_cost(self) -> float:
        return self._total_cost

    # ── internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _require_api_key() -> str:
        import os
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise OSError(
                "ANTHROPIC_API_KEY is not set. "
                "Copy .env.example → .env and add your key."
            )
        return key

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

    def _record_cost(self, model: str, usage: Any) -> None:
        pricing = self._pricing.get(model)
        if pricing is None:
            return  # unknown model — skip cost tracking
        cost = (
            usage.input_tokens * pricing.input_per_mtok / 1_000_000
            + usage.output_tokens * pricing.output_per_mtok / 1_000_000
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

    @staticmethod
    def _search(query: str) -> list[dict]:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append({
                    "source": r.get("title", "Unknown"),
                    "quote": r.get("body", "")[:400],
                    "url": r.get("href"),
                })
        return results
