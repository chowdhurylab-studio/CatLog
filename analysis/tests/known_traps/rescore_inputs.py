#!/usr/bin/env python3
"""Inputs for the blind re-score: each plain read's stored values, converted to catalog units by the same code as every
arm (score_w1.arm_values), plus the read's own note, so a scorer can judge whether the reader saw the problem.

  python3 rescore_inputs.py [set]     set = '' (the first 22: keys/ here) or 'expand' (expand/keys/)
Writes <set>/rescore/inputs/<PMID>.values.json and <set>/rescore/args.json (each paper's code verdicts from
<set>/scores.json, which score_hard.py writes first)."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EV = Path('<the kit folder>')
sys.path.insert(0, str(EV / 'code' / 'tools' / 'w1'))
sys.path.insert(0, str(EV / 'code' / 'tools'))
import common_w1 as W  # noqa: E402
import score_w1 as SW  # noqa: E402

UNIT = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}


def main():
    base = HERE / sys.argv[1] if len(sys.argv) > 1 else HERE
    pmids = sorted(p.stem for p in (base / 'keys').glob('*.json') if not p.name.endswith('.check.json'))
    vals, status, _ = SW.arm_values(W.EVAL, 'A0', 'hard', pmids)
    by = {}
    for v in vals:
        by.setdefault(str(v['pmid']), []).append({**{k: v.get(k) for k in ('id', 'metric', 'raw', 'raw_unit', 'value', 'enzyme',
                                                                              'variant', 'substrate', 'where', 'conditions',
                                                                              'metric_note', 'quote')},
                                                   'value_unit': UNIT.get(v.get('metric'), '')})
    out = base / 'rescore' / 'inputs'
    out.mkdir(parents=True, exist_ok=True)
    for p in pmids:
        f = W.out_file(W.EVAL, 'A0', 'hard', None, p)
        note = json.loads(f.read_text()).get('note', '') if f.exists() else ''
        (out / f'{p}.values.json').write_text(json.dumps({
            'pmid': p, 'reader_note': note,
            'note': 'Every value one plain read of this paper stored, converted to catalog units by code (kcat s^-1, Km mM, '
                    'kcat/Km mM^-1 s^-1). raw and raw_unit are the cell and unit as the read copied them; reader_note is the '
                    "read's own note on the paper.",
            'values': by.get(p, [])}, indent=1, ensure_ascii=False))
    scores = json.loads((base / 'scores.json').read_text())
    papers = []
    for p in pmids:
        k = json.loads((base / 'keys' / f'{p}.json').read_text())
        code = [{'index': c['index'], 'verdict': c['verdict']} for c in scores['cells'] if c['pmid'] == p]
        if code:
            papers.append({'pmid': p, 'class_id': k.get('class_id'),
                           'identity': str(k.get('trap_kind', '')).startswith('identity'), 'code': code})
    (base / 'rescore' / 'args.json').write_text(json.dumps({'papers': papers}, separators=(',', ':'), ensure_ascii=False))
    print(f'{len(pmids)} papers, {sum(len(by.get(p, [])) for p in pmids)} stored values; {len(papers)} with scored cells '
          f'-> {base / "rescore"}')


if __name__ == '__main__':
    main()
