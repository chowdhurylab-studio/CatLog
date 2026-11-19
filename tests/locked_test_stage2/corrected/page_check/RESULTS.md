# Stage 2, page check of the disputed values: every source against the corrected reference (post hoc)

Rules: CHECK_PLAN.md. Papers checked: 63 of the 63 with a value the curation, CatLog and the run do not all three agree on (part 1: 33 of 33; part 2: 30 of 30). Values checked: {'curation': 501, 'catlog': 272, 'rgf': 260}.

## What the checked values are

| Verdict | Curation | CatLog | EnzyExtract run |
|---|---|---|---|
| measured here at this scale | 186 | 233 | 65 |
| measured here other scale | 75 | 0 | 97 |
| as printed but misprint | 12 | 1 | 8 |
| corrected misprint | 0 | 38 | 7 |
| repeat of one printed value | 81 | 0 | 34 |
| not this metric | 8 | 0 | 22 |
| credited to earlier work | 135 | 0 | 19 |
| not found in paper | 4 | 0 | 8 |
| cannot decide | 0 | 0 | 0 |

kcat only: curation: {'repeat_of_one_printed_value': 42, 'credited_to_earlier_work': 33, 'as_printed_but_misprint': 12, 'measured_here_at_this_scale': 36, 'measured_here_other_scale': 21}; catlog: {'measured_here_at_this_scale': 80, 'corrected_misprint': 20}; rgf: {'as_printed_but_misprint': 7, 'measured_here_at_this_scale': 7, 'not_this_metric': 7, 'measured_here_other_scale': 33, 'repeat_of_one_printed_value': 29, 'not_found_in_paper': 3}.
Second agent on 6 papers: 67 values, the same verdict on 67, the same right-or-not on 67.

## kcat, a misprinted scale counts as printed: complete

| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision | Against the curation list |
|---|---|---|---|---|---|
| CatLog | 0.920 (0.834-0.982) | 0.945 (0.850-1.000) |  |  | 0.696, 0.727 |
| Plain read (Opus 5.5) | 0.979 (0.952-0.997) | 0.989 (0.975-1.000) | -0.059 (-0.145 to -0.003) | -0.044 (-0.134 to +0.014) | 0.743, 0.763 |
| EnzyExtract full pipeline (RGF) | 0.707 (0.575-0.833) | 0.624 (0.493-0.779) | +0.213 (+0.046 to +0.375) | +0.321 (+0.122 to +0.483) | 0.890, 0.798 |
| EnzyExtract run 4o-05 | 0.726 (0.594-0.855) | 0.661 (0.527-0.803) | +0.194 (+0.024 to +0.352) | +0.284 (+0.099 to +0.445) | 0.830, 0.768 |
| EnzyExtract run 4o-mini | 0.636 (0.508-0.770) | 0.629 (0.489-0.771) | +0.285 (+0.105 to +0.445) | +0.316 (+0.125 to +0.488) | 0.694, 0.697 |
| EnzyExtract run 4o-mini_Rx | 0.487 (0.371-0.629) | 0.581 (0.451-0.723) | +0.434 (+0.260 to +0.576) | +0.364 (+0.186 to +0.524) | 0.461, 0.559 |
| EnzyExtract run 4o-mini_xG | 0.625 (0.500-0.761) | 0.671 (0.538-0.800) | +0.295 (+0.117 to +0.455) | +0.274 (+0.105 to +0.439) | 0.665, 0.726 |
| EnzyExtract run RxF | 0.601 (0.456-0.739) | 0.704 (0.577-0.816) | +0.319 (+0.139 to +0.492) | +0.241 (+0.082 to +0.393) | 0.599, 0.713 |
| EnzyExtract run gemini | 0.665 (0.514-0.805) | 0.725 (0.592-0.843) | +0.255 (+0.125 to +0.403) | +0.221 (+0.071 to +0.375) | 0.757, 0.838 |
| EnzyExtract run sonnet37 | 0.713 (0.585-0.848) | 0.751 (0.627-0.872) | +0.207 (+0.033 to +0.358) | +0.195 (+0.025 to +0.342) | 0.723, 0.773 |
| EnzyExtract run xGF | 0.707 (0.572-0.838) | 0.633 (0.485-0.797) | +0.213 (+0.041 to +0.380) | +0.312 (+0.105 to +0.488) | 0.887, 0.807 |
| EnzyExtract database | 0.362 (0.213-0.519) | 0.735 (0.585-0.926) | +0.559 (+0.396 to +0.715) | +0.210 (-0.023 to +0.382) | 0.395, 0.816 |
| BRENDA 2026.1 | 0.069 (0.020-0.138) | 0.684 (0.386-0.974) | +0.851 (+0.740 to +0.937) | +0.261 (-0.064 to +0.601) | 0.068, 0.684 |

