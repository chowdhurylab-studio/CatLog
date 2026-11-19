#!/usr/bin/env python3
"""Stage 2 scored again with its units reading fixed (post hoc: CORRECTIONS.md, F1; an independent audit,
writing/research/comparison_audit_20261118/enzyextract.md). The registered scorers (score_stage2.py, score_checked.py)
and their outputs are unchanged.

The registered reading (the kit's h2h_common.parse_value_unit) misreads or leaves unread some curation and EnzyExtract
cells. Two readers replace it here:

  misreads   a cell the registered reading read as another number is read as written: an exponent inside the ± part
             ('3 x 10^-4 ± 5 x 10^-5'), 'E' after a space ('3.8 E7'), a space between thousands ('59 500'), and
             per microsecond ('µs^-1'). A cell it left unread stays unread.
  written    misreads, and the cells it left unread are read as written when they can be: brackets around 'a ± b',
             a multiplier written after the unit with '*', a footnote mark after the number, and 'mm^-1' for mM^-1.

Outputs (corrected/):
  table.json        the registered table against the curation, under the registered reading, misreads and written,
                    with CatLog minus every source, by constant, on RGF's 78 papers, without the two misprint papers,
                    and (F6) without and with only the 15 papers in EnzyExtract's fine-tuning set
  checked/          the page check (score_checked.py, unchanged) with both fixes: the misreads reader (values the judges
                    saw keep their places; a value judged at another scale whose right value equals its new reading
                    counts as measured here), and the reference merge fixed (a reading's value judged right may merge
                    only into a reference value that the same reading does not already hold; see MERGE below). The four
                    rules of paper/evidence/stage2_scoring_rules_20261117.
  checked_registered_reproduced/, checked_merge_fixed_only/, checked_misreads_fixed_only/
                    the same page check with neither fix (asserted equal to checked/results.json next to this file),
                    with the merge fixed only, and with the misreads fixed only
  checked_whatif_repeats_keep_the_registered_merge/
                    what-if (post hoc): both fixes, except that values judged a repeat of one printed value keep the
                    registered merge
  RESULTS.md        the numbers side by side

  python3 -I -B score_corrected.py
"""
import importlib.util, json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = HERE / 'corrected'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


M = load('s2c_score_stage2', HERE / 'score_stage2.py')
W, h2h, C = M.W, M.h2h, M.C
BASE = C.parse_value_unit  # the registered reading
H06 = sys.modules['h2h_s06']
PM_EXP = re.compile(r'^\s*([-+]?[\d.]+\s*(?:×|x|\*)\s*10\s*\^?\s*[-−]?\s*\d+)\s*(?:±|\+/-|\+-)\s*[\d.]+\s*(?:×|x|\*)\s*10\s*\^?\s*[-−]?\s*\d+\s*(.*)$')
E_SPACE = re.compile(r'^\s*([-+]?[\d.]+)\s+[Ee]\s*([-+−]?\d+)(?=\s)')
THOUSANDS = re.compile(r'^\s*(\d{1,3}(?: \d{3})+)(?=\s*[^\d\s])')
PER_MICROSECOND = re.compile(r'[µμ]s(\s*\^\s*[-−]\s*1)')
FT = set((HERE.parents[3] / 'writing/research/enzyextract_broad_20261118/ee_finetune_train_pmids.txt').read_text().split())


def misread_fix(s):
    """(string, multiplier) for a string the registered reading reads as another number, else None."""
    t, mult = str(s).strip(), 1.0
    m = PM_EXP.match(t)
    if m:
        t = f'{m.group(1)} {m.group(2)}'
    t2 = E_SPACE.sub(lambda x: f'{x.group(1)}e{x.group(2).replace("−", "-")}', t)
    t3 = THOUSANDS.sub(lambda x: x.group(1).replace(' ', ''), t2)
    if PER_MICROSECOND.search(t3):
        t3, mult = PER_MICROSECOND.sub(r's\1', t3), 1e6
    return None if (t3 == str(s).strip() and mult == 1.0) else (t3, mult)


