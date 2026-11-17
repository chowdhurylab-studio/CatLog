"""Does CatLog's error rate fall as people's and agents' finds become rules? Measured from the random audit.

Run:  python3 build_learning.py          (from anywhere; writes only into this folder)

Reads, all read-only:
  log.tsv                     audit_keep / audit_drop lines (the verdicts), sampled lines (the rounds), add / recover /
                              drop lines (papers read so far, values in the catalogue), relabelled lines (dropped
                              values back under a corrected organism label). Only the first LOG_LINES lines: the
                              snapshot this folder was built from (README gives its sha256).
  catlog.py                   imported for audit_targeted (which audit lines are outside the random audit), kv (log
                              fields), relabelled_drops (the label corrections) and audit_summary (the count this build
                              must reproduce, run on the snapshot's lines). Nothing is called that writes.
  catalog.jsonl, rejected.jsonl   the audited rows' own fields: when each was added, its reader model; whether a
                              relabelled value is still in the catalogue (relabelled_drops).
  sources/provenance_backfill.tsv the reader model of rows added before models were stamped on rows.
  papers.tsv, config.json, sources/<lists>.txt   each paper's text route and the list that queued it.
  paper/figures/method_overview/v5/taxonomy.tsv   the 85 kinds of error and the commit that made each a rule.
  git history                 commit times of those rules and of prompts/read.md, prompts/verify.md, catlog.py.

Writes (this folder): learning.csv (one row per audit round), learning_bins.csv (rounds and values in 8 groups of
about equal size), rules_by_papers.csv (one row per kind of error), drops.csv (each value the random audit found
wrong), tests.json (every trend test and comparison quoted in README.md).
"""
import bisect
import csv
import json
import math
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import statsmodels.api as sm
from scipy import stats as st

HERE = Path(__file__).resolve().parent
ROOT = Path('<the CatLog folder>')
LOG_LINES = 124753          # log.tsv lines read (the snapshot; log.tsv is append-only)
sys.path.insert(0, str(ROOT))
import catlog  # noqa: E402

AUDIT_DESIGN = (  # (commit, what changed in how the random audit samples or judges), from git log of the audit files
    ('e8d2290', 'B'),   # two thirds of each sample from the values added since the last audit (before: catalogue-wide)
    ('045fd0e', 'C'),   # sample size 7% of the values added since the last audit, at least 12 (before: 12 per 300);
                        # rows a database check flagged are audited apart and left out; auditors blind to databases
                        # since c722037, 2 hours earlier
    ('694668f', 'D'),   # 6 auditors at a time instead of 3; same instructions
)
DESIGN_TEXT = {
    'A': '12 rows drawn from the whole catalogue for every 300 values added',
    'B': '12 rows per 300 values; two thirds from values added since the last audit',
    'C': '7% of the values added since the last audit (at least 12); two thirds of them new',
    'D': 'as C, 6 auditors at a time',
}

# Each value the random audit found wrong, put in its kind of error (taxonomy.tsv id) by reading the auditor's reason in
# log.tsv in full. The two values it dropped for a wrong organism label alone (18620421; nearest kind PP8, open) came
# back under the corrected label: label corrections (LABELS), not wrong values, so they have no kind here.
KIND = {
    '2915f1e1292fb682': 'CU2', 'b5d71573f8ac5dcb': 'PP1', '8f0a9f458d764de2': 'RA3', 'e08d46429605abbb': 'PP2',
    'bc67b6b55224238e': 'RA3', '0801ba3d9ded1e13': 'RA3', '5a5ef64ab0a1ef0f': 'RA1', 'cc08efb605b01c69': 'IP11',
    '76291a8572c3430e': 'PP2', 'e5af34ff68e52efd': 'PP2', '565f019e4e3b3afb': 'PP2', 'c749258eb5ca5f6c': 'PP2',
    'a6c353b225a24eeb': 'PP2', '9f88602eae7a3656': 'PP2', '761c9376e7f534f0': 'RA3', '356ea37befb517c0': 'TL6',
    'b747f756d8a29e16': 'PP2', '0ebd25a81b032ad0': 'PP2', '3aaa254e9f3f5ba4': 'RA1', 'f7e920821c2763d1': 'PP1',
    'ede44dfc7862336a': 'IP11', '36a6151199ec70f1': 'IP12', '881df8a0413d19b2': 'PP2', '8bd41bcbee3a7389': 'RA1',
    '2287ba6ada15f0f3': 'PP2', 'a1a366af7c1697e6': 'PP1', 'a95e0d71196509f4': 'PP1', '2cdfcb9aa2dd230a': 'RA3',
    '50d752087807a291': 'PP2', 'c52be9f0fc3659aa': 'PP1', '1fd6f5193fb8c3bf': 'PP1', 'e13a0af2e34074d1': 'RA1',
    'dc84dd58aefdc84e': 'PP2', '50d47a65f9b99d38': 'PP2', '3ee490cf439f45dd': 'PP1', 'a5469323e736ee72': 'IP11',
    '7da021c42a6e6297': 'RA1', '433aa9a3b7895db7': 'RA8', '1c209523f603bfc6': 'PP2', '9bc4e03f2a1839f5': 'IP12',
    'a3b221750fa455b0': 'PP1', '28bdfdd3d6216486': 'PP2', '0d7a1ee69cfed920': 'PP2', 'a5cae02fb28c4d1c': 'PP2',
    '87be7e396327b79d': 'PP2', '7edb40f387c40443': 'PP1', '6f0284bf849d6b26': 'PP2', '6c2a2afb95c3d046': 'PP3',
    'f772f97bab584d62': 'PP4', '93857679fdcf1aa8': 'PP2', '8fbda81aa590d2fe': 'PP2', '25bb195c8605ead7': 'RA1',
    '162f1195f86dd922': 'PP2', '6a7f07394bdb01dc': 'PP2', '0a095a7f8edb64c7': 'RA4', '2f1f806966b071db': 'PP1',
    'b050dfe004ea6541': 'RA1', '1acbee8c52ae5a5c': 'PP1', 'b3609f6202e02742': 'PP1', '8b828761baecec7b': 'PP4',
    'b4ae22e7e38d3622': 'RA3', '5ec8a1579bb34a0f': 'PP2', 'c22c839783f53eca': 'RA3', '14f678ffafb68ccd': 'RA3',
    'e3628eeabb456499': 'RA3', 'df78a308bcd47382': 'RA3', 'fe1ccb6481669a66': 'PP2', '843445ff1489c20e': 'PP2',
    '938493b702444f59': 'PP2',
}
GROUP = {  # plain words for each kind that occurs
    'PP2': 'copied from earlier work', 'RA3': 'part of a constant', 'RA1': 'another constant',
    'PP1': 'unit or scale', 'RA4': 'unit or scale', 'RA8': 'unit or scale',
    'IP11': 'wrong label', 'IP12': 'wrong label',
    'PP4': 'slipped cell', 'PP3': 'slipped cell', 'TL6': 'scan misread', 'CU2': 'code added a ±',
}
ERROR_TYPE = {'FA': 'wrong value kept', 'FR': 'right value lost', 'PROC': 'process'}


