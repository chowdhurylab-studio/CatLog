#!/usr/bin/env python3
"""The broad test scored again with the scoring errors found after the result fixed (CORRECTIONS.md). The registered
scorer (`build.py score`) and its output (`run/results.json`) are unchanged. This file applies the same rules and
bootstrap, and puts each fix behind a switch:

  F5   An exponent inside the ± part of an EnzyExtract string ('2.15 × 10^6 ± 8.20 × 10^4 M^-1 s^-1') was applied to
       the value. The string is read without its error term, and the paper is matched again. A value judged at
       another scale whose judge's right value equals the new reading counts as measured here.
  F2   The scope "records that hold a kcat" was applied to CatLog only. An EnzyExtract value that equals (1.5%, one to
       one, the test's matcher) a value CatLog stores for the paper on a record without a kcat is out of scope too.
  F10  Estimates and bounds are kept unrounded until printed (the registered results.json rounds them to 4 places).

With every switch off it reproduces run/results.json exactly, and it stops otherwise. Also computed:
  F13  the two registered secondaries left unreported (PDF papers against XML-only papers; EnzyExtract values by
       how they were read, with their verdicts);
  F4   post hoc, the scores without 12723605;
  F2a  the scope fix as the audit defined it (only values judged right, greedy), for comparison.

  python3 -I -B score_corrected.py      -> corrected/results.json, corrected/RESULTS.md
"""
import csv, gzip, importlib.util, json, re, sys
from collections import Counter
from fractions import Fraction
from math import comb
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('build', HERE / 'build.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
C = B.common()
RUN, OUT = HERE / 'run', HERE / 'corrected'
RIGHT, WRONG_NUMBER, RULES, VERDICTS = B.RIGHT, B.WRONG_NUMBER, B.RULES, B.VERDICTS
PRIMARY = 'printed_here (primary)'
F5_STRINGS = []
PM_EXP = re.compile(r'^\s*([-+]?[\d.]+\s*(?:×|x|\*)\s*10\s*\^?\s*[-−]?\s*\d+)\s*(?:±|\+/-|\+-)\s*[\d.]+\s*(?:×|x|\*)\s*10\s*\^?\s*[-−]?\s*\d+\s*(.*)$')


def load():
    with gzip.open(B.WORK / 'frame_values.json.gz', 'rt') as f:
        allv = json.load(f)
    key = json.loads((RUN / 'key.json').read_text())
    V, V2 = {}, {}
    for p in key:
        V[p], V2[p] = {}, {}
        for _, c in key[p].get('parts', []):
            for n, store in ((1, V[p]), (2, V2[p])):
                f = RUN / 'judged' / p / c.replace('check1', f'check{n}')
                if f.exists():
                    for x in json.loads(f.read_text())['verdicts']:
                        if x.get('verdict') in VERDICTS:
                            store[str(x['id'])] = x
    frame = {r['pmid']: r for r in csv.DictReader(open(HERE / 'frame.tsv'), delimiter='\t')}
    return allv, key, V, V2, frame


def out_of_scope_values(papers):
    """CatLog's values on records without a kcat at the freeze (the export): Km in mM, printed kcat/Km."""
    out = {p: [] for p in papers}
    with gzip.open(B.EXPORT, 'rt') as f:
        for line in f:
            m = re.search(r'"pubmed_id": "([^"]+)"', line[:400])
            if not m or m.group(1) not in out:
                continue
            r = json.loads(line)
            if C.num(r.get('kcat')) is not None:
                continue
            p = r['pubmed_id']
            base = {'organism': r.get('organism') or '', 'temp': '' if r.get('temperature_c') in (None, 'None') else str(r.get('temperature_c')),
                    'pH': '' if r.get('ph') in (None, 'None') else str(r.get('ph')), 'cosub': r.get('cosubstrate') or '', 'where': '', 'quote': ''}
            if C.num(r.get('km')) is not None and r.get('km_unit') == 'mM':
                out[p].append({**base, 'pmid': p, 'metric': 'Km', 'value': float(r['km']), 'enzyme': r.get('enzyme_name', ''),
                               'substrate': r.get('substrate_name', ''), 'variant': r.get('mutation_signature', ''), 'id': r['measurement_id'] + ':Km'})
            if C.num(r.get('kcat_over_km')) is not None and r.get('kcat_over_km_source') == 'printed':
                out[p].append({**base, 'pmid': p, 'metric': 'kcat/Km', 'value': float(r['kcat_over_km']), 'enzyme': r.get('enzyme_name', ''),
                               'substrate': r.get('substrate_name', ''), 'variant': r.get('mutation_signature', ''), 'id': r['measurement_id'] + ':kcat/Km'})
    return out


def prepare(allv, key, V, fix5=False, fix2=False, scope=None, audit_f2=False):
    """Per paper: CatLog and EnzyExtract values, pairs, each disputed value's verdict, and the values out of scope."""
    P, notes = {}, Counter()
    for p in key:
        d = allv[p]
        Cv = d['catlog']
        Ev = [dict(v) for v in d['enzyextract']]
        pairs = [tuple(x) for x in d['pairs']]
        changed = set()
        if fix5:
            for k, v in enumerate(Ev):
                m = PM_EXP.match(v['raw']) if v['how'] == 'catlog_units' else None
                if m:
                    x = C.parse_value_unit(v['metric'], f'{m.group(1)} {m.group(2)}')
                    if x is not None and abs(x - v['value']) > 0.015 * max(x, v['value']):
                        v['value'] = float(f'{x:.6g}')
                        changed.add(k)
            if changed:
                new, _, _ = C.match(Cv, Ev)
                pairs = [(a, b) for a, b, _ in new]
                notes['F5 values read again'] += len(changed)
                rev0 = {(s_, k_): i for i, (s_, k_) in key[p]['index'].items()}
                ae_new = {b for _, b in pairs}
                for k in sorted(changed):
                    x = V[p].get(rev0.get(('enzyextract', k)), {})
                    F5_STRINGS.append({'pmid': p, 'id': rev0.get(('enzyextract', k)), 'metric': Ev[k]['metric'], 'string': Ev[k]['raw'],
                                       'registered_reading': d['enzyextract'][k]['value'], 'reading_without_the_error_term': Ev[k]['value'],
                                       'verdict': x.get('verdict'), 'judges_right_value': x.get('right_value'),
                                       'catlog_stores_it': any(c['metric'] == Ev[k]['metric'] and C.close(c['value'], Ev[k]['value']) for c in Cv),
                                       'agreed_after_matching_again': k in ae_new})
        rev = {(s, k): i for i, (s, k) in key[p]['index'].items()}
        ac, ae = {a for a, _ in pairs}, {b for _, b in pairs}
        J = {'catlog': {}, 'enzyextract': {}}
        for s, L, agreed in (('catlog', Cv, ac), ('enzyextract', Ev, ae)):
            old = {a for a, _ in d['pairs']} if s == 'catlog' else {b for _, b in d['pairs']}
            for k in range(len(L)):
                if k in agreed:
                    continue
                i = rev.get((s, k))
                x = V[p].get(i) if i else None
                vv = x['verdict'] if x else 'cannot_decide'
                if k in old:
                    vv, _ = 'cannot_decide', notes.update(['agreed before, disputed after matching again'])
                if s == 'enzyextract' and k in changed and vv == 'measured_here_other_scale' and x and x.get('right_value'):
                    rv = C.parse_value_unit(L[k]['metric'], re.sub(r'\s*\(.*$', '', x['right_value']))
                    if rv and abs(rv - L[k]['value']) <= 0.015 * max(rv, L[k]['value']):
                        vv = RIGHT
                        notes['F5 verdict read again (right value equals the new reading)'] += 1
                J[s][k] = vv
        notes['F5 values now agreed'] += sum(1 for k in changed if k in ae)
        out_e = set()
        if fix2:
            disp = [k for k in range(len(Ev)) if k not in ae and (not audit_f2 or J['enzyextract'][k] in RULES[PRIMARY][0])]
            pool = scope.get(p, [])
            if disp and pool:
                if audit_f2:  # the audit's own rule: greedy, in order, values judged right only
                    left = list(pool)
                    for k in disp:
                        for j, c in enumerate(left):
                            if c['metric'] == Ev[k]['metric'] and C.close(Ev[k]['value'], c['value']):
                                out_e.add(k)
                                left.pop(j)
                                break
                else:
                    sub = [Ev[k] for k in disp]
                    m, _, _ = C.match(pool, sub)
                    out_e = {disp[j] for _, j, _ in m}
            notes['F2 EnzyExtract values out of scope'] += len(out_e)
            notes['F2 of them judged right (primary rule)'] += sum(1 for k in out_e if J['enzyextract'][k] in RULES[PRIMARY][0])
        P[p] = {'C': Cv, 'E': Ev, 'pairs': pairs, 'J': J, 'out_e': out_e}
    return P, dict(notes)


def rows(P, rule, metric='all', drop=()):
    right, neutral = RULES[rule]
    out, w = [], {'catlog': 0, 'enzyextract': 0, 'discordant_ee_only': 0, 'discordant_catlog_only': 0}
    for p, x in P.items():
        if p in drop:
            continue
        L = {'catlog': x['C'], 'enzyextract': x['E']}
        J = x['J']
        inm = lambda s, k: metric == 'all' or L[s][k]['metric'] == metric  # noqa: E731
        ac, ae = {a for a, _ in x['pairs']}, {b for _, b in x['pairs']}
        keep = {s: [k for k in range(len(L[s])) if inm(s, k) and J[s].get(k) not in neutral and J[s].get(k) != 'cannot_decide'
                    and not (s == 'enzyextract' and k in x['out_e'])] for s in L}
        ok_c = [k for k in keep['catlog'] if k in ac or J['catlog'].get(k) in right]
        ok_e = [k for k in keep['enzyextract'] if k in ae or J['enzyextract'].get(k) in right]
        ref = sum(1 for a, _ in x['pairs'] if inm('catlog', a)) + sum(1 for k in ok_c if k not in ac) + sum(1 for k in ok_e if k not in ae)
        wc = any(J['catlog'].get(k) in WRONG_NUMBER for k in J['catlog'] if inm('catlog', k))
        we = any(J['enzyextract'].get(k) in WRONG_NUMBER for k in J['enzyextract'] if inm('enzyextract', k) and k not in x['out_e'])
        w['catlog'] += wc
        w['enzyextract'] += we
        w['discordant_ee_only'] += we and not wc
        w['discordant_catlog_only'] += wc and not we
        out.append({'pmid': p, 'ref': ref, 'c_held': len(ok_c), 'c_n': len(keep['catlog']), 'e_held': len(ok_e), 'e_n': len(keep['enzyextract']),
                    'c_wrong_numbers': sum(1 for k in J['catlog'] if inm('catlog', k) and J['catlog'][k] in WRONG_NUMBER),
                    'e_wrong_numbers': sum(1 for k in J['enzyextract'] if inm('enzyextract', k) and k not in x['out_e'] and J['enzyextract'][k] in WRONG_NUMBER)})
    return out, w


def sign_p(a, b):
    n, k = a + b, min(a, b)
    return 1.0 if n == 0 else float(min(Fraction(1), 2 * Fraction(sum(comb(n, i) for i in range(k + 1)), 2 ** n)))


def boot(rs, Bn=10000, seed=20261031):
    """build.boot_diff, unrounded (the same generator, draws and order)."""
    a = {k: np.array([r[k] for r in rs], float) for k in ('ref', 'c_held', 'c_n', 'e_held', 'e_n')}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(rs), (Bn, len(rs)))
    out = {}
    for name, (nc, dc, ne, de) in {'recall': ('c_held', 'ref', 'e_held', 'ref'), 'precision': ('c_held', 'c_n', 'e_held', 'e_n')}.items():
        ec, ee = a[nc].sum() / max(a[dc].sum(), 1), a[ne].sum() / max(a[de].sum(), 1)
        d = a[nc][idx].sum(1) / np.maximum(a[dc][idx].sum(1), 1) - a[ne][idx].sum(1) / np.maximum(a[de][idx].sum(1), 1)
        lo, hi = np.percentile(d, [2.5, 97.5])
        out[name] = {'catlog': float(ec), 'enzyextract': float(ee), 'diff': float(ec - ee), 'lo': float(lo), 'hi': float(hi)}
    return out


