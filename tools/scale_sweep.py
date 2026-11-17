"""Measurements whose printed kcat/Km misses kcat ÷ Km by a unit factor (CLAUDE.md open item on scale errors).

A table whose unit header is misprinted stores a whole column off by an exact unit factor (2026-10-19: 15659684
Table 3 kcat/Km 'mM^-1 min^-1' really µM^-1 min^-1; 42228390 Table 2 kcat 's^-1' really min^-1 and Km 'µM' really
mM; 25022854 Table 1 kcat/Km '10^3 M^-1 min^-1' really 10^6). Where the paper prints kcat, Km and kcat/Km for one
measurement, F = printed kcat/Km ÷ (kcat ÷ Km) then sits near 60^a × 1000^b instead of 1. This lists every such
measurement (F within 10% of a unit factor, widened by the rounding of the printed cells, at most 35%), grouped by
paper and table: a table where most measurements share one factor is the strong signal (a whole column off), a lone
one may be a coincidence or a typo in one cell.

state     open   the stored values miss closure by that factor;
          fixed  the stored values close, but the printed headers (raw_unit, no unit_for_conversion) miss by the
                 factor: a reader, verifier or unitfix already chose another unit (unitfix if log.tsv says so).
override  the metrics whose plain printed unit (no power of ten in it) a reader, verifier or unitfix replaced: a
          judgement that this header is misprinted, made by choosing one column (42228390's verifier chose kcat/Km;
          kcat and Km were the misprinted ones).
db        per metric, the factor between CatLog's value and the same paper's database value when that is a unit
          factor too (dbcompare: factor = CatLog / database), with its status. The databases often copy a misprinted
          header (SABIO-RK did for 15659684), so they are context, never evidence.

Blind spots: a table whose columns are ALL misprinted consistently closes (42228390), and a table without a printed
kcat cannot be tested (15659684 printed Vmax in U/mg); those need Vmax/[E], molecular mass or figure axes.

Writes work/scale_sweep.tsv (one line per flagged measurement, strongest tables first); prints counts by factor and
the top tables; `checked` gives the verdict of a paper check already done (work/scale_<PMID>.json). `tasks` writes
work/scale_<PMID>.task.json per paper for the paper check (prompts/scale.md): the paper's files and every catalog row
of it with the flagged measurements marked, no database numbers (the check reads blind). Then `catlog.py unitfix` /
`drop --file` apply what the check shows.

    python3 tools/scale_sweep.py
    python3 tools/scale_sweep.py tasks <PMID> ...
"""
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT))
from units import normalize, clean  # noqa: E402
from catlog import locked  # noqa: E402  (the method paper's test set: never swept)

TOL, TOL_MAX = 0.10, 0.35
MULTIPLIER = re.compile(r'10\s*\^|(?:x|\*)\s*10|\d[eE][-+]?\d')  # a header power of ten, as opposed to a plain unit
METRICS = ('kcat', 'Km', 'kcat/Km')


def label(a, b):
    """60^a x 1000^b written out: '10^3', '1/60', '60x10^3', '10^3/60'."""
    num, den = [], []
    for e, txt in ((a, lambda n: '60' if n == 1 else '3600'), (b, lambda n: f'10^{3 * n}')):
        (num if e > 0 else den if e < 0 else []).append(txt(abs(e)))
    return '×'.join(num or ['1']) + ('/' + '×'.join(den) if den else '')


FACTORS = [(60.0 ** a * 1000.0 ** b, label(a, b)) for a in range(-2, 3) for b in range(-3, 4) if (a, b) != (0, 0)]


def rounding(raw):
    """Relative rounding of a printed cell's central value: '2' -> 0.25, '0.05' -> 0.1, '225' -> 0.002."""
    m = re.search(r'\d[\d,]*(?:\.\d*)?|\.\d+', clean(raw).split('±')[0])
    if not m:
        return 0.0
    tok = m.group(0).replace(',', '')
    try:
        v = float(tok)
    except ValueError:
        return 0.0
    ulp = 10.0 ** -len(tok.split('.')[1]) if '.' in tok else 1.0
    return 0.5 * ulp / v if v else 0.0


