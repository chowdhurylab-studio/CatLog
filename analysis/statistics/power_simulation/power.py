#!/usr/bin/env python3
"""Power simulation for the third test (the second random test), written 12 November 2026, before its registration.

  python3 power.py            checks, then the full simulation -> power_results.json, power_table.md (next to this file)
  python3 power.py --check    only the checks: the earlier tests' reported numbers, and a case with a known answer
  python3 power.py --sims 200 --out /some/scratch    a quick look that leaves the saved results alone
  options: --B (resamples inside each simulated test), --jobs (processes; the results do not depend on it)

Input: the per-paper counts of the two earlier tests (key per_paper of each results.json: values and wrong values per
source). Nothing else is read: no paper text, no catalogue row, no judge file, no held-out paper's file.

One simulated test: N papers drawn with replacement from the pool. For it, the registered analysis: wrong values per
1,000 stored values, plain minus CatLog, with a paired paper bootstrap 95% percentile interval (the kit's
score_rand.boot: the same resampled papers for both sides, np.percentile at 2.5 and 97.5). B is 2,000 inside the
simulation; the test itself uses 10,000. 2,000 simulated tests per size.

Views of the earlier results (how the 230 papers' wrong values are counted):
  corrected     the 34 values of 9973343 and 10447675 (locked test) count as right for CatLog: plain 57 wrong in 9
                papers, CatLog 6 in 1. Post hoc; the count the design brief starts from.
  registered    as the two tests reported: plain 57 in 9 papers, CatLog 40 in 3.
  newrule       as corrected, and the plain read's 34 as-printed values in those two papers count as wrong, which is how
                the design brief's primary view would count a misprint copied as printed: plain 91 in 11, CatLog 6 in 1.
  catlog_none   as corrected, and CatLog's 6 values of 7334001 (random test, judged wrong 2 to 1) count as right too:
                CatLog has no wrong value. Only to show how much hangs on that one paper.

The plain read's rate:
  seen          as counted.
  half_values   each wrong plain value of a drawn paper is kept with probability 1/2 (nearly as many papers with a wrong
                value, about half as many wrong values in each).
  half_papers   each drawn paper with wrong plain values keeps them all with probability 1/2, else has none (half as
                many such papers, each as bad as seen).
Both halve the plain rate. They are drawn again for every simulated test.

null: the corrected counts, with the two sides of each drawn paper swapped with probability 1/2. The two sides then
have the same error distribution, so this is the share of tests in which the rule claims a difference that is not there.

Pools: pooled (both tests, 230 papers), random_only (147), locked_only (83), and for sizes 300 and 400 the pooled papers
without each one of the 10 papers that hold a wrong value in the corrected view (leave_one_out).

Decision rules, per simulated test:
  above         the interval's lower limit is above zero (the brief's rule; plain higher)
  below         the interval's upper limit is below zero (CatLog higher)
  above_5       above, and at least 5 papers have a wrong value on one side only (the kit prints the interval only then:
                score_rand.MIN_WRONG_PAPERS)
  above_sign    above, and the exact two-sided sign test on those papers gives p < 0.05 (the fix the earlier plan review
                proposed, locked_test_20261109/review/stage2/findings.json, finding 30)

Denominators are each paper's stored values as per_paper gives them. The tests' own rates leave cannot-decide values
out of the denominator; per_paper does not hold them (41 values of the random test, none of the locked test). The
check step shows what that changes: under 0.2 per 1,000 at either end of the random test's interval.
"""
import argparse, collections, json, math, os, sys, time
from pathlib import Path

for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')  # the products here are small: BLAS threads only get in each other's way
import numpy as np  # noqa: E402

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
EVID = HERE.parents[1]  # paper/evidence
FILES = {'random': EVID / 'random_papers_20261104' / 'full_record' / 'results.json',
         'locked': EVID / 'locked_test_20261109' / 'result' / 'results.json'}
