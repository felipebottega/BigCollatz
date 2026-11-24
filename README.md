# BigCollatz

BigCollatz investigates positive Collatz cycles using algebraic equations.
The symbolic search generates two-run patterns and evaluates them in the
same execution.

## Lower bound for a nontrivial cycle

Any nontrivial positive Collatz cycle must contain **at least 72,057,431,991
odd steps** and have an **unaccelerated period of at least 186,265,759,595
steps**. The unaccelerated period counts both the odd operations `3n+1` and
the divisions by 2. These bounds are derived from convergence verification
below `2^71`. [Barina, *Improved verification limit for the convergence of
the Collatz conjecture* (2025)](https://doi.org/10.1007/s11227-025-07337-0).

To see how the verification gives a cycle bound, let `k` count odd steps
and `S` count divisions by 2. Each odd member `n` of a nontrivial cycle is
at least `2^71`. Multiplying the odd-to-odd updates around the cycle gives
`2^S = product(3 + 1/n)`, so
`log2(3) < S/k < log2(3) + 1/(3 * 2^71 * ln(2))`.
This interval lies strictly between the fractions
`103768467013/65470613321` and `10439860591/6586818670`.
Their cross products differ by one, so any fraction strictly between them
has numerator and denominator at least the respective sums. Thus
`S >= 114,208,327,604`, `k >= 72,057,431,991`, and the period `S + k`
has the lower bound above.

## Symbolic cycle search

`collatz-algebra` generates candidates and evaluates every candidate in the
same run.

A run is a stretch of consecutive increases or decreases between odd terms.
To get from one odd term to the next, apply `3n+1` and divide by 2 until the
result is odd. For example, the odd terms `27 → 41 → 31 → 47 → 71` rise,
fall, then rise twice. The fall separates two rising runs, and the last two
increases belong to the same run.

In a cycle, runs are counted around the entire loop, including the return
to the starting term. A two-run cycle would rise from its minimum to its
maximum and then fall back to its minimum. The search covers patterns that
divide by 2 once per rising step and twice per falling step, with at least
one step in each run. Steiner's theorem excludes nontrivial positive cycles
with one rising run and one falling run. A search for a nontrivial cycle
therefore needs to consider patterns with at least two rising runs and two
falling runs.

Run the symbolic two-run search with a ceiling of 150 billion odd steps
and the lower bound on the unaccelerated period:

```bash
python -m collatz_algebra.cli --search-two-run 150000000000 --minimum-period 186265759595
```

1. **Choose the size of each candidate pattern.** Compute the convergents of
   the continued fraction for `log2(3)`. Keep the fractions `S/k` above
   `log2(3)` with `k` at or below the chosen ceiling and `k < S < 2k`.
   Here `k` counts odd steps and `S` counts divisions by 2. Approximating
   from above selects pairs near the boundary `2^S > 3^k`, a necessary
   condition for a positive cycle.

2. **Build a pattern with two runs.** For the first `2k - S` odd steps,
   divide by 2 once after each `3n+1`. For the next `S - k` odd steps,
   divide by 2 twice after each `3n+1`. Together the runs account for
   exactly `k` odd steps and `S` divisions.

3. **Check necessary conditions for closure.** Compare the total period
   `k + S` with the given lower bound. Compose the pattern into the
   closure equation `(2^S - 3^k)n = A`, where `A` is the constant from
   composing the updates. Test whether the equation can hold modulo
   small prime divisors of `2^S - 3^k`. A failed check rules out the
   pattern.

4. **Apply Steiner's theorem.** In a nontrivial positive cycle, the first
   run would strictly increase and the second would strictly decrease.
   Steiner's theorem excludes such cycles with exactly one local minimum,
   so every proposed pattern in this family is rejected.

Each retained convergent gives one candidate pattern. Raising the ceiling
adds candidates only when more convergents satisfy the selection rules.
The JSON report records the checks for each candidate. Its `conclusion` is
`all_candidates_rejected` when every generated pattern is ruled out, or
`no_candidates` when the bounds yield no proposals. Exit code `0` indicates
that the report was produced successfully.
See [the symbolic analysis](ALGEBRAIC_PROJECT.md#symbolic-two-run-family).

## Setup and tests

BigCollatz requires Python 3.11 or newer and has no runtime dependencies.

```bash
python -m pip install -e .
python -m unittest discover -v
```