def near(f, tol):
    """The unit factor f sits within tol of, else None."""
    if not f or f <= 0 or not math.isfinite(f):
        return None
    for u, name in FACTORS:
        if abs(f / u - 1) <= tol:
            return name
    return None


def table_of(loc):
    """'Table 2', 'Table S3', 'Fig. 4' from a location; prose locations are 'text'."""
    m = re.search(r'\b(Supplementa\w*\s+)?(Table|Fig(?:ure)?\.?|Scheme)\s*(S?\s*[0-9IVXL]+[A-Za-z]?)', loc or '', re.I)
    if not m:
        return 'text'
    kind = 'Table' if m.group(2).lower().startswith('tab') else 'Fig.' if m.group(2).lower().startswith('fig') else 'Scheme'
    return ('Supplementary ' if m.group(1) else '') + f"{kind} {m.group(3).replace(' ', '')}"


def printed_value(metric, ev):
    """The value converted with the printed unit only (no unit_for_conversion)."""
    v, _, err = normalize(metric, ev.get('raw_value', ''), ev.get('raw_unit', ''))
    return None if err else v


def unitfixed_rows():
    out = set()
    for l in open(ROOT / 'log.tsv', encoding='utf-8'):
        f = l.rstrip('\n').split('\t')
        if len(f) > 4 and (f[2] == 'unitfix' or f[2] == 'audit_keep' and f[4].startswith('unit corrected')):
            out.add(f[3])  # a row a unitfix brought back from an audit drop logs only the audit_keep
    return out


def db_note(d):
    out = []
    for m in METRICS:
        c = (d.get('database_check') or {}).get(m) or {}
        name = near(c.get('factor'), TOL) if c.get('factor') else None
        if name:
            out.append(f"{m}:{name} {c.get('status')}{'/' + c['cause_by'] if c.get('cause_by') else ''}"
                       f"({','.join(c.get('sources') or [])})")
    return '; '.join(out)


def checked():
    """(pmid, table) -> the paper check's verdict (work/scale_<PMID>.json; a `review` on the file overrides it)."""
    out = {}
    for f in (ROOT / 'work').glob('scale_*.json'):
        if f.name.endswith('.task.json'):
            continue
        try:
            d = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for t in d.get('tables') or []:
            v = (d.get('review') or {}).get('verdict') or t.get('verdict', '')
            out[(str(d.get('pmid')), table_of(t.get('table', '')))] = f"{v} ({f.name})"
    return out


