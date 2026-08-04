import json, shutil
from pathlib import Path

import pytest

from bigcollatz.adaptive import AdaptiveCell, VerifiedCycleFound, allocate_stage_b, deterministic_score, run_adaptive_pilot, validate_cell_candidate
from bigcollatz.cycle import evidence_from_result, reconstruct_cycle_members, verify_cycle_evidence
from bigcollatz.evaluator import evaluate, evaluate_with_metrics
from bigcollatz.generator import CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY


def t(mapping): return lambda n: mapping[n]


def test_metric_and_normal_evaluation_agree_reached_interrupted_and_repeat():
    for kwargs in [{"start": 7}, {"start": 7, "max_steps": 3}, {"start": 10, "transition": t({10:11,11:12,12:10})}]:
        normal = evaluate(**kwargs)
        metric, _ = evaluate_with_metrics(**kwargs)
        assert (normal.outcome, normal.total_steps_executed, normal.maximum_integer, normal.repeated_integer, normal.first_seen_step, normal.repeated_at_step, normal.cycle_length) == (metric.outcome, metric.total_steps_executed, metric.maximum_integer, metric.repeated_integer, metric.first_seen_step, metric.repeated_at_step, metric.cycle_length)


def test_cycle_a_starts_at_starting_integer():
    trans=t({10:11,11:12,12:10})
    result=evaluate(10, transition=trans)
    assert (result.first_seen_step,result.repeated_at_step,result.cycle_length)==(0,3,3)
    assert reconstruct_cycle_members(10,0,3,transition=trans)==[10,11,12]


def test_cycle_b_transient_prefix_excluded():
    trans=t({1_000:1_001,1_001:10,10:11,11:12,12:10})
    result=evaluate(1_000, transition=trans)
    assert result.first_seen_step == 2
    assert reconstruct_cycle_members(1_000,2,5,transition=trans)==[10,11,12]


def test_cycle_c_self_loop():
    trans=lambda n:n
    result=evaluate(99, transition=trans)
    assert (result.first_seen_step,result.repeated_at_step,result.cycle_length)==(0,1,1)
    assert reconstruct_cycle_members(99,0,1,transition=trans)==[99]


def good_evidence(trans=t({10:11,11:12,12:10})):
    return evidence_from_result(result=evaluate(10, transition=trans), pilot_id="p", strategy="s", deterministic_seed="seed", transition=trans), trans


def test_cycle_d_trivial_collatz_rejected_by_replay():
    result=evaluate(1)
    ev={"starting_integer":"1","repeated_integer":"1","first_seen_step":0,"repeated_at_step":3,"cycle_length":3,"cycle_members":["1","4","2"]}
    assert reconstruct_cycle_members(1,0,3)==[1,4,2]
    assert verify_cycle_evidence(ev)[0] is False


def test_cycle_e_tampered_members_fail():
    ev, trans=good_evidence(); ev["cycle_members"][1]="999"
    assert verify_cycle_evidence(ev, transition=trans)[0] is False


def test_cycle_f_wrong_order_fails():
    ev, trans=good_evidence(); ev["cycle_members"]=["11","12","10"]
    assert verify_cycle_evidence(ev, transition=trans)[0] is False


def test_cycle_g_missing_first_member_fails():
    ev, trans=good_evidence(); ev["cycle_members"]=["11","12"]
    assert verify_cycle_evidence(ev, transition=trans)[0] is False


def test_cycle_h_i_j_wrong_scalars_and_broken_closure_fail():
    ev, trans=good_evidence(); ev["cycle_length"]=2
    assert verify_cycle_evidence(ev, transition=trans)[0] is False
    ev, trans=good_evidence(); ev["repeated_integer"]="11"
    assert verify_cycle_evidence(ev, transition=trans)[0] is False
    ev, trans=good_evidence(); ev["cycle_members"]=["10","11","13"]
    assert verify_cycle_evidence(ev, transition=trans)[0] is False


