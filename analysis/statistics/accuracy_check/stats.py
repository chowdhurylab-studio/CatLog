#!/usr/bin/env python3
"""Paper-level statistics for the accuracy claim: task (a) of accuracy_check_20261114 (14 November 2026).

  python3 stats.py      checks every count against the results files, then writes stats.json next to this file

Post hoc. The two tests were pooled, and the three ways of counting chosen, after both results were in. No paper is read:
the inputs are the per-paper counts (key per_paper: stored values and wrong values per source) and the lists of wrong
values and misses in the tests' results.json files. A few more files are read only to cross-check how the plain
reading's 34 as-printed values were found; each cross-check is skipped, and stats.json says so, if its file is absent.

Inputs (paths from paper/evidence):
  random_papers_20261104/full_record/results.json                        random test, final judging (147 papers)
  random_papers_20261104/full_record/first_on_same_papers/results.json   random test, first judging (same papers)
  locked_test_20261109/result/results.json                               locked test (83 held-out papers)
Cross-checks:
  locked_test_20261109/result/investigation/{9973343,10447675}.task.json and _key.json   the blind page check's readings
  <the kit folder>/records/score_locked/private/values.json      every stored value of the locked test
  <the kit folder>/records/score_randfull/private/values.json    the same for the random test
  random_test2_20261112/work/power_results.json                             an earlier rebuild of three of the intervals

Three ways of counting. Only the locked test's 9973343 and 10447675 change between them; the random test is the same in
all three (7334001's 6 CatLog values stay as judged, wrong, in every way):
  as_printed          (i)   the registered rubric, as judged: plain 57 wrong values in 9 papers, CatLog 40 in 3.
  unit_changes_right  (ii)  CatLog's 34 unit changes (9973343: 29, 10447675: 5) counted right.
  own_numbers_both    (iii) by each paper's own numbers for both sides: as (ii), and the plain reading's 34 values of
                            the same cells, which it stored as printed and the judges called supported, counted wrong.

How the 34 plain values are found (identify_as_printed): in the locked test's results.json, misses['catlog'] (supported
values that only the plain reading stored) holds 29 values of 9973343 and 5 of 10447675. Each is paired one to one with
one of CatLog's wrong values in the same paper (all wrong_scale): same metric, variant, pH and temperature, the same
substrate (first word), and the plain value equal to CatLog's value times 1000 (9973343) or 60 (10447675), within 0.5%
(CatLog's shown values are rounded to 2 decimals). The plain value must also equal CatLog's own record of the printed
cell (stored.raw at stored.raw_unit) converted to catalogue units, i.e. the plain reading stored the cell as printed.
No plain value of these papers may be left over and no CatLog value unpaired.

Statistics:
  papers with a wrong value   per source, way and test (random, locked, pooled = both, 230 papers)
  sign test                   papers where only one source erred: exact two-sided binomial test, p = 0.5
                              (scipy.stats.binomtest); papers where both erred are ties and left out
  leave one out               the sign test again without each paper that holds a wrong value, one at a time
  first judging               the sign test with the random test's first judging in place of its final judging
  bootstrap                   plain minus CatLog wrong per 1,000 stored values, paired paper bootstrap: B 10,000,
                              numpy default_rng(20261031), papers resampled with replacement, the same indices for both
                              sources, 95% percentile interval (np.percentile 2.5 and 97.5). This is the kit's
                              score_rand.boot, rate part. Pooled papers in the order random (file order) then locked
                              (file order), as random_test2_20261112/work/power.py did. Denominators: every stored value,
                              as per_paper gives them; the tests' own rates leave cannot-decide values out (random test:
                              plain 20, CatLog 21; locked: none), so the random test alone differs a little from its
                              report and the locked test matches its report exactly.
  kinds                       wrong values by verdict and by paper, per source; a descriptive sub-kind from the first
                              two judges' own reasons (keyword rules in SUBKINDS, checked to give each value exactly one)
"""
import collections, hashlib, json, re, sys, time
from pathlib import Path

import numpy as np
import scipy
from scipy.stats import binomtest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
EVID = HERE.parent  # paper/evidence
RECORDS = Path('<the kit folder>') / 'records'
FILES = {'random': EVID / 'random_papers_20261104' / 'full_record' / 'results.json',
         'random_first': EVID / 'random_papers_20261104' / 'full_record' / 'first_on_same_papers' / 'results.json',
         'locked': EVID / 'locked_test_20261109' / 'result' / 'results.json'}
INVESTIGATION = EVID / 'locked_test_20261109' / 'result' / 'investigation'
VALUES = {'locked': RECORDS / 'score_locked' / 'private' / 'values.json',
          'random': RECORDS / 'score_randfull' / 'private' / 'values.json'}
