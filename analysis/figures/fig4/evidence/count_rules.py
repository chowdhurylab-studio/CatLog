#!/usr/bin/env python3
"""Fig. 4 v2 evidence (co-learning that works): for each kind of error on CatLog's list, who first found it, how many
papers CatLog had read when its rule entered, the step that holds the rule, and what the rule has caught, fixed or kept
out since, counted from CatLog's own files.

Read-only. Run from anywhere:  python3 -I -B count_rules.py
Reads   (catlog-v2) paper/figures/method_overview/v5/taxonomy.tsv and error_ledger_v5.tsv; log.tsv; rejected.jsonl;
        catalog.jsonl; bounds.jsonl; catlog_wide.csv; sources/holdout_locked.txt, implausible_as_printed.tsv and
        natural_forms.tsv; work/*.missed.read.json and work/old/*.missed.read.*.json (never one of a test-set paper);
        work/record_merge_20261111/merged_sets_v2.json and merged_sets_v5_new.json; tools/units.py (imported for its
        unit arithmetic only); `git show -s` for the time of each rule's commit.
Writes  rules.csv and catches_by_paper.csv beside this script, nothing else.
Never opens texts/ or papers/. Papers of the method paper's test set (sources/holdout_locked.txt) are left out of every
catch count; their work files are never opened.
"""
import bisect
import collections
import csv
import glob
import importlib.util
import json
import math
import os
import re
import subprocess

ROOT = '<the CatLog folder>'
HERE = os.path.dirname(os.path.abspath(__file__))
TAX = 'paper/figures/method_overview/v5/taxonomy.tsv'
LEDGER = 'paper/figures/method_overview/v5/error_ledger_v5.tsv'
P = lambda *a: os.path.join(ROOT, *a)
csv.field_size_limit(10 ** 9)
I = re.I
R = lambda s: re.compile(s, I)

# ======================================================================================================================
# the list of kinds (taxonomy.tsv, 85 lines, built 2 November 2026) and the kinds found after it (EXTRA)
KINDS = list(csv.DictReader(open(P(TAX), newline='', encoding='utf-8'), delimiter='\t'))
assert len(KINDS) == 85, len(KINDS)
LED = {r['line']: r for r in csv.DictReader(open(P(LEDGER), newline='', encoding='utf-8'), delimiter='\t')}

# Two kinds found after the list was built, each with a rule commit and a log trail (CLAUDE.md, "Open items", the
# JATS paragraph). Same fields as taxonomy.tsv; their facts are asserted against log.tsv and git below.
EXTRA = [
    dict(id='X1', **{'class': 'Figure captions outside the article body left out of the text'},
         origin='the PDF text layer or OCR', kind='FR', novelty='new', first_found='2026-11-06', found_route='code check',
         found='2026-11-06 code check (28362483: 6 values of its Figure 3 legend refused quote_not_in_paper)',
         found_again='', guard_layer='code conversion', layers='code conversion', rule_commit='ae075aa',
         rule_date='2026-11-09', rule_dates='2026-11-09 ae075aa', status='rule', ledger_lines='', first_papers='28362483',
         found_time='2026-11-06 10:44'),          # log.tsv: the add line of 28362483 that refused the 6 values
    dict(id='X2', **{'class': 'A table cell holding only a drawn structure rendered empty'},
         origin='the PDF text layer or OCR', kind='FR', novelty='new', first_found='2026-11-12', found_route='operator',
         found='2026-11-12 operator (34680172: reader and verifier stored no value; its 20 amines are named only by drawn '
               'structures)', found_again='', guard_layer='code conversion', layers='code conversion',
         rule_commit='16b11e1', rule_date='2026-11-12', rule_dates='2026-11-12 16b11e1', status='rule', ledger_lines='',
         first_papers='34680172', found_time='2026-11-12 22:49'),   # log.tsv: the add line of 34680172 with no value
]

FINDER = {'reviewer': 'people', 'owner': 'people', 'operator': 'agents', 'outside review': 'agents', 'audit': 'agents',
          'verifier': 'agents', 'database check': 'agents', 'reader': 'agents', 'code check': 'code', 'sweep': 'code',
          'old system': 'known at the start'}            # as writing/figures/fig4/fig4_data.py _FINDER (Fig. 4 v1)
STEP = {'reader prompt': 'Read', 'code conversion': 'Convert', 'verifier prompt': 'Verify', 'code check': 'Check',
        'database check': 'Database check', "sweep from the paper's own numbers": 'Sweep', 'audit': 'Audit',
        'people': 'People'}
EFFECT = {'FA': 'wrong value or label let in', 'FR': 'right value refused or lost', 'PROC': 'process failure'}
PMID_RX = re.compile(r'(?<![\d-])(\d{5,9}|NP[0-9A-F]{8})(?![\d-])')


def first_papers(k):
    """Papers named in the kind's first finding: the first segment of `found` and the ledger lines of that date."""
    if 'first_papers' in k:
        return set(k['first_papers'].split())
    ids = set(PMID_RX.findall(k['found'].split('; found again')[0]))
    for line in [x.strip() for x in k['ledger_lines'].split(',') if x.strip()]:
        L = LED[line]
        if k['first_found'] and L['date'] == k['first_found']:
            ids |= set(PMID_RX.findall(' '.join((L['failure'], L['rows'], L['found_by']))))
    return ids


# ======================================================================================================================
# time. A rule enters at its commit (git, local wall time, the clock log.tsv writes). Papers read so far = distinct
# papers at their first `add` line in log.tsv (taxonomy.tsv's discovery curve and Fig. 1 count papers the same way).
def git_time(h):
    out = subprocess.run(['git', '-C', ROOT, 'show', '-s', '--format=%ci', h], capture_output=True, text=True).stdout
    assert out.strip(), h
    return out.strip()[:16]


LOG = [ln.rstrip('\n').split('\t') for ln in open(P('log.tsv'), encoding='utf-8')]
FIRST_ADD = {}
for p in LOG:
    if len(p) > 2 and p[2] == 'add' and p[1] not in FIRST_ADD:
        FIRST_ADD[p[1]] = p[0]
ADD_TIMES = sorted(FIRST_ADD.values())
PAPERS_NOW = len(ADD_TIMES)
LAST_LOG = max(p[0] for p in LOG if p and p[0][:2] == '20')


def papers_read(t):
    """Papers read before time t ('YYYY-MM-DD HH:MM')."""
    return bisect.bisect_left(ADD_TIMES, t) if t else None


HOLD = {l.strip() for l in open(P('sources/holdout_locked.txt')) if l.strip() and not l.startswith('#')}
assert len(HOLD) == 369, len(HOLD)

