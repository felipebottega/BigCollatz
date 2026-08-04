"""Exact Collatz trajectory evaluator with optional recurrence metrics."""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

from .model import EvaluationResult

Transition = Callable[[int], int]


@dataclass(frozen=True, slots=True)
class RecurrenceMetrics:
    """Compact heuristic metrics collected by the exact trajectory engine.

    Definitions: odd_step_count counts transitions taken from odd states; density is
    odd_step_count / total steps (0 when no steps execute); first_descent_step is the
    first step whose generated state is below the start; maximum excursion is the exact
    ratio max_state/start stored as numerator/denominator; same_decimal_digit_band_return_count
    counts generated states with the same decimal digit count as the start after leaving
    that band; repeated_residue_hit_count counts repeated residues in a bounded LRU window.
    These are heuristic scoring signals only; exact state repetition remains authoritative.
    """

    odd_step_count: int
    odd_step_density: Fraction
    first_descent_step: int | None
    maximum_excursion_numerator: int
    maximum_excursion_denominator: int
    same_decimal_digit_band_return_count: int
    repeated_residue_hit_count: int
    residue_modulus: int


@dataclass(frozen=True, slots=True)
class MetricEvaluation:
    result: EvaluationResult
    metrics: RecurrenceMetrics


def collatz_step(n: int) -> int:
    return n // 2 if n % 2 == 0 else 3 * n + 1


def _trajectory_engine(
    start: int,
    *,
    transition: Transition = collatz_step,
    max_steps: int | None = None,
    collect_metrics: bool = False,
    residue_modulus: int = 65536,
    residue_window: int = 4096,
) -> tuple[EvaluationResult, RecurrenceMetrics | None]:
    if start <= 0:
        raise ValueError("start must be positive")
    if max_steps is not None and max_steps < 0:
        raise ValueError("max_steps must be nonnegative")
    if residue_modulus < 2 or residue_window < 1:
        raise ValueError("residue metric parameters are invalid")

    state, maximum, steps = start, start, 0
    seen: dict[int, int] = {start: 0}
    odd_steps = 0
    first_descent = None
    start_digits = len(str(start))
    band_low = 10 ** (start_digits - 1)
    band_high = 10 ** start_digits
    left_digit_band = False
    same_band_returns = 0
    residue_hits = 0
    residues: Counter[int] = Counter()
    residue_queue: deque[int] = deque()

    def remember_residue(value: int) -> None:
        nonlocal residue_hits
        residue = value % residue_modulus
        if residues[residue] > 0:
            residue_hits += 1
        residues[residue] += 1
        residue_queue.append(residue)
        if len(residue_queue) > residue_window:
            old = residue_queue.popleft()
            residues[old] -= 1
            if residues[old] <= 0:
                del residues[old]

    if collect_metrics:
        remember_residue(start)

    def metrics() -> RecurrenceMetrics | None:
        if not collect_metrics:
            return None
        frac = Fraction(maximum, start)
        return RecurrenceMetrics(
            odd_step_count=odd_steps,
            odd_step_density=Fraction(odd_steps, steps) if steps else Fraction(0, 1),
            first_descent_step=first_descent,
            maximum_excursion_numerator=frac.numerator,
            maximum_excursion_denominator=frac.denominator,
            same_decimal_digit_band_return_count=same_band_returns,
            repeated_residue_hit_count=residue_hits,
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
            odd_steps += 1
        state = transition(state)
        steps += 1
        maximum = max(maximum, state)
        if first_descent is None and state < start:
            first_descent = steps
        if collect_metrics:
            in_start_band = band_low <= state < band_high
            if not in_start_band:
                left_digit_band = True
            elif left_digit_band:
                same_band_returns += 1
            remember_residue(state)
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
    result, _ = _trajectory_engine(start, transition=transition, max_steps=max_steps, collect_metrics=False)
    return result


def evaluate_with_metrics(
    start: int, *, transition: Transition = collatz_step, max_steps: int | None = None,
    residue_modulus: int = 65536, residue_window: int = 4096,
) -> MetricEvaluation:
    """Evaluate via the same exact engine and return compact heuristic metrics."""
    result, metrics = _trajectory_engine(
        start, transition=transition, max_steps=max_steps, collect_metrics=True,
        residue_modulus=residue_modulus, residue_window=residue_window,
    )
    assert metrics is not None
    return MetricEvaluation(result, metrics)


def evaluate_hashset(start: int, *, transition: Transition = collatz_step, max_steps: int | None = None) -> EvaluationResult:
    """Backward-compatible alias for the exact mapping evaluator."""
    return evaluate(start, transition=transition, max_steps=max_steps)
