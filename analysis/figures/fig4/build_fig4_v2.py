"""Fig. 4, co-learning: four panels since the evening of 18 November 2026, when the owner chose "Merge into Fig. 3"
(Fig. 3 became the comparison figure): d is the rules and flags learned from errors, all 16, as Fig. 3a and Extended
Data 7 drew them (panel_rules below). Earlier that day the owner had dropped the old c ("Yes, drop 4c": Fig. 3a then
listed all 16 rules), and the old d became c, its two kinds side by side. Below, the panels as drawn on 16 November
(fifth pass).

a  Rules written, along papers read from the 12th paper on, stacked by who first found the error each rule answers.
   The grey bottom layer is named inside itself ('25 from checking databases against papers', the owner's 16 Nov wording as the files carry it); the y axis is ticked at 0, at the
   known layer's top (25) and at the stack's end, 73, in bold (the total, on a line of its own). The four learned
   layers are named right of the stack, evenly spaced in stack order under the head 'Learned from errors found by'
   (code checks, checking agents, people with an agent, people), each beside a dot in its colours. These names are
   also the colour key of c and of d's dots. No grid (as Fig. 3b and 3g).
b  Misprinted unit headers caught, on a's scale: one rule from start to finish. An open green step for the 7 papers
   verifiers caught before the rule, ending at its last catch; at 1,285 papers read a thin ink line, 'rule', rising to
   the auditing agent's find (x60, a mint dot at its top, its words beside it); CatLog's catches since the rule, green
   and filled, to 121; a later catch by a verifier (x10^6, a mint dot on the curve: checking agents' colour). Each
   callout: the factor in bold, who found or caught it, what was printed. No grid, no boxes behind the words.
c  Rules learned from errors (8 of 48): for each finder its two rules on the Extended Data list (flags left out) that
   acted on the most papers (code checks have one there), and the rule of b, in bold and marked '(b)'. Two groups under
   heads: errors kept out or corrected, and right values no longer lost (the Extended Data list's first head adds 'or
   flagged'; c draws no flag, so its head drops it); within a group, rows by finder as a's names run, then by reach,
   0.8 mm between finders. Each row: a filled dot at all papers the rule acted on, its count printed beside it (log
   axis, no stems). The papers among them first read before the rule are counted for the legend only (the owner,
   16 Nov: the open dots that showed them were dropped).
d  Right values refused, then brought back: two small axes on a's scale, one per kind of right value code refused,
   each a red step of the values refused and not yet brought back. It rises with each refusal and falls when a change
   to the rule brought them back (log.tsv recover lines); there a dot in the colour of who had found these losses
   just before (a person; checking agents in an outside review), with words of timing only ('after ...'); the y axis
   ticked at 0 and at the peak; the values still out at the curve's end. The third change of the earlier passes (no
   organism printed: 168 values of one paper, refused and brought back within the first 69 papers read) sits on the
   y axis at this scale and is in the legend only.

On 16 November the owner kept Fig. 4 to co-learning: the 32 papers that print a misleading value and the list of 16
rules and flags are Extended Data items (writing/figures/extended_data/known_traps/, .../rules_reach/, which imports
this build's counts and labels and writes the Supplementary Table of all 87 kinds of error).

Run from anywhere (seconds; writes fig4.png beside this script):
    python3 -I -B writing/figures/fig4/v2/final/build_fig4_v2.py
    python3 -I -B writing/figures/fig4/v2/final/build_fig4_v2.py --report      (every drawn number, for the README)

Numbers come from ../evidence/ (rules/rules.csv, rules/catches_by_paper.csv, learning/rules_by_papers.csv,
learning/learning.csv, learning/learning_bins.csv, learning/tests.json, cases/cases.json) and, read only, from three of
CatLog's own files the evidence was counted from: log.tsv to the evidence's cut (15 November 00:30), its `add` lines for
when each paper was first read (c's open dots; the same count as count_rules.py's papers read, asserted to give the
evidence's 10,276) and its `recover` lines for when d's refused values came back (each paper's amount asserted against
the evidence's lost lines); paper/figures/method_overview/v5/taxonomy.tsv (rules.csv's source), for the dates of d's
rule changes, who found the losses again before each, and the 168 values of the organism change; and rejected.jsonl,
its rows checked to the cut for the five papers whose 34 values d leaves out at the end (the second reason each was
refused, legend d4). git gives the time of the commit that added taxonomy.tsv (the list of 2 November, legend a6), as
count_rules.py times every rule. The counts the critics' checks changed are made
here by code from those files: catches that are not the drawn kind are left out as named sets, each paper's amount
asserted and its reason stated (PP1, RA3, PP5); verifier fixes filed under RA4 whose notes describe a misprinted header
in other words are counted under PP1, a named set with each paper's amount asserted; and three rows of the full list
are counted without a part the row's label does not cover (TL6 less TL10's values and less the eight papers whose
image-only tables TL10's lines miss, TL10_LATER; CU5 less the values with no organism; RA10's values kept only).
Nothing is typed by hand. The build stops when a drawn number is not the number of its file (lean.same), and when two
texts overlap or a text comes within 1 mm of the page's edge (check_layout). Shared drawing code: ../../../lean.py
(imported, not edited); `rich` below copies lean.rich with scripts held at 5 pt or more.
"""
import bisect
import csv
import io
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True               # lean.py lives outside this folder: leave no __pycache__ beside it
HERE = Path(__file__).resolve().parent        # writing/figures/fig4/v2/final
FIGS = HERE.parents[2]                        # writing/figures
EV = HERE.parent / 'evidence'                 # writing/figures/fig4/v2/evidence
ROOT = HERE.parents[4]                        # the CatLog folder: log.tsv, paper/figures/method_overview/v5/taxonomy.tsv
sys.path.insert(0, str(FIGS))
import lean  # noqa: E402
from lean import Page, same, GREEN, BLUE, SLATE, MINT, TAN, RED, INK, GRID  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter  # noqa: E402
from PIL import Image  # noqa: E402

GREY = '#BDBDBD'                              # a: the known layer's line
KNOWN_FILL = '#D9D9D9'                        # a: rules from checking databases against papers (a lighter grey: background)
LEADER = '#9A9A9A'                            # b: the thin leader from the x10^6 dot to its words
KEY = '#666666'                               # c: the key's two marks (neutral: no finder)


