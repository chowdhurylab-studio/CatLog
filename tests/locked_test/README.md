# The locked test

Held-out papers that nothing had read, each read once by CatLog's frozen first pass (reader, independent verifier and
code checks, at tag `catlog-freeze-20261109`, commit fb0cf1758951) and once by a plain reading by the same model
(Claude Opus 5.5 at maximum effort, one session per paper). Every disagreement and 500 agreeing pairs were judged blind,
two judges per chunk and a third on split claims, with planted errors as a gate. 83 of the 119 drawn papers were
analysed.

## The plan and when it was fixed

`PREREGISTRATION.md` is the registration: the file as committed at 8bfc6be, the last of its commits, before the first
result. Its body is as registered at 708f4b3; the three later commits only append to its "Record" section (its "Changes
after it"), each before triage, as that section says.

| Commit | Time (US Central) | What it did to `PREREGISTRATION.md` |
| --- | --- | --- |
| eb9d87f60b626d7ad5a653c3761940de0cc8042b | 2026-11-09 19:41:23 | the draft, after the code review and before the review rounds; not the registration |
| 708f4b38ba0a423e7732a30d497264ad3f7a7779 | 2026-11-10 16:31:03 | **registered**: endpoints, set rule, judging, gate and limits, "fixed before the first session" (kit b9b401e, snapshot fb0cf1758951) |
| 86d1eb52f1ee4afb858c5e0b04b4a2f00ac3aac1 | 2026-11-11 04:03:44 | records the code of the pre-registered curation secondary (kit 546f558), committed before triage |
| 91d6ad9c3b5da5ddadbdadcdf6b3fb32b0c2ef52 | 2026-11-11 10:27:24 | records how the copy's last papers were read (operational) |
| 8bfc6be8076c32994ff222e5768c83043d9aa58c | 2026-11-11 11:58:30 | records the audit bug fix (kit f3e2a20), the re-reads' shared `/tmp` folders, the scan hits and the set of 83 (`--short`), before triage |

- **First session:** 2026-11-10 16:31:27, 24 seconds after the registration (the kit's session records).
- **Triage** (the set and the claims): 2026-11-11 11:58:38. **Report** (`results.json` "time"): 12:53:35.
- **First result committed:** ae74b6a43da0fe48efa88341d5f2cfe1e03b6333, 2026-11-11 12:56:20.

`PLAN.md` is the plan of 9 November that the registration follows (41464f3a161bef59d61214e8532be5ea797c0f78,
2026-11-09 07:08:36, unchanged since): what the test answers, what is frozen, and the scorer's first design. It is
not the registration.

`PREREGISTRATION.as_registered.md` is the same file as registered at 708f4b3, before the three appended records, so
the two can be compared directly. All three files are byte for byte as committed (`git hash-object <file>` gives these
ids): `PREREGISTRATION.md` 586f5dd037f2893349a2edc3da74f3bdecdf57dc, `PREREGISTRATION.as_registered.md`
46e64e28429dda3c54461f2f5dc8df08a3537873, `PLAN.md` d9faa56cfacc4aa90e95bbeddc95c73657f2e07e.

## Files

| File | What it is |
| --- | --- |
| `PREREGISTRATION.md` | the registration, with its amendments |
| `PREREGISTRATION.as_registered.md` | the registration as first committed (708f4b3) |
| `PLAN.md` | the plan it follows (above) |
| `drawn_papers.tsv` | the 119 drawn papers in the seeded draw order (seed 20261109): analysed or not, the first reason a paper left the set, and whether CatLog's copy read it in two launches (the registered sensitivity analysis) |
| `values.tsv` | every stored value of both sides on the 83 papers: CatLog's (`source` catlog, its row id) and the plain reading's (`source` plain), with the value in catalogue units, the printed cell and unit, the labels each side wrote, CatLog's quoted line, and the pair it was matched to; CatLog's rows carry their stamps (models, prompt and task hashes, code commit) |
| `repeats_dropped.tsv` | the plain reading's exact repeats dropped before matching (as registered) |
| `claims.tsv` | every claim the judges ruled on (1,388): the disputed values, 1,000 values of the 500 sampled agreeing pairs, and the 105 planted errors (`kind` decoy; `planted` the change, ×60 or ×1000; `planted_from` the kind of value it was made from), as the judges were shown them, with each judge's verdict and the final verdict by the registered rule |
| `verdicts.tsv` | every verdict as each judge wrote it: where the judge found the value, whether on a page image, and the judge's reason (dropped where it copies the paper's text) |
| `curation_matches.tsv` | the pre-registered secondary: each scored value of EnzyExtract's manual curation (by its row in `manual_curated_runeem_dataset.csv`) and which side's value matched it |
| `RESULTS.md`, `results.json` | the scorer's report (`score_locked.py report`) and its aggregates |
| `sensitivity_read_once/`, `sensitivity_without_misprint_papers/` | the registered sensitivity analysis without the 41 papers the copy read twice, and the post hoc one without the two papers whose misprinted headers CatLog corrected |

The scorer is `analysis/tests/score_locked.py`, with the shared rules of `score_w1.py`; `final` in `claims.tsv` is
recomputed here with `score_w1.final_verdict` and agrees with `results.json` on every claim's count.

## Changes made here

None to the plans or the reports. The scorer's JSON outputs are aggregates: their per-value lists (`wrong`,
`misses`, `restated_values_not_counted_as_misses`) are replaced by a note, since the same claims and verdicts are in the
TSV files. In the TSV files, 131 of CatLog's 1,400 quoted lines are blanked for having more than 25 words, 62 of 2,869
conditions and 29 of 1,388 claim details for copying more than 25 words of the paper, and 95 of 2,786 judges' reasons for
sharing a run of 8 words with it.

## Not here

The papers (their PubMed ids only), the agents' and judges' transcripts, the code reviews of the kit (`review/`), the
writing notes, and the post hoc blind re-checks of CatLog's 34 values judged wrong: kept by the authors.
