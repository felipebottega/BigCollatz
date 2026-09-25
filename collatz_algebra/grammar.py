"""A straight-line grammar for accelerated Collatz exponent words.

The grammar never expands a repeated word.  This is the central representation
choice: a word containing billions of odd steps can still have a small syntax
tree and can be evaluated modulo an integer in logarithmic time per repetition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias


@dataclass(frozen=True, slots=True)
class Step:
    """One accelerated odd step ``(3n + 1) / 2**divisions``."""

    divisions: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.divisions, bool)
            or not isinstance(self.divisions, int)
            or self.divisions < 1
        ):
            raise ValueError("step divisions must be a positive integer")


@dataclass(frozen=True, slots=True)
class Concat:
    """Words applied from left to right."""

    parts: tuple[Word, ...]

    def __post_init__(self) -> None:
        if not self.parts:
            raise ValueError("concat must contain at least one word")


@dataclass(frozen=True, slots=True)
class Repeat:
    """A compressed repetition; the repeated word is never materialized."""

    word: Word
    times: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.times, bool)
            or not isinstance(self.times, int)
            or self.times < 1
        ):
            raise ValueError("repeat times must be a positive integer")


Word: TypeAlias = Step | Concat | Repeat


def _positive_integer(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a positive integer")
    if isinstance(value, str):
        if not value.isascii() or not value.isdecimal():
            raise ValueError(f"{field} must be a positive decimal integer")
        value = int(value)
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def parse_word(document: Any) -> Word:
    """Parse the deliberately small, unambiguous JSON grammar."""

    if not isinstance(document, dict) or len(document) != 1:
        raise ValueError("each word must have exactly one of: step, concat, repeat")
    if "step" in document:
        return Step(_positive_integer(document["step"], "step"))
    if "concat" in document:
        parts = document["concat"]
        if not isinstance(parts, list) or not parts:
            raise ValueError("concat must be a non-empty array")
        return Concat(tuple(parse_word(part) for part in parts))
    if "repeat" in document:
        repeat = document["repeat"]
        if not isinstance(repeat, dict) or set(repeat) != {"word", "times"}:
            raise ValueError("repeat must contain exactly word and times")
        return Repeat(
            parse_word(repeat["word"]),
            _positive_integer(repeat["times"], "repeat times"),
        )
    raise ValueError("unknown word node; expected step, concat, or repeat")


def counts(word: Word) -> tuple[int, int]:
    """Return ``(odd_steps, total_divisions)`` without expanding the word."""

    if isinstance(word, Step):
        return 1, word.divisions
    if isinstance(word, Concat):
        odd_steps = total_divisions = 0
        for part in word.parts:
            part_odd, part_divisions = counts(part)
            odd_steps += part_odd
            total_divisions += part_divisions
        return odd_steps, total_divisions
    odd_steps, total_divisions = counts(word.word)
    return odd_steps * word.times, total_divisions * word.times


def is_manifestly_imprimitive(word: Word) -> bool:
    """Detect the cheap, rigorous case where the complete word is a power."""

    return isinstance(word, Repeat) and word.times > 1
