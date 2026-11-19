# Locked test, stage 2: every source against EnzyExtract's manual curation on 79 held-out papers

Plan: ../STAGE2.md (commit 41d125f, before any run was scored on these papers). The curation's values on these papers: 1428 scored, 98 not scored. Matching: per paper and metric, one to one, within 1.5%. Intervals: paper-clustered bootstrap, B 10000, seed 20261031; differences paired. Exact repeats dropped.

| Source | Papers with values | Values | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision |
|---|---|---|---|---|---|---|
| CatLog (first pass) | 78 | 1346 | 0.742 (0.673-0.808) | 0.787 (0.718-0.856) |  |  |
| Plain read (Opus 5.5) | 78 | 1411 | 0.768 (0.699-0.838) | 0.777 (0.706-0.849) | -0.027 (-0.047 to -0.011) | +0.009 (-0.008 to +0.033) |
| EnzyExtract run RGF | 77 | 1433 | 0.819 (0.759-0.873) | 0.816 (0.743-0.883) | -0.078 (-0.165 to +0.015) | -0.030 (-0.100 to +0.043) |
| EnzyExtract run 4o-05 | 78 | 1450 | 0.789 (0.713-0.853) | 0.777 (0.702-0.845) | -0.048 (-0.132 to +0.048) | +0.010 (-0.055 to +0.084) |
| EnzyExtract run 4o-mini | 79 | 1340 | 0.655 (0.579-0.733) | 0.698 (0.615-0.782) | +0.087 (+0.018 to +0.162) | +0.089 (+0.011 to +0.174) |
| EnzyExtract run 4o-mini_Rx | 78 | 1043 | 0.463 (0.391-0.545) | 0.634 (0.557-0.717) | +0.279 (+0.196 to +0.358) | +0.153 (+0.063 to +0.245) |
| EnzyExtract run 4o-mini_xG | 78 | 1267 | 0.557 (0.475-0.644) | 0.627 (0.534-0.719) | +0.185 (+0.101 to +0.271) | +0.159 (+0.074 to +0.252) |
| EnzyExtract run RxF | 79 | 1256 | 0.639 (0.554-0.723) | 0.726 (0.652-0.797) | +0.103 (+0.029 to +0.184) | +0.061 (-0.008 to +0.135) |
| EnzyExtract run gemini | 76 | 1175 | 0.653 (0.582-0.721) | 0.793 (0.717-0.863) | +0.089 (-0.017 to +0.194) | -0.006 (-0.086 to +0.079) |
| EnzyExtract run sonnet37 | 75 | 1283 | 0.725 (0.638-0.810) | 0.807 (0.721-0.889) | +0.017 (-0.058 to +0.103) | -0.020 (-0.086 to +0.048) |
| EnzyExtract run xGF | 79 | 1464 | 0.751 (0.670-0.822) | 0.732 (0.623-0.833) | -0.009 (-0.107 to +0.094) | +0.055 (-0.045 to +0.160) |
| EnzyExtract database | 20 | 443 | 0.259 (0.142-0.378) | 0.835 (0.731-0.948) | +0.482 (+0.336 to +0.631) | -0.048 (-0.174 to +0.070) |
| BRENDA 2026.1 | 78 | 516 | 0.326 (0.274-0.385) | 0.901 (0.853-0.944) | +0.416 (+0.345 to +0.480) | -0.114 (-0.191 to -0.040) |

Best EnzyExtract run by recall: RGF; by precision: RGF.

## By metric (recall, precision)

| Source | kcat | Km | kcat/Km |
|---|---|---|---|
| CatLog (first pass) | 0.696, 0.727 | 0.787, 0.906 | 0.703, 0.659 |
| Plain read (Opus 5.5) | 0.743, 0.763 | 0.816, 0.892 | 0.703, 0.616 |
| EnzyExtract run RGF | 0.890, 0.798 | 0.816, 0.846 | 0.750, 0.783 |
| EnzyExtract run 4o-05 | 0.830, 0.768 | 0.808, 0.815 | 0.711, 0.717 |
| EnzyExtract run 4o-mini | 0.694, 0.697 | 0.669, 0.808 | 0.586, 0.538 |
| EnzyExtract run 4o-mini_Rx | 0.461, 0.559 | 0.487, 0.829 | 0.419, 0.465 |
| EnzyExtract run 4o-mini_xG | 0.665, 0.726 | 0.501, 0.639 | 0.547, 0.520 |
| EnzyExtract run RxF | 0.599, 0.713 | 0.703, 0.816 | 0.558, 0.584 |
| EnzyExtract run gemini | 0.757, 0.838 | 0.736, 0.782 | 0.383, 0.750 |
| EnzyExtract run sonnet37 | 0.723, 0.773 | 0.771, 0.903 | 0.639, 0.676 |
| EnzyExtract run xGF | 0.887, 0.807 | 0.695, 0.682 | 0.711, 0.742 |
| EnzyExtract database | 0.395, 0.816 | 0.201, 0.836 | 0.225, 0.871 |
| BRENDA 2026.1 | 0.068, 0.684 | 0.625, 0.929 | 0.028, 0.625 |

