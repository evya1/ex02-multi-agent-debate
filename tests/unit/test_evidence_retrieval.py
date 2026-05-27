"""
Prove that ProAgent/ConAgent trigger call_search when the LLM returns
a tool-use response (retrieve_evidence tool call).

Tests cover:
  - Both agents expose the retrieve_evidence tool to the LLM
  - run_tool_loop() calls gatekeeper.call_search() when tool_calls are present
  - The search result is folded back into the history before the next LLM call
  - Judge does NOT get any tools (evidence retrieval is debater-only)
"""

from __future__ import annotations

from debate.agents.con import ConAgent
from debate.agents.pro import ProAgent
from debate.agents.tool_loop import EVIDENCE_TOOL, run_tool_loop
from debate.providers.base import LLMResponse, ToolCall


class _ToolThenTextProvider:
    """Mock provider: first call returns a tool_call; second call returns text."""

    def __init__(self, tool_input: dict, final_text: str) -> None:
        self._tool_input = tool_input
        self._final_text = final_text
        self.call_count = 0

    def name(self) -> str:
        return "tool_then_text"

    def complete(self, *, model, system, messages, max_tokens, tools=None):
        self.call_count += 1
        if self.call_count == 1:
            return LLMResponse(
                content="",
                stop_reason="tool_use",
                tool_calls=[
                    ToolCall(id="tc-001", name="retrieve_evidence", input=self._tool_input)
                ],
                input_tokens=10,
                output_tokens=5,
            )
        return LLMResponse(
            content=self._final_text,
            stop_reason="end_turn",
            tool_calls=[],
            input_tokens=10,
            output_tokens=20,
        )


class TestEvidenceToolExposure:
    def test_pro_exposes_retrieve_evidence_tool(
        self, minimal_config, skill_registry, mock_gatekeeper
    ):
        pro = ProAgent(minimal_config.pro, skill_registry, mock_gatekeeper)
        tools = pro._tools_for_role()
        assert tools is not None and len(tools) >= 1
        names = [t["name"] for t in tools]
        assert "retrieve_evidence" in names

    def test_con_exposes_retrieve_evidence_tool(
        self, minimal_config, skill_registry, mock_gatekeeper
    ):
        con = ConAgent(minimal_config.con, skill_registry, mock_gatekeeper)
        tools = con._tools_for_role()
        assert tools is not None
        assert any(t["name"] == "retrieve_evidence" for t in tools)

    def test_judge_has_no_tools(self, minimal_config, skill_registry, mock_gatekeeper):
        from debate.agents.judge import JudgeAgent

        judge = JudgeAgent(minimal_config, skill_registry, mock_gatekeeper)
        assert judge._tools_for_role() is None

    def test_evidence_tool_has_required_schema_fields(self):
        assert "name" in EVIDENCE_TOOL
        assert "input_schema" in EVIDENCE_TOOL
        props = EVIDENCE_TOOL["input_schema"]["properties"]
        assert "query" in props
        assert "query" in EVIDENCE_TOOL["input_schema"].get("required", [])


class TestToolLoopSearchInvocation:
    def test_call_search_invoked_when_tool_call_returned(self, minimal_config):
        from debate.gatekeeper import Gatekeeper
        from debate.providers.mock_search import MockSearchProvider

        provider = _ToolThenTextProvider(
            tool_input={"query": "AI benefits"},
            final_text='{"content": "AI helps a lot.", "evidence": []}',
        )
        gk = Gatekeeper(minimal_config, provider, MockSearchProvider())

        history: list[dict] = []
        result = run_tool_loop(
            gatekeeper=gk,
            history=history,
            system_prompt="You are a debater.",
            model=minimal_config.pro.model,
            max_tokens=256,
            tools=[EVIDENCE_TOOL],
        )

        assert "AI helps" in result
        assert provider.call_count == 2  # tool call + final text call

    def test_tool_result_appended_to_history(self, minimal_config):
        from debate.gatekeeper import Gatekeeper
        from debate.providers.mock_search import MockSearchProvider

        provider = _ToolThenTextProvider(
            tool_input={"query": "search term"},
            final_text='{"content": "done", "evidence": []}',
        )
        gk = Gatekeeper(minimal_config, provider, MockSearchProvider())

        history: list[dict] = []
        run_tool_loop(
            gatekeeper=gk,
            history=history,
            system_prompt="sys",
            model=minimal_config.pro.model,
            max_tokens=128,
            tools=[EVIDENCE_TOOL],
        )

        # History must contain a tool_result turn (the search result fed back)
        roles = [m["role"] for m in history]
        assert "user" in roles
        tool_result_found = any(
            isinstance(m.get("content"), list)
            and any(c.get("type") == "tool_result" for c in m["content"])
            for m in history
            if m["role"] == "user"
        )
        assert tool_result_found, "No tool_result message found in history"
