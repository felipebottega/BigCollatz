"""Exact nonintegrality certificates using directed decimal enclosures."""

from __future__ import annotations

from decimal import (
    MAX_EMAX, MIN_EMIN, Context, Decimal, DecimalException, ROUND_CEILING, ROUND_FLOOR,
)

from .grammar import Concat, Repeat, Step, Word


_ZERO = Decimal(0)
_ONE = Decimal(1)
_HALF = Decimal("0.5")
_THREE = Decimal(3)
Affine = tuple[Decimal, Decimal]


def _power_of_half(exponent: int, context: Context) -> Decimal:
    # Use correctly rounded multiplication. Decimal's general power
    # operation does not guarantee directed rounding on all backends.
    result, base = _ONE, _HALF
    while exponent:
        if exponent & 1:
            result = context.multiply(result, base)
        exponent >>= 1
        if exponent:
            base = context.multiply(base, base)
    return result


def _compose(left: Affine, right: Affine, context: Context) -> Affine:
    a, b = left
    c, d = right
    return context.multiply(c, a), context.add(context.multiply(c, b), d)


def _affine(word: Word, context: Context) -> Affine:
    # Normalized affine coefficients are nonnegative, so every composition
    # is monotone in every operand and preserves the directed enclosure.
    if isinstance(word, Step):
        additive = _power_of_half(word.divisions, context)
        return context.multiply(_THREE, additive), additive
    result = (_ONE, _ZERO)
    if isinstance(word, Concat):
        for part in word.parts:
            result = _compose(result, _affine(part, context), context)
        return result
    base, copies = _affine(word.word, context), word.times
    while copies:
        if copies & 1:
            result = _compose(result, base, context)
        copies >>= 1
        if copies:
            base = _compose(base, base, context)
    return result


def noninteger_closure(word: Word) -> dict[str, str | int] | None:
    """Prove the full affine fixed point lies strictly between integers.

    An inconclusive enclosure leaves the verdict to exact integer closure.
    """
    for precision in (48, 96):
        down = Context(prec=precision, rounding=ROUND_FLOOR, Emin=MIN_EMIN, Emax=MAX_EMAX)
        up = Context(prec=precision, rounding=ROUND_CEILING, Emin=MIN_EMIN, Emax=MAX_EMAX)
        try:
            a_lo, b_lo = _affine(word, down)
            a_hi, b_hi = _affine(word, up)
            denominator_lo = down.subtract(_ONE, a_hi)
            if denominator_lo <= 0:
                continue
            lower = down.divide(b_lo, up.subtract(_ONE, a_lo))
            upper = up.divide(b_hi, denominator_lo)
            floor = lower.to_integral_value(rounding=ROUND_FLOOR, context=down)
            if floor < lower and upper.to_integral_value(rounding=ROUND_FLOOR, context=up) == floor:
                return {
                    "precision": precision,
                    "lower": str(lower),
                    "upper": str(upper),
                    "integer_below": str(floor),
                }
        except DecimalException:
            # Exponent range and precision are not search cutoffs.
            continue
    return None
