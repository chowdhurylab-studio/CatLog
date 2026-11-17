#!/usr/bin/env python3
"""Papers BRENDA cites without a PMID: journals PubMed does not index, book chapters, or a PMID BRENDA never linked.

  python3 tools/nopmid.py extract   sources/nopmid_refs.tsv: one row per distinct reference with numeric
                                    kcat/Km/kcat-Km values (title, authors, journal, year, volume, pages, values)
  python3 tools/nopmid.py pmids     find a PMID: NCBI ECitMatch (journal, year, volume, first page, first author),
                                    then a PubMed title search; a hit is kept only when PubMed's own title and year
                                    agree with BRENDA's (pmid_how says which route and the title score)
  python3 tools/nopmid.py dois      the rest: a DOI from Crossref (title, year and first page or volume must agree);
                                    a DOI that Europe PMC knows under a PMID becomes that PMID
  python3 tools/nopmid.py ids       paper_id = the PMID, else a stand-in NP + 8 hex for a paper with a DOI (set once,
                                    never recomputed); sources/nopmid_ids.txt lists them, most values first
  python3 tools/nopmid.py recheck   re-validate PubMed matches with the current rules (run after changing them)
  python3 tools/nopmid.py stats

Re-runs keep finished rows (resumable); every lookup is paced (NCBI 3/s without a key, Crossref polite pool)."""
import csv, hashlib, json, os, re, socket, sys, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'sources' / 'nopmid_refs.tsv'
socket.setdefaulttimeout(90)  # a sleeping laptop once left a lookup hanging for 20 h
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}
COLS = ['key', 'paper_id', 'title', 'authors', 'journal', 'year', 'vol', 'pages', 'values', 'ecs', 'brenda_refs',
        'pmid', 'pmid_how', 'doi', 'doi_how', 'crossref_title']
IDS = ROOT / 'sources' / 'nopmid_ids.txt'  # in config.json sources: `catlog.py more` queues them
STOP = set('with from that this their which into using during between other study analysis role novel new the and '
           'for its are was were has have been'.split())
GREEK = {'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta', 'ε': 'epsilon', 'κ': 'kappa', 'λ': 'lambda',
         'ω': 'omega', 'μ': 'mu'}


def words(s):
    s = unicodedata.normalize('NFKC', s or '').lower()
    for g, name in GREEK.items():
        s = s.replace(g, name)
    s = re.sub(r'<[^>]+>', ' ', s)  # Crossref titles carry <i>, <sub>
    return {w for w in re.findall(r'[a-z0-9]+', s) if len(w) > 2 and w not in STOP}


SHORT_STOP = set('a an as at by in is it of on or to we'.split())


def shorts(s):
    """One- and two-character tokens that name things: cathepsin B vs L, type I vs II, kinase 2 vs 3."""
    s = unicodedata.normalize('NFKC', re.sub(r'<[^>]+>', ' ', s or '')).lower()
    return {w for w in re.findall(r'[a-z0-9]+', s) if len(w) <= 2 and w not in SHORT_STOP}


def title_score(a, b):
    """Shared content words over the longer title's words: 1.0 = same words."""
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(len(wa), len(wb)) if wa and wb else 0.0


def names_agree(a, b):
    """No conflicting short naming tokens ('cathepsin B' vs 'cathepsin L' share every long word). Only asked of a
    match that has nothing else (no shared volume or page): incidental tokens ('Co-A', 'D-b-', 'E.') differ often."""
    sa, sb = shorts(a), shorts(b)
    return not (sa and sb and sa != sb)


def lead_num(v):
    m = re.match(r'\s*(\d+)', str(v or ''))
    return m.group(1) if m else ''


def same_citation(r, summ):
    """BRENDA's volume or first page equals PubMed's (leading numbers: '71 Pt C' = 71, 'S101' ~ 101 is not taken)."""
    fp = first_page(r['pages'])
    return bool(fp and first_page(summ.get('pages', '')) == fp) or bool(lead_num(r['vol']) and lead_num(summ.get('volume')) == lead_num(r['vol']))


def first_page(pages):
    m = re.match(r'\s*([A-Za-z]?\d+)', pages or '')
    return m.group(1) if m else ''


def key_of(title, year, pages):
    return 'B' + hashlib.sha1(f"{' '.join(sorted(words(title)))}|{year}|{first_page(pages)}".encode()).hexdigest()[:10]


def get(url, timeout=60, tries=4):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                raise
            time.sleep(3 * (i + 1) + (10 if e.code == 429 else 0))
        except Exception:
            time.sleep(3 * (i + 1))
    raise RuntimeError(f'lookup failed: {url[:120]}')


