"""HTTP LLM backends with mocked httpx."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from factory_agents.llm.backends import OllamaBackend, OpenAICompatibleBackend
from factory_agents.llm.reviewer import ModelReviewLLM
from factory_agents.models import RiskLevel


def test_ollama_generate_and_review():
    payload = {
        "response": json.dumps(
            {
                "findings": [
                    {
                        "title": "SQL injection risk",
                        "risk": "high",
                        "path": "db.py",
                        "line": 10,
                        "rationale": "string concat in query",
                        "suggestion": "use parameterized queries",
                    }
                ]
            }
        )
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.status_code = 200

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = mock_resp

    with patch("factory_agents.llm.backends.httpx.Client", return_value=mock_client):
        backend = OllamaBackend("http://127.0.0.1:11434", "llama3.2")
        llm = ModelReviewLLM(backend=backend)
        findings = llm.review_diff("diff --git a/db.py b/db.py\n")

    assert len(findings) == 1
    assert findings[0].risk == RiskLevel.high
    assert findings[0].path == "db.py"
    mock_client.post.assert_called()
    args, kwargs = mock_client.post.call_args
    assert args[0].endswith("/api/generate")
    assert kwargs["json"]["format"] == "json"


def test_openai_compatible_chat():
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "findings": [
                                {
                                    "title": "ok",
                                    "risk": "informational",
                                    "rationale": "noop",
                                }
                            ]
                        }
                    )
                }
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.status_code = 200
    mock_resp.text = ""

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = mock_resp

    with patch("factory_agents.llm.backends.httpx.Client", return_value=mock_client):
        backend = OpenAICompatibleBackend(
            "https://api.openai.com/v1",
            "gpt-4o-mini",
            api_key="sk-test",
        )
        text = backend.generate("prompt")
    assert "findings" in text
    headers = mock_client.post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer sk-test"
