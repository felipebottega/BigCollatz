# Experiment Ledger

This is an append-only human-readable index. Raw records belong under
`results/<id>/`; derived output belongs under `reports/<id>/`. Each completed
entry must include artifact hashes, code revision, configuration, hardware,
runtime, result summary, interpretation, limitations, and next decision.

## Planned experiments

### E000 — evaluator correctness and throughput pilot

- **Status:** planned; not run
- **Scale:** small fixtures and deterministic benchmark only
- **Purpose:** verify scalar/optimized equivalence, exact cycle classification,
  interruption/censoring classification, checkpoint recovery, schema
  validation, and bigint throughput.
- **Acceptance:** all correctness tests pass; interrupted output resumes without
  missing/duplicate records; benchmark metadata is complete.

### E001 — stratified control pilot

- **Status:** planned; not run
- **Scale:** 100--1,000 candidates
- **Purpose:** validate S0 generation and estimate full-run operational
  safety limits/cost.
- **Decision:** choose safety limits and shard sizing without interpreting an
  interrupted pilot trajectory as completed or as a strategy result.

### E002 — parity-prefix beam pilot

- **Status:** planned; not run
- **Scale:** 100--1,000 guided starts plus matched controls
- **Purpose:** test S1 implementation and whether forced-prefix benefits survive
  beyond the controlled prefix at acceptable generation cost.

No 100,000-sequence experiment has been conducted.
