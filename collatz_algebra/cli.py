"""Command-line entry point for definitive compressed-word decisions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .definitive import DEFAULT_EXACT_WORK_LIMIT, IneligibleCandidate, verify_exact
from .grammar import parse_word
from .sieve import DEFAULT_MINIMUM_PERIOD, DEFAULT_PRIME_LIMIT
from .search import search_two_run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collatz-algebra",
        description="Decide eligible compressed accelerated-Collatz cycle words",
    )
    parser.add_argument(
        "word", type=Path, nargs="?", help="JSON straight-line word grammar"
    )
    parser.add_argument(
        "--search-two-run",
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
    parser.add_argument(
        "--exact-work-limit",
        type=int,
        default=DEFAULT_EXACT_WORK_LIMIT,
        help=(
            "accept a WORD only when both its odd-step count and total divisions "
            "fit this exact-verification bound"
        ),
    )
    parser.add_argument("--output", type=Path, help="write JSON report to this file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if (args.word is None) == (args.search_two_run is None):
        _parser().error("supply exactly one of WORD or --search-two-run")
    if args.search_two_run is not None:
        if args.modulus:
            _parser().error("--modulus is only valid with WORD")
        report = search_two_run(
            args.search_two_run,
            minimum_period=args.minimum_period,
            prime_limit=args.prime_limit,
        )
    else:
        document = json.loads(args.word.read_text(encoding="utf-8"))
        word = parse_word(document)
        if args.modulus:
            _parser().error("--modulus is unavailable for definitive WORD verification")
        try:
            report = verify_exact(word, work_limit=args.exact_work_limit)
        except IneligibleCandidate as exc:
            report = {
                "schema": "collatz-algebra-ineligible-v1",
                "definitive": False,
                "conclusion": "not_tested",
                "reason": str(exc),
                "counts": {
                    "odd_steps": str(exc.odd_steps),
                    "total_divisions": str(exc.total_divisions),
                    "unaccelerated_period": str(
                        exc.odd_steps + exc.total_divisions
                    ),
                },
                "exact_work_limit": exc.work_limit,
            }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if report.get("conclusion") == "not_tested":
        return 2
    return 0 if report.get("is_cycle", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
