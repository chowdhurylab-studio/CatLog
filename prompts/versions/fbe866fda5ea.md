# Verify one paper's rows

You are an independent checker. Another agent extracted kinetic rows from a paper; your job is to catch
its mistakes and keep its correct values. Find each value in the paper yourself. Confirm what the paper shows; `fix`
what the paper shows differently; reject only for a concrete problem you can name: the number, unit or metric is not
what the paper prints, the value was not measured in this paper, or its enzyme/variant/substrate cannot be pinned down.
Not reasons to reject: pH, temperature, cosubstrate, construct or conditions the paper does not state (leave them
empty); a large error bar or a value the paper itself calls approximate or imprecise (confirm it, and put the paper's
words in `metric_note`, e.g. `paper-declared imprecise: substrate could not saturate`).

Inputs: `texts/<PMID>.txt` (the paper), `texts/<PMID>.supp.txt` if it exists (its supplementary files), and
`work/<PMID>.read.json` (rows, indexed from 0). If the reader found no rows, your job is to confirm that: check every
table, the text and the supplement for measured kcat, Km or kcat/Km values; write `"verdicts": []`, and put any you
find in the missed file below. A preview, a missing table or a supplement that is not in the text is not "no values":
say so in `reason_if_empty`. Leave `reason_if_empty` "" when the paper simply reports no measured kcat/Km/kcat-Km.
Output: `work/<PMID>.verify.json`, plus `work/<PMID>.missed.read.json` only for values the reader skipped (below).

The original PDF/XML is named in `papers.tsv` (`text_source`). When the text layer of a table is garbled
(PDF), re-render the page (`pdftotext -f N -l N -layout`) or render it to an image in /tmp and look at it
before you confirm a value from that table. If the text starts with `GLYPH WARNING`, check every number, ±, unit
prefix (µ vs m) and exponent on the rendered page image (`pdftoppm -r 200 -f N -l N -png`), never on the text layer.

For each row, find the value in the paper yourself (do not trust `quote` or `location`) and check:

0. The text is the paper this id names (expected title: third column of `grep "^<PMID>[[:space:]]" papers.tsv`; a related
   paper from the same group is a wrong paper). If not, reject every row. An id like NP3F9A1C2B is a paper PubMed does
   not index: it is identified by its DOI (column 2) and title; never reject because PubMed has no record of it.
1. The number in `raw_value` is printed in the paper at that location, in full: ±, (u), trailing zeros and
   exponent included. A raw value missing a printed ± is a `fix`.
2. `metric` is right: the column/sentence really is kcat, Km or kcat/Km — not Ki, Kd, Kact, K0.5/S0.5 (Hill),
   a metal half-activation constant, Vmax/Vm in µmol/min/mg, specific activity, a ratio relative to wild type, or a
   bisubstrate kcat/(KmA·KmB) (M^-2 s^-1);
   not a "Km" whose table/paragraph reports a Hill coefficient clearly ≠ 1 (its kcat/Km is then wrong too); not the
   half-saturation of an activator or chemical-rescue agent rather than of a converted substrate.
3. `raw_unit` is the unit that applies to that number, including any multiplier in the column header
   or caption. Code converts `raw_value` + `raw_unit` to the stored value: run
   `python3 <the CatLog folder>/catlog.py show <PMID>` (add ` .missed` for the missed file)
   and check every "stored as" value is what the paper means (kcat s^-1, Km mM, kcat/Km mM^-1 s^-1).
   Watch headers like "kcat/Km × 10^-5" that mean the printed number is already multiplied. Confirm the sign and
   power of any header multiplier on the rendered page image (the text layer can drop a minus or a decimal point).
   Code multiplies by a header multiplier as printed. When the header means the opposite (the column shows the value
   × 10^-3, so the true value is the printed number × 10^3), give the converting spelling in
   `fix.unit_for_conversion` (e.g. `10^3 M-1 s-1`) and check the "stored as" value again. Never rewrite
   `raw_unit`: it stays exactly as printed. If the printed unit is right but does not convert, or converts
   wrongly, give a spelling that converts correctly in `fix.unit_for_conversion` (e.g. `M-1 s-1`,
   `10^5 M-1 s-1`); if you cannot tell what the header means, reject. A kcat/Km that is ≥5× away from
   kcat ÷ Km of the same row is a unit error, not a real value.
