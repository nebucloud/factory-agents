from pathlib import Path

from factory_agents.models import RiskLevel
from factory_agents.review import run_review
from factory_agents.safety import SafetyPolicy

FIXTURE = Path(__file__).parent / "fixtures" / "sample.diff"


def test_heuristic_review_flags_secret_and_privileged():
    report = run_review(FIXTURE.read_text(encoding="utf-8"), policy=SafetyPolicy())
    assert report.merge_allowed is False
    assert report.risk_max in (RiskLevel.high, RiskLevel.critical)
    ids = {f.id.split("-")[0] for f in report.findings}
    assert "secretish" in ids or any(f.risk == RiskLevel.critical for f in report.findings)
    assert any("privileged" in (f.rationale or "").lower() or "privileged" in f.title.lower()
               or f.id.startswith("dangerous") for f in report.findings)
