#!/usr/bin/env python3
"""Cost per paper and per value: CatLog's frozen run against the plain reading, on the locked test's 83 papers.

Records only: nothing is read again, judged or run, and nothing goes over the network. The script reads only
~/Documents/catlog-v2 and ~/Documents/kinetics-reading; it opens no transcript (their paths are only named).

Plain reading: each analysed paper's session records in kinetics-reading/records/logs/A0-locked/ (<PMID>.a1.json, and
.a2.json where the kit's one retry ran): tokens per model (result.modelUsage), total_cost_usd, seconds, command. The
kit's audit of those sessions (records/audit/A0-locked/audit.json, read from their transcripts once per message id)
is the check of the records' tokens. The random test's A0-rand/ records are a second set, plain side only.

CatLog: every agent of the frozen run (records/logs/A6-locked/<launch>/agents.json: readers, verifiers, missed-values
verifiers, the workflow's retries and refused agents, and each launch's own session). Each agent's tokens, model and
times come from the kit's audit of the run (records/audit/A6-locked/audit.json: the four usage fields counted once per
message id from the transcript that agents.json names, as rethink/r01_tokens.py counts), checked against tokens.json
and against each launch's session.json. An agent's cache writes are 5-minute writes and a launch session's are 1-hour
writes; session.json's split checks that rule. A paper's cost is its agents in the launch whose rows were kept (the last
launch that ran agents for it, the kit's common_w1.a6_kept_agents; every such launch completed) plus an equal share of
that launch's own session over the papers its launch line names. Earlier launches (three that a usage limit stopped,
one whose own session was refused) and earlier plain sessions are reported apart.

Prices: list prices, i.e. Claude Code's own cost figures (costBasis 'list' in every record), whose price table is solved
here from the records and checked against every one of them (each cache write at the price of its lifetime); and, for
comparison with the catalogue's earlier estimate, the prices and cache rule of paper/evidence/rethink_20261101/
r01b_cost.py and cost_summary.json, read from those files (every cache write at the 5-minute rate).

Run: python3 -I -B cost.py   Writes next to itself: README.md, results.json, per_paper_locked.tsv,
per_agent_locked.tsv, launch_check.tsv, per_paper_random.tsv, production_roles.tsv. Stops on any failed check.
"""
import ast
import csv
import glob
import hashlib
import json
import os
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
CATLOG = '<the CatLog folder>'
KIT = '<the kit folder>'
EV = os.path.join(CATLOG, 'paper', 'evidence')
LOCKED = os.path.join(EV, 'locked_test_20261109', 'result', 'results.json')
READ_TWICE = os.path.join(EV, 'locked_test_20261109', 'result', 'locked_copy_read_twice.txt')
RANDOM = os.path.join(EV, 'random_papers_20261104', 'full_record', 'results.json')
RETHINK = os.path.join(EV, 'rethink_20261101')
COST_SUMMARY = os.path.join(RETHINK, 'cost_summary.json')
R01B = os.path.join(RETHINK, 'r01b_cost.py')
TOKENS = os.path.join(RETHINK, 'cache', 'tokens_per_agent.tsv')
PIPELINE = os.path.join(RETHINK, 'pipeline_stats.json')
REPRINT_HANDOFF = os.path.join(CATLOG, 'work', 'reprint_sweep', 'HANDOFF.md')
LOGS = os.path.join(KIT, 'records', 'logs')
A0L, A0R, A6L = (os.path.join(LOGS, x) for x in ('A0-locked', 'A0-rand', 'A6-locked'))
AUDIT = os.path.join(KIT, 'records', 'audit')
A6_AUDIT, A6_TOKENS = os.path.join(AUDIT, 'A6-locked', 'audit.json'), os.path.join(AUDIT, 'A6-locked', 'tokens.json')
A0L_AUDIT, A0R_AUDIT = os.path.join(AUDIT, 'A0-locked', 'audit.json'), os.path.join(AUDIT, 'A0-rand', 'audit.json')
PROJECTS = os.path.expanduser('~/.claude/projects')  # only to shorten the transcript paths the records name; never read
SESSION_RECORD = re.compile(r'^(?P<pmid>[^.]+)\.a(?P<k>\d+)(?P<b>b?)\.json$')  # common_w1.SESSION_RECORD
LAUNCH_DIR = re.compile(r'main|redo|(?:redo-)?more-\d+')  # common_w1.A6_LAUNCH
RUN_ID = re.compile(r'wf_[0-9a-f]{8}-[0-9a-f]{3}')  # a workflow run id as the handoff and the transcript paths write it
MODEL = 'claude-opus-5-5'
SEED, B = 20261031, 10000  # the locked test's paired paper bootstrap: seed and resamples
KEYS = ('in', 'cw', 'w5', 'w1', 'cr', 'out')  # input, cache write (all), 5-minute and 1-hour writes, cache read, output
CHECKS = Counter()  # every assertion that passed, in words, with how many times it was tested


def check(cond, what, group=None):
    if not cond:
        sys.exit(f'CHECK FAILED: {what}')
    CHECKS[group or what] += 1


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def tok0():
    return dict.fromkeys(KEYS, 0)


def tadd(a, b, f=1):
    for k in KEYS:
        a[k] += b[k] * f


def total_tokens(t):
    return t['in'] + t['cw'] + t['cr'] + t['out']


def parse_ts(s):
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def flag_value(cmd, flag):
    cmd = list(cmd or [])
    return cmd[cmd.index(flag) + 1] if flag in cmd and cmd.index(flag) + 1 < len(cmd) else None


# ---------------------------------------------------------------- prices
def rethink_prices():
    """r01b_cost.py's PRICE and WRITE, read from its source, and the same as cost_summary.json states."""
    tree = ast.parse(open(R01B).read())
    price = write = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == 'PRICE':
                price = ast.literal_eval(node.value)
            elif node.targets[0].id == 'WRITE':
                write = ast.literal_eval(node.value)
    cs = json.load(open(COST_SUMMARY))
    check({k: list(v) for k, v in price.items()} == cs['prices_per_mtok'] and write == cs['cache_write_multiplier'],
          'r01b_cost.py PRICE and WRITE equal cost_summary.json prices_per_mtok and cache_write_multiplier')
    return price, write


PRICE, WRITE = rethink_prices()


def cost_r01b(model, t):
    """r01b_cost.py's rule: input, output and cache read at its price for the model; every cache write at WRITE x input,
    whatever its lifetime (its docstring: '(5 min) at 1.25 x input for all')."""
    i, o, cr = PRICE[model]
    return (t['in'] * i + t['cw'] * i * WRITE + t['cr'] * cr + t['out'] * o) / 1e6


def solve(rows):
    """Least squares in exact fractions: prices (per million tokens) that best give each row's costUSD from its token
    counts. rows: [(x tuple of 5 counts: in, out, cr, w5, w1), costUSD]. Columns that are zero in every row cannot be
    solved: None."""
    cols = [j for j in range(5) if any(x[j] for x, _ in rows)]
    n = len(cols)
    A = [[Fraction(0)] * (n + 1) for _ in range(n)]
    for x, y in rows:
        xs = [Fraction(x[j]) for j in cols]
        fy = Fraction(y) * 10 ** 6
        for a in range(n):
            for b in range(n):
                A[a][b] += xs[a] * xs[b]
            A[a][n] += xs[a] * fy
    for c in range(n):  # Gauss-Jordan
        piv = next(r for r in range(c, n) if A[r][c] != 0)
        A[c], A[piv] = A[piv], A[c]
        for r in range(n):
            if r != c and A[r][c] != 0:
                f = A[r][c] / A[c][c]
                A[r] = [A[r][k] - f * A[c][k] for k in range(n + 1)]
    sol = [None] * 5
    for c, j in enumerate(cols):
        sol[j] = round(float(A[c][n] / A[c][c]), 6)
    return sol


# ---------------------------------------------------------------- records
def plain_session(path):
    d = json.load(open(path))
    r = d.get('result') or {}
    per, mu = {}, r.get('modelUsage') or {}
    for model, u in mu.items():
        per[model] = {'in': int(u.get('inputTokens') or 0), 'cw': int(u.get('cacheCreationInputTokens') or 0),
                      'w5': int(u.get('cacheCreationEphemeral5mInputTokens') or 0),
                      'w1': int(u.get('cacheCreationEphemeral1hInputTokens') or 0),
                      'cr': int(u.get('cacheReadInputTokens') or 0), 'out': int(u.get('outputTokens') or 0),
                      'costUSD': u.get('costUSD'), 'basis': u.get('costBasis'), 'provider': u.get('provider'),
                      'split_from': 'modelUsage'}
        if 'cacheCreationEphemeral5mInputTokens' not in u and 'cacheCreationEphemeral1hInputTokens' not in u:
            # Claude Code 2.1.309 (the random test's sessions) gives no 5-minute/1-hour split per model; a session of
            # one model has it in result.usage, which then holds the same totals
            cc, us = (r.get('usage') or {}).get('cache_creation') or {}, r.get('usage') or {}
            one = len(mu) == 1 and int(us.get('cache_creation_input_tokens') or -1) == per[model]['cw'] and cc
            per[model]['w5'] = int(cc.get('ephemeral_5m_input_tokens') or 0) if one else None
            per[model]['w1'] = int(cc.get('ephemeral_1h_input_tokens') or 0) if one else None
            per[model]['split_from'] = 'result.usage' if one else None
        if per[model]['split_from']:
            check(per[model]['w5'] + per[model]['w1'] == per[model]['cw'],
                  f'{path}: cache writes split into 5-minute and 1-hour', 'plain records: every session\'s cache '
                  'writes split into 5-minute and 1-hour ones (from modelUsage, or result.usage for a one-model session)')
    return {'path': path, 'label': d.get('label'), 'ok': d.get('ok'), 'model': d.get('model'),
            'session_id': d.get('session_id'), 'command': d.get('command') or [],
            'seconds': d.get('seconds'), 'total_cost_usd': r.get('total_cost_usd'), 'per': per,
            'usage': r.get('usage') or {}, 'transcript': d.get('transcript'), 'switched': d.get('switched'),
            'stop_reason': r.get('stop_reason'), 'safety_stops': r.get('safety_stops') or 0,
            'check': d.get('check'), 'has_result': bool(r)}


def plain_steps(run_dir):
    """{pmid: [session records of the kept invocation, a1 first]} from the run folder's top level, and {pmid: [records
    of earlier invocations]} from its earlier/<step>/<k>/ (claude_session.keep_earlier)."""
    top = defaultdict(list)
    for f in os.listdir(run_dir):
        m = SESSION_RECORD.match(f)
        if m:
            top[m['pmid']].append((int(m['k']), m['b'], os.path.join(run_dir, f)))
    earlier = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(run_dir, 'earlier', '*', '*', '*.json'))):
        m = SESSION_RECORD.match(os.path.basename(f))
        if m:
            earlier[m['pmid']].append(f)
    return {p: [plain_session(x[2]) for x in sorted(v)] for p, v in top.items()}, \
           {p: [plain_session(f) for f in v] for p, v in earlier.items()}


def session_costs(s):
    """A plain session's cost at list prices (Claude Code's own total_cost_usd) and under the r01b rule (its tokens)."""
    return (s['total_cost_usd'] or 0.0), sum(cost_r01b(m, t) for m, t in s['per'].items())


def session_tokens(s):
    t = tok0()
    for x in s['per'].values():
        tadd(t, x)
    return t


def four(u):
    """The four usage fields of a record's result.usage (or an audit row, which uses the same names)."""
    return tuple(int(u.get(k) or 0) for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens',
                                              'output_tokens'))


# ---------------------------------------------------------------- statistics
def quart(xs):
    xs = sorted(xs)
    if len(xs) < 2:
        return None
    q1, q2, q3 = statistics.quantiles(xs, n=4, method='inclusive')
    return {'n': len(xs), 'median': q2, 'q1': q1, 'q3': q3, 'mean': statistics.mean(xs), 'min': xs[0],
            'max': xs[-1], 'sum': sum(xs)}


def boot_ratio(papers, num, den, num_n=None, den_n=None):
    """Paired paper bootstrap (B, SEED) of sum(num)/sum(den), or of (sum(num)/sum(num_n)) / (sum(den)/sum(den_n))
    for a ratio of pooled costs per value. Percentile 95% interval."""
    rng = random.Random(SEED)
    n, out = len(papers), []
    for _ in range(B):
        s = [papers[rng.randrange(n)] for _ in range(n)]
        a, b = sum(num[p] for p in s), sum(den[p] for p in s)
        if num_n is not None:
            an, bn = sum(num_n[p] for p in s), sum(den_n[p] for p in s)
            if not an or not bn or not b:
                continue
            out.append((a / an) / (b / bn))
        else:
            out.append(a / b)
    out.sort()
    return {'lo': out[int(0.025 * len(out))], 'hi': out[int(0.975 * len(out)) - 1], 'B': len(out), 'seed': SEED}


def rel(path):
    return os.path.relpath(path, PROJECTS) if str(path).startswith(PROJECTS) else path


# ================================================================ inputs: the two tests' results
L = json.load(open(LOCKED))
R = json.load(open(RANDOM))
papers = sorted(L['per_paper'])
pset = set(papers)
tri = L['triage']
check(len(papers) == 83 == L['papers_used'] == tri['papers_analysed'], 'locked test: 83 papers analysed')
check(tri['papers_listed'] == 119, 'locked test: 119 papers listed')
check(tri['left_out_by_reason'] == {'refused (plain)': 12, 'catlog rule_broken': 7, 'refused (catlog)': 17},
      'locked test: left out 12 plain refused, 17 CatLog refused, 7 CatLog rule broken')
