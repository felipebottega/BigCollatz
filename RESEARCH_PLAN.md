# Research Plan

The practical question is whether simple candidate-selection strategies find
longer exact Collatz trajectories than the deterministic uniform control.

Each new experiment evaluates 10,000 distinct 1000-digit candidates. Its
summary records outcome counts, mean, median, p90, p99, maximum, wall time, and
throughput. Only the experiment top ten and persistent global top ten retain
complete result details. Interrupted runs remain censored.

Work iteratively: describe a strategy, run the exact evaluator, and inspect the
small generated summaries. Results are empirical sample descriptions, not a
proof or evidence of a new cycle without exact repetition. S1 is not currently
implemented.
