"""OPAR-style review loop — Observe / Plan / Act / Reflect (review-only)."""

from __future__ import annotations

from factory_agents.models import ReviewReport, RiskLevel
from factory_agents.review.heuristics import heuristic_findings
from factory_agents.risk import max_risk
from factory_agents.safety import SafetyPolicy


def run_review(diff_text: str, policy: SafetyPolicy | None = None) -> ReviewReport:
    """
    Observe: parse diff
    Plan: select heuristic (LLM later)
    Act: emit findings only — never merge
    Reflect: compute risk_max + human-review flags
    """
    policy = policy or SafetyPolicy()
    policy.assert_no_merge()

    findings = heuristic_findings(diff_text, policy)
    report = ReviewReport(
        findings=findings,
        risk_max=max_risk(findings),
        merge_allowed=False,
    )
    report.refresh_risk_max()
    high = sum(
        1 for f in report.findings if f.risk in (RiskLevel.high, RiskLevel.critical)
    )
    report.summary = (
        f"{len(report.findings)} finding(s); max risk={report.risk_max.value}; "
        f"{high} need human review; merge_allowed=false"
    )
    return report
