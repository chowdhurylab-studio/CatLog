#!/usr/bin/env python3
"""Match each of the plain reading's wrong values against CatLog's own records (read-only).

For every wrong value (source plain) of the two tests:
- every CatLog reader row of that paper (all read files: kept and older copies), converted by CatLog's own
  units.normalize, same metric within 1.5%;
- the same check across all metrics (a number stored under another label);
- CatLog's catalogue rows for the paper (random test: the frozen copy the test compared, and the catalogue now;
  locked test: the A6-locked run's catalog.jsonl), any metric within 1.5%;
- rejected.jsonl rows of the paper with that number;
- log.tsv lines of the paper (drops, rereads, audits).
Writes match.json next to this script."""
import glob, json, os, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = Path('<the CatLog folder>')
EV = Path('<the kit folder>')
A6 = EV / 'records' / 'runs' / 'A6-locked'
sys.path.insert(0, str(MAIN / 'tools'))
from units import normalize  # noqa: E402

RESULTS = {
    'random': MAIN / 'paper/evidence/random_papers_20261104/full_record/results.json',
    'locked': MAIN / 'paper/evidence/locked_test_20261109/result/results.json',
}
FROZEN = EV / 'records/score_rand/private/catalog_rows.jsonl'  # the random test's CatLog rows as compared (2026-11-05 00:01)
TOL = 0.015


def close(a, b):
    return a is not None and b is not None and b != 0 and abs(a - b) / abs(b) <= TOL


def conv(r):
    try:
        v, u, err = normalize(r['metric'], r.get('raw_value', ''), r.get('unit_for_conversion') or r.get('raw_unit', ''))
    except Exception as e:  # noqa
        return None, None, f'exception {e}'
    return v, u, err


def mtime(f):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(f)))


def reads_of(test, p):
    if test == 'random':
        base = MAIN / 'work'
    else:
        base = A6 / 'work'
    out = []
    for f in sorted(glob.glob(str(base / 'old' / f'{p}.read.*.json'))) + [str(base / f'{p}.read.json')]:
        if not os.path.exists(f):
            continue
        d = json.load(open(f))
        vf = f.replace('.read.', '.verify.')
        v = json.load(open(vf)) if os.path.exists(vf) else None
        out.append({'file': f, 'mtime': mtime(f), 'verify_file': vf if v else None,
                    'verify_mtime': mtime(vf) if v else None, 'data': d, 'verify': v})
    return out


def jsonl(path, p):
    rows = []
    if not os.path.exists(path):
        return rows
    key = f'"pmid": "{p}"'
    with open(path) as fh:
        for line in fh:
            if key in line:
                rows.append(json.loads(line))
    return rows


def log_lines(path, p):
    out = []
    with open(path) as fh:
        for line in fh:
            parts = line.rstrip('\n').split('\t')
            if len(parts) > 1 and parts[1] == p:
                out.append(parts)
    return out


