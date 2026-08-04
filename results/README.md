# Raw results

Machine-readable experiment artifacts belong in one immutable directory per
experiment, following `ARCHITECTURE.md`. Large result files should use external
artifact storage and be referenced by URI and SHA-256 in `EXPERIMENTS.md`;
do not commit them merely to preserve provenance.

Raw schemas must distinguish the mathematical outcomes `reached_one` and
`repeated_state` from `interrupted`. Operationally censored records retain the
exact observed prefix and interruption reason but make no convergence,
divergence, or cycle claim.
