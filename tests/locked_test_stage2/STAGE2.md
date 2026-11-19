# Locked test, stage 2: CatLog and EnzyExtract on the held-out papers, against EnzyExtract's manual curation (plan, 11 November 2026)

## Status of this plan
- Written after stage 1's result was seen (`result/README.md`). The owner asked for a proper comparison with
  EnzyExtract on these papers, which come from its 384-paper benchmark.
- Committed **before** any EnzyExtract output on these papers was scored. The commit's time is the record.
- Stage 1 stands as reported. Stage 2 is a second, separately reported analysis on the same papers.
- A first draft of this plan also ran CatLog's later steps and judged every disagreement blind. Two reviewers found
  47 problems in it (`review/stage2/`), so this plan is narrowed to what the existing, checked code can score. What
  the full version needs is listed at the end.

## Question
On held-out papers from EnzyExtract's own benchmark, how do CatLog's reading and EnzyExtract's runs compare against
EnzyExtract's manual curation?

## Papers
- The 79 of stage 1's 83 analysed papers that the curation covers (holdout_374.tsv gold_set enzyextract;
  `result/triage.json`). The other 4 are Co-Scientist papers, not in EnzyExtract's benchmark.
- No paper is added or removed. Stage 1 took 32 benchmark papers out for a refusal or a broken rule on the Opus side.
  EnzyExtract's runs had no such exits, and this plan cannot put those papers back.

## Sources
| Source | What it is |
|---|---|
| CatLog | Stage 1's stored values: the frozen reader, verifier and code checks (`values.json`). **Primary.** |
| Plain read | Stage 1's Opus 5.5 reads (`values.json`) |
| EnzyExtract runs | Every `rumble_*_dev1` run of their benchmark SI, as the 22 October head-to-head extracted them: RGF, RxF, xGF, 4o-05, 4o-mini, 4o-mini_Rx, 4o-mini_xG, gemini, sonnet37 |
| EnzyExtract database | Their released database's values for these papers, if the extract on disk covers them; otherwise not scored, and said so |
| BRENDA 2026.1 | As in the 22 October head-to-head |

- **Primary comparator: RGF.** By our reading of their SI's naming it is "EnzyExtract full" (re-OCR, table
  extraction, fine-tuned model). That reading is an inference, so every run is reported and the best run on each
  measure is named beside RGF.
- **The plain read row** shows what the model alone gives: CatLog and the plain read use Opus 5.5, and EnzyExtract's
  runs use its authors' 2025 models.

## Scoring: the 22 October head-to-head's code, with four rules fixed here
- **Code.** The kit's checked copies (`h2h_common.py`, `h2h_s06.py`):
  - Loaders: `rows_to_values` for the curation and the runs; `enzyextract_values` and `brenda_values`.
  - Matcher: `match`, per paper and metric, one to one, within 1.5%.
  - Other systems' strings are converted with CatLog's units code, as there.
- **Check before use.** The script first reproduces that head-to-head's numbers for every run on its 59 development
  papers (`results_enzyextract_manual.json`). If it does not, it stops.
- **Rule 1: repeated rows.** A source's exact repeats are dropped before matching, for every source alike. An exact
  repeat is the same paper, metric, value and enzyme, substrate and variant labels. The table is also given with
  repeats kept.
- **Rule 2: unreadable cells.** Cells the units code cannot read are counted per source and metric, and reported.
  They are not scored. (The curation's unreadable cells are already kept unscored.)
- **Rule 3: papers with no row.** A paper for which a run has no row counts with no values, so its curation values
  are missed. The number of such papers is reported per run. The table is also given on the papers where the run has
  rows.
- **Rule 4: intervals.** Paper-clustered bootstrap, B 10,000, seed 20261031. Differences are paired on the same
  resampled papers.

## Endpoints
1. **Recall and precision against the curation**, all three metrics pooled, per source, with 95% intervals.
   - Recall is the share of the curation's scored values a source holds.
   - Precision is the share of a source's values the curation holds.
2. **CatLog minus RGF**, recall and precision, paired. A difference is claimed only if its interval excludes zero.
3. **The same for kcat and for Km separately**, as their Table S1 scores them, and for kcat/Km.
4. **CatLog minus each other source**, paired: the plain read, the best EnzyExtract run, the database, BRENDA.
5. **Sensitivity without 9973343 and 10447675**, for every source. In those two papers stage 1's investigation
   found a misprinted unit header that CatLog corrected and the curation holds as printed.

## Fixed from this commit on
- The papers, the sources, the primary comparator, the code and its four rules, the endpoints and the seed.
- A bug found on the way is fixed and stated, and its step is run again.

## Limits stated now
- **The curation is EnzyExtract's own reference.** It is not ground truth, and it holds values as printed.
- **Nothing is judged here.** Disagreements with the curation are not decided against the papers. Stage 1 decided
  the ones between CatLog and the plain read.
- **CatLog's side is its first pass.** Its later steps (database checks, audit, sweeps) are not run on these papers.
- **Models differ.** EnzyExtract's runs were made by its authors in 2025; CatLog and the plain read use Opus 5.5.
- **Earlier exposure.** The 22 October head-to-head scored every run on all 384 benchmark papers pooled, these
  among them. No number for these papers alone was computed.

## Not in this stage: what the full comparison needs (`review/stage2/`)
- **CatLog's later steps in the frozen copy.**
  - Three of the four saved workflows and two prompts name the main folder.
  - The copy holds no rows and no lookup caches.
  - The audit's sample size comes from a log the copy lacks.
  - Those agents would need their own isolation, audit and model rule.
- **A scorer for three judged sources plus the curation.** It needs the new misprint verdict and its classes, claim
  merging across sources, a rule for a value matched to a curation value that is itself judged wrong, and planted
  errors for three sources. All of it must be written, reviewed and committed before EnzyExtract's rows are loaded.
- **A check outside the model family.** CatLog, the plain read and the judges are all Opus 5.5; EnzyExtract and its
  curation are not. Verdicts against EnzyExtract or the curation need a judge of another family or a person.
