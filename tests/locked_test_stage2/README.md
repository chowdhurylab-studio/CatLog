# The locked test's second stage, and its page check

**Stage 2** scores, on the 79 of the locked test's 83 papers that EnzyExtract's manual curation covers, every source
against that curation: CatLog's stored values and the plain reading from the locked test, EnzyExtract's nine runs on its
benchmark (from its supplementary files; RGF, its full pipeline by our reading, is the primary comparator), its released
database and BRENDA 2026.1. Nothing is judged in stage 2; it is code only.

**The page check** then checked on the page every value that the curation, CatLog and RGF do not all three agree on
(1,055 values in 63 papers), one agent per paper (Claude Fable 5.2, which made none of the values) shown the three
readings as A, B and C in a seeded random order, no source named. It is post hoc (written after stage 2's table) but its
rules, task builder and scorer were committed before any of its verdicts.

## The plans and when they were fixed

| File | Commit | Time (US Central) | What |
| --- | --- | --- | --- |
| `STAGE2.md` | 41d125f9520ca860fd75197fc5cf80787ed7e3ee | 2026-11-11 14:36:53 | **stage 2 registered**: papers, sources, the scoring code and its four rules, endpoints and seed, "committed before any EnzyExtract output on these papers was scored" |
| | 47994079414e23b856a1d38901cfc9f0845aa2f9 | 2026-11-11 15:04:54 | stage 2's scorer (`analysis/tests/second_stage/score_stage2.py`), reviewed on made-up data, committed before it ran on these papers |
| | 53f737ebb11d456d5d61242b7ed5dc99ebfc4645 | 2026-11-11 15:08:00 | **stage 2's first result** |
| `CHECK_PLAN.md` | 0cf7f0d233d2427f4dbdd263ce6193b23f1cb4d4 | 2026-11-11 16:14:29 | **page check registered**: its rules, with its task builder and scorer, "committed before any verdict of this check exists" |
| `CHECK_PLAN.md` | 1e7f176dd90d3f1c39d2cdcff5089cfe0b4ef62f | 2026-11-11 16:15:37 | amended before any verdict: the two misprint verdicts and both views (as printed, corrected) |
| | | 2026-11-11 16:17:08 | the page check's first verdict file is written (its file time in the kit's records) |
| | 36bbe61cd279a87bd1100ee27854c0d827e74b39 | 2026-11-12 09:00:30 | **the page check's first verdicts committed** (part 1: 33 papers, kcat complete) |
| | 78d823b651d844813b040c351897d5d15ded8113 | 2026-11-12 10:00:07 | the page check complete (63 papers, 1,055 values) |

Neither plan has changed since. `CHECK_PLAN.as_registered.md` is the page check's plan as first committed (0cf7f0d),
before the amendment. All three are byte for byte as committed (`git hash-object <file>` gives these ids): `STAGE2.md`
c6856c27a082e053b3188c0df1f957d19ebf97f6, `CHECK_PLAN.md` 767dac54f2784a339da329c352cdf586b4c994ed,
`CHECK_PLAN.as_registered.md` cadbb4419094baa598b2f70116acff72dcad18f4.

**Corrected scores, after the result.** On 18 November an audit of both EnzyExtract comparisons found scoring errors
(the units reader misread some of EnzyExtract's strings; the page check's reference merge let a value judged right
merge into a value its own reading already held; and others). The corrected scorer, `score_corrected.py`, runs
beside the registered one and reproduces it exactly with the corrections off; its outputs are in `corrected/`. The
corrections are listed, with their reasons and every number they move, in `../enzyextract_broad/CORRECTIONS.md`
(commits 87c06fdb to 0f2a687b, 18 November 17:43:40 to 19:05:25).

## Files

| File | What it is |
| --- | --- |
| `STAGE2.md`, `CHECK_PLAN.md` | the two plans, as committed |
| `CHECK_PLAN.as_registered.md` | the page check's plan before its amendment |
| `RESULTS.md`, `results.json` | stage 2's registered table: recall and precision of each source against the curation, with paired paper-bootstrap intervals (aggregates; the database sources counted only) |
| `page_check/values.tsv` | every value shown to a page-check agent: the paper, its id in the agent's task (`A0`, `B3`, ...), whose reading it is (`curation`, `catlog`, `rgf`), the value itself as a reference (a CatLog value id, which `../locked_test/values.tsv` holds, or a row of EnzyExtract's file), whether it was to be judged, and each agent's verdict, the right value it gave and its evidence (dropped where it copies the paper's text) |
| `page_check/key.json` | the blinding key: which reading each letter was, per paper; the two parts and the 6 papers that got a second agent |
| `page_check/RESULTS.md`, `page_check/results.json` | the page check's registered scores (`score_checked.py`): the corrected reference, both views, every source's recall and precision |
| `corrected/` | the corrected scores: `table.json` (stage 2's table read three ways: as registered, with the misreads fixed, and as written), `counts.json`, `f6_pagecheck.json` (the papers in EnzyExtract's fine-tuning set), `page_check/` (the page check with both fixes), `RESULTS.md`, and `changed_cells.tsv`, the cells of the curation and the runs that the corrected reader reads differently, by their rows |
| `score_corrected.py` | the corrected scorer (`check_tasks.py`, `score_checked.py` and `score_stage2.py` are in `analysis/tests/second_stage/`) |

EnzyExtract's files, named by row here (0-based, in the order pandas reads them): from the article's `SI.zip`,
`dataset_223_EnzyExtract_BRENDA_manual_curation/manual_curated_runeem_dataset.csv` (sha256 37b2ff4cde194521a1afa247dfd4c29bf9eebfc1d4cb9a566e10dfb03a7b68ca) and
`dataset_384_pipeline_benchmark_dataset/rumble_<run>_dev1.parquet` (RGF: sha256 88433dccadef7829912284bbdbdf0aaf726d716249ff9c6d549e6dbbfad40ecf). The tests read the runs from
TSV copies of those files; the sync checks that each copy holds the file's rows in order.

## Changes made here

None to the plans. The JSON outputs are aggregates (their per-value lists left out); `RESULTS.md` files are as written.

## Not here

The page-check agents' transcripts, the first check of 6 papers that this plan replaced (`check_first7/`, a selected
set), and the independent recounts of the corrected scores: kept by the authors.
