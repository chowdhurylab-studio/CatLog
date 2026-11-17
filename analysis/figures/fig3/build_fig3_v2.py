"""Fig. 3, more than the databases hold: version B (the owner's pick, 15 November 2026) in more of his palette.

One build, three colour codes (README.md, "Colour"):
  1  fig3.png: the enzyme class in a, b and e, in palette colours other than red and green; green means the paper and
     CatLog alone wherever it appears (c, d, f), red only g's 'CatLog wrong';
  0  the first v2: the website's class colours (oxidoreductases red, hydrolases green);
  2  no classes: a and e coloured, like f, by where a record's values stand against the six databases; b one area.
Nothing on the art beyond panel titles, row labels, axis labels, two small keys and the names of a's four outlines; the
legend notes are in README.md.
Text: 6.5 pt (labels, keys, ticks), 7 pt bold (titles, g's spike heads), 8 pt bold (letters), 6 pt along a's lines;
exponents and subscripts 5 pt.

Data, all from ONE export (the paper freeze's catlog_wide.jsonl, written 2026-11-16 12:52:17; tag
paper-catalog-freeze-20261116, 16 November 2026 13:03; read only), in data/ here:
  data/snapshot.json, data/kcat_km.csv.gz   python3 -I -B writing/figures/fig3/extract.py --out writing/figures/fig3/v2/data
  data/classes.json, data/kcat_km_class.csv.gz   python3 -I -B writing/figures/fig3/v2/extract_classes.py
and, for g, paper/figures/database_errors/factor_counts.json (the agents' checks at the paper freeze, read through
../factor_panel.py, whose bins, stacking order, colours and spike labels g keeps; g is drawn here in this figure's sizes).

Run:  python3 -I -B writing/figures/fig3/v2/build_fig3_v2.py               fig3.png (code 1)
      ... --choices [DIR]   also fig3_colour_choices.png (codes 0, 1, 2) and fig3_a_choices.png (a's dots three ways);
                            the single renders go to DIR when one is given
      ... --numbers         every drawn number, for README.md
"""
import json
import math
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DATA = HERE / 'data'
sys.path[:0] = [str(HERE.parent), str(HERE.parents[1])]   # fig3_panels.py, factor_panel.py; lean.py (python -I leaves folders out)
import csv  # noqa: E402
import gzip  # noqa: E402
import numpy as np  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402
from matplotlib.collections import PathCollection  # noqa: E402
from matplotlib.colors import to_rgba  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402
from matplotlib.text import Annotation  # noqa: E402
from lean import BLUE, BROWN, GREEN, GRID, INK, MINT, NAVY, PALE, RED, SLATE, TAN, W, Page, row_y, same  # noqa: E402
import fig3_panels  # noqa: E402
from fig3_panels import kcat_km_axes, kcat_km_draw  # noqa: E402
import factor_panel  # noqa: E402

# ---------------------------------------------------------------------------------------------------------------
# Type: few sizes (points)
PT = 25.4 / 72                      # mm per point
TEXT, TITLE, LETTER, ALONG, SMALL = 6.5, 7.0, 8.0, 6.0, 5.0
RISE, DROP = 0.40, 0.22             # a raised or lowered run moves by this many ems of the text it sits in
TICK_GAP = 3.5                      # points from an axis line to the top of its tick labels (tick 2 + pad 1.5)

# ---------------------------------------------------------------------------------------------------------------
# Colour (README.md, "Colour"). Fills at alpha 0.6, lines and text opaque; a's dots and g's bars are the exceptions.
SALMON = '#F39B7F'
GREY = '#BDBDBD'          # no EC number
CLOUD, CLOUD_ALPHA = '#A3A3A3', 0.30   # a's dots under the class outlines: every record, a grey darker than GREY's key square
CASING = [pe.Stroke(linewidth=1.8, foreground='white', alpha=0.85), pe.Normal()]   # a white edge round a's outlines
BAND = '#ECEDEC'          # the diffusion limit in a, grey as on the website's landing figure (kmplane.py BAND_GREY)
LINE_GREY = '#ABABAB'     # a's lines of equal kcat/Km: ink at 0.38 on white, drawn opaque
JOIN_GREY = '#909090'     # c's EC-number line: ink at 0.5 on white, drawn opaque
CLASSES = ['1', '2', '3', '4', '5', '6', '7', 'none']
CLASS_NAME = {'1': 'Oxidoreductases', '2': 'Transferases', '3': 'Hydrolases', '4': 'Lyases', '5': 'Isomerases', '6': 'Ligases',
              '7': 'Translocases', 'none': 'No EC number'}
CLASS_COLOUR = {
    0: {'1': RED, '2': BLUE, '3': GREEN, '4': NAVY, '5': SALMON, '6': SLATE, '7': BROWN, 'none': GREY},   # the website's
    1: {'1': SALMON, '2': BLUE, '3': BROWN, '4': NAVY, '5': TAN, '6': SLATE, '7': MINT, 'none': GREY},    # no red, no green
}
STATUSES = ['same', 'other', 'different', 'none', 'not_compared']          # the order of f's strip
STATUS_NAME = {'same': 'Same number', 'other': 'Same number, other name', 'different': 'Different number',
               'none': 'In no database', 'not_compared': 'Not compared'}
STATUS_COLOUR = {'same': NAVY, 'other': SLATE, 'different': BROWN, 'none': GREEN, 'not_compared': PALE}   # f's, as in B


class Code:
    """One colour code of the figure."""

    def __init__(self, n):
        self.n = n
        if n in (0, 1):
            self.by, self.groups, self.name, self.colour = 'class', CLASSES, CLASS_NAME, CLASS_COLOUR[n]
            self.first, self.large, self.small = ['none'], ['1', '2', '3'], ['4', '5', '6', '7']   # a's drawing order
            self.key = [['1', '2', '3'], ['4', '5', '6'], ['7', 'none']]
        else:
            self.by, self.groups, self.name, self.colour = 'status', STATUSES, STATUS_NAME, STATUS_COLOUR
            self.first, self.large, self.small = ['not_compared'], ['same', 'none'], ['other', 'different']
            self.key = [['same', 'different'], ['other'], ['none', 'not_compared']]
        # c and d: green is the paper's; in 0 what code links is navy and a constant printed only as a bound is mint
        self.linked = (NAVY, False) if n == 0 else (GREEN, True)        # (colour, open)
        self.bound = (MINT, False) if n == 0 else (GREEN, False)   # d: all three printed, so filled (15 Nov recount)
        self.linked_word = 'Linked' if n == 0 else 'Linked by code'


# ---------------------------------------------------------------------------------------------------------------
# Data
SNAP = json.loads((DATA / 'snapshot.json').read_text())
CLS = json.loads((DATA / 'classes.json').read_text())
EXPORT, REC, C, BOUNDS = SNAP['export'], SNAP['records'], SNAP['c'], SNAP['bounds']['by_constant_and_kind']
RECORDS, VALUES = EXPORT['records'], EXPORT['values']
same('classes.json and snapshot.json: one export', {k: CLS['export'][k] for k in ('size', 'written', 'sha256', 'records', 'values')},
     {k: EXPORT[k] for k in ('size', 'written', 'sha256', 'records', 'values')})

