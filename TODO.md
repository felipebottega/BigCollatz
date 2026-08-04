# Prioritized Implementation Plan

## P0 — correctness foundation (exact next step)

- [ ] Create the Python package and typed evaluator result model matching raw
  schema v1.
- [ ] Implement a scalar arbitrary-precision reference evaluator with explicit
  `reached_one`, exact full-state-set repetition detection, maximum tracking,
  and distinctly censored operational interruption reasons.
- [ ] Add hand-checked trajectory tests (`1`, `2`, `3`, `6`, `27`), an injected
  transition function for nontrivial cycle tests, and interruption/safety-limit
  boundary tests that reject mathematical classifications.
- [ ] Implement the trailing-zero batched evaluator and property-test every
  field against the scalar reference.
- [ ] Add record serialization/validation with decimal-string bigints.

**Exit gate:** correctness suite passes, including deliberate hash-collision and
large-integer serialization cases. No large experiment may precede this gate.

## P1 — reproducible execution and persistence

- [ ] Define versioned TOML experiment configs and canonical JSONL manifests.
- [ ] Implement deterministic sharding, atomic raw writes, rolling checksums,
  checkpoints, resume validation, and fault-injection tests.
- [ ] Capture git revision, command, Python/backend, OS/kernel, CPU, memory, and
  effective limits; add periodic progress/ETA reporting.
- [ ] Build streaming validator and summary generator with exact documented
  percentile conventions.

**Exit gate:** repeated generation is byte-identical and every simulated
interruption resumes to the same output as an uninterrupted fixture.

## P2 — controls and first guided generator

- [ ] Implement S0 counter-based and low-discrepancy stratified controls.
- [ ] Implement parity-word to residue-class construction with brute-force tests
  at small `k`.
- [ ] Implement S1 beam scoring and deterministic lifting into 500--1000 digits.
- [ ] Create residue/digit-matched controls and manifest deduplication reports.

## P3 — pilots, not full experiments

- [ ] Run and record E000, then E001 and E002 at 100--1,000 candidates.
- [ ] Profile bigint transitions, batching, I/O, cache opportunities, beam
  generation cost, and memory.
- [ ] Set optional production safety limits and shard sizes from pilot evidence;
  verify that every limit produces only a censored interruption record.
- [ ] Recheck bibliography against primary sources when network access permits.

## P4 — second construction and scale gate

- [ ] Implement/test canonical inverse edges, deduplication, and S2 frontier.
- [ ] Pilot S2 with generation cost included.
- [ ] Independently replay every apparent repeated state; document that long
  nonrepeating runs are not loop candidates.
- [ ] Approve a 100,000-candidate experiment only after all earlier exit gates,
  storage estimates, and frozen preregistration are complete.

## Later

- [ ] Evaluate bounded certified-suffix memoization and Brent cycle mode.
- [ ] Implement S3/S4 held-out analysis, then S5 only if evidence supports it.
- [ ] Consider a native backend only after profiling and differential fixtures.
