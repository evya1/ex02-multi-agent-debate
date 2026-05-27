"""
RateLimiter — budget cap, call-rate throttling, and cost tracking.

Extracted from Gatekeeper so each module has one responsibility:
  - RateLimiter  owns spend state and enforces limits.
  - Gatekeeper   owns the call machinery (timeout, provider dispatch).

BudgetExceededError is defined here and re-exported by gatekeeper.py for
backward-compatible imports (``from debate.gatekeeper import BudgetExceededError``).
"""

from __future__ import annotations

import logging
import threading
import time

from debate.models.config import GatekeeperSettings, PricingEntry

logger = logging.getLogger(__name__)


class BudgetExceededError(RuntimeError):
    """Raised when the cumulative LLM spend reaches the configured cap."""


class RateLimiter:
    """
    Tracks cumulative cost and enforces a per-minute call-rate ceiling.

    Thread-safe: all mutable state is guarded by a single lock.

    Args:
        gk_settings:  Budget cap and max calls-per-minute from AppConfig.
        pricing:      Per-model token pricing (input/output per million tokens).
    """

    def __init__(
        self,
        gk_settings: GatekeeperSettings,
        pricing: dict[str, PricingEntry],
    ) -> None:
        self._gk = gk_settings
        self._pricing = pricing
        self._total_cost: float = 0.0
        self._call_timestamps: list[float] = []
        self._lock = threading.Lock()

    # ── public interface ───────────────────────────────────────────────────────

    def check_budget(self) -> None:
        """Raise BudgetExceededError if the spend cap has been reached."""
        with self._lock:
            if self._total_cost >= self._gk.max_budget_usd:
                raise BudgetExceededError(
                    f"Budget cap of ${self._gk.max_budget_usd:.2f} reached "
                    f"(spent ${self._total_cost:.4f})."
                )

    def throttle(self) -> None:
        """Sleep until the per-minute call rate is within the configured limit."""
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

    def record_cost(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """Add the cost of one LLM call to the running total."""
        pricing: PricingEntry | None = self._pricing.get(model)
        if pricing is None:
            return  # unknown model — skip cost tracking
        cost = (
            input_tokens * pricing.input_per_mtok / 1_000_000
            + output_tokens * pricing.output_per_mtok / 1_000_000
        )
        with self._lock:
            self._total_cost += cost

    @property
    def total_cost(self) -> float:
        return self._total_cost
