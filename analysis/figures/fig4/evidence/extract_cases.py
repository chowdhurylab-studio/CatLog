"""Fig. 4 v2 evidence: three co-learning cases told from start to finish, every step and number read from CatLog's
own files. Writes cases.json beside this script; cases.md tells the same cases in words.

Run (read-only on the project, seconds; never opens texts/, papers/ or a held-out paper's files):
    python3 -I -B writing/figures/fig4/v2/evidence/cases/extract_cases.py

Files read: log.tsv, catalog.jsonl, rejected.jsonl, sources/db_values.tsv, sources/holdout_locked.txt,
sources/provenance_backfill.tsv, sources/prompt_versions/<hash>.md, sources/implausible_as_printed.tsv,
work/old/25514023.verify.1792637045.json, work/old/12226525.verify.1793116325.json,
work/old/12591933.verify.1794252840.json, work/record_merge_20261111/{merged_sets_v2,merged_sets_v5_new,
check_results_v1,check_results_v2,check_results_v5}.json, tools/units.py (to convert units, as the catalogue does),
and git (commit times only).

'Papers read so far' at a moment = the distinct papers with an 'add' line in log.tsv up to that minute, the
definition writing/fig1_v8/ref/catalogue_counts.py uses for papers_read. It orders the steps without dates.
"""
import bisect
import collections
import csv
import datetime
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, *(['..'] * 6)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import units  # noqa: E402  (pure functions; converts a printed cell and unit as the catalogue does)

P = lambda *a: os.path.join(ROOT, *a)
HOLD = {ln.strip() for ln in open(P('sources/holdout_locked.txt')) if ln.strip() and not ln.startswith('#')}
env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')


def check(what, ok):
    if not ok:
        raise SystemExit(f'cases: {what}')


def commit(h):
    out = subprocess.run(['git', '-C', ROOT, 'show', '-s', '--format=%h|%ad|%s', '--date=format:%Y-%m-%d %H:%M', h],
                         capture_output=True, text=True, check=True, env=env).stdout.strip().split('|', 2)
    return {'commit': out[0], 'time': out[1], 'subject': out[2]}


def jl(path, needle=None):
    with open(P(path), 'rb') as fh:
        for raw in fh:
            if needle is None or needle in raw:
                yield json.loads(raw)


# ------------------------------------------------------------------------------------------------- log and order
LOG = []
for n, line in enumerate(open(P('log.tsv'), encoding='utf-8'), 1):
    f = line.rstrip('\n').split('\t')
    if len(f) >= 3:
        LOG.append((n, f))
FIRST_ADD = {}
for n, f in LOG:
    if f[2] == 'add' and f[1] not in FIRST_ADD:
        FIRST_ADD[f[1]] = f[0]
ADD_TIMES = sorted(FIRST_ADD.values())
NOW_READ = len(ADD_TIMES)


def read_so_far(t):
    return bisect.bisect_right(ADD_TIMES, t)


def lines(pmid, kinds, day=None):
    return [(n, f) for n, f in LOG if f[1] == pmid and f[2] in kinds and (day is None or f[0].startswith(day))]


# databases, in catalogue units (kcat s^-1, Km mM, kcat/Km mM^-1 s^-1)
DB = collections.defaultdict(list)
with open(P('sources/db_values.tsv'), newline='') as fh:
    for row in csv.DictReader(fh, delimiter='\t'):
        try:
            DB[(row['pmid'], row['metric'])].append(dict(source=row['source'], value=float(row['value']),
                                                         substrate=row['substrate'], comment=row['comment']))
        except ValueError:
            pass


def near(a, b, tol=0.02):
    return a and b and abs(a / b - 1) <= tol


def factor(metric, unit):
    """What one printed unit of this header is in catalogue units (None if the unit does not parse)."""
    v, _, err = units.normalize(metric, '1', unit)
    return v if err is None else None


BACKFILL = {}
with open(P('sources/provenance_backfill.tsv'), newline='') as fh:
    for row in csv.DictReader(fh, delimiter='\t'):
        BACKFILL[row['row_id']] = row


def prompt_line(h, needle):
    for i, ln in enumerate(open(P(f'sources/prompt_versions/{h}.md'), encoding='utf-8'), 1):
        if needle in ln:
            return i
    return None


out = {'made_by': 'writing/figures/fig4/v2/evidence/cases/extract_cases.py',
       'made': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
       'papers_read_now': NOW_READ, 'papers_read_definition': 'distinct papers with an add line in log.tsv up to that '
       'minute (writing/fig1_v8/ref/catalogue_counts.py, papers_read)', 'cases': []}