ALLK = KINDS + EXTRA
RULES = {}                                               # id -> [(commit, time)], the first rule then later changes
for k in ALLK:
    hs = re.findall(r'\b[0-9a-f]{7}\b', k['rule_dates'])
    if k['rule_commit'] and k['rule_commit'] not in hs:
        hs.insert(0, k['rule_commit'])
    RULES[k['id']] = [(h, git_time(h)) for h in hs]
    if k['rule_commit']:
        assert RULES[k['id']][0][0] == k['rule_commit'], k['id']
        assert RULES[k['id']][0][1][:10] == k['rule_date'], (k['id'], RULES[k['id']][0], k['rule_date'])
assert sum(max(len(v) - 1, 0) for i, v in RULES.items() if not i.startswith('X')) == 65   # taxonomy.tsv: 65 later commits
# rule changes after the list: IP2's join rule followed a reviewer's finding (HUMAN_REVIEW.md; CLAUDE.md "Measurements")
POST_LIST = {'IP2': ['5c441ee', '1d2a10f']}
for i, hs in POST_LIST.items():
    RULES[i] += [(h, git_time(h)) for h in hs]

# ======================================================================================================================
# events: one per value (or record, paper, verdict, join), with its kind, the step that acted and what it did.
# by_code = the event exists only through the rule's own code (a recover, unitfix or fix line, a rebuilt text, a value
# stored in a unit code learned to convert, a field the export sets): it is the rule acting, whatever its time. Agent
# events (a verifier's rejection or fix, an audit's drop, a reader's page-image read) count as the rule's from the
# rule's commit on.
EV = []


def ev(kind, sub, source, step, action, pmid, key, t, n=1, unit='values', by_code=False, rid=None):
    if pmid in HOLD:
        return
    if rid is None and key and key[0] == 'row':
        rid = key[1]
    EV.append(dict(kind=kind, sub=sub, source=source, step=step, action=action, pmid=pmid, key=key, t=(t or '')[:16],
                   n=n, unit=unit, by_code=by_code, rid=rid))


# ---- 1. rejected.jsonl: every refusal (code checks at add, verifiers' rejections) and every drop (audits, sweeps,
# whole-paper follow-ups, re-read copies). The reason is free text; a regular expression assigns the kind, first match
# wins. The six validated classes keep paper/figures/supp_agent_flow/flow_counts.py's patterns and order (a blind
# agent agreed for 87 of 100 sampled refusals: reprinted 20/20, retracted 3/3, not a kcat or Km 9/10, printed twice
# 18/20, partial constant 17/19, misprint 11/13; work/agent_highlights_20261028/round2/reason_sample_*). The rest were
# written for this file from the reasons themselves (README, "How the refusals were sorted").
AGENT_RULES = [
    ('IP3', 're-read copy dropped', R(r're-read copy|re-read duplicat|reworded|duplicate of accepted|'
                                      r'cop(?:y|ies) of (?:an )?accepted|already accepted')),
    ('IP4', 'audit drop stays dropped', R(r'audit dropped this (?:measurement|censored value) before')),
    ('PR16', 'recovered without its unit fix', R(r'recovered without its column')),
    ('PP7', 'retracted or corrected by the authors', R(r'retract|corrigend|erratum|withdrawn')),
    ('RA11', 'not detected stored for a constant not determined', R(
        r'not detected was stored for a constant|could not (?:be )?determine|marker covers both|enzyme was active|'
        r'not determined[^.;]{0,80}(?:active|activity)|though the enzyme|the variant was active|was active (?:in|on|with)|'
        r'not attainable|not calculated|precluded our determination|could not be fitted|not-determined marker|'
        r'not determined due to')),
    ('IP3', 'printed twice in the paper', R(r'duplicate|printed again|restates|same measurement as row|copy of row')),
    ('PP2', 'reprinted from earlier work', R(
        r'reprint|carried over|not measured (?:here|in this)|previously reported|identical to (?:ref|PMID|the same lab|'
        r'the authors)|not prepared in this|credit(?:s|ed)? (?:\S+ )?(?:to )?(?:ref|data)|literature values|'
        r'have been reported|unpublished data|not (?:this|a) paper\'s measurement|not a measurement shown in this paper|'
        r'from ref\.? ?\[?\d|PMID \d+\)? Table')),
    ('RA3', 'partial constant', R(r'partial|per-product|per[- ]site|branched reaction|two bonds|cleavage|beta-kcat|'
                                  r'cin-kcat|one product|per-metabolite|βkcat')),
    ('UNITNONE', 'no unit printed anywhere', R(r'no unit (?:is )?printed|prints no unit|no unit for k|'
                                               r'unit is printed nowhere|no unit .{0,40}anywhere|with no unit')),
    ('RA4', 'reader read a header multiplier the wrong way', R(r"read as ×|read as x10|applied as ×")),
    ('RA9', 'implausible scale rejected', R(r'cannot mean what it prints')),
    ('PP3', 'a row printed again under another label', R(
        r'cell-for-cell copy|wrong table row|carries (?:peptide|the) \S+ cells|identical to the \S+ row|repeats the \S+ row')),
    ('PP1', 'misprinted unit header', R(r'header[^.;]{0,60}misprint|misprint[^.;]{0,40}header|units are contradicted|'
                                        r'pkat')),
    ('PP4', 'cell slip or kcat/Km off kcat ÷ Km', R(
        r'slip|typo|quotient|10x|1000x|100x|inconsisten|\d(?:\.\d)?x (?:below|above|away|from|off|the|kcat)|\d+-fold|'
        r'>=\s?5x|≥\s?5x|non-closure|does not close|impossible beside|disagree|contradict|misprint')),
    ('PP1', 'misprinted unit header', R(r'header')),
    ('PP5', 'beyond the diffusion limit', R(r'diffusion')),
    ('RA1', 'not a kcat or Km', R(
        r'\bHill\b|K0\.5|S0\.5|\bK_?i\b|\bK_?d\b|inhibition constant|dissociation constant|specific activity|\bVmax\b|'
        r'molecular activity|rate constant|single[- ]turnover|pseudo-first|initial rate|binding constant|not a kcat|'
        r'not a Km|not a turnover|fold ratio|not converted|not consumed|activator|cofactor|not a measured|'
        r'not a Michaelis|velocity rather|a rate at one|one (?:fixed )?(?:substrate )?concentration|half-reaction|'
        r'intercept|simulated|V_?max/K_?m')),
    ('IP11', 'variant recorded wrongly', R(r'wrong variant|incomplete variant|variant (?:cannot|mismatch)|not a mutant|'
                                           r'never prints the residue|names no substitution|residue that replaced')),
    ('IP12', 'wrong substrate label', R(r'wrong substrate|substrate label')),
    ('RA10', 'censored row the paper does not support', R(
        r'undefined|never defines|defines (?:the|this) marker nowhere|not a (?:not-detected|censored)|bound is not on|'
        r'not-detected finding|virtually no|no (?:measurable|detectable)|unable to|data not shown|\bND\b|n\.d\.|inactive')),
    ('CU2', 'a ± the cell does not print', R(r'± the cell does not print|borrows that neighbouring')),
    ('TL2', 'two decimal points', R(r'two decimal points')),
    ('TL7', 'OCR text only', R(r'no page image or PDF|text is Elsevier OCR only|OCR \(no page image')),
    ('TL5', 'exponent missing', R(r'with no exponent')),
]
CODE_RULES = [                                           # code checks at add: the reason's own key
    ('CU5', 'a detail the paper does not print was required', R(r'^missing:(?:raw_unit|organism|pH|temperature)')),
    ('RA7', 'a required field left empty', R(r'^missing:')),
    ('RA12', 'M^-2 kcat/Km refused', R(r'^not_kcat_over_km_unit')),
    ('CU1', 'a unit code does not convert, refused', R(r'^unknown_(?:kcat|km|kcatkm)_unit')),
    ('IP4', 'conflict with an accepted value kept apart', R(r'^conflicts with accepted|^same printed cell as accepted|'
                                                            r'^verifier_stale')),
    ('PP6', 'kcat/Km off kcat ÷ Km refused', R(r'^ratio_non_closure')),
    ('CU6', 'above the physical limit refused', R(r'^beyond_physical_limit')),
    ('QUOTE', 'value or quote not in the text', R(r'^value_not_in_quote|^quote_not_in_paper|^marker_not_in_quote')),
    ('CU4', 'printed form refused', R(r'^bound_or_range|^range_not_a_bound|^censored_sign_mismatch|^non_positive_value')),
]


