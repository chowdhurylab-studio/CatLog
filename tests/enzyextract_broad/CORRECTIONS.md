# Corrections to the scoring of both EnzyExtract tests (18 November 2026, found after the results)

**Why.**
- Two independent audits found calculation errors:
  - `writing/research/comparison_audit_20261118/enzyextract.md`: findings F1, F2, F5, F6, F10 and F13, and F4's
    sensitivity;
  - `databases.md` in the same folder: its first finding, a registered comparison with BRENDA reported nowhere.
- A second independent recount (`writing/research/enzyextract_recount_20261118/`) checked every published number.
- The recounts of the second stage found one more scoring error, in how the page check builds its reference (the
  reference merge, below).

**How the numbers are made.**
- Every correction is a scoring error fixed in code after the result. The registered scorers and outputs stand
  unchanged.
- Each corrected scorer first reproduces the registered numbers exactly, and stops otherwise.
- Corrections, registered endpoints that were never reported, and what-ifs are kept apart, in the headings below
  and in `corrections.json` (field `kind`).

## Corrected headline numbers

**Broad test** (300 papers, primary rule, CatLog minus EnzyExtract, 95% intervals):

| Endpoint | Registered | Corrected (F5 and F2) |
|---|---|---|
| Papers holding a wrong number | CatLog 2, EnzyExtract 80; 78 against 0 on one side only, *P* = 6.6 × 10⁻²⁴ | CatLog 2, EnzyExtract 78; 76 against 0, *P* = 2.6 × 10⁻²³ |
| Recall | 0.877 against 0.866, +0.011 (−0.049 to +0.069) | 0.901 against 0.863, +0.038 (−0.021 to +0.094): no difference claimed |
| Precision | 0.981 against 0.910, +0.071 (+0.042 to +0.100) | 0.981 against 0.909, +0.073 (+0.043 to +0.102) |
| *K*m recall | −0.073 (−0.132 to −0.017) | −0.018 (−0.076 to +0.036): no difference |
| EnzyExtract's wrong numbers | 792 (427 at another scale, 270 of another quantity, 95 not in the paper) | 781 (418, 268, 95) |
| Values not right, and missed | CatLog 170 and 1,252; EnzyExtract 870 and 1,368 | CatLog 170 and 982; EnzyExtract 859 and 1,360 |

**Second stage** (79 papers, against the EnzyExtract group's curation; corrected = every cell read as written; in the
page check, the misread cells read as written and the reference merge fixed):

