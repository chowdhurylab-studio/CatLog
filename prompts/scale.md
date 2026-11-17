# Check a table whose kcat/Km misses kcat ÷ Km by a unit factor

CatLog stores enzyme kinetics read from papers: an AI reader copies each printed cell and its unit, a separate AI
verifier checks it, and code converts it (kcat s^-1, Km mM, kcat/Km mM^-1 s^-1). In the table named in your task, the
paper prints kcat, Km and kcat/Km for each measurement, and the printed kcat/Km misses kcat ÷ Km by an exact unit
factor (1,000, 10^6, 60, 60,000, ...) for most of its rows. A misprinted unit header does this: one column's header
names the wrong unit, so code stored the whole column off by that factor (15659684 Table 3: kcat/Km headed
mM^-1 min^-1, really µM^-1 min^-1; 25022854 Table 1: kcat/Km headed 10^3 M^-1 min^-1, really 10^6). Closure alone
shows that the three columns disagree, not which column is wrong: you decide that from the paper.

Input: `work/scale_<PMID>.task.json`. Output: `work/scale_<PMID>.json` and nothing else (page images go under /tmp).

## Read blind

Use only the paper's own files: `text`, `supplement`, the `original_file` (PDF or XML) and page images you render from
it (`pdftoppm -r 200 -f N -l N -png <file> /tmp/s<PMID>`). Never open database values or exports (`sources/`,
`catlog_wide.*`, `work/scale_sweep.tsv`, `work/dbcheck_*`, `work/old/`), the earlier catalog (anything under realkcat
except the original file you are given) or `human_review/`.

Read every number, unit prefix (µ vs m), exponent and header multiplier of the table on the rendered page image, never
on the text layer alone: PDF text often prints µ as `m` or `l`, drops a superscript minus or loses a header's
`× 10^3`. If `glyph_warning` is true, the text layer is known to be damaged.

## Find which column is wrong

`rows` holds every catalog row of the paper (`raw_value` / `raw_unit` as the reader copied them;
`unit_for_conversion`, when set, is the unit code converted with instead; `value` / `unit` the stored number).
`flagged` lists the measurements whose stored values miss closure, with their row_ids (kcat/Km, kcat, Km) and
`closure_factor` = stored kcat/Km ÷ (stored kcat ÷ stored Km).

A table whose `state` is `fixed:reader(<metrics>)` already closes: the reader or verifier converted those metrics with
another unit than the printed header (`unit_for_conversion`), so `closure_factor` is about 1 and `printed_factor` is
the miss of the headers as printed. That reader chose one column as the misprinted one, from closure alone; nobody
checked the choice (42228390: the verifier re-read kcat/Km, while kcat and Km were the misprinted headers). Check every
column with step 2 as if nothing had been converted: `keep` the reader's unit only when a printed fact shows that
column is the misprinted one, `unitfix` another column (and the reader's column back to its printed unit) when the
facts show that instead, `ambiguous` when nothing decides.

1. Copy the table's headers and cells from the page image. Did the reader copy every header unit and multiplier as
   printed? A multiplier or prefix the reader dropped or misread is a reader error, not a misprint: say so.
2. Test each column against facts the paper prints elsewhere, and write the arithmetic down:
   - kcat = Vmax ÷ [E]: a printed Vmax (µmol/min/mg × molecular mass, or µM/min ÷ the enzyme concentration in
     Methods) in the same table, another table or the text;
   - Km against the substrate concentrations of Methods or a figure's x-axis (a saturation curve reaching
     Vmax/2 near the Km; a Km far outside the range tested is suspect), and against any Km the text quotes;
   - the same value printed again in the abstract, Results, Discussion, another table or the supplement, in a unit;
   - limits: kcat/Km above ~10^9-10^10 M^-1 s^-1 (diffusion) or a Km unit that makes the table absurd.
   Check every column, not only the one closure points at: 42228390 Table 2 had kcat (s^-1, really min^-1) and Km
   (µM, really mM) both misprinted, and its kcat/Km closed in the wrong units.
3. Decide per column: printed unit right, or misprinted and what it really is. A column is misprinted only when a
   fact in step 2 shows it (or the header is not a possible unit for that parameter, e.g. kcat/Km headed `µM s^-1`)
   AND the corrected unit makes the table close. Closure alone never decides between two columns: if the paper gives
   nothing else, the verdict is `ambiguous` and nothing changes.
4. A lone row that misses closure while the rest of its column closes is a cell typo or a misread, not a header
   misprint: say which cell and how the paper shows it.

## One action per row

For every row of the flagged table(s) (all rows of that column in that table, flagged or not, so the column stays
consistent; for a `fixed:reader` table, all rows of its three columns) give one action:

