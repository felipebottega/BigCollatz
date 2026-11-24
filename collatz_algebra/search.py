"""Sample and refine compressed Collatz cycle patterns."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from functools import cache
from random import Random
from typing import Iterator

from .definitive import verify_exact
from .grammar import Concat, Repeat, Step, Word
from .sieve import DEFAULT_PRIME_LIMIT, MINIMUM_NONTRIVIAL_PERIOD, analyze, targeted_moduli


def boundary_convergents(max_odd_steps: int) -> Iterator[tuple[int, int]]:
    """Yield reduced ``(k, S)`` convergents above ``log_2(3)``.

    Decimal arithmetic only proposes representations.  Every rejection is
    subsequently made by exact integer or modular tests in :func:`analyze`.
    Thus rounding here can affect coverage, but can never create a proof.
    """

    if (
        isinstance(max_odd_steps, bool)
        or not isinstance(max_odd_steps, int)
        or max_odd_steps < 1
    ):
        raise ValueError("max_odd_steps must be a positive integer")
    with localcontext() as context:
        context.prec = max(80, len(str(max_odd_steps)) * 3)
        boundary = Decimal(3).ln() / Decimal(2).ln()
        value = boundary
        p0, p1, q0, q1 = 0, 1, 1, 0
        seen: set[tuple[int, int]] = set()
        while True:
            coefficient = int(value)
            p0, p1 = p1, coefficient * p1 + p0
            q0, q1 = q1, coefficient * q1 + q0
            if q1 > max_odd_steps:
                break
            pair = (q1, p1)
            # This is candidate selection, not a proof predicate (see docstring).
            if pair not in seen and Decimal(p1) / Decimal(q1) > boundary:
                seen.add(pair)
                yield pair
            remainder = value - coefficient
            if not remainder:
                break
            value = 1 / remainder


def two_run_word(odd_steps: int, total_divisions: int) -> Word:
    """Represent the exponent word ``1**u 2**v`` without expansion."""

    v = total_divisions - odd_steps
    u = 2 * odd_steps - total_divisions
    if u < 1 or v < 1:
        raise ValueError("two-run family requires k < S < 2*k")
    return Concat((Repeat(Step(1), u), Repeat(Step(2), v)))


DEFAULT_CASES_PER_LEVEL = 24
DEFAULT_DEPTH = 3

# Neighboring fractions enclosing the necessary interval for S/k.
# See the lower-bound proof in ALGEBRAIC_PROJECT.md.
_LOWER = Fraction(103_768_467_013, 65_470_613_321)
_UPPER = Fraction(10_439_860_591, 6_586_818_670)
_MIN_ODD_STEPS = _LOWER.denominator + _UPPER.denominator
_MIN_RUNS = 128
_MAX_RUNS = 256
_MAX_DIVISIONS = 8
_SHORT_UPHILL = 70
_SHORT_DOWNHILL = 40
_MINIMUM_CYCLE_MEMBER = 1 << 71


@dataclass(frozen=True, order=True, slots=True)
class Run:
    uphill: int
    downhill_divisions: int
    downhill: int


Pattern = tuple[Run, ...]


@dataclass(frozen=True, slots=True)
class RankedPattern:
    identifier: int
    pattern: Pattern
    slope: Fraction


def _sample_counts(
    rng: Random, ceiling: int, near: tuple[int, int] | None = None
) -> tuple[int, int]:
    """Sample lattice points near the necessary closure interval.

    Decimal arithmetic guides sampling only. The sieve uses integer and
    modular predicates for rejection.
    """
    left_k, right_k = _LOWER.denominator, _UPPER.denominator
    with localcontext() as context:
        context.prec = max(80, len(str(ceiling)) * 3)
        ln2 = Decimal(2).ln()
        lower = Decimal(3).ln() / ln2
        upper = lower + 1 / (3 * _MINIMUM_CYCLE_MEMBER * ln2)
        min_ratio = (lower * left_k - _LOWER.numerator) / (
            _UPPER.numerator - lower * right_k
        )
        max_ratio = (upper * left_k - _LOWER.numerator) / (
            _UPPER.numerator - upper * right_k
        )
        # Leave enough room for at least one copy of the upper fraction.
        max_a = (ceiling - right_k) // left_k
        if near is None:
            a = rng.randint(1, max_a)
        else:
            k, divisions = near
            current_a = _UPPER.numerator * k - right_k * divisions
            a = rng.randint(max(1, current_a - 1), min(max_a, current_a + 1))
        b_min = int(min_ratio * a) + 1
        b_max = min(int(max_ratio * a), (ceiling - a * left_k) // right_k)
        if b_min > b_max:
            if near is not None:
                return near
            # The mediant fits at every supported ceiling.
            a = b = 1
        else:
            b = rng.randint(b_min, b_max)
    return a * left_k + b * right_k, a * _LOWER.numerator + b * _UPPER.numerator


def _split(rng: Random, total: int, parts: int) -> list[int]:
    cuts = [0, *sorted(rng.randrange(total + 1) for _ in range(parts - 1)), total]
    return [right - left for left, right in zip(cuts, cuts[1:])]


def _sample_pattern(rng: Random, ceiling: int) -> Pattern:
    k, divisions = _sample_counts(rng, ceiling)
    run_count = rng.randint(_MIN_RUNS, _MAX_RUNS)
    max_divisions = rng.randint(2, _MAX_DIVISIONS)
    # Keep one valley between short runs. Long stretches on both sides can
    # force the odd term at the valley to be enormous by divisibility alone.
    short_uphill = rng.randint(1, _SHORT_UPHILL)
    short_downhill = rng.randint(1, _SHORT_DOWNHILL)
    exponents = [2, 2, max_divisions]
    exponents.extend(rng.randint(2, max_divisions) for _ in range(run_count - 3))
    weights = [d - 1 for d in exponents[:-1]]
    extra = divisions - k - short_downhill * (exponents[-1] - 1) - sum(weights)
    allocations = _split(rng, extra, run_count - 1)
    downhill = [1 + share // weight for share, weight in zip(allocations, weights)]
    downhill[0] += sum(share % weight for share, weight in zip(allocations, weights))
    downhill.append(short_downhill)
    remaining_uphill = k - sum(downhill) - short_uphill - (run_count - 1)
    uphill = [short_uphill, *[steps + 1 for steps in _split(rng, remaining_uphill, run_count - 1)]]
    return tuple(Run(u, d, w) for u, d, w in zip(uphill, exponents, downhill))


def _rescale_lengths(lengths: list[int], weights: list[int], total: int) -> list[int]:
    """Keep every run positive and distribute the new weighted total."""
    available = total - sum(weights)
    previous = sum((length - 1) * weight for length, weight in zip(lengths, weights))
    scaled = [1 + (length - 1) * available // previous for length in lengths]
    remainder = total - sum(length * weight for length, weight in zip(scaled, weights))
    scaled[weights.index(1)] += remainder
    return scaled


def _vary_pattern(rng: Random, pattern: Pattern, ceiling: int) -> Pattern:
    """Reorder or resize runs, sometimes moving to nearby step counts."""
    runs = list(pattern)
    donor, recipient = rng.sample(range(1, len(runs) - 1), 2)
    if runs[donor].uphill == 1:
        donor, recipient = recipient, donor
    first, second = runs[donor], runs[recipient]
    moved = rng.randrange(first.uphill)
    if moved:
        runs[donor] = Run(first.uphill - moved, first.downhill_divisions, first.downhill)
        runs[recipient] = Run(second.uphill + moved, second.downhill_divisions, second.downhill)
    if not moved or rng.getrandbits(1):
        first, second = runs[donor], runs[recipient]
        runs[donor] = Run(first.uphill, second.downhill_divisions, second.downhill)
        runs[recipient] = Run(second.uphill, first.downhill_divisions, first.downhill)
    if rng.randrange(3) == 0:
        k = sum(run.uphill + run.downhill for run in runs)
        divisions = sum(run.uphill + run.downhill_divisions * run.downhill for run in runs)
        new_k, new_divisions = _sample_counts(rng, ceiling, near=(k, divisions))
        if (new_k, new_divisions) != (k, divisions):
            exponents = [run.downhill_divisions for run in runs]
            short_downhill = runs[-1].downhill
            short_uphill = runs[0].uphill
            downhill = _rescale_lengths(
                [run.downhill for run in runs[:-1]],
                [exponent - 1 for exponent in exponents[:-1]],
                new_divisions - new_k - short_downhill * (exponents[-1] - 1),
            )
            downhill.append(short_downhill)
            uphill = [short_uphill, *_rescale_lengths(
                [run.uphill for run in runs[1:]], [1] * (len(runs) - 1),
                new_k - sum(downhill) - short_uphill,
            )]
            return tuple(Run(u, d, w) for u, d, w in zip(uphill, exponents, downhill))
    return tuple(runs)


def _canonical_pattern(pattern: Pattern) -> Pattern:
    # Start at a short valley so mutations can preserve it. At least the
    # original first rising block and preceding falling block qualify.
    return min(
        pattern[index:] + pattern[:index]
        for index, run in enumerate(pattern)
        if run.uphill <= _SHORT_UPHILL and pattern[index - 1].downhill <= _SHORT_DOWNHILL
    )


def _word(pattern: Pattern) -> Word:
    return Concat(tuple(
        part
        for run in pattern
        for part in (Repeat(Step(1), run.uphill), Repeat(Step(run.downhill_divisions), run.downhill))
    ))


@cache
def _log_bounds(value: int) -> tuple[Fraction, Fraction]:
    """Enclose ln(value) using the atanh series and a geometric tail bound."""
    z = Fraction(value - 1, value + 1)
    terms = 100
    lower = 2 * sum(z ** (2*j + 1) / (2*j + 1) for j in range(terms))
    tail = 2 * z ** (2*terms + 1) / ((2*terms + 1) * (1 - z*z))
    return lower, lower + tail


def _run_gap_exceeds_bound(k: int, divisions: int, runs: int) -> bool:
    # Going uphill gives growth by at least 3/2. Traversing a downhill
    # run backwards gives growth by at least 5/4 for members >= 4.
    # Each run contributes at most 3/m or 5/m to the reciprocal sum.
    ln2_lower, _ = _log_bounds(2)
    _, ln3_upper = _log_bounds(3)
    gap_lower = divisions * ln2_lower - k * ln3_upper
    return gap_lower >= Fraction(8 * runs, 3 * _MINIMUM_CYCLE_MEMBER)


def _evaluate_pattern(pattern: Pattern, prime_limit: int) -> tuple[str, dict[str, object]]:
    word = _word(pattern)
    report = analyze(word, prime_limit=prime_limit)
    if report["rejected"]:
        return "rejected", report
    counts = report["counts"]
    k, divisions = int(counts["odd_steps"]), int(counts["total_divisions"])
    if _run_gap_exceeds_bound(k, divisions, len(pattern)):
        report["rejection_certificates"].append({
            "filter": "run_log_gap_bound",
            "rigorous": True,
            "uphill_runs": len(pattern),
            "minimum_member": str(_MINIMUM_CYCLE_MEMBER),
        })
        report["rejected"] = True
        report["conclusion"] = "impossible_for_the_requested_model"
        return "rejected", report
    exact = verify_exact(word)
    report["exact_verification"] = exact
    report["rejected"] = not exact["is_cycle"]
    report["conclusion"] = exact["conclusion"]
    return ("confirmed" if exact["is_cycle"] else "rejected"), report


def _margin(slope: Fraction) -> str:
    with localcontext() as context:
        context.prec = max(80, len(str(slope.denominator)) * 3)
        return str(Decimal(slope.numerator) / Decimal(slope.denominator)
                   * Decimal(2).ln() - Decimal(3).ln())


def search_cycles(
    max_odd_steps: int,
    *,
    cases_per_level: int = DEFAULT_CASES_PER_LEVEL,
    depth: int = DEFAULT_DEPTH,
    seed: int = 0,
    prime_limit: int = DEFAULT_PRIME_LIMIT,
) -> dict[str, object]:
    """Evaluate random patterns and refine the best-scoring proposals."""
    for name, value in (
        ("max_odd_steps", max_odd_steps), ("cases_per_level", cases_per_level), ("depth", depth)
    ):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    targeted_moduli(1, 2, prime_limit)  # Validate even when the ceiling precludes any proposal.

    rng = Random(seed)
    candidates = []
    levels = []
    seen: set[Pattern] = set()
    elite: list[RankedPattern] = []
    total: Counter[str] = Counter()
    statuses = ("rejected", "confirmed")

    if max_odd_steps >= _MIN_ODD_STEPS:
        for level in range(1, depth + 1):
            parents = elite[:]
            level_counts: Counter[str] = Counter()
            family_counts: dict[tuple[int, int], Counter[str]] = {}
            family_best: dict[tuple[int, int], RankedPattern] = {}
            best: RankedPattern | None = None
            # Each slot has a bounded number of retries for duplicate rotations.
            for slot in range(cases_per_level):
                parent = rng.choice(parents) if parents and slot % 3 != 0 else None
                for _ in range(4):
                    pattern = _canonical_pattern(
                        _vary_pattern(rng, parent.pattern, max_odd_steps) if parent
                        else _sample_pattern(rng, max_odd_steps)
                    )
                    if pattern not in seen:
                        break
                else:
                    continue
                seen.add(pattern)
                status, analysis = _evaluate_pattern(pattern, prime_limit)
                counts = analysis["counts"]
                slope = Fraction(int(counts["total_divisions"]), int(counts["odd_steps"]))
                score = _margin(slope)
                identifier = len(candidates) + 1
                family = (len(pattern), max(run.downhill_divisions for run in pattern))
                family_counts.setdefault(family, Counter())[status] += 1
                level_counts[status] += 1
                if Decimal(score) > 0:
                    ranked = RankedPattern(identifier, pattern, slope)
                    elite.append(ranked)
                    elite.sort(key=lambda entry: entry.slope)
                    del elite[4:]
                    if best is None or slope < best.slope:
                        best = ranked
                    if family not in family_best or slope < family_best[family].slope:
                        family_best[family] = ranked
                candidates.append({
                    "id": identifier,
                    "level": level,
                    "parent_id": parent.identifier if parent else None,
                    "family": {"uphill_runs": family[0], "max_downhill_divisions": family[1]},
                    "runs": [[str(run.uphill), run.downhill_divisions, str(run.downhill)] for run in pattern],
                    "closure_margin_per_step": score,
                    "status": status,
                    "analysis": analysis,
                })
            total.update(level_counts)
            levels.append({
                "level": level,
                "evaluated": level_counts.total(),
                **{status: level_counts[status] for status in statuses},
                "best_candidate_id": best.identifier if best else None,
                "families": [
                    {
                        "uphill_runs": family[0],
                        "max_downhill_divisions": family[1],
                        **{status: results[status] for status in statuses},
                        "best_candidate_id": family_best[family].identifier if family in family_best else None,
                    }
                    for family, results in sorted(family_counts.items())
                ],
            })

    if total["confirmed"]:
        conclusion = "cycle_confirmed"
    elif candidates:
        conclusion = "all_candidates_rejected"
    else:
        conclusion = "no_candidates"
    return {
        "schema": "collatz-monte-carlo-search-v2",
        "coverage_is_exhaustive": False,
        "settings": {
            "max_odd_steps": str(max_odd_steps),
            "minimum_period": str(MINIMUM_NONTRIVIAL_PERIOD),
            "cases_per_level": cases_per_level,
            "depth": depth,
            "seed": seed,
            "prime_limit": prime_limit,
        },
        "conclusion": conclusion,
        "best_candidate_id": elite[0].identifier if elite else None,
        "totals": {status: total[status] for status in statuses},
        "levels": levels,
        "candidates": candidates,
    }
