# Architecture

The normal experiment flow is deliberately small and sequential:

```text
candidate generator -> exact evaluator -> aggregate statistics and top 10
```

`bigcollatz/experiment.py` selects one of the deterministic strategies in
`bigcollatz/generator.py`, evaluates each candidate, and writes compact result
artifacts. It retains completed trajectory lengths for statistics, a ten-entry
heap for ranking, and any cycle candidates; it does not retain raw trajectories
or every result record.

`bigcollatz/evaluator.py` is the single authoritative trajectory loop. It keeps
a trajectory-local mapping from each exact arbitrary-precision integer to its
first step. This provides mandatory repeated-state detection and the cycle entry
and period without relying on hashes as proof of equality. The optional metrics
path uses the same loop, preventing the pilot and normal evaluators from
drifting apart.

Normal experiment directories contain `summary.json`, `summary.md`, and
`top_10.json`. After successful completion, the local top ten is merged by
starting integer with `results/global_top_10.json`. Adaptive pilots use their own
summary and ranking artifacts and deliberately leave the global top ten
unchanged. Large integers are decimal strings in JSON to preserve exact values.

`bigcollatz/adaptive.py` adds strict cell and candidate validation, compact
recurrence metrics, deterministic cross-cell ranking, and independent cycle
verification for small adaptive pilots. `bigcollatz/p007.py` is the reproducible
construction of the completed P007 pilot, not a second general-purpose runner.

The project intentionally has no shards, checkpoints, schedulers, workers,
persistent caches, database, schema framework, or storage abstraction.
