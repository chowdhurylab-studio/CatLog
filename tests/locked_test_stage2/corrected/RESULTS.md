# Stage 2 scored again with its units reading fixed (post hoc)

Registered: score_stage2.py and score_checked.py as committed (their results.json, reproduced here). Misreads: cells the registered reading read as another number read as written. Written: also the cells it left unread, read as written. Found after the result by an independent audit (writing/research/comparison_audit_20261118/enzyextract.md, F1).

## Cells whose reading changes

curation left unread: 49; curation read as another number: 15; enzyextract_db read as another number: 2; run_4o-05 left unread: 2; run_4o-05 read as another number: 7; run_4o-mini left unread: 1; run_4o-mini read as another number: 5; run_4o-mini_Rx left unread: 1; run_4o-mini_Rx read as another number: 5; run_4o-mini_xG left unread: 23; run_4o-mini_xG read as another number: 5; run_RGF left unread: 26; run_RGF read as another number: 6; run_RxF left unread: 26; run_RxF read as another number: 3; run_gemini left unread: 20; run_gemini read as another number: 2; run_sonnet37 left unread: 7; run_sonnet37 read as another number: 19; run_xGF left unread: 26; run_xGF read as another number: 6.

## Against the curation

| Source | Registered | Misreads fixed | Every cell as written |
|---|---|---|---|
| catlog | 0.742 / 0.787 | 0.752 / 0.798 | 0.754 / 0.828 |
| plain | 0.768 / 0.777 | 0.779 / 0.788 | 0.780 / 0.816 |
| run_RGF | 0.819 / 0.816 | 0.821 / 0.819 | 0.814 / 0.825 |
| run_4o-05 | 0.789 / 0.777 | 0.791 / 0.779 | 0.774 / 0.787 |
| run_sonnet37 | 0.725 / 0.807 | 0.727 / 0.809 | 0.708 / 0.810 |
| enzyextract_db | 0.259 / 0.835 | 0.259 / 0.835 | 0.251 / 0.835 |
| brenda | 0.326 / 0.901 | 0.326 / 0.901 | 0.316 / 0.905 |

| CatLog minus RGF | Registered | Misreads fixed | Every cell as written |
|---|---|---|---|
| all recall | -0.078 (-0.165 to +0.015) | -0.069 (-0.160 to +0.028) | -0.060 (-0.153 to +0.037) |
| all precision | -0.030 (-0.100 to +0.043) | -0.021 (-0.093 to +0.052) | +0.003 (-0.073 to +0.079) |
| kcat recall | -0.194 (-0.337 to -0.033) | -0.194 (-0.337 to -0.033) | -0.145 (-0.315 to +0.059) |
| kcat precision | -0.071 (-0.217 to +0.081) | -0.071 (-0.217 to +0.081) | -0.017 (-0.193 to +0.160) |
| Km recall | -0.029 (-0.116 to +0.060) | -0.029 (-0.116 to +0.060) | -0.029 (-0.115 to +0.060) |
| Km precision | +0.060 (+0.007 to +0.119) | +0.060 (+0.007 to +0.119) | +0.061 (+0.008 to +0.120) |
| kcat/Km recall | -0.047 (-0.189 to +0.101) | -0.014 (-0.172 to +0.162) | -0.026 (-0.182 to +0.144) |
| kcat/Km precision | -0.124 (-0.260 to +0.021) | -0.093 (-0.241 to +0.062) | -0.066 (-0.211 to +0.087) |
| on RGF's 78 papers, recall | -0.091 (-0.176 to -0.003) | -0.083 (-0.170 to +0.009) | -0.073 (-0.164 to +0.021) |
| on RGF's 78 papers, precision | -0.033 (-0.104 to +0.041) | -0.023 (-0.096 to +0.051) | +0.001 (-0.075 to +0.076) |
| without misprint papers (77), recall | -0.074 (-0.165 to +0.023) | -0.066 (-0.158 to +0.034) | -0.057 (-0.151 to +0.044) |
| without misprint papers (77), precision | -0.022 (-0.097 to +0.052) | -0.013 (-0.087 to +0.062) | +0.012 (-0.066 to +0.088) |
| without finetuning papers (64), recall | -0.137 (-0.227 to -0.040) | -0.130 (-0.223 to -0.029) | -0.135 (-0.226 to -0.036) |
| without finetuning papers (64), precision | -0.100 (-0.168 to -0.034) | -0.092 (-0.162 to -0.025) | -0.078 (-0.147 to -0.015) |
| finetuning papers only (15), recall | +0.134 (-0.020 to +0.322) | +0.146 (-0.012 to +0.335) | +0.195 (+0.027 to +0.360) |
| finetuning papers only (15), precision | +0.174 (+0.049 to +0.349) | +0.186 (+0.062 to +0.362) | +0.242 (+0.107 to +0.393) |

