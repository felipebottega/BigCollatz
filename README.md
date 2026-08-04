# BigCollatz

BigCollatz is a small experimental Python program for comparing ways to choose
500--1000 digit starting integers for Collatz trajectories. It favors exact,
readable code and plain JSONL/JSON reports over execution infrastructure.

For `n > 0`, one unaccelerated step is `n / 2` when even and `3n + 1` when odd.
Evaluation continues until `1` is reached or an exact state repeats. Optional
safety limits produce censored records, never mathematical conclusions.

## What is included

- a constant-memory exact evaluator and a hash-set test oracle;
- a deterministic, uniformly sampled baseline generator;
- a sequential six-stratum pilot runner;
- append-only JSONL output, basic benchmarks, and statistical reports;
- unit tests and strategy notes.

There is deliberately no sharding, scheduler, checkpoint orchestration,
persistent cache, complex manifest, or multi-worker pipeline.

## Run

```bash
python -m unittest discover -v
python -m bigcollatz pilot --per-digit 100
```

The pilot writes raw records to `results/e000-p0-pilot/raw/part-00000.jsonl`
and summaries to `reports/e000-p0-pilot/`. Each record retains only useful
result and reproducibility fields: start, digit count, steps, maximum, outcome,
runtime, strategy, and small evaluator/seed identifiers.

See `ARCHITECTURE.md` for the complete program flow, `STRATEGIES.md` for search
ideas, and `EXPERIMENTS.md` for completed runs. S1 remains a note and has not
been implemented.
