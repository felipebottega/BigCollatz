# Experiment Ledger

## E000 — historical multi-stratum pilot

- **Status:** complete; corrected and rerun 2026-08-04.
- **Scale:** 600 trajectories, with 100 at each of 500, 600, 700, 800, 900,
  and 1000 decimal digits.
- **Generator:** the former S0 SHA-256 expansion with digit-stratum domain separation and
  uniform rejection sampling.
- **Result:** all 600 reached `1`; mean trajectory length 18,008.112, median
  17,984, p90 23,930, and maximum 25,873.
- **Artifacts:** raw JSONL under `results/e000-p0-pilot/`; JSON and Markdown
  summaries under `reports/e000-p0-pilot/`.
- **Limitations:** one deterministic sample on one machine. It describes these
  observations and makes no general claim about Collatz trajectories.

The report gives the top ten actual starting integers and separate count, mean,
median, p90, maximum, and best start for every digit stratum. S1 has not been
implemented or run. This 600-candidate pilot is historical documentation only;
its multi-stratum layout and raw-record storage are not used by new experiments.

New experiments use 10,000 distinct 1000-digit candidates by default and the
`S0-uniform-deterministic` strategy.
