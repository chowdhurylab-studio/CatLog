#!/usr/bin/env python3
"""CatLog's own first reading of each hard-case paper, scored on the same keys with the same code.

The first reading is the earliest work/<PMID>.read*.json (work/old/ keeps the earlier ones) that holds kcat, Km or
kcat/Km rows; files from the censored-values pass hold only censored rows and are skipped. Its raw cells are converted
by CatLog's own code (units.normalize on the reader's raw_value and unit_for_conversion or raw_unit, as catlog.check
does at add) and scored by score_hard.score_cell. This is CatLog's reader alone: before its verifier, code checks, sweeps and audits.
Writes catlog_first_scores.json here and prints, per kind of trap, the papers whose first reading stored a trap value
next to the plain read and CatLog's catalogue now (summary.json)."""
import collections, glob, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[2]
EV = Path('<the kit folder>')
sys.path.insert(0, str(EV / 'code' / 'tools' / 'w1'))
sys.path.insert(0, str(EV / 'code' / 'tools'))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(MAIN / 'tools'))
import score_hard as SH  # noqa: E402
from units import normalize  # noqa: E402

UNITS = ('s^-1', 'mM', 'mM^-1 s^-1')


def converted(p, rows):
    out = []
    for i, r in enumerate(rows):
        if r.get('metric') not in ('kcat', 'Km', 'kcat/Km'):
            continue
        try:
            v, u, err = normalize(r['metric'], r.get('raw_value', ''), r.get('unit_for_conversion') or r.get('raw_unit', ''))
        except Exception:
            continue
        if err or u not in UNITS or not v or v <= 0:
            continue
        out.append({'metric': r['metric'], 'value': float(v), 'raw': r.get('raw_value', ''), 'raw_unit': r.get('raw_unit', ''),
                    'enzyme': r.get('enzyme', ''), 'variant': r.get('variant', ''), 'substrate': r.get('substrate', ''),
                    'id': f'first:{p}:{i}'})
    return out


def first_read(p):
    cands = []
    for f in glob.glob(str(MAIN / 'work' / 'old' / f'{p}.read.*.json')) + [str(MAIN / 'work' / f'{p}.read.json')]:
        if not os.path.exists(f):
            continue
        m = re.search(r'\.read\.(\d+)\.json$', f)
        ts = int(m.group(1)) if m else os.path.getmtime(f)
        try:
            d = json.load(open(f))
        except Exception:
            continue
        rows = [r for r in d.get('rows') or [] if not r.get('censored')]
        if rows:
            cands.append((ts, f, d, rows))
    return min(cands, key=lambda c: c[0]) if cands else None


def main():
    summ = {r['pmid']: r for r in json.loads((HERE / 'summary.json').read_text())}
    out = {}
    for p, s in summ.items():
        base = HERE if s['set'] == 'first' else HERE / 'expand'
        key, cells = SH.cells_of(p, base)
        fr = first_read(p)
        if not fr or not key.get('usable', True):
            out[p] = {'class_id': s['class_id'], 'first_read': None}
            continue
        ts, f, d, rows = fr
        vals = converted(p, rows)
        ident = str(key.get('trap_kind', '')).startswith('identity')
        verdicts = [SH.score_cell(c, vals, ident)[0] for c in cells]
        out[p] = {'class_id': s['class_id'], 'first_read': os.path.relpath(f, MAIN), 'model': d.get('model', ''),
                  'cells': len(cells), 'trap': verdicts.count('trap'), 'review': verdicts.count('review'),
                  'verdicts': verdicts, 'fell_in': verdicts.count('trap') > 0}
    (HERE / 'catlog_first_scores.json').write_text(json.dumps(out, indent=1) + '\n')
    by = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for p, r in out.items():
        if not r.get('first_read'):
            continue
        s = summ[p]
        b = by[r['class_id']]
        b[0] += 1; b[1] += s['fell_in']; b[2] += r['fell_in']; b[3] += bool(s['catlog_trap']); b[4] += r['review'] > 0
    print('kind   papers  plain-read-fell-in  CatLog-first-read-fell-in  CatLog-catalogue-now  (first reads with cells to judge)')
    tot = [0, 0, 0, 0, 0]
    for k in ['RA3', 'RA1', 'PP2', 'PP7', 'PP3', 'PP4', 'PP1', 'IP11', 'RA4', 'TL1', 'TL2', 'TL4']:
        b = by.get(k)
        if b:
            print(f'{k:5s}  {b[0]:6d}  {b[1]:18d}  {b[2]:25d}  {b[3]:20d}  ({b[4]})')
            tot = [t + x for t, x in zip(tot, b)]
    print(f'all    {tot[0]:6d}  {tot[1]:18d}  {tot[2]:25d}  {tot[3]:20d}  ({tot[4]})')


if __name__ == '__main__':
    main()