def endpoints(P, rule=PRIMARY, drop=()):
    res = {}
    for metric in ('all', 'kcat', 'Km', 'kcat/Km'):
        rs, w = rows(P, rule, metric, drop)
        w['sign_test_p'] = sign_p(w['discordant_ee_only'], w['discordant_catlog_only'])
        t = {k: sum(r[k] for r in rs) for k in ('ref', 'c_held', 'c_n', 'e_held', 'e_n', 'c_wrong_numbers', 'e_wrong_numbers')}
        res[metric] = {'papers': len(rs), 'papers_with_a_wrong_number': w, **boot(rs), 'totals': t,
                       'catlog_not_right': t['c_n'] - t['c_held'], 'catlog_missed': t['ref'] - t['c_held'],
                       'enzyextract_not_right': t['e_n'] - t['e_held'], 'enzyextract_missed': t['ref'] - t['e_held']}
    return res


def reproduce_registered(R):
    """With every switch off, the registered output (run/results.json, rounded to 4 places) exactly; else stop."""
    reg = json.loads((RUN / 'results.json').read_text())
    bad = []
    for rule in RULES:
        for metric in ('all', 'kcat', 'Km', 'kcat/Km'):
            a, b = R[rule][metric], reg['rules'][rule][metric]
            if a['papers_with_a_wrong_number'] | {'sign_test_p': 0} != b['papers_with_a_wrong_number'] | {'sign_test_p': 0}:
                bad.append((rule, metric, 'wrong papers'))
            if {k: a['totals'][k] for k in b['totals']} != b['totals']:
                bad.append((rule, metric, 'totals'))
            for m in ('recall', 'precision'):
                for k in ('catlog', 'enzyextract', 'diff', 'lo', 'hi'):
                    if round(a[m][k], 4) != b[m][k]:
                        bad.append((rule, metric, m, k, a[m][k], b[m][k]))
    if bad:
        sys.exit(f'the switches-off scoring does not reproduce run/results.json: {bad[:5]}')
    return True


