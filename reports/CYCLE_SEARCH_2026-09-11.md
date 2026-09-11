# Cycle-search run — 2026-09-11

## Objective

Exercise the exact algebraic cycle-search path, verify its positive control,
and search a practical bounded region for a nontrivial positive Collatz cycle.

## Executions

### Positive control

Command:

```bash
python -m bigcollatz search-cycles c000-trivial-sanity-k3-s6 \
  --max-odd-period 3 \
  --max-total-divisions 6 \
  --include-trivial \
  --checkpoint-every 10
```

The run completed and found the expected cycle with odd member `1`, exponent
word `(2)`, odd period 1, and unaccelerated period 3. It generated 15 canonical
vectors, rejected 13 through necessary modular filters, and solved two closure
equations. This confirms that the configured search can recover the known
`1 -> 4 -> 2 -> 1` cycle.

### Nontrivial-cycle search

Command:

```bash
python -m bigcollatz search-cycles c001-k12-s24 \
  --max-odd-period 12 \
  --max-total-divisions 24 \
  --checkpoint-every 10000
```

The run completed in approximately 13.8 seconds of wall-clock time. It covered
odd periods 1 through 12 and exponent sums from each period's strict positivity
boundary through 24. The enumerator represented a brute-force region of
9,671,963 ordered compositions using 963,213 canonical primitive necklaces.
Necessary modular conditions rejected 534,997 vectors and 428,216 closure
equations were solved exactly. There was one integral candidate in the region:
the known trivial cycle, which this run was configured to exclude. Consequently,
the search reported no nontrivial discovery.

## Parameter and operational checks

- The complete test suite passed: 92 tests.
- Repeating the completed `c001-k12-s24` command exercised checkpoint resume and
  returned immediately with `wall_time_ns` equal to zero and the same empty
  discovery list.
- A temporary two-shard search over odd periods through 8 and total divisions
  through 16 processed 3,003 vectors in each shard. Their combined 6,006 vectors
  and discoveries exactly matched the corresponding unsharded run.

## Conclusion and scope

No nontrivial positive Collatz cycle was found within odd period at most 12 and
total divisions at most 24. This is a finite bounded exclusion only; it does not
rule out cycles outside that `(odd period, total divisions)` region. The
positive-control, resume, and shard-partition checks behaved as expected.