# what each file must hold, so that a changed file stops the run: papers, plain values and wrong, CatLog values and wrong
EXPECT = {'random': (147, 4530, 42, 4390, 6), 'locked': (83, 1473, 15, 1400, 34)}
MISPRINT = {'9973343': 29, '10447675': 5}  # locked test: CatLog's unit changes, and the plain read's as-printed values
DISPUTED = {'7334001': 6}                  # random test: CatLog's 6 Km values judged wrong scale 2 to 1
SIZES = (150, 200, 250, 300, 400, 500)     # the sizes asked for
MORE = (350, 450, 600, 800, 1000)          # to place the 80% and 90% points
LOO_SIZES = (300, 400)
SIMS, B_SIM = 2000, 2000
SEED = 20261112        # this simulation's seed
SEED_BOOT = 20261031   # the kit's bootstrap seed (common_w1.SEED_BOOT), used only in the check step
VIEWS = ('corrected', 'registered', 'newrule')
RATES = ('seen', 'half_values', 'half_papers')
MAIN_SCEN = [f'{v}/{r}' for v in VIEWS for r in RATES] + ['catlog_none/seen', 'null']
SIDE_SCEN = ['corrected/seen', 'corrected/half_values', 'corrected/half_papers', 'registered/seen', 'newrule/seen']
SHARES = ('above', 'below', 'above_5', 'above_sign', 'sign_alone', 'fewer_than_5_one_sided_papers', 'no_wrong_plain_paper')


def load():
    """The pooled papers, the random test's first: one row per paper."""
    rows = []
    for test, f in FILES.items():
        d = json.loads(f.read_text())
        pp = d['per_paper']
        got = (len(pp), sum(v['plain']['values'] for v in pp.values()), sum(v['plain']['wrong'] for v in pp.values()),
               sum(v['catlog']['values'] for v in pp.values()), sum(v['catlog']['wrong'] for v in pp.values()))
        if got != EXPECT[test]:
            sys.exit(f'{f}: papers and counts {got}, expected {EXPECT[test]}')
        ps, cs = d['per_source']['plain'], d['per_source']['catlog']
        if (d['papers_used'], ps['values'], ps['wrong'], cs['values'], cs['wrong']) != got:
            sys.exit(f'{f}: per_paper does not add up to per_source')
        for p, v in pp.items():  # the order of the file is the order the kit's bootstrap used
            rows.append({'test': test, 'pmid': p, 'n_plain': v['plain']['values'], 'e_plain': v['plain']['wrong'],
                         'n_catlog': v['catlog']['values'], 'e_catlog': v['catlog']['wrong']})
        if test == 'locked':  # the newrule view's 34: supported values of the plain read at the scale CatLog changed
            for p, k in MISPRINT.items():
                as_printed = [m for m in d['misses']['catlog'] if m['pmid'] == p and m['stored_by'] == 'plain']
                changed = [w for w in d['wrong'] if w['pmid'] == p and w['source'] == 'catlog' and w['verdict'] == 'wrong_scale']
                if len(as_printed) != k or len(changed) != k:
                    sys.exit(f'{p}: {len(as_printed)} as-printed plain values and {len(changed)} changed CatLog values, expected {k}')
    for special, test in ((MISPRINT, 'locked'), (DISPUTED, 'random')):
        for p, k in special.items():
            r = [x for x in rows if x['pmid'] == p]
            if len(r) != 1 or r[0]['test'] != test or r[0]['e_catlog'] != k or r[0]['e_plain'] != 0:
                sys.exit(f'{p}: not the paper the {test} test reported')
    if len({x['pmid'] for x in rows}) != len(rows):
        sys.exit('a paper is in both tests')
    return rows


def arrays(rows):
    """Per-paper arrays for every view."""
    a = {k: np.array([r[k] for r in rows], dtype=np.int64) for k in ('n_plain', 'e_plain', 'n_catlog', 'e_catlog')}
    mis = np.array([MISPRINT.get(r['pmid'], 0) for r in rows], dtype=np.int64)
    dis = np.array([DISPUTED.get(r['pmid'], 0) for r in rows], dtype=np.int64)
    return {'n_plain': a['n_plain'], 'n_catlog': a['n_catlog'],
            'e_plain': a['e_plain'],                 # every view but newrule
            'e_plain_extra': mis,                    # newrule: the plain read's as-printed values in the misprint papers
            'e_catlog_registered': a['e_catlog'],
            'e_catlog_corrected': a['e_catlog'] - mis,
            'e_catlog_none': a['e_catlog'] - mis - dis,
            'test': np.array([r['test'] for r in rows]), 'pmid': np.array([r['pmid'] for r in rows])}


