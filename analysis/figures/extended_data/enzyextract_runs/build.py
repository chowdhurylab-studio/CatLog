"""Extended Data 9: EnzyExtract's nine runs against the curation (a table in two blocks), 16 November 2026.

The locked test's second stage (paper/evidence/locked_test_20261109/STAGE2.md, committed 41d125f before any run was
scored on these papers) scored every source against the EnzyExtract group's manual curation of the 79 held-out papers
it covers. Table 1c gives one of EnzyExtract's runs, RGF, which the plan takes as the complete tool, and its footnote 9
says that all nine runs are in Extended Data 9. This is that table, with the rows of CatLog's stored values and the
plain reading above the runs, scored in the same way:
- block a, the stage's first endpoint: for each source the papers where it has a value, its values, those matched to the
  curation, and recall and precision with their 95% intervals;
- block b, the two views Supplementary Note 1 says are given (STAGE2.md's endpoints 3 and 5): recall and precision for
  each constant (kcat, Km, kcat/Km), and recall and precision with their 95% intervals without the two papers whose unit
  header CatLog changed (the two STAGE2.md names).
The stage's rows for EnzyExtract's released database and for BRENDA are not runs and are left out. Rows: CatLog, the
plain reading, RGF, then the other runs by name, case aside (RESULTS.md sorts them by case, which put RxF before gemini).

Run from anywhere (seconds; writes enzyextract_runs.png, .pdf, .tsv and .md beside this script):
    python3 -I -B writing/figures/extended_data/enzyextract_runs/build.py
    python3 -I -B writing/figures/extended_data/enzyextract_runs/build.py --report    (every number and its source)

Every number is read from stage2/results.json; none is typed. The build stops (lean.same) unless:
- results.json was made by the stage's script as it stands (the sha256 of score_stage2.py is the one results.json
  records), after the script's check before use passed, under the plan commit that RESULTS.md names;
- the runs scored are the nine the plan names (STAGE2.md), each read from its rumble_<run>_dev1.tsv, and the plan's
  primary comparator is one of them and the highest of the nine on recall and on precision (the legend says so);
- in every row, recall and precision are the matched count over the curation's scored values and over the source's
  values, the counts add up over kcat, Km and kcat/Km, and each estimate lies inside its interval; the same for each
  constant and for the view without the two papers;
- every row prints as RESULTS.md prints it: in its first table (block a), its table by metric and its table without the
  two papers (block b), which are the two papers STAGE2.md's endpoint 5 names;
- the three rows Table 1c holds (writing/manuscript/results/T1_tests.md, read only) print as Table 1 prints them, with
  Table 1's row labels and column heads, and Table 1's footnote 9 names the same run and counts the same runs;
- the page is 180 mm wide (a two-column table), every text lies inside it, no two texts overlap and no text touches a
  rule;
- the PDF is made as a person would set the table (the owner, 16 Nov 2026: never hundreds or thousands of small pieces,
  but built the way a person makes it): one text object per cell or label, text kept as text, each rule one line, no
  clipping, no images, and fewer than MAX_OBJECTS objects in all.
Style: Nature's Extended Data tables (research-figure-guide.nature.com/figures/extended-data-formatting-guidelines/,
read 16 Nov; writing/research/stocktake_20261111/5_nature_methods_rules.md): 7-pt Arial throughout (the title and the
block letters too), a rule above and below the column heads and at the foot of each block, space rather than a rule
between the blocks, ink only (lean.INK), no grid. ../../lean.py is imported, not edited. Counts and three-decimal shares
are right-aligned among themselves and centred as a block under their head; estimates with intervals start at their
head's left edge; the width left over goes to the gaps between columns. The PDF keeps its text as text (pdf.fonttype 42,
TrueType embedded) and carries no date. The PNG (300 dpi, RGB) is drawn at 1,200 dpi and reduced, so that every cell of
a row sits on one baseline. Neither PNG nor PDF is a file the journal takes for Extended Data (JPEG, TIFF or EPS): both
are working copies until the owner calls the art final (README, open items).
"""
import csv
import hashlib
import io
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True               # lean.py lives outside this folder: leave no __pycache__ beside it
HERE = Path(__file__).resolve().parent        # writing/figures/extended_data/enzyextract_runs
FIGS = HERE.parents[1]                        # writing/figures
ROOT = HERE.parents[3]                        # the CatLog folder
TEST = ROOT / 'paper' / 'evidence' / 'locked_test_20261109'
STAGE2 = TEST / 'stage2'
TABLE1 = ROOT / 'writing' / 'manuscript' / 'results' / 'T1_tests.md'
sys.path.insert(0, str(FIGS))
import lean  # noqa: E402
from lean import same, INK  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from PIL import Image  # noqa: E402
import fitz  # noqa: E402  (PyMuPDF: reads the PDF back to count what it is made of)

NAME = 'enzyextract_runs'
SUPER = 4      # the PNG is drawn at 4 x 300 dpi and reduced: at 300 dpi Agg rounds each text to whole pixels by its own
               # descent, which set a cell holding a comma or a bracket a pixel off its row
METRICS = ('kcat', 'Km', 'kcat/Km')
SHARES = ('recall', 'precision')
WORDS = dict(enumerate('zero one two three four five six seven eight nine ten eleven twelve'.split()))
MAX_OBJECTS = 400                             # the PDF's text objects and drawn paths together (199 now)
RULE_CLEAR = 0.25                             # mm: the least room between a text's box and a rule
REPORT = []                                   # every number and its source, for --report


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def find(pattern, text, where):
    m = re.search(pattern, text)
    if not m:
        raise SystemExit(f'{where}: {pattern!r} not found')
    return m