def table(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


# Who found the error: one palette hue each, the same in a, c and d (fills at alpha 0.6, lines opaque in the same hue).
# Cyan is Fig. 1's co-learning colour (its box shows a person and an agent): the session in which the owner runs CatLog
# with an agent ('operator' in rules.csv `first_found_route`). Green is CatLog's catches (b; Figs 1 and 2); red is right
# values refused, an error of CatLog's (d; red marks errors in Fig. 1). Navy (the databases in Figs 1 and 3) is unused.
FINDER = {'known': ('From checking databases against papers', KNOWN_FILL, GREY), 'people': ('People', TAN, TAN),
          'with': ('People with an agent', BLUE, BLUE), 'agents': ('Checking agents', MINT, MINT),
          'code': ('Code checks', SLATE, SLATE)}
ORDER = ('known', 'people', 'with', 'agents', 'code')
# What the rule does, the two group heads of the Extended Data list (rules.csv `effect`); c holds no flag, so its
# first head says no 'flagged' (asserted below)
EFFECT = {'wrong value or label let in': 'Errors kept out, corrected or flagged',
          'right value refused or lost': 'Right values no longer lost'}
C_HEADS = {'wrong value or label let in': 'Errors kept out or corrected',
           'right value refused or lost': 'Right values no longer lost'}

# ======================================================================== data, panel c (the rules and their reach)
RULES = {r['id']: r for r in table(EV / 'rules/rules.csv')}
same('kinds on the list plus the two found after it', len(RULES), 87)
CATCH = table(EV / 'rules/catches_by_paper.csv')
CASES = json.load(open(EV / 'cases/cases.json', encoding='utf-8'))
NOW = CASES['papers_read_now']
same('papers read now', NOW, 10276)


def since_rule(kid, unit=None):
    """A kind's catches since its rule, in papers other than the finding papers, losses left out, as rows."""
    return [r for r in CATCH if r['id'] == kid and r['since_rule'] == 'yes' and r['in_finding_paper'] == 'no'
            and not r['action'].startswith('lost') and (unit is None or r['unit'] == unit)]


def by_paper(rows):
    out = defaultdict(int)
    for r in rows:
        out[r['pmid']] += int(r['amount'])
    return out


for kid, k in RULES.items():                  # every kind's reach in its own unit recounted: it must equal rules.csv
    got = by_paper(since_rule(kid, k['unit']))
    same(f'{kid}: other papers since the rule', len(got), int(k['papers_since_rule_other_papers'] or 0))
    same(f'{kid}: caught since the rule', sum(got.values()), int(k['caught_since_rule_other_papers'] or 0))

# --- catches left out, each a named paper with its amount asserted and its reason ---------------------------------
# PP1, the misprinted-header rule. count_rules.py files a verifier fix under PP1 when its note says "misprint"
# anywhere, and a refusal when its reason names a "header". b counts misprinted unit headers only: a paper counts
# when its own numbers show a header's unit misprinted for the whole column (or the row label that carries the unit
# in a table set sideways), or for one block of rows under a header that is right for the column's other blocks
# (41516070's PhA block, 27452902's ATP-varied block, 30476594's acetaminophen block, 22822057's CYP90A1 rows). Values
# under such a header that were refused, not corrected, count too. The PP1 lines below are not that, by their own
# lines: the verifier's note in catalog.jsonl (`verify_note`), log.tsv, or the reason in rejected.jsonl (and for
# 3966794 its line in papers.tsv). Read 15 November; none is a held-out paper. The first five were found first, the
# next ten by the critics' recount, the next six by a second, independent recount (the same day): one cell or one row
# printed in another unit under a header that is right for the rest, a cell's own exponent, a header that may be the
# OCR's misreading, and the authors' own calculation slip. The last three by a third recount (the same day): two cells,
# a row's own exponent, and 2222421's PP1-filed values, a misread multiplier (that paper still counts, by its Table 6,
# whose values are filed under RA4: RA4_HEADER below).
PP1_NOT_A_MISPRINT = {
    '37686129': (29, "its header 'K_cat (k s^-1)' was printed right: the reader and verifier had taken the k as stray "
                     "(log.tsv unitfix lines of 14 Nov; cases.json later_check_lines_left_out)"),
    '16684501': (1, "a row brought back without its column's conversion of a correctly printed '(x10^-5)' header "
                    "(log.tsv drop of 11 Oct, recover of 12 Oct)"),
    '1537854': (3, 'an audit drop for a wrong variant, filed under PP1 because its reason names a header (rejected.jsonl)'),
    '20201526': (3, 'a verifier refusal of values a parallel paper prints, the header citing it (rejected.jsonl)'),
    '11062561': (1, 'a verifier refusal of a value credited to an earlier paper in a header footnote (rejected.jsonl)'),
    '12689513': (8, "its header 'kcat/Km x 10^-5' is printed right and the reader applied the multiplier the wrong "
                    "way (a misread multiplier, RA4); the note's 'misprint' is an EC number"),
    '18297308': (1, 'a slipped digit, 0.3 printed for 1.3; the verifier changed the cell (a lone cell, PP4)'),
    '9041518': (2, 'one cell ten-fold off its row while the other rows close under the header (a lone cell)'),
    '9843375': (1, "a lone cell printed in another unit (CLAUDE.md, 'Misprinted unit headers': not a header misprint)"),
    '16930134': (1, "a lone cell printed in another unit (CLAUDE.md, 'Misprinted unit headers': not a header misprint)"),
    '28129670': (2, "two cells of one block printed in another unit (CLAUDE.md: not a header misprint)"),
    '29910900': (4, "a cell's own printed exponent misprinted, not its column's"),
    '8662720': (1, "a footnote value's exponent sign misprinted, not a column header"),
    '10978616': (5, 'the unit misprinted in a Results sentence (nM for mM), not in a column header'),
    '7864636': (1, 'a turnover number misprinted 1,000-fold in the Results text, not in a column header'),
    '12590613': (1, "one cell of Table 2 ten-fold off under a header that is right for its other cells: 'the paper "
                    "shows a 10x cell misprint' (verify_note)"),
    '19179361': (2, "two cells whose own printed exponent is misprinted: 'cell exponent misprinted, converted x10' "
                    "(verify_note)"),
    '17709343': (1, "one row printed in nM under a uM header that is right for its other rows: 'header unit "
                    "misprinted for this row' (verify_note; the template Km)"),
    '23848398': (2, "one enzyme's row printed in mM under a uM header that is right for the table's other enzymes: "
                    "'the uM header is a misprint for this row' (verify_note; its Table 3 prints both Km in mM)"),
    '38495554': (40, 'the authors computed kcat from a pkat per mg specific activity with the umol per min formula: '
                     'a calculation slip, refused on 11 Nov, no header named as misprinted (rejected.jsonl)'),
    '3966794': (8, "'the header's 10^-6 is an OCR misread or misprint' (verify_note): its text is Elsevier's OCR of a "
                   "1985 scan with no page image (papers.tsv), so the paper does not show the misprint is its own"),
    '18700786': (2, "two cells of Table 2 (7,100 and 1,500 M^-1 s^-1) 100x low (log.tsv unitfix); the table's other "
                    "10 kcat/Km cells under the same header are stored as printed, 3,200,000 in the same row among "
                    "them (catalog.jsonl)"),
    '31226373': (3, "the DMP Km cells' own exponent, '(3.96 ± 0.47) x 10^3' uM printed for x10^4 (log.tsv unitfix); "
                    "the guaiacol Km cells of the same Table 6 print the same form and are stored as right "
                    "(catalog.jsonl)"),
    '2222421': (5, "Table 3: its header '10^-3 x kcat/Km (M^-1 s^-1)' is right and code applied the multiplier the "
                   "wrong way, as 12689513; the note's misprint is the Vmax 'nmol' header, not a stored value's "
                   "(verify_note)"),
    # a fourth recount (16 November) compared each paper's unit_for_conversion with its raw_unit in catalog.jsonl
    '39859356': (70, "header multipliers read the wrong way, as 12611890 (RA4 below): all five tables print 'x10^n' "
                     "after the unit (kcat x10^5, x10^2, x10^6; kcat/Km x10^6, x10^3) and close only as printed = "
                     "value x 10^n; the notes' 'misprint' is that direction, and read as a misprint the kcat would "
                     "move 10^10-fold"),
}
PP1_BEFORE_NOT_A_HEADER = {   # before the rule: b's grey
    '21454538': (5, 'the unit misprinted in a Results paragraph (uM for mM), not in a column header'),
}
# RA3, partial rate constants: count_rules.py sorts refusals by a reason regex ('partial', 'cleavage'); these four
# papers' reasons (rejected.jsonl) are other kinds.
RA3_NOT_PARTIAL = {
    '14718657': (25, "an audit's wrong-substrate drop: in that partial reaction ATP is the product, not the substrate"),
    '39877815': (1, "a free parameter of the authors' kinetic model, not kcat (a constant that is not kcat or Km)"),
    '33995334': (1, 'no activity detected: the row prints a not-determined placeholder'),
    '15003560': (1, "an internal-standard peptide 'which cannot be cleaved': the assay's premise, not a result"),
    '22705398': (3, 'a component constant of a two-component fit (k_app(2)), a constant that is not kcat/Km, as 39877815'),
}
# PP5, values at the diffusion ceiling: the export writes a note only for a review flag in catlog.TAIL_NOTE; these four
# papers' review lines (sources/implausible_as_printed.tsv) are all 'plausible', so nothing was flagged there.
PP5_NO_FLAG = {p: (1, "its review lines are all 'plausible': the export writes no note (catlog.TAIL_NOTE)")
               for p in ('10677435', '10777548', '12573282', '29030427')}
OUT = {'PP1': PP1_NOT_A_MISPRINT, 'RA3': RA3_NOT_PARTIAL, 'PP5': PP5_NO_FLAG}
for kid, named in OUT.items():
    have = by_paper(since_rule(kid))
    for p, (amount, _) in named.items():
        same(f'{kid} catch left out: {p}', have[p], amount)

# PP1 is counted from what the notes say, not from the word. count_rules.py files a verifier's unit-factor fix under
# PP1 only when its note says "misprint", and every other one under RA4 (a unit, prefix or multiplier read wrongly).
# The notes of all 100 RA4 verifier-fix papers were read (catalog.jsonl `verify_note`, 15 November; none held out).
# These papers' RA4 lines describe a misprinted header in other words, by the rule above (a whole column, one block
# under a header that is right for the rest, or a sideways table's row label, whose unit the paper's own numbers
# contradict), and are counted under PP1, timed by PP1's rule. The other 83 are not: a header's power of ten whose
# direction the paper's numbers settle, read the wrong way (61, as 12689513); a printed form code or the reader read
# wrongly (8); one cell, one row or scattered cells in another unit (6); a value taken from the text or another table
# (6); a header seen only in Elsevier's OCR text, with no page image (7766669, 7674929; as 3966794).
RA4_HEADER = {
    # papers counted under PP1 by these lines alone, since the rule
    'NP049D13D6': (26, "Table 1's kcat column is min^-1, not the s^-1 printed: kcat/Vmax = 22.0 in all 13 rows (Vmax "
                       "per mg, a 22 kDa protein), and the kcat/Km column with it"),
    '28726643': (6, "Table 1's glucose Km column is mM under its uM header: the Results print 31 mM, and every glucose "
                    "kcat/Km closes only with Km in mM"),
    '20673213': (6, "Table 2's kcat column is 10^3 short: every cell is Amax x 0.24, where the paper's own Amax and "
                    "240-kDa Mr give Amax x 240 min^-1"),
    'NP854A3E4B': (11, "Table 5's kcat column is 10^3 high by the paper's own Vmax and masses, and its catalytic "
                       "efficiencies are s^-1 M^-1, as the Results print them, not the s^-1 mM^-1 of the header"),
    '40033318': (4, "Table 2 is set sideways: its row label 'K_m (umol/L)' is contradicted by the Methods (substrate "
                    "0.05-4 mM), and all four cells are mM"),
    '40756634': (8, "Table 1's kcat column is Vmax x 105/60 with no nmol to umol, 10^3 high by the paper's own Vmax, "
                    "and its kcat/Km column, computed from it"),
    '40943432': (6, "Table 3 is set sideways: its kcat row is Vmax (nM min^-1) / [E] (20 uM) as bare numbers, 10^3 "
                    "high, and its kcat/Km row, computed from it"),
    '6542583': (4, "Table 2's tertiary-amine block of the Km column is mM under the column's uM header, which holds "
                   "for its 13 secondary-amine rows"),
    '28256782': (6, "Table 1's kcat column (min^-1, no multiplier) is 10^3 low by the paper's own U/mg and subunit "
                    "mass; the kcat/Km beside it prints no unit and was computed from it"),
    '30022031': (23, "Table 2's kcat/Km header '[M^-1 s^-1]' is missing its x10^3: all 23 cells close only at x10^3, "
                     "and the Discussion repeats the mislabel"),
    # before the rule (b's grey)
    '23747922': (8, "Table 1's mM header is wrong for the nucleotide block (ATP, GTP, UTP, CTP; Km and kcat/Km), which "
                    "is uM by the paper's footnote a and its 1 mM ATP assay"),
    # a paper whose PP1-filed values are left out above: it counts by these
    '2222421': (14, "Table 6's header '10^-3 x kcat/Km (M^-1 s^-1)' does not hold for that table: its 8 cells are "
                    "plain M^-1 s^-1 by the paper's own Vmax and Km, while Tables 1-2 under the same header close with "
                    "x10^3; the line's other 6 values (Tables 1-2) are misread multipliers, counted with it"),
    # papers already counted: the same misprint, in values the note does not call one
    '11148033': (1, "the third R234K cell of Table 3, under the 'x10^6 s^-1 uM^-1' header its PP1-filed values call "
                    "misprinted"),
    '15175333': (3, "Table II's kcat column, 10^3 high: the misprint its PP1-filed kcat/Km carries"),
    '19640561': (1, "the GlAD row of Table 4's Km column, whose uM header its PP1-filed rows call misprinted"),
    '27452902': (1, "the second row of the ATP-varied block its PP1-filed value calls misprinted"),
    '34162386': (2, "the AcmB cells of Table 4's kcat/Km column, per minute like the KSTD1 cells its PP1-filed values "
                    "call misprinted"),
}
PP1_RULE_AT = int(RULES['PP1']['papers_read_at_rule'])
REFILED = []
for p, (amount, _) in RA4_HEADER.items():
    lines = [r for r in CATCH
             if r['id'] == 'RA4' and r['pmid'] == p and r['step'] == 'Verify' and r['action'] == 'fixed']
    same(f'RA4 line counted under PP1: {p}', [(int(r['amount']), r['unit'], r['in_finding_paper']) for r in lines],
         [(amount, 'values', 'no')])
    at = int(lines[0]['papers_read_at_first'])
    same(f'{p}: clear of the PP1 rule, on one side', at != PP1_RULE_AT, True)
    REFILED.append(dict(lines[0], id='PP1', since_rule='yes' if at > PP1_RULE_AT else 'no', refiled='RA4',
                        in_finding_paper='yes' if p in RULES['PP1']['first_found_papers'].split() else 'no'))
same('RA4 lines counted under PP1 (since the rule: lines, values; before it: lines, values)',
     [(sum(1 for r in REFILED if r['since_rule'] == s), sum(int(r['amount']) for r in REFILED if r['since_rule'] == s))
      for s in ('yes', 'no')], [(16, 122), (1, 8)])
CATCH = [r for r in CATCH if not (r['id'] == 'RA4' and r['pmid'] in RA4_HEADER and r['step'] == 'Verify')] + REFILED
CU5_NO_ORGANISM = 'stored with no organism given'      # CU5's values with no organism: in the legend, not counted


def keep_row(kid, r):
    """What a rule's reach counts of its kind's catches (all units). A left-out paper's own lines go; lines counted
    under the kind from another (RA4_HEADER) stay."""
    if r['pmid'] in OUT.get(kid, {}) and not r.get('refiled'):
        return False
    if kid == 'CU5' and r['what'].startswith(CU5_NO_ORGANISM):
        return False
    if kid == 'RA10' and r['action'] != 'kept':
        return False      # 'Right values kept' counts values kept: RA10's refusals of censored rows are left out
    return True


same("c: the 'right values kept' kinds whose catches are not all values kept",
     sorted({kid for kid in ('RA10', 'PP6', 'TL6', 'TL10', 'CU8', 'CU5')
             for r in since_rule(kid) if r['action'] != 'kept'}), ['RA10'])
RA10_OUT = by_paper([r for r in since_rule('RA10') if r['action'] != 'kept'])
same('RA10: refusals of censored rows the paper does not support, left out', (len(RA10_OUT), sum(RA10_OUT.values())),
     (21, 72))


# TL6 and TL10, values in tables printed only as images. count_rules.py files a value under TL10 when the reader's
# quote begins '[page image', and under TL6 when it carries the page-image flag (catalog.jsonl quote_check), which
# every value read off a page image carries; so reach() takes TL10's values out of TL6, paper by paper. In eight papers
# the image-only tables got past both: their readers quoted the cells themselves, or the image file ('[table image
# ...'), so TL10 has no line for them and TL6 kept them whole. They are moved by name, each paper's TL6 amount asserted.
# TL10 counts the reader's values of the six later papers, as its lines count every other paper's; all eight leave
# TL6, TL10's two finding papers included (TL10 does not count those). Read 16 November in catalog.jsonl (location,
# quote, quote_check, read_by: each paper's flagged rows equal its TL6 line, all added before the evidence's cut of
# 15 November 00:30) and papers.tsv (7493990's note); none is a held-out paper.
TL10_LATER = {   # (TL6 values, of them read by the reader, where the paper shows its tables only as images)
    '24980702': (218, 206, "Tables 2 and 7 deposited as image files (quoted '[table image elife03275t002.jpg, Table "
                           "2]'); the other 12 values, of Table 7, the verifier found (RA6), which TL10 does not count"),
    '10913258': (122, 122, 'tables inside Figures 3 to 6, image only'),
    '8537366': (46, 46, 'Tables I and II deposited as images in the Elsevier XML (objects fx501 and fx502)'),
    '7559518': (18, 18, 'Tables I and III deposited as images in the Elsevier XML (objects fx1t and fx3t)'),
    '7493990': (7, 7, "Table II an image only (papers.tsv: 'article PDF: Table II is an image only')"),
    '17462992': (8, 8, 'a table inside Figure 2, image only, not in the text layer'),
}
TL10_FINDING = {'102640': 147, '10965051': 191}   # TL10's own finding papers: out of TL6, not counted under TL10
TL6_LINES = by_paper(since_rule('TL6'))
for p, amount in list({p: v[0] for p, v in TL10_LATER.items()}.items()) + list(TL10_FINDING.items()):
    same(f'TL6 values of an image-only table, moved: {p}', TL6_LINES.get(p, 0), amount)
same('TL10: no line for the eight papers', sorted(set(by_paper([r for r in CATCH if r['id'] == 'TL10']))
                                                  & (set(TL10_LATER) | set(TL10_FINDING))), [])
same('TL10: its finding papers', sorted(RULES['TL10']['first_found_papers'].split()), sorted(TL10_FINDING))
same('TL10: the six first caught after its rule', {r['pmid'] for r in since_rule('TL6') if r['pmid'] in TL10_LATER
                                                   and int(r['papers_read_at_first']) >
                                                   int(RULES['TL10']['papers_read_at_rule'])}, set(TL10_LATER))
same("TL10: the reader's values within each paper's TL6 values", all(0 < rd <= v for v, rd, _ in TL10_LATER.values()),
     True)
same('values moved (to TL10; out of TL6)', (sum(v[1] for v in TL10_LATER.values()),
                                            sum(v[0] for v in TL10_LATER.values()) + sum(TL10_FINDING.values())),
     (407, 757))


def reach(kid):
    """{pmid: amount} of a rule's reach, the papers where it applied: catches since the rule, outside the papers
    where the error was found, every unit, losses left out."""
    got = by_paper([r for r in since_rule(kid) if keep_row(kid, r)])
    if kid == 'TL10':    # the reader's values of the six later papers whose image-only tables TL10's lines miss
        got.update({p: rd for p, (_, rd, _) in TL10_LATER.items()})
    if kid == 'TL6':     # TL6 counts every value with the page-image flag, TL10's page-image tables included:
        tl10 = by_paper(since_rule('TL10'))     # counted without TL10's values, paper by paper, and without the
        got = {p: n - tl10.get(p, 0) for p, n in got.items()       # eight papers' image-only tables
               if p not in TL10_LATER and p not in TL10_FINDING and n - tl10.get(p, 0) > 0}
    return dict(got)


def finder(kid):
    """Who found the error behind a rule. 'with': found in the chat where the owner runs CatLog with an agent (route
    'operator'). IP2 is the agents', as rules.csv and a have it (an outside review by an agent, at 12 papers read); a
    reviewer's later finding extended its rule to join records the reads had split."""
    k = RULES[kid]
    return 'with' if k['first_found_route'] == 'operator' else k['first_found_by']


same('IP2: first found by an agent, in an outside review',
     (RULES['IP2']['first_found_by'], RULES['IP2']['first_found_route']), ('agents', 'outside review'))


same("the route 'operator' is always under agents",
     {k['first_found_by'] for k in RULES.values() if k['first_found_route'] == 'operator'}, {'agents'})
MIN_PAPERS = 10                               # the full list holds rules that applied in ten or more papers
NOT_LISTED = {   # found while CatLog read, with a reach, but not on the full list: why (for the legend)
    'PP4': "its rule was in CatLog's first rules, before an agent recorded the kind at 97 papers read",
    'X1': 'rebuilt texts, not values (2,470 texts and 3 papers read again in other papers; the 6 values kept are the '
          "finding paper's own: catches_by_paper.csv, in_finding_paper = yes)",
    'X2': 'rebuilt texts of papers not yet read (409)',
    'TL9': 'rebuilt texts, not values (124)',
    'TL12': 'values in supplements, a count that includes supplements bound into the article (TL12_SUPP: a count '
            'that keeps only supplements obtained and read)',
    'DB2': 'a rule on the method (readers who had seen database values; 291 papers read again blind), no value',
}
same('PP4: its rule came before its finding', int(RULES['PP4']['papers_read_at_rule']) <
     int(RULES['PP4']['papers_read_when_found']), True)
same("X1: its values kept are the finding paper's own; in other papers it rebuilt texts and read papers again",
     sorted({(r['unit'], r['in_finding_paper']) for r in CATCH if r['id'] == 'X1' and r['since_rule'] == 'yes'}),
     [('papers', 'no'), ('papers', 'yes'), ('papers read again', 'no'), ('values', 'yes')])
same('X1: the values kept, all in its finding paper',
     sum(int(r['amount']) for r in CATCH if r['id'] == 'X1' and r['unit'] == 'values'), 6)
REACH, LEARNED, SMALL = {}, [], []            # LEARNED: the full list of 16 (Extended Data); c draws eight of them
for kid, k in RULES.items():
    if finder(kid) not in ('people', 'with', 'agents', 'code') or k['status'] not in ('rule', 'flag kept as printed'):
        continue
    REACH[kid] = reach(kid)
    n = len(REACH[kid])
    if n == 0 or kid in NOT_LISTED:
        continue
    (LEARNED if n >= MIN_PAPERS else SMALL).append(dict(id=kid, who=finder(kid), papers=n, effect=k['effect'],
                                                        flag=k['status'] != 'rule'))
same('c: kinds found while reading with a reach (rules design: 25 + DB2)',
     len(LEARNED) + len(SMALL) + len(NOT_LISTED), 26)
same('c: rules under ten papers', sorted((k['id'], k['papers']) for k in SMALL),
     [('CU2', 9), ('CU4', 8), ('CU6', 7), ('IP5', 1)])
same('c: every kind of the full list changes values or labels', {k['effect'] for k in LEARNED}, set(EFFECT))
BY_EFFECT = [sorted([k for k in LEARNED if k['effect'] == e], key=lambda k: -k['papers']) for e in EFFECT]
same('c: the full list by what the rule does', [len(g) for g in BY_EFFECT], [10, 6])
same('c: the full list by who found', sorted(Counter(k['who'] for k in LEARNED).items()),
     [('agents', 7), ('code', 1), ('people', 2), ('with', 6)])
same('c: flags on the full list', sorted(k['id'] for k in LEARNED if k['flag']), ['PP5', 'PP6'])
same('c: papers per rule of the full list', {k['id']: k['papers'] for k in LEARNED},
     {'IP8': 139, 'PP1': 121, 'IP2': 68, 'IP6': 44, 'PP5': 39, 'RA8': 33, 'RA11': 25, 'RA3': 24, 'IP4': 21,
      'CU7': 10, 'RA10': 4204, 'PP6': 559, 'TL6': 214, 'TL10': 207, 'CU8': 137, 'CU5': 66})
# where the count differs from rules.csv's own-unit count, each change is one of the reasons stated above
same('c: amounts of the rules that differ from rules.csv',
     {kid: (len(REACH[kid]), sum(REACH[kid].values())) for kid in ('PP1', 'RA3', 'PP5', 'RA8', 'RA10', 'PP6', 'TL6',
                                                                   'TL10', 'CU5')},
     {'PP1': (121, 1372), 'RA3': (24, 607), 'PP5': (39, 331), 'RA8': (33, 153), 'RA10': (4204, 37896),
      'PP6': (559, 1108), 'TL6': (214, 1720), 'TL10': (207, 6874), 'CU5': (66, 1224)})
# TL12, values printed only in a supplement, is not on the full list (NOT_LISTED): count_rules.py counts every value
# whose location names a supplement, bound into the article or not. Counted only in papers where a supplement was
# obtained and the paper read again (its log.tsv line) and values printed only in a supplement were stored, it would
# reach more papers than either rule c draws for people with an agent (139 and 137) and take the place of the second;
# the README says so (c, 'Not on the full list'), and the full list decides.
TL12_SINCE = since_rule('TL12')
TL12_OBTAINED = {r['pmid'] for r in TL12_SINCE if r['unit'] == 'papers'}
TL12_SUPP = {p: n for p, n in by_paper([r for r in TL12_SINCE if r['unit'] == 'values']).items() if p in TL12_OBTAINED}
same('TL12 where a supplement was obtained and its values stored (papers, values; supplements obtained)',
     (len(TL12_SUPP), sum(TL12_SUPP.values()), len(TL12_OBTAINED)), (162, 6480, 231))
same("TL12 so counted against the two rules c draws for people with an agent (Trim signal peptides; Km in mg ml-1)",
     (len(TL12_SUPP), sorted((k['papers'] for k in LEARNED if k['who'] == 'with' and not k['flag']),
                             reverse=True)[:2]), (162, [139, 137]))
# the bold row says 'Correct': its legend note says the count includes values refused, not corrected (the paper shows
# the header misprinted but not which unit is right, or the cells were miscalculated as well)
PP1_REFUSED = by_paper([r for r in since_rule('PP1') if keep_row('PP1', r) and r['action'] == 'kept out'])
PP1_ONLY_REFUSED = sorted(p for p in PP1_REFUSED if p not in by_paper([r for r in since_rule('PP1')
                                                                       if keep_row('PP1', r)
                                                                       and r['action'] != 'kept out']))
same('c: PP1 values refused, not corrected (papers, values; papers only refused)',
     (len(PP1_REFUSED), sum(PP1_REFUSED.values()), PP1_ONLY_REFUSED), (3, 42, ['15342115', '18093993']))
CU5_ORG = by_paper([r for r in since_rule('CU5') if r['what'].startswith(CU5_NO_ORGANISM)])
same('CU5: values with no organism, left out of its reach', (len(CU5_ORG), sum(CU5_ORG.values())), (414, 14531))

# --- the eight rules c draws -----------------------------------------------------------------------------------------
# Rules only: a flag (values kept as printed with a note) is not one of a's 73 rules, so the flag 'kcat, Km and kcat/Km
# that disagree' (PP6) leaves c (its refused values are d's first curve) and c's title can say '8 of 48'. For each
# finder, its two rules on the Extended Data list that acted on the most papers (code checks have one there), and the
# rule of b, in bold. Rows in two groups by what the rule does, as the Extended Data list (errors kept out or
# corrected; right values no longer lost); within a group by finder, as a's names run from the top (code checks,
# checking agents, people with an agent, people), then by reach: a pick of two per finder, so not drawn as CatLog's
# widest-reaching rules. Rules that acted on ten or more papers but are not on the list (texts rebuilt, papers read
# again, the supplement rule: NOT_LISTED) are not candidates.
B_RULE = 'PP1'
PER_FINDER = 2
C_ORDER = ('code', 'agents', 'with', 'people')      # a's stack from the top: ORDER reversed, the known layer left out
same("c: finders in the order of a's names", C_ORDER, tuple(reversed(ORDER))[:-1])
C_ROWS = []
for who in C_ORDER:
    mine = sorted((k for k in LEARNED if k['who'] == who and not k['flag']), key=lambda k: -k['papers'])
    if len(mine) > PER_FINDER:                 # no tie at the cut, so the choice is the rule's and not the order's
        same(f'c: {who}: the second widest above the third',
             mine[PER_FINDER - 1]['papers'] > mine[PER_FINDER]['papers'], True)
    C_ROWS += mine[:PER_FINDER]
C_ROWS += [k for k in LEARNED if k['id'] == B_RULE and k not in C_ROWS]
C_ROWS.sort(key=lambda k: (list(EFFECT).index(k['effect']), C_ORDER.index(k['who']), -k['papers']))
same('c: rows drawn, by what the rule does, then finder, then reach (rule, finder, papers)',
     [(k['id'], k['who'], k['papers']) for k in C_ROWS],
     [('PP1', 'agents', 121), ('IP8', 'with', 139), ('IP6', 'people', 44), ('CU7', 'people', 10),
      ('TL6', 'code', 214), ('RA10', 'agents', 4204), ('TL10', 'agents', 207), ('CU8', 'with', 137)])
same("c: no flag among the rows, so the first head says no 'flagged'", [k['id'] for k in C_ROWS if k['flag']], [])
same('c: no two rows at the same reach', len({k['papers'] for k in C_ROWS}), len(C_ROWS))
same('c: rows drawn by what the rule does', sorted((k['effect'][:5], k['id']) for k in C_ROWS),
     [('right', 'CU8'), ('right', 'RA10'), ('right', 'TL10'), ('right', 'TL6'),
      ('wrong', 'CU7'), ('wrong', 'IP6'), ('wrong', 'IP8'), ('wrong', 'PP1')])
same('c: flags among the rows drawn', [k['id'] for k in C_ROWS if k['flag']], [])
same('c: the flags of the full list, not drawn', sorted(k['id'] for k in LEARNED if k['flag']), ['PP5', 'PP6'])
same('c: the rows not drawn (the rest of the full list)',
     sorted((k['id'], k['who'], k['papers']) for k in LEARNED if k not in C_ROWS),
     [('CU5', 'with', 66), ('IP2', 'agents', 68), ('IP4', 'agents', 21), ('PP5', 'agents', 39), ('PP6', 'with', 559),
      ('RA11', 'with', 25), ('RA3', 'agents', 24), ('RA8', 'with', 33)])
same("c: the people-with-an-agent pick against its next rule (Keep Km printed in mg ml-1, then values missing a "
     "printed pH, temperature or column unit)",
     [k['papers'] for k in sorted((k for k in LEARNED if k['who'] == 'with' and not k['flag']),
                                  key=lambda k: -k['papers'])][:3], [139, 137, 66])

K, M = [('k', 'i'), ('cat', 'sub')], [('K', 'i'), ('m', 'sub')]      # kcat and Km: italic, roman subscript
KM = K + [('/', '')] + M
X = [('x', 'i')]
# What each rule does: a plain clause led by its verb, the owner's rule for figure text (Fig. 1, 7 November); runs for
# `rich`. The full list (Extended Data) imports these, so its eight rows shared with c read word for word as c's. Each
# names the act in its own words (the kind's taxonomy name is rules.csv `kind`). Reworded on 16 November (fourth pass)
# for the readers' and the judges' notes, and in the fifth pass for the critics' (CU7, RA3, IP4; PP6 in Fig. 1's words):
# README, "Reader ambiguities and their fixes".
LABEL = {
    'TL6': [('Keep values verified on the page image', '')],     # code keeps, flagged, a cell the verifier read there
    'RA10': [('Record < ', '')] + X + [(', > ', '')] + X + [(' and not-detected values', '')],   # Fig. 1b's '< x', '> x'
    'TL10': [('Read tables printed as images', '')],
    'PP1': [('Correct misprinted unit headers', '')],
    'IP8': [('Trim signal peptides from sequences', '')],
    'CU8': [('Keep ', '')] + M + [(' printed in mg ml', ''), ('−1', 'sup')],
    'IP6': [('Store isozymes and alleles as enzymes, not mutants', '')],   # and strain, species, splice, paralog forms
    'CU7': [('Never calculate ', '')] + KM + [(' where a limit is printed', '')],
    'IP2': [('Rejoin one table row split into records', '')],
    'PP5': [('Flag ', '')] + KM + [(' above the diffusion limit', '')],
    'RA8': [('Set aside checking agents’ unusable verdicts', '')],
    'RA11': [('Use ‘not detected’ only for no activity', '')],
    'RA3': [('Keep out rate constants for one product only', '')],
    'IP4': [('Settle a second reading’s different value from the paper', '')],
    'PP6': [('Keep and flag ', '')] + K + [(', ', '')] + M + [(' and ', '')] + KM + [(' that disagree', '')],   # Fig. 1's
    'CU5': [('Keep values missing a printed pH, temperature or column unit', '')],          # words, its Flag box
}
same('every rule of the full list has a label', sorted(LABEL), sorted(k['id'] for k in LEARNED))
B_MARK = ' (b)'                               # c's bold row: the rule b follows


def text_of(parts):
    return ''.join(t for t, _ in parts)

# ===================================================================================== data, panel a (rules in force)
LRULES = [r for r in table(EV / 'learning/rules_by_papers.csv') if r['status'] == 'rule']
same('a: rules on the list of 2 November', len(LRULES), 71)
same('a: the same 71 as rules.csv', {r['id'] for r in LRULES},
     {kid for kid, k in RULES.items() if k['status'] == 'rule' and k['on_list_of_2_nov'] == 'yes'})
same("a: the 71 by Fig. 1's steps (68 in the four steps + 3 in the database check)",
     dict(Counter(RULES[r['id']]['rule_step'] for r in LRULES)),
     {'Read': 16, 'Convert': 10, 'Verify': 7, 'Check': 35, 'Database check': 3})
GROUP = {'old system': 'known', 'verifier': 'agents', 'operator': 'with', 'outside review': 'agents',
         'audit': 'agents', 'database check': 'agents', 'code check': 'code', 'sweep': 'code',
         'reviewer': 'people', 'owner': 'people'}
same('a: rules by who found, as the learning evidence counts them',
     dict(Counter(GROUP[r['first_found_by']] for r in LRULES)),
     {'known': 24, 'with': 20, 'agents': 14, 'code': 8, 'people': 5})
# the two kinds found after the list (rules.csv: X1 figure captions, code; X2 drawn structures in table cells, found
# in the owner's chat with an agent), each a rule at its commit
LATER = [k for k in RULES.values() if k['on_list_of_2_nov'] != 'yes']
same('a: rules found after the list', sorted((k['id'], k['status'], k['first_found_route'], k['papers_read_at_rule'])
                                             for k in LATER),
     [('X1', 'rule', 'code check', '8335'), ('X2', 'rule', 'operator', '9900')])


def a_group(r):
    """PP4 is drawn as already known, as c's full list leaves it out: its rule was in the first commit, before an
    agent recorded the kind (rules.csv). It is the only kind whose rule came before its recorded finding."""
    return 'known' if r['id'] == 'PP4' else GROUP[r['first_found_by']]


early = sorted(kid for kid, k in RULES.items() if k['first_found_by'] in ('people', 'agents', 'code')
               and k['papers_read_at_rule'] and k['papers_read_when_found']
               and int(k['papers_read_at_rule']) < int(k['papers_read_when_found']))
same('a: kinds whose rule came before their recorded finding', early, ['PP4'])
ENTRY = sorted([(int(r['papers_read_at_rule']), a_group(r)) for r in LRULES] +
               [(int(k['papers_read_at_rule']), GROUP[k['first_found_route']]) for k in LATER])
A_COUNT = Counter(g for _, g in ENTRY)
same('a: layers', dict(A_COUNT), {'known': 25, 'people': 5, 'with': 21, 'agents': 13, 'code': 9})
tests = json.load(open(EV / 'learning/tests.json', encoding='utf-8'))
same('a: papers read at the end', tests['snapshot']['papers_read_at_end'], NOW)


def in_force(at, who=None):
    return sum(1 for p, g in ENTRY if p <= at and (who is None or g == who))


FIRST_LATER = min(int(k['papers_read_at_rule']) for k in LATER)
for at, n in tests['rules_in_force_at_papers_read'].items():   # the learning evidence counts the list's 71 only
    if int(at) < FIRST_LATER:
        same(f'a: rules in force at {at} papers read', in_force(int(at)), n)
same('a: test points after the first later rule', [a for a in tests['rules_in_force_at_papers_read']
                                                   if int(a) >= FIRST_LATER], ['10276'])
same('a: rules in force: the list complete at, then the two later', (in_force(7510), in_force(8335), in_force(NOW)),
     (71, 72, 73))
same('a: last rule entered at', max(p for p, _ in ENTRY), 9900)
A_IDS = {r['id'] for r in LRULES} | {k['id'] for k in LATER}      # the 73 rules a stacks
same('a: rules stacked', len(A_IDS), len(ENTRY))
same("c: every row drawn is one of a's 73 rules", sorted(k['id'] for k in C_ROWS if k['id'] in A_IDS),
     sorted(k['id'] for k in C_ROWS))
same("c: the flags of the full list are not among a's 73 rules", [k['id'] for k in LEARNED if k['flag'] and k['id'] in A_IDS],
     [])

# ============================================================================= data, panel b (misprinted unit headers)
PP1 = RULES['PP1']
RULE_AT = int(PP1['papers_read_at_rule'])
same('b: PP1 found and ruled at the same papers read', int(PP1['papers_read_when_found']), RULE_AT)
same('b: the find is 25514023', PP1['first_found_papers'], '25514023')
A = CASES['cases'][0]['numbers']
same('b: 25514023 x60', A['factor_25514023'], 60)
same('b: 12226525 x10^6', A['factor_12226525'], 1000000.0)
same("b: 25514023's header", {x['header'] for x in A['a_25514023_kcat_s-1']}, {'min^-1'})
same("b: 12226525's header", {x['header'] for x in A['b_12226525_kcat_over_km_M-1_s-1']}, {'nM^-1 s^-1'})


def first_catch(rows):
    first = {}
    for r in rows:
        x = int(r['papers_read_at_first'])
        first[r['pmid']] = min(first.get(r['pmid'], x), x)
    return first


pp1_rows = [r for r in CATCH if r['id'] == 'PP1' and r['in_finding_paper'] == 'no' and r['unit'] == 'values'
            and not r['action'].startswith('lost')]
for p, (amount, _) in PP1_BEFORE_NOT_A_HEADER.items():
    same(f'PP1 catch before the rule left out: {p}',
         sum(int(r['amount']) for r in pp1_rows if r['since_rule'] == 'no' and r['pmid'] == p), amount)
before_rows = [r for r in pp1_rows if r['since_rule'] == 'no' and r['pmid'] not in PP1_BEFORE_NOT_A_HEADER]
BEFORE = first_catch(before_rows)
AFTER = first_catch([r for r in pp1_rows if r['since_rule'] == 'yes' and keep_row('PP1', r)])
BEFORE_VALUES = sum(int(r['amount']) for r in before_rows)
same('b: papers and values caught before the rule', (len(BEFORE), BEFORE_VALUES), (7, 207))
same('b: before the rule, all before it', max(BEFORE.values()) < RULE_AT, True)
same("b: papers caught since the rule are c's bold row", set(AFTER), set(REACH[B_RULE]))
X10_6 = AFTER['12226525']
same('b: 12226525 caught at', X10_6, 2600)
same('b: papers caught by then', sum(1 for x in AFTER.values() if x <= X10_6), 19)


# ========================================================== data, panel c's open dots (papers read before the rule)
# When each paper was first read: its first `add` line in log.tsv, placed among all papers' first adds, as
# count_rules.py counts papers read (rules/README.md: 'papers read so far = distinct papers with an add line in log.tsv
# before that moment'). Read only, to the evidence's cut (log.tsv to its 00:30 line of 15 November); the count there is
# the evidence's papers read now (asserted), and later lines change no earlier paper's place.
LOG_CUT = '2026-11-15 00:30'
FIRST_READ = {}
with open(ROOT / 'log.tsv', encoding='utf-8') as f:
    for ln in f:
        p = ln.rstrip('\n').split('\t')
        if len(p) > 2 and p[2] == 'add' and p[0] <= LOG_CUT and p[1] not in FIRST_READ:
            FIRST_READ[p[1]] = p[0]
READ_TIMES = sorted(FIRST_READ.values())
same('papers read at the evidence cut (first add lines of log.tsv)', len(READ_TIMES), NOW)
POS = {p: bisect.bisect_left(READ_TIMES, t) for p, t in FIRST_READ.items()}     # papers read before p was first read
same('every paper of the full list was read before the cut', all(p in POS for k in LEARNED for p in REACH[k['id']]),
     True)


def later_changes(kid):
    return [int(x) for x in RULES[kid]['papers_read_at_later_changes'].split()]


# A paper counts as read before the rule when it was first read before the first version of the rule that did that
# kind of act. For most rules that is the rule's first commit. Three kinds' first commits did none of an act counted,
# each named (judges' check of 16 November; critics' check of the same day). Acts that later changes added to a rule
# that already did that kind of act are set against the first commit: PP1's unitfix corrections (14d5288, 1,457 papers
# read) and the unit and Vmax sweeps (6d851aa, d5812ab), TL6's OCR hyphens (7d212bd, 3,248). A paper first read after
# the rule and caught later is a miss caught later, not the rule reaching back.
ACT_LATER = {
    'IP2': 'the joins counted are the join rule of commit 5c441ee (its first later change), written after a '
           "reviewer's finding; the rule first written at 12 papers read grouped records and joined none",
    'PP6': 'two acts: a disagreement noted in the export, from its first commit (aa032a4, 12 papers read: under 5-fold '
           'kept and noted, 5-fold or more refused); and values brought back, from its change at 893 papers read '
           '(commit 12770bd, "drops nothing (user decision)"), when code stopped refusing all three at 5-fold or more',
    'CU5': "two parts: an unprinted pH or temperature left empty, from its first commit (12 papers read); the verifier's "
           'unit where the column prints none, from its second later change (commit bdab76f, 6,839 papers read)',
}
PP6_BACK_WHAT = 'brought back'                # PP6's lines of values brought back at its change (the rest: noted records)
same('the later changes the act versions name', {k: later_changes(k) for k in ACT_LATER},
     {'IP2': [9317, 10019], 'PP6': [893], 'CU5': [69, 6839]})
CU5_UNIT = "stored with the verifier's unit"
CU5_PH = 'an unprinted pH or temperature left empty'
same("CU5's two parts drawn in the full list, by their lines (papers each)",
     sorted(Counter(r['what'][:len(CU5_UNIT)] if r['what'].startswith(CU5_UNIT) else r['what'][:len(CU5_PH)]
                    for r in since_rule('CU5') if keep_row('CU5', r)).items()), [(CU5_PH, 33), (CU5_UNIT, 33)])


def act_at(kid, row=None):
    """Papers read when the first rule version that did this kind of act entered."""
    if kid == 'IP2':
        return later_changes(kid)[0]
    if kid == 'PP6' and row is not None and row['what'].startswith(PP6_BACK_WHAT):
        return later_changes(kid)[0]
    if kid == 'CU5' and row is not None and row['what'].startswith(CU5_UNIT):
        return later_changes(kid)[1]
    return int(RULES[kid]['papers_read_at_rule'])


READ_BEFORE = {}                              # {rule: papers of its reach first read before the act's rule version}
for k in LEARNED:
    kid = k['id']
    if kid in ('CU5', 'PP6'):                 # by act, line by line
        READ_BEFORE[kid] = {r['pmid'] for r in since_rule(kid) if keep_row(kid, r) and r['pmid'] in REACH[kid]
                            and POS[r['pmid']] < act_at(kid, r)}
    else:
        READ_BEFORE[kid] = {p for p in REACH[kid] if POS[p] < act_at(kid)}
same('papers read before the rule, per rule of the full list', {kid: len(v) for kid, v in READ_BEFORE.items()},
     {'TL6': 2, 'RA10': 2609, 'TL10': 3, 'PP1': 3, 'IP8': 78, 'CU8': 8, 'IP6': 41, 'CU7': 7,
      'PP6': 48, 'IP2': 68, 'CU5': 24, 'PP5': 26, 'RA8': 6, 'RA11': 14, 'RA3': 8, 'IP4': 0})
PP6_ROWS = [r for r in since_rule('PP6') if keep_row('PP6', r)]
PP6_BACK_PAPERS = {r['pmid'] for r in PP6_ROWS if r['what'].startswith(PP6_BACK_WHAT)}
PP6_NOTED = {r['pmid'] for r in PP6_ROWS if not r['what'].startswith(PP6_BACK_WHAT)}
same('PP6 by act: papers with values brought back (read before 893); noted only (read before 893; before 12)',
     (len(PP6_BACK_PAPERS), sum(POS[p] < 893 for p in PP6_BACK_PAPERS), len(PP6_NOTED - PP6_BACK_PAPERS),
      sum(POS[p] < 893 for p in PP6_NOTED - PP6_BACK_PAPERS), sum(POS[p] < 12 for p in PP6_NOTED)), (48, 48, 511, 37, 0))
same("CU5: read before, by part (the verifier's unit before 6,839; pH or temperature before 12)",
     (len({r['pmid'] for r in since_rule('CU5') if keep_row('CU5', r) and r['what'].startswith(CU5_UNIT)
           and POS[r['pmid']] < 6839}),
      len({r['pmid'] for r in since_rule('CU5') if keep_row('CU5', r) and r['what'].startswith(CU5_PH)
           and POS[r['pmid']] < 12})), (24, 0))
C_BACK = (sum(len(READ_BEFORE[k['id']]) for k in C_ROWS), sum(len(REACH[k['id']]) for k in C_ROWS))
FULL_BACK = (sum(len(READ_BEFORE[k['id']]) for k in LEARNED), sum(len(REACH[k['id']]) for k in LEARNED))
same("c: rule-paper pairs read before the rule, of all pairs (c's eight; the full list)", (C_BACK, FULL_BACK),
     ((2751, 5076), (2945, 5911)))
same('c: the rule of b read before it (b counts all 121 at their catch, after the rule)',
     (len(READ_BEFORE[B_RULE]), len(REACH[B_RULE]) - len(READ_BEFORE[B_RULE])), (3, 118))
same('c: no paper is read before a rule that came first (rules at 12 papers read: IP4; and pH or temperature)',
     len(READ_BEFORE['IP4']), 0)

# ======================================================== data, panel d (right values refused until the rule changed)
# Right values code refused: a kind's `lost:` lines in catches_by_paper.csv (rules.csv lost_before_last_rule_change,
# lost_after_last_rule_change). Two kinds whose rule changed to keep such values: CU5 (code required a detail the paper
# omits) and PP6 (the printed kcat/Km disagrees with kcat / Km). CU5's losses stopped at two different changes, so its
# two parts are drawn apart: values of a paper that never names its organism (one paper, 168 values: commit 3c6a6b4,
# 'organism no longer required', the first later change) and values whose column prints no unit (the second later
# change, bdab76f, 'a unit_for_conversion stands in for an empty raw_unit'). taxonomy.tsv dates each change and lists
# who found the kind again; the dot at a change is in the colour of the latest such finding on or before its day.
TAX = {r['id']: r for r in csv.DictReader(open(ROOT / 'paper/figures/method_overview/v5/taxonomy.tsv', newline='',
                                               encoding='utf-8'), delimiter='\t')}


def rule_dates(kid):
    return [d.strip().split()[0] for d in TAX[kid]['rule_dates'].split(';')]


def found_again_by(kid, day):
    """Who found the kind again, latest on or before `day` (taxonomy.tsv `found_again`), as a's groups."""
    again = [e.strip().split(' ', 1) for e in TAX[kid]['found_again'].split(';')]
    when, route = max((d, r) for d, r in again if d <= day)
    return GROUP[route.split(':')[0].strip()]


for kid in ('CU5', 'PP6'):
    same(f'd: {kid}: one rule date per change (taxonomy.tsv; rules.csv)', len(rule_dates(kid)), 1 + len(later_changes(kid)))
same('d: what each change did, on its day (taxonomy.tsv guard)',
     [('organism is optional (9 Oct)' in TAX['CU5']['guard'], rule_dates('CU5')[1]),
      ('stands in for an empty raw_unit (23 Oct)' in TAX['CU5']['guard'], rule_dates('CU5')[2]),
      ('drops nothing' in TAX['PP6']['guard'] and '(10 Oct)' in TAX['PP6']['guard'], rule_dates('PP6')[1])],
     [(True, '2026-10-09'), (True, '2026-10-23'), (True, '2026-10-10')])


def losses(kid):
    return sorted((int(c['papers_read_at_first']), int(c['amount']), c['action'], c['pmid']) for c in CATCH
                  if c['id'] == kid and c['action'].startswith('lost'))


D_CURVES = []    # (name, kid, losses, the change that stopped them (papers read), who found them again before it)
cu5, pp6 = losses('CU5'), losses('PP6')
org_at, unit_at = later_changes('CU5')
D_CURVES.append(('organism', 'CU5', [x for x in cu5 if x[0] < org_at], org_at,
                 found_again_by('CU5', rule_dates('CU5')[1])))
D_CURVES.append(('ratio', 'PP6', pp6, later_changes('PP6')[0], found_again_by('PP6', rule_dates('PP6')[1])))
D_CURVES.append(('unit', 'CU5', [x for x in cu5 if x[0] >= org_at], unit_at, found_again_by('CU5', rule_dates('CU5')[2])))
D = {name: dict(kid=kid, pts=pts, at=at, who=who,
                before=sum(a for x, a, _, _ in pts if x < at), after=sum(a for x, a, _, _ in pts if x >= at),
                papers_before=len({p for x, *_, p in pts if x < at}), papers_after=len({p for x, *_, p in pts if x >= at}),
                stored=sum(a for _, a, act, _ in pts if act == 'lost: refused, now stored'))
     for name, kid, pts, at, who in D_CURVES}
same('d: per curve (refused before the change, after it; their papers; now in the catalogue; change at; found again '
     'by)', {n: (v['before'], v['after'], v['papers_before'], v['papers_after'], v['stored'], v['at'], v['who'])
             for n, v in D.items()},
     {'organism': (168, 0, 1, 0, 168, 69, 'code'), 'ratio': (36, 0, 9, 0, 36, 893, 'people'),
      'unit': (333, 2, 28, 1, 301, 6839, 'agents')})
same("d: CU5's two curves are rules.csv's losses before and after its last change",
     (D['organism']['before'] + D['unit']['before'], D['unit']['after']),
     (int(RULES['CU5']['lost_before_last_rule_change']), int(RULES['CU5']['lost_after_last_rule_change'])))
same("d: PP6's curve is rules.csv's", (D['ratio']['before'], D['ratio']['after']),
     (int(RULES['PP6']['lost_before_last_rule_change']), int(RULES['PP6']['lost_after_last_rule_change'])))
same("d: the organism curve is the change's own count (taxonomy.tsv values: 'N values (organism)')",
     D['organism']['before'], int(re.search(r'(\d+) values \(organism\)', TAX['CU5']['values']).group(1)))
same('d: the organism losses came after the first rule and before its change', [x[0] for x in D['organism']['pts']],
     [40])
PP6_BACK = Counter()
for c in since_rule('PP6'):
    if c['what'].startswith('brought back'):
        PP6_BACK[c['what']] += int(c['amount'])
same("d: values brought back when PP6's rule changed (code's refusals; verifiers' refusals for the ratio alone)",
     (PP6_BACK['brought back (ratio_non_closure)'], PP6_BACK['brought back (verifier_reject)']), (36, 77))
same('d: the first rule of CU5 and PP6 came at 12 papers read, at or before every loss drawn',
     (int(RULES['CU5']['papers_read_at_rule']), int(RULES['PP6']['papers_read_at_rule']),
      min(x[0] for v in D.values() for x in v['pts'])), (12, 12, 12))
# Words at a change's dot: timing only ('after ...'). The files date who found these losses again before the change;
# only PP6's commit names its cause (a person's decision, 'user decision'), and bdab76f names no review.
D_WORDS = {'code': 'brought back after code checks', 'people': 'brought back after a person’s decision',
           'agents': 'brought back after agents’ review'}
D_PARTS = {'code': [('after ', ''), ('code checks', 'b')],          # the art, under 'brought back': who, in bold; the
           'people': [('after ', ''), ('a person’s', 'b'), (' decision', '')],   # drop is the earlier values coming
           'agents': [('after ', ''), ('agents’', 'b'), (' review', '')]}       # back at once
same('d: the drawn words are the report words', {k: 'brought back ' + ''.join(t for t, _ in v) for k, v in D_PARTS.items()},
     D_WORDS)

# The art draws the values refused and not yet brought back: each refusal at its paper's first catch, and each paper's
# refused values that are in the catalogue now ('lost: refused, now stored') taken off where its recover line in log.tsv
# (to the evidence's cut) brought them back. A recover line counts rows, the evidence printed cells: 25736839's 9 cells
# were refused at both of its readings (18 rows; CLAUDE.md, 'Readers sometimes omit'), so its line keeps 18 and the
# curve takes off 9; that is why the change's commit says 310 values and the curve 301. The organism curve (one paper:
# refused at 40 papers read, read again the same night after the change at 69) stays within the y axis' line width at
# this scale; it is in the legend only (D['organism'], asserted above).
RECOVER = defaultdict(list)                   # reason: [(papers read then, pmid, rows kept)]
with open(ROOT / 'log.tsv', encoding='utf-8') as f:
    for ln in f:
        p = ln.rstrip('\n').split('\t')
        if len(p) > 2 and p[2] == 'recover' and p[0] <= LOG_CUT:
            kv = dict(x.split('=', 1) for x in p[3:] if '=' in x)
            RECOVER[kv.get('reason', '')].append((bisect.bisect_left(READ_TIMES, p[0]), p[1], int(kv['kept'])))
D_ART = {'ratio': 'ratio_non_closure', 'unit': 'missing:raw_unit'}     # the curves drawn, top to bottom: recover reason
ROWS_PER_CELL = {'25736839': 2}               # refused at both of its readings: its recover line keeps each cell twice
for name, reason in D_ART.items():
    v = D[name]
    stored = defaultdict(int)
    for x, a, act, p in v['pts']:
        if act == 'lost: refused, now stored':
            stored[p] += a
    rec = {p: (x, kept) for x, p, kept in RECOVER[reason]}
    same(f'd: {name}: one recover line per paper ({reason})', len(rec), len(RECOVER[reason]))
    same(f'd: {name}: the papers brought back are those whose refused values are in the catalogue now',
         sorted(rec), sorted(stored))
    same(f'd: {name}: rows each recover line kept, against the printed cells stored now',
         {p: kept for p, (x, kept) in rec.items()}, {p: n * ROWS_PER_CELL.get(p, 1) for p, n in stored.items()})
    v['back'] = sorted((rec[p][0], n, p) for p, n in stored.items())
    v['curve'] = [(0, 0)]                     # (papers read, values refused and not brought back), a step after each
    level = 0
    for x, a in sorted([(x, a) for x, a, _, _ in v['pts']] + [(x, -n) for x, n, _ in v['back']]):
        level += a
        v['curve'].append((x, level))
    v['peak'], v['end'] = max(y for _, y in v['curve']), level
    v['back_at'] = sorted({x for x, _, _ in v['back']})
same('d: drawn curves (peak, still out at the end, brought back at papers read, rule changed at, values back)',
     {n: (D[n]['peak'], D[n]['end'], D[n]['back_at'], D[n]['at'], sum(b for _, b, _ in D[n]['back'])) for n in D_ART},
     {'ratio': (36, 0, [883], 893, 36), 'unit': (333, 34, [6839], 6839, 301)})
same('d: each curve peaks before its change and is brought back within 10 papers read of it (0.06 mm here)',
     all(max(x for x, y in D[n]['curve'] if y == D[n]['peak']) < D[n]['at'] and
         abs(D[n]['back_at'][0] - D[n]['at']) <= 10 for n in D_ART), True)
same('d: still out at the end (no unit printed): kept out before the change, refused after it',
     (sum(a for x, a, act, _ in D['unit']['pts'] if act == 'lost: kept out' and x < D['unit']['at']),
      len({p for x, a, act, p in D['unit']['pts'] if act == 'lost: kept out' and x < D['unit']['at']}),
      D['unit']['after']), (32, 4, 2))
# d4: every value still out at the end was also refused for a second reason: its quote is not in the text, or no unit
# was given at all (no printed raw_unit and no unit_for_conversion from the reader or verifier, so code met an empty
# unit), so the 34 are not shown to be right values. From rejected.jsonl (append-only; read only): these papers' rows
# refused for 'missing:raw_unit' and checked by the evidence's cut, each paper's count asserted against its loss line.
STILL_OUT = defaultdict(int)                  # paper: values refused and never brought back (the curve's end)
for x, a, act, p in D['unit']['pts']:
    if act == 'lost: kept out':
        STILL_OUT[p] += a
same('d4: the values still out at the end, and their papers (the loss lines never brought back)',
     (sum(STILL_OUT.values()), len(STILL_OUT)), (D['unit']['end'], 5))
QUOTE, NO_UNIT, BOTH = 'its quote is not in the text', 'no unit given at all', 'quote not in the text, no unit either'
SECOND = defaultdict(Counter)                 # the second reason: {paper: values}
with open(ROOT / 'rejected.jsonl', encoding='utf-8') as f:
    for ln in f:
        if not any(p in ln for p in STILL_OUT):
            continue
        r = json.loads(ln)
        why = r.get('why') or []
        if (str(r.get('pmid')) not in STILL_OUT or 'missing:raw_unit' not in why or not r.get('checked')
                or r['checked'] > LOG_CUT):
            continue
        no_unit = (not r.get('raw_unit') and not r.get('unit_for_conversion')
                   and any(re.fullmatch(r'unknown_\w+_unit:', w) for w in why))
        SECOND[QUOTE if 'quote_not_in_paper' in why else NO_UNIT if no_unit else 'none'][str(r['pmid'])] += 1
        if 'quote_not_in_paper' in why and no_unit:
            SECOND[BOTH][str(r['pmid'])] += 1
same("d4: each paper's values still out are its rows refused for an empty unit in rejected.jsonl (to the cut)",
     {p: sum(SECOND[k][p] for k in (QUOTE, NO_UNIT, 'none') if k in SECOND) for p in STILL_OUT}, dict(STILL_OUT))
same('d4: the second reason each value still out was refused (values, papers); none without one',
     {k: (sum(v.values()), len(v)) for k, v in SECOND.items()},
     {QUOTE: (17, 3), NO_UNIT: (17, 2), BOTH: (2, 1)})
ORG_PAPER = D['organism']['pts'][0][3]
ORG_READS = []                                # the organism paper's add lines: (papers read then, kept, rejected)
with open(ROOT / 'log.tsv', encoding='utf-8') as f:
    for ln in f:
        p = ln.rstrip('\n').split('\t')
        if len(p) > 2 and p[2] == 'add' and p[1] == ORG_PAPER and p[0] <= LOG_CUT:
            kv = dict(x.split('=', 1) for x in p[3:] if '=' in x)
            ORG_READS.append((bisect.bisect_left(READ_TIMES, p[0]), int(kv['kept']), int(kv['rejected'])))
same('d (legend): the organism paper refused whole at its first reading, then kept whole when read again after the change',
     [(r[1], r[2]) for r in ORG_READS], [(0, 168), (168, 0)])
same('d (legend): its second reading came after the change of 69 papers read', ORG_READS[1][0] >= org_at, True)

# ============================================================ legend facts (not drawn; each from the files, checked)
# a: the known layer; rules sharpened later; the rules that entered between 6,508 and 7,510 papers read; the same day
KNOWN_IDS = [r['id'] for r in LRULES if a_group(r) == 'known']
LEG = {
    'known: with a count in later papers': sum(1 for k in KNOWN_IDS if int(RULES[k]['papers_since_rule_other_papers'] or 0)),
    'known: sharpened later (kinds, changes)': (sum(1 for k in KNOWN_IDS if int(RULES[k]['later_rule_changes'] or 0)),
                                                sum(int(RULES[k]['later_rule_changes'] or 0) for k in KNOWN_IDS)),
    'known: in force at the first paper, then by the 12th': (in_force(0, 'known'), in_force(12, 'known')),
    'later changes by status (kinds, changes)': {st: (sum(1 for k in RULES.values() if k['status'] == st
                                                          and int(k['later_rule_changes'] or 0)),
                                                      sum(int(k['later_rule_changes'] or 0) for k in RULES.values()
                                                          if k['status'] == st))
                                                 for st in ('rule', 'flag kept as printed', 'open')},
    'rules entered at 6,508 to 7,510 papers read, by finder': dict(sorted(Counter(
        a_group(r) for r in LRULES if 6508 <= int(r['papers_read_at_rule']) <= 7510).items())),
    'learned rules in force by the 12th paper': in_force(12) - in_force(12, 'known'),
}
DATED = [t for t in TAX.values() if t['first_found'] and t['rule_commit']]
LAG = {t['id']: (date.fromisoformat(t['rule_date']) - date.fromisoformat(t['first_found'])).days for t in DATED}
same('days from finding to rule, dated kinds', sorted(Counter(LAG.values()).items()), [(-2, 1), (0, 47), (1, 2), (2, 2)])
LEG['kinds with a dated finding and a rule, flag or guard; the same day; of them rules; rules the same day'] = (
    len(DATED), sum(1 for v in LAG.values() if v == 0), sum(1 for t in DATED if t['status'] == 'rule'),
    sum(1 for t in DATED if t['status'] == 'rule' and LAG[t['id']] == 0))
PP1_STEPS = defaultdict(set)
for r in since_rule('PP1'):
    if keep_row('PP1', r) and r['pmid'] in REACH['PP1']:
        PP1_STEPS['verifier' if r['step'] == 'Verify' else 'later checks'].add(r['pmid'])
LEG['b: papers caught by the verifier while reading, by later checks, by both'] = (
    len(PP1_STEPS['verifier']), len(PP1_STEPS['later checks']), len(PP1_STEPS['verifier'] & PP1_STEPS['later checks']))
LEG['b: papers first caught at the last later check of 10,220 papers read'] = sum(1 for x in AFTER.values() if x == 10220)
LEG['b: before the rule, papers whose values verifiers refused rather than corrected'] = sorted(
    {r['pmid'] for r in before_rows if r['action'] == 'kept out'})
LEG['d: losses that went on after the last change (kind: before, after)'] = {
    k: (int(RULES[k]['lost_before_last_rule_change']), int(RULES[k]['lost_after_last_rule_change']))
    for k in ('CU4', 'CU6', 'RA7')}
same('legend facts', LEG, {
    'known: with a count in later papers': 15, 'known: sharpened later (kinds, changes)': (10, 18),
    'known: in force at the first paper, then by the 12th': (11, 25),
    'later changes by status (kinds, changes)': {'rule': (28, 61), 'flag kept as printed': (2, 2), 'open': (1, 4)},
    'rules entered at 6,508 to 7,510 papers read, by finder': {'agents': 5, 'code': 1, 'people': 1, 'with': 7},
    'learned rules in force by the 12th paper': 7,
    'kinds with a dated finding and a rule, flag or guard; the same day; of them rules; rules the same day':
        (52, 47, 47, 43),
    'b: papers caught by the verifier while reading, by later checks, by both': (101, 23, 3),
    'b: papers first caught at the last later check of 10,220 papers read': 4,
    'b: before the rule, papers whose values verifiers refused rather than corrected': ['30290081'],
    'd: losses that went on after the last change (kind: before, after)': {'CU4': (28, 15), 'CU6': (17, 34),
                                                                           'RA7': (48, 147)}})

# More legend facts, each asserted (the critics' check of 16 November found them quoted but not counted here)
LEARN = table(EV / 'learning/learning.csv')                   # one row per random audit round
LIMIT = (tests['snapshot']['values_audited'], tests['snapshot']['wrong'],
         int(LEARN[0]['rules_in_force']), int(LEARN[0]['papers_read']),
         int(LEARN[-1]['rules_in_force']), int(LEARN[-1]['papers_read']), in_force(int(LEARN[-1]['papers_read'])))
same('the one limit: audited, wrong; rules in force at the first round (taken at 12 papers read, before most of that '
     "day's rules were committed) and at the last (the list's 71), and a's count at the last round",
     LIMIT, (12502, 69, 13, 12, 71, 10276, 73))
# The one limit's trend: no significant trend along papers read, by when values were audited or read
# (learning/tests.json logistic regressions, standard errors clustered by paper). The last rounds (the learning evidence's
# group 8, rounds 137-139) are its highest: 15 of 1,376 values (1.1%). They coincide with a change of reader model and
# paper mix: of the eight groups, theirs are the audited values most often read with Opus 5 and most often from papers
# found by search (learning/README.md, sections 5 and 7)
TREND = {t['label']: t['p'] for t in tests['logistic']}
L3 = tests['last_three_rounds']
G8 = [r for r in LEARN if r['group_of_rounds'] == LEARN[-1]['group_of_rounds']]
BINS = [r for r in table(EV / 'learning/learning_bins.csv') if r['axis'] == 'when audited']
LIMIT_LAST = (L3['rounds'], [int(r['round']) for r in G8], L3['values'], L3['wrong'],
              sum(int(r['values_audited']) for r in G8), sum(int(r['values_wrong']) for r in G8),
              round(100 * L3['wrong'] / L3['values'], 1),
              max(BINS, key=lambda b: float(b['share_read_with_opus5']))['group'],
              max(BINS, key=lambda b: float(b['share_from_search_papers']))['group'], LEARN[-1]['group_of_rounds'])
same('the one limit: no significant trend (wrong ~ papers read when audited; when read: p above 0.05)',
     [TREND['wrong (dropped or unit corrected) ~ papers read when audited'] > 0.05,
      TREND['wrong ~ papers read when the value was read'] > 0.05], [True, True])
same("the one limit: the last rounds (tests.json's rounds, learning.csv's last group; values audited and wrong in each; "
     "per cent), and the group whose audited values were most often read with Opus 5 and from papers found by search",
     LIMIT_LAST, ([137, 138, 139], [137, 138, 139], 1376, 15, 1376, 15, 1.1, '8', '8', '8'))
# a6: the list of 2 November (taxonomy.tsv, added by one commit) was written at 7,662 papers read; its last rule had
# entered at 7,510, and the two kinds found after it entered at 8,335 and 9,900. Papers read at the commit as
# count_rules.py counts them: its git time (local clock, to the minute, as log.tsv writes) among the first adds; no paper
# was first read in that minute, so a time to the second gives the same
LIST_ADDED = subprocess.run(['git', '-C', str(ROOT), 'log', '--diff-filter=A', '--format=%h %ci', '--',
                             'paper/figures/method_overview/v5/taxonomy.tsv'], capture_output=True, text=True,
                            check=True).stdout.split()
same('a6: the commit that added the list (taxonomy.tsv), and its day', (LIST_ADDED[0][:7], LIST_ADDED[1], len(LIST_ADDED)),
     ('c727c6b', '2026-11-02', 4))
LIST_AT = f'{LIST_ADDED[1]} {LIST_ADDED[2]}'[:16]
A6 = (bisect.bisect_left(READ_TIMES, LIST_AT), bisect.bisect_right(READ_TIMES, LIST_AT),
      max(int(r['papers_read_at_rule']) for r in LRULES), sorted(int(k['papers_read_at_rule']) for k in LATER))
same('a6: papers read when the list was written (none first read in its minute); its last rule entered at; the two '
     'found after it entered at', A6, (7662, 7662, 7510, [8335, 9900]))
same('a2: every rule rules.csv calls a rule is one of the 73 a stacks, none withdrawn',
     sorted(kid for kid, k in RULES.items() if k['status'] == 'rule'), sorted(A_IDS))
same("a2: the one refusal that became a flag: PP6's 5-fold refusal, at its change of 893 papers read",
     (RULES['PP6']['status'], later_changes('PP6'), 'drops nothing' in TAX['PP6']['guard']),
     ('flag kept as printed', [893], True))
# a draws each rule at learning/rules_by_papers.csv's papers read; b, c, the Extended Data list and legend c5 use
# rules.csv's. The two files differ for 16 rules: the learning file counts f171ab3's 11 rules from the start (0; its
# commit came after the first 3 papers were added, rules.csv's 3) and takes five commits' papers read from a minute-level
# log against rules.csv's second-level commit times. No b or c number depends on these.
ENTRY_VS_RULES = {r['id']: (int(r['papers_read_at_rule']), int(RULES[r['id']]['papers_read_at_rule'])) for r in LRULES
                  if int(r['papers_read_at_rule']) != int(RULES[r['id']]['papers_read_at_rule'])}
same("a: rules whose papers read at the rule differ between the learning file (a) and rules.csv (b, c)",
     ENTRY_VS_RULES, {**{k: (0, 3) for k in ('CU1', 'DB1', 'IP1', 'IP11', 'IP18', 'PP2', 'PP4', 'RA1', 'RA4', 'RA5',
                                             'RA6')},
                      'CU4': (9, 3), 'CU2': (254, 239), 'IP7': (942, 929), 'PR10': (1245, 1242), 'PR11': (4205, 4203)})
same("a: the 11 rules counted from the start are f171ab3's", {RULES[k]['rule_commit'] for k, v in ENTRY_VS_RULES.items()
                                                             if v == (0, 3)}, {'f171ab3'})
# a7: the list of 2 November puts 68 rules in Fig. 1's four steps, slipped digits (PP4) among its learned; here PP4 is
# with the known (a_group), the database check's 3 are added and the 2 found after the list. Since its final pass of
# 16 Nov, Fig. 1 itself draws all 73 by step (Read 16, Convert 12 with X1 and X2, Verify 7, Check 35, Decide 3)
FIG1 = Counter(('known' if r['first_found_by'] == 'old system' else 'learned') for r in LRULES
               if RULES[r['id']]['rule_step'] in ('Read', 'Convert', 'Verify', 'Check'))
DBCHECK = Counter(a_group(r) for r in LRULES if RULES[r['id']]['rule_step'] == 'Database check')
same("a7: Fig. 1's four steps (known, learned with PP4); the database check's 3 (a's groups); after the list (steps)",
     (dict(FIG1), dict(DBCHECK), sorted((k['id'], k['rule_step']) for k in LATER)),
     ({'known': 23, 'learned': 45}, {'known': 1, 'with': 1, 'agents': 1}, [('X1', 'Convert'), ('X2', 'Convert')]))
same("a7: 25 known = Fig. 1's 23 + slipped digits + the database check's 1; 48 learned = 45 - 1 + 2 + 2",
     (FIG1['known'] + 1 + DBCHECK['known'], FIG1['learned'] - 1 + (sum(DBCHECK.values()) - DBCHECK['known']) + len(LATER)),
     (A_COUNT['known'], sum(A_COUNT.values()) - A_COUNT['known']))
B_RATES = (round(1000 * len(BEFORE) / RULE_AT, 1), round(1000 * BEFORE_VALUES / RULE_AT),
           round(1000 * len(AFTER) / (NOW - RULE_AT), 1), round(1000 * sum(REACH['PP1'].values()) / (NOW - RULE_AT)),
           NOW - RULE_AT)
same('b7: papers and values caught per 1,000 papers read, before the rule and since it (papers read since)',
     B_RATES, (5.4, 161, 13.5, 153, 8991))
PP1_LATER_LINES = [r for r in since_rule('PP1') if keep_row('PP1', r) and r['pmid'] in REACH['PP1'] and r['step'] != 'Verify']
CONFLICT_FIXES = set()
with open(ROOT / 'log.tsv', encoding='utf-8') as f:
    for ln in f:
        p = ln.rstrip('\n').split('\t')
        if len(p) > 2 and p[2] == 'unitfix' and p[0] <= LOG_CUT and any('blind re-read conflict judged from the paper' in x
                                                                             for x in p[3:]):
            CONFLICT_FIXES.add(p[1])
same("b2: later checks include conflicts between two readings judged from the paper (log.tsv unitfix reasons)",
     sorted(CONFLICT_FIXES & {r['pmid'] for r in PP1_LATER_LINES}), ['21306440', '25577102', '36394293'])
CENSORED_PASS = set()
with open(ROOT / 'log.tsv', encoding='utf-8') as f:
    for ln in f:
        p = ln.rstrip('\n').split('\t')
        if len(p) > 2 and p[2] == 'add' and p[0] <= LOG_CUT and 'pass=censored' in p[3:]:
            CENSORED_PASS.add(p[1])
IP6_LINES = [r for r in since_rule('IP6') if keep_row('IP6', r)]
same('c3: limits row, papers first read before the rule, of them read again in a pass for these values alone; natural '
     'forms: lines, all corrected by code from the checked list, papers first read before the rule',
     (len(READ_BEFORE['RA10']), len(READ_BEFORE['RA10'] & CENSORED_PASS), len(IP6_LINES),
      sum(r['what'] == 'older value: natural form moved from variant to enzyme' for r in IP6_LINES),
      len(READ_BEFORE['IP6'])), (2609, 2601, 44, 44, 41))
same('d3: papers read since the kcat/Km change', NOW - later_changes('PP6')[0], 9383)


# ================================================================================================= drawing
SIZE = 6.5                                     # every label, axis label and tick label (pt)
TOTAL = 7.0                                    # the bold totals (b's 7 and 121; d's ends); titles 6.8, letters 8
plt.rcParams.update({'axes.labelsize': SIZE, 'xtick.labelsize': SIZE, 'ytick.labelsize': SIZE})
SCRIPT = {'sup': 0.42, 'sub': -0.22}           # rise of a script, in ems of its line (as lean.rich)
LINE = 2.9                                     # mm between the lines of a callout or a block
NAME_PITCH = 4.4                               # a: mm between the head and each finder's name, evenly
GAP = 0.8                                      # c: mm between one finder's rows and the next's, within a group
FILLED, OPEN = 4.9, 3.6                        # c: the dots' sizes (pt), 1.73 and 1.27 mm across
LINE_IN_SLOT = 1.1                             # c: mm from a row's top to its filled dot (and its label and count)
OPEN_DROP = 1.6                                # c: mm from a row's filled dot down to its open dot: the two never touch
HEAD_ABOVE = 3.6                               # c: mm from a group's head up from its first row (rows are 4 mm apart)
HEAD_SPACE = 4.4                               # c: mm added between the two groups for the second head
WORDS = []                                     # every line of words drawn, for the README's count
TEXTS = []                                     # (line, its text artists) for every line drawn: check_layout's input


def rich(pg, x, y, parts, size=SIZE, ha='left', weight='normal', color=INK):
    """One line set from runs (text, kind), its baseline at y mm: kind '' plain, 'i' italic, 'sup' raised, 'sub'
    lowered, 'b' bold (a key number or word inside a plain line; 16 Nov, the owner asked for bold key words).
    lean.rich, with a script never under 5 pt (0.72 of its line otherwise) and the bold weight measured.
    Returns the line's ends, mm."""
    renderer = pg.fig.canvas.get_renderer()
    runs = []
    for text, kind in parts:
        fs = max(5.0, 0.72 * size) if kind in SCRIPT else size
        style = 'italic' if kind == 'i' else 'normal'
        w = 'bold' if kind == 'b' else weight
        prop = FontProperties(family='Arial', style=style, weight=w, size=fs)
        width = renderer.get_text_width_height_descent(text, prop, ismath=False)[0] / pg.fig.dpi * 25.4
        runs.append((text, style, fs, SCRIPT.get(kind, 0.0) * size * 25.4 / 72, width, w))
    at = x - sum(r[4] for r in runs) * {'left': 0.0, 'center': 0.5, 'right': 1.0}[ha]   # r[4]: the run's width
    x0, drawn = at, []
    for text, style, fs, lift, width, w in runs:
        drawn.append(pg.fig.text(at / lean.W, 1 - (y - lift) / pg.h, text, fontsize=fs, fontstyle=style,
                                 fontweight=w, color=color, va='baseline', ha='left'))
        at += width
    line = text_of(parts)
    WORDS.append(line)
    TEXTS.append((line, drawn))
    return x0, at


def label(pg, x, y, parts, size=SIZE, **kw):
    """A line of text whose capitals are centred on y mm (a row's dot), set by `rich`."""
    if isinstance(parts, str):
        parts = [(parts, '')]
    return rich(pg, x, lean.baseline(y, size), parts, size=size, **kw)


def title(pg, letter, x, y, name, rest=''):
    n = len(pg.fig.texts)
    pg.title(letter, x, y, name, rest)
    TEXTS.extend((t.get_text(), [t]) for t in pg.fig.texts[n:])
    WORDS.append(f'{name} {rest}')


def dot(ax, x, y, colour, size, marker='o', mew=0.9, z=3, hollow=False, edge=None, halo=0.0):
    """One mark: fill at alpha 0.6 over a white disc (no line shows through), edge opaque (in the same colour unless
    given); hollow: white inside; halo: a white ring this many points wide around it, so it stands off a line."""
    if halo:
        ax.plot([x], [y], marker=marker, markersize=size + 2 * halo, markerfacecolor='white', markeredgecolor='none',
                linestyle='none', zorder=z - 0.05, clip_on=False)
    ax.plot([x], [y], marker=marker, markersize=size, markerfacecolor='white', markeredgecolor='none',
            linestyle='none', zorder=z, clip_on=False)
    ax.plot([x], [y], marker=marker, markersize=size, markerfacecolor='white' if hollow else colour + '99',
            markeredgecolor=edge or colour, markeredgewidth=mew, linestyle='none', zorder=z + 0.1, clip_on=False)


def frame(ax, left_spine=False):
    for s in ('top', 'right') if left_spine else ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)


