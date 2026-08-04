# BigCollatz Research Log

## P001 — S3 recursive weighted-lineage pilot

- **Hypothesis:** E003 top-10 lineage productivity contains a reusable signal, and recursively weighting those productive lineages will improve trajectory-length distribution while preserving exact cycle detection.
- **Strategy:** `S3-recursive-weighted-lineages`, prefix length 256, seed `recursive-v1`, temporary output root so persistent global top 10 was not updated.
- **Parameters:** 500 distinct 1000-digit candidates; lineage weights 4, 4, 1, 1; allocations 200, 200, 50, 50.
- **Result:** 500 reached `1`; 0 repeated state; 0 interrupted; mean 24,269.38; median 24,253.0; p90 25,302.1; p99 26,222.47; maximum 27,432; 25.327 trajectories/s.
- **Comparison:** pilot maximum was below E003 by 13 but mean/median/p90 exceeded prior full experiments.
- **Conclusion:** supported enough for full promotion.
- **Next decision:** run E004 at exactly 10,000 candidates.

## E004 — S3 recursive weighted-lineage full experiment

- **Hypothesis:** recursive weighting from E003 productive lineages remains useful at full scale and may uncover longer delayed-descent trajectories.
- **Strategy:** `S3-recursive-weighted-lineages`, prefix length 256, seed `recursive-v1`.
- **Parameters:** 10,000 distinct 1000-digit candidates; lineage weights 4, 4, 1, 1; allocations 4,000, 4,000, 1,000, 1,000.
- **Result:** 10,000 reached `1`; 0 repeated state; 0 interrupted; mean 24,228.0526; median 24,215.0; p90 25,271.0; p99 26,134.03; maximum 27,707; 24.769 trajectories/s.
- **Comparison:** maximum exceeded E003 by 262 and E001 by 265; mean exceeded E003 by 27.2265 and E001 by 239.9372.
- **Conclusion:** supported; recursive lineage weighting improved the global best but risks convergence.
- **Next decision:** avoid immediate equivalent recursion; test a diversity-preserving adaptive-prefix or perturbation strategy.

## P002 — S1 384-prefix global-top pilot

- **Hypothesis:** a longer fixed parity prefix around the updated global top 10 may preserve more delayed-descent structure than the 256-prefix search.
- **Strategy:** `S1-parity-prefix-top10`, prefix length 384, seed `prefix384-v1`, temporary output root.
- **Parameters:** 500 distinct 1000-digit candidates; 10 parents; balanced allocation of 50 each.
- **Result:** 500 reached `1`; 0 repeated state; 0 interrupted; mean 24,281.634; median 24,251.0; p90 25,320.2; p99 26,053.32; maximum 27,251; 24.958 trajectories/s.
- **Comparison:** distribution was respectable, but maximum was below P001, E003, and E004; the method was only a fixed-parameter variation of S1.
- **Conclusion:** rejected for full experiment now.
- **Next decision:** pursue a genuinely different diversity-preserving strategy rather than another fixed-prefix run.

## P003 — S4 diversified mixed-prefix top-10 pilot

- **Hypothesis:** the E004/global top 10 contain useful delayed-descent parity-prefix information, but fixed 256-prefix exploitation has become too lineage-concentrated; mixing 128-, 256-, and 384-step prefixes across all global top parents may recover diversity while retaining signal.
- **Strategy:** `S4-diversified-mixed-prefix-top10`, seed `mixed-prefix-v1`, temporary output root so persistent global top 10 was not updated.
- **Candidate generation:** read `results/global_top_10.json`; for each of 10 parents and each prefix length in 128, 256, and 384, sample deterministic SHA-256 quotient lifts in the corresponding residue class; allocate 500 candidates as evenly as possible across the 30 parent/prefix cells; validate exact parity-prefix preservation.
- **Parameters:** 500 distinct 1000-digit candidates; prefix lengths 128, 256, 384; per-cell quotas 16 or 17.
- **Result:** 500 reached `1`; 0 repeated state; 0 interrupted; mean 24,141.456; median 24,101.5; p90 25,184.5; p99 26,209.17; maximum 26,969; 25.431 trajectories/s.
- **Comparison:** maximum was below P001 (27,432), P002 (27,251), E003 (27,445), and E004 (27,707); p99 was close to P001 but the tail did not produce record candidates.
- **Conclusion:** inconclusive to weakly rejected for immediate full promotion; mixed prefixes preserved broad distribution but did not demonstrate enough top-tail value.
- **Next decision:** test whether the apparent 128-prefix contribution from the pilot was useful by running a simpler 128-prefix top-10 pilot before designing more complex adaptive selection.

