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
- Changes after it: none yet.
