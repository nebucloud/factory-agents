"""Notify Nexus gateway when factory review needs human approval."""

from __future__ import annotations

import os
from typing import Any

import httpx

from factory_agents.models import ReviewReport, RiskLevel

NOTIFY_RISKS = {RiskLevel.high, RiskLevel.critical}


class GatewayNotifyError(RuntimeError):
    pass


def resolve_gateway_url(url: str | None = None) -> str | None:
    value = url or os.environ.get("FACTORY_AGENTS_GATEWAY_URL")
    if not value:
        return None
    return value.rstrip("/")


def resolve_gateway_token(token: str | None = None) -> str | None:
    return token or os.environ.get("FACTORY_AGENTS_GATEWAY_TOKEN")


def should_notify(report: ReviewReport) -> bool:
    return report.risk_max in NOTIFY_RISKS


def build_payload(
    report: ReviewReport,
    *,
    repo: str,
    head_sha: str,
    pr_number: int | None = None,
    check_run_url: str | None = None,
) -> dict[str, Any]:
    return {
        "repo": repo,
        "head_sha": head_sha,
        "pr_number": pr_number,
        "check_run_url": check_run_url,
        "risk_max": report.risk_max.value,
        "summary": report.summary,
        "findings": [
            {
                "id": f.id,
                "title": f.title,
                "risk": f.risk.value,
                "path": f.path,
                "line": f.line,
                "rationale": f.rationale,
            }
            for f in report.findings
            if f.risk in NOTIFY_RISKS
        ],
    }


def notify_gateway(
    report: ReviewReport,
    *,
    repo: str,
    head_sha: str,
    gateway_url: str,
    token: str,
    pr_number: int | None = None,
    check_run_url: str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    if not should_notify(report):
        return {"notified": False, "reason": "risk_below_threshold"}

    url = f"{gateway_url.rstrip('/')}/api/v1/factory/reviews"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = build_payload(
        report,
        repo=repo,
        head_sha=head_sha,
        pr_number=pr_number,
        check_run_url=check_run_url,
    )
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=body, headers=headers)
        if response.status_code >= 400:
            raise GatewayNotifyError(
                f"gateway notify failed: {response.status_code} {response.text}"
            )
        data = response.json()
        if not isinstance(data, dict):
            raise GatewayNotifyError("gateway notify returned non-object JSON")
        return {"notified": True, **data}
