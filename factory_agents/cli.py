"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from factory_agents import __version__
from factory_agents.github_check import check_run_from_report, parse_github_event
from factory_agents.kiln_client import KilnError, validate_pipeline_file
from factory_agents.kiln_client import verify as kiln_verify
from factory_agents.llm import get_llm
from factory_agents.llm.config import load_settings
from factory_agents.review import run_review
from factory_agents.risk import exit_code_for_risk
from factory_agents.safety import SafetyError, SafetyPolicy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="factory-agents",
        description="Factory AI review agents (never merge). kiln = hermetic callee.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_review = sub.add_parser("review", help="Review a unified diff")
    p_review.add_argument("--diff", type=Path, required=True, help="Path to unified diff")
    p_review.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Allowlist/capabilities dir",
    )
    p_review.add_argument("--json", action="store_true", help="Emit ReviewReport JSON")
    p_review.add_argument(
        "--llm",
        default="none",
        help="LLM backend: none|echo|ollama|openai|vllm (default none)",
    )
    p_review.add_argument(
        "--llm-config",
        type=Path,
        default=None,
        help="Optional TOML (see config/llm.example.toml)",
    )

    p_check = sub.add_parser(
        "check",
        help="Review + emit GitHub Check Run JSON (does not post to API)",
    )
    p_check.add_argument("--diff", type=Path, required=True)
    p_check.add_argument("--sha", default="", help="head SHA (or from --event)")
    p_check.add_argument(
        "--event",
        type=Path,
        default=None,
        help="GitHub event JSON (pull_request)",
    )
    p_check.add_argument("--config-dir", type=Path, default=None)
    p_check.add_argument("--llm", default="none")
    p_check.add_argument("--llm-config", type=Path, default=None)
    p_check.add_argument(
        "--kiln-pipeline",
        type=Path,
        default=None,
        help="Optional kiln pipeline to schema-validate / dry-run",
    )

    p_kiln = sub.add_parser("kiln-verify", help="Validate/run a kiln pipeline JSON")
    p_kiln.add_argument("--pipeline", type=Path, required=True)
    p_kiln.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Schema + plan only (default). Use --no-dry-run to execute kiln.",
    )
    p_kiln.add_argument("--cache", type=Path, default=None, help="kiln --cache DIR")
    p_kiln.add_argument("--seal-network", action="store_true")
    p_kiln.add_argument("--no-sandbox", action="store_true")

    p_val = sub.add_parser("kiln-validate", help="Schema + kiln validate")
    p_val.add_argument("--pipeline", type=Path, required=True)

    args = parser.parse_args(argv)

    try:
        if args.cmd == "review":
            return _cmd_review(args)
        if args.cmd == "check":
            return _cmd_check(args)
        if args.cmd == "kiln-verify":
            return _cmd_kiln(args)
        if args.cmd == "kiln-validate":
            return _cmd_kiln_validate(args)
    except (SafetyError, KilnError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


def _policy(config_dir: Path | None) -> SafetyPolicy:
    if config_dir:
        return SafetyPolicy.from_config_dir(config_dir)
    return SafetyPolicy()


def _llm(args: argparse.Namespace):
    settings = load_settings(
        backend=args.llm,
        config_path=getattr(args, "llm_config", None),
    )
    return get_llm(args.llm, settings=settings)


def _cmd_review(args: argparse.Namespace) -> int:
    text = args.diff.read_text(encoding="utf-8")
    report = run_review(text, policy=_policy(args.config_dir), llm=_llm(args))
    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print(report.summary)
        for f in report.findings:
            loc = f.path or "?"
            if f.line:
                loc = f"{loc}:{f.line}"
            print(f"  [{f.risk.value}] {f.id} {loc} — {f.title}")
    return exit_code_for_risk(report.risk_max)


def _cmd_check(args: argparse.Namespace) -> int:
    sha = args.sha
    if args.event:
        event = json.loads(args.event.read_text(encoding="utf-8"))
        ref = parse_github_event(event)
        if ref and ref.head_sha:
            sha = sha or ref.head_sha
    if not sha:
        sha = "0000000000000000000000000000000000000000"

    text = args.diff.read_text(encoding="utf-8")
    report = run_review(text, policy=_policy(args.config_dir), llm=_llm(args))

    kiln_info = None
    if args.kiln_pipeline:
        kiln_info = kiln_verify(args.kiln_pipeline, dry_run=True)
        report.kiln_verify = kiln_info

    check = check_run_from_report(report, head_sha=sha)
    payload = check.model_dump(exclude_none=True)
    if kiln_info is not None:
        payload["kiln_verify"] = kiln_info
    print(json.dumps(payload, indent=2))

    code = exit_code_for_risk(report.risk_max)
    if kiln_info and kiln_info.get("status") == "invalid":
        return 1
    return code


def _cmd_kiln(args: argparse.Namespace) -> int:
    result = kiln_verify(
        args.pipeline,
        dry_run=args.dry_run,
        cache_dir=args.cache,
        seal_network=args.seal_network,
        no_sandbox=args.no_sandbox,
    )
    print(json.dumps(result, indent=2))
    if result.get("status") in ("failed", "invalid"):
        return 1
    return 0


def _cmd_kiln_validate(args: argparse.Namespace) -> int:
    result = validate_pipeline_file(args.pipeline)
    print(json.dumps(result, indent=2))
    if result.get("status") in ("failed", "invalid"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
