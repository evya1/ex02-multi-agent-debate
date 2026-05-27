# TODO — Implementation Progress

## ✅ Completed

### Core Architecture
- [x] `pyproject.toml` — uv project with all dependencies
- [x] `.env.example` — API key template
- [x] `config/debate.yaml` — debate parameters, gatekeeper, watchdog, logging
- [x] `config/models.yaml` — per-agent model config + pricing
- [x] `config/skills.yaml` — skill-to-agent assignment documentation

### Models
- [x] `DebateMessage` — universal message envelope (Pydantic v2)
- [x] `Evidence` — source-attributed evidence citation
- [x] `Role`, `MessageType` — enums for type safety
- [x] `Verdict` / `RoundScore` — final judgment (tie structurally impossible)
- [x] `SkillDefinition` — full skill metadata with prompt injection method
- [x] `AppConfig` and sub-configs — YAML loader with env var overrides

### Skills
- [x] `judge_moderation_skill` — neutral round moderation
- [x] `pro_argument_skill` — structured pro-side argument
- [x] `con_argument_skill` — structured con-side argument
- [x] `evidence_retrieval_skill` — web search instructions and tool definition
- [x] `rebuttal_skill` — direct counter-argument pattern
- [x] `verdict_skill` — scored verdict, no ties
- [x] `json_protocol_skill` — JSON-only output enforcement
- [x] `SkillRegistry` — register, get, filter by agent role
- [x] `build_registry()` — factory for all 7 skills

### Agents
- [x] `BaseAgent` — LLM-call loop, tool-use resolution, JSON parsing, fallback
- [x] `JudgeAgent` — parent agent: spawns Pro+Con, routes all messages, verdict
- [x] `ProAgent` — PRO debater with evidence tool
- [x] `ConAgent` — CON debater with evidence tool

### Infrastructure
- [x] `Gatekeeper` — budget, rate limit, timeout, retry, cost tracking
- [x] `Watchdog` — daemon thread stall detector with context manager API
- [x] `DebateLogger` — JSONL structured logging
- [x] `DebateRunner` — public SDK facade
- [x] `DebateCLI` — Rich terminal menu (5 options)
- [x] `main.py` — entry point with `--run` flag for SDK mode

### Tests (all mocked, no API key required)
- [x] `test_models.py` — DebateMessage, Evidence, Verdict validation
- [x] `test_skills.py` — SkillRegistry, all 7 skills, per-agent counts
- [x] `test_agents.py` — Pro/Con/Judge with mocked Gatekeeper
- [x] `test_gatekeeper.py` — budget tracking, timeout, search mock
- [x] `test_runner.py` — integration test with full mock chain

### Documentation
- [x] `docs/PRD.md` — product requirements
- [x] `docs/PLAN.md` — architecture, classes, data flow, decisions
- [x] `docs/TODO.md` — this file
- [x] `docs/PROMPTS.md` — all significant prompts used
- [x] `README.md` — setup, usage, architecture overview, skills table
- [x] `CLAUDE.md` — commands and architecture for Claude Code

## 🔜 Remaining / Future Work

- [ ] **Screenshots** — add terminal screenshots after running the full debate once
- [ ] **Full debate transcript** — run the system and paste the output into README
- [ ] **async support** — replace `ThreadPoolExecutor` timeouts with `asyncio` for performance
- [ ] **Streaming output** — stream Claude responses in real time via `stream=True`
- [ ] **Multi-provider** — add OpenAI or Gemini as alternate backends behind Gatekeeper
- [ ] **Persistent transcript store** — SQLite or local JSON for replaying past debates
- [ ] **Round-count increase** — verify 10-round "full mode" runs within the $2 budget cap
