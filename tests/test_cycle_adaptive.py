import json, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch
from bigcollatz.evaluator import evaluate, evaluate_with_metrics, RecurrenceMetrics, MetricEvaluation
from bigcollatz.model import EvaluationResult
from bigcollatz.cycle import reconstruct_cycle, verify_cycle_independently
from bigcollatz.adaptive import *
from bigcollatz.generator import CandidateRecord, S1_STRATEGY

A,B,C,P,Q=101,202,303,11,22
EDGES={A:B,B:C,C:A,P:Q,Q:A}
def tr(n): return EDGES[n]

class EngineCycleTests(unittest.TestCase):
 def assert_agree(self,start,**kw):
  r=evaluate(start,**kw); m=evaluate_with_metrics(start,**kw).result
  self.assertEqual((r.outcome,r.total_steps_executed,r.maximum_integer,r.repeated_integer,r.first_seen_step,r.repeated_at_step,r.cycle_length),(m.outcome,m.total_steps_executed,m.maximum_integer,m.repeated_integer,m.first_seen_step,m.repeated_at_step,m.cycle_length))
 def test_evaluation_agreement_reached_interrupted_repeated(self):
  self.assert_agree(7); self.assert_agree(27,max_steps=10); self.assert_agree(A,transition=tr)
 def test_cycle_matrix(self):
  r=evaluate(A,transition=tr); self.assertEqual((r.first_seen_step,r.repeated_at_step,r.cycle_length),(0,3,3)); self.assertEqual(reconstruct_cycle(A,r,transition=tr),[A,B,C])
  r=evaluate(P,transition=tr); self.assertEqual(reconstruct_cycle(P,r,transition=tr),[A,B,C])
  r=evaluate(A,transition=lambda n:n); self.assertEqual(reconstruct_cycle(A,r,transition=lambda n:n),[A])
 def test_trivial_and_tamper_failures(self):
  r=evaluate(1); self.assertEqual(r.outcome,'reached_one')
  rr=evaluate(1,transition=lambda n:n); self.assertFalse(verify_cycle_independently(1,rr,[1],transition=lambda n:n).confirmed)
  r=evaluate(A,transition=tr)
  for members in ([A,999,C],[B,C,A],[B,C],[A,B],[A,B,999]): self.assertFalse(verify_cycle_independently(A,r,members,transition=tr).confirmed)
  bad=EvaluationResult(A,3,'repeated_state',C,999,0,3,'repeated_state')
  self.assertFalse(verify_cycle_independently(A,bad,[A,B,C],transition=tr).confirmed)

