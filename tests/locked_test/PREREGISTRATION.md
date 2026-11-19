# Locked test: what is fixed before the first paid session (pre-registration, 9 November 2026)

Written after the independent review of the code (55 findings; `PLAN.md`) and before any held-out paper was read by
anyone. It is committed before the first locked session; the commit's time is the record. Changes after that are listed
at the end with their reason, and never touch the judging rules or the endpoints once any output has been seen.

## Question
On held-out papers that nothing had read, how often does CatLog's frozen first pass store a wrong value, against one
plain reading by the same model? CatLog's first pass is its reader, independent verifier and code checks: catlog-copy
at snapshot fb0cf1758951, tag `catlog-freeze-20261109`. The plain reading is Opus 5.5 at maximum effort, one session,
with the random test's prompt.

## Papers
- **Draw.** The 119 held-out papers ready on 9 November, in the seeded order of `records/orders/locked_draw.txt` (seed
  20261109). Ready means: status todo, never read, text with a kept PDF or publisher XML, not OCR-only, and with kinetic
  terms. `locked_draw.tsv` gives every held-out paper's reason.
- **Order of work.** Papers are read in that order, in batches, by both sides.
- **The set.** It is the first 100 papers of that order with a usable read from both sides.
  - Usable plain read: it passed its format check, ran on claude-opus-5-5, and the audit found no broken rule.
  - Usable CatLog read: the paper finished in the copy, every agent of the kept launch ran on claude-opus-5-5 (a Sonnet
    retry takes the paper out), and no rule was broken.
  - The text, supplement and original are the same on both sides and for the judges.
- **What leaves the set.** A paper refused by the safety filter on either side, read by another model, or breaking an
  isolation rule leaves the set and is listed with its reason. A paper that fails for an operational reason (usage
  limit, crash) is read again, not replaced.
- **Fewer than 100.** If fewer than 100 of the 119 are usable, the test reports on all usable papers and says so.

## Primary endpoint
- **Rate.** Wrong values per 1,000 stored values for each source, judged blind with each record's full details.
  cannot_decide is left out of numerator and denominator. An agreeing pair that is not sampled counts as right for both.
- **Comparison.** Plain minus CatLog, per 1,000, with a paired paper-level bootstrap 95% interval (B 10,000, seed
  20261031).
- **Stated in advance.** At this size the interval may well include zero, as the random test's did, because errors
  cluster in few papers. A fold difference is claimed only if the interval excludes zero.

## Secondary
- Papers with a wrong value, with exact intervals, and their paired difference.
- The rate with the agreeing sample scaled to the unsampled pairs.
- cannot_decide counted as wrong (sensitivity).
- Kinds of error.
- Misses: supported values that only the other source stored.
- Agreement with the EnzyExtract manual curation on the drawn papers it covers (111 of 119), scored by the kit's
  head-to-head matcher, with disagreements reported but not judged. It is used only if its code is written and committed
  before triage; otherwise it is dropped, and the report says so.

## Judging
- **Protocol.** As in the full-record re-judging: prompt `tools/w1/prompts/adjudicate_full.txt`, two judges per chunk, a
  third on split claims, chunks of up to 40 claims per paper.
- **Claims.** Every disagreement, plus 500 agreeing pairs drawn with seed 20261109, each source's value as its own
  claim.
- **Planted errors.** ceil(5%) of each paper's claims, at least 1: values of unsampled agreeing pairs changed 1000-fold
  or 60-fold. A paper with no such value takes its own claimed values, marked twin-visible. Twin-visible planted errors
  are reported apart.
- **Gate.** At least 90% of the planted errors judged errors, and the first two judges agree on at least 85% of the
  disputed claims.
  - If the gate fails, the result is reported as failed, with its numbers.
  - No re-judging with a changed prompt.
  - One re-judging by fresh judges under the same prompt is allowed only for a technical fault, which is stated.
- **Refused judge sessions.** One more try. A step refused twice leaves its claims cannot_decide, and a paper with
  nothing judged leaves the analysis.

