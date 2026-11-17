"""Supplementary Tables 1-5 of the CatLog paper, as a referee reads them.

The source tables carry the agents' evidence notes word for word: file names, log line numbers, XML ids, timestamps.
Here those long note columns are replaced by short plain cells (plain_words.tsv). Tables 1-3: each plain cell was
written by one agent, compared with its original by a second agent, and any correction confirmed by a third (workflow
catlog-supp-plain, 16 Nov 2026). Table 4: the cells the final review flagged (old-CatLog counts, banned words, internal
names) were rewritten by the coordinating chat and checked by a separate agent. `how` says which path each cell took.
Every table gets readable column heads and a second sheet saying what each column means (s1_heads.tsv, guides.tsv),
Table 1's verdict codes become words (s1_codes.tsv), and a paper without a PMID is named by its DOI, not by CatLog's
stand-in id. Nothing else changes: every other cell is copied.

The sources stay as they are (their full notes are the evidence):
  Supplementary Table 1  paper/evidence/accuracy_check_20261114/supp_wrong_values.tsv (column guide: supp_wrong_values.md)
  Supplementary Table 2  writing/figures/extended_data/known_traps/trap_papers.tsv (built by that folder's build.py)
  Supplementary Table 3  writing/figures/extended_data/known_traps/trap_cells.tsv
  Supplementary Table 4  writing/figures/extended_data/rules_reach/rules_table.tsv (built by that folder's build.py)
  Supplementary Table 5  writing/manuscript/supp_table_agent_cases.md (the writing chat's; copied, comments dropped)
Each plain cell records the sha256 (first 12 characters) of the original it was written from; the build stops if a
source cell changed since, or if a plain cell is missing, extra, over its length cap, or carries anything internal.

Writes out/Supplementary_Table_{1..5}_*.tsv and .xlsx.
Usage: python3 -I -B writing/supplementary/build_supplementary.py
"""
import csv
import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'out'
csv.field_size_limit(10 ** 9)

SOURCES = {
    'S1': (ROOT / 'paper/evidence/accuracy_check_20261114/supp_wrong_values.tsv', 'Supplementary_Table_1_wrong_values', 97),
    'S2': (ROOT / 'writing/figures/extended_data/known_traps/trap_papers.tsv', 'Supplementary_Table_2_known_trap_papers', 32),
    'S3': (ROOT / 'writing/figures/extended_data/known_traps/trap_cells.tsv', 'Supplementary_Table_3_known_trap_key_cells', 180),
    'S4': (ROOT / 'writing/figures/extended_data/rules_reach/rules_table.tsv', 'Supplementary_Table_4_kinds_of_error', 87),
}
REWRITTEN = {  # item: {column: word cap}; S1-S3 every cell of the column (S1 the non-empty ones), S4 the listed rows
    'S1': {'later_check': 40},
    'S2': {'the trap (key)': 45, "how CatLog's records documented it before the test": 45},
    'S3': {'where it is printed': 25, 'how the right value is known': 45},
    'S4': {'kind of error': 12, "example (from CatLog's records)": 30},
}
PARTIAL = {'S4'}
INTERNAL = re.compile(r'\.jsonl?\b|\.tsv\b|\.md\b|log\.tsv|rejected\.jsonl|work/|paper/evidence|/Users/|\bXML\b|\bp\d{4}\b|'
                      r'\bce:|\bi=\d+|\b[0-9a-f]{16}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b|\bdbdiff\b|catlog-[a-z]+|'
                      r'\bverify\.md\b|\bread\.md\b|error_ledger|human[- ]review pack|\brow_id\b|\braw_unit\b|build\.py|'
                      r'\bgrep\b|\bregex\b|\btranscript\b')
NAMED = re.compile(r'\breviewer [A-Z][A-Za-z]')
WORDS = re.compile(r'\bmeasurements?\b|(?<!protein )(?<!UniProt )(?<!database )(?<!PDB )\bentr(?:y|ies)\b|'
                   r'\bdata points?\b|\bpipeline\b', re.I)   # a protein's or database's entry is its own word
CODE_COLUMNS = ('final_verdict', 'votes', 'dissent', 'first_judging')
STANDIN = re.compile(r'\bNP[0-9A-F]{8}\b')


def same(what, got, want):
    if got != want:
        sys.exit(f'STOP {what}: got {got!r}, expected {want!r}')