POWER = EVID / 'random_test2_20261112' / 'work' / 'power_results.json'
OUT = HERE / 'stats.json'

SOURCES = ('plain', 'catlog')
WAYS = ('as_printed', 'unit_changes_right', 'own_numbers_both')
WAY_NAMES = {'as_printed': '(i) as printed, the registered rubric',
             'unit_changes_right': "(ii) CatLog's 34 unit changes counted right",
             'own_numbers_both': "(iii) by each paper's own numbers, both sides: (ii), and the plain reading's 34 "
                                 "as-printed values of the same cells counted wrong"}
MISPRINT = {'9973343': 1000.0, '10447675': 60.0}  # CatLog stored each printed cell divided by this
EXPECT_34 = {'9973343': 29, '10447675': 5}
CLUSTER = '40195502'  # the random test's paper with 27 of the plain reading's 42 wrong values
B, SEED = 10000, 20261031
# what each file must hold: papers; per source (values, wrong values, papers with a wrong value); papers wrong on one
# side only (plain, CatLog)
EXPECT = {'random': (147, {'plain': (4530, 42, 5), 'catlog': (4390, 6, 1)}, (5, 1)),
          'random_first': (147, {'plain': (4530, 63, 11), 'catlog': (4390, 15, 6)}, (7, 2)),
          'locked': (83, {'plain': (1473, 15, 4), 'catlog': (1400, 34, 2)}, (4, 2))}
EXPECT_POOLED = {'plain': (6003, 57, 9), 'catlog': (5790, 40, 3)}  # as printed, both tests
# descriptive sub-kinds of the plain reading's wrong values, from the first two judges' reasons (and a third's if any)
SUBKINDS = [('Hill-type half-saturation constant (S0.5, K0.5, [S]0.5, K_app or K′) stored as Km, or in a kcat/Km',
             'wrong_metric', re.compile(r"Hill|S0\.5|K0\.5|sigmoid|K′|cooperativ")),
            ('activation constant (Ka) stored as Km, or in a kcat/Km', 'wrong_metric',
             re.compile(r"activation constant|kcat/Ka|\bKa\b")),
            ('credited by the paper to earlier work', 'not_measured_here',
             re.compile(r"Davidi|Taken from|previously|\[\d+\]"))]
CATLOG_KINDS = {'9973343': 'unit change from the paper’s own numbers (header printed 10^3 too high), one of the 34',
                '10447675': 'unit change from the paper’s own numbers (s^-1 header read as min^-1), one of the 34',
                '7334001': 'contested exponent of a 1981 scan (x10^-5 M read as x10^-6 M), judged 2 to 1'}


def fail(msg):
    sys.exit(f'stats.py stopped: {msg}')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def klass(v):
    return None if v is None else 'supported' if v == 'supported' else 'cannot_decide' if v == 'cannot_decide' else 'error'


# ---------- checks of the results files ----------

def check_file(name, d):
    """Every count of the file against itself and against EXPECT; returns what was checked."""
    pp = d['per_paper']
    papers, per, only = EXPECT[name]
    got = {'papers': len(pp)}
    if len(pp) != d['papers_used'] or len(pp) != papers:
        fail(f'{name}: {len(pp)} papers in per_paper, papers_used {d["papers_used"]}, expected {papers}')
    for s in SOURCES:
        vals = sum(v[s]['values'] for v in pp.values())
        wrong = sum(v[s]['wrong'] for v in pp.values())
        wp = sum(v[s]['wrong'] > 0 for v in pp.values())
        ps = d['per_source'][s]
        if (vals, wrong, wp) != (ps['values'], ps['wrong'], ps['papers_with_a_wrong_value']):
            fail(f'{name} {s}: per_paper gives {(vals, wrong, wp)}, per_source {(ps["values"], ps["wrong"], ps["papers_with_a_wrong_value"])}')
        if (vals, wrong, wp) != per[s]:
            fail(f'{name} {s}: {(vals, wrong, wp)}, expected {per[s]}')
        listed = collections.Counter(w['pmid'] for w in d['wrong'] if w['source'] == s)
        if set(listed) - set(pp) or any(listed.get(p, 0) != v[s]['wrong'] for p, v in pp.items()):
            fail(f'{name} {s}: the wrong list does not match per_paper paper by paper')
        kinds = collections.Counter(w['verdict'] for w in d['wrong'] if w['source'] == s)
        if dict(kinds) != ps['kinds']:
            fail(f'{name} {s}: verdicts {dict(kinds)} against per_source kinds {ps["kinds"]}')
        got[s] = {'values': vals, 'wrong': wrong, 'papers_with_a_wrong_value': wp, 'kinds': dict(kinds)}
    one = {'plain': sum(v['plain']['wrong'] > 0 and v['catlog']['wrong'] == 0 for v in pp.values()),
           'catlog': sum(v['catlog']['wrong'] > 0 and v['plain']['wrong'] == 0 for v in pp.values())}
    if one != d['papers_wrong_in_one_source_only'] or (one['plain'], one['catlog']) != only:
        fail(f'{name}: papers wrong on one side only {one}, file {d["papers_wrong_in_one_source_only"]}, expected {only}')
    got['papers_wrong_in_one_source_only'] = one
    got['both_sources_wrong'] = sum(v['plain']['wrong'] > 0 and v['catlog']['wrong'] > 0 for v in pp.values())
    return got


