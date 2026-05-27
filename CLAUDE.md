# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python multi-agent debate system where autonomous agents argue opposing sides of a topic, a judge agent orchestrates the debate, communicate via structured JSON messages, cite evidence to back arguments, and produce structured logs of the full debate.

## Common Commands

Once the project is set up, typical commands will be:

```bash
# Install dependencies
pip install -r requirements.txt   # or: pip install -e .

# Run the debate system
python main.py

# Run tests
pytest

# Run a single test
pytest tests/test_<module>.py::test_<name> -v

# Lint
ruff check .
ruff format .
```

> These commands should be updated once the project structure is established.

## Architecture

The system is built around three roles:

- **Pro Agent** — argues in favour of the debate topic; generates evidence-backed arguments in a structured JSON format.
- **Con Agent** — argues against the topic; mirrors the same message schema as the Pro Agent.
- **Judge / Orchestrator** — drives the debate loop: decides turn order, evaluates argument quality, determines when the debate concludes, and writes a final verdict.

### Key design constraints

- **JSON-based inter-agent communication** — all messages passed between agents (arguments, rebuttals, verdicts) must be serialisable JSON objects with a consistent schema.
- **Evidence-backed arguments** — each argument payload should include citations or supporting evidence fields; agents must not assert claims without an evidence reference.
- **Structured logs** — every exchange is appended to a structured log (JSON lines or similar) so the full debate can be replayed or audited offline.

### Expected module layout (to be created)

| Module | Responsibility |
|--------|---------------|
| `agents/pro_agent.py` | Pro-side argument generation |
| `agents/con_agent.py` | Con-side argument generation |
| `agents/judge.py` | Orchestration, turn management, verdict |
| `models/messages.py` | Pydantic (or dataclass) schemas for agent messages |
| `debate/runner.py` | Top-level debate loop |
| `utils/logger.py` | Structured JSON logging |
| `main.py` | Entry point |

## Inter-Agent Message Schema

All agent messages should conform to a shared envelope (adapt as the schema evolves):

```json
{
  "round": 1,
  "role": "pro | con | judge",
  "argument": "...",
  "evidence": [{"source": "...", "quote": "..."}],
  "timestamp": "ISO-8601"
}
```