EXITS_REFUSED = tri['left_out_by_reason']['refused (plain)'] + tri['left_out_by_reason']['refused (catlog)']
EXITS = sum(tri['left_out_by_reason'].values())
ps = L['per_source']
check(ps['plain']['values'] == 1473 and ps['catlog']['values'] == 1400, 'locked test: values 1,473 plain and 1,400 CatLog')
check(ps['plain']['wrong'] == 15 and ps['catlog']['wrong'] == 34, 'locked test: wrong 15 plain and 34 CatLog')
check(ps['plain']['cannot_decide'] == 0 and ps['catlog']['cannot_decide'] == 0, 'locked test: no value left undecided')
check(ps['plain']['values_agreed_not_judged'] == ps['catlog']['values_agreed_not_judged'] == 795
      and ps['plain']['sample']['wrong'] == ps['catlog']['sample']['wrong'] == 0
      and ps['plain']['sample']['of'] == ps['catlog']['sample']['of'] == 500,
      'locked test: 795 agreeing values per side not judged; 0 of 500 sampled agreeing pairs wrong')
for s in ('plain', 'catlog'):
    check(sum(L['per_paper'][p][s]['values'] for p in papers) == ps[s]['values']
          and sum(L['per_paper'][p][s]['wrong'] for p in papers) == ps[s]['wrong'],
          f'locked test: per-paper values and wrong values add up to the {s} totals')
VAL = {s: {p: L['per_paper'][p][s]['values'] for p in papers} for s in ('plain', 'catlog')}
SUP = {s: {p: L['per_paper'][p][s]['values'] - L['per_paper'][p][s]['wrong'] for p in papers} for s in ('plain', 'catlog')}
rpapers = sorted(R['per_paper'])
rps = R['per_source']
check(len(rpapers) == 147 == R['papers_used'], 'random test: 147 papers analysed')
check(rps['plain']['wrong'] == 42 and rps['catlog']['wrong'] == 6, 'random test: wrong 42 plain and 6 CatLog')
check(ps['plain']['values'] + rps['plain']['values'] == 6003 and ps['catlog']['values'] + rps['catlog']['values'] == 5790,
      'both tests: 6,003 plain and 5,790 CatLog values')
check(sum(R['per_paper'][p]['plain']['values'] for p in rpapers) == rps['plain']['values'],
      'random test: per-paper plain values add up to its total')

# ================================================================ list prices: Claude Code's own table, solved from the records
obs = defaultdict(list)  # model -> [(x, costUSD, where)]
record_files = sorted(glob.glob(os.path.join(A0L, '*.json')) + glob.glob(os.path.join(A0L, 'earlier', '*', '*', '*.json'))
                      + glob.glob(os.path.join(A0R, '*.json')) + glob.glob(os.path.join(A0R, 'earlier', '*', '*', '*.json')))
record_files = [f for f in record_files if SESSION_RECORD.match(os.path.basename(f))]
launch_names = sorted((d for d in os.listdir(A6L) if LAUNCH_DIR.fullmatch(d) and os.path.isdir(os.path.join(A6L, d))),
                      key=lambda d: (d.startswith('redo'), int(d.split('-')[-1]) if d.split('-')[-1].isdigit() else 0))
check(launch_names == ['main'] + [f'more-{k}' for k in range(1, 12)], 'A6-locked: launches main and more-1 to more-11, no redo')
sessions = {d: json.load(open(os.path.join(A6L, d, 'session.json'))) for d in launch_names}
for f in record_files:
    s = plain_session(f)
    for m, t in s['per'].items():
        check(t['split_from'] is not None, f'{f}: cache-write split known', 'plain records: the cache-write split of '
              'every session is known')
        check(t['basis'] == 'list' and t['provider'] == 'firstParty', f'{f}: costBasis list',
              'records: every priced model entry has costBasis "list" and provider "firstParty"')
        obs[m].append(((t['in'], t['out'], t['cr'], t['w5'], t['w1']), t['costUSD'], f))
for d in launch_names:
    for m, u in (sessions[d].get('modelUsage') or {}).items():
        check(u.get('costBasis') == 'list' and u.get('provider') == 'firstParty', f'{d}: costBasis list',
              'records: every priced model entry has costBasis "list" and provider "firstParty"')
        obs[m].append(((u['inputTokens'], u['outputTokens'], u['cacheReadInputTokens'],
                        u['cacheCreationEphemeral5mInputTokens'], u['cacheCreationEphemeral1hInputTokens']),
                       u['costUSD'], os.path.join(A6L, d, 'session.json')))
CC, cc_fit = {}, {}
for m, rows in sorted(obs.items()):
    sol = solve([(x, y) for x, y, _ in rows])
    worst = max(abs(sum((x[j] * sol[j] if sol[j] is not None else 0) for j in range(5)) / 1e6 - y) for x, y, _ in rows)
    check(worst < 1e-6, f'one price table gives every record\'s costUSD for {m} (largest difference {worst:.2e} USD)')
    CC[m] = sol
    cc_fit[m] = {'records': len(rows), 'largest_difference_usd': worst,
                 'records_with_tokens': [sum(1 for x, _, _ in rows if x[j]) for j in range(5)]}
check(CC[MODEL][4] is not None and CC[MODEL][3] is not None, 'Opus 5.5 5-minute and 1-hour cache-write prices both solved')
W5_X, W1_X = CC[MODEL][3] / CC[MODEL][0], CC[MODEL][4] / CC[MODEL][0]  # the write multipliers of the list prices


def cost_list(model, t):
    p = CC[model]
    parts = [(t['in'], p[0]), (t['out'], p[1]), (t['cr'], p[2]), (t['w5'], p[3]), (t['w1'], p[4])]
    for n, price in parts:
        check(not n or price is not None, f'a price for every token kind {model} uses',
              'list prices: every token kind used has a solved price')
    return sum(n * (price or 0) for n, price in parts) / 1e6


check(PRICE[MODEL][0] == CC[MODEL][0] and PRICE[MODEL][1] == CC[MODEL][1] and PRICE[MODEL][2] == CC[MODEL][2]
      and CC[MODEL][3] == PRICE[MODEL][0] * WRITE,
      'Opus 5.5: r01b input, output and cache-read prices, and its 1.25 x input cache write, equal the list prices '
      '(5-minute writes)')

# ================================================================ plain reading, locked set
top, earlier = plain_steps(A0L)
aud0l = {a['session_id']: a for a in json.load(open(A0L_AUDIT))['agents']}
plain = {}
for p in papers:
    att = top.get(p) or []
    check(att and att[-1]['ok'] is True, f'plain {p}: the kept invocation ends in a valid read',
          'plain, locked: each analysed paper\'s kept invocation ends in a valid read')
    for s in att:
        check(s['has_result'] and s['model'] == MODEL and not s['switched'] and set(s['per']) <= {MODEL},
              f'plain {p}: every session of the kept invocation ran {MODEL} alone',
              f'plain, locked: every kept session ran {MODEL} alone, no model switch')
        check(flag_value(s['command'], '--model') == MODEL and flag_value(s['command'], '--effort') == 'max',
              f'plain {s["label"]}: command sets --model {MODEL} --effort max',
              'plain, locked: every kept session\'s command sets --model claude-opus-5-5 --effort max')
        check(s['safety_stops'] == 0 and s['stop_reason'] != 'refusal', f'plain {s["label"]}: no refusal',
              'plain, locked: no kept session logged a safety stop')
        check(abs(sum(cost_list(m, t) for m, t in s['per'].items()) - s['total_cost_usd']) < 1e-6,
              f'plain {s["label"]}: the list price table gives its total_cost_usd',
              'plain, locked: the solved list price table gives each kept session\'s total_cost_usd')
        a = aud0l.get(s['session_id'])
        check(a is not None and a['transcript'] == s['transcript'] and four(a) == four(s['usage']),
              f'plain {s["label"]}: the kit\'s audit, from its transcript, gives the record\'s four token counts',
              'plain, locked: for every kept session, the kit\'s audit (its transcript, once per message id) gives the '
              'record\'s four token counts exactly')
    t = tok0()
    for s in att:
        tadd(t, session_tokens(s))
    plain[p] = {'sessions': [s['label'] for s in att], 'retries': len(att) - 1,
                'cost_list': sum(session_costs(s)[0] for s in att), 'cost_r01b': sum(session_costs(s)[1] for s in att),
                'tokens': t, 'seconds': sum(s['seconds'] or 0 for s in att),
                'writes_5m': sum(x['w5'] for s in att for x in s['per'].values()),
                'earlier_sessions': [s['label'] for s in earlier.get(p, [])],
                'earlier_cost_list': sum(session_costs(s)[0] for s in earlier.get(p, [])),
                'earlier_cost_r01b': sum(session_costs(s)[1] for s in earlier.get(p, []))}
check(all(plain[p]['writes_5m'] == 0 for p in papers) and all(plain[p]['tokens']['w1'] == plain[p]['tokens']['cw'] for p in papers),
      'plain, locked: every kept session writes 1-hour cache entries only')
# the whole plain run against the kit's audit: equal, except refused sessions, whose records count more
all_plain = [plain_session(f) for f in record_files if f.startswith(A0L + os.sep)]
plain_audit_equal = plain_audit_more = 0
for s in all_plain:
    a = aud0l.get(s['session_id'])
    check(a is not None, f'{s["path"]}: an audit row', 'plain, locked: every session record has a row in the kit\'s audit')
    rec, au = four(s['usage']), four(a)
    if rec == au:
        plain_audit_equal += 1
    else:
        check(s['stop_reason'] == 'refusal' and all(x >= y for x, y in zip(rec, au)),
              f'{s["path"]}: only a refused session counts more than its transcript',
              'plain, locked: a record counts more tokens than its transcript only for a refused session')
        plain_audit_more += 1
check(len(aud0l) == len(all_plain), 'plain, locked: the kit\'s audit holds every session record and no other')

# ================================================================ CatLog's frozen run, from the kit's audit
A6 = json.load(open(A6_AUDIT))
arow = {}
for a in A6['agents']:
    check((a['launch'], a['label']) not in arow, 'audit.json: one row per launch and label')
    arow[(a['launch'], a['label'])] = a
check(len(arow) == A6['summary']['agents'] == 386, 'audit.json: 386 rows (374 agents and 12 launch sessions)')
check(A6['summary']['tokens_total'] == sum(a['total'] for a in A6['agents'])
      and A6['summary']['usd_total'] == round(sum(a['usd'] for a in A6['agents']), 2),
      'audit.json: the summary\'s tokens_total and usd_total are the sums of its rows')
toks6 = json.load(open(A6_TOKENS))
check(len(toks6) == sum(1 for a in A6['agents'] if a['role'] != 'launch'), 'tokens.json: one row per agent of audit.json')
for t in toks6:
    a = arow.get((t['launch'], t['label']))
    check(a is not None and all(t[k] == a[k] for k in ('pmid', 'role', 'input_tokens', 'cache_creation_input_tokens',
                                                        'cache_read_input_tokens', 'output_tokens', 'total', 'usd',
                                                        'minutes')),
          f'tokens.json {t["label"]}: equal to audit.json', 'tokens.json: every row equals its audit.json row')
