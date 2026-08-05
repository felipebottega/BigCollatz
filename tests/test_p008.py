import json, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock

from bigcollatz.adaptive import rank_trajectories, run_adaptive_pilot
from bigcollatz.evaluator import EvaluationMetrics
from bigcollatz.generator import CandidateRecord, S5_STRATEGY
from bigcollatz.model import EvaluationResult
from bigcollatz.p008 import (
    CANDIDATES_PER_CELL, DETERMINISTIC_SEED, REQUESTED_CANDIDATES,
    build_p008_cells, build_p008_generators, load_p007_candidates,
)
from bigcollatz.p007 import build_p007_cells, build_p007_generators

P1=int('1'+'0'*999); P2=int('2'+'0'*999)

def write_global(root):
    p=root/'results'/'global_top_10.json'; p.parent.mkdir(parents=True, exist_ok=True)
    rec=[{'starting_integer':str(P1)},{'starting_integer':str(P2)}]
    for i, d in enumerate('3456789'):
        rec.append({'starting_integer': d + str(i) * 999})
    rec.append({'starting_integer':'9' + '8' * 999})
    p.write_text(json.dumps(rec)+'\n'); return p

def write_p007_artifacts(root):
    (root/'results'/'p007-adaptive-stage-a-300').mkdir(parents=True, exist_ok=True)
    (root/'results'/'p007-adaptive-stage-a-300'/'design.json').write_text(json.dumps({'pilot_id':'p007-adaptive-stage-a-300'})+'\n')
    (root/'results'/'p007-adaptive-stage-a-300'/'summary.json').write_text(json.dumps({'candidates_evaluated':300})+'\n')

class P008Tests(unittest.TestCase):
    def test_design_exact_bindings_and_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); gp=write_global(root)
            a=build_p008_cells(gp); b=build_p008_cells(gp)
        self.assertEqual(a,b); self.assertEqual(len(a),4)
        self.assertEqual(sum(c.candidate_count for c in a), REQUESTED_CANDIDATES)
        self.assertTrue(all(c.candidate_count == CANDIDATES_PER_CELL for c in a))
        self.assertEqual([(c.family,c.parent_rank,c.parameters) for c in a], [
            ('decimal-suffix',2,{'suffix_digits':64}),
            ('parity-prefix',2,{'prefix_length':256}),
            ('parity-prefix',2,{'prefix_length':128}),
            ('residue',1,{'residue_modulus':2**128+1}),
        ])

    def test_p007_exclusion_reconstructs_300_and_rejects_before_eval(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); gp=write_global(root); write_p007_artifacts(root)
            p007=load_p007_candidates(root)
            self.assertEqual(len(p007),300)
            cells=build_p008_cells(gp)
            first=next(iter(build_p007_generators(build_p007_cells(gp))[build_p007_cells(gp)[0].cell_id]))
            gens=build_p008_generators(cells, {first.candidate})
            # Direct wrapper rejection is covered by forcing a P007 record through adaptive validation path.
            ev=Mock(return_value=(EvaluationResult(first.candidate,1,'reached_one',first.candidate), EvaluationMetrics(0,(0,1),1,1,1,0,0,1024)))
            bad_cell=cells[0]
            bad=CandidateRecord(first.candidate, bad_cell.strategy, bad_cell.validation_mode, parent=bad_cell.source_parent, suffix_digits=64)
            with self.assertRaises(ValueError):
                run_adaptive_pilot(root,pilot_id='p008-test',deterministic_seed=DETERMINISTIC_SEED,cells=[bad_cell],generators={bad_cell.cell_id:[bad]},evaluator=ev)
            self.assertEqual(ev.call_count,0)

    def test_top40_decimal_posix_and_threshold_27707(self):
        trajectories=[]
        for i in range(45):
            trajectories.append({'starting_integer':str(10**999+i),'trajectory_length':27707 if i==44 else i,'maximum_integer':str(10**1000+i),'cell_id':'c','family':'f','strategy':'s','source_parent':str(P1),'parent_rank':1,'generation_parameters':{'x':1},'validation_mode':'v','deterministic_seed':DETERMINISTIC_SEED,'candidate_order_within_cell':i})
        ranked=rank_trajectories(trajectories,40)
        self.assertEqual(len(ranked),40); self.assertIsInstance(ranked[0]['starting_integer'],str); self.assertGreaterEqual(ranked[0]['trajectory_length'],27707)

if __name__ == '__main__': unittest.main()
