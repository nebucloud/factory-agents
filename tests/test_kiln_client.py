from pathlib import Path

from factory_agents.kiln_client import load_pipeline_json, validate_pipeline_schema, verify

EXAMPLE = Path(__file__).resolve().parents[1] / "config" / "kiln-verify.example.json"


def test_example_pipeline_schema_ok():
    pipeline = load_pipeline_json(EXAMPLE)
    assert validate_pipeline_schema(pipeline) == []


def test_verify_dry_run_lists_targets():
    result = verify(EXAMPLE, dry_run=True)
    assert result["status"] == "dry_run"
    assert result["schema_ok"] is True
    assert "lint" in result["targets"]
    assert result["would_run"][0:2] == ["kiln", "run"]


def test_invalid_pipeline_caught():
    bad = {"version": "9", "targets": {}}
    errs = validate_pipeline_schema(bad)
    assert any("version" in e for e in errs)
