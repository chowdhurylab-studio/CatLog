# Values people confirmed: CatLog and EnzyExtract against them

Planned before either source was scored; the paper does not call this comparison registered. This folder keeps its
working name, the person-anchored comparison.

On papers whose values people checked against the paper, how many of the values people confirmed does each source hold,
and how many of the values people could not find in the paper, or found wrong? The reference is the reviewed records of
CatLog's earlier catalogue, built mostly from the databases before CatLog read these papers, and checked by people
between 29 June and 14 October 2026. A reference value is held when a source has a value within 1.5% of it in the same
paper and metric, matched one to one. 123 papers are scored. No agent is involved: code only.

## The plan and when it was fixed

| Commit | Time (US Central) | What |
| --- | --- | --- |
| ce89e0a679884c4d3a9ca786ecd33c5e0801e93e | 2026-11-18 17:15:52 | **the plan**, "fixed before any source is scored": the reference, the papers and the exclusions, the sources, the matcher and the endpoints |
| 9d09b670b49a57526baa5c993ca46d4124b095df | 2026-11-18 17:21:50 | **the first result**: `build.py` (written after the plan) and `results.json` |
| 0a58a3293ed3b9444f82095b09b91c7b9906606c | 2026-11-18 18:23:08 | post hoc checks: an independent recount (it agrees on every count), a fairness check, and `build_v2.py` with `results_v2.json`, which reads one more kind of EnzyExtract string (a power of ten inside the ± part, the F5 fix of `../enzyextract_broad/CORRECTIONS.md`) |

`PLAN.md` is byte for byte as committed at ce89e0a and unchanged since: git blob id
d3e39f832ea959c4a69316cabddf88c24e2fb629 (`git hash-object PLAN.md` gives it).

## Files

| File | What it is |
| --- | --- |
| `PLAN.md` | the plan, as committed |
| `reference.tsv` | every reference value on the 123 papers: its paper and metric, whether people confirmed it (`confirmed`, with the database it came from) or found it not in the paper or wrong (with that category), and the CatLog value and the EnzyExtract row that hold it. **The reference values themselves are not here**: they are the databases' values (BRENDA, OED, SABIO-RK, UniProt), whose licences are their own. No reviewer and no review time is given |
| `values.tsv` | CatLog's stored values on the 123 papers (its row id, the value in catalogue units, the printed cell and unit, its labels and its quoted line) |
| `enzyextract_rows.tsv` | EnzyExtract's values on the 123 papers, each by its row of `TheData.parquet` and its metric, with how its string was read |
| `results.json` | the result as planned (`build.py`): both endpoints, by metric and by database, per paper |
| `results_v2.json` | the same with the F5 fix (`build_v2.py`), post hoc |
| `build.py`, `build_v2.py` | the scorers |

`reference.tsv` is made here by `build.py`'s own functions (its reference, its papers, its readers and its rule for a
held value, kept as pairs), and its counts are checked against `results.json`: 1,617 confirmed values, 1,372 held by
CatLog and 1,297 by EnzyExtract.

## Changes made here

None to the plan. The JSON outputs are aggregates (their per-value lists left out).

## Not here

The reference values (above), who reviewed each record and when, the earlier catalogue, and the post hoc recount,
fairness and sensitivity analyses and their notes: kept by the authors.
