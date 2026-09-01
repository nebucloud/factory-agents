# factory-agents

Factory AI for **secure coding** and **PR review**. Sibling to [kiln](https://github.com/nebucloud/kiln) and [ssf](https://github.com/nebucloud/ssf). Locked by Underground Nexus [ADR 0009](https://github.com/acald-creator/core-nexus/blob/main/docs/decisions/0009-factory-ai-secure-coding-review-agents.md).

```
agent runtime (this repo)
  → security-compliance-hub (enforce)
  → kiln (hermetic lint/test/build on SHA)
  → ssf (sign / attest / SBOM / policy)
  → registry → Flux → Argo
```

## Status

| Phase | Intent | Status |
| --- | --- | --- |
| F0 | ADR + vocabulary | ✅ |
| F1 | kiln verify on PR SHA | ✅ schema validate + `kiln run` callee |
| F2 | Review agent + check payload | ✅ heuristics + Check Run POST + **Ollama/OpenAI/vLLM** |
| F3 | Coding agent | deferred |
| F4 | Signed model promote | deferred |

## Install

```bash
pip install -e ".[dev]"
factory-agents --help
```

## Commands

```bash
# Heuristic review (exit 1 on high/critical)
factory-agents review --diff tests/fixtures/sample.diff --json

# Optional LLM hook (stub)
factory-agents review --diff tests/fixtures/sample.diff --llm echo

# Real local model via Ollama (requires ollama serve + pulled model)
factory-agents review --diff tests/fixtures/sample.diff --llm ollama \
  --llm-config config/llm.example.toml

# OpenAI-compatible (OpenAI API or vLLM)
FACTORY_AGENTS_LLM_MODEL=gpt-4o-mini OPENAI_API_KEY=sk-... \
  factory-agents review --diff tests/fixtures/sample.diff --llm openai

# GitHub Check Run JSON (local only)
factory-agents check --diff tests/fixtures/sample.diff --sha "$GITHUB_SHA" \
  --kiln-pipeline config/kiln-verify.example.json

# POST Check Run (Actions: GITHUB_TOKEN; App: GITHUB_APP_ID + INSTALLATION_ID + key)
factory-agents check --diff tests/fixtures/sample.diff --sha "$GITHUB_SHA" --post \
  --repo nebucloud/factory-agents --kiln-pipeline config/kiln-verify.example.json

# kiln pipeline schema + dry-run plan
factory-agents kiln-validate --pipeline config/kiln-verify.example.json
factory-agents kiln-verify --pipeline config/kiln-verify.example.json
# execute for real when kiln-cli is installed:
# factory-agents kiln-verify --pipeline config/kiln-verify.example.json --no-dry-run
```

kiln manifest shape (KLN-D-02 / ssf `pkg/kiln`):

```json
{
  "version": "1",
  "targets": {
    "lint": {
      "run": { "interpreter": "bash", "code": "ruff check .\n" }
    }
  }
}
```

## Safety defaults

- **Never merges**; `git.merge` / push-to-protected / promote are hard-denied.
- Path deny for `.env`, keys, `*secret*`.
- High/critical → Check conclusion `action_required` + `needs_human_review`.

## Layout

```
factory_agents/
  review/           # OPAR + heuristics
  kiln_client.py    # kiln validate/run callee
  github_check.py   # Check Run payload
  github_api.py     # POST check-runs (token / App auth)
  llm/               # none|echo|ollama|openai|vllm backends
config/kiln-verify.example.json
config/llm.example.toml
```

## License

Dual MIT / Apache-2.0.
