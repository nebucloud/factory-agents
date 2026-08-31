# factory-agents

Factory AI for **secure coding** and **PR review**. Sibling to [kiln](https://github.com/nebucloud/kiln) and [ssf](https://github.com/nebucloud/ssf). Locked by Underground Nexus [ADR 0009](https://github.com/acald-creator/core-nexus/blob/main/docs/decisions/0009-factory-ai-secure-coding-review-agents.md).

```
agent runtime (this repo)
  → security-compliance-hub (enforce)
  → kiln (hermetic lint/test/build on SHA)
  → ssf (sign / attest / SBOM / policy)
  → registry → Flux → Argo
```

## What this is / is not

| Is | Is not |
| --- | --- |
| Review agent first (diff → findings + risk) | kiln — hermetic *build* engine |
| Coding agent later (allowlisted paths, bot PRs) | ssf — signing / SBOM / policy |
| OPAR-style loop + capability gates | athena-agents red/offensive skills |
| Callee of kiln for verify | `platform/ai-inference` (SOC triage only) |
| Human merge gate always | Autonomous merge / promote |

kiln’s “sandbox” means Linux namespace isolation around **build targets**. Agents do **not** live inside kiln; they **call** kiln.

## Status

Scaffold (F0→F2 path). Heuristic review runs without an LLM. LLM backends and GitHub App wiring come next.

| Phase | Intent | Here |
| --- | --- | --- |
| F0 | ADR + vocabulary | ✅ (core-nexus ADR 0009) |
| F1 | kiln verify on PR SHA | stub client + docs |
| F2 | Review agent + human gate | CLI + heuristics + safety |
| F3 | Coding agent | deferred |
| F4 | Signed model promote | deferred |

## Install

```bash
pip install -e ".[dev]"
factory-agents --help
factory-agents review --diff tests/fixtures/sample.diff
```

## Review CLI

```bash
# Heuristic review of a unified diff (no LLM, no merge)
factory-agents review --diff path/to.patch --json

# Optional: ask kiln to run a verify pipeline (requires kiln on PATH)
factory-agents kiln-verify --pipeline config/kiln-verify.example.json --dry-run
```

Exit codes: `0` ok / informational, `1` high-risk findings (check failed), `2` usage/config error.

## Safety defaults

- **Never merges** and never pushes to protected defaults.
- Path allowlists / denylists via `config/`.
- Capability gates: `review.write_comment` may be enabled; `git.push_main` and `git.merge` are hard-denied.
- High-risk findings require human approval (GitHub + Nexus Console Approvals).

## Layout

```
factory_agents/          # Python package
  review/                # OPAR review loop + heuristics
  kiln_client.py         # invoke kiln (callee)
  safety.py              # allowlist + capability gates
  models.py              # Finding / ReviewReport schemas
config/                  # example allowlist + capabilities
tests/
```

## License

Dual MIT / Apache-2.0 (same as kiln and ssf).
