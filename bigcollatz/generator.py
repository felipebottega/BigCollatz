"""Simple deterministic baseline candidate generation."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator


def baseline_candidates(count: int, seed: str = "baseline-v1") -> Iterator[int]:
    """Generate a deterministic, distinct sequence of uniformly offset 1000-digit values."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must be nonnegative")
    low, width = 10**999, 9 * 10**999
    offset = int.from_bytes(hashlib.sha256(seed.encode()).digest(), "big") % width
    for ordinal in range(count):
        yield low + (offset + ordinal) % width
