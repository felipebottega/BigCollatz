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

The superscript counts repetitions. For example, $2^w$ means $w$
consecutive entries of value $2$. Choosing block lengths $2,1,1,2$ gives

$$
1^2 2^1 1^1 3^2 \longleftrightarrow (1,1,2,1,3,3).
$$

Read each entry as the number of divisions by two after applying $3x+1$.
For odd terms greater than one, a single division makes the value rise
and two or more make it fall. The six entries therefore mean
**rise, rise, fall, rise, fall, fall**. The first two rises form one
run, and the last two falls form another.

Starting from $3367$, the actual odd terms are

$$
3367 \xrightarrow{1} 5051 \xrightarrow{1} 7577
\xrightarrow{2} 5683 \xrightarrow{1} 8525
\xrightarrow{3} 3197 \xrightarrow{3} 1199.
$$

Each arrow includes the $3x+1$ operation. Its label counts the divisions
that follow. For instance, $3\cdot7577+1=22732$, and dividing by two twice
gives $5683$. The six steps end at $1199$, so this segment does not close
back at $3367$.

### How the search limits relate to a family

```bash
python -m collatz_algebra.cli --search-cycles 200000000000 --cases-per-level 24 --depth 3 --seed 0
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

The value of `--search-cycles` caps $k$ for each candidate. The length check uses a fixed lower bound of $186{,}265{,}759{,}595$ on $k+S$.
If the four-block family were searched with the command above, a pattern
within the ceiling and passing the length check would satisfy

$$
\begin{aligned}
u+w+v+z &\le 150{,}000{,}000{,}000,\\
2u+3w+2v+4z &\ge 186{,}265{,}759{,}595.
\end{aligned}
$$

The four-block family illustrates the counting. The implemented search
samples patterns with more runs, using the same rules for counting steps.
The odd-step ceiling limits which proposals are generated, and the fixed
period bound remains part of the sieve.

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

The verifier combines blocks by affine composition and computes repeated
blocks by binary exponentiation. It uses exact integer coefficients to
decide whether $D=2^S-3^k$ is positive and divides $A$. If so, $x=A/D$ is a
positive odd integer because $D$ and $A$ are odd.

The divisibility check also proves that the intermediate steps are valid.
For any prefix with $S_j$ divisions, let $B_j$ be its affine numerator at
$x$. The full numerator is congruent to $3^{k-j}B_j$ modulo $2^{S_j}$.
Closure makes that numerator divisible by $2^S$, so the odd multiplier
implies $2^{S_j}\mid B_j$. Thus all intermediate results are integers.
Each intermediate value is odd because its next update has an even
numerator. The final value equals the initial odd value, so every listed
division count is exact. The verifier can prove closure without replaying
the trajectory. If the entire word repeats an affine map with positive multiplier, its
fixed points equal those of the base map. The verifier can therefore
decide a whole-word repetition from its base, keeping the original
step counts in the result. For other words it balances concatenations
and stores the denominator as the shift count $S$ during composition.
The exact coefficients can still grow with $S$. The optional GMP backend
uses the same integer operations and verdict criteria.

### Exact rejection by interval

The verifier can also prove nonintegrality without constructing both
integer coefficients. It encloses the normalized map
$T(x)=\lambda x+\beta$ using directed rounding. When the bounds prove
$\lambda<1$, it encloses the unique solution $\beta/(1-\lambda)$.
An interval strictly between consecutive integers excludes any integer
solution. If the interval is inconclusive, the verifier uses exact
integer composition and division.

The giant-word audit exercises a primitive word with $137{,}528{,}045{,}312$
odd steps. It passes the screening filters. The verifier places its
fixed point between consecutive integers, and a separate GMP/MPFR
calculation checks that the two integers give opposite signs in the
closure equation. Run both checks after installing the optional
dependency with `python -m unittest tests.test_giant_certificate -v`.

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

## Monte Carlo search

The sampler uses patterns of the form

$$
1^{u_1}d_1^{w_1}\,1^{u_2}d_2^{w_2}\cdots 1^{u_r}d_r^{w_r},
\qquad u_i,w_i>0,\quad d_i\ge2.
$$

Each uphill run is followed by a downhill run, which can contain blocks
with different division counts.
The sampler chooses the run count from the necessary lower bound and the
available number of steps. Each uphill run needs at least one odd step,
and the downhill run that follows needs at least one more. Thus a pattern
with $k$ odd steps has at most $\lfloor k/2\rfloor$ uphill runs. The report
groups patterns by their uphill run count and largest downhill exponent.

### Check the step-count range

Let $r$ be the number of uphill runs and $m=2^{71}$ the lower bound on
cycle members. Hercher's Corollary 17 gives a necessary bound on the gap
$G=S\ln 2-k\ln 3$.

$$
0<G<\frac{97r}{162m}.
$$

The program encloses $\log_2 3$ between consecutive Farey fractions
$L=p_L/q_L$ and $R=p_R/q_R$ at the chosen odd-step ceiling $M$.
It verifies the enclosure with rational bounds on the logarithms.
The neighbors satisfy $p_Rq_L-p_Lq_R=1$ and $q_L+q_R>M$.
Therefore any $S/k>\log_2 3$ with $k\le M$ is at least $R$. Its
numerator and denominator have the unique representation

$$
(S,k)=b(p_R,q_R)-t(p_L,q_L),
\qquad b\ge 1,\quad t\ge 0.
$$

Every such pair has gap at least $p_R\ln 2-q_R\ln 3$, since the upper
fraction has positive gap and the lower fraction has negative gap. If a
certified lower bound on that minimum meets or exceeds the allowance even
for $\lfloor M/2\rfloor$ runs, the program reports `scope_excluded`.
Otherwise it samples coefficients $b,t$ subject to the odd-step ceiling
and the gap allowance. At $M=200{,}000{,}000{,}000$, the certified minimum
gap implies at least $3{,}543{,}773{,}083$ uphill runs.

### Build around a valley

For a downhill run of length $w$ with division count $d$, let
$B=2^d-3$. At the odd term $x$ where the run ends, the inverse updates
require $Bx\equiv 1\pmod{3^w}$. To start an uphill run, the same term
must satisfy $x\equiv 3\pmod 4$. The generator combines these conditions
by the Chinese remainder theorem. It picks an odd representative above the
verified convergence range and follows at least 12 actual odd-to-odd
steps, ending at another valley. Then it assigns the remaining steps
and divisions to the rest of the pattern. Variations preserve the
checked prefix and the incoming downhill run. Some proposals have no
anchor, so this construction does not constrain the entire search.

### Represent large run counts

The default sampler stores high run counts as repeated motifs made of
short runs. It varies the length and order of the motif groups and
preserves the valley anchor. The exact and modular affine evaluators
compose the repeated blocks directly. The `--independent-runs` option
samples individual step exponents without an anchor. After choosing the
number of rising and falling steps, it distributes the steps among the runs
and distributes the extra divisions among all falling steps. This gives
arbitrary downhill exponents and changes of exponent within a run.

For a repeated motif of $p$ odd steps and $q$ divisions, each phase from
one copy to the next obeys an affine map with multiplier $3^p/2^q$.
If $3^p>2^q$, the phase values grow geometrically. If $3^p<2^q$, they grow
geometrically backwards once the additive coefficient is sufficiently
small relative to the minimum cycle member. The reciprocal sum of each
phase can then be bounded by a geometric series independently of the
number of copies. The program uses that bound to reject repeated
patterns when it proves the gap is too large. Remaining candidates
still go to exact affine closure.

### Reject using local congruences

At each valley, the verifier combines the incoming downhill congruence
with the integrality condition from up to 128 forward odd steps.
It may use only a prefix of the incoming divisibility constraint to
keep the arithmetic small. The least compatible integer at or above $m$
gives a lower bound $m_i$ on that valley's value.

Along a rising run, values grow by at least $3/2$. Along a falling run
traversed backwards, values grow by at least $5/4$, since
$(4y-1)/3\ge 5y/4$ for $y\ge4$. Summing reciprocals of the members on the
two sides of each valley gives

$$
G=\sum_j\ln\left(1+\frac{1}{3x_j}\right)
<\frac{8}{3}\sum_i\frac{1}{m_i}.
$$

The program compares an exact rational lower bound on $G$ to an
upwards-rounded bound on the right. If neither this inequality, the
global run bound, nor the modular checks rejects the pattern, the program
solves the full affine closure equation.

### Score and refinement

Among candidates with a positive margin, the program prioritizes smaller
values of

$$
\delta=\frac{S\ln 2-k\ln 3}{k}.
$$

The score measures how close the ratio $S/k$ is to the lower edge of the
necessary interval. It ties for patterns with the same ratio, regardless of
the order of their steps. After the first level, some slots sample fresh
patterns and the rest vary one of the four highest-ranked
patterns found so far. Variations can redistribute uphill steps, exchange
downhill blocks, or resize the pattern using nearby counts $(k,S)$.
Rearranging the steps can change the modular results even when the score
stays the same.

The report records the counts by outcome and family, the best-scoring
candidate at each level, and the parent of each variation. Each entry in
`runs` lists the uphill length, divisions per downhill step, and downhill
length in that order. A fourth entry, when present, lists additional
downhill blocks as exponent and length pairs. The `packed_runs` groups are inserted immediately
after the anchor's prefix. Each group has a `copies` field and a list of
runs that form one copy. The `anchor` records the starting term and how
many initial runs were checked at generation. A completed search reports
each pattern as rejected or confirmed.

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
  the 3n+1 problem* (2005). Bounds based on blocks of minima and maxima. [DOI](https://doi.org/10.4064/aa117-1-3)
- Hercher, *There are no Collatz m-Cycles with m ≤ 91* (2023).
  The search uses Corollary 17. [Paper](https://arxiv.org/abs/2201.00406) ·
  [Formalization of Corollary 17](https://github.com/PhilNorfleet/Hercher2023_lean/blob/HEAD/Collatz/Bridge.lean)
- Wirsching, *The Dynamical System Generated by the 3n+1 Function* (1998).
  Parity words and their 2-adic interpretation. [DOI](https://doi.org/10.1007/BFb0095985)
- Kontorovich and Lagarias, *Stochastic models for the 3x+1 and 5x+1
  problems*. Probabilistic models for orbit behavior. [arXiv:0910.1944](https://arxiv.org/abs/0910.1944)
- Tao, *Almost all orbits of the Collatz map attain almost bounded values*
  (2022). A result on almost all orbits. [arXiv:1909.03562](https://arxiv.org/abs/1909.03562)
- Steiner, *A theorem on the Syracuse problem* (1977), Proceedings of the
  Seventh Manitoba Conference on Numerical Mathematics and Computing,
  pp. 553–559. Exclusion of nontrivial positive cycles with one local minimum.
