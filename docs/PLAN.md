# Implementation Plan — AI Agent Debate System

> Strict granular phases. Each phase = one git commit.
> Existing code is never deleted; phases build on top of each other.

---

## Phase 01 — Project Skeleton

**Goal:** Establish the repository layout, dependency manifest, and configuration files.

Deliverables:
- `pyproject.toml` (uv, ruff, pytest config)
- `.gitignore`, `.env.example`
- `config/debate.yaml`, `config/models.yaml`, `config/skills.yaml`
- Empty `src/debate/__init__.py`, `tests/` directory
- `README.md` stub

Commit message: `Phase 01: project skeleton, config files, toolchain`

---

## Phase 02 — Core Data Models

**Goal:** Define all Pydantic v2 models used across the system.

Deliverables:
- `src/debate/models/message.py` — `Role`, `MessageType`, `Evidence`, `DebateMessage`
- `src/debate/models/verdict.py` — `Verdict`, `RoundScore` (no-tie validator)
- `src/debate/models/skill.py` — `SkillDefinition`
- `src/debate/models/config.py` — `AppConfig` + all nested settings
- `tests/test_models.py`

Commit message: `Phase 02: core Pydantic models (message, verdict, skill, config)`

---

## Phase 03 — Skills System

**Goal:** Implement the 7 mandatory skills and the SkillRegistry.

Deliverables:
- `src/debate/skills/registry.py` — `SkillRegistry`
- `src/debate/skills/definitions.py` — all 7 `SkillDefinition` objects + `build_registry()`
- `tests/test_skills.py`

Commit message: `Phase 03: skills registry and 7 skill definitions`

---

## Phase 04 — Agent Base + Pro/Con Agents

**Goal:** Implement shared LLM-call logic and the two child agents.

Deliverables:
- `src/debate/agents/base.py` — `BaseAgent` ABC (JSON parse, tool_use loop)
- `src/debate/agents/pro.py` — `ProAgent`
- `src/debate/agents/con.py` — `ConAgent`

Commit message: `Phase 04: BaseAgent, ProAgent, ConAgent`

---

## Phase 05 — Judge Agent (Parent Orchestration)

**Goal:** Implement the parent JudgeAgent that spawns and routes between Pro and Con.

Deliverables:
- `src/debate/agents/judge.py` — `JudgeAgent`
  - `run_debate()`, `_introduce_round()`, `_summarise_round()`, `_render_verdict()`
  - `_build_pro_context()`, `_build_con_context()` (static)

Commit message: `Phase 05: JudgeAgent — parent orchestration and round routing`

---

## Phase 06 — Gatekeeper (Budget + Rate + Timeout)

**Goal:** Single gateway for all external calls; enforce budget, rate, and timeout.

Deliverables:
- `src/debate/gatekeeper.py` — `Gatekeeper`, `BudgetExceededError`
- `tests/test_gatekeeper.py`

Commit message: `Phase 06: Gatekeeper — budget, rate-limit, timeout, retry`

---

## Phase 07 — Provider Abstraction Layer

**Goal:** Decouple the system from Anthropic/DuckDuckGo; make it LLM-provider-agnostic.

Deliverables:
- `src/debate/providers/base.py` — `AbstractLLMProvider`, `AbstractSearchProvider` (ABCs)
- `src/debate/providers/anthropic_provider.py` — Anthropic implementation
- `src/debate/providers/mock_llm.py` — deterministic mock for tests
- `src/debate/providers/mock_search.py` — deterministic mock for tests
- `config/provider_config.json` — selects which provider to load at runtime
- `config/rate_limits.json` — rate-limit parameters (separate from YAML)
- Refactor `Gatekeeper` to accept a provider instance (no direct `anthropic` import)

Commit message: `Phase 07: provider abstraction layer (LLM + search, mock providers)`

---

## Phase 08 — Enhanced Message Schema + skill_id_used

**Goal:** Every `DebateMessage` must record which skill produced it.

Deliverables:
- Add `skill_id_used: str` field to `DebateMessage`
- Add `debate_id: str`, `ping_index: int | None` fields
- Update all agents to populate `skill_id_used` on every message they emit
- Update tests

