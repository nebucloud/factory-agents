"""Prompt + JSON finding parse for model review."""

from __future__ import annotations

import json
import re
from typing import Any

from factory_agents.models import Finding, RiskLevel

REVIEW_PROMPT = """You are a secure code review agent for a software factory.
You MUST NOT approve merges. Humans approve merges.

Analyze the unified diff below for security and correctness risks.
Return ONLY a JSON object with this shape:
{{
  "findings": [
    {{
      "id": "llm-1",
      "title": "short title",
      "risk": "informational|low|medium|high|critical",
      "path": "path/in/repo or null",
      "line": 12,
      "rationale": "why this matters",
      "suggestion": "how to fix",
      "needs_human_review": true
    }}
  ]
}}

Rules:
- Prefer precise, high-signal findings; empty findings array is OK.
- Flag secrets, injection, authz bypass, privileged containers, unsafe deserialization.
- Set needs_human_review true for medium+ risk.
- Do not invent files that are not in the diff.

DIFF:
```
{diff}
```
"""


def build_review_prompt(diff_text: str, max_chars: int) -> str:
    text = diff_text
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[diff truncated for model context]\n"
    return REVIEW_PROMPT.format(diff=text)


def parse_findings_json(raw: str) -> list[Finding]:
    data = _extract_json_object(raw)
    items = data.get("findings")
    if items is None and isinstance(data.get("results"), list):
        items = data["results"]
    if not isinstance(items, list):
        # Single finding object
        if "title" in data and "risk" in data:
            items = [data]
        else:
            return []

    findings: list[Finding] = []
    for i, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        try:
            risk = RiskLevel(str(item.get("risk", "informational")).lower())
        except ValueError:
            risk = RiskLevel.medium
        fid = str(item.get("id") or f"llm-{i}")
        if not fid.startswith("llm-"):
            fid = f"llm-{fid}"
        path = item.get("path")
        line_raw = item.get("line")
        line: int | None
        if isinstance(line_raw, int):
            line = line_raw
        elif isinstance(line_raw, str) and line_raw.isdigit():
            line = int(line_raw)
        else:
            line = None
        findings.append(
            Finding(
                id=fid,
                title=str(item.get("title") or "Model finding")[:200],
                risk=risk,
                path=str(path) if path else None,
                line=line,
                rationale=str(item.get("rationale") or item.get("reason") or "")[:2000],
                suggestion=(
                    str(item["suggestion"])[:1000] if item.get("suggestion") else None
                ),
                needs_human_review=bool(
                    item.get("needs_human_review")
                    or risk in (RiskLevel.medium, RiskLevel.high, RiskLevel.critical)
                ),
            )
        )
    return findings


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"findings": data}
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            return data
    raise ValueError("model response was not valid JSON findings object")
