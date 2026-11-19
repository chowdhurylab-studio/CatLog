# The random test judged again with each record's full details (plan and draw, 6 November 2026)

**Why.** The first judging showed each claim's metric, value, unit, enzyme, organism, variant, substrate, cosubstrate, pH
and temperature, so that the source stayed hidden; the record's location, construct, conditions and notes were not shown.
All 28 values it judged to carry another value's label or number (14 per source) name the judges' fact in those fields
(`label_verdicts_full_record.tsv`). Read in full, by hand: plain 49 wrong instead of 63, CatLog 1 instead of 15. The owner
(6 November): "we can do more if you think that will strengthen our case", and, offered a blind re-judging of the 28: "if
this is better i am good and stronger as well. i dont mind".

**Design (after two independent reviews, below).** Every value of every claim of the first judging (not its decoys) is
judged again, on all 144 papers with claims, each source on its own (a claim the first judging showed once for both
sources is two claims here, since their details differ), in its paper's company, by fresh blind judges under the same
protocol (two judges per chunk, a third on split claims; Opus 5.5 at max effort; planted errors). Each claim adds one
"details" text: the record's location and, for CatLog, its construct, conditions and metric note; for the plain read, its
location and conditions. The judges' prompt (kit `tools/w1/prompts/adjudicate_full.txt`) reads fields and details together;
a detail that says the value itself is of another metric, enzyme, variant, substrate or cosubstrate makes the claim wrong,
a mention is no contradiction, and the location is only a pointer. Planted errors are values of the paper's agreeing pairs
that no claim shows, changed 1000-fold or 60-fold, with their own details (9 of 176 have their twin in the chunk, on papers
with no unshown value; counted apart). The same report code scores both judgings (`score_rand.py report --which`), and the
comparison restates the first judging on the second's papers with a paired paper bootstrap.

**Isolation.** Each judge role works in its own folder family `folios/<code>/<PMID>/` (APFS clones of the first judges'
input files, sealed read-only), with its own scratch code. Closed to it: the first judges' folders and Claude sessions
(transcripts, saved tool results, temp folders), the other roles' sessions, its own role's other transcripts, and sessions
started in a CatLog chat's scratchpad. A check of the first judging found no session that opened another session's
transcript: no tool call named a session folder or transcript, and the only session-folder paths in any result were
Claude Code's own notices of a large output saved in that session's folder (4 sessions).

**Reviews.** Two agents (blinding and fairness; selection, logic and report) reviewed the first design and found 22
problems, among them: the new judges would have shared the first judges' folders (their transcripts readable), a headline
that could only fall, a reverse check too small to bound CatLog, decoys that contradicted their own details, no rule for a
field-details conflict, and a report that could never finish after a refusal. The design was reworked; a second review
confirmed the fixes and found 14 more (decoys with a visible twin, a contradiction rule too broad, other roles' saved
outputs readable, the comparison mixing the agreeing sample with disputed values and needing the same papers on both
sides); all were fixed except three limitations the report now states: a record's shape shows its source, an agreeing
value shows as two claims (662 of the first judging's 750 sampled pairs did too), and regression to the mean in the
re-decided first errors (split by how the first judging decided them). Findings: the workflow journals of this chat
(`subagents/workflows/wf_94e2006f-82d`, `wf_c4261932-246`).

**Kit.** Commit 53c0964 on w1-eval: `score_randfull.py` (triage, next, report), the prompt, the run label `randfull`
(common_w1, run_adjudicate), `score_rand.py report --which/only/out` (the first report re-run byte-identical in
results.json), deny rules (run_adjudicate.adj_deny, claude_session.record_slugs), 78 tests pass.

**Drawn 6 Nov 16:30 (once).** 2,132 claims (plain 1,048, CatLog 908 real; 176 decoys: 76 x1000, 100 x60), 151 chunks,
144 papers, about 302 judge sessions and a third judge on splits; papers in a seeded order (records/score_randfull/private/
order.txt) so that a partial run is a random set of papers.

**Run (not started; the judges' account stood at 72% of its week, reset Nov 13).** After the old account's
reset (Nov 9, 10am Chicago), the owner signs the command line into the judges' account (`auth login` in a terminal tab,
choosing that account), then: test the account with a tiny call; in `~/Documents/kinetics-reading/code`:
`nohup python3 -B tools/w1/run_adjudicate.py --runs randfull --lanes 3 > ../records/randfull_judges1.console.txt 2>&1 &`
(or `python3 -B tools/w1/score_randfull.py next N` for the next papers, run with `--pmids ...`); then
`python3 -B tools/w1/w1_audit.py adjudication_randfull`, a content scan of every session for transcripts or first-judging
verdicts, and `python3 -B tools/w1/score_randfull.py report` (RESULTS.md, results.json, comparison.json and
first_on_same_papers/ in records/score_randfull/, to be copied here).