def unread_fix(s):
    t = str(s).strip()
    t = re.sub(r'^\(\s*([-+]?[\d.]+\s*(?:±|\+/-|\+-)\s*[\d.]+)\s*\)', r'\1', t)
    t = re.sub(r'^([-+]?\d[\d.]*)\s*[*†‡§]+(?=\s)', r'\1', t)
    t = re.sub(r'(?<![A-Za-zµμ])mm(?=\s*\^)', 'mM', t)
    t = re.sub(r'\s\*\s*10\s*\^', ' × 10^', t)
    return t


def reader(mode):
    def read(metric, s):
        v = BASE(metric, s)
        if mode == 'registered' or s is None or not isinstance(s, str):
            return v
        if v is not None:  # read: fix it only if it is a misread form
            f = misread_fix(s)
            if f:
                x = BASE(metric, f[0])
                return None if x is None else x * f[1]
            return v
        if mode == 'written':  # unread: try the forms written otherwise
            t = unread_fix(s)
            f = misread_fix(t)
            t, mult = (f if f else (t, 1.0))
            x = BASE(metric, t)
            return None if x is None else x * mult
        return None
    return read


def use(mode):
    C.parse_value_unit = H06.parse_value_unit = reader(mode)


# The page check's reference (score_checked.main, reference()) starts from the curation's values (those CatLog and RGF
# both match, those judged right, and every value of a paper with no check file) and adds each reading's values judged
# right after matching them one to one against the reference so far, so that one measurement held by two readings is
# counted once. A reading's value judged right is one the curation does not match (check_tasks.disputed). Merged into a
# curation value that the same reading already matches through another of its values, it never enters the reference,
# and that reading's own listing then counts against it, because the score matches one to one. Fixed after the result
# (the recounts' finding): a reading's value judged right may merge only into a reference value that the same reading
# does not already hold, i.e. not into a curation value that reading matches in check_tasks.disputed()'s pairing.
# Only the calls made inside score_checked's reference() change. Counted per rule and reading (MERGE['absorbed']): with the
# merge as registered, the values judged right that it sends into a value their own reading holds; with the merge fixed,
# the values judged right that enter the reference because of the fix (main() checks that they are its growth).
MERGE = {'on': False, 'held': None, 'views': None, 'absorbed': None}
MERGED = 'right_values_the_registered_merge_sent_into_a_value_their_own_reading_holds'
ENTERED = 'right_values_entering_the_reference_through_the_merge_fix'
_MATCH = C.match


def match(gold, sysv, *a, **k):
    f = sys._getframe(1)
    if MERGE['held'] is None or f.f_code.co_name != 'reference' or Path(f.f_code.co_filename).name != 'score_checked.py':
        return _MATCH(gold, sysv, *a, **k)
    src = sysv[0]['from']
    assert src in MERGE['held'] and all(v['from'] == src for v in sysv) and all('from' in g for g in gold)
    held = {j for j, g in enumerate(gold) if g['from'] == 'curation' and int(g['id'][3:]) in MERGE['held'][src]}
    view = next(n for n, r in MERGE['views'].items() if tuple(r) == tuple(f.f_locals['right']))
    reg = _MATCH(gold, sysv, *a, **k)
    if not MERGE['on']:
        MERGE['absorbed'].setdefault(view, {})[src] = sum(1 for x, _, _ in reg[0] if x in held)
        return reg
    free = [j for j in range(len(gold)) if j not in held]
    pairs, _, su = _MATCH([gold[j] for j in free], sysv, *a, **k)
    if MERGE['on'] == 'except_repeats':  # what-if (post hoc): a value judged a repeat keeps the registered merge
        judged, idx = f.f_locals['judged'], [int(v['id'][len(src):]) for v in sysv]
        kept = {j for j in set(su) - set(reg[2]) if judged[src].get(idx[j]) == 'repeat_of_one_printed_value'}
        su = [j for j in su if j not in kept]
    MERGE['absorbed'].setdefault(view, {})[src] = len(su) - len(reg[2])
    pairs = [(free[x], y, z) for x, y, z in pairs]
    return pairs, sorted(set(range(len(gold))) - {x for x, _, _ in pairs}), su


