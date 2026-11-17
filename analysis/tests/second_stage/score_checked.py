#!/usr/bin/env python3
"""Stage 2's page check, scored (CHECK_PLAN.md; committed with it, before any verdict existed): every source against a
corrected reference on the held-out papers.

  python3 -B score_checked.py     -> checked/results.json, checked/RESULTS.md

Reference, per paper and metric: the curation's values that CatLog and the run (RGF) both match (taken as right), plus
every checked value judged measured_here_at_this_scale, from any of the three readings, the same measurement held by two
readings counted once (matched one to one, within 1.5%). A paper with no check file keeps the curation as its reference;
a metric's table is called complete only when every paper with a disputed value of that metric has a check file.
Verdict files: records/stage2_check/<PMID>.check1.json (and .check2.json for the second agent):
{"pmid": ..., "verdicts": [{"id": "A3", "verdict": ..., "right_value": ..., "evidence": ...}]}."""
import collections, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ct', HERE / 'check_tasks.py')
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)
s2, W, C, h2h = ct.s2, ct.W, ct.C, ct.h2h
CHK = ct.OUT
RIGHT = 'measured_here_at_this_scale'
VIEWS = {'as_printed': (RIGHT, 'as_printed_but_misprint'), 'corrected': (RIGHT, 'corrected_misprint')}
VERDICTS = (RIGHT, 'measured_here_other_scale', 'as_printed_but_misprint', 'corrected_misprint', 'repeat_of_one_printed_value', 'not_this_metric', 'credited_to_earlier_work',
            'not_found_in_paper', 'cannot_decide')


def verdicts(p, k=1):
    f = CHK / f'{p}.check{k}.json'
    if not f.exists():
        return None
    try:
        d = json.loads(f.read_text())
    except json.JSONDecodeError:
        return None
    return {str(v.get('id')): v.get('verdict') for v in d.get('verdicts', []) if v.get('verdict') in VERDICTS}