# =================================================================================================================
# A. A misprinted unit header: an auditor finds it, the verifier's instructions change, the next verifiers fix it
A_PMID, B_PMID = '25514023', '12226525'
check('A: no case paper is held out', not ({A_PMID, B_PMID, '12591933', '11694539'} & HOLD))
drops = lines(A_PMID, ('drop', 'audit_drop'), '2026-10-11')
audit = [(n, f) for n, f in drops if f[2] == 'audit_drop']
check('A: one audit drop on 11 Oct', len(audit) == 1)
dropped = sorted({f[3] for n, f in drops if 'kcat header' in f[4] or '60x too low' in f[4]})
check('A: 11 kcat values dropped as 60x too low', len(dropped) == 11)
before = {r['row_id']: r for r in jl('rejected.jsonl', A_PMID.encode()) if r['row_id'] in dropped}
after = {r['row_id']: r for r in jl('catalog.jsonl', f'"{A_PMID}"'.encode()) if r['row_id'] in dropped}
check('A: the 11 are in rejected.jsonl and back in catalog.jsonl', len(before) == len(after) == 11)
a_rows = []
for rid in dropped:
    b, a = before[rid], after[rid]
    check(f'A: {rid} came back as the same printed cell, converted as s^-1',
          (a['raw_value'], a['raw_unit'], a.get('unit_for_conversion')) == (b['raw_value'], b['raw_unit'], 's^-1'))
    a_rows.append(dict(variant=b['variant'], printed=b['raw_value'], header=b['raw_unit'], stored_before=b['value'],
                       stored_now=a['value'], ratio=round(a['value'] / b['value'], 3)))
check('A: every value moved by 60', all(abs(r['ratio'] - 60) < 0.01 for r in a_rows))
wt = [r for r in jl('catalog.jsonl', f'"{A_PMID}"'.encode()) if r['metric'] == 'kcat' and r['variant'] == 'wild type'
      and r['substrate'] == 'MSmB']
check('A: one wild-type MSmB kcat (Table 5, s^-1)', len(wt) == 1 and wt[0]['value'] == 3.56)
catlog_kcat = {r['variant']: r['stored_now'] for r in a_rows} | {'wild type': wt[0]['value']}
db_a = []
for q in DB[(A_PMID, 'kcat')]:
    m = re.search(r'(?:mutant |; )([A-Z]\d+[A-Z])\b', q['comment'])
    var = m.group(1) if m else ('wild type' if re.search(r'wild-?type|wildtype', q['comment']) else None)
    if var in catlog_kcat:
        db_a.append(dict(source=q['source'], variant=var, database=q['value'], catlog=catlog_kcat[var],
                         ratio=round(q['value'] / catlog_kcat[var], 4)))
check('A: BRENDA and OED list the 12 MSmB kcat values (wild type + 11 mutants) each',
      collections.Counter(d['source'] for d in db_a) == {'BRENDA': 12, 'OED': 12})
check('A: every one of them about 60-fold below CatLog', all(1 / 61.5 < d['ratio'] < 1 / 58.5 for d in db_a))
v_old = BACKFILL[dropped[0]]['verify_prompt']
old_verdict = [d for d in json.load(open(P('work/old/25514023.verify.1792637045.json')))['verdicts']
               if d.get('metric') == 'kcat' and d.get('raw_value') == '3.88±2.6']
check('A: the first verifier confirmed the D132A cell as printed', len(old_verdict) == 1 and old_verdict[0]['verdict'] == 'confirm')
recover = lines(A_PMID, ('recover',))
check('A: one recover line, 11 kept', len(recover) == 1 and 'kept=11' in recover[0][1][3])
rule = commit('cb53ec3')
unitfix_cmd = commit('14d5288')

# 12226525: the next paper's verifier applies the new rule
b_all = [r for r in jl('catalog.jsonl', f'"{B_PMID}"'.encode()) if str(r['pmid']) == B_PMID]
b_rows = [r for r in b_all if r['metric'] == 'kcat/Km']
check('A: 12226525 has five kcat/Km values, all from Table II', len(b_rows) == 5 and {r['location'] for r in b_rows} == {'Table II'})
TABLE_II = {(r['enzyme'], r['substrate']) for r in b_rows}
kc = {r['substrate']: r['value'] for r in b_all if r['metric'] == 'kcat' and (r['enzyme'], r['substrate']) in TABLE_II}
km = {r['substrate']: r['value'] for r in b_all if r['metric'] == 'Km' and (r['enzyme'], r['substrate']) in TABLE_II
      and r['location'] == 'Table II'}
check('A: the five rows have their kcat and Km', len(kc) == len(km) == 5)
verify_b = json.load(open(P('work/old/12226525.verify.1793116325.json')))['verdicts']
verdicts_b = {d['raw_value']: d for d in verify_b if d.get('metric') == 'kcat/Km'}
v_new = {BACKFILL[r['row_id']]['verify_prompt'] for r in b_rows}
check('A: one verifier prompt for the five', len(v_new) == 1)
v_new = v_new.pop()
c_rows = []
for r in sorted(b_rows, key=lambda r: -r['value']):
    printed = units.normalize('kcat/Km', r['raw_value'], r['raw_unit'])[0]           # under the printed nM^-1 s^-1
    d = verdicts_b[r['raw_value']]
    check(f"A: {r['raw_value']}: verifier fixed the unit to mM-1 s-1", (d['verdict'], d['fix']) == ('fix', {'unit_for_conversion': 'mM-1 s-1'}))
    sub = r['substrate']
    own = kc[sub] / km[sub] if sub in kc and sub in km else None
    dbs = sorted({q['source'] for q in DB[(B_PMID, 'kcat/Km')] if near(q['value'], printed)})
    c_rows.append(dict(substrate=sub, printed_cell=r['raw_value'], header=r['raw_unit'],
                       as_printed_M=round(printed * 1e3, 3), catlog_M=round(r['value'] * 1e3, 3),
                       kcat_over_km_M=round(own * 1e3, 1) if own else None, databases_at_printed=dbs))
