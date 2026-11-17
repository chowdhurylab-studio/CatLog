"""The numbers of Fig. 2, read from the result files and asserted (used by build_fig2.py and build_fig2_lean.py).

Every number a Fig. 2 builder draws is read here from a result file under paper/evidence/ (read only) and asserted
against the literal the manuscript prints (writing/manuscript/results.md, results/T1_tests.md) or, for the count over
both tests, the literal the accuracy check reports (paper/evidence/accuracy_check_20261114/stats.md). Importing this
module stops when one differs. DRAWN lists each number with its source; a builder writes it out.
"""
import collections
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

# ---------------------------------------------------------------------------------------------------------------
# Result files (read only)
SRC = {
    'r2': 'paper/evidence/random_papers_20261104/r2_numbers.json',
    'rand': 'paper/evidence/random_papers_20261104/full_record/results.json',
    'rand_first': 'paper/evidence/random_papers_20261104/full_record/first_on_same_papers/results.json',
    'locked': 'paper/evidence/locked_test_20261109/result/results.json',
    'traps': 'paper/evidence/hard_cases_20261102/summary.json',
}
D = {k: json.loads((ROOT / p).read_text()) for k, p in SRC.items()}
# The accuracy check of 14 November 2026 (both tests together; its report stats.md, verified in verify.md there)
STATS = 'paper/evidence/accuracy_check_20261114/stats.json'
REPORT = 'paper/evidence/accuracy_check_20261114/stats.md gives'
ST = json.loads((ROOT / STATS).read_text())
for key, name in (('rand', 'random'), ('locked', 'locked')):    # it was computed from the result files read here
    if hashlib.sha256((ROOT / SRC[key]).read_bytes()).hexdigest() != ST['inputs'][name]['sha256']:
        raise SystemExit(f'Fig. 2: {STATS} was not computed from {SRC[key]} as it is now')
DRAWN = []  # (panel, what, value as drawn, source)


def drawn(panel, what, value, source, expect=None, where='the manuscript prints'):
    """Record a drawn number; stop when it is not its literal (expect): the number the manuscript prints, or the one
    another report gives (where says whose)."""
    if expect is not None and value != expect:
        raise SystemExit(f'Fig. 2 {panel}: {what} is {value!r} in {source}; {where} {expect!r}')
    DRAWN.append((panel, what, value, source))
    return value


def same(what, a, b):
    if a != b:
        raise SystemExit(f'Fig. 2: {what}: {a!r} != {b!r}')


