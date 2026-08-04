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

## Correctness-first adaptive cross-family runner

The evaluator now uses one private authoritative trajectory engine for the unaccelerated transition, trajectory iteration, exact seen-state mapping, first-seen indexing, repeated-at indexing, cycle length, stopping at `1`, maximum tracking, and `EvaluationResult` construction. `evaluate()` is the normal public interface; `evaluate_with_metrics()` is a thin wrapper that enables compact metric collection inside the same engine.

Metric definitions are heuristic and never replace exact repeated-state detection: odd-step count and density count odd source states per executed step; first-descent step is the first generated state below the start when defined; maximum excursion is stored exactly as numerator `maximum_integer` over denominator `start`; same-decimal-digit-band returns count generated states with the start's decimal digit count; repeated-residue hits count repeated residues modulo a bounded residue modulus. Per-cell aggregation records means, undefined first-descent count, exact maximum-excursion ratio, and residue modulus.

Canonical cycle reconstruction independently replays states through `repeated_at_step` and slices `states[first_seen_step:repeated_at_step]`, so the first member is the repeated integer and the closing repeated state is excluded. Independent verification replays the start with the shared evaluator, reconstructs the cycle, compares scalar evidence and ordered members, checks every transition and closure, rejects cycles containing `1`, and validates canonical unabridged decimal strings.

If a verified nontrivial cycle is found, the runner first writes the compact `results/cycle_candidates.json` record, then writes complete unabridged `results/nontrivial_cycle_discovery.json` and `NONTRIVIAL_CYCLE_FOUND.md`, and immediately stops after writing `results/<pilot_id>/summary.json` with `stopped_early=true`, the exact evaluated count, active cell metadata, artifact paths, and global-top isolation status. Failed verification writes a failure summary and does not create discovery artifacts.

Adaptive cells are explicit objects containing `cell_id`, `family`, `strategy`, `validation_mode`, `source_parent`, `parent_rank`, `candidate_count`, and complete parameters. Families authoritatively bind to strategies and validation modes: parity-prefix to `S1-parity-prefix-top10`/`parity_prefix`, decimal-suffix to `S5-decimal-suffix-top10`/`decimal_suffix`, and residue to `S6-residue-class-top10`/`residue`. A single pilot-wide candidate set enforces global uniqueness before evaluation.

The overall pilot top tail selects exactly `ceil(10% of completed trajectories)`, sorted by length descending with deterministic `cell_id` and cell-local-order tie breaks. The persisted deterministic score is `0.45*mean + 0.25*p90 + 0.15*p99_or_p90 + 25*top_tail_count + 10*threshold_evidence + 5*mean_repeated_residue_hits + 20*repeated_state_count`; missing optional p99 uses p90. Stage B allocation gives every selected cell a positive feasible minimum, handles nonpositive scores by equal weights, uses largest remainders, and preserves exact requested totals.

Current adaptive pilots in main: `p007-adaptive-stage-a-300` and `p008-adaptive-stage-b-300`. Both were isolated pilots, found no repeated state, and did not justify full-experiment promotion.
