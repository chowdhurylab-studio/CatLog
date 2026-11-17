#!/usr/bin/env python3
"""Merge every database's per-paper values into sources/db_values.tsv (source, pmid, ec, metric, value, substrate,
organism, comment), all in catalog units (kcat s^-1, Km mM, kcat/Km mM^-1 s^-1).

Inputs (rebuild them first if a source is refreshed):
  sources/brenda_values.tsv   <- tools/brenda_values.py   (BRENDA 2026.1)
  sources/sabio_values.tsv    <- tools/sabio_values.py    (SABIO-RK Export API, all entries)
  sources/oed_export_*.csv    the Open Enzyme Database export the user downloaded (kcat s^-1, km mM, kcat_km mM^-1 s^-1)
  sources/skid_values.tsv     <- tools/skid_values.py     (SKiD main dataset + its BRENDA reference -> PMID files)
  sources/strenda_values.tsv  <- tools/strenda_values.py  (STRENDA DB, author-deposited; independent of BRENDA)
  sources/uniprot_values.tsv  <- tools/uniprot_values.py  (UniProtKB reviewed entries: KM, kcat and kcat/KM with a PubMed ID)
Sources in tools/dbcompare.py's SOURCES order. Used by `catlog.py export` (db_check and database_check per value),
tools/coverage.py (values cited per paper) and tools/structures.py (same-paper names).
Usage: python3 tools/db_values.py
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / 'sources'


def tsv(path, source):
    if not path.exists():
        return
    for i, line in enumerate(open(path)):
        if i and line.strip():  # line 0 is the header; ids are PMIDs or stand-ins (NP + 8 hex, papers without a PMID)
            yield source + '\t' + line


def oed():
    files = sorted(S.glob('oed_export_*.csv'))
    if not files:
        return
    for r in csv.DictReader(open(files[-1], encoding='utf-8-sig')):
        pmid = (r.get('PubMed') or '').strip()
        if not pmid.isdigit():
            continue
        comment = f"OED; {r.get('Enzyme Types', '')}; pH {r.get('pH', '')}; {r.get('Temp (°C)', '')} C; UniProt {r.get('UniProt Accessions', '')}"
        for col, metric in (('kcat', 'kcat'), ('km', 'Km'), ('kcat_km', 'kcat/Km')):
            try:
                v = float(r.get(col) or '')
            except ValueError:
                continue
            if v > 0:
                fields = [pmid, r.get('EC Numbers', ''), metric, f'{v:.6g}', r.get('Compounds', ''), r.get('Organisms', ''), comment]
                yield 'OED\t' + '\t'.join(f.replace('\t', ' ').replace('\n', ' ') for f in fields) + '\n'


n = Counter()
S.mkdir(exist_ok=True)
with open(S / 'db_values.tsv', 'w') as out:
    out.write('source\tpmid\tec\tmetric\tvalue\tsubstrate\torganism\tcomment\n')
    for gen in (tsv(S / 'brenda_values.tsv', 'BRENDA'), tsv(S / 'sabio_values.tsv', 'SABIO-RK'), oed(),
                tsv(S / 'skid_values.tsv', 'SKiD'), tsv(S / 'strenda_values.tsv', 'STRENDA'),
                tsv(S / 'uniprot_values.tsv', 'UniProt')):
        for line in gen:
            out.write(line); n[line.split('\t', 1)[0]] += 1
print('db_values.tsv:', ', '.join(f'{k} {v:,}' for k, v in n.items()), f'(total {sum(n.values()):,})')
