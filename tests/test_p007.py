import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from bigcollatz.adaptive import AdaptiveCell, rank_trajectories, run_adaptive_pilot
from bigcollatz.evaluator import EvaluationMetrics
from bigcollatz.generator import CandidateRecord, S1_STRATEGY
from bigcollatz.model import EvaluationResult
from bigcollatz.p007 import build_p007_cells, build_p007_generators, CANDIDATES_PER_CELL, DETERMINISTIC_SEED

PARENT1 = int("1" + "0" * 999)
PARENT2 = int("2" + "0" * 999)


def global_top(path: Path):
    path.parent.mkdir(parents=True)
    records = [{"starting_integer": str(PARENT1), "total_unaccelerated_trajectory_length": 10}, {"starting_integer": str(PARENT2), "total_unaccelerated_trajectory_length": 9}]
    for i in range(8):
        records.append({"starting_integer": str(3 + i if i < 7 else 11).ljust(1000, "0"), "total_unaccelerated_trajectory_length": 8 - i})
    path.write_text(json.dumps(records)+"\n")


class P007DesignTests(unittest.TestCase):
    def test_exact_grid_counts_and_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "results" / "global_top_10.json"
            global_top(p)
            a = build_p007_cells(p)
            b = build_p007_cells(p)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 12)
        self.assertEqual(sum(c.candidate_count for c in a), 300)
        self.assertTrue(all(c.candidate_count == CANDIDATES_PER_CELL for c in a))
        families = {f: sum(c.family == f for c in a) for f in {c.family for c in a}}
        self.assertEqual(families, {"parity-prefix": 4, "decimal-suffix": 4, "residue": 4})

    def test_generators_are_deterministic_and_counted(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "results" / "global_top_10.json"
            global_top(p)
            cells = build_p007_cells(p)
        one = {k: [r.candidate for r in v] for k, v in build_p007_generators(cells).items()}
        two = {k: [r.candidate for r in v] for k, v in build_p007_generators(cells).items()}
        self.assertEqual(one, two)
        self.assertTrue(all(len(v) == 25 for v in one.values()))


class P007RankingTests(unittest.TestCase):
    def test_top30_order_ties_and_decimal_strings(self):
        trajectories = []
        for i in range(35):
            trajectories.append({"starting_integer": str(10**999 + i), "trajectory_length": 100 if i in (1,2) else i, "maximum_integer": str(10**1000 + i), "cell_id": "b" if i == 1 else "a", "family": "f", "strategy": "s", "source_parent": str(PARENT1), "parent_rank": 1, "generation_parameters": {"x": 1}, "validation_mode": "v", "deterministic_seed": DETERMINISTIC_SEED, "candidate_order_within_cell": i})
        ranked = rank_trajectories(trajectories, 30)
        self.assertEqual(len(ranked), 30)
        self.assertEqual(ranked[0]["cell_id"], "a")
        required = {"starting_integer", "trajectory_length", "maximum_integer", "cell_id", "family", "strategy", "source_parent", "parent_rank", "generation_parameters", "validation_mode", "deterministic_seed", "candidate_order_within_cell"}
        self.assertTrue(required <= set(ranked[0]))
        self.assertIsInstance(ranked[0]["starting_integer"], str)
        self.assertIsInstance(ranked[0]["maximum_integer"], str)

    def test_summary_no_placeholders_and_global_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            gp = root / "results" / "global_top_10.json"
            global_top(gp)
            before = gp.read_bytes()
            c = AdaptiveCell("c", "parity-prefix", S1_STRATEGY, "parity_prefix", PARENT1, 1, 1, {"prefix_length": 1})
            rec = CandidateRecord(PARENT1 + 2, S1_STRATEGY, "parity_prefix", parent=PARENT1, prefix_length=1)
            ev = Mock(return_value=(EvaluationResult(rec.candidate, 7, "reached_one", rec.candidate * 3), EvaluationMetrics(3, (3, 7), 2, rec.candidate * 3, rec.candidate, 5, 6, 1024)))
            s = run_adaptive_pilot(root, pilot_id="p", deterministic_seed="seed", cells=[c], generators={"c": [rec]}, evaluator=ev)
            self.assertEqual(gp.read_bytes(), before)
            self.assertTrue(s["global_top_10_isolated"])
            self.assertEqual(s["requested_candidate_count"], 1)
            self.assertEqual(s["candidates_evaluated"], 1)
            self.assertIsNotNone(s["cells"][0]["deterministic_score"])
            self.assertIn("top_30", s["artifact_paths"])

if __name__ == "__main__":
    unittest.main()
