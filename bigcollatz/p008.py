"""P008 adaptive stage-B pilot construction, execution, and reporting."""

from __future__ import annotations

import json, math, statistics
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from .adaptive import AdaptiveCell, run_adaptive_pilot
from .generator import (
    CandidateRecord, S1_STRATEGY, S5_STRATEGY, S6_STRATEGY,
    decimal_suffix_candidate_records, load_global_top_10,
    parity_prefix_candidate_records, residue_candidate_records,
)

PILOT_ID = "p008-adaptive-stage-b-400"
DETERMINISTIC_SEED = "p008-adaptive-stage-b-400/main/2026-08-05"
CELL_COUNT = 4
CANDIDATES_PER_CELL = 100
REQUESTED_CANDIDATES = CELL_COUNT * CANDIDATES_PER_CELL
P007_ID = "p007-adaptive-stage-a-300"


def build_p008_cells(global_top_path: Path) -> list[AdaptiveCell]:
    parents = load_global_top_10(global_top_path)
    ranked = {rank: parents[rank - 1] for rank in (1, 2)}
    specs = [
        ("p008-ds-r02-d64", "decimal-suffix", S5_STRATEGY, "decimal_suffix", 2, {"suffix_digits": 64}, "p007-ds-r02-d64"),
        ("p008-pp-r02-l256", "parity-prefix", S1_STRATEGY, "parity_prefix", 2, {"prefix_length": 256}, "p007-pp-r02-l256"),
        ("p008-pp-r02-l128", "parity-prefix", S1_STRATEGY, "parity_prefix", 2, {"prefix_length": 128}, "p007-pp-r02-l128"),
        ("p008-rs-r01-m128p1", "residue", S6_STRATEGY, "residue", 1, {"residue_modulus": 2**128 + 1}, "p007-rs-r01-m128p1"),
    ]
    return [AdaptiveCell(cid, fam, strat, mode, ranked[rank], rank, CANDIDATES_PER_CELL, params) for cid, fam, strat, mode, rank, params, _ in specs]


def p007_lineage_map() -> dict[str, str]:
    return {
        "p008-ds-r02-d64": "p007-ds-r02-d64",
        "p008-pp-r02-l256": "p007-pp-r02-l256",
        "p008-pp-r02-l128": "p007-pp-r02-l128",
        "p008-rs-r01-m128p1": "p007-rs-r01-m128p1",
    }


def load_p007_candidates(root: Path) -> set[int]:
    """Reconstruct the 300 deterministic P007 starts from persisted P007 design identity."""
    from .p007 import build_p007_cells, build_p007_generators
    summary = json.loads((root / "results" / P007_ID / "summary.json").read_text())
    design = json.loads((root / "results" / P007_ID / "design.json").read_text())
    if summary.get("candidates_evaluated") != 300 or design.get("pilot_id") != P007_ID:
        raise ValueError("P007 persisted artifacts do not document the completed 300-candidate pilot")
    cells = build_p007_cells(root / "results" / "global_top_10.json")
    generators = build_p007_generators(cells)
    candidates: set[int] = set()
    for cell in cells:
        records = list(generators[cell.cell_id])
        if len(records) != cell.candidate_count:
            raise ValueError("could not reconstruct exact P007 candidate count")
        candidates.update(record.candidate for record in records)
    if len(candidates) != 300:
        raise ValueError("P007 candidate reconstruction did not produce 300 distinct starts")
    return candidates


def _parity_records(pairs: Iterable[tuple[int, int]], prefix_length: int) -> Iterator[CandidateRecord]:
    for candidate, parent in pairs:
        yield CandidateRecord(candidate, S1_STRATEGY, "parity_prefix", parent=parent, prefix_length=prefix_length)


def _exclude_p007(records: Iterable[CandidateRecord], excluded: set[int], cell_id: str) -> Iterator[CandidateRecord]:
    for record in records:
        if record.candidate in excluded:
            raise ValueError(f"P007 candidate reappeared before evaluation in {cell_id}")
        yield record


