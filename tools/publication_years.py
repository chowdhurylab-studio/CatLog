"""CatLog's values per publication year of the source paper, beside BRENDA's: the Stats figure "BRENDA vs CatLog values
per publication year" (round 16 brief section 1; the user approved the figure of work/brenda_lag_20261021/broad/) and the
site manifest's summary.publication_years, which `site build` writes (site_release.publication_years).

Counting, as work/brenda_lag_20261021/broad/catlog_by_year.py counts (tests check catlog_by_year gives its numbers),
with three changes so the figure compares like with like and gives the site's own total (round 16 review, 2026-10-21;
round 17, 2026-10-24): every catalog.jsonl row is one value (a kcat, Km or kcat/Km), dated by its paper's PubMed
publication year (NCBI esummary sortpubdate, else pubdate; its first four digits); a paper without a PubMed ID (a
stand-in NP..., catlog.STANDIN, always a paper BRENDA cites) is dated by BRENDA's reference year in
sources/nopmid_refs.tsv, the rule BRENDA's side uses for its references without a PubMed ID (catlog_by_year.py left them
out of every year: 4,880 values of 2000-2025 on 2026-10-21, up to 7% of a year); a Km or kcat/Km stored over a mass
concentration (units.MASS_UNIT: mg/mL, mL mg^-1 s^-1) is left out, as the site and its downloads leave it out of the mM
columns (577 values that day); and only the rows of the papers the site shows from CatLog count: papers.tsv status
`done` (the site data rule, site_release's module docstring), so a paper still reading, waiting for a supplement
(needs_supplement) or for a fuller copy (incomplete) counts once it is finished. `site build` passes the paper set its
records come from (site_release._v2_done: those done papers, less one the export has not caught yet), so the totals are
the values and papers of the site's records read from the paper (Stats' Quality, overview.from_paper: one proof line
per value). Before round 17 every catalog.jsonl row counted, and Stats gave a larger CatLog total here than in Quality.
Papers with neither date count in the totals only (catlog_values_without_year). as_of: the day the values were counted
(UTC); `site build` dates it by its snapshot's own day (the manifest's generated_at, UTC, as the page and the release
date the snapshot), which the exporter sets after the counting. BRENDA's side is fixed until a new BRENDA release:
sources/brenda_values_by_year_2026_1.tsv, copied from the approved figure's data with its provenance in the file's
header.

Cache: sources/ref/pubmed_years.jsonl, one NCBI answer per line ({uid, pubdate, sortpubdate}; a later line for the same
PMID wins). When it is missing or empty it is seeded once from the BRENDA lag analysis's caches (SEEDS, read only);
afterwards only PMIDs it does not hold are fetched (NCBI esummary, 200 per request, 0.4 s apart, 3 tries each). A failed
fetch never stops anything: the first request that fails three times ends the fetching, and its papers count as without
a year. A PMID NCBI answered without a date is not asked again (catlog_by_year.py asks again; NCBI gives the same).

  python3 tools/publication_years.py              summary.publication_years as JSON (fetches dates for new papers)
  python3 tools/publication_years.py --offline    the same from the cache only
"""
import csv, json, os, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from units import MASS_UNIT  # noqa: E402  (Km and kcat/Km over a mass concentration: not in the site's columns)

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path('sources') / 'ref' / 'pubmed_years.jsonl'  # under the root; sources/ref/ is git-ignored (a cache)
SEEDS = (Path('work') / 'brenda_lag_20261021' / 'cache' / 'ncbi_esummary.jsonl',  # under the root; read only
         Path('work') / 'brenda_lag_20261021' / 'broad' / 'pubmed_years_extra.jsonl')