# ---------- the plain reading's 34 as-printed values ----------

def first_word(s):
    w = re.sub(r'[(),;]', ' ', str(s)).lower().split()
    return w[0] if w else ''


def printed_value(raw, raw_unit, metric):
    """The printed cell in catalogue units (kcat s^-1, kcat/Km mM^-1 s^-1), for the cells of these two papers only."""
    m = re.fullmatch(r'\s*([0-9]*\.?[0-9]+)\s*(?:[x×]\s*10\^\s*(-?[0-9]+))?\s*', str(raw))
    if not m:
        fail(f'unreadable printed cell {raw!r}')
    x = float(m.group(1)) * (10 ** int(m.group(2)) if m.group(2) else 1)
    unit = str(raw_unit).replace('μ', 'µ').strip()
    factor = {('kcat', 's^-1'): 1.0, ('kcat/Km', 'µM^-1 s^-1'): 1000.0}.get((metric, unit))
    if factor is None:
        fail(f'printed unit {raw_unit!r} for {metric} not expected in these papers')
    return x * factor


def identify_as_printed(L):
    """The 34 pairs (CatLog's wrong value, the plain reading's as-printed value of the same cell); see the docstring."""
    pairs = []
    for p, f in MISPRINT.items():
        cw = [w for w in L['wrong'] if w['pmid'] == p and w['source'] == 'catlog']
        pw = [w for w in L['wrong'] if w['pmid'] == p and w['source'] == 'plain']
        pm = [m for m in L['misses']['catlog'] if m['pmid'] == p]
        if pw or len(cw) != EXPECT_34[p] or len(pm) != EXPECT_34[p]:
            fail(f'{p}: {len(cw)} CatLog wrong, {len(pw)} plain wrong, {len(pm)} plain-only supported values')
        if any(w['verdict'] != 'wrong_scale' for w in cw):
            fail(f'{p}: a CatLog wrong value that is not wrong_scale')
        if any(m['stored_by'] != 'plain' or m['kind'] != 'unmatched' for m in pm):
            fail(f'{p}: a miss that is not an unmatched plain value')
        if any(m['pmid'] == p for m in L['misses']['plain']) or any(r['pmid'] == p for r in L['restated_values_not_counted_as_misses']):
            fail(f'{p}: other unmatched values in this paper')
        used = set()
        for w in cw:
            s, st = w['shown'], w['stored']
            cands = [i for i, m in enumerate(pm) if i not in used
                     and m['shown']['metric'] == s['metric'] and m['shown']['variant'] == s['variant']
                     and m['shown']['pH'] == s['pH'] and m['shown']['temperature_C'] == s['temperature_C']
                     and first_word(m['shown']['substrate']) == first_word(s['substrate'])
                     and abs(m['shown']['value'] / (s['value'] * f) - 1) < 0.005]
            if len(cands) != 1:
                fail(f'{p} {w["claim_id"]}: {len(cands)} plain values pair with it')
            m = pm[cands[0]]
            cell = printed_value(st['raw'], st['raw_unit'], s['metric'])
            if abs(m['shown']['value'] / cell - 1) > 1e-9:
                fail(f'{p} {w["claim_id"]}: the plain value {m["shown"]["value"]} is not the printed cell {cell}')
            used.add(cands[0])
            pairs.append({'pmid': p, 'metric': s['metric'], 'substrate': s['substrate'], 'temperature_C': s['temperature_C'],
                          'printed_cell': f'{st["raw"]} {st["raw_unit"]}', 'catlog_claim': w['claim_id'],
                          'catlog_value': s['value'], 'catlog_verdict': w['verdict'], 'plain_claim': m['claim_id'],
                          'plain_value': m['shown']['value'], 'plain_verdict': 'supported (a miss of CatLog)',
                          'unit': s['unit'], 'plain_over_catlog': round(m['shown']['value'] / s['value'], 4)})
        if len(used) != len(pm):
            fail(f'{p}: {len(pm) - len(used)} plain values left unpaired')
    return pairs