check('A: SABIO-RK and OED list all five at the printed header', all(x['databases_at_printed'] == ['OED', 'SABIO-RK'] for x in c_rows))
check('A: printed / stored = 1e6 for all five', all(abs(x['as_printed_M'] / x['catlog_M'] - 1e6) < 1 for x in c_rows))
brenda_b = sorted(q['value'] for q in DB[(B_PMID, 'kcat/Km')] if q['source'] == 'BRENDA')
check("A: BRENDA's five kcat/Km for 12226525 are the paper's kcat cells", brenda_b == sorted(kc.values()))

# reach: values whose unit CatLog corrected because the paper's own numbers show a misprinted unit, by two routes
#  1. the verifier while reading: verify_note names a misprint (or a 'typo') and the unit code converts with differs
#     from the printed one by a factor (header-multiplier conventions, whose notes do not, are not counted);
#  2. a later check: unitfix lines in log.tsv (audits, database checks, the scale and Vmax sweeps, the blind re-read),
#     less the four that are not a misprint corrected (below), and 25514023's recover line.
NOT_A_MISPRINT = {'41657244': 'a code change read the spaced exponent; the stored value did not change',
                  '42639739': 'a code change read the spaced exponent; the stored value did not change',
                  '40723313': "the reverse: a verifier's wrong unit override taken back to the printed unit",
                  '37686129': "the header's 'k s-1' was right; CatLog's reader and verifier had taken the k as stray"}
RULE_T = rule['time']
later = collections.defaultdict(dict)          # pmid -> row_id -> time of the unitfix
for n, f in LOG:
    if f[2] == 'unitfix' and f[1] not in HOLD and f[1] not in NOT_A_MISPRINT:
        later[f[1]].setdefault(f[3], f[0])
later[A_PMID] = {rid: recover[0][1][0] for rid in dropped}
later_ids = {rid for d in later.values() for rid in d}
reach = collections.defaultdict(list)
for r in jl('catalog.jsonl', b'unit_for_conversion'):
    p = str(r['pmid'])
    if p in HOLD or not r.get('unit_for_conversion'):
        continue
    note = r.get('verify_note') or ''
    is_later = r['row_id'] in later_ids
    if not is_later and (not re.search(r'misprint|typo', note, re.I) or 'unit corrected to' in note):
        continue
    fp, fu = factor(r['metric'], r['raw_unit']), factor(r['metric'], r['unit_for_conversion'])
    if fp is None or fu is None or abs(fu / fp - 1) <= 0.02:
        continue
    as_printed = r['value'] * fp / fu
    dbv = DB[(p, r['metric'])]
    reach[p].append(dict(t=later[p][r['row_id']] if is_later else r['checked'], later=is_later, f=fp / fu,
                         metric=r['metric'], raw=r['raw_unit'], used=r['unit_for_conversion'],
                         db_misprint=any(near(q['value'], as_printed) for q in dbv),
                         db_right=any(near(q['value'], r['value']) for q in dbv)))
check('A: every later-check paper found in the catalogue', set(later) <= set(reach))
papers = sorted(reach, key=lambda p: min(x['t'] for x in reach[p]))
pre = [p for p in papers if min(x['t'] for x in reach[p]) <= RULE_T]
post = [p for p in papers if p not in pre]
check('A: the later checks all came after the rule', not (set(later) & set(pre)))
pre_read = read_so_far(RULE_T)
series = []
for p in post:
    xs = reach[p]
    t = min(x['t'] for x in xs)
    series.append(dict(pmid=p, papers_read_so_far=read_so_far(t), values=len(xs),
                       by=('a later check' if xs[0]['later'] else 'the verifier while reading'),
                       factor=sorted({float(f'{x["f"]:.4g}') for x in xs})))
post_vals = [x for p in post for x in reach[p]]
MIL = lambda x: x['metric'] == 'kcat/Km' and abs(x['f'] / 1e6 - 1) < 0.02     # printed header a million-fold off
million = []
for p in papers:
    xs = [x for x in reach[p] if MIL(x)]
    if xs:
        million.append(dict(pmid=p, before_rule=p in pre, printed_unit=sorted({x['raw'] for x in xs}), values=len(xs),
                            nM_printed=any('nM' in x['raw'] for x in xs),
                            database_lists_the_misprint=sum(x['db_misprint'] for x in xs),
                            database_lists_catlog=sum(x['db_right'] for x in xs)))
