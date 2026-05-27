"""
Retry configuration tests — GatekeeperSettings carries retry fields
that must match rate_limits.json, and RateLimiter must accumulate costs
correctly across multiple calls.

Covers:
  - GatekeeperSettings.max_retries and retry_backoff_factor exist with correct types
  - Default max_retries is consistent with rate_limits.json retry_attempts
  - RateLimiter.record_cost accumulates costs faithfully across repeated calls
  - BudgetExceededError fires when cumulative spend reaches the cap
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from debate.gatekeeper import BudgetExceededError
from debate.models.config import GatekeeperSettings, PricingEntry
from debate.rate_limiter import RateLimiter

_RATE_LIMITS_PATH = Path(__file__).parent.parent.parent / "config" / "rate_limits.json"
_MODEL = "claude-haiku-4-5-20251001"
_PRICING = {_MODEL: PricingEntry(input_per_mtok=1.0, output_per_mtok=5.0)}


class TestRetryConfigFields:
    def test_has_max_retries(self):
        gs = GatekeeperSettings()
        assert hasattr(gs, "max_retries")
        assert isinstance(gs.max_retries, int)
        assert gs.max_retries >= 0

    def test_has_retry_backoff_factor(self):
        gs = GatekeeperSettings()
        assert hasattr(gs, "retry_backoff_factor")
        assert isinstance(gs.retry_backoff_factor, float)
        assert gs.retry_backoff_factor >= 1.0

    def test_default_retries_match_rate_limits_json(self):
        """GatekeeperSettings.max_retries must equal rate_limits.json retry_attempts."""
        data = json.loads(_RATE_LIMITS_PATH.read_text())
        assert data["retry_attempts"] == GatekeeperSettings().max_retries


class TestRateLimiterCostAccumulation:
    def _rl(self, max_budget: float = 10.0) -> RateLimiter:
        gs = GatekeeperSettings(max_budget_usd=max_budget, max_calls_per_minute=60)
        return RateLimiter(gs, _PRICING)

    def test_single_call_cost_tracked(self):
        rl = self._rl()
        rl.record_cost(_MODEL, 1_000_000, 0)
        assert abs(rl.total_cost - 1.0) < 1e-9  # 1M input tokens × $1/Mtok

    def test_accumulates_across_calls(self):
        rl = self._rl()
        rl.record_cost(_MODEL, 500_000, 100_000)
        rl.record_cost(_MODEL, 500_000, 100_000)
        expected = 2 * (500_000 * 1.0 / 1_000_000 + 100_000 * 5.0 / 1_000_000)
        assert abs(rl.total_cost - expected) < 1e-9

    def test_unknown_model_is_skipped(self):
        rl = self._rl()
        rl.record_cost("unknown-model-xyz", 999_999, 999_999)
        assert rl.total_cost == 0.0

    def test_budget_check_raises_when_exceeded(self):
        rl = self._rl(max_budget=0.001)
        rl.record_cost(_MODEL, 10_000_000, 0)  # $10, well over $0.001
        with pytest.raises(BudgetExceededError):
            rl.check_budget()

    def test_budget_check_passes_when_under(self):
        rl = self._rl(max_budget=10.0)
        rl.record_cost(_MODEL, 100, 50)  # tiny cost
        rl.check_budget()  # must not raise