# --- a, the random test (147 papers), judged with full records; the first judging restated on the same papers
RF, R1, N = D['rand'], D['rand_first'], D['r2']
F = N['full_record']
A = {'papers': drawn('a', 'papers analysed', RF['papers_used'], SRC['rand'] + '#papers_used', 147)}
same('a papers, r2_numbers', F['papers'], A['papers'])
same('a first judging papers', R1['papers_used'], A['papers'])
for key, exp in (('plain', dict(values=4530, wrong=42, rate=9.31, papers=5, first_rate=13.91, first_wrong=63, first_papers=11)),
                 ('catlog', dict(values=4390, wrong=6, rate=1.37, papers=1, first_rate=3.42, first_wrong=15, first_papers=6))):
    s, s1 = RF['per_source'][key], R1['per_source'][key]
    src, src1 = f"{SRC['rand']}#per_source.{key}", f"{SRC['rand_first']}#per_source.{key}"
    a = {'values': drawn('a', f'{key} values stored', s['values'], src + '.values', exp['values']),
         'wrong': drawn('a', f'{key} wrong values', s['wrong'], src + '.wrong', exp['wrong']),
         'rate': drawn('a', f'{key} wrong per 1,000', s['wrong_per_1000'], src + '.wrong_per_1000', exp['rate']),
         'papers': drawn('a', f'{key} papers with a wrong value', s['papers_with_a_wrong_value'],
                         src + '.papers_with_a_wrong_value', exp['papers']),
         'first_rate': drawn('a', f'{key} first judging, wrong per 1,000', s1['wrong_per_1000'], src1 + '.wrong_per_1000',
                             exp['first_rate']),
         'first_wrong': drawn('a', f'{key} first judging, wrong values', s1['wrong'], src1 + '.wrong', exp['first_wrong']),
         'first_papers': drawn('a', f'{key} first judging, papers with a wrong value', s1['papers_with_a_wrong_value'],
                               src1 + '.papers_with_a_wrong_value', exp['first_papers'])}
    # intervals: paper-level bootstrap, to one decimal as the report prints them; none under five papers with a wrong value
    a['ci'] = [round(s['bootstrap']['per_1000_lo'], 1), round(s['bootstrap']['per_1000_hi'], 1)] if a['papers'] >= 5 else None
    a['first_ci'] = [round(s1['bootstrap']['per_1000_lo'], 1), round(s1['bootstrap']['per_1000_hi'], 1)]
    same(f'a {key} values, r2_numbers', F['values'][key], a['values'])
    same(f'a {key} wrong, r2_numbers', F['wrong'][key], a['wrong'])
    same(f'a {key} rate, r2_numbers', F['wrong_per_1000'][key][0], a['rate'])
    same(f'a {key} first rate, r2_numbers', F['first_on_same_papers'][key]['wrong_per_1000'][0], a['first_rate'])
    same(f'a {key} first interval, r2_numbers', F['first_on_same_papers'][key]['wrong_per_1000'][1:], a['first_ci'])
    same(f'a {key} first wrong, r2_numbers', F['first_on_same_papers'][key]['wrong'], a['first_wrong'])
    same(f'a {key} first papers, r2_numbers', F['first_on_same_papers'][key]['papers_with_a_wrong_value'], a['first_papers'])
    if a['ci']:
        same(f'a {key} interval, r2_numbers', F['wrong_per_1000'][key][1:], a['ci'])
    A[key] = a
drawn('a', 'plain interval, wrong per 1,000', A['plain']['ci'], SRC['rand'] + '#per_source.plain.bootstrap', [0.6, 23.7])
drawn('a', 'plain first judging interval', A['plain']['first_ci'], SRC['rand_first'] + '#per_source.plain.bootstrap', [3.8, 28.9])
drawn('a', 'catlog first judging interval', A['catlog']['first_ci'], SRC['rand_first'] + '#per_source.catlog.bootstrap', [0.7, 7.3])
same('a catlog: no interval under five papers', A['catlog']['ci'], None)
A['diff'] = drawn('a', 'plain minus CatLog, wrong per 1,000 (95% interval)',
                  [round(RF['plain_minus_catlog']['per_1000_lo'], 1), round(RF['plain_minus_catlog']['per_1000_hi'], 1)],
                  SRC['rand'] + '#plain_minus_catlog', [-1.7, 22.5])
A['catlog_lacked'] = drawn('a', 'supported values only the plain reading stored', len(RF['misses']['catlog']),
                           SRC['rand'] + '#misses.catlog', 110)
A['plain_lacked'] = drawn('a', 'supported values only CatLog stored', len(RF['misses']['plain']),
                          SRC['rand'] + '#misses.plain', 7)
same('a misses, per_source', (RF['per_source']['catlog']['misses_supported_values_only_the_other_stored'],
                              RF['per_source']['plain']['misses_supported_values_only_the_other_stored']), (110, 7))

