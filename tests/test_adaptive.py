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
    if f=="decimal-suffix": return CandidateRecord((C//10)*10+P%10,S5_STRATEGY,"decimal_suffix",parent=P,suffix_digits=1)
    return CandidateRecord((C//10)*10+P%10,S6_STRATEGY,"residue",parent=P,residue_modulus=10,residue=P%10)

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
