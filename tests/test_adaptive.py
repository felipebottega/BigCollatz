import json
import tempfile
import unittest
from pathlib import Path

from bigcollatz.adaptive import CellSpec, evaluate_with_recurrence, run_adaptive_pilot, stage_a_cells, stage_b_cells
from bigcollatz.generator import CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY, validate_parity_prefix, validate_decimal_suffix, validate_residue
from bigcollatz.experiment import _validate_candidate_record

class RecurrenceMetricTests(unittest.TestCase):
    def test_recurrence_metrics_are_streaming_summaries(self):
        result, metrics = evaluate_with_recurrence(27)
        self.assertEqual(result.outcome, "reached_one")
        self.assertEqual(result.total_steps_executed, 111)
        self.assertGreater(metrics["odd_step_density"], 0)
        self.assertGreater(metrics["same_decimal_digit_band_returns"], 0)
        self.assertIn("/27", metrics["max_excursion_ratio"])

class AdaptivePilotTests(unittest.TestCase):
    def _root(self):
        d=tempfile.TemporaryDirectory(); root=Path(d.name); (root/"results").mkdir()
        parents=["9"*1000, "8"+"7"*999]
        (root/"results"/"global_top_10.json").write_text(json.dumps([{"starting_integer":p} for p in parents]))
        self.addCleanup(d.cleanup)
        return root, [int(p) for p in parents]

    def test_stage_a_cells_cover_required_families(self):
        _, parents = self._root()
        cells = stage_a_cells(parents, count_per_cell=2)
        self.assertEqual({c.family for c in cells}, {"parity_prefix", "decimal_suffix", "residue"})
        self.assertEqual(sum(c.count for c in cells), 12)

    def test_strategy_bound_validation_rejects_cross_family_mismatch(self):
        record = CandidateRecord(27, S5_STRATEGY, "decimal_suffix", parent=27, suffix_digits=1)
        with self.assertRaisesRegex(ValueError, "incompatible"):
            _validate_candidate_record(record, S1_STRATEGY)
        bad = CandidateRecord(28, S5_STRATEGY, "decimal_suffix", parent=27, suffix_digits=1)
        with self.assertRaisesRegex(ValueError, "decimal suffix"):
            _validate_candidate_record(bad, S5_STRATEGY)
        incomplete = CandidateRecord(27, S6_STRATEGY, "residue")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            _validate_candidate_record(incomplete, S6_STRATEGY)

    def test_run_adaptive_pilot_is_isolated_and_validated(self):
        root, parents = self._root()
        before=(root/"results"/"global_top_10.json").read_text()
        cells=[
            CellSpec("p", "parity_prefix", 1, parents[0], 2, prefix_length=8),
            CellSpec("d", "decimal_suffix", 1, parents[0], 2, suffix_digits=4),
            CellSpec("r", "residue", 2, parents[1], 2, residue_modulus=17),
        ]
        result=run_adaptive_pilot(root, pilot_id="pilot", seed="seed", cells=cells)
        self.assertEqual(result["candidates_evaluated"], 6)
        self.assertEqual(result["distinct_candidates"], 6)
        self.assertEqual(len(result["cell_summaries"]), 3)
        self.assertEqual((root/"results"/"global_top_10.json").read_text(), before)
        for entry in result["top_10"]:
            candidate=int(entry["starting_integer"])
            if entry["family"] == "parity_prefix":
                self.assertTrue(validate_parity_prefix(candidate, int(entry["parent_starting_integer"]), entry["prefix_length"]))
            elif entry["family"] == "decimal_suffix":
                self.assertTrue(validate_decimal_suffix(candidate, int(entry["parent_starting_integer"]), entry["suffix_digits"]))
            else:
                self.assertTrue(validate_residue(candidate, entry["residue_modulus"], entry["residue"]))

    def test_stage_b_preserves_diversity(self):
        _, parents = self._root()
        summaries=[]
        for i,fam in enumerate(["parity_prefix","parity_prefix","decimal_suffix","residue"]):
            summaries.append({"cell_id":str(i),"family":fam,"source_parent":str(parents[i%2]),"parent_rank":1,"parameters":{"prefix_length":8} if fam=="parity_prefix" else ({"suffix_digits":4} if fam=="decimal_suffix" else {"residue_modulus":17}),"selection_score":100-i})
        cells=stage_b_cells(summaries, parents, total_count=20)
        self.assertGreaterEqual(len({c.family for c in cells}), 3)
        self.assertEqual(sum(c.count for c in cells), 20)

if __name__ == "__main__":
    unittest.main()
