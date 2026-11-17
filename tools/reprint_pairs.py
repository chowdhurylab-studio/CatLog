"""Paper pairs that may share reprinted values (CLAUDE.md open item "Reprinted reference columns").

A paper can print an earlier paper's measurements again with nothing saying so (12591933, 21081665, 26570983,
12604203). Readers catch it only when the earlier paper's text is on disk, so this lists where to look:

  catalog   two catalog papers sharing MIN or more identical specific printed cells of one metric
            (the raw cell with its +-: '6.9 ± 1.3', not '0.5');
  database  a catalog paper whose converted values equal MIN or more values that a database lists for an EARLIER
            paper (lower PMID) of the same EC, for the same metric.

Writes work/reprint_pairs.tsv (kind, later, earlier, shared, examples). A list to check against the papers, never
evidence: shared numbers can be a re-measurement, a coincidence or a database's own error.

    python3 tools/reprint_pairs.py [MIN]      (default 4)
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from catlog import locked  # noqa: E402  (the method paper's test set: never swept)


def cell(raw):
    """The printed cell normalized for comparison: spaces dropped, ± spellings unified."""
    s = str(raw or '').strip().lower().replace('+/-', '±').replace('+-', '±')
    s = re.sub(r'\s+', '', s).replace('x10', '×10').replace('*10', '×10')
    return s


def specific(c):
    """A cell specific enough that two papers printing it are worth a look: a printed ± or exponent, or 3+
    significant figures."""
    if '±' in c or '×10' in c or re.search(r'\de[-+]?\d', c):
        return True
    digits = re.sub(r'\D', '', c.split('±')[0]).lstrip('0')
    return len(digits) >= 3


def sig(v, n=3):
    return float(f'{v:.{n}g}') if v else 0.0


def subkey(name):
    """A substrate name reduced for matching across sources: case, punctuation, stereo prefixes and a leading
    'p-nitrophenyl'/'4-nitrophenyl' spelling set aside."""
    s = str(name or '').lower()
    s = re.sub(r'\b(?:d|l|dl|r|s)-', '', s).replace('p-nitrophenyl', '4-nitrophenyl')
    return re.sub(r'[^a-z0-9]', '', s)


def main(minimum=4):
    held = locked()
    rows = [x for x in (json.loads(l) for l in open(ROOT / 'catalog.jsonl')) if x['pmid'] not in held]
    ecs = defaultdict(set)  # pmid -> ECs (the reader's, then the export's)
    for x in rows:
        for e in re.split(r'[;,\s]+', str(x.get('ec') or '')):
            if re.fullmatch(r'\d+\.\d+\.\d+\.\d+', e):
                ecs[x['pmid']].add(e)
    wide = ROOT / 'catlog_wide.jsonl'
    if wide.exists():
        for l in open(wide):
            w = json.loads(l)
            for e in re.split(r'[;,\s]+', str(w.get('ec_number') or '')):
                if re.fullmatch(r'\d+\.\d+\.\d+\.\d+', e):
                    ecs[str(w.get('pubmed_id'))].add(e)

    out = []
    # catalog pairs
    by_cell = defaultdict(set)
    for x in rows:
        c = cell(x.get('raw_value'))
        if c and specific(c):
            by_cell[(x['metric'], c)].add(x['pmid'])
    pairs = defaultdict(list)
    for (m, c), ps in by_cell.items():
        if 1 < len(ps) <= 6:  # a cell printed by many papers is a standard value, not a reprint
            ps = sorted(ps, key=lambda p: (not p.isdigit(), int(p) if p.isdigit() else 0, p))
            for i, a in enumerate(ps):
                for b in ps[i + 1:]:
                    pairs[(b, a)].append(f'{m} {c}')
    for (later, earlier), shared in pairs.items():
        if len(shared) >= minimum:
            out.append(('catalog', later, earlier, len(shared), '; '.join(sorted(shared)[:6])))

    # database: an earlier paper's database values
    index = defaultdict(set)
    with open(ROOT / 'sources' / 'db_values.tsv') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            p = r['pmid']
            if r['source'] == 'SKiD':  # BRENDA-derived, and its pmid column holds SKiD's own reference numbers
                continue
            try:
                v = float(r['value'])
            except ValueError:
                continue
            if p.isdigit() and v > 0 and p not in held:  # a test paper is never the earlier side either: checking a
                for e in re.split(r'[;,\s]+', r['ec']):  # pair means reading both papers
                    index[(r['metric'], e, sig(v), subkey(r['substrate']))].add(p)
    hits = defaultdict(set)
    for x in rows:
        p = x['pmid']
        try:
            v = float(x.get('value'))
        except (TypeError, ValueError):
            continue
        if not p.isdigit() or v <= 0 or x.get('unit') not in ('s^-1', 'mM', 'mM^-1 s^-1'):
            continue
        if len(re.sub(r'\D', '', f'{v:.6g}').lstrip('0').rstrip('0')) < 2:
            continue  # 0.5, 2, 10: too common to point anywhere
        for e in ecs.get(p, ()):
            for q in index.get((x['metric'], e, sig(v), subkey(x.get('substrate'))), ()):
                if int(q) < int(p):
                    hits[(p, q)].add(f"{x['metric']} {x.get('raw_value')}")
    done = {(a, b) for k, a, b, *_ in out}
    for (p, q), shared in hits.items():
        if len(shared) >= minimum and (p, q) not in done:
            out.append(('database', p, q, len(shared), '; '.join(sorted(shared)[:6])))

    out.sort(key=lambda r: (-r[3], r[0], r[1]))
    path = ROOT / 'work' / 'reprint_pairs.tsv'
    with open(path, 'w') as fh:
        fh.write('kind\tlater\tearlier\tshared\texamples\n')
        for r in out:
            fh.write('\t'.join(map(str, r)) + '\n')
    n = defaultdict(int)
    for r in out:
        n[r[0]] += 1
    print(f"{len(out)} pairs sharing {minimum}+ values ({', '.join(f'{k} {v}' for k, v in sorted(n.items()))}) -> {path}")


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
