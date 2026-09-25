"""Necessary-condition sieve for compressed Collatz cycle words."""

from __future__ import annotations

from decimal import Decimal, localcontext
from math import gcd
from typing import Iterable

from .grammar import Word, counts, is_manifestly_imprimitive
from .modular import evaluate_mod

DEFAULT_MINIMUM_PERIOD = 186_000_000_000
DEFAULT_PRIME_LIMIT = 10_000


def _primes_through(limit: int) -> list[int]:
    if limit < 2:
        return []
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for value in range(2, int(limit**0.5) + 1):
        if sieve[value]:
            sieve[value * value : limit + 1 : value] = b"\x00" * (
                (limit - value * value) // value + 1
            )
    return [value for value in range(5, limit + 1) if sieve[value]]


def targeted_moduli(odd_steps: int, total_divisions: int, limit: int) -> list[int]:
    """Return small primes that divide ``2**S - 3**k`` without building it."""

    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 5:
        raise ValueError("prime_limit must be an integer of at least 5")
    return [
        prime
        for prime in _primes_through(limit)
        if pow(2, total_divisions, prime) == pow(3, odd_steps, prime)
    ]


def _log_gap(odd_steps: int, total_divisions: int) -> str:
    # This value is explicitly diagnostic, not used as a proof. Decimal.ln is
    # correctly rounded for its context but is not an interval computation.
    with localcontext() as context:
        context.prec = 60
        gap = Decimal(total_divisions) * Decimal(2).ln()
        gap -= Decimal(odd_steps) * Decimal(3).ln()
    return str(gap)


def analyze(
    word: Word,
    moduli: Iterable[int] | None = None,
    minimum_period: int = DEFAULT_MINIMUM_PERIOD,
    prime_limit: int = DEFAULT_PRIME_LIMIT,
) -> dict[str, object]:
    """Apply rigorous cheap filters and return a machine-readable report.

    A modular rejection is a certificate: closure requires ``D*n = A`` where
    ``D = 2**S - 3**k``.  The congruence has a solution modulo ``m`` only when
    ``gcd(D, m)`` divides ``A``.
    """

    if (
        isinstance(minimum_period, bool)
        or not isinstance(minimum_period, int)
        or minimum_period < 1
    ):
        raise ValueError("minimum_period must be a positive integer")
    odd_steps, total_divisions = counts(word)
    period = odd_steps + total_divisions
    reasons: list[dict[str, object]] = []
    selected_moduli = (
        targeted_moduli(odd_steps, total_divisions, prime_limit)
        if moduli is None
        else list(moduli)
    )

    if period < minimum_period:
        reasons.append(
            {
                "filter": "minimum_period",
                "actual": str(period),
                "required": str(minimum_period),
            }
        )
    # 2**1054 < 3**665 proves log_2(3) > 1054/665 using only
    # small, exact integers. Hence 665*S <= 1054*k implies 2**S < 3**k,
    # while positive cycle closure requires the opposite inequality.
    if 665 * total_divisions <= 1054 * odd_steps:
        reasons.append(
            {
                "filter": "nonpositive_closure_denominator",
                "bound": "665*S <= 1054*k",
                "rigorous": True,
            }
        )
    if is_manifestly_imprimitive(word):
        reasons.append({"filter": "top_level_power", "rigorous": True})

    modular_checks: list[dict[str, object]] = []
    for modulus in selected_moduli:
        residue = evaluate_mod(word, modulus)
        coefficient = (residue.denominator - residue.multiplier) % modulus
        divisor = gcd(coefficient, modulus)
        passed = residue.additive % divisor == 0
        check = {
            "modulus": str(modulus),
            "gcd": str(divisor),
            "additive_mod_gcd": str(residue.additive % divisor),
            "passed": passed,
        }
        modular_checks.append(check)
        if not passed:
            reasons.append({"filter": "closure_congruence", **check})

    return {
        "schema": "collatz-algebra-sieve-v1",
        "counts": {
            "odd_steps": str(odd_steps),
            "total_divisions": str(total_divisions),
            "unaccelerated_period": str(period),
        },
        "diagnostics": {
            "log_gap_s_ln2_minus_k_ln3": _log_gap(odd_steps, total_divisions),
            "log_gap_is_not_a_proof": True,
        },
        "modulus_selection": {
            "mode": "targeted_small_prime_divisors" if moduli is None else "explicit",
            "prime_limit": prime_limit if moduli is None else None,
            "selected_count": len(selected_moduli),
        },
        "modular_checks": modular_checks,
        "rejected": bool(reasons),
        "rejection_certificates": reasons,
        "conclusion": (
            "impossible_for_the_requested_model"
            if reasons
            else "survives_necessary_conditions_not_a_confirmed_cycle"
        ),
    }