def wilson(k, n, z=1.959964):
    if n == 0:
        return float('nan'), float('nan')
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - h) / d), min(1.0, (c + h) / d)


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True).stdout


def commit_time(c):
    s = git('show', '-s', '--format=%ci', c).strip()
    return s[:16] if s else None


# ---------------------------------------------------------------------------------------------------------------
# 1. log.tsv: the running state after each line
ev, SNAP = [], []             # SNAP: the snapshot's lines as catlog.events() gives the whole log
with open(ROOT / 'log.tsv') as fh:
    for i, line in enumerate(fh, 1):
        if i > LOG_LINES:
            break
        f = line.rstrip('\n').split('\t')
        if len(f) >= 3:
            SNAP.append(f)
        if len(f) >= 3 and re.match(r'\d{4}-\d\d-\d\d', f[0]):
            ev.append((i, f))
assert i >= LOG_LINES, f'log.tsv has {i} lines, fewer than the snapshot'
# audit drops whose value came back under a corrected organism label: label corrections, not wrong values
# (catlog.audit_summary leaves them out of wrong and counts them apart)
LABELS = catlog.relabelled_drops(SNAP)
LINES = [i for i, _ in ev]
TIMES = [f[0][:16] for _, f in ev]
LINE_TIME = dict(zip(LINES, TIMES))
assert TIMES == sorted(TIMES), 'log.tsv times are expected to run forward'

papers, reads, values = set(), 0, 0
state = {}                    # line -> (papers read so far, reads incl. re-reads, values in the catalogue)
adds_of = defaultdict(list)   # pmid -> [(minute, line)] of its add lines
for i, f in ev:
    if f[2] == 'add':
        values += catlog.kv(f, 'kept')
        adds_of[f[1]].append((f[0][:16], i))
        if 'pass=censored' not in f[3:]:       # a censored-only pass reads no new paper (as status counts)
            reads += 1
            papers.add(f[1])
    elif f[2] == 'recover':
        values += catlog.kv(f, 'kept')
    elif f[2] == 'drop':
        values -= 1
    state[i] = (len(papers), reads, values)


def state_at_time(t):
    k = bisect.bisect_right(TIMES, t[:16]) - 1
    return (0, 0, 0) if k < 0 else state[LINES[k]]


def state_before_line(n):
    k = bisect.bisect_left(LINES, n) - 1
    return (0, 0, 0) if k < 0 else state[LINES[k]]


# ---------------------------------------------------------------------------------------------------------------
# 2. verdicts, the random rows and their rounds
aud = [(i, f) for i, f in ev if f[2] in ('audit_keep', 'audit_drop') and len(f) > 3]
samples = [(i, f) for i, f in ev if f[2] == 'sampled']
by_row = defaultdict(list)
for i, f in aud:
    by_row[f[3]].append((i, f))
random_rows = {r for r, ls in by_row.items() if any(not catlog.audit_targeted(f) for _, f in ls)}


def outcome(ls):
    """Latest verdict, as catlog.audit_summary counts it: a keep that supersedes a drop is a keep, and a drop whose
    value came back under a corrected organism label (LABELS) is a label correction, not a wrong value."""
    f = ls[-1][1]
    if f[2] == 'audit_drop':
        return 'label corrected' if f[3] in LABELS else 'dropped'
    return 'unit corrected' if ' '.join(f[4:]).startswith('unit corrected') else 'kept'


first_rand = {r: next((i, f) for i, f in by_row[r] if not catlog.audit_targeted(f)) for r in random_rows}
first_sample_line = samples[0][0]
rounds = []
# before sample lines were logged: a round is a burst of verdict lines (a gap over 20 minutes starts the next)
cur = []
for i, f, r in sorted((i, f, r) for r, (i, f) in first_rand.items() if i < first_sample_line):
    if cur and (datetime.strptime(f[0][:16], '%Y-%m-%d %H:%M')
                - datetime.strptime(cur[-1][1][0][:16], '%Y-%m-%d %H:%M')).total_seconds() > 20 * 60:
        rounds.append({'how': 'burst', 'rows': cur, 'anchor_line': cur[0][0], 'anchor_time': cur[0][1][0][:16],
                       'sample_rows': ''})
        cur = []
    cur.append((i, f, r))
if cur:
    rounds.append({'how': 'burst', 'rows': cur, 'anchor_line': cur[0][0], 'anchor_time': cur[0][1][0][:16],
                   'sample_rows': ''})
# from the first sample line on: a verdict belongs to the latest sample line before it; a sample whose verdicts fall
# short of its size is joined with the next sample when that one holds more verdicts than its size (a second sample
# logged while the first audit's verdicts were still being recorded: 376 rows, then 12, on one night)
sl = [i for i, _ in samples]
srows = [catlog.kv(f, 'rows') for _, f in samples]
groups = defaultdict(list)
for i, f, r in sorted((i, f, r) for r, (i, f) in first_rand.items() if i >= first_sample_line):
    groups[bisect.bisect_right(sl, i) - 1].append((i, f, r))
