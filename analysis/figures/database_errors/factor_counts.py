#!/usr/bin/env python3
"""When CatLog and an enzyme database give the same paper different numbers, by how much do they differ? Writes
factor_counts.json beside this file, the data of the figure (build_figure.py).

Source: sources/database_corrections.tsv, one line per value where CatLog and a database (BRENDA, SABIO-RK, OED, SKiD,
UniProt, STRENDA DB) differ by 1.5x or more and an agent decided it against the paper (prompts/dbcheck.md); the line in
effect per value and database is the latest (paper/numbers.py reads it the same way). CatLog's value is the catalog's
converted value (catalog.jsonl, else the row's last refusal in rejected.jsonl for a value dropped since). Both are in
catalog units (kcat s^-1, Km mM, kcat/Km mM^-1 s^-1), so their ratio is unit-free.

The ratio is the one the agent judged: the database's number over CatLog's value at the time of the check, from the
check's task file; CatLog's value today only where no task file exists. A ratio is "a unit factor" when it is within 1%
of a power of ten other than 1 (a prefix, a x10^n header, a slipped decimal point or exponent), or of 60 or 3600 either
way up (minutes or hours against seconds), alone or times or over 1000. Run from catlog-v2:
python3 paper/figures/database_errors/factor_counts.py"""
import collections, csv, glob, json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
lines = list(csv.DictReader(open(os.path.join(ROOT, 'sources', 'database_corrections.tsv'), encoding='utf-8'),
                            delimiter='\t', quoting=csv.QUOTE_NONE))
latest = {}
for i, r in sorted(enumerate(lines), key=lambda x: (x[1]['date'], x[0])):
    latest[(r['row_id'], r['database'])] = r
cat = {}
for l in open(os.path.join(ROOT, 'catalog.jsonl')):
    r = json.loads(l)
    cat[r['row_id']] = r
rej = {}
for l in open(os.path.join(ROOT, 'rejected.jsonl')):
    r = json.loads(l)
    if r.get('row_id'):
        rej[r['row_id']] = r

KIND = {'corrected': 'database misread the paper', 'catlog_wrong': 'CatLog was wrong',
        'different_measurement': 'both right, different measurements', 'ambiguous': 'the paper does not decide'}
kind = lambda r: ("database copied the paper's own misprint" if r['cause'] == 'paper_unit_misprint'
                  else KIND['corrected']) if r['verdict'] == 'corrected' else KIND[r['verdict']]
TOL = math.log10(1.01)
FACTORS = sorted({b for b in range(-13, 14)} |                       # powers of ten: prefixes, x10^n headers, decimals
                 {b + a * math.log10(t) for b in (-3, 0, 3) for t in (60, 3600) for a in (1, -1)})   # time units
num = re.compile(r'^\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?)')

# The ratio the agent judged: each check writes a task file and a verdict file with the same time stamp
# (work/old/dbcheck_<PMID>.task.<t>.json and dbcheck_<PMID>.<t>.json). The task gives, per value and database, the
# database's number as a multiple of CatLog's value at that time ('times_catlog'); CatLog's value today can differ (ten
# of its twelve wrong values were corrected after the check). A verdict line in the tsv is paired with the latest check
# of its paper whose verdict file holds the same value, database and verdict, made on or before the line's day.
checks = collections.defaultdict(list)                     # pmid -> [(made, ratios, verdict keys)]
for f in glob.glob(os.path.join(ROOT, 'work', 'old', 'dbcheck_*.task.*.json')) + \
        glob.glob(os.path.join(ROOT, 'work', 'dbcheck_*.task.*.json')):
    t = json.load(open(f))
    ratios = {(v['row_id'], d['database']): d.get('times_catlog') for v in t.get('values') or []
              for d in v.get('databases') or [] if d.get('times_catlog')}
    vf = f.replace('.task.', '.')
    keys = set()
    if os.path.exists(vf):
        for v in json.load(open(vf)).get('verdicts') or []:
            for db in str(v.get('database') or '').split(','):
                keys.add((v.get('row_id'), db.strip(), v.get('verdict')))
    checks[str(t['pmid'])].append((t.get('made') or '', ratios, keys))


def judged(r):
    """times_catlog of the check that gave this verdict, else None."""
    dbs = [d.strip() for d in r['database'].split(',')]
    for made, ratios, keys in sorted(checks.get(r['pmid'], []), key=lambda m: m[0], reverse=True):
        if made[:10] > r['date'] or not any((r['row_id'], db, r['verdict']) in keys for db in dbs):
            continue
        for db in dbs:
            if (r['row_id'], db) in ratios:
                return ratios[(r['row_id'], db)]
    return None


points = []
for r in latest.values():
    t = judged(r)
    if t:
        x, source = math.log10(t), 'task file'
    else:                                                     # no task file: CatLog's value today
        c = cat.get(r['row_id']) or rej.get(r['row_id'])
        x, source = math.log10(float(num.match(r['database_value']).group(1)) / float(c['value'])), 'catalog today'
    f = min(FACTORS, key=lambda f: abs(10 ** (x - f) - 1))
    on_factor = abs(10 ** (x - f) - 1) <= 0.01 and f != 0   # within 1% of a unit factor other than 1
    db = math.log10(float(num.match(r['database_value']).group(1)))     # the database's number, catalog units
    points.append({'pmid': r['pmid'], 'database': r['database'], 'metric': r['metric'], 'log10_ratio': round(x, 5),
                   'log10_database': round(db, 5), 'log10_catlog': round(db - x, 5),   # CatLog's value at the check
                   'factor': round(f, 4) if on_factor else None, 'kind': kind(r), 'cause': r['cause'],
                   'ratio_from': source})
on = [p for p in points if p['factor'] is not None]
out = {'source': 'sources/database_corrections.tsv (latest line per value and database), catalog.jsonl, rejected.jsonl',
       'database_values': len(points), 'papers': len({p['pmid'] for p in points}),
       'on_a_unit_factor': len(on), 'papers_on_a_unit_factor': len({p['pmid'] for p in on}),
       'kinds': collections.Counter(p['kind'] for p in points),
       'ratio_from': collections.Counter(p['ratio_from'] for p in points), 'points': points}
json.dump(out, open(os.path.join(HERE, 'factor_counts.json'), 'w'), indent=0)
print({k: v for k, v in out.items() if k != 'points'})
