# Architecture

The whole program has four direct parts:

```text
candidate generator -> evaluator -> JSONL file -> statistical report
```

- `bigcollatz/generator.py` deterministically samples candidates. The baseline
  uses digit-stratum-separated SHA-256 input and rejection sampling.
- `bigcollatz/evaluator.py` applies exact arbitrary-precision Collatz steps.
  Brent cycle detection is the normal implementation; a simple state set is an
  independent test oracle.
- `bigcollatz/model.py` validates results and schema-v1 JSON records. Large
  integers are canonical decimal strings so JSON consumers cannot round them.
- `bigcollatz/experiment.py` runs candidates sequentially, appends their result
  records to one JSONL file, and produces JSON and Markdown summaries.

A result ends as `reached_one`, `repeated_state`, or `interrupted`. Cycle entry
and period exist only for exact repetitions. Operational stopping reasons are
censored and are not interpreted as Collatz outcomes.

## Output

The pilot keeps one raw JSONL file, a short metadata JSON file, and generated
summary/benchmark files. Reports contain raw trajectory-length statistics,
top starting integers, and separate statistics for every digit stratum.

The project does not need shards, checkpoints, rolling checksums, worker
coordination, manifests, resumable scheduling, persistent caches, or storage
abstractions. If the small sequential runner becomes measurably inadequate,
changes should be justified by an experiment rather than planned in advance.
