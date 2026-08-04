"""Adaptive cross-family pilot runner with shared exact evaluator."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from fractions import Fraction
import json, math, statistics, time
from pathlib import Path
from typing import Any, Callable, Iterable
from .cycle import reconstruct_cycle, verify_cycle_independently
from .evaluator import evaluate_with_metrics, RecurrenceMetrics, MetricEvaluation
from .experiment import _percentile, _persist_cycle_candidates, _cycle_candidate_record, STRATEGY_VALIDATION_MODES, _validate_candidate_record
from .generator import CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY, parity_prefix_candidate_records, decimal_suffix_candidate_records, residue_candidate_records, load_global_top_10

FAMILY_MAP={"parity-prefix":(S1_STRATEGY,"parity_prefix"),"decimal-suffix":(S5_STRATEGY,"decimal_suffix"),"residue":(S6_STRATEGY,"residue")}

@dataclass(frozen=True)
class AdaptiveCell:
    cell_id:str; family:str; strategy:str; validation_mode:str; source_parent:int; parent_rank:int; candidate_count:int; parameters:dict[str,Any]

class NontrivialCycleFound(RuntimeError): pass
class CycleVerificationFailed(RuntimeError): pass

def validate_cell(cell:AdaptiveCell)->None:
    if cell.family not in FAMILY_MAP: raise ValueError("unknown family")
    strategy,mode=FAMILY_MAP[cell.family]
    if (cell.strategy,cell.validation_mode)!=(strategy,mode): raise ValueError("wrong strategy or validation mode")
    if not cell.cell_id or cell.source_parent is None or cell.parent_rank<1 or cell.candidate_count<1: raise ValueError("incomplete metadata")
    if len(str(cell.source_parent))!=1000: raise ValueError("source parent must be 1000 digits")
    if cell.family=="parity-prefix" and not isinstance(cell.parameters.get("prefix_length"),int): raise ValueError("malformed parameters")
    if cell.family=="decimal-suffix" and not isinstance(cell.parameters.get("suffix_digits"),int): raise ValueError("malformed parameters")
    if cell.family=="residue" and not isinstance(cell.parameters.get("residue_modulus"),int): raise ValueError("malformed parameters")

def records_for_cell(cell:AdaptiveCell, seed:str)->Iterable[CandidateRecord]:
    validate_cell(cell)
    if cell.family=="parity-prefix":
        return (CandidateRecord(item[0], cell.strategy, cell.validation_mode, parent=item[1], prefix_length=(item[2] if len(item) == 3 else cell.parameters["prefix_length"])) for item in parity_prefix_candidate_records(cell.candidate_count,[cell.source_parent],seed+":"+cell.cell_id,cell.parameters["prefix_length"]))
    if cell.family=="decimal-suffix": return decimal_suffix_candidate_records(cell.candidate_count,[cell.source_parent],seed+":"+cell.cell_id,cell.parameters["suffix_digits"])
    return residue_candidate_records(cell.candidate_count,[cell.source_parent],seed+":"+cell.cell_id,cell.parameters["residue_modulus"])

def aggregate_metrics(metrics:list[RecurrenceMetrics])->dict[str,Any]:
    if not metrics: return {}
    defined=[m.first_descent_step for m in metrics if m.first_descent_step is not None]
    max_metric=max(metrics, key=lambda m: Fraction(m.maximum_excursion_numerator,m.maximum_excursion_denominator))
    return {"mean_odd_step_count":statistics.fmean(m.odd_step_count for m in metrics),"mean_odd_step_density":statistics.fmean(m.odd_step_density for m in metrics),"mean_first_descent_step":statistics.fmean(defined) if defined else None,"undefined_first_descent_count":len(metrics)-len(defined),"maximum_excursion_numerator":str(max_metric.maximum_excursion_numerator),"maximum_excursion_denominator":str(max_metric.maximum_excursion_denominator),"mean_same_decimal_digit_band_return_count":statistics.fmean(m.same_decimal_digit_band_return_count for m in metrics),"mean_repeated_residue_hit_count":statistics.fmean(m.repeated_residue_hit_count for m in metrics),"residue_modulus":metrics[0].residue_modulus}

def assign_top_tail(cell_lengths:dict[str,list[int]], fraction:float=.10)->dict[str,int]:
    entries=[(l,c,i) for c,ls in cell_lengths.items() for i,l in enumerate(ls)]
    if not entries: return {c:0 for c in cell_lengths}
    k=max(1,math.ceil(len(entries)*fraction))
    chosen=sorted(entries,key=lambda x:(-x[0],x[1],x[2]))[:k]
    out={c:0 for c in cell_lengths}
    for _,c,_ in chosen: out[c]+=1
    return out

def score_cell(summary:dict[str,Any])->float:
    m=summary.get("recurrence_metric_aggregates") or {}
    return round((summary.get("mean_trajectory_length") or 0)*1.0 + (summary.get("p90_trajectory_length") or 0)*0.25 + (summary.get("p99_trajectory_length") or 0)*0.1 + summary.get("overall_top_tail_count",0)*100 + m.get("mean_repeated_residue_hit_count",0)*0.5 + m.get("mean_odd_step_density",0)*50 + summary.get("repeated_state_count",0)*1000, 12)

def allocate_stage_b(cell_scores:list[tuple[str,float]], total:int, minimum:int=1)->dict[str,int]:
    if not cell_scores or total<1: raise ValueError("no cells or total")
    n=len(cell_scores)
    if minimum*n>total: raise ValueError("minimum quota infeasible")
    base={cid:minimum for cid,_ in cell_scores}; remaining=total-minimum*n
    weights=[max(0.0,s) for _,s in cell_scores]
    if sum(weights)==0: weights=[1.0]*n
    totalw=sum(weights); floors=[]
    for (cid,_),w in zip(cell_scores,weights):
        exact=remaining*w/totalw; add=math.floor(exact); base[cid]+=add; floors.append((exact-add,cid))
    left=total-sum(base.values())
    for _,cid in sorted(floors,key=lambda x:(-x[0],x[1]))[:left]: base[cid]+=1
    return base

def _discovery(output_root:Path,pilot_id:str,cell:AdaptiveCell,seed:str,record:CandidateRecord,me:MetricEvaluation)->None:
    members=reconstruct_cycle(record.candidate,me.result)
    verification=verify_cycle_independently(record.candidate,me.result,members)
    cycle_record=_cycle_candidate_record(result=me.result,candidate=record.candidate,experiment_id=pilot_id,strategy=cell.strategy,metadata=record.metadata())
    cycle_record["cycle_members"]=[str(x) for x in verification.cycle_members or members]
    cycle_record["independent_replay_confirmed"]=verification.confirmed
    _persist_cycle_candidates(output_root,[cycle_record])
    if not verification.confirmed: raise CycleVerificationFailed(verification.failure or "verification failed")
    artifact={**cycle_record,"pilot_id":pilot_id,"deterministic_seed":seed,"cell_id":cell.cell_id,"family":cell.family,"generation_parameters":cell.parameters,"source_metadata":{"parent_starting_integer":str(cell.source_parent),"parent_rank":cell.parent_rank},"validation_mode":cell.validation_mode}
    (output_root/"results").mkdir(exist_ok=True,parents=True)
    (output_root/"results/nontrivial_cycle_discovery.json").write_text(json.dumps(artifact,indent=2,sort_keys=True)+"\n")
    (output_root/"NONTRIVIAL_CYCLE_FOUND.md").write_text(f"# Nontrivial cycle found\n\nPilot `{pilot_id}` cell `{cell.cell_id}`.\n")
    raise NontrivialCycleFound()

def run_adaptive_pilot(output_root:Path,*,pilot_id:str,cells:list[AdaptiveCell],seed:str,evaluator:Callable[...,MetricEvaluation]=evaluate_with_metrics)->dict[str,Any]:
    before=(output_root/"results/global_top_10.json").read_bytes() if (output_root/"results/global_top_10.json").exists() else b""
    seen=set(); per={c.cell_id:[] for c in cells}; mets={c.cell_id:[] for c in cells}; outcomes={c.cell_id:{"reached_one":0,"repeated_state":0,"interrupted":0} for c in cells}; evaluated=0; start=time.perf_counter()
    for cell in cells:
        validate_cell(cell)
        for record in records_for_cell(cell,seed):
            _validate_candidate_record(record,cell.strategy)
            if record.parent != cell.source_parent: raise ValueError("incorrect source parent")
            if len(str(record.candidate))!=1000: raise ValueError("non-1000-digit candidate")
            if record.candidate in seen: raise ValueError("duplicate candidate across pilot")
            seen.add(record.candidate)
            me=evaluator(record.candidate)
            evaluated+=1; outcomes[cell.cell_id][me.result.outcome]+=1; mets[cell.cell_id].append(me.metrics)
            if me.result.outcome=="repeated_state":
                if int(me.result.repeated_integer)==1: continue
                _discovery(output_root,pilot_id,cell,seed,record,me)
            if me.result.outcome in {"reached_one","repeated_state"}: per[cell.cell_id].append(me.result.total_steps_executed)
    tails=assign_top_tail(per); summaries=[]
    for cell in cells:
        ls=per[cell.cell_id]; agg=aggregate_metrics(mets[cell.cell_id])
        s={"cell_id":cell.cell_id,"family":cell.family,"strategy":cell.strategy,"validation_mode":cell.validation_mode,"source_parent":str(cell.source_parent),"parent_rank":cell.parent_rank,"candidate_count":cell.candidate_count,"candidates_evaluated":sum(outcomes[cell.cell_id].values()),"outcome_counts":outcomes[cell.cell_id],"reached_one_count":outcomes[cell.cell_id]["reached_one"],"repeated_state_count":outcomes[cell.cell_id]["repeated_state"],"interrupted_count":outcomes[cell.cell_id]["interrupted"],"mean_trajectory_length":statistics.fmean(ls) if ls else None,"p90_trajectory_length":_percentile(ls,.9) if ls else None,"p99_trajectory_length":_percentile(ls,.99) if ls else None,"maximum_trajectory_length":max(ls) if ls else None,"overall_top_tail_count":tails[cell.cell_id],"recurrence_metric_aggregates":agg,"parameters":cell.parameters}
        s["deterministic_score"]=score_cell(s); summaries.append(s)
    elapsed=time.perf_counter()-start
    result={"pilot_id":pilot_id,"pilot":True,"deterministic_seed":seed,"distinct_candidate_count":len(seen),"total_evaluated_candidates":evaluated,"top_tail_definition":"highest ceil(10%) by length; ties by cell_id then cell-local order","cells":summaries,"runtime_seconds":elapsed,"trajectories_per_second":evaluated/elapsed if elapsed else None}
    out=output_root/"results"/pilot_id; out.mkdir(parents=True,exist_ok=True); (out/"summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    after=(output_root/"results/global_top_10.json").read_bytes() if (output_root/"results/global_top_10.json").exists() else b""
    if before!=after: raise RuntimeError("global_top_10 isolation violated")
    return result

def default_stage_a_cells(output_root:Path,count_per_cell:int=100)->list[AdaptiveCell]:
    parents=load_global_top_10(output_root/"results/global_top_10.json")[:3]
    return [AdaptiveCell("A-parity","parity-prefix",S1_STRATEGY,"parity_prefix",parents[0],1,count_per_cell,{"prefix_length":256}),AdaptiveCell("A-suffix","decimal-suffix",S5_STRATEGY,"decimal_suffix",parents[1],2,count_per_cell,{"suffix_digits":64}),AdaptiveCell("A-residue","residue",S6_STRATEGY,"residue",parents[2],3,count_per_cell,{"residue_modulus":2**128+1})]