taken = set()
for k in sorted(groups):
    if k in taken:
        continue
    members = [k]
    while True:
        have = sum(len(groups.get(m, [])) for m in members)
        want = sum(srows[m] for m in members)
        nxt = members[-1] + 1
        if nxt in groups and have < want and len(groups[nxt]) > srows[nxt]:
            members.append(nxt)
            taken.add(nxt)
        else:
            break
    rounds.append({'how': 'sample' if len(members) == 1 else 'two samples joined',
                   'rows': sorted(x for m in members for x in groups[m]), 'anchor_line': samples[k][0],
                   'anchor_time': samples[k][1][0][:16], 'sample_rows': sum(srows[m] for m in members)})
rounds.sort(key=lambda rd: rd['anchor_line'])
for n, rd in enumerate(rounds, 1):
    rd['n'] = n
    rd['papers_read'], rd['reads'], rd['values_in_catalogue'] = (
        state[rd['anchor_line']] if rd['how'] != 'burst' else state_before_line(rd['anchor_line']))
    design = 'A'
    for c, d in AUDIT_DESIGN:
        if rd['anchor_time'] >= commit_time(c):
            design = d
    rd['design'] = design
anchors = [rd['anchor_line'] for rd in rounds]
for rd in rounds:
    rd['targeted_lines'] = rd['targeted_drops'] = 0
for i, f in aud:  # verdicts outside the random audit, counted in the round window they fall in (left out of the rate)
    if catlog.audit_targeted(f):
        k = bisect.bisect_right(anchors, i) - 1
        if k >= 0:
            rounds[k]['targeted_lines'] += 1
            rounds[k]['targeted_drops'] += f[2] == 'audit_drop'

# ---------------------------------------------------------------------------------------------------------------
# 3. the audited rows' own fields (a regex picks the lines; only those are parsed)
want = set(random_rows)
rowinfo = defaultdict(list)
rx_id = re.compile(r'"row_id": "(\w+)"')
for src in ('catalog', 'rejected'):
    with open(ROOT / f'{src}.jsonl') as fh:
        for line in fh:
            m = rx_id.search(line)
            if m and m.group(1) in want:
                r = json.loads(line)
                rowinfo[r['row_id']].append({k: r.get(k) for k in ('pmid', 'metric', 'added', 'checked', 'reader_model')})
assert set(rowinfo) == want, f'rows not found: {sorted(want - set(rowinfo))[:5]}'
backfill = {r['row_id']: r['reader_model'] for r in
            csv.DictReader(open(ROOT / 'sources/provenance_backfill.tsv'), delimiter='\t')}


def added_time(rid):
    a = sorted({x['added'][:16] for x in rowinfo[rid] if x.get('added')})
    if a:
        return a[0]
    c = sorted({x['checked'][:16] for x in rowinfo[rid] if x.get('checked')})
    return c[0] if c else None


def add_line_for(pmid, t):
    cand = [i for tt, i in adds_of.get(pmid, []) if tt <= t]
    return cand[-1] if cand else None


# a row with no model of its own and none in the backfill (rows dropped before models were stamped): the model of the
# same paper's rows added in the same minute (the same reader agent)
need = {rid for rid in want if not any(x.get('reader_model') for x in rowinfo[rid]) and not backfill.get(rid)}
need_p = {rowinfo[rid][0]['pmid']: None for rid in need}
same = defaultdict(Counter)
rx_p, rx_a, rx_m = re.compile(r'"pmid": "([^"]+)"'), re.compile(r'"added": "([^"]+)"'), re.compile(r'"reader_model": "([^"]*)"')
for src in ('catalog', 'rejected'):
    with open(ROOT / f'{src}.jsonl') as fh:
        for line in fh:
            m = rx_p.search(line)
            if not m or m.group(1) not in need_p:
                continue
            rid = rx_id.search(line).group(1)
            a = rx_a.search(line)
            mm = rx_m.search(line)
            model = (mm.group(1) if mm else '') or backfill.get(rid, '')
            if model and a:
                same[(m.group(1), a.group(1)[:16])][model] += 1


def model_of(rid):
    own = next((x['reader_model'] for x in rowinfo[rid] if x.get('reader_model')), '')
    if own:
        return own, 'stamped on the row'
    if backfill.get(rid):
        return backfill[rid], 'provenance backfill'
    c = same.get((rowinfo[rid][0]['pmid'], added_time(rid)))
    return (c.most_common(1)[0][0], 'same paper, same add') if c else ('', 'unknown')


def model_group(m):
    return {'claude-opus-5-5': 'Opus 5.5', 'claude-opus-5-5>claude-opus-5': 'Opus 5.5 then Opus 5',
            'claude-opus-5': 'Opus 5', 'claude-sonnet-5-5': 'Sonnet 5.5'}.get(m, m or 'unknown')


# the paper: its text route (papers.tsv) and the list that queued it (config.json order)
ptsv = {r['pmid']: r for r in csv.DictReader(open(ROOT / 'papers.tsv'), delimiter='\t')}
cfg = json.load(open(ROOT / 'config.json'))
src_list = {}
for p in cfg['sources']:
    fp = ROOT / p
    if fp.exists():
        for w in fp.read_text().split():
            src_list.setdefault(w, Path(p).stem)


def text_format(pmid):
    ts = ptsv.get(pmid, {}).get('text_source', '')
    return 'xml' if ts.endswith('.xml') or ts.split(':')[0] in ('europepmc', 'pmc_cloud') else (
        'pdf' if ts.endswith('.pdf') else 'other')


def source_group(pmid):
    return 'found by search' if src_list.get(pmid, '').startswith('discovered_') else 'cited or in the library'