def classify(why):
    rules = AGENT_RULES if (why.startswith('verifier_reject') or why.startswith('audit')) else CODE_RULES
    for kind, sub, rx in rules:
        if rx.search(why):
            return kind, sub
    return ('OTHER', 'other reason') if rules is AGENT_RULES else ('OTHERCODE', why.split(':')[0][:40])


def slot(r):
    return (str(r.get('pmid')), r.get('metric'), str(r.get('raw_value')).strip(), str(r.get('location')).strip(),
            str(r.get('variant')).strip(), str(r.get('substrate')).strip(), str(r.get('censored') or ''))


def jsonl(path):
    for ln in open(P(path), encoding='utf-8'):
        try:
            yield json.loads(ln)
        except ValueError:                               # a cut-off last line
            continue


CAT = list(jsonl('catalog.jsonl'))
BOUND = list(jsonl('bounds.jsonl'))
REJ = list(jsonl('rejected.jsonl'))
STORED_IDS = {r['row_id'] for r in CAT} | {r['row_id'] for r in BOUND}
STORED_SLOTS = {slot(r) for r in CAT} | {slot(r) for r in BOUND}

for r in REJ:
    why = ' | '.join(r.get('why') or [])
    kind, sub = classify(why)
    step = 'Verify' if why.startswith('verifier_reject') else ('After reading' if why.startswith('audit') else 'Check')
    if kind == 'IP4' and why.startswith('audit dropped'):
        step = 'Check'                                   # add refuses a slot an audit dropped
    back = r['row_id'] in STORED_IDS or slot(r) in STORED_SLOTS     # stored again since (recovered or read again)
    ev(kind, sub, 'rejected.jsonl', step, 'refused, now stored' if back else 'kept out', str(r['pmid']),
       ('slot',) + slot(r), (r.get('dropped') or r.get('checked') or ''), rid=r['row_id'])


# ---- 2. log.tsv lines
def recover_kind(pmid, t, why):
    if why == 'ratio_non_closure' or (why == 'verifier_reject' and t[:10] == '2026-10-10'):
        return 'PP6'                                     # 10 Oct: recover ratio_non_closure (12770bd, the owner's rule)
    if why.startswith('verifier_reject') and pmid == '36756200':
        return 'RA9'
    if why in ('unknown_km_unit', 'unknown_kcatkm_unit', 'unknown_kcat_unit'):
        return 'CU8' if t[:10] == '2026-10-12' else 'CU4'   # 12 Oct: Km over mass concentration (66d9143)
    if why == 'value_not_in_quote':
        return 'TL6' if t[:10] == '2026-10-14' else 'QUOTE'  # 14 Oct: OCR hyphens read as decimal points (7d212bd)
    if why == 'quote_not_in_paper':
        return 'X1' if pmid == '28362483' else 'QUOTE'
    if why == 'conflicts with accepted row':
        return 'CU4' if pmid == '7470464' else 'IP5'         # 7470464: 322c01c; 18783250: a blanked pH (27ad550)
    if why == 'unitfix':
        return 'RA8' if pmid == '19001118' else 'PP1'        # 19001118: an audit's drop restored
    return {'beyond_physical_limit': 'CU6', 'missing:raw_unit': 'CU5', 'missing:organism': 'CU5', 'restore': 'RA8',
            'range_not_a_bound': 'CU4', 'bound_or_range': 'CU4', 'censored_sign_mismatch': 'CU4',
            'marker_not_in_quote': 'CU4'}.get(why, 'RECOVER?')


