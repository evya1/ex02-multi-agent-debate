"""
ProAgent — argues in favour of the debate topic.

Owned skills (injected into system prompt):
  - pro_argument_skill      constructs in-favour arguments
  - evidence_retrieval_skill  searches the web for supporting evidence
  - rebuttal_skill          directly counters Con's most recent argument
  - json_protocol_skill     enforces JSON-only output

The Pro agent only receives context from the Judge (round intro + Con's last message).
It never holds a reference to the Con agent.
"""
from __future__ import annotations

from debate.agents.base import EVIDENCE_TOOL, BaseAgent
from debate.gatekeeper import Gatekeeper
from debate.models.config import AgentModelConfig
from debate.models.message import DebateMessage, MessageType, Role
from debate.skills.registry import SkillRegistry


class ProAgent(BaseAgent):
    role = Role.PRO

    def __init__(
        self,
        config: AgentModelConfig,
        skill_registry: SkillRegistry,
        gatekeeper: Gatekeeper,
    ) -> None:
        super().__init__(config, skill_registry, gatekeeper)

    def _tools_for_role(self) -> list[dict]:
        return [EVIDENCE_TOOL]

    def _build_system_prompt(self) -> str:
        return (
            "You are the PRO debater in a structured AI debate.\n"
            "Your mission: argue persuasively IN FAVOUR of the topic.\n"
            "Engage directly with your opponent's arguments every round.\n\n"
            + self._skill_prompt_blocks()
        )

    def generate_argument(self, context: str, round_num: int) -> DebateMessage:
        """
        Produce an opening argument (round 1) or a rebuttal (rounds 2+).
        `context` is the Judge's routing message, which includes the Con side's
        previous argument from round 2 onwards.
        """
        message_type = MessageType.ARGUMENT if round_num == 1 else MessageType.REBUTTAL
        prompt = self._compose_prompt(context, round_num, message_type)
        raw = self._call_llm(prompt)
        data = self._parse_json(raw)
        return self._build_message(data, round_num, message_type, raw)

    def _compose_prompt(self, context: str, round_num: int, msg_type: MessageType) -> str:
        if msg_type == MessageType.ARGUMENT:
            return (
                f"Round {round_num}: present your opening PRO argument.\n\n"
                f"Judge's introduction:\n{context}"
            )
        return (
            f"Round {round_num}: the CON side has argued. Rebut them, "
            f"then reinforce your PRO position with fresh evidence.\n\n"
            f"Context from the judge (includes Con's argument):\n{context}"
        )
