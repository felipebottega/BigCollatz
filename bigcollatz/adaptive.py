"""Correctness-first adaptive cross-family pilot runner."""
from __future__ import annotations

import json, math, statistics, time
from fractions import Fraction
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .cycle import verify_cycle_evidence, write_discovery_artifacts
from .evaluator import evaluate_with_metrics
from .experiment import _persist_cycle_candidates, _cycle_candidate_record, _percentile
from .generator import CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY, validate_decimal_suffix, validate_parity_prefix, validate_residue

FAMILY_RULES = {
    "parity-prefix": (S1_STRATEGY, "parity_prefix"),
    "decimal-suffix": (S5_STRATEGY, "decimal_suffix"),
    "residue": (S6_STRATEGY, "residue"),
}
THRESHOLDS = (24000, 25000, 26000, 27000)

@dataclass(frozen=True)
class AdaptiveCell:
    cell_id: str; family: str; strategy: str; validation_mode: str
    source_parent: int; parent_rank: int; candidate_count: int; parameters: dict[str, Any]

def validate_cell(cell: AdaptiveCell) -> None:
    if cell.family not in FAMILY_RULES: raise ValueError("unknown family")
    if (cell.strategy, cell.validation_mode) != FAMILY_RULES[cell.family]: raise ValueError("wrong strategy or validation mode")
    if not cell.cell_id or cell.source_parent <= 0 or cell.parent_rank < 1 or cell.candidate_count < 1: raise ValueError("missing metadata or invalid parent rank")
    if not isinstance(cell.parameters, dict): raise ValueError("malformed parameters")
    if cell.family == "parity-prefix" and cell.parameters.get("prefix_length", 0) < 1: raise ValueError("malformed parameters")
    if cell.family == "decimal-suffix" and cell.parameters.get("suffix_digits", 0) < 1: raise ValueError("malformed parameters")
    if cell.family == "residue" and cell.parameters.get("residue_modulus", 0) < 2: raise ValueError("malformed parameters")

def validate_candidate_for_cell(record: CandidateRecord, cell: AdaptiveCell, seen: set[int]) -> None:
    validate_cell(cell)
    if record.strategy != cell.strategy or record.validation_mode != cell.validation_mode: raise ValueError("candidate strategy-bound validation mismatch")
    if record.parent != cell.source_parent: raise ValueError("incorrect source parent")
    if len(str(record.candidate)) != 1000: raise ValueError("candidate not exactly 1,000 decimal digits")
    if record.candidate in seen: raise ValueError("duplicate candidate")
    if cell.family == "parity-prefix" and not validate_parity_prefix(record.candidate, cell.source_parent, int(cell.parameters["prefix_length"])): raise ValueError("invalid generated candidate invariant")
    if cell.family == "decimal-suffix" and not validate_decimal_suffix(record.candidate, cell.source_parent, int(cell.parameters["suffix_digits"])): raise ValueError("invalid generated candidate invariant")
    if cell.family == "residue" and not validate_residue(record.candidate, int(cell.parameters["residue_modulus"]), record.residue if record.residue is not None else cell.source_parent % int(cell.parameters["residue_modulus"])): raise ValueError("invalid generated candidate invariant")

def aggregate_metrics(metrics: list[Any]) -> dict[str, Any]:
    defined = [m.first_descent_step for m in metrics if m.first_descent_step is not None]
    max_m = max(metrics, key=lambda m: Fraction(m.maximum_excursion_numerator, m.maximum_excursion_denominator)) if metrics else None
    return {
        "mean_odd_step_count": statistics.fmean(m.odd_step_count for m in metrics) if metrics else None,
        "mean_odd_step_density": statistics.fmean(m.odd_step_density for m in metrics) if metrics else None,
        "mean_first_descent_step": statistics.fmean(defined) if defined else None,
        "undefined_first_descent_count": len(metrics) - len(defined),
        "maximum_excursion": None if max_m is None else {"numerator": str(max_m.maximum_excursion_numerator), "denominator": str(max_m.maximum_excursion_denominator)},
        "mean_same_decimal_digit_band_return_count": statistics.fmean(m.same_decimal_digit_band_return_count for m in metrics) if metrics else None,
        "mean_repeated_residue_hit_count": statistics.fmean(m.repeated_residue_hit_count for m in metrics) if metrics else None,
        "residue_modulus": metrics[0].residue_modulus if metrics else None,
    }