# --- b, the locked test as registered (83 held-out papers)
L = D['locked']
B = {'papers': drawn('b', 'papers analysed', L['papers_used'], SRC['locked'] + '#papers_used', 83)}
for key, exp in (('plain', dict(values=1473, wrong=15, rate=10.18, papers=4)),
                 ('catlog', dict(values=1400, wrong=34, rate=24.29, papers=2))):
    s, src = L['per_source'][key], f"{SRC['locked']}#per_source.{key}"
    B[key] = {'values': drawn('b', f'{key} values stored', s['values'], src + '.values', exp['values']),
              'wrong': drawn('b', f'{key} wrong values', s['wrong'], src + '.wrong', exp['wrong']),
              'rate': drawn('b', f'{key} wrong per 1,000', s['wrong_per_1000'], src + '.wrong_per_1000', exp['rate']),
              'papers': drawn('b', f'{key} papers with a wrong value', s['papers_with_a_wrong_value'],
                              src + '.papers_with_a_wrong_value', exp['papers'])}
    if B[key]['papers'] >= 5:
        raise SystemExit('Fig. 2 b: a side has five papers with a wrong value: the report then gives an interval; draw it')
B['diff'] = drawn('b', 'plain minus CatLog, wrong per 1,000 (95% interval)',
                  [round(L['plain_minus_catlog']['per_1000_lo'], 1), round(L['plain_minus_catlog']['per_1000_hi'], 1)],
                  SRC['locked'] + '#plain_minus_catlog', [-63.2, 17.2])
B['catlog_lacked'] = drawn('b', 'supported values only the plain reading stored', len(L['misses']['catlog']),
                           SRC['locked'] + '#misses.catlog', 87)
B['plain_lacked'] = drawn('b', 'supported values only CatLog stored', len(L['misses']['plain']),
                          SRC['locked'] + '#misses.plain', 1)
same('b misses, per_source', (L['per_source']['catlog']['misses_supported_values_only_the_other_stored'],
                              L['per_source']['plain']['misses_supported_values_only_the_other_stored']), (87, 1))
# the ticks: every wrong value of the registered result, by side, verdict and paper
ticks = collections.defaultdict(collections.Counter)
for w in L['wrong']:
    ticks[(w['source'], w['verdict'])][w['pmid']] += 1
same('b verdict kinds', sorted(ticks), [('catlog', 'wrong_scale'), ('plain', 'not_measured_here'), ('plain', 'wrong_metric')])
same('b kinds, per_source', (L['per_source']['plain']['kinds'], L['per_source']['catlog']['kinds']),
     ({'wrong_metric': 9, 'not_measured_here': 6}, {'wrong_scale': 34}))
STRIP = []  # (side, verdict, [values per paper, most first])
for side, verdict, exp in (('plain', 'wrong_metric', [5, 2, 2]), ('plain', 'not_measured_here', [6]),
                           ('catlog', 'wrong_scale', [29, 5])):
    groups = sorted(ticks[(side, verdict)].values(), reverse=True)
    drawn('b strip', f'{side} {verdict}: wrong values per paper', groups, SRC['locked'] + '#wrong (source, verdict, pmid)', exp)
    STRIP.append((side, verdict, groups))
same('b strip, plain ticks', sum(sum(g) for s, _, g in STRIP if s == 'plain'), B['plain']['wrong'])
same('b strip, CatLog ticks', sum(sum(g) for s, _, g in STRIP if s == 'catlog'), B['catlog']['wrong'])
same('b strip, plain papers', sum(len(g) for s, _, g in STRIP if s == 'plain'), B['plain']['papers'])
same('b strip, CatLog papers', sum(len(g) for s, _, g in STRIP if s == 'catlog'), B['catlog']['papers'])
# every one of the 9 is a Hill-type or half-saturation constant: 8 stored as Km, 1 a kcat over such a constant stored
# as kcat/Km (result/README.md "What the wrong values are"); the label says "taken as Km", which holds for all nine
same('b strip, the nine by constant', collections.Counter(w['shown']['metric'] for w in L['wrong']
                                                          if (w['source'], w['verdict']) == ('plain', 'wrong_metric')),
     collections.Counter({'Km': 8, 'kcat/Km': 1}))
# Found after the result: CatLog's unit changes. A wrong value of CatLog's is a unit change when its verdict is
# wrong_scale and the plain reading stored, for the same paper and constant, a supported value that CatLog lacked at
# 1,000 or 60 times it: the printed form of the same cell, whose unit factor CatLog took off. Each printed form
# pairs with one value. Any other wrong value of CatLog's is not a unit change and stays wrong in every count.
UNIT_FACTORS = (1000, 60)


