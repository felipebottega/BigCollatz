"""Exact confirmation of materializable accelerated Collatz cycle words.

Modular sieving can reject a word but cannot confirm one.  Confirmation requires
constructing the exact closure candidate and replaying every prescribed odd
step.  This module makes that boundary explicit and returns a resource-limit
result instead of mislabelling an unverified survivor.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterator

from .grammar import Concat, Repeat, Step, Word, counts


class ConfirmationStatus(str, Enum):
    CONFIRMED = "confirmed_cycle"
    REJECTED = "rejected"
    RESOURCE_LIMIT = "resource_limit"


@dataclass(frozen=True, slots=True)
class ExactAffine:
    """Exact numerator data for ``(multiplier*n + additive)/denominator``."""

    multiplier: int
    additive: int
    denominator: int


def _compose(left: ExactAffine, right: ExactAffine) -> ExactAffine:
    return ExactAffine(
        multiplier=right.multiplier * left.multiplier,
        additive=(
            right.multiplier * left.additive
            + right.additive * left.denominator
        ),
        denominator=right.denominator * left.denominator,
    )


def _power(value: ExactAffine, exponent: int) -> ExactAffine:
    result = ExactAffine(1, 0, 1)
    base = value
    while exponent:
        if exponent & 1:
            result = _compose(result, base)
        exponent >>= 1
        if exponent:
            base = _compose(base, base)
    return result


def exact_affine(word: Word) -> ExactAffine:
    """Build the exact affine transformation for a materializable word."""

    if isinstance(word, Step):
        return ExactAffine(3, 1, 1 << word.divisions)
    if isinstance(word, Concat):
        result = ExactAffine(1, 0, 1)
        for part in word.parts:
            result = _compose(result, exact_affine(part))
        return result
    return _power(exact_affine(word.word), word.times)


def iter_exponents(word: Word) -> Iterator[int]:
    """Expand a word lazily; callers must enforce an odd-step budget first."""

    if isinstance(word, Step):
        yield word.divisions
    elif isinstance(word, Concat):
        for part in word.parts:
            yield from iter_exponents(part)
    else:
        for _ in range(word.times):
            yield from iter_exponents(word.word)


def _estimated_bits(odd_steps: int, total_divisions: int) -> int:
    # 3**k has ceil(k*log2(3)) bits.  8/5 is a rigorous convenient upper
    # bound for log2(3), avoiding floating-point decisions at the budget edge.
    multiplier_bits = (8 * odd_steps + 4) // 5 + 1
    return max(multiplier_bits, total_divisions + 1)


def confirm(
    word: Word,
    *,
    max_odd_steps: int = 1_000_000,
    max_integer_bits: int = 8_000_000,
) -> dict[str, object]:
    """Construct and replay a cycle, or explain why confirmation did not occur.

    ``confirmed_cycle`` is returned only after exact closure, exact exponent
    validation at every accelerated step, return to the initial integer, and a
    primitiveness check.  A resource limit is neither success nor rejection.
    """

    for value, name in (
        (max_odd_steps, "max_odd_steps"),
        (max_integer_bits, "max_integer_bits"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")

    odd_steps, total_divisions = counts(word)
    estimated_bits = _estimated_bits(odd_steps, total_divisions)
    common = {
        "odd_steps": str(odd_steps),
        "total_divisions": str(total_divisions),
        "unaccelerated_period": str(odd_steps + total_divisions),
        "estimated_exact_integer_bits": str(estimated_bits),
    }
    exceeded = []
    if odd_steps > max_odd_steps:
        exceeded.append("max_odd_steps")
    if estimated_bits > max_integer_bits:
        exceeded.append("max_integer_bits")
    if exceeded:
        return {
            "status": ConfirmationStatus.RESOURCE_LIMIT.value,
            "confirmed": False,
            "exceeded": exceeded,
            **common,
        }

    affine = exact_affine(word)
    closure_denominator = affine.denominator - affine.multiplier
    if closure_denominator <= 0:
        return {
            "status": ConfirmationStatus.REJECTED.value,
            "confirmed": False,
            "reason": "nonpositive_closure_denominator",
            **common,
        }
    quotient, remainder = divmod(affine.additive, closure_denominator)
    if remainder:
        return {
            "status": ConfirmationStatus.REJECTED.value,
            "confirmed": False,
            "reason": "nonintegral_closure_candidate",
            "remainder": str(remainder),
            **common,
        }
    if quotient < 1 or quotient % 2 == 0:
        return {
            "status": ConfirmationStatus.REJECTED.value,
            "confirmed": False,
            "reason": "closure_candidate_is_not_positive_odd",
            "starting_integer": str(quotient),
            **common,
        }

    initial = current = quotient
    seen = {initial}
    for index, expected_divisions in enumerate(iter_exponents(word), start=1):
        value = 3 * current + 1
        actual_divisions = (value & -value).bit_length() - 1
        if actual_divisions != expected_divisions:
            return {
                "status": ConfirmationStatus.REJECTED.value,
                "confirmed": False,
                "reason": "exponent_mismatch",
                "odd_step_index": str(index),
                "expected_divisions": str(expected_divisions),
                "actual_divisions": str(actual_divisions),
                **common,
            }
        current = value >> actual_divisions
        if current == initial:
            if index != odd_steps:
                return {
                    "status": ConfirmationStatus.REJECTED.value,
                    "confirmed": False,
                    "reason": "imprimitive_word",
                    "shorter_odd_period": str(index),
                    **common,
                }
        elif current in seen:
            return {
                "status": ConfirmationStatus.REJECTED.value,
                "confirmed": False,
                "reason": "repeated_member_before_closure",
                "odd_step_index": str(index),
                **common,
            }
        seen.add(current)

    if current != initial:
        return {
            "status": ConfirmationStatus.REJECTED.value,
            "confirmed": False,
            "reason": "failed_exact_return",
            **common,
        }
    return {
        "status": ConfirmationStatus.CONFIRMED.value,
        "confirmed": True,
        "trivial": initial == 1 and odd_steps == 1,
        "starting_integer": str(initial),
        "minimum_member": str(min(seen)),
        "maximum_member": str(max(seen)),
        **common,
    }
