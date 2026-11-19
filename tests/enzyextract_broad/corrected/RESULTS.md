# The broad test, scored again with the scoring errors fixed (post hoc)

Registered: `build.py score` (run/results.json), reproduced exactly here with every fix switched off. Corrected: F5 and F2 fixed, bounds rounded once (F10). Every correction was found after the result, by an independent audit (writing/research/comparison_audit_20261118/enzyextract.md).

Notes: F5 {'F5 values now agreed': 8, 'F5 values read again': 11}; F2 {'F5 values now agreed': 0, 'F2 EnzyExtract values out of scope': 273, 'F2 of them judged right (primary rule)': 270}; both {'F5 values now agreed': 8, 'F2 EnzyExtract values out of scope': 273, 'F2 of them judged right (primary rule)': 270, 'F5 values read again': 11}; the audit's F2 rule {'F5 values now agreed': 8, 'F2 EnzyExtract values out of scope': 270, 'F2 of them judged right (primary rule)': 270, 'F5 values read again': 11}.

## printed_here (primary)

| | Registered | F5 only | F2 only | Corrected (F5 and F2) |
|---|---|---|---|---|
| Papers with a wrong number | CatLog 2, EnzyExtract 80; 78:0, P = 6.6e-24 | CatLog 2, EnzyExtract 79; 77:0, P = 1.3e-23 | CatLog 2, EnzyExtract 79; 77:0, P = 1.3e-23 | CatLog 2, EnzyExtract 78; 76:0, P = 2.6e-23 |
| all recall | 0.877 / 0.866; +0.011 (-0.049 to +0.069) | 0.877 / 0.867; +0.011 (-0.050 to +0.069) | 0.901 / 0.862; +0.039 (-0.020 to +0.095) | 0.901 / 0.863; +0.038 (-0.021 to +0.094) |
| all precision | 0.981 / 0.910; +0.071 (+0.042 to +0.100) | 0.981 / 0.911; +0.070 (+0.041 to +0.099) | 0.981 / 0.908; +0.073 (+0.044 to +0.103) | 0.981 / 0.909; +0.073 (+0.043 to +0.102) |
| kcat recall | 0.896 / 0.861; +0.035 (-0.045 to +0.120) | 0.896 / 0.861; +0.035 (-0.045 to +0.120) | 0.896 / 0.861; +0.035 (-0.045 to +0.120) | 0.896 / 0.861; +0.035 (-0.045 to +0.120) |
| kcat precision | 0.997 / 0.914; +0.083 (+0.038 to +0.138) | 0.997 / 0.914; +0.083 (+0.038 to +0.138) | 0.997 / 0.914; +0.083 (+0.038 to +0.138) | 0.997 / 0.914; +0.083 (+0.038 to +0.138) |
| Km recall | 0.848 / 0.921; -0.073 (-0.132 to -0.017) | 0.848 / 0.921; -0.073 (-0.132 to -0.017) | 0.898 / 0.916; -0.018 (-0.076 to +0.036) | 0.898 / 0.916; -0.018 (-0.076 to +0.036) |
| Km precision | 0.990 / 0.958; +0.032 (+0.005 to +0.059) | 0.990 / 0.958; +0.032 (+0.005 to +0.059) | 0.990 / 0.956; +0.035 (+0.007 to +0.063) | 0.990 / 0.956; +0.035 (+0.007 to +0.063) |
| kcat/Km recall | 0.890 / 0.799; +0.091 (+0.013 to +0.169) | 0.890 / 0.802; +0.089 (+0.010 to +0.167) | 0.912 / 0.794; +0.118 (+0.040 to +0.194) | 0.912 / 0.797; +0.115 (+0.037 to +0.191) |
| kcat/Km precision | 0.950 / 0.840; +0.109 (-0.006 to +0.200) | 0.950 / 0.844; +0.106 (-0.009 to +0.197) | 0.950 / 0.837; +0.113 (-0.003 to +0.204) | 0.950 / 0.840; +0.110 (-0.007 to +0.201) |
| Values: CatLog not right, missed; EnzyExtract not right, missed | 170, 1252; 870, 1368 | 170, 1252; 862, 1360 | 170, 982; 867, 1368 | 170, 982; 859, 1360 |
| Wrong numbers: CatLog, EnzyExtract | 129, 792 | 129, 784 | 129, 789 | 129, 781 |

## measured_here

