from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cycle_search import CycleSearchConfig, run_cycle_search


def main() -> None:
    parser = argparse.ArgumentParser(prog="bigcollatz")
    sub = parser.add_subparsers(dest="command", required=True)
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