C.match = match


# ------------------------------------------------------------------------------------- the table against the curation
def sources_for(ps):
    vals = json.loads((W.eval_paths(W.EVAL)['score'].parent / 'score_locked' / 'private' / 'values.json').read_text())
    src = {'catlog': [v for v in vals['catlog'] if v['pmid'] in ps], 'plain': [v for v in vals['plain'] if v['pmid'] in ps]}
    rr = M.runs()
    with_rows = {}
    for name, df in rr.items():
        src[f'run_{name}'], _ = h2h.rows_to_values(df, f'run_{name}', ps)
        with_rows[f'run_{name}'] = sorted({str(x).strip() for x in df['pmid']} & ps, key=W.pmid_key)
    db = C.enzyextract_values(ps)
    if db:
        src['enzyextract_db'] = db
    src['brenda'] = C.brenda_values(ps)
    return src, with_rows


def diffs_of(arrs, names):
    return {n: {m: {k: M.paired(arrs['catlog'][m], arrs[n][m], den) for k, den in (('recall', 'gold_n'), ('precision', 'sys_n'))}
                for m in M.METRICS} for n in names if n != 'catlog'}


def table_for(mode, papers):
    use(mode)
    ps = set(papers)
    gold, _ = h2h.rows_to_values(M.curation(), 'ee_manual', ps)
    scored = [g for g in gold if g['value'] is not None]
    src, with_rows = sources_for(ps)
    res, arrs = M.table(gold, src, papers)
    out = {'reader': mode, 'curation_values': {'scored': len(scored), 'unscored': len(gold) - len(scored)},
           'sources': {n: res[n] for n in res}, 'catlog_minus': diffs_of(arrs, src)}
    pl = with_rows['run_RGF']
    g2 = [g for g in gold if g['pmid'] in set(pl)]
    r2, a2 = M.table(g2, {'run_RGF': src['run_RGF'], 'catlog': src['catlog']}, pl)
    out['on_rgf_papers'] = {'papers': len(pl), 'catlog_minus_rgf': {k: M.paired(a2['catlog']['all'], a2['run_RGF']['all'], den)
                                                                    for k, den in (('recall', 'gold_n'), ('precision', 'sys_n'))}}
    for label, sub in (('without_misprint_papers', [p for p in papers if p not in M.MISPRINT]),
                       ('without_finetuning_papers', [p for p in papers if p not in FT]),
                       ('finetuning_papers_only', [p for p in papers if p in FT])):
        g3 = [g for g in gold if g['pmid'] in set(sub)]
        names = [n for n in ('catlog', 'plain', 'run_RGF', 'enzyextract_db', 'brenda') if n in src]
        r3, a3 = M.table(g3, {n: src[n] for n in names}, sub)
        out[label] = {'papers': len(sub), 'sources': {n: r3[n]['all'] for n in r3},
                      'catlog_minus': {n: {k: M.paired(a3['catlog']['all'], a3[n]['all'], den) for k, den in (('recall', 'gold_n'), ('precision', 'sys_n'))}
                                       for n in names if n != 'catlog'}}
    run_names = [n for n in src if n.startswith('run_')]
    out['best_run'] = {k: max(run_names, key=lambda n: res[n]['all'][k]['est'] or 0) for k in ('recall', 'precision')}
    return out