def share(b, sep):
    """An estimate and its 95% interval: RESULTS.md writes 'lo-hi' (sep '-'), Table 1 'lo to hi' (sep ' to ')."""
    return f"{b['est']:.3f} ({b['lo']:.3f}{sep}{b['hi']:.3f})"


def key_of(label):
    """The results.json key of a RESULTS.md row label; None for EnzyExtract's database and BRENDA (not runs)."""
    if label.startswith('CatLog'):
        return 'catlog'
    if label.startswith('Plain read'):
        return 'plain'
    if label.startswith('EnzyExtract run '):
        return 'run_' + label[len('EnzyExtract run '):]
    return None


# ===================================================================================================== data
RES = json.loads((STAGE2 / 'results.json').read_text())
RES_MD = (STAGE2 / 'RESULTS.md').read_text()
PLAN = (TEST / 'STAGE2.md').read_text()
T1 = TABLE1.read_text()
SRC = RES['sources']
PAPERS = RES['papers']
CURATED = RES['curation_values']['scored']
LINES = RES_MD.splitlines()


def printed_table(first, where):
    """RESULTS.md's table whose head line starts with `first`: {key: the cells after the label}, in its order."""
    top = next((i for i, line in enumerate(LINES) if line.startswith(first)), None)
    if top is None:
        raise SystemExit(f'RESULTS.md: no table starts {first!r} ({where})')
    rows = {}
    for line in LINES[top + 2:]:
        if not line.startswith('|'):
            break
        c = cells(line)
        if key_of(c[0]):
            rows[key_of(c[0])] = c[1:]
    return rows


# Provenance: the stage's own script made results.json, under the plan RESULTS.md names, after its check passed.
same('plan commit: results.json against RESULTS.md', RES['plan_commit'],
     find(r'STAGE2\.md \(commit (\w+),', RES_MD, 'RESULTS.md').group(1))
same('the check before use passed (results.json)', RES['check_passed'], True)
same('score_stage2.py is the script results.json records', sha256(STAGE2 / 'score_stage2.py'),
     RES['inputs_sha256']['score_stage2.py'])
same('papers: results.json against RESULTS.md', PAPERS, int(find(r'on (\d+) held-out papers', RES_MD, 'RESULTS.md').group(1)))
same('papers: results.json papers_list', len(RES['papers_list']), PAPERS)
same("the curation's scored values: results.json against RESULTS.md", CURATED,
     int(find(r"The curation's values on these papers: (\d+) scored", RES_MD, 'RESULTS.md').group(1)))
same("the curation's values not scored: results.json against RESULTS.md", RES['curation_values']['unscored'],
     int(find(r"The curation's values on these papers: \d+ scored, (\d+) not scored", RES_MD, 'RESULTS.md').group(1)))
BOOT = find(r'B (\d+), seed (\d+)', RES_MD, 'RESULTS.md')
same('bootstrap: results.json against RESULTS.md', (RES['bootstrap']['B'], RES['bootstrap']['seed']),
     (int(BOOT.group(1)), int(BOOT.group(2))))
TOLERANCE = find(r'within ([\d.]+)%', RES_MD, 'RESULTS.md').group(1)          # the matching tolerance, for the legend

# The runs: the nine the plan names, each read from its file of the EnzyExtract paper's supplementary data.
RUN_KEYS = [k for k in SRC if k.startswith('run_')]
for k in RUN_KEYS:
    if f'rumble_{k[4:]}_dev1.tsv' not in RES['inputs_sha256']:
        raise SystemExit(f'{k}: no rumble_{k[4:]}_dev1.tsv among the files results.json hashed')
PLAN_RUNS = find(r'extracted them: ([^|]+?) \|', PLAN, 'STAGE2.md').group(1).split(', ')
same('runs: the plan (STAGE2.md) against results.json', sorted(PLAN_RUNS), sorted(k[4:] for k in RUN_KEYS))
PRIMARY = find(r'\*\*Primary comparator: ([^.*]+)\.\*\*', PLAN, 'STAGE2.md').group(1)
same("the plan's primary comparator is a scored run", 'run_' + PRIMARY in RUN_KEYS, True)
for what in SHARES:
    top = max(RUN_KEYS, key=lambda k: SRC[k]['all'][what]['est'])
    same(f'the highest run on {what}: recomputed against results.json best_run', top, RES['best_run'][what])
    same(f"the highest run on {what} is the plan's primary comparator (the legend says so)", top, 'run_' + PRIMARY)

# Block a: RESULTS.md's first table, its rows for CatLog, the plain reading and the runs.
PRINTED = printed_table('| Source | Papers with values | Values | Recall', 'the first table')
ORDER = list(PRINTED)
same("RESULTS.md's order: CatLog, the plain reading, the primary run", ORDER[:3], ['catlog', 'plain', 'run_' + PRIMARY])
same("RESULTS.md's run rows are the runs scored", sorted(ORDER[2:]), sorted(RUN_KEYS))
ORDER = ORDER[:3] + sorted(ORDER[3:], key=str.lower)   # the other runs by name, case aside (RESULTS.md: by case)