with gzip.open(DATA / 'kcat_km_class.csv.gz', 'rt') as fh:
    _rows = list(csv.reader(fh))
same('a: the columns of kcat_km_class.csv.gz', _rows[0], ['kcat_per_s', 'km_mM', 'ec_class', 'db_status'])
KCAT = np.array([float(r[0]) for r in _rows[1:]])
KM = np.array([float(r[1]) for r in _rows[1:]])
GROUP = {'class': np.array([r[2] for r in _rows[1:]]), 'status': np.array([r[3] for r in _rows[1:]])}
with gzip.open(DATA / 'kcat_km.csv.gz', 'rt') as fh:
    same('a: the records of both extracts, in one order', [(float(a), float(b)) for a, b in list(csv.reader(fh))[1:]],
         list(zip(KCAT.tolist(), KM.tolist())))
same('a: records with kcat and Km', len(KCAT), SNAP['a']['records_with_kcat_and_km'])
same('a: the classes of those records', {c: int(np.sum(GROUP['class'] == c)) for c in CLASSES}, CLS['kcat_km_records_by_class'])
same('a: their database status', {s: int(np.sum(GROUP['status'] == s)) for s in STATUSES}, CLS['kcat_km_records_by_status'])
same('records by class, the two extracts', {c: CLS['records_by_class'][c] for c in CLASSES},
     {c: REC['by_enzyme_class'][f'{c}|wild_type'] + REC['by_enzyme_class'][f'{c}|variant'] for c in CLASSES})
same('records by status add up to the records', sum(CLS['records_by_status'].values()), RECORDS)

BY_YEAR = {int(y): d for y, d in CLS['values_by_year_and_class'].items()}
same('b: the years, the two extracts', sorted(BY_YEAR), sorted(int(y) for y in SNAP['b']['values_by_year']))
for _y, _d in BY_YEAR.items():
    same(f'b: {_y}, the classes add up to the year', sum(_d.values()), SNAP['b']['values_by_year'][str(_y)])
same('b: no value without a year', SNAP['b']['values_without_year'], 0)
YEARS = list(range(min(BY_YEAR), max(BY_YEAR) + 1))
LAYERS = {c: np.array([BY_YEAR.get(y, {}).get(c, 0) for y in YEARS]) for c in CLASSES}
TOTAL = sum(LAYERS.values())
same('b: every value is drawn', int(TOTAL.sum()), VALUES)

CARRIES = REC['carries']
ECF = CLS['ec_number_from']
same('c: EC numbers by origin add up to the records with one', ECF['paper'] + ECF['uniprot'] + ECF['databases'], CARRIES['ec_number'])
same('c: and with the records without one, to every record', sum(ECF.values()), RECORDS)
# (row, key, where it comes from): the organism, pH, temperature, printed line and printed ± are the paper's; the
# substrate structure, UniProt entry and sequence are linked by code; the EC number is the paper's where it prints one
HAS = [('Printed line', 'printed_line', 'printed'), ('Organism', 'organism', 'printed'), ('Substrate structure', 'substrate_structure', 'linked'),
       ('pH', 'ph', 'printed'), ('EC number', 'ec_number', 'both'), ('Temperature', 'temperature', 'printed'),
       ('Printed ±', 'printed_uncertainty', 'printed'), ('UniProt entry', 'uniprot_entry', 'linked'), ('Sequence', 'sequence', 'linked')]
HAS.sort(key=lambda t: -CARRIES[t[1]])
same('every record has its printed line', CARRIES['printed_line'], RECORDS)

same('d: values by constant add up', sum(EXPORT['values_by_metric'].values()), VALUES)
same('d: the constants and kinds', sorted(BOUNDS), sorted(f'{m}|{k}' for m in ('kcat', 'Km', 'kcat/Km') for k in ('limit', 'not_detected')))
PRINTED_AS = [('A number', VALUES), ('Not detected', sum(n for k, n in BOUNDS.items() if k.endswith('|not_detected'))),
              ('A limit', sum(n for k, n in BOUNDS.items() if k.endswith('|limit')))]

# e: the six species with the most records, every spelling of a species counted under it (extract_classes.binomial)
ORGANISMS = CLS['organisms_by_class'][:6]
ORG_STATUS = dict((o, d) for o, d in CLS['organisms_by_status'])
same('e: the spellings as written, the two extracts', CLS['organisms_as_written'][:6], [[o, n] for o, n, _ in REC['top_organisms'][:6]])
for _o, _d in ORGANISMS:
    _sp = CLS['organism_spellings'][_o]
    same(f'e: {_o!r} is a genus and a species', len(_o.split()), 2)
    same(f'e: {_o!r}, its spellings add up', sum(_sp.values()), sum(_d.values()))
    same(f'e: {_o!r}, by class and by status', sum(_d.values()), sum(ORG_STATUS[_o].values()))
    same(f'e: {_o!r} as written, the two extracts', _sp.get(_o), dict((o, n) for o, n, _ in REC['top_organisms']).get(_o))

LISTED = [('Same number', C['same_number']), ('Same, other name', C['same_number_other_label']),
          ('Different number', C['different_number']), ('Value not listed', C['none_paper_listed_without_this_value']),
          ('Paper not listed', C['none_paper_in_no_database'])]
same('f: the categories add up to every value', sum(n for _, n in LISTED) + C['not_compared'], VALUES)

# g: the approved panel's data, read through factor_panel (which asserts the approved counts)
NUMBERS, PAPERS = factor_panel.NUMBERS, factor_panel.PAPERS

# ---------------------------------------------------------------------------------------------------------------
# Layout, in mm on a page 180 mm wide
Y_T = 4.4                                  # the first row of titles
TOP = 9.4                                  # a's frame and b's box
A_L, DEC = 17.0, 7.5                       # a: left edge of the frame; mm per decade, the same on both axes
(KCAT0, KCAT1), (KM0, KM1), BEYOND = kcat_km_axes(KCAT, KM)
A_W, A_H = (KM1 - KM0) * DEC, (KCAT1 - KCAT0) * DEC
RX = A_L + A_W + 8.5                       # the right column's left edge
B_H = 17.0
SUB = 45.5                                 # c's width; d and e take the rest of the right column
RIGHT = W - 4.0
ROW_D, ROW_E = 3.5, 3.4                    # row pitches of d and e
KEY_X, KEY_Y, KEY_PITCH, KEY_SQ = 2.0, 1.7, 2.75, 1.5   # b's key: first mark, first row, row pitch, mark size (mm)
CD_TOP = TOP + B_H + 14.0                  # the first rows of c and d
D_END = CD_TOP + len(PRINTED_AS) * ROW_D
E_TOP = D_END + 14.5
E_END = E_TOP + len(ORGANISMS) * ROW_E
ROW_END = max(TOP + A_H + 7.6, E_END + 7.6)
F_TOP = ROW_END + 10.0                     # the strip
G_TOP = F_TOP + 4.0 + 6.2 + 10.6           # g's frame
G_H = 37.0
HEIGHT = G_TOP + G_H + 8.8
same('the figure is at most 170 mm tall', HEIGHT <= 170.0, True)


