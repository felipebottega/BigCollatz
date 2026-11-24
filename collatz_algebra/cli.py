"""Command-line entry point for symbolic two-run cycle search."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .sieve import DEFAULT_MINIMUM_PERIOD, DEFAULT_PRIME_LIMIT
from .search import search_cycles


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collatz-algebra",
        description="Generate and evaluate symbolic two-run Collatz cycle patterns",
    )
    parser.add_argument(
        "--search-cycles",
        required=True,
        type=int,
        metavar="MAX_ODD_STEPS",
        help="search symbolic 1^u 2^v representations selected by convergents",
    )
    parser.add_argument(
        "--minimum-period",
        type=int,
        default=DEFAULT_MINIMUM_PERIOD,
        help="minimum unaccelerated period assumed by the research model",
    )
    parser.add_argument(
        "--prime-limit",
        type=int,
        default=DEFAULT_PRIME_LIMIT,
        help="scan primes through this value for divisors of the closure coefficient",
    )
    parser.add_argument("--output", type=Path, help="write JSON report to this file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = search_cycles(
        args.search_cycles,
        minimum_period=args.minimum_period,
        prime_limit=args.prime_limit,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
