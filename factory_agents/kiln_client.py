"""Invoke kiln as an external hermetic build/verify callee.

kiln CLI (nebucloud/kiln):
  kiln validate <pipeline.json>
  kiln run <pipeline.json> [--cache DIR] [--seal-network] [--no-sandbox]

Pipeline JSON matches kiln-core / ssf pkg/kiln (version \"1\", targets.*.run).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class KilnError(RuntimeError):
    pass


def kiln_binary() -> str | None:
    return shutil.which("kiln")


def kiln_on_path() -> bool:
    return kiln_binary() is not None


def load_pipeline_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_pipeline_schema(pipeline: dict[str, Any]) -> list[str]:
    """Local structural checks mirroring kiln-core basics (no kiln binary needed)."""
    errors: list[str] = []
    version = pipeline.get("version")
    if version != "1" and version != 1:
        errors.append(f"version must be \"1\" (got {version!r})")
    targets = pipeline.get("targets")
    if not isinstance(targets, dict) or not targets:
        errors.append("targets must be a non-empty object")
        return errors
    for name, target in targets.items():
        if not isinstance(target, dict):
            errors.append(f"target {name!r} must be an object")
            continue
        run = target.get("run")
        if not isinstance(run, dict):
            errors.append(f"target {name!r} missing run object")
            continue
        if not run.get("interpreter"):
            errors.append(f"target {name!r} run.interpreter required")
        if not isinstance(run.get("code"), str) or not run.get("code"):
            errors.append(f"target {name!r} run.code required non-empty string")
        for dep in target.get("requires") or []:
            if dep not in targets:
                errors.append(f"target {name!r} requires unknown {dep!r}")
    return errors


def validate_pipeline_file(pipeline_path: Path) -> dict[str, Any]:
    pipeline_path = pipeline_path.resolve()
    if not pipeline_path.is_file():
        raise KilnError(f"pipeline not found: {pipeline_path}")
    pipeline = load_pipeline_json(pipeline_path)
    schema_errors = validate_pipeline_schema(pipeline)
    result: dict[str, Any] = {
        "pipeline": str(pipeline_path),
        "schema_ok": not schema_errors,
        "schema_errors": schema_errors,
        "target_count": len(pipeline.get("targets") or {}),
        "kiln_present": kiln_on_path(),
    }
    if schema_errors:
        result["status"] = "invalid"
        return result

    binary = kiln_binary()
    if not binary:
        result["status"] = "schema_ok"
        result["note"] = (
            "Schema OK; kiln binary not on PATH — install kiln-cli to run "
            "`kiln validate` / `kiln run`."
        )
        return result

    proc = _run_kiln([binary, "validate", str(pipeline_path)])
    result["status"] = "ok" if proc["exit_code"] == 0 else "failed"
    result["exit_code"] = proc["exit_code"]
    result["stdout_tail"] = proc["stdout_tail"]
    result["stderr_tail"] = proc["stderr_tail"]
    return result


def verify(
    pipeline_path: Path,
    *,
    dry_run: bool = True,
    timeout_sec: int = 600,
    cache_dir: Path | None = None,
    seal_network: bool = False,
    no_sandbox: bool = False,
) -> dict[str, Any]:
    """Validate schema, optionally dry-run, or execute `kiln run`."""
    pipeline_path = pipeline_path.resolve()
    if not pipeline_path.is_file():
        raise KilnError(f"pipeline not found: {pipeline_path}")

    pipeline = load_pipeline_json(pipeline_path)
    schema_errors = validate_pipeline_schema(pipeline)
    if schema_errors:
        return {
            "status": "invalid",
            "pipeline": str(pipeline_path),
            "schema_errors": schema_errors,
            "kiln_present": kiln_on_path(),
        }

    if dry_run:
        return {
            "status": "dry_run",
            "pipeline": str(pipeline_path),
            "schema_ok": True,
            "target_count": len(pipeline["targets"]),
            "targets": list(pipeline["targets"].keys()),
            "kiln_present": kiln_on_path(),
            "would_run": ["kiln", "run", str(pipeline_path)]
            + (["--cache", str(cache_dir)] if cache_dir else [])
            + (["--seal-network"] if seal_network else [])
            + (["--no-sandbox"] if no_sandbox else []),
            "note": "kiln is the hermetic build engine; agents call it, they are not kiln.",
        }

    binary = kiln_binary()
    if not binary:
        raise KilnError(
            "kiln binary not found on PATH (cargo install kiln-cli). "
            "Use --dry-run to validate schema only."
        )

    cmd = [binary, "run", str(pipeline_path)]
    if cache_dir:
        cmd.extend(["--cache", str(cache_dir)])
    if seal_network:
        cmd.append("--seal-network")
    if no_sandbox:
        cmd.append("--no-sandbox")

    proc = _run_kiln(cmd, timeout_sec=timeout_sec)
    return {
        "status": "ok" if proc["exit_code"] == 0 else "failed",
        "exit_code": proc["exit_code"],
        "stdout_tail": proc["stdout_tail"],
        "stderr_tail": proc["stderr_tail"],
        "pipeline": str(pipeline_path),
        "command": cmd,
    }


def _run_kiln(cmd: list[str], timeout_sec: int = 600) -> dict[str, Any]:
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
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
    }
