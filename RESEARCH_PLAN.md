# Research Plan

## 1. Research question

Can deterministic or systematically guided construction produce 500--1000
decimal-digit starting values with longer Collatz trajectories than
compute-matched baselines, and which measurable structures predict that
performance?

The primary response is the number of *unaccelerated* map applications before
first reaching `1`. Runtime and integer-operation cost are co-primary practical
measurements. Runs that do not reach `1` within limits are right-censored and
must not be assigned a fabricated trajectory length.

## 2. Mathematical guardrails

- Positive integers only; decimal digit count is checked exactly from the
  generated integer.
- Evaluation implements the stated map one step at a time conceptually. An
  optimized odd step may compute `(3n+1) >> v2(3n+1)` in one operation, but
  adds exactly `1 + v2(3n+1)` to the unaccelerated step count and checks limits
  at the equivalent boundaries.
- `reached_one` takes precedence over recognizing the known cycle.
- `repeated_state` requires equality of two arbitrary-precision integers from
  the same trajectory. A hash collision is never sufficient.
- Passing 1,000,000 steps sets `exceeded_million_steps=true`; it says nothing
  about cycling.
- Maximum state and bit length include the starting state and every produced
  state. No state is converted to floating point.
- Cached suffixes may shorten work only when their exact semantics and maxima
  are known. A cache hit cannot be used to infer absence of a cycle unless the
  cached suffix is independently certified.

## 3. What prior work changes about the design

The established literature treats parity vectors/congruence classes, stopping
times, inverse iteration, and large computational verification as distinct
tools. That motivates four non-naive choices: (1) compare residue-balanced
controls instead of claiming that modular structure alone is predictive; (2)
construct finite parity prefixes through congruences rather than sampling huge
integers; (3) measure both total stopping time and computational cost; and (4)
make exhaustive claims only over an explicitly defined finite manifest.

Key starting references:

1. Jeffrey C. Lagarias, “The 3x+1 Problem: An Annotated Bibliography
   (1963--1999),” arXiv:math/0309224.
2. Jeffrey C. Lagarias, ed., *The Ultimate Challenge: The 3x+1 Problem*,
   American Mathematical Society, 2010.
3. Terence Tao, “Almost all orbits of the Collatz map attain almost bounded
   values,” *Forum of Mathematics, Pi* 10 (2022), e12,
   doi:10.1017/fmp.2022.8.
4. David Barina, “Convergence verification of the Collatz problem,” *The
   Journal of Supercomputing* 77 (2021), 2681--2688,
   doi:10.1007/s11227-020-03368-x.

These works do not provide a known optimal generator for 500--1000 digit total
stopping time records. Heuristics based on random-walk intuition are hypothesis
sources, not guarantees. Network access was unavailable during this initial
repository pass, so bibliographic details and any additional implementation
claims must be rechecked against primary texts before the relevant strategy is
implemented.

## 4. Experimental unit and controls

An experimental unit is one unique starting integer plus its generator
provenance. Deduplication happens before evaluation, while aliases are retained
in the manifest. The standard full experiment contains approximately 100,000
unique starts, split into deterministic shards.

Each strategy receives comparable candidate-count and wall/CPU budgets.
Controls are:

- a counter-based pseudorandom baseline mapped uniformly into a declared digit
  interval (reproducible, but never the central search method);
- stratified modular/digit baselines matching the strategy's digit lengths and
  unavoidable congruences;
- a deterministic low-discrepancy bit-pattern generator;
- incumbent replay to detect evaluator regressions.

No consecutive interval is used as the principal baseline. Candidate-generation
cost, evaluator cost, and analysis cost are reported separately.

## 5. Iterative protocol

### Phase A: preregister

Create a committed experiment entry containing hypothesis, strategy version,
parameters, budget, candidate ordering, evaluator limits, controls, success
metrics, and stop rules. Freeze a manifest hash before inspecting outcomes.

### Phase B: pilot

Run correctness fixtures, then 100--1,000 candidates to estimate throughput,
censoring, result size, and checkpoint behavior. Pilot results are labeled and
never silently pooled into the full run.

### Phase C: full evaluation

Generate about 100,000 starts. Workers atomically claim deterministic shards,
append raw records, fsync checkpoints, and emit progress (completed, rate,
ETA, current/best length, censored counts). Resume skips record IDs already
validated by checksum.

### Phase D: locked summary

Validate schema and uniqueness, then calculate count; reached/censored/repeated
counts; max, arithmetic mean, median, p90/p95/p99/p99.9; fixed logarithmic and
scientifically useful histogram bins; counts above preregistered thresholds;
top starts; CPU and wall time per sequence; bigint work proxies; and improvement
over matched controls and the previous strategy.

Means and percentiles of completed trajectories exclude censored observations
and are labeled accordingly. Censoring is separately summarized; survival-style
estimates may be added when censoring is material.

### Phase E: analyze and iterate

Relate outcomes to preregistered features: digit/bit length, low residues,
initial parity prefix, odd-step fraction, valuations `v2(3n+1)`, initial run
lengths, Hamming weight, and maximum excursion. Use held-out shards or nested
selection to avoid reporting optimization-set associations as validation.
Register the next hypothesis in `STRATEGIES.md`, including negative results.

## 6. Comparison metrics

Primary quality: maximum completed total stopping time, with top-k values and
bootstrap uncertainty for distributional summaries. Efficiency: completed
evaluations/CPU-second, bigint limb-operations proxy, and generation plus
evaluation CPU time per candidate. Report a Pareto frontier (quality versus
cost), not a single winner that hides tradeoffs.

Duplicate yield, censoring rate, and memory/disk costs are required diagnostics.
Multiple strategy comparisons must disclose the number tried; promising results
are validated on a newly generated, frozen manifest.

## 7. Risks and limitations

- **Unknown convergence:** a resource-limited run cannot establish divergence.
- **Loop detection cost:** exact detection and reusable suffix caching can
  compete for memory; constant-memory algorithms cost extra evaluations.
- **Heavy tails:** maxima are unstable and comparisons at 100,000 samples can
  have large variance.
- **Selection bias:** repeatedly mutating winners overfits the evaluator budget.
- **Bigint growth:** rare excursions can dominate runtime and memory.
- **Congruence illusion:** forcing a favorable finite prefix may merely defer,
  rather than increase, eventual descent.
- **Metric ambiguity:** accelerated and unaccelerated step counts are easily
  confused; only unaccelerated counts are canonical here.
- **Hardware variability:** wall time alone is not portable; record CPU time,
  platform, library versions, and work proxies.
- **Verification:** computations provide experimental records, never a proof of
  the conjecture or a novel cycle without independently replayed exact equality.
