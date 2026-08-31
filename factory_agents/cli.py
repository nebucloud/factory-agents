"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from factory_agents import __version__
from factory_agents.kiln_client import KilnError
from factory_agents.kiln_client import verify as kiln_verify
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

    p_review = sub.add_parser("review", help="Review a unified diff (heuristic; no LLM yet)")
    p_review.add_argument("--diff", type=Path, required=True, help="Path to unified diff")
    p_review.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Allowlist/capabilities dir",
    )
    p_review.add_argument("--json", action="store_true", help="Emit ReviewReport JSON")

    p_kiln = sub.add_parser("kiln-verify", help="Call kiln run on a pipeline JSON (optional)")
    p_kiln.add_argument("--pipeline", type=Path, required=True)
    p_kiln.add_argument("--dry-run", action="store_true", default=True)
    p_kiln.add_argument("--execute", action="store_true", help="Actually invoke kiln (not dry-run)")

    args = parser.parse_args(argv)

    try:
        if args.cmd == "review":
            return _cmd_review(args)
        if args.cmd == "kiln-verify":
            return _cmd_kiln(args)
    except (SafetyError, KilnError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


def _cmd_review(args: argparse.Namespace) -> int:
    diff_path: Path = args.diff
    text = diff_path.read_text(encoding="utf-8")
    if args.config_dir:
        policy = SafetyPolicy.from_config_dir(args.config_dir)
    else:
        policy = SafetyPolicy()
    report = run_review(text, policy=policy)
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


def _cmd_kiln(args: argparse.Namespace) -> int:
    dry = not args.execute
    result = kiln_verify(args.pipeline, dry_run=dry)
    print(json.dumps(result, indent=2))
    if result.get("status") == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