## Isolation and checks
- **Audit.** Every session's transcript is audited. A plain read that broke a rule may be read again once. A judged
  paper that broke a rule is judged again by both judges. A CatLog paper that broke a rule leaves the set.
- **Content scans.** Every judge, plain and copy session is scanned for other papers' verdicts, closed folders and
  hidden fields, and for the answer keys in ~/Downloads/data, which are denied to every session.
- **Stamps.** Every stored row must carry the snapshot's commit and the frozen prompt hashes.

## Fixed from the first locked session on
- The prompts, the frozen copy, the kit's code (the commit recorded below), the draw, the set size of 100, the 500
  sampled pairs and the seeds.
- A bug found mid-run (a crash, a wrong path) is fixed and stated, and the affected step is run again. No judging rule
  or endpoint changes after any output is seen.

## Limits stated now
- CatLog's side is its frozen first pass, not its catalogue. The random test measured the catalogue, after every later
  check.
- A record's shape shows its source, and an agreeing value shows as two claims.
- The judges' rubric holds curation conventions, such as a Vmax per mg not being kcat, that the plain prompt states only
  in part.
- A paper CatLog rightly declines (wrong paper, no kinetics) can count as its misses.
- The 119 ready papers are those with a text on disk on 9 November, and they may differ from the other 250 held-out
  papers.

## Rules as coded (kit b9b401e, after four review rounds: `review/`)
- **Exits.** A paper leaves the set for one of these:
  - a safety-filter refusal on the plain side;
  - on CatLog's side, a refusal that started the workflow's Sonnet retry (an Opus agent that got past a refusal and
    finished, or died at a usage limit, does not count);
  - a read by another model;
  - a broken isolation rule.
- **Not exits.** Anything else that leaves a paper unfinished is operational: the paper is read again, never replaced.
  This includes a usage limit, a crash, and a Sonnet retry with no refusal before it.
- **Inputs.** CatLog's copy takes each paper's text, supplement and original from the judges' recorded inputs, so
  every side reads the same bytes.
- **Stamps.** Every stored row must carry the tag's commit fb0cf1758951 and the frozen prompt hashes.

## Record
- Kit commit at the first locked session: **b9b401e** (branch w1-eval); catlog-copy at snapshot fb0cf1758951; the
  check is clean (10 November).
