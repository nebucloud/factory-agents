import json
from pathlib import Path

from factory_agents.github_check import (
    annotations_from_report,
    check_run_from_report,
    parse_github_event,
)
from factory_agents.review import run_review
from factory_agents.safety import SafetyPolicy

FIXTURE = Path(__file__).parent / "fixtures" / "sample.diff"


def test_parse_pull_request_event():
    event = {
        "pull_request": {
            "number": 12,
            "head": {"sha": "abc123", "ref": "feat/x"},
            "base": {"ref": "main"},
            "diff_url": "https://example/diff",
        }
    }
    ref = parse_github_event(event)
    assert ref is not None
    assert ref.number == 12
    assert ref.head_sha == "abc123"
    assert ref.base_ref == "main"


def test_check_run_action_required_on_critical():
    report = run_review(FIXTURE.read_text(encoding="utf-8"), policy=SafetyPolicy())
    check = check_run_from_report(report, head_sha="deadbeef")
    assert check.conclusion == "action_required"
    assert "merge_allowed" in (check.output.text or "")
    anns = annotations_from_report(report)
    assert anns
    json.dumps(check.model_dump())