def unit_changes_of(wrong, misses):
    """Among CatLog's wrong values (wrong) and the supported values only the plain reading stored (misses): the unit
    changes as {claim: paper}, the claims of their printed forms, per paper the wrong values that are not unit
    changes, and per (paper, constant) the values CatLog lacked that are the printed form of none."""
    lacked = collections.defaultdict(list)
    for m in misses:
        lacked[(m['pmid'], m['shown']['metric'])].append((m['shown']['value'], m['claim_id']))
    changes, forms, others = {}, set(), collections.Counter()
    for w in sorted(wrong, key=lambda w: (w['pmid'], w['shown']['metric'], w['shown']['value'])):
        key = (w['pmid'], w['shown']['metric'])
        partner = next((c for c in sorted(lacked[key]) if w['verdict'] == 'wrong_scale'
                        and any(abs(c[0] / w['shown']['value'] / factor - 1) < 1e-3 for factor in UNIT_FACTORS)), None)
        if partner is None:
            others[w['pmid']] += 1
            continue
        lacked[key].remove(partner)
        changes[w['claim_id']] = w['pmid']
        forms.add(partner[1])
    return changes, forms, others, lacked


CATLOG_WRONG = [w for w in L['wrong'] if w['source'] == 'catlog']
unit_changes, printed_forms, not_unit_changes, lacked = unit_changes_of(CATLOG_WRONG, L['misses']['catlog'])
# the rule can fail: with another verdict, or without its printed form, a value is no unit change and its paper stays wrong
probe = CATLOG_WRONG[0]
same('b strip: a value of another verdict is not a unit change',
     unit_changes_of([dict(probe, verdict='wrong_metric')] + CATLOG_WRONG[1:], L['misses']['catlog'])[2],
     collections.Counter({probe['pmid']: 1}))
same('b strip: a value without a printed form is not a unit change',
     sum(unit_changes_of(CATLOG_WRONG, [m for m in L['misses']['catlog'] if m['pmid'] != probe['pmid']])[2].values()),
     sum(1 for w in CATLOG_WRONG if w['pmid'] == probe['pmid']))
listed = ST['as_printed_34']['pairs']        # the same values, as the accuracy check lists them one by one
same('b strip: the unit changes are the values the accuracy check lists', set(unit_changes), {q['catlog_claim'] for q in listed})
same('b strip: their printed forms are the values the accuracy check lists', printed_forms, {q['plain_claim'] for q in listed})
B['as_printed'] = drawn('b strip', 'of the values CatLog lacked, the printed forms of those it stored with a changed unit',
                        len(printed_forms), SRC['locked'] + '#misses.catlog paired with #wrong (catlog)', 34)
B['never_stored'] = drawn('b strip (not drawn)', 'of the values CatLog lacked, those it never stored',
                          B['catlog_lacked'] - B['as_printed'], SRC['locked'] + '#misses.catlog', 53)
same('b strip: every wrong value of CatLog is a unit change, as its row of ticks is labelled',
     (len(unit_changes), sum(not_unit_changes.values())), (B['catlog']['wrong'], 0))
same('b strip, papers with values never stored (results.md: 16)', len({pmid for (pmid, _), left in lacked.items() if left}), 16)

# --- the tests of a and b together (the owner, 14 November 2026: "Yes, add it", one line under the panels, labelled
# as put together afterwards, nothing else changed). The pooling and the two ways of counting were chosen after both
# results were in. Papers with a wrong value: the plain reading; CatLog as the tests judged its values; CatLog with
# its 34 unit changes judged by the papers' own numbers (right: agents' checks on the page images, no person's).
same('both tests: every analysed paper has its counts', (len(RF['per_paper']), len(L['per_paper'])), (A['papers'], B['papers']))
same('both tests: no paper is in both tests', set(RF['per_paper']) & set(L['per_paper']), set())
WRONG_PAPERS = {side: {test: {pmid for pmid, v in res['per_paper'].items() if v[side]['wrong'] > 0}
                       for test, res in (('random', RF), ('locked', L))} for side in ('plain', 'catlog')}
