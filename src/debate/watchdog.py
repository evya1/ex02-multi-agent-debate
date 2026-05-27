"""
Watchdog — a daemon thread that monitors long-running agent calls.

Why a watchdog instead of a hard timeout in every call?
  - The Gatekeeper already enforces per-call timeouts.
  - The Watchdog is a second line of defence for the overall session:
    it warns when a call has been active unusually long (network stall,
    model capacity issue) without forcibly killing it.
  - Keeping it non-destructive means a slow-but-valid call still completes;
    only genuinely hung calls need manual intervention.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid

from debate.models.config import WatchdogSettings

logger = logging.getLogger(__name__)


class Watchdog:
    """
    Non-destructive background monitor.  Agents register a call on entry
    and deregister it on exit; the watchdog thread fires a warning if any
    registered call exceeds the stall threshold.
    """

    def __init__(self, config: WatchdogSettings) -> None:
        self._config = config
        self._active: dict[str, float] = {}  # call_id → start_time
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._monitor, daemon=True, name="watchdog")

    def start(self) -> None:
        if self._config.enabled:
            self._thread.start()
            logger.debug(
                "Watchdog started (stall_threshold=%.0fs)",
                self._config.stall_threshold_seconds,
            )

    def stop(self) -> None:
        self._stop.set()

    def register(self, call_id: str | None = None) -> str:
        """Mark a call as in-flight.  Returns the call_id for deregistration."""
        cid = call_id or str(uuid.uuid4())[:8]
        with self._lock:
            self._active[cid] = time.monotonic()
        return cid

    def deregister(self, call_id: str) -> None:
        with self._lock:
            self._active.pop(call_id, None)

    # ── context manager interface ───────────────────────────────────────────

    def watch(self, label: str = ""):
        """Use as `with watchdog.watch('label'): ...` to auto-register/deregister."""
        return _WatchContext(self, label)

    # ── background thread ───────────────────────────────────────────────────

    def _monitor(self) -> None:
        while not self._stop.wait(timeout=self._config.check_interval_seconds):
            now = time.monotonic()
            with self._lock:
                snapshot = dict(self._active)
            for cid, start in snapshot.items():
                elapsed = now - start
                if elapsed > self._config.stall_threshold_seconds:
                    logger.warning(
                        "Watchdog: call '%s' has been running for %.0fs — possible stall.",
                        cid,
                        elapsed,
                    )


class _WatchContext:
    def __init__(self, dog: Watchdog, label: str) -> None:
        self._dog = dog
        self._label = label
        self._cid: str = ""

    def __enter__(self) -> _WatchContext:
        self._cid = self._dog.register(self._label or None)
        return self

    def __exit__(self, *_) -> None:
        self._dog.deregister(self._cid)