## kcat, a misprinted scale counts as corrected: complete

| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision | Against the curation list |
|---|---|---|---|---|---|
| CatLog | 0.971 (0.943-0.992) | 1.000 (1.000-1.000) |  |  | 0.696, 0.727 |
| Plain read (Opus 5.5) | 0.926 (0.833-0.989) | 0.938 (0.845-0.997) | +0.045 (-0.013 to +0.140) | +0.062 (+0.003 to +0.155) | 0.743, 0.763 |
| EnzyExtract full pipeline (RGF) | 0.655 (0.515-0.791) | 0.580 (0.450-0.736) | +0.316 (+0.175 to +0.464) | +0.420 (+0.268 to +0.548) | 0.890, 0.798 |
| EnzyExtract run 4o-05 | 0.674 (0.532-0.811) | 0.615 (0.480-0.759) | +0.297 (+0.156 to +0.443) | +0.385 (+0.238 to +0.522) | 0.830, 0.768 |
| EnzyExtract run 4o-mini | 0.584 (0.453-0.721) | 0.579 (0.436-0.730) | +0.387 (+0.244 to +0.526) | +0.421 (+0.273 to +0.560) | 0.694, 0.697 |
| EnzyExtract run 4o-mini_Rx | 0.456 (0.339-0.599) | 0.546 (0.418-0.687) | +0.515 (+0.366 to +0.637) | +0.454 (+0.312 to +0.586) | 0.461, 0.559 |
| EnzyExtract run 4o-mini_xG | 0.578 (0.448-0.718) | 0.623 (0.486-0.758) | +0.393 (+0.245 to +0.530) | +0.377 (+0.241 to +0.514) | 0.665, 0.726 |
| EnzyExtract run RxF | 0.549 (0.402-0.693) | 0.645 (0.506-0.768) | +0.422 (+0.277 to +0.572) | +0.355 (+0.231 to +0.489) | 0.599, 0.713 |
| EnzyExtract run gemini | 0.650 (0.499-0.790) | 0.710 (0.576-0.830) | +0.321 (+0.183 to +0.471) | +0.290 (+0.172 to +0.427) | 0.757, 0.838 |
| EnzyExtract run sonnet37 | 0.660 (0.528-0.803) | 0.697 (0.568-0.829) | +0.310 (+0.170 to +0.444) | +0.303 (+0.174 to +0.431) | 0.723, 0.773 |
| EnzyExtract run xGF | 0.655 (0.514-0.793) | 0.588 (0.442-0.751) | +0.316 (+0.171 to +0.464) | +0.412 (+0.249 to +0.557) | 0.887, 0.807 |
| EnzyExtract database | 0.347 (0.200-0.505) | 0.708 (0.563-0.902) | +0.623 (+0.470 to +0.771) | +0.292 (+0.093 to +0.437) | 0.395, 0.816 |
| BRENDA 2026.1 | 0.058 (0.014-0.123) | 0.579 (0.277-0.895) | +0.912 (+0.845 to +0.961) | +0.421 (+0.056 to +0.750) | 0.068, 0.684 |