| CatLog minus BRENDA (STAGE2.md endpoint 4) | Registered | Misreads fixed | Every cell as written |
|---|---|---|---|
| all, recall | +0.416 (+0.345 to +0.480) | +0.426 (+0.356 to +0.490) | +0.438 (+0.366 to +0.503) |
| without the two misprint papers, recall | +0.418 (+0.347 to +0.484) | +0.429 (+0.358 to +0.494) | +0.441 (+0.367 to +0.507) |
| all, precision | -0.114 (-0.191 to -0.040) | -0.103 (-0.180 to -0.030) | -0.077 (-0.152 to -0.011) |
| without the two misprint papers, precision | -0.093 (-0.162 to -0.023) | -0.082 (-0.150 to -0.012) | -0.055 (-0.118 to +0.006) |
| kcat recall | +0.628 (+0.500 to +0.758) | +0.628 (+0.500 to +0.758) | +0.641 (+0.515 to +0.769) |
| kcat precision | +0.043 (-0.303 to +0.383) | +0.043 (-0.303 to +0.383) | +0.100 (-0.244 to +0.438) |
| Km recall | +0.162 (+0.069 to +0.251) | +0.162 (+0.069 to +0.251) | +0.163 (+0.069 to +0.252) |
| Km precision | -0.023 (-0.075 to +0.027) | -0.023 (-0.075 to +0.027) | -0.022 (-0.075 to +0.027) |
| kcat/Km recall | +0.675 (+0.555 to +0.782) | +0.717 (+0.593 to +0.824) | +0.719 (+0.598 to +0.825) |
| kcat/Km precision | +0.034 (-0.450 to +0.709) | +0.073 (-0.413 to +0.748) | +0.115 (-0.369 to +0.784) |

CatLog minus the plain reading, recall: registered -0.027 (-0.047 to -0.011); misreads -0.027 (-0.047 to -0.011); written -0.026 (-0.046 to -0.010).
Best run: registered {'recall': 'run_RGF', 'precision': 'run_RGF'}; misreads {'recall': 'run_RGF', 'precision': 'run_RGF'}; written {'recall': 'run_RGF', 'precision': 'run_RGF'}.

## The page check: misreads fixed in place, and the reference merge fixed

A reading's value judged right may merge only into a reference value that the same reading does not already hold, i.e. not into a curation value that reading matches (registered: into any reference value, so such a value never entered the reference and counted against its own reading). Values the registered merge sent into a value their own reading holds: as_printed {'catlog': 5, 'rgf': 4}; corrected {'catlog': 5, 'rgf': 3}; reprints_right {'catlog': 5, 'rgf': 5}; reprints_repeats_right {'catlog': 5, 'rgf': 25}. Fixed, the values that enter the reference because of it (the growth of the reference): as_printed {'catlog': 5, 'rgf': 1}; corrected {'catlog': 5, 'rgf': 0}; reprints_right {'catlog': 5, 'rgf': 2}; reprints_repeats_right {'catlog': 5, 'rgf': 22}.

