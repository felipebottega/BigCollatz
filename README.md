# BigCollatz

BigCollatz runs exact, reproducible experiments on the unaccelerated Collatz map
for 1,000-digit positive integers. Its scientific objective is to find a
nontrivial cycle; long trajectories are only a search heuristic. One step is
`n / 2` for even `n` and `3n + 1` for odd `n`.

Every trajectory records each visited integer and stops at the first exact
repetition or at `1`. Verified cycle candidates are persisted separately from
the trajectory ranking, so a discovery cannot be discarded for missing the top
ten. Normal experiments retain aggregate statistics and only their ten best
completed trajectories rather than raw trajectories or every result record.

## Setup and tests

BigCollatz requires Python 3.11 or newer and has no runtime dependencies.

```bash
python -m pip install -e .
python -m unittest discover -v
```

## Run an experiment

```bash
python -m bigcollatz run e001
python -m bigcollatz run e002 \
  --strategy S1-parity-prefix-top10 \
  --seed guided-v1
```

A run evaluates 10,000 deterministic candidates by default. Use `--count` for
a smaller trial and `python -m bigcollatz run --help` for all options. Guided
strategies read parent trajectories from committed result files, so they require
the corresponding source artifact to be present.

The CLI supports the uniform control (`S0`) and the guided strategies `S1`
through `S6`. Their definitions and data dependencies are documented in
[`STRATEGIES.md`](STRATEGIES.md). Completed experiments and pilots are recorded
in [`EXPERIMENTS.md`](EXPERIMENTS.md) and
[`RESEARCH_LOG.md`](RESEARCH_LOG.md); the current conclusion and next action
live in [`RESEARCH_STATE.md`](RESEARCH_STATE.md).

Normal runs write `summary.json`, `summary.md`, and `top_10.json` beneath
`results/<experiment-id>/`, then merge their winners into
`results/global_top_10.json`. Large integers remain complete decimal strings in
machine-readable files and are abbreviated only in Markdown tables.

The project intentionally has no sharding, checkpointing, scheduler, persistent
cache, database, or worker orchestration.
