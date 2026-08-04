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