def papers_axis(ax, labels, title=None):
    """The papers-read scale a, b and d share, from 0. No grid: Fig. 3's panels along a scale (b, g) have none, and
    the words of b and d then sit on nothing (the critics' check: white boxes behind them cut grid lines into stubs)."""
    ax.set_xlim(0, NOW + 150)
    ticks = list(range(0, 10001, 2000))
    ax.set_xticks(ticks)
    ax.set_xticklabels([f'{t:,}' for t in ticks] if labels else [])
    ax.tick_params(axis='x', length=2 if labels else 0, pad=1.5)
    frame(ax, left_spine=True)
    ax.spines['bottom'].set_visible(True)
    if labels if title is None else title:      # d's first axis: tick labels, no title (its second carries it)
        ax.set_xlabel('Papers read', labelpad=2)


def mm_of(ax, left, top, width, height):
    """Data (x, y) of an axes placed at (left, top, width, height) mm to page mm."""
    def at(x, y):
        x_lo, x_hi = ax.get_xlim()
        y_lo, y_hi = ax.get_ylim()
        return left + width * (x - x_lo) / (x_hi - x_lo), top + height * (1 - (y - y_lo) / (y_hi - y_lo))
    return at


def data_of(ax, left, top, width, height):
    """Page mm to data (x, y) of an axes placed at (left, top, width, height) mm: mm_of the other way."""
    def at(x, y):
        x_lo, x_hi = ax.get_xlim()
        y_lo, y_hi = ax.get_ylim()
        return x_lo + (x - left) / width * (x_hi - x_lo), y_lo + (1 - (y - top) / height) * (y_hi - y_lo)
    return at


