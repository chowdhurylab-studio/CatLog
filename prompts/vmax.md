# Check a stored kcat that disagrees with the paper's own printed rate

A sweep (`tools/vmax_sweep.py`) found that one or more kcat values CatLog stored from this paper are far above the
turnover number the paper's own printed rate allows:

    kcat [s^-1] = Vmax or specific activity [µmol min^-1 mg^-1] × subunit mass [kDa] / 60

Your task file `work/vmax_<PMID>.task.json` gives the paper's files, the mass used, the rates the sweep read with the
kcat each implies, the bound, the stored kcat values above it, and every catalog row of the paper. Decide what the
paper's own facts show. Nothing changes unless you say so, and a value is never changed to make it look plausible.

## Read blind

Use only the paper's own files: `text`, `supplement`, the `original_file` (PDF or XML) and page images you render from
it (`pdftoppm -r 200 -f N -l N -png <file> /tmp/v<PMID>`). Never open database values or exports (`sources/`,
`catlog_wide.*`, `work/vmax_sweep.tsv`, `work/dbcheck_*`, `work/old/`), the earlier catalog (anything under realkcat
except the original file you are given) or `human_review/`.

Read every number, unit prefix (µ vs m vs n), exponent and header multiplier on the rendered page image, never on the
text layer alone: PDF text often prints µ as `m` or `l`, a middle dot as `Æ`, a superscript minus as `21`, `31` or
`)1`, and drops a header's `× 10^3`. If `glyph_warning` is true the text layer is known to be damaged.

## What the disagreement can mean

Work through these before proposing anything; several can be true at once.

1. **The rate is not the enzyme's maximal rate.** It is a relative-activity panel (100% = some small number), a
   trace-substrate comparison, a crude extract or a membrane fraction (per mg of total protein, not of enzyme), a
   coupled-assay rate, or a rate for another form, another substrate or another temperature. Then the rate bounds
   nothing: `keep`, and say which it is.
2. **The mass is wrong for this construct.** The sweep used the largest UniProt subunit of the paper. A multi-domain
   fusion, a tagged construct, a processed chain or a multimer the paper quotes per mol of multimer changes the
   arithmetic. Recompute with the paper's own mass if it prints one.
3. **A misprinted unit header** on the kcat column (or the reader read it wrongly): the stored values are a whole
   column off by an exact factor, and the paper's own rate, a sister table, a Methods range or a figure axis shows the
   right unit. Then `unitfix` every row of that column, flagged or not, so the column stays consistent.
4. **One cell is wrong**: a decimal or exponent slip in a single value (`505215` for `505.215`), a cell taken from
   another row, or a number that is not a kcat at all. Then `drop` (or `unitfix` when a unit fixes it), that row only.
5. **The paper's own numbers disagree with each other.** Its rate and its kcat cannot both be right, and nothing it
   prints settles which. Then `ambiguous`: the value stays as printed, and the disagreement is the finding.

Say in `basis_check` whether the sweep's own inputs hold: was the rate it read really offered as a maximal rate, and
is the mass right for the measured construct?

## One action per row

For every row the task marks in `kcat_above_the_bound`, and for every other row of the same column or table when your
verdict is a header misprint, give one action:

- `unitfix`: the printed unit is misprinted (or the reader copied it wrongly) and `unit` is the unit the paper's own
  facts show. Spell `unit` so code converts it, and test it on the row's raw_value:
  `cd <the CatLog folder> && python3 -c "import sys; sys.path.insert(0,'tools'); from units import normalize; print(normalize('kcat', '505215', 'min^-1'))"`
  (metric `kcat`, `Km` or `kcat/Km`; it prints value, catalog unit, error). Spellings that work: `s^-1`, `min^-1`,
  `10^-3 s^-1`, `uM`, `mM`, `mM^-1 s^-1`, `uM^-1 min^-1`, `10^3 M^-1 s^-1`.
- `keep`: the stored value is right as it stands (case 1 or 2, or the paper's rate is for something else).
- `drop`: the stored value is wrong and no unit fixes it.
- `ambiguous`: the paper cannot settle it. Nothing changes.

`evidence` (at most 300 characters, the same for rows that share it): facts a reader can check in the paper, every
number as printed, including the arithmetic: `Table 1 'V max (units/mg)' 63.9 and 'k cat (s-1)' 505215; 63.9 µmol/min/mg
× 107 kDa / 60 = 114 s^-1; the row's other cells print kcat 505.215`. No reasoning words (so, thus, therefore, because,
since, must, likely, probably, clearly, suggests, implies, means), no `I` or `we`, no row_ids.

## Output

```json
{"pmid": "<PMID>",
 "basis_check": {"rate_is_a_maximal_rate": true, "rate_note": "<where the rate is printed and what it is per>",
                 "mass_ok": true, "mass_note": "<the paper's own mass if it prints one>"},
 "verdict": "header_misprint | cell_slip | rate_not_comparable | mass_wrong | paper_disagrees | consistent",
 "summary": "<one line>",
 "rows": [{"row_id": "<row_id>", "metric": "kcat", "raw_value": "<the row's raw_value>", "action": "unitfix",
           "unit": "min^-1", "evidence": "<at most 300 characters>"}]}
```

Copy each row's `metric` and `raw_value` exactly from the task file. Write `work/vmax_<PMID>.json`, validate it
(`python3 -c "import json;json.load(open('work/vmax_<PMID>.json'))"`) and report one line: the verdict and the number
of rows per action.

## Refute a proposed change (when your task says so)

Your task gives a change another checker proposed: the rows, the action, the unit and its evidence. Try to show it is
wrong. Re-read the table's headers and cells on the page image; find every fact the evidence cites (numbers, ranges,
quoted sentences) in the paper and check it is printed as cited; redo its arithmetic, including the mass and the
`/ 60`; test the other readings of this disagreement (cases 1-5 above, above all whether the rate is a maximal rate at
all and whether the mass fits the measured construct); look for a printed fact that contradicts the change. A row is
`refuted: true` when a cited fact is not in the paper or is misquoted, the arithmetic does not hold, a printed fact
contradicts the change, or the evidence leaves another reading as likely as the one proposed. It is `refuted: false`
only when every cited fact checks out and together they decide the action and the unit. When unsure, refuted. Write
`work/vmax_<PMID>.refute<k>.json` (k from your task):

```json
{"pmid": "<PMID>", "refuter": 1, "rows": [{"row_id": "<row_id>", "refuted": true, "reason": "<one line: the fact checked and what the paper prints>"}]}
```