for key in ORDER:
    s, a = SRC[key], SRC[key]['all']
    rec, pre = a['recall'], a['precision']
    same(f'{key}: recall counts the matched values', rec['num'], a['matched'])
    same(f'{key}: precision counts the matched values', pre['num'], a['matched'])
    same(f"{key}: recall is over the curation's scored values", (rec['den'], a['gold_n']), (CURATED, CURATED))
    same(f'{key}: precision is over its values', pre['den'], a['sys_n'])
    same(f'{key}: recall = matched / curation', round(rec['est'], 12), round(a['matched'] / CURATED, 12))
    same(f'{key}: precision = matched / values', round(pre['est'], 12), round(a['matched'] / a['sys_n'], 12))
    for what, b in (('recall', rec), ('precision', pre)):
        same(f'{key}: {what} lies inside its interval', b['lo'] <= b['est'] <= b['hi'], True)
    for n in ('matched', 'gold_n', 'sys_n'):
        same(f'{key}: {n} adds up over kcat, Km and kcat/Km', sum(s[m][n] for m in METRICS), a[n])
    same(f'{key}: papers with values, of {PAPERS}', 0 < s['papers_with_values'] <= PAPERS, True)
    same(f'{key}: RESULTS.md prints the same row', PRINTED[key][:4],
         [str(s['papers_with_values']), str(a['sys_n']), share(rec, '-'), share(pre, '-')])

# Block b, by constant (endpoint 3's view, per source): RESULTS.md's table by metric.
BY_PRINTED = printed_table('| Source | kcat | Km | kcat/Km |', 'by metric')
GOLD = {m: SRC['catlog'][m]['gold_n'] for m in METRICS}                     # the curation's values per constant
for key in ORDER:
    s = SRC[key]
    for m in METRICS:
        b = s[m]
        same(f'{key}, {m}: the curation holds the same values for every source', b['gold_n'], GOLD[m])
        same(f'{key}, {m}: it has values', b['sys_n'] > 0, True)
        same(f'{key}, {m}: recall = matched / curation', round(b['recall']['est'], 12), round(b['matched'] / b['gold_n'], 12))
        same(f'{key}, {m}: precision = matched / values', round(b['precision']['est'], 12),
             round(b['matched'] / b['sys_n'], 12))
    same(f'{key}: RESULTS.md prints the same shares by constant', BY_PRINTED[key],
         [f"{s[m]['recall']['est']:.3f}, {s[m]['precision']['est']:.3f}" for m in METRICS])

# Block b, without the two papers (endpoint 5): RESULTS.md's table of that name, the papers STAGE2.md registered.
WO = RES['without_misprint_papers']
WO_HEAD = find(r'(?m)^## Without (\d+) and (\d+) \((\d+) papers\)$', RES_MD, 'RESULTS.md')
LEFT_OUT = (WO_HEAD.group(1), WO_HEAD.group(2))
same('without the two: papers, results.json against RESULTS.md', WO['papers'], int(WO_HEAD.group(3)))
same('without the two: the stage\'s papers less the two', WO['papers'], PAPERS - 2)
same('without the two: both are papers of the stage', all(p in RES['papers_list'] for p in LEFT_OUT), True)
same("without the two: the papers of STAGE2.md's endpoint 5", f'Sensitivity without {LEFT_OUT[0]} and {LEFT_OUT[1]}' in PLAN,
     True)
WO_PRINTED = printed_table('| Source | Recall (95%) | Precision (95%) |', 'without the two papers')
WO_CURATED = WO['sources']['catlog']['gold_n']
same("without the two: fewer of the curation's values than on all the papers", 0 < WO_CURATED < CURATED, True)
for key in ORDER:
    w = WO['sources'][key]
    rec, pre = w['recall'], w['precision']
    same(f'{key} without the two: recall counts the matched over the curation', (rec['num'], rec['den'], w['gold_n']),
         (w['matched'], WO_CURATED, WO_CURATED))
    same(f'{key} without the two: precision counts the matched over its values', (pre['num'], pre['den']),
         (w['matched'], w['sys_n']))
    same(f'{key} without the two: recall = matched / curation', round(rec['est'], 12), round(w['matched'] / WO_CURATED, 12))
    same(f'{key} without the two: precision = matched / values', round(pre['est'], 12), round(w['matched'] / w['sys_n'], 12))
    for what, b in (('recall', rec), ('precision', pre)):
        same(f'{key} without the two: {what} lies inside its interval', b['lo'] <= b['est'] <= b['hi'], True)
    same(f'{key} without the two: RESULTS.md prints the same row', WO_PRINTED[key][:2], [share(rec, '-'), share(pre, '-')])

# Table 1 as written (read only): block c's head, columns, three rows and footnote.
T1_LINES = T1.splitlines()
C_AT = next(i for i, line in enumerate(T1_LINES) if line.startswith('**c,'))
D_AT = next(i for i, line in enumerate(T1_LINES) if line.startswith('**d,'))
C_HEAD = T1_LINES[C_AT]
same('Table 1c: papers', int(find(r'on (\d+) of the \d+ papers', C_HEAD, 'Table 1c').group(1)), PAPERS)
GROUP = find(r"(the EnzyExtract group's manual curation)", C_HEAD, 'Table 1c').group(1)
BLOCK = [cells(line) for line in T1_LINES[C_AT + 1:D_AT] if line.startswith('|') and not line.startswith('|---')]
T1_HEAD, T1_ROWS = BLOCK[0], BLOCK[1:]
same("Table 1c's columns", [h.split(' ')[0] for h in T1_HEAD], ['Source', 'Values', 'Recall', 'Precision'])


def t1_row(prefix):
    hits = [r for r in T1_ROWS if r[0].startswith(prefix)]
    same(f'Table 1c: rows that start {prefix!r}', len(hits), 1)
    return hits[0]


