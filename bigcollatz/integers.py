"""Integer formatting helpers that do not inherit Python's decimal digit limit."""

from __future__ import annotations


def decimal_string(value: int) -> str:
    """Format an integer exactly even when ``sys.int_max_str_digits`` is active."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("value must be an integer")
    try:
        return str(value)
    except ValueError:
        if value == 0:
            return "0"
        sign = "-" if value < 0 else ""
        remaining = abs(value)
        base = 1_000_000_000
        chunks: list[int] = []
        while remaining:
            remaining, chunk = divmod(remaining, base)
            chunks.append(chunk)
        return (
            sign
            + str(chunks[-1])
            + "".join(f"{chunk:09d}" for chunk in reversed(chunks[:-1]))
        )