out['cases'].append({
    'id': 'A', 'title': 'A misprinted unit header', 'found_by': 'an agent (an auditor)', 'kind': 'a wrong value kept',
    'papers': {A_PMID: 'PLoS One 2014, mycothiol S-conjugate amidase (Mca), Corynebacterium glutamicum',
               B_PMID: 'Plant Physiol 2002, benzoyl-CoA:benzyl alcohol benzoyltransferase (BEBT), Clarkia breweri'},
    'steps': [
        {'step': 'read', 'paper': A_PMID, 'papers_read_so_far': read_so_far(FIRST_ADD[A_PMID]),
         'what': "The reader stored Table 6's kcat cells under the printed header 'kcat (min-1)'. The verifier saw that "
                 "Table 5 and the kcat/Km column point to s-1 and still confirmed the cells as printed, as its "
                 "instructions then said ('If all three are printed exactly as read, confirm them').",
         'quote': old_verdict[0]['reason'],
         'files': ['work/old/25514023.verify.1792637045.json (verdict i=28)',
                   f'sources/prompt_versions/{v_old}.md:{prompt_line(v_old, "printed exactly as read")} (sources/provenance_backfill.tsv)']},
        {'step': 'found', 'who': 'an auditor (agent)', 'paper': A_PMID, 'papers_read_so_far': read_so_far(audit[0][1][0]),
         'what': 'An auditor checked the stored D132A kcat (0.0647 s-1) and found it 60-fold low: Table 5 and the '
                 "Results print the same wild-type cell in s-1, and Table 6's own kcat/Km closes only in s-1. "
                 'The 11 Table 6 kcat values were dropped.',
         'files': [f'log.tsv:{audit[0][0]} (audit_drop {audit[0][1][3]})', f'log.tsv:{drops[0][0]}-{drops[-1][0]}',
                   'work/audit_sample3.json']},
        {'step': 'rule', 'papers_read_so_far': read_so_far(rule['time']), 'commit': rule,
         'what': "Two minutes later the verifier's instructions gained an exception: when the paper itself shows a "
                 "header's unit is a misprint (the same measurement printed elsewhere in another unit, the table's own "
                 'kcat/Km closing only in that unit), set that unit and say where the paper shows it. The next morning '
                 'a command to correct a unit instead of dropping the value (catlog.py unitfix) brought the 11 back.',
         'files': [f"git show {rule['commit']} -- prompts/verify.md",
                   f"git show {unitfix_cmd['commit']} ({unitfix_cmd['time']})",
                   f'log.tsv:{recover[0][0]} (recover kept=11 reason=unitfix)']},
        {'step': 'caught again', 'who': "a later paper's verifier (agent)", 'paper': B_PMID,
         'papers_read_so_far': read_so_far(FIRST_ADD[B_PMID]),
         'what': "Table II heads kcat/Km in nM-1 s-1. The verifier, whose instructions held the new exception and named "
                 '25514023, set all five to mM-1 s-1 because every row closes as kcat/Km only in that unit.',
         'quote': verdicts_b['85.2']['reason'],
         'files': ['work/old/12226525.verify.1793116325.json', f'sources/prompt_versions/{v_new}.md:'
                   f'{prompt_line(v_new, "25514023")}', 'sources/provenance_backfill.tsv (verify_prompt of the five rows)',
                   'paper/evidence/agent_highlights_20261028/boxes/plain_r8/12226525.md']},
        {'step': 'databases', 'paper': f'{A_PMID}, {B_PMID}',
         'what': 'BRENDA and OED list all 12 MSmB kcat values of 25514023 (wild type and 11 mutants) 60-fold low; '
                 'SABIO-RK and OED list the five kcat/Km of 12226525 a million-fold high, as the header prints them; '
                 "BRENDA lists 12226525's five kcat cells as its kcat/Km.",
         'files': ['sources/db_values.tsv']},
        {'step': 'since', 'papers_read_so_far': NOW_READ,
         'what': "Papers whose stored values CatLog unit-corrected because the paper's own numbers show a misprinted "
                 'unit, held-out papers left out, by two routes: the verifier while reading (its note names a '
                 'misprint and the unit it converts with differs from the printed one by a factor) and later checks '
                 '(unitfix lines: audits, database checks, the scale and Vmax sweeps, the blind re-read). Some '
                 'verifiers made such fixes before the rule; after it the fix is in every verifier\'s instructions.',
         'files': ['catalog.jsonl (unit_for_conversion, verify_note)', 'log.tsv (unitfix lines)']}],
    'numbers': {
        'a_25514023_kcat_s-1': a_rows, 'a_25514023_databases': db_a,
        'b_12226525_kcat_over_km_M-1_s-1': c_rows, 'b_12226525_brenda_lists_kcat_cells_as_kcat_over_km': brenda_b,
        'factor_25514023': 60, 'factor_12226525': 1e6,
        'reach': {
            'papers_before_rule': len(pre), 'papers_before_rule_list': pre,
            'values_before_rule': sum(len(reach[p]) for p in pre), 'papers_read_by_rule': pre_read,
            'papers_after_rule': len(post), 'values_after_rule': len(post_vals),
            'papers_read_after_rule': NOW_READ - pre_read,
            'after_rule_by_the_verifier_while_reading': sum(1 for s in series if s['by'] == 'the verifier while reading'),
            'after_rule_by_a_later_check': sum(1 for s in series if s['by'] == 'a later check'),
            'values_after_rule_by_the_verifier_while_reading': sum(1 for x in post_vals if not x['later']),
            'values_after_rule_by_a_later_check': sum(1 for x in post_vals if x['later']),
            'values_after_rule_a_database_lists_at_the_misprint': sum(x['db_misprint'] for x in post_vals),
            'values_after_rule_a_database_lists_as_catlog': sum(x['db_right'] for x in post_vals),
            'later_check_lines_left_out': NOT_A_MISPRINT,
            'kcat_over_km_a_million_fold_off_like_12226525': million,
            'note': "series: one line per paper, in the order of its first correction. Route 1's filter was not checked "
                    "row by row: 25 random notes were read and each names the paper's own numbers that show the "
                    'misprint; misprints whose note uses other words are missed, so the counts are a floor.',
            'series': series}},
})