def cross_check_investigation(pairs):
    """The blind page check's task files list each misprint paper's two readings; _key.json says which is the plain's."""
    key_f = INVESTIGATION / '_key.json'
    if not key_f.exists():
        return {'done': False, 'why': f'{key_f} not found'}
    key = json.loads(key_f.read_text())
    out = {'done': True, 'files': {}}
    for p in MISPRINT:
        f = INVESTIGATION / f'{p}.task.json'
        t = json.loads(f.read_text())
        side = [k for k, v in key[p].items() if v == 'plain']
        if len(side) != 1:
            fail(f'{p}: _key.json names no single plain reading')
        listed = sorted((r['metric'], round(float(r['value']), 6), first_word(r['substrate']), r['temperature_C'])
                        for r in t[f'reading_{side[0]}'])
        ours = sorted((q['metric'], round(float(q['plain_value']), 6), first_word(q['substrate']), q['temperature_C'])
                      for q in pairs if q['pmid'] == p)
        if listed != ours:
            fail(f'{p}: the investigation task file lists other plain values than the 34 found here')
        out['files'][p] = {'plain_reading': side[0], 'values': len(listed), 'same_as_found_here': True,
                           'sha256': sha256(f)}
    return out


def cross_check_values(pairs):
    """The eval records' values.json: in each misprint paper, the plain values the matcher paired with no CatLog value
    are exactly the 34, each with CatLog's printed cell, and the paper's other values are paired. Also, for both tests,
    the papers where both sources hold values the matcher paired with nothing (where a cell could have been converted
    differently by the two sides)."""
    out = {}
    for test, f in VALUES.items():
        if not f.exists():
            out[test] = {'done': False, 'why': f'{f} not found'}
            continue
        v = json.loads(f.read_text())
        paired_c = {pr[0]: pr[1] for pr in v['pairs']}
        paired_p = {pr[1]: pr[0] for pr in v['pairs']}
        if not all(pr[0] in {x['id'] for x in v['catlog']} for pr in v['pairs'][:50]):
            fail(f'{f}: pairs are not (CatLog id, plain id)')
        un = {s: collections.defaultdict(list) for s in SOURCES}
        for x in v['plain']:
            if x['id'] not in paired_p:
                un['plain'][x['pmid']].append(x)
        for x in v['catlog']:
            if x['id'] not in paired_c:
                un['catlog'][x['pmid']].append(x)
        both = sorted(set(un['plain']) & set(un['catlog']))
        rec = {'done': True, 'sha256': sha256(f),
               'unpaired_values': {s: sum(map(len, un[s].values())) for s in SOURCES},
               'papers_with_unpaired_values_on_both_sides': {
                   p: {'plain': [(x['metric'], x['value'], x['raw'], x['raw_unit']) for x in un['plain'][p]][:5],
                       'catlog': [(x['metric'], x['value'], x['raw'], x['raw_unit']) for x in un['catlog'][p]][:5],
                       'plain_count': len(un['plain'][p]), 'catlog_count': len(un['catlog'][p])} for p in both}}
        if test == 'locked':
            for p in MISPRINT:
                up = sorted((x['metric'], round(x['value'], 6)) for x in un['plain'][p])
                ours = sorted((q['metric'], round(float(q['plain_value']), 6)) for q in pairs if q['pmid'] == p)
                if up != ours:
                    fail(f'{p}: values.json leaves other plain values unpaired than the 34 found here')
                cells_p = sorted((x['metric'], str(x['raw']).strip(), str(x['raw_unit']).replace('μ', 'µ').strip())
                                 for x in un['plain'][p])
                cells_c = sorted((x['metric'], str(x['raw']).strip(), str(x['raw_unit']).replace('μ', 'µ').strip())
                                 for x in un['catlog'][p])
                pv = [x for x in v['plain'] if x['pmid'] == p]
                rec[p] = {'plain_values': len(pv), 'plain_unpaired': len(un['plain'][p]),
                          'plain_unpaired_by_metric': dict(collections.Counter(x['metric'] for x in un['plain'][p])),
                          'plain_paired_by_metric': dict(collections.Counter(x['metric'] for x in pv if x['id'] in paired_p)),
                          'catlog_unpaired': len(un['catlog'][p]),
                          'same_printed_cells_both_sides': cells_p == cells_c}
                if cells_p != cells_c:
                    fail(f'{p}: the unpaired plain and CatLog values are not the same printed cells')
            # 11382747: the stage-2 page check calls 11 of CatLog's kcat/Km values corrected misprints (the XML header
            # prints mg ml^-1 s^-1); if the plain reading changed them the same way, no way of counting touches them
            p = '11382747'
            plain_by_id = {x['id']: x for x in v['plain']}
            cm = [x for x in v['catlog'] if x['pmid'] == p and str(x['raw_unit']).strip().startswith('mg ml')]
            same = [x for x in cm if x['id'] in paired_c
                    and abs(plain_by_id[paired_c[x['id']]]['value'] / x['value'] - 1) < 1e-9]
            rec['paper_11382747'] = {
                'catlog_values_printed_mg_ml_s': len(cm), 'paired_with_an_equal_plain_value': len(same),
                'plain_raw_units': sorted({plain_by_id[paired_c[x['id']]]['raw_unit'] for x in same})}
            if not cm or len(same) != len(cm):
                fail(f'{p}: {len(same)} of {len(cm)} CatLog mg ml^-1 s^-1 cells paired with an equal plain value')
        out[test] = rec
    return out


