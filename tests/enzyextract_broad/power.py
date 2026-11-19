#!/usr/bin/env python3
"""How many papers does the broad test need? A resampling simulation from the locked test's stage-2 page check
(the only data with every disputed CatLog and EnzyExtract value judged against its paper).

Per paper of stage 2 (79 papers, 63 with a dispute), from its verdicts and its scorer's reference
(../../../paper/evidence/locked_test_20261109/stage2/score_checked.py, imported, not changed):
  - for CatLog and EnzyExtract's full-pipeline run (RGF): values held, values matched to the reference, and values
    judged a wrong number (another scale, not this metric, not in the paper);
  - under the plan's two rules: "printed here" (a value credited to earlier work counts as right, a repeated listing
    counts neither way) and "measured here" (stage 2's own rule: only a value this paper measured counts as right).
One simulated test draws N papers with replacement and runs the plan's analysis: the exact sign test on papers with a
wrong number on one side only, and paired paper-bootstrap 95% intervals for CatLog minus EnzyExtract recall and
precision (B 1,000 inside the simulation). Scenarios thin EnzyExtract's wrong numbers (each kept with probability 1/2,
or each paper's kept with probability 1/2), because random catalogue papers may be easier than its benchmark, and one
scenario also gives CatLog a wrong number in a random 3% of papers (stage 2 judged none of its values a wrong number).
Writes power_results.json and prints the table. Seed 20261118. Reads the kit's records and the stage-2 verdicts only;
opens no paper text."""
import importlib.util, json, sys
from math import comb
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
S2 = HERE.parents[2] / 'paper' / 'evidence' / 'locked_test_20261109' / 'stage2'
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('sc', S2 / 'score_checked.py')
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)
ct, C, W = sc.ct, sc.C, sc.W
WRONG_NUMBER = {'measured_here_other_scale', 'not_this_metric', 'not_found_in_paper'}
SEED, SIMS, B = 20261118, 1000, 1000
SIZES = [50, 100, 150, 200, 250, 300, 400]


def per_paper():
    papers, R = ct.readings()
    D, both = ct.disputed(R)
    key = json.loads((sc.CHK / '_key.json').read_text())
    judged = {s: {} for s in R}
    for p in key:
        v = sc.verdicts(p)
        if v is None:
            continue
        for i, (s, ix) in key[p]['index'].items():
            if ix in D[s]:
                judged[s][ix] = v.get(i, 'cannot_decide')
    rules = {'printed_here': ({sc.RIGHT, 'as_printed_but_misprint', 'credited_to_earlier_work'}, {'repeat_of_one_printed_value'}),
             'measured_here': ({sc.RIGHT, 'as_printed_but_misprint'}, set())}
    out = {}
    for rule, (right, neutral) in rules.items():
        ref = []
        for i, g in enumerate(R['curation']):
            if i in both or judged['curation'].get(i) in right:
                ref.append(g)
        for s in ('catlog', 'rgf'):
            cand = [v for i, v in enumerate(R[s]) if judged[s].get(i) in right]
            if cand:
                _, _, su = C.match(ref, cand)
                ref += [cand[j] for j in su]
        rows = []
        for p in papers:
            row = {'pmid': p, 'ref': sum(1 for g in ref if g['pmid'] == p)}
            for s in ('catlog', 'rgf'):
                vals = [v for i, v in enumerate(R[s]) if v['pmid'] == p and judged[s].get(i) not in neutral and judged[s].get(i) != 'cannot_decide']
                pr, _, _ = C.match([g for g in ref if g['pmid'] == p], vals)
                row[s] = {'n': len(vals), 'held': len(pr),
                          'wrong_number': sum(1 for i, v in enumerate(R[s]) if v['pmid'] == p and judged[s].get(i) in WRONG_NUMBER)}
            rows.append(row)
        out[rule] = rows
    return out


