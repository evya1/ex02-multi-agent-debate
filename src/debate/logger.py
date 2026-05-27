"""
DebateLogger — writes every DebateMessage (and the final Verdict) to a JSONL file.

Why JSONL?
  - One JSON object per line makes it trivial to stream, grep, and replay.
  - The file is human-readable AND machine-parseable without a special parser.
  - Each entry is a self-contained snapshot, so partial logs are still useful.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from debate.models.message import DebateMessage
from debate.models.verdict import Verdict

logger = logging.getLogger(__name__)


class DebateLogger:
    def __init__(self, log_path: Path) -> None:
        self._path = log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = log_path.open("a", encoding="utf-8")

    def log_message(self, message: DebateMessage) -> None:
        self._write(message.to_log_entry())

    def log_verdict(self, verdict: Verdict) -> None:
        entry = {
            "event": "verdict",
            **verdict.model_dump(mode="json"),
        }
        self._write(entry)

    def log_event(self, event: str, **kwargs) -> None:
        self._write({"event": event, **kwargs})

    def close(self) -> None:
        self._file.flush()
        self._file.close()

    def _write(self, record: dict) -> None:
        self._file.write(json.dumps(record, default=str) + "\n")
        self._file.flush()
        logger.debug("Logged: %s", record.get("event") or record.get("message_type"))

    def __enter__(self) -> DebateLogger:
        return self

    def __exit__(self, *_) -> None:
        self.close()