def steps(first, x_start, x_end):
    """A cumulative step through the papers' first catches: x, y, the count."""
    xs, ys, c = [x_start], [0], 0
    for x in sorted(first.values()):
        xs += [x, x]
        ys += [c, c + 1]
        c += 1
    return xs + [x_end], ys + [c], c


def mm_box(pg, drawn):
    """The box of a line's runs, mm from the page's top left: (x0, y0, x1, y1)."""
    pg.fig.canvas.draw()
    bs = [t.get_window_extent() for t in drawn]
    fw, fh = pg.fig.bbox.width, pg.fig.bbox.height
    return (min(b.x0 for b in bs) / fw * lean.W, (1 - max(b.y1 for b in bs) / fh) * pg.h,
            max(b.x1 for b in bs) / fw * lean.W, (1 - min(b.y0 for b in bs) / fh) * pg.h)


def panel_a(pg, x0, top, left, right, h, limit):
    """Rules written against papers read, stacked by who first found the error each rule answers. The known layer is
    named inside itself; the y axis ticked at 0, the known layer's top and the total (bold); the four learned layers
    named right of the stack, evenly spaced in stack order, each with its count beside a dot in its colours, under the
    head 'Learned from errors found by' (also c's key and d's dots' key)."""
    title(pg, 'a', x0, 4, 'Rules written')
    ax = pg.box(left, top, right - left, h)
    papers_axis(ax, True)
    ymax = 78
    ax.set_ylim(0, ymax)
    ax.tick_params(axis='y', length=2, pad=1.2)
    ax.set_ylabel('Rules', labelpad=2)
    # from the 12th paper read (32 rules): the 21 rules written within the first 12 papers (11 in force at the first)
    # would draw a line down to 11 at the y axis, 0.07 mm wide (the legend gives both numbers)
    first = 12
    same('a: rules in force at the first paper and at the 12th', (in_force(0), in_force(first)), (11, 32))
    xs = sorted({first, NOW} | {p for p, _ in ENTRY if p > first})
    low = [0] * len(xs)
    ends = {}
    for who in ORDER:
        high = [lo + in_force(x, who) for lo, x in zip(low, xs)]
        _, fill, line = FINDER[who]
        ax.fill_between(xs, low, high, step='post', facecolor=fill + '99', edgecolor='none', zorder=2)
        ax.step(xs, high, where='post', color=line, linewidth=0.8, zorder=3)
        ends[who] = ((low[-1] + high[-1]) / 2, high[-1] - low[-1])
        low = high
    total = low[-1]
    same('a: rules at the end of the axis', total, 73)
    same('a: layer counts at the end', {w: n for w, (_, n) in ends.items()}, dict(A_COUNT))
    same('a: rules learned from errors (c: of 48)', total - ends['known'][1], 48)
    known = ends['known'][1]
    ax.set_yticks([0, known, total])            # the known layer's top and the stack's end: the total on its own line
    ticks = ax.set_yticklabels(['0', f'{known}', f'{total}'])
    ticks[-1].set_fontweight('bold')
    same('a: y ticks (0, the known layer, the total in bold)', [t.get_text() for t in ticks], ['0', '25', '73'])
    at = mm_of(ax, left, top, right - left, h)
    xk, yk = at(500, ends['known'][0])
    label(pg, xk, yk, [(f'{known}', 'b'), (' from checking databases against papers', '')])   # named inside itself
    # the head level with the stack's end, then the four names under it, evenly spaced, from the top layer down (the
    # head's first letter over the dots' left edge: each dot's centre at right + 2.3, its edge 0.95 mm from it)
    y_head = at(0, total)[1] + 0.6
    far = label(pg, right + 1.35, y_head, 'Learned from errors found by')[1]
    for i, who in enumerate(('code', 'agents', 'with', 'people')):
        y = y_head + NAME_PITCH * (i + 1)
        name, fill, line = FINDER[who]
        dot(pg.canvas(right + 0.8, y - 1.5, 3, 3), 1.5, 1.5, fill, 4.6, mew=0.8, edge=line)
        far = max(far, label(pg, right + 3.7, y, [(f'{name} ', ''), (f'{ends[who][1]}', 'b')])[1])   # the count bold
    if far > limit:
        raise SystemExit(f"a's names end at {far:.1f} mm, past {limit:.1f} mm")
    return far


