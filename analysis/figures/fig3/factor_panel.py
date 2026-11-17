"""The panel on database numbers that differ from CatLog's, for Fig. 3: the approved figure of 30 October 2026
(paper/figures/database_errors/build_figure.py, a hand-built SVG that the owner approved) drawn again as a panel, with
the same bins, colours, order of stacking, spike labels and key. Only the axis labels and the key start with a
capital, like the other panels of Fig. 3.

Data: paper/figures/database_errors/factor_counts.json (read only; written by factor_counts.py beside it from
sources/database_corrections.tsv and the checks' files at the paper freeze: tag paper-catalog-freeze-20261116,
16 November 2026 13:03). One point per checked database number: the database's number over CatLog's value for the same
paper and constant, and the agent's verdict. Bars: papers per bin of the ratio (bins of 0.02 in log10, so every power
of ten is the middle of a bin); a paper counts once per bin and verdict.
"""
import collections
import json
import math
from pathlib import Path

from matplotlib.font_manager import FontProperties

ROOT = Path(__file__).resolve().parents[3]
FILE = 'paper/figures/database_errors/factor_counts.json'
DATA = json.loads((ROOT / FILE).read_text())
POINTS = DATA['points']
KINDS = [  # (verdict in factor_counts.json, the key's label, colour), bottom of the stack first: as approved
    ('database misread the paper', 'Database misread', '#3C5488'),
    ("database copied the paper's own misprint", 'Database copied a misprint', '#4DBBD5'),
    ('both right, different measurements', 'Both right, different records', '#B09C85'),
    ('the paper does not decide', 'Paper does not decide', '#C8C8C8'),
    ('CatLog was wrong', 'CatLog wrong', '#E64B35'),
]
ORDER = [k for k, _, _ in KINDS]
BIN, LO, HI, YMAX = 0.02, -12.61, 6.61, 120
SPIKES = [  # (log10 of the factor, head, lines of what went wrong, where the label sits): as approved. A part is
    # (text, raised): raised parts are exponents, set small and lifted, since Arial has no superscript minus
    (3, [('×1000', 0)], [[('concentration', 0)], [('units mixed up', 0)]], 'mid'),
    (-3, [('×1/1000', 0)], [[('concentration', 0)], [('units mixed up', 0)]], 'mid'),
    (1, [('×10', 0)], [[('decimal point', 0)], [('or exponent slipped', 0)]], 'mid'),
    (-1, [('×1/10', 0)], [[('decimal point', 0)], [('or exponent slipped', 0)]], 'mid'),
    (math.log10(60), [('×60', 0)], [[('min', 0), ('−1', 1)], [('taken as s', 0), ('−1', 1)]], 'mid'),
    (-12, [('×10', 0), ('−12', 1)], [[("a header's power of ten applied backwards", 0)]], 'right'),
]


def same(what, a, b):
    if a != b:
        raise SystemExit(f'database numbers panel: {what}: {a!r} != {b!r}')


# The counts of this panel at the paper freeze (tag paper-catalog-freeze-20261116, 16 November 2026 13:03), for the
# Results' paragraph on it (writing/manuscript/results.md, which still gives the counts of 30 October until refreshed)
NUMBERS, PAPERS, ON_FACTOR = len(POINTS), len({p['pmid'] for p in POINTS}), DATA['on_a_unit_factor']
VERDICTS = collections.Counter(p['kind'] for p in POINTS)
same('numbers that agents decided', (NUMBERS, DATA['database_values']), (3113, 3113))
same('papers', (PAPERS, DATA['papers']), (889, 889))
same('numbers on a unit factor', ON_FACTOR, 2196)
same('verdicts, the file\'s own count', dict(VERDICTS), DATA['kinds'])
same('verdicts', [VERDICTS[k] for k in ORDER], [2445, 264, 306, 84, 14])
same('every ratio is inside the axis', all(LO <= p['log10_ratio'] < HI for p in POINTS), True)

_cell = collections.defaultdict(set)                 # (bin, verdict) -> papers
for p in POINTS:
    _cell[(math.floor((p['log10_ratio'] - LO) / BIN), p['kind'])].add(p['pmid'])
STACK = collections.defaultdict(list)
for (b, k), papers in _cell.items():
    STACK[b].append((k, len(papers)))
for b in STACK:
    STACK[b].sort(key=lambda kn: ORDER.index(kn[0]))
TOP = {b: sum(n for _, n in parts) for b, parts in STACK.items()}
same('the tallest bar fits the axis', max(TOP.values()) < YMAX, True)
bin_of = lambda v: math.floor((v - LO) / BIN)
centre = lambda b: LO + (b + 0.5) * BIN


def draw(ax, ink='#222222'):
    """The panel into ax (x in log10 of the ratio, y in papers)."""
    colour = {k: c for k, _, c in KINDS}
    for b, parts in sorted(STACK.items()):
        bottom = 0
        for k, n in parts:
            ax.bar(centre(b), n, width=BIN, bottom=bottom, color=colour[k], linewidth=0, zorder=2)
            bottom += n
    ax.set_xlim(LO, HI)
    ax.set_ylim(0, YMAX)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel('Papers', labelpad=2)
    labelled = {-12: r'$10^{-12}$', -9: r'$10^{-9}$', -6: r'$10^{-6}$', -3: '1/1000', -1: '1/10', 0: '1', 1: '10',
                math.log10(60): '60', 3: '1000', 6: r'$10^{6}$'}
    ax.set_xticks(list(labelled))
    ax.set_xticklabels(list(labelled.values()))
    ax.set_xticks([e for e in range(-12, 7) if e not in labelled], minor=True)     # a small tick at every power of ten
    ax.tick_params(axis='both', pad=1.5)
    ax.set_xlabel('Database value ÷ CatLog value', labelpad=2)
    renderer = ax.figure.canvas.get_renderer()

    def rich(xy, dx, dy, parts, size, weight, middle):
        """One line of text from (text, raised) parts, dx and dy in points from xy; centred on dx where `middle`."""
        runs = []
        for text, raised in parts:
            fs = 5.0 if raised else size
            prop = FontProperties(family='Arial', weight=weight, size=fs)
            runs.append((text, fs, size * 0.38 if raised else 0.0,
                         renderer.get_text_width_height_descent(text, prop, ismath=False)[0] * 72 / ax.figure.dpi))
        at = dx - sum(w for *_, w in runs) / 2 if middle else dx
        for text, fs, lift, w in runs:
            ax.annotate(text, xy, xytext=(at, dy + lift), textcoords='offset points', ha='left', va='baseline', fontsize=fs,
                        fontweight=weight, color=ink)
            at += w

    for v, head, lines, side in SPIKES:
        b = bin_of(v)
        xy, middle, dx = (centre(b), TOP.get(b, 0)), side == 'mid', 0 if side == 'mid' else 2.5
        up = 2.0 + 6.6 * len(lines)                   # points above the bar: the lines, then the head
        rich(xy, dx, up + 1.0, head, 7, 'bold', middle)
        for i, parts in enumerate(lines):
            rich(xy, dx, up - 6.6 * (i + 1) + 1.2, parts, 6, 'normal', middle)
    for i, (_, label, c) in enumerate(KINDS):         # the key, from the left edge of the x10^-12 label
        at = (centre(bin_of(-12)), YMAX)
        ax.annotate('■', at, xytext=(2.5, -6.5 - 8.2 * i), textcoords='offset points', fontsize=7, color=c, va='baseline')
        ax.annotate(label, at, xytext=(10.5, -6.5 - 8.2 * i), textcoords='offset points', fontsize=6, color=ink, va='baseline')