# ---------------------------------------------------------------------------------------------------------------
# Text set from runs, so that exponents and subscripts are 5 pt: a run is (text, size, style, weight, rise in points)
def run(text, size=TEXT, italic=False, bold=False, rise=0.0):
    return (text, size, 'italic' if italic else 'normal', 'bold' if bold else 'normal', rise)


def sup(text, base=TEXT, bold=False):
    return run(text, SMALL, bold=bold, rise=RISE * base)


def sub(text, base=TEXT, bold=False):
    return run(text, SMALL, bold=bold, rise=-DROP * base)


def power(e, base=TEXT):
    return [run('10', base), sup(str(e).replace('-', '−'), base)]


def width(fig, text, size=TEXT, style='normal', weight='normal'):
    """The width of a run in mm."""
    prop = FontProperties(family='Arial', style=style, weight=weight, size=size)
    return fig.canvas.get_renderer().get_text_width_height_descent(text, prop, ismath=False)[0] / fig.dpi * 25.4


def runs(page, x, y, parts, ha='left', rotation=0, color=INK):
    """One line set from runs, its baseline at y (mm from the page's top); rotation 90 reads upwards from y. The width."""
    fig = page.fig
    widths = [width(fig, t, s, st, wt) for t, s, st, wt, _ in parts]
    total = sum(widths)
    shift = {'left': 0.0, 'center': 0.5, 'right': 1.0}[ha] * total
    at = x - shift if rotation == 0 else y + shift
    for (t, s, st, wt, rise), w in zip(parts, widths):
        px, py = (at, y - rise * PT) if rotation == 0 else (x - rise * PT, at)
        fig.text(px / W, 1 - py / page.h, t, fontsize=s, fontstyle=st, fontweight=wt, color=color, va='baseline',
                 ha='left', rotation=rotation, rotation_mode='anchor')
        at = at + w if rotation == 0 else at - w
    return total


def caps(y, size=TEXT):
    """The baseline for a line whose capitals are centred at y."""
    return y + 0.358 * size * PT


def title(page, letter, x, y, name, rest=''):
    """A panel's letter (8 pt bold) and name (7 pt bold, what it counts in plain weight), on one baseline."""
    base = caps(y, TITLE)
    runs(page, x, base, [run(letter, LETTER, bold=True)])
    parts = name if isinstance(name, list) else [run(name, TITLE, bold=True)]
    runs(page, x + 4.5, base, parts + ([run(' ' + rest, TITLE)] if rest else []))


def tick_base(parts):
    """mm from an axis line down to the baseline of its tick labels: the top of the highest run TICK_GAP below the axis."""
    return (TICK_GAP + max(0.716 * s + r for _, s, _, _, r in parts)) * PT


def x_labels(page, left, bottom, wid, xlim, ticks, base=None):
    """Tick labels under an x axis from runs, all on one baseline: ticks = [(value, parts)]. The baseline used."""
    base = base if base is not None else max(tick_base(p) for _, p in ticks)
    for v, parts in ticks:
        runs(page, left + (v - xlim[0]) / (xlim[1] - xlim[0]) * wid, bottom + base, parts, ha='center')
    return base


def x_title(page, left, wid, y, parts):
    """An axis label centred under its axis, its baseline at y."""
    runs(page, left + wid / 2, y, parts, ha='center')


def rows(page, left, top, wid, height, n, xlim, ticks, xlabel=None, manual=False):
    """Axes with n rows, row 0 at the top, an x axis at the bottom (lean.Page.rows, with tick labels set by hand where
    `manual`)."""
    ax = page.box(left, top, wid, height)
    ax.set_xlim(*xlim)
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_yticks([])
    ax.set_xticks(ticks)
    ax.grid(axis='x', color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis='x', pad=1.5)
    if manual:
        ax.set_xticklabels([''] * len(ticks))
    if xlabel:
        ax.set_xlabel(xlabel, labelpad=2)
        if width(page.fig, xlabel) > wid:           # a label wider than its axis ends at the axis' right end
            ax.xaxis.label.set_horizontalalignment('right')
            ax.xaxis.label.set_x(1.0)
    return ax


def dot(ax, x, y, colour, size=3.9, hollow=False, clip=False):
    """A dot: filled at 0.6, or open (white face); its edge opaque."""
    ax.plot([x], [y], marker='o', markersize=size, markerfacecolor='white' if hollow else colour + '99', markeredgecolor=colour,
            markeredgewidth=0.8, linestyle='none', zorder=3, clip_on=clip)


def square(ax, x, y, colour, size=KEY_SQ, alpha='99'):
    """A key's mark on a canvas in mm: a square filled at 0.6 (or as given), no edge, centred at y."""
    ax.add_patch(Rectangle((x, y - size / 2), size, size, facecolor=colour + alpha, edgecolor='none', linewidth=0))


# ---------------------------------------------------------------------------------------------------------------
# a
HALO = [pe.withStroke(linewidth=1.5, foreground='white', alpha=0.8)]


def iso_lines():
    """fig3_panels.kcat_km_draw's lines of equal kcat/Km: how many it draws, the labelled ones and the named one."""
    low, high = fig3_panels.DIFFUSION
    k = math.ceil((KCAT0 - KM1 + fig3_panels.MOLAR) / fig3_panels.ISO_STEP) * fig3_panels.ISO_STEP - fig3_panels.MOLAR
    drawn, labels = 0, []
    while k < KCAT1 - KM0:
        if not low <= k <= high:
            drawn += 1
            enter, leave = max(KM0, KCAT0 - k), min(KM1, KCAT1 - k)
            if leave - enter >= 1.5:
                labels.append((enter, leave, k))
        k += fig3_panels.ISO_STEP
    named = max((k for enter, leave, k in labels if k < low and leave - enter >= 3), default=None)
    return drawn, labels, named


def on_line(fig, ax, x, y, parts, lift=1.5):
    """Text along a 45-degree line, centred at (x, y) and just above it; parts are runs (rise in points)."""
    widths = [width(fig, t, s, st, wt) / PT for t, s, st, wt, _ in parts]      # in points
    c45 = math.sqrt(0.5)
    along = -sum(widths) / 2
    for (t, s, st, wt, rise), w in zip(parts, widths):
        up = lift + rise
        ax.annotate(t, (x, y), xytext=((along - up) * c45, (along + up) * c45), textcoords='offset points', rotation=45,
                    rotation_mode='anchor', ha='left', va='baseline', fontsize=s, fontstyle=st, fontweight=wt, color=INK,
                    zorder=4, path_effects=HALO)
        along += w
    return sum(widths) * PT        # its length in mm


