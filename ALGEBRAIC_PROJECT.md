# Algebraic Collatz project

## Research question

Can large classes of hypothetical nontrivial positive Collatz cycles be
eliminated without generating their terms?

The working scale is a minimum unaccelerated period of 186 billion steps. This
number is a configurable premise of the software, because published bounds may
use different cycle and step conventions. The project never translates that
period premise into a claim about the number of decimal digits of a cycle
member.

This is deliberately a **sieve**, not an exhaustive solver. An arbitrary cycle
of that period contains too much information even to write down. The tractable
search domain consists of exponent words that have a short straight-line
grammar: concatenations and repeated subwords. The hypothesis being tested is
that a hypothetical cycle has enough algebraic structure to admit such a
compressed description.

## Algebraic model

For odd `n`, one accelerated step is

```text
T_a(n) = (3n + 1) / 2^a,    a >= 1.
```

An exponent word with `k` odd steps and `S = sum(a_i)` composes to

```text
T_word(n) = (3^k n + A) / 2^S.
```

Cycle closure therefore requires

```text
(2^S - 3^k)n = A.
```

The old search built `A` and enumerated every exponent. That cannot reach the
working scale. The new implementation instead evaluates the affine triple
`(3^k, A, 2^S)` modulo several integers. Concatenation is affine composition;
repetition is binary exponentiation. Consequently, a subword repeated 100
billion times costs only about 37 modular compositions, rather than 100 billion
trajectory steps.

For any modulus `m`, closure has a solution only if

```text
gcd(2^S - 3^k, m) divides A.
```

Failure is a rigorous certificate that no integer—hence no positive Collatz
cycle—can close with that exponent word. Passing every modulus proves nothing;
it only means that more filters are needed.

## Representation

Candidate words are JSON trees with three nodes:

```json
{"step": 2}
```

```json
{"concat": [{"step": 1}, {"step": 2}]}
```

```json
{"repeat": {"word": {"step": 2}, "times": "186000000000"}}
```

Large counts may be decimal strings so that producers written in languages with
limited JSON-number precision do not corrupt them. A top-level repetition is
immediately rejected as imprimitive: it describes repetitions of a shorter
cycle. Repetition below a concatenation remains useful for structured primitive
templates.

## Pipeline

1. Parse and validate a compressed exponent word.
2. Compute `k`, `S`, and `k + S` symbolically.
3. Enforce the configured period premise.
4. Reject an obvious top-level power.
5. Apply the exact rational positivity bound
   `665*S <= 1054*k => 2^S < 3^k`.
6. Scan small primes and retain only those dividing `2^S - 3^k`, using modular
   powers rather than constructing that enormous coefficient.
7. Evaluate modular affine summaries for those targeted primes by tree
   composition and binary powering.
8. Emit each failed closure congruence as a reproducible certificate.
9. Label survivors accurately: they are not confirmed cycles.
10. When exact confirmation is requested, construct `A` and
    `D = 2^S - 3^k`, require `D > 0` and `D | A`, and replay the resulting odd
    integer through every prescribed exponent.

The reported logarithmic gap is a ranking diagnostic only. It is never used as
a proof because ordinary high-precision decimal arithmetic is not interval
arithmetic.

## Exact confirmation

`collatz-algebra --confirm` adds a separate proof phase. It returns
`confirmed_cycle` only after all of the following exact checks succeed:

1. The closure denominator is positive.
2. `A` is divisible by `2^S - 3^k` with zero remainder.
3. The quotient is a positive odd integer.
4. Every replayed step has exactly the requested value of `v2(3n+1)`.
5. No member repeats before the final return to the starting integer.
6. The final member equals the starting integer.

The confirmed report includes the starting integer, minimum and maximum odd
members, odd period, and unaccelerated period. This is a sufficient check, not a
probabilistic one.

Exact confirmation has explicit odd-step and integer-bit budgets. If either is
exceeded, the result is `resource_limit`, never `confirmed_cycle`. This is an
unavoidable distinction: a modular non-rejection does not supply the enormous
integer quotient or prove every local 2-adic valuation. A billion-scale cycle
can be confirmed economically only if an additional concise algebraic
certificate exists for its particular grammar family; absent such a certificate,
the proof itself has billion-scale information content.

## Complexity and limitations

For a grammar of `g` nodes, largest repetition `r`, and `q` moduli, evaluation
uses approximately `O(q * g * log r)` modular compositions. Memory depends on
grammar size, not expanded period. This makes individual structured candidates
at the 186-billion-step scale practical.

It does **not** make an exhaustive search over all cycles practical. Most words
are incompressible, and no finite collection of grammar templates covers them.
The sieve is therefore scientifically useful only if reports state the grammar
family searched, parameter ranges, moduli, and number of survivors. “No cycle
exists” is not a valid conclusion from this project.

## Next research stages

- Add canonical parameterized grammar families while excluding rotations and
  manifest powers.
- Extend targeted-modulus selection beyond the default small-prime scan, using
  factorizations of relevant multiplicative orders.
- Add independently checkable certificate bundles for large batch searches.
- Add family-specific symbolic confirmation certificates whose identities and
  2-adic constraints can be checked without expanding the word.
- Add interval or exact Diophantine bounds for the narrow positive gap
  `S*ln(2) - k*ln(3)`.
- Materialize and replay a survivor only when its expanded size is below an
  explicit resource budget. Billion-scale survivors must remain symbolic.

These stages strengthen rejection power; none should silently convert the
structured search into a claim of exhaustive coverage.
