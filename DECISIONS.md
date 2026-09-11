# Decision Log

## Exact metric

Count every application of the unaccelerated Collatz map. Start `1` has length
zero. Reaching `1` takes precedence over recognizing the familiar cycle.

## Exact outcomes

A repeated-state result requires equality of full arbitrary-precision integers.
Operational interruption is a censored computation, not a mathematical outcome.
The evaluator maps each visited integer to its first step so it can report the
cycle entry and period while checking every generated state. Cycle discoveries
are reconstructed and independently verified before they are reported.

## Simple experiments

Candidate generation is deterministic. A run retains only trajectory lengths
needed for statistics and a top-ten heap; it writes no per-trajectory raw file.
The current scale needs only a sequential loop and small ordinary files.

## Fair comparison

Raw unaccelerated trajectory length is the primary response. Strategies are
compared with 1000-digit candidates and equal sample budgets; a composite score
cannot replace the raw measurement. Candidate-generation runtime should be
considered when a nontrivial generator is eventually tested.
