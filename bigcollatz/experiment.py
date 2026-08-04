"""Small sequential experiment runner."""

from __future__ import annotations

import heapq
import json
import statistics
import time
from pathlib import Path
from typing import Any

from .evaluator import evaluate
from .generator import (
    DEFAULT_PREFIX_LENGTH, S0_STRATEGY, S1_STRATEGY, S2_STRATEGY, balanced_allocation,
    baseline_candidates, load_global_top_10, load_lineage_weights, parity_prefix_candidate_records,
    validate_parity_prefix, weighted_allocation, weighted_parity_prefix_candidate_records,
)

DEFAULT_CANDIDATE_COUNT = 10_000
STRATEGY = S0_STRATEGY
SUPPORTED_STRATEGIES = (S0_STRATEGY, S1_STRATEGY, S2_STRATEGY)
COMPLETED_OUTCOMES = frozenset(("reached_one", "repeated_state"))


def _percentile(values: list[int], p: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lower = int(position)
    fraction = position - lower
    return ordered[lower] if not fraction else ordered[lower] + fraction * (ordered[lower + 1] - ordered[lower])


def _abbreviate(value: str, width: int = 16) -> str:
    return value if len(value) <= width * 2 else f"{value[:width]}…{value[-width:]}"


def _top_key(entry: dict[str, Any]) -> tuple[int, int]:
    return entry["total_unaccelerated_trajectory_length"], int(entry["starting_integer"])


def _update_global(output_root: Path, current: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = output_root / "results" / "global_top_10.json"
    existing = json.loads(path.read_text()) if path.exists() else []
    deduplicated: dict[str, dict[str, Any]] = {}
    for entry in existing + current:
        if entry.get("outcome") not in COMPLETED_OUTCOMES:
            continue
        start = entry["starting_integer"]
        if start not in deduplicated or _top_key(entry) > _top_key(deduplicated[start]):
            deduplicated[start] = entry
    global_top = sorted(deduplicated.values(), key=_top_key, reverse=True)[:10]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(global_top, indent=2, sort_keys=True) + "\n")
    return global_top


def _cycle_candidate_record(
    *, result: Any, candidate: int, experiment_id: str, strategy: str,
    parent: int | None, prefix_length: int,
) -> dict[str, Any]:
    record = {
        "starting_integer": str(candidate),
        "repeated_integer": result.repeated_integer,
        "first_seen_step": result.first_seen_step,
        "repeated_at_step": result.repeated_at_step,
        "cycle_length": result.cycle_length,
        "experiment_id": experiment_id,
        "strategy": strategy,
    }
    if strategy in (S1_STRATEGY, S2_STRATEGY):
        record["parent_starting_integer"] = str(parent)
        record["prefix_length"] = prefix_length
    return record


def _persist_cycle_candidates(output_root: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    path = output_root / "results" / "cycle_candidates.json"
    existing = json.loads(path.read_text()) if path.exists() else []
    deduplicated: dict[tuple[str, int], dict[str, Any]] = {}
    for record in existing + records:
        deduplicated[(record["repeated_integer"], record["cycle_length"])] = record
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(deduplicated.values()), indent=2, sort_keys=True) + "\n")