def panel_b(pg, x0, top, left, right, h):
    """The rule of c's bold row, from start to finish: papers caught before the rule (an open green step to its last
    catch), the rule (a thin ink line) rising to the auditing agent's find (a mint dot) with its words, and papers
    caught since the rule (green, filled); a later catch by a verifier marked on the curve (mint: a checking agent)."""
    title(pg, 'b', x0, 4, 'Misprinted unit headers caught')
    ax = pg.box(left, top, right - left, h)
    papers_axis(ax, True)
    ymax = 172
    ax.set_ylim(0, ymax)
    ax.set_yticks([0, 50, 100, 150])
    ax.tick_params(axis='y', length=2, pad=1.2)
    ax.set_ylabel('Papers caught', labelpad=2)
    at = mm_of(ax, left, top, right - left, h)
    back = data_of(ax, left, top, right - left, h)
    unit = ymax / h                                # data units per mm

    last_before = max(BEFORE.values())
    same('b: the step before the rule ends at its last catch, short of the rule (papers read)', (last_before, RULE_AT),
         (1007, 1285))
    bx, by, nb = steps(BEFORE, 0, last_before)    # before the rule: an open step, CatLog's green, no fill
    ax.plot(bx, by, color=GREEN, linewidth=0.9, zorder=3, solid_joinstyle='miter')
    axx, ayy, na = steps(AFTER, RULE_AT, NOW)     # since the rule: CatLog's catches, filled
    ax.fill_between(axx, ayy, color=GREEN + '99', linewidth=0, zorder=1)
    ax.plot(axx, ayy, color=GREEN, linewidth=0.9, zorder=2)
    same('b: papers drawn before, since the rule', (nb, na), (7, 121))
    x7, y7 = at(last_before, nb)
    label(pg, x7 - 0.3, y7 - 2.2, f'{nb}', size=TOTAL, weight='bold', color=GREEN, ha='center')
    label(pg, right + 1.2, at(NOW, na)[1], f'{na}', size=TOTAL, weight='bold', color=GREEN)

    # the rule and the find, at the same papers read: a thin ink line from the axis up to the auditing agent's mint
    # dot, the find's words beside the dot (the factor in bold, who found it, what was printed: as Fig. 3g sets its
    # factors), 'rule' left of the line
    y_find = 160                                   # above the top tick, so the dot is not read as a count
    ax.plot([RULE_AT, RULE_AT], [0, y_find - 0.7 * unit], color=INK, linewidth=0.6, zorder=4, solid_capstyle='butt')
    dot(ax, RULE_AT, y_find, MINT, 4.6, mew=0.9, z=5)
    xr, yr = at(RULE_AT, y_find)
    lx = xr + 1.5
    rich(pg, lx, lean.baseline(yr), [('×60', '')], weight='bold')
    rich(pg, lx, lean.baseline(yr) + LINE, [('found by ', ''), ('an auditing agent', 'b')])   # who, bold, as d
    rich(pg, lx, lean.baseline(yr) + 2 * LINE, [('min', ''), ('−1', 'sup'), (' printed for s', ''), ('−1', 'sup')])
    label(pg, xr - 1.0, yr + LINE, 'rule', ha='right', weight='bold')

    # a later catch the rule made: 12226525's nM header, a million-fold, caught by its verifier: a mint dot (checking
    # agents) on the green curve of CatLog's catches, a white ring setting it off the line
    y_dot = sum(1 for v in AFTER.values() if v <= X10_6)
    same('b: the x10^6 paper is the 19th caught since the rule', y_dot, 19)
    y_text = 92                                    # the block's first baseline, in data units
    block = []
    x6, y6 = at(X10_6, y_text)
    for i, parts in enumerate(([('×10', ''), ('6', 'sup')], [('caught by ', ''), ('a verifier', 'b')], [('nM printed for mM', '')])):
        rich(pg, x6 - 0.4, y6 + i * LINE, parts, weight='bold' if i == 0 else 'normal')
        block.append(TEXTS[-1])
    low_text = max(mm_box(pg, drawn)[3] for _, drawn in block)       # the block's lowest ink, mm
    ax.plot([X10_6, X10_6], [y_dot + 1.0 * unit, back(0, low_text + 1.0)[1]], color=LEADER, linewidth=0.5, zorder=4)
    dot(ax, X10_6, y_dot, MINT, 4.6, mew=0.9, z=5, halo=0.8)
    # every callout clears the curve of catches by 1 mm or more: the curve rises left to right, so the highest it gets
    # under a line is its count at the line's right end
    for line, drawn in block + TEXTS[-len(block) - 4:-len(block)]:
        x_0, _, x_1, y_1 = mm_box(pg, drawn)
        x_data, y_data = back(x_1, y_1)
        under = sum(1 for v in AFTER.values() if v <= x_data) if x_data >= RULE_AT else 0
        if y_data - under < 1.0 * unit:
            raise SystemExit(f"b: {line!r} comes within 1 mm of the curve ({y_data:.0f} against {under})")
    return ax


