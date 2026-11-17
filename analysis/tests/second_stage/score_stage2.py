#!/usr/bin/env python3
"""Locked test, stage 2 (../STAGE2.md, committed 41d125f before any run was scored on these papers): every source
against EnzyExtract's manual curation on the held-out papers, with the 22 October head-to-head's code (the kit's checked
copies: h2h_common.py, h2h_s06.py) and the four rules the plan fixes.

  python3 -B score_stage2.py check    the code reproduces that head-to-head's numbers for every run, the database and
                                      BRENDA on its 59 development papers (results_enzyextract_manual.json); else exit 1
  python3 -B score_stage2.py run      (after check) the held-out table -> results.json, RESULTS.md

Sources: CatLog and the plain read from stage 1's values.json (the values the judging used); EnzyExtract's runs
(work/top_journal_20261021/h2h/data/rumble_*_dev1.tsv, extracted on 22 October from their benchmark SI); their database
(thedata_subset.tsv, if it covers these papers); BRENDA (sources/db_values.tsv).
Rule 1: a source's exact repeats (same paper, metric, value, and enzyme, substrate and variant labels) are dropped before
matching, for every source alike; also given with repeats kept. Rule 2: cells the units code cannot read are counted per
source and metric, never scored. Rule 3: a paper for which a run has no row counts with no values; also given on the
papers where the run has rows. Rule 4: paper-clustered bootstrap, B 10,000, seed 20261031; differences paired on the
same resampled papers."""
import glob, hashlib, json, os, re, sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
KIT = Path('<the kit folder>')
MAIN = Path('<the CatLog folder>')
H2H_WORK = MAIN / 'work' / 'top_journal_20261021' / 'h2h'
sys.dont_write_bytecode = True
sys.path.insert(0, str(KIT / 'code' / 'tools' / 'w1'))
import common_w1 as W  # noqa: E402
import h2h  # noqa: E402

C = h2h.C
C.H2H = str(H2H_WORK)  # the head-to-head's extracts of EnzyExtract's files (its loaders read H2H/data/)
B, SEED = 10000, W.SEED_BOOT
MISPRINT = ('9973343', '10447675')
METRICS = [*C.METRICS, 'all']


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def curation():
    f = W.eval_paths(W.EVAL)['keys'] / h2h.GOLD_NAMES['ee_manual']
    if sha(f) != h2h.GOLD_SHA256['ee_manual']:
        sys.exit(f'{f}: not the checked copy of the curation')
    h2h.use_keys(f.parent)
    return C.load_ee_manual_raw()


def runs():
    out = {}
    for f in sorted(glob.glob(str(H2H_WORK / 'data' / 'rumble_*_dev1.tsv'))):
        out[os.path.basename(f).replace('rumble_', '').replace('_dev1.tsv', '')] = pd.read_csv(f, sep='\t', dtype=str)
    return out


def unread(df, papers):
    """Rule 2: a run's cells for these papers that the units code cannot read, per metric (rows_to_values drops them)."""
    n = {m: 0 for m in C.METRICS}
    for _, r in df.iterrows():
        if str(r['pmid']).strip() not in papers:
            continue
        for m, col in (('kcat', 'kcat'), ('Km', 'km'), ('kcat/Km', 'kcat_km')):
            raw = r[col] if col in r and isinstance(r[col], str) else ''
            if raw.strip() and raw.strip().lower() not in ('none', 'nan', 'null') and C.parse_value_unit(m, raw) is None:
                n[m] += 1
    return n


def lab(x):
    return re.sub(r'\s+', ' ', str(x if x is not None else '')).strip().lower()


def no_repeats(vals):
    """Rule 1: the first of each group of exact repeats."""
    seen, out = set(), []
    for v in vals:
        k = (v['pmid'], v['metric'], float(f"{v['value']:.6g}"), lab(v.get('enzyme')), lab(v.get('substrate')), lab(v.get('variant')))
        if k not in seen:
            seen.add(k)
            out.append(v)
    return out


