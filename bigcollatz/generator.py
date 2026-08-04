"""Simple deterministic baseline candidate generation."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator


def baseline_candidates(count: int, digits: int, seed: str = "p0-baseline-v1") -> Iterator[int]:
    """Sample the decimal stratum uniformly with domain-separated rejection sampling."""
    if (not isinstance(count, int) or isinstance(count, bool) or count < 0 or
            not isinstance(digits, int) or isinstance(digits, bool) or not 500 <= digits <= 1000):
        raise ValueError("count must be nonnegative and digits must be 500..1000")
    low, width = 10 ** (digits - 1), 9 * 10 ** (digits - 1)
    byte_count = (width.bit_length() + 7) // 8
    sample_space = 1 << (8 * byte_count)
    acceptance_limit = sample_space - sample_space % width
    seen: set[int] = set()
    for ordinal in range(count):
        attempt = 0
        while True:
            material = bytearray()
            for block in range((byte_count + 31) // 32):
                domain = f"{seed}:digits={digits}:ordinal={ordinal}:attempt={attempt}:block={block}"
                material.extend(hashlib.sha256(domain.encode()).digest())
            sample = int.from_bytes(material[:byte_count], "big")
            candidate = low + sample % width
            if sample < acceptance_limit and candidate not in seen:
                seen.add(candidate)
                yield candidate
                break
            attempt += 1
