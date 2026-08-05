"""Correctness-first adaptive pilot infrastructure for future searches."""

from __future__ import annotations

import json, statistics, time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .cycle import reconstruct_cycle, verify_nontrivial_cycle, write_discovery_artifacts
from .evaluator import evaluate_with_metrics
from .generator import CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY, validate_decimal_suffix, validate_parity_prefix, validate_residue

FAMILY_BINDINGS = {
    "parity-prefix": (S1_STRATEGY, "parity_prefix", {"prefix_length"}),
    "decimal-suffix": (S5_STRATEGY, "decimal_suffix", {"suffix_digits"}),
    "residue": (S6_STRATEGY, "residue", {"residue_modulus"}),
}

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


def _take_exact(records: Iterable[CandidateRecord], count: int, cell_id: str) -> list[CandidateRecord]:
    iterator = iter(records); out=[]
    for idx in range(count):
        try: out.append(next(iterator))
        except StopIteration as exc: raise ValueError(f"short generator for cell {cell_id}: expected {count}, got {idx}") from exc
    try: next(iterator)
    except StopIteration: return out
    raise ValueError(f"long generator for cell {cell_id}: produced more than {count}")


def _percentile(values: list[int], p: float) -> float | None:
    if not values: return None
    ordered=sorted(values); pos=(len(ordered)-1)*p; lo=int(pos); frac=pos-lo
    return ordered[lo] if not frac else ordered[lo]+frac*(ordered[lo+1]-ordered[lo])


def run_adaptive_pilot(output_root: Path, *, pilot_id: str, deterministic_seed: str, cells: list[AdaptiveCell], generators: dict[str, Iterable[CandidateRecord]], evaluator: Callable[..., Any]=evaluate_with_metrics, timer: Callable[[], float]=time.perf_counter) -> dict[str, Any]:
    requested=sum(c.candidate_count for c in cells); seen:set[int]=set(); cell_summaries=[]; outcomes={"reached_one":0,"repeated_state":0,"interrupted":0}; total=0; start_time=timer(); artifacts={}
    result_dir=output_root/"results"/pilot_id; result_dir.mkdir(parents=True, exist_ok=True)
    def write_summary(reason: str, stopped: bool, failure: str|None=None):
        summary={"pilot_id":pilot_id,"pilot":True,"deterministic_seed":deterministic_seed,"requested_candidate_count":requested,"candidates_evaluated":total,"distinct_candidate_count":len(seen),"stopped_early":stopped,"stopping_reason":reason,"outcome_counts":outcomes,"elapsed_runtime_seconds":timer()-start_time,"global_top_10_isolated":True,"cells":cell_summaries,"artifact_paths":artifacts}
        if failure: summary["verification_failure"]=failure
        (result_dir/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
        return summary
    try:
        for cell in cells:
            validate_cell(cell)
            cell_start=timer(); iterator=iter(generators[cell.cell_id])
            lengths=[]; maxint=0; counts={"reached_one":0,"repeated_state":0,"interrupted":0}; evaluated=0
            for requested_index in range(cell.candidate_count):
                try:
                    record=next(iterator)
                except StopIteration as exc:
                    raise ValueError(f"short generator for cell {cell.cell_id}: expected {cell.candidate_count}, got {requested_index}") from exc
                validate_record_for_cell(record, cell, seen)
                result, metrics=evaluator(record.candidate)
                evaluated += 1; total += 1; outcomes[result.outcome]+=1; counts[result.outcome]+=1
                lengths.append(result.total_steps_executed); maxint=max(maxint,result.maximum_integer)
                if result.outcome == "repeated_state":
                    members=reconstruct_cycle(record.candidate,result)
                    verification=verify_nontrivial_cycle(record.candidate,result,[str(v) for v in members])
                    if not verification.confirmed:
                        summary=write_summary("verification_failed", True, verification.failure_reason)
                        raise ValueError(f"cycle verification failed: {verification.failure_reason}")
                    artifacts.update(write_discovery_artifacts(output_root, starting_integer=record.candidate, result=result, cycle_members=members, pilot_id=pilot_id, strategy=cell.strategy, deterministic_seed=deterministic_seed, cell_id=cell.cell_id, family=cell.family, generation_parameters=cell.parameters, source_metadata=record.metadata(), validation_mode=cell.validation_mode))
                    runtime=timer()-cell_start
                    cell_summaries.append({**asdict(cell),"requested_candidate_count":cell.candidate_count,"candidates_evaluated":evaluated,"reached_one_count":counts["reached_one"],"repeated_state_count":counts["repeated_state"],"interrupted_count":counts["interrupted"],"mean_trajectory_length":statistics.fmean(lengths),"median_trajectory_length":statistics.median(lengths),"p90_trajectory_length":_percentile(lengths,.9),"p99_trajectory_length":_percentile(lengths,.99),"maximum_trajectory_length":max(lengths),"maximum_integer_reached":str(maxint),"fixed_threshold_exceedance_counts":{},"overall_pilot_top_tail_count":0,"recurrence_metric_aggregates":{"odd_step_count":metrics.odd_step_count},"deterministic_score":0,"runtime_seconds":runtime,"trajectories_per_second":evaluated/runtime})
                    return write_summary("verified_nontrivial_cycle", True)
            try:
                next(iterator)
            except StopIteration:
                pass
            else:
                raise ValueError(f"long generator for cell {cell.cell_id}: produced more than {cell.candidate_count}")
            runtime=timer()-cell_start
            if evaluated != cell.candidate_count: raise ValueError("cell count mismatch")
            cell_summaries.append({**asdict(cell),"requested_candidate_count":cell.candidate_count,"candidates_evaluated":evaluated,"reached_one_count":counts["reached_one"],"repeated_state_count":counts["repeated_state"],"interrupted_count":counts["interrupted"],"mean_trajectory_length":statistics.fmean(lengths),"median_trajectory_length":statistics.median(lengths),"p90_trajectory_length":_percentile(lengths,.9),"p99_trajectory_length":_percentile(lengths,.99),"maximum_trajectory_length":max(lengths),"maximum_integer_reached":str(maxint),"fixed_threshold_exceedance_counts":{},"overall_pilot_top_tail_count":0,"recurrence_metric_aggregates":{},"deterministic_score":0,"runtime_seconds":runtime,"trajectories_per_second":evaluated/runtime})
        if total != requested or len(seen)!=total: raise ValueError("pilot count mismatch")
        return write_summary("completed", False)
    except Exception:
        if not (result_dir/"summary.json").exists(): write_summary("error", True)
        raise