def score(gold, sv, papers):
    """Per metric and all: recall and precision with the paper-clustered interval, the counts, and the per-paper arrays
    (for the paired differences)."""
    pairs, gu, su = C.match(gold, sv)
    sc = C.scores(gold, sv, pairs, papers)
    out = {}
    for m, d in sc.items():
        out[m] = {'recall': C.boot(d, 'matched', 'gold_n', B, SEED), 'precision': C.boot(d, 'matched', 'sys_n', B, SEED),
                  'gold_n': int(d.gold_n.sum()), 'sys_n': int(d.sys_n.sum()), 'matched': int(d.matched.sum())}
    arr = {m: {c: sc[m][c].to_numpy(float) for c in ('matched', 'gold_n', 'sys_n')} for m in sc}
    return out, arr, (pairs, gu, su)


def paired(a, b, den):
    """a minus b of matched / den (ratio of sums over papers), both on the same resampled papers; papers where either has
    a denominator; a resample where one sums to zero is left out and counted."""
    keep = (a[den] > 0) | (b[den] > 0)
    na, ka, nb, kb = a['matched'][keep], a[den][keep], b['matched'][keep], b[den][keep]
    m = int(keep.sum())
    out = {'est': None, 'lo': None, 'hi': None, 'papers': m, 'resamples_without_a_share': 0}
    if not (ka.sum() > 0 and kb.sum() > 0):
        return out
    out['est'] = float(na.sum() / ka.sum() - nb.sum() / kb.sum())
    idx = np.random.default_rng(SEED).integers(0, m, size=(B, m))
    KA, KB = ka[idx].sum(1), kb[idx].sum(1)
    ok = (KA > 0) & (KB > 0)
    d = na[idx].sum(1)[ok] / KA[ok] - nb[idx].sum(1)[ok] / KB[ok]
    out['resamples_without_a_share'] = int(B - ok.sum())
    if d.size:
        out['lo'], out['hi'] = float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
    return out


def check():
    """The loaders and the matcher give the 22 October numbers on its 59 development papers (rows as loaded, no rule 1)."""
    ref = json.loads((MAIN / 'paper' / 'evidence' / 'h2h_20261101' / 'results_enzyextract_manual.json').read_text())['on_catlog_done']
    man = curation()
    pp = pd.read_csv(H2H_WORK / 'data' / 'papers_ee384.tsv', sep='\t', dtype=str)
    done = set(pp[pp.catlog_status == 'done'].pmid)
    gold, _ = h2h.rows_to_values(man, 'ee_manual', done)
    systems = {'enzyextract_db': C.enzyextract_values(done), 'brenda': C.brenda_values(done)}
    for name, df in runs().items():
        systems[f'run_{name}'], _ = h2h.rows_to_values(df, f'run_{name}', done)
    bad = []
    for name, sv in systems.items():
        pairs, _, _ = C.match(gold, sv)
        s = C.summarize(gold, sv, pairs, sorted(done), B=50)
        for m in METRICS:
            got = (s[m]['gold_n'], s[m]['sys_n'], s[m]['matched'])
            want = (ref[name][m]['gold_n'], ref[name][m]['sys_n'], ref[name][m]['matched'])
            if got != want:
                bad.append((name, m, got, want))
        print(f"{name:18s} recall {s['all']['recall']['est']:.3f} precision {s['all']['precision']['est']:.3f} "
              f"(22 Oct: {ref[name]['all']['recall']['est']:.3f} {ref[name]['all']['precision']['est']:.3f})")
    if bad:
        sys.exit(f'{len(bad)} counts differ from the 22 October head-to-head: {bad[:6]}')
    print(f'check passed: {len(systems)} sources, every count (curation values, source values, matched) as on 22 October, '
          f'on {len(done)} development papers')


def table(gold, sources, papers, keep_repeats=False):
    res, arrs = {}, {}
    for name, sv in sources.items():
        sv = [v for v in sv if v['pmid'] in set(papers)]
        if not keep_repeats:
            sv = no_repeats(sv)
        res[name], arrs[name], _ = score(gold, sv, papers)
        res[name]['papers_with_values'] = len({v['pmid'] for v in sv})
    return res, arrs


