#!/usr/bin/env python3
"""The repeat of the reprint sweep, 16 Nov 2026, counted against the catalogue frozen for the paper.

Two steps:
  python3 build.py collect   once, on 16 Nov 2026: copies what the sweep used and decided out of work/ (git-ignored)
                             and the chat's scratch folder into this folder (pair lists, the papers chosen, the judges'
                             cases, every verdict file of the day as verdicts.tar.gz, the earlier check files of every
                             other listed paper as verdicts_before.tar.gz) and writes rows.tsv, papers.tsv, drops.tsv
  python3 build.py           counts numbers.json from this folder's files and the freeze tag's catalog.jsonl and
                             bounds.jsonl (`git show`), so it reruns from git alone

Runs: 'main' = the 205 papers chosen from the 08:24 and 13:38 scans (check, refute, judges); 'gap' = 15 papers checked
on 16 Oct whose 17 pairs no agent had seen (found by the fact check, CHECK.md), checked the same way that evening
against those pairs only (work/reprint_<PMID>.gap*.json).

A row is one stored value (a kcat, Km or kcat/Km; row_id as in catalog.jsonl). 'decision' is the first agent's call
(OWN, REPRINT or UNSURE), 'refuter' the second agent's on a REPRINT call (confirmed or refuted), 'judge_*' the two
further agents' calls on a refuted row (provenance lens, cells lens), 'outcome' what happened to the row.
"""
import csv
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TAG = 'paper-catalog-freeze-20261116'
EPMC = os.path.join(ROOT, 'paper', 'evidence', 'europepmc_freeze_20261116', 'papers.tsv')
SCRATCH = '<the scratch folder of the session that ran the sweep>'
MARK = '2026-11-16 pair scan repeat'
LISTS = ('pairs_20261116_0824.tsv', 'pairs_20261116_1338.tsv')


def here(name):
    return os.path.join(HERE, name)


def read_tsv(name):
    return list(csv.DictReader(open(here(name), newline=''), delimiter='\t'))


