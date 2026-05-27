"""
Transcript I/O — load DebateMessage objects from a JSONL log file.

Extracted from AgentDebateSDK so the file-parsing concern lives in one place.
Silently skips event-only lines (debate_start, debate_end, etc.).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_transcript(path: str | Path) -> list[Any]:
    """
    Load a JSONL debate log and return a list of DebateMessage objects.

    Args:
        path:  Path to a .jsonl file produced by the debate logger.

    Returns:
        List of DebateMessage instances (event-only lines are skipped).
    """
    from debate.models.message import DebateMessage

    messages = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if "role" in data and "content" in data:
                    messages.append(DebateMessage.model_validate(data))
            except Exception as exc:
                logger.debug("Skipping non-message log line: %s", exc)
    return messages