def main():
    wrong = []
    for test, f in RESULTS.items():
        d = json.load(open(f))
        for w in d['wrong']:
            if w['source'] == 'plain':
                wrong.append((test, w))
    print(len(wrong), 'plain wrong values')
    cache = {}
    out = []
    for test, w in wrong:
        p = w['pmid']
        s = w['shown']
        if (test, p) not in cache:
            reads = reads_of(test, p)
            if test == 'random':
                rej = jsonl(MAIN / 'rejected.jsonl', p)
                cat_frozen = jsonl(FROZEN, p)
                cat_now = jsonl(MAIN / 'catalog.jsonl', p)
                logs = log_lines(MAIN / 'log.tsv', p)
            else:
                rej = jsonl(A6 / 'rejected.jsonl', p)
                cat_frozen = jsonl(A6 / 'catalog.jsonl', p)
                cat_now = []
                logs = log_lines(A6 / 'log.tsv', p)
            cache[(test, p)] = (reads, rej, cat_frozen, cat_now, logs)
        reads, rej, cat_frozen, cat_now, logs = cache[(test, p)]
        val = float(s['value'])
        rec = {'test': test, 'pmid': p, 'claim_id': w['claim_id'], 'kind': w['kind'], 'verdict': w['verdict'],
               'metric': s['metric'], 'value': val, 'unit': s['unit'], 'variant': s['variant'], 'substrate': s['substrate'],
               'raw': (w.get('stored') or {}).get('raw'), 'raw_unit': (w.get('stored') or {}).get('raw_unit'),
               'where': (w.get('stored') or {}).get('where'),
               'reads': [], 'catalog_frozen_hits': [], 'catalog_now_hits': [], 'rejected_hits': [],
               'log_actions': sorted({x[2] for x in logs})}
        for rd in reads:
            d = rd['data']
            hits_same, hits_other = [], []
            for i, r in enumerate(d.get('rows') or []):
                if r.get('censored'):
                    continue
                v, u, err = conv(r)
                if v is None:
                    continue
                if close(v, val):
                    verdict = None
                    if rd['verify']:
                        vv = [x for x in rd['verify'].get('verdicts', []) if x.get('i') == i]
                        verdict = vv[0] if vv else None
                    h = {'i': i, 'metric': r['metric'], 'raw_value': r.get('raw_value'), 'raw_unit': r.get('raw_unit'),
                         'value': v, 'unit': u, 'variant': r.get('variant'), 'substrate': r.get('substrate'),
                         'location': r.get('location'), 'quote': (r.get('quote') or '')[:200],
                         'metric_note': r.get('metric_note'), 'conditions': (r.get('conditions') or '')[:200],
                         'verify': {k: verdict.get(k) for k in ('verdict', 'reason')} if verdict else None}
                    (hits_same if r['metric'] == s['metric'] else hits_other).append(h)
            rec['reads'].append({'file': rd['file'], 'mtime': rd['mtime'], 'verify_file': rd['verify_file'],
                                 'verify_mtime': rd['verify_mtime'], 'n_rows': len(d.get('rows') or []),
                                 'model': d.get('model'), 'note': d.get('note'),
                                 'missed_count': (rd['verify'] or {}).get('missed_count'),
                                 'same_metric_hits': hits_same, 'other_metric_hits': hits_other})
        for name, rows in (('catalog_frozen_hits', cat_frozen), ('catalog_now_hits', cat_now)):
            for r in rows:
                if close(r.get('value'), val):
                    rec[name].append({'row_id': r.get('row_id'), 'metric': r.get('metric'), 'raw_value': r.get('raw_value'),
                                      'raw_unit': r.get('raw_unit'), 'value': r.get('value'), 'unit': r.get('unit'),
                                      'variant': r.get('variant'), 'substrate': r.get('substrate'),
                                      'location': r.get('location'), 'quote': (r.get('quote') or '')[:160]})
        for r in rej:
            v, u, err = conv(r) if r.get('metric') in ('kcat', 'Km', 'kcat/Km') else (None, None, None)
            if close(v, val) or close(r.get('value'), val):
                rec['rejected_hits'].append({'metric': r.get('metric'), 'raw_value': r.get('raw_value'),
                                             'raw_unit': r.get('raw_unit'), 'location': r.get('location'),
                                             'substrate': r.get('substrate'), 'variant': r.get('variant'),
                                             'why': r.get('why'), 'checked': r.get('checked')})
        rec['n_catalog_frozen'] = len(cat_frozen)
        rec['n_catalog_now'] = len(cat_now)
        rec['n_rejected'] = len(rej)
        out.append(rec)
    (HERE / 'match.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    for r in out:
        same = [(Path(x['file']).name, [(h['i'], h['metric'], h['raw_value'], h['raw_unit'], h['substrate'], h['variant'], h['location'])
                                        for h in x['same_metric_hits']]) for x in r['reads'] if x['same_metric_hits']]
        other = [(Path(x['file']).name, [(h['i'], h['metric'], h['raw_value'], h['raw_unit'], h['substrate'], h['variant'])
                                         for h in x['other_metric_hits']]) for x in r['reads'] if x['other_metric_hits']]
        print(r['test'], r['pmid'], r['claim_id'], r['metric'], r['value'], r['unit'], '| reads', len(r['reads']),
              '| same', same, '| other', other,
              '| cat_frozen', [(h['metric'], h['raw_value'], h['substrate'], h['variant']) for h in r['catalog_frozen_hits']],
              '| cat_now', [(h['metric'], h['raw_value'], h['substrate'], h['variant']) for h in r['catalog_now_hits']],
              '| rej', len(r['rejected_hits']), '| log', r['log_actions'])


if __name__ == '__main__':
    main()