def by_how(P, allv):
    """F13 (registered secondary): EnzyExtract values by how they were read, with their verdicts."""
    c = Counter()
    for p, x in P.items():
        ae = {b for _, b in x['pairs']}
        for k, v in enumerate(x['E']):
            vv = 'agreed' if k in ae else ('out of scope' if k in x['out_e'] else x['J']['enzyextract'].get(k, 'cannot_decide'))
            c[(v['how'], vv)] += 1
    out = {}
    for (how, vv), n in sorted(c.items()):
        out.setdefault(how, {})[vv] = n
    for how in out:
        out[how]['values'] = sum(out[how].values())
        out[how]['wrong_numbers'] = sum(n for vv, n in out[how].items() if vv in WRONG_NUMBER)
    return out


def second_agent(key, V, V2):
    n = same = same_w = 0
    for p in key:
        for i, x in V2[p].items():
            if i in V[p]:
                n += 1
                same += V[p][i]['verdict'] == x['verdict']
                same_w += (V[p][i]['verdict'] in WRONG_NUMBER) == (x['verdict'] in WRONG_NUMBER)
    return {'values': n, 'same_verdict': same, 'same_wrong_number_call': same_w}


def f3(x):
    return f'{x:.3f}'


def diff(b):
    return f"{b['diff']:+.3f} ({b['lo']:+.3f} to {b['hi']:+.3f})"