# ---------------------------------------------------------------------------------------------------------------
# 4. rules (taxonomy) and instruction versions (git), as times and as papers read
FIRST = git('rev-list', '--max-parents=0', 'HEAD').split()[0]
tax = list(csv.DictReader(open(ROOT / 'paper/figures/method_overview/v5/taxonomy.tsv'), delimiter='\t'))
assert len(tax) == 85
rules = []
for r in tax:
    c = r['rule_commit']
    t = commit_time(c) if c else None
    start = bool(c) and FIRST.startswith(c)   # the first commit holds the starting pipeline: in force from the start
    versions = []
    for part in [p.strip() for p in r['rule_dates'].split(';') if p.strip()]:
        h = part.split()[-1]
        versions.append((h, commit_time(h), FIRST.startswith(h)))
    rules.append({**r, 'time': t, 'start': start, 'versions': versions,
                  'pos': (0, 0, 0) if start else (state_at_time(t) if t else (None, None, None))})
RULES = [r for r in rules if r['status'] == 'rule']
FA_RULES = [r for r in RULES if r['kind'] == 'FA']


def in_force(rs, t):
    return sum(1 for r in rs if r['start'] or (r['time'] and t and r['time'] <= t))


def versions_in_force(t):
    return sum(1 for r in RULES for h, ht, s in r['versions'] if s or (ht and t and ht <= t))


def commits_of(path):
    out = []
    for l in git('log', '--format=%h %ci', '--', path).splitlines():
        h, d, tm, _ = l.split()
        out.append((h, f'{d} {tm[:5]}', FIRST.startswith(h)))
    return out


GIT = {p: commits_of(p) for p in ('prompts/read.md', 'prompts/verify.md', 'catlog.py')}


def commits_so_far(path, t):
    return sum(1 for h, ht, s in GIT[path] if s or ht <= t)


# ---------------------------------------------------------------------------------------------------------------
# 5. one record per randomly audited value
V = []
pmid_index = {}
for rd in rounds:
    prev = rounds[rd['n'] - 2]['anchor_time'] if rd['n'] > 1 else ''
    for i, f, rid in rd['rows']:
        ls = by_row[rid]
        out = outcome(ls)
        t_add = added_time(rid)              # when the row entered the catalogue (a value brought back later: then)
        al = add_line_for(f[1], t_add) if t_add else None
        st_add = state[al] if al else state_at_time(t_add)
        t_read = LINE_TIME[al] if al else t_add   # the add line of the read that produced it
        model, model_how = model_of(rid)
        first_why = ' '.join(f[4:])
        V.append({
            'row_id': rid, 'pmid': f[1], 'round': rd['n'], 'metric': rowinfo[rid][0].get('metric'),
            'outcome': out, 'wrong': out in ('dropped', 'unit corrected'), 'dropped': out == 'dropped',
            'label_corrected': out == 'label corrected',
            # the round's own auditor found the value wrong (a drop for the organism label alone, the value then back
            # under the corrected label, is not: those auditors wrote that the value is right)
            'by_round_auditor': (f[2] == 'audit_drop' and rid not in LABELS) or first_why.startswith('unit corrected'),
            'unverified': f[2] == 'audit_keep' and first_why.lower().startswith('unverified'),
            'reason': ' '.join(ls[-1][1][4:]),
            'papers_at_audit': rd['papers_read'], 'papers_at_read': st_add[0], 'values_at_read': st_add[2],
            'fresh': bool(t_add and prev and t_add >= prev),
            'rules_at_read': in_force(RULES, t_read), 'fa_rules_at_read': in_force(FA_RULES, t_read),
            'added_time': t_add, 'read_time': t_read, 'model': model, 'model_group': model_group(model), 'model_how': model_how,
            'opus5': 'opus-5' in model and model != 'claude-opus-5-5', 'source': src_list.get(f[1], 'not on a list'),
            'source_group': source_group(f[1]), 'format': text_format(f[1]), 'design': rd['design'],
        })
        pmid_index.setdefault(f[1], len(pmid_index))

def summary_on_snapshot(**kw):
    """catlog.audit_summary over the snapshot's lines (SNAP) instead of the whole log.tsv, which grows while other chats
    work: its own code, given the lines this build read (it reads only those and catalog.jsonl; nothing writes)."""
    whole = catlog.events
    catlog.events = lambda: SNAP
    try:
        return catlog.audit_summary(**kw)
    finally:
        catlog.events = whole


n_aud, n_drop, n_fix, n_lab = summary_on_snapshot(split=True)
mine = (len(V), sum(v['dropped'] for v in V), sum(v['outcome'] == 'unit corrected' for v in V),
        sum(v['label_corrected'] for v in V))
assert mine == (n_aud, n_drop, n_fix, n_lab), \
    f'random audit counts differ from catlog.audit_summary: {mine} vs {(n_aud, n_drop, n_fix, n_lab)}'

# ---------------------------------------------------------------------------------------------------------------
# 6. tests
TESTS = {'snapshot': {'log_lines': LOG_LINES, 'rounds': len(rounds), 'values_audited': mine[0], 'dropped': mine[1],
                      'unit_corrected': mine[2], 'wrong': mine[1] + mine[2], 'label_corrected': mine[3],
                      'label_corrected_rows': {v['row_id']: v['pmid'] for v in V if v['label_corrected']},
                      'papers_read_at_end': state[LINES[-1]][0], 'values_in_catalogue_at_end': state[LINES[-1]][2],
                      'audit_summary_catlog_py': [n_aud, n_drop, n_fix, n_lab]}}


