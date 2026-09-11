"""Accelerated Collatz map on positive odd integers."""

from __future__ import annotations

from dataclasses import dataclass


def trailing_zero_count(value: int) -> int:
    """Return v_2(value) for a positive integer without converting it to text."""
    if value <= 0:
        raise ValueError("value must be positive")
    return (value & -value).bit_length() - 1


def odd_step(value: int) -> tuple[int, int]:
    """Return the next odd Collatz value and the exact number of divisions by two."""
    if value <= 0 or value % 2 == 0:
        raise ValueError("odd_step requires a positive odd integer")
    expanded = 3 * value + 1
    exponent = trailing_zero_count(expanded)
    return expanded >> exponent, exponent


@dataclass(frozen=True, slots=True)
class OddCycle:
    """An exactly verified cycle represented by its odd members and exponents."""

    members: tuple[int, ...]
    exponents: tuple[int, ...]

    @property
    def unaccelerated_period(self) -> int:
        return len(self.members) + sum(self.exponents)


def verify_odd_cycle(start: int, exponents: tuple[int, ...]) -> OddCycle:
    """Replay an exponent vector exactly and require it to close at ``start``."""
    if start <= 0 or start % 2 == 0:
        raise ValueError("cycle start must be a positive odd integer")
    if not exponents or any(
        not isinstance(value, int) or isinstance(value, bool) or value < 1
        for value in exponents
    ):
        raise ValueError("exponents must be a nonempty tuple of positive integers")

    members: list[int] = []
    seen: set[int] = set()
    state = start
    for expected in exponents:
        if state in seen:
            raise ValueError("exponent vector contains a shorter cycle")
        members.append(state)
        seen.add(state)
        state, observed = odd_step(state)
        if observed != expected:
            raise ValueError("declared exponent does not match the exact odd step")
    if state != start:
        raise ValueError("exponent vector does not close")
    return OddCycle(tuple(members), exponents)
