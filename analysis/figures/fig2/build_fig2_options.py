"""Fig. 2, accuracy, in two versions for the owner to pick from (PNG drafts).

Planned in writing/research/display_plan_20261111/STRENGTHS_PLAN.md (14 November 2026): the figure leads with the
paper's strengths. Each test alone stays in Table 1.

  a  People agree with CatLog: the records people checked against their papers, and those with a value disputed.
       options/fig2_A.png   one dot per reviewer: the share of that reviewer's records with no value disputed
       options/fig2_B.png   one small square per record, column by column in the order they were decided; red where
                           a value is disputed
  b  Both tests together (230 papers): one dot per paper, in two blocks at the same places; a mark where a reading
     stored a wrong value. An open diamond: a paper where CatLog changed the printed unit (the one key line of the
     figure says so: the independent check of 14 November found that a reader cannot guess it).
  c  The twelve papers of b by kind of mistake, at their number of wrong values.

Nothing else is on the art (the owner, 14 November: "Figure 2 reads a lot"; "doesnt it look and feel ai with
internal verbose"): no count lines, intervals, p-values or notes. What the legend must say is in options/README.md.

Numbers: people_data.py (the review file) and fig2_data.py (the tests' result files and the accuracy check), read and
asserted there and here. Colours: the owner's Nature BPG palette.

Run:  python3 -I -B writing/figures/fig2/build_fig2_options.py
"""
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]     # fig2_data.py, people_data.py; lean.py (python -I leaves folders out)
from lean import CATLOG, GREEN, INK, KM_T, PALE, PEOPLE, PLAIN, RED, W, Page, mark, row_y, same  # noqa: E402
from fig2_data import BOTH, L, PAPERS_WRONG, RF, ROOT, ST  # noqa: E402
import people_data as people  # noqa: E402

OUT = HERE / 'options'

# ---------------------------------------------------------------------------------------------------------------
# Numbers
# a: people's review as frozen for the paper on 16 November 2026 (paper/evidence/human_review_freeze_20261116/
#    numbers.json, which the Results quote too; people_data.py asserts the frozen file against it)
same('a: records people checked against a paper (frozen)', people.RECORDS, people.NUMBERS['records_checked'])
same('a: records with a value disputed (frozen)', people.DISPUTED, people.NUMBERS['records_disputed'])
same('a: disputed values found as printed', people.AS_PRINTED, people.DISPUTED)
same('a: papers that hold the disputed records (frozen)', people.PAPERS_DISPUTED, people.NUMBERS['disputed_papers'])
same('a: reviewers', len(people.REVIEWERS), 8)

# b: every paper of both tests, in the order of the result files (the random test, then the locked test)
PAPERS = list(RF['per_paper']) + list(L['per_paper'])
same('b: papers of both tests', len(PAPERS), BOTH['papers'])
same('b: no paper twice', len(set(PAPERS)), len(PAPERS))
WRONG = {(q['side'], q['pmid']): q for q in PAPERS_WRONG}
same('b: no paper has a wrong value on both sides', {p for s, p in WRONG if s == 'plain'} & {p for s, p in WRONG if s == 'catlog'}, set())
same('b: papers with a wrong value', (sum(1 for s, _ in WRONG if s == 'plain'), sum(1 for s, _ in WRONG if s == 'catlog')),
     (BOTH['plain'], BOTH['catlog']))
same('b: papers left for CatLog with its unit changes counted right', sum(1 for (s, _), q in WRONG.items() if s == 'catlog' and not q['unit_changes']),
     BOTH['catlog_changes_right'])

# c: the kind of each paper's wrong values, from the accuracy check (stats.json#kinds_final); one kind per paper.
# Not every one of a kind's values was stored as Km (final review, 16 Nov, #11: of the 18 Hill-type values 17 are Km
# and 1 a kcat/K stored as kcat/Km; of the activator's 4, 2 are Km and 2 kcat/Ka): the labels name the constant only
KINDS = (('credited by the paper to earlier work', 'Value from an earlier paper', 'plain', 35),
         ('Hill-type half-saturation constant', 'Hill constant', 'plain', 18),
         ('activation constant', 'Activator constant', 'plain', 4),
         ('unit change from the paper', 'Printed unit changed', 'catlog', 34),
         ('contested exponent', 'Exponent read from a scan', 'catlog', 6))
BY_KIND = [[] for _ in KINDS]                    # per kind: (wrong values, open mark) of each paper
for side in ('plain', 'catlog'):
    for q in ST['kinds_final'][side]['by_paper']:
        same(f"c: {q['pmid']}: one kind", len(q['subkind']), 1)
        name, n = next(iter(q['subkind'].items()))
        row = [i for i, (prefix, _, s, _) in enumerate(KINDS) if name.startswith(prefix) and s == side]
        same(f"c: {q['pmid']}: a kind this panel names ({name!r})", len(row), 1)
        w = WRONG[(side, q['pmid'])]
        same(f"c: {q['pmid']}: wrong values, both files", (n, q['wrong']), (w['wrong'], w['wrong']))
        BY_KIND[row[0]].append((n, w['unit_changes'] > 0))