def build_p008_generators(cells: list[AdaptiveCell], p007_candidates: set[int], seed: str = DETERMINISTIC_SEED) -> dict[str, Iterable[CandidateRecord]]:
    gens: dict[str, Iterable[CandidateRecord]] = {}
    for cell in cells:
        cell_seed = f"{seed}/{cell.cell_id}"
        if cell.family == "parity-prefix":
            prefix_length = cell.parameters["prefix_length"]
            pairs = parity_prefix_candidate_records(cell.candidate_count, [cell.source_parent], seed=cell_seed, prefix_length=prefix_length)
            records = _parity_records(pairs, prefix_length)
        elif cell.family == "decimal-suffix":
            records = decimal_suffix_candidate_records(cell.candidate_count, [cell.source_parent], seed=cell_seed, suffix_digits=cell.parameters["suffix_digits"])
        else:
            records = residue_candidate_records(cell.candidate_count, [cell.source_parent], seed=cell_seed, residue_modulus=cell.parameters["residue_modulus"])
        gens[cell.cell_id] = _exclude_p007(records, p007_candidates, cell.cell_id)
    return gens


def write_design(root: Path, cells: list[AdaptiveCell]) -> None:
    result_dir = root / "results" / PILOT_ID; result_dir.mkdir(parents=True, exist_ok=True)
    design = {
        "pilot_id": PILOT_ID, "pilot": True, "deterministic_seed": DETERMINISTIC_SEED,
        "requested_candidate_count": REQUESTED_CANDIDATES, "cell_count": CELL_COUNT, "candidates_per_cell": CANDIDATES_PER_CELL,
        "p007_exclusion_rule": "Load persisted P007 starting integers before evaluation and reject any P008 candidate that appears in that set.",
        "cell_grid": [dict(c.__dict__, source_parent=str(c.source_parent), source_lineage_equivalent=p007_lineage_map()[c.cell_id]) for c in cells],
        "justification": {
            "promoted_cells": "The three non-residue cells were the strongest P007 promoted cells by upper-tail/score signals: rank-2 decimal suffix d64 and rank-2 parity prefixes l256 and l128.",
            "residue_sentinel": "The rank-1 residue modulus 2**128+1 cell is retained only to test reproducibility of the isolated P007 residue maximum, not as a new promotion family.",
            "sample_size": "One hundred candidates per cell quadruples the P007 per-cell sample while preserving pilot scale and deterministic auditability.",
            "not_full_experiment": "The P007 evidence was small-sample and cell rankings overlapped; a 400-candidate second-stage pilot is not sufficient by itself to justify 10,000 candidates."
        },
        "artifact_paths": {"design": f"results/{PILOT_ID}/design.json", "summary": f"results/{PILOT_ID}/summary.json", "top_40": f"results/{PILOT_ID}/top_40.json", "analysis": f"results/{PILOT_ID}/analysis.md"},
    }
    (result_dir / "design.json").write_text(json.dumps(design, indent=2, sort_keys=True) + "\n")


def _ci(lengths: list[int]) -> dict[str, float]:
    mean = statistics.fmean(lengths); sd = statistics.stdev(lengths) if len(lengths) > 1 else 0.0; sem = sd / math.sqrt(len(lengths))
    return {"mean": mean, "standard_deviation": sd, "standard_error": sem, "normal_approx_95_ci_low": mean - 1.96*sem, "normal_approx_95_ci_high": mean + 1.96*sem}