def kit_boot(e_p, n_p, e_c, n_c, B, seed):
    """score_rand.boot, the rate part, line for line: the check step compares it with the reported intervals."""
    papers = len(n_p)
    idx = np.random.default_rng(seed).integers(0, papers, size=(B, papers))
    rate = []
    for e, n in ((e_p, n_p), (e_c, n_c)):
        E, N = e[idx].sum(1), n[idx].sum(1)
        rate.append(np.where(N > 0, E / np.where(N > 0, N, 1), 0.0) * 1000)
    d = rate[0] - rate[1]
    return {'plain': [float(np.percentile(rate[0], 2.5)), float(np.percentile(rate[0], 97.5))],
            'catlog': [float(np.percentile(rate[1], 2.5)), float(np.percentile(rate[1], 97.5))],
            'diff': [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], 'share_plain_higher': float((d > 0).mean())}


def counts_boot(M, B, rng, offs):
    """The same resampling done with counts: B resamples of the N rows of M (N x k), the column sums of each (B x k)."""
    N = M.shape[0]
    idx = rng.integers(0, N, size=(B, N))
    idx += offs
    C = np.bincount(idx.ravel(), minlength=B * N).reshape(B, N).astype(np.float64)
    return C @ M


def rate_diff(S):
    """Columns in fours (plain wrong, plain values, CatLog wrong, CatLog values): plain minus CatLog per 1,000."""
    EP, NP, EC, NC = S[:, 0::4], S[:, 1::4], S[:, 2::4], S[:, 3::4]
    return 1000 * (np.where(NP > 0, EP / np.where(NP > 0, NP, 1), 0.0) - np.where(NC > 0, EC / np.where(NC > 0, NC, 1), 0.0))


def sign_p(a, b):
    """Exact two-sided sign test: a papers wrong on one side only, b on the other only."""
    n, k = a + b, min(a, b)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def simulate(A, keep, N, sims, B, seed, scen):
    """sims simulated tests of N papers drawn from the papers `keep` (indexes into A); scen: the scenarios to score."""
    rng = np.random.default_rng(np.random.SeedSequence(seed))
    offs = (np.arange(B, dtype=np.int64) * N)[:, None]
    tally = {s: collections.Counter() for s in scen}
    sums = {s: collections.defaultdict(float) for s in scen}
    for _ in range(sims):
        draw = keep[rng.integers(0, len(keep), N)]
        n_p, n_c = A['n_plain'][draw], A['n_catlog'][draw]
        e_p, extra = A['e_plain'][draw], A['e_plain_extra'][draw]
        e_c = {'registered': A['e_catlog_registered'][draw], 'corrected': A['e_catlog_corrected'][draw],
               'catlog_none': A['e_catlog_none'][draw]}
        e_c['newrule'] = e_c['corrected']
        # drawn for every simulated test whether used or not, so that every scenario sees the same papers and resamples
        kept_values, kept_extra = rng.binomial(e_p, 0.5), rng.binomial(extra, 0.5)
        kept_paper = rng.random(N) < 0.5
        swap = rng.random(N) < 0.5
        plain = {('seen', 0): e_p, ('half_values', 0): kept_values, ('half_papers', 0): e_p * kept_paper,
                 ('seen', 1): e_p + extra, ('half_values', 1): kept_values + kept_extra, ('half_papers', 1): (e_p + extra) * kept_paper}
        cols, parts = [], {}
        for s in scen:
            if s == 'null':
                c = e_c['corrected']
                parts[s] = (np.where(swap, c, e_p), np.where(swap, n_c, n_p), np.where(swap, e_p, c), np.where(swap, n_p, n_c))
            else:
                view, rate = s.split('/')
                parts[s] = (plain[(rate, int(view == 'newrule'))], n_p, e_c[view], n_c)
            cols.extend(parts[s])
        M = np.column_stack(cols).astype(np.float64)
        D = rate_diff(counts_boot(M, B, rng, offs))
        lo, hi = np.percentile(D, [2.5, 97.5], axis=0)
        point = rate_diff(M.sum(0)[None, :])[0]
        for j, s in enumerate(scen):
            ep, _, ec, _ = parts[s]
            a, b = int(((ep > 0) & (ec == 0)).sum()), int(((ec > 0) & (ep == 0)).sum())
            above, below = bool(lo[j] > 0), bool(hi[j] < 0)
            sign = a > b and sign_p(a, b) < 0.05
            t = tally[s]
            t['above'] += above
            t['below'] += below
            t['above_5'] += above and a + b >= 5
            t['above_sign'] += above and sign
            t['sign_alone'] += sign
            t['fewer_than_5_one_sided_papers'] += a + b < 5
            t['no_wrong_plain_paper'] += int((ep > 0).sum()) == 0
            for k, x in (('difference', point[j]), ('lower', lo[j]), ('upper', hi[j]), ('papers_plain_wrong', (ep > 0).sum()),
                         ('papers_catlog_wrong', (ec > 0).sum()), ('plain_wrong', ep.sum()), ('catlog_wrong', ec.sum())):
                sums[s][k] += float(x)
    return {s: {**{k: tally[s][k] / sims for k in SHARES}, 'excludes_zero': (tally[s]['above'] + tally[s]['below']) / sims,
                'mean': {k: round(x / sims, 3) for k, x in sums[s].items()}} for s in scen}


