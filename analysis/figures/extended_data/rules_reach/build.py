"""Extended Data figure: rules and flags learned from errors (PNG only), 16 November 2026 (third pass), and the
Supplementary Table of all 87 kinds of error (rules_table.tsv).

The list of 16 rules and flags learned from errors (it began as Fig. 4a at git ace3e6c; Fig. 4c draws eight of them):
each kind of error that people, people with an agent, checking agents or code checks found while CatLog read, whose
rule (or flag) has since acted on ten or more papers, its values or records. Five more rules learned from errors acted
on ten or more papers and are not listed (Fig. 4's NOT_LISTED: three that rebuilt texts, a rule on the method, and the
supplement rule, whose files count supplements another way), so the title says '16 of those'; NOT_LISTED also holds
slipped digits, which acted on ten or more papers too and is drawn with the known in Fig. 4a. Fig. 4c's marks: a
filled dot at all papers the rule acted on, its count printed beside it, and 1.6 mm under it an open dot at those of
them first read before the rule (log axis, no stems), both in the colour of who found the error; a '0' where none was.
Two groups on one axis, each under its head:
errors kept out, corrected or flagged (10 rows), and right values no longer lost (6); within a group, rows by finder as
Fig. 4a's names run (0.8 mm between finders), then by reach, so the eight rows Fig. 4c draws come in its order. Row
labels are Fig. 4's (imported); the rule Fig. 4b follows is marked '(Fig. 4b)'. The finder key and the marks' key sit at
the top, the marks' key over the dot columns.

Run from anywhere (seconds; writes rules_reach.png and rules_table.tsv beside this script):
    python3 -I -B writing/figures/extended_data/rules_reach/build.py
    python3 -I -B writing/figures/extended_data/rules_reach/build.py --report      (every drawn number, for the README)

Every count and label is imported from Fig. 4's build (writing/figures/fig4/v2/final/build_fig4_v2.py, as F4), which
holds the data code and all its checks: catches that are not the drawn kind left out as named sets, each paper's amount
asserted and its reason stated (PP1, RA3, PP5); verifier fixes filed under RA4 whose notes describe a misprinted header
in other words counted under PP1; image-only tables moved from TL6 to TL10 by paper; rows drawn without a part the
label does not cover (TL6 less TL10's values, CU5 less the values with no organism, RA10's values kept only); and when
each paper was first read (log.tsv's add lines to the evidence's cut, asserted to give its 10,276 papers), measured
against the first rule version that did that kind of act (IP2's joins, PP6's values brought back and CU5's
verifier-unit part at a later change). Importing runs every one of those checks and draws nothing, so this list and
Fig. 4c cannot disagree. Nothing is typed by hand. The build stops when a drawn number is not the number of its file
(lean.same), and when two texts overlap or a text leaves the page. Shared drawing code: ../../lean.py (imported, not
edited; its page is 180 mm wide, this one 140 mm); `rich` below copies lean.rich with scripts held at 5 pt or more.

The table (rules_table.tsv, one row per kind of error, 87): what each kind is (rules.csv `kind`, the taxonomy's
example), whether it is a rule, a flag or open, Fig. 4a's layer (from checking databases against papers, or who first found it),
papers read when found and at the rule, the commit that first wrote it (for an open kind, the commit of its partial
guard, so marked) and the papers read at its later changes, its step (Fig. 1's Read, Convert, Verify, Check, or the
database check), what it guards, what it caught since the rule in other papers (rules.csv, in the kind's own unit), and
for the 16 listed here the papers drawn and those first read before the rule. It answers 'which 25 were known before
reading began' row by row.
"""
import csv
import io
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True               # lean.py lives outside this folder: leave no __pycache__ beside it
HERE = Path(__file__).resolve().parent        # writing/figures/extended_data/rules_reach
FIGS = HERE.parents[1]                        # writing/figures
ROOT = HERE.parents[3]                        # the CatLog folder
sys.path.insert(0, str(FIGS))
import lean  # noqa: E402
from lean import Page, same, INK, GRID  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter  # noqa: E402
from PIL import Image  # noqa: E402