def main():
    papers, R = ct.readings()
    D, both = ct.disputed(R)
    key = json.loads((CHK / '_key.json').read_text())
    parts = json.loads((CHK / '_papers.json').read_text())
    judged = {s: {} for s in R}  # source -> index -> verdict
    checked, missing_ids = [], {}
    for p in key:
        v = verdicts(p)
        if v is None:
            continue
        want = [i for i, (s, ix) in key[p]['index'].items() if ix in D[s]]
        miss = [i for i in want if i not in v]
        if miss:
            missing_ids[p] = len(miss)
        checked.append(p)
        for i in want:
            s, ix = key[p]['index'][i]
            judged[s][ix] = v.get(i, 'cannot_decide')
    cset = set(checked)
    def reference(right):
        ref = []
        for i, g in enumerate(R['curation']):
            if g['pmid'] not in cset or i in both or judged['curation'].get(i) in right:
                ref.append({**g, 'id': f'cur{i}', 'from': 'curation'})
        for s in ('catlog', 'rgf'):
            cand = [{**v, 'id': f'{s}{i}', 'from': s} for i, v in enumerate(R[s]) if judged[s].get(i) in right]
            if cand:
                _, _, su = C.match(ref, cand)
                ref += [cand[j] for j in su]
        for g in ref:
            g.setdefault('quote', '')
            g.setdefault('temp', '')
            g.setdefault('pH', '')
        return ref
    # what each metric's table covers
    disp_papers = {m: sorted({R[s][i]['pmid'] for s in R for i in D[s] if R[s][i]['metric'] == m}, key=W.pmid_key) for m in C.METRICS}
    complete = {m: all(p in cset for p in disp_papers[m]) for m in C.METRICS}
    # sources, as in stage 2
    vals = json.loads((W.eval_paths(W.EVAL)['score'].parent / 'score_locked' / 'private' / 'values.json').read_text())
    ps = set(papers)
    sources = {'catlog': [v for v in vals['catlog'] if v['pmid'] in ps], 'plain': [v for v in vals['plain'] if v['pmid'] in ps]}
    for name, df in s2.runs().items():
        sources[f'run_{name}'], _ = h2h.rows_to_values(df, f'run_{name}', ps)
    db = C.enzyextract_values(ps)
    if db:
        sources['enzyextract_db'] = db
    sources['brenda'] = C.brenda_values(ps)
    orig, _ = s2.table(R['curation'], sources, papers)
    views = {}
    for name, right in VIEWS.items():
        ref = reference(right)
        res, arrs = s2.table(ref, sources, papers)
        views[name] = {'res': res, 'ref': ref,
                       'diffs': {n: {m: {k: s2.paired(arrs['catlog'][m], arrs[n][m], den) for k, den in (('recall', 'gold_n'), ('precision', 'sys_n'))}
                                     for m in s2.METRICS} for n in sources if n != 'catlog'}}
    tally = {s: {m: dict(collections.Counter(v for i, v in judged[s].items() if R[s][i]['metric'] == m)) for m in C.METRICS} for s in R}
    tally_all = {s: dict(collections.Counter(judged[s].values())) for s in R}
    # the second agent
    same = cls = n2 = 0
    for p in parts.get('second_agent', []):
        a, b = verdicts(p, 1), verdicts(p, 2)
        if a is None or b is None:
            continue
        for i in a:
            if i in b:
                n2 += 1
                same += a[i] == b[i]
                cls += (a[i] == RIGHT) == (b[i] == RIGHT)
    out = {'plan': 'CHECK_PLAN.md', 'papers': len(papers), 'papers_checked': len(checked), 'papers_with_a_dispute': len(key),
           'part1': len(parts['part1']), 'part1_checked': sum(p in cset for p in parts['part1']),
           'part2': len(parts['part2']), 'part2_checked': sum(p in cset for p in parts['part2']),
           'values_checked': {s: len(judged[s]) for s in R}, 'verdicts': tally_all, 'verdicts_by_metric': tally,
           'values_without_a_verdict_counted_cannot_decide': missing_ids,
           'reference': {m: {'values': {v: sum(1 for g in views[v]['ref'] if g['metric'] == m) for v in views},
                             'curation_values': sum(1 for g in R['curation'] if g['metric'] == m),
                             'complete': complete[m], 'papers_with_a_dispute': len(disp_papers[m]),
                             'checked': sum(p in cset for p in disp_papers[m])} for m in C.METRICS},
           'reference_from': {v: dict(collections.Counter(g['from'] for g in views[v]['ref'])) for v in views},
           'views': {v: {'sources': views[v]['res'], 'catlog_minus': views[v]['diffs']} for v in views},
           'against_the_curation_list': {n: orig[n] for n in orig},
           'second_agent': {'values': n2, 'same_verdict': same, 'same_right_or_not': cls},
           'bootstrap': {'B': s2.B, 'seed': s2.SEED}}
    (HERE / 'checked').mkdir(exist_ok=True)
    (HERE / 'checked' / 'results.json').write_text(json.dumps(out, indent=1, default=str))
    f3 = lambda x: '-' if x is None else f'{x:.3f}'  # noqa: E731
    share = lambda b: '-' if b['est'] is None else f"{b['est']:.3f} ({b['lo']:.3f}-{b['hi']:.3f})"  # noqa: E731
    dif = lambda b: '-' if b['est'] is None else f"{b['est']:+.3f} ({b['lo']:+.3f} to {b['hi']:+.3f})"  # noqa: E731
    names = {'catlog': 'CatLog', 'plain': 'Plain read (Opus 5.5)', 'run_RGF': 'EnzyExtract full pipeline (RGF)',
             'enzyextract_db': 'EnzyExtract database', 'brenda': 'BRENDA 2026.1'}
    order = ['catlog', 'plain', 'run_RGF'] + sorted(n for n in sources if n.startswith('run_') and n != 'run_RGF') + \
        [n for n in ('enzyextract_db', 'brenda') if n in orig]
    L = ['# Stage 2, page check of the disputed values: every source against the corrected reference (post hoc)', '',
         f"Rules: CHECK_PLAN.md. Papers checked: {len(checked)} of the {len(key)} with a value the curation, CatLog and the run do "
         f"not all three agree on (part 1: {out['part1_checked']} of {out['part1']}; part 2: {out['part2_checked']} of {out['part2']}). "
         f"Values checked: {out['values_checked']}.", '',
         '## What the checked values are', '', '| Verdict | Curation | CatLog | EnzyExtract run |', '|---|---|---|---|']
    for v in VERDICTS:
        L.append(f"| {v.replace('_', ' ')} | " + ' | '.join(str(tally_all[s].get(v, 0)) for s in ('curation', 'catlog', 'rgf')) + ' |')
    L += ['', 'kcat only: ' + '; '.join(f"{s}: {tally[s]['kcat']}" for s in ('curation', 'catlog', 'rgf')) + '.',
          f"Second agent on {len(parts.get('second_agent', []))} papers: {n2} values, the same verdict on {same}, the same right-or-not on {cls}.", '']
    for m in [*C.METRICS, 'all']:
        full = all(complete.values()) if m == 'all' else complete[m]
        for vname, label in (('as_printed', 'a misprinted scale counts as printed'), ('corrected', 'a misprinted scale counts as corrected')):
            res, diffs = views[vname]['res'], views[vname]['diffs']
            L += [f"## {m}, {label}: " + ('complete' if full else 'PARTIAL: not every paper with a dispute is checked, so unchecked papers keep the curation list'),
                  '', '| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision | Against the curation list |',
                  '|---|---|---|---|---|---|']
            for n in order:
                a, d, o = res[n][m], diffs.get(n, {}).get(m), orig[n][m]
                L.append(f"| {names.get(n, 'EnzyExtract run ' + n[4:])} | {share(a['recall'])} | {share(a['precision'])} | "
                         f"{dif(d['recall']) if d else ''} | {dif(d['precision']) if d else ''} | {f3(o['recall']['est'])}, {f3(o['precision']['est'])} |")
            L.append('')
    L += [f"Reference values by where they come from: {out['reference_from']}; per metric: "
          + '; '.join(f"{m} {out['reference'][m]['values']} (the curation has {out['reference'][m]['curation_values']})" for m in C.METRICS) + '.',
          "Read with care: post hoc; one agent per value (a second on a sample), no planted errors; the checkers are Claude models, as "
          "are CatLog's readers, and each value's page and words are on file for a person to check; only the curation, CatLog and RGF "
          "were checked, so the precision of the plain read and the other runs is a lower bound; a value all three readings agree on "
          "was not checked."]
    (HERE / 'checked' / 'RESULTS.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L[:14]))


if __name__ == '__main__':
    main()
