# Locked set, unseen papers read once by each (CatLog as frozen on 9 November 2026): the values the two sources differ on, and a sample of the rest, judged blind with each record's full details (2026-11-11 12:53:35 -0600)

Papers: 83 analysed of 119 listed (left out before judging: {'refused (plain)': 12, 'catlog rule_broken': 7, 'refused (catlog)': 17}; nothing left to judge: 0).
Judge check: passed: decoys caught 105 of 105, the first two judges agree on 0.965 of the disputed claims (0.993 of all).

| | Plain read | CatLog |
|---|---|---|
| Values | 1473 | 1400 |
| Judged | 678 | 605 |
| Agreed, not judged | 795 | 795 |
| Wrong found | 15 | 34 |
| Wrong found per 1,000 (95% interval) | 10.18 (in 4 of 83 papers: too few for an interval) | 24.29 (in 2 of 83 papers: too few for an interval) |
| Papers with a wrong value found, per 100 (exact 95%) | 4.8 (1.3-11.9) | 2.4 (0.3-8.4) |
| Same, on papers where the source stored a value | 4.9 of 82 | 2.4 of 82 |
| Agreed pairs sampled: wrong | 0 of 500 (exact 0.00-0.74%) | 0 of 500 (exact 0.00-0.74%) |
| Per 1,000 with the sample scaled to the unsampled pairs | 10.18 | 24.29 |
| Per 1,000 at the sample's upper limit | 14.15 | 28.46 |
| Cannot decide | 0 | 0 |
| Per 1,000, cannot-decide as wrong | 10.18 | 24.29 |
| Per 1,000, 200 values per paper at most | 10.18 | 24.29 |
| Largest paper's share of wrong | 0.4 | 0.853 |
| Supported values only the other stored (misses) | 1 | 87 |

The rate with the sample scaled resamples papers only; it does not carry the sample's own uncertainty, which the exact line gives.

Papers wrong in one source only: plain 4, CatLog 2.
Plain minus CatLog, wrong per 1,000: -63.2 to 17.2; papers with a wrong value per 100: -3.6 to 8.4 (paper-level bootstrap, B 10000).
Kinds (plain): wrong_metric 9, not_measured_here 6
Kinds (catlog): wrong_scale 34
Papers read by claude-opus-5-5: 83.

Judges: decoys called an error j1 105/105, j2 105/105; kappa on real claims 0.894; third judge on 10 real claims.
Sampled claims judged: 1000 ({'supported': 1000}).


## The set, what was left out, and limits