W = 140.0                                     # page width, mm: lean's Page reads lean.W when it is built and placed
lean.W = W

# ================================================================================================= data
# Every count and label is Fig. 4's. Its build (writing/figures/fig4/v2/final/build_fig4_v2.py) holds the data code and
# all its checks. Its list of 16 (LEARNED) is this figure, and Fig. 4c draws eight of them. Imported, not copied, so the
# two figures cannot disagree; importing runs every check of that build and draws nothing.
sys.path.insert(0, str(FIGS / 'fig4' / 'v2' / 'final'))
import build_fig4_v2 as F4  # noqa: E402
RULES, REACH, NOW, since_rule, keep_row = F4.RULES, F4.REACH, F4.NOW, F4.since_rule, F4.keep_row
A_ROWS, SMALL, NOT_DRAWN, READ_BEFORE = F4.LEARNED, F4.SMALL, F4.NOT_LISTED, F4.READ_BEFORE
OUT, REFILED, RA4_HEADER, RA10_OUT = F4.OUT, F4.REFILED, F4.RA4_HEADER, F4.RA10_OUT
PP1_REFUSED, PP1_ONLY_REFUSED, CU5_ORG = F4.PP1_REFUSED, F4.PP1_ONLY_REFUSED, F4.CU5_ORG
FINDER = {k: F4.FINDER[k][:2] for k in F4.C_ORDER}        # name, colour: Fig. 4a's names, in its order from the top
EFFECT = F4.EFFECT                            # the two group heads
LABEL = F4.LABEL                              # Fig. 4's labels: c's eight rows read word for word as here
B_MARK = ' (Fig. 4b)'                         # the rule Fig. 4b follows (Fig. 4c marks it '(b)')
same('rules.csv: rules, flags and open kinds (note 6)', dict(Counter(k['status'] for k in RULES.values())),
     {'rule': 73, 'flag kept as printed': 4, 'open': 10})
same('papers per row, as drawn (Fig. 4c draws eight of them)', {k['id']: k['papers'] for k in A_ROWS},
     {'IP8': 139, 'PP1': 121, 'IP2': 68, 'IP6': 44, 'PP5': 39, 'RA8': 33, 'RA11': 25, 'RA3': 24, 'IP4': 21,
      'CU7': 10, 'RA10': 4204, 'PP6': 559, 'TL6': 214, 'TL10': 207, 'CU8': 137, 'CU5': 66})
# within a group, rows by finder (Fig. 4a's names from the top: code checks, checking agents, people with an agent,
# people), then by reach: the order of Fig. 4c
GROUPS = [sorted((k for k in A_ROWS if k['effect'] == e), key=lambda k: (F4.C_ORDER.index(k['who']), -k['papers']))
          for e in EFFECT]
same('rows per group', [len(g) for g in GROUPS], [10, 6])
same('rows by group, as they run',
     [[k['id'] for k in g] for g in GROUPS],
     [['PP1', 'IP2', 'PP5', 'RA3', 'IP4', 'IP8', 'RA8', 'RA11', 'IP6', 'CU7'],
      ['TL6', 'RA10', 'TL10', 'PP6', 'CU8', 'CU5']])
same("Fig. 4c's eight rows come in its order here", [k['id'] for g in GROUPS for k in g if k in F4.C_ROWS],
     [k['id'] for k in F4.C_ROWS])
same('read before the rule, the list (pairs)', (sum(len(READ_BEFORE[k['id']]) for k in A_ROWS),
                                               sum(len(REACH[k['id']]) for k in A_ROWS)), (2945, 5911))
same('flags on the list (so the title says rules and flags)', sorted(k['id'] for k in A_ROWS if k['flag']), ['PP5', 'PP6'])

# Note 7, the account of all 87 kinds in Fig. 4a's split: slipped digits (PP4) with the known, as Fig. 4a draws it
KNOWN_KINDS = [kid for kid, k in RULES.items() if k['first_found_by'] == 'known at the start'] + ['PP4']
FOUND = [kid for kid in RULES if kid not in KNOWN_KINDS]
WITH_COUNT = [k['id'] for k in A_ROWS] + [k['id'] for k in SMALL] + [kid for kid in NOT_DRAWN if kid != 'PP4']
same('note 7: kinds from checking databases against papers (with slipped digits), and the rules among them (Fig. 4a: 25)',
     (len(KNOWN_KINDS), sum(RULES[k]['status'] == 'rule' for k in KNOWN_KINDS)), (27, 25))