| | Registered | F5 only | F2 only | Corrected (F5 and F2) |
|---|---|---|---|---|
| Papers with a wrong number | CatLog 2, EnzyExtract 80; 78:0, P = 6.6e-24 | CatLog 2, EnzyExtract 79; 77:0, P = 1.3e-23 | CatLog 2, EnzyExtract 79; 77:0, P = 1.3e-23 | CatLog 2, EnzyExtract 78; 76:0, P = 2.6e-23 |
| all recall | 0.934 / 0.857; +0.076 (+0.024 to +0.127) | 0.934 / 0.858; +0.076 (+0.023 to +0.127) | 0.961 / 0.853; +0.108 (+0.057 to +0.157) | 0.961 / 0.854; +0.107 (+0.056 to +0.156) |
| all precision | 0.981 / 0.781; +0.200 (+0.151 to +0.257) | 0.981 / 0.782; +0.200 (+0.150 to +0.256) | 0.981 / 0.776; +0.206 (+0.155 to +0.264) | 0.981 / 0.776; +0.205 (+0.154 to +0.263) |
| kcat recall | 0.956 / 0.852; +0.105 (+0.032 to +0.184) | 0.956 / 0.852; +0.105 (+0.032 to +0.184) | 0.956 / 0.852; +0.105 (+0.032 to +0.184) | 0.956 / 0.852; +0.105 (+0.032 to +0.184) |
| kcat precision | 0.997 / 0.749; +0.248 (+0.175 to +0.323) | 0.997 / 0.749; +0.248 (+0.175 to +0.323) | 0.997 / 0.749; +0.248 (+0.175 to +0.323) | 0.997 / 0.749; +0.248 (+0.175 to +0.323) |
| Km recall | 0.908 / 0.915; -0.007 (-0.057 to +0.040) | 0.908 / 0.915; -0.007 (-0.057 to +0.040) | 0.965 / 0.910; +0.056 (+0.011 to +0.099) | 0.965 / 0.910; +0.056 (+0.011 to +0.099) |
| Km precision | 0.990 / 0.829; +0.161 (+0.105 to +0.228) | 0.990 / 0.829; +0.161 (+0.105 to +0.228) | 0.990 / 0.820; +0.171 (+0.111 to +0.242) | 0.990 / 0.820; +0.171 (+0.111 to +0.242) |
| kcat/Km recall | 0.937 / 0.788; +0.148 (+0.074 to +0.222) | 0.937 / 0.791; +0.145 (+0.071 to +0.218) | 0.960 / 0.783; +0.178 (+0.104 to +0.250) | 0.960 / 0.786; +0.175 (+0.101 to +0.246) |
| kcat/Km precision | 0.950 / 0.761; +0.189 (+0.070 to +0.290) | 0.950 / 0.764; +0.186 (+0.068 to +0.287) | 0.950 / 0.755; +0.194 (+0.075 to +0.296) | 0.950 / 0.758; +0.191 (+0.072 to +0.294) |
| Values: CatLog not right, missed; EnzyExtract not right, missed | 170, 636; 2300, 1368 | 170, 636; 2292, 1360 | 170, 366; 2297, 1368 | 170, 366; 2289, 1360 |
| Wrong numbers: CatLog, EnzyExtract | 129, 792 | 129, 784 | 129, 789 | 129, 781 |

## printed_here, misprint corrected

