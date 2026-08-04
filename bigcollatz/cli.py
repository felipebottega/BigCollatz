from __future__ import annotations

import argparse
import json
from pathlib import Path

from .experiment import DEFAULT_CANDIDATE_COUNT, run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(prog="bigcollatz")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run a sequential 1000-digit experiment")
    run.add_argument("experiment_id", help="identifier used for the result directory")
    run.add_argument("--count", type=int, default=DEFAULT_CANDIDATE_COUNT,
                     help=f"distinct candidates to evaluate (default: {DEFAULT_CANDIDATE_COUNT})")
    run.add_argument("--seed", default="baseline-v1")
    run.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    if args.command == "run":
        result = run_experiment(args.output_root, experiment_id=args.experiment_id,
                                count=args.count, seed=args.seed)
        print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