BRENDA = Path('sources') / 'brenda_values_by_year_2026_1.tsv'
NOPMID = Path('sources') / 'nopmid_refs.tsv'  # BRENDA's references without a PMID: paper_id (the stand-in) and year
FIRST_YEAR, LAST_YEAR = 2000, 2025  # BRENDA 2026.1 lists no paper from 2026; CatLog's 2026 values go in the caption
ESUMMARY = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?'
BATCH, PAUSE, TRIES, TIMEOUT = 200, 0.4, 3, 30
DEFINITION = ('kcat, Km and kcat/Km values per publication year of the source paper, {first}-{last}. brenda_values: '
              '{release} (fixed until a new release; a value citing two papers counts under each, ranges count, '
              'references without a PubMed ID are dated by BRENDA\'s reference year). catlog_values: the values of the '
              'site\'s records read from the paper on as_of, the snapshot\'s day (kcat, Km and kcat/Km of the papers '
              'CatLog has finished, each read from the paper and checked against it; a paper still being read, or '
              'waiting for its supplement or a fuller copy, counts once it is finished, as everywhere on the site; a Km '
              'or kcat/Km per mass concentration, not in the site\'s columns, left out), each dated by its paper\'s '
              'PubMed publication year, a paper without a PubMed ID by BRENDA\'s reference year as on BRENDA\'s side; '
              'catlog_papers: the papers they come from. Values of papers with neither date count in the totals only '
              '(catlog_values_without_year); catlog_after_last_year and catlog_before_first_year: CatLog values from '
              'papers published after or before the compared years. brenda_papers: the BRENDA papers those values come '
              'from, each once in its year; brenda_papers_total: their sum over the compared years. CatLog reads first '
              'the papers the databases cite for the most values and also reads papers no database cites, so its line '
              'is no measure of how much of BRENDA it covers.')


def _fields(line):
    """(uid, year or None) of one cache line; None for a line that is not an NCBI answer."""
    try:
        r = json.loads(line)
    except ValueError:
        return None  # a cut-off last line (a killed write): that paper is fetched again
    if not isinstance(r, dict) or not r.get('uid'):
        return None
    y = str(r.get('sortpubdate') or r.get('pubdate') or '')[:4]
    return str(r['uid']), (int(y) if y.isdigit() else None)


def load_years(paths):
    """{PMID: year} from cache files in order (a later line for the same PMID wins when it has a year, as
    catlog_by_year.load_years reads them), and the set of PMIDs NCBI answered (with or without a date)."""
    year, answered = {}, set()
    for path in paths:
        if not Path(path).exists():
            continue
        with open(path) as fh:
            for line in fh:
                f = _fields(line) if line.strip() else None
                if f:
                    answered.add(f[0])
                    if f[1] is not None:
                        year[f[0]] = f[1]
    return year, answered


def seed(cache, seeds):
    """Write the cache from the seed files when it does not exist yet or is empty (NCBI's uid, pubdate and sortpubdate
    of each line, in order); the seed files are only read. Returns the lines written (0 when the cache holds answers)."""
    cache = Path(cache)
    if cache.exists() and cache.stat().st_size:
        return 0
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp, n = cache.with_name(cache.name + f'.tmp{os.getpid()}'), 0
    with open(tmp, 'w') as out:
        for path in seeds:
            if not Path(path).exists():
                continue
            with open(path) as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(r, dict) and r.get('uid'):
                        out.write(json.dumps({'uid': str(r['uid']), 'pubdate': r.get('pubdate'),
                                              'sortpubdate': r.get('sortpubdate')}) + '\n')
                        n += 1
    tmp.replace(cache)
    return n


def fetch(pmids, cache, urlopen=None, sleep=time.sleep, log=print):
    """PubMed dates for PMIDs the cache does not hold (NCBI esummary, BATCH per request, PAUSE apart), appended to the
    cache. Never raises: the first request that fails TRIES times ends the fetching (the network or NCBI is down), and
    the papers not fetched count as without a year. Returns the number of PMIDs NCBI answered."""
    urlopen = urlopen or urllib.request.urlopen
    pmids, got = sorted(set(pmids)), 0
    if not pmids:
        return 0
    try:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        out = open(cache, 'a')
    except OSError as e:
        log(f'publication years: cache not writable ({e}); {len(pmids)} papers count as without a year')
        return 0
    with out:
        for i in range(0, len(pmids), BATCH):
            chunk = pmids[i:i + BATCH]
            url = ESUMMARY + urllib.parse.urlencode({'db': 'pubmed', 'id': ','.join(chunk), 'retmode': 'json',
                                                     'tool': 'catlog_v2'})
            res = None
            for attempt in range(TRIES):
                try:
                    with urlopen(url, timeout=TIMEOUT) as r:
                        res = json.load(r)['result']
                    break
                except Exception:  # network, HTTP, a page that is not JSON: try again, then give up quietly
                    if attempt + 1 < TRIES:
                        sleep(3)
            if not isinstance(res, dict):
                log(f'publication years: NCBI did not answer; {len(pmids) - i} papers count as without a year this time')
                break
            for u in res.get('uids') or []:
                e = res.get(u) if isinstance(res.get(u), dict) else {}
                out.write(json.dumps({'uid': str(u), 'pubdate': e.get('pubdate'), 'sortpubdate': e.get('sortpubdate')}) + '\n')
                got += 1
            out.flush()
            if i + BATCH < len(pmids):
                sleep(PAUSE)
    return got


