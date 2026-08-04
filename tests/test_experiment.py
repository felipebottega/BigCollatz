import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bigcollatz.experiment import DEFAULT_CANDIDATE_COUNT, STRATEGY, run_experiment
from bigcollatz.generator import S1_STRATEGY, S2_STRATEGY, S3_STRATEGY, S4_STRATEGY
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


class ExperimentTests(unittest.TestCase):
    def test_default_scope(self):
        self.assertEqual(DEFAULT_CANDIDATE_COUNT, 10_000)
        self.assertEqual(STRATEGY, "S0-uniform-deterministic")

    @patch("bigcollatz.experiment.evaluate", side_effect=interrupted_evaluate)
    def test_guided_strategy_records_generation_parameters(self, _evaluate):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "results/global_top_10.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps([
                {"starting_integer": "1" + "0" * 999},
                {"starting_integer": "2" + "0" * 999},
            ]))
            result = run_experiment(
                root, experiment_id="guided", count=5, seed="fixture",
                strategy=S1_STRATEGY, validate_candidates=True,
            )
            parameters = result["summary"]["strategy"]["parameters"]
            self.assertEqual(parameters["prefix_length"], 256)
            self.assertEqual(parameters["source_global_top_10_file"],
                             "results/global_top_10.json")
            self.assertEqual(parameters["number_of_parents_used"], 2)
            self.assertEqual(parameters["deterministic_seed"], "fixture")
            self.assertEqual([item["candidate_count"]
                              for item in parameters["allocation_per_parent"]], [3, 2])

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
            self.assertTrue(all("parent_starting_integer" not in entry
                                and "prefix_length" not in entry for entry in result["top_10"]))
            self.assertNotIn("Parent (abbreviated)", report)

    @patch("bigcollatz.experiment.parity_prefix_candidate_records")
    @patch("bigcollatz.experiment.evaluate", side_effect=fake_evaluate)
    def test_guided_winner_lineage_survives_outputs_and_global_merge(
            self, _evaluate, candidate_records):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parents = [10**999 + 101, 2 * 10**999 + 202]
            candidates = [10**999 + ordinal for ordinal in range(4)]
            candidate_records.return_value = iter([
                (candidate, parents[index % 2]) for index, candidate in enumerate(candidates)
            ])
            source = root / "results/global_top_10.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps([
                {"starting_integer": str(parent)} for parent in parents
            ]))

            result = run_experiment(
                root, experiment_id="guided-lineage", count=4, seed="fixture",
                strategy=S1_STRATEGY, prefix_length=17,
            )

            expected_parents = {
                str(candidate): str(parents[index % 2])
                for index, candidate in enumerate(candidates)
            }
            for entry in result["top_10"]:
                self.assertEqual(entry["parent_starting_integer"],
                                 expected_parents[entry["starting_integer"]])
                self.assertEqual(entry["prefix_length"], 17)
            stored = json.loads((root / "results/guided-lineage/top_10.json").read_text())
            self.assertEqual(stored, result["top_10"])
            persistent_global = json.loads(source.read_text())
            self.assertEqual(persistent_global, result["global_top_10"])
            self.assertTrue(all("parent_starting_integer" in entry
                                and entry["prefix_length"] == 17
                                for entry in persistent_global))
            report = (root / "results/guided-lineage/summary.md").read_text()
            self.assertIn("Parent (abbreviated)", report)
            self.assertIn("…", report)


    @patch("bigcollatz.experiment.weighted_parity_prefix_candidate_records")
    @patch("bigcollatz.experiment.evaluate", side_effect=fake_evaluate)
    def test_s2_records_parameters_and_lineage_survives_outputs_and_global_merge(
            self, _evaluate, candidate_records):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parents = [10**999 + 101, 2 * 10**999 + 202]
            candidates = [10**999 + ordinal for ordinal in range(4)]
            candidate_records.return_value = iter([
                (candidate, parents[index % 2]) for index, candidate in enumerate(candidates)
            ])
            source = root / "results/e002-s1-parity-prefix-256/top_10.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps([
                {"parent_starting_integer": str(parents[0]), "prefix_length": 256},
                {"parent_starting_integer": str(parents[0]), "prefix_length": 256},
                {"parent_starting_integer": str(parents[1]), "prefix_length": 256},
            ]))

            result = run_experiment(
                root, experiment_id="s2-lineage", count=4, seed="fixture",
                strategy=S2_STRATEGY,
            )

            parameters = result["summary"]["strategy"]["parameters"]
            self.assertEqual(parameters["source_top_10_file"],
                             "results/e002-s1-parity-prefix-256/top_10.json")
            self.assertEqual(parameters["prefix_length"], 256)
            self.assertEqual(parameters["deterministic_seed"], "fixture")
            self.assertEqual(parameters["number_of_productive_parent_lineages"], 2)
            self.assertEqual([item["weight"] for item in parameters["lineage_weights"]], [2, 1])
            self.assertEqual([item["candidate_count"]
                              for item in parameters["allocation_per_parent"]], [3, 1])
            expected_parents = {
                str(candidate): str(parents[index % 2])
                for index, candidate in enumerate(candidates)
            }
            for entry in result["top_10"]:
                self.assertEqual(entry["parent_starting_integer"],
                                 expected_parents[entry["starting_integer"]])
                self.assertEqual(entry["prefix_length"], 256)
            stored = json.loads((root / "results/s2-lineage/top_10.json").read_text())
            self.assertEqual(stored, result["top_10"])
            persistent_global = json.loads((root / "results/global_top_10.json").read_text())
            self.assertTrue(all("parent_starting_integer" in entry
                                and entry["prefix_length"] == 256
                                for entry in persistent_global))
            report = (root / "results/s2-lineage/summary.md").read_text()
            self.assertIn("Parent (abbreviated)", report)


    @patch("bigcollatz.experiment.weighted_parity_prefix_candidate_records")
    @patch("bigcollatz.experiment.evaluate", side_effect=fake_evaluate)
    def test_s3_records_parameters_lineage_outputs_and_report(self, _evaluate, candidate_records):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parents = [10**999 + 101, 2 * 10**999 + 202, 3 * 10**999 + 303, 4 * 10**999 + 404]
            candidates = [10**999 + ordinal for ordinal in range(4)]
            candidate_records.return_value = iter([
                (candidate, parents[index]) for index, candidate in enumerate(candidates)
            ])
            source = root / "results/e003-s2-weighted-lineages-256/top_10.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps([
                {"parent_starting_integer": str(parent), "prefix_length": 256,
                 "strategy": S2_STRATEGY, "experiment_id": "e003-s2-weighted-lineages-256",
                 "outcome": "reached_one"}
                for parent in [parents[0]] * 4 + [parents[1]] * 4 + [parents[2], parents[3]]
            ]))

            result = run_experiment(root, experiment_id="s3-lineage", count=10_000,
                                    seed="fixture", strategy=S3_STRATEGY)

            parameters = result["summary"]["strategy"]["parameters"]
            self.assertEqual(parameters["source_top_10_file"],
                             "results/e003-s2-weighted-lineages-256/top_10.json")
            self.assertEqual(parameters["prefix_length"], 256)
            self.assertEqual(parameters["deterministic_seed"], "fixture")
            self.assertEqual(parameters["number_of_productive_parent_lineages"], 4)
            self.assertEqual([item["weight"] for item in parameters["lineage_weights"]], [4, 4, 1, 1])
            self.assertEqual([item["candidate_count"] for item in parameters["allocation_per_parent"]],
                             [4000, 4000, 1000, 1000])
            candidate_records.assert_called_once_with(10_000, [(parents[0], 4), (parents[1], 4),
                                                              (parents[2], 1), (parents[3], 1)],
                                                      "fixture", 256, S3_STRATEGY)
            self.assertTrue(all("parent_starting_integer" in entry and entry["prefix_length"] == 256
                                for entry in result["top_10"]))
            self.assertTrue(all("parent_starting_integer" in entry and entry["prefix_length"] == 256
                                for entry in result["global_top_10"]))
            self.assertIn("Parent (abbreviated)", (root / "results/s3-lineage/summary.md").read_text())



    @patch("bigcollatz.experiment.mixed_prefix_candidate_records")
    @patch("bigcollatz.experiment.evaluate", side_effect=fake_evaluate)
    def test_s4_records_mixed_prefix_lineage_outputs_and_report(self, _evaluate, candidate_records):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parents = [10**999 + 101, 2 * 10**999 + 202]
            candidates = [10**999 + ordinal for ordinal in range(6)]
            prefixes = [128, 256, 384, 128, 256, 384]
            candidate_records.return_value = iter([
                (candidate, parents[index % 2], prefixes[index])
                for index, candidate in enumerate(candidates)
            ])
            source = root / "results/global_top_10.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps([
                {"starting_integer": str(parent)} for parent in parents
            ]))

            result = run_experiment(root, experiment_id="s4-mixed", count=6, seed="fixture",
                                    strategy=S4_STRATEGY)

            parameters = result["summary"]["strategy"]["parameters"]
            self.assertEqual(parameters["source_global_top_10_file"], "results/global_top_10.json")
            self.assertEqual(parameters["prefix_lengths"], [128, 256, 384])
            self.assertEqual(parameters["number_of_parents_used"], 2)
            self.assertEqual(parameters["deterministic_seed"], "fixture")
            self.assertEqual([item["candidate_count"] for item in parameters["allocation_per_parent_prefix"]],
                             [1, 1, 1, 1, 1, 1])
            self.assertTrue(all("parent_starting_integer" in entry for entry in result["top_10"]))
            self.assertEqual(sorted({entry["prefix_length"] for entry in result["top_10"]}), [128, 256, 384])
            self.assertIn("Parent (abbreviated)", (root / "results/s4-mixed/summary.md").read_text())
            candidate_records.assert_called_once_with(6, parents, "fixture", (128, 256, 384))


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



