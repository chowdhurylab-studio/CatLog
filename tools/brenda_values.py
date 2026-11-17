#!/usr/bin/env python3
"""Write sources/brenda_values.tsv: one line per BRENDA kcat / Km / kcat/Km value that cites a PMID.

BRENDA units already match the catalog (kcat s^-1, Km mM, kcat/Km mM^-1 s^-1), so `catlog.py export`
can compare each verified row with BRENDA's value for the same paper. Streams the archive one EC entry
at a time (same parser as brenda_count.py). Usage: python3 tools/brenda_values.py
"""
import json, re, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / 'sources' / 'brenda_2026_1.json.tar.gz'
OUT = ROOT / 'sources' / 'brenda_values.tsv'
FIELDS = {'turnover_number': 'kcat', 'km_value': 'Km', 'kcat_km_value': 'kcat/Km'}
start_re = re.compile(r'^    "(.*)": \{\s*$')
end_re = re.compile(r'^    \},?\s*$')


def entries():
    with tarfile.open(ARCHIVE, 'r|gz') as tf:
        member = next(m for m in tf if m.isfile() and m.name.endswith('.json'))
        in_data, buf, cur = False, None, None
        for raw in tf.extractfile(member):
            line = raw.decode('utf-8')
            if not in_data:
                in_data = line.startswith('  "data": {')
                continue
            if buf is None:
                m = start_re.match(line)
                if m:
                    cur, buf = m.group(1), ['{']
                continue
            if end_re.match(line):
                buf.append('}')
                yield cur, json.loads(''.join(buf))
                buf, cur = None, None
                continue
            buf.append(line)


def nopmid_ids():
    """'<EC>#<reference no>' -> paper id for BRENDA references without a PMID (sources/nopmid_refs.tsv, tools/nopmid.py):
    the PMID PubMed has after all, or the stand-in id (NP + 8 hex) of a paper only known by its DOI."""
    p = ROOT / 'sources' / 'nopmid_refs.tsv'
    if not p.exists():
        return {}
    import csv
    out = {}
    for r in csv.DictReader(open(p), delimiter='\t'):
        for ref in (r.get('brenda_refs') or '').split():
            if r.get('paper_id'):
                out[ref] = r['paper_id']
    return out


def main():
    n = 0
    alias = nopmid_ids()
    with open(OUT, 'w') as out:
        out.write('pmid\tec\tmetric\tvalue\tsubstrate\torganism\tcomment\n')
        for ec, entry in entries():
            refs = entry.get('reference') if isinstance(entry.get('reference'), dict) else {}
            prots = entry.get('protein') if isinstance(entry.get('protein'), dict) else {}
            for field, metric in FIELDS.items():
                for it in entry.get(field) or []:
                    if not isinstance(it, dict):
                        continue
                    v = str(it.get('value') or '')
                    head = v.split('{')[0].strip()
                    if not re.fullmatch(r'\d+(?:\.\d+)?(?:[eE][-+]?\d+)?', head):
                        continue  # ranges, -999 placeholders and text are not point values
                    value = float(head)
                    if value <= 0:
                        continue
                    sub = v.split('{', 1)[1].rsplit('}', 1)[0].strip() if '{' in v else ''
                    orgs = sorted({(prots.get(str(p)) or {}).get('organism', '') for p in it.get('proteins') or []} - {''})
                    comment = ' '.join(str(it.get('comment') or '').split())[:300].replace('\t', ' ')
                    for r in it.get('references') or []:
                        pmid = str((refs.get(str(r)) or {}).get('pmid') or '').strip()
                        if not (pmid.isdigit() and pmid.strip('0')):
                            pmid = alias.get(f'{ec}#{r}', '')  # no PMID in BRENDA: found by tools/nopmid.py, or a stand-in
                        if pmid:
                            out.write(f'{pmid}\t{ec}\t{metric}\t{value:.6g}\t{sub}\t{"; ".join(orgs)}\t{comment}\n')
                            n += 1
    print(f'{n} BRENDA values with a paper id (PMID, or a stand-in for a paper with no PMID) -> {OUT}')


if __name__ == '__main__':
    main()