| Endpoint | Registered | Corrected |
|---|---|---|
| CatLog minus RGF, recall | −0.078 (−0.165 to +0.015) | −0.060 (−0.153 to +0.037) |
| CatLog minus RGF, precision | −0.030 (−0.100 to +0.043) | +0.003 (−0.073 to +0.079) |
| *k*cat recall | −0.194 (−0.337 to −0.033): EnzyExtract higher | −0.145 (−0.315 to +0.059): no difference |
| On RGF's 78 papers with output, recall | −0.091 (−0.176 to −0.003): EnzyExtract higher | −0.073 (−0.164 to +0.021): no difference |
| *K*m precision | +0.060 (+0.007 to +0.119): CatLog higher | +0.061 (+0.008 to +0.120): CatLog higher |
| CatLog minus BRENDA, precision (registered, never reported) | −0.114 (−0.191 to −0.040); without the two misprint papers −0.093 (−0.162 to −0.023) | −0.077 (−0.152 to −0.011); without them −0.055 (−0.118 to +0.006) |
| CatLog minus BRENDA, recall | +0.416 (+0.345 to +0.480) | +0.438 (+0.366 to +0.503) |
| Page check: the curation's values at another scale; RGF's | 90 of 505; 100 of 263 | 75 of 501; 97 of 260 |
| Page check, as printed: CatLog; RGF | 0.952/0.967; 0.748/0.714 | 0.952/0.971; 0.752/0.720 |
| Page check, credited and repeated values counted as right (footnote 8's last two numbers): CatLog minus RGF, recall; precision | +0.054 (−0.029 to +0.141); +0.120 (+0.059 to +0.184) | +0.038 (−0.047 to +0.128); +0.103 (+0.037 to +0.171) |

**The BRENDA comparison.** BRENDA's precision against the curation is higher than CatLog's.
- BRENDA holds few values for these papers: recall 0.316 against CatLog's 0.754 once read as written.
- Most of the values it does hold match the curation, which records values as printed.
- Without the two papers whose misprinted headers CatLog corrected, the corrected difference no longer excludes zero.

## 79 or 80: settled from the strings themselves (F5)

The second recount kept 80, because it did not test these strings.
- Each string below has an exponent inside its ± part. The registered reading applied that exponent to the value: for
  example, one string (TheData.parquet row 120625) became 2.15 × 10⁷ mM⁻¹ s⁻¹, beyond any diffusion limit.
- In all 8 strings judged at another scale, the judge's right value is the string read without the error term, and
  CatLog stores that same number. So the 8 are our parser's errors, not EnzyExtract's. Read correctly, they become
  agreed values.
- 32107312 held no other wrong number, so it leaves EnzyExtract's side: **79 with F5 alone**.
- 23436726 keeps three values judged of another quantity, a verdict about the quantity rather than the scale.
- The strings are in the last table of this file.

## The scope fix (F2): which values go out

**Both versions take a value out of scope when CatLog stores the same number for the paper on a record without a
*k*cat.**
- The audit and the second recount take out only EnzyExtract's values judged right: 270 values.
  - With F5 this gives 79 papers (77:0, *P* = 1.3 × 10⁻²³).
  - Recall is +0.038 (−0.021 to +0.094) and precision +0.073 (+0.043 to +0.103).
  - The second recount, without F5, gets +0.039 (−0.020 to +0.095) and +0.074 (+0.044 to +0.103), the same as this
    file's F2 alone.
- The corrected scorer takes out every such value, whatever its verdict: 273 values. The 3 extra are wrong numbers:
  - two in 16403023, a *K*m derived from an IC50 and its *k*cat/*K*m, judged of another quantity;
  - one in 12105228, another substrate's cell, judged at another scale.
- CatLog's copies of the same three numbers are out of scope and were never judged.
- A scope that depends on the verdict is applied unevenly again. The rule that does not depend on it is also the more
  lenient to EnzyExtract.
- Both versions agree on every conclusion. They differ only in the paper count: 78 against 79.

## The page check's reference merge (second stage)

**What was wrong.**
- The page check scores each reading against a reference. The reference starts from the curation's values that all
  three readings agree on or that were judged right.
- Each reading's values judged right are then matched one to one against the reference so far, so that one
  measurement counts once, and only those left unmatched are added.
- That match did not ask whose value a reference value already was. A reading's right value could merge into a
  curation value that the same reading already matches through another of its values.
- The score matches one to one, so the reading's two values then competed for one reference value, and the value
  judged right counted against its own reading.
- This happened to 5 of CatLog's values and 4 of RGF's as printed, and to 5 and 25 when repeats count as right. The
  curation's own repeats judged right entered the reference separately all along.

**The fix.** A reading's value judged right may merge only into a reference value that the same reading does not
already hold, that is, not into a curation value that reading matches.
- `paper/evidence/locked_test_20261109/stage2/score_corrected.py` applies it around the registered
  `score_checked.py`, which stays unchanged.
- With the fix off it reproduces the registered page check exactly, all four rules included.
- With the fix on it gives the earlier recount's numbers for this rule (160 of 160, both readings, to that recount's
  6 decimals).

**Effect** (CatLog minus RGF; F1 = the misread cells read as written):

| Rule | | Registered | Merge fixed only | F1 only | Both fixed |
|---|---|---|---|---|---|
| As printed (the check's own view) | recall | +0.204 (+0.132 to +0.279) | +0.204 (+0.130 to +0.279) | +0.200 (+0.127 to +0.275) | +0.200 (+0.126 to +0.276) |
|  | precision | +0.253 (+0.172 to +0.334) | +0.254 (+0.172 to +0.335) | +0.250 (+0.169 to +0.331) | +0.251 (+0.169 to +0.332) |
| Misprints corrected | recall | +0.237 (+0.166 to +0.309) | +0.237 (+0.167 to +0.309) | +0.233 (+0.162 to +0.305) | +0.234 (+0.163 to +0.306) |
|  | precision | +0.289 (+0.215 to +0.362) | +0.291 (+0.216 to +0.364) | +0.286 (+0.210 to +0.360) | +0.287 (+0.212 to +0.361) |
| Credited to earlier work counted as right | recall | +0.093 (+0.003 to +0.181) | +0.092 (+0.002 to +0.181) | +0.089 (+0.000 to +0.177) | +0.089 (−0.001 to +0.178) |
|  | precision | +0.157 (+0.087 to +0.228) | +0.157 (+0.087 to +0.228) | +0.154 (+0.084 to +0.225) | +0.154 (+0.084 to +0.226) |
| Also repeats counted as right (footnote 8's last two numbers) | recall | +0.054 (−0.029 to +0.141) | +0.041 (−0.044 to +0.131) | +0.051 (−0.033 to +0.138) | +0.038 (−0.047 to +0.128) |
|  | precision | +0.120 (+0.059 to +0.184) | +0.106 (+0.041 to +0.174) | +0.117 (+0.056 to +0.181) | +0.103 (+0.037 to +0.171) |

- The reference grows by 6 values as printed (1,367 to 1,373) and by 27 when repeats count as right (1,615 to 1,642
  with F1). Of the 4 RGF values as printed, 1 enters; the other 3 now merge into values RGF does not hold.
- As printed, CatLog's precision becomes 0.971 (registered 0.967) and RGF's 0.720 (0.714). CatLog's recall stays 0.952.
- No conclusion changes. Under the most generous rule the recall interval still includes zero, and the precision
  interval still excludes it.
- Under "credited to earlier work counted as right" (not printed) the recall lower bound becomes −0.001.
- Under the most generous rule, 20 of the 27 values the fix lets in are RGF repeats of one printed value. Each becomes
  a second reference copy of a value already there, and CatLog, which lists that value once, can match only one copy.
  - The registered builder already adds the curation's 81 repeats and 14 of RGF's that way, so this comes with the
    rule, not the fix.
  - Kept at the registered merge, those 20 would give +0.051 (−0.033 to +0.138) and +0.117 (+0.055 to +0.181)
    (what-ifs, below).
- Recounted by a separate agent: every score agrees (below).

## Claims in the paper that change
1. **Broad test, *K*m recall (F2).** Drop "CatLog's *K*m recall was lower (−0.073, −0.132 to −0.017)" (results.md:138,
   Table 1 footnote 10). Corrected it is −0.018 (−0.076 to +0.036). "No difference in recall is claimed" stays.
2. **Second stage, *k*cat and the 78 papers (F1).** Drop "EnzyExtract's recall was higher for *k*cat and on its 78
   papers with output" (results.md:146, footnote 7). Both intervals now include zero. "CatLog's precision for *K*m"
   and "no difference ... overall" stay.
3. **The broad test's counts (F5, F2).**
   - results.md:137 and Table 1d: 80 papers become 78 (79 with the audit's scope), and *P* becomes 2.6 × 10⁻²³.
   - Table 1d becomes recall 0.901 and 0.863, precision 0.981 and 0.909 (+0.073, +0.043 to +0.102), and EnzyExtract's
     values 9,418.
   - Under the second rule: +0.107 (+0.056 to +0.156) and +0.205 (+0.154 to +0.263).
   - Footnote 10:
     - reference 9,919;
     - 781 wrong numbers (418, 268, 95);
     - with misprints as corrected, +0.024 (−0.033 to +0.078) and +0.057 (−0.008 to +0.104).
4. **The page check (F1 and the reference merge).** Footnote 8 and results.md:151: 90 at another scale becomes 75,
   and EnzyExtract's 100 becomes 97.
   - 15 of the curation's 90 and 3 of EnzyExtract's 100 were cells our units code misread. Read as written, they
     equal the judges' own right value.
   - Of those, 13 and 1 now count as measured here. The other 2 and 2 agree across all three readings and leave
     the check.
   - Footnote 8's last two numbers, with credited and repeated values counted as right: +0.054 (−0.029 to +0.141)
     and +0.120 (+0.059 to +0.184) become **+0.038 (−0.047 to +0.128) and +0.103 (+0.037 to +0.171)**. F1 alone
     gives +0.051 and +0.117, the merge fix alone +0.041 and +0.106.
   - The merge fix's share of that move comes from 20 RGF repeats it lets in as second copies of values already in
     the reference (the what-ifs below). Either way the recall interval includes zero and the precision interval
     excludes it.
   - The check's own scores, as printed: CatLog 0.952 and 0.971 (precision 0.967 registered), RGF 0.752 and 0.720
     (0.748 and 0.714).
5. **Rounding (F10).** +0.101 is +0.100, +0.150 is +0.151, and −0.009 is −0.008.
6. **Registered but unreported, now reported.**
   - The broad test splits the same way on PDF papers (2 against 52) and XML-only papers (0 against 26) (F13).
   - CatLog minus BRENDA against the curation: precision −0.077 (−0.152 to −0.011), recall +0.438 (+0.366 to +0.503).
7. **F6 (post hoc).** 15 of the second stage's 79 papers are among EnzyExtract's 52 fine-tuning papers. On the other
   64, EnzyExtract's agreement with its curation is higher still (recall −0.135, −0.226 to −0.036). The page check
   still finds RGF with a wrong number in 11 of those 64 papers and CatLog in none.

**Not changed:**
- the broad test's precision lead and the papers-with-a-wrong-number result;
- no difference in recall;
- the second stage's lack of an overall difference, and CatLog's higher *K*m precision;
- the page check's conclusions, and CatLog's recall in it (0.952);
- the second judge (544 of 546);
- RGF as the best of the nine runs.

## What-ifs (post hoc, not corrections; corrected scoring, registered in the table)
- **12723605's 128 *k*cat/*K*m counted right** (the second recount's what-if; an earlier paper prints the *k*cat at
  CatLog's scale):
  - CatLog then holds a wrong number in 1 paper, against 78 (77:0, *P* = 1.3 × 10⁻²³; registered 79:0, *P* = 2⁻⁷⁸).
  - Precision +0.087 (+0.063 to +0.112).
- **Without 12723605 (F4):** 1 against 77. Precision is +0.083 (+0.061 to +0.107), and +0.085 (+0.063 to +0.110)
  with misprints as corrected.
- **EnzyExtract's repeats with no listing that kept its own verdict:** 97 values in 10 groups. One listing per group
  counted right moves recall by −0.001 and precision by less than 0.001.
- **EnzyExtract's unread cells counted as wrong numbers.** These are the cells the judge's prompt calls not this
  metric: bounds, not-detected entries, relative values and per-mass activities.
  - 91 distinct cells in 22 papers give 94 papers (92:0; registered 95).
  - The second recount counts 113 cells with each repeated cell, and gets 96.
  - The plan leaves such cells unscored, which is lenient to EnzyExtract.
- **The audit's and the second recount's scope fix:** above.
- **The page check's most generous rule, with RGF's repeats kept at the registered merge** (the merge recount's
  what-if): footnote 8's last two numbers become +0.051 (−0.033 to +0.138) and +0.117 (+0.055 to +0.181), against
  +0.038 and +0.103 with both fixes. Either way the recall interval includes zero and the precision interval excludes
  it.

## Reconciliation with the second recount (`writing/research/enzyextract_recount_20261118/`)
- **Every published number reproduces exactly**, there and in this file's scorers with the fixes switched off.
- **The one-sided scope.** The same flaw and the same numbers, to the 3 values described above.
- **The three bounds rounded twice.** The same three.
- **Its additions are the what-ifs above,** computed here with the corrected scoring as well: the repeats, the unread
  cells and 12723605 counted right.
- **F5.** It did not test the strings, so its count stays at 80. Settled above: 79 with F5 alone.
- **Two details it notes, left as they are:**
  - In 28005309 one *k*cat/*K*m pair (2.2% apart) is matched only through the matcher's absolute floor of 5 × 10⁻⁷.
    That is one pair.
  - 247 EnzyExtract values in 31 papers are in scope only through a row *k*cat judged a repeat or wrong. That is a
    scope defined on EnzyExtract's own rows; this file defines it through CatLog's records.

## Recounts by independent agents

Each agent wrote its own code from the rules above, apart from the units converter and the matcher, and compared
its numbers with this file's only at the end.

**Broad test** (`corrected/recount_broad.json`).
- **Result:** 2,452 numbers compared, unrounded, and none differs. That covers:
  - every run (registered, F5 alone, F2 alone, both, and the audit's F2);
  - every rule and every constant;
  - the PDF and XML-only split, EnzyExtract's values by how they were read, the run without 12723605, and the
    second judge.
- **Checks first:**
  - its registered run reproduced all 324 numbers of `run/results.json`;
  - its matcher gave the registered pairs in all 300 papers;
  - every disputed value has exactly one verdict.
- **Not recounted:** the what-ifs and the unread cells.
- **What it notes about F2's rule.** None of this changes a conclusion.
  - The rule matches numbers only. In 12105228, EnzyExtract's value for one substrate leaves because CatLog's record
    for another substrate, without a *k*cat, prints the same number. The paper stays on EnzyExtract's list anyway.
  - The rule sees only values whose number CatLog also stores. In 20952389, eight right *K*m values leave scope, but
    two "not in the paper" *K*m values on the same kind of rows stay and count as wrong. So the rule is conservative
    for EnzyExtract's wrong-number count.
  - In 16332250 two equal values tie, and the matcher's description score picks which one leaves. The other choice
    would take the paper off EnzyExtract's list (77 instead of 78).
- **A scope defined on EnzyExtract's own rows was tried and dropped.** A Km or kcat/Km would be out when its row's
  kcat is a repeat, not a kcat, not in the paper, or missing. A row's kcat dropped as an exact copy cannot be told
  apart from a missing one without a further rule.
- **Rounding.** The registered scorer's own printout, `run/RESULTS.md`, rounds 3 places from 4. Eight of its 32
  lines come out wrong, among them CatLog's *K*m precision: 0.991 there, 0.990 rounded once. The paper prints none of
  these eight except the three bounds of F10. Every number here is rounded once.

**Second stage** (`paper/evidence/locked_test_20261109/stage2/corrected/recount_stage2.json`): everything agrees with zero differences.
- **What it reproduced first:** the registered results (1,653 numbers), the page check (3,413) and the four rules
  (5,113). Its disputed values match the judges' task flags.
- **Then, against the corrected files:**
  - the table, 1,634 numbers per reading;
  - the 254 changed cells, cell by cell;
  - the page check (5,970 numbers);
  - the F6 split (38) and the counts (44);
  - the earlier recount's stage2.json (534 numbers, at its rounding).
- **Its points, now fixed:**
  - "18 verdicts read again" counted 4 values that the fix makes agreed by all three readings, which therefore leave
    the check. 14 conversions stay (13 curation, 1 RGF). No number changed.
  - The two *k*cat/*K*m strings of EnzyExtract's released database in 15210695, read as written by the same fix, are
    now listed among the changed cells.
- **Its points, noted here:**
  - **The "reprints right" rule (not printed in the paper).** The corrected recall interval of CatLog minus RGF has a
    lower bound of exactly 0.000 with F1 alone (registered +0.003), and −0.001 with the merge fixed too. So the
    scoring-rules README's "recall lead holds unless both reprints and repeats count as right" holds only as
    registered. The README now says so.
  - **Two older flaws in the page check's reference,** both found by the earlier recount:
    - A value judged right could be absorbed by a reference value its own reading already holds. Now corrected: the
      reference merge, above, recounted below.
    - 12 values of 0 can never be matched. Not corrected here.
  - **Cells in the other runs (Extended Data 9 only) the reader still misses:** a cell whose unit a footnote mark follows
    and a cell whose power of ten lost its caret (two cells of the runs, left out here). None is in the curation, CatLog, the plain reading or RGF.

**The reference merge** (`paper/evidence/locked_test_20261109/stage2/corrected/recount_merge.json`): a third agent
wrote its own reference builder from the rule alone.
- **Checks first:** with the fix off it reproduced, unrounded, the registered page check (3,437 numbers), the four
  rules of `views.json` (5,912) and the page check with F1 alone (6,095).
- **Result:** with the fix on, every score and every reference count agrees under both readings (6,003, 6,095 and
  6,009 numbers compared).
  - Footnote 8's last two numbers: recall +0.0384 (−0.0466 to +0.1280), precision +0.1029 (+0.0373 to +0.1709).
  - The merges the registered builder made into a value the reading already holds: CatLog 5 under every rule; RGF 4,
    3, 5 and 25 (as printed, corrected, credited, and repeats too), under both readings.
- **Its points:**
  - One stored count was named wrong. In the runs with the fix, it was counted against the corrected reference and
    gave RGF 1, 0, 2 and 22. That is the number of values the fix lets in, now stored under that name. No score
    depends on it.
  - No value not judged right gains credit. Merging RGF before CatLog gives the same numbers.
  - With the fix, no value of CatLog's judged right counts against it (5 before). RGF has 6 left, all of value 0:
    the older zero flaw.
  - The 20 repeats under the most generous rule, above. Its what-if, with those 20 kept at the registered merge, is
    computed by the scorer as well (`corrected/checked_whatif_repeats_keep_the_registered_merge/`): the same 18
    numbers and a reference of 1,622.

## What was wrong, and the fix in code
- **F5 (broad test).** "a × 10ⁿ ± b × 10ᵐ unit" was read with the error's exponent applied to the value.
  - Fix: `score_corrected.py` reads such strings without the error term, matches the paper again, and counts a value
    judged at another scale as measured here when the judge's right value equals the new reading.
  - Effect: 11 strings in 2 papers; 8 now agree with CatLog's values.
- **F2 (broad test).** The scope "records that hold a *k*cat" was applied to CatLog only.
  - Fix: `score_corrected.py` takes out of scope every EnzyExtract disputed value equal, one to one within 1.5%, to a
    value CatLog stores on a record without a *k*cat.
  - Effect: 273 values, 270 of them judged right.
- **F10 (broad test).** Bounds were rounded twice. Fix: `score_corrected.py` keeps them unrounded, with the same draws
  as `build.py`.
- **F13 (broad test).** The two registered secondaries, now computed by `score_corrected.py`.
- **F1 (second stage).** The kit's units reading misread 21 curation and RGF cells and left 75 unread.
  - Fix: `paper/evidence/locked_test_20261109/stage2/score_corrected.py`.
    - Table against the curation: every cell is read as written.
    - Page check: only the misreads are fixed, in place, because the judges never saw the unread cells.
  - The four rules of the scoring-rules folder: `paper/evidence/stage2_scoring_rules_20261117/rescore_corrected.py`.
- **The reference merge (second stage's page check).** A reading's value judged right could merge into a curation
  value the same reading already matched.
  - Fix: `paper/evidence/locked_test_20261109/stage2/score_corrected.py` lets it merge only into a reference value
    that the same reading does not hold; `paper/evidence/stage2_scoring_rules_20261117/rescore_corrected.py` keeps
    the four rules with both fixes.
  - Effect: 9 values as printed (5 CatLog, 4 RGF) and 30 when repeats count as right (5, 25). The reference grows by
    6 and 27.
- **Stage 2's registered CatLog minus BRENDA, with and without the misprint papers.** Computed by the same file.
- **F6 and F4 (post hoc).** The split by EnzyExtract's fine-tuning papers, and the scores without 12723605.

## Every number the paper prints about EnzyExtract, and the rest

"Printed" is the text of `writing/manuscript/` at main 9d09b670. "Registered" is what the registered scorers give,
reproduced and rounded once. "Corrected" is what the fixed scorers give. Each row's sources are in `corrections.json`.

### Scoring errors fixed

| Where | What | Printed | Registered (reproduced) | Corrected | Finding | Claim changes |
|---|---|---|---|---|---|---|
| results.md:137; Table 1d (EnzyExtract row) | papers in which EnzyExtract's database holds a wrong number, of 300 | 80 | 80 | 78 | F5, F2 | the count only; the claim stands |
| results.md:137 | papers in which CatLog holds a wrong number | 2 of those 80 | 2 of those 80 | 2 of those 78 | F5, F2 | no |
| results.md:137; Table 1d (difference row) | papers on one side only, and the exact sign test | 78 and 0; P = 6.6 × 10⁻²⁴ | 78 and 0; P = 6.6 × 10^-24 | 76 and 0; P = 2.6 × 10^-23 | F5, F2 | no: smaller, as strong |
| results.md:138; Table 1d | precision, CatLog against EnzyExtract, primary rule | 0.981 against 0.910 (+0.071, +0.042 to +0.101) | 0.981 against 0.910 (+0.071 (+0.042 to +0.100)) | 0.981 against 0.909 (+0.073 (+0.043 to +0.102)) | F2, F5; F10 for the registered upper bound (printed +0.101, is +0.100) | no: CatLog higher |
| results.md:138; Table 1d | recall, CatLog against EnzyExtract, primary rule | +0.011 (−0.049 to +0.069), no difference claimed | 0.877 against 0.866 (+0.011 (-0.049 to +0.069)) | 0.901 against 0.863 (+0.038 (-0.021 to +0.094)) | F2, F5 | no: no difference claimed |
| results.md:138; Table 1, footnote 10 | Km recall, CatLog minus EnzyExtract | −0.073 (−0.132 to −0.017), CatLog lower | -0.073 (-0.132 to -0.017) | -0.018 (-0.076 to +0.036) | F2 | YES: the interval now includes zero; the clause goes |
| not printed (Table 1d by constant) | kcat recall, CatLog minus EnzyExtract | — | +0.035 (-0.045 to +0.120) | +0.035 (-0.045 to +0.120) | F2, F5 | not printed; the audit (F8) asks to give every constant whose interval excludes zero |
| not printed (Table 1d by constant) | kcat precision, CatLog minus EnzyExtract | — | +0.083 (+0.038 to +0.138) | +0.083 (+0.038 to +0.138) | F2, F5 | not printed; the audit (F8) asks to give every constant whose interval excludes zero |
| not printed (Table 1d by constant) | Km precision, CatLog minus EnzyExtract | — | +0.032 (+0.005 to +0.059) | +0.035 (+0.007 to +0.063) | F2, F5 | not printed; the audit (F8) asks to give every constant whose interval excludes zero |
| not printed (Table 1d by constant) | kcat/Km recall, CatLog minus EnzyExtract | — | +0.091 (+0.013 to +0.169) | +0.115 (+0.037 to +0.191) | F2, F5 | not printed; the audit (F8) asks to give every constant whose interval excludes zero |
| not printed (Table 1d by constant) | kcat/Km precision, CatLog minus EnzyExtract | — | +0.109 (-0.006 to +0.200) | +0.110 (-0.007 to +0.201) | F2, F5 | not printed; the audit (F8) asks to give every constant whose interval excludes zero |
| results.md:139; Table 1, footnote 10 | CatLog's wrong numbers, and those in one paper | 129; 128 | 129; 128 | 129; 128 | none | no |
| results.md:140; Table 1, footnote 10 | precision with misprints counted as corrected | +0.056 (−0.009 to +0.102), no difference claimed | +0.056 (-0.008 to +0.102) | +0.057 (-0.008 to +0.104) | F2, F5; F10 for the registered lower bound (printed −0.009, is −0.008) | no |
| Table 1, footnote 10 | recall with misprints counted as corrected | −0.003 (−0.060 to +0.052) | -0.003 (-0.060 to +0.052) | +0.024 (-0.033 to +0.078) | F2, F5 | no |
| Table 1d | CatLog: values compared | 9,107 | 9,107 | 9,107 | none | no |
| Table 1d | EnzyExtract: values compared | 9,691 | 9,691 | 9,418 | F2 | no |
| Table 1d | recall, CatLog and EnzyExtract | 0.877; 0.866 | 0.877; 0.866 | 0.901; 0.863 | F2, F5 | no: no difference claimed |
| Table 1d | precision, CatLog and EnzyExtract | 0.981; 0.910 | 0.981; 0.910 | 0.981; 0.909 | F2, F5 | no |
| Table 1d (second rule) | recall, measured-here rule | +0.076 (+0.024 to +0.127) | +0.076 (+0.024 to +0.127) | +0.107 (+0.056 to +0.156) | F2, F5 | no |
| Table 1d (second rule) | precision, measured-here rule | +0.200 (+0.150 to +0.257) | +0.200 (+0.151 to +0.257) | +0.205 (+0.154 to +0.263) | F2, F5; F10 for the registered lower bound (printed +0.150, is +0.151) | no |
| Table 1, footnote 10 | the reference: values agreed or judged right | 10,189 | 10,189 | 9,919 | F2, F5 | no |
| Table 1, footnote 10 | EnzyExtract's wrong numbers: at another scale, of another quantity, not in the paper | 792: 427, 270, 95 | 792: 427, 270, 95 | 781: 418, 268, 95 | F5 (8 at another scale), F2 (1 at another scale, 2 of another quantity) | no |
| Table 1, footnote 10 | EnzyExtract's values credited to earlier work, and repeats | 616; 814 | 616; 814 | 616; 814 | none | no |
| Methods (broad test) | second judge: papers, values, same verdict | 19; 546; 544 | 19; 546; 544 | 19; 546; 544 | none | no |
| results.md:145; Table 1c; Fig. 3b legend | run_RGF: recall and precision against the curation | 0.819 and 0.816 (Table 1c: 0.819 (0.759 to 0.873), 0.816 (0.743 to 0.883); 1,433 values) | 0.819 (0.759 to 0.873), 0.816 (0.743 to 0.883); 1,433 values | 0.814 (0.754 to 0.867), 0.825 (0.752 to 0.890); 1,459 values | F1 | no (the order of the marks is the same) |
| results.md:145; Table 1c; Fig. 3b legend | catlog: recall and precision against the curation | 0.742 and 0.787 (Table 1c: 0.742 (0.673 to 0.808), 0.787 (0.718 to 0.856); 1,346 values) | 0.742 (0.673 to 0.808), 0.787 (0.718 to 0.856); 1,346 values | 0.754 (0.684 to 0.822), 0.828 (0.756 to 0.893); 1,346 values | F1 | no (the order of the marks is the same) |
| results.md:145; Table 1c; Fig. 3b legend | plain: recall and precision against the curation | 0.768 and 0.777 (Table 1c: 0.768 (0.699 to 0.838), 0.777 (0.706 to 0.849); 1,411 values) | 0.768 (0.699 to 0.838), 0.777 (0.706 to 0.849); 1,411 values | 0.780 (0.710 to 0.849), 0.816 (0.742 to 0.886); 1,411 values | F1 | no (the order of the marks is the same) |
| results.md:145; Table 1c; Fig. 3b legend | enzyextract_db: recall and precision against the curation | Table 1c: 0.259 (0.142 to 0.378), 0.835 (0.731 to 0.948); 443 values | 0.259 (0.142 to 0.378), 0.835 (0.731 to 0.948); 443 values | 0.251 (0.136 to 0.367), 0.835 (0.731 to 0.948); 443 values | F1 | no (the order of the marks is the same) |
| results.md:145; Table 1c; Fig. 3b legend | brenda: recall and precision against the curation | Table 1c: 0.326 (0.274 to 0.385), 0.901 (0.853 to 0.944); 516 values | 0.326 (0.274 to 0.385), 0.901 (0.853 to 0.944); 516 values | 0.316 (0.268 to 0.374), 0.905 (0.857 to 0.948); 516 values | F1 | no (the order of the marks is the same) |
| results.md:145; Table 1, footnote 7 | CatLog minus the plain reading, recall and precision | −0.027 (−0.047 to −0.011); +0.009 (−0.008 to +0.033) | -0.027 (-0.047 to -0.011); +0.009 (-0.008 to +0.033) | -0.026 (-0.046 to -0.010); +0.011 (-0.007 to +0.035) | F1 | no |
| results.md:146; Table 1, footnote 7 | CatLog minus EnzyExtract, recall and precision | −0.078 (−0.165 to +0.015); −0.030 (−0.100 to +0.043) | -0.078 (-0.165 to +0.015); -0.030 (-0.100 to +0.043) | -0.060 (-0.153 to +0.037); +0.003 (-0.073 to +0.079) | F1 | no: no difference claimed |
| results.md:146; Table 1, footnote 7 | kcat recall, CatLog minus EnzyExtract | −0.194 (−0.337 to −0.033), EnzyExtract higher | -0.194 (-0.337 to -0.033) | -0.145 (-0.315 to +0.059) | F1 (19 curation kcat cells of 10514486 left unread) | YES: the interval now includes zero; the clause goes |
| results.md:146; Table 1, footnote 7 | Km precision, CatLog minus EnzyExtract | +0.060 (+0.007 to +0.119), CatLog higher | +0.060 (+0.007 to +0.119) | +0.061 (+0.008 to +0.120) | F1 | no: holds |
| results.md:146; Table 1, footnote 7 | on EnzyExtract's 78 papers with output, recall and precision | −0.091 (−0.176 to −0.003); −0.033 (−0.104 to +0.041) | -0.091 (-0.176 to -0.003); -0.033 (-0.104 to +0.041) | -0.073 (-0.164 to +0.021); +0.001 (-0.075 to +0.076) | F1 | YES: the recall interval now includes zero; the clause goes |
| not printed (stage 2 sensitivity) | without the two misprint papers, recall and precision | — | -0.074 (-0.165 to +0.023); -0.022 (-0.097 to +0.052) | -0.057 (-0.151 to +0.044); +0.012 (-0.066 to +0.088) | F1 | no |
| Fig. 3b legend; Extended Data 9 legend | the curation's scored values, and cells not scored | 1,428; 98 of 1,526 | 1,428; 98 of 1,526 | 1,477; 49 of 1,526 | F1 | the counts only |
| Extended Data 9 legend | curation values per constant (kcat, Km, kcat/Km) | 382, 686, 360 | 382, 686, 360 | 407, 689, 381 | F1 | the counts only |
| Extended Data 9 legend | cells not scored per EnzyExtract run | 49 to 255 | 49 to 255 | 38 to 235 | F1 | the counts only |
| Extended Data 9 legend | without the two misprint papers: papers and values | 77 papers, 1,397 values | 77 papers, 1,397 values | 77 papers, 1,446 values | F1 | the counts only |
| Extended Data 9 legend | the best of the nine runs on both measures | RGF | RGF | RGF (recall), RGF (precision) | F1 | no |
| Extended Data 9 (table) | 4o-05: recall and precision against the curation | — | 0.789, 0.777 | 0.774, 0.787 | F1 | no |
| Extended Data 9 (table) | 4o-mini: recall and precision against the curation | — | 0.655, 0.698 | 0.648, 0.714 | F1 | no |
| Extended Data 9 (table) | 4o-mini_Rx: recall and precision against the curation | — | 0.463, 0.634 | 0.450, 0.637 | F1 | no |
| Extended Data 9 (table) | 4o-mini_xG: recall and precision against the curation | — | 0.557, 0.627 | 0.545, 0.624 | F1 | no |
| Extended Data 9 (table) | RxF: recall and precision against the curation | — | 0.639, 0.726 | 0.632, 0.729 | F1 | no |
| Extended Data 9 (table) | gemini: recall and precision against the curation | — | 0.653, 0.793 | 0.648, 0.801 | F1 | no |
| Extended Data 9 (table) | sonnet37: recall and precision against the curation | — | 0.725, 0.807 | 0.708, 0.810 | F1 | no |
| Extended Data 9 (table) | xGF: recall and precision against the curation | — | 0.751, 0.732 | 0.739, 0.732 | F1 | no |
| results.md:151; Table 1, footnote 8 | the curation's checked values at another scale | 90 (of 505) | 90 (of 505) | 75 (of 501) | F1: 15 were cells the units code misread (the judges' right value is the cell as written); 13 now count as measured here, and 2 agree across all three readings and leave the check | the count only |
| Table 1, footnote 8 | EnzyExtract's checked values at another scale | 100 (of 263) | 100 (of 263) | 97 (of 260) | F1: 3 were misread cells; 1 now counts as measured here, and 2 agree across all three readings and leave the check | the count only |
| results.md:151; Table 1, footnote 8 | the curation's checked values credited to earlier work, and repeats | 135; 81 | 135; 81 | 135; 81 | none | no |
| Table 1, footnote 8; Fig. 3b legend | values checked, and papers | 1,055 values in 63 papers | 1,055 values in 63 papers | 1,055 checked; 1,033 of them still disputed once the misreads are fixed, in 63 papers | F1 | no: 1,055 is what the agents checked |
| Table 1, footnote 8; Fig. 3b legend | the reference: agreed by all three (not checked) plus judged right | 1,367 (923 + 444) | 1,367 (923 + 444) | 1,373 (927 + 446) | F1; reference merge | the split only |
| Table 1, footnote 8; Fig. 3b legend (arrows) | catlog: recall and precision against the checked reference | 0.952 (0.923 to 0.976) and 0.967 (0.925 to 0.998) | 0.952 (0.923 to 0.976) and 0.967 (0.925 to 0.998) | 0.952 (0.922 to 0.976) and 0.971 (0.933 to 0.999) | F1; reference merge | no |
| Table 1, footnote 8; Fig. 3b legend (arrows) | run_RGF: recall and precision against the checked reference | 0.748 (0.682 to 0.811) and 0.714 (0.640 to 0.787) | 0.748 (0.682 to 0.811) and 0.714 (0.640 to 0.787) | 0.752 (0.685 to 0.815) and 0.720 (0.645 to 0.795) | F1; reference merge | no |
| Table 1, footnote 8; Fig. 3b legend | the plain reading's lower bounds | at least 0.974 (0.956 to 0.989); at least 0.944 | 0.974 (0.956 to 0.989); 0.944 | 0.975 (0.957 to 0.989); 0.948 | F1; reference merge | no |
| not printed (page check, as printed) | page check, CatLog minus EnzyExtract, recall; precision (as_printed) | — | +0.204 (+0.132 to +0.279); +0.253 (+0.172 to +0.334) | +0.200 (+0.126 to +0.276); +0.251 (+0.169 to +0.332) | F1; reference merge (both fixed) | no |
| Table 1, footnote 8 (its last two numbers) | page check, CatLog minus EnzyExtract, recall; precision (reprints_repeats_right: credited and repeated values counted as right) | +0.054 (−0.029 to +0.141); +0.120 (+0.059 to +0.184) | +0.054 (-0.029 to +0.141); +0.120 (+0.059 to +0.184) | +0.038 (-0.047 to +0.128); +0.103 (+0.037 to +0.171) | F1; reference merge (both fixed) | the numbers only: the recall interval still includes zero, the precision interval still excludes it |
| Table 1, footnote 8 (the page check's reference) | values judged right that the registered reference merged into a value their own reading already holds, so that they never entered it and counted against their own reading: CatLog; RGF, by rule | — | as_printed 5; 4; corrected 5; 3; reprints_right 5; 5; reprints_repeats_right 5; 25 (the same with the misreads fixed: as_printed 5; 4; corrected 5; 3; reprints_right 5; 5; reprints_repeats_right 5; 25) | none; the values that now enter the reference because of the fix (its growth), both fixes: as_printed 5; 1; corrected 5; 0; reprints_right 5; 2; reprints_repeats_right 5; 22 (the others merge into reference values their reading does not hold) | reference merge: a reading's value judged right may merge only into a reference value that the same reading does not already hold, i.e. not into a curation value that reading matches (the recounts' finding) | the count only |
| not printed (page check, each fix alone) | page check, the reference (as_printed): values | — | 1,367 (registered); 1,367 with the misreads fixed only | 1,373 with the merge fixed only; 1,373 with both | reference merge: a reading's value judged right may merge only into a reference value that the same reading does not already hold, i.e. not into a curation value that reading matches (the recounts' finding); F1 | the count only |
| not printed (page check, each fix alone) | page check, the reference (corrected): values | — | 1,385 (registered); 1,385 with the misreads fixed only | 1,390 with the merge fixed only; 1,390 with both | reference merge: a reading's value judged right may merge only into a reference value that the same reading does not already hold, i.e. not into a curation value that reading matches (the recounts' finding); F1 | the count only |
| not printed (page check, each fix alone) | page check, the reference (reprints_right): values | — | 1,521 (registered); 1,520 with the misreads fixed only | 1,528 with the merge fixed only; 1,527 with both | reference merge: a reading's value judged right may merge only into a reference value that the same reading does not already hold, i.e. not into a curation value that reading matches (the recounts' finding); F1 | the count only |
| not printed (page check, each fix alone) | page check, the reference (reprints_repeats_right): values | — | 1,616 (registered); 1,615 with the misreads fixed only | 1,643 with the merge fixed only; 1,642 with both | reference merge: a reading's value judged right may merge only into a reference value that the same reading does not already hold, i.e. not into a curation value that reading matches (the recounts' finding); F1 | the count only |
| Table 1, footnote 8; Fig. 3b legend (arrows) | page check, CatLog minus EnzyExtract (as_printed), each fix alone: recall; precision | — | +0.204 (+0.132 to +0.279); +0.253 (+0.172 to +0.334) | merge fixed only +0.204 (+0.130 to +0.279); +0.254 (+0.172 to +0.335) / misreads fixed only +0.200 (+0.127 to +0.275); +0.250 (+0.169 to +0.331) / both +0.200 (+0.126 to +0.276); +0.251 (+0.169 to +0.332) | reference merge: a reading's value judged right may merge only into a reference value that the same reading does not already hold, i.e. not into a curation value that reading matches (the recounts' finding); F1 | the split of the two fixes |
| not printed (page check) | page check, CatLog minus EnzyExtract (corrected), each fix alone: recall; precision | — | +0.237 (+0.166 to +0.309); +0.289 (+0.215 to +0.362) | merge fixed only +0.237 (+0.167 to +0.309); +0.291 (+0.216 to +0.364) / misreads fixed only +0.233 (+0.162 to +0.305); +0.286 (+0.210 to +0.360) / both +0.234 (+0.163 to +0.306); +0.287 (+0.212 to +0.361) | reference merge: a reading's value judged right may merge only into a reference value that the same reading does not already hold, i.e. not into a curation value that reading matches (the recounts' finding); F1 | the split of the two fixes |
| not printed (page check) | page check, CatLog minus EnzyExtract (reprints_right), each fix alone: recall; precision | — | +0.093 (+0.003 to +0.181); +0.157 (+0.087 to +0.228) | merge fixed only +0.092 (+0.002 to +0.181); +0.157 (+0.087 to +0.228) / misreads fixed only +0.089 (+0.000 to +0.177); +0.154 (+0.084 to +0.225) / both +0.089 (-0.001 to +0.178); +0.154 (+0.084 to +0.226) | reference merge: a reading's value judged right may merge only into a reference value that the same reading does not already hold, i.e. not into a curation value that reading matches (the recounts' finding); F1 | the split of the two fixes |
| Table 1, footnote 8 | page check, CatLog minus EnzyExtract (reprints_repeats_right), each fix alone: recall; precision | — | +0.054 (-0.029 to +0.141); +0.120 (+0.059 to +0.184) | merge fixed only +0.041 (-0.044 to +0.131); +0.106 (+0.041 to +0.174) / misreads fixed only +0.051 (-0.033 to +0.138); +0.117 (+0.056 to +0.181) / both +0.038 (-0.047 to +0.128); +0.103 (+0.037 to +0.171) | reference merge: a reading's value judged right may merge only into a reference value that the same reading does not already hold, i.e. not into a curation value that reading matches (the recounts' finding); F1 | the split of the two fixes |

### Registered endpoints that were not reported

| Where | What | Printed | Registered (reproduced) | Corrected | Finding | Claim changes |
|---|---|---|---|---|---|---|
| not printed (F13, registered secondary) | pdf papers: wrong-number papers CatLog and EnzyExtract; recall; precision | — | 2 and 54; +0.029 (-0.048 to +0.104); +0.075 (+0.031 to +0.121) | 2 and 52; +0.060 (-0.016 to +0.133); +0.077 (+0.032 to +0.123) | F13 | adds one line: the same held on both kinds of paper |
| not printed (F13, registered secondary) | xml only papers: wrong-number papers CatLog and EnzyExtract; recall; precision | — | 0 and 26; -0.012 (-0.108 to +0.076); +0.066 (+0.039 to +0.097) | 0 and 26; +0.010 (-0.086 to +0.097); +0.068 (+0.040 to +0.099) | F13 | adds one line: the same held on both kinds of paper |
| not printed (stage 2, endpoint 4) | CatLog minus BRENDA against the curation, all: recall; precision | — | +0.416 (+0.345 to +0.480); -0.114 (-0.191 to -0.040) | +0.438 (+0.366 to +0.503); -0.077 (-0.152 to -0.011) | databases audit F1 (unreported); F1 for the correction | adds: BRENDA's precision against the curation is higher than CatLog's, also once read as written |
| not printed (stage 2, endpoint 4) | CatLog minus BRENDA against the curation, kcat: recall; precision | — | +0.628 (+0.500 to +0.758); +0.043 (-0.303 to +0.383) | +0.641 (+0.515 to +0.769); +0.100 (-0.244 to +0.438) | databases audit F1 (unreported); F1 for the correction | adds (by constant) |
| not printed (stage 2, endpoint 4) | CatLog minus BRENDA against the curation, Km: recall; precision | — | +0.162 (+0.069 to +0.251); -0.023 (-0.075 to +0.027) | +0.163 (+0.069 to +0.252); -0.022 (-0.075 to +0.027) | databases audit F1 (unreported); F1 for the correction | adds (by constant) |
| not printed (stage 2, endpoint 4) | CatLog minus BRENDA against the curation, kcat/Km: recall; precision | — | +0.675 (+0.555 to +0.782); +0.034 (-0.450 to +0.709) | +0.719 (+0.598 to +0.825); +0.115 (-0.369 to +0.784) | databases audit F1 (unreported); F1 for the correction | adds (by constant) |
| not printed (stage 2, endpoint 4) | CatLog minus BRENDA without the two misprint papers: recall; precision | — | +0.418 (+0.347 to +0.484); -0.093 (-0.162 to -0.023) | +0.441 (+0.367 to +0.507); -0.055 (-0.118 to +0.006) | databases audit F1 (unreported); F1 for the correction | adds: no longer a difference once read as written |

### What-ifs (post hoc, not corrections)

| Where | What | Printed | Registered (reproduced) | Corrected | Finding | Claim changes |
|---|---|---|---|---|---|---|
| not printed (F4: add after "no precision difference is claimed") | post hoc, without 12723605: precision (printed_here (primary)) | — | +0.082 (+0.060 to +0.105) | +0.083 (+0.061 to +0.107) | F4 (post hoc) | adds: without that paper the precision difference excludes zero under both views |
| not printed (F4: add after "no precision difference is claimed") | post hoc, without 12723605: precision (printed_here, misprint corrected) | — | +0.084 (+0.062 to +0.108) | +0.085 (+0.063 to +0.110) | F4 (post hoc) | adds: without that paper the precision difference excludes zero under both views |
| Table 1, footnote 8 (its last two numbers): what-if | page check, credited and repeated values counted as right, with RGF's repeats of one printed value kept at the registered merge (under this rule the fix lets them in as second copies of values already in the reference): CatLog minus EnzyExtract, recall; precision | — | +0.054 (-0.029 to +0.141); +0.120 (+0.059 to +0.184) | +0.051 (-0.033 to +0.138); +0.117 (+0.055 to +0.181) (both fixes otherwise; with them all +0.038 (-0.047 to +0.128); +0.103 (+0.037 to +0.171)) | what-if (post hoc; the merge recount's): the registered builder already adds the curation's repeats judged right as reference values | no: the recall interval includes zero and the precision interval excludes it either way |
| not printed (F6: add to Table 1, footnote 9, or the Extended Data 9 legend) | the 79 papers in EnzyExtract's 52 fine-tuning papers | — | 15 | 15 | F6 | adds one sentence |
| not printed (F6, post hoc) | against the curation without the 15 and with only the 15: recall; precision, CatLog minus EnzyExtract | — | without -0.137 (-0.227 to -0.040); -0.100 (-0.168 to -0.034) / only +0.134 (-0.020 to +0.322); +0.174 (+0.049 to +0.349) | without -0.135 (-0.226 to -0.036); -0.078 (-0.147 to -0.015) / only +0.195 (+0.027 to +0.360); +0.242 (+0.107 to +0.393) | F6, F1 | no: on the other 64 papers EnzyExtract's agreement with its own curation is higher still |
| not printed (F6, post hoc) | page check: papers whose checked values include a wrong number, EnzyExtract against CatLog, on the 64 and the 15 | — | 11 against 0; 6 against 0 | 11 against 0; 6 against 0 | F6 | no |
| what-if (broad test, post hoc) | 12723605: its 128 kcat/Km counted right: wrong-number papers; recall; precision | — | 1 and 80 (79:0, P = 3.3 × 10^-24); +0.024 (-0.046 to +0.093); +0.085 (+0.063 to +0.109) | 1 and 78 (77:0, P = 1.3 × 10^-23); +0.050 (-0.018 to +0.119); +0.087 (+0.063 to +0.112) | second recount | what-if only |
| what-if (broad test, post hoc) | EnzyExtract repeats with no listing keeping its own verdict: one listing each counted right: wrong-number papers; recall; precision | — | 2 and 80 (78:0, P = 6.6 × 10^-24); +0.010 (-0.051 to +0.068); +0.071 (+0.042 to +0.100) | 2 and 78 (76:0, P = 2.6 × 10^-23); +0.037 (-0.023 to +0.094); +0.072 (+0.043 to +0.102) | second recount (97 values in 10 groups) | what-if only |
| what-if (broad test, post hoc) | EnzyExtract unread bounds, not-detected, relative and per-mass cells counted as wrong numbers (91 distinct cells in 22 papers): wrong-number papers | — | 2 and 95 (93:0, P = 2.0 × 10^-28) | 2 and 94 (92:0, P = 4.0 × 10^-28) | second recount (113 cells, 96 papers, with each repeated cell counted) | what-if only: the plan leaves such cells unscored, lenient to EnzyExtract |
| what-if (broad test, post hoc) | the scope fix as the audit and the second recount define it (only values judged right out, 270), with F5: wrong-number papers; recall; precision | — | — | 2 and 79 (77:0, P = 1.3 × 10^-23); +0.038 (-0.021 to +0.094); +0.073 (+0.043 to +0.103) | audit F2; second recount | what-if only |

### F5 from the strings themselves

| Paper | String in the database | Registered reading | Without the error term | Verdict | Judge's right value | CatLog stores it | Agreed once read |
|---|---|---|---|---|---|---|---|
| 23436726 | TheData.parquet row 120624 | 1.77e+08 | 1770 | not_this_metric | — | no | no |
| 23436726 | TheData.parquet row 120625 | 2.15e+07 | 2150 | measured_here_other_scale | 2150 mM^-1 s^-1 (2.15 x 10^6 M^-1 s^-1) | yes | yes |
| 23436726 | TheData.parquet row 120626 | 1.86e+08 | 1860 | measured_here_other_scale | 1860 mM^-1 s^-1 (1.86 x 10^6 M^-1 s^-1) | yes | yes |
| 23436726 | TheData.parquet row 120627 | 4.53e+08 | 4530 | not_this_metric | — | no | no |
| 23436726 | TheData.parquet row 120628 | 5.37e+06 | 537 | measured_here_other_scale | 537 mM^-1 s^-1 (5.37 x 10^5 M^-1 s^-1) | yes | yes |
| 23436726 | TheData.parquet row 120629 | 6.83e+08 | 6830 | measured_here_other_scale | 6830 mM^-1 s^-1 (6.83 x 10^6 M^-1 s^-1) | yes | yes |
| 23436726 | TheData.parquet row 120630 | 7.2e+09 | 7200 | not_this_metric | — | no | no |
| 23436726 | TheData.parquet row 120631 | 2.33e+08 | 2330 | measured_here_other_scale | 2330 mM^-1 s^-1 (2.33 x 10^6 M^-1 s^-1) | yes | yes |
| 23436726 | TheData.parquet row 120632 | 1.89e+10 | 18900 | measured_here_other_scale | 18900 mM^-1 s^-1 (1.89 x 10^7 M^-1 s^-1) | yes | yes |
| 32107312 | TheData.parquet rows 22713, 22714 | 0.0033 | 3.3 | measured_here_other_scale | 3.3 mM^-1 s^-1 (3.3 x 10^-3 uM^-1 s^-1) | yes | yes |
| 32107312 | TheData.parquet rows 22721, 22722 | 5.4e-05 | 0.54 | measured_here_other_scale | 0.54 mM^-1 s^-1 (5.4 x 10^-4 uM^-1 s^-1) | yes | yes |

## Files
- **Broad test** (`writing/research/enzyextract_broad_20261118/`):
  - `score_corrected.py`, which writes `corrected/results.json` (with `F5_strings` and `what_ifs_post_hoc`) and
    `corrected/RESULTS.md`;
  - `corrections.py`, which writes the tables above (`corrected/corrections_table.md`) and `corrections.json`.
- **Second stage** (`paper/evidence/locked_test_20261109/stage2/`): `score_corrected.py`, which writes
  `corrected/table.json`, `corrected/checked/` (the page check with both fixes), `corrected/f6_pagecheck.json`,
  `corrected/counts.json` and `corrected/RESULTS.md`, and the page check with neither fix
  (`corrected/checked_registered_reproduced/`), the merge fixed only (`corrected/checked_merge_fixed_only/`) and the
  misreads fixed only (`corrected/checked_misreads_fixed_only/`).
- **Scoring rules:** `paper/evidence/stage2_scoring_rules_20261117/rescore_corrected.py`, which writes
  `views_corrected.json`.
- **Recounts:** `corrected/recount_broad.json` (this folder), and the second stage's `corrected/recount_stage2.json`
  and `corrected/recount_merge.json` (the reference merge).
- **Rerun order:** the two `score_corrected.py`, then `rescore_corrected.py`, then `corrections.py`.
