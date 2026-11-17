#!/usr/bin/env python3
"""The blind re-score of CatLog's side: code against the agent, as the plain read had it.

  python3 rescore2_final.py ties    lists the items and cells where the agent and the code differ (every cell only an
                                    agent can decide is one): code|pmid|set|indices, for the third blind look
  python3 rescore2_final.py final   writes rescore2/final.json: per item its source, cells (code, agent, tie, final)
A cell's final verdict is the plain read's rule: the agent's when it agrees with the code, otherwise the majority of the
code, the agent and the third look (a 'review' from the code is no vote); no majority is 'unresolved'."""
import collections, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE / 'rescore2'


def load(code, tie=False):
    f = R / 'out' / f"{code}{'.tie' if tie else ''}.json"
    return {c['index']: c for c in json.loads(f.read_text())['cells']} if f.exists() else {}


def main():
    back = json.loads((R / 'private' / 'map.json').read_text())
    items = {i['code']: i for i in json.loads((R / 'args.json').read_text())['items']}
    if sys.argv[1] == 'ties':
        out, n = [], 0
        for code, b in back.items():
            a = load(code)
            if not a:
                sys.exit(f'{code}: no first score')
            d = [int(i) for i, v in b['code_verdicts'].items() if a.get(int(i), {}).get('verdict') != v]
            if d:
                out.append(f"{code}|{b['pmid']}|{'e' if items[code]['keys'].startswith('expand') else 'f'}|{','.join(map(str, d))}")
                n += len(d)
        print(json.dumps(sorted(out), separators=(',', ':')))
        print(f'{len(out)} items, {n} cells', file=sys.stderr)
        return
    res, unresolved = [], 0
    for code, b in back.items():
        a, t = load(code), load(code, True)
        cells = []
        for i, c in b['code_verdicts'].items():
            i = int(i)
            va, vt = a.get(i, {}).get('verdict'), t.get(i, {}).get('verdict')
            votes = [v for v in (c, va, vt) if v and v != 'review']
            top = collections.Counter(votes).most_common(1)
            final = va if va == c else top[0][0] if top and top[0][1] >= 2 else 'unresolved'
            unresolved += final == 'unresolved'
            cells.append({'index': i, 'code': c, 'agent': va, 'tie': vt, 'final': final})
        res.append({'code': code, 'pmid': b['pmid'], 'source': b['source'], 'class_id': b['class_id'], 'cells': cells,
                    'fell_in': any(c['final'] == 'trap' for c in cells)})
    (R / 'final.json').write_text(json.dumps(res, indent=1) + '\n')
    agree = sum(1 for r in res for c in r['cells'] if c['code'] != 'review' and c['code'] == c['agent'])
    dec = sum(1 for r in res for c in r['cells'] if c['code'] != 'review')
    print(f'items {len(res)}; code and agent agree on {agree} of {dec} decidable cells; unresolved {unresolved}')
    for s in ('first', 'catalogue'):
        x = [r for r in res if r['source'] == s]
        print(s, 'fell in', sum(r['fell_in'] for r in x), 'of', len(x), '; trap cells',
              sum(c['final'] == 'trap' for r in x for c in r['cells']), 'of', sum(len(r['cells']) for r in x))


if __name__ == '__main__':
    main()