def density_line(ax, x, y, colour, share=0.5):
    """One opaque line, edged in white, round the densest `share` of the points (a 2-D histogram of 0.1-decade bins,
    smoothed over a quarter of a decade). Its pieces, in data coordinates."""
    from scipy.ndimage import gaussian_filter
    xe, ye = np.arange(KM0, KM1 + 1e-9, 0.1), np.arange(KCAT0, KCAT1 + 1e-9, 0.1)
    h, _, _ = np.histogram2d(x, y, bins=[xe, ye])
    h = gaussian_filter(h, 2.5)
    flat = np.sort(h.ravel())[::-1]
    level = flat[np.searchsorted(np.cumsum(flat), share * flat.sum())]
    cs = ax.contour((xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2, h.T, levels=[level], colors=[colour], linewidths=0.8,
                    zorder=3)
    cs.set_path_effects(CASING)
    return [np.asarray(s) for s in cs.allsegs[0]]


NAME_GAP = (0.6, 1.6)      # mm from a class name in a to its own outline: at least, at most
NAME_CLEAR = 0.5           # mm a class name keeps from the other outlines, the band and the frame
NAME_TEXT = 2.0            # mm a class name keeps from every other text of a
NAME_HALO = [pe.withStroke(linewidth=1.6, foreground='white', alpha=0.9)]


def dense(pieces, step=0.002):
    """Points every `step` decades along an outline's pieces."""
    out = []
    for s in pieces:
        for a, b in zip(s[:-1], s[1:]):
            out.append(a + (b - a) * np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / step) + 1))[:, None])
    return np.vstack(out)


def box_mm(points, box):
    """mm from a box (x0, y0, x1, y1, data coordinates) to the nearest of the points."""
    x0, y0, x1, y1 = box
    dx = np.maximum(np.maximum(x0 - points[:, 0], 0), points[:, 0] - x1)
    dy = np.maximum(np.maximum(y0 - points[:, 1], 0), points[:, 1] - y1)
    return float(np.sqrt(dx ** 2 + dy ** 2).min() * DEC)


def text_boxes(page, ax, texts):
    """The boxes of texts in ax, in data coordinates."""
    renderer, inv = page.fig.canvas.get_renderer(), ax.transData.inverted()
    out = []
    for t in texts:
        bb = t.get_window_extent(renderer)
        (x0, y0), (x1, y1) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
        out.append((x0, y0, x1, y1))
    return out


def outline_names(page, ax, outlines, band, code):
    """Each outline's class name (6.5 pt, the outline's colour, a white halo) where that outline stands apart: of the
    places NAME_GAP from its own outline, outside the other outlines, NAME_CLEAR from them, the frame and the band and
    NAME_TEXT from every other text of a, the one where the other outlines are farthest beyond its own (to 0.1 mm; then
    the one nearest 1 mm from its own outline). The class with the fewest places is named first. Searched on a grid of
    0.01 decade; returns the names' boxes (data coordinates)."""
    from matplotlib.path import Path as MPath
    from scipy.ndimage import distance_transform_edt, minimum_filter
    step, cell = 0.01, 0.01 * DEC                             # decades and mm per cell
    nx, ny = round((KM1 - KM0) / step), round((KCAT1 - KCAT0) / step)
    X, Y = np.meshgrid(KM0 + (np.arange(nx) + 0.5) * step, KCAT0 + (np.arange(ny) + 0.5) * step)
    centres = np.column_stack([X.ravel(), Y.ravel()])

    def marked(points):
        m = np.zeros((ny, nx), bool)
        m[np.clip(((points[:, 1] - KCAT0) / step).astype(int), 0, ny - 1),
          np.clip(((points[:, 0] - KM0) / step).astype(int), 0, nx - 1)] = True
        return m

    points = {c: dense(p) for c, p in outlines.items()}
    near = {c: distance_transform_edt(~marked(points[c])) * cell for c in outlines}          # mm to each outline
    inside = {c: np.logical_or.reduce([MPath(s).contains_points(centres).reshape(ny, nx) for s in p])
              for c, p in outlines.items()}
    blocked = MPath(band).contains_points(centres).reshape(ny, nx)
    blocked[[0, -1], :] = blocked[:, [0, -1]] = True                                          # the frame
    more = (NAME_TEXT - NAME_CLEAR) / DEC                                                     # texts keep the larger gap
    texts_at = text_boxes(page, ax, ax.texts)
    for x0, y0, x1, y1 in texts_at:
        blocked |= (X >= x0 - more) & (X <= x1 + more) & (Y >= y0 - more) & (Y <= y1 + more)
    down, up = 0.21 * TEXT * PT, 0.72 * TEXT * PT                                             # mm under and over the baseline
    size = {c: (2 * round((down + up) / cell / 2) + 1, 2 * round(width(page.fig, CLASS_NAME[c]) / cell / 2) + 1) for c in outlines}

    def places(c, blocked):
        """(own, other) mm for a name of class c centred on each cell; NaN where it may not go."""
        lo = lambda f, cval: minimum_filter(f, size=size[c], mode='constant', cval=cval)
        own = lo(near[c], np.inf)
        other = np.min([lo(near[o], np.inf) for o in outlines if o != c], axis=0)
        ok = (own >= NAME_GAP[0]) & (own <= NAME_GAP[1]) & (other >= NAME_CLEAR) \
            & (lo(distance_transform_edt(~blocked) * cell, 0.0) >= NAME_CLEAR) \
            & ~np.logical_or.reduce([inside[o] for o in outlines if o != c])
        return np.where(ok, own, np.nan), np.where(ok, other, np.nan)

    boxes = {}
    for c in sorted(outlines, key=lambda c: int(np.sum(~np.isnan(places(c, blocked)[0])))):
        own, other = places(c, blocked)
        same(f'a: a place for the name of class {c}', bool(np.any(~np.isnan(own))), True)
        score = np.where(np.isnan(other), -np.inf, np.round(other - own, 1) * 100 - np.abs(own - 1.0))
        i, j = np.unravel_index(np.argmax(score), score.shape)
        w = width(page.fig, CLASS_NAME[c]) / DEC
        x0, base = X[i, j] - w / 2, Y[i, j] - (up - down) / 2 / DEC
        ax.text(x0, base, CLASS_NAME[c], fontsize=TEXT, color=code.colour[c], ha='left', va='baseline', zorder=5,
                path_effects=NAME_HALO)
        boxes[c] = (x0, base - down / DEC, x0 + w, base + up / DEC)
        blocked |= (X >= boxes[c][0] - more) & (X <= boxes[c][2] + more) & (Y >= boxes[c][1] - more) & (Y <= boxes[c][3] + more)
    gap = lambda a, b: math.hypot(max(0.0, a[0] - b[2], b[0] - a[2]), max(0.0, a[1] - b[3], b[1] - a[3])) * DEC   # mm
    for c, box in boxes.items():                             # checked again on the outlines and boxes, not the grid
        own = box_mm(points[c], box)
        same(f'a: the name of class {c} beside its outline', NAME_GAP[0] - 0.1 <= own <= NAME_GAP[1] + 0.1, True)
        same(f'a: the name of class {c} clear of the other outlines',
             all(box_mm(points[o], box) >= NAME_CLEAR - 0.1 for o in outlines if o != c), True)
        same(f'a: the name of class {c} clear of the other texts',
             all(gap(box, b) >= NAME_TEXT - 0.1 for b in texts_at + [b for o, b in boxes.items() if o != c]), True)
    return boxes