def task(args):
    key, A, keep, N, sims, B, seed, scen = args
    return key, simulate(A, keep, N, sims, B, seed, scen)


def known_case(sims=1000, B=2000):
    """A pool with a known answer: 100 papers of 20 values a side, 5 of them with 3 wrong plain values, CatLog none.
    With CatLog at zero the lower limit is above zero exactly when fewer than 2.5% of the resamples hold no paper with a
    wrong value. For a test of 100 papers that is 4 or more such papers drawn ((1 - 4/100)^100 = 1.7%, (1 - 3/100)^100
    = 4.8%), so the share must be P(Binomial(100, 0.05) >= 4)."""
    n = np.full(100, 20, dtype=np.int64)
    e = np.zeros(100, dtype=np.int64)
    e[:5] = 3
    zero = np.zeros(100, dtype=np.int64)
    A = {'n_plain': n, 'n_catlog': n, 'e_plain': e, 'e_plain_extra': zero, 'e_catlog_registered': zero,
         'e_catlog_corrected': zero, 'e_catlog_none': zero}
    got = simulate(A, np.arange(100), 100, sims, B, [SEED, 99], ['corrected/seen'])['corrected/seen']['above']
    want = 1 - sum(math.comb(100, k) * 0.05 ** k * 0.95 ** (100 - k) for k in range(4))
    return {'simulated': got, 'exact': round(want, 4), 'simulated_tests': sims, 'passed': bool(abs(got - want) < 0.05)}


