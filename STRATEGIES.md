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
