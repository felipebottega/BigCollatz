"""Deterministic baseline candidate generation."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator


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
