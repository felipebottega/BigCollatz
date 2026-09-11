"""Exact algebra for cycles of the accelerated odd Collatz map."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .odd_map import OddCycle, verify_odd_cycle

DEFAULT_FILTER_PRIMES = (5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)


@dataclass(frozen=True, slots=True)
class CycleEquation:
    exponents: tuple[int, ...]
    numerator: int
    denominator: int

    @property
    def candidate(self) -> int | None:
        quotient, remainder = divmod(self.numerator, self.denominator)
        return quotient if remainder == 0 and quotient > 0 and quotient % 2 else None


def compose_cycle_equation(exponents: Iterable[int]) -> CycleEquation:
    """Compose ``(3n+1)/2**a`` steps and solve the resulting closure equation."""
    vector = tuple(exponents)
    if not vector or any(
        not isinstance(value, int) or isinstance(value, bool) or value < 1
        for value in vector
    ):
        raise ValueError("exponents must be positive integers")

    additive = 0
    divisions = 0
    power_of_three = 1
    for exponent in vector:
        additive = 3 * additive + (1 << divisions)
        power_of_three *= 3
        divisions += exponent
    denominator = (1 << divisions) - power_of_three
    if denominator <= 0:
        raise ValueError(
            "a positive cycle requires 2**sum(exponents) > 3**len(exponents)"
        )
    return CycleEquation(vector, additive, denominator)


def solve_cycle_equation(exponents: Iterable[int]) -> OddCycle | None:
    """Return an exact cycle when the exponent vector has an integral solution."""
    equation = compose_cycle_equation(exponents)
    candidate = equation.candidate
    if candidate is None:
        return None
    try:
        return verify_odd_cycle(candidate, equation.exponents)
    except ValueError:
        return None


def passes_modular_filters(
    exponents: tuple[int, ...], primes: tuple[int, ...] = DEFAULT_FILTER_PRIMES
) -> bool:
    """Apply necessary divisibility conditions before constructing large integers.

    If a prime divides ``2**S - 3**k``, it must also divide the additive
    numerator. Primes not dividing the denominator impose no condition.
    """
    if not exponents or any(value < 1 for value in exponents):
        raise ValueError("exponents must be positive integers")
    total = sum(exponents)
    active = [
        prime
        for prime in primes
        if pow(2, total, prime) == pow(3, len(exponents), prime)
    ]
    for prime in active:
        additive = 0
        divisions = 0
        for exponent in exponents:
            additive = (3 * additive + pow(2, divisions, prime)) % prime
            divisions += exponent
        if additive:
            return False
    return True


def least_rotation(values: tuple[int, ...]) -> tuple[int, ...]:
    """Return the lexicographically least rotation using Booth's linear algorithm."""
    if not values:
        raise ValueError("rotation requires a nonempty tuple")
    doubled = values + values
    i, j, offset, length = 0, 1, 0, len(values)
    while i < length and j < length and offset < length:
        left, right = doubled[i + offset], doubled[j + offset]
        if left == right:
            offset += 1
            continue
        if left > right:
            i += offset + 1
            if i == j:
                i += 1
        else:
            j += offset + 1
            if i == j:
                j += 1
        offset = 0
    start = min(i, j)
    return doubled[start : start + length]


def is_primitive(values: tuple[int, ...]) -> bool:
    """Whether ``values`` is not a repetition of a shorter word, in linear time."""
    if not values:
        raise ValueError("primitive-word test requires a nonempty tuple")
    failure = [0] * len(values)
    matched = 0
    for index in range(1, len(values)):
        while matched and values[index] != values[matched]:
            matched = failure[matched - 1]
        if values[index] == values[matched]:
            matched += 1
            failure[index] = matched
    period = len(values) - failure[-1]
    return period == len(values) or len(values) % period != 0
