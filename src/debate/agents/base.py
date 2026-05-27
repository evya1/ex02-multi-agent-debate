"""
BaseAgent — shared LLM-call mechanics for all three debate participants.

Design principles:
  - Agents never call the Anthropic SDK directly; everything flows through Gatekeeper.
  - Tool-use (evidence retrieval) is handled in the base class so Pro and Con
    don't need to duplicate the response-loop logic.
  - JSON parsing is centralised with a layered fallback strategy so a slightly
    malformed Claude response doesn't crash the debate.
  - Each agent maintains its own conversation history (the judge's history stays
    separate from the debaters', which keeps context windows smaller).
"""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod

from debate.gatekeeper import Gatekeeper
from debate.models.config import AgentModelConfig
from debate.models.message import DebateMessage, Evidence, MessageType, Role
from debate.models.skill import SkillDefinition
from debate.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

# The single tool available to debater agents (Pro, Con).
# The judge does not retrieve evidence — it moderates and judges.
EVIDENCE_TOOL: dict = {
    "name": "retrieve_evidence",
    "description": (
        "Search the web for real evidence to support your argument. "
        "Returns a list of {source, quote, url} objects."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Precise search query to find supporting evidence.",
            }
        },
        "required": ["query"],
    },
}


class BaseAgent(ABC):
    """
    Abstract base for JudgeAgent, ProAgent, and ConAgent.

    Subclasses must declare their `role` as a class attribute and implement
    `_build_system_prompt()`.  Everything else — API calls, tool handling,
    JSON parsing — lives here.
    """

    role: Role  # set by each subclass

    def __init__(
        self,
        config: AgentModelConfig,
        skill_registry: SkillRegistry,
        gatekeeper: Gatekeeper,
    ) -> None:
        self._config = config
        self._gatekeeper = gatekeeper
        self._skills: list[SkillDefinition] = skill_registry.get_for_agent(self.role.value)
        self._system_prompt: str = self._build_system_prompt()
        self._history: list[dict] = []

    # ── abstract interface ─────────────────────────────────────────────────────

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """Compose the system prompt from role identity and injected skills."""

    # ── LLM call with tool-use loop ────────────────────────────────────────────

    def _tools_for_role(self) -> list[dict] | None:
        """Override in Pro/Con to enable evidence retrieval. Judge returns None."""
        return None

    def _call_llm(self, user_message: str) -> str:
        """
        Send `user_message`, resolve any tool calls, and return the final text.

        The tool-use loop works as follows:
          1. Send the current history + new user message.
          2. If the LLM returns stop_reason == "tool_use", execute the tool.
          3. Append both the assistant's tool-use block and our tool_result.
          4. Repeat until the LLM produces a text response.
        """
        self._history.append({"role": "user", "content": user_message})
        tools = self._tools_for_role()

        response = self._gatekeeper.call_llm(
            messages=self._history,
            system=self._system_prompt,
            model=self._config.model,
            max_tokens=self._config.max_tokens,
            tools=tools,
        )

        while response.stop_reason == "tool_use":
            tool_block = next(b for b in response.content if b.type == "tool_use")
            search_results = self._gatekeeper.call_search(tool_block.input["query"])

            self._history.append({"role": "assistant", "content": response.content})
            self._history.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": json.dumps(search_results),
                }],
            })

            response = self._gatekeeper.call_llm(
                messages=self._history,
                system=self._system_prompt,
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                tools=tools,
            )

        text = next(b.text for b in response.content if b.type == "text")
        self._history.append({"role": "assistant", "content": text})
        return text

    # ── JSON parsing ───────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json(text: str) -> dict:
        """
        Extract a JSON object from the LLM response.
        Tries three approaches in order:
          1. Direct parse (the happy path — json_protocol_skill usually ensures this).
          2. Strip a markdown ```json ... ``` fence.
          3. Regex to find the first {...} block in the text.
        Falls back to wrapping the raw text in a minimal envelope if all else fails,
        so the debate is never interrupted by a formatting quirk.
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

    # ── Evidence extraction ────────────────────────────────────────────────────

    @staticmethod
    def _extract_evidence(raw_list: list[dict]) -> list[Evidence]:
        """Convert raw JSON evidence entries into typed Evidence objects."""
        result = []
        for entry in raw_list:
            if not entry.get("quote"):
                continue
            result.append(Evidence(
                source=entry.get("source", "Unknown"),
                quote=entry["quote"],
                url=entry.get("url"),
            ))
        return result

    # ── Skill helpers ──────────────────────────────────────────────────────────

    def _skill_prompt_blocks(self) -> str:
        return "\n\n".join(s.as_system_prompt_block() for s in self._skills)

    def _build_message(
        self,
        data: dict,
        round_num: int,
        message_type: MessageType,
        raw_fallback: str,
    ) -> DebateMessage:
        return DebateMessage(
            round=round_num,
            role=self.role,
            message_type=message_type,
            content=data.get("content") or raw_fallback,
            evidence=self._extract_evidence(data.get("evidence", [])),
        )
