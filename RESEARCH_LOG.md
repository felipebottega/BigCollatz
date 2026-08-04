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

## P005 — S5 decimal-suffix global-top pilot

- **Hypothesis:** preserving exact low decimal suffixes of global top-10 starts may retain arithmetic neighborhood signals not captured by parity-prefix congruences.
- **Strategy name:** `S5-decimal-suffix-global-top10`.
- **Candidate generation:** loaded `results/global_top_10.json`; for each parent, preserved the exact final 24 decimal digits and sampled SHA-256 quotient lifts uniformly across the 1000-digit interval; balanced allocation was 30 candidates per parent.
- **Validation rule:** strategy-specific `decimal_suffix` validation: candidate and parent must have identical residue modulo `10^24`; parity-prefix validation is not applied.
- **Source data:** current merged `results/global_top_10.json` from E001–E004.
- **Parameters:** 1,000 decimal digits, 300 distinct candidates, `suffix_digits=24`, seed `p005-s5-decimal-suffix-v1`, candidate validation enabled, temporary output root `/tmp/bigcollatz-pilots` so persistent `results/global_top_10.json` was not modified.
- **Status:** pilot only.
- **Results:** reached-one 300; repeated-state 0; interrupted 0; mean 24,002.657; median 23,985.0; p90 25,071.6; p99 25,764.0; maximum 25,846; runtime 11.947177912 s; throughput 25.110532563 trajectories/s.
- **Best pilot start:** `3353636333590324028236861151081587018703527839367380067236823090562414285952994925980484948687985064270572657243477476187578694041904716220132068645652059251263076146375265807496606026623109040454587807012112291690449219816332330319805421020323252255958583747308195894443848848950518502027726065473742778933357413303127212976607395548657285940460282626555983036927698253014939483425156383550481984188530446054200049623219450916449972599307492283291974222714081683139594360600567509635850926913355533761824063685510602181409215625118007611467063421948421566231075142251305820005414832058126175046647066951299954864246037089417861227845198609994426541924987045786155324398629125656870973170998922271971088933994933149113053412969589954047382832792110398346890935331955604184643419111803640094144545553651285946107946892263436697903899327337386213312324849805781035875839770956144485004881877888242235280525865133328167772969410920280166489704264115013335361222556162911969270791648133634729855893929285`.
- **Strategy-specific metrics:** best source parent index 7, preserved suffix `8133634729855893929285`; metadata survived in top-10 records as `validation_mode=decimal_suffix` and `suffix_digits=24`.
- **Comparison:** maximum 25,846 is below E004's 27,707 and below S6/P006's 27,087; the tail is respectable but not stronger than current parity lineage evidence.
- **Conclusion:** inconclusive but not promoted; decimal suffix locality alone did not beat the strongest merged signal in this deterministic 300-candidate pilot.
- **Next decision:** test a genuinely different low-bit modular neighborhood that deliberately perturbs, rather than preserves, the parent residue.

## P006 — S6 binary nearby-residue global-top pilot

- **Hypothesis:** exact low-binary residues near, but not equal to, strong parents may explore local modular neighborhoods around high-performing starts without enforcing their full parity prefixes.
- **Strategy name:** `S6-binary-nearby-residue-global-top10`.
- **Candidate generation:** loaded `results/global_top_10.json`; for each parent and each nonzero delta in `{-3,-2,-1,1,2,3}`, sampled SHA-256 quotient lifts satisfying `candidate ≡ parent + delta (mod 2^20)` across the 1000-digit interval; balanced allocation was 5 candidates per parent/delta cell.
- **Validation rule:** strategy-specific `residue` validation: candidate must equal its recorded residue modulo 1,048,576; parity-prefix and decimal-suffix validators are not applied.
- **Source data:** current merged `results/global_top_10.json` from E001–E004.
- **Parameters:** 1,000 decimal digits, 300 distinct candidates, `modulus_bits=20`, `radius=3`, seed `p006-s6-binary-nearby-residue-v1`, candidate validation enabled, temporary output root `/tmp/bigcollatz-pilots` so persistent `results/global_top_10.json` was not modified.
- **Status:** pilot only.
- **Results:** reached-one 300; repeated-state 0; interrupted 0; mean 23,973.547; median 23,968.5; p90 24,958.3; p99 25,616.03; maximum 27,087; runtime 11.986406401 s; throughput 25.028352115 trajectories/s.
- **Best pilot start:** `3878134742025292525649658251640210821491059403042049876789665959104736154269507767915560492135037208749842967099640091738021782617845782324607634314066743312246361928763462035703407053223889344127304608093183052892233798246314639049905643750168098661973506483872177508871392884757958359720431048876027351781758070415043749383986993577749188127617740041967297409384015548544861203480788806006697254391426359361812770558551167586125192583711171162580256830197293639769484367558294782419805791108228412670240469772580421765728201635761732432916990288446037032603925209883702294603790234072970636443367286580338300997114197175392045443849808447910974629875313371382499748220165501304149125897287157318009452881582870630769404997053157093448945850310486491380660924814031665853053583685690741870494485616755456897597212171260110341267753980249430140694204157440646309868777262437787838329891409764888110543458194017893873298174288862786567778372480797200451306968230721886029577333903632947267709366302678`.
- **Strategy-specific metrics:** best source parent index 3, delta -2, modulus 1,048,576, residue 653,270; metadata survived in top-10 records as `validation_mode=residue`.
- **Comparison:** maximum 27,087 is below E004's 27,707 but much closer than P005 and above P004/S1-128-style weak tail noted in the state file; no repeated state appeared.
- **Conclusion:** supported for follow-up replication but not full promotion from one 300-candidate pilot; low-bit near-residue perturbation appears more promising than exact decimal-suffix preservation.
- **Next decision:** continue from S6 by concentrating a follow-up pilot on productive parent/delta cells before considering a full experiment.