UNITFIX_AT = {(p[0], p[1]) for p in LOG if len(p) > 2 and p[2] == 'unitfix'}
for p in LOG:
    if len(p) < 4:
        continue
    t, pmid, typ, rest = p[0], p[1], p[2], p[3:]
    if typ == 'unitfix':
        why = rest[2] if len(rest) > 2 else ''
        kind = 'CU3' if 'spaced exponent' in why else ('RA8' if pmid == '40723313' else 'PP1')
        ev(kind, 'unit corrected after reading', 'log.tsv unitfix', 'After reading', 'fixed', pmid, ('row', rest[0]), t,
           by_code=True)
    elif typ == 'pmfix':
        ev('CU2', 'a borrowed ± taken off', 'log.tsv pmfix', 'After reading', 'fixed', pmid, ('row', rest[0]), t,
           by_code=True)
    elif typ == 'cellfix':
        ev('CELL', 'a misread cell replaced', 'log.tsv cellfix', 'After reading', 'fixed', pmid, ('row', rest[0]), t,
           by_code=True)
    elif typ == 'limitfix':
        ev('RA11', 'a limit of another quantity cleared', 'log.tsv limitfix', 'After reading', 'fixed', pmid,
           ('row', rest[0]), t)                          # decided by two paper checks: timed like an agent's verdict
    elif typ == 'reworded_duplicate':
        ev('IP3', 're-read copy refused at add', 'log.tsv reworded_duplicate', 'Check', 'kept out', pmid, ('row', rest[0]),
           t, by_code=True)
    elif typ == 'conflict':
        ev('IP4', 'conflict kept apart', 'log.tsv conflict', 'Check', 'kept out', pmid, ('row', rest[0]), t, by_code=True)
    elif typ == 'fix' and 'degree sign' in rest[0]:
        n = int(re.search(r'restored on (\d+) rows', rest[0]).group(1))
        ev('TL11', 'temperature restored', 'log.tsv fix', 'Check', 'fixed', pmid, ('fix', t), t, n=n, by_code=True)
    elif typ == 'recover':
        kv = dict(x.split('=', 1) for x in rest if '=' in x)
        n = int(kv.get('kept', 0)) + int(kv.get('bounds', 0) or 0)
        why = kv.get('reason', '')
        if n:
            kind = recover_kind(pmid, t, why)
            if why == 'unitfix' and (t, pmid) in UNITFIX_AT:
                continue                                 # the same rows have their own unitfix lines (41154624)
            action = 'fixed' if kind in ('PP1', 'RA8') else 'kept'
            if kind in ('CU5', 'CU6', 'CU8'):
                action = 'brought back (counted where stored)'   # these rows are in the catalogue counts below
            ev(kind, 'brought back (' + why.split(':')[0] + ')', 'log.tsv recover', 'Check', action, pmid,
               ('recover', t, pmid, why), t, n=n, by_code=True)
    elif typ == 'retext':
        why = rest[0]
        kind = ('TL9' if '<break/>' in why else 'TL2' if 'two decimal points' in why else 'X1' if 'figure captions' in why
                else 'X2' if 'drawn structure' in why else 'GLYPH' if 'glyph rule revised' in why else 'RETEXT?')
        ev(kind, 'text rebuilt', 'log.tsv retext', 'Convert', 'fixed', pmid, ('retext', pmid, kind), t, unit='papers',
           by_code=True)
    elif typ == 'wrong_paper':
        ev('IP18', 'wrong article refused', 'log.tsv wrong_paper', 'Check', 'kept out', pmid, ('paper', pmid, t), t,
           unit='papers', by_code=True)
    elif typ == 'file_rejected' and len(rest) > 1 and 'title check failed' in rest[1]:
        ev('IP18', 'file refused by the title check', 'log.tsv file_rejected', 'Check', 'kept out', pmid,
           ('file', pmid, rest[0]), t, unit='papers', by_code=True)
    elif typ == 'reread':
        why = rest[0]
        if why.startswith('blind re-read') or why.startswith('blind re-verify'):
            ev('DB2', 'read again blind', 'log.tsv reread', 'Read', 'fixed', pmid, ('reread', pmid), t, unit='papers',
               by_code=True)
        elif re.search(r'agents stopped mid-round|usage limit|agents died|verifier died|safety filter|never finished', why):
            ev('PR1', 'paper put back after its agents died', 'log.tsv reread', 'Check', 'fixed', pmid,
               ('reread', pmid, t), t, unit='papers', by_code=True)
        elif why.startswith('retext 2026-11-09'):
            ev('X1', 'read again with its captions', 'log.tsv reread', 'Read', 'fixed', pmid, ('reread', pmid, t), t,
               unit='papers read again', by_code=True)
    elif typ == 'supplement':
        ev('TL12', 'supplement obtained, paper read again', 'log.tsv supplement', 'Read', 'kept', pmid, ('supp', pmid), t,
           unit='papers', by_code=True)
    elif typ == 'dbcheck':
        kv = dict(x.split('=', 1) for x in rest if '=' in x)
        nu = int(kv.get('not_used', 0) or 0)
        if nu:
            ev('RA8', 'database-check verdict set aside', 'log.tsv dbcheck', 'Database check', 'kept out', pmid,
               ('dbcheck', pmid, t), t, n=nu, unit='verdicts', by_code=True)

# ---- 3. catalog.jsonl and bounds.jsonl: what rules let in, fixed or flagged on the values stored today
spec = importlib.util.spec_from_file_location('units', P('tools/units.py'))
units = importlib.util.module_from_spec(spec)
spec.loader.exec_module(units)


def conv(metric, raw_value, unit_for_conversion, raw_unit):
    try:
        v, u, err = units.normalize(metric, raw_value, unit_for_conversion or raw_unit)
    except Exception:
        return None
    return v if (err is None and v) else None


MISSED = set()                                           # (pmid, metric, printed cell) the verifier found skipped
for f in glob.glob(P('work/*.missed.read.json')) + glob.glob(P('work/old/*.missed.read.*.json')):
    pm = os.path.basename(f).split('.')[0]
    if pm in HOLD:
        continue                                         # never open a test-set paper's file
    try:
        d = json.load(open(f, encoding='utf-8'))
    except ValueError:
        continue
    for row in d.get('rows') or []:
        MISSED.add((pm, row.get('metric'), str(row.get('raw_value')).strip()))

SUPP_LOC = R(r'\bTable S\d|\bS\d+ Table|\bFig(?:ure)?\.? S\d|supplement|Additional file')
MUT = re.compile(r'[A-Z]\d+(?:[A-Z]|\*|del|ins)')


def changed_variant(a, b):
    """True when the verifier changed the measured variant, not only its spelling."""
    wt = lambda s: bool(re.fullmatch(r'\s*wild[- ]?type\s*|\s*WT\s*', s, I))
    if wt(a) != wt(b):
        return True
    return set(MUT.findall(a.upper().replace('P.', ''))) != set(MUT.findall(b.upper().replace('P.', '')))


def changed_substrate(a, b):
    """True when the verifier named another compound, not the same one spelled otherwise."""
    n = lambda s: re.sub(r'[^a-z0-9]', '', re.sub(r'\([^)]*\)', '', s.lower()))
    x, y = n(a), n(b)
    return bool(x) and bool(y) and x not in y and y not in x
