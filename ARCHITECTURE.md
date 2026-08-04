# Architecture

## 1. Design principles

The system separates candidate generation, exact evaluation, raw persistence,
and analysis. Generators never see hidden evaluation results except through an
explicit next-round artifact. Raw data is immutable; reports are disposable
derivatives. Every object carries schema and strategy versions.

The initial implementation should use Python for orchestration and its
arbitrary-precision `int`, with a narrow evaluator API that can later gain a
Rust/GMP backend after profiling. Correctness comes before native optimization.

## 2. Components

```text
strategy config -> generator -> canonical manifest -> shard scheduler
                                                      |
                                                      v
                                              exact evaluator
                                                      |
                           checkpoint <- raw JSONL shards + checksums
                                                      |
                                                      v
                                      validator -> summary -> report
```

### Strategy registry and generators

Each generator is a pure deterministic iterator over `(candidate, provenance)`
given a versioned config. It validates digit bounds, canonicalizes integers,
and emits stable candidate IDs derived from experiment ID, generator version,
ordinal, and integer digest. Parameters include all deterministic seeds even
when a counter-based baseline is used.

### Evaluator

The evaluator accepts one positive bigint and optional operational safety
limits. Its hot loop uses trailing zero counts to batch divisions while
preserving exact unaccelerated metrics. It continues until `1` or an exact
repetition unless interrupted, and returns a typed record, never a sentinel
length. Interruption handling is separate from mathematical classification.

Exact cycle detection starts with a hash set of full integer states for bounded
pilots and tests. Production will support Brent's algorithm as a constant-memory
mode; equality compares full bigints and its cycle result is replayed to derive
cycle entry/period before reporting. A second, independent replay command is
mandatory for any nontrivial repetition. The known cycle is classified by
reaching `1` first.

Memoization is initially conservative: a process-local cache maps a state to a
certified `reached_one` suffix with exact remaining step count and suffix
maximum. It has a byte budget and deterministic eviction policy. Cache entries
from censored or repeated trajectories are not reused. Persistent caches are a
later optimization because compatibility, maxima, and corruption complicate
correctness.

### Scheduler and checkpoints

The canonical manifest is partitioned by stable record ID into fixed shards.
Workers write to temporary JSONL files, periodically write a checkpoint with
last committed ordinal and rolling checksum, then atomically rename completed
shards. Resume validates records and checksums rather than trusting only a
counter. One candidate is the smallest possible rework after interruption.

### Validator and analyzer

Validation rejects duplicate IDs, malformed decimal bigints, inconsistent digit
counts, impossible flags, negative timing, and summaries lacking raw records.
The analyzer streams JSONL, uses exact integers/decimal arithmetic where needed,
and emits versioned JSON plus human-readable Markdown/CSV. Starting and maximum
integers are decimal strings in JSON to avoid downstream precision loss.

## 3. Raw record schema (version 1 proposal)

Required fields:

| Field | Type / meaning |
| --- | --- |
| `schema_version` | integer, initially `1` |
| `experiment_id`, `record_id` | strings |
| `start` | canonical decimal string |
| `decimal_digits` | integer, 500--1000 |
| `total_steps_executed` | nonnegative integer, unaccelerated |
| `outcome` | `reached_one`, `repeated_state`, or `interrupted` |
| `reached_one` | boolean; true exactly when `outcome` is `reached_one` |
| `repeated_state_found` | boolean, exact equality only |
| `repeated_state`, `cycle_entry_step`, `cycle_period` | decimal string/integers or null |
| `maximum_integer` | canonical decimal string |
| `maximum_bit_length` | integer |
| `stopping_reason` | `reached_one`, `repeated_state`, `user_stop`, `process_shutdown`, `resource_exhaustion`, `safety_limit`, or `error` |
| `safety_limit_kind`, `safety_limit_value` | configured limit kind/value when applicable, otherwise null |
| `censored` | boolean; true exactly when `outcome` is `interrupted` |
| `wall_time_ns`, `cpu_time_ns` | integer timing |
| `strategy`, `strategy_version`, `strategy_parameters` | provenance |
| `software_revision`, `evaluator_version` | exact code identity |
| `limits` | effective configurable safety limits, or an empty object |

Experiment metadata separately records UTC timestamps, CLI/config, manifest and
file SHA-256 hashes, OS/kernel, architecture, logical CPUs, memory, interpreter,
bigint/backend versions, hostname or anonymized machine ID, shard count, and
environment variables that affect execution.

`total_steps_executed` is work performed, including a terminal step that creates
`1` or the first repeated state. A start of `1` has zero steps. For an
interrupted computation it is only the observed prefix length, not a completed
trajectory length. If a batched operation would cross a configured safety
limit, the evaluator executes only the permitted logical work so the last exact
state and maximum remain well-defined. No safety-limit value has mathematical
significance.

The validator enforces mutually exclusive outcomes. Repetition details are
present only for `repeated_state`; interrupted records have `reached_one=false`,
`repeated_state_found=false`, and null cycle details. A `safety_limit` reason
requires its kind and configured value, while other reasons leave those fields
null. An abrupt shutdown may preserve only the most recent durable checkpoint;
that prefix is censored at its recorded step and is not extrapolated.

## 4. Storage layout

```text
results/e001/
  metadata.json
  manifest.jsonl
  raw/part-00000.jsonl
  checkpoints/part-00000.json
  checksums.sha256
reports/e001/
  summary.json
  summary.md
  histogram.csv
```

Large raw artifacts are normally external/ignored, while small fixture or
milestone summaries may be committed. `EXPERIMENTS.md` always records artifact
locations and hashes so history is not lost.

## 5. Correctness and test plan

- Unit tests for even/odd transitions, zero-step start at 1, exact digit bounds,
  batched versus scalar counts/maxima, and known small trajectories.
- Cycle tests using an injected finite transition function, plus the known
  `1-4-2` classification and deliberate hash collisions to prove full equality.
- Interruption tests for every operational reason and safety-limit boundary,
  asserting that all such records are censored and have no mathematical result.
- Property tests comparing scalar and optimized evaluators over bounded inputs.
- Serialization round trips for integers beyond IEEE-754 range.
- Resume fault-injection at every checkpoint boundary; duplicate-free output.
- Differential tests between Python and any future native backend.
- Golden manifest and report fixtures to enforce determinism.

## 6. Performance plan

Measure before optimizing. Profile scalar Python, trailing-zero batching, cache
hit rate, limb growth, and serialization on a small deterministic benchmark.
Parallelize by processes to avoid interpreter contention. Keep per-worker caches
local initially; shared-cache coordination may cost more than saved work.
Native code is justified only by an identical-record differential benchmark.

Progress is emitted at fixed time intervals, not per state. It includes manifest
progress, throughput, CPU/wall time, cache statistics, current best, censoring,
and checkpoint age without writing full trajectories.
