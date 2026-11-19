---
description: Run one CatLog v2 batch (get → read → verify → add → enrich → export → database differences) and report one line
---
Run one batch in the CatLog folder (this repository). This command is the user's request
to run the saved workflows `catlog-batch`, `catlog-dbcheck` (when step 1 says so), `catlog-audit` (when step 6 applies)
and `catlog-corrigendum` (when step 5 lists Correction notices).

0. Agents: LANES = the user's number if they gave one (`/batch 12`, "use 10 agents": $ARGUMENTS), otherwise 5 (the user, 2026-11-09). No upper
   limit of ours (the workflow tool itself runs at most 9 at once on this 11-core Mac; extra lanes simply queue). Only
   if `memory_pressure -Q | tail -1` shows below 20% free, use 3 for this batch and say so in one line (a full-memory
   crash once killed the app); never stop for it. N = 2 × LANES papers.
   Disk: if `df -h .` shows under 15 GB free, start no batch. Say so in one line with the biggest
   folders (`du -sh ~/.claude/projects .`, read only) and wait
   for the user (2026-10-28: it fell to 14 GB; each paper's agents leave about 3 MB of transcripts).
1. First, if `python3 catlog.py status` says an audit is due, do the /audit steps (a stopped loop or a new chat
   catches up here; never ask the user). Then `python3 catlog.py file` (downloads from Codex/Chrome/the user land in ~/Downloads as PMID<id>_* or in inbox/;
   this files them so this batch can read them). Then `python3 catlog.py next N` prints up to N PMIDs, and
   `python3 catlog.py dbdiff --pending N` up to N papers whose database differences wait for a check (task files an
   earlier step 4 or `dbdiff --all` wrote), claimed for this batch: another chat or the scheduled task skips them for
   3 h, and the backlog goes N papers per batch. Pass only the PMIDs it prints. If `next` prints nothing: run the saved
   workflow `catlog-dbcheck` with `args = {"pmids": [those claimed PMIDs], "lanes": LANES, "root": "<this folder, absolute path>"}` when there are any, then
   `python3 catlog.py dbcheck-record`; run `python3 catlog.py status`, say why in one line, and stop.
2. Run the saved workflow `catlog-batch` with `args = {"pmids": [those PMIDs], "lanes": LANES, "dbcheck": [the claimed PMIDs], "root": "<this folder, absolute path>"}`
   (after its readers and verifiers it runs one `catlog-dbcheck` agent per claimed paper). No Workflow tool (a chat
   started before an account switch can lose it; ~/.claude/settings.json has `enableWorkflows: true` since 2026-10-11,
   so it comes back within minutes, also in a running chat, unless the account's organization forbids workflows):
   check it again next round; meanwhile start the same agents yourself with the Agent tool, LANES at a time, using the reader and
   verifier prompts in `.claude/workflows/catlog-batch.js` and the check prompt in `.claude/workflows/catlog-dbcheck.js` (read them once). If its result has a
   `stop` field (3 agents in a row returned nothing: the session usage limit), do step 3 with all the PMIDs, the ones
   it lists in `not_started` included (add puts papers without agent files back in the queue without counting a
   failure; a `reread` would count one), say the stop reason in one line and stop the loop here: do not
   start another batch until the user says the limit is back.
3. `python3 catlog.py add <the same PMIDs>` (all of them in one call). If 3 or more came back without agent files (the
   usage limit hit mid-round), add puts those back in the queue itself (finished reads kept, not counted as failures).
   A paper it still leaves as `reading` (one reader or verifier died, or its files are out of date):
   `python3 catlog.py reread <PMID> "<what add said>"` and carry on; never stop the loop for it.
   Then `python3 catlog.py dbcheck-record` (the database checks of step 2: usable verdicts go to
   sources/database_corrections.tsv, also those it lists under "evidence to look at" (a number the paper does not
   print, a ratio that does not hold: one agent's evidence, no second check); a value the check found wrong is never
   changed, `sample` puts it first for the next /audit; a value left unanswered or with a verdict it cannot use is
   asked again: it writes that paper's task file for a later batch's `dbdiff --pending N` itself, up to 2 checks per
   paper, then `dbdiff --all` takes it).
   Nothing to record is fine.
4. `python3 catlog.py supp 10` (open-access supplements for papers whose values are only in a supplement),
   then `python3 catlog.py enrich`, then `python3 catlog.py export`, then `python3 catlog.py dbdiff <the batch's PMIDs>`
   (task files for the papers with a value that differs from a database by 1.5x or more and no check on record; the
   next batch's step 2 checks them against the paper, so the site's "not yet resolved" lines settle by themselves).
5. `python3 catlog.py status` (for your own checks; no need to show it). If it lists Correction notices, check each
   pair now, unasked (the user, 2026-11-17: "The batch loop, unasked"; the authors' notes ("Correction notices"; not included here)): run the saved
   workflow `catlog-corrigendum` by scriptPath (`<this folder>/.claude/workflows/catlog-corrigendum.js`,
   args `{"article": "<ARTICLE>", "notice": "<NOTICE>", "root": "<this folder, absolute path>"}`), then `python3 tools/corrigendum.py ARTICLE NOTICE` (a dry run:
   read it), then the same with `--apply`, and do what it prints for values left waiting (a `reread` of the notice);
   say in one line what it dropped, fixed or left open, and the next step 4's export carries it. If its Human review line's "CatLog v2 has re-read N of these papers" went
   up, run `python3 catlog.py review compare` and the authors' notes ("Learning from it"; not included here). Show progress to the user only when status
   says it is time (about every 50 agents), when the loop stops, or when they ask: then run `python3 catlog.py report`
   and paste its output as is (markdown, not in a code block). Otherwise the batch reply is a few words. Status is the only counter.
6. If status says an audit is due (300 or more values since the last one), do the /audit steps now, also when
   the loop is about to stop.
7. If this batch added no values, or status says "no progress", work through the authors' notes ("When nothing moves"; not included here) before
   the next batch, and say in one line what was stuck and what you changed.
8. Every 10th batch and when the loop stops, back up the data files (catalog.jsonl, rejected.jsonl, bounds.jsonl,
   papers.tsv, log.tsv, human_review/): this repository git-ignores them, so never `git add -f` them here; keep
   them in a separate private repository or backup.

Keep going. If many rows are rejected for the same CODE reason (a unit that does not convert, a quote check), that is
a bug: fix it as the authors' notes ("Improving as you go"; not included here) say, `reread` the affected papers, and continue. Verifier rejects
of one paper (retracted, reprinted values) are normal. Stop and ask the user only if the same problem keeps coming
back after your fix.
