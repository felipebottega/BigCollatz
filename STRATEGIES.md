# Strategy Registry

Every strategy remains here after testing, including failures. Status values are
`proposed`, `pilot`, `tested`, and `retired`. None has yet been experimentally
shown effective in this project.

## S0 — stratified deterministic controls (`pilot`)

Generate 500--1000 digit integers with a counter-based cryptographic expansion,
plus a low-discrepancy bit construction, stratified by digit length and selected
small moduli. These are reproducible controls, not the central method and not a
consecutive scan. They quantify ordinary variation, residue imbalance, and the
cost floor against which guided methods must be judged.

E000's SHA-256 counter component was deliberately trajectory-blind. Across 600
starts, mean work rose primarily with digit count; it supplied no mechanism to
enrich the long upper tail. It remains a matched control, not a search strategy.

## S1 — parity-prefix congruence beam (`proposed`, implement first)

For a desired finite parity word of length `k`, forward affine composition
determines a congruence class modulo `2^k` whose members realize that prefix.
Build words deterministically with a beam. Rank partial words using preregistered
surrogates: delayed descent, cumulative odd/even balance, low average
`v2(3n+1)`, and predicted affine growth. Lift the best residue classes into the
500--1000 digit interval using a deterministic, spread-out quotient schedule.

This directly controls early behavior without scanning integers. It is selected
first because it is mathematically auditable, produces disjoint strata, and can
be compared with residue-matched controls. Risk: optimizing a finite prefix can
simply shift work earlier and overfit the surrogate.

**First intelligent experiment:** freeze prefix length and beam width before
evaluation; lift every winning residue deterministically into every digit
stratum; and pair it with equal digit- and residue-matched S0 controls. Charge
generation and evaluation time jointly, deduplicate, and reserve a held-out
confirmation batch. This is proposed here only and is not implemented in P0.

## S2 — inverse-tree frontier construction (`proposed`, implement first pilot)

Use reverse edges `2m` and, only when integral, positive, and odd,
`(m-1)/3`. Traverse a canonical deduplicated frontier with beam/branch-and-bound
scores favoring depth, controlled size growth, and novel residue signatures.
Select 500--1000 digit frontier nodes as starts. The known reverse path supplies
a certified finite suffix to `1`, making achieved length at least the reverse
depth (after validating edge accounting).

This is deterministic and gives an interpretable lower bound. It is selected
for a pilot because it tests a different construction principle from S1. Major
risks are frontier duplication, exponential growth, and spending enormous
generation cost for only linear guaranteed depth.

## S3 — residue-class response model (`proposed`, second round)

Evaluate a balanced design over residues modulo products/powers of small primes
and powers of two. Fit regularized models on training shards to select residue
combinations, then generate a frozen held-out manifest from chosen classes.
Compare with class-matched controls. This tests whether low-modulus information
predicts behavior beyond the forced prefix. It comes after S0/S1 so model choice
is informed by validated features rather than intuition.

## S4 — deterministic elite mutation (`proposed`, second round)

From top training starts, enumerate a fixed schedule of bit flips, block edits,
and congruence-preserving changes across scales; deduplicate and evaluate in
rounds. Maintain novelty by Hamming distance and residue buckets, and reserve a
held-out confirmation batch. This exploits local structure without randomness.
Risk: adjacent bigints can have unrelated trajectories, and adaptive reuse of
results creates severe selection bias.

## S5 — hybrid branch-and-bound (`proposed`, later)

Combine parity-prefix classes, inverse certified suffixes, and empirical
cost/quality bounds in a best-first frontier. Prune only by explicit resource
bounds; heuristic pruning is labeled and cannot support exhaustive claims.
Implement only after S1/S2 measurements reveal useful bounds.

## Rejected as principal strategies

- Pure random sampling: useful only as a controlled baseline.
- Consecutive scanning: violates the research goal and poorly covers digit
  structure.
- Maximizing the starting value or its Hamming weight alone: no justified link
  to total stopping time.
- Calling any long or interrupted run a loop candidate: mathematically invalid
  without an exact repeated state.
- Storing all full trajectories by default: unnecessary disk/memory cost.

## Initial strategy order and decision gates

1. Implement S0 to validate the framework and establish cost/quality baselines.
2. Implement S1 with small beam-depth/width pilots and residue-matched controls.
3. Pilot S2 only after inverse-edge unit tests and generation-cost accounting.
4. Advance a strategy only if it improves the quality/cost Pareto frontier or
   yields a reproducible structural insight; otherwise preserve and retire it.
5. Do not start a 100,000-candidate run until evaluator, resume, determinism,
   schema, and pilot acceptance checks pass.
