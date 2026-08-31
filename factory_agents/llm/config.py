"""LLM connection settings from env / optional TOML."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LLMSettings:
    backend: str = "none"
    url: str = ""
    model: str = ""
    api_key: str = ""
    timeout: float = 120.0
    max_diff_chars: int = 48_000


def load_settings(*, backend: str | None = None, config_path: Path | None = None) -> LLMSettings:
    settings = LLMSettings()
    if config_path and config_path.is_file():
        settings = _from_toml(config_path)
    settings.backend = backend or os.environ.get("FACTORY_AGENTS_LLM", settings.backend)
    settings.url = os.environ.get("FACTORY_AGENTS_LLM_URL", settings.url)
    settings.model = os.environ.get("FACTORY_AGENTS_LLM_MODEL", settings.model)
    settings.api_key = os.environ.get(
        "FACTORY_AGENTS_LLM_API_KEY",
        os.environ.get("OPENAI_API_KEY", settings.api_key),
    )
    if os.environ.get("FACTORY_AGENTS_LLM_TIMEOUT"):
        settings.timeout = float(os.environ["FACTORY_AGENTS_LLM_TIMEOUT"])
    if os.environ.get("FACTORY_AGENTS_LLM_MAX_DIFF"):
        settings.max_diff_chars = int(os.environ["FACTORY_AGENTS_LLM_MAX_DIFF"])
    return settings


def _from_toml(path: Path) -> LLMSettings:
    import tomllib

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    section = data.get("backend") or data.get("llm") or {}
    return LLMSettings(
        backend=str(section.get("type") or section.get("backend") or "none"),
        url=str(section.get("url") or ""),
        model=str(section.get("model") or ""),
        api_key=str(section.get("api_key") or ""),
        timeout=float(section.get("timeout_seconds") or section.get("timeout") or 120.0),
        max_diff_chars=int(section.get("max_diff_chars") or 48_000),
    )
