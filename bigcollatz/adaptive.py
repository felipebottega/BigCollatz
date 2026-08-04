"""Correctness-first adaptive cross-family pilot runner utilities."""
from __future__ import annotations

import json, math, statistics, time
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Callable

from .cycle import discovery_payload, verify_cycle, write_discovery_artifacts
from .evaluator import evaluate_with_metrics
from .experiment import _cycle_candidate_record, _persist_cycle_candidates, STRATEGY_VALIDATION_MODES, _percentile
from .generator import CandidateRecord, validate_decimal_suffix, validate_parity_prefix, validate_residue

FAMILY_BINDINGS = {
    "parity-prefix": ("S1-parity-prefix-top10", "parity_prefix"),
    "decimal-suffix": ("S5-decimal-suffix-top10", "decimal_suffix"),
    "residue": ("S6-residue-class-top10", "residue"),
}

@dataclass(frozen=True)
class AdaptiveCell:
    cell_id: str; family: str; strategy: str; validation_mode: str; source_parent: int
    parent_rank: int; candidate_count: int; parameters: dict[str, Any]


def validate_cell(cell: AdaptiveCell) -> None:
    if cell.family not in FAMILY_BINDINGS: raise ValueError("unsupported cell family")
    if (cell.strategy, cell.validation_mode) != FAMILY_BINDINGS[cell.family]: raise ValueError("family strategy validation_mode binding mismatch")
    if not cell.cell_id or cell.source_parent <= 0 or cell.candidate_count < 1: raise ValueError("malformed cell")
    p = cell.parameters
    if cell.family == "parity-prefix":
        if set(p) != {"prefix_length"} or not isinstance(p["prefix_length"], int) or isinstance(p["prefix_length"], bool) or p["prefix_length"] < 1: raise ValueError("invalid parity-prefix parameters")
    elif cell.family == "decimal-suffix":
        if set(p) != {"suffix_digits"} or not isinstance(p["suffix_digits"], int) or isinstance(p["suffix_digits"], bool) or p["suffix_digits"] < 1: raise ValueError("invalid decimal-suffix parameters")
    else:
        if set(p) != {"residue_modulus"} or not isinstance(p["residue_modulus"], int) or isinstance(p["residue_modulus"], bool) or p["residue_modulus"] < 2: raise ValueError("invalid residue parameters")


def validate_record_for_cell(record: CandidateRecord, cell: AdaptiveCell) -> None:
    validate_cell(cell)
    if record.strategy != cell.strategy or record.validation_mode != cell.validation_mode or record.parent != cell.source_parent: raise ValueError("record metadata does not match cell")
    if len(str(record.candidate)) != 1000: raise ValueError("candidate must be exactly 1000 digits")
    if cell.family == "parity-prefix":
        if record.prefix_length is None or record.prefix_length != cell.parameters["prefix_length"] or record.suffix_digits is not None or record.residue_modulus is not None or record.residue is not None: raise ValueError("parity-prefix metadata mismatch")
        if not validate_parity_prefix(record.candidate, record.parent, record.prefix_length): raise ValueError("parity-prefix invariant failed")
    elif cell.family == "decimal-suffix":
        if record.suffix_digits is None or record.suffix_digits != cell.parameters["suffix_digits"] or record.prefix_length is not None or record.residue_modulus is not None or record.residue is not None: raise ValueError("decimal-suffix metadata mismatch")
        if not validate_decimal_suffix(record.candidate, record.parent, record.suffix_digits): raise ValueError("decimal-suffix invariant failed")
    else:
        expected = cell.source_parent % cell.parameters["residue_modulus"]
        if record.residue_modulus is None or record.residue is None or record.residue_modulus != cell.parameters["residue_modulus"] or record.residue != expected or record.prefix_length is not None or record.suffix_digits is not None: raise ValueError("residue metadata mismatch")
        if not validate_residue(record.candidate, record.residue_modulus, record.residue): raise ValueError("residue invariant failed")


def metadata_for_artifact(record: CandidateRecord, cell: AdaptiveCell) -> dict[str, Any]:
    data = record.metadata(); data.update({"cell_id": cell.cell_id, "family": cell.family, "source_parent": str(cell.source_parent), "parent_rank": cell.parent_rank, "parameters": cell.parameters})
    return data