agents, launch_info, matched = [], {}, set()
for d in launch_names:
    rows = json.load(open(os.path.join(A6L, d, 'agents.json')))
    lj = json.load(open(os.path.join(A6L, d, 'launch.json')))
    named = [str(x) for x in (lj.get('args') or {}).get('pmids') or lj.get('pmids') or []]
    check(named and len(set(named)) == len(named), f'{d}: the launch line names its papers once each',
          'A6-locked: each launch line names its papers once each')
    check(flag_value(lj.get('command'), '--model') == MODEL and flag_value(lj.get('command'), '--effort') == 'max',
          f'{d}: command sets --model {MODEL} --effort max',
          'A6-locked: every launch\'s command sets --model claude-opus-5-5 --effort max')
    sj = sessions[d]
    ended = ('usage limit' if sj.get('api_error_status') == 429 else 'refused' if sj.get('stop_reason') == 'refusal'
             else 'completed' if sj.get('terminal_reason') == 'completed' and not sj.get('is_error')
             and lj.get('exit_code') == 0 else None)
    check(ended is not None, f'{d}: the launch ended by completing, a usage limit or a refusal',
          'A6-locked: every launch ended by completing, by a usage limit (429) or by a refusal')
    launch_info[d] = {'named': named, 'seconds': lj.get('seconds'), 'start': lj.get('start'), 'end': lj.get('end'),
                      'lanes': (lj.get('args') or {}).get('lanes'), 'exit_code': lj.get('exit_code'), 'ended': ended}
    check(sum(1 for r in rows if r['role'] == 'launch') == 1, f'{d}: one launch session row',
          'A6-locked: each agents.json has one launch session row')
    for r in rows:
        lab = f'launch:{d}' if r['role'] == 'launch' else r['label']
        a = arow.get((d, lab))
        check(a is not None and a['transcript'] == r['transcript'] and a['role'] == r['role']
              and str(a['pmid'] or '') == str(r.get('pmid') or ''),
              f'{d} {lab}: the audit row names the same transcript, role and paper',
              'A6-locked: every agents.json row has an audit.json row with the same transcript, role and paper')
        matched.add((d, lab))
        refusals = r.get('refusals') or 0
        check(sum(int(v[2]) for v in a['violations'] if v[0] == 'note' and v[1] == 'refusal') == refusals,
              f'{d} {lab}: refusals', 'A6-locked: agents.json refusals equal the audit\'s refusal notes, row by row')
        check(a['retry'] == ('sonnet' in str(r['label']).lower()), f'{d} {lab}: retry flag',
              'A6-locked: the audit\'s retry flag marks exactly the -sonnet agents')
        real = sorted(set(m for m in a['models'] if m != '<synthetic>'))
        check(len(real) <= 1 and (real or a['total'] == 0) and a['model_sequence'] in ('', *real),
              f'{d} {lab}: one model', 'A6-locked: every agent ran one model (an agent with no model used no tokens)')
        model = real[0] if real else None
        t = {'in': a['input_tokens'], 'cw': a['cache_creation_input_tokens'], 'cr': a['cache_read_input_tokens'],
             'out': a['output_tokens']}
        check(t['in'] + t['cw'] + t['cr'] + t['out'] == a['total'], f'{d} {lab}: total',
              'A6-locked: each audit row\'s total is its four counts')
        # a launch session writes 1-hour cache entries, an agent 5-minute ones (checked against session.json below)
        t['w1'], t['w5'] = (t['cw'], 0) if r['role'] == 'launch' else (0, t['cw'])
        t0, t1 = parse_ts(a['start']), parse_ts(a['end'])
        secs = (t1 - t0).total_seconds() if t0 and t1 else 0.0
        check(abs(round(secs / 60, 2) - (a['minutes'] or 0)) < 1e-9, f'{d} {lab}: minutes',
              'A6-locked: each audit row\'s minutes are its first-to-last timestamp span')
        per = {model: t} if model else {}
        c_r01b = sum(cost_r01b(m, x) for m, x in per.items())
        check(abs(c_r01b - a['usd']) <= 0.0000501, f'{d} {lab}: usd',
              'A6-locked: each audit row\'s usd is the r01b rule on its tokens (to 4 decimals)')
        agents.append({'launch': d, 'label': r['label'], 'pmid': str(r.get('pmid') or ''), 'role': r['role'],
                       'refusals': refusals, 'ending': (r.get('ending') or {}).get('stop_reason'), 'retry': a['retry'],
                       'transcript': r['transcript'], 'model': model, 'per': per, 'tokens': dict(t),
                       'start': t0, 'end': t1, 'seconds': secs, 'tool_calls': a['tool_calls'],
                       'cost_r01b': c_r01b, 'cost_list': sum(cost_list(m, x) for m, x in per.items())})
check(matched == set(arow), 'A6-locked: every audit.json row belongs to a row of the launches\' agents.json')
drawn = set(tri['papers_failed']) | pset
check(len(drawn) == 119, 'locked test: the 119 listed papers are the 83 analysed and the 36 left out')
check(all(a['pmid'] in drawn for a in agents if a['role'] != 'launch'),
      'A6-locked: every agent that is not a launch session reads one of the 119 listed papers')
check(all(set(v['named']) <= drawn for v in launch_info.values()), 'A6-locked: every launch names listed papers only')

# each launch's audit counts against its session.json (also the check of the 5-minute/1-hour rule)
launch_rows = []
for d in launch_names:
    mine = defaultdict(tok0)
    for a in agents:
        if a['launch'] == d:
            for m, t in a['per'].items():
                tadd(mine[m], t)
    mu = sessions[d].get('modelUsage') or {}
    refusals = sum(a['refusals'] for a in agents if a['launch'] == d)
    for m in sorted(set(mine) | set(mu)):
        u = mu.get(m) or {}
        sess = {'in': u.get('inputTokens', 0), 'cw': u.get('cacheCreationInputTokens', 0),
                'w5': u.get('cacheCreationEphemeral5mInputTokens', 0), 'w1': u.get('cacheCreationEphemeral1hInputTokens', 0),
                'cr': u.get('cacheReadInputTokens', 0), 'out': u.get('outputTokens', 0)}
        t = mine.get(m, tok0())
        gap = {k: sess[k] - t[k] for k in KEYS}
        check(all(v >= 0 for v in gap.values()), f'{d} {m}: the audit holds no more tokens than the session counted',
              'A6-locked: per launch and model, the audit holds no more tokens of any kind (5-minute and 1-hour writes '
              'apart) than session.json counts')
        if refusals == 0:
            check(not any(gap.values()), f'{d} {m}: with no refusal in the launch, audit and session.json agree exactly',
                  'A6-locked: in every launch where no agent logged a refusal, the audit and session.json agree exactly, '
                  '5-minute and 1-hour writes included')
        launch_rows.append({'launch': d, 'model': m, 'refusals_logged': refusals, 'audit': t, 'session': sess,
                            'gap': gap, 'session_costUSD': u.get('costUSD'),
                            'audit_cost_list': cost_list(m, t), 'audit_cost_r01b': cost_r01b(m, t),
                            'gap_cost_list': cost_list(m, gap), 'gap_cost_r01b': cost_r01b(m, gap)})
    check(abs(sum((mu[m] or {}).get('costUSD', 0) for m in mu) - sessions[d]['total_cost_usd']) < 1e-6,
          f'{d}: session.json total_cost_usd is the sum of its models\' costUSD',
          'A6-locked: each session.json total_cost_usd is the sum of its models\' costUSD')
launch_row = {a['launch']: a for a in agents if a['role'] == 'launch'}
w1_exact = [d for d in launch_names
            if launch_row[d]['tokens']['w1'] == ((sessions[d].get('modelUsage') or {}).get(MODEL) or {}).get(
                'cacheCreationEphemeral1hInputTokens')]

# kept launch per paper (common_w1.a6_kept_agents: the last launch of main, more-<k> that ran agents for it)
rank = {d: i for i, d in enumerate(launch_names)}
by_paper = defaultdict(lambda: defaultdict(list))
for a in agents:
    if a['role'] != 'launch':
        by_paper[a['pmid']][a['launch']].append(a)
share = {d: {'cost_r01b': launch_row[d]['cost_r01b'] / len(launch_info[d]['named']),
             'cost_list': launch_row[d]['cost_list'] / len(launch_info[d]['named']),
             'tokens': {k: launch_row[d]['tokens'][k] / len(launch_info[d]['named']) for k in KEYS}}
         for d in launch_names}
catlog, kept_agents = {}, []
for p in papers:
    ls = sorted(by_paper[p], key=rank.get)
    check(bool(ls), f'CatLog {p}: agents in at least one launch', 'CatLog: each analysed paper has agents in a launch')
    kept = ls[-1]
    ka = by_paper[p][kept]
    kept_agents += ka
    check(launch_info[kept]['ended'] == 'completed', f'CatLog {p}: its kept launch completed',
          'CatLog: each analysed paper\'s kept launch completed')
    check(any(a['role'] == 'read' and total_tokens(a['tokens']) for a in ka)
          and any(a['role'] == 'verify' and total_tokens(a['tokens']) for a in ka),
          f'CatLog {p}: its kept launch ran a reader and a verifier',
          'CatLog: each analysed paper\'s kept launch ran a reader and a verifier')
    check(all(a['model'] == MODEL for a in ka), f'CatLog {p}: every kept agent ran {MODEL}',
          f'CatLog: every kept agent of the analysed papers ran {MODEL}')
    check(p in launch_info[kept]['named'], f'CatLog {p}: its kept launch names it',
          'CatLog: each analysed paper\'s kept launch names it in its launch line')
    t = tok0()
    for a in ka:
        tadd(t, a['tokens'])
    tadd(t, share[kept]['tokens'])
    starts = [a['start'] for a in ka if a['start']]
    ends = [a['end'] for a in ka if a['end']]
    other = [d for d in launch_names if d != kept and p in launch_info[d]['named']]
    earlier_agents = [a for d in ls[:-1] for a in by_paper[p][d]]
    catlog[p] = {'kept_launch': kept, 'agents': len(ka), 'roles': dict(Counter(a['role'] for a in ka)),
                 'refused_agents': sum(1 for a in ka if a['refusals']), 'retries': sum(1 for a in ka if a['retry']),
                 'agents_cost_r01b': sum(a['cost_r01b'] for a in ka),
                 'share_cost_r01b': share[kept]['cost_r01b'], 'share_cost_list': share[kept]['cost_list'],
                 'cost_r01b': sum(a['cost_r01b'] for a in ka) + share[kept]['cost_r01b'],
                 'cost_list': sum(a['cost_list'] for a in ka) + share[kept]['cost_list'],
                 'tokens': t, 'agent_seconds': sum(a['seconds'] for a in ka),
                 'span_seconds': (max(ends) - min(starts)).total_seconds(),
                 'role_cost': {r: sum(a['cost_list'] for a in ka if a['role'] == r) for r in ('read', 'verify', 'verify_missed')},
                 'earlier_launches': ls[:-1], 'other_launches_naming_it': other,
                 'earlier_agents': len(earlier_agents),
                 'earlier_cost_r01b': sum(a['cost_r01b'] for a in earlier_agents) + sum(share[d]['cost_r01b'] for d in other),
                 'earlier_cost_list': sum(a['cost_list'] for a in earlier_agents) + sum(share[d]['cost_list'] for d in other)}
    check(abs(catlog[p]['role_cost']['read'] + catlog[p]['role_cost']['verify'] + catlog[p]['role_cost']['verify_missed']
              - sum(a['cost_r01b'] for a in ka)) < 1e-9,
          f'CatLog {p}: its kept agents cost the same at list prices and under the r01b rule',
          'CatLog: the kept agents\' cost is the same at list prices and under the r01b rule (5-minute writes, Opus 5.5)')
read_twice = {x.strip() for x in open(READ_TWICE) if x.strip()}
check({p for p in papers if catlog[p]['earlier_agents']} == read_twice & pset,
      'CatLog: the analysed papers with agents in an earlier launch are exactly the analysed papers of '
      'locked_copy_read_twice.txt')
check(all(launch_info[d]['ended'] in ('usage limit', 'refused') for p in papers
          for d in catlog[p]['earlier_launches'] + catlog[p]['other_launches_naming_it']),
      'CatLog: every earlier launch of an analysed paper was stopped by a usage limit or refused')

# ================================================================ summaries, locked set
def side_stats(cost, val, sup, ps_):
    return {'per_paper': quart([cost[p] for p in ps_]),
            'per_stored_value': quart([cost[p] / val[p] for p in ps_ if val[p]]),
            'per_supported_value': quart([cost[p] / sup[p] for p in ps_ if sup[p]]),
            'total': sum(cost[p] for p in ps_),
            'pooled_per_stored_value': sum(cost[p] for p in ps_) / sum(val[p] for p in ps_),
            'pooled_per_supported_value': sum(cost[p] for p in ps_) / sum(sup[p] for p in ps_),
            'papers_with_values': sum(1 for p in ps_ if val[p]), 'values': sum(val[p] for p in ps_),
            'supported_values': sum(sup[p] for p in ps_)}


def compare(base):
    C = {p: catlog[p][base] for p in papers}
    P = {p: plain[p][base] for p in papers}
    out = {'plain': side_stats(P, VAL['plain'], SUP['plain'], papers),
           'catlog': side_stats(C, VAL['catlog'], SUP['catlog'], papers)}
    both_v = [p for p in papers if VAL['catlog'][p] and VAL['plain'][p]]
    both_s = [p for p in papers if SUP['catlog'][p] and SUP['plain'][p]]
    out['ratio'] = {
        'per_paper': quart([C[p] / P[p] for p in papers]),
        'per_stored_value': quart([(C[p] / VAL['catlog'][p]) / (P[p] / VAL['plain'][p]) for p in both_v]),
        'per_supported_value': quart([(C[p] / SUP['catlog'][p]) / (P[p] / SUP['plain'][p]) for p in both_s]),
        'of_totals': sum(C.values()) / sum(P.values()),
        'of_totals_ci': boot_ratio(papers, C, P),
        'pooled_per_stored_value': (sum(C.values()) / sum(VAL['catlog'].values())) / (sum(P.values()) / sum(VAL['plain'].values())),
        'pooled_per_stored_value_ci': boot_ratio(papers, C, P, VAL['catlog'], VAL['plain']),
        'pooled_per_supported_value': (sum(C.values()) / sum(SUP['catlog'].values())) / (sum(P.values()) / sum(SUP['plain'].values())),
        'pooled_per_supported_value_ci': boot_ratio(papers, C, P, SUP['catlog'], SUP['plain']),
        'papers_catlog_dearer': sum(1 for p in papers if C[p] > P[p]),
        'smallest_paired_ratio': min(C[p] / P[p] for p in papers),
        'papers_with_values_on_both_sides': len(both_v), 'papers_with_supported_values_on_both_sides': len(both_s)}
    return out


locked = {'list_prices': compare('cost_list'), 'r01b_rule': compare('cost_r01b')}
TOK = {s: {p: total_tokens((plain if s == 'plain' else catlog)[p]['tokens']) for p in papers} for s in ('plain', 'catlog')}
OUT = {s: {p: (plain if s == 'plain' else catlog)[p]['tokens']['out'] for p in papers} for s in ('plain', 'catlog')}
SEC = {'plain': {p: plain[p]['seconds'] for p in papers}, 'catlog': {p: catlog[p]['agent_seconds'] for p in papers}}
locked['tokens'] = {s: {'per_paper': quart(list(TOK[s].values())), 'total': sum(TOK[s].values()),
                        'output_per_paper': quart(list(OUT[s].values())), 'output_total': sum(OUT[s].values()),
                        'mix': {k: sum((plain if s == 'plain' else catlog)[p]['tokens'][k] for p in papers) for k in KEYS}}
                    for s in ('plain', 'catlog')}