# ------------------------------------------------------------------------------------------------ what-ifs (post hoc)
UNREAD_KINDS = (('bound', re.compile(r'^\s*(<|>|≤|≥|less than|greater than|below|above)', re.I)),
                ('not detected', re.compile(r'^\s*(n\.?\s?d\.?|not\s+detect\w*|n\.\s?a\.?|undetect\w*)\s*$', re.I)),
                ('percent or relative', re.compile(r'%|relative|\bfold\b', re.I)),
                ('per mass or activity', re.compile(r'(\bU\b|units?|kat)\s*(/|per|·\s*)?\s*(mg|µg|ug|g|kg)\b|/\s*mg\b|mg\s*\^\s*-1|/\s*kg\b', re.I)))


def unread_kinds(key):
    """EnzyExtract cells of the sampled papers that no route read, of a kind the judge's prompt calls not this metric
    (a bound or not-detected entry, a relative value, a per-mass activity), by paper."""
    st = {r['pmid']: r for r in csv.DictReader(B.git_show('papers.tsv').splitlines(), delimiter='\t')}
    doi = {}
    for p, r in st.items():
        d = (r.get('doi') or '').strip().lower()
        if d:
            doi[d] = p
            doi[d.replace('/', '_')] = p
    rows = {p: [] for p in key}
    with open(B.WORK / 'thedata.tsv') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            k = r['pmid'].strip()
            p = k if k in st else doi.get(k.lower())
            if p in rows:
                rows[p].append(r)
    out = {}
    for p, rs in rows.items():
        for r in rs:
            for m, col, own in (('kcat', 'kcat', r['kcat_value']), ('Km', 'km', r['km_value']), ('kcat/Km', 'kcat_km', '')):
                raw = (r[col] or '').strip()
                if not raw or raw.lower() in ('none', 'nan', 'null'):
                    continue
                v = None
                for t in (raw, B.ee_clean(m, raw)):
                    try:
                        v = C.parse_value_unit(m, t)
                    except (OverflowError, ValueError, ZeroDivisionError):
                        v = None
                    if v is not None:
                        break
                if v is None and C.num(own) and C.num(own) > 0:
                    v = C.num(own)
                if v is not None:
                    continue
                kind = next((n for n, rx in UNREAD_KINDS if rx.search(raw)), None)
                if kind and (m, raw) not in {(c['metric'], c['cell']) for c in out.get(p, [])}:  # each distinct cell once
                    out.setdefault(p, []).append({'metric': m, 'cell': raw, 'kind': kind})
    return out


