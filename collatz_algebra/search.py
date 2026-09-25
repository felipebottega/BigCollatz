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


def _reject_one_cycle_family(report: dict[str, object], u: int, v: int) -> None:
    """Apply Steiner's one-cycle theorem to ``1**u 2**v``.

    For an odd member greater than one, exponent 1 is a strict increase and
    exponent 2 is a strict decrease.  Hence this word has exactly one local
    minimum and one local maximum.  Steiner proved that a positive Collatz
    cycle of this type is necessarily the trivial cycle.  The trivial cycle
    has word ``[2]`` and is not in this family because ``u`` and ``v`` are both
    positive.
    """

    certificate = {
        "filter": "steiner_one_cycle_theorem",
        "rigorous": True,
        "family": "1^u 2^v",
        "one_run": str(u),
        "two_run": str(v),
        "reason": "a nontrivial positive 1-cycle does not exist",
        "reference": "Steiner, A theorem on the Syracuse problem (1977)",
    }
    reasons = report["rejection_certificates"]
    assert isinstance(reasons, list)
    reasons.append(certificate)
    report["rejected"] = True
    report["conclusion"] = "impossible_one_cycle_family"


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
        # Every member produced by this search has one increasing and one
        # decreasing run.  This theorem closes the gap left by finite modular
        # tests, including cases where no small prime divides 2**S - 3**k.
        _reject_one_cycle_family(
            report,
            2 * odd_steps - total_divisions,
            total_divisions - odd_steps,
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
        "family_eliminated_by": "Steiner one-cycle theorem (1977)",
        "trajectory_terms_computed": False,
        "candidates": candidates,
    }
