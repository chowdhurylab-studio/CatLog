#!/usr/bin/env python3
"""THE OWNER'S RULE (16 Nov, evening): built like a person draws it, never hundreds or thousands of small pieces ("make
sure the .ai or whatever isnt hundreds thousands of object ... rather how human makes ... grouped"). FAILs: more than
MAX_OBJECTS (1,000) drawn elements in the SVG (the art has about 320, in 3 panel groups and about 40 named groups under
them), a <text> of one glyph outside the panel letters (a label split into pieces), and a PDF or an .ai beside the SVG
with more than MAX_OBJECTS objects (PyMuPDF's drawn paths, text spans and images). Context: the counts, the groups,
the largest set of same-style marks inside one group (a candidate for one compound path; the illustrator-deliverable
route folds six or more into one) and the PDF's or .ai's clips. A drawn element outside a named group was a FAIL
already ('loose elements'). The .ai beside the SVG now gets the PDF's checks too (fonts, strings, objects).
FINAL PASS check (16 Nov): the optional PDF branch (a PDF beside the checked SVG, as the .ai/PDF deliverable will
put one) looks for strings the current art prints; it had listed the 4 Nov figure's ('384 ± 6.2', '243,749', ...), so
that PDF would have failed. Nothing else changed.
M2 (11 Nov): as L2, with the slate rendering of the same picture (IMAGE_SHA256) and one more group in b, the line of
sequence beside the picture (b_record_sequence: one text and a small box in code's fill, under AREA_MIN). Nothing else.
L2 (11 Nov): b's record shows what code adds to it. One <image> is allowed again, the enzyme's picture in the record
(group b_record_enzyme; embedded PNG data whose sha256 is the prepared picture's, no transform, no text ink on it); any
other <image>, or none, FAILs. The sources over the record are databases, so navy marks are allowed in b_sources (six
small cylinders and their lines) and b_sources_arrows (the two arrows that drop onto the card, measured like every
arrow), and the databases' tint in b_sources (the lids), as in a_databases. Nothing else changed.
W1 (11 Nov): three panels, lettered a, b, c (b: from papers to values; c: the co-learning loop; the panel of rules is
gone), so the groups this check knows by name carry the drawn letters: b_store and b_record (the catalogue's tint;
green marks in b_store), c_found (red and the errors' tint), c_written and c_loop (cyan). One new shape, b's trail
(group b_trail): a dashed line in the neutral grey (#666666) with one head in the same grey. It cannot be one filled
polygon, so it has a rule of its own, as strict as the arrows': the group holds open paths stroked in that grey and
exactly one closed grey head, the head 1.2-1.5 mm long; a grey-filled head in any other group FAILs.
R5 (10 Nov): a's 'After reading' is a dashed frame, so the band grey (#F2F2F2) is no longer a neutral fill: any area
in it FAILs (grey areas are the plates of what a paper prints). Code's four arrows in c's record are slate (#8491B4,
group c_record_code): they are found and measured as arrows, held to the in-pieces rule, and a slate-filled mark anywhere
else FAILs. b's frame is one dashed line (b_outline holds no rectangle).
R4 (10 Nov): a database is drawn one way. The database each case of b names stands in the box a's Databases card
gives it (white, a navy hairline; groups b_read_database, b_convert_database, b_verify_database, b_check_database), and
the cylinder beside 'cited by databases' in c is navy (c_papers_database): DB_GROUPS holds these, and navy anywhere
else still FAILs. Text, icons and arrows are black (INK #000000; they were #3C3C3C and #262626), so the black arrows are
found and measured under that ink.
R1 (10 Nov): b's cases name a database in navy text (text is not held to DB_GROUPS, marks are) and show what it
lists in red (B_ERROR_GROUPS, as before); the Databases card has its strip back (DB_TINT in a_databases); no picture is
drawn (c's record shows the sequence as a bar), so any <image> FAILs; d's examples and their red arrow are gone.
X1 round 2 (9 Nov, a cold figure editor's review of X1): b's learned rules are cyan dots again, one group per step
(b_read_dots, b_convert_dots, b_verify_dots, b_check_dots; cyan allowed there), and the error each card's rule stops is
red in a group of its own per card (b_read_error ... b_check_error: the trap cell's red outline, the misprinted letter's
red stroke, the sizes of the errors as red text, which RED_TEXT_GROUPS now allows there). A struck value is grey text
with a grey stroke through it, and the misprinted letter a text of its own with a red stroke across it: in those groups
(STRIKE_GROUPS) an open stroked path may touch the text of its own group, and nothing else (it is listed as context).
b_check_refused is gone (b has no red cross now; d keeps its crossed arrow). c has no Reading box. Nothing else.
X1 (9 Nov, the owner's three points on U1 round 2): b is four decks of rule cards with no cyan, so cyan leaves b
(LEARN_GROUPS without the b groups: any cyan there now FAILs); its Check card's refused reading is struck by d's red
cross, a group of its own (b_check_refused) allowed red. The Databases card spans CatLog's left edge to Decide's right
(its names 6.5 pt); its colours and groups as P1's. Nothing else.
P1 (9 Nov): a's Databases card is back: navy (NPG #3C5488) marks the databases, on the card's outline and hairline
(a_databases) and its one arrow into Decide (a_databases_arrow, its own group so the card's hairline is not taken for
an arrow in pieces; measured like the other arrows); the card's strip is the databases' tint (#B1BBCF, navy at 0.40
over white), allowed in a_databases only. Navy anywhere else FAILs. The exit grey is no longer drawn (its rule stays).
T1 round 2 (7 Nov, the editor's review of T1): the role fills of slate and tan lighter (alpha 0.36 and 0.40, as light
as mint reads), so KEY_FILLS changes; the one picture is the light-grey re-render of the same structure
(P00805_AF_v6_N270_grey_600.png), so IMAGE_SHA256 changes. Nothing else.
T1 (7 Nov, the owner on S1r: the CatLog boxes "less color ish", "like the people one"): the catalogue's two boxes
(a_catalog, c_store) are no longer solid green but a light tint of it, #E0F4F1 (NPG green at 0.12 over white), the one
area colour allowed there and nowhere else; their green edges were allowed already (GREEN_MARK_GROUPS). b's rule ticks
are coloured by who found the error behind each rule (grey, the agents' and the people's edges) and are smaller than
AREA_MIN, so they need no rule; LEARN_GROUPS keeps the b groups (cyan is allowed there, no longer drawn).
S1r (7 Nov, the editor's review of S1): red is also a surface where errors are held: the errors' tint (#FCE8E5,
NPG red at 0.13 over white) fills a_flag's box and d_found's step and nothing else, and its outline there is red; b's
rule ticks (groups b_read_rules, b_convert_rules, b_verify_rules, b_check_rules) are learned rules, so cyan is allowed
there; the catalogue's own green (#00785F) fills the two CatLog boxes (a_catalog, c_store; the green rule already allows
it there); the one picture is the re-rendered slate structure (P00805_AF_v6_N270_slate_600.png).
S1 (7 Nov): red (NPG #E64B35) now means errors, and only errors: marks in a_errors (the two 'errors' arrows into
co-learning and their labels), a_flag (the pennant and the suspect mark of each source's icon), d_found (its pennant),
d_examples (the red '=', cross and lens of the three errors) and d_errors_in (their arrow into the loop); red text only
in a_errors; red arrows are measured like ink ones and their groups held to the in-pieces rule; any other red, or red
anywhere else, FAILs. One <image> is allowed: the structure picture of c's Linked row (group c_link_structure), PNG
data in the file, its sha256 the prepared picture's, inside the artboard, and no text ink on it.
Q2 (7 Nov): two colours added to the key. LEARN (#2E9BB7, NPG cyan's edge shade) marks learning: arrows and outlines
in a_rules, a_learning, d_written and d_loop only. OUT_GREY (#B3B3B3) is the one arrow that leaves the method, in a_exit
only. Arrows in either colour are measured like ink ones (head length, pieces); a LEARN or OUT_GREY fill on anything
but an arrow is an area colour outside the key. Checker: a_learning, a_exit and d_loop are held to the arrows-in-pieces
rule as a_arrows is; neither colour may colour text; any red FAILs. Copied from writing/fig1_v8/check_style_v8.py
by way of Q1.
Style check of Fig. 1 design A (design.svg), copied 2026-11-05 from writing/fig1_v8/check_style_v8.py; only the
colour rules changed (KEY_FILLS: the three role fills at alpha 0.5; NEUTRAL_FILLS: white, the plate grey, the
"outside" grey of d's split; green marks in a_catalog, c_store, c_record). v8's note follows.
Style check of Fig. 1 v8 (fig1_v8.svg), copied 2026-11-04 from writing/fig1_v7/check_style_v7.py and adapted for
v8: four panels (d_* groups and a fourth letter; zoom_lines_d belongs to d), the rule fill (NPG cyan at alpha 0.6,
#94D6E6) allowed. v7's note follows.
Style check of Fig. 1 v7 (fig1_v7.svg), copied 2026-11-04 from writing/fig1_v6/check_style_v6.py and adapted for
v7: three panels (a_*, b_*, c_* groups; three 12-pt letters), green marks allowed in a_catalog, b_check and c_store
(the catalogue and catalog.jsonl), and the height checked against the brief's 200 mm at most (Nature's 170 mm is
reported as context). v6's own note follows.
Style check of Fig. 1 v6 (fig1_v6.svg), copied 2026-11-04 from paper/figures/method_overview/v4/check_style_v4.py
and adapted: no red-'8' check (v6 has no worked example), green marks allowed in a_catalog and b_catalogue (the
catalogue), and the figure's height checked against the journal's 170 mm only (v4's aims of 115 mm and a 58-mm b were
for v4's layout). v4's description follows.
Style check of Fig. 1 v4 (method_overview_v4.svg) against the figure rules (BRIEF.md sections 2 and 4.7, the
owner's lessons.md and nature-bpg; Nature: Arial, text 5-7 pt, lines at least 0.25 pt), measured with Arial's own
metrics (fontTools, the system's Arial TTFs). Adapted from ../check_style_v3.py on 2026-11-01 for the v4 layout: arcs,
Bezier curves and ellipses are measured (v3 had none), and v3's panel targets (a's word cap, navy-and-grey-only a, the
36-mm a, the 100-mm figure) are replaced by v4's (README.md "Rebuild": b at most 58 mm, the figure at most 115 mm).

FAIL (exit 1):
- text under 5 pt, or over 7 pt other than the 12-pt bold black panel letters; a stroke under 0.25 pt; a font other
  than Arial, or a character Arial cannot draw (the renderer would substitute another font);
- two text elements whose glyph ink overlaps; text ink touched by a stroke, an arrow or an icon (strokes of rects,
  paths, circles and ellipses, arrow polygons; a filled area behind text is not a touch);
- anything (text ink, strokes included) outside the artboard;
- a banned element (filter, mask, image, clipPath, use, foreignObject, pattern, gradient, <line>), an opacity or
  text-decoration attribute, or a drawn element outside a named <g id>;
- an arrowhead outside 1.65-2.3 mm long (BRIEF 2, item 8), or an arrow drawn as more than one shape;
- a red '8' of the text-layer row more than 0.25 pt off the centre of its page-row ±;
- colour meanings: green (#00A087 / #00785F) on a mark outside the catalogue (a_catalog, b_record), since green marks
  only the value and the catalogue (legend); an area fill that is not a key colour (agent, code, people), white, the
  band grey or the database tint (one colour per role: a fill with no key entry is decoration);
- the figure not 183 mm wide, over 170 mm tall (journal) or over the 115-mm aim; b over the 58-mm aim;
- (16 Nov) more than 1,000 drawn elements, a one-glyph <text> outside the panel letters, or a PDF or .ai beside the SVG
  with more than 1,000 objects, other fonts than Arial or the art's strings missing.
Context (never a FAIL): text boxes closer than 0.5 pt, words per panel, every arrow with its head, colours, sizes,
groups, the objects and groups the figure is made of, and the fonts the PDF embeds.
Panels by group id: a_* and panel_letter_a are a; b_* and panel_letter_b are b.

Usage: python3 paper/figures/method_overview/v4/check_style_v4.py [FIGURE.svg]   (reads only; prints the report)
"""
import collections
import itertools
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
SVG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'design.svg')
PDF = os.path.splitext(SVG)[0] + '.pdf'
AI = os.path.splitext(SVG)[0] + '.ai'          # 16 Nov: the Illustrator file beside the SVG (PDF-compatible, read as PDF)
MAX_OBJECTS = 1000                             # 16 Nov, the owner: a few hundred objects per figure, never thousands
DRAWN = ('text', 'path', 'rect', 'circle', 'ellipse', 'image')
NS = '{http://www.w3.org/2000/svg}'
FONT_DIR = '/System/Library/Fonts/Supplemental'
FONT_FILES = {('normal', 'normal'): 'Arial.ttf', ('bold', 'normal'): 'Arial Bold.ttf',
              ('normal', 'italic'): 'Arial Italic.ttf', ('bold', 'italic'): 'Arial Bold Italic.ttf'}