def panel_a(page, code, alpha=0.34, contours=False):
    fig = page.fig
    title(page, 'a', 4.0, Y_T, [run('k', TITLE, True, True), sub('cat', TITLE, True), run(' against ', TITLE, bold=True),
                                run('K', TITLE, True, True), sub('m', TITLE, True)], f'({len(KCAT):,} records)')
    ax = page.box(A_L, TOP, A_W, A_H)
    ax.spines[:].set_color(INK)
    # the draw order: the records of the first group (no EC number) under, then the large groups in one shuffled order,
    # then the small ones in another, so that their dots show
    group = GROUP[code.by]
    rng = np.random.default_rng(20261115)
    order = np.concatenate([rng.permutation(np.flatnonzero(np.isin(group, part))) for part in (code.first, code.large, code.small)])
    same('a: every record drawn once', np.array_equal(np.sort(order), np.arange(len(group))), True)
    before = (len(ax.collections), len(ax.patches), len(ax.lines), len(ax.texts))
    kcat_km_draw(fig, ax, KCAT[order], KM[order], (KCAT0, KCAT1), (KM0, KM1))
    clouds = [c for c in ax.collections[before[0]:] if isinstance(c, PathCollection)]
    same('a: one cloud of dots', len(clouds), 1)
    same('a: one dot per record', len(clouds[0].get_offsets()), len(KCAT))
    clouds[0].set_alpha(None)
    outlines = {}
    if contours:                # every record one grey dot; a line round the densest half of each of the four large classes
        clouds[0].set_facecolor(to_rgba(CLOUD, CLOUD_ALPHA))
        xy = clouds[0].get_offsets()
        drawn_group = group[order]
        for c in ('2', '1', '3', '4'):          # oxidoreductases over transferases, where the two meet on the left
            pick = drawn_group == c
            outlines[c] = density_line(ax, xy[pick, 0], xy[pick, 1], code.colour[c])
    else:
        lighter = {g: alpha for g in code.groups}
        if code.by == 'class' and alpha < 0.5:
            lighter['none'] = round(alpha * 0.30 / 0.34, 3)     # no EC number a shade lighter, as in the first v2
        clouds[0].set_facecolor([to_rgba(code.colour[g], lighter[g]) for g in group[order]])
    bands = [p for p in ax.patches[before[1]:] if isinstance(p, Polygon)]
    same('a: one diffusion band', len(bands), 1)
    bands[0].set_facecolor(BAND)
    bands[0].set_alpha(1.0)
    drawn, labels, named = iso_lines()
    same('a: the lines of equal kcat/Km', len(ax.lines) - before[2], drawn)
    for line in ax.lines[before[2]:]:                       # opaque grey, the colour they had at alpha 0.38
        line.set_color(LINE_GREY)
        line.set_alpha(None)
    olds = [t for t in ax.texts[before[3]:] if isinstance(t, Annotation)]
    same('a: the line labels kcat_km_draw set', len(olds), sum(12 if k == named else 2 for *_, k in labels))
    for t in olds:                                          # set again below at 6 pt, exponents 5 pt
        t.remove()
    for t in ax.texts:
        if t.get_text() == 'diffusion limit':
            t.set_fontsize(ALONG)
            t.set_color('#666666')
    c45 = math.sqrt(0.5)
    named_runs = []
    for enter, leave, k in labels:
        exp = power(k + fig3_panels.MOLAR, ALONG)
        parts = exp if k != named else [run('k', ALONG, True), sub('cat', ALONG), run('/', ALONG), run('K', ALONG, True), sub('m', ALONG),
                                        run(' = ', ALONG)] + exp + [run(' M', ALONG), sup('−1', ALONG), run(' s', ALONG), sup('−1', ALONG)]
        length = sum(width(fig, t, s, st, wt) for t, s, st, wt, _ in parts)
        at = leave - (length / 2 * c45) / DEC - (0.35 if k == named else 0.5)    # the named one clear of the outlines
        first = len(ax.texts)
        on_line(fig, ax, at, at + k, parts)
        if k == named:
            named_runs = ax.texts[first:]
    if outlines:
        lines = np.vstack([dense(p) for p in outlines.values()])
        runs_at = text_boxes(page, ax, named_runs)
        same('a: the named line label clear of the outlines', min(box_mm(lines, b) for b in runs_at) >= 0.4, True)
        same('a: the named line label inside the frame', max(b[3] for b in runs_at) <= KCAT1, True)
        outline_names(page, ax, outlines, bands[0].get_xy(), code)
    # tick labels and axis labels from runs (5-pt exponents and subscripts)
    ax.set_xticklabels([''] * len(ax.get_xticks()))
    ax.set_yticklabels([''] * len(ax.get_yticks()))
    ax.set_xlabel('')
    ax.set_ylabel('')
    bottom = TOP + A_H
    base = x_labels(page, A_L, bottom, A_W, (KM0, KM1), [(d, power(d)) for d in range(KM0, KM1 + 1)])
    x_title(page, A_L, A_W, bottom + base + 2.45, [run('K', italic=True), sub('m'), run(' (mM)')])
    widest = 0.0
    for d in range(KCAT0, KCAT1 + 1):
        y = TOP + (KCAT1 - d) / (KCAT1 - KCAT0) * A_H
        widest = max(widest, runs(page, A_L - TICK_GAP * PT, caps(y), power(d), ha='right'))
    runs(page, A_L - TICK_GAP * PT - widest - (1.0 + 0.21 * TEXT) * PT, TOP + A_H / 2,
         [run('k', italic=True), sub('cat'), run(' (s'), sup('−1'), run(')')], ha='center', rotation=90)
    return ax


# ---------------------------------------------------------------------------------------------------------------
# b to g
def panel_b(page, code):
    title(page, 'b', RX, Y_T, 'Values by publication year')
    left = RX + 11.0
    bx = page.box(left, TOP, RIGHT - left, B_H)
    bx.spines[:].set_color(INK)
    for s in ('top', 'right'):
        bx.spines[s].set_visible(False)
    if code.by == 'class':
        stack = [LAYERS[c] / 1000 for c in CLASSES]
        bx.stackplot(YEARS, *stack, colors=[code.colour[c] + '99' for c in CLASSES], edgecolor='white', linewidth=0.25, zorder=2)
    else:                                                    # one area: CatLog's values
        bx.fill_between(YEARS, 0, TOTAL / 1000, facecolor=GREEN + '99', edgecolor='none', zorder=2)
    top = 4 * int(np.ceil(TOTAL.max() / 4000))
    bx.set_xlim(YEARS[0] - 0.5, YEARS[-1] + 0.5)
    bx.set_ylim(0, top + 0.4)
    bx.set_yticks(range(0, top + 1, 4))
    bx.set_xticks(range(10 * int(np.ceil(YEARS[0] / 10)), YEARS[-1] + 1, 10))
    bx.set_ylabel('Values (thousands)', labelpad=2)
    bx.set_xlabel('Publication year of the paper', labelpad=2)
    bx.tick_params(axis='both', pad=1.5)
    # the key of a, b and e (b and e alone in code 2), in the years with few values, in EC order
    wid = RIGHT - left
    key = page.canvas(left, TOP, wid, B_H)
    mm_per_year = wid / (YEARS[-1] - YEARS[0] + 1.0)
    per_mm = (top + 0.4) / B_H                                   # thousands of values per mm, up the axis
    for r, row in enumerate(code.key):
        x, y = KEY_X, KEY_Y + r * KEY_PITCH
        for g in row:
            square(key, x, y, code.colour[g])
            key.text(x + KEY_SQ + 0.6, caps(y) - 0.0, code.name[g], fontsize=TEXT, va='baseline', ha='left')
            end = x + KEY_SQ + 0.6 + width(page.fig, code.name[g])
            # nothing of the areas may be under the key: every year from its left to its right edge stays below it
            span = [YEARS[0] - 0.5 + u / mm_per_year for u in (x - 0.5, end + 0.5)]
            floor = (B_H - (y + KEY_PITCH / 2)) * per_mm
            for yr, tot in zip(YEARS, TOTAL / 1000):
                if span[0] - 0.5 <= yr <= span[1] + 0.5:
                    same(f'b: the key over {yr} clears the areas', bool(tot < floor), True)
            x = end + 2.2
    return TOP + B_H