def logit(x, y='wrong', sub=None, extra=(), scale=1000.0, label=''):
    D = [v for v in V if (sub is None or sub(v))]
    cols, names = [np.array([v[x] for v in D], float) / scale], [x]
    for e in extra:
        cats = sorted({v[e] for v in D})
        for c in cats[1:]:
            cols.append(np.array([1.0 if v[e] == c else 0.0 for v in D]))
            names.append(f'{e}={c}')
    A = sm.add_constant(np.column_stack(cols))
    yv = np.array([1.0 if v[y] else 0.0 for v in D])
    g = np.array([pmid_index[v['pmid']] for v in D])
    m = sm.GLM(yv, A, family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': g})
    b, se = float(m.params[1]), float(m.bse[1])
    return {'label': label, 'x': x, 'per': scale, 'y': y, 'n': len(D), 'events': int(yv.sum()),
            'odds_ratio': round(math.exp(b), 4), 'ci95': [round(math.exp(b - 1.96 * se), 4), round(math.exp(b + 1.96 * se), 4)],
            'p': round(float(m.pvalues[1]), 4), 'covariates': names[1:],
            'se': 'cluster-robust by paper'}


T = TESTS['logistic'] = []
T.append(logit('papers_at_audit', 'wrong', label='wrong (dropped or unit corrected) ~ papers read when audited'))
T.append(logit('papers_at_audit', 'dropped', label='dropped ~ papers read when audited (the rate status reports)'))
T.append(logit('papers_at_read', 'wrong', label='wrong ~ papers read when the value was read'))
T.append(logit('rules_at_read', 'wrong', scale=10.0, label='wrong ~ rules in force when the value was read (per 10 rules)'))
T.append(logit('fa_rules_at_read', 'wrong', scale=10.0,
               label='wrong ~ rules against wrong values in force when read (per 10 rules)'))
T.append(logit('papers_at_read', 'wrong', sub=lambda v: v['fresh'],
               label='wrong ~ papers read when read; values audited in the first round after they were added'))
T.append(logit('papers_at_audit', 'by_round_auditor', label="the round's own auditor found it wrong ~ papers read when audited"))
T.append(logit('papers_at_audit', 'wrong', sub=lambda v: v['design'] in ('C', 'D'),
               label='wrong ~ papers read when audited; only rounds of the one audit design C/D'))
T.append(logit('papers_at_read', 'wrong', sub=lambda v: v['model_group'] != 'unknown',
               extra=('model_group', 'source_group'), label='wrong ~ papers read when read, adjusted for reader model and paper source'))
T.append(logit('papers_at_read', 'wrong', sub=lambda v: v['model_group'] == 'Opus 5.5',
               label='wrong ~ papers read when read; values read by Opus 5.5 alone'))
T.append(logit('papers_at_read', 'wrong', sub=lambda v: v['source_group'] == 'cited or in the library',
               label='wrong ~ papers read when read; papers cited by a database or in the library (chosen after seeing the data)'))


def halves(key, y='wrong'):
    Vs = sorted(V, key=lambda v: (v[key], v['round']))
    h = len(Vs) // 2
    a, b = Vs[:h], Vs[h:]
    ka, kb = sum(v[y] for v in a), sum(v[y] for v in b)
    _, p = st.fisher_exact([[ka, len(a) - ka], [kb, len(b) - kb]])
    # rate ratio late/early, 95% interval by resampling papers within each half (2,000 draws, seed 1)
    rng = random.Random(1)
    def by_paper(part):
        d = defaultdict(lambda: [0, 0])
        for v in part:
            d[v['pmid']][0] += v[y]
            d[v['pmid']][1] += 1
        return list(d.values())
    pa, pb = by_paper(a), by_paper(b)
    rr = []
    for _ in range(2000):
        sa = [pa[rng.randrange(len(pa))] for _ in pa]
        sb = [pb[rng.randrange(len(pb))] for _ in pb]
        ra = sum(x[0] for x in sa) / sum(x[1] for x in sa)
        rb = sum(x[0] for x in sb) / sum(x[1] for x in sb)
        if ra > 0:
            rr.append(rb / ra)
    rr.sort()
    return {'axis': key, 'y': y, 'split_at_papers_read': b[0][key],
            'early': {'n': len(a), 'k': ka, 'rate': round(ka / len(a), 5), 'wilson95': [round(x, 5) for x in wilson(ka, len(a))]},
            'late': {'n': len(b), 'k': kb, 'rate': round(kb / len(b), 5), 'wilson95': [round(x, 5) for x in wilson(kb, len(b))]},
            'fisher_p': round(float(p), 4), 'rate_ratio_late_over_early': round((kb / len(b)) / (ka / len(a)), 3),
            'rate_ratio_ci95_resampling_papers': [round(rr[int(0.025 * len(rr))], 3), round(rr[int(0.975 * len(rr)) - 1], 3)]}


TESTS['halves'] = [halves('papers_at_audit'), halves('papers_at_audit', 'dropped'), halves('papers_at_read')]


def min_detectable(n, p1, alpha=0.05, power=0.8):
    """Smallest fall from p1 a two-sided test of two equal halves of n values detects with this power (no clustering)."""
    za, zb = st.norm.ppf(1 - alpha / 2), st.norm.ppf(power)
    lo, hi = 0.0, p1
    for _ in range(60):
        p2 = (lo + hi) / 2
        pb = (p1 + p2) / 2
        need = za * math.sqrt(2 * pb * (1 - pb) / n) + zb * math.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / n)
        if p1 - p2 > need:
            lo = p2
        else:
            hi = p2
    return lo


e = TESTS['halves'][0]['early']
TESTS['power'] = {'early_half_rate': e['rate'], 'n_per_half': e['n'],
                  'late_rate_detectable_80pct_power': round(min_detectable(e['n'], e['rate']), 5),
                  'note': 'naive (values independent); clustering by paper makes the detectable fall larger'}


def compare(key, a_val, b_val, y='wrong', sub=None):
    D = [v for v in V if sub is None or sub(v)]
    out = {}
    for name, test in (('a', a_val), ('b', b_val)):
        part = [v for v in D if test(v[key])]
        k = sum(v[y] for v in part)
        pp = {v['pmid'] for v in part}
        pw = {v['pmid'] for v in part if v[y]}
        out[name] = {'values': len(part), 'wrong': k, 'rate': round(k / len(part), 5),
                     'wilson95': [round(x, 5) for x in wilson(k, len(part))], 'papers': len(pp), 'papers_with_wrong': len(pw)}
    pa, pb = out['a'], out['b']
    out['fisher_p_values'] = round(float(st.fisher_exact([[pa['wrong'], pa['values'] - pa['wrong']], [pb['wrong'], pb['values'] - pb['wrong']]])[1]), 4)
    out['fisher_p_papers'] = round(float(st.fisher_exact([[pa['papers_with_wrong'], pa['papers'] - pa['papers_with_wrong']],
                                                          [pb['papers_with_wrong'], pb['papers'] - pb['papers_with_wrong']]])[1]), 4)
    return out


