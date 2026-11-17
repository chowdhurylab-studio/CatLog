# CatLog

CatLog is a catalogue of enzyme kinetic constants (kcat, Km and kcat/Km) in which every value is read from the
paper that measured it and checked against that paper. AI agents read and check the papers; code converts every
printed value into common units and checks the agents' work, so no model ever types a converted number. Each stored
value keeps where the paper prints it, the line that holds the number (copied word for word), and which models,
prompts and code version produced it.

This repository holds the code and the agents' instructions. The catalogue itself is at
<https://catlog.structf.studio>.

## How it works

| Step | Who | What | Where |
| --- | --- | --- | --- |
| Read | an agent | Reads one paper (its text, and page images where the text cannot be trusted) and writes every kcat, Km and kcat/Km the paper itself measured: the printed cell with its ± and unit as printed, the enzyme, organism, variant, substrate, conditions, where it is printed, and the line that holds the number, copied word for word. Values the paper prints only as a bound or as not detected are kept apart. | `prompts/read.md` |
| Convert | code | Converts each printed cell and unit to the catalogue units (kcat s⁻¹, Km mM, kcat/Km mM⁻¹ s⁻¹). | `tools/units.py` |
| Verify | a second agent | Checks each value against the paper (confirm, fix or reject, with a reason) without having written it, and lists values the reader missed; those are verified in turn. | `prompts/verify.md` |
| Check | code, before storing | The quoted line is in the paper's text and holds the printed number (for a cell the verifier confirmed on the page image because the text layer cannot be trusted, a failed quote test is a flag, not a refusal); the unit converts; the value is within physical limits; a printed kcat/Km is compared with kcat ÷ Km. CatLog holds one value per slot (paper, record identity, assay, place in the paper, constant and per-value note): a second value that agrees (within 2%, or equal at two significant figures) is a duplicate; one that differs is a conflict, refused and logged for a decision from the paper. Each value is stamped with the reader's and verifier's models, the hashes of the prompts and task text they followed, and the code commit. | `catlog.py add` |
| Flag and decide | agents, then code | Auditors try to refute a sample of stored values (mostly random; up to a third are values a database check called wrong); an error that may repeat sends the rest of that paper to a follow-up. Values that differ from BRENDA, SABIO-RK, OED, SKiD, STRENDA DB or UniProt by 1.5× or more go back to an agent with the paper. Sweeps look for tables whose printed units disagree with each other or with the paper's own rates, and for values reprinted from an earlier paper. Code applies every decision (`drop`, `unitfix`, `cellfix`, ...), and `tools/recheck.py` re-runs every code check on the whole catalogue. | `prompts/audit_standard.md`, `prompts/dbcheck.md`, `prompts/scale.md`, `prompts/vmax.md`, the workflows below |

Readers and verifiers read blind: their instructions forbid them to open database values, the catalogue's export,
the earlier catalogue and reviewers' verdicts. No file permission enforces this. `tools/human_review.py`
(`blind_check`) finds, in the agents' transcripts, every reader or verifier tool call that names a forbidden file and
records it in `human_review/exposed.tsv`; `python3 catlog.py review compare` reports those papers and the agreement
with reviewers sets them apart. The list does not name `catalog.jsonl`, `bounds.jsonl` or `rejected.jsonl`, so an
agent re-reading a paper can see its earlier values. The databases serve as a list of papers to read and as a
cross-check, never as a source of values.

### The agents

The agents run as Claude Code subagents, started by the saved workflows in `.claude/workflows/`:

- `catlog-batch` (read and verify), `catlog-audit`, `catlog-dbcheck`, `catlog-scale`, `catlog-vmax` and
  `catlog-nd-census` (a one-off census of not-detected values);
