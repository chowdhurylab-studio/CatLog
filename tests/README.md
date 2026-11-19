# The paper's tests: registrations and records

Each test of CatLog in the paper that was registered has its plan here, exactly as committed before any result, with the
commits that registered and amended it and the time of its first result. Beside each plan are the test's records: both
sides' stored values, every claim the judges ruled on and every verdict, the planted errors, the papers and why any left,
the blinding keys, the scorers' reports and, for the EnzyExtract comparisons, the corrected scores. The scorers that
`analysis/` does not hold are here too.

| Folder | Test | Plan registered | Changed before the first result | First session or judge | First result committed |
| --- | --- | --- | --- | --- | --- |
| `locked_test/` | The locked test: held-out papers nothing had read, CatLog's frozen first pass against one plain reading by the same model, judged blind | 708f4b3, 10 Nov 2026 16:31:03 | 86d1eb5 (11 Nov 04:03:44), 91d6ad9 (10:27:24), 8bfc6be (11:58:30), each appended to the plan's record | 10 Nov 16:31:27 | ae74b6a, 11 Nov 12:56:20 |
| `locked_test_stage2/` | The locked test's second stage: CatLog, the plain reading and EnzyExtract's runs and database against EnzyExtract's manual curation on 79 of the papers | 41d125f, 11 Nov 14:36:53 | none (its scorer was committed at 4799407, 15:04:54) | no agent: code only | 53f737e, 11 Nov 15:08:00 |
| `locked_test_stage2/` | The second stage's page check of every disputed value (post hoc, its rules fixed before any verdict) | 0cf7f0d, 11 Nov 16:14:29 | 1e7f176 (16:15:37) | first verdict file 11 Nov 16:17:08 | 36bbe61, 12 Nov 09:00:30 (part 1); 78d823b, 10:00:07 (complete) |
| `enzyextract_broad/` | The broad test: CatLog's catalogue against EnzyExtract's released database on 300 papers both cover, every disputed value judged on its paper | cd4cbe0, 18 Nov 06:26:50 | 8316180 (06:28:50), c9df866 (06:31:21) | 18 Nov 07:02:03 | a6e44c5, 18 Nov 08:03:31 |
| `people_anchored/` | CatLog and EnzyExtract against values people checked in their papers | ce89e0a, 18 Nov 17:15:52 | none | no agent: code only | 9d09b67, 18 Nov 17:21:50 |
| `random_test/` | The random test: finished papers drawn at random, CatLog's catalogue against one plain reading, judged blind. **Not registered** | none (the re-judging's plan, f8b0afd, 6 Nov 16:31:28, came after the first judging's report) | none | 4 Nov 16:00:46 | 4e5ccaa, 6 Nov 12:58:10 (first judging); 3b59a97, 9 Nov 12:49:58 (re-judging) |

Commit ids and times are those of the authors' working repository, which is private; times are US Central (UTC−6),
from `git log` on each plan file. Each test's README gives the full ids, every commit that touched its plan and the git
blob id of the plan as published, so the files can be checked against that repository. The plans are byte for byte as
committed, except where a test's README lists a change. A session or judge time comes from the run's own records (the
kit's session records, the broad test's judge logs; for the page check, the time of its first verdict file).

## How the records were scrubbed

`../sync_tests.py` makes every file here except the READMEs, by fixed rules, and checks the result before it writes
anything:

- **EnzyExtract's data are not copied.** EnzyExtract's repository (github.com/ChemBioHTP/EnzyExtract) releases its data
  under CC BY-NC 4.0, the non-commercial term because of the publishers' text-mining licences, and the article (Wei et
  al., *Protein Science* 2025, e70251) names no licence for its supplementary `SI.zip`. Neither clearly allows the values
  in an MIT repository, so every EnzyExtract value is named by its file in `SI.zip` and its 0-based row as pandas reads
  the file (`TheData.parquet row 144184` is row 144184 of `dataset_crude_database/TheData.parquet`), with each file's
  sha256 in the test's README.
  Documents that printed EnzyExtract's cells name their rows instead (listed in the test's README).
- **No database values.** BRENDA, SABIO-RK, OED, SKiD and UniProt values carry their own licences. A test that scored
  a database reports its counts only, and the person-anchored reference (values of CatLog's earlier catalogue, built
  from those databases, that people then checked) is listed without its numbers.
- **No paper text beyond a printed line.** CatLog's quoted line stays when it has at most 25 words. A label field
  (enzyme, conditions, location, a judge's "found at") is blanked when more than 25 of its words are copied from the
  paper, counted in runs of 8 or more words of the paper's own text. A judge's reasoning is dropped when it shares any
  run of 8 words with the paper; the verdict stays.
- **No people.** No reviewer's name, and no time of anyone's review. Machine paths read `<the CatLog folder>`,
  `<the kit folder>` and `<the home folder>`, as in `analysis/`.
- **The scorers' JSON outputs are aggregates.** Every per-value list in them is replaced by a note; the per-value
  records are the TSV files beside them, whose columns are fixed.

The check, which must pass before anything is written: no name from the authors' private names file (in any case,
inside paths and identifiers too), no user name, e-mail address, home-folder path, key or `.env` value; no file over
5 MB; every `.py` compiles, `.json` parses and `.tsv` is rectangular; the paper-text rule on every free-text column
against its own paper's text, and no document holding a run of more than 25 words of any paper of its test; no
EnzyExtract or database value in a record; and no held-out paper outside the locked test's draw.

    python3 -B sync_tests.py --catlog <the CatLog folder> --kit <the kit folder> --names <private names file> [--ref REF] [--check]

## Not here

- **The papers.** Only their PubMed ids. The judges and readers read each paper's text, supplement and original file,
  which are their publishers'.
- **The third test** (a second random test of 600 papers), designed on 12 to 14 November and paused before it was
  registered or run. Its draft registration is not a registration, and it has no records. Its power simulation is in
  `analysis/statistics/power_simulation/`.
- **The judges' and readers' transcripts**, kept by the authors. Every session's audit (its model, its tools, anything it
  must not see) is summarised in the scorers' reports.
- **The code reviews and notes** written while the tests' kit was built (the locked test's `review/` folder), the
  writing notes, and the blind re-checks of the locked test's 34 values judged wrong (its post hoc investigation).
- **One person's blinded check** of the wrong values (Table 1, footnote 5), which belongs with that person's sheet.
- The person-anchored comparison's post hoc checks (an independent recount, a fairness check, sensitivity analyses) and
  the broad test's and second stage's independent recounts of their corrected scores: kept by the authors.