C_LABEL = 23.6                                               # c's row labels: the widest at 6.5 pt, measured in the build


def panel_c(page, code, top, bottom):
    """What a record carries: the share of records that have each thing; filled green where it is printed in the paper,
    open green (code 0: navy) where code links it; the EC number both: two dots on one line."""
    title(page, 'c', RX, top - 4.0, 'What a record carries')
    widest = max(width(page.fig, name) for name, _, _ in HAS)
    same('c: the row labels fit their column', widest <= C_LABEL, True)
    left, wid = RX + C_LABEL + 1.5, SUB - C_LABEL - 3.0
    n = len(HAS)
    ax = rows(page, left, top, wid, bottom - top, n, (0, 104), [0, 50, 100], 'Records (%)')
    colour, hollow = code.linked
    for i, (name, key, origin) in enumerate(HAS):
        share = 100 * CARRIES[key] / RECORDS
        if origin == 'both':
            printed = 100 * ECF['paper'] / RECORDS
            ax.plot([printed, share], [i, i], color=JOIN_GREY, linewidth=0.5, zorder=2)
            dot(ax, printed, i, GREEN)
            dot(ax, share, i, colour, hollow=hollow)
        elif origin == 'printed':
            dot(ax, share, i, GREEN)
        else:
            dot(ax, share, i, colour, hollow=hollow)
        runs(page, left - 1.5, caps(row_y(top, bottom - top, n, i)), [run(name)], ha='right')
    # the key, under the row labels, on the lines of the tick labels and the axis label: one line, or two where it
    # does not fit
    words = [('Printed', GREEN, False), (code.linked_word, colour, hollow)]
    widths = [1.4 + width(page.fig, w) for w, _, _ in words]
    one_line = sum(widths) + 2.0 <= C_LABEL
    canvas = page.canvas(RX, bottom, C_LABEL, 7.0)
    lines = [(TICK_GAP + 0.73 * TEXT) * PT, 5.85]           # baselines, mm under the axis: tick labels, axis label
    for j, (word, col, hol) in enumerate(words):
        x, base = (1.0 + (widths[0] + 2.0) * j, lines[0]) if one_line else (1.0, lines[j])
        dot(canvas, x, base - 0.358 * TEXT * PT, col, size=3.4, hollow=hol)
        canvas.text(x + 1.4, base, word, fontsize=TEXT, va='baseline', ha='left')


def panel_d(page, code, top):
    xs = RX + SUB
    title(page, 'd', xs, top - 4.0, 'How a constant is printed')   # final review #35: a value is a number; not detected and limits are constants
    left = xs + 15.5
    height = len(PRINTED_AS) * ROW_D
    xlim = (2.8, 5.75)
    ax = rows(page, left, top, RIGHT - left, height, len(PRINTED_AS), xlim, [3, 4, 5], manual=True)
    for i, (name, n) in enumerate(PRINTED_AS):
        same(f'd: {name} inside the axis', 10 ** xlim[0] < n < 10 ** xlim[1], True)
        colour, hollow = (GREEN, False) if name == 'A number' else code.bound
        dot(ax, np.log10(n), i, colour, hollow=hollow)
        runs(page, left - 1.5, caps(row_y(top, height, len(PRINTED_AS), i)), [run(name)], ha='right')
    bottom = top + height
    base = x_labels(page, left, bottom, RIGHT - left, xlim, [(d, power(d)) for d in (3, 4, 5)])
    x_title(page, left, RIGHT - left, bottom + base + 2.45, [run('Constants')])
    return bottom


def panel_e(page, code, top):
    xs = RX + SUB
    title(page, 'e', xs, top - 4.0, 'Organisms')
    left = xs + 15.5
    height = len(ORGANISMS) * ROW_E
    ax = rows(page, left, top, RIGHT - left, height, len(ORGANISMS), (0, 25), [0, 10, 20], 'Records (thousands)')
    for i, (name, by_class) in enumerate(ORGANISMS):
        by = by_class if code.by == 'class' else ORG_STATUS[name]
        x = 0.0
        for g in code.groups:
            w = by[g] / 1000
            if w:
                ax.add_patch(Rectangle((x, i - 0.34), w, 0.68, facecolor=code.colour[g] + '99', edgecolor='white', linewidth=0.2, zorder=2))
            x += w
        same(f'e: {name} drawn in full', round(x * 1000), sum(by.values()))
        genus, species = name.split()
        runs(page, left - 1.5, caps(row_y(top, height, len(ORGANISMS), i)), [run(f'{genus[0]}. {species}', italic=True)], ha='right')
    return top + height


