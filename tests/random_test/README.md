# The test on 147 random papers (not registered)

This folder keeps the test's working name, the random test, which its files and the scripts in `analysis/` use.

Papers CatLog had finished, drawn at random, each read once by a plain reading (Claude Opus 5.5 at maximum effort, one
session per paper, on 4 November 2026) and compared with CatLog's catalogue: the reading plus every later check. Every
disagreement and a sample of the agreeing pairs were judged by agents not told which side stored a value, two judges per
chunk and a third on split claims, with planted errors. The test was judged twice: first with each claim's short record
(`first_judging/`), then again with each record's full details, the judging the paper reports. 147 papers were analysed.

**This test was not registered.** Its papers were drawn, read and judged before any plan was committed for it, and the
paper calls it unregistered. Its records are here because the paper reports it beside the test on 83 unread papers.

| Commit or record | Time (US Central) | What |
| --- | --- | --- |
| the kit's session records | 2026-11-04 16:00:46 to 23:56:44 | the plain reading's sessions |
| 4e5ccaae54d187e88c7c0935cf3b30e69f7bf027 | 2026-11-06 12:58:10 | the first judging's report |
| f8b0afdf602e6a42c9c613923f4f8ac043aab8a5 | 2026-11-06 16:31:28 | `FULL_RECORD_PLAN.md`: the re-judging with each record's full details, planned, reviewed twice and drawn. Written after the first judging's result and because of it, so it is not a registration of the test |
| 3b59a97b499b57a821b1ea88c644c69e1a59d9a5 | 2026-11-09 12:49:58 | the re-judging's results (its report, `RESULTS.md`, made at the kit's commit 70e5f04; its scorer, `analysis/tests/score_randfull.py`, is the same at f3e2a20) |

## Files

| File | What it is |
| --- | --- |
| `FULL_RECORD_PLAN.md` | the re-judging's plan, as committed at f8b0afd and unchanged since, but for one change: the names of two accounts (e-mail addresses' local parts) are left out, so the file is not the committed blob 3208b4db47387bf9e5d7ae445a0527c1f39eab40 |
| `drawn_papers.tsv` | every paper drawn: analysed or not, and why not |
| `values.tsv` | every stored value of both sides: CatLog's catalogue (`source` catlog, its row id) and the plain reading (`source` plain), with the value in catalogue units, the printed cell and unit, each side's labels, CatLog's quoted line and stamps, and the pair it was matched to |
| `repeats_dropped.tsv` | the exact repeats dropped before matching |
| `claims.tsv` | every claim of the full-record judging (2,132): disputed values, the sampled agreeing values and 176 planted errors (`kind` decoy, `planted` ×60 or ×1000), with each judge's verdict, the final verdict and, for each claim, the first judging's claim and its final verdict. `in_analysis` is `no` for the 3 papers whose judge session was refused or switched model; a claim of a judge step stopped by refusals is `cannot_decide`, as the scorer rules |
| `verdicts.tsv` | every verdict of the full-record judging as each judge wrote it, the reason dropped where it copies the paper's text |
| `first_judging/claims.tsv`, `first_judging/verdicts.tsv` | the same for the first judging (2,042 claims, 174 planted) |
| `RESULTS.md`, `results.json`, `comparison.json` | the scorer's report of the full-record judging, its aggregates, and the comparison of the two judgings on the same papers |
| `first_judging/RESULTS.md`, `first_judging/results.json` | the first judging's report |

The scorers are `analysis/tests/score_randfull.py` and `score_rand.py` (with `score_w1.py`); `final` is recomputed here
with `score_w1.final_verdict` and agrees with each report's counts.

## Changes made here

- `FULL_RECORD_PLAN.md`: the names of the two accounts it gives are left out (above), by two exact rules of
  `../../sync_tests.py`.
- The JSON outputs are aggregates: their per-value lists (`wrong`, `misses`, the new errors of `comparison.json`) are
  replaced by a note, since the claims and verdicts are in the TSV files.
- In the TSV files, 351 of CatLog's 4,447 quoted lines are blanked for having more than 25 words, 18 of 9,032
  conditions, 10 claim details and 7 judges' "found at" for copying more than 25 words of the paper, and 304 of the
  8,310 judges' reasons of both judgings for sharing a run of 8 words with it.

## Not here

The papers (their PubMed ids only) and the sessions' transcripts: kept by the authors.