Commit message: `Phase 08: add skill_id_used + debate_id to DebateMessage`

---

## Phase 09 — Per-Skill Filesystem Directories

**Goal:** Each skill lives in its own directory with machine and human docs.

Deliverables:
- `skills/<skill_name>/SKILL.md` — machine-readable metadata (name, intended_agents, trigger, schemas)
- `skills/<skill_name>/prompt.md` — human-readable skill prompt / instructions
- One directory per skill (7 total)
- Skill loader reads from filesystem; `build_registry()` uses it

Commit message: `Phase 09: per-skill filesystem dirs (SKILL.md + prompt.md × 7)`

---

## Phase 10 — Skill Router

**Goal:** Map agent actions to the correct skill at runtime.

Deliverables:
- `src/debate/skills/router.py` — `SkillRouter`
  - `route(agent_role, round_num, has_opponent_msg) -> SkillDefinition`
  - Logic: round 1 → argument skill; round 2+ → rebuttal skill; judge → moderation/verdict
- Tests for all routing branches

Commit message: `Phase 10: SkillRouter — maps agent action to skill at runtime`

---

## Phase 11 — SDK Layer

**Goal:** Expose a clean Python API for programmatic use (no CLI required).

Deliverables:
- `src/debate/sdk/sdk.py` — `AgentDebateSDK` class:
  - `run_debate(topic, rounds, mock) -> (transcript, verdict)`
  - `load_transcript(path) -> list[DebateMessage]`
  - `validate_config(path) -> bool`
  - `list_skills() -> list[SkillDefinition]`
  - `validate_skills() -> dict[str, bool]`
- Tests in `tests/integration/test_sdk.py`

Commit message: `Phase 11: SDK layer (run_debate, load_transcript, validate_config, list/validate_skills)`

---

## Phase 12 — CLI Entry Point + Subcommands

**Goal:** Install `agent-debate` as a console script with full subcommand support.

Deliverables:
- `src/debate/cli/entry.py` — `main()` entry point
  - `agent-debate run [--topic "..." --rounds N --mock]`
  - `agent-debate skills list`
  - `agent-debate skills validate`
  - `agent-debate --mock --topic "..." --pings N` (ping mode)
- Register `agent-debate = debate.cli.entry:main` in `pyproject.toml`
- Update README with usage examples

Commit message: `Phase 12: CLI entry point — agent-debate with skills subcommands`

---

## Phase 13 — Test Reorganisation

**Goal:** Split tests into unit/ and integration/ directories.

Deliverables:
- `tests/unit/` — fast, offline, no real providers
  - `test_models.py`, `test_skills.py`, `test_agents.py`, `test_gatekeeper.py`
  - `test_skill_router.py`
- `tests/integration/` — may use mock providers but exercise full pipelines
  - `test_runner.py`, `test_sdk.py`
- Update `pytest.ini` / `pyproject.toml` testpaths

Commit message: `Phase 13: reorganise tests into unit/ and integration/`

---

## Summary Table

| Phase | Scope | Commit label |
|-------|-------|--------------|
| 01 | Project skeleton | `Phase 01: project skeleton` |
| 02 | Core data models | `Phase 02: Pydantic models` |
| 03 | Skills system | `Phase 03: skills registry` |
| 04 | BaseAgent + Pro/Con | `Phase 04: BaseAgent, ProAgent, ConAgent` |
| 05 | JudgeAgent | `Phase 05: JudgeAgent` |
| 06 | Gatekeeper | `Phase 06: Gatekeeper` |
| 07 | Provider abstraction | `Phase 07: provider abstraction` |
| 08 | skill_id_used | `Phase 08: skill_id_used in messages` |
| 09 | Skill filesystem dirs | `Phase 09: per-skill filesystem dirs` |
| 10 | Skill router | `Phase 10: SkillRouter` |
| 11 | SDK layer | `Phase 11: SDK layer` |
| 12 | CLI entry point | `Phase 12: CLI entry point` |
| 13 | Test reorganisation | `Phase 13: test reorganisation` |