def load():
    if not OUT.exists():
        return []
    with open(OUT) as f:
        return [{c: r.get(c) or '' for c in COLS} for r in csv.DictReader(f, delimiter='\t')]  # older files lack columns


def save(rows):
    tmp = OUT.with_suffix('.tmp')
    with open(tmp, 'w', newline='') as f:
        w = csv.DictWriter(f, COLS, delimiter='\t', extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    tmp.replace(OUT)


# ---------- extract ----------

def cmd_extract():
    sys.path.insert(0, str(ROOT / 'tools'))
    import brenda_values as bv
    old = {r['key']: r for r in load()}
    refs = {}
    for ec, entry in bv.entries():
        rs = entry.get('reference') if isinstance(entry.get('reference'), dict) else {}
        for field in bv.FIELDS:
            for it in entry.get(field) or []:
                if not isinstance(it, dict):
                    continue
                head = str(it.get('value') or '').split('{')[0].strip()
                if not re.fullmatch(r'\d+(?:\.\d+)?(?:[eE][-+]?\d+)?', head) or float(head) <= 0:
                    continue
                for rid in it.get('references') or []:
                    ref = rs.get(str(rid)) or {}
                    if str(ref.get('pmid') or '').strip().strip('0').isdigit() or not ref.get('title'):
                        continue
                    k = key_of(ref['title'], ref.get('year'), ref.get('pages'))
                    r = refs.setdefault(k, {
                        'key': k, 'title': ' '.join(str(ref['title']).split()), 'authors': '; '.join(ref.get('authors') or []),
                        'journal': ' '.join(str(ref.get('journal') or '').split()), 'year': str(ref.get('year') or ''),
                        'vol': str(ref.get('vol') or ''), 'pages': str(ref.get('pages') or ''), 'values': 0,
                        'ecs': set(), 'brenda_refs': set()})
                    r['values'] += 1
                    r['ecs'].add(ec)
                    r['brenda_refs'].add(f'{ec}#{rid}')
    rows = []
    for k, r in sorted(refs.items(), key=lambda x: -x[1]['values']):
        r['ecs'] = ' '.join(sorted(r['ecs']))
        r['brenda_refs'] = ' '.join(sorted(r['brenda_refs']))
        for c in ('paper_id', 'pmid', 'pmid_how', 'doi', 'doi_how', 'crossref_title'):
            r[c] = (old.get(k) or {}).get(c, '')
        rows.append(r)
    save(rows)
    print(f'{len(rows)} references without a PMID, {sum(r["values"] for r in rows)} values -> {OUT}')


# ---------- PubMed ----------

def esummary(pmids):
    out = {}
    for i in range(0, len(pmids), 200):
        d = json.loads(get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json'
                           '&tool=catlog' + (f'&email={CONTACT}' if CONTACT else '') + '&id=' + ','.join(pmids[i:i + 200])))['result']
        for p in d.get('uids', []):
            out[p] = d[p]
        time.sleep(0.4)
    return out


def check(r, summ):
    """(ok, score) for a PubMed record against a BRENDA reference: title words and year must agree."""
    if not summ or summ.get('error'):
        return False, 0.0
    titles = [summ.get('title', '')] + ([summ['vernaculartitle']] if summ.get('vernaculartitle') else [])
    score = max(title_score(r['title'], t) for t in titles)
    y = re.match(r'\d{4}', summ.get('pubdate') or summ.get('epubdate') or '')
    year_ok = not r['year'] or not y or abs(int(y.group(0)) - int(r['year'])) <= 1
    return score >= 0.7 and year_ok, score


def ecitmatch(batch):
    lines = []
    for r in batch:
        au = (r['authors'].split(';')[0] if r['authors'] else '').strip()
        m = re.match(r'([^,]+),\s*(.*)', au)
        au = f"{m.group(1)} {re.sub(r'[^A-Za-z]', '', m.group(2))}" if m else au
        j = re.sub(r'\s+', ' ', r['journal'].replace('.', ' ')).strip()
        lines.append('|'.join([j, r['year'], r['vol'], first_page(r['pages']), au, r['key'], '']))
    url = ('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/ecitmatch.cgi?db=pubmed&retmode=xml'
           '&tool=catlog' + (f'&email={CONTACT}' if CONTACT else '') + '&bdata=' + urllib.parse.quote('\r'.join(lines)))
    found = {}
    for line in get(url).decode(errors='replace').splitlines():
        f = line.split('|')
        if len(f) >= 7 and f[6].strip().isdigit():
            found[f[5]] = f[6].strip()
    return found