same('note 7: kinds first found while CatLog read, by status (rules, flags, open)',
     (len(FOUND), sum(RULES[k]['status'] == 'rule' for k in FOUND),
      sum(RULES[k]['status'] == 'flag kept as printed' for k in FOUND), sum(RULES[k]['status'] == 'open' for k in FOUND)),
     (60, 48, 3, 9))
same('note 7: of those 51 rules and flags, those with a count in other papers (the 16 here, 4 under ten papers, 5 not '
     'listed)', (len(WITH_COUNT), len(A_ROWS), len(SMALL), len(WITH_COUNT) - len(A_ROWS) - len(SMALL)), (25, 16, 4, 5))
same('note 7: every kind with a count is a rule or a flag found while reading',
     all(k in FOUND and RULES[k]['status'] != 'open' for k in WITH_COUNT), True)
same('the rules and flags not listed that acted on ten or more papers (texts rebuilt, papers read again, the supplement '
     'rule; slipped digits with the known)',
     sorted((kid, len(REACH[kid])) for kid in NOT_DRAWN), [('DB2', 291), ('PP4', 61), ('TL12', 292), ('TL9', 124),
                                                           ('X1', 2470), ('X2', 409)])
same('of them, the rules learned from errors (found while reading; slipped digits is with the known): five, all rules',
     sorted(kid for kid in NOT_DRAWN if kid in FOUND and RULES[kid]['status'] == 'rule'),
     ['DB2', 'TL12', 'TL9', 'X1', 'X2'])

# ================================================================================================= drawing
SIZE = 6.5                                     # every label, key, axis label and tick label (pt), as in Fig. 4
plt.rcParams.update({'axes.labelsize': SIZE, 'xtick.labelsize': SIZE, 'ytick.labelsize': SIZE})
SCRIPT = {'sup': 0.42, 'sub': -0.22}           # rise of a script, in ems of its line (as lean.rich)
KEY = F4.KEY                                   # the key's neutral grey (no finder)
FILLED, OPEN = F4.FILLED, F4.OPEN              # the dots' sizes (pt), Fig. 4c's
LINE_IN_SLOT, OPEN_DROP = F4.LINE_IN_SLOT, F4.OPEN_DROP      # a row's filled dot, and its open dot under it, Fig. 4c's
WORDS = []                                     # every line of words drawn, for the README's count
LINES = []                                     # every line's text artists, for the overlap check


def rich(pg, x, y, parts, size=SIZE, ha='left', weight='normal', color=INK):
    """One line set from runs (text, kind), its baseline at y mm: kind '' plain, 'i' italic, 'sup' raised, 'sub'
    lowered. lean.rich, with a script never under 5 pt (0.72 of its line otherwise) and the bold weight measured.
    Returns the line's ends, mm."""
    renderer = pg.fig.canvas.get_renderer()
    runs = []
    for text, kind in parts:
        fs = max(5.0, 0.72 * size) if kind in SCRIPT else size
        style = 'italic' if kind == 'i' else 'normal'
        prop = FontProperties(family='Arial', style=style, weight=weight, size=fs)
        width = renderer.get_text_width_height_descent(text, prop, ismath=False)[0] / pg.fig.dpi * 25.4
        runs.append((text, style, fs, SCRIPT.get(kind, 0.0) * size * 25.4 / 72, width))
    at = x - sum(r[-1] for r in runs) * {'left': 0.0, 'center': 0.5, 'right': 1.0}[ha]
    x0, drawn = at, []
    for text, style, fs, lift, width in runs:
        drawn.append(pg.fig.text(at / lean.W, 1 - (y - lift) / pg.h, text, fontsize=fs, fontstyle=style,
                                 fontweight=weight, color=color, va='baseline', ha='left'))
        at += width
    WORDS.append(''.join(t for t, _ in parts))
    LINES.append((''.join(t for t, _ in parts), drawn))
    return x0, at


