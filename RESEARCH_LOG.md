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

## P005 pilot — S5 decimal suffix top-10

- **Identifier:** `p005-s5-decimal-suffix-100`.
- **Hypothesis:** preserving the trailing decimal block of current global-top starts may retain arithmetic structure not captured by parity-prefix cells while still exploring distant 1000-digit neighborhoods.
- **Strategy:** `S5-decimal-suffix-top10`.
- **Candidate generation:** load `results/global_top_10.json`; allocate 100 candidates evenly across the ten parents; for each parent preserve the exact final 64 decimal digits and sample the remaining quotient uniformly with the deterministic SHA-256 stream.
- **Validation rule:** strategy-bound `decimal_suffix`; each explicit `CandidateRecord` must declare `validation_mode="decimal_suffix"`, include `parent` and `suffix_digits`, and satisfy `candidate % 10**suffix_digits == parent % 10**suffix_digits` before evaluation.
- **Source data:** current `results/global_top_10.json` from the merged main branch.
- **Parameters:** 100 candidates, 1,000 decimal digits, suffix digits 64, balanced 10-per-parent allocation.
- **Deterministic seed:** `p005-s5-decimal-suffix-seed-20260804`.
- **Status:** deterministic pilot only; persistent global top ten was not updated.
- **Outcomes:** reached one 100; repeated state 0; interrupted 0.
- **Statistics:** mean 24,050.85; median 24,008.0; p90 25,187.4; p99 25,564.86; maximum 25,749.
- **Runtime:** 4.059158701 seconds; 24.635646784483775 trajectories/second.
- **Strategy-specific metrics:** all 100 candidates validated by decimal-suffix dispatch; ten global-top suffix cells sampled equally; no source parent was generated.
- **Comparison:** the maximum exceeded the weak P004 128-prefix pilot tail but remained below the 27,707 E004 global record and did not produce a repeated state.
- **Conclusion:** inconclusive rather than rejected; the suffix signal is broad enough to keep as a possible diversification source but too weak for immediate full promotion.
- **Next decision:** test a genuinely different modular residue hypothesis rather than another suffix-length variation.

## P006 pilot — S6 residue class top-10

- **Identifier:** `p006-s6-residue-class-100`.
- **Hypothesis:** preserving a non-power-of-ten residue class from current global-top starts may capture modular near-return information independent of decimal suffixes and parity-prefix lineage structure.
- **Strategy:** `S6-residue-class-top10`.
- **Candidate generation:** load `results/global_top_10.json`; allocate 100 candidates evenly across the ten parents; for each parent preserve its residue modulo `2**128 + 1` and sample quotient lifts uniformly across the full 1,000-digit interval.
- **Validation rule:** strategy-bound `residue`; each explicit `CandidateRecord` must declare `validation_mode="residue"`, include `residue_modulus` and `residue`, and satisfy `candidate % residue_modulus == residue` before evaluation.
- **Source data:** current `results/global_top_10.json` from the merged main branch.
- **Parameters:** 100 candidates, 1,000 decimal digits, residue modulus 340282366920938463463374607431768211457, balanced 10-per-parent allocation.
- **Deterministic seed:** `p006-s6-residue-class-seed-20260804`.
- **Status:** deterministic pilot only; persistent global top ten was not updated.
- **Outcomes:** reached one 100; repeated state 0; interrupted 0.
- **Statistics:** mean 24,029.56; median 24,022.5; p90 24,918.4; p99 25,885.21; maximum 25,906.
- **Runtime:** 3.898373787 seconds; 25.651721836800867 trajectories/second.
- **Strategy-specific metrics:** all 100 candidates validated by residue dispatch; ten top-parent residue classes sampled equally; no source parent was generated.
- **Comparison:** P006 slightly beat P005 on maximum and p99 but still trailed E004's 27,707 maximum and found no exact repeated state.
- **Conclusion:** inconclusive; residue targeting is competitive with suffix diversification at pilot scale but does not justify a full 10,000-candidate run without a stronger cell-ranking stage.
- **Next decision:** continue with a compact productivity-ranked cell strategy that can compare parity, suffix, and residue cells under a single validation-bound runner path before allocating full-experiment scale.

## P007/P008 — adaptive cross-family cell pilots

- **Hypothesis:** compact productivity-ranked cells across parity-prefix, decimal-suffix, and residue families can identify reusable signal without compromising exact repeated-state detection.
- **Shared evaluator/cycle rule:** every adaptive candidate used the single evaluator engine via `evaluate_with_metrics`; repeated states would be reconstructed canonically, independently replayed, persisted through `results/cycle_candidates.json`, and stop the pilot immediately on verified nontrivial discovery.
- **Validation mapping:** parity-prefix cells required strategy `S1-parity-prefix-top10` and validation `parity_prefix`; decimal-suffix cells required `S5-decimal-suffix-top10` and `decimal_suffix`; residue cells required `S6-residue-class-top10` and `residue`.
- **Stage A (`p007-adaptive-stage-a-300`):** seed `adaptive-stage-a-20260804`; 300 total candidates split evenly across three cells: parent-1 128-step parity prefix, parent-2 64-digit decimal suffix, and parent-3 residue modulo `2**128 + 1`.
  - Parity cell: 100 reached one, 0 repeated states, maximum length 26,289, mean 23,967.33.
  - Decimal-suffix cell: 100 reached one, 0 repeated states, maximum length 25,831, mean 24,130.15.
  - Residue cell: 100 reached one, 0 repeated states, maximum length 26,416, mean 24,014.54.
- **Stage B (`p008-adaptive-stage-b-300`):** seed `adaptive-stage-b-20260804`; deterministic allocation was 100/100/100 because Stage A scores were close enough that largest-remainder allocation preserved family diversity.
  - Parity cell: 100 reached one, 0 repeated states, maximum length 26,413, mean 24,149.64.
  - Decimal-suffix cell: 100 reached one, 0 repeated states, maximum length 26,343, mean 24,196.89.
  - Residue cell: 100 reached one, 0 repeated states, maximum length 25,529, mean 23,794.93.
- **Comparison:** Stage A/B maxima remained below P003 (26,969), P005 (25,749) was exceeded, P006 (25,906) was exceeded by parity/suffix cells, but all adaptive maxima remained below E003 (27,445) and E004 (27,707).
- **Decision:** reject immediate full-experiment promotion; one 300-candidate parity/suffix signal is not convincing enough for exactly 10,000 candidates. The next hypothesis should broaden cell count or use E004 lineage-derived parent diversity while retaining the same validation-bound adaptive runner.
- **Stopping reason:** correctness gate and two deterministic pilots completed; no nontrivial cycle was found and no full experiment was justified.
