"""
JSON parsing and evidence extraction utilities for agents.

Extracted from BaseAgent so the parsing concern lives in one focused module.
All functions are stateless and re-exported through BaseAgent as static methods
for backward compatibility with existing tests.
"""

from __future__ import annotations

import json
import logging
import re

from debate.models.message import Evidence

logger = logging.getLogger(__name__)


def parse_json(text: str) -> dict:
    """
    Extract a JSON object from an LLM response string.

    Tries three approaches in order:
      1. Direct parse  — the happy path (json_protocol_skill usually ensures this).
      2. Strip a markdown ```json ... ``` fence.
      3. Regex to find the first {...} block in the text.
    Falls back to wrapping the raw text in a minimal envelope if all else
    fails, so the debate is never interrupted by a formatting quirk.
    """
    stripped = text.strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    obj = re.search(r"\{.*\}", stripped, re.DOTALL)
    if obj:
        try:
            return json.loads(obj.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse JSON from response; wrapping as plain text.")
    return {"content": stripped, "evidence": []}


def extract_evidence(raw_list: list[dict]) -> list[Evidence]:
    """Convert raw JSON evidence entries into typed Evidence objects."""
    result = []
    for entry in raw_list:
        if not entry.get("quote"):
            continue
        result.append(
            Evidence(
                source=entry.get("source", "Unknown"),
                quote=entry["quote"],
                url=entry.get("url"),
            )
        )
    return result
