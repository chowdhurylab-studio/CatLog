#!/usr/bin/env python3
"""Which papers did we already do? One table over every source at once.

Writes sources/coverage.tsv: per PMID, how many values the databases cite (BRENDA + SABIO-RK + OED + SKiD + STRENDA
from sources/db_values.tsv, not UniProt kinetics: QUEUE_SKIP; and the old catalog's merged BRENDA / SABIO-RK / OED /
SKiD / UniProt rows), how many the OLD system certified (verified/corrected), how many v2 has verified, whether the
paper is on disk, its v2 queue status and, for papers no database cites that a literature search found
(sources/discovered_*.tsv, tools/discover_europepmc.py), the tier it found them in. Also writes
sources/cited_not_queued.txt: papers any source cites that are not in v2's queue yet (most values first).
`catlog.py next` uses coverage.tsv to read the papers that cite the most values first (never-certified first on ties).
Usage: python3 tools/coverage.py
"""
import re, csv, gzip, json, os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD_SNAPSHOT = Path(os.environ.get('REALKCAT_DIR') or ROOT / 'realkcat') / 'output/catlog-static-20261002a-webonly/data/catlog-enriched.889fbe06ec74.jsonl.gz'  # the earlier catalog (optional; README: settings)

# db_values.tsv sources that do not feed the queue (tools/discover_europepmc.py known() skips the same rows). Empty: the
# user said yes to UniProt-cited papers joining the queue (2026-10-14, with `catlog.py more 2000`).
QUEUE_SKIP = set()

# values each paper is cited for, across BRENDA + SABIO-RK + OED + ... (tools/db_values.py); BRENDA counts as fallback
brenda = Counter()
if (ROOT / 'sources' / 'db_values.tsv').exists():
    for l in open(ROOT / 'sources' / 'db_values.tsv'):
        f = l.split('\t', 2)
        if len(f) > 1 and f[0] not in QUEUE_SKIP and (f[1].isdigit() or re.fullmatch(r'NP[0-9A-F]{8}', f[1])):  # NP...: a paper with no PMID
            brenda[f[1]] += 1
else:
    brenda.update({l.split('\t')[0]: int(l.split('\t')[1]) for l in open(ROOT / 'sources' / 'brenda_pmids.tsv') if l[:1].isdigit()})

old_rows, old_cert, old_src = Counter(), Counter(), defaultdict(set)
if not OLD_SNAPSHOT.exists():
    print('the earlier catalog snapshot is not here (set REALKCAT_DIR): its rows are left out of coverage.tsv')
with (gzip.open(OLD_SNAPSHOT, 'rt') if OLD_SNAPSHOT.exists() else open(os.devnull)) as f:
    for line in f:
        r = json.loads(line)
        pmid = str(r.get('pubmed_id') or '').strip()
        if not pmid.isdigit():
            continue
        old_rows[pmid] += 1
        old_src[pmid].add(str(r.get('source_db') or '?'))
        if r.get('verification_status') in ('verified', 'corrected'):
            old_cert[pmid] += 1

v2 = Counter(json.loads(l)['pmid'] for l in open(ROOT / 'catalog.jsonl')) if (ROOT / 'catalog.jsonl').exists() else Counter()
queue = {r['pmid']: r['status'] for r in csv.DictReader(open(ROOT / 'papers.tsv'), delimiter='\t')}
disk = {l.split('\t')[0] for l in open(ROOT / 'library.tsv') if l[:1].isdigit()}
if (ROOT / 'papers').exists():
    disk |= {p.name.split('.')[0] for p in (ROOT / 'papers').glob('*.*')}

found = {}  # literature-search finds: pmid -> tier (where the paper prints kcat: table, abstract, body)
for p in sorted((ROOT / 'sources').glob('discovered_*.tsv')):
    found.update({r['pmid']: r['tier'] for r in csv.DictReader(open(p), delimiter='\t')})

pmids = set(brenda) | set(old_rows) | set(v2) | set(queue) | set(found)
with open(ROOT / 'sources' / 'coverage.tsv', 'w') as out:
    out.write('pmid\tdb_values\told_rows\told_certified\told_sources\tv2_rows\tv2_status\ton_disk\tdiscovered\n')
    for p in sorted(pmids, key=lambda p: -max(brenda.get(p, 0), old_rows[p])):
        out.write(f"{p}\t{brenda.get(p, 0)}\t{old_rows[p]}\t{old_cert[p]}\t{','.join(sorted(old_src[p]))}\t"
                  f"{v2[p]}\t{queue.get(p, 'not_queued')}\t{int(p in disk)}\t{found.get(p, '')}\n")

new = sorted((p for p in set(old_rows) | set(brenda) if p not in queue), key=lambda p: -max(brenda.get(p, 0), old_rows[p]))
(ROOT / 'sources' / 'cited_not_queued.txt').write_text(''.join(p + '\n' for p in new))

cited = pmids - set(found)  # a literature-search find is cited by no database
done_before = {p for p in cited if old_cert[p]}
print(f'papers cited by any source: {len(cited):,}')
print(f'  old system certified something from: {len(done_before):,} papers ({sum(old_cert.values()):,} certified rows)')
print(f'  never certified by anyone: {len(cited - done_before):,} papers')
print(f'  on disk: {len(disk & cited):,} (never certified and on disk: {len((disk & cited) - done_before):,})')
if found:
    print(f'  found by literature search, cited by no database: {len(found):,} papers ({sum(p in queue for p in found):,} queued; '
          + ', '.join(f'{t} {n:,}' for t, n in Counter(found.values()).most_common()) + ')')
print(f'  cited but not in the v2 queue yet: {len(new):,} papers (sources/cited_not_queued.txt; `catlog.py more` adds them)')
src = Counter(s for p in old_src for s in old_src[p])
print('  old catalog papers by database: ' + ', '.join(f'{k} {v:,}' for k, v in src.most_common()))
