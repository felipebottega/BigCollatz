"""Exact Collatz trajectory evaluator with mandatory repeated-state detection."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .model import EvaluationResult

Transition = Callable[[int], int]


@dataclass(frozen=True, slots=True)
class RecurrenceMetrics:
    """Compact metrics collected by the authoritative evaluator loop."""

    odd_step_count: int
    odd_step_density: float
    first_descent_step: int | None
    maximum_excursion_ratio: float
    same_decimal_digit_band_return_count: int
    residue_modulus: int
    repeated_residue_hit_count: int


@dataclass(frozen=True, slots=True)
class EvaluationWithMetrics:
    result: EvaluationResult
    metrics: RecurrenceMetrics


def collatz_step(n: int) -> int:
    return n // 2 if n % 2 == 0 else 3 * n + 1


def _decimal_digit_band(n: int) -> int:
    return len(str(n))


def _evaluate_engine(
    start: int,
    *,
    transition: Transition = collatz_step,
    max_steps: int | None = None,
    collect_metrics: bool = False,
    residue_modulus: int = 65537,
) -> EvaluationResult | EvaluationWithMetrics:
    """Single authoritative trajectory loop for normal and metric-enabled evaluation."""
    if start <= 0:
        raise ValueError("start must be positive")
    if max_steps is not None and max_steps < 0:
        raise ValueError("max_steps must be nonnegative")
    if residue_modulus < 2:
        raise ValueError("residue_modulus must be at least 2")

    state, maximum, steps = start, start, 0
    seen: dict[int, int] = {start: 0}
    odd_step_count = 0
    first_descent_step: int | None = None
    start_band = _decimal_digit_band(start)
    same_band_returns = 0
    seen_residues = {start % residue_modulus} if collect_metrics else set()
    repeated_residue_hits = 0

    def finish(result: EvaluationResult) -> EvaluationResult | EvaluationWithMetrics:
        if not collect_metrics:
            return result
        metrics = RecurrenceMetrics(
            odd_step_count=odd_step_count,
            odd_step_density=(odd_step_count / steps) if steps else 0.0,
            first_descent_step=first_descent_step,
            maximum_excursion_ratio=maximum / start,
            same_decimal_digit_band_return_count=same_band_returns,
            residue_modulus=residue_modulus,
            repeated_residue_hit_count=repeated_residue_hits,
        )
        return EvaluationWithMetrics(result=result, metrics=metrics)

    if state == 1:
        return finish(EvaluationResult(start, steps, "reached_one", maximum))

    while True:
        if max_steps is not None and steps >= max_steps:
            return finish(EvaluationResult(
                start, steps, "interrupted", maximum,
                stopping_reason="safety_limit", safety_limit_kind="steps",
                safety_limit_value=max_steps,
            ))
        if state % 2:
            odd_step_count += 1
        state = transition(state)
        steps += 1
        maximum = max(maximum, state)
        if first_descent_step is None and state < start:
            first_descent_step = steps
        if collect_metrics:
            if steps > 0 and state != start and _decimal_digit_band(state) == start_band:
                same_band_returns += 1
            residue = state % residue_modulus
            if residue in seen_residues:
                repeated_residue_hits += 1
            else:
                seen_residues.add(residue)
        first_seen = seen.get(state)
        if first_seen is not None:
            return finish(EvaluationResult(
                start, steps, "repeated_state", maximum,
                repeated_state=state, cycle_entry_step=first_seen,
                cycle_period=steps - first_seen, stopping_reason="repeated_state",
                repeated_integer=str(state), first_seen_step=first_seen,
                repeated_at_step=steps, cycle_length=steps - first_seen,
            ))
        if state == 1:
            return finish(EvaluationResult(start, steps, "reached_one", maximum))
        seen[state] = steps


def evaluate(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None
) -> EvaluationResult:
    """Evaluate exactly, checking every generated state for exact repetition."""
    result = _evaluate_engine(start, transition=transition, max_steps=max_steps)
    assert isinstance(result, EvaluationResult)
    return result


def evaluate_with_metrics(
    start: int,
    *,
    transition: Transition = collatz_step,
    max_steps: int | None = None,
    residue_modulus: int = 65537,
) -> EvaluationWithMetrics:
    """Evaluate through the shared loop while collecting compact recurrence metrics."""
    result = _evaluate_engine(
        start, transition=transition, max_steps=max_steps,
        collect_metrics=True, residue_modulus=residue_modulus,
    )
    assert isinstance(result, EvaluationWithMetrics)
    return result


def evaluate_hashset(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None
) -> EvaluationResult:
    """Backward-compatible alias for the exact mapping evaluator."""
    return evaluate(start, transition=transition, max_steps=max_steps)
