"""
BaseAgent — shared LLM-call mechanics for all three debate participants.

Design principles:
  - Agents never call providers directly; everything flows through Gatekeeper.
  - Tool-use (evidence retrieval) is handled via tool_loop.run_tool_loop() so
    Pro and Con don't need to duplicate the response-loop logic.
  - JSON parsing is centralised in agents.parsing with a layered fallback
    strategy so a slightly malformed response doesn't crash the debate.
  - Each agent maintains its own conversation history.
  - LLMResponse (provider-agnostic) is used throughout; no direct SDK types.

Parsing helpers (_parse_json, _extract_evidence) are exposed as static methods
for backward compatibility with tests that call BaseAgent._parse_json(...).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from debate.agents.parsing import extract_evidence, parse_json
from debate.agents.tool_loop import EVIDENCE_TOOL, run_tool_loop
from debate.gatekeeper import Gatekeeper
from debate.models.config import AgentModelConfig
from debate.models.message import DebateMessage, Evidence, MessageType, Role
from debate.models.skill import SkillDefinition
from debate.skills.registry import SkillRegistry


class BaseAgent(ABC):
    """
    Abstract base for JudgeAgent, ProAgent, and ConAgent.

    Subclasses must declare their `role` as a class attribute and implement
    `_build_system_prompt()`.  Everything else — API calls, tool handling,
    JSON parsing — lives here or in the dedicated sub-modules.
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

    # ── LLM call ───────────────────────────────────────────────────────────────

    def _tools_for_role(self) -> list[dict] | None:
        """Override in Pro/Con to enable evidence retrieval. Judge returns None."""
        return None

    def _call_llm(self, user_message: str) -> str:
        """
        Append user_message to history, run the tool-use loop, and return
        the final text.  History is updated in-place by run_tool_loop().
        """
        self._history.append({"role": "user", "content": user_message})
        text = run_tool_loop(
            gatekeeper=self._gatekeeper,
            history=self._history,
            system_prompt=self._system_prompt,
            model=self._config.model,
            max_tokens=self._config.max_tokens,
            tools=self._tools_for_role(),
        )
        self._history.append({"role": "assistant", "content": text})
        return text

    # ── JSON parsing (static wrappers for backward compat) ────────────────────

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Wrapper around agents.parsing.parse_json for backward compatibility."""
        return parse_json(text)

    @staticmethod
    def _extract_evidence(raw_list: list[dict]) -> list[Evidence]:
        """Wrapper around agents.parsing.extract_evidence for backward compatibility."""
        return extract_evidence(raw_list)

    # ── Skill and message helpers ──────────────────────────────────────────────

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
            evidence=extract_evidence(data.get("evidence", [])),
        )


# Re-export so importers can do: from debate.agents.base import EVIDENCE_TOOL
__all__ = ["BaseAgent", "EVIDENCE_TOOL"]
