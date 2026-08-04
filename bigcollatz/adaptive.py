"""Two-stage adaptive cross-family Collatz pilot using the shared evaluator."""

from __future__ import annotations

import json, statistics, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .evaluator import EvaluationWithMetrics, collatz_step, evaluate, evaluate_with_metrics
from .experiment import _persist_cycle_candidates, _validate_candidate_record, _percentile
from .generator import (
    CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY, balanced_allocation,
    load_global_top_10, parity_prefix_candidate_records, decimal_suffix_candidate_records,
    residue_candidate_records,
)

CELL_VALIDATION = {"parity_prefix": (S1_STRATEGY, "parity_prefix"), "decimal_suffix": (S5_STRATEGY, "decimal_suffix"), "residue": (S6_STRATEGY, "residue")}
THRESHOLDS = (24000, 26000, 27707)

@dataclass(frozen=True, slots=True)
class AdaptiveCell:
    cell_id: str
    family: str
    source_parent: int
    parent_rank: int
    candidate_count: int
    parameters: dict[str, Any]
    required_validation_mode: str


def default_cells(output_root: Path, count_per_family: int = 2, per_cell: int = 40) -> list[AdaptiveCell]:
    parents = load_global_top_10(output_root / "results" / "global_top_10.json")
    cells: list[AdaptiveCell] = []
    for rank, parent in enumerate(parents[:count_per_family], 1):
        cells.append(AdaptiveCell(f"ap-parity-r{rank}-p256", "parity_prefix", parent, rank, per_cell, {"prefix_length": 256}, "parity_prefix"))
        cells.append(AdaptiveCell(f"ap-suffix-r{rank}-d64", "decimal_suffix", parent, rank, per_cell, {"suffix_digits": 64}, "decimal_suffix"))
        cells.append(AdaptiveCell(f"ap-residue-r{rank}-m2p128p1", "residue", parent, rank, per_cell, {"residue_modulus": 2**128 + 1, "residue": parent % (2**128 + 1)}, "residue"))
    return cells


def _records_for_cell(cell: AdaptiveCell, seed: str) -> Iterable[CandidateRecord]:
    parents = [cell.source_parent]
    if cell.family == "parity_prefix":
        for cand, parent in parity_prefix_candidate_records(cell.candidate_count, parents, seed, cell.parameters["prefix_length"]):
            yield CandidateRecord(cand, S1_STRATEGY, "parity_prefix", parent=parent, prefix_length=cell.parameters["prefix_length"])
    elif cell.family == "decimal_suffix":
        yield from decimal_suffix_candidate_records(cell.candidate_count, parents, seed, cell.parameters["suffix_digits"])
    elif cell.family == "residue":
        yield from residue_candidate_records(cell.candidate_count, parents, seed, cell.parameters["residue_modulus"])
    else:
        raise ValueError(f"unsupported cell family: {cell.family}")


def validate_cell_record(cell: AdaptiveCell, record: CandidateRecord) -> None:
    expected_strategy, expected_mode = CELL_VALIDATION[cell.family]
    if cell.required_validation_mode != expected_mode or record.strategy != expected_strategy or record.validation_mode != expected_mode:
        raise ValueError("cell strategy/validation mismatch")
    if record.parent != cell.source_parent:
        raise ValueError("candidate parent does not match cell source parent")
    _validate_candidate_record(record, expected_strategy)


def _cycle_members(start: int, first: int, repeat_at: int) -> list[str]:
    state = start
    members: list[str] = []
    for step in range(1, repeat_at + 1):
        state = collatz_step(state)
        if step >= first and step < repeat_at:
            members.append(str(state))
    return members


def cycle_evidence(result: Any, *, start: int, pilot_id: str, strategy: str, cell: AdaptiveCell, seed: str, validation_mode: str) -> dict[str, Any]:
    members = _cycle_members(start, result.first_seen_step, result.repeated_at_step)
    return {"starting_integer": str(start), "repeated_integer": result.repeated_integer, "first_seen_step": result.first_seen_step,
            "repeated_at_step": result.repeated_at_step, "cycle_length": result.cycle_length, "cycle_members": members,
            "pilot_id": pilot_id, "strategy": strategy, "cell_id": cell.cell_id, "family": cell.family,
            "deterministic_seed": seed, "cell_parameters": cell.parameters, "parent_starting_integer": str(cell.source_parent),
            "parent_rank": cell.parent_rank, "validation_mode": validation_mode}