MIN_PT, MAX_PT, LETTER_PT, MIN_LINE, NEAR = 5.0, 7.0, 8.0, 0.25, 0.5
PDF_FONTS_OK = ('ArialMT', 'Arial-BoldMT', 'Arial-ItalicMT', 'Arial-BoldItalicMT')
MM = 72 / 25.4
WIDTH_MM, HMAX_MM, H_AIM_MM, B_AIM_MM = 183.0, 200.0, 170.0, 58.0   # v7: the brief's 200 mm at most; 170 context
HEAD_MM = (1.2, 1.5)
INK = '#000000'                                 # R4: black ink (it was #262626)
RED = '#E64B35'
GREENS = {'#00A087', '#00785F'}
GREEN_MARK_GROUPS = {'a_catalog', 'b_store'}    # W1: the catalogue's two cylinders (a, b)
LEARN = '#2E9BB7'                               # Q2: learning (NPG cyan, edge shade): errors in, findings and rules out
LEARN_GROUPS = {'a_rules', 'a_learning', 'c_written', 'c_loop'}   # W1: the loop is panel c
OUT_GREY = '#B3B3B3'                            # Q2: the arrow out of the method, to Fig. 4 (P1: no longer drawn)
OUT_GROUPS = {'a_exit'}
NAVY = '#3C5488'                                # P1: the databases (NPG navy): a's Databases card and its one arrow
DB_TINT = '#B1BBCF'                             # P1: the card's title strip (NPG navy at 0.40 over white)
DB_GROUPS = {'a_databases', 'a_databases_arrow',
             'b_read_database', 'b_convert_database', 'b_verify_database', 'b_check_database',   # R4: a's name box in b's cases
             'c_papers_database',                # R4: the databases' cylinder in c's Papers box
             'b_sources', 'b_sources_arrows'}    # L2: the sources over b's record, and their two arrows onto it
