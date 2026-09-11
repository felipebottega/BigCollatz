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


def decimal_integer(value: str) -> int:
    """Parse a canonical decimal without Python's configurable digit ceiling."""
    if not isinstance(value, str) or not value or not value.isascii():
        raise ValueError("value must be a canonical decimal string")
    sign = -1 if value.startswith("-") else 1
    unsigned = value[1:] if sign < 0 else value
    if (
        not unsigned.isdecimal()
        or (len(unsigned) > 1 and unsigned.startswith("0"))
        or value == "-0"
    ):
        raise ValueError("value must be a canonical decimal string")
    result = 0
    for start in range(0, len(unsigned), 9):
        chunk = unsigned[start : start + 9]
        result = result * (10 ** len(chunk)) + int(chunk)
    return sign * result