T1_KEYS = {'catlog': t1_row('CatLog'), 'plain': t1_row('Plain'), 'run_' + PRIMARY: t1_row('EnzyExtract')}
NOTE = find(r'\^(\d+)$', T1_KEYS['run_' + PRIMARY][0], 'Table 1c').group(1)
TOOL = T1_KEYS['run_' + PRIMARY][0][:-len('^' + NOTE)]                         # 'EnzyExtract'
NOTE_TEXT = next(line for line in T1_LINES if line.startswith(f'^{NOTE} '))
same(f"Table 1's footnote {NOTE}: the run it names", find(r'Its run (\S+?),', NOTE_TEXT, 'Table 1').group(1), PRIMARY)
# 'All nine runs are in Extended Data 9' (the writing chat's edit pass of 16 Nov; it said 'are reported in' before)
CITED = find(r'All (\w+) runs are (?:reported )?in (Extended Data \d+)', NOTE_TEXT, 'Table 1')
same(f"Table 1's footnote {NOTE}: the runs it counts", CITED.group(1), WORDS[len(RUN_KEYS)])
ED = CITED.group(2)                                                            # 'Extended Data 9'
for key, row in T1_KEYS.items():
    a = SRC[key]['all']
    same(f'Table 1c prints {row[0]!r} as this table does', row[1:4],
         [f"{a['sys_n']:,}", share(a['recall'], ' to '), share(a['precision'], ' to ')])
LABEL = {'catlog': T1_KEYS['catlog'][0], 'plain': T1_KEYS['plain'][0]}       # Table 1's row labels

# ===================================================================================================== the table
HEAD = {'papers': 'Papers with values', 'values': T1_HEAD[1], 'matched': 'Matched', 'recall': T1_HEAD[2],
        'precision': T1_HEAD[3]}
COLS = (('papers', 'right'), ('values', 'right'), ('matched', 'right'), ('recall', 'left'), ('precision', 'left'))
SUB = {what: HEAD[what].split(' (')[0] for what in SHARES}                    # 'Recall', 'Precision'
MATH = {'kcat': r'$k_\mathrm{cat}$', 'Km': lean.KM_T, 'kcat/Km': r'$k_\mathrm{cat}/K_\mathrm{m}$'}
WITHOUT = 'Without two papers'
B_COLS = [(f'{m}|{what}', SUB[what], 'right') for m in METRICS for what in SHARES] + \
         [(f'wo|{what}', HEAD[what], 'left') for what in SHARES]
SPANS = [MATH[m] for m in METRICS] + [WITHOUT]                                 # over block b's columns, two each
ROWS = []
for key in ORDER:
    s, a, w = SRC[key], SRC[key]['all'], WO['sources'][key]
    row = {'key': key, 'source': LABEL.get(key, TOOL), 'run': key[4:] if key in RUN_KEYS else '',
           'stub': LABEL.get(key, TOOL if key == ORDER[2] else ''),             # the tool's name once, on its first run
           'papers': str(s['papers_with_values']), 'values': f"{a['sys_n']:,}", 'matched': f"{a['matched']:,}",
           'recall': share(a['recall'], ' to '), 'precision': share(a['precision'], ' to ')}
    row.update({f'{m}|{what}': f"{s[m][what]['est']:.3f}" for m in METRICS for what in SHARES})
    row.update({f'wo|{what}': share(w[what], ' to ') for what in SHARES})
    ROWS.append(row)
TITLE_BOLD = f'{TOOL}’s {WORDS[len(RUN_KEYS)]} runs against the curation'
TITLE_PLAIN = f"({GROUP.replace(chr(39), chr(0x2019))}: {CURATED:,} values in {PAPERS} held-out papers)"

# ===================================================================================================== layout, mm
SIZE = 7.0                                    # pt, every text: Nature's Extended Data tables ask for 7-pt text
W = lean.W                                    # 180 mm: Nature sets a table at one column (89 mm) or two (180 mm)
ML = MR = 2.0                                 # the other Extended Data items start their title 2 mm in
GAP_MIN, GAP_IN, STUB_GAP, NAME_GAP = 3.0, 3.5, 1.6, 0.9   # least gap; under one spanner; tool name to runs; title parts
PITCH, GROUP_GAP = 3.2, 1.0                   # baseline to baseline; added above the tool's runs
Y_TITLE = 4.85                                # the title's baseline (its ink starts 3.1 mm down, as in ED 3 and 7)
ABOVE = 2.3                                   # a baseline to the rule under it, where that rule tops a block
DROP = 3.2                                    # a rule to the baseline of the heads under it
BELOW = 1.3                                   # a baseline to the rule under it (the heads, the last row)
SPAN_BELOW = 1.7                              # a spanner's baseline to its rule: room for the subscripts of kcat and Km
FIRST = 3.1                                   # the rule under the heads to the first row's baseline
BLOCK_GAP = 4.0                               # block a's foot rule to block b's top rule: space, not a rule
FOOT = 1.8                                    # block b's foot rule to the page's foot

_measure = plt.figure(dpi=lean.DPI)
_renderer = _measure.canvas.get_renderer()


def width(text, size=SIZE, weight='normal'):
    prop = FontProperties(family='Arial', size=size, weight=weight)
    return _renderer.get_text_width_height_descent(text, prop, ismath='$' in text)[0] / lean.DPI * 25.4