def create_nontrivial_cycle_discovery(output_root: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    start = int(evidence["starting_integer"])
    replay = evaluate(start)
    confirmed = replay.outcome == "repeated_state" and replay.repeated_integer == evidence["repeated_integer"] and replay.first_seen_step == evidence["first_seen_step"] and replay.repeated_at_step == evidence["repeated_at_step"] and replay.cycle_length == evidence["cycle_length"] and "1" not in evidence["cycle_members"]
    discovery = dict(evidence, independent_replay_confirmed=confirmed)
    if confirmed:
        path = output_root / "results" / "nontrivial_cycle_discovery.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(discovery, indent=2, sort_keys=True) + "\n")
        (output_root / "NONTRIVIAL_CYCLE_FOUND.md").write_text("\n".join(["# Nontrivial Collatz Cycle Found", "", f"- Starting integer: `{evidence['starting_integer']}`", f"- Repeated integer: `{evidence['repeated_integer']}`", f"- Cycle length: {evidence['cycle_length']}", f"- Strategy: `{evidence['strategy']}`", f"- Cell: `{evidence['cell_id']}`", f"- Pilot: `{evidence['pilot_id']}`", f"- Independent replay confirmed: {confirmed}", "", "## Exact ordered cycle", "", "```text", *evidence["cycle_members"], "```", ""]))
    return discovery


def score_cell(summary: dict[str, Any]) -> float:
    # Signals are on comparable count/step scales: p90 and p99 reward robust tails;
    # threshold and top-tail counts reward repeatable exceedances; residue hits are a small heuristic tiebreaker.
    return (summary.get("p90_trajectory_length") or 0) + 0.5 * (summary.get("p99_trajectory_length") or 0) + 200 * sum(summary["threshold_exceedance_counts"].values()) + 100 * summary["overall_pilot_top_tail_count"] + 0.02 * summary["recurrence_metric_aggregates"]["mean_repeated_residue_hit_count"] + 10000 * summary["repeated_state_count"]


def run_adaptive_pilot(output_root: Path, *, pilot_id: str, stage: str, seed: str, cells: list[AdaptiveCell], evaluator: Callable[..., EvaluationWithMetrics] = evaluate_with_metrics) -> dict[str, Any]:
    seen_candidates: set[int] = set(); all_lengths: list[int] = []; cell_summaries = []; cycles=[]
    started_all = time.perf_counter_ns()
    for cell in cells:
        lengths=[]; maxes=[]; odd=[]; density=[]; descent=[]; excursion=[]; residues=[]; sameband=[]; outcomes={"reached_one":0,"repeated_state":0,"interrupted":0}
        started = time.perf_counter_ns(); top_tail_cut = 26000
        for record in _records_for_cell(cell, seed + ":" + cell.cell_id):
            validate_cell_record(cell, record)
            if len(str(record.candidate)) != 1000 or record.candidate in seen_candidates:
                raise ValueError("adaptive candidate uniqueness or digit invariant failed")
            seen_candidates.add(record.candidate)
            evaluated = evaluator(record.candidate)
            result, metrics = evaluated.result, evaluated.metrics
            outcomes[result.outcome]+=1
            if result.outcome == "repeated_state":
                ev = cycle_evidence(result, start=record.candidate, pilot_id=pilot_id, strategy=record.strategy, cell=cell, seed=seed, validation_mode=record.validation_mode)
                cycles.append(ev); create_nontrivial_cycle_discovery(output_root, ev)
            if result.outcome in ("reached_one","repeated_state"):
                lengths.append(result.total_steps_executed); all_lengths.append(result.total_steps_executed); maxes.append(result.maximum_integer)
                odd.append(metrics.odd_step_count); density.append(metrics.odd_step_density); excursion.append(metrics.maximum_excursion_ratio); residues.append(metrics.repeated_residue_hit_count); sameband.append(metrics.same_decimal_digit_band_return_count)
                if metrics.first_descent_step is not None: descent.append(metrics.first_descent_step)
        elapsed=(time.perf_counter_ns()-started)/1e9
        summary={"cell_id":cell.cell_id,"family":cell.family,"source_parent":str(cell.source_parent),"parent_rank":cell.parent_rank,"parameters":cell.parameters,"required_validation_mode":cell.required_validation_mode,"candidates_evaluated":cell.candidate_count,**{k+"_count":v for k,v in outcomes.items()},"mean_trajectory_length":statistics.fmean(lengths) if lengths else None,"median_trajectory_length":statistics.median(lengths) if lengths else None,"p90_trajectory_length":_percentile(lengths,.90) if lengths else None,"p99_trajectory_length":_percentile(lengths,.99) if len(lengths)>=10 else None,"maximum_trajectory_length":max(lengths) if lengths else None,"maximum_integer_reached":str(max(maxes)) if maxes else None,"runtime_seconds":elapsed,"trajectories_per_second":cell.candidate_count/elapsed,"threshold_exceedance_counts":{str(t):sum(1 for x in lengths if x>=t) for t in THRESHOLDS},"overall_pilot_top_tail_count":sum(1 for x in lengths if x>=top_tail_cut),"recurrence_metric_aggregates":{"mean_odd_step_count":statistics.fmean(odd) if odd else None,"mean_odd_step_density":statistics.fmean(density) if density else None,"mean_first_descent_step":statistics.fmean(descent) if descent else None,"mean_maximum_excursion_ratio":statistics.fmean(excursion) if excursion else None,"mean_same_decimal_digit_band_return_count":statistics.fmean(sameband) if sameband else None,"residue_modulus":65537,"mean_repeated_residue_hit_count":statistics.fmean(residues) if residues else 0},}
        summary["cell_score"] = score_cell(summary); cell_summaries.append(summary)
    selected = select_cells(cell_summaries, limit=min(3, len(cell_summaries)))
    result={"pilot_id":pilot_id,"stage":stage,"seed":seed,"candidate_count":sum(c.candidate_count for c in cells),"distinct_candidate_count":len(seen_candidates),"decimal_digits":1000,"cell_summaries":cell_summaries,"selected_cell_ids":selected,"scoring_rule":"p90 + 0.5*p99 + 200*threshold_exceedances + 100*top_tail_count + 0.02*mean_repeated_residue_hit_count + 10000*repeated_state_count; ties by score desc, family, parent_rank, cell_id; selection keeps best unseen families first, then score.","repeated_state_count":len(cycles),"cycle_evidence":cycles,"total_wall_time_seconds":(time.perf_counter_ns()-started_all)/1e9}
    out=output_root/"results"/pilot_id; out.mkdir(parents=True, exist_ok=True); (out/"summary.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    _persist_cycle_candidates(output_root, [{k:v for k,v in c.items() if k!="cycle_members"} for c in cycles])
    return result


def select_cells(cell_summaries: list[dict[str, Any]], limit: int) -> list[str]:
    ordered=sorted(cell_summaries, key=lambda s:(-s["cell_score"], s["family"], s["parent_rank"], s["cell_id"]))
    picked=[]; families=set()
    for s in ordered:
        if len(picked)<limit and s["family"] not in families:
            picked.append(s["cell_id"]); families.add(s["family"])
    for s in ordered:
        if len(picked)>=limit: break
        if s["cell_id"] not in picked: picked.append(s["cell_id"])
    return picked


def allocate_stage_b(stage_a: dict[str, Any], output_root: Path, total_count: int = 360) -> list[AdaptiveCell]:
    by_id={s["cell_id"]:s for s in stage_a["cell_summaries"]}
    selected=[by_id[cid] for cid in stage_a["selected_cell_ids"]]
    raw=[max(1.0, s["cell_score"]) for s in selected]; alloc=balanced_allocation(total_count, selected) if sum(raw)==0 else [max(40, int(total_count*r/sum(raw))) for r in raw]
    alloc[-1]+= total_count-sum(alloc)
    cells=[]
    for s,n in zip(selected, alloc):
        cells.append(AdaptiveCell(s["cell_id"]+"-b", s["family"], int(s["source_parent"]), s["parent_rank"], n, s["parameters"], s["required_validation_mode"]))
    return cells
