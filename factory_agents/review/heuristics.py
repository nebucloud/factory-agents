"""Deterministic review heuristics (no LLM) — F2 scaffold."""

from __future__ import annotations

import re
from dataclasses import dataclass

from factory_agents.models import Finding, RiskLevel
from factory_agents.safety import SafetyPolicy


@dataclass
class DiffFile:
    path: str
    added_lines: list[tuple[int, str]]  # (line_no_in_new_file_est, text)


_DIFF_GIT = re.compile(r"^diff --git a/(.+) b/(.+)$")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_unified_diff(text: str) -> list[DiffFile]:
    files: list[DiffFile] = []
    current: DiffFile | None = None
    new_line = 0
    for raw in text.splitlines():
        m = _DIFF_GIT.match(raw)
        if m:
            current = DiffFile(path=m.group(2), added_lines=[])
            files.append(current)
            new_line = 0
            continue
        if current is None:
            continue
        hm = _HUNK.match(raw)
        if hm:
            new_line = int(hm.group(1))
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            current.added_lines.append((new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        elif raw.startswith(" "):
            new_line += 1
    return files


_SECRETISH = re.compile(
    r"(?i)(api[_-]?key|secret|password|token|aws_access|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"
)
_SUDO = re.compile(r"(?i)\b(curl\s+\|.*sh|chmod\s+777|privileged:\s*true)\b")


def heuristic_findings(diff_text: str, policy: SafetyPolicy) -> list[Finding]:
    policy.require("review.read_diff")
    findings: list[Finding] = []
    n = 0
    for df in parse_unified_diff(diff_text):
        if not policy.path_allowed(df.path):
            n += 1
            findings.append(
                Finding(
                    id=f"path-denied-{n}",
                    title="Change touches denied or non-allowlisted path",
                    risk=RiskLevel.high,
                    path=df.path,
                    rationale=(
                        f"Path '{df.path}' is outside the review allowlist "
                        "or matches a deny rule."
                    ),
                    suggestion="Move secrets/config out of the PR or narrow the change.",
                    needs_human_review=True,
                )
            )
            continue
        for line_no, line in df.added_lines:
            if _SECRETISH.search(line):
                n += 1
                findings.append(
                    Finding(
                        id=f"secretish-{n}",
                        title="Possible hardcoded secret in added line",
                        risk=RiskLevel.critical,
                        path=df.path,
                        line=line_no,
                        rationale="Added line matches common secret assignment patterns.",
                        suggestion=(
                            "Use Vault / env injection; rotate if a real secret was committed."
                        ),
                        needs_human_review=True,
                    )
                )
            if _SUDO.search(line):
                n += 1
                findings.append(
                    Finding(
                        id=f"dangerous-{n}",
                        title="Dangerous command or privileged container flag",
                        risk=RiskLevel.high,
                        path=df.path,
                        line=line_no,
                        rationale=line.strip()[:200],
                        suggestion=(
                            "Avoid pipe-to-shell and privileged:true unless explicitly justified."
                        ),
                        needs_human_review=True,
                    )
                )
    return findings