def rows_from(y):
    """The rows' baselines, the first at y; the tool's runs a little apart from the rows above them."""
    out = []
    for i in range(len(ROWS)):
        y += GROUP_GAP if i == 2 else 0
        out.append(y)
        y += PITCH
    return out


RUN_X = ML + width(TOOL) + STUB_GAP
STUB_RIGHT = max([ML + width(t) for t in LABEL.values()] + [RUN_X + width(r['run']) for r in ROWS if r['run']])
TABLE_RIGHT = W - MR

# Block a: five columns from the stub to the table's right edge, the room left over shared out as gaps.
A_W = {c: max(width(HEAD[c]), max(width(r[c]) for r in ROWS)) for c, _ in COLS}
A_GAP = (TABLE_RIGHT - STUB_RIGHT - sum(A_W.values())) / len(COLS)
same(f'block a: its columns fit at {W:g} mm with gaps of {GAP_MIN} mm or more', A_GAP >= GAP_MIN, True)
COLX, x = {}, STUB_RIGHT                      # per column: (x, ha) of its head and of its cells
for c, align in COLS:
    x += A_GAP
    w = A_W[c]
    if align == 'right':                      # counts: right-aligned among themselves, the block centred under its head
        COLX[c] = ((x + w / 2, 'center'), (x + (w + max(width(r[c]) for r in ROWS)) / 2, 'right'))
    else:                                     # estimates with intervals: head and cells from the same left edge
        COLX[c] = ((x, 'left'), (x, 'left'))
    x += w
same('block a: its last column ends at the right margin', round(x, 6), round(TABLE_RIGHT, 6))

# Block b: four spanners of two columns each; the two under a spanner GAP_IN apart, the room left over between spanners.
B_W = [max(width(head), max(width(r[k]) for r in ROWS)) for k, head, _ in B_COLS]
B_GAP = (TABLE_RIGHT - STUB_RIGHT - sum(B_W) - len(SPANS) * GAP_IN) / len(SPANS)
same(f'block b: its columns fit at {W:g} mm with gaps of {GAP_MIN} mm or more', B_GAP >= GAP_MIN, True)
B_COLX, SPANX, x = {}, [], STUB_RIGHT
for i, (k, head, align) in enumerate(B_COLS):
    x += B_GAP if i % 2 == 0 else GAP_IN
    w = B_W[i]
    if align == 'right':
        B_COLX[k] = ((x + w / 2, 'center'), (x + (w + max(width(r[k]) for r in ROWS)) / 2, 'right'), x, x + w)
    else:
        B_COLX[k] = ((x, 'left'), (x, 'left'), x, x + w)
    x += w
same('block b: its last column ends at the right margin', round(x, 6), round(TABLE_RIGHT, 6))
for j, text in enumerate(SPANS):                # each spanner centred over its two columns, its rule under both
    x0, x1 = B_COLX[B_COLS[2 * j][0]][2], B_COLX[B_COLS[2 * j + 1][0]][3]
    same(f'block b: spanner {text!r} is narrower than its two columns', width(text) < x1 - x0, True)
    SPANX.append((text, (x0 + x1) / 2, x0, x1))

PLAIN_X = ML + width(TITLE_BOLD, weight='bold') + NAME_GAP
TITLE_RIGHT = PLAIN_X + width(TITLE_PLAIN)
same('the title fits on one line', TITLE_RIGHT <= TABLE_RIGHT, True)
plt.close(_measure)

A_TOP = Y_TITLE + ABOVE                       # block a: the rule above its heads, its heads (and the letter a), the rule
A_HEAD = A_TOP + DROP                         # under them, its rows and the rule at its foot
A_RULE = A_HEAD + BELOW
A_YS = rows_from(A_RULE + FIRST)
A_FOOT = A_YS[-1] + BELOW
B_TOP = A_FOOT + BLOCK_GAP                    # block b: the same, with a line of spanners (and the letter b) above its
B_SPAN = B_TOP + DROP                         # heads and a short rule under each spanner
B_SPAN_RULE = B_SPAN + SPAN_BELOW
B_HEAD = B_SPAN_RULE + DROP
B_RULE = B_HEAD + BELOW
B_YS = rows_from(B_RULE + FIRST)
B_FOOT = B_YS[-1] + BELOW
H = math.ceil((B_FOOT + FOOT) * 2) / 2
RULES = [(y, ML, TABLE_RIGHT) for y in (A_TOP, A_RULE, A_FOOT, B_TOP, B_RULE, B_FOOT)] + \
        [(B_SPAN_RULE, x0, x1) for _, _, x0, x1 in SPANX]


