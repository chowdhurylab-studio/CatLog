"""Extended Data figure: papers with the wrong value stored, of 32 papers that print a misleading value, found before the
test (PNG only, 16 November 2026, third pass), and two Supplementary Tables of those papers (trap_papers.tsv, one row
per paper; trap_cells.tsv, one row per key cell).

Fig. 4d of git ace3e6c (writing/figures/fig4/v2/final/build_fig4_v2.py, panel_d), moved out of Fig. 4 on 16 November:
three rows (the plain reading, CatLog before Verify and Check, CatLog after Verify and Check: Fig. 1a's step names), the
catalogue row left out because its count is partly built in; the columns grouped by kind of trap, each group named by a
head of two lines over its columns. The marks take Fig. 2a's readings (the plain reading red circles, CatLog green
diamonds, each on a grey dot where it stored the right value). The third pass (the critics' check of 16 November): the
key shows both shapes and says 'undecided' (the test's scoring cannot tell), not 'code cannot decide', which read as
CatLog's own code; a grey dot is 'right value stored', asserted cell by cell (no paper here was left with nothing
stored); each row's total of wrong values in its reading's colour, as Fig. 2a, and beside it its undecided marks, each
column headed by its key mark, both under 'of 32'; the half-filled marks are drawn as a half fill under a whole outline
(matplotlib's half-filled diamond stroked its divider with a miter spike).

One column per paper, the same paper in every row. A filled mark: that reading stored the trap's wrong value. A
half-filled mark: it stored no trap cell, but at least one cell of the paper's key is undecided (the scoring cannot tell
under which label or variant the value was stored). A small grey dot: the right value stored in every key cell.

Run from anywhere (seconds; writes known_traps.png, trap_papers.tsv and trap_cells.tsv beside this script):
    python3 -I -B writing/figures/extended_data/known_traps/build.py
    python3 -I -B writing/figures/extended_data/known_traps/build.py --report      (every drawn number, for the README)

Numbers come from writing/figures/fig4/v2/evidence/traps/: traps.csv (rows `named_by_catlog = no` with a frozen
reading, as panel d took them), cells.csv (each key cell's verdict per reading) and totals.json (set "no instruction or
code names (32)", its kinds and its tests). The tables also read, as the trap evidence did, each paper's key in
paper/evidence/hard_cases_20261102/keys/ or expand/keys/ (what the trap is, how CatLog's records documented it, and per
cell where it is printed, the printed cell, the right value and the trap's), each cell matched to cells.csv by its
metric, variant and substrate (asserted); the paper table writes PP1's kind in the words of the README's family table
(KIND_WORDS). Note 5's 16 papers left out (their plain reading refused by Opus 5.5's safety filter, read by Sonnet 5.5)
are counted from paper/evidence/hard_cases_20261102/summary.json. The build stops when a drawn number is not the number
of its file (lean.same), and when two texts overlap or a text leaves the page (check_layout); nothing is typed by hand
except the expected counts it asserts. Shared drawing code: ../../lean.py (imported, not edited); `rich`, `label` and
`dot` are copies of Fig. 4's.
"""
import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

sys.dont_write_bytecode = True               # lean.py lives outside this folder: leave no __pycache__ beside it
HERE = Path(__file__).resolve().parent        # writing/figures/extended_data/known_traps
FIGS = HERE.parents[1]                        # writing/figures
ROOT = HERE.parents[3]                        # the CatLog folder
EV = FIGS / 'fig4' / 'v2' / 'evidence' / 'traps'
KEYS = ROOT / 'paper' / 'evidence' / 'hard_cases_20261102'
sys.path.insert(0, str(FIGS))
import lean  # noqa: E402
from lean import Page, same, INK  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from PIL import Image  # noqa: E402

OFF = '#C4C4C4'                               # the right value stored (Fig. 2a's grey dots)
KEY = '#666666'                               # the key's marks: a neutral grey (no reading)


