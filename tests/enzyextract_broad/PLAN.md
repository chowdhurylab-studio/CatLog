# Broad test: CatLog against EnzyExtract's released database (plan, registered 18 November 2026)

## Status
- **Registered.** The owner said yes on 18 November 2026 ("yeah run"). This plan is committed before any judge
  reads a sampled paper, and that commit's time is the record.
- **Done before this plan, and known:**
  - the frame, the order and each frame paper's agreement counts (`frame.tsv`, made by code; no value of a sampled
    paper has been judged);
  - a pilot on 5 papers that are not in the frame (`pilot/`).
- Separate from the locked test and its two stages, which stand as reported.

## Question
On papers both cover, which holds more of the kinetic values the papers report, and fewer wrong ones: CatLog's
catalogue or EnzyExtract's released database?

## Sources
| Source | What is compared |
|---|---|
| CatLog | Its stored kcat, Km and kcat/Km at the paper's freeze: tag `paper-catalog-freeze-20261116`, `catalog.jsonl`, with records from that tag's export. |
| EnzyExtract | Its released database, the SI file `dataset_crude_database/TheData.parquet` (sha256 903023a9…). The article calls it "the raw output from the EnzyExtract pipeline", made with its fine-tuned model. |

Why the database and not a run of our own is in `ASSESSMENT.md`, section 2.
- The full pipeline's fine-tuned model can be called only from its authors' account.
- New fine-tuning jobs are closed to new OpenAI accounts.
- The GPT-4o snapshot that matched the full pipeline is retired.

## Papers
- **Frame** (`frame.tsv`, 3,245 papers): catalogue papers that meet all of these.
  - Status `done` or `no_kinetics` at the tag.
  - Covered by the database, by PMID or by DOI through `papers.tsv`.
  - CatLog's text and an original file (PDF or publisher XML) on disk.
- **Left out of the frame:** every paper that one of these used.
  - The locked test's held-out papers.
  - EnzyExtract's 384-paper benchmark and its 52 fine-tuning papers.
  - The Co-Scientist gold set.
  - The test kit's development, held-out and people lists.
  - The random test and the hard cases.
  - Papers whose CatLog values people reviewed (`human_review/first_compare.tsv` at the tag).
  - The pilot.

  `frame_summary.json` gives the count for each.
- **Order** (`order.txt`): the frame sorted by PMID, then shuffled with Python's `random.Random(20261118)`.
- **Sample:** the first 300 papers of the order that are analysed.
  - A paper is analysed when every value it has to judge has a verdict, or when it has none to judge.
  - A paper whose judge cannot finish (two refusals, or a source that will not open) is replaced by the next paper in
    the order. Every replacement is listed with its reason.

## Values
- **CatLog:** stored kcat, Km and kcat/Km values in catalogue units, on records that hold a kcat.
  - The database keeps only rows with a kcat, so records without one are out on both sides.
  - Never in scope: a Km over a mass concentration, a derived kcat/Km, or a censored value.
- **EnzyExtract:** every kcat, km and kcat_km cell, converted from its printed string with CatLog's units code, as
  stage 2 converted every EnzyExtract run (`parse_value_unit` in `paper/evidence/h2h_20261101/common.py`).
  - If that code cannot read a string, it is read again after `ee_clean` rewrites the notation. The rewrites cover
    `(a ± b) × 10^n`, a lost caret, a thousands comma, and `m^-1 s^-1` or `L mol^-1` for kcat/Km.
  - If it is still unread, the database's own number is used (`kcat_value`, `km_value`).
  - Cells still unread (bounds, ND, percentages, per-mass activities, numbers with no unit) are counted, not scored.
