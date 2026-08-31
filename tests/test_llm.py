from factory_agents.llm import EchoLLM, get_llm, merge_llm_findings
from factory_agents.models import ReviewReport
from factory_agents.review import run_review


def test_echo_llm_adds_informational():
    report = run_review("diff --git a/x b/x\n", llm=EchoLLM())
    assert any(f.id.startswith("llm-echo") for f in report.findings)


def test_get_llm_none():
    assert get_llm("none").review_diff("x") == []


def test_get_llm_ollama_factory():
    llm = get_llm("ollama")
    assert hasattr(llm, "backend_id")
    assert "ollama:" in llm.backend_id


def test_merge_preserves_merge_allowed_false():
    base = ReviewReport(summary="s", merge_allowed=False)
    out = merge_llm_findings(base, EchoLLM(), "diff")
    assert out.merge_allowed is False
