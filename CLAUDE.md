# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install all dependencies (requires uv)
uv sync --all-extras

# Interactive debate CLI (Rich menu)
uv run python main.py

# Run debate directly (no menu, uses config/debate.yaml)
uv run python main.py --run

# agent-debate console script (registered after uv sync)
agent-debate run --mock --topic "AI will help humanity" --rounds 3
agent-debate skills list
agent-debate skills validate
agent-debate --mock --topic "AI" --pings 2   # offline smoke test

# Python SDK (no CLI)
python -c "
from debate.sdk import AgentDebateSDK
sdk = AgentDebateSDK(use_mock=True)
transcript, verdict = sdk.run_debate('AI is beneficial', rounds=1)
print(verdict.summary())
"

# Run all tests (no real API calls needed)
uv run pytest

# Unit tests only (fast, offline)
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v

# Single test file
uv run pytest tests/unit/test_agents.py -v

# Lint
uv run ruff check src tests

# Auto-fix + format
uv run ruff check --fix src tests && uv run ruff format src tests
```

## Architecture

Three-agent hierarchy: **JudgeAgent** (parent) spawns **ProAgent** and **ConAgent** (children). All communication is routed exclusively through the Judge — child agents never hold a reference to each other.

```
CLI / SDK  (main.py  |  agent-debate  |  AgentDebateSDK)
  └── DebateRunner
        └── JudgeAgent  (parent, spawns children)
              ├── ProAgent   (child, read-only view of debate)
              └── ConAgent   (child, read-only view of debate)

Every external call ──► Gatekeeper (budget + rate + timeout)
                              │
                     AbstractLLMProvider   AbstractSearchProvider
                     (AnthropicProvider)   (DuckDuckGoSearchProvider)
                     (MockLLMProvider)     (MockSearchProvider)
                              │
                       Watchdog thread (stall detection)
```

### Provider Abstraction (Phase 07)

The system is **LLM-provider-agnostic**. `Gatekeeper` accepts any
`AbstractLLMProvider` / `AbstractSearchProvider` implementation:

```python
# Real providers (needs ANTHROPIC_API_KEY)
runner = DebateRunner(config)

# Mock providers (no key, offline)
runner = DebateRunner(config, use_mock=True)

# Explicit injection
from debate.providers.mock_llm import MockLLMProvider
from debate.providers.mock_search import MockSearchProvider
runner = DebateRunner(config, llm_provider=MockLLMProvider(), search_provider=MockSearchProvider())
```

Provider selection at runtime is controlled by `config/provider_config.json`.

### Data Flow per Round

```
Judge._introduce_round()  → LLM call  (skill: judge_moderation_skill)
Pro.generate_argument()   → LLM call  (skill: pro_argument_skill / rebuttal_skill)
  ↳ may call retrieve_evidence tool → SearchProvider
  Judge routes Pro msg to Con
Con.generate_argument()   → LLM call  (skill: con_argument_skill / rebuttal_skill)
  ↳ may call retrieve_evidence tool → SearchProvider
  Judge routes Con msg to Pro
Judge._summarise_round()  → LLM call  (skill: judge_moderation_skill)
  ... repeat for N rounds ...
Judge._render_verdict()   → LLM call  (skill: verdict_skill)  → Verdict (no ties)
```

### Skills System

`SkillDefinition` objects (in `src/debate/skills/definitions.py`) are loaded into
`SkillRegistry` at startup. Each agent receives its required skills; their
`instructions` text is injected into the agent's system prompt.

Every `DebateMessage` records `skill_id_used` — which skill produced it.

**SkillRouter** (`src/debate/skills/router.py`) maps `(role, round, is_verdict)` to
the correct `SkillDefinition` at runtime.

**Per-skill filesystem docs** live in `skills/<skill_name>/SKILL.md` + `prompt.md`.

| Skill | Owner(s) |
|-------|----------|
| `judge_moderation_skill` | judge |
| `verdict_skill` | judge |
| `pro_argument_skill` | pro |
| `con_argument_skill` | con |
| `evidence_retrieval_skill` | pro, con |
| `rebuttal_skill` | pro, con |
| `json_protocol_skill` | all |

### Key Source Files

| File | Role |
|------|------|
| `src/debate/runner.py` | Top-level facade — wires providers, watchdog, logger |
| `src/debate/agents/judge.py` | Parent agent — routing, moderation, verdict |
| `src/debate/agents/base.py` | Shared LLM-call loop + JSON-parse (provider-agnostic) |
| `src/debate/providers/base.py` | `AbstractLLMProvider` / `AbstractSearchProvider` ABCs |
| `src/debate/providers/factory.py` | `build_providers(use_mock=)` factory |
| `src/debate/skills/definitions.py` | All 7 `SkillDefinition` instances |
| `src/debate/skills/router.py` | Maps agent action → skill at runtime |
| `src/debate/sdk/sdk.py` | `AgentDebateSDK` — public Python API |
| `src/debate/cli/entry.py` | `agent-debate` console script entry point |
| `src/debate/gatekeeper.py` | Single gateway (budget + rate + timeout, provider-agnostic) |
| `src/debate/watchdog.py` | Daemon thread monitoring for stalled calls |
| `src/debate/logger.py` | JSONL structured-log writer |
| `config/debate.yaml` | Topic, rounds, budget, timeouts |
| `config/models.yaml` | Model name + token limits per agent |
| `config/provider_config.json` | Which LLM/search provider to use at runtime |
| `config/rate_limits.json` | Rate-limit and retry parameters |

### Message Protocol

All inter-agent messages are `DebateMessage` Pydantic models serialised to JSON.
Key fields added in Phase 08:
- `skill_id_used` — which skill produced this message (audit trail)
- `debate_id` — UUID tying all messages in one session together
- `ping_index` — set in ping/mock mode only

The `json_protocol_skill` instructs every agent to return raw JSON only.
`BaseAgent._parse_json()` handles fallback extraction (markdown fences, regex).

### Configuration

`AppConfig` is loaded from `config/debate.yaml` + `config/models.yaml` via
`AppConfig.from_yaml_files()`. Override debate parameters with env vars:

```
ANTHROPIC_API_KEY=      # required for real provider
DEBATE_TOPIC=           # optional — overrides config/debate.yaml
DEBATE_ROUNDS=          # optional — overrides config/debate.yaml (default: 5)
```

### Test Layout

```
tests/
  unit/        ← fast, offline (no providers)
    test_models.py, test_skills.py, test_agents.py,
    test_gatekeeper.py, test_skill_router.py, test_skill_dirs.py
  integration/ ← exercises full pipeline with mock providers
    test_runner.py, test_sdk.py
  (root-level copies kept for backward compat)
```

Run unit tests only: `uv run pytest tests/unit/`
Run integration: `uv run pytest tests/integration/`