def aggregate_metrics(metrics: list[Any]) -> dict[str, Any]:
    if not metrics: return {}
    defined = [m.first_descent_step for m in metrics if m.first_descent_step is not None]
    max_exc = max(Fraction(m.maximum_excursion_numerator, m.maximum_excursion_denominator) for m in metrics)
    return {
        "mean_odd_step_count": statistics.fmean(m.odd_step_count for m in metrics),
        "mean_odd_step_density": float(sum((m.odd_step_density for m in metrics), Fraction(0,1)) / len(metrics)),
        "mean_first_descent_step": statistics.fmean(defined) if defined else None,
        "undefined_first_descent_count": len(metrics) - len(defined),
        "maximum_excursion_numerator": max_exc.numerator,
        "maximum_excursion_denominator": max_exc.denominator,
        "mean_same_decimal_digit_band_return_count": statistics.fmean(m.same_decimal_digit_band_return_count for m in metrics),
        "mean_repeated_residue_hit_count": statistics.fmean(m.repeated_residue_hit_count for m in metrics),
        "residue_modulus": metrics[0].residue_modulus,
    }

def top_tail_counts(trajectories: list[dict[str, Any]], fraction: float = .10) -> dict[str, int]:
    n = math.ceil(len(trajectories) * fraction) if trajectories else 0
    selected = sorted(trajectories, key=lambda t: (-t["length"], t["cell_id"], t["cell_order"]))[:n]
    return dict(Counter(t["cell_id"] for t in selected))

def deterministic_score(summary: dict[str, Any]) -> float:
    p99 = summary.get("p99_trajectory_length") or summary.get("p90_trajectory_length") or 0
    m = summary.get("recurrence_metrics", {}) or {}
    return (summary.get("mean_trajectory_length") or 0) + .6*(summary.get("p90_trajectory_length") or 0) + .3*p99 + 25*(summary.get("overall_pilot_top_tail_count") or 0) + 10*(m.get("mean_repeated_residue_hit_count") or 0) + 50*(summary.get("repeated_state_count") or 0)

def allocate_stage_b(cells: list[dict[str, Any]], total: int, minimum: int = 1) -> dict[str, int]:
    if total < minimum * len(cells): raise ValueError("infeasible minimum quota")
    if len(cells) == 1: return {cells[0]["cell_id"]: total}
    scores = [max(0.0, float(c.get("score", 0))) for c in cells]
    if sum(scores) == 0: scores = [1.0] * len(cells)
    remaining = total - minimum * len(cells); s = sum(scores)
    floors = [math.floor(remaining*x/s) for x in scores]; rem = remaining - sum(floors)
    alloc = [minimum + f for f in floors]
    residues = [(remaining*x) % s for x in scores]
    for i in sorted(range(len(cells)), key=lambda i: (-residues[i], cells[i]["cell_id"]))[:rem]: alloc[i]+=1
    return {c["cell_id"]: a for c,a in zip(cells, alloc)}