def what_ifs(allv, key, V, P, unread, label):
    """Post hoc what-ifs on a prepared scoring P (registered or corrected)."""
    res = {}
    # 12723605's 128 kcat/Km of CatLog counted right
    P1 = {p: dict(x, J={s: dict(j) for s, j in x['J'].items()}) for p, x in P.items()}
    j = P1['12723605']['J']['catlog']
    n = 0
    for k, vv in j.items():
        if vv == 'measured_here_other_scale' and P1['12723605']['C'][k]['metric'] == 'kcat/Km':
            j[k] = RIGHT
            n += 1
    res['12723605: its 128 kcat/Km counted right'] = {'values': n, **{r: endpoints(P1, r)['all'] for r in (PRIMARY, 'measured_here')}}
    res['without 12723605'] = {r: endpoints(P, r, drop={'12723605'})['all'] for r in (PRIMARY, 'printed_here, misprint corrected')}
    # EnzyExtract repeats with no listing keeping its own verdict: one listing of each such printed value counted right
    P2 = {p: dict(x, J={s: dict(j) for s, j in x['J'].items()}) for p, x in P.items()}
    groups = vals = 0
    for p, x in P2.items():
        E, J, ae = x['E'], x['J']['enzyextract'], {b for _, b in x['pairs']}
        for metric in ('kcat', 'Km', 'kcat/Km'):
            idx = sorted((k for k in range(len(E)) if E[k]['metric'] == metric and k not in x['out_e']), key=lambda k: E[k]['value'])
            cl = []
            for k in idx:
                if cl and C.close(E[cl[-1][-1]]['value'], E[k]['value']):
                    cl[-1].append(k)
                else:
                    cl.append([k])
            for g in cl:
                reps = [k for k in g if J.get(k) == 'repeat_of_one_printed_value']
                if reps and all(k not in ae and J.get(k) == 'repeat_of_one_printed_value' for k in g):
                    J[reps[0]] = RIGHT
                    groups += 1
                    vals += len(reps)
    res['EnzyExtract repeats with no listing keeping its own verdict: one listing each counted right'] = {
        'repeat_values_in_such_groups': vals, 'listings_counted_right': groups, **{r: endpoints(P2, r)['all'] for r in (PRIMARY,)}}
    # EnzyExtract cells no route read that the prompt calls not this metric, counted as wrong numbers
    base = endpoints(P, PRIMARY)['all']
    wrong_e = {p for p, x in P.items() if any(vv in WRONG_NUMBER for k, vv in x['J']['enzyextract'].items() if k not in x['out_e'])}
    wrong_c = {p for p, x in P.items() if any(vv in WRONG_NUMBER for vv in x['J']['catlog'].values())}
    e2 = wrong_e | set(unread)
    a, b2 = len(e2 - wrong_c), len(wrong_c - e2)
    res['EnzyExtract unread bounds, not-detected, relative and per-mass cells counted as wrong numbers'] = {
        'cells': sum(len(v) for v in unread.values()), 'by_kind': dict(Counter(c['kind'] for v in unread.values() for c in v)),
        'papers_with_such_cells': len(unread), 'of_them_without_another_wrong_number': len(set(unread) - wrong_e),
        'papers_with_a_wrong_number': {'catlog': len(wrong_c), 'enzyextract': len(e2), 'discordant_ee_only': a, 'discordant_catlog_only': b2,
                                       'sign_test_p': sign_p(a, b2)}, 'note': 'recall and precision unchanged: these cells are not values'}
    return res


