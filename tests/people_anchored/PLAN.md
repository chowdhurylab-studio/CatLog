# CatLog and EnzyExtract against values people checked in their papers (plan, fixed before any source is scored)

## Question
On papers whose values people checked against the paper, how many of the values people confirmed does each source
hold, and how many of the values people could not find in the paper, or found wrong, does each source hold?

The owner, 18 November 2026: "we already have 6k plus with person's verdict". The broad test's judges are agents
(PLAN.md of `../enzyextract_broad_20261118/`, "Limits stated now": "No person checks the verdicts"). Here a person's
verdict decides.

## Why this reference is fair to both sources
- The records come from the earlier catalogue, built mostly from the databases (OED, UniProt, BRENDA, SKiD, SABIO-RK)
  before CatLog read these papers. Neither CatLog's reading nor EnzyExtract made them.
- People checked them against the papers between 29 June and 14 October 2026, in the review packs of the earlier
  catalogue's records (`human_review._decisions()`, records without a `v2_pack`: 2,770 records, 5,641 values).
- CatLog's readers and verifiers never see people's verdicts, database values or the earlier catalogue
  (HUMAN_REVIEW.md, "Measuring CatLog against the reviewers"). Papers where a reading agent saw them anyway are left out
  (below).

## Reference values
Each record's kcat, Km and kcat/Km, in catalogue units as `human_review._decisions()` gives them (kcat s⁻¹, Km mM,
kcat/Km mM⁻¹ s⁻¹).
- **Confirmed:** every value of an approved record whose `disagree` flag is false. A kcat/Km the earlier catalogue
  computed from kcat and Km (`kcat/Km_derived`) is left out.
- **Not found or wrong:** every value of a record rejected in category `no_literature` (the person could not find the
  value in the paper) or `value` (the person said the number or unit is wrong), unless the paper is in
  `human_review.CLEARED` (rejections checked against the paper and cleared). A derived kcat/Km is left out here too.
- Rejections for a missing value, organism, DOI, substrate, duplicate, evidence or other reasons are left out: they do
  not say a number is wrong.

## Papers
Reference papers that meet all of these:
1. CatLog's status at the tag `paper-catalog-freeze-20261116` is `done`.
2. EnzyExtract's released database covers the paper, by PMID or by DOI through `papers.tsv` at the tag, as the broad
   test maps them (`frame()` in `../enzyextract_broad_20261118/build.py`).

Left out, each count reported:
3. Papers either side was tuned or evaluated on during development: EnzyExtract's 384-paper benchmark and its 52
   fine-tuning papers; the Co-Scientist gold set and the test kit's 165 development papers (CatLog's development).
4. Papers where a reading agent saw database values or earlier-catalogue files before the paper's first add
   (`human_review/exposed.tsv`).
5. Papers whose catalogue rows changed in response to people's review: a `drop`, `reread`, `unitfix`, `cellfix`,
   `recover`, `pmfix` or `limitfix` line of `log.tsv` at the tag whose text names a review, reviewer, people or human
   (the download marks' "Verify you are human" aside).

## Sources
- **CatLog:** the kcat, Km and kcat/Km rows of `catalog.jsonl` at the tag, in catalogue units; a value kept over a mass
  concentration is left out (`catlog.molar` is None). The catalogue holds no derived kcat/Km and no censored value.
- **EnzyExtract:** its released database (`TheData.parquet`, sha256 903023a9…), every kcat, km and kcat_km cell
  converted exactly as the broad test converts it (`ee_values`), exact repeats dropped (`no_repeats`).

## Matching
Per paper and metric, a reference value r is **held** by a source when the source has a value v with
|v − r| ≤ 0.015 r, the broad test's tolerance. One to one: pairs are taken closest first, each source value used at most
once. No labels are compared, as in the broad test, so a held value can be a chance match with another record's number,
for both sources alike.

## Endpoints
Each is reported whichever way it falls.
1. **Confirmed values held.** The share each source holds, and CatLog minus EnzyExtract with a paired paper bootstrap
   95% interval (B 10,000, seed 20261031). A difference is claimed only if the interval excludes zero.
2. **Not-found or wrong values held.** Per source: the values held, and the papers holding at least one. An exact
   two-sided sign test on the papers where only one source holds one; a difference is claimed at P < 0.05.

Secondary: endpoint 1 by metric; endpoint 1 by the database each reference value came from (`old_source_db`); the
confirmed values neither source holds; endpoint 2 by category.

## Limits stated now
- **People make mistakes too.** Agents' adjudications of some rejections sided with the agent (24) or with both (31).
  The rejections checked against the paper and cleared are left out (`CLEARED`); the rest stand as the person decided.
- **The reference holds only what the earlier catalogue held.** A value both sources hold that it lacked is not scored,
  so endpoint 1 is recall against database-derived values, not against everything the paper prints.
- **Lenient to EnzyExtract.** People confirmed values as printed, which includes values a paper credits to earlier work
  and Hill or apparent constants, which CatLog leaves out by rule and EnzyExtract keeps.
- **Label-free matching,** the same for both sources.
- **Not a random sample of papers:** they are the papers people chose to review.

## Fixed from the commit on
The reference, the papers and the exclusions, the sources, the matcher and the endpoints. The code (`build.py`) is
written after this commit, and a separate agent recounts every number from the inputs with its own code.