# =================================================================================================================
# B. Values copied from an earlier paper without a word: an audit, a rule, a sweep of every pair of papers
C_PMID, ORIG = '12591933', '11694539'
cdrops = lines(C_PMID, ('drop',), '2026-10-14')
cids = sorted({f[3] for n, f in cdrops})
check('B: 24 values dropped from 12591933 on 14 Oct', len(cids) == 24)
crows = {}
for r in jl('rejected.jsonl', C_PMID.encode()):
    if r['row_id'] in cids:
        crows.setdefault(r['row_id'], r)                       # the first entry: the drop itself
check('B: all 24 in rejected.jsonl', len(crows) == 24)
orig_rows = [r for r in jl('catalog.jsonl', f'"{ORIG}"'.encode()) if str(r['pmid']) == ORIG]
orig_n = len(orig_rows)
LABEL = lambda s: (re.search(r'\b([ABC]\d+[A-Z]?)\b', s) or re.search('(.*)', s)).group(1)   # peptide A3, B74, A13R ...
MMP = lambda s: (re.search(r'MMP-?(\d+)', s) or re.search('(.*)', '')).group(1)
same_in_orig = []                         # each copied value against the earlier paper's own stored value
for r in crows.values():
    hits = [o for o in orig_rows if o['metric'] == r['metric'] and LABEL(o['substrate']) == LABEL(r['substrate'])
            and MMP(o['enzyme']) == MMP(r['enzyme']) and near(o['value'], r['value'], 1e-6)]
    same_in_orig.append(dict(metric=r['metric'], enzyme=r['enzyme'], peptide=LABEL(r['substrate']), value=r['value'],
                             unit=r['unit'], earlier_paper_same_value=bool(hits)))
first_drop = cdrops[0][1][0]
rule_b = commit('078ea59')
scan_c = commit('7a59890')
mins = (datetime.datetime.strptime(rule_b['time'], '%Y-%m-%d %H:%M') - datetime.datetime.strptime(first_drop, '%Y-%m-%d %H:%M')).seconds // 60
brenda_both = []
for rid, r in sorted(crows.items(), key=lambda kv: (kv[1]['metric'], kv[1]['value'])):
    later = [q for q in DB[(C_PMID, r['metric'])] if q['source'] == 'BRENDA' and near(q['value'], r['value'])]
    earlier = [q for q in DB[(ORIG, r['metric'])] if q['source'] == 'BRENDA' and near(q['value'], r['value'])]
    if later:
        brenda_both.append(dict(metric=r['metric'], substrate=r['substrate'], value=r['value'], unit=r['unit'],
                                brenda_under_12591933=True, brenda_under_11694539=bool(earlier)))
v_c = [d for d in json.load(open(P('work/old/12591933.verify.1794252840.json')))['verdicts']
       if d.get('metric') == 'kcat' and d.get('raw_value') == '622']
pair = [(n, f) for n, f in LOG if f[2] == 'drop' and 'pair scan' in '\t'.join(f[4:])]
pair_ids = {f[3]: f[1] for n, f in pair}
pair_rows = {}
for r in jl('rejected.jsonl'):
    if r['row_id'] in pair_ids:
        pair_rows.setdefault(r['row_id'], r)                   # the first entry: the drop itself (a later re-read can add one)
check('B: every pair-scan drop is in rejected.jsonl', len(pair_rows) == len(pair_ids))
by_src, listed = collections.Counter(), set()
per_paper = collections.defaultdict(lambda: [0, 0])          # pmid -> [values dropped, of them a database lists]
for rid, r in pair_rows.items():
    s = {q['source'] for q in DB[(str(r['pmid']), r['metric'])] if near(q['value'], r['value'])}
    by_src.update(s)
    per_paper[pair_ids[rid]][0] += 1
    if s:
        listed.add(rid)
        per_paper[pair_ids[rid]][1] += 1
FOLLOW = ('18563901', '22302521', '21087930', '15477086')
follow = {p: len({f[3] for n, f in LOG if f[1] == p and f[2] == 'drop' and re.search('reprint', '\t'.join(f[4:]), re.I)})
          for p in FOLLOW}
