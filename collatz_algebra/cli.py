"""Command-line entry point for Monte Carlo cycle search."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .modular_closure import DEFAULT_MODULUS_BITS
from .search import DEFAULT_CASES_PER_LEVEL, DEFAULT_DEPTH, search_cycles
from .sieve import DEFAULT_PRIME_LIMIT


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collatz-algebra",
        description="Generate and evaluate Collatz cycle patterns with Monte Carlo search",
    )
    parser.add_argument(
        "--search-cycles",
        required=True,
        type=int,
        metavar="MAX_ODD_STEPS",
        help="maximum odd steps per candidate",
    )
    parser.add_argument(
        "--cases-per-level", type=int, default=DEFAULT_CASES_PER_LEVEL,
        help="maximum number of distinct candidates evaluated per level",
    )
    parser.add_argument(
        "--depth", type=int, default=DEFAULT_DEPTH,
        help="number of search levels",
    )
    parser.add_argument("--seed", type=int, default=0, help="seed for reproducible sampling")
    parser.add_argument(
        "--independent-runs", action="store_true",
        help="sample arbitrary individual downhill exponents without requiring an anchor",
    )
    parser.add_argument(
        "--prime-limit",
        type=int,
        default=DEFAULT_PRIME_LIMIT,
        help="scan primes through this value for divisors of the closure coefficient",
    )
    parser.add_argument(
        "--modulus-bits", type=int, default=DEFAULT_MODULUS_BITS,
        help="target size of each prime-power modulus in the exact closure proof",
    )
    parser.add_argument(
        "--checkpoint-dir", type=Path,
        help="save modular proof progress and resume it when rerunning the same search",
    )
    parser.add_argument("--output", type=Path, help="write JSON report to this file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        report = search_cycles(
            args.search_cycles,
            cases_per_level=args.cases_per_level,
            depth=args.depth,
            seed=args.seed,
            prime_limit=args.prime_limit,
            independent_runs=args.independent_runs,
            modulus_bits=args.modulus_bits,
            checkpoint_dir=args.checkpoint_dir,
        )
    except ValueError as error:
        parser.error(str(error))
    except KeyboardInterrupt:
        print("Search interrupted before a complete report was produced.", file=sys.stderr)
        return 130
    except OSError as error:
        print(f"Could not access modular checkpoint: {error}", file=sys.stderr)
        return 1
    except (MemoryError, OverflowError):
        print(
            "Exact search could not finish within this process's arithmetic or memory capacity.",
            file=sys.stderr,
        )
        return 1
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
