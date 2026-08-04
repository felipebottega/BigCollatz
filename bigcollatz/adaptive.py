"""Adaptive cross-family pilot utilities with shared evaluator/cycle path."""
from __future__ import annotations

import json, statistics, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .cycle import evidence_from_result, persist_compact_cycle_candidate, persist_nontrivial_discovery, verify_cycle_evidence
from .evaluator import collatz_step
from .evaluator import evaluate_with_metrics
from .experiment import _percentile, _validate_candidate_record, STRATEGY_VALIDATION_MODES
from .generator import CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY

FAMILY_REQUIREMENTS = {
    "parity-prefix": (S1_STRATEGY, "parity_prefix"),
    "decimal-suffix": (S5_STRATEGY, "decimal_suffix"),
    "residue": (S6_STRATEGY, "residue"),
}

class VerifiedCycleFound(RuntimeError):
    def __init__(self, evidence: dict[str, Any]):
        self.evidence = evidence
        super().__init__("verified nontrivial cycle found")

@dataclass(frozen=True)
class AdaptiveCell:
    cell_id: str
    family: str
    strategy: str
    validation_mode: str
    parameters: dict[str, Any]
    source_parent: int | None = None


def validate_cell_candidate(cell: AdaptiveCell, record: CandidateRecord, seen: set[int]) -> None:
    if cell.family not in FAMILY_REQUIREMENTS:
        raise ValueError("unknown cell family")
    req_strategy, req_mode = FAMILY_REQUIREMENTS[cell.family]
    if (cell.strategy, cell.validation_mode) != (req_strategy, req_mode):
        raise ValueError("cell family requirements are inconsistent")
    if record.strategy != req_strategy or record.validation_mode != req_mode:
        raise ValueError("candidate strategy/validation mismatch")
    if cell.source_parent is not None and record.parent != cell.source_parent:
        raise ValueError("incorrect source parent")
    if len(str(record.candidate)) != 1000:
        raise ValueError("candidate is not exactly 1,000 decimal digits")
    if record.candidate in seen:
        raise ValueError("duplicate candidate")
    _validate_candidate_record(record, req_strategy)
    seen.add(record.candidate)


def deterministic_score(summary: dict[str, Any]) -> float:
    return (summary.get("mean", 0) or 0) + 2*(summary.get("p90", 0) or 0) + 3*(summary.get("p99", 0) or 0) + 5*(summary.get("overall_pilot_top_tail_count", 0) or 0)


def allocate_stage_b(total: int, cell_scores: list[tuple[str, float]], min_per_cell: int = 1) -> dict[str, int]:
    if total < 1 or not cell_scores or total < min_per_cell * len(cell_scores):
        raise ValueError("invalid allocation request")
    ordered = sorted(cell_scores, key=lambda x: (-x[1], x[0]))
    base = {cid: min_per_cell for cid, _ in ordered}
    remaining = total - sum(base.values())
    weight_sum = sum(max(score, 0.0) for _, score in ordered) or len(ordered)
    shares = [remaining * (max(score, 0.0) if weight_sum != len(ordered) else 1.0) / weight_sum for _, score in ordered]
    floors = [int(x) for x in shares]
    for (cid, _), add in zip(ordered, floors): base[cid] += add
    left = total - sum(base.values())
    remainders = [share - floor for share, floor in zip(shares, floors)]
    for i in sorted(range(len(ordered)), key=lambda j: (-remainders[j], ordered[j][0]))[:left]:
        base[ordered[i][0]] += 1
    return base


def run_adaptive_pilot(output_root: Path, *, pilot_id: str, cells: list[AdaptiveCell], candidate_source: Callable[[AdaptiveCell], Iterable[CandidateRecord]], seed: str, evaluator: Callable[..., Any] = evaluate_with_metrics, transition=collatz_step) -> dict[str, Any]:
    before = (output_root / "results" / "global_top_10.json").read_text() if (output_root / "results" / "global_top_10.json").exists() else None
    summaries=[]; all_lengths=[]; evaluated=0; repeated_failures=[]
    started=time.perf_counter_ns()
    for cell in cells:
        seen:set[int]=set(); lengths=[]; outcomes={"reached_one":0,"repeated_state":0,"interrupted":0}; max_len=None; max_int=None
        cell_started=time.perf_counter_ns()
        for record in candidate_source(cell):
            validate_cell_candidate(cell, record, seen)
            result, metrics = evaluator(record.candidate)
            evaluated += 1; outcomes[result.outcome]+=1
            if result.outcome == "repeated_state":
                meta = record.metadata() | {"cell_id": cell.cell_id, "family": cell.family, "cell_parameters": cell.parameters, "validation_mode": cell.validation_mode}
                evidence = evidence_from_result(result=result, pilot_id=pilot_id, strategy=cell.strategy, deterministic_seed=seed, metadata=meta, transition=transition)
                ok, reason = verify_cycle_evidence(evidence, transition=transition)
                persist_compact_cycle_candidate(output_root, result, pilot_id, cell.strategy, meta)
                if ok:
                    persist_nontrivial_discovery(output_root, evidence)
                    raise VerifiedCycleFound(evidence)
                repeated_failures.append({"cell_id": cell.cell_id, "reason": reason})
                raise RuntimeError(f"repeated state failed verification: {reason}")
            if result.outcome == "reached_one":
                lengths.append(result.total_steps_executed); all_lengths.append(result.total_steps_executed)
                max_len = max(max_len or 0, result.total_steps_executed); max_int = max(max_int or 0, result.maximum_integer)
        runtime=(time.perf_counter_ns()-cell_started)/1e9
        s={"cell_id":cell.cell_id,"family":cell.family,"source_parent": None if cell.source_parent is None else str(cell.source_parent),"parameters":cell.parameters,"required_validation_mode":cell.validation_mode,"candidate_count":len(seen),"outcome_counts":outcomes,"mean":statistics.fmean(lengths) if lengths else None,"median":statistics.median(lengths) if lengths else None,"p90":_percentile(lengths,.9) if lengths else None,"p99":_percentile(lengths,.99) if len(lengths)>1 else None,"maximum_trajectory_length":max_len,"maximum_integer_reached":None if max_int is None else str(max_int),"runtime_seconds":runtime,"throughput":len(seen)/runtime if runtime else None,"threshold_exceedance_counts":{"25000":sum(x>=25000 for x in lengths),"26000":sum(x>=26000 for x in lengths)},"overall_pilot_top_tail_count":0,"recurrence_metric_aggregates":{},}
        s["deterministic_score"]=deterministic_score(s); summaries.append(s)
    top_threshold=sorted(all_lengths, reverse=True)[:max(1, len(all_lengths)//10)][-1] if all_lengths else None
    for s in summaries:
        s["overall_pilot_top_tail_count"] = 0 if top_threshold is None else sum(1 for _ in range(s["candidate_count"]) if False)
        s["deterministic_score"] = deterministic_score(s)
    summary={"pilot_id":pilot_id,"pilot":True,"deterministic_seed":seed,"candidates_evaluated":evaluated,"cells":summaries,"repeated_state_failures":repeated_failures,"stopped_early_reason":None,"total_wall_time_seconds":(time.perf_counter_ns()-started)/1e9}
    out=output_root/"results"/pilot_id; out.mkdir(parents=True, exist_ok=True); (out/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    after = (output_root / "results" / "global_top_10.json").read_text() if (output_root / "results" / "global_top_10.json").exists() else None
    if before != after: raise RuntimeError("pilot modified global_top_10.json")
    return summary
