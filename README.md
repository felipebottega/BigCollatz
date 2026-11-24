# BigCollatz

BigCollatz uses algebra to check whether a pattern of Collatz steps could
bring a number back to where it started.

The Collatz rule is simple. If a number is even, divide it by 2. If it is
odd, multiply it by 3 and add 1. The known loop is `1 → 4 → 2 → 1`.
Finding a different loop of positive numbers would disprove the conjecture.

## How the search works

The patterns describe steps between odd numbers. To reach the next odd number,
apply `3n+1` and divide by 2 until the result is odd. For example, the odd
terms `27 → 41 → 31 → 47 → 71` go up, down, then up twice. Those last two
increases belong to the same uphill stretch.

1. **Check the search range.** The program uses known bounds to see whether
   the chosen step limit leaves room for a cycle in the families it samples.
2. **Build different patterns.** Some start with a checked stretch around
   a valley. Others are sampled without a fixed starting stretch.
3. **Check each pattern.** The program uses small remainders and bounds on
   the values at the valleys to rule out patterns that cannot close. When
   those checks cannot decide, it tests the full equation in pieces using remainders.
4. **Refine the search.** The program scores each pattern and tries
   variations of the best ones at the next level. It also saves some of
   each level for fresh patterns.

The score tells us how closely a pattern matches one requirement for
closing a cycle. A pattern can score well and still fail to close. See the
[mathematical guide](ALGEBRAIC_PROJECT.md) for the score and its limits.

## Lower bound for a nontrivial cycle

If a different loop exists, it contains at least **72,057,431,991 odd steps**
and **186,265,759,595 total steps**. The total counts every multiply-and-add
operation and every division by 2. See the [derivation](ALGEBRAIC_PROJECT.md#lower-bound-for-a-nontrivial-cycle)
and [Barina's verification (2025)](https://doi.org/10.1007/s11227-025-07337-0).

## Try it

From the project directory, with Python 3.11 or newer:

```bash
python -m collatz_algebra.cli --search-cycles 200000000000 \
  --cases-per-level 24 --depth 3 --seed 0 \
  --checkpoint-dir search-checkpoints --output search.json
```

- `--search-cycles` sets the maximum number of odd steps per pattern.
- `--cases-per-level` sets how many distinct patterns to check at each level.
- `--depth` sets the number of levels.
- `--seed` lets you reproduce a search or try a different sample.
- `--checkpoint-dir` saves progress on modular proofs. Rerun the same
  command with the same settings to resume those checks.

At 200 billion, the mathematical bound requires at least 3,543,773,083
ups and an equal number of downs. The sampler can work at that scale.
The default sampler packs sequences into repeated blocks.
With `--independent-runs`, it samples the steps individually so the divisions
can vary even within one downhill stretch. That can take much more memory.

Look at `totals` and `levels` in the JSON report. A completed search gives
each candidate a score and an exact decision. One nonzero remainder
rules out a proposed starting value. A cycle is confirmed only when the
zero remainders prove the equation holds exactly. The verifier avoids
building the giant coefficients or multiplying all the moduli together.
Confirmation can still require many checks. An interruption leaves the
current candidate undecided.

Run the tests with `python -m unittest discover -v`. Install the optional
GMP/MPFR dependency with `python -m pip install '.[large]'` to include the
independent giant-word audit.