def main():
    fixed_ids, done, held = unitfixed_rows(), checked(), locked()
    flagged, triples = [], Counter()
    for line in open(ROOT / 'catlog_wide.jsonl', encoding='utf-8'):
        d = json.loads(line)
        if d['pubmed_id'] in held:
            continue
        if d.get('kcat_over_km_source') != 'printed' or not all(d.get(k) for k in ('kcat', 'km', 'kcat_over_km')):
            continue
        ev = d.get('evidence') or {}
        if not all(m in ev for m in METRICS):
            continue
        table = table_of(ev['kcat/Km'].get('location'))
        key = (d['pubmed_id'], table)
        triples[key] += 1
        tol = min(TOL_MAX, TOL + sum(rounding(ev[m].get('raw_value')) for m in METRICS))
        f_stored = d['kcat_over_km'] / (d['kcat'] / d['km'])
        pv = {m: printed_value(m, ev[m]) for m in METRICS}
        f_printed = pv['kcat/Km'] / (pv['kcat'] / pv['Km']) if all(pv.values()) else None
        name = near(f_stored, tol)
        state = 'open'
        if not name:
            name = near(f_printed, tol) if f_printed else None
            if not name:
                continue
            ufc = [m for m in METRICS if ev[m].get('unit_for_conversion')]
            state = ('fixed:unitfix' if any(ev[m]['row_id'] in fixed_ids for m in ufc) else 'fixed:reader') + \
                    f"({','.join(ufc)})"
        flagged.append({
            'pmid': d['pubmed_id'], 'table': table, 'factor': name, 'state': state,
            'f_stored': f'{f_stored:.4g}', 'f_printed': f'{f_printed:.4g}' if f_printed else '', 'tol': f'{tol:.2f}',
            'enzyme': d.get('enzyme_name', ''), 'variant': d.get('mutation_signature') or 'wild type',
            'substrate': d.get('substrate_name', ''),
            **{f'{m}_printed': ' | '.join(x for x in (ev[m].get('raw_value', ''), ev[m].get('raw_unit', ''),
                                                       ev[m].get('unit_for_conversion') and 'used ' + ev[m]['unit_for_conversion']) if x)
               for m in METRICS},
            'override': ','.join(m for m in METRICS if ev[m].get('unit_for_conversion') and not MULTIPLIER.search(
                clean(ev[m].get('raw_unit', '')))),
            'db': db_note(d), 'audit': json.dumps(d['audit'], ensure_ascii=False) if d.get('audit') else '',
            'location': ev['kcat/Km'].get('location', ''), 'measurement_id': d.get('measurement_id', ''),
            'row_ids': ','.join(ev[m]['row_id'] for m in METRICS),
        })
    groups = defaultdict(list)
    for r in flagged:
        groups[(r['pmid'], r['table'])].append(r)
    for key, rs in groups.items():
        by = Counter(r['factor'] for r in rs)  # open and fixed together: an open row left in a fixed column counts
        for r in rs:
            r['table_triples'] = triples[key]
            r['table_same'] = by[r['factor']]
            r['column'] = 'yes' if r['table_same'] >= 2 and r['table_same'] >= 0.6 * triples[key] else ''
            r['checked'] = done.get(key, '')
    flagged.sort(key=lambda r: (r['state'] != 'open', r['column'] != 'yes', -r['table_same'], r['pmid'], r['table']))
    cols = ['pmid', 'table', 'factor', 'state', 'column', 'checked', 'table_same', 'table_triples', 'f_stored', 'f_printed',
            'tol', 'enzyme', 'variant', 'substrate', 'kcat_printed', 'Km_printed', 'kcat/Km_printed', 'override', 'db', 'audit',
            'location', 'measurement_id', 'row_ids']
    out = ROOT / 'work' / 'scale_sweep.tsv'
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, cols, delimiter='\t', extrasaction='ignore')
        w.writeheader()
        w.writerows(flagged)

    n_tri = sum(triples.values())
    opened = [r for r in flagged if r['state'] == 'open']
    print(f'{n_tri:,} measurements with printed kcat, Km and kcat/Km; {len(flagged):,} miss closure by a unit factor '
          f'({len(opened):,} open, {len(flagged) - len(opened):,} already converted with another unit) -> {out.relative_to(ROOT)}')
    print('\nopen, by factor (F = printed kcat/Km ÷ (kcat ÷ Km)): measurements / tables / of which whole-column tables')
    for name, n in Counter(r['factor'] for r in opened).most_common():
        tabs = {(r['pmid'], r['table']) for r in opened if r['factor'] == name}
        cols_ = {(r['pmid'], r['table']) for r in opened if r['factor'] == name and r['column']}
        print(f'  {name:>12}  {n:5}  {len(tabs):4}  {len(cols_):4}')
    seen, top = set(), []
    for r in opened:
        k = (r['pmid'], r['table'], r['factor'])
        if r['column'] and k not in seen:
            seen.add(k)
            top.append(r)
    print(f'\nwhole-column tables, open ({len(top)}): pmid, table, factor, same/triples, db, paper check')
    for r in top[:60]:
        dbs = {x.split(' ')[0] + ' ' + x.split(' ')[1].split('(')[0] for g in groups[(r['pmid'], r['table'])] if g['factor'] == r['factor']
               for x in g['db'].split('; ') if x}
        print(f"  {r['pmid']:>10}  {r['table']:<22} {r['factor']:>9}  {r['table_same']}/{r['table_triples']}  "
              f"{'; '.join(sorted(dbs))[:60]}  {r['checked'] or 'not checked'}")
    fixed = {(r['pmid'], r['table'], r['factor'], r['state']) for r in flagged if r['state'] != 'open'}
    print(f'\nalready converted with another unit ({len(fixed)} tables):')
    for k in sorted(fixed)[:40]:
        print('  ', *k)


