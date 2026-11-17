#!/usr/bin/env python3
"""The Europe PMC part of the paper, frozen (the owner, 16 Nov 2026: "this is a wrap for europe pmc (for the paper not
overall) the website and db will keep growing but wrap for this part in the nature method paper report (freeze)").

The part: papers new to CatLog when two Europe PMC searches ran (tools/discover_europepmc.py: not in its queue, its
source lists, its database table, its no-PMID references, the old library or an earlier list), in
sources/discovered_europepmc_20261014.tsv (kcat with Km or Michaelis) and sources/discovered_km_20261109.tsv (Km or
Michaelis with kinetic context and no kcat). Reading goes on for the website after the freeze; the paper counts only
the papers of these lists whose read had finished at the freeze, from one snapshot of CatLog's own files.

Run from anywhere:
  python3 paper/evidence/europepmc_freeze_20261116/build.py [--ref REF] [--set FILE] [--db-pmids FILE] [--out DIR]
  --ref REF       read the tracked files (catalog.jsonl, bounds.jsonl, papers.tsv, log.tsv, the two lists) from git
                  REF, e.g. the tag europepmc-freeze-20261116; default: the working tree
  --set FILE      count only the PMIDs of FILE (the papers.tsv the freeze run wrote); default: every paper of the two
                  lists with a finished read (status done, incomplete or needs_supplement) at the snapshot
  --db-pmids FILE the papers CatLog's database table lists (one PMID per line, .gz allowed), e.g. the copy saved at
                  the freeze (db_pmids_at_freeze.txt.gz); default: the pmid column of the working tree's
                  sources/db_values.tsv (git-ignored, so a tag does not hold it)
  --out DIR       where numbers.json and papers.tsv go (default: this folder)
It stops if a working-tree file it read changed while it ran.

Words as in CLAUDE.md "State": a value is one number (kcat, Km or kcat/Km: a catalog.jsonl row), a record one row of
the export (catlog.measurements(): one enzyme or variant, substrate and assay of one paper, up to three values; the
website shows the records of finished papers), a paper its PMID. A censored value (bounds.jsonl: printed only as a
bound or as not detected) is never a value.
"""
import collections
import csv
import gzip
import hashlib
import io
import json
import os
import re
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, ROOT)
sys.argv, ARGS = ['catlog.py'], sys.argv[1:]
import catlog  # noqa: E402  (its measurements() is the export's grouping of values into records)


def arg(name):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else None


OUT, SET, REF, DBP = arg('--out') or HERE, arg('--set'), arg('--ref'), arg('--db-pmids')
LISTS = (('kcat', 'sources/discovered_europepmc_20261014.tsv', '2026-10-14', ('table', 'abstract', 'body')),
         ('km', 'sources/discovered_km_20261109.tsv', '2026-11-09', ('km_table', 'km_abstract', 'km_body')))
# the search's own header (found, known, non-enzyme, listed); the Km list's .txt lost it when the gain order rewrote
# that file on 9 Nov (commit 8b8e7c5), so it is read from the commit that wrote it
HEADERS = {'kcat': ('HEAD', 'sources/discovered_europepmc_20261014.txt'),
           'km': ('4df707d', 'sources/discovered_km_20261109.txt')}
READ = ('done', 'incomplete', 'needs_supplement')  # a finished read; values of a paper waiting for its supplement are stored
COUNT_ORDER = {'kcat': '2026-11-10', 'km': '2026-11-09'}  # the order by counted constants began (REPORT.md lines 53, 70)
OPEN = ('europepmc', 'pmc_cloud', 'openalex_oa')  # free to read; elsevier_api (campus subscription) and downloaded are not
TRACKED = ['catalog.jsonl', 'bounds.jsonl', 'papers.tsv', 'log.tsv'] + [f for _, f, _, _ in LISTS]


def git(*a):
    return subprocess.run(['git', *a], cwd=ROOT, capture_output=True, check=True).stdout


def read_bytes(rel):
    if REF:
        return git('show', f'{REF}:{rel}')
    with open(os.path.join(ROOT, rel), 'rb') as fh:
        return fh.read()


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def tsv(data):
    csv.field_size_limit(10 ** 9)
    return list(csv.DictReader(io.StringIO(data.decode()), delimiter='\t'))


def jsonl(data):
    return [json.loads(l) for l in data.decode().splitlines() if l.strip()]


def header_counts(name):
    ref, rel = HEADERS[name]
    text = git('show', f'{ref}:{rel}').decode(errors='replace')
    head = ' '.join(l.lstrip('# ').strip() for l in text.splitlines() if l.startswith('#'))
    num = lambda pat: int(re.search(pat, head).group(1).replace(',', ''))
    return {'found': num(r'([\d,]+) papers found'), 'already_known_to_catlog': num(r'([\d,]+) already known'),
            'non_enzyme_titles_left_out': num(r'([\d,]+) non-enzyme'), 'listed': num(r'([\d,]+) listed'),
            'header_source': f'git show {ref}:{rel}'}


