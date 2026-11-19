# Stage 2, page check of the disputed values: rules (11 November 2026, post hoc)

## Status
- Written after stage 2's table (`RESULTS.md`), and after a first check of kcat in the 6 papers where EnzyExtract's
  run was furthest ahead (`check_first7/`).
  - That first check found that many of the curation's kcat entries there are values credited to earlier work,
    entries with a lost exponent sign, or repeats.
  - It was a selected set. This plan replaces it with a complete one.
- Committed before any verdict of this check exists. The pre-registered stage-2 table stands as it is.

## What is checked
- **Readings:** three readings of each paper: EnzyExtract's manual curation, CatLog, and EnzyExtract's full pipeline
  run (RGF).
- **Values:** every value that is not agreed by all three (same paper and metric, within 1.5%, matched one to one):
  - a curation value that CatLog or the run does not match;
  - a CatLog value the curation does not match;
  - a run value the curation does not match.

  A value all three agree on is taken as right and not checked.
- **Papers, in two parts** because of the account's limit:
  1. The 31 papers with a disputed kcat, with their disputed Km and kcat/Km too.
  2. The other papers with a disputed Km or kcat/Km.

  A metric's corrected table is given only when every paper with a dispute in that metric has been checked.

## How
- **One agent per paper** (the session's model, Fable 5.2: not the model that made CatLog's values or the plain
  read).
  - It reads the paper's text and page images.
  - It sees the three readings as A, B and C in a random order (seed 20261111), with no source named.
  - It sees each reading's full list for the paper, so it can tell a repeat.
- **Verdict per disputed value:**
  - measured_here_at_this_scale;
  - measured_here_other_scale (with the right scale);
  - as_printed_but_misprint: the value is what the cell and header print, but the paper's own numbers (a Vmax or
    specific activity with the enzyme's mass, the same measurement printed elsewhere, a ratio column) show that the
    printed scale is a misprint;
  - corrected_misprint: the value follows the scale the paper's own numbers support, not the printed one;
  - repeat_of_one_printed_value;
  - not_this_metric (a Vmax per mg, a Hill constant, a Ki, a relative value);
  - credited_to_earlier_work;
  - not_found_in_paper;
  - cannot_decide.
- **Second agent:** 6 of the papers of part 1, drawn with the same seed, get a second agent. Agreement between the
  two is reported.

## Corrected reference and scores (`score_checked.py`, committed with this plan)
- **Reference, per paper and metric:** the values all three agree on, plus every checked value judged right, from any
  reading. The same measurement held by two readings is counted once (matched one to one).
- **Two tables, side by side** (amended before any verdict, 11 Nov 16:20):
  - **as printed:** right is measured_here_at_this_scale or as_printed_but_misprint (the curation's own rule, and
    stage 1's);
  - **corrected:** right is measured_here_at_this_scale or corrected_misprint.
- **Per source** (CatLog, the plain read, RGF, the other runs, the database, BRENDA):
  - recall is the share of the reference it holds;
  - precision is the share of its values that are in the reference;
  - paper-clustered intervals and CatLog-minus-source differences, as in stage 2.
- **Per checked reading:** how many of its checked values got each verdict.
- **cannot_decide** values are left out of the reference and counted.

## Limits stated now
- Post hoc. One agent per value, no planted errors, no gate.
- The checkers are Claude models, as are CatLog's readers. A value's page, table and words are recorded so that a
  person can check any of them.
- Only CatLog, the curation and RGF are checked. A value that only the plain read or another run holds is not checked,
  so their precision here is a lower bound.
- A value all three readings agree on is not checked. A mistake all three share stays in the reference.
