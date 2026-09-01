from unittest.mock import MagicMock, patch

from factory_agents.gateway_notify import (
    build_payload,
    notify_gateway,
    should_notify,
)
from factory_agents.models import Finding, ReviewReport, RiskLevel
from factory_agents.review import run_review
from factory_agents.safety import SafetyPolicy

FIXTURE_DIFF = """diff --git a/.env b/.env
--- a/.env
+++ b/.env
@@ -1 +1,2 @@
+API_KEY=supersecret
"""


def test_should_notify_high_critical():
    report = ReviewReport(risk_max=RiskLevel.high, findings=[])
    assert should_notify(report) is True
    report.risk_max = RiskLevel.medium
    assert should_notify(report) is False


def test_build_payload_filters_findings():
    report = run_review(FIXTURE_DIFF, policy=SafetyPolicy())
    payload = build_payload(
        report,
        repo="nebucloud/factory-agents",
        head_sha="abc123",
        pr_number=7,
    )
    assert payload["repo"] == "nebucloud/factory-agents"
    assert payload["risk_max"] in ("high", "critical")
    assert payload["findings"]


@patch("factory_agents.gateway_notify.httpx.Client")
def test_notify_gateway_posts(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"accepted": True, "approval": {"id": "factory-abc"}}
    mock_client.post.return_value = mock_response

    report = ReviewReport(
        risk_max=RiskLevel.critical,
        summary="1 critical",
        findings=[
            Finding(
                id="x",
                title="secret",
                risk=RiskLevel.critical,
                rationale="leak",
            )
        ],
    )
    result = notify_gateway(
        report,
        repo="nebucloud/factory-agents",
        head_sha="deadbeef",
        gateway_url="http://gateway:3100",
        token="shared",
    )
    assert result["notified"] is True
    call = mock_client.post.call_args
    assert call.args[0] == "http://gateway:3100/api/v1/factory/reviews"
    assert call.kwargs["headers"]["Authorization"] == "Bearer shared"
