# Architecture

The active program has one direct flow:

```text
1000-digit candidate generator -> exact evaluator -> statistics and top 10
```

`bigcollatz/experiment.py` runs a sequential loop. It temporarily retains the
10,000 integer trajectory lengths to compute the median and percentiles, plus a
ten-entry heap. It does not retain all candidates or full result records.

Each experiment directory contains only `summary.json`, `summary.md`, and
`top_10.json`. After successful completion, its top ten is merged by starting
integer with `results/global_top_10.json` and the longest ten are retained.
Large integers are decimal strings in JSON to preserve exact values.

The evaluator uses Brent cycle detection with constant state. A state-set
implementation remains solely as a test oracle. The project intentionally has
no shards, checkpoints, schedulers, manifests, workers, persistent caches,
database, schema framework, or storage abstraction.
