"""Tests for the skill definitions and registry."""
from __future__ import annotations

import pytest

from debate.models.skill import SkillDefinition
from debate.skills.definitions import ALL_SKILLS, build_registry
from debate.skills.registry import SkillRegistry


class TestSkillDefinition:
    def test_as_system_prompt_block_contains_name_and_trigger(self):
        skill = SkillDefinition(
            name="test_skill",
            description="A test.",
            intended_agents=["pro"],
            trigger="when testing",
            instructions="Do the thing.",
            input_schema={},
            output_schema={},
        )
        block = skill.as_system_prompt_block()
        assert "test_skill" in block
        assert "when testing" in block
        assert "Do the thing." in block


class TestSkillRegistry:
    def test_register_and_get(self):
        registry = SkillRegistry()
        skill = SkillDefinition(
            name="s1", description="x", intended_agents=["judge"],
            trigger="t", instructions="i", input_schema={}, output_schema={},
        )
        registry.register(skill)
        assert registry.get("s1") is skill

    def test_get_missing_raises_key_error(self):
        registry = SkillRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_get_for_agent_filters_correctly(self):
        registry = SkillRegistry()
        for role in ["judge", "pro", "con"]:
            registry.register(SkillDefinition(
                name=f"skill_{role}", description="", intended_agents=[role],
                trigger="", instructions="", input_schema={}, output_schema={},
            ))
        shared = SkillDefinition(
            name="shared", description="", intended_agents=["pro", "con"],
            trigger="", instructions="", input_schema={}, output_schema={},
        )
        registry.register(shared)

        pro_skills = registry.get_for_agent("pro")
        names = {s.name for s in pro_skills}
        assert "skill_pro" in names
        assert "shared" in names
        assert "skill_judge" not in names

    def test_len(self):
        registry = SkillRegistry()
        assert len(registry) == 0
        registry.register(SkillDefinition(
            name="x", description="", intended_agents=[], trigger="",
            instructions="", input_schema={}, output_schema={},
        ))
        assert len(registry) == 1


class TestAllSkills:
    def test_seven_skills_defined(self):
        assert len(ALL_SKILLS) == 7

    def test_build_registry_loads_all(self):
        registry = build_registry()
        assert len(registry) == 7

    def test_required_skill_names_present(self):
        registry = build_registry()
        required = {
            "judge_moderation_skill",
            "pro_argument_skill",
            "con_argument_skill",
            "evidence_retrieval_skill",
            "rebuttal_skill",
            "verdict_skill",
            "json_protocol_skill",
        }
        loaded = {s.name for s in registry.all()}
        assert required == loaded

    @pytest.mark.parametrize("role,expected_count", [
        ("judge", 3),  # moderation, verdict, json_protocol
        ("pro", 4),    # pro_argument, evidence, rebuttal, json_protocol
        ("con", 4),    # con_argument, evidence, rebuttal, json_protocol
    ])
    def test_skill_counts_per_agent(self, role, expected_count):
        registry = build_registry()
        assert len(registry.get_for_agent(role)) == expected_count

    def test_every_skill_has_non_empty_instructions(self):
        for skill in ALL_SKILLS:
            assert skill.instructions.strip(), f"Skill {skill.name} has empty instructions"

    def test_json_protocol_skill_targets_all_agents(self):
        registry = build_registry()
        jp = registry.get("json_protocol_skill")
        assert set(jp.intended_agents) == {"judge", "pro", "con"}