# ---------- per-paper rows, ways and statistics ----------

def paper_rows(d, test, way):
    rows = []
    for p, v in d['per_paper'].items():
        pw, cw = v['plain']['wrong'], v['catlog']['wrong']
        if test == 'locked' and p in MISPRINT and way != 'as_printed':
            cw -= EXPECT_34[p]                 # CatLog's unit changes counted right
            if way == 'own_numbers_both':
                pw += EXPECT_34[p]             # the plain reading's as-printed values of the same cells counted wrong
        rows.append({'test': test, 'pmid': p, 'pv': v['plain']['values'], 'pw': pw,
                     'cv': v['catlog']['values'], 'cw': cw})
    return rows


def summary(rows):
    out = {'papers': len(rows)}
    for s, e, n in (('plain', 'pw', 'pv'), ('catlog', 'cw', 'cv')):
        V, W = sum(r[n] for r in rows), sum(r[e] for r in rows)
        out[s] = {'values': V, 'wrong': W, 'per_1000': round(1000 * W / V, 3),
                  'papers_with_a_wrong_value': sum(r[e] > 0 for r in rows),
                  'papers_per_100': round(100 * sum(r[e] > 0 for r in rows) / len(rows), 2),
                  'papers': sorted((r['pmid'] for r in rows if r[e] > 0), key=lambda p: (not p.isdigit(), p.zfill(12)))}
    return out


def sign(rows):
    a = sum(r['pw'] > 0 and r['cw'] == 0 for r in rows)
    b = sum(r['cw'] > 0 and r['pw'] == 0 for r in rows)
    both = sum(r['pw'] > 0 and r['cw'] > 0 for r in rows)
    p = float(binomtest(a, a + b, 0.5, alternative='two-sided').pvalue) if a + b else None
    return {'plain_only': a, 'catlog_only': b, 'both': both, 'discordant': a + b, 'p': p,
            'more_papers_with_a_wrong_value': 'plain' if a > b else 'catlog' if b > a else 'neither'}


def leave_one_out(rows):
    base = sign(rows)
    drops = []
    for i, r in enumerate(rows):
        if r['pw'] == 0 and r['cw'] == 0:
            continue
        s = sign(rows[:i] + rows[i + 1:])
        erred = 'both' if r['pw'] and r['cw'] else 'plain' if r['pw'] else 'catlog'
        drops.append({'drop': r['pmid'], 'test': r['test'], 'erred': erred, 'plain_only': s['plain_only'],
                      'catlog_only': s['catlog_only'], 'p': s['p'], 'p_over_0.05': s['p'] is None or s['p'] > 0.05,
                      'takes_p_over_0.05': base['p'] is not None and base['p'] <= 0.05 and (s['p'] is None or s['p'] > 0.05)})
    ps = [x['p'] for x in drops if x['p'] is not None]
    return {'base': base, 'drops': drops, 'largest_p': max(ps) if ps else None, 'smallest_p': min(ps) if ps else None,
            'drops_taking_p_over_0.05': [x['drop'] for x in drops if x['takes_p_over_0.05']],
            'drops_with_p_over_0.05': [x['drop'] for x in drops if x['p_over_0.05']]}


def boot(rows, B=B, seed=SEED):
    """score_rand.boot, the rate part: plain minus CatLog wrong per 1,000 stored values, the same resampled papers."""
    a = {k: np.array([r[k] for r in rows], dtype=float) for k in ('pv', 'pw', 'cv', 'cw')}
    n = len(rows)
    idx = np.random.default_rng(seed).integers(0, n, size=(B, n))
    rate = {}
    for s, e, v in (('plain', a['pw'], a['pv']), ('catlog', a['cw'], a['cv'])):
        E, N = e[idx].sum(1), v[idx].sum(1)
        rate[s] = np.where(N > 0, E / np.where(N > 0, N, 1), 0.0) * 1000
    d = rate['plain'] - rate['catlog']
    lo, hi = float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
    est = 1000 * (a['pw'].sum() / a['pv'].sum() - a['cw'].sum() / a['cv'].sum())
    return {'papers': n, 'plain_per_1000': float(1000 * a['pw'].sum() / a['pv'].sum()),
            'catlog_per_1000': float(1000 * a['cw'].sum() / a['cv'].sum()), 'difference': float(est),
            'lo': lo, 'hi': hi, 'includes_zero': bool(lo <= 0 <= hi), 'share_plain_higher': float((d > 0).mean()),
            'share_zero_or_below': float((d <= 0).mean()), 'B': B, 'seed': seed}