- `catlog-reprint-pairs` and `catlog-reprint-third-opinion` (the reprint sweep: a checker per suspect paper and
  refuters, then two judges where those split), `catlog-audit-followup` (the rest of a paper's values after an audit
  found an error that may repeat) and `catlog-unitcheck` (the unit of one table column, decided from the paper's own
  numbers). These four, and `tools/reread_copies.py`, ran from the authors' work folder and were never committed
  there; this copy takes them from disk;
- `catlog-chrome-lanes`: downloads in a person's own browser (see "Downloads in a browser").

Readers and verifiers run as Claude Code's default workflow agent. `.claude/agents/catlog-reader.md` is the lean
agent type of the scale, Vmax and n.d.-census checks (and of readers and verifiers only with `args.lean`). The
workflows set no model for a first attempt, so agents run on the session's model (the paper's values were read
mostly by Claude Opus 5.5, some by Claude Opus 5); an agent that returns nothing or reports a problem is retried once
on Sonnet.

The paper's readers and verifiers ran in the authors' working folder, where Claude Code loads the project's notes
(`CLAUDE.md`) into every agent, together with the user's own `~/.claude/CLAUDE.md` (the authors': rules for their own
computers and storage). Those notes are not in this repository, so agents started here do not see them; the
scientific rules are in `prompts/`.

`.claude/commands/` holds the `/batch` and `/audit` commands, written for the authors' Mac. `/batch` runs steps 2 to 6
below and also files downloads, runs an audit when one is due and fetches open-access supplements; some of its steps
point to the authors' notes, which are not included.

The workflows here are the saved, recurring ones and the sweeps that changed the catalogue. Some one-off checks the
paper's supplementary notes describe (the two agents that check a value a reviewer disputed, the check of values with
a not-detected cue, the checks of joined records, the checks of reviewer-approved values CatLog lacked) ran from task
texts kept only in the agents' logs, which the authors archive.

## What is here

- `catlog.py`: the command line (`python3 catlog.py` shows the status; its docstring lists the commands, and
  `unitfix`, `restore`, `audit-record` and `recover` are described at their functions).
- `tools/`: paper text (`fetch.py`, `jats_to_text.py`, `elsevier_to_text.py`), units (`units.py`), sequences and
  structures (`sequences.py`, `structures.py`, `enrich.py`, `ids.py`), the database comparison (`dbcompare.py`,
  `dbcheck.py` and the `*_values.py` importers), checks and sweeps (`recheck.py`, `scale_sweep.py`, `vmax_sweep.py`,
  `reprint_pairs.py`, `censored_scan.py`, `nd_census.py`, `reread_copies.py`), provenance (`provenance_backfill.py`),
  the human review (`human_review.py`), the website's data build (`site_release.py`, `export_site.py`, and
  `publication_years.py`, which serves only the website's comparison with BRENDA), the browser download lane
  (`lane_agent.py`) and tests (`test_*.py`).
- `prompts/`: the scientific rules the agents follow. `prompts/versions/` keeps every earlier prompt and task text
  that a value's stamp names (see "Versions").
- `config.json`: the queue's source lists and reading order.
- `.claude/settings.example.json`: permissions for the agents (see "Install").
- `sync_from_catlog.py`: how this copy is made (see the end).

Not here: the data (the catalogue, paper texts, agents' outputs, database downloads, reviews, and the hand-checked
tables and held-out lists in `sources/`), the website's own code, the authors' notes (`CLAUDE.md` and their guides),
the reviewers' review page (`tools/review_ui/`, so `catlog.py review pack` stops with a message), the authors'
machine helpers (Chrome and memory watchers, a website wording check), and the paper's analysis code (the tests'
scoring, the statistics and the figure builders), which the authors keep with the paper's evidence.

## Install

- macOS or Linux: `catlog.py` locks files with `fcntl`. Supplements in Word or RTF (`.doc`, `.docx`, `.rtf`) are read
  with macOS `textutil`; the browser download lane is written for the authors' Mac.
