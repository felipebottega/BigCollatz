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

The adaptive design compares small, explicit cells whose family authoritatively determines both strategy and validation mode. A parity-prefix cell must use `S1-parity-prefix-top10` with `parity_prefix`; a decimal-suffix cell must use `S5-decimal-suffix-top10` with `decimal_suffix`; a residue cell must use `S6-residue-class-top10` with `residue`. Candidate records are rejected before evaluation for wrong strategy, wrong validation mode, missing source metadata, source-parent mismatch, malformed parameters, failed invariant, duplicates, or anything other than exactly 1,000 decimal digits.

All adaptive evaluation calls the shared evaluator interface. The evaluator owns the only exact unaccelerated transition loop, seen-state map, first-seen registration, repeated-at calculation, cycle-length calculation, maximum tracking, and `EvaluationResult` construction. The metrics-enabled interface delegates to the same loop and adds compact metrics without changing `EvaluationResult`.

Cycle evidence uses canonical replay from the starting integer through `repeated_at_step` and slices `states[first_seen_step:repeated_at_step]`. Independent verification replays the start again, reconstructs the ordered cycle independently, checks exact scalar agreement, exact member order, exact closure, repeated integer at the first member, nontriviality by excluding `1`, and complete canonical decimal integers before setting `independent_replay_confirmed`.

Metrics are compact heuristics: odd-step count and density are exact O(1) per step and O(1) memory; first descent step is exact O(1) per step; maximum excursion is stored exactly as numerator `maximum_integer` and denominator `starting_integer`; same decimal-digit-band returns are heuristic O(decimal digit count) per step and O(1) memory; repeated residue hits use bounded modulus `2**16 + 1` with O(1) expected per-step time and bounded memory. These metrics are aggregated in pilot summaries and may influence deterministic cell scores, but they do not alter exact outcomes.

Stage A uses 300-1,000 total candidates across a meaningful small set of parity-prefix, decimal-suffix, and residue cells. Stage B uses a new seed and deterministic largest-remainder allocation with positive counts that sum exactly to the requested total. Scores combine persisted mean, p90, p99, and top-tail counts; they are deterministic and are not based solely on a single maximum. Current status: P007/P008 completed, no repeated state, no full promotion.
