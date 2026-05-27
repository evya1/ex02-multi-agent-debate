# AI Agent Debate System
### Exercise 02 — Orchestration of AI

A Python system in which two Claude-powered AI agents debate a topic under
the supervision of a third parent/judge agent. Every argument is backed by
real web evidence; every exchange is routed through the judge; the judge
declares a winner — no ties allowed.

The system is **LLM-provider-agnostic**: swap Anthropic for any provider
by implementing two abstract base classes. A built-in mock provider lets
the full pipeline run **offline without any API key**.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              CLI / agent-debate / AgentDebateSDK             │
└──────────────────────┬───────────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  DebateRunner   │  owns lifecycle of all objects
              └────────┬────────┘
                       │
         ┌─────────────▼──────────────┐
         │        JudgeAgent           │  parent entity
         │   ┌──────────┐ ┌────────┐  │
         │   │ ProAgent │ │ConAgent│  │  child agents (never touch each other)
         │   └──────────┘ └────────┘  │
         └─────────────┬──────────────┘
                       │ all external calls via
              ┌────────▼────────┐
              │   Gatekeeper    │  budget · rate-limit · timeout
              └────────┬────────┘
          ┌────────────┴────────────┐
  AbstractLLMProvider      AbstractSearchProvider
  (AnthropicProvider)      (DuckDuckGoSearchProvider)
  (MockLLMProvider)        (MockSearchProvider)
```

**Skills** are first-class Python objects (`SkillDefinition`) injected into
each agent's system prompt. A `SkillRouter` maps the current round context
to the correct skill at runtime.

| Skill | Owner | Trigger |
|-------|-------|---------|
| `judge_moderation_skill` | Judge | Every round intro / summary |
| `verdict_skill` | Judge | Final verdict rendering |
| `pro_argument_skill` | Pro | Round 1 opening argument |
| `con_argument_skill` | Con | Round 1 opening argument |
| `evidence_retrieval_skill` | Pro, Con | Backing every claim |
| `rebuttal_skill` | Pro, Con | Rounds 2+ |
| `json_protocol_skill` | All | Every single message |

Each skill also has filesystem docs: `skills/<name>/SKILL.md` + `prompt.md`.

---

## Setup

**Requirements:** Python 3.11+, [uv](https://docs.astral.sh/uv/)

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd ex02-multi-agent-debate

# 2. Install all dependencies (including dev tools)
uv sync --all-extras

# 3. Set your Anthropic API key (only needed for real debates)
cp .env.example .env
# Edit .env → ANTHROPIC_API_KEY=sk-ant-...
```

---

## Running the Debate

### Interactive menu

```bash
uv run python main.py
```

Launches a Rich terminal menu: change topic, adjust rounds, start debate,
view previous transcripts.

### Direct SDK mode

```bash
uv run python main.py --run
```

### `agent-debate` console script

```bash
# Real debate (needs ANTHROPIC_API_KEY)
agent-debate run --topic "Nuclear energy is safer than fossil fuels" --rounds 5

# Offline mock debate
agent-debate run --mock --topic "AI will benefit humanity" --rounds 3

# Skills management
agent-debate skills list       # table of all 7 skills
agent-debate skills validate   # verify skill filesystem dirs

# Ping mode — N quick mock rounds (CI / smoke test)
agent-debate --mock --topic "AI" --pings 3
```

### Python SDK

```python
from debate.sdk import AgentDebateSDK

# Offline (no API key)
sdk = AgentDebateSDK(use_mock=True)
transcript, verdict = sdk.run_debate("AI will help humanity", rounds=3)
print(verdict.summary())
# 🏆 PRO wins  (PRO 32.5 — CON 28.0)

# Utility methods
sdk.list_skills()                          # → list[SkillDefinition]
sdk.validate_skills()                      # → dict[str, bool]
sdk.validate_config("config/debate.yaml")  # → bool
sdk.load_transcript("logs/debate.jsonl")   # → list[DebateMessage]
```

### Advanced: explicit provider injection

```python
from debate.runner import DebateRunner
from debate.providers.mock_llm import MockLLMProvider
from debate.providers.mock_search import MockSearchProvider
from debate.models.config import AppConfig

config = AppConfig.from_yaml_files()
runner = DebateRunner(
    config,
    llm_provider=MockLLMProvider(),
    search_provider=MockSearchProvider(),
)
transcript, verdict = runner.run()
```

---

## Configuration

| File | Controls |
|------|---------|
| `config/debate.yaml` | Topic, rounds, budget cap, timeouts, watchdog, log path |
| `config/models.yaml` | Model name and token limits per agent |
| `config/skills.yaml` | Skill-to-agent assignment documentation |
| `config/provider_config.json` | Which LLM/search provider to load at runtime |
| `config/rate_limits.json` | Rate-limit and retry parameters |