TESTS['reader_model'] = {
    'a = Opus 5 in all or part of the read; b = Opus 5.5 alone': compare('model_group', lambda m: m in ('Opus 5', 'Opus 5.5 then Opus 5'), lambda m: m == 'Opus 5.5'),
    'same, papers found by search only': compare('model_group', lambda m: m in ('Opus 5', 'Opus 5.5 then Opus 5'), lambda m: m == 'Opus 5.5',
                                                 sub=lambda v: v['source_group'] == 'found by search'),
    'same, papers cited or in the library only': compare('model_group', lambda m: m in ('Opus 5', 'Opus 5.5 then Opus 5'), lambda m: m == 'Opus 5.5',
                                                         sub=lambda v: v['source_group'] == 'cited or in the library'),
    'by model': {g: {'values': sum(1 for v in V if v['model_group'] == g), 'wrong': sum(v['wrong'] for v in V if v['model_group'] == g)}
                 for g in ('Opus 5.5', 'Opus 5.5 then Opus 5', 'Opus 5', 'Sonnet 5.5', 'unknown')},
    'model found from': dict(Counter(v['model_how'] for v in V)),
}
TESTS['paper_source'] = {
    'a = found by search; b = cited or in the library': compare('source_group', lambda s: s == 'found by search', lambda s: s != 'found by search'),
    'by list': {s: {'values': sum(1 for v in V if v['source'] == s), 'wrong': sum(v['wrong'] for v in V if v['source'] == s)}
                for s in sorted({v['source'] for v in V})},
}
TESTS['text_format'] = {fm: {'values': sum(1 for v in V if v['format'] == fm), 'wrong': sum(v['wrong'] for v in V if v['format'] == fm)}
                        for fm in ('xml', 'pdf', 'other')}
TESTS['metric'] = {m: {'values': sum(1 for v in V if v['metric'] == m), 'wrong': sum(v['wrong'] for v in V if v['metric'] == m)}
                   for m in ('kcat', 'Km', 'kcat/Km')}

# kinds of the wrong values, and whether a rule for the kind was in force when the value was read
taxd = {r['id']: r for r in rules}
W = [v for v in V if v['wrong']]
assert {v['row_id'] for v in W} == set(KIND), 'every wrong value needs a kind in KIND'
for v in W:
    k = KIND[v['row_id']]
    r = taxd[k]
    v['kind'] = k
    if r['status'] != 'rule':
        v['rule_when_read'] = 'no rule for this kind'
    elif r['start'] or (r['time'] and r['time'] <= v['read_time']):
        v['rule_when_read'] = 'yes'
    else:
        v['rule_when_read'] = 'no, the rule came later'
    v['rule_when_audited'] = ('no rule for this kind' if r['status'] != 'rule' else
                              'yes' if r['start'] or r['time'] <= rounds[v['round'] - 1]['anchor_time'] else 'no')
hs = TESTS['halves'][0]['split_at_papers_read']
TESTS['kinds'] = {
    'all': dict(Counter(v['rule_when_read'] for v in W)),
    'late half (audited at or after the split)': dict(Counter(v['rule_when_read'] for v in W if v['papers_at_audit'] >= hs)),
    'by kind, all': dict(Counter(f"{v['kind']} {GROUP[v['kind']]}" for v in W).most_common()),
    'by kind, late half': dict(Counter(f"{v['kind']} {GROUP[v['kind']]}" for v in W if v['papers_at_audit'] >= hs).most_common()),
    'by group, early half': dict(Counter(GROUP[v['kind']] for v in W if v['papers_at_audit'] < hs).most_common()),
    'by group, late half': dict(Counter(GROUP[v['kind']] for v in W if v['papers_at_audit'] >= hs).most_common()),
}
for v in V:
    v['kind'] = v.get('kind', '')
last3 = [rd['n'] for rd in rounds[-3:]]
TESTS['last_three_rounds'] = {
    'rounds': last3, 'values': sum(1 for v in V if v['round'] in last3), 'wrong': sum(v['wrong'] for v in V if v['round'] in last3),
    'wrong_by_paper': dict(Counter(v['pmid'] for v in W if v['round'] in last3).most_common()),
    'wrong_read_with_opus5': sum(1 for v in W if v['round'] in last3 and v['opus5']),
    'wrong_from_search_papers': sum(1 for v in W if v['round'] in last3 and v['source_group'] == 'found by search'),
    'rule_when_read': dict(Counter(v['rule_when_read'] for v in W if v['round'] in last3)),
}
TESTS['found_later'] = {
    'wrong values the round auditor kept, found wrong by a later check of the same paper': sum(1 for v in W if not v['by_round_auditor']),
    'dropped by the round auditor, then restored after review (auditor wrong)': sum(1 for v in V if v['by_round_auditor'] and not v['wrong']),
    'unverified keeps (auditor could not check)': sum(v['unverified'] for v in V),
    'dropped by the round auditor for a wrong organism label, the value back under the corrected label (label '
    'corrections, not wrong)': sum(v['label_corrected'] for v in V),
}
t_aud, t_drop, t_fix, t_lab = summary_on_snapshot(targeted=True, split=True)
split = defaultdict(lambda: Counter())
for r, ls in by_row.items():
    if r in random_rows:
        continue
    f = ls[-1][1]
    tag = ('database check flagged it' if f[-1] == catlog.TARGETED else
           'whole-paper follow-up' if f[-1] == catlog.FOLLOWUP or catlog.audit_targeted(f) else 'other')
    split[tag]['values'] += 1
    split[tag][outcome(ls)] += 1