for s in ('plain', 'catlog'):
    locked['tokens'][s]['cache_read_share'] = locked['tokens'][s]['mix']['cr'] / locked['tokens'][s]['total']
locked['tokens']['ratio_of_totals'] = locked['tokens']['catlog']['total'] / locked['tokens']['plain']['total']
locked['tokens']['ratio_per_paper'] = quart([TOK['catlog'][p] / TOK['plain'][p] for p in papers])
locked['seconds'] = {'plain_session': quart(list(SEC['plain'].values())), 'catlog_agent_seconds': quart(list(SEC['catlog'].values())),
                     'catlog_span': quart([catlog[p]['span_seconds'] for p in papers]),
                     'ratio_per_paper': quart([SEC['catlog'][p] / SEC['plain'][p] for p in papers]),
                     'ratio_of_totals': sum(SEC['catlog'].values()) / sum(SEC['plain'].values()),
                     'plain_total': sum(SEC['plain'].values()), 'catlog_agent_total': sum(SEC['catlog'].values())}
locked['catlog_by_role'] = {r: quart([catlog[p]['role_cost'][r] for p in papers]) for r in ('read', 'verify')}
locked['catlog_by_role']['verify_missed_total'] = sum(catlog[p]['role_cost']['verify_missed'] for p in papers)
locked['catlog_by_role']['verify_missed_papers'] = sum(1 for p in papers if catlog[p]['role_cost']['verify_missed'])
locked['catlog_by_role']['launch_share_total_list'] = sum(catlog[p]['share_cost_list'] for p in papers)
locked['catlog_by_role']['launch_share_total_r01b'] = sum(catlog[p]['share_cost_r01b'] for p in papers)
locked['catlog_by_role']['launch_share_per_paper_list'] = quart([catlog[p]['share_cost_list'] for p in papers])
locked['catlog_by_role']['read_over_plain_paired_list'] = quart([catlog[p]['role_cost']['read'] / plain[p]['cost_list'] for p in papers])
locked['kept'] = {'launches': dict(Counter(catlog[p]['kept_launch'] for p in papers)),
                  'agents': sum(catlog[p]['agents'] for p in papers),
                  'roles': dict(sum((Counter(catlog[p]['roles']) for p in papers), Counter())),
                  'papers_with_a_refused_agent': sorted(p for p in papers if catlog[p]['refused_agents']),
                  'papers_with_a_retry_agent': sorted(p for p in papers if catlog[p]['retries']),
                  'plain_papers_with_a_retry': sorted(p for p in papers if plain[p]['retries'])}
check(not locked['kept']['papers_with_a_refused_agent'] and not locked['kept']['papers_with_a_retry_agent']
      and not locked['kept']['plain_papers_with_a_retry'],
      'locked: no kept agent of an analysed paper logged a refusal or is a retry, and no analysed paper has a plain retry')


def earlier_by_launch(kind):
    """Per earlier launch: the analysed papers it touches and what it adds (its agents, or its launch session's shares)."""
    out = {}
    for d in launch_names:
        if kind == 'agents':
            ps_ = [p for p in papers if d in catlog[p]['earlier_launches']]
            ag = [a for p in ps_ for a in by_paper[p][d]]
            if ps_:
                out[d] = {'ended': launch_info[d]['ended'], 'papers': len(ps_), 'agents': len(ag),
                          'cost_r01b': sum(a['cost_r01b'] for a in ag), 'cost_list': sum(a['cost_list'] for a in ag),
                          'refused_agents': sum(1 for a in ag if a['refusals'])}
        else:
            ps_ = [p for p in papers if d in catlog[p]['other_launches_naming_it']]
            if ps_:
                out[d] = {'ended': launch_info[d]['ended'], 'papers': len(ps_),
                          'cost_r01b': share[d]['cost_r01b'] * len(ps_), 'cost_list': share[d]['cost_list'] * len(ps_),
                          'agents_in_launch': sum(1 for a in agents if a['launch'] == d and a['role'] != 'launch'),
                          'launch_session_refusals': launch_row[d]['refusals']}
    return out


ER = {'catlog_agents_by_launch': earlier_by_launch('agents'), 'catlog_shares_by_launch': earlier_by_launch('shares')}
ER['catlog_papers_with_earlier_agents'] = sum(1 for p in papers if catlog[p]['earlier_agents'])
ER['catlog_papers_with_earlier_shares'] = sum(1 for p in papers if catlog[p]['other_launches_naming_it'])
ER['catlog_agents'] = sum(catlog[p]['earlier_agents'] for p in papers)
ER['catlog_earlier_agents_refused'] = sum(v['refused_agents'] for v in ER['catlog_agents_by_launch'].values())
for base in ('cost_r01b', 'cost_list'):
    ER[f'catlog_agents_{base}'] = sum(v[base] for v in ER['catlog_agents_by_launch'].values())
    ER[f'catlog_shares_{base}'] = sum(v[base] for v in ER['catlog_shares_by_launch'].values())
    ER[f'catlog_{base}'] = sum(catlog[p][f'earlier_{base}'] for p in papers)
    check(abs(ER[f'catlog_{base}'] - ER[f'catlog_agents_{base}'] - ER[f'catlog_shares_{base}']) < 1e-9,
          f'earlier runs: CatLog\'s earlier cost ({base}) is its earlier agents plus its earlier launch shares')
ER['plain_papers'] = sum(1 for p in papers if plain[p]['earlier_sessions'])
ER['plain_sessions'] = sum(len(plain[p]['earlier_sessions']) for p in papers)
ER['plain_cost_r01b'] = sum(plain[p]['earlier_cost_r01b'] for p in papers)
ER['plain_cost_list'] = sum(plain[p]['earlier_cost_list'] for p in papers)
check(set(ER['catlog_agents_by_launch']) <= {d for d in launch_names if launch_info[d]['ended'] == 'usage limit'},
      'earlier runs: the earlier agents of analysed papers all ran in launches that a usage limit stopped')
locked['earlier_runs'] = ER
locked['with_earlier_runs'] = {}
for base, key in (('cost_list', 'list_prices'), ('cost_r01b', 'r01b_rule')):
    c = locked[key]['catlog']['total'] + ER[f'catlog_{base}']
    q = locked[key]['plain']['total'] + ER[f'plain_{base}']
    locked['with_earlier_runs'][key] = {'catlog_total': c, 'plain_total': q, 'ratio_of_totals': c / q}
# post hoc view of the 34: CatLog's unit changes counted as right makes every stored value supported
sup34 = {p: VAL['catlog'][p] for p in papers}
locked['catlog_34_counted_right'] = {}
for base, key in (('cost_list', 'list_prices'), ('cost_r01b', 'r01b_rule')):
    c = locked[key]['catlog']['total'] / sum(sup34.values())
    locked['catlog_34_counted_right'][key] = {
        'pooled_per_supported_value': c,
        'ratio_pooled_per_supported_value': c / (locked[key]['plain']['total'] / sum(SUP['plain'].values())),
        'ci': boot_ratio(papers, {p: catlog[p][base] for p in papers}, {p: plain[p][base] for p in papers}, sup34, SUP['plain'])}

# whole runs, all 119 listed papers and every session (left-out papers, earlier and stopped runs included)
WR = {
    'plain_sessions': len(all_plain),
    'plain_sessions_without_result': sum(1 for s in all_plain if not s['has_result']),
    'plain_cost_list': sum(session_costs(s)[0] for s in all_plain),
    'plain_cost_r01b': sum(session_costs(s)[1] for s in all_plain),
    'plain_refused_sessions': sum(1 for s in all_plain if s['stop_reason'] == 'refusal'),
    'plain_refused_sessions_cost_list': sum(session_costs(s)[0] for s in all_plain if s['stop_reason'] == 'refusal'),
    'plain_refused_sessions_cost_r01b': sum(session_costs(s)[1] for s in all_plain if s['stop_reason'] == 'refusal'),
    'plain_audit_equal': plain_audit_equal, 'plain_audit_records_count_more': plain_audit_more,
    'catlog_rows': len(agents), 'catlog_launches': len(launch_names),
    'catlog_cost_r01b': sum(a['cost_r01b'] for a in agents), 'catlog_cost_list': sum(a['cost_list'] for a in agents),
    'catlog_audit_usd_total': A6['summary']['usd_total'],
    'catlog_session_total_cost_usd': sum(sessions[d]['total_cost_usd'] for d in launch_names),
    'catlog_gap_cost_list': sum(r['gap_cost_list'] for r in launch_rows),
    'catlog_gap_cost_r01b': sum(r['gap_cost_r01b'] for r in launch_rows),
    'catlog_launch_seconds': sum(launch_info[d]['seconds'] or 0 for d in launch_names),
    'catlog_launches_ended': {d: launch_info[d]['ended'] for d in launch_names},
    # refused and retried agents: none is among the analysed papers' kept agents (their papers left the set, or the
    # agent ran in an earlier launch), so they appear here, over the whole runs
    'catlog_refused_agents': sum(1 for a in agents if a['role'] != 'launch' and a['refusals']),
    'catlog_refused_agents_cost_r01b': sum(a['cost_r01b'] for a in agents if a['role'] != 'launch' and a['refusals']),
    'catlog_refused_agents_cost_list': sum(a['cost_list'] for a in agents if a['role'] != 'launch' and a['refusals']),
    'catlog_refused_agents_papers': len({a['pmid'] for a in agents if a['role'] != 'launch' and a['refusals']}),
    'catlog_refused_launch_sessions': {d: {'refusals': a['refusals'], 'cost_r01b': a['cost_r01b'], 'cost_list': a['cost_list']}
                                       for d, a in launch_row.items() if a['refusals']},
    'catlog_retry_agents': sum(1 for a in agents if a['retry']),
    'catlog_retry_agents_cost_r01b': sum(a['cost_r01b'] for a in agents if a['retry']),
    'catlog_retry_agents_cost_list': sum(a['cost_list'] for a in agents if a['retry']),
    'launch_session_writes_equal_session_1h': w1_exact}
check(all(a['model'] in ('claude-sonnet-5-5', None) for a in agents if a['retry'])
      and all(a['model'] != 'claude-sonnet-5-5' for a in agents if not a['retry']),
      'CatLog: the retry agents are exactly the agents that ran claude-sonnet-5-5 (a retry with no model used no tokens)')
check(abs(WR['catlog_cost_r01b'] - WR['catlog_audit_usd_total']) < 0.01,
      'CatLog: the whole run\'s r01b cost equals the audit\'s usd_total (to the cent)')
check(abs(WR['catlog_cost_list'] + WR['catlog_gap_cost_list'] - WR['catlog_session_total_cost_usd']) < 1e-4,
      'CatLog: the audit\'s counts plus the gap give the launches\' session.json total_cost_usd')
check(abs(sum(catlog[p]['cost_r01b'] + catlog[p]['earlier_cost_r01b'] for p in papers)
          - sum(a['cost_r01b'] for a in agents if a['pmid'] in pset)
          - sum(share[d]['cost_r01b'] * len(set(launch_info[d]['named']) & pset) for d in launch_names)) < 1e-6,
      'CatLog: kept plus earlier costs of the 83 papers are their agents plus their launch shares')
locked['whole_runs'] = WR

# ================================================================ random test, plain side (a second set)
rtop, rearlier = plain_steps(A0R)
aud0r = {a['session_id']: a for a in json.load(open(A0R_AUDIT))['agents']}
rplain, r_audit, r_audit_more = {}, Counter(), []
for p in rpapers:
    att = rtop.get(p) or []
    check(att and att[-1]['ok'] is True and all(s['model'] == MODEL and set(s['per']) <= {MODEL} for s in att),
          f'random plain {p}: kept invocation valid, {MODEL} alone',
          f'plain, random: each analysed paper\'s kept invocation ends in a valid read, {MODEL} alone')
    check(all(s['ok'] is not True for s in att[:-1]), f'random plain {p}: only the last session of the kept invocation is valid',
          'plain, random: a retry (a2) follows only a session with no valid read')
    for s in att:
        check(abs(sum(cost_list(m, t) for m, t in s['per'].items()) - session_costs(s)[0]) < 1e-6,
              f'random plain {s["label"]}: the list price table gives its total_cost_usd',
              'plain, random: the solved list price table gives each kept session\'s total_cost_usd')
        check(flag_value(s['command'], '--effort') == 'max', f'random plain {s["label"]}: --effort max',
              'plain, random: every kept session\'s command sets --effort max')
        a = aud0r.get(s['session_id'])
        check(a is not None and a['transcript'] == s['transcript'], f'random plain {s["label"]}: an audit row',
              'plain, random: every kept session has a row in the kit\'s audit, for the same transcript')
        rec, au = four(s['usage']), four(a)
        check(all(x >= y for x, y in zip(rec, au)),
              f'random plain {s["label"]}: the kit\'s audit gives no more tokens than the record',
              'plain, random: for every kept session the kit\'s audit gives no more of any token kind than the record')
        r_audit['equal' if rec == au else 'record_counts_more'] += 1
        if rec != au:
            r_audit_more.append(s['label'])
    t = tok0()
    for s in att:
        tadd(t, session_tokens(s))
    rplain[p] = {'sessions': [s['label'] for s in att], 'cost_list': sum(session_costs(s)[0] for s in att),
                 'cost_r01b': sum(session_costs(s)[1] for s in att), 'tokens': t,
                 'failed_first_list': sum(session_costs(s)[0] for s in att[:-1]),
                 'failed_first_r01b': sum(session_costs(s)[1] for s in att[:-1]),
                 'safety_stops': sum(s['safety_stops'] for s in att),
                 'seconds': sum(s['seconds'] or 0 for s in att), 'values': R['per_paper'][p]['plain']['values'],
                 'wrong': R['per_paper'][p]['plain']['wrong'], 'earlier_sessions': [s['label'] for s in rearlier.get(p, [])]}