DB_TINT_GROUPS = {'a_databases', 'b_sources'}    # L2: the lids of the sources' cylinders, as a's
B_ERROR_GROUPS = {'b_read_error', 'b_convert_error', 'b_verify_error', 'b_check_error'}   # X1 round 2: what b's rules stop
RED_GROUPS = {'a_errors', 'a_flag', 'c_found'}   # S1: red means errors (W1: the loop is panel c; b draws no error)
RED_TEXT_GROUPS = {'a_errors'}                  # S1: the two 'errors' labels (W1: nothing else)
STRIKE_GROUPS = B_ERROR_GROUPS                  # X1 round 2: a strike touches its own struck text (and nothing else)
ERR_TINT = '#FCE8E5'                            # S1r: the errors' surface (NPG red at 0.13 over white)
ERR_TINT_GROUPS = {'a_flag', 'c_found'}         # S1r: a's Flag box and the loop's errors step (W1: panel c), nothing else
CAT_TINT = '#E0F4F1'                            # T1: the catalogue's tint (NPG green at 0.12 over white)
CAT_TINT_GROUPS = {'a_catalog', 'b_store', 'b_record'}   # T1: the two CatLog stores; U1, W1: the record's header strip (panel b)
CODE_LINE = '#8491B4'                           # R5: code's line colour (NPG slate): its outlines, and its four arrows in c's record
CODE_ARROW_GROUPS = {'c_record_code'}           # R5: the one place a mark is filled in code's line colour
ARROW_FILLS = (INK, LEARN, OUT_GREY, RED, NAVY, CODE_LINE)  # arrows are drawn in these only (S1: red; P1: navy, the databases'; R5: slate, code's)
TRAIL_GREY = '#666666'                          # W1: the neutral grey of dashed lines: b's trail and its one head
TRAIL_GROUPS = {'b_trail'}
ARROW_GROUPS_Q2 = {'a_learning', 'a_exit', 'c_loop', 'a_errors', 'a_databases_arrow', 'c_record_code'}   # checker: groups of arrows, held to the
#                                                 in-pieces rule too (S1: a_errors, d_errors_in)
IMAGE_GROUP = 'b_record_enzyme'                 # L2: the one picture allowed, the enzyme in b's record (S1: c_link_structure)
IMAGE_SHA256 = '5b5ba2995c2fce9443adaecd83d98c266400b5ebd5b347fccd783d05148bb58f'   # M2: P00805_AF_v6_N270_slate_600.png, S1r's
#                                                 slate picture (T1 round 2's grey one was 095abb24...)
EDGE_MM = 1.76                                  # the least white between ink and the page edge
KEY_FILLS = {'#C8E8E0': 'agent', '#D3D7E4': 'code', '#DFD7CE': 'people'}   # T1 round 2: mint at alpha 0.5, slate 0.36, tan 0.40
#                                                 (design A: all three at 0.5; slate and tan now as light as mint reads)
NEUTRAL_FILLS = {'#FFFFFF': 'white', '#E9E9E9': 'plate grey', '#D9D9D9': 'outside reviews (d split)'}   # R5: no band grey (#F2F2F2)
PS_FACES = {'ArialMT': ('normal', 'normal'), 'Arial-BoldMT': ('bold', 'normal'), 'Arial-ItalicMT': ('normal', 'italic'),
            'Arial-BoldItalicMT': ('bold', 'italic')}
AREA_MIN = 40.0                                  # pt^2: smaller closed shapes are icon parts or arrowheads


def panel_of(group):
    for p in 'abcd':
        if group.startswith(p + '_') or group == 'panel_letter_' + p:
            return p
    if group == 'zoom_lines':
        return 'b'
    if group == 'zoom_lines_d':
        return 'd'
    return '-'


class Metrics:
    """Advance widths and glyph ink boxes of one Arial face, in font units."""

    def __init__(self, path):
        f = TTFont(path)
        self.upem = f['head'].unitsPerEm
        self.cmap = f.getBestCmap()
        self.hmtx = f['hmtx'].metrics
        self.glyf = f['glyf']
        self.cache = {}

    def char(self, ch):
        if ch in self.cache:
            return self.cache[ch]
        g = self.cmap.get(ord(ch))
        if g is None:
            out = None
        else:
            adv = self.hmtx[g][0]
            gl = self.glyf[g]
            box = None
            if getattr(gl, 'numberOfContours', 0) != 0 and hasattr(gl, 'xMin'):
                box = (gl.xMin, gl.yMin, gl.xMax, gl.yMax)
            out = (adv, box)
        self.cache[ch] = out
        return out


FACES = {k: Metrics(os.path.join(FONT_DIR, v)) for k, v in FONT_FILES.items()}


def overlap(a, b, tol=0.0):
    return a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol


def gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0)
    dy = max(b[1] - a[3], a[1] - b[3], 0)
    return math.hypot(dx, dy)


def union(boxes):
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


STYLE_KEYS = ('font-family', 'font-size', 'font-weight', 'font-style', 'fill', 'stroke', 'stroke-width',
              'stroke-linecap', 'text-anchor', 'stroke-dasharray')


def style_of(el, parent):
    st = dict(parent)
    for k in STYLE_KEYS:
        if el.get(k) is not None:
            st[k] = el.get(k)
    for decl in (el.get('style') or '').split(';'):
        if ':' in decl:
            k, v = decl.split(':', 1)
            st[k.strip()] = v.strip()
    return st


class Glyph:
    def __init__(self, ch, x, y, size, st, box, adv, text_id, group):
        self.ch, self.x, self.y, self.size, self.st = ch, x, y, size, st
        self.box, self.adv, self.text_id, self.group = box, adv, text_id, group


def layout_text(el, st0, group, text_id, problems):
    """Lay out one <text> element run by run (cumulative tspan dy, inherited styles); returns its glyphs."""
    x0, y0 = float(el.get('x', 0)), float(el.get('y', 0))
    runs = []                                    # (text, style, dy before it, dx before it)

    def walk(node, st):
        if node.text:
            runs.append((node.text, st, 0.0, 0.0))
        for ch in node:
            if ch.tag != NS + 'tspan':
                problems['other'].append(f'{group}: <{ch.tag.replace(NS, "")}> inside <text>')
                continue
            cst = style_of(ch, st)
            dy, dx = float(ch.get('dy', 0) or 0), float(ch.get('dx', 0) or 0)
            if ch.get('x') is not None or ch.get('y') is not None:
                problems['other'].append(f'{group}: tspan with absolute x/y (not handled)')
            first = True
            if ch.text:
                runs.append((ch.text, cst, dy, dx))
                first = False
            for sub in ch:
                walk(sub, cst)
            if first and (dy or dx):
                runs.append(('', cst, dy, dx))
            if ch.tail:
                runs.append((ch.tail, st, 0.0, 0.0))

    walk(el, st0)
    pen_x, pen_y = x0, y0
    glyphs = []
    for text, st, dy, dx in runs:
        pen_x += dx
        pen_y += dy
        size = float(st.get('font-size', 16))
        weight = 'bold' if st.get('font-weight', 'normal') in ('bold', '700', '600', '800', '900') else 'normal'
        style = 'italic' if st.get('font-style', 'normal') in ('italic', 'oblique') else 'normal'
        fam = st.get('font-family', '').strip().strip('"\'')
        if fam in PS_FACES:                    # v8: Arial's faces named by PostScript name (for Illustrator)
            weight, style = PS_FACES[fam]
        face = FACES[(weight, style)]
        s = size / face.upem
        for ch in text:
            got = face.char(ch)
            if got is None:
                problems['glyph'].append(f'{group}: {ch!r} (U+{ord(ch):04X}) not in Arial {weight} {style}')
                adv, b = 0.5 * face.upem, None
            else:
                adv, b = got
            box = (pen_x + b[0] * s, pen_y - b[3] * s, pen_x + b[2] * s, pen_y - b[1] * s) if b else None
            glyphs.append(Glyph(ch, pen_x, pen_y, size, dict(st, **{'_weight': weight, '_style': style}),
                                box, adv * s, text_id, group))
            pen_x += adv * s
    anchor = st0.get('text-anchor', 'start')
    width = pen_x - x0
    shift = {'start': 0, 'middle': -width / 2, 'end': -width}.get(anchor, 0)
    if el.get('transform'):
        problems['other'].append(f'{group}: text transform {el.get("transform")} (positions ignore it)')
    for g in glyphs:
        if g.box:
            g.box = (g.box[0] + shift, g.box[1], g.box[2] + shift, g.box[3])
        g.x += shift
    return glyphs