def run():
    check()  # the plan's "check before use": stops if the code no longer reproduces the 22 October numbers
    stage1 = json.loads((W.eval_paths(W.EVAL)['score'].parent / 'score_locked' / 'results.json').read_text())['curation']
    tri = json.loads((W.eval_paths(W.EVAL)['score'].parent / 'score_locked' / 'private' / 'triage.json').read_text())
    vals = json.loads((W.eval_paths(W.EVAL)['score'].parent / 'score_locked' / 'private' / 'values.json').read_text())
    sets = {r['pmid']: r['gold_set'] for r in W.read_tsv(W.KIT / 'holdout_374.tsv')}
    papers = sorted((p for p in vals['papers'] if sets.get(p) in ('enzyextract', 'both')), key=W.pmid_key)
    ps = set(papers)
    man = curation()
    gold, _ = h2h.rows_to_values(man, 'ee_manual', ps)
    scored = [g for g in gold if g['value'] is not None]
    rr = runs()
    sources = {'catlog': [v for v in vals['catlog'] if v['pmid'] in ps], 'plain': [v for v in vals['plain'] if v['pmid'] in ps]}
    unreadable, with_rows = {}, {}
    for name, df in rr.items():
        sources[f'run_{name}'], _ = h2h.rows_to_values(df, f'run_{name}', ps)
        unreadable[f'run_{name}'] = unread(df, ps)
        with_rows[f'run_{name}'] = sorted({str(x).strip() for x in df['pmid']} & ps, key=W.pmid_key)
    db = C.enzyextract_values(ps)
    if db:
        sources['enzyextract_db'] = db
    ext = pd.read_csv(H2H_WORK / 'data' / 'thedata_subset.tsv', sep='\t', dtype=str).rename(columns={'catlog_pmid': 'pmid'})
    unreadable['enzyextract_db (kcat/Km strings only)'] = unread(ext[['pmid', 'kcat_km']], ps)
    unscored = {m: sum(1 for g in gold if g['value'] is None and g['metric'] == m) for m in C.METRICS}
    pe = pd.read_csv(H2H_WORK / 'data' / 'papers_ee384.tsv', sep='\t', dtype=str)
    no_doi = sorted(pe[pe.pmid.isin(ps) & ~(pe.doi.fillna('').str.strip() != '')].pmid) if 'doi' in pe.columns else None
    sources['brenda'] = C.brenda_values(ps)
    res, arrs = table(gold, sources, papers)
    kept, akept = table(gold, sources, papers, keep_repeats=True)
    for src in ('catlog', 'plain'):  # with repeats kept these are stage 1's pre-registered secondary: the same numbers
        a, b = kept[src]['all'], stage1['per_source'][src]['all']
        if (a['gold_n'], a['sys_n'], a['matched']) != (b['gold_n'], b['sys_n'], b['matched']):
            sys.exit(f"{src}: with repeats kept {(a['gold_n'], a['sys_n'], a['matched'])} is not stage 1's "
                     f"{(b['gold_n'], b['sys_n'], b['matched'])}: values.json, the curation or the units code changed")
    dkept = {name: {k: paired(akept['catlog']['all'], akept[name]['all'], den) for k, den in (('recall', 'gold_n'), ('precision', 'sys_n'))}
             for name in sources if name != 'catlog'}
    diffs = {name: {m: {k: paired(arrs['catlog'][m], arrs[name][m], den) for k, den in (('recall', 'gold_n'), ('precision', 'sys_n'))}
                    for m in METRICS} for name in sources if name != 'catlog'}
    # rule 3's second view: each run on the papers where it has rows, CatLog on the same papers
    on_rows = {}
    for name, pl in with_rows.items():
        g2 = [g for g in gold if g['pmid'] in set(pl)]
        r2, a2 = table(g2, {name: sources[name], 'catlog': sources['catlog']}, pl)
        on_rows[name] = {'papers': len(pl), 'source': r2[name]['all'], 'catlog': r2['catlog']['all'],
                         'catlog_minus': {k: paired(a2['catlog']['all'], a2[name]['all'], den)
                                          for k, den in (('recall', 'gold_n'), ('precision', 'sys_n'))}}
    # the sensitivity without the two misprint papers
    p2 = [p for p in papers if p not in MISPRINT]
    g3 = [g for g in gold if g['pmid'] in set(p2)]
    r3, a3 = table(g3, sources, p2)
    d3 = {name: {k: paired(a3['catlog']['all'], a3[name]['all'], den) for k, den in (('recall', 'gold_n'), ('precision', 'sys_n'))}
          for name in sources if name != 'catlog'}
    run_names = [n for n in sources if n.startswith('run_')]
    best = {k: max(run_names, key=lambda n: res[n]['all'][k]['est'] or 0) for k in ('recall', 'precision')}
    out = {'plan_commit': '41d125f', 'papers': len(papers), 'papers_list': papers,
           'curation_values': {'scored': len(scored), 'unscored': len(gold) - len(scored)},
           'curation_unscored_by_metric': unscored, 'curation_exact_repeats': len(scored) - len(no_repeats(scored)),
           'check_passed': True, 'stage1_plain_repeats_already_dropped': (tri.get('repeats_dropped') or {}).get('plain'),
           'stage1_catlog_repeats_already_dropped': (tri.get('repeats_dropped') or {}).get('catlog'),
           'database_papers_without_a_doi_key': no_doi,
           'bootstrap': {'B': B, 'seed': SEED}, 'sources': res, 'with_repeats_kept': {n: kept[n]['all'] for n in kept},
           'with_repeats_kept_catlog_minus': dkept,
           'repeats_dropped': {n: kept[n]['all']['sys_n'] - res[n]['all']['sys_n'] for n in res},
           'unreadable_cells': unreadable, 'papers_without_a_row': {n: len(papers) - len(pl) for n, pl in with_rows.items()},
           'catlog_minus': diffs, 'on_papers_where_the_run_has_rows': on_rows, 'best_run': best,
           'without_misprint_papers': {'papers': len(p2), 'sources': {n: r3[n]['all'] for n in r3}, 'catlog_minus': d3},
           'enzyextract_db_scored': bool(db),
           'inputs_sha256': {'curation': h2h.GOLD_SHA256['ee_manual'],
                             **{os.path.basename(f): sha(f) for f in sorted(glob.glob(str(H2H_WORK / 'data' / 'rumble_*_dev1.tsv')))},
                             'db_values.tsv': sha(MAIN / 'sources' / 'db_values.tsv'),
                             'units.py': sha(KIT / 'code' / 'tools' / 'units.py'),
                             'values.json': sha(W.eval_paths(W.EVAL)['score'].parent / 'score_locked' / 'private' / 'values.json'),
                             'thedata_subset.tsv': sha(H2H_WORK / 'data' / 'thedata_subset.tsv'),
                             'holdout_374.tsv': sha(W.KIT / 'holdout_374.tsv'), 'score_stage2.py': sha(__file__)}}
    (HERE / 'results.json').write_text(json.dumps(out, indent=1, default=str))
    share = lambda b: '-' if b['est'] is None else f"{b['est']:.3f} ({b['lo']:.3f}-{b['hi']:.3f})"  # noqa: E731
    dif = lambda b: '-' if b['est'] is None else f"{b['est']:+.3f} ({b['lo']:+.3f} to {b['hi']:+.3f})"  # noqa: E731
    f3 = lambda x: '-' if x is None else f'{x:.3f}'  # noqa: E731
    names = {'catlog': 'CatLog (first pass)', 'plain': 'Plain read (Opus 5.5)', 'enzyextract_db': 'EnzyExtract database',
             'brenda': 'BRENDA 2026.1'}
    L = [f"# Locked test, stage 2: every source against EnzyExtract's manual curation on {len(papers)} held-out papers", '',
         f"Plan: ../STAGE2.md (commit 41d125f, before any run was scored on these papers). The curation's values on these "
         f"papers: {len(scored)} scored, {len(gold) - len(scored)} not scored. Matching: per paper and metric, one to one, "
         f"within 1.5%. Intervals: paper-clustered bootstrap, B {B}, seed {SEED}; differences paired. Exact repeats dropped.", '',
         '| Source | Papers with values | Values | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision |',
         '|---|---|---|---|---|---|---|']
    order = ['catlog', 'plain', 'run_RGF'] + sorted(n for n in run_names if n != 'run_RGF') + [n for n in ('enzyextract_db', 'brenda') if n in res]
    for n in order:
        a = res[n]['all']
        d = diffs.get(n, {}).get('all')
        L.append(f"| {names.get(n, 'EnzyExtract run ' + n[4:])} | {res[n]['papers_with_values']} | {a['sys_n']} | {share(a['recall'])} | "
                 f"{share(a['precision'])} | {dif(d['recall']) if d else ''} | {dif(d['precision']) if d else ''} |")
    L += ['', f"Best EnzyExtract run by recall: {best['recall'][4:]}; by precision: {best['precision'][4:]}.", '',
          '## By metric (recall, precision)', '', '| Source | kcat | Km | kcat/Km |', '|---|---|---|---|']
    for n in order:
        L.append(f"| {names.get(n, 'EnzyExtract run ' + n[4:])} | " + ' | '.join(
            f"{f3(res[n][m]['recall']['est'])}, {f3(res[n][m]['precision']['est'])}" for m in C.METRICS) + ' |')
    # 2: endpoint 3, CatLog minus RGF per metric, with intervals
    L += ['', 'CatLog minus RGF by metric: ' + '; '.join(
        f"{m}: recall {dif(diffs['run_RGF'][m]['recall'])}, precision {dif(diffs['run_RGF'][m]['precision'])}" for m in C.METRICS) + '.']
    L += ['', '## Rules 1 to 3', '',
          f"Repeats dropped (values): {out['repeats_dropped']}. Stage 1 had already dropped {out['stage1_plain_repeats_already_dropped']} "
          f"repeats of the plain read and {out['stage1_catlog_repeats_already_dropped']} of CatLog. The curation keeps its own "
          f"{out['curation_exact_repeats']} exact repeats, each of which a source can match only once.",
          "With repeats kept (recall/precision; CatLog minus it: recall, precision): " + '; '.join(
              f"{n} {f3(kept[n]['all']['recall']['est'])}/{f3(kept[n]['all']['precision']['est'])}"
              + (f" ({dif(dkept[n]['recall'])}, {dif(dkept[n]['precision'])})" if n in dkept else '') for n in order) + '. '
          "For CatLog and the plain read these are stage 1's secondary numbers, checked equal.",
          f"Not scored, per source and metric (a bound, a number with no unit, or a cell the units code cannot read): {unreadable}; "
          f"the curation's unscored cells: {unscored}. CatLog, the plain read and BRENDA arrive as numbers.",
          ("EnzyExtract database: scored" + (f"; the extract of 22 October found its rows through each paper's DOI and "
           f"could not look for {no_doi} (no DOI key then)" if no_doi else '') + '.') if db else
          "EnzyExtract database: not scored, the extract on disk holds no value for these papers.",
          f"Papers for which a run has no row (their curation values count as missed): {out['papers_without_a_row']}.",
          'On the papers where a run has rows (the run; CatLog on the same papers; CatLog minus the run): ' + '; '.join(
              f"{n[4:]} on {v['papers']} papers: {f3(v['source']['recall']['est'])}/{f3(v['source']['precision']['est'])}; "
              f"CatLog {f3(v['catlog']['recall']['est'])}/{f3(v['catlog']['precision']['est'])}; recall {dif(v['catlog_minus']['recall'])}, "
              f"precision {dif(v['catlog_minus']['precision'])}" for n, v in on_rows.items() if n == 'run_RGF' or v['papers'] < len(papers)) + '.',
          '', f"## Without 9973343 and 10447675 ({len(p2)} papers)", '',
          '| Source | Recall (95%) | Precision (95%) | CatLog minus it: recall | CatLog minus it: precision |', '|---|---|---|---|---|']
    for n in order:
        a = r3[n]['all']
        d = d3.get(n)
        L.append(f"| {names.get(n, 'EnzyExtract run ' + n[4:])} | {share(a['recall'])} | {share(a['precision'])} | "
                 f"{dif(d['recall']) if d else ''} | {dif(d['precision']) if d else ''} |")
    L += ['', "Read with care: the curation is EnzyExtract's own reference, as printed, not ground truth; nothing is judged "
          "here; CatLog's side is its first pass; EnzyExtract's runs are its authors' 2025 models, CatLog and the plain read "
          "use Opus 5.5; 32 benchmark papers left stage 1's set for a refusal or a broken rule on the Opus side; on 22 October "
          "every run was scored on all 384 benchmark papers pooled, these among them, but no number for these papers alone "
          "was computed before this plan."]
    (HERE / 'RESULTS.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('check', 'run'):
        sys.exit(__doc__)
    check() if sys.argv[1] == 'check' else run()
