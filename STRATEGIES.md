# Strategy Notes

## S0-uniform-deterministic

The active baseline deterministically chooses an offset in the 1000-digit
decimal interval from a SHA-256 seed, then walks the interval without
replacement. Every generated candidate has exactly 1000 digits and candidates
within an experiment are distinct. This trajectory-blind generator is a
reproducible control.

## S1-parity-prefix-top10

A finite parity word determines a residue class modulo a power of two. S1 uses
the starting integers in `results/global_top_10.json` as parents and preserves
their first 256 unaccelerated parity decisions by default. It allocates work as
evenly as possible among those parents, then uses unbiased, SHA-256-based
sampling of quotient values to lift each residue across the full 1000-digit
interval. The real 10,000-candidate S1 experiment was executed as
`e002-s1-parity-prefix-256`, with generated artifacts stored under
`results/e002-s1-parity-prefix-256/`.

## S2-parity-prefix-weighted-lineages

S2 reuses the same parity-prefix candidate-generation mathematics as S1 and
keeps the default 256-decision prefix. Its parent lineages come from
`results/e002-s1-parity-prefix-256/top_10.json`: entries are grouped by
`parent_starting_integer`, and each parent's weight is the number of E002 top-10
descendants it produced; productive lineages are ordered by descending weight, with source-file order breaking weight ties. Candidate quotas are assigned proportionally by those
weights, with floors first and any remainder distributed by largest fractional
remainder, breaking ties by first parent order in the source file. The runner
records the source file, prefix length, seed, productive lineage count, lineage
weights, and final allocation in `summary.json`.


## S3-recursive-weighted-lineages

S3 repeats the S2 weighted-lineage process recursively using the most recent
completed guided experiment as its lineage source. It reads
`results/e003-s2-weighted-lineages-256/top_10.json`, validates that every source
entry came from `e003-s2-weighted-lineages-256` with strategy
`S2-parity-prefix-weighted-lineages` and a completed outcome, then groups entries
by `parent_starting_integer`. Each parent's weight is the number of E003 top-10
descendants it produced. Only those productive E003 parent lineages are used.

Candidate generation remains the shared 256-decision parity-prefix generator:
every candidate has exactly 1000 decimal digits, is distinct, excludes source
parents, and preserves its assigned parent's first 256 unaccelerated parity
decisions. Candidate quotas use the existing proportional largest-remainder
allocation rule, with deterministic parent-order tie breaks. The runner records
the E003 source file, prefix length, deterministic seed, productive lineage
count, lineage weights, and final per-parent allocation in `summary.json`. The real 10,000-candidate S3 experiment was executed as
`e004-s3-recursive-weighted-lineages-256`, with generated artifacts stored under
`results/e004-s3-recursive-weighted-lineages-256/`.

## S4-diversified-mixed-prefix-top10

S4 uses the persistent `results/global_top_10.json` parents and preserves several
prefix lengths in one experiment instead of committing to one fixed parity-prefix
scale. For each global top-10 parent and each prefix length in 128, 256, and 384,
it samples deterministic SHA-256 quotient lifts in the matching residue class
inside the 1000-digit interval. Allocation is balanced across all parent/prefix
cells, every candidate is distinct, source parents are excluded, and optional
validation directly checks the assigned parity prefix. This tests whether
lineage diversity plus mixed prefix granularity can preserve the strong E004
signal without further narrowing to the two dominant recursive lineages. The
strategy is controlled by the seed, parent file, prefix-length tuple, and total
candidate count. It has been piloted as P003 only; no full experiment has been
run.

## S5-decimal-suffix-top10

S5 tests whether the trailing decimal digits of successful 1,000-digit starts carry useful structure independent of parity-prefix lineage. It uses `results/global_top_10.json`, balances candidates across the current top-ten parents, preserves each selected parent's last 64 decimal digits, and samples quotient lifts uniformly by the shared SHA-256 sampler across the full 1,000-digit interval. Every generated candidate is an explicit `CandidateRecord` with required validation mode `decimal_suffix`, parent metadata, and `suffix_digits`. Validation requires exact equality modulo `10**suffix_digits` before the common exact evaluator runs. Pilot `p005-s5-decimal-suffix-100` reached one for all 100 candidates, found no repeated state, and reached maximum length 25,749. Current status: inconclusive diversification signal; not promoted to a full experiment.

## S6-residue-class-top10

S6 tests whether preserving non-decimal modular classes from successful starts captures near-return information missed by decimal suffix and parity-prefix searches. It uses `results/global_top_10.json`, balances candidates across the current top-ten parents, preserves each parent's residue modulo `2**128 + 1`, and samples quotient lifts uniformly by the shared SHA-256 sampler across the full 1,000-digit interval. Every generated candidate is an explicit `CandidateRecord` with required validation mode `residue`, `residue_modulus`, and `residue`. Validation requires exact residue equality before the common exact evaluator runs. Pilot `p006-s6-residue-class-100` reached one for all 100 candidates, found no repeated state, and reached maximum length 25,906. Current status: inconclusive; competitive with S5 at pilot scale but not promoted without additional cell-ranking evidence.


## S7 — Adaptive cross-family cell search

- **Hypothesis:** delayed-descent signal may be localized in a small number of cross-family cells, so a two-stage pilot can compare parity-prefix, decimal-suffix, and residue preservation under one budget before concentrating on productive cells.
- **Stage A design:** `p007-s7-adaptive-cross-family-stage-a-300` compared six 50-candidate cells: top-two parents crossed with parity-prefix length 256, decimal suffix length 64, and residue modulo `2**128 + 1`.
- **Stage B design:** `p008-s7-adaptive-cross-family-stage-b-300` selected the top three scored Stage A cells plus the best missing family and allocated 120/90/60/30 candidates.
- **Scoring rule:** `p90 + 0.5*p99_or_0 + 100*count(length>=26000) + 250*repeated_state_count - 0.01*mean_first_descent_step`. The rule deliberately avoids ranking solely by a single maximum.
- **Diversity rule:** Stage B keeps the top three scored cells and adds the best missing family when the top three omit a required family, preventing immediate collapse to one family.
- **Validation dispatch:** the cell family fixes the required validation mode: parity-prefix cells require `parity_prefix`, decimal-suffix cells require `decimal_suffix`, and residue cells require `residue`; candidate metadata mismatches are rejected before evaluation.
- **Recurrence metrics:** compact streaming metrics are odd-step density, first descent below start, maximum-excursion ratio, same-decimal-digit-band returns, and repeated residues modulo `2**64 - 59`. They are heuristics only; exact trajectory-local repeated-state mapping remains mandatory.
- **Full experiment:** none. S7 was rejected for immediate full promotion after P008.
- **Limitations:** Stage A used only the top two global parents and 50 candidates per cell, so cell scores are noisy; Stage B improved distributional tail but not the maximum or exact recurrence evidence relative to E003/E004.