| CatLog minus RGF | Registered | Merge fixed only | Misreads fixed only | Both fixed |
|---|---|---|---|---|
| as_printed, recall | +0.204 (+0.132 to +0.279) | +0.204 (+0.130 to +0.279) | +0.200 (+0.127 to +0.275) | +0.200 (+0.126 to +0.276) |
| as_printed, precision | +0.253 (+0.172 to +0.334) | +0.254 (+0.172 to +0.335) | +0.250 (+0.169 to +0.331) | +0.251 (+0.169 to +0.332) |
| corrected, recall | +0.237 (+0.166 to +0.309) | +0.237 (+0.167 to +0.309) | +0.233 (+0.162 to +0.305) | +0.234 (+0.163 to +0.306) |
| corrected, precision | +0.289 (+0.215 to +0.362) | +0.291 (+0.216 to +0.364) | +0.286 (+0.210 to +0.360) | +0.287 (+0.212 to +0.361) |
| reprints_right, recall | +0.093 (+0.003 to +0.181) | +0.092 (+0.002 to +0.181) | +0.089 (+0.000 to +0.177) | +0.089 (-0.001 to +0.178) |
| reprints_right, precision | +0.157 (+0.087 to +0.228) | +0.157 (+0.087 to +0.228) | +0.154 (+0.084 to +0.225) | +0.154 (+0.084 to +0.226) |
| reprints_repeats_right, recall | +0.054 (-0.029 to +0.141) | +0.041 (-0.044 to +0.131) | +0.051 (-0.033 to +0.138) | +0.038 (-0.047 to +0.128) |
| reprints_repeats_right, precision | +0.120 (+0.059 to +0.184) | +0.106 (+0.041 to +0.174) | +0.117 (+0.056 to +0.181) | +0.103 (+0.037 to +0.171) |
| as_printed: CatLog; RGF (recall / precision) | 0.952 / 0.967; 0.748 / 0.714 | 0.952 / 0.971; 0.748 / 0.717 | 0.952 / 0.967; 0.752 / 0.717 | 0.952 / 0.971; 0.752 / 0.720 |
| as_printed: reference values | 1367 | 1373 | 1367 | 1373 |
| corrected: reference values | 1385 | 1390 | 1385 | 1390 |
| reprints_right: reference values | 1521 | 1528 | 1520 | 1527 |
| reprints_repeats_right: reference values | 1616 | 1643 | 1615 | 1642 |

What-if (post hoc): under reprints_repeats_right the fix lets in {'catlog': 5, 'rgf': 22} values, among them RGF's repeats of one printed value, each a second copy of a value already in the reference. With only those kept at the registered merge (both fixes otherwise; {'catlog': 5, 'rgf': 2} let in, reference 1622): CatLog minus RGF recall +0.051 (-0.033 to +0.138), precision +0.117 (+0.055 to +0.181).

## The page check, both fixed: details

Misread values corrected: {'curation': 15, 'catlog': 0, 'rgf': 6}. Of those judged at another scale, with the judge's right value equal to the new reading: 14 still disputed now count as measured here ({'curation': 13, 'rgf': 1}), and 4 now agree across all three readings and leave the check ({'rgf': 2, 'curation': 2}).

Verdicts now: {'curation': {'measured_here_at_this_scale': 186, 'measured_here_other_scale': 75, 'repeat_of_one_printed_value': 81, 'credited_to_earlier_work': 135, 'as_printed_but_misprint': 12, 'not_this_metric': 8, 'not_found_in_paper': 4}, 'catlog': {'measured_here_at_this_scale': 233, 'corrected_misprint': 38, 'as_printed_but_misprint': 1}, 'rgf': {'measured_here_other_scale': 97, 'measured_here_at_this_scale': 65, 'not_found_in_paper': 8, 'as_printed_but_misprint': 8, 'corrected_misprint': 7, 'not_this_metric': 22, 'credited_to_earlier_work': 19, 'repeat_of_one_printed_value': 34}}.

| View | CatLog | RGF | CatLog minus RGF: recall | precision |
|---|---|---|---|---|
| as_printed | 0.952 / 0.971 | 0.752 / 0.720 | +0.200 (+0.126 to +0.276) | +0.251 (+0.169 to +0.332) |
| corrected | 0.967 / 0.999 | 0.733 / 0.711 | +0.234 (+0.163 to +0.306) | +0.287 (+0.212 to +0.361) |
| reprints_right | 0.856 / 0.971 | 0.767 / 0.817 | +0.089 (-0.001 to +0.178) | +0.154 (+0.084 to +0.226) |
| reprints_repeats_right | 0.796 / 0.971 | 0.758 / 0.868 | +0.038 (-0.047 to +0.128) | +0.103 (+0.037 to +0.171) |

## F6, post hoc: the 15 papers in EnzyExtract's fine-tuning set

Against the curation, CatLog minus RGF without them and with only them is in the table above. Papers whose checked values include a wrong number (another scale, not this metric, not in the paper), RGF against CatLog:

| Papers | Registered | Misreads fixed |
|---|---|---|
| all (79) | 17 against 0, sign test P = 1.5e-05 | 17 against 0, P = 1.5e-05 |
| without finetuning papers (64) | 11 against 0, sign test P = 0.00098 | 11 against 0, P = 0.00098 |
| finetuning papers only (15) | 6 against 0, sign test P = 0.031 | 6 against 0, P = 0.031 |

The 15: 10029307, 10514486, 10564758, 10671479, 10714990, 10801893, 11278915, 11279139, 11322958, 11336650, 11382747, 11415449, 11707391, 11820932, 11880657.
