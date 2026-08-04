# Strategy Notes

## S0-uniform-deterministic

The active baseline deterministically chooses an offset in the 1000-digit
decimal interval from a SHA-256 seed, then walks the interval without
replacement. Every generated candidate has exactly 1000 digits and candidates
within an experiment are distinct. This trajectory-blind generator is a
reproducible control.

## S1 — parity-prefix congruences (`idea only`)

A finite parity word determines a residue class modulo a power of two. This is
only a research note; S1 has not been implemented or run.