def tasks(pmids):
    """work/scale_<PMID>.task.json: what the paper check needs, from the sweep's tsv, papers.tsv and the catalog."""
    held = locked() & set(pmids)
    if held:
        print(f'left out (the method paper\'s test set): {" ".join(sorted(held))}', file=sys.stderr)
        pmids = [p for p in pmids if p not in held]
    sweep = [r for r in csv.DictReader(open(ROOT / 'work' / 'scale_sweep.tsv', encoding='utf-8'), delimiter='\t')
             if r['pmid'] in pmids]
    papers = {r['pmid']: r for r in csv.DictReader(open(ROOT / 'papers.tsv', encoding='utf-8'), delimiter='\t')
              if r['pmid'] in pmids}
    rows = defaultdict(list)
    keep = ('row_id', 'metric', 'raw_value', 'raw_unit', 'unit_for_conversion', 'value', 'unit', 'enzyme', 'organism',
            'variant', 'substrate', 'cosubstrate', 'pH', 'temperature_C', 'location', 'quote', 'metric_note')
    for line in open(ROOT / 'catalog.jsonl', encoding='utf-8'):
        if any(f'"pmid": "{p}"' in line for p in pmids):
            r = json.loads(line)
            rows[r['pmid']].append({k: r.get(k, '') for k in keep})
    for p in pmids:
        text = ROOT / 'texts' / f'{p}.txt'
        if p not in papers or not text.exists():
            print(f'{p}: no paper text or papers.tsv line; no task written')
            continue
        src = papers[p].get('text_source', '')
        flagged = defaultdict(list)
        for r in sweep:
            if r['pmid'] == p:
                flagged[(r['table'], r['factor'], r['state'])].append({
                    'enzyme': r['enzyme'], 'variant': r['variant'], 'substrate': r['substrate'],
                    'closure_factor': r['f_stored'], 'printed_factor': r['f_printed'],
                    'row_ids': r['row_ids'].split(',')})
        supp = ROOT / 'texts' / f'{p}.supp.txt'
        task = {'pmid': p, 'doi': papers[p].get('doi', ''), 'title': papers[p].get('title', ''),
                'text': f'texts/{p}.txt', 'supplement': f'texts/{p}.supp.txt' if supp.exists() else '',
                'original_file': src.split(':', 1)[1] if ':' in src else src,
                'glyph_warning': text.read_text(errors='replace').startswith('GLYPH WARNING'),
                'flagged': [{'table': t, 'factor': f, 'state': s, 'measurements': ms}
                            for (t, f, s), ms in flagged.items()],
                'rows': rows[p]}
        out = ROOT / 'work' / f'scale_{p}.task.json'
        out.write_text(json.dumps(task, ensure_ascii=False, indent=1))
        print(f'{p}: {sum(len(m) for m in flagged.values())} flagged measurements, {len(rows[p])} rows -> {out.relative_to(ROOT)}')


if __name__ == '__main__':
    if sys.argv[1:2] == ['tasks']:
        tasks(sys.argv[2:])
    else:
        main()
