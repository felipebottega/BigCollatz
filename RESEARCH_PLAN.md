# Research Plan

The practical question is whether simple candidate-selection strategies find
longer exact Collatz trajectories than a uniformly sampled control.

For every candidate, record its starting integer, decimal digits, unaccelerated
trajectory length, maximum reached, outcome, runtime, and strategy. Compare raw
trajectory lengths overall and within the same decimal-digit stratum using
count, mean, median, p90, maximum, and the best starting integer. Interrupted
runs remain censored and are never assigned a completed length.

Work iteratively: describe a strategy, generate a modest deterministic sample,
run the exact evaluator, retain JSONL, and inspect a generated summary. Charge
generation and evaluation cost when comparing strategies. Results are empirical
sample descriptions, not evidence of a proof or of a new cycle without exact
repetition.

The current S0 baseline covers six strata from 500 through 1000 digits. The next
guided strategy may be explored only after its small construction and comparison
protocol are clear. S1 is not implemented in the current project.