| | Registered | F5 only | F2 only | Corrected (F5 and F2) |
|---|---|---|---|---|
| Papers with a wrong number | CatLog 2, EnzyExtract 80; 78:0, P = 6.6e-24 | CatLog 2, EnzyExtract 79; 77:0, P = 1.3e-23 | CatLog 2, EnzyExtract 79; 77:0, P = 1.3e-23 | CatLog 2, EnzyExtract 78; 76:0, P = 2.6e-23 |
| all recall | 0.871 / 0.874; -0.003 (-0.060 to +0.052) | 0.871 / 0.875; -0.004 (-0.061 to +0.051) | 0.895 / 0.870; +0.024 (-0.033 to +0.079) | 0.895 / 0.871; +0.024 (-0.033 to +0.078) |
| all precision | 0.972 / 0.916; +0.056 (-0.008 to +0.102) | 0.972 / 0.917; +0.055 (-0.009 to +0.101) | 0.972 / 0.914; +0.058 (-0.007 to +0.105) | 0.972 / 0.915; +0.057 (-0.008 to +0.104) |
| kcat recall | 0.878 / 0.889; -0.011 (-0.083 to +0.057) | 0.878 / 0.889; -0.011 (-0.083 to +0.057) | 0.878 / 0.889; -0.011 (-0.083 to +0.057) | 0.878 / 0.889; -0.011 (-0.083 to +0.057) |
| kcat precision | 0.964 / 0.931; +0.033 (-0.050 to +0.095) | 0.964 / 0.931; +0.033 (-0.050 to +0.095) | 0.964 / 0.931; +0.033 (-0.050 to +0.095) | 0.964 / 0.931; +0.033 (-0.050 to +0.095) |
| Km recall | 0.849 / 0.913; -0.064 (-0.126 to -0.007) | 0.849 / 0.913; -0.064 (-0.126 to -0.007) | 0.899 / 0.908; -0.010 (-0.069 to +0.046) | 0.899 / 0.908; -0.010 (-0.069 to +0.046) |
| Km precision | 1.000 / 0.958; +0.042 (+0.024 to +0.062) | 1.000 / 0.958; +0.042 (+0.024 to +0.062) | 1.000 / 0.956; +0.044 (+0.025 to +0.066) | 1.000 / 0.956; +0.044 (+0.025 to +0.066) |
| kcat/Km recall | 0.890 / 0.799; +0.091 (+0.012 to +0.169) | 0.890 / 0.802; +0.088 (+0.009 to +0.166) | 0.912 / 0.795; +0.117 (+0.040 to +0.193) | 0.912 / 0.798; +0.114 (+0.037 to +0.190) |
| kcat/Km precision | 0.949 / 0.840; +0.108 (-0.007 to +0.199) | 0.949 / 0.843; +0.105 (-0.010 to +0.196) | 0.949 / 0.837; +0.112 (-0.004 to +0.203) | 0.949 / 0.840; +0.109 (-0.007 to +0.200) |
| Values: CatLog not right, missed; EnzyExtract not right, missed | 255, 1312; 810, 1283 | 255, 1312; 802, 1275 | 255, 1042; 807, 1283 | 255, 1042; 799, 1275 |
| Wrong numbers: CatLog, EnzyExtract | 129, 792 | 129, 784 | 129, 789 | 129, 781 |

## measured_here, misprint corrected

| | Registered | F5 only | F2 only | Corrected (F5 and F2) |
|---|---|---|---|---|
| Papers with a wrong number | CatLog 2, EnzyExtract 80; 78:0, P = 6.6e-24 | CatLog 2, EnzyExtract 79; 77:0, P = 1.3e-23 | CatLog 2, EnzyExtract 79; 77:0, P = 1.3e-23 | CatLog 2, EnzyExtract 78; 76:0, P = 2.6e-23 |
| all recall | 0.927 / 0.866; +0.061 (+0.012 to +0.111) | 0.927 / 0.866; +0.061 (+0.011 to +0.110) | 0.954 / 0.862; +0.092 (+0.043 to +0.141) | 0.954 / 0.863; +0.092 (+0.042 to +0.140) |
| all precision | 0.972 / 0.787; +0.185 (+0.115 to +0.254) | 0.972 / 0.788; +0.184 (+0.114 to +0.253) | 0.972 / 0.781; +0.191 (+0.119 to +0.261) | 0.972 / 0.782; +0.190 (+0.119 to +0.260) |
| kcat recall | 0.938 / 0.882; +0.057 (-0.014 to +0.119) | 0.938 / 0.882; +0.057 (-0.014 to +0.119) | 0.938 / 0.882; +0.057 (-0.014 to +0.119) | 0.938 / 0.882; +0.057 (-0.014 to +0.119) |
| kcat precision | 0.964 / 0.764; +0.200 (+0.113 to +0.283) | 0.964 / 0.764; +0.200 (+0.113 to +0.283) | 0.964 / 0.764; +0.200 (+0.113 to +0.283) | 0.964 / 0.764; +0.200 (+0.113 to +0.283) |
| Km recall | 0.908 / 0.907; +0.001 (-0.051 to +0.049) | 0.908 / 0.907; +0.001 (-0.051 to +0.049) | 0.965 / 0.901; +0.064 (+0.017 to +0.108) | 0.965 / 0.901; +0.064 (+0.017 to +0.108) |
| Km precision | 1.000 / 0.829; +0.171 (+0.114 to +0.236) | 1.000 / 0.829; +0.171 (+0.114 to +0.236) | 1.000 / 0.820; +0.180 (+0.121 to +0.249) | 1.000 / 0.820; +0.180 (+0.121 to +0.249) |
| kcat/Km recall | 0.937 / 0.789; +0.148 (+0.074 to +0.221) | 0.937 / 0.792; +0.145 (+0.071 to +0.218) | 0.961 / 0.784; +0.177 (+0.104 to +0.249) | 0.961 / 0.787; +0.174 (+0.101 to +0.245) |
| kcat/Km precision | 0.949 / 0.760; +0.188 (+0.070 to +0.288) | 0.949 / 0.763; +0.185 (+0.068 to +0.286) | 0.949 / 0.755; +0.194 (+0.074 to +0.295) | 0.949 / 0.758; +0.191 (+0.072 to +0.292) |
| Values: CatLog not right, missed; EnzyExtract not right, missed | 255, 696; 2240, 1283 | 255, 696; 2232, 1275 | 255, 426; 2237, 1283 | 255, 426; 2229, 1275 |
| Wrong numbers: CatLog, EnzyExtract | 129, 792 | 129, 784 | 129, 789 | 129, 781 |

