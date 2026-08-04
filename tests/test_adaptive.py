import ast
import json
import tempfile
import unittest
from pathlib import Path

from bigcollatz.adaptive import AdaptiveCell, create_nontrivial_cycle_discovery, run_adaptive_pilot, validate_cell_record
from bigcollatz.evaluator import EvaluationWithMetrics, RecurrenceMetrics, evaluate, evaluate_with_metrics
from bigcollatz.generator import CandidateRecord, S1_STRATEGY, S5_STRATEGY
from bigcollatz.model import EvaluationResult


class AdaptiveTests(unittest.TestCase):
    def test_metric_enabled_and_normal_evaluation_agree(self):
        for n in (1, 2, 3, 7, 27):
            normal = evaluate(n)
            metric = evaluate_with_metrics(n).result
            self.assertEqual(normal.outcome, metric.outcome)
            self.assertEqual(normal.total_steps_executed, metric.total_steps_executed)
            self.assertEqual(normal.maximum_integer, metric.maximum_integer)
            self.assertEqual(normal.repeated_integer, metric.repeated_integer)
            self.assertEqual(normal.first_seen_step, metric.first_seen_step)
            self.assertEqual(normal.repeated_at_step, metric.repeated_at_step)
            self.assertEqual(normal.cycle_length, metric.cycle_length)

    def test_exact_repeat_detection_active_with_injected_transition(self):
        result = evaluate(5, transition=lambda n: 5 if n == 16 else 3 * n + 1 if n % 2 else n // 2)
        self.assertEqual(result.outcome, "repeated_state")
        self.assertEqual(result.repeated_integer, "5")
        self.assertEqual(result.first_seen_step, 0)
        self.assertEqual(result.cycle_length, result.repeated_at_step)

    def test_adaptive_module_has_no_collatz_loop_or_transition_definition(self):
        tree = ast.parse(Path("bigcollatz/adaptive.py").read_text())
        functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        self.assertNotIn("evaluate", functions)
        self.assertNotIn("collatz_step", functions)
        source = Path("bigcollatz/adaptive.py").read_text()
        self.assertNotIn("3 * state + 1", source)
        self.assertNotIn("3 * n + 1", source)

    def test_strategy_bound_validation_rejects_cross_family_mismatch(self):
        cell = AdaptiveCell("c", "decimal_suffix", 12345, 1, 1, {"suffix_digits": 1}, "decimal_suffix")
        bad = CandidateRecord(10**999, S1_STRATEGY, "parity_prefix", parent=12345, prefix_length=1)
        with self.assertRaises(ValueError):
            validate_cell_record(cell, bad)

    def test_repeated_state_persists_complete_adaptive_cycle_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cell = AdaptiveCell("fake-cell", "parity_prefix", 10**999, 1, 1, {"prefix_length": 1}, "parity_prefix")

            def fake_records(_cell, _seed):
                yield CandidateRecord(10**999 + 2, S1_STRATEGY, "parity_prefix", parent=10**999, prefix_length=1)

            def fake_eval(_n):
                return EvaluationWithMetrics(
                    EvaluationResult(10**999 + 2, 3, "repeated_state", 10**999 + 2, repeated_state=10**999 + 2, cycle_entry_step=0, cycle_period=3, stopping_reason="repeated_state"),
                    RecurrenceMetrics(1, 1/3, None, 1.0, 1, 65537, 1),
                )

            import bigcollatz.adaptive as adaptive
            original = adaptive._records_for_cell
            try:
                adaptive._records_for_cell = fake_records
                result = run_adaptive_pilot(root, pilot_id="p-test", stage="test", seed="seed", cells=[cell], evaluator=fake_eval)
            finally:
                adaptive._records_for_cell = original
            self.assertEqual(result["repeated_state_count"], 1)
            evidence = result["cycle_evidence"][0]
            for key in ("repeated_integer", "first_seen_step", "repeated_at_step", "cycle_length", "cell_id", "family", "validation_mode", "parent_starting_integer"):
                self.assertIn(key, evidence)
            persisted = json.loads((root / "results" / "cycle_candidates.json").read_text())
            self.assertEqual(persisted[0]["cell_id"], "fake-cell")
            self.assertEqual(persisted[0]["family"], "parity_prefix")

    def test_discovery_artifact_creation_with_known_one_cycle_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = {"starting_integer":"1","repeated_integer":"1","first_seen_step":0,"repeated_at_step":3,"cycle_length":3,"cycle_members":["4","2","1"],"pilot_id":"fixture","strategy":S5_STRATEGY,"cell_id":"fixture-cell","family":"decimal_suffix","deterministic_seed":"fixture","cell_parameters":{"suffix_digits":1},"parent_starting_integer":"1","parent_rank":1,"validation_mode":"decimal_suffix"}
            discovery = create_nontrivial_cycle_discovery(root, evidence)
            self.assertFalse(discovery["independent_replay_confirmed"])
            self.assertFalse((root / "results" / "nontrivial_cycle_discovery.json").exists())


if __name__ == "__main__":
    unittest.main()
