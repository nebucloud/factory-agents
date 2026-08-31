"""GitHub Check Run / PR review payload helpers (F2)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from factory_agents.models import ReviewReport, RiskLevel

Conclusion = Literal["success", "failure", "neutral", "cancelled", "timed_out", "action_required"]


class CheckRunOutput(BaseModel):
    title: str
    summary: str
    text: str | None = None


class CheckRunResult(BaseModel):
    """Shape suitable for checks API create/update (name + conclusion + output)."""

    name: str = "factory-agents / review"
    head_sha: str
    status: Literal["completed"] = "completed"
    conclusion: Conclusion
    output: CheckRunOutput
    details_url: str | None = None


class PullRequestRef(BaseModel):
    number: int
    head_sha: str
    base_ref: str = "main"
    head_ref: str = ""
    diff_url: str | None = None


def conclusion_for_report(report: ReviewReport) -> Conclusion:
    if report.risk_max in (RiskLevel.high, RiskLevel.critical):
        return "action_required"
    if report.findings:
        return "neutral"
    return "success"


def check_run_from_report(
    report: ReviewReport,
    *,
    head_sha: str,
    name: str = "factory-agents / review",
) -> CheckRunResult:
    lines = [report.summary, "", "Findings:"]
    if not report.findings:
        lines.append("- (none)")
    for f in report.findings:
        loc = f.path or "?"
        if f.line:
            loc = f"{loc}:{f.line}"
        flag = " **needs human review**" if f.needs_human_review else ""
        lines.append(f"- [{f.risk.value}] `{loc}` — {f.title}{flag}")
    lines.append("")
    lines.append("`merge_allowed` is always false from factory-agents (ADR 0009).")
    return CheckRunResult(
        name=name,
        head_sha=head_sha,
        conclusion=conclusion_for_report(report),
        output=CheckRunOutput(
            title=f"Review: {report.risk_max.value}",
            summary=report.summary,
            text="\n".join(lines),
        ),
    )


def parse_github_event(event: dict[str, Any]) -> PullRequestRef | None:
    """Extract PR ref from pull_request or check_suite-ish webhook payloads."""
    pr = event.get("pull_request")
    if isinstance(pr, dict):
        head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
        base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
        return PullRequestRef(
            number=int(pr.get("number") or 0),
            head_sha=str(head.get("sha") or ""),
            base_ref=str(base.get("ref") or "main"),
            head_ref=str(head.get("ref") or ""),
            diff_url=pr.get("diff_url"),
        )
    sha = event.get("after") or event.get("sha")
    if sha:
        return PullRequestRef(number=0, head_sha=str(sha))
    return None


class Annotation(BaseModel):
    path: str
    start_line: int = Field(ge=1)
    end_line: int | None = None
    annotation_level: Literal["notice", "warning", "failure"] = "warning"
    message: str


def annotations_from_report(report: ReviewReport) -> list[Annotation]:
    out: list[Annotation] = []
    for f in report.findings:
        if not f.path or not f.line:
            continue
        level: Literal["notice", "warning", "failure"] = "notice"
        if f.risk in (RiskLevel.medium, RiskLevel.high):
            level = "warning"
        if f.risk == RiskLevel.critical:
            level = "failure"
        out.append(
            Annotation(
                path=f.path,
                start_line=f.line,
                end_line=f.line,
                annotation_level=level,
                message=f"{f.title}: {f.rationale}",
            )
        )
    return out
