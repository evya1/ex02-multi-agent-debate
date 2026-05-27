"""
Abstract base classes for LLM and search providers.

Why abstract providers?
  The core debate logic must not depend on Anthropic specifically.
  Swapping to OpenAI, Gemini, or a local model requires only a new
  concrete class — nothing else in the system changes.

Provider contract:
  - LLMProvider.complete() receives provider-agnostic dicts and returns
    a LLMResponse (also provider-agnostic).
  - SearchProvider.search() returns a list of plain Evidence-shaped dicts.

Tool-use (function calling) is expressed as a list of ToolDefinition
dicts in the same shape Claude's API expects.  Providers that do not
support tool-use should raise NotImplementedError.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# ── Shared data structures ─────────────────────────────────────────────────────


@dataclass
class ToolCall:
    """A single tool invocation returned by the LLM."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    """Provider-agnostic response envelope."""

    content: str  # final text content (may be empty if tool_use)
    stop_reason: str  # "end_turn" | "tool_use" | "max_tokens" | ...
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Any = None  # original provider response (for debugging)


@dataclass
class SearchResult:
    """One result from a web-search provider."""

    source: str
    quote: str
    url: str | None = None


# ── Abstract providers ─────────────────────────────────────────────────────────


class AbstractLLMProvider(ABC):
    """
    Contract every LLM back-end must fulfil.

    Implementors:
      - anthropic_provider.AnthropicProvider
      - mock_llm.MockLLMProvider
    """

    @abstractmethod
    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict],
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """
        Send a chat-completion request and return a provider-agnostic response.

        Args:
            model:      The model identifier (provider-specific string).
            system:     System-prompt text.
            messages:   List of {"role": ..., "content": ...} dicts.
            max_tokens: Hard ceiling on output tokens.
            tools:      Optional list of tool schemas (Claude tool-use format).
        """

    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g. 'anthropic', 'mock')."""


class AbstractSearchProvider(ABC):
    """
    Contract every search back-end must fulfil.

    Implementors:
      - duckduckgo_provider.DuckDuckGoProvider  (implicit in AnthropicProvider)
      - mock_search.MockSearchProvider
    """

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Run a web search and return up to max_results results."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g. 'duckduckgo', 'mock')."""