same('c: wrong values by kind', [sum(n for n, _ in ps) for ps in BY_KIND], [k[3] for k in KINDS])
same('c: papers by kind', [len(ps) for ps in BY_KIND], [3, 5, 1, 2, 1])
same('c: every paper of b is in c', sum(len(ps) for ps in BY_KIND), len(WRONG))
same('c: the open marks are the unit changes', [all(o for _, o in ps) for ps in BY_KIND], [False, False, False, True, False])


# ---------------------------------------------------------------------------------------------------------------
# Panels
def reviewers(page, x_letter, left, top, width, pitch=5.0):
    """a, as dots: per reviewer the share of records with no value disputed; all records in the last row."""
    page.title('a', x_letter, top - 5.8, "People's review", f'({people.RECORDS:,} records)')
    n = len(people.REVIEWERS)
    height = (n + 1.5) * pitch
    ax = page.box(left, top, width, height)
    ax.set_xlim(89.4, 100.6)
    ax.set_ylim(n + 1.0, -0.5)
    ax.set_yticks([])
    ax.set_xticks([90, 95, 100])
    ax.grid(axis='x', color='#E6E6E6', linewidth=0.5)
    ax.set_axisbelow(True)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis='x', pad=1.5)
    ax.set_xlabel('Records with no value disputed (%)', labelpad=2)
    y_of = lambda i: top + height * (i + 0.5) / (n + 1.5)
    page.text(left + width + 2.0, top - 1.6, 'Records', fontsize=6)
    for i, (number, records, disputed) in enumerate(people.REVIEWERS):
        mark(ax, 100 * (1 - disputed / records), i, PEOPLE)
        page.text(left - 1.5, y_of(i), f'Reviewer {number}', ha='right')
        page.text(left + width + 2.0, y_of(i), f'{records:,}')
    i = n + 0.25
    mark(ax, 100 * (1 - people.DISPUTED / people.RECORDS), i, PEOPLE, size=5.6)
    page.text(left - 1.5, y_of(i), 'All', ha='right', fontweight='bold')
    page.text(left + width + 2.0, y_of(i), f'{people.RECORDS:,}', fontweight='bold')
    return top + height


