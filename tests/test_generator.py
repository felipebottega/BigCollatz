import unittest

from bigcollatz.generator import baseline_candidates


class GeneratorTests(unittest.TestCase):
    def test_deterministic_unique_and_in_range(self):
        first = list(baseline_candidates(20, 500, "fixture"))
        self.assertEqual(first, list(baseline_candidates(20, 500, "fixture")))
        self.assertEqual(len(first), len(set(first)))
        self.assertTrue(all(len(str(value)) == 500 for value in first))

    def test_all_supported_boundaries(self):
        self.assertEqual(len(str(next(baseline_candidates(1, 500)))), 500)
        self.assertEqual(len(str(next(baseline_candidates(1, 1000)))), 1000)
        for digits in (499, 1001):
            with self.assertRaises(ValueError):
                list(baseline_candidates(1, digits))


if __name__ == "__main__":
    unittest.main()