def main():
    allv, key, V, V2, frame = load()
    scope = out_of_scope_values(set(key))
    runs = {}
    P0, n0 = prepare(allv, key, V)
    runs['registered'] = ({r: endpoints(P0, r) for r in RULES}, n0, P0)
    reproduce_registered(runs['registered'][0])
    for name, kw in (('F5 only', {'fix5': True}), ('F2 only', {'fix2': True, 'scope': scope}),
                     ('corrected (F5 and F2)', {'fix5': True, 'fix2': True, 'scope': scope}),
                     ('F5 and F2 as the audit defined it (check)', {'fix5': True, 'fix2': True, 'scope': scope, 'audit_f2': True})):
        Pn, notes = prepare(allv, key, V, **kw)
        runs[name] = ({r: endpoints(Pn, r) for r in RULES}, notes, Pn)
    Pc = runs['corrected (F5 and F2)'][2]
    pdf = [p for p in key if frame[p]['original'] == 'pdf']
    xml = [p for p in key if frame[p]['original'] != 'pdf']
    sec = {'papers': {'pdf': len(pdf), 'xml_only': len(xml)}}
    for name, P in (('registered', P0), ('corrected', Pc)):
        sec[name] = {'pdf_papers': endpoints(P, PRIMARY, drop=set(xml))['all'], 'xml_only_papers': endpoints(P, PRIMARY, drop=set(pdf))['all'],
                     'enzyextract_values_by_how_read': by_how(P, allv)}
    post = {}
    for name, P in (('registered', P0), ('corrected', Pc)):
        post[name] = {rule: endpoints(P, rule, drop={'12723605'})['all'] for rule in (PRIMARY, 'printed_here, misprint corrected')}
    unread = unread_kinds(key)
    wif = {name: what_ifs(allv, key, V, P, unread, name) for name, P in (('registered', P0), ('corrected', Pc))}
    Pa = runs['F5 and F2 as the audit defined it (check)'][2]
    res_audit = endpoints(Pa, PRIMARY)['all']
    res = {'what': __doc__.strip().splitlines()[0], 'second_agent': second_agent(key, V, V2),
           'what_ifs_post_hoc': wif, 'unread_cells_of_a_kind_the_prompt_calls_not_this_metric': unread,
           'F5_strings': [x for i, x in enumerate(F5_STRINGS) if x not in F5_STRINGS[:i]],
           'runs': {n: {'notes': v[1], 'rules': v[0]} for n, v in runs.items()},
           'registered_secondaries_F13': sec, 'post_hoc_without_12723605_F4': post,
           'reproduces_run_results_json_with_switches_off': True}
    OUT.mkdir(exist_ok=True)
    (OUT / 'results.json').write_text(json.dumps(res, indent=1) + '\n')
    # RESULTS.md: registered and corrected side by side, rounded once
    R, Cc = runs['registered'][0], runs['corrected (F5 and F2)'][0]
    L = ['# The broad test, scored again with the scoring errors fixed (post hoc)', '',
         'Registered: `build.py score` (run/results.json), reproduced exactly here with every fix switched off. Corrected: F5 and F2 '
         'fixed, bounds rounded once (F10). Every correction was found after the result, by an independent audit '
         '(writing/research/comparison_audit_20261118/enzyextract.md).', '',
         f"Notes: F5 {runs['F5 only'][1]}; F2 {runs['F2 only'][1]}; both {runs['corrected (F5 and F2)'][1]}; the audit's F2 rule "
         f"{runs['F5 and F2 as the audit defined it (check)'][1]}.", '']
    for rule in RULES:
        L += [f'## {rule}', '', '| | Registered | F5 only | F2 only | Corrected (F5 and F2) |', '|---|---|---|---|---|']
        cols = [runs[n][0][rule] for n in ('registered', 'F5 only', 'F2 only', 'corrected (F5 and F2)')]
        w = lambda a: (f"CatLog {a['all']['papers_with_a_wrong_number']['catlog']}, EnzyExtract {a['all']['papers_with_a_wrong_number']['enzyextract']}; "  # noqa: E731
                       f"{a['all']['papers_with_a_wrong_number']['discordant_ee_only']}:{a['all']['papers_with_a_wrong_number']['discordant_catlog_only']}, "
                       f"P = {a['all']['papers_with_a_wrong_number']['sign_test_p']:.2g}")
        L.append('| Papers with a wrong number | ' + ' | '.join(w(a) for a in cols) + ' |')
        for metric in ('all', 'kcat', 'Km', 'kcat/Km'):
            for m in ('recall', 'precision'):
                L.append(f'| {metric} {m} | ' + ' | '.join(f"{f3(a[metric][m]['catlog'])} / {f3(a[metric][m]['enzyextract'])}; {diff(a[metric][m])}" for a in cols) + ' |')
        L.append('| Values: CatLog not right, missed; EnzyExtract not right, missed | ' + ' | '.join(
            f"{a['all']['catlog_not_right']}, {a['all']['catlog_missed']}; {a['all']['enzyextract_not_right']}, {a['all']['enzyextract_missed']}" for a in cols) + ' |')
        L.append('| Wrong numbers: CatLog, EnzyExtract | ' + ' | '.join(f"{a['all']['totals']['c_wrong_numbers']}, {a['all']['totals']['e_wrong_numbers']}" for a in cols) + ' |')
        L.append('')
    L += ['## Registered secondaries left unreported (F13), primary rule', '', '| Papers | Registered | Corrected |', '|---|---|---|']
    for g in ('pdf_papers', 'xml_only_papers'):
        a, b = sec['registered'][g], sec['corrected'][g]
        L.append(f"| {g.replace('_', ' ')} ({a['papers']}) | wrong-number papers {a['papers_with_a_wrong_number']['catlog']} against "
                 f"{a['papers_with_a_wrong_number']['enzyextract']}; recall {diff(a['recall'])}; precision {diff(a['precision'])} | "
                 f"{b['papers_with_a_wrong_number']['catlog']} against {b['papers_with_a_wrong_number']['enzyextract']}; recall {diff(b['recall'])}; precision {diff(b['precision'])} |")
    L += ['', 'EnzyExtract values by how they were read, with their verdicts: registered '
          + json.dumps(sec['registered']['enzyextract_values_by_how_read']) + '; corrected '
          + json.dumps(sec['corrected']['enzyextract_values_by_how_read']), '',
          '## Post hoc, without 12723605 (F4)', '', '| | Registered | Corrected |', '|---|---|---|']
    for rule in (PRIMARY, 'printed_here, misprint corrected'):
        a, b = post['registered'][rule], post['corrected'][rule]
        L.append(f"| {rule} | wrong-number papers {a['papers_with_a_wrong_number']['catlog']} against {a['papers_with_a_wrong_number']['enzyextract']}; "
                 f"recall {diff(a['recall'])}; precision {diff(a['precision'])} | {b['papers_with_a_wrong_number']['catlog']} against "
                 f"{b['papers_with_a_wrong_number']['enzyextract']}; recall {diff(b['recall'])}; precision {diff(b['precision'])} |")
    L += ['', f"Second judge: {res['second_agent']}."]
    (OUT / 'RESULTS.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