def field(page, x_letter, left, top, width, pitch=0.8):
    """a, as every record: one small square each, down each column and then to the right, in the order decided."""
    page.title('a', x_letter, top - 4.3, "People's review", f'({people.RECORDS:,} records)')
    rows = math.ceil(people.RECORDS / int(width / pitch))
    cols = math.ceil(people.RECORDS / rows)
    ax = page.canvas(left, top, cols * pitch, rows * pitch)
    xs = [(i // rows + 0.5) * pitch for i in range(people.RECORDS)]
    ys = [(i % rows + 0.5) * pitch for i in range(people.RECORDS)]
    pt = 72 / 25.4
    calm = [i for i, d in enumerate(people.ORDER) if not d]
    hot = [i for i, d in enumerate(people.ORDER) if d]
    same('a: squares', (len(calm), len(hot)), (people.RECORDS - people.DISPUTED, people.DISPUTED))
    ax.scatter([xs[i] for i in calm], [ys[i] for i in calm], s=(0.6 * pt) ** 2, marker='s', color=GREEN, alpha=0.6, linewidths=0, zorder=2)
    ax.scatter([xs[i] for i in hot], [ys[i] for i in hot], s=(0.95 * pt) ** 2, marker='s', color=RED, edgecolors='white', linewidths=0.25, zorder=3,
               clip_on=False)
    y = top + rows * pitch + 4.0
    key = page.canvas(left, y - 1.5, 90.0, 3.0)
    at = 0.6
    for color, alpha, name, count in ((GREEN, 0.6, 'No value disputed', people.RECORDS - people.DISPUTED), (RED, 1.0, 'A value disputed', people.DISPUTED)):
        key.scatter([at], [1.5], s=(1.5 * pt) ** 2, marker='s', color=color, alpha=alpha, linewidths=0)
        label = key.text(at + 1.6, 1.5, name, va='center', fontsize=6.5)
        page.fig.canvas.draw()
        end = label.get_window_extent().transformed(key.transData.inverted()).x1
        number = key.text(end + 1.0, 1.5, f'{count:,}', va='center', fontsize=6.5, fontweight='bold')
        page.fig.canvas.draw()
        at = number.get_window_extent().transformed(key.transData.inverted()).x1 + 5.0
    return y + 1.5


def papers(page, x_letter, left, top, pitch=1.5, cols=23, gap=9.0, key_right=False, letter='b'):
    """b: two blocks of one dot per paper, the same paper at the same place in both."""
    page.title(letter, x_letter, top - 8.3, 'Papers with a wrong value', f"({BOTH['papers']} papers)")
    rows = math.ceil(len(PAPERS) / cols)
    for k, (side, st, name) in enumerate((('plain', PLAIN, 'Plain reading'), ('catlog', CATLOG, 'CatLog'))):
        x0 = left + k * (cols * pitch + gap)
        ax = page.canvas(x0, top, cols * pitch, rows * pitch)
        quiet, loud = [], []
        for i, pmid in enumerate(PAPERS):
            at = ((i % cols + 0.5) * pitch, (i // cols + 0.5) * pitch)
            (loud if (side, pmid) in WRONG else quiet).append((at, pmid))
        ax.plot([x for (x, _), _ in quiet], [y for (_, y), _ in quiet], marker='o', markersize=1.5, color=PALE, linestyle='none', markeredgewidth=0)
        for (x, y), pmid in loud:
            mark(ax, x, y, st, hollow=WRONG[(side, pmid)]['unit_changes'] > 0, size=st['size'] - 0.7)
        same(f'b: marks, {side}', len(loud), BOTH[side])
        page.text(x0, top - 2.6, name)
        page.text(x0 + cols * pitch, top - 2.6, str(len(loud)), ha='right', fontweight='bold', color=st['color'], fontsize=7.5)
    # under CatLog's block: what an open diamond is; the line ends at the block's right edge where it would leave the page.
    # The words are Table 1 footnote 4's (final read, 17 Nov): "as the paper's own numbers support" stated as fact what
    # two agents judged after the result, while the tests' own judges had ruled those values wrong
    x_cat, y_key, words = left + cols * pitch + gap, top + rows * pitch + 3.2, "unit changed from the paper's own numbers"
    if key_right:
        t = page.text(x_cat + cols * pitch, y_key, words, fontsize=6.0, ha='right')
        page.fig.canvas.draw()
        x_text = t.get_window_extent().x0 / page.fig.bbox.width * W
    else:
        x_text = x_cat + 2.6
        page.text(x_text, y_key, words, fontsize=6.0)
    key = page.canvas(x_text - 2.6, y_key - 1.5, 3.0, 3.0)
    mark(key, 0.9, 1.5, CATLOG, hollow=True, size=CATLOG['size'] - 0.7)
    return y_key + 1.5


def kinds(page, x_letter, left, top, width, pitch=4.4, letter='c'):
    """c: the papers of b by kind of mistake; one mark per paper at its number of wrong values."""
    page.title(letter, x_letter, top - 3.6, 'Kinds of mistake')
    height = len(KINDS) * pitch
    ax = page.rows(left, top, width, height, len(KINDS), (-1.2, 31.5), [0, 10, 20, 30], 'Wrong values in the paper')
    for i, ((_, label, side, _), ps) in enumerate(zip(KINDS, BY_KIND)):
        st = PLAIN if side == 'plain' else CATLOG
        seen = {}
        for n, hollow in sorted(ps):
            k = seen.get(n, 0)                       # papers with the same number sit one above the other
            seen[n] = k + 1
            mark(ax, n, i + (0.0 if ps_count(ps, n) == 1 else (k - (ps_count(ps, n) - 1) / 2) * 0.36), st, hollow=hollow, size=st['size'] - 0.4)
        page.text(left - 1.5, row_y(top, height, len(KINDS), i), label, ha='right')
    return top + height


def ps_count(ps, n):
    return sum(1 for m, _ in ps if m == n)


# ---------------------------------------------------------------------------------------------------------------
# A: a as one dot per reviewer, at the left; b over c at the right
page = Page(72.0, OUT, ROOT)
reviewers(page, 4.0, 24.0, 11.0, 42.0, pitch=5.25)
end = papers(page, 92.0, 96.0, 13.5, key_right=True)
kinds(page, 92.0, 132.0, end + 9.5, 42.0)
page.save('fig2_A.png')

# B, the owner's pick of 15 November, without its people's panel since 16 November (the owner, on the 7,522 squares:
# "isnt that pointless ai crap -_- 7522 square wtf"): the tests only, a papers with a wrong value, b kinds of mistake.
# People's review stays a total in the Results (7,522 records, a value disputed on 30, all as printed) and in Fig. 1's
# People box; field() above is kept for the record and no longer drawn.
page = Page(38.0, OUT, ROOT)
papers(page, 4.0, 8.0, 13.5, letter='a')
kinds(page, 96.0, 136.0, 8.8, 38.0, letter='b')
page.save('fig2_B.png')