out['cases'].append({
    'id': 'B', 'title': 'Values copied from an earlier paper', 'found_by': 'an agent (an auditor)',
    'kind': "a wrong value kept (another paper's measurement counted as new)",
    'papers': {C_PMID: 'J Biol Chem 2003, MMP-2 E412D against wild-type MMP-2 and MMP-9 on six peptides',
               ORIG: 'J Biol Chem 2002, the same lab: the MMP-2 substrate profile (Table III)'},
    'steps': [
        {'step': 'read', 'paper': C_PMID, 'papers_read_so_far': read_so_far(FIRST_ADD[C_PMID]),
         'what': "The reader stored Table II's wild-type MMP-2 and MMP-9 columns with the mutant's, noting that the "
                 "wild-type preparations are 'not described here (method of ref. 23)'; the verifier confirmed them "
                 "cell by cell. CatLog had read the earlier paper the day before.",
         'quote': v_c[0]['reason'] if v_c else '',
         'files': ['work/old/12591933.read.1794252840.json (note)', 'work/old/12591933.verify.1794252840.json',
                   f"log.tsv (add {ORIG}, {FIRST_ADD[ORIG]}: {orig_n} values in catalog.jsonl)"]},
        {'step': 'found', 'who': 'auditors (agents)', 'paper': C_PMID, 'papers_read_so_far': read_so_far(first_drop),
         'what': f"Auditors found the wild-type columns identical, cell for cell, to {ORIG}'s Table III (the paper's "
                 "ref. 23; Table II's caption cites it for the peptides' selectivity and the MMP-9 assay, not as the "
                 'source of the numbers). 24 values dropped.',
         'files': [f'log.tsv:{cdrops[0][0]}-{cdrops[-1][0]} (drop and audit_drop lines)']},
        {'step': 'rule', 'papers_read_so_far': read_so_far(rule_b['time']), 'commit': rule_b,
         'minutes_after_first_drop': mins,
         'what': "Both agents' instructions: a mutant table's wild-type column can be an earlier paper's numbers "
                 "carried over silently; when the cited paper's text is on disk, compare the cells and skip a column "
                 "identical to that paper's table.",
         'files': [f"git show {rule_b['commit']} -- prompts/read.md prompts/verify.md"]},
        {'step': 'caught again', 'who': 'code lists the pairs, agents check them (a checker, a refuter, two judges on a '
                                        'disagreement)',
         'papers_read_so_far': read_so_far(pair[0][1][0]), 'commit': scan_c,
         'what': 'tools/reprint_pairs.py listed every catalogue paper sharing 3 or more specific printed cells with '
                 "another, or with an earlier paper's database values; every pair (296 papers) was checked cell by "
                 'cell against the earlier paper.',
         'files': ['work/reprint_sweep/HANDOFF.md', 'work/reprint_pairs_4plus_20261016.tsv', 'work/reprint_<PMID>.json',
                   f'log.tsv:{pair[0][0]}-{pair[-1][0]} ({len(pair)} drop lines naming the pair scan)']},
        {'step': 'databases', 'paper': f'{C_PMID}, {ORIG}',
         'what': f'BRENDA lists {len(brenda_both)} of the 24 copied values under {C_PMID}, each the same number it '
                 f'lists under {ORIG}. Of the {len(pair_ids)} values the sweep dropped, a database lists {len(listed)} '
                 'as the copying paper\'s own.',
         'files': ['sources/db_values.tsv']},
        {'step': 'since', 'what': 'Later audits found more copied rows and their papers were checked whole.',
         'files': ['CLAUDE.md, open item "Audit follow-up 2026-11-11"', 'log.tsv (drop lines)']}],
    'numbers': {
        'copied_values_12591933': collections.Counter(r['metric'] for r in crows.values()),
        'brenda_lists_under_both_papers': brenda_both,
        'copied_values_against_the_earlier_paper_in_catalog': same_in_orig,
        'copied_values_equal_to_the_earlier_papers_stored_value': sum(x['earlier_paper_same_value'] for x in same_in_orig),
        'sweep': {'papers_checked': 296, 'values_dropped': len(pair_ids), 'papers_with_values_dropped': len(set(pair_ids.values())),
                  'kept_after_refutation': 165, 'kept_unsure': 206, 'earlier_papers': 84,
                  'dropped_values_whose_original_is_in_the_catalogue': 689, 'dropped_values_whose_original_is_queued': 284,
                  'note': 'papers_checked, kept, earlier papers and originals from work/reprint_sweep/HANDOFF.md and '
                          'CLAUDE.md (2026-10-16); drops from log.tsv'},
        'earlier_copied_column_found_by_an_audit': {'pmid': '15618685', 'papers_read_so_far': read_so_far(
            next(f[0] for n, f in LOG if f[1] == '15618685' and f[2] == 'audit_drop'))},
        'sweep_values_a_database_lists_under_the_copying_paper': len(listed),
        'sweep_values_by_database': dict(by_src),
        'sweep_by_paper_values_dropped_and_listed_by_a_database': dict(sorted(per_paper.items(), key=lambda kv: -kv[1][0])),
        'sweep_papers_held_out': sorted(set(pair_ids.values()) & HOLD),
        'later_audit_follow_ups_values_dropped': follow},
})

# =================================================================================================================
# C. One printed line kept as two or three records: a reviewer's note, a rule agents built and tested
M = 'work/record_merge_20261111/'
v2, v5 = json.load(open(P(M + 'merged_sets_v2.json'))), json.load(open(P(M + 'merged_sets_v5_new.json')))


def tally(fn):
    d = json.load(open(P(M + fn)))
    c = collections.Counter(r.get('one_measurement') for p in d['papers'] for r in p['records'])
    return dict(checked=sum(c.values()), papers=len(d['papers']), one_measurement=c['yes'], not_one=c['no'], unsure=c['unsure'])


