#!/usr/bin/env python3
"""Inputs for the blind re-score of CatLog's side: the same scoring the plain read had (code, then an agent that does not
see the code's verdicts, then a third look at any difference), on the papers Opus 5.5 read and CatLog has read.
Two readings per paper, each its own item: CatLog's first reading (the earliest work file, its cells converted by its
code) and its catalogue now. An item has a neutral code, its values neutral ids and the same note as the plain read's
inputs, so a scorer cannot tell which reading it scores. private/map.json holds the way back; no scorer opens it.

  python3 rescore2_inputs.py     writes rescore2/inputs/<code>.values.json, rescore2/args.json, rescore2/private/map.json"""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_catlog_first as F  # noqa: E402  (sets the import paths for the kit and units)
import score_catlog as SC  # noqa: E402
import score_hard as SH  # noqa: E402

OUT = HERE / 'rescore2'
UNIT = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}
FIELDS = ('metric', 'raw', 'raw_unit', 'value', 'enzyme', 'variant', 'substrate', 'where', 'conditions', 'metric_note', 'quote')
READ = ('done', 'incomplete', 'needs_supplement')


def code_of(pmid, source):
    return 'x' + hashlib.sha256(f'hard-cases/{pmid}/{source}'.encode()).hexdigest()[:9]


def first_values(p):
    fr = F.first_read(p)
    if not fr:
        return None
    rows = fr[3]
    done = []
    for r in rows:
        one = F.converted(p, [r])
        if one:
            done.append({**one[0], 'where': r.get('location', ''), 'conditions': r.get('conditions', ''),
                         'metric_note': r.get('metric_note', ''), 'quote': r.get('quote', '')})
    return done


def catalogue_values(pmids):
    want, by = set(pmids), {}
    with open(SC.MAIN / 'catalog.jsonl') as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            p = str(r.get('pmid'))
            if p in want and r.get('unit') in UNIT.values():
                by.setdefault(p, []).append({'metric': r.get('metric'), 'value': r.get('value'), 'raw': r.get('raw_value'),
                                             'raw_unit': r.get('raw_unit'), 'enzyme': r.get('enzyme'), 'variant': r.get('variant'),
                                             'substrate': r.get('substrate'), 'where': r.get('location', ''),
                                             'conditions': r.get('conditions', ''), 'metric_note': r.get('metric_note', ''),
                                             'quote': r.get('quote', ''), 'row_id': r.get('row_id')})
    return by


def main():
    summ = {r['pmid']: r for r in json.loads((HERE / 'summary.json').read_text())}
    lead = [p for p, r in summ.items() if r['model'] == 'Opus 5.5' and r['catlog_status'] in READ]
    cat = json.loads((HERE / 'catlog_scores.json').read_text())
    first = json.loads((HERE / 'catlog_first_scores.json').read_text())
    catv = catalogue_values(lead)
    (OUT / 'inputs').mkdir(parents=True, exist_ok=True)
    (OUT / 'private').mkdir(parents=True, exist_ok=True)
    items, back = [], {}
    for p in sorted(lead, key=lambda x: (len(x), x)):
        s = summ[p]
        keyset = 'keys' if s['set'] == 'first' else 'expand/keys'
        base = HERE if s['set'] == 'first' else HERE / 'expand'
        _, cells = SH.cells_of(p, base)
        idx = [c['index'] for c in cells]
        for source, vals, verdicts in (('catalogue', catv.get(p, []), [c['catlog'] for c in cat[p]['cells']]),
                                       ('first', first_values(p), first[p].get('verdicts'))):
            if vals is None or not verdicts:
                continue
            assert len(verdicts) == len(idx), (p, source, len(verdicts), len(idx))
            code = code_of(p, source)
            shown = [{'id': f'v{i}', **{k: v.get(k) for k in FIELDS}, 'value_unit': UNIT.get(v.get('metric'), '')}
                     for i, v in enumerate(vals, 1)]
            (OUT / 'inputs' / f'{code}.values.json').write_text(json.dumps({
                'pmid': p, 'note': 'Every value one reading of this paper stored, converted to catalog units by code (kcat s^-1, '
                                   'Km mM, kcat/Km mM^-1 s^-1). raw and raw_unit are the cell and unit as the reading copied them.',
                'values': shown}, indent=1, ensure_ascii=False))
            back[code] = {'pmid': p, 'source': source, 'class_id': s['class_id'], 'values': len(shown),
                          'code_verdicts': dict(zip(map(str, idx), verdicts))}
            items.append({'code': code, 'pmid': p, 'keys': keyset, 'class_id': s['class_id'],
                          'identity': bool(cat[p].get('identity')) if 'identity' in cat[p] else None,
                          'verdicts': [{'index': i, 'verdict': v} for i, v in zip(idx, verdicts)]})
    # neutral order: an item's place says nothing of its source
    items.sort(key=lambda it: it['code'])
    (OUT / 'private' / 'map.json').write_text(json.dumps(back, indent=1))
    (OUT / 'args.json').write_text(json.dumps({'items': items}, separators=(',', ':')))
    print(f"{len(lead)} papers; {len(items)} items; cells {sum(len(i['verdicts']) for i in items)}, of them for an agent alone "
          f"{sum(1 for i in items for c in i['verdicts'] if c['verdict'] == 'review')}; "
          f"values {sum(b['values'] for b in back.values())}")


if __name__ == '__main__':
    main()
