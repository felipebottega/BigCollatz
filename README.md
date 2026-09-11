# BigCollatz

BigCollatz runs exact, reproducible experiments on the unaccelerated Collatz map
for positive integers with **more than 1,000 decimal digits**. Its scientific objective is to find a
nontrivial cycle; long trajectories are only a search heuristic. One step is
`n / 2` for even `n` and `3n + 1` for odd `n`.

The primary cycle-search path is not limited to a decimal interval. It enumerates
exponent words for the accelerated map on odd integers, solves each resulting
closure equation exactly, removes rotational and repeated-word duplicates, and
replays every integral solution. Search bounds apply to odd period and total
divisions by two, not to the number of digits in a candidate.

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

A run evaluates 100 deterministic guided candidates by default using the S1
top-trajectory lineages, favoring a small, focused set over a broad regular
sweep. The uniform S0 strategy remains available as an explicit control. Use
`--digits N` to select any exact
candidate size of at least 1,001 digits; there is no application-level maximum.
The practical ceiling is available memory and execution time. Use `--count` and
`python -m bigcollatz run --help` for all options. Guided
strategies read parent trajectories from committed result files, so they require
the corresponding source artifact to be present.

## Search cycle equations

```bash
python -m bigcollatz search-cycles c001-k20-s40 \
  --max-odd-period 20 \
  --max-total-divisions 40
```

The search enumerates positive exponent vectors `(a_0, ..., a_{k-1})` for
`T(n) = (3n + 1) / 2**v2(3n + 1)`. Composition gives the exact candidate
`n = A / (2**sum(a_i) - 3**k)`.

Candidate generation is cycle-directed rather than trajectory-directed: it uses
a sum-constrained necklace recursion to construct only primitive,
lexicographically least exponent words. It therefore does not first generate all
ordered compositions and then discard their rotations. Totals are visited from
the sharp positivity boundary `2**S > 3**k` upward, and necessary small-prime
divisibility tests reject impossible closure equations before large numerators
are built.

Consequently, rotations of one cycle and repetitions of a shorter cycle are not
searched again. No previous long trajectory, decimal suffix, fixed digit count,
or random starting integer participates in candidate selection. The trivial
`1 -> 4 -> 2 -> 1` cycle is excluded unless `--include-trivial` is supplied.
Progress is atomically checkpointed under `results/<search-id>/checkpoint.json`;
rerunning the same command resumes it or returns the completed result. Use
`--shard-count N --shard-index I` to split the deterministic enumeration among
independent processes or machines. Each shard needs a distinct search ID.

The defaults are intentionally small. The number of positive compositions grows
combinatorially, so serious searches should increase bounds gradually, measure
the explored vector count, and distribute shards. No finite bounded search proves
that a cycle does not exist outside its stated `(k, sum(a_i))` region.

Cycle-equation search is different from trajectory sampling: it enumerates
possible cycle structures and derives their exact members, so its bounds are
period and exponent sum rather than starting-number magnitude. The greater-than-
1,000-digit rule applies to all newly generated trajectory candidates.

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

The legacy trajectory runner intentionally has no scheduler, persistent cache,
database, or worker orchestration; algebraic cycle searches add only deterministic
sharding and local atomic checkpoints.
