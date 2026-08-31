"""Pydantic schemas for review findings and reports."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    informational = "informational"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Finding(BaseModel):
    id: str
    title: str
    risk: RiskLevel
    path: str | None = None
    line: int | None = None
    rationale: str
    suggestion: str | None = None
    needs_human_review: bool = False


class ReviewReport(BaseModel):
    """Output of a review pass — never implies merge authority."""

    schema_version: str = "0.1.0"
    agent: str = "factory-agents-review"
    risk_max: RiskLevel = RiskLevel.informational
    findings: list[Finding] = Field(default_factory=list)
    summary: str = ""
    kiln_verify: dict[str, Any] | None = None
    merge_allowed: bool = False  # always false from this agent

    def refresh_risk_max(self) -> None:
        order = [
            RiskLevel.informational,
            RiskLevel.low,
            RiskLevel.medium,
            RiskLevel.high,
            RiskLevel.critical,
        ]
        rank = {r: i for i, r in enumerate(order)}
        self.risk_max = max(
            (f.risk for f in self.findings),
            default=RiskLevel.informational,
            key=lambda r: rank[r],
        )
        if self.risk_max in (RiskLevel.high, RiskLevel.critical):
            for f in self.findings:
                if f.risk in (RiskLevel.high, RiskLevel.critical):
                    f.needs_human_review = True
