# Architecture

## Symbolic cycle search

`collatz_algebra` represents exponent words with concatenation and repetition.
The CLI verifies bounded words exactly and uses a theorem to decide the
symbolic two-run family. See [the algebraic model](ALGEBRAIC_PROJECT.md).

## Bounded cycle-equation search

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
