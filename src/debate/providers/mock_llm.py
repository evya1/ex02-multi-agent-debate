"""
MockLLMProvider — deterministic fake for offline tests.

Returns pre-canned JSON so tests never make real API calls.
The response rotates through a short set of fixtures so different
test assertions can be satisfied without complex mock setup.
"""

from __future__ import annotations

import json

from debate.providers.base import AbstractLLMProvider, LLMResponse

_ARGUMENT_JSON = json.dumps(
    {
        "message_type": "argument",
        "role": "pro",
        "round": 1,
        "content": "AI will cure diseases and advance human potential.",
        "evidence": [{"source": "Mock Source", "quote": "AI cures diseases.", "url": None}],
    }
)

_REBUTTAL_JSON = json.dumps(
    {
        "message_type": "rebuttal",
        "role": "con",
        "round": 2,
        "content": "AI poses significant ethical and safety risks.",
        "evidence": [{"source": "Mock Source", "quote": "AI has risks.", "url": None}],
    }
)

_MODERATION_JSON = json.dumps(
    {
        "message_type": "moderation",
        "role": "judge",
        "round": 1,
        "content": "Welcome to the debate. Round 1 begins now.",
        "evidence": [],
    }
)

_VERDICT_JSON = json.dumps(
    {
        "message_type": "verdict",
        "role": "judge",
        "round": 5,
        "content": "PRO presented the stronger case.",
        "evidence": [],
        "winner": "pro",
        "total_pro_score": 32.0,
        "total_con_score": 28.0,
        "round_scores": [],
        "reasoning": "Pro had better evidence and clearer arguments.",
        "key_turning_point": "Round 1 medical AI argument.",
    }
)

_RESPONSES = [_MODERATION_JSON, _ARGUMENT_JSON, _REBUTTAL_JSON]


class MockLLMProvider(AbstractLLMProvider):
    """
    Offline-safe LLM provider for tests.

    Each call returns the next response from the rotation.
    Call `reset()` between tests for deterministic ordering.
    """

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = responses or _RESPONSES
        self._index = 0
        self.calls: list[dict] = []  # record of every call for assertions

    def name(self) -> str:
        return "mock"

    def reset(self) -> None:
        self._index = 0
        self.calls.clear()

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict],
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "model": model,
                "system_length": len(system),
                "num_messages": len(messages),
                "tools": bool(tools),
            }
        )
        text = self._responses[self._index % len(self._responses)]
        self._index += 1
        return LLMResponse(
            content=text,
            stop_reason="end_turn",
            tool_calls=[],
            input_tokens=10,
            output_tokens=50,
        )


class VerdictMockLLMProvider(MockLLMProvider):
    """
    Variant that always returns a valid verdict JSON.
    Use this for JudgeAgent._render_verdict() tests.
    """

    def complete(self, *, model, system, messages, max_tokens, tools=None):
        self.calls.append({})
        self._index += 1
        return LLMResponse(
            content=_VERDICT_JSON,
            stop_reason="end_turn",
            tool_calls=[],
            input_tokens=20,
            output_tokens=100,
        )
