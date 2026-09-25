import json
import tempfile
import unittest
from pathlib import Path

from collatz_algebra.cli import main
from collatz_algebra.confirmation import confirm, exact_affine
from collatz_algebra.grammar import Concat, Repeat, Step, counts, parse_word
from collatz_algebra.modular import evaluate_mod
from collatz_algebra.sieve import analyze, targeted_moduli


def expand(word):
    if isinstance(word, Step):
        return [word.divisions]
    if isinstance(word, Concat):
        return sum((expand(part) for part in word.parts), [])
    return expand(word.word) * word.times


def direct(word, modulus):
    multiplier, additive, denominator = 1, 0, 1
    for divisions in expand(word):
        additive = (3 * additive + denominator) % modulus
        multiplier = 3 * multiplier % modulus
        denominator = denominator * pow(2, divisions, modulus) % modulus
    return multiplier, additive, denominator


class GrammarTests(unittest.TestCase):
    def test_large_counts_do_not_expand(self):
        word = Repeat(Concat((Step(1), Step(2))), 93_000_000_000)
        self.assertEqual(counts(word), (186_000_000_000, 279_000_000_000))

    def test_json_parser_accepts_decimal_repeat_and_rejects_bad_nodes(self):
        word = parse_word(
            {"repeat": {"word": {"step": 2}, "times": "186000000000"}}
        )
        self.assertEqual(counts(word), (186_000_000_000, 372_000_000_000))
        for invalid in ({}, {"step": 1, "concat": []}, {"step": True}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_word(invalid)


class ModularTests(unittest.TestCase):
    def test_compressed_evaluation_matches_expansion(self):
        word = Concat((Repeat(Concat((Step(1), Step(3))), 7), Step(2)))
        for modulus in (7, 25, 97, 641):
            residue = evaluate_mod(word, modulus)
            self.assertEqual(
                (residue.multiplier, residue.additive, residue.denominator),
                direct(word, modulus),
            )

    def test_billion_scale_repeat_uses_modular_powering(self):
        word = Concat((Repeat(Step(2), 186_000_000_000), Step(1)))
        residue = evaluate_mod(word, 2_147_483_647)
        self.assertTrue(0 <= residue.additive < 2_147_483_647)


class ConfirmationTests(unittest.TestCase):
    def test_exact_affine_matches_direct_small_word(self):
        word = Concat((Step(1), Step(3), Step(2)))
        affine = exact_affine(word)
        self.assertEqual(
            (affine.multiplier, affine.additive, affine.denominator),
            direct(word, affine.denominator + 1),
        )

    def test_trivial_cycle_is_confirmed_by_exact_replay(self):
        result = confirm(Step(2))
        self.assertEqual(result["status"], "confirmed_cycle")
        self.assertTrue(result["confirmed"])
        self.assertTrue(result["trivial"])
        self.assertEqual(result["starting_integer"], "1")

    def test_nonintegral_and_imprimitive_words_are_rejected(self):
        self.assertEqual(confirm(Step(3))["reason"], "nonintegral_closure_candidate")
        result = confirm(Concat((Step(2), Step(2))))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "imprimitive_word")

    def test_billion_scale_word_reports_resource_limit_not_survival(self):
        word = Concat((Repeat(Step(1), 80_000_000_000), Repeat(Step(2), 40_000_000_000)))
        result = confirm(word)
        self.assertEqual(result["status"], "resource_limit")
        self.assertFalse(result["confirmed"])
        self.assertEqual(result["odd_steps"], "120000000000")


class SieveTests(unittest.TestCase):
    def test_targeted_moduli_are_actual_closure_coefficient_divisors(self):
        for modulus in targeted_moduli(125_000_000_001, 200_000_000_003, 3_000):
            self.assertEqual(
                pow(2, 200_000_000_003, modulus),
                pow(3, 125_000_000_001, modulus),
            )

    def test_exact_rational_bound_rejects_nonpositive_denominator(self):
        report = analyze(Concat((Step(1), Step(2))), moduli=(), minimum_period=1)
        self.assertIn(
            "nonpositive_closure_denominator",
            [item["filter"] for item in report["rejection_certificates"]],
        )

    def test_trivial_cycle_survives_closure_but_period_filter_rejects(self):
        report = analyze(Step(2), moduli=(5, 7, 31), minimum_period=186_000_000_000)
        self.assertTrue(report["rejected"])
        self.assertEqual(report["modular_checks"][0]["passed"], True)
        self.assertEqual(
            report["rejection_certificates"][0]["filter"], "minimum_period"
        )

    def test_modular_unsatisfiability_is_reported_as_certificate(self):
        # Word [1, 1] has D = 4 - 9 = -5 and A = 5. Modulo 25 the
        # congruence is solvable; changing to [1, 2] gives D = -1 and no
        # rejection. Search a tiny oracle to exercise a genuine certificate.
        found = None
        for left in range(1, 5):
            for right in range(1, 5):
                candidate = Concat((Step(left), Step(right)))
                report = analyze(candidate, moduli=(25,), minimum_period=1)
                if any(
                    reason["filter"] == "closure_congruence"
                    for reason in report["rejection_certificates"]
                ):
                    found = report
                    break
            if found:
                break
        self.assertIsNotNone(found)

    def test_cli_writes_stable_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "word.json"
            output = root / "report.json"
            source.write_text(json.dumps({"step": 2}), encoding="utf-8")
            self.assertEqual(
                main(
                    [
                        str(source),
                        "--minimum-period",
                        "1",
                        "--modulus",
                        "5",
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["schema"],
                "collatz-algebra-sieve-v1",
            )

    def test_cli_confirmation_has_distinct_success_and_resource_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trivial = root / "trivial.json"
            huge = root / "huge.json"
            output = root / "report.json"
            trivial.write_text(json.dumps({"step": 2}), encoding="utf-8")
            huge.write_text(
                json.dumps(
                    {
                        "concat": [
                            {"repeat": {"word": {"step": 1}, "times": "40000000000"}},
                            {"repeat": {"word": {"step": 2}, "times": "80000000000"}},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                main(
                    [
                        str(trivial),
                        "--minimum-period",
                        "1",
                        "--confirm",
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["confirmation"][
                    "status"
                ],
                "confirmed_cycle",
            )
            self.assertEqual(
                main(
                    [
                        str(huge),
                        "--minimum-period",
                        "1",
                        "--confirm",
                        "--modulus",
                        "2",
                        "--output",
                        str(output),
                    ]
                ),
                2,
            )
