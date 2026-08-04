"""Deterministic candidate-generation strategies."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from collections.abc import Iterator
from pathlib import Path

S0_STRATEGY = "S0-uniform-deterministic"
S1_STRATEGY = "S1-parity-prefix-top10"
S2_STRATEGY = "S2-parity-prefix-weighted-lineages"
S3_STRATEGY = "S3-recursive-weighted-lineages"
LINEAGE_STRATEGIES = frozenset((S1_STRATEGY, S2_STRATEGY, S3_STRATEGY))
DEFAULT_PREFIX_LENGTH = 256


def _sample_below(width: int, seed: bytes, domain: bytes, attempt: int) -> int | None:
    """Return an unbiased SHA-256 sample below ``width``, or None on rejection."""
    bit_count = width.bit_length()
    byte_count = (bit_count + 7) // 8
    material = bytearray()
    block = 0
    while len(material) < byte_count:
        material.extend(hashlib.sha256(
            b"bigcollatz\0" + domain + b"\0" + len(seed).to_bytes(8, "big") + seed
            + attempt.to_bytes(16, "big") + block.to_bytes(4, "big")
        ).digest())
        block += 1
    sampled = int.from_bytes(material[:byte_count], "big") & ((1 << bit_count) - 1)
    return sampled if sampled < width else None


def baseline_candidates(count: int, seed: str = "baseline-v1") -> Iterator[int]:
    """Sample distinct 1000-digit integers with a deterministic SHA-256 stream."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must be nonnegative")
    low, width = 10**999, 9 * 10**999
    seed_bytes = seed.encode()
    seen: set[int] = set()
    attempt = 0

    while len(seen) < count:
        sampled = _sample_below(width, seed_bytes, S0_STRATEGY.encode(), attempt)
        attempt += 1
        if sampled is None:
            continue
        candidate = low + sampled
        if candidate in seen:
            continue
        seen.add(candidate)
        yield candidate


def parity_decisions(value: int, prefix_length: int = DEFAULT_PREFIX_LENGTH) -> tuple[int, ...]:
    """Compute unaccelerated Collatz parity decisions (zero even, one odd)."""
    if value < 1 or prefix_length < 0:
        raise ValueError("value must be positive and prefix_length nonnegative")
    decisions = []
    for _ in range(prefix_length):
        decisions.append(value & 1)
        value = 3 * value + 1 if value & 1 else value // 2
    return tuple(decisions)


def validate_parity_prefix(candidate: int, parent: int,
                           prefix_length: int = DEFAULT_PREFIX_LENGTH) -> bool:
    """Directly validate that candidate and parent share a parity prefix."""
    return parity_decisions(candidate, prefix_length) == parity_decisions(parent, prefix_length)


def _validate_canonical_1000_digit(value: object, source_name: str, path: Path) -> str:
    if (not isinstance(value, str) or len(value) != 1000
            or value[0] == "0" or not value.isascii() or not value.isdecimal()):
        raise ValueError(
            f"invalid {source_name} (expected canonical 1000-digit decimal): {path}"
        )
    return value


def load_global_top_10(path: Path) -> list[int]:
    """Load distinct canonical 1000-digit parents from a persistent top-ten file."""
    if not path.exists():
        raise ValueError(f"global top-10 file is missing: {path}")
    try:
        contents = path.read_text()
    except OSError as error:
        raise ValueError(f"cannot read global top-10 file: {path}") from error
    if not contents.strip():
        raise ValueError(f"global top-10 file is empty: {path}")
    try:
        records = json.loads(contents)
    except json.JSONDecodeError as error:
        raise ValueError(f"malformed JSON in global top-10 file: {path}") from error
    if not isinstance(records, list) or not records:
        raise ValueError(f"global top-10 file is empty: {path}")
    parents: list[int] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"invalid parent record in global top-10 file: {path}")
        value = _validate_canonical_1000_digit(record.get("starting_integer"), "parent in global top-10 file", path)
        if value in seen:
            raise ValueError(f"duplicate parent in global top-10 file: {path}")
        seen.add(value)
        parents.append(int(value))
    return parents


