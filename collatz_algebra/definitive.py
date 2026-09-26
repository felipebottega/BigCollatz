"""Exact, definitive verification for bounded compressed Collatz words."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from .grammar import Concat, Repeat, Step, Word, counts

DEFAULT_EXACT_WORK_LIMIT = 1_000_000


@dataclass(frozen=True, slots=True)
class IneligibleCandidate(ValueError):
    """A word whose exact proof would exceed the configured deterministic bound."""

    odd_steps: int
    total_divisions: int
    work_limit: int

    def __str__(self) -> str:
        return (
            "candidate is not eligible for a definitive answer: "
            f"odd_steps={self.odd_steps}, total_divisions={self.total_divisions}, "
            f"exact_work_limit={self.work_limit}"
        )


def iter_exponents(word: Word) -> Iterator[int]:
    """Expand an eligible word lazily, without retaining its exponent vector."""

    if isinstance(word, Step):
        yield word.divisions
    elif isinstance(word, Concat):
        for part in word.parts:
            yield from iter_exponents(part)
    else:
        for _ in range(word.times):
            yield from iter_exponents(word.word)


def verify_exact(
    word: Word, *, work_limit: int = DEFAULT_EXACT_WORK_LIMIT
) -> dict[str, object]:
    """Decide exactly whether a bounded exponent word is a positive Collatz cycle.

    Both the number of odd steps and the total power of two are bounded before any
    affine integer or trajectory is constructed.  Consequently every accepted
    input terminates with either a proof of rejection or a confirmed cycle.
    """

    if (
        isinstance(work_limit, bool)
        or not isinstance(work_limit, int)
        or work_limit < 1
    ):
        raise ValueError("work_limit must be a positive integer")
    odd_steps, total_divisions = counts(word)
    if max(odd_steps, total_divisions) > work_limit:
        raise IneligibleCandidate(odd_steps, total_divisions, work_limit)

    additive = 0
    prefix_divisions = 0
    for exponent in iter_exponents(word):
        additive = 3 * additive + (1 << prefix_divisions)
        prefix_divisions += exponent

    denominator = (1 << total_divisions) - pow(3, odd_steps)
    base = {
        "schema": "collatz-algebra-definitive-v1",
        "method": "exact_boehm_sontacchi_and_2_adic_replay",
        "counts": {
            "odd_steps": str(odd_steps),
            "total_divisions": str(total_divisions),
            "unaccelerated_period": str(odd_steps + total_divisions),
        },
        "definitive": True,
        "exact_work_limit": work_limit,
    }
    if denominator <= 0:
        return {
            **base,
            "is_cycle": False,
            "conclusion": "not_a_cycle",
            "reason": "nonpositive_closure_denominator",
        }
    quotient, remainder = divmod(additive, denominator)
    if remainder:
        return {
            **base,
            "is_cycle": False,
            "conclusion": "not_a_cycle",
            "reason": "nonintegral_closure",
        }
    if quotient <= 0 or quotient % 2 == 0:
        return {
            **base,
            "is_cycle": False,
            "conclusion": "not_a_cycle",
            "reason": "closure_is_not_a_positive_odd_integer",
        }

    start = state = quotient
    for index, exponent in enumerate(iter_exponents(word)):
        value = 3 * state + 1
        actual = (value & -value).bit_length() - 1
        if actual != exponent:
            return {
                **base,
                "is_cycle": False,
                "conclusion": "not_a_cycle",
                "reason": "incorrect_2_adic_valuation",
                "failed_odd_step": str(index),
                "expected_divisions": str(exponent),
                "actual_divisions": str(actual),
            }
        state = value >> exponent
        if state <= 0 or state % 2 == 0:
            return {
                **base,
                "is_cycle": False,
                "conclusion": "not_a_cycle",
                "reason": "invalid_odd_state",
            }

    if state != start:
        return {
            **base,
            "is_cycle": False,
            "conclusion": "not_a_cycle",
            "reason": "word_does_not_close",
        }
    return {
        **base,
        "is_cycle": True,
        "conclusion": (
            "confirmed_trivial_cycle" if start == 1 else "confirmed_nontrivial_cycle"
        ),
        "starting_integer": str(start),
    }
