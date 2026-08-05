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


## Recurrence-metric comparisons from the persisted summary

The following comparisons use only `summary.json`; exact maximum-excursion evidence remains the persisted `{numerator, denominator}` pair for each cell. Any decimal in this Markdown is only a display approximation after exact-rational ranking with `Fraction(numerator, denominator)`.

### Cell-level recurrence metrics

| Cell | Family | Odd-step density | Mean first descent | Max-excursion ratio (approx; exact in summary JSON) | Mean same-digit-band returns | Mean repeated residue hits |
|---|---|---:|---:|---:|---:|---:|
| `p007-pp-r01-l128` | parity-prefix | 201388/603612 = 0.333638 | 3.00 | 13.871 | 44.24 | 23121.48 |
| `p007-pp-r01-l256` | parity-prefix | 198731/596741 = 0.333027 | 3.00 | 13.871 | 43.36 | 22846.64 |
| `p007-pp-r02-l128` | parity-prefix | 200967/602512 = 0.333549 | 26.00 | 810.778 | 79.64 | 23077.48 |
| `p007-pp-r02-l256` | parity-prefix | 203025/607837 = 0.334012 | 26.00 | 810.778 | 75.24 | 23290.48 |
| `p007-ds-r01-d32` | decimal-suffix | 200403/601060 = 0.333416 | 3.00 | 39.499 | 47.36 | 23019.40 |
| `p007-ds-r01-d64` | decimal-suffix | 200302/600807 = 0.333388 | 3.00 | 13.871 | 51.84 | 23009.28 |
| `p007-ds-r02-d32` | decimal-suffix | 198921/597229 = 0.333073 | 26.00 | 924.569 | 45.88 | 22866.16 |
| `p007-ds-r02-d64` | decimal-suffix | 203083/607984 = 0.334027 | 26.00 | 3510.470 | 56.40 | 23296.36 |
| `p007-rs-r01-m64p1` | residue | 196721/591541 = 0.332557 | 5.36 | 88.874 | 26.36 | 22638.64 |
| `p007-rs-r01-m128p1` | residue | 199629/599056 = 0.333239 | 3.52 | 189.812 | 18.60 | 22939.24 |
| `p007-rs-r02-m64p1` | residue | 201039/602712 = 0.333557 | 6.72 | 221.934 | 25.00 | 23085.48 |
| `p007-rs-r02-m128p1` | residue | 197170/592702 = 0.332663 | 5.44 | 51.258 | 16.28 | 22685.08 |

### Family-level recurrence metrics

| Family | Aggregated odd-step density | Mean first descent | Best exact-ranked max-excursion cell (approx ratio) | Mean same-digit-band returns | Mean repeated residue hits |
|---|---:|---:|---:|---:|---:|
| parity-prefix | 804111/2410702 = 0.333559 | 14.50 | `p007-pp-r02-l128` (810.778) | 60.62 | 23084.02 |
| decimal-suffix | 802709/2407080 = 0.333478 | 14.50 | `p007-ds-r02-d64` (3510.470) | 50.37 | 23047.80 |
| residue | 794559/2386011 = 0.333007 | 5.26 | `p007-rs-r02-m64p1` (221.934) | 21.56 | 22837.11 |

### Interpretation boundaries

**Observed values.** Odd-step densities are tightly clustered near one third, so they do not separate families materially at 25 candidates per cell. First-descent means split mostly by source parent rank in parity-prefix and decimal-suffix cells (3.00 for rank 1 versus 26.00 for rank 2), while residue cells descend early on average. Exact maximum-excursion ratios are most extreme in `p007-ds-r02-d64`, followed by `p007-ds-r02-d32` and the two rank-2 parity-prefix cells, but the isolated longest trajectory remains `p007-rs-r01-m128p1`. Same-decimal-digit-band returns are highest in rank-2 parity-prefix cells, moderate in decimal-suffix cells, and lower in residue cells. Repeated residue-hit counts are close across cells and broadly track trajectory length rather than providing an independent family separation.

**Heuristic interpretation.** The recurrence metrics are useful descriptive diagnostics for tail behavior. They mildly reinforce the existing promotion preference for `p007-ds-r02-d64`, `p007-pp-r02-l256`, and `p007-pp-r02-l128`: those cells combine strong or sustained tail placement with comparatively high same-digit-band returns and repeated residue-hit counts. They also support retaining a residue sentinel because residue still produced the longest single trajectory, even though residue recurrence summaries are not strongest at family level.

**Unsupported speculation.** These recurrence summaries do not establish cycle evidence, family superiority, or asymptotic behavior. In particular, high maximum-excursion ratios and high digit-band-return counts should not be interpreted as evidence for nontrivial cycles; all 300 trajectories reached one, with zero repeated states and zero interruptions.

### Effect on the promotion decision

The recurrence metrics do not materially change the promotion decision. The decision remains driven by trajectory length, absence of >=26,000 and >=27,000 threshold exceedances, and top-tail concentration: parity-prefix contributed 13 top-tail records and 12 >=25,000 exceedances, decimal-suffix contributed 11 top-tail records and 9 >=25,000 exceedances, and residue contributed 6 top-tail records and 6 >=25,000 exceedances despite the isolated 25,940-step maximum. The added recurrence evidence qualifies the interpretation by showing that decimal-suffix has the strongest exact-ranked excursion cell and parity-prefix has the strongest digit-band-return family profile, but it does not justify replacing the proposed second-stage mix or starting a full experiment.