## P004 — S1 128-prefix global-top pilot

- **Hypothesis:** shorter parity-prefix preservation may keep the useful early delayed-descent signal while allowing more quotient diversity than 256- or 384-prefix descendants.
- **Strategy:** `S1-parity-prefix-top10`, prefix length 128, seed `prefix128-v1`, temporary output root so persistent global top 10 was not updated.
- **Candidate generation:** read `results/global_top_10.json`; allocate 50 candidates to each of the 10 parents; sample deterministic SHA-256 quotient lifts preserving each parent's first 128 unaccelerated parity decisions; validate exact parity-prefix preservation.
- **Parameters:** 500 distinct 1000-digit candidates; 10 parents; balanced allocation of 50 each.
- **Result:** 500 reached `1`; 0 repeated state; 0 interrupted; mean 24,114.886; median 24,068.0; p90 25,066.0; p99 25,880.11; maximum 26,187; 24.474 trajectories/s.
- **Comparison:** this was weaker than P003, P002, P001, E003, and E004 on maximum and p99.
- **Conclusion:** rejected for full experiment; merely shortening the prefix loses too much high-tail structure.
- **Next decision:** stop before a full experiment because the two new pilots did not justify the 10,000-candidate budget; next direction should combine diversity with a stronger parent signal, e.g. rank parent/prefix cells by pilot productivity and only then allocate a full run.

## P005 — S4 cell-productivity pilot with per-cell statistics

- **Hypothesis:** the weak uniform S4 mixed-prefix signal hides useful productivity in particular `(parent_starting_integer, prefix_length)` cells, so a compact balanced pilot with explicit cell statistics can identify whether a selected-cell follow-up is justified.
- **Strategy:** `S4-diversified-mixed-prefix-top10`, seed `cell-productivity-v1`, temporary output root so persistent `results/global_top_10.json` was not updated.
- **Implementation change:** the experiment runner now records compact per-cell statistics for all lineage strategies whenever a completed candidate has a parent and prefix length.
- **Parameters:** 900 distinct 1000-digit candidates; 10 current global-top parents; prefix lengths 128, 256, and 384; exactly 30 candidates per parent/prefix cell; candidate validation enabled.
- **Result:** 900 reached `1`; 0 repeated state; 0 interrupted; mean 24,160.5378; median 24,160.0; p90 25,145.1; p99 26,135.52; maximum 26,729; about 25.276 trajectories/s.
- **Top cells by cell maximum:**
  - Prefix 384 under parent `6737013310778104…7798508614155589`: count 30; mean 24,464.9; max 26,729.
  - Prefix 128 under parent `9600562701858268…3625762246478235`: count 30; mean 24,449.3; max 26,540.
  - Prefix 256 under parent `8826636225257441…9267257417891141`: count 30; mean 24,184.1; max 26,459.
  - Prefix 384 under parent `9590801569104990…1619023447883077`: count 30; mean 24,130.4; max 26,302.
  - Prefix 256 under parent `8146724180242977…0926154567895451`: count 30; mean 24,460.3; max 26,281.
- **Comparison:** the pilot's maximum did not beat P003 (26,969), P002 (27,251), P001 (27,432), E003 (27,445), or E004 (27,707). Cell maxima were noisy at 30 samples per cell, but the top-five cells included all three tested prefix lengths rather than confirming uniform prefix-256 dominance.
- **Conclusion:** reject immediate full promotion of balanced S4 or a selected-cell full experiment from only 30 samples per cell. The new per-cell statistics are useful instrumentation and should be kept.
- **Next decision:** run a refined pilot that allocates more candidates only to the P005 top cells and compares them against a small recursive-256 control, before spending a full 10,000-candidate budget.
