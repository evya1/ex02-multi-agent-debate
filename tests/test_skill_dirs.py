"""
Tests for per-skill filesystem directories.

Phase 09 requirement: every skill has its own directory under skills/
containing SKILL.md (machine metadata) and prompt.md (human prompt).
"""
from __future__ import annotations

from pathlib import Path

import pytest

_SKILLS_ROOT = Path(__file__).parent.parent / "skills"

_EXPECTED_SKILLS = [
    "judge_moderation_skill",
    "pro_argument_skill",
    "con_argument_skill",
    "evidence_retrieval_skill",
    "rebuttal_skill",
    "verdict_skill",
    "json_protocol_skill",
]


@pytest.mark.parametrize("skill_name", _EXPECTED_SKILLS)
def test_skill_directory_exists(skill_name: str) -> None:
    assert (_SKILLS_ROOT / skill_name).is_dir(), (
        f"Missing skill directory: skills/{skill_name}/"
    )


@pytest.mark.parametrize("skill_name", _EXPECTED_SKILLS)
def test_skill_md_exists(skill_name: str) -> None:
    path = _SKILLS_ROOT / skill_name / "SKILL.md"
    assert path.is_file(), f"Missing: skills/{skill_name}/SKILL.md"


@pytest.mark.parametrize("skill_name", _EXPECTED_SKILLS)
def test_prompt_md_exists(skill_name: str) -> None:
    path = _SKILLS_ROOT / skill_name / "prompt.md"
    assert path.is_file(), f"Missing: skills/{skill_name}/prompt.md"


@pytest.mark.parametrize("skill_name", _EXPECTED_SKILLS)
def test_skill_md_contains_name(skill_name: str) -> None:
    content = (_SKILLS_ROOT / skill_name / "SKILL.md").read_text()
    assert skill_name in content, f"SKILL.md for {skill_name} does not mention its own name"


@pytest.mark.parametrize("skill_name", _EXPECTED_SKILLS)
def test_prompt_md_non_empty(skill_name: str) -> None:
    content = (_SKILLS_ROOT / skill_name / "prompt.md").read_text().strip()
    assert len(content) > 20, f"prompt.md for {skill_name} appears empty"
