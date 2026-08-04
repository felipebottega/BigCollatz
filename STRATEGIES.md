# Strategy Notes

## S0 — deterministic uniform control (`pilot`)

Use SHA-256 counter expansion with a separate domain for every decimal-digit
stratum. Rejection sampling gives a uniform value in each requested interval.
This trajectory-blind generator is a reproducible control, not an informed
search strategy. E000 contains 100 starts in each of six strata.

## S1 — parity-prefix congruences (`idea only`)

A finite parity word determines a residue class modulo a power of two. A future
small experiment could construct a few such classes, lift them into each digit
stratum, and compare their raw trajectory lengths with digit-matched S0 values.
The construction and comparison must remain auditable and include generation
runtime. **S1 is not implemented yet.**

## Other ideas, not commitments

- traverse a small canonical inverse Collatz tree and measure whether its nodes
  provide useful starts;
- test simple residue-balanced controls;
- make deterministic edits to a held-out set of promising starts.

These are research notes, not an implementation roadmap. A new generator should
be added only for a concrete, modest experiment. Pure random sampling,
consecutive scanning, and storing full trajectories are not principal methods.
