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

## Adaptive correctness infrastructure

Future adaptive cross-family pilots must use the shared evaluator in `bigcollatz.evaluator` as the single production trajectory engine. `evaluate()` and `evaluate_with_metrics()` both delegate to the same exact integer loop for the unaccelerated positive Collatz transition, first-seen step mapping, repeated-state detection, stopping at 1, maximum tracking, and `EvaluationResult` construction. Metric collection is optional and compact: it preserves the exact `EvaluationResult` while adding odd-step counts and density, first descent, exact maximum-excursion ratio components, digit-band returns, and residue-recurrence counts.

Canonical nontrivial-cycle evidence is reconstructed as `states[first_seen_step:repeated_at_step]`, so the closing repeated state is not duplicated. Independent verification replays the starting integer through the shared evaluator, compares all repeated-state fields and ordered members, checks every transition and exact closure, rejects cycles containing `1`, and requires canonical unabridged decimal evidence.

`AdaptiveCell` defines the correctness contract for future cells: `cell_id`, `family`, `strategy`, `validation_mode`, `source_parent`, `parent_rank`, `candidate_count`, and exact `parameters`. The supported families are `parity-prefix`, `decimal-suffix`, and `residue`, bound respectively to the current strategy constants `S1-parity-prefix-top10`, `S5-decimal-suffix-top10`, and `S6-residue-class-top10` and their validation modes.

Candidate records are validated strictly against their cell before evaluation. Records must carry complete metadata, match the cell exactly, contain exactly 1,000 decimal digits, satisfy the mathematical family invariant using the same persisted metadata, and be globally unique across the entire pilot. Missing metadata is never filled from the cell.

The adaptive runner consumes exactly `cell.candidate_count` records for each normally completed cell: short generators and long generators fail clearly, and a count mismatch cannot report `completed`. A single pilot-wide `seen_candidates` set rejects duplicates within or across cells before a duplicate evaluator call. Per-cell runtime is measured with a monotonic high-resolution timer and persisted along with throughput. If a verified repeated state is found, the runner persists the canonical compact cycle candidate, writes complete discovery JSON and Markdown evidence, stops before requesting another candidate, and writes an early-stop summary while keeping global top-ten results isolated.


## P007 adaptive cross-family instantiation

Pilot `p007-adaptive-stage-a-300` instantiated the adaptive comparison as a balanced 12-cell grid over the existing S1, S5, and S6 families. It used the current `results/global_top_10.json` rank-1 and rank-2 parents, 25 candidates per cell, and deterministic seed `p007-adaptive-stage-a-300/main/2026-08-05`. For each family, parent rank and preservation strength were varied independently: S1 parity-prefix cells used prefix lengths 128 and 256; S5 decimal-suffix cells used 32 and 64 preserved trailing decimal digits; S6 residue cells used moduli `2**64 + 1` and `2**128 + 1`.

P007 completed all 300 evaluations with the shared exact evaluator: 300 reached one, no repeated state was found, and `results/global_top_10.json` remained isolated. The strongest sustained cell metrics were `p007-ds-r02-d64`, `p007-pp-r02-l256`, and `p007-pp-r02-l128`; the isolated maximum length 25,940 came from `p007-rs-r01-m128p1`, so residue remains useful as a sentinel but did not dominate the pilot tail.
