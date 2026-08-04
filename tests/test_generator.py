import unittest
import json
import tempfile
from pathlib import Path

from bigcollatz.generator import baseline_candidates, load_global_top_10


class GeneratorTests(unittest.TestCase):
    def test_global_parents_must_have_exactly_1000_digits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "global_top_10.json"
            path.write_text(json.dumps([{"starting_integer": "9" * 999}]))
            with self.assertRaisesRegex(ValueError, "exactly 1000 decimal digits"):
                load_global_top_10(path)

            parent = "1" + "0" * 999
            path.write_text(json.dumps([{"starting_integer": parent}]))
            self.assertEqual(load_global_top_10(path), [int(parent)])

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


if __name__ == "__main__":
    unittest.main()
