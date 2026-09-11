"""Deterministic, resumable enumeration of accelerated Collatz cycle equations."""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

from .cycle_equation import (
    passes_modular_filters,
    solve_cycle_equation,
)
from .integers import decimal_string

SEARCH_SCHEMA_VERSION = 2
ALGORITHM = "sum-constrained-primitive-necklace-cycle-equations"


@dataclass(frozen=True, slots=True)
class CycleSearchConfig:
    min_odd_period: int = 1
    max_odd_period: int = 12
    max_total_divisions: int = 24
    shard_index: int = 0
    shard_count: int = 1
    include_trivial: bool = False
    checkpoint_every: int = 100_000

    def validate(self) -> None:
        integer_fields = (
            self.min_odd_period,
            self.max_odd_period,
            self.max_total_divisions,
            self.shard_index,
            self.shard_count,
            self.checkpoint_every,
        )
        if any(not isinstance(v, int) or isinstance(v, bool) for v in integer_fields):
            raise ValueError("search parameters must be integers")
        if self.min_odd_period < 1 or self.max_odd_period < self.min_odd_period:
            raise ValueError("invalid odd-period range")
        if self.max_total_divisions < 1:
            raise ValueError("max_total_divisions must be positive")
        if self.shard_count < 1 or not 0 <= self.shard_index < self.shard_count:
            raise ValueError("shard_index must be in [0, shard_count)")
        if self.checkpoint_every < 1:
            raise ValueError("checkpoint_every must be positive")


@dataclass(slots=True)
class CycleSearchStats:
    ordered_compositions_in_region: int = 0
    canonical_vectors_generated: int = 0
    shard_vectors: int = 0
    modular_rejections: int = 0
    equations_solved: int = 0
    integral_candidates: int = 0


def compositions(total: int, parts: int) -> Iterator[tuple[int, ...]]:
    """Yield positive ordered compositions in deterministic lexicographic order."""
    if parts < 1 or total < parts:
        return
    vector = [1] * parts

    def visit(position: int, remaining: int) -> Iterator[tuple[int, ...]]:
        if position == parts - 1:
            vector[position] = remaining
            yield tuple(vector)
            return
        maximum = remaining - (parts - position - 1)
        for value in range(1, maximum + 1):
            vector[position] = value
            yield from visit(position + 1, remaining - value)

    yield from visit(0, total)


def primitive_necklaces(total: int, length: int) -> Iterator[tuple[int, ...]]:
    """Generate each primitive cyclic exponent word once, with an exact sum.

    This is a sum-constrained Fredricksen-Kessler-Maiorana recursion. Unlike
    filtering ordered compositions after generation, it constructs only
    lexicographically least rotations and emits only words whose fundamental
    period is ``length``.
    """
    if length < 1 or total < length:
        return
    maximum = total - length + 1
    word = [1] * (length + 1)

    def visit(position: int, period: int, used: int) -> Iterator[tuple[int, ...]]:
        if position > length:
            if period == length and used == total:
                yield tuple(word[1:])
            return

        remaining_positions = length - position
        repeated = word[position - period]
        candidates = range(repeated, maximum + 1)
        for value in candidates:
            new_used = used + value
            if new_used + remaining_positions > total:
                break
            if new_used + remaining_positions * maximum < total:
                continue
            word[position] = value
            next_period = period if value == repeated else position
            yield from visit(position + 1, next_period, new_used)

    yield from visit(1, 1, 0)


def minimum_total_divisions(odd_period: int) -> int:
    """Smallest S satisfying the necessary positivity condition 2**S > 3**k."""
    if odd_period < 1:
        raise ValueError("odd_period must be positive")
    # Integer arithmetic corrects the floating estimate at exact boundaries.
    estimate = max(odd_period, math.floor(odd_period * math.log2(3)) + 1)
    while (1 << estimate) <= 3**odd_period:
        estimate += 1
    while estimate > odd_period and (1 << (estimate - 1)) > 3**odd_period:
        estimate -= 1
    return estimate


