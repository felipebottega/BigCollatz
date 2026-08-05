# P007 adaptive stage-A pilot analysis

Pilot `p007-adaptive-stage-a-300` evaluated exactly 300 deterministic 1,000-digit candidates: 12 adaptive cells, 25 candidates per cell, four cells from each of `parity-prefix`, `decimal-suffix`, and `residue`. The deterministic seed was `p007-adaptive-stage-a-300/main/2026-08-05`.

## Cell design

The grid used the current global top-10 rank 1 and rank 2 parents, each at two preservation strengths per family:

- parity-prefix: prefix lengths 128 and 256;
- decimal-suffix: suffix lengths 32 and 64 decimal digits;
- residue: moduli `2**64 + 1` and `2**128 + 1`.

This creates a balanced 2-by-2 comparison inside each family: parent lineage is varied independently from family-specific preservation strength. Rank 1 and rank 2 were selected because they are the strongest persisted global records and provide two distinct high-performing lineages without overfitting all 12 cells to one parent.

## Observed results

No nontrivial cycle was found. All 300 trajectories reached 1, with zero repeated states and zero interruptions.

| Cell | Family | Parameters | Mean length | Median | Max | Top-tail count | >=25k | >=26k | >=27k | Throughput/s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| p007-ds-r02-d64 | decimal-suffix | suffix_digits=64 | 24319.4 | 24291 | 25802 | 4 | 4 | 0 | 0 | 3.85 |
| p007-pp-r02-l256 | parity-prefix | prefix_length=256 | 24313.5 | 24260 | 25887 | 4 | 4 | 0 | 0 | 3.86 |
| p007-pp-r02-l128 | parity-prefix | prefix_length=128 | 24100.5 | 23786 | 25719 | 4 | 4 | 0 | 0 | 4.02 |
| p007-ds-r01-d32 | decimal-suffix | suffix_digits=32 | 24042.4 | 24022 | 25873 | 4 | 3 | 0 | 0 | 3.98 |
| p007-rs-r02-m64p1 | residue | residue_modulus=2**64+1 | 24108.5 | 24053 | 25717 | 3 | 3 | 0 | 0 | 3.85 |
| p007-pp-r01-l128 | parity-prefix | prefix_length=128 | 24144.5 | 24181 | 25351 | 4 | 3 | 0 | 0 | 4.10 |
| p007-rs-r01-m128p1 | residue | residue_modulus=2**128+1 | 23962.2 | 23872 | 25940 | 2 | 2 | 0 | 0 | 3.99 |
| p007-ds-r01-d64 | decimal-suffix | suffix_digits=64 | 24032.3 | 23990 | 25423 | 3 | 2 | 0 | 0 | 4.03 |
| p007-pp-r01-l256 | parity-prefix | prefix_length=256 | 23869.6 | 23787 | 25439 | 1 | 1 | 0 | 0 | 4.15 |
| p007-ds-r02-d32 | decimal-suffix | suffix_digits=32 | 23889.2 | 23825 | 24909 | 0 | 0 | 0 | 0 | 4.00 |
| p007-rs-r01-m64p1 | residue | residue_modulus=2**64+1 | 23661.6 | 23800 | 25082 | 1 | 1 | 0 | 0 | 4.06 |
| p007-rs-r02-m128p1 | residue | residue_modulus=2**128+1 | 23708.1 | 23795 | 24901 | 0 | 0 | 0 | 0 | 4.05 |

Family aggregates:

| Family | Mean of cell means | Max length | Overall top-10% tail records | >=25k | >=26k | >=27k | Mean throughput/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| parity-prefix | 24107.0 | 25887 | 13 | 12 | 0 | 0 | 4.03 |
| decimal-suffix | 24070.8 | 25873 | 11 | 9 | 0 | 0 | 3.97 |
| residue | 23860.1 | 25940 | 6 | 6 | 0 | 0 | 3.99 |

The overall maximum trajectory was 25,940 steps from `p007-rs-r01-m128p1`, but that cell had only two records in the overall top-10% tail. No candidate exceeded 26,000 or 27,000 steps. Runtime and throughput were similar across families, with no operational bottleneck separating the cells.

## Heuristic interpretation

The strongest sustained evidence belongs to `p007-ds-r02-d64` and `p007-pp-r02-l256`: both combined top mean length, four records in the 30-record pilot tail, and four >=25,000-step exceedances. `p007-pp-r02-l128`, `p007-ds-r01-d32`, and `p007-pp-r01-l128` also produced four tail records, so the result does not justify a single-cell-only promotion.

At the family level, parity-prefix and decimal-suffix were close. Parity-prefix had the most tail concentration and >=25,000 exceedances; decimal-suffix had the highest-scoring individual cell. Residue produced the isolated maximum but weaker tail concentration, so the maximum alone is insufficient to promote residue as the primary family.

## Unsupported speculation to avoid

P007 does not prove or disprove the Collatz conjecture. The absence of a repeated positive state among 300 starts is only an observation at this pilot scale. Trajectory length, maximum excursion, digit-band return, and residue-recurrence metrics remain heuristics rather than evidence for or against existence of a nontrivial cycle.

## Decision and next action

Promote a small second-stage pilot that keeps multiple families alive, emphasizing `p007-ds-r02-d64`, `p007-pp-r02-l256`, and `p007-pp-r02-l128`, with at least one residue sentinel cell retained because `p007-rs-r01-m128p1` produced the isolated maximum. Reject no cell as clearly unproductive at this scale; `p007-ds-r02-d32` and `p007-rs-r02-m128p1` were weak in P007 but each had only 25 samples.
