# CLAUDE.md — factory-agents

## What this repo is

Factory AI **secure coding / PR review** agents for NebuCloud + Underground Nexus.
ADR: `acald-creator/core-nexus` → `docs/decisions/0009-factory-ai-secure-coding-review-agents.md`.

- **kiln** runs hermetic builds; this repo **calls** kiln.
- **ssf** signs outputs; this repo does not sign.
- **athena-agents** is red-range OPAR — reuse *safety patterns only*, never red skills.
- **ai-inference** is SOC triage — do not put coding LLMs there.

## Product order

1. Review agent (current scaffold)
2. Coding agent (later; allowlisted paths; bot PRs only)
3. Never autonomous merge/promote

## Commands

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
factory-agents review --diff tests/fixtures/sample.diff --json
```

## Conventions

- Python 3.11+, pydantic v2
- Conventional commits: `feat(review): …`, `fix(safety): …`
- No `git merge`, no push to `main` from agent code paths
