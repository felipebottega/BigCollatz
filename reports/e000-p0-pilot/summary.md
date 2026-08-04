# E000 P0 pilot analysis

## Experimental result

The deterministic SHA-256 counter baseline produced 100 starts in each of six
decimal-digit strata (500 through 1000), for 600 exact trajectories. All 600
reached `1`; no exact repeated state and no operational interruption occurred.
Mean total stopping time was 18,023.795 steps, median was 18,078.5, linearly
interpolated p90 was 23,761.2, and the maximum was 25,678
(`d1000-00093`). The largest maximum excursion added four decimal digits.

These observations describe this fixed sample, not all Collatz trajectories.

## Benchmark

Sequential CPython evaluation took 22.174 seconds wall and 17.092 seconds CPU.
Overall throughput was 27.06 trajectories/s, mean per-record evaluator time was
27.34 ms, and peak process RSS was 27,960 KiB. Throughput declined with size:
72.05/s at 500 digits, 55.39/s at 600, 42.47/s at 700, 34.88/s at 800, 26.35/s
at 900, and 23.86/s at 1000 digits.

At the measured end-to-end sequential rate, projected runtimes are 36.96 seconds
for 1,000 trajectories, 369.56 seconds (6.16 minutes) for 10,000, and 3,695.60
seconds (61.59 minutes) for 100,000. These linear point estimates exclude
parallelization, checkpointing, thermal effects, and changed storage overhead.

## Baseline weakness and next strategy

The generator is reproducible and spreads values across each decimal interval,
but its hash output is intentionally ignorant of Collatz structure. It neither
controls early parity words nor favors delayed descent, affine growth, unusual
`v2(3n+1)`, or promising residue classes. Digit count explains much observed
work increase, so unmatched comparisons would reward size rather than
intelligence. Only 100 samples per stratum also makes upper-tail estimates noisy.

The first intelligent search should be S1, a preregistered parity-prefix
congruence beam. It should construct residues modulo `2^k` that force selected
early parity words, score predicted affine growth and delayed descent, then
deterministically lift winners into each digit stratum. Every guided start needs
digit- and residue-matched S0 controls, generation cost must count against the
budget, and a frozen held-out batch must test survival beyond the forced prefix.
S1 is proposed, not implemented.

## Reproducibility

Raw records and metadata are under `results/e000-p0-pilot/`; machine-readable
summary and benchmark files are beside this report. Raw SHA-256 is
`2dbc1c7df598c6d6fd1c039db18b87cadabb13ee89c47783b29b4ac03840cd22`.
Percentiles use linear interpolation at `(n - 1) p`.
