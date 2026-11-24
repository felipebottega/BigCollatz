# BigCollatz

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

The active research path is `collatz-algebra`. It now admits a candidate only
when the selected path is guaranteed to finish with a definitive answer. A JSON
word is verified exactly only when both its odd-step count and total divisions
fit a configurable work bound. Larger generic words are reported as `not_tested`
before their repetitions are expanded or their affine integers are constructed.
The billion-scale symbolic search is restricted to families with a theorem that
decides every generated member.

The approach is intentionally not advertised as an exhaustive search over all
words. See [`ALGEBRAIC_PROJECT.md`](ALGEBRAIC_PROJECT.md) for the model, proof
obligations, eligibility policy, complexity, and limitations.

Ask whether the included billion-scale example is eligible for exact checking:

```bash
python -m collatz_algebra.cli examples/billion_period_word.json
```

The command emits `not_tested` and exits with status `2`: its exact proof would
exceed the default work bound, so the program does not run an inconclusive sieve.
For eligible JSON words, status `0` means a confirmed cycle and status `1` means
an exact rejection. `--exact-work-limit` configures the admission bound; both the
odd-step count and total divisions must fit it.

Run the symbolic two-run search with a ceiling of 200 billion odd steps and
the lower bound above on the unaccelerated period:

```bash
python -m collatz_algebra.cli --search-two-run 200000000000 --minimum-period 186265759595
```

The command proposes a small set of `1^u 2^v` patterns using continued
fractions. It displays proposals below the period bound as rejections.
Steiner's one-cycle theorem excludes the entire family of patterns with
one increasing run and one decreasing run, including those above the bound.
See [the proof and next research directions](RESEARCH_SYMBOLIC.md).

## Setup and tests

BigCollatz requires Python 3.11 or newer and has no runtime dependencies.

```bash
python -m pip install -e .
python -m unittest discover -v
```

## Validate the exact cycle-equation search

Use the known cycle `1 -> 4 -> 2 -> 1` as a positive control:

```bash
python -m bigcollatz search-cycles trivial-check \
  --max-odd-period 1 \
  --max-total-divisions 2 \
  --include-trivial
```

The search enumerates positive exponent vectors `(a_0, ..., a_{k-1})` for
`T(n) = (3n + 1) / 2**v2(3n + 1)`. Composition gives the exact candidate
`n = A / (2**sum(a_i) - 3**k)`.

Candidate generation is cycle-directed rather than trajectory-directed: it uses
a sum-constrained necklace recursion to construct only primitive,
lexicographically least exponent words. It therefore does not first generate all
ordered compositions and then discard their rotations. Totals are visited from
the sharp positivity boundary `2**S > 3**k` upward, and necessary small-prime
divisibility tests reject impossible closure equations before large numerators
are built.

Consequently, rotations of one cycle and repetitions of a shorter cycle are not
searched again. The trivial
`1 -> 4 -> 2 -> 1` cycle is excluded unless `--include-trivial` is supplied.
Progress is atomically checkpointed under `results/<search-id>/checkpoint.json`,
rerunning the same command resumes it or returns the completed result. Use
`--shard-count N --shard-index I` to split the deterministic enumeration among
independent processes or machines. Each shard needs a distinct search ID.

The enumerator is practical for small validation ranges. The number of
positive compositions grows combinatorially, which makes direct enumeration
at the lower bound for nontrivial cycles impractical.
