"""Sample and refine compressed Collatz cycle patterns."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import groupby
from pathlib import Path
from random import Random
from typing import Iterator

from .bounds import (
    MINIMUM_ODD_STEPS, CountWindow, count_window, lower_log_gap, run_gap_bound,
    MINIMUM_CYCLE_MEMBER as _MINIMUM_CYCLE_MEMBER,
)
from .definitive import verify_exact
from .grammar import Concat, Repeat, Step, Word, counts
from .modular import evaluate_affine
from .modular_closure import DEFAULT_MODULUS_BITS
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

# Steiner excludes a single uphill run in a nontrivial cycle.
_MIN_RUNS = 2
_VALLEY_PREFIX_STEPS = 12
_VALLEY_FILTER_STEPS = 128
_VALLEY_MODULUS_BITS = 384


@dataclass(frozen=True, order=True, slots=True)
class Run:
    uphill: int
    downhill_divisions: int
    downhill: int
    following: tuple[tuple[int, int], ...] = ()

    @property
    def descent(self) -> tuple[tuple[int, int], ...]:
        return ((self.downhill_divisions, self.downhill), *self.following)


Pattern = tuple[Run, ...]


@dataclass(frozen=True, slots=True)
class RunGroup:
    runs: Pattern
    copies: int


@dataclass(frozen=True, slots=True)
class AnchoredPattern:
    runs: Pattern
    prefix_runs: int
    valley: int | None
    packed: tuple[RunGroup, ...] = ()

    @property
    def run_count(self) -> int:
        return len(self.runs) + sum(len(group.runs) * group.copies for group in self.packed)


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


def _scale(rng: Random) -> int:
    """Prefer small adjustments while giving every nonnegative size support."""
    size = 0
    while rng.getrandbits(1):
        size += 1
    return size


def _sample_valley(rng: Random) -> tuple[int, Pattern, int, int] | None:
    """Build a short valid prefix and a compatible incoming downhill run."""
    for _ in range(64):
        divisions, length = 2 + _scale(rng), 1 + _scale(rng)
        b = 3**length
        residue = _combine_residues(4, 3, b, pow(pow(2, divisions, b) - 3, -1, b))
        stride = 4 * b
        first = _MINIMUM_CYCLE_MEMBER + (residue - _MINIMUM_CYCLE_MEMBER) % stride
        lifts = max(1, (1 << (_MINIMUM_CYCLE_MEMBER.bit_length() + _scale(rng))) // stride)
        valley = first + stride * rng.randrange(lifts)
        term, uphill = valley, 0
        descent: list[int] = []
        prefix = []
        for step in range(_VALLEY_PREFIX_STEPS + 8 + _scale(rng)):
            value = 3 * term + 1
            exponent = (value & -value).bit_length() - 1
            if exponent == 1 and descent:
                blocks = [(d, sum(1 for _ in entries)) for d, entries in groupby(descent)]
                d, w = blocks[0]
                prefix.append(Run(uphill, d, w, tuple(blocks[1:])))
                if step >= _VALLEY_PREFIX_STEPS:
                    return valley, tuple(prefix), divisions, length
                uphill, descent = 0, []
            term = value >> exponent
            if term < _MINIMUM_CYCLE_MEMBER:
                break
            if exponent == 1:
                uphill += 1
            else:
                descent.append(exponent)
    return None


def _required_runs(k: int, divisions: int) -> int:
    return max(_MIN_RUNS, int(lower_log_gap(k, divisions) / run_gap_bound(1)) + 1)


def _sample_run_count(rng: Random, low: int, high: int) -> int:
    band = rng.randrange((high // low).bit_length())
    start = low << band
    return rng.randint(start, min(high, 2 * start - 1))


def _independent_pattern(
    rng: Random, k: int, divisions: int, run_count: int
) -> AnchoredPattern:
    excess = divisions - k
    downhill_steps = rng.randint(run_count, min(k - run_count, excess))
    up_lengths = _split(rng, k - downhill_steps - run_count, run_count)
    down_lengths = _split(rng, downhill_steps - run_count, run_count)
    powers = iter(_split(rng, excess - downhill_steps, downhill_steps))
    runs = []
    for uphill, downhill in zip(up_lengths, down_lengths):
        blocks = [
            (d + 2, sum(1 for _ in items))
            for d, items in groupby(next(powers) for _ in range(downhill + 1))
        ]
        exponent, length = blocks[0]
        runs.append(Run(uphill + 1, exponent, length, tuple(blocks[1:])))
    return AnchoredPattern(tuple(runs), 0, None)


def _fixed_parts(prefix: Pattern, incoming: Run | None) -> Pattern:
    return prefix if incoming is None else prefix + (incoming,)


def _run_range(k: int, divisions: int, prefix: Pattern, incoming: Run | None) -> tuple[int, int]:
    fixed = _fixed_parts(prefix, incoming)
    fixed_k, fixed_s = counts(_word(fixed)) if fixed else (0, 0)
    # Leave two steps and one excess division for the adjustable run.
    packed_max = min((k - fixed_k - 2) // 2, divisions - k - (fixed_s - fixed_k) - 1)
    return max(len(fixed) + 2, _required_runs(k, divisions)), len(fixed) + 1 + packed_max


def _many_runs(
    rng: Random, k: int, divisions: int, run_count: int, valley: int | None,
    prefix: Pattern, incoming: Run | None,
) -> AnchoredPattern:
    fixed = _fixed_parts(prefix, incoming)
    fixed_k, fixed_s = counts(_word(fixed)) if fixed else (0, 0)
    run_slots = run_count - len(fixed) - 1
    remaining_steps = k - fixed_k - 2 * run_slots
    remaining_excess = divisions - k - (fixed_s - fixed_k) - run_slots
    threes = rng.randint(
        max(0, remaining_excess - remaining_steps + 1),
        min(run_slots, remaining_excess - 1),
    )
    down = remaining_excess - threes
    # Move some downhill steps to the ascent and spend their divisions on
    # one high-exponent step. The other downhill steps can retain exponent 2.
    spike = rng.randint(0, down - 1) if rng.getrandbits(1) else 0
    filler = Run(
        remaining_steps - down + spike, 2 + spike, 1,
        ((2, down - spike - 1),) if down - spike > 1 else (),
    )

    # Interleave mixed motifs and homogeneous motifs in independently sized
    # groups. This representation expands to the requested run count.
    twos = run_slots - threes
    mixed = rng.randint(0, min(twos, threes))
    groups = []
    for motif, copies in (
        ((Run(1, 2, 1),), twos - mixed),
        ((Run(1, 3, 1),), threes - mixed),
        ((Run(1, 2, 1), Run(1, 3, 1)), mixed),
    ):
        for part in _split(rng, copies, 4):
            if part:
                groups.append(RunGroup(motif, part))
    rng.shuffle(groups)
    return AnchoredPattern(_fixed_parts(prefix + (filler,), incoming), len(prefix), valley, tuple(groups))


def _sample_pattern(
    rng: Random, window: CountWindow, independent: bool = False
) -> AnchoredPattern | None:
    if independent:
        for _ in range(8):
            k, divisions = window.sample(rng)
            low = _required_runs(k, divisions)
            high = min(k // 2, divisions - k)
            if low <= high:
                return _independent_pattern(rng, k, divisions, _sample_run_count(rng, low, high))
        return None
    anchor = _sample_valley(rng) if rng.randrange(4) else None
    if anchor is None:
        valley, prefix, incoming = None, (), None
    else:
        valley, prefix, incoming_exponent, incoming_length = anchor
        incoming = Run(1, incoming_exponent, incoming_length)
    for _ in range(8):
        k, divisions = window.sample(rng)
        low, high = _run_range(k, divisions, prefix, incoming)
        if low <= high:
            break
    else:
        return None
    return _many_runs(
        rng, k, divisions, _sample_run_count(rng, low, high), valley, prefix, incoming
    )


def _rescale_lengths(lengths: list[int], weights: list[int], total: int) -> list[int]:
    available = total - sum(weights)
    if available < 0:
        raise ValueError("resizing must leave at least one step in each run")
    previous = max(1, sum((length - 1) * weight for length, weight in zip(lengths, weights)))
    scaled = [1 + (length - 1) * available // previous for length in lengths]
    remainder = total - sum(length * weight for length, weight in zip(scaled, weights))
    scaled[weights.index(1)] += remainder
    return scaled


def _vary_pattern(rng: Random, pattern: AnchoredPattern, window: CountWindow) -> AnchoredPattern:
    """Vary the unanchored runs while preserving both sides of the anchor."""
    if pattern.valley is None and not pattern.packed:
        if rng.randrange(3):
            runs = list(pattern.runs)
            left, right = rng.sample(range(len(runs)), 2)
            first, second = runs[left], runs[right]
            moved = rng.randrange(first.uphill)
            runs[left] = Run(first.uphill - moved, *second.descent[0], second.following)
            runs[right] = Run(second.uphill + moved, *first.descent[0], first.following)
            return AnchoredPattern(tuple(runs), 0, None)
        k, divisions = window.sample(rng)
        low, high = _required_runs(k, divisions), min(k // 2, divisions - k)
        if low > high:
            return pattern
        run_count = min(high, max(low, pattern.run_count + rng.choice((-1, 0, 1))))
        return _independent_pattern(rng, k, divisions, run_count)
    if pattern.packed:
        if len(pattern.packed) > 1 and rng.randrange(3) == 0:
            groups = list(pattern.packed)
            a, b = rng.sample(range(len(groups)), 2)
            groups[a], groups[b] = groups[b], groups[a]
            return AnchoredPattern(pattern.runs, pattern.prefix_runs, pattern.valley, tuple(groups))
        k, divisions = counts(_pattern_word(pattern.runs, pattern.packed, pattern.prefix_runs))
        prefix = pattern.runs[:pattern.prefix_runs]
        incoming = pattern.runs[-1] if pattern.valley is not None else None
        low, high = _run_range(k, divisions, prefix, incoming)
        run_count = rng.randint(
            max(low, pattern.run_count - max(1, pattern.run_count // 8)),
            min(high, pattern.run_count + max(1, pattern.run_count // 8)),
        )
        return _many_runs(rng, k, divisions, run_count, pattern.valley, prefix, incoming)
    runs = list(pattern.runs)
    donor, recipient = rng.sample(range(pattern.prefix_runs, len(runs) - 1), 2)
    if runs[donor].uphill == 1:
        donor, recipient = recipient, donor
    first, second = runs[donor], runs[recipient]
    moved = rng.randrange(first.uphill)
    runs[donor] = Run(first.uphill - moved, second.downhill_divisions, second.downhill, second.following)
    runs[recipient] = Run(second.uphill + moved, first.downhill_divisions, first.downhill, first.following)
    if rng.randrange(3) == 0 and not any(run.following for run in runs[pattern.prefix_runs:-1]):
        k, divisions = window.sample(rng)
        if lower_log_gap(k, divisions) < run_gap_bound(len(runs)):
            prefix = runs[:pattern.prefix_runs]
            fixed_k, fixed_divisions = counts(_word(tuple(prefix + runs[-1:])))
            interior = runs[pattern.prefix_runs:-1]
            k -= fixed_k
            divisions -= fixed_divisions
            exponents = [run.downhill_divisions for run in interior]
            weights = [d - 1 for d in exponents]
            if divisions - k >= sum(weights):
                downhill = _rescale_lengths(
                    [run.downhill for run in interior], weights, divisions - k
                )
                if k - sum(downhill) >= len(interior):
                    uphill = _rescale_lengths(
                        [run.uphill for run in interior], [1] * len(interior), k - sum(downhill)
                    )
                    runs[pattern.prefix_runs:-1] = [
                        Run(u, d, w) for u, d, w in zip(uphill, exponents, downhill)
                    ]
    return AnchoredPattern(tuple(runs), pattern.prefix_runs, pattern.valley)


def _canonical_pattern(pattern: Pattern) -> Pattern:
    """Find the least cyclic rotation without materializing every rotation."""
    size = len(pattern)
    left, right, matched = 0, 1, 0
    while left < size and right < size and matched < size:
        first = pattern[(left + matched) % size]
        second = pattern[(right + matched) % size]
        if first == second:
            matched += 1
            continue
        if first > second:
            left = max(left + matched + 1, right + 1)
        else:
            right = max(right + matched + 1, left + 1)
        matched = 0
    start = min(left, right)
    return pattern[start:] + pattern[:start]


def _word(pattern: Pattern) -> Word:
    return Concat(tuple(
        part
        for run in pattern
        for part in (Repeat(Step(d), w) for d, w in ((1, run.uphill), *run.descent))
    ))


def _pattern_word(pattern: Pattern, packed: tuple[RunGroup, ...], prefix_runs: int) -> Word:
    if not packed:
        return _word(pattern)
    head = (_word(pattern[:prefix_runs]),) if prefix_runs else ()
    middle = tuple(Repeat(_word(group.runs), group.copies) for group in packed)
    return Concat(head + middle + (_word(pattern[prefix_runs:]),))


def _packed_gap_bound(pattern: Pattern, packed: tuple[RunGroup, ...]) -> Fraction:
    # Every phase of a repeated motif is geometrically increasing in one
    # direction. Bound all cyclic shifts with the same coefficient estimate.
    reciprocal_units = 8 * len(pattern)
    for group in packed:
        k, divisions = counts(_word(group.runs))
        phases = group.copies
        # A compact proof can use exact motif coefficients when the simple
        # bit bound guarantees they are safely below the cycle-member bound.
        if 2 * k + divisions + k.bit_length() < _MINIMUM_CYCLE_MEMBER.bit_length() - 1:
            denominator, multiplier = 1 << divisions, 3**k
            phases = min(phases, 2 * max(denominator, multiplier) + 1)
        reciprocal_units += k * phases
    return Fraction(reciprocal_units, 3 * _MINIMUM_CYCLE_MEMBER)


def _valley_lower_bound(pattern: Pattern, index: int) -> int:
    """Smallest member satisfying necessary local congruences at a valley."""
    remaining = _VALLEY_FILTER_STEPS
    bits = _VALLEY_MODULUS_BITS
    parts = []
    for offset in range(len(pattern)):
        run = pattern[(index + offset) % len(pattern)]
        for exponent, length in ((1, run.uphill), *run.descent):
            take = min(remaining, length, bits // exponent)
            if take:
                parts.append(Repeat(Step(exponent), take))
                remaining -= take
                bits -= exponent * take
            if remaining == 0 or take < length:
                break
        else:
            continue
        break
    prefix = evaluate_affine(Concat(tuple(parts)))
    two_power = prefix.denominator
    forward = -prefix.additive * pow(prefix.multiplier, -1, two_power)
    exponent, length = pattern[index - 1].descent[-1]
    three_power = 3 ** min(length, _VALLEY_FILTER_STEPS)
    backward = pow(pow(2, exponent, three_power) - 3, -1, three_power)
    residue = _combine_residues(two_power, forward, three_power, backward)
    return _MINIMUM_CYCLE_MEMBER + (residue - _MINIMUM_CYCLE_MEMBER) % (two_power * three_power)


def _valley_gap_bound(pattern: Pattern) -> Fraction:
    # Sum upwards-rounded reciprocals so the test stays rigorous and avoids
    # carrying the product of a different denominator for every valley.
    units = 1 << 192
    minima = (_valley_lower_bound(pattern, i) for i in range(len(pattern)))
    reciprocals = sum((units + minimum - 1) // minimum for minimum in minima)
    return Fraction(8 * reciprocals, 3 * units)


def _evaluate_pattern(
    pattern: Pattern, prime_limit: int, packed: tuple[RunGroup, ...] = (), prefix_runs: int = 0,
    *, modulus_bits: int = DEFAULT_MODULUS_BITS, checkpoint_dir: Path | None = None,
) -> tuple[str, dict[str, object]]:
    word = _pattern_word(pattern, packed, prefix_runs)
    run_count = len(pattern) + sum(len(group.runs) * group.copies for group in packed)
    report = analyze(word, prime_limit=prime_limit)
    if report["rejected"]:
        return "rejected", report
    counts = report["counts"]
    k, divisions = int(counts["odd_steps"]), int(counts["total_divisions"])
    gap_lower = lower_log_gap(k, divisions)
    for name, gap_upper in (
        ("run_log_gap_bound", run_gap_bound(run_count)),
        ("packed_runs_gap_bound", _packed_gap_bound(pattern, packed))
        if packed else ("valley_congruence_gap_bound", _valley_gap_bound(pattern)),
    ):
        if gap_lower >= gap_upper:
            report["rejection_certificates"].append({
                "filter": name,
                "rigorous": True,
                "uphill_runs": run_count,
                "gap_upper_bound": str(gap_upper),
            })
            report["rejected"] = True
            report["conclusion"] = "impossible_for_the_requested_model"
            return "rejected", report
    exact = verify_exact(word, modulus_bits=modulus_bits, checkpoint_dir=checkpoint_dir)
    report["exact_verification"] = exact
    report["rejected"] = not exact["is_cycle"]
    report["conclusion"] = exact["conclusion"]
    return ("confirmed" if exact["is_cycle"] else "rejected"), report


def _margin(slope: Fraction) -> str:
    with localcontext() as context:
        context.prec = max(80, len(str(slope.denominator)) * 3)
        return str(Decimal(slope.numerator) / Decimal(slope.denominator)
                   * Decimal(2).ln() - Decimal(3).ln())


def _report_run(run: Run) -> list:
    data = [str(run.uphill), run.downhill_divisions, str(run.downhill)]
    if run.following:
        data.append([[d, str(w)] for d, w in run.following])
    return data


def search_cycles(
    max_odd_steps: int,
    *,
    cases_per_level: int = DEFAULT_CASES_PER_LEVEL,
    depth: int = DEFAULT_DEPTH,
    seed: int = 0,
    prime_limit: int = DEFAULT_PRIME_LIMIT,
    independent_runs: bool = False,
    modulus_bits: int = DEFAULT_MODULUS_BITS,
    checkpoint_dir: Path | None = None,
) -> dict[str, object]:
    """Evaluate random patterns and refine the best-scoring proposals."""
    for name, value in (
        ("max_odd_steps", max_odd_steps), ("cases_per_level", cases_per_level), ("depth", depth)
    ):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if type(modulus_bits) is not int or modulus_bits < 2:
        raise ValueError("modulus_bits must be at least 2")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    targeted_moduli(1, 2, prime_limit)  # Validate even when the ceiling precludes any proposal.

    rng = Random(seed)
    candidates = []
    levels = []
    seen = set()
    elite: list[RankedPattern] = []
    total: Counter[str] = Counter()
    statuses = ("rejected", "confirmed")

    max_uphill_runs = max_odd_steps // 2
    window = count_window(max_odd_steps, max_uphill_runs) if max_odd_steps >= MINIMUM_ODD_STEPS else None
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
                        if parent else _sample_pattern(rng, window, independent_runs)
                    )
                    if sampled is None:
                        continue
                    key = (
                        (sampled.runs, sampled.packed, sampled.prefix_runs) if sampled.packed
                        else _canonical_pattern(sampled.runs)
                    )
                    if key not in seen:
                        break
                else:
                    continue
                seen.add(key)
                pattern = sampled.runs
                status, analysis = _evaluate_pattern(
                    pattern, prime_limit, sampled.packed, sampled.prefix_runs,
                    modulus_bits=modulus_bits, checkpoint_dir=checkpoint_dir,
                )
                counts = analysis["counts"]
                slope = Fraction(int(counts["total_divisions"]), int(counts["odd_steps"]))
                score = _margin(slope)
                identifier = len(candidates) + 1
                family = (sampled.run_count, max(
                    d for run in pattern + tuple(run for group in sampled.packed for run in group.runs)
                    for d, _ in run.descent
                ))
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
                    "anchor": {"odd_member": str(sampled.valley), "prefix_runs": sampled.prefix_runs} if sampled.valley is not None else None,
                    "runs": [_report_run(run) for run in pattern],
                    "packed_runs": [
                        {"copies": str(group.copies), "runs": [_report_run(run) for run in group.runs]}
                        for group in sampled.packed
                    ],
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
        "schema": "collatz-monte-carlo-search-v5",
        "coverage_is_exhaustive": False,
        "settings": {
            "max_odd_steps": str(max_odd_steps),
            "minimum_period": str(MINIMUM_NONTRIVIAL_PERIOD),
            "cases_per_level": cases_per_level,
            "depth": depth,
            "seed": seed,
            "prime_limit": prime_limit,
            "modulus_bits": modulus_bits,
            "independent_runs": independent_runs,
        },
        "conclusion": conclusion,
        "preflight": {
            "max_uphill_runs": max_uphill_runs,
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
