"""Exact and modular affine evaluation of compressed exponent words."""

from __future__ import annotations

from dataclasses import dataclass

from .grammar import Concat, Repeat, Step, Word


@dataclass(frozen=True, slots=True)
class AffineResidue:
    """Residues for ``T(n) = (multiplier*n + additive) / denominator``."""

    multiplier: int
    additive: int
    denominator: int


def compose(
    left: AffineResidue, right: AffineResidue, modulus: int | None = None
) -> AffineResidue:
    """Compose words in trajectory order: apply left, then right."""
    multiplier = right.multiplier * left.multiplier
    additive = right.multiplier * left.additive + right.additive * left.denominator
    denominator = right.denominator * left.denominator
    if modulus is not None:
        multiplier %= modulus
        additive %= modulus
        denominator %= modulus
    return AffineResidue(multiplier, additive, denominator)


def _power(value: AffineResidue, exponent: int, modulus: int | None) -> AffineResidue:
    result = AffineResidue(1, 0, 1)
    base = value
    while exponent:
        if exponent & 1:
            result = compose(result, base, modulus)
        exponent >>= 1
        if exponent:
            base = compose(base, base, modulus)
    return result


def _evaluate(word: Word, modulus: int | None) -> AffineResidue:
    if isinstance(word, Step):
        if modulus is None:
            return AffineResidue(3, 1, 1 << word.divisions)
        return AffineResidue(3 % modulus, 1, pow(2, word.divisions, modulus))
    if isinstance(word, Concat):
        result = AffineResidue(1, 0, 1)
        for part in word.parts:
            result = compose(result, _evaluate(part, modulus), modulus)
        return result
    return _power(_evaluate(word.word, modulus), word.times, modulus)


def evaluate_affine(word: Word) -> AffineResidue:
    """Compute exact coefficients without expanding repetitions."""
    return _evaluate(word, None)


def evaluate_mod(word: Word, modulus: int) -> AffineResidue:
    """Evaluate a word modulo modulus without expanding repetitions."""
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus < 2:
        raise ValueError("modulus must be an integer of at least 2")
    return _evaluate(word, modulus)
