import pytest

from factory_agents.safety import HARD_DENIED_CAPABILITIES, SafetyError, SafetyPolicy


def test_hard_deny_merge_capability():
    with pytest.raises(SafetyError):
        SafetyPolicy(capabilities={"review.read_diff", "git.merge"})


def test_path_deny_env():
    policy = SafetyPolicy()
    assert policy.path_allowed("src/ok.py")
    assert not policy.path_allowed(".env")
    assert not policy.path_allowed("secrets/cosign.key")


def test_hard_denied_constant():
    assert "git.merge" in HARD_DENIED_CAPABILITIES
    assert "argo.sync" in HARD_DENIED_CAPABILITIES