def title_search(r):
    ws = [w for w in re.findall(r'[A-Za-z0-9]+', r['title']) if len(w) > 3 and w.lower() not in STOP][:12]
    if len(ws) < 3:
        return []
    term = ' AND '.join(f'{w}[ti]' for w in ws) + (f' AND {r["year"]}[dp]' if r['year'] else '')
    d = json.loads(get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=5'
                       '&tool=catlog' + (f'&email={CONTACT}' if CONTACT else '') + '&term=' + urllib.parse.quote(term)))
    return d.get('esearchresult', {}).get('idlist', [])


def cmd_pmids():
    rows = load()
    todo = [r for r in rows if not r['pmid_how']]
    print(f'{len(todo)} references to look up in PubMed', flush=True)
    for i in range(0, len(todo), 20):  # ECitMatch: several citations per request (100 makes the URL too long)
        batch = todo[i:i + 20]
        try:
            hits = ecitmatch(batch)
        except Exception:
            continue  # this batch falls through to the title search
        summ = esummary(sorted(set(hits.values())))
        for r in batch:
            p = hits.get(r['key'])
            if p:
                ok, score = check(r, summ.get(p))
                if ok:
                    r['pmid'], r['pmid_how'] = p, f'ecitmatch title {score:.2f}'
            if not r['pmid']:
                r['pmid_how'] = 'ecitmatch: none'  # a restart goes straight to the title search
        time.sleep(0.4)
        if i % 200 == 0:
            save(rows)
            print(f'  ecitmatch {min(i + 20, len(todo))}/{len(todo)}: {sum(1 for r in rows if r["pmid"])} with a PMID', flush=True)
    rest = [r for r in rows if not r['pmid'] and r['pmid_how'] in ('', 'ecitmatch: none')]
    for n, r in enumerate(rest, 1):
        try:
            ids = title_search(r)
        except Exception:
            continue  # stays unlooked (pmid_how empty): the next run retries it
        time.sleep(0.35)
        good = []
        if ids:
            summ = esummary(ids)
            good = [(check(r, summ.get(p))[1], p) for p in ids if check(r, summ.get(p))[0]
                    and (same_citation(r, summ.get(p)) or check(r, summ.get(p))[1] >= 0.95
                         and names_agree(r['title'], summ[p].get('title', '')))]  # a title alone must be exact
        if len(good) == 1 or (good and sorted(good)[-1][0] - sorted(good)[-2][0] >= 0.15):
            score, p = max(good)
            r['pmid'], r['pmid_how'] = p, f'title search {score:.2f}'
        else:
            r['pmid_how'] = 'not in PubMed' if not good else f'ambiguous ({len(good)} PubMed matches)'
        if n % 50 == 0:
            save(rows)
            print(f'  title search {n}/{len(rest)}: {sum(1 for r in rows if r["pmid"])} with a PMID', flush=True)
    save(rows)
    cmd_stats()


# ---------- Crossref ----------

def crossref(r):
    q = f"{r['title']} {r['journal']} {r['year']}"
    flt = f"&filter=from-pub-date:{int(r['year']) - 1},until-pub-date:{int(r['year']) + 1}" if r['year'].isdigit() else ''
    d = json.loads(get('https://api.crossref.org/works?rows=5' + (f'&mailto={CONTACT}' if CONTACT else '') + ''
                       '&select=DOI,title,page,volume,issued,container-title&query.bibliographic='
                       + urllib.parse.quote(q) + flt))
    best = None
    for it in d.get('message', {}).get('items', []):
        score = max([title_score(r['title'], t) for t in it.get('title') or ['']])
        fp, page = first_page(r['pages']), str(it.get('page') or '')
        same_page = bool(fp) and first_page(page) == fp
        same_vol = bool(r['vol']) and str(it.get('volume') or '') == r['vol']
        agree = names_agree(r['title'], ' '.join(it.get('title') or ['']))
        if score >= 0.8 and (same_page or same_vol and agree) or score >= 0.95 and not fp and agree:
            if not best or (score, same_page) > (best[0], best[2] == 'page'):  # a page match beats a volume match
                best = (score, it['DOI'].lower(), 'page' if same_page else 'volume' if same_vol else 'title only',
                        ' '.join(re.sub(r'<[^>]+>', ' ', (it.get('title') or [''])[0]).split()))
    return best


def epmc_pmid(doi):
    d = json.loads(get('https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=lite&query='
                       + urllib.parse.quote(f'DOI:"{doi}"')))
    pm = [h.get('pmid') for h in d.get('resultList', {}).get('result', []) if h.get('pmid')]
    return pm[0] if len(set(pm)) == 1 else ''


