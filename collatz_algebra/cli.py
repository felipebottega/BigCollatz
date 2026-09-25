"""Command-line entry point for the compressed algebraic sieve."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .grammar import parse_word
from .confirmation import ConfirmationStatus, confirm
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
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="construct and replay an exact candidate after sieving",
    )
    parser.add_argument("--max-confirm-odd-steps", type=int, default=1_000_000)
    parser.add_argument("--max-confirm-integer-bits", type=int, default=8_000_000)
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
    if args.confirm:
        report["confirmation"] = confirm(
            word,
            max_odd_steps=args.max_confirm_odd_steps,
            max_integer_bits=args.max_confirm_integer_bits,
        )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if report["rejected"]:
        return 1
    if args.confirm:
        status = report["confirmation"]["status"]
        if status == ConfirmationStatus.CONFIRMED.value:
            return 0
        return 2 if status == ConfirmationStatus.RESOURCE_LIMIT.value else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
