#!/usr/bin/env python3
"""The locked test's registered sensitivity analysis, and how much the count over both tests depends on the judging.

  python3 -I -B sensitivity.py    checks the inputs against the counts already reported, then writes sensitivity.json,
                                  rule_differences.tsv and README.md next to this file; stops at the first mismatch

Nothing is read or judged again. The inputs are the two tests' results files, the judges' own verdict files, the claims
maps and values files that tie each verdict to a stored value, and the accuracy check's stats.py, whose functions and
definitions are used unchanged: papers with a wrong value (summary), the exact two-sided sign test on papers where only
one side holds a wrong value (sign), leave one out (leave_one_out), the paired paper bootstrap (boot), the per-paper rows
(paper_rows) and the three ways of counting CatLog's 34 unit changes (identify_as_printed, WAYS).

What was chosen before judging, and what after
  Before judging, the locked test chose a sensitivity analysis without the 41 papers that CatLog's side read again while
  a stopped launch's folders remained (PREREGISTRATION.md, "Changes after it"). Registered are that exclusion and the
  kit's report of it on the locked test alone, counted as the judges ruled (way (i)): sensitivity_read_once/RESULTS.md.
  That report prints no interval, because fewer than MIN_WRONG_PAPERS papers hold a wrong value (the kit's fixed rule in
  score_rand.py). The sign tests, ways (ii) and (iii), pooling with the random test, and (b) to (e) were all chosen after
  both results were in, as was the paper's own count over both tests.

What is computed
  (a) The locked test without the papers read again (its own results file, sensitivity_read_once/), alone and pooled with
      the random test. The kit's interval rule is applied as the kit applies it: plain minus CatLog gets an interval only
      when at least MIN_WRONG_PAPERS papers hold a wrong value on one side only; below that, counts and P values only.
      The pooled interval of way (ii) is also recomputed with 40 other seeds.
  (b) The random test's first judging pooled with the locked test (stats.py has the sign test; checked equal here), and,
      as an extra, with the locked test read once.
  (c) Two other judging rules, applied to every claim the judges ruled: stricter, wrong only when both first judges call
      it wrong; looser, wrong when any judge does (the third judge included). The kit's rule (two judges, a third on a
      split, score_w1.final_verdict) is replayed from the same files first and must give every paper's count in all
      three results files. The three ways are applied claim by claim: (ii) CatLog's 34 unit-change claims count right,
      (iii) also the plain reading's 34 as-printed claims of the same cells count wrong. Papers with a wrong value and the
      papers where only one side holds one (the sign test's papers) are reported apart wherever they differ.
  (d) The first two judges' agreement on whether a claim is wrong (a verdict that is one of the error verdicts, against
      supported or cannot decide), on the real claims both ruled: Cohen's kappa for these two classes, positive and
      negative agreement, and the kit's three-class kappa beside it (checked against the reports and the figures the
      paper's full Methods print).
  (e) The sampled agreeing pairs (values both readings stored, two claims each): pairs ruled wrong on both sides, the
      exact one-sided 95% upper bound on that share (Clopper-Pearson), scaled to all agreeing pairs, per test; over both
      tests, the exact bound for a sample drawn separately in each test (the sup of N1 p1 + N2 p2 over the joint 95%
      region). It bounds what these judges would rule wrong on both sides, not every error both readings share.
"""
import collections, hashlib, importlib.util, json, math, re, sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402
import scipy  # noqa: E402
from scipy.stats import beta, binom  # noqa: E402

HERE = Path(__file__).resolve().parent
EVID = HERE.parent                                   # catlog-v2/paper/evidence
KIT = Path.home() / 'Documents' / 'kinetics-reading'
RECORDS = KIT / 'records'
KIT_OUT = KIT / 'out'
OUT_JSON, OUT_TSV, OUT_MD = HERE / 'sensitivity.json', HERE / 'rule_differences.tsv', HERE / 'README.md'


def fail(msg):
    sys.exit(f'sensitivity.py stopped: {msg}')


def load_base():
    """stats.py of the accuracy check, loaded by path under its own name; its main() is not run."""
    f = EVID / 'accuracy_check_20261114' / 'stats.py'
    spec = importlib.util.spec_from_file_location('accuracy_check_stats', f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ST = load_base()
SOURCES, WAYS, MISPRINT, EXPECT_34 = ST.SOURCES, ST.WAYS, ST.MISPRINT, ST.EXPECT_34
WAY_SHORT = {'as_printed': '(i) as the judges ruled', 'unit_changes_right': "(ii) CatLog's 34 unit changes right",
             'own_numbers_both': "(iii) each paper's own numbers, both sides"}
SIDE = {'plain': 'the plain reading', 'catlog': 'CatLog'}

FILES = dict(ST.FILES)  # random (second judging, the one analysed), random_first, locked
FILES['locked_once'] = EVID / 'locked_test_20261109' / 'result' / 'sensitivity_read_once' / 'results.json'
TWICE = EVID / 'locked_test_20261109' / 'result' / 'locked_copy_read_twice.txt'
ONCE_REPORT = EVID / 'locked_test_20261109' / 'result' / 'sensitivity_read_once' / 'RESULTS.md'
PREREG = EVID / 'locked_test_20261109' / 'PREREGISTRATION.md'
FIRST_150 = EVID / 'random_papers_20261104' / 'results.json'   # the first judging's own report, on its 150 papers
STATS_JSON = EVID / 'accuracy_check_20261114' / 'stats.json'
KIT_SCORE_RAND = KIT / 'code' / 'tools' / 'w1' / 'score_rand.py'
# the same files where the kit wrote them (must be byte for byte the evidence copies)
KIT_COPIES = {'random': RECORDS / 'score_randfull' / 'results.json',
              'random_first': RECORDS / 'score_randfull' / 'first_on_same_papers' / 'results.json',
              'locked': RECORDS / 'score_locked' / 'results.json',
              'locked_once': RECORDS / 'score_locked' / 'sensitivity_read_once' / 'results.json',
              'twice': RECORDS / 'locked_copy_read_twice.txt',
              'once_report': RECORDS / 'score_locked' / 'sensitivity_read_once' / 'RESULTS.md'}
# each judging: the kit's run name (its claims and verdict folders) and its private folder (claims map, values)
JUDGINGS = {'random': ('randfull', RECORDS / 'score_randfull' / 'private'),
            'random_first': ('rand', RECORDS / 'score_rand' / 'private'),
            'locked': ('locked', RECORDS / 'score_locked' / 'private')}
ADJ_LOGS = {'randfull': RECORDS / 'logs' / 'adjudication_randfull', 'rand': RECORDS / 'logs' / 'adjudication_rand',
            'locked': RECORDS / 'logs' / 'adjudication_locked'}
REASON_WORDS = {'refused (catlog)': 'refused on CatLog\'s side', 'refused (plain)': 'refused on the plain side',
                'catlog rule_broken': 'with a rule broken on CatLog\'s side'}
RULES = ('kit', 'strict', 'loose')
RULE_NAMES = {'kit': 'the kit\'s rule: two judges, a third on a split (as reported)',
              'strict': 'stricter: wrong only when both first judges call it wrong',
              'loose': 'looser: wrong when any judge calls it wrong (the third judge included)'}
CONF = 0.95  # (e): exact one-sided 95% upper bounds
OTHER_SEEDS = tuple(range(1, 41))  # (a): the pooled bootstrap again with 40 other seeds

# Counts the paper and its evidence already print; the script stops if a recomputed one differs.
PRINTED_BOTH_TESTS = {  # Table 1b and stats.md: papers (values) plain, CatLog; sign test P; largest P leaving one out;
    'as_printed': ((9, 57), (3, 40), '0.146', '0.227', ('+2.59', '-12.07', '+16.60')),  # bootstrap per 1,000
    'unit_changes_right': ((9, 57), (1, 6), '0.0215', '0.039', ('+8.46', '+0.67', '+20.53')),
    'own_numbers_both': ((11, 91), (1, 6), '0.0063', '0.012', ('+14.12', '+2.75', '+29.80'))}
PRINTED_FIRST = {'as_printed': (11, 4, '0.118'), 'unit_changes_right': (11, 2, '0.0225'),  # stats.md, first judging
                 'own_numbers_both': (13, 2, '0.0074')}
PRINTED_FIRST_TIES = 4                                # stats.md: "4 papers had wrong values on both sides"
# the kit's sensitivity report (sensitivity_read_once/RESULTS.md; locked test README "52 papers remain", 7 and 34 wrong)
EXPECT_ONCE = (52, {'plain': (1010, 7, 2), 'catlog': (948, 34, 2)}, (2, 2))
READ_TWICE_N = 41                                     # methods.md: "a sensitivity analysis without 41 papers"
REGISTERED_SENTENCE = 'This sensitivity is chosen now, before any judging.'   # PREREGISTRATION.md, "Changes after it"
READ_TWICE_SENTENCE = '41 papers had agents in two launches'                  # the same entry
VISIBLE_PAIRING = 'an agreeing value shows as two claims'                     # PREREGISTRATION.md, "Limits stated now"
MIN_WRONG_PRINTED = 5      # Table 1 note 2: "A rate has an interval only when at least five papers hold a wrong value"
PRINTED_KAPPA = {'random': '0.837', 'locked': '0.894', 'random_first': '0.897'}  # results files, kappa on real claims
PRINTED_KAPPA_150 = '0.863'                           # the first judging's own report, 150 papers (Methods prints it)
# the paper's full Methods (writing/manuscript/methods_full.md): "Cohen's kappa over the three classes on all real claims
# was 0.863, 0.837 and 0.894" (first judging on its 150 papers, the random test's second judging, the locked test)
PRINTED_KAPPA_METHODS = ('0.863', '0.837', '0.894')
PRINTED_DISPUTED = {'random': '0.970', 'locked': '0.965', 'random_first': '0.968'}  # first two agree, disputed claims
PRINTED_SAMPLE = {'random': {'plain': (1, 739), 'catlog': (0, 739)}, 'locked': {'plain': (0, 500), 'catlog': (0, 500)}}
PRINTED_AGREED_NOT_JUDGED = {'random': 3499, 'locked': 795}
PRINTED_LOCKED_AGREEING = (1295, 500)                 # locked triage: agreeing pairs, of them sampled


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------- the kit's verdict rules, copied from kinetics-reading/code/tools/w1/score_w1.py and common_w1.py ----------

KIT_ERRORS = ('wrong_number', 'wrong_scale', 'wrong_metric', 'wrong_identity', 'wrong_conditions', 'not_measured_here',
              'not_printed')
KIT_MISPRINTS = ('printed_misprint', 'corrected_misprint')
KIT_VERDICTS = ('supported',) + KIT_ERRORS + ('cannot_decide',) + KIT_MISPRINTS
JUDGES = ('j1', 'j2', 'j3')
CODE_ALPHABET = 'bcdfghjkmnpqrstvxz23456789'


def kit_code(label):
    """common_w1.code: the six-character folder name under out/ for an internal label."""
    h = int(hashlib.sha256(f'kinetics-reading/{label}'.encode()).hexdigest(), 16)
    out = ''
    for _ in range(6):
        h, r = divmod(h, len(CODE_ALPHABET))
        out += CODE_ALPHABET[r]
    return out


def klass(v):
    """score_w1.klass."""
    return (None if v is None else 'supported' if v == 'supported' else 'cannot_decide' if v == 'cannot_decide'
            else v if v in KIT_MISPRINTS else 'error')


def final_verdict(v1, v2, v3=None):
    """score_w1.final_verdict: (final verdict or None while pending, whether a third judge is needed)."""
    if v1 is None or v2 is None:
        return None, False
    if klass(v1) == klass(v2):
        return (v1 if v1 == v2 or klass(v1) != 'error' else 'mixed'), False
    if v3 is None:
        return None, True
    ks = [klass(v1), klass(v2), klass(v3)]
    win = [k for k in set(ks) if ks.count(k) >= 2]
    if not win:
        return 'cannot_decide', True
    if win[0] != 'error':
        return win[0], True
    errs = [v for v in (v1, v2, v3) if klass(v) == 'error']
    kinds = [k for k in set(errs) if errs.count(k) >= 2]
    return (kinds[0] if kinds else v3 if klass(v3) == 'error' else errs[0]), True


def kappa(a, b):
    """score_w1.kappa (Cohen's kappa of two equal-length label lists)."""
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(k) / n) * (b.count(k) / n) for k in set(a) | set(b))
    return None if pe == 1 else (po - pe) / (1 - pe)


