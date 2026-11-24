"""Audit exact modular closure against direct arithmetic and interruption."""

from fractions import Fraction
from itertools import islice, product
import json
from math import isqrt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from collatz_algebra.binary_interval import isolate_candidate
from collatz_algebra.definitive import verify_exact
from collatz_algebra.grammar import Concat, Repeat, Step
from collatz_algebra.modular import evaluate_mod
from collatz_algebra.modular_closure import _primes_after, closure_certificate


def _is_prime(n):
    return n >= 2 and all(n % divisor for divisor in range(2, isqrt(n) + 1))


class ModularClosureTests(unittest.TestCase):
    def test_segmented_primes_match_trial_division_at_resume_boundaries(self):
        for start in (1, 2, 3, 32_755, 1_000_000):
            expected = [n for n in range(start + 1, start + 1500) if _is_prime(n)][:30]
            self.assertEqual(list(islice(_primes_after(start), 30)), expected)

    def test_zero_residues_reach_the_required_product_bound(self):
        word = Concat((Repeat(Step(2), 1000), Step(2)))
        report = verify_exact(word, modulus_bits=16)
        self.assertTrue(report["is_cycle"])
        self.assertEqual(report["starting_integer"], "1")
        proof = report["modular_certificate"]
        self.assertGreater(proof["zero_moduli"], 1)
        self.assertIsNone(proof["nonzero_witness"])
        # Reconstruct the small test product using an independent prime
        # generator and direct closed-form integer coefficients.
        remaining = int(proof["residual_bound_bits"])
        combined = 1
        checked = 0
        numerator = (1 << 2002) - 3**1001
        for prime in range(2, proof["last_zero_prime"] + 1):
            if not _is_prime(prime):
                continue
            exponent = max(1, (min(16, remaining + 1) - 1) // prime.bit_length())
            modulus = prime**exponent
            self.assertEqual((numerator - numerator * int(proof["candidate"])) % modulus, 0)
            combined *= modulus
            checked += 1
            remaining -= modulus.bit_length() - 1
        self.assertEqual(checked, proof["zero_moduli"])
        self.assertLessEqual(remaining, 0)
        self.assertGreaterEqual(combined, 1 << int(proof["residual_bound_bits"]))

    def test_primitive_giant_closure_reaches_a_nonzero_residue_after_two_zeros(self):
        repeats = 72_057_431_991
        word = Concat((Step(3), Repeat(Step(2), repeats)))
        report = verify_exact(word, modulus_bits=2)
        self.assertEqual(report["method"], "exact_modular_closure")
        self.assertEqual(report["counts"]["odd_steps"], str(repeats + 1))
        self.assertFalse(report["is_cycle"])
        proof = report["modular_certificate"]
        self.assertEqual(proof["candidate"], "1")
        self.assertEqual(proof["zero_moduli"], 2)
        self.assertLess(int(proof["prime_product_lower_bound_bits"]),
                        int(proof["residual_bound_bits"]))
        witness = proof["nonzero_witness"]
        self.assertEqual(witness["prime"], 5)
        modulus = witness["prime"] ** witness["power"]
        # The numerator of T(1) - 1 is exactly -4 * 3**repeats.
        self.assertEqual(int(witness["residue_hex"], 16), (-4 * pow(3, repeats, modulus)) % modulus)

    def test_resume_neither_repeats_nor_double_counts_saved_moduli(self):
        word = Concat((Repeat(Step(2), 50), Step(2)))
        checked, resumed = [], []

        def interrupt_after_two(word, modulus):
            if len(checked) == 2:
                raise KeyboardInterrupt
            checked.append(modulus)
            return evaluate_mod(word, modulus)

        def observe_resume(word, modulus):
            resumed.append(modulus)
            return evaluate_mod(word, modulus)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch("collatz_algebra.modular_closure._CHECKPOINT_BATCH", 2), patch(
                "collatz_algebra.modular_closure.evaluate_mod", side_effect=interrupt_after_two
            ), self.assertRaises(KeyboardInterrupt):
                closure_certificate(word, 1, 60, modulus_bits=8, checkpoint_dir=path)

            with patch("collatz_algebra.modular_closure.evaluate_mod", side_effect=observe_resume):
                restored = closure_certificate(word, 1, 60, modulus_bits=8, checkpoint_dir=path)

            self.assertFalse(set(checked) & set(resumed))
            self.assertEqual(restored["zero_moduli"], len(checked) + len(resumed))
            self.assertEqual(restored, closure_certificate(word, 1, 60, modulus_bits=8))
            self.assertEqual(
                restored, closure_certificate(word, 1, 60, modulus_bits=8, checkpoint_dir=path)
            )

            checkpoint, = path.iterdir()
            record = json.loads(checkpoint.read_text(encoding="utf-8"))
            record["payload"]["progress"]["covered_bits"] += 1
            checkpoint.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid modular checkpoint"):
                closure_certificate(word, 1, 60, modulus_bits=8, checkpoint_dir=path)

    def test_logical_exponents_beyond_decimal_range_do_not_limit_verification(self):
        huge = 10**25
        word = Concat((Step(3), Repeat(Step(2), huge)))
        match = verify_exact(word, modulus_bits=2)
        self.assertEqual(match["method"], "exact_modular_closure")
        self.assertFalse(match["is_cycle"])

    def test_dyadic_isolation_and_modular_verdict_match_exact_small_words(self):
        # An independent affine recurrence gives the exact integer answer.
        for k in range(1, 6):
            for exponents in product(range(1, 4), repeat=k):
                additive, divisions = 0, 0
                for d in exponents:
                    additive = 3 * additive + (1 << divisions)
                    divisions += d
                denominator = (1 << divisions) - 3**k
                word = Concat(tuple(Step(d) for d in exponents))
                candidate = isolate_candidate(word, divisions)
                is_cycle = denominator > 0 and additive % denominator == 0
                if candidate.start is None:
                    self.assertFalse(is_cycle, exponents)
                else:
                    residual = additive - denominator * candidate.start
                    self.assertLess(abs(residual), 1 << candidate.residual_bits)
                    self.assertLess(abs(Fraction(additive, denominator) - candidate.start), 2)
                    result = closure_certificate(word, candidate.start, candidate.residual_bits)
                    self.assertEqual(result["nonzero_witness"] is None, is_cycle, exponents)