- **Exact repeats** (same paper, metric, value and labels) are dropped on both sides, as in stage 2's rule 1.
- **Matching:** per paper and metric, one to one, within 1.5% (the head-to-head's matcher). A matched pair is agreed and
  taken as right. Every other value is disputed.

## Judging
- **Every disputed value** is judged on its paper by one agent, using `judge_prompt.md` verbatim.
  - The model is claude-fable-5-2. It judged stage 2 and made none of CatLog's values.
  - The agent sees two readings, A and B, in an order seeded per paper. Each reading's full list for the paper is shown,
    and no source is named.
  - It gives one of nine verdicts: stage 2's, with bounds and not-detected entries named under `not_this_metric`.
- **What the agent reads:** only the paper's folder.
  - CatLog's text of the paper.
  - The original PDF, read as page images, and/or the publisher XML.
  - The supplement's text, if there is one.
- **Large papers:** a paper with more than 150 values to judge is split into parts of at most 150. Each part gets its
  own agent, which sees both full lists.
- **Second agent:** a seeded 10% of the papers with a dispute get a second agent. Agreement is reported; the first
  agent's verdicts are the ones scored.
- **Launch:** every judge is its own headless Claude Code session (`run_judges.py`, 5 at a time, from `jobs.json`).
  - It starts in its paper's folder under `/private/tmp/pages_check_20261118/`. That folder names neither source and is
    not a git checkout, so no commit subject reaches the judge.
  - It uses a clone of the app's Claude Code 2.1.325 (`kinetics-reading/cli/2.1.325`), kept beside the kit's 2.1.317
    clone so no app update can remove it mid-run, and the kit's isolation: no git context, no memory, no CLAUDE.md
    files, MCP off, and project settings only.
  - The model is pinned with no fallback: `--model claude-fable-5-2 --effort high`.
  - Permissions are `--permission-mode dontAsk`.
    - Allowed: Read, Write, Glob, Grep, and the shell commands pdftoppm, pdftotext, mktemp, ls and mkdir.
    - Denied: web tools, sub-agents, python, git, find and cat.
    - Unreadable: `~/Documents`, `~/Downloads`, `~/Library`, `~/.claude` and this session's scratch folders.
  - Each session gets its own temporary folder for page images.
  - A session stopped by the account's usage limit is not a try: it runs again after a 20-minute wait.
  - A session whose replies came from another model counts as a failed try.
  - After two failed tries, the paper is replaced as under "Papers". `run_judges.py` does this and records it in
    `run/sample.json`.
  - The first job runs alone, so a broken launch stops before the rest.
  - Six failed jobs in a row stop new starts. More than 20 failed papers replace nothing and stop the run, for a
    decision.
- **Amended before any judge ran** (18 November, 06:28 and 06:35): launch changes only, none touching a rule.
  - The tool is 2.1.325 instead of the kit's 2.1.317, which does not know claude-fable-5-2.
  - Two stops for repeated failures were added.
  - The run starts with a tiny call on the judges' account in their clean environment, and waits while the account
    is at its limit.
  - It runs detached from any chat, with its process ID in `run/runner.pid`. It resumes from the verdicts already
    copied to `run/judged/`, so a wiped `/private/tmp` loses none.
  - A refusal, a timeout, or a session that ends without a full check file is a try.
  - A dropped connection or a server error is not a try. The session waits 5 minutes and runs again, at most 6 times
    per job.

## Registered inputs (sha256)
| File | What it is | sha256 |
|---|---|---|
| `frame.tsv` | the frame, 3,245 papers | `752405e7ec15db19473a2c7f9bd77a704643f376338e83da3d5bad71004dce44` |
| `order.txt` | the seeded order of the frame | `0ab14f13aa47ad1d21bac5ac1c242706ee2e67758e2eb948d7e00ffbc240874d` |
| `run/sample_300.txt` | the sample: the first 300 papers of the order | `272a877e977a457f6251a0ccc2fccdc03ccbd1626f927f1182322604e412ab45` |
| `judge_prompt.md` | the judge's prompt | `c6247c778a30f45204780d6cc0eb05040492c85adc901f6bdabae2215bdb1048` |
| `run/key.json` | which reading is whose, per paper | `8d8e1e7d4fa24d05be0f7175a159fd32feb9a68213c9e5d10cf15020ea0ed1d0` |
| `run/jobs.json` | every judge's filled prompt (216 sessions) | `3ce666e52ebae605fa3d3be21a5e7f2cd2db747849a13cf85a6ae164e7ffc14d` |
| `build.py` | frame, tasks and the scorer | `eaf2a20c61b90df203877d3bd7c39351fe9c068f30dbc8a0991c3dc449321643` |
| `run_judges.py` | the launch | `56bf8415f8dfec76ad625e100d2ecf14c9f9a22a13d9e4194d5bdb89c9c5881e` |

## Verdicts and rules
| Class | Verdicts |
|---|---|
| Right | measured here at this scale; a misprint, under the view's convention |
| Wrong number | measured here at another scale; not this metric; not found in the paper |
| Printed here, measured elsewhere | credited to earlier work |
| Listed twice | repeat of one printed value |
| Undecided | cannot decide: left out of every count and reported |

| Rule | Counts as right | Counts neither way |
|---|---|---|
| **Printed here** (primary, the more lenient to EnzyExtract) | measured here; credited to earlier work | repeats |
| Measured here (secondary, stage 2's rule) | measured here only | nothing |

**Misprints:** the primary view counts a value as printed as right (`as_printed_but_misprint`), the convention of
EnzyExtract and its curation. The secondary view counts the corrected value as right (`corrected_misprint`).

## Endpoints
**Primary.** All three are reported whichever way they fall, each at the 5% level with no adjustment, as in stage 2.
1. **Papers holding a wrong number.** Per paper: does each source hold at least one value judged at another scale,
   not this metric, or not in the paper? The exact two-sided sign test is run on the papers where only one source does.
   A difference is claimed at P < 0.05.
2. **Recall, CatLog minus EnzyExtract,** under the primary rule.
   - The reference, per paper: each agreed value once, plus every disputed value judged right.
   - Recall is the share of the reference a source holds.
   - The interval is a paired paper bootstrap, 95%, B 10,000, seed 20261031. A difference is claimed only if the
     interval excludes zero.
3. **Precision, CatLog minus EnzyExtract,** the same way. Precision is the share of a source's values that are right;
   repeats are left out under the primary rule.

**Secondary:**
- the measured-here rule;
- misprints counted as corrected;
- kcat, Km and kcat/Km apart;
- the verdict counts of each source;
- papers with a PDF against papers with XML only;
- the second agent's agreement;
- EnzyExtract values read through `ee_clean` or the database's number, with their verdicts.

## Fixed from the commit on
- The frame, the order, the seed, the sample size and the replacement rule.
- The scope, the conversion, the matcher, the prompt, the rules and the endpoints.
- The scorer (`build.py score`, run on the pilot before this commit).
- The launch (`run_judges.py`).

A bug found later is fixed and stated, and the step it touched is run again.

## How many papers
`power.py` resamples stage 2's 79 checked papers to size N.

| Scenario | Size | Sign test decides | Recall interval excludes zero | Precision interval excludes zero |
|---|---|---|---|---|
| As stage 2 saw it | 300 | 100% | 98% | 100% |
| EnzyExtract's wrong papers halved, and CatLog given a wrong number in 3% of papers | 300 | 96% | 62% | 100% |

- Under the measured-here rule, recall decides in 100% of simulated tests at every size from 100 papers up.
- Under the primary rule, recall is the weak endpoint. It can fail to decide if EnzyExtract's errors are rarer here
  than in its benchmark, and that is reported as it falls.
- The intervals' half-widths at 300 papers are about ±0.045 for recall and ±0.038 for precision.

## Limits stated now
- **The judges are Claude models,** as are CatLog's readers and verifiers. EnzyExtract's model is OpenAI's. No person
  checks the verdicts.
- **Agreed values are not checked.** A mistake both sources make stays in the reference. A value both miss is not seen,
  so recall is relative to what either source holds.
- **Different copies of the papers.** The database was made from EnzyExtract's own copies: Elsevier and Wiley TDM,
  and OpenAlex open access. A value read from a version or supplement that we lack is judged on our copy, and may count
  as not in the paper. Those values are listed.
- **Only records with a kcat are compared.**
- **A released product, not a run made for this test.** The models and their dates differ: a 2024 fine-tuned
  GPT-4o-mini for EnzyExtract, and Claude Opus 5.5-era agents for CatLog.
- **CatLog's values are what its catalogue holds**, including its later automatic checks (audits, database checks,
  sweeps). Papers people reviewed are left out.
- **The sample is of papers both cover and CatLog finished.** It says nothing about papers only one source covers.

## Cost and time
- **Scale:** the first 300 papers of the order hold 4,476 values to judge, in 191 papers; the largest has 422. With
  second agents and parts that comes to about 215 agents.
- **Cost:** about $600 to $850 at Fable 5.2's list prices, run on the subscription. Stage 2's judges cost $4.13 per
  checked paper all in; the pilot's two judges cost $1.68 and $1.24, on text-only papers.
- **Time:** stage 2's agents took a median of 3 minutes. That is a few hours at 5 agents live, or a day or two with
  the account's usage limit.
- No API spend and nothing on Nova.

## Files
| File | What it is |
|---|---|
| `build.py` | `extract`, `frame`, `tasks`, `score` |
| `run_judges.py` | runs the judges and the replacements |
| `judge_prompt.md` | the judge's prompt |
| `frame.tsv`, `order.txt`, `frame_summary.json` | the frame, the order and their counts |
| `ee_finetune_train_pmids.txt` | EnzyExtract's 52 fine-tuning PMIDs, from its repository |
| `power.py`, `power_results.json` | the sample-size simulation |
| `pilot/` | the pilot's key, tasks, verdicts and scores |

Not in git:
- `work/enzyextract_broad_20261118/thedata.tsv` and `frame_values.json.gz`, which `build.py` rebuilds;
- the judges' paper folders, which are copies of the papers.
