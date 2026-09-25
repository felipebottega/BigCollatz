"""Symbolic searches for compressed cycle representations.

The search space is made of *descriptions*, not starting integers.  In the
two-run family ``1**u 2**v`` the exponents are stored as two grammar nodes even
when ``u + v`` is enormous.  Continued fractions select ratios close to the
necessary boundary ``S/k = log_2(3)`` without walking through all values of
``k``.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Iterator

from .grammar import Concat, Repeat, Step, Word
from .sieve import analyze


def boundary_convergents(max_odd_steps: int) -> Iterator[tuple[int, int]]:
    """Yield reduced ``(k, S)`` convergents above ``log_2(3)``.

    Decimal arithmetic only proposes representations.  Every rejection is
    subsequently made by exact integer or modular tests in :func:`analyze`.
    Thus rounding here can affect coverage, but can never create a proof.
    """

    if (
        isinstance(max_odd_steps, bool)
        or not isinstance(max_odd_steps, int)
        or max_odd_steps < 1
    ):
        raise ValueError("max_odd_steps must be a positive integer")
    with localcontext() as context:
        context.prec = max(80, len(str(max_odd_steps)) * 3)
        boundary = Decimal(3).ln() / Decimal(2).ln()
        value = boundary
        p0, p1, q0, q1 = 0, 1, 1, 0
        seen: set[tuple[int, int]] = set()
        while True:
            coefficient = int(value)
            p0, p1 = p1, coefficient * p1 + p0
            q0, q1 = q1, coefficient * q1 + q0
            if q1 > max_odd_steps:
                break
            pair = (q1, p1)
            # This is candidate selection, not a proof predicate (see docstring).
            if pair not in seen and Decimal(p1) / Decimal(q1) > boundary:
                seen.add(pair)
                yield pair
            remainder = value - coefficient
            if not remainder:
                break
            value = 1 / remainder


def two_run_word(odd_steps: int, total_divisions: int) -> Word:
    """Represent the exponent word ``1**u 2**v`` without expansion."""

    v = total_divisions - odd_steps
    u = 2 * odd_steps - total_divisions
    if u < 1 or v < 1:
        raise ValueError("two-run family requires k < S < 2*k")
    return Concat((Repeat(Step(1), u), Repeat(Step(2), v)))


def search_two_run(
    max_odd_steps: int,
    *,
    minimum_period: int = 1,
    prime_limit: int = 10_000,
) -> dict[str, object]:
    """Sieve continued-fraction members of a symbolic two-run family."""

    candidates = []
    for odd_steps, total_divisions in boundary_convergents(max_odd_steps):
        if not odd_steps < total_divisions < 2 * odd_steps:
            continue
        word = two_run_word(odd_steps, total_divisions)
        report = analyze(
            word,
            minimum_period=minimum_period,
            prime_limit=prime_limit,
        )
        candidates.append(
            {
                "parameters": {
                    "odd_steps": str(odd_steps),
                    "total_divisions": str(total_divisions),
                    "one_run": str(2 * odd_steps - total_divisions),
                    "two_run": str(total_divisions - odd_steps),
                },
                "status": "rejected" if report["rejected"] else "symbolic_candidate",
                "analysis": report,
            }
        )
    return {
        "schema": "collatz-symbolic-search-v1",
        "family": "1^u 2^v",
        "selection": "upper continued-fraction convergents of log_2(3)",
        "coverage_is_exhaustive": False,
        "trajectory_terms_computed": False,
        "candidates": candidates,
    }
