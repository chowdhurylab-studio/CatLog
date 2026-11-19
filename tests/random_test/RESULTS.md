# Further set read once: the same values judged again blind, each claim with its record's full details (2026-11-09 12:43:08 -0600)

Papers: 147 analysed of 167 listed (left out before judging: {'refused': 17}; nothing left to judge: 3).
Judge check: passed: decoys caught 171 of 171, the first two judges agree on 0.970 of the disputed claims (0.992 of all).

| | Plain read | CatLog |
|---|---|---|
| Values | 4530 | 4390 |
| Judged | 1011 | 873 |
| Agreed, not judged | 3499 | 3499 |
| Wrong found | 42 | 6 |
| Wrong found per 1,000 (95% interval) | 9.31 (0.6-23.7) | 1.37 (in 1 of 147 papers: too few for an interval) |
| Papers with a wrong value found, per 100 (exact 95%) | 3.4 (1.1-7.8) | 0.7 (0.0-3.7) |
| Same, on papers where the source stored a value | 3.4 of 147 | 0.7 of 147 |
| Agreed pairs sampled: wrong | 1 of 739 (exact 0.00-0.75%) | 0 of 739 (exact 0.00-0.50%) |
| Per 1,000 with the sample scaled to the unsampled pairs | 10.36 (0.6-27.0) | 1.37 |
| Per 1,000 at the sample's upper limit | 15.14 | 5.36 |
| Cannot decide | 20 | 21 |
| Per 1,000, cannot-decide as wrong | 13.69 | 6.15 |
| Per 1,000, 200 values per paper at most | 9.31 | 1.37 |
| Largest paper's share of wrong | 0.643 | 1.0 |
| Supported values only the other stored (misses) | 7 | 110 |

The rate with the sample scaled resamples papers only; it does not carry the sample's own uncertainty, which the exact line gives.

Papers wrong in one source only: plain 5, CatLog 1.
Plain minus CatLog, wrong per 1,000: -1.7 to 22.5; papers with a wrong value per 100: 0.0 to 6.1 (paper-level bootstrap, B 10000).
Kinds (plain): not_measured_here 29, wrong_metric 13
Kinds (catlog): wrong_scale 6
Papers read by claude-opus-5-5: 147.

Judges: decoys called an error j1 171/171, j2 171/171; kappa on real claims 0.837; third judge on 17 real claims.
Sampled claims judged: 1482 ({'supported': 1477, 'not_measured_here': 1, 'cannot_decide': 4}).


## Against the first judging, on the same papers (details now shown)

| | Plain read | CatLog |
|---|---|---|
| Wrong per 1,000 stored values, first judging | 13.91 | 3.42 |
| Wrong per 1,000 stored values, with full records | 9.27 | 1.37 |
| Second minus first, paired paper bootstrap 95% | [-9.76, -0.86] | [-6.5, 2.39] |
| Scaled with the agreeing sample, first / second | [22.25, 10.36] | [13.11, 1.37] |
| Papers with a wrong value, first / second | [11, 5] | [6, 1] |

Each value, first verdict -> verdict with full records (agreeing-sample values weigh about 1 + unsampled/sampled agreeing pairs in the scaled rates; disputed values weigh 1):

| | Plain, agreeing sample | Plain, disputed | CatLog, agreeing sample | CatLog, disputed |
|---|---|---|---|---|
| error -> error | 1 | 41 | 0 | 0 |
| error -> supported | 7 | 14 | 9 | 6 |
| error -> cannot_decide | 0 | 0 | 0 | 0 |
| supported -> error | 0 | 0 | 0 | 6 |
| supported -> supported | 731 | 217 | 730 | 119 |
| supported -> cannot_decide | 2 | 18 | 2 | 16 |
| cannot_decide -> error | 0 | 0 | 0 | 0 |
| cannot_decide -> supported | 0 | 0 | 0 | 0 |
| cannot_decide -> cannot_decide | 0 | 0 | 0 | 3 |

Decoys caught by kind (the gate's decoys): {'x1000': [74, 74], 'x60': [97, 97]}; with their twin in the chunk: 9 of 9.
First errors by how the first judging decided them: plain {'2-0': {'error': 42, 'supported': 14}, 'third judge': {'supported': 7}}; CatLog {'2-0': {'supported': 14}, 'third judge': {'supported': 1}}.
Read with care: fresh judges re-deciding values first judged wrong rescue some without any cause (regression to the mean; compare the 2-0 and third-judge rows); a record's shape shows its source (CatLog's details join up to four fields, the plain read's two); an agreeing value shows as two claims, so a lone claim is a disputed value (662 of the first judging's 750 sampled pairs showed so too). Per-claim figures above this section (claims judged, kappa, misses) count the 88 former shared claims twice and differ from the first report for that reason.
