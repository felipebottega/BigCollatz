"""Correctness-first adaptive pilot infrastructure for future searches."""

from __future__ import annotations

import json, math, re, statistics, time
from fractions import Fraction
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .cycle import reconstruct_cycle, verify_nontrivial_cycle, write_discovery_artifacts
from .evaluator import EvaluationMetrics, evaluate_with_metrics
from .generator import CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY, validate_decimal_suffix, validate_parity_prefix, validate_residue

FAMILY_BINDINGS = {
    "parity-prefix": (S1_STRATEGY, "parity_prefix", {"prefix_length"}),
    "decimal-suffix": (S5_STRATEGY, "decimal_suffix", {"suffix_digits"}),
    "residue": (S6_STRATEGY, "residue", {"residue_modulus"}),
}
THRESHOLDS = (25000, 26000, 27000)
WINDOWS_DRIVE_QUALIFIED_RE = re.compile(r"^[A-Za-z]:")

@dataclass(frozen=True)
class AdaptiveCell:
    cell_id: str
    family: str
    strategy: str
    validation_mode: str
    source_parent: int
    parent_rank: int
    candidate_count: int
    parameters: dict[str, int]


def _int(value: Any, name: str, *, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def validate_cell(cell: AdaptiveCell) -> None:
    if not cell.cell_id:
        raise ValueError("cell_id must be nonempty")
    if cell.family not in FAMILY_BINDINGS:
        raise ValueError("unknown family")
    strategy, mode, keys = FAMILY_BINDINGS[cell.family]
    if (cell.strategy, cell.validation_mode) != (strategy, mode):
        raise ValueError("incorrect family/strategy/validation binding")
    _int(cell.source_parent, "source_parent", minimum=1)
    _int(cell.parent_rank, "parent_rank", minimum=1)
    _int(cell.candidate_count, "candidate_count", minimum=1)
    if set(cell.parameters) != keys:
        raise ValueError("missing or extra parameters")
    for key, value in cell.parameters.items():
        _int(value, key, minimum=1 if key != "residue_modulus" else 2)


def validate_record_for_cell(record: CandidateRecord, cell: AdaptiveCell, seen: set[int]) -> None:
    validate_cell(cell)
    if record.candidate == cell.source_parent:
        raise ValueError("candidate must not equal source_parent")
    if record.strategy != cell.strategy:
        raise ValueError("record strategy does not match cell")
    if record.validation_mode != cell.validation_mode:
        raise ValueError("record validation_mode does not match cell")
    if record.parent != cell.source_parent:
        raise ValueError("record parent does not match cell")
    if len(str(record.candidate)) != 1000:
        raise ValueError("candidate must have exactly 1,000 decimal digits")
    if cell.family == "parity-prefix":
        if record.prefix_length is None: raise ValueError("missing prefix_length")
        if record.prefix_length != cell.parameters["prefix_length"]: raise ValueError("mismatched prefix_length")
        if record.suffix_digits is not None or record.residue_modulus is not None or record.residue is not None: raise ValueError("unrelated metadata in parity record")
        if not validate_parity_prefix(record.candidate, record.parent, record.prefix_length): raise ValueError("failed mathematical invariant")
    elif cell.family == "decimal-suffix":
        if record.suffix_digits is None: raise ValueError("missing suffix_digits")
        if record.suffix_digits != cell.parameters["suffix_digits"]: raise ValueError("mismatched suffix_digits")
        if record.prefix_length is not None or record.residue_modulus is not None or record.residue is not None: raise ValueError("unrelated metadata in suffix record")
        if not validate_decimal_suffix(record.candidate, record.parent, record.suffix_digits): raise ValueError("failed mathematical invariant")
    else:
        if record.residue_modulus is None: raise ValueError("missing residue_modulus")
        if record.residue is None: raise ValueError("missing residue")
        if record.residue_modulus != cell.parameters["residue_modulus"]: raise ValueError("mismatched residue_modulus")
        if record.residue != cell.source_parent % record.residue_modulus: raise ValueError("mismatched residue")
        if record.prefix_length is not None or record.suffix_digits is not None: raise ValueError("unrelated metadata in residue record")
        if not validate_residue(record.candidate, record.residue_modulus, record.residue): raise ValueError("failed mathematical invariant")
    if record.candidate in seen:
        raise ValueError("duplicate candidate in pilot")
    seen.add(record.candidate)


def _percentile(values: list[int], p: float) -> float | None:
    if not values: return None
    ordered=sorted(values); pos=(len(ordered)-1)*p; lo=int(pos); frac=pos-lo
    return ordered[lo] if not frac else ordered[lo]+frac*(ordered[lo+1]-ordered[lo])


def _cell_dict(cell: AdaptiveCell) -> dict[str, Any]:
    data = asdict(cell)
    data["source_parent"] = str(cell.source_parent)
    return data


def _trajectories_per_second(evaluated: int, runtime_seconds: float) -> float | None:
    if runtime_seconds <= 0:
        return None
    return evaluated / runtime_seconds


def _metric_aggregates(metrics: list[EvaluationMetrics]) -> dict[str, Any]:
    moduli = {m.residue_modulus for m in metrics}
    if len(moduli) != 1:
        raise ValueError("inconsistent residue_modulus values within cell")
    density_num = sum(m.odd_step_density[0] for m in metrics)
    density_den = sum(m.odd_step_density[1] for m in metrics)
    density_mean = sum(Fraction(*m.odd_step_density) for m in metrics) / len(metrics)
    descents = [m.first_descent_step for m in metrics if m.first_descent_step is not None]
    maximum = max(metrics, key=lambda m: Fraction(m.maximum_excursion_numerator, m.maximum_excursion_denominator))
    return {
        "mean_odd_step_count": statistics.fmean(m.odd_step_count for m in metrics),
        "odd_step_density": {"numerator": density_num, "denominator": density_den},
        "mean_odd_step_density": float(density_mean),
        "mean_first_descent_step": statistics.fmean(descents) if descents else None,
        "undefined_first_descent_count": len(metrics) - len(descents),
        "maximum_excursion": {"numerator": maximum.maximum_excursion_numerator, "denominator": maximum.maximum_excursion_denominator},
        "mean_same_decimal_digit_band_return_count": statistics.fmean(m.same_decimal_digit_band_return_count for m in metrics),
        "mean_repeated_residue_hit_count": statistics.fmean(m.repeated_residue_hit_count for m in metrics),
        "residue_modulus": next(iter(moduli)),
    }


def _score(summary: dict[str, Any]) -> float:
    p99 = summary["p99_trajectory_length"]
    if p99 is None:  # fallback for empty/incomplete cells is documented by field name
        p99 = summary["p99_fallback_trajectory_length"]
    m = summary["recurrence_metric_aggregates"]
    return (summary["mean_trajectory_length"] + summary["p90_trajectory_length"] + p99 + 10 * summary["overall_pilot_top_tail_count"] + m["mean_repeated_residue_hit_count"])


def rank_trajectories(trajectories: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    """Return compact ranked pilot trajectories with deterministic tie-breaking."""
    ranked = sorted(trajectories, key=lambda t: (-t["trajectory_length"], t["cell_id"], t["candidate_order_within_cell"], t["starting_integer"]))[:limit]
    return [{"rank": index + 1, **record} for index, record in enumerate(ranked)]


def _finalize_completed_cells(cell_summaries: list[dict[str, Any]], trajectories: list[dict[str, Any]]) -> None:
    tail_n = math.ceil(len(trajectories) * 0.10)
    selected = sorted(trajectories, key=lambda t: (-t["trajectory_length"], t["cell_id"], t["candidate_order_within_cell"]))[:tail_n]
    tail_counts: dict[str, int] = {}
    for t in selected: tail_counts[t["cell_id"]] = tail_counts.get(t["cell_id"], 0) + 1
    for s in cell_summaries:
        lengths = s.pop("_lengths")
        s["fixed_threshold_exceedance_counts"] = {f"length_gte_{x}": sum(v >= x for v in lengths) for x in THRESHOLDS}
        s["overall_pilot_top_tail_count"] = tail_counts.get(s["cell_id"], 0)
        s["deterministic_score"] = _score(s)


def _validate_pilot_id(pilot_id: str) -> None:
    if (
        not pilot_id
        or pilot_id in {".", ".."}
        or "/" in pilot_id
        or "\\" in pilot_id
        or pilot_id.startswith("/")
        or WINDOWS_DRIVE_QUALIFIED_RE.match(pilot_id)
    ):
        raise ValueError("pilot_id must be a single portable path-safe name")


def run_adaptive_pilot(output_root: Path, *, pilot_id: str, deterministic_seed: str, cells: list[AdaptiveCell], generators: dict[str, Iterable[CandidateRecord]], evaluator: Callable[..., Any]=evaluate_with_metrics, timer: Callable[[], float]=time.perf_counter) -> dict[str, Any]:
    _validate_pilot_id(pilot_id)
    requested=sum(c.candidate_count for c in cells); seen:set[int]=set(); cell_summaries=[]; trajectories=[]; outcomes={"reached_one":0,"repeated_state":0,"interrupted":0}; total=0; start_time=timer(); artifacts={}
    global_path = output_root / "results" / "global_top_10.json"
    initial_global = global_path.read_bytes() if global_path.exists() else None
    result_dir=output_root/"results"/pilot_id; result_dir.mkdir(parents=True, exist_ok=True)
    def global_isolated() -> bool:
        return (global_path.read_bytes() if global_path.exists() else None) == initial_global
    def write_summary(reason: str, stopped: bool, failure: str|None=None):
        isolated = global_isolated()
        summary={"pilot_id":pilot_id,"pilot":True,"deterministic_seed":deterministic_seed,"requested_candidate_count":requested,"candidates_evaluated":total,"distinct_candidate_count":len(seen),"stopped_early":stopped,"stopping_reason":reason,"outcome_counts":outcomes,"elapsed_runtime_seconds":timer()-start_time,"global_top_10_isolated":isolated,"cells":cell_summaries,"artifact_paths":artifacts}
        if failure: summary["failure_message"]=failure; summary["verification_failure"]=failure if reason == "verification_failed" else summary.get("verification_failure")
        (result_dir/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
        if not isolated:
            raise RuntimeError("adaptive pilot modified global_top_10.json")
        return summary
    try:
        for cell in cells:
            validate_cell(cell)
            cell_start=timer(); iterator=iter(generators[cell.cell_id])
            lengths=[]; maxint=0; counts={"reached_one":0,"repeated_state":0,"interrupted":0}; evaluated=0; metrics_list=[]
            for requested_index in range(cell.candidate_count):
                try: record=next(iterator)
                except StopIteration as exc: raise ValueError(f"short generator for cell {cell.cell_id}: expected {cell.candidate_count}, got {requested_index}") from exc
                validate_record_for_cell(record, cell, seen)
                result, metrics=evaluator(record.candidate)
                evaluated += 1; total += 1; outcomes[result.outcome]+=1; counts[result.outcome]+=1
                lengths.append(result.total_steps_executed); maxint=max(maxint,result.maximum_integer); metrics_list.append(metrics)
                trajectories.append({"starting_integer": str(record.candidate), "trajectory_length": result.total_steps_executed, "maximum_integer": str(result.maximum_integer), "cell_id": cell.cell_id, "family": cell.family, "strategy": cell.strategy, "source_parent": str(cell.source_parent), "parent_rank": cell.parent_rank, "generation_parameters": dict(cell.parameters), "validation_mode": cell.validation_mode, "deterministic_seed": deterministic_seed, "candidate_order_within_cell": evaluated - 1})
                if result.outcome == "repeated_state":
                    members=reconstruct_cycle(record.candidate,result)
                    verification=verify_nontrivial_cycle(record.candidate,result,[str(v) for v in members])
                    if not verification.confirmed:
                        write_summary("verification_failed", True, verification.failure_reason)
                        raise ValueError(f"cycle verification failed: {verification.failure_reason}")
                    artifacts.update(write_discovery_artifacts(output_root, starting_integer=record.candidate, result=result, cycle_members=members, pilot_id=pilot_id, strategy=cell.strategy, deterministic_seed=deterministic_seed, cell_id=cell.cell_id, family=cell.family, generation_parameters=cell.parameters, source_metadata=record.metadata(), validation_mode=cell.validation_mode))
                    runtime=timer()-cell_start
                    cell_summaries.append({**_cell_dict(cell),"requested_candidate_count":cell.candidate_count,"candidates_evaluated":evaluated,"partial":True,"reached_one_count":counts["reached_one"],"repeated_state_count":counts["repeated_state"],"interrupted_count":counts["interrupted"],"mean_trajectory_length":statistics.fmean(lengths),"median_trajectory_length":statistics.median(lengths),"p90_trajectory_length":_percentile(lengths,.9),"p99_trajectory_length":None,"p99_fallback_trajectory_length":max(lengths),"maximum_trajectory_length":max(lengths),"maximum_integer_reached":str(maxint),"fixed_threshold_exceedance_counts":None,"overall_pilot_top_tail_count":None,"recurrence_metric_aggregates":None,"deterministic_score":None,"runtime_seconds":runtime,"trajectories_per_second":_trajectories_per_second(evaluated, runtime)})
                    return write_summary("verified_nontrivial_cycle", True)
            try: next(iterator)
            except StopIteration: pass
            else: raise ValueError(f"long generator for cell {cell.cell_id}: produced more than {cell.candidate_count}")
            runtime=timer()-cell_start
            if evaluated != cell.candidate_count: raise ValueError("cell count mismatch")
            aggs=_metric_aggregates(metrics_list)
            p99=_percentile(lengths,.99)
            cell_summaries.append({**_cell_dict(cell),"requested_candidate_count":cell.candidate_count,"candidates_evaluated":evaluated,"reached_one_count":counts["reached_one"],"repeated_state_count":counts["repeated_state"],"interrupted_count":counts["interrupted"],"mean_trajectory_length":statistics.fmean(lengths),"median_trajectory_length":statistics.median(lengths),"p90_trajectory_length":_percentile(lengths,.9),"p99_trajectory_length":p99,"p99_fallback_trajectory_length":max(lengths),"maximum_trajectory_length":max(lengths),"maximum_integer_reached":str(maxint),"recurrence_metric_aggregates":aggs,"runtime_seconds":runtime,"trajectories_per_second":_trajectories_per_second(evaluated, runtime),"_lengths":lengths})
        if total != requested or len(seen)!=total: raise ValueError("pilot count mismatch")
        _finalize_completed_cells(cell_summaries, trajectories)
        artifacts["top_30"] = str(Path("results") / pilot_id / "top_30.json")
        (result_dir / "top_30.json").write_text(json.dumps(rank_trajectories(trajectories, 30), indent=2, sort_keys=True)+"\n")
        summary = write_summary("completed", False)
        summary["overall_pilot_top_tail_count"] = sum(s["overall_pilot_top_tail_count"] for s in cell_summaries)
        (result_dir/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
        if not global_isolated(): raise RuntimeError("adaptive pilot modified global_top_10.json")
        return summary
    except Exception as exc:
        if isinstance(exc, RuntimeError) and str(exc) == "adaptive pilot modified global_top_10.json":
            raise
        if not (result_dir/"summary.json").exists(): write_summary(type(exc).__name__, True, str(exc))
        raise