def kit_min_wrong_papers():
    """score_rand.MIN_WRONG_PAPERS, read from the kit's code: fewer papers with a wrong value, no percentile interval."""
    m = re.findall(r'^MIN_WRONG_PAPERS = (\d+)\b', KIT_SCORE_RAND.read_text(), re.M)
    if len(m) != 1 or int(m[0]) != MIN_WRONG_PRINTED:
        fail(f'{KIT_SCORE_RAND}: MIN_WRONG_PAPERS {m}, Table 1 prints {MIN_WRONG_PRINTED}')
    return int(m[0])


def load_verdicts(which):
    """score_w1.load_verdicts on out/<code of verdicts-jK-which>/: {claim id: {judge: verdict}}, the first verdict per
    claim and judge (files in name order). Also the files read, with their hashes."""
    out, files = {}, {}
    for j in JUDGES:
        d = KIT_OUT / kit_code(f'verdicts-{j}-{which}')
        if not d.is_dir():
            fail(f'{d} not found')
        for f in sorted(d.glob('*.json')):
            files[str(f.relative_to(KIT))] = sha256(f)
            try:
                x = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            for v in x.get('verdicts') or []:
                if isinstance(v, dict) and v.get('verdict') in KIT_VERDICTS:
                    out.setdefault(str(v.get('id')), {}).setdefault(j, v['verdict'])
    return out, files


def session_outs(which):
    """The verdict files named by the judges' session records (records/logs/adjudication_<which>/*.json, key out)."""
    outs = set()
    for f in ADJ_LOGS[which].glob('*.json'):
        try:
            d = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and d.get('out') and d.get('ok'):
            try:
                outs.add(str(Path(d['out']).relative_to(KIT)))
            except ValueError:  # a session of another layout writes elsewhere; it names none of these files
                continue
    return outs


def session_checks(which, pmid, chunk, judge):
    """The status ('check') of every recorded session of one judge on one chunk, e.g. 'refused by the safety filter'."""
    out = []
    for f in sorted(ADJ_LOGS[which].glob(f'{pmid}.{chunk}.{judge}.a*.json')):
        d = json.loads(f.read_text())
        out.append({'record': f.name, 'ok': bool(d.get('ok')), 'check': str(d.get('check'))})
    return out


def refusals_logged(which, pmid, chunk, judge):
    """How many times the kit's refusal log (records/logs/adjudication_<which>/refused.tsv, one line per refusal) lists
    one judge's step on one chunk as refused."""
    f = ADJ_LOGS[which] / 'refused.tsv'
    lines = f.read_text().splitlines()
    if not lines or lines[0].split('\t')[:2] != ['step', 'pmid']:
        fail(f'{f}: not the refusal log the kit writes')
    return sum(line.split('\t')[0] == f'{pmid}.{chunk}.{judge}' for line in lines[1:] if line.strip())


# ---------- replay: each stored value's verdict, and the kit's per-paper counts ----------

def replay(name, res):
    """Ties every stored value of the papers in res to its claim and the claim's verdicts; the kit's rule must give every
    paper's count in res (per_paper) exactly."""
    which, priv = JUDGINGS[name]
    cmap = [json.loads(line) for line in open(priv / 'claims_map.jsonl') if line.strip()]
    vals = json.loads((priv / 'values.json').read_text())
    V, vfiles = load_verdicts(which)
    named = session_outs(which)
    unnamed = sorted(set(vfiles) - named)
    if unnamed:
        fail(f'{which}: verdict files no ok judge session names as its output: {unnamed[:5]}')
    if any(x in KIT_MISPRINTS for v in V.values() for x in v.values()):
        fail(f'{which}: a misprint verdict, which no judging of these two tests may hold')
    final, stopped = {}, collections.Counter()
    for c in cmap:
        v = V.get(c['claim_id'], {})
        f, _ = final_verdict(v.get('j1'), v.get('j2'), v.get('j3'))
        if f is None:  # no verdict once the judging had ended: a step the filter stopped, cannot_decide for the kit
            f = 'cannot_decide'
            stopped[c['pmid']] += not c['decoy']
        final[c['claim_id']] = f
    if {p: k for p, k in stopped.items() if k} != res['left_out']['claims_cannot_decide_by_a_stopped_judge_session']:
        fail(f'{name}: claims with no final verdict {dict(stopped)} against the report\'s stopped steps')
    good = set(res['per_paper'])
    claim_of = {}
    for c in cmap:
        if c['decoy'] or c['pmid'] not in good:
            continue
        srcs = sorted(m['src'] for m in c['members'])
        shown = 'both' if srcs == sorted(SOURCES) else srcs[0] if len(srcs) == 1 else None
        if shown is None or shown != c.get('source_shown') or not set(srcs) <= set(SOURCES):
            fail(f'{name}: claim {c["claim_id"]} shows {c.get("source_shown")} for values of {srcs}')
        for m in c['members']:  # a claim shown word for word for both sides (first judging only) is one verdict for both
            if (m['src'], m['id']) in claim_of:
                fail(f'{name}: value {m["src"]} {m["id"]} is in two claims')
            claim_of[(m['src'], m['id'])] = c
    values = {s: [v for v in vals[s] if v['pmid'] in good] for s in SOURCES}
    pp = {p: {s: {'values': 0, 'wrong': 0} for s in SOURCES} for p in res['per_paper']}
    for s in SOURCES:
        for v in values[s]:
            c = claim_of.get((s, v['id']))
            pp[v['pmid']][s]['values'] += 1
            pp[v['pmid']][s]['wrong'] += c is not None and klass(final[c['claim_id']]) == 'error'
    if pp != res['per_paper']:
        bad = [p for p in pp if pp[p] != res['per_paper'][p]]
        fail(f'{name}: the replayed verdicts give other per-paper counts than the report: {bad[:5]}')
    real = [c for c in cmap if not c['decoy'] and c['pmid'] in good]
    return {'name': name, 'which': which, 'cmap': cmap, 'real': real, 'final': final, 'V': V, 'claim_of': claim_of,
            'values': values, 'order': list(res['per_paper']), 'good': good, 'verdict_files': len(vfiles),
            'verdict_files_sha256': hashlib.sha256(json.dumps(vfiles, sort_keys=True).encode()).hexdigest(),
            'claims_map_sha256': sha256(priv / 'claims_map.jsonl'), 'values_sha256': sha256(priv / 'values.json')}


# ---------- (c) claim-level rules and the three ways ----------

def claim_flags(rp):
    """Per real claim: wrong under each rule."""
    out = {}
    for c in rp['real']:
        v = rp['V'].get(c['claim_id'], {})
        k = [klass(v.get(j)) for j in JUDGES]
        out[c['claim_id']] = {'kit': klass(rp['final'][c['claim_id']]) == 'error',
                              'strict': k[0] == 'error' and k[1] == 'error',
                              'loose': 'error' in k}
    return out


def rule_rows(rp, test, rule, way, flags, cat34, pl34):
    """Rows in stats.py's paper_rows shape (test, pmid, pv, pw, cv, cw) for one rule and way. An agreeing pair that was not
    sampled is right for both sides, as the kit counts it; the denominators are every stored value, as in stats.py."""
    per = {p: {'pv': 0, 'pw': 0, 'cv': 0, 'cw': 0} for p in rp['order']}
    for s, nv, nw in (('plain', 'pv', 'pw'), ('catlog', 'cv', 'cw')):
        for v in rp['values'][s]:
            c = rp['claim_of'].get((s, v['id']))
            per[v['pmid']][nv] += 1
            if c is None:
                continue
            cid = c['claim_id']
            wrong = flags[cid][rule]
            if test == 'locked' and way != 'as_printed' and s == 'catlog' and cid in cat34:
                wrong = False                      # (ii) and (iii): CatLog's 34 unit changes right
            if test == 'locked' and way == 'own_numbers_both' and s == 'plain' and cid in pl34:
                wrong = True                       # (iii): the plain reading's 34 as-printed values of those cells wrong
            per[v['pmid']][nw] += wrong
    return [{'test': test, 'pmid': p, **per[p]} for p in rp['order']]


def analyse(rows, min_wrong, boot=True):
    """stats.py's statistics on one set of rows, and whether the kit's rule gives the difference an interval."""
    lo = ST.leave_one_out(rows)
    s = ST.sign(rows)
    out = {'papers_with_a_wrong_value': ST.summary(rows), 'sign_test': s,
           'leave_one_out': {k: lo[k] for k in ('largest_p', 'smallest_p', 'drops_taking_p_over_0.05',
                                                 'drops_with_p_over_0.05', 'drops')},
           'kit_interval_rule': {'papers_wrong_on_one_side_only': s['plain_only'] + s['catlog_only'],
                                 'min_wrong_papers': min_wrong,
                                 'interval_given': s['plain_only'] + s['catlog_only'] >= min_wrong}}
    if boot:
        out['bootstrap'] = ST.boot(rows)
        out['bootstrap']['within_the_kit_rule'] = out['kit_interval_rule']['interval_given']
    return out


# ---------- (e) exact upper bounds ----------

def cp_upper(x, n, conf=CONF):
    """Clopper-Pearson upper limit for x of n at level conf (one-sided)."""
    return 1.0 if x >= n else float(beta.ppf(conf, x + 1, n - x))


def strat_prob(p1, p2, s1, s2, t):
    """P(N1 y1/n1 + N2 y2/n2 <= t), y_h ~ Binomial(n_h, p_h) independent; s_h = (N_h, n_h, x_h)."""
    (N1, n1, _), (N2, n2, _) = s1, s2
    eps = 1e-9 * max(1.0, t)
    total = 0.0
    for y2 in range(0, int(math.floor(t * n2 / N2 + eps)) + 1):
        m1 = int(math.floor((t - N2 * y2 / n2) * n1 / N1 + eps))
        if m1 >= 0:
            total += float(binom.pmf(y2, n2, p2)) * float(binom.cdf(m1, n1, p1))
    return total


