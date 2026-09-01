import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from factory_agents.github_api import (
    GitHubAPIError,
    check_run_api_body,
    create_check_run,
    resolve_repository,
    resolve_token,
)
from factory_agents.github_check import (
    annotations_from_report,
    check_run_from_report,
)
from factory_agents.review import run_review
from factory_agents.safety import SafetyPolicy

FIXTURE = Path(__file__).parent / "fixtures" / "sample.diff"


def test_resolve_token_from_explicit():
    assert resolve_token(token="ghs_test") == "ghs_test"


def test_resolve_token_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_env")
    assert resolve_token() == "ghs_env"


def test_resolve_token_missing():
    with pytest.raises(GitHubAPIError):
        resolve_token()


def test_resolve_repository_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "nebucloud/factory-agents")
    assert resolve_repository() == "nebucloud/factory-agents"


def test_check_run_api_body_includes_annotations():
    report = run_review(FIXTURE.read_text(encoding="utf-8"), policy=SafetyPolicy())
    check = check_run_from_report(report, head_sha="abc")
    anns = annotations_from_report(report)
    body = check_run_api_body(check, anns)
    assert body["head_sha"] == "abc"
    assert "annotations" in body["output"]
    assert body["output"]["annotations"]


@patch("factory_agents.github_api.httpx.Client")
def test_create_check_run_posts(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 99,
        "html_url": "https://github.com/o/r/runs/99",
        "conclusion": "action_required",
    }
    mock_client.post.return_value = mock_response

    report = run_review(FIXTURE.read_text(encoding="utf-8"), policy=SafetyPolicy())
    check = check_run_from_report(report, head_sha="deadbeef")
    result = create_check_run(
        "nebucloud/factory-agents",
        check,
        token="ghs_test",
        annotations=annotations_from_report(report),
    )

    assert result["id"] == 99
    call = mock_client.post.call_args
    assert call.args[0].endswith("/repos/nebucloud/factory-agents/check-runs")
    payload = call.kwargs["json"]
    assert payload["head_sha"] == "deadbeef"
    assert payload["conclusion"] == "action_required"
    json.dumps(payload)