rv = {p: rplain[p]['values'] for p in rpapers}
r_supported = rps['plain']['values'] - rps['plain']['wrong'] - rps['plain']['cannot_decide']
rand = {}
for base in ('cost_list', 'cost_r01b'):
    C = {p: rplain[p][base] for p in rpapers}
    Cn = {p: rplain[p][base] - rplain[p]['failed_first_' + base.split('_')[1]] for p in rpapers}
    rand[base] = {'per_paper': quart(list(C.values())), 'per_stored_value': quart([C[p] / rv[p] for p in rpapers if rv[p]]),
                  'total': sum(C.values()), 'pooled_per_stored_value': sum(C.values()) / sum(rv.values()),
                  'pooled_per_supported_value': sum(C.values()) / r_supported,
                  'failed_first_sessions': sum(C[p] - Cn[p] for p in rpapers),
                  'without_failed_first_sessions': {
                      'total': sum(Cn.values()), 'per_paper': quart(list(Cn.values())),
                      'per_stored_value': quart([Cn[p] / rv[p] for p in rpapers if rv[p]]),
                      'pooled_per_stored_value': sum(Cn.values()) / sum(rv.values()),
                      'pooled_per_supported_value': sum(Cn.values()) / r_supported}}
rand['papers'] = len(rpapers)
rand['values'] = sum(rv.values())
rand['supported_values'] = r_supported
rand['cannot_decide'] = rps['plain']['cannot_decide']
rand['tokens_per_paper'] = quart([total_tokens(rplain[p]['tokens']) for p in rpapers])
rand['seconds_per_paper'] = quart([rplain[p]['seconds'] for p in rpapers])
rand['papers_with_a_retry'] = sorted(p for p in rpapers if len(rplain[p]['sessions']) > 1)
rand['papers_with_a_safety_stop'] = sorted(p for p in rpapers if rplain[p]['safety_stops'])
rand['papers_with_earlier_sessions'] = sorted(p for p in rpapers if rplain[p]['earlier_sessions'])
rand['kept_sessions_against_audit'] = dict(r_audit)
rand['kept_sessions_counting_more_than_their_transcript'] = r_audit_more
rand['writes_5m'] = sum(x['w5'] for p in rpapers for x in [rplain[p]['tokens']])
check(rand['writes_5m'] == 0, 'plain, random: every kept session writes 1-hour cache entries only')

# ================================================================ CatLog in the catalogue, by role (rethink's table)
rows = list(csv.DictReader(open(TOKENS), delimiter='\t'))
check(len(rows) == 16938, 'per-agent token table: 16,938 agents')
check(all('/subagents/' in r['file'] for r in rows), 'per-agent token table: every row is a subagent transcript')


def r01b_cost(r, sonnet_list=False):
    """r01b_cost.py's cost(): the agent's main model, cache writes at WRITE x input; with sonnet_list, Sonnet 5.5's
    cache read at its list price instead (the only r01b price that differs from the solved list prices)."""
    p = PRICE.get(r['model'])
    if not p:
        return None
    i, o, cr = p
    if sonnet_list and r['model'] == 'claude-sonnet-5-5':
        cr = CC['claude-sonnet-5-5'][2]
    return (int(r['input_tokens']) * i + int(r['cache_creation_input_tokens']) * i * WRITE +
            int(r['cache_read_input_tokens']) * cr + int(r['output_tokens']) * o) / 1e6


def r01b_summ(xs):  # r01b_cost.py's summ()
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return {}
    q = lambda f: xs[int(f * (len(xs) - 1))]  # noqa: E731
    return {'n': len(xs), 'median': round(statistics.median(xs), 3), 'mean': round(statistics.mean(xs), 3),
            'p10': round(q(.1), 3), 'p90': round(q(.9), 3), 'sum': round(sum(xs), 1)}


check(CC['claude-sonnet-5-5'][0] == PRICE['claude-sonnet-5-5'][0] and CC['claude-sonnet-5-5'][1] == PRICE['claude-sonnet-5-5'][1]
      and CC['claude-sonnet-5-5'][3] == PRICE['claude-sonnet-5-5'][0] * WRITE and CC['claude-sonnet-5-5'][2] != PRICE['claude-sonnet-5-5'][2],
      'Sonnet 5.5: r01b input, output and 5-minute write equal the list prices; its cache read does not')
by_role, per_paper_role, per_paper_sl = defaultdict(list), defaultdict(lambda: defaultdict(float)), defaultdict(float)
sonnet_papers = set()
for r in rows:
    c = r01b_cost(r)
    by_role[r['role']].append(c)
    if r['role'] in ('read', 'verify', 'verify_missed') and r['paper'] and c is not None:
        per_paper_role[r['paper']][r['role']] += c
        per_paper_sl[r['paper']] += r01b_cost(r, sonnet_list=True)
        if r['model'] == 'claude-sonnet-5-5':
            sonnet_papers.add(r['paper'])
both = {p: v for p, v in per_paper_role.items() if v.get('read') and v.get('verify')}
cs = json.load(open(COST_SUMMARY))
check({k: r01b_summ(v) for k, v in sorted(by_role.items())} == cs['per_role_usd'],
      'r01b_cost.py rerun on tokens_per_agent.tsv gives cost_summary.json per_role_usd')
check(r01b_summ([v['read'] + v['verify'] + v.get('verify_missed', 0) for v in both.values()])
      == cs['per_paper_read_plus_verify_usd'], 'r01b rerun gives cost_summary.json per_paper_read_plus_verify_usd')
check(sum(1 for r in rows if r01b_cost(r) is None) == cs['unpriced_agents'] == 248, 'r01b rerun: 248 agents unpriced')
pp = cs['per_paper_read_plus_verify_usd']
check((pp['n'], f"{pp['median']:.2f}", f"{pp['mean']:.2f}", f"{pp['p10']:.2f}", f"{pp['p90']:.2f}")
      == (6013, '1.52', '1.89', '0.99', '3.26'), 'cost_summary.json: read + verify per paper $1.52, mean $1.89, '
                                                   '$0.99-3.26, n = 6,013, as the Methods ledger n66 prints')
check(tuple(f"{cs['per_role_usd'][r]['median']:.2f}" for r in ('read', 'verify', 'audit', 'dbcheck', 'scale_check'))
      == ('0.75', '0.71', '0.99', '0.51', '0.66'), 'cost_summary.json: per-agent medians $0.75, $0.71, $0.99, $0.51, $0.66 (n66)')
check(round(sum(v['sum'] for v in cs['per_role_usd'].values())) == 18026 and round(pp['sum']) == 11372,
      'cost_summary.json: all priced roles $18,026, read + verify $11,372 (n66)')
ADDED = json.load(open(PIPELINE))['totals_from_log']['papers_first_added']
LATER = ('audit', 'dbcheck', 'scale_check', 'scale_refute', 'scale_second')
starts = lambda roles: sorted(r['start'] for r in rows if r['role'] in roles and r['start'])  # noqa: E731
rv_starts, all_starts = starts(('read', 'verify', 'verify_missed')), starts(set(r['role'] for r in rows))
check(rv_starts[0][:10] == '2026-10-09' and rv_starts[-1][:10] == '2026-10-22',
      'per-agent table: reading and verifying agents started 9 to 22 October 2026 (n66)')
prod = {'papers_with_read_and_verify': len(both), 'papers_added_by_then': ADDED,
        'first_agent_start_utc': all_starts[0], 'last_agent_start_utc': all_starts[-1],
        'first_read_verify_start_utc': rv_starts[0], 'last_read_verify_start_utc': rv_starts[-1], 'roles': {}}
for role in ('read', 'verify', 'verify_missed'):
    xs = [v.get(role, 0.0) for v in both.values()]
    prod['roles'][role] = {'agents': len(by_role[role]), 'per_paper': quart(xs),
                           'papers_with_one': sum(1 for x in xs if x),
                           'per_paper_with_one': quart([x for x in xs if x]) if sum(1 for x in xs if x) > 1 else None,
                           'total_on_these_papers': sum(xs), 'total_all_agents': sum(c for c in by_role[role] if c is not None)}
prod['roles']['read_verify_missed'] = {'per_paper': quart([v['read'] + v['verify'] + v.get('verify_missed', 0) for v in both.values()])}
prod['read_verify_missed_sonnet_cache_read_at_list'] = {
    'per_paper': quart([per_paper_sl[p] for p in both]), 'papers_with_a_sonnet_agent': len(sonnet_papers & set(both)),
    'sonnet_read_verify_agents': sum(1 for r in rows if r['role'] in ('read', 'verify', 'verify_missed') and r['model'] == 'claude-sonnet-5-5'),
    'difference_total': sum(per_paper_sl[p] for p in both) - sum(v['read'] + v['verify'] + v.get('verify_missed', 0) for v in both.values())}
for role in LATER:
    tot = sum(c for c in by_role[role] if c is not None)
    prod['roles'][role] = {'agents': len(by_role[role]), 'total_all_agents': tot, 'per_paper_added': tot / ADDED,
                           'per_agent_median': cs['per_role_usd'][role]['median']}
prod['classified_checks_total'] = sum(prod['roles'][r]['total_all_agents'] for r in LATER)
prod['classified_checks_agents'] = sum(prod['roles'][r]['agents'] for r in LATER)
prod['classified_checks_per_paper_added'] = prod['classified_checks_total'] / ADDED
prod['not_counted'] = {r: {'agents': len(by_role[r]), 'total': sum(c for c in by_role[r] if c is not None)}
                       for r in ('chrome_lane', 'other')}
prod['later_checks_at_most_per_paper_added'] = (prod['classified_checks_total'] + prod['not_counted']['other']['total']) / ADDED
# the reprint sweep: later checks the table leaves unclassified ('other'); its handoff names its workflow runs
handoff_runs = sorted(set(RUN_ID.findall(open(REPRINT_HANDOFF).read())))
check(len(handoff_runs) >= 1, 'reprint sweep handoff: names at least one workflow run')
sweep_rows = [r for r in rows if any(f'/workflows/{w}/' in r['file'] for w in handoff_runs)]
check(sweep_rows and all(r['role'] == 'other' for r in sweep_rows),
      'per-agent table: the reprint sweep\'s named workflow runs are all unclassified (role "other")')
prod['reprint_sweep_named_runs'] = {'runs': handoff_runs, 'agents': len(sweep_rows),
                                    'total': sum(r01b_cost(r) or 0 for r in sweep_rows),
                                    'per_paper_added': sum(r01b_cost(r) or 0 for r in sweep_rows) / ADDED,
                                    'start_days_utc': sorted(set(r['start'][:10] for r in sweep_rows))}
prod['models_read_verify'] = dict(Counter(r['model'] for r in rows if r['role'] in ('read', 'verify', 'verify_missed')))

# ================================================================ the paper's sentences, every number from above
def usd(x, d=2):
    return f'${x:,.{d}f}'


def mid(q, d=2, f=usd):
    return f'{f(q["median"], d)} ({f(q["q1"], d)} to {f(q["q3"], d)})'


def x2(x, d=2):
    return f'{x:,.{d}f}'


def ci(c, d=2):
    return f'{c["lo"]:.{d}f} to {c["hi"]:.{d}f}'


def mtok(x, d=2):
    return f'{x / 1e6:,.{d}f}'


def pct(x):
    return f'{100 * x:.0f}%'


