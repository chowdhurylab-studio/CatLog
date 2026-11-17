#!/usr/bin/env python3
"""Render an Elsevier Article Retrieval API full-text XML (``httpAccept=text/xml&view=FULL``)
to plain text for a transcription package, mirroring jats_to_text.py.

Output layout (same conventions as the Europe PMC renderer):
  TITLE: ...            DOI: ...            ABSTRACT: ...
  ## Section title      paragraphs one per line
  === Table 1: caption  then one ' | '-separated line per table row, TABLE FOOT: ..., === end table
  FIGURE: caption

Kinetic values depend on super/subscripts, so they are never flattened silently:
``10<ce:sup>5</ce:sup>`` renders as ``10^5`` and ``M<ce:sup>−1</ce:sup>`` as ``M^−1``;
``k<ce:inf>cat</ce:inf>`` renders as ``k_cat``.  Multi-character scripts are braced (``10^{−3}``).
Tables are laid out on the CALS column grid: a cell spanning columns (namest/nameend) is repeated
across them and marked ``[span]``; a cell spanning rows (morerows) is carried down into those rows
and marked ``[rowspan]``; entries go to their colname column.  So every row has one cell per column
and a value always sits under its own header (a flat positional layout shifted 360 of 1,658
tables left).  Table footnotes (``TABLE FOOT: <label> <text>``, markers stay on the cell as ``^d``),
float credit lines (``TABLE SOURCE:`` / ``FIGURE SOURCE:``, e.g. "Reprinted with permission
from ..."), the nomenclature list and the bibliography (``## REFERENCES``) are all kept, because they
are how a reprinted, not-this-paper's measurement is recognised.  Scanned back-file articles carry
no structured body, only OCR text in ``<xocs:rawtext>``; that is emitted under ``## OCR TEXT``.

Usage: elsevier_to_text.py <article.xml>   (writes the rendering to stdout)
"""
import re
import sys
import xml.etree.ElementTree as ET


def local(tag):
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def norm_space(s):
    return re.sub(r'\s+', ' ', s).strip()


def script(prefix, text):
    text = norm_space(text)
    if not text:
        return ''
    return prefix + (text if len(text) == 1 else '{' + text + '}')


def inline(el):
    """Text of an element with sup/inf made explicit."""
    out = [el.text or '']
    for ch in el:
        name = local(ch.tag)
        if name in ('sup', 'inf'):
            # "k <inf>cat</inf>" -> "k_cat": a script binds to the token before it
            if out and out[-1] != out[-1].rstrip():
                out[-1] = out[-1].rstrip()
            out.append(script('^' if name == 'sup' else '_', inline(ch)))
        elif name == 'float-anchor':
            pass
        elif name == 'hsp':
            out.append(' ')
        else:
            out.append(inline(ch))
        out.append(ch.tail or '')
    return ''.join(out)


def txt(el):
    return norm_space(inline(el)) if el is not None else ''


def first(root, name):
    for el in root.iter():
        if local(el.tag) == name:
            return el
    return None


def grid_rows(section, colnames):
    return [' | '.join(cells) for cells in grid_cells(section, colnames)]


def grid_cells(section, colnames):
    """Lay one thead/tbody/tfoot out on the CALS column grid (a list of cell lists per row).

    Each entry goes to its colname (or namest) column; an entry spanning columns
    (namest..nameend) is repeated across them with " [span]"; an entry spanning rows
    (morerows=N) is carried down into the next N rows with " [rowspan]".  Without this,
    a row that starts under a carried-down label shifts left and its values read as
    belonging to the wrong column header.
    """
    index = {name: i for i, name in enumerate(colnames) if name}
    width = len(colnames)
    pending = {}  # column -> [text, rows still to fill]
    rows = []
    for row in (r for r in section if local(r.tag) == 'row'):
        cells = [None] * width
        for col, carry in sorted(pending.items()):
            if col >= len(cells):
                cells.extend([None] * (col + 1 - len(cells)))
            cells[col] = carry[0] + ' [rowspan]'
            carry[1] -= 1
        pending = {col: carry for col, carry in pending.items() if carry[1] > 0}
        cursor = 0
        for entry in row:
            if local(entry.tag) != 'entry':
                continue
            named = entry.get('colname') or entry.get('namest')
            if named in index:
                start = index[named]
            else:
                start = cursor
                while start < len(cells) and cells[start] is not None:
                    start += 1
            end = index.get(entry.get('nameend'), start)
            if end < start:
                end = start
            if width and start >= width and named not in index and not txt(entry):
                continue  # empty padding entry after a full-width span; nothing to place
            if end >= len(cells):
                cells.extend([None] * (end + 1 - len(cells)))
            value = txt(entry) + (' [span]' if end > start else '')
            for col in range(start, end + 1):
                cells[col] = value
            morerows = entry.get('morerows')
            if morerows and morerows.isdigit() and int(morerows) > 0:
                for col in range(start, end + 1):
                    pending[col] = [value, int(morerows)]
            cursor = end + 1
        rows.append(['' if c is None else c for c in cells])
    return rows


