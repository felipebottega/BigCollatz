# Algebraic Collatz model

BigCollatz studies cycle patterns by recording the number of divisions by
two between successive odd terms.

## What is a family?

Apply $3x+1$ to an odd number $x$, then divide by two until the result is
odd. An entry in the pattern records how many divisions this takes. A
family is a template for arranging those entries. Choosing the lengths
of its blocks gives one candidate pattern.

For example, consider the family

$$
\mathcal{F}=\{\,1^u 2^w 1^v 3^z \mid u,w,v,z\in\mathbb{Z}_{>0}\,\}.
$$

Here $2^w$ means $w$ consecutive entries of value $2$. In this notation,
the superscript counts repetitions of an entry. A member with two entries
in the first block, one in the second, one in the third, and two in the
fourth is

$$
1^2 2^1 1^1 3^2 \;\longleftrightarrow\; (1,1,2,1,3,3).
$$

For odd values greater than one, one division gives an uphill step and
two or more divisions give a downhill step. The template above has two
uphill runs and two downhill runs.

### How the command bounds relate to a family

```bash
python -m collatz_algebra.cli --search-cycles 150000000000 --minimum-period 186265759595
```

Let $k$ be the number of odd steps and $S$ the number of divisions by
two. Each entry contributes one odd step and as many divisions as its
value. For the four-block example:

$$
\begin{aligned}
k &= u+w+v+z,\\
S &= u+2w+v+3z,\\
k+S &= 2u+3w+2v+4z.
\end{aligned}
$$

The value of `--search-cycles` caps $k$ for each candidate. The value of
`--minimum-period` sets the lower bound on $k+S$ for the length check.
If the four-block family were searched with the command above, a pattern
within the ceiling and passing the length check would satisfy

$$
\begin{aligned}
u+w+v+z &\le 150{,}000{,}000{,}000,\\
2u+3w+2v+4z &\ge 186{,}265{,}759{,}595.
\end{aligned}
$$

The four-block family illustrates the counting. The command searches only
the [two-run family](#symbolic-two-run-family). The odd-step ceiling limits
which proposals are generated. The period bound is checked after generation.

## Cycle equation

For an odd term $x_i$, let $a_i=\nu_2(3x_i+1)$ be the number of factors
of two in $3x_i+1$. The next odd term is

$$
x_{i+1}=\frac{3x_i+1}{2^{a_i}}.
$$

For the word $\mathbf{a}=(a_0,\ldots,a_{k-1})$, the total number of
divisions is $S=\sum_{i=0}^{k-1}a_i$. Composing the steps gives
the Böhm–Sontacchi equation:

$$
\begin{aligned}
T_{\mathbf{a}}(x)&=\frac{3^k x+A}{2^S},\\
A&=\sum_{j=0}^{k-1}3^{k-1-j}\,2^{\sum_{i=0}^{j-1}a_i}.
\end{aligned}
$$

The inner sum for $j=0$ is zero. At closure, $T_{\mathbf{a}}(x)=x$, so

$$
(2^S-3^k)x=A.
$$

Since $A$ is positive, a positive solution requires $2^S>3^k$.

## Lower bound for a nontrivial cycle

Every odd member $x_i$ of a nontrivial cycle must be at least $2^{71}$.
Otherwise its orbit would reach one by the convergence verification below
that threshold. [Barina's verification (2025)](https://doi.org/10.1007/s11227-025-07337-0)

Multiplying the odd-to-odd updates around the cycle gives

$$
2^S=\prod_{i=0}^{k-1}\left(3+\frac{1}{x_i}\right).
$$

Taking logarithms and using $\ln(1+t)<t$ for $t>0$ gives

$$
\log_2 3<\frac{S}{k}<\log_2 3+\frac{1}{3\cdot 2^{71}\ln 2}.
$$

This interval lies strictly between

$$
\frac{103768467013}{65470613321}
\qquad\text{and}\qquad
\frac{10439860591}{6586818670}.
$$

The cross products of these fractions differ by one, so any fraction
strictly between them has numerator and denominator at least the respective
sums. Therefore

$$
S\ge114{,}208{,}327{,}604,\qquad
k\ge72{,}057{,}431{,}991,\qquad
S+k\ge186{,}265{,}759{,}595.
$$

## Compressed words and exact verification

The internal verifier stores words as steps, concatenations, and
repetitions. A repeated block can be counted without expanding it.
For exact verification, both $k$ and $S$ must fit the configured work
limit. The verifier solves the closure equation for a positive odd integer,
then checks that each step has the specified number of divisions and
that the final member equals the starting member. Exact verification
constructs integers whose bit length grows with $S$.

## Modular certificates

The symbolic search combines the coefficients of consecutive blocks.
A block repeated $r$ times can be evaluated modulo a small integer using
$O(\log r)$ compositions. For a modulus $m$, an integer solution requires

$$
\gcd(2^S-3^k,m)\mid A.
$$

A failed check rules out the word. Passing leaves full divisibility and the
step-by-step counts open. The gap $S\ln 2-k\ln 3$ is a finite-precision
diagnostic.

## Symbolic two-run family

The command proposes words of the form $1^u2^w$, with positive block lengths.
For this family,

$$
k=u+w,\qquad S=u+2w,\qquad k+S=2u+3w.
$$

The program uses upper continued-fraction convergents of $\log_2 3$ to
select pairs $(k,S)$ near the boundary $2^S>3^k$. It keeps proposals with
$k<S<2k$ and $k$ within the odd-step ceiling. The length check and modular
certificates can give reasons to reject individual proposals.

The word has one uphill run and one downhill run for odd terms greater
than one. Steiner's theorem excludes any nontrivial positive cycle with
this shape. The known cycle $1\to4\to2\to1$ has the single-entry word $(2)$.
Cycles with more uphill and downhill runs lie outside the command's scope.

## References

- Böhm and Sontacchi, *On the existence of cycles of given length in integer
  sequences like x_n → x_n/2 or 3x_n+1* (1978). Exponent words and the closure
  equation.
- Lagarias, *The 3x+1 problem and its generalizations* (1985). Equivalent maps,
  2-adic conjugacy, and cycle obstructions. [DOI](https://doi.org/10.1080/00029890.1985.11971628)
- Lagarias (ed.), *The Ultimate Challenge: The 3x+1 Problem* (2010). Surveys
  and bibliography on the Collatz problem.
- Eliahou, *The 3x+1 problem: new lower bounds on nontrivial cycle lengths*
  (1993). Diophantine approximation of the logarithmic gap. [DOI](https://doi.org/10.1016/0166-218X(93)90152-U)
- Simons and de Weger, *Theoretical and computational bounds for m-cycles of
  the 3n+1 problem* (2005). Bounds based on blocks of minima and maxima. [DOI](https://doi.org/10.4064/aa117-1-5)
- Wirsching, *The Dynamical System Generated by the 3n+1 Function* (1998).
  Parity words and their 2-adic interpretation. [DOI](https://doi.org/10.1007/BFb0095985)
- Kontorovich and Lagarias, *Stochastic models for the 3x+1 and 5x+1
  problems*. Probabilistic models for orbit behavior. [arXiv:0910.1944](https://arxiv.org/abs/0910.1944)
- Tao, *Almost all orbits of the Collatz map attain almost bounded values*
  (2022). A result on almost all orbits. [arXiv:1909.03562](https://arxiv.org/abs/1909.03562)
- Steiner, *A theorem on the Syracuse problem* (1977), Proceedings of the
  Seventh Manitoba Conference on Numerical Mathematics and Computing,
  pp. 553–559. Exclusion of nontrivial positive cycles with one local minimum.