CatLog minus RGF by metric: kcat: recall -0.194 (-0.337 to -0.033), precision -0.071 (-0.217 to +0.081); Km: recall -0.029 (-0.116 to +0.060), precision +0.060 (+0.007 to +0.119); kcat/Km: recall -0.047 (-0.189 to +0.101), precision -0.124 (-0.260 to +0.021).

## Rules 1 to 3

Repeats dropped (values): {'catlog': 16, 'plain': 20, 'run_4o-05': 20, 'run_4o-mini_Rx': 7, 'run_4o-mini': 27, 'run_4o-mini_xG': 32, 'run_RGF': 20, 'run_RxF': 42, 'run_gemini': 22, 'run_sonnet37': 12, 'run_xGF': 34, 'enzyextract_db': 164, 'brenda': 7}. Stage 1 had already dropped 10 repeats of the plain read and 0 of CatLog. The curation keeps its own 24 exact repeats, each of which a source can match only once.
With repeats kept (recall/precision; CatLog minus it: recall, precision): catlog 0.748/0.784; plain 0.775/0.773 (-0.027 (-0.047 to -0.011), +0.011 (-0.007 to +0.035)); run_RGF 0.826/0.812 (-0.078 (-0.166 to +0.015), -0.028 (-0.099 to +0.045)); run_4o-05 0.799/0.776 (-0.051 (-0.137 to +0.045), +0.008 (-0.057 to +0.083)); run_4o-mini 0.662/0.691 (+0.086 (+0.016 to +0.162), +0.093 (+0.015 to +0.179)); run_4o-mini_Rx 0.466/0.634 (+0.282 (+0.198 to +0.362), +0.150 (+0.059 to +0.243)); run_4o-mini_xG 0.564/0.620 (+0.184 (+0.100 to +0.271), +0.164 (+0.078 to +0.258)); run_RxF 0.646/0.710 (+0.102 (+0.027 to +0.185), +0.074 (+0.000 to +0.153)); run_gemini 0.664/0.792 (+0.084 (-0.023 to +0.191), -0.008 (-0.087 to +0.077)); run_sonnet37 0.732/0.807 (+0.016 (-0.059 to +0.103), -0.023 (-0.089 to +0.045)); run_xGF 0.758/0.723 (-0.011 (-0.111 to +0.094), +0.061 (-0.040 to +0.169)); enzyextract_db 0.265/0.624 (+0.482 (+0.332 to +0.634), +0.160 (-0.115 to +0.331)); brenda 0.327/0.893 (+0.421 (+0.350 to +0.485), -0.109 (-0.186 to -0.033)). For CatLog and the plain read these are stage 1's secondary numbers, checked equal.
Not scored, per source and metric (a bound, a number with no unit, or a cell the units code cannot read): {'run_4o-05': {'kcat': 16, 'Km': 18, 'kcat/Km': 76}, 'run_4o-mini_Rx': {'kcat': 6, 'Km': 10, 'kcat/Km': 33}, 'run_4o-mini': {'kcat': 17, 'Km': 7, 'kcat/Km': 42}, 'run_4o-mini_xG': {'kcat': 22, 'Km': 8, 'kcat/Km': 31}, 'run_RGF': {'kcat': 8, 'Km': 15, 'kcat/Km': 100}, 'run_RxF': {'kcat': 8, 'Km': 5, 'kcat/Km': 84}, 'run_gemini': {'kcat': 41, 'Km': 78, 'kcat/Km': 136}, 'run_sonnet37': {'kcat': 8, 'Km': 23, 'kcat/Km': 67}, 'run_xGF': {'kcat': 8, 'Km': 16, 'kcat/Km': 105}, 'enzyextract_db (kcat/Km strings only)': {'kcat': 0, 'Km': 0, 'kcat/Km': 8}}; the curation's unscored cells: {'kcat': 27, 'Km': 17, 'kcat/Km': 54}. CatLog, the plain read and BRENDA arrive as numbers.
EnzyExtract database: scored; the extract of 22 October found its rows through each paper's DOI and could not look for ['10564758'] (no DOI key then).
Papers for which a run has no row (their curation values count as missed): {'run_4o-05': 0, 'run_4o-mini_Rx': 1, 'run_4o-mini': 0, 'run_4o-mini_xG': 1, 'run_RGF': 1, 'run_RxF': 0, 'run_gemini': 2, 'run_sonnet37': 3, 'run_xGF': 0}.
On the papers where a run has rows (the run; CatLog on the same papers; CatLog minus the run): 4o-mini_Rx on 78 papers: 0.472/0.634; CatLog 0.742/0.797; recall +0.269 (+0.188 to +0.348), precision +0.163 (+0.073 to +0.255); 4o-mini_xG on 78 papers: 0.558/0.627; CatLog 0.741/0.792; recall +0.184 (+0.100 to +0.272), precision +0.165 (+0.077 to +0.259); RGF on 78 papers: 0.830/0.816; CatLog 0.738/0.784; recall -0.091 (-0.176 to -0.003), precision -0.033 (-0.104 to +0.041); gemini on 77 papers: 0.670/0.793; CatLog 0.740/0.782; recall +0.070 (-0.032 to +0.175), precision -0.011 (-0.092 to +0.072); sonnet37 on 76 papers: 0.767/0.807; CatLog 0.741/0.779; recall -0.026 (-0.083 to +0.036), precision -0.028 (-0.092 to +0.041).