def test_strategy_bound_mismatches_and_digit_duplicate_rejection():
    cell=AdaptiveCell("c","decimal-suffix",S5_STRATEGY,"decimal_suffix",{"suffix_digits":1},source_parent=21)
    validate_cell_candidate(cell, CandidateRecord(10**999+1,S5_STRATEGY,"decimal_suffix",parent=21,suffix_digits=1), set())
    with pytest.raises(ValueError): validate_cell_candidate(cell, CandidateRecord(10**999+1,S6_STRATEGY,"residue",residue_modulus=3,residue=1), set())
    with pytest.raises(ValueError): validate_cell_candidate(cell, CandidateRecord(123,S5_STRATEGY,"decimal_suffix",parent=21,suffix_digits=1), set())
    seen=set(); rec=CandidateRecord(10**999+1,S5_STRATEGY,"decimal_suffix",parent=21,suffix_digits=1); validate_cell_candidate(cell,rec,seen)
    with pytest.raises(ValueError): validate_cell_candidate(cell,rec,seen)
    bad_cell=AdaptiveCell("c","residue",S5_STRATEGY,"decimal_suffix",{},None)
    with pytest.raises(ValueError): validate_cell_candidate(bad_cell, rec, set())


def test_stage_b_allocation_edges_and_score_determinism():
    s1={"mean":10,"p90":20,"p99":30,"overall_pilot_top_tail_count":1}; s2={"mean":1,"p90":2,"p99":3,"overall_pilot_top_tail_count":0}
    assert deterministic_score(s1) > deterministic_score(s2)
    alloc=allocate_stage_b(7, [("b", 1.0), ("a", 3.0), ("c", 0.0)])
    assert sum(alloc.values()) == 7 and all(v > 0 for v in alloc.values())
    assert alloc == allocate_stage_b(7, [("b", 1.0), ("a", 3.0), ("c", 0.0)])
    with pytest.raises(ValueError): allocate_stage_b(2, [("a", 1), ("b", 1), ("c", 1)])


def prep_root(tmp_path):
    root=tmp_path; (root/"results").mkdir(); shutil.copy(Path("results/global_top_10.json"), root/"results/global_top_10.json"); return root


def test_adaptive_repeated_state_integration_and_early_stop(tmp_path, monkeypatch):
    root=prep_root(tmp_path); calls=[]; trans=t({10**999+1:10**999+2,10**999+2:10**999+3,10**999+3:10**999+1})
    cell=AdaptiveCell("c","decimal-suffix",S5_STRATEGY,"decimal_suffix",{"suffix_digits":1},source_parent=10**999+1)
    def source(_):
        yield CandidateRecord(10**999+1,S5_STRATEGY,"decimal_suffix",parent=10**999+1,suffix_digits=1)
        raise AssertionError("later candidate evaluated")
    def evaluator(n): calls.append(n); return evaluate_with_metrics(n, transition=trans)
    with pytest.raises(VerifiedCycleFound): run_adaptive_pilot(root,pilot_id="p",cells=[cell],candidate_source=source,seed="seed",evaluator=evaluator,transition=trans)
    assert calls == [10**999+1]
    assert (root/"results/cycle_candidates.json").exists()
    assert (root/"results/nontrivial_cycle_discovery.json").exists()
    assert (root/"NONTRIVIAL_CYCLE_FOUND.md").exists()


def test_adaptive_trivial_cycle_integration_no_discovery(tmp_path):
    root=prep_root(tmp_path); cell=AdaptiveCell("c","decimal-suffix",S5_STRATEGY,"decimal_suffix",{"suffix_digits":1},source_parent=10**999+1)
    def source(_): yield CandidateRecord(10**999+1,S5_STRATEGY,"decimal_suffix",parent=10**999+1,suffix_digits=1)
    # A normal trivial Collatz trajectory is not a repeated-state discovery.
    def evaluator(n): return evaluate_with_metrics(1)
    summary=run_adaptive_pilot(root,pilot_id="p",cells=[cell],candidate_source=source,seed="seed",evaluator=evaluator)
    assert summary["repeated_state_failures"] == []
    assert not (root/"results/nontrivial_cycle_discovery.json").exists()
    assert not (root/"NONTRIVIAL_CYCLE_FOUND.md").exists()


def test_adaptive_uses_injected_shared_evaluator_and_preserves_global(tmp_path):
    root=prep_root(tmp_path); before=(root/"results/global_top_10.json").read_text(); called=[]
    cell=AdaptiveCell("c","decimal-suffix",S5_STRATEGY,"decimal_suffix",{"suffix_digits":1},source_parent=21)
    def source(_): yield CandidateRecord(10**999+1,S5_STRATEGY,"decimal_suffix",parent=21,suffix_digits=1)
    def evaluator(n): called.append(n); return evaluate_with_metrics(7)
    summary=run_adaptive_pilot(root,pilot_id="p",cells=[cell],candidate_source=source,seed="seed",evaluator=evaluator)
    assert called == [10**999+1] and summary["candidates_evaluated"] == 1
    assert (root/"results/global_top_10.json").read_text() == before