# ------------------------------------------------------------------ paths: lines, arcs and curves, as point lists
def _arc_points(p0, rx, ry, phi, large, sweep, p1, n=24):
    """Points along an SVG elliptical arc (endpoint parameterization, SVG 1.1 F.6.5)."""
    x1, y1 = p0
    x2, y2 = p1
    if rx == 0 or ry == 0:
        return [p1]
    rx, ry = abs(rx), abs(ry)
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = c * dx + s * dy, -s * dx + c * dy
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    k = math.sqrt(max(num / den, 0)) if den else 0
    if large == sweep:
        k = -k
    cxp, cyp = k * rx * y1p / ry, -k * ry * x1p / rx
    cx, cy = c * cxp - s * cyp + (x1 + x2) / 2, s * cxp + c * cyp + (y1 + y2) / 2

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a

    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    pts = []
    for i in range(1, n + 1):
        t = t1 + dt * i / n
        xe, ye = rx * math.cos(t), ry * math.sin(t)
        pts.append((c * xe - s * ye + cx, s * xe + c * ye + cy))
    return pts


def _bez(p, n=16):
    out = []
    for i in range(1, n + 1):
        t = i / n
        if len(p) == 3:
            x = (1 - t) ** 2 * p[0][0] + 2 * (1 - t) * t * p[1][0] + t * t * p[2][0]
            y = (1 - t) ** 2 * p[0][1] + 2 * (1 - t) * t * p[1][1] + t * t * p[2][1]
        else:
            x = ((1 - t) ** 3 * p[0][0] + 3 * (1 - t) ** 2 * t * p[1][0] + 3 * (1 - t) * t * t * p[2][0]
                 + t ** 3 * p[3][0])
            y = ((1 - t) ** 3 * p[0][1] + 3 * (1 - t) ** 2 * t * p[1][1] + 3 * (1 - t) * t * t * p[2][1]
                 + t ** 3 * p[3][1])
        out.append((x, y))
    return out


def path_subpaths(d):
    """Subpaths of an SVG path as point lists (curves and arcs sampled), each with closed flag and its vertices."""
    toks = re.findall(r'[MLHVZCSQTAmlhvzcsqta]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', d)
    subs, pts, verts = [], [], []
    cur = start = (0.0, 0.0)
    cmd, i, prev_ctrl = None, 0, None

    def num():
        nonlocal i
        v = float(toks[i])
        i += 1
        return v

    def flush(closed):
        nonlocal pts, verts
        if pts:
            subs.append(dict(pts=pts, closed=closed, verts=verts))
        pts, verts = [], []

    while i < len(toks):
        t = toks[i]
        if re.match(r'[A-Za-z]', t):
            cmd = t
            i += 1
            if cmd in 'Zz':
                if pts:
                    pts.append(start)
                flush(True)
                cur = start
                prev_ctrl = None
                continue
            continue
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = cur if rel else (0.0, 0.0)
        if C == 'M':
            x, y = num() + ox, num() + oy
            flush(False)
            pts, verts, start, cur = [(x, y)], [(x, y)], (x, y), (x, y)
            cmd = 'l' if rel else 'L'
            prev_ctrl = None
        elif C == 'L':
            cur = (num() + ox, num() + oy)
            pts.append(cur)
            verts.append(cur)
            prev_ctrl = None
        elif C == 'H':
            cur = (num() + (cur[0] if rel else 0), cur[1])
            pts.append(cur)
            verts.append(cur)
            prev_ctrl = None
        elif C == 'V':
            cur = (cur[0], num() + (cur[1] if rel else 0))
            pts.append(cur)
            verts.append(cur)
            prev_ctrl = None
        elif C == 'C':
            c1 = (num() + ox, num() + oy)
            c2 = (num() + ox, num() + oy)
            p = (num() + ox, num() + oy)
            pts += _bez([cur, c1, c2, p])
            verts.append(p)
            prev_ctrl, cur = c2, p
        elif C == 'S':
            c1 = (2 * cur[0] - prev_ctrl[0], 2 * cur[1] - prev_ctrl[1]) if prev_ctrl else cur
            c2 = (num() + ox, num() + oy)
            p = (num() + ox, num() + oy)
            pts += _bez([cur, c1, c2, p])
            verts.append(p)
            prev_ctrl, cur = c2, p
        elif C == 'Q':
            c1 = (num() + ox, num() + oy)
            p = (num() + ox, num() + oy)
            pts += _bez([cur, c1, p])
            verts.append(p)
            prev_ctrl, cur = c1, p
        elif C == 'T':
            c1 = (2 * cur[0] - prev_ctrl[0], 2 * cur[1] - prev_ctrl[1]) if prev_ctrl else cur
            p = (num() + ox, num() + oy)
            pts += _bez([cur, c1, p])
            verts.append(p)
            prev_ctrl, cur = c1, p
        elif C == 'A':
            rx, ry, phi, large, sweep = num(), num(), num(), int(num()), int(num())
            p = (num() + ox, num() + oy)
            pts += _arc_points(cur, rx, ry, phi, large, sweep, p)
            verts.append(p)
            prev_ctrl, cur = None, p
        else:
            raise ValueError(cmd)
    flush(False)
    return subs


def stroke_segs(pts):
    return list(zip(pts, pts[1:]))


def seg_hits_box(p, q, box, half):
    """Does segment p-q, thickened by `half`, touch box (x0, y0, x1, y1)? Liang-Barsky on the inflated box."""
    x0, y0, x1, y1 = box[0] - half, box[1] - half, box[2] + half, box[3] + half
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pp == 0:
            if qq < 0:
                return False
        else:
            r = qq / pp
            if pp < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                return False
    return True


def point_in_poly(x, y, poly):
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1:
            inside = not inside
    return inside


def poly_area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


def colour(v):
    return (v or '').upper()


def arrow_head(verts):
    """The head of an arrow polygon (build_figure_v4.Fig.arrow): the vertex whose two neighbours stand symmetric
    about it at an acute angle, both at least 3 pt away. Returns (length, width, tip) in pt, or None."""
    v = verts[:-1] if len(verts) > 1 and verts[0] == verts[-1] else verts
    n = len(v)
    best = None
    for i in range(n):
        a, t, b = v[i - 1], v[i], v[(i + 1) % n]
        da, db = math.dist(a, t), math.dist(b, t)
        if min(da, db) < 3 or abs(da - db) > 0.05:
            continue
        cosang = ((a[0] - t[0]) * (b[0] - t[0]) + (a[1] - t[1]) * (b[1] - t[1])) / (da * db)
        if cosang < 0.3:                          # wider than about 73 degrees: not a head
            continue
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        cand = (math.dist(t, mid), math.dist(a, b), t)
        if best is None or cand[0] > best[0]:
            best = cand
    return best


