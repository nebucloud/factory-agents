"""Model-backed ReviewLLM using a GenerateBackend."""

from __future__ import annotations

import logging

from factory_agents.llm.backends import GenerateBackend
from factory_agents.llm.prompt import build_review_prompt, parse_findings_json
from factory_agents.models import Finding

logger = logging.getLogger(__name__)


class ModelReviewLLM:
    def __init__(self, backend: GenerateBackend, max_diff_chars: int = 48_000) -> None:
        self._backend = backend
        self._max_diff_chars = max_diff_chars

    @property
    def backend_id(self) -> str:
        return self._backend.backend_id

    def review_diff(self, diff_text: str) -> list[Finding]:
        prompt = build_review_prompt(diff_text, self._max_diff_chars)
        raw = self._backend.generate(prompt, max_tokens=2048)
        try:
            findings = parse_findings_json(raw)
        except ValueError as exc:
            logger.warning("Failed to parse model JSON (%s): %s", self.backend_id, exc)
            raise RuntimeError(f"LLM returned unparseable review JSON: {exc}") from exc
        return findings
