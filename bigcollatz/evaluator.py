"""Exact Collatz trajectory evaluator with mandatory repeated-state detection."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .model import EvaluationResult

Transition = Callable[[int], int]


@dataclass(frozen=True)
class EvaluationMetrics:
    odd_step_count: int
    odd_step_density: tuple[int, int]
    first_descent_step: int | None
    maximum_excursion_numerator: int
    maximum_excursion_denominator: int
    same_decimal_digit_band_return_count: int
    repeated_residue_hit_count: int
    residue_modulus: int


def collatz_step(n: int) -> int:
    return n // 2 if n % 2 == 0 else 3 * n + 1


def _evaluate_engine(start: int, *, transition: Transition = collatz_step, max_steps: int | None = None, collect_metrics: bool = False, residue_modulus: int = 1024) -> tuple[EvaluationResult, EvaluationMetrics | None]:
    """Single authoritative trajectory loop for exact evaluation and optional metrics."""
    if start <= 0:
        raise ValueError("start must be positive")
    if max_steps is not None and max_steps < 0:
        raise ValueError("max_steps must be nonnegative")
    if residue_modulus < 2:
        raise ValueError("residue_modulus must be at least 2")

    state, maximum, steps = start, start, 0
    seen: dict[int, int] = {start: 0}
    residue_hits: set[int] = {start % residue_modulus}
    repeated_residue_hit_count = 0
    odd_step_count = 0
    first_descent_step: int | None = None
    same_decimal_digit_band_return_count = 0
    start_digits = len(str(start))

    def metrics() -> EvaluationMetrics | None:
        if not collect_metrics:
            return None
        return EvaluationMetrics(
            odd_step_count=odd_step_count,
            odd_step_density=(odd_step_count, steps),
            first_descent_step=first_descent_step,
            maximum_excursion_numerator=maximum,
            maximum_excursion_denominator=start,
            same_decimal_digit_band_return_count=same_decimal_digit_band_return_count,
            repeated_residue_hit_count=repeated_residue_hit_count,
            residue_modulus=residue_modulus,
        )

    if state == 1:
        return EvaluationResult(start, steps, "reached_one", maximum), metrics()

    while True:
        if max_steps is not None and steps >= max_steps:
            return EvaluationResult(
                start, steps, "interrupted", maximum,
                stopping_reason="safety_limit", safety_limit_kind="steps",
                safety_limit_value=max_steps,
            ), metrics()
        if state & 1:
            odd_step_count += 1
        state = transition(state)
        steps += 1
        maximum = max(maximum, state)
        if first_descent_step is None and state < start:
            first_descent_step = steps
        if state != start and len(str(state)) == start_digits:
            same_decimal_digit_band_return_count += 1
        residue = state % residue_modulus
        if residue in residue_hits:
            repeated_residue_hit_count += 1
        else:
            residue_hits.add(residue)
        first_seen = seen.get(state)
        if first_seen is not None:
            return EvaluationResult(
                start, steps, "repeated_state", maximum,
                repeated_state=state, cycle_entry_step=first_seen,
                cycle_period=steps - first_seen, stopping_reason="repeated_state",
                repeated_integer=str(state), first_seen_step=first_seen,
                repeated_at_step=steps, cycle_length=steps - first_seen,
            ), metrics()
        if state == 1:
            return EvaluationResult(start, steps, "reached_one", maximum), metrics()
        seen[state] = steps


def evaluate(start: int, *, transition: Transition = collatz_step, max_steps: int | None = None) -> EvaluationResult:
    """Evaluate exactly, checking every generated state for exact repetition."""
    result, _ = _evaluate_engine(start, transition=transition, max_steps=max_steps, collect_metrics=False)
    return result


def evaluate_with_metrics(start: int, *, transition: Transition = collatz_step, max_steps: int | None = None, residue_modulus: int = 1024) -> tuple[EvaluationResult, EvaluationMetrics]:
    """Evaluate with compact metrics while preserving the exact EvaluationResult."""
    result, metrics = _evaluate_engine(start, transition=transition, max_steps=max_steps, collect_metrics=True, residue_modulus=residue_modulus)
    assert metrics is not None
    return result, metrics


def evaluate_hashset(start: int, *, transition: Transition = collatz_step, max_steps: int | None = None) -> EvaluationResult:
    """Backward-compatible alias for the exact mapping evaluator."""
    return evaluate(start, transition=transition, max_steps=max_steps)
