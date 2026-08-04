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

## Adaptive cross-family cell search

The adaptive search is a pilot-only strategy that compares explicit candidate-generation cells from multiple existing families without introducing a second Collatz evaluator. A cell records `cell_id`, family, source parent, parent rank, candidate count, family parameters, and required validation mode. The implemented comparison set uses the current global top-10 parent ranks 1 and 2 across three families: 256-step parity-prefix preservation, 64-digit decimal-suffix preservation, and residue preservation modulo `2**128 + 1`.

All adaptive trajectory evaluation goes through `evaluate_with_metrics`, which uses the same internal evaluator engine as `evaluate`. The shared engine remains the only authoritative location for the Collatz transition, exact seen-state mapping, stopping at `1`, first-seen and repeated-at step tracking, cycle length computation, maximum integer tracking, and `EvaluationResult` construction.

Metric collection is compact and never replaces exact repeated-state detection. The metrics are: exact `odd_step_count`; exact `odd_step_density = odd_step_count / total_steps`; exact `first_descent_step`, the first step with state below the starting integer; exact `maximum_excursion_ratio = maximum_integer / start`; exact `same_decimal_digit_band_return_count`, the number of post-start states with the same decimal digit count as the start; and heuristic `repeated_residue_hit_count`, the number of states whose residue modulo 65,537 has already appeared. Metric memory is O(number of residues up to 65,537 plus the evaluator's exact seen-state map); per-step runtime overhead is O(1) plus decimal digit-band checks. Cell scoring uses p90, p99, fixed threshold exceedance counts, top-tail counts, repeated-state count, and mean repeated-residue hits from persisted summaries.

Stage A (`p007-adaptive-cross-family-stage-a-360`) evaluated six cells with 60 candidates each using seed `p007-stage-a-v1`. It selected `ap-parity-r2-p256`, `ap-residue-r2-m2p128p1`, and `ap-suffix-r2-d64` using the documented deterministic scoring and diversity rule. Stage B (`p008-adaptive-cross-family-stage-b-360`) used seed `p008-stage-b-v1`, allocated 126/116/118 candidates to those selected cells, and remained isolated from global full-experiment artifacts. Both pilots found 0 repeated states. Stage B reached maximum trajectory length 26,118, below Stage A, P003, E003, and E004, so the adaptive method is not promoted to a full experiment.

Cycle evidence path: if an adaptive candidate reports `repeated_state`, the runner writes complete cycle evidence including full starting integer, repeated integer, first-seen step, repeated-at step, cycle length, exact cycle members, pilot id, strategy, cell id, family, seed, cell parameters, parent metadata, and validation mode. Compact records are persisted through the normal `results/cycle_candidates.json` path. Confirmed nontrivial discoveries create `results/nontrivial_cycle_discovery.json` and `NONTRIVIAL_CYCLE_FOUND.md` only after independent replay confirms the same repeated state and excludes `1`.