TESTS['outside_the_random_audit'] = {'values': t_aud, 'dropped': t_drop, 'unit_corrected': t_fix,
                                     'label_corrected': t_lab, 'by_why': {k: dict(v) for k, v in split.items()},
                                     'note': 'rows only targeted audits saw (catlog.audit_summary(targeted=True, '
                                             'split=True) on the snapshot\'s lines); never in the rate'}
TESTS['rules_in_force_at_papers_read'] = {
    str(P): sum(1 for r in RULES if r['pos'][0] is not None and r['pos'][0] <= P)
    for P in (0, 12, 100, 500, 1000, 2000, 3000, 5000, 7000, 8000, state[LINES[-1]][0])}
TESTS['audited_before'] = {str(P): sum(1 for v in V if v['papers_at_audit'] <= P) for P in (100, 500, 1000, 2000, 3000)}
TESTS['held_out_papers'] = {'values_audited_in_papers_now_held_out': sum(1 for v in V if v['pmid'] in catlog.locked()),
                            'wrong': sum(v['wrong'] for v in V if v['pmid'] in catlog.locked())}

# ---------------------------------------------------------------------------------------------------------------
# 7. files
def r5(x):
    return '' if x is None or (isinstance(x, float) and math.isnan(x)) else round(x, 5)


byr = defaultdict(list)
for v in V:
    byr[v['round']].append(v)
# 8 groups of whole rounds with about equal values audited
total = len(V)
cum, bin_of = 0, {}
for rd in rounds:
    bin_of[rd['n']] = min(8, int(cum / (total / 8)) + 1)
    cum += len(byr[rd['n']])
cols = ['round', 'log_line', 'grouped_by', 'audit_design', 'papers_read', 'values_in_catalogue', 'rules_in_force',
        'rules_against_wrong_values_in_force', 'rule_versions_in_force', 'reader_instruction_versions',
        'checker_instruction_versions', 'code_versions', 'values_audited', 'values_dropped', 'values_unit_corrected',
        'values_wrong', 'values_label_corrected', 'wrong_found_by_this_round', 'drop_rate', 'drop_low95', 'drop_high95',
        'wrong_rate', 'wrong_low95', 'wrong_high95', 'papers_audited', 'papers_with_wrong',
        'values_new_since_last_round', 'wrong_among_new', 'median_papers_read_when_values_were_read',
        'share_from_search_papers', 'share_read_with_opus5', 'kept_unverified', 'sample_size_logged',
        'outside_random_audit_lines', 'outside_random_audit_drops', 'group_of_rounds']