- Changes after it:
  - **11 Nov 04:03, kit 546f558: the code of the curation secondary**, written as the "Secondary" list allows: before
    triage, while the reads were still running, with no output of the test seen. It is reviewed and tested on made-up
    data only (116 tests). Nothing else changed: no judging rule, endpoint, prompt, draw or seed.
  - **Scope.** `score_locked.curation` scores each side's values, the ones the judging uses (values.json), against
    EnzyExtract's manual curation.
    - Matcher: the head-to-head's. Numbers match within 1.5% of the larger, or 5e-7 in catalog units, the matcher's
      rounding floor.
    - Unscored: the curation's bounds and cells it cannot read.
    - Pairs with a similar description: listed and flagged; their disagreements are not judged.
    - Output: recall and precision with paper-clustered intervals (B 10,000, seed 20261031), and CatLog minus plain,
      paired.
  - **Papers.** Only the set's papers the curation covers are scored, because values.json holds the set alone. The other
    drawn papers it covers (111 of 119 in all) are counted by why each is out.
  - **The condition is checked by code.** The report compares the commit that first holds this code with triage's time,
    and the code that runs with the code committed when triage ran. If either fails, the report says the secondary is
    dropped and computes nothing.
  - **The kit's check.** After this commit, `w1_setup.py check` reports that the kit branch has moved past the manifest's
    b9b401e. This is expected: the manifest is not remade mid-run (no `freeze`). The runners, audits, triage and judges
    do not compare the kit's commit.
  - **11 Nov, how the copy's last papers were read (operational: no rule, endpoint or set rule changed).**
    - Batch 4's copy ran as follow-up launches of at most 10 papers, later 4, each started only when the account's
      5-hour window was under half used. A launch adds its papers only at its end, so a usage-limit stop discards the
      whole launch; batch 3's launch had been lost that way once.
    - Launch more-6: the safety filter stopped the launch session itself while it listed the waiting papers' titles,
      before any agent ran. Its papers were left reading and read again, as for any operational stop.
    - Launch more-7: stopped at the 5-hour limit, and its papers were read again too.
  - **11 Nov 11:55, kit f3e2a20: two audit bugs fixed** (a bug found mid-run is fixed, stated and its step run again).
    The copy's first audit broke 11 papers. Four of those breaks were the audit's errors:
    - 12878037 and 9202000 ran `cd catlog-copy/tools`, then read `../work/<own PMID>.read.json` and `../catlog.py`. The
      audit read those paths from the session's folder instead, naming files above the copy that do not exist.
    - The verifiers of 10411640 and 11488932 made their own private folders with `mktemp -d /tmp/claude-verify-XXXXXX`,
      holding only their own paper's page images and scripts. The audit took them for another session's scratchpad.

    The fix:
    - A `../` is read where the command has `cd`'d to, and also from the session's folder when that names a real path.
    - Only Claude Code's per-user folder `/tmp/claude-<uid>/` counts as other sessions' scratchpads. A copy agent's
      other `/tmp/claude-*` folders and its role folders one level down are noted for copy agents, and still break plain
      sessions and judges.

    Two reviewers tried to break the first version and found that a failed or conditional `cd` could hide a real climb
    out of the copy. The final version breaks all 25 such synthetic cases. Re-run on every recorded audit (the copy's
    and the plain reads of this test, the rules-only check, the random test's plain reads and both of its judgings),
    it changes only those 4 papers' breaks. The copy's broken papers are now 7: 9305868, 10446163, 10480878, 11078532,
    11889053, 11955282, 15123660 (a PubMed tool, network fetches, `git log` in the copy, realkcat's `.env`). The
    reviews are in `review/auditfix/`.
  - **11 Nov: the copy's re-reads shared the first launch's `/tmp` folders** (a gap in the kit; no rule changed).
    - After an operational stop, `claim` moves a paper's work files to work/old, but the first launch's
      `/tmp/read-<PMID>` and `/tmp/verify-<PMID>` folders stay. 41 papers had agents in two launches
      (`records/locked_copy_read_twice.txt`): batch 3's 30, batch 2's 6 and more-7's 5.
    - The second launch's agents mostly used the same folders. Several made their own subfolders when they saw others'
      files.
    - A scan of every re-reading agent of the 41 found one that opened a decision-carrying leftover (a script or data
      file it had not written). 9495750's verifier printed
      the earlier verifier's check script and the first 600 characters of its verdict script. It said it would keep
      its work separate and not use them, and it did not. No re-reading agent opened work/old.
    - The paper is kept, as the coded rules say. The report adds a sensitivity result without the papers the copy read
      twice. This sensitivity is chosen now, before any judging.
  - **11 Nov: before the judges, the two copy verifiers' mktemp folders were moved from `/tmp` into
    `records/a6_tmp_leftovers/`.** Judge sessions are denied the copy's `/tmp/read-*` and `/tmp/verify-*` folders, but
    not those two names.
  - **11 Nov: the content scan's hits were looked at and accepted** (`--accept-scan-hits`; `review/scan_hits.md`).
    They are rows of the copy's own queue file, reprint searches by title, and one read file's format printed by a
    reader of another paper. None is a verdict, a key, or another side's output.
  - **11 Nov: fewer than 100 usable papers, so triage runs with `--short`.** 83 of the 119 are usable, as the "Fewer
    than 100" rule provides. Left out: plain refused 12, copy refused 17, copy rule broken 7.
  - **11 Nov: 12888555, 11943176 and 10429198 were not read again in the copy.** The plain read refused all three, so
    they leave the set whatever the copy does. A launch session that showed their titles had just been stopped by the
    filter, which halted 8 other papers' reads, so they were left out of the follow-up launches. Triage counts them
    under the plain refusal.