joins = v2 + v5
held = [j for j in joins if j['pmid'] in HOLD]
before_records = sum(len(j['parts']) if 'parts' in j else len(j['rows']) for j in joins)
# HUMAN_REVIEW.md ("the reviewer's doc"): the reviewer's cards 413, 531, 563 and 717, one in each of four papers; agents then
# counted the rows of those papers stored this way
REVIEWER_PAPERS = {'33621065': 5, '39897407': 4, '8055963': 6, '16431280': 60}
imp = sum(1 for ln in open(P('sources/implausible_as_printed.tsv'), encoding='utf-8')
          if not ln.startswith('#') and ln.split('\t')[1:2] == ['16431280'])
c1, c2 = commit('5c441ee'), commit('1d2a10f')
out['cases'].append({
    'id': 'C', 'title': 'One printed line kept as two or three records', 'found_by': 'a person (a reviewer)',
    'kind': 'record keeping (no value wrong; a record half empty, its kcat/Km not derivable)',
    'steps': [
        {'step': 'found', 'who': 'a reviewer (person)', 'when': 'the day the rule was written (HUMAN_REVIEW.md)',
         'what': "Checking records against their papers, a reviewer noted on four cards (one in each of four papers) that "
                 'one printed table row appeared as two or three records (a kcat-only and a Km-only record). Agents '
                 "found why: two reads had spelled the substrate or enzyme differently (for example 'Abz-AGGRGDGQ-EDDnp' "
                 "and 'Abz-A-G-G-R-G-D-G-Q-EDDnp'), or the grouping code had declined an unclear pairing. They counted "
                 'the rows stored this way in those papers; a scan put it at about 1.1% of records, in 135 papers.',
         'reviewer_cards': 4, 'rows_split_in_the_reviewer_papers': REVIEWER_PAPERS,
         'files': ['HUMAN_REVIEW.md ("the reviewer\'s doc", 2026-11-11)', 'human_review/correspondence/ (screenshot of the notes from a reviewer, 2026-11-11)',
                   M + 'HANDOFF.md']},
        {'step': 'rule tested', 'who': 'agents (25 paper checkers, an adversarial reviewer, then blind checkers)',
         'what': 'A first, loose rule joined 577 groups in 87 papers; checkers reading the papers judged 74 joins and '
                 'found 12 wrong (a kcat of one assay put with a Km of another). The rule was tightened until none of '
                 'the 12 joined; a fresh blind check of 60 joins found all 60 right.',
         'loose_rule_check': tally('check_results_v1.json'), 'strict_rule_fresh_check': tally('check_results_v2.json'),
         'files': [M + 'check_results_v1.json', M + 'check_results_v2.json', M + 'rule_review/']},
        {'step': 'rule', 'commit': c1, 'papers_read_so_far': read_so_far(c1['time']),
         'what': 'catlog.join_lines: the values of one printed line that spelling kept in '
         'separate records are joined into one record.', 'files': [f"git show {c1['commit']}", 'catlog.py join_lines']},
        {'step': 'caught again', 'commit': c2,
         'what': 'Refined for a paper that measures the same peptides with and without DNA (39897407): 38 more joins '
                 'in 9 papers, each checked against its paper.',
         'refined_rule_check': tally('check_results_v5.json'),
         'files': [M + 'merged_sets_v5_new.json', M + 'check_results_v5.json']},
        {'step': 'since', 'what': f'Joined across the catalogue. In the reviewer\'s 16431280, the 58 joined records got '
         f'a kcat/Km for the first time; those at or above 1e9 M-1 s-1 were checked by two blind agents and flagged as '
         f'implausible as printed ({imp} lines).', 'files': [M + 'merged_sets_v2.json', 'sources/implausible_as_printed.tsv']},
        {'step': 'databases', 'what': 'Not applicable: an error of CatLog\'s own record keeping.'}],
    'numbers': {
        'joins': len(joins), 'papers': len({j['pmid'] for j in joins}), 'values_joined': sum(len(j['rows']) for j in joins),
        'records_before': before_records, 'records_after': len(joins),
        'joins_by_size': dict(collections.Counter(len(j['rows']) for j in joins)),
        'joins_in_held_out_papers': len(held), 'held_out_papers': sorted({j['pmid'] for j in held}),
        'reviewer_papers_joins': {p: sum(1 for j in joins if j['pmid'] == p) for p in REVIEWER_PAPERS},
        'joins_by_paper': dict(collections.Counter(j['pmid'] for j in joins).most_common()),
        'checks': {'loose': tally('check_results_v1.json'), 'strict_fresh': tally('check_results_v2.json'),
                   'refined': tally('check_results_v5.json')},
        'note': "records_before counts v2's parts per join and, for the 38 refined joins (no parts listed), one record per value"},
})

