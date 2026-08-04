"""Simple deterministic baseline candidate generation."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator


def baseline_candidates(count: int, digits: int, seed: str = "p0-baseline-v1") -> Iterator[int]:
    """Expand SHA-256 counter blocks and map them uniformly into the digit range."""
    if count < 0 or not 500 <= digits <= 1000:
        raise ValueError("count must be nonnegative and digits must be 500..1000")
    low, width = 10 ** (digits - 1), 9 * 10 ** (digits - 1)
    for ordinal in range(count):
        material, block = bytearray(), 0
        while len(material) * 8 < width.bit_length() + 128:
            material.extend(hashlib.sha256(f"{seed}:{ordinal}:{block}".encode()).digest())
            block += 1
        yield low + int.from_bytes(material, "big") % width