def assign_top_tail(entries: list[dict[str, Any]], fraction: float = .10) -> dict[str, int]:
    n = math.ceil(len(entries) * fraction) if entries else 0
    selected = sorted(entries, key=lambda e: (-e["length"], e["cell_id"], e["cell_local_order"]))[:n]
    counts: dict[str, int] = {}
    for e in selected: counts[e["cell_id"]] = counts.get(e["cell_id"], 0) + 1
    return counts

def deterministic_score(summary: dict[str, Any]) -> float:
    p99 = summary.get("p99_trajectory_length") or summary.get("p90_trajectory_length") or 0
    m = summary.get("recurrence_metric_aggregates") or {}
    return (0.45*(summary.get("mean_trajectory_length") or 0) + 0.25*(summary.get("p90_trajectory_length") or 0) +
            0.15*p99 + 25*(summary.get("overall_pilot_top_tail_count") or 0) +
            10*sum(summary.get("fixed_threshold_exceedance_counts", {}).values()) +
            5*(m.get("mean_repeated_residue_hit_count") or 0) + 20*(summary.get("repeated_state_count") or 0))

def allocate_stage_b(cells: list[dict[str, Any]], total: int, minimum: int = 1) -> dict[str, int]:
    if total < 1 or not cells: raise ValueError("allocation requires positive total and cells")
    if total < minimum * len(cells): raise ValueError("minimum quotas infeasible")
    base = {c["cell_id"]: minimum for c in cells}; remaining = total - minimum*len(cells)
    scores = [max(0.0, float(c.get("deterministic_score", 0))) for c in cells]
    if sum(scores) == 0: scores = [1.0]*len(cells)
    quotas = [remaining*s/sum(scores) for s in scores]
    floors = [math.floor(q) for q in quotas]
    for c,f in zip(cells, floors): base[c["cell_id"]] += f
    rem = remaining - sum(floors)
    order = sorted(range(len(cells)), key=lambda i: (-(quotas[i]-floors[i]), cells[i]["cell_id"]))
    for i in order[:rem]: base[cells[i]["cell_id"]] += 1
    return base

def _write_summary(root: Path, pilot_id: str, summary: dict[str, Any]) -> None:
    d=root/"results"/pilot_id; d.mkdir(parents=True, exist_ok=True); (d/"summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n")

