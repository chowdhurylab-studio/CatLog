#!/usr/bin/env python3
"""Trap papers, paper by paper, on one basis: the plain reading by the same model (Opus 5.5), CatLog's first reading
of each paper (its reader alone, with the rules of its day), the paper read again by CatLog as frozen on 9 November
2026 (its reader alone, then reader + verifier + code), and the catalogue after its later checks.

One basis: every reading is scored here, at build time, by the same code on the same checked keys and the same cells
(score_hard.cells_of and score_hard.score_cell in paper/evidence/hard_cases_20261102/). CatLog's readings are converted
by the same code (score_catlog_first.converted, i.e. CatLog's tools/units.py, byte-identical in the main folder, the
reading kit and the frozen copy); the plain reading keeps the catalogue-unit values it wrote itself, as in the test.
A cell only an agent can decide ('review') counts as not fallen in, as in today/today_summary.md; every set also gives
the count with a 'review' cell counted as fallen in. Each recomputed verdict is compared with the verdict on file, and
every difference is printed and kept in totals.json.

  python3 -I -B build_traps.py      writes traps.csv, cells.csv and totals.json beside this file (nothing else)

Reads only: the hard-case evidence folder; CatLog's work files of these papers (work/, work/old/), catalog.jsonl,
rejected.jsonl, papers.tsv, sources/provenance_backfill.tsv, the failure list (paper/figures/method_overview/v5/
taxonomy.tsv) and the frozen tag's files (git show); in <the kit folder> the plain reading's output files
and the frozen run's papers.tsv, work files and catalog.jsonl. Never texts/ or papers/, and no paper of
sources/holdout_locked.txt (checked below)."""
import collections, csv, datetime, json, math, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = Path('<the CatLog folder>')
EVD = MAIN / 'paper' / 'evidence' / 'hard_cases_20261102'
TAG = 'catlog-freeze-20261109'
sys.path[:0] = [str(EVD), str(EVD / 'today')]
import score_catlog_first as F  # noqa: E402  (kit import paths; converted(), first_read())
import score_hard as SH  # noqa: E402  (cells_of(), score_cell())
import score_today as T  # noqa: E402  (named_papers(), kept_run(): the frozen run's files)
import score_w1 as SW  # noqa: E402  (arm_values(): the plain reading's values)
import common_w1 as W  # noqa: E402

KIND = {'RA3': 'partial per-product constants', 'RA1': 'a constant that is not kcat or Km (Hill, Adair, K0.5)',
        'PP2': "an earlier paper's values reprinted", 'PP7': 'values a corrigendum or retraction withdrew',
        'PP3': "a row printed under another row's label", 'PP4': "a lone cell's slipped digits",
        'PP1': 'misprinted unit or exponent in a header', 'IP11': 'the measured variant',
        'RA4': 'a unit, prefix or multiplier header', 'TL1': 'µ drawn as m in the text layer',
        'TL2': '± drawn as a digit in the text layer', 'TL4': 'stray control characters in a number'}
ORDER = ['RA3', 'RA1', 'PP2', 'PP7', 'PP3', 'PP4', 'PP1', 'IP11', 'RA4', 'TL1', 'TL2', 'TL4']
# internal key -> the name used in traps.csv, cells.csv and totals.json
NAME = {'plain': 'plain_reading', 'first': 'first_reading', 'frozen_reader': 'frozen_reader_alone',
        'frozen_pass': 'frozen_with_verifier_and_code', 'catalogue': 'catalogue_now'}