def main():
    t0 = time.time()
    raw = {rel: read_bytes(rel) for rel in TRACKED}
    stamp = {rel: hashlib.sha256(b).hexdigest() for rel, b in raw.items()}
    head = git('rev-parse', '--short', f'{REF}^{{commit}}' if REF else 'HEAD').decode().strip()
    stamp['catlog.py (git blob at HEAD; records come from its measurements())'] = git('rev-parse', 'HEAD:catlog.py').decode().strip()
    if DBP:
        opener = gzip.open if DBP.endswith('.gz') else open
        with opener(DBP, 'rt') as fh:
            db_papers = {l.strip() for l in fh if l.strip()}
        stamp[DBP] = sha_file(DBP)
    else:
        dbv = os.path.join(ROOT, 'sources/db_values.tsv')
        stamp['sources/db_values.tsv (working tree, git-ignored)'] = sha_file(dbv)
        with open(dbv, newline='') as fh:
            db_papers = {r['pmid'] for r in csv.DictReader(fh, delimiter='\t')}

    lists, tier_of, list_of = {}, {}, {}
    for name, rel, date, tiers in LISTS:
        rows = tsv(raw[rel])
        lists[name] = {'file': rel, 'searched': date, **header_counts(name),
                       'by_tier': {t: sum(1 for r in rows if r['tier'] == t) for t in tiers},
                       'listed_papers_in_database_table': sum(1 for r in rows if r['pmid'] in db_papers)}
        if lists[name]['listed'] != len(rows):
            sys.exit(f'{rel}: {len(rows)} rows, its header says {lists[name]["listed"]} listed')
        for r in rows:
            if r['pmid'] not in list_of:  # the Km search left out every paper already known, the kcat list included
                list_of[r['pmid']], tier_of[r['pmid']] = name, r['tier']

    queue = {r['pmid']: r for r in tsv(raw['papers.tsv'])}
    cat, bounds = jsonl(raw['catalog.jsonl']), jsonl(raw['bounds.jsonl'])
    first_add = {}
    for line in raw['log.tsv'].decode(errors='replace').splitlines():
        f = line.split('\t')
        if len(f) > 3 and f[2] == 'add' and f[1] not in first_add:
            first_add[f[1]] = f[0]

    rows_of = collections.defaultdict(list)
    for r in cat:
        rows_of[r['pmid']].append(r)
    cens_of = collections.Counter(r['pmid'] for r in bounds)

    if SET:
        with open(SET, newline='') as fh:
            frozen = sorted(r['pmid'] for r in csv.DictReader(fh, delimiter='\t'))
    else:
        frozen = sorted(p for p in list_of if queue.get(p, {}).get('status') in READ)
    per = []
    for p in frozen:
        rows = rows_of.get(p, [])
        per.append({'pmid': p, 'list': list_of[p], 'tier': tier_of[p], 'status': queue[p]['status'],
                    'text_source': (queue[p].get('text_source') or '').split(':')[0], 'first_added': first_add.get(p, ''),
                    'values': len(rows), 'kcat': sum(r['metric'] == 'kcat' for r in rows),
                    'Km': sum(r['metric'] == 'Km' for r in rows), 'kcat/Km': sum(r['metric'] == 'kcat/Km' for r in rows),
                    'mass_concentration_values': sum(r.get('unit') in catlog_mass() for r in rows),
                    'records': len(catlog.measurements(rows)) if rows else 0, 'censored': cens_of.get(p, 0),
                    'in_database_table': p in db_papers})

    def block(ps):
        v = [x['values'] for x in ps]
        return {'papers_read': len(ps), 'papers_with_values': sum(1 for x in v if x),
                'papers_without_values': sum(1 for x in v if not x),
                'values': sum(v), 'kcat': sum(x['kcat'] for x in ps), 'Km': sum(x['Km'] for x in ps),
                'kcat_over_Km': sum(x['kcat/Km'] for x in ps), 'records': sum(x['records'] for x in ps),
                'censored_values': sum(x['censored'] for x in ps),
                'censored_values_in_papers_with_values': sum(x['censored'] for x in ps if x['values']),
                'values_per_paper_read_mean': round(sum(v) / len(v), 1) if v else None,
                'values_per_paper_read_median': statistics.median(v) if v else None}

    # the order each paper was read in, worked out once from the agents' transcripts (reading_order.py, which saved
    # reading_order.tsv: the gain chat's readers since the count order began = 'count', everything else = 'tier')
    ro_path = os.path.join(HERE, 'reading_order.tsv')
    ro = {}
    if os.path.exists(ro_path):
        with open(ro_path, newline='') as fh:
            ro = {r['pmid']: r['order'] for r in csv.DictReader(fh, delimiter='\t')}

    def order(ps):
        name = ps[0]['list'] if ps else 'kcat'
        out = {'count_order_began': COUNT_ORDER[name], 'source': 'reading_order.tsv' if ro else 'not worked out'}
        for o in ('tier', 'count', 'unknown'):
            sel = [x for x in ps if ro.get(x['pmid'], 'unknown') == o]
            if sel:
                v = [x['values'] for x in sel]
                out[o] = {'papers': len(sel), 'values': sum(v), 'mean': round(sum(v) / len(v), 1),
                          'median': statistics.median(v), 'papers_without_values': sum(1 for x in v if not x)}
        return out

    routes = collections.Counter(x['text_source'] or '(none recorded)' for x in per)
    out = {'what': 'papers new to CatLog when the Europe PMC searches ran, read by CatLog by this snapshot',
           'paper_set': SET or 'every paper of the two lists whose read had finished at this snapshot',
           'snapshot': {'built': time.strftime('%Y-%m-%d %H:%M'), 'read_from': f'git {REF}' if REF else 'working tree',
                        'git': head, 'sha256': stamp},
           'lists': lists,
           'queue': {name: dict(collections.Counter(queue[p]['status'] if p in queue else 'not queued'
                                                    for p in list_of if list_of[p] == name)) for name, *_ in LISTS},
           'all': block(per),
           'by_list': {name: block([x for x in per if x['list'] == name]) for name, *_ in LISTS},
           'by_tier': {t: block([x for x in per if x['tier'] == t]) for _, _, _, ts in LISTS for t in ts},
           'reading_order': {name: order([x for x in per if x['list'] == name]) for name, *_ in LISTS},
           'text_route': {'open_access': {k: routes[k] for k in OPEN if routes[k]},
                          'subscription': {k: n for k, n in routes.items() if k not in OPEN},
                          'note': 'open_access: Europe PMC XML, PMC Cloud, OpenAlex; subscription: the Elsevier API '
                                  "and browser downloads, both through Iowa State University's subscriptions on its "
                                  'network (DOWNLOADS.md)'}}

    in_table = [x for x in per if x['in_database_table']]
    compared = lambda r: r.get('unit') not in catlog_mass() and (r.get('value') or 0) > 0
    out['catalog'] = {
        'values': len(cat), 'censored_values': len(bounds),
        'share_of_values_from_these_papers': round(out['all']['values'] / len(cat), 4),
        'set_papers_in_database_table': len(in_table),
        'their_values': sum(x['values'] for x in in_table),
        'values_whose_paper_the_table_lacks': sum(1 for r in cat if r['pmid'] not in db_papers),
        'of_those_from_these_papers': sum(x['values'] for x in per if not x['in_database_table']),
        'fig3c_new_a': {
            'values': sum(1 for r in cat if r['pmid'] not in db_papers and compared(r)),
            'papers': len({r['pmid'] for r in cat if r['pmid'] not in db_papers and compared(r)}),
            'of_those_from_these_papers': sum(1 for x in per if not x['in_database_table']
                                              for r in rows_of.get(x['pmid'], []) if compared(r)),
            'note': "tools/dbcompare.py classify(): a value whose paper has no line in the table is NEW_a, except a "
                    "value over a mass concentration (mg/mL Km, mL mg^-1 s^-1 kcat/Km), which is NO_VALUE (not "
                    "compared); so Fig. 3c's NEW_a at an export of this snapshot should equal 'values'"},
        'note': "the table is CatLog's copy of the databases (sources/db_values.tsv: BRENDA 2026.1, SABIO-RK, OED, "
                'SKiD, UniProt 2026_03, STRENDA DB), built 14 Oct 2026 and not rebuilt since; UniProt joined it after '
                'the kcat search had run'}

    if not REF:
        changed = [rel for rel in TRACKED if sha_file(os.path.join(ROOT, rel)) != stamp[rel]]
        if changed:
            sys.exit(f'changed while this ran: {", ".join(changed)}: run it again')
    with open(os.path.join(OUT, 'numbers.json'), 'w') as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    cols = ['pmid', 'list', 'tier', 'status', 'text_source', 'first_added', 'values', 'kcat', 'Km', 'kcat/Km',
            'mass_concentration_values', 'records', 'censored', 'in_database_table']
    with open(os.path.join(OUT, 'papers.tsv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter='\t')
        w.writeheader()
        w.writerows(per)
    a = out['all']
    print(f"{a['papers_read']:,} papers read from the two lists, {a['papers_with_values']:,} with values: "
          f"{a['values']:,} values in {a['records']:,} records, {a['censored_values']:,} censored values; "
          f"{out['catalog']['share_of_values_from_these_papers']:.1%} of the catalogue's {len(cat):,} values "
          f"({out['snapshot']['read_from']} {head}; {time.time() - t0:.0f} s) -> {OUT}")


def catlog_mass():
    return set(catlog.MASS_UNIT.values()) if hasattr(catlog, 'MASS_UNIT') else {'mg/mL', 'mL mg^-1 s^-1'}


if __name__ == '__main__':
    main()
