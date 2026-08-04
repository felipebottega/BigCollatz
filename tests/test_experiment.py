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


class ExperimentTests(unittest.TestCase):
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
            report = (root / "results/e001/summary.md").read_text()
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


if __name__ == "__main__":
    unittest.main()
