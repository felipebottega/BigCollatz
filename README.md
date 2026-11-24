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

1. **Pick a pattern.** The program chooses how many odd steps go uphill and
   how many go downhill. Each pattern has one uphill stretch followed by one
   downhill stretch.
2. **Combine the steps.** The program treats each stretch as one block and
   combines the blocks into a single equation. The equation asks whether
   following the whole pattern could return to the starting number.
3. **Decide whether it can close.** The program checks the equation using
   remainders, which keeps the arithmetic small even for huge patterns.
   Steiner's theorem rules out every nontrivial loop with one uphill stretch
   and one downhill stretch.

The search covers this one family of patterns. A nontrivial loop would need
at least two uphill stretches and two downhill stretches. See the
[mathematical guide](ALGEBRAIC_PROJECT.md) for how the program chooses patterns
and checks the equation.

## Lower bound for a nontrivial cycle

If a different loop exists, it contains at least **72,057,431,991 odd steps**
and **186,265,759,595 total steps**. The total counts every multiply-and-add
operation and every division by 2. See the [derivation](ALGEBRAIC_PROJECT.md#lower-bound-for-a-nontrivial-cycle)
and [Barina's verification (2025)](https://doi.org/10.1007/s11227-025-07337-0).

## Try it

From the project directory, with Python 3.11 or newer:

```bash
python -m collatz_algebra.cli --search-cycles 150000000000 --minimum-period 186265759595
```

- `--search-cycles` caps the number of odd steps in each pattern at
  150 billion. The program works with the two block sizes, so it can check
  huge patterns without stepping through them.
- `--minimum-period` sets the minimum number of total steps for a pattern
  to pass the length check.

The program generates and checks the patterns in the same run. This example
prints a JSON report with 11 candidates and the conclusion
`all_candidates_rejected`. A smaller ceiling can yield `no_candidates`.
Exit code `0` means the report was produced successfully. The report gives
the mathematical result.

Run the tests with `python -m unittest discover -v`.