def table(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


# ================================================================================================= data
TRAPS = table(EV / 'traps.csv')
CELLS = table(EV / 'cells.csv')
TOTALS = json.load(open(EV / 'totals.json', encoding='utf-8'))
SET = TOTALS['sets']['no instruction or code names (32)']
BY_KIND = TOTALS['by_kind']['no instruction or code names (32)']
TESTS = TOTALS['tests']
PAPERS = [t for t in TRAPS if t['named_by_catlog'] == 'no' and t['frozen_reader_alone_fell_in'] in ('yes', 'no')]
BY_PMID = {t['pmid']: t for t in PAPERS}
same('papers', len(PAPERS), SET['papers'])
same('papers', len(PAPERS), 32)
same('papers no CatLog instruction or code names, all with a frozen reading or not',
     sum(t['named_by_catlog'] == 'no' for t in TRAPS), 42)
same('papers with a misleading value on record, all', len(TRAPS), 53)
# the selection (legend note 5), counted here: the set's two parts, where the trap shows, the papers CatLog names, and
# why ten of the unnamed papers have no frozen reading
same('note 5: the 53 by part (first pick, fixed draw); the 32 by part; the 32 by where the trap shows; papers named',
     (dict(Counter(t['set'] for t in TRAPS)), dict(Counter(t['set'] for t in PAPERS)),
      dict(Counter(t['trap_seen_in'] for t in PAPERS)), sum(t['named_by_catlog'] != 'no' for t in TRAPS)),
     ({'first': 16, 'drawn': 37}, {'drawn': 27, 'first': 5}, {'the paper': 29, 'another publication': 3}, 11))
same('note 5: why the other 10 unnamed papers have no frozen reading',
     dict(Counter(t['frozen_left_out'] for t in TRAPS if t['named_by_catlog'] == 'no' and t not in PAPERS)),
     {'refused (catlog)': 7, 'broke a rule': 3})
# note 5: the papers left out of the set before it was scored. The hard cases' summary has one plain reading per paper:
# Opus 5.5 read the set's 53; its safety filter refused the plain reading of 16 more, which Sonnet 5.5 (CatLog's own
# retry) read, and those are outside the set (paper/evidence/hard_cases_20261102/README.md)
SUMMARY = json.load(open(KEYS / 'summary.json', encoding='utf-8'))
LEFT_OUT = [d['pmid'] for d in SUMMARY if d['model'] == 'Sonnet 5.5']
same("note 5: plain readings by model (summary.json); Opus 5.5's are the set's 53; the papers left out (read by Sonnet "
     "5.5) and how many of them are in the set",
     (dict(Counter(d['model'] for d in SUMMARY)),
      sorted(d['pmid'] for d in SUMMARY if d['model'] == 'Opus 5.5') == sorted(t['pmid'] for t in TRAPS),
      len(LEFT_OUT), len(set(LEFT_OUT) & {t['pmid'] for t in TRAPS})),
     ({'Opus 5.5': 53, 'Sonnet 5.5': 16}, True, 16, 0))

# the rows: (field, row label, mark: Fig. 2a's, the plain reading a red circle and CatLog a green diamond). Before Verify
# and Check is the reader's rows as CatLog's code converts them (Read and Convert); after is the rows kept after the
# verifier and code checks (Read, Convert, Verify and Check: Fig. 1a's four steps, nothing after reading)
READINGS = [('plain_reading', 'Plain reading', lean.PLAIN),
            ('frozen_reader_alone', 'CatLog before Verify and Check', lean.CATLOG),
            ('frozen_with_verifier_and_code', 'CatLog after Verify and Check', lean.CATLOG)]
same("the rows' colours are Fig. 2a's (the plain reading red, CatLog green)", [st['color'] for _, _, st in READINGS],
     [lean.RED, lean.GREEN, lean.GREEN])
NOT_DRAWN = 'catalogue_now'                  # CatLog's catalogue: in the README, not on the art


def fell(t, key):
    return t[key + '_fell_in'] == 'yes'


for key, _, _ in READINGS:
    same(f'{key}: every paper scored', {t[key + '_fell_in'] for t in PAPERS}, {'yes', 'no'})
FELL = {key: [sum(fell(t, key) for t in PAPERS), sum(t[key + '_fell_in'] in ('yes', 'no') for t in PAPERS)]
        for key, _, _ in READINGS + [(NOT_DRAWN, '', None)]}
for key in FELL:
    same(f'{key}: fell in, of papers', FELL[key], SET[key])
same('rows drawn, and the catalogue (not drawn)', [FELL[k] for k, _, _ in READINGS] + [FELL[NOT_DRAWN]],
     [[16, 32], [15, 32], [10, 32], [4, 31]])
same('the paper CatLog had not read when the set was scored', [t['pmid'] for t in PAPERS
                                                               if t[NOT_DRAWN + '_fell_in'] == ''], ['9692923'])

# --- six families of trap, in column order; each named by a head of two short lines (kcat and Km are symbols) -----
K, M = [('k', 'i'), ('cat', 'sub')], [('K', 'i'), ('m', 'sub')]      # kcat and Km: italic, roman subscript
FAMILIES = [   # (id, head: two lines, each as runs for `rich`, the kinds of traps.csv it holds); no colour of its own:
    # the heads name the families, and the marks carry the reading's colour (Fig. 2a)
    ('constant', [[('Another constant', '')], [('as ', '')] + K + [(' or ', '')] + M], ('RA1',)),
    ('earlier', [[('Value from an', '')], [('earlier paper', '')]], ('PP2',)),
    ('digits', [[('Misprinted', '')], [('digits', '')]], ('PP4',)),
    ('label', [[('Value under the', '')], [('wrong label', '')]], ('PP3', 'IP11')),
    ('unit', [[('Wrong unit', '')], [('or multiplier', '')]], ('PP1', 'RA4')),
    ('text', [[('Garbled', '')], [('PDF text', '')]], ('TL1', 'TL2', 'TL4')),
]


def head_text(head):
    """A family's head as one line of words (kcat and Km spelled as their letters)."""
    return ' '.join(''.join(t for t, _ in line) for line in head)


FAMILY_OF = {kind: fam for fam, _, kinds in FAMILIES for kind in kinds}
HEAD_OF = {fam: head_text(head) for fam, head, _ in FAMILIES}
same('every paper in one family', sorted(Counter(t['kind'] for t in PAPERS)), sorted(FAMILY_OF))
same('papers per kind', dict(Counter(t['kind'] for t in PAPERS)),
     {k: v['papers'] for k, v in BY_KIND.items() if k != 'all'})
same("totals.json's 'all' line of the kinds", [BY_KIND['all']['papers']] + [BY_KIND['all'][k] for k in FELL],
     [32] + [FELL[k] for k in FELL])
same('papers per kind, as expected', dict(Counter(t['kind'] for t in PAPERS)),
     {'RA1': 7, 'PP2': 3, 'PP4': 3, 'PP3': 4, 'IP11': 2, 'PP1': 3, 'RA4': 3, 'TL1': 2, 'TL2': 3, 'TL4': 2})
same('heads of two lines, each of at most three words (kcat and Km set as symbols, not counted)',
     ({len(head) for _, head, _ in FAMILIES},
      max(sum(any(c.isalpha() for c in w) for w in ''.join(t for t, k in line if k == '').split())
          for _, head, _ in FAMILIES for line in head)), ({2}, 3))
same('the heads, in words (the plain clause of each family)', [head_text(h) for _, h, _ in FAMILIES],
     ['Another constant as kcat or Km', 'Value from an earlier paper', 'Misprinted digits',
      'Value under the wrong label', 'Wrong unit or multiplier', 'Garbled PDF text'])

BY_FAMILY = {fam: [t for t in PAPERS if FAMILY_OF[t['kind']] == fam] for fam, *_ in FAMILIES}
COUNTS = {fam: [sum(fell(t, k) for t in BY_FAMILY[fam]) for k, _, _ in READINGS + [(NOT_DRAWN, '', None)]]
          for fam, *_ in FAMILIES}
for fam, _, kinds in FAMILIES:               # each family's count is the sum of its kinds' counts in totals.json
    for i, (key, _, _) in enumerate(READINGS + [(NOT_DRAWN, '', None)]):
        same(f'{fam}: {key}', COUNTS[fam][i], sum(BY_KIND[k][key][0] for k in kinds))
same('papers per family', {f: len(p) for f, p in BY_FAMILY.items()},
     {'constant': 7, 'earlier': 3, 'digits': 3, 'label': 6, 'unit': 6, 'text': 7})
same('fell in per family: plain, before Verify and Check, after, catalogue (not drawn)', COUNTS,
     {'constant': [6, 3, 2, 1], 'earlier': [3, 3, 3, 0], 'digits': [3, 3, 3, 3], 'label': [3, 3, 1, 0],
      'unit': [1, 3, 1, 0], 'text': [0, 0, 0, 0]})
# column order: families by the plain reading's count, then the after count, then size (the README says so)
same('families in order of the plain reading, then after Verify and Check, then size',
     [f for f, *_ in FAMILIES],
     [f for f, *_ in sorted(FAMILIES, key=lambda F: (-COUNTS[F[0]][0], -COUNTS[F[0]][2], -len(BY_FAMILY[F[0]])))])

# --- undecided cells (`*_review_cells`: the scoring cannot tell under which label or variant the value was stored):
# a half-filled mark where the reading stored no trap cell; counted as not stored, as in totals.json's basis ---------
REVIEW = {key: [t['pmid'] for t in PAPERS if int(t[key + '_review_cells'] or 0)] for key, _, _ in READINGS}
OPEN = {key: [p for p in REVIEW[key] if not fell(BY_PMID[p], key)] for key, _, _ in READINGS}
same('papers with an undecided cell, per row', {k: len(v) for k, v in REVIEW.items()},
     {'plain_reading': 4, 'frozen_reader_alone': 4, 'frozen_with_verifier_and_code': 6})
same('half-filled marks per row', {k: sorted(v) for k, v in OPEN.items()},
     {'plain_reading': sorted(['16584181', '10387055', '22855027', '34681120']),
      'frozen_reader_alone': sorted(['16584181', '10387055', '22855027']),
      'frozen_with_verifier_and_code': sorted(['11733990', '16584181', '30253338', '10387055', '22855027'])})
OPEN_ALL = sorted({p for v in OPEN.values() for p in v})
same('half-filled marks, and the papers they are on', (sum(len(v) for v in OPEN.values()), len(OPEN_ALL)), (12, 6))
for key, _, _ in READINGS:
    same(f'{key}: filled and half-filled marks together (counted as stored)', FELL[key][0] + len(OPEN[key]),
         SET['review_counted_as_fell_in'][key][0])
same('counted as stored, per row', [FELL[k][0] + len(OPEN[k]) for k, _, _ in READINGS], [20, 18, 15])
same('the measured variant: every cell one the scoring cannot decide',
     {t['pmid']: (t['cells'], t['plain_reading_review_cells']) for t in PAPERS if t['kind'] == 'IP11'},
     {'10387055': ('10', '10'), '22855027': ('3', '3')})

# --- the grey dots: the right value stored. cells.csv gives each key cell's verdict per reading (trap, right, review,
# missing); a paper with no filled or half-filled mark stored the right value in every cell of its key, in every row
# (asserted), so no reading stays clear of a trap by storing nothing --------------------------------------------------
CELLS_OF = defaultdict(list)
for c in CELLS:
    if c['pmid'] in BY_PMID:
        CELLS_OF[c['pmid']].append(c)
same('key cells of the 32 papers (cells.csv), and per paper as traps.csv counts them',
     (sum(len(v) for v in CELLS_OF.values()), all(len(CELLS_OF[p]) == int(BY_PMID[p]['cells']) for p in BY_PMID)),
     (180, True))
for key, _, _ in READINGS:
    same(f"{key}: a paper fell in exactly when one of its cells is the trap's", sorted(p for p in BY_PMID if fell(BY_PMID[p], key)),
         sorted(p for p in BY_PMID if any(c[key] == 'trap' for c in CELLS_OF[p])))
RIGHT = {key: [p for p in BY_PMID if not fell(BY_PMID[p], key) and p not in OPEN[key]] for key, _, _ in READINGS}
same('grey dots: the right value stored in every key cell, per row (and the papers that number)',
     {k: (len(v), all(c[k] == 'right' for p in v for c in CELLS_OF[p])) for k, v in RIGHT.items()},
     {'plain_reading': (12, True), 'frozen_reader_alone': (14, True), 'frozen_with_verifier_and_code': (17, True)})
same('no reading of the 32 left a key cell with nothing stored (missing)',
     sum(c[k] == 'missing' for p in BY_PMID for c in CELLS_OF[p] for k, _, _ in READINGS), 0)
# the blind re-score (another basis, in the legend only): the plain reading's alone; the frozen readings have none
BLIND = {t['pmid'] for t in PAPERS if t['plain_reading_fell_in_blind_rescore'] == 'yes'}
same('the plain reading, blind re-score: papers, and its one difference from code',
     (len(BLIND), sorted(BLIND ^ {t['pmid'] for t in PAPERS if fell(t, 'plain_reading')})), (17, ['16584181']))
same("the plain reading's half-filled marks as the blind re-score judged them",
     {p: BY_PMID[p]['plain_reading_fell_in_blind_rescore'] for p in OPEN['plain_reading']},
     {'16584181': 'yes', '10387055': 'no', '22855027': 'no', '34681120': 'no'})
same('no blind re-score of the frozen readings in traps.csv', [c for c in TRAPS[0] if 'frozen' in c and 'blind' in c],
     [])


def order(fam, kinds):
    """Within a family: papers after Verify and Check holds first, then before, then the plain reading's; then papers
    with a half-filled mark, rows in the same order; then by kind in the family's order and by row of traps.csv."""
    rows_ = ('frozen_with_verifier_and_code', 'frozen_reader_alone', 'plain_reading')
    return sorted(BY_FAMILY[fam], key=lambda t: tuple(-fell(t, k) for k in rows_) +
                  tuple(-(t['pmid'] in OPEN[k]) for k in rows_) + (kinds.index(t['kind']), PAPERS.index(t)))


COLUMNS = [(fam, t) for fam, _, kinds in FAMILIES for t in order(fam, kinds)]
same('columns, left to right', [t['pmid'] for _, t in COLUMNS],
     ['25225291', '41552538', '314446', '25658941', '26142822', '14990577', '15799715',
      '14622249', '17521737', '24463048',
      '17567047', '23148601', '26412334',
      '12604226', '11733990', '30253338', '16584181', '10387055', '22855027',
      '18700786', '21454538', '16431280', '34681120', 'NPD832847D', '22112405',
      '1702991', '9415401', '16554717', '9616041', '9692923', '20632378', '25320211'])


# --- paired tests (exact McNemar, two-sided), recomputed from the drawn marks and checked against totals.json ------
def mcnemar(better, worse):
    n, k = better + worse, min(better, worse)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0


def pair(a, b):
    """Papers that fell in on a and not on b, and the other way."""
    return ([t['pmid'] for t in PAPERS if fell(t, a) and not fell(t, b)],
            [t['pmid'] for t in PAPERS if fell(t, b) and not fell(t, a)])


PAIRS = {   # (left, right): the test's name in totals.json
    ('plain_reading', 'frozen_with_verifier_and_code'): 'plain reading vs frozen reader with verifier and code, unnamed',
    ('plain_reading', 'frozen_reader_alone'): 'plain reading vs frozen reader alone, unnamed',
    ('frozen_reader_alone', 'frozen_with_verifier_and_code'):
        'frozen reader alone vs frozen reader with verifier and code, unnamed',
}
TEST = {}
for (a, b), name in PAIRS.items():
    better, worse = pair(a, b)
    rec = TESTS[name]
    same(f'{name}: better', sorted(better), sorted(rec[f'{a} fell in, {b} not']))
    same(f'{name}: worse', sorted(worse), sorted(rec[f'{b} fell in, {a} not']))
    p = mcnemar(len(better), len(worse))
    same(f'{name}: p', round(p, 4), round(rec['exact_mcnemar_two_sided_p'], 4))
    TEST[(a, b)] = (better, worse, p)
same('tests: better, worse', {k: (len(v[0]), len(v[1])) for k, v in TEST.items()},
     {('plain_reading', 'frozen_with_verifier_and_code'): (6, 0), ('plain_reading', 'frozen_reader_alone'): (3, 2),
      ('frozen_reader_alone', 'frozen_with_verifier_and_code'): (5, 0)})
same('before Verify and Check, worse than the plain reading: both in the wrong-unit family',
     sorted(FAMILY_OF[BY_PMID[p]['kind']] + ' ' + p for p in TEST[('plain_reading', 'frozen_reader_alone')][1]),
     ['unit 16431280', 'unit 21454538'])
DROP = TEST[('plain_reading', 'frozen_with_verifier_and_code')][0]
KIND_OF = {t['pmid']: t['kind'] for t in PAPERS}
same('the drop from the plain reading to after Verify and Check, by kind', sorted(Counter(KIND_OF[p] for p in DROP).items()),
     [('PP3', 2), ('RA1', 4)])
same('the two rows printed under another label: after Verify and Check stored the number under another label '
     '(half-filled marks)',
     {p: BY_PMID[p]['frozen_with_verifier_and_code_review_cells'] for p in DROP if KIND_OF[p] == 'PP3'},
     {'11733990': '1', '30253338': '3'})
same('... and every key cell of those two is undecided', {p: BY_PMID[p]['cells'] for p in DROP if KIND_OF[p] == 'PP3'},
     {'11733990': '1', '30253338': '3'})
REVIEW_TEST = TESTS['plain reading vs frozen reader with verifier and code, unnamed, a review cell counted as fallen in']
MAIN = TESTS['MAIN: first reading vs frozen reader alone, the 32 papers no instruction or code names']
same('the reader alone, first reading against reading again: pairs, better, worse, p',
     (MAIN['pairs'], len(MAIN['first_reading fell in, frozen_reader_alone not']),
      len(MAIN['frozen_reader_alone fell in, first_reading not']), MAIN['exact_mcnemar_two_sided_p']), (30, 4, 2, 0.688))
same('plain against after Verify and Check with undecided cells counted as stored: better, worse, p',
     (len(REVIEW_TEST['plain_reading fell in, frozen_with_verifier_and_code not']),
      len(REVIEW_TEST['frozen_with_verifier_and_code fell in, plain_reading not']),
      REVIEW_TEST['exact_mcnemar_two_sided_p']), (5, 0, 0.0625))

# ================================================================================================= the tables
# Supplementary Tables of the 32 papers: what the trap is and how CatLog's records documented it before the test (the
# key's own words), and per key cell where it is printed, the printed cell, the right value and the trap's, with each
# reading's verdict. From each paper's key, read as the trap evidence read it (keys/ for the first pick, expand/keys/
# for the draw); each key cell matched to its cells.csv row by metric, variant and substrate (asserted, in order).
HELD_OUT = {ln.strip() for ln in open(ROOT / 'sources/holdout_locked.txt', encoding='utf-8') if ln.strip()}
same('none of the 32 is a held-out paper', sorted(p for p in BY_PMID if p in HELD_OUT), [])
KEY_FILES = {p: [f for f in (KEYS / 'keys' / f'{p}.json', KEYS / 'expand' / 'keys' / f'{p}.json') if f.exists()]
             for p in BY_PMID}
same('each paper has one key file', {p: len(f) for p, f in KEY_FILES.items() if len(f) != 1}, {})
KEY_OF = {p: json.load(open(f[0], encoding='utf-8')) for p, f in KEY_FILES.items()}
same("each key is the paper's, its kind traps.csv's", [p for p, k in KEY_OF.items()
                                                       if k['pmid'] != p or k['class_id'] != BY_PMID[p]['kind']], [])
SUBSTRATE = max(len(c['substrate']) for c in CELLS)          # cells.csv keeps a substrate's first 60 characters
same("cells.csv's substrates, cut at", SUBSTRATE, 60)
same("each key's cells are cells.csv's, in order (metric, variant, substrate as cells.csv cuts it)",
     [p for p, k in KEY_OF.items() if [(c['metric'], c['variant'], c['substrate'][:SUBSTRATE]) for c in k['cells']] !=
      [(c['metric'], c['variant'], c['substrate']) for c in sorted(CELLS_OF[p], key=lambda c: int(c['cell']))]], [])
same('kinds of right answer and trap in the keys (a value; store nothing; store this value under that label)',
     sorted(Counter((c['right']['kind'], c['trap']['kind']) for k in KEY_OF.values() for c in k['cells']).items()),
     [(('not_stored', 'stored'), 70), (('value', 'stored'), 23), (('value', 'value'), 87)])
VERDICT = {'trap': 'wrong value stored', 'review': 'undecided', 'right': 'right value stored', 'missing': 'nothing stored'}


def answer(cell, which):
    """A key cell's right answer or trap in words: a value and its unit; for the right answer 'none' where the cell must
    not be stored as this metric (the next column says why); for a trap that is the value itself, where it would be
    stored (under another variant, or as this metric)."""
    d = cell[which]
    if d['kind'] == 'value':
        return f"{d['value']:g} {d['unit']}"
    if d['kind'] == 'not_stored':
        return 'none: not to be stored (why: next column)'   # not this constant, an earlier paper's value or another row's
    same(f"a key's {which} kind", (which, d['kind']), ('trap', 'stored'))
    where = f"under {cell['trap_variant']}" if cell.get('trap_variant') else f"as {cell['metric']}"
    return f"{d['value']:g} {d['unit']} stored {where}" if 'value' in d else f'stored {where}'


def outcome(t, key):
    return ('wrong value stored' if fell(t, key) else 'undecided' if t['pmid'] in OPEN[key] else 'right value stored')


# 'kind of trap': traps.csv's words, except PP1's. 'misprinted unit or exponent in a header' fits one of its three papers
# (NPD832847D's Table V header); 18700786 prints two kcat/Km cells 100-fold low under a header that is right for the
# row's other cells, and 21454538 a unit misprinted in its Results and its Fig. 3B axis (their keys' own words). So PP1
# is written as the README's family table words it, which fits all three
KIND_WORDS = {'PP1': 'a misprinted unit or exponent'}
same("PP1: its papers, and traps.csv's words for the kind",
     (sorted(t['pmid'] for t in PAPERS if t['kind'] == 'PP1'), {t['kind_in_words'] for t in PAPERS if t['kind'] == 'PP1'}),
     (['18700786', '21454538', 'NPD832847D'], {'misprinted unit or exponent in a header'}))
PAPER_COLUMNS = ['pmid', 'family (Extended Data head)', 'kind of trap', 'the trap (key)',
                 "how CatLog's records documented it before the test", 'set', 'trap seen in', 'key cells'] + \
                [f'{name}: outcome' for _, name, _ in READINGS] + [f'{name}: trap cells' for _, name, _ in READINGS]
CELL_COLUMNS = ['pmid', 'family (Extended Data head)', 'cell', 'where it is printed', 'metric', 'enzyme', 'variant',
                'substrate', 'printed', 'right value (catalogue units)', 'how the right value is known', 'the trap'] + \
               [name for _, name, _ in READINGS]


def tables():
    papers, cells = [], []
    for fam, t in COLUMNS:
        p, k = t['pmid'], KEY_OF[t['pmid']]
        papers.append(dict(zip(PAPER_COLUMNS, [p, HEAD_OF[fam], KIND_WORDS.get(t['kind'], t['kind_in_words']),
                                               k['trap'], k.get('caught_by', ''), t['set'], t['trap_seen_in'],
                                               t['cells']] +
                               [outcome(t, key) for key, _, _ in READINGS] +
                               [t[key + '_trap_cells'] for key, _, _ in READINGS])))
        for c, row in zip(k['cells'], sorted(CELLS_OF[p], key=lambda c: int(c['cell']))):
            cells.append(dict(zip(CELL_COLUMNS, [p, HEAD_OF[fam], int(row['cell']) + 1, c.get('where', ''),
                                                 c['metric'], c.get('enzyme', ''), c['variant'], c['substrate'],
                                                 c.get('printed', ''), answer(c, 'right'), c['right'].get('why', ''),
                                                 answer(c, 'trap')] +
                                  [VERDICT[row[key]] for key, _, _ in READINGS])))
    return papers, cells


PAPER_ROWS, CELL_ROWS = tables()
same('tables: papers, cells', (len(PAPER_ROWS), len(CELL_ROWS)), (32, 180))
same('tables: outcomes per row are the marks drawn',
     {name: dict(Counter(r[f'{name}: outcome'] for r in PAPER_ROWS)) for _, name, _ in READINGS},
     {name: {'wrong value stored': FELL[k][0], 'undecided': len(OPEN[k]), 'right value stored': len(RIGHT[k])}
      for k, name, _ in READINGS})
NUMBERS = re.compile(r'(?<![\d.])\d{6,8}(?![\d.])')
same('tables: no held-out paper is named anywhere in them',
     sorted({n for r in PAPER_ROWS + CELL_ROWS for v in r.values() for n in NUMBERS.findall(str(v)) if n in HELD_OUT}), [])


# No reviewer is named in anything written under writing/ (the owner's rule): three keys say a record "waits in
# reviewer <name>'s human review pack", which the tables write as "a reviewer's". The pattern names nobody.
NAMED_REVIEWER = re.compile(r"\b(?:in )?reviewer [A-Z][A-Za-z]{0,20}'s\b")


def no_names(v):
    return NAMED_REVIEWER.sub(lambda m: ('in ' if m.group(0).startswith('in ') else '') + "a reviewer's", v) \
        if isinstance(v, str) else v


same('tables: reviewers named in the keys, written as "a reviewer"',
     sum(len(NAMED_REVIEWER.findall(str(v))) for r in PAPER_ROWS + CELL_ROWS for v in r.values()), 3)


def write_tables():
    for name, cols, rows in (('trap_papers.tsv', PAPER_COLUMNS, PAPER_ROWS), ('trap_cells.tsv', CELL_COLUMNS, CELL_ROWS)):
        rows = [{k: no_names(v) for k, v in r.items()} for r in rows]
        same(f'{name}: no reviewer named', sum(1 for r in rows for v in r.values()
                                               if re.search(r'\breviewer [A-Z][A-Za-z]', str(v))), 0)
        with open(HERE / name, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols, delimiter='\t', lineterminator='\n')
            w.writeheader()
            w.writerows(rows)
        print('wrote', HERE / name, f'({len(rows)} rows)')


# ================================================================================================= drawing
H = 34.0                                       # page height, mm (180 mm wide: lean.W)
SIZE = 6.5                                     # row labels, heads (pt)
TOTAL = 7.0                                    # row totals, bold
TITLE = 6.8                                    # the title, as lean.title sets panel titles
SCRIPT = {'sup': 0.42, 'sub': -0.22}           # rise of a script, in ems of its line (as lean.rich)
X0 = 2.0                                       # the left edge of the title and of the longest row label
TITLE_Y = 4.0                                  # the title's capitals are centred here (mm from the top)
HEAD_Y = (8.6, 11.2)                           # the heads' two lines
ROWS_Y = (16.6, 21.0, 25.4)                    # the three rows
KEY_Y = 30.9                                   # the key line under the rows
GRID_R = 163.0                                 # the last column's right edge
TOT_X = (169.6, 176.0)                         # the totals' centres: wrong values (bold), undecided marks
GAP = 1.5                                      # empty columns between families
MARK = {'o': 5.0, 'D': 4.6}                    # circle and diamond sizes (pt)
MEW = 0.85                                     # mark edges (pt)
WORDS = []                                     # every line of words drawn, for the README's count
BOXES = []                                     # every line's drawn texts, for the overlap check


def rich(pg, x, y, parts, size=SIZE, ha='left', weight='normal', color=INK):
    """One line set from runs (text, kind), its baseline at y mm: kind '' plain, 'i' italic, 'sup' raised, 'sub'
    lowered (Fig. 4's copy of lean.rich: a script never under 5 pt, the bold weight measured). Returns the right end."""
    renderer = pg.fig.canvas.get_renderer()
    runs = []
    for text, kind in parts:
        fs = max(5.0, 0.72 * size) if kind in SCRIPT else size
        style = 'italic' if kind == 'i' else 'normal'
        prop = FontProperties(family='Arial', style=style, weight=weight, size=fs)
        width = renderer.get_text_width_height_descent(text, prop, ismath=False)[0] / pg.fig.dpi * 25.4
        runs.append((text, style, fs, SCRIPT.get(kind, 0.0) * size * 25.4 / 72, width))
    at = x - sum(r[-1] for r in runs) * {'left': 0.0, 'center': 0.5, 'right': 1.0}[ha]
    drawn = []
    for text, style, fs, lift, width in runs:
        drawn.append(pg.fig.text(at / lean.W, 1 - (y - lift) / pg.h, text, fontsize=fs, fontstyle=style,
                                 fontweight=weight, color=color, va='baseline', ha='left'))
        at += width
    WORDS.append(''.join(t for t, _ in parts))
    BOXES.append((''.join(t for t, _ in parts), drawn))
    return at


def label(pg, x, y, parts, size=SIZE, **kw):
    """A line of text whose capitals are centred on y mm (a row's marks), set by `rich`."""
    if isinstance(parts, str):
        parts = [(parts, '')]
    return rich(pg, x, lean.baseline(y, size), parts, size=size, **kw)


def dot(ax, x, y, colour, size, marker='o', mew=MEW, z=3):
    """A filled mark: fill at alpha 0.6 over a white disc (nothing shows through), edge opaque in the same colour."""
    ax.plot([x], [y], marker=marker, markersize=size, markerfacecolor='white', markeredgecolor='none',
            linestyle='none', zorder=z, clip_on=False)
    ax.plot([x], [y], marker=marker, markersize=size, markerfacecolor=colour + '99', markeredgecolor=colour,
            markeredgewidth=mew, linestyle='none', zorder=z + 0.1, clip_on=False)


def half(ax, x, y, colour, size, marker='o', mew=MEW, z=3):
    """A half-filled mark, the size of a filled one: its left half filled (alpha 0.6 over white), its right half white,
    its whole outline opaque in the reading's colour. Drawn as a half fill with no edge under a whole outline with no
    fill, so no edge is stroked along the divider (matplotlib's half-filled diamond did, with a miter spike)."""
    ax.plot([x], [y], marker=marker, markersize=size, markerfacecolor='white', markeredgecolor='none',
            linestyle='none', zorder=z, clip_on=False)
    ax.plot([x], [y], marker=marker, markersize=size, fillstyle='left', markerfacecolor=colour + '99',
            markerfacecoloralt='white', markeredgecolor='none', linestyle='none', zorder=z + 0.05, clip_on=False)
    ax.plot([x], [y], marker=marker, markersize=size, markerfacecolor='none', markeredgecolor=colour,
            markeredgewidth=mew, linestyle='none', zorder=z + 0.1, clip_on=False)


def grey(ax, x, y):
    """A small grey dot: the reading stored the right value in every key cell (Fig. 2a's grey dots)."""
    ax.plot([x], [y], marker='o', markersize=1.6, markerfacecolor=OFF, markeredgecolor='none', linestyle='none',
            clip_on=False)


def build(out=HERE / 'known_traps.png'):
    WORDS.clear()
    BOXES.clear()
    pg = Page(H, HERE, HERE)
    # title: what the marks count in bold, then which papers in plain weight (Fig. 2a's pattern, no comma)
    rich(pg, X0, lean.baseline(TITLE_Y, TITLE), [('Papers with the wrong value stored', '')], size=TITLE, weight='bold')
    rich(pg, pg_right(pg) + 0.9, lean.baseline(TITLE_Y, TITLE),
         [(f'({len(PAPERS)} papers that print a misleading value, found before the test)', '')], size=TITLE)

    # the columns: one per paper, families set apart by an empty column and a half; the row labels right-aligned so
    # the longest starts at the title's left edge
    lab_r = X0 + max(text_width(pg, name) for _, name, _ in READINGS)
    grid_l = lab_r + 2.6
    units = len(COLUMNS) + GAP * (len(FAMILIES) - 1)
    pitch = (GRID_R - grid_l) / units
    xs, at, last = [], 0.0, None
    for fam, _ in COLUMNS:
        if last is not None and fam != last:
            at += GAP
        xs.append(grid_l + pitch * (at + 0.5))
        at += 1
        last = fam

    # the heads: each family named in two lines, centred over its own columns; over the totals 'of 32', then each
    # total column's key mark (filled: wrong values; half-filled: undecided)
    spans = {}
    for fam, head, _ in FAMILIES:
        mine = [x for x, (f, _) in zip(xs, COLUMNS) if f == fam]
        spans[fam] = (mine[0], mine[-1])
        for line, y in zip(head, HEAD_Y):
            label(pg, (mine[0] + mine[-1]) / 2, y, line, ha='center')
    label(pg, sum(TOT_X) / 2, HEAD_Y[0], f'of {len(PAPERS)}', ha='center')
    for x, mark in zip(TOT_X, (dot, half)):
        mark(pg.canvas(x - 1.5, HEAD_Y[1] - 1.5, 3, 3), 1.5, 1.5, KEY, MARK['o'])

    # the rows
    top = ROWS_Y[0] - 3.0
    ax = pg.canvas(grid_l, top, GRID_R - grid_l, ROWS_Y[-1] - ROWS_Y[0] + 6.0)
    drawn = {key: Counter() for key, _, _ in READINGS}
    for (key, name, st), y in zip(READINGS, ROWS_Y):
        label(pg, lab_r, y, name, ha='right')
        for xm, (fam, t) in zip(xs, COLUMNS):
            if fell(t, key):
                dot(ax, xm - grid_l, y - top, st['color'], MARK[st['marker']], marker=st['marker'])
                drawn[key]['filled'] += 1
            elif t['pmid'] in OPEN[key]:
                half(ax, xm - grid_l, y - top, st['color'], MARK[st['marker']], marker=st['marker'])
                drawn[key]['half'] += 1
            else:
                grey(ax, xm - grid_l, y - top)
                drawn[key]['grey'] += 1
        # the totals in the reading's colour (Fig. 2a): wrong values bold, undecided marks plain
        label(pg, TOT_X[0], y, str(FELL[key][0]), size=TOTAL, ha='center', weight='bold', color=st['color'])
        label(pg, TOT_X[1], y, str(len(OPEN[key])), size=TOTAL, ha='center', color=st['color'])
    same('marks drawn per row: filled (the total), half-filled (the second total), grey (right value stored)',
         {k: (c['filled'], c['half'], c['grey']) for k, c in drawn.items()},
         {k: (FELL[k][0], len(OPEN[k]), len(RIGHT[k])) for k, _, _ in READINGS})
    # the key line under the rows, from the grid's left edge: each state as a grey circle and a grey diamond (both
    # readings' shapes), then the grey dot
    kx = grid_l + pitch / 2
    for what, mark in (('wrong value stored', dot), ('undecided', half), ('right value stored', None)):
        if mark:
            for i, marker in enumerate(('o', 'D')):
                mark(pg.canvas(kx - 1.5 + 2.7 * i, KEY_Y - 1.5, 3, 3), 1.5, 1.5, KEY, MARK[marker], marker=marker)
            kx += 2.7
        else:
            grey(pg.canvas(kx - 1.5, KEY_Y - 1.5, 3, 3), 1.5, 1.5)
        kx = label(pg, kx + 1.9, KEY_Y, what) + 4.0
    check_layout(pg, spans)
    buf = io.BytesIO()
    pg.fig.savefig(buf, dpi=lean.DPI, facecolor='white', format='png')
    Image.open(buf).convert('RGB').save(out, dpi=(lean.DPI, lean.DPI))
    print('wrote', out, f'({lean.W:.0f} x {H:.1f} mm; {words()} words; column pitch {pitch:.2f} mm; row labels end at'
                        f' {lab_r:.1f} mm, columns {grid_l + pitch / 2:.1f} to {GRID_R - pitch / 2:.1f} mm)')
    plt.close(pg.fig)
    write_tables()


def text_width(pg, text, size=SIZE):
    """The width, in mm, of a line of plain text."""
    prop = FontProperties(family='Arial', size=size)
    return pg.fig.canvas.get_renderer().get_text_width_height_descent(text, prop, ismath=False)[0] / pg.fig.dpi * 25.4


def pg_right(pg):
    """The right end, in mm, of the last line drawn."""
    pg.fig.canvas.draw()
    return max(t.get_window_extent().x1 for t in BOXES[-1][1]) / pg.fig.bbox.width * lean.W


def check_layout(pg, spans):
    """Stop when two lines of text overlap or a line leaves the page; report the extents (the heads against their
    columns, the gaps between neighbouring heads, the margins)."""
    pg.fig.canvas.draw()
    fw, fh = pg.fig.bbox.width, pg.fig.bbox.height
    ext = []
    for text, drawn in BOXES:
        bb = [t.get_window_extent() for t in drawn]
        ext.append((text, min(b.x0 for b in bb) / fw * lean.W, (1 - max(b.y1 for b in bb) / fh) * H,
                    max(b.x1 for b in bb) / fw * lean.W, (1 - min(b.y0 for b in bb) / fh) * H))
    for i, (a, ax0, ay0, ax1, ay1) in enumerate(ext):
        if ax0 < 1.0 or ax1 > lean.W - 1.0 or ay0 < 0.3 or ay1 > H - 0.3:
            raise SystemExit(f'{a!r} leaves the page: {ax0:.1f}-{ax1:.1f} x {ay0:.1f}-{ay1:.1f} mm')
        for b, bx0, by0, bx1, by1 in ext[i + 1:]:
            if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                raise SystemExit(f'{a!r} overlaps {b!r}')
    by_text = {e[0]: e for e in ext}
    heads = []
    for fam, head, _ in FAMILIES:
        lines = [by_text[''.join(t for t, _ in line)] for line in head]
        heads.append((fam, min(e[1] for e in lines), max(e[3] for e in lines)))
    gaps = [f'{a[0]}|{b[0]} {b[1] - a[2]:.1f}' for a, b in zip(heads, heads[1:])]
    same('heads in column order, none touching the next', all(b[1] - a[2] > 1.0 for a, b in zip(heads, heads[1:])),
         True)
    same('the last head clear of the totals\' head', heads[-1][2] < by_text[f'of {len(PAPERS)}'][1] - 1.0, True)
    print(f'layout: {len(ext)} lines of text, none overlapping; leftmost text starts at {min(e[1] for e in ext):.1f} mm,'
          f' rightmost ends at {max(e[3] for e in ext):.1f} mm; lowest ink of text {max(e[4] for e in ext):.1f} mm')
    print('  heads (mm, left-right) over their columns (first-last centre):',
          '; '.join(f'{f} {l:.1f}-{r:.1f} over {spans[f][0]:.1f}-{spans[f][1]:.1f}' for f, l, r in heads))
    print('  gaps between neighbouring heads (mm):', ', '.join(gaps))


def words():
    """Words on the art: tokens with a letter in them (counts are not words); kcat and Km, set as symbols, count as
    words here."""
    return sum(sum(any(ch.isalpha() for ch in w) for w in s.split()) for s in WORDS)


def report():
    """Every drawn number, from the files, for the README."""
    print('rows (filled marks = wrong value stored, of papers):', {name: FELL[k] for k, name, _ in READINGS},
          '; not drawn, the catalogue:', FELL[NOT_DRAWN])
    print('half-filled marks (an undecided cell, no trap cell):', {name: OPEN[k] for k, name, _ in READINGS},
          f'; {sum(len(v) for v in OPEN.values())} on {len(OPEN_ALL)} papers {OPEN_ALL}')
    print('grey dots (the right value stored in every key cell):', {name: len(RIGHT[k]) for k, name, _ in READINGS})
    print('counted as stored (filled + half-filled):', {name: FELL[k][0] + len(OPEN[k]) for k, name, _ in READINGS})
    print('the plain reading, blind re-score:', len(BLIND), 'of 32; differs from code at',
          sorted(BLIND ^ {t['pmid'] for t in PAPERS if fell(t, 'plain_reading')}))
    for fam, head, kinds in FAMILIES:
        per_kind = ', '.join(f"{k} {BY_KIND[k]['papers']}" for k in kinds)
        read = sum(t[NOT_DRAWN + '_fell_in'] in ('yes', 'no') for t in BY_FAMILY[fam])
        opened = [sum(t['pmid'] in OPEN[k] for t in BY_FAMILY[fam]) for k, _, _ in READINGS]
        print(f'family {fam} ({head_text(head)}): {len(BY_FAMILY[fam])} papers ({per_kind});'
              f' plain {COUNTS[fam][0]}, before Verify and Check {COUNTS[fam][1]}, after {COUNTS[fam][2]},'
              f' catalogue {COUNTS[fam][3]} of {read}; half-filled marks {opened}')
    print('columns, left to right (F filled, H half-filled, . grey; rows plain, before, after Verify and Check):')
    for fam, t in COLUMNS:
        marks = ''.join('F' if fell(t, k) else 'H' if t['pmid'] in OPEN[k] else '.' for k, _, _ in READINGS)
        print(f"  {fam:8s} {t['pmid']:11s} {t['kind']:4s} {marks}  catalogue {t[NOT_DRAWN + '_fell_in'] or 'not read'}")
    for (a, b), (better, worse, p) in TEST.items():
        print(f'test {a} -> {b}: better {len(better)} {better}, worse {len(worse)} {worse}, p = {p:.4f}')
    print('drop plain -> after Verify and Check by kind:', sorted(Counter(KIND_OF[p] for p in DROP).items()))
    print('main test, first reading -> before Verify and Check:', MAIN['pairs'], 'pairs;',
          MAIN['first_reading fell in, frozen_reader_alone not'], 'better;',
          MAIN['frozen_reader_alone fell in, first_reading not'], 'worse; p =', MAIN['exact_mcnemar_two_sided_p'])
    print('plain -> after Verify and Check, undecided counted as stored:',
          REVIEW_TEST['plain_reading fell in, frozen_with_verifier_and_code not'], 'better; p =',
          REVIEW_TEST['exact_mcnemar_two_sided_p'])
    print('selection: the 53 by part', dict(Counter(t['set'] for t in TRAPS)), '; the 32 by part',
          dict(Counter(t['set'] for t in PAPERS)), '; trap seen in', dict(Counter(t['trap_seen_in'] for t in PAPERS)),
          '; plain readings by model (summary.json; Sonnet 5.5 read the papers left out)',
          dict(Counter(d['model'] for d in SUMMARY)))
    print("tables: 'kind of trap' words differing from traps.csv's:", KIND_WORDS)
    print('tables: kinds of right answer and trap', sorted(Counter((c['right']['kind'], c['trap']['kind'])
                                                                  for k in KEY_OF.values() for c in k['cells']).items()))


if __name__ == '__main__':
    if '--report' in sys.argv:
        report()
    else:
        build(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'known_traps.png')
