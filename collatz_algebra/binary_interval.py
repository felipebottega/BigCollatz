"""Directed dyadic arithmetic with a separate, arbitrary-size exponent."""

from __future__ import annotations

from dataclasses import dataclass

from .grammar import Concat, Repeat, Step, Word


@dataclass(frozen=True, slots=True)
class Dyadic:
    significand: int
    exponent: int = 0

    @property
    def top(self) -> int:
        return self.significand.bit_length() + self.exponent


_ZERO = Dyadic(0)
_ONE = Dyadic(1)


def _at_exponent(value: Dyadic, exponent: int, up: bool) -> int:
    """Round onto a grid of spacing 2**exponent, without extending a distant tail."""
    shift = value.exponent - exponent
    n = value.significand
    if not n:
        return 0
    if shift >= 0:
        return n << shift
    dropped = -shift
    if dropped >= abs(n).bit_length():
        return int(n > 0) if up else -int(n < 0)
    low = n >> dropped
    return low + int(up and (low << dropped) != n)


def _rounded(n: int, exponent: int, precision: int, up: bool) -> Dyadic:
    drop = max(0, n.bit_length() - precision)
    exponent += drop
    return Dyadic(_at_exponent(Dyadic(n, exponent - drop), exponent, up), exponent)


def _sum(
    left: Dyadic, right: Dyadic, precision: int, up: bool, *, subtract: bool = False
) -> Dyadic:
    if not left.significand:
        n = -right.significand if subtract else right.significand
        return _rounded(n, right.exponent, precision, up)
    if not right.significand:
        return _rounded(left.significand, left.exponent, precision, up)
    exponent = max(left.top, right.top) - precision
    a = _at_exponent(left, exponent, up)
    b = _at_exponent(right, exponent, up != subtract)
    return _rounded(a - b if subtract else a + b, exponent, precision, up)


def _multiply(left: Dyadic, right: Dyadic, precision: int, up: bool) -> Dyadic:
    return _rounded(
        left.significand * right.significand, left.exponent + right.exponent, precision, up
    )


def _divide(numerator: Dyadic, denominator: Dyadic, precision: int, up: bool) -> Dyadic:
    n, d = numerator.significand, denominator.significand
    if not n:
        return _ZERO
    shift = precision + d.bit_length() - n.bit_length()
    quotient, remainder = divmod(n << max(0, shift), d << max(0, -shift))
    return _rounded(
        quotient + int(up and bool(remainder)),
        numerator.exponent - denominator.exponent - shift,
        precision,
        up,
    )


def _affine(word: Word, precision: int, up: bool) -> tuple[Dyadic, Dyadic]:
    def compose(left, right):
        a, b = left
        c, d = right
        return _multiply(c, a, precision, up), _sum(
            _multiply(c, b, precision, up), d, precision, up
        )

    if isinstance(word, Step):
        return Dyadic(3, -word.divisions), Dyadic(1, -word.divisions)
    result = (_ONE, _ZERO)
    if isinstance(word, Concat):
        for part in word.parts:
            result = compose(result, _affine(part, precision, up))
    else:
        base, copies = _affine(word.word, precision, up), word.times
        while copies:
            if copies & 1:
                result = compose(result, base)
            copies >>= 1
            if copies:
                base = compose(base, base)
    return result


@dataclass(frozen=True, slots=True)
class ClosureCandidate:
    start: int | None
    residual_bits: int
    precision: int
    reason: str | None = None


def isolate_candidate(word: Word, divisions: int) -> ClosureCandidate:
    """Isolate the sole possible positive odd fixed point using exact bounds."""
    precision = 64
    while True:
        a_lo, b_lo = _affine(word, precision, False)
        a_hi, b_hi = _affine(word, precision, True)
        denominator_hi = _sum(_ONE, a_lo, precision, True, subtract=True)
        if denominator_hi.significand <= 0:
            return ClosureCandidate(None, 0, precision, "nonpositive_closure_denominator")
        denominator_lo = _sum(_ONE, a_hi, precision, False, subtract=True)
        if denominator_lo.significand > 0:
            lo = _divide(b_lo, denominator_hi, precision, False)
            hi = _divide(b_hi, denominator_lo, precision, True)
            width = _sum(hi, lo, precision, True, subtract=True)
            # Avoid constructing a huge integer candidate before the unit
            # position is resolved. The check only compares a scale.
            if not width.significand or width.top <= 1:
                first = max(1, _at_exponent(lo, 0, True)) | 1
                last = _at_exponent(hi, 0, False)
                if first > last:
                    return ClosureCandidate(None, 0, precision, "nonintegral_closure")
                # D < 2**divisions and |fixed_point - first| <= width.
                bits = max(1, divisions + width.top) if width.significand else 1
                return ClosureCandidate(first, bits, precision)
        precision *= 2