## Km, a misprinted scale counts as printed: complete

| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision | Against the curation list |
|---|---|---|---|---|---|
| CatLog | 0.961 (0.927-0.986) | 0.998 (0.995-1.000) |  |  | 0.787, 0.906 |
| Plain read (Opus 5.5) | 0.981 (0.967-0.992) | 0.967 (0.943-0.986) | -0.019 (-0.052 to +0.000) | +0.032 (+0.013 to +0.056) | 0.816, 0.892 |
| EnzyExtract full pipeline (RGF) | 0.835 (0.755-0.904) | 0.781 (0.695-0.859) | +0.126 (+0.052 to +0.209) | +0.217 (+0.140 to +0.303) | 0.816, 0.846 |
| EnzyExtract run 4o-05 | 0.813 (0.724-0.889) | 0.740 (0.645-0.828) | +0.149 (+0.063 to +0.244) | +0.259 (+0.172 to +0.352) | 0.808, 0.815 |
| EnzyExtract run 4o-mini | 0.719 (0.629-0.805) | 0.783 (0.699-0.858) | +0.242 (+0.149 to +0.338) | +0.215 (+0.142 to +0.298) | 0.669, 0.808 |
| EnzyExtract run 4o-mini_Rx | 0.530 (0.452-0.614) | 0.814 (0.739-0.880) | +0.431 (+0.340 to +0.516) | +0.184 (+0.117 to +0.260) | 0.487, 0.829 |
| EnzyExtract run 4o-mini_xG | 0.530 (0.432-0.628) | 0.610 (0.498-0.715) | +0.431 (+0.328 to +0.532) | +0.389 (+0.284 to +0.498) | 0.501, 0.639 |
| EnzyExtract run RxF | 0.761 (0.684-0.834) | 0.797 (0.714-0.872) | +0.200 (+0.126 to +0.278) | +0.201 (+0.125 to +0.286) | 0.703, 0.816 |
| EnzyExtract run gemini | 0.763 (0.669-0.849) | 0.731 (0.643-0.813) | +0.199 (+0.105 to +0.298) | +0.268 (+0.185 to +0.354) | 0.736, 0.782 |
| EnzyExtract run sonnet37 | 0.840 (0.756-0.912) | 0.887 (0.809-0.951) | +0.121 (+0.041 to +0.207) | +0.111 (+0.048 to +0.191) | 0.771, 0.903 |
| EnzyExtract run xGF | 0.696 (0.589-0.796) | 0.617 (0.513-0.717) | +0.265 (+0.160 to +0.377) | +0.382 (+0.281 to +0.484) | 0.695, 0.682 |
| EnzyExtract database | 0.195 (0.100-0.306) | 0.733 (0.590-0.872) | +0.766 (+0.655 to +0.864) | +0.265 (+0.127 to +0.407) | 0.201, 0.836 |
| BRENDA 2026.1 | 0.643 (0.558-0.725) | 0.861 (0.786-0.922) | +0.318 (+0.228 to +0.409) | +0.137 (+0.076 to +0.213) | 0.625, 0.929 |

## Km, a misprinted scale counts as corrected: complete

| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision | Against the curation list |
|---|---|---|---|---|---|
| CatLog | 0.961 (0.927-0.986) | 0.998 (0.995-1.000) |  |  | 0.787, 0.906 |
| Plain read (Opus 5.5) | 0.981 (0.967-0.992) | 0.967 (0.943-0.986) | -0.019 (-0.052 to +0.000) | +0.032 (+0.013 to +0.056) | 0.816, 0.892 |
| EnzyExtract full pipeline (RGF) | 0.835 (0.755-0.904) | 0.781 (0.695-0.859) | +0.126 (+0.052 to +0.209) | +0.217 (+0.140 to +0.303) | 0.816, 0.846 |
| EnzyExtract run 4o-05 | 0.813 (0.724-0.889) | 0.740 (0.645-0.828) | +0.149 (+0.063 to +0.244) | +0.259 (+0.172 to +0.352) | 0.808, 0.815 |
| EnzyExtract run 4o-mini | 0.719 (0.629-0.805) | 0.783 (0.699-0.858) | +0.242 (+0.149 to +0.338) | +0.215 (+0.142 to +0.298) | 0.669, 0.808 |
| EnzyExtract run 4o-mini_Rx | 0.530 (0.452-0.614) | 0.814 (0.739-0.880) | +0.431 (+0.340 to +0.516) | +0.184 (+0.117 to +0.260) | 0.487, 0.829 |
| EnzyExtract run 4o-mini_xG | 0.530 (0.432-0.628) | 0.610 (0.498-0.715) | +0.431 (+0.328 to +0.532) | +0.389 (+0.284 to +0.498) | 0.501, 0.639 |
| EnzyExtract run RxF | 0.761 (0.684-0.834) | 0.797 (0.714-0.872) | +0.200 (+0.126 to +0.278) | +0.201 (+0.125 to +0.286) | 0.703, 0.816 |
| EnzyExtract run gemini | 0.763 (0.669-0.849) | 0.731 (0.643-0.813) | +0.199 (+0.105 to +0.298) | +0.268 (+0.185 to +0.354) | 0.736, 0.782 |
| EnzyExtract run sonnet37 | 0.840 (0.756-0.912) | 0.887 (0.809-0.951) | +0.121 (+0.041 to +0.207) | +0.111 (+0.048 to +0.191) | 0.771, 0.903 |
| EnzyExtract run xGF | 0.696 (0.589-0.796) | 0.617 (0.513-0.717) | +0.265 (+0.160 to +0.377) | +0.382 (+0.281 to +0.484) | 0.695, 0.682 |
| EnzyExtract database | 0.195 (0.100-0.306) | 0.733 (0.590-0.872) | +0.766 (+0.655 to +0.864) | +0.265 (+0.127 to +0.407) | 0.201, 0.836 |
| BRENDA 2026.1 | 0.643 (0.558-0.725) | 0.861 (0.786-0.922) | +0.318 (+0.228 to +0.409) | +0.137 (+0.076 to +0.213) | 0.625, 0.929 |

## kcat/Km, a misprinted scale counts as printed: complete

| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision | Against the curation list |
|---|---|---|---|---|---|
| CatLog | 0.968 (0.938-0.992) | 0.953 (0.889-1.000) |  |  | 0.744, 0.698 |
| Plain read (Opus 5.5) | 0.960 (0.911-0.995) | 0.883 (0.771-0.986) | +0.008 (-0.025 to +0.056) | +0.070 (+0.009 to +0.162) | 0.744, 0.652 |
| EnzyExtract full pipeline (RGF) | 0.659 (0.511-0.798) | 0.722 (0.592-0.837) | +0.310 (+0.161 to +0.465) | +0.231 (+0.100 to +0.381) | 0.758, 0.791 |
| EnzyExtract run 4o-05 | 0.698 (0.548-0.839) | 0.739 (0.616-0.847) | +0.270 (+0.125 to +0.428) | +0.214 (+0.087 to +0.357) | 0.719, 0.725 |
| EnzyExtract run 4o-mini | 0.561 (0.426-0.702) | 0.541 (0.401-0.682) | +0.407 (+0.264 to +0.544) | +0.412 (+0.265 to +0.562) | 0.594, 0.546 |
| EnzyExtract run 4o-mini_Rx | 0.354 (0.251-0.476) | 0.412 (0.282-0.555) | +0.614 (+0.477 to +0.731) | +0.541 (+0.393 to +0.683) | 0.419, 0.465 |
| EnzyExtract run 4o-mini_xG | 0.484 (0.346-0.636) | 0.483 (0.346-0.623) | +0.484 (+0.325 to +0.627) | +0.470 (+0.333 to +0.615) | 0.550, 0.522 |
| EnzyExtract run RxF | 0.521 (0.369-0.676) | 0.573 (0.418-0.728) | +0.447 (+0.290 to +0.601) | +0.380 (+0.210 to +0.556) | 0.558, 0.584 |
| EnzyExtract run gemini | 0.278 (0.167-0.420) | 0.571 (0.429-0.716) | +0.690 (+0.554 to +0.799) | +0.382 (+0.231 to +0.539) | 0.386, 0.755 |
| EnzyExtract run sonnet37 | 0.738 (0.599-0.873) | 0.821 (0.691-0.931) | +0.230 (+0.096 to +0.367) | +0.133 (+0.008 to +0.276) | 0.647, 0.685 |
| EnzyExtract run xGF | 0.587 (0.435-0.744) | 0.643 (0.474-0.813) | +0.381 (+0.219 to +0.536) | +0.310 (+0.127 to +0.495) | 0.719, 0.751 |
| EnzyExtract database | 0.161 (0.064-0.283) | 0.656 (0.391-0.892) | +0.807 (+0.676 to +0.914) | +0.297 (+0.046 to +0.586) | 0.225, 0.871 |
| BRENDA 2026.1 | 0.034 (0.000-0.087) | 0.812 (0.500-1.000) | +0.934 (+0.877 to +0.978) | +0.141 (-0.092 to +0.475) | 0.028, 0.625 |