def check(rows, A):
    """This file's bootstrap against the numbers the tests reported, and the simulation against a known answer."""
    out, ok = {}, True
    rep = {t: json.loads(f.read_text()) for t, f in FILES.items()}
    for t in FILES:
        m = A['test'] == t
        f = lambda k: A[k][m].astype(float)  # noqa: E731
        got = kit_boot(f('e_plain'), f('n_plain'), f('e_catlog_registered'), f('n_catlog'), 10000, SEED_BOOT)
        want = rep[t]['plain_minus_catlog']
        gap = max(abs(got['diff'][0] - want['per_1000_lo']), abs(got['diff'][1] - want['per_1000_hi']))
        out[t] = {'rebuilt': got['diff'], 'reported': [want['per_1000_lo'], want['per_1000_hi']], 'largest_gap': gap,
                  'share_plain_higher': [got['share_plain_higher'], want['share_plain_higher']]}
        # the locked test has no cannot-decide value: exact. The random test has 41: close.
        ok &= gap < (1e-9 if t == 'locked' else 0.2)
    # the random test with the plain read's 20 cannot-decide values taken out of 33082260 (a judge session the filter
    # stopped): the plain side's own interval is then exact, which shows the counts and the code are the kit's
    m = A['test'] == 'random'
    n_p = A['n_plain'][m].astype(float)
    n_p[list(A['pmid'][m]).index('33082260')] -= rep['random']['per_source']['plain']['cannot_decide']
    got = kit_boot(A['e_plain'][m].astype(float), n_p, A['e_catlog_registered'][m].astype(float),
                   A['n_catlog'][m].astype(float), 10000, SEED_BOOT)
    want = rep['random']['per_source']['plain']['bootstrap']
    gap = max(abs(got['plain'][0] - want['per_1000_lo']), abs(got['plain'][1] - want['per_1000_hi']))
    out['random_plain_side_without_cannot_decide'] = {'rebuilt': got['plain'], 'reported': [want['per_1000_lo'], want['per_1000_hi']],
                                                      'largest_gap': gap}
    ok &= gap < 1e-9
    # the locked test with the 34 counted as right: result/README.md gives +1.2 to +23.3, plain higher in 98.3%
    m = A['test'] == 'locked'
    got = kit_boot(A['e_plain'][m].astype(float), A['n_plain'][m].astype(float), A['e_catlog_corrected'][m].astype(float),
                   A['n_catlog'][m].astype(float), 10000, SEED_BOOT)
    out['locked_corrected'] = {'rebuilt': got['diff'], 'reported_rounded': [1.2, 23.3],
                               'share_plain_higher': [got['share_plain_higher'], 0.983]}
    ok &= [round(x, 1) for x in got['diff']] == [1.2, 23.3] and round(got['share_plain_higher'], 3) == 0.983
    # both tests pooled, corrected: FOR_WRITING.md gives +0.7 to +20.5
    f = lambda k: A[k].astype(float)  # noqa: E731
    got = kit_boot(f('e_plain'), f('n_plain'), f('e_catlog_corrected'), f('n_catlog'), 10000, SEED_BOOT)
    out['pooled_corrected'] = {'rebuilt': got['diff'], 'reported_rounded': [0.7, 20.5], 'share_plain_higher': got['share_plain_higher']}
    ok &= [round(x, 1) for x in got['diff']] == [0.7, 20.5]
    got = kit_boot(f('e_plain'), f('n_plain'), f('e_catlog_registered'), f('n_catlog'), 10000, SEED_BOOT)
    out['pooled_registered'] = {'rebuilt': got['diff'], 'share_plain_higher': got['share_plain_higher']}
    got = kit_boot(f('e_plain') + f('e_plain_extra'), f('n_plain'), f('e_catlog_corrected'), f('n_catlog'), 10000, SEED_BOOT)
    out['pooled_newrule'] = {'rebuilt': got['diff'], 'share_plain_higher': got['share_plain_higher']}
    # the counting form of the bootstrap gives the indexing form's sums
    M = np.column_stack([f('e_plain'), f('n_plain'), f('e_catlog_registered'), f('n_catlog')])
    N, Bc = M.shape[0], 500
    S = counts_boot(M, Bc, np.random.default_rng(1), (np.arange(Bc, dtype=np.int64) * N)[:, None])
    same = bool(np.array_equal(S, M[np.random.default_rng(1).integers(0, N, size=(Bc, N))].sum(1)))
    out['counting_form_equals_indexing_form'] = same
    ok &= same
    ok &= abs(sign_p(6, 0) - 0.03125) < 1e-12 and abs(sign_p(5, 0) - 0.0625) < 1e-12 and abs(sign_p(8, 1) - 20 / 512) < 1e-12
    out['known_case'] = known_case()
    ok &= out['known_case']['passed']
    out['passed'] = bool(ok)
    return out


def pooled_counts(A):
    """What the pool holds under each view."""
    out = {}
    for v in VIEWS + ('catlog_none',):
        ep = A['e_plain'] + (A['e_plain_extra'] if v == 'newrule' else 0)
        ec = A['e_catlog_' + {'newrule': 'corrected', 'catlog_none': 'none'}.get(v, v)]
        out[v] = {'papers': int(len(ep)),
                  'plain': {'values': int(A['n_plain'].sum()), 'wrong': int(ep.sum()), 'papers_with_wrong': int((ep > 0).sum()),
                            'per_1000': round(1000 * ep.sum() / A['n_plain'].sum(), 2)},
                  'catlog': {'values': int(A['n_catlog'].sum()), 'wrong': int(ec.sum()), 'papers_with_wrong': int((ec > 0).sum()),
                             'per_1000': round(1000 * ec.sum() / A['n_catlog'].sum(), 2)}}
    return out


def pct(x):
    """A share as a whole percent, halves up (the shares are multiples of 1/2000, so exact halves occur)."""
    return f'{math.floor(100 * x + 0.5 + 1e-9)}%'


def first_size(res, s, rule, level, sizes):
    """The smallest simulated size whose share is at least level, and stays so at every larger simulated size."""
    ok = [N for N in sizes if all(res[str(M)][s][rule] >= level for M in sizes if M >= N)]
    return ok[0] if ok else None


def table_rows(res, sizes):
    """The table's numbers: shares of simulated tests whose interval excludes zero, on either side."""
    return [{'papers': N, 'corrected': res[str(N)]['corrected/seen']['excludes_zero'],
             'as_registered': res[str(N)]['registered/seen']['excludes_zero'],
             'corrected_half_values': res[str(N)]['corrected/half_values']['excludes_zero'],
             'corrected_half_papers': res[str(N)]['corrected/half_papers']['excludes_zero'],
             'as_registered_half_values': res[str(N)]['registered/half_values']['excludes_zero'],
             'as_registered_half_papers': res[str(N)]['registered/half_papers']['excludes_zero']} for N in sizes]


