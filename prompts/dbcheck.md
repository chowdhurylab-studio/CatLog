# Check database differences against one paper

CatLog read this paper blind: an AI reader, a separate AI verifier and code that converts every printed cell. Then code
compared CatLog's values with the enzyme databases (BRENDA, SABIO-RK, OED, SKiD, STRENDA, UniProt) for the same paper.
For each value in the task file, a database lists a number for the same paper, parameter, substrate and variant that
differs from CatLog's. You decide from the paper itself which number the paper supports and why the other differs.
You never change a value: `catlog.py dbcheck-record` checks your verdicts and records them in
`sources/database_corrections.tsv`, and the website then says, per value, what the check found.

Input: `work/dbcheck_<PMID>.task.json`. Output: write `work/dbcheck_<PMID>.json` and nothing else (page images go
under /tmp). Do not open other database files, the catalog or its exports (`sources/`, `catalog.jsonl`,
`catlog_wide.*`): the task file holds every database row you need, and the paper decides.

## The task file

- `text` (and `supplement` when it is not empty): the paper as text. `original_file`: the PDF or XML it came from
  (render a page with `pdftoppm -r 200 -f N -l N -png <file> /tmp/p<PMID>` and look at it when a table is garbled,
  an exponent, ± or unit prefix is unclear, or `glyph_warning` is set: that text layer prints µ as `m` or `l`, ± as
  `6`, a superscript minus as `21` or `)1`). In PDF text a µ often renders as `m`: check the unit prefix on the image
  whenever a factor of 1,000 is at stake. Relative paths are inside the CatLog folder your task names (the one
  holding work/ and texts/).
- `values`: one per CatLog value. `raw_value` / `raw_unit` are what CatLog read as printed (`unit_for_conversion`,
  when present, is the unit CatLog read the cell in instead of the printed one); `value` is CatLog's number in catalog
  units (`unit`: kcat s^-1, Km mM, kcat/Km mM^-1 s^-1); `location` and `quote` say where; `measurement` gives the same
  measurement's other printed values (kcat, Km or kcat/Km), for the paper's own arithmetic.
- `databases`: the database rows that differ, each with its `number` exactly as the database lists it, in the same
  catalog units, `times_catlog` (database ÷ CatLog), and the database's own label: substrate, organism, EC and comment
  (its mutant, conditions, entry id).
- `code_notes`: code's reading of the difference (`relation`: power_of_ten, time_factor, printed_unit_as_printed,
  printed_number_unit_not_applied, other_factor, under_1.5x; `closure`: whether the paper's own kcat ÷ Km agrees with
  its printed kcat/Km using CatLog's number or the database's; `pairing`). Hints only: check them against the paper.
- `recorded_before`: earlier checks of this value (for another database, or one an audit has since looked at).

## One verdict per value and database

For each value, give one verdict for each database in its `databases` list. Databases that list the same number for
it may share one verdict: name them all in `database` (`"BRENDA, OED"`).

- `corrected`: the paper prints CatLog's value (CatLog converted it correctly) and the database number is wrong.
  `cause`: one code from the table below, the one that describes how the database number came about. Only when a
  fact the paper prints decides it, and the evidence names that fact: the cell and its unit as printed, the paper's
  kcat ÷ Km against its printed kcat/Km, the same value in the text or in another table, a legend or sentence that
  gives the unit. A header's power of ten does not decide by itself which way it applies (`kcat × 10^-3 (s^-1)` over
  4.1 is read as 4,100 s^-1 and as 0.0041 s^-1): when the difference is such a factor and nothing else printed shows
  which reading is right, the verdict is `ambiguous`.
- `different_measurement`: the database number is another measurement the paper prints: another condition, pH,
  temperature, additive, cosubstrate, enzyme form, mutant, substrate or table; a number the paper reprints from
  earlier work; or a value the reader did not pair with this row. Not an error of either. `cause`:
  `different_measurement`; the evidence says where the paper prints the database's number.
- `catlog_wrong`: the paper shows CatLog's value is wrong (a misread cell, another row or column, a header factor or
  unit applied wrongly, a lost exponent). `cause`: `""` (the codes below describe database numbers, not CatLog's
  errors). Say in the evidence what the paper prints. Nothing is changed: the value goes first to the next
  independent audit.