def render_table(tbl, out):
    lab = next((c for c in tbl if local(c.tag) == 'label'), None)
    cap = next((c for c in tbl if local(c.tag) == 'caption'), None)
    out.append('')
    out.append('=== ' + ((txt(lab) + ': ') if lab is not None else 'TABLE: ') + txt(cap))
    for tgroup in (c for c in tbl.iter() if local(c.tag) == 'tgroup'):
        colnames = [c.get('colname') or ('col' + c.get('colnum', '')) for c in tgroup if local(c.tag) == 'colspec']
        declared = tgroup.get('cols')
        if declared and declared.isdigit() and int(declared) > len(colnames):
            colnames += [None] * (int(declared) - len(colnames))
        sections = [c for c in tgroup if local(c.tag) in ('thead', 'tbody', 'tfoot')]
        for section in sections or [tgroup]:
            out.extend(grid_rows(section, colnames))
    for foot in (c for c in tbl.iter() if local(c.tag) in ('table-footnote', 'legend')):
        out.append('TABLE FOOT: ' + txt(foot))
    for source in (c for c in tbl if local(c.tag) == 'source'):
        out.append('TABLE SOURCE: ' + txt(source))
    out.append('=== end table')


def flat_words(el):
    return norm_space(' '.join(t for t in el.itertext() if t.strip()))


def render(path):
    root = ET.parse(path).getroot()
    out = []
    out.append('TITLE: ' + txt(first(root, 'title')))  # dc:title in coredata comes first
    doi = first(root, 'doi')
    if doi is not None:
        out.append('DOI: ' + txt(doi))
    for ab in (e for e in root.iter() if local(e.tag) == 'abstract'):
        sec_title = first(ab, 'section-title')
        label = txt(sec_title) if sec_title is not None else 'Abstract'
        paras = [txt(p) for p in ab.iter() if local(p.tag) in ('simple-para', 'para')]
        if paras:
            out.append('ABSTRACT (' + label + '): ' + ' '.join(paras))

    rendered_tables = set()
    body = first(root, 'body')

    def walk(el, depth=0):
        name = local(el.tag)
        if name == 'table':
            rendered_tables.add(id(el))
            render_table(el, out)
            return
        if name == 'section-title':
            out.append('')
            out.append('#' * min(2 + depth // 2, 4) + ' ' + txt(el))
            return
        if name in ('para', 'simple-para') and depth > 0:
            nested = [t for t in el.iter() if local(t.tag) == 'table']
            out.append(txt(el))
            for t in nested:
                rendered_tables.add(id(t))
                render_table(t, out)
            return
        if name == 'figure':
            render_figure(el)
            return
        if name == 'nomenclature':
            render_nomenclature(el)
            return
        for ch in el:
            walk(ch, depth + 1)

    rendered_figures = set()

    def render_figure(fig):
        rendered_figures.add(id(fig))
        cap = next((c for c in fig if local(c.tag) == 'caption'), None)
        lab = next((c for c in fig if local(c.tag) == 'label'), None)
        out.append('FIGURE: ' + ((txt(lab) + ': ') if lab is not None else '') + txt(cap))
        for source in (c for c in fig if local(c.tag) == 'source'):
            out.append('FIGURE SOURCE: ' + txt(source))

    def render_nomenclature(nom):
        out.append('')
        out.append('## Nomenclature')
        term = None
        for d in nom.iter():
            if local(d.tag) == 'def-term':
                term = txt(d)
            elif local(d.tag) == 'def-description':
                out.append((term + ': ' if term else '') + txt(d))
                term = None

    if body is not None:
        walk(body)
    # Floats (tables, figures) are often held outside <body> in <ce:floats>.
    for t in (e for e in root.iter() if local(e.tag) == 'table'):
        if id(t) not in rendered_tables:
            rendered_tables.add(id(t))
            render_table(t, out)
    for f in (e for e in root.iter() if local(e.tag) == 'figure'):
        if id(f) not in rendered_figures:
            render_figure(f)

    structured = body is not None and any(local(e.tag) in ('para', 'section') for e in body.iter())
    raw = first(root, 'rawtext')
    if not structured and raw is not None:
        out.append('')
        out.append('## OCR TEXT (scanned article; no structured body in the Elsevier XML)')
        out.append((raw.text or '').strip())
    # The bibliography lets a "Data from reference [90]" footnote be resolved to the cited work.
    refs = [e for e in root.iter() if local(e.tag) == 'bib-reference']
    if refs:
        out.append('')
        out.append('## REFERENCES')
        for ref in refs:
            lab = next((c for c in ref if local(c.tag) == 'label'), None)
            rest = ' '.join(flat_words(c) for c in ref if local(c.tag) != 'label')
            out.append(((txt(lab) + ' ') if lab is not None else '') + rest)
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    sys.stdout.write(render(sys.argv[1]))