def table(res, sizes):
    L = ['| Papers | Corrected | As registered | Corrected, plain rate halved (values; papers) | As registered, plain rate halved (values; papers) |',
         '|---|---|---|---|---|']
    for r in table_rows(res, sizes):
        L.append(f"| {r['papers']} | {pct(r['corrected'])} | {pct(r['as_registered'])} | {pct(r['corrected_half_values'])}; "
                 f"{pct(r['corrected_half_papers'])} | {pct(r['as_registered_half_values'])}; {pct(r['as_registered_half_papers'])} |")
    return '\n'.join(L) + '\n'


def sides_table(res, sizes):
    """Which side the claims are on: plain higher / CatLog higher."""
    scen = ('corrected/seen', 'registered/seen', 'corrected/half_values', 'corrected/half_papers', 'registered/half_values',
            'registered/half_papers')
    L = ['| Papers | ' + ' | '.join(scen) + ' |', '|---|' + '---|' * len(scen)]
    for N in sizes:
        L.append(f'| {N} | ' + ' | '.join(f"{pct(res[str(N)][s]['above'])} / {pct(res[str(N)][s]['below'])}" for s in scen) + ' |')
    return '\n'.join(L) + '\n'


def other_table(res, sizes):
    p = res['pooled']
    L = ['| Papers | New rule (plain 91 wrong in 11 papers) | Corrected, sign test as well | Corrected, random test\'s papers only | '
         'Corrected, locked test\'s papers only | CatLog with no wrong value | No true difference: claimed either way | '
         'No true difference: plain higher | No true difference: plain higher, sign test as well |',
         '|---|---|---|---|---|---|---|---|---|']
    for N in sizes:
        r = p[str(N)]
        L.append(f"| {N} | {pct(r['newrule/seen']['above'])} | {pct(r['corrected/seen']['above_sign'])} | "
                 f"{pct(res['random_only'][str(N)]['corrected/seen']['above'])} | {pct(res['locked_only'][str(N)]['corrected/seen']['above'])} | "
                 f"{pct(r['catlog_none/seen']['above'])} | {pct(r['null']['excludes_zero'])} | {pct(r['null']['above'])} | "
                 f"{pct(r['null']['above_sign'])} |")
    return '\n'.join(L) + '\n'