WORDS = {'plain_reading': 'one plain reading of the paper by Opus 5.5 (the hard-case test, run hard, prompt A0)',
         'first_reading': "CatLog's first reading of the paper: its reader alone, with the rules of its day (the earliest "
                          'work file with kcat/Km rows; only readings made before the freeze)',
         'frozen_reader_alone': 'the paper read again by CatLog as frozen on 9 November 2026: its reader alone',
         'frozen_with_verifier_and_code': 'the same reading again: the rows its add kept (reader, independent verifier, '
                                          'verifier of missed values, code conversion and code checks; nothing after)',
         'catalogue_now': "CatLog's catalogue at build time (catalog.jsonl), after its later checks (audits, sweeps, "
                          'database checks, re-reads)',
         'catalogue_scored_4nov': 'the catalogue as scored by code for the first trap test (catlog_scores.json)'}
READ = ('done', 'incomplete', 'needs_supplement')  # CatLog has read the paper (summary.py)
FREEZE = datetime.datetime.fromisoformat(
    subprocess.run(['git', '-C', str(MAIN), 'log', '-1', '--format=%cI', TAG], capture_output=True, text=True,
                   check=True).stdout.strip())


def yn(x):
    return '' if x is None else ('yes' if x else 'no')


def tally(verdicts):
    c = collections.Counter(verdicts)
    return {'trap': c['trap'], 'review': c['review'], 'right': c['right'], 'other': c['other'], 'missing': c['missing'],
            'fell_in': c['trap'] > 0, 'fell_in_if_review': (c['trap'] + c['review']) > 0}


def score(cells, vals, ident):
    return [SH.score_cell(c, vals, ident)[0] for c in cells]


def exact_mcnemar(b, c):
    """Exact McNemar test (a sign test on the discordant pairs): the two-sided p, and the one-sided p for b > c."""
    n = b + c
    if n == 0:
        return 1.0, 1.0
    cdf = lambda k: sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n  # noqa: E731
    return min(1.0, 2 * cdf(min(b, c))), cdf(c)


def snapshot_mentions(pmids):
    """{pmid: [files]}: every file of the frozen tag (the sparse copy the frozen run used) that names the paper."""
    names = subprocess.run(['git', '-C', str(MAIN), 'ls-tree', '-r', '--name-only', TAG], capture_output=True,
                           text=True, check=True).stdout.split('\n')
    out = collections.defaultdict(list)
    for f in filter(None, names):
        t = subprocess.run(['git', '-C', str(MAIN), 'show', f'{TAG}:{f}'], capture_output=True).stdout.decode('utf-8', 'replace')
        for p in pmids:
            if re.search(rf'(?<![0-9A-Za-z]){re.escape(p)}(?![0-9A-Za-z])', t):
                out[p].append(f)
    return out


def taxonomy_mentions(pmids):
    """{pmid: [kind ids]}: the lines of CatLog's failure list (85 kinds to 2 Nov) that cite the paper."""
    t = (MAIN / 'paper' / 'figures' / 'method_overview' / 'v5' / 'taxonomy.tsv').read_text()
    rows = list(csv.DictReader(t.splitlines(), delimiter='\t'))
    out = {}
    for p in pmids:
        ids = [r['id'] for r in rows if re.search(rf'(?<![0-9A-Za-z]){re.escape(p)}(?![0-9A-Za-z])', '\t'.join(r.values()))]
        if ids:
            out[p] = ids
    return out


def catalogue_now(pmids):
    """(rows in catalogue units by paper, every row by paper, (added, row_id, reader_model) of every row that carries an
    add time, in catalog.jsonl and among the rows dropped since, by paper)."""
    want, by, every, added = set(pmids), collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    for name in ('catalog.jsonl', 'rejected.jsonl'):
        with open(MAIN / name) as fh:
            for line in fh:
                if not any(p in line for p in want):  # cheap pre-filter; parsed below
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                p = str(r.get('pmid'))
                if p not in want:
                    continue
                if r.get('added') and r.get('row_id') and (name == 'catalog.jsonl' or r.get('dropped')):
                    added[p].append((r['added'], r['row_id'], r.get('reader_model') or ''))
                if name != 'catalog.jsonl':
                    continue
                v = {'metric': r.get('metric'), 'value': r.get('value'), 'raw': r.get('raw_value'),
                     'raw_unit': r.get('raw_unit'), 'enzyme': r.get('enzyme'), 'variant': r.get('variant'),
                     'substrate': r.get('substrate'), 'id': r.get('row_id'), 'unit': r.get('unit')}
                every[p].append(v)
                if r.get('unit') in F.UNITS:
                    by[p].append(v)
    return by, every, added


