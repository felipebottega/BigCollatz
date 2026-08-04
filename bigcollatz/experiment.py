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
    DEFAULT_PREFIX_LENGTH, S0_STRATEGY, S1_STRATEGY, S2_STRATEGY, S3_STRATEGY, S4_STRATEGY, S5_STRATEGY, S6_STRATEGY,
    DECIMAL_SUFFIX_STRATEGIES, LINEAGE_STRATEGIES, RESIDUE_STRATEGIES, CandidateRecord, balanced_allocation,
    baseline_candidates, binary_nearby_residue_candidate_records, decimal_suffix_candidate_records,
    load_global_top_10, load_lineage_weights, parity_prefix_candidate_records,
    mixed_prefix_candidate_records, validate_decimal_suffix, validate_parity_prefix, validate_residue,
    weighted_allocation, weighted_parity_prefix_candidate_records,
)

DEFAULT_CANDIDATE_COUNT = 10_000
STRATEGY = S0_STRATEGY
SUPPORTED_STRATEGIES = (S0_STRATEGY, S1_STRATEGY, S2_STRATEGY, S3_STRATEGY, S4_STRATEGY, S5_STRATEGY, S6_STRATEGY)
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
    metadata: CandidateRecord | None = None, parent: int | None = None, prefix_length: int | None = None,
) -> dict[str, Any]:
    cycle_record = {
        "starting_integer": str(candidate),
        "repeated_integer": result.repeated_integer,
        "first_seen_step": result.first_seen_step,
        "repeated_at_step": result.repeated_at_step,
        "cycle_length": result.cycle_length,
        "experiment_id": experiment_id,
        "strategy": strategy,
    }
    if strategy in LINEAGE_STRATEGIES:
        cycle_record["parent_starting_integer"] = str(parent)
        cycle_record["prefix_length"] = prefix_length
    if strategy in DECIMAL_SUFFIX_STRATEGIES and metadata is not None:
        cycle_record["parent_starting_integer"] = str(metadata.parent)
        cycle_record["suffix_digits"] = metadata.suffix_digits
        cycle_record["validation_mode"] = metadata.validation_mode
        cycle_record["source_metadata"] = metadata.source_metadata
    if strategy in RESIDUE_STRATEGIES and metadata is not None:
        cycle_record["parent_starting_integer"] = str(metadata.parent)
        cycle_record["residue_modulus"] = metadata.residue_modulus
        cycle_record["residue"] = metadata.residue
        cycle_record["validation_mode"] = metadata.validation_mode
        cycle_record["source_metadata"] = metadata.source_metadata
    return cycle_record


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
    elif strategy == S4_STRATEGY:
        source = output_root / "results" / "global_top_10.json"
        parents = load_global_top_10(source)
        prefix_lengths = (128, 256, 384)
        pair_count = len(parents) * len(prefix_lengths)
        allocation = balanced_allocation(count, list(range(pair_count)))
        parameters.update({
            "source_global_top_10_file": "results/global_top_10.json",
            "prefix_lengths": list(prefix_lengths),
            "number_of_parents_used": len(parents),
            "deterministic_seed": seed,
            "allocation_per_parent_prefix": [
                {"parent": str(parent), "prefix_length": prefix, "candidate_count": allocated}
                for (parent, prefix), allocated in zip(
                    [(parent, prefix) for parent in parents for prefix in prefix_lengths], allocation
                )
            ],
        })
        candidate_records = mixed_prefix_candidate_records(count, parents, seed, prefix_lengths)
    elif strategy == S5_STRATEGY:
        source = output_root / "results" / "global_top_10.json"
        parents = load_global_top_10(source)
        suffix_digits = 24
        allocation = balanced_allocation(count, parents)
        parameters.update({
            "source_global_top_10_file": "results/global_top_10.json",
            "suffix_digits": suffix_digits,
            "number_of_parents_used": len(parents),
            "deterministic_seed": seed,
            "allocation_per_parent": [
                {"parent": str(parent), "candidate_count": allocated}
                for parent, allocated in zip(parents, allocation)
            ],
        })
        candidate_records = decimal_suffix_candidate_records(count, parents, seed, suffix_digits)
    elif strategy == S6_STRATEGY:
        source = output_root / "results" / "global_top_10.json"
        parents = load_global_top_10(source)
        modulus_bits = 20
        radius = 3
        cells = len(parents) * (2 * radius)
        allocation = balanced_allocation(count, list(range(cells)))
        parameters.update({
            "source_global_top_10_file": "results/global_top_10.json",
            "modulus_bits": modulus_bits,
            "residue_modulus": 1 << modulus_bits,
            "radius": radius,
            "number_of_parents_used": len(parents),
            "deterministic_seed": seed,
            "allocation_per_parent_delta_cell": allocation,
        })
        candidate_records = binary_nearby_residue_candidate_records(count, parents, seed, modulus_bits, radius)
    elif strategy in (S2_STRATEGY, S3_STRATEGY):
        if strategy == S2_STRATEGY:
            source_relative = "results/e002-s1-parity-prefix-256/top_10.json"
            source = output_root / "results" / "e002-s1-parity-prefix-256" / "top_10.json"
            parent_weights = load_lineage_weights(source, prefix_length)
            generator_domain = S2_STRATEGY
        else:
            source_relative = "results/e003-s2-weighted-lineages-256/top_10.json"
            source = output_root / "results" / "e003-s2-weighted-lineages-256" / "top_10.json"
            parent_weights = load_lineage_weights(
                source, prefix_length, expected_strategy=S2_STRATEGY,
                expected_experiment_id="e003-s2-weighted-lineages-256",
                completed_outcomes=COMPLETED_OUTCOMES,
            )
            generator_domain = S3_STRATEGY
        allocation = weighted_allocation(count, [weight for _, weight in parent_weights])
        parameters.update({
            "source_top_10_file": source_relative,
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
            count, parent_weights, seed, prefix_length, generator_domain
        )
    else:
        candidate_records = ((candidate, None) for candidate in baseline_candidates(count, seed=seed))
    lengths: list[int] = []
    outcomes = {"reached_one": 0, "repeated_state": 0, "interrupted": 0}
    top_heap: list[tuple[tuple[int, int], dict[str, Any]]] = []
    cycle_candidates: list[dict[str, Any]] = []
    started = time.perf_counter_ns()

    for raw_record in candidate_records:
        metadata: CandidateRecord | None = None
        if isinstance(raw_record, CandidateRecord):
            metadata = raw_record
            candidate = raw_record.candidate
            parent = raw_record.parent
            candidate_prefix_length = raw_record.prefix_length
        elif len(raw_record) == 3:
            candidate, parent, candidate_prefix_length = raw_record
        else:
            candidate, parent = raw_record
            candidate_prefix_length = prefix_length
        if validate_candidates:
            if metadata is not None:
                if metadata.validation_mode == "decimal_suffix":
                    if metadata.parent is None or metadata.suffix_digits is None:
                        raise ValueError("decimal suffix candidate metadata is incomplete")
                    if not validate_decimal_suffix(candidate, metadata.parent, metadata.suffix_digits):
                        raise ValueError("generated candidate does not preserve its decimal suffix")
                elif metadata.validation_mode == "residue":
                    if metadata.residue_modulus is None or metadata.residue is None:
                        raise ValueError("residue candidate metadata is incomplete")
                    if not validate_residue(candidate, metadata.residue_modulus, metadata.residue):
                        raise ValueError("generated candidate does not satisfy its residue constraint")
                else:
                    raise ValueError(f"unsupported validation mode: {metadata.validation_mode}")
            elif parent is not None:
                if candidate_prefix_length is None or not validate_parity_prefix(candidate, parent, candidate_prefix_length):
                    raise ValueError("generated candidate does not reproduce its parent's parity prefix")
        trajectory_started = time.perf_counter_ns()
        result = evaluate(candidate)
        runtime_ns = time.perf_counter_ns() - trajectory_started
        outcomes[result.outcome] += 1
        if result.outcome == "repeated_state":
            cycle_candidates.append(_cycle_candidate_record(
                result=result, candidate=candidate, experiment_id=experiment_id,
                strategy=strategy, metadata=metadata, parent=parent, prefix_length=candidate_prefix_length,
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
        if strategy in LINEAGE_STRATEGIES:
            entry["parent_starting_integer"] = str(parent)
            entry["prefix_length"] = candidate_prefix_length
        if strategy in DECIMAL_SUFFIX_STRATEGIES and metadata is not None:
            entry["parent_starting_integer"] = str(metadata.parent)
            entry["suffix_digits"] = metadata.suffix_digits
            entry["validation_mode"] = metadata.validation_mode
            entry["source_metadata"] = metadata.source_metadata
        if strategy in RESIDUE_STRATEGIES and metadata is not None:
            entry["parent_starting_integer"] = str(metadata.parent)
            entry["residue_modulus"] = metadata.residue_modulus
            entry["residue"] = metadata.residue
            entry["validation_mode"] = metadata.validation_mode
            entry["source_metadata"] = metadata.source_metadata
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
                  "Maximum (abbreviated) | Outcome | Runtime (s) |") if strategy in LINEAGE_STRATEGIES or strategy in DECIMAL_SUFFIX_STRATEGIES or strategy in RESIDUE_STRATEGIES else (
                  "| Start (abbreviated) | Length | Maximum (abbreviated) | Outcome | Runtime (s) |")
    top_separator = ("| --- | --- | ---: | --- | --- | ---: |" if strategy in LINEAGE_STRATEGIES or strategy in DECIMAL_SUFFIX_STRATEGIES or strategy in RESIDUE_STRATEGIES
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
                       if strategy in LINEAGE_STRATEGIES or strategy in DECIMAL_SUFFIX_STRATEGIES or strategy in RESIDUE_STRATEGIES else "")
        lines.append(f"| `{_abbreviate(entry['starting_integer'])}` | {parent_cell}{entry['total_unaccelerated_trajectory_length']} | "
                     f"`{_abbreviate(entry['maximum_integer_reached'])}` | {entry['outcome']} | {entry['runtime_seconds']:.6f} |")
    if top_10:
        lines += ["", "## Best starting integer (complete)", "", "```text", top_10[0]["starting_integer"], "```", ""]
    (result_dir / "summary.md").write_text("\n".join(lines))
    _persist_cycle_candidates(output_root, cycle_candidates)
    global_top = _update_global(output_root, top_10)
    return {"summary": summary, "top_10": top_10, "global_top_10": global_top}
