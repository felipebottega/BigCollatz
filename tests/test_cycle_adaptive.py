import json, tempfile, unittest
from unittest.mock import patch
from pathlib import Path

from bigcollatz.adaptive import AdaptiveCell, aggregate_metrics, allocate_stage_b, assign_top_tail, deterministic_score, run_adaptive_pilot
from bigcollatz.cycle import reconstruct_cycle, verify_cycle_evidence, write_discovery_artifacts
from bigcollatz.evaluator import TrajectoryMetrics
from bigcollatz.generator import CandidateRecord, S5_STRATEGY
from bigcollatz.model import EvaluationResult

D=10**999
CELL=AdaptiveCell('c1','decimal-suffix',S5_STRATEGY,'decimal_suffix',D+7,1,1,{'suffix_digits':1})

def ev_repeat(n):
    return type('X',(),{'result':EvaluationResult(n,1,'repeated_state',n,n,0,1,'repeated_state'), 'metrics':TrajectoryMetrics(0,0,None,n,n,0,0,65536)})()

def ev_one(n):
    return type('X',(),{'result':EvaluationResult(n,5,'reached_one',n+1), 'metrics':TrajectoryMetrics(2,.4,3,n+1,n,1,2,65536)})()

class CycleMatrixTests(unittest.TestCase):
    def test_cycle_begin_transient_self_and_trivial(self):
        for start, edges, exp in [(2,{2:3,3:4,4:2},[2,3,4]), (9,{9:8,8:2,2:3,3:4,4:2},[2,3,4]), (7,{7:7},[7])]:
            r=EvaluationResult(start, len(edges) if start==9 else len(exp), 'repeated_state', max(edges), exp[0], 0 if start!=9 else 2, len(exp), 'repeated_state')
            if start==9: r=EvaluationResult(9,5,'repeated_state',9,2,2,3,'repeated_state')
            self.assertEqual(reconstruct_cycle(start,r,transition=edges.__getitem__), exp)
        r=EvaluationResult(4,3,'repeated_state',4,4,0,3,'repeated_state')
        self.assertFalse(verify_cycle_evidence(start=4, expected=r).confirmed)
    def test_tampered_wrong_order_missing_wrong_scalar_noncanonical_fail(self):
        edges={2:3,3:4,4:2}; r=EvaluationResult(2,3,'repeated_state',4,2,0,3,'repeated_state')
        self.assertTrue(verify_cycle_evidence(start=2, expected=r, supplied_cycle_members=['2','3','4'], transition=edges.__getitem__).confirmed)
        for members in (['2','4','3'], ['3','4','2'], ['3','4'], ['02','3','4']):
            self.assertFalse(verify_cycle_evidence(start=2, expected=r, supplied_cycle_members=members, transition=edges.__getitem__).confirmed)
        bad=EvaluationResult(2,3,'repeated_state',4,3,0,3,'repeated_state')
        self.assertFalse(verify_cycle_evidence(start=2, expected=bad, transition=edges.__getitem__).confirmed)
    def test_discovery_artifacts_complete(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); r=EvaluationResult(2,3,'repeated_state',4,2,0,3,'repeated_state')
            paths=write_discovery_artifacts(root,result=r,members=[2,3,4],metadata={'pilot_id':'p','strategy':'s','deterministic_seed':'seed','cell_id':'c','family':'f','generation_parameters':{'a':1},'source_parent':'9','validation_mode':'v'})
            data=json.loads(paths['discovery'].read_text()); self.assertEqual(data['cycle_members'],['2','3','4'])
            md=paths['markdown'].read_text()
            for text in ['2','3','4','first_seen_step','repeated_at_step','cycle_length','independent_replay_confirmed']:
                self.assertIn(text, md)