def draw():
    fig = plt.figure(figsize=(W / 25.4, H / 25.4), dpi=lean.DPI)

    def put(x, y, text, ha='left', weight='normal'):
        fig.text(x / W, 1 - y / H, text, fontsize=SIZE, fontweight=weight, ha=ha, va='baseline', color=INK)

    put(ML, Y_TITLE, TITLE_BOLD, weight='bold')
    put(PLAIN_X, Y_TITLE, TITLE_PLAIN)
    for y, x0, x1 in RULES:
        fig.add_artist(Line2D([x0 / W, x1 / W], [1 - y / H] * 2, transform=fig.transFigure, color=INK, linewidth=0.5,
                              solid_capstyle='butt'))
    put(ML, A_HEAD, 'a', weight='bold')
    for c, ((hx, ha), _) in COLX.items():
        put(hx, A_HEAD, HEAD[c], ha=ha)
    put(ML, B_SPAN, 'b', weight='bold')
    for text, cx, _, _ in SPANX:
        put(cx, B_SPAN, text, ha='center')
    for k, head, _ in B_COLS:
        (hx, ha), _, _, _ = B_COLX[k]
        put(hx, B_HEAD, head, ha=ha)
    for ys, cols in ((A_YS, [(c, COLX[c][1]) for c, _ in COLS]), (B_YS, [(k, B_COLX[k][1]) for k, _, _ in B_COLS])):
        for r, y in zip(ROWS, ys):
            if r['stub']:
                put(ML, y, r['stub'])
            if r['run']:
                put(RUN_X, y, r['run'])
            for c, (cx, ha) in cols:
                put(cx, y, r[c], ha=ha)
    # every text inside the page, no two overlapping, none touching a rule; the closest pairs, for the README
    fig.canvas.draw()
    px = lean.DPI / 25.4
    boxes = [(t.get_text(), t.get_window_extent()) for t in fig.texts]
    for text, b in boxes:
        if b.x0 < 0 or b.y0 < 0 or b.x1 > fig.bbox.x1 or b.y1 > fig.bbox.y1:
            raise SystemExit(f'text leaves the page: {text!r}')
    across, down, ruled = [], [], []
    for i, (ta, a) in enumerate(boxes):
        for tb, b in boxes[i + 1:]:
            if a.x0 < b.x1 and b.x0 < a.x1 and a.y0 < b.y1 and b.y0 < a.y1:
                raise SystemExit(f'texts overlap: {ta!r} and {tb!r}')
            if a.y0 < b.y1 and b.y0 < a.y1:
                across.append((max(b.x0 - a.x1, a.x0 - b.x1) / px, ta, tb))
            elif a.x0 < b.x1 and b.x0 < a.x1:
                down.append((max(b.y0 - a.y1, a.y0 - b.y1) / px, ta, tb))
        for y, x0, x1 in RULES:                 # the rule's own half width (0.25 pt) counts against the room
            ry = (H - y) * px
            if a.x0 < x1 * px and x0 * px < a.x1:
                ruled.append((max(a.y0 - ry, ry - a.y1) / px - 0.25 / 72 * 25.4, ta, y))
    if min(ruled)[0] < RULE_CLEAR:
        raise SystemExit(f'a text touches a rule: {min(ruled)}')
    left = min(b.x0 for _, b in boxes) / px
    right = max(b.x1 for _, b in boxes) / px
    return fig, min(across), min(down), min(ruled), (left, right)


# ===================================================================================================== outputs
def make_up(data):
    """What the PDF is made of, read back with PyMuPDF: text objects (BT ... ET), drawn paths, clips, images, forms."""
    doc = fitz.open(stream=data, filetype='pdf')
    page = doc[0]
    raw = b''.join(doc.xref_stream(x) or b'' for x in page.get_contents()).decode('latin-1')
    raw = re.sub(r'\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]*>', ' ', raw)          # strings set aside: count operators only
    out = {'text objects': len(re.findall(r'(?<![A-Za-z])BT(?![A-Za-z])', raw)),
           'paths': len(page.get_drawings()),
           'clips': len(re.findall(r'(?<![A-Za-z])W\*?\s+n(?![A-Za-z])', raw)),
           'images': len(page.get_images(full=True)),
           'forms': len(page.get_xobjects()),
           'text': ' '.join(page.get_text().split())}
    doc.close()
    return out


def check_pdf(data, fig):
    """The PDF as a person would make the table: one text object per cell or label, text kept as text, each rule one
    line (and the white page), no clipping, images or nested forms, and fewer than MAX_OBJECTS objects in all."""
    got = make_up(data)
    texts = [t.get_text() for t in fig.texts]
    same('PDF: one text object per cell or label', got['text objects'], len(texts))
    same('PDF: the rules as single lines, and the page', got['paths'], len(RULES) + 1)
    same('PDF: no clipping (nothing opens as a clip group)', got['clips'], 0)
    same('PDF: no images, no nested forms', (got['images'], got['forms']), (0, 0))
    same(f'PDF: fewer than {MAX_OBJECTS} objects', got['text objects'] + got['paths'] < MAX_OBJECTS, True)
    lost = [t for t in texts if '$' not in t and ' '.join(t.split()) not in got['text']]
    same('PDF: every text kept as text, each in one piece', lost, [])
    return got


def write_tsv():
    buf = io.StringIO()
    out = csv.writer(buf, delimiter='\t', lineterminator='\n')
    by = [f"{m.replace('/', '_over_')}_{what}" for m in METRICS for what in SHARES]
    out.writerow(['source', 'run', 'papers', 'papers_with_values', 'values', 'matched', 'curation_values', 'recall',
                  'recall_lo', 'recall_hi', 'precision', 'precision_lo', 'precision_hi', *by,
                  'without_two_papers', 'without_two_curation_values', 'without_two_recall', 'without_two_recall_lo',
                  'without_two_recall_hi', 'without_two_precision', 'without_two_precision_lo',
                  'without_two_precision_hi', 'results_json_key'])
    for r in ROWS:
        s, a, w = SRC[r['key']], SRC[r['key']]['all'], WO['sources'][r['key']]
        out.writerow([r['source'], r['run'], PAPERS, s['papers_with_values'], a['sys_n'], a['matched'], CURATED,
                      *(f'{a[what][k]:.3f}' for what in SHARES for k in ('est', 'lo', 'hi')),
                      *(f"{s[m][what]['est']:.3f}" for m in METRICS for what in SHARES),
                      WO['papers'], WO_CURATED, *(f'{w[what][k]:.3f}' for what in SHARES for k in ('est', 'lo', 'hi')),
                      r['key']])
    (HERE / f'{NAME}.tsv').write_text(buf.getvalue())


