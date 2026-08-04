import unittest

from bigcollatz.generator import baseline_candidates


class GeneratorTests(unittest.TestCase):
    def test_ten_thousand_1000_digit_candidates_are_distinct_and_not_consecutive(self):
        candidates = list(baseline_candidates(10_000, 1000, "large-fixture"))
        self.assertEqual(len(candidates), len(set(candidates)))
        self.assertTrue(all(len(str(value)) == 1000 for value in candidates))
        self.assertTrue(all(abs(left - right) != 1
                            for left, right in zip(candidates, candidates[1:])))

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

    def test_digit_strata_use_domain_separated_streams(self):
        # The first 500 digits are not a shared prefix of another stratum's hash stream.
        a = list(baseline_candidates(3, 500, "same-seed"))
        b = list(baseline_candidates(3, 501, "same-seed"))
        self.assertNotEqual([str(value)[:100] for value in a],
                            [str(value)[:100] for value in b])

    def test_rejection_sampling_is_deterministic(self):
        expected = list(baseline_candidates(5, 500, "rejection-fixture"))
        self.assertEqual(expected, list(baseline_candidates(5, 500, "rejection-fixture")))

    def test_different_seeds_produce_different_candidates(self):
        self.assertNotEqual(list(baseline_candidates(20, 1000, "seed-a")),
                            list(baseline_candidates(20, 1000, "seed-b")))


if __name__ == "__main__":
    unittest.main()