def boot_leave_one_out(rows):
    out = []
    for i, r in enumerate(rows):
        if r['pw'] == 0 and r['cw'] == 0:
            continue
        b = boot(rows[:i] + rows[i + 1:])
        out.append({'drop': r['pmid'], 'test': r['test'], 'erred': 'both' if r['pw'] and r['cw'] else 'plain' if r['pw'] else 'catlog',
                    'difference': b['difference'], 'lo': b['lo'], 'hi': b['hi'], 'includes_zero': b['includes_zero'],
                    'share_plain_higher': b['share_plain_higher']})
    return {'drops': out, 'drops_where_it_includes_zero': [x['drop'] for x in out if x['includes_zero']]}


# ---------- kinds ----------

def decided(w):
    j = w.get('judges') or {}
    k1, k2 = klass((j.get('j1') or {}).get('verdict')), klass((j.get('j2') or {}).get('verdict'))
    if k1 == 'error' and k2 == 'error':
        return '2-0'
    if j.get('j3'):
        return f'2-1 (third judge; j1 {k1}, j2 {k2})'
    return f'other (j1 {k1}, j2 {k2})'


def subkind(w):
    j = w.get('judges') or {}
    text = ' '.join(str((j.get(k) or {}).get('reason') or '') for k in ('j1', 'j2', 'j3'))
    hits = [lab for lab, verdict, rx in SUBKINDS if verdict == w['verdict'] and rx.search(text)]
    return hits[0] if len(hits) == 1 else 'unclassified' if not hits else 'ambiguous: ' + ' | '.join(hits)


def kinds(results, tests, extra_plain=None, labels=True):
    """Wrong values by verdict and by paper, per source. results: {test: results.json}; extra_plain: the 34 pairs;
    labels: add the descriptive sub-kinds (SUBKINDS for the plain reading, CATLOG_KINDS for CatLog: final judgings only)."""
    out = {}
    for s in SOURCES:
        by_verdict, by_paper, by_sub = collections.Counter(), {}, collections.Counter()
        papers_of = collections.defaultdict(set)
        sub_papers = collections.defaultdict(set)
        for t in tests:
            d = results[t]
            for w in d['wrong']:
                if w['source'] != s:
                    continue
                by_verdict[w['verdict']] += 1
                papers_of[w['verdict']].add(w['pmid'])
                k = (t, w['pmid'])
                pp = d['per_paper'][w['pmid']]
                rec = by_paper.setdefault(k, {'test': t, 'pmid': w['pmid'], 'wrong': 0, 'verdicts': collections.Counter(),
                                              'metrics': collections.Counter(), 'decided': collections.Counter(),
                                              'subkind': collections.Counter(), 'stored_values': pp[s]['values'],
                                              'other_source_wrong_in_paper': pp['catlog' if s == 'plain' else 'plain']['wrong']})
                rec['wrong'] += 1
                rec['verdicts'][w['verdict']] += 1
                rec['metrics'][w['shown']['metric']] += 1
                rec['decided'][decided(w)] += 1
                if labels and s == 'plain':
                    sk = subkind(w)
                    rec['subkind'][sk] += 1
                    by_sub[sk] += 1
                    sub_papers[sk].add(w['pmid'])
                elif labels and w['pmid'] in CATLOG_KINDS:
                    rec['subkind'][CATLOG_KINDS[w['pmid']]] += 1
        rows = []
        for k, rec in sorted(by_paper.items(), key=lambda kv: (-kv[1]['wrong'], kv[0])):
            rows.append({**rec, **{x: dict(rec[x]) for x in ('verdicts', 'metrics', 'decided', 'subkind')}})
        out[s] = {'values': sum(by_verdict.values()), 'papers': len(by_paper),
                  'by_verdict': {v: {'values': n, 'papers': len(papers_of[v])} for v, n in by_verdict.most_common()},
                  'by_paper': rows}
        if labels and s == 'plain':
            out[s]['by_subkind'] = {k: {'values': n, 'papers': len(sub_papers[k]), 'which': sorted(sub_papers[k])}
                                    for k, n in by_sub.most_common()}
            if any(k == 'unclassified' or k.startswith('ambiguous') for k in by_sub):
                out[s]['subkind_warning'] = 'some values got no single sub-kind: see by_paper'
    if extra_plain is not None:
        c = collections.Counter((q['pmid'], q['metric']) for q in extra_plain)
        out['plain_as_printed_34_way_iii'] = {
            'values': len(extra_plain), 'papers': len({q['pmid'] for q in extra_plain}),
            'by_paper': {p: {m: n for (pp, m), n in c.items() if pp == p} for p in MISPRINT},
            'verdict': 'supported (as printed), in misses["catlog"]; counted wrong in way (iii) only'}
    return out


