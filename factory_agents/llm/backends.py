"""HTTP backends — sync httpx for CLI use."""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


class GenerateBackend(Protocol):
    @property
    def backend_id(self) -> str: ...

    def generate(self, prompt: str, max_tokens: int = 2048) -> str: ...

    def health_check(self) -> bool: ...


class OllamaBackend:
    """Ollama native /api/generate."""

    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def backend_id(self) -> str:
        return f"ollama:{self._model}@{self._base_url}"

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        url = f"{self._base_url}/api/generate"
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"num_predict": max_tokens},
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return str(data.get("response") or "")
        except httpx.HTTPError as exc:
            msg = f"Ollama generate failed ({self.backend_id}): {exc}"
            logger.error(msg)
            raise RuntimeError(msg) from exc

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=min(10.0, self._timeout)) as client:
                response = client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False


class OpenAICompatibleBackend:
    """OpenAI / vLLM / llama.cpp OpenAI-compatible chat completions."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout: float = 120.0,
        label: str = "openai",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout
        self._label = label

    @property
    def backend_id(self) -> str:
        return f"{self._label}:{self._model}@{self._base_url}"

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        url = f"{self._base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a secure code review assistant. "
                        "Respond with JSON only, no markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                # Some local servers reject response_format — retry without it.
                if response.status_code >= 400 and "response_format" in response.text.lower():
                    payload.pop("response_format", None)
                    response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices") or []
                if not choices:
                    return ""
                message = choices[0].get("message") or {}
                return str(message.get("content") or choices[0].get("text") or "")
        except httpx.HTTPError as exc:
            msg = f"{self._label} generate failed ({self.backend_id}): {exc}"
            logger.error(msg)
            raise RuntimeError(msg) from exc

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=min(10.0, self._timeout)) as client:
                headers = {}
                if self._api_key:
                    headers["Authorization"] = f"Bearer {self._api_key}"
                response = client.get(f"{self._base_url}/models", headers=headers)
                return response.status_code == 200
        except httpx.HTTPError:
            return False
