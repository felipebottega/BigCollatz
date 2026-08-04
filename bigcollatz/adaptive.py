"""Adaptive cross-family pilot runner for compact Collatz cell comparisons."""

from __future__ import annotations

import heapq
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .evaluator import collatz_step
from .experiment import COMPLETED_OUTCOMES, _abbreviate, _percentile, _top_key, _validate_candidate_record
from .generator import (
    CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY, balanced_allocation,
    load_global_top_10, parity_prefix_candidate_records, decimal_suffix_candidate_records,
    residue_candidate_records,
)

ADAPTIVE_STRATEGY = "S7-adaptive-cross-family-cells"
THRESHOLDS = (25_000, 26_000, 27_000)

@dataclass(frozen=True)
class CellSpec:
    cell_id: str
    family: str
    parent_rank: int
    parent: int
    count: int
    prefix_length: int | None = None
    suffix_digits: int | None = None
    residue_modulus: int | None = None

    def parameters(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.prefix_length is not None:
            data["prefix_length"] = self.prefix_length
        if self.suffix_digits is not None:
            data["suffix_digits"] = self.suffix_digits
        if self.residue_modulus is not None:
            data["residue_modulus"] = self.residue_modulus
            data["residue"] = self.parent % self.residue_modulus
        return data

    @property
    def validation_strategy(self) -> str:
        if self.family == "parity_prefix":
            return S1_STRATEGY
        if self.family == "decimal_suffix":
            return S5_STRATEGY
        if self.family == "residue":
            return S6_STRATEGY
        raise ValueError(f"unsupported adaptive family: {self.family}")


def _single_parent_records(cell: CellSpec, seed: str) -> Iterable[CandidateRecord | tuple[int, int]]:
    if cell.family == "parity_prefix":
        if cell.prefix_length is None:
            raise ValueError("parity-prefix cell requires prefix_length")
        for candidate, parent in parity_prefix_candidate_records(cell.count, [cell.parent], f"{seed}:{cell.cell_id}", cell.prefix_length):
            yield CandidateRecord(candidate, S1_STRATEGY, "parity_prefix", parent=parent, prefix_length=cell.prefix_length)
    elif cell.family == "decimal_suffix":
        if cell.suffix_digits is None:
            raise ValueError("decimal-suffix cell requires suffix_digits")
        yield from decimal_suffix_candidate_records(cell.count, [cell.parent], f"{seed}:{cell.cell_id}", cell.suffix_digits)
    elif cell.family == "residue":
        if cell.residue_modulus is None:
            raise ValueError("residue cell requires residue_modulus")
        yield from residue_candidate_records(cell.count, [cell.parent], f"{seed}:{cell.cell_id}", cell.residue_modulus)
    else:
        raise ValueError(f"unsupported adaptive family: {cell.family}")


def evaluate_with_recurrence(start: int) -> tuple[Any, dict[str, Any]]:
    """Exact evaluator plus compact streaming recurrence-oriented metrics."""
    if start <= 0:
        raise ValueError("start must be positive")
    state = maximum = start
    steps = odd_steps = 0
    first_descent_step: int | None = 0 if start == 1 else None
    start_digits = len(str(start))
    band_low = 10 ** (start_digits - 1)
    band_high = 10 ** start_digits
    same_band_returns = 0
    seen_residues: set[int] = {start % (2**64 - 59)}
    repeated_residue_hits = 0
    seen: dict[int, int] = {start: 0}
    if state == 1:
        from .model import EvaluationResult
        return EvaluationResult(start, 0, "reached_one", maximum), {
            "odd_step_density": 0.0, "first_descent_step": 0,
            "max_excursion_ratio": "1/1", "same_decimal_digit_band_returns": 1,
            "repeated_residue_hits_mod_2_64_minus_59": 0,
        }
    while True:
        if state & 1:
            odd_steps += 1
        state = collatz_step(state)
        steps += 1
        maximum = max(maximum, state)
        if first_descent_step is None and state < start:
            first_descent_step = steps
        if band_low <= state < band_high:
            same_band_returns += 1
        residue = state % (2**64 - 59)
        if residue in seen_residues:
            repeated_residue_hits += 1
        else:
            seen_residues.add(residue)
        first_seen = seen.get(state)
        if first_seen is not None:
            from .model import EvaluationResult
            result = EvaluationResult(start, steps, "repeated_state", maximum, repeated_state=state,
                                      cycle_entry_step=first_seen, cycle_period=steps-first_seen,
                                      stopping_reason="repeated_state", repeated_integer=str(state),
                                      first_seen_step=first_seen, repeated_at_step=steps,
                                      cycle_length=steps-first_seen)
            break
        if state == 1:
            from .model import EvaluationResult
            result = EvaluationResult(start, steps, "reached_one", maximum)
            break
        seen[state] = steps
    return result, {
        "odd_step_density": odd_steps / steps if steps else 0.0,
        "first_descent_step": first_descent_step,
        "max_excursion_ratio": f"{maximum}/{start}",
        "same_decimal_digit_band_returns": same_band_returns,
        "repeated_residue_hits_mod_2_64_minus_59": repeated_residue_hits,
    }


def stage_a_cells(parents: list[int], count_per_cell: int = 50) -> list[CellSpec]:
    return [
        CellSpec("A-parity-r1-p256", "parity_prefix", 1, parents[0], count_per_cell, prefix_length=256),
        CellSpec("A-parity-r2-p256", "parity_prefix", 2, parents[1], count_per_cell, prefix_length=256),
        CellSpec("A-decimal-r1-s64", "decimal_suffix", 1, parents[0], count_per_cell, suffix_digits=64),
        CellSpec("A-decimal-r2-s64", "decimal_suffix", 2, parents[1], count_per_cell, suffix_digits=64),
        CellSpec("A-residue-r1-m2p128p1", "residue", 1, parents[0], count_per_cell, residue_modulus=2**128 + 1),
        CellSpec("A-residue-r2-m2p128p1", "residue", 2, parents[1], count_per_cell, residue_modulus=2**128 + 1),
    ]


def score_cell(summary: dict[str, Any]) -> float:
    return (summary["p90_trajectory_length"] or 0) + 0.5 * (summary["p99_trajectory_length"] or 0) + 100 * summary["threshold_exceedance_counts"]["ge_26000"] + 250 * summary["repeated_state_count"] - 0.01 * summary["mean_first_descent_step"]


def stage_b_cells(stage_a_summaries: list[dict[str, Any]], parents: list[int], total_count: int = 600) -> list[CellSpec]:
    ranked = sorted(stage_a_summaries, key=lambda s: (-s["selection_score"], s["cell_id"]))
    selected = ranked[:3]
    families = {s["family"] for s in selected}
    for summary in ranked[3:]:
        if len(selected) >= 4:
            break
        if summary["family"] not in families:
            selected.append(summary); families.add(summary["family"])
    alloc = weighted_allocation_simple(total_count, [4, 3, 2, 1][:len(selected)])
    cells=[]
    for idx,(summary,count) in enumerate(zip(selected, alloc),1):
        params=summary["parameters"]; parent=int(summary["source_parent"])
        cells.append(CellSpec(f"B{idx}-from-{summary['cell_id']}", summary["family"], summary["parent_rank"], parent, count,
                              prefix_length=params.get("prefix_length"), suffix_digits=params.get("suffix_digits"), residue_modulus=params.get("residue_modulus")))
    return cells


def weighted_allocation_simple(count:int, weights:list[int])->list[int]:
    floors=[count*w//sum(weights) for w in weights]; rem=count-sum(floors)
    for i in range(rem): floors[i]+=1
    return floors


def run_adaptive_pilot(output_root: Path, *, pilot_id: str, seed: str, cells: list[CellSpec]) -> dict[str, Any]:
    seen_candidates:set[int]=set(); all_entries=[]; cycle_candidates=[]; cell_summaries=[]; started=time.perf_counter_ns()
    for cell in cells:
        lengths=[]; maxints=[]; outcomes={"reached_one":0,"repeated_state":0,"interrupted":0}; rec_first=[]; rec_odd=[]; rec_band=[]; rec_res=[]; entries=[]; cstart=time.perf_counter_ns()
        for record in _single_parent_records(cell, seed):
            assert isinstance(record, CandidateRecord)
            _validate_candidate_record(record, cell.validation_strategy)
            if record.candidate in seen_candidates: raise ValueError("adaptive pilot generated duplicate candidate")
            seen_candidates.add(record.candidate)
            t0=time.perf_counter_ns(); result, rec=evaluate_with_recurrence(record.candidate); rt=(time.perf_counter_ns()-t0)/1e9
            outcomes[result.outcome]+=1
            if result.outcome in COMPLETED_OUTCOMES:
                lengths.append(result.total_steps_executed); maxints.append(result.maximum_integer)
            entry={"starting_integer":str(record.candidate),"total_unaccelerated_trajectory_length":result.total_steps_executed,"maximum_integer_reached":str(result.maximum_integer),"outcome":result.outcome,"runtime_seconds":rt,"strategy":ADAPTIVE_STRATEGY,"experiment_id":pilot_id,"cell_id":cell.cell_id,"family":cell.family,**record.metadata()}
            entries.append(entry); all_entries.append(entry)
            rec_first.append(rec["first_descent_step"] or result.total_steps_executed); rec_odd.append(rec["odd_step_density"]); rec_band.append(rec["same_decimal_digit_band_returns"]); rec_res.append(rec["repeated_residue_hits_mod_2_64_minus_59"])
            if result.outcome=="repeated_state": cycle_candidates.append(entry)
        elapsed=(time.perf_counter_ns()-cstart)/1e9
        summary={"cell_id":cell.cell_id,"family":cell.family,"source_parent":str(cell.parent),"parent_rank":cell.parent_rank,"parameters":cell.parameters(),"candidates_evaluated":cell.count,"reached_one_count":outcomes["reached_one"],"repeated_state_count":outcomes["repeated_state"],"interrupted_count":outcomes["interrupted"],"mean_trajectory_length":statistics.fmean(lengths),"median_trajectory_length":statistics.median(lengths),"p90_trajectory_length":_percentile(lengths,.90),"p99_trajectory_length":_percentile(lengths,.99) if len(lengths)>=100 else None,"maximum_trajectory_length":max(lengths),"maximum_integer_reached":str(max(maxints)),"runtime_seconds":elapsed,"trajectories_per_second":cell.count/elapsed,"threshold_exceedance_counts":{f"ge_{t}":sum(v>=t for v in lengths) for t in THRESHOLDS},"overall_pilot_top_tail_count":0,"mean_first_descent_step":statistics.fmean(rec_first),"mean_odd_step_density":statistics.fmean(rec_odd),"mean_same_decimal_digit_band_returns":statistics.fmean(rec_band),"mean_repeated_residue_hits_mod_2_64_minus_59":statistics.fmean(rec_res)}
        summary["selection_score"]=score_cell(summary); cell_summaries.append(summary)
    elapsed=(time.perf_counter_ns()-started)/1e9; lengths=[e["total_unaccelerated_trajectory_length"] for e in all_entries]
    top_10=sorted(all_entries,key=_top_key,reverse=True)[:10]
    tail_cut=sorted(lengths, reverse=True)[:max(1, len(lengths)//10)][-1]
    tail_counts={}
    for e in all_entries:
        if e["total_unaccelerated_trajectory_length"] >= tail_cut:
            tail_counts[e["cell_id"]]=tail_counts.get(e["cell_id"],0)+1
    for summary in cell_summaries:
        summary["overall_pilot_top_tail_count"] = tail_counts.get(summary["cell_id"], 0)
        summary["selection_score"] = score_cell(summary)
    scoring={"formula":"p90 + 0.5*p99_or_0 + 100*count(length>=26000) + 250*repeated_state_count - 0.01*mean_first_descent_step","diversity_rule":"Stage B keeps the top three scored cells and adds the best missing family when needed."}
    result={"pilot_id":pilot_id,"strategy":ADAPTIVE_STRATEGY,"seed":seed,"candidates_evaluated":len(all_entries),"distinct_candidates":len(seen_candidates),"reached_one_count":sum(e["outcome"]=="reached_one" for e in all_entries),"repeated_state_count":sum(e["outcome"]=="repeated_state" for e in all_entries),"interrupted_count":sum(e["outcome"]=="interrupted" for e in all_entries),"mean_trajectory_length":statistics.fmean(lengths),"median_trajectory_length":statistics.median(lengths),"p90_trajectory_length":_percentile(lengths,.90),"p99_trajectory_length":_percentile(lengths,.99),"maximum_trajectory_length":max(lengths),"total_wall_time_seconds":elapsed,"trajectories_per_second":len(all_entries)/elapsed,"thresholds":list(THRESHOLDS),"cell_scoring_rule":scoring,"cell_summaries":cell_summaries,"top_10":top_10,"cycle_candidates":cycle_candidates}
    out=output_root/"results"/pilot_id; out.mkdir(parents=True,exist_ok=True)
    (out/"summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    (out/"top_10.json").write_text(json.dumps(top_10,indent=2,sort_keys=True)+"\n")
    lines=[f"# {pilot_id}","",f"Strategy: `{ADAPTIVE_STRATEGY}`; candidates: {len(all_entries):,}; seed `{seed}`.","", "## Cell summaries"]
    for s in sorted(cell_summaries,key=lambda x:-x["selection_score"]):
        lines.append(f"- `{s['cell_id']}` ({s['family']}): n={s['candidates_evaluated']}, mean={s['mean_trajectory_length']:.2f}, p90={s['p90_trajectory_length']:.1f}, p99={s['p99_trajectory_length']}, max={s['maximum_trajectory_length']}, score={s['selection_score']:.2f}, repeated={s['repeated_state_count']}")
    lines += ["", "## Top 10", "", "| Start (abbreviated) | Cell | Family | Length | Maximum (abbreviated) |", "| --- | --- | --- | ---: | --- |"]
    for e in top_10: lines.append(f"| `{_abbreviate(e['starting_integer'])}` | `{e['cell_id']}` | {e['family']} | {e['total_unaccelerated_trajectory_length']} | `{_abbreviate(e['maximum_integer_reached'])}` |")
    (out/"summary.md").write_text("\n".join(lines)+"\n")
    return result


def load_default_parents(output_root: Path) -> list[int]:
    return load_global_top_10(output_root/"results"/"global_top_10.json")
