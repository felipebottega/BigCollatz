from __future__ import annotations

import argparse
import json
from pathlib import Path

from .experiment import run_pilot


def main() -> None:
    parser = argparse.ArgumentParser(prog="bigcollatz")
    sub = parser.add_subparsers(dest="command", required=True)
    pilot = sub.add_parser("pilot", help="run deterministic P0 pilot and benchmark")
    pilot.add_argument("--per-digit", type=int, default=40)
    pilot.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    if args.command == "pilot":
        print(json.dumps(run_pilot(args.output_root, per_digit=args.per_digit)["summary"], indent=2))


if __name__ == "__main__":
    main()