# =================================================================================================================
# Runners-up (not picked; cases.md says why) and who first found each kind of error on CatLog's list
TAX = list(csv.DictReader(open(P('paper/figures/method_overview/v5/taxonomy.tsv'), newline=''), delimiter='\t'))
people = [dict(id=r['id'], kind=r['class'], route=r['found_route']) for r in TAX if r['found_route'] in ('reviewer', 'owner')]
bounds = collections.Counter(r.get('censored') for r in jl('bounds.jsonl'))
g270e = [r for r in jl('bounds.jsonl', b'0d100f0a377410de')]
check('runners-up: the G270E bound', len(g270e) == 1 and g270e[0]['censored'] == 'not_detected')
db_g270e = sorted({q['source'] for q in DB[('21257746', 'kcat')] if near(q['value'], 0.002)})
ra10 = next(r for r in TAX if r['id'] == 'RA10')
lim = collections.Counter()
lim_papers = collections.defaultdict(set)
for r in jl('catlog_wide.jsonl', b'"kcat_over_km_bound": "'):
    b, p = r.get('kcat_over_km_bound'), str(r['pubmed_id'])
    if not b or p in HOLD or not isinstance(r.get('kcat'), (int, float)) or not isinstance(r.get('km'), (int, float)) or not r['km']:
        continue
    calc = r['kcat'] / r['km']                                     # mM^-1 s^-1, as export would have calculated it
    m = re.match(r'\s*([<>])\s*([0-9.eE+-]+)', b)
    contra = bool(m) and ((m.group(1) == '<' and calc > float(m.group(2)) * 1.02) or (m.group(1) == '>' and calc < float(m.group(2)) / 1.02))
    contra = contra or b.startswith('not_detected')
    lim['records'] += 1
    lim['contradicted'] += contra
    lim_papers['records'].add(p)
add36 = [f for n, f in LOG if f[1] == '36756200' and f[2] in ('add', 'recover')]
rule_e = commit('c005e33')
out['runners_up'] = {
    'not_detected_or_limit': {'found': 'outside review (agent), taxonomy RA10', 'before': ra10['values'],
                              'rule': commit('47eafb8'), 'rule_papers_read_so_far': read_so_far(commit('47eafb8')['time']),
                              'case_21257746_bound': {k: g270e[0].get(k) for k in ('enzyme', 'variant', 'metric', 'censored', 'limit')},
                              'case_21257746_databases_listing_0.002': db_g270e,
                              'bounds_now': dict(bounds), 'bounds_now_total': sum(bounds.values())},
    'calculated_beside_a_printed_limit': {'found': 'the owner, on the website (10390216, aztreonam); taxonomy CU7',
                                          'rule': commit('4767cad'), 'records_with_a_limit_and_kcat_and_km': lim['records'],
                                          'papers': len(lim_papers['records']), 'calculation_would_contradict_the_limit': lim['contradicted']},
    'implausible_scale_kept': {'paper': '36756200', 'log': ['\t'.join(f[:6]) for f in add36], 'rule': rule_e,
                               'later_paper_19810726_added': FIRST_ADD.get('19810726'),
                               'note': '19810726 was added one minute after the rule commit: which instructions its '
                                       'agents read needs checking before it is called caught again'}}
out['people_found_kinds'] = {'of_kinds': len(TAX), 'people_first_found': people}

# The judgements cases.md argues for (not computed; kept here so a builder can read them with the numbers)
out['selection_rule'] = ('a first find in one paper by a named finder, with its file; a written rule with its commit; '
                         "that rule acting on a different paper, shown by that paper's own work file or log line; what "
                         'the databases list (sources/db_values.tsv); numbers a panel can draw and a count of the reach')
out['picks'] = [
    {'id': 'A', 'rank': 1, 'holds_all_five': True, 'panel_without_legend': 'yes, for the values: rows As printed / '
     'Databases / CatLog on a log axis, one block per paper; the order of steps as a short row of marks coloured by who '
     "acts; the legend says what the rule says and who found it"},
    {'id': 'B', 'rank': 2, 'holds_all_five': True, 'panel_without_legend': 'mostly: the 24 copied values on Earlier '
     'paper against Later paper sit on the diagonal; the sweep as one dot per paper; how pairs were found and checked '
     'goes to the legend'},
    {'id': 'C', 'rank': 3, 'holds_all_five': False, 'missing': 'no database step; no value was wrong',
     'panel_without_legend': "no: what a split record is needs the box's words"}]
out['supports'] = 'yes'
out['caveats'] = [
    'The value errors (A, B) were found by agents; the person-found case (C) changed records, not values. Of the 85 '
    'kinds on the list to 2 November, people first found 6, none a printed value stored wrong.',
    "A's before and after counts are not a controlled comparison; some verifiers fixed misprinted headers before the rule.",
    "A's reach filter is a floor, not checked row by row (25 notes read).",
    "B's sweep counts include one held-out paper (22574886, 11 values) read before the lock; C's joins include 3 in "
    'one (23071703).',
    'Database matches for the reach counts are by paper, constant and value within 2%.']

with open(os.path.join(HERE, 'cases.json'), 'w', encoding='utf-8') as fh:
    json.dump(out, fh, indent=1, ensure_ascii=False, default=dict)
    fh.write('\n')
for c in out['cases']:
    print(c['id'], c['title'], json.dumps({k: v for k, v in c['numbers'].items() if not isinstance(v, (list, dict))}))
print('A reach', json.dumps({k: v for k, v in out['cases'][0]['numbers']['reach'].items() if k != 'series'}))
print('B', json.dumps({k: out['cases'][1]['numbers'][k] for k in ('sweep', 'sweep_values_a_database_lists_under_the_copying_paper', 'sweep_values_by_database', 'later_audit_follow_ups_values_dropped')}))
print('C', json.dumps(out['cases'][2]['numbers']['checks']), out['cases'][2]['numbers']['reviewer_papers_joins'])
