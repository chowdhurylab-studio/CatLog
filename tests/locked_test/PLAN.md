# Locked test and rules-only check (plan and state, 9 November 2026)

The owner (9 Nov): "what is locked test or rules only test - see whats needed - run it i guess".

## What each test answers
- **Locked test.** CatLog as frozen today, on held-out papers nothing has read, against one plain read by the same
  model. The random test compared plain reads with CatLog's *catalogue* (the reading plus every later check). This
  test compares them on unseen papers, with CatLog's first pass only: reader, independent verifier and code checks.
- **Rules-only check.** CatLog today on the 53 trap papers Opus 5.5 read in the hard-case test, scored on the same keys
  as before. It shows whether today's written rules (the reader alone) avoid the traps the earlier readings fell into,
  or whether the verifier and the code are still needed. (On these papers, the rules were written after CatLog's checks
  caught the traps, so they are in-sample for the rules. The locked test is the out-of-sample one.)

## What is frozen
- Main 5d99a6a (9 Nov 06:31) merged into the kit branch `w1-eval` (4032773). The prompts (read.md 86e5d7668c1c,
  verify.md 6cdd7782a0f2) and the task text (369efeee4c39) are the same as on 1 November. catlog.py (the code checks
  of 1-9 Nov), CLAUDE.md and the tools changed.
- catlog-copy (the isolated CatLog folder, its own one-commit repository) is at the snapshot **fb0cf1758951**, cut from
  kit commit 418acaf. The main repository tags that snapshot `catlog-freeze-20261109`. Every row it stores carries
  `pipeline_commit` fb0cf1758951. `w1_setup.py check` reports no problem.
- The CLI is pinned to 2.1.317 (the first random-test judging ran on 2.1.309, which the app deleted on 7 Nov). Every
  session runs on claude-opus-5-5 at max effort, with no Sonnet fallback kept: a paper whose agents switched model is
  read again once, then left out.
- Manifest: `~/Documents/kinetics-reading/MANIFEST.json` (`freeze` record). The 1 Nov manifest is kept in
  `records/manifests/`.

## Locked test design (kit `tools/w1/score_locked.py`)
- **Papers.** The 369 held-out papers of `sources/holdout_locked.txt`. A paper is ready when all of these hold:
  - status todo, and never read (no catalogue row, no work file, no add in log.tsv);
  - text on disk with a kept PDF or publisher XML, not an OCR-only text;
  - the kinetic terms `next` needs are in its text.

  119 are ready. They were drawn in a seeded order (20261109) on 9 Nov: `records/orders/locked_draw.txt`, with every
  held-out paper's reason in `locked_draw.tsv`. Of the rest: 125 have no text yet, 76 need the browser, 17 were read
  before the hold, 17 are not in the queue, 8 need a supplement, 6 are OCR-only and 1 is the wrong paper.
- **Reads.** Two reads of the same papers in the draw's order, in batches:
  - plain: one read with the random test's prompt (`run_plain.py --arm A0 --run locked`);
  - CatLog: `run_a6.py locked`, after `w1_setup.py a6-papers locked`.

  The first 100 papers with a usable read from both are the set. A refusal by the safety filter, a model switch that
  repeats, or a broken isolation rule takes a paper out.
- **Judging.** The random test's pairing, as in `score_rand.py`. All disagreements are judged, plus 500 sampled agreeing
  pairs, each source's value as its own claim. Every claim carries its record's details, and blind judges decide with
  the full-record prompt and protocol (`adjudicate_full.txt`, two judges plus a third on splits). Planted errors are
  1000-fold and 60-fold changes of unsampled agreeing values. Each judge role works in its own folders.
- **Report.** `score_rand.py`'s report: wrong values per 1,000 with a paper bootstrap, papers with a wrong value, misses,
  the judges' check.

## Folders built (no quota used)
Plain inputs `papers/<PMID>/` and judge inputs `checks/<PMID>/` for all 119 (records/hard_inputs.json,
judge_inputs.json). catlog-copy holds the 53 trap papers now (`a6-papers hard`). The locked set is laid down after the
trap run is kept.

## Cost and timing (estimated 9 Nov, from the kit's session costs)
| Job | List price | Share of a week | Note |
|---|---|---|---|
| CatLog copy per paper | ~$5 | | from the pilot |
| Plain read per paper | ~$1 | | |
| Judge session | ~$0.7 | | |
| Rules-only check | ~$270 | about 18% | |
| Locked test (110 papers) | ~$800 | about 50% | |

The account is shared with the batch loop and the other chats. On 9 Nov morning it rose about 10% an hour while
"Send 10 batches" ran. The owner chooses the order.

## Papers named in CatLog's own instructions
Every reader and verifier loads CatLog's CLAUDE.md, and the prompts are part of its task. Together they name 8 of the 53
trap papers by PMID, with their trap: 12604203, 21443518, 11284698, 21306440, 11779198, 26570983, 21361343 and
25514023. Code comments name 3 more: 21094652, 21757926 and 10712619. The smoke test's reader of 12604203 said so in its
note, and a scan of the snapshot's files found the rest. Production agents load the same files, so this is how CatLog
reads those papers today. For the rules-only question, the main result is on the 42 papers nothing names, and the 11
named ones are counted apart (`score_today.py`, `named_in`). The same scan found **none of the 369 held-out papers**
named in any instruction, prompt or code file, so the locked test has no such leak.

## State
- 9 Nov 06:51-07:05: smoke test of the frozen copy on the first 2 trap papers (`run_a6.py hard --pmids 12604203
  9415401`, run A6-hard, launch `main`), run alongside the full-record judging (302 sessions, since 06:09). Both papers
  are done, with 4 agents, all on claude-opus-5-5 and no switch. 51 values were kept (18 + 33) and 19 censored values
  went to bounds. The stamps are right: `pipeline_commit` fb0cf1758951, read 86e5d7668c1c, verify 6cdd7782a0f2, task
  369efeee4c39. The scorer, tried on these two in a scratch copy, puts both readings right on every cell.
- The other 51 trap papers wait for the judging to end: other chats are reading (60 papers claimed in 30 min at 06:59),
  so this chat keeps to 3 agents. Next: `run_a6.py hard --pmids <the 51>` (a follow-up launch in the same state), then
  `w1_setup.py reset-a6 hard`, `w1_audit.py A6-hard`, `score_today.py`.
- The owner (9 Nov ~07:00): keep the judges running while the account has tokens. Another account can be switched to,
  for the app and the judges' command line (`.../cli/2.1.317/claude.app/Contents/MacOS/claude auth login`).
- Scorer for the rules-only check: `paper/evidence/hard_cases_20261102/today/score_today.py`, with code scoring first.
  The blind re-score of today's readings follows the hard-case method (rescore2's workflow), once the owner agrees to
  its ~110 agent sessions.
