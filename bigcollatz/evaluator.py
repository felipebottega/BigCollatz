"""Exact Collatz trajectory evaluator with mandatory repeated-state detection."""

from __future__ import annotations

from collections.abc import Callable

from .model import EvaluationResult

Transition = Callable[[int], int]


def collatz_step(n: int) -> int:
    return n // 2 if n % 2 == 0 else 3 * n + 1


def evaluate(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None
) -> EvaluationResult:
    """Evaluate exactly, checking every generated state for exact repetition."""
    if start <= 0:
        raise ValueError("start must be positive")
    if max_steps is not None and max_steps < 0:
        raise ValueError("max_steps must be nonnegative")

    state, maximum, steps = start, start, 0
    seen: dict[int, int] = {start: 0}
    if state == 1:
        return EvaluationResult(start, steps, "reached_one", maximum)

    while True:
        if max_steps is not None and steps >= max_steps:
            return EvaluationResult(
                start, steps, "interrupted", maximum,
                stopping_reason="safety_limit", safety_limit_kind="steps",
                safety_limit_value=max_steps,
            )
        state = transition(state)
        steps += 1
        maximum = max(maximum, state)
        first_seen = seen.get(state)
        if first_seen is not None:
            return EvaluationResult(
                start, steps, "repeated_state", maximum,
                repeated_state=state, cycle_entry_step=first_seen,
                cycle_period=steps - first_seen, stopping_reason="repeated_state",
                repeated_integer=str(state), first_seen_step=first_seen,
                repeated_at_step=steps, cycle_length=steps - first_seen,
            )
        if state == 1:
            return EvaluationResult(start, steps, "reached_one", maximum)
        seen[state] = steps


def evaluate_hashset(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None
) -> EvaluationResult:
    """Backward-compatible alias for the exact mapping evaluator."""
    return evaluate(start, transition=transition, max_steps=max_steps)
