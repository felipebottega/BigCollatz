# Results

Normal experiments store `summary.json`, `summary.md`, and `top_10.json` in
their directory. `global_top_10.json` contains the longest ten distinct starting
integers merged from normal completed experiments. Machine-readable files use
canonical decimal strings for exact large integers.

Adaptive pilot directories may instead include a design, analysis, compact
cross-cell ranking, and JSON summary. Pilots are isolated from
`global_top_10.json`. The historical `e000-p0-pilot` directory is the sole raw
JSONL exception; new runs do not create raw records, shards, checkpoints,
caches, or manifests.