def changed_cells(papers):
    """Every curation and run cell whose reading differs between the registered reader and 'written'."""
    ps = set(papers)
    out = []
    import pandas as pd
    db = pd.read_csv(M.H2H_WORK / 'data' / 'thedata_subset.tsv', sep='\t', dtype=str).rename(columns={'catlog_pmid': 'pmid'})
    frames = [('curation', M.curation())] + [(f'run_{n}', df) for n, df in M.runs().items()] + [('enzyextract_db', db)]
    w = reader('written')
    for name, df in frames:
        cols = (('kcat/Km', 'kcat_km'),) if name == 'enzyextract_db' else (('kcat', 'kcat'), ('Km', 'km'), ('kcat/Km', 'kcat_km'))
        for _, r in df.iterrows():
            p = str(r['pmid']).strip()
            if p not in ps:
                continue
            for m, col in cols:
                raw = r[col] if col in r and isinstance(r[col], str) else ''
                if not raw.strip() or raw.strip().lower() in ('none', 'nan', 'null'):
                    continue
                a, b = BASE(m, raw), w(m, raw)
                if a != b and not (a is not None and b is not None and abs(a - b) <= 1e-9 * max(abs(a), abs(b))):
                    out.append({'source': name, 'pmid': p, 'metric': m, 'cell': raw, 'registered': a, 'as_written': b,
                                'kind': 'read as another number' if a is not None else 'left unread'})
    return out


# ------------------------------------------------------------------------------------------------- the page check
def page_check(mode='misreads', merge=False, out_name='checked'):
    sc = sys.modules.get('s2c_score_checked') or load('s2c_score_checked', HERE / 'score_checked.py')
    ct = sc.ct
    use('registered')
    R_reg = ct.readings()[1]
    use(mode)
    papers, R_mis = ct.readings()
    MERGE['on'], MERGE['absorbed'] = merge, {}
    MERGE['held'] = {s: {i for i, _, _ in _MATCH(R_mis['curation'], R_mis[s])[0]} for s in ('catlog', 'rgf')}
    for s in R_reg:  # the values the judges saw keep their places
        assert [v['id'] for v in R_reg[s]] == [v['id'] for v in R_mis[s]], f'{s}: a value moved; the key would not apply'
    changed = {s: {i for i, (a, b) in enumerate(zip(R_reg[s], R_mis[s])) if a['value'] != b['value']} for s in R_reg}
    key = json.loads((sc.CHK / '_key.json').read_text())
    base_verdicts = sc.BASE_VERDICTS if hasattr(sc, 'BASE_VERDICTS') else sc.verdicts
    sc.BASE_VERDICTS = base_verdicts
    reread = []

    def verdicts(p, k=1):
        v = base_verdicts(p, k)
        if v is None:
            return None
        f = sc.CHK / f'{p}.check{k}.json'
        full = {str(x.get('id')): x for x in json.loads(f.read_text()).get('verdicts', [])}
        for i, (s, ix) in key.get(p, {}).get('index', {}).items():
            if ix in changed[s] and v.get(i) == 'measured_here_other_scale':
                rv = str(full.get(i, {}).get('right_value') or '')
                x = reader('written')(R_mis[s][ix]['metric'], re.sub(r'\s*[(;].*$', '', rv)) if rv else None
                new = R_mis[s][ix]['value']
                if x is not None and new and abs(x - new) <= 0.015 * max(abs(x), abs(new)):
                    v[i] = sc.RIGHT
                    if k == 1:
                        reread.append({'source': s, 'pmid': p, 'id': i, 'value': new, 'right_value': rv})
        return v

    sc.verdicts = verdicts
    Rr = sc.RIGHT
    sc.VIEWS = {'as_printed': (Rr, 'as_printed_but_misprint'), 'corrected': (Rr, 'corrected_misprint'),
                'reprints_right': (Rr, 'as_printed_but_misprint', 'credited_to_earlier_work'),
                'reprints_repeats_right': (Rr, 'as_printed_but_misprint', 'credited_to_earlier_work', 'repeat_of_one_printed_value')}
    tmp = OUT / f'_{out_name}'
    tmp.mkdir(parents=True, exist_ok=True)
    sc.HERE = tmp
    MERGE['views'] = sc.VIEWS
    sc.main()
    absorbed = MERGE['absorbed']
    MERGE['on'], MERGE['held'] = False, None
    assert set(absorbed) == set(sc.VIEWS), absorbed
    (OUT / out_name).mkdir(parents=True, exist_ok=True)
    for f in ('results.json', 'RESULTS.md'):
        (tmp / 'checked' / f).replace(OUT / out_name / f)
    (tmp / 'checked').rmdir()
    tmp.rmdir()
    d = json.loads((OUT / out_name / 'results.json').read_text())
    D, _ = ct.disputed(R_mis)
    still = [x for x in reread if key[x['pmid']]['index'][x['id']][1] in D[x['source']]]
    gone = [x for x in reread if x not in still]
    d['misreads_corrected_in_place'] = {s: len(changed[s]) for s in changed}
    d['verdicts_read_again'] = still
    d['misread_values_now_agreed_by_all_three'] = gone
    d['reader'], d['reference_merge_fixed'] = mode, merge
    d[MERGED if not merge else ENTERED] = absorbed
    if merge == 'except_repeats':
        d['what_if_post_hoc'] = 'values judged a repeat of one printed value keep the registered merge; every other value as with the merge fixed'
    (OUT / out_name / 'results.json').write_text(json.dumps(d, indent=1, default=str))
    # F6: the page check without and with only the fine-tuning papers (the scorer's table on a subset of papers)
    return d, changed


