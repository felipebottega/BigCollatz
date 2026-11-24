import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from collatz_algebra.cli import main
from collatz_algebra.definitive import verify_exact
from collatz_algebra.grammar import Concat, Repeat, Step, counts, parse_word
from collatz_algebra.modular import evaluate_mod
from collatz_algebra.sieve import analyze, targeted_moduli
from collatz_algebra.search import (
    Run, _evaluate_pattern, boundary_convergents, search_cycles, two_run_word,
)


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


class SieveTests(unittest.TestCase):
    def test_targeted_moduli_are_actual_closure_coefficient_divisors(self):
        for modulus in targeted_moduli(125_000_000_001, 200_000_000_003, 3_000):
            self.assertEqual(
                pow(2, 200_000_000_003, modulus),
                pow(3, 125_000_000_001, modulus),
            )

    def test_exact_rational_bound_rejects_nonpositive_denominator(self):
        report = analyze(Concat((Step(1), Step(2))), moduli=())
        self.assertIn(
            "nonpositive_closure_denominator",
            [item["filter"] for item in report["rejection_certificates"]],
        )

    def test_trivial_cycle_survives_closure_but_period_filter_rejects(self):
        report = analyze(Step(2), moduli=(5, 7, 31))
        self.assertTrue(report["rejected"])
        self.assertEqual(report["modular_checks"][0]["passed"], True)
        self.assertEqual(
            report["rejection_certificates"][0]["filter"], "minimum_period"
        )

    def test_fixed_period_bound_is_inclusive(self):
        for total_steps in (186_265_759_594, 186_265_759_595):
            with self.subTest(total_steps=total_steps):
                last_step = Step(1 if total_steps % 2 == 0 else 2)
                leading_steps = (total_steps - last_step.divisions - 1) // 2
                word = Concat((Repeat(Step(1), leading_steps), last_step))
                report = analyze(word, moduli=())
                self.assertEqual(report["counts"]["unaccelerated_period"], str(total_steps))
                period_checks = [
                    reason for reason in report["rejection_certificates"]
                    if reason["filter"] == "minimum_period"
                ]
                if total_steps == 186_265_759_594:
                    self.assertEqual(period_checks, [{
                        "filter": "minimum_period",
                        "actual": "186265759594",
                        "required": "186265759595",
                    }])
                else:
                    self.assertEqual(period_checks, [])

    def test_modular_unsatisfiability_is_reported_as_certificate(self):
        # Word [1, 1] has D = 4 - 9 = -5 and A = 5. Modulo 25 the
        # congruence is solvable; changing to [1, 2] gives D = -1 and no
        # rejection. Search a tiny oracle to exercise a genuine certificate.
        found = None
        for left in range(1, 5):
            for right in range(1, 5):
                candidate = Concat((Step(left), Step(right)))
                report = analyze(candidate, moduli=(25,))
                if any(
                    reason["filter"] == "closure_congruence"
                    for reason in report["rejection_certificates"]
                ):
                    found = report
                    break
            if found:
                break
        self.assertIsNotNone(found)