def main():
    tree = ET.parse(SVG)
    root = tree.getroot()
    raw = open(SVG, encoding='utf-8').read()
    vb = [float(v) for v in root.get('viewBox').split()]
    X0, Y0, W, H = vb      # v8 final: the viewBox starts at minus the page margin
    wmm = float(root.get('width', '0').replace('mm', '') or 0)
    hmm = float(root.get('height', '0').replace('mm', '') or 0)
    problems = collections.defaultdict(list)
    glyphs, marks, groups, colours = [], [], [], collections.Counter()
    images = []                                    # S1
    text_owner = {}
    for el in root.iter():
        tag = el.tag.replace(NS, '')
        if tag in ('filter', 'mask', 'clipPath', 'use', 'foreignObject', 'pattern', 'linearGradient',
                   'radialGradient', 'line', 'polyline', 'polygon'):
            problems['banned'].append(f'<{tag}>')
    # S1: the attribute scan reads the file with the picture's PNG data set aside
    bare = re.sub(r'(xlink:)?href="data:image/png;base64,[A-Za-z0-9+/=]+"', 'href=""', raw)
    for attr in ('opacity', 'text-decoration', 'clip-path', 'filter=', 'mask='):
        if attr in bare:
            problems['banned'].append(f'attribute {attr!r} present')
    loose = [el.tag.replace(NS, '') for el in root if el.tag != NS + 'g' and el.get('id') != 'background']
    if loose:
        problems['banned'].append(f'drawn outside a named group: {loose}')

    def visit(el, st, group):
        tag = el.tag.replace(NS, '')
        st = style_of(el, st)
        if el.get('transform'):
            problems['other'].append(f'{group}: transform {el.get("transform")} (positions ignore it)')
        if tag == 'g':
            gid = el.get('id') or group
            if el.get('id'):
                groups.append(el.get('id'))
            for ch in el:
                visit(ch, st, gid)
            return
        if tag == 'image':                         # S1: the one picture, checked after the walk
            images.append(dict(group=group, el=el))
            return
        if tag == 'text':
            tid = len(text_owner)
            text_owner[tid] = group
            gl = layout_text(el, st, group, tid, problems)
            glyphs.extend(gl)
            for g in gl:
                if not g.ch.isspace():
                    colours['text ' + colour(g.st.get('fill', '#000000'))] += 1
            return
        stroke = st.get('stroke', 'none')
        fill = st.get('fill', '#000000')
        sw = float(st.get('stroke-width', 1)) if stroke not in (None, 'none') else 0.0
        if stroke not in (None, 'none'):
            colours['stroke ' + colour(stroke)] += 1
        if fill not in (None, 'none'):
            colours['fill ' + colour(fill)] += 1
        base = dict(group=group, stroke=stroke, sw=sw, fill=fill, tag=tag)
        if tag == 'path':
            for sp in path_subpaths(el.get('d', '')):
                pts = sp['pts']
                box = union([(x - sw / 2, y - sw / 2, x + sw / 2, y + sw / 2) for x, y in pts])
                marks.append(dict(base, kind='path', pts=pts, closed=sp['closed'], verts=sp['verts'], box=box))
        elif tag == 'circle':
            cx, cy, r = float(el.get('cx')), float(el.get('cy')), float(el.get('r'))
            pts = [(cx + r * math.cos(2 * math.pi * k / 32), cy + r * math.sin(2 * math.pi * k / 32))
                   for k in range(33)]
            marks.append(dict(base, kind='circle', pts=pts, closed=True, verts=pts,
                              box=(cx - r - sw / 2, cy - r - sw / 2, cx + r + sw / 2, cy + r + sw / 2)))
        elif tag == 'ellipse':
            cx, cy = float(el.get('cx')), float(el.get('cy'))
            rx, ry = float(el.get('rx')), float(el.get('ry'))
            pts = [(cx + rx * math.cos(2 * math.pi * k / 48), cy + ry * math.sin(2 * math.pi * k / 48))
                   for k in range(49)]
            marks.append(dict(base, kind='ellipse', pts=pts, closed=True, verts=pts,
                              box=(cx - rx - sw / 2, cy - ry - sw / 2, cx + rx + sw / 2, cy + ry + sw / 2)))
        elif tag == 'rect':
            x, y = float(el.get('x', 0)), float(el.get('y', 0))
            w, h = float(el.get('width')), float(el.get('height'))
            pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
            marks.append(dict(base, kind='rect', id=el.get('id'), pts=pts, closed=True, verts=pts,
                              box=(x - sw / 2, y - sw / 2, x + w + sw / 2, y + h + sw / 2), wh=(w, h)))
            if min(w, h) < MIN_LINE and fill not in (None, 'none'):
                problems['line'].append(f'{group}: filled rect {w:g} x {h:g} pt (thinner than {MIN_LINE} pt)')
        if stroke not in (None, 'none') and sw < MIN_LINE:
            problems['line'].append(f'{group}: <{tag}> stroke-width {sw:g} pt (under {MIN_LINE} pt)')
        for ch in el:
            visit(ch, st, group)

    for el in root:
        visit(el, {}, el.get('id') or '(root)')

    # S1: the one picture: in its group, embedded PNG data whose sha256 is the prepared picture's, placed by x, y, width
    # and height (no transform); it joins the marks for the artboard check, and no text ink may lie on it (below)
    if len(images) != 1:                           # L2: exactly one picture, the enzyme of b's record (R1 allowed none)
        problems['banned'].append(f'{len(images)} <image> elements (exactly one is allowed)')
    image_boxes = []
    for im in images:
        el = im['el']
        href = el.get('{http://www.w3.org/1999/xlink}href') or el.get('href') or ''
        if im['group'] != IMAGE_GROUP:
            problems['banned'].append(f'<image> in {im["group"]} (allowed only in {IMAGE_GROUP})')
        if not href.startswith('data:image/png;base64,'):
            problems['banned'].append('<image> is not embedded PNG data')
        else:
            import base64
            import hashlib
            dig = hashlib.sha256(base64.b64decode(href.split(',', 1)[1])).hexdigest()
            if dig != IMAGE_SHA256:
                problems['banned'].append(f'<image> data sha256 {dig[:12]}... is not the prepared picture')
        if el.get('transform'):
            problems['banned'].append('<image> with a transform')
        x, y, w, h = (float(el.get(k)) for k in ('x', 'y', 'width', 'height'))
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
        marks.append(dict(group=im['group'], stroke='none', sw=0.0, fill='none', tag='image', kind='image', pts=pts,
                          closed=True, verts=pts, box=(x, y, x + w, y + h)))
        image_boxes.append((im['group'], (x, y, x + w, y + h)))

    # 1. text size (5-7 pt; panel letters 8 pt bold black)
    sizes = collections.Counter(g.size for g in glyphs if not g.ch.isspace())
    for g in glyphs:
        if g.ch.isspace():
            continue
        if g.size < MIN_PT - 1e-9:
            problems['size'].append(f'{g.group}: {g.ch!r} at {g.size:g} pt')
        elif g.size > MAX_PT + 1e-9:
            letter = (g.group.startswith('panel_letter') and g.size == LETTER_PT and g.st['_weight'] == 'bold'
                      and colour(g.st.get('fill')) == '#000000' and g.ch in 'abcd')
            if not letter:
                problems['size'].append(f'{g.group}: {g.ch!r} at {g.size:g} pt (over {MAX_PT:g} pt)')
    # 2. fonts
    fams = collections.Counter(g.st.get('font-family', '(none)') for g in glyphs)
    for fam, n in fams.items():
        if fam.strip().strip('"\'') not in ('Arial',) + tuple(PS_FACES):
            problems['font'].append(f'font-family {fam!r} on {n} characters')
    weights = collections.Counter((g.st['_weight'], g.st['_style']) for g in glyphs if not g.ch.isspace())

    by_text = collections.defaultdict(list)
    for g in glyphs:
        by_text[g.text_id].append(g)
    tboxes = {t: union([g.box for g in gs]) for t, gs in by_text.items()}
    tstring = {t: ''.join(g.ch for g in gs) for t, gs in by_text.items()}

    # 3. overlapping text (glyph ink of different <text> elements); near misses as context
    near = []
    for a, b in itertools.combinations(sorted(tboxes), 2):
        A, B = tboxes[a], tboxes[b]
        if not A or not B or gap(A, B) > NEAR:
            continue
        hit, dmin = None, float('inf')
        for ga in by_text[a]:
            if not ga.box:
                continue
            for gb in by_text[b]:
                if not gb.box:
                    continue
                if overlap(ga.box, gb.box):
                    hit = (ga, gb)
                    break
                dmin = min(dmin, gap(ga.box, gb.box))
            if hit:
                break
        if hit:
            problems['overlap'].append(f'{text_owner[a]} "{tstring[a][:40]}" overlaps {text_owner[b]} '
                                       f'"{tstring[b][:40]}" (at {hit[0].ch!r} / {hit[1].ch!r})')
        elif dmin < NEAR:
            near.append(f'{dmin:.2f} pt: {text_owner[a]} "{tstring[a][:32]}" / {text_owner[b]} "{tstring[b][:32]}"')

    # 4. text touched by a stroke, an arrow polygon or a filled icon shape (a filled area behind text is not a touch)
    strikes = []                                   # X1 round 2: the strikes, as context
    for mk in marks:
        for t, gs in by_text.items():
            B = tboxes[t]
            if not B or not overlap(mk['box'], B, -0.01):
                continue
            hits = []
            for g in gs:
                if not g.box:
                    continue
                touched = False
                if mk['stroke'] not in (None, 'none') and any(
                        seg_hits_box(p, q, g.box, mk['sw'] / 2) for p, q in stroke_segs(mk['pts'])):
                    touched = True
                elif mk['fill'] not in (None, 'none') and mk['closed'] and mk['kind'] != 'rect' \
                        and poly_area(mk['pts'][:-1]) < 400:
                    # a filled shape smaller than a card: an arrow or an icon part
                    cxg, cyg = (g.box[0] + g.box[2]) / 2, (g.box[1] + g.box[3]) / 2
                    if point_in_poly(cxg, cyg, mk['pts'][:-1]) or any(
                            seg_hits_box(p, q, g.box, 0) for p, q in stroke_segs(mk['pts'])):
                        touched = True
                if touched:
                    hits.append(g.ch)
            if hits and text_owner[t] == 'a_tags':   # a tag's letter sits on its own ink disc, over what the disc hides
                continue
            if hits and mk['group'] in STRIKE_GROUPS and text_owner[t] == mk['group'] and mk['kind'] == 'path' \
                    and not mk['closed'] and mk['stroke'] not in (None, 'none'):   # X1 round 2: a strike on its own text
                strikes.append(f'{mk["group"]}: {mk["stroke"]} stroke across "{tstring[t][:24]}" at {"".join(hits)[:12]!r}')
                continue
            if hits:
                problems['touch'].append(f'{mk["group"]} {mk["kind"]} ({mk["stroke"] if mk["sw"] else mk["fill"]}) '
                                         f'touches {text_owner[t]} "{tstring[t][:36]}" at {"".join(hits)[:12]!r}')

    for grp_i, ib in image_boxes:                      # S1: no text ink on the picture
        for t, gs in by_text.items():
            hit = [g.ch for g in gs if g.box and overlap(g.box, ib)]
            if hit:
                problems['touch'].append(f'{grp_i} picture under {text_owner[t]} "{tstring[t][:36]}" at {"".join(hit)[:12]!r}')

    # 5. outside the artboard (text ink and marks, strokes included)
    def outside(box):              # v8 final: ink must keep 1.5 mm from every page edge
        m = EDGE_MM * MM - 0.005
        return box[0] < X0 + m or box[1] < Y0 + m or box[2] > X0 + W - m or box[3] > Y0 + H - m

    for t, B in tboxes.items():
        if B and outside(B):
            problems['outside'].append(f'{text_owner[t]} "{tstring[t][:40]}" ink box '
                                       f'({B[0]:.2f}, {B[1]:.2f}, {B[2]:.2f}, {B[3]:.2f})')
    for mk in marks:
        if mk.get('id') != 'background' and outside(mk['box']):
            problems['outside'].append(f'{mk["group"]} {mk["kind"]} box ({", ".join(f"{v:.2f}" for v in mk["box"])})')
    allbox = union([b for b in tboxes.values()] + [m['box'] for m in marks if m.get('id') != 'background'])

    # 6. arrows: closed INK polygons with a head
    arrows = []
    for mk in marks:
        if mk['kind'] == 'path' and mk['closed'] and colour(mk['fill']) in ARROW_FILLS and mk['sw'] == 0:
            hd = arrow_head(mk['verts'])
            if hd and len(mk['verts']) >= 7:
                L = max(math.dist(p, q) for p, q in itertools.combinations(mk['verts'], 2))
                arrows.append(dict(group=mk['group'], head_mm=hd[0] / MM, width_mm=hd[1] / MM, tip=hd[2],
                                   span_mm=L / MM, n=len(mk['verts'])))
    for a in arrows:
        if not HEAD_MM[0] <= a['head_mm'] <= HEAD_MM[1]:
            problems['arrow'].append(f"{a['group']}: head {a['head_mm']:.2f} mm at {a['tip']}")
    open_heads = [mk for mk in marks if mk['kind'] == 'path' and not mk['closed'] and mk['stroke'] not in (None, 'none')
                  and colour(mk['stroke']) in ARROW_FILLS
                  and (mk['group'].endswith('arrows') or mk['group'] in ARROW_GROUPS_Q2)]
    for mk in open_heads:
        problems['arrow'].append(f'{mk["group"]}: an open stroked path among the arrows (line plus head?)')
    # W1: the trail, a dashed line with one head, both in the neutral grey: its own group, one head, the arrows' size
    for grp_t in sorted(TRAIL_GROUPS):
        tm = [mk for mk in marks if mk['group'] == grp_t]
        heads = [mk for mk in tm if mk['kind'] == 'path' and mk['closed']]
        lines_ = [mk for mk in tm if mk['kind'] == 'path' and not mk['closed']]
        if len(heads) != 1 or not lines_ or len(heads) + len(lines_) != len(tm):
            problems['arrow'].append(f'{grp_t}: {len(lines_)} open path(s), {len(heads)} head(s), {len(tm)} marks (a dashed line and one head)')
        for mk in lines_:
            if colour(mk['stroke']) != TRAIL_GREY or mk['fill'] not in (None, 'none'):
                problems['arrow'].append(f'{grp_t}: a line that is not stroked in the neutral grey')
        for mk in heads:
            hd = arrow_head(mk['verts'])
            if colour(mk['fill']) != TRAIL_GREY or mk['sw'] != 0 or not hd or not HEAD_MM[0] <= hd[0] / MM <= HEAD_MM[1]:
                problems['arrow'].append(f'{grp_t}: head {"%.2f mm" % (hd[0] / MM) if hd else "not found"} ({mk["fill"]})')
            else:
                tip = hd[2]
                if not any(math.dist(tip, p) <= HEAD_MM[1] * MM + 0.01 for l_ in lines_ for p in (l_['pts'][0], l_['pts'][-1])):
                    problems['arrow'].append(f'{grp_t}: the head does not end the line')
                arrows.append(dict(group=grp_t, head_mm=hd[0] / MM, width_mm=hd[1] / MM, tip=tip,
                                   span_mm=max(math.dist(p, q) for p, q in itertools.combinations(lines_[0]['pts'] + [tip], 2)) / MM, n=3))
    for mk in marks:
        if mk['kind'] == 'path' and mk['closed'] and colour(mk['fill']) == TRAIL_GREY and mk['group'] not in TRAIL_GROUPS:
            problems['arrow'].append(f'{mk["group"]}: a mark filled in the neutral grey (only the trail\'s head)')

    align = []                                 # v6: no text-layer row, no red '8's

    # 8. colour meanings
    for mk in marks:
        cols = {colour(mk[k]) for k in ('fill', 'stroke') if mk[k] not in (None, 'none')}
        if cols & GREENS and mk['group'] not in GREEN_MARK_GROUPS:
            problems['colour'].append(f'{mk["group"]}: green {mk["kind"]} (green marks only the value and the '
                                      f'catalogue)')
        if LEARN in cols and mk['group'] not in LEARN_GROUPS:
            problems['colour'].append(f'{mk["group"]}: cyan {mk["kind"]} (cyan marks only learning)')
        if OUT_GREY in cols and mk['group'] not in OUT_GROUPS:
            problems['colour'].append(f'{mk["group"]}: exit grey {mk["kind"]} (only the arrow out of the method)')
        if NAVY in cols and mk['group'] not in DB_GROUPS:                       # P1
            problems['colour'].append(f'{mk["group"]}: navy {mk["kind"]} (navy marks only the databases)')
        if RED in cols and mk['group'] not in RED_GROUPS:                       # S1
            problems['colour'].append(f'{mk["group"]}: red {mk["kind"]} (red marks only errors)')
        if colour(mk['fill']) == CODE_LINE and mk['group'] not in CODE_ARROW_GROUPS:   # R5
            problems['colour'].append(f'{mk["group"]}: {mk["kind"]} filled in code\'s line colour (only its arrows in c\'s record)')
        if mk['group'] in CODE_ARROW_GROUPS and not (colour(mk['fill']) == CODE_LINE and mk['kind'] == 'path' and mk['closed']
                                                     and arrow_head(mk['verts'])):   # R5: that group holds slate arrows only
            problems['colour'].append(f'{mk["group"]}: a mark that is not one of code\'s slate arrows')
    for g in glyphs:                               # checker: cyan (3.2:1) and the exit grey (2.1:1) never colour text
        if not g.ch.isspace() and colour(g.st.get('fill', '#000000')) in (LEARN, OUT_GREY):
            problems['colour'].append(f'{g.group}: text {g.ch!r} in {colour(g.st.get("fill"))} (labels stay ink or grey)')
        if not g.ch.isspace() and colour(g.st.get('fill', '#000000')) == RED and g.group not in RED_TEXT_GROUPS:
            problems['colour'].append(f'{g.group}: text {g.ch!r} in red (only the errors labels of a)')
    import colorsys
    for k_ in colours:                             # checker: no red of any shade, in any mark or text (S1: but NPG red,
        c_ = k_.split()[-1]                        # whose places are held to RED_GROUPS above)
        if c_ == RED:
            continue
        if re.fullmatch(r'#[0-9A-F]{6}', c_):
            h_, s_, v_ = colorsys.rgb_to_hsv(*[int(c_[i:i + 2], 16) / 255 for i in (1, 3, 5)])
            if s_ >= 0.3 and v_ >= 0.3 and not 20 < h_ * 360 < 340:
                problems['colour'].append(f'{k_}: a red (hue {h_ * 360:.0f}) is drawn')
    fills_seen = collections.defaultdict(set)
    tint_boxes = set()                             # S1r: the groups whose box has the tint and a red outline
    for mk in marks:
        if mk.get('id') == 'background' or mk['fill'] in (None, 'none') or not mk['closed']:
            continue
        area = poly_area(mk['pts'][:-1]) if mk['kind'] != 'rect' else mk['wh'][0] * mk['wh'][1]
        if area < AREA_MIN:
            continue
        f = colour(mk['fill'])
        if f == INK:                              # arrows and icon ink, not an area colour
            continue
        if f in (LEARN, OUT_GREY, RED, NAVY) and arrow_head(mk['verts']) and len(mk['verts']) >= 7:   # Q2, S1, P1: an arrow
            continue
        if f == DB_TINT:                          # P1: the Databases card's strip, nowhere else
            if mk['group'] not in DB_TINT_GROUPS:
                problems['colour'].append(f'{mk["group"]}: the databases\' tint {f} outside a_databases and b_sources')
            continue
        fills_seen[f].add(mk['group'])
        if f == CAT_TINT:                         # T1: the catalogue's two boxes only
            if mk['group'] not in CAT_TINT_GROUPS:
                problems['colour'].append(f'{mk["group"]}: the catalogue\'s tint {f} outside a_catalog, b_store and b_record')
            continue
        if f == ERR_TINT:                         # S1r: the errors' surface, in its two places only (icon parts on it
            if mk['group'] not in ERR_TINT_GROUPS:  # take its tint too); each place's box outlined in red, below
                problems['colour'].append(f'{mk["group"]}: the errors\' tint {f} outside a_flag and c_found')
            elif colour(mk['stroke']) == RED and area > 400:
                tint_boxes.add(mk['group'])
            continue
        if f not in KEY_FILLS and f not in NEUTRAL_FILLS and not (f in GREENS and mk['group'] in GREEN_MARK_GROUPS):
            problems['colour'].append(f'{mk["group"]}: area fill {f} ({area:.0f} pt²) is not a key colour, white, '
                                      f'the plate grey or the database tint')

    for grp_t in sorted(ERR_TINT_GROUPS - tint_boxes):   # S1r
        problems['colour'].append(f'{grp_t}: no box in the errors\' tint with a red outline')

    # 9. size targets
    b_out = [mk for mk in marks if mk['group'] == 'b_outline' and mk['kind'] == 'rect']
    b_mm = b_out[0]['wh'][1] / MM if b_out else float('nan')
    targets = [
        (abs(wmm - WIDTH_MM) < 0.05 and abs(wmm * MM - W) < 0.05, f'width {wmm:g} mm (183 mm), viewBox {W:g} pt'),
        (hmm <= HMAX_MM and abs(hmm * MM - H) < 0.05, f'height {hmm:g} mm (the brief: at most {HMAX_MM:g} mm; '
                                                         f'{"within" if hmm <= H_AIM_MM else "over"} Nature\'s {H_AIM_MM:g} mm)'),
    ]
    letters = [(g.group, g.ch, g.size, g.st['_weight'], round(g.y, 2)) for g in glyphs if g.group.startswith('panel_letter')
               and g.size == LETTER_PT]
    titles = {g.group: (g.size, g.st['_weight'], round(g.y, 2)) for g in glyphs if g.group.startswith('panel_letter')
              and g.size != LETTER_PT and not g.ch.isspace()}
    targets.append((len(letters) == 3 and [c for _, c, *_ in letters] == ['a', 'b', 'c'] and   # W1: three panels, a, b, c
                    all(w == 'bold' for *_, w, _ in letters) and
                    all(titles.get(gp, (0, '', 0)) == (7.0, 'bold', y) for gp, _, _, _, y in letters),
                    f'panel letters {[(c, s, w) for _, c, s, w, _ in letters]}, titles 7 pt bold on their baseline: '
                    f'{titles}'))

    words = collections.Counter()
    for t, s in tstring.items():
        words[panel_of(text_owner[t])] += sum(1 for w in s.split() if any(c.isalnum() for c in w))

    # 16 Nov, the owner's rule: built like a person draws it. The drawn elements and the groups they sit in; a label
    # split into one-glyph texts; the largest set of same-style marks inside one group (context: one compound path?)
    drawn = collections.Counter(el.tag.replace(NS, '') for el in root.iter() if el.tag.replace(NS, '') in DRAWN)
    n_drawn = sum(drawn.values())
    if n_drawn > MAX_OBJECTS:
        problems['objects'].append(f'{n_drawn} drawn elements, over {MAX_OBJECTS}: fold same-style marks into one '
                                   'compound path (a dense cloud into one picture under its labels)')
    for t, s in sorted(tstring.items()):
        if len(s.strip()) == 1 and not text_owner[t].startswith('panel_letter'):
            problems['objects'].append(f'{text_owner[t]}: a text of one glyph, {s.strip()!r} (one text per label)')
    top_groups = [el for el in root if el.tag == NS + 'g' and el.get('id') != 'background']
    sub_named = sum(1 for g in top_groups for el in g.iter(NS + 'g') if el is not g and el.get('id'))
    parent = {c: p for p in root.iter() for c in p}

    def named(el):                              # the nearest group with an id, for a group that has none
        while el is not None and not el.get('id'):
            el = parent.get(el)
        return el.get('id') if el is not None else '(root)'

    same_style = (0, '')
    for g in root.iter(NS + 'g'):
        sets = collections.Counter(
            (el.tag, tuple(el.get(k) for k in ('fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'style')))
            for el in g if el.tag.replace(NS, '') in DRAWN and el.tag != NS + 'text')
        if sets and max(sets.values()) > same_style[0]:
            same_style = (max(sets.values()), g.get('id') or f'an unnamed group in {named(g)}')

    # report
    print(f'Fig. 1 design A style check: {SVG}')
    print(f'Artboard: {wmm:g} x {hmm:g} mm; viewBox {W:g} x {H:g} pt. Everything drawn spans x {allbox[0]:.2f}-'
          f'{allbox[2]:.2f}, y {allbox[1]:.2f}-{allbox[3]:.2f} pt.')
    print(f'Elements: {len(by_text)} text elements ({sum(1 for g in glyphs if not g.ch.isspace())} characters), '
          f'{len(marks)} marks; {len(groups)} named groups.')
    print('Text sizes (pt: characters): ' + ', '.join(f'{k:g}: {v}' for k, v in sorted(sizes.items())))
    print('Faces: ' + ', '.join(f'Arial {w}{" " + s if s != "normal" else ""}: {n}' for (w, s), n in
                                sorted(weights.items())) + f'; families: {dict(fams)}')
    sws = collections.Counter(round(m['sw'], 3) for m in marks if m['stroke'] not in (None, 'none'))
    print('Stroke widths (pt: marks): ' + ', '.join(f'{k:g}: {v}' for k, v in sorted(sws.items())))
    print('Area fills (colour: groups): ' + '; '.join(f'{k} {sorted(v)}' for k, v in sorted(fills_seen.items())))
    print('Colours: ' + ', '.join(f'{k} x{v}' for k, v in sorted(colours.items())))
    print()
    checks = (('size', f'Text outside {MIN_PT:g}-{MAX_PT:g} pt (letters {LETTER_PT:g} pt bold)'),
              ('line', f'Lines under {MIN_LINE:g} pt'), ('font', 'Fonts other than Arial'),
              ('glyph', 'Characters Arial cannot draw'), ('overlap', 'Overlapping text (glyph ink)'),
              ('touch', 'Text touched by a stroke, an arrow or an icon'), ('outside', 'Ink within 1.76 mm of the page edge, or outside it'),
              ('banned', 'Banned elements or attributes, loose elements (one picture allowed: the structure)'),
              ('arrow', f'Arrowheads outside {HEAD_MM[0]:g}-{HEAD_MM[1]:g} mm, or arrows in pieces'),
              ('colour', 'Colour meanings (green, cyan, exit grey, red for errors only; red text only for errors; fills outside the key)'),
              ('objects', f'Built like a person draws it (16 Nov): over {MAX_OBJECTS} drawn elements, or a label in one-glyph pieces'),
              ('other', 'Not measured / other'))
    fails = 0
    for key, title in checks:
        items = problems.get(key, [])
        status = 'ok' if not items else ('FAIL' if key != 'other' else 'NOTE')
        if items and key != 'other':
            fails += len(items)
        print(f'[{status}] {title}: {len(items)}')
        for it in items[:40]:
            print('       ' + it)
    print()
    for ok, text in targets:
        print(f'[{"ok" if ok else "FAIL"}] {text}')
        fails += 0 if ok else 1
    print()
    print(f'[context] Text boxes closer than {NEAR:g} pt (not overlapping): {len(near)}')
    for it in sorted(near):
        print('       ' + it)
    print(f"[context] words: a {words['a']}, b {words['b']}, c {words['c']}, d {words['d']}")
    print(f'[context] strikes on their own text ({len(strikes)}): ' + '; '.join(strikes))
    print(f'[context] arrows ({len(arrows)}): ' + '; '.join(
        f"{a['group']} span {a['span_mm']:.1f} mm head {a['head_mm']:.2f} x {a['width_mm']:.2f} mm" for a in arrows))
    print(f'[context] made of {n_drawn} drawn elements (' + ', '.join(f'{k} {v}' for k, v in drawn.most_common()) +
          f') in {len(top_groups)} top-level groups ({", ".join(g.get("id") or "?" for g in top_groups)}) with '
          f'{sub_named} named groups under them; the largest set of same-style marks in one group: {same_style[0]} '
          f'({same_style[1]})')
    for side in (PDF, AI):                      # 16 Nov: the .ai too, read as the PDF it carries
        if not os.path.exists(side):
            continue
        try:
            import fitz
            doc = fitz.open(side, filetype='pdf')
            pg = doc[0]
            fonts = sorted({f[3].split('+')[-1] for f in doc.get_page_fonts(0)})
            other = [f for f in fonts if f not in PDF_FONTS_OK]
            print(f'[{"ok" if not other else "FAIL"}] {os.path.basename(side)}: '
                  f'{pg.rect.width / MM:.1f} x {pg.rect.height / MM:.1f} mm, embedded fonts {fonts}')
            fails += 1 if other else 0
            ptxt = pg.get_text()
            # FINAL PASS check (16 Nov): the strings the art prints now (the frozen counts, the Flag's ≥, c's second
            # step, the record's residues); until then this listed the 4 Nov figure's, which the art no longer prints
            missing = [s for s in ('≥1.5-fold', '7,522', '1,669', '10,466', '140,147', '10,060', '313,609', '35,853',
                                   '2,953', '343', 'kept unread for the test', 'A rule is written', 'GNG')
                       if s not in ptxt]
            print(f'       its text keeps ≥, the words and the numbers: '
                  f'{"yes" if not missing else "missing " + str(missing)}')
            fails += 1 if missing else 0
            # 16 Nov, the owner's rule: a few hundred objects, never thousands (PyMuPDF's count; Illustrator's own count
            # comes from the illustrator-deliverable skill's audit_ai.jsx, on a copy)
            raw = b''.join(doc.xref_stream(x) or b'' for x in pg.get_contents()).decode('latin-1')
            raw = re.sub(r'\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]*>', ' ', raw)
            clips = len(re.findall(r'(?<![A-Za-z])W\*?\s+n(?![A-Za-z])', raw))
            paths = len(pg.get_drawings())
            spans = sum(len(ln['spans']) for b in pg.get_text('dict')['blocks'] if b.get('type') == 0 for ln in b['lines'])
            images = len(pg.get_images(full=True))
            total = paths + spans + images
            print(f'[{"ok" if total <= MAX_OBJECTS else "FAIL"}] {os.path.basename(side)} is made of {total} objects '
                  f'(at most {MAX_OBJECTS}): {paths} drawn paths, {spans} text spans, {images} pictures; {clips} clips '
                  '(context)')
            fails += 0 if total <= MAX_OBJECTS else 1
        except ImportError:
            print('[note] PyMuPDF not installed: PDF fonts not checked')
    print()
    print(f'Summary: {fails} FAIL item(s); {len(near)} near-touching text pair(s).')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