class AdaptiveUnitTests(unittest.TestCase):
 def metric(self,steps,odd=2,dens=.5,fd=1,exc=2,band=3,hits=4):
  return MetricEvaluation(EvaluationResult(10**999,steps,'reached_one',10**999+1),RecurrenceMetrics(odd,dens,fd,exc,1,band,hits,1024))
 def test_metric_aggregation_known_values(self):
  agg=aggregate_metrics([RecurrenceMetrics(2,.2,4,3,1,6,8,17),RecurrenceMetrics(4,.4,None,5,1,8,10,17)])
  self.assertEqual(agg['mean_odd_step_count'],3); self.assertEqual(agg['mean_odd_step_density'],.30000000000000004); self.assertEqual(agg['mean_first_descent_step'],4); self.assertEqual(agg['undefined_first_descent_count'],1); self.assertEqual(agg['mean_repeated_residue_hit_count'],9)
 def test_top_tail_and_ties(self):
  self.assertEqual(assign_top_tail({'A':[100,90,80],'B':[70,60,50]},fraction=.34),{'A':3,'B':0})
  self.assertEqual(sum(assign_top_tail({'A':[100,90],'B':[90,80]},fraction=.5).values()),2)
 def test_score_and_allocation(self):
  s={'mean_trajectory_length':100,'p90_trajectory_length':120,'p99_trajectory_length':130,'overall_top_tail_count':1,'repeated_state_count':0,'recurrence_metric_aggregates':{'mean_repeated_residue_hit_count':2,'mean_odd_step_density':.5}}
  self.assertEqual(score_cell(s),score_cell(dict(s)))
  s2=json.loads(json.dumps(s)); s2['overall_top_tail_count']=2; self.assertGreater(score_cell(s2),score_cell(s))
  s3=json.loads(json.dumps(s)); s3['recurrence_metric_aggregates']['mean_repeated_residue_hit_count']=9; self.assertGreater(score_cell(s3),score_cell(s))
  robust={'mean_trajectory_length':150,'p90_trajectory_length':150,'p99_trajectory_length':150,'overall_top_tail_count':0,'recurrence_metric_aggregates':{}}
  lucky={'mean_trajectory_length':10,'p90_trajectory_length':10,'p99_trajectory_length':10,'overall_top_tail_count':0,'recurrence_metric_aggregates':{}}
  self.assertGreater(score_cell(robust),score_cell(lucky))
  self.assertEqual(sum(allocate_stage_b([('a',1),('b',1)],5).values()),5)
  self.assertEqual(allocate_stage_b([('a',0),('b',0)],4),{'a':2,'b':2})
  self.assertEqual(allocate_stage_b([('a',-1),('b',2)],5)['b'],4)
  self.assertEqual(allocate_stage_b([('a',3)],3),{'a':3})
  self.assertEqual(allocate_stage_b([('a',1),('b',2)],2),{'a':1,'b':1})
  with self.assertRaises(ValueError): allocate_stage_b([('a',1),('b',1)],1)
 def test_global_duplicate_rejected_after_one_evaluation(self):
  parent=10**999+123; c=AdaptiveCell('c1','parity-prefix',S1_STRATEGY,'parity_prefix',parent,1,1,{'prefix_length':1}); d=AdaptiveCell('c2','parity-prefix',S1_STRATEGY,'parity_prefix',parent,1,1,{'prefix_length':1})
  rec=CandidateRecord(10**999,S1_STRATEGY,'parity_prefix',parent=parent,prefix_length=1)
  with tempfile.TemporaryDirectory() as td, patch('bigcollatz.adaptive.records_for_cell',side_effect=[iter([rec]),iter([rec])]), patch('bigcollatz.adaptive._validate_candidate_record'):
   root=Path(td); (root/'results').mkdir(); (root/'results/global_top_10.json').write_text('[]')
   ev=Mock(return_value=self.metric(5))
   with self.assertRaises(ValueError): run_adaptive_pilot(root,pilot_id='p',cells=[c,d],seed='s',evaluator=ev)
   self.assertEqual(ev.call_count,1)
 def test_repeated_state_end_to_end_and_trivial_path_and_shared_evaluator(self):
  parent=10**999+123; cell=AdaptiveCell('c','parity-prefix',S1_STRATEGY,'parity_prefix',parent,1,2,{'prefix_length':1})
  AA=10**999+101; BB=10**999+202; CC=10**999+303; edges={AA:BB,BB:CC,CC:AA}
  nontriv=CandidateRecord(AA,S1_STRATEGY,'parity_prefix',parent=parent,prefix_length=1); sentinel=CandidateRecord(10**999,S1_STRATEGY,'parity_prefix',parent=parent,prefix_length=1)
  def ev(x): return evaluate_with_metrics(x,transition=lambda n: edges[n]) if x==AA else self.metric(9)
  with tempfile.TemporaryDirectory() as td, patch('bigcollatz.adaptive.records_for_cell',return_value=iter([nontriv,sentinel])), patch('bigcollatz.adaptive._validate_candidate_record'), patch('bigcollatz.adaptive.reconstruct_cycle',return_value=[AA,BB,CC]), patch('bigcollatz.adaptive.verify_cycle_independently',return_value=__import__('bigcollatz.cycle').cycle.CycleVerification(True,[AA,BB,CC])):
   root=Path(td); (root/'results').mkdir(); (root/'results/global_top_10.json').write_text('[]')
   with self.assertRaises(NontrivialCycleFound): run_adaptive_pilot(root,pilot_id='p',cells=[cell],seed='s',evaluator=ev)
   self.assertTrue((root/'results/nontrivial_cycle_discovery.json').exists()); self.assertTrue((root/'NONTRIVIAL_CYCLE_FOUND.md').exists())
  triv=CandidateRecord(10**999,S1_STRATEGY,'parity_prefix',parent=parent,prefix_length=1)
  with tempfile.TemporaryDirectory() as td, patch('bigcollatz.adaptive.records_for_cell',return_value=iter([triv])), patch('bigcollatz.adaptive._validate_candidate_record'):
   root=Path(td); (root/'results').mkdir(); (root/'results/global_top_10.json').write_text('[]')
   run_adaptive_pilot(root,pilot_id='p',cells=[cell],seed='s',evaluator=lambda x: MetricEvaluation(EvaluationResult(x,1,'repeated_state',x,1,0,1,'repeated_state',repeated_integer='1',first_seen_step=0,repeated_at_step=1,cycle_length=1), RecurrenceMetrics(0,0.0,None,x,x,0,0,1024)))
   self.assertFalse((root/'results/nontrivial_cycle_discovery.json').exists()); self.assertFalse((root/'NONTRIVIAL_CYCLE_FOUND.md').exists())
  mock=Mock(return_value=self.metric(1))
  with tempfile.TemporaryDirectory() as td, patch('bigcollatz.adaptive.records_for_cell',return_value=iter([sentinel])), patch('bigcollatz.adaptive._validate_candidate_record'):
   root=Path(td); (root/'results').mkdir(); (root/'results/global_top_10.json').write_text('[]')
   run_adaptive_pilot(root,pilot_id='p',cells=[cell],seed='s',evaluator=mock); mock.assert_called_once_with(sentinel.candidate)
if __name__=='__main__': unittest.main()
