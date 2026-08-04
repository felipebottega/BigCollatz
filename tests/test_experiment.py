import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bigcollatz.experiment import run_pilot
from bigcollatz.model import EvaluationResult


class ExperimentTests(unittest.TestCase):
    def test_interrupted_trajectories_are_excluded_from_length_statistics_and_top_ten(self):
        calls = 0

        def alternating_result(start):
            nonlocal calls
            calls += 1
            if calls % 2:
                return EvaluationResult(start, 999, "interrupted", start,
                                        stopping_reason="safety_limit",
                                        safety_limit_kind="steps", safety_limit_value=999)
            return EvaluationResult(start, 5, "reached_one", start)

        with tempfile.TemporaryDirectory() as directory, \
                patch("bigcollatz.experiment.evaluate", side_effect=alternating_result):
            result = run_pilot(Path(directory), per_digit=1)

            summary = result["summary"]
            self.assertEqual(summary["outcomes"]["interrupted"], 3)
            self.assertEqual(summary["steps"], {
                "mean": 5.0, "median": 5, "p90_linear_interpolation": 5, "maximum": 5,
            })
            self.assertEqual(len(summary["top_10"]), 3)
            self.assertTrue(all(item["total_steps_executed"] == 5
                                for item in summary["top_10"]))
            written = (Path(directory) / "reports/e000-p0-pilot/summary.json").read_text()
            self.assertNotIn('"total_steps_executed": 999', written)

    def test_no_completed_trajectories_produces_null_statistics(self):
        def interrupted(start):
            return EvaluationResult(start, 999, "interrupted", start,
                                    stopping_reason="safety_limit",
                                    safety_limit_kind="steps", safety_limit_value=999)

        with tempfile.TemporaryDirectory() as directory, \
                patch("bigcollatz.experiment.evaluate", side_effect=interrupted):
            summary = run_pilot(Path(directory), per_digit=1)["summary"]
            self.assertEqual(summary["steps"], {
                "mean": None, "median": None, "p90_linear_interpolation": None,
                "maximum": None,
            })
            self.assertEqual(summary["top_10"], [])
            self.assertIsNone(summary["best_starting_integer"])

    def test_report_contains_starts_and_strata(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pilot(Path(directory), per_digit=1)
            summary = result["summary"]
            self.assertEqual(len(summary["top_10"]), 6)
            self.assertEqual(set(summary["by_decimal_digits"]),
                             {"500", "600", "700", "800", "900", "1000"})
            self.assertIn("best_starting_integer", summary)
            report = (Path(directory) / "reports/e000-p0-pilot/summary.md").read_text()
            self.assertIn("Top 10 by trajectory length", report)
            self.assertIn(summary["best_starting_integer"], report)


if __name__ == "__main__":
    unittest.main()
