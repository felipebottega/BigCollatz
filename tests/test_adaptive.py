import json, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch
from bigcollatz.adaptive import AdaptiveCell, run_adaptive_pilot, validate_cell, validate_record_for_cell
from bigcollatz.generator import CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY
from bigcollatz.model import EvaluationResult
from bigcollatz.evaluator import EvaluationMetrics

P=10**999+1
C=10**999+3

def metric(): return EvaluationMetrics(1,(1,1),None,1,1,0,0,1024)
def reached(n): return EvaluationResult(n,2,"reached_one",n), metric()
def cell(f="parity-prefix", count=1):
    if f=="parity-prefix": return AdaptiveCell("c",f,S1_STRATEGY,"parity_prefix",P,1,count,{"prefix_length":1})
    if f=="decimal-suffix": return AdaptiveCell("c",f,S5_STRATEGY,"decimal_suffix",P,1,count,{"suffix_digits":1})
    return AdaptiveCell("c",f,S6_STRATEGY,"residue",P,1,count,{"residue_modulus":10})
def rec(f="parity-prefix", cand=C):
    if f=="parity-prefix": return CandidateRecord(cand,S1_STRATEGY,"parity_prefix",parent=P,prefix_length=1)
    if f=="decimal-suffix": return CandidateRecord(((C//10)*10+P%10)+10,S5_STRATEGY,"decimal_suffix",parent=P,suffix_digits=1)
    return CandidateRecord(((C//10)*10+P%10)+10,S6_STRATEGY,"residue",parent=P,residue_modulus=10,residue=P%10)

class AdaptiveTests(unittest.TestCase):
    def test_cell_validation(self):
        for kwargs in [{"parent_rank":0},{"parent_rank":-1},{"candidate_count":0}]:
            c=cell(); c=AdaptiveCell(c.cell_id,c.family,c.strategy,c.validation_mode,c.source_parent,kwargs.get("parent_rank",c.parent_rank),kwargs.get("candidate_count",c.candidate_count),c.parameters)
            with self.assertRaises(ValueError): validate_cell(c)
        with self.assertRaises(ValueError): validate_cell(AdaptiveCell("c","parity-prefix",S1_STRATEGY,"parity_prefix",P,True,1,{"prefix_length":1}))
        with self.assertRaises(ValueError): validate_cell(AdaptiveCell("c","parity-prefix",S1_STRATEGY,"parity_prefix",P,1,1,{}))
        with self.assertRaises(ValueError): validate_cell(AdaptiveCell("c","parity-prefix",S1_STRATEGY,"parity_prefix",P,1,1,{"prefix_length":0,"x":1}))

    def test_record_positive_controls(self):
        for f in ("parity-prefix","decimal-suffix","residue"):
            seen=set(); validate_record_for_cell(rec(f), cell(f), seen); self.assertEqual(len(seen),1)

    def test_record_rejections_before_eval(self):
        cases=[CandidateRecord(C,S1_STRATEGY,"parity_prefix",parent=P), CandidateRecord(C,S1_STRATEGY,"parity_prefix",parent=P,prefix_length=2), CandidateRecord(C,S1_STRATEGY,"parity_prefix",parent=P,prefix_length=1,suffix_digits=1), CandidateRecord(C,S1_STRATEGY,"parity_prefix",parent=P,prefix_length=1,residue=1), CandidateRecord(C,"wrong","parity_prefix",parent=P,prefix_length=1), CandidateRecord(C,S1_STRATEGY,"wrong",parent=P,prefix_length=1), CandidateRecord(C,S1_STRATEGY,"parity_prefix",parent=P+2,prefix_length=1)]
        for r in cases:
            with self.subTest(r=r), self.assertRaises(ValueError): validate_record_for_cell(r, cell(), set())

    def test_generator_counts_timing_and_totals(self):
        times=iter([0,0,2,2])
        with tempfile.TemporaryDirectory() as d:
            s=run_adaptive_pilot(Path(d),pilot_id="p",deterministic_seed="seed",cells=[cell(count=1)],generators={"c":[rec()]},evaluator=reached,timer=lambda: next(times))
            self.assertEqual(s["stopping_reason"],"completed"); self.assertEqual(s["candidates_evaluated"],1); self.assertEqual(s["distinct_candidate_count"],1); self.assertEqual(s["cells"][0]["runtime_seconds"],2); self.assertEqual(s["cells"][0]["trajectories_per_second"],0.5)
        for records,msg in [([],"short"),([rec(),rec(cand=C+2)],"long")]:
            with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError,msg): run_adaptive_pilot(Path(d),pilot_id="p",deterministic_seed="seed",cells=[cell(count=1)],generators={"c":records},evaluator=reached)


    def test_zero_runtime_persists_null_throughput(self):
        times=iter([1,1,1,1])
        with tempfile.TemporaryDirectory() as d:
            s=run_adaptive_pilot(Path(d),pilot_id="p",deterministic_seed="seed",cells=[cell(count=1)],generators={"c":[rec()]},evaluator=reached,timer=lambda: next(times))
        self.assertEqual(s["stopping_reason"], "completed")
        self.assertEqual(s["cells"][0]["runtime_seconds"], 0)
        self.assertIsNone(s["cells"][0]["trajectories_per_second"])


    def test_pilot_id_must_be_single_portable_path_safe_name(self):
        invalid_pilot_ids = ["", ".", "..", "a/b", "a\\b", "../p", "..\\p", "/tmp/p", "C:\\temp\\p", "\\\\server\\share"]
        for pilot_id in invalid_pilot_ids:
            with self.subTest(pilot_id=pilot_id), tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError, "pilot_id"):
                run_adaptive_pilot(Path(d),pilot_id=pilot_id,deterministic_seed="seed",cells=[cell()],generators={"c":[rec()]},evaluator=reached)

        with tempfile.TemporaryDirectory() as d:
            s=run_adaptive_pilot(Path(d),pilot_id="p007-adaptive-stage-a-300",deterministic_seed="seed",cells=[cell()],generators={"c":[rec()]},evaluator=reached)
        self.assertEqual(s["pilot_id"], "p007-adaptive-stage-a-300")

    def test_duplicates_before_second_evaluation(self):
        ev=Mock(side_effect=reached)
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError,"duplicate"):
            run_adaptive_pilot(Path(d),pilot_id="p",deterministic_seed="seed",cells=[cell(count=2)],generators={"c":[rec(),rec()]},evaluator=ev)
        self.assertEqual(ev.call_count,1)

    def test_early_stop(self):
        cyc=EvaluationResult(C,1,"repeated_state",C,C,0,1,"repeated_state")
        ev=Mock(return_value=(cyc,metric()))
        with tempfile.TemporaryDirectory() as d, patch("bigcollatz.adaptive.reconstruct_cycle",return_value=[C]), patch("bigcollatz.adaptive.verify_nontrivial_cycle") as ver, patch("bigcollatz.cycle.verify_nontrivial_cycle") as ver2:
            ver.return_value=type("V",(),{"confirmed":True,"failure_reason":None})()
            ver2.return_value=type("V",(),{"confirmed":True,"members":[C],"failure_reason":None})()
            s=run_adaptive_pilot(Path(d),pilot_id="p",deterministic_seed="seed",cells=[cell(count=1)],generators={"c":[rec()]},evaluator=ev)
            self.assertTrue(s["stopped_early"]); self.assertEqual(s["stopping_reason"],"verified_nontrivial_cycle"); self.assertEqual(s["candidates_evaluated"],1); self.assertTrue((Path(d)/"NONTRIVIAL_CYCLE_FOUND.md").exists())

class CandidateRecordCompleteNegativeTests(unittest.TestCase):
    def assert_rejects_before_eval(self, record, adaptive_cell):
        evaluator=Mock()
        with self.assertRaises(ValueError):
            validate_record_for_cell(record, adaptive_cell, set())
        evaluator.assert_not_called()

    def test_all_required_negative_metadata_cases(self):
        suffix_cell=cell("decimal-suffix")
        residue_cell=cell("residue")
        cases=[
            (CandidateRecord(C,S5_STRATEGY,"decimal_suffix",parent=P), suffix_cell),
            (CandidateRecord(C,S5_STRATEGY,"decimal_suffix",parent=P,suffix_digits=2), suffix_cell),
            (CandidateRecord(C,S5_STRATEGY,"decimal_suffix",parent=P,suffix_digits=1,prefix_length=1), suffix_cell),
            (CandidateRecord(C,S5_STRATEGY,"decimal_suffix",parent=P,suffix_digits=1,residue=1), suffix_cell),
            (CandidateRecord(C,S6_STRATEGY,"residue",parent=P,residue=P%10), residue_cell),
            (CandidateRecord(C,S6_STRATEGY,"residue",parent=P,residue_modulus=10), residue_cell),
            (CandidateRecord(C,S6_STRATEGY,"residue",parent=P,residue_modulus=11,residue=P%11), residue_cell),
            (CandidateRecord(C,S6_STRATEGY,"residue",parent=P,residue_modulus=10,residue=(P+1)%10), residue_cell),
            (CandidateRecord(C,S6_STRATEGY,"residue",parent=P,residue_modulus=10,residue=P%10,prefix_length=1), residue_cell),
            (CandidateRecord(C,S6_STRATEGY,"residue",parent=P,residue_modulus=10,residue=P%10,suffix_digits=1), residue_cell),
            (CandidateRecord(10**999+2,S1_STRATEGY,"parity_prefix",parent=P,prefix_length=1), cell()),
        ]
        for record, adaptive_cell in cases:
            with self.subTest(record=record):
                self.assert_rejects_before_eval(record, adaptive_cell)

class MultiCellTests(unittest.TestCase):
    def test_multiple_cells_exact_counts(self):
        c1=cell(); c2=AdaptiveCell("d","decimal-suffix",S5_STRATEGY,"decimal_suffix",P,1,1,{"suffix_digits":1})
        with tempfile.TemporaryDirectory() as d:
            s=run_adaptive_pilot(Path(d),pilot_id="p",deterministic_seed="seed",cells=[c1,c2],generators={"c":[rec()],"d":[rec("decimal-suffix")]},evaluator=reached)
            self.assertEqual(s["requested_candidate_count"],2)
            self.assertEqual(s["candidates_evaluated"],2)
            self.assertEqual([x["candidates_evaluated"] for x in s["cells"]],[1,1])

    def test_duplicate_across_cells(self):
        c1=cell(); c2=AdaptiveCell("d","parity-prefix",S1_STRATEGY,"parity_prefix",P,1,1,{"prefix_length":1})
        ev=Mock(side_effect=reached)
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError,"duplicate"):
            run_adaptive_pilot(Path(d),pilot_id="p",deterministic_seed="seed",cells=[c1,c2],generators={"c":[rec()],"d":[rec()]},evaluator=ev)
        self.assertEqual(ev.call_count,1)

class AdaptiveSummaryAccuracyTests(unittest.TestCase):
    def test_normal_completion_aggregates_thresholds_tail_and_score(self):
        c = cell(count=2)
        records = [rec(cand=C), rec(cand=C+2)]
        results = [
            (EvaluationResult(C, 25000, "reached_one", C*2), EvaluationMetrics(3,(3,10),5,4,2,1,7,1024)),
            (EvaluationResult(C+2, 27000, "reached_one", (C+2)*3), EvaluationMetrics(5,(5,20),None,9,3,3,11,1024)),
        ]
        with tempfile.TemporaryDirectory() as d:
            s=run_adaptive_pilot(Path(d),pilot_id="p",deterministic_seed="seed",cells=[c],generators={"c":records},evaluator=Mock(side_effect=results))
        cs=s["cells"][0]
        self.assertEqual(cs["candidates_evaluated"], cs["requested_candidate_count"])
        self.assertEqual(s["candidates_evaluated"], s["requested_candidate_count"])
        self.assertEqual(s["distinct_candidate_count"], s["candidates_evaluated"])
        self.assertEqual(cs["fixed_threshold_exceedance_counts"], {"length_gte_25000":2,"length_gte_26000":1,"length_gte_27000":1,"length_gte_27707":0})
        self.assertEqual(cs["overall_pilot_top_tail_count"], 1)
        ag=cs["recurrence_metric_aggregates"]
        self.assertEqual(ag["mean_odd_step_count"], 4)
        self.assertEqual(ag["odd_step_density"], {"numerator":8,"denominator":30})
        self.assertEqual(ag["mean_odd_step_density"], 0.275)
        self.assertEqual(ag["mean_first_descent_step"], 5)
        self.assertEqual(ag["undefined_first_descent_count"], 1)
        self.assertEqual(ag["maximum_excursion"], {"numerator":9,"denominator":3})
        self.assertEqual(ag["mean_same_decimal_digit_band_return_count"], 2)
        self.assertEqual(ag["mean_repeated_residue_hit_count"], 9)
        self.assertEqual(ag["residue_modulus"], 1024)
        self.assertGreater(cs["deterministic_score"], 0)

    def test_top_tail_ties_are_deterministic_and_score_uses_metric(self):
        c1=cell(count=1); c2=AdaptiveCell("d","parity-prefix",S1_STRATEGY,"parity_prefix",P,1,1,{"prefix_length":1})
        def run(hit):
            with tempfile.TemporaryDirectory() as d:
                return run_adaptive_pilot(Path(d),pilot_id="p",deterministic_seed="seed",cells=[c1,c2],generators={"c":[rec(cand=C)],"d":[rec(cand=C+2)]},evaluator=Mock(side_effect=[(EvaluationResult(C, 100, "reached_one", C), EvaluationMetrics(1,(1,2),1,1,1,0,hit,1024)),(EvaluationResult(C+2, 100, "reached_one", C+2), EvaluationMetrics(1,(1,2),1,1,1,0,0,1024))]))
        s1=run(0); s2=run(5)
        self.assertEqual([x["overall_pilot_top_tail_count"] for x in s1["cells"]], [1,0])
        self.assertGreater(s2["cells"][0]["deterministic_score"], s1["cells"][0]["deterministic_score"])
        self.assertIsNotNone(s1["cells"][0]["p99_trajectory_length"])

    def test_inconsistent_residue_modulus_and_global_modification_are_errors(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); gp=root/"results"/"global_top_10.json"; gp.parent.mkdir(); gp.write_bytes(b"[]\n")
            def bad(_):
                gp.write_bytes(b"[1]\n")
                return reached(C)
            with self.assertRaisesRegex(RuntimeError,"modified global"):
                run_adaptive_pilot(root,pilot_id="p",deterministic_seed="seed",cells=[cell()],generators={"c":[rec()]},evaluator=bad)
            self.assertFalse(json.loads((root/"results"/"p"/"summary.json").read_text())["global_top_10_isolated"])
        with tempfile.TemporaryDirectory() as d:
            vals=[(EvaluationResult(C,1,"reached_one",C), EvaluationMetrics(1,(1,1),None,1,1,0,0,1024)),(EvaluationResult(C+2,1,"reached_one",C+2), EvaluationMetrics(1,(1,1),None,1,1,0,0,2048))]
            with self.assertRaisesRegex(ValueError,"inconsistent residue"):
                run_adaptive_pilot(Path(d),pilot_id="p",deterministic_seed="seed",cells=[cell(count=2)],generators={"c":[rec(),rec(cand=C+2)]},evaluator=Mock(side_effect=vals))

    def test_immediate_stop_does_not_advance_generator(self):
        class Sentinel:
            def __init__(self): self.calls=0
            def __iter__(self): return self
            def __next__(self):
                self.calls += 1
                if self.calls == 1: return rec()
                raise AssertionError("generator advanced after verified discovery")
        cyc=EvaluationResult(C,1,"repeated_state",C,C,0,1,"repeated_state")
        ev=Mock(return_value=(cyc,metric()))
        with tempfile.TemporaryDirectory() as d, patch("bigcollatz.adaptive.reconstruct_cycle",return_value=[C]), patch("bigcollatz.adaptive.verify_nontrivial_cycle") as ver, patch("bigcollatz.cycle.verify_nontrivial_cycle") as ver2:
            root=Path(d); gp=root/"results"/"global_top_10.json"; gp.parent.mkdir(); gp.write_bytes(b"[]\n")
            ver.return_value=type("V",(),{"confirmed":True,"failure_reason":None})()
            ver2.return_value=type("V",(),{"confirmed":True,"members":[C],"failure_reason":None})()
            sentinel=Sentinel()
            s=run_adaptive_pilot(root,pilot_id="p",deterministic_seed="seed",cells=[cell(count=2)],generators={"c":sentinel},evaluator=ev)
            self.assertEqual(s["candidates_evaluated"],1); self.assertEqual(s["requested_candidate_count"],2)
            self.assertEqual(ev.call_count,1); self.assertEqual(sentinel.calls,1)
            self.assertTrue(s["stopped_early"]); self.assertEqual(s["stopping_reason"],"verified_nontrivial_cycle")
            self.assertTrue((root/"results"/"nontrivial_cycle_discovery.json").exists())
            self.assertTrue((root/"NONTRIVIAL_CYCLE_FOUND.md").exists())
            self.assertTrue((root/"results"/"cycle_candidates.json").exists())
            self.assertEqual(gp.read_bytes(), b"[]\n")
