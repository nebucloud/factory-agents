# Agent instructions — factory-agents

- Source of truth for product placement: core-nexus **ADR 0009**.
- kiln = hermetic build callee; do not redefine kiln as an agent workspace.
- Prefer expanding `factory_agents/review/` before adding a coding agent.
- Keep capability denials for merge / push-to-protected in `safety.py`.
- Do not import or vendor athena-agents offensive tools.
