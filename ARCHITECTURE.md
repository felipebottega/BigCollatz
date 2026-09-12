# Architecture

The normal experiment flow is deliberately small and sequential:

```text
candidate generator -> exact evaluator -> aggregate statistics and top 10
```

`bigcollatz/experiment.py` selects one of the deterministic strategies in
`bigcollatz/generator.py`, evaluates each candidate, and writes compact result
artifacts. It retains completed trajectory lengths for statistics, a ten-entry
heap for ranking, and any cycle candidates; it does not retain raw trajectories
or every result record.

`bigcollatz/evaluator.py` is the single authoritative trajectory loop. It retains
the exact initial integer, the current integer, and an iteration counter rather
than a trajectory-local collection of every state. A cycle is reported only when
the trajectory returns exactly to its initial integer, at which point the counter
is its period. The optional metrics path uses the same loop, preventing the pilot
and normal evaluators from drifting apart.

Normal experiment directories contain `summary.json`, `summary.md`, and
`top_10.json`. After successful completion, the local top ten is merged by
starting integer with `results/global_top_10.json`. Adaptive pilots use their own
summary and ranking artifacts and deliberately leave the global top ten
unchanged. Large integers are decimal strings in JSON to preserve exact values.

`bigcollatz/adaptive.py` adds strict cell and candidate validation, compact
recurrence metrics, deterministic cross-cell ranking, and independent cycle
verification for small adaptive pilots. `bigcollatz/p007.py` is the reproducible
construction of the completed P007 pilot, not a second general-purpose runner.

The legacy trajectory experiment path intentionally has no schedulers, workers,
persistent caches, database, schema framework, or storage abstraction.

New trajectory experiments enforce at least 1,000,001 decimal digits at both the
generator and runner boundaries. The requested exact digit count has no software
maximum and is constrained only by resources. The default batch is deliberately
small (4 candidates), with modular-residue guidance by default, so algebraic
candidate quality can take priority over regular volume. Trajectory-length
statistics remain diagnostic output for compatibility, not the search target.

## Algebraic cycle search

`bigcollatz/odd_map.py` implements the accelerated odd map and exact replay of an
exponent word. `bigcollatz/cycle_equation.py` composes that word into an affine
closure equation, solves it with arbitrary-precision integer division, and
canonicalizes cyclic words with linear-time rotation and primitivity algorithms.

`bigcollatz/cycle_search.py` uses a sum-constrained FKM necklace recursion within
explicit odd-period and total-division bounds. It generates primitive
lexicographically least cyclic words directly instead of enumerating every
ordered composition and filtering equivalent rotations afterward. The necessary
positivity condition `2**S > 3**k` removes impossible totals before enumeration.
Canonical-vector ordinals are deterministically assigned to shards; each shard
applies exact small-prime divisibility filters before constructing the full
equation. Atomic JSON checkpoints contain
the configuration signature, exact cursor, counters, and discoveries, allowing
safe resumption without silently changing the searched region.

This path has no decimal-digit bound and does not depend on the 1,000-digit
trajectory generators. Decimal conversion happens only when a verified integral
candidate is persisted. The older experiment runner remains available as a
trajectory research tool and is not part of the algebraic enumeration.