def cmd_dois():
    rows = load()
    todo = [r for r in rows if not r['pmid'] and not r['doi_how']]
    print(f'{len(todo)} references to look up in Crossref', flush=True)
    for n, r in enumerate(todo, 1):
        try:
            best = crossref(r)
        except Exception:
            continue
        time.sleep(0.25)
        if best:
            score, doi, how, ctitle = best
            r['doi'], r['doi_how'], r['crossref_title'] = doi, f'crossref title {score:.2f} + {how}', ctitle
            try:
                p = epmc_pmid(doi)
            except Exception:
                p = ''
            if p:
                r['pmid'], r['pmid_how'] = p, f'DOI {doi} -> Europe PMC'
        else:
            r['doi_how'] = 'no confident Crossref match'
        if n % 50 == 0:
            save(rows)
            print(f'  crossref {n}/{len(todo)}: {sum(1 for r in rows if r["doi"])} with a DOI', flush=True)
    save(rows)
    cmd_stats()


def cmd_ids():
    """paper_id once per row: the PMID, else NP + 8 hex of the row key for a paper with a DOI. An id already given
    stays (texts, reads and catalog rows hang on it), even if a PMID turns up later (noted in pmid_how)."""
    rows = load()
    queued = {}
    with open(ROOT / 'papers.tsv') as f:
        for q in csv.DictReader(f, delimiter='\t'):
            if q.get('doi'):
                queued[q['doi'].lower()] = q['pmid']
    held = {r['doi'].lower(): r['paper_id'] for r in rows if r['paper_id'] and r['doi']}
    for r in rows:
        if r['paper_id']:
            continue
        if r['pmid']:
            r['paper_id'] = r['pmid']
        elif r['doi']:
            other = held.get(r['doi'].lower()) or queued.get(r['doi'].lower())
            if other:  # one paper, one id: two references on one DOI, or the DOI is already queued under a PMID
                r['doi_how'] = f'DOI shared with {other}: not given a second id'
                continue
            r['paper_id'] = 'NP' + r['key'][1:9].upper()
            held[r['doi'].lower()] = r['paper_id']
    ids = [r['paper_id'] for r in sorted(rows, key=lambda r: -int(r['values'])) if r['paper_id']]
    nps = [i for i in ids if i.startswith('NP')]
    assert len(nps) == len(set(nps)), 'stand-in id clash: two references hash to one id'
    save(rows)
    IDS.write_text('\n'.join(dict.fromkeys(ids)) + '\n')
    print(f'{len(set(ids))} ids -> {IDS} ({sum(i.startswith("NP") for i in set(ids))} stand-ins)')


def cmd_recheck():
    """Re-validate every PubMed match with the current rules (short naming tokens; a title-search hit needs the same
    volume or first page, or an essentially exact title). A failed match is cleared and goes to the Crossref step."""
    rows = load()
    got = [r for r in rows if r['pmid'] and not r['paper_id'].startswith('NP')]
    summ = esummary(sorted({r['pmid'] for r in got}))
    dropped = 0
    for r in got:
        ok, score = check(r, summ.get(r['pmid']))
        if r['pmid_how'].startswith('title search'):
            sm = summ.get(r['pmid'], {})
            ok = ok and (same_citation(r, sm) or score >= 0.95 and names_agree(r['title'], sm.get('title', '')))
        if not ok:
            if r['paper_id'] == r['pmid']:
                r['paper_id'] = ''
            r['pmid_how'] = f"rejected on recheck: PMID {r['pmid']} ({r['pmid_how']}; now {score:.2f})"
            r['pmid'] = ''
            dropped += 1
    save(rows)
    print(f'{dropped} of {len(got)} PubMed matches rejected on recheck')
    cmd_stats()


def cmd_stats():
    rows = load()
    v = lambda rs: sum(int(r['values']) for r in rs)
    pm = [r for r in rows if r['pmid']]
    doi = [r for r in rows if r['doi'] and not r['pmid']]
    none = [r for r in rows if not r['pmid'] and not r['doi']]
    print(f'{len(rows)} references ({v(rows)} values): PMID found {len(pm)} ({v(pm)} values); DOI only {len(doi)} '
          f'({v(doi)} values); neither {len(none)} ({v(none)} values)')


if __name__ == '__main__':
    {'extract': cmd_extract, 'pmids': cmd_pmids, 'dois': cmd_dois, 'ids': cmd_ids, 'recheck': cmd_recheck,
     'stats': cmd_stats}[sys.argv[1]]()
