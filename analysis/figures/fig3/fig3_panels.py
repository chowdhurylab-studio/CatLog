"""Panels a and b of Fig. 3, as functions (used by build_fig3.py and build_fig3_options.py, so both draw them alike).

a  kcat against Km, one dot per record that has both, with lines of equal kcat/Km every hundredfold and the diffusion
   limit (10^8 to 10^9 M^-1 s^-1) as a band; modelled on the website's landing figure (cloudflare/kmplane.py).
b  CatLog's values by publication year of the paper.
"""
import math
import re

import numpy as np
import matplotlib.patheffects as pe
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Polygon

GREEN, TAN, INK = '#00A087', '#B09C85', '#222222'
KCAT_T, KM_T, RATIO_T = r'$k_\mathrm{cat}$', r'$K_\mathrm{m}$', r'$k_\mathrm{cat}/K_\mathrm{m}$'
AXIS_SHARE = 0.99      # the axes: whole decades round the middle 99% of the values (the website's rule)
JITTER, JITTER_SEED = 0.2, 20261025   # for drawing only: each value moved by at most a fifth of its last digit
DIFFUSION = (5, 6)     # log10 mM^-1 s^-1: 10^8 to 10^9 M^-1 s^-1
ISO_STEP, MOLAR = 2, 3
SUP, SUB, FLAT = (0.72, 0.42), (0.72, -0.22), (1.0, 0.0)   # a raised, lowered or plain run: its size and its rise, in ems


def span(logs):
    tail = (1 - AXIS_SHARE) / 2 * 100
    low, high = math.floor(np.percentile(logs, tail)), math.ceil(np.percentile(logs, 100 - tail))
    return low, max(high, low + 2)


def last_place(x):
    """The place of the last digit the value is written with (24.7 -> 0.1, 135 -> 1, 0.005 -> 0.001)."""
    m = re.fullmatch(r'(\d*)(?:\.(\d*))?(?:e([+-]?\d+))?', repr(float(f'{x:.12g}')))
    frac = (m.group(2) or '')
    frac = '' if frac == '0' else frac
    return 10.0 ** (int(m.group(3) or 0) - len(frac))


def kcat_km_axes(kcat, km):
    """The whole decades each axis spans (kcat, then Km) and the number of records beyond them."""
    log_kcat, log_km = np.log10(kcat), np.log10(km)
    (kcat0, kcat1), (km0, km1) = span(log_kcat), span(log_km)
    beyond = int(np.sum((log_kcat < kcat0) | (log_kcat > kcat1) | (log_km < km0) | (log_km > km1)))
    return (kcat0, kcat1), (km0, km1), beyond


