"""Command-line entry point for the compressed algebraic sieve."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .grammar import parse_word
from .sieve import DEFAULT_MINIMUM_PERIOD, DEFAULT_PRIME_LIMIT, analyze


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collatz-algebra",
        description="Sieve compressed accelerated-Collatz cycle words",
    )
    parser.add_argument("word", type=Path, help="JSON straight-line word grammar")
    parser.add_argument(
        "--minimum-period",
        type=int,
        default=DEFAULT_MINIMUM_PERIOD,
        help="minimum unaccelerated period assumed by the research model",
    )
    parser.add_argument(
        "--modulus",
        type=int,
        action="append",
        help="explicit closure modulus; repeat to use several (disables prime scan)",
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
    document = json.loads(args.word.read_text(encoding="utf-8"))
    word = parse_word(document)
    report = analyze(
        word,
        moduli=args.modulus,
        minimum_period=args.minimum_period,
        prime_limit=args.prime_limit,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if report["rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
