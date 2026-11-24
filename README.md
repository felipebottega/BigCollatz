# BigCollatz

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

Search the first implemented representation family directly:

```bash
python -m collatz_algebra.cli --search-two-run 1000000 --minimum-period 1
```

The search uses continued-fraction proposals near the algebraic positivity
boundary. Every proposed `1^u 2^v` word is rejected definitively by
Steiner's one-cycle theorem: the single increasing run followed by a single
decreasing run cannot be a nontrivial positive cycle. This closes the vacuous
modular survivors previously reported at billion-scale periods. See
[`RESEARCH_SYMBOLIC.md`](RESEARCH_SYMBOLIC.md) for the derivation,
bibliography, proof boundary, and the required next search space (`m >= 2`).

## Setup and tests

BigCollatz requires Python 3.11 or newer and has no runtime dependencies.

```bash
python -m pip install -e .
python -m unittest discover -v
```

## Search cycle equations

```bash
python -m bigcollatz search-cycles c001-k20-s40 \
  --max-odd-period 20 \
  --max-total-divisions 40
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

The defaults are intentionally small. The number of positive compositions grows
combinatorially, so serious searches should increase bounds gradually, measure
the explored vector count, and distribute shards. No finite bounded search proves
that a cycle does not exist outside its stated `(k, sum(a_i))` region.