def f6_pagecheck():
    """F6, post hoc: papers whose checked values include a wrong number (another scale, not this metric, not in the paper),
    RGF against CatLog, on the 15 papers in EnzyExtract's fine-tuning set and on the other 64; the misreads reader and the
    verdicts read again as in page_check(), registered alongside."""
    from math import comb
    sc = sys.modules.get('s2c_score_checked') or load('s2c_score_checked', HERE / 'score_checked.py')
    ct = sc.ct
    WRONG = {'measured_here_other_scale', 'not_this_metric', 'not_found_in_paper'}
    key = json.loads((sc.CHK / '_key.json').read_text())
    out = {}
    for mode in ('registered', 'misreads'):
        use('registered')
        R_reg = ct.readings()[1]
        use(mode)
        papers, R = ct.readings()
        D, _ = ct.disputed(R)
        changed = {s: {i for i, (a, b) in enumerate(zip(R_reg[s], R[s])) if a['value'] != b['value']} for s in R}
        wrong = {'catlog': set(), 'rgf': set()}
        for p in key:
            f = sc.CHK / f'{p}.check1.json'
            if not f.exists():
                continue
            full = {str(x.get('id')): x for x in json.loads(f.read_text()).get('verdicts', [])}
            for i, (s, ix) in key[p]['index'].items():
                if s not in wrong or ix not in D[s]:
                    continue
                x = full.get(i, {})
                vv = x.get('verdict')
                if ix in changed[s] and vv == 'measured_here_other_scale' and x.get('right_value'):
                    rv = reader('written')(R[s][ix]['metric'], re.sub(r'\s*[(;].*$', '', str(x['right_value'])))
                    new = R[s][ix]['value']
                    if rv is not None and new and abs(rv - new) <= 0.015 * max(abs(rv), abs(new)):
                        vv = sc.RIGHT
                if vv in WRONG:
                    wrong[s].add(p)
        def split(ps):
            a = len([p for p in ps if p in wrong['rgf'] and p not in wrong['catlog']])
            b = len([p for p in ps if p in wrong['catlog'] and p not in wrong['rgf']])
            n, k = a + b, min(a, b)
            pv = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
            return {'papers': len(ps), 'rgf': len([p for p in ps if p in wrong['rgf']]), 'catlog': len([p for p in ps if p in wrong['catlog']]),
                    'rgf_only': a, 'catlog_only': b, 'sign_test_p': pv}
        out[mode] = {'all': split(papers), 'without_finetuning_papers': split([p for p in papers if p not in FT]),
                     'finetuning_papers_only': split([p for p in papers if p in FT]),
                     'finetuning_papers': sorted(p for p in papers if p in FT)}
    use('registered')
    (OUT / 'f6_pagecheck.json').write_text(json.dumps(out, indent=1))
    print(json.dumps({m: {k: v for k, v in out[m].items() if k != 'finetuning_papers'} for m in out}, indent=1))
    return out


