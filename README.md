# BigCollatz

BigCollatz is a reproducible experimental system for **finding unusually long
Collatz trajectories whose starting values have 500--1000 decimal digits**.
It is not a proof project, a random-number sweep, or a consecutive-integer
scanner. The search will compare deterministic, structurally motivated
generators under a common compute budget.

For an integer `n > 0`, one step is

```text
n -> n / 2       when n is even
n -> 3*n + 1     when n is odd
```

All states will use arbitrary-precision integers. Exact evaluation continues
until the trajectory first reaches `1` or an exact integer repeats within that
trajectory. The familiar `1 -> 4 -> 2 -> 1` cycle is therefore recorded as
`reached_one`, never as a discovery. An operational interruption may stop a
computation early, but produces only an interrupted/censored record—not a
claim of convergence, divergence, or cycling.

## Status

Phase P0 is complete. The package now has an arbitrary-precision evaluator,
production Brent cycle detection, an independent hash-set oracle, schema
validation, and a deterministic 500--1000 digit baseline. E000 evaluated 600
trajectories and preserved raw data, benchmarks, metadata, and analysis. No
100,000-candidate experiment has been run.

## Planned workflow

1. Generate a deterministic manifest of candidates and provenance.
2. Evaluate it with resumable workers and exact cycle detection.
3. Preserve append-only raw records in `results/<experiment-id>/`.
4. Validate and summarize those records into `reports/<experiment-id>/`.
5. Compare quality and cost, analyze structural features, and register the
   next strategy before running it.

Every experiment will be reproducible from a committed configuration, seed
manifest, software revision, and documented execution environment. See
[`RESEARCH_PLAN.md`](RESEARCH_PLAN.md), [`ARCHITECTURE.md`](ARCHITECTURE.md),
and [`STRATEGIES.md`](STRATEGIES.md) for the full design.

## Command-line interface

```bash
python -m bigcollatz pilot --per-digit 100
```

General-purpose manifest, sharding, and resume commands remain P1 work.

## Repository map

| Path | Purpose |
| --- | --- |
| `RESEARCH_PLAN.md` | hypotheses, experimental protocol, and analysis plan |
| `ARCHITECTURE.md` | components, data model, correctness, and checkpointing |
| `STRATEGIES.md` | strategy registry, including rejected and untested ideas |
| `EXPERIMENTS.md` | append-only experiment ledger |
| `DECISIONS.md` | consequential decisions and rationale |
| `TODO.md` | prioritized implementation plan |
| `results/` | raw machine-readable outputs (large artifacts stay uncommitted) |
| `reports/` | derived summaries and plots |

## Scope and safety limits

Candidates must be positive and have 500--1000 decimal digits. Evaluations may
have configurable operational safety limits, and may also be interrupted by a
user stop, process shutdown, or resource exhaustion. These events are reported
only as censored computations with the applicable interruption reason; they
are never mathematical outcomes. Conclusions are empirical associations, not
proofs about Collatz.