def panel_c(pg, title_y, top, left_lab, ax_l, ax_r, rowh, key_end, gap=GAP):
    """Eight rules learned from errors in two groups (errors kept out or corrected; right values no longer lost), each
    under its head, rows by finder (as a's names run) and then by reach, `gap` mm between finders: a filled dot at all
    papers the rule acted on, its count beside it (log axis), in the colour of who found the error (a's names); b's
    rule in bold. No key: a's names are the colour key. The first head sits above the axes; `top` is the axes' top, mm.
    The papers first read before each rule (READ_BEFORE) are for the legend only; the owner dropped their open dots
    (16 Nov: "yeah drop")."""
    n_texts = len(TEXTS)
    title(pg, 'c', 2, title_y, 'Rules learned from errors')   # '(8 of 48)' left the title for the legend (the owner, 18 Nov 2026)
    title_end = max(mm_box(pg, drawn)[2] for _, drawn in TEXTS[n_texts:])
    groups = [[k for k in C_ROWS if k['effect'] == e] for e in C_HEADS]
    same('c: rows per group (errors kept out or corrected; right values no longer lost)', [len(g) for g in groups], [4, 4])
    same('c: finders drawn, in a group, as a\'s names run', all([k['who'] for k in g] ==
                                                                [w for w in C_ORDER for k in g if k['who'] == w]
                                                                for g in groups), True)
    line_y, head_y, y = {}, [], 0.0
    for gi, rows in enumerate(groups):
        if gi:
            y += HEAD_SPACE
        head_y.append(top + y + LINE_IN_SLOT - HEAD_ABOVE)
        prev = None
        for k in rows:
            if prev is not None and k['who'] != prev:
                y += gap
            line_y[k['id']] = y + LINE_IN_SLOT
            y += rowh
            prev = k['who']
    ax = pg.box(ax_l, top, ax_r - ax_l, y)
    ax.set_xscale('log')
    ax.set_xlim(0.75, 10000)                    # from 0.75, so a dot at 1 stays inside the axes
    ax.xaxis.set_major_locator(FixedLocator([1, 10, 100, 1000, 10000]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{int(v):,}'))
    ax.xaxis.set_minor_locator(FixedLocator([m * 10 ** e for e in range(4) for m in range(2, 10)]))  # none below 1
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(y, 0)                           # data y = mm from the axes' top
    ax.set_yticks([])
    ax.grid(axis='x', color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    frame(ax)
    ax.spines['bottom'].set_bounds(1, 10000)    # the axis line from 1 paper: no marks for fractions of a paper
    ax.tick_params(axis='x', pad=1.5)
    ax.set_xlabel('Papers the rule acted on', labelpad=2)
    x_lo, x_hi = ax.get_xlim()
    span = math.log10(x_hi) - math.log10(x_lo)
    for (e, head), hy in zip(C_HEADS.items(), head_y):
        label(pg, left_lab, hy, head, ha='right', weight='bold')
    drawn = {}
    for k in C_ROWS:
        yc = line_y[k['id']]
        colour = FINDER[k['who']][1]
        n_all = len(REACH[k['id']])
        dot(ax, n_all, yc, colour, FILLED, mew=1.0)
        drawn[k['id']] = n_all
        x_dot = ax_l + (ax_r - ax_l) * (math.log10(n_all) - math.log10(x_lo)) / span
        label(pg, x_dot + 1.5, top + yc, f'{n_all:,}')                    # every count plain, as the row labels
        parts = LABEL[k['id']] + ([(B_MARK, '')] if k['id'] == B_RULE else [])   # all plain (16 Nov, the owner: "why whole
        label(pg, left_lab, top + yc, parts, ha='right')                          # sentence in 4c?", then "dont make that b bold")
    same('c: dots drawn per row (all papers the rule acted on)', drawn, {k['id']: len(REACH[k['id']]) for k in C_ROWS})
    if title_end > key_end:
        raise SystemExit(f"c's title ends at {title_end:.1f} mm, past {key_end:.1f} mm (d's letter)")
    return top + y                              # the axis line, mm


C_WHEN = False   # c: when each change came (papers read) in the words on the art too; the legend gives it either way


def panel_d(pg, x0, title_y, top, left, width):
    """Right values code refused, by why it refused them: one bar per reason on one values axis, the values brought back
    (green) and those still out (red), and in words how many came back after whose finding.

    Since 18 Nov 2026 this is panel c (the owner dropped the old c, whose rules Fig. 3a lists in full). Until then the
    two reasons were red step curves along papers read, which the owner found misleading: the axis to 10,000 'make it
    feel like 10k paper read or sth', when the values came from 9 and 28 papers. When each change came is in the
    legend; fresh readers compared the step curves with these bars before the change (scratchpad fig4c_options)."""
    title(pg, 'c', x0, title_y, 'Right values refused, then brought back')
    NAME = {'ratio': KM + [(' and ', '')] + K + [(' ÷ ', '')] + M + [(' differ 5-fold or more', '')],   # what the
            'unit': [('No unit in the column header', '')]}          # check compares (fresh readers, 18 Nov 2026)
    BACK = {n: sum(b for _, b, _ in D[n]['back']) for n in D_ART}
    same('c: brought back, still out at the end, refused in all, papers refused before the change, the change at',
         {n: (BACK[n], D[n]['end'], D[n]['before'] + D[n]['after'], D[n]['papers_before'], D[n]['at']) for n in D_ART},
         {'ratio': (36, 0, 36, 9, 893), 'unit': (301, 34, 335, 28, 6839)})
    same('c: brought back plus still out is all refused', all(BACK[n] + D[n]['end'] == D[n]['before'] + D[n]['after']
                                                                for n in D_ART), True)
    vmax = 350.0
    mm = width / vmax                                  # mm per value
    tops = (top + C_FIRST, top + C_FIRST + C_STEP)     # each bar's top, page mm
    ax = pg.box(left, top, width, C_H)
    ax.set_xlim(0, vmax)
    ax.set_ylim(C_H, 0)                                # y in mm down from the axes' top
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.set_yticks([])
    ax.set_xticks([0, 100, 200, 300])
    ax.set_xticklabels(['0', '100', '200', '300'])
    ax.tick_params(axis='x', length=2, pad=1.5)
    ax.set_xlabel('Values', labelpad=2)
    for i, name in enumerate(D_ART):
        v, back, out = D[name], BACK[name], D[name]['end']
        y = tops[i] - top
        rich(pg, left, tops[i] - 1.3, NAME[name])      # the reason, over its bar
        ax.add_patch(Rectangle((0, y), back, C_BAR, facecolor=GREEN + '99', edgecolor=GREEN, linewidth=0.6))
        if out:
            ax.add_patch(Rectangle((back, y), out, C_BAR, facecolor=RED + '99', edgecolor=RED, linewidth=0.6))
        end = left + (back + out) * mm + 1.6           # the words start just right of the bar
        mid = tops[i] + C_BAR / 2
        when = [(f' at {v["at"]:,} papers read', '')] if C_WHEN else []
        who = [(', ', '')] + D_PARTS[v['who']]          # after whose finding, the key word in bold
        if out:
            label(pg, end, mid - 1.5, [(f'{back}', 'b'), (' brought back', '')] + when + who)
            label(pg, end, mid + 1.6, [(f'{out}', 'b'), (' still out', '')], color=RED)
        else:
            label(pg, end, mid, [('all ', ''), (f'{back}', 'b'), (' brought back', '')] + when + who)
    return top + C_H


def panel_rules(pg, x0, title_y, top, label_right, ax_r, rowh, key_x):
    """d (since 18 Nov 2026, evening): the rules and flags learned from errors, the full list of 16 (LEARNED), as
    Extended Data 7 and Fig. 3a drew them. Two groups under their heads; within a group, rows by finder as a's names
    run (0.8 mm between finders), then by reach. Each row: a filled dot at all papers the rule acted on, in the colour
    of who found the error, its count beside it (log axis from 10: no rule acted on fewer). The rule b follows is
    marked '(b)'. The key of who found the error stands at key_x, on the title's line and the next: a cold read found
    the dots' colours undecoded without it, though a's key names the same finders."""
    title(pg, 'd', x0, title_y, 'Rules and flags learned from errors')
    x = x_first = label(pg, key_x, title_y, 'Error found by')[1] + 1.6
    y_key = title_y
    for i, who in enumerate(C_ORDER):
        if i == 2:                                     # the second line starts under the first name's dot
            x, y_key = x_first, title_y + 3.4
        name, colour = FINDER[who][:2]
        dot(pg.canvas(x, y_key - 1.5, 3, 3), 1.5, 1.5, colour, 4.6)
        x = label(pg, x + 2.9, y_key, name)[1] + 2.6
    groups = [sorted((k for k in LEARNED if k['effect'] == e), key=lambda k: (C_ORDER.index(k['who']), -k['papers'])) for e in EFFECT]
    same('d: rows per group, as Extended Data 7 runs them', [[k['id'] for k in g] for g in groups],
         [['PP1', 'IP2', 'PP5', 'RA3', 'IP4', 'IP8', 'RA8', 'RA11', 'IP6', 'CU7'], ['TL6', 'RA10', 'TL10', 'PP6', 'CU8', 'CU5']])
    row_label = lambda k: LABEL[k['id']] + ([(' (b)', '')] if k['id'] == B_RULE else [])
    line_y, head_y, y = {}, [], 0.0
    for gi, group in enumerate(groups):
        if gi:
            y += HEAD_SPACE
        head_y.append(top + y + LINE_IN_SLOT - HEAD_ABOVE)
        prev = None
        for k in group:
            if prev is not None and k['who'] != prev:
                y += GAP
            line_y[k['id']] = y + LINE_IN_SLOT
            y += rowh
            prev = k['who']
    lo, decades = 7.0, (10, 100, 1000, 10000)
    same('d: no rule acted on fewer than 10 papers', min(k['papers'] for k in LEARNED) >= 10, True)
    ax_l = label_right + 2.0
    ax = pg.box(ax_l, top, ax_r - ax_l, y)
    ax.set_xscale('log')
    ax.set_xlim(lo, 10000)
    ax.xaxis.set_major_locator(FixedLocator(decades))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{int(v):,}'))
    ax.xaxis.set_minor_locator(FixedLocator([m * d for d in decades[:-1] for m in range(2, 10)]))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(y, 0)
    ax.set_yticks([])
    ax.grid(axis='x', color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    for sp in ('top', 'right', 'left'):
        ax.spines[sp].set_visible(False)
    ax.spines['bottom'].set_bounds(10, 10000)
    ax.tick_params(axis='x', pad=1.5)
    ax.set_xlabel('Papers the rule acted on', labelpad=2)
    span = math.log10(10000) - math.log10(lo)
    x_mm = lambda n: ax_l + (ax_r - ax_l) * (math.log10(n) - math.log10(lo)) / span
    for name, hy in zip(EFFECT.values(), head_y):
        label(pg, label_right, hy, name, ha='right', weight='bold')
    drawn = {}
    for k in (k for g in groups for k in g):
        yc, colour, n = line_y[k['id']], FINDER[k['who']][1], len(REACH[k['id']])
        dot(ax, n, yc, colour, FILLED, mew=1.0)
        drawn[k['id']] = n
        label(pg, x_mm(n) + 1.5, top + yc, f'{n:,}')
        label(pg, label_right, top + yc, row_label(k), ha='right')
    same('d: a dot per rule at the papers it acted on', drawn, {k['id']: k['papers'] for k in LEARNED})
    return top + y


def check_layout(pg, margin=1.0):
    """Stop the build when two texts overlap (bounding boxes, a line of runs as one) or a text comes within `margin`
    mm of the page's edge. Returns the extreme edges of the text, mm (left, top, right, bottom)."""
    pg.fig.canvas.draw()
    fw, fh = pg.fig.bbox.width, pg.fig.bbox.height

    def mm(bs):
        return (min(b.x0 for b in bs) / fw * lean.W, (1 - max(b.y1 for b in bs) / fh) * pg.h,
                max(b.x1 for b in bs) / fw * lean.W, (1 - min(b.y0 for b in bs) / fh) * pg.h)

    boxes = [(line, mm([t.get_window_extent() for t in drawn])) for line, drawn in TEXTS if line.strip()]
    for ax in (ax for ax in pg.fig.axes if ax.axison):     # canvases for marks placed by hand draw no ticks
        for t in ax.get_xticklabels() + ax.get_yticklabels():
            if t.get_visible() and t.get_text():
                boxes.append((f'tick {t.get_text()}', mm([t.get_window_extent()])))
        for lab in (ax.xaxis.label, ax.yaxis.label):
            if lab.get_text():
                boxes.append((f'axis label {lab.get_text()}', mm([lab.get_window_extent()])))
    for i, (n1, a) in enumerate(boxes):
        if a[0] < margin or a[1] < margin or a[2] > lean.W - margin or a[3] > pg.h - margin:
            raise SystemExit(f'{n1!r} reaches the page edge: {a}')
        for n2, b in boxes[i + 1:]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                raise SystemExit(f'texts overlap: {n1!r} {a} and {n2!r} {b}')
    return tuple(f(b[j] for _, b in boxes) for j, f in enumerate((min, min, max, max)))


def words(fig):
    """Words on the art, for the README: tokens with a letter in them (tick numbers and counts are not words), in
    every line drawn and the axis labels; the panel letters are left out."""
    n = sum(sum(any(ch.isalpha() for ch in w) for w in s.split()) for s in WORDS)
    for ax in fig.axes:
        for lab in (ax.xaxis.label, ax.yaxis.label):
            n += sum(any(ch.isalpha() for ch in w) for w in lab.get_text().split())
    return n


C_FIRST, C_STEP, C_BAR = 3.2, 12.0, 3.4           # c: the first bar's top, from one bar's top to the next's, bar height (mm)
C_H = C_FIRST + C_STEP + C_BAR + 3.0             # c's axes, down to its values axis (mm)
H1, D_ROW = 32.0, 3.45                            # a's and b's plot height (38 until d came, 18 Nov evening); d's row pitch, mm
H = 170.0                                         # page height, mm (180 mm wide: lean.W): the journal's limit, since d came;
                                                 # before: 10 + 38 + 11.5 + 6 + C_H + 10 = 97 mm; 114 until the old c was dropped,
                                                 # 107 while c drew the old d's step curves (18 Nov 2026)


def build(out=HERE / 'fig4.png'):
    WORDS.clear()
    TEXTS.clear()
    pg = Page(H, HERE, HERE)
    xb, w = 104.0, 57.0                         # b's letter; the papers-read axis of a, b and d (one scale), mm
    top1, h1 = 10.0, H1
    panel_a(pg, 2.0, top=top1, left=13.0, right=13.0 + w, h=h1, limit=xb + 1.5)
    panel_b(pg, xb, top=top1, left=xb + 12.0, right=xb + 12.0 + w, h=h1)
    row2 = top1 + h1 + 11.5                     # the second row's title
    below = row2 + 6.0                          # the top of c's axes
    width = 92.0 if C_WHEN else 120.0           # c's values axis (mm): its words run on to the right of each bar
    bottom = panel_d(pg, 2.0, title_y=row2, top=below, left=13.0, width=width)
    row3 = bottom + 12.0                        # d's title: c's axis name ends about 7.5 mm under c's axis
    end_d = panel_rules(pg, 2.0, row3, row3 + 5.6, 76.0, 168.0, D_ROW, 96.0)
    same("d's axis and its name end above the page's foot (mm)", end_d + 8.5 <= H, True)
    edges = check_layout(pg)
    buf = io.BytesIO()
    pg.fig.savefig(buf, dpi=lean.DPI, facecolor='white', format='png')
    Image.open(buf).convert('RGB').save(out, dpi=(lean.DPI, lean.DPI))
    print('wrote', out, f'({lean.W:.0f} x {H:.0f} mm; c\'s values axis {width:.1f} mm wide; text from'
                        f' {edges[0]:.1f} to {edges[2]:.1f} mm across and {edges[1]:.1f} to {edges[3]:.1f} mm down;'
                        f' {words(pg.fig)} words)')
    plt.close(pg.fig)



def report():
    """Every drawn number, from the files, for the README (python3 -I -B build_fig4_v2.py --report)."""
    print('c: the Extended Data list, 16 of the rules and flags that acted on ten or more papers, by reach (* drawn in'
          ' c) | kind | label | found by [route] | what it does | papers (first read before the rule) | amounts by unit |'
          ' rules.csv if it differs')
    for k in sorted(LEARNED, key=lambda k: -k['papers']):
        r = RULES[k['id']]
        units = defaultdict(int)
        for c in since_rule(k['id']):
            if keep_row(k['id'], c) and c['pmid'] in REACH[k['id']]:
                units[c['unit']] += int(c['amount'])
        if k['id'] in ('TL6', 'TL10'):
            units = {'values': sum(REACH[k['id']].values())}
        orig = (int(r['papers_since_rule_other_papers']), int(r['caught_since_rule_other_papers']))
        print(f"  {'*' if k in C_ROWS else ' '} {k['id']} | {text_of(LABEL[k['id']])}"
              f" | {FINDER[k['who']][0]} [{r['first_found_route']}] | {EFFECT[k['effect']]} | {k['papers']:,}"
              f" ({len(READ_BEFORE[k['id']]):,} first read before the rule at {act_at(k['id']):,}"
              f"{'; by part' if k['id'] in ('CU5', 'PP6') else ''}) | "
              + ', '.join(f'{v:,} {u}' for u, v in sorted(units.items()))
              + ('' if (k['papers'], sum(units.values())) == orig and len(units) == 1
                 else f" | rules.csv {orig[0]:,} papers, {orig[1]:,} {r['unit']}") + (' | flag' if k['flag'] else ''))
    print('c: drawn (each finder\'s two widest rules on the list, flags left out; code checks have one there; and the'
          ' rule of b), by finder:', {FINDER[w][0]: [(k['id'], k['papers']) for k in C_ROWS if k['who'] == w]
                                      for w in C_ORDER}, '; rows as drawn:', [k['id'] for k in C_ROWS])
    print(f'c: rule-paper pairs read before the rule: the eight drawn {C_BACK[0]:,} of {C_BACK[1]:,}; the full list'
          f' {FULL_BACK[0]:,} of {FULL_BACK[1]:,}')
    for kid, why in ACT_LATER.items():
        print(f'c: {kid} read before its act ({len(READ_BEFORE[kid])} of {len(REACH[kid])}): {why}')
    for p, (v, rd, why) in TL10_LATER.items():
        print(f'c: TL10 counts {p} ({rd} values, the reader\'s), TL6 leaves it out ({v} values): {why}')
    for p, v in TL10_FINDING.items():
        print(f'c: TL6 leaves out {p} ({v} values): a finding paper of TL10 (image-only tables), not counted there')
    print(f'c: TL12 where a supplement was obtained and its values stored: {len(TL12_SUPP)} papers,'
          f' {sum(TL12_SUPP.values()):,} values (of {len(TL12_OBTAINED)} papers with a supplement obtained); not on'
          f' the full list')
    print('c: not on the list, under ten papers:',
          ', '.join(f"{k['id']} {k['papers']} ({sum(REACH[k['id']].values())} {RULES[k['id']]['unit']})"
                    for k in sorted(SMALL, key=lambda k: -k['papers'])))
    for kid, why in NOT_LISTED.items():
        r = RULES[kid]
        print(f"c: not on the list {kid} ({r['first_found_by']}; {r['papers_since_rule_other_papers']} papers,"
              f" {r['caught_since_rule_other_papers']} {r['unit']}): {why}")
    for kid, named in OUT.items():
        for p, (amount, why) in named.items():
            print(f'c: {kid} left out {p} ({amount}): {why}')
    for r in REFILED:
        print(f"b, c: PP1 counts RA4's line of {r['pmid']} ({r['amount']} value{'' if r['amount'] == '1' else 's'},"
              f" first at {int(r['papers_read_at_first']):,},"
              f" {'since' if r['since_rule'] == 'yes' else 'before'} the rule): {RA4_HEADER[r['pmid']][1]}")
    for p, (amount, why) in PP1_BEFORE_NOT_A_HEADER.items():
        print(f'b: PP1 before the rule left out {p} ({amount} values): {why}')
    print(f'b, c: PP1 values refused, not corrected: {sum(PP1_REFUSED.values())} values in {len(PP1_REFUSED)} papers',
          dict(PP1_REFUSED), '; papers only refused', PP1_ONLY_REFUSED)
    print(f'c: CU5 values with no organism, left out: {len(CU5_ORG)} papers, {sum(CU5_ORG.values()):,} values')
    print('a: rules in force at', {at: in_force(int(at)) for at in tests['rules_in_force_at_papers_read']},
          '; layers', dict(A_COUNT))
    print('a: entries by group and papers read:', sorted(Counter(ENTRY).items()))
    after_values = sum(REACH['PP1'].values())
    print(f'b: before the rule {len(BEFORE)} papers ({BEFORE_VALUES} values) in {RULE_AT:,} papers read:'
          f' {1000 * len(BEFORE) / RULE_AT:.1f} papers and {1000 * BEFORE_VALUES / RULE_AT:.0f} values per 1,000')
    print(f'b: since the rule {len(AFTER)} papers ({after_values:,} values) in {NOW - RULE_AT:,} papers read:'
          f' {1000 * len(AFTER) / (NOW - RULE_AT):.1f} papers and {1000 * after_values / (NOW - RULE_AT):.0f} values'
          f' per 1,000; last first catch at {max(AFTER.values()):,}')
    print(f'b: x60 at {RULE_AT:,} (25514023, the find); x10^6 at {X10_6:,} (12226525), papers caught by then'
          f' {sum(1 for x in AFTER.values() if x <= X10_6)}')
    print('b: before-rule papers', sorted(BEFORE.items(), key=lambda kv: kv[1]))
    for name, v in D.items():
        print(f"d: {name} ({v['kid']}): {v['before']} values refused in {v['papers_before']} papers before the change"
              f" at {v['at']:,} papers read, {v['after']} after (in {v['papers_after']}); {v['stored']} of them in the"
              f" catalogue now; found again"
              f" before the change by {FINDER[v['who']][0]} ('{D_WORDS[v['who']]}'); losses at papers read"
              f" {[(x, a) for x, a, _, _ in v['pts']]}" + ('' if name not in D_ART else
                                                          f"; drawn: peak {v['peak']}, brought back at"
                                                          f" {v['back_at']} ({sum(b for _, b, _ in v['back'])} values,"
                                                          f" {len(v['back'])} papers), still out at the end {v['end']}"))
    print(f"d (legend): the organism paper {ORG_PAPER}: add lines (papers read, kept, refused) {ORG_READS}")
    print(f"d: PP6's change also brought back {PP6_BACK['brought back (verifier_reject)']} values verifiers had refused"
          f" for the ratio alone ({sum(PP6_BACK.values())} in all)")
    for what, v in LEG.items():
        print(f'legend: {what}: {v}')
    print('legend: the one limit (audited, wrong; first round rules, papers read; last round rules, papers read; a at'
          ' the last round):', LIMIT)
    print('legend: the one limit, the last rounds (rounds in tests.json, in learning.csv; values, wrong; the same from'
          ' learning.csv; per cent; the groups most read with Opus 5 and from search papers; the last group):', LIMIT_LAST,
          '; trend p:', TREND)
    print(f'legend: a6: the list of 2 November ({LIST_ADDED[0][:7]}, {LIST_AT}) written at {A6[0]:,} papers read; its'
          f' last rule entered at {A6[2]:,}; the two found after it at {A6[3]}')
    print('legend: d4: the second reason each value still out was refused (values; by paper):',
          {k: (sum(v.values()), dict(v)) for k, v in SECOND.items()})
    print('legend: a: papers read at the rule, learning file against rules.csv:', ENTRY_VS_RULES)
    print("legend: a7: Fig. 1's four steps", dict(FIG1), '; database check', dict(DBCHECK), '; after the list',
          [(k['id'], k['rule_step']) for k in LATER])
    print('legend: b7 rates (papers, values per 1,000 before; papers, values since; papers read since):', B_RATES)
    print('legend: b2 conflicts judged from the paper among the later checks:', sorted(CONFLICT_FIXES &
                                                                                     {r['pmid'] for r in PP1_LATER_LINES}))
    print('legend: c3 limits row read before / in a censored pass:', len(READ_BEFORE['RA10']),
          len(READ_BEFORE['RA10'] & CENSORED_PASS), '; natural forms lines / papers read before:', len(IP6_LINES),
          len(READ_BEFORE['IP6']))


if __name__ == '__main__':
    if '--report' in sys.argv:
        report()
    else:
        build(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'fig4.png')
