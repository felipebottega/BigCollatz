"""Exact Collatz trajectory evaluator with mandatory repeated-state detection."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

from .model import EvaluationResult

Transition = Callable[[int], int]


def collatz_step(n: int) -> int:
    return n // 2 if n % 2 == 0 else 3 * n + 1


@dataclass(frozen=True)
class EvaluationMetrics:
    """Compact exact/heuristic metrics collected by the shared evaluator engine."""

    odd_step_count: int
    odd_step_density: Fraction
    first_descent_step: int | None
    maximum_excursion_numerator: int
    maximum_excursion_denominator: int
    same_decimal_digit_band_return_count: int
    repeated_residue_hit_count: int
    residue_modulus: int


def _evaluate_engine(
    start: int,
    *,
    transition: Transition = collatz_step,
    max_steps: int | None = None,
    collect_metrics: bool = False,
    residue_modulus: int = 2**16 + 1,
) -> EvaluationResult | tuple[EvaluationResult, EvaluationMetrics]:
    """Single authoritative trajectory loop for all exact evaluation modes."""
    if start <= 0:
        raise ValueError("start must be positive")
    if max_steps is not None and max_steps < 0:
        raise ValueError("max_steps must be nonnegative")

    state, maximum, steps = start, start, 0
    seen: dict[int, int] = {start: 0}
    odd_steps = 0
    first_descent_step: int | None = None
    digit_band = len(str(start))
    same_band_returns = 0
    residue_seen = {start % residue_modulus}
    residue_hits = 0

    def finish(result: EvaluationResult) -> EvaluationResult | tuple[EvaluationResult, EvaluationMetrics]:
        if not collect_metrics:
            return result
        metrics = EvaluationMetrics(
            odd_step_count=odd_steps,
            odd_step_density=Fraction(odd_steps, steps) if steps else Fraction(0, 1),
            first_descent_step=first_descent_step,
            maximum_excursion_numerator=maximum,
            maximum_excursion_denominator=start,
            same_decimal_digit_band_return_count=same_band_returns,
            repeated_residue_hit_count=residue_hits,
            residue_modulus=residue_modulus,
        )
        return result, metrics

    if state == 1:
        return finish(EvaluationResult(start, steps, "reached_one", maximum))

    while True:
        if max_steps is not None and steps >= max_steps:
            return finish(EvaluationResult(
                start, steps, "interrupted", maximum,
                stopping_reason="safety_limit", safety_limit_kind="steps",
                safety_limit_value=max_steps,
            ))
        previous = state
        if previous & 1:
            odd_steps += 1
        state = transition(state)
        steps += 1
        maximum = max(maximum, state)
        if first_descent_step is None and state < start:
            first_descent_step = steps
        if len(str(state)) == digit_band and steps > 0:
            same_band_returns += 1
        residue = state % residue_modulus
        if residue in residue_seen:
            residue_hits += 1
        else:
            residue_seen.add(residue)
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
    result = _evaluate_engine(start, transition=transition, max_steps=max_steps, collect_metrics=False)
    assert isinstance(result, EvaluationResult)
    return result


def evaluate_with_metrics(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None
) -> tuple[EvaluationResult, EvaluationMetrics]:
    """Evaluate with compact metrics from the same authoritative trajectory loop."""
    result = _evaluate_engine(start, transition=transition, max_steps=max_steps, collect_metrics=True)
    assert isinstance(result, tuple)
    return result


def evaluate_hashset(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None
) -> EvaluationResult:
    """Backward-compatible alias for the exact mapping evaluator."""
    return evaluate(start, transition=transition, max_steps=max_steps)
