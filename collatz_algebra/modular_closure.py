"""Exact zero proof from distinct prime powers, without forming their product."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isqrt
from pathlib import Path
import tempfile
from typing import Iterator

from .grammar import Concat, Repeat, Step, Word
from .modular import evaluate_mod
from .sieve import _primes_through


DEFAULT_MODULUS_BITS = 16_384
_CHECKPOINT_BATCH = 128
_PRIME_SEGMENT = 32_768


def _primes_after(last: int) -> Iterator[int]:
    for prime in (2, 3):
        if prime > last:
            yield prime
    low = max(5, last + 1)
    while True:
        high = low + _PRIME_SEGMENT - 1
        flags = bytearray(b"\x01") * _PRIME_SEGMENT
        for p in (2, 3, *_primes_through(isqrt(high))):
            first = max(p * p, ((low + p - 1) // p) * p)
            if first <= high:
                flags[first - low::p] = (
                    b"\x00" * ((high - first) // p + 1)
                )
        for offset, flag in enumerate(flags):
            if flag:
                yield low + offset
        low = high + 1


def _modulus(prime: int, modulus_bits: int, remaining_bits: int) -> tuple[int, int]:
    # Near the end use a smaller prime power when it suffices. The base
    # prime is the minimum possible modulus, even for a tiny bit target.
    target = min(modulus_bits, remaining_bits + 1)
    exponent = max(1, (target - 1) // prime.bit_length())
    return prime**exponent, exponent


def _word_key(word: Word) -> str:
    digest = sha256()

    def add(node):
        if isinstance(node, Step):
            digest.update(f"s{node.divisions:x};".encode())
        elif isinstance(node, Repeat):
            digest.update(f"r{node.times:x}:".encode())
            add(node.word)
        elif isinstance(node, Concat):
            digest.update(b"[")
            for part in node.parts:
                add(part)
            digest.update(b"]")

    add(word)
    return digest.hexdigest()


@dataclass(slots=True)
class _Progress:
    last_prime: int = 1
    covered_bits: int = 0
    zero_moduli: int = 0
    witness: dict[str, int | str] | None = None


def _checksum(data: dict) -> str:
    return sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _load(path: Path, identity: dict) -> _Progress:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _Progress()
    except ValueError as error:
        raise ValueError(f"Unreadable modular checkpoint: {path}") from error
    try:
        payload = record["payload"]
        if payload["identity"] != identity or record["sha256"] != _checksum(payload):
            raise ValueError
        progress = _Progress(**payload["progress"])
        if (type(progress.last_prime) is not int or progress.last_prime < 1
                or type(progress.covered_bits) is not int or progress.covered_bits < 0
                or type(progress.zero_moduli) is not int or progress.zero_moduli < 0
                or progress.covered_bits < progress.zero_moduli
                or (progress.last_prime == 1) != (progress.zero_moduli == 0)
                or (progress.witness is not None and not isinstance(progress.witness, dict))):
            raise ValueError
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid modular checkpoint: {path}") from error
    return progress


def _save(path: Path, identity: dict, progress: _Progress) -> None:
    payload = {"identity": identity, "progress": asdict(progress)}
    data = {"payload": payload, "sha256": _checksum(payload)}
    pending = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            pending = Path(handle.name)
            json.dump(data, handle)
        pending.replace(path)
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)


def closure_certificate(
    word: Word,
    start: int,
    residual_bits: int,
    *,
    modulus_bits: int = DEFAULT_MODULUS_BITS,
    checkpoint_dir: Path | None = None,
) -> dict[str, object]:
    """Test R = A - (2**S - 3**k)*start given the strict bound |R| < 2**residual_bits.

    Each modulus uses a new prime base, so zero residues prove divisibility
    by their product. Summing floor(log2(modulus)) gives an exact lower
    bound on the product's bit scale without allocating the product.
    """
    if type(residual_bits) is not int or residual_bits < 1:
        raise ValueError("residual_bits must be a positive integer")
    if type(modulus_bits) is not int or modulus_bits < 2:
        raise ValueError("modulus_bits must be at least 2")

    progress = _Progress()
    path = None
    identity = {}
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        identity = {
            "schema": "collatz-modular-checkpoint-v1",
            "word": _word_key(word),
            "candidate": hex(start),
            "residual_bits": residual_bits,
            "modulus_bits": modulus_bits,
        }
        path = checkpoint_dir / f"{_checksum(identity)}.json"
        progress = _load(path, identity)

    if progress.witness is None and progress.covered_bits < residual_bits:
        for prime in _primes_after(progress.last_prime):
            modulus, exponent = _modulus(prime, modulus_bits, residual_bits - progress.covered_bits)
            affine = evaluate_mod(word, modulus)
            residue = (
                affine.additive - (affine.denominator - affine.multiplier) * (start % modulus)
            ) % modulus
            if residue:
                progress.witness = {"prime": prime, "power": exponent, "residue_hex": hex(residue)}
                break
            progress.last_prime = prime
            progress.zero_moduli += 1
            progress.covered_bits += modulus.bit_length() - 1
            if progress.covered_bits >= residual_bits:
                break
            if path is not None and progress.zero_moduli % _CHECKPOINT_BATCH == 0:
                _save(path, identity, progress)
        if path is not None:
            _save(path, identity, progress)

    return {
        "scheme": "distinct_prime_powers_v1",
        "residual_bound_bits": str(residual_bits),
        "modulus_bits": modulus_bits,
        "prime_product_lower_bound_bits": str(progress.covered_bits),
        "zero_moduli": progress.zero_moduli,
        "last_zero_prime": progress.last_prime,
        "nonzero_witness": progress.witness,
    }