def write_tsv(name, rows):
    with open(here(name), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def ids(xs):
    return {x if isinstance(x, str) else x['row_id'] for x in xs}


def collect():
    import shutil
    w = lambda *p: os.path.join(ROOT, 'work', *p)
    shutil.copy2(w('reprint_pairs.tsv'), here('pairs_20261116_0824.tsv'))  # the scan the 198 papers came from
    shutil.copy2(os.path.join(SCRATCH, 'reprint_pairs_topup_all.tsv'), here('pairs_20261116_1338.tsv'))  # the top-up's
    shutil.copy2(os.path.join(SCRATCH, 'reprint_pairs_gap_20261116.tsv'), here('pairs_gap_20261116.tsv'))  # the gap run's
    shutil.copy2(w('reprint_sweep', 'reprint_pairs_before_20261116.tsv'), here('pairs_before_20261116.tsv'))  # 11 Nov
    shutil.copy2(w('reprint_pairs_4plus_20261016.tsv'), here('pairs_4plus_20261016.tsv'))  # the 16 Oct 4+ run's list
    chosen = [str(x) for x in json.load(open(os.path.join(SCRATCH, 'reprint_pmids.json')))]
    topup = [str(x) for x in json.load(open(os.path.join(SCRATCH, 'topup_pmids.json')))]
    gap = [str(x) for x in json.load(open(os.path.join(SCRATCH, 'gap_pmids.json')))]
    cases = json.load(open(os.path.join(SCRATCH, 'third_cases.json')))
    json.dump({'scan_0824': chosen, 'topup_1338': topup, 'gap': gap}, open(here('papers_chosen.json'), 'w'), indent=1)
    json.dump(cases, open(here('judge_cases.json'), 'w'), indent=1, ensure_ascii=False)
    again = {re.match(r'reprint_(.+?)\.(check\.)?json$', os.path.basename(f)).group(1)
             for f in glob.glob(w('reprint_sweep', 'first_check_files_20261116', 'reprint_*.json'))}

    applied = {}  # what log.tsv records as dropped by this repeat: row_id -> (time, pmid, why)
    for line in open(os.path.join(ROOT, 'log.tsv'), encoding='utf-8', errors='replace'):
        f = line.rstrip('\n').split('\t')
        if len(f) >= 5 and f[2] in ('drop', 'drop_bound') and MARK in f[4]:
            applied[f[3]] = (f[0], f[1], f[4])

    files, rows, papers = [], [], []
    judged = {}  # row_id -> (earlier, provenance verdict, cells verdict)
    for c in cases:  # the main run's judges, one case per suspect paper and earlier paper
        v = {}
        for lens in ('provenance', 'cells'):
            fn = w(f"reprint_{c['pmid']}.third_{lens}_{c['earlier']}.json")
            files.append(fn)
            v[lens] = {r['row_id']: r.get('verdict', '') for r in json.load(open(fn))['rows']}
        for rid in c['row_ids']:
            judged[rid] = (c['earlier'], v['provenance'].get(rid, ''), v['cells'].get(rid, ''))
    for pm in gap:  # the gap run's judges, found by name
        for fn in sorted(glob.glob(w(f'reprint_{pm}.gap.third_*_*.json'))):
            lens, earlier = re.match(rf'reprint_{re.escape(pm)}\.gap\.third_(provenance|cells)_(.+)\.json$',
                                     os.path.basename(fn)).groups()
            files.append(fn)
            for r in json.load(open(fn))['rows']:
                e, jp, jc = judged.get(r['row_id'], (earlier, '', ''))
                judged[r['row_id']] = (earlier, r.get('verdict', '') if lens == 'provenance' else jp,
                                       r.get('verdict', '') if lens == 'cells' else jc)

    for run, plist in (('main', chosen + topup), ('gap', gap)):
        suffix = '.gap' if run == 'gap' else ''
        for pm in plist:
            fn = w(f'reprint_{pm}{suffix}.json')
            files.append(fn)
            first = json.load(open(fn))
            seen = {}
            for r in first['rows']:  # a row listed twice (14745009 lists 5 rows under two earlier papers) counts once
                if r['row_id'] in seen:
                    if seen[r['row_id']]['decision'] != r['decision']:
                        raise SystemExit(f"{pm} {r['row_id']}: listed twice with different decisions")
                    continue
                seen[r['row_id']] = r
            conf, refu = set(), set()
            if any(r['decision'] == 'REPRINT' for r in seen.values()):
                chk = w(f'reprint_{pm}{suffix}.check.json')
                old = w('reprint_sweep', 'first_check_files_20261116', f'reprint_{pm}.check.json')
                # a paper checked again with no REPRINT call keeps its 16 Oct refuter file in work/ (16325466, 17521737)
                if run == 'main' and os.path.exists(old) and open(old, 'rb').read() == open(chk, 'rb').read():
                    raise SystemExit(f'{pm}: REPRINT calls today but only the 16 Oct refuter file')
                files.append(chk)
                d = json.load(open(chk))
                conf, refu = ids(d.get('confirmed', [])), ids(d.get('refuted', []))
            n = Counter()
            for rid, r in seen.items():
                dec = r['decision']
                refuter = 'confirmed' if rid in conf else 'refuted' if rid in refu else ''
                jp, jc, earlier = '', '', str(r.get('earlier_pmid') or '')
                if rid in judged and dec == 'REPRINT':
                    earlier, jp, jc = judged[rid]
                if rid in applied:
                    outcome = ('dropped: attributed to other work' if 'attributed to other work' in applied[rid][2]
                               else 'dropped: reprint')
                elif dec == 'OWN':
                    outcome = 'kept: own'
                elif dec == 'UNSURE':
                    outcome = 'kept: unsure'
                elif refuter == 'refuted' and (jp or jc):
                    outcome = 'kept: judges split'
                elif refuter == 'refuted':
                    outcome = 'kept: refuted'
                else:
                    raise SystemExit(f'{pm} {rid}: {dec} {refuter} but not dropped')
                if dec == 'REPRINT' and (refuter == 'confirmed' or (jp == jc == 'NOT_OWN')) and rid not in applied:
                    raise SystemExit(f'{rid}: confirmed but not dropped')
                rows.append({'run': run, 'row_id': rid, 'pmid': pm, 'metric': r.get('metric', ''), 'decision': dec,
                             'earlier_pmid': earlier if dec != 'OWN' else '', 'refuter': refuter,
                             'judge_provenance': jp, 'judge_cells': jc, 'outcome': outcome})
                n[dec] += 1
                n[outcome] += 1
            if run == 'gap':
                how = 'gap: checked 16 Oct, these pairs never before an agent'
            else:
                how = ('top-up 13:38' if pm in topup else 'scan 08:24') + (
                    ', checked 16 Oct, pairs changed since the 11 Nov list' if pm in again else ', never checked before')
            papers.append({'run': run, 'pmid': pm, 'chosen': how, 'values_judged': len(seen), 'own': n['OWN'],
                           'reprint_called': n['REPRINT'], 'unsure': n['UNSURE'],
                           'dropped': n['dropped: reprint'] + n['dropped: attributed to other work']})
    missing = set(applied) - {r['row_id'] for r in rows}
    if missing:
        raise SystemExit(f'dropped but in no verdict file: {sorted(missing)}')
    if len({r['row_id'] for r in rows}) != len(rows):
        raise SystemExit('a value judged in both runs')
    write_tsv('rows.tsv', rows)
    write_tsv('papers.tsv', papers)
    write_tsv('drops.tsv', [{'time': t, 'pmid': p, 'row_id': rid, 'why': why} for rid, (t, p, why) in sorted(applied.items())])
    with tarfile.open(here('verdicts.tar.gz'), 'w:gz') as tar:
        for fn in sorted(set(files)):
            tar.add(fn, arcname='verdicts/' + os.path.basename(fn))
    # the earlier verdict files of every listed paper not checked today in the main run (16 Oct sweep, follow-ups):
    # the coverage test below reads them
    listed = {r['later'] for name in LISTS for r in read_tsv(name)}
    before = []
    for pm in sorted(listed - set(chosen) - set(topup)):
        before += [f for f in glob.glob(w(f'reprint_{pm}.json')) + glob.glob(w(f'reprint_{pm}.check.json'))
                   + glob.glob(w(f'reprint_{pm}.third_*.json')) + glob.glob(w(f'reprint_{pm}.rest.json'))]
    for pm in sorted(again):  # the re-checked papers' 16 Oct files, kept aside before today's check rewrote them
        before += glob.glob(w('reprint_sweep', 'first_check_files_20261116', f'reprint_{pm}*.json'))
    with tarfile.open(here('verdicts_before.tar.gz'), 'w:gz') as tar:
        for fn in sorted(set(before)):
            sub = 'first_check_files_20261116/' if 'first_check_files' in fn else ''
            tar.add(fn, arcname='verdicts_before/' + sub + os.path.basename(fn))
    print(f'collected: {len(rows)} rows, {len(papers)} papers, {len(applied)} drops, {len(set(files))} verdict files, '
          f'{len(set(before))} earlier verdict files')


def tag_rows(path):
    out = subprocess.run(['git', 'show', f'{TAG}:{path}'], cwd=ROOT, capture_output=True, check=True).stdout
    rows = {}
    for line in io.TextIOWrapper(io.BytesIO(out), encoding='utf-8'):
        if line.strip():
            r = json.loads(line)
            rows[r['row_id']] = r['pmid']
    return rows


def texts_by_paper(archive):
    """Every verdict file's text, by the suspect paper it is about."""
    out = {}
    with tarfile.open(here(archive)) as tar:
        for m in tar.getmembers():
            if m.isfile():
                pm = re.match(r'reprint_(.+?)\.', os.path.basename(m.name)).group(1)
                out[pm] = out.get(pm, '') + tar.extractfile(m).read().decode('utf-8', 'replace')
    return out


def count():
    rows, papers = read_tsv('rows.tsv'), read_tsv('papers.tsv')
    chosen = json.load(open(here('papers_chosen.json')))
    cat, bnd = tag_rows('catalog.jsonl'), tag_rows('bounds.jsonl')
    commit = subprocess.run(['git', 'rev-parse', f'{TAG}^{{commit}}'], cwd=ROOT, capture_output=True, text=True,
                            check=True).stdout.strip()
    frozen = len(cat)
    frozen_papers = Counter(cat.values())
    epmc = {r['pmid'] for r in csv.DictReader(open(EPMC), delimiter='\t')}
    pairs = {name: read_tsv(name) for name in LISTS}
    listed = {r['later'] for v in pairs.values() for r in v}
    partners = {r['earlier'] for v in pairs.values() for r in v if r['kind'] == 'catalog'}
    in_freeze = lambda r: r['row_id'] in cat or r['row_id'] in bnd

    # coverage: does a verdict file about the later paper (today's or an earlier one) name each pair's earlier paper?
    named = texts_by_paper('verdicts.tar.gz')
    for pm, t in texts_by_paper('verdicts_before.tar.gz').items():
        named[pm] = named.get(pm, '') + t
    allpairs = {(r['later'], r['earlier']) for v in pairs.values() for r in v}
    unnamed = sorted((l, e) for l, e in allpairs if not re.search(rf'(?<![0-9A-Z]){re.escape(e)}(?![0-9])', named.get(l, '')))

    def tally(sel):
        sel = list(sel)
        c = Counter(r['outcome'] for r in sel)
        return {'values': len(sel), 'papers': len({r['pmid'] for r in sel}),
                'kept_own': c['kept: own'], 'kept_unsure': c['kept: unsure'],
                'called_reprint': sum(r['decision'] == 'REPRINT' for r in sel),
                'papers_with_reprint_call': len({r['pmid'] for r in sel if r['decision'] == 'REPRINT'}),
                'refuter_confirmed': sum(r['refuter'] == 'confirmed' for r in sel),
                'refuter_refuted': sum(r['refuter'] == 'refuted' for r in sel),
                'judged': sum(bool(r['judge_cells'] or r['judge_provenance']) for r in sel),
                'judges_both_not_own': sum(r['judge_provenance'] == 'NOT_OWN' and r['judge_cells'] == 'NOT_OWN' for r in sel),
                'kept_judges_split': c['kept: judges split'], 'kept_refuted': c['kept: refuted'],
                'dropped_reprint': c['dropped: reprint'],
                'dropped_attributed': c['dropped: attributed to other work'],
                'dropped': c['dropped: reprint'] + c['dropped: attributed to other work'],
                'papers_with_a_drop': len({r['pmid'] for r in sel if r['outcome'].startswith('dropped')})}

    def run(sel_papers, sel_rows):
        checked = {p['pmid'] for p in sel_papers}
        t = tally(r for r in sel_rows if in_freeze(r))
        return {**t, 'papers_checked': len(checked), 'papers_checked_in_freeze': len(checked & set(frozen_papers)),
                'values_stored_in_these_papers': sum(frozen_papers[p] for p in checked),
                'not_in_freeze': len([r for r in sel_rows if not in_freeze(r)])}

    main = run([p for p in papers if p['run'] == 'main'], [r for r in rows if r['run'] == 'main'])
    gap = run([p for p in papers if p['run'] == 'gap'], [r for r in rows if r['run'] == 'gap'])
    both = run(papers, rows)
    epmc_drops = [r for r in rows if r['outcome'].startswith('dropped') and r['pmid'] in epmc and in_freeze(r)]
    n = {
        'what': 'repeat of the reprint sweep (tools/reprint_pairs.py, 3 or more shared values), 16 Nov 2026, '
                'counted against the catalogue frozen for the paper',
        'freeze': {'tag': TAG, 'commit': commit, 'values': frozen, 'papers': len(frozen_papers)},
        'scan': {'pairs_0824': len(pairs['pairs_20261116_0824.tsv']), 'pairs_1338': len(pairs['pairs_20261116_1338.tsv']),
                 'pairs_both_lists': len(allpairs),
                 'database_pairs_0824': sum(r['kind'] == 'database' for r in pairs['pairs_20261116_0824.tsv']),
                 'suspect_papers_listed': len(listed), 'suspect_papers_in_freeze': len(listed & set(frozen_papers)),
                 'catalogue_partners_not_suspects': len(partners - listed), 'catalogue_partners_named': len(partners),
                 'values_in_freeze_in_listed_papers': sum(frozen_papers[p] for p in listed & set(frozen_papers)),
                 'main_from_0824': len(chosen['scan_0824']), 'main_from_1338': len(chosen['topup_1338']),
                 'main_never_checked_before': sum('never checked' in p['chosen'] for p in papers),
                 'main_checked_16oct_pairs_changed': sum('pairs changed' in p['chosen'] for p in papers),
                 'gap_papers': len(chosen['gap']), 'gap_pairs': len(read_tsv('pairs_gap_20261116.tsv')),
                 'listed_papers_checked_on_16oct_only': len(listed - {p['pmid'] for p in papers}),
                 'pairs_whose_earlier_paper_no_verdict_file_names': len(unnamed), 'unnamed_pairs': unnamed},
        'main': main,
        'gap': gap,
        'both_runs': {**both, 'share_of_frozen_values_dropped': both['dropped'] / frozen,
                      'share_of_frozen_values_judged': both['values'] / frozen,
                      'share_of_judged_dropped': both['dropped'] / both['values']},
        'europepmc_frozen_set': {'values': sum(frozen_papers[p] for p in epmc),
                                 'papers_checked': len({p['pmid'] for p in papers} & epmc),
                                 'dropped_in_freeze': len(epmc_drops),
                                 'papers_with_a_drop': len({r['pmid'] for r in epmc_drops})},
        'inputs': {name: hashlib.sha256(open(here(name), 'rb').read()).hexdigest()
                   for name in ('rows.tsv', 'papers.tsv', 'drops.tsv', 'papers_chosen.json', 'judge_cases.json',
                                'pairs_20261116_0824.tsv', 'pairs_20261116_1338.tsv', 'pairs_gap_20261116.tsv',
                                'pairs_before_20261116.tsv', 'pairs_4plus_20261016.tsv', 'verdicts.tar.gz',
                                'verdicts_before.tar.gz')},
    }
    json.dump(n, open(here('numbers.json'), 'w'), indent=1)
    print(json.dumps({k: n[k] for k in ('freeze', 'scan', 'main', 'gap', 'both_runs', 'europepmc_frozen_set')}, indent=1))


if __name__ == '__main__':
    collect() if sys.argv[1:] == ['collect'] else count()
