"""LLM backends for factory-agents review (Ollama + OpenAI-compatible)."""

from __future__ import annotations

import logging
import os
from typing import Protocol

from factory_agents.llm.backends import OllamaBackend, OpenAICompatibleBackend
from factory_agents.llm.config import LLMSettings, load_settings
from factory_agents.llm.reviewer import ModelReviewLLM
from factory_agents.models import Finding, ReviewReport, RiskLevel

logger = logging.getLogger(__name__)

__all__ = [
    "EchoLLM",
    "NullLLM",
    "ReviewLLM",
    "get_llm",
    "merge_llm_findings",
]


class ReviewLLM(Protocol):
    def review_diff(self, diff_text: str) -> list[Finding]:
        """Return additional findings from model analysis."""
        ...


class NullLLM:
    """No-op backend — keeps CI deterministic."""

    def review_diff(self, diff_text: str) -> list[Finding]:
        return []


class EchoLLM:
    """Dev stub that emits one informational finding proving the hook works."""

    def review_diff(self, diff_text: str) -> list[Finding]:
        from factory_agents.models import RiskLevel

        size = len(diff_text)
        return [
            Finding(
                id="llm-echo-1",
                title="LLM backend stub engaged",
                risk=RiskLevel.informational,
                rationale=f"EchoLLM saw {size} bytes of diff.",
                suggestion="Use --llm ollama or --llm openai for real models.",
            )
        ]


def get_llm(name: str | None, settings: LLMSettings | None = None) -> ReviewLLM:
    """
    Resolve a review LLM.

    name: none|echo|ollama|openai|vllm
    Env (when settings omitted):
      FACTORY_AGENTS_LLM_URL, FACTORY_AGENTS_LLM_MODEL,
      FACTORY_AGENTS_LLM_API_KEY, FACTORY_AGENTS_LLM_TIMEOUT
    """
    if not name or name in ("none", "null", "off"):
        return NullLLM()
    if name == "echo":
        return EchoLLM()

    cfg = settings or load_settings(backend=name)
    if name == "ollama":
        backend = OllamaBackend(
            base_url=cfg.url or "http://127.0.0.1:11434",
            model=cfg.model or "llama3.2",
            timeout=cfg.timeout,
        )
        return ModelReviewLLM(backend=backend, max_diff_chars=cfg.max_diff_chars)
    if name in ("openai", "vllm"):
        default_url = (
            "https://api.openai.com/v1"
            if name == "openai"
            else "http://127.0.0.1:8000/v1"
        )
        api_key = cfg.api_key or os.environ.get("OPENAI_API_KEY", "")
        backend = OpenAICompatibleBackend(
            base_url=cfg.url or default_url,
            model=cfg.model or ("gpt-4o-mini" if name == "openai" else "default"),
            api_key=api_key,
            timeout=cfg.timeout,
            label=name,
        )
        return ModelReviewLLM(backend=backend, max_diff_chars=cfg.max_diff_chars)
    raise ValueError(
        f"unknown LLM backend: {name!r} (supported: none, echo, ollama, openai, vllm)"
    )


def merge_llm_findings(
    report: ReviewReport, llm: ReviewLLM, diff_text: str
) -> ReviewReport:
    try:
        extra = llm.review_diff(diff_text)
    except Exception as exc:
        logger.warning("LLM review failed; continuing with heuristics only: %s", exc)
        report.findings.append(
            Finding(
                id="llm-error-1",
                title="LLM review unavailable",
                risk=RiskLevel.low,
                rationale=str(exc)[:500],
                suggestion="Check LLM URL/model; heuristics still applied.",
                needs_human_review=False,
            )
        )
        report.refresh_risk_max()
        report.summary = _summary(report)
        return report

    if not extra:
        return report
    report.findings.extend(extra)
    report.refresh_risk_max()
    report.summary = _summary(report)
    return report


def _summary(report: ReviewReport) -> str:
    high = sum(1 for f in report.findings if f.needs_human_review)
    return (
        f"{len(report.findings)} finding(s); max risk={report.risk_max.value}; "
        f"{high} need human review; merge_allowed=false"
    )
