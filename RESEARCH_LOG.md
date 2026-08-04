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

## P005 — S5 productivity-weighted prefix-cell pilot

- **Hypothesis:** useful signal after E004 is concentrated in parent/prefix cells, and a small rank-weighted allocation across intermediate prefix lengths will outperform uniform mixed-prefix diversity without collapsing to one lineage.
- **Strategy:** `S5-productivity-weighted-prefix-cells`, seed `cell-weighted-v1`, temporary output root so persistent `results/global_top_10.json` was not modified.
- **Candidate generation:** read `results/global_top_10.json`; form cells from each global top-10 parent crossed with prefix lengths 192, 256, and 320; allocate candidates by parent rank weights 10 down to 1 multiplied by prefix weights 2, 4, and 3; sample SHA-256 quotient lifts preserving each assigned parity prefix; validate parity-prefix preservation.
- **Source data or parent selection:** all 10 persistent global top-10 starts after E004, with higher allocation to better-ranked entries.
- **Parameters:** 300 distinct 1000-digit candidates; prefix lengths 192/256/320; aggregate prefix allocations 67/133/100; deterministic seed `cell-weighted-v1`.
- **Status:** pilot.
- **Result:** 300 reached `1`; 0 repeated state; 0 interrupted; mean 24,192.24; median 24,204.0; p90 25,144.3; p99 26,135.71; maximum 26,698; runtime 12.095219322 seconds; 24.803 trajectories/s.
- **Relevant strategy metrics:** compared with P003's uniform 30-cell mixed-prefix pilot, P005 raised the median by 102.5 and kept p99 near E004's 26,134.03, but maximum stayed 1,009 below E004 and 734 below P001.
- **Comparison:** stronger central tendency than P003/P004, weaker maximum than P001/P002/E003/E004; distribution did not justify full promotion because it did not produce a compelling top-tail improvement despite concentrating work into higher-signal cells.
- **Conclusion:** inconclusive to weakly rejected for full scale; cell weighting is a better allocation rule than uniform mixed prefixes but still not enough evidence for a 10,000-candidate run.
- **Next decision:** test a genuinely different local-neighborhood perturbation around the current best starting integer rather than another prefix-cell variant.

## P006 — S6 best-neighborhood suffix-perturbation pilot

- **Hypothesis:** the current E004 best start may lie in a decimal neighborhood sharing late trajectory behavior; perturbing only a large decimal suffix may generate many nearby starts with equal or near-equal delayed descent while exploring exact states not generated by parity-prefix lifting.
- **Strategy:** `S6-best-neighborhood-suffix-perturbation`, seed `suffix-perturb-v1`, temporary output root so persistent `results/global_top_10.json` was not modified.
- **Candidate generation:** read the first entry of `results/global_top_10.json`; preserve its first 760 decimal digits; replace the final 240 decimal digits with deterministic SHA-256 samples; exclude the source parent; evaluate with the common exact evaluator.
- **Source data or parent selection:** the E004 global-best starting integer only.
- **Parameters:** 300 distinct 1000-digit candidates; suffix digits 240; preserved decimal prefix digits 760; deterministic seed `suffix-perturb-v1`.
- **Status:** pilot.
- **Result:** 300 reached `1`; 0 repeated state; 0 interrupted; mean 24,090.02; median 23,620.0; p90 24,556.0; p99 26,306.0; maximum 27,707; runtime 11.535351645 seconds; 26.007 trajectories/s.
- **Relevant strategy metrics:** maximum tied the global record without reusing the parent; p99 exceeded P005/P003/P001 and E004's p99, while mean/median were weaker than guided prefix-lineage experiments.
- **Comparison:** the top tail was unusually strong for only 300 candidates, but central distribution was bimodal/weak, so a deterministic replication was needed before promotion.
- **Conclusion:** supported for targeted replication, not yet full promotion.
- **Next decision:** run a second deterministic S6 pilot with a new seed to check whether record ties are reproducible.

## P007 — S6 suffix-perturbation deterministic replication

- **Hypothesis:** if S6's top-tail signal is structural rather than one seed accident, a second seed preserving the same 760-digit prefix should again produce exact candidates tying or approaching the 27,707 E004 trajectory length.
- **Strategy:** `S6-best-neighborhood-suffix-perturbation`, seed `suffix-perturb-v2`, temporary output root so persistent `results/global_top_10.json` was not modified.
- **Candidate generation:** same as P006, but with independent deterministic suffix stream `suffix-perturb-v2`; source parent excluded; common exact evaluator used.
- **Source data or parent selection:** the E004 global-best starting integer only.
- **Parameters:** 300 distinct 1000-digit candidates; suffix digits 240; preserved decimal prefix digits 760; deterministic seed `suffix-perturb-v2`.
- **Status:** pilot.
- **Result:** 300 reached `1`; 0 repeated state; 0 interrupted; mean 24,093.196666666667; median 23,620.0; p90 24,556.0; p99 26,320.009999999987; maximum 27,707; runtime 11.471772047 seconds; 26.151 trajectories/s.
- **Relevant strategy metrics:** the independent seed again produced multiple non-parent candidates with trajectory length 27,707, supporting a robust local-neighborhood plateau signal; no repeated state was detected.
- **Comparison:** P007 replicated P006's maximum and p99 pattern but did not exceed the E004 global best; it is stronger than S5 for top-tail preservation and genuinely different from parity-prefix lineage lifting.
- **Conclusion:** supported as the active strategy for a future full experiment or a smaller suffix-width sensitivity pilot; no nontrivial cycle found.
- **Next decision:** the immediate continuation point is a correctness-gated full E005 S6 run if execution allowance permits, otherwise first run a 100-candidate suffix-width sensitivity check over narrower suffixes such as 120 or 180 digits.

## Stop record — autonomous loop pause

- **Reason:** the measured runtime of a 300-candidate S6 pilot was about 11.5 seconds, so the next meaningful full E005 promotion at 10,000 candidates is estimated at roughly 6.4 minutes plus correctness-gate overhead; the remaining task interaction budget is insufficient to safely run that full experiment, analyze it, document it, commit it, and create the required pull request in this turn.
- **Immediate continuation point:** run the complete correctness gates, then promote S6 to `e005-s6-best-neighborhood-suffix-perturbation` at exactly 10,000 candidates with seed `suffix-perturb-full-v1` if the gate passes.