- Python 3.11 or newer (the authors ran 3.12): `pip install -r requirements.txt` installs the versions they ran.
  Text from PDFs needs poppler and PyMuPDF (PyMuPDF finds the symbol font that prints µ as 'm'; without it that
  warning is skipped silently). `enrich`, `export` and `dbdiff` need RDKit.
- Command-line tools: poppler (`pdftotext`, `pdftoppm`, `pdfinfo`), `tesseract` for scanned papers, `git`, and Java 8
  or newer for OPSIN (optional; `tools/ref_structures.py` downloads `opsin.jar`).
- The reference files the lookups read (about 200 MB, into `sources/ref/`): `python3 tools/ref_sequences.py` and
  `python3 tools/ref_structures.py`.
- [Claude Code](https://claude.com/claude-code) with workflows, opened in this folder, for the agent steps. Copy
  `.claude/settings.example.json` to `.claude/settings.json` so the agents can use shell, file and web tools without
  asking each time; it lets them run any shell command in this folder, so use it only where that is acceptable. It
  asks before destructive git commands.

Tested on macOS 26.3.1 (Apple silicon) with Python 3.12.12, and on the same Mac with Python 3.11 from a fresh clone;
poppler 25.10.0, tesseract 5.5.2, Java 1.8.0_402, git 2.50.1. Linux was not tested. In a fresh virtual environment
`pip install -r requirements.txt` takes about 20 seconds; the reference files take as long as their 200 MB download.
No special hardware is needed. The agent steps need Claude Code with a paid Claude plan or Anthropic API access; the
code checks, the demo and the tests need neither.

Data files are written into this folder and are git-ignored (`papers.tsv`, `catalog.jsonl`, `rejected.jsonl`,
`bounds.jsonl`, `log.tsv`, `texts/`, `work/`, `enrich/`, `sources/`, the exports); the folders are made on first use.

## Demo

    bash demo/run_demo.sh

It copies the code to a temporary folder and puts one made-up paper through the code checks, with no agent, API key
or network: the paper's text, a reader's file and a verifier's file (`demo/make_demo_paper.py`), then `catlog.py add`,
the refusal reasons, `catlog.py show` and `tools/recheck.py`. Of its nine values CatLog keeps six and refuses three:
one whose quote is not in the paper, one whose number is not in its quote, and a Ki read as a Km that the verifier
rejected. The run takes about a second; `demo/expected_output.txt` is the output to expect. The tests: `python3 -I -B
-m unittest discover -s tools -p 'test_*.py'` (about 8 seconds, offline).

## Settings

None is needed to start. Environment variables:

| Setting | Use |
| --- | --- |
| `CATLOG_CONTACT_EMAIL` | Your e-mail address: the contact in the User-Agent of every request (Europe PMC, UniProt, PubChem, ...) and the `email=` / `mailto=` of NCBI E-utilities, Crossref and OpenAlex requests (their polite pools). Set it before fetching papers or running lookups; left empty, no contact is sent. |
| `ELSEVIER_API_KEY`, `OPENALEX_API_KEY` | Optional API keys, in the environment or in a `.env` file in this folder (git-ignored). The Elsevier API returns full text only on a subscribing institution's network. |
| `REALKCAT_DIR` | Optional: the folder of the earlier CatLog system, for those who have it (its paper library in `config.json`, its `.env`, the earlier catalogue in `tools/coverage.py`, the old review store, and the website build). Unset, these parts are skipped or stop with a message. |
| `CATLOG_BULK_FASTA` | Optional: a UniProt FASTA file that seeds the sequence cache. |
| `CATLOG_ARCHIVER` | Optional: a script whose `pending()` lists agent logs not archived yet; `status` then shows them. |
| `CATLOG_CAMPUS_IP_PREFIX` | Optional, for the browser download lane: the start of your institution's public IP addresses. `catlog.py lanes-record` and `tools/lane_agent.py` count an address with this start as on the campus network; unset, none counts. |

The workflows cannot read the environment: pass `"root": "<this folder's absolute path>"` in their arguments (the
`/batch` and `/audit` commands do), or set `CATLOG_ROOT` at the top of each `.claude/workflows/*.js`. The four
workflows from the authors' work folder also take `"scratch"`, a folder for the agents' scratch files.

## Run one batch

1. Queue papers: write PMIDs, one per line, into a file that `config.json` lists under `"sources"` (for example
   `sources/fulltext_never_read.txt`), then `python3 catlog.py more 50`.
2. `python3 catlog.py next 10` claims up to 10 papers, gets their text into `texts/` (a local copy, open-access XML
   from Europe PMC, XML from the PMC text-mining collection, the Elsevier API, or an open PDF from OpenAlex or PubMed
   LinkOut, with OCR for scans) and prints their PMIDs. Papers no free route can supply are listed by
   `python3 catlog.py worklist`.
3. In Claude Code, run the saved workflow `catlog-batch` with
   `{"pmids": ["..."], "lanes": 5, "root": "<this folder's absolute path>"}`, or type `/batch`.
   Each paper gets a reader and then a verifier, which write `work/<PMID>.read.json` and `work/<PMID>.verify.json`.
4. `python3 catlog.py add <PMIDs>`: the code checks; accepted values go to `catalog.jsonl`, the rest to
   `rejected.jsonl` with the reason.
5. `python3 catlog.py enrich`, then `python3 catlog.py export`: `catlog_wide.jsonl` and `.csv`, one record per
   enzyme, variant, substrate and assay with up to three values, each value's database cross-check and provenance.
6. `python3 catlog.py dbdiff <PMIDs>` writes a paper-check task for each value that differs from a database; a later
   batch (or the `catlog-dbcheck` workflow) runs them, and `python3 catlog.py dbcheck-record` records the verdicts.

`/batch` first runs `python3 catlog.py file`, which moves files named `PMID<id>_*`, and PDFs from the last three days
that it can match to a waiting paper, from `~/Downloads` (and anything in `inbox/`) into `papers/`.
`python3 catlog.py review ingest` looks for reviewers' results files in `~/Downloads`, `~/Desktop` and `inbox/`.

## Checks

- `python3 tools/recheck.py` after `export` (exit 1 on any problem).
- `python3 catlog.py status`: values, records and papers, what waits, what is stuck.
- `/audit`: `python3 catlog.py sample`, the `catlog-audit` workflow, then
  `python3 catlog.py audit-record work/audit_*.json`.
- Tests that need no data: `python3 tools/test_blind_check.py`, `tools/test_dropped_relabel.py`,
  `tools/test_provenance.py`, `tools/test_provenance_backfill.py` and `tools/test_publication_years.py` (two of its
  tests need the authors' BRENDA comparison files and are skipped without them).

## Database cross-check (optional)

Put the downloads in `sources/` and run the importers, then `python3 tools/db_values.py`, which merges them into
`sources/db_values.tsv` (read by `export`, `dbdiff` and `tools/coverage.py`). Without it, `export` runs with an empty
database table.

| Input | Source | Read by |
| --- | --- | --- |
| `sources/brenda_2026_1.json.tar.gz` | BRENDA release 2026.1 (JSON) | `tools/brenda_values.py`; `python3 tools/brenda_count.py sources` writes `sources/brenda_pmids.tsv`, which `tools/coverage.py` and `tools/brenda_overlap.py` read |
| (fetched) | the SABIO-RK Export API, all entries (about 25 minutes) | `tools/sabio_values.py` |
| (fetched) | UniProtKB reviewed entries' kinetics | `tools/uniprot_values.py` |
| `sources/oed_export_<date>.csv` | an Open Enzyme Database export (the paper's: 7 October 2026) | `tools/db_values.py` |
| `sources/skid/Main_dataset_v1.xlsx`, `sources/skid/References.tar.gz` | SKiD | `tools/skid_values.py` |
| `sources/strenda/STRENDA_Claude_handoff.zip` | a snapshot of STRENDA DB's public datasets (7 October 2026) prepared for the authors | `tools/strenda_values.py` |

## Held-out papers

`catlog.locked()` keeps the papers listed in `sources/holdout_locked.txt` (the paper's locked test set) and
`sources/holdout_rand2.txt` out of `next`, the censored pass, `sample`, `dbdiff`, the sweeps and review packs. Neither
list is in this repository; without them nothing is held out.

## Data

The catalogue is at <https://catlog.structf.studio> and grows as papers are read. The counts in the paper are of a
frozen snapshot of 16 November 2026, kept by the authors (see "Versions"). `add` and `export` also read hand-checked
tables in `sources/` when they are there (natural forms of enzymes, organism-label corrections, values reviewed as
implausible as printed, database corrections); the authors keep them with the data. The reading order's growth and
reread mixes and `tools/coverage.py` use the earlier catalogue (`REALKCAT_DIR`). The website's own code is not
included; `tools/site_release.py` and `tools/export_site.py`, which turn the catalogue into the website's data files,
are, but they need the earlier system (`REALKCAT_DIR`).

## Versions

This copy is made from a commit of the authors' working repository, which each commit message here names. The
`pipeline_commit` stamped on each value names a commit of that repository, not of this one. The paper's counts come
from its tag `paper-catalog-freeze-20261116`; `sync_from_catlog.py --ref paper-catalog-freeze-20261116` makes this
copy as of that tag (the files that come from disk aside). The locked test's CatLog run used the tag
`catlog-freeze-20261109`; the rules here are written for later code and stop on that tag, so a copy of it needs rule
changes first.

Each value's `read_prompt`, `verify_prompt` and `task_prompt` stamp is the first 12 hex digits of the SHA-256 of the
text its agent followed. `python3 catlog.py prompt HASH` prints that text: from `prompts/versions/` (the texts saved
when values were stamped, and the ones rebuilt for values stamped before 21 October 2026), else from this repository's
history. In the texts that `prompts/versions/MANIFEST.tsv` marks `changed_here`, the authors' folder path became
`<the CatLog folder>`, so they no longer hash to their names; nothing else differs. `prompts/read.md` and
`prompts/verify.md` are copied byte for byte, so a value read with this version gets the same `read_prompt` and
`verify_prompt` as in the authors' folder; its `task_prompt` (`catlog-batch.js` and `catlog-reader.md`, which differ
here by `args.root`) is new.

## Downloads in a browser

`catlog-chrome-lanes` and `tools/lane_agent.py` download papers in a person's own Google Chrome (Claude in Chrome)
through their library's access, stopping a site at its first bot check. The workflow's instructions and page scripts
are written for the authors' institution (Iowa State University's library access and campus network) and for
publishers' sites as they were in late 2026: edit them before using them anywhere else, and check that your library's
licences allow it, since many publishers' licences restrict systematic downloading.

## Licence

MIT (`LICENSE`). It covers this code and its prompts. The catalogue's data are published on the CatLog website:
CatLog's reading is CC BY 4.0, structures keep their sources' terms, and quoted lines remain the publishers' text.

## How this copy is made

This repository is a code-only copy of the authors' working folder, made by `sync_from_catlog.py`:

    python3 -I -B sync_from_catlog.py /path/to/catlog --names <private names file> [--ref REF] [--check]

It copies only the files it lists, as committed in that folder, plus the files that folder keeps out of git: the four
workflows and one tool from its work folder, and the saved prompt and task texts. It makes every change by fixed
rules: the contact e-mail and machine paths become the settings above, the workflows take their folder from
`args.root`, people's names become neutral labels (Reviewer A, B, ...), and the reviewers' own review data stays out.
It checks the result before writing anything, and it refuses to write into this repository while the next commit
would carry a personal name or e-mail.