LP, RB = locked['list_prices'], locked['r01b_rule']
lp_, lc_, lr = LP['plain'], LP['catlog'], LP['ratio']
rp_, rc_, rr = RB['plain'], RB['catlog'], RB['ratio']
T, S, BR = locked['tokens'], locked['seconds'], locked['catlog_by_role']
WE = locked['with_earlier_runs']
o55, s55 = CC[MODEL], CC['claude-sonnet-5-5']
stopped = sorted((d for d in ER['catlog_agents_by_launch'] if launch_info[d]['ended'] == 'usage limit'), key=rank.get)
sentences = [
    (f"On the 83 held-out papers, one completed read of each paper (for CatLog, its agents and a share of its launch "
     f"session) used tokens worth a median of {usd(lc_['per_paper']['median'])} at list prices with CatLog "
     f"(interquartile range {usd(lc_['per_paper']['q1'])} to {usd(lc_['per_paper']['q3'])}) and "
     f"{usd(lp_['per_paper']['median'])} ({usd(lp_['per_paper']['q1'])} to {usd(lp_['per_paper']['q3'])}) with the plain "
     f"reading, a median of {x2(lr['per_paper']['median'], 1)} times as much for the same paper (interquartile range "
     f"{x2(lr['per_paper']['q1'], 1)} to {x2(lr['per_paper']['q3'], 1)}); the totals were {usd(lc_['total'])} and "
     f"{usd(lp_['total'])} (ratio of totals {x2(lr['of_totals'])}, 95% interval {ci(lr['of_totals_ci'])}), and "
     f"{usd(lc_['pooled_per_supported_value'], 3)} and {usd(lp_['pooled_per_supported_value'], 3)} per value judged "
     f"supported, pooled (ratio {x2(lr['pooled_per_supported_value'])}, 95% interval "
     f"{ci(lr['pooled_per_supported_value_ci'])})."),
    (f"These are list-price equivalents of the recorded tokens, not amounts paid (claude-opus-5-5, per million tokens: "
     f"${o55[0]:g} input, ${o55[1]:g} output, ${o55[2]:.2f} cache read, ${o55[3]:g} per 5-minute and ${o55[4]:g} per "
     f"1-hour cache write); earlier runs are left out, among them launches that a usage limit stopped after they had "
     f"run agents on {ER['catlog_papers_with_earlier_agents']} of these papers (with all earlier runs, "
     f"{usd(WE['list_prices']['catlog_total'])} against {usd(WE['list_prices']['plain_total'])}); no counted agent or "
     f"session logged a refusal (papers with a refused session or agent left the test: {EXITS_REFUSED} of its {EXITS} "
     f"exits), so no refusal cost is included; and with every cache write priced at the 5-minute rate, as in the "
     f"catalogue's cost estimate, the ratio of totals is {x2(rr['of_totals'])} (95% interval {ci(rr['of_totals_ci'])}).")]
locked['paper_sentences'] = sentences

# ================================================================ write
def r4(x):
    return round(x, 4) if isinstance(x, float) else x


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, float):
        return round(o, 6)
    if isinstance(o, datetime):
        return o.isoformat()
    return o


inputs = {x: sha256(x) for x in (LOCKED, READ_TWICE, RANDOM, COST_SUMMARY, R01B, TOKENS, PIPELINE, REPRINT_HANDOFF,
                                 A6_AUDIT, A6_TOKENS, A0L_AUDIT, A0R_AUDIT)}
for d in launch_names:
    for f in ('agents.json', 'launch.json', 'session.json'):
        x = os.path.join(A6L, d, f)
        inputs[x] = sha256(x)
inputs_records = {'plain_session_records': len(record_files),
                  'plain_session_records_sha256_of_hashes': hashlib.sha256(
                      ''.join(f'{f}\t{sha256(f)}\n' for f in record_files).encode()).hexdigest()}
results = {
    'question': 'Cost per paper and per value, CatLog\'s frozen run against the plain reading, locked test (83 papers)',
    'draft_text': ' '.join(sentences),
    'prices': {'list_per_mtok': {m: dict(zip(('input', 'output', 'cache_read', 'cache_write_5m', 'cache_write_1h'), v))
                                 for m, v in CC.items()},
               'list_write_multipliers_opus_5_5': {'5m': W5_X, '1h': W1_X},
               'list_fit': cc_fit,
               'r01b_per_mtok': {m: {'input': v[0], 'output': v[1], 'cache_read': v[2], 'cache_write_any': v[0] * WRITE}
                                 for m, v in PRICE.items()},
               'r01b_cache_write_multiplier': WRITE},
    'locked': locked, 'random_plain': rand, 'production': prod,
    'launches': {d: {**launch_info[d], 'agents': sum(1 for a in agents if a['launch'] == d and a['role'] != 'launch'),
                     'session_total_cost_usd': sessions[d]['total_cost_usd'],
                     'audit_cost_r01b': sum(a['cost_r01b'] for a in agents if a['launch'] == d),
                     'audit_cost_list': sum(a['cost_list'] for a in agents if a['launch'] == d),
                     'papers_kept_here': sum(1 for p in papers if catlog[p]['kept_launch'] == d)} for d in launch_names},
    'inputs_sha256': inputs, 'inputs_records': inputs_records, 'checks_passed': dict(CHECKS)}
json.dump(clean(results), open(os.path.join(HERE, 'results.json'), 'w'), indent=1)

with open(os.path.join(HERE, 'per_paper_locked.tsv'), 'w') as fh:
    cols = ['pmid', 'plain_values', 'plain_supported', 'plain_sessions', 'plain_cost_list_usd', 'plain_cost_r01b_usd',
            'plain_tokens', 'plain_output_tokens', 'plain_seconds', 'catlog_values', 'catlog_supported', 'catlog_kept_launch',
            'catlog_agents', 'catlog_cost_list_usd', 'catlog_cost_r01b_usd', 'catlog_launch_share_list_usd',
            'catlog_read_usd', 'catlog_verify_usd', 'catlog_missed_values_usd', 'catlog_tokens', 'catlog_output_tokens',
            'catlog_agent_seconds', 'catlog_span_seconds', 'ratio_cost_list', 'ratio_cost_r01b', 'catlog_earlier_launches',
            'catlog_other_launches_naming_it', 'catlog_earlier_cost_list_usd', 'plain_earlier_sessions',
            'plain_earlier_cost_list_usd']
    fh.write('\t'.join(cols) + '\n')
    for p in papers:
        c, q = catlog[p], plain[p]
        row = [p, VAL['plain'][p], SUP['plain'][p], ' '.join(q['sessions']), r4(q['cost_list']), r4(q['cost_r01b']),
               total_tokens(q['tokens']), q['tokens']['out'], q['seconds'], VAL['catlog'][p], SUP['catlog'][p],
               c['kept_launch'], c['agents'], r4(c['cost_list']), r4(c['cost_r01b']), r4(c['share_cost_list']),
               r4(c['role_cost']['read']), r4(c['role_cost']['verify']), r4(c['role_cost']['verify_missed']),
               round(total_tokens(c['tokens'])), round(c['tokens']['out']), round(c['agent_seconds'], 1),
               round(c['span_seconds'], 1), r4(c['cost_list'] / q['cost_list']), r4(c['cost_r01b'] / q['cost_r01b']),
               ' '.join(c['earlier_launches']) or '-', ' '.join(c['other_launches_naming_it']) or '-',
               r4(c['earlier_cost_list']), ' '.join(q['earlier_sessions']) or '-', r4(q['earlier_cost_list'])]
        fh.write('\t'.join(str(x) for x in row) + '\n')
with open(os.path.join(HERE, 'per_agent_locked.tsv'), 'w') as fh:
    cols = ['launch', 'launch_ended', 'label', 'pmid', 'role', 'model', 'analysed', 'kept', 'retry', 'refusals', 'ending',
            'input', 'cache_write_5m', 'cache_write_1h', 'cache_read', 'output', 'total_tokens', 'seconds', 'cost_list_usd',
            'cost_r01b_usd', 'transcript']
    fh.write('\t'.join(cols) + '\n')
    for a in agents:
        row = [a['launch'], launch_info[a['launch']]['ended'], a['label'], a['pmid'] or '-', a['role'], a['model'] or '-',
               'yes' if a['pmid'] in pset else 'no',
               'yes' if a['pmid'] in pset and catlog[a['pmid']]['kept_launch'] == a['launch'] else 'no',
               'yes' if a['retry'] else 'no', a['refusals'], a['ending'], a['tokens']['in'], a['tokens']['w5'],
               a['tokens']['w1'], a['tokens']['cr'], a['tokens']['out'], total_tokens(a['tokens']), round(a['seconds'], 1),
               r4(a['cost_list']), r4(a['cost_r01b']), rel(a['transcript'])]
        fh.write('\t'.join(str(x) for x in row) + '\n')
with open(os.path.join(HERE, 'launch_check.tsv'), 'w') as fh:
    cols = ['launch', 'ended', 'model', 'refusals_logged'] + [f'{w}_{k}' for w in ('audit', 'session', 'gap') for k in KEYS] + \
           ['session_costUSD', 'audit_cost_list_usd', 'gap_cost_list_usd', 'audit_cost_r01b_usd', 'gap_cost_r01b_usd']
    fh.write('\t'.join(cols) + '\n')
    for r in launch_rows:
        row = [r['launch'], launch_info[r['launch']]['ended'], r['model'], r['refusals_logged']] + \
              [r[w][k] for w in ('audit', 'session', 'gap') for k in KEYS] + \
              [r4(r['session_costUSD']) if r['session_costUSD'] is not None else '-', r4(r['audit_cost_list']),
               r4(r['gap_cost_list']), r4(r['audit_cost_r01b']), r4(r['gap_cost_r01b'])]
        fh.write('\t'.join(str(x) for x in row) + '\n')
with open(os.path.join(HERE, 'per_paper_random.tsv'), 'w') as fh:
    cols = ['pmid', 'plain_values', 'plain_wrong', 'plain_sessions', 'plain_cost_list_usd', 'plain_cost_r01b_usd',
            'failed_first_session_cost_list_usd', 'failed_first_session_cost_r01b_usd', 'safety_stops', 'plain_tokens',
            'plain_seconds', 'plain_earlier_sessions']
    fh.write('\t'.join(cols) + '\n')
    for p in rpapers:
        q = rplain[p]
        fh.write('\t'.join(str(x) for x in [p, q['values'], q['wrong'], ' '.join(q['sessions']), r4(q['cost_list']),
                                            r4(q['cost_r01b']), r4(q['failed_first_list']), r4(q['failed_first_r01b']),
                                            q['safety_stops'], total_tokens(q['tokens']), q['seconds'],
                                            ' '.join(q['earlier_sessions']) or '-']) + '\n')
with open(os.path.join(HERE, 'production_roles.tsv'), 'w') as fh:
    fh.write('role\tagents\tpapers\tmedian_per_paper_usd\tq1\tq3\tmean_per_paper_usd\ttotal_usd\tper_paper_added_usd\n')
    for role in ('read', 'verify', 'verify_missed'):
        x = prod['roles'][role]
        fh.write('\t'.join(str(v) for v in [role, x['agents'], len(both), r4(x['per_paper']['median']), r4(x['per_paper']['q1']),
                                            r4(x['per_paper']['q3']), r4(x['per_paper']['mean']), r4(x['total_on_these_papers']),
                                            '-']) + '\n')
    x = prod['roles']['read_verify_missed']['per_paper']
    fh.write('\t'.join(str(v) for v in ['read+verify+missed', '-', len(both), r4(x['median']), r4(x['q1']), r4(x['q3']),
                                        r4(x['mean']), r4(x['sum']), '-']) + '\n')
    for role in LATER:
        x = prod['roles'][role]
        fh.write('\t'.join(str(v) for v in [role, x['agents'], '-', '-', '-', '-', '-', r4(x['total_all_agents']),
                                            r4(x['per_paper_added'])]) + '\n')
    fh.write('\t'.join(str(v) for v in ['audit+dbcheck+unit-factor checks (lower bound for later checks)',
                                        prod['classified_checks_agents'], '-', '-', '-', '-', '-',
                                        r4(prod['classified_checks_total']), r4(prod['classified_checks_per_paper_added'])]) + '\n')
    x = prod['reprint_sweep_named_runs']
    fh.write('\t'.join(str(v) for v in ['reprint sweep, named runs (in other)', x['agents'], '-', '-', '-', '-', '-',
                                        r4(x['total']), r4(x['per_paper_added'])]) + '\n')
    for r in ('chrome_lane', 'other'):
        x = prod['not_counted'][r]
        fh.write('\t'.join(str(v) for v in [r, x['agents'], '-', '-', '-', '-', '-', r4(x['total']), r4(x['total'] / ADDED)]) + '\n')

# ================================================================ README.md, every number from above
n_cc_records = sum(v['records'] for v in cc_fit.values())
n_launch_rows = sum(1 for a in agents if a['role'] == 'launch')
no_ref_launches = [d for d in launch_names if not sum(a['refusals'] for a in agents if a['launch'] == d)]
kept_launches = sorted(locked['kept']['launches'], key=rank.get)
ESL = ER['catlog_shares_by_launch']
refused_launch = sorted((d for d in ESL if launch_info[d]['ended'] == 'refused'), key=rank.get)
md = []
w = md.append
w('# Cost per paper and per value: CatLog against the plain reading')
w('')
w('## The question')
w('What does CatLog\'s reading cost per paper, per stored value and per value judged supported, against the plain '
  'reading, on the locked test\'s 83 analysed papers? Each side\'s figure is one completed read of each paper, on '
  'claude-opus-5-5 with `--effort max` on the command line: the plain reading\'s kept session, and CatLog\'s frozen run '
  '(reader, independent verifier and, where it ran, the missed-values verifier) in the completed launch whose rows were '
  'kept, plus an equal share of that launch\'s own session. Earlier runs of the same papers are counted apart. Records '
  'only: nothing was read, judged or run again.')
w('')
w('## Inputs')
w(f'- The 83 papers, their stored values and the values judged wrong: `{LOCKED}` (`per_paper`, `per_source`, `triage`).')
w(f'- Plain reading: `{A0L}/<PMID>.a1.json` (and `.a2.json` where the kit\'s one retry ran; none of the 83 has one): '
  f'`result.modelUsage` (tokens by kind, `costUSD`, `costBasis`), `total_cost_usd`, `seconds`, `command`. Earlier '
  f'sessions: `{A0L}/earlier/`. The check of their tokens: `{A0L_AUDIT}`, the kit\'s audit of every session, read from '
  'its transcript.')