Environment variable overrides (highest priority):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export DEBATE_TOPIC="Nuclear energy is safer than fossil fuels"
export DEBATE_ROUNDS=10
```

---

## Running Tests

Tests run **offline** — no API key needed (mock providers are used).

```bash
uv run pytest                           # all 246 tests
uv run pytest tests/unit/ -v            # unit tests only (fast)
uv run pytest tests/integration/ -v     # integration tests
uv run pytest tests/unit/test_agents.py -v
uv run pytest -k "test_skill_id" -v
```

---

## Linting

```bash
uv run ruff check src tests
uv run ruff check --fix src tests && uv run ruff format src tests
```

---

## How It Works

### Debate loop (one round)

1. **Judge** introduces the round (`judge_moderation_skill`).
2. **Pro** calls the LLM with `retrieve_evidence` tool available.
   The tool may call the search provider before finalising the argument.
3. **Judge routes** Pro's message to Con as context.
4. **Con** rebuts, also with evidence retrieval available.
5. **Judge summarises** the key clash.
6. After N rounds, **Judge renders a scored verdict** — PRO or CON wins
   (`verdict_skill` — no ties).

### Gatekeeper guards

Every external call passes through:
1. **Budget check** — raises `BudgetExceededError` if USD cap is reached.
2. **Rate throttle** — sleeps to stay within `max_calls_per_minute`.
3. **Timeout** — `ThreadPoolExecutor` with `future.result(timeout=T)`.
4. **Cost recording** — token counts × per-model pricing from config.

### Watchdog

A daemon thread checks every 10 s for calls running longer than 120 s
(configurable). Logs a warning but never kills a call — preserving
slow-but-valid responses while surfacing genuine stalls.

---

## Message Traceability

Every `DebateMessage` carries:
- `skill_id_used` — which skill produced it (full audit trail)
- `debate_id` — UUID shared across all messages in one session
- `ping_index` — populated in ping/mock mode

```python
msg.skill_id_used   # "pro_argument_skill" | "rebuttal_skill" | ...
msg.debate_id       # "a3f1b2c4d5e6"
```

---

## Structured Logs

Every message and event is appended to `logs/debate.jsonl`:

```json
{"event": "debate_start", "topic": "AI will...", "rounds": 5}
{"id": "...", "round": 1, "role": "pro", "message_type": "argument",
 "skill_id_used": "pro_argument_skill", "debate_id": "a3f1b2c4", ...}
{"event": "verdict", "winner": "pro", "total_pro_score": 32.5, ...}
{"event": "debate_end", "winner": "pro", "total_cost_usd": 0.0087}
```

---

## Project Structure

```
src/debate/
  models/         ← DebateMessage (+skill_id_used/debate_id), Verdict, Config
  skills/         ← 7 SkillDefinitions, SkillRegistry, SkillRouter
  agents/         ← BaseAgent, JudgeAgent, ProAgent, ConAgent
  providers/      ← AbstractLLMProvider/SearchProvider, Anthropic, Mock
  sdk/            ← AgentDebateSDK (run_debate, load_transcript, validate_*)
  cli/            ← Rich menu (menu.py) + agent-debate entry (entry.py)
  gatekeeper.py   ← single provider-agnostic API gateway
  watchdog.py     ← daemon stall detector
  logger.py       ← JSONL writer
  runner.py       ← DebateRunner facade
skills/           ← per-skill dirs: <name>/SKILL.md + prompt.md (×7)
config/           ← debate.yaml, models.yaml, skills.yaml,
                     provider_config.json, rate_limits.json
tests/
  unit/           ← fast offline tests (models, skills, agents, gatekeeper, router, dirs)
  integration/    ← full-pipeline tests with mock providers
docs/             ← PRD.md, PLAN.md (13 phases), TODO.md, PROMPTS.md
logs/             ← JSONL debate logs (gitignored)
main.py           ← entry point
```

---

## Implementation Phases

The codebase was built in 13 strict granular phases — one git commit each.
See [`docs/PLAN.md`](docs/PLAN.md) for the full phase specification.

| Phase | Scope |
|-------|-------|
| 01 | Project skeleton |
| 02 | Core Pydantic models |
| 03 | Skills registry + 7 definitions |
| 04 | BaseAgent + Pro/Con agents |
| 05 | JudgeAgent (parent orchestration) |
| 06 | Gatekeeper + Watchdog + Logger + Runner + CLI |
| 07 | **Provider abstraction layer** (LLM + search, mock providers) |
| 08 | `skill_id_used` + `debate_id` on every message |
| 09 | Per-skill filesystem dirs (SKILL.md + prompt.md × 7) |
| 10 | SkillRouter |
| 11 | SDK layer (`AgentDebateSDK`) |
| 12 | `agent-debate` CLI entry point + subcommands |
| 13 | Test reorganisation (unit/ + integration/) |
