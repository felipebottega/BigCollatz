import unittest
import json
import tempfile
from pathlib import Path

from bigcollatz.generator import (
    balanced_allocation, baseline_candidates, load_global_top_10, load_lineage_weights,
    parity_prefix_candidate_records, parity_prefix_candidates, validate_parity_prefix,
    S2_STRATEGY, weighted_allocation, weighted_parity_prefix_candidate_records,
)


class GeneratorTests(unittest.TestCase):
    def test_deterministic_distinct_and_exactly_1000_digits(self):
        first = list(baseline_candidates(10_000, "fixture"))
        self.assertEqual(len(first), len(set(first)))
        self.assertTrue(all(len(str(value)) == 1000 for value in first))
        self.assertTrue(all(right - left != 1 for left, right in zip(first, first[1:])))

    def test_deterministic_for_same_seed(self):
        self.assertEqual(list(baseline_candidates(100, "fixture")),
                         list(baseline_candidates(100, "fixture")))

    def test_seed_selects_stream(self):
        self.assertNotEqual(list(baseline_candidates(3, "a")),
                            list(baseline_candidates(3, "b")))

    def test_invalid_count(self):
        for count in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                list(baseline_candidates(count))  # type: ignore[arg-type]


class ParityPrefixGeneratorTests(unittest.TestCase):
    parents = [27, 97, 871]

    def test_properties_and_parity_prefix(self):
        records = list(parity_prefix_candidate_records(31, self.parents, "fixture", 256))
        candidates = [candidate for candidate, _ in records]
        self.assertEqual(len(candidates), len(set(candidates)))
        self.assertTrue(all(len(str(candidate)) == 1000 for candidate in candidates))
        self.assertTrue(all(candidate not in self.parents for candidate in candidates))
        self.assertTrue(all(right - left != 1 for left, right in zip(candidates, candidates[1:])))
        self.assertTrue(all(validate_parity_prefix(candidate, parent, 256)
                            for candidate, parent in records))

    def test_deterministic_and_seeded(self):
        first = list(parity_prefix_candidates(20, self.parents, "same"))
        self.assertEqual(first, list(parity_prefix_candidates(20, self.parents, "same")))
        self.assertNotEqual(first, list(parity_prefix_candidates(20, self.parents, "different")))

    def test_balanced_parent_allocation(self):
        records = list(parity_prefix_candidate_records(11, self.parents, "fixture"))
        counts = [sum(parent == expected for _, parent in records) for expected in self.parents]
        self.assertEqual(counts, balanced_allocation(11, self.parents))
        self.assertLessEqual(max(counts) - min(counts), 1)

    def test_parent_is_excluded_even_when_it_is_1000_digits(self):
        parent = next(parity_prefix_candidates(1, [27], "parent-source"))
        self.assertNotIn(parent, list(parity_prefix_candidates(50, [parent], "fixture")))

    def test_missing_or_empty_parent_file_has_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "global_top_10.json"
            with self.assertRaisesRegex(ValueError, "missing"):
                load_global_top_10(path)
            path.write_text(json.dumps([]))
            with self.assertRaisesRegex(ValueError, "empty"):
                load_global_top_10(path)

    def test_parent_file_validation_errors_are_clear(self):
        valid = "1" + "0" * 999
        cases = [
            ("", "empty"),
            ("not json", "malformed JSON"),
            (json.dumps([{"wrong_field": valid}]), "invalid parent"),
            (json.dumps([{"starting_integer": "1" + "0" * 998}]), "1000-digit"),
            (json.dumps([{"starting_integer": "0" + "1" * 999}]), "canonical"),
            (json.dumps([{"starting_integer": valid}, {"starting_integer": valid}]),
             "duplicate parent"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "global_top_10.json"
            for contents, message in cases:
                with self.subTest(message=message):
                    path.write_text(contents)
                    with self.assertRaisesRegex(ValueError, message):
                        load_global_top_10(path)

    def test_nonempty_parent_list_need_not_have_ten_entries(self):
        parent = "9" * 1000
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "global_top_10.json"
            path.write_text(json.dumps([{"starting_integer": parent}]))
            self.assertEqual(load_global_top_10(path), [int(parent)])

class WeightedLineageGeneratorTests(unittest.TestCase):
    def test_e002_style_weights_allocate_10000_exactly(self):
        self.assertEqual(weighted_allocation(10_000, [3, 3, 2, 1, 1]),
                         [3000, 3000, 2000, 1000, 1000])

    def test_e003_style_weights_allocate_10000_exactly(self):
        self.assertEqual(weighted_allocation(10_000, [4, 4, 1, 1]),
                         [4000, 4000, 1000, 1000])

    def test_weighted_allocation_sums_exactly_and_remainders_are_deterministic(self):
        for count in range(25):
            self.assertEqual(sum(weighted_allocation(count, [1, 1, 1])), count)
        self.assertEqual(weighted_allocation(5, [1, 1, 1]), [2, 2, 1])
        self.assertEqual(weighted_allocation(5, [2, 2, 2]), [2, 2, 1])

    def test_load_lineage_weights_uses_only_productive_lineages_in_source_order(self):
        parent_a = "1" + "0" * 999
        parent_b = "2" + "0" * 999
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "top_10.json"
            path.write_text(json.dumps([
                {"parent_starting_integer": parent_b, "prefix_length": 256},
                {"parent_starting_integer": parent_a, "prefix_length": 256},
                {"parent_starting_integer": parent_b, "prefix_length": 256},
            ]))
            self.assertEqual(load_lineage_weights(path), [(int(parent_b), 2), (int(parent_a), 1)])

    def test_s3_lineage_weights_are_derived_and_validated(self):
        parents = ["1" + "0" * 999, "2" + "0" * 999, "3" + "0" * 999, "4" + "0" * 999]
        records = []
        for parent, copies in zip(parents, [1, 4, 1, 4]):
            records.extend({
                "parent_starting_integer": parent,
                "prefix_length": 256,
                "strategy": S2_STRATEGY,
                "experiment_id": "e003-s2-weighted-lineages-256",
                "outcome": "reached_one",
            } for _ in range(copies))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "top_10.json"
            path.write_text(json.dumps(records))
            weights = load_lineage_weights(
                path, expected_strategy=S2_STRATEGY,
                expected_experiment_id="e003-s2-weighted-lineages-256",
                completed_outcomes=frozenset(("reached_one", "repeated_state")),
            )
            self.assertEqual(weights, [(int(parents[1]), 4), (int(parents[3]), 4),
                                       (int(parents[0]), 1), (int(parents[2]), 1)])
            self.assertEqual(weighted_allocation(10_000, [weight for _, weight in weights]),
                             [4000, 4000, 1000, 1000])

    def test_weighted_candidates_properties_parity_and_determinism(self):
        parents = [(10**999 + 12345, 2), (2 * 10**999 + 54321, 1)]
        first = list(weighted_parity_prefix_candidate_records(12, parents, "fixture", 256))
        second = list(weighted_parity_prefix_candidate_records(12, parents, "fixture", 256))
        self.assertEqual(first, second)
        self.assertNotEqual(first, list(weighted_parity_prefix_candidate_records(12, parents, "other", 256)))
        candidates = [candidate for candidate, _ in first]
        self.assertEqual(len(candidates), len(set(candidates)))
        self.assertTrue(all(len(str(candidate)) == 1000 for candidate in candidates))
        self.assertTrue(all(candidate not in {parent for parent, _ in parents} for candidate in candidates))
        self.assertTrue(all(right - left != 1 for left, right in zip(candidates, candidates[1:])))
        self.assertTrue(all(validate_parity_prefix(candidate, parent, 256) for candidate, parent in first))

    def test_invalid_lineage_source_files_have_clear_errors(self):
        valid_parent = "9" * 1000
        cases = [
            (None, "missing"),
            ("", "empty"),
            ("not json", "malformed JSON"),
            (json.dumps([]), "empty"),
            (json.dumps([{}]), "missing lineage fields"),
            (json.dumps([{"parent_starting_integer": "1" + "0" * 998, "prefix_length": 256}]), "1000-digit"),
            (json.dumps([{"parent_starting_integer": "0" + "1" * 999, "prefix_length": 256}]), "canonical"),
            (json.dumps([{"parent_starting_integer": valid_parent, "prefix_length": 255}]), "does not match requested"),
            (json.dumps({"parent_starting_integer": valid_parent, "prefix_length": 256}), "empty"),
            (json.dumps([
                {"parent_starting_integer": valid_parent, "prefix_length": 256},
                {"parent_starting_integer": valid_parent, "prefix_length": 255},
            ]), "inconsistent prefix lengths"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "top_10.json"
            for contents, message in cases:
                with self.subTest(message=message):
                    if contents is None:
                        if path.exists():
                            path.unlink()
                    else:
                        path.write_text(contents)
                    with self.assertRaisesRegex(ValueError, message):
                        load_lineage_weights(path)

    def test_s3_foreign_and_incomplete_source_records_are_rejected(self):
        valid_parent = "9" * 1000
        base = {
            "parent_starting_integer": valid_parent,
            "prefix_length": 256,
            "strategy": S2_STRATEGY,
            "experiment_id": "e003-s2-weighted-lineages-256",
            "outcome": "reached_one",
        }
        cases = [
            ({**base, "strategy": "S1-parity-prefix-top10"}, "foreign strategy"),
            ({**base, "experiment_id": "other"}, "foreign experiment"),
            ({**base, "outcome": "interrupted"}, "incomplete or invalid outcome"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "top_10.json"
            for record, message in cases:
                with self.subTest(message=message):
                    path.write_text(json.dumps([record]))
                    with self.assertRaisesRegex(ValueError, message):
                        load_lineage_weights(
                            path, expected_strategy=S2_STRATEGY,
                            expected_experiment_id="e003-s2-weighted-lineages-256",
                            completed_outcomes=frozenset(("reached_one", "repeated_state")),
                        )


    def test_mixed_prefix_records_are_distinct_1000_digit_and_validate(self):
        from bigcollatz.generator import mixed_prefix_candidate_records, validate_parity_prefix
        parents = [10**999 + 12345, 2 * 10**999 + 67890]
        records = list(mixed_prefix_candidate_records(12, parents, "fixture", (8, 12)))
        self.assertEqual(len(records), 12)
        starts = [candidate for candidate, _, _ in records]
        self.assertEqual(len(set(starts)), 12)
        self.assertTrue(all(len(str(candidate)) == 1000 for candidate in starts))
        self.assertEqual(sorted({prefix for _, _, prefix in records}), [8, 12])
        for candidate, parent, prefix in records:
            self.assertIn(parent, parents)
            self.assertTrue(validate_parity_prefix(candidate, parent, prefix))


class NewResearchStrategyGeneratorTests(unittest.TestCase):
    def test_productivity_weighted_cells_are_distinct_and_validate(self):
        from bigcollatz.generator import productivity_weighted_cell_records
        parents = [10**999 + 12345, 2 * 10**999 + 67890, 3 * 10**999 + 13579]
        records = list(productivity_weighted_cell_records(30, parents, "fixture", (8, 12)))
        candidates = [candidate for candidate, _, _ in records]
        self.assertEqual(len(candidates), len(set(candidates)))
        self.assertTrue(all(len(str(candidate)) == 1000 for candidate in candidates))
        counts = {parent: 0 for parent in parents}
        for candidate, parent, prefix in records:
            counts[parent] += 1
            self.assertTrue(validate_parity_prefix(candidate, parent, prefix))
        self.assertGreater(counts[parents[0]], counts[parents[-1]])

    def test_suffix_perturbation_preserves_decimal_prefix(self):
        from bigcollatz.generator import suffix_perturbation_candidate_records
        parent = int("8" * 1000)
        records = list(suffix_perturbation_candidate_records(25, parent, "fixture", suffix_digits=40))
        candidates = [candidate for candidate, source in records]
        self.assertEqual(len(candidates), len(set(candidates)))
        self.assertTrue(all(source == parent for _, source in records))
        self.assertTrue(all(len(str(candidate)) == 1000 for candidate in candidates))
        self.assertTrue(all(str(candidate)[:960] == str(parent)[:960] for candidate in candidates))
        self.assertNotIn(parent, candidates)


if __name__ == "__main__":
    unittest.main()
