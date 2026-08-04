import unittest
import json
import tempfile
from pathlib import Path

from bigcollatz.generator import (
    balanced_allocation, baseline_candidates, load_global_top_10,
    parity_prefix_candidate_records, parity_prefix_candidates,
    validate_parity_prefix,
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


if __name__ == "__main__":
    unittest.main()
