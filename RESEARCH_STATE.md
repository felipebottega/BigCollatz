# BigCollatz Research State

- **Final objective:** find a nontrivial cycle of the positive unaccelerated Collatz map with exact repeated-state detection on every generated state.
- **Latest completed full experiment:** `e004-s3-recursive-weighted-lineages-256`.
- **Current best trajectory:** length 27,707 from E004 start `3185353875247117911475057017000664279293531176511945858986494214186110162369316342912193940570936269314582938084636059000992080804674517148678841573653125994473450223353521673971632297920819710858765003989469558980591576310306453706453988794115061326133413794419526221977625982493346122637626500722495082188315435693256681397960019537528367466284620169339462598568209152978897448921300877823808426283066993714325615247659614346372403322870636516497222102813953529408338235441881059224890931372714767344880824613105803593256139375649227504948175778722300954674248816202698970761223546662676777349669938272526653336059008742999049825583882127273620161268991280572503172574558746530871528146957957405210543375309916553835831718601596404048066140614579592273396284094782596263479982693414825499528720178176135678947481545183443016695921458238973771022346786358247832724499652813989608774873248676699322104277075696749076390055232359825122934560105757986096788493964680276964536513706090477185192255061317`.
- **Repeated state found:** no exact repeated state has been detected in any current full experiment or pilot.
- **Strategies tested:** S0 baseline (E001); S1 256-prefix global-top lineage search (E002); S2 weighted E002 lineages (E003); S3 recursive weighted E003 lineages (E004); S4 mixed 128/256/384 global-top prefixes (P003 pilot only); S1 384-prefix pilot (P002); S1 128-prefix pilot (P004); S5 decimal-suffix top10 (P005 pilot only); S6 residue-class top10 (P006 pilot only).
- **Rejected or inconclusive hypotheses:** S1 384-prefix global-top pilot rejected for full scale; S4 mixed-prefix pilot inconclusive/weak for full promotion; S1 128-prefix pilot rejected because the high tail collapsed relative to prior pilots and full experiments.
- **Strongest observed signals:** recursive 256-prefix lineage weighting remains the best full-scale evidence and produced the 27,707 global maximum; fixed shorter or longer prefixes around the global top 10 have not improved the tail; broad mixed-prefix diversity improved over pure 128-prefix but not enough for full-scale promotion; decimal-suffix and non-decimal residue pilots were competitive with each other but below the E004 record.
- **Current working hypothesis:** useful signal may be concentrated in specific cross-family cells, but isolated decimal-suffix and residue preservation were insufficient at 100-candidate pilot scale.
- **Next intended direction:** build a compact productivity-ranked cell pilot that compares parity-prefix, decimal-suffix, and residue cells with strategy-bound validation before allocating any future full experiment.
- **Stopping reason for this task:** after implementing and validating two new strategy families and executing pilots P005 and P006, the remaining task window was insufficient to implement a third genuinely distinct strategy, add full dispatch and runner tests for it, execute another 100-1,000 candidate validated pilot, analyze artifacts, and update the repository without risking partial research state.


## Adaptive runner status (2026-08-04)

- **Final objective:** unchanged: find a nontrivial cycle of the positive unaccelerated Collatz map using exact state-by-state repeated-state detection.
- **Latest completed full experiment:** `e004-s3-recursive-weighted-lineages-256`.
- **Current best complete starting integer:** unchanged from E004, the 1,000-digit start listed above.
- **Current best length:** 27,707.
- **Repeated-state status:** no repeated state was found in completed Stage A or Stage B adaptive pilots; no nontrivial discovery artifact exists.
- **Valid strategies and pilots present in main:** S0 through S6 plus adaptive pilots `p007-adaptive-stage-a-300` and `p008-adaptive-stage-b-300`.
- **Rejected or inconclusive hypotheses:** adaptive Stage A/B did not provide convincing repeatable evidence for promotion to a 10,000-candidate full experiment; residue was not selected for Stage B.
- **Strongest evidence:** E004 remains the strongest full-scale result; adaptive suffix/parity cells produced only pilot-scale maxima of 26,307 and 26,230.
- **Active hypothesis:** cross-family cells may still be useful, but require better parent/cell selection than the first adaptive Stage A/B pilots.
- **Immediate next action:** inspect adaptive summaries and design a follow-up only if it adds a stronger selection signal; otherwise retain E004 as current best.
