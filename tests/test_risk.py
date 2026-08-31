from factory_agents.models import Finding, RiskLevel
from factory_agents.risk import exit_code_for_risk, max_risk


def test_max_risk_and_exit_code():
    findings = [
        Finding(
            id="a",
            title="t",
            risk=RiskLevel.low,
            rationale="r",
        ),
        Finding(
            id="b",
            title="t",
            risk=RiskLevel.critical,
            rationale="r",
        ),
    ]
    assert max_risk(findings) == RiskLevel.critical
    assert exit_code_for_risk(RiskLevel.critical) == 1
    assert exit_code_for_risk(RiskLevel.low) == 0