def ordered_composition_count(config: CycleSearchConfig) -> int:
    """Return the brute-force search-space size avoided by necklace generation."""
    return sum(
        math.comb(total - 1, odd_period - 1)
        for odd_period in range(config.min_odd_period, config.max_odd_period + 1)
        for total in range(
            minimum_total_divisions(odd_period), config.max_total_divisions + 1
        )
    )


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _signature(config: CycleSearchConfig) -> dict[str, object]:
    data = asdict(config)
    data.pop("checkpoint_every")
    return data


def search_cycles(
    config: CycleSearchConfig,
    *,
    checkpoint_path: Path | None = None,
) -> dict[str, object]:
    """Enumerate canonical primitive exponent vectors and persist resumable progress."""
    config.validate()
    stats = CycleSearchStats(
        ordered_compositions_in_region=ordered_composition_count(config)
    )
    resume_after = 0
    discoveries: list[dict[str, object]] = []
    if checkpoint_path is not None and checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text())
        if checkpoint.get("schema_version") != SEARCH_SCHEMA_VERSION:
            raise ValueError("unsupported checkpoint schema")
        if checkpoint.get("config") != _signature(config):
            raise ValueError("checkpoint does not match search configuration")
        resume_after = checkpoint["vectors_processed"]
        stats = CycleSearchStats(**checkpoint["stats"])
        discoveries = checkpoint.get("discoveries", [])
        if checkpoint.get("completed"):
            return {
                "schema_version": SEARCH_SCHEMA_VERSION,
                "algorithm": ALGORITHM,
                "config": asdict(config),
                "stats": asdict(stats),
                "discoveries": discoveries,
                "completed": True,
                "wall_time_ns": 0,
            }

    started = time.monotonic_ns()

    def save(completed: bool) -> None:
        if checkpoint_path is None:
            return
        _atomic_json(
            checkpoint_path,
            {
                "schema_version": SEARCH_SCHEMA_VERSION,
                "config": _signature(config),
                "vectors_processed": stats.canonical_vectors_generated,
                "stats": asdict(stats),
                "discoveries": discoveries,
                "completed": completed,
            },
        )

    ordinal = 0
    since_checkpoint = 0
    for odd_period in range(config.min_odd_period, config.max_odd_period + 1):
        first_total = minimum_total_divisions(odd_period)
        for total in range(first_total, config.max_total_divisions + 1):
            for vector in primitive_necklaces(total, odd_period):
                ordinal += 1
                if ordinal <= resume_after:
                    continue
                stats.canonical_vectors_generated += 1
                since_checkpoint += 1
                if (ordinal - 1) % config.shard_count == config.shard_index:
                    stats.shard_vectors += 1
                    if not passes_modular_filters(vector):
                        stats.modular_rejections += 1
                        cycle = None
                    else:
                        stats.equations_solved += 1
                        cycle = solve_cycle_equation(vector)
                    if cycle is not None:
                        stats.integral_candidates += 1
                        if config.include_trivial or 1 not in cycle.members:
                            discoveries.append(
                                {
                                    "odd_members": [
                                        decimal_string(value) for value in cycle.members
                                    ],
                                    "exponents": list(cycle.exponents),
                                    "odd_period": len(cycle.members),
                                    "total_divisions": sum(cycle.exponents),
                                    "unaccelerated_period": cycle.unaccelerated_period,
                                }
                            )
                            save(False)
                if (
                    checkpoint_path is not None
                    and since_checkpoint >= config.checkpoint_every
                ):
                    save(False)
                    since_checkpoint = 0

    save(True)
    return {
        "schema_version": SEARCH_SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "config": asdict(config),
        "stats": asdict(stats),
        "discoveries": discoveries,
        "completed": True,
        "wall_time_ns": time.monotonic_ns() - started,
    }


def run_cycle_search(
    output_root: Path, search_id: str, config: CycleSearchConfig
) -> dict[str, object]:
    """Run a search with durable checkpoint and summary artifacts."""
    if not search_id or Path(search_id).name != search_id:
        raise ValueError("search_id must be a nonempty path-safe name")
    directory = output_root / "results" / search_id
    checkpoint = directory / "checkpoint.json"
    result = search_cycles(config, checkpoint_path=checkpoint)
    _atomic_json(directory / "summary.json", result)
    return result
