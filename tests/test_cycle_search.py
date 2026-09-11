import json
import tempfile
import unittest
from pathlib import Path

from bigcollatz.cycle_equation import (
    compose_cycle_equation,
    is_primitive,
    least_rotation,
    passes_modular_filters,
    solve_cycle_equation,
)
from bigcollatz.cycle_search import (
    CycleSearchConfig,
    compositions,
    minimum_total_divisions,
    primitive_necklaces,
    run_cycle_search,
    search_cycles,
)
from bigcollatz.odd_map import odd_step, trailing_zero_count, verify_odd_cycle
from bigcollatz.integers import decimal_string


class OddMapTests(unittest.TestCase):
    def test_accelerated_steps_and_arbitrary_precision(self):
        self.assertEqual(odd_step(1), (1, 2))
        self.assertEqual(odd_step(3), (5, 1))
        value = (1 << 10_000) - 1
        following, exponent = odd_step(value)
        self.assertEqual(following, (3 * value + 1) >> exponent)
        self.assertEqual((3 * value + 1) % (1 << exponent), 0)

    def test_validation(self):
        for value in (0, -2):
            with self.assertRaises(ValueError):
                trailing_zero_count(value)
        for value in (0, 2, -1):
            with self.assertRaises(ValueError):
                odd_step(value)
        self.assertEqual(verify_odd_cycle(1, (2,)).members, (1,))
        with self.assertRaises(ValueError):
            verify_odd_cycle(3, (1,))

    def test_decimal_format_has_no_runtime_digit_limit(self):
        value = 10**5000 + 123
        rendered = decimal_string(value)
        self.assertEqual(len(rendered), 5001)
        self.assertTrue(rendered.endswith("123"))


class EquationTests(unittest.TestCase):
    def test_trivial_cycle_equations_and_nonintegral_vector(self):
        equation = compose_cycle_equation((2,))
        self.assertEqual((equation.numerator, equation.denominator), (1, 1))
        self.assertEqual(solve_cycle_equation((2,)).members, (1,))
        self.assertIsNone(solve_cycle_equation((2, 2)))
        self.assertIsNone(solve_cycle_equation((1, 3)))
        with self.assertRaises(ValueError):
            compose_cycle_equation((1,))

    def test_rotation_and_primitive_words(self):
        self.assertEqual(least_rotation((3, 1, 2)), (1, 2, 3))
        self.assertTrue(is_primitive((1, 2, 1, 3)))
        self.assertFalse(is_primitive((1, 2, 1, 2)))

    def test_modular_filter_is_necessary_not_probabilistic(self):
        self.assertTrue(passes_modular_filters((2,)))
        self.assertFalse(passes_modular_filters((1, 3)))
        for vector in compositions(12, 4):
            if solve_cycle_equation(vector) is not None:
                self.assertTrue(passes_modular_filters(vector))


class SearchTests(unittest.TestCase):
    def test_compositions_and_positivity_boundary(self):
        self.assertEqual(
            list(compositions(5, 3)),
            [(1, 1, 3), (1, 2, 2), (1, 3, 1), (2, 1, 2), (2, 2, 1), (3, 1, 1)],
        )
        self.assertEqual(minimum_total_divisions(1), 2)
        self.assertEqual(minimum_total_divisions(2), 4)

    def test_necklace_generator_matches_exhaustive_canonical_oracle(self):
        for length in range(1, 7):
            for total in range(length, length + 8):
                expected = {
                    vector
                    for vector in compositions(total, length)
                    if vector == least_rotation(vector) and is_primitive(vector)
                }
                generated = list(primitive_necklaces(total, length))
                self.assertEqual(set(generated), expected)
                self.assertEqual(len(generated), len(set(generated)))

    def test_search_finds_or_excludes_trivial_cycle(self):
        included = search_cycles(
            CycleSearchConfig(
                max_odd_period=3, max_total_divisions=6, include_trivial=True
            )
        )
        self.assertEqual(len(included["discoveries"]), 1)
        self.assertEqual(included["discoveries"][0]["odd_members"], ["1"])
        self.assertGreater(
            included["stats"]["ordered_compositions_in_region"],
            included["stats"]["canonical_vectors_generated"],
        )
        excluded = search_cycles(
            CycleSearchConfig(max_odd_period=3, max_total_divisions=6)
        )
        self.assertEqual(excluded["discoveries"], [])

    def test_shards_partition_work_and_checkpoint_is_resumable(self):
        common = dict(max_odd_period=4, max_total_divisions=8, include_trivial=True)
        whole = search_cycles(CycleSearchConfig(**common))
        shards = [
            search_cycles(CycleSearchConfig(**common, shard_index=i, shard_count=2))
            for i in range(2)
        ]
        self.assertEqual(
            sum(part["stats"]["shard_vectors"] for part in shards),
            whole["stats"]["shard_vectors"],
        )
        self.assertEqual(
            sum((part["discoveries"] for part in shards), []), whole["discoveries"]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_cycle_search(root, "small", CycleSearchConfig(**common))
            resumed = run_cycle_search(root, "small", CycleSearchConfig(**common))
            self.assertEqual(resumed["discoveries"], result["discoveries"])
            checkpoint = json.loads(
                (root / "results/small/checkpoint.json").read_text()
            )
            self.assertTrue(checkpoint["completed"])
            self.assertTrue((root / "results/small/summary.json").exists())

    def test_invalid_configuration_and_checkpoint_mismatch(self):
        with self.assertRaises(ValueError):
            search_cycles(CycleSearchConfig(shard_count=0))
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            search_cycles(
                CycleSearchConfig(max_total_divisions=3), checkpoint_path=checkpoint
            )
            with self.assertRaises(ValueError):
                search_cycles(
                    CycleSearchConfig(max_total_divisions=4), checkpoint_path=checkpoint
                )


if __name__ == "__main__":
    unittest.main()