def load_lineage_weights(
    path: Path,
    prefix_length: int = DEFAULT_PREFIX_LENGTH,
    *,
    expected_strategy: str | None = None,
    expected_experiment_id: str | None = None,
    completed_outcomes: frozenset[str] | None = None,
) -> list[tuple[int, int]]:
    """Load parent weights from a lineage top-ten file, preserving first-seen parent order."""
    if not path.exists():
        raise ValueError(f"source top-10 file is missing: {path}")
    try:
        contents = path.read_text()
    except OSError as error:
        raise ValueError(f"cannot read source top-10 file: {path}") from error
    if not contents.strip():
        raise ValueError(f"source top-10 file is empty: {path}")
    try:
        records = json.loads(contents)
    except json.JSONDecodeError as error:
        raise ValueError(f"malformed JSON in source top-10 file: {path}") from error
    if not isinstance(records, list):
        raise ValueError(f"source top-10 file is not a nonempty list: {path}")
    if not records:
        raise ValueError(f"source top-10 file is empty: {path}")
    weights: OrderedDict[str, int] = OrderedDict()
    first_seen: dict[str, int] = {}
    observed_prefix: int | None = None
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"invalid descendant record in source top-10 file: {path}")
        if expected_strategy is not None and record.get("strategy") != expected_strategy:
            raise ValueError(f"source top-10 file contains a foreign strategy record: {path}")
        if expected_experiment_id is not None and record.get("experiment_id") != expected_experiment_id:
            raise ValueError(f"source top-10 file contains a foreign experiment record: {path}")
        if completed_outcomes is not None and record.get("outcome") not in completed_outcomes:
            raise ValueError(f"source top-10 file contains an incomplete or invalid outcome: {path}")
        if "parent_starting_integer" not in record or "prefix_length" not in record:
            raise ValueError(f"source top-10 file is missing lineage fields: {path}")
        parent = _validate_canonical_1000_digit(
            record["parent_starting_integer"], "parent lineage in source top-10 file", path
        )
        record_prefix = record["prefix_length"]
        if not isinstance(record_prefix, int) or isinstance(record_prefix, bool) or record_prefix < 1:
            raise ValueError(f"invalid prefix length in source top-10 file: {path}")
        if observed_prefix is None:
            observed_prefix = record_prefix
        elif record_prefix != observed_prefix:
            raise ValueError(f"source top-10 file has inconsistent prefix lengths: {path}")
        if record_prefix != prefix_length:
            raise ValueError(
                f"source top-10 prefix length {record_prefix} does not match requested {prefix_length}: {path}"
            )
        if parent not in first_seen:
            first_seen[parent] = len(first_seen)
        weights[parent] = weights.get(parent, 0) + 1
    ordered = sorted(weights.items(), key=lambda item: (-item[1], first_seen[item[0]]))
    return [(int(parent), weight) for parent, weight in ordered]


def balanced_allocation(count: int, parents: list[int]) -> list[int]:
    """Allocate candidates across parents with counts differing by at most one."""
    if count < 0 or not parents:
        raise ValueError("count must be nonnegative and parents must be nonempty")
    base, extra = divmod(count, len(parents))
    return [base + (index < extra) for index in range(len(parents))]


def weighted_allocation(count: int, weights: list[int]) -> list[int]:
    """Proportionally allocate exactly ``count`` by weight using deterministic remainders."""
    if (not isinstance(count, int) or isinstance(count, bool) or count < 0
            or not weights or any(not isinstance(w, int) or isinstance(w, bool) or w < 1 for w in weights)):
        raise ValueError("count must be nonnegative and weights must be positive integers")
    total_weight = sum(weights)
    floors = [(count * weight) // total_weight for weight in weights]
    remaining = count - sum(floors)
    remainders = [(count * weight) % total_weight for weight in weights]
    allocation = floors[:]
    for index in sorted(range(len(weights)), key=lambda i: (-remainders[i], i))[:remaining]:
        allocation[index] += 1
    return allocation


def _parity_prefix_candidate_records_with_allocation(
    parents: list[int], allocation: list[int], seed: str, prefix_length: int, strategy_domain: str,
) -> Iterator[tuple[int, int]]:
    low, high = 10**999, 10**1000 - 1
    modulus = 1 << prefix_length
    excluded = set(parents)
    seen: set[int] = set()
    seed_bytes = seed.encode()
    for parent_index, (parent, quota) in enumerate(zip(parents, allocation)):
        residue = parent % modulus
        quotient_low = (low - residue + modulus - 1) // modulus
        quotient_high = (high - residue) // modulus
        width = quotient_high - quotient_low + 1
        produced = attempt = 0
        domain = strategy_domain.encode() + b":" + parent_index.to_bytes(4, "big")
        while produced < quota:
            offset = _sample_below(width, seed_bytes, domain, attempt)
            attempt += 1
            if offset is None:
                continue
            candidate = residue + modulus * (quotient_low + offset)
            if candidate in excluded or candidate in seen:
                continue
            seen.add(candidate)
            produced += 1
            yield candidate, parent


def parity_prefix_candidate_records(
    count: int, parents: list[int], seed: str = "parity-prefix-v1",
    prefix_length: int = DEFAULT_PREFIX_LENGTH,
) -> Iterator[tuple[int, int]]:
    """Yield ``(descendant, parent)`` pairs sampled evenly across each congruence class."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must be nonnegative")
    if not isinstance(prefix_length, int) or isinstance(prefix_length, bool) or prefix_length < 1:
        raise ValueError("prefix_length must be a positive integer")
    allocation = balanced_allocation(count, parents)
    yield from _parity_prefix_candidate_records_with_allocation(
        parents, allocation, seed, prefix_length, S1_STRATEGY
    )


def weighted_parity_prefix_candidate_records(
    count: int, parent_weights: list[tuple[int, int]], seed: str = "parity-prefix-v1",
    prefix_length: int = DEFAULT_PREFIX_LENGTH, strategy_domain: str = S2_STRATEGY,
) -> Iterator[tuple[int, int]]:
    """Yield parity-prefix candidates proportionally allocated by productive lineage weight."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must be nonnegative")
    if not isinstance(prefix_length, int) or isinstance(prefix_length, bool) or prefix_length < 1:
        raise ValueError("prefix_length must be a positive integer")
    parents = [parent for parent, _ in parent_weights]
    allocation = weighted_allocation(count, [weight for _, weight in parent_weights])
    yield from _parity_prefix_candidate_records_with_allocation(
        parents, allocation, seed, prefix_length, strategy_domain
    )


def parity_prefix_candidates(count: int, parents: list[int], seed: str = "parity-prefix-v1",
                             prefix_length: int = DEFAULT_PREFIX_LENGTH) -> Iterator[int]:
    """Yield only candidate values for the guided strategy."""
    for candidate, _ in parity_prefix_candidate_records(count, parents, seed, prefix_length):
        yield candidate