def strat_upper(s1, s2, conf=CONF, grid=401):
    """Exact upper confidence bound for N1 p1 + N2 p2 from a sample stratified in two (s_h = (N_h, n_h, x_h)): the sup of
    N1 p1 + N2 p2 over the region where the observed estimate of the total, N1 x1/n1 + N2 x2/n2, is not in the lower
    alpha tail (test inversion: coverage at least conf). The region is a lower set in (p1, p2), so for each p2 the largest
    p1 is found by bisection, and the total is maximised over p2 on a grid, then refined."""
    a = 1 - conf
    t = s1[0] * s1[2] / s1[1] + s2[0] * s2[2] / s2[1]

    def bisect(f, lo=0.0, hi=1.0, it=60):  # the largest x in [lo, hi] with f(x) > a, f decreasing
        if f(hi) > a:
            return hi
        for _ in range(it):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) > a else (lo, mid)
        return lo

    p2max = bisect(lambda p2: strat_prob(0.0, p2, s1, s2, t))

    def total(p2):
        if strat_prob(0.0, p2, s1, s2, t) <= a:
            return -1.0
        return s1[0] * bisect(lambda p1: strat_prob(p1, p2, s1, s2, t)) + s2[0] * p2

    xs = np.linspace(0.0, p2max * (1 - 1e-12), grid)
    ts = [total(x) for x in xs]
    i = int(np.argmax(ts))
    lo, hi = xs[max(i - 1, 0)], xs[min(i + 1, grid - 1)]
    g = (math.sqrt(5) - 1) / 2  # golden section on the bracket around the best grid point
    c, d = hi - g * (hi - lo), lo + g * (hi - lo)
    for _ in range(60):
        if total(c) >= total(d):
            hi, d = d, c
            c = hi - g * (hi - lo)
        else:
            lo, c = c, d
            d = lo + g * (hi - lo)
    best_x = max([xs[i], c, d], key=total)
    return {'bound': total(best_x), 'at_p2': best_x, 'p2_alone_max': p2max, 't_observed': t}


def strat_upper_zero(s1, s2, conf=CONF, n=200001):
    """The same bound when x1 = x2 = 0, in closed form along the region's edge (1-p1)^n1 (1-p2)^n2 = alpha."""
    a = 1 - conf
    (N1, n1, _), (N2, n2, _) = s1, s2
    p2 = np.linspace(0.0, 1 - a ** (1 / n2), n)
    p1 = 1 - (a / (1 - p2) ** n2) ** (1 / n1)
    return float(np.max(N1 * np.clip(p1, 0, 1) + N2 * p2))


def agreeing_pairs(rp, res, test):
    """(e) for one test: the sampled agreeing pairs (two claims each, one per side) and the unsampled ones."""
    pairs = {}
    for c in rp['real']:
        if c['kind'] != 'matched_sample':
            continue
        m, other = c['members'][0], c.get('partner') or []
        if len(other) != 2 or other[0] == m['src']:
            fail(f'{test}: sampled claim {c["claim_id"]} has no partner of the other side')
        key = (m['id'], other[1]) if m['src'] == 'catlog' else (other[1], m['id'])
        if m['src'] in pairs.setdefault(key, {}):
            fail(f'{test}: pair {key} holds two claims of one side')
        pairs[key][m['src']] = {'final': rp['final'][c['claim_id']], 'value': m['value'], 'pmid': c['pmid'],
                                'chunk': c['chunk'], 'claim_id': c['claim_id'], 'shown_value': c['shown'].get('value')}
    if any(set(p) != set(SOURCES) for p in pairs.values()):
        fail(f'{test}: a sampled pair without its two claims')
    if any(p['plain']['pmid'] != p['catlog']['pmid'] for p in pairs.values()):
        fail(f'{test}: a sampled pair across two papers')
    cls = [{s: klass(p[s]['final']) for s in SOURCES} for p in pairs.values()]
    with_wrong = [{'pmid': p['plain']['pmid'], 'ruled_wrong': [s for s in SOURCES if klass(p[s]['final']) == 'error'],
                   'verdicts': {s: p[s]['final'] for s in SOURCES},
                   'plain_over_catlog': round(p['plain']['value'] / p['catlog']['value'], 4) if p['catlog']['value'] else None}
                  for p in pairs.values() if any(klass(p[s]['final']) == 'error' for s in SOURCES)]
    undecided = [k for k in cls if 'cannot_decide' in k.values()]
    if any('error' in k.values() for k in undecided):
        fail(f'{test}: a sampled pair with one claim wrong and the other undecided (the counts below assume none)')
    both_undecided = sum(all(k[s] == 'cannot_decide' for s in SOURCES) for k in undecided)
    # each undecided claim: which judges ruled it (verdict classes), which gave no verdict, and their sessions' status
    undecided_claims = []
    for p in pairs.values():
        if not any(klass(p[s]['final']) == 'cannot_decide' for s in SOURCES):
            continue
        for s in SOURCES:
            v = rp['V'].get(p[s]['claim_id'], {})
            silent = [j for j in ('j1', 'j2') if j not in v]
            undecided_claims.append({'pmid': p[s]['pmid'], 'side': s, 'final': p[s]['final'],
                                     'verdict_classes': {j: klass(x) for j, x in sorted(v.items())},
                                     'no_verdict_from': silent,
                                     'sessions_of_judges_without_a_verdict': {
                                         j: session_checks(rp['which'], p[s]['pmid'], p[s]['chunk'], j) for j in silent},
                                     'refusals_logged': {
                                         j: refusals_logged(rp['which'], p[s]['pmid'], p[s]['chunk'], j) for j in silent}})
    decided = [k for k in cls if 'cannot_decide' not in k.values()]
    shared = sum(all(k[s] == 'error' for s in SOURCES) for k in decided)
    either = sum(any(k[s] == 'error' for s in SOURCES) for k in decided)
    side = {s: (sum(k[s] == 'error' for k in cls), sum(k[s] != 'cannot_decide' for k in cls)) for s in SOURCES}
    for s in SOURCES:
        smp = res['per_source'][s]['sample']
        if side[s] != (smp['wrong'], smp['of']) or side[s] != PRINTED_SAMPLE[test][s]:
            fail(f'{test} {s}: sampled claims wrong {side[s]}, report {(smp["wrong"], smp["of"])}')
        lo, hi = smp['exact_share']  # the kit's two-sided 95% limits, the same formula at 97.5% one-sided
        if abs(cp_upper(side[s][0], side[s][1], 0.975) - hi) > 1e-12:
            fail(f'{test} {s}: Clopper-Pearson limit {cp_upper(side[s][0], side[s][1], 0.975)} against the report {hi}')
    unsampled = {s: sum((s, v['id']) not in rp['claim_of'] for v in rp['values'][s]) for s in SOURCES}
    if len(set(unsampled.values())) != 1 or unsampled['plain'] != res['per_source']['plain']['values_agreed_not_judged'] \
            or unsampled['plain'] != PRINTED_AGREED_NOT_JUDGED[test]:
        fail(f'{test}: unsampled agreeing values {unsampled}, report {PRINTED_AGREED_NOT_JUDGED[test]}')
    N = len(pairs) + unsampled['plain']
    if test == 'locked':
        tri = res['triage']
        if (N, len(pairs)) != (tri['agreeing_pairs'], tri['agreeing_pairs_sampled']) or (N, len(pairs)) != PRINTED_LOCKED_AGREEING:
            fail(f'locked: {N} agreeing pairs, {len(pairs)} sampled; triage {tri["agreeing_pairs"]}, {tri["agreeing_pairs_sampled"]}')
    stored = {s: len(rp['values'][s]) for s in SOURCES}
    undecided_papers = sorted({p['plain']['pmid'] for p in pairs.values()
                               if any(klass(p[s]['final']) == 'cannot_decide' for s in SOURCES)})
    same_shown = sum(p['plain']['shown_value'] is not None and p['plain']['shown_value'] == p['catlog']['shown_value']
                     for p in pairs.values())
    out = {'agreeing_pairs': N, 'sampled_pairs': len(pairs), 'sampled_pairs_shown_with_the_same_number': same_shown,
           'sampled_pairs_with_a_claim_undecided': len(undecided),
           'sampled_pairs_with_both_claims_undecided': both_undecided, 'undecided_pairs_papers': undecided_papers,
           'undecided_claims': undecided_claims,
           'sampled_pairs_decided': len(decided), 'unsampled_pairs': unsampled['plain'], 'stored_values': stored,
           'sampled_claims_wrong_by_side': {s: {'wrong': side[s][0], 'of': side[s][1]} for s in SOURCES},
           'sampled_pairs_with_a_claim_ruled_wrong': with_wrong}
    for lab, x in (('both_claims_wrong', shared), ('either_claim_wrong', either)):
        u = cp_upper(x, len(decided))
        out[lab] = {'found': x, 'of': len(decided), 'upper_share': u, 'upper_count_all_pairs': u * N,
                    'upper_per_1000_stored': {s: 1000 * u * N / stored[s] for s in SOURCES}}
    return out


# ---------- (d) agreement ----------

def agreement(rp, res):
    """The first two judges on the real claims both ruled: the kit's three-class kappa (checked against the report), the
    error class (an error verdict against supported or cannot decide) as a 2x2, and the same on the disputed claims."""
    def table(claims):
        both = [rp['V'][c['claim_id']] for c in claims if 'j1' in rp['V'].get(c['claim_id'], {})
                and 'j2' in rp['V'].get(c['claim_id'], {})]
        e1 = ['error' if klass(b['j1']) == 'error' else 'not' for b in both]
        e2 = ['error' if klass(b['j2']) == 'error' else 'not' for b in both]
        a = sum(x == y == 'error' for x, y in zip(e1, e2))
        b_ = sum(x == 'error' and y == 'not' for x, y in zip(e1, e2))
        c_ = sum(x == 'not' and y == 'error' for x, y in zip(e1, e2))
        d = len(both) - a - b_ - c_
        same_kind = sum(klass(b['j1']) == 'error' and b['j1'] == b['j2'] for b in both)
        return {'claims': len(both), 'both_error': a, 'j1_only_error': b_, 'j2_only_error': c_, 'neither_error': d,
                'either_error': a + b_ + c_,
                'kappa_error_class': kappa(e1, e2),
                'positive_agreement': 2 * a / (2 * a + b_ + c_) if (2 * a + b_ + c_) else None,
                'negative_agreement': 2 * d / (2 * d + b_ + c_) if (2 * d + b_ + c_) else None,
                'observed_agreement': (a + d) / len(both) if both else None,
                'both_error_same_verdict': same_kind,
                'claims_with_a_cannot_decide_vote': sum('cannot_decide' in (klass(b['j1']), klass(b['j2'])) for b in both),
                'kappa_three_classes': kappa([klass(b['j1']) for b in both], [klass(b['j2']) for b in both]),
                'agree_three_classes': (sum(klass(b['j1']) == klass(b['j2']) for b in both) / len(both)) if both else None}
    out = {'all_real_claims': table(rp['real']),
           'disputed_claims': table([c for c in rp['real'] if c['kind'] != 'matched_sample'])}
    j = res['judges']
    if abs(out['all_real_claims']['kappa_three_classes'] - j['kappa_real_claims']) > 1e-12:
        fail(f'{rp["name"]}: three-class kappa {out["all_real_claims"]["kappa_three_classes"]}, report {j["kappa_real_claims"]}')
    if abs(out['disputed_claims']['agree_three_classes'] - j['first_two_agree_disputed']) > 1e-12:
        fail(f'{rp["name"]}: agreement on disputed claims differs from the report')
    if f'{j["kappa_real_claims"]:.3f}' != PRINTED_KAPPA[rp['name']] or \
            f'{j["first_two_agree_disputed"]:.3f}' != PRINTED_DISPUTED[rp['name']]:
        fail(f'{rp["name"]}: the report\'s kappa or agreement is not the printed one')
    return out


# ---------- formatting (README) ----------

def fmt_p(p):
    if p is None:
        return '-'
    if p >= 0.9995:
        return '1'
    return f'{p:.3g}' if p >= 0.01 else f'{p:.2g}'


def fmt_signed(x):
    return '0.00' if round(x, 2) == 0 else f'{x:+.2f}'.replace('-', '−')