Set: the draw's order (locked_draw.txt, seed 20261109): its first 100 papers with a usable read from both sides; 119 papers of the draw laid down for both sides, 83 analysed.
Left out before the set was full (each place taken by a later paper of the draw): plain {'refused (plain)': 12}; CatLog {'refused (catlog)': 26, 'catlog rule_broken': 7, 'catlog failed': 3}.
Read past the target, not judged: 0 papers; left out after the set was full: 0.
CatLog's models (the kept rows of the analysed papers): reader {'claude-opus-5-5': 1450}, verifier {'claude-opus-5-5': 1450}: all claude-opus-5-5; papers left out before the set was full because an agent of their kept launch ran on another model, or a kept row is stamped with one: 0 (after the set was full, not counted: 0). The plain reads' models, by paper: {'claude-opus-5-5': 83}.
Decoys caught by kind (the gate's decoys): {'x1000': [52, 52], 'x60': [53, 53]}; with their twin in the chunk: 8 of 8; made from a paper's lone claims (no agreeing or identity-suspect value to change; outside the gate, since a lone claim may itself be a slip whose 1000-fold or 60-fold copy is the printed value): 0 of 0; by base: {'agreeing_sampled': [1, 1], 'agreeing_unsampled': [97, 97], 'identity_suspect': [7, 7]}.
Read with care: a record's shape shows its source (CatLog's details join up to four fields: location, construct, conditions and metric note; the plain read's two: location and conditions); an agreeing value shows as two claims with one number, so a lone claim is a disputed value or a decoy; CatLog's side is its frozen first pass (reader, independent verifier, code conversion and checks: catlog.py add), not its catalogue (no audit, database check, sweep or re-read after it).

## Agreement with the EnzyExtract manual curation (secondary, not judged)

Pre-registered condition (PREREGISTRATION.md "Secondary": used only if its code is written and committed before triage; otherwise dropped, and the report says so): met. Its code (the definitions score_locked.CURATION_CODE names) was first committed in 546f5588f292 at 2026-11-11T04:03:06-06:00; triage ran at 2026-11-11 11:58:38 -0600; this file as committed then: 546f5588f292; the kit's HEAD: f3e2a20e1290.
Papers: the set's papers the curation covers (gold set enzyextract or both in holdout_374.tsv; for both, this curation alone): 79 of 83 ({'enzyextract': 79}); not covered: {'cosci': 4}; covered with no row in the curation: 0 (they count with no curation value). The whole set, whatever the judging has reached. The pre-registration places this secondary on the drawn papers the curation covers (111 of the 119 drawn); only the set's are scored, since the values the judging used (values.json) are the set's alone. Of those 111: in the set 79, left out 32, read past the target 0, never laid down 0.
The curation's values on them: 1428 scored, 98 not scored (a bound or a cell CatLog's units code cannot read: kept, never matched).
Each source's values as the judging took them, matched to the curation's by the head-to-head's matcher (per paper and metric, one to one, most pairs first, closest description second): two numbers in catalog units match when they differ by at most 1.5% of the larger, or by at most 5e-07 (the head-to-head's floor for its gold's rounding to 6 decimals, kept as the matcher is: below 3.3e-05 the tolerance is wider than 1.5%). Recall is the share of the curation's scored values the source holds; precision is the share of the source's values the curation holds.

| | Plain read | CatLog | CatLog minus plain |
|---|---|---|---|
| Values on the covered papers | 1431 | 1362 | |
| Matched to a curation value | 1106 | 1068 | |
| Recall (95% interval), matched of the curation's scored values | 0.775 (0.706-0.844), 1106 of 1428 | 0.748 (0.679-0.815), 1068 of 1428 | -0.027 (-0.047 to -0.011) |
| Precision (95% interval), matched of the source's values | 0.773 (0.702-0.844), 1106 of 1431 | 0.784 (0.715-0.853), 1068 of 1362 | +0.011 (-0.007 to +0.035) |
| kcat: recall, precision | 0.749, 0.765 | 0.702, 0.728 | -0.047, -0.036 |
| Km: recall, precision | 0.824, 0.883 | 0.796, 0.900 | -0.028, +0.017 |
| kcat/Km: recall, precision | 0.708, 0.612 | 0.706, 0.656 | -0.003, +0.045 |

The curation's scored values by who matched them: both 1055, plain only 51, CatLog only 13, neither 309.
Left after matching: the curation's scored values a source did not match, plain 322, CatLog 360; the source's values the curation did not match, plain 325, CatLog 294. Among them, pairs with a similar description (the head-to-head's desc_pairs: per paper and metric, one to one, a description score of 3.2 or more of 5: the variant up to 2, substrate words 1.5, enzyme 0.7, temperature 0.4, pH 0.4), plain 54, CatLog 67: often the same measurement with another number, sometimes two measurements of the paper (a value the source missed beside one the curation lacks, such as another substrate of a series at the same temperature and pH). Of these pairs, the same variant with the same substrate words: plain 51, CatLog 58; the same variant with some substrate words in common: plain 3, CatLog 1; the rest (another variant, or no substrate word in common): plain 0, CatLog 8. Otherwise unmatched (no similar description on the other side): the curation's values, plain 268, CatLog 293; the source's values, plain 271, CatLog 227.
Intervals: paper-clustered bootstrap, B 10000, seed 20261031; the difference draws the same papers for both sources.
Read with care: the curation is another group's manual reading of these papers, not ground truth. These disagreements are reported, never judged (each is listed in curation.json): one may be either side's slip or a convention the two apply differently, and a source's value the curation did not match is not wrong by that alone.
