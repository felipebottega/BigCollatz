# TODO

## Complete

- [x] Exact arbitrary-precision evaluator with independent cycle-detection oracle.
- [x] Strict schema-v1 record validation and malformed-record tests.
- [x] Deterministic uniform baseline with rejection sampling and digit-stratum
  domain separation.
- [x] A 600-trajectory baseline pilot with raw JSONL output, top-10 starts, and
  per-digit count/mean/median/p90/maximum/best-start summaries.
- [x] Simplify documentation and remove infrastructure plans.

## Next small experiments

- [ ] Compare another simple control generator with S0 under the same digit and
  candidate counts.
- [ ] Add report comparisons only when a second strategy has actual results.
- [ ] Profile only if evaluator runtime blocks a concrete experiment.

S1 is intentionally not implemented yet. Do not add sharding, checkpoints,
resumable workers, persistent caches, complex manifests, or scheduler layers.