def fmt_interval(b):
    return f'{fmt_signed(b["difference"])} ({fmt_signed(b["lo"])} to {fmt_signed(b["hi"])})'


def papers_cell(a):
    """Papers with a wrong value (wrong values), plain vs CatLog."""
    pw = a['papers_with_a_wrong_value']
    return (f'{pw["plain"]["papers_with_a_wrong_value"]} ({pw["plain"]["wrong"]}) vs '
            f'{pw["catlog"]["papers_with_a_wrong_value"]} ({pw["catlog"]["wrong"]})')


def cell(a, mark=''):
    """The main table: papers with a wrong value, and the sign test; with ties, the one-side-only count it uses."""
    s = a['sign_test']
    txt = papers_cell(a) + mark
    if s['both']:
        return (f'{txt}; one side only {s["plain_only"]} vs {s["catlog_only"]}, *P* = {fmt_p(s["p"])} '
                f'({s["both"]} on both sides)')
    return f'{txt}, *P* = {fmt_p(s["p"])}'


class Notes:
    """Footnote markers for a table: the same text gets the same letter."""
    def __init__(self, letters='abcdefghijklmnopqrstuvwxyz'):
        self.letters, self.items = letters, []

    def mark(self, text):
        for k, t in self.items:
            if t == text:
                return f'^{k}'
        k = self.letters[len(self.items)]
        self.items.append((k, text))
        return f'^{k}'

    def lines(self):
        return [f'^{k} {t}' for k, t in self.items]


def tie_note(a):
    s = a['sign_test']
    return (f'The sign test uses the {s["plain_only"]} against {s["catlog_only"]} papers where only one side holds a '
            f'wrong value; the {s["both"]} paper{"s" if s["both"] != 1 else ""} holding one on both sides '
            f'{"are" if s["both"] != 1 else "is"} left out as a tie.')


def t1b_row(label, a, notes, extra=None):
    """A row in Table 1b's columns. A P value from a sign test with ties, and a difference the kit's rule gives no
    interval, carry a note."""
    pw, cw = a['papers_with_a_wrong_value']['plain'], a['papers_with_a_wrong_value']['catlog']
    s, k = a['sign_test'], a['kit_interval_rule']
    p = fmt_p(s['p']) + (notes.mark(tie_note(a)) if s['both'] else '')
    if k['interval_given']:
        iv = fmt_interval(a['bootstrap'])
    else:
        iv = 'no interval' + notes.mark(
            f'Fewer than {k["min_wrong_papers"]} papers hold a wrong value on one side only, so the kit\'s fixed rule '
            '(score_rand.py, MIN_WRONG_PAPERS) gives no interval for plain minus CatLog: counts and P values only. '
            'sensitivity.json keeps stats.py\'s bootstrap for these rows, marked as outside that rule.')
    return (f'| {label}{extra or ""} | {pw["papers_with_a_wrong_value"]} ({pw["wrong"]}) | '
            f'{cw["papers_with_a_wrong_value"]} ({cw["wrong"]}) | {p} | {fmt_p(a["leave_one_out"]["largest_p"])} | {iv} |')


def check_once_report(text, d):
    """The kit's printed sensitivity report must say what its results.json says: the registered result as printed."""
    ps, cs = d['per_source']['plain'], d['per_source']['catlog']
    only = d['papers_wrong_in_one_source_only']

    def rate(s):
        return f'{s["wrong_per_1000"]} (in {s["papers_with_a_wrong_value"]} of {s["papers"]} papers: too few for an interval)'

    def pap(s):
        lo, hi = s['papers_per_100_exact']
        return f'{s["papers_with_a_wrong_value_per_100"]} ({lo}-{hi})'
    want = [f'Papers: {d["papers_used"]} analysed of {d["triage"]["papers_listed"]} listed',
            f'| Values | {ps["values"]} | {cs["values"]} |', f'| Wrong found | {ps["wrong"]} | {cs["wrong"]} |',
            f'| Wrong found per 1,000 (95% interval) | {rate(ps)} | {rate(cs)} |',
            f'| Papers with a wrong value found, per 100 (exact 95%) | {pap(ps)} | {pap(cs)} |',
            f'Papers wrong in one source only: plain {only["plain"]}, CatLog {only["catlog"]}.']
    missing = [w for w in want if w not in text]
    if missing:
        fail(f'{ONCE_REPORT}: the printed report lacks {missing}')
    if any(line.startswith('Plain minus CatLog') for line in text.splitlines()):
        fail(f'{ONCE_REPORT}: the printed report gives a difference interval, which its rule withholds here')
    return want


# ---------- main ----------