w(f'- CatLog: `{A6L}/<launch>/agents.json` for the {len(launch_names)} launches ({len(agents)} rows: '
  f'{len(agents) - n_launch_rows} agents and {n_launch_rows} launch sessions), `launch.json` (the papers each launch line '
  f'names, the command, times) and `session.json` (Claude Code\'s totals and how the launch ended, the check). Each '
  f'agent\'s tokens, model and times: `{A6_AUDIT}`, the kit\'s audit of the run, read from the transcripts that '
  f'`agents.json` names; `{A6_TOKENS}` is its token table, a check.')
w(f'- Second set, plain side only: `{A0R}/`, `{A0R_AUDIT}` and `{RANDOM}`.')
w(f'- Prices and the catalogue\'s cost: `{R01B}`, `{COST_SUMMARY}`, `{TOKENS}`, `{PIPELINE}` '
  f'(`totals_from_log.papers_first_added`), and the reprint sweep\'s handoff `{REPRINT_HANDOFF}` (the workflow runs it '
  'names).')
w(f'- `{READ_TWICE}` (the papers the copy read twice, a check).')
w('- sha256 of every input file: `results.json` `inputs_sha256` (the session records as one hash of their hashes, '
  '`inputs_records`). No transcript is opened.')
w('')
w('## Method')
w(f'- **Tokens.** Plain: each session record\'s `modelUsage`; the kit\'s audit gives the same four counts from the '
  f'transcript of each of the {len(papers)} kept sessions. CatLog: the kit\'s audit, each agent\'s four counts once per '
  'message id (as `r01_tokens.py` counts). An agent\'s cache writes are 5-minute writes and a launch session\'s are '
  f'1-hour writes: in the {len(no_ref_launches)} launches where no agent logged a refusal the audit gives '
  f'`session.json`\'s counts exactly, both kinds of write included, and elsewhere never more of any kind; the launch '
  f'session\'s writes equal `session.json`\'s 1-hour writes in {len(w1_exact)} of {len(launch_names)} launches ('
  + '; '.join(f'in {d}, whose own session was refused, `session.json` counts {r["gap"]["w1"]} more, from the refused '
              f'requests' for d in launch_names if d not in w1_exact
              for r in launch_rows if r['launch'] == d and r['model'] == MODEL) + ').')
w('- **A CatLog paper** = its agents in the launch whose rows were kept (the last launch that ran agents for it, as the '
  f'kit\'s `a6_kept_agents` picks; {", ".join(kept_launches)}, all completed) plus an equal share of that launch\'s own '
  f'session over the papers its launch line names. {ER["catlog_papers_with_earlier_agents"]} of the 83 papers also have '
  f'agents in earlier launches that a usage limit stopped ({", ".join(stopped)}); these agents, the earlier launches\' '
  'session shares and earlier plain sessions are counted apart.')
w(f'- **List prices** are Claude Code\'s own cost figures: every record gives `costBasis` "list", and one price table '
  f'gives all {n_cc_records} records\' `costUSD` (every plain session record and every launch\'s `session.json`) to '
  f'within {max(v["largest_difference_usd"] for v in cc_fit.values()):.0e} USD. Per million tokens: claude-opus-5-5 '
  f'{usd(o55[0])} input, {usd(o55[1])} output, {usd(o55[2])} cache read, {usd(o55[3])} per 5-minute and {usd(o55[4])} '
  f'per 1-hour cache write ({W5_X:g} and {W1_X:g} x input); claude-sonnet-5-5 {usd(s55[0])}, {usd(s55[1])}, '
  f'{usd(s55[2])}, {usd(s55[3])} per 5-minute write. These are also the prices in the claude-api reference that ships '
  'with Claude Code; nothing was checked over the network.')
w(f'- **The r01b rule** (`r01b_cost.py`, as `cost_summary.json` states it), used for the catalogue\'s earlier estimate: '
  f'claude-opus-5-5 {usd(PRICE[MODEL][0])} input, {usd(PRICE[MODEL][1])} output, {usd(PRICE[MODEL][2])} cache read; '
  f'claude-opus-5 {usd(PRICE["claude-opus-5"][0])}, {usd(PRICE["claude-opus-5"][1])}, {usd(PRICE["claude-opus-5"][2])}; '
  f'claude-sonnet-5-5 {usd(PRICE["claude-sonnet-5-5"][0])}, {usd(PRICE["claude-sonnet-5-5"][1])}, '
  f'{usd(PRICE["claude-sonnet-5-5"][2])}; every cache write at {WRITE:g} x input, the 5-minute rate. For CatLog\'s '
  'agents the two price sets give the same cost; they differ on 1-hour writes (every write of the plain sessions, and '
  'of CatLog\'s launch sessions) and on claude-sonnet-5-5\'s cache read.')
w('- **Per value**: a paper\'s cost over its values (papers with at least one value), and pooled: the 83 papers\' cost '
  'over all their values. Values judged supported = stored values less those judged wrong. No value was left '
  f'undecided, and the {ps["plain"]["values_agreed_not_judged"]} agreeing values per side that were not sampled count '
  f'as supported, as in the registered analysis ({ps["plain"]["sample"]["wrong"]} of the {ps["plain"]["sample"]["of"]} '
  'sampled agreeing pairs was wrong).')
w(f'- **Summaries**: medians with interquartile ranges (quartiles by linear interpolation); ratios are CatLog over the '
  f'plain reading for the same paper; 95% intervals for ratios of totals and of pooled costs by a paired paper '
  f'bootstrap ({B:,} resamples, seed {SEED}, as the locked test\'s analysis). Time: the plain session\'s seconds; for '
  'CatLog, the summed time of its agents, each from its transcript\'s first to last entry as the audit gives them.')
w('')
w('## Numbers: the 83 papers at list prices')
w('')
w('| | Plain reading | CatLog | CatLog over plain |')
w('|---|---|---|---|')
w(f'| Cost per paper, median (IQR) | {mid(lp_["per_paper"])} | {mid(lc_["per_paper"])} | '
  f'{mid(lr["per_paper"], 2, x2)}, paired; higher for CatLog in {lr["papers_catlog_dearer"]} of 83 |')
w(f'| Cost per stored value, median (IQR) | {mid(lp_["per_stored_value"], 3)} | {mid(lc_["per_stored_value"], 3)} | '
  f'{mid(lr["per_stored_value"], 2, x2)}, paired |')
w(f'| Cost per value judged supported, median (IQR) | {mid(lp_["per_supported_value"], 3)} | '
  f'{mid(lc_["per_supported_value"], 3)} | {mid(lr["per_supported_value"], 2, x2)}, paired |')
w(f'| Pooled per stored value | {usd(lp_["pooled_per_stored_value"], 3)} ({lp_["values"]:,} values) | '
  f'{usd(lc_["pooled_per_stored_value"], 3)} ({lc_["values"]:,}) | {x2(lr["pooled_per_stored_value"])} '
  f'(95% interval {ci(lr["pooled_per_stored_value_ci"])}) |')
w(f'| Pooled per value judged supported | {usd(lp_["pooled_per_supported_value"], 3)} ({lp_["supported_values"]:,}) | '
  f'{usd(lc_["pooled_per_supported_value"], 3)} ({lc_["supported_values"]:,}) | '
  f'{x2(lr["pooled_per_supported_value"])} (95% interval {ci(lr["pooled_per_supported_value_ci"])}) |')
w(f'| Total, 83 papers | {usd(lp_["total"])} | {usd(lc_["total"])} | {x2(lr["of_totals"])} (95% interval '
  f'{ci(lr["of_totals_ci"])}), ratio of totals |')
w(f'| Tokens per paper, millions, median (IQR) | {mid(T["plain"]["per_paper"], 2, mtok)} | '
  f'{mid(T["catlog"]["per_paper"], 2, mtok)} | {x2(T["ratio_of_totals"])}, ratio of totals |')
w(f'| Cache reads, share of all tokens | {pct(T["plain"]["cache_read_share"])} | {pct(T["catlog"]["cache_read_share"])} | |')
w(f'| Output tokens per paper, thousands, median | {x2(T["plain"]["output_per_paper"]["median"] / 1e3, 1)} | '
  f'{x2(T["catlog"]["output_per_paper"]["median"] / 1e3, 1)} | '
  f'{x2(T["catlog"]["output_total"] / T["plain"]["output_total"])}, ratio of totals |')
w(f'| Seconds per paper, median (IQR): the plain session; CatLog\'s agents summed | {mid(S["plain_session"], 0, x2)} | '
  f'{mid(S["catlog_agent_seconds"], 0, x2)} | {x2(S["ratio_of_totals"])}, ratio of totals |')
w('')
w('## The same at the r01b rule (every cache write at the 5-minute rate)')
w('')
w('| | Plain reading | CatLog | CatLog over plain |')
w('|---|---|---|---|')
w(f'| Cost per paper, median (IQR) | {mid(rp_["per_paper"])} | {mid(rc_["per_paper"])} | '
  f'{mid(rr["per_paper"], 2, x2)}, paired; higher for CatLog in {rr["papers_catlog_dearer"]} of 83 |')
w(f'| Cost per stored value, median (IQR) | {mid(rp_["per_stored_value"], 3)} | {mid(rc_["per_stored_value"], 3)} | '
  f'{mid(rr["per_stored_value"], 2, x2)}, paired |')
w(f'| Cost per value judged supported, median (IQR) | {mid(rp_["per_supported_value"], 3)} | '
  f'{mid(rc_["per_supported_value"], 3)} | {mid(rr["per_supported_value"], 2, x2)}, paired |')
w(f'| Pooled per stored value | {usd(rp_["pooled_per_stored_value"], 3)} | {usd(rc_["pooled_per_stored_value"], 3)} | '
  f'{x2(rr["pooled_per_stored_value"])} (95% interval {ci(rr["pooled_per_stored_value_ci"])}) |')
w(f'| Pooled per value judged supported | {usd(rp_["pooled_per_supported_value"], 3)} | '
  f'{usd(rc_["pooled_per_supported_value"], 3)} | {x2(rr["pooled_per_supported_value"])} (95% interval '
  f'{ci(rr["pooled_per_supported_value_ci"])}) |')
w(f'| Total, 83 papers | {usd(rp_["total"])} | {usd(rc_["total"])} | {x2(rr["of_totals"])} (95% interval '
  f'{ci(rr["of_totals_ci"])}), ratio of totals |')
w('')
w(f'- **CatLog by role**, per paper (median, IQR; the same at both price sets): reader {mid(BR["read"])}, verifier '
  f'{mid(BR["verify"])}; the missed-values verifier ran on {BR["verify_missed_papers"]} papers '
  f'({usd(BR["verify_missed_total"])} in all); the launch sessions\' shares {usd(BR["launch_share_total_list"])} in all '
  f'at list prices ({usd(BR["launch_share_total_r01b"])} at the r01b rule). The reader alone cost a median of '
  f'{x2(BR["read_over_plain_paired_list"]["median"])} times the plain reading of the same paper.')
c34 = locked['catlog_34_counted_right']
w(f'- **The 34 unit changes counted as right** (found after the result): every CatLog value is then supported, '
  f'{usd(c34["list_prices"]["pooled_per_supported_value"], 3)} per value pooled, ratio '
  f'{x2(c34["list_prices"]["ratio_pooled_per_supported_value"])} (95% interval {ci(c34["list_prices"]["ci"])}); at the '
  f'r01b rule {x2(c34["r01b_rule"]["ratio_pooled_per_supported_value"])} ({ci(c34["r01b_rule"]["ci"])}).')
EAL = ER['catlog_agents_by_launch']
w(f'- **Earlier runs of the same papers, left out above.** Launches that a usage limit stopped had run '
  f'{ER["catlog_agents"]} agents on {ER["catlog_papers_with_earlier_agents"]} of the 83 papers '
  + (f'({usd(ER["catlog_agents_cost_list"])} at both price sets: '
     if usd(ER["catlog_agents_cost_list"]) == usd(ER["catlog_agents_cost_r01b"]) else
     f'({usd(ER["catlog_agents_cost_list"])} at list prices, {usd(ER["catlog_agents_cost_r01b"])} at the r01b rule: ')
  + ', '.join(f'{d} on {EAL[d]["papers"]} papers' for d in stopped) +
  f'; {ER["catlog_earlier_agents_refused"]} of these agents logged a refusal and carried on). The own sessions of the '
  f'earlier launches ({", ".join(sorted(ESL, key=rank.get))}) add shares on {ER["catlog_papers_with_earlier_shares"]} '
  f'papers ({usd(ER["catlog_shares_cost_list"])} at list prices, {usd(ER["catlog_shares_cost_r01b"])} at the r01b '
  f'rule); ' + ', '.join(f'{d} ran no agent: its own session was refused '
                         f'({usd(WR["catlog_refused_launch_sessions"][d]["cost_list"])} for the whole session at list '
                         f'prices, {usd(WR["catlog_refused_launch_sessions"][d]["cost_r01b"])} at the r01b rule, shared '
                         f'over the {len(launch_info[d]["named"])} papers it names, {ESL[d]["papers"]} of them analysed)'
                         for d in refused_launch) +
  f'. Earlier plain sessions: {ER["plain_sessions"]} on {ER["plain_papers"]} papers ({usd(ER["plain_cost_list"])} at '
  f'list prices, {usd(ER["plain_cost_r01b"])} at the r01b rule). With all of these the 83 papers cost '
  f'{usd(WE["list_prices"]["catlog_total"])} and {usd(WE["list_prices"]["plain_total"])} at list prices (ratio '
  f'{x2(WE["list_prices"]["ratio_of_totals"])}), {usd(WE["r01b_rule"]["catlog_total"])} and '
  f'{usd(WE["r01b_rule"]["plain_total"])} at the r01b rule (ratio {x2(WE["r01b_rule"]["ratio_of_totals"])}).')