def run_adaptive_pilot(output_root: Path, *, pilot_id: str, cells: list[AdaptiveCell], generators: dict[str, Iterable[CandidateRecord]], deterministic_seed: str, evaluator: Callable[..., Any] = evaluate_with_metrics) -> dict[str, Any]:
    before = (output_root/"results/global_top_10.json").read_bytes() if (output_root/"results/global_top_10.json").exists() else b""
    started=time.perf_counter_ns(); seen:set[int]=set(); outcomes={"reached_one":0,"repeated_state":0,"interrupted":0}; all_entries=[]; cell_summaries=[]; failures=[]
    requested=sum(c.candidate_count for c in cells); evaluated=0
    try:
      for cell in cells:
        validate_cell(cell); lengths=[]; maxints=[]; mets=[]; local_outcomes={"reached_one":0,"repeated_state":0,"interrupted":0}; cstart=time.perf_counter_ns(); local=0
        it=iter(generators[cell.cell_id])
        for _ in range(cell.candidate_count):
            rec=next(it); validate_candidate_for_cell(rec, cell, seen); seen.add(rec.candidate); local+=1; evaluated+=1
            ev=evaluator(rec.candidate); result=ev.result; mets.append(ev.metrics); outcomes[result.outcome]+=1; local_outcomes[result.outcome]+=1
            if result.outcome=="repeated_state":
                meta={"pilot_id":pilot_id,"cell_id":cell.cell_id,"family":cell.family,"validation_mode":cell.validation_mode,"parent_rank":cell.parent_rank,"source_parent":str(cell.source_parent),"deterministic_seed":deterministic_seed,"generation_parameters":cell.parameters}
                cc=_cycle_candidate_record(result=result,candidate=rec.candidate,experiment_id=pilot_id,strategy=cell.strategy,metadata=meta); _persist_cycle_candidates(output_root,[cc])
                ver=verify_cycle_evidence(start=rec.candidate, expected=result)
                if ver.confirmed:
                    paths=write_discovery_artifacts(output_root,result=result,members=ver.members,metadata={**meta,"strategy":cell.strategy})
                    summary={"pilot_id":pilot_id,"pilot":True,"deterministic_seed":deterministic_seed,"requested_candidate_count":requested,"candidates_evaluated":evaluated,"distinct_candidate_count":len(seen),"stopped_early":True,"stopping_reason":"verified_nontrivial_cycle","active_cell_id":cell.cell_id,"active_family":cell.family,"outcome_counts":outcomes,"discovery_artifact_path":str(paths["discovery"]),"cycle_candidate_artifact_path":"results/cycle_candidates.json","elapsed_runtime_seconds":(time.perf_counter_ns()-started)/1e9,"global_top_10_isolated":before==((output_root/"results/global_top_10.json").read_bytes() if (output_root/"results/global_top_10.json").exists() else b"")}
                    _write_summary(output_root,pilot_id,summary); return summary
                failures.append(ver.failure_reason); raise RuntimeError(f"cycle verification failed: {ver.failure_reason}")
            if result.outcome in ("reached_one","repeated_state"):
                lengths.append(result.total_steps_executed); maxints.append(result.maximum_integer); all_entries.append({"length":result.total_steps_executed,"cell_id":cell.cell_id,"cell_local_order":local})
        cs={"cell_id":cell.cell_id,"family":cell.family,"strategy":cell.strategy,"validation_mode":cell.validation_mode,"source_parent":str(cell.source_parent),"parent_rank":cell.parent_rank,"parameters":cell.parameters,"requested_candidate_count":cell.candidate_count,"candidates_evaluated":local,"reached_one_count":local_outcomes["reached_one"],"repeated_state_count":local_outcomes["repeated_state"],"interrupted_count":local_outcomes["interrupted"],"mean_trajectory_length":statistics.fmean(lengths) if lengths else None,"median_trajectory_length":statistics.median(lengths) if lengths else None,"p90_trajectory_length":_percentile(lengths,.9) if lengths else None,"p99_trajectory_length":_percentile(lengths,.99) if len(lengths)>=2 else None,"maximum_trajectory_length":max(lengths) if lengths else None,"maximum_integer_reached":str(max(maxints)) if maxints else None,"fixed_threshold_exceedance_counts":{str(t):sum(x>=t for x in lengths) for t in THRESHOLDS},"overall_pilot_top_tail_count":0,"recurrence_metric_aggregates":aggregate_metrics(mets),"runtime_seconds":(time.perf_counter_ns()-cstart)/1e9,"trajectories_per_second":local/((time.perf_counter_ns()-cstart)/1e9)}; cs["deterministic_score"]=deterministic_score(cs); cell_summaries.append(cs)
      tails=assign_top_tail(all_entries)
      for cs in cell_summaries: cs["overall_pilot_top_tail_count"]=tails.get(cs["cell_id"],0); cs["deterministic_score"]=deterministic_score(cs)
      summary={"pilot_id":pilot_id,"pilot":True,"deterministic_seed":deterministic_seed,"requested_candidate_count":requested,"candidates_evaluated":evaluated,"distinct_candidate_count":len(seen),"stopped_early":False,"stopping_reason":"completed","outcome_counts":outcomes,"cell_summaries":cell_summaries,"elapsed_runtime_seconds":(time.perf_counter_ns()-started)/1e9,"global_top_10_isolated":before==((output_root/"results/global_top_10.json").read_bytes() if (output_root/"results/global_top_10.json").exists() else b"")}
      _write_summary(output_root,pilot_id,summary); return summary
    except Exception:
      summary={"pilot_id":pilot_id,"pilot":True,"deterministic_seed":deterministic_seed,"requested_candidate_count":requested,"candidates_evaluated":evaluated,"distinct_candidate_count":len(seen),"stopped_early":True,"stopping_reason":"verification_failed_or_invalid_candidate","outcome_counts":outcomes,"verification_failures":failures,"elapsed_runtime_seconds":(time.perf_counter_ns()-started)/1e9,"global_top_10_isolated":before==((output_root/"results/global_top_10.json").read_bytes() if (output_root/"results/global_top_10.json").exists() else b"")}
      _write_summary(output_root,pilot_id,summary); raise