def done_papers(path):
    """The papers papers.tsv marks `done`, read as site_release._v2_done reads them: the papers whose values the site
    shows from CatLog (the site data rule). A missing papers.tsv is an error (site_release then leaves the figure out)."""
    with open(path) as fh:
        return {r['pmid'] for r in csv.DictReader(fh, delimiter='\t') if r['status'] == 'done'}


def catalog_pmids(path, site=False, papers=None):
    """The paper of every catalog.jsonl row (one row = one value, as `catlog.py status` counts them); with site=True
    only the values the site shows (a Km or kcat/Km stored over a mass concentration, units.MASS_UNIT, left out); with
    papers, only the rows of those papers (the site's: done_papers, or the set `site build` passes). A cut-off last line
    (another chat's add writing it now) is left out, as status leaves it out; any other bad line is an error."""
    out, mass = [], set(MASS_UNIT.values())
    with open(path) as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                if line.endswith('\n'):
                    raise ValueError(f'catalog.jsonl line {i} is not valid JSON')
                continue
            if not (site and row.get('unit') in mass) and (papers is None or str(row['pmid']) in papers):
                out.append(str(row['pmid']))
    return out


def standin_years(path):
    """{stand-in paper id: BRENDA's reference year} from sources/nopmid_refs.tsv (paper_id, year), the year BRENDA's
    side dates its references without a PubMed ID by. A stand-in whose references give two different years is left
    without one; a missing file gives none."""
    years = defaultdict(set)
    if not Path(path).exists():
        return {}
    with open(path, newline='') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            y = str(r.get('year') or '').strip()
            if r.get('paper_id') and y.isdigit() and len(y) == 4:
                years[r['paper_id'].strip()].add(int(y))
    return {p: next(iter(ys)) for p, ys in years.items() if len(ys) == 1}


def count(pmids, year):
    """(values per year, papers per year as sets, values without a year): catlog_by_year.main's counting."""
    values, papers, undated = Counter(), defaultdict(set), 0
    for p in pmids:
        y = year.get(p)
        if y is None:
            undated += 1
            continue
        values[y] += 1
        papers[y].add(p)
    return values, papers, undated


def brenda_by_year(path):
    """(release, {year: values}) from the BRENDA per-year file ('# release: BRENDA 2026.1' in its header)."""
    release, out = None, {}
    with open(path) as fh:
        for line in fh:
            if line.startswith('#'):
                if line[1:].strip().lower().startswith('release:'):
                    release = line.split(':', 1)[1].strip()
                continue
            f = line.rstrip('\n').split('\t')
            if len(f) >= 2 and f[0].strip().isdigit():
                out[int(f[0])] = int(float(f[1]))
    if not release or not out:
        raise ValueError(f'{path}: no release line or no years')
    return release, out


def brenda_papers_by_year(path):
    """{year: BRENDA papers} from the per-year file's brenda_papers column (added 2026-10-22); {} when the file has none."""
    out, col = {}, None
    with open(path) as fh:
        for line in fh:
            if line.startswith('#'):
                continue
            f = line.rstrip('\n').split('\t')
            if f[0].strip() == 'year':
                col = f.index('brenda_papers') if 'brenda_papers' in f else None
            elif col is not None and len(f) > col and f[0].strip().isdigit() and f[col].strip():
                out[int(f[0])] = int(float(f[col]))
    return out