def write_md():
    plain = TITLE_PLAIN[1:-1].replace('’', "'")
    md_math = {'kcat': '*k*cat', 'Km': '*K*m', 'kcat/Km': '*k*cat/*K*m'}
    head_a = ['Source', 'Run'] + [HEAD[c] for c, _ in COLS]
    head_b = ['Source', 'Run'] + [f'{md_math[m]}: {SUB[what].lower()}' for m in METRICS for what in SHARES] + \
             [f'{WITHOUT}: {HEAD[what][0].lower() + HEAD[what][1:]}' for what in SHARES]
    md = [f"# {ED} | {TITLE_BOLD.replace(chr(0x2019), chr(39))}", '', plain[0].upper() + plain[1:] + '.', '',
          '**a**', '', '| ' + ' | '.join(head_a) + ' |',
          '|' + '|'.join(['---', '---'] + ['---:' if a == 'right' else '---' for _, a in COLS]) + '|']
    for r in ROWS:
        md.append('| ' + ' | '.join([r['stub'], r['run']] + [r[c] for c, _ in COLS]) + ' |')
    md += ['', f"**b** By constant ({', '.join(f'{md_math[m]} {GOLD[m]:,}' for m in METRICS)} of the curation's values), "
               f"and {WITHOUT.lower()}: {LEFT_OUT[0]} and {LEFT_OUT[1]}, whose unit header CatLog changed "
               f"({WO['papers']} papers, {WO_CURATED:,} of the curation's values).", '',
           '| ' + ' | '.join(head_b) + ' |',
           '|' + '|'.join(['---', '---'] + ['---:' if a == 'right' else '---' for _, _, a in B_COLS]) + '|']
    for r in ROWS:
        md.append('| ' + ' | '.join([r['stub'], r['run']] + [r[k] for k, _, _ in B_COLS]) + ' |')
    md += ['', f"<!-- src: {rel(STAGE2 / 'results.json')} (papers ; curation_values.scored ; sources.<key>.papers_with_values, "
               f".all.sys_n, .all.matched, .all.recall, .all.precision ; sources.<key>.<constant>.recall.est and "
               f".precision.est ; without_misprint_papers.papers and .sources.<key>.recall, .precision) ; "
               f"{rel(STAGE2 / 'RESULTS.md')}#first table, #By metric, #Without {LEFT_OUT[0]} and {LEFT_OUT[1]} (every "
               f"row checked equal) ; {rel(TEST / 'STAGE2.md')} (commit {RES['plan_commit']}: the "
               f"{WORDS[len(RUN_KEYS)]} runs, {PRIMARY} the primary comparator, endpoints 1, 3 and 5) ; {rel(TABLE1)} block c "
               f"(its three rows checked equal) ; built by {rel(HERE / 'build.py')} ; as of 2026-11-11 ; registered ; "
               "refresh: no -->", '']
    (HERE / f'{NAME}.md').write_text('\n'.join(md))


def words_on_art():
    """Tokens with a letter in them, as drawn: the title, the heads and spanners (a constant's symbol is one word), the
    row labels in both blocks; numbers, the run names and the block letters are not counted."""
    def n(text):
        return 1 if '$' in text else sum(1 for t in text.split() if re.search('[A-Za-z]', t))
    heads = [HEAD[c] for c, _ in COLS] + SPANS + [head for _, head, _ in B_COLS]
    labels = [r['stub'] for r in ROWS if r['stub']] * 2
    return {'title': n(TITLE_BOLD) + n(TITLE_PLAIN), 'heads': sum(n(t) for t in heads),
            'row labels': sum(n(t) for t in labels)}


