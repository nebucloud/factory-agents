"""Risk helpers."""

from __future__ import annotations

from factory_agents.models import Finding, RiskLevel

_RANK = {
    RiskLevel.informational: 0,
    RiskLevel.low: 1,
    RiskLevel.medium: 2,
    RiskLevel.high: 3,
    RiskLevel.critical: 4,
}


def max_risk(findings: list[Finding]) -> RiskLevel:
    if not findings:
        return RiskLevel.informational
    return max(findings, key=lambda f: _RANK[f.risk]).risk


def exit_code_for_risk(risk: RiskLevel) -> int:
    """CI-friendly: high/critical fail the check."""
    if risk in (RiskLevel.high, RiskLevel.critical):
        return 1
    return 0
