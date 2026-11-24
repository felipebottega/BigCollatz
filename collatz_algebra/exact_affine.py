"""Exact affine composition for the large-coefficient closure path."""

from __future__ import annotations

from dataclasses import dataclass

from .grammar import Concat, Repeat, Step, Word

try:
    from gmpy2 import mpz as _integer
except ImportError:
    _integer = int


@dataclass(frozen=True, slots=True)
class ExactAffine:
    multiplier: int
    additive: int
    divisions: int


def _compose(left: ExactAffine, right: ExactAffine) -> ExactAffine:
    return ExactAffine(
        right.multiplier * left.multiplier,
        right.multiplier * left.additive + (right.additive << left.divisions),
        left.divisions + right.divisions,
    )


def evaluate_exact_affine(word: Word) -> ExactAffine:
    """Combine balanced blocks and store the power-of-two denominator by exponent."""
    if isinstance(word, Step):
        return ExactAffine(_integer(3), _integer(1), word.divisions)
    if isinstance(word, Concat):
        def fold(start: int, stop: int) -> ExactAffine:
            if stop - start == 1:
                return evaluate_exact_affine(word.parts[start])
            middle = (start + stop) // 2
            return _compose(fold(start, middle), fold(middle, stop))

        return fold(0, len(word.parts))
    base = evaluate_exact_affine(word.word)
    result = ExactAffine(_integer(1), _integer(0), 0)
    copies = word.times
    while copies:
        if copies & 1:
            result = _compose(result, base)
        copies >>= 1
        if copies:
            base = _compose(base, base)
    return result


def closure_denominator(coefficients: ExactAffine) -> int:
    return (_integer(1) << coefficients.divisions) - coefficients.multiplier