def first_add_models(added):
    """{pmid: (time, 'model (rows); ...')}: the reader model of the rows of each paper's first add (the row's own
    stamp, else sources/provenance_backfill.tsv, reconstructed from the agents' logs); '?' where neither has it."""
    want = {rid for rows in added.values() for _, rid, m in rows if not m}
    back = {}
    with open(MAIN / 'sources' / 'provenance_backfill.tsv') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            if r['row_id'] in want:
                back[r['row_id']] = r['reader_model']
    out = {}
    for p, rows in added.items():
        first = min(a for a, _, _ in rows)
        c = collections.Counter(m or back.get(rid) or '?' for a, rid, m in rows if a == first)
        out[p] = (first, '; '.join(f'{m} ({n})' for m, n in c.most_common()))
    return out


def main():
    summ = {r['pmid']: r for r in json.loads((EVD / 'summary.json').read_text()) if r['model'] == 'Opus 5.5'}
    pmids = list(summ)
    hold = {l.strip() for l in open(MAIN / 'sources' / 'holdout_locked.txt') if l.strip() and not l.startswith('#')}
    assert not hold & set(pmids), 'a held-out paper is among the trap papers'
    today = json.loads((EVD / 'today' / 'today_scores.json').read_text())
    first_old = json.loads((EVD / 'catlog_first_scores.json').read_text())
    cat_old = json.loads((EVD / 'catlog_scores.json').read_text())
    blind2 = {(r['pmid'], r['source']): r for r in json.loads((EVD / 'rescore2' / 'final.json').read_text())}
    status_now = {r['pmid']: r['status'] for r in W.read_tsv(MAIN / 'papers.tsv')}
    named = T.named_papers(pmids)
    mentions = snapshot_mentions(pmids)
    tax = taxonomy_mentions(pmids)
    _, rows_run, work_run, _ = T.kept_run()
    cat_now, cat_every, added = catalogue_now(pmids)
    models = first_add_models(added)
    diffs = []

    # the plain reading, scored now by code, as score_hard.main does it (one call per key set)
    plain_code, plain_blind, plain_stored = {}, {}, {}
    for base in (EVD, EVD / 'expand'):
        keyset = sorted(p.stem for p in (base / 'keys').glob('*.json') if not p.name.endswith('.check.json'))
        vals, status, _ = SW.arm_values(W.EVAL, 'A0', 'hard', keyset)
        by = collections.defaultdict(list)
        for v in vals:
            by[str(v.get('pmid'))].append(v)
        for c in json.loads((base / 'scores.json').read_text())['cells']:
            plain_stored.setdefault(c['pmid'], {})[c['index']] = c['verdict']
        for r in json.loads((base / 'rescore' / 'final.json').read_text()):
            plain_blind[r['pmid']] = {c['index']: c['final'] for c in r['cells']}
        for p in keyset:
            if p in summ:
                key, cells = SH.cells_of(p, base)
                ident = str(key.get('trap_kind', '')).startswith('identity')
                plain_code[p] = score(cells, by.get(p, []), ident) if status.get(p) == 'ok' else None

    out, cell_rows = {}, []
    for p in pmids:
        s = summ[p]
        base = EVD if s['set'] == 'first' else EVD / 'expand'
        key, cells = SH.cells_of(p, base)
        ident = str(key.get('trap_kind', '')).startswith('identity')
        idx = [c['index'] for c in cells]
        rec = {'pmid': p, 'kind': s['class_id'], 'set': s['set'], 'visible': s['visible'], 'cells': len(cells),
               'identity_trap': ident, 'named_in': named.get(p, ''), 'snapshot_files': mentions.get(p, []),
               'failure_list': tax.get(p, [])}
        v = {}
        # the plain reading
        v['plain'] = plain_code[p]
        if [plain_stored[p][i] for i in idx] != v['plain']:
            diffs.append(f"{p} plain reading: on file {[plain_stored[p][i] for i in idx]}, now {v['plain']}")
        rec['plain_blind_fell_in'] = any(plain_blind[p][i] == 'trap' for i in idx)
        # CatLog's first reading: the earliest work file with kcat/Km rows, kept only when it predates the freeze
        fr = F.first_read(p)
        v['first'] = v['first_after_freeze'] = None
        rec.update(first_file='', first_date='', first_model='', first_blind_fell_in=None)
        if fr:
            ts, f, d, rows = fr
            when = datetime.datetime.fromtimestamp(os.path.getmtime(f), tz=FREEZE.tzinfo)
            rec.update(first_file=os.path.relpath(f, MAIN), first_date=when.date().isoformat(), first_model=d.get('model', ''))
            fv = score(cells, F.converted(p, rows), ident)
            old = first_old.get(p, {}).get('verdicts')
            if old is None:
                diffs.append(f'{p} first reading: none on file (catlog_first_scores.json); now {rec["first_file"]} '
                             f'of {rec["first_date"]}, {"before" if when < FREEZE else "after"} the freeze')
            elif old != fv:
                diffs.append(f'{p} first reading: on file {old}, now {fv}')
            v['first' if when < FREEZE else 'first_after_freeze'] = fv
            b1 = blind2.get((p, 'first'))
            rec['first_blind_fell_in'] = any(c['final'] == 'trap' for c in b1['cells']) if b1 else None
        # the frozen run (9 November): reader alone, then reader + verifier + code; papers left out as on file
        rec['frozen_left_out'] = (today.get(p) or {}).get('why', '')
        v['frozen_reader'] = v['frozen_pass'] = None
        if not rec['frozen_left_out']:
            rf = work_run[p] / f'{p}.read.json'
            rr = [r for r in (json.loads(rf.read_text()).get('rows') or []) if not r.get('censored')] if rf.exists() else []
            v['frozen_reader'] = score(cells, F.converted(p, rr), ident)
            v['frozen_pass'] = score(cells, [x for x in rows_run.get(p, []) if x.get('unit') in F.UNITS], ident)
            for name, k in (('frozen_reader', 'reader'), ('frozen_pass', 'first_pass')):
                if today[p][k]['verdicts'] != v[name]:
                    diffs.append(f"{p} {NAME[name]}: on file {today[p][k]['verdicts']}, now {v[name]}")
        # the catalogue: now (catalog.jsonl as it is) and as scored by code for the first trap test (catlog_scores.json)
        rec['status_now'] = status_now.get(p, '')
        rec['status_then'] = s.get('catlog_status') or ''
        v['catalogue'] = score(cells, cat_now.get(p, []), ident) if rec['status_now'] in READ else None
        if v['catalogue'] is not None and score(cells, cat_every.get(p, []), ident) != v['catalogue']:
            diffs.append(f'{p} catalogue now: the verdicts differ when rows outside catalogue units are kept')
        v['catalogue_then'] = [c['catlog'] for c in cat_old[p]['cells']] if rec['status_then'] in READ else None
        b2 = blind2.get((p, 'catalogue'))
        rec['catalogue_then_blind_fell_in'] = any(c['final'] == 'trap' for c in b2['cells']) if b2 else None
        rec['first_add'], rec['first_add_models'] = models.get(p, ('', ''))
        rec['v'] = v
        out[p] = rec
        for j, c in enumerate(cells):
            cell_rows.append({'pmid': p, 'kind': s['class_id'], 'cell': c['index'], 'metric': c.get('metric'),
                              'variant': c.get('variant'), 'substrate': str(c.get('substrate') or '')[:60],
                              **{NAME[k]: (v[k][j] if v.get(k) is not None else '') for k in NAME},
                              'catalogue_scored_4nov': v['catalogue_then'][j] if v['catalogue_then'] is not None else '',
                              'plain_reading_blind_rescore': plain_blind[p][c['index']]})

    write_csv(out, cell_rows)
    totals = summarise(out)
    totals['recomputed_against_files_on_record'] = diffs or ['every recomputed verdict equals the one on file']
    (HERE / 'totals.json').write_text(json.dumps(totals, indent=1, ensure_ascii=False) + '\n')
    print('\n'.join(diffs) or 'every recomputed verdict equals the one on file')
    for k, t in totals['tests'].items():
        print(f"{k}: {t}")


