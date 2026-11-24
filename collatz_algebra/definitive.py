"""Exact cycle decisions by composing compressed exponent words."""

from __future__ import annotations

from .closure_interval import noninteger_closure
from .exact_affine import closure_denominator, evaluate_exact_affine
from .grammar import Repeat, Word, counts


def verify_exact(word: Word) -> dict[str, object]:
    """Decide closure with a certified interval or exact affine division.

    Divisibility by the full power of two implies divisibility at each
    prefix because the remaining multiplier is odd. Each intermediate
    integer is odd because its next update multiplies it by three, adds one,
    and produces an even numerator.
    """
    odd_steps, total_divisions = counts(word)
    # A real affine map with a positive multiplier and any positive power
    # share the same fixed points. A whole-word repeat can therefore be
    # verified by its base, including the exact divisibility of every step.
    while isinstance(word, Repeat):
        word = word.word
    result = {
        "schema": "collatz-algebra-definitive-v2",
        "method": "exact_compressed_affine_closure",
        "counts": {
            "odd_steps": str(odd_steps),
            "total_divisions": str(total_divisions),
            "unaccelerated_period": str(odd_steps + total_divisions),
        },
        "definitive": True,
    }

    interval = noninteger_closure(word)
    if interval is not None:
        return {
            **result,
            "method": "directed_affine_interval",
            "is_cycle": False,
            "conclusion": "not_a_cycle",
            "reason": "nonintegral_closure",
            "closure_interval": interval,
        }

    coefficients = evaluate_exact_affine(word)
    denominator = closure_denominator(coefficients)
    if denominator <= 0:
        return {
            **result, "is_cycle": False, "conclusion": "not_a_cycle",
            "reason": "nonpositive_closure_denominator",
        }
    start, remainder = divmod(coefficients.additive, denominator)
    if remainder:
        return {
            **result, "is_cycle": False, "conclusion": "not_a_cycle",
            "reason": "nonintegral_closure",
        }
    try:
        starting_integer = str(start)
    except ValueError:
        # Python can limit decimal conversion of large integers.
        starting_integer = hex(start)
    return {
        **result,
        "is_cycle": True,
        "conclusion": "confirmed_trivial_cycle" if start == 1 else "confirmed_nontrivial_cycle",
        "starting_integer": starting_integer,
    }
