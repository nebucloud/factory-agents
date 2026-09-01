"""GitHub REST client for Check Runs (F2)."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from factory_agents.github_check import Annotation, CheckRunResult

DEFAULT_API_URL = "https://api.github.com"
MAX_ANNOTATIONS = 50


class GitHubAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def resolve_token(
    *,
    token: str | None = None,
    app_id: str | None = None,
    private_key: str | None = None,
    installation_id: str | None = None,
) -> str:
    """Resolve a bearer token from CLI flag, Actions token, or GitHub App credentials."""
    if token:
        return token

    env_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env_token:
        return env_token

    app_id = app_id or os.environ.get("GITHUB_APP_ID")
    installation_id = installation_id or os.environ.get("GITHUB_INSTALLATION_ID")
    private_key = private_key or _load_private_key()
    if app_id and installation_id and private_key:
        return app_installation_token(
            app_id=app_id,
            private_key=private_key,
            installation_id=installation_id,
            api_url=os.environ.get("GITHUB_API_URL", DEFAULT_API_URL),
        )

    raise GitHubAPIError(
        "No GitHub token: set GITHUB_TOKEN or GitHub App env "
        "(GITHUB_APP_ID, GITHUB_INSTALLATION_ID, GITHUB_APP_PRIVATE_KEY)"
    )


def resolve_repository(repo: str | None = None) -> str:
    value = repo or os.environ.get("GITHUB_REPOSITORY")
    if not value or "/" not in value:
        raise GitHubAPIError(
            "Repository required: pass --repo owner/name or set GITHUB_REPOSITORY"
        )
    return value


def _load_private_key() -> str | None:
    inline = os.environ.get("GITHUB_APP_PRIVATE_KEY")
    if inline:
        return inline.replace("\\n", "\n")
    path = os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH")
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    return None


def app_installation_token(
    *,
    app_id: str,
    private_key: str,
    installation_id: str,
    api_url: str = DEFAULT_API_URL,
) -> str:
    try:
        import jwt
    except ImportError as exc:
        raise GitHubAPIError(
            "GitHub App auth requires pyjwt: pip install 'factory-agents[github]'"
        ) from exc

    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": app_id}
    app_jwt = jwt.encode(payload, private_key, algorithm="RS256")

    url = f"{api_url.rstrip('/')}/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers)
        if response.status_code >= 400:
            raise GitHubAPIError(
                f"installation token failed: {response.status_code} {response.text}",
                status_code=response.status_code,
            )
        data = response.json()
        token = data.get("token")
        if not isinstance(token, str) or not token:
            raise GitHubAPIError("installation token response missing token")
        return token


def check_run_api_body(
    check: CheckRunResult,
    annotations: list[Annotation] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = check.model_dump(exclude_none=True)
    if annotations:
        body["output"]["annotations"] = [
            ann.model_dump(exclude_none=True) for ann in annotations[:MAX_ANNOTATIONS]
        ]
    return body


def create_check_run(
    repo: str,
    check: CheckRunResult,
    *,
    token: str,
    annotations: list[Annotation] | None = None,
    api_url: str = DEFAULT_API_URL,
) -> dict[str, Any]:
    """POST /repos/{owner}/{repo}/check-runs."""
    url = f"{api_url.rstrip('/')}/repos/{repo}/check-runs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = check_run_api_body(check, annotations)
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            raise GitHubAPIError(
                f"create check run failed: {response.status_code} {response.text}",
                status_code=response.status_code,
            )
        data = response.json()
        if not isinstance(data, dict):
            raise GitHubAPIError("create check run returned non-object JSON")
        return data
