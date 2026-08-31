"""Allowlists and capability gates — merge/push-to-protected always denied."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Hard denials — cannot be enabled via config.
HARD_DENIED_CAPABILITIES = frozenset(
    {
        "git.merge",
        "git.push_main",
        "git.push_protected",
        "registry.promote",
        "argo.sync",
    }
)


class SafetyError(RuntimeError):
    pass


class SafetyPolicy:
    def __init__(
        self,
        *,
        allowed_path_globs: list[str] | None = None,
        denied_path_globs: list[str] | None = None,
        capabilities: set[str] | None = None,
    ):
        self.allowed_path_globs = allowed_path_globs or ["**/*"]
        self.denied_path_globs = denied_path_globs or [
            "**/.env",
            "**/.env.*",
            "**/cosign.key",
            "**/*credential*",
            "**/*secret*",
        ]
        caps = set(capabilities or {"review.read_diff", "review.write_report"})
        illegal = caps & HARD_DENIED_CAPABILITIES
        if illegal:
            raise SafetyError(f"capabilities hard-denied: {sorted(illegal)}")
        self.capabilities = caps

    @classmethod
    def from_config_dir(cls, config_dir: Path) -> SafetyPolicy:
        allow_path = config_dir / "allowlist.json"
        cap_path = config_dir / "capabilities.json"
        allowed: list[str] = ["**/*"]
        denied: list[str] = []
        caps: set[str] = {"review.read_diff", "review.write_report"}
        if allow_path.is_file():
            data = json.loads(allow_path.read_text(encoding="utf-8"))
            allowed = list(data.get("allowed_path_globs") or allowed)
            denied = list(data.get("denied_path_globs") or denied)
        if cap_path.is_file():
            data = json.loads(cap_path.read_text(encoding="utf-8"))
            caps = set(data.get("capabilities") or caps)
        return cls(
            allowed_path_globs=allowed,
            denied_path_globs=denied,
            capabilities=caps,
        )

    def require(self, capability: str) -> None:
        if capability in HARD_DENIED_CAPABILITIES:
            raise SafetyError(f"capability hard-denied: {capability}")
        if capability not in self.capabilities:
            raise SafetyError(f"capability not granted: {capability}")

    def path_allowed(self, path: str) -> bool:
        norm = path
        while norm.startswith("./"):
            norm = norm[2:]
        if any(_glob_match(g, norm) for g in self.denied_path_globs):
            return False
        return any(_glob_match(g, norm) for g in self.allowed_path_globs)

    def assert_no_merge(self) -> None:
        """Explicit guard for any code path that might apply changes."""
        self.require("review.write_report")  # must at least be a review context
        for banned in HARD_DENIED_CAPABILITIES:
            if banned in self.capabilities:
                raise SafetyError(f"capability hard-denied: {banned}")


def _glob_match(pattern: str, path: str) -> bool:
    """Minimal ** / * glob match for path allowlists."""
    # Escape then translate glob to regex
    regex = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            regex += "(.*/)?"
            i += 3
        elif pattern[i] == "*":
            regex += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            regex += "[^/]"
            i += 1
        else:
            regex += re.escape(pattern[i])
            i += 1
    return re.fullmatch(regex, path) is not None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