def label(pg, x, y, parts, size=SIZE, **kw):
    """A line of text whose capitals are centred on y mm (a row's dot), set by `rich`."""
    if isinstance(parts, str):
        parts = [(parts, '')]
    return rich(pg, x, lean.baseline(y, size), parts, size=size, **kw)


def width_of(pg, parts, weight='normal'):
    """The width, in mm, of a line of runs, as `rich` sets it."""
    renderer = pg.fig.canvas.get_renderer()
    w = 0.0
    for text, kind in parts:
        fs = max(5.0, 0.72 * SIZE) if kind in SCRIPT else SIZE
        prop = FontProperties(family='Arial', style='italic' if kind == 'i' else 'normal', weight=weight, size=fs)
        w += renderer.get_text_width_height_descent(text, prop, ismath=False)[0] / pg.fig.dpi * 25.4
    return w


def dot(ax, x, y, colour, size, mew=0.9, z=3, hollow=False):
    """One mark: fill at alpha 0.6 over a white disc (no line shows through), edge opaque in the same colour; hollow:
    white inside."""
    ax.plot([x], [y], marker='o', markersize=size, markerfacecolor='white', markeredgecolor='none',
            linestyle='none', zorder=z, clip_on=False)
    ax.plot([x], [y], marker='o', markersize=size, markerfacecolor='white' if hollow else colour + '99',
            markeredgecolor=colour, markeredgewidth=mew, linestyle='none', zorder=z + 0.1, clip_on=False)


def row_label(k):
    return LABEL[k['id']] + ([(B_MARK, '')] if k['id'] == F4.B_RULE else [])