## Registered secondaries left unreported (F13), primary rule

| Papers | Registered | Corrected |
|---|---|---|
| pdf papers (187) | wrong-number papers 2 against 54; recall +0.029 (-0.048 to +0.104); precision +0.075 (+0.031 to +0.121) | 2 against 52; recall +0.060 (-0.016 to +0.133); precision +0.077 (+0.032 to +0.123) |
| xml only papers (113) | wrong-number papers 0 against 26; recall -0.012 (-0.108 to +0.076); precision +0.066 (+0.039 to +0.097) | 0 against 26; recall +0.010 (-0.086 to +0.097); precision +0.068 (+0.040 to +0.099) |

EnzyExtract values by how they were read, with their verdicts: registered {"catlog_units": {"agreed": 7248, "as_printed_but_misprint": 18, "corrected_misprint": 78, "credited_to_earlier_work": 605, "measured_here_at_this_scale": 606, "measured_here_other_scale": 392, "not_found_in_paper": 93, "not_this_metric": 261, "repeat_of_one_printed_value": 811, "values": 10112, "wrong_numbers": 746}, "catlog_units_after_notation_fix": {"agreed": 255, "credited_to_earlier_work": 9, "measured_here_at_this_scale": 1, "measured_here_other_scale": 2, "not_found_in_paper": 2, "not_this_metric": 3, "repeat_of_one_printed_value": 3, "values": 275, "wrong_numbers": 7}, "database_number": {"agreed": 66, "credited_to_earlier_work": 2, "measured_here_at_this_scale": 11, "measured_here_other_scale": 33, "not_this_metric": 6, "values": 118, "wrong_numbers": 39}}; corrected {"catlog_units": {"agreed": 7256, "as_printed_but_misprint": 18, "corrected_misprint": 78, "credited_to_earlier_work": 605, "measured_here_at_this_scale": 339, "measured_here_other_scale": 384, "not_found_in_paper": 93, "not_this_metric": 259, "out of scope": 269, "repeat_of_one_printed_value": 811, "values": 10112, "wrong_numbers": 736}, "catlog_units_after_notation_fix": {"agreed": 255, "credited_to_earlier_work": 9, "measured_here_at_this_scale": 1, "measured_here_other_scale": 1, "not_found_in_paper": 2, "not_this_metric": 3, "out of scope": 1, "repeat_of_one_printed_value": 3, "values": 275, "wrong_numbers": 6}, "database_number": {"agreed": 66, "credited_to_earlier_work": 2, "measured_here_at_this_scale": 8, "measured_here_other_scale": 33, "not_this_metric": 6, "out of scope": 3, "values": 118, "wrong_numbers": 39}}

## Post hoc, without 12723605 (F4)

| | Registered | Corrected |
|---|---|---|
| printed_here (primary) | wrong-number papers 1 against 79; recall -0.000 (-0.058 to +0.054); precision +0.082 (+0.060 to +0.105) | 1 against 77; recall +0.027 (-0.030 to +0.080); precision +0.083 (+0.061 to +0.107) |
| printed_here, misprint corrected | wrong-number papers 1 against 79; recall +0.002 (-0.055 to +0.057); precision +0.084 (+0.062 to +0.108) | 1 against 77; recall +0.029 (-0.027 to +0.083); precision +0.085 (+0.063 to +0.110) |

Second judge: {'values': 546, 'same_verdict': 544, 'same_wrong_number_call': 546}.
