"""Deterministic baseline candidate generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path


def load_global_top_10(path: Path) -> list[int]:
    """Load the distinct, positive, 1000-digit starts in a global top-ten file."""
    if path.is_dir():
        path = path / "results" / "global_top_10.json"
    if not path.exists():
        raise ValueError(f"global top-10 file does not exist: {path}")
    if not path.read_text().strip():
        raise ValueError(f"global top-10 file is empty: {path}")
    try:
        records = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(f"invalid global top-10 file: {path}") from error
    if not isinstance(records, list) or not records:
        raise ValueError("global top-10 must be a nonempty JSON list")

    parents: list[int] = []
    for record in records:
        if not isinstance(record, dict) or "starting_integer" not in record:
            raise ValueError("invalid global top-10 record")
        raw_parent = record["starting_integer"]
        if not isinstance(raw_parent, str) or not raw_parent.isdecimal():
            raise ValueError("invalid parent starting integer")
        parent = int(raw_parent)
        if parent <= 0:
            raise ValueError("parent starting integers must be positive")
        if len(raw_parent) != 1000 or raw_parent[0] == "0":
            raise ValueError("parent starting integers must have exactly 1000 decimal digits")
        if parent in parents:
            raise ValueError("duplicate parent starting integer")
        parents.append(parent)
    return parents


def baseline_candidates(count: int, seed: str = "baseline-v1") -> Iterator[int]:
    """Sample distinct 1000-digit integers with a deterministic SHA-256 stream."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must be nonnegative")
    low, width = 10**999, 9 * 10**999
    bit_count = width.bit_length()
    byte_count = (bit_count + 7) // 8
    seed_bytes = seed.encode()
    seen: set[int] = set()
    attempt = 0

    while len(seen) < count:
        # Expand independently addressed SHA-256 blocks.  Masking and rejecting
        # values outside ``width`` avoids the bias introduced by reduction modulo
        # an interval whose size is not a power of two.
        material = bytearray()
        block = 0
        while len(material) < byte_count:
            digest_input = (
                b"bigcollatz:S0-uniform-deterministic\0"
                + len(seed_bytes).to_bytes(8, "big")
                + seed_bytes
                + attempt.to_bytes(16, "big")
                + block.to_bytes(4, "big")
            )
            material.extend(hashlib.sha256(digest_input).digest())
            block += 1
        sampled = int.from_bytes(material[:byte_count], "big")
        sampled &= (1 << bit_count) - 1
        attempt += 1
        if sampled >= width:
            continue
        candidate = low + sampled
        if candidate in seen:
            continue
        seen.add(candidate)
        yield candidate