def rules_panel(pg, top, ax_r, rowh, head_space, gap):
    """The title, the finder key, the marks' key over the dot columns, and rows of rules in two groups stacked on one
    log axis, each group under its head; Fig. 4c's marks, in the finder's colour. No panel letter: the title, the key
    and the longest row label start at the page's 2 mm margin."""
    _, x = rich(pg, 2, lean.baseline(4, 6.8), [('Rules and flags learned from errors', '')], size=6.8, weight='bold')
    rich(pg, x + 0.9, lean.baseline(4, 6.8), [(f'({len(A_ROWS)} of those that acted on ten or more papers)', '')],
         size=6.8)                                      # as lean.title: the name bold, what it counts plain
    x = label(pg, 2, 9.6, 'Error found by')[1] + 1.6        # key: who found the error, Fig. 4a's names
    for who in FINDER:
        name, colour = FINDER[who]
        dot(pg.canvas(x, 8.1, 3, 3), 1.5, 1.5, colour, 4.6)
        x = label(pg, x + 2.9, 9.6, name)[1] + 2.6
    left_lab = 2 + max(width_of(pg, row_label(k)) for g in GROUPS for k in g)
    left_lab = max(left_lab, 2 + max(width_of(pg, [(name, '')], 'bold') for name in EFFECT.values()))
    ax_l = left_lab + 2.0
    # no marks' key: one filled dot per row, as Fig. 4c since the owner dropped the open dots (16 Nov, "yeah drop")
    # rows: within a group, `gap` mm between finders; `head_space` mm between the groups for the second head
    line_y, head_y, y = {}, [], 0.0
    for gi, kinds in enumerate(GROUPS):
        if gi:
            y += head_space
        head_y.append(top + y + LINE_IN_SLOT - F4.HEAD_ABOVE)
        prev = None
        for k in kinds:
            if prev is not None and k['who'] != prev:
                y += gap
            line_y[k['id']] = y + LINE_IN_SLOT
            y += rowh
            prev = k['who']
    ax = pg.box(ax_l, top, ax_r - ax_l, y)
    ax.set_xscale('log')
    ax.set_xlim(0.75, 10000)
    ax.xaxis.set_major_locator(FixedLocator([1, 10, 100, 1000, 10000]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{int(v):,}'))
    ax.xaxis.set_minor_locator(FixedLocator([m * 10 ** e for e in range(4) for m in range(2, 10)]))  # none below 1
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(y, 0)                           # data y = mm from the axes' top
    ax.set_yticks([])
    ax.grid(axis='x', color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_bounds(1, 10000)
    ax.tick_params(axis='x', pad=1.5)
    ax.set_xlabel('Papers the rule acted on', labelpad=2)      # Fig. 4c's axis
    span = math.log10(10000) - math.log10(0.75)

    def x_mm(n):
        return ax_l + (ax_r - ax_l) * (math.log10(n) - math.log10(0.75)) / span

    for name, hy in zip(EFFECT.values(), head_y):
        label(pg, left_lab, hy, name, ha='right', weight='bold')
    drawn, zeros = {}, []
    for k in (k for g in GROUPS for k in g):
        yc = line_y[k['id']]
        colour = FINDER[k['who']][1]
        n_all = len(REACH[k['id']])
        dot(ax, n_all, yc, colour, FILLED, mew=1.0)
        drawn[k['id']] = n_all
        label(pg, x_mm(n_all) + 1.5, top + yc, f'{n_all:,}')
        label(pg, left_lab, top + yc, row_label(k), ha='right')
        x0 = LINES[-1][1][0].get_position()[0] * lean.W      # where the label's first run starts, mm
        if x0 < 1.5:
            raise SystemExit(f'label of {k["id"]} runs off the page (starts at {x0:.1f} mm)')
    same('dots drawn per row (all papers the rule acted on)', drawn, {k['id']: len(REACH[k['id']]) for k in A_ROWS})
    return ax, top + y, left_lab, ax_l


def words(fig):
    """Words on the art, for the README: tokens with a letter in them (tick numbers and counts are not words), in
    every line drawn and the axis labels."""
    n = sum(sum(any(ch.isalpha() for ch in w) for w in s.split()) for s in WORDS)
    for ax in fig.axes:
        for lab in (ax.xaxis.label, ax.yaxis.label):
            n += sum(any(ch.isalpha() for ch in w) for w in lab.get_text().split())
    return n


def text_boxes(pg, ax):
    """Every text on the page as (what, x0, y0, x1, y1) in mm from the top left: each drawn line as one box, the axis
    label and the tick labels."""
    pg.fig.canvas.draw()
    fw, fh = pg.fig.bbox.width, pg.fig.bbox.height

    def mm(b):
        return b.x0 / fw * lean.W, (1 - b.y1 / fh) * pg.h, b.x1 / fw * lean.W, (1 - b.y0 / fh) * pg.h

    out = []
    for what, drawn in LINES:
        bs = [mm(t.get_window_extent()) for t in drawn if t.get_text().strip()]
        out.append((what, min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)))
    out.append((ax.xaxis.label.get_text(), *mm(ax.xaxis.label.get_window_extent())))
    for t in ax.get_xticklabels():
        if t.get_visible() and t.get_text().strip() and 0.75 <= t.get_position()[0] <= 10000:
            out.append((f'tick {t.get_text()}', *mm(t.get_window_extent())))
    return out


def check_texts(boxes, height, margin=1.0):
    """Stop the build when a text leaves the page (less than `margin` mm from an edge) or two texts overlap."""
    for what, x0, y0, x1, y1 in boxes:
        if x0 < margin or y0 < margin or x1 > W - margin or y1 > height - margin:
            raise SystemExit(f'{what!r} leaves the page: {x0:.1f}-{x1:.1f} x {y0:.1f}-{y1:.1f} mm')
    for i, (a, *p) in enumerate(boxes):
        for b, *q in boxes[i + 1:]:
            if p[0] < q[2] and q[0] < p[2] and p[1] < q[3] and q[1] < p[3]:
                raise SystemExit(f'{a!r} and {b!r} overlap')


H = 97.0                                       # page height, mm (102 until the marks' key left, 16 Nov)
TOP, AX_R, ROWH, HEAD_SPACE, GAP = 17.0, 130.0, 4.0, F4.HEAD_SPACE, F4.GAP   # rows' top; axis' right end (counts end
#                                                inside the page); row pitch, the second head, finders: Fig. 4c's


# ================================================================================================= the table
# The Supplementary Table: one row per kind of error (87), from rules.csv and taxonomy.tsv, with Fig. 4a's layer and,
# for the 16 listed here, the papers drawn and those first read before the rule. Read with any spreadsheet.
TAX = F4.TAX
LAYER = {kid: ('From checking databases against papers' if kid in KNOWN_KINDS else
               F4.FINDER[F4.finder(kid) if F4.finder(kid) in FINDER else 'known'][0]) for kid in RULES}
ROUTE = {'old system': 'checking database values against their papers', 'operator': 'the session in which an author runs CatLog '
         'with an agent', 'code check': 'a code check', 'sweep': 'a sweep code lists and agents check',
         'outside review': 'an outside review by agents', 'audit': 'an audit', 'verifier': 'the verifier',
         'database check': 'the database check', 'reviewer': 'a reviewer of records', 'owner': 'an author'}
WHAT = {'wrong value or label let in': 'a wrong value or label let in', 'right value refused or lost':
        'a right value refused or lost', 'process failure': 'the process (no value)'}
HELD_OUT = {ln.strip() for ln in open(ROOT / 'sources/holdout_locked.txt', encoding='utf-8') if ln.strip()}
TABLE_COLUMNS = ['id', 'kind of error', 'example (from CatLog\'s records)', 'status', 'Fig. 4a layer', 'first found in',
                 'papers read when found', 'papers read at the rule', 'rule commit', 'papers read at later changes',
                 'step', 'what it guards against', 'caught since the rule, other papers', 'unit',
                 'papers, other papers', 'on the Extended Data list', 'papers drawn (Extended Data)',
                 'of them first read before the rule']
LISTED = {k['id']: k for k in A_ROWS}
PARTIAL = ' (partial guard, not a rule)'       # an open kind's commit: it guards part of the kind (taxonomy.tsv `guard`
#                                                names what is still open), so it is no rule


def commit_of(k):
    """The rule commit as the table writes it: an open kind's is marked as a partial guard."""
    return k['rule_commit'] + PARTIAL if k['status'] == 'open' and k['rule_commit'] else k['rule_commit']


# One CatLog (BRIEF.md): four of the taxonomy's examples say 'the old catalogue' or 'the old system'; the table says
# 'CatLog once', the same fact without an earlier and a newer CatLog
OLD_CATLOG = re.compile(r'\bthe old (?:catalogue|catalog|system)\b')
# DB2's example as the Methods count it: 302 papers whose reader or verifier opened such files, and 4 more that only a
# completeness audit exposed, which the taxonomy's 306 counted among the readers' and verifiers' (final read, 17 Nov 2026)
EXAMPLE_FIX = {'DB2': ('306 papers whose reader or verifier opened database values before the rule',
                       '302 papers whose reader or verifier opened database values or other catalogue files before the '
                       'rule')}


def table_rows():
    rows = []
    for kid, k in RULES.items():
        listed = kid in LISTED
        example = OLD_CATLOG.sub('CatLog once', TAX[kid]['example']) if kid in TAX else ''
        if kid in EXAMPLE_FIX:
            assert EXAMPLE_FIX[kid][0] in example, f'{kid}: its taxonomy example changed, so EXAMPLE_FIX needs a look'
            example = example.replace(*EXAMPLE_FIX[kid])
        rows.append({
            'id': kid, 'kind of error': k['kind'], "example (from CatLog's records)": example,
            'status': k['status'], 'Fig. 4a layer': LAYER[kid] if k['status'] == 'rule' else
            ('' if k['status'] == 'open' else f"flag; {LAYER[kid]}"),
            'first found in': ROUTE[k['first_found_route']], 'papers read when found': k['papers_read_when_found'],
            'papers read at the rule': k['papers_read_at_rule'], 'rule commit': commit_of(k),
            'papers read at later changes': k['papers_read_at_later_changes'], 'step': k['rule_step'],
            'what it guards against': WHAT[k['effect']],
            'caught since the rule, other papers': k['caught_since_rule_other_papers'], 'unit': k['unit'],
            'papers, other papers': k['papers_since_rule_other_papers'],
            'on the Extended Data list': 'yes' if listed else '',
            'papers drawn (Extended Data)': len(REACH[kid]) if listed else '',
            'of them first read before the rule': len(READ_BEFORE[kid]) if listed else ''})
    return rows


TABLE = table_rows()
same('table: rows, and the rules by Fig. 4a layer', (len(TABLE), dict(Counter(r['Fig. 4a layer'] for r in TABLE
                                                                               if r['status'] == 'rule'))),
     (87, {'From checking databases against papers': 25, 'People': 5, 'People with an agent': 21, 'Checking agents': 13,
           'Code checks': 9}))
same("table: each rule's Fig. 4a layer, as Fig. 4's build stacks it (rules_by_papers.csv groups; the two found after "
     "the list by route)",
     {r['id']: r['Fig. 4a layer'] for r in TABLE if r['status'] == 'rule'},
     {**{r['id']: F4.FINDER[F4.a_group(r)][0] for r in F4.LRULES},
      **{k['id']: F4.FINDER[F4.GROUP[k['first_found_route']]][0] for k in F4.LATER}})
same('table: one CatLog in the examples (no old catalogue or system)',
     [r['id'] for r in TABLE if re.search(r'\bold (?:catalogue|catalog|system)\b', r["example (from CatLog's records)"])], [])
same('table: no example names a held-out paper',
     [r['id'] for r in TABLE if any(p in HELD_OUT for p in r["example (from CatLog's records)"].replace(';', ' ')
                                    .replace(':', ' ').replace(',', ' ').split())], [])
same("table: open kinds with a commit, each marked a partial guard; the guard's own words name what is still open",
     {r['id']: (r['rule commit'].endswith(PARTIAL), 'OPEN' in TAX[r['id']]['guard'])
      for r in TABLE if r['status'] == 'open' and r['rule commit']},
     {'IP3': (True, True), 'RA7': (True, True), 'PR14': (True, True)})
same('table: the listed rows carry the drawn counts', {r['id']: (r['papers drawn (Extended Data)'],
                                                                r['of them first read before the rule'])
                                                       for r in TABLE if r['on the Extended Data list']},
     {k['id']: (len(REACH[k['id']]), len(READ_BEFORE[k['id']])) for k in A_ROWS})


def write_table(path=HERE / 'rules_table.tsv'):
    order = {s: i for i, s in enumerate(('rule', 'flag kept as printed', 'open'))}
    layer = {n: i for i, n in enumerate(['From checking databases against papers'] + [FINDER[w][0] for w in FINDER])}
    rows = sorted(TABLE, key=lambda r: (order[r['status']], layer.get(r['Fig. 4a layer'].replace('flag; ', ''), 9),
                                        int(r['papers read at the rule'] or 10 ** 6), r['id']))
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=TABLE_COLUMNS, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    print('wrote', path, f'({len(rows)} kinds of error: {dict(Counter(r["status"] for r in rows))})')


def build(out=HERE / 'rules_reach.png'):
    WORDS.clear()
    LINES.clear()
    pg = Page(H, HERE, HERE)
    ax, axis_at, left_lab, ax_l = rules_panel(pg, top=TOP, ax_r=AX_R, rowh=ROWH, head_space=HEAD_SPACE, gap=GAP)
    boxes = text_boxes(pg, ax)
    check_texts(boxes, H)
    buf = io.BytesIO()
    pg.fig.savefig(buf, dpi=lean.DPI, facecolor='white', format='png')
    Image.open(buf).convert('RGB').save(out, dpi=(lean.DPI, lean.DPI))
    label_words = sum(sum(any(ch.isalpha() for ch in w) for w in ''.join(t for t, _ in row_label(k)).split())
                      for k in A_ROWS)
    print('wrote', out, f'({W:.0f} x {H:.0f} mm; labels end at {left_lab:.1f} mm, axis {ax_l:.1f} to {AX_R:.1f} mm,'
                        f' its line at {axis_at:.1f} mm; texts from {min(b[1] for b in boxes):.1f} to'
                        f' {max(b[3] for b in boxes):.1f} mm across and {min(b[2] for b in boxes):.1f} to'
                        f' {max(b[4] for b in boxes):.1f} mm down; {words(pg.fig)} words, {label_words} of them the'
                        f' rule labels)')
    plt.close(pg.fig)
    write_table()


def report():
    """Every drawn number, from the files, for the README (python3 -I -B build.py --report)."""
    print('rows (group | kind | label | found by [route] | papers the rule acted on (first read before the rule, at) |'
          ' amounts by unit | rules.csv if it differs)')
    for name, kinds in zip(EFFECT.values(), GROUPS):
        for k in kinds:
            r = RULES[k['id']]
            units = defaultdict(int)
            for c in since_rule(k['id']):
                if keep_row(k['id'], c) and c['pmid'] in REACH[k['id']]:
                    units[c['unit']] += int(c['amount'])
            if k['id'] in ('TL6', 'TL10'):    # Fig. 4's build moves image-only tables from TL6 to TL10 by paper
                units = {'values': sum(REACH[k['id']].values())}
            orig = (int(r['papers_since_rule_other_papers']), int(r['caught_since_rule_other_papers']))
            at = {'CU5': '12 and 6,839', 'PP6': '12 (noted) and 893 (brought back)'}.get(k['id'], f"{F4.act_at(k['id']):,}")
            print(f"  {name} | {k['id']} | {''.join(t for t, _ in row_label(k))} | {FINDER[k['who']][0]}"
                  f" [{r['first_found_route']}] | {k['papers']:,} ({len(READ_BEFORE[k['id']]):,}, {at}) | "
                  + ', '.join(f'{v:,} {u}' for u, v in sorted(units.items()))
                  + ('' if (k['papers'], sum(units.values())) == orig and len(units) == 1
                     else f" | rules.csv {orig[0]:,} papers, {orig[1]:,} {r['unit']}") + (' | flag' if k['flag'] else ''))
    print('dots by who found:', dict(sorted(Counter(FINDER[k['who']][0] for k in A_ROWS).items())))
    print(f'first read before the rule: {sum(len(READ_BEFORE[k["id"]]) for k in A_ROWS):,} of'
          f' {sum(len(REACH[k["id"]]) for k in A_ROWS):,} row-paper pairs')
    print('not drawn, under ten papers:',
          ', '.join(f"{k['id']} {k['papers']} ({sum(REACH[k['id']].values())} {RULES[k['id']]['unit']})"
                    for k in sorted(SMALL, key=lambda k: -k['papers'])))
    for kid, why in NOT_DRAWN.items():
        r = RULES[kid]
        print(f"not drawn {kid} ({r['first_found_by']}; {r['papers_since_rule_other_papers']} papers,"
              f" {r['caught_since_rule_other_papers']} {r['unit']}): {why}")
    print(f'note 7: known kinds {len(KNOWN_KINDS)} (rules {sum(RULES[k]["status"] == "rule" for k in KNOWN_KINDS)});'
          f' found while reading {len(FOUND)}; with a count {len(WITH_COUNT)}')
    for kid, named in OUT.items():
        for p, (amount, why) in named.items():
            print(f'{kid} left out {p} ({amount}): {why}')
    for r in REFILED:
        print(f"PP1 counts RA4's line of {r['pmid']} ({r['amount']} value{'' if r['amount'] == '1' else 's'},"
              f" first at {int(r['papers_read_at_first']):,},"
              f" {'since' if r['since_rule'] == 'yes' else 'before'} the rule): {RA4_HEADER[r['pmid']][1]}")
    print(f'PP1 values refused, not corrected: {sum(PP1_REFUSED.values())} values in {len(PP1_REFUSED)} papers',
          dict(PP1_REFUSED), '; papers only refused', PP1_ONLY_REFUSED)
    print(f'RA10 refusals left out: {len(RA10_OUT)} papers, {sum(RA10_OUT.values())} values')
    print(f'CU5 values with no organism, left out: {len(CU5_ORG)} papers, {sum(CU5_ORG.values()):,} values')
    print(f'rules.csv: {dict(Counter(k["status"] for k in RULES.values()))}; papers read now {NOW:,}')
    print('table rows by status and layer:', sorted(Counter((r['status'], r['Fig. 4a layer']) for r in TABLE).items()))


if __name__ == '__main__':
    if '--report' in sys.argv:
        report()
    else:
        build(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'rules_reach.png')