# ---------- main ----------

def main():
    R = {}
    inputs = {}
    for name, f in FILES.items():
        if not f.exists():
            fail(f'{f} not found')
        R[name] = json.loads(f.read_text())
        inputs[name] = {'path': str(f.relative_to(EVID)), 'sha256': sha256(f), 'time': R[name].get('time')}
    checks = {name: check_file(name, R[name]) for name in FILES}
    if set(R['random']['per_paper']) != set(R['random_first']['per_paper']) or \
            any(R['random']['per_paper'][p][s]['values'] != R['random_first']['per_paper'][p][s]['values']
                for p in R['random']['per_paper'] for s in SOURCES):
        fail('the random test\'s two judgings do not hold the same papers and stored values')
    if set(R['random']['per_paper']) & set(R['locked']['per_paper']):
        fail('a paper is in both tests')
    checks['random_first_same_papers_and_values_as_final'] = True
    checks['no_paper_in_both_tests'] = True

    pairs = identify_as_printed(R['locked'])
    if len(pairs) != sum(EXPECT_34.values()):
        fail(f'{len(pairs)} pairs, expected 34')
    as_printed = {'rule': ('misses["catlog"] of the locked test (supported values only the plain reading stored) in '
                           '9973343 and 10447675, each paired one to one with a CatLog wrong_scale value of the same paper: '
                           'same metric, variant, pH, temperature and substrate (first word); plain value = CatLog value '
                           'x 1000 (9973343) or x 60 (10447675) within 0.5%; plain value = the printed cell of CatLog\'s own '
                           'record (stored.raw at stored.raw_unit) in catalogue units. None left over on either side.'),
                  'count': {p: sum(q['pmid'] == p for q in pairs) for p in MISPRINT},
                  'by_metric': {p: dict(collections.Counter(q['metric'] for q in pairs if q['pmid'] == p)) for p in MISPRINT},
                  'pairs': pairs,
                  'cross_check_investigation_task_files': cross_check_investigation(pairs),
                  'cross_check_eval_records_values_json': cross_check_values(pairs)}

    # rows per way and test; pooled = random (file order) then locked (file order)
    tests = {'random': 'random', 'locked': 'locked'}
    rows = {w: {t: paper_rows(R[t], t, w) for t in tests} for w in WAYS}
    for w in WAYS:
        rows[w]['pooled'] = rows[w]['random'] + rows[w]['locked']
    rows_first = {w: {'random': paper_rows(R['random_first'], 'random', w), 'locked': rows[w]['locked']} for w in WAYS}
    for w in WAYS:
        rows_first[w]['pooled'] = rows_first[w]['random'] + rows_first[w]['locked']

    papers = {w: {t: summary(rows[w][t]) for t in ('random', 'locked', 'pooled')} for w in WAYS}
    pooled_printed = papers['as_printed']['pooled']
    for s in SOURCES:
        got = (pooled_printed[s]['values'], pooled_printed[s]['wrong'], pooled_printed[s]['papers_with_a_wrong_value'])
        if got != EXPECT_POOLED[s]:
            fail(f'pooled as printed {s}: {got}, expected {EXPECT_POOLED[s]}')
    checks['pooled_as_printed'] = {s: EXPECT_POOLED[s] for s in SOURCES}
    checks['pooled_as_printed_matches_57_40_values_9_3_papers'] = True

    sign_tests = {w: {t: sign(rows[w][t]) for t in ('random', 'locked', 'pooled')} for w in WAYS}
    loo = {w: {t: leave_one_out(rows[w][t]) for t in ('random', 'locked', 'pooled')} for w in WAYS}
    first = {'papers_with_a_wrong_value': {w: {t: summary(rows_first[w][t]) for t in ('random', 'pooled')} for w in WAYS},
             'sign_test': {w: {t: sign(rows_first[w][t]) for t in ('random', 'pooled')} for w in WAYS},
             'leave_one_out': {w: {t: leave_one_out(rows_first[w][t]) for t in ('random', 'pooled')} for w in WAYS}}

    boots = {}
    for w in WAYS:
        boots[w] = {'pooled': boot(rows[w]['pooled']),
                    f'pooled_without_{CLUSTER}': boot([r for r in rows[w]['pooled'] if r['pmid'] != CLUSTER]),
                    'random': boot(rows[w]['random']),
                    f'random_without_{CLUSTER}': boot([r for r in rows[w]['random'] if r['pmid'] != CLUSTER]),
                    'locked': boot(rows[w]['locked']),
                    'pooled_leave_one_out': boot_leave_one_out(rows[w]['pooled'])}

    # the bootstrap against the numbers reported before
    L = R['locked']['plain_minus_catlog']
    got = boots['as_printed']['locked']
    if abs(got['lo'] - L['per_1000_lo']) > 1e-9 or abs(got['hi'] - L['per_1000_hi']) > 1e-9 or \
            abs(got['share_plain_higher'] - L['share_plain_higher']) > 1e-12:
        fail(f'locked as printed: {got["lo"]}, {got["hi"]} against the report {L["per_1000_lo"]}, {L["per_1000_hi"]}')
    rep = {'locked_as_printed_equals_results_json': [L['per_1000_lo'], L['per_1000_hi'], L['share_plain_higher']]}
    g = boots['unit_changes_right']['locked']
    if [round(g['lo'], 1), round(g['hi'], 1), round(g['share_plain_higher'], 3)] != [1.2, 23.3, 0.983]:
        fail(f'locked, 34 right: {g["lo"]}, {g["hi"]}, {g["share_plain_higher"]}; README gives +1.2 to +23.3, 98.3%')
    rep['locked_34_right_equals_README_rounded'] = [1.2, 23.3, 0.983]
    g = boots['unit_changes_right']['pooled']
    if [round(g['lo'], 1), round(g['hi'], 1)] != [0.7, 20.5]:
        fail(f'pooled, 34 right: {g["lo"]}, {g["hi"]}; FOR_WRITING gives +0.7 to +20.5')
    rep['pooled_34_right_equals_FOR_WRITING_rounded'] = [0.7, 20.5]
    rf = R['random']['plain_minus_catlog']
    rep['random_against_its_report'] = {
        'here': [boots['as_printed']['random']['lo'], boots['as_printed']['random']['hi']],
        'report': [rf['per_1000_lo'], rf['per_1000_hi']],
        'why_they_differ': 'the report leaves 20 plain and 21 CatLog cannot-decide values out of the denominators; '
                           'per_paper counts them'}
    if POWER.exists():
        pc = json.loads(POWER.read_text())['check']
        cmp_ = {'random': ('as_printed', 'random'), 'pooled_registered': ('as_printed', 'pooled'),
                'pooled_corrected': ('unit_changes_right', 'pooled'), 'pooled_newrule': ('own_numbers_both', 'pooled'),
                'locked_corrected': ('unit_changes_right', 'locked')}
        rep['power_results_json'] = {}
        for k, (w, t) in cmp_.items():
            here = [boots[w][t]['lo'], boots[w][t]['hi']]
            there = pc[k]['rebuilt']
            same = max(abs(a - b) for a, b in zip(here, there)) < 1e-9
            rep['power_results_json'][k] = {'here': here, 'power_py': there, 'same': same}
            if not same:
                fail(f'{k}: {here} here, {there} in power_results.json')
    else:
        rep['power_results_json'] = {'done': False, 'why': f'{POWER} not found'}
    checks['bootstrap_against_earlier_numbers'] = rep

    out = {'written': time.strftime('%Y-%m-%d %H:%M:%S %z'), 'script': 'stats.py', 'numpy': np.__version__,
           'scipy': scipy.__version__, 'inputs': inputs,
           'post_hoc': 'the pooling and the three ways were chosen after both tests\' results were in',
           'ways': WAY_NAMES,
           'denominators': 'every stored value (per_paper "values"); the tests\' own rates leave cannot-decide values out '
                           '(random test plain 20, CatLog 21; locked none)',
           'bootstrap_settings': {'B': B, 'seed': SEED, 'rng': 'numpy.random.default_rng(seed).integers(0, papers, (B, papers))',
                                  'interval': 'np.percentile 2.5 and 97.5 of plain minus CatLog per 1,000',
                                  'pooled_order': 'random test papers in file order, then locked test papers in file order'},
           'checks': checks,
           'as_printed_34': as_printed,
           'papers_with_a_wrong_value': papers,
           'sign_test': sign_tests,
           'leave_one_out_sign_test': loo,
           'first_judging': first,
           'bootstrap': boots,
           'kinds_final': kinds({'random': R['random'], 'locked': R['locked']}, ('random', 'locked'), pairs),
           'kinds_random_first_judging': kinds({'random': R['random_first']}, ('random',), labels=False)}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
