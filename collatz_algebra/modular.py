"""Modular affine evaluation of compressed exponent words."""

from __future__ import annotations

from dataclasses import dataclass

from .grammar import Concat, Repeat, Step, Word


@dataclass(frozen=True, slots=True)
class AffineResidue:
    """Residues for ``T(n) = (multiplier*n + additive) / denominator``."""

    multiplier: int
    additive: int
    denominator: int


def _identity(modulus: int) -> AffineResidue:
    return AffineResidue(1 % modulus, 0, 1 % modulus)


def compose(
    left: AffineResidue, right: AffineResidue, modulus: int
) -> AffineResidue:
    """Compose words in trajectory order: apply ``left``, then ``right``."""

    return AffineResidue(
        multiplier=right.multiplier * left.multiplier % modulus,
        additive=(
            right.multiplier * left.additive
            + right.additive * left.denominator
        )
        % modulus,
        denominator=right.denominator * left.denominator % modulus,
    )


def _power(value: AffineResidue, exponent: int, modulus: int) -> AffineResidue:
    result = _identity(modulus)
    base = value
    while exponent:
        if exponent & 1:
            result = compose(result, base, modulus)
        base = compose(base, base, modulus)
        exponent >>= 1
    return result


def evaluate_mod(word: Word, modulus: int) -> AffineResidue:
    """Evaluate a word modulo ``modulus`` without expanding repetitions."""

    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus < 2:
        raise ValueError("modulus must be an integer of at least 2")
    if isinstance(word, Step):
        return AffineResidue(3 % modulus, 1 % modulus, pow(2, word.divisions, modulus))
    if isinstance(word, Concat):
        result = _identity(modulus)
        for part in word.parts:
            result = compose(result, evaluate_mod(part, modulus), modulus)
        return result
    return _power(evaluate_mod(word.word, modulus), word.times, modulus)
