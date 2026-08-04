import json, tempfile, unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import Mock

from bigcollatz.adaptive import *
from bigcollatz.cycle import reconstruct_cycle, verify_cycle, discovery_payload, write_discovery_artifacts
from bigcollatz.evaluator import RecurrenceMetrics
from bigcollatz.model import EvaluationResult
from bigcollatz.generator import CandidateRecord

A=10**999+1; B=10**999+3; C=10**999+5; P=10**999+7; Q=10**999+9

def trans(n): return {A:B,B:C,C:A,P:Q,Q:A}.get(n, 1)
def cell(f='parity-prefix'):
    if f=='parity-prefix': return AdaptiveCell('a','parity-prefix','S1-parity-prefix-top10','parity_prefix',A,1,1,{'prefix_length':1})
    if f=='decimal-suffix': return AdaptiveCell('d','decimal-suffix','S5-decimal-suffix-top10','decimal_suffix',A,1,1,{'suffix_digits':1})
    return AdaptiveCell('r','residue','S6-residue-class-top10','residue',A,1,1,{'residue_modulus':7})
def rec(f='parity-prefix', cand=None):
    cand = cand or A
    if f=='parity-prefix': return CandidateRecord(cand,'S1-parity-prefix-top10','parity_prefix',parent=A,prefix_length=1)
    if f=='decimal-suffix': return CandidateRecord(cand,'S5-decimal-suffix-top10','decimal_suffix',parent=A,suffix_digits=1)
    return CandidateRecord(cand,'S6-residue-class-top10','residue',parent=A,residue_modulus=7,residue=A%7)

class CycleMatrix(unittest.TestCase):
    def test_cycle_begins_at_start(self):
        r=EvaluationResult(A,3,'repeated_state',C,repeated_state=A,cycle_entry_step=0,cycle_period=3,stopping_reason='repeated_state')
        self.assertEqual(reconstruct_cycle(A,r,transition=trans),[A,B,C])
    def test_transient_prefix(self):
        r=EvaluationResult(P,5,'repeated_state',Q,repeated_state=A,cycle_entry_step=2,cycle_period=3,stopping_reason='repeated_state')
        self.assertEqual(reconstruct_cycle(P,r,transition=trans),[A,B,C])
    def test_self_loop(self):
        r=EvaluationResult(A,1,'repeated_state',A,repeated_state=A,cycle_entry_step=0,cycle_period=1,stopping_reason='repeated_state')
        self.assertEqual(reconstruct_cycle(A,r,transition=lambda n:n),[A])
    def test_trivial_cycle_rejected(self):
        from bigcollatz.evaluator import evaluate
        r=evaluate(1, transition=lambda n:n)
        self.assertFalse(verify_cycle(start=1,result=r,claimed_members=['1'],transition=lambda n:n).confirmed)
    def test_tampered_wrong_order_missing_length_repeated_broken_decimal(self):
        r=EvaluationResult(A,3,'repeated_state',C,repeated_state=A,cycle_entry_step=0,cycle_period=3,stopping_reason='repeated_state')
        for members in ([A,B,999],[B,C,A],[B,C],[A,B],[B,B,C],['01',str(B),str(C)]):
            self.assertFalse(verify_cycle(start=A,result=r,claimed_members=members,transition=trans).confirmed)

class AdaptiveValidationTests(unittest.TestCase):
    def test_positive_controls(self):
        for f in ('parity-prefix','decimal-suffix','residue'): validate_record_for_cell(rec(f), cell(f))
    def test_mismatch_matrix_rejected_before_evaluator(self):
        cases=[(rec(), cell()), (CandidateRecord(A,'S1-parity-prefix-top10','parity_prefix',parent=A), cell()), (CandidateRecord(A,'S1-parity-prefix-top10','parity_prefix',parent=A,prefix_length=2), cell()), (CandidateRecord(A,'bad','parity_prefix',parent=A,prefix_length=1), cell()), (CandidateRecord(A,'S1-parity-prefix-top10','bad',parent=A,prefix_length=1), cell()), (CandidateRecord(A,'S1-parity-prefix-top10','parity_prefix',parent=A,prefix_length=1,suffix_digits=1), cell()), (CandidateRecord(A+1,'S1-parity-prefix-top10','parity_prefix',parent=A,prefix_length=1), cell()), (CandidateRecord(A,'S5-decimal-suffix-top10','decimal_suffix',parent=A), cell('decimal-suffix')), (CandidateRecord(A,'S5-decimal-suffix-top10','decimal_suffix',parent=A,suffix_digits=2), cell('decimal-suffix')), (CandidateRecord(A,'S5-decimal-suffix-top10','decimal_suffix',parent=A,suffix_digits=1,prefix_length=1), cell('decimal-suffix')), (CandidateRecord(A+1,'S5-decimal-suffix-top10','decimal_suffix',parent=A,suffix_digits=1), cell('decimal-suffix')), (CandidateRecord(A,'S6-residue-class-top10','residue',parent=A,residue_modulus=7), cell('residue')), (CandidateRecord(A,'S6-residue-class-top10','residue',parent=A,residue_modulus=7,residue=(A+1)%7), cell('residue')), (CandidateRecord(A,'S6-residue-class-top10','residue',parent=A,residue_modulus=5,residue=A%5), cell('residue')), (CandidateRecord(A,'S6-residue-class-top10','residue',parent=A,residue_modulus=7,residue=A%7,prefix_length=1), cell('residue')), (CandidateRecord(A+1,'S6-residue-class-top10','residue',parent=A,residue_modulus=7,residue=A%7), cell('residue'))]
        calls=0
        for record,c in cases[1:]:
            with self.assertRaises(ValueError): validate_record_for_cell(record,c)
        self.assertEqual(calls,0)
    def test_persisted_metadata_consistency(self):
        for f in ('parity-prefix','decimal-suffix','residue'):
            m=metadata_for_artifact(rec(f),cell(f)); self.assertEqual(m['validation_mode'], cell(f).validation_mode); self.assertEqual(m['strategy'], cell(f).strategy)

