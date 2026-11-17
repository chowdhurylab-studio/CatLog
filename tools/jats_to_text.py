#!/usr/bin/env python3
"""Render a JATS (Europe PMC fullTextXML) article to plain text with tables as ' | '-separated rows.

Same layout as elsevier_to_text.py: '## Section', one paragraph per line, '=== Table N: caption' blocks with
one row per line and 'TABLE FOOT:' lines, 'FIGURE:' captions. Super/subscripts are kept explicit
(10<sup>-4</sup> -> 10^-4, k<sub>cat</sub> -> k_cat). Tables are laid out on their grid: a cell spanning
rows is carried down (' [rowspan]'), a cell spanning columns is repeated (' [span]'), so every value sits under
its own header. Tables anywhere in the file are rendered (body, inside paragraphs, floats-group, back matter), and so
are figure captions (those outside the body and back sections, e.g. in floats-group, come last).
Usage: jats_to_text.py <article.xml>   (writes the rendering to stdout)
"""
import re
import sys
import xml.etree.ElementTree as ET


def local(tag):
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def script(prefix, text):
    text = norm(text)
    return prefix + (text if len(text) <= 1 else '{' + text + '}') if text else ''


def inline(el, skip=('table-wrap', 'fig')):
    """Text of an element with sup/sub made explicit, leaving out nested tables and figures."""
    out = [el.text or '']
    for ch in el:
        name = local(ch.tag)
        if name in skip:
            pass
        elif name == 'break':  # a line break inside a cell stacks two values: '0.1906<break/>0.2145' is two numbers
            out.append(' ')
        elif name in ('sup', 'sub'):
            if out and out[-1] != out[-1].rstrip():
                out[-1] = out[-1].rstrip()
            out.append(script('^' if name == 'sup' else '_', inline(ch)))
        else:
            out.append(inline(ch, skip))
        out.append(ch.tail or '')
    return ''.join(out)


def txt(el):
    return norm(inline(el)) if el is not None else ''


def child(el, name):
    return next((c for c in el if local(c.tag) == name), None)


def cell_text(cell):
    """A cell's text, or `[IMAGE: file]` when the cell holds only a picture, so a reader sees that something is printed
    there that this text cannot carry (as `TABLE IS AN IMAGE ONLY` says for a whole table deposited as a picture).
    Found 2026-11-12 on 34680172, whose Table 2 identifies its 20 amines only by number and a drawn structure: its
    reader and verifier both rightly stored nothing, so about 110 values waited on cells that rendered as empty.
    Only an empty cell gets the marker, so no line that already carries text changes."""
    t = txt(cell)
    if t.strip():
        return t
    img = next((e for e in cell.iter() if local(e.tag) in ('graphic', 'inline-graphic')), None)
    if img is None:
        return t
    href = next((v for k, v in img.attrib.items() if k.endswith('href')), '')
    return f'[IMAGE: {href.split("/")[-1]}]' if href else '[IMAGE]'


def grid(table):
    """Rows of cells on the table grid, honouring rowspan and colspan."""
    rows, carry = [], {}  # column -> [text, rows left]
    for tr in (e for e in table.iter() if local(e.tag) == 'tr'):
        cells, col = {}, 0
        for c, (text, left) in list(carry.items()):
            cells[c] = text + ' [rowspan]'
            if left <= 1:
                del carry[c]
            else:
                carry[c][1] = left - 1
        for cell in (e for e in tr if local(e.tag) in ('td', 'th')):
            while col in cells:
                col += 1
            text = cell_text(cell)
            span = max(1, int(cell.get('colspan') or 1))
            down = max(1, int(cell.get('rowspan') or 1))
            for k in range(span):
                cells[col + k] = text + (' [span]' if span > 1 else '')
                if down > 1:
                    carry[col + k] = [text, down - 1]
            col += span
        rows.append(' | '.join(cells.get(i, '') for i in range(max(cells) + 1)) if cells else '')
    return rows


def render(path):
    root = ET.parse(path).getroot()
    out, done = [], set()
    title = next((e for e in root.iter() if local(e.tag) == 'article-title'), None)
    out.append('TITLE: ' + txt(title))
    for ab in (e for e in root.iter() if local(e.tag) == 'abstract'):
        out.append('ABSTRACT: ' + txt(ab))

    def table(el):
        done.add(id(el))
        lab, cap = child(el, 'label'), child(el, 'caption')
        out.append('')
        out.append('=== ' + ((txt(lab) + ': ') if lab is not None else 'TABLE: ') + (txt(cap) if cap is not None else ''))
        tables = [e for e in el.iter() if local(e.tag) == 'table']
        for t in tables:
            out.extend(grid(t))
        if not tables:  # the journal deposited this table as a picture: its values are not in this text
            img = next((e for e in el.iter() if local(e.tag) == 'graphic'), None)
            href = next((v for k, v in (img.attrib.items() if img is not None else []) if k.endswith('href')), '')
            out.append(f'TABLE IS AN IMAGE ONLY ({href or "no file name"}): its values are not in this text')
        for foot in (e for e in el.iter() if local(e.tag) == 'table-wrap-foot'):
            out.append('TABLE FOOT: ' + txt(foot))
        out.append('=== end table')

    def walk(el, depth=0):
        tag = local(el.tag)
        if tag == 'table-wrap':
            table(el); return
        if tag == 'fig':
            done.add(id(el))
            cap = child(el, 'caption'); out.append('FIGURE: ' + (txt(cap) if cap is not None else '')); return
        if tag == 'title' and depth < 8:
            out.append(''); out.append('## ' + txt(el)); return
        if tag == 'p':
            out.append(txt(el))
            for e in el.iter():  # tables and figures nested inside the paragraph
                if e is not el and local(e.tag) in ('table-wrap', 'fig') and id(e) not in done:
                    walk(e, depth + 1)
            return
        if tag in ('ref-list', 'ref'):
            return
        for ch in el:
            walk(ch, depth + 1)

    body = next((e for e in root.iter() if local(e.tag) == 'body'), None)
    if body is not None:
        walk(body)
    for sec in (e for e in root.iter() if local(e.tag) == 'back'):
        for s in (e for e in sec if local(e.tag) == 'sec'):
            walk(s)
    for tw in (e for e in root.iter() if local(e.tag) == 'table-wrap'):  # floats-group, back matter
        if id(tw) not in done:
            table(tw)
    # figures outside the body and back sections, after everything else (so an earlier text only gains lines): NIH
    # author manuscripts (PMC's text-mining datasets) put every figure in <floats-group>, and a legend can print the
    # constants (28362483: kcat, K_M and kcat/K_M of two enzymes, rejected quote_not_in_paper until 2026-11-09)
    for f in (e for e in root.iter() if local(e.tag) == 'fig'):
        if id(f) not in done:
            walk(f)
    return '\n'.join(out)


if __name__ == '__main__':
    sys.stdout.write(render(sys.argv[1]))
