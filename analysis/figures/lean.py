"""Shared drawing code of the option drafts of Figs 2 to 4 (build_fig2_options.py, build_fig3_options.py,
build_fig4_options.py), so the three figures look alike.

The look, from the owner's comments of 14 November 2026: a panel has a title of a few plain words, row labels and
an axis label; marks are dots on an axis or one mark per unit (a record, a paper, a kind of error); no notes,
brackets, tick strips or names of our own inside a panel. What a panel leaves out goes to the legend. Colours: the
owner's Nature BPG palette, fills at alpha 0.6 (hex suffix 99), lines and text opaque. Arial 5 to 7 pt on a page
180 mm wide; everything is placed in mm from the page's top left.
"""
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402

RED, NAVY, GREEN, BLUE, SLATE, MINT, TAN = '#E64B35', '#3C5488', '#00A087', '#4DBBD5', '#8491B4', '#91D1C2', '#B09C85'
BROWN = '#7E6148'
INK, GRID, PALE, AXIS = '#222222', '#E6E6E6', '#C8C8C8', '#888888'
PLAIN = dict(color=RED, marker='o', size=4.4)       # the plain reading: a red circle
CATLOG = dict(color=GREEN, marker='D', size=4.0)    # CatLog: a green diamond
PEOPLE = dict(color='#8C7860', face=TAN, marker='o', size=4.4)   # people: a tan circle, as in Fig. 1
W, DPI = 180.0, 300
KM_T = r'$K_\mathrm{m}$'

plt.rcParams.update({'font.family': 'Arial', 'font.size': 6.5, 'axes.linewidth': 0.5, 'axes.edgecolor': AXIS,
                     'xtick.major.width': 0.5, 'ytick.major.width': 0.5, 'xtick.major.size': 2, 'ytick.major.size': 2,
                     'xtick.minor.width': 0.35, 'ytick.minor.width': 0.35, 'xtick.minor.size': 1.2, 'ytick.minor.size': 1.2,
                     'xtick.color': INK, 'ytick.color': INK, 'axes.labelcolor': INK, 'text.color': INK,
                     'mathtext.fontset': 'custom', 'mathtext.rm': 'Arial', 'mathtext.it': 'Arial:italic',
                     'mathtext.bf': 'Arial:bold', 'mathtext.bfit': 'Arial:bold:italic'})


def same(what, a, b):
    """Stop the build when a drawn number is not the number of its file."""
    if a != b:
        raise SystemExit(f'{what}: {a!r} != {b!r}')


class Page:
    """A figure 180 mm wide."""

    def __init__(self, height, out, root):
        self.h, self.out, self.root = height, out, root
        self.fig = plt.figure(figsize=(W / 25.4, height / 25.4), dpi=DPI)

    def box(self, left, top, width, height):
        return self.fig.add_axes([left / W, 1 - (top + height) / self.h, width / W, height / self.h])

    def canvas(self, left, top, width, height):
        """Axes in mm with no frame, for marks placed by hand: x to the right, y down, from the box's top left."""
        ax = self.box(left, top, width, height)
        ax.set_xlim(0, width)
        ax.set_ylim(height, 0)
        ax.axis('off')
        return ax

    def text(self, x, y, s, **kw):
        kw.setdefault('va', 'center')
        return self.fig.text(x / W, 1 - y / self.h, s, **kw)

    def rich(self, x, y, parts, ha='left', size=6.5, **kw):
        """One line of text set from runs (text, kind), its baseline at y: kind '' is plain, 'i' italic, 'sup' small and
        raised, 'sub' small and lowered. For units and symbols: mathtext sets Arial exponents too high and too far."""
        renderer = self.fig.canvas.get_renderer()
        shape = {'sup': (0.72, 0.42), 'sub': (0.72, -0.22)}
        runs = []
        for text, kind in parts:
            scale, rise = shape.get(kind, (1.0, 0.0))
            style = 'italic' if kind == 'i' else 'normal'
            prop = FontProperties(family='Arial', style=style, size=size * scale)
            width = renderer.get_text_width_height_descent(text, prop, ismath=False)[0] / self.fig.dpi * 25.4
            runs.append((text, style, size * scale, rise * size * 25.4 / 72, width))
        at = x - sum(r[-1] for r in runs) * {'left': 0.0, 'center': 0.5, 'right': 1.0}[ha]
        for text, style, fs, lift, width in runs:
            self.fig.text(at / W, 1 - (y - lift) / self.h, text, fontsize=fs, fontstyle=style, va='baseline', ha='left', **kw)
            at += width

    def right_of(self, t, gap=0.9):
        """The x, in mm, just right of a text already placed."""
        self.fig.canvas.draw()
        return t.get_window_extent().x1 / self.fig.bbox.width * W + gap

    def title(self, letter, x, y, name, rest=''):
        """A panel's letter, its name in bold, and what it counts in plain weight."""
        self.text(x, y, letter, fontsize=8, fontweight='bold')
        bold = self.text(x + 4.5, y, name, fontsize=6.8, fontweight='bold')
        if rest:
            self.text(self.right_of(bold), y, rest, fontsize=6.8)

    def rows(self, left, top, width, height, n, xlim, ticks, xlabel=None, labels=None):
        """Axes with n rows, row 0 at the top; an x axis only where a label is given."""
        ax = self.box(left, top, width, height)
        ax.set_xlim(*xlim)
        ax.set_ylim(n - 0.5, -0.5)
        ax.set_yticks([])
        ax.set_xticks(ticks)
        if labels:
            ax.set_xticklabels(labels)
        ax.grid(axis='x', color=GRID, linewidth=0.5)
        ax.set_axisbelow(True)
        for s in ('top', 'right', 'left'):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis='x', pad=1.5)
        if xlabel:
            ax.set_xlabel(xlabel, labelpad=2)
            self.fig.canvas.draw()       # a label wider than its axis ends at the axis' right end
            if ax.xaxis.label.get_window_extent().width / self.fig.bbox.width * W > width:
                ax.xaxis.label.set_horizontalalignment('right')
                ax.xaxis.label.set_x(1.0)
        else:
            ax.spines['bottom'].set_visible(False)
            ax.tick_params(axis='x', length=0, labelbottom=False)
        return ax

    def save(self, name):
        self.out.mkdir(exist_ok=True)
        self.fig.savefig(self.out / name, dpi=DPI, facecolor='white')
        plt.close(self.fig)
        print('wrote', (self.out / name).relative_to(self.root))


def row_y(top, height, n, i):
    """The height, in mm from the page's top, of row i of n in a block."""
    return top + height * (i + 0.5) / n


def baseline(y, size=6.5):
    """The baseline, in mm from the page's top, of a line of text whose capitals are centred at y."""
    return y + 0.358 * size * 25.4 / 72


def mark(ax, x, y, st, hollow=False, size=None, lo=None, hi=None, clip=False):
    """One mark; open where `hollow`; with a line from lo to hi where given."""
    if lo is not None:
        ax.plot([lo, hi], [y, y], color=st['color'], linewidth=1.0, solid_capstyle='round', zorder=2)
    ax.plot([x], [y], marker=st['marker'], markersize=size or st['size'],
            markerfacecolor='white' if hollow else st.get('face') or st['color'] + '99',
            markeredgecolor=st['color'], markeredgewidth=0.8, linestyle='none', zorder=3, clip_on=clip)
