# BigCollatz Research State

- **Final objective:** find a nontrivial cycle of the positive unaccelerated Collatz map with exact repeated-state detection on every generated state.
- **Latest completed full experiment:** `e004-s3-recursive-weighted-lineages-256`.
- **Current best trajectory:** length 27,707 from E004 start `3185353875247117911475057017000664279293531176511945858986494214186110162369316342912193940570936269314582938084636059000992080804674517148678841573653125994473450223353521673971632297920819710858765003989469558980591576310306453706453988794115061326133413794419526221977625982493346122637626500722495082188315435693256681397960019537528367466284620169339462598568209152978897448921300877823808426283066993714325615247659614346372403322870636516497222102813953529408338235441881059224890931372714767344880824613105803593256139375649227504948175778722300954674248816202698970761223546662676777349669938272526653336059008742999049825583882127273620161268991280572503172574558746530871528146957957405210543375309916553835831718601596404048066140614579592273396284094782596263479982693414825499528720178176135678947481545183443016695921458238973771022346786358247832724499652813989608774873248676699322104277075696749076390055232359825122934560105757986096788493964680276964536513706090477185192255061317`.
- **Repeated state found:** no exact repeated state has been detected in any current full experiment or pilot, including P007.
- **Strategies tested:** S0 baseline (E001); S1 256-prefix global-top lineage search (E002); S2 weighted E002 lineages (E003); S3 recursive weighted E003 lineages (E004); S4 mixed 128/256/384 global-top prefixes (P003 pilot only); S1 384-prefix pilot (P002); S1 128-prefix pilot (P004); S5 decimal-suffix top10 (P005 pilot only); S6 residue-class top10 (P006 pilot only); adaptive cross-family S1/S5/S6 cell comparison (P007 pilot only).
- **Rejected or inconclusive hypotheses:** S1 384-prefix global-top pilot rejected for full scale; S4 mixed-prefix pilot inconclusive/weak for full promotion; S1 128-prefix pilot rejected because the high tail collapsed relative to prior pilots and full experiments.
- **Strongest observed signals:** recursive 256-prefix lineage weighting remains the best full-scale evidence and produced the 27,707 global maximum; fixed shorter or longer prefixes around the global top 10 have not improved the tail; broad mixed-prefix diversity improved over pure 128-prefix but not enough for full-scale promotion; decimal-suffix and non-decimal residue pilots were competitive with each other but below the E004 record.
- **Current working hypothesis:** useful signal is concentrated in specific cross-family cells, with P007 favoring sustained parity-prefix and decimal-suffix tails more than residue at 25 samples per cell.
- **Next intended direction:** run a small second-stage adaptive pilot that promotes `p007-ds-r02-d64`, `p007-pp-r02-l256`, and `p007-pp-r02-l128`, while retaining at least one residue sentinel; do not begin a full 10,000-candidate experiment yet.

## P007 adaptive stage-A pilot

- **Identifier:** `p007-adaptive-stage-a-300`.
- **Candidate count:** exactly 300 requested, 300 distinct, and 300 evaluated candidates.
- **Deterministic seed:** `p007-adaptive-stage-a-300/main/2026-08-05`.
- **Cell grid:** 12 cells with 25 candidates each: `p007-pp-r01-l128`, `p007-pp-r01-l256`, `p007-pp-r02-l128`, `p007-pp-r02-l256`, `p007-ds-r01-d32`, `p007-ds-r01-d64`, `p007-ds-r02-d32`, `p007-ds-r02-d64`, `p007-rs-r01-m64p1`, `p007-rs-r01-m128p1`, `p007-rs-r02-m64p1`, and `p007-rs-r02-m128p1`. The grid varies current global top-10 parent ranks 1 and 2 against family-specific preservation strengths: parity prefixes 128/256, decimal suffixes 32/64, and residue moduli `2**64 + 1` / `2**128 + 1`.
- **Outcome counts:** 300 reached one, 0 repeated states, and 0 interruptions; no nontrivial cycle was found.
- **Principal results:** maximum trajectory length 25,940 from residue cell `p007-rs-r01-m128p1`; no candidate exceeded 26,000 or 27,000 steps; 30 records form the overall top-10% tail.
- **Top-performing cells by sustained metrics:** `p007-ds-r02-d64` (mean 24,319.4; max 25,802; four tail records; four >=25,000), `p007-pp-r02-l256` (mean 24,313.5; max 25,887; four tail records; four >=25,000), and `p007-pp-r02-l128` (mean 24,100.5; max 25,719; four tail records; four >=25,000).
- **Family comparison:** parity-prefix had 13 top-tail records and 12 >=25,000 exceedances; decimal-suffix had 11 top-tail records and 9 >=25,000 exceedances; residue had 6 top-tail records and 6 >=25,000 exceedances despite the isolated maximum.
- **Interpretation:** P007 supports promoting multiple parity-prefix and decimal-suffix cells to a second-stage pilot, while keeping a residue sentinel alive because the residue family produced the isolated maximum. No cell is rejected as clearly unproductive at only 25 samples.
- **Artifacts:** summary, design, analysis, and top-30 ranking are stored under `results/p007-adaptive-stage-a-300/`.

## Infrastructure note

Correctness-first infrastructure is available for future adaptive cross-family pilots: shared exact evaluation with optional metrics, canonical cycle reconstruction, independent verification, strict adaptive-cell metadata validation, exact generator-count enforcement, global uniqueness, timing, and verified-discovery early stopping. P007 used this infrastructure without modifying `results/global_top_10.json`; no P008, E005, or new full experiment has been started.