class AdaptiveTests(unittest.TestCase):
    def prep(self, root):
        (root/'results').mkdir(); (root/'results/global_top_10.json').write_text('[{"starting_integer":"'+str(D+7)+'"}]\n')
    def test_early_stop_no_second_candidate_and_summary(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.prep(root); calls=[]
            class Sent:
                def __iter__(self): return self
                def __next__(self):
                    if calls: raise AssertionError('advanced after discovery')
                    calls.append(1); return CandidateRecord(D+17,S5_STRATEGY,'decimal_suffix',parent=D+7,suffix_digits=1)
            cell=AdaptiveCell('c1','decimal-suffix',S5_STRATEGY,'decimal_suffix',D+7,1,2,{'suffix_digits':1})
            
            with patch('bigcollatz.adaptive.verify_cycle_evidence', return_value=type('V',(),{'confirmed':True,'members':[D+17],'failure_reason':None})()):
                s=run_adaptive_pilot(root,pilot_id='p',cells=[cell],generators={'c1':Sent()},deterministic_seed='seed',evaluator=ev_repeat)
            self.assertEqual(s['candidates_evaluated'],1); self.assertTrue(s['stopped_early']); self.assertEqual(s['stopping_reason'],'verified_nontrivial_cycle')
            self.assertTrue((root/'results/nontrivial_cycle_discovery.json').exists()); self.assertTrue((root/'NONTRIVIAL_CYCLE_FOUND.md').exists()); self.assertTrue((root/'results/cycle_candidates.json').exists())
    def test_failed_verification_no_discovery(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.prep(root)
            with self.assertRaises(RuntimeError): run_adaptive_pilot(root,pilot_id='p',cells=[CELL],generators={'c1':[CandidateRecord(D+17,S5_STRATEGY,'decimal_suffix',parent=D+7,suffix_digits=1)]},deterministic_seed='seed',evaluator=lambda n: type('X',(),{'result':EvaluationResult(n,1,'repeated_state',n,n,0,2,'repeated_state'),'metrics':TrajectoryMetrics(0,0,None,n,n,0,0,65536)})())
            self.assertFalse((root/'results/nontrivial_cycle_discovery.json').exists()); self.assertFalse((root/'NONTRIVIAL_CYCLE_FOUND.md').exists())
    def test_duplicate_across_cells_before_eval_and_isolation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.prep(root); x=D+17; calls=[]
            cells=[CELL, AdaptiveCell('c2','decimal-suffix',S5_STRATEGY,'decimal_suffix',D+7,2,1,{'suffix_digits':1})]
            def ev(n): calls.append(n); return ev_one(n)
            with self.assertRaises(ValueError): run_adaptive_pilot(root,pilot_id='p',cells=cells,generators={'c1':[CandidateRecord(x,S5_STRATEGY,'decimal_suffix',parent=D+7,suffix_digits=1)],'c2':[CandidateRecord(x,S5_STRATEGY,'decimal_suffix',parent=D+7,suffix_digits=1)]},deterministic_seed='seed',evaluator=ev)
            self.assertEqual(len(calls),1)
    def test_metrics_top_tail_score_allocation(self):
        ms=[TrajectoryMetrics(2,.5,4,8,4,1,3,17),TrajectoryMetrics(4,.25,None,9,3,3,5,17)]
        ag=aggregate_metrics(ms); self.assertEqual(ag['undefined_first_descent_count'],1); self.assertEqual(ag['maximum_excursion']['numerator'],'9')
        tail=assign_top_tail([{'cell_id':'A','length':x,'cell_local_order':i} for i,x in enumerate([100,90,80])]+[{'cell_id':'B','length':x,'cell_local_order':i} for i,x in enumerate([70,60,50])], .34)
        self.assertEqual(tail, {'A':3})
        tie=assign_top_tail([{'cell_id':'B','length':100,'cell_local_order':0},{'cell_id':'A','length':100,'cell_local_order':0}], .5); self.assertEqual(tie, {'A':1})
        base={'mean_trajectory_length':100,'p90_trajectory_length':110,'p99_trajectory_length':None,'overall_pilot_top_tail_count':1,'fixed_threshold_exceedance_counts':{'1':2},'recurrence_metric_aggregates':{'mean_repeated_residue_hit_count':1},'repeated_state_count':0}
        self.assertEqual(deterministic_score(base), deterministic_score(base)); self.assertGreater(deterministic_score({**base,'overall_pilot_top_tail_count':2}), deterministic_score(base)); self.assertGreater(deterministic_score({**base,'recurrence_metric_aggregates':{'mean_repeated_residue_hit_count':9}}), deterministic_score(base))
        self.assertGreater(deterministic_score({**base,'mean_trajectory_length':120,'p90_trajectory_length':120}), deterministic_score({**base,'mean_trajectory_length':50,'maximum_trajectory_length':10000}))
        for cells,total in [([{'cell_id':'a','deterministic_score':1}],5),([{'cell_id':'a','deterministic_score':0},{'cell_id':'b','deterministic_score':0}],4),([{'cell_id':'a','deterministic_score':-1},{'cell_id':'b','deterministic_score':2}],5),([{'cell_id':'a','deterministic_score':1},{'cell_id':'b','deterministic_score':1}],2)]:
            self.assertEqual(sum(allocate_stage_b(cells,total).values()), total)
        with self.assertRaises(ValueError): allocate_stage_b([{'cell_id':'a'},{'cell_id':'b'}],1,minimum=1)