def repeated_evaluate(candidate: int) -> EvaluationResult:
    length = candidate - 10**999
    if length == 0:
        return EvaluationResult(candidate, 5, "repeated_state", candidate + 10, 42, 2, 3, "repeated_state")
    return EvaluationResult(candidate, 100 + length, "reached_one", candidate + length)


def duplicate_repeated_evaluate(candidate: int) -> EvaluationResult:
    return EvaluationResult(candidate, 5, "repeated_state", candidate + 10, 42, 2, 3, "repeated_state")


class CycleCandidatePersistenceTests(unittest.TestCase):
    @patch("bigcollatz.experiment.baseline_candidates", side_effect=fake_candidates)
    @patch("bigcollatz.experiment.evaluate", side_effect=repeated_evaluate)
    def test_repeated_state_count_and_persistence_outside_top_ten(self, _evaluate, _candidates):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_experiment(root, experiment_id="cycles", count=12)
            self.assertEqual(result["summary"]["repeated_state_count"], 1)
            self.assertEqual(result["summary"]["nontrivial_cycle_candidate_count"], 1)
            self.assertEqual(result["summary"]["smallest_detected_cycle_length"], 3)
            self.assertTrue(all(entry["outcome"] == "reached_one" for entry in result["top_10"]))
            records = json.loads((root / "results/cycle_candidates.json").read_text())
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["repeated_integer"], "42")

    @patch("bigcollatz.experiment.baseline_candidates", side_effect=fake_candidates)
    @patch("bigcollatz.experiment.evaluate", side_effect=duplicate_repeated_evaluate)
    def test_duplicate_cycle_records_are_deduplicated(self, _evaluate, _candidates):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_experiment(root, experiment_id="dupes", count=3)
            records = json.loads((root / "results/cycle_candidates.json").read_text())
            self.assertEqual(len(records), 1)

    @patch("bigcollatz.experiment.parity_prefix_candidate_records")
    @patch("bigcollatz.experiment.evaluate", side_effect=duplicate_repeated_evaluate)
    def test_s1_cycle_record_preserves_lineage(self, _evaluate, candidate_records):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = 10**999 + 100
            candidate_records.return_value = iter([(10**999, parent)])
            source = root / "results/global_top_10.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps([{"starting_integer": str(parent)}]))
            run_experiment(root, experiment_id="s1-cycles", count=1, strategy=S1_STRATEGY, prefix_length=17)
            record = json.loads((root / "results/cycle_candidates.json").read_text())[0]
            self.assertEqual(record["parent_starting_integer"], str(parent))
            self.assertEqual(record["prefix_length"], 17)

    @patch("bigcollatz.experiment.weighted_parity_prefix_candidate_records")
    @patch("bigcollatz.experiment.evaluate", side_effect=duplicate_repeated_evaluate)
    def test_s2_cycle_record_preserves_lineage(self, _evaluate, candidate_records):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = 10**999 + 100
            candidate_records.return_value = iter([(10**999, parent)])
            source = root / "results/e002-s1-parity-prefix-256/top_10.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps([{"parent_starting_integer": str(parent), "prefix_length": 256}]))
            run_experiment(root, experiment_id="s2-cycles", count=1, strategy=S2_STRATEGY)
            record = json.loads((root / "results/cycle_candidates.json").read_text())[0]
            self.assertEqual(record["parent_starting_integer"], str(parent))
            self.assertEqual(record["prefix_length"], 256)


    @patch("bigcollatz.experiment.weighted_parity_prefix_candidate_records")
    @patch("bigcollatz.experiment.evaluate", side_effect=duplicate_repeated_evaluate)
    def test_s3_cycle_record_preserves_lineage(self, _evaluate, candidate_records):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = 10**999 + 100
            candidate_records.return_value = iter([(10**999, parent)])
            source = root / "results/e003-s2-weighted-lineages-256/top_10.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps([{
                "parent_starting_integer": str(parent), "prefix_length": 256,
                "strategy": S2_STRATEGY, "experiment_id": "e003-s2-weighted-lineages-256",
                "outcome": "reached_one",
            }]))
            run_experiment(root, experiment_id="s3-cycles", count=1, strategy=S3_STRATEGY)
            record = json.loads((root / "results/cycle_candidates.json").read_text())[0]
            self.assertEqual(record["parent_starting_integer"], str(parent))
            self.assertEqual(record["prefix_length"], 256)

    @patch("bigcollatz.experiment.baseline_candidates", side_effect=fake_candidates)
    @patch("bigcollatz.experiment.evaluate", side_effect=fake_evaluate)
    def test_no_repeated_state_does_not_create_or_modify_cycle_file(self, _evaluate, _candidates):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "results/cycle_candidates.json"
            path.parent.mkdir(parents=True)
            path.write_text("[]\n")
            before = path.read_text()
            run_experiment(root, experiment_id="no-cycles", count=3)
            self.assertEqual(path.read_text(), before)

