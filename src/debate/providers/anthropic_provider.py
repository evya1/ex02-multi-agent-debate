"""
Anthropic provider — wraps the official `anthropic` SDK.

This is the only file in the project that imports `anthropic` directly.
Everything else talks to `AbstractLLMProvider` / `AbstractSearchProvider`.

Environment:
    ANTHROPIC_API_KEY  (required — read from environment; never from source)
"""

from __future__ import annotations

import os
from typing import Any

from debate.providers.base import (
    AbstractLLMProvider,
    AbstractSearchProvider,
    LLMResponse,
    SearchResult,
    ToolCall,
)


class AnthropicProvider(AbstractLLMProvider):
    """Concrete LLM provider backed by Anthropic's Messages API."""

    def __init__(self, api_key: str | None = None) -> None:
        import anthropic  # deferred so other providers don't need the package

        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise OSError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example → .env and add your key."
            )
        self._client = anthropic.Anthropic(api_key=key)

    def name(self) -> str:
        return "anthropic"

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict],
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        if tools:
            kwargs["tools"] = tools

        resp = self._client.messages.create(**kwargs)

        # Extract text content (may be empty on tool_use turns)
        text = ""
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))

        return LLMResponse(
            content=text,
            stop_reason=resp.stop_reason or "end_turn",
            tool_calls=tool_calls,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            raw=resp,
        )


class DuckDuckGoSearchProvider(AbstractSearchProvider):
    """Concrete search provider backed by DuckDuckGo (no API key needed)."""

    def name(self) -> str:
        return "duckduckgo"

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        from duckduckgo_search import DDGS  # deferred import

        results: list[SearchResult] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    SearchResult(
                        source=r.get("title", "Unknown"),
                        quote=r.get("body", "")[:400],
                        url=r.get("href"),
                    )
                )
        return results
