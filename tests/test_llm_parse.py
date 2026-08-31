"""Parse model JSON into Finding list."""

from factory_agents.llm.prompt import parse_findings_json
from factory_agents.models import RiskLevel


def test_parse_clean_object():
    raw = """
    {
      "findings": [
        {
          "id": "1",
          "title": "Hardcoded token",
          "risk": "critical",
          "path": "app.py",
          "line": 3,
          "rationale": "secret in source",
          "suggestion": "use Vault",
          "needs_human_review": true
        }
      ]
    }
    """
    findings = parse_findings_json(raw)
    assert len(findings) == 1
    assert findings[0].id == "llm-1"
    assert findings[0].risk == RiskLevel.critical
    assert findings[0].path == "app.py"


def test_parse_fenced_json():
    raw = """Here you go:
```json
{"findings":[{"title":"x","risk":"low","rationale":"y"}]}
```
"""
    findings = parse_findings_json(raw)
    assert len(findings) == 1
    assert findings[0].id.startswith("llm-")


def test_parse_empty_findings():
    assert parse_findings_json('{"findings":[]}') == []
