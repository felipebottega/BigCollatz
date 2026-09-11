"""P007 adaptive stage-A pilot construction and reporting."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .adaptive import AdaptiveCell, run_adaptive_pilot
from .generator import (
    CandidateRecord,
    S1_STRATEGY,
    S5_STRATEGY,
    S6_STRATEGY,
    load_global_top_10,
)

PILOT_ID = "p007-adaptive-stage-a-300"
DETERMINISTIC_SEED = "p007-adaptive-stage-a-300/main/2026-08-05"
CELL_COUNT = 12
CANDIDATES_PER_CELL = 25


def build_p007_cells(global_top_path: Path) -> list[AdaptiveCell]:
    parents = load_global_top_10(global_top_path)
    ranked = {rank: parents[rank - 1] for rank in (1, 2)}
    specs = [
        (
            "p007-pp-r01-l128",
            "parity-prefix",
            S1_STRATEGY,
            "parity_prefix",
            1,
            {"prefix_length": 128},
        ),
        (
            "p007-pp-r01-l256",
            "parity-prefix",
            S1_STRATEGY,
            "parity_prefix",
            1,
            {"prefix_length": 256},
        ),
        (
            "p007-pp-r02-l128",
            "parity-prefix",
            S1_STRATEGY,
            "parity_prefix",
            2,
            {"prefix_length": 128},
        ),
        (
            "p007-pp-r02-l256",
            "parity-prefix",
            S1_STRATEGY,
            "parity_prefix",
            2,
            {"prefix_length": 256},
        ),
        (
            "p007-ds-r01-d32",
            "decimal-suffix",
            S5_STRATEGY,
            "decimal_suffix",
            1,
            {"suffix_digits": 32},
        ),
        (
            "p007-ds-r01-d64",
            "decimal-suffix",
            S5_STRATEGY,
            "decimal_suffix",
            1,
            {"suffix_digits": 64},
        ),
        (
            "p007-ds-r02-d32",
            "decimal-suffix",
            S5_STRATEGY,
            "decimal_suffix",
            2,
            {"suffix_digits": 32},
        ),
        (
            "p007-ds-r02-d64",
            "decimal-suffix",
            S5_STRATEGY,
            "decimal_suffix",
            2,
            {"suffix_digits": 64},
        ),
        (
            "p007-rs-r01-m64p1",
            "residue",
            S6_STRATEGY,
            "residue",
            1,
            {"residue_modulus": 2**64 + 1},
        ),
        (
            "p007-rs-r01-m128p1",
            "residue",
            S6_STRATEGY,
            "residue",
            1,
            {"residue_modulus": 2**128 + 1},
        ),
        (
            "p007-rs-r02-m64p1",
            "residue",
            S6_STRATEGY,
            "residue",
            2,
            {"residue_modulus": 2**64 + 1},
        ),
        (
            "p007-rs-r02-m128p1",
            "residue",
            S6_STRATEGY,
            "residue",
            2,
            {"residue_modulus": 2**128 + 1},
        ),
    ]
    return [
        AdaptiveCell(
            cid, fam, strat, mode, ranked[rank], rank, CANDIDATES_PER_CELL, params
        )
        for cid, fam, strat, mode, rank, params in specs
    ]


def build_p007_generators(
    cells: list[AdaptiveCell], seed: str = DETERMINISTIC_SEED
) -> dict[str, Iterable[CandidateRecord]]:
    del cells, seed
    raise ValueError(
        "P007 is a historical 1,000-digit pilot and cannot generate new candidates "
        "under the greater-than-one-million-digit policy"
    )


def run_p007(root: Path) -> dict[str, Any]:
    cells = build_p007_cells(root / "results" / "global_top_10.json")
    design_dir = root / "results" / PILOT_ID
    design_dir.mkdir(parents=True, exist_ok=True)
    design = {
        "pilot_id": PILOT_ID,
        "deterministic_seed": DETERMINISTIC_SEED,
        "cell_grid": [
            dict(c.__dict__, source_parent=str(c.source_parent)) for c in cells
        ],
        "justification": "Balanced 2x2 grids per family compare the current global rank-1 and rank-2 parents at two preservation strengths: parity prefixes 128/256, decimal suffixes 32/64, and residues modulo 2**64+1 / 2**128+1.",
    }
    (design_dir / "design.json").write_text(
        json.dumps(design, indent=2, sort_keys=True) + "\n"
    )
    return run_adaptive_pilot(
        root,
        pilot_id=PILOT_ID,
        deterministic_seed=DETERMINISTIC_SEED,
        cells=cells,
        generators=build_p007_generators(cells),
    )


if __name__ == "__main__":
    print(json.dumps(run_p007(Path.cwd()), indent=2, sort_keys=True))
