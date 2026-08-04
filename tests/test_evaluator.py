import json
import unittest

from bigcollatz.evaluator import collatz_step, evaluate, evaluate_hashset
from bigcollatz.model import EvaluationResult


class EvaluatorTests(unittest.TestCase):
    def test_step_is_exact_for_arbitrary_precision(self):
        huge = 10**2000 + 1
        self.assertEqual(collatz_step(huge), 3 * huge + 1)
        self.assertEqual(collatz_step(huge - 1), (huge - 1) // 2)

    def test_hand_checked_trajectories(self):
        expected = {1: (0, 1), 2: (1, 2), 3: (7, 16), 6: (8, 16), 27: (111, 9232)}
        for start, (steps, maximum) in expected.items():
            with self.subTest(start=start):
                result = evaluate(start)
                self.assertEqual((result.outcome, result.total_steps_executed, result.maximum_integer),
                                 ("reached_one", steps, maximum))

    def test_brent_and_hashset_match_bounded_collatz_domain(self):
        for start in range(1, 5001):
            self.assertEqual(evaluate(start), evaluate_hashset(start))

    def test_injected_tail_and_nontrivial_cycle(self):
        edges = {10: 11, 11: 12, 12: 13, 13: 14, 14: 12}
        transition = edges.__getitem__
        expected = EvaluationResult(10, 5, "repeated_state", 14, 12, 2, 3, "repeated_state")
        self.assertEqual(evaluate(10, transition=transition), expected)
        self.assertEqual(evaluate_hashset(10, transition=transition), expected)

    def test_hash_collision_does_not_create_false_equality(self):
        # CPython deliberately gives -1 and -2 the same hash.
        self.assertEqual(hash(-1), hash(-2))
        edges = {5: -1, -1: -2, -2: -1}
        expected = EvaluationResult(5, 3, "repeated_state", 5, -1, 1, 2, "repeated_state")
        self.assertEqual(evaluate_hashset(5, transition=edges.__getitem__), expected)
        self.assertEqual(evaluate(5, transition=edges.__getitem__), expected)

    def test_known_cycle_is_reached_one_not_repetition(self):
        for start in (1, 2, 4):
            self.assertTrue(evaluate(start).reached_one)

    def test_safety_boundaries_are_censored(self):
        for limit in (0, 1, 6):
            result = evaluate(3, max_steps=limit)
            oracle = evaluate_hashset(3, max_steps=limit)
            self.assertEqual(result, oracle)
            self.assertTrue(result.censored)
            self.assertFalse(result.reached_one)
            self.assertFalse(result.repeated_state_found)
            self.assertEqual(result.total_steps_executed, limit)
        self.assertTrue(evaluate(3, max_steps=7).reached_one)

    def test_invalid_inputs(self):
        for value in (0, -1):
            with self.assertRaises(ValueError):
                evaluate(value)
        with self.assertRaises(ValueError):
            evaluate(3, max_steps=-1)

    def test_large_integer_json_round_trip_and_validation(self):
        original = evaluate(10**600)
        record = original.to_record(wall_time_ns=1)
        transported = json.loads(json.dumps(record))
        self.assertEqual(EvaluationResult.from_record(transported), original)
        transported["start"] = "0" + transported["start"]
        with self.assertRaises(ValueError):
            EvaluationResult.from_record(transported)

    def test_result_invariants_reject_false_classification(self):
        invalid = EvaluationResult(3, 2, "interrupted", 10, stopping_reason="reached_one")
        with self.assertRaises(ValueError):
            invalid.validate()

    def test_deserialization_rejects_inconsistent_records(self):
        record = evaluate(27).to_record()
        mutations = {
            "outcome": "repeated_state",
            "stopping_reason": "error",
            "reached_one": False,
            "repeated_state_found": True,
            "censored": True,
            "decimal_digits": 99,
            "maximum_bit_length": 1,
            "schema_version": 2,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                malformed = dict(record)
                malformed[field] = value
                with self.assertRaises(ValueError):
                    EvaluationResult.from_record(malformed)

    def test_deserialization_rejects_malformed_types_and_decimals(self):
        record = evaluate(3).to_record()
        mutations = {
            "start": "03", "maximum_integer": "+16", "total_steps_executed": "7",
            "decimal_digits": True, "maximum_bit_length": 5.0, "reached_one": 1,
            "schema_version": True,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                malformed = dict(record)
                malformed[field] = value
                with self.assertRaises(ValueError):
                    EvaluationResult.from_record(malformed)

    def test_cycle_record_validation(self):
        result = EvaluationResult(10, 5, "repeated_state", 14, 12, 2, 3, "repeated_state")
        record = result.to_record()
        self.assertEqual(EvaluationResult.from_record(record), result)
        for field, value in (("cycle_entry_step", -1), ("cycle_period", 0),
                             ("repeated_state", "012")):
            malformed = dict(record)
            malformed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                EvaluationResult.from_record(malformed)


class MandatoryCycleDetectionTests(unittest.TestCase):
    def test_starting_integer_is_registered_at_step_zero(self):
        result = evaluate(7, transition=lambda _: 7)
        self.assertEqual(result.outcome, "repeated_state")
        self.assertEqual(result.first_seen_step, 0)
        self.assertEqual(result.repeated_at_step, 1)
        self.assertEqual(result.cycle_length, 1)

    def test_repetition_checked_after_every_generated_step_and_stops_first(self):
        calls = []
        edges = {8: 9, 9: 10, 10: 9}
        def transition(n):
            calls.append(n)
            return edges[n]
        result = evaluate(8, transition=transition)
        self.assertEqual(calls, [8, 9, 10])
        self.assertEqual(result.repeated_integer, "9")
        self.assertEqual((result.first_seen_step, result.repeated_at_step, result.cycle_length), (1, 3, 2))

    def test_reached_one_has_no_cycle_metadata(self):
        result = evaluate(2)
        self.assertEqual(result.outcome, "reached_one")
        self.assertIsNone(result.repeated_integer)
        self.assertIsNone(result.first_seen_step)
        self.assertIsNone(result.repeated_at_step)
        self.assertIsNone(result.cycle_length)

if __name__ == "__main__":
    unittest.main()

class MetricEvaluatorAgreementTests(unittest.TestCase):
    def assert_agrees(self, start, **kwargs):
        plain = evaluate(start, **kwargs)
        met = __import__('bigcollatz.evaluator', fromlist=['evaluate_with_metrics']).evaluate_with_metrics(start, **kwargs).result
        self.assertEqual(plain, met)
    def test_reached_one_agrees(self): self.assert_agrees(27)
    def test_starting_one_agrees(self): self.assert_agrees(1)
    def test_interrupted_agrees(self): self.assert_agrees(27, max_steps=0)
    def test_controlled_repeat_agrees(self):
        trans={5:7,7:9,9:7}.__getitem__
        self.assert_agrees(5, transition=trans)
