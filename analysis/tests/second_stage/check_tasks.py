#!/usr/bin/env python3
"""Stage 2's page check (CHECK_PLAN.md): the task file of each paper with a value the curation, CatLog and the full
pipeline run (RGF) do not all three agree on. Three readings as A, B, C in a random order (seed 20261111), each with its
full list for the paper and a 'judge' flag on the disputed values. -> records/stage2_check/<PMID>.task.json,
_key.json (which reading is whose), _papers.json (part 1: papers with a disputed kcat; part 2: the others; the 6 papers
of part 1 that get a second agent)."""
import importlib.util, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('s2', HERE / 'score_stage2.py')
s2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s2)
W, C, h2h = s2.W, s2.C, s2.h2h
OUT = Path('<the kit folder>') / 'records' / 'stage2_check'
SEED = 20261111


def readings():
    vals = json.loads((W.eval_paths(W.EVAL)['score'].parent / 'score_locked' / 'private' / 'values.json').read_text())
    sets = {r['pmid']: r['gold_set'] for r in W.read_tsv(W.KIT / 'holdout_374.tsv')}
    papers = sorted((p for p in vals['papers'] if sets.get(p) in ('enzyextract', 'both')), key=W.pmid_key)
    ps = set(papers)
    gold, _ = h2h.rows_to_values(s2.curation(), 'ee_manual', ps)
    gold = [g for g in gold if g['value'] is not None]
    cat = s2.no_repeats([v for v in vals['catlog'] if v['pmid'] in ps])
    rgf = s2.no_repeats(h2h.rows_to_values(s2.runs()['RGF'], 'run_RGF', ps)[0])
    return papers, {'curation': gold, 'catlog': cat, 'rgf': rgf}


def disputed(R):
    """{source: set of indexes to judge}: curation values not matched by both others; CatLog and run values the curation
    does not match."""
    pc, _, cu = C.match(R['curation'], R['catlog'])
    pr, _, ru = C.match(R['curation'], R['rgf'])
    both = {i for i, _, _ in pc} & {i for i, _, _ in pr}
    return {'curation': {i for i in range(len(R['curation'])) if i not in both}, 'catlog': set(cu), 'rgf': set(ru)}, both


def shown(v, src):
    cell = v.get('raw') if src != 'catlog' else f"{v.get('raw')} {v.get('raw_unit') or ''}".strip()
    return {'metric': v['metric'], 'value_in_catalog_units': v['value'], 'cell_as_this_reading_wrote_it': cell,
            'enzyme': str(v.get('enzyme') or '').strip()[:120], 'substrate': str(v.get('substrate') or '').strip()[:120],
            'variant': str(v.get('variant') or '').strip()[:80]}


def main():
    papers, R = readings()
    D, _ = disputed(R)
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    key, part1, part2 = {}, [], []
    for p in papers:
        per = {s: [(i, v) for i, v in enumerate(R[s]) if v['pmid'] == p] for s in R}
        n = {s: sum(1 for i, _ in per[s] if i in D[s]) for s in R}
        if not sum(n.values()):
            continue
        kc = any(i in D[s] and v['metric'] == 'kcat' for s in R for i, v in per[s])
        (part1 if kc else part2).append(p)
        order = list(R)
        rng.shuffle(order)
        task = {'pmid': p, 'units': 'kcat s^-1, Km mM, kcat/Km mM^-1 s^-1'}
        for letter, s in zip('ABC', order):
            task[f'reading_{letter}'] = [{'id': f'{letter}{k}', 'judge': i in D[s], **shown(v, s)} for k, (i, v) in enumerate(per[s])]
        key[p] = {'order': dict(zip('ABC', order)),
                  'index': {f'{letter}{k}': [s, i] for letter, s in zip('ABC', order) for k, (i, _) in enumerate(per[s])},
                  'to_judge': n}
        (OUT / f'{p}.task.json').write_text(json.dumps(task, indent=1, ensure_ascii=False))
    second = sorted(random.Random(SEED).sample(part1, min(6, len(part1))), key=W.pmid_key)
    (OUT / '_key.json').write_text(json.dumps(key, indent=1))
    (OUT / '_papers.json').write_text(json.dumps({'part1': part1, 'part2': part2, 'second_agent': second}, indent=1))
    tot = {s: sum(key[p]['to_judge'][s] for p in key) for s in R}
    print(f'part 1: {len(part1)} papers; part 2: {len(part2)} papers; second agent on {second}; values to judge {tot}')


if __name__ == '__main__':
    main()
