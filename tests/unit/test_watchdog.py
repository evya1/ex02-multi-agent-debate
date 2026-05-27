"""
Prove that the Watchdog correctly detects stalled in-flight calls.

Tests cover:
  - register() returns an ID; deregister() removes it cleanly
  - watch() context manager auto-registers on entry and deregisters on exit
  - A call exceeding stall_threshold_seconds triggers a WARNING log
  - A disabled watchdog never emits stall warnings
  - Stopping the watchdog while a call is registered does not crash
"""

from __future__ import annotations

import time

from debate.models.config import WatchdogSettings
from debate.watchdog import Watchdog


def _dog(*, enabled: bool = True, threshold: float = 0.05, interval: float = 0.02) -> Watchdog:
    """Build a Watchdog with very short timings so tests don't need real delays."""
    return Watchdog(
        WatchdogSettings(
            enabled=enabled,
            stall_threshold_seconds=threshold,
            check_interval_seconds=interval,
        )
    )


class TestWatchdogRegisterDeregister:
    def test_register_returns_string_id(self):
        dog = _dog(enabled=False)
        cid = dog.register()
        assert isinstance(cid, str) and len(cid) > 0

    def test_register_with_explicit_id(self):
        dog = _dog(enabled=False)
        cid = dog.register("my-call-001")
        assert cid == "my-call-001"

    def test_deregister_removes_active_entry(self):
        dog = _dog(enabled=False)
        cid = dog.register()
        dog.deregister(cid)
        with dog._lock:
            assert cid not in dog._active

    def test_deregister_missing_id_is_safe(self):
        dog = _dog(enabled=False)
        dog.deregister("nonexistent")  # must not raise


class TestWatchdogContextManager:
    def test_watch_auto_registers(self):
        dog = _dog(enabled=False)
        with dog.watch("test-label") as ctx:
            assert ctx._cid in dog._active

    def test_watch_auto_deregisters_on_exit(self):
        dog = _dog(enabled=False)
        with dog.watch("test-label") as ctx:
            cid = ctx._cid
        with dog._lock:
            assert cid not in dog._active

    def test_watch_deregisters_on_exception(self):
        dog = _dog(enabled=False)
        ctx_cid = None
        try:
            with dog.watch("err-label") as ctx:
                ctx_cid = ctx._cid
                raise RuntimeError("simulated error")
        except RuntimeError:
            pass
        with dog._lock:
            assert ctx_cid not in dog._active


class TestWatchdogStallDetection:
    def test_stall_emits_warning(self, caplog):
        """A registered call older than threshold must produce a WARNING."""
        import logging

        dog = _dog(enabled=True, threshold=0.05, interval=0.02)
        dog.start()
        cid = dog.register("slow-call")

        # Wait long enough for the watchdog thread to fire at least once
        time.sleep(0.20)

        dog.deregister(cid)
        dog.stop()

        with caplog.at_level(logging.WARNING, logger="debate.watchdog"):
            # Re-run: the stall is already logged; just verify the string appears
            pass

        # caplog captures may differ by pytest version — check the log text
        # by triggering a fresh short stall:
        dog2 = _dog(enabled=True, threshold=0.02, interval=0.01)
        with caplog.at_level(logging.WARNING):
            dog2.start()
            dog2.register("stall-target")
            time.sleep(0.12)
            dog2.stop()

        assert any("stall" in r.message.lower() or "running" in r.message.lower()
                   for r in caplog.records), (
            "Expected a stall warning from the watchdog"
        )

    def test_disabled_watchdog_does_not_emit_warning(self, caplog):
        import logging

        dog = _dog(enabled=False, threshold=0.02, interval=0.01)
        dog.start()  # should be a no-op
        dog.register("unused-call")
        time.sleep(0.08)
        dog.stop()

        stall_records = [
            r for r in caplog.records
            if r.name == "debate.watchdog" and r.levelno >= logging.WARNING
        ]
        assert not stall_records, "Disabled watchdog should never emit stall warnings"

    def test_start_stop_with_no_calls_is_safe(self):
        dog = _dog(enabled=True, threshold=0.05, interval=0.02)
        dog.start()
        time.sleep(0.06)
        dog.stop()  # must not raise or hang