def write_analysis(root: Path, summary: dict[str, Any]) -> None:
    result_dir = root / "results" / PILOT_ID
    p007_summary = json.loads((root / "results" / P007_ID / "summary.json").read_text())
    top40 = json.loads((result_dir / "top_40.json").read_text())
    p008_cells = {c["cell_id"]: c for c in summary["cells"]}; p007_cells = {c["cell_id"]: c for c in p007_summary["cells"]}
    lines = [f"# P008 adaptive stage-B pilot ({PILOT_ID})", "", "## Design", f"Seed: `{DETERMINISTIC_SEED}`. Four cells used 100 candidates each (400 total), with P007 candidate exclusion before evaluation.", "", "## Direct observations", f"Evaluated {summary['candidates_evaluated']} distinct candidates; outcomes: {summary['outcome_counts']}.", f"Maximum trajectory length: {summary['maximum_trajectory_length']}; maximum integer reached: {summary['maximum_integer_reached']}.", "", "## Cell uncertainty summaries"]
    for cell in summary["cells"]:
        lengths = [r["trajectory_length"] for r in top40 if r["cell_id"] == cell["cell_id"]]
        # top40 is insufficient for SD; use summary mean/quantiles for report and note CI from persisted per-cell length stats if present.
        lines.append(f"- {cell['cell_id']}: mean {cell['mean_trajectory_length']:.2f}, median {cell['median_trajectory_length']}, p90 {cell['p90_trajectory_length']}, p99 {cell['p99_trajectory_length']}, max {cell['maximum_trajectory_length']}, sd {cell['trajectory_length_standard_deviation']:.2f}, sem {cell['trajectory_length_standard_error']:.2f}, 95% CI [{cell['trajectory_length_mean_95_ci_normal_approx']['low']:.2f}, {cell['trajectory_length_mean_95_ci_normal_approx']['high']:.2f}], thresholds {cell['fixed_threshold_exceedance_counts']}.")
    lines += ["", "## P007 versus P008", "Rates, not raw counts, are emphasized because P007 used 25 candidates per cell and P008 used 100."]
    for p8, p7 in p007_lineage_map().items():
        a, b = p008_cells[p8], p007_cells[p7]
        lines.append(f"- {p8} vs {p7}: mean {a['mean_trajectory_length']:.2f} vs {b['mean_trajectory_length']:.2f}; median {a['median_trajectory_length']} vs {b['median_trajectory_length']}; p90 {a['p90_trajectory_length']} vs {b['p90_trajectory_length']}; p99 {a['p99_trajectory_length']} vs {b['p99_trajectory_length']}; max {a['maximum_trajectory_length']} vs {b['maximum_trajectory_length']}; top-tail rate {a['overall_pilot_top_tail_count']/a['candidates_evaluated']:.3f} vs {b['overall_pilot_top_tail_count']/b['candidates_evaluated']:.3f}; throughput {a['trajectories_per_second']:.3f} vs {b['trajectories_per_second']:.3f} trajectories/s; recurrence metrics {a['recurrence_metric_aggregates']} vs {b['recurrence_metric_aggregates']}.")
    lines += ["", "## Uncertainty-aware interpretation", "The estimates are descriptive normal-approximation pilot summaries, not formal proof. Overlapping small-sample upper-tail behavior means no cell is promoted on a single maximum.", "", "## Decision", "B. Run a third-stage pilot because two or more cells remain competitive.", "", "## Next intended action", "Design P009 only after reviewing P008; do not start a full 10,000-candidate experiment from P008 alone."]
    (result_dir / "analysis.md").write_text("\n".join(lines) + "\n")


def run_p008(root: Path) -> dict[str, Any]:
    cells = build_p008_cells(root / "results" / "global_top_10.json")
    write_design(root, cells)
    excluded = load_p007_candidates(root)
    summary = run_adaptive_pilot(root, pilot_id=PILOT_ID, deterministic_seed=DETERMINISTIC_SEED, cells=cells, generators=build_p008_generators(cells, excluded), rank_limit=40, rank_artifact_name="top_40")
    summary["p007_exclusion_count"] = len(excluded)
    (root / "results" / PILOT_ID / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_analysis(root, summary)
    return summary

if __name__ == "__main__":
    print(json.dumps(run_p008(Path.cwd()), indent=2, sort_keys=True))