def sign_p(a, b):
    n, k = a + b, min(a, b)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def simulate(rows, n, rng, thin=None):
    ref = np.array([r['ref'] for r in rows], float)
    ch, cn, cw = (np.array([r['catlog'][k] for r in rows], float) for k in ('held', 'n', 'wrong_number'))
    eh, en, ew = (np.array([r['rgf'][k] for r in rows], float) for k in ('held', 'n', 'wrong_number'))
    res = {'sign': 0, 'sign_favours_catlog': 0, 'recall': 0, 'precision': 0, 'recall_hw': [], 'precision_hw': [],
           'papers_wrong_catlog': [], 'papers_wrong_ee': []}
    for _ in range(SIMS):
        idx = rng.integers(0, len(rows), n)
        w_e = ew[idx].copy()
        h_e = eh[idx].copy()
        if thin == 'values':   # each wrong EnzyExtract number becomes a right, held value with probability 1/2
            keep = rng.binomial(w_e.astype(int), 0.5)
            h_e = h_e + (w_e - keep)
            w_e = keep.astype(float)
        elif thin in ('papers', 'papers_and_catlog'):  # each paper's wrong EnzyExtract numbers all become right with probability 1/2
            gone = (rng.random(n) < 0.5) & (w_e > 0)
            h_e = h_e + np.where(gone, w_e, 0)
            w_e = np.where(gone, 0, w_e)
        h_c, w_c = ch[idx].copy(), cw[idx].copy()
        if thin == 'papers_and_catlog':  # also: CatLog holds one wrong number in a random 3% of papers
            extra = (rng.random(n) < 0.03) & (cn[idx] > 0)
            w_c = w_c + extra
            h_c = h_c - np.minimum(extra, h_c)
        wc, we = w_c > 0, w_e > 0
        a, b = int((we & ~wc).sum()), int((wc & ~we).sum())
        p = sign_p(a, b)
        res['sign'] += p < 0.05
        res['sign_favours_catlog'] += (p < 0.05) and a > b
        res['papers_wrong_catlog'].append(int(wc.sum()))
        res['papers_wrong_ee'].append(int(we.sum()))
        bi = rng.integers(0, n, (B, n))
        r_ref = ref[idx][bi].sum(1)
        rc = h_c[bi].sum(1) / r_ref
        re_ = h_e[bi].sum(1) / r_ref
        pc = h_c[bi].sum(1) / np.maximum(cn[idx][bi].sum(1), 1)
        pe = h_e[bi].sum(1) / np.maximum(en[idx][bi].sum(1), 1)
        for k, d in (('recall', rc - re_), ('precision', pc - pe)):
            lo, hi = np.percentile(d, [2.5, 97.5])
            res[k] += (lo > 0) or (hi < 0)
            res[f'{k}_hw'].append((hi - lo) / 2)
    return {'sign_decides': res['sign'] / SIMS, 'sign_decides_for_catlog': res['sign_favours_catlog'] / SIMS,
            'recall_decides': res['recall'] / SIMS, 'precision_decides': res['precision'] / SIMS,
            'recall_halfwidth': float(np.mean(res['recall_hw'])), 'precision_halfwidth': float(np.mean(res['precision_hw'])),
            'papers_wrong_catlog_mean': float(np.mean(res['papers_wrong_catlog'])), 'papers_wrong_ee_mean': float(np.mean(res['papers_wrong_ee']))}


def main():
    data = per_paper()
    summary = {r: {'papers': len(rows), 'ref': sum(x['ref'] for x in rows),
                   **{s: {k: sum(x[s][k] for x in rows) for k in ('n', 'held', 'wrong_number')} for s in ('catlog', 'rgf')},
                   'papers_with_a_wrong_number': {s: sum(1 for x in rows if x[s]['wrong_number'] > 0) for s in ('catlog', 'rgf')},
                   'discordant': {'ee_only': sum(1 for x in rows if x['rgf']['wrong_number'] > 0 and x['catlog']['wrong_number'] == 0),
                                  'catlog_only': sum(1 for x in rows if x['catlog']['wrong_number'] > 0 and x['rgf']['wrong_number'] == 0)}}
               for r, rows in data.items()}
    rng = np.random.default_rng(SEED)
    table = {r: {sc_: {n: simulate(rows, n, rng, thin) for n in SIZES} for sc_, thin in (('as_seen', None), ('ee_wrong_halved_values', 'values'), ('ee_wrong_halved_papers', 'papers'), ('ee_halved_papers_catlog_wrong_3pct', 'papers_and_catlog'))}
             for r, rows in data.items()}
    (HERE / 'power_results.json').write_text(json.dumps({'seed': SEED, 'sims': SIMS, 'B': B, 'stage2_summary': summary, 'table': table, 'per_paper': data}, indent=1))
    print(json.dumps(summary, indent=1))
    for r in table:
        for s in table[r]:
            print(f'\n{r} / {s}: N | sign test decides (for CatLog) | recall CI excludes 0 | precision CI excludes 0 | half-widths')
            for n, x in table[r][s].items():
                print(f"  {n:4d} | {x['sign_decides']:.2f} ({x['sign_decides_for_catlog']:.2f}) | {x['recall_decides']:.2f} | {x['precision_decides']:.2f} | "
                      f"±{x['recall_halfwidth']:.3f} ±{x['precision_halfwidth']:.3f} | wrong papers C {x['papers_wrong_catlog_mean']:.1f} E {x['papers_wrong_ee_mean']:.1f}")


if __name__ == '__main__':
    main()