for r in CAT:
    pmid = str(r['pmid'])
    t = (r.get('added') or r.get('checked') or '')[:16]
    key = ('row', r['row_id'])
    c = r.get('corrected') or {}
    note = ' '.join((str(r.get('verify_note') or ''), json.dumps(c, ensure_ascii=False)))
    if c and ({'unit_for_conversion', 'raw_unit', 'raw_value'} & set(c)):
        g = lambda f, d: (c[f] or {}).get('reader', d) if f in c else d
        before = conv(r['metric'], g('raw_value', r.get('raw_value')), g('unit_for_conversion', r.get('unit_for_conversion')),
                      g('raw_unit', r.get('raw_unit')))
        after = r.get('value')
        if before is None:
            ev('VCONV', "verifier gave the unit to convert a printed form code could not read", 'catalog.jsonl corrected',
               'Verify', 'fixed', pmid, key, t)
        elif after and abs(math.log10(after / before)) > 0.004:          # the stored number moved by more than 1%
            ev('PP1' if re.search(r'misprint', note, I) else 'RA4', 'verifier corrected a number off by a unit factor',
               'catalog.jsonl corrected', 'Verify', 'fixed', pmid, key, t)
    for fld, kind in (('variant', 'IP11'), ('substrate', 'IP12'), ('pH', 'RA2'), ('temperature_C', 'RA2')):
        if fld in c:
            rd, vf = (c[fld] or {}).get('reader'), (c[fld] or {}).get('verifier')
            if rd in ('', None) or vf in ('', None) or str(rd) == str(vf):
                continue
            if fld == 'variant' and not changed_variant(rd, vf):
                continue                                 # 'p.G154E' -> 'G154E': the same mutations written otherwise
            if fld == 'substrate' and not changed_substrate(rd, vf):
                continue                                 # 'coumaric acid' -> '4-coumaric acid': the same compound
            ev(kind, f'verifier changed the {fld}', 'catalog.jsonl corrected', 'Verify', 'fixed', pmid, key, t)
    for fld in ('enzyme', 'variant', 'substrate'):
        if fld in c and (c[fld] or {}).get('reader') in ('', None) and (c[fld] or {}).get('verifier'):
            ev('RA7', f'verifier filled an empty {fld}', 'catalog.jsonl corrected', 'Verify', 'kept', pmid, key, t)
    if 'page image' in str(r.get('quote_check') or ''):
        ev('TL6', 'confirmed on the page image: kept with a flag, not refused', 'catalog.jsonl quote_check', 'Check',
           'kept', pmid, key, t, by_code=True)
    rb = str(r.get('read_by') or '')
    if str(r.get('quote') or '').lstrip().startswith('[page image') and not rb.startswith('verifier'):
        ev('TL10', 'read off a page image by the reader', 'catalog.jsonl quote', 'Read', 'kept', pmid, key, t)
    if rb.startswith('verifier') or (pmid, r.get('metric'), str(r.get('raw_value')).strip()) in MISSED:
        ev('RA6', 'skipped by the reader, found by the verifier', 'catalog.jsonl read_by + work missed files', 'Verify',
           'kept', pmid, key, t)
    if 'mg' in str(r.get('unit') or ''):
        ev('CU8', 'stored in its own mass-concentration unit', 'catalog.jsonl unit', 'Convert', 'kept', pmid, key, t,
           by_code=True)
    if r['metric'] == 'kcat' and r.get('value') and 1e7 < float(r['value']) <= 1e8:
        ev('CU6', 'kcat between 1e7 and 1e8 s^-1 stored', 'catalog.jsonl value', 'Check', 'kept', pmid, key, t, by_code=True)
    if re.search(r'(?:pH|temperature_C) \S+ is not printed in the paper: left empty', str(r.get('condition_note') or '')):
        ev('CU5', 'an unprinted pH or temperature left empty, value stored', 'catalog.jsonl condition_note', 'Check', 'kept',
           pmid, key, t, by_code=True)
    if not str(r.get('organism') or '').strip():
        ev('CU5', 'stored with no organism given (refused as missing:organism before commit 3c6a6b4)', 'catalog.jsonl organism',
           'Check', 'kept', pmid, key, t, by_code=True)
    if not str(r.get('raw_unit') or '').strip() and str(r.get('unit_for_conversion') or '').strip():
        ev('CU5', "stored with the verifier's unit where the column prints none", 'catalog.jsonl raw_unit', 'Check', 'kept',
           pmid, key, t, by_code=True)
    if SUPP_LOC.search(str(r.get('location') or '')):
        ev('TL12', 'value printed only in a supplement', 'catalog.jsonl location', 'Read', 'kept', pmid, key, t)

for r in BOUND:
    ev('RA10', 'bound or not-detected value stored', 'bounds.jsonl', 'Read', 'kept', str(r['pmid']), ('row', r['row_id']),
       (r.get('added') or r.get('checked') or ''))