def years_for(pmids, root=None, online=True, log=print):
    """{PMID: year} for these papers from the cache (seeded when missing), fetching the PMIDs it does not hold."""
    root = Path(root or ROOT)
    cache = root / CACHE
    n = seed(cache, [root / s for s in SEEDS])
    if n:
        log(f'publication years: cache seeded with {n:,} PubMed answers ({cache})')
    year, answered = load_years([cache])
    need = sorted({p for p in pmids if p.isdigit() and p not in answered})
    if need and online:
        log(f'publication years: fetching PubMed dates for {len(need):,} new papers')
        if fetch(need, cache, log=log):
            year, answered = load_years([cache])
    return year


def catlog_by_year(pmids, year, as_of):
    """The same object work/brenda_lag_20261021/broad/catlog_by_year.py writes (catlog_by_year.json), for checks."""
    values, papers, undated = count(pmids, year)
    return {'as_of': as_of, 'values': {str(k): v for k, v in sorted(values.items())},
            'papers': {str(k): len(v) for k, v in sorted(papers.items())},
            'total_values': len(pmids), 'total_papers': len(set(pmids)), 'values_without_year': undated}


def summary(root=None, online=True, log=print, papers=None, as_of=None):
    """summary.publication_years (round 16 brief section 1's data contract, with three additions: definition,
    catlog_papers_without_year and catlog_before_first_year, so the totals add up on the page; and, when the BRENDA
    file has them, brenda_papers per year and brenda_papers_total over the compared years, so the figure can give
    BRENDA's paper count beside CatLog's: round 16b quality review). Counts the values of the papers the site shows
    from CatLog: `papers` (site_release._v2_done's set, which `site build` passes), else papers.tsv's done papers.
    as_of: the day given (`site build` gives its snapshot's day), else today (UTC)."""
    root = Path(root or ROOT)
    catalog = root / 'catalog.jsonl'
    release, brenda = brenda_by_year(root / BRENDA)
    brenda_papers = brenda_papers_by_year(root / BRENDA)
    shown = {str(p) for p in papers} if papers is not None else done_papers(root / 'papers.tsv')
    as_of = as_of or time.strftime('%Y-%m-%d', time.gmtime())  # the snapshot's generated_at is UTC too
    pmids = catalog_pmids(catalog, site=True, papers=shown)
    year = years_for(pmids, root, online, log)
    standins = standin_years(root / NOPMID)  # dated as BRENDA dates its references without a PubMed ID
    year = {**year, **{p: standins[p] for p in set(pmids) if not p.isdigit() and p in standins}}
    values, papers, undated = count(pmids, year)
    first, last = max(FIRST_YEAR, min(brenda)), min(LAST_YEAR, max(brenda))

    def beyond(keep):
        ys = [y for y in values if keep(y)]
        return {'values': sum(values[y] for y in ys), 'papers': len(set().union(*(papers[y] for y in ys)))}
    with_papers = all(y in brenda_papers for y in range(first, last + 1))  # all compared years, or none
    return {'brenda_release': release, 'as_of': as_of, 'first_year': first, 'last_year': last,
            'years': [{'year': y, 'brenda_values': brenda.get(y),
                       **({'brenda_papers': brenda_papers[y]} if with_papers else {}), 'catlog_values': values.get(y, 0),
                       'catlog_papers': len(papers.get(y, ()))} for y in range(first, last + 1)],
            **({'brenda_papers_total': sum(brenda_papers[y] for y in range(first, last + 1))} if with_papers else {}),
            'catlog_values_total': len(pmids), 'catlog_papers_total': len(set(pmids)),
            'catlog_values_without_year': undated,
            'catlog_papers_without_year': len({p for p in pmids if p not in year}),
            'catlog_after_last_year': beyond(lambda y: y > last),
            'catlog_before_first_year': beyond(lambda y: y < first),
            'definition': DEFINITION.format(first=first, last=last, release=release)}


if __name__ == '__main__':
    args = sys.argv[1:]
    root = Path(args[args.index('--root') + 1]) if '--root' in args else ROOT
    print(json.dumps(summary(root, online='--offline' not in args, log=lambda m: print(m, file=sys.stderr)), indent=1))
