import tempfile
import unittest
from pathlib import Path

from bigcollatz.experiment import run_pilot


class ExperimentTests(unittest.TestCase):
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
