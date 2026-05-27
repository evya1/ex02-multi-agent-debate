"""
ConAgent — argues against the debate topic.

Owned skills (injected into system prompt):
  - con_argument_skill      constructs against arguments
  - evidence_retrieval_skill  searches the web for supporting evidence
  - rebuttal_skill          directly counters Pro's most recent argument
  - json_protocol_skill     enforces JSON-only output

Mirror of ProAgent; only the role identity and system-prompt flavour differ.
"""

from __future__ import annotations

from debate.agents.base import EVIDENCE_TOOL, BaseAgent
from debate.gatekeeper import Gatekeeper
from debate.models.config import AgentModelConfig
from debate.models.message import DebateMessage, MessageType, Role
from debate.skills.registry import SkillRegistry


class ConAgent(BaseAgent):
    role = Role.CON

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
            "You are the CON debater in a structured AI debate.\n"
            "Your mission: argue persuasively AGAINST the topic.\n"
            "Challenge the PRO's strongest points every round.\n\n" + self._skill_prompt_blocks()
        )

    def generate_argument(
        self, context: str, round_num: int, *, debate_id: str = ""
    ) -> DebateMessage:
        """
        Produce an opening argument (round 1) or a rebuttal (rounds 2+).
        `context` is the Judge's routing message, which always includes the Pro
        side's argument that Con must respond to.
        `debate_id` tags the message to its parent session.
        """
        message_type = MessageType.ARGUMENT if round_num == 1 else MessageType.REBUTTAL
        skill_id = "con_argument_skill" if round_num == 1 else "rebuttal_skill"
        prompt = self._compose_prompt(context, round_num, message_type)
        raw = self._call_llm(prompt)
        data = self._parse_json(raw)
        msg = self._build_message(data, round_num, message_type, raw)
        msg.skill_id_used = skill_id
        msg.debate_id = debate_id
        return msg

    def _compose_prompt(self, context: str, round_num: int, msg_type: MessageType) -> str:
        if msg_type == MessageType.ARGUMENT:
            return (
                f"Round {round_num}: present your opening CON argument.\n\n"
                f"PRO has just argued:\n{context}"
            )
        return (
            f"Round {round_num}: the PRO side has argued. Rebut them, "
            f"then reinforce your CON position with fresh evidence.\n\n"
            f"Context from the judge (includes Pro's argument):\n{context}"
        )
