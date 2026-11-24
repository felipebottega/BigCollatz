"""Rational certificates and sampling windows for Collatz step counts."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from math import ceil
from random import Random


MINIMUM_CYCLE_MEMBER = 1 << 71
MINIMUM_ODD_STEPS = 72_057_431_991


@cache
def log_bounds(value: int, terms: int = 100) -> tuple[Fraction, Fraction]:
    """Enclose ln(value) via the atanh series and a geometric tail bound."""
    z = Fraction(value - 1, value + 1)
    lower = 2 * sum(z ** (2 * j + 1) / (2 * j + 1) for j in range(terms))
    tail = 2 * z ** (2 * terms + 1) / ((2 * terms + 1) * (1 - z * z))
    return lower, lower + tail


def lower_log_gap(k: int, divisions: int) -> Fraction:
    ln2_lower, _ = log_bounds(2)
    _, ln3_upper = log_bounds(3)
    return divisions * ln2_lower - k * ln3_upper


def run_gap_bound(runs: int) -> Fraction:
    """Hercher's Corollary 17 in odd-to-odd step conventions."""
    return Fraction(97 * runs, 162 * MINIMUM_CYCLE_MEMBER)


def _farey_neighbors(value: Fraction, ceiling: int) -> tuple[Fraction, Fraction]:
    """Bracket a rational by consecutive fractions of order ceiling."""
    numerator, denominator = value.numerator, value.denominator
    p0, q0, p1, q1 = 0, 1, 1, 0
    while denominator:
        quotient, remainder = divmod(numerator, denominator)
        next_q = q0 + quotient * q1
        if next_q > ceiling:
            break
        p0, q0, p1, q1 = p1, q1, p0 + quotient * p1, next_q
        numerator, denominator = denominator, remainder
    if not denominator:
        # The midpoint must lie strictly inside the bracketing interval.
        return value, value
    steps = (ceiling - q0) // q1
    first, second = Fraction(p0 + steps * p1, q0 + steps * q1), Fraction(p1, q1)
    return min(first, second), max(first, second)


@dataclass(frozen=True, slots=True)
class CountWindow:
    ceiling: int
    lower: Fraction
    upper: Fraction
    lower_negative_gap: Fraction
    upper_positive_gap: Fraction
    gap_limit: Fraction

    @property
    def excluded(self) -> bool:
        return self.upper_positive_gap >= self.gap_limit

    def sample(self, rng: Random) -> tuple[int, int]:
        """Sample lattice pairs with a lower gap bound below the run limit."""
        left, right = self.lower, self.upper
        max_t = int(self.gap_limit / self.lower_negative_gap)
        max_b = min(
            ceil(self.gap_limit / self.upper_positive_gap) - 1,
            (self.ceiling + max_t * left.denominator) // right.denominator,
        )
        for _ in range(8):
            b = rng.randint(1, max_b)
            t_min = max(0, (b * right.denominator - self.ceiling + left.denominator - 1)
                        // left.denominator)
            t_max = min(
                (b * right.denominator - MINIMUM_ODD_STEPS) // left.denominator,
                ceil((self.gap_limit - b * self.upper_positive_gap) / self.lower_negative_gap) - 1,
            )
            if t_min <= t_max:
                t = rng.randint(t_min, t_max)
                return (
                    b * right.denominator - t * left.denominator,
                    b * right.numerator - t * left.numerator,
                )
        # The upper neighbor has the smallest certified positive gap.
        return right.denominator, right.numerator


def count_window(ceiling: int, max_runs: int) -> CountWindow:
    terms = 100
    while True:
        ln2_low, ln2_high = log_bounds(2, terms)
        ln3_low, ln3_high = log_bounds(3, terms)
        alpha_low, alpha_high = ln3_low / ln2_high, ln3_high / ln2_low
        left, right = _farey_neighbors((alpha_low + alpha_high) / 2, ceiling)
        if left < alpha_low <= alpha_high < right:
            return CountWindow(
                ceiling, left, right,
                left.denominator * ln3_low - left.numerator * ln2_high,
                right.numerator * ln2_low - right.denominator * ln3_high,
                run_gap_bound(max_runs),
            )
        terms *= 2
