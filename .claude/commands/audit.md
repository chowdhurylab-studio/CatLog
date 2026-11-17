---
description: Independent audit of a random 7% of the values added since the last audit (at least 12 rows) against the papers (old audit standard); drops what fails
---
In the CatLog folder (this repository). This command is the user's request to run the saved workflow `catlog-audit`.

1. `python3 catlog.py sample` → JSON list of unaudited rows on stdout: 7% of the values added since the last audit, at
   least 12 (`status` says how many); the same rows go to
   `work/audit_rows_current.json` and their row_id groups are printed on stderr.
2. Run the saved workflow `catlog-audit` with `args = {"groups": <those groups>, "root": "<this folder, absolute path>"}` (args.lanes auditors live, default 6): the auditors read
   their rows from that file, so the launch carries row_ids only. `args = {"rows": <the list>, "root": "<this folder, absolute path>"}` still works, for rows
   that are not the ones on disk.
   No Workflow tool (switched off on some accounts): start the same auditors yourself with the Agent tool, one per
   4 rows, at most 3 live, with the prompt in `.claude/workflows/catlog-audit.js`; each writes
   `work/audit_<first row_id>.json`.
3. Record the verdicts: `python3 catlog.py audit-record work/audit_*.json` (both modes: it reads every verdict file,
   records each verdict and sets the file aside). A drop moves the row to rejected.jsonl. A kept value a database
   check had called wrong opens that difference again (it writes the paper's dbcheck task file). When the drop reason is a
   unit the paper itself shows is misprinted (another table prints the same cell in the right unit, or the column's
   kcat/Km closes only in that unit), correct instead of dropping, for that row and the same column's siblings:
   `python3 catlog.py unitfix <unit> "<where the paper shows it>" <row_id> ...` (keeps the printed value; a row
   already dropped comes back). In workflow mode run a
   `record` line of its output only for a row_id audit-record did not record (its auditor wrote no file): running
   both records a verdict twice.
4. `python3 catlog.py status`, then report one line: audited, kept, dropped, the drop reasons. Targeted rows (up to a
   third of a sample: values a database check found wrong, `work/audit_priority.txt`) are reported apart: audit-record
   ends their log lines `targeted=dbcheck` and the audit rate (status, the site) leaves them out. Auditing the rest of a
   paper's rows after a sample found a systematic error there is a follow-up: record it with
   `python3 catlog.py audit-record --followup work/audit_*.json` (lines end `targeted=paper`, also out of the rate).
5. If 2 or more of 12 drop for the same kind of reason, fix the cause in `prompts/read.md`, `prompts/verify.md`
   or the checks in `catlog.py` (never by editing rows), commit, and say what changed.
6. Completeness (sampling accepted rows cannot show an omitted table): pick one random `done` paper with values, never
   one in `sources/holdout_locked.txt` (the method paper's test set, `catlog.locked()`). One
   agent lists every measured kcat, Km and kcat/Km the paper prints (tables, text, figures with printed numbers,
   supplement) and compares with that paper's rows in catalog.jsonl and rejected.jsonl, reading blind like a reader
   (prompts/read.md "Read blind": no database values, catlog_wide, earlier-catalog or review files). Report what is missing; if
   values were missed, `python3 catlog.py reread <PMID> "completeness audit: <what>"` and look for the cause.