with open(HERE / 'learning.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(cols)
    for rd in rounds:
        vs = byr[rd['n']]
        k_d = sum(v['dropped'] for v in vs)
        k_u = sum(v['outcome'] == 'unit corrected' for v in vs)
        k_w = k_d + k_u
        k_l = sum(v['label_corrected'] for v in vs)
        n = len(vs)
        t = rd['anchor_time']
        pr = sorted(v['papers_at_read'] for v in vs)
        new = [v for v in vs if v['fresh']]
        w.writerow([rd['n'], rd['anchor_line'], rd['how'], rd['design'], rd['papers_read'], rd['values_in_catalogue'],
                    in_force(RULES, t), in_force(FA_RULES, t), versions_in_force(t), commits_so_far('prompts/read.md', t),
                    commits_so_far('prompts/verify.md', t), commits_so_far('catlog.py', t), n, k_d, k_u, k_w, k_l,
                    sum(v['wrong'] and v['by_round_auditor'] for v in vs),
                    r5(k_d / n), r5(wilson(k_d, n)[0]), r5(wilson(k_d, n)[1]),
                    r5(k_w / n), r5(wilson(k_w, n)[0]), r5(wilson(k_w, n)[1]),
                    len({v['pmid'] for v in vs}), len({v['pmid'] for v in vs if v['wrong']}),
                    len(new), sum(v['wrong'] for v in new), pr[len(pr) // 2],
                    r5(sum(v['source_group'] == 'found by search' for v in vs) / n), r5(sum(v['opus5'] for v in vs) / n),
                    sum(v['unverified'] for v in vs), rd['sample_rows'], rd['targeted_lines'], rd['targeted_drops'],
                    bin_of[rd['n']]])

bcols = ['axis', 'group', 'rounds', 'papers_read_from', 'papers_read_to', 'rules_in_force_at_end', 'values_audited',
         'values_dropped', 'values_unit_corrected', 'values_wrong', 'values_label_corrected', 'wrong_rate',
         'wrong_low95', 'wrong_high95', 'papers_audited', 'papers_with_wrong', 'share_from_search_papers',
         'share_read_with_opus5',
         'opus55_alone_values', 'opus55_alone_wrong', 'opus55_alone_rate', 'opus55_alone_low95', 'opus55_alone_high95']
with open(HERE / 'learning_bins.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(bcols)
    parts = []
    for b in range(1, 9):  # by when audited: whole rounds
        rs = [rd for rd in rounds if bin_of[rd['n']] == b]
        vs = [v for rd in rs for v in byr[rd['n']]]
        parts.append(('when audited', b, f"{rs[0]['n']}-{rs[-1]['n']}", rs[0]['papers_read'], rs[-1]['papers_read'],
                      in_force(RULES, rs[-1]['anchor_time']), vs))
    Vr = sorted(V, key=lambda v: (v['papers_at_read'], v['round']))
    q = len(Vr) / 8
    for b in range(8):  # by when read: values in eighths
        vs = Vr[int(b * q):int((b + 1) * q)]
        last_t = max(v['read_time'] for v in vs)
        parts.append(('when read', b + 1, '', vs[0]['papers_at_read'], vs[-1]['papers_at_read'], in_force(RULES, last_t), vs))
    for axis, b, rr, p0, p1, rif, vs in parts:
        n = len(vs)
        kd = sum(v['dropped'] for v in vs)
        ku = sum(v['outcome'] == 'unit corrected' for v in vs)
        kw = kd + ku
        kl = sum(v['label_corrected'] for v in vs)
        o = [v for v in vs if v['model_group'] == 'Opus 5.5']
        ko = sum(v['wrong'] for v in o)
        w.writerow([axis, b, rr, p0, p1, rif, n, kd, ku, kw, kl, r5(kw / n), r5(wilson(kw, n)[0]), r5(wilson(kw, n)[1]),
                    len({v['pmid'] for v in vs}), len({v['pmid'] for v in vs if v['wrong']}),
                    r5(sum(v['source_group'] == 'found by search' for v in vs) / n), r5(sum(v['opus5'] for v in vs) / n),
                    len(o), ko, r5(ko / len(o) if o else None), r5(wilson(ko, len(o))[0]), r5(wilson(ko, len(o))[1])])

kcount = Counter(v['kind'] for v in W)
rcols = ['id', 'kind_of_error', 'status', 'error_type', 'where_it_arises', 'first_found_by', 'rule_lives_in',
         'rule_commit', 'papers_read_at_rule', 'values_in_catalogue_at_rule', 'rules_in_force_after',
         'rule_versions', 'papers_read_at_versions', 'random_audit_wrong_values', 'audited_values_read_before_rule',
         'wrong_values_read_before_rule', 'audited_values_read_after_rule', 'wrong_values_read_after_rule']
order = sorted(rules, key=lambda r: (r['pos'][0] is None, r['pos'][0] if r['pos'][0] is not None else 0, r['time'] or '', r['id']))
with open(HERE / 'rules_by_papers.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(rcols)
    count = 0
    for r in order:
        if r['status'] == 'rule':
            count += 1
        is_rule = r['status'] == 'rule' and (r['start'] or r['time'])
        before = [v for v in V if is_rule and not r['start'] and v['read_time'] < r['time']]
        after = [v for v in V if is_rule and (r['start'] or v['read_time'] >= r['time'])]
        w.writerow([r['id'], r['class'], r['status'], ERROR_TYPE.get(r['kind'], r['kind']), r['origin'], r['found_route'],
                    r['guard_layer'], r['rule_commit'], '' if r['pos'][0] is None else r['pos'][0],
                    '' if r['pos'][2] is None else r['pos'][2], count if r['status'] == 'rule' else '',
                    len(r['versions']),
                    '; '.join(str(0 if s else state_at_time(ht)[0]) for h, ht, s in r['versions'] if s or ht),
                    kcount.get(r['id'], 0),
                    len(before) if is_rule else '', sum(1 for v in before if v['kind'] == r['id']) if is_rule else '',
                    len(after) if is_rule else '', sum(1 for v in after if v['kind'] == r['id']) if is_rule else ''])

dcols = ['round', 'papers_read_when_audited', 'papers_read_when_read', 'row_id', 'pmid', 'metric', 'outcome',
         'found_by', 'kind_id', 'kind_of_error', 'plain_group', 'rule_in_force_when_read', 'reader_model',
         'paper_source', 'text_format', 'auditor_reason']
with open(HERE / 'drops.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(dcols)
    for v in sorted(W, key=lambda v: (v['round'], v['pmid'], v['row_id'])):
        w.writerow([v['round'], v['papers_at_audit'], v['papers_at_read'], v['row_id'], v['pmid'], v['metric'],
                    v['outcome'], 'this round\'s auditor' if v['by_round_auditor'] else 'a later check of the same paper',
                    v['kind'], taxd[v['kind']]['class'], GROUP[v['kind']], v['rule_when_read'], v['model_group'],
                    v['source'], v['format'], v['reason'][:400]])

nb = {}
for b in range(1, 9):
    vs = [v for v in V if bin_of[v['round']] == b]
    for part, sel in (('new', lambda v: v['fresh']), ('older', lambda v: not v['fresh'])):
        p = [v for v in vs if sel(v)]
        k = sum(v['wrong'] for v in p)
        nb[f'{b} {part}'] = {'values': len(p), 'wrong': k, 'papers_with_wrong': len({v['pmid'] for v in p if v['wrong']}),
                             'rate': round(k / len(p), 5) if p else None}
depth = {}  # how much each round's auditors wrote and how often they looked at a page image (crude depth signs)
img = re.compile(r'page image|page-image|rendered|pdftoppm|\bimage\b', re.I)
earlier = re.compile(r'earlier paper|\bref(?:erence)?\.? ?\[?\d|reprint', re.I)
for b in range(1, 9):
    vs = [v for v in V if bin_of[v['round']] == b]
    first = [' '.join(first_rand[v['row_id']][1][4:]) for v in vs]
    ln = sorted(len(x) for x in first)
    depth[str(b)] = {'values': len(vs), 'median_reason_characters': ln[len(ln) // 2],
                     'share_naming_a_page_image': round(sum(bool(img.search(x)) for x in first) / len(vs), 4),
                     'share_naming_an_earlier_paper': round(sum(bool(earlier.search(x)) for x in first) / len(vs), 4)}
TESTS['auditor_reasons_by_group'] = depth

g1 = nb['1 new']
mid = {'values': sum(nb[f'{b} new']['values'] for b in range(2, 8)), 'wrong': sum(nb[f'{b} new']['wrong'] for b in range(2, 8))}
nb['post hoc: group 1 new vs groups 2-7 new, Fisher p'] = round(float(st.fisher_exact(
    [[g1['wrong'], g1['values'] - g1['wrong']], [mid['wrong'], mid['values'] - mid['wrong']]])[1]), 4)
nb['groups 2-7 new'] = mid
TESTS['new_and_older_values_by_group'] = nb

json.dump(TESTS, open(HERE / 'tests.json', 'w'), indent=1)
print(json.dumps(TESTS['snapshot']))
print('catlog.audit_summary(split=True) on the whole log.tsv now:', catlog.audit_summary(split=True))
for t in TESTS['logistic']:
    print(f"{t['label']}: OR {t['odds_ratio']} {t['ci95']} p={t['p']} (n={t['n']}, events={t['events']})")
for h in TESTS['halves']:
    print(h)