class MonteCarloSearchTests(unittest.TestCase):
    def test_cli_evaluates_and_refines_multiple_families(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            self.assertEqual(main([
                "--search-cycles", "150000000000", "--cases-per-level", "6",
                "--depth", "3", "--seed", "0", "--output", str(output),
            ]), 0)
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["schema"], "collatz-monte-carlo-search-v2")
        self.assertEqual([level["evaluated"] for level in report["levels"]], [6, 6, 6])
        self.assertEqual(sum(report["totals"].values()), 18)
        self.assertEqual(report["conclusion"], "all_candidates_rejected")
        candidates = {item["id"]: item for item in report["candidates"]}
        self.assertGreater(len(report["levels"][0]["families"]), 1)
        self.assertTrue(any(item["parent_id"] is not None for item in candidates.values()))
        self.assertTrue(any(item["level"] == 3 and item["parent_id"] is None
                            for item in candidates.values()))
        for item in candidates.values():
            runs = [(int(u), d, int(w)) for u, d, w in item["runs"]]
            odd_steps = sum(u + w for u, _, w in runs)
            divisions = sum(u + d*w for u, d, w in runs)
            self.assertLessEqual(odd_steps, 150_000_000_000)
            self.assertGreaterEqual(odd_steps + divisions, 186_265_759_595)
            self.assertTrue(all(u > 0 and d >= 2 and w > 0 for u, d, w in runs))
            self.assertEqual(int(item["analysis"]["counts"]["total_divisions"]), divisions)
            if item["parent_id"] is not None:
                parent = candidates[item["parent_id"]]
                self.assertLess(parent["level"], item["level"])
                self.assertEqual(parent["status"], "rejected")
                self.assertNotEqual(parent["runs"], item["runs"])
            self.assertEqual(item["status"], "rejected")
            self.assertTrue(item["analysis"]["rejection_certificates"])
            self.assertIn("closure_margin_per_step", item)
        self.assertTrue(any(
            reason["filter"] == "run_log_gap_bound"
            for item in candidates.values()
            for reason in item["analysis"]["rejection_certificates"]
        ))

    def test_candidate_passing_the_sieve_gets_an_exact_decision(self):
        # Scaled-down bounds exercise the same fallback with a small word.
        # The small-prime test misses the closure denominator, which is 7.
        with patch("collatz_algebra.sieve.MINIMUM_NONTRIVIAL_PERIOD", 1), patch(
            "collatz_algebra.search._MINIMUM_CYCLE_MEMBER", 4
        ):
            status, report = _evaluate_pattern((Run(1, 3, 1),), prime_limit=5)
        self.assertEqual(status, "rejected")
        self.assertTrue(report["rejected"])
        self.assertEqual(report["exact_verification"]["reason"], "nonintegral_closure")

    def test_reproducible_sampling_in_the_same_seed(self):
        options = dict(cases_per_level=3, depth=2, seed=61, prime_limit=100)
        report = search_cycles(150_000_000_000, **options)
        self.assertEqual(report, search_cycles(150_000_000_000, **options))
        options["seed"] = 62
        self.assertNotEqual(report["candidates"], search_cycles(150_000_000_000, **options)["candidates"])

    def test_search_reports_when_no_candidates_fit_the_ceiling(self):
        report = search_cycles(72_057_431_990)
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["conclusion"], "no_candidates")

    def test_search_samples_at_the_minimum_odd_step_ceiling(self):
        report = search_cycles(72_057_431_991, cases_per_level=1, depth=1)
        candidate, = report["candidates"]
        self.assertEqual(candidate["analysis"]["counts"]["odd_steps"], "72057431991")
        self.assertEqual(candidate["analysis"]["counts"]["unaccelerated_period"], "186265759595")


class SymbolicSearchTests(unittest.TestCase):
    def test_convergents_are_compact_boundary_proposals(self):
        proposals = list(boundary_convergents(1_000_000))
        self.assertTrue(proposals)
        self.assertTrue(all(k <= 1_000_000 for k, _ in proposals))

    def test_two_run_counts_without_expansion(self):
        word = two_run_word(70_000_000_000, 111_000_000_000)
        self.assertEqual(counts(word), (70_000_000_000, 111_000_000_000))

class DefinitiveVerificationTests(unittest.TestCase):
    def test_confirms_the_trivial_cycle_exactly(self):
        report = verify_exact(Step(2))
        self.assertTrue(report["definitive"])
        self.assertTrue(report["is_cycle"])
        self.assertEqual(report["conclusion"], "confirmed_trivial_cycle")
        self.assertEqual(report["starting_integer"], "1")

    def test_rejects_nonintegral_closure_exactly(self):
        report = verify_exact(Step(3))
        self.assertTrue(report["definitive"])
        self.assertFalse(report["is_cycle"])
        self.assertEqual(report["reason"], "nonintegral_closure")

    def test_confirms_a_repeated_cycle_without_expansion(self):
        report = verify_exact(Repeat(Step(2), 1000))
        self.assertTrue(report["is_cycle"])
        self.assertEqual(report["conclusion"], "confirmed_trivial_cycle")

    def test_decides_words_beyond_the_previous_work_limit(self):
        report = verify_exact(Step(1_000_001))
        self.assertTrue(report["definitive"])
        self.assertFalse(report["is_cycle"])
        self.assertEqual(report["reason"], "nonintegral_closure")

    def test_four_run_example_is_rejected_by_exact_closure(self):
        word = Concat(tuple(Step(a) for a in (1, 1, 2, 1, 3, 3)))
        report = verify_exact(word)
        self.assertEqual(report["reason"], "nonintegral_closure")