def main():
    R, inputs = {}, {}
    for name, f in FILES.items():
        if not f.exists():
            fail(f'{f} not found')
        R[name] = json.loads(f.read_text())
        inputs[name] = {'path': str(f), 'sha256': sha256(f)}
        if name in KIT_COPIES and sha256(KIT_COPIES[name]) != inputs[name]['sha256']:
            fail(f'{f} is not byte for byte {KIT_COPIES[name]}')
    for key, f in (('twice', TWICE), ('once_report', ONCE_REPORT)):
        if sha256(f) != sha256(KIT_COPIES[key]):
            fail(f'{f} is not byte for byte {KIT_COPIES[key]}')
    inputs['read_twice'] = {'path': str(TWICE), 'sha256': sha256(TWICE)}
    inputs['once_report'] = {'path': str(ONCE_REPORT), 'sha256': sha256(ONCE_REPORT)}
    inputs['kit_copies'] = {k: {'path': str(f), 'sha256': sha256(f), 'same_bytes_as': inputs[
        {'twice': 'read_twice', 'once_report': 'once_report'}.get(k, k)]['path']} for k, f in KIT_COPIES.items()}
    for key, f in (('preregistration', PREREG), ('first_judging_150', FIRST_150), ('kit_score_rand', KIT_SCORE_RAND),
                   ('refusal_log_randfull', ADJ_LOGS['randfull'] / 'refused.tsv')):
        inputs[key] = {'path': str(f), 'sha256': sha256(f)}
    stats_json = json.loads(STATS_JSON.read_text())
    inputs['stats_json'] = {'path': str(STATS_JSON), 'sha256': sha256(STATS_JSON)}
    inputs['stats_py'] = {'path': str(EVID / 'accuracy_check_20261114' / 'stats.py'),
                          'sha256': sha256(EVID / 'accuracy_check_20261114' / 'stats.py')}
    for name, f in FILES.items():  # stats.json was written from these same files
        if name in stats_json['inputs'] and stats_json['inputs'][name]['sha256'] != inputs[name]['sha256']:
            fail(f'{name} changed since stats.json was written')

    # what was chosen before judging: the exclusion (the registration's own words) and the kit's printed report of it
    prereg = PREREG.read_text()
    for sentence in (REGISTERED_SENTENCE, READ_TWICE_SENTENCE, VISIBLE_PAIRING):
        if sentence not in prereg:
            fail(f'{PREREG} does not say "{sentence}"')
    min_wrong = kit_min_wrong_papers()
    once_lines = check_once_report(ONCE_REPORT.read_text(), R['locked_once'])
    first_150 = json.loads(FIRST_150.read_text())
    if f'{first_150["judges"]["kappa_real_claims"]:.3f}' != PRINTED_KAPPA_150 or first_150['papers_used'] != 150:
        fail(f'{FIRST_150}: kappa {first_150["judges"]["kappa_real_claims"]} on {first_150["papers_used"]} papers')

    # every count of the results files, as stats.py checks them, and the sensitivity file the same way
    ST.EXPECT['locked_once'] = EXPECT_ONCE
    checks = {name: ST.check_file(name, R[name]) for name in FILES}
    twice = [line.strip() for line in TWICE.read_text().splitlines() if line.strip()]
    analysed = list(R['locked']['per_paper'])
    once = [p for p in analysed if p not in set(twice)]
    if len(twice) != READ_TWICE_N or len(set(twice)) != READ_TWICE_N:
        fail(f'{len(twice)} papers in the read-twice list, the paper says {READ_TWICE_N}')
    if once != list(R['locked_once']['per_paper']):
        fail('the sensitivity file does not hold exactly the analysed papers outside the read-twice list, in order')
    if any(R['locked_once']['per_paper'][p] != R['locked']['per_paper'][p] for p in once):
        fail('a read-once paper has other counts in the sensitivity file than in the locked test')
    if any(p not in once for p in MISPRINT):
        fail('a paper of the 34 unit changes is not read once')
    failed = R['locked']['triage'].get('papers_failed') or {}
    not_analysed = sorted(set(twice) - set(analysed), key=lambda p: p.zfill(12))
    if any(p not in failed for p in not_analysed):
        fail('a read-twice paper is neither analysed nor listed with a reason in the locked triage')
    read_twice = {'listed': len(twice), 'among_the_83_analysed': len(set(twice) & set(analysed)),
                  'not_analysed': not_analysed,
                  'not_analysed_by_reason': dict(collections.Counter(failed[p] for p in not_analysed)),
                  'read_once_analysed': len(once)}
    checks['read_twice'] = read_twice

    # the plain reading's 34 as-printed values and CatLog's 34 unit changes, as stats.py finds them
    pairs34 = ST.identify_as_printed(R['locked'])
    cat34, pl34 = {q['catlog_claim'] for q in pairs34}, {q['plain_claim'] for q in pairs34}
    if len(pairs34) != 34 or len(cat34) != 34 or len(pl34) != 34:
        fail('the 34 pairs are not 34 distinct claims on each side')

    # replay the judges' verdict files; the kit's rule must give every paper's count in each results file
    rp = {'random': replay('random', R['random']), 'random_first': replay('random_first', R['random_first']),
          'locked': replay('locked', R['locked'])}
    flags = {t: claim_flags(rp[t]) for t in ('random', 'locked')}
    if any(not flags['locked'][c]['kit'] for c in cat34) or any(flags['locked'][c]['kit'] for c in pl34):
        fail('the 34 CatLog claims are not all wrong, or the 34 plain claims not all right, by the kit\'s rule')

    rows = {r: {w: {t: rule_rows(rp[t], t, r, w, flags[t], cat34, pl34) for t in ('random', 'locked')} for w in WAYS}
            for r in RULES}
    for w in WAYS:  # the kit's rule, claim by claim, is stats.py's paper_rows, row by row
        for t in ('random', 'locked'):
            if rows['kit'][w][t] != ST.paper_rows(R[t], t, w):
                fail(f'kit rule, {w}, {t}: the claim-level rows differ from stats.py\'s paper_rows')
    rows_once = {w: ST.paper_rows(R['locked_once'], 'locked', w) for w in WAYS}
    rows_first = {w: ST.paper_rows(R['random_first'], 'random', w) for w in WAYS}
    for w in WAYS:
        if rows_once[w] != [r for r in rows['kit'][w]['locked'] if r['pmid'] in set(once)]:
            fail(f'{w}: the read-once rows are not the locked rows of those papers')
    # which papers with a wrong value the read-once rule takes out of the locked test, as the judges ruled
    read_twice['papers_with_a_wrong_value_left_out'] = {
        s: {r['pmid']: r[e] for r in rows['kit']['as_printed']['locked'] if r[e] > 0 and r['pmid'] not in set(once)}
        for s, e in (('plain', 'pw'), ('catlog', 'cw'))}

    # ---- the analyses
    A = collections.OrderedDict()

    def add(key, label, papers_note, rows_by_way, boot=True):
        A[key] = {'label': label, 'papers_note': papers_note,
                  'ways': {w: analyse(rows_by_way[w], min_wrong, boot) for w in WAYS}}

    add('both_tests', 'Both tests, as the paper reports them', 'random 147 (second judging) + locked 83',
        {w: rows['kit'][w]['random'] + rows['kit'][w]['locked'] for w in WAYS})
    add('random_alone', 'Random test alone (second judging)', 'random 147', {w: rows['kit'][w]['random'] for w in WAYS})
    add('locked_alone', 'Locked test alone, all 83 papers', 'locked 83', {w: rows['kit'][w]['locked'] for w in WAYS})
    add('a_locked_read_once', '(a) Locked test alone, without the 31', 'locked 52', rows_once)
    add('a_both_tests_read_once', '(a) Both tests, locked test without the 31', 'random 147 (second judging) + locked 52',
        {w: rows['kit'][w]['random'] + rows_once[w] for w in WAYS})
    add('b_first_judging_both_tests', "(b) Both tests, random test's first judging",
        'random 147 (first judging) + locked 83', {w: rows_first[w] + rows['kit'][w]['locked'] for w in WAYS})
    add('b_first_judging_read_once', "(b) Both tests, random test's first judging, locked test without the 31 (extra)",
        'random 147 (first judging) + locked 52', {w: rows_first[w] + rows_once[w] for w in WAYS})
    for r in ('strict', 'loose'):
        word = 'Stricter' if r == 'strict' else 'Looser'
        add(f'c_{r}_both_tests', f'(c) {word} rule, both tests', 'random 147 (second judging) + locked 83',
            {w: rows[r][w]['random'] + rows[r][w]['locked'] for w in WAYS})
        add(f'c_{r}_random', f'(c) {word} rule, random test', 'random 147 (second judging)',
            {w: rows[r][w]['random'] for w in WAYS})
        add(f'c_{r}_locked', f'(c) {word} rule, locked test', 'locked 83', {w: rows[r][w]['locked'] for w in WAYS})
        add(f'c_{r}_both_tests_read_once', f'(c) {word} rule, both tests, locked test without the 31 (extra)',
            'random 147 (second judging) + locked 52',
            {w: rows[r][w]['random'] + [x for x in rows[r][w]['locked'] if x['pmid'] in set(once)] for w in WAYS})

    # ---- checks against what the paper and its evidence print
    fp = lambda x, n: f'{x:.{n}g}'  # noqa: E731
    for w in WAYS:
        a = A['both_tests']['ways'][w]
        if a['sign_test'] != stats_json['sign_test'][w]['pooled']:
            fail(f'{w}: the pooled sign test differs from stats.json')
        if a['papers_with_a_wrong_value'] != stats_json['papers_with_a_wrong_value'][w]['pooled']:
            fail(f'{w}: the pooled papers with a wrong value differ from stats.json')
        if a['leave_one_out']['largest_p'] != stats_json['leave_one_out_sign_test'][w]['pooled']['largest_p']:
            fail(f'{w}: the pooled leave-one-out differs from stats.json')
        if any(abs(a['bootstrap'][k] - stats_json['bootstrap'][w]['pooled'][k]) > 1e-9 for k in ('difference', 'lo', 'hi')):
            fail(f'{w}: the pooled bootstrap differs from stats.json')
        (pp_, pv_), (cp_, cv_), p_txt, loo_txt, bt = PRINTED_BOTH_TESTS[w]
        s = a['papers_with_a_wrong_value']
        got = ((s['plain']['papers_with_a_wrong_value'], s['plain']['wrong']),
               (s['catlog']['papers_with_a_wrong_value'], s['catlog']['wrong']))
        p_ok = fp(a['sign_test']['p'], len(p_txt.split('.')[1].lstrip('0')) or 1) == p_txt
        loo_ok = fp(a['leave_one_out']['largest_p'], len(loo_txt.split('.')[1].lstrip('0'))) == loo_txt
        b = a['bootstrap']
        bt_ok = tuple(f'{x:+.2f}' for x in (b['difference'], b['lo'], b['hi'])) == bt
        if got != ((pp_, pv_), (cp_, cv_)) or not p_ok or not loo_ok or not bt_ok or a['sign_test']['both'] != 0:
            fail(f'{w}: both tests give {got}, P {a["sign_test"]["p"]}, leave one out {a["leave_one_out"]["largest_p"]}, '
                 f'bootstrap {b["difference"]}, {b["lo"]}, {b["hi"]}; the paper prints {PRINTED_BOTH_TESTS[w]}')
        if not a['kit_interval_rule']['interval_given']:
            fail(f'{w}: the paper prints an interval the kit\'s rule would withhold')
        f = A['b_first_judging_both_tests']['ways'][w]
        if f['sign_test'] != stats_json['first_judging']['sign_test'][w]['pooled'] or \
                f['papers_with_a_wrong_value'] != stats_json['first_judging']['papers_with_a_wrong_value'][w]['pooled'] or \
                f['leave_one_out']['largest_p'] != stats_json['first_judging']['leave_one_out'][w]['pooled']['largest_p']:
            fail(f'{w}: the first judging pooled differs from stats.json')
        a_, b_, p_ = PRINTED_FIRST[w]
        if (f['sign_test']['plain_only'], f['sign_test']['catlog_only']) != (a_, b_) or \
                fp(f['sign_test']['p'], len(p_.split('.')[1].lstrip('0'))) != p_ or \
                f['sign_test']['both'] != PRINTED_FIRST_TIES:
            fail(f'{w}: the first judging gives {f["sign_test"]}, stats.md prints {PRINTED_FIRST[w]}, '
                 f'{PRINTED_FIRST_TIES} ties')
        for t, key in (('random', 'random_alone'), ('locked', 'locked_alone')):
            x = A[key]['ways'][w]
            if x['sign_test'] != stats_json['sign_test'][w][t] or \
                    any(abs(x['bootstrap'][k] - stats_json['bootstrap'][w][t][k]) > 1e-9 for k in ('difference', 'lo', 'hi')):
                fail(f'{w} {t}: the test alone differs from stats.json')
    # the kit's sensitivity results.json: its bootstrap is stats.py's boot on the read-once rows (the report withholds it)
    so = ST.boot(rows_once['as_printed'])
    k = R['locked_once']['plain_minus_catlog']
    if abs(so['lo'] - k['per_1000_lo']) > 1e-9 or abs(so['hi'] - k['per_1000_hi']) > 1e-9 or \
            abs(so['share_plain_higher'] - k['share_plain_higher']) > 1e-12:
        fail('the read-once bootstrap differs from the kit\'s sensitivity results.json')
    s1 = A['a_locked_read_once']['ways']['as_printed']['sign_test']
    if (s1['plain_only'], s1['catlog_only']) != EXPECT_ONCE[2] or s1['both'] != 0:
        fail('the read-once papers wrong on one side only differ from the kit\'s sensitivity report')
    if A['a_locked_read_once']['ways']['as_printed']['kit_interval_rule']['interval_given']:
        fail('the kit\'s rule would give the read-once difference an interval, but its report prints none')
    checks['sensitivity_bootstrap_equals_kit_results_json'] = [k['per_1000_lo'], k['per_1000_hi'], k['share_plain_higher']]
    ps = R['locked_once']['per_source']
    registered = {
        'what': ('the exclusion of the papers CatLog\'s side read again while a stopped launch\'s folders remained, and '
                 'the kit\'s report of it on the locked test alone, counted as the judges ruled (way (i))'),
        'registration': f'{PREREG}, "Changes after it": "{REGISTERED_SENTENCE}"',
        'report': str(ONCE_REPORT), 'report_lines_checked': once_lines,
        'papers': R['locked_once']['papers_used'],
        'values': {s: ps[s]['values'] for s in SOURCES}, 'wrong': {s: ps[s]['wrong'] for s in SOURCES},
        'wrong_per_1000': {s: ps[s]['wrong_per_1000'] for s in SOURCES},
        'papers_with_a_wrong_value': {s: ps[s]['papers_with_a_wrong_value'] for s in SOURCES},
        'papers_with_a_wrong_value_per_100': {s: ps[s]['papers_with_a_wrong_value_per_100'] for s in SOURCES},
        'papers_per_100_exact': {s: ps[s]['papers_per_100_exact'] for s in SOURCES},
        'papers_wrong_in_one_source_only': R['locked_once']['papers_wrong_in_one_source_only'],
        'misses': {s: ps[s]['misses_supported_values_only_the_other_stored'] for s in SOURCES},
        'interval_printed': None,
        'why_no_interval': (f'under the kit\'s fixed rule (score_rand.py, MIN_WRONG_PAPERS = {min_wrong}), a rate gets an '
                            f'interval only when at least {min_wrong} papers hold a wrong value on that side, and plain minus '
                            f'CatLog only when at least {min_wrong} papers hold a wrong value on one side only; here '
                            + ' and '.join(f'{ps[s]["papers_with_a_wrong_value"]}' for s in SOURCES)
                            + ' papers hold one, '
                            + f'{sum(R["locked_once"]["papers_wrong_in_one_source_only"][s] for s in SOURCES)} '
                            + 'on one side only'),
        'interval_in_results_json_outside_the_rule': {'lo': k['per_1000_lo'], 'hi': k['per_1000_hi']},
        'note': 'cannot-decide values out of the denominators, as the kit counts them; the locked test has none'}
    if (registered['wrong'], registered['papers']) != ({'plain': 7, 'catlog': 34}, 52):
        fail('the kit\'s sensitivity report does not give 7 and 34 wrong values on 52 papers')
    checks['kit_rule_replayed_from_verdict_files'] = {
        t: {'per_paper_equal_to_results_file': True, 'verdict_files': rp[t]['verdict_files'],
            'verdict_files_sha256': rp[t]['verdict_files_sha256'], 'claims_map_sha256': rp[t]['claims_map_sha256'],
            'values_sha256': rp[t]['values_sha256']} for t in rp}
    checks['claim_level_kit_rows_equal_stats_py_paper_rows'] = True
    checks['both_tests_and_first_judging_equal_stats_json_and_the_printed_numbers'] = True
    checks['kit_min_wrong_papers'] = min_wrong

    # ---- (a) how the count over both tests changes without the 31, and the pooled interval with other seeds
    change = {}
    for w in WAYS:
        a0, a1 = A['both_tests']['ways'][w], A['a_both_tests_read_once']['ways'][w]
        bs = [ST.boot(rows['kit'][w]['random'] + rows_once[w], seed=sd) for sd in OTHER_SEEDS]
        change[w] = {'reported': {'plain_only': a0['sign_test']['plain_only'], 'catlog_only': a0['sign_test']['catlog_only'],
                                  'p': a0['sign_test']['p'], 'bootstrap': [a0['bootstrap'][x] for x in ('difference', 'lo', 'hi')]},
                     'without_the_31': {'plain_only': a1['sign_test']['plain_only'],
                                        'catlog_only': a1['sign_test']['catlog_only'], 'p': a1['sign_test']['p'],
                                        'bootstrap': [a1['bootstrap'][x] for x in ('difference', 'lo', 'hi')]},
                     'weaker': a1['sign_test']['p'] > a0['sign_test']['p'],
                     'other_seeds': {'seeds': [min(OTHER_SEEDS), max(OTHER_SEEDS)], 'n': len(OTHER_SEEDS),
                                     'lo_range': [min(b['lo'] for b in bs), max(b['lo'] for b in bs)],
                                     'hi_range': [min(b['hi'] for b in bs), max(b['hi'] for b in bs)],
                                     'seeds_with_lo_at_or_below_zero': sum(b['lo'] <= 0 for b in bs),
                                     'seeds_with_hi_at_or_below_zero': sum(b['hi'] <= 0 for b in bs)}}

    # ---- (c) the claims whose ruling depends on the rule, and the claims no rule can change
    diffs = []
    for t in ('random', 'locked'):
        for c in rp[t]['real']:
            fl = flags[t][c['claim_id']]
            if len(set(fl.values())) > 1:
                v = rp[t]['V'].get(c['claim_id'], {})
                diffs.append({'test': t, 'pmid': c['pmid'], 'source': c['members'][0]['src'], 'claim_kind': c['kind'],
                              'metric': c['metric'], 'j1': v.get('j1') or '', 'j2': v.get('j2') or '',
                              'j3': v.get('j3') or '', 'final': rp[t]['final'][c['claim_id']],
                              'kit': fl['kit'], 'strict': fl['strict'], 'loose': fl['loose'],
                              'one_of_the_34': ('catlog unit change' if c['claim_id'] in cat34 else
                                                'plain as printed' if c['claim_id'] in pl34 else '') if t == 'locked' else '',
                              'claim_id': c['claim_id']})
    diffs.sort(key=lambda d: (d['test'], d['pmid'].zfill(12), d['source'], d['claim_id']))
    by_rule = {}
    for t in ('random', 'locked'):
        by_rule[t] = {}
        for r in RULES:
            cnt = collections.Counter()
            pap = collections.defaultdict(set)
            for c in rp[t]['real']:
                if flags[t][c['claim_id']][r]:
                    s = c['members'][0]['src']
                    cnt[s] += 1
                    pap[s].add(c['pmid'])
            by_rule[t][r] = {s: {'wrong_claims': cnt[s], 'papers': sorted(pap[s], key=lambda p: p.zfill(12))}
                             for s in SOURCES}
    undecided_real = {}
    for t in ('random', 'locked'):
        cd = [c for c in rp[t]['real'] if rp[t]['final'][c['claim_id']] == 'cannot_decide']
        votes = [rp[t]['V'].get(c['claim_id'], {}) for c in cd]
        if any(klass(x) == 'error' for v in votes for x in v.values()):
            fail(f'{t}: a claim left at cannot decide carries an error vote (the rules would differ on it)')
        why = collections.Counter()
        for c, v in zip(cd, votes):
            reason = ('no verdict from judge 2' if 'j2' not in v and 'j1' in v else
                      'both first judges said cannot decide' if klass(v.get('j1')) == klass(v.get('j2')) == 'cannot_decide'
                      else 'other')
            why[(c['pmid'], reason)] += 1
        if any(r == 'other' for _, r in why):
            fail(f'{t}: a claim at cannot decide for a reason not described here')
        undecided_real[t] = {'claims': len(cd), 'with_an_error_vote': 0,
                             'by_paper_and_reason': [{'pmid': p, 'reason': r, 'claims': n}
                                                     for (p, r), n in sorted(why.items(), key=lambda x: x[0][0].zfill(12))]}

    # ---- (d)
    agree = {t: agreement(rp[t], R[t]) for t in ('random', 'locked', 'random_first')}
    got_k = (f'{first_150["judges"]["kappa_real_claims"]:.3f}',
             f'{agree["random"]["all_real_claims"]["kappa_three_classes"]:.3f}',
             f'{agree["locked"]["all_real_claims"]["kappa_three_classes"]:.3f}')
    if got_k != PRINTED_KAPPA_METHODS:
        fail(f'three-class kappas {got_k}; the paper\'s Methods print {PRINTED_KAPPA_METHODS}')
    checks['three_class_kappas_equal_the_methods'] = list(got_k)

    # ---- (e)
    agp = {t: agreeing_pairs(rp[t], R[t], t) for t in ('random', 'locked')}
    pooled_e = {}
    for lab in ('both_claims_wrong', 'either_claim_wrong'):
        sL = (agp['locked']['agreeing_pairs'], agp['locked'][lab]['of'], agp['locked'][lab]['found'])
        sR = (agp['random']['agreeing_pairs'], agp['random'][lab]['of'], agp['random'][lab]['found'])
        su = strat_upper(sL, sR)
        # checks of the bound: with the locked stratum at 0, the random stratum alone is Clopper-Pearson; with nothing
        # found in either stratum, the closed form along the region's edge gives the same bound
        if abs(su['p2_alone_max'] - cp_upper(sR[2], sR[1])) > 1e-9 and sL[2] == 0:
            fail(f'{lab}: the stratified bound\'s edge {su["p2_alone_max"]} is not Clopper-Pearson {cp_upper(sR[2], sR[1])}')
        if sL[2] == 0 and sR[2] == 0:
            z = strat_upper_zero(sL, sR)
            if abs(z - su['bound']) > 1e-6 * max(1.0, z):
                fail(f'{lab}: the stratified bound {su["bound"]} differs from the closed form {z}')
            su['closed_form_check'] = z
        stored = {s: agp['random']['stored_values'][s] + agp['locked']['stored_values'][s] for s in SOURCES}
        pooled_e[lab] = {'found': sL[2] + sR[2], 'of': sL[1] + sR[1],
                         'sampled_pairs': agp['locked']['sampled_pairs'] + agp['random']['sampled_pairs'],
                         'agreeing_pairs': sL[0] + sR[0], 'upper_count_all_pairs': su['bound'],
                         'upper_per_1000_stored': {s: 1000 * su['bound'] / stored[s] for s in SOURCES},
                         'stored_values': stored, 'method': su}
    if pooled_e['both_claims_wrong']['stored_values'] != {'plain': ST.EXPECT_POOLED['plain'][0],
                                                          'catlog': ST.EXPECT_POOLED['catlog'][0]}:
        fail('the stored values of both tests are not 6,003 and 5,790')
    agp['both_tests_stratified'] = pooled_e

    # ---- write
    out = {'script': 'sensitivity.py', 'numpy': np.__version__, 'scipy': scipy.__version__, 'inputs': inputs,
           'kit_records': {'verdict_folders': {t: {j: str((KIT_OUT / kit_code(f'verdicts-{j}-{rp[t]["which"]}')).relative_to(KIT))
                                                    for j in JUDGES} for t in rp},
                           'claims_maps': {t: str((JUDGINGS[t][1] / 'claims_map.jsonl')) for t in rp},
                           'values': {t: str((JUDGINGS[t][1] / 'values.json')) for t in rp},
                           'session_records': {t: str(ADJ_LOGS[rp[t]['which']]) for t in rp}},
           'chosen_before_judging': registered,
           'chosen_after_both_results': ('ways (ii) and (iii); every sign test, leave-one-out and P value; every bootstrap '
                                         'here; pooling with the random test (as the paper\'s own count over both tests '
                                         'was); (b) the first judging; (c) the stricter and looser rules; (d) the two-class '
                                         'kappa and positive agreement; (e) the bounds'),
           'ways': ST.WAY_NAMES, 'rules': RULE_NAMES,
           'definitions': {
               'papers_with_a_wrong_value': 'papers where the side stored at least one value ruled wrong (stats.py summary)',
               'sign_test': ('exact two-sided binomial test, p = 0.5, on papers where only one side holds a wrong value; '
                             'papers where both do are ties and left out (stats.py sign: plain_only, catlog_only, both)'),
               'leave_one_out': 'the sign test again without each paper that holds a wrong value (stats.py leave_one_out)',
               'bootstrap': ('plain minus CatLog wrong per 1,000 stored values, paired paper bootstrap, B 10,000, seed '
                             '20261031, 95% percentile interval; pooled papers in the order random then locked (stats.py boot)'),
               'kit_interval_rule': (f'the kit\'s fixed rule (score_rand.py, MIN_WRONG_PAPERS = {min_wrong}): plain minus '
                                     f'CatLog gets an interval only when at least {min_wrong} papers hold a wrong value on '
                                     'one side only; a bootstrap below that is kept here with within_the_kit_rule false'),
               'error_class': 'a verdict that is one of the kit\'s seven error verdicts (score_w1.klass == error)',
               'kappa_error_class': 'Cohen\'s kappa of the first two judges, two classes: wrong against not wrong',
               'kappa_three_classes': ('the kit\'s kappa (score_w1.kappa): supported, wrong, cannot decide; the figure the '
                                       'tests\' reports print'),
               'positive_agreement': '2a / (2a + b + c), a = claims both first judges called wrong, b and c = only one did',
               'negative_agreement': '2d / (2d + b + c), d = claims neither called wrong',
               'agreeing_pair': ('a value both readings stored (the matcher paired them, labels agreeing); a sample was '
                                 'judged as two claims, one per side, nearly always shown with the same number '
                                 '(sampled_pairs_shown_with_the_same_number)'),
               'upper_share': ('exact one-sided 95% Clopper-Pearson upper limit on the share of decided sampled pairs that '
                               'these judges ruled wrong'),
               'upper_count_all_pairs': ('upper_share times all agreeing pairs of the test (sampled and not): pairs that '
                                         'would be ruled wrong on both sides'),
               'stratified_bound': ('both tests: the sup of N1 p1 + N2 p2 over the (p1, p2) whose probability of an estimated '
                                    'total no larger than the one observed exceeds 5% (exact, at least 95% coverage)')},
           'checks': checks,
           'read_twice': read_twice,
           'analyses': A,
           'a_change_from_the_reported_count': change,
           'wrong_claims_by_rule': by_rule,
           'rule_differences': len(diffs),
           'claims_at_cannot_decide_under_every_rule': undecided_real,
           'agreement': agree,
           'agreement_first_judging_own_report_150_papers': {'path': str(FIRST_150),
                                                              'kappa_three_classes': first_150['judges']['kappa_real_claims']},
           'agreeing_pairs': agp}
    OUT_JSON.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    cols = ['test', 'pmid', 'source', 'claim_kind', 'metric', 'j1', 'j2', 'j3', 'final', 'kit', 'strict', 'loose',
            'one_of_the_34', 'claim_id']
    OUT_TSV.write_text('\t'.join(cols) + '\n' + ''.join('\t'.join(str(d[c]) for c in cols) + '\n' for d in diffs))
    OUT_MD.write_text(readme(out, A, agree, agp, read_twice, diffs, change, undecided_real))
    print(f'wrote {OUT_JSON.name}, {OUT_TSV.name}, {OUT_MD.name}')


