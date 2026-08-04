"""Exact Collatz trajectory evaluator with mandatory repeated-state detection."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

from .model import EvaluationResult

Transition = Callable[[int], int]

@dataclass(frozen=True)
class RecurrenceMetrics:
    odd_step_count: int
    odd_step_density: float
    first_descent_step: int | None
    maximum_excursion_numerator: int
    maximum_excursion_denominator: int
    same_decimal_digit_band_return_count: int
    repeated_residue_hit_count: int
    residue_modulus: int

@dataclass(frozen=True)
class MetricEvaluation:
    result: EvaluationResult
    metrics: RecurrenceMetrics



def collatz_step(n: int) -> int:
    return n // 2 if n % 2 == 0 else 3 * n + 1


def _trajectory_engine(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None, collect_metrics: bool = False, residue_modulus: int = 1024
) -> EvaluationResult | MetricEvaluation:
    """Authoritative exact trajectory loop; optionally collects compact metrics."""
    if start <= 0:
        raise ValueError("start must be positive")
    if max_steps is not None and max_steps < 0:
        raise ValueError("max_steps must be nonnegative")

    state, maximum, steps = start, start, 0
    seen: dict[int, int] = {start: 0}
    odd_steps = 0
    first_descent_step = None
    start_digits = len(str(start))
    band_returns = 0
    residues: set[int] = {start % residue_modulus}
    residue_hits = 0

    def finish(result: EvaluationResult) -> EvaluationResult | MetricEvaluation:
        if not collect_metrics:
            return result
        metrics = RecurrenceMetrics(
            odd_step_count=odd_steps,
            odd_step_density=(odd_steps / result.total_steps_executed) if result.total_steps_executed else 0.0,
            first_descent_step=first_descent_step,
            maximum_excursion_numerator=maximum,
            maximum_excursion_denominator=start,
            same_decimal_digit_band_return_count=band_returns,
            repeated_residue_hit_count=residue_hits,
            residue_modulus=residue_modulus,
        )
        return MetricEvaluation(result, metrics)

    if state == 1:
        return finish(EvaluationResult(start, steps, "reached_one", maximum))

    while True:
        if max_steps is not None and steps >= max_steps:
            return finish(EvaluationResult(
                start, steps, "interrupted", maximum,
                stopping_reason="safety_limit", safety_limit_kind="steps",
                safety_limit_value=max_steps,
            ))
        was_odd = state & 1
        state = transition(state)
        steps += 1
        odd_steps += int(was_odd)
        maximum = max(maximum, state)
        if first_descent_step is None and state < start:
            first_descent_step = steps
        if state != start and len(str(state)) == start_digits:
            band_returns += 1
        residue = state % residue_modulus
        if residue in residues:
            residue_hits += 1
        else:
            residues.add(residue)
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


def evaluate_hashset(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None
) -> EvaluationResult:
    """Backward-compatible alias for the exact mapping evaluator."""
    return evaluate(start, transition=transition, max_steps=max_steps)


def evaluate(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None
) -> EvaluationResult:
    return _trajectory_engine(start, transition=transition, max_steps=max_steps, collect_metrics=False)  # type: ignore[return-value]

def evaluate_with_metrics(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None, residue_modulus: int = 1024
) -> MetricEvaluation:
    return _trajectory_engine(start, transition=transition, max_steps=max_steps, collect_metrics=True, residue_modulus=residue_modulus)  # type: ignore[return-value]
