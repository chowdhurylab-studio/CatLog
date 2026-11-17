#!/usr/bin/env python3
"""SKiD (Structure-oriented Kinetics Dataset) kcat and Km values with their PMIDs -> sources/skid_values.tsv.

SKiD rows cite BRENDA's per-EC reference numbers; sources/skid/References.tar.gz maps (EC, reference number) to a
PMID. Units already match the catalog (kcat s^-1, Km mM). Same columns as the other *_values.tsv files.
Usage: python3 tools/skid_values.py
"""
import csv, io, tarfile
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parent.parent
SKID = ROOT / 'sources' / 'skid'

refs = {}
with tarfile.open(SKID / 'References.tar.gz') as tf:
    for m in tf:
        if m.isfile() and m.name.endswith('.csv'):
            ec = Path(m.name).stem
            for r in csv.DictReader(io.TextIOWrapper(tf.extractfile(m), encoding='utf-8', errors='replace'), delimiter='\t'):
                pmid = (r.get('PMID') or '').strip()
                if pmid.isdigit():
                    refs[(ec, str(r.get('ID', '')).strip())] = pmid

wb = openpyxl.load_workbook(SKID / 'Main_dataset_v1.xlsx', read_only=True)
n = missing = 0
with open(ROOT / 'sources' / 'skid_values.tsv', 'w') as out:
    out.write('pmid\tec\tmetric\tvalue\tsubstrate\torganism\tcomment\n')
    for sheet, col, metric in (('kcat_dataset', 'kcat_value', 'kcat'), ('Km_dataset', 'Km_value', 'Km')):
        rows = wb[sheet].iter_rows(values_only=True)
        hdr = next(rows)
        for vals in rows:
            r = dict(zip(hdr, vals))
            try:
                v = float(r[col])
            except (TypeError, ValueError):
                continue
            pmids = [refs.get((str(r['EC_number']), ref.strip())) for ref in str(r['References']).split(',')]
            pmids = [p for p in pmids if p]
            if not pmids or v <= 0:
                missing += 1
                continue
            comment = f"SKiD {r['Entry_ID']}; UniProt {r['UniProt_ID']}; mutant {r['Mutation']}; pH {r['pH']}; {r['Temperature']}"
            for p in sorted(set(pmids)):
                fields = [p, str(r['EC_number']), metric, f'{v:.6g}', str(r['Substrate']), str(r['Organism_name']), comment]
                out.write('\t'.join(f.replace('\t', ' ').replace('\n', ' ') for f in fields) + '\n'); n += 1
print(f'{n} SKiD values with a PMID ({missing} rows had no PMID-backed reference)')
