# Experiment Ledger

## E000 — historical multi-stratum pilot

- **Status:** complete; corrected and rerun 2026-08-04.
- **Scale:** 600 trajectories, with 100 at each of 500, 600, 700, 800, 900,
  and 1000 decimal digits.
- **Generator:** the former S0 SHA-256 expansion with digit-stratum domain separation and
  uniform rejection sampling.
- **Result:** all 600 reached `1`; mean trajectory length 18,008.112, median
  17,984, p90 23,930, and maximum 25,873.
- **Artifacts:** raw JSONL under `results/e000-p0-pilot/`; JSON and Markdown
  summaries under `reports/e000-p0-pilot/`.
- **Limitations:** one deterministic sample on one machine. It describes these
  observations and makes no general claim about Collatz trajectories.

The report gives the top ten actual starting integers and separate count, mean,
median, p90, maximum, and best start for every digit stratum. S1 has not been
implemented or run. This 600-candidate pilot is historical documentation only;
its multi-stratum layout and raw-record storage are not used by new experiments.

New experiments use 10,000 distinct 1000-digit candidates by default and the
`S0-uniform-deterministic` strategy.

## e001-s0-baseline

- **Strategy:** `S0-uniform-deterministic` (default deterministic seed `baseline-v1`).
- **Scale:** 10,000 distinct starting integers, each exactly 1,000 decimal digits.
- **Outcomes:** 10,000 reached `1`; 0 repeated state; 0 interrupted.
- **Trajectory lengths:** mean 23988.1154, median 23967.0, p90 24989.0, p99 25886.02, maximum 27,442.
- **Performance:** 198.451134643 seconds total; 50.390238473513 trajectories per second.
- **Best starting integer:** `6914663278705479762900771166016727687144899608953511314466641976043472617765426824756232799248289827551874328196370861839441633134984745399714003325204082479027758499759636626874348078481627191129923503679322885699074163863746276886115733889364993003728884912298253441747468430238653735409057838982726622115438122280528596075356573379234017828454681982802564786302189282177320929249216730528244297889480467491384663090651649688899144445880553784001555339882012833302130532958666404596595815970801612658739204405099331684395488627909062829513266601137472319605202570931149165456121505597863349856226634209091057440212981344090446822991161477214682287382786592187260222662155727051218275578956581990051605536652052349509985004161722046354657804327601447176995845001220857437370129976739807634377020544881039954698858655785223083298444373531962323801419743871238103296460932543342246292978197069048991993155301029325649969314641171179142367782243031544734868783101668237841596978555229087168165739886552`.