for side in ('plain', 'catlog'):
    same(f'both tests: {side} papers with a wrong value, as each panel draws them',
         (len(WRONG_PAPERS[side]['random']), len(WRONG_PAPERS[side]['locked'])), (A[side]['papers'], B[side]['papers']))
for test in ('random', 'locked'):       # so every paper with a wrong value has it on one side only
    same(f'both tests: no paper of the {test} test has a wrong value on both sides',
         WRONG_PAPERS['plain'][test] & WRONG_PAPERS['catlog'][test], set())
same('both tests: the unit changes are in papers of the locked test', set(unit_changes.values()) <= WRONG_PAPERS['catlog']['locked'], True)
still_wrong = {pmid for pmid in WRONG_PAPERS['catlog']['locked'] if not_unit_changes[pmid]}   # a wrong value of another kind
POOLED = {'papers': A['papers'] + B['papers'],
          'plain': sorted(WRONG_PAPERS['plain']['random'] | WRONG_PAPERS['plain']['locked']),
          'catlog': sorted(WRONG_PAPERS['catlog']['random'] | WRONG_PAPERS['catlog']['locked']),
          'catlog_changes_right': sorted(WRONG_PAPERS['catlog']['random'] | still_wrong)}
PW = ST['papers_with_a_wrong_value']
for way, key in (('as_printed', 'catlog'), ('unit_changes_right', 'catlog_changes_right')):
    pooled = PW[way]['pooled']
    same(f'both tests, {way}: papers, {STATS}', pooled['papers'], POOLED['papers'])
    same(f'both tests, {way}: the plain reading\'s papers with a wrong value, {STATS}', sorted(pooled['plain']['papers']), POOLED['plain'])
    same(f'both tests, {way}: CatLog\'s papers with a wrong value, {STATS}', sorted(pooled['catlog']['papers']), POOLED[key])
    same(f'both tests, {way}: counts, {STATS}', (pooled['plain']['papers_with_a_wrong_value'], pooled['catlog']['papers_with_a_wrong_value']),
         (len(POOLED['plain']), len(POOLED[key])))