def report(across, down, ruled, span, pdf):
    k = 'results.json'
    REPORT.extend([
        f"inputs: {rel(STAGE2 / 'results.json')} sha256 {sha256(STAGE2 / 'results.json')}",
        f"        {rel(STAGE2 / 'RESULTS.md')} sha256 {sha256(STAGE2 / 'RESULTS.md')}",
        f"        {rel(STAGE2 / 'score_stage2.py')} sha256 {sha256(STAGE2 / 'score_stage2.py')} (= results.json inputs_sha256)",
        f"        {rel(TEST / 'STAGE2.md')} sha256 {sha256(TEST / 'STAGE2.md')}; {rel(TABLE1)} sha256 {sha256(TABLE1)}",
        f"title: {WORDS[len(RUN_KEYS)]} runs = the {len(RUN_KEYS)} run_* sources of {k} (= STAGE2.md's list; Table 1 "
        f"footnote {NOTE} 'All {CITED.group(1)} runs')",
        f"title: {CURATED:,} values = {k} curation_values.scored (= RESULTS.md; recall's denominator in every row of a); "
        f"{PAPERS} held-out papers = {k} papers (= RESULTS.md; Table 1c)",
        f"curation values not scored: {RES['curation_values']['unscored']} ({k} curation_values.unscored = RESULTS.md), "
        f"so {CURATED + RES['curation_values']['unscored']:,} in all",
        f"primary comparator: {PRIMARY} (STAGE2.md); highest of the runs on recall and on precision ({k} best_run)",
        f"matching within {TOLERANCE}%; bootstrap B {RES['bootstrap']['B']}, seed {RES['bootstrap']['seed']} (RESULTS.md, {k})",
        f"b, the curation's values per constant: " + ', '.join(f'{m} {GOLD[m]}' for m in METRICS) +
        f" ({k} sources.<key>.<constant>.gold_n, the same for every source; sum {sum(GOLD.values()):,})",
        f"b, without the two: {LEFT_OUT[0]} and {LEFT_OUT[1]} (RESULTS.md's section head; STAGE2.md endpoint 5): "
        f"{WO['papers']} papers, {WO_CURATED:,} curation values ({k} without_misprint_papers)"])
    for r in ROWS:
        q = f"{k} sources.{r['key']}"
        also = ' = RESULTS.md' + ('; = Table 1c' if r['key'] in T1_KEYS else '')
        REPORT.append(f"a, {r['source']}{' ' + r['run'] if r['run'] else ''}: papers with values {r['papers']} "
                      f"({q}.papers_with_values); values {r['values']} (.all.sys_n); matched {r['matched']} (.all.matched); "
                      f"recall {r['recall']} (.all.recall); precision {r['precision']} (.all.precision){also}")
    for r in ROWS:
        REPORT.append(f"b, {r['source']}{' ' + r['run'] if r['run'] else ''}: " +
                      '; '.join(f"{m} {r[f'{m}|recall']}, {r[f'{m}|precision']}" for m in METRICS) +
                      f" ({k} sources.{r['key']}.<constant>.recall.est, .precision.est = RESULTS.md by metric); "
                      f"without the two: recall {r['wo|recall']}, precision {r['wo|precision']} "
                      f"({k} without_misprint_papers.sources.{r['key']} = RESULTS.md)")
    others = [kk for kk in RUN_KEYS if kk != 'run_' + PRIMARY]
    for what in SHARES:
        lo_k = min(others, key=lambda kk: SRC[kk]['all'][what]['est'])
        hi_k = max(others, key=lambda kk: SRC[kk]['all'][what]['est'])
        REPORT.append(f"the other {WORDS[len(others)]} runs, {what}: {SRC[lo_k]['all'][what]['est']:.3f} ({lo_k[4:]}) to "
                      f"{SRC[hi_k]['all'][what]['est']:.3f} ({hi_k[4:]})")
    unread = {kk[4:]: sum(v.values()) for kk, v in RES['unreadable_cells'].items() if kk.startswith('run_')}
    REPORT.append('cells not scored per run (a bound, a number with no unit, or a cell the units code cannot read; '
                  f"{k} unreadable_cells summed over the constants): " +
                  ', '.join(f'{kk} {v}' for kk, v in sorted(unread.items(), key=lambda kv: kv[1])) +
                  f" (from {min(unread.values())} to {max(unread.values())})")
    wd = words_on_art()
    REPORT.append(f"words on the art: {sum(wd.values())} (" + ', '.join(f'{kk} {v}' for kk, v in wd.items()) +
                  f"; numbers, the {len(RUN_KEYS)} run names and the block letters not counted)")
    REPORT.extend([
        f"context, {k}: papers without a row {RES['papers_without_a_row']}",
        f"context, {k}: exact repeats dropped {RES['repeats_dropped']}",
        f"context, {k}: cells the units code cannot read (not scored) {RES['unreadable_cells']}",
        f"render: {W:g} x {H:g} mm, {int(W / 25.4 * lean.DPI)} x {int(H / 25.4 * lean.DPI)} px at {lean.DPI} dpi; 7 pt; "
        f"block a's gaps {A_GAP:.2f} mm, block b's {B_GAP:.2f} mm ({GAP_IN} mm under a spanner); text from {span[0]:.1f} "
        f"to {span[1]:.1f} mm across; closest texts side by side {across[0]:.2f} mm ({across[1]!r}, {across[2]!r}); "
        f"closest texts one above the other {down[0]:.2f} mm ({down[1]!r}, {down[2]!r}); closest text to a rule "
        f"{ruled[0]:.2f} mm ({ruled[1]!r}, the rule at {ruled[2]:.2f} mm)",
        f"PDF made of: {pdf['text objects']} text objects, {pdf['paths']} paths ({len(RULES)} rules and the page), "
        f"{pdf['clips']} clips, {pdf['images']} images, {pdf['forms']} nested forms: "
        f"{pdf['text objects'] + pdf['paths']} objects (the build stops at {MAX_OBJECTS})"])


if __name__ == '__main__':
    fig, across, down, ruled, span = draw()
    plt.rcParams['pdf.fonttype'] = 42             # TrueType embedded: the PDF's text stays text
    vector = io.BytesIO()
    fig.savefig(vector, format='pdf', facecolor='white', metadata={'CreationDate': None})
    pdf = check_pdf(vector.getvalue(), fig)       # checked in memory: nothing is written unless every check passes
    big = io.BytesIO()
    fig.savefig(big, format='png', dpi=lean.DPI * SUPER, facecolor='white')
    plt.close(fig)
    size = (int(W / 25.4 * lean.DPI), int(H / 25.4 * lean.DPI))
    (HERE / f'{NAME}.pdf').write_bytes(vector.getvalue())
    Image.open(big).convert('RGB').resize(size, Image.LANCZOS).save(HERE / f'{NAME}.png', dpi=(lean.DPI, lean.DPI))
    write_tsv()
    write_md()
    for suffix in ('png', 'pdf', 'tsv', 'md'):
        print('wrote', rel(HERE / f'{NAME}.{suffix}'))
    if '--report' in sys.argv:
        report(across, down, ruled, span, pdf)
        print('\n'.join(REPORT))