def loo_table(loo):
    L = ['| Paper left out | Test | Its wrong values (plain; CatLog) | ' + ' | '.join(f'{N} papers' for N in LOO_SIZES) + ' |',
         '|---|---|---|' + '---|' * len(LOO_SIZES)]
    for pm, v in loo.items():
        L.append(f"| {pm} | {v['left_out']['test']} | {v['left_out']['plain_wrong']}; {v['left_out']['catlog_wrong']} | "
                 + ' | '.join(pct(v[str(N)]) for N in LOO_SIZES) + ' |')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--sims', type=int, default=SIMS)
    ap.add_argument('--B', type=int, default=B_SIM)
    ap.add_argument('--jobs', type=int, default=6)
    ap.add_argument('--out', default=str(HERE))
    a = ap.parse_args()
    rows = load()
    A = arrays(rows)
    chk = check(rows, A)
    print(json.dumps(chk, indent=1))
    if not chk['passed']:
        sys.exit('a check failed: nothing simulated')
    if a.check:
        return
    out_dir = Path(a.out).resolve()
    if out_dir == HERE and (a.sims, a.B) != (SIMS, B_SIM):
        sys.exit('a run with other --sims or --B needs its own --out, so that the saved results stay the full run')
    sim = {k: v for k, v in A.items() if k not in ('test', 'pmid')}
    everyone = np.arange(len(rows))
    pools = {'pooled': everyone, 'random_only': everyone[A['test'] == 'random'], 'locked_only': everyone[A['test'] == 'locked']}
    sizes = sorted(SIZES + MORE)
    # every pool and size has its own random stream, named by the seed, the pool's number and the size
    tasks = [((pool, N), sim, keep, N, a.sims, a.B, [SEED, pi, N], MAIN_SCEN if pool == 'pooled' else SIDE_SCEN)
             for pi, (pool, keep) in enumerate(pools.items()) for N in sizes]
    wrong_papers = [i for i in everyone if A['e_plain'][i] > 0 or A['e_catlog_corrected'][i] > 0]
    tasks += [(('leave_one_out', str(A['pmid'][i]), N), sim, everyone[everyone != i], N, a.sims, a.B, [SEED, 10, int(i), N],
               ['corrected/seen']) for i in wrong_papers for N in LOO_SIZES]
    tasks.sort(key=lambda t: -t[3])  # the long ones first
    res, loo, t0 = {p: {} for p in pools}, {}, time.time()
    if a.jobs > 1:
        import multiprocessing as mp
        with mp.get_context('spawn').Pool(a.jobs) as pool:
            done = list(pool.imap_unordered(task, tasks))
    else:
        done = [task(t) for t in tasks]
    for key, r in done:
        if key[0] == 'leave_one_out':
            loo.setdefault(key[1], {})[str(key[2])] = r['corrected/seen']
        else:
            res[key[0]][str(key[1])] = r
    for p in res:
        res[p] = {str(N): res[p][str(N)] for N in sizes}
    print(f'simulated in {time.time() - t0:.0f} s', file=sys.stderr)
    p = res['pooled']
    need = {s: {rule: {str(level): first_size(p, s, rule, level, sizes) for level in (0.8, 0.9)} for rule in ('above', 'above_5', 'above_sign')}
            for s in MAIN_SCEN if s != 'null'}
    need_side = {pool: {s: {str(level): first_size(res[pool], s, 'above', level, sizes) for level in (0.8, 0.9)} for s in SIDE_SCEN}
                 for pool in ('random_only', 'locked_only')}
    loo_out = {str(A['pmid'][i]): {'left_out': {'test': str(A['test'][i]), 'plain_wrong': int(A['e_plain'][i]),
                                                'catlog_wrong': int(A['e_catlog_corrected'][i])},
                                   **{N: loo[str(A['pmid'][i])][N]['above'] for N in map(str, LOO_SIZES)}}
               for i in wrong_papers}  # in the pool's order, whatever order the processes finished in
    out = {'written': time.strftime('%Y-%m-%d %H:%M:%S %z'), 'numpy': np.__version__, 'seed': SEED, 'simulated_tests_per_size': a.sims,
           'B_inside': a.B, 'sizes_asked': list(SIZES), 'sizes_added': list(MORE),
           'inputs': {t: str(f.relative_to(EVID)) for t, f in FILES.items()},
           'monte_carlo_standard_error_at_most': round(math.sqrt(0.25 / a.sims), 4),
           'check': chk, 'pool': pooled_counts(A),
           'pool_by_test': {t: {'papers': int((A['test'] == t).sum()),
                                'papers_plain_wrong': int(((A['e_plain'] > 0) & (A['test'] == t)).sum()),
                                'papers_catlog_wrong_corrected': int(((A['e_catlog_corrected'] > 0) & (A['test'] == t)).sum())}
                           for t in FILES},
           'table_rows': table_rows(p, SIZES), 'table_rows_sizes_added': table_rows(p, MORE),
           'smallest_size_reaching': need, 'smallest_size_reaching_other_pools': need_side,
           'leave_one_out_corrected_above': loo_out,
           'leave_one_out_range': {N: [min(v[N] for v in loo_out.values()), max(v[N] for v in loo_out.values())] for N in map(str, LOO_SIZES)},
           'results': res}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'power_results.json').write_text(json.dumps(out, indent=1) + '\n')
    text = ('Share of simulated tests whose interval excludes zero (power.py; the sizes asked for):\n\n' + table(p, SIZES)
            + '\nThe sizes added:\n\n' + table(p, MORE)
            + '\nWhich side: plain higher / CatLog higher (every size):\n\n' + sides_table(p, sizes)
            + '\nOther views, plain higher claimed (every size):\n\n' + other_table(res, sizes)
            + '\nCorrected view with one of the 10 papers that hold a wrong value left out of the pool:\n\n' + loo_table(loo_out))
    (out_dir / 'power_table.md').write_text(text)
    print(text)
    print(json.dumps({'smallest_size_reaching': need, 'other_pools': need_side, 'leave_one_out': loo_out,
                      'leave_one_out_range': out['leave_one_out_range']}, indent=1))


if __name__ == '__main__':
    main()
