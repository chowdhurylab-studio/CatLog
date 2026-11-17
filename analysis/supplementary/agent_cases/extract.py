#!/usr/bin/env python3
"""Every agent case that held, in one structured file: case_data/cases.json (233 cases).

Read only from the project's checked files:
  paper/04_supplementary_case_tables.md   Tables S1-S11: one row per case, its kind (the table) and the checked cells
  paper/04_agent_case_tables.md           the main table: the twelve cases and their row numbers
  round*/provenance/<PMID>.json           how each case was found (classification) and by whom (found_by, free text)
  boxes/scripts/assemble_page.py ORDER    the nine cases told in the Supplementary Note, in order
  papers.tsv                              the DOI of the two papers that have no PMID (stand-in ids NP...)
and the paper's journal and year from PubMed (E-utilities esummary; for a stand-in id, Crossref by DOI), cached in
case_data/meta.json so the network is asked once.

One correction to the provenance files, as page 04 states it (its main-table legend, re-pick of 2026-11-06): 41357771
was found afterwards to be a prompted test, not the agent's own reasoning. With it the classes are 71 own reasoning,
145 instructions, 14 code, 3 earlier agent, the counts page 04 gives; the script stops if they differ.

Run: python3 -I -B paper/evidence/agent_highlights_20261028/case_data/extract.py
"""
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path('<the CatLog folder>')
A = ROOT / 'paper/evidence/agent_highlights_20261028'
OUT = A / 'case_data'
SUPP = ROOT / 'paper/04_supplementary_case_tables.md'
MAIN = ROOT / 'paper/04_agent_case_tables.md'
ORDER = ['25799411', '12226525', '19686854', '9637365', '16484232', '20117081', '15767255', '21257746', '19810726']
CLASS = {
    "agent's own reasoning": 'own reasoning',
    "prompted test, agent's application": 'its instructions',
    'code flagged, agent confirmed': 'code flagged it',
    'proposed earlier, agent confirmed': 'an earlier agent proposed it',
}
CORRECTED = {'41357771': 'its instructions'}
EXPECTED = {'own reasoning': 71, 'its instructions': 145, 'code flagged it': 14, 'an earlier agent proposed it': 3}
ID = re.compile(r'(\d{5,9}|NP[0-9A-F]{8})')


def tables():
    rows, kind, sid, cols = [], None, None, None
    for line in SUPP.read_text(encoding='utf-8').split('\n'):
        m = re.match(r'^## Table (S\d+) \| (.+?) \((\d+) cases?\)', line)
        if m:
            sid, kind, cols = m.group(1), m.group(2), None
            continue
        if sid and line.startswith('| ') and not line.startswith('|---'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if cols is None:
                cols = cells
                continue
            if len(cells) != len(cols):
                sys.exit(f'{sid}: a row splits into {len(cells)} cells, not {len(cols)}')
            pm = ID.search(cells[0].replace('*', ''))
            rows.append({'table': sid, 'kind': kind, 'pmid': pm.group(1), 'cells': dict(zip(cols, cells))})
    return rows


def main_table():
    out = {}
    for line in MAIN.read_text(encoding='utf-8').split('\n'):
        m = re.match(r'^\| (\d+) \| \*\*(\d{5,9}|NP[0-9A-F]{8})\*\*', line)
        if m:
            out[m.group(2)] = int(m.group(1))
    if len(out) != 12:
        sys.exit(f'main table: {len(out)} rows, not 12')
    return out


def provenance(pmid):
    files = sorted(A.glob(f'round*/provenance/{pmid}.json'))
    if len(files) != 1:
        sys.exit(f'{pmid}: {len(files)} provenance files')
    p = json.loads(files[0].read_text(encoding='utf-8'))
    how = CORRECTED.get(pmid) or CLASS.get(p.get('classification'))
    if not how:
        sys.exit(f'{pmid}: classification {p.get("classification")!r} not known')
    return how, (p.get('found_by') or ''), files[0].parent.parent.name


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'catalog-case-table/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def metadata(ids):
    cache_file = OUT / 'meta.json'
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    want = [i for i in ids if i not in cache]
    num = [i for i in want if i.isdigit()]
    for k in range(0, len(num), 150):
        chunk = num[k:k + 150]
        url = ('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&tool=catalog-case-table&id='
               + ','.join(chunk))
        res = get(url)['result']
        for i in chunk:
            r = res.get(i) or {}
            year = (re.search(r'(\d{4})', r.get('pubdate', '') or r.get('epubdate', '')) or [None, ''])[1]
            cache[i] = {'journal': r.get('source', ''), 'year': year, 'from': 'pubmed'}
        time.sleep(0.5)
    doi = {}
    with open(ROOT / 'papers.tsv', newline='', encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            doi[r['pmid']] = r.get('doi', '')
    for i in [i for i in want if not i.isdigit()]:
        d = doi.get(i, '')
        if not d:
            cache[i] = {'journal': '', 'year': '', 'from': 'no doi'}
            continue
        msg = get('https://api.crossref.org/works/' + urllib.parse.quote(d))['message']
        parts = (msg.get('issued') or {}).get('date-parts') or [[None]]
        cache[i] = {'journal': (msg.get('short-container-title') or msg.get('container-title') or [''])[0],
                    'year': str(parts[0][0] or ''), 'from': 'crossref', 'doi': d}
        time.sleep(0.5)
    cache_file.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    return cache


def run():
    OUT.mkdir(exist_ok=True)
    rows = tables()
    pmids = [r['pmid'] for r in rows]
    if len(rows) != 233 or len(set(pmids)) != 233:
        sys.exit(f'{len(rows)} rows, {len(set(pmids))} papers: expected 233 and 233')
    main = main_table()
    meta = metadata(pmids)
    counts = {}
    cases = []
    for n, r in enumerate(rows, 1):
        how, found_by, rnd = provenance(r['pmid'])
        counts[how] = counts.get(how, 0) + 1
        m = meta.get(r['pmid'], {})
        cases.append({
            'case': n, 'pmid': r['pmid'], 'journal': m.get('journal', ''), 'year': m.get('year', ''),
            'table': r['table'], 'kind': r['kind'], 'how': how, 'round': rnd,
            'main_table_row': main.get(r['pmid']), 'note_case': (ORDER.index(r['pmid']) + 1) if r['pmid'] in ORDER else None,
            'cells': r['cells'], 'found_by_provenance': found_by,
        })
    if counts != EXPECTED:
        sys.exit(f'provenance classes {counts}, expected {EXPECTED}')
    if sum(1 for c in cases if c['main_table_row']) != 12 or sum(1 for c in cases if c['note_case']) != 9:
        sys.exit('the twelve or the nine are not all among the 233')
    missing = [c['pmid'] for c in cases if not (c['journal'] and c['year'])]
    (OUT / 'cases.json').write_text(json.dumps(cases, indent=1, ensure_ascii=False))
    print(f'wrote case_data/cases.json: {len(cases)} cases; classes {counts}; no journal or year: {missing}')


if __name__ == '__main__':
    run()