if __name__ == "__main__":
    unittest.main()


class EvaluatorUseTests(unittest.TestCase):
    def test_runner_imports_common_exact_evaluator_for_all_strategies(self):
        import bigcollatz.experiment as experiment
        import bigcollatz.evaluator as evaluator
        self.assertIs(experiment.evaluate, evaluator.evaluate)

class StrategyBoundValidationTests(unittest.TestCase):
    def _root_with_global(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        parent = 10**999 + 123456789
        path = root / "results/global_top_10.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps([{"starting_integer": str(parent)}]))
        return directory, root, parent

    @patch("bigcollatz.experiment.validate_residue", side_effect=AssertionError("wrong validator"))
    @patch("bigcollatz.experiment.validate_decimal_suffix", return_value=True)
    @patch("bigcollatz.experiment.evaluate", side_effect=duplicate_repeated_evaluate)
    @patch("bigcollatz.experiment.decimal_suffix_candidate_records")
    def test_s5_dispatch_metadata_cycles_and_unrelated_validator_not_called(self, records, _eval, dec_validator, res_validator):
        from bigcollatz.generator import CandidateRecord, S5_STRATEGY
        directory, root, parent = self._root_with_global()
        with directory:
            records.return_value = iter([CandidateRecord(10**999, S5_STRATEGY, "decimal_suffix", parent=parent, suffix_digits=3)])
            result = run_experiment(root, experiment_id="s5", count=1, strategy=S5_STRATEGY, validate_candidates=True)
            self.assertEqual(result["top_10"][0]["validation_mode"], "decimal_suffix")
            self.assertEqual(result["top_10"][0]["suffix_digits"], 3)
            cycle = json.loads((root / "results/cycle_candidates.json").read_text())[0]
            self.assertEqual(cycle["validation_mode"], "decimal_suffix")
            dec_validator.assert_called_once()
            res_validator.assert_not_called()

    @patch("bigcollatz.experiment.validate_decimal_suffix", side_effect=AssertionError("wrong validator"))
    @patch("bigcollatz.experiment.validate_residue", return_value=True)
    @patch("bigcollatz.experiment.evaluate", side_effect=duplicate_repeated_evaluate)
    @patch("bigcollatz.experiment.residue_candidate_records")
    def test_s6_dispatch_metadata_cycles_and_unrelated_validator_not_called(self, records, _eval, res_validator, dec_validator):
        from bigcollatz.generator import CandidateRecord, S6_STRATEGY
        directory, root, parent = self._root_with_global()
        with directory:
            records.return_value = iter([CandidateRecord(10**999, S6_STRATEGY, "residue", parent=parent, residue_modulus=7, residue=1)])
            result = run_experiment(root, experiment_id="s6", count=1, strategy=S6_STRATEGY, validate_candidates=True)
            self.assertEqual(result["top_10"][0]["validation_mode"], "residue")
            self.assertEqual(result["top_10"][0]["residue_modulus"], 7)
            cycle = json.loads((root / "results/cycle_candidates.json").read_text())[0]
            self.assertEqual(cycle["validation_mode"], "residue")
            res_validator.assert_called_once()
            dec_validator.assert_not_called()

    @patch("bigcollatz.experiment.evaluate", side_effect=fake_evaluate)
    @patch("bigcollatz.experiment.decimal_suffix_candidate_records")
    def test_s5_rejects_residue_mode_and_incomplete_or_invalid_metadata(self, records, _eval):
        from bigcollatz.generator import CandidateRecord, S5_STRATEGY
        directory, root, parent = self._root_with_global()
        with directory:
            records.return_value = iter([CandidateRecord(10**999, S5_STRATEGY, "residue", parent=parent, residue_modulus=7, residue=1)])
            with self.assertRaises(ValueError):
                run_experiment(root, experiment_id="bad-mode", count=1, strategy=S5_STRATEGY, validate_candidates=True)
            records.return_value = iter([CandidateRecord(10**999, S5_STRATEGY, "decimal_suffix", parent=parent)])
            with self.assertRaises(ValueError):
                run_experiment(root, experiment_id="missing", count=1, strategy=S5_STRATEGY, validate_candidates=True)
            records.return_value = iter([CandidateRecord(10**999, S5_STRATEGY, "decimal_suffix", parent=parent, suffix_digits=3)])
            with self.assertRaises(ValueError):
                run_experiment(root, experiment_id="invalid", count=1, strategy=S5_STRATEGY, validate_candidates=True)

    @patch("bigcollatz.experiment.evaluate", side_effect=fake_evaluate)
    @patch("bigcollatz.experiment.residue_candidate_records")
    def test_s6_rejects_decimal_suffix_mode_and_incomplete_or_invalid_metadata(self, records, _eval):
        from bigcollatz.generator import CandidateRecord, S6_STRATEGY
        directory, root, parent = self._root_with_global()
        with directory:
            records.return_value = iter([CandidateRecord(10**999, S6_STRATEGY, "decimal_suffix", parent=parent, suffix_digits=3)])
            with self.assertRaises(ValueError):
                run_experiment(root, experiment_id="bad-mode", count=1, strategy=S6_STRATEGY, validate_candidates=True)
            records.return_value = iter([CandidateRecord(10**999, S6_STRATEGY, "residue", parent=parent, residue_modulus=7)])
            with self.assertRaises(ValueError):
                run_experiment(root, experiment_id="missing", count=1, strategy=S6_STRATEGY, validate_candidates=True)
            records.return_value = iter([CandidateRecord(10**999, S6_STRATEGY, "residue", parent=parent, residue_modulus=7, residue=2)])
            with self.assertRaises(ValueError):
                run_experiment(root, experiment_id="invalid", count=1, strategy=S6_STRATEGY, validate_candidates=True)
