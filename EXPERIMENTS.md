# Experiment Ledger

This is an append-only human-readable index. Raw records belong under
`results/<id>/`; derived output belongs under `reports/<id>/`. Each completed
entry must include artifact hashes, code revision, configuration, hardware,
runtime, result summary, interpretation, limitations, and next decision.

## Planned experiments

### E000 — evaluator correctness and throughput pilot

- **Status:** complete, 2026-08-04
- **Scale:** 600 trajectories; 100 at each of 500, 600, 700, 800, 900, and
  1000 decimal digits
- **Purpose:** verify scalar/optimized equivalence, exact cycle classification,
  interruption/censoring classification, checkpoint recovery, schema
  validation, and bigint throughput.
- **Result:** all 600 reached one; mean 18,023.795 steps, maximum 25,678;
  27.06 trajectories/s overall and 27,960 KiB peak RSS.
- **Artifacts:** `results/e000-p0-pilot/` and `reports/e000-p0-pilot/`; raw
  SHA-256 `2dbc1c7df598c6d6fd1c039db18b87cadabb13ee89c47783b29b4ac03840cd22`.
- **Decision:** advance to a preregistered S1 parity-prefix beam with matched
  controls. The baseline contains no trajectory-aware signal.
- **Limitations:** one machine, 100 observations per stratum, sequential
  CPython, and no claim beyond this sample. Resume remains a P1 gate.

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
