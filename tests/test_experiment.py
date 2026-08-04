import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bigcollatz.experiment import DEFAULT_CANDIDATE_COUNT, STRATEGY, run_experiment
from bigcollatz.model import EvaluationResult


def fake_candidates(count: int, seed: str):
    del seed
    yield from (10**999 + ordinal for ordinal in range(count))


def fake_evaluate(candidate: int) -> EvaluationResult:
    length = candidate - 10**999
    return EvaluationResult(candidate, length, "reached_one", candidate + length)


def mixed_evaluate(candidate: int) -> EvaluationResult:
    length = candidate - 10**999
    if length % 2:
        return EvaluationResult(candidate, 10_000 + length, "interrupted", candidate,
                                stopping_reason="user_stop")
    return EvaluationResult(candidate, length, "reached_one", candidate + length)


def interrupted_evaluate(candidate: int) -> EvaluationResult:
    return EvaluationResult(candidate, 123, "interrupted", candidate,
                            stopping_reason="user_stop")


def fake_s1_candidates(count: int, seed: str):
    del seed
    for ordinal in range(count):
        parent = 2 * 10**999 + ordinal
        yield 10**999 + ordinal, parent


class ExperimentTests(unittest.TestCase):
    @patch("bigcollatz.experiment.baseline_candidates", side_effect=fake_s1_candidates)
    @patch("bigcollatz.experiment.evaluate", side_effect=fake_evaluate)
    def test_s1_lineage_survives_local_global_and_report(self, _evaluate, _candidates):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_experiment(root, experiment_id="s1", count=3, prefix_length=17)
            for entry in result["top_10"]:
                ordinal = int(entry["starting_integer"]) - 10**999
                self.assertEqual(entry["parent_starting_integer"], str(2 * 10**999 + ordinal))
                self.assertEqual(entry["prefix_length"], 17)
            self.assertEqual(result["top_10"], result["global_top_10"])
            self.assertEqual(result["top_10"], json.loads(
                (root / "results/s1/top_10.json").read_text()))
            self.assertIn("Parent (abbreviated)", (root / "results/s1/summary.md").read_text())

    def test_default_scope(self):
        self.assertEqual(DEFAULT_CANDIDATE_COUNT, 10_000)
        self.assertEqual(STRATEGY, "S0-uniform-deterministic")

    @patch("bigcollatz.experiment.baseline_candidates", side_effect=fake_candidates)
    @patch("bigcollatz.experiment.evaluate", side_effect=fake_evaluate)
    def test_writes_only_summaries_and_top_tens(self, _evaluate, _candidates):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_experiment(root, experiment_id="e001", count=12, seed="fixture")
            experiment_files = {path.name for path in (root / "results/e001").iterdir()}
            self.assertEqual(experiment_files, {"summary.json", "summary.md", "top_10.json"})
            self.assertEqual(len(result["top_10"]), 10)
            self.assertEqual(result["top_10"][0]["total_unaccelerated_trajectory_length"], 11)
            self.assertEqual(result["summary"]["candidates_evaluated"], 12)
            self.assertEqual(result["summary"]["p99_trajectory_length"], 10.89)
            stored = json.loads((root / "results/e001/top_10.json").read_text())
            self.assertEqual(stored, result["top_10"])
            self.assertTrue(all("parent_starting_integer" not in entry and
                                "prefix_length" not in entry for entry in stored))
            report = (root / "results/e001/summary.md").read_text()
            self.assertNotIn("Parent (abbreviated)", report)
            self.assertIn("…", report)
            self.assertIn(result["top_10"][0]["starting_integer"], report)
            self.assertFalse(any(path.suffix in {".jsonl", ".csv"} for path in root.rglob("*")))

    @patch("bigcollatz.experiment.baseline_candidates", side_effect=fake_candidates)
    @patch("bigcollatz.experiment.evaluate", side_effect=fake_evaluate)
    def test_global_top_ten_is_merged_and_deduplicated(self, _evaluate, _candidates):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_experiment(root, experiment_id="first", count=10)
            run_experiment(root, experiment_id="second", count=12)
            global_top = json.loads((root / "results/global_top_10.json").read_text())
            self.assertEqual(len(global_top), 10)
            self.assertEqual(len({entry["starting_integer"] for entry in global_top}), 10)
            self.assertEqual(global_top[0]["experiment_id"], "second")
            self.assertEqual(global_top[0]["total_unaccelerated_trajectory_length"], 11)

    @patch("bigcollatz.experiment.baseline_candidates", side_effect=fake_candidates)
    @patch("bigcollatz.experiment.evaluate", side_effect=mixed_evaluate)
    def test_interrupted_are_excluded_from_statistics_and_top_tens(self, _evaluate, _candidates):
        with tempfile.TemporaryDirectory() as directory:
            result = run_experiment(Path(directory), experiment_id="mixed", count=6)
            self.assertEqual(result["summary"]["interrupted_count"], 3)
            self.assertEqual(result["summary"]["mean_trajectory_length"], 2.0)
            self.assertEqual(result["summary"]["maximum_trajectory_length"], 4)
            self.assertTrue(all(entry["outcome"] != "interrupted" for entry in result["top_10"]))
            self.assertTrue(all(entry["outcome"] != "interrupted" for entry in result["global_top_10"]))

    @patch("bigcollatz.experiment.baseline_candidates", side_effect=fake_candidates)
    @patch("bigcollatz.experiment.evaluate", side_effect=interrupted_evaluate)
    def test_all_interrupted_has_null_statistics_and_empty_tops(self, _evaluate, _candidates):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_experiment(root, experiment_id="interrupted", count=3)
            for name in ("mean_trajectory_length", "median_trajectory_length",
                         "p90_trajectory_length", "p99_trajectory_length",
                         "maximum_trajectory_length"):
                self.assertIsNone(result["summary"][name])
            self.assertEqual(result["summary"]["interrupted_count"], 3)
            self.assertEqual(result["top_10"], [])
            self.assertEqual(result["global_top_10"], [])
            self.assertEqual(json.loads((root / "results/global_top_10.json").read_text()), [])


if __name__ == "__main__":
    unittest.main()