def readme(out, A, agree, agp, read_twice, diffs, change, undecided_real):
    W = WAYS
    tw = read_twice
    reg = out['chosen_before_judging']
    left = tw['papers_with_a_wrong_value_left_out']
    inp = out['inputs']
    L = ['# The locked test\'s registered sensitivity analysis, and how much the count over both tests depends on the '
         'judging', '',
         '## Question', '',
         'Over both tests, CatLog stored a wrong value in fewer papers than one plain reading by the same model; that count '
         'was made after both results were in. Before judging, the locked test chose a sensitivity analysis without the '
         f'{tw["listed"]} papers that CatLog\'s side read again while a stopped launch\'s folders remained. The paper does '
         'not report its result. (a) What does it give, alone and with the random test? (b) What does the count over both '
         'tests give with the random test\'s first judging? (c) And with a stricter and a looser rule for which values '
         'count as wrong? (d) How well did the first two judges agree on whether a value was wrong? (e) Among the values '
         'both readings stored, how many could both have wrong, which a comparison of the two sides cannot see?', '',
         'Nothing was read or judged again. Every number below is computed by `sensitivity.py` from the files listed, and '
         'the script stops if a count that the paper or its evidence already prints comes out different.', '']

    L += ['## What was chosen before judging, and what after', '',
          f'- Before judging: the exclusion, and the kit\'s report of it on the locked test alone, counted as the judges '
          f'ruled (way (i)). The registration says so in its list of changes ("{REGISTERED_SENTENCE}"). The report '
          f'(`{reg["report"]}`) gives {reg["papers"]} papers; {reg["wrong"]["plain"]} of the plain reading\'s '
          f'{reg["values"]["plain"]:,} values wrong ({reg["wrong_per_1000"]["plain"]} per 1,000) and '
          f'{reg["wrong"]["catlog"]} of CatLog\'s {reg["values"]["catlog"]:,} ({reg["wrong_per_1000"]["catlog"]} per 1,000); '
          f'a wrong value in {reg["papers_with_a_wrong_value"]["plain"]} papers for the plain reading and '
          f'{reg["papers_with_a_wrong_value"]["catlog"]} for CatLog ({reg["papers_with_a_wrong_value_per_100"]["plain"]} '
          f'per 100 each, exact 95% {reg["papers_per_100_exact"]["plain"][0]} to {reg["papers_per_100_exact"]["plain"][1]}), '
          f'none on both sides. It gives no interval for either rate or for the difference: {reg["why_no_interval"]}.',
          f'- After both results: {out["chosen_after_both_results"]}. None of the P values is adjusted for the number of '
          'comparisons, and they come from overlapping data.', '']

    vf = out['kit_records']['verdict_folders']
    L += ['## Inputs', '',
          '- Results files: ' + ', '.join(f'`{inp[k]["path"]}`' for k in ('random', 'random_first', 'locked',
                                                                         'locked_once')) + '.',
          f'- The kit\'s printed report of the sensitivity analysis: `{inp["once_report"]["path"]}`. The papers CatLog\'s '
          f'side read again: `{inp["read_twice"]["path"]}`.',
          '- The same files where the kit wrote them, checked byte for byte equal to the copies above: '
          + ', '.join(f'`{v["path"]}`' for v in inp['kit_copies'].values()) + '.',
          f'- The registration: `{inp["preregistration"]["path"]}`. The kit\'s interval rule: `{inp["kit_score_rand"]["path"]}` '
          f'(MIN_WRONG_PAPERS). The first judging\'s own report, on its 150 papers: `{inp["first_judging_150"]["path"]}`.',
          f'- The base: `{inp["stats_py"]["path"]}` (its functions and definitions, used unchanged) and '
          f'`{inp["stats_json"]["path"]}` (its results, checked equal).',
          '- The judges\' per-claim verdicts (judges 1, 2 and 3), as the kit reads them, under `' + str(KIT_OUT) + '/`: '
          + '; '.join(f'{lab} `' + '/`, `'.join(vf[t][j].split('/')[-1] for j in JUDGES) + '/`'
                      for t, lab in (('random', 'random test, second judging'), ('locked', 'locked test'),
                                     ('random_first', 'random test, first judging')))
          + '. The judges\' session records, which name each of these files as their output, are in `'
          + str(RECORDS / 'logs') + '/adjudication_randfull/`, `adjudication_locked/` and `adjudication_rand/`; the '
          f'random test\'s refusal log, `{inp["refusal_log_randfull"]["path"]}`, is read for the undecided pairs of (e).',
          '- What ties a verdict to a stored value: `claims_map.jsonl` and `values.json` in `' + str(RECORDS)
          + '/score_randfull/private/`, `score_locked/private/` and `score_rand/private/`.', '']

    L += ['## Method', '',
          '- Papers with a wrong value per side, and the exact two-sided sign test, with stats.py\'s own functions. The sign '
          'test uses only the papers where one side alone holds a wrong value; papers where both sides do are ties and left '
          'out, and the tables say so wherever there are any. Every analysis is given the three ways: '
          + '; '.join(WAY_SHORT[w] for w in W) + '.',
          f'- (a) uses the kit\'s own sensitivity file. Of the {tw["listed"]} papers read again, '
          f'{tw["among_the_83_analysed"]} were among the 83 analysed (the other {len(tw["not_analysed"])} had already left '
          'the set: ' + ', '.join(f'{v} {REASON_WORDS.get(k, k)}' for k, v in sorted(tw['not_analysed_by_reason'].items()))
          + f'), so {tw["read_once_analysed"]} remain. Their counts are checked equal to the locked test\'s, paper by paper. '
          f'The kit\'s rule for intervals is applied as the kit applies it: plain minus CatLog gets an interval only when at '
          f'least {out["checks"]["kit_min_wrong_papers"]} papers hold a wrong value on one side only.',
          '- (c) first replays the kit\'s rule (two judges, a third on a split) from the judges\' verdict files; it gives '
          'every paper\'s count in the three results files. Then every claim is ruled again: stricter, wrong only when both '
          'first judges called it wrong; looser, wrong when any judge did. The 34 unit changes are set claim by claim.',
          '- (d) uses the real claims both first judges ruled (planted errors left out). Two classes: wrong (any of the '
          'seven error verdicts) against not wrong (supported or cannot decide). The kit\'s own kappa uses three classes '
          '(supported, wrong, cannot decide); both are given, labelled.',
          '- (e) uses the sampled agreeing pairs (two claims each, one per side). A pair counts as wrong for both readings '
          'when both its claims were ruled wrong. Bounds are exact one-sided 95% (Clopper-Pearson), multiplied by all '
          'agreeing pairs of the test. Over both tests the bound is exact for a sample drawn separately in each test.', '']

    # ---- (a) to (c): one table
    notes = Notes('RS')
    rmark = notes.mark('Registered before judging: these counts are the kit\'s report of the sensitivity analysis. The P '
                       'value and every other cell of the table were computed after both results.')
    L += ['## (a) to (c): papers with a wrong value, plain reading against CatLog', '',
          'Each cell: papers with a wrong value (wrong values in brackets), plain reading vs CatLog, then the exact two-sided '
          'sign test. Where some papers hold a wrong value on both sides, the cell also gives the papers where only one '
          'side holds one: the sign test uses those, and leaves the others out as ties.', '',
          '| Analysis | Papers | ' + ' | '.join(WAY_SHORT[w] for w in W) + ' |', '|---|---|---|---|---|']
    for key in ('both_tests', 'random_alone', 'locked_alone', 'a_locked_read_once', 'a_both_tests_read_once',
                'b_first_judging_both_tests', 'b_first_judging_read_once', 'c_strict_both_tests', 'c_loose_both_tests',
                'c_strict_random', 'c_strict_locked', 'c_loose_random', 'c_loose_locked'):
        a = A[key]
        n = a['ways'][W[0]]['papers_with_a_wrong_value']['papers']
        cells = [cell(a['ways'][w], rmark if (key == 'a_locked_read_once' and w == 'as_printed') else '') for w in W]
        L.append(f'| {a["label"]} | {n} | ' + ' | '.join(cells) + ' |')
    L += [''] + notes.lines() + ['']

    lk = A['locked_alone']['ways']['as_printed']['papers_with_a_wrong_value']
    ch = change
    seeds = ch['unit_changes_right']['other_seeds']
    L += ['- (a) Leaving out the 31 takes out ' + ' and '.join(
              f'{len(left[s])} of {SIDE[s]}\'s {lk[s]["papers_with_a_wrong_value"]} papers with a wrong value in the locked '
              'test' + (f' ({"; ".join(f"{p}, {k} values" for p, k in left[s].items())})' if left[s] else '')
              for s in SOURCES) + '. Both papers of the 34 unit changes were read once.',
          '- (a) Over both tests, the count without the 31 is weaker than the paper\'s in every way: ' + '; '.join(
              f'{WAY_SHORT[w].split(" ")[0]} {ch[w]["reported"]["plain_only"]} vs {ch[w]["reported"]["catlog_only"]}, '
              f'*P* = {fmt_p(ch[w]["reported"]["p"])}, becomes {ch[w]["without_the_31"]["plain_only"]} vs '
              f'{ch[w]["without_the_31"]["catlog_only"]}, *P* = {fmt_p(ch[w]["without_the_31"]["p"])}' for w in W)
          + '. With the 34 counted as right, the interval for plain minus CatLog now reaches below zero '
          f'({fmt_signed(ch["unit_changes_right"]["without_the_31"]["bootstrap"][1])} to '
          f'{fmt_signed(ch["unit_changes_right"]["without_the_31"]["bootstrap"][2])} per 1,000, against '
          f'{fmt_signed(ch["unit_changes_right"]["reported"]["bootstrap"][1])} to '
          f'{fmt_signed(ch["unit_changes_right"]["reported"]["bootstrap"][2])}). With {seeds["n"]} other seeds '
          f'({seeds["seeds"][0]} to {seeds["seeds"][1]}) its lower limit runs from {fmt_signed(seeds["lo_range"][0])} to '
          f'{fmt_signed(seeds["lo_range"][1])}, at or below zero with {seeds["seeds_with_lo_at_or_below_zero"]} of them.',
          f'- (a) The kit\'s report prints no interval for the {reg["papers"]} papers. Its results.json holds one for way '
          f'(i), {fmt_signed(reg["interval_in_results_json_outside_the_rule"]["lo"])} to '
          f'{fmt_signed(reg["interval_in_results_json_outside_the_rule"]["hi"])} per 1,000, which stats.py\'s bootstrap '
          'reproduces; it falls outside the kit\'s rule, and nothing here uses it.']
    nd = collections.Counter((d['test'], d['source']) for d in diffs)
    npap = collections.defaultdict(set)
    for d in diffs:
        npap[d['test']].add(d['pmid'])
    ur = [x for t in ('random', 'locked') for x in undecided_real[t]['by_paper_and_reason']]
    L += [f'- (c) Only {len(diffs)} claims are ruled differently by the three rules, in '
          + ' and '.join(f'{len(npap[t])} paper{"s" if len(npap[t]) != 1 else ""} of the {t} test '
                         f'({", ".join(sorted(npap[t], key=lambda p: p.zfill(12)))})'
                         for t in ('random', 'locked') if npap[t])
          + ': ' + '; '.join(f'{t} test, {SIDE[s]} {nd[(t, s)]}' for t in ('random', 'locked') for s in SOURCES
                             if nd[(t, s)])
          + '. They are listed in `rule_differences.tsv` with the three judges\' verdicts. The '
          + f'{sum(undecided_real[t]["claims"] for t in undecided_real)} real claims left at cannot decide carry no error '
          'vote, so no rule changes them: ' + '; '.join(f'{x["claims"]} in {x["pmid"]} ({x["reason"]})' for x in ur) + '.']
    for key, word in (('c_loose_both_tests', 'looser rule'), ('b_first_judging_both_tests', 'first judging')):
        ties = [w for w in W if A[key]['ways'][w]['sign_test']['both']]
        if ties:
            L.append(f'- ({key[0]}) With the {word}, ' + '; '.join(
                f'{WAY_SHORT[w].split(" ")[0]} {papers_cell(A[key]["ways"][w])} papers with a wrong value, of which '
                f'{A[key]["ways"][w]["sign_test"]["both"]} on both sides, so the sign test uses '
                f'{A[key]["ways"][w]["sign_test"]["plain_only"]} vs {A[key]["ways"][w]["sign_test"]["catlog_only"]}'
                for w in ties) + '.')
    L += ['']

    # ---- Table 1b rows
    names = {'as_printed': 'Wrong, as the judges ruled', 'unit_changes_right': 'Right',
             'own_numbers_both': "Right, and the plain reading's 34 as-printed values of the same cells wrong"}
    head = ('| How the 34 are counted | Papers with a wrong value (wrong values), plain reading | Papers with a wrong '
            'value (wrong values), CatLog | Exact sign test on papers, two-sided *P* | Largest *P* with any one paper '
            'left out | Plain reading minus CatLog, wrong per 1,000 (95% interval) |')
    a199 = A['a_both_tests_read_once']
    t1 = Notes()
    L += ['## Rows for Table 1b', '',
          f'Sub-heading: *Without the {tw["among_the_83_analysed"]} analysed papers that CatLog\'s side read again while a '
          'stopped launch\'s folders remained (the exclusion was chosen before judging; this count was not), '
          f'{a199["ways"][W[0]]["papers_with_a_wrong_value"]["papers"]} papers.* The random test\'s 147 and the '
          f'{tw["read_once_analysed"]} papers of the locked test left. Same columns as Table 1b; the bootstrap is '
          'stats.py\'s (B 10,000, seed 20261031, every stored value).', '', head, '|---|---|---|---|---|---|']
    for w in W:
        L.append(t1b_row(names[w], a199['ways'][w], t1))
    L += ['', f'In the second row the interval reaches below zero with all {seeds["n"]} other seeds tried '
              f'({seeds["seeds"][0]} to {seeds["seeds"][1]}; lower limits {fmt_signed(seeds["lo_range"][0])} to '
              f'{fmt_signed(seeds["lo_range"][1])}).' if seeds['seeds_with_lo_at_or_below_zero'] == seeds['n'] else
          f'In the second row the lower limit is {fmt_signed(seeds["lo_range"][0])} to {fmt_signed(seeds["lo_range"][1])} '
          f'with {seeds["n"]} other seeds, at or below zero with {seeds["seeds_with_lo_at_or_below_zero"]}.']
    L += ['', 'The same columns for the other analyses, all chosen after both results except the counts marked:', '',
          head.replace('| How the 34 are counted |', '| Analysis | How the 34 are counted |'), '|---|---|---|---|---|---|---|']
    reg_mark = t1.mark('The counts in this row are the registered sensitivity analysis, as the kit\'s report prints them; '
                       'the P values are computed here, after both results.')
    for key, lab in (('a_locked_read_once', f'Locked test alone, without the 31, {reg["papers"]} papers'),
                     ('b_first_judging_both_tests', "Random test's first judging, both tests, 230 papers"),
                     ('c_strict_both_tests', 'Stricter rule, both tests, 230 papers'),
                     ('c_loose_both_tests', 'Looser rule, both tests, 230 papers')):
        for w in W:
            ex = reg_mark if (key == 'a_locked_read_once' and w == 'as_printed') else ''
            L.append(t1b_row(names[w], A[key]['ways'][w], t1, ex).replace('| ', f'| {lab} | ', 1))
    L += [''] + t1.lines() + ['']

    # ---- (d)
    tl = {'random': 'Random test, second judging', 'locked': 'Locked test',
          'random_first': 'Random test, first judging (same 147 papers)'}
    L += ['## (d) The first two judges\' agreement on whether a value is wrong', '',
          '| Judging | Claims both first judges ruled | Called wrong by either | By both | Kappa, wrong against not wrong '
          '(two classes) | Positive agreement | Negative agreement | Kappa, three classes (the kit\'s, as the reports print '
          'it) |', '|---|---|---|---|---|---|---|---|']
    for t in ('random', 'locked'):
        x = agree[t]['all_real_claims']
        L.append(f'| {tl[t]} | {x["claims"]:,} | {x["either_error"]} | {x["both_error"]} | {x["kappa_error_class"]:.3f} | '
                 f'{x["positive_agreement"]:.3f} | {x["negative_agreement"]:.4f} | {x["kappa_three_classes"]:.3f} |')
    lk_cd = agree['locked']['all_real_claims']['claims_with_a_cannot_decide_vote']
    rf = agree['random_first']['all_real_claims']
    L += ['',
          '- Of the claims either first judge called wrong, both did for ' + ' and '.join(
              f'{agree[t]["all_real_claims"]["both_error"]} of {agree[t]["all_real_claims"]["either_error"]} '
              f'({tl[t].lower()})' for t in ('random', 'locked')) + '; where both did, they gave the same error verdict in '
          + ' and '.join(f'{agree[t]["all_real_claims"]["both_error_same_verdict"]} of {agree[t]["all_real_claims"]["both_error"]}'
                         for t in ('random', 'locked')) + '.',
          ('- In the locked test neither first judge said cannot decide on a claim both ruled, so its two kappas are the '
           'same number.' if lk_cd == 0 else
           f'- In the locked test {lk_cd} claims both ruled have a cannot-decide vote.'),
          '- The paper\'s full Methods print the three-class kappa: '
          + ', '.join(out['checks']['three_class_kappas_equal_the_methods'][:2]) + ' and '
          + out['checks']['three_class_kappas_equal_the_methods'][2]
          + ' (the first judging on its 150 papers, the random test\'s second judging, the locked test). The two-class '
          'kappa is another figure, so the two are labelled apart.',
          '- On the disputed claims alone (sampled agreeing pairs left out): ' + '; '.join(
              f'{tl[t].lower()}, two-class kappa {agree[t]["disputed_claims"]["kappa_error_class"]:.3f} and positive agreement '
              f'{agree[t]["disputed_claims"]["positive_agreement"]:.3f} on {agree[t]["disputed_claims"]["claims"]:,} claims'
              for t in ('random', 'locked')) + '.',
          f'- For reference, the random test\'s first judging on the same 147 papers ({rf["claims"]:,} claims): two-class '
          f'kappa {rf["kappa_error_class"]:.3f}, positive agreement {rf["positive_agreement"]:.3f}, three-class kappa '
          f'{rf["kappa_three_classes"]:.3f} (on its own 150 papers, '
          f'{out["agreement_first_judging_own_report_150_papers"]["kappa_three_classes"]:.3f}, as above). In that judging '
          'the judges were shown less of each record.', '']

    # ---- (e)
    L += ['## (e) Values both readings stored: how many could be ruled wrong on both sides', '',
          '| Test | Agreeing pairs | Sampled | Both claims decided | Ruled wrong on both sides | Upper limit on the share '
          '(one-sided 95%) | At most, pairs that would be ruled wrong on both sides | Per 1,000 stored values, plain reading '
          '/ CatLog |', '|---|---|---|---|---|---|---|---|']
    for t, lab in (('locked', 'Locked test'), ('random', 'Random test')):
        e = agp[t]['both_claims_wrong']
        L.append(f'| {lab} | {agp[t]["agreeing_pairs"]:,} | {agp[t]["sampled_pairs"]:,} | {e["of"]:,} | {e["found"]} | '
                 f'{100 * e["upper_share"]:.2f}% | {e["upper_count_all_pairs"]:.1f} | '
                 f'{e["upper_per_1000_stored"]["plain"]:.2f} / {e["upper_per_1000_stored"]["catlog"]:.2f} |')
    pe = agp['both_tests_stratified']['both_claims_wrong']
    L.append(f'| Both tests (sample drawn in each test) | {pe["agreeing_pairs"]:,} | {pe["sampled_pairs"]:,} | {pe["of"]:,} | '
             f'{pe["found"]} | {100 * pe["upper_count_all_pairs"] / pe["agreeing_pairs"]:.2f}% of all pairs | '
             f'{pe["upper_count_all_pairs"]:.1f} | {pe["upper_per_1000_stored"]["plain"]:.2f} / '
             f'{pe["upper_per_1000_stored"]["catlog"]:.2f} |')
    ee = {t: agp[t]['either_claim_wrong'] for t in ('locked', 'random')}
    pe2 = agp['both_tests_stratified']['either_claim_wrong']
    ww = [dict(x, test=t) for t in ('random', 'locked') for x in agp[t]['sampled_pairs_with_a_claim_ruled_wrong']]
    und = agp['random']
    silent = collections.Counter(j for x in und['undecided_claims'] for j in x['no_verdict_from'])
    sess = sorted({c['check'] for x in und['undecided_claims'] for v in x['sessions_of_judges_without_a_verdict'].values()
                   for c in v})
    refs = sorted({n for x in und['undecided_claims'] for n in x['refusals_logged'].values()})
    times = {1: 'once', 2: 'twice'}.get(refs[0], f'{refs[0]} times') if len(refs) == 1 else None
    L += ['',
          '- Over both tests the exact bound equals the random test\'s alone: the locked test sampled a larger share of its '
          f'pairs ({agp["locked"]["sampled_pairs"]} of {agp["locked"]["agreeing_pairs"]:,} against '
          f'{agp["random"]["sampled_pairs"]} of {agp["random"]["agreeing_pairs"]:,}).',
          '- Counting a pair when either of its claims was ruled wrong: ' + '; '.join(
              f'{t} test {ee[t]["found"]} of {ee[t]["of"]:,}, at most {ee[t]["upper_count_all_pairs"]:.1f}' for t in ee)
          + f'; both tests at most {pe2["upper_count_all_pairs"]:.1f} ({pe2["upper_per_1000_stored"]["plain"]:.2f} and '
          f'{pe2["upper_per_1000_stored"]["catlog"]:.2f} per 1,000 stored values, plain reading and CatLog). '
          + ' '.join(f'The one such pair ({x["test"]} test, {x["pmid"]}) paired two numbers that differ by '
                     f'{100 * abs(x["plain_over_catlog"] - 1):.1f}%; only {SIDE[x["ruled_wrong"][0]]}\'s was ruled wrong '
                     f'({x["verdicts"][x["ruled_wrong"][0]].replace("_", " ")}).' for x in ww
                     if len(ww) == 1 and len(x['ruled_wrong']) == 1),
          f'- In {und["sampled_pairs_with_a_claim_undecided"]} sampled pairs of the random test '
          f'({", ".join(und["undecided_pairs_papers"])}), '
          + ('both claims are' if und['sampled_pairs_with_both_claims_undecided'] == und['sampled_pairs_with_a_claim_undecided']
             else 'a claim is') + ' at cannot decide'
          + (f': judge 2 gave no verdict on them. Its step on that part of the paper was refused by the safety filter '
             f'{times} (the kit\'s refusal log, `refused.tsv` in the session records), and its session record reads '
             f'"{"; ".join(sess)}"' if set(silent) == {'j2'} and sess and times and refs[0] > 0 else
             f': judge 2 gave no verdict on them (its session on that part of the paper is recorded as '
             f'"{"; ".join(sess)}")' if set(silent) == {'j2'} and sess else '')
          + '. They are left out of the decided pairs.',
          '- What the bound covers: only what these judges would rule wrong on both sides. The judges were agents of the '
          'readers\' model. They ruled against the printed page, so a misprint both readings copied as printed counts as '
          'supported. They saw each sampled pair as two claims, shown with the same number in '
          + ' and '.join(f'{agp[t]["sampled_pairs_shown_with_the_same_number"]} of {agp[t]["sampled_pairs"]} pairs '
                         f'({t} test)' for t in ('random', 'locked'))
          + ', a limit the kit states in advance ("'
          + VISIBLE_PAIRING + '"), which can make a judge lenient on values the readings agree on. Values both readings '
          'missed are outside the bound. The binomial bound is also conservative for a sample drawn without replacement.',
          '']

    L += ['## Files', '',
          '- `sensitivity.py`: the script. `sensitivity.json`: every number with its definition, the checks and the input '
          'hashes. `rule_differences.tsv`: the claims whose ruling depends on the rule, with the three judges\' verdicts.',
          '', '## Rerun', '', '```', f'cd {HERE}', 'python3 -I -B sensitivity.py', '```', '',
          'It needs numpy and scipy, reads only the files listed under Inputs, writes only the three files in this folder, '
          'and takes about ten seconds.', '']
    return '\n'.join(L)


if __name__ == '__main__':
    main()
