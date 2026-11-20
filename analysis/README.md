# The paper's analysis code

The scripts that ran and scored the paper's two tests, computed its statistics and built its figures, Extended Data
items and tables. They read the catalogue frozen for the paper (the authors keep it as a git tag of their working
folder, with copies of its export; the main README's "Versions" names the tag) and the tests' records: every reading of
both sides, every judge's verdict and the audit of every session. The catalogue is not in this repository, and the
tests' records are in `../tests/` as tables (each side's values, every claim, verdict and planted error; not the
sessions' audits or transcripts) rather than the files these scripts read, so these scripts show how each result was
made; to run one again, it needs those inputs.

The scripts ran in two folders: the authors' working copy of CatLog, with its data (`<the CatLog folder>` here), and
the folder the tests ran in (`<the kit folder>`; its `code/` is CatLog's code on the tests' branch, with the tests'
kit in `code/tools/w1/`). `../sync_analysis.py` copies them:

- the kit (`tests/*.py` and `tests/prompts/`) as committed at f3e2a20, the commit the report of the test on 83 unread
  papers ran at (its results record it). The plain reading, judging and scoring of the test on 147 random papers ran
  earlier on the same branch (its report on 9 November, at commit 70e5f04); its scorer `score_randfull.py` is the same
  in both commits. The kit's later
  commits and uncommitted edits, made after both tests for a third test that was not run, are not here;
- the launch scripts (`tests/launch/`) from the kit folder's `records/`, as they ran there (not in git);
- every other script from the CatLog folder, as it stands there; the sync prints that folder's commit and any copied
  file that differs from it.

Fixed rules make these changes, and no other:
- the authors' folders read `<the CatLog folder>`, `<the kit folder>`, `<the first layout of the kit folder>` (where
  the kit ran before it moved), `<the earlier CatLog folder>` (CatLog's earlier system), `<the home folder>` and
  `<the scratch folder of the session that ran the sweep>`;
- a Claude Code session folder, named after its working folder, reads `-Users-<user>-Documents-...`;
- the made-up home folders of `tests/test_w1.py` read `/home/x` and `/home/s`, and session folders named after made-up
  homes `-home-x-` and `-home-y`;
- the ids of the authors' claude.ai connectors in the sessions' deny list (`tests/w1_setup.py`) read
  `mcp__<connector id>`;
- one reviewer's pronoun in `figures/fig1/build_fig1_v8.py` reads "their".

No person is named. Scripts that find their folder from their own place expect to stand where they came from (the
table "Where each file came from"), and the commands below are the ones that ran there: from the CatLog folder, or from
`<the kit folder>/code` for `tools/w1/`.

Besides `../requirements.txt` they use numpy, scipy, pandas, statsmodels, matplotlib, Pillow, cairosvg and fontTools
(where they ran: Python 3.12.12 with numpy 1.26.4, scipy 1.17.1, pandas 2.2.1, statsmodels 0.14.5, matplotlib 3.8.4,
Pillow 12.0.0, cairosvg 2.9.0 and fontTools 4.51.0), the Arial font, and open-source PyMOL 3.1.0 for Fig. 1's protein
picture. The tests' runners start Claude Code sessions (`claude -p`), which need a paid Claude plan or Anthropic API
access.

## What makes what

| Item | Script (in this folder) | Reads | Command, as it ran |
| --- | --- | --- | --- |
| Fig. 1 | `figures/fig1/build_fig1_v8.py`; `check_style_v8.py` checks the drawing; `structure/` renders the protein picture | the frozen catalogue's files and export, its counts (`catalogue_counts.py`), people's review as frozen (`freeze.py`), the rules (`count_rules.py`), the CatLog folder's code and notes, the AlphaFold model of the enzyme drawn | `python3 -I -B writing/fig1_v8/build_fig1_v8.py` |
| Fig. 2 | `figures/fig2/build_fig2_options.py` (version B is the figure), with `fig2_data.py` and `people_data.py` | both tests' results (`score_randfull.py`, `score_locked.py`), the count over both tests (`stats.py`), the known-trap summary (`summary.py`), the numbers of the test on 147 random papers (`r2_numbers.py`), people's review as frozen | `python3 -I -B writing/figures/fig2/build_fig2_options.py` |
| Fig. 3 | `figures/fig3/build_fig3_v2.py`, with `fig3_panels.py` and `factor_panel.py`; its data from `extract.py`, `extract_classes.py` and `database_errors/factor_counts.py` | the frozen export, publication years from PubMed, each value's database comparison, the agents' checks of values that differ from a database | `python3 -I -B writing/figures/fig3/extract.py --out writing/figures/fig3/v2/data`, then `writing/figures/fig3/v2/extract_classes.py`, `paper/figures/database_errors/factor_counts.py` and `writing/figures/fig3/v2/build_fig3_v2.py` |
| Fig. 4 | `figures/fig4/build_fig4_v2.py`; its data from `evidence/count_rules.py`, `build_learning.py` and `extract_cases.py`, on the list of kinds of error that `evidence/build_taxonomy.py` makes (with the earlier list in `r03_error_ledger.py`) | CatLog's log, catalogue, refused values and agents' work files, its git history and notes (when each error was found and each rule entered) | `python3 paper/figures/method_overview/v5/build_taxonomy.py`, the scripts of `writing/figures/fig4/v2/evidence/rules/`, `learning/` and `cases/`, then `python3 -I -B writing/figures/fig4/v2/final/build_fig4_v2.py` |
| Extended Data 3 | `figures/extended_data/known_traps/build.py` | the known-trap scores (`build_traps.py`) and each paper's checked key | `python3 -I -B writing/figures/extended_data/known_traps/build.py` |
| Extended Data 7 | `figures/extended_data/rules_reach/build.py` | Fig. 4's counts (it imports `build_fig4_v2.py`) | `python3 -I -B writing/figures/extended_data/rules_reach/build.py` |
| Extended Data 9 | `figures/extended_data/enzyextract_runs/build.py` | the second stage's results (`score_stage2.py`) | `python3 -I -B writing/figures/extended_data/enzyextract_runs/build.py` |
| Table 1a | test on 147 random papers: `tests/score_randfull.py` (its first judging: `score_rand.py`); test on 83 unread papers: `tests/score_locked.py` | both sides' readings, the judges' verdicts, the audits | `python3 -B tools/w1/score_randfull.py report`; `python3 -B tools/w1/score_locked.py report` |
| Table 1b | `statistics/accuracy_check/stats.py` | both tests' results | `python3 paper/evidence/accuracy_check_20261114/stats.py` |
| Table 1, footnote 5: what CatLog did with the plain reading's 57 wrong values | `statistics/accuracy_check/trace_code/match.py` | both tests' results, every CatLog reader file of those papers (kept and older copies), CatLog's catalogue, refused values and log | `python3 paper/evidence/accuracy_check_20261114/trace_code/match.py` |
| Table 1c | `tests/second_stage/score_stage2.py`; the page check of disputed values: `check_tasks.py`, then `score_checked.py` | the values both sides stored in the test on 83 unread papers, EnzyExtract's runs and its group's manual curation (the EnzyExtract paper's supplementary files), BRENDA 2026.1 | `python3 -B paper/evidence/locked_test_20261109/stage2/score_stage2.py check`, then `run` |
| Table 1d | `tests/known_traps/` (`summary.py` last) and `figures/fig4/evidence/build_traps.py`. The STRENDA DB row has no script of its own: it was counted from the database check of each value in the frozen export, which `catlog.py export` writes | the known-trap keys, every reading of those papers, the frozen export | `python3 paper/evidence/hard_cases_20261102/summary.py`; `python3 -I -B writing/figures/fig4/v2/evidence/traps/build_traps.py` |
| Supplementary Table 1 | `supplementary/build_supplementary.py`; its source from `statistics/accuracy_check/build_task_c.py` | both tests' wrong values and the judges' verdicts, and the plain cells agents wrote for Tables 1-4 (`plain_words.tsv`, not here; its text is in the Supplementary Tables) | `python3 paper/evidence/accuracy_check_20261114/build_task_c.py`, then `python3 -I -B writing/supplementary/build_supplementary.py` |
| Supplementary Tables 2 and 3 | `supplementary/build_supplementary.py`; their sources from Extended Data 3's `build.py` | as Extended Data 3 | as Supplementary Table 1 |
| Supplementary Table 4 | `supplementary/build_supplementary.py`; its source from Extended Data 7's `build.py` | as Extended Data 7 | as Supplementary Table 1 |
| Supplementary Table 5 and Supplementary Data 1 | `supplementary/agent_cases/build.py`, after `extract.py`, writes Supplementary Data 1 and Table 5's source; `supplementary/build_supplementary.py` makes Table 5 | the agent cases as CatLog's records hold them, each checked by agents, and the lines agents wrote and checked for each case (not here); journal and year from PubMed | `python3 -I -B paper/evidence/agent_highlights_20261028/case_data/extract.py`, then `build.py` there, then as Supplementary Table 1 |
| Table 1b, the 199-paper rows (without the 31 papers CatLog's side read again while a stopped launch's folders remained), and the Methods' rules for what counts as wrong, the judges' agreement and the bound on errors both readings share | `statistics/sensitivity/sensitivity.py` | both tests' results files, the sensitivity report of the test on 83 unread papers, the judges' verdict files and the kit's claim maps; `stats.py`'s functions | `python3 -I -B sensitivity.py` in `paper/evidence/sensitivity_20261117/` |
| Methods: the repeat launch of one batch of the test on 83 unread papers | `statistics/stability/stability.py` | the frozen copy's work files from both launches, its code (replayed on them in a scratch copy), the names and times of the files in its agents' scratch folders, the test's catalogue and log, EnzyExtract's curation | `python3 -I -B paper/evidence/stability_20261117/stability.py` |
| Results and Methods: the cost per paper and per value | `statistics/cost/cost.py` | both sides' session records and the kit's audits of them (tokens by kind, model, times), the results of the test on 83 unread papers | `python3 -I -B paper/evidence/cost_20261117/cost.py` |
| Results: each record's UniProt entry, EC number, organism and sequence against the databases and the STRENDA DB deposits | `statistics/linked_fields/linked_fields.py` | the frozen export and database table, the tag's own code and files (run from a `git archive` copy), the Swiss-Prot and UniProt reference files, the STRENDA DB snapshot | `python3 -I -B paper/evidence/linked_fields_20261117/linked_fields.py --scratch <a new folder>` |
| Headline numbers | `figures/fig1/catalogue_counts.py` (the catalogue's counts), `statistics/human_review_freeze/freeze.py` (people's review), `statistics/accuracy_check/stats.py` (both tests together), `figures/database_errors/factor_counts.py` (values that differ from a database), `statistics/europepmc_freeze/build.py` (the papers new to CatLog that the two Europe PMC searches found: papers read, their values, and those no database lists) with `reading_order.py` (which order each paper was read in, for the values per paper by order), `statistics/reprint_sweep/build.py` (the reprint sweep, repeated on the frozen catalogue), `statistics/power_simulation/power.py` (how often the paired interval excludes zero when there is no difference), `statistics/numbers/numbers_build.py` with `rederive/` (the numbers ledger of an earlier draft, each number with its definition and source; the text takes from its `numbers.json` the first reprint sweep's counts, and Supplementary Note 1 also those of the unit-header and Vmax sweeps). The counts of values no database lists, and Fig. 3f's table, come from `work/database_compare.json`, which CatLog's own `catlog.py export` writes (`tools/dbcompare.py`, in this repository) | the frozen catalogue and its records; for the Europe PMC part, CatLog's files at its tag `europepmc-freeze-20261116`, the papers CatLog's database table listed then and, for the reading order, the agents' transcripts | `python3 -I -B writing/fig1_v8/ref/catalogue_counts.py <the tag>` in a worktree of the tag; in `paper/evidence/europepmc_freeze_20261116/`, `python3 build.py --ref europepmc-freeze-20261116 --db-pmids db_pmids_at_freeze.txt.gz`, then `python3 reading_order.py`; the others as `python3 <script>` at their place (`numbers_build.py` reads CatLog's working tree, so a recount of the frozen catalogue runs it in a worktree of the tag) |

## The tests

`tests/*.py` and `tests/prompts/` are the kit as committed at f3e2a20 (above). `run_plain.py` runs the plain reading,
one Claude Code session per paper with `prompts/A0.txt`; `run_a6.py` runs CatLog's reading steps in a frozen copy of
CatLog; `run_adjudicate.py` runs the judges (`prompts/adjudicate.txt`, and `adjudicate_full.txt` with each record's full
details); `w1_audit.py`, `scan_reads.py` and `scan_judges.py` audit every session (its model, its tools and anything it
must not see); `score_rand.py`, `score_randfull.py` and `score_locked.py` score the tests with the shared rules of
`score_w1.py`; `common_w1.py`, `claude_session.py`, `h2h.py`, `h2h_common.py`, `h2h_s06.py`, `validate_plain.py`,
`w1_setup.py` and `build_people_list.py` are the shared code and the setup; `test_w1.py` tests them on made-up data. It
runs only in the kit folder, beside the branch's tools; as copied here, with paths replaced, it does not run (with this
repository's tools it stops at its imports). `launch/` holds the shell loops that ran the readings of the test on 83
unread papers and the judging of the test on 147 random papers in batches, `random_test/select.py` draws the papers of
the test on 147 random papers, and `known_traps/` scores the papers with a known trap. `run_reconcile.py` with
`prompts/A2_reconcile.txt` (a two-reading arm the kit was first built for) gave no result in the paper; `test_w1.py`
imports it.

The kit imports CatLog's own `units.py` and `human_review.py` as they are on its branch, not this repository's. That
`human_review.py` adds the files a reading agent in a copy of CatLog must not open, on which the audit of CatLog's
sessions in the copy builds (`w1_audit.py`, `FORBIDDEN_A6`). At f3e2a20 they read as follows; `FORBIDDEN` is the same
list as in this repository's `tools/human_review.py`:

```python
# A reading agent whose task names a CatLog folder other than the main one (a copy of it) also never opens the main
# folder's catalog, queue, log, work files or paper evidence (production reads and checked values of the same papers)
# or the other folders next to its own. Only for such agents: production agents use the main folder.
COPY_TASK = re.compile(r'/Documents/kinetics-reading/')
FORBIDDEN_COPY = re.compile(
    r'catlog-v2/(?:catalog\.jsonl|rejected\.jsonl|bounds\.jsonl|papers\.tsv|log\.tsv|work/|paper/)|'
    r'kinetics-reading/(?:records|out|checks|papers|code)\b')
FORBIDDEN_IN_COPY = re.compile(FORBIDDEN.pattern + '|' + FORBIDDEN_COPY.pattern)


def forbidden_for(task):
    """The forbidden-file pattern for a reading agent with this task text: FORBIDDEN, plus FORBIDDEN_COPY when the
    task names a CatLog copy."""
    return FORBIDDEN_IN_COPY if COPY_TASK.search(task or '') else FORBIDDEN
```

In the test on 83 unread papers, CatLog's side ran CatLog as frozen at tag `catlog-freeze-20261109` (commit
fb0cf1758951), in a copy of its folder. The kit sets every session it starts to claude-opus-5-5 at max effort
(`common_w1.py`: `MODEL`, `EFFORT`), and its audits check each session's model. The sessions ran on Claude Code 2.1.309
and, from 9 November, on a pinned copy of 2.1.317 (`CLI_VERSION`).

## Where each file came from

Paths under `<the CatLog folder>` unless the kit folder is named.

| Here | From |
| --- | --- |
| `tests/*.py` (same names) | `<the kit folder>/code/tools/w1/` at commit f3e2a20 |
| `tests/prompts/` | `<the kit folder>/code/tools/w1/prompts/` at commit f3e2a20 |
| `tests/launch/` | `<the kit folder>/records/` |
| `tests/second_stage/` | `paper/evidence/locked_test_20261109/stage2/` |
| `tests/random_test/` | `paper/evidence/random_papers_20261104/` |
| `tests/known_traps/` (with `today/`) | `paper/evidence/hard_cases_20261102/` |
| `statistics/accuracy_check/` (with `trace_code/`) | `paper/evidence/accuracy_check_20261114/` |
| `statistics/europepmc_freeze/` | `paper/evidence/europepmc_freeze_20261116/` |
| `statistics/power_simulation/power.py` | `paper/evidence/random_test2_20261112/work/` |
| `statistics/human_review_freeze/freeze.py` | `paper/evidence/human_review_freeze_20261116/` |
| `statistics/reprint_sweep/build.py` | `paper/evidence/reprint_sweep_20261116/` |
| `statistics/numbers/numbers_build.py` | `paper/manuscript/` |
| `statistics/numbers/rederive/` | `paper/evidence/rederive_20261101/` |
| `figures/lean.py` | `writing/figures/` |
| `figures/fig1/build_fig1_v8.py`, `check_style_v8.py` | `writing/fig1_v8/` |
| `figures/fig1/catalogue_counts.py` | `writing/fig1_v8/ref/` |
| `figures/fig1/structure/` | `writing/fig1_v8/structure/scripts/` |
| `figures/fig2/` | `writing/figures/fig2/` |
| `figures/fig3/build_fig3_v2.py`, `extract_classes.py` | `writing/figures/fig3/v2/` |
| `figures/fig3/extract.py`, `fig3_panels.py`, `factor_panel.py` | `writing/figures/fig3/` |
| `figures/database_errors/factor_counts.py` | `paper/figures/database_errors/` |
| `figures/fig4/build_fig4_v2.py` | `writing/figures/fig4/v2/final/` |
| `figures/fig4/evidence/count_rules.py`, `build_learning.py`, `extract_cases.py`, `build_traps.py` | `writing/figures/fig4/v2/evidence/rules/`, `learning/`, `cases/`, `traps/` |
| `figures/fig4/evidence/build_taxonomy.py` | `paper/figures/method_overview/v5/` |
| `figures/fig4/evidence/r03_error_ledger.py` | `paper/evidence/rethink_20261101/` |
| `figures/extended_data/known_traps/`, `rules_reach/`, `enzyextract_runs/` | `writing/figures/extended_data/` (the same folders) |
| `supplementary/` (the script and its three tables of column guides, column heads and verdict words) | `writing/supplementary/` |
| `supplementary/agent_cases/` | `paper/evidence/agent_highlights_20261028/case_data/` |

## Not here

Left out on purpose, besides the data (the catalogue, the tests' records, every agent's and judge's output):
- `plain_words.tsv`, the plain cells that agents wrote for Supplementary Tables 1-4 and `build_supplementary.py`
  reads: agent output, whose text is in the Supplementary Tables;
- the trace's `build.py`, which writes the trace table from quotes of the readers' and verifiers' notes: agents' notes;
- the scripts and judges' workflow of one person's blinded check of the 97 wrong values (Table 1, footnote 5): they
  belong with that person's sheet and answers;
- the task texts of the agents that checked disputed values on the page (between `check_tasks.py` and
  `score_checked.py`) and of those that read the known-trap papers' keys and scored their readings: like the one-off
  checks the main README names, they ran from task texts kept with the agents' logs, which the authors archive;
- the scripts of the third test, designed and not run (the kit's later commits, and the rest of
  `paper/evidence/random_test2_20261112/work/`), and `records/run_stage2_step.py`, written for a fuller second stage
  that was not run;
- earlier versions of the figures, the standalone dot form of Fig. 3g (`paper/figures/database_errors/build_years.py`),
  and the Illustrator steps that made the `.ai` and PDF files of the same drawings;
- the kit's copy of CatLog (`<the kit folder>/catlog-copy`, CatLog at tag `catlog-freeze-20261109`) and the rest of
  `<the kit folder>/code`: CatLog's own code, which this repository holds (the main README's "Versions").
