#!/usr/bin/env python3
"""Papers with kinetics that NO database cites: a literature search in Europe PMC (free REST API, no key).

The databases (BRENDA, SABIO-RK, OED, ...) lag the literature by years: of the papers this search finds, 20-39% of
those published before 2015 are already known to CatLog, but only 8% of 2020-2026 ones (2026-10-13). This finds the rest.

Search (PubMed papers, reviews left out; Europe PMC searches full text for open-access papers, abstracts for the rest):
  ALL      (kcat OR "k cat" OR "turnover number") AND (Km OR "K m" OR Michaelis)
  TABLE    kcat / "k cat" / "turnover number" inside a table (full text only)
  ABSTRACT the ALL terms inside the abstract
Each paper gets a tier: table > abstract > body (body = only in the body text). A 36-paper sample on 2026-10-13
(12 per tier, open access, read by hand) found the paper's own measured kcat/Km values in 10/12, 10/12 and 6/12;
`expected_values` (table 15, abstract 5, body 2: share with values x a typical count) orders them in catlog.priority().

Left out: every PMID or DOI CatLog already knows (queue, coverage.tsv, every config.json source, the database table,
no-PMID references, the old library, earlier discovered_* lists, so a rerun adds only new papers) and titles that
name a non-enzyme catalyst (nanozyme, "peroxidase-like", enzyme mimic: 307 papers on 2026-10-13).

Writes sources/discovered_europepmc_<YYYYMMDD>.txt (header + PMIDs, best tier and newest first: a config.json source)
and .tsv (pmid, tier, expected_values, year, access, pmcid, doi, journal, title). access = how the free routes will
likely get it: oa_epmc (Europe PMC XML), pmc_not_oa (PMC Cloud for author manuscripts, else lane pmc), elsevier
(Elsevier API on campus), other (OpenAlex/LinkOut, else a download), no_doi.
Usage: python3 tools/discover_europepmc.py      (about 5 minutes; only when the user asks, then tools/coverage.py, catlog.py more)

Km mode (`km`, the user 2026-11-09: read AFTER the current queue): papers that print Km but no kcat. Same scope, known
papers and non-enzyme titles left out, plus `NOT (kcat OR "k cat" OR "turnover number")`. A bare Km matches kilometres
(941k papers), so every tier needs Michaelis context (KIN: Vmax, "maximal velocity", Michaelis, "catalytic efficiency",
"kinetic parameters" ...). Tiers km_table (Km/Michaelis in a table + KIN anywhere) > km_abstract (Km/Michaelis and
enzyme/substrate/KIN words in the abstract) > km_body (Km/Michaelis + KIN anywhere). Hand check 2026-11-09
(work/discovery_km/REPORT.md: 36 open-access papers per tier, two blind checkers each, 108/108 agreed): the paper's own
enzyme Km numbers in 50%, 47%, 17%, 2.8, 0.8 and 0.2 Km values per paper (the catalog holds ~31 per paper read), so
`expected_values` is 3, 1, 0 and `later` = 1: catlog.priority() puts these after every other paper and `more` queues
them only once nothing else is left to read. `flag` marks titles of transport/uptake or pharmacokinetic papers (7 of 7
such abstract-tier papers were not enzyme kinetics, 3 of 11 elsewhere were): expected_values 0, never left out.
Writes sources/discovered_km_<YYYYMMDD>.txt/.tsv (+ later, flag columns). About an hour (the km_body query pages 89k hits).
Usage: python3 tools/discover_europepmc.py km [--hits DIR]   (--hits: reuse a run's raw hits, DIR/hits_<query>.json)
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}
SEARCH = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
TERMS = '(kcat OR "k cat" OR "turnover number") AND (Km OR "K m" OR Michaelis)'
SCOPE = 'SRC:MED AND NOT PUB_TYPE:review'
QUERIES = {
    'all': f'{TERMS} AND {SCOPE}',
    'table': f'(TABLE:kcat OR TABLE:"k cat" OR TABLE:"turnover number") AND {SCOPE}',
    'abstract': f'ABSTRACT:(kcat OR "k cat" OR "turnover number") AND ABSTRACT:(Km OR "K m" OR Michaelis) AND {SCOPE}',
}
EXPECTED = {'table': 15, 'abstract': 5, 'body': 2}
NOT_ENZYME = re.compile(r'(?i)nanozyme|(peroxidase|oxidase|catalase|phosphatase|esterase|laccase|nuclease)[- ]like'
                        r'|enzyme[- ]mimic|mimetic|artificial enzyme|catecholase')
ELSEVIER = ('10.1016/', '10.1006/', '10.1053/', '10.1124/', '10.1074/', '10.1194/')  # as tools/fetch.py

KM = '(Km OR "K m" OR Michaelis)'
KIN = ('Vmax OR "V max" OR "maximal velocity" OR "maximum velocity" OR "maximal rate" OR Michaelis'
       ' OR "catalytic efficiency" OR "kinetic parameters"')
NO_KCAT = 'NOT (kcat OR "k cat" OR "turnover number")'
KM_QUERIES = {
    'table': f'(TABLE:Km OR TABLE:"K m" OR TABLE:Michaelis) AND ({KIN}) AND {NO_KCAT} AND {SCOPE}',
    'abstract': f'ABSTRACT:{KM} AND ABSTRACT:(enzyme OR enzymes OR enzymatic OR substrate OR substrates OR {KIN})'
                f' AND {NO_KCAT} AND {SCOPE}',
    'all': f'{KM} AND ({KIN}) AND {NO_KCAT} AND {SCOPE}',
}
KM_EXPECTED = {'km_table': 3, 'km_abstract': 1, 'km_body': 0}
NOISE = re.compile(r'(?i)(?P<transport>transporter|symporter|antiporter|exchanger\b|permease|\buptake\b|\btransport\b'
                   r'|\befflux\b|\binflux\b|\bchannels?\b|carrier-mediated)'
                   r'|(?P<pharmacokinetic>pharmacokinetic|\bPBPK\b|physiologically[- ]based|drug[- ]drug interaction'
                   r'|\bdosing\b|\bdose\b)')
SEARCHES = {  # kind -> list name, queries, tier names (table, abstract, body), expected values per tier
    'kcat': ('discovered_europepmc', QUERIES, ('table', 'abstract', 'body'), EXPECTED),
    'km': ('discovered_km', KM_QUERIES, ('km_table', 'km_abstract', 'km_body'), KM_EXPECTED),
}


def harvest(query):
    """Every hit of one query (lite records), 1,000 per page by cursorMark, politely paced."""
    cursor, out = '*', []
    while True:
        url = f'{SEARCH}?format=json&resultType=lite&pageSize=1000&cursorMark={urllib.parse.quote(cursor)}&query={urllib.parse.quote(query)}'
        for attempt in range(12):  # Europe PMC and the network drop out for minutes at a time (2026-10-13: DNS, timeouts)
            try:
                d = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read())
                break
            except Exception as e:
                print(f'  retry ({e})', file=sys.stderr); time.sleep(min(120, 10 * (attempt + 1)))
        else:
            sys.exit('Europe PMC search keeps failing; nothing written')
        rows = d.get('resultList', {}).get('result', [])
        out += rows
        if not rows or not d.get('nextCursorMark') or d['nextCursorMark'] == cursor:
            if len(out) < 0.995 * d.get('hitCount', 0):  # the index moves while it pages: a few hits come or go
                sys.exit(f'got {len(out)} of {d["hitCount"]} hits; nothing written')
            return out
        cursor = d['nextCursorMark']
        time.sleep(0.4)


def known():
    """PMIDs and DOIs CatLog already has anywhere."""
    pm, doi = set(), set()
    for r in csv.DictReader(open(ROOT / 'papers.tsv'), delimiter='\t'):
        pm.add(r['pmid']); doi.add((r.get('doi') or '').lower().strip())
    lists = json.loads((ROOT / 'config.json').read_text())['sources'] + ['sources/cited_not_queued.txt']
    for src in lists:
        if (ROOT / src).exists():
            pm |= {x.strip() for x in (ROOT / src).read_text().splitlines() if not x.startswith('#')}
    for name, col in (('sources/coverage.tsv', 0), ('sources/db_values.tsv', 1), ('library.tsv', 0)):
        if (ROOT / name).exists():  # db_values rows of a source that does not feed the queue (coverage.QUEUE_SKIP) don't count
            pm |= {f[col] for f in (l.split('\t', col + 1) for l in open(ROOT / name))
                   if len(f) > col and not (col == 1 and f[0] == 'UniProt')}
    for r in csv.DictReader(open(ROOT / 'sources' / 'nopmid_refs.tsv'), delimiter='\t'):
        pm.add(r.get('pmid') or ''); doi.add((r.get('doi') or '').lower().strip())
    for p in (ROOT / 'sources').glob('discovered_*.tsv'):
        for r in csv.DictReader((l for l in open(p) if not l.startswith('#')), delimiter='\t'):
            pm.add(r['pmid']); doi.add((r.get('doi') or '').lower().strip())
    if (ROOT / 'sources' / 'holdout_locked.txt').exists():  # the method paper's test set (catlog.locked())
        pm |= {w for l in (ROOT / 'sources' / 'holdout_locked.txt').read_text().splitlines() if not l.startswith('#') for w in l.split()}
    pm.discard(''); doi.discard('')
    return pm, doi


def access(r):
    if r.get('isOpenAccess') == 'Y' and r.get('pmcid'):
        return 'oa_epmc'
    if r.get('pmcid'):
        return 'pmc_not_oa'
    d = (r.get('doi') or '').lower()
    return 'elsevier' if d.startswith(ELSEVIER) else 'other' if d else 'no_doi'


def main(kind='kcat', hits_dir=None):
    name, queries, tier_names, expected = SEARCHES[kind]
    day = time.strftime('%Y%m%d')
    hits = {}
    for q_name, q in queries.items():
        if hits_dir:  # a run's raw hits (lite records), e.g. work/discovery_km/hits_<query>.json; dated by that run
            f = Path(hits_dir) / f'hits_{q_name}.json'
            rows, day = json.load(open(f)), time.strftime('%Y%m%d', time.localtime(f.stat().st_mtime))
        else:
            rows = harvest(q)
        print(f'{q_name}: {len(rows):,} hits', file=sys.stderr)
        hits[q_name] = {r['pmid']: r for r in rows if r.get('pmid')}
    every = {**hits['table'], **hits['abstract'], **hits['all']}
    pm, doi = known()
    new = {p: r for p, r in every.items() if p not in pm and (r.get('doi') or '').lower() not in doi}
    not_enzyme = {p for p, r in new.items() if NOT_ENZYME.search(r.get('title') or '')}
    rows = []
    for p, r in new.items():
        if p in not_enzyme:
            continue
        tier = tier_names[0] if p in hits['table'] else tier_names[1] if p in hits['abstract'] else tier_names[2]
        title = re.sub(r'\s+', ' ', r.get('title', ''))
        row = {'pmid': p, 'tier': tier, 'expected_values': expected[tier]}
        if kind == 'km':
            m = NOISE.search(title)
            flag = m.lastgroup if m else ''
            row.update({'expected_values': 0 if flag else expected[tier], 'later': 1, 'flag': flag})
        row.update({'year': r.get('pubYear', ''), 'access': access(r), 'pmcid': r.get('pmcid', ''), 'doi': r.get('doi', ''),
                    'journal': r.get('journalTitle', ''), 'title': title[:300]})
        rows.append(row)
    rows.sort(key=lambda r: (-r['expected_values'], tier_names.index(r['tier']), -int(r['year'] or 0), r['pmid']))
    from collections import Counter
    tiers, acc = Counter(r['tier'] for r in rows), Counter(r['access'] for r in rows)
    flags = Counter(r.get('flag') for r in rows if r.get('flag'))
    base = ROOT / 'sources' / f'{name}_{day}'
    with open(f'{base}.tsv.tmp', 'w') as f:  # catlog.priority() reads it while the batch loop runs: replace in one step
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['pmid'], delimiter='\t', lineterminator='\n')
        w.writeheader(); w.writerows(rows)
    Path(f'{base}.tsv.tmp').replace(f'{base}.tsv')
    what = ('Papers with kinetics that no database cites' if kind == 'kcat' else
            'Papers that print Km but no kcat (Km mode; read after the current queue, the user 2026-11-09)')
    head = [f'# {what}, found by tools/discover_europepmc.py on {day[:4]}-{day[4:6]}-{day[6:]}',
            '# (Europe PMC REST search; full text for PMC papers, abstracts for the rest; PubMed papers, no reviews).',
            *(f'#   {k}: {q}' for k, q in queries.items()),
            f'# {len(every):,} papers found; {len(every) - len(new):,} already known to CatLog (queue, coverage.tsv, config.json',
            f'# sources, database values, no-PMID references, library, earlier discovered lists); {len(not_enzyme):,} non-enzyme',
            f'# catalysts left out (nanozyme, "-like" activity, mimic). {len(rows):,} listed, most expected values first, newest first:',
            '#   ' + ', '.join(f'{t} {tiers[t]:,} (expected_values {expected[t]})' for t in tier_names),
            '#   likely route: ' + ', '.join(f'{a} {n:,}' for a, n in acc.most_common()),
            *([f'#   title flags (expected_values 0, read last): ' + ', '.join(f'{k} {n:,}' for k, n in flags.most_common())] if flags else []),
            f'# Details per paper: {base.name}.tsv. Read order: catlog.priority() uses expected_values where no database cites a paper'
            + ('; `later` papers come after every other paper.' if kind == 'km' else '.')]
    Path(f'{base}.txt').write_text('\n'.join(head) + '\n' + ''.join(r['pmid'] + '\n' for r in rows))
    print('\n'.join(head[len(queries) + 2:]))
    print(f'wrote {base.name}.txt and .tsv; next: add it to config.json "sources" if new, then tools/coverage.py and catlog.py more')


if __name__ == '__main__':
    a = sys.argv[1:]
    kind = a.pop(0) if a and a[0] in SEARCHES else 'kcat'
    main(kind, a[a.index('--hits') + 1] if '--hits' in a else None)
