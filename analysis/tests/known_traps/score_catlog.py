#!/usr/bin/env python3
"""CatLog's side of the hard-case test: the same checked keys, scored with the same code (score_hard.score_cell)
against what CatLog's catalogue holds now for each paper (catalog.jsonl; values CatLog refused or dropped are not in it).

  python3 score_catlog.py          both sets (keys/ and expand/keys/)
Writes catlog_scores.json here: per paper and cell, CatLog's verdict (right, trap, other, missing, review) next to the
plain read's (scores.json, expand/scores.json, and the blind re-score where it ran: rescore/final.json,
expand/rescore/final.json).
A 'missing' on a cell whose right value is a number means CatLog holds no value for it (refused, dropped, or a row
another reading split differently); on a not_stored cell, holding nothing is 'right'."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[2]
sys.path.insert(0, str(HERE))
import score_hard as SH  # noqa: E402


def catalog_values(pmids):
    want, by = set(pmids), {}
    with open(MAIN / 'catalog.jsonl') as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            p = str(r.get('pmid'))
            if p in want:
                by.setdefault(p, []).append({'metric': r.get('metric'), 'value': r.get('value'),
                                             'raw': r.get('raw_value'), 'raw_unit': r.get('raw_unit'),
                                             'enzyme': r.get('enzyme'), 'variant': r.get('variant'),
                                             'substrate': r.get('substrate'), 'id': r.get('row_id')})
    return by


def plain_final(base):
    f = base / 'rescore' / 'final.json'
    if not f.exists():
        return {}
    return {p['pmid']: {c['index']: c['final'] for c in p['cells']} for p in json.loads(f.read_text())}


def main():
    out = {}
    for name, base in (('first', HERE), ('expand', HERE / 'expand')):
        pmids = sorted(p.stem for p in (base / 'keys').glob('*.json') if not p.name.endswith('.check.json'))
        cat = catalog_values(pmids)
        code_plain = json.loads((base / 'scores.json').read_text()) if (base / 'scores.json').exists() else {'cells': []}
        plain_code = {(c['pmid'], c['index']): c['verdict'] for c in code_plain['cells']}
        plain_blind = plain_final(base)
        for p in pmids:
            key, cells = SH.cells_of(p, base)
            if not key.get('usable', True):
                continue
            ident = str(key.get('trap_kind', '')).startswith('identity')
            rows = []
            for c in cells:
                v, hits = SH.score_cell(c, cat.get(p, []), ident)
                plain = plain_blind.get(p, {}).get(c['index']) or plain_code.get((p, c['index']))
                rows.append({'index': c['index'], 'metric': c.get('metric'), 'catlog': v,
                             'catlog_rows': [h.get('id') for h in hits[:6]], 'plain': plain})
            out[p] = {'set': name, 'class_id': key.get('class_id'), 'visible': key.get('visible', ''),
                      'cells': rows, 'catlog_trap': sum(r['catlog'] == 'trap' for r in rows),
                      'plain_trap': sum(r['plain'] == 'trap' for r in rows), 'n': len(rows),
                      'catlog_rows_now': len(cat.get(p, []))}
    (HERE / 'catlog_scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    tot = {'papers': len(out), 'catlog_papers_with_trap': sum(1 for r in out.values() if r['catlog_trap']),
           'plain_papers_with_trap': sum(1 for r in out.values() if r['plain_trap']),
           'cells': sum(r['n'] for r in out.values()), 'catlog_trap_cells': sum(r['catlog_trap'] for r in out.values()),
           'plain_trap_cells': sum(r['plain_trap'] for r in out.values())}
    print(json.dumps(tot))
    for p, r in sorted(out.items(), key=lambda kv: (kv[1]['class_id'], kv[0])):
        cv = [c['catlog'] for c in r['cells']]
        print(f"{p:10s} {r['class_id']:5s} {r['set']:6s} plain trap {r['plain_trap']:2d}/{r['n']:2d} | CatLog now: trap {cv.count('trap'):2d} "
              f"right {cv.count('right'):2d} missing {cv.count('missing'):2d} other {cv.count('other'):2d} review {cv.count('review'):2d}")


if __name__ == '__main__':
    main()