w(f'- **Whole runs** (all 119 listed papers: left-out papers, refusals, retries and stopped runs included): plain '
  f'{WR["plain_sessions"]} sessions, {usd(WR["plain_cost_list"])} at list prices ({usd(WR["plain_cost_r01b"])} at the '
  f'r01b rule), {WR["plain_refused_sessions"]} of them refused ({usd(WR["plain_refused_sessions_cost_list"])} at list '
  f'prices, {usd(WR["plain_refused_sessions_cost_r01b"])} at the r01b rule); CatLog {WR["catlog_launches"]} launches, '
  f'{usd(WR["catlog_cost_list"])} from the audit\'s counts at list prices ({usd(WR["catlog_cost_r01b"])} at the r01b '
  f'rule, the audit\'s own `usd_total`), and {usd(WR["catlog_session_total_cost_usd"])} by the launches\' own '
  f'`session.json` totals, which also count refused requests; {WR["catlog_refused_agents"]} agents logged a refusal, '
  f'on {WR["catlog_refused_agents_papers"]} papers ('
  + (f'{usd(WR["catlog_refused_agents_cost_list"])} at both price sets'
     if usd(WR["catlog_refused_agents_cost_list"]) == usd(WR["catlog_refused_agents_cost_r01b"]) else
     f'{usd(WR["catlog_refused_agents_cost_list"])} at list prices, {usd(WR["catlog_refused_agents_cost_r01b"])} at the '
     'r01b rule') +
  f'), and {WR["catlog_retry_agents"]} retry agents ran on '
  f'claude-sonnet-5-5 ({usd(WR["catlog_retry_agents_cost_list"])} at list prices, '
  f'{usd(WR["catlog_retry_agents_cost_r01b"])} at the r01b rule). No refused agent or retry is among the analysed '
  'papers\' kept agents, and no kept plain session logged a safety stop.')
w(f'- **The check against the launches\' totals**: `session.json` counts {usd(WR["catlog_gap_cost_list"])} more than '
  'the audit at list prices, all in launches where an agent logged a refusal: input that refused requests used and the '
  'transcripts do not hold (`launch_check.tsv`). It is in no paper\'s cost. On the plain side, the records count more '
  f'than their transcripts only for refused sessions ({WR["plain_audit_records_count_more"]} of '
  f'{WR["plain_sessions"]}); total_cost_usd, the figure used, counts them.')
w('')
w('## Second set: the random test\'s plain reading (147 papers)')
w('')
rl, rb = rand['cost_list'], rand['cost_r01b']
w('| | List prices | r01b rule |')
w('|---|---|---|')
w(f'| Cost per paper, median (IQR) | {mid(rl["per_paper"])} | {mid(rb["per_paper"])} |')
w(f'| Cost per stored value, median (IQR) | {mid(rl["per_stored_value"], 3)} | {mid(rb["per_stored_value"], 3)} |')
w(f'| Pooled per stored value ({rand["values"]:,} values) | {usd(rl["pooled_per_stored_value"], 3)} | '
  f'{usd(rb["pooled_per_stored_value"], 3)} |')
w(f'| Pooled per value judged supported ({rand["supported_values"]:,}: less the wrong and the {rand["cannot_decide"]} '
  f'undecided) | {usd(rl["pooled_per_supported_value"], 3)} | {usd(rb["pooled_per_supported_value"], 3)} |')
w(f'| Total | {usd(rl["total"])} | {usd(rb["total"])} |')
w(f'| Without the {len(rand["papers_with_a_retry"])} failed first sessions: total; per stored value, median; pooled | '
  f'{usd(rl["without_failed_first_sessions"]["total"])}; {usd(rl["without_failed_first_sessions"]["per_stored_value"]["median"], 3)}; '
  f'{usd(rl["without_failed_first_sessions"]["pooled_per_stored_value"], 3)} | '
  f'{usd(rb["without_failed_first_sessions"]["total"])}; {usd(rb["without_failed_first_sessions"]["per_stored_value"]["median"], 3)}; '
  f'{usd(rb["without_failed_first_sessions"]["pooled_per_stored_value"], 3)} |')
w('')
w(f'A paper\'s cost is every session of its kept invocation: `.a1`, and `.a2` where the kit\'s one retry ran after a '
  f'session with no valid read ({len(rand["papers_with_a_retry"])} papers here, none in the locked set); those failed '
  f'first sessions cost {usd(rl["failed_first_sessions"])} at list prices ({usd(rb["failed_first_sessions"])} at the '
  f'r01b rule). {len(rand["papers_with_a_safety_stop"])} papers\' kept sessions logged a safety stop, the two failed '
  f'ones among them. The kit\'s audit gives the records\' four token counts for {r_audit["equal"]} of the '
  f'{sum(r_audit.values())} kept sessions; for {", ".join(r_audit_more) or "none"} the record counts more than the '
  f'transcript holds, and the record is what is priced. Tokens per paper {mid(rand["tokens_per_paper"], 2, mtok)} '
  f'million; seconds {mid(rand["seconds_per_paper"], 0, x2)}. CatLog\'s side of that test is its catalogue, so it has '
  'no run of its own to price.')
w('')
w('## Context: CatLog\'s cost per paper in the catalogue, by role')
w(f'`r01b_cost.py`\'s rule on `tokens_per_agent.tsv` ({len(rows):,} subagents whose transcripts were on disk when it was '
  f'built; agents started from {prod["first_agent_start_utc"][:10]} to {prod["last_agent_start_utc"][:10]} UTC, the '
  f'reading and verifying agents to {prod["last_read_verify_start_utc"][:16].replace("T", " ")} UTC). The rerun gives '
  f'`cost_summary.json` exactly. Per paper over the {prod["papers_with_read_and_verify"]:,} papers with a reading and a '
  f'verifying transcript; checks spread over the {prod["papers_added_by_then"]:,} papers added by then '
  '(`pipeline_stats.json`). The table does not split cache writes by lifetime; the r01b rule prices them as 5-minute '
  'writes, which is what every agent of the frozen run wrote.')
w('')
w('| Role | Agents | Per paper, median (IQR) | Mean per paper | Total |')
w('|---|---|---|---|---|')
for role, name in (('read', 'Reader (re-reads summed)'), ('verify', 'Verifier'), ('verify_missed', 'Missed-values verifier')):
    x = prod['roles'][role]
    med = mid(x['per_paper']) if role != 'verify_missed' else f'{usd(0)} ({x["papers_with_one"]} papers had one: median {usd(x["per_paper_with_one"]["median"])})'
    w(f'| {name} | {x["agents"]:,} | {med} | {usd(x["per_paper"]["mean"])} | {usd(x["total_on_these_papers"])} |')
x = prod['roles']['read_verify_missed']['per_paper']
w(f'| Read + verify + missed | | {mid(x)} | {usd(x["mean"])} | {usd(x["sum"])} |')
for role, name in (('audit', 'Audit'), ('dbcheck', 'Database check'), ('scale_check', 'Unit-factor check'),
                   ('scale_refute', 'Unit-factor refuters'), ('scale_second', 'Unit-factor second look')):
    x = prod['roles'][role]
    w(f'| {name} | {x["agents"]:,} | | {usd(x["per_paper_added"], 3 if x["per_paper_added"] >= 0.001 else 4)} per paper '
      f'added | {usd(x["total_all_agents"])} |')
w(f'| Audits, database checks and unit-factor checks | {prod["classified_checks_agents"]:,} | | '
  f'{usd(prod["classified_checks_per_paper_added"], 3)} per paper added | {usd(prod["classified_checks_total"])} |')
w('')
RS = prod['reprint_sweep_named_runs']
w(f'- **Later checks cost at least {usd(prod["classified_checks_per_paper_added"], 3)} per paper added.** The table '
  'classifies only the roles above; other later checks are among its unclassified agents '
  f'({prod["not_counted"]["other"]["agents"]:,}, {usd(prod["not_counted"]["other"]["total"])}). For example, the '
  f'{len(RS["runs"])} workflow runs that the reprint sweep\'s handoff names ran {RS["agents"]} of them '
  f'({usd(RS["total"])}, {usd(RS["per_paper_added"], 3)} per paper added). With every unclassified agent counted as a '
  f'check, later checks would cost {usd(prod["later_checks_at_most_per_paper_added"], 3)} per paper added.')
SL = prod['read_verify_missed_sonnet_cache_read_at_list']
w(f'- Not counted: browser downloads ({prod["not_counted"]["chrome_lane"]["agents"]} agents, '
  f'{usd(prod["not_counted"]["chrome_lane"]["total"])}). Agent counts include the {cs["unpriced_agents"]} the table '
  f'cannot price. The table records no effort setting. With claude-sonnet-5-5\'s list cache-read price '
  f'({usd(s55[2])} instead of {usd(PRICE["claude-sonnet-5-5"][2])}; {SL["sonnet_read_verify_agents"]} reading and '
  f'verifying agents on {SL["papers_with_a_sonnet_agent"]} papers) read + verify + missed is {mid(SL["per_paper"])} per '
  f'paper, {usd(-SL["difference_total"])} less in all.')
w('')
w('## For the paper')
for s_ in sentences:
    w(f'- {s_}')
w('')
w('## Read with care')
w('- List-price equivalents, not what was paid: the work ran on a subscription with a usage limit.')
w(f'- The price set matters for the plain reading, not for CatLog\'s agents. The plain sessions write only 1-hour cache '
  f'entries, which list at {usd(o55[4])} per million; the r01b rule charges them {usd(o55[3])}, so at that rule the '
  f'plain reading costs {usd(lp_["total"] - rp_["total"])} less over the 83 papers and the ratio of totals rises from '
  f'{x2(lr["of_totals"])} to {x2(rr["of_totals"])}. CatLog\'s launch sessions also write 1-hour entries: '
  f'{usd(lc_["total"] - rc_["total"])} over the 83 papers. The kit\'s audit `usd` fields use the r01b rule.')
w('- The per-paper figures carry no refusal or retry cost: no counted agent or session logged one. By the test\'s '
  f'rules a paper with a refused plain session, or with a CatLog agent that refused and was retried on another model, '
  f'left the set ({EXITS_REFUSED} of the {EXITS} exits). Running CatLog on papers the safety filter flags costs more '
  'than these figures show; the whole-run line gives what refusals and retries cost here.')
w('- CatLog\'s per-paper figures also leave out the earlier launches and the refused requests\' input that only '
  '`session.json` counts (both given above), and they include an equal share of the launch session, which runs the '
  'workflow and the add step.')
w('- Per value medians leave out the one paper on each side with no value; the pooled figures keep its cost.')
w('- Time is measured differently on each side: CatLog\'s per-paper time adds up its agents\' transcript spans (they ran '
  f'{launch_info["main"]["lanes"]} papers at a time), while the plain figure is the session\'s process time.')
w('- The agents\' own effort setting is recorded only in their transcripts, which this script does not open; the launch '
  'commands set `--effort max`.')
MRV = prod['models_read_verify']
w(f'- The catalogue context is a different setting: production prompts of their day, several models (reading and '
  f'verifying agents: {", ".join(f"{m} {n:,}" for m, n in sorted(MRV.items(), key=lambda x: -x[1]) if m in PRICE)}, '
  f'and {sum(n for m, n in MRV.items() if m not in PRICE):,} with no priced model), re-reads summed, transcripts only '
  'of agents still on disk when the table was built. The frozen '
  f'run\'s median per paper at the r01b rule ({usd(rc_["per_paper"]["median"])}) is more than twice the catalogue\'s '
  f'read + verify median ({usd(prod["roles"]["read_verify_missed"]["per_paper"]["median"])}); the records do not say why.')
w('- The kit\'s audit counted each agent\'s tokens from its transcript; Claude Code deletes transcripts after 30 days '
  'unless they are archived, and `audit.json` and `per_agent_locked.tsv` keep the counts.')
w('')
w('## Rerun')
w(f'`python3 -I -B {os.path.join(HERE, "cost.py")}` (a few seconds; reads only the two folders above and no transcript, '
  f'writes the files below next to itself and stops on any failed check: {len(CHECKS)} kinds of check, '
  f'{sum(CHECKS.values()):,} tests, listed in `results.json`).')
w('')
w('## Files')
w('- `cost.py`: this analysis.')
w('- `results.json`: every number above and more, the prices, the paper sentences (`draft_text`), the checks passed, '
  'input hashes.')
w('- `per_paper_locked.tsv`: the 83 papers, both sides: values, supported values, sessions or kept launch, cost at both '
  'price sets, tokens, time, CatLog by role, earlier runs.')
w('- `per_agent_locked.tsv`: every CatLog agent and launch session of the 12 launches (how its launch ended): model, '
  'tokens by kind, time, cost at both price sets, refusals, retry, the transcript the audit read.')
w('- `launch_check.tsv`: per launch and model, the audit\'s tokens against `session.json`.')
w('- `per_paper_random.tsv`: the random test\'s 147 papers, plain side.')
w('- `production_roles.tsv`: the catalogue\'s cost by role.')
open(os.path.join(HERE, 'README.md'), 'w').write('\n'.join(md) + '\n')
print('\n'.join(sentences))
print(len(CHECKS), 'kinds of check passed,', sum(CHECKS.values()), 'tests')