def panel_f(page, top, height=4.0):
    """The values against six databases as one strip of all values (as B): the three large groups named above it,
    the two small ones under it, each small segment joined to its name by a hairline; the values no database lists
    are one segment (the legend gives its two parts)."""
    title(page, 'f', 4.0, top - 7.0, 'Values against six databases')
    left, right = A_L, RIGHT
    ax = page.canvas(0, top - 5.0, W, height + 10.5)
    none = LISTED[3][1] + LISTED[4][1]
    parts = [(LISTED[0][1], 'same'), (LISTED[1][1], 'other'), (LISTED[2][1], 'different'), (none, 'none'),
             (C['not_compared'], 'not_compared')]
    same('f: the strip holds every value', sum(n for n, _ in parts), VALUES)
    edges, x = {}, left
    for n, s in parts:
        w = (right - left) * n / VALUES
        colour = STATUS_COLOUR[s]
        ax.add_patch(Rectangle((x, 5.0), w, height, facecolor=colour if colour == PALE else colour + '99', edgecolor='white', linewidth=0.4))
        edges[s] = (x, x + w)
        x += w
    same('f: the strip ends at its right edge', round(x, 6), round(right, 6))
    pct = lambda n: f'{100 * n / VALUES:.0f}%' if 100 * n / VALUES >= 10 else f'{100 * n / VALUES:.1f}%'
    mid = lambda s: sum(edges[s]) / 2
    hair, gap = 1.5, 0.35
    above, below = 5.0 - hair - gap, 5.0 + height + hair + gap + 0.716 * TEXT * PT
    for s, at in (('different', 5.0), ('other', 5.0 + height)):       # the hairlines of the two small segments
        ax.plot([mid(s), mid(s)], [at, at - hair if s == 'different' else at + hair], color=INK, linewidth=0.4, solid_capstyle='butt')
    labels = [  # (text, x, ha, row)
        (f"Same number {pct(LISTED[0][1])}", edges['same'][0], 'left', above),
        (f"Different number {pct(LISTED[2][1])}", mid('different'), 'center', above),
        (f"In no database {pct(none)}", mid('none'), 'center', above),
        (f"Same number, other name {pct(LISTED[1][1])}", mid('other'), 'center', below),
        (f"Not compared {pct(C['not_compared'])}", edges['not_compared'][1], 'right', below)]
    spans = []
    for text, at, ha, row in labels:
        ax.text(at, row, text, fontsize=TEXT, va='baseline', ha=ha)
        w = width(page.fig, text)
        x0 = at - {'left': 0, 'center': w / 2, 'right': w}[ha]
        spans.append((row, x0, x0 + w, text))
    for i, (r1, a0, a1, t1) in enumerate(spans):
        for r2, b0, b1, t2 in spans[i + 1:]:
            if r1 == r2:
                same(f'f: {t1!r} and {t2!r} keep apart', bool(a1 + 1.5 <= b0 or b1 + 1.5 <= a0), True)
    return top + height + 6.2


def g_text(ax, xy, dx, dy, parts, size, weight, middle):
    """factor_panel's rich(), in this figure's sizes: one line from (text, raised) parts, dx and dy in points from xy."""
    fig = ax.figure
    pieces = []
    for text, raised in parts:
        fs = SMALL if raised else size
        pieces.append((text, fs, size * 0.38 if raised else 0.0, width(fig, text, fs, weight=weight) / PT))
    at = dx - sum(p[-1] for p in pieces) / 2 if middle else dx
    for text, fs, lift, w in pieces:
        ax.annotate(text, xy, xytext=(at, dy + lift), textcoords='offset points', ha='left', va='baseline', fontsize=fs,
                    fontweight=weight, color=INK)
        at += w


def panel_g(page, top, height):
    """The approved panel of database values that differ from CatLog's (factor_panel.draw: the same bins, stacking order,
    colours, spike labels and key), set in this figure's sizes; the bars opaque, as approved."""
    fp = factor_panel
    title(page, 'g', 4.0, top - 6.5, 'Database values that differ', f'({NUMBERS:,} values, {PAPERS} papers)')
    left, wid = A_L, RIGHT - A_L
    ax = page.box(left, top, wid, height)
    ax.spines[:].set_color(INK)
    colour = {k: c for k, _, c in fp.KINDS}
    for b, parts in sorted(fp.STACK.items()):
        bottom = 0
        for k, n in parts:
            ax.bar(fp.centre(b), n, width=fp.BIN, bottom=bottom, color=colour[k], linewidth=0, zorder=2)
            bottom += n
    ax.set_xlim(fp.LO, fp.HI)
    ax.set_ylim(0, fp.YMAX)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel('Papers', labelpad=2)
    labelled = {-12: power(-12), -9: power(-9), -6: power(-6), -3: [run('1/1000')], -1: [run('1/10')], 0: [run('1')],
                1: [run('10')], math.log10(60): [run('60')], 3: [run('1000')], 6: power(6)}
    ax.set_xticks(list(labelled))
    ax.set_xticklabels([''] * len(labelled))
    ax.set_xticks([e for e in range(-12, 7) if e not in labelled], minor=True)
    ax.tick_params(axis='both', pad=1.5)
    bottom = top + height
    base = x_labels(page, left, bottom, wid, (fp.LO, fp.HI), list(labelled.items()))
    x_title(page, left, wid, bottom + base + 2.45, [run('Database value ÷ CatLog value')])
    lead = 7.1                                                     # points between the lines of a spike's label
    per_unit = wid / (fp.HI - fp.LO) / PT                          # points per log10 unit, across
    per_paper = height / fp.YMAX / PT                              # points per paper, up
    x_of = lambda b: (fp.centre(b) - fp.LO) * per_unit
    tall = {b: n * per_paper for b, n in fp.TOP.items()}           # every bar's height, in points
    line_w = lambda parts, size: sum(width(fig_, t, SMALL if r else size, weight='bold' if size == TITLE else 'normal')
                                     for t, r in parts) / PT
    fig_ = page.fig
    boxes = []
    for v, head, lines, side in fp.SPIKES:
        b = fp.bin_of(v)
        xy, middle, dx = (fp.centre(b), fp.TOP.get(b, 0)), side == 'mid', 0 if side == 'mid' else 2.5
        up = 2.0 + lead * len(lines)
        span = max([line_w(head, TITLE)] + [line_w(p, TEXT) for p in lines])
        low = tall.get(b, 0) + 1.8                                 # the label's lowest point, above the axis

        def line_boxes(dx):
            """Each line's box at the sideways shift dx, in points from the axis' left end."""
            out = []
            for parts, size, rise in [(head, TITLE, up + 1.0)] + [(p, TEXT, up - lead * (i + 1) + 1.2) for i, p in enumerate(lines)]:
                w = line_w(parts, size)
                a = x_of(b) + (dx - w / 2 if middle else dx)
                base = tall.get(b, 0) + rise
                raised = any(r for _, r in parts)
                out.append((v, a, a + w, base - 0.21 * size, base + (size * 0.38 + 0.716 * SMALL if raised else 0.716 * size)))
            return out
        if middle:          # a centred label moves sideways, as little as it can, to clear every taller bar by 2 points
            for _ in range(20):  # and every line of a label already placed by 2 points
                hits = [x_of(b2) - x_of(b) for b2, t in tall.items() if b2 != b and t > low
                        and abs(x_of(b2) - x_of(b) - dx) < span / 2 + 2.0]
                if hits:
                    h = min(hits, key=lambda h: abs(h - dx))
                    dx = h + span / 2 + 2.0 if h < dx else h - span / 2 - 2.0
                    continue
                meets = [(a1 + 2.0 - c0, c1 + 2.0 - a0) for _, a0, a1, b0, b1 in line_boxes(dx)
                         for _, c0, c1, d0, d1 in boxes
                         if not (a1 + 2.0 <= c0 or c1 + 2.0 <= a0 or b1 + 2.0 <= d0 or d1 + 2.0 <= b0)]
                if not meets:
                    break
                to_left, to_right = max(m[0] for m in meets), max(m[1] for m in meets)
                dx = dx - to_left - 0.01 if to_left <= to_right else dx + to_right + 0.01
            else:
                raise SystemExit(f'g: the label of {v:.2f} finds no place clear of the bars and the other labels')
        x0 = x_of(b) + (dx - span / 2 if middle else dx)
        same(f'g: the label of {v:.2f} clears the bars', any(t > low and x0 - 2.0 < x_of(b2) < x0 + span + 2.0
                                                              for b2, t in tall.items() if b2 != b), False)
        boxes += line_boxes(dx)
        g_text(ax, xy, dx, up + 1.0, head, TITLE, 'bold', middle)
        for i, parts in enumerate(lines):
            g_text(ax, xy, dx, up - lead * (i + 1) + 1.2, parts, TEXT, 'normal', middle)
    for i, (v1, a0, a1, b0, b1) in enumerate(boxes):                # no line of one label meets a line of another
        for v2, c0, c1, d0, d1 in boxes[i + 1:]:
            if v1 != v2:
                same(f'g: the labels of {v1:.2f} and {v2:.2f} keep apart',
                     bool(a1 + 1 < c0 or c1 + 1 < a0 or b1 + 1 < d0 or d1 + 1 < b0), True)
    # the key, from the left edge of the x10^-12 label, its marks squares as opaque as the bars
    key = page.canvas(left, top, wid, height)
    x0 = (fp.centre(fp.bin_of(-12)) - fp.LO) / (fp.HI - fp.LO) * wid + 2.5 * PT
    for i, (_, label, c) in enumerate(fp.KINDS):
        y = (6.5 + 8.4 * i) * PT - 0.358 * TEXT * PT
        square(key, x0, y, c, alpha='')
        key.text(x0 + KEY_SQ + 0.9, caps(y), label, fontsize=TEXT, va='baseline', ha='left')
    return bottom


