import unittest

from bigcollatz.generator import baseline_candidates


class GeneratorTests(unittest.TestCase):
    def test_deterministic_distinct_and_exactly_1000_digits(self):
        first = list(baseline_candidates(100, "fixture"))
        self.assertEqual(first, list(baseline_candidates(100, "fixture")))
        self.assertEqual(len(first), len(set(first)))
        self.assertTrue(all(len(str(value)) == 1000 for value in first))

    def test_seed_selects_stream(self):
        self.assertNotEqual(list(baseline_candidates(3, "a")),
                            list(baseline_candidates(3, "b")))

    def test_invalid_count(self):
        for count in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                list(baseline_candidates(count))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
