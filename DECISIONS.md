# Decision Log

## D001 — canonical metric is the unaccelerated map

**Decision:** Count each application of the map in the README; optimizations
must reconstruct exactly that count. Start `1` has length zero.

**Reason:** Accelerated conventions differ and otherwise make results
incomparable. **Consequence:** batched operations need boundary-aware tests.

## D002 — exact repetition is distinct from a long run

**Decision:** Only full-bigint equality within one trajectory establishes a
repeated state. One million steps is merely a recorded threshold. Reaching `1`
classifies the known cycle as ordinary convergence.

**Reason:** runtime length alone supplies no evidence of a cycle.

## D003 — manifests and raw results are immutable

**Decision:** Freeze candidate manifests before evaluation; append raw records
and regenerate summaries rather than editing data in place.

**Reason:** prevents adaptive leakage, enables audits, and makes resume safe.

## D004 — JSON big integers are decimal strings

**Decision:** Serialize Collatz states as canonical decimal strings.

**Reason:** common JSON consumers silently lose precision for large numeric
literals. Integer counters and nanosecond timings remain JSON integers.

## D005 — Python-first, backend-neutral evaluator

**Decision:** Build the reference evaluator in Python and define a narrow
backend contract before considering Rust/GMP.

**Reason:** rapid correctness work with native arbitrary precision; profiling
and differential tests will determine whether native complexity is worthwhile.

## D006 — conservative memoization and bounded exact cycle modes

**Decision:** Cache only certified suffixes to `1`; begin with full-state-set
cycle detection and add Brent mode for memory-bounded production runs.

**Reason:** cached/censored paths and hash-only detection can create invalid
claims. **Tradeoff:** Brent may evaluate more transitions and does not by itself
provide all maximum-prefix metrics, so evaluator and detector concerns remain
explicit.

## D007 — quality and cost form a Pareto comparison

**Decision:** Do not collapse trajectory length and compute cost into an
arbitrary single score for strategy conclusions.

**Reason:** a small length gain at extreme cost is not automatically progress.

## D008 — online research limitation is recorded

**Decision:** Treat the initial bibliography as orientation and verify primary
sources before importing detailed algorithms or claims.

**Reason:** network access was blocked during this initial planning pass; the
architecture therefore relies only on conservative, independently testable
mathematical invariants.