def run_experiment(
    output_root: Path,
    *,
    experiment_id: str,
    count: int = DEFAULT_CANDIDATE_COUNT,
    seed: str = "baseline-v1",
    strategy: str = S0_STRATEGY,
    prefix_length: int = DEFAULT_PREFIX_LENGTH,
    validate_candidates: bool = False,
) -> dict[str, Any]:
    """Evaluate distinct 1000-digit candidates and retain statistics and two top tens."""
    if not experiment_id or Path(experiment_id).name != experiment_id:
        raise ValueError("experiment_id must be a nonempty path-safe name")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("count must be a positive integer")
    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError(f"unsupported strategy: {strategy}")

    parameters = {"seed": seed, "decimal_digits": 1000}
    if strategy == S1_STRATEGY:
        source = output_root / "results" / "global_top_10.json"
        parents = load_global_top_10(source)
        allocation = balanced_allocation(count, parents)
        parameters.update({
            "prefix_length": prefix_length,
            "source_global_top_10_file": "results/global_top_10.json",
            "number_of_parents_used": len(parents),
            "deterministic_seed": seed,
            "allocation_per_parent": [
                {"parent": str(parent), "candidate_count": allocated}
                for parent, allocated in zip(parents, allocation)
            ],
        })
        candidate_records = parity_prefix_candidate_records(count, parents, seed, prefix_length)
    elif strategy == S2_STRATEGY:
        source = output_root / "results" / "e002-s1-parity-prefix-256" / "top_10.json"
        parent_weights = load_lineage_weights(source, prefix_length)
        allocation = weighted_allocation(count, [weight for _, weight in parent_weights])
        parameters.update({
            "source_top_10_file": "results/e002-s1-parity-prefix-256/top_10.json",
            "prefix_length": prefix_length,
            "deterministic_seed": seed,
            "number_of_productive_parent_lineages": len(parent_weights),
            "lineage_weights": [
                {"parent": str(parent), "weight": weight}
                for parent, weight in parent_weights
            ],
            "allocation_per_parent": [
                {"parent": str(parent), "weight": weight, "candidate_count": allocated}
                for (parent, weight), allocated in zip(parent_weights, allocation)
            ],
        })
        candidate_records = weighted_parity_prefix_candidate_records(
            count, parent_weights, seed, prefix_length
        )
    else:
        candidate_records = ((candidate, None) for candidate in baseline_candidates(count, seed=seed))
    lengths: list[int] = []
    outcomes = {"reached_one": 0, "repeated_state": 0, "interrupted": 0}
    top_heap: list[tuple[tuple[int, int], dict[str, Any]]] = []
    cycle_candidates: list[dict[str, Any]] = []
    started = time.perf_counter_ns()

    for candidate, parent in candidate_records:
        if validate_candidates and parent is not None and not validate_parity_prefix(
                candidate, parent, prefix_length):
            raise ValueError("generated candidate does not reproduce its parent's parity prefix")
        trajectory_started = time.perf_counter_ns()
        result = evaluate(candidate)
        runtime_ns = time.perf_counter_ns() - trajectory_started
        outcomes[result.outcome] += 1
        if result.outcome == "repeated_state":
            cycle_candidates.append(_cycle_candidate_record(
                result=result, candidate=candidate, experiment_id=experiment_id,
                strategy=strategy, parent=parent, prefix_length=prefix_length,
            ))
        if result.outcome not in COMPLETED_OUTCOMES:
            continue
        lengths.append(result.total_steps_executed)
        entry = {
            "starting_integer": str(candidate),
            "total_unaccelerated_trajectory_length": result.total_steps_executed,
            "maximum_integer_reached": str(result.maximum_integer),
            "outcome": result.outcome,
            "runtime_seconds": runtime_ns / 1e9,
            "strategy": strategy,
            "experiment_id": experiment_id,
        }
        if strategy in (S1_STRATEGY, S2_STRATEGY):
            entry["parent_starting_integer"] = str(parent)
            entry["prefix_length"] = prefix_length
        keyed = (_top_key(entry), entry)
        if len(top_heap) < 10:
            heapq.heappush(top_heap, keyed)
        elif keyed[0] > top_heap[0][0]:
            heapq.heapreplace(top_heap, keyed)

    elapsed_seconds = (time.perf_counter_ns() - started) / 1e9
    top_10 = [entry for _, entry in sorted(top_heap, reverse=True)]
    repeated_lengths = [record["cycle_length"] for record in cycle_candidates]
    summary = {
        "experiment_id": experiment_id,
        "strategy": {"name": strategy, "parameters": parameters},
        "candidates_evaluated": count,
        "reached_one_count": outcomes["reached_one"],
        "repeated_state_count": outcomes["repeated_state"],
        "interrupted_count": outcomes["interrupted"],
        "mean_trajectory_length": statistics.fmean(lengths) if lengths else None,
        "median_trajectory_length": statistics.median(lengths) if lengths else None,
        "p90_trajectory_length": _percentile(lengths, .90) if lengths else None,
        "p99_trajectory_length": _percentile(lengths, .99) if lengths else None,
        "maximum_trajectory_length": max(lengths) if lengths else None,
        "total_wall_time_seconds": elapsed_seconds,
        "trajectories_per_second": count / elapsed_seconds,
    }
    if repeated_lengths:
        summary.update(
            nontrivial_cycle_candidate_count=len(repeated_lengths),
            smallest_detected_cycle_length=min(repeated_lengths),
            largest_detected_cycle_length=max(repeated_lengths),
        )

    result_dir = output_root / "results" / experiment_id
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (result_dir / "top_10.json").write_text(json.dumps(top_10, indent=2, sort_keys=True) + "\n")
    top_header = ("| Start (abbreviated) | Parent (abbreviated) | Length | "
                  "Maximum (abbreviated) | Outcome | Runtime (s) |") if strategy in (S1_STRATEGY, S2_STRATEGY) else (
                  "| Start (abbreviated) | Length | Maximum (abbreviated) | Outcome | Runtime (s) |")
    top_separator = ("| --- | --- | ---: | --- | --- | ---: |" if strategy in (S1_STRATEGY, S2_STRATEGY)
                     else "| --- | ---: | --- | --- | ---: |")
    lines = [
        f"# {experiment_id}", "", f"Strategy: `{strategy}`; candidates: {count:,} (all 1000 digits).", "",
        "## Statistics", "", f"- Mean: {summary['mean_trajectory_length']:.3f}" if lengths else "- Mean: null",
        f"- Median: {summary['median_trajectory_length']}", f"- P90: {summary['p90_trajectory_length']}",
        f"- P99: {summary['p99_trajectory_length']}", f"- Maximum: {summary['maximum_trajectory_length']}", "",
        "## Top 10", "", top_header, top_separator,
    ]
    for entry in top_10:
        parent_cell = (f"`{_abbreviate(entry['parent_starting_integer'])}` | "
                       if strategy in (S1_STRATEGY, S2_STRATEGY) else "")
        lines.append(f"| `{_abbreviate(entry['starting_integer'])}` | {parent_cell}{entry['total_unaccelerated_trajectory_length']} | "
                     f"`{_abbreviate(entry['maximum_integer_reached'])}` | {entry['outcome']} | {entry['runtime_seconds']:.6f} |")
    if top_10:
        lines += ["", "## Best starting integer (complete)", "", "```text", top_10[0]["starting_integer"], "```", ""]
    (result_dir / "summary.md").write_text("\n".join(lines))
    _persist_cycle_candidates(output_root, cycle_candidates)
    global_top = _update_global(output_root, top_10)
    return {"summary": summary, "top_10": top_10, "global_top_10": global_top}
