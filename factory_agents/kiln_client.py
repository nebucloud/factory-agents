"""Invoke kiln as an external hermetic build/verify callee."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class KilnError(RuntimeError):
    pass


def kiln_on_path() -> bool:
    return shutil.which("kiln") is not None


def verify(
    pipeline_path: Path,
    *,
    dry_run: bool = True,
    timeout_sec: int = 600,
) -> dict[str, Any]:
    """
    Run `kiln run` against a JSON pipeline manifest.

    dry_run=True records intent without executing when kiln is missing or
    when --dry-run is requested by the CLI.
    """
    pipeline_path = pipeline_path.resolve()
    if not pipeline_path.is_file():
        raise KilnError(f"pipeline not found: {pipeline_path}")

    if dry_run or not kiln_on_path():
        return {
            "status": "dry_run",
            "pipeline": str(pipeline_path),
            "kiln_present": kiln_on_path(),
            "note": "kiln is the hermetic build engine; agents call it, they are not kiln.",
        }

    cmd = ["kiln", "run", str(pipeline_path)]
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except FileNotFoundError as exc:
        raise KilnError("kiln binary not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise KilnError(f"kiln timed out after {timeout_sec}s") from exc

    return {
        "status": "ok" if proc.returncode == 0 else "failed",
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
        "pipeline": str(pipeline_path),
    }


def load_pipeline_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
