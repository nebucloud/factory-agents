"""Optional LLM backend for review (F2 stub — heuristics remain default)."""

from __future__ import annotations

from typing import Protocol

from factory_agents.models import Finding, ReviewReport


class ReviewLLM(Protocol):
    def review_diff(self, diff_text: str) -> list[Finding]:
        """Return additional findings from model analysis."""
        ...


class NullLLM:
    """No-op backend — keeps CI deterministic."""

    def review_diff(self, diff_text: str) -> list[Finding]:
        return []


class EchoLLM:
    """Dev stub that emits one informational finding proving the hook works."""

    def review_diff(self, diff_text: str) -> list[Finding]:
        from factory_agents.models import RiskLevel

        size = len(diff_text)
        return [
            Finding(
                id="llm-echo-1",
                title="LLM backend stub engaged",
                risk=RiskLevel.informational,
                rationale=f"EchoLLM saw {size} bytes of diff (replace with real model).",
                suggestion="Set FACTORY_AGENTS_LLM=ollama|openai when backends land.",
            )
        ]


def get_llm(name: str | None) -> ReviewLLM:
    if not name or name in ("none", "null", "off"):
        return NullLLM()
    if name == "echo":
        return EchoLLM()
    raise ValueError(f"unknown LLM backend: {name!r} (supported: none, echo)")


def merge_llm_findings(report: ReviewReport, llm: ReviewLLM, diff_text: str) -> ReviewReport:
    extra = llm.review_diff(diff_text)
    if not extra:
        return report
    report.findings.extend(extra)
    report.refresh_risk_max()
    high = sum(1 for f in report.findings if f.needs_human_review)
    report.summary = (
        f"{len(report.findings)} finding(s); max risk={report.risk_max.value}; "
        f"{high} need human review; merge_allowed=false"
    )
    return report
