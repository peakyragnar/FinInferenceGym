"""CLI entry point: `uv run python -m fingym.operator report`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fingym.operator.report import print_report

DEFAULT_SCOREBOARD_PATH: Path = Path("data_cache") / "scoreboard.jsonl"
DEFAULT_L3_DIR: Path = Path("memory_registry") / "promoted"
DEFAULT_L2_DIR: Path = Path("memory_registry") / "probationary"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fingym.operator",
        description="Read-only operator view of the FinInferenceGym system state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    report_parser = sub.add_parser(
        "report",
        help="Print the full operator report (Scoreboard + attribution + memory + gate log).",
    )
    report_parser.add_argument(
        "--scoreboard-path",
        type=Path,
        default=DEFAULT_SCOREBOARD_PATH,
        help=f"Path to the Scoreboard JSONL file. Default: {DEFAULT_SCOREBOARD_PATH}.",
    )
    report_parser.add_argument(
        "--l3-dir",
        type=Path,
        default=DEFAULT_L3_DIR,
        help=f"Directory holding L3 promoted-skill YAMLs. Default: {DEFAULT_L3_DIR}.",
    )
    report_parser.add_argument(
        "--l2-dir",
        type=Path,
        default=DEFAULT_L2_DIR,
        help=f"Directory holding L2 probationary-skill YAMLs. Default: {DEFAULT_L2_DIR}.",
    )

    args = parser.parse_args(argv)
    if args.command == "report":
        print_report(
            scoreboard_path=args.scoreboard_path,
            l3_dir=args.l3_dir,
            l2_dir=args.l2_dir,
        )
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