- `unitfix`: the printed unit is misprinted (or the reader copied it wrongly) and `unit` is the unit the paper's own
  facts show; or a reader's `unit_for_conversion` is wrong and `unit` is the printed unit (or the right one). Spell
  `unit` so code converts it, and test it on the row's raw_value:
  `cd <the CatLog folder> && python3 -c "import sys; sys.path.insert(0,'tools'); from units import normalize; print(normalize('kcat/Km', '13.3 ± 0.6', 'mM^-1 s^-1'))"`
  (metric `kcat`, `Km` or `kcat/Km`; it prints value, catalog unit, error). Spellings that work: `s^-1`, `min^-1`,
  `uM`, `mM`, `mM^-1 s^-1`, `uM^-1 min^-1`, `10^6 M^-1 min^-1`, `10^3 M^-1 s^-1`.
- `keep`: the stored value is right as it stands (its column is not the misprinted one, or the paper's own numbers
  disagree for a reason it prints, such as kcat/Km from a separate fit).
- `drop`: the stored value is wrong and no unit fixes it (the cell is another row's, the metric is not kcat, Km or
  kcat/Km, the number is misread).
- `ambiguous`: the paper cannot settle it. Nothing changes.

`evidence` (at most 300 characters, the same for rows that share it): facts a reader can check in the paper, every
number as printed: the header and cell, the arithmetic of the paper's own numbers (`Vmax 0.43 µmol/min/mg × 52 kDa
= 0.37 s^-1 = Table 2 kcat 0.37`), the Methods range or figure axis. No reasoning words (so, thus, therefore,
because, since, must, likely, probably, clearly, suggests, implies, means), no `I` or `we`, no row_ids. Examples:

- `Table 2 header 'kcat/KM (M^-1 s^-1)'; every row prints kcat (s^-1) ÷ KM (mM): guanine 2.8/0.21 = 13.3, printed 13.3 ± 0.6; Methods vary guanine 0.01-2 mM; Results text: kcat/KM 1.3 × 10^4 M^-1 s^-1 for guanine.`
- `Table 1 header 'kcat (s^-1)'; Vmax column 12.4 µmol/min/mg × 58 kDa = 12.0 s^-1 = 720 min^-1; kcat cells 720 ± 30; Fig. 3 y-axis 'kcat (min^-1)'.`

## Output

```json
{"pmid": "<PMID>",
 "tables": [{"table": "Table 2", "verdict": "header_misprint | reader_misread | cell_typo | consistent | ambiguous",
             "columns": {"kcat": "s^-1 as printed", "Km": "mM as printed", "kcat/Km": "printed M^-1 s^-1, really mM^-1 s^-1"},
             "page_image": true, "summary": "<one line>"}],
 "rows": [{"row_id": "<row_id>", "metric": "kcat/Km", "raw_value": "<the row's raw_value>", "action": "unitfix",
           "unit": "mM^-1 s^-1", "evidence": "<at most 300 characters>"}]}
```

Copy each row's `metric` and `raw_value` exactly. Write the file, validate it
(`python3 -c "import json;json.load(open('work/scale_<PMID>.json'))"`) and report one line: the verdict per table and
the number of rows per action.

## Second look (when your task says so)

A first check called a table `ambiguous`; its summary is in your task. Look for a printed fact it did not use that
decides which column is misprinted: render the pages with figures (axis units, the substrate range of a fitted curve,
where it reaches Vmax/2), the Methods (enzyme amount or concentration in the kinetic assay, substrate ranges), every
Results and Discussion sentence that quotes one of the table's numbers, the abstract, other tables, the supplement.
Closure, the databases and values typical for the enzyme family never decide. Write `work/scale_<PMID>.second.json`
in the output format above: `ambiguous` again when nothing printed decides (that is a correct answer).

## Refute a proposed change (when your task says so)

Your task gives a change another checker proposed: the rows, the unit, and its evidence. Try to show it is wrong.
Re-read the table's headers and cells on the page image; find every fact the evidence cites (numbers, ranges, quoted
sentences) in the paper and check it is printed as cited; redo its arithmetic; test the other readings (another
column misprinted instead, a header multiplier read the other way, a copying error of the reader); look for a printed
fact that contradicts the change. A row is `refuted: true` when a cited fact is not in the paper or is misquoted, the
arithmetic does not hold, a printed fact contradicts the change, or the evidence leaves another column as likely as
the one changed (closure alone). It is `refuted: false` only when every cited fact checks out and together they decide
the column and the unit. When unsure, refuted. Write `work/scale_<PMID>.refute<k>.json` (k from your task):

```json
{"pmid": "<PMID>", "refuter": 1, "rows": [{"row_id": "<row_id>", "refuted": true, "reason": "<one line: the fact checked and what the paper prints>"}]}
```