## Without 9973343 and 10447675 (77 papers)

| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision |
|---|---|---|---|---|
| CatLog (first pass) | 0.744 (0.674-0.813) | 0.806 (0.741-0.870) |  |  |
| Plain read (Opus 5.5) | 0.768 (0.697-0.838) | 0.792 (0.723-0.858) | -0.024 (-0.042 to -0.009) | +0.014 (-0.001 to +0.037) |
| EnzyExtract run RGF | 0.819 (0.757-0.874) | 0.828 (0.755-0.895) | -0.074 (-0.165 to +0.023) | -0.022 (-0.097 to +0.052) |
| EnzyExtract run 4o-05 | 0.788 (0.712-0.855) | 0.788 (0.714-0.856) | -0.044 (-0.131 to +0.052) | +0.019 (-0.048 to +0.095) |
| EnzyExtract run 4o-mini | 0.651 (0.575-0.732) | 0.708 (0.622-0.794) | +0.094 (+0.024 to +0.169) | +0.098 (+0.015 to +0.184) |
| EnzyExtract run 4o-mini_Rx | 0.461 (0.390-0.544) | 0.634 (0.555-0.718) | +0.283 (+0.197 to +0.363) | +0.172 (+0.081 to +0.263) |
| EnzyExtract run 4o-mini_xG | 0.552 (0.466-0.641) | 0.634 (0.537-0.728) | +0.193 (+0.107 to +0.283) | +0.172 (+0.081 to +0.266) |
| EnzyExtract run RxF | 0.631 (0.546-0.718) | 0.732 (0.656-0.805) | +0.114 (+0.040 to +0.194) | +0.074 (+0.004 to +0.150) |
| EnzyExtract run gemini | 0.654 (0.582-0.723) | 0.803 (0.725-0.870) | +0.091 (-0.016 to +0.199) | +0.003 (-0.082 to +0.090) |
| EnzyExtract run sonnet37 | 0.719 (0.631-0.803) | 0.816 (0.730-0.896) | +0.026 (-0.051 to +0.114) | -0.009 (-0.078 to +0.060) |
| EnzyExtract run xGF | 0.749 (0.667-0.820) | 0.741 (0.629-0.843) | -0.004 (-0.104 to +0.099) | +0.065 (-0.037 to +0.174) |
| EnzyExtract database | 0.258 (0.139-0.377) | 0.831 (0.724-0.945) | +0.487 (+0.336 to +0.637) | -0.025 (-0.152 to +0.092) |
| BRENDA 2026.1 | 0.326 (0.276-0.387) | 0.899 (0.848-0.943) | +0.418 (+0.347 to +0.484) | -0.093 (-0.162 to -0.023) |

Read with care: the curation is EnzyExtract's own reference, as printed, not ground truth; nothing is judged here; CatLog's side is its first pass; EnzyExtract's runs are its authors' 2025 models, CatLog and the plain read use Opus 5.5; 32 benchmark papers left stage 1's set for a refusal or a broken rule on the Opus side; on 22 October every run was scored on all 384 benchmark papers pooled, these among them, but no number for these papers alone was computed before this plan.