def run_adaptive_pilot(output_root: Path, *, pilot_id: str, cells: list[AdaptiveCell], generators: dict[str, Iterable[CandidateRecord]], deterministic_seed: str, evaluator: Callable[..., Any] = evaluate_with_metrics) -> dict[str, Any]:
    before = (output_root/"results/global_top_10.json").read_bytes() if (output_root/"results/global_top_10.json").exists() else b""
    started = time.perf_counter_ns(); seen=set(); outcomes=Counter(); cell_data=defaultdict(lambda: {"lengths":[],"metrics":[],"maxima":[],"records":0,"outcomes":Counter()}); trajectories=[]; cycle_path="results/cycle_candidates.json"
    evaluated=0; requested=sum(c.candidate_count for c in cells); active=None; verification_failure=None
    try:
      for cell in cells:
        validate_cell(cell); active=cell
        order=0
        for record in generators[cell.cell_id]:
            validate_record_for_cell(record, cell)
            if record.candidate in seen: raise ValueError("duplicate candidate across pilot cells")
            seen.add(record.candidate); order += 1; evaluated += 1
            ev = evaluator(record.candidate); result = ev.result if hasattr(ev, "result") else ev; metrics = getattr(ev, "metrics", None)
            outcomes[result.outcome]+=1; d=cell_data[cell.cell_id]; d["records"]+=1; d["outcomes"][result.outcome]+=1
            if result.outcome in {"reached_one","repeated_state"}:
                d["lengths"].append(result.total_steps_executed); d["maxima"].append(result.maximum_integer); trajectories.append({"length":result.total_steps_executed,"cell_id":cell.cell_id,"cell_order":order})
                if metrics: d["metrics"].append(metrics)
            if result.outcome == "repeated_state":
                meta=metadata_for_artifact(record, cell); compact=_cycle_candidate_record(result=result,candidate=record.candidate,experiment_id=pilot_id,strategy=record.strategy,metadata=meta); _persist_cycle_candidates(output_root,[compact])
                ver=verify_cycle(start=record.candidate,result=result,claimed_members=None)
                if ver.confirmed:
                    payload=discovery_payload(start=record.candidate,result=result,members=ver.members,context={"pilot_id":pilot_id,"strategy":record.strategy,"deterministic_seed":deterministic_seed,"cell_id":cell.cell_id,"family":cell.family,"generation_parameters":cell.parameters,"source_metadata":meta,"validation_mode":record.validation_mode})
                    jp,mp=write_discovery_artifacts(output_root,payload)
                    summary={"pilot_id":pilot_id,"pilot":True,"deterministic_seed":deterministic_seed,"stopped_early":True,"stopping_reason":"verified_nontrivial_cycle","requested_candidate_count":requested,"candidates_evaluated":evaluated,"distinct_candidate_count":len(seen),"active_cell_id":cell.cell_id,"active_family":cell.family,"outcome_counts":dict(outcomes),"discovery_artifact_path":str(jp.relative_to(output_root)),"cycle_candidate_artifact_path":cycle_path,"elapsed_runtime_seconds":(time.perf_counter_ns()-started)/1e9,"global_top_10_isolated":before==((output_root/"results/global_top_10.json").read_bytes() if (output_root/"results/global_top_10.json").exists() else b"")}
                    out=output_root/"results"/pilot_id; out.mkdir(parents=True,exist_ok=True); (out/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n"); return summary
                verification_failure=ver.failure_reason; raise RuntimeError(f"cycle verification failed: {ver.failure_reason}")
      tails=top_tail_counts(trajectories); summaries=[]
      for cell in cells:
        d=cell_data[cell.cell_id]; lengths=d["lengths"]
        summ={"cell_id":cell.cell_id,"family":cell.family,"strategy":cell.strategy,"validation_mode":cell.validation_mode,"source_parent":str(cell.source_parent),"parent_rank":cell.parent_rank,"parameters":cell.parameters,"requested_candidate_count":cell.candidate_count,"candidates_evaluated":d["records"],"reached_one_count":d["outcomes"].get("reached_one",0),"repeated_state_count":d["outcomes"].get("repeated_state",0),"interrupted_count":d["outcomes"].get("interrupted",0),"mean_trajectory_length":statistics.fmean(lengths) if lengths else None,"median_trajectory_length":statistics.median(lengths) if lengths else None,"p90_trajectory_length":_percentile(lengths,.9) if lengths else None,"p99_trajectory_length":_percentile(lengths,.99) if len(lengths)>1 else None,"maximum_trajectory_length":max(lengths) if lengths else None,"maximum_integer_reached":str(max(d["maxima"])) if d["maxima"] else None,"threshold_exceedance_counts":{"ge_25000":sum(x>=25000 for x in lengths),"ge_26000":sum(x>=26000 for x in lengths),"ge_27000":sum(x>=27000 for x in lengths)},"overall_pilot_top_tail_count":tails.get(cell.cell_id,0),"recurrence_metrics":aggregate_metrics(d["metrics"]),"runtime_seconds":0,"trajectories_per_second":None}
        summ["deterministic_score"]=deterministic_score(summ); summaries.append(summ)
      summary={"pilot_id":pilot_id,"pilot":True,"deterministic_seed":deterministic_seed,"stopped_early":False,"stopping_reason":"completed","requested_candidate_count":requested,"candidates_evaluated":evaluated,"distinct_candidate_count":len(seen),"cell_summaries":summaries,"outcome_counts":dict(outcomes),"global_top_10_isolated":before==((output_root/"results/global_top_10.json").read_bytes() if (output_root/"results/global_top_10.json").exists() else b"")}
      out=output_root/"results"/pilot_id; out.mkdir(parents=True,exist_ok=True); (out/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n"); return summary
    except Exception:
      out=output_root/"results"/pilot_id; out.mkdir(parents=True,exist_ok=True); (out/"summary.json").write_text(json.dumps({"pilot_id":pilot_id,"pilot":True,"stopped_early":True,"stopping_reason":"verification_failed" if verification_failure else "validation_failed","verification_failure":verification_failure,"candidates_evaluated":evaluated,"distinct_candidate_count":len(seen),"global_top_10_isolated":before==((output_root/"results/global_top_10.json").read_bytes() if (output_root/"results/global_top_10.json").exists() else b"")},indent=2,sort_keys=True)+"\n"); raise
