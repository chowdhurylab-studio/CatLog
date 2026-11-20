# The test on 300 random papers: CatLog against EnzyExtract's released database

This folder keeps the test's working name, the broad test, which its plan, `CORRECTIONS.md` and scripts use. The test
was registered.

On papers both cover, which holds more of the kinetic values the papers report, and fewer wrong ones: CatLog's catalogue
at the paper's freeze (tag `paper-catalog-freeze-20261116`) or EnzyExtract's released database (`TheData.parquet` of its
supplementary files)? The first 300 papers of a seeded order of 3,245 papers both cover. A value the other source does
not match is disputed, and every disputed value (4,476 in 191 papers) was judged on its paper by one agent (Claude Fable
5.2), shown the two readings as A and B, no source named; a seeded 10% of the papers got a second agent for agreement.

## The plan and when it was fixed

| Commit | Time (US Central) | What it did to `PLAN.md` |
| --- | --- | --- |
| 12a10895a904be356f945f34abf13e93af2a1dd7 | 2026-11-18 05:08:10 | the draft, with the frame, power simulation and a 5-paper pilot; not the registration |
| cd4cbe00c977929ddc5db89c8bbbf454a6fb6d1a | 2026-11-18 06:26:50 | **registered** (the owner's yes): sample, values, page check, rules and endpoints, "fixed before any judge runs" |
| 8316180a803c18d68e9d86015b63060381b3b124 | 2026-11-18 06:28:50 | amended before any judge ran: the launch only (Claude Code 2.1.325, stops on repeated failures) |
| c9df866784ddd62965bd07a3cd70454b1c971c65 | 2026-11-18 06:31:21 | finalized with the sha256 of the frame, the sample, the key, the judges' prompt and the code, before any judge ran |

- **First judge:** 2026-11-18 07:02:03 (the judges' logs; the last ended at 07:57:11).
- **First result committed:** a6e44c584300db459894b1cf21d196757c7b3d7a, 2026-11-18 08:03:31.

`PLAN.md` and `judge_prompt.md` are byte for byte as committed at c9df866 and unchanged since, and
`PLAN.as_registered.md` is the plan as first registered at cd4cbe0, before the two amendments (`git hash-object <file>`
gives these ids): `PLAN.md` d7205f48d7cd2dccdbe25368f8190f32adaefbbc, `PLAN.as_registered.md`
ab1bce5b20522b59e04b0746e1938f80c20e3a1d, `judge_prompt.md` c4e457e4a9a64dba3f95b5d4c0fe86e70e861593. The registered inputs are byte for byte too, so their sha256 is the one `PLAN.md` gives:
`frame.tsv`, `order.txt`, `sample_300.txt` (registered as `run/sample_300.txt`), `key.json` (`run/key.json`) and
`judge_prompt.md`. `build.py` and `run_judges.py` were registered by sha256 too, but their copies here have the
machine paths replaced (below), so they no longer hash to it.

**Corrected scores, after the result.** `CORRECTIONS.md` (first committed 87c06fdb, 2026-11-18 17:43:40; last
0f2a687b, 19:05:25) lists every correction to the scoring of both EnzyExtract comparisons after their results, with its
reason and every number it moves. The corrected scorer, `score_corrected.py`, runs beside the registered `build.py score`
and reproduces it exactly with the corrections off; its outputs are in `corrected/`.

## Files

| File | What it is |
| --- | --- |
| `PLAN.md`, `judge_prompt.md` | the registration and the judges' prompt, as committed |
| `PLAN.as_registered.md` | the plan as first registered (cd4cbe0) |
| `frame.tsv`, `order.txt`, `frame_summary.json` | the frame (3,245 papers, each with its counts of values, agreed and disputed values and unread cells), the seeded order (seed 20261118), and why each other paper is out |
| `sample_300.txt` | the sample: the first 300 papers of the order |
| `key.json` | the key of which reading was whose: for each paper, which reading was A and which B, and the reading id of every value |
| `values.tsv` | CatLog's stored values on the 300 papers: its row id, the value in catalogue units, the printed cell and unit, its labels, its quoted line, its record, and the EnzyExtract row it agreed with |
| `enzyextract_rows.tsv` | EnzyExtract's values on the 300 papers, each by its row of `TheData.parquet` and its metric: how its string was read (CatLog's units code, the same after a notation fix, or the database's own number) and the CatLog value it agreed with |
| `verdicts.tsv` | every verdict (4,476 by the first agents, 546 by the second): the paper, the part, the reading id, whose reading it was, the value (a CatLog value id or a row of `TheData.parquet`), the verdict, the right value the agent gave and its evidence (dropped where it copies the paper's text) |
| `RESULTS.md`, `results.json` | the registered scorer's report (`build.py score`): the primary endpoints and every secondary one |
| `CORRECTIONS.md` | the corrections after the result (above) |
| `corrected/` | the corrected scores: `RESULTS.md`, `results.json`, and the table of corrections (`corrections_table.md`, `corrections.json`, made by `corrections.py`) |
| `build.py` | the frame, the tasks and the registered scorer |
| `run_judges.py` | the launch of the judges |
| `score_corrected.py`, `corrections.py` | the corrected scorer and the table of corrections |
| `power.py`, `power_results.json` | the sample-size simulation in the plan |

EnzyExtract's database is `dataset_crude_database/TheData.parquet` of the article's `SI.zip` (sha256
903023a9ec5366a4a560c1e11b5f6dca9ef5a27a6686ef633e7297866126290b). A row here is its 0-based position as pandas reads
the file; `pd.read_parquet(path).iloc[row]` gives it. The values were read from a TSV copy written from the parquet in
order; the sync checks the copy's sha256 and row count.

## Changes made here

- `CORRECTIONS.md`, by three rules of `../../sync_tests.py` (DOC_RULES), each checked to match exactly as often as
  stated: the 11 rows of its table "F5 from the strings themselves" print EnzyExtract's database strings, and each string
  is replaced by its row or rows of `TheData.parquet` (the readings our code made of it, the verdict and the judge's right
  value stay); the one example string in the text above that table is replaced the same way; and two cells of
  EnzyExtract's runs, quoted as strings the reader still misses, are replaced by a description of each. Its blob id is
  therefore not the committed one (the committed file is 0f2a687b's).
- `build.py`: the CatLog folder's and the kit folder's paths read `<the CatLog folder>` and `<the kit folder>`.
- The JSON outputs are aggregates: per-value lists that hold EnzyExtract's cells (for example the unread cells per paper
  in `corrected/results.json`) are replaced by a note.
- In the TSV files, CatLog's quoted line is blanked where it has more than 25 words, and a verdict's evidence where it
  shares a run of 8 words with the paper (counts in the sync's output).

## Not here

`run/jobs.json` (every judge's filled prompt, which prints EnzyExtract's values), the judges' transcripts and session
logs, the pilot on 5 papers outside the frame, and the independent recount of the corrected scores
(`corrected/recount_broad.json`): kept by the authors.
