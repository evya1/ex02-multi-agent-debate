"""
LLM tool-use loop machinery for debater agents.

Contains the EVIDENCE_TOOL schema and the run_tool_loop() function that
drives the multi-turn exchange when an agent calls retrieve_evidence.
Extracted from BaseAgent so the tool-call plumbing is isolated from the
agent class hierarchy.
"""

from __future__ import annotations

import json
import logging

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


def run_tool_loop(
    gatekeeper,
    history: list[dict],
    system_prompt: str,
    model: str,
    max_tokens: int,
    tools: list[dict] | None,
) -> str:
    """
    Execute one LLM call, resolve any tool calls, and return the final text.

    1. Sends the current history to the LLM.
    2. If the response contains tool_calls, executes each tool via gatekeeper.
    3. Appends the assistant content and tool_result to history.
    4. Repeats until the response has no tool_calls (the final text turn).

    History management for tool-use:
      - When tool_calls are present, the raw provider response is echoed back
        as the assistant content so the provider can reconstruct full context
        (e.g. Anthropic's content-block format).
      - If raw is None (e.g. mock provider), the text content string is used.
    """
    from debate.providers.base import LLMResponse  # local import avoids circular

    response: LLMResponse = gatekeeper.call_llm(
        messages=history,
        system=system_prompt,
        model=model,
        max_tokens=max_tokens,
        tools=tools,
    )

    while response.tool_calls:
        tool_call = response.tool_calls[0]
        search_results = gatekeeper.call_search(tool_call.input["query"])

        assistant_content = (
            response.raw.content if response.raw is not None else response.content
        )
        history.append({"role": "assistant", "content": assistant_content})
        history.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": json.dumps(search_results),
                    }
                ],
            }
        )

        response = gatekeeper.call_llm(
            messages=history,
            system=system_prompt,
            model=model,
            max_tokens=max_tokens,
            tools=tools,
        )

    return response.content
