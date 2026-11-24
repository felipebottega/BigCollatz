import json
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from random import Random
from unittest.mock import patch

from collatz_algebra.bounds import _farey_neighbors, count_window, run_gap_bound
from collatz_algebra.cli import main
from collatz_algebra.definitive import verify_exact
from collatz_algebra.exact_affine import evaluate_exact_affine
from collatz_algebra.grammar import Concat, Repeat, Step, counts, parse_word
from collatz_algebra.modular import evaluate_mod
from collatz_algebra.sieve import analyze, targeted_moduli
from collatz_algebra.search import (
    AnchoredPattern, Run, _evaluate_pattern, _independent_pattern, _vary_pattern, _word,
    boundary_convergents, search_cycles, two_run_word,
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
                "--search-cycles", "5000000000000000000", "--cases-per-level", "6",
                "--depth", "3", "--seed", "0", "--prime-limit", "5", "--output", str(output),
            ]), 0)
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["schema"], "collatz-monte-carlo-search-v5")
        self.assertEqual([level["evaluated"] for level in report["levels"]], [6, 6, 6])
        self.assertEqual(sum(report["totals"].values()), 18)
        self.assertEqual(report["conclusion"], "all_candidates_rejected")
        candidates = {item["id"]: item for item in report["candidates"]}
        self.assertGreater(len(report["levels"][0]["families"]), 1)
        self.assertTrue(any(item["anchor"] is not None for item in candidates.values()))
        self.assertTrue(any(item["anchor"] is None for item in candidates.values()))
        self.assertTrue(any(item["parent_id"] is not None for item in candidates.values()))
        self.assertTrue(any(item["level"] == 3 and item["parent_id"] is None
                            for item in candidates.values()))
        for item in candidates.values():
            def decode(entries):
                return [
                    Run(int(u), d, int(w), tuple((a, int(n)) for a, n in tail[0]) if tail else ())
                    for u, d, w, *tail in entries
                ]

            runs = decode(item["runs"])
            odd_steps, divisions = counts(_word(tuple(runs)))
            run_count = len(runs)
            for group in item["packed_runs"]:
                copies = int(group["copies"])
                motif = decode(group["runs"])
                k, S = counts(_word(tuple(motif)))
                odd_steps += copies * k
                divisions += copies * S
                run_count += copies * len(motif)
            self.assertEqual(item["family"]["uphill_runs"], run_count)
            self.assertLessEqual(odd_steps, 5_000_000_000_000_000_000)
            self.assertGreaterEqual(odd_steps + divisions, 186_265_759_595)
            self.assertEqual(int(item["analysis"]["counts"]["total_divisions"]), divisions)
            anchor = item["anchor"]
            if anchor is not None:
                valley = int(anchor["odd_member"])
                prefix = runs[:anchor["prefix_runs"]]
                term = valley
                self.assertGreaterEqual(counts(_word(tuple(prefix)))[0], 12)
                for run in prefix:
                    for exponent, length in ((1, run.uphill), *run.descent):
                        for _ in range(length):
                            value = 3 * term + 1
                            term, remainder = divmod(value, 1 << exponent)
                            self.assertEqual(remainder, 0)
                            self.assertEqual(term % 2, 1)
                            self.assertGreaterEqual(term, 2**71)
                incoming_divisions, incoming_length = runs[-1].descent[-1]
                predecessor = valley
                for _ in range(incoming_length):
                    predecessor, remainder = divmod((predecessor << incoming_divisions) - 1, 3)
                    self.assertEqual(remainder, 0)
                    self.assertEqual(predecessor % 2, 1)
            if item["parent_id"] is not None:
                parent = candidates[item["parent_id"]]
                self.assertLess(parent["level"], item["level"])
                self.assertEqual(parent["status"], "rejected")
                self.assertNotEqual(
                    (parent["runs"], parent["packed_runs"]), (item["runs"], item["packed_runs"])
                )
                self.assertEqual(parent["anchor"], item["anchor"])
                if anchor is not None:
                    self.assertEqual(parent["runs"][:anchor["prefix_runs"]], item["runs"][:anchor["prefix_runs"]])
                    self.assertEqual(parent["runs"][-1], item["runs"][-1])
            self.assertEqual(item["status"], "rejected")
            self.assertTrue(item["analysis"]["rejection_certificates"])
            self.assertIn("closure_margin_per_step", item)
        self.assertTrue(any(
            reason["filter"] in ("valley_congruence_gap_bound", "packed_runs_gap_bound")
            for item in candidates.values()
            for reason in item["analysis"]["rejection_certificates"]
        ))

    def test_candidate_passing_the_sieve_gets_an_exact_decision(self):
        # Scaled-down bounds exercise the same fallback with a small word.
        # The small-prime test misses the closure denominator, which is 7.
        with patch("collatz_algebra.sieve.MINIMUM_NONTRIVIAL_PERIOD", 1), patch(
            "collatz_algebra.search._MINIMUM_CYCLE_MEMBER", 4
        ), patch("collatz_algebra.search.run_gap_bound", return_value=Fraction(1)), patch(
            "collatz_algebra.search._valley_gap_bound", return_value=Fraction(1)
        ):
            status, report = _evaluate_pattern((Run(1, 3, 1),), prime_limit=5)
        self.assertEqual(status, "rejected")
        self.assertTrue(report["rejected"])
        self.assertEqual(report["exact_verification"]["reason"], "nonintegral_closure")

    def test_reproducible_sampling_in_the_same_seed(self):
        options = dict(cases_per_level=3, depth=2, seed=61, prime_limit=100)
        report = search_cycles(5_000_000_000_000_000_000, **options)
        self.assertEqual(report, search_cycles(5_000_000_000_000_000_000, **options))
        options["seed"] = 62
        self.assertNotEqual(report["candidates"], search_cycles(5_000_000_000_000_000_000, **options)["candidates"])

    def test_search_reports_when_no_candidates_fit_the_ceiling(self):
        report = search_cycles(72_057_431_990)
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["conclusion"], "no_candidates")

    def test_samples_billions_of_runs_at_the_200_billion_step_ceiling(self):
        report = search_cycles(200_000_000_000, cases_per_level=8, depth=2, seed=200)
        self.assertEqual(report["conclusion"], "all_candidates_rejected")
        self.assertEqual(len(report["candidates"]), 16)
        proof = report["preflight"]
        self.assertEqual(proof["necessary_uphill_runs"], "3543773083")
        self.assertEqual(proof["max_uphill_runs"], 100_000_000_000)
        for item in report["candidates"]:
            self.assertGreaterEqual(item["family"]["uphill_runs"], 3_543_773_083)
            self.assertLessEqual(int(item["analysis"]["counts"]["odd_steps"]), 200_000_000_000)
            self.assertTrue(item["packed_runs"])
            self.assertTrue(item["analysis"]["rejection_certificates"])

    def test_independent_sampling_can_materialize_more_than_256_runs(self):
        pattern = _independent_pattern(Random(3), 700, 1109, 300)
        self.assertEqual(len(pattern.runs), 300)
        self.assertFalse(pattern.packed)
        self.assertIsNone(pattern.valley)
        self.assertEqual(counts(_word(pattern.runs)), (700, 1109))

    def test_independent_sampling_varies_divisions_within_a_downhill_run(self):
        pattern = _independent_pattern(Random(8), 70, 350, 3)
        self.assertEqual(counts(_word(pattern.runs)), (70, 350))
        self.assertTrue(any(run.following for run in pattern.runs))
        self.assertGreater(max(d for run in pattern.runs for d, _ in run.descent), 8)
        self.assertEqual(pattern.prefix_runs, 0)

    def test_resize_preserves_positive_runs_when_new_totals_do_not_fit(self):
        rng = Random(92003)
        runs = (Run(2, 2, 1), Run(15, 2, 3), Run(5, 4, 2), Run(100, 2, 3))
        parent = AnchoredPattern(runs, 1, 11)

        class SmallerWindow:
            def sample(self, rng):
                return 10, 16

        with patch("collatz_algebra.search.lower_log_gap", return_value=Fraction(0)):
            for _ in range(32):
                child = _vary_pattern(rng, parent, SmallerWindow())
                self.assertTrue(all(run.uphill > 0 and run.downhill > 0 for run in child.runs))
                self.assertEqual(child.runs[0], runs[0])
                self.assertEqual(child.runs[-1], runs[-1])

    def test_count_window_brackets_and_samples_constrained_pairs(self):
        ceiling = 5 * 10**18
        window = count_window(ceiling, 256)
        self.assertFalse(window.excluded)
        self.assertGreater(window.lower.denominator + window.upper.denominator, ceiling)
        self.assertEqual(
            window.upper.numerator * window.lower.denominator
            - window.lower.numerator * window.upper.denominator, 1,
        )
        rng = Random(4)
        for _ in range(10):
            k, divisions = window.sample(rng)
            self.assertLessEqual(k, ceiling)
            self.assertGreaterEqual(k, 72_057_431_991)
            self.assertGreaterEqual(Fraction(divisions, k), window.upper)
            self.assertLess(window.upper_positive_gap, run_gap_bound(256))

    def test_farey_neighbors_match_small_exhaustive_search(self):
        value = Fraction(163, 103)
        for ceiling in (1, 2, 10, 40):
            fractions = {
                Fraction((value.numerator * k) // value.denominator + offset, k)
                for k in range(1, ceiling + 1) for offset in (0, 1)
            }
            self.assertEqual(_farey_neighbors(value, ceiling), (
                max(f for f in fractions if f < value),
                min(f for f in fractions if f > value),
            ))


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

    def test_verifies_giant_whole_word_repetitions_by_their_fixed_point(self):
        copies = 200_000_000_000
        positive = verify_exact(Repeat(Step(2), copies))
        self.assertTrue(positive["is_cycle"])
        self.assertEqual(positive["counts"]["odd_steps"], str(copies))
        rejected = verify_exact(Repeat(Concat((Step(1), Step(3))), copies))
        self.assertFalse(rejected["is_cycle"])
        self.assertEqual(rejected["reason"], "nonintegral_closure")
        self.assertEqual(rejected["counts"]["odd_steps"], str(2 * copies))

    def test_balanced_exact_coefficients_match_left_to_right_composition(self):
        from collatz_algebra.modular import evaluate_affine

        word = Concat(tuple(
            Repeat(Concat((Step(2), Step(d), Step(1))), d + 1) for d in range(1, 17)
        ))
        expected = evaluate_affine(word)
        exact = evaluate_exact_affine(word)
        self.assertEqual(exact.multiplier, expected.multiplier)
        self.assertEqual(exact.additive, expected.additive)
        self.assertEqual(1 << exact.divisions, expected.denominator)

    def test_decides_words_beyond_the_previous_work_limit(self):
        report = verify_exact(Step(1_000_001))
        self.assertTrue(report["definitive"])
        self.assertFalse(report["is_cycle"])
        self.assertEqual(report["reason"], "nonintegral_closure")

    def test_four_run_example_is_rejected_by_exact_closure(self):
        word = Concat(tuple(Step(a) for a in (1, 1, 2, 1, 3, 3)))
        report = verify_exact(word)
        self.assertEqual(report["reason"], "nonintegral_closure")
