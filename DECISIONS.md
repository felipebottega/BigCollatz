# Decision Log

## Exact metric

Count every application of the unaccelerated Collatz map. Start `1` has length
zero. Reaching `1` takes precedence over recognizing the familiar cycle.

## Exact outcomes

A repeated-state result requires equality of full arbitrary-precision integers.
Operational interruption is a censored computation, not a mathematical outcome.
Brent detection is used for normal evaluation and a state-set implementation is
kept only as a test oracle.

## Simple experiments

Candidate generation is deterministic. Results are appended to plain JSONL and
reports are regenerated from them. The current scale does not justify execution
or storage infrastructure beyond a sequential loop and ordinary files.

## Fair comparison

Raw unaccelerated trajectory length is the primary response. Strategies are
compared under equal digit strata and sample budgets; a composite score cannot
replace the raw measurement. Candidate-generation runtime should be considered
when a nontrivial generator is eventually tested.
