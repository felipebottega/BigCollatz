# Algebraic Collatz project

## Research question

Can large classes of hypothetical nontrivial positive Collatz cycles be
eliminated without generating their terms?

The working scale is a minimum unaccelerated period of 186 billion steps. This
number is a configurable premise of the software, because published bounds may
use different cycle and step conventions. The project never translates that
period premise into a claim about the number of decimal digits of a cycle
member.

This is deliberately not an exhaustive solver. An arbitrary cycle of that
period contains too much information even to write down. The command-line
interface therefore admits only candidates for which its selected method is
guaranteed to return a definitive answer: bounded words receive exact checking,
and enormous generated words must belong to a family eliminated or confirmed by
a symbolic theorem. Other compressed words are reported as `not_tested`.

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

## Definitive bounded-word pipeline

1. Parse and validate a compressed exponent word.
2. Compute `k`, `S`, and `k + S` without expanding repetitions.
3. Before constructing large integers, require both `k` and `S` to fit the
   configured exact-work limit. Otherwise return `not_tested`.
4. For an admitted word, construct the exact Böhm–Sontacchi additive term `A`
   and closure denominator `D = 2^S - 3^k`.
5. Reject nonpositive `D`, or reject when `D` does not divide `A`.
6. Set `n = A/D`, require a positive odd integer, and replay every accelerated
   step exactly.
7. At every step require `v2(3*n_i + 1) = a_i`, then require the final member to
   equal the initial member.
8. Emit only `confirmed_*_cycle` or `not_a_cycle`; no admitted word can finish as
   a mere survivor.

The reported logarithmic gap is a ranking diagnostic only. It is never used as
a proof because ordinary high-precision decimal arithmetic is not interval
arithmetic.

## Symbolic proof boundary

The active CLI performs exact replay only inside the explicit bound. The older
modular sieve remains an internal research component, but the CLI no longer
uses a finite set of congruences as the final result for an arbitrary JSON word:
passing them would not establish divisibility by the full closure denominator or
the local 2-adic valuations. Above the exact bound, admission requires a
family-specific theorem whose verification depends on representation size rather
than expanded period. The implemented `1^u 2^v` search qualifies because
Steiner's theorem rejects every nontrivial member.

## Complexity and limitations

Eligibility counting costs `O(g)` for a grammar of `g` nodes. Exact checking is
pseudo-polynomial in the admitted `k` and `S` and constructs integers with
`O(S)` bits. The default bound makes that work explicit and prevents a compressed
input from unexpectedly expanding into a 186-billion-step computation.

The symbolic theorem path can still decide compact candidates at the
186-billion-step scale, but only within a theorem-covered family. It does **not**
make an exhaustive search over all cycles practical. Most words are
incompressible, and no finite collection of grammar templates covers them. “No
cycle exists” is not a valid conclusion from this project.

## Next research stages

- Add canonical parameterized grammar families while excluding rotations and
  manifest powers.
- Extend targeted-modulus selection beyond the default small-prime scan, using
  factorizations of relevant multiplicative orders.
- Add independently checkable certificate bundles for large batch searches.
- Add family-specific symbolic entailment certificates whose identities and
  2-adic constraints can be checked without expanding the word.
- Add interval or exact Diophantine bounds for the narrow positive gap
  `S*ln(2) - k*ln(3)`.
- Keep every survivor symbolic. Any future sufficient criterion must verify a
  concise identity certificate rather than materialize or replay its orbit.

These stages strengthen rejection power; none should silently convert the
structured search into a claim of exhaustive coverage.
