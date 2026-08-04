"""Small sequential experiment runner."""

from __future__ import annotations

import heapq
import json
import statistics
import time
from pathlib import Path
from typing import Any

from .evaluator import evaluate
from .generator import baseline_candidates

DEFAULT_CANDIDATE_COUNT = 10_000
STRATEGY = "S0-uniform-deterministic"


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
        start = entry["starting_integer"]
        if start not in deduplicated or _top_key(entry) > _top_key(deduplicated[start]):
            deduplicated[start] = entry
    global_top = sorted(deduplicated.values(), key=_top_key, reverse=True)[:10]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(global_top, indent=2, sort_keys=True) + "\n")
    return global_top


def run_experiment(
    output_root: Path,
    *,
    experiment_id: str,
    count: int = DEFAULT_CANDIDATE_COUNT,
    seed: str = "baseline-v1",
) -> dict[str, Any]:
    """Evaluate distinct 1000-digit candidates and retain statistics and two top tens."""
    if not experiment_id or Path(experiment_id).name != experiment_id:
        raise ValueError("experiment_id must be a nonempty path-safe name")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("count must be a positive integer")

    parameters = {"seed": seed, "decimal_digits": 1000}
    lengths: list[int] = []
    outcomes = {"reached_one": 0, "repeated_state": 0, "interrupted": 0}
    top_heap: list[tuple[tuple[int, int], dict[str, Any]]] = []
    started = time.perf_counter_ns()

    for candidate in baseline_candidates(count, seed=seed):
        trajectory_started = time.perf_counter_ns()
        result = evaluate(candidate)
        runtime_ns = time.perf_counter_ns() - trajectory_started
        lengths.append(result.total_steps_executed)
        outcomes[result.outcome] += 1
        entry = {
            "starting_integer": str(candidate),
            "total_unaccelerated_trajectory_length": result.total_steps_executed,
            "maximum_integer_reached": str(result.maximum_integer),
            "outcome": result.outcome,
            "runtime_seconds": runtime_ns / 1e9,
            "strategy": STRATEGY,
            "experiment_id": experiment_id,
        }
        keyed = (_top_key(entry), entry)
        if len(top_heap) < 10:
            heapq.heappush(top_heap, keyed)
        elif keyed[0] > top_heap[0][0]:
            heapq.heapreplace(top_heap, keyed)

    elapsed_seconds = (time.perf_counter_ns() - started) / 1e9
    top_10 = [entry for _, entry in sorted(top_heap, reverse=True)]
    summary = {
        "experiment_id": experiment_id,
        "strategy": {"name": STRATEGY, "parameters": parameters},
        "candidates_evaluated": count,
        "reached_one_count": outcomes["reached_one"],
        "repeated_state_count": outcomes["repeated_state"],
        "interrupted_count": outcomes["interrupted"],
        "mean_trajectory_length": statistics.fmean(lengths),
        "median_trajectory_length": statistics.median(lengths),
        "p90_trajectory_length": _percentile(lengths, .90),
        "p99_trajectory_length": _percentile(lengths, .99),
        "maximum_trajectory_length": max(lengths),
        "total_wall_time_seconds": elapsed_seconds,
        "trajectories_per_second": count / elapsed_seconds,
    }

    result_dir = output_root / "results" / experiment_id
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (result_dir / "top_10.json").write_text(json.dumps(top_10, indent=2, sort_keys=True) + "\n")
    lines = [
        f"# {experiment_id}", "", f"Strategy: `{STRATEGY}`; candidates: {count:,} (all 1000 digits).", "",
        "## Statistics", "", f"- Mean: {summary['mean_trajectory_length']:.3f}",
        f"- Median: {summary['median_trajectory_length']}", f"- P90: {summary['p90_trajectory_length']}",
        f"- P99: {summary['p99_trajectory_length']}", f"- Maximum: {summary['maximum_trajectory_length']}", "",
        "## Top 10", "", "| Start (abbreviated) | Length | Maximum (abbreviated) | Outcome | Runtime (s) |",
        "| --- | ---: | --- | --- | ---: |",
    ]
    for entry in top_10:
        lines.append(f"| `{_abbreviate(entry['starting_integer'])}` | {entry['total_unaccelerated_trajectory_length']} | "
                     f"`{_abbreviate(entry['maximum_integer_reached'])}` | {entry['outcome']} | {entry['runtime_seconds']:.6f} |")
    lines += ["", "## Best starting integer (complete)", "", "```text", top_10[0]["starting_integer"], "```", ""]
    (result_dir / "summary.md").write_text("\n".join(lines))
    global_top = _update_global(output_root, top_10)
    return {"summary": summary, "top_10": top_10, "global_top_10": global_top}