## kcat/Km, a misprinted scale counts as corrected: complete

| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision | Against the curation list |
|---|---|---|---|---|---|
| CatLog | 0.972 (0.943-0.995) | 0.997 (0.991-1.000) |  |  | 0.744, 0.698 |
| Plain read (Opus 5.5) | 0.944 (0.862-0.995) | 0.905 (0.793-0.987) | +0.028 (-0.021 to +0.110) | +0.092 (+0.012 to +0.204) | 0.744, 0.652 |
| EnzyExtract full pipeline (RGF) | 0.647 (0.507-0.787) | 0.739 (0.608-0.854) | +0.325 (+0.178 to +0.473) | +0.258 (+0.146 to +0.391) | 0.758, 0.791 |
| EnzyExtract run 4o-05 | 0.685 (0.543-0.822) | 0.756 (0.632-0.860) | +0.287 (+0.145 to +0.435) | +0.241 (+0.138 to +0.368) | 0.719, 0.725 |
| EnzyExtract run 4o-mini | 0.561 (0.424-0.707) | 0.564 (0.419-0.707) | +0.411 (+0.261 to +0.550) | +0.434 (+0.291 to +0.576) | 0.594, 0.546 |
| EnzyExtract run 4o-mini_Rx | 0.338 (0.233-0.464) | 0.409 (0.279-0.552) | +0.635 (+0.493 to +0.752) | +0.588 (+0.448 to +0.720) | 0.419, 0.465 |
| EnzyExtract run 4o-mini_xG | 0.482 (0.344-0.637) | 0.501 (0.362-0.643) | +0.490 (+0.326 to +0.636) | +0.496 (+0.355 to +0.639) | 0.550, 0.522 |
| EnzyExtract run RxF | 0.515 (0.371-0.661) | 0.590 (0.431-0.748) | +0.457 (+0.307 to +0.604) | +0.407 (+0.254 to +0.567) | 0.558, 0.584 |
| EnzyExtract run gemini | 0.282 (0.166-0.428) | 0.603 (0.446-0.757) | +0.690 (+0.548 to +0.804) | +0.394 (+0.243 to +0.554) | 0.386, 0.755 |
| EnzyExtract run sonnet37 | 0.723 (0.592-0.854) | 0.838 (0.707-0.944) | +0.249 (+0.118 to +0.379) | +0.159 (+0.055 to +0.290) | 0.647, 0.685 |
| EnzyExtract run xGF | 0.579 (0.429-0.739) | 0.661 (0.487-0.831) | +0.393 (+0.228 to +0.546) | +0.337 (+0.166 to +0.512) | 0.719, 0.751 |
| EnzyExtract database | 0.152 (0.058-0.272) | 0.645 (0.378-0.880) | +0.820 (+0.690 to +0.922) | +0.352 (+0.116 to +0.630) | 0.225, 0.871 |
| BRENDA 2026.1 | 0.033 (0.000-0.084) | 0.812 (0.500-1.000) | +0.939 (+0.883 to +0.981) | +0.185 (-0.007 to +0.500) | 0.028, 0.625 |