def main():
    if '--f6' in sys.argv:
        return f6_pagecheck()
    OUT.mkdir(exist_ok=True)
    use('registered')
    M.check()  # the code still gives the 22 October counts with the registered reading
    reg = json.loads((HERE / 'results.json').read_text())
    papers = reg['papers_list']
    T = {mode: table_for(mode, papers) for mode in ('registered', 'misreads', 'written')}
    a, b = T['registered']['sources'], reg['sources']
    for n in ('catlog', 'run_RGF', 'plain'):
        for k in ('recall', 'precision'):
            assert a[n]['all'][k]['est'] == b[n]['all'][k]['est'], ('the registered reading does not reproduce results.json', n, k)
    cells = changed_cells(papers)
    T['changed_cells'] = cells
    (OUT / 'table.json').write_text(json.dumps(T, indent=1, default=str))
    dr, _ = page_check('registered', merge=False, out_name='checked_registered_reproduced')
    pub = json.loads((HERE / 'checked' / 'results.json').read_text())
    # checked/results.json holds the check's own two rules; views.json (stage2_scoring_rules_20261117) all four
    rules = json.loads((HERE.parents[1] / 'stage2_scoring_rules_20261117' / 'views.json').read_text())
    for v in pub['views']:
        assert dr['views'][v] == pub['views'][v], ('the registered page check is not reproduced', v)
        assert dr['reference_from'][v] == pub['reference_from'][v], ('the registered reference is not reproduced', v)
        for m in pub['reference']:
            assert dr['reference'][m]['values'][v] == pub['reference'][m]['values'][v], ('the registered reference is not reproduced', v, m)
    for k in ('verdicts', 'values_checked', 'against_the_curation_list'):
        assert dr[k] == pub[k], ('the registered page check is not reproduced', k)
    for v in rules['views']:
        assert {k: dr['views'][v][k] for k in ('sources', 'catlog_minus')} == rules['views'][v], ('views.json is not reproduced', v)
    print('check passed: the registered page check reproduced exactly (checked/results.json, and all four rules of views.json)')
    dm, _ = page_check('registered', merge=True, out_name='checked_merge_fixed_only')
    do, _ = page_check('misreads', merge=False, out_name='checked_misreads_fixed_only')
    d, changed = page_check('misreads', merge=True, out_name='checked')
    # what-if (post hoc, the merge recount's): under the most generous rule the fix lets RGF's repeats of one printed
    # value in as second copies of values already in the reference; here those alone keep the registered merge
    dw, _ = page_check('misreads', merge='except_repeats', out_name='checked_whatif_repeats_keep_the_registered_merge')
    def size(x, v):
        return sum(x['reference'][m]['values'][v] for m in x['reference'])
    for off, on in ((dr, dm), (do, d), (do, dw)):  # what the fix lets in is the reference's growth
        for v in on[ENTERED]:
            assert size(on, v) - size(off, v) == sum(on[ENTERED][v].values()), ('the merge fix: growth', v)
    print('check passed: with the merge fixed, the reference grows by exactly the values the fix lets in')
    use('registered')
    f6_pagecheck()
    write_md(T, d, reg)


