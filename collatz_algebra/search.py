"""Sample and refine compressed Collatz cycle patterns."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from random import Random
from typing import Iterator

from .bounds import (
    MINIMUM_ODD_STEPS, CountWindow, count_window, lower_log_gap, run_gap_bound,
    MINIMUM_CYCLE_MEMBER as _MINIMUM_CYCLE_MEMBER,
)
from .definitive import verify_exact
from .grammar import Concat, Repeat, Step, Word, counts
from .modular import evaluate_affine
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

_MIN_RUNS = 128
_MAX_RUNS = 256
_MAX_DIVISIONS = 8
_VALLEY_PREFIX_STEPS = 12
_VALLEY_FILTER_STEPS = 128


@dataclass(frozen=True, order=True, slots=True)
class Run:
    uphill: int
    downhill_divisions: int
    downhill: int


Pattern = tuple[Run, ...]


@dataclass(frozen=True, slots=True)
class AnchoredPattern:
    runs: Pattern
    prefix_runs: int
    valley: int


@dataclass(frozen=True, slots=True)
class RankedPattern:
    identifier: int
    pattern: AnchoredPattern
    slope: Fraction


def _split(rng: Random, total: int, parts: int) -> list[int]:
    cuts = [0, *sorted(rng.randrange(total + 1) for _ in range(parts - 1)), total]
    return [right - left for left, right in zip(cuts, cuts[1:])]


def _combine_residues(a: int, first: int, b: int, second: int) -> int:
    """Combine residues modulo the coprime moduli a and b."""
    return (first + a * ((second - first) * pow(a, -1, b) % b)) % (a * b)


def _sample_valley(rng: Random) -> tuple[int, Pattern, int, int] | None:
    """Build a short valid prefix and a compatible incoming downhill run."""
    for _ in range(64):
        divisions, length = rng.randint(2, _MAX_DIVISIONS), rng.randint(1, 8)
        b = 3**length
        residue = _combine_residues(4, 3, b, pow((1 << divisions) - 3, -1, b))
        stride = 4 * b
        first = _MINIMUM_CYCLE_MEMBER + (residue - _MINIMUM_CYCLE_MEMBER) % stride
        valley = first + stride * rng.randrange(15 * _MINIMUM_CYCLE_MEMBER // stride)
        term, uphill, downhill, exponent = valley, 0, 0, 0
        prefix = []
        for step in range(32):
            value = 3 * term + 1
            next_exponent = (value & -value).bit_length() - 1
            if next_exponent == 1 and downhill:
                prefix.append(Run(uphill, exponent, downhill))
                if step >= _VALLEY_PREFIX_STEPS:
                    return valley, tuple(prefix), divisions, length
                uphill = downhill = 0
            if next_exponent > _MAX_DIVISIONS or (
                downhill and next_exponent != exponent
            ):
                break
            term = value >> next_exponent
            if term < _MINIMUM_CYCLE_MEMBER:
                break
            if next_exponent == 1:
                uphill += 1
            else:
                downhill += 1
                exponent = next_exponent
    return None


def _sample_pattern(rng: Random, window: CountWindow) -> AnchoredPattern | None:
    k, divisions = window.sample(rng)
    required_runs = int(lower_log_gap(k, divisions) / run_gap_bound(1)) + 1
    if required_runs > _MAX_RUNS:
        return None
    run_count = rng.randint(max(_MIN_RUNS, required_runs), _MAX_RUNS)
    anchor = _sample_valley(rng)
    if anchor is None:
        return None
    valley, prefix, incoming_exponent, incoming_length = anchor
    prefix_k, prefix_divisions = counts(_word(prefix))
    remaining_runs = run_count - len(prefix)
    max_divisions = rng.randint(max(2, incoming_exponent), _MAX_DIVISIONS)
    exponents = [2, max_divisions]
    exponents.extend(rng.randint(2, max_divisions) for _ in range(remaining_runs - 3))
    weights = [d - 1 for d in exponents]
    extra = (divisions - prefix_divisions) - (k - prefix_k)
    extra -= incoming_length * (incoming_exponent - 1) + sum(weights)
    allocations = _split(rng, extra, remaining_runs - 1)
    downhill = [1 + share // weight for share, weight in zip(allocations, weights)]
    downhill[0] += sum(share % weight for share, weight in zip(allocations, weights))
    downhill.append(incoming_length)
    exponents.append(incoming_exponent)
    uphill = _split(rng, k - prefix_k - sum(downhill) - remaining_runs, remaining_runs)
    runs = prefix + tuple(Run(u + 1, d, w) for u, d, w in zip(uphill, exponents, downhill))
    return AnchoredPattern(runs, len(prefix), valley)


def _rescale_lengths(lengths: list[int], weights: list[int], total: int) -> list[int]:
    available = total - sum(weights)
    previous = max(1, sum((length - 1) * weight for length, weight in zip(lengths, weights)))
    scaled = [1 + (length - 1) * available // previous for length in lengths]
    remainder = total - sum(length * weight for length, weight in zip(scaled, weights))
    scaled[weights.index(1)] += remainder
    return scaled


def _vary_pattern(rng: Random, pattern: AnchoredPattern, window: CountWindow) -> AnchoredPattern:
    """Vary the unanchored runs while preserving both sides of the anchor."""
    runs = list(pattern.runs)
    donor, recipient = rng.sample(range(pattern.prefix_runs, len(runs) - 1), 2)
    if runs[donor].uphill == 1:
        donor, recipient = recipient, donor
    first, second = runs[donor], runs[recipient]
    moved = rng.randrange(first.uphill)
    runs[donor] = Run(first.uphill - moved, second.downhill_divisions, second.downhill)
    runs[recipient] = Run(second.uphill + moved, first.downhill_divisions, first.downhill)
    if rng.randrange(3) == 0:
        k, divisions = window.sample(rng)
        if lower_log_gap(k, divisions) < run_gap_bound(len(runs)):
            prefix = runs[:pattern.prefix_runs]
            fixed_k, fixed_divisions = counts(_word(tuple(prefix + runs[-1:])))
            interior = runs[pattern.prefix_runs:-1]
            k -= fixed_k
            divisions -= fixed_divisions
            exponents = [run.downhill_divisions for run in interior]
            downhill = _rescale_lengths(
                [run.downhill for run in interior], [d - 1 for d in exponents], divisions - k
            )
            uphill = _rescale_lengths(
                [run.uphill for run in interior], [1] * len(interior), k - sum(downhill)
            )
            runs[pattern.prefix_runs:-1] = [
                Run(u, d, w) for u, d, w in zip(uphill, exponents, downhill)
            ]
    return AnchoredPattern(tuple(runs), pattern.prefix_runs, pattern.valley)


def _canonical_pattern(pattern: Pattern) -> Pattern:
    return min(pattern[index:] + pattern[:index] for index in range(len(pattern)))


def _word(pattern: Pattern) -> Word:
    return Concat(tuple(
        part
        for run in pattern
        for part in (Repeat(Step(1), run.uphill), Repeat(Step(run.downhill_divisions), run.downhill))
    ))


def _valley_lower_bound(pattern: Pattern, index: int) -> int:
    """Smallest member satisfying necessary local congruences at a valley."""
    uphill = pattern[index].uphill
    if uphill >= _VALLEY_FILTER_STEPS:
        two_power, forward = 1 << _VALLEY_FILTER_STEPS, -1
    else:
        remaining = _VALLEY_FILTER_STEPS
        parts = []
        for offset in range(len(pattern)):
            run = pattern[(index + offset) % len(pattern)]
            for exponent, length in ((1, run.uphill), (run.downhill_divisions, run.downhill)):
                take = min(remaining, length)
                parts.append(Repeat(Step(exponent), take))
                remaining -= take
                if not remaining:
                    break
            if not remaining:
                break
        prefix = evaluate_affine(Concat(tuple(parts)))
        two_power = prefix.denominator
        forward = -prefix.additive * pow(prefix.multiplier, -1, two_power)
    incoming = pattern[index - 1]
    three_power = 3 ** min(incoming.downhill, _VALLEY_FILTER_STEPS)
    backward = pow((1 << incoming.downhill_divisions) - 3, -1, three_power)
    residue = _combine_residues(two_power, forward, three_power, backward)
    return _MINIMUM_CYCLE_MEMBER + (residue - _MINIMUM_CYCLE_MEMBER) % (two_power * three_power)


def _valley_gap_bound(pattern: Pattern) -> Fraction:
    # Sum upwards-rounded reciprocals so the test stays rigorous and avoids
    # carrying the product of a different denominator for every valley.
    units = 1 << 192
    minima = (_valley_lower_bound(pattern, i) for i in range(len(pattern)))
    reciprocals = sum((units + minimum - 1) // minimum for minimum in minima)
    return Fraction(8 * reciprocals, 3 * units)


def _evaluate_pattern(pattern: Pattern, prime_limit: int) -> tuple[str, dict[str, object]]:
    word = _word(pattern)
    report = analyze(word, prime_limit=prime_limit)
    if report["rejected"]:
        return "rejected", report
    counts = report["counts"]
    k, divisions = int(counts["odd_steps"]), int(counts["total_divisions"])
    gap_lower = lower_log_gap(k, divisions)
    for name, gap_upper in (
        ("run_log_gap_bound", run_gap_bound(len(pattern))),
        ("valley_congruence_gap_bound", _valley_gap_bound(pattern)),
    ):
        if gap_lower >= gap_upper:
            report["rejection_certificates"].append({
                "filter": name,
                "rigorous": True,
                "uphill_runs": len(pattern),
                "gap_upper_bound": str(gap_upper),
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

    window = count_window(max_odd_steps, _MAX_RUNS) if max_odd_steps >= MINIMUM_ODD_STEPS else None
    if window is not None and not window.excluded:
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
                    sampled = (
                        _vary_pattern(rng, parent.pattern, window)
                        if parent else _sample_pattern(rng, window)
                    )
                    if sampled is None:
                        continue
                    key = _canonical_pattern(sampled.runs)
                    if key not in seen:
                        break
                else:
                    continue
                seen.add(key)
                pattern = sampled.runs
                status, analysis = _evaluate_pattern(pattern, prime_limit)
                counts = analysis["counts"]
                slope = Fraction(int(counts["total_divisions"]), int(counts["odd_steps"]))
                score = _margin(slope)
                identifier = len(candidates) + 1
                family = (len(pattern), max(run.downhill_divisions for run in pattern))
                family_counts.setdefault(family, Counter())[status] += 1
                level_counts[status] += 1
                if Decimal(score) > 0:
                    ranked = RankedPattern(identifier, sampled, slope)
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
                    "anchor": {"odd_member": str(sampled.valley), "prefix_runs": sampled.prefix_runs},
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
    elif window is not None and window.excluded:
        conclusion = "scope_excluded"
    elif candidates:
        conclusion = "all_candidates_rejected"
    else:
        conclusion = "no_candidates"
    return {
        "schema": "collatz-monte-carlo-search-v3",
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
        "preflight": {
            "max_uphill_runs": _MAX_RUNS,
            "necessary_uphill_runs": str(int(window.upper_positive_gap / run_gap_bound(1)) + 1),
            "minimum_log_gap_lower_bound": str(window.upper_positive_gap),
            "cycle_log_gap_upper_bound": str(window.gap_limit),
            "farey_lower": str(window.lower),
            "farey_upper": str(window.upper),
        } if window is not None else {"minimum_odd_steps": str(MINIMUM_ODD_STEPS)},
        "best_candidate_id": elite[0].identifier if elite else None,
        "totals": {status: total[status] for status in statuses},
        "levels": levels,
        "candidates": candidates,
    }