def sha12(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def read_tsv(path):
    with open(path, encoding='utf-8', newline='') as f:
        r = csv.DictReader(f, delimiter='\t')
        return r.fieldnames, list(r)


def key_of(item, row):
    return {'S1': lambda r: f"{r['test']}|{r['pmid']}|{r['claim_id']}", 'S2': lambda r: r['pmid'],
            'S3': lambda r: f"{r['pmid']}#{r['cell']}", 'S4': lambda r: r['id']}[item](row)


plain = {}
_, prow = read_tsv(HERE / 'plain_words.tsv')
for r in prow:
    k = (r['item'], r['key'], r['column'])
    same(f'one plain cell per {k}', k in plain, False)
    plain[k] = r

tables, used = {}, set()
for item, (path, name, n) in SOURCES.items():
    cols, rows = read_tsv(path)
    same(f'{item}: rows in {path.name}', len(rows), n)
    same(f'{item}: keys unique', len({key_of(item, r) for r in rows}), n)
    for r in rows:
        for col, cap in REWRITTEN[item].items():
            orig = r[col]
            k = (item, key_of(item, r), col)
            p = plain.get(k)
            if p is None:
                if item in PARTIAL or (item == 'S1' and not orig.strip()):
                    continue                    # S4: only the listed cells; S1: rows with no later check stay empty
                sys.exit(f'STOP no plain cell for {k}')
            same(f'{k}: written from this original', p['original_sha12'], sha12(orig))
            words = len(p['plain'].split())
            if words > cap:
                sys.exit(f'STOP {k}: {words} words, cap {cap}')
            if INTERNAL.search(p['plain']) or NAMED.search(p['plain']) or WORDS.search(p['plain']):
                sys.exit(f'STOP {k}: carries something internal, a name or a banned word: {p["plain"]!r}')
            r[col] = p['plain']
            used.add(k)
    tables[item] = (cols, rows, name)
same('every plain cell used', sorted(set(plain) - used), [])

# A paper without a PMID is named by its DOI (papers.tsv), never by CatLog's stand-in id
_, papers = read_tsv(ROOT / 'papers.tsv')
DOI = {p['pmid']: p['doi'] for p in papers if STANDIN.fullmatch(p['pmid'] or '')}


def doi_of(m):
    d = DOI.get(m.group(0), '')
    if not d:
        sys.exit(f'STOP no DOI on file for {m.group(0)}')
    return f'doi:{d}'


for item, (cols, rows, _) in tables.items():
    for r in rows:
        for c in cols:
            r[c] = STANDIN.sub(doi_of, r[c])

# Supplementary Table 1: readable heads and verdict codes as words
_, heads = read_tsv(HERE / 's1_heads.tsv')
_, codes = read_tsv(HERE / 's1_codes.tsv')
cols1, rows1, _ = tables['S1']
same('S1: a head for every column, in order', [h['column'] for h in heads], cols1)
CODE = {c['code']: c['words'] for c in codes}
CODE_RX = re.compile(r'\b(' + '|'.join(sorted(map(re.escape, CODE), key=len, reverse=True)) + r')\b')
for r in rows1:
    for col in CODE_COLUMNS:
        r[col] = CODE_RX.sub(lambda m: CODE[m.group(1)], r[col])
left = sorted({m for r in rows1 for col in CODE_COLUMNS for m in re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', r[col])})
same('S1: no verdict code left in the verdict columns', left, [])

# Tables 2-4: readable heads and what each column means
_, guides = read_tsv(HERE / 'guides.tsv')
GUIDE = {'S1': [(h['column'], h['header'], h['meaning']) for h in heads]}
for item in ('S2', 'S3', 'S4'):
    GUIDE[item] = [(g['column'], g['header'], g['meaning']) for g in guides if g['item'] == item]
    same(f'{item}: a head and meaning for every column, in order', [g[0] for g in GUIDE[item]], tables[item][0])

# Every cell of the four tables, rewritten or copied: nothing internal, no reviewer named, and one CatLog (the paper
# never speaks of an earlier and a newer CatLog, BRIEF.md)
WHOLE = re.compile(r'\.jsonl?\b|\.tsv\b|log\.tsv|rejected\.jsonl|work/|paper/evidence|/Users/|\bi=\d+|\b[0-9a-f]{16}\b|'
                   r'\bdbdiff\b|catlog-[a-z]+|error_ledger|human[- ]review pack')
ONE_CATLOG = re.compile(r"earlier version|old(?:er)? (?:system|catalogue|catalog|version|converter)|"
                        r"earlier (?:system|catalogue|catalog)|previous version|first pass|realkcat|CatLog's earlier|"
                        r"old certified", re.I)
bad = [(item, c, r[c][:80]) for item, (cols, rows, _) in tables.items() for r in rows for c in cols
       if WHOLE.search(r[c]) or NAMED.search(r[c]) or ONE_CATLOG.search(r[c]) or STANDIN.search(r[c])]
same('cells with something internal, a name, a stand-in id or an earlier CatLog', bad, [])
bad = [(item, c, r[c][:80]) for item, (cols, rows, _) in tables.items() if item in ('S2', 'S3', 'S4')
       for r in rows for c in cols if WORDS.search(r[c])]
same('Tables 2-4: cells with measurement(s), entries, data points or pipeline', bad, [])
for item, gl in GUIDE.items():   # the guides may give the 15 November cut's date and time, so WHOLE, not INTERNAL
    for col, head, meaning in gl:
        if len(head.split()) > 7 or len(meaning.split()) > 45 or WHOLE.search(meaning) or WORDS.search(meaning):
            sys.exit(f'STOP {item} head {col}: {head!r} / {meaning!r}')


def write(name, head, rows, guide=None, note=None, codes=None):
    with open(OUT / f'{name}.tsv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(head)
        w.writerows(rows)
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    wb = Workbook()
    ws = wb.active
    ws.title = 'table'
    ws.append(head)
    for r in rows:
        ws.append(r)
    for c in ws[1]:
        c.font = Font(bold=True)
    for col in ws.columns:
        longest = max(len(str(c.value or '')) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(60, max(10, longest * 0.9 if longest < 30 else 60))
        for c in col[1:]:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'A2'
    if guide:
        m = wb.create_sheet('columns')
        m.append(['column', 'meaning'])
        for head_, meaning in guide:
            m.append([head_, meaning])
        if codes:
            m.append([])
            m.append(['verdict', 'meaning'])
            for c in codes:
                m.append([c['words'], c['gloss']])
        for c in m[1]:
            c.font = Font(bold=True)
        m.column_dimensions['A'].width, m.column_dimensions['B'].width = 34, 100
        for row in m.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical='top')
    if note:
        m = wb.create_sheet('note')
        m.append([note])
        m.column_dimensions['A'].width = 120
        m['A1'].alignment = Alignment(wrap_text=True, vertical='top')
    wb.save(OUT / f'{name}.xlsx')
    print(f'wrote {OUT / name}.tsv and .xlsx ({len(rows)} rows)')


OUT.mkdir(exist_ok=True)
for item, (cols, rows, name) in tables.items():
    gl = GUIDE[item]
    write(name, [g[1] for g in gl], [[r[c] for c in cols] for r in rows], guide=[(g[1], g[2]) for g in gl],
          codes=codes if item == 'S1' else None)

# Supplementary Table 5, copied (kept as Markdown by the writing chat; its source comments are dropped, its lead
# paragraph goes to a second sheet)
md = re.sub(r'<!--.*?-->', '', (ROOT / 'writing/manuscript/supp_table_agent_cases.md').read_text(encoding='utf-8'), flags=re.S)
lines = [ln.strip() for ln in md.splitlines()]
table = [ln for ln in lines if ln.startswith('|')]
lead = ' '.join(ln for ln in lines if ln and not ln.startswith('|') and not ln.startswith('#')).strip()
cells5 = [[c.strip() for c in ln.strip('|').split('|')] for ln in table]
head5, rows5 = cells5[0], cells5[2:]
same('S5: separator row under the head', set(''.join(cells5[1])) <= set('-: '), True)
same('S5: twelve cases, each as wide as the head', (len(rows5), {len(r) for r in rows5}), (12, {len(head5)}))
bad = [v[:80] for r in rows5 for v in r if WHOLE.search(v) or NAMED.search(v) or ONE_CATLOG.search(v)]
same('S5: cells with something internal, a name or an earlier CatLog', bad, [])
write('Supplementary_Table_5_agent_cases', head5, rows5, note=lead)

how = {}
for r in prow:
    how[r['how']] = how.get(r['how'], 0) + 1
print('plain cells by path:', how)
