from __future__ import annotations

import argparse
import json
from pathlib import Path

from .experiment import (
    DEFAULT_CANDIDATE_COUNT,
    STRATEGY,
    SUPPORTED_STRATEGIES,
    run_experiment,
)
from .generator import DEFAULT_DECIMAL_DIGITS, DEFAULT_PREFIX_LENGTH
from .cycle_search import CycleSearchConfig, run_cycle_search


def main() -> None:
    parser = argparse.ArgumentParser(prog="bigcollatz")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run a focused experiment above 1,000,000 digits")
    run.add_argument("experiment_id", help="identifier used for the result directory")
    run.add_argument(
        "--count",
        type=int,
        default=DEFAULT_CANDIDATE_COUNT,
        help=f"distinct candidates to evaluate (default: {DEFAULT_CANDIDATE_COUNT})",
    )
    run.add_argument("--seed", default="baseline-v1")
    run.add_argument(
        "--digits",
        type=int,
        default=DEFAULT_DECIMAL_DIGITS,
        help=f"decimal digits per candidate, more than one million (default: {DEFAULT_DECIMAL_DIGITS})",
    )
    run.add_argument("--strategy", choices=SUPPORTED_STRATEGIES, default=STRATEGY)
    run.add_argument(
        "--prefix-length",
        type=int,
        default=DEFAULT_PREFIX_LENGTH,
        help="parity decisions preserved by S1-S3 strategies (default: 256)",
    )
    run.add_argument(
        "--validate-candidates",
        action="store_true",
        help="verify every guided candidate against its strategy invariant",
    )
    run.add_argument("--output-root", type=Path, default=Path("."))
    cycles = sub.add_parser(
        "search-cycles", help="enumerate exact accelerated-map cycle equations"
    )
    cycles.add_argument("search_id", help="identifier used for the result directory")
    cycles.add_argument("--min-odd-period", type=int, default=1)
    cycles.add_argument("--max-odd-period", type=int, default=12)
    cycles.add_argument("--max-total-divisions", type=int, default=24)
    cycles.add_argument("--shard-index", type=int, default=0)
    cycles.add_argument("--shard-count", type=int, default=1)
    cycles.add_argument("--include-trivial", action="store_true")
    cycles.add_argument("--checkpoint-every", type=int, default=100_000)
    cycles.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    if args.command == "run":
        result = run_experiment(
            args.output_root,
            experiment_id=args.experiment_id,
            count=args.count,
            seed=args.seed,
            strategy=args.strategy,
            prefix_length=args.prefix_length,
            decimal_digits=args.digits,
            validate_candidates=args.validate_candidates,
        )
        print(json.dumps(result["summary"], indent=2))
    elif args.command == "search-cycles":
        result = run_cycle_search(
            args.output_root,
            args.search_id,
            CycleSearchConfig(
                min_odd_period=args.min_odd_period,
                max_odd_period=args.max_odd_period,
                max_total_divisions=args.max_total_divisions,
                shard_index=args.shard_index,
                shard_count=args.shard_count,
                include_trivial=args.include_trivial,
                checkpoint_every=args.checkpoint_every,
            ),
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
