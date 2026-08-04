"""Exact evaluators. Brent is production; the full-state set is a test oracle."""

from __future__ import annotations

from collections.abc import Callable

from .model import EvaluationResult

Transition = Callable[[int], int]


def collatz_step(n: int) -> int:
    return n // 2 if n % 2 == 0 else 3 * n + 1


def _cycle_details(start: int, transition: Transition, period: int) -> tuple[int, int]:
    ahead = start
    for _ in range(period):
        ahead = transition(ahead)
    behind, entry = start, 0
    while behind != ahead:
        behind, ahead, entry = transition(behind), transition(ahead), entry + 1
    return entry, behind


def _replay(start: int, transition: Transition, steps: int) -> tuple[int, int]:
    state, maximum = start, start
    for _ in range(steps):
        state = transition(state)
        maximum = max(maximum, state)
    return state, maximum


def evaluate(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None
) -> EvaluationResult:
    """Evaluate exactly using Brent's O(1)-state cycle detector.

    Cycle metrics are replayed and normalized to the first repeated state, making
    results independent of Brent's collision location.
    """
    if start <= 0:
        raise ValueError("start must be positive")
    if max_steps is not None and max_steps < 0:
        raise ValueError("max_steps must be nonnegative")
    if start == 1:
        return EvaluationResult(start, 0, "reached_one", 1)
    if max_steps == 0:
        return EvaluationResult(start, 0, "interrupted", start,
                                stopping_reason="safety_limit", safety_limit_kind="steps",
                                safety_limit_value=0)
    power = period = 1
    tortoise, hare = start, transition(start)
    observed_steps = 1
    maximum = max(start, hare)
    while hare != 1 and tortoise != hare:
        if max_steps is not None and observed_steps >= max_steps:
            return EvaluationResult(start, observed_steps, "interrupted", maximum,
                                    stopping_reason="safety_limit", safety_limit_kind="steps",
                                    safety_limit_value=max_steps)
        if power == period:
            tortoise, power, period = hare, power * 2, 0
        hare = transition(hare)
        observed_steps += 1
        period += 1
        maximum = max(maximum, hare)
    if hare == 1:
        return EvaluationResult(start, observed_steps, "reached_one", maximum)
    entry_step, entry_state = _cycle_details(start, transition, period)
    logical_steps = entry_step + period
    _, logical_maximum = _replay(start, transition, logical_steps)
    return EvaluationResult(start, logical_steps, "repeated_state", logical_maximum,
                            entry_state, entry_step, period, "repeated_state")


def evaluate_hashset(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None
) -> EvaluationResult:
    """Memory-heavy independent oracle retained exclusively for validation."""
    if start <= 0:
        raise ValueError("start must be positive")
    if max_steps is not None and max_steps < 0:
        raise ValueError("max_steps must be nonnegative")
    state, maximum, steps = start, start, 0
    seen: dict[int, int] = {state: 0}
    while state != 1:
        if max_steps is not None and steps >= max_steps:
            return EvaluationResult(start, steps, "interrupted", maximum,
                                    stopping_reason="safety_limit", safety_limit_kind="steps",
                                    safety_limit_value=max_steps)
        state, steps = transition(state), steps + 1
        maximum = max(maximum, state)
        if state in seen:
            entry = seen[state]
            return EvaluationResult(start, steps, "repeated_state", maximum, state, entry,
                                    steps - entry, "repeated_state")
        seen[state] = steps
    return EvaluationResult(start, steps, "reached_one", maximum)