def kcat_km_draw(fig, ax, kcat, km, kcat_span, km_span):
    """Panel a into ax, whose width and height must be in the ratio of the decades (a line of equal kcat/Km at 45 degrees)."""
    (kcat0, kcat1), (km0, km1) = kcat_span, km_span
    rng = np.random.default_rng(JITTER_SEED)
    place_k = np.minimum(np.array([last_place(v) for v in kcat]), kcat)
    place_m = np.minimum(np.array([last_place(v) for v in km]), km)
    draw_k = np.clip(np.log10(kcat + place_k * rng.uniform(-JITTER, JITTER, len(kcat))), kcat0, kcat1)
    draw_m = np.clip(np.log10(km + place_m * rng.uniform(-JITTER, JITTER, len(km))), km0, km1)
    ax.set_xlim(km0, km1)
    ax.set_ylim(kcat0, kcat1)
    low, high = DIFFUSION
    ax.add_patch(Polygon([(km0, km0 + low), (km1, km1 + low), (km1, km1 + high), (km0, km0 + high)], closed=True,
                         facecolor=TAN, alpha=0.30, linewidth=0, zorder=1))
    # dots below the palette's 0.6 on purpose: tens of thousands of them overlap, and the colour builds up where they crowd
    ax.scatter(draw_m, draw_k, s=0.5, color=GREEN, alpha=0.18, linewidths=0, zorder=2, rasterized=True, snap=False)
    k = math.ceil((kcat0 - km1 + MOLAR) / ISO_STEP) * ISO_STEP - MOLAR
    labels = []
    while k < kcat1 - km0:
        if not low <= k <= high:
            ax.plot([km0, km1], [km0 + k, km1 + k], color=INK, alpha=0.38, linewidth=0.4, zorder=3)
            enter, leave = max(km0, kcat0 - k), min(km1, kcat1 - k)
            if leave - enter >= 1.5:           # a corner line has no label
                labels.append((enter, leave, k))
        k += ISO_STEP
    named = max((k for enter, leave, k in labels if k < low and leave - enter >= 3), default=None)
    halo = [pe.withStroke(linewidth=1.5, foreground='white', alpha=0.8)]

    def on_line(x, y, runs, size=5.4, lift=1.5):
        """Text set along a 45-degree line, centred at (x, y) and just above it: runs of (text, italic, (scale, rise)).
        Plain text piece by piece, because rotated mathtext spaces its exponents badly."""
        renderer = fig.canvas.get_renderer()
        widths = []
        for text, italic, (scale, rise) in runs:
            prop = FontProperties(family='Arial', style='italic' if italic else 'normal', size=size * scale)
            widths.append(renderer.get_text_width_height_descent(text, prop, ismath=False)[0] * 72 / fig.dpi)
        c45 = math.sqrt(0.5)
        along = -sum(widths) / 2
        for (text, italic, (scale, rise)), w in zip(runs, widths):
            up = lift + rise * size
            ax.annotate(text, (x, y), xytext=((along - up) * c45, (along + up) * c45), textcoords='offset points', rotation=45,
                        rotation_mode='anchor', ha='left', va='baseline', fontsize=size * scale,
                        fontstyle='italic' if italic else 'normal', color=INK, zorder=4, path_effects=halo)
            along += w

    for enter, leave, k in labels:             # one line is named in full, the others carry the number only
        power = [('10', False, FLAT), (str(k + MOLAR).replace('-', '−'), False, SUP)]
        if k == named:
            at = leave - 1.45
            on_line(at, at + k, [('k', True, FLAT), ('cat', False, SUB), ('/', False, FLAT), ('K', True, FLAT), ('m', False, SUB),
                                 (' = ', False, FLAT)] + power + [(' M', False, FLAT), ('−1', False, SUP),
                                                                   (' s', False, FLAT), ('−1', False, SUP)])
        else:
            at = leave - 0.8
            on_line(at, at + k, power)
    mid = (low + high) / 2
    at = min(km1, kcat1 - mid) - 1.25
    ax.text(at, at + mid, 'diffusion limit', rotation=45, rotation_mode='anchor', ha='center', va='center', fontsize=5.4,
            color='#4F4132', zorder=4)
    for axis, a0, a1 in ((ax.xaxis, km0, km1), (ax.yaxis, kcat0, kcat1)):
        axis.set_ticks(range(a0, a1 + 1))
        axis.set_ticklabels([f'$10^{{{d}}}$'.replace('-', '−') for d in range(a0, a1 + 1)])
        axis.set_ticks([d + math.log10(m) for d in range(a0, a1) for m in range(2, 10)], minor=True)
    ax.set_xlabel(f'{KM_T} (mM)', labelpad=2)
    ax.set_ylabel(r'$k_\mathrm{cat}\ (\mathrm{s}^{-1}\!\!)$', labelpad=1)
    ax.tick_params(axis='both', which='both', pad=1.5)


def years_draw(bx, years, per_year, ylabel):
    """Panel b into bx: values (thousands) by publication year."""
    bx.plot(years, [n / 1000 for n in per_year], color=GREEN, lw=1.0, marker='o', ms=2.1, zorder=3)
    bx.set_xlim(years[0] - 1.5, years[-1] + 1.5)
    y_top = 2 * math.ceil(max(per_year) / 2000)          # thousands, the next even number above the highest year
    bx.set_ylim(0, y_top + 0.3)
    bx.set_xticks(range(10 * math.ceil(years[0] / 10), years[-1] + 1, 10))
    bx.set_yticks(range(0, y_top + 1, 2))
    bx.set_ylabel(ylabel, labelpad=2)
    bx.set_xlabel('Publication year of the paper', labelpad=2)
    for s_ in ('top', 'right'):
        bx.spines[s_].set_visible(False)
    bx.tick_params(axis='both', pad=1.5)
