import json, tempfile, unittest
from pathlib import Path
from bigcollatz.cycle import reconstruct_cycle, verify_cycle_members, verify_nontrivial_cycle, write_discovery_artifacts, CycleVerification
from unittest.mock import patch
from bigcollatz.model import EvaluationResult

class CycleTests(unittest.TestCase):
    def test_reconstruct_variants_and_failures(self):
        edges={9:10,10:11,11:12,12:10}
        r=EvaluationResult(9,4,"repeated_state",12,10,1,3,"repeated_state")
        self.assertEqual(reconstruct_cycle(9,r,transition=edges.__getitem__),[10,11,12])
        verify_cycle_members([10,11,12],r,transition=edges.__getitem__)
        for members,msg in [([11,12,10],"order"),([11,12],"first"),([10,11],"count"),([10,11,13],"order")]:
            with self.subTest(msg=msg), self.assertRaises(ValueError): verify_cycle_members(members,r,transition=edges.__getitem__)
        rr=EvaluationResult(7,1,"repeated_state",7,7,0,1,"repeated_state")
        self.assertEqual(reconstruct_cycle(7,rr,transition=lambda _:7),[7])
        with self.assertRaises(ValueError): verify_cycle_members([1],EvaluationResult(1,1,"repeated_state",1,1,0,1,"repeated_state"),transition=lambda _:1)

    def test_independent_verification_and_artifacts(self):
        edges={9:10,10:11,11:12,12:10}
        r=EvaluationResult(9,4,"repeated_state",12,10,1,3,"repeated_state")
        v=verify_nontrivial_cycle(9,r,["10","11","12"],transition=edges.__getitem__)
        self.assertTrue(v.confirmed)
        self.assertEqual(v.members,[10,11,12])
        self.assertFalse(verify_nontrivial_cycle(9,r,["010","11","12"],transition=edges.__getitem__).confirmed)
        with tempfile.TemporaryDirectory() as d:
            # use a self-loop so default independent replay can confirm artifacts
            rr=EvaluationResult(7,1,"repeated_state",7,7,0,1,"repeated_state")
            with patch("bigcollatz.cycle.verify_nontrivial_cycle", return_value=CycleVerification(True,[7],None)):
                paths=write_discovery_artifacts(Path(d),starting_integer=7,result=rr,cycle_members=[7],pilot_id="p",strategy="s",deterministic_seed="seed",cell_id="c",family="f",generation_parameters={"x":1},source_metadata={"m":2},validation_mode="v")
            payload=json.loads((Path(d)/paths["discovery_json"]).read_text())
            self.assertTrue(payload["independent_replay_confirmed"])
            self.assertIn("7", (Path(d)/paths["discovery_markdown"]).read_text())