def write_md(T, d, reg):
    def dif(x):
        return '-' if x['est'] is None else f"{x['est']:+.3f} ({x['lo']:+.3f} to {x['hi']:+.3f})"

    def sh(x):
        return f"{x['est']:.3f} ({x['lo']:.3f} to {x['hi']:.3f})"
    L = ['# Stage 2 scored again with its units reading fixed (post hoc)', '',
         'Registered: score_stage2.py and score_checked.py as committed (their results.json, reproduced here). Misreads: cells the '
         'registered reading read as another number read as written. Written: also the cells it left unread, read as written. '
         'Found after the result by an independent audit (writing/research/comparison_audit_20261118/enzyextract.md, F1).', '',
         '## Cells whose reading changes', '']
    from collections import Counter
    cnt = Counter((c['source'], c['kind']) for c in T['changed_cells'])
    L.append('; '.join(f'{s} {k}: {n}' for (s, k), n in sorted(cnt.items())) + '.')
    L += ['', '## Against the curation', '', '| Source | Registered | Misreads fixed | Every cell as written |', '|---|---|---|---|']
    for n in ('catlog', 'plain', 'run_RGF', 'run_4o-05', 'run_sonnet37', 'enzyextract_db', 'brenda'):
        L.append(f'| {n} | ' + ' | '.join(f"{T[m]['sources'][n]['all']['recall']['est']:.3f} / {T[m]['sources'][n]['all']['precision']['est']:.3f}"
                                         for m in ('registered', 'misreads', 'written')) + ' |')
    L += ['', '| CatLog minus RGF | Registered | Misreads fixed | Every cell as written |', '|---|---|---|---|']
    for metric in ('all', 'kcat', 'Km', 'kcat/Km'):
        for k in ('recall', 'precision'):
            L.append(f'| {metric} {k} | ' + ' | '.join(dif(T[m]['catlog_minus']['run_RGF'][metric][k]) for m in ('registered', 'misreads', 'written')) + ' |')
    for k in ('recall', 'precision'):
        L.append(f"| on RGF's 78 papers, {k} | " + ' | '.join(dif(T[m]['on_rgf_papers']['catlog_minus_rgf'][k]) for m in ('registered', 'misreads', 'written')) + ' |')
    for lab in ('without_misprint_papers', 'without_finetuning_papers', 'finetuning_papers_only'):
        for k in ('recall', 'precision'):
            L.append(f"| {lab.replace('_', ' ')} ({T['written'][lab]['papers']}), {k} | " + ' | '.join(
                dif(T[m][lab]['catlog_minus']['run_RGF'][k]) for m in ('registered', 'misreads', 'written')) + ' |')
    L += ['', '| CatLog minus BRENDA (STAGE2.md endpoint 4) | Registered | Misreads fixed | Every cell as written |', '|---|---|---|---|']
    for k in ('recall', 'precision'):
        L.append(f'| all, {k} | ' + ' | '.join(dif(T[m]['catlog_minus']['brenda']['all'][k]) for m in ('registered', 'misreads', 'written')) + ' |')
        L.append(f'| without the two misprint papers, {k} | ' + ' | '.join(dif(T[m]['without_misprint_papers']['catlog_minus']['brenda'][k]) for m in ('registered', 'misreads', 'written')) + ' |')
    for metric in ('kcat', 'Km', 'kcat/Km'):
        for k in ('recall', 'precision'):
            L.append(f'| {metric} {k} | ' + ' | '.join(dif(T[m]['catlog_minus']['brenda'][metric][k]) for m in ('registered', 'misreads', 'written')) + ' |')
    L += ['', f"CatLog minus the plain reading, recall: " + '; '.join(f"{m} {dif(T[m]['catlog_minus']['plain']['all']['recall'])}" for m in ('registered', 'misreads', 'written')) + '.',
          f"Best run: " + '; '.join(f"{m} {T[m]['best_run']}" for m in ('registered', 'misreads', 'written')) + '.', '',
          '## The page check: misreads fixed in place, and the reference merge fixed', '']
    VV = {n: json.loads((OUT / n / 'results.json').read_text()) for n in ('checked_registered_reproduced', 'checked_merge_fixed_only', 'checked_misreads_fixed_only', 'checked')}
    VV0 = VV['checked_registered_reproduced']
    L += [
          'A reading\'s value judged right may merge only into a reference value that the same reading does not already hold, '
          'i.e. not into a curation value that reading matches (registered: into any reference value, so such a value never entered '
          'the reference and counted against its own reading). Values the registered merge sent into a value their own reading holds: '
          + '; '.join(f"{v} {x}" for v, x in VV0[MERGED].items()) + '. Fixed, the values that enter the reference because of it '
          '(the growth of the reference): ' + '; '.join(f"{v} {x}" for v, x in VV['checked'][ENTERED].items()) + '.', '',
          '| CatLog minus RGF | Registered | Merge fixed only | Misreads fixed only | Both fixed |', '|---|---|---|---|---|']
    for v in ('as_printed', 'corrected', 'reprints_right', 'reprints_repeats_right'):
        for k in ('recall', 'precision'):
            L.append(f'| {v}, {k} | ' + ' | '.join(dif(VV[n]['views'][v]['catlog_minus']['run_RGF']['all'][k]) for n in VV) + ' |')
    for v in ('as_printed',):
        L.append('| as_printed: CatLog; RGF (recall / precision) | ' + ' | '.join(
            f"{VV[n]['views'][v]['sources']['catlog']['all']['recall']['est']:.3f} / {VV[n]['views'][v]['sources']['catlog']['all']['precision']['est']:.3f}; "
            f"{VV[n]['views'][v]['sources']['run_RGF']['all']['recall']['est']:.3f} / {VV[n]['views'][v]['sources']['run_RGF']['all']['precision']['est']:.3f}" for n in VV) + ' |')
    for v in ('as_printed', 'corrected', 'reprints_right', 'reprints_repeats_right'):
        L.append(f'| {v}: reference values | ' + ' | '.join(str(sum(VV[n]['reference'][m]['values'][v] for m in VV[n]['reference'])) for n in VV) + ' |')
    W_ = json.loads((OUT / 'checked_whatif_repeats_keep_the_registered_merge' / 'results.json').read_text())
    w = W_['views']['reprints_repeats_right']['catlog_minus']['run_RGF']['all']
    L += ['', f"What-if (post hoc): under reprints_repeats_right the fix lets in {VV['checked'][ENTERED]['reprints_repeats_right']} values, among them "
          f"RGF's repeats of one printed value, each a second copy of a value already in the reference. With only those kept at the registered merge "
          f"(both fixes otherwise; {W_[ENTERED]['reprints_repeats_right']} let in, reference {sum(W_['reference'][m]['values']['reprints_repeats_right'] for m in W_['reference'])}): "
          f"CatLog minus RGF recall {dif(w['recall'])}, precision {dif(w['precision'])}."]
    L += ['', '## The page check, both fixed: details', '',
          f"Misread values corrected: {d['misreads_corrected_in_place']}. Of those judged at another scale, with the judge's right value equal to the new "
          f"reading: {len(d['verdicts_read_again'])} still disputed now count as measured here ({dict(Counter(x['source'] for x in d['verdicts_read_again']))}), "
          f"and {len(d['misread_values_now_agreed_by_all_three'])} now agree across all three readings and leave the check "
          f"({dict(Counter(x['source'] for x in d['misread_values_now_agreed_by_all_three']))}).", '',
          f"Verdicts now: {d['verdicts']}.", '', '| View | CatLog | RGF | CatLog minus RGF: recall | precision |', '|---|---|---|---|---|']
    for v in d['views']:
        s, cm = d['views'][v]['sources'], d['views'][v]['catlog_minus']['run_RGF']['all']
        L.append(f"| {v} | {s['catlog']['all']['recall']['est']:.3f} / {s['catlog']['all']['precision']['est']:.3f} | "
                 f"{s['run_RGF']['all']['recall']['est']:.3f} / {s['run_RGF']['all']['precision']['est']:.3f} | {dif(cm['recall'])} | {dif(cm['precision'])} |")
    f6 = json.loads((OUT / 'f6_pagecheck.json').read_text())
    L += ['', '## F6, post hoc: the 15 papers in EnzyExtract\'s fine-tuning set', '',
          'Against the curation, CatLog minus RGF without them and with only them is in the table above. Papers whose checked values '
          'include a wrong number (another scale, not this metric, not in the paper), RGF against CatLog:', '',
          '| Papers | Registered | Misreads fixed |', '|---|---|---|']
    for k in ('all', 'without_finetuning_papers', 'finetuning_papers_only'):
        a, b = f6['registered'][k], f6['misreads'][k]
        L.append(f"| {k.replace('_', ' ')} ({a['papers']}) | {a['rgf']} against {a['catlog']}, sign test P = {a['sign_test_p']:.2g} | "
                 f"{b['rgf']} against {b['catlog']}, P = {b['sign_test_p']:.2g} |")
    L.append('')
    L.append('The 15: ' + ', '.join(f6['misreads']['finetuning_papers']) + '.')
    (OUT / 'RESULTS.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