class AggregationTailScoreAllocation(unittest.TestCase):
    def test_metric_aggregation(self):
        ms=[RecurrenceMetrics(2,Fraction(1,2),3,5,2,1,4,17),RecurrenceMetrics(4,Fraction(1,4),None,3,1,3,6,17)]
        a=aggregate_metrics(ms); self.assertEqual(a['undefined_first_descent_count'],1); self.assertEqual((a['maximum_excursion_numerator'],a['maximum_excursion_denominator']),(3,1)); self.assertAlmostEqual(a['mean_odd_step_density'],.375)
    def test_top_tail_and_tie(self):
        traj=[{'cell_id':'A','length':x,'cell_order':i} for i,x in enumerate([100,90,80])]+[{'cell_id':'B','length':x,'cell_order':i} for i,x in enumerate([70,60,50])]
        self.assertEqual(top_tail_counts(traj,.5), {'A':3})
        self.assertEqual(top_tail_counts([{'cell_id':'B','length':10,'cell_order':0},{'cell_id':'A','length':10,'cell_order':0}],.5), {'A':1})
    def test_score_and_allocation(self):
        s={'mean_trajectory_length':100,'p90_trajectory_length':120,'overall_pilot_top_tail_count':1,'recurrence_metrics':{'mean_repeated_residue_hit_count':1},'repeated_state_count':0}
        self.assertEqual(deterministic_score(s), deterministic_score(s)); self.assertGreater(deterministic_score({**s,'overall_pilot_top_tail_count':2}), deterministic_score(s)); self.assertGreater(deterministic_score({**s,'recurrence_metrics':{'mean_repeated_residue_hit_count':2}}), deterministic_score(s)); self.assertGreater(deterministic_score({'mean_trajectory_length':200,'p90_trajectory_length':200,'p99_trajectory_length':200}), deterministic_score({'mean_trajectory_length':10,'p90_trajectory_length':10,'p99_trajectory_length':1000}))
        for cells,total in [([{'cell_id':'a','score':1}],5),([{'cell_id':'a','score':0},{'cell_id':'b','score':0}],4),([{'cell_id':'a','score':-1},{'cell_id':'b','score':2}],5),([{'cell_id':'a','score':1},{'cell_id':'b','score':1}],2),([{'cell_id':'a','score':1},{'cell_id':'b','score':3}],7)]: self.assertEqual(sum(allocate_stage_b(cells,total).values()), total)
        with self.assertRaises(ValueError): allocate_stage_b([{'cell_id':'a','score':1},{'cell_id':'b','score':1}],1)

class AdaptivePilotIntegration(unittest.TestCase):
    def test_duplicate_rejected_before_second_evaluation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'results').mkdir(); (root/'results/global_top_10.json').write_text('[]')
            c1=cell(); c2=AdaptiveCell('b','parity-prefix','S1-parity-prefix-top10','parity_prefix',A,2,1,{'prefix_length':1})
            ev=Mock(return_value=type('X',(),{'result':EvaluationResult(A,1,'reached_one',A),'metrics':None})())
            with self.assertRaises(ValueError): run_adaptive_pilot(root,pilot_id='p',cells=[c1,c2],generators={'a':[rec()],'b':[CandidateRecord(A,'S1-parity-prefix-top10','parity_prefix',parent=A,prefix_length=1)]},deterministic_seed='s',evaluator=ev)
            self.assertEqual(ev.call_count,1)
    def test_early_stop_discovery_summary_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'results').mkdir(); (root/'results/global_top_10.json').write_text('[]')
            r=EvaluationResult(A,3,'repeated_state',C,repeated_state=A,cycle_entry_step=0,cycle_period=3,stopping_reason='repeated_state')
            ev=Mock(return_value=type('X',(),{'result':r,'metrics':None})())
            with unittest.mock.patch('bigcollatz.adaptive.verify_cycle', return_value=type('V',(),{'confirmed':True,'failure_reason':None,'members':[A,B,C]})()):
                summary=run_adaptive_pilot(root,pilot_id='p',cells=[cell()],generators={'a':iter([rec()])},deterministic_seed='s',evaluator=ev)
            self.assertEqual(ev.call_count,1); self.assertTrue(summary['stopped_early']); self.assertEqual(summary['candidates_evaluated'],1); self.assertTrue((root/'results/nontrivial_cycle_discovery.json').exists()); md=(root/'NONTRIVIAL_CYCLE_FOUND.md').read_text(); [self.assertIn(str(x),md) for x in (A,B,C)]
    def test_failed_verification_no_discovery(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'results').mkdir(); (root/'results/global_top_10.json').write_text('[]')
            r=EvaluationResult(A,3,'repeated_state',C,repeated_state=A,cycle_entry_step=0,cycle_period=3,stopping_reason='repeated_state')
            ev=Mock(return_value=type('X',(),{'result':r,'metrics':None})())
            with unittest.mock.patch('bigcollatz.adaptive.verify_cycle', return_value=type('V',(),{'confirmed':False,'failure_reason':'bad','members':[]})()):
                with self.assertRaises(RuntimeError): run_adaptive_pilot(root,pilot_id='p',cells=[cell()],generators={'a':[rec()]},deterministic_seed='s',evaluator=ev)
            self.assertFalse((root/'results/nontrivial_cycle_discovery.json').exists()); self.assertFalse((root/'NONTRIVIAL_CYCLE_FOUND.md').exists())
