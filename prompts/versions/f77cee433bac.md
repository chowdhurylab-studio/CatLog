# Verify one paper's rows

You are an independent checker. Another agent extracted kinetic rows from a paper; your job is to catch
its mistakes. Assume each row may be wrong until the paper shows it is right. When in doubt, reject: a
dropped good row costs one row, an accepted bad row corrupts the catalog.

Inputs: `texts/<PMID>.txt` (the paper) and `work/<PMID>.read.json` (rows, indexed from 0).
Output: write `work/<PMID>.verify.json` and nothing else.

The original PDF/XML is named in `papers.tsv` (`text_source`). When the text layer of a table is garbled
(PDF), re-render the page (`pdftotext -f N -l N -layout`) or render it to an image in /tmp and look at it
before you confirm a value from that table.

For each row, find the value in the paper yourself (do not trust `quote` or `location`) and check:

0. The text is the paper the PMID names (title on the first page). If not, reject every row.
1. The number in `raw_value` is printed in the paper at that location, in full: ±, (u), trailing zeros and
   exponent included. A raw value missing a printed ± is a `fix`.
2. `metric` is right: the column/sentence really is kcat, Km or kcat/Km — not Ki, Kd, Kact, K0.5/S0.5 (Hill),
   a metal half-activation constant, Vmax/Vm in µmol/min/mg, specific activity, or a ratio relative to wild type.
3. `raw_unit` is the unit that applies to that number, including any multiplier in the column header
   or caption. Code converts `raw_value` + `raw_unit` to the stored value: run
   `python3 <the CatLog folder>/catlog.py show <PMID>` (add ` .missed` for the missed file)
   and check every "stored as" value is what the paper means (kcat s^-1, Km mM, kcat/Km mM^-1 s^-1).
   Watch headers like "kcat/Km × 10^-5" that mean the printed number is already multiplied. Never rewrite
   `raw_unit`: it stays exactly as printed. If the printed unit is right but does not convert, or converts
   wrongly, give a spelling that converts correctly in `fix.unit_for_conversion` (e.g. `M-1 s-1`,
   `10^5 M-1 s-1`); if you cannot tell what the header means, reject. A kcat/Km that is ≥5× away from
   kcat ÷ Km of the same row is a unit error, not a real value.
4. `enzyme`, `organism`, `variant` and `substrate` match that table row / sentence. Check row/column
   alignment in tables: a value must sit under its own header and on its own variant's line. Watch for
   kcat and Km taken from different blocks (cofactor, metal, substrate or condition), NAD+/NADP+ and
   stereoisomer swaps, and multipliers credited to the wrong column.
5. `pH`, `temperature_C` and `conditions` match the assay that produced this value.
6. The value was measured in this paper: not "taken from", "previously reported", a cited row, or a
   caption/footnote crediting another source.
7. The row is not a duplicate of another row in the file (same variant, substrate, metric, conditions).

Verdicts:
- `confirm`: everything checks out.
- `fix`: one or more fields are wrong but the paper clearly shows the right value; give only the corrected
  fields in `fix` (same field names as the row). If you change the number, also give the new `quote`.
- `reject`: the value is not in the paper, is not a measured kcat/Km/kcat/Km, is from another source, or
  identity/conditions cannot be pinned down.

If the extractor skipped measured kcat, Km or kcat/Km values that you are sure of, write them to
`work/<PMID>.missed.read.json` in the same format as the read file (`{"pmid", "doi", "title", "note", "rows"}`).
A separate checker verifies them. Do not include them in your verdicts.

```json
{"pmid": "", "verdicts": [{"i": 0, "verdict": "confirm|fix|reject", "reason": "one line", "fix": {}}],
 "missed_count": 0}
```

Give one verdict for every row index. Keep reasons to one line with the location you checked.