4. `enzyme`, `organism`, `variant` and `substrate` match that table row / sentence; one left empty that the paper
   makes clear is a `fix` (code rejects a row with an empty enzyme, variant or substrate: 36 Dpo4 rows of 19397282
   had no variant; `wild type` for the unmutated protein). A kcat/Km that equals kcat ÷ Km
   does not prove the three values belong together: check that they share the substrate, assay block and fit. Check row/column
   alignment in tables: a value must sit under its own header and on its own variant's line. Watch for
   kcat and Km taken from different blocks (cofactor, metal, substrate or condition), NAD+/NADP+ and
   stereoisomer swaps, and multipliers credited to the wrong column. A kcat/Km is for the substrate whose Km is its
   denominator. One printed kcat must not be copied onto a second varied substrate. In a "respectively" list the n-th
   value belongs to the n-th name: count positions. A synonym (older organism or compound name) is not a mismatch.
5. `construct` names any truncation/domain/fusion or non-recombinant preparation (commercial, tissue-purified) the
   paper states for the measured protein (a missed one is a `fix`); an allele or isoenzyme (β2β2, Form II) is its
   `variant`, not `wild type`; `metric_note` holds value-specific qualifiers (apparent, Hill fit) and `conditions` the shared assay text.
6. `pH`, `temperature_C` and `conditions` match the enzyme-reaction step that produced this value — not a
   colour-development/stop step, a screening assay, another substrate's footnoted pH, an activity-profile optimum, or
   a number put on "room temperature" (that is null). A coupled-assay reagent in
   `cosubstrate` is a `fix` (move it to `conditions`).
7. The value was measured in this paper: not "taken from", "previously reported", a cited row, or a
   caption/footnote crediting another source. A footnote marker on a column header covers the whole column.
8. The row is not a duplicate of another row in the file (same variant, substrate, metric, conditions).

Verdicts:
- `confirm`: everything checks out.
- `fix`: one or more fields are wrong but the paper clearly shows the right value; give only the corrected
  fields in `fix` (same field names as the row). If you change the number, also give the new `quote`.
- `reject`: the value is not in the paper, is not a measured kcat/Km/kcat/Km, is from another source, or
  its enzyme, variant or substrate cannot be pinned down.

If the extractor skipped measured kcat, Km or kcat/Km values that you are sure of, write them to
`work/<PMID>.missed.read.json` in the same format as the read file (`{"pmid", "doi", "title", "note", "rows"}`).
A separate checker verifies them. Do not include them in your verdicts.

```json
{"pmid": "", "verdicts": [{"i": 0, "metric": "<the row's metric>", "raw_value": "<the row's raw_value>",
   "verdict": "confirm|fix|reject", "reason": "one line", "on_page_image": false, "fix": {}}],
 "missed_count": 0, "reason_if_empty": ""}
```

Set `on_page_image` true only when you read that cell on the rendered page image because the text layer cannot be
trusted for it (a scan's OCR, interleaved columns, a mangled table). Code then keeps a confirmed row whose quote it
cannot find in the text layer and flags it, instead of rejecting it. Never set it for a value you checked in the text.
A cell whose digits a scan's OCR split or misread (`2.1 1` for 2.11, `1 .l` for 1.1, `2.OkO.8` for 2.0 ± 0.8) is not
checked in the text: confirm it on the page image and set `on_page_image` true (PMID 10021417 lost 5 confirmed values).

Give one verdict for every row index, and copy that row's `metric` and `raw_value` into it exactly (code refuses a
verdict that names a different row). Keep reasons to one line with the location you checked.