def save_rgb(page, path):
    """The page as an RGB PNG (the journal's form), 300 dpi."""
    from PIL import Image
    page.fig.savefig(path, dpi=300, facecolor='white')
    import matplotlib.pyplot as plt
    plt.close(page.fig)
    with Image.open(path) as im:
        im.convert('RGB').save(path, dpi=(300, 300))


def build(n, path, alpha=0.34, contours=False):
    code = Code(n)
    page = Page(HEIGHT, path.parent, path.parent)
    panel_a(page, code, alpha, contours)
    panel_b(page, code)
    panel_c(page, code, CD_TOP, E_END)
    panel_d(page, code, CD_TOP)
    panel_e(page, code, E_TOP)
    panel_f(page, F_TOP)
    panel_g(page, G_TOP, G_H)
    save_rgb(page, path)
    print(f'wrote {path} (code {n}; a: dots {"grey, lines round the densest half" if contours else f"at {alpha}"})')


def sheet(paths, words, out, crop=None, scale=2 / 3):
    """Pictures side by side with a few words over each, as one PNG (scaled to `scale` of 300 dpi)."""
    from PIL import Image, ImageDraw, ImageFont
    ims = []
    for p in paths:
        with Image.open(p) as im:
            im = im.convert('RGB')
            if crop:
                im = im.crop(crop)
            ims.append(im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS))
    px = 300 * scale / 25.4                                  # pixels per mm
    gap, head = round(8 * px), round(9 * px)
    canvas = Image.new('RGB', (sum(i.width for i in ims) + gap * (len(ims) + 1), max(i.height for i in ims) + head + gap), 'white')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', round(9 * 300 * scale / 72))
    x = gap
    for im, word in zip(ims, words):
        canvas.paste(im, (x, head))
        draw.text((x + round(4 * px), round(2.5 * px)), word, fill=INK, font=font)
        x += im.width + gap
    canvas.save(out, dpi=(round(300 * scale), round(300 * scale)))
    print('wrote', out)


if __name__ == '__main__':
    build(1, HERE / 'fig3.png', contours=True)       # a as grey dots with a line round each large class (15 Nov)
    print(f'180 x {HEIGHT:.1f} mm; a: {len(KCAT):,} records ({BEYOND} on the frame), axes {KM0}..{KM1} and {KCAT0}..{KCAT1}')
    if '--choices' in sys.argv:
        i = sys.argv.index('--choices')
        keep = Path(sys.argv[i + 1]) if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith('--') else None
        with tempfile.TemporaryDirectory() as tmp:
            out = keep or Path(tmp)
            out.mkdir(parents=True, exist_ok=True)
            singles = [out / f'fig3_code{n}.png' for n in (0, 1, 2)]
            for n, p in zip((0, 1, 2), singles):
                build(n, p)
            sheet(singles, ['0  As first built: the website\'s class colours', '1  Classes without red or green (fig3.png)',
                            '2  One colour code, no classes'], HERE / 'fig3_colour_choices.png')
            dots = [out / 'fig3_a_034.png', out / 'fig3_a_060.png', out / 'fig3_a_lines.png']
            build(1, dots[0], alpha=0.34)
            build(1, dots[1], alpha=0.6)
            build(1, dots[2], alpha=0.34, contours=True)
            box = (0, 0, round((RX - 2.0) * 300 / 25.4), round((TOP + A_H + 8.0) * 300 / 25.4))
            sheet(dots, ['Dots at 0.34', 'Dots at 0.6', 'Grey dots, a named line round each large class (fig3.png)'],
                  HERE / 'fig3_a_choices.png', crop=box, scale=1.0)

if '--numbers' in sys.argv:                 # every drawn number, for README.md
    pct = lambda n, of: f'{100 * n / of:.1f}%'
    print(f"export {EXPORT['written']}: {RECORDS:,} records, {VALUES:,} values, {EXPORT['papers']:,} papers")
    print(f"a: {len(KCAT):,} records in {SNAP['a']['papers']:,} papers; by class", {CLASS_NAME[c]: int(np.sum(GROUP['class'] == c)) for c in CLASSES},
          '; by status', {s: int(np.sum(GROUP['status'] == s)) for s in STATUSES})
    print(f"b: {YEARS[0]}-{YEARS[-1]}; values by class", {CLASS_NAME[c]: int(LAYERS[c].sum()) for c in CLASSES})
    print('c:', '; '.join(f'{name} {pct(CARRIES[key], RECORDS)}' for name, key, _ in HAS),
          f"; EC number printed {ECF['paper']:,} ({pct(ECF['paper'], RECORDS)}), from UniProt {ECF['uniprot']:,} ({pct(ECF['uniprot'], RECORDS)}),"
          f" from the databases {ECF['databases']:,} ({pct(ECF['databases'], RECORDS)})")
    print('d:', '; '.join(f'{n} {v:,}' for n, v in PRINTED_AS), '| by constant', BOUNDS, f"| {SNAP['bounds']['papers']:,} papers")
    print('e:', '; '.join(f"{o} {sum(d.values()):,} ({', '.join(f'{CLASS_NAME[c]} {d[c]:,}' for c in CLASSES)})" for o, d in ORGANISMS))
    print('e, spellings:', {o: CLS['organism_spellings'][o] for o, _ in ORGANISMS})
    print('e, by status:', {o: ORG_STATUS[o] for o, _ in ORGANISMS})
    print('f:', '; '.join(f'{n} {v:,} ({pct(v, VALUES)})' for n, v in LISTED), f"; not compared {C['not_compared']:,} ({pct(C['not_compared'], VALUES)})")
    print(f'g: {NUMBERS:,} values, {PAPERS} papers, {factor_panel.ON_FACTOR:,} on a unit factor;', dict(factor_panel.VERDICTS))