def sign_test(a, b):
    """Exact two-sided sign test: a papers erred on one side only, b on the other only."""
    n, k = a + b, min(a, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


BOTH = {'papers': drawn('both tests', 'papers of both tests together', POOLED['papers'],
                        STATS + '#papers_with_a_wrong_value.as_printed.pooled.papers', 230, REPORT),
        'plain': drawn('both tests', 'papers with a wrong value, the plain reading', len(POOLED['plain']),
                       STATS + '#papers_with_a_wrong_value.as_printed.pooled.plain', 9, REPORT),
        'catlog': drawn('both tests', 'papers with a wrong value, CatLog as judged in the tests', len(POOLED['catlog']),
                        STATS + '#papers_with_a_wrong_value.as_printed.pooled.catlog', 3, REPORT),
        'catlog_changes_right': drawn('both tests', "papers with a wrong value, CatLog with its 34 unit changes judged by the papers' own numbers",
                                      len(POOLED['catlog_changes_right']),
                                      STATS + '#papers_with_a_wrong_value.unit_changes_right.pooled.catlog', 1, REPORT)}
P_BOTH = {}                                  # the exact sign test of each count, to two figures as the text gives it
for way, key, literal in (('as_printed', 'catlog', '0.15'), ('unit_changes_right', 'catlog_changes_right', '0.021')):
    p_here = sign_test(BOTH['plain'], BOTH[key])
    if abs(p_here - ST['sign_test'][way]['pooled']['p']) > 1e-12:
        raise SystemExit(f"Fig. 2 both tests: exact sign test {way}: {p_here!r} here, {ST['sign_test'][way]['pooled']['p']!r} in {STATS}")
    P_BOTH[key] = drawn('both tests', f"exact sign test, two-sided, {BOTH['plain']} papers against {BOTH[key]}: p ({p_here:.3g} to three figures)",
                        f'{p_here:.2g}', STATS + f'#sign_test.{way}.pooled.p', literal,
                        'paper/evidence/locked_test_20261109/FOR_WRITING.md (How to state the accuracy claim) gives')

# --- c, the trap papers: the 53 the plain model read, by kind of trap
READ = ('done', 'incomplete', 'needs_supplement')  # CatLog has read the paper (hard_cases summary.py)
rows = [r for r in D['traps'] if r['model'] == 'Opus 5.5']
C_PAPERS = drawn('c', 'trap papers', len(rows), SRC['traps'] + ' (rows read by Opus 5.5)', 53)
KIND = {}
for r in rows:
    k = KIND.setdefault(r['class_id'], dict(n=0, plain=0, read=0, reader=0, catalogue=0))
    k['n'] += 1
    k['plain'] += bool(r['fell_in'])
    if r['catlog_status'] in READ:
        k['read'] += 1
        k['reader'] += bool(r['catlog_first_fell_in'])
        k['catalogue'] += r['catlog_trap'] > 0
EXPECT_C = {  # paper/evidence/hard_cases_20261102/summary.md: papers, plain, CatLog's reader (of read), catalogue (of read)
    'RA3': (6, 6, 6, 1, 6), 'RA1': (7, 6, 4, 1, 7), 'PP2': (5, 5, 5, 0, 5), 'PP7': (2, 2, 2, 0, 2), 'PP3': (4, 4, 3, 1, 4),
    'PP4': (5, 5, 5, 4, 5), 'PP1': (6, 3, 5, 0, 6), 'RA4': (5, 0, 5, 0, 5), 'IP11': (3, 1, 1, 1, 3), 'TL1': (2, 0, 0, 0, 2),
    'TL2': (4, 0, 0, 0, 2), 'TL4': (4, 0, 0, 0, 4)}
same('c kinds', sorted(KIND), sorted(EXPECT_C))
for code, k in KIND.items():
    drawn('c', f'{code}: papers, plain fell in, reader fell in, catalogue holds, of papers CatLog read',
          (k['n'], k['plain'], k['reader'], k['catalogue'], k['read']), SRC['traps'] + f' (class_id {code})', EXPECT_C[code])
    hk = N['hard_cases_by_kind'][code]
    same(f'c {code}, r2_numbers', (hk['papers'], hk['plain'], hk['catlog_first_read'], hk['catlog_catalogue']),
         (k['n'], [k['plain'], k['n']], [k['reader'], k['read']], [k['catalogue'], k['read']]))
same('c totals (results.md: 32 of 53; 36 and 8 of 51)',
     (sum(k['plain'] for k in KIND.values()), sum(k['reader'] for k in KIND.values()),
      sum(k['catalogue'] for k in KIND.values()), sum(k['read'] for k in KIND.values())), (32, 36, 8, 51))

# --- for the versions the owner picks from (build_fig2_options.py): the same results per paper; and per group of
# traps, kept for the trap papers' own display (they left Fig. 2 on 14 November: Fig. 4 and Extended Data)
# Every paper with a wrong value in either test: its side, how many wrong values, their verdict, and for CatLog how
# many of them are unit changes (the 34 of the locked test, above).
PAPERS_WRONG = []
for test, res in (('random', RF), ('locked', L)):
    per = collections.defaultdict(collections.Counter)
    for w in res['wrong']:
        per[(w['source'], w['pmid'])][w['verdict']] += 1
    for (side, pmid), verdicts in sorted(per.items()):
        same(f'{test} test, {side}, {pmid}: its wrong values are of one kind', len(verdicts), 1)
        same(f'{test} test, {side}, {pmid}: wrong values', sum(verdicts.values()), res['per_paper'][pmid][side]['wrong'])
        PAPERS_WRONG.append({'test': test, 'side': side, 'pmid': pmid, 'wrong': sum(verdicts.values()), 'verdict': next(iter(verdicts)),
                             'unit_changes': sum(1 for paper in unit_changes.values() if paper == pmid) if (test, side) == ('locked', 'catlog') else 0})


def papers_wrong(side, verdict=None, unit_change=None):
    """Wrong values per paper, most first: of one side, of one verdict, with or without unit changes."""
    return sorted((q['wrong'] for q in PAPERS_WRONG if q['side'] == side and (verdict is None or q['verdict'] == verdict)
                   and (unit_change is None or bool(q['unit_changes']) == unit_change)), reverse=True)


same('both tests, the plain reading: wrong values per paper credited to earlier work', papers_wrong('plain', 'not_measured_here'), [27, 6, 2])
same('both tests, the plain reading: wrong values per paper that are another constant', papers_wrong('plain', 'wrong_metric'), [8, 5, 4, 2, 2, 1])
same('both tests, CatLog: wrong values per paper, unit changes', papers_wrong('catlog', 'wrong_scale', True), [29, 5])
same('both tests, CatLog: wrong values per paper, not unit changes', papers_wrong('catlog', 'wrong_scale', False), [6])
same('both tests: papers and wrong values, as the lines on both tests give them',
     (len(papers_wrong('plain')), sum(papers_wrong('plain')), len(papers_wrong('catlog')), sum(papers_wrong('catlog')),
      len(papers_wrong('catlog', unit_change=False))),
     (BOTH['plain'], A['plain']['wrong'] + B['plain']['wrong'], BOTH['catlog'], A['catlog']['wrong'] + B['catlog']['wrong'],
      BOTH['catlog_changes_right']))
same('both tests: a paper\'s unit changes are all of its wrong values', [q for q in PAPERS_WRONG if q['unit_changes'] not in (0, q['wrong'])], [])

# The trap papers by group of trap (the groups of hard_cases_20261102/summary.py): what a number is, how it is
# printed, and the two kinds in neither group.
TRAP_GROUPS = {'number': ('RA3', 'RA1', 'PP2', 'PP7', 'PP3', 'PP4'), 'print': ('TL1', 'TL2', 'TL4', 'RA4'), 'other': ('PP1', 'IP11')}
same('trap groups hold every kind once', sorted(c for codes in TRAP_GROUPS.values() for c in codes), sorted(KIND))
TRAPS = {g: {f: sum(KIND[c][f] for c in codes) for f in ('n', 'plain', 'read', 'reader', 'catalogue')} for g, codes in TRAP_GROUPS.items()}
TRAPS['all'] = {f: sum(t[f] for t in TRAPS.values()) for f in ('n', 'plain', 'read', 'reader', 'catalogue')}
same('trap papers by group: papers, plain fell in, papers CatLog read, reader fell in, catalogue holds',
     {g: tuple(t.values()) for g, t in TRAPS.items()},
     {'number': (29, 28, 29, 25, 7), 'print': (15, 0, 13, 5, 0), 'other': (9, 4, 9, 6, 1), 'all': (53, 32, 51, 36, 8)})
HC = N['hard_cases']     # the same totals in r2_numbers.json (summary.md of the trap papers)
same('trap papers by group, r2_numbers', (HC['judgment_traps'], HC['reading_traps'], HC['fell_in'], HC['catlog_first_read_fell_in'], HC['catlog_papers_with_trap']),
     ([TRAPS['number']['plain'], TRAPS['number']['n']], [TRAPS['print']['plain'], TRAPS['print']['n']],
      [TRAPS['all']['plain'], TRAPS['all']['n']], [TRAPS['all']['reader'], TRAPS['all']['read']], [TRAPS['all']['catalogue'], TRAPS['all']['read']]))