def fi(rec, k, review=False):
    v = rec['v'].get(k)
    if v is None:
        return None
    t = tally(v)
    return t['fell_in_if_review'] if review else t['fell_in']


def write_csv(out, cell_rows):
    R = list(NAME)
    cols = (['pmid', 'kind', 'kind_in_words', 'set', 'trap_seen_in', 'named_by_catlog', 'cells']
            + [f'{NAME[k]}_fell_in' for k in R] + ['first_reading_then_frozen_reader_alone']
            + [f'{NAME[k]}_trap_cells' for k in R] + [f'{NAME[k]}_review_cells' for k in R]
            + ['frozen_left_out', 'first_reading_file', 'first_reading_date', 'first_reading_model_stamped',
               'first_add', 'first_add_reader_model', 'first_reading_after_freeze_fell_in', 'catalogue_status_now',
               'catalogue_scored_4nov_fell_in', 'plain_reading_fell_in_blind_rescore', 'first_reading_fell_in_blind_rescore',
               'catalogue_scored_4nov_fell_in_blind_rescore', 'failure_list_kinds', 'other_snapshot_files'])
    pair_words = {(True, False): 'fell in, then not', (False, True): 'not, then fell in',
                  (True, True): 'fell in both times', (False, False): 'neither time'}
    with open(HERE / 'traps.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for p, r in sorted(out.items(), key=lambda kv: (ORDER.index(kv[1]['kind']), kv[1]['set'] != 'first', kv[0])):
            v = r['v']
            t = {k: (tally(v[k]) if v.get(k) is not None else None) for k in R}
            a, b = fi(r, 'first'), fi(r, 'frozen_reader')
            other = [f for f in r['snapshot_files'] if not (f.endswith('.py') or f in (
                'CLAUDE.md', '.claude/agents/catlog-reader.md', '.claude/workflows/catlog-batch.js') or f.startswith('prompts/'))]
            w.writerow({
                'pmid': p, 'kind': r['kind'], 'kind_in_words': KIND[r['kind']],
                'set': 'first' if r['set'] == 'first' else 'drawn',
                'trap_seen_in': 'the paper' if r['visible'] == 'in_paper' else 'another publication',
                'named_by_catlog': r['named_in'] or 'no', 'cells': r['cells'],
                **{f'{NAME[k]}_fell_in': yn(t[k]['fell_in'] if t[k] else None) for k in R},
                'first_reading_then_frozen_reader_alone': '' if a is None or b is None else pair_words[(a, b)],
                **{f'{NAME[k]}_trap_cells': (t[k]['trap'] if t[k] else '') for k in R},
                **{f'{NAME[k]}_review_cells': (t[k]['review'] if t[k] else '') for k in R},
                'frozen_left_out': r['frozen_left_out'],
                'first_reading_file': r['first_file'], 'first_reading_date': r['first_date'],
                'first_reading_model_stamped': r['first_model'],
                'first_add': r['first_add'], 'first_add_reader_model': r['first_add_models'],
                'first_reading_after_freeze_fell_in': yn(tally(v['first_after_freeze'])['fell_in']) if v.get('first_after_freeze') else '',
                'catalogue_status_now': r['status_now'],
                'catalogue_scored_4nov_fell_in': yn(tally(v['catalogue_then'])['fell_in'] if v.get('catalogue_then') is not None else None),
                'plain_reading_fell_in_blind_rescore': yn(r['plain_blind_fell_in']),
                'first_reading_fell_in_blind_rescore': yn(r['first_blind_fell_in']),
                'catalogue_scored_4nov_fell_in_blind_rescore': yn(r['catalogue_then_blind_fell_in']),
                'failure_list_kinds': ' '.join(r['failure_list']), 'other_snapshot_files': ' '.join(other)})
    with open(HERE / 'cells.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(cell_rows[0]))
        w.writeheader()
        w.writerows(cell_rows)


def summarise(out):
    R = list(NAME)
    every = list(out.values())
    read = [r for r in every if not r['frozen_left_out']]
    unnamed = [r for r in read if not r['named_in']]
    named_read = [r for r in read if r['named_in']]
    drawn_unnamed = [r for r in unnamed if r['set'] == 'expand']
    clean = [r for r in unnamed if not r['failure_list'] and not r['snapshot_files']]

    def opus55_only(m):  # every stamped row of the first add by Opus 5.5 (rows with no stamp, '?', set aside)
        names = {x.rsplit(' (', 1)[0] for x in (m or '').split('; ') if x}
        return 'claude-opus-5-5' in names and names <= {'claude-opus-5-5', '?'}
    same_model = [r for r in unnamed if opus55_only(r['first_add_models'])]
    sets = {'all 53': every, 'read again by the frozen CatLog (41)': read,
            'no instruction or code names (32)': unnamed,
            'named by an instruction or code, read again (9)': named_read,
            'no instruction or code names, drawn set only': drawn_unnamed,
            'no instruction or code names, not cited by the failure list or any snapshot file': clean,
            'no instruction or code names, first add read by Opus 5.5 alone': same_model}

    def count(sel, k, review=False):
        x = [fi(r, k, review) for r in sel]
        x = [y for y in x if y is not None]
        return [sum(x), len(x)]

    res = {'readings': WORDS, 'basis': 'code scoring now (score_hard.score_cell) on the checked keys; a review cell '
                                       'counts as not fallen in unless the entry says otherwise; [fell in, of papers]',
           'sets': {}, 'by_kind': {}, 'tests': {}, 'papers': {}}
    for name, sel in sets.items():
        res['sets'][name] = {'papers': len(sel), **{NAME[k]: count(sel, k) for k in R},
                             'catalogue_scored_4nov': count(sel, 'catalogue_then'),
                             'review_counted_as_fell_in': {NAME[k]: count(sel, k, True) for k in R},
                             'trap_cells': {NAME[k]: [sum(tally(r['v'][k])['trap'] for r in sel if r['v'].get(k) is not None),
                                                      sum(r['cells'] for r in sel if r['v'].get(k) is not None)] for k in R}}
        res['papers'][name] = [r['pmid'] for r in sel]
    for name, sel in (('no instruction or code names (32)', unnamed), ('read again by the frozen CatLog (41)', read),
                      ('all 53', every)):
        res['by_kind'][name] = {}
        for k in ORDER + ['all']:
            ks = [r for r in sel if k in (r['kind'], 'all')]
            if ks:
                pairs = [(fi(r, 'first'), fi(r, 'frozen_reader')) for r in ks]
                pairs = [x for x in pairs if None not in x]
                res['by_kind'][name][k] = {'papers': len(ks), **{NAME[x]: count(ks, x) for x in R},
                                           'first_reading_then_frozen_reader_alone': {
                                               'pairs': len(pairs), 'fell in, then not': sum(1 for a, b in pairs if a and not b),
                                               'not, then fell in': sum(1 for a, b in pairs if b and not a)}}

    def paired(sel, a, b, review=False):
        pairs = [(fi(r, a, review), fi(r, b, review), r['pmid']) for r in sel]
        pairs = [x for x in pairs if x[0] is not None and x[1] is not None]
        down = [p for x, y, p in pairs if x and not y]
        up = [p for x, y, p in pairs if y and not x]
        two, one = exact_mcnemar(len(down), len(up))
        return {'pairs': len(pairs), f'{NAME[a]} fell in, {NAME[b]} not': down, f'{NAME[b]} fell in, {NAME[a]} not': up,
                'both fell in': sum(1 for x, y, _ in pairs if x and y), 'neither': sum(1 for x, y, _ in pairs if not x and not y),
                'exact_mcnemar_two_sided_p': float(f'{two:.3g}'), f'one_sided_p_{NAME[b]}_falls_in_less': float(f'{one:.3g}')}

    def cells_sign(sel, a, b):
        d = [(tally(r['v'][a])['trap'], tally(r['v'][b])['trap'], r['pmid']) for r in sel
             if r['v'].get(a) is not None and r['v'].get(b) is not None]
        fewer = [p for x, y, p in d if y < x]
        more = [p for x, y, p in d if y > x]
        two, one = exact_mcnemar(len(fewer), len(more))
        return {'papers': len(d), f'fewer trap cells in {NAME[b]}': fewer, f'more trap cells in {NAME[b]}': more,
                'same': len(d) - len(fewer) - len(more), 'sign_test_two_sided_p': float(f'{two:.3g}'),
                f'one_sided_p_{NAME[b]}_fewer': float(f'{one:.3g}')}

    t = res['tests']
    t['MAIN: first reading vs frozen reader alone, the 32 papers no instruction or code names'] = paired(unnamed, 'first', 'frozen_reader')
    t['same, a review cell counted as fallen in'] = paired(unnamed, 'first', 'frozen_reader', True)
    t['same, trap cells per paper (sign test)'] = cells_sign(unnamed, 'first', 'frozen_reader')
    t['same, drawn set only'] = paired(drawn_unnamed, 'first', 'frozen_reader')
    t['same, also cited by neither the failure list nor any snapshot file'] = paired(clean, 'first', 'frozen_reader')
    t['same, first add read by Opus 5.5 alone (the model of the frozen and the plain reading)'] = paired(same_model, 'first', 'frozen_reader')
    t['first reading vs frozen reader alone, the 9 named papers'] = paired(named_read, 'first', 'frozen_reader')
    t['first reading vs frozen reader alone, all 41 read again'] = paired(read, 'first', 'frozen_reader')
    t['plain reading vs frozen reader alone, unnamed'] = paired(unnamed, 'plain', 'frozen_reader')
    t['plain reading vs frozen reader with verifier and code, unnamed'] = paired(unnamed, 'plain', 'frozen_pass')
    t['plain reading vs frozen reader with verifier and code, unnamed, a review cell counted as fallen in'] = paired(unnamed, 'plain', 'frozen_pass', True)
    t['frozen reader alone vs frozen reader with verifier and code, unnamed'] = paired(unnamed, 'frozen_reader', 'frozen_pass')
    t['first reading vs frozen reader with verifier and code, unnamed (not like for like)'] = paired(unnamed, 'first', 'frozen_pass')
    t['plain reading vs catalogue now, unnamed'] = paired(unnamed, 'plain', 'catalogue')
    t['frozen reader with verifier and code vs catalogue now, unnamed'] = paired(unnamed, 'frozen_pass', 'catalogue')
    t['first reading vs catalogue now, unnamed'] = paired(unnamed, 'first', 'catalogue')
    t['plain reading vs catalogue now, all 53'] = paired(every, 'plain', 'catalogue')
    t['first reading vs catalogue now, all 53'] = paired(every, 'first', 'catalogue')
    return res


if __name__ == '__main__':
    main()
