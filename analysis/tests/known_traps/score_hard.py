#!/usr/bin/env python3
"""Score the hard-case test: did one plain read of each paper store the trap value or the right one?

Inputs: the checked trap keys (<set>/keys/<PMID>.json with <PMID>.check.json: a cell the checker dropped is left out, a
fix replaces the key's object) and the plain reads of run 'hard' in <the kit folder> (values converted by
the same code as every arm: score_w1.arm_values). Output: <set>/scores.json and <set>/scores.tsv (per cell and paper).
  python3 score_hard.py           the first 22 papers (keys/ here)
  python3 score_hard.py expand    the drawn papers (expand/keys/)

Per cell:
  right value  -> 'trap' if a value of the cell's metric and identity is within 0.1% of the trap value (storing it is the
                  error, even beside the right one), else 'right' if one is within 0.1% of the right value, 'other' if a
                  value of that identity is neither, 'missing' if none
  not stored   -> 'trap' if a value of the cell's metric and identity equals the trap value (or, when the key gives
                  none, carries the printed number), else 'right'
Identity: the cell's variant and substrate tokens against the value's (a mutation like E542A must match exactly).
A number hit with no identity hit is 'review' (decided by reading).
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EV = Path('<the kit folder>')
sys.path.insert(0, str(EV / 'code' / 'tools' / 'w1'))
sys.path.insert(0, str(EV / 'code' / 'tools'))
import common_w1 as W  # noqa: E402
import score_w1 as SW  # noqa: E402

STOP = {'the', 'of', 'and', 'a', 'an', 'for', 'with', 'in', 'on', 'to', 'by', 'wild', 'type', 'wt', 'enzyme', 'peptide',
        'substrate', 'mm', 'acid', 'row', 'table'}
MUT = re.compile(r'\b[A-Z]\d{1,4}[A-Z]\b')


def tokens(*xs):
    t = set()
    for x in xs:
        t |= {w for w in re.findall(r'[a-z0-9]+', str(x or '').lower()) if w not in STOP and len(w) > 1}
    return t


def first_number(s):
    m = re.search(r'\d+(?:\.\d+)?', str(s or '').replace(',', ''))
    return float(m.group()) if m else None


def close(a, b, tol=1e-3):
    return a is not None and b is not None and (abs(a - b) <= tol * abs(b) if b else abs(a) < 1e-12)


def same_identity(cell, v):
    cm, vm = set(MUT.findall(str(cell.get('variant')))), set(MUT.findall(str(v.get('variant'))))
    if cm != vm:
        return False
    ct = tokens(cell.get('substrate'))
    vt = tokens(v.get('substrate'))
    return not ct or not vt or bool(ct & vt)


def cells_of(pmid, base):
    key = json.loads((base / 'keys' / f'{pmid}.json').read_text())
    if not key.get('usable', True):
        return key, []
    chk = base / 'keys' / f'{pmid}.check.json'
    verdicts = {}
    if chk.exists():
        for c in json.loads(chk.read_text()).get('cells') or []:
            verdicts[int(c.get('index', -1))] = c
    out = []
    for i, cell in enumerate(key.get('cells') or []):
        v = verdicts.get(i)  # the checkers number cells from 0, as the key lists them
        verdict = (v or {}).get('verdict', 'unchecked')
        if verdict == 'drop':
            continue
        if verdict == 'fix' and isinstance(v.get('fix'), dict):
            cell = {**cell, **{k: v['fix'][k] for k in ('right', 'trap') if k in v['fix']}}
        out.append({**cell, 'index': i, 'check': verdict})
    return key, out


def score_cell(cell, vals, identity_trap=False):
    metric = cell.get('metric')
    cand = [v for v in vals if v.get('metric') == metric]
    if identity_trap:  # the number is right either way: which variant it is filed under decides (the key's how_to_judge)
        rv = (cell.get('right') or {}).get('value')
        hits = [v for v in cand if close(v.get('value'), rv) and
                (not tokens(cell.get('substrate')) or not tokens(v.get('substrate')) or
                 tokens(cell.get('substrate')) & tokens(v.get('substrate')))]
        return ('review', hits) if hits else ('missing', [])
    ident = [v for v in cand if same_identity(cell, v)]
    right, trap = cell.get('right') or {}, cell.get('trap') or {}
    if right.get('kind') == 'value':
        rv, tv = right.get('value'), trap.get('value') if trap.get('kind') == 'value' else None
        def side(v):  # the nearer of the right and the trap value, within 0.1% (a merged '1.2580.04' is 0.6% off)
            dr = abs(v - rv) / abs(rv) if rv else abs(v)
            dt = abs(v - tv) / abs(tv) if tv else float('inf')
            return 'right' if dr <= 1e-3 and dr <= dt else 'trap' if dt <= 1e-3 else None
        r_hit = [v for v in ident if v.get('value') is not None and side(v['value']) == 'right']
        t_hit = [v for v in ident if v.get('value') is not None and side(v['value']) == 'trap']
        if t_hit:
            return 'trap', t_hit + r_hit
        if r_hit:
            return 'right', r_hit
        loose = [v for v in cand if close(v.get('value'), right.get('value')) or
                 (trap.get('kind') == 'value' and close(v.get('value'), trap.get('value')))]
        if loose:
            return 'review', loose
        return ('other', ident) if ident else ('missing', [])
    tv = trap.get('value')  # the value storing it would give, when the key names one; else the printed number
    n = None if tv is not None else first_number(cell.get('printed'))
    hit = [v for v in ident if (tv is not None and close(v.get('value'), tv)) or
           (n is not None and close(first_number(v.get('raw')), n, 1e-9))]
    if hit:
        return 'trap', hit
    loose = [v for v in cand if (tv is not None and close(v.get('value'), tv)) or
             (n is not None and close(first_number(v.get('raw')), n, 1e-9))]
    return ('review', loose) if loose else ('right', [])


def main():
    base = HERE / sys.argv[1] if len(sys.argv) > 1 else HERE
    pmids = sorted(p.stem for p in (base / 'keys').glob('*.json') if not p.name.endswith('.check.json'))
    vals, status, _ = SW.arm_values(W.EVAL, 'A0', 'hard', pmids)
    by = {}
    for v in vals:
        by.setdefault(str(v.get('pmid')), []).append(v)
    rows, papers = [], {}
    for p in pmids:
        key, cells = cells_of(p, base)
        res = {'pmid': p, 'class_id': key.get('class_id'), 'usable': key.get('usable', True), 'read': status.get(p),
               'visible': key.get('visible', ''),
               'cells': len(cells), 'right': 0, 'trap': 0, 'other': 0, 'missing': 0, 'review': 0}
        ident_trap = str(key.get('trap_kind', '')).startswith('identity')
        for c in cells:
            verdict, hits = score_cell(c, by.get(p, []), ident_trap)
            res[verdict] += 1
            rows.append({'pmid': p, 'class_id': key.get('class_id'), 'index': c['index'], 'check': c['check'],
                         'metric': c.get('metric'), 'variant': c.get('variant'), 'substrate': str(c.get('substrate'))[:60],
                         'printed': c.get('printed'), 'right': json.dumps(c.get('right'), ensure_ascii=False)[:120],
                         'trap': json.dumps(c.get('trap'), ensure_ascii=False)[:120], 'verdict': verdict,
                         'stored': '; '.join(f"{h.get('raw')} {h.get('raw_unit')} = {h.get('value')} [{h.get('variant')}]" for h in hits[:4])})
        res['fell_in'] = res['trap'] > 0 if cells else None
        papers[p] = res
    (base / 'scores.json').write_text(json.dumps({'papers': papers, 'cells': rows}, indent=1, ensure_ascii=False) + '\n')
    cols = list(rows[0]) if rows else []
    with open(base / 'scores.tsv', 'w') as f:
        f.write('\t'.join(cols) + '\n')
        for r in rows:
            f.write('\t'.join(str(r[c]).replace('\t', ' ').replace('\n', ' ') for c in cols) + '\n')
    for p, r in papers.items():
        print(f"{p:9s} {r['class_id'] or '':5s} cells {r['cells']:2d}  right {r['right']:2d}  trap {r['trap']:2d}  other {r['other']:2d}"
              f"  missing {r['missing']:2d}  review {r['review']:2d}  {'FELL IN' if r['fell_in'] else ''}")


if __name__ == '__main__':
    main()