- `ambiguous`: the paper cannot settle it (an illegible cell, two tables that disagree, a misprint either way, or
  a header's power of ten that only its convention decides). `cause`: `ambiguous`.

Cause codes (how the database number differs from what the paper prints):

| code | the database number is |
|---|---|
| `header_scale_inverted` | the cell with the table header's power of ten applied the wrong way round (× 10^3 where the paper means × 10^-3, or the reverse), where the paper's other printed numbers, such as its kcat ÷ Km, show which way is right |
| `header_scale_ignored` | the cell with the header's power of ten left out |
| `unit_not_converted` | the printed number with its printed unit not converted (M^-1 s^-1 taken as mM^-1 s^-1, nM as mM; µM/mM and time have their own codes) |
| `uM_entered_as_mM` | a µM number entered as mM (1,000× too high) |
| `mM_entered_as_uM` | a mM number entered as µM (1,000× too low) |
| `time_unit` | minutes, seconds or hours taken for one another: database ÷ CatLog is 60 or 3,600 (× 10^n for kcat/Km) |
| `decimal_or_exponent_slip` | the printed number with a decimal point or a power of ten off (a typo) |
| `value_from_other_row` | a number from another cell of the table (another row or column), listed under this value's label |
| `value_not_in_paper` | a number the paper prints nowhere, and no code above explains it |
| `paper_unit_misprint` | the printed number read in its printed unit, where the paper's own numbers show that unit is misprinted (its kcat ÷ Km closes only in another unit, or another table prints the same cell in another unit) and CatLog read the corrected unit |
| `recomputed_ratio` | a kcat/Km the database worked out from its own kcat and Km instead of the paper's printed kcat/Km |

Code checks each verdict: `paper_unit_misprint` needs the database number to be the printed value read in its
printed unit; `time_unit` needs a factor of 60 or 3,600 (× 10^n); `database_value` must be the database's number as the
task lists it; a `corrected` verdict cannot name CatLog's own number. When the database's label describes another
measurement than CatLog's value (another mutant, additive or substrate), that is `different_measurement`, never
`corrected`.

## Evidence

At most 240 characters of facts a reader can check in the paper, published on the website as written: where it is
printed, what is printed there (header and cell as printed), the arithmetic of the paper's own printed numbers when it
shows the point, and what the database lists. Every number exactly as the paper prints it or the database lists it.
No reasoning words (so, thus, therefore, hence, i.e., implies, means, likely, probably, presumably, apparently,
appears, seems, suggests, because, since, must, should, would, could, clearly, consistent, instead of, read as,
literally, matches, exactly), no arrows, no `I` or `we`, no internal words (row_id, triplet, task, catalog units,
verdict, v2). Examples:

- `Table 2 header 'kcat × 10^-3 (s^-1)' prints 4.1 ± 0.2 for wild type with NADPH; the same row prints Km 0.12 mM and kcat/Km 3.4 × 10^7 M^-1 s^-1 (4100/0.12 = 34000 per mM); BRENDA lists 0.0041 s^-1.`
- `Table II 'Km (µM)' prints 150 for H99N, penicillin G; SABIO-RK and OED list 150 mM.`
- `Table III kcat/Km header prints 'M^-1 s^-1'; H99N penicillin G prints kcat 0.28 s^-1, Km 150 µM, kcat/Km 0.0018 (0.28/150 = 0.0019 per µM); SABIO-RK lists 1.8e-06 mM^-1 s^-1.`
- `Results p. 5 prints kcat 60 ± 1 s^-1 with 500 mM NaCl; BRENDA 17 s^-1 is the Table 3 kcat without NaCl.`

Values of one paper often share one cause: check each anyway, one verdict per value and database.

## Output

```json
{"pmid": "<PMID>",
 "verdicts": [
  {"row_id": "<the value's row_id>", "metric": "kcat | Km | kcat/Km", "database": "BRENDA",
   "database_value": "<the number as the task lists it, with its unit>", "verdict": "corrected",
   "cause": "uM_entered_as_mM", "evidence": "<at most 240 characters>"}
 ]}
```

Write it to `work/dbcheck_<PMID>.json` and validate it:
`python3 -c "import json;json.load(open('work/dbcheck_<PMID>.json'))"`. Report the number of verdicts.