## all, a misprinted scale counts as printed: complete

| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision | Against the curation list |
|---|---|---|---|---|---|
| CatLog | 0.952 (0.922-0.976) | 0.971 (0.933-0.999) |  |  | 0.752, 0.798 |
| Plain read (Opus 5.5) | 0.975 (0.957-0.989) | 0.948 (0.913-0.979) | -0.023 (-0.043 to -0.007) | +0.023 (-0.004 to +0.054) | 0.779, 0.788 |
| EnzyExtract full pipeline (RGF) | 0.752 (0.685-0.815) | 0.720 (0.645-0.795) | +0.200 (+0.126 to +0.276) | +0.251 (+0.169 to +0.332) | 0.821, 0.819 |
| EnzyExtract run 4o-05 | 0.757 (0.677-0.831) | 0.717 (0.641-0.791) | +0.194 (+0.112 to +0.281) | +0.254 (+0.167 to +0.341) | 0.791, 0.779 |
| EnzyExtract run 4o-mini | 0.653 (0.570-0.736) | 0.669 (0.590-0.747) | +0.299 (+0.206 to +0.392) | +0.302 (+0.214 to +0.392) | 0.657, 0.700 |
| EnzyExtract run 4o-mini_Rx | 0.470 (0.395-0.553) | 0.618 (0.540-0.703) | +0.482 (+0.392 to +0.564) | +0.353 (+0.263 to +0.439) | 0.463, 0.634 |
| EnzyExtract run 4o-mini_xG | 0.543 (0.456-0.635) | 0.589 (0.503-0.677) | +0.409 (+0.308 to +0.505) | +0.382 (+0.290 to +0.474) | 0.557, 0.628 |
| EnzyExtract run RxF | 0.651 (0.571-0.734) | 0.712 (0.640-0.782) | +0.301 (+0.211 to +0.389) | +0.259 (+0.176 to +0.342) | 0.639, 0.726 |
| EnzyExtract run gemini | 0.602 (0.529-0.680) | 0.704 (0.633-0.771) | +0.350 (+0.269 to +0.426) | +0.267 (+0.187 to +0.346) | 0.653, 0.794 |
| EnzyExtract run sonnet37 | 0.777 (0.687-0.859) | 0.832 (0.759-0.898) | +0.175 (+0.088 to +0.267) | +0.139 (+0.063 to +0.220) | 0.727, 0.809 |
| EnzyExtract run xGF | 0.669 (0.580-0.754) | 0.628 (0.530-0.728) | +0.283 (+0.189 to +0.381) | +0.343 (+0.235 to +0.451) | 0.753, 0.734 |
| EnzyExtract database | 0.232 (0.131-0.345) | 0.718 (0.606-0.854) | +0.720 (+0.607 to +0.825) | +0.253 (+0.107 to +0.370) | 0.259, 0.835 |
| BRENDA 2026.1 | 0.318 (0.271-0.375) | 0.847 (0.774-0.910) | +0.634 (+0.573 to +0.684) | +0.124 (+0.048 to +0.205) | 0.326, 0.901 |

## all, a misprinted scale counts as corrected: complete

| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision | Against the curation list |
|---|---|---|---|---|---|
| CatLog | 0.967 (0.945-0.984) | 0.999 (0.996-1.000) |  |  | 0.752, 0.798 |
| Plain read (Opus 5.5) | 0.955 (0.907-0.986) | 0.941 (0.890-0.980) | +0.012 (-0.023 to +0.062) | +0.057 (+0.019 to +0.109) | 0.779, 0.788 |
| EnzyExtract full pipeline (RGF) | 0.733 (0.668-0.799) | 0.711 (0.636-0.785) | +0.234 (+0.163 to +0.306) | +0.287 (+0.212 to +0.361) | 0.821, 0.819 |
| EnzyExtract run 4o-05 | 0.739 (0.661-0.813) | 0.708 (0.631-0.782) | +0.228 (+0.150 to +0.310) | +0.290 (+0.217 to +0.366) | 0.791, 0.779 |
| EnzyExtract run 4o-mini | 0.637 (0.554-0.722) | 0.661 (0.581-0.741) | +0.329 (+0.240 to +0.417) | +0.337 (+0.258 to +0.418) | 0.657, 0.700 |
| EnzyExtract run 4o-mini_Rx | 0.455 (0.378-0.544) | 0.607 (0.527-0.693) | +0.512 (+0.418 to +0.594) | +0.392 (+0.308 to +0.473) | 0.463, 0.634 |
| EnzyExtract run 4o-mini_xG | 0.529 (0.441-0.622) | 0.581 (0.496-0.668) | +0.437 (+0.341 to +0.530) | +0.418 (+0.334 to +0.502) | 0.557, 0.628 |
| EnzyExtract run RxF | 0.634 (0.553-0.718) | 0.701 (0.630-0.771) | +0.333 (+0.248 to +0.416) | +0.297 (+0.228 to +0.369) | 0.639, 0.726 |
| EnzyExtract run gemini | 0.596 (0.521-0.673) | 0.705 (0.631-0.775) | +0.371 (+0.292 to +0.445) | +0.294 (+0.225 to +0.366) | 0.653, 0.794 |
| EnzyExtract run sonnet37 | 0.758 (0.672-0.841) | 0.822 (0.749-0.888) | +0.209 (+0.125 to +0.294) | +0.177 (+0.108 to +0.248) | 0.727, 0.809 |
| EnzyExtract run xGF | 0.652 (0.565-0.736) | 0.619 (0.522-0.718) | +0.315 (+0.228 to +0.406) | +0.380 (+0.281 to +0.476) | 0.753, 0.734 |
| EnzyExtract database | 0.224 (0.124-0.337) | 0.704 (0.594-0.836) | +0.742 (+0.628 to +0.844) | +0.294 (+0.158 to +0.404) | 0.259, 0.835 |
| BRENDA 2026.1 | 0.312 (0.264-0.369) | 0.839 (0.766-0.903) | +0.655 (+0.595 to +0.707) | +0.159 (+0.095 to +0.233) | 0.326, 0.901 |

Reference values by where they come from: {'as_printed': {'curation': 1125, 'catlog': 234, 'rgf': 14}, 'corrected': {'curation': 1113, 'catlog': 271, 'rgf': 6}, 'reprints_right': {'curation': 1260, 'catlog': 234, 'rgf': 33}, 'reprints_repeats_right': {'curation': 1341, 'catlog': 234, 'rgf': 67}}; per metric: kcat {'as_printed': 376, 'corrected': 377, 'reprints_right': 409, 'reprints_repeats_right': 480} (the curation has 382); Km {'as_printed': 619, 'corrected': 619, 'reprints_right': 710, 'reprints_repeats_right': 739} (the curation has 686); kcat/Km {'as_printed': 378, 'corrected': 394, 'reprints_right': 408, 'reprints_repeats_right': 423} (the curation has 360).
Read with care: post hoc; one agent per value (a second on a sample), no planted errors; the checkers are Claude models, as are CatLog's readers, and each value's page and words are on file for a person to check; only the curation, CatLog and RGF were checked, so the precision of the plain read and the other runs is a lower bound; a value all three readings agree on was not checked.