# ---- 4. the export (catlog_wide.csv): code rules applied to every record each time the catalogue is exported
SIGNAL = R(r"(?:after UniProt's (?:signal|transit) peptide|^unresolved: .{0,40}(?:signal|transit|leader|targeting))")
with open(P('catlog_wide.csv'), newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        pmid, key = r['pubmed_id'], ('record', r['measurement_id'])
        notes = ' '.join((r['kcat_note'], r['km_note'], r['kcat_over_km_note']))
        if 'differs from kcat ÷ Km' in notes:
            ev('PP6', 'kept with the note "differs from kcat ÷ Km"', 'catlog_wide.csv note', 'Check', 'kept', pmid, key, '',
               unit='records', by_code=True)
        if 'above the diffusion limit' in notes:
            ev('PP5', 'derived kcat/Km above the diffusion limit: flagged', 'catlog_wide.csv note', 'Check', 'flagged', pmid,
               key, '', unit='records', by_code=True)
        if SIGNAL.search(r['sequence_basis']):
            ev('IP8', 'precursor sequence trimmed to the stated mature chain, or left blank', 'catlog_wide.csv sequence_basis',
               'Check', 'fixed', pmid, key, '', unit='records', by_code=True)
        if r['mutation_signature'] and re.search(r'^mature chain|author numbering|mutagenesis primers', r['sequence_frame']):
            ev('IP16', "mutations placed in a numbering frame other than UniProt's", 'catlog_wide.csv sequence_frame',
               'Check', 'fixed', pmid, key, '', unit='records', by_code=True)
        if 'CHECK:' in r['uniprot_how']:
            ev('DB4', "UniProt's EC differs from the paper's: flagged", 'catlog_wide.csv uniprot_how', 'Check', 'flagged',
               pmid, key, '', unit='records', by_code=True)
        if r['kcat'] and r['km'] and not r['kcat_over_km'] and r['kcat_over_km_bound']:
            ev('CU7', 'no kcat/Km derived beside a printed bound', 'catlog_wide.csv', 'Check', 'kept out', pmid, key, '',
               unit='records', by_code=True)

# ---- 5. side tables CatLog keeps
for row in csv.DictReader((l for l in open(P('sources/implausible_as_printed.tsv'), encoding='utf-8')
                           if not l.startswith('#')), delimiter='\t'):
    ev('PP5', 'at the diffusion ceiling, checked against the paper, kept as printed with a flag',
       'sources/implausible_as_printed.tsv', 'Check', 'flagged', row['pmid'], ('implausible', row['row_id']), '',
       by_code=True)
for row in csv.DictReader((l for l in open(P('sources/natural_forms.tsv'), encoding='utf-8') if not l.startswith('#')),
                          delimiter='\t'):
    ev('IP6', 'older value: natural form moved from variant to enzyme', 'sources/natural_forms.tsv', 'Check', 'fixed',
       row['pmid'], ('natural', row['pmid'], row['variant']), '', unit='forms', by_code=True)
# IP2 found again by a person after the list (a reviewer, HUMAN_REVIEW.md): join_lines (5c441ee, 1d2a10f)
REVIEWER_PAPERS = {'33621065', '39897407', '8055963', '16431280'}   # named by the reviewer (record_merge HANDOFF.md)
for fname, commit in (('merged_sets_v2.json', '5c441ee'), ('merged_sets_v5_new.json', '1d2a10f')):
    for j in json.load(open(P('work/record_merge_20261111', fname), encoding='utf-8')):
        ev('IP2', "one printed line's records joined (a reviewer's finding)", 'work/record_merge_20261111/' + fname,
           'Check', 'fixed', j['pmid'], ('join', j['pmid'], tuple(sorted(j['rows']))), '', unit='joins', by_code=True)

# ======================================================================================================================
# per kind: what was caught, before and since the rule, in the papers of the first finding and in other papers
EFFECT_OF = {k['id']: k['kind'] for k in ALLK}
FIRSTS = {k['id']: first_papers(k) for k in ALLK}
LATER_FIRSTS = {'IP2': REVIEWER_PAPERS}                                # papers of a later finding that led to the counted rule


def is_catch(kind, action):
    if action in ('refused, now stored', 'brought back (counted where stored)'):
        return False                                     # a refusal later undone is never a catch
    if action == 'kept out':                             # for a kind that loses right values, a refusal is the loss
        return EFFECT_OF.get(kind) != 'FR' or kind == 'RA10'
    return True


def is_loss(kind, action):
    return EFFECT_OF.get(kind) == 'FR' and kind != 'RA10' and action in ('kept out', 'refused, now stored')


def count(events):
    """(amount, papers): amount sums n over distinct keys; papers = distinct PMIDs."""
    seen, amount, papers = set(), 0, set()
    for e in events:                                     # one value refused in two files counts once (row id or slot)
        if e['key'] in seen or (e['rid'] and ('rid', e['rid']) in seen):
            continue
        seen.add(e['key'])
        if e['rid']:
            seen.add(('rid', e['rid']))
        amount += e['n']
        if e['pmid']:
            papers.add(e['pmid'])
    return amount, papers


# Which counts cover a kind fully, partly or not at all, and what each misses (plain words; the README says more).
PARTLY = {
    'PP1': "verifier fixes count only when the verifier's note calls the header misprinted (the others are under RA4)",
    'PP2': 'refusals whose reason names a reprint; what readers skipped under the rule leaves no trace',
    'PP4': 'refusals naming a cell slip or a kcat/Km 5x or more off kcat ÷ Km',
    'TL2': 'texts given the two-decimal-point warning; what readers then read off page images is not separable',
    'TL11': "66 values of the paper where it was found again; '378C' read as 37 °C elsewhere leaves no trace",
    'TL12': 'values whose location is a supplementary table or figure (a supplement bound into the PDF counts too)',
    'RA1': 'refusals naming a constant that is not kcat or Km; what readers skipped leaves no trace',
    'RA2': 'verifier changes of a printed pH or temperature only; changes of the conditions text are not counted',
    'RA3': 'refusals naming a partial constant; what readers skipped leaves no trace',
    'RA4': ('verifier fixes that moved the stored number by a unit factor and do not call the header misprinted, '
            'and refusals naming a multiplier read the wrong way'),
    'RA6': 'values the verifier found that the reader skipped (read_by and the missed-value files)',
    'RA8': 'database-check verdicts set aside by code, audit drops restored, one verifier override undone',
    'RA11': 'drops, refusals and cleared limits whose reason names a constant not determined',
    'IP3': 're-read copies refused at add or dropped, and values a paper prints twice refused',
    'IP11': 'verifier changes of the mutations and refusals naming a wrong variant; spelling-only changes left out',
    'IP12': 'verifier changes to another compound and refusals naming a wrong substrate; spelling-only changes left out',
    'IP18': 'papers whose file was refused as another article',
    'CU2': '± taken off by pmfix and refusals naming a borrowed ±',
    'CU4': 'values brought back by recover after a parser change',
}
NONE = {
    'PP8': 'no rule (open); three checked agent cases, no reason class in the files',
    'TL1': 'the warning acts on texts (not opened here); its flag is set only in the website build',
    'TL3': 'acts on the quote shown with a value; leaves no count',
    'TL4': 'code cleans the characters before parsing; leaves no trace',
    'TL7': 'open; the refusals are the loss',
    'TL8': 'open; the refusals are the loss',
    'RA5': 'code completes a dropped ± silently',
    'RA7': 'open; no stored row shows a verifier filling an empty enzyme, variant or substrate; refusals are the loss',
    'RA12': 'no refusal in rejected.jsonl names an M^-2 kcat/Km (readers skip such cells)',
    'RA13': 'a reader rule; leaves no count', 'RA14': 'a reader rule; leaves no count',
    'IP1': 'grouping code never makes the pairing; leaves no count',
    'IP7': '3 papers fixed; no trace in the files', 'IP9': "about 790 values (an enrichment sweep, commit 31721e1); not recounted",
    'IP10': 'open', 'IP13': 'a reader rule; leaves no count', 'IP14': 'a reader rule; leaves no count',
    'IP15': 'grouping code; leaves no count', 'IP17': 'about 450 values (an enrichment sweep, commit 31721e1); not recounted',
    'IP19': 'export code; leaves no count', 'IP20': 'title check; one paper',
    'DB1': 'by design database values never become catalogue rows', 'DB3': '3 papers; not recounted',
    'DB5': 'export code; leaves no count',
}
for i in range(2, 19):
    NONE.setdefault(f'PR{i}', 'a process failure; no values to count')
PARTLY.update({
    'PP3': 'no rule (open): agents caught these in sweeps and audits on their own judgement; counted from drop reasons',
    'PP7': 'no rule (open): verifiers reject on their own judgement; counted from refusal reasons',
    'TL5': 'one verifier rejection names a missing exponent; code refusals of a bare × 10 do not say so',
    'RA9': 'only the paper where it was found (its 20 values brought back); no later case recorded',
    'IP5': 'one paper brought back after the slot rules (18783250); later slot splits leave no trace',
    'CU3': 'only the two papers named in its finding',
})

# counts that record everything the rule did, in its unit, from code-written traces or exact fields (no reading of
# free-text reasons): a complete count for the unit named
COMPLETE = {'TL6', 'TL9', 'TL10', 'CU1', 'CU5', 'CU6', 'CU7', 'CU8', 'RA10', 'IP2', 'IP4', 'IP6', 'IP8', 'IP16', 'DB2',
            'DB4', 'PP5', 'PP6', 'PR1', 'X1', 'X2'}
assert not COMPLETE & set(PARTLY)
COMPLETE_NOTE = {
    'TL6': 'every stored value code kept with the page-image flag, and the 32 OCR-hyphen values brought back',
    'TL9': 'every text rebuilt by the rule', 'TL10': "every stored value the reader quoted from a page image",
    'CU1': 'every value still refused for a unit code does not convert',
    'CU5': 'every stored value with no organism given, an unprinted pH or temperature left empty, or the verifier\'s '
           'unit where the column prints none; the 310 values brought back by recover are among them',
    'CU6': 'every stored kcat between 1e7 and 1e8 s^-1; the 12 brought back by recover are among them',
    'CU7': 'every record the export now leaves without a derived kcat/Km', 'CU8': 'every value stored in mass units',
    'RA10': 'every bound or not-detected value stored, and the verifier\'s refusals of censored rows the paper does not '
            'support (the second by reason text)',
    'IP2': "every join of one printed line's records made by the rule after the reviewer's finding (when commits 5c441ee "
           'and 1d2a10f applied it)',
    'IP4': 'every conflict kept apart and every refused re-add of an audit-dropped slot',
    'IP6': 'every form line of sources/natural_forms.tsv (older rows; readers following the rule leave no trace)',
    'IP8': 'every record trimmed after UniProt\'s signal or transit peptide or left blank where UniProt marks none',
    'IP16': 'every mutant record whose mutations matched only in another numbering frame',
    'DB2': 'every paper read again blind; the wrong values that found are counted in paper/evidence, not here',
    'DB4': 'every record flagged CHECK: in uniprot_how',
    'PP5': 'every value reviewed at the diffusion ceiling (sources/implausible_as_printed.tsv) and every derived kcat/Km '
           'flagged at export',
    'PP6': 'every record carrying the note, and the 113 values brought back when the rule entered',
    'PR1': 'every paper put back to be read after its agents died', 'X1': 'every text rebuilt with its captions',
    'X2': 'every unread text rebuilt',
}


def amount_in(events, unit):
    return count([e for e in events if e['unit'] == unit])


BYK = collections.defaultdict(list)
BY_PAPER_DAY = collections.defaultdict(list)
for e in EV:
    BYK[e['kind']].append(e)
    if e['t']:
        BY_PAPER_DAY[(e['t'][:10],)].append(e)

ROWS = []
for k in ALLK:
    kid = k['id']
    evs = BYK.get(kid, [])
    rules = RULES[kid]
    t_rule = rules[0][1] if rules else ''
    t_last = rules[-1][1] if rules else ''
    firsts = FIRSTS[kid] | LATER_FIRSTS.get(kid, set())
    since = lambda e: bool(t_rule) and (e['by_code'] or (e['t'] and e['t'] >= t_rule))
    catches = [e for e in evs if is_catch(kid, e['action'])]
    losses = [e for e in evs if is_loss(kid, e['action'])]
    c_since = [e for e in catches if since(e)]
    c_before = [e for e in catches if not since(e)]
    unit = (collections.Counter(e['unit'] for e in c_since) or collections.Counter(e['unit'] for e in catches)
            or collections.Counter(['values'])).most_common(1)[0][0]
    a_all, p_all = amount_in(catches, unit)
    a_since, p_since = amount_in(c_since, unit)
    a_other, p_other = amount_in([e for e in c_since if e['pmid'] not in firsts], unit)
    a_before, p_before = amount_in(c_before, unit)
    l_before = count([e for e in losses if e['t'] and t_last and e['t'] < t_last])[0]
    l_after_last = count([e for e in losses if e['t'] and t_last and e['t'] >= t_last])[0]
    # the finding, in papers read
    found, basis = '', ''
    if k['found_route'] != 'old system' and k['first_found']:
        # the finding's own trace, never after the rule's commit: for a kind code found, the finding paper's first
        # refusal that day (the refusal was the finding, whatever heading it is sorted under here); for a kind people
        # or agents found, their first verdict of this kind in the finding paper that day
        cap = t_rule if t_rule and t_rule[:10] >= k['first_found'] else ''     # PP4's rule came before its finding
        day = [e for e in BY_PAPER_DAY.get((k['first_found'],), []) if e['pmid'] in FIRSTS[kid] and e['t']
               and (not cap or e['t'] <= cap)]
        if k['found_route'] == 'code check':
            tr = sorted(e['t'] for e in day if e['action'] in ('kept out', 'refused, now stored') and not e['by_code'])
        else:
            tr = sorted(e['t'] for e in day if e['kind'] == kid and not e['by_code'])
        fix = sorted(e['t'] for e in evs if e['by_code'] and e['t'][:10] == k['first_found']
                     and (not cap or e['t'] <= cap))
        if k.get('found_time'):
            found, basis = papers_read(k['found_time']), 'the log line that recorded the finding'
        elif tr:
            found, basis = papers_read(tr[0]), 'first trace of the finding in the files'
        elif fix:
            found, basis = papers_read(fix[0]), "the rule's first fix that day (the finding came first)"
        elif t_rule and t_rule[:10] == k['first_found']:
            found, basis = papers_read(t_rule), 'rule commit of the same day (the finding came first)'
        else:
            found, basis = papers_read(k['first_found'] + ' 00:00'), 'start of the day of the finding'
    steps = collections.Counter()
    seen = set()
    for e in c_since:
        if e['key'] not in seen and not (e['rid'] and ('rid', e['rid']) in seen):
            seen.add(e['key'])
            if e['rid']:
                seen.add(('rid', e['rid']))
            steps[(e['step'], e['action'], e['unit'])] += e['n']
    acts = collections.Counter()
    for (s, a, u), n in steps.items():
        if u == unit:
            acts[a] += n
    srcs = collections.OrderedDict()
    for e in (c_since or catches):
        srcs.setdefault(f"{e['source']} ({e['sub']})", None)
    again = collections.Counter()
    for x in k['found_again'].split(';'):
        x = x.strip()
        if x:
            route = next((r for r in sorted(FINDER, key=len, reverse=True) if x[11:].startswith(r)), '?')
            again[FINDER.get(route, '?')] += 1
    if kid == 'IP2':
        again['people'] += 1                             # the reviewer's finding (after the list)
    has_rule = bool(t_rule)
    countable = ('no' if a_all == 0 or kid in NONE else 'yes' if kid in COMPLETE else 'partly')
    ROWS.append({
        'id': kid,
        'kind': k['class'],
        'on_list_of_2_nov': 'yes' if not kid.startswith('X') else 'no (found after the list)',
        'origin': k['origin'],
        'effect': EFFECT[k['kind']],
        'first_found_by': FINDER[k['found_route']],
        'first_found_route': k['found_route'],
        'first_found_papers': ' '.join(sorted(FIRSTS[kid])),
        'papers_read_when_found': found,
        'found_position_basis': basis,
        'found_again_by': '; '.join(f'{g} {n}' for g, n in sorted(again.items())),
        'rule_step': STEP.get(k['guard_layer'], k['guard_layer']) if has_rule else 'none (open)',
        'status': k['status'],
        'rule_commit': k['rule_commit'],
        'papers_read_at_rule': papers_read(t_rule) if has_rule else '',
        'papers_read_since_rule': PAPERS_NOW - papers_read(t_rule) if has_rule else '',
        'later_rule_changes': len(rules) - 1 if has_rule else '',
        'papers_read_at_later_changes': ' '.join(str(papers_read(t)) for _, t in rules[1:]),
        'unit': unit if a_all else '',
        'caught_since_rule': a_since if has_rule else '',
        'papers_since_rule': len(p_since) if has_rule else '',
        'caught_since_rule_other_papers': a_other if has_rule else '',
        'papers_since_rule_other_papers': len(p_other) if has_rule else '',
        'kept_out_since_rule': acts['kept out'] if has_rule else '',
        'fixed_since_rule': acts['fixed'] if has_rule else '',
        'kept_since_rule': acts['kept'] if has_rule else '',
        'flagged_since_rule': acts['flagged'] if has_rule else '',
        'caught_before_rule': a_before,
        'papers_before_rule': len(p_before),
        'caught_all': a_all,
        'papers_all': len(p_all),
        'lost_before_last_rule_change': l_before if EFFECT_OF[kid] == 'FR' and has_rule else '',
        'lost_after_last_rule_change': l_after_last if EFFECT_OF[kid] == 'FR' and has_rule else '',
        'by_step_since_rule': '; '.join(f'{s}: {a} {n} {u}' for (s, a, u), n in
                                        sorted(steps.items(), key=lambda x: (-x[1], x[0]))),
        'countable': countable,
        'how_counted': '; '.join(srcs) if a_all else '',
        'count_note': (NONE.get(kid, '') if countable == 'no' else COMPLETE_NOTE.get(kid, '') if countable == 'yes'
                       else PARTLY.get(kid, '')),
    })

ASSIGNED = set(RULES)
UNASSIGNED = collections.Counter()
for e in EV:
    if e['kind'] not in ASSIGNED and is_catch('?', e['action']):
        UNASSIGNED[(e['kind'], e['sub'], e['unit'])] += e['n']

# ======================================================================================================================
# checks against facts recorded elsewhere (a changed input stops here)
_r = {r['id']: r for r in ROWS}
assert _r['PP1']['first_found_papers'] == '25514023' and _r['RA3']['first_found_papers'] == '21361343'
assert {x['id'] for x in ROWS if x['first_found_by'] == 'people'} == {'IP6', 'IP7', 'IP9', 'IP10', 'DB5', 'CU7'}
assert collections.Counter(x['first_found_by'] for x in ROWS if x['on_list_of_2_nov'] == 'yes') == \
    {'agents': 42, 'known at the start': 26, 'code': 11, 'people': 6}          # Fig. 4 v1, fig4_data.py BY_FINDER
assert sum(1 for p in LOG if len(p) > 2 and p[2] == 'unitfix' and p[0] <= '2026-11-15 00:30') == 363   # to this README
assert sum(e['n'] for e in EV if e['kind'] == 'CU5' and e['source'] == 'log.tsv recover') == 310   # taxonomy CU5
assert sum(e['n'] for e in EV if e['kind'] == 'TL11') == 66
assert sum(1 for e in EV if e['source'] == 'log.tsv retext' and e['kind'] == 'TL9') == 125
assert ['2026-11-06 10:44', '28362483', 'add', 'kept=8', 'dup=0', 'rejected=6', 'status=done'] in LOG
assert ['2026-11-12 22:49', '34680172', 'add', 'kept=0', 'dup=0', 'rejected=0', 'status=needs_supplement'] in LOG

# ======================================================================================================================
COLS = [c for c in ROWS[0]]
with open(os.path.join(HERE, 'rules.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(ROWS)

# one line per kind, paper, step, action and what was done: for drawing catches along papers read
groups = collections.defaultdict(lambda: {'n': 0, 'times': []})
SEEN_G = collections.defaultdict(set)
for e in EV:
    if e['kind'] not in ASSIGNED:
        continue
    kid = e['kind']
    rules = RULES[kid]
    t_rule = rules[0][1] if rules else ''
    catch = is_catch(kid, e['action'])
    loss = is_loss(kid, e['action'])
    if not (catch or loss):
        continue
    since = bool(t_rule) and (e['by_code'] or (e['t'] and e['t'] >= t_rule))
    if e['key'] in SEEN_G[(kid, catch)] or (e['rid'] and ('rid', e['rid']) in SEEN_G[(kid, catch)]):
        continue
    g = groups[(kid, e['pmid'], e['step'], e['action'] if catch else 'lost: ' + e['action'], e['sub'], e['unit'],
                'yes' if since else ('no' if t_rule else 'no rule'))]
    SEEN_G[(kid, catch)].add(e['key'])
    if e['rid']:
        SEEN_G[(kid, catch)].add(('rid', e['rid']))
    g['n'] += e['n']
    if e['t']:
        g['times'].append(e['t'])
with open(os.path.join(HERE, 'catches_by_paper.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['id', 'pmid', 'step', 'action', 'what', 'unit', 'since_rule', 'amount', 'papers_read_at_first',
                'in_finding_paper'])
    for (kid, pmid, step, action, sub, unit, since), g in sorted(groups.items()):
        w.writerow([kid, pmid, step, action, sub, unit, since, g['n'],
                    papers_read(min(g['times'])) if g['times'] else '',
                    'yes' if pmid in (FIRSTS[kid] | LATER_FIRSTS.get(kid, set())) else 'no'])

if __name__ == '__main__':
    print(f'papers read now {PAPERS_NOW}; log to {LAST_LOG}; events {len(EV)}')
    for r in ROWS:
        print(r['id'], r['first_found_by'][:6], 'found@', r['papers_read_when_found'], 'rule@', r['papers_read_at_rule'],
              r['rule_step'], '| since', r['caught_since_rule'], r['unit'], 'in', r['papers_since_rule'],
              '| other', r['caught_since_rule_other_papers'], 'in', r['papers_since_rule_other_papers'],
              '| before', r['caught_before_rule'], '| lost', r['lost_before_last_rule_change'], '/', r['lost_after_last_rule_change'],
              '|', r['countable'])
    print('not on a kind:')
    for k, n in sorted(UNASSIGNED.items(), key=lambda x: -x[1]):
        print('  ', k, n)
