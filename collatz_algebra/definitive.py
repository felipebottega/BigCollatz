"""Exact cycle decisions by composing compressed exponent words."""

from __future__ import annotations

from pathlib import Path

from .binary_interval import isolate_candidate
from .closure_interval import noninteger_closure
from .modular_closure import DEFAULT_MODULUS_BITS, closure_certificate
from .grammar import Repeat, Word, counts


def verify_exact(
    word: Word, *, modulus_bits: int = DEFAULT_MODULUS_BITS, checkpoint_dir: Path | None = None
) -> dict[str, object]:
    """Decide closure by interval isolation and an exact modular proof.

    Divisibility by the full power of two implies divisibility at each
    prefix because the remaining multiplier is odd. Each intermediate
    integer is odd because its next update multiplies it by three, adds one,
    and produces an even numerator.
    """
    odd_steps, total_divisions = counts(word)
    # A real affine map with a positive multiplier and any positive power
    # share the same fixed points. A whole-word repeat can therefore be
    # verified by its base, including the exact divisibility of every step.
    while isinstance(word, Repeat):
        word = word.word
    result = {
        "schema": "collatz-algebra-definitive-v2",
        "method": "exact_modular_closure",
        "counts": {
            "odd_steps": str(odd_steps),
            "total_divisions": str(total_divisions),
            "unaccelerated_period": str(odd_steps + total_divisions),
        },
        "definitive": True,
    }

    interval = noninteger_closure(word)
    if interval is not None:
        return {
            **result,
            "method": "directed_affine_interval",
            "is_cycle": False,
            "conclusion": "not_a_cycle",
            "reason": "nonintegral_closure",
            "closure_interval": interval,
        }

    candidate = isolate_candidate(word, counts(word)[1])
    if candidate.start is None:
        return {
            **result, "method": "directed_binary_interval", "is_cycle": False,
            "conclusion": "not_a_cycle", "reason": candidate.reason,
        }

    start = candidate.start
    proof = closure_certificate(
        word, start, candidate.residual_bits, modulus_bits=modulus_bits,
        checkpoint_dir=checkpoint_dir,
    )
    try:
        starting_integer = str(start)
    except ValueError:
        starting_integer = hex(start)
    result["modular_certificate"] = {
        **proof, "candidate": starting_integer, "isolation_precision": candidate.precision,
    }
    if proof["nonzero_witness"] is not None:
        return {
            **result, "is_cycle": False, "conclusion": "not_a_cycle",
            "reason": "nonintegral_closure",
        }
    return {
        **result,
        "is_cycle": True,
        "conclusion": "confirmed_trivial_cycle" if start == 1 else "confirmed_nontrivial_cycle",
        "starting_integer": starting_integer,
    }
