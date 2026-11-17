#!/usr/bin/env python3
"""CatLog v2: get paper -> read -> verify -> add -> get more.

  python catlog.py status            the only counter: values, measurements, papers, what waits on you, last days
  python catlog.py report            the same, shown to the user; resets the 'papers read since the last report' count
  python catlog.py next N            claim the next N papers with text, biggest BRENDA papers first (prints PMIDs)
  python catlog.py get PMID          write texts/PMID.txt (local copy, Europe PMC, Elsevier API, OpenAlex; OCR)
  python catlog.py fetch N           try to get text for the next N todo papers without claiming them
  python catlog.py file [DAYS]       file downloads: ~/Downloads/PMID<id>_*, inbox/ (any name; inbox/<PMID>/ for
                                     supplements) and publisher-named PDFs saved to ~/Downloads in the last DAYS (3)
  python catlog.py asks              downloads/asks.html: links to every paper that needs a person (+ ill_requests.csv)
  python catlog.py mark PMID[,PMID] lane=X|click=URL|login=URL|doi=DOI|todo|no_kinetics|wrong_paper|unavailable WHY
                                     record what a person found out, so no later chat redoes it
  python catlog.py supp [N]          fetch open-access supplements (Europe PMC) for needs_supplement papers
  python catlog.py drop ROW_ID WHY   move a catalog row to rejected.jsonl (audit refutations)
  python catlog.py worklist [LANE] [N]  needs_browser papers, most BRENDA values first (download list)
  python catlog.py lanes [--retry] [--force]   work/downloads/lanes.json: waiting papers per Chrome download method,
                                     worklist order (chrome-lanes workflow); not ill, PMC website or tried by an agent in
                                     the last 14 days; refuses while a lane_*.jsonl changed in the last 10 min (a live
                                     run would halt) unless --force
  python catlog.py lanes-record [--dry]   Chrome agents' progress lines (work/downloads/lane_*.jsonl) -> marks: no access
                                     on campus (springer, sd) -> lane=ill, bot check -> click=<site>; the rest printed
  python catlog.py sample N          N random unaudited catalog rows as JSON (for /audit)
  python catlog.py audited ROW_ID keep|drop WHY   record an audit verdict (drop moves the row out)
  python catlog.py reread PMID WHY   send a paper back to be read again (work files kept in work/old/)
  python catlog.py censored N        claim N papers of sources/censored_reread.txt for a censored-values-only pass
                                     (catlog-batch with args.censored = true, then add)
  python catlog.py limitfix WHY ROW_ID...   clear the printed limit of censored values whose limit bounds another quantity
  python catlog.py pmfix WHY ROW_ID...      take a ± off values whose printed cell has none (code had filled in a neighbour's)
  python catlog.py cellfix CELL WHY ROW_ID... replace a printed cell its reader misread with the page image's (same row_id)
  python catlog.py show PMID         list extracted rows with the value code will store
  python catlog.py add PMID          merge work/PMID.read.json + work/PMID.verify.json, check, append
  python catlog.py prompt HASH       the exact prompt or task text a row's read_prompt/verify_prompt/task_prompt names
  python catlog.py index             index the downloaded papers in the old repo (library.tsv)
  python catlog.py more [N]          top up papers.tsv from the source lists
  python catlog.py enrich            UniProt accession + sequence, substrate SMILES (cached lookups)
  python catlog.py export            catlog_wide.jsonl/.csv: kcat, Km, kcat/Km side by side + all fields, and each
                                     value against the enzyme databases (database_check, tools/dbcompare.py)
  python catlog.py dbdiff PMID...|--all|--pending [N]   values that differ from a database and wait for a check
                                     against the paper: work/dbcheck_<PMID>.task.json (tools/dbcheck.py, prompts/dbcheck.md);
                                     --pending N takes and claims N waiting papers for one batch
  python catlog.py dbcheck-record [FILE...]   record the agents' verdicts (work/dbcheck_<PMID>.json) in
                                     sources/database_corrections.tsv; values found wrong go first to the next audit
  python catlog.py review ingest|stats|compare [PMID]|audit|site   human review (HUMAN_REVIEW.md)
  python catlog.py site status|update                               the CatLog website (WEBSITE.md; publish: cloudflare/publish.py)

Files: papers.tsv (queue), catalog.jsonl (verified rows), bounds.jsonl (verified censored values), rejected.jsonl, log.tsv,
texts/ (paper text), work/ (per-paper agent output), uniprot/ (sequence cache).
"""
import csv, fcntl, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from units import normalize, clean, MASS_UNIT  # noqa: E402
from fetch import (elsevier_xml, openalex_pdf, linkout_pdf, lane, ocr_pdf, pdf_pages, first_pages_text, thin,  # noqa: E402
                   esummary, glyph_warning, scan_warning, PERSON_LINK)

PAPERS = ROOT / 'papers.tsv'
CATALOG = ROOT / 'catalog.jsonl'
REJECTED = ROOT / 'rejected.jsonl'
BOUNDS = ROOT / 'bounds.jsonl'  # censored values: a kcat, Km or kcat/Km printed only as a bound or as not detected
LOG = ROOT / 'log.tsv'
TEXTS = ROOT / 'texts'
WORK = ROOT / 'work'
CONFIG = json.loads((ROOT / 'config.json').read_text())
COLS = ['pmid', 'doi', 'title', 'status', 'text_source', 'kept', 'rejected', 'note', 'updated']
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}
METRICS = {'kcat', 'Km', 'kcat/Km'}
NEEDED = ['enzyme', 'variant', 'substrate', 'metric', 'raw_value', 'raw_unit', 'location', 'quote']
# a censored row's kind (prompts/read.md "Censored values"): below a printed limit, above one, or reported not detected
CENSORED = {'<': '<', '\u2264': '<', '<=': '<', '>': '>', '\u2265': '>', '>=': '>', 'not_detected': 'not_detected',
            'not detected': 'not_detected', 'nd': 'not_detected', 'n.d.': 'not_detected'}
# organism is NOT required: a paper that never states the enzyme's source species (only the expression host) would
# otherwise lose every value (PMID 25324420, 168 values, 2026-10-09). It stays empty in the export, to filter on.


STANDIN = re.compile(r'NP[0-9A-F]{8}')  # a paper PubMed does not index (no PMID): tools/nopmid.py gives it this id
NOPMID = ROOT / 'sources' / 'nopmid_refs.tsv'


def is_standin(p):
    return bool(STANDIN.fullmatch(str(p)))


def paper_id(s):
    """A paper id as typed or found in a file name: PMIDs stay as they are, stand-ins become upper case."""
    s = str(s).strip()
    return s.upper() if STANDIN.fullmatch(s.upper()) else s


def id_in_name(name):
    """The paper id a file name starts with: PMID<digits>..., or a stand-in (NP + 8 hex), with or without 'PMID'."""
    m = re.match(r'PMID(\d+)', name, re.I)
    if m:
        return m.group(1)
    m = re.match(r'(?:PMID)?(NP[0-9A-F]{8})(?![0-9A-Z])', name, re.I)
    return m.group(1).upper() if m else None


def id_folder(name):
    """An inbox/<id>/ folder name: a PMID or a stand-in."""
    return name if re.fullmatch(r'\d{1,9}', name) else paper_id(name) if is_standin(paper_id(name)) else None


_standins = [{}, None]


def standins():
    """Stand-in id -> its row in sources/nopmid_refs.tsv (BRENDA's citation and the Crossref-checked DOI)."""
    seen = NOPMID.stat().st_mtime if NOPMID.exists() else None
    if _standins[1] != seen:
        _standins[0] = {}
        if seen:
            with open(NOPMID) as f:
                _standins[0] = {r['paper_id']: r for r in csv.DictReader(f, delimiter='\t') if is_standin(r.get('paper_id', ''))}
        _standins[1] = seen
    return _standins[0] or {}


def now():
    return time.strftime('%Y-%m-%d %H:%M')


def log(*fields):
    with open(LOG, 'a') as f:
        f.write('\t'.join([now(), *(' '.join(str(x).split()) for x in fields)]) + '\n')


# ---------- queue ----------

class Queue:
    """papers.tsv under an exclusive lock, so parallel agents can claim and update safely."""

    def __init__(self, write=True):
        self.write = write

    def __enter__(self):
        PAPERS.touch()
        self.lock = open(ROOT / 'papers.tsv.lock', 'w')
        fcntl.flock(self.lock, fcntl.LOCK_EX)
        with open(PAPERS) as fh:
            self.rows = {r['pmid']: r for r in csv.DictReader(fh, delimiter='\t')}
        return self

    def save(self):
        """Write a temp file and rename it over papers.tsv, so a killed process never leaves it truncated."""
        tmp = PAPERS.with_suffix('.tsv.tmp')
        with open(tmp, 'w') as fh:
            w = csv.DictWriter(fh, COLS, delimiter='\t', extrasaction='ignore')
            w.writeheader(); w.writerows(self.rows.values())
        os.replace(tmp, PAPERS)

    def set(self, pmid, **kw):
        r = self.rows.setdefault(pmid, {c: '' for c in COLS} | {'pmid': pmid, 'status': 'todo'})
        r.update({k: str(v) for k, v in kw.items()}); r['updated'] = now()

    def __exit__(self, *a):
        if self.write:
            self.save()
        fcntl.flock(self.lock, fcntl.LOCK_UN); self.lock.close()


# ---------- get ----------

def http(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


LIBRARY = ROOT / 'library.tsv'
RANK = {'elsevier_xml': 0, 'jats_xml': 1, 'pdf': 2, 'pdf_other': 3}


def cmd_index():
    """Index the old repo's downloaded papers once: library.tsv = pmid, kind, path (best asset per PMID)."""
    best, seen = {}, {}
    for pattern in CONFIG['library_globs']:
        # ${REALKCAT_DIR}: the earlier system's folder (README: settings), else a realkcat/ folder in this one
        pattern = pattern.replace('${REALKCAT_DIR}', os.environ.get('REALKCAT_DIR') or str(ROOT / 'realkcat'))
        for p in Path('/').glob(pattern.lstrip('/')):
            m = re.search(r'_pmid_(\d+)/', str(p)) or re.search(r'/PMID(\d+)[_.][^/]*$', str(p))
            if not m or not p.is_file():
                continue
            pmid, name = m.group(1), p.name.lower()
            if 'derived' in name or 'extract' in name:
                continue  # the old system's own transcriptions, not papers
            if name.endswith('.pdf'):
                if not p.read_bytes()[:1024].lstrip().startswith(b'%PDF-'):
                    continue  # HTML stubs ('Preparing to download...') and empty files saved as .pdf
                kind = 'pdf' if name in (f'paper_{pmid}.pdf',) or re.fullmatch(rf'pmid{pmid}_[a-z]+\.pdf', name) else 'pdf_other'
                if 'supp' in name or 'si_' in name:
                    continue
            elif name.endswith('.xml') and ('elsevier' in name or name.endswith('_els.xml')):
                data = p.read_bytes()
                raw = re.search(rb'<xocs:rawtext[^>]*>(.*?)</xocs:rawtext>', data, re.S)
                if b'<ce:sections' not in data and not (raw and len(raw.group(1)) > 8000):
                    continue  # abstract-only API response
                kind = 'elsevier_xml'
            elif name.endswith('.xml') and ('europepmc' in name or 'jats' in name or 'pmc' in name):
                data = p.read_bytes()
                if b'<article' not in data[:4000] or b'<html' in data[:4000].lower() or b'<body' not in data:
                    continue  # metadata-only record or a saved HTML page
                kind = 'jats_xml'
            else:
                continue
            seen.setdefault(hashlib.sha1(p.read_bytes()).hexdigest(), set()).add(pmid)
            if pmid not in best or RANK[kind] < RANK[best[pmid][0]]:
                best[pmid] = (kind, str(p))
    # one file saved under several PMIDs means at least one wrong paper: trust neither copy
    dup_hashes = {h for h, ps in seen.items() if len(ps) > 1}
    shared = set().union(*(seen[h] for h in dup_hashes)) if dup_hashes else set()
    for pmid in shared & set(best):
        if hashlib.sha1(Path(best[pmid][1]).read_bytes()).hexdigest() in dup_hashes:
            del best[pmid]
    with open(LIBRARY, 'w') as f:
        f.write('pmid\tkind\tpath\n')
        for pmid, (kind, path) in sorted(best.items()):
            f.write(f'{pmid}\t{kind}\t{path}\n')
    counts = {}
    for kind, _ in best.values():
        counts[kind] = counts.get(kind, 0) + 1
    log('-', 'index', f'papers={len(best)}', *(f'{k}={v}' for k, v in sorted(counts.items())))
    print(f'{len(best)} papers indexed:', counts, f'({len(shared)} PMIDs share a file with another PMID; those copies are not used)')


def library():
    if not LIBRARY.exists():
        return {}
    rows = [l.rstrip('\n').split('\t') for l in open(LIBRARY) if l[:1].isdigit()]
    found = {r[0]: r[2] for r in rows if os.path.exists(r[2])}  # a moved old-repo file is not a copy we have
    if rows and len(found) < len(rows) / 2:
        sys.exit(f'the old paper library ({len(rows)} papers listed in library.tsv, {len(found)} reachable) has moved: '
                 'point config.json library_globs at it and run `catlog.py index`; nothing was fetched or claimed')
    return found


def local_asset(pmid):
    """papers/<PMID>.* (v2's own downloads) first, then the old library."""
    for suffix in ('.els.xml', '.jats.xml', '.pdf'):
        p = ROOT / 'papers' / f'{pmid}{suffix}'
        if p.exists():
            return p
    path = library().get(pmid)
    return Path(path) if path else None


def to_text(path):
    name = path.name.lower()
    if name.endswith('.pdf'):
        text = subprocess.run(['pdftotext', '-layout', str(path), '-'], capture_output=True, text=True, errors="replace", timeout=120).stdout
        if len(text.strip()) < 2000 or thin(text, max(1, text.count('\f'))):  # scan: no text layer, or only a watermark
            ocr = ocr_pdf(path)
            return scan_warning(ocr) + ocr  # OCR reads a ± as a digit too
        return glyph_warning(path, text) + text  # a first line when the text layer mangles µ, ±, minus or °
    head = path.read_bytes()[:3000]
    tool = 'elsevier_to_text.py' if b'full-text-retrieval-response' in head or name.endswith('.els.xml') else 'jats_to_text.py'
    return subprocess.run([sys.executable, str(ROOT / 'tools' / tool), str(path)], capture_output=True, text=True, errors="replace", timeout=120).stdout


def standin_meta(pid):
    """A paper with no PMID is its DOI: title (BRENDA's || Crossref's) and DOI from sources/nopmid_refs.tsv; Europe PMC
    by DOI adds a PMCID when it holds the paper from another source. {} when there is no DOI on record."""
    reg = standins()
    if not reg:  # registry missing or unreadable: an outage, not an answer (like library() for the old library)
        raise RuntimeError(f'{NOPMID} is missing or has no stand-ins: run tools/nopmid.py ids')
    r = reg.get(pid)
    if not r or not r.get('doi'):
        return {}
    meta = {'title': r.get('crossref_title') or r.get('title', ''), 'doi': r['doi'], 'pmcid': '', 'pii': '', 'oa': ''}
    for attempt in range(3):
        try:
            s = json.loads(http('https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=lite&query='
                                + urllib.parse.quote(f'DOI:"{r["doi"]}"')))
            break
        except Exception:
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError('europe pmc search failed')  # get() keeps the paper todo
    hit = next((h for h in s.get('resultList', {}).get('result', []) if (h.get('doi') or '').lower() == r['doi'].lower()), None)
    if hit:
        meta.update(pmcid=hit.get('pmcid', ''), oa=hit.get('isOpenAccess', ''), alias=hit.get('pmid', ''))
    return meta


def epmc_meta(pmid):
    """Title, DOI and PMCID from Europe PMC, else from PubMed; PubMed also gives the PII of an old paper without a DOI.
    Raises when both lookups are dead (the paper then stays todo). A stand-in (no PMID) never goes to PubMed."""
    if is_standin(pmid):
        return standin_meta(pmid)
    for attempt in range(3):
        try:
            s = json.loads(http(f'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:{pmid}%20AND%20SRC:MED&format=json&resultType=lite'))
            hit = next(iter(s.get('resultList', {}).get('result', [])), None)
            if hit is None:
                break
            meta = {'title': hit.get('title', ''), 'doi': hit.get('doi', ''), 'pmcid': hit.get('pmcid', ''), 'pii': '',
                    'oa': hit.get('isOpenAccess', '')}
            if not meta['doi'] or meta['title'].startswith('['):  # no DOI (PII), or a translated title (original title)
                pm = esummary(pmid)
                meta['pii'] = pm.get('pii', '')
                if meta['title'].startswith('[') and pm.get('vernacular'):
                    meta['title'] = f"{meta['title']} || {pm['vernacular']}"
            return meta
        except Exception:
            time.sleep(2 * (attempt + 1))
    pm = esummary(pmid)  # Europe PMC down or without the record
    if pm.get('title', '').startswith('[') and pm.get('vernacular'):
        pm['title'] = f"{pm['title']} || {pm['vernacular']}"
    return pm


def europe_pmc_xml(pmid, pmcid):
    xml = http(f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML')
    if b'<article' not in xml[:4000] or b'<body' not in xml:
        return None
    (ROOT / 'papers').mkdir(exist_ok=True)
    p = ROOT / 'papers' / f'{pmid}.jats.xml'; p.write_bytes(xml)
    return p


PMC_CLOUD = 'https://pmc-oa-opendata.s3.amazonaws.com'


def names_pmid(path, pmid, doi=''):
    """A JATS file that prints this PMID as its own article-id is this paper, whatever its title wording (author
    manuscripts keep the authors' title: 'Cu- and Ni-substituted analogs' vs PubMed's 'copper- and nickel-...')."""
    if not str(path).endswith('.jats.xml'):
        return False
    head = Path(path).read_text(errors='ignore')[:30000]
    return f'<article-id pub-id-type="pmid">{pmid}</article-id>' in head or bool(doi) and \
        f'<article-id pub-id-type="doi">{doi.lower()}</article-id>' in head.lower()  # a no-PMID paper is its DOI


def pmc_cloud_xml(pmid, pmcid):
    """JATS XML from NLM's PMC Cloud Service (the PMC Article Datasets on AWS): open-access articles and NIH author
    manuscripts (license TDM: text mining allowed). Europe PMC answers 500 for author manuscripts; scanned back issues
    are not in the bucket (they stay lane pmc). None when no version of the article is there."""
    for version in (3, 2, 1):  # newest version first
        try:
            meta = json.loads(http(f'{PMC_CLOUD}/metadata/{pmcid}.{version}.json', timeout=30))
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                continue  # S3 answers 403 for a key that does not exist
            raise
        url = (meta.get('xml_url') or '').split('?')[0].replace('s3://pmc-oa-opendata', PMC_CLOUD)
        if not url or not (meta.get('is_pmc_openaccess') or meta.get('license_code')):
            continue
        xml = http(url, timeout=60)
        if b'<article' not in xml[:4000] or b'<body' not in xml:
            continue
        (ROOT / 'papers').mkdir(exist_ok=True)
        p = ROOT / 'papers' / f'{pmid}.jats.xml'; p.write_bytes(xml)
        return p
    return None


STOP = set('with from that this their which into using during between other study analysis role novel new'.split())
GREEK = 'alpha|beta|gamma|delta|epsilon|kappa|lambda|omega'  # PubMed spells them out; the paper prints the letter


def title_ok(title, text):
    """The file is the right article: most content words of the PubMed title appear near its start. Ligatures (the
    single 'fi' glyph), words hyphenated across a line break and a GLYPH WARNING first line do not count against it."""
    import unicodedata
    title = re.sub(r'<[^>]+>', ' ', title or '')  # Crossref titles carry <i>, <sub>
    if ' || ' in title:  # PubMed's English translation || the original title (non-English papers)
        parts = [t for t in title.split(' || ') if len(re.findall(r'[a-z0-9]{4,}', t.lower())) >= 3] or title.split(' || ')[:1]
        return any(title_ok(t, text) for t in parts)  # a cut-off fragment ('|| Acti') is not a title
    words = [w for w in (re.sub(GREEK, '', w) for w in re.findall(r'[a-z0-9]+', clean(unicodedata.normalize(
             'NFKC', title or '')).lower())) if len(w) > 3 and w not in STOP]  # '17beta' is printed '17β'
    text = re.sub(r'^GLYPH WARNING[^\n]*\n+', '', text or '')
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', unicodedata.normalize('NFKC', text[:10000]))
    head = squash(text[:8000])
    flat = head.replace(' ', '')
    ocr = flat.replace('rn', 'm')  # scanned 1970s pages: 'foenum' OCRed as 'foenurn' (PMID 25183)
    return not words or sum(w in head or w in flat or w in ocr for w in words) / len(words) >= 0.8


_doi_fixes, _doi_seen = None, None


def doi_fixes():
    """DOIs corrected by hand (`catlog.py mark <PMID> doi=<DOI>`, log event doi_fix). get() keeps them. Rebuilt
    whenever log.tsv changed, so a long fetch sees a DOI another chat fixed meanwhile."""
    global _doi_fixes, _doi_seen
    seen = (LOG.stat().st_size, LOG.stat().st_mtime) if LOG.exists() else None
    if _doi_fixes is None or seen != _doi_seen:
        _doi_fixes, _doi_seen = {}, seen
        for f in events():
            if f[2] == 'doi_fix' and len(f) > 3:
                _doi_fixes[f[1]] = f[3]
    return _doi_fixes


def events():
    """log.tsv as field lists: [time, pmid or '-', event, details...]."""
    if not LOG.exists():
        return []
    return [f for f in (line.rstrip('\n').split('\t') for line in open(LOG)) if len(f) >= 3]


BAD_FILES = WORK / 'rejected_files.tsv'


def file_sha(p):
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()


def known_bad(pmid, p, ignore=('title',)):
    """True when this exact file (by content, whatever its name) was already rejected for this paper."""
    if not BAD_FILES.exists():
        return False
    sha = file_sha(p)  # title-check rejections are not remembered: the check runs again and may have been fixed
    return any(l.split('\t')[:2] == [pmid, sha] and not l.split('\t')[2].startswith(ignore) for l in open(BAD_FILES))


def single_page(pmid):
    """True when PubMed prints one page for the paper (Biochem J '127:15P', Biochem Soc Trans '24:128S': one-page
    meeting abstracts), so a one-page PDF is the whole item, not a preview (2026-10-13: 4342549, 8674614)."""
    try:
        pg = (esummary_many([pmid]).get(pmid) or {}).get('pages', '')
    except Exception:
        return False
    return bool(pg.strip()) and '-' not in pg


def remember_bad(pmid, p, why):
    with open(BAD_FILES, 'a') as f:
        f.write(f'{pmid}\t{file_sha(p)}\t{why}\t{p}\t{now()}\n')


def get(pmid):
    """Write texts/PMID.txt (read-only). Routes: local copy, Europe PMC OA XML, Elsevier API XML, OpenAlex OA PDF.
    A paper none of them can supply becomes needs_browser, with its publisher lane in `note` (DOWNLOADS.md)."""
    out = TEXTS / f'{pmid}.txt'
    if out.exists() and out.stat().st_size > 2000:
        return out, 'cached'
    try:
        meta = epmc_meta(pmid)
    except RuntimeError:
        return None, 'lookup_failed'  # stays todo; never read a paper whose identity we cannot check
    if meta.get('alias'):  # a no-PMID paper PubMed has indexed since: read it once, under its PMID
        with Queue() as q:
            q.set(pmid, status='unavailable', note=f"in PubMed as PMID {meta['alias']}: read under that id")
            if meta['alias'] not in q.rows:
                q.set(meta['alias'], status='todo', note=f'PMID of no-PMID paper {pmid} ({meta["doi"]})')
        log(pmid, 'unavailable', f"alias PMID {meta['alias']}")
        return None, 'unavailable'
    if not meta:  # neither Europe PMC nor PubMed has this PMID
        why = 'no DOI on record for this no-PMID paper' if is_standin(pmid) else 'PMID not found in PubMed or Europe PMC'
        with Queue() as q:
            q.set(pmid, status='unavailable', note=why)
        log(pmid, 'unavailable', why)
        return None, 'unavailable'
    if doi_fixes().get(pmid):
        meta = {**meta, 'doi': doi_fixes()[pmid]}  # corrected by hand (`mark doi=`): PubMed's stale DOI never wins
    with Queue(write=False) as q:
        chosen = q.rows.get(pmid, {}).get('text_source', '')
    src = local_asset(pmid)
    if chosen.startswith('downloaded:') and Path(chosen.split(':', 1)[1]).exists():
        src = Path(chosen.split(':', 1)[1])  # the copy the user downloaded beats an XML that lacked something
    whole = bool(src) and src.suffix == '.pdf' and pdf_pages(src) == 1 and single_page(pmid)  # a one-page item, not a preview
    if src and known_bad(pmid, src, ('title', 'one-page preview') if whole else ('title',)):
        log(pmid, 'local_copy_skipped', 'file rejected before', src); src = None
    if src and src.suffix == '.pdf' and pdf_pages(src) < 2 and not whole:
        log(pmid, 'local_copy_skipped', 'one-page preview', src); remember_bad(pmid, src, 'one-page preview'); src = None
    text = to_text(src) if src else ''
    if src and meta.get('title') and not title_ok(meta['title'], text):
        log(pmid, 'local_copy_skipped', 'title does not match', src); remember_bad(pmid, src, 'title does not match'); src = None
    mine = bool(src) and chosen.startswith('downloaded:') and str(src) == chosen.split(':', 1)[1]
    # publisher XML first, PDF fallback; not for a scan's OCR warning (an XML route may hold only the same OCR text)
    mangled = src if src and text.startswith('GLYPH WARNING: the text layer') and not mine else None
    if mangled:
        src = None
    source = f"{'downloaded' if mine else 'local'}:{src}" if src else ''
    epmc_down = False
    try:
        if not src and meta.get('pmcid') and meta.get('oa') != 'N':  # a non-OA PMC article has no XML (HTTP 500)
            try:
                src = europe_pmc_xml(pmid, meta['pmcid']); source = f'europepmc:{src}' if src else ''
            except urllib.error.HTTPError as e:
                if e.code < 500:
                    raise
                epmc_down = True  # Europe PMC answers 500 for some OA papers: the PMC Cloud and the DOI routes go on
        if not src and meta.get('pmcid'):  # NIH author manuscripts: in PMC's text-mining datasets, not Europe PMC's
            src = pmc_cloud_xml(pmid, meta['pmcid']); source = f'pmc_cloud:{src}' if src else ''
        if not src and (meta.get('doi') or meta.get('pii')):
            src = elsevier_xml(pmid, meta.get('doi'), meta.get('pii')); source = f'elsevier_api:{src}' if src else ''
    except Exception as e:  # network trouble, not an answer: the paper stays todo
        return None, 'off_campus' if 'entitlement' in str(e) else 'lookup_failed'  # off_campus: Elsevier, retry on campus
    if not src and mangled:
        src, source = mangled, f'local:{mangled}'
    try:
        if not src and meta.get('title'):
            src = openalex_pdf(pmid, title_ok, meta['title'], doi=meta.get('doi', '')); source = f'openalex_oa:{src}' if src else ''
        if not src and meta.get('title') and not is_standin(pmid):  # LinkOut is PubMed's
            src = linkout_pdf(pmid, title_ok, meta['title']); source = f'pubmed_linkout:{src}' if src else ''
    except RuntimeError:
        return None, 'lookup_failed'  # an outage is not an answer: the paper stays todo
    text = (text if src == mangled or source.startswith(('local:', 'downloaded:')) else to_text(src)) if src else ''
    if mangled and src != mangled and '\n## OCR TEXT (scanned article' in text:  # the publisher's XML is only OCR (old
        src, source, text = mangled, f'local:{mangled}', to_text(mangled)        # JBC scans): the PDF's pages can be seen
    status, note = '', ''
    if not src and epmc_down:
        return None, 'lookup_failed'  # an open-access paper Europe PMC could not serve: retry later, not the browser
    if not src:
        status, note = 'needs_browser', f"lane={lane(meta.get('doi'), meta.get('pii'), meta.get('pmcid'))}"
        if PERSON_LINK.get(str(pmid)):  # free, but the site asks scripts not to fetch its PDFs (J-STAGE robots.txt)
            note = f"lane=jstage; free={PERSON_LINK.pop(str(pmid))}"
        elif off_campus_now():
            note += '; retry'  # free routes can fail off campus: `fetch` tries it once more from campus
    elif len(text) < 2000:
        status = 'no_text'
    elif meta.get('title') and not title_ok(meta['title'], text) and \
            not names_pmid(src, pmid, meta.get('doi', '') if is_standin(pmid) else ''):
        status = 'wrong_paper'
    with Queue() as q:
        before = q.rows.get(pmid, {})
        if not status and before.get('status') == 'needs_browser':
            status, note = 'todo', f'found by {source.split(":")[0]}'  # a new free route found a paper a browser was to get
        elif status == 'needs_browser' and before.get('status') == 'needs_browser' and \
                (lane_of(before) in ILL_LANES or re.search(r'\b(click|login)=', before.get('note', ''))):
            note = re.sub(r';\s*retry$', '', before['note'])  # a person's finding outlives a retry; the retry is used up
        keep = is_standin(pmid)  # a no-PMID paper's DOI is its identity: never blanked
        q.set(pmid, text_source=source or 'none', doi=meta.get('doi') or (before.get('doi', '') if keep else ''),
              title=(meta.get('title') or (before.get('title', '') if keep else ''))[:200].replace('\t', ' '),
              **({'status': status} if status else {}), **({'note': note} if note else {}))
    if status and status != 'todo':
        log(pmid, status, source or note or 'none')
        return None, status
    try:
        out.write_text(text); out.chmod(0o444)
        log(pmid, 'text', source.split(':', 1)[0])  # progress counts papers obtained by route from these lines
    except PermissionError:  # another process (fetch vs next) wrote it a moment ago
        pass
    return out, source


KINETIC = re.compile(r'(?i:k\s?_?\{?cat\b|michaelis|turnover number|catalytic efficienc|catalytic constant|kinetic (?:parameters|constants))'
                     r'|\bK\s?_?\{?[mM]\b|\bK\s?\(\s?[mM]\s?\)')


def brenda_counts():
    p = ROOT / 'sources' / 'brenda_pmids.tsv'
    if not p.exists():
        return {}
    return {l.split('\t')[0]: int(l.split('\t')[1]) for l in open(p) if l[:1].isdigit() or is_standin(l.split('\t')[0])}


def coverage():
    """pmid -> (values the databases cite, rows the OLD system certified), from tools/coverage.py."""
    p = ROOT / 'sources' / 'coverage.tsv'
    if not p.exists():
        return {}
    out = {}
    for l in open(p):
        f = l.split('\t')
        if f[0].isdigit() or is_standin(f[0]):
            out[f[0]] = (max(int(f[1]), int(f[2])), int(f[3]))
    return out


_DISCOVERED = {}


def _discovered_rows():
    """(pmid, expected_values, later, gain) of every sources/discovered_*.tsv, read once per file version."""
    out = []
    for p in sorted((ROOT / 'sources').glob('discovered_*.tsv')):
        key = (p.name, p.stat().st_mtime)
        if key not in _DISCOVERED:
            num = lambda v: int(v) if (v or '').isdigit() else None
            _DISCOVERED[key] = [(r['pmid'], num(r.get('expected_values')), r.get('later') == '1', num(r.get('gain')))
                                for r in csv.DictReader(open(p), delimiter='\t')]
        out += _DISCOVERED[key]
    return out


def discovered():
    """pmid -> values a paper no database cites is expected to print, for the papers a literature search found
    (sources/discovered_*.tsv, tools/discover_europepmc.py): by where it prints kcat, table 15, abstract 5, body 2;
    the Km-only list (discovered_km_*): the Km numbers code counts in its free full text (tools/km_gain.py), else by
    where it prints Km, 3, 1, 0."""
    return {p: v for p, v, _, _ in _discovered_rows() if v is not None}


def gains():
    """pmid -> values a paper of either Europe PMC list (kcat list, Km-only list) is expected to add, on one scale:
    tools/km_gain.py counts the constants its free full text prints and calibrates the count on papers already read
    (`gain` column, apply-gain). Only the "gain" order uses it."""
    return {p: g for p, _, _, g in _discovered_rows() if g is not None}


def later():
    """The Km-only list (about 3 Km values per paper on average, against ~31 per paper read). Every order but "gain"
    puts them last and plain `more` queues them only once nothing else is left to read; the chat reading the Europe
    PMC lists takes them by expected values (the user, 2026-11-09: "read them here": `more --km N`,
    priority(focus='gain'))."""
    return {p for p, _, late, _ in _discovered_rows() if late}


def old_rows():
    """pmid -> rows the old catalog (the website's base) holds for it, from sources/coverage.tsv."""
    p = ROOT / 'sources' / 'coverage.tsv'
    return {f[0]: int(f[2]) for f in (l.split('\t') for l in open(p)) if f[0].isdigit()} if p.exists() else {}


FOCUSES = ('verify', 'growth', 'reread')


def priority(pmids, focus=None):
    """Papers on disk first; then, by config.json "focus" (or the one given):
    "mix" (the user, 2026-11-01): the orders named in config.json "mix" ({"reread": 2, "growth": 1}), taken in turn by
      weight, so every batch holds papers of each: 12 papers at 2:1 are the first 8 of one order and 4 of the other,
      a paper taken once, by the first order that reaches it. Without a usable "mix", the verify order;
    "verify" (default): the papers the databases say carry the most values first; between equal counts, papers nobody
      certified before the ones the old system already did (a paper the old system certified 2 rows from still has
      most of its values unchecked);
    "growth": the papers most likely to ADD rows: values the databases cite (about 2.4 per measurement) minus the rows
      the old catalog already holds; papers it never had come first. Re-reading a paper it already covers adds ~0.
    "reread" (the user, 2026-10-19): the papers behind the old catalog's accepted rows first, most such rows first,
      so the site's "Not yet re-read" records get replaced (a finished paper replaces all its old rows); then the
      papers with the most old rows of any kind (the user, 2026-11-01: the growth order had put them last, so the
      verify order would have taken about 25,600 papers to replace the on-disk ones, this about 10,200); after those,
      the growth order, so it needs no switching back.
    A paper no database cites, found by literature search, counts the values it is expected to print instead (the
    user, 2026-10-13: mixed in by expected yield). The Km-only list (later()) comes after every other paper, on disk
    or not, in every order (the user, 2026-11-09);
    "gain" (the user, 2026-11-09/10: "read them here", highest gain first, "what if both km kcat"; only the chat
    reading the two Europe PMC lists asks for it, in process like any named order; "km" is the same order): papers of
    either list with a counted gain first, most expected values first (gains()); the rest after, in the verify order."""
    focus = focus or CONFIG.get('focus')
    if focus in ('gain', 'km'):
        g = gains()
        rest = {p: i for i, p in enumerate(priority([p for p in pmids if p not in g], 'verify'))}
        return sorted(pmids, key=lambda p: (p not in g, -g.get(p, 0), rest.get(p, 0)))
    if focus == 'mix':
        weights = [(f, int(w)) for f, w in (CONFIG.get('mix') or {}).items() if f in FOCUSES and int(w) > 0]
        if not weights:
            return priority(pmids, 'verify')
        orders, out, seen, n = {f: iter(priority(pmids, f)) for f, _ in weights}, [], set(), len(set(pmids))
        while len(out) < n:
            before = len(out)
            for f, w in weights:
                for _ in range(w):
                    p = next((x for x in orders[f] if x not in seen), None)
                    if p is not None:
                        seen.add(p); out.append(p)
            if len(out) == before:  # every order is a permutation of pmids: cannot happen, but never loop forever
                break
        return out
    have = set(library()) | {f.stem for f in TEXTS.glob('*.txt') if '.' not in f.stem}
    if (ROOT / 'papers').exists():
        have |= {f.name.split('.')[0] for f in (ROOT / 'papers').glob('*.*')}
    cov, counts, found, late = coverage(), brenda_counts(), discovered(), later()
    calib = ROOT / 'human_review' / 'calibration.txt'  # human-reviewed papers on disk: read early, to measure v2 against reviewers
    calib = set(calib.read_text().split()) if calib.exists() else set()
    flagged = ROOT / 'sources' / 'flagged_old.txt'  # papers behind old-catalog values the site flags (kcat/Km >1.5x off,
    flagged = set(flagged.read_text().split()) if flagged.exists() else set()  # unit folds, magnitudes): read early
    # blind re-reads first, whatever the focus (the user, 2026-10-21: the 303 papers whose agents saw database values
    # before 2026-10-12, CLAUDE.md Open items); a paper leaves the list's effect once it is read (no longer todo)
    blind = ROOT / 'sources' / 'blind_reread.txt'
    blind = set(blind.read_text().split()) if blind.exists() else set()
    if focus in ('growth', 'reread'):
        old = old_rows()
        def key(p):
            values = cov.get(p, (counts.get(p, 0), 0))[0] or found.get(p, 0)
            accepted_old = cov.get(p, (0, 0))[1] if focus == 'reread' else 0
            old_any = old.get(p, 0) if focus == 'reread' else 0
            return (p in late, p not in have, p not in blind, p not in calib, p not in flagged, -accepted_old, -old_any,
                    -(values / 2.4 - old.get(p, 0)))
        return sorted(pmids, key=key)
    def key(p):
        values, certified_before = cov.get(p, (counts.get(p, 0), 0))
        values = values or found.get(p, 0)
        return (p in late, p not in have, p not in blind, p not in calib, p not in flagged, -values, certified_before > 0)
    return sorted(pmids, key=key)


def unpark_due():
    """A paper parked because its agents kept dying (usage/API limits, a safety stop) comes back by itself after 24 h,
    at most 3 times; after that `status` lists it and `reread` retries it."""
    from collections import Counter
    cutoff = time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time() - 24 * 3600))
    auto = Counter(f[1] for f in events() if f[2] == 'unparked' and len(f) > 3 and f[3].startswith('auto'))
    with Queue() as q:
        due = [p for p, r in q.rows.items() if r['status'] == 'parked' and r.get('updated', '') < cutoff and auto[p] < 3]
        for p in due:
            q.set(p, status='todo', note=f'back after 24 h parked (automatic retry {auto[p] + 1} of 3)')
    for p in due:
        log(p, 'unparked', 'auto: 24 h passed')
    return due


def release_stale_claims(hours=3):
    """Claims a chat left behind (it ended: a restart, a closed lid, a killed app): a paper 'reading' for more than
    `hours` with no work file written in the last hour. Read and verified: add it. Otherwise back to todo without
    counting a death (a finished unverified read is kept, keep_read). A missed file nobody verified needs a verifier,
    so that paper stays (status shows it as Stuck). 57 such claims sat for hours on 2026-10-11."""
    old = time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time() - hours * 3600))
    with Queue(write=False) as q:
        stale = [p for p, r in q.rows.items() if r['status'] == 'reading' and r.get('updated', '') < old]
    for p in stale:
        files = list(WORK.glob(f'{p}.*.json'))
        if any(time.time() - f.stat().st_mtime < 3600 for f in files):
            continue  # an agent is still writing for it
        have = {f.name[len(p):] for f in files}
        if '.missed.read.json' in have and '.missed.verify.json' not in have:
            continue
        if '.read.json' in have and '.verify.json' in have:
            add_one(p)
            with Queue(write=False) as q:
                if q.rows.get(p, {}).get('status') != 'reading':
                    continue
            cmd_reread(p, 'add could not finish an old claim (files out of date)', limit=True)
        else:
            cmd_reread(p, f'claim older than {hours} h with no agent output (the chat that claimed it ended)', limit=True)


def locked():
    """The method paper's test set (sources/holdout_locked.txt, the user 2026-11-01): read for the first time only by
    the frozen harness after preregistration, so next, the censored pass,
    sample, dbdiff, the sweeps and review packs never take them and no audit or sweep can turn them into a rule
    (downloads still list them: downloading is not reading). Also the papers a later test drew from the finished ones
    (sources/holdout_rand2.txt, written at its draw; paper/evidence/random_test2_20261112/): left alone the same way
    until its report. '#' lines are comments."""
    out = set()
    for name in ('holdout_locked.txt', 'holdout_rand2.txt'):
        f = ROOT / 'sources' / name
        if f.exists():
            out |= {w for line in f.read_text().splitlines() if not line.startswith('#') for w in line.split()}
    return out


def cmd_next(n):
    """Claim up to n todo papers that yield text with kinetic terms; mark them 'reading'. Papers held out for the
    method paper's test (locked()) are never claimed."""
    picked = []
    unpark_due()
    release_stale_claims()
    held = locked()
    with Queue() as q:
        todo = [p for p, r in q.rows.items() if r['status'] == 'todo' and p not in held]
    fails = 0
    cands, rf = priority(todo), recent_failures()
    for pmid in [p for p in cands if p not in rf] + [p for p in cands if p in rf]:
        if len(picked) >= n:
            break
        if pmid in held:  # again here: a chat that patches priority() to return its own list must not claim one either
            continue
        try:
            path, how = get(pmid)
        except subprocess.SubprocessError as e:  # a PDF that hangs pdftotext / OCR
            with Queue() as q:
                q.set(pmid, status='no_text', note=f'conversion failed: {type(e).__name__}')
            log(pmid, 'no_text', 'conversion failed'); continue
        if how == 'lookup_failed':
            log(pmid, 'lookup_failed', 'next')
        fails = fails + 1 if how == 'lookup_failed' else 0
        if fails >= 3:
            print('paper lookups keep failing (network?); stopping', file=sys.stderr)
            break
        if not path:
            continue
        if not KINETIC.search(path.read_text()):
            with Queue() as q:
                q.set(pmid, status='no_kinetics')
            log(pmid, 'no_kinetics')
            continue
        with Queue() as q:
            if q.rows.get(pmid, {}).get('status') != 'todo':
                continue  # another session claimed it meanwhile
            q.set(pmid, status='reading')
        kept = keep_read(pmid)  # the batch reader keeps any read.json it finds: only a read `reread` kept may be there
        (WORK / 'old').mkdir(exist_ok=True)  # (a done paper sent back for its supplement still has its old files)
        for f in WORK.glob(f'{pmid}.*.json'):
            if not (kept and f.name in (f'{pmid}.read.json', f'{pmid}.prompts.json')):  # a kept read keeps its claim record
                shutil.move(str(f), str(WORK / 'old' / f'{f.stem}.{int(time.time())}.json'))
        claim_prompts(pmid, kept)
        picked.append(pmid)
    print(' '.join(picked))


def off_campus_now():
    """True when this network cannot read Elsevier (the campus probe); False when on campus or unknown (no key)."""
    from fetch import elsevier_key, elsevier_entitled
    key = elsevier_key()
    try:
        return bool(key) and not elsevier_entitled(key)
    except Exception:
        return False


def recent_failures(hours=6):
    """Papers whose lookup failed in the last hours: tried after the others, so one stuck paper cannot stop a run."""
    since = time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time() - hours * 3600))
    return {f[1] for f in events() if f[2] == 'lookup_failed' and f[0] >= since}


def cmd_fetch(n):
    """Get text for up to n todo papers ahead of reading (no claim). Papers no route can supply
    become needs_browser with a lane: that list is the browser/Codex download worklist. Browser-list papers that
    were tagged '; retry' (missed off campus) get one more try when this run is on campus."""
    with Queue() as q:
        todo = [p for p, r in q.rows.items() if r['status'] == 'todo']
        retry = [p for p, r in q.rows.items() if r['status'] == 'needs_browser' and r.get('note', '').endswith('; retry')]
    if retry and not off_campus_now():
        todo += retry
    have = set(library())
    tried = got = fails = off = 0
    cands = priority([p for p in todo if p not in have and not (TEXTS / f'{p}.txt').exists()])
    rf = recent_failures()
    for pmid in [p for p in cands if p not in rf] + [p for p in cands if p in rf]:
        if tried >= n:
            break
        try:
            path, how = get(pmid)
        except subprocess.SubprocessError as e:  # a PDF that hangs pdftotext / OCR
            with Queue() as q:
                q.set(pmid, status='no_text', note=f'conversion failed: {type(e).__name__}')
            log(pmid, 'no_text', 'conversion failed'); continue
        if how == 'off_campus':  # an Elsevier paper this network may not read: skipped, not a failure, stays todo
            off += 1; continue
        tried += 1; got += bool(path)
        print(pmid, how)
        if how == 'lookup_failed':
            log(pmid, 'lookup_failed', 'fetch')
        fails = fails + 1 if how == 'lookup_failed' else 0
        if fails >= 3:
            print('paper lookups keep failing (network or Elsevier quota?); stopping', file=sys.stderr)
            break
    print(f'fetched {got} of {tried}' + (f' ({off} Elsevier papers skipped: off campus, they stay todo)' if off else ''))


INBOX = ROOT / 'inbox'
SUPP_NAME = re.compile(r'supp(?:l(?:\b|_|-|\d|ementa(?:ry|l))|\d|_|-|\b|orting)|mmc\d|\bSI\b|_si[_.]|_ESM|MOESM|appendix'
                       r'|-sup-\d|[._-]s\d{3,4}\b|\.sapp\.|data_sheet|[._]SOM\b|_SM\b', re.I)  # not 'Suppression', 'Supplementation'
SUPP_HEAD = re.compile(r'(?i)^\W*(supporting information|supporting online material|supplementa(?:ry|l) (?:material|data|information|figures?|tables?|methods)'
                       r'|electronic supplementary material|appendix)\b')  # how a supplement PDF starts
SUPP_EXT = ('.xlsx', '.xlsm', '.xls', '.csv', '.tsv', '.txt', '.docx', '.doc', '.zip')
PARTIAL = ('.crdownload', '.download', '.part')
REDOWNLOAD = ('incomplete', 'no_text', 'wrong_paper')  # the copy we have is a preview, unreadable or another article
WAITING = ('needs_browser', 'needs_supplement') + REDOWNLOAD


def identify(f, queue):
    """(PMID, how) for a downloaded file of any name, or (None, reason). The PMID in the name or folder first, then a
    DOI printed in the file that matches exactly one queued paper, then a title that matches exactly one paper waiting
    for a download. Never a guess."""
    named = id_in_name(f.name)
    if named:
        return named, 'PMID in the file name'
    rel = f.relative_to(INBOX).parts if INBOX in f.parents else ()
    if len(rel) > 1 and id_folder(rel[0]):
        return id_folder(rel[0]), 'PMID folder in inbox/'
    if f.suffix.lower() != '.pdf':
        return None, 'not a PDF and no PMID in its name or folder'
    pii = re.search(r'1-s2\.0-([0-9A-Z-]{12,20})-main', f.name)  # ScienceDirect's own download name
    if pii:
        try:
            cr = json.loads(http('https://api.crossref.org/works?rows=2&select=DOI&filter=alternative-id:' + pii.group(1).replace('-', '')))
            dois = [i['DOI'] for i in cr['message']['items']]
            hits = json.loads(http('https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=lite&query='
                                   + urllib.parse.quote(f'DOI:"{dois[0]}"')))['resultList']['result'] if len(dois) == 1 else []
            pm = [h.get('pmid') for h in hits if h.get('pmid')]
            if len(pm) == 1:
                return pm[0], f'Elsevier PII {pii.group(1)} in the file name -> DOI {dois[0]} -> PMID'
        except Exception:
            pass  # offline or unknown: fall through to the content routes
    text = first_pages_text(f)
    dois = {d.rstrip('.,;)]').lower() for d in re.findall(r'10\.\d{4,9}/[^\s"<>]+', text)}
    hits = {p for p, r in queue.items() if r.get('doi') and r['doi'].lower() in dois
            and (not r.get('title') or title_ok(r['title'], text))}  # a DOI it merely cites is not its own
    if len(hits) == 1:
        return hits.pop(), 'DOI printed in the file'
    waiting = [p for p, r in queue.items() if r['status'] in WAITING and r.get('title') and not is_standin(p)
               and title_ok(r['title'], text)]  # a no-PMID paper is filed by its id or its printed DOI only
    # Title words alone are not enough for a file nobody named: 'The influence of sodium ion binding on factor IXa
    # activity' has five common words that a 1994 ribosome paper also prints (3 of 14 title filings were wrong).
    # The title itself must be printed near the top.
    top = letters(text[:6000])
    printed = [p for p in waiting if any(letters(t)[:50] in top for t in re.sub(r'<[^>]+>', ' ', queue[p]['title']).split(' || ')
                                         if len(letters(t)) >= 20)]
    if len(printed) == 1:
        return printed[0], 'title printed at the top of the file'
    return None, f'no unique match (DOI hits {len(hits)}, title hits {len(waiting)}, printed titles {len(printed)})'


def letters(s):
    """Lower-case letters and digits only, Greek letters spelled out as PubMed spells them ('17β' -> '17beta')."""
    import unicodedata
    s = unicodedata.normalize('NFKC', clean(s)).lower()
    for g, name in zip('αβγδεκλω', GREEK.split('|')):
        s = s.replace(g, name)
    return re.sub(r'[^a-z0-9]', '', s)


def file_paper(f, pmid, how, title, status=''):
    """Title-check a downloaded PDF and make it the paper's text source; True when filed. A paper whose copy was a
    preview or the wrong article (REDOWNLOAD) gets the new file in place of the old one (kept in papers/replaced/);
    a paper already read or being read keeps its text and status (the file is stored for later)."""
    papers, rejected = ROOT / 'papers', ROOT / 'papers' / 'rejected'
    pages = pdf_pages(f)
    whole = pages == 1 and single_page(pmid)  # a one-page item, not a preview
    seen_bad = known_bad(pmid, f, ('title', 'one-page preview') if whole else ('title',))
    ok = not seen_bad and bool(title) and (pages >= 2 or whole) and title_ok(title, first_pages_text(f))
    why_bad = ('this exact file was rejected before' if seen_bad else 'empty or unreadable PDF' if pages == 0
               else 'one-page preview' if pages < 2 else 'title check failed')
    if not ok and not seen_bad:
        remember_bad(pmid, f, why_bad + ' at filing')
    have = papers / f'{pmid}.pdf'
    if ok and have.exists() and status in REDOWNLOAD:
        keep = papers / 'replaced' / f'{pmid}.{time.time_ns()}.pdf'
        keep.parent.mkdir(exist_ok=True); shutil.move(str(have), str(keep))
    dest = have if ok and not have.exists() else rejected / f.name
    if dest.exists():
        dest = dest.with_name(f'{dest.stem}_{time.time_ns()}{dest.suffix}')  # never overwrite a kept file
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(f), str(dest))
    if dest.parent != papers:
        why = why_bad if not ok else 'papers/ already has this PMID'
        log(pmid, 'file_rejected', f.name, why)
        print(pmid, 'rejected:', why, '->', dest)
        return False
    if status in ('done', 'reading', 'no_kinetics'):
        log(pmid, 'filed', f.name, how, f'kept status {status}')
        print(pmid, f'filed ({how}); paper stays {status}')
        return True
    old = TEXTS / f'{pmid}.txt'  # text from an earlier copy (preview, wrong file): keep it aside, read the new one
    if old.exists():
        keep = TEXTS / 'replaced' / f'{pmid}.{time.time_ns()}.txt'
        keep.parent.mkdir(exist_ok=True)
        old.chmod(0o644); shutil.move(str(old), str(keep))
    with Queue() as q:
        q.set(pmid, status='todo', text_source=f'downloaded:{dest}', title=title[:200], note=f'filed ({how})')
    log(pmid, 'filed', f.name, how)
    print(pmid, 'filed', f'({how})')
    return True


def foreign_supplement(f, r):
    """Why a supplement file (a PDF, or PDFs inside a zip) belongs to another article, or ''. An SI prints its own
    article's DOI near the top of page 1; one that prints only another DOI there and not this paper's title is foreign."""
    if not (r.get('doi') and r.get('title')):
        return ''
    def check(pdf):
        text = first_pages_text(pdf)
        dois = {x.rstrip('.,;)]').lower() for x in re.findall(r'10\.\d{4,9}/[^\s"<>]+', text[:1500])}
        return dois and r['doi'].lower() not in dois and not title_ok(r['title'], text)
    try:
        if f.suffix.lower() == '.pdf':
            return "supplement prints another article's DOI and not this title" if check(f) else ''
        if f.suffix.lower() == '.zip':
            import zipfile, tempfile
            with zipfile.ZipFile(f) as z, tempfile.TemporaryDirectory() as tmp:
                for m in z.namelist():
                    if m.lower().endswith('.pdf') and '__MACOSX' not in m:
                        t = Path(tmp) / Path(m).name
                        t.write_bytes(z.read(m))
                        if check(t):
                            return f"a PDF in this zip ({Path(m).name}) is another article's supplement"
    except Exception:
        return ''  # unreadable here: add_supplement decides whether any text can be used
    return ''


def cmd_file(days=3):
    """File downloads so the next batch reads them.
    - ~/Downloads/PMID<id>_* (any age) and anything in inbox/ (any name; everything in inbox/<PMID>/ is that paper's
      supplementary material). Unidentified inbox files go to inbox/unmatched/.
    - Other PDFs saved to ~/Downloads in the last `days` days (publisher names such as 1-s2.0-<PII>-main.pdf, or what
      the user typed): moved only when they are certainly a paper the queue is waiting for (identified by PMID, PII,
      printed DOI or a unique title AND the title check passes). Everything else in Downloads is left alone.
    A PDF that starts "Supporting Information" / "Supplementary material" is a supplement whatever its name."""
    INBOX.mkdir(exist_ok=True)
    lock = open(INBOX / '.file.lock', 'w')
    fcntl.flock(lock, fcntl.LOCK_EX)  # two `file` runs (Codex and a chat) never handle the same file
    with Queue(write=False) as q:
        queue = dict(q.rows)
    dl = Path.home() / 'Downloads'
    named = [f for f in sorted(dl.glob('*')) if f.is_file() and id_in_name(f.name) and not f.name.endswith(PARTIAL)
             and (not is_standin(id_in_name(f.name)) or id_in_name(f.name) in queue)]  # NP........: only a queued stand-in
    since = time.time() - days * 86400
    loose = [f for f in sorted(dl.glob('*')) if f.is_file() and f.suffix.lower() == '.pdf' and f not in named
             and max(f.stat().st_mtime, f.stat().st_ctime) >= since]  # a Finder copy keeps its old date
    inbox = [f for f in sorted(INBOX.rglob('*')) if f.is_file() and 'unmatched' not in f.parts and not f.name.startswith('.')
             and not f.name.endswith(PARTIAL) and not (f.suffix.lower() == '.json'
             and b'CatLog Human Review Results' in f.open('rb').read(4096))]  # review results files: `review ingest`
    filed = left = 0

    def park(f, where, why, pmid='-'):
        dest = where / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest = dest.with_name(f'{dest.stem}_{time.time_ns()}{dest.suffix}')
        shutil.move(str(f), str(dest))
        log(pmid, 'file_unmatched' if where.name == 'unmatched' else 'file_rejected', f.name, why)
        print(pmid if pmid != '-' else f.name, '->', dest.relative_to(ROOT), ':', why)

    for f in named + inbox + loose:
        try:
            if not f.exists():
                continue  # taken by another run meanwhile
            is_loose = f in loose
            pmid, how = identify(f, queue)
            r = queue.get(pmid, {}) if pmid else {}
            status = r.get('status', '')
            if is_loose:  # not named for us: touch it only when it is certainly a paper we are waiting for
                sure = pmid and (not is_standin(pmid) or how == 'DOI printed in the file') and r.get('title') and (status in WAITING or status == 'todo' and not (TEXTS / f'{pmid}.txt').exists()) \
                    and not known_bad(pmid, f) and pdf_pages(f) >= 2 and title_ok(r['title'], first_pages_text(f))
                if not sure:
                    left += 1
                    continue
            if not pmid:
                park(f, INBOX / 'unmatched', how)
                continue
            rel = f.relative_to(INBOX).parts if INBOX in f.parents else ()
            pdf = f.suffix.lower() == '.pdf'
            head = first_pages_text(f)[:300] if pdf else ''
            is_supp = (len(rel) > 1 and bool(id_folder(rel[0]))) or bool(SUPP_NAME.search(f.name)) or f.suffix.lower() in SUPP_EXT \
                or bool(SUPP_HEAD.search(head))
            if is_supp and pmid not in queue:
                park(f, INBOX / 'unmatched', 'PMID not in papers.tsv: check the number', pmid)
                continue
            if is_supp:
                d = ROOT / 'papers' / f'{pmid}_supp'
                if d.exists() and any(g.is_file() and file_sha(g) == file_sha(f) for g in d.rglob('*')):
                    park(f, ROOT / 'papers' / 'rejected', 'duplicate of a supplement already filed', pmid)
                    continue
                why = foreign_supplement(f, r)  # another article's supplement must not join this paper
                if why:
                    park(f, ROOT / 'papers' / 'rejected', why, pmid)
                    continue
                d.mkdir(parents=True, exist_ok=True)
                dest = d / f.name if not (d / f.name).exists() else d / f'{f.stem}_{time.time_ns()}{f.suffix}'
                shutil.move(str(f), str(dest))
                if add_supplement(pmid, [dest], 'downloaded'):
                    print(pmid, 'supplement filed'); filed += 1
                else:
                    log(pmid, 'supplement_unreadable', dest.name)
                    print(pmid, dest.name, 'kept in papers/', f'{pmid}_supp/ but no text could be read from it '
                          '(save tables as .xlsx or .csv into inbox/<PMID>/)')
                continue
            if not pdf:  # a saved web page or XML of the article: ask for the PDF instead
                park(f, INBOX / 'unmatched', 'not a PDF: save the PDF (supplementary files go in inbox/<PMID>/)', pmid)
                continue
            try:
                title = r.get('title') or epmc_meta(pmid).get('title', '')
            except RuntimeError:
                print(pmid, f.name, 'left in place: no title to check against (paper lookup offline)')
                continue
            if file_paper(f, pmid, how, title, status):
                filed += 1
                if status in WAITING:
                    queue[pmid] = {**r, 'status': 'todo'}  # a second copy in this run is a duplicate, not a re-download
        except FileNotFoundError:
            continue  # moved by another run meanwhile
    for d in sorted(INBOX.rglob('*'), reverse=True):  # tidy the empty folders the files came in (deepest first)
        if d.is_dir() and 'unmatched' not in d.parts and not any(d.iterdir()):
            d.rmdir()
    fcntl.flock(lock, fcntl.LOCK_UN); lock.close()
    print(f'{filed} of {len(named) + len(inbox) + len(loose) - left} files filed' if named or inbox or loose else 'nothing to file',
          f'({left} other PDFs from the last {days} days in ~/Downloads are not papers we wait for: left there)' if left else '')


# Lines CatLog writes into a text, never printed by the paper: the GLYPH WARNING line (tools/fetch.py glyph_warning and
# scan_warning, atop a text, a supplement PDF's part or an older copy), a supplement file's '--- name ---' header
# (add_supplement) and jats_to_text's image-table note. Their numbers ('378C is 37 °C', '12.3 6 0.4', page lists, file
# names) counted as printed in every warned text (item 21 of writing/research/FIXES_FOR_OTHER_CHATS_20261104.md).
OWN_LINES = re.compile(r'^(?:GLYPH WARNING: .*|--- [^\n/]+\.(?i:pdf|docx?|xlsx|xlsm|xls|csv|tsv|txt|rtf|zip) ---|'
                       r'TABLE IS AN IMAGE ONLY \(.*\): its values are not in this text)$', re.M)


def paper_only(text):
    """A text without the lines CatLog wrote into it (OWN_LINES): what the printed-in-the-paper tests read."""
    return OWN_LINES.sub('', text)


def paper_text(pmid):
    """Main text plus the supplement text, when one was added (texts/<PMID>.supp.txt), without CatLog's own lines."""
    t = (TEXTS / f'{pmid}.txt').read_text()
    supp = TEXTS / f'{pmid}.supp.txt'
    return paper_only(t + ('\n\n=== SUPPLEMENT ===\n' + supp.read_text() if supp.exists() else ''))


def supp_to_text(path):
    """Text of a supplementary file: PDF via pdftotext, spreadsheets as ' | ' rows, CSV/TXT as is."""
    n = path.name.lower()
    if n.endswith('.pdf'):
        return to_text(path)
    if n.endswith('.xls'):
        try:
            import xlrd
        except ImportError:
            return ''
        head = path.read_bytes()[:4]
        if head.startswith(b'PK'):  # an .xlsx saved with an .xls name
            import openpyxl
            return '\n'.join(' | '.join('' if c is None else str(c) for c in row) for ws in
                             openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets for row in ws.iter_rows(values_only=True))
        if head.lstrip().startswith(b'<'):  # an HTML table saved as .xls
            return re.sub(r'<[^>]+>', ' ', path.read_text(errors='replace'))
        out = []
        for sh in xlrd.open_workbook(str(path)).sheets():
            out.append(f'=== Sheet: {sh.name}')
            out += [' | '.join(str(c.value) for c in sh.row(i)) for i in range(sh.nrows)]
        return '\n'.join(out)
    if n.endswith(('.xlsx', '.xlsm')):
        import openpyxl
        out = []
        for ws in openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets:
            out.append(f'=== Sheet: {ws.title}')
            out += [' | '.join('' if c is None else str(c) for c in row) for row in ws.iter_rows(values_only=True)]
        return '\n'.join(out)
    if n.endswith(('.csv', '.tsv', '.txt')):
        return path.read_text(errors='replace')
    if n.endswith(('.docx', '.doc', '.rtf')):
        return subprocess.run(['textutil', '-convert', 'txt', '-stdout', str(path)], capture_output=True, text=True, errors="replace").stdout
    if n.endswith('.zip'):  # a journal's supplement bundle: unpack next to it and read every member
        import zipfile
        out_dir = path.with_name(path.stem)
        out_dir.mkdir(exist_ok=True)
        parts = []
        with zipfile.ZipFile(path) as z:
            for m in z.namelist():
                name = Path(m).name
                if m.endswith('/') or '__MACOSX' in m or not name or name.startswith('.'):
                    continue
                (out_dir / name).write_bytes(z.read(m))
                t = supp_to_text(out_dir / name)
                if t.strip():
                    parts.append(f'--- {name} ---\n{t}')
        return '\n\n'.join(parts)
    return ''


def add_supplement(pmid, files, how):
    """Append supplementary files' text to texts/<PMID>.supp.txt and send the paper back to be read again."""
    def read_or_empty(f):
        try:
            return supp_to_text(f)
        except Exception:  # a corrupt or disguised file: reported as unreadable, never a crash
            return ''
    parts = [f'--- {f.name} ---\n' + read_or_empty(f) for f in files]
    text = '\n\n'.join(p for p in parts if len(p) > 200)
    if not text:
        return False
    supp = TEXTS / f'{pmid}.supp.txt'
    old = supp.read_text() if supp.exists() else ''
    if supp.exists():
        supp.chmod(0o644)
    supp.write_text(old + ('\n\n' if old else '') + text); supp.chmod(0o444)
    with Queue() as q:
        r = q.rows.get(pmid, {})
        if r.get('status') == 'reading':
            (WORK / f'{pmid}.supp_arrived').touch()  # finish() sends the paper back to be read with it
        elif r.get('status') in REDOWNLOAD + ('needs_browser',) or not (TEXTS / f'{pmid}.txt').exists():
            q.set(pmid, note=f"{r.get('note', '')}; supplement on file"[:200])  # still waiting for the article itself
        else:
            q.set(pmid, status='todo', note=f'supplement added ({how}); read again')
    log(pmid, 'supplement', how, ' '.join(f.name for f in files))
    return True


def cmd_supp(n):
    """For papers flagged needs_supplement: fetch open-access supplements from Europe PMC automatically."""
    import io, zipfile
    from collections import Counter
    with Queue() as q:
        want = [p for p, r in q.rows.items() if r['status'] == 'needs_supplement'
                and not (TEXTS / f'{p}.supp.txt').exists()]  # a second request needs a person (asks), not the same zip
        info = {p: q.rows[p] for p in want}
    got = 0
    tries = Counter(f[1] for f in events() if f[2] == 'supp_none')
    ranked = {p: i for i, p in enumerate(priority(want))}
    for pmid in sorted(want, key=lambda p: (tries[p], ranked[p]))[:n]:  # least-tried first: every paper gets its turn
        try:
            pmcid = epmc_meta(pmid).get('pmcid')
            data = http(f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/supplementaryFiles', timeout=120) if pmcid else b''
        except Exception:
            data = b''
        files = []
        if data[:2] == b'PK':
            d = ROOT / 'papers' / f'{pmid}_supp'
            d.mkdir(parents=True, exist_ok=True)
            for name in zipfile.ZipFile(io.BytesIO(data)).namelist():
                if name.lower().endswith(('.pdf', '.xlsx', '.xlsm', '.xls', '.csv', '.tsv', '.txt', '.docx', '.doc')):
                    out = d / Path(name).name
                    out.write_bytes(zipfile.ZipFile(io.BytesIO(data)).read(name)); files.append(out)
        how = 'europepmc'
        if not files and 'image' in info[pmid].get('note', '').lower() and info[pmid].get('title'):
            try:
                pdf = openalex_pdf(pmid, title_ok, info[pmid]['title'], doi=info[pmid].get('doi', ''))  # tables the XML only has as pictures
            except RuntimeError:
                pdf = None  # an outage: tried again in a later batch
            if pdf:
                d = ROOT / 'papers' / f'{pmid}_supp'; d.mkdir(parents=True, exist_ok=True)
                out = d / f'{pmid}.article_pdf_ocr.txt'; out.write_text(ocr_pdf(pdf)); files, how = [out], 'OCR of the article PDF'
        if files and add_supplement(pmid, files, how):
            got += 1; print(pmid, 'supplement added:', how)
        else:
            log(pmid, 'supp_none', how)
            print(pmid, 'no open-access supplement: download it (worklist supplement)')
    print(f'{got} of {min(n, len(want))} supplements fetched')


# ---------- check + add ----------

def squash(s):
    return re.sub(r'[\s|]+', ' ', clean(s)).strip().lower()


def numbers(s):
    return re.findall(r'\d+(?:\.\d+)?', clean(s).replace(',', ''))


def quote_found(q, text_sq):
    """Exact (whitespace-insensitive) match, or, for PDF text whose columns got split, every quote
    token in order with gaps under 400 characters, starting from some occurrence of the first token."""
    def find(tok, i, end=None, edge=False):
        """Position of tok at or after i (and before end); a token with digits must not be part of a longer number.
        edge: checked only on the side where the token starts or ends with a number, so a unit glued to the number
        before it still matches ('s^-1.' in 'm^-1s^-1.' where the quote spaced the units: 6 legend values of 28362483
        were rejected quote_not_in_paper until 2026-11-09)."""
        end = len(text_sq) if end is None else min(end, len(text_sq))
        if edge:
            left, right = bool(re.match(r'\.?\d|[-+−±]\d', tok)), bool(re.search(r'\d\.?$', tok))
        else:
            left = right = bool(re.search(r'\d', tok))
        j = text_sq.find(tok, i, end)
        while j >= 0 and ((left and j and (text_sq[j - 1].isdigit() or text_sq[j - 1] == '.'))
                          or (right and j + len(tok) < len(text_sq) and text_sq[j + len(tok)].isdigit())):
            j = text_sq.find(tok, j + 1, end)
        return (j, j + len(tok)) if j >= 0 else (-1, -1)

    def chain(edge):
        if find(q, 0, edge=edge)[0] >= 0:
            return True
        toks = q.split()
        if not toks:
            return False
        start, end = find(toks[0], 0, edge=edge)
        while start >= 0:
            i, ok = end, True
            for t in toks[1:]:
                j, e = find(t, i, i + 400 + len(t), edge=edge)
                if j < 0:
                    ok = False; break
                i = e
            if ok:
                return True
            start, end = find(toks[0], start + 1, edge=edge)
        return False
    # the strict pass first, exactly as before (a quote that matched still matches); the edge pass only adds matches
    return chain(False) or chain(True)


from functools import lru_cache


@lru_cache(maxsize=8)
def printed_numbers(text_sq):
    """Every number printed in a paper (computed once per paper text, not once per row)."""
    return frozenset(float(n) for n in numbers(text_sq))


LIMITS = {'kcat': 1e8, 'Km': 1e4, 'kcat/Km': 1e7}  # s^-1, mM, mM^-1 s^-1 (diffusion limit)
# kcat: catalase (~4x10^7 s^-1) and carbonic anhydrases (SazCA, CA IX 1-3x10^7 s^-1) are measured above 10^7 (2026-10-12)


def check(row, text_sq):
    """Deterministic checks. Returns (normalized fields, list of failure reasons)."""
    # a unit_for_conversion (the column header's unit, or a verifier's fix) is the unit the cell is converted with, so it
    # stands in for an empty raw_unit (23946505 lost 25 confirmed kcat/Km values to missing:raw_unit, 2026-10-22)
    # a censored row (a bound or "not detected", 2026-10-24) needs no unit: a "not detected" sentence prints none, and a
    # bound whose unit is not printed keeps its printed cell without a converted limit
    cens = censored_kind(row)
    bad = [f'missing:{k}' for k in NEEDED if not str(row.get(k, '')).strip()
           and not (k == 'raw_unit' and (cens or str(row.get('unit_for_conversion') or '').strip()))]
    if row.get('metric') not in METRICS:
        bad.append(f"bad_metric:{row.get('metric')}")
    if cens and cens not in ('<', '>', 'not_detected'):
        bad.append(f'bad_censored:{cens}')
    q = squash(row.get('quote', ''))
    if q and not quote_found(q, text_sq):
        bad.append('quote_not_in_paper')
    raw = clean(row.get('raw_value', ''))
    nums = numbers(raw)
    forms = [row.get('quote', ''), re.sub(r'(\d\.)\s+(\d)', r'\1\2', row.get('quote', ''))]  # XML '596. 4' is 596.4
    # A scan of a journal that printed the raised decimal point ('0·34') OCRs it as a hyphen ('0-34'). When the whole
    # quote is in that form (no digit.digit anywhere), read those hyphens as decimal points: NPEBD0B162 (Phytochemistry
    # 1973) lost all 20 of its confirmed values to value_not_in_quote.
    if not re.search(r'\d\.\d', forms[0]) and re.search(r'\d-\d', forms[0]):
        forms.append(re.sub(r'(?<=\d)-(?=\d)', '.', forms[0]))
    if cens == 'not_detected':  # the printed marker or words ('ND', 'no detectable activity'), as a whole word; a
        mark = squash(raw)      # footnote letter may stick to it ('NDa', 10206992); a '0' must be a whole number
        if re.fullmatch(r'[\d.]+', mark or 'x'):
            found = mark in numbers(row.get('quote', ''))
        else:  # a footnote mark may also come first ('^aNA', 42688155): read it as a space; the marker may also BE
            # a footnote mark ('^b', footnote b: not detected; 70 bounds of 7 papers, e.g. 16901567), so try both
            sq = squash(row.get('quote', ''))
            pat = r'(?<![a-z0-9])' + re.escape(mark) + r'(?![0-9]|[a-z]{2})'
            found = bool(mark) and any(re.search(pat, f) for f in (sq, re.sub(r'\^\{?[a-z*†‡§]\}?', ' ', sq)))
        if not found:
            bad.append('marker_not_in_quote')
    elif cens and not nums:
        bad.append('bound_without_number')
    elif cens and SIGN_OF(raw) != cens:  # '< 0.01' is '<': the printed sign or words decide, never the reader's label
        bad.append(f'censored_sign_mismatch:{cens} for {raw[:20]}')
    elif nums and all(nums[0] not in numbers(f) for f in forms):
        # a glyph-damaged text layer prints '384 ± 6.2' as '38466.2' (GLYPH WARNING papers): the joined form counts
        glued = re.sub(r'\s*\u00b1\s*', '6', raw).replace(' ', '')
        if '\u00b1' not in raw or glued not in re.sub(r'\s', '', clean(row.get('quote', ''))):
            bad.append('value_not_in_quote')
    fixed = {}
    if not cens and nums and not re.search(r'\u00b1|\+/-|\(', raw):
        quote = re.sub(r'[\s|]+', ' ', clean(row.get('quote', '')))
        # not when the \u00b1 term carries its own exponent ('59.40 \u00b1 4 x 10^-4', PMID 16792995): '\u00b1 4' would overstate it
        m = re.search(r'(?<![\d.])' + re.escape(nums[0]) +
                      r'\s*(?:\u00b1|\+/-)\s*\d+(?:\.\d+)?(?![\d.])(?!\s*(?:x|\*|\u00d7)\s*10)', quote)
        once = len(re.findall(r'(?<![\d.])' + re.escape(nums[0]) + r'(?![\d.])', quote)) == 1  # 33 (kcat/Km) beside Km 33 ± 9.4
        if m and raw.strip() == nums[0] and once:
            fixed['raw_value'] = m.group(0)  # the reader dropped the printed ± : complete it from the quote
    body = re.sub(r'(?:x|\*)\s*10\s*\^?\s*\(?-?\s*\d+\)?|[eE][-+]?\d+', '', raw.split('\u00b1')[0])  # exponents are not ranges
    # a value followed by the interval around it in brackets is the value with its confidence interval, not a range:
    # '27,828 (24,558\u201331,987)', '38.5 \u03bcM (35.2\u201342.0 \u03bcM)' (42249657: 9 values lost to bound_or_range)
    ci = re.match(r'\s*([\d.,]+)[^\d(]*\(\s*([\d.,]+)[^\d\-\u2013]*[\-\u2013]\s*([\d.,]+)[^\d)]*\)\s*$', body)
    try:
        if ci and float(ci.group(2).replace(',', '')) <= float(ci.group(1).replace(',', '')) <= float(ci.group(3).replace(',', '')):
            body = ci.group(1)
    except ValueError:
        pass
    if not cens and (re.match(r'\s*(?:<|>|\u2264|\u2265|ca\.?\s*$)', raw) or re.search(r'\d\s*-\s*\d', body)):
        bad.append('bound_or_range')
    elif cens in ('<', '>') and re.search(r'\d\s*[-\u2013]\s*\d', body):  # a range is no bound
        # not a not-detected row: its raw value is the printed words, and their numbers are names ('No \u03b2 1\u20134 glucanase
        # activity', 'except for M4-4', 'hFXII\u2013CP110 \u2013128': all 9 such rejects to 2026-11-08); its limit is read by bound_of
        bad.append('range_not_a_bound')
    printed = printed_numbers(text_sq)
    for k in ('pH', 'temperature_C'):
        v = row.get(k)
        if v in (None, ''):
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):  # '25 °C', '7.5-8.0', 'room temperature': unknown as a number, not a reason to lose the value
            note = fixed.get('condition_note') or row.get('condition_note')
            fixed[k] = None
            fixed['condition_note'] = f'{k} "{v}" is not a number: left empty' + (f'; {note}' if note else '')
            continue
        # a PDF text layer that prints ° as 8: '378C', and 'at 378' where the paper wrote 'at 37°' with no C
        # (PMID 20564561, 66 values). 'at 348 nm' / 'at 298 k' / 'at 48 h' are a wavelength, a kelvin and a time.
        degree_as_8 = lambda: k == 'temperature_C' and v == int(v) and re.search(
            rf'(?<![\d.]){int(v)}8 ?c\b|(?<![\d.])at {int(v)}8\b(?! ?(?:°|(?:nm|k|kda|mpa|kpsi|h|min|s|ms|ns|mm|µm|um|m|rpm|g|%)(?![a-z0-9])))',
            text_sq)
        if (k == 'pH' and not 0 < v <= 14) or (v not in printed and not degree_as_8() and
                not (k == 'temperature_C' and (round(v + 273.15, 2) in printed or round(v + 273) in printed))):
            note = fixed.get('condition_note') or row.get('condition_note')
            fixed[k] = None  # a condition the paper does not print is unknown, not a reason to lose the value
            fixed['condition_note'] = f"{k} {v:g} is not printed in the paper: left empty" + (f'; {note}' if note else '')
    if cens:  # never a value: the limit, when one is printed, converted into catalog units as `bound`
        bound, bunit, why = bound_of(row, cens)
        lim = numbers(str(row.get('limit') or ''))
        if cens == 'not_detected' and bound is not None and lim and float(lim[0]) not in printed_numbers(text_sq):
            bound, bunit, why = None, None, f'limit "{str(row.get("limit"))[:40]}" is not printed in the paper: left out'

        return {'value': None, 'unit': bunit, 'censored': cens, 'bound': bound, **({'bound_note': why} if why else {}), **fixed}, bad
    value, unit = None, None
    if row.get('metric') in METRICS:
        value, unit, err = normalize(row['metric'], row.get('raw_value', ''), row.get('unit_for_conversion') or row.get('raw_unit', ''))
        if err:
            bad.append(err)
        elif not (value > 0):
            bad.append('non_positive_value')
        else:
            value = float(f'{value:.6g}')
            if value > LIMITS[row['metric']]:
                bad.append('beyond_physical_limit')
    return {'value': value, 'unit': unit, **fixed}, bad


SIGN = r'(?:<=|>=|<|>|\u2264|\u2265|\u226a|\u226b|\u2aa1|\u2aa2|less than|lower than|below|under|smaller than|greater than|higher than|larger than|above|over|exceed\w*|more than|up to)'
# '\u226a'/'\u2aa1' (much less than) and '\u226b'/'\u2aa2' (much greater than) are bounds too (18669639 prints '\u226b12')
SIGN_OF = lambda raw: ('<' if re.match(r'\s*(?:<|\u2264|\u226a|\u2aa1|less|lower|below|under|smaller|up to)', raw, re.I) else
                       '>' if re.match(r'\s*(?:>|\u2265|\u226b|\u2aa2|greater|higher|larger|above|over|exceed|more)', raw, re.I) else '')


def censored_kind(row):
    """'<', '>' or 'not_detected' for a censored row (prompts/read.md "Censored values"), '' for a value; an unknown kind
    as written (check() rejects it)."""
    c = str(row.get('censored') or '').strip()
    if c.lower() in ('', 'none', 'no', 'false', 'null', 'n/a', 'na', '-', 'ordinary', 'value'):  # a filled-in blank
        return ''
    return CENSORED.get(c.lower(), c)


def bound_of(row, cens):
    """(limit in catalog units, its unit, note) of a censored row: the printed number of a '<' or '>' cell (with the row's
    unit), or the detection limit a not-detected row's `limit` prints with its own unit ('< 0.001 s^-1'). (None, None, '')
    when nothing is printed; (None, None, why) when it does not convert (a limit in % of wild-type activity)."""
    text = str(row.get('raw_value', '') if cens in ('<', '>') else row.get('limit') or '').strip()
    if not text or row.get('metric') not in METRICS:
        return None, None, ''
    text = clean(text)
    if cens == 'not_detected':  # a limit copied with its footnote ('ND, < 0.001 s^-1'): from its comparator or number on
        m = re.search(r'(?:<=|>=|<|>|\u2264|\u2265|\u226a|\u226b|\u2aa1|\u2aa2)|\d', text)
        text = text[m.start():] if m else text
    num = re.sub(r'^\s*' + SIGN + r'\s*', '', text, flags=re.I)
    num = re.sub(r'^\s*10\s*\^\s*\(?\s*([-+\u2212]?\s*\d+)\s*\)?', r'1 x 10^\1', num)  # '<10^-4' is 1 x 10^-4, not 10
    unit = row.get('unit_for_conversion') or row.get('raw_unit') or ''
    if cens == 'not_detected':
        m = re.match(r'\s*([-+]?[\d.,]+(?:\s*(?:[x\u00d7*]\s*10\s*\^?\s*[-\u2212]?\s*\d+|[eE][-+]?\d+))?)\s*(.*)$', num)
        if not m:
            return None, None, f'detection limit "{text[:40]}" has no number'
        num, unit = m.group(1), (m.group(2).strip() or unit)
    v, u, err = normalize(row['metric'], num, unit)
    if err or v is None or not v > 0:
        return None, None, f'limit not converted ({err or "not a positive number"})'
    return float(f'{v:.6g}'), u, ''


TUPLE = ('organism', 'enzyme', 'variant', 'substrate', 'cosubstrate', 'pH', 'temperature_C', 'conditions', 'location')
IDENT = ('pmid', 'organism', 'enzyme', 'variant', 'substrate', 'cosubstrate', 'pH', 'temperature_C', 'location')
# plus `construct` when given: values from different preparations (truncation, tag, native vs recombinant) never pair


def construct_of(r):
    return str(r.get('construct') or '').strip().lower()


def gene_of(r):
    """The printed gene/locus and strain: paralogs a reader names alike ('AtChlADR' At1g54870 and At3g04000, PMID
    21169366) and one species' strains (Enterobacter cloacae P99 and 908R, PMID 3264155) stay apart. Empty for most
    rows, so their slots and groups are unchanged."""
    gene, strain = (str(r.get(k) or '').strip().lower() for k in ('gene', 'strain'))
    return gene + (f'|strain:{strain}' if strain else '')
# 'apparent molecular weight Mr ...' is an assay state, not a per-value qualifier: PMID 7470464 prints Km per enzyme
# aggregation state, and setting it aside put 11 states in one slot (21 verified values rejected as conflicts)
QUALIFIER = re.compile(r'^(apparent|app\.?|hill fit|approximate|paper-declared approximate|estimated|'
                       r'kcat (calculated|derived) from|paper states)\b(?!.*\b(molecular weight|Mr \d))', re.I)


def condition_parts(cond):
    """(shared assay segments, metric-specific qualifier segments) of a conditions text split on ';'."""
    segs = [re.sub(r'\s+', ' ', s).strip() for s in (cond or '').split(';') if s.strip()]
    return [s for s in segs if not QUALIFIER.match(s)], [s for s in segs if QUALIFIER.match(s)]


def measurements(rows):
    """Group rows into measurements: same paper, enzyme, organism, variant, substrate, cosubstrate, pH, temperature and
    location, and the same assay - after setting aside per-value qualifiers ('apparent', 'Hill fit', ...), one row's
    condition segments must contain the other's. Each metric at most once. If a row could join more than one
    measurement, nothing in that identity group is paired (one row per measurement), as before. Then values of one
    printed line that this kept apart, only by spelling or an ambiguity the line itself settles, are joined
    (join_lines, 2026-11-11)."""
    ident = {}
    for r in rows:
        ident.setdefault(tuple(str(r.get(k, '')).strip().lower() for k in IDENT) + (construct_of(r), gene_of(r)), []).append(r)
    out = []
    for g in ident.values():
        clusters, ambiguous = [], False
        for r in g:
            s = frozenset(x.lower() for x in condition_parts(r.get('conditions'))[0])
            fits = [c for c in clusters if (s <= c[0] or c[0] <= s) and r['metric'] not in {x['metric'] for x in c[1]}]
            clash = [c for c in clusters if (s <= c[0] or c[0] <= s) and r['metric'] in {x['metric'] for x in c[1]}]
            if len(fits) > 1 or (fits and clash) or (clash and any(len(c[1]) > 1 for c in clash)):
                ambiguous = True
            if fits:
                fits[0][0] = fits[0][0] | s; fits[0][1].append(r)
            else:
                clusters.append([s, [r]])
        if ambiguous:
            out += [[r] for r in g]
        else:
            out += [c[1] for c in clusters]
    return join_lines(out)[0]  # one printed line's values that spelling kept apart: one measurement (join_lines)


# One printed line, several records (Reviewer C's review, 2026-11-11; work/record_merge_20261111/HANDOFF.md): a table row's kcat
# and Km sat in two records because two reads spelled the substrate or enzyme differently ('Abz-AGGRGDGQ-EDDnp' /
# 'Abz-A-G-G-R-G-D-G-Q-EDDnp', 16431280) or measurements() could not tell which values pair. join_lines() joins them
# under strict tests: a first, looser rule made 12 wrong joins in 74 checked against the papers (a kcat of one assay
# with a Km of another on one row); this one made none of those 12 and passed a fresh blind check of 60 joins in 22
# papers and an adversarial review of all its joins (check_results_v1.json, check_results_v2.json there).
from collections import defaultdict
import functools


@functools.lru_cache(maxsize=None)
def _line_key(quote):
    return re.sub(r'\s+', '', squash(quote).replace('↓', ''))


def line_of(r):
    """The printed line a value quotes, spacing and a peptide's cleavage mark aside (cached by the quote's text)."""
    return _line_key(str(r.get('quote', '') or ''))

def plain_name(s):
    """A compound or enzyme name without separators (hyphens, spaces, brackets' own marks; never a sign, prime, comma or
    colon: twin()'s rule), Greek letters spelled out, a peptide's cleavage mark aside."""
    s = re.sub('[αβγδεκλω]', lambda m: GREEK.split('|')['αβγδεκλω'.index(m.group())], squash(s or '').replace('↓', ''))
    return re.sub(r'[\s_\-‐‑\[\]{}^]', '', s.translate(SUBSCRIPT))

def same_enzyme(x, y):
    """Equal names, a bracketed gloss on one side only ('TrpB' / 'tryptophan synthase beta-subunit (TrpB)' too: a name
    equal to the other's bracketed label). Never one name inside another ('KPC-2' / 'KPC-28', 'trypsin' / 'chymotrypsin')."""
    a, b = squash(x or ''), squash(y or '')
    if a == b or plain_name(a) == plain_name(b):
        return True
    for p, q in ((a, b), (b, a)):
        if '(' not in p and '(' in q:
            if plain_name(p) == plain_name(re.sub(r'\([^()]*\)', '', q)):
                return True
            if any(plain_name(p) == plain_name(lab) for lab in re.findall(r'\(([^()]*)\)', q)):
                return True
    return False

OPPOSED = (('native', 'recombinant'), ('truncated', 'full'), ('mature', 'precursor'), ('tagged', 'untagged'),
           ('monomer', 'dimer'), ('monomeric', 'dimeric'), ('control', 'treated'), ('apo', 'holo'), ('reduced', 'oxidized'))
TAG_NAMES = re.compile(r'\b(his|gst|mbp|strep|flag|sumo|trx|gfp|myc|ha)\b')
NUM = re.compile(r'\d+(?:\.\d+)?')

def same_construct(a, b):
    """Two construct notes that may describe one preparation: one is empty, or they share at least half of the shorter
    one's words, carry no number the other lacks on both sides (residue spans, Δ ranges, masses, pI) and say nothing
    opposed (native / recombinant, N- / C-terminal, two different tags, monomer / dimer)."""
    ca, cb = construct_of(a), construct_of(b)
    if not ca or not cb or ca == cb:
        return True
    ta, tb = (set(re.findall(r'[a-z0-9]{3,}', c)) for c in (ca, cb))
    if len(ta & tb) < 0.5 * min(len(ta), len(tb)):
        return False
    na, nb = set(NUM.findall(ca)), set(NUM.findall(cb))
    if not (na <= nb or nb <= na):
        return False
    for x, y in OPPOSED:
        if (x in ta and y not in ta and y in tb and x not in tb) or (y in ta and x not in ta and x in tb and y not in tb):
            return False
    ends = [set(re.findall(r'\b([nc])-termin', c)) for c in (ca, cb)]
    if ends[0] and ends[1] and ends[0] != ends[1]:
        return False
    tags = [set(TAG_NAMES.findall(c)) for c in (ca, cb)]
    return not (tags[0] and tags[1] and tags[0] != tags[1])

def both_or_neither(x, y, same):
    x, y = str(x if x is not None else '').strip(), str(y if y is not None else '').strip()
    return (not x and not y) or (bool(x) and bool(y) and same(x, y))

def same_identity(a, b):
    """Two values of one paper name the same enzyme, variant, substrate and assay point, spelling aside: nothing one
    read gives and the other leaves out counts as the same, except the organism, gene, strain and construct."""
    from enrich import binomial
    if not (same_variant(a, b) or spelled_out(a.get('variant', ''), b.get('variant', '')) or spelled_out(b.get('variant', ''), a.get('variant', ''))):
        return False
    if plain_name(a.get('substrate', '')) != plain_name(b.get('substrate', '')):
        return False
    if not both_or_neither(a.get('cosubstrate'), b.get('cosubstrate'), lambda x, y: plain_name(x) == plain_name(y)):
        return False
    for k in ('pH', 'temperature_C'):
        if not both_or_neither(a.get(k), b.get(k), lambda x, y: isnum(x) and isnum(y) and float(x) == float(y)):
            return False
    if not same_enzyme(a.get('enzyme', ''), b.get('enzyme', '')):
        return False
    oa, ob = (binomial(str(r.get('organism') or '')).strip().lower() for r in (a, b))
    if oa and ob and oa != ob:
        return False
    for k in ('gene', 'strain'):
        ga, gb = (str(r.get(k) or '').strip().lower() for r in (a, b))
        if ga and gb and ga != gb:
            return False
    return same_construct(a, b)

NEGATION = {'without', 'absence', 'absent', 'omitted', 'omitting', 'lacking', 'minus', 'no', 'devoid', 'excluding',
            'removed', 'free'}
OPPOSED_ASSAY = (('oxidized', 'reduced'), ('oxidised', 'reduced'), ('single', 'multiple'), ('forward', 'reverse'),
                 ('atpase', 'kinase'))


def opposed_conditions(a, b):
    """One assay with and one without something ('without DTT' / 'with 2 mM DTT', 23387521; 'homoserine omitted ...
    (inherent ATPase activity)' / the kinase assay, 8973190), or two opposed assays (oxidized / reduced, single /
    multiple turnover, forward / reverse, ATPase / kinase): the words one condition text has and the other lacks."""
    wa, wb = (set(re.findall(r'[a-z]+', str(r.get('conditions') or '').lower())) for r in (a, b))
    if (wa ^ wb) & NEGATION:
        return True
    return any((x in wa and y in wb and not (y in wa and x in wb)) or (y in wa and x in wb and not (x in wa and y in wb))
               for x, y in OPPOSED_ASSAY)


def same_conditions(a, b):
    """One assay: the shared condition segments of one hold the other's (measurements()' own test), or the two texts
    are one description worded twice: every number of one is in the other and they share at least half of the shorter
    one's words ('100 mM Tris-HCl buffer pH 8.5; ... (excitation 320 nm ...)' twice, 16431280; never a multiple-
    turnover run with BSA and a single-turnover run with C12E8, 11420444)."""
    if opposed_conditions(a, b):
        return False
    sa, sb = (frozenset(x.lower() for x in condition_parts(r.get('conditions'))[0]) for r in (a, b))
    if sa <= sb or sb <= sa:
        return True
    ta, tb = ' '.join(sorted(sa)), ' '.join(sorted(sb))
    na, nb = set(NUM.findall(ta)), set(NUM.findall(tb))
    if not (na <= nb or nb <= na):
        return False
    wa, wb = set(re.findall(r'[a-z]{3,}', ta)), set(re.findall(r'[a-z]{3,}', tb))
    return len(wa & wb) >= 0.5 * min(len(wa), len(wb))

def closes(by):
    """kcat / Km within 1.5x of the printed kcat/Km, both over the same kind of concentration."""
    k, km, e = by['kcat'], by['Km'], by['kcat/Km']
    if (km.get('unit') in MASS_UNIT.values()) != (e.get('unit') in MASS_UNIT.values()):
        return False
    try:
        q = k['value'] / km['value']
        return max(e['value'] / q, q / e['value']) <= 1.5
    except (TypeError, ZeroDivisionError, KeyError):
        return False

PLATEAU = re.compile(r'ph[- ]independent|ph[- ]rate profile|plateau|limiting value', re.I)


def cond_set(r):
    """A row's shared condition segments (slot()'s; per-value qualifiers set aside), lower case, spaces squeezed."""
    return frozenset(' '.join(x.lower().split()) for x in condition_parts(r.get('conditions'))[0])


def join_lines(groups, rivals=None):
    """One printed line's values that spelling kept in several records become one measurement. `rivals`: rows kept out
    of the catalog (rejected.jsonl, bounds.jsonl) that are not copies of an accepted cell on their own line; None reads
    them for the papers that have a line to join (load_rivals)."""
    import functools
    lq = {}
    def lineq(r):
        k = id(r)
        if k not in lq:
            lq[k] = line_of(r)
        return lq[k]
    pname = functools.lru_cache(maxsize=None)(plain_name)
    line, paper, glines = defaultdict(set), defaultdict(list), {}
    for i, g in enumerate(groups):
        paper[g[0]['pmid']].append(i)
        ls = set()
        for r in g:
            q = lineq(r)
            if len(q) >= 12:
                line[(r['pmid'], q)].add(i); ls.add((r['pmid'], q))
        glines[i] = ls
    todo_lines = sorted(k for k, v in line.items() if len(v) > 1)
    if not todo_lines:
        return [list(g) for g in groups], []
    if rivals is None:
        rivals = load_rivals([r for g in groups for r in g], {p for p, _ in todo_lines})
    rival = defaultdict(list)
    for r in rivals:
        q = line_of(r)
        if len(q) >= 12 and (r.get('pmid'), q) in line:
            rival[(r['pmid'], q)].append(r)
    parent = list(range(len(groups)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    members = {i: [i] for i in range(len(groups))}
    rows_of = lambda root: [r for i in members[root] for r in groups[i]]
    base_of = lambda root: groups[members[root][0]][0]
    lines_of = lambda root: set().union(*(glines[i] for i in members[root]))
    ident = {}
    def same(a, b):  # same_identity, cheap test first, cached per pair of rows
        if pname(a.get('substrate', '')) != pname(b.get('substrate', '')):
            return False
        k = (id(a), id(b)) if id(a) < id(b) else (id(b), id(a))
        if k not in ident:
            ident[k] = same_identity(a, b)
        return ident[k]
    by_sub = defaultdict(list)  # paper and substrate -> its groups (the 'again' guard looks only there)
    for i, g in enumerate(groups):
        by_sub[(g[0]['pmid'], pname(g[0].get('substrate', '')))].append(i)
    done = set()
    for key in todo_lines:
        for a in sorted({find(i) for i in line[key]}):
            if a in done or find(a) != a:
                continue
            fam, grew = {a}, True
            while grew:  # every group, on any line a member sits on, that names the same identity
                grew = False
                for L in set().union(*(lines_of(x) for x in fam)):
                    for b in {find(i) for i in line[L]} - fam:
                        if any(same(base_of(x), base_of(b)) for x in fam):
                            fam.add(b); grew = True
            done |= fam
            fam = sorted(fam)
            if len(fam) < 2:
                continue
            bases = [base_of(x) for x in fam]
            if not all(same(p, q) and same_conditions(p, q) for n, p in enumerate(bases) for q in bases[n + 1:]):
                continue
            rows = [r for x in fam for r in rows_of(x)]
            by = {r['metric']: r for r in rows}
            if len(by) != len(rows):
                continue  # a metric twice among records that fit each other: which pairs with which is not known
            L = set().union(*(lines_of(x) for x in fam))
            if any(r.get('metric') in by and any(same_identity(r, p) for p in bases) for l in L for r in rival[l]):
                continue  # the line prints that metric once more for this identity (a value kept out of the catalog)
            whole = all(m in by for m in METRICS)
            if whole and not closes(by):
                continue
            if not whole and any(PLATEAU.search(str(r.get('conditions') or '')) for r in rows):
                continue  # limits of a pH-rate profile: which plateau of one goes with which of the other is not printed
            famset = set(fam)
            # another record of this identity under conditions other than the one wording every member of the family
            # shares is another measurement of the paper (39897407: the same peptides with dsDNA, on their own line), not
            # this assay again; only when the family gives a pH, so a pH-rate profile's limits keep the guard whatever
            # their wording; a family whose members word the conditions differently keeps it too
            one = {cond_set(p) for p in bases}
            one = next(iter(one)) if len(one) == 1 and isnum(bases[0].get('pH')) else None
            elsewhere = lambda i: one is not None and cond_set(groups[i][0]) != one
            again = any(r['metric'] in by for i in by_sub[(bases[0]['pmid'], pname(bases[0].get('substrate', '')))]
                        if find(i) not in famset and not elsewhere(i) for r in groups[i] if any(same(groups[i][0], p) for p in bases))
            if again and not whole:
                continue  # the paper measures this identity more than once: only a kcat, Km and kcat/Km that agree pair
            keep = fam[0]
            for x in fam[1:]:
                parent[x] = keep; members[keep] += members.pop(x)
    said = lambda g: sum(bool(str(g[0].get(k) or '').strip()) for k in ('organism', 'cosubstrate', 'construct', 'gene', 'strain'))
    out, merged = [], []
    for ms in members.values():
        parts = [groups[i] for i in ms]
        if len(parts) > 1:
            parts = sorted(parts, key=lambda g: (-said(g), -len(g)))
            merged.append(([r for g in parts for r in g], parts))
        out.append([r for g in parts for r in g])
    return out, merged

def load_rivals(cat, pmids=None):
    """Rows kept out of the catalog (rejected.jsonl, bounds.jsonl) that print a cell no accepted row on their own line
    holds (a rejected re-read copy of an accepted value is no rival; an equal cell elsewhere in the paper does not hide
    one). `pmids`: read only these papers' rows."""
    pid = re.compile(r'"pmid":\s*"([^"]*)"')
    want = set(pmids) if pmids is not None else None
    have = {(r['pmid'], line_of(r), *printed_cell(r)[1:]) for r in cat if want is None or r['pmid'] in want}
    out = []
    for path in (REJECTED, BOUNDS):
        if path.exists():
            for l in open(path):
                if not l.strip():
                    continue
                m = pid.search(l)
                if want is not None and (not m or m.group(1) not in want):
                    continue
                try:
                    r = json.loads(l)
                except json.JSONDecodeError:
                    continue
                if r.get('pmid') and r.get('metric') in METRICS and r.get('quote') and (r['pmid'], line_of(r), *printed_cell(r)[1:]) not in have:
                    out.append(r)
    return out


BRACKET_PM = re.compile(r'\(\s*(\d+(?:\.\d+)?)\s*(?:\u00b1|\+/-)\s*(\d+(?:\.\d+)?)\s*\)\s*(?:x\s*)?10\s*\^?\s*\(?\s*(-?\d+)\)?')


def printed_err(raw, value, row=None):
    """A printed cell's ± in the stored value's units: the ± term's own number (with an exponent that follows it) times
    the factor code converted the value with (stored value / the number units.parse_number reads in the cell), so the
    error converts exactly as the value did: '(5.1 ± 0.7) x 10^5' M^-1 s^-1 -> 70 mM^-1 s^-1, '12.3 ± 0.4' min^-1 ->
    0.006667 s^-1, and '0.004 ± 0.6 x 10^-3' keeps its exponent on the ± (2026-10-26, the website chat: SABIO-RK,
    EnzymeML and ML users expect a numeric error). None when the cell prints no ± or the value is not stored.
    A bracketed '(a ± u) x 10^n' whose power the paper puts on the ± alone (u > a and u x 10^n < a, units.parse_number's
    test for the unbracketed form) is stored as a, through a unit_for_conversion that is the printed unit times exactly
    10^-n (23294602: '(0.77 ± 3.6) x 10^-3' min^-1 with '10^3 min^-1' is 0.77 ± 0.0036), and the ± keeps its power
    (until 2026-11-03 it took the value's undoing too, 10^3 and 10^5 times too large)."""
    from units import parse_number
    c = clean(raw or '')
    if value is None or not re.search(r'\u00b1|\+/-', c):
        return None
    u, read = parse_number(re.sub(r'[()]', ' ', re.split(r'\u00b1|\+/-', c, maxsplit=1)[1]).strip()), parse_number(c)
    b = BRACKET_PM.search(c)
    if b and row and row.get('unit_for_conversion'):
        from units import unit_scale
        a, e, n = float(b.group(1)), float(b.group(2)), int(b.group(3))
        s1, rest1 = unit_scale(row['unit_for_conversion'])
        s0, rest0 = unit_scale(row.get('raw_unit') or rest1)  # no printed unit: the unit_for_conversion's own
        f1, f0 = normalize(row.get('metric', ''), '1', rest1)[0], normalize(row.get('metric', ''), '1', rest0)[0]
        if e > a and e * 10 ** n < a and s1 and s0 and f1 and f0 and abs(f1 / f0 - 1) < 1e-9 and abs(s1 / s0 * 10 ** n - 1) < 1e-9:
            read = a  # the unit_for_conversion undoes exactly the bracket's 10^n on the printed unit: the value is a
    return float(f'{abs(u) * value / read:.4g}') if u and read else None


def rel_uncertainty(raw):
    """Printed relative uncertainty of a cell ('12 ± 3' -> 0.25); 0 when none is printed."""
    from units import parse_number
    # the error's own E exponent goes with it, as units.parse_number drops it: '6.6E+02 ± 9.4E+01' is 94/660, not 9.4/660
    m = re.search(r'(?:\u00b1|\+/-)\s*(\d+(?:[.,]\d+)?(?:\s*[eE]\s*[-+]?\s*\d+)?)', clean(raw or ''))
    v = parse_number(raw or '')
    if not m or not v:
        return 0.0
    u = parse_number(m.group(1)) or 0.0
    mant = parse_number(re.split(r'\u00b1|\+/-', clean(raw))[0]) or v  # '(a ± u) x 10^n': compare u with the mantissa
    return min(abs(u / mant), 3.0) if mant else 0.0


def molar(r):
    """The row's value in the catalog's molar units, None for a mass-concentration Km or kcat/Km (mg/mL, mL mg^-1 s^-1):
    those are never compared with database values or mM numbers, nor exported in the mM columns."""
    return None if r.get('unit') in MASS_UNIT.values() else r.get('value')


def ratio_check(by):
    """(ok, text) for one measurement with printed kcat, Km and kcat/Km: they agree within 1.5x, widened by the
    printed uncertainties (a paper that prints Km 5000 ± 5000 cannot be held to 1.5x). A disagreement drops nothing
    (the user, 2026-10-10: kcat and Km printed and verified are kept, the printed kcat/Km is kept as printed); the
    export notes it on the kcat/Km value ("differs from kcat ÷ Km by N×"). Before that, 5x or more dropped all three
    as a unit or pairing error (`catlog.py recover ratio_non_closure` brought back what the new rule keeps)."""
    k, km, e = by['kcat'], by['Km'], by['kcat/Km']
    if (km.get('unit') in MASS_UNIT.values()) != (e.get('unit') in MASS_UNIT.values()):
        return True, 'not compared: Km and kcat/Km are printed over different kinds of concentration (mass and molar)'
    quotient, printed = k['value'] / km['value'], e['value']
    tol = min(4.0, 1.5 * (1 + sum(rel_uncertainty(r.get('raw_value')) for r in (k, km, e))))
    fold = max(printed / quotient, quotient / printed)
    return fold <= tol, f'printed kcat/Km {printed:.4g} vs kcat/Km {quotient:.4g} ({fold:.2f}x; allowed {tol:.2f}x)' + (
        '' if fold <= tol else ' -- outside tolerance, kept as printed')


def ratio_note(by):
    """The kcat/Km note when the printed kcat/Km disagrees with kcat ÷ Km, else ''."""
    ok, _ = ratio_check(by)
    if ok:
        return ''
    q = by['kcat']['value'] / by['Km']['value']
    fold = max(by['kcat/Km']['value'] / q, q / by['kcat/Km']['value'])
    return f'differs from kcat ÷ Km by {fold:.1f}×' if fold < 100 else f'differs from kcat ÷ Km by {fold:.3g}×'


def row_id(r):
    key = '|'.join(str(r.get(k, '')).strip().lower() for k in
                   ('pmid', 'organism', 'enzyme', 'variant', 'substrate', 'cosubstrate', 'metric', 'raw_value', 'pH',
                    'temperature_C', 'conditions', 'location'))
    if construct_of(r):  # two preparations printing the same cell are two rows (existing ids are unchanged)
        key += '|' + construct_of(r)
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def existing_ids():
    ids = set()
    if CATALOG.exists():
        for line in open(CATALOG):
            if line.strip():
                ids.add(json.loads(line)['row_id'])
    return ids


def stale(pmid, read_p, ver_p):
    """Why the work files cannot be trusted together, or ''. The paper text must be older than the reader's output,
    and the reader's output older than the verdicts (a re-read after a verification invalidates those verdicts)."""
    t = TEXTS / f'{pmid}.txt'
    if t.exists() and read_p.exists() and t.stat().st_mtime > read_p.stat().st_mtime + 1:
        return f'{t.name} changed after {read_p.name} was written: read again'
    if ver_p.exists() and read_p.exists() and read_p.stat().st_mtime > ver_p.stat().st_mtime + 1:
        return f'{read_p.name} changed after {ver_p.name} was written: verify again'
    return ''


def cmd_add(pmid):
    """Accept a paper's verified rows. Every reader file needs a fresh verifier file (zero-row reads too: the verifier
    confirms the paper really has no measured values); unverified 'missed' rows keep the paper open."""
    read_p, ver_p = WORK / f'{pmid}.read.json', WORK / f'{pmid}.verify.json'
    miss_r, miss_v = WORK / f'{pmid}.missed.read.json', WORK / f'{pmid}.missed.verify.json'
    try:
        if not read_p.exists() or not ver_p.exists():
            print(f'{pmid}: need {read_p.name} and {ver_p.name}; left as reading', file=sys.stderr)
            return
        for rp, vp in ((read_p, ver_p), (miss_r, miss_v)):
            why = stale(pmid, rp, vp)
            if why:
                print(f'{pmid}: {why}; left as reading', file=sys.stderr); log(pmid, 'stale', why)
                return
        if miss_r.exists() and json.loads(miss_r.read_text()).get('rows') and not miss_v.exists():
            print(f'{pmid}: {miss_r.name} has values nobody verified yet; left as reading', file=sys.stderr)
            log(pmid, 'missed_unverified', miss_r.name)
            return
        read = json.loads(read_p.read_text())
        pairs = [(read, json.loads(ver_p.read_text()))]
        if miss_r.exists() and miss_v.exists():
            pairs.append((json.loads(miss_r.read_text()), json.loads(miss_v.read_text())))
    except json.JSONDecodeError as e:
        print(f'{pmid}: unreadable work file ({e}); left as reading', file=sys.stderr)
        return
    text_sq = squash(paper_text(pmid))
    kept, rejected = [], []
    for (rd, vd), (rp, vp, by) in zip(pairs, ((read_p, ver_p, None), (miss_r, miss_v, pairs[0][1]))):
        k, r = judge(pmid, rd, vd, text_sq, row_stamp(pmid, rd, vd, rp, vp, by))  # missed rows: read by the verifier
        kept += k; rejected += r
    finish(pmid, read, kept, rejected, empty_reason=str(pairs[0][1].get('reason_if_empty') or ''))


def add_one(pmid):
    """`add` for one paper; an error is reported and the next paper still gets added."""
    try:
        cmd_add(pmid)
    except Exception as e:
        log(pmid, 'add_failed', f'{type(e).__name__}: {e}'[:200])
        print(f'{pmid}: add failed ({type(e).__name__}: {e}); left as reading', file=sys.stderr)


def cmd_add_all(pmids):
    """`add` for a round's papers. When 3 or more of them came back without a reader or verifier file, the agents ran out
    (the session usage limit, or the API down), not 3 bad papers: those papers go straight back to the queue (a finished
    read is kept, keep_read) without counting as deaths, so a usage limit never parks a paper. Works however the agents
    were started (the workflow, or the Agent tool when the workflow tool is off after an account switch)."""
    gone = [p for p in pmids if not (WORK / f'{p}.read.json').exists() or not (WORK / f'{p}.verify.json').exists()]
    for p in pmids:
        add_one(p)
    if len(gone) < 3:
        return
    with Queue(write=False) as q:
        back = [p for p in gone if q.rows.get(p, {}).get('status') == 'reading']
    for p in back:
        cmd_reread(p, 'agents stopped mid-round (session usage limit or API outage)', limit=True)
    if back:
        print(f'{len(back)} papers came back without agent output (most likely the session usage limit): they are back in '
              'the queue, finished reads kept, not counted as failures. Carry on once agents run again.')


# ---------- provenance: the model, prompts and code behind each row (reviewers ask; 2026-10-21) ----------

STAMP = ('read_by', 'reader_model', 'verifier_model', 'read_prompt', 'verify_prompt', 'task_prompt', 'pipeline_commit')
MISSED = 'verifier (missed values)'  # read_by of the values the verifier found the reader had skipped
# the agents' task text: the batch workflow writes each reader's and verifier's task (what to read, in slices, which
# file to write or leave alone); with args.lean the agent file is their system prompt (blind-reading rules)
TASK = ('.claude/workflows/catlog-batch.js', '.claude/agents/catlog-reader.md')
PIPELINE = ('catlog.py', 'prompts', 'tools/units.py', *TASK)  # what reads, judges and converts a row: '+dirty' if it differs from HEAD


def model_id(x):
    """The model id an agent wrote as `model` in its work file (prompts/read.md, verify.md), as written; '' when it wrote
    none (work files from before 2026-10-21, or a batch then mid-flight): the row still adds, its model stamp empty."""
    return ' '.join(x.split())[:100] if isinstance(x, str) else ''


_agent_logs, _agent_log_files = {}, []  # this run's parsed agent transcripts (by path under ~/.claude/projects), and
MODEL_HOURS = 6                          # this folder's ones with their mtimes; an agent's ends within hours of its write


def agent_model(path):
    """(models, agent id) of the agent that wrote a work file, from its transcript: 'A', or 'A>B' when it switched model
    mid-run (a fallback). The agent's own `model` keeps naming the first, so it hides the switch (112 of 599 agents of
    the batches of 2026-10-29..11-01; paper/planning/FIXES_FOR_MAIN_CHAT_20261031.md item 2). ('', '') when no
    transcript shows the write (logs moved to Nova, another machine, a chat opened in another folder): the caller then
    takes the agent's own `model`. Only the transcripts of chats opened in this folder or a worktree of it
    (~/.claude/projects/<this folder's path, '/' and '.' as '-'>*) that ended within MODEL_HOURS after the write are
    parsed; tools/provenance_backfill.py (scan, Writers) picks the one whose call was running at the file's mtime. That
    file is outside PIPELINE: an uncommitted edit there does not mark pipeline_commit '+dirty'."""
    try:
        import provenance_backfill as pb
        mtime = path.stat().st_mtime
        if not _agent_log_files:
            listed = []
            for p in pb.PROJECTS.glob(re.sub(r'[^A-Za-z0-9]', '-', str(ROOT)) + '*/*/subagents/**/*.jsonl'):
                try:
                    listed.append((p, p.stat().st_mtime))
                except OSError:  # removed meanwhile (an archive, Claude Code's 30-day cleanup)
                    pass
            _agent_log_files[:] = listed
        trans = {}
        for p, m in _agent_log_files:
            if mtime - pb.SLACK <= m <= mtime + MODEL_HOURS * 3600:
                rel = str(p.relative_to(pb.PROJECTS))
                if rel not in _agent_logs:
                    try:
                        _agent_logs[rel] = pb.scan(p)[0]
                    except Exception:  # an unreadable transcript names no file
                        _agent_logs[rel] = {'files': set()}
                if path.name in _agent_logs[rel]['files']:
                    trans[rel] = _agent_logs[rel]
        w = pb.Writers(trans)
        rel, i, _ = w.find(path.name, mtime)
        return (w.model(rel, i), Path(rel).stem) if rel else ('', '')
    except Exception:  # never stops an add: the agent's own `model` stands
        return '', ''


def git(*a, text=True):
    """git in this folder, read-only use: never takes git's index lock (a data checkpoint may be committing)."""
    return subprocess.run(['git', '--no-optional-locks', '-C', str(ROOT), *a], capture_output=True, text=text, timeout=30,
                          env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})


def git_commit():
    """This folder's git HEAD (12 hex), '+dirty' when a file in PIPELINE differs from it; '' when the folder is not its
    own repository (a test root) or git cannot tell."""
    try:
        top, head = git('rev-parse', '--show-toplevel'), git('rev-parse', '--short=12', 'HEAD')
        if top.returncode or head.returncode or Path(top.stdout.strip()).resolve() != Path(ROOT).resolve():
            return ''
        dirty = git('status', '--porcelain', '--untracked-files=no', '--', *PIPELINE)
        return '' if dirty.returncode else head.stdout.strip() + ('+dirty' if dirty.stdout.strip() else '')
    except (OSError, subprocess.SubprocessError):
        return ''


def prompt_hash(name, written=None):
    """sha256[:12] of prompts/<name> as it is now; '' when it is missing or was changed after `written` (the agent's
    work file): a prompt fix that landed after the agent wrote its file is not the prompt it followed."""
    p = ROOT / 'prompts' / name
    if not p.is_file() or (written is not None and written.exists() and p.stat().st_mtime > written.stat().st_mtime + 1):
        return ''
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def task_text():
    """The task files (TASK) as one text, each under its path: task_prompt hashes exactly this (cmd_prompt rebuilds it)."""
    return b''.join(f'=== {f} ===\n'.encode() + (ROOT / f).read_bytes() for f in TASK if (ROOT / f).is_file())


def task_hash():
    t = task_text()
    return hashlib.sha256(t).hexdigest()[:12] if t else ''


def claim_prompts(pmid, kept=False):
    """At claim (`next`): work/<PMID>.prompts.json records each prompt's hash as the paper's agents will load it, so
    `add` can tell a prompt that changed while they worked (an agent loads its prompt when it starts and writes its file
    minutes later: a median 7.6 min from claim to read, 2.3 more to the verdicts). A kept read (keep_read: only the
    verifier runs) keeps the record of its own claim for the reader; none (claimed before 2026-10-21) means unknown."""
    p, old = WORK / f'{pmid}.prompts.json', {}
    if kept:
        try:
            old = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    old = old if isinstance(old, dict) else {}
    task = task_hash()  # a kept read's reader and its verifier had the same task text only if it did not change since
    rec = {'claimed': now(), 'read.md': old.get('read.md') if kept else prompt_hash('read.md'),
           'verify.md': prompt_hash('verify.md'), 'task': (task if old.get('task') == task else None) if kept else task,
           **({'censored_only': True} if kept and old.get('censored_only') else {})}
    p.write_text(json.dumps(rec) + '\n')


def claimed(pmid):
    """The claim-time prompt hashes (claim_prompts); {} for a paper claimed before they were recorded."""
    try:
        d = json.loads((WORK / f'{pmid}.prompts.json').read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return d if isinstance(d, dict) else {}


def prompt_stamp(name, written, followed, at_claim=None):
    """The hash of prompts/<name> that the agent writing `written` followed, or '' when that cannot be known: a blank,
    never a wrong hash. Blank when the prompt changed after the file was written; when the file has no `model` key
    (`followed` False: every prompt since 2026-10-21 asks for it, even as "", so its agent loaded an older prompt, e.g.
    one mid-flight at the merge of this change); or when the prompt is not the one hashed when the paper was claimed
    (an edit while its agents worked). at_claim None: claimed before claim records (claim_prompts) existed."""
    h = prompt_hash(name, written)
    return keep_prompt(h, lambda: (ROOT / 'prompts' / name).read_bytes()) if h and followed and at_claim in (None, h) else ''


def keep_prompt(h, text):
    """h, once work/prompts/<h>.md holds the text it hashes (written the first time; work/ is evidence, never cleaned),
    so every hash in the catalog resolves to its exact text, also a prompt edit never committed (`catlog.py prompt
    HASH`). `text()` gives the bytes now; '' when they no longer hash to h (edited this instant) or cannot be read."""
    try:
        data = text()
    except OSError:
        return ''
    if not data or hashlib.sha256(data).hexdigest()[:12] != h:
        return ''
    p = WORK / 'prompts' / f'{h}.md'
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(f'.{h}.{os.getpid()}.tmp')
        tmp.write_bytes(data)
        os.replace(tmp, p)
    return h


def cmd_prompt(h):
    """Print the text a row's read_prompt, verify_prompt or task_prompt names: work/prompts/<hash>.md (saved when a row
    was stamped) or sources/prompt_versions/<hash>.md (saved by tools/provenance_backfill.py), else the prompt or task
    files at a commit in this folder's history (or now) that hash to it."""
    h = h.strip().lower()
    if not re.fullmatch(r'[0-9a-f]{12}', h):
        sys.exit("usage: catlog.py prompt HASH   (the 12 hex characters of a row's read_prompt, verify_prompt or task_prompt)")
    for saved in (WORK / 'prompts' / f'{h}.md', ROOT / 'sources' / 'prompt_versions' / f'{h}.md',  # the latter: backfill
                  ROOT / 'prompts' / 'versions' / f'{h}.md'):  # this copy: the authors' saved texts (README)
        if saved.exists():
            print(f'{h}: {saved.relative_to(ROOT)}', file=sys.stderr)
            sys.stdout.write(saved.read_text(errors='replace'))
            return

    def at(commit, f):  # a file's bytes at a commit ('' = as it is now), None if it was not there
        if not commit:
            return (ROOT / f).read_bytes() if (ROOT / f).is_file() else None
        r = git('show', f'{commit}:{f}', text=False)
        return r.stdout if r.returncode == 0 else None
    files = ['prompts/read.md', 'prompts/verify.md']
    log_ = git('log', '--format=%H', '--', *files, *TASK)
    for commit in [''] + (log_.stdout.split() if log_.returncode == 0 else []):
        parts = {f: at(commit, f) for f in files + list(TASK)}
        task = b''.join(f'=== {f} ===\n'.encode() + parts[f] for f in TASK if parts[f] is not None)
        for name, data in [(f, parts[f]) for f in files] + [('task files (' + ' + '.join(TASK) + ')', task)]:
            if data and hashlib.sha256(data).hexdigest()[:12] == h:
                print(f"{h}: {name} {'as it is now' if not commit else 'at commit ' + commit[:12]}", file=sys.stderr)
                sys.stdout.write(data.decode('utf-8', 'replace'))
                return
    sys.exit(f'{h}: no saved text (work/prompts/, sources/prompt_versions/) and no prompt or task-file version in this '
             'folder\'s git history hashes to it')


def row_stamp(pmid, read, ver, read_p=None, ver_p=None, missed_by=None):
    """Who read and who checked one pair of work files, the prompts they followed, and the code at add time.
    missed_by: the paper's verify file, when this pair holds the values that verifier found the reader had skipped:
    read_by says so, its read_prompt is a hash of verify.md (the prompt that verifier followed), and its model and
    prompt version come from either of that agent's two files (it may write `model` in only one)."""
    at, by = claimed(pmid), missed_by if isinstance(missed_by, dict) else {}
    rp = 'verify.md' if missed_by is not None else 'read.md'
    # the models from the agents' transcripts (agent_model: a mid-run switch shows), else what each agent wrote; the
    # log line says which, and which agent's log (its id) it came from
    (rm, ra), (vm, va) = (agent_model(p) if p else ('', '') for p in (read_p, ver_p))
    if read_p or ver_p:
        log(pmid, 'agent_models', *(f'{p.name}={m}@{a}' if m else f'{p.name}=own:{own}'
                                    for p, m, a, own in ((read_p, rm, ra, model_id(read.get('model')) or model_id(by.get('model'))),
                                                         (ver_p, vm, va, model_id(ver.get('model')))) if p))
    return {'read_by': MISSED if missed_by is not None else 'reader',
            'reader_model': rm or model_id(read.get('model')) or model_id(by.get('model')),
            'verifier_model': vm or model_id(ver.get('model')),
            'read_prompt': prompt_stamp(rp, read_p, 'model' in read or 'model' in by, at.get(rp)),
            'verify_prompt': prompt_stamp('verify.md', ver_p, 'model' in ver, at.get('verify.md')),
            # the task text the workflow gave both agents: only when it is the text hashed at claim (the workflow loads
            # it after `next`), so blank for papers claimed before claim records existed or when it changed meanwhile
            'task_prompt': keep_prompt(task, task_text) if (task := task_hash()) and at.get('task') == task else '',
            'pipeline_commit': git_commit()}


RECONSTRUCTED = 'reconstructed'  # `how` of a stamp tools/provenance_backfill.py rebuilt for a row added before stamping
_backfill = {}


def backfill_stamps():
    """row_id -> the STAMP values tools/provenance_backfill.py reconstructed (sources/provenance_backfill.tsv) for rows
    added before stamping, from the agents' transcripts, the work files and git (task_prompt is not reconstructed: "");
    {} without the file. Read once per file version."""
    p = ROOT / 'sources' / 'provenance_backfill.tsv'
    try:
        st = p.stat()
    except OSError:
        return {}
    key = (str(p), st.st_mtime_ns, st.st_size)
    if _backfill.get('key') != key:
        rows = {}
        with open(p, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                if r.get('row_id') and r.get('how') == RECONSTRUCTED:
                    rows[r['row_id']] = tuple(sys.intern(r.get(k) or '') for k in STAMP)
        _backfill.update(key=key, rows=rows)
    return _backfill['rows']


def provenance(m):
    """The export's per-value stamps ({metric: stamp}): the row's own, written by `add` (since 2026-10-21), else for a row
    added before stamping the stamp tools/provenance_backfill.py reconstructed from evidence, marked how 'reconstructed'
    (never over a row's own stamp); None when no value has either."""
    bf = backfill_stamps()
    out = {}
    for k, r in m.items():
        if any(f in r for f in STAMP):
            out[k] = {f: r.get(f, '') for f in STAMP}
        elif r.get('row_id') in bf:
            out[k] = {**dict(zip(STAMP, bf[r['row_id']])), 'how': RECONSTRUCTED}
    return out or None


def flat_provenance(w):
    """One CSV cell per stamp: the distinct values of the measurement's rows, in metric order ('' for unstamped rows),
    and provenance_how: 'stamped' (by add), 'reconstructed' (tools/provenance_backfill.py) or both."""
    p = (w.get('provenance') or {}).values()
    return {**{f: '; '.join(dict.fromkeys(x[f] for x in p if x.get(f))) for f in STAMP},
            'provenance_how': '; '.join(dict.fromkeys(x.get('how', 'stamped') for x in p))}


def judge(pmid, read, ver, text_sq, stamp=None):
    verdicts = {int(v['i']): v for v in ver.get('verdicts', []) if str(v.get('i', '')).strip().isdigit()}  # "i": "0" counts too
    # who read and who checked these rows, with which prompts and code (row_stamp): set last, so no row or fix field
    # can overwrite it
    stamp = stamp if stamp is not None else row_stamp(pmid, read, ver)
    meta = {k: read.get(k, '') for k in ('doi', 'title')}
    if not all(meta.values()):  # the reader left them out: the queue knows them (a reviewer missed a DOI this way)
        with Queue(write=False) as q:
            known = q.rows.get(pmid, {})
        meta = {k: meta[k] or known.get(k, '') for k in meta}
    kept, rejected = [], []
    for i, row in enumerate(read.get('rows', [])):
        v = verdicts.get(i, {'verdict': 'missing', 'reason': 'verifier gave no verdict'})
        # a verdict names the row it judged: a verdict for a different row (reordered or edited reader output) is void
        cens_row = bool(censored_kind(row))  # an 'ND' carries no number: its echo must name the cell and, if given, the variant
        if ('metric' in v and v['metric'] != row.get('metric')) or \
           ('raw_value' in v and (numbers(v['raw_value'])[:1] != numbers(row.get('raw_value', ''))[:1])) or \
           (cens_row and 'raw_value' in v and squash(v['raw_value']) != squash(row.get('raw_value', ''))) or \
           (cens_row and v.get('variant') and squash(v['variant']) != squash(row.get('variant', ''))):
            v = {'verdict': 'stale', 'reason': f"verdict {i} was for {v.get('metric')} {v.get('raw_value')}, not this row"}
        corrected = {}
        if v['verdict'] == 'fix':  # keep what the reader had: the trail of what the second reader changed
            corrected = {k: {'reader': row.get(k, ''), 'verifier': x} for k, x in (v.get('fix') or {}).items() if row.get(k, '') != x}
            row = {**row, **v.get('fix', {})}
        row = {'pmid': pmid, **meta, **row}
        norm, bad = check(row, text_sq)
        # A scanned paper's OCR text is not evidence: it drops and misreads digits (PMID 4622304, 1972 scan, 4 values).
        # When the verifier confirmed the cell on the rendered page image, an unfindable quote is a flag, not a reject.
        # The same OCR text also garbles the digits inside the quote ('3.6 x 10^7' prints as '3 . 6 107', PMID 8055963),
        # so value_not_in_quote is the same artefact. The verdict already had to echo this row's raw_value.
        if set(bad) <= {'quote_not_in_paper', 'value_not_in_quote', 'marker_not_in_quote'} and bad and v['verdict'] in ('confirm', 'fix') \
                and v.get('on_page_image') is True:
            row['quote_check'] = f"{' and '.join(bad)}: the verifier read this cell on the page image (the text layer is a scan)"
            bad = []
        if v['verdict'] not in ('confirm', 'fix'):
            bad.insert(0, f"verifier_{v['verdict']}: {v.get('reason', '')}")
        row.update(norm)
        row['row_id'] = row_id(row)
        row['checked'] = now()
        row.update(stamp)
        if bad:
            rejected.append({**row, 'why': bad})
        else:
            row['verify_note'] = v.get('reason', '')
            if corrected:
                row['corrected'] = corrected
            kept.append(row)
    return kept, rejected


def slot(r):
    """One measurement-metric: the same paper, identity, assay, location, metric and per-value note. A catalog holds at
    most one current value per slot."""
    shared = sorted(x.lower() for x in condition_parts(r.get('conditions'))[0])
    key = [str(r.get(k, '')).strip().lower() for k in IDENT] + [r.get('metric', ''), (r.get('metric_note') or '').strip().lower()] + shared
    key += [construct_of(r)] if construct_of(r) else []  # keeps the slots of rows without a construct unchanged
    key += ['gene:' + gene_of(r)] if gene_of(r) else []
    blanked = re.findall(r'\b(pH|temperature_C) ([\d.]+) is not printed', r.get('condition_note') or '')
    key += [f'{k}~{v}' for k, v in sorted(blanked)]  # rows without such a note keep their slot
    return hashlib.sha1('|'.join(key).encode()).hexdigest()[:16]


def audit_dropped():
    """Rows an audit refuted. A re-read must not bring them back silently, under the same or new wording."""
    out = []
    if REJECTED.exists():
        for line in open(REJECTED):
            r = json.loads(line)
            if any(str(w).startswith('audit:') for w in r.get('why', [])):
                out.append(r)
    return out


LABEL_DROPS = ROOT / 'sources' / 'organism_label_drops.tsv'  # drops of right values whose organism label was wrong
NO_ORGANISM = {'', 'not stated', 'not given', 'not specified', 'not reported', 'unspecified', 'unknown', 'none', 'n/a',
               'na', 'n.d.', 'nd', '-'}


def label_drops(strict=False):
    """(row_id, dropped) -> line of sources/organism_label_drops.tsv: drops of values right as printed whose organism
    label was wrong. Columns: row_id; pmid; dropped, the stamp of that one drop in rejected.jsonl (a later drop of the
    same row_id is not listed); organism, the dropped label; organism_now and strain_now, the corrected label ('' where
    the paper names none); why. Written by hand after a check against the paper and after the drop, as
    sources/natural_forms.tsv ('#' lines are comments). An audit's free-text reason never decides this. An unreadable
    list keeps every listed value out of `add` and stops no add; strict (restore, unitfix) stops the command."""
    if not LABEL_DROPS.exists():
        return {}
    try:
        with open(LABEL_DROPS, encoding='utf-8-sig') as fh:
            lines = [l for l in fh if l.strip() and not l.startswith('#')]
    except (OSError, UnicodeDecodeError) as e:
        if strict:
            sys.exit(f'{LABEL_DROPS.name}: not read ({e}); fix it first (a listed drop must not come back under its old label)')
        print(f'{LABEL_DROPS.name}: not read ({e}); its values stay dropped', file=sys.stderr)
        return {}
    out = {}
    for r in csv.DictReader(lines, delimiter='\t', quoting=csv.QUOTE_NONE):
        rid, when = (r.get('row_id') or '').strip(), (r.get('dropped') or '').strip()
        if rid and when:
            out[(rid, when)] = r
    if len(lines) > 1 and not out:
        if strict:
            sys.exit(f'{LABEL_DROPS.name}: no line with a row_id and a dropped stamp (check its header); fix it first')
        print(f'{LABEL_DROPS.name}: no line with a row_id and a dropped stamp (check its header)', file=sys.stderr)
    return out


def organism_label(x):
    """An organism or strain text as compared: lower case, one space; a placeholder for none ('not stated') is ''."""
    t = ' '.join(str(x or '').lower().split())
    return '' if t in NO_ORGANISM else t


def organism_relabelled(r, o, listed):
    """True when `o`, one drop listed in sources/organism_label_drops.tsv (`listed`: label_drops()), does not keep the
    re-read row `r` of the same printed cell out: `r` gives exactly the corrected label the list states (organism_now,
    strain_now: '' where the paper names none, as 18620421 on 2026-11-15, whose 'Pseudomonas sp.' strain CBS3 is the CBL
    of its ref 20), its enzyme, gene and construct do not carry the old label on, and it converts the cell to the same
    value. Carried on: a letter word of the old organism or strain as a word of its own, or plural ('rats'; 'homodimer'
    is not 'Homo'), or a word with a digit, or the whole strain, anywhere once separators are gone ('CBS-3' and
    'Synpcc7942_1593' carry CBS3 and PCC 7942). Anything else keeps the value out, for a decision by hand: code cannot
    tell a synonym or an abbreviation from another species, a value converted otherwise is a conflict to review, and
    restore and unitfix refuse a listed drop, so such a value comes back only through a read giving the listed label."""
    line = listed.get((o.get('row_id'), o.get('dropped')))
    if not line:
        return False
    if (organism_label(r.get('organism')), organism_label(r.get('strain'))) != \
            (organism_label(line.get('organism_now')), organism_label(line.get('strain_now'))):
        return False
    alnum = lambda x: re.sub(r'[^a-z0-9]', '', str(x or '').lower())
    words = lambda *xs: {alnum(w) for x in xs for w in str(x or '').split()} - {'sp', 'spp', 'strain', 'str', 'subsp', 'var'}
    new = words(line.get('organism_now'), line.get('strain_now')) | {alnum(line.get('strain_now'))}
    old = {w for w in words(o.get('organism'), o.get('strain')) | {alnum(o.get('strain'))} if len(w) >= 3} - new
    text = ' '.join(str(r.get(k) or '') for k in ('enzyme', 'gene', 'construct')).lower()
    toks, joined = set(re.findall(r'[a-z0-9]+', text)), alnum(text)
    if any((w in joined) if re.search(r'\d', w) else ({w, w + 's', w + 'es'} & toks) for w in old):
        return False
    return o.get('unit') == r.get('unit') and bool(o.get('value')) and bool(r.get('value')) and close(o['value'], r['value'])


from contextlib import contextmanager


@contextmanager
def catalog_lock():
    """One writer at a time for catalog.jsonl and rejected.jsonl. The lock is a side file: `drop` replaces
    catalog.jsonl, so a lock on the catalog file itself would be lost by whoever opened the old copy."""
    with open(ROOT / 'catalog.jsonl.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for f in (CATALOG, REJECTED, BOUNDS):  # a write killed half-way leaves a cut-off last line: drop that fragment
            if f.exists() and f.stat().st_size:
                data = f.read_bytes()
                if not data.endswith(b'\n'):
                    f.write_bytes(data[:data.rfind(b'\n') + 1])
                    log('-', 'repaired', f.name, 'cut-off last line removed')
        if CATALOG.exists() and len(ids := re.findall(rb'"row_id": "(\w+)"', CATALOG.read_bytes())) != len(set(ids)):
            unique_row_ids()
        yield


def unique_id(r, taken):
    """row_id leaves out metric_note and gene, so two values with the same printed cell in one table row (kcat/Km1 and
    kcat/Km2 both 8.4 x 10^1, PMID 30893549) would share an id: the later one gets its slot folded in."""
    rid = r['row_id']
    return hashlib.sha1(f'{rid}|{slot(r)}'.encode()).hexdigest()[:16] if rid in taken else rid


def unique_row_ids():
    """Rows added before unique_id() existed: the first keeps its id, a later row of another slot gets a new one."""
    rows, taken = [json.loads(l) for l in open(CATALOG) if l.strip()], set()
    for r in rows:
        new = unique_id(r, taken)
        if new != r['row_id']:
            log(r['pmid'], 'repaired', 'row_id', f"{r['row_id']} -> {new} (shared with another value)")
            r['row_id'] = new
        taken.add(new)
    tmp = CATALOG.with_suffix('.jsonl.tmp')
    with open(tmp, 'w') as out:
        for r in rows:
            out.write(json.dumps(r, ensure_ascii=False) + '\n')
    os.replace(tmp, CATALOG)


def printed_cell(r):
    """What the paper printed, whatever words a reader used around it: paper, metric and cell. Not the unit as the
    reader typed it ('s^-1' / 's-1', 1831974: 290 re-read copies on 2026-10-22): callers compare the converted unit and
    value, so the same cell read in another unit is a conflict, not a new value."""
    return (r.get('pmid'), r.get('metric'), squash(r.get('raw_value', '')).replace(' ', ''))


LOCATOR = re.compile(r'\[[^\]]*\]|\b(?:pp?|pages?|table|tab|fig|figure|scheme|panel)\b\.?\s*s?(?:\d+|[ivx]+\b)[a-z]?'
                     r'|(?<=[A-Za-zµμ)])\s*\^?\s*[-−–]\s*[123]\b', re.I)


def quote_numbers(s):
    """The printed numbers of a quote in order, without the reader's locator and labels ('[page image p.5] Table 1',
    'Fig. 3B', '[table image elife03275t002.jpg]', a unit '[s-1]' or 'M-1 s-1' one reader put between the cells,
    24980702) and with an exponent's sign kept ('10^-5' is not '10^5', 10749856)."""
    s = LOCATOR.sub(' ', clean(s or '')).replace(',', '')
    return [x.replace('^', '').replace('−', '-').replace('–', '-')
            for x in re.findall(r'(?<![\d.])10\^?[-−–]\d+|\d+(?:\.\d+)?', s)]


def same_quote(a, b):
    """Two quotes of one printed cell: one holds the other (spacing aside), or the shorter quote's printed numbers (3 or
    more) all appear, in the same order and in one run, in the other, the cell among them. Readers word their own
    locator differently ('[page image p.5] Table 1, D-Xylose, ...' / '... D-xylose block, ...', 1831974) and space a ±
    differently ('60±0.4' / '60 ± 0.4', 3264155); a row of another table sharing the cell and a few small numbers is not
    the same quote (25514023: 'WT | 275.32±12 | 3.397±0.7 | 0.21±0.3' / 'GlcNAcb | 275.30±12 | 0.057±0.7 | 0.21±0.3'),
    nor a quote that is only a locator and the cell ('[page image p.4] Table 2 | E. coli | 0.5')."""
    flat = lambda r: re.sub(r'\s+', '', squash(r.get('quote', '')).replace('↓', ''))
    qa, qb = flat(a), flat(b)
    if not qa or not qb:
        return False
    if qa in qb or qb in qa:
        return True
    na, nb, cell = quote_numbers(a.get('quote')), quote_numbers(b.get('quote')), quote_numbers(a.get('raw_value'))[:1]
    best, end, prev = 0, 0, [0] * (len(nb) + 1)  # longest run of equal numbers in both quotes
    for i, x in enumerate(na):
        cur = [0] * (len(nb) + 1)
        for j, y in enumerate(nb):
            if x == y:
                cur[j + 1] = prev[j] + 1
                if cur[j + 1] > best:
                    best, end = cur[j + 1], i + 1
        prev = cur
    return bool(cell) and best >= 3 and best == min(len(na), len(nb)) and cell[0] in na[end - best:end]


def mutation_set(v):
    """A variant written only as point mutations ("D13E/M26I/R301K"): the set of them, else None."""
    parts = [p for p in re.split(r'[/,+\s]+', (v or '').strip()) if p]
    return frozenset(parts) if len(parts) > 1 and all(re.fullmatch(r'[A-Z]\d+[A-Z*]', p) for p in parts) else None


def relabelled(va, vb):
    """The same variant words outside brackets, and each bracketed label of one inside a label of the other: a reader's
    own label moved or lengthened (41255148: "HisH W123AzoF (hAzoF); HisF wild type" = "HisH W123AzoF; HisF wild type
    (hAzoF_HisF)"). A label naming another form keeps them apart ("AKR1C21* (DD1)" / "AKR1C21 (DD3)", 15577209)."""
    alnum = lambda s: re.sub(r'[^a-z0-9]', '', s)
    la, lb = ([x for x in map(alnum, re.findall(r'\(([^()]*)\)', v)) if x] for v in (va, vb))
    inside = lambda xs, ys: all(any(x in y or y in x for y in ys) for x in xs)
    return bool(la and lb) and alnum(re.sub(r'\([^()]*\)', '', va)) == alnum(re.sub(r'\([^()]*\)', '', vb)) \
        and inside(la, lb) and inside(lb, la)


def same_variant(a, b):
    """The same variant text, or a natural form (sources/natural_forms.tsv) one read wrote in `variant` and the other,
    as the read prompt says since 2026-10-10, in `enzyme` with variant wild type. Also the same point mutations listed
    in another order (22564138: R301K last) and a relabelled variant (relabelled); the 2026-10-18 scan of the whole
    catalog found these two only as re-read copies of one cell, never between two values of one read."""
    va, vb = squash(a.get('variant', '')), squash(b.get('variant', ''))
    if va == vb or relabelled(va, vb):
        return True
    if mutation_set(a.get('variant')) and mutation_set(a.get('variant')) == mutation_set(b.get('variant')):
        return True
    return any((natural_form(x) or {}).get('_by') == 'variant' and vy in ('wild type', 'wildtype', 'wt', '') and vx in squash(y.get('enzyme', ''))
               for x, y, vx, vy in ((a, b, va, vb), (b, a, vb, va)))


SUBSCRIPT = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')
POINT_MUTATION = re.compile(r'[A-Z]\d+[A-Z*]')


def spelled_out(short, long):
    """One read names the variant by the paper's label, the other spells out its point mutations with that label in
    brackets ('PpDyP^PR' = 'L7I/.../P283A (PpDyP^PR)', 40933351; 'M309V' = 'C291Y/W295R/M309V (M309V)', 34306835).
    Only that shape: the short form has no brackets, the long one is 2+ point mutations and one label, the label is not
    wild type, and a short form that is itself mutations has them all in the long one. A bracket naming a background
    ('I10C (Cys-free C78A/...)', 17689871) or a deletion ('E3A/Δ(19–30)', 10969089) is another variant."""
    if '(' in short or not short.strip():
        return False
    m = re.fullmatch(r'\s*(.*?)\s*\(([^()]*)\)\s*', long or '')
    if not m:
        return False
    outside, label = m.groups()
    muts = [p for p in re.split(r'[/,+\s]+', outside) if p]
    if len(muts) < 2 or not all(POINT_MUTATION.fullmatch(p) for p in muts):
        return False
    alnum = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
    own = [p for p in re.split(r'[/,+\s]+', short) if p]
    if own and all(POINT_MUTATION.fullmatch(p) for p in own) and set(own) == set(muts):
        return True  # the same mutations, one read adding the paper's label ('A144Q/D207A/S209A (ADS)', 14718657)
    if alnum(short) != alnum(label) or alnum(short) in ('wt', 'wildtype'):
        return False
    return not all(POINT_MUTATION.fullmatch(p) for p in own) or set(own) <= set(muts)


def twin(r, cells, claimed=()):
    """An accepted row of an earlier read with the same printed cell and an overlapping quote: a re-read that worded
    the enzyme, location or conditions differently describes the same value, not a new one. `claimed`: rows an earlier
    row of the same add already matched (5724562: three enzymes print Km 0.59 in one table; each re-read row pairs
    with its own enzyme's row, not all three with the first)."""
    unmark = lambda s: squash(s).replace('↓', '')  # a peptide's printed cleavage mark (20635860: RKRSRR↓QVNT = RKRSRRQVNT)
    spelt = lambda s: re.sub('[αβγδεκλω]', lambda m: GREEK.split('|')['αβγδεκλω'.index(m.group())], unmark(s))  # 'α-D-xylulose' = 'alpha-D-xylulose (...)'
    sub_ = spelt(r.get('substrate', ''))
    cands = [o for o in cells.get(printed_cell(r), []) if same_quote(r, o)]
    # without separators only ('H_2O_2' = 'H2O2', 40933351; '[2H]benzylamine' = '[2H]-benzylamine', 21819071), and equal,
    # never a part ('NADP+' is not 'NADPH'): a sign, prime, comma or colon names another compound ('(+)-'/'(−)-borneol')
    sep = lambda s: re.sub(r'[\s_\-\u2010\u2011\[\]{}^]', '', s.translate(SUBSCRIPT))  # hyphens, not the minus sign
    same_sub = lambda o: sub_ in spelt(o.get('substrate', '')) or spelt(o.get('substrate', '')) in sub_ \
        or bool(sep(sub_)) and sep(sub_) == sep(spelt(o.get('substrate', '')))
    same_cond = lambda o: all(not (isnum(o.get(k)) and isnum(r.get(k))) or float(o[k]) == float(r[k]) for k in ('pH', 'temperature_C'))
    named = lambda o: spelled_out(o.get('variant', ''), r.get('variant', '')) or spelled_out(r.get('variant', ''), o.get('variant', ''))
    # another variant, substrate, pH or temperature with the same printed cell is a new value (same number, different measurement)
    hits = [o for o in cands if o['row_id'] not in claimed and (same_variant(o, r) or named(o)) and same_sub(o) and same_cond(o)]
    same_value = lambda o: o.get('unit') == r.get('unit') and o.get('value') and r.get('value') and close(o['value'], r['value'])
    rank = lambda o: (not same_value(o), squash(o.get('enzyme', '')) != squash(r.get('enzyme', '')))
    return min(hits, key=rank) if hits else None  # a twin that converts alike first, then the same enzyme


def finish(pmid, read, kept, rejected, empty_reason=''):
    """Append the paper's rows (append_rows), then set its status."""
    new, dup, nb = append_rows(pmid, kept, rejected)
    status = 'wrong_paper' if str(read.get('note', '')).startswith('wrong_paper') else 'done'
    note = str(read.get('note') or '')[:200].replace('\t', ' ').replace('\n', ' ')
    only = claimed(pmid).get('censored_only')  # a pass for censored values only (`catlog.py censored`): the values stand
    if only and status == 'done':
        note = f'censored values pass: {len(nb)} new'
    elif status == 'done' and read.get('needs_supplement'):  # also when a supplement already came but lacked the table
        have = ' (one supplement already on file)' if (TEXTS / f'{pmid}.supp.txt').exists() else ''
        status, note = 'needs_supplement', f"lane=supplement; {read['needs_supplement']}{have}"[:200]
    elif status == 'done' and not kept and not rejected and empty_reason:
        status, note = 'incomplete', f'no values read; verifier: {empty_reason}'[:200]  # a preview is not "no kinetics"
    arrived = WORK / f'{pmid}.supp_arrived'
    if arrived.exists():  # a supplement was filed while this paper was being read: read it again with it
        (WORK / 'old').mkdir(exist_ok=True)
        shutil.move(str(arrived), str(WORK / 'old' / f'{pmid}.supp_arrived.{time.time_ns()}'))
        if status in ('done', 'needs_supplement'):
            status, note = 'todo', 'supplement arrived during the read; read again'
    with Queue() as q:
        q.set(pmid, status=status, **({} if only else {'kept': len(new), 'rejected': len(rejected)}), note=note)
    log(pmid, 'add', f'kept={len(new)}', f'dup={dup}', f'rejected={len(rejected)}', f'status={status}',
        *([f'bounds={len(nb)}'] if nb or only else []), *(['pass=censored'] if only else []))
    print(f'{pmid}: kept {len(new)} (dup {dup}), rejected {len(rejected)}' + (f', censored {len(nb)}' if nb or only else ''))


def append_rows(pmid, kept, rejected):
    """Append new rows. A row whose slot already holds the same value is a duplicate; a different value is a
    conflict (rejected, logged, never a second version); a slot an audit dropped stays dropped, reworded too, except
    a value listed as dropped for its organism label alone, which a re-read brings back under the corrected label
    (organism_relabelled; log.tsv `relabelled`). A re-read's rewording of an accepted value (same printed cell,
    overlapping quote) is a duplicate too. Censored values go to bounds.jsonl
    (append_bounds) under the same lock. Returns (new rows, duplicates, new censored values)."""
    bounds = [r for r in kept if censored_kind(r)]
    kept = [r for r in kept if not censored_kind(r)]
    gone = [r for r in audit_dropped() if not censored_kind(r)]
    dropped = {slot(r): r['row_id'] for r in gone}
    dropped_cells = {}
    for r in gone:
        if r.get('pmid') == pmid:
            dropped_cells.setdefault(printed_cell(r), []).append(r)
    # drops listed for their organism label alone (organism_relabelled): a key two drops share (two drops of one row in
    # one minute) is not listed, and a listed drop whose value came back (log `relabelled`, with the drop's stamp) is used
    listed, returned = label_drops() if dropped_cells else {}, {}
    if listed:
        from collections import Counter
        mine = [o for os in dropped_cells.values() for o in os]
        twice = Counter((o['row_id'], o.get('dropped')) for o in mine)
        listed = {k: v for k, v in listed.items() if twice[k] == 1}
        if listed and LOG.exists():
            with open(LOG) as fh:
                returned = {(f[3], f[6]): f[4] for f in (l.rstrip('\n').split('\t') for l in fh
                                                         if f'\t{pmid}\trelabelled\t' in l) if len(f) >= 7}
    relabels = []  # logged once the rows are written, so a cut add leaves no line naming a row that is not there

    def decides(r, o, pc):
        """(drop, how) for re-read row r and dropped row o that it pairs with: 'back' (a listed drop whose value is in
        the catalog again), 'free' (a listed drop r may bring back: organism_relabelled, and the same enzyme, since
        twin() pairs any enzyme of one printed line) or 'hard' (r stays out). A listed drop whose returned row was
        dropped again is followed to that later drop (a second label correction); gone for any other reason, 'hard'."""
        seen = set()
        while (key := (o['row_id'], o.get('dropped'))) in returned and key not in seen:
            seen.add(key)
            n = returned[key]
            if any(c['row_id'] == n for c in current.values()):
                return o, 'back'
            later = [x for x in dropped_cells.get(pc, []) if x['row_id'] == n and (x['row_id'], x.get('dropped')) not in seen]
            if not later:
                return o, 'hard'
            o = max(later, key=lambda x: x.get('dropped') or '')
        if (o['row_id'], o.get('dropped')) in listed and organism_relabelled(r, o, listed) and \
                (same_enzyme(o.get('enzyme'), r.get('enzyme')) or enzyme_core(o) == enzyme_core(r)):
            return o, 'free'
        return o, 'hard'
    with catalog_lock(), open(CATALOG, 'a+') as cat:
        cat.seek(0)
        text = cat.read()
        taken = set(re.findall(r'"row_id": "(\w+)"', text))  # every id, without parsing 60k+ rows
        current, cells = {}, {}
        for line in text.splitlines():
            if pmid not in line or not line.strip():
                continue
            r = json.loads(line)
            if r.get('pmid') != pmid:  # slot keys start with the pmid: other papers' rows can never collide
                continue
            current[slot(r)] = r
            cells.setdefault(printed_cell(r), []).append(r)
            for misread, _, _ in cell_fixes(r):  # a reading cellfix corrected: a re-read that misreads it again conflicts
                cells.setdefault((r.get('pmid'), r.get('metric'), squash(misread).replace(' ', '')), []).append(r)
        held = bound_rows(pmid)  # this paper's censored values, by slot
        taken |= {r['row_id'] for r in held.values()} | bound_ids()
        new, dup = [], 0
        claimed = {current[slot(r)]['row_id'] for r in kept if slot(r) in current}  # each accepted row pairs once
        for r in kept:
            k = slot(r)
            old = twin(r, cells, claimed) if k not in current else None
            if old:
                claimed.add(old['row_id'])
                if printed_cell(old) != printed_cell(r):  # matched through a reading cellfix corrected
                    rejected.append({**r, 'why': [f"the page image prints {old.get('raw_value')} (accepted row {old['row_id']}, "
                                                  f"corrected by cellfix from this reading); review which is right"]})
                    log(pmid, 'conflict', old['row_id'], r['row_id'])
                elif old.get('unit') == r.get('unit') and old.get('value') and r.get('value') and close(old['value'], r['value']):
                    dup += 1; log(pmid, 'reworded_duplicate', old['row_id'], r['row_id'])
                else:
                    rejected.append({**r, 'why': [f"same printed cell as accepted row {old['row_id']} but converted differently "
                                                  f"({old.get('value')} {old.get('unit')}); review which is right"]})
                    log(pmid, 'conflict', old['row_id'], r['row_id'])
                continue
            back = None  # a value an audit dropped for its organism label alone, coming back relabelled
            if k not in current and k not in dropped:
                pc = printed_cell(r)
                found = {}  # each dropped row pairing with r on its own, followed to the drop that decides now
                for o in dropped_cells.get(pc, []):
                    if twin(r, {pc: [o]}):
                        f, s = decides(r, o, pc)
                        found[(f['row_id'], f.get('dropped'))] = (f, s)
                hard = [f for f, s in found.values() if s == 'hard']
                free = [f for f, s in found.values() if s == 'free']
                came = [f for f, s in found.values() if s == 'back']
                if hard or len(free) > 1:  # a refuted value, or two listed drops it could be: decided by hand
                    k = slot(twin(r, {pc: hard or free}) or (hard or free)[0])
                elif free:
                    back = free[0]
                elif came:  # its value came back already: a copy, or the same cell converted otherwise
                    got = next(c for c in current.values() if c['row_id'] == returned[(came[0]['row_id'], came[0].get('dropped'))])
                    if got.get('unit') == r.get('unit') and got.get('value') and r.get('value') and close(got['value'], r['value']):
                        dup += 1; log(pmid, 'reworded_duplicate', got['row_id'], r['row_id'])
                    else:
                        rejected.append({**r, 'why': [f"same printed cell as accepted row {got['row_id']} but converted "
                                                      f"differently ({got.get('value')} {got.get('unit')}); review which is right"]})
                        log(pmid, 'conflict', got['row_id'], r['row_id'])
                    continue
            if k in dropped:
                rejected.append({**r, 'why': [f'audit dropped this measurement before (row {dropped[k]}); '
                                              f'reconsider it explicitly, do not re-add it silently']})
            elif k in current:
                old = current[k]
                if old.get('unit') == r.get('unit') and old.get('value') and r.get('value') and close(old['value'], r['value']):
                    dup += 1
                else:
                    rejected.append({**r, 'why': [f"conflicts with accepted row {old['row_id']} "
                                                  f"({old.get('raw_value')} {old.get('raw_unit')}); review which is right"]})
                    log(pmid, 'conflict', old['row_id'], r['row_id'])
            elif k in held:  # the paper's censored value for this slot: a value and a bound for one measurement
                rejected.append({**r, 'why': [f"conflicts with censored row {held[k]['row_id']} ({held[k].get('raw_value')} "
                                              f"{held[k].get('raw_unit')}); review which is right"]})
                log(pmid, 'conflict', held[k]['row_id'], r['row_id'])
            else:
                r['added'] = now()
                r['row_id'] = unique_id(r, taken); taken.add(r['row_id'])
                current[k] = r; new.append(r)
                if back:
                    returned[(back['row_id'], back.get('dropped'))] = r['row_id']
                    relabels.append((back, r))
        nb, bdup = append_bounds(pmid, bounds, rejected, current, held, taken)
        dup += bdup
        cat.seek(0, 2)
        for r in new:
            cat.write(json.dumps(r, ensure_ascii=False) + '\n')
        cat.flush()
        with open(REJECTED, 'a') as rej:
            for r in rejected:
                rej.write(json.dumps(r, ensure_ascii=False) + '\n')
        for o, r in relabels:
            log(pmid, 'relabelled', o['row_id'], r['row_id'], f"organism {o.get('organism') or '-'} -> "
                f"{r.get('organism') or '-'}, strain {o.get('strain') or '-'} -> {r.get('strain') or '-'}", o.get('dropped'))
    return new, dup, nb


def bound_ids():
    """Every row_id in bounds.jsonl (a row_id is unique across it and catalog.jsonl)."""
    return {json.loads(l)['row_id'] for l in open(BOUNDS) if l.strip()} if BOUNDS.exists() else set()


def bound_rows(pmid):
    """This paper's censored values in bounds.jsonl, by slot."""
    out = {}
    if BOUNDS.exists():
        for line in open(BOUNDS):
            if pmid in line and line.strip():
                r = json.loads(line)
                if r.get('pmid') == pmid:
                    out[slot(r)] = r
    return out


def append_bounds(pmid, bounds, rejected, current, held, taken):
    """Censored values (a printed bound or "not detected", check()) into bounds.jsonl, apart from the numeric catalog:
    never in its kcat/Km columns, medians or database comparisons (item 7 of
    work/top_journal_20261021/FIXES_FOR_MAIN_CHAT_20261022.md, 2026-10-24). One per slot, as for values: the same
    censored cell again is a duplicate (also reworded: same metric, kind, cell, location, substrate and variant), another
    one a conflict; a slot the catalog holds a value for is a conflict; a slot an audit dropped stays dropped. Called by
    append_rows under the catalog lock. Returns (new rows, duplicates)."""
    if not bounds:
        return [], 0
    gone = [r for r in audit_dropped() if censored_kind(r) and r.get('pmid') == pmid]
    # a dropped censored value blocks the same kind again; another kind is a correction ('not detected' dropped as a
    # constant the paper could not determine, then the paper's own 'Km >> 15 mM' as a '>' bound)
    dropped = {slot(r): r['row_id'] for r in gone}
    dropped_kind = {slot(r): censored_kind(r) for r in gone}
    same = lambda o, r: o.get('censored') == r.get('censored') and squash(o.get('raw_value', '')) == squash(r.get('raw_value', ''))
    # an 'ND' cell is no fingerprint (unlike a printed number): a reworded copy differs in the enzyme's wording only, and
    # agrees on everything that tells one assay from another (19362172 prints ND for H21A with and without Co2+)
    assay = lambda x: ([squash(x.get(k) or '') for k in ('location', 'substrate', 'cosubstrate', 'metric_note', 'construct')]
                       + [str(x.get(k)) for k in ('pH', 'temperature_C')]
                       + sorted(squash(c) for c in condition_parts(x.get('conditions'))[0]))
    # the same enzyme in other words ('HisA' / 'HisA protein'), never another enzyme, organism or gene of the table
    named = lambda o, r: enzyme_core(o) == enzyme_core(r) and squash(o.get('organism', '')) == squash(r.get('organism', '')) and gene_of(o) == gene_of(r)
    reworded = lambda o, r: o['metric'] == r['metric'] and same(o, r) and assay(o) == assay(r) and same_variant(o, r) and named(o, r)
    earlier = list(held.values())  # rows of one read are never copies of each other
    new, dup = [], 0
    for r in bounds:
        k = slot(r)
        old = held.get(k) or next((o for o in earlier if reworded(o, r)), None)
        if k not in dropped and k not in held:
            was = next((o for o in gone if reworded(o, r)), None)  # an audit-dropped censored value, reworded
            if was:
                dropped[k] = was['row_id']
        if k in dropped and k in dropped_kind and dropped_kind[k] != censored_kind(r):
            dropped.pop(k)  # another kind than the one dropped: a correction
        if k in dropped:
            rejected.append({**r, 'why': [f'audit dropped this censored value before (row {dropped[k]}); '
                                          f'reconsider it explicitly, do not re-add it silently']})
        elif k in current:
            o = current[k]
            rejected.append({**r, 'why': [f"the catalog holds a value for this measurement (row {o['row_id']}: "
                                          f"{o.get('raw_value')} {o.get('raw_unit')}); review which is right"]})
            log(pmid, 'conflict', o['row_id'], r['row_id'])
        elif old and same(old, r):
            dup += 1
        elif old:
            rejected.append({**r, 'why': [f"conflicts with censored row {old['row_id']} ({old.get('raw_value')}); review which is right"]})
            log(pmid, 'conflict', old['row_id'], r['row_id'])
        else:
            r['added'] = now()
            r['row_id'] = unique_id(r, taken); taken.add(r['row_id'])
            held[k] = r; new.append(r)
    if new:
        with open(BOUNDS, 'a') as f:
            for r in new:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return new, dup


def cmd_limitfix(why, *ids):
    """Clear the `limit` of censored values (bounds.jsonl) whose printed limit bounds another quantity than their own
    kcat, Km or kcat/Km (19646996: a hydrolysis rate's detection limit was stored as the kcat's): the limit goes, code
    checks the row again (bound then empty), the evidence goes into verify_note and log.tsv says 'limitfix'."""
    ids = set(ids)
    with catalog_lock():
        rows = [json.loads(l) for l in open(BOUNDS) if l.strip()] if BOUNDS.exists() else []
        texts, done = {}, []
        for i, r in enumerate(rows):
            if r['row_id'] not in ids:
                continue
            r = {**r, 'limit': ''}
            if r['pmid'] not in texts:
                texts[r['pmid']] = squash(paper_text(r['pmid']))
            norm, bad = check(r, texts[r['pmid']])
            if set(bad) <= {'quote_not_in_paper', 'value_not_in_quote', 'marker_not_in_quote'} and r.get('quote_check'):
                bad = []
            if bad:
                print(f"{r['row_id']}: not changed, the check fails: {'; '.join(bad)}"); continue
            r.update(norm)
            r.pop('bound_note', None) if not norm.get('bound_note') else None
            r['verify_note'] = f'limit removed ({now()}): {why}' + (f"; {r['verify_note']}" if r.get('verify_note') else '')
            rows[i] = r; done.append(r)
        if done:
            tmp = BOUNDS.with_suffix('.jsonl.tmp')
            with open(tmp, 'w') as out:
                out.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in rows)
            os.replace(tmp, BOUNDS)
            for r in done:
                log(r['pmid'], 'limitfix', r['row_id'], why)
    missing = ids - {r['row_id'] for r in done}
    print(f'{len(done)} limits removed' + (f'; not changed: {" ".join(sorted(missing))}' if missing else ''))


def cmd_pmfix(why, *ids):
    """Take the ± off values whose printed cell has none: before 2026-10-09 11:49 (495383e) check() completed a ±
    the reader had dropped from the first '<number> ±' in the quote even when the number was printed twice, so a bare
    cell beside an equal cell with a ± got the neighbour's (20659899 W315L: kcat 1.13 ± 0.05, kcat/Km 1.13). raw_value
    becomes the printed number alone, code checks the row again (it no longer fills a ± for a number printed twice), the
    evidence goes into verify_note and log.tsv says 'pmfix'. The value itself is unchanged."""
    ids = set(ids)
    with catalog_lock():
        lines = [l for l in open(CATALOG) if l.strip()]
        at = {json.loads(l)['row_id']: i for i, l in enumerate(lines) if any(f'"row_id": "{x}"' in l for x in ids)}
        texts, done = {}, []
        for rid in sorted(ids):
            if rid not in at:
                print(f'{rid}: not in the catalog'); continue
            r = json.loads(lines[at[rid]])
            bare = re.split(r'\s*(?:\u00b1|\+/-)', r.get('raw_value', ''))[0].strip()
            if bare == r.get('raw_value', '').strip():
                print(f'{rid}: {r["raw_value"]!r} has no ±: nothing to take off'); continue
            r = {**r, 'raw_value': bare}
            if r['pmid'] not in texts:
                texts[r['pmid']] = squash(paper_text(r['pmid']))
            norm, bad = check(r, texts[r['pmid']])
            if set(bad) <= {'quote_not_in_paper', 'value_not_in_quote', 'marker_not_in_quote'} and r.get('quote_check'):
                bad = []
            if bad or norm.get('raw_value', bare) != bare:
                print(f"{rid}: not changed: {'; '.join(bad) or 'check() would fill the ± in again'}"); continue
            r.update(norm)
            r['verify_note'] = f'± removed ({now()}): {why}' + (f"; {r['verify_note']}" if r.get('verify_note') else '')
            r['checked'] = now()
            lines[at[rid]] = json.dumps(r, ensure_ascii=False) + '\n'
            done.append(r)
            print(f"{rid}: {r['metric']} {bare} {r['raw_unit']} (± removed)")
        if done:
            tmp = CATALOG.with_suffix(f'.jsonl.{os.getpid()}.tmp')
            tmp.write_text(''.join(lines))
            os.replace(tmp, CATALOG)
            for r in done:
                log(r['pmid'], 'pmfix', r['row_id'], why)
    print(f'{len(done)} ± removed')
    return {r['row_id'] for r in done}


CELL_TEXT = re.compile(r"[\d\s.,()\[\]{}\u00b1x\u00d7X*^+\-\u2212\u2013/eE']+")  # digits, ±, brackets, a x 10^n or E power


def is_cell(text):
    """True when `text` can be a printed cell (3.4 x 10^5, (0.77 ± 3.6) x 10^-3, 1.2E-04): never a sentence, so a CELL and
    WHY given the wrong way round are refused instead of stored."""
    from units import parse_number
    t = (text or '').replace('+/-', '\u00b1').strip()
    return bool(t) and bool(CELL_TEXT.fullmatch(t)) and bool(re.search(r'\d', t)) and parse_number(t) is not None


def cmd_cellfix(cell, why, *ids):
    """Correct a printed cell its reader misread, when the page image prints another cell than the stored raw_value
    (3624267 Table II: the toluquinone kcat/Km exponent is a 5 whose bowl the 1-bit scan closed; its reader, its
    verifier and the OCR text layer read 3.4 x 10^6, three refuters on the scan 3.4 x 10^5, 2026-11-03). unitfix keeps
    a misread raw_value and drop blocks the slot, so neither fits. raw_value becomes the page image's cell, code converts
    it again and check() must pass; the quote stays the text layer's line, so the row says the cell was read on the page
    image (quote_check). The reading replaced goes into verify_note (append_rows then refuses it from a re-read), log.tsv
    says 'cellfix', same row_id; records keyed to the row (audits, database checks, implausible-value reviews) are
    listed for whoever runs it."""
    if not is_cell(cell) or not why.strip() or is_cell(why):
        sys.exit(f'usage: catlog.py cellfix CELL WHY ROW_ID... ({cell!r} is not a printed cell, or WHY is missing)')
    ids = set(ids)
    with catalog_lock():
        lines = [l for l in open(CATALOG) if l.strip()]
        at = {json.loads(l)['row_id']: i for i, l in enumerate(lines) if any(f'"row_id": "{x}"' in l for x in ids)}
        texts, done = {}, []
        for rid in sorted(ids):
            if rid not in at:
                print(f'{rid}: not in the catalog'); continue
            r = json.loads(lines[at[rid]])
            old = r.get('raw_value', '')
            if squash(old) == squash(cell):
                print(f'{rid}: already {old!r}'); continue
            r = {**r, 'raw_value': cell}
            if r['pmid'] not in texts:
                texts[r['pmid']] = squash(paper_text(r['pmid']))
            norm, bad = check(r, texts[r['pmid']])
            if not set(bad) <= {'quote_not_in_paper', 'value_not_in_quote', 'marker_not_in_quote'} or norm.get('raw_value', cell) != cell:
                print(f"{rid}: not changed: {'; '.join(bad) or 'check() would change the cell again'}"); continue
            r.update(norm)
            r['quote_check'] = (f"the page image prints {cell}; the reader had read {old} (cellfix {now()})"
                                + (f"; {r['quote_check']}" if r.get('quote_check') else ''))
            r['verify_note'] = f"printed cell corrected from '{old}' to '{cell}' ({now()}): {why}" + (f"; {r['verify_note']}" if r.get('verify_note') else '')
            r['checked'] = now()
            lines[at[rid]] = json.dumps(r, ensure_ascii=False) + '\n'
            done.append((r, old))
            print(f"{rid}: {r['metric']} {old} -> {cell} {r['raw_unit']} = {r['value']:.4g} {r['unit']}")
        if done:
            tmp = CATALOG.with_suffix(f'.jsonl.{os.getpid()}.tmp')
            tmp.write_text(''.join(lines))
            os.replace(tmp, CATALOG)
            for r, old in done:
                log(r['pmid'], 'cellfix', r['row_id'], f"{old} -> {r['raw_value']}: {why}")
    for r, _ in done:  # verdicts given on the old reading carry over by row_id: say so
        rid = r['row_id']
        keyed = [f'{f[2]} {f[0]}' for f in events() if len(f) > 3 and f[3] == rid and f[2] in ('audit_keep', 'audit_drop')]
        for name in ('database_corrections.tsv', 'implausible_as_printed.tsv'):
            f = ROOT / 'sources' / name
            if f.exists() and rid in f.read_text():
                keyed.append(f'a line in sources/{name}')
        if keyed:
            print(f"{rid}: records made on the old reading: {', '.join(keyed)}; review them")
    print(f'{len(done)} cells corrected')
    return {r['row_id'] for r, _ in done}


def cmd_censored(n):
    """Claim up to n papers of sources/censored_reread.txt (tools/censored_scan.py: papers read before the reader prompt
    recorded censored values) for a pass that reads only those (`catlog-batch` with args.censored = true, then `add`):
    papers that are done and had no such pass. Their work files go to work/old/ (never deleted) and the claim record says
    censored_only, so `add` leaves the paper done and its counts as they were."""
    lst = ROOT / 'sources' / 'censored_reread.txt'
    if not lst.exists():
        sys.exit('no sources/censored_reread.txt: run python3 tools/censored_scan.py first')
    ev = events()  # passed: an add line with bounds= (every add since the rule) after the paper's last claim, so a full
    # re-read under the rule counts too (36394293, 31436969 on 2026-10-29); an unfinished pass is claimed again
    claims = {f[1]: f[0] for f in ev if f[2] == 'censored_claim'}
    passed = {f[1] for f in ev if f[2] == 'add' and f[0] >= claims.get(f[1], '') and any(x.startswith('bounds=') for x in f[3:])}
    picked, held = [], locked()  # the method paper's test set: never read again here
    with Queue() as q:
        for pmid in lst.read_text().split():
            if len(picked) >= n:
                break
            if pmid in passed or pmid in held or q.rows.get(pmid, {}).get('status') != 'done' or not (TEXTS / f'{pmid}.txt').exists():
                continue
            q.set(pmid, status='reading', note='censored values pass')
            picked.append(pmid)
    (WORK / 'old').mkdir(exist_ok=True)
    for pmid in picked:
        for f in WORK.glob(f'{pmid}.*.json'):
            shutil.move(str(f), str(WORK / 'old' / f'{f.stem}.{int(time.time())}.json'))
        claim_prompts(pmid)
        p = WORK / f'{pmid}.prompts.json'
        p.write_text(json.dumps({**json.loads(p.read_text()), 'censored_only': True}) + '\n')
        log(pmid, 'censored_claim')
    print(' '.join(picked))


def cmd_recover(reason, *args):
    """Bring back rows a rule no longer rejects: each row of rejected.jsonl whose ONLY reason starts with `reason` is
    checked again by today's code and appended as `add` does (duplicates, conflicts and audit drops handled the same).
    2026-10-10: ratio_non_closure (the printed kcat/Km disagreeing with kcat ÷ Km dropped all three; now it drops
    nothing). rejected.jsonl keeps its history; log.tsv says `recover`. `--dry` lists without writing; PMIDs limit it."""
    dry = '--dry' in args
    only = {a for a in args if a != '--dry'}
    rows = {}
    for line in open(REJECTED):
        if line.strip():
            r = json.loads(line)
            w = [str(x) for x in r.get('why', [])]
            if w and all(x.startswith(reason) for x in w) and (not only or r['pmid'] in only or r.get('row_id') in only):
                rows.setdefault(r['pmid'], []).append(r)
    total = 0
    for pmid, rs in rows.items():
        text_sq = squash(paper_text(pmid))
        kept, still = [], []
        for r in rs:
            was = '; '.join(str(x) for x in r.get('why', []))
            r = {k: v for k, v in r.items() if k not in ('why', 'added', 'dropped')}
            r['verify_note'] = '; '.join(x for x in (f'recovered ({reason}); was rejected: {was}'[:300], r.get('verify_note')) if x)
            norm, bad = check(r, text_sq)
            if set(bad) <= {'quote_not_in_paper', 'value_not_in_quote', 'marker_not_in_quote'} and r.get('quote_check'):
                bad = []  # verified on the page image (judge)
            if bad:
                still.append((r, bad)); continue
            r.update(norm); r['row_id'] = row_id(r); r['checked'] = now()
            kept.append(r)
        for r, bad in still:
            print(f'{pmid}: {r["metric"]} {r.get("raw_value")} stays rejected: {"; ".join(bad)}')
        if dry:
            print(f'{pmid}: would recover {len(kept)} of {len(rs)} ({", ".join(r["metric"] + " " + str(r.get("raw_value")) for r in kept)})')
            total += len(kept); continue
        rej = []
        new, dup, nb = append_rows(pmid, kept, rej)
        log(pmid, 'recover', f'kept={len(new)}', f'dup={dup}', f'rejected={len(rej)}', f'still_rejected={len(still)}', f'reason={reason}',
            *([f'bounds={len(nb)}'] if nb else []))
        print(f'{pmid}: recovered {len(new)} (dup {dup})' + (f', censored {len(nb)}' if nb else '') + f', still rejected {len(still)}')
        total += len(new) + len(nb)  # a censored row goes to bounds.jsonl, not the catalog
    print(f'{"would recover" if dry else "recovered"} {total} values from {len(rows)} papers ({reason})')


def keep_read(pmid):
    """True when the paper only needs verifying: a readable reader file, written after the paper text and never
    verified. An interrupted batch (usage limit, killed chat) leaves exactly this, and reading it again costs a full
    reader for nothing (17 papers on 2026-10-10/11). Any other reread (supplement, prompt fix, audit) has verdicts
    on file, or a read older than the text, and sets the reader file aside as before."""
    r, v = WORK / f'{pmid}.read.json', WORK / f'{pmid}.verify.json'
    t, s = TEXTS / f'{pmid}.txt', TEXTS / f'{pmid}.supp.txt'  # a supplement filed after the read: read again
    if v.exists() or not r.exists() or not (t.exists() and r.stat().st_mtime > max(t.stat().st_mtime, s.stat().st_mtime if s.exists() else 0) + 1):
        return False
    try:
        return isinstance(json.loads(r.read_text()).get('rows'), list)
    except (json.JSONDecodeError, OSError):
        return False


def cmd_reread(pmid, why, fresh=False, limit=False):
    """Send a paper back to be read again (supplement added, prompt fixed, completeness audit): its work files are set
    aside in work/old/ (never deleted) and the paper returns to todo. A fresh unverified read is kept, so the next
    batch only verifies it (keep_read). Accepted rows stay; finish() keeps one value per measurement and flags any
    conflict."""
    old = WORK / 'old'
    old.mkdir(exist_ok=True)
    with Queue(write=False) as q:
        st = q.rows.get(pmid, {}).get('status')
    was_parked = st == 'parked'
    kept = not fresh and keep_read(pmid)  # --fresh: read it again anyway (e.g. after a reader prompt fix)
    # the agents died (usage limit, safety stop): no reader output, or `add` could not finish it (no verifier output)
    # a death = this paper's agents produced nothing usable: no reader file, or a fresh read whose verifier died (kept).
    # Files merely out of date (a newer text or supplement) are no death; nor is an outage (limit).
    died = not limit and st == 'reading' and (kept or not (WORK / f'{pmid}.read.json').exists())
    if st == 'reading' and claimed(pmid).get('censored_only') and not fresh:  # a censored-values pass that did not
        with Queue() as q:                                                   # finish: the paper is done; claim it again
            q.set(pmid, status='done', note='censored values pass not finished: `catlog.py censored` claims it again')
        for f in WORK.glob(f'{pmid}.*.json'):
            shutil.move(str(f), str(old / f'{f.stem}.{int(time.time())}.json'))
        log(pmid, 'reread', why, 'censored_pass_back')
        print(pmid, 'back to done (censored values pass not finished)')
        return
    for f in WORK.glob(f'{pmid}.*.json'):
        if kept and f.name in (f'{pmid}.read.json', f'{pmid}.prompts.json'):  # the kept read's claim record (claim_prompts)
            continue
        shutil.move(str(f), str(old / f'{f.stem}.{int(time.time())}.json'))
    ev = [f for f in events() if f[1] == pmid]
    since = max((i for i, f in enumerate(ev) if f[2] == 'unparked'), default=-1)
    deaths = sum(1 for f in ev[since + 1:] if f[2] == 'reread' and 'no_reader_output' in f[3:]) + died
    status = 'parked' if deaths >= 3 and not was_parked else 'todo'  # parked: back by itself after 24 h (unpark_due)
    if was_parked:
        log(pmid, 'unparked', why)
    with Queue() as q:
        q.set(pmid, status=status, note=(f'agents died {deaths} times; ' if status == 'parked'
                                        else 'read kept, verify only: ' if kept else 'read again: ') + why[:150])
    log(pmid, 'reread', why, *(['read_kept'] if kept else []), *(['no_reader_output'] if died else []))
    print(pmid, 'parked (agents died 3 times)' if status == 'parked'
          else 'back to todo (read kept: only the verifier has to run)' if kept else 'back to todo')


def cmd_worklist(lane_name='', n=20):
    """Papers no automatic route could supply, most BRENDA values first: the browser download list."""
    cov = coverage()
    with Queue() as q:
        rows = {p: r for p, r in q.rows.items() if r['status'] in ('needs_browser', 'needs_supplement')
                and (lane_of(r) == lane_name if lane_name else r['status'] == 'needs_browser')}
    for p in priority(list(rows))[:n]:
        r = rows[p]
        values, before = cov.get(p, (0, 0))
        print(f"{p}\t{r.get('note', '')}\tdoi={r.get('doi', '')}\tdb_values={values}\tcertified_before={before}\t{r.get('title', '')[:90]}")


MARKS = ('todo', 'done', 'no_kinetics', 'wrong_paper', 'unavailable', 'incomplete')


def cmd_mark(pmids, what, why):
    """Write down what a person found out, so no later chat redoes it:
    lane=<lane>            waiting for a browser or interlibrary loan (lane=ill: ISU has no access)
    click=<url>            waiting for the user to clear a robot/Cloudflare check at that site once, in a normal tab
    login=<url>            waiting for the user to sign in there (OpenAthens, society account)
    doi=<DOI>              PubMed's DOI is stale; this one is right (get() keeps it; the free routes are retried)
    todo | no_kinetics | wrong_paper | unavailable   set the status (unavailable: no copy exists anywhere we can reach)
    incomplete             the copy lacks what a value needs (publisher OCR text, no PDF to see the table on): it goes
                           to the "better copy" download list; filing the PDF reads it again (its values stay meanwhile)
    A paper waiting for a supplement or a better copy keeps that status; the earlier reason is kept in the note."""
    from fetch import lane as lane_for
    key, _, val = what.strip().partition('=')
    val, why = val.strip(), ' '.join(why.split())
    if key == 'doi':
        val = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', val, flags=re.I)
    if key in ('click', 'login'):
        u = urllib.parse.urlsplit(val if '//' in val else 'https://' + val)
        val = f'{u.scheme}://{u.netloc}' if u.netloc else ''  # one site, one check: grouped by site in asks
    if not (key in ('lane', 'click', 'login', 'doi') and val or what in MARKS):
        sys.exit(f'mark: {what!r} is not one of lane=, click=, login=, doi= or {", ".join(MARKS)}')
    with Queue() as q:
        for p in (x.strip() for x in pmids if x.strip()):
            r = q.rows.get(p)
            if r is None:
                print(p, 'is not in the queue'); continue
            lane_now = re.search(r'lane=([^\s;]+)', r.get('note', ''))
            lane_now = lane_now[1] if lane_now else (lane_for(r.get('doi')) if r.get('doi') else 'other')
            earlier = re.sub(r'\b(?:lane|click|login)=[^\s;]+;?\s*|;?\s*\bretry$', '', r.get('note', '')).strip('; ')
            keep = r['status'] if r['status'] in ('needs_supplement',) + REDOWNLOAD else 'needs_browser'
            if key == 'doi' and is_standin(p):
                print(p, 'has no PMID: it IS its DOI; a different DOI is another paper (mark it wrong_paper)'); continue
            if key == 'doi':
                q.set(p, doi=val, **({'status': 'todo', 'note': f'doi fixed ({val}); free routes retried'}
                                     if r['status'] in ('needs_browser', 'wrong_paper') else {}))  # a wrong DOI fetched another article
                doi_fixes()[p] = val
                log(p, 'doi_fix', val, why)
            elif key in ('lane', 'click', 'login'):
                lane_new = val if key == 'lane' else lane_now
                extra = f'; {key}={val}' if key != 'lane' else ''
                free = re.search(r'\bfree=[^\s;]+', earlier)  # a J-STAGE paper's only link: kept ahead of the 200-character cut
                if free:
                    extra, earlier = f'{extra}; {free[0]}', re.sub(r'\bfree=[^\s;]+;?\s*', '', earlier).strip('; ')
                q.set(p, status=keep, note='; '.join(x for x in (f'lane={lane_new}{extra}', why, earlier) if x)[:200])
                log(p, 'mark', f'{key}={val}', why)
            else:
                have = ROOT / 'papers' / f'{p}.pdf'
                if what == 'wrong_paper' and have.exists():
                    remember_bad(p, have, f'wrong_paper (mark): {why}')  # never filed for this paper again
                q.set(p, status=what, note=why[:200]); log(p, 'mark', what, why)
            print(p, f'{key}={val}' if val else what)


def esummary_many(pmids):
    """PubMed citation facts (title, journal, year, authors, volume, pages, DOI, PMCID, PII), 200 papers per request,
    cached in work/esummary.json."""
    cache_p = WORK / 'esummary.json'
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    for p in pmids:
        r = standins().get(p) if is_standin(p) else None
        if r:  # no PMID: BRENDA's citation (journal, year, volume:pages, authors) and the Crossref-checked DOI
            cache[p] = {'title': r['title'], 'journal': r['journal'], 'year': r['year'], 'authors': r['authors'],
                        'volume': r['vol'], 'issue': '', 'pages': r['pages'], 'doi': r['doi'], 'pmc': '', 'pii': '', 'issn': ''}
    need = [p for p in pmids if p not in cache and not is_standin(p)]
    for i in range(0, len(need), 200):
        chunk = need[i:i + 200]
        try:
            d = json.loads(http('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json'
                                '&tool=catlog' + (f'&email={CONTACT}' if CONTACT else '') + '&id=' + ','.join(chunk)))['result']
        except Exception:
            break  # offline: the page still lists what papers.tsv knows
        for p in chunk:
            e = d.get(p) or {}
            ids = {a['idtype']: a['value'] for a in e.get('articleids', [])}
            au = [a['name'] for a in e.get('authors', [])]
            cache[p] = {'title': e.get('title', ''), 'journal': e.get('source', ''), 'year': e.get('pubdate', '')[:4],
                        'authors': '; '.join(au[:6]) + ('; et al.' if len(au) > 6 else ''), 'volume': e.get('volume', ''),
                        'issue': e.get('issue', ''), 'pages': e.get('pages', ''), 'issn': e.get('issn') or e.get('essn', ''),
                        'doi': ids.get('doi', ''), 'pmc': ids.get('pmc', ''), 'pii': ids.get('pii', '')}
        time.sleep(0.4)
    WORK.mkdir(exist_ok=True)
    cache_p.write_text(json.dumps(cache))
    return cache


HOW = {  # one line per lane, from the old download chat's proven routes (downloads/old_download_routes_README.md)
    'pmc': 'Free, no login: open the PMC page and click "PDF".',
    'jstage': 'Free, no login: open the J-STAGE link and click "Download PDF" (J-STAGE asks scripts not to fetch PDFs).',
    'sciencedirect': 'Open the DOI on the campus network; use the "View PDF" link that carries this article\'s own PII '
                     '(not a recommended article). One paper at a time. ISU access ends around 2004: newer ones usually '
                     'need interlibrary loan.',
    'jbc': 'Free archive: open the DOI (jbc.org / jlr.org) and use the PDF button.',
    'acs': 'Direct PDF link on the campus network.',
    'wiley': 'Direct PDF link (pdfdirect); campus network or OpenAthens.',
    'oup': 'Article page on academic.oup.com, then the PDF link.',
    'springer_ill': 'Direct PDF link works only for titles ISU licenses; "Buy article" means interlibrary loan.',
    'other': 'Open the DOI; PDF link on the article page.',
}
PDF_LINK = {'acs': 'https://pubs.acs.org/doi/pdf/{doi}', 'wiley': 'https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}',
            'springer_ill': 'https://link.springer.com/content/pdf/{doi}.pdf'}
ILL_LANES = ('ill', 'ill_no_doi')


def lane_of(r):
    return (re.search(r'lane=([^\s;]+)', r.get('note', '')) or [None, 'other'])[1]


def cmd_asks():
    """Write downloads/asks.html: every paper that needs a person, cheapest first, with links: checks to clear once,
    free PMC papers, publisher papers by lane, supplements, re-downloads, then interlibrary loan (also written as
    downloads/ill_requests.csv). Rebuilt from papers.tsv every time: never edit it, never copy it elsewhere."""
    import html as H
    with Queue(write=False) as q:
        rows = {p: r for p, r in q.rows.items() if r['status'] in WAITING}
    cov = coverage()
    meta = esummary_many(list(rows))
    order = sorted(rows, key=lambda p: -cov.get(p, (0, 0))[0])
    secs = {k: [] for k in ('pmc', 'publisher', 'supplement', 'redownload', 'ill')}
    checks = {}
    for p in order:
        r, ln = rows[p], lane_of(rows[p])
        m = re.search(r'\b(click|login)=([^\s;]+)', r.get('note', ''))
        if m:
            u = urllib.parse.urlsplit(m[2] if '//' in m[2] else 'https://' + m[2])
            checks.setdefault((m[1], f'{u.scheme}://{u.netloc}'), []).append(p)
        sec = ('ill' if ln in ILL_LANES else 'supplement' if r['status'] == 'needs_supplement'
               else 'redownload' if r['status'] in REDOWNLOAD else 'pmc' if ln == 'pmc' else 'publisher')
        secs[sec].append(p)
    secs['publisher'].sort(key=lambda p: (list(HOW).index(lane_of(rows[p])) if lane_of(rows[p]) in HOW else 99,
                                          -cov.get(p, (0, 0))[0]))

    def esc(x):
        return H.escape(str(x or ''))

    def link(url, text):
        return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(text)}</a>' if url else ''

    def row_html(i, p):
        r, e, ln = rows[p], meta.get(p, {}), lane_of(rows[p])
        doi = r.get('doi') or e.get('doi', '')
        links = [link(f'https://doi.org/{doi}', 'article') if doi else link(
                     'https://pubmed.ncbi.nlm.nih.gov/?term=' + urllib.parse.quote(e.get('title') or r.get('title', '')), 'search title')]
        if doi and ln in PDF_LINK:
            links.append(link(PDF_LINK[ln].format(doi=doi), 'PDF'))
        if e.get('pmc'):
            links.append(link(f"https://pmc.ncbi.nlm.nih.gov/articles/{e['pmc']}/", 'PMC'))
        free = re.search(r'\bfree=(\S+?)(?:;|\s|$)', r.get('note', ''))
        if free:
            links.append(link(free[1], 'free copy'))
        cite = ' '.join(x for x in (e.get('journal', ''), e.get('year', ''), e.get('volume', '') and f"{e['volume']}:{e.get('pages', '')}") if x)
        why = re.sub(r'(lane|free)=[^\s;]+;?\s*', '', r.get('note', '')).strip()
        save = f'PMID{p}_supp1.&lt;ext&gt; or inbox/{p}/' if r['status'] == 'needs_supplement' else f'PMID{p}.pdf'
        idcell = esc(p) + ' <span class="m">(no PMID)</span>' if is_standin(p) else link(f"https://pubmed.ncbi.nlm.nih.gov/{p}/", p)
        return (f'<tr><td>{i}</td><td>{idcell}</td>'
                f'<td><b>{esc(e.get("title") or r.get("title"))}</b><br><span class="m">{esc(cite)}'
                f'{" · " + esc(ln) if ln else ""}{" · " + esc(why) if why else ""}</span></td>'
                f'<td class="n">{cov.get(p, (0, 0))[0]}</td><td>{" · ".join(x for x in links if x)}</td><td><code>{save}</code></td></tr>')

    def table(ps):
        if not ps:
            return '<p class="m">Nothing here.</p>'
        head = '<tr><th>#</th><th>PMID or id</th><th>Paper</th><th title="values the databases cite from this paper">values</th><th>Links</th><th>Save as</th></tr>'
        return '<div class="t"><table>' + head + ''.join(row_html(i + 1, p) for i, p in enumerate(ps)) + '</table></div>'

    parts = []
    if checks:
        items = ''.join(f'<li>{link(u, u)} — {"sign in" if k == "login" else "clear the check"}'
                        f' in a normal Chrome tab, then tell Claude "done" ({len(ps)} papers wait on it)</li>'
                        for (k, u), ps in checks.items())
        parts.append(f'<h2>1. Clear once in Chrome ({len(checks)} sites)</h2><ul>{items}</ul>')
    parts.append(f'<h2>Free in PMC, no login ({len(secs["pmc"])})</h2><p class="m">{HOW["pmc"]}</p>' + table(secs['pmc']))
    lanes_txt = ''.join(f'<li><b>{esc(k)}</b>: {esc(v)}</li>' for k, v in HOW.items() if k != 'pmc'
                        and any(lane_of(rows[p]) == k for p in secs['publisher']))
    parts.append(f'<h2>Publisher sites, campus network ({len(secs["publisher"])})</h2><ul class="m">{lanes_txt}</ul>' + table(secs['publisher']))
    parts.append(f'<h2>Supplementary files ({len(secs["supplement"])})</h2><p class="m">The values are only in a supplement '
                 '(the line says which). Article page → Supplementary material. Save as shown, or put the files in '
                 f'<code>inbox/&lt;PMID&gt;/</code> under any names.</p>' + table(secs['supplement']))
    parts.append(f'<h2>Get a better copy ({len(secs["redownload"])})</h2><p class="m">The copy we have is a preview, '
                 'unreadable, or a different article.</p>' + table(secs['redownload']))
    parts.append(f'<h2>Interlibrary loan, optional ({len(secs["ill"])})</h2><p class="m">None of these are downloaded: ISU does '
                 'not subscribe to them and no free copy exists. To read one, request it through the ISU Library '
                 'interlibrary-loan service (it borrows a copy from another library); skipping them is fine. Request sheet: '
                 '<code>downloads/ill_requests.csv</code>. When a PDF arrives, save it to Downloads and tell Claude "filed".</p>'
                 + table(secs['ill']))
    with Queue(write=False) as q:
        untried = sum(1 for p, r in q.rows.items() if r['status'] == 'todo' and not on_disk(p))
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Papers to get</title><style>
:root{{--bg:#fff;--fg:#1d1d1f;--mute:#6e6e73;--line:#e3e3e8;--link:#0a58ca;--head:#f5f5f7}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#161618;--fg:#ececf0;--mute:#9a9aa2;--line:#2c2c31;--link:#7aa7ff;--head:#1f1f23}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.45 -apple-system,system-ui,sans-serif;margin:0;padding:16px;max-width:1200px}}
a{{color:var(--link)}} li,p,.box,td{{overflow-wrap:anywhere}} .m{{color:var(--mute);font-size:13px}} .n{{text-align:right}} code{{font-size:12px}}
.t{{overflow-x:auto}} table{{border-collapse:collapse;width:100%}} th,td{{border-bottom:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left}}
th{{background:var(--head);font-size:13px}} h2{{margin-top:28px}} .box{{border:1px solid var(--line);border-radius:8px;padding:10px 14px;background:var(--head)}}
</style></head><body>
<h1>Papers to get</h1>
<div class="box">Save each paper into <b>~/Downloads</b> under any name (or <code>PMID&lt;id&gt;.pdf</code>), or drop it into
<code>inbox/</code>. Then tell Claude <b>"filed"</b> (it runs <code>python3 catlog.py file</code>, checks the title and
sends the paper to be read). Supplements: <code>inbox/&lt;PMID&gt;/</code>. Highest-value papers first in every section.</div>
<p class="m">Generated {now()} by <code>python3 catlog.py asks</code> from papers.tsv; rebuilt every time, do not edit.
{len(rows)} papers need a person. {untried:,} papers have not been tried by the automatic routes yet
(<code>python3 catlog.py fetch 200</code> tries them; only what it cannot get lands here).</p>
{''.join(parts)}
</body></html>"""
    out = ROOT / 'downloads' / 'asks.html'
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    ill_p = ROOT / 'downloads' / 'ill_requests.csv'
    old_status = {}  # keep the request status the user typed; from the old list only an actual request
    for src in (ROOT / 'downloads' / 'springer_ill_requests_20261007.csv', ill_p):
        if src.exists():
            for r in csv.DictReader(open(src)):
                if src == ill_p or r.get('request_status', '').lower().startswith('requested'):
                    old_status[r.get('pmid', '')] = r.get('request_status', '')
    cols = ['priority_rank', 'db_values', 'lane', 'pmid', 'doi', 'authors', 'title', 'journal', 'year', 'volume', 'issue',
            'pages', 'issn', 'pubmed_url', 'request_status']
    with open(ill_p, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for i, p in enumerate(secs['ill'], 1):
            e = meta.get(p, {})
            w.writerow([i, cov.get(p, (0, 0))[0], lane_of(rows[p]), p, rows[p].get('doi') or e.get('doi', ''), e.get('authors', ''),
                        e.get('title') or rows[p].get('title', ''), e.get('journal', ''), e.get('year', ''), e.get('volume', ''),
                        e.get('issue', ''), e.get('pages', ''), e.get('issn', ''), '' if is_standin(p) else f'https://pubmed.ncbi.nlm.nih.gov/{p}/',
                        old_status.get(p) or 'not requested'])
    log('-', 'asks', *(f'{k}={len(v)}' for k, v in secs.items()), f'checks={len(checks)}')
    print(f'{out}: ' + ', '.join(f'{k} {len(v)}' for k, v in secs.items()) + f', sites to clear {len(checks)}')
    print(f'{ill_p}: {len(secs["ill"])} interlibrary-loan requests')


# ---------- Chrome download lanes (chrome-lanes workflow) ----------

DL = WORK / 'downloads'
LANES = DL / 'lanes.json'
CHROME_KEYS = ('acs', 'sd', 'wiley', 'wiley_sub', 'springer', 'oup', 'rsc', 'pnas', 'portland', 'jstage', 'microbiology', 'asm')
NO_CHROME = ('nature', 'jbc', 'other')  # listed in lanes.json, but no Chrome agent method for them (yet)
ROUTES = (  # DOI (lower case) -> Chrome method (paper-download skill's route table). First match wins, so journals that
    # moved host come first; Elsevier DOIs nothing here catches are 'sd' (fetch.ELSEVIER), the rest 'other'.
    (r'10\.1074/|10\.1016/s0021-9258|10\.1194/|10\.1016/s0022-2275', 'jbc'),  # JBC, J Lipid Res: Elsevier API (PDFs hit Cloudflare)
    (r'10\.1016/(s?0014-5793|j\.febslet)|10\.1111/(j\.1432-1033|j\.1742-4658|j\.0014-2956|febs\.)|10\.1046/j\.(1432-1033|'
     r'1432-1327|0014-2956)|10\.1002/(1873-3468|2211-5463|cssc\.)|10\.1096/|10\.1042/ba|10\.1007/s1174[56]|10\.1021/bp', 'wiley_sub'),
    # Wiley journal sub-sites: FEBS Lett, Eur J Biochem, FEBS J, FEBS Open Bio (febs.), ChemSusChem (chemistry-europe.),
    # FASEB J (faseb.), Biotechnol Appl Biochem (iubmb.), Lipids and JAOCS (aocs.), Biotechnol Prog (aiche.)
    (r'10\.1007/s10545', 'wiley'),  # J Inherit Metab Dis moved to Wiley
    (r'10\.1093/|10\.1104/|10\.1105/|10\.1210/|10\.1007/s10295|10\.1038/sj\.jim|10\.(1046|1111)/(j\.)?(1574-|1567-1364|1365-2672|1472-765x'
     r'|2042-7158)|10\.1111/(jam|lam|jphp)\.|10\.1016/s?(0378-1097|0168-6496|0168-6445|0928-8244)|10\.1271/bbb(?!1961)'
     r'|10\.1080/(09168451|00021369)|10\.1039/c\d(mb|mt)', 'oup'),
    # OUP, Plant Physiol, Plant Cell, and journals that moved there: JIMB, FEMS (Wiley and Elsevier DOIs), J Appl Microbiol,
    # Lett Appl Microbiol, J Pharm Pharmacol, Biosci Biotechnol Biochem and Agric Biol Chem (T&F DOIs; J-STAGE when the
    # note has a free= link), Mol BioSyst / Metallomics, Endocrine Society journals (10.1210)
    (r'10\.1053/he\.', 'other'),  # Hepatology: LWW
    (r'10\.1263/jbb', 'sd'),  # J Biosci Bioeng
    (r'10\.1529/', 'sd'), (r'10\.1110/', 'wiley'),  # Biophys J's old DOIs (Elsevier now), Protein Sci (Wiley; doi.org 2026-10-24)
    (r'10\.1002/|10\.1111/|10\.1046/|10\.1034/|10\.1155/', 'wiley'),  # wiley_sub when wiley_by_host.json saw a sub-site
    (r'10\.1021/', 'acs'), (r'10\.1039/', 'rsc'), (r'10\.1073/', 'pnas'), (r'10\.1042/', 'portland'),
    (r'10\.1007/|10\.1023/|10\.1385/|10\.1134/', 'springer'), (r'10\.1038/', 'nature'), (r'10\.1128/', 'asm'),
    (r'10\.1099/(vir|0022-1317)', 'other'), (r'10\.1099/', 'microbiology'))  # J Gen Virol: no free PDF
MOVED = {'academic.oup.com': 'oup', 'linkinghub.elsevier.com': 'sd', 'link.springer.com': 'springer'}  # Wiley DOIs gone elsewhere
SITE = {'acs': 'https://pubs.acs.org', 'sd': 'https://www.sciencedirect.com', 'wiley': 'https://onlinelibrary.wiley.com',
        'oup': 'https://academic.oup.com', 'rsc': 'https://pubs.rsc.org', 'pnas': 'https://www.pnas.org',
        'springer': 'https://link.springer.com', 'portland': 'https://portlandpress.com', 'asm': 'https://journals.asm.org',
        'microbiology': 'https://www.microbiologyresearch.org', 'jstage': 'https://www.jstage.jst.go.jp'}
RESULTS = ('saved', 'no_access', 'no_pdf', 'error', 'STOP')  # what a Chrome agent writes per paper
HOST = re.compile(r'\b(?:[a-z0-9-]+\.)+(?:org|com|net|jp|uk|de|cz)\b', re.I)


def wiley_journal(doi):
    """'10.1111/1432-1033' for 10.1111/j.1432-1033.1975.tb02282.x, '10.1002/cbic' for 10.1002/cbic.200300764 (one key
    for a journal's old j.<ISSN> and newer <ISSN> DOIs)."""
    m = re.match(r'(10\.\d+/)(?:\(sici\))?(?:j\.)?([a-z0-9-]+)', doi.lower())
    return m[1] + m[2] if m else doi.lower()


def wiley_hosts():
    """DOI -> the host a Wiley DOI's doi.org link went to (work/downloads/wiley_by_host.json, cached by a Chrome session),
    plus journal -> host where all its cached DOIs agree. Only journal sub-sites and other publishers count: a DOI sent
    to onlinelibrary.wiley.com can go on to a sub-site (the map lists FEBS Lett there; agents met it on febs.)."""
    try:
        pairs = [(x[1].lower(), h) for h, ps in json.loads((DL / 'wiley_by_host.json').read_text()).items()
                 if h not in ('onlinelibrary.wiley.com', 'doi.wiley.com') for x in ps if len(x) > 1]
    except (OSError, ValueError, AttributeError):
        return {}
    journals = {}
    for d, h in pairs:
        journals.setdefault(wiley_journal(d), set()).add(h)
    return {j: min(hs) for j, hs in journals.items() if len(hs) == 1} | dict(pairs)


def chrome_lane(r, hosts):
    """The Chrome method for a waiting paper (ROUTES), or None for a paper in PMC that no publisher method can get:
    that one is for the PMC website, whose terms forbid systematic downloading (the user's lane). A PMC paper with a
    publisher method (ASM, PNAS, ACS, ...) goes to the publisher's site, which is not PMC."""
    from fetch import ELSEVIER
    d, note = (r.get('doi') or '').lower(), r.get('note', '')
    if 'lane=jstage' in note or 'free=' in note and d.startswith(('10.1271/bbb1961', '10.1080/00021369')):
        return 'jstage'
    key = next((k for pat, k in ROUTES if re.match(pat, d)), 'sd' if d.startswith(ELSEVIER) else 'other')
    if key == 'wiley':  # where doi.org sent this DOI, else the Wiley sub-site an agent was stopped at, else its journal's
        m = re.search(r'\bclick=https?://([^\s;/]+\.onlinelibrary\.wiley\.com)', note)
        h = hosts.get(d) or (m[1] if m else '') or hosts.get(wiley_journal(d), '')
        key = 'wiley_sub' if h.endswith('.onlinelibrary.wiley.com') else MOVED.get(h, 'other') if h else 'wiley'
    if key == 'rsc' and 'click=https://academic.oup.com' in note:  # Mol BioSyst b-series DOIs: the journal moved to OUP
        key = 'oup'
    return None if lane_of(r) == 'pmc' and key in NO_CHROME else key


def still_needed(r):
    """A paper waiting for a download with no PDF here (a re-download keeps its old text, so texts do not count)."""
    return bool(r) and r['status'] in ('needs_browser',) + REDOWNLOAD and not (ROOT / 'papers' / f"{r['pmid']}.pdf").exists()


def progress_line(s):
    """One Chrome agent progress line {id, result, detail?, host?, ip?, ts?}, or None for junk."""
    try:
        j = json.loads(s)
    except ValueError:
        return None
    return j if isinstance(j, dict) and str(j.get('id') or '').strip() and j.get('result') in RESULTS else None


def line_date(ts, default):
    """YYYY-MM-DD of a progress line's ts (ISO text, or epoch seconds or milliseconds), else default."""
    s = str(ts or '').strip()
    if re.fullmatch(r'\d{9,13}(\.\d+)?', s):
        x = float(s)
        return time.strftime('%Y-%m-%d', time.localtime(x / 1000 if x > 1e11 else x))
    return s[:10] if re.match(r'\d{4}-\d\d-\d\d', s) else default


def lane_key(name):
    """The method of a progress file: lane_<method>_<tag>_<start>.jsonl, or an older lane_<method><tag>_<start>.jsonl."""
    rest = name[len('lane_'):]
    return max((k for k in CHROME_KEYS + NO_CHROME if rest.startswith(k)), key=len, default='')


LIVE_MINUTES = 10  # a lane_*.jsonl written this recently = a chrome-lanes run is live (critic.md C1)


def live_lane_files(minutes=LIVE_MINUTES):
    """Chrome agents' progress files (work/downloads/lane_*.jsonl) changed in the last `minutes`, newest first, as
    (path, mtime): a live chrome-lanes run appends to one after every paper."""
    now, out = time.time(), []
    for f in DL.glob('lane_*.jsonl'):
        try:
            t = f.stat().st_mtime
        except OSError:  # renamed or removed meanwhile
            continue
        if now - t < minutes * 60:
            out.append((f, t))
    return sorted(out, key=lambda x: -x[1])


def lane_run(name):
    """The run tag in a progress file's name: lane_<method>_<tag>_<start>.jsonl (the kit; a tag has no '_') or the
    older lane_<method><tag>_<start>.jsonl (lane_springerg_200 -> g); '' when the name has none (lane_acs_0)."""
    head = name[len('lane_'):].removesuffix('.jsonl').rpartition('_')[0]
    method, _, tag = head.rpartition('_')
    if method in CHROME_KEYS + NO_CHROME:
        return tag
    k = lane_key(name)
    return head[len(k):].lstrip('_') if k else head


def live_runs_text(live):
    """live_lane_files() grouped by run tag, newest run first: one line per run with its files and last change."""
    runs = {}
    for f, t in live:
        runs.setdefault(lane_run(f.name), []).append((f, t))
    return '\n'.join(f"  run {tag or '(no tag)'}: {len(fs)} file(s), last change "
                     f"{time.strftime('%H:%M:%S', time.localtime(fs[0][1]))}: " + ', '.join(f.name for f, _ in fs)
                     for tag, fs in runs.items())


def cmd_lanes(retry=False, force=False):
    """Write work/downloads/lanes.json for the chrome-lanes workflow: the papers waiting for a browser, one list per
    Chrome method (ROUTES), each in worklist order, entries [id, doi, free url]. Reads papers.tsv only; no network.
    Left out: a PDF already in papers/, interlibrary loan, no DOI (except J-STAGE free links), PMC website papers, and
    papers a Chrome agent saved or found no access/PDF for in the last 14 days (--retry takes those again). A paper
    whose try in the last 14 days ended in error or STOP comes last in its list.
    Writes nothing while a lane_*.jsonl changed in the last LIVE_MINUTES (a live run's later chunks would find a new
    list and halt every lane: '# ERROR lanes.json was rebuilt'); --force rebuilds anyway (every run listed has ended)."""
    live = live_lane_files()
    if live and not force:
        sys.exit(f'lanes: a Chrome-lanes run looks live: {len(live)} progress file(s) changed in the last {LIVE_MINUTES} '
                 'min, by run tag:\n' + live_runs_text(live)
                 + f'\n{LANES} NOT rewritten: a live run\'s later chunks would find a new list and halt every lane '
                 f'("# ERROR lanes.json was rebuilt"). Wait until no lane_*.jsonl changed for {LIVE_MINUTES} minutes; '
                 'or, only when every run listed has ended (its result came back; a tag you do not know may be another '
                 "chat's run), `python3 catlog.py lanes" + (' --retry' if retry else '') + ' --force`.')
    if live:
        print(f'lanes: --force over {len(live)} progress file(s) changed in the last {LIVE_MINUTES} min (a run still '
              'writing them halts at its next chunk):\n' + live_runs_text(live))
    from collections import Counter
    with Queue(write=False) as q:
        rows = dict(q.rows)
    tried, failed = set(), set()  # failed: a try in the last 14 days ended in error or STOP (listed last, below)
    for f in DL.glob('lane_*.jsonl'):
        if time.time() - f.stat().st_mtime < 14 * 86400:
            js = [j for j in map(progress_line, f.read_text(errors='replace').splitlines()) if j]
            tried |= set() if retry else {paper_id(j['id']) for j in js if j['result'] in ('saved', 'no_access', 'no_pdf')}
            failed |= {paper_id(j['id']) for j in js if j['result'] in ('error', 'STOP')}
    hosts, lists, skip = wiley_hosts(), {k: [] for k in CHROME_KEYS + NO_CHROME}, Counter()
    for p in priority([p for p, r in rows.items() if r['status'] in ('needs_browser',) + REDOWNLOAD]):
        r = rows[p]
        free = re.search(r'\bfree=(\S+?)(?:;|\s|$)', r.get('note', ''))
        key = chrome_lane(r, hosts)
        why = ('on disk' if (ROOT / 'papers' / f'{p}.pdf').exists() else 'interlibrary loan' if lane_of(r) in ILL_LANES
               else 'tried by a Chrome agent in the last 14 days' if p in tried
               else 'no DOI' if not r.get('doi') and not (key == 'jstage' and free)
               else 'PMC website (the user\'s lane)' if key is None else '')
        if why:
            skip[why] += 1
        else:
            lists[key].append([p, r.get('doi', ''), free[1] if free else ''])
    for k in lists:  # a paper whose last try failed goes last: in a method-A lane two empty clicks on the first paper
        lists[k].sort(key=lambda e: e[0] in failed)  # stop the lane (3 J-STAGE PDFs failed to load 10-16, led the list)
    out = {'_built': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
           '_note': 'python3 catlog.py lanes' + (' --retry' if retry else '') + ': papers.tsv needs_browser + re-downloads with '
                    'no papers/<id>.pdf, routed by DOI (catlog.ROUTES); no interlibrary loan, no PMC website papers'
                    + ('' if retry else ', none a Chrome agent tried in the last 14 days') + '; each list in worklist order '
                    '(papers whose try ended in error or STOP last); '
                    'entries [id, doi, free url]'} | lists
    LANES.parent.mkdir(parents=True, exist_ok=True)
    tmp = LANES.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(out))
    old = None
    if LANES.exists():  # kept (copied, then replaced: a reader never finds the file missing)
        (LANES.parent / 'old').mkdir(exist_ok=True)
        old = LANES.parent / 'old' / f"lanes_{time.strftime('%Y%m%d-%H%M')}.json"
        old = old.with_name(f"lanes_{time.strftime('%Y%m%d-%H%M%S')}.json") if old.exists() else old
        shutil.copy2(LANES, old)
    os.replace(tmp, LANES)
    print(f'{LANES}: {sum(map(len, lists.values()))} papers' + (f' (the previous list is kept as {old})' if old else ''))
    for k in CHROME_KEYS + NO_CHROME:
        print(f'  {k:<13}{len(lists[k]):>6}' + ('   no Chrome method' if k in NO_CHROME else ''))
    print('left out: ' + (', '.join(f'{n} {why}' for why, n in skip.most_common()) or 'none'))
    if any(e[0] in failed for es in lists.values() for e in es):
        print(f'put last in their lists (a Chrome try in the last 14 days ended in error or STOP): '
              f'{sum(e[0] in failed for es in lists.values() for e in es)}')
    sites = {}
    for k in CHROME_KEYS:
        for p, _, _ in lists[k]:
            for m in re.findall(r'\b(?:click|login)=([^\s;]+)', rows[p].get('note', '')):
                sites.setdefault(m, Counter())[k] += 1
    if sites:
        print('waiting for your clear (click=/login= in the note): ' + '; '.join(
            f"{s} {sum(c.values())} ({', '.join(f'{k} {n}' for k, n in c.most_common())})"
            for s, c in sorted(sites.items(), key=lambda x: -sum(x[1].values()))))
    if lists['other']:
        print('other, commonest DOI prefixes: ' + ', '.join(
            f'{d} {n}' for d, n in Counter(d.split('/')[0] for _, d, _ in lists['other']).most_common(10)))


def stop_site(j, lane, doi, hosts):
    """The site whose check stopped an agent: the line's host, else a host its detail names, else (Wiley) where the DOI
    or its journal went, else the lane's usual site; '' when unknown (the DOI went to another publisher)."""
    detail = str(j.get('detail') or '')
    h = str(j.get('host') or '') or next((x for x in HOST.findall(detail) if x.lower() != 'doi.org'), '')
    if not h and re.search(r'resolves to|non-\w+ host|not on \w|moved', detail, re.I):
        return ''
    h = h or (hosts.get(doi.lower(), '') or hosts.get(wiley_journal(doi), '') if lane in ('wiley', 'wiley_sub') else '') \
        or SITE.get(lane, '')
    u = urllib.parse.urlsplit(h if '//' in h else 'https://' + h)
    return f'https://{u.netloc.lower()}' if h and u.netloc else ''


def cmd_lanes_record(dry=False):
    """Turn Chrome agents' progress lines (work/downloads/lane_*.jsonl) into queue marks, so no later chat retries a
    paper blindly: no access on the campus network (the line's ip starts with CATLOG_CAMPUS_IP_PREFIX; lines without ip never count) in the
    springer (a 204 or a buy page) or sd lane -> lane=ill; a bot check (STOP) -> click=<site>. Everything else is printed only. Lines already
    recorded are counted in work/downloads/recorded.tsv (file<TAB>lines); --dry writes nothing."""
    from collections import Counter
    state_p = DL / 'recorded.tsv'
    done = {}
    for l in (state_p.read_text().splitlines() if state_p.exists() else []):
        f, _, n = l.partition('\t')
        if n.strip().isdigit():
            done[f] = int(n)
    with Queue(write=False) as q:
        rows = dict(q.rows)
    hosts, counts, seen, junk, new = wiley_hosts(), {}, Counter(), 0, 0
    ill, click, unmarked, nopdf, saved, errors, unknown_site, recheck = {}, {}, Counter(), {}, [], [], [], []
    for f in sorted(DL.glob('lane_*.jsonl')):
        lines = f.read_text(errors='replace').split('\n')[:-1]  # complete lines only: an agent may be writing the last one
        counts[f.name] = len(lines)
        lane, start = lane_key(f.name), done.get(f.name, 0) if done.get(f.name, 0) <= len(lines) else 0
        mdate, new = time.strftime('%Y-%m-%d', time.localtime(f.stat().st_mtime)), new + len(lines) - start
        for s in lines[start:]:
            j = progress_line(s)
            if not j:
                junk += bool(s.strip()); continue
            p, res, r = paper_id(j['id']), j['result'], rows.get(paper_id(j['id']))
            detail, date = ' '.join(str(j.get('detail') or '').split()), line_date(j.get('ts'), mdate)
            seen[res] += 1
            if r is None:
                unmarked[f'{res}, id not in the queue'] += 1; continue
            if res in ('saved', 'no_pdf', 'error') and not still_needed(r):
                continue  # filed, or got by another route meanwhile
            if res == 'saved':
                saved.append(p)
            elif res == 'no_pdf':
                nopdf.setdefault(detail[:80], {})[p] = 1
            elif res == 'error':
                errors.append(f'{p} ({lane}): {detail[:110]}')
            elif res == 'no_access':
                why = ('not a springer/sd lane' if lane not in ('springer', 'sd') else 'no ip in the line' if not j.get('ip')
                       else 'off campus' if not str(j['ip']).startswith(os.environ.get('CATLOG_CAMPUS_IP_PREFIX') or '-') else 'no longer waiting' if not still_needed(r)
                       else 'already lane=ill' if lane_of(r) == 'ill' else 'Springer answered a page, not 204'
                       if lane == 'springer' and not re.search(r'\b204\b|\bbuy|purchas|subscri', detail, re.I) else '')
                if why:  # Springer's 200 HTML came only for DOIs with letters (A:, BF): the URL's lower-case DOI, not a licence
                    unmarked[f'no_access, {why}'] += 1
                    if why.startswith('Springer'):
                        recheck.append(p)
                else:
                    ill[p] = f'no access on ISU campus via Chrome ({lane}: {detail[:50]}, {date})'
            elif res == 'STOP':
                site = stop_site(j, lane, (r or {}).get('doi', ''), hosts)
                if not site:
                    unknown_site.append(f'{p} ({lane}): {detail[:110]}')
                elif not still_needed(r) or f'click={site}' in r.get('note', ''):
                    unmarked['STOP, ' + ('no longer waiting' if not still_needed(r) else f'already click={site}')] += 1
                else:
                    click[p] = (site, f'Chrome agent stopped at a bot check ({lane}: {detail[:50]}, {date})')
    groups = {}  # one mark per identical (what, why), so papers.tsv is rewritten a few times, not once per paper
    for p, why in ill.items():
        groups.setdefault(('lane=ill', why), []).append(p)
    for p, (site, why) in click.items():
        if p not in ill:  # no licence on campus is the answer; a check on the way there no longer matters
            groups.setdefault((f'click={site}', why), []).append(p)
    print(f"lanes-record{' (dry run: nothing written)' if dry else ''}: {new} new lines in {len(counts)} files, {junk} junk; "
          + ', '.join(f'{k} {seen[k]}' for k in RESULTS))
    for (what, why), ps in groups.items():
        print(f"{'would mark' if dry else 'mark'} {what} ({len(ps)}): {','.join(ps[:12])}{' ...' if len(ps) > 12 else ''}  \"{why}\"")
        if not dry:
            cmd_mark(ps, what, why)
    if unmarked:
        print('not marked: ' + ', '.join(f'{n} {k}' for k, n in unmarked.most_common()))
    for x in unknown_site:
        print('STOP at an unknown site (printed only):', x)
    if recheck:
        print(f"Springer no_access not marked ill ({len(set(recheck))}; a page, not 204: the lower-case DOI URL; the springer "
              f"lane fetches the page's citation_pdf_url since 2026-10-16, so `lanes` lists them again after 14 days): "
              f"{','.join(dict.fromkeys(recheck))}")
    if nopdf:
        print('no_pdf by detail: ' + '; '.join(f"{d or '(no detail)'}: {len(ps)} ({','.join(list(ps)[:4])})"
                                               for d, ps in sorted(nopdf.items(), key=lambda x: -len(x[1]))[:15]))
    for x in errors[:20]:
        print('error:', x)
    if len(errors) > 20:
        print(f'... {len(errors) - 20} more errors')
    if saved:
        dl = Path.home() / 'Downloads'
        found = {}
        for d, label in ((dl, '~/Downloads'), (ROOT / 'papers' / 'rejected', 'papers/rejected')):
            for x in (d.iterdir() if d.exists() else ()):
                k = id_in_name(x.name) or (re.match(r'\d+(?=_|\.pdf$)', x.name) or [''])[0]  # not '10X ...xlsx'
                found.setdefault(k, []).append(f'{label}/{x.name}')
        for l in (BAD_FILES.read_text(errors='replace').splitlines() if BAD_FILES.exists() else []):
            g = l.split('\t')
            if len(g) > 2:
                found.setdefault(g[0], []).append(f'rejected_files.tsv: {g[2]}')
        print(f'saved by an agent but still not on disk: {len(set(saved))}')
        for p in dict.fromkeys(saved):
            print(f"  {p}: {'; '.join(found.get(p, [])[:3]) or 'not found (run python3 catlog.py file, or file 30)'}")
    if not dry:
        tmp = state_p.with_suffix('.tsv.tmp')
        tmp.write_text(''.join(f'{f}\t{n}\n' for f, n in sorted(counts.items())))
        os.replace(tmp, state_p)
        log('-', 'lanes_record', f'lines={new}', f'ill={sum(len(ps) for (x, _), ps in groups.items() if x == "lane=ill")}',
            f'click={sum(len(ps) for (x, _), ps in groups.items() if x != "lane=ill")}')


AUDIT_RATE = 0.07  # /audit re-checks this share of the values added since the last audit (the user, 2026-10-13: "random 7%")
AUDIT_DUE = 300    # values added since the last audit after which status says an audit is due


def audit_start(ev):
    """Index of the log event the current audit window starts after: the last `sample` an audit then recorded verdicts
    for, so values added while that audit was running stay in the next window (2026-10-18: batches added between a
    sample and its verdicts, 1,900 values, had fallen out of both). Before samples were logged: the last verdict."""
    verdicts = [i for i, f in enumerate(ev) if f[2].startswith('audit_')]
    samples = [i for i, f in enumerate(ev) if f[2] == 'sampled' and verdicts and i < verdicts[-1]]
    return samples[-1] if samples else (verdicts[-1] if verdicts else -1)


def values_since_audit(ev=None):
    """Values added (kept) since the current audit window started (audit_start), less those dropped since: the 2,255
    re-read copies of accepted values dropped on 2026-10-22 are not there to audit."""
    ev = events() if ev is None else ev
    start = audit_start(ev)
    kept = sum(kv(f, 'kept') for f in ev[start + 1:] if f[2] == 'add')
    gone = {f[3] for f in ev[start + 1:] if f[2] == 'drop' and len(f) > 3}
    if gone and REJECTED.exists():
        last, seen = ev[start][0] if start >= 0 else '', set()
        for line in open(REJECTED):
            if '"dropped"' in line and (rid := re.search(r'"row_id": "(\w+)"', line)) and rid.group(1) in gone:
                if (json.loads(line).get('added') or '') >= last:
                    seen.add(rid.group(1))
        kept -= len(seen)
    return max(0, kept)


def audit_size():
    """Rows the next /audit samples: 7% of the values added since the last audit, at least 12."""
    import math
    return max(12, math.ceil(AUDIT_RATE * values_since_audit()))


def cmd_sample(n):
    """n catalog rows not audited yet, as JSON, for the /audit command: first up to a third targeted rows (values a
    paper check of a database difference found wrong, work/audit_priority.txt; audit-record logs their verdicts
    targeted=dbcheck and audit_summary keeps them out of the audit rate), the rest random. Rows of the method paper's
    test set (locked(): read before the lock) are never sampled, so no audit of them can become a rule."""
    import random
    done = {l.split('\t')[3] for l in open(LOG) if '\taudit_' in l} if LOG.exists() else set()
    held = locked()
    rows = [r for r in (json.loads(l) for l in open(CATALOG) if l.strip()) if r['pmid'] not in held]
    from dbcheck import audit_first  # values a paper check of a database difference found wrong (dbcheck-record)
    first = audit_first(sys.modules[__name__])  # come first, even when an audit before that check kept them
    pool = [r for r in rows if r['row_id'] not in done and r['row_id'] not in first]  # the random part: never a targeted row
    ev = events()
    last = ev[audit_start(ev)][0] if audit_start(ev) >= 0 else ''
    fresh = [r for r in pool if (r.get('added') or '') >= last]
    log('-', 'sampled', f'rows={n}', f'fresh={len(fresh)}')
    pick = sorted((r for r in rows if r['row_id'] in first), key=lambda r: first[r['row_id']])[:max(1, n // 3) if n > 0 else 0]
    if pick:
        print(f'{len(pick)} targeted rows first (a database check found them wrong; not in the audit rate)', file=sys.stderr)
    k = n - len(pick)
    pick += random.sample(fresh, min(len(fresh), k * 2 // 3))  # of the random part two thirds newest, one third catalog-wide
    rest = [r for r in pool if r['row_id'] not in {p['row_id'] for p in pick}]
    pick += random.sample(rest, min(n - len(pick), len(rest)))
    keep = ('row_id', 'pmid', 'doi', 'title', 'enzyme', 'organism', 'variant', 'substrate', 'cosubstrate', 'metric', 'raw_value',
            'raw_unit', 'value', 'unit', 'pH', 'temperature_C', 'conditions', 'location', 'quote')
    rows = [{k: r.get(k) for k in keep} for r in pick]
    # The same rows on disk, so an audit can be started with row_ids alone (the auditors read the file):
    # catlog-audit takes args.groups instead of args.rows, and a launch no longer carries every row's text.
    (WORK / 'audit_rows_current.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(rows, ensure_ascii=False))
    ids = [r['row_id'] for r in rows]
    print('groups:', json.dumps([ids[i:i + 4] for i in range(0, len(ids), 4)]), file=sys.stderr)


TARGETED = 'targeted=dbcheck'  # last field of an audit_keep/audit_drop line for a row work/audit_priority.txt put first
FOLLOWUP = 'targeted=paper'  # last field of an audit line of a whole-paper follow-up (`audit-record --followup`): the
# rest of a paper's rows audited because a sample found a systematic error there
# Whole-paper and whole-table audits logged before FOLLOWUP existed, as (pmid, first minute, last minute): that paper's
# audit lines in the window are follow-ups (round 16b quality review: they held 50 of the 74 drops counted as the
# random audit's). Like targeted lines they stay out of the audit rate; their drops count among CatLog's own errors.
FOLLOWUP_AUDITS = (
    ('17462992', '2026-10-12 12:07', '2026-10-12 12:07'),  # unit check of 32 rows: "Shared cause for all 32 rows"
    ('19021757', '2026-10-12 12:07', '2026-10-12 12:07'),  # unit check of Table 5's 10 rows
    ('19001118', '2026-10-12 12:07', '2026-10-12 12:11'),  # unit check of the paper's rows (62 lines)
    ('23747922', '2026-10-12 12:11', '2026-10-12 14:27'),  # unit check of Table 1's 8 rows, twice
    ('21361343', '2026-10-13 02:03', '2026-10-13 02:04'),  # all 48 rows after a sample found partial constants
    ('12591933', '2026-10-14 15:58', '2026-10-14 16:00'),  # its rows after a sample found a reprinted column
)


def audit_targeted(f):
    """Whether a log.tsv audit line is outside the random audit: a targeted re-check (TARGETED) or a whole-paper
    follow-up (FOLLOWUP, or in a FOLLOWUP_AUDITS window)."""
    return f[-1] in (TARGETED, FOLLOWUP) or any(f[1] == p and a <= f[0][:16] <= b for p, a, b in FOLLOWUP_AUDITS)


def cmd_audited(rid, verdict, why, targeted=None):
    """Record an audit verdict; 'drop' also moves the row to rejected.jsonl. A row sample took from
    work/audit_priority.txt (targeted; worked out here when not given) gets TARGETED as the line's last field; a tag
    given as `targeted` (FOLLOWUP) is that field instead."""
    if targeted is None:
        from dbcheck import audit_first
        targeted = rid in audit_first(sys.modules[__name__])
    if verdict not in ('keep', 'drop'):
        sys.exit(f'audited: verdict must be keep or drop, not {verdict!r}')
    pmid = next((json.loads(l)['pmid'] for l in open(CATALOG) if f'"row_id": "{rid}"' in l), None)
    if pmid is None:
        sys.exit(f'audited: {rid} is not in catalog.jsonl')
    if verdict == 'drop':
        cmd_drop(rid, why)
    log(pmid, f'audit_{verdict}', rid, why, *([targeted if isinstance(targeted, str) else TARGETED] if targeted else []))


def cmd_audit_record(*paths):
    """Record the verdicts auditors wrote to work/audit_<row_id>.json (file-based, so a verdict never depends on how an
    agent worded its reply); each file is set aside in work/old/ once recorded. A keep already logged for that row with
    the same reason (recorded with `audited`, file left behind) is not logged again. A kept value that a paper check of a
    database difference had called wrong (work/audit_priority.txt) makes that difference open again: dbcheck.reask
    writes the paper's task file for the next batch (at most dbcheck.ASK_MAX checks per paper). `--followup`: the
    verdicts are a whole-paper follow-up (every other row of a paper where a sample found a systematic error); their
    lines end FOLLOWUP and stay out of the audit rate."""
    from dbcheck import audit_first, reask, PRIORITY
    followup = '--followup' in paths
    paths = [x for x in paths if x != '--followup']
    first = audit_first(sys.modules[__name__])
    logged = set()
    if LOG.exists():
        for l in open(LOG):
            f = l.rstrip('\n').split('\t')
            if len(f) > 4 and f[2] == 'audit_keep':
                logged.add((f[3], f[4]))
    for p in map(Path, paths):
        try:
            data = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError) as e:
            print(f'{p.name}: unreadable ({e}); not recorded'); continue
        verdicts = data.get('verdicts') if isinstance(data, dict) else None
        if not isinstance(verdicts, list):  # e.g. a saved `sample` list that matched work/audit_*.json
            print(f'{p.name}: not a verdict file (no "verdicts" list); left as it is'); continue
        done, keep_file = 0, False
        for v in verdicts:
            if isinstance(v, dict) and v.get('verdict') in ('keep', 'drop') and v.get('row_id'):
                try:
                    why = str(v.get('reason') or '')
                    if v['verdict'] == 'keep' and (str(v['row_id']), ' '.join(why.split())) in logged:
                        print(f'{p.name}: {v["row_id"]} keep recorded already'); done += 1; continue
                    fix = re.match(r'unit_fix:\s*(.*)', why, re.S) if v['verdict'] == 'drop' else None
                    if fix:  # a unit the paper shows is misprinted: corrected, not dropped
                        ufc, rest = audit_unit(str(v['row_id']), fix.group(1))
                        if str(v['row_id']) not in (cmd_unitfix(ufc, rest.strip(' ;:-.') or why, str(v['row_id'])) if ufc else set()):
                            print(f'{p.name}: {v["row_id"]} unit_fix not applied ({fix.group(1)[:60]!r}): not recorded, file kept')
                            keep_file = True; continue
                        log(next((json.loads(l)['pmid'] for l in open(CATALOG) if f'"row_id": "{v["row_id"]}"' in l), '-'),
                            'audit_keep', str(v['row_id']), f'unit corrected: {why}',
                            *([FOLLOWUP] if followup else [TARGETED] if str(v['row_id']) in first else []))
                    else:
                        cmd_audited(str(v['row_id']), v['verdict'], why, FOLLOWUP if followup else str(v['row_id']) in first)
                    done += 1
                except SystemExit as e:  # the row left the catalog (recorded already, or a wrong id): say so, go on
                    print(f'{p.name}: {e}')
            else:
                print(f'{p.name}: not recorded (needs row_id and verdict keep or drop): {json.dumps(v)[:120]}')
        if keep_file:  # recorded verdicts are skipped next time (keeps by reason; drops left the catalog)
            print(f'{p.name}: {done} of {len(verdicts)} verdicts recorded; left in place for the unit fix'); continue
        (WORK / 'old').mkdir(exist_ok=True)
        shutil.move(str(p), str(WORK / 'old' / f'{p.stem}.{int(time.time())}.json'))
        print(f'{p.name}: {done} of {len(verdicts)} verdicts recorded')
    audited = set(first) - set(audit_first(sys.modules[__name__]))
    kept = audited & set(audit_marks())  # audited since and still in the catalog
    if kept:
        reask(sys.modules[__name__], {r['pmid'] for r in csv.DictReader(open(WORK / PRIORITY, encoding='utf-8'), delimiter='\t')
                                      if r.get('row_id') in kept and r.get('pmid')},
              'an audit kept a value a paper check had called wrong')


def audit_unit(rid, text):
    """The unit an auditor's 'unit_fix: <unit> <evidence>' names, as the shortest leading words the units code accepts for
    that row ('10^-6 M^-1 s^-1 -- Table 3 ...' gives '10^-6 M^-1 s^-1'; the first word alone, '10^-6', is no unit:
    4 rows of 21094652 were logged corrected but left unchanged on 2026-10-23), and the rest as evidence."""
    row = next((json.loads(l) for f in (CATALOG, REJECTED) for l in open(f) if f'"row_id": "{rid}"' in l), None)
    words = text.split()
    for k in range(1, min(6, len(words)) + 1):
        ufc = ' '.join(words[:k]).rstrip('.,;:')
        if row and not normalize(row.get('metric', ''), row.get('raw_value', ''), ufc)[2]:
            return ufc, ' '.join(words[k:])
    return None, text


def cmd_unitfix(ufc, why, *ids):
    """Correct the unit code converted a printed value with, when the paper itself shows the printed unit is a misprint
    (another table prints the same cell in the right unit, or a block of the column's kcat/Km closes only in that
    unit): the fix an audit needs instead of a drop. raw_value and raw_unit stay as printed; unit_for_conversion is
    set, code converts again and check() must pass. A row still in the catalog is changed in place (same row_id); a
    row an audit dropped comes back, and so does a verified row code rejected only for the physical limit (2026-11-05:
    a misprinted header puts a whole column 10^3-10^6 above it, 18621017). The evidence goes into verify_note; log.tsv
    says 'unitfix', or 'recover' for a row brought back (status counts it)."""
    ids = set(ids)
    with catalog_lock():
        lines = [l for l in open(CATALOG) if l.strip()]
        rows = {json.loads(l)['row_id']: i for i, l in enumerate(lines) if any(f'"row_id": "{x}"' in l for x in ids)}
        back = {}
        for l in open(REJECTED):
            if any(f'"row_id": "{x}"' in l for x in ids):
                r = json.loads(l)
                if r['row_id'] not in rows and (any(str(w).startswith('audit:') for w in r.get('why', []))
                                                or r.get('why') == ['beyond_physical_limit']):
                    back[r['row_id']] = r  # the latest audit drop (or limit reject) of that row
        texts, fixed, recovered = {}, [], {}
        for rid in sorted(ids):
            r = json.loads(lines[rows[rid]]) if rid in rows else back.get(rid)
            if r is None:
                print(f'{rid}: neither in the catalog nor dropped by an audit'); continue
            if censored_kind(r):  # a censored value has no unit to correct, and never enters catalog.jsonl
                print(f'{rid}: a censored value (bounds.jsonl), not a value: nothing to correct'); continue
            if rid not in rows and (rid, r.get('dropped')) in label_drops(strict=True):  # its label is known to be wrong
                print(f'{rid}: dropped for its organism label (sources/organism_label_drops.tsv): read the paper again instead'); continue
            if rid not in rows:  # a later read may already hold the cell (21306440, 2026-11-05: its Km came back twice)
                cells = {}
                for l in lines:
                    if f'"pmid": "{r["pmid"]}"' in l:
                        o = json.loads(l)
                        cells.setdefault(printed_cell(o), []).append(o)
                held = twin(r, cells)
                if held:
                    print(f"{rid}: not brought back, the catalog already holds this cell as {held['row_id']}"); continue
            r = {k: v for k, v in r.items() if k not in ('why', 'dropped')}
            r['unit_for_conversion'] = ufc
            if r['pmid'] not in texts:
                texts[r['pmid']] = squash(paper_text(r['pmid']))
            norm, bad = check(r, texts[r['pmid']])
            if set(bad) <= {'quote_not_in_paper', 'value_not_in_quote', 'marker_not_in_quote'} and r.get('quote_check'):
                bad = []
            if bad:
                print(f'{rid}: not changed, the check fails with {ufc}: {"; ".join(bad)}'); continue
            r.update(norm)
            r['verify_note'] = f'unit corrected to {ufc} ({now()}): {why}' + (f"; {r['verify_note']}" if r.get('verify_note') else '')
            r['checked'] = now()
            if rid in rows:
                lines[rows[rid]] = json.dumps(r, ensure_ascii=False) + '\n'
                fixed.append(r)
            else:
                if not r.get('added'):  # a limit reject was never stored: it enters the catalog now (an audit drop keeps its own)
                    r['added'] = r['checked']
                lines.append(json.dumps(r, ensure_ascii=False) + '\n')
                recovered.setdefault(r['pmid'], []).append(r)
            print(f"{rid}: {r['metric']} {r['raw_value']} {r['raw_unit']} -> {r['value']:.4g} {r['unit']}"
                  + ('' if rid in rows else ' (back from an audit drop or a limit reject)'))
        tmp = CATALOG.with_suffix(f'.jsonl.{os.getpid()}.tmp')
        tmp.write_text(''.join(lines))
        os.replace(tmp, CATALOG)
        for r in fixed:
            log(r['pmid'], 'unitfix', r['row_id'], ufc, why)
        for pmid, rs in recovered.items():
            log(pmid, 'recover', f'kept={len(rs)}', 'dup=0', 'rejected=0', 'still_rejected=0', 'reason=unitfix', why)
    return {r['row_id'] for r in fixed} | {r['row_id'] for rs in recovered.values() for r in rs}


def cmd_restore(why, *ids):
    """Bring back a value an audit dropped when a review against the paper shows the auditor was wrong and the stored
    value right as it stands (unitfix is the same for a misprinted unit). 41835576 on 2026-10-19: Table 1's header says
    kcat | KM but its cells sit in swapped columns (the prose, the table's own median and mean rows and Table S1's
    Vmax/[E] all show it); one auditor read the header and dropped a correct kcat, another kept its sibling. check()
    must still pass. log.tsv: 'recover' (status counts it) and an audit_keep that supersedes the drop, as 19001118."""
    ids = set(ids)
    with catalog_lock():
        lines = [l for l in open(CATALOG) if l.strip()]
        have = {x for x in ids if any(f'"row_id": "{x}"' in l for l in lines)}
        back = {}
        for l in open(REJECTED):
            if any(f'"row_id": "{x}"' in l for x in ids - have):
                r = json.loads(l)
                if any(str(w).startswith('audit:') for w in r.get('why', [])):
                    back[r['row_id']] = r  # the latest audit drop of that row
        restored = []
        for rid in sorted(ids):
            r = back.get(rid)
            if r is None:
                print(f'{rid}: {"still in the catalog" if rid in have else "not dropped by an audit"}'); continue
            if censored_kind(r):  # it would land in catalog.jsonl as a value; a censored value comes back through a re-read
                print(f'{rid}: a censored value: not restored into the catalog (re-read the paper instead)'); continue
            if (rid, r.get('dropped')) in label_drops(strict=True):  # its label is known to be wrong: a re-read brings it back
                print(f'{rid}: dropped for its organism label (sources/organism_label_drops.tsv): read the paper again instead'); continue
            cells = {}  # a later read may already hold the cell, e.g. relabelled (organism_relabelled), as unitfix checks
            for l in lines:
                if f'"pmid": "{r["pmid"]}"' in l:
                    o = json.loads(l)
                    cells.setdefault(printed_cell(o), []).append(o)
            held = twin(r, cells)
            if held:
                print(f"{rid}: not restored, the catalog already holds this cell as {held['row_id']} "
                      f"({held.get('organism') or 'no organism'}, {held.get('enzyme') or 'no enzyme'})"); continue
            r = {k: v for k, v in r.items() if k not in ('why', 'dropped')}
            norm, bad = check(r, squash(paper_text(r['pmid'])))
            if set(bad) <= {'quote_not_in_paper', 'value_not_in_quote', 'marker_not_in_quote'} and r.get('quote_check'):
                bad = []
            if bad:
                print(f'{rid}: not restored, the check fails: {"; ".join(bad)}'); continue
            r.update(norm)
            r['verify_note'] = f'restored after review ({now()}): {why}' + (f"; {r['verify_note']}" if r.get('verify_note') else '')
            r['checked'] = now()
            lines.append(json.dumps(r, ensure_ascii=False) + '\n')
            restored.append(r)
            print(f"{rid}: {r['metric']} {r['raw_value']} {r['raw_unit']} back from an audit drop")
        tmp = CATALOG.with_suffix(f'.jsonl.{os.getpid()}.tmp')
        tmp.write_text(''.join(lines))
        os.replace(tmp, CATALOG)
        for r in restored:
            log(r['pmid'], 'recover', 'kept=1', 'dup=0', 'rejected=0', 'still_rejected=0', 'reason=restore', why)
            log(r['pmid'], 'audit_keep', r['row_id'], f'kept on review: {why}; supersedes the audit drop')


def audit_marks():
    """row_id -> (date, 'kept' or 'unit corrected') for every value an AI audit re-checked against its paper and kept:
    audit verdicts only (log.tsv audit_keep), 'unit corrected' only when the audit_keep reason says so (cmd_audit_record);
    a unitfix from a sweep is not an audit. The latest verdict counts; a dropped value left the catalog."""
    out = {}
    for f in events():
        if f[2] == 'audit_keep' and len(f) > 3:
            out[f[3]] = (f[0][:10], 'unit corrected' if ' '.join(f[4:]).startswith('unit corrected') else 'kept')
        elif f[2] == 'audit_drop' and len(f) > 3:
            out.pop(f[3], None)
    return out


_PRESENT = {}


def rows_present(ids):
    """The ones of `ids` that are row_ids in catalog.jsonl: streamed, never the whole file in memory, and kept per
    version of the file (status and a site build ask several times)."""
    if not CATALOG.exists() or not ids:
        return set()
    st = CATALOG.stat()
    key = (str(CATALOG), st.st_mtime_ns, st.st_size)
    if key not in _PRESENT:
        _PRESENT.clear()
        _PRESENT[key] = ({}, set())
    seen, have = _PRESENT[key]
    want = {i for i in ids if i not in seen}
    if want:
        rid = re.compile(rb'"row_id": "([0-9a-f]{16})"')
        with open(CATALOG, 'rb') as fh:
            for line in fh:
                m = rid.search(line)
                if m and m.group(1).decode() in want:
                    have.add(m.group(1).decode())
        seen.update({i: True for i in want})
    return {i for i in ids if i in have}


def relabelled_drops(evs=None):
    """{dropped row_id: pmid} for the drops whose value came back under a corrected organism label (log `relabelled
    <dropped> <new>`, organism_relabelled), following a second correction (the returned row dropped and relabelled
    again) to a row not dropped since: label corrections, not values removed (the user, 2026-11-15, 18620421's 88).
    audit_summary counts such an audit drop as corrected, human_review.catlog_errors under label_fix."""
    evs = events() if evs is None else evs
    hexid = re.compile(r'[0-9a-f]{16}')
    back = {f[3]: (f[4], f[1]) for f in evs if f[2] == 'relabelled' and len(f) >= 7  # the latest return of each drop
            and hexid.fullmatch(f[3]) and hexid.fullmatch(f[4])}
    if not back:
        return {}
    present = rows_present({n for n, _ in back.values()})
    out = {}
    for d, (n, pmid) in back.items():
        seen = {d}
        while n not in present and n in back and n not in seen:  # its returned row was dropped and relabelled again
            seen.add(n)
            n = back[n][0]
        if n in present:
            out[d] = pmid
    return out


def audit_summary(targeted=False, split=False):
    """(values audited, wrong ones dropped, units the audits corrected), each counted once per row_id by its latest
    verdict, as audit_marks (a keep that supersedes an audit drop, 19001118 on 2026-10-12, is not a wrong value).
    A value dropped for its organism label and back under the right one (relabelled_drops) is a label correction, not
    a wrong value (the user, 2026-11-15): left out of wrong, and counted only with split=True, (audited, wrong, units
    corrected, labels corrected). The rate is the random audit's: a row only targeted audits saw (audit_targeted:
    values a database check found wrong, whole-paper follow-ups) is left out; a row a random audit sampled counts by
    its latest verdict, targeted or not. targeted=True: the same numbers for the rows only targeted audits saw."""
    last, sampled = {}, set()
    evs = events()
    for f in evs:
        if f[2] in ('audit_keep', 'audit_drop') and len(f) > 3:
            last[f[3]] = (f[2], ' '.join(f[4:]))
            if not audit_targeted(f):
                sampled.add(f[3])
    last = {k: v for k, v in last.items() if (k in sampled) != targeted}
    labels = set(relabelled_drops(evs))
    units = sum(e == 'audit_keep' and why.startswith('unit corrected') for e, why in last.values())
    relabelled = sum(e == 'audit_drop' and k in labels for k, (e, _) in last.items())
    wrong = sum(e == 'audit_drop' for e, _ in last.values()) - relabelled
    return (len(last), wrong, units, relabelled) if split else (len(last), wrong, units)


def cmd_drop(rid, why):
    """Move one catalog row to rejected.jsonl (an audit refuted it). The only way rows leave the catalog.
    `drop --file F`: every row_id<TAB>why line of F in one rewrite (a sweep that drops hundreds of rows)."""
    if rid == '--file':
        reasons = dict(l.rstrip('\n').split('\t', 1) for l in open(why) if '\t' in l)
    else:
        reasons = {rid: why}
    with catalog_lock(), open(CATALOG, 'r+') as cat:
        rows = [json.loads(l) for l in cat if l.strip()]
        gone = [r for r in rows if r['row_id'] in reasons]
        brows = [json.loads(l) for l in open(BOUNDS) if l.strip()] if BOUNDS.exists() else []
        bgone = [r for r in brows if r['row_id'] in reasons]  # a censored value (bounds.jsonl) leaves the same way
        missing = sorted(set(reasons) - {r['row_id'] for r in gone + bgone})
        if missing:
            sys.exit(f"{', '.join(missing[:10])}: not in catalog (nothing dropped)")
        for path, keep, lost in ((CATALOG, rows, gone), (BOUNDS, brows, bgone)):
            if not lost:
                continue
            tmp = path.with_suffix('.jsonl.tmp')
            with open(tmp, 'w') as out:
                for r in keep:
                    if r['row_id'] not in reasons:
                        out.write(json.dumps(r, ensure_ascii=False) + '\n')
            os.replace(tmp, path)
        with open(REJECTED, 'a') as rej:  # every row with this id (older rows of two preparations could share one)
            for r in gone + bgone:
                rej.write(json.dumps({**r, 'why': [f"audit: {reasons[r['row_id']]}"], 'dropped': now()}, ensure_ascii=False) + '\n')
        for r in gone:  # one log line per row (inside the lock), so status's file check stays exact
            log(r['pmid'], 'drop', r['row_id'], reasons[r['row_id']])
        for r in bgone:
            log(r['pmid'], 'drop_bound', r['row_id'], reasons[r['row_id']])
    for k in reasons:
        print(f'{k} moved to rejected.jsonl')


def cmd_show(pmid, which=''):
    """Print each extracted row with the value code will store, so the verifier can check the conversion."""
    read = json.loads((WORK / f'{pmid}{which}.read.json').read_text())
    for i, r in enumerate(read.get('rows', [])):
        cens = censored_kind(r)
        if cens:  # a censored value: stored apart (bounds.jsonl), with its limit in catalog units when one converts
            b, bu, why = bound_of(r, cens)
            stored = f"censored {cens}" + (f', limit {b:.4g} {bu}' if b is not None else f' ({why})' if why else ', no limit printed')
        else:
            v, u, err = normalize(r.get('metric', ''), r.get('raw_value', ''), r.get('unit_for_conversion') or r.get('raw_unit', ''))
            stored = err or f'{v:.4g} {u}'
        print(f"[{i}] {r.get('variant', '')} | {r.get('substrate', '')} | {r.get('metric', '')} = "
              f"{r.get('raw_value', '')} {r.get('raw_unit', '')}  ->  stored as {stored}")


# ---------- more ----------

def cmd_more(n=200, km=False):
    """Append unseen PMIDs from the source lists in config.json, in list order. Papers to read after every other paper
    (later(): the Km-only list) wait until no other paper is left to read (todo, outside the held-out test set), so
    papers.tsv does not carry ~94k of them for months.
    `more --km N` (the chat that reads the Km-only list, the user 2026-11-09): the N unqueued Km-only papers whose free
    full text prints the most Km numbers (tools/km_gain.py: `fulltext` set, expected_values above 0), whatever else
    is left. They stay later() papers, so every other order still reads them last."""
    added, late, waiting = 0, later(), 0
    if km:
        best = []
        for src in sorted((ROOT / 'sources').glob('discovered_km_*.tsv')):
            best += [(-int(r['expected_values']), r['pmid']) for r in csv.DictReader(open(src), delimiter='\t')
                     if r.get('fulltext') and (r.get('expected_values') or '').isdigit() and int(r['expected_values']) > 0]
        with Queue() as q:
            held = locked()
            for _, pmid in sorted(best):
                if added >= n:
                    break
                if pmid not in q.rows and pmid not in held:
                    q.set(pmid, status='todo', note='from discovered_km (most Km numbers first)'); added += 1
        log('-', 'more', f'added={added} km')
        print(f'added {added} Km-only papers (most Km numbers in their free full text first)')
        return
    with Queue() as q:
        held = locked()
        others_left = any(r['status'] == 'todo' and p not in late and p not in held for p, r in q.rows.items())
        for src in CONFIG['sources']:
            p = ROOT / src
            if not p.exists():
                continue
            for pmid in (x.strip() for x in p.read_text().splitlines()):
                if not (pmid.isdigit() or is_standin(pmid)):
                    continue
                if added >= n:
                    break
                if pmid not in q.rows:
                    if pmid in late and others_left:
                        waiting += 1; continue
                    q.set(pmid, status='todo', note=f'from {p.name}'); added += 1
    log('-', 'more', f'added={added}' + (f' later_waiting={waiting}' if waiting else ''))
    print(f'added {added} papers' + (f'; {waiting:,} Km-only papers wait until nothing else is left to read' if waiting else ''))


# ---------- enrich + export ----------

_NATURAL = None
_IMPLAUSIBLE = None
TAIL = 1e6  # mM^-1 s^-1 = 1e9 M^-1 s^-1: the diffusion ceiling's neighbourhood, where every value gets a review line
TAIL_NOTE = {'implausible_as_printed': 'physically implausible as printed: ',
             'paper_claims_super_diffusion': "the paper's own claim, above the diffusion limit: ",
             'near_limit_as_printed': 'near the diffusion limit as printed: '}


def implausible(row_ids):
    """The review line of sources/implausible_as_printed.tsv for a measurement, matched by any of its row_ids (a
    printed kcat/Km by its own row, a derived one by its kcat row), or None. Each line is a kcat/Km at the diffusion
    ceiling or above that was checked against its paper: on 2026-10-22/23 none of 103 was a CatLog misread, so the
    values stay as printed and carry the reason (work/top_journal_20261021/verify/catlog_tail.md)."""
    global _IMPLAUSIBLE
    if _IMPLAUSIBLE is None:
        p = ROOT / 'sources' / 'implausible_as_printed.tsv'
        lines = [l for l in open(p, encoding='utf-8') if not l.startswith('#')] if p.exists() else []
        _IMPLAUSIBLE = {x['row_id']: x for x in csv.DictReader(lines, delimiter='\t')}
    return next((_IMPLAUSIBLE[r] for r in row_ids if r in _IMPLAUSIBLE), None)


def natural_form(r):
    """The reviewed natural form (isozyme, paralog, allele, strain ortholog) from sources/natural_forms.tsv, or None. It
    is the enzyme's identity, not a mutation (the user, 2026-10-10). A line names the form either in `variant`, as the
    readers of 2026-10-10 wrote it (`_by` 'variant': identity() then moves it into the enzyme name and makes the row
    wild type), or in `enzyme` for a row that already follows the current convention (the form in `enzyme`, variant wild
    type; `_by` 'enzyme': only the sequence guard uses it, the row is shown as the reader wrote it)."""
    global _NATURAL
    if _NATURAL is None:
        p = ROOT / 'sources' / 'natural_forms.tsv'
        lines = [l for l in open(p) if not l.startswith('#')] if p.exists() else []
        _NATURAL = {}
        for x in csv.DictReader(lines, delimiter='\t'):
            if (x.get('variant') or '').strip():
                _NATURAL[(x['pmid'], 'variant', squash(x['variant']))] = {**x, '_by': 'variant'}
            if (x.get('enzyme') or '').strip():
                _NATURAL[(x['pmid'], 'enzyme', squash(x['enzyme']))] = {**x, '_by': 'enzyme'}
    pmid = str(r.get('pmid', ''))
    return (_NATURAL.get((pmid, 'variant', squash(r.get('variant') or ''))) or
            _NATURAL.get((pmid, 'enzyme', squash(r.get('enzyme') or ''))))


def identity(r):
    """The row as the protein lookup and the export see it. A natural form written in `variant` joins the enzyme name,
    is the gene when it looks like one, brings its printed IDs, and the variant is wild type: each form is looked up as
    its own protein (AmPDH2 by its printed AY753308 -> Q3L243)."""
    f = natural_form(r)
    if not f or f.get('_by') == 'enzyme':
        return r  # named in `enzyme`: the reader already wrote the form as the identity, with variant wild type
    from enrich import ACC
    v, name, enzyme = r.get('variant') or '', f['isoform_name'] or r.get('variant') or '', r.get('enzyme') or ''
    if re.sub(r'\W', '', v.lower()) not in re.sub(r'\W', '', enzyme.lower()):
        enzyme = f'{enzyme} {v}'.strip()
    printed = [x.strip() for x in f['printed_ids'].split(';') if x.strip()]
    acc = next((x for x in printed if ACC.match(x.split('-')[0])), '')
    return {**r, 'enzyme': enzyme, 'variant': 'wild type', 'uniprot': acc or r.get('uniprot', ''),
            'gene': name if re.fullmatch(r'[\w.*-]{2,15}', name) else r.get('gene', ''),
            'protein_ids': ', '.join(x for x in printed if x != acc) or r.get('protein_ids', '')}


def ident_key(r):
    r = identity(r)
    return '|'.join(str(r.get(k, '')).strip().lower() for k in ('uniprot', 'protein_ids', 'gene', 'enzyme', 'organism'))


def substrate_key(r):
    return (r.get('substrate_full_name') or r.get('substrate') or '').strip().lower()


def clean_ec(text):
    """An EC number as the paper printed it, in the standard form: 'EC1.1.3.10' and 'EC 1.1.3.10' -> '1.1.3.10'
    (39915905: the export's ec_number kept the prefix, so the site's EC filter missed its records), an incomplete one
    '3.4.11' or '1.14.13.x' -> '3.4.11.-' / '1.14.13.-'; several -> '; '-joined. Provisional numbers stay as printed
    ('3.5.1.n3', BRENDA's '1.1.1.B47'); text that is no EC number is kept unchanged."""
    out = []
    for t in re.split(r'[;,/]|\s+and\s+', str(text or '')):
        t = re.sub(r'^\s*(?:E\.?\s*C\.?)\s*:?\s*', '', t.strip(), flags=re.I).strip()
        m = re.fullmatch(r'(\d+)((?:\.(?:\d+|[nB]\d+|-|x|X|\*))*)', t)
        if not m:
            if t:
                out.append(t)
            continue
        parts = [m.group(1)] + [p if p not in ('x', 'X', '*') else '-' for p in m.group(2).split('.')[1:]]
        out.append('.'.join(parts + ['-'] * (4 - len(parts))) if len(parts) < 4 else '.'.join(parts))
    return '; '.join(dict.fromkeys(out))


def cmd_enrich():
    """UniProt accession + sequence and substrate SMILES for every catalog row (cached, so reruns are cheap)."""
    from enrich import Cache
    from sequences import find_protein, sequence, split_variant, variant_sequence, save as save_lookups
    from structures import find_smiles, same_paper_names, provisional, _refused
    lock = open(ROOT / 'enrich' / '.lock', 'w')
    fcntl.flock(lock, fcntl.LOCK_EX)  # held until this process ends: another chat's enrich waits, then sees our entries
    ids, sm = Cache(ROOT / 'enrich' / 'protein.json'), Cache(ROOT / 'enrich' / 'structures.json')
    new_id = new_sm = failed = 0
    for line in open(CATALOG):
        if not line.strip():
            continue
        r = json.loads(line)
        before = new_id + new_sm
        try:
            r = {**r, 'ec': clean_ec(r.get('ec'))}  # 'EC1.1.3.10' finds nothing on the EC route
            if ident_key(r) not in ids:
                got = find_protein(identity(r))
                if natural_form(r) and not (got.get('acc') or got.get('seq_ref')):  # the form's own name found nothing:
                    plain = find_protein(r)  # the enzyme as written (OASS-A, PMID 8518286); export checks it is not shared
                    if plain.get('acc') or plain.get('seq_ref'):
                        got = {**plain, 'how': f"{plain['how']} (looked up without the form's name; under it: {got['how'][:80]})"}
                ids[ident_key(r)] = got; new_id += 1
        except (RuntimeError, ValueError):
            failed += 1  # network trouble or an odd answer: not cached, retried next run
        if new_id + new_sm != before and (new_id + new_sm) % 25 == 0:
            ids.save(); sm.save()
    ids.save(); sm.save()
    from enrich import uniprot_ec, pick_by_mutations
    from sequences import unshare_cited
    muts, paper = {}, {}
    for line in open(CATALOG):
        if not line.strip():
            continue
        r = json.loads(line)
        muts.setdefault(ident_key(r), []).extend(split_variant(r.get('variant'))[1])
        paper.setdefault(r['pmid'], set()).add(ident_key(r))
    unshare_cited(ids, paper)  # a structure the paper solved is not its sibling enzymes' entry (10652317: GSTM1 got GSTM2)
    for k, v in ids.items():  # several candidates: let the paper's own mutations decide
        if not v.get('acc') and v.get('candidates') and k in muts:
            try:
                acc = pick_by_mutations(v['candidates'], muts[k], ROOT / 'enrich' / 'seq')
            except (RuntimeError, ValueError):
                acc = None; failed += 1  # a candidate's sequence could not be fetched: decide next run
            if acc:
                v.update(acc=acc, seq_ref=acc, how=f"{v['how']}; chosen: the only candidate whose sequence has every wild-type residue the paper's mutations name")
    for v in ids.values():
        try:
            if v.get('seq_ref'):
                sequence(v['seq_ref'])
            if v.get('acc') and 'ec' not in v:
                v['ec'] = uniprot_ec(v['acc'])
        except (RuntimeError, ValueError):
            failed += 1
    ids.save()
    # substrate structures, keyed by paper + name (abbreviations are paper-local); needs EC and accession first
    subs = {}
    for line in open(CATALOG):
        if not line.strip():
            continue
        r = json.loads(line)
        if substrate_key(r):
            subs.setdefault(f"{r['pmid']}|{substrate_key(r)}", []).append(r)
    printed = {}  # every substrate and co-substrate name each paper's rows print: a database name that is one of them is
    for group in subs.values():  # another compound of the paper, not this one (structures.find_smiles)
        for x in group:
            printed.setdefault(x['pmid'], set()).update(
                n for n in [x.get('substrate'), x.get('substrate_full_name')] + re.split(r'\s*(?:\+|;)\s*', x.get('cosubstrate') or '') if n)
    for k, group in subs.items():
        if k in sm and not provisional(sm[k]):  # provisional: OPSIN's answer while PubChem refused, asked again
            continue
        if ident_key(group[0]) not in ids:
            continue  # its protein lookup failed this run: wait, so the Rhea route can use the accession next run
        r, idr = group[0], ids.get(ident_key(group[0]), {})
        try:
            db = same_paper_names(r['pmid'], r.get('substrate'), [(x['metric'], molar(x)) for x in group if molar(x)],
                                  ROOT / 'sources' / 'db_values.tsv')
            sm[k] = find_smiles([r.get('substrate_full_name'), r.get('substrate')], ec=r.get('ec') or idr.get('ec', ''),
                                uniprot=idr.get('acc', ''), pmid=r['pmid'], db_rows=db, paper_names=printed.get(r['pmid'], ()))
            new_sm += 1
        except (RuntimeError, ValueError):
            failed += 1  # network/OPSIN trouble or an odd answer: not cached, retried next run
    sm.save()
    pm, rows = {}, [json.loads(l) for l in open(CATALOG) if l.strip()]  # fetch numbering frames now, so export runs offline
    for r in rows:
        ref = ids.get(ident_key(r), {}).get('seq_ref')
        if ref:
            pm.setdefault((r['pmid'], ref), []).extend(split_variant(r.get('variant'))[1])
    for r in rows:
        v = ids.get(ident_key(r), {})
        if v.get('seq_ref'):
            try:
                variant_sequence(v['seq_ref'], r.get('variant'), r['pmid'], pm[(r['pmid'], v['seq_ref'])], v.get('pdb', []))
            except (RuntimeError, ValueError, OSError, EOFError, SyntaxError):  # SyntaxError: a cut-off SIFTS XML
                failed += 1
    save_lookups()
    found = sum(1 for v in ids.values() if v.get('acc'))
    smiles = sum(1 for v in sm.values() if v.get('smiles'))
    waiting = len({ident_key(r) for r in rows} - set(ids)) + sum(1 for k in subs if k not in sm or provisional(sm[k]))
    refused = ','.join(sorted(_refused)) or '-'  # status shows these: they wait for the next enrich, not for a person
    log('-', 'enrich', f'enzymes={len(ids)} with_uniprot={found}', f'substrates={len(sm)} with_smiles={smiles}',
        f'waiting={waiting}', f'refused={refused}')
    why = f'{refused} refused (rate limit)' if _refused else 'network trouble'
    print(f'enzymes: {found}/{len(ids)} have a UniProt entry; substrates: {smiles}/{len(sm)} have SMILES '
          f'(looked up now: {new_id} enzymes, {new_sm} substrates)' + (
              f'; {failed} lookups failed, {waiting} entries waiting ({why}): the next export or enrich asks again'
              if failed or waiting else ''))


def isnum(x):
    try:
        float(x); return True
    except (TypeError, ValueError):
        return False


def close(a, b):
    return abs(a - b) <= 0.02 * max(a, b) or f'{a:.2g}' == f'{b:.2g}'


def db_check(pmid, metric, value, db):
    """Compare a verified value with what the databases of sources/db_values.tsv (dbcompare.SOURCES) list for the same
    paper and metric."""
    vals = db.get((pmid, metric), [])
    if value is None:
        return ''
    if not vals:
        return 'no database value for this paper'
    hits = sorted({src for src, v in vals if close(v, value)})
    if hits:
        return 'same number in ' + ', '.join(hits) + ' for this paper (substrate/variant not compared)'
    return f"number not in {', '.join(sorted({src for src, _ in vals}))} for this paper ({len(vals)} values listed)"


AA = {'Ala': 'A', 'Arg': 'R', 'Asn': 'N', 'Asp': 'D', 'Cys': 'C', 'Gln': 'Q', 'Glu': 'E', 'Gly': 'G', 'His': 'H', 'Ile': 'I',
      'Leu': 'L', 'Lys': 'K', 'Met': 'M', 'Phe': 'F', 'Pro': 'P', 'Ser': 'S', 'Thr': 'T', 'Trp': 'W', 'Tyr': 'Y', 'Val': 'V'}
CONSTRUCT_WORDS = re.compile(r'truncat|\bNt\d+\b|\bCt\d+\b|ΔN|ΔC|Δ\s*[12]\s*[-–]\s*\d|catalytic domain|'
                             r'(?:construct|comprising|spanning|consisting of|expressed|fragment|domain|lacking|without|deleted|deletion of|removal of)'
                             r'\W{0,25}residues?\s+\d+\s*[-–]\s*\d+|residues?\s+\d+\s*[-–]\s*\d+\W{0,10}(?:(?:were|was)\s+)?(?:expressed|construct|fragment|domain)'
                             r'|lacking the (?:first|N-terminal|C-terminal)|signal peptide removed|mature form', re.I)
NOT_THIS_PROTEIN = re.compile(r'coupl|auxiliary|excess|helper enzyme|reporter', re.I)  # another enzyme's construct
# in the reader's own `construct` field a clause that starts with the span is the construct ('core domain of ttRecJ,
# residues 40-463', 'residues 1-305, C-terminal His6-tag', 'mature CpdB, amino acids 20-647'; PMIDs 21087930, 18275836)
SPAN_CLAUSE = re.compile(r'(?:^|[,;(]\s*)(?:full-length\s*\(?\s*)?(?:residues?|amino acids?)\s+(\d+)\s*[-\u2013]\s*(\d+)', re.I)
CHIMERA = re.compile(r'chim|replaced (?:by|with)|swapp|hybrid', re.I)  # another protein's segments: no UniProt span


def construct_spec(row):
    """The measured construct as the paper states it: the reader's `construct` field, or for older rows the one
    variant/conditions segment that states it (never a coupled/auxiliary enzyme's). None when no truncation is
    described, else {'text', 'start', 'end', 'res'} in the paper's numbering; start/end None = stated but not readable."""
    if (row.get('construct') or '').strip():
        seg = row['construct'].strip()
        if CHIMERA.search(seg) and re.search(r'\d', seg):
            return {'text': seg, 'start': None, 'end': None, 'res': ''}
        m = SPAN_CLAUSE.search(seg)
        if m and not CONSTRUCT_WORDS.search(seg):
            return {'text': seg, 'start': int(m.group(1)), 'end': int(m.group(2)), 'res': ''}
        segs = [seg]
    else:
        segs = [x.strip() for x in ' ; '.join(x for x in (row.get('variant'), row.get('conditions')) if x).split(';')]
    segs = [x for x in segs if CONSTRUCT_WORDS.search(x) and not NOT_THIS_PROTEIN.search(x)]
    if not segs:
        return None
    segs.sort(key=lambda x: 0 if re.search(r'construct|truncat|expressed|domain', x, re.I) else 1)
    seg = segs[0]
    spec = {'text': seg, 'start': None, 'end': None, 'res': ''}
    aa = '|'.join(AA)
    d = re.search(r'(?:lacking|without|deleted|deletion of|removal of|Δ)\W{0,10}(?:residues?\s+)?(\d+)\s*[-–]\s*(\d+)', seg, re.I)
    if d:  # a deleted range: N-terminal deletions set the start; an internal one is not a span we can trim
        if int(d.group(1)) in (1, 2):
            spec['start'] = int(d.group(2)) + 1
        return spec
    m = re.search(r'residues?\s+(\d+)\s*[-–]\s*(\d+)', seg, re.I)
    if m:
        spec.update(start=int(m.group(1)), end=int(m.group(2)))
        return spec
    for m in re.finditer(r'truncated\s+(?:at|to|before|from)\s+(' + aa + r'|[A-Z])\s?-?(\d+)', seg):
        if re.search(r'C-?\s*terminal(?:ly)?\s*$', seg[max(0, m.start() - 25):m.start()], re.I):
            spec['end'] = int(m.group(2))
        else:
            spec.update(start=int(m.group(2)), res=AA.get(m.group(1), m.group(1)))
    m2 = re.search(r'\bNt(\d+)\b', seg)
    if m2 and spec['start'] is None:
        spec['start'] = int(m2.group(1))
    m3 = re.search(r'lacking the (?:first|N-terminal) (\d+) (?:residues|amino acids)', seg)
    if m3 and spec['start'] is None:
        spec['start'] = int(m3.group(1)) + 1
    m4 = re.search(r'C-?\s*terminal(?:ly)?\s+truncated\s+(?:at|after)\s+(?:' + aa + r'|[A-Z])?\s?-?(\d+)', seg)
    if m4:
        spec['end'] = int(m4.group(1))
    m5 = re.search(r'\bfrom (?:residue|amino acid|position)\s+(' + aa + r'|[A-Z])?\s?-?(\d+)', seg, re.I)  # 'mature chain from residue 19'
    if m5 and spec['start'] is None:
        spec.update(start=int(m5.group(2)), res=AA.get(m5.group(1), m5.group(1)) if m5.group(1) else '')
    return spec


# A construct the paper states without its signal peptide ('VPL2 without its signal peptide', 'mature protein without
# native signal peptide'): 1,250 records of 109 papers kept the full UniProt sequence, signal included (2026-10-24,
# found on 22566208). A start residue the paper prints is used (printed_span); else UniProt's own Signal (or Transit
# peptide) span is removed, and a Propeptide right after it when the paper removed that too; no such span in UniProt
# leaves the sequence blank with the reason.
SIGNAL_GONE = re.compile(r'(?:without|lacking|minus|devoid of|removal of|deleted|deletion of|replacing|in place of|instead of)'
                         r'\W{0,15}(?:(?:its|the|native|predicted|putative|N-terminal|natural|own|endogenous|secretory|\w+)\s+){0,3}'
                         r'(?:signal|leader|transit|targeting) (?:peptide|sequence)|(?:signal|leader|transit|targeting) (?:peptide|sequence)s? '
                         r'(?:was |were |had been |is |are )?(?:removed|deleted|replaced|cleaved off|omitted|excluded)', re.I)
UNIPROT_ACC = re.compile(r'(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})(?:-\d+)?')
PRO_GONE = re.compile(r'(?:without|lacking|minus|removal of|deleted|deletion of)\W{0,30}(?:[\w-]+\s+){0,4}pro-?(?:peptide|segment|region|sequence)'
                      r'|pro-?(?:peptide|segment|region|sequence)s? (?:was |were |had been )?(?:removed|deleted|cleaved)', re.I)


def printed_span(text):
    """The residues a construct stated without its signal peptide prints for itself: 'residues Gln30-Glu546', 'residues
    T43-Q388', 'N-terminus Val-59', 'lacking N-terminal 27 residues' -> {'start', 'end', 'res'} (res: the printed start
    residue, checked against UniProt by apply_construct), else None. Read before UniProt's own signal span is used."""
    aa = '|'.join(AA)
    one = lambda x: AA.get(x[:1].upper() + x[1:].lower(), x) if x else ''
    if len(re.findall(r'residues?\s+(?:' + aa + r'|[A-Z])-?\d+\s*[-\u2013]|N-terminus\s+(?:is\s+|at\s+)?(?:' + aa + r'|[A-Z])-?\d+|'
                      r'lacking (?:the )?(?:first|N-terminal) \d+ (?:residues|amino acids)', text)) > 1:
        return None  # one per subunit ('alpha lacking N-terminal 27 residues, beta ... 34'): which is this one's is not said
    m = re.search(r'residues?\s+(' + aa + r'|[A-Z])-?(\d+)\s*[-\u2013]\s*(?:' + aa + r'|[A-Z])-?(\d+)', text)
    if m:
        return {'start': int(m.group(2)), 'end': int(m.group(3)), 'res': one(m.group(1))}
    m = re.search(r'N-terminus\s+(?:is\s+|at\s+)?(' + aa + r'|[A-Z])-?(\d+)', text)
    if m:
        return {'start': int(m.group(2)), 'end': None, 'res': one(m.group(1))}
    m = re.search(r'lacking (?:the )?(?:first|N-terminal) (\d+) (?:residues|amino acids)', text)
    if m:
        return {'start': int(m.group(1)) + 1, 'end': None, 'res': ''}
    return None


def signal_span(acc, text):
    """(last residue to remove, what it is) for a construct stated without its signal peptide (SIGNAL_GONE): UniProt's
    Signal feature starting at residue 1, plus the Propeptide that follows it when the paper removed that too
    (PRO_GONE). (None, why) when UniProt marks no such span or the entry cannot be read."""
    from sequences import entry
    try:
        feats = entry(acc.split('-')[0]).get('features') or []
    except RuntimeError:
        return None, f'UniProt {acc} could not be read'
    sig = [f for f in feats if f[0] in ('Signal', 'Transit peptide') and f[1] == 1 and f[2]]  # a leader, by UniProt's name
    if not sig:
        return None, f'UniProt {acc} marks no signal or transit peptide'
    end, label = sig[0][2], f'{sig[0][0].lower().replace("signal", "signal peptide")} 1-{sig[0][2]}'
    if PRO_GONE.search(text):
        pro = [f for f in feats if f[0] == 'Propeptide' and f[1] == end + 1 and f[2]]
        if not pro:
            return None, f'the paper removed a propeptide too, and UniProt {acc} marks none after its signal peptide 1-{end}'
        end, label = pro[0][2], label + f' and propeptide {end + 1}-{pro[0][2]}'
    return end, label


def apply_construct(full, canonical, spec, frame, dels):
    """(sequence, basis) for the measured construct. Positions are the paper's; they are used only when the paper's
    numbering is UniProt's (canonical frame), and the printed start residue must match. Otherwise fail closed."""
    if spec is None:  # the frame names the source: 'UniProt canonical', 'NCBI AAF43045.1 sequence', 'UniParc UPI... sequence'
        src = 'UniProt canonical sequence' if frame in ('UniProt canonical', '') else frame
        return full, f'{src} (paper describes no truncated construct)' if full else ''
    if not full:
        return '', ''
    if spec.get('signal_why'):
        return '', f'unresolved: paper states the signal peptide was removed ("{spec["text"][:100]}"); {spec["signal_why"]}'
    if spec['start'] is None and spec['end'] is None:
        return '', f'unresolved: paper states a construct ("{spec["text"][:120]}") whose residue span could not be read'
    if frame != 'UniProt canonical':
        return '', f'unresolved: construct "{spec["text"][:80]}" is in the paper\'s numbering, which is not UniProt\'s here ({frame})'
    start, end = spec['start'] or 1, spec['end'] or len(canonical)
    if not (0 < start <= end <= len(canonical)) or (spec['res'] and canonical[start - 1] != spec['res']):
        return '', f'unresolved: construct "{spec["text"][:80]}" does not fit UniProt (residue {start} is {canonical[start - 1] if 0 < start <= len(canonical) else "-"})'
    gone = lambda p: sum(e - s + 1 for s, e, *_ in dels if e < p)  # residues deleted before position p
    if any(s <= start <= e or s <= end <= e for s, e, *_ in dels):
        return '', f'unresolved: construct boundary falls inside a deletion'
    seq = full[start - 1 - gone(start): end - gone(end + 1)]
    inside = [f'\u0394{s_}-{e_}' for s_, e_, *_ in dels if start <= s_ and e_ <= end]
    return seq, (f'measured construct: UniProt residues {start}-{end}' + (f' minus {", ".join(inside)}' if inside else '') +
                 (f", after UniProt's {spec['signal']}" if spec.get('signal') else '') +
                 f' ({len(seq)} aa; paper: "{spec["text"][:100]}")')


_strenda_prot = None


def deposited_protein(pmid, acc, organism):
    """(sequence, note) the paper's authors deposited in STRENDA DB for this protein, matched by UniProt or organism."""
    global _strenda_prot
    if _strenda_prot is None:
        _strenda_prot = {}
        p = ROOT / 'sources' / 'strenda_proteins.tsv'
        if p.exists():
            for r in csv.DictReader(open(p), delimiter='\t'):
                _strenda_prot.setdefault(r['pmid'], []).append(r)
    rows = _strenda_prot.get(str(pmid), [])
    hits = [r for r in rows if acc and r['uniprot'] == acc] or \
           [r for r in rows if organism and r['organism'].split()[:2] == organism.split()[:2]]
    seqs = {r['sequence'] for r in hits if r['sequence']}
    if len(seqs) != 1:
        return '', (f'{len(seqs)} different deposited sequences in STRENDA for this paper; not chosen' if len(seqs) > 1 else '')
    r = hits[0]
    return seqs.pop(), f"STRENDA {r['srn']}: sequence deposited by the authors ({r['protein_name'][:60]}; expressed in {r['expression_system'][:40]})"


UNIT_FIXED = re.compile(r'(?:^|; )unit corrected to (.+?) \((\d{4}-\d{2}-\d{2}) \d{2}:\d{2}\): ')  # cmd_unitfix's verify_note
CELL_FIXED = re.compile(r"(?:^|; )printed cell corrected from (?:'([^']*)' to '([^']*)'|(.+?) to (.+?)) "
                        r"\((\d{4}-\d{2}-\d{2}) \d{2}:\d{2}\): ")  # cmd_cellfix's (unquoted before 2026-11-03 10:00)


def cell_fixes(r):
    """cmd_cellfix's corrections in a row's verify_note, latest first: (misread cell, the page image's cell, date)."""
    return [(m.group(1) if m.group(1) is not None else m.group(3), m.group(2) if m.group(2) is not None else m.group(4),
             m.group(5)) for m in CELL_FIXED.finditer(r.get('verify_note') or '')]


@lru_cache(maxsize=1)
def ever_dropped():
    """row_ids an audit (or `drop`) once moved to rejected.jsonl: one still in the catalog was restored."""
    return frozenset(r.get('row_id') for r in audit_dropped())


def value_note(r):
    """A value's own note for the export. cmd_unitfix and cmd_cellfix record a correction in verify_note only, so a note
    that explained the earlier reading would stand beside the corrected value as if it still held (40723313: 'kcat
    column of Table 2 stored x10^-3' beside 3.35 s^-1, fixed back to the printed unit on 2026-11-02): the note then
    leads with the correction (2026-11-03), whose bracket says the note predates it. The note's own '; ' segments stay
    as they were, so the website still reads a leading qualifier ('apparent') from them."""
    note = r.get('metric_note') or ''
    unit, cell = UNIT_FIXED.search(r.get('verify_note') or ''), cell_fixes(r)
    heads = ([f'printed cell corrected {cell[0][2]} (was read as {cell[0][0]}'] if cell else []) + (
        [f"{'restored by a unit fix' if r.get('row_id') in ever_dropped() else 'unit corrected'} {unit.group(2)} "
         f"({'read' if r.get('row_id') in ever_dropped() else 'now read'} as {unit.group(1)}"] if unit else [])
    if not heads:
        return note
    heads = [h + ')' for h in heads[:-1]] + [heads[-1] + ('; the note that follows predates it)' if note else ')')]
    return '; '.join(heads + ([note] if note else []))


def evidence_of(r):
    """The export's evidence fields for one value. A cell cmd_cellfix corrected before it set quote_check (3624267, the
    first) is read on the page image too: its quote is the text layer's line, which prints the misread cell."""
    out = {f: r.get(f, '') for f in ('row_id', 'raw_value', 'raw_unit', 'unit_for_conversion', 'location', 'quote', 'quote_check')}
    fixes = cell_fixes(r)
    if fixes and not out['quote_check']:
        out['quote_check'] = f"the page image prints {fixes[0][1]}; the reader had read {fixes[0][0]} (cellfix {fixes[0][2]})"
    return out


def wide(part, ids, sm, paired, muts=None, db=None, forms=None):
    """One measurement (kcat, Km, kcat/Km side by side) in the old catalog's field names."""
    from enrich import parse_variant, binomial
    from sequences import variant_sequence, construct
    base = part[0]
    nf, who = natural_form(base), identity(base)  # a natural form in `variant` is the enzyme's identity: wild type
    m = {r['metric']: r for r in part}
    idr = ids.get(ident_key(base), {'acc': '', 'how': 'not enriched yet'})
    ref = idr.get('seq_ref', '')
    try:
        vs = variant_sequence(ref, who.get('variant'), base['pmid'], (muts or {}).get((base['pmid'], ref), []), idr.get('pdb', []))
        cons = construct(idr['acc'], idr['pdb'])['note'] if idr.get('acc') and idr.get('pdb') else ''
    except RuntimeError:  # offline: export still works, the sequence comes on a later run
        vs, cons = {'sequence': '', 'check': 'not enriched yet (lookup failed)', 'frame': ''}, ''
    from sequences import split_variant, sequence as canon_seq
    spec = construct_spec(base)
    stated = (base.get('construct') or '').strip()
    # only when the signal peptide is all the paper left unnumbered: not beside an unreadable truncation
    unread = spec is not None and spec['start'] is None and spec['end'] is None and \
        CONSTRUCT_WORDS.search(re.sub(r'signal peptide removed|mature form', '', stated, flags=re.I))
    if ref and UNIPROT_ACC.fullmatch(ref) and SIGNAL_GONE.search(stated) and (spec is None or (spec['start'] is None and not unread)):
        own = printed_span(stated)  # a start residue the paper prints wins over UniProt's signal span
        if own:
            spec = {**(spec or {'text': stated}), **own, 'end': own['end'] or (spec or {}).get('end')}
        else:
            end, label = signal_span(ref, stated)  # the paper says the signal peptide is gone and names no residue
            spec = {**(spec or {'text': stated, 'end': None, 'res': ''}), 'start': end + 1 if end else None,
                    **({'signal': label} if end else {'signal_why': label})}
    try:
        canonical = canon_seq(ref) if ref else ''
    except RuntimeError:
        canonical = ''
    seq, basis = apply_construct(vs['sequence'], canonical, spec, vs['frame'], split_variant(who.get('variant'))[2])
    if nf and seq:  # the entry must be this form's own: not shared with another form, not an allele that differs from it
        mine = idr.get('acc') or ref
        label = base.get('enzyme') if nf.get('_by') == 'enzyme' else base['variant']
        same = sorted(v for v, x in (forms or {}).get(base['pmid'], {}).items() if v != label and (x.get('acc') or x.get('seq_ref')) == mine)
        why = (nf['sequence_note'] and f"{label} {nf['sequence_note']}" or
               same and f"{label} and {', '.join(same)} share UniProt {mine}: which sequence is which is not known" or
               idr.get('how', '').startswith('EC + organism') and len((forms or {}).get(base['pmid'], {})) > 1 and
               f"UniProt {mine} was found by EC number only and the paper has several forms" or '')
        if why:
            seq, basis = '', f'unresolved: natural form {why}'
    seq_check = vs['check']
    # shared assay conditions = segments every value of the measurement carries; the rest are per-value notes
    segs = {k: condition_parts(r.get('conditions')) for k, r in m.items()}
    common = set.intersection(*({x.lower() for x in v[0]} for v in segs.values()))
    common_q = set.intersection(*({x.lower() for x in v[1]} for v in segs.values())) if len(m) > 1 else set()
    shared = [x for x in condition_parts(base.get('conditions'))[0] if x.lower() in common]
    shared += [x for x in condition_parts(base.get('conditions'))[1] if x.lower() in common_q]  # e.g. a table of apparent values
    metric_notes = {k: '; '.join(x for x in [*(q for q in v[1] if q.lower() not in common_q),
                                              *(y for y in v[0] if y.lower() not in common), value_note(m[k]),
                                              m[k].get('condition_note', '')] if x)
                    for k, v in segs.items()}
    if all(x in m for x in METRICS) and ratio_note(m):  # kept as printed; the reader of the value is told
        metric_notes['kcat/Km'] = '; '.join(x for x in (metric_notes.get('kcat/Km', ''), ratio_note(m)) if x)
    wt = parse_variant(who.get('variant'))[0]
    s = sm.get(f"{base['pmid']}|{substrate_key(base)}", {'smiles': '', 'how': 'not enriched yet'})
    kcat, km = m.get('kcat', {}).get('value'), molar(m.get('Km', {}))
    eff = molar(m.get('kcat/Km', {}))
    eff_src = 'printed' if eff is not None else ''
    mass = {k: m[k]['value'] for k in ('Km', 'kcat/Km') if k in m and molar(m[k]) is None}  # their own columns
    if eff is None and paired and kcat and km:
        eff, eff_src = float(f'{kcat / km:.6g}'), 'derived: kcat / Km of this measurement'
        if eff > LIMITS['kcat/Km']:  # the limit check() holds a printed kcat/Km to (2026-10-22: 47 derived above it, 41 in 11779198)
            eff_src += '; above the physical limit'
            metric_notes['kcat/Km'] = '; '.join(x for x in (metric_notes.get('kcat/Km', ''), (
                f"kcat ÷ Km = {eff:.3g} mM^-1 s^-1, above the diffusion limit ({LIMITS['kcat/Km']:.0e} mM^-1 s^-1) a printed "
                'kcat/Km is held to: the kcat or Km as printed is implausible')) if x)
    tail = implausible([r['row_id'] for r in m.values()]) if eff and eff >= TAIL else None
    if tail and tail.get('flag') in TAIL_NOTE:  # a reviewed value at the ceiling: kept as printed, with its reason
        metric_notes['kcat/Km'] = '; '.join(x for x in (metric_notes.get('kcat/Km', ''),
                                                       TAIL_NOTE[tail['flag']] + tail['reason']) if x)
    t = base.get('temperature_C')
    mid = hashlib.sha1('|'.join(str(x).strip().lower() for x in (
        base['pmid'], idr.get('acc') or f"{base.get('enzyme')}|{base.get('organism')}", base.get('variant'),
        base.get('substrate'), base.get('cosubstrate'), base.get('pH'), t, '; '.join(shared), base.get('location'),
        *([construct_of(base)] if construct_of(base) else []))).encode()).hexdigest()[:16]
    ec = clean_ec(base.get('ec'))  # as printed, in the standard form
    ec, ec_src = ec, 'paper' if ec else ''
    if not ec and idr.get('ec'):
        ec, ec_src = clean_ec(idr['ec']), f"UniProt {idr['acc']}"
    b = db or {}
    return {
        'measurement_id': mid,
        'pubmed_id': base['pmid'], 'doi': base.get('doi', ''), 'title': base.get('title', ''),
        'ec_number': ec, 'ec_source': ec_src, 'enzyme_name': who.get('enzyme', ''), 'gene': base.get('gene', ''),
        'organism': binomial(base.get('organism', '')), 'strain': base.get('strain', ''),  # 'human' -> Homo sapiens (ids keep the printed word)
        'uniprot_id': idr.get('acc', ''), 'uniprot_how': idr.get('how', ''), 'uniprot_candidates': idr.get('candidates', []),
        'wild_type': wt, 'mutation_signature': None if wt else base.get('variant', ''),
        'sequence': seq, 'sequence_basis': basis, 'sequence_check': seq_check, 'sequence_frame': vs['frame'],
        'sequence_source': idr.get('seq_how', ''), 'sequence_construct': cons,
        'construct': spec['text'] if spec else '', 'preparation': base.get('construct', ''), 'uniprot_sequence': vs['sequence'],
        **dict(zip(('deposited_sequence', 'deposited_sequence_note'), deposited_protein(base['pmid'], idr.get('acc', ''), base.get('organism', '')))),
        'substrate_name': base.get('substrate', ''), 'substrate_full_name': base.get('substrate_full_name', ''),
        'smiles': s.get('smiles', ''), 'smiles_id': s.get('id', ''), 'smiles_how': s.get('how', ''), 'cosubstrate': base.get('cosubstrate', ''),
        'kcat': kcat, 'kcat_unit': 's^(-1)', 'km': km, 'km_unit': 'mM',
        'kcat_over_km': eff, 'kcat_over_km_unit': 's^(-1)*mM^(-1)', 'kcat_over_km_source': eff_src,
        'km_mg_per_ml': mass.get('Km'), 'km_mg_per_ml_unit': 'mg/mL',
        'kcat_over_km_ml_per_mg_s': mass.get('kcat/Km'), 'kcat_over_km_ml_per_mg_s_unit': 'mL*mg^(-1)*s^(-1)',
        'kcat_err': printed_err(m['kcat']['raw_value'], kcat, m['kcat']) if 'kcat' in m else None,
        'km_err': printed_err(m['Km']['raw_value'], km, m['Km']) if 'Km' in m and km is not None else None,
        'kcat_over_km_err': printed_err(m['kcat/Km']['raw_value'], eff, m['kcat/Km']) if eff_src == 'printed' else None,
        'ph': base.get('pH'), 'temperature_c': t, 'temperature_k': round(float(t) + 273.15, 2) if isnum(t) else None,
        'conditions': '; '.join(shared), 'metric_notes': {k: v for k, v in metric_notes.items() if v},
        'kcat_note': metric_notes.get('kcat', ''), 'km_note': metric_notes.get('Km', ''),
        'kcat_over_km_note': metric_notes.get('kcat/Km', ''),
        'kcat_over_km_flag': tail['flag'] if tail else '',
        'evidence': {k: evidence_of(r) for k, r in m.items()},
        'reasoning': {k: {'read': r.get('reasoning', ''), 'verify': r.get('verify_note', ''),
                          **({'corrected': r['corrected']} if r.get('corrected') else {})} for k, r in m.items()},
        # reader/verifier model, prompt hashes, code commit per value: stamped by add since 2026-10-21, reconstructed before
        'provenance': provenance(m),
        'db_check': {k: db_check(base['pmid'], k, molar(r), b) if molar(r) is not None else
                     'not compared: printed over a mass concentration' for k, r in m.items()},
        'ratio_check': ratio_check(m)[1] if all(x in m for x in METRICS) else '',
        'paired': paired, 'row_ids': [r['row_id'] for r in part],
    }


FLAT = ['measurement_id', 'pubmed_id', 'doi', 'ec_number', 'enzyme_name', 'organism', 'uniprot_id', 'uniprot_how', 'wild_type',
        'mutation_signature', 'sequence_basis', 'sequence_check', 'sequence_frame', 'construct', 'sequence_construct', 'substrate_name', 'smiles', 'smiles_id', 'cosubstrate', 'kcat', 'km',
        'kcat_over_km', 'kcat_over_km_source', 'kcat_err', 'km_err', 'kcat_over_km_err', 'km_mg_per_ml', 'kcat_over_km_ml_per_mg_s',
        'ph', 'temperature_c', 'conditions', 'kcat_note', 'km_note', 'kcat_over_km_note',
        'substrate_chebi', 'substrate_inchikey', 'substrate_pubchem_cid', 'taxon_id', 'organism_source',
        'kcat_bound', 'km_bound', 'kcat_over_km_bound', *STAMP, 'provenance_how', 'sequence']
# catlog_bounds.csv: one censored value per line (bounds.jsonl), with the record it joined (measurement_id) if any
BOUND_FLAT = ['row_id', 'measurement_id', 'pubmed_id', 'doi', 'enzyme_name', 'ec_number', 'organism', 'uniprot_id', 'variant', 'construct',
              'substrate_name', 'cosubstrate', 'metric', 'censored', 'bound', 'bound_unit', 'bound_note', 'raw_value', 'raw_unit',
              'limit', 'ph', 'temperature_c', 'conditions', 'metric_note', 'location', 'quote', *STAMP, 'provenance_how']
BOUND_COL = {'kcat': 'kcat_bound', 'Km': 'km_bound', 'kcat/Km': 'kcat_over_km_bound'}
STD_UNIT = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}


def bound_text(b):
    """A censored value as a record shows it: '<0.01', '>50', 'not_detected', 'not_detected (<0.001)', in catalog units
    (a mass-concentration limit names its unit); a limit that did not convert shows the printed cell."""
    lim = b.get('bound')
    unit = '' if b.get('unit') in (None, STD_UNIT[b['metric']]) else f" {b.get('unit')}"
    if b.get('censored') == 'not_detected':
        return 'not_detected' + (f' (<{lim:.4g}{unit})' if lim is not None else '')
    return f"{b['censored']}{lim:.4g}{unit}" if lim is not None else f"{b['censored']} (as printed: {b.get('raw_value', '')} {b.get('raw_unit', '')})".rstrip()


def enzyme_core(r):
    """An enzyme name without brackets and filler words ('HisA protein (E. coli)' = 'HisA'), for telling a reworded copy
    of one enzyme from another enzyme ('ADH1' is not 'ADH1A')."""
    return re.sub(r'[^a-z0-9]|\b(?:protein|enzyme|the|recombinant|native|purified)\b', '',
                  re.sub(r'\([^()]*\)', '', squash(r.get('enzyme', ''))))


def attach_bounds(out, groups, bounds):
    """Each censored value joins the one record of its paper it fits as measurements() pairs values: the same identity,
    construct and gene, one's assay segments within the other's, its metric not already there; two censored values of one
    metric for one record, or a value that fits several records, join none. Sets kcat_bound / km_bound /
    kcat_over_km_bound and bound_row_ids on every record (never the numeric columns), clears a kcat/Km derived from kcat ÷ Km
    where the paper prints that kcat/Km as a bound, and returns {row_id: measurement_id or ''} for catlog_bounds."""
    num = lambda v: f'{float(v):g}' if isnum(v) else str(v if v is not None else '').strip().lower()  # 25 = 25.0
    key = lambda r: tuple(num(r.get(k)) if k in ('pH', 'temperature_C') else str(r.get(k, '')).strip().lower() for k in IDENT) \
        + (construct_of(r), gene_of(r))
    segs = lambda rows: frozenset(x.lower() for r in rows for x in condition_parts(r.get('conditions'))[0])
    by, papers = {}, {}
    for i, g in groups.items():
        by.setdefault(key(g[0]), []).append(i)
        papers.setdefault(g[0]['pmid'], []).append(i)
    joined = {}
    for b in bounds:
        s_ = segs([b])
        near = [i for i in by.get(key(b), []) if s_ <= segs(groups[i]) or segs(groups[i]) <= s_]
        fits = [i for i in near if b['metric'] not in {r['metric'] for r in groups[i]}]
        clash = [i for i in near if b['metric'] in {r['metric'] for r in groups[i]}]
        joined[b['row_id']] = fits[0] if len(fits) == 1 and not clash else None  # as measurements(): no ambiguous pairing
        if not near:  # a pass for censored values only words the assay its own way ('spectrophotometric hydrolysis assay'
            # for 'spectrophotometric, complete hydrolysis time courses', 17207608): the same printed table line, enzyme,
            # variant, substrate, pH and temperature, and a record whose slot for this metric is empty, is that record
            line = squash(b.get('quote', ''))
            same = lambda r: (squash(r.get('quote', '')) == line and enzyme_core(r) == enzyme_core(b) and same_variant(r, b)
                              and squash(r.get('substrate', '')) == squash(b.get('substrate', ''))
                              and all(num(r.get(k)) == num(b.get(k)) for k in ('pH', 'temperature_C')))
            cand = [i for i in papers.get(b['pmid'], []) if any(same(r) for r in groups[i])]
            if len(cand) == 1 and b['metric'] not in {r['metric'] for r in groups[cand[0]]} and line:
                joined[b['row_id']] = cand[0]
    per = {}
    for b in bounds:
        if joined[b['row_id']] is not None:
            per.setdefault((joined[b['row_id']], b['metric']), []).append(b['row_id'])
    for ids_ in per.values():
        if len(ids_) > 1:
            for x in ids_:
                joined[x] = None
    for w in out:
        w.update({c: '' for c in BOUND_COL.values()}, bound_row_ids=[])
    for b in bounds:
        i = joined[b['row_id']]
        if i is not None:
            out[i][BOUND_COL[b['metric']]] = bound_text(b)
            out[i]['bound_row_ids'].append(b['row_id'])
    for w in out:  # the paper prints kcat/Km only as a bound or not detected: no kcat ÷ Km beside it (the user, 2026-10-27;
        # 10390216 aztreonam: kcat 13.2 s^-1 and Km 400 µM gave 33 mM^-1 s^-1 beside the printed '<0.02 µM^-1 s^-1')
        if w['kcat_over_km_bound'] and str(w.get('kcat_over_km_source') or '').startswith('derived'):
            w.update(kcat_over_km=None, kcat_over_km_source='', kcat_over_km_note='', kcat_over_km_flag='')
            w['metric_notes'].pop('kcat/Km', None)  # a derived kcat/Km's only notes are about the derived number
    return {b['row_id']: out[joined[b['row_id']]]['measurement_id'] if joined[b['row_id']] is not None else '' for b in bounds}


def bound_record(b, mid, ids, doi, ec=''):
    """One line of catlog_bounds.jsonl / .csv (organism as the record shows it: the binomial for 'human', 'rat', ...;
    ec_number: the paper's own EC for it, else the one its record or its enzyme's records of the paper carry)."""
    from enrich import binomial
    who = identity(b)
    t = b.get('temperature_C')
    return {'row_id': b['row_id'], 'measurement_id': mid, 'pubmed_id': b['pmid'], 'doi': b.get('doi') or doi.get(b['pmid'], ''),
            'title': b.get('title', ''), 'enzyme_name': who.get('enzyme', ''), 'ec_number': clean_ec(b.get('ec')) or ec,
            'organism': binomial(who.get('organism', '')),
            'uniprot_id': ids.get(ident_key(b), {}).get('acc', ''), 'variant': who.get('variant', ''),
            'construct': b.get('construct', ''), 'substrate_name': b.get('substrate', ''),
            'substrate_full_name': b.get('substrate_full_name', ''), 'cosubstrate': b.get('cosubstrate', ''),
            'metric': b['metric'], 'censored': b['censored'], 'bound': b.get('bound'), 'bound_unit': b.get('unit') or '',
            'bound_note': b.get('bound_note', ''), 'raw_value': b.get('raw_value', ''), 'raw_unit': b.get('raw_unit', ''),
            'limit': b.get('limit', ''), 'ph': b.get('pH'), 'temperature_c': t, 'conditions': b.get('conditions', ''),
            'metric_note': b.get('metric_note', ''), 'location': b.get('location', ''), 'quote': b.get('quote', ''),
            'reasoning': {'read': b.get('reasoning', ''), 'verify': b.get('verify_note', ''),
                          **({'corrected': b['corrected']} if b.get('corrected') else {})},
            'provenance': provenance({b['metric']: b})}


def add_ids(out):
    """Cross-reference IDs on each record (2026-10-26, the website chat): substrate_chebi (when the structure came from
    ChEBI), substrate_inchikey (RDKit, from the SMILES), substrate_pubchem_cid and taxon_id (tools/ids.py, cached;
    a structure or organism not looked up yet is asked here, few after the first run). A record whose paper names no
    organism takes its UniProt entry's (organism_source says so; 'paper' otherwise), so a filter on the organism finds it
    (KPC-2: 50 of 148 records named none)."""
    import ids
    from sequences import sprot
    from enrich import binomial
    ids.fill(out, log=lambda *a: None)
    c = ids.cache()
    for w in out:
        sid = w.get('smiles_id') or ''
        w['substrate_chebi'] = sid if sid.startswith('CHEBI:') else ''
        # where the structure came from, in one word (ChEBI, Rhea, SABIO-RK, PubChem, peptide, OPSIN, SKiD, deposited):
        # a structure keeps its source's terms (SKiD's are CC BY-NC-ND), so the values file names it
        w['smiles_source'] = re.split(r'[ :(]', w.get('smiles_how') or '')[0] if w.get('smiles') else ''
        key = ids.inchikey(w.get('smiles') or '')
        w['substrate_inchikey'] = key
        w['substrate_pubchem_cid'] = c.get('pubchem|' + key, '') if key else ''
        w['organism_source'] = 'paper' if w.get('organism') else ''
        acc = (w.get('uniprot_id') or '').split('-')[0]
        if not w.get('organism') and acc and (sprot().get(acc) or ('', ''))[1]:
            w['organism'], w['organism_source'] = binomial(sprot()[acc][1]), f'UniProt {acc}'
        o = re.sub(r'\s+', ' ', (w.get('organism') or '').strip()).lower()
        w['taxon_id'] = c.get('taxon|' + o, '') if o else ''
    ids.save()


def database_ec(out, db_ec):
    """No EC in the paper and none from UniProt: the EC the databases list this paper's values under (one full EC), else
    the one EC they list this enzyme's other values in the paper under. A label with its source, never a value; values
    filed under two ECs, or an enzyme whose values sit under several, stay blank. A measurement with two or more printed
    values needs two of them listed under the EC. An EC another enzyme of the same paper carries (printed, from UniProt,
    or shown strongly by its own values) is not given to this one unless its own values show it strongly (two printed
    values of one measurement within 2%, no two-digit rounding): the databases often list only one enzyme of a paper,
    and single or rounded numbers then match its sibling (2026-10-09 review: CPB got CPM's EC, MMP-2/9 MMP-12's, CelB
    BglB's, lipoamidase biotinidase's)."""
    def listed(w, strict=False):
        hits, printed = {}, 0
        for field, metric in (('kcat', 'kcat'), ('km', 'Km'), ('kcat_over_km', 'kcat/Km')):
            v = w.get(field)
            if v is not None and (field != 'kcat_over_km' or w['kcat_over_km_source'] == 'printed'):
                printed += 1
                for ec in {ec for ec, x in db_ec.get((w['pubmed_id'], metric), [])
                           if (abs(x - v) <= 0.02 * max(abs(x), abs(v)) if strict else close(x, v))}:
                    hits[ec] = hits.get(ec, 0) + 1
        return {ec for ec, n in hits.items() if n >= (2 if strict else min(2, printed))}
    def name(w):
        return w['pubmed_id'], w['enzyme_name'], w['organism']
    strong, held = {}, {}
    for w in out:
        strong.setdefault(name(w), set()).update(listed(w, strict=True))
    for w in out:  # paper -> EC -> the enzymes that carry it
        for ec in {e.strip() for e in w['ec_number'].split(';') if e.strip()} | strong[name(w)]:
            held.setdefault(w['pubmed_id'], {}).setdefault(ec, set()).add(name(w))
    def sibling(w, ec):
        return bool(held.get(w['pubmed_id'], {}).get(ec, set()) - {name(w)}) and ec not in strong[name(w)]
    # a paper whose enzymes without an EC of their own match two or more database ECs strongly, where one EC matches
    # several of them: the databases mixed the paper's enzymes up (20549272 files MMP-2's values under MMP-14's EC,
    # 26002966 swaps AKR1C34 and AKR1C35), so that EC goes to none of them
    contenders = {}
    for w in out:
        if not w['ec_number']:
            contenders.setdefault(w['pubmed_id'], {})[name(w)] = strong[name(w)]
    mixed = set()
    for pmid, enz in contenders.items():
        if len(set().union(*enz.values())) >= 2:
            mixed |= {(pmid, ec) for ec in set().union(*enz.values()) if sum(ec in e for e in enz.values()) >= 2}
    blank = [(w, {ec for ec in listed(w) if not sibling(w, ec) and (w['pubmed_id'], ec) not in mixed})
             for w in out if not w['ec_number']]
    enzyme = {}
    for w, ecs in blank:
        enzyme.setdefault(name(w), set()).update(ecs)
    for w, ecs in blank:
        same = enzyme[name(w)]
        if len(ecs) == 1:
            w['ec_number'], w['ec_source'] = next(iter(ecs)), 'databases: the EC they list this value of the paper under'
        elif not ecs and len(same) == 1:
            w['ec_number'], w['ec_source'] = next(iter(same)), "databases: the EC they list this enzyme's other values of the paper under"


def cmd_export():
    """catlog_wide.jsonl (full, with evidence and reasoning) and catlog_wide.csv (flat), one row per measurement.
    Enrich runs first when rows were added since the last enrich or lookups are waiting (a refused PubChem): the batch
    loop does not always run it, and a site build exports, so new rows never reach the site without their lookups."""
    last = next((f for f in reversed(events()) if f[2] == 'enrich'), None)
    added_since = not last or time.strftime('%Y-%m-%d %H:%M', time.localtime(CATALOG.stat().st_mtime)) >= last[0]
    if added_since or kv(last, 'waiting'):
        try:
            cmd_enrich()
        except Exception as e:  # a lookup service outage must not stop the export: it waits for the next one
            print(f'enrich failed ({e}); exporting with the lookups on file')
    from enrich import Cache
    ids, sm = Cache(ROOT / 'enrich' / 'protein.json'), Cache(ROOT / 'enrich' / 'structures.json')
    cat = [json.loads(l) for l in open(CATALOG) if l.strip()]
    groups = {i: g for i, g in enumerate(measurements(cat))}
    from sequences import split_variant
    muts = {}  # every printed mutation per (paper, protein): one numbering frame must fit them all
    for rows in groups.values():
        ref = ids.get(ident_key(rows[0]), {}).get('seq_ref')
        if ref:
            muts.setdefault((rows[0]['pmid'], ref), []).extend(split_variant(rows[0].get('variant'))[1])
    pmids = {g[0]['pmid'] for g in groups.values()}
    db, db_rows, db_ec = {}, [], {}
    dv = ROOT / 'sources' / 'db_values.tsv'
    if dv.exists():
        for line in open(dv):
            f = line.rstrip('\n').split('\t')  # source, pmid, ec, metric, value, substrate, organism, comment
            if len(f) > 4 and f[1] in pmids:
                db.setdefault((f[1], f[3]), []).append((f[0], float(f[4]))); db_rows.append(f)
                if re.fullmatch(r'\d+\.\d+\.\d+\.\d+', f[2]):  # full EC numbers only (not 1.1.1, 3.2.1.B28)
                    db_ec.setdefault((f[1], f[3]), []).append((f[2], float(f[4])))
    forms = {}  # each paper's natural forms -> their UniProt lookups (one entry for several forms tells none apart)
    for rows in groups.values():
        nf0 = natural_form(rows[0])
        if nf0:  # keyed by the name the form carries: its variant, or its enzyme name under the current convention
            key = rows[0].get('enzyme') if nf0.get('_by') == 'enzyme' else rows[0]['variant']
            forms.setdefault(rows[0]['pmid'], {})[key] = ids.get(ident_key(rows[0]), {})
    out = []
    for rows in groups.values():  # measurements() already keeps one value per metric and refuses ambiguous pairings
        out.append(wide(rows, ids, sm, len(rows) > 1, muts, db, forms))
    # Two measurements of the same slot that could not be paired (one kcat-only, one Km-only: an ambiguous pairing
    # measurements() refuses) hash to the same measurement_id. Only those get their printed cells folded into the id,
    # so every other id stays what earlier exports and review packs printed.
    seen = {}
    for w in out:
        seen[w['measurement_id']] = seen.get(w['measurement_id'], 0) + 1
    clash = {k for k, n in seen.items() if n > 1}
    for w in out:
        if w['measurement_id'] in clash:
            cells = sorted(f"{k}={v.get('raw_value', '')}" for k, v in w['evidence'].items())
            w['measurement_id'] = hashlib.sha1('|'.join([w['measurement_id'], *cells]).encode()).hexdigest()[:16]
    seen = {}
    for w in out:
        seen[w['measurement_id']] = seen.get(w['measurement_id'], 0) + 1
    for w in out:  # the same printed cells too (kcat/Km1 and kcat/Km2 of one row): the row ids tell them apart
        if seen[w['measurement_id']] > 1:
            w['measurement_id'] = hashlib.sha1('|'.join([w['measurement_id'], *sorted(w['row_ids'])]).encode()).hexdigest()[:16]
    database_ec(out, db_ec)
    add_ids(out)
    bounds = [json.loads(l) for l in open(BOUNDS) if l.strip()] if BOUNDS.exists() else []
    bound_mid = attach_bounds(out, groups, bounds)  # censored values beside a record's values, never in its numeric columns
    marks = audit_marks()
    for w in out:  # values an independent audit re-checked against the paper (the site shows it per value)
        w['audit'] = {r: marks[r] for r in w['row_ids'] if r in marks} or None
    doi = {r['pmid']: r['doi'] for r in csv.DictReader(open(PAPERS), delimiter='\t') if r.get('doi')}
    for w in out:  # a read that left the DOI out (31072150): the queue knows it
        w['doi'] = w['doi'] or doi.get(w['pubmed_id'], '')
    # each value against the enzyme databases for the same paper: database_check (status, the paired database row,
    # the relation code can state, a recorded cause) and database_note (an error that covers the paper); the website
    # publishes them as fixed phrases. After reading and verifying only: databases are never evidence for a value.
    from dbcompare import compare
    compared = compare(out, cat, ROOT, sm)
    # database values for these papers that no verified row matches: hints for a missed-value re-read
    ours = {}
    for r in cat:
        ours.setdefault((r['pmid'], r['metric']), []).append(molar(r) or 0)
    unmatched = [f for f in db_rows if not any(close(float(f[4]), v) for v in ours.get((f[1], f[3]), []) if v)]
    def tmp(path):  # per process: two exports at once (a batch and a website build) never share a temp file
        return path.with_name(f'{path.name}.{os.getpid()}.tmp')

    def whole(path):  # write next to it, then swap in: a reader (status, review, the website) never sees half a file
        return open(tmp(path), 'w', newline='')
    with whole(WORK / 'db_unmatched.tsv') as fh:
        fh.write('source\tpmid\tec\tmetric\tvalue\tsubstrate\torganism\tcomment\n')
        fh.writelines('\t'.join(f) + '\n' for f in unmatched)
    with whole(ROOT / 'catlog_wide.jsonl') as f:
        for w in out:
            f.write(json.dumps(w, ensure_ascii=False) + '\n')
    with whole(ROOT / 'catlog_wide.csv') as f:
        cw = csv.DictWriter(f, FLAT, extrasaction='ignore'); cw.writeheader(); cw.writerows({**w, **flat_provenance(w)} for w in out)
    with whole(WORK / 'database_compare.json') as f:  # counts per paper for the website's Stats (site build)
        json.dump(compared, f, ensure_ascii=False, indent=1)
    by_mid = {w['measurement_id']: w for w in out}
    enzyme_ec = {}  # (paper, enzyme) -> the ECs of its records; one EC means that enzyme's
    for w in out:
        if w.get('ec_number'):
            enzyme_ec.setdefault((w['pubmed_id'], enzyme_core({'enzyme': w.get('enzyme_name')})), set()).add(w['ec_number'])
    def ec_for(b):
        mid = bound_mid[b['row_id']]
        if mid and by_mid.get(mid, {}).get('ec_number'):
            return by_mid[mid]['ec_number']
        ecs = enzyme_ec.get((b['pmid'], enzyme_core(identity(b))), set())
        return next(iter(ecs)) if len(ecs) == 1 else ''
    brecs = [bound_record(b, bound_mid[b['row_id']], ids, doi, ec_for(b)) for b in bounds]
    with whole(ROOT / 'catlog_bounds.jsonl') as f:
        for x in brecs:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')
    with whole(ROOT / 'catlog_bounds.csv') as f:
        cw = csv.DictWriter(f, BOUND_FLAT, extrasaction='ignore'); cw.writeheader()
        cw.writerows({**x, **flat_provenance(x)} for x in brecs)
    for path in (WORK / 'db_unmatched.tsv', ROOT / 'catlog_wide.jsonl', ROOT / 'catlog_wide.csv', WORK / 'database_compare.json',
                 ROOT / 'catlog_bounds.jsonl', ROOT / 'catlog_bounds.csv'):
        os.replace(tmp(path), path)
    from dbcompare import NEW_TSV, new_to_databases  # values no database lists for their paper, for paper writing
    new_tsv = ROOT / NEW_TSV
    new_tsv.parent.mkdir(parents=True, exist_ok=True)
    text = new_to_databases(out)
    with whole(new_tsv) as f:
        f.write(text)
    os.replace(tmp(new_tsv), new_tsv)
    print(text.split('\n', 1)[0].lstrip('# ').replace(' (written by catlog.py export)', '') + f' -> {NEW_TSV}')
    n = len(out)
    print(f'{n} measurements -> catlog_wide.jsonl / .csv | with UniProt {sum(1 for w in out if w["uniprot_id"])}, '
          f'sequence {sum(1 for w in out if w["sequence"])}, SMILES {sum(1 for w in out if w["smiles"])}, '
          f'kcat {sum(1 for w in out if w["kcat"])}, Km {sum(1 for w in out if w["km"])}, '
          f'kcat/Km {sum(1 for w in out if w["kcat_over_km"])} (derived {sum(1 for w in out if w["kcat_over_km_source"].startswith("derived"))}), '
          f'EC {sum(1 for w in out if w["ec_number"])}'
          + (f' | censored values {len(bounds)} -> catlog_bounds.jsonl / .csv ({sum(1 for v in bound_mid.values() if v)} beside a record)' if bounds else ''))
    checks = [c for w in out for c in w['db_check'].values()]
    comparable = [c for c in checks if c.startswith(('same number', 'number not'))]
    from dbcompare import SOURCES
    print(f'Databases ({"/".join(SOURCES)}): {sum(c.startswith("same number") for c in comparable)} of {len(comparable)} values '
          f'appear as the same number for the same paper (a numeric cross-check: substrate, variant and assay are not compared); '
          f'{len(unmatched)} database values for these papers not found by v2 (work/db_unmatched.tsv)')
    st = {k: sum(v.values()) for k, v in compared['values_by_status_metric'].items()}
    new_a = sum(1 for w in out for c in w['database_check'].values() if c.get('paper_not_in_databases'))
    print('Against the databases (database_check: substrate, variant, organism and conditions compared): '
          + ', '.join(f"{k.replace('_', ' ')} {st.get(k, 0):,}" for k in ('confirmed', 'corrected', 'differs', 'same_number_other_label', 'new', 'not_compared'))
          + f' ({new_a:,} new values from papers in no database; not compared = calculated kcat/Km, or a Km or kcat/Km '
            f'printed over a mass concentration)'
          + (f"; {len(compared['catlog_wrong'])} values a paper check found wrong: `status` lists them" if compared['catlog_wrong'] else '')
          + (f"; {len(compared['recorded_problems'])} rows of sources/database_corrections.tsv not used (`status`): "
             + '; '.join(f"line {n}{' ' + rid if rid else ''} {why}" for n, rid, why in compared['recorded_problems'][:3])
             + (' …' if len(compared['recorded_problems']) > 3 else '') if compared['recorded_problems'] else ''))


# ---------- status ----------

_disk = {}


def on_disk(pmid):
    """A copy of the paper is here: the old library, papers/, or a text already made."""
    if not _disk:
        _disk['lib'] = set(library())
        _disk['papers'] = {f.name.split('.')[0] for f in (ROOT / 'papers').glob('*') if f.is_file()} if (ROOT / 'papers').exists() else set()
        _disk['texts'] = {f.stem for f in TEXTS.glob('*.txt') if '.' not in f.stem}  # main texts, not <pmid>.supp.txt
    return any(pmid in v for v in _disk.values())


def kv(fields, key):
    """The number in a 'key=N' field of a log line (0 when absent)."""
    for x in fields:
        if x.startswith(key + '='):
            try:
                return int(x.split('=', 1)[1])
            except ValueError:
                return 0
    return 0


ARCHIVER = os.environ.get('CATLOG_ARCHIVER', '')  # the authors' agent-log archiver (optional; README: settings)


def agent_logs_waiting():
    """[(chat, hours quiet, bytes)] of finished CatLog chats whose agent logs are not on Nova yet (2026-10-28: they are
    evidence, and Claude Code deletes them 30 days after a chat's last activity); [] when the archiver is not there."""
    if not ARCHIVER:
        return []
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location('archive_catlog_chats', ARCHIVER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.pending()
    except Exception:
        return []


def live_site_line():
    """What the live website (catlog.structf.studio) shows, from the receipt cloudflare/publish.py writes after each
    publish (site_build/published.json): its records, accepted records and papers, the data's date and ID. '' without
    such a receipt (quietly: a chat without one, a worktree). Read-only: one file read."""
    try:
        cf = json.loads((ROOT / 'site_build' / 'published.json').read_text(encoding='utf-8'))['cloudflare']
        day = time.strftime('%b %-d, %Y', time.strptime(cf['date'], '%Y-%m-%d'))
        return (f"catlog.structf.studio: {int(cf['records']):,} records ({int(cf['accepted_records']):,} accepted) from "
                f"{int(cf['all_papers']):,} papers · data of {day}, ID {cf['data_id']}")
    except (OSError, KeyError, TypeError, ValueError):
        return ''


def cmd_status(report=False):
    """The ONLY place progress numbers are computed (from papers.tsv, catalog.jsonl, rejected.jsonl and log.tsv). Prints a
    short summary in the chat; nothing is written to disk. Never copy its numbers into files: run it again."""
    from collections import Counter
    with Queue(write=False) as q:
        qrows = list(q.rows.values())
    cat, in_flight = [], False
    for i, l in enumerate(open(CATALOG) if CATALOG.exists() else [], 1):
        try:
            cat.append(json.loads(l)) if l.strip() else None
        except json.JSONDecodeError:
            if not l.endswith('\n'):  # another chat's add is writing this line right now
                in_flight = True; continue
            sys.exit(f'catalog.jsonl line {i} is not valid JSON: fix or restore it before anything else')
    n_rej = sum(1 for _ in open(REJECTED)) if REJECTED.exists() else 0
    ev = [f for f in events() if re.match(r'\d{4}-\d\d-\d\d', f[0])]
    by = Counter(r['status'] for r in qrows)
    meas = measurements(cat)
    with_values = {r['pmid'] for r in cat}
    first_add = {}
    for f in ev:
        if f[2] == 'add':
            first_add.setdefault(f[1], f[0][:10])
    held = locked()  # the method paper's test set: todo, but never read by this loop
    held_todo = sum(1 for r in qrows if r['status'] == 'todo' and r['pmid'] in held)
    late = later()  # the Km-only list: read after everything else, queued only then (cmd_more)
    queued = {r['pmid'] for r in qrows}
    late_todo = sum(1 for r in qrows if r['status'] == 'todo' and r['pmid'] in late and r['pmid'] not in held)
    late_left = late_todo + len(late - queued)
    todo_disk = sum(1 for r in qrows if r['status'] == 'todo' and on_disk(r['pmid']) and r['pmid'] not in held
                    and r['pmid'] not in late)
    lanes = Counter(lane_of(r) for r in qrows if r['status'] == 'needs_browser')
    ill_waiting = sum(1 for r in qrows if lane_of(r) in ILL_LANES and r['status'] in WAITING)
    supp_w = sum(1 for r in qrows if r['status'] == 'needs_supplement' and lane_of(r) not in ILL_LANES)  # as asks sorts them
    redl_w = sum(1 for r in qrows if r['status'] in REDOWNLOAD and lane_of(r) not in ILL_LANES)
    ill = sum(v for k, v in lanes.items() if k in ILL_LANES)  # needs_browser only: the partition below
    browser = sorted(((k, v) for k, v in lanes.items() if k not in ILL_LANES), key=lambda kv_: -kv_[1])
    checks = {m for r in qrows for m in re.findall(r'\b((?:click|login)=[^\s;]+)', r.get('note', ''))}
    redl = sum(by[x] for x in REDOWNLOAD)
    old = time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time() - 3 * 3600))
    stuck = [r['pmid'] for r in qrows if r['status'] == 'reading' and r.get('updated', '') < old]
    days, first_value = {}, {}
    for f in ev:
        c = days.setdefault(f[0][:10], Counter())
        e = f[2]
        if e == 'add':
            c['values added'] += kv(f, 'kept'); c['values rejected'] += kv(f, 'rejected')
            c['censored added'] += kv(f, 'bounds')
            c['censored passes' if 'pass=censored' in f[3:] else 'papers read'] += 1
            if kv(f, 'kept') and f[1] not in first_value:
                first_value[f[1]] = 1; c['new papers with values'] += 1
        elif e == 'recover':  # rows a changed rule brings back from rejected.jsonl (they stay there as history)
            c['values added'] += kv(f, 'kept'); c['values rejected'] += kv(f, 'rejected'); c['values recovered'] += kv(f, 'kept')
            c['censored added'] += kv(f, 'bounds')
        elif e == 'drop':
            c['dropped by audit'] += 1
        elif e == 'drop_bound':
            c['censored dropped'] += 1
        elif e == 'text':
            c['obtained'] += 1; c['via ' + (f[3] if len(f) > 3 else '?')] += 1
        elif e in ('filed', 'file_rejected', 'file_unmatched', 'supplement', 'audit_keep', 'audit_drop', 'conflict', 'needs_browser'):
            c[e] += 1
    for g in meas:
        d = min((r.get('added') or first_add.get(r['pmid'], '?'))[:10] for r in g)
        days.setdefault(d, Counter())['measurements added'] += 1
    kept = sum(c['values added'] for c in days.values()); drops = sum(c['dropped by audit'] for c in days.values())
    rej = sum(c['values rejected'] for c in days.values())
    n_bounds = sum(1 for l in open(BOUNDS) if l.strip()) if BOUNDS.exists() else 0
    b_added, b_drops = sum(c['censored added'] for c in days.values()), sum(c['censored dropped'] for c in days.values())
    ok = kept - drops == len(cat) and rej + drops + b_drops == n_rej and b_added - b_drops == n_bounds
    busy = in_flight or (not ok and time.time() - max(CATALOG.stat().st_mtime, REJECTED.stat().st_mtime,
                                                      BOUNDS.stat().st_mtime if BOUNDS.exists() else 0) < 60)
    if not ok and not busy:  # another chat may be adding right now: the files and log.tsv catch up within seconds
        with open(ROOT / 'catalog.jsonl.lock', 'w') as lk:
            try:
                fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.flock(lk, fcntl.LOCK_UN)
            except BlockingIOError:
                busy = True
    check = (f'catalog and log agree ({len(cat):,} values, {n_bounds:,} censored, {n_rej:,} rejected)' if ok else
             'another chat is adding or dropping right now: run status again in a minute' if busy else
             f'MISMATCH: log.tsv says {kept - drops:,} values / {b_added - b_drops:,} censored / {rej + drops + b_drops:,} rejected, '
             f'files hold {len(cat):,} / {n_bounds:,} / {n_rej:,}')
    today = days.get(now()[:10], Counter())
    conflicts = sum(c['conflict'] for d, c in days.items() if d >= time.strftime('%Y-%m-%d', time.localtime(time.time() - 14 * 86400)))
    lane_txt = ', '.join(f'{k} {v}' for k, v in browser) or 'none'
    net = today['values added'] - today['dropped by audit']
    since_audit = values_since_audit(ev)
    def day(d):  # '2026-10-09' -> 'Oct 9'
        return time.strftime('%b %-d', time.strptime(d, '%Y-%m-%d'))
    # (round 17, the user: the site's two counting words, here too: a value is one number; a record (the code's
    # "measurement") is one enzyme, variant, substrate and assay of one paper with up to three values)
    out = [f'### CatLog v2 progress ({now()})', '',
           f'**{len(cat):,} values** · **{len(meas):,} records** · **{len(with_values):,} papers with values**  ',
           f'Today: {net:+,} values, {today["measurements added"]:+,} records from {today["papers read"]:,} papers read', '']
    dated = sorted(d for d in days if re.match(r'\d{4}-\d\d-\d\d$', d))[-5:][::-1]
    if dated:
        out += ['| Day | Values | Records | Papers read | Papers obtained | Downloads filed |',
                '|---|---:|---:|---:|---:|---:|']
        out += [f"| {day(d)} | {days[d]['values added'] - days[d]['dropped by audit']:+,} | {days[d]['measurements added']:,} | "
                f"{days[d]['papers read']:,} | {days[d]['obtained']:,} | {days[d]['filed']:,} |" for d in dated]
        out.append('')
    need = [f'browser {sum(v for _, v in browser)} ({lane_txt})' if browser else '',
            f'supplement or better copy {by["needs_supplement"] + redl:,}' if by['needs_supplement'] + redl else '',
            f'interlibrary loan {ill:,} (optional)' if ill else '']
    out += [f'**Papers** ({len(qrows):,} in the queue)',
            f'- Done {by["done"]:,} · reading now {by["reading"]:,}' + (f' · parked {by["parked"]} (agents kept dying, e.g. usage limits; they come back by themselves after 24 h)'
                                                                      if by['parked'] else ''),
            f'- To read: {todo_disk:,} on disk · {by["todo"] - todo_disk - held_todo - late_todo:,} not tried yet'
            + (f' · {held_todo:,} held out (the method paper\'s test set)' if held_todo else '')
            + (f' · {late_left:,} Km-only papers (read by their own chat, most Km numbers first; last in other orders)'
               if late_left else ''),
            '- Need a download: ' + (' · '.join(x for x in need if x) or 'none'),
            f'- No kinetics {by["no_kinetics"]:,} · unavailable {by["unavailable"]:,}', '']
    asks = [f'{len(checks)} sites to clear' if checks else '', f'{sum(v for _, v in browser)} browser downloads' if browser else '',
            f'{supp_w} supplements' if supp_w else '', f'{redl_w} better copies' if redl_w else '']
    asks = [x for x in asks if x]
    out.append('- **Waiting on you:** ' + (', '.join(asks) + ' (links: `python3 catlog.py asks`)' if asks else 'nothing')
               + (f'; interlibrary loan {ill_waiting:,} is optional' if ill_waiting else ''))
    import math
    size = max(12, math.ceil(AUDIT_RATE * since_audit))  # what /audit samples (audit_size)
    audit = (f'audit due ({since_audit:,} values since the last one; /audit checks {size:,} of them, {AUDIT_RATE:.0%}; the loop runs it '
             'before its next batch)' if since_audit >= AUDIT_DUE else f'next audit in {AUDIT_DUE - since_audit:,} values')
    out.append(f"- **Checks:** {check} · {audit}")
    enr = next((f for f in reversed(ev) if f[2] == 'enrich'), None)
    if enr and kv(enr, 'waiting'):  # lookups a service refused (PubChem's rate limit): every batch's enrich asks again
        ref = next((x.split('=', 1)[1] for x in enr if x.startswith('refused=')), '-')
        out.append(f"- **Enrich:** {kv(enr, 'waiting'):,} lookups waiting after the last run ({enr[0]}"
                   + (f'; {ref} refused, rate limit' if ref != '-' else '') + "); the next export (or `catlog.py enrich`) asks again")
    n_aud, n_wrong, n_fix, n_lab = audit_summary(split=True)
    t_aud, t_wrong, _ = audit_summary(targeted=True)
    if n_aud:
        out.append(f'- **Audits:** {n_aud:,} values re-checked against their papers by a separate AI auditor: '
                   f'{n_wrong} wrong and dropped ({100 * n_wrong / n_aud:.1f}%), {n_fix} units corrected'
                   + (f'; targeted re-checks (values a database check found wrong, whole-paper follow-ups; not in the '
                      f'rate): {t_aud:,}, {t_wrong} dropped' if t_aud else '')
                   + (f'; {n_lab} organism {"label" if n_lab == 1 else "labels"} corrected (the values right)' if n_lab else ''))
    from dbcompare import usable  # paper checks of database differences (sources/database_corrections.tsv)
    problems, audited = [], audit_marks()  # the rows export cannot use, as export finds them (usable())
    # a catlog_wrong verdict waits for an audit: an audit keep on or after its date ends it (a drop removes the row)
    wrong = sorted({(r['pmid'], rid) for rid, rs in usable(ROOT, cat, problems).items() for r in rs if r['verdict'] == 'catlog_wrong'
                    and r['pmid'] not in held  # the method paper's test set: not audited here
                    and not (rid in audited and audited[rid][0] >= (r.get('date') or ''))})
    if wrong:
        out.append(f'- **Audit these:** {len(wrong)} values a paper check of a database difference found wrong in CatLog '
                   f'(sources/database_corrections.tsv, verdict catlog_wrong): '
                   + ', '.join(f'{p} {rid}' for p, rid in wrong[:10]) + (' …' if len(wrong) > 10 else '')
                   + '; audit them (`audited ROW_ID keep|drop WHY`)')
    if problems:
        out.append(f'- **database_corrections.tsv:** {len(problems)} rows not used as written (fix the row, or remove a '
                   f'row whose value left the catalog): ' + '; '.join(f"line {n}{' ' + rid if rid else ''} {why}" for n, rid, why in problems[:5]) + (' …' if len(problems) > 5 else ''))
    from human_review import status_line
    line = status_line(md=True)
    if line:
        out.append(f'- **Human review:** {line}')
    site = live_site_line()
    if site:
        out.append(f'- **Website:** {site}')
    free = shutil.disk_usage(ROOT).free / 1e9  # site builds clean up after themselves; papers, texts and work/ are evidence
    out.append(f'- **Disk:** {free:,.0f} GB free' + ('' if free >= 30 else
               ' · **LOW**: tell the user (chat scratchpads and old transcripts are the usual growers; they decide what '
               'goes). Under 10 GB: no site build (it needs ~5 GB while it runs), no bulk downloads'))
    logs = agent_logs_waiting()
    if logs:
        out.append(f'- **Agent logs:** {len(logs)} finished chats not on Nova yet ({sum(b for *_, b in logs) / 1e9:.1f} GB, '
                   f'oldest quiet {max(h for _, h, _ in logs) / 24:.0f} days; Claude Code deletes them 30 days after a '
                   f'chat\'s last activity): `/archive`')
    if stuck:
        out.append(f'- **Stuck:** {len(stuck)} papers reading for 3h+ ({" ".join(stuck[:10])}): `add` those with '
                   f'work/<PMID>.read.json and .verify.json, `reread` the rest')
    adds = [f for f in ev if f[2] == 'add']
    last_value = next((f[0] for f in reversed(adds) if kv(f, 'kept') or kv(f, 'bounds')), '')  # a censored value is progress
    read_since = sum(1 for f in adds if f[0] > last_value and 'pass=censored' not in f[3:]) if last_value else len(adds)
    if last_value:
        hours = (time.time() - time.mktime(time.strptime(last_value, '%Y-%m-%d %H:%M'))) / 3600
        out.append(f'- **Last value added:** {last_value} ({hours:.0f} h ago)' + (
            f' · **no progress since: {read_since} papers read** (CLAUDE.md "When nothing moves")' if read_since >= 3 else ''))
    last_report = max((i for i, f in enumerate(ev) if f[2] == 'report'), default=-1)
    since = sum(1 for f in ev[last_report + 1:] if f[2] == 'add')
    if not report:  # for the chat itself, not for the user
        out += ['', f'_(for the chat: {since} papers read since the last progress report, about {2 * since} agents'
                    + ('; time to show the user `python3 catlog.py report`' if since >= 25 else '') + ')_']
    if report:
        log('-', 'report', f'papers_read_since_last={since}')
    print('\n'.join(out))


if __name__ == '__main__':
    for d in (TEXTS, WORK, ROOT / 'enrich', ROOT / 'sources'):  # a fresh clone has none of them yet
        d.mkdir(exist_ok=True)
    a = [paper_id(x) for x in sys.argv[1:]] or ['status']
    {'status': lambda: cmd_status(),
     'report': lambda: cmd_status(report=True),
     'review': lambda: __import__('human_review').main(a[1:]),
     'site': lambda: __import__('site_release').main(a[1:]),
     'next': lambda: cmd_next(int(a[1]) if len(a) > 1 else 3),
     'get': lambda: print(*get(a[1])),
     'add': lambda: cmd_add_all(a[1:]),
     'prompt': lambda: cmd_prompt(a[1] if len(a) > 1 else ''),
     'show': lambda: cmd_show(a[1], a[2] if len(a) > 2 else ''),
     'more': lambda: cmd_more(next((int(x) for x in a[1:] if x.isdigit()), 200), km='--km' in a),
     'enrich': lambda: cmd_enrich(),
     'export': lambda: cmd_export(),
     'index': lambda: cmd_index(),
     'fetch': lambda: cmd_fetch(int(a[1]) if len(a) > 1 else 20),
     'file': lambda: cmd_file(int(a[1]) if len(a) > 1 else 3),
     'drop': lambda: cmd_drop(a[1], ' '.join(a[2:]) or 'no reason given'),
     'worklist': lambda: cmd_worklist(a[1] if len(a) > 1 and not a[1].isdigit() else '', int(a[-1]) if len(a) > 1 and a[-1].isdigit() else 20),
     'lanes': lambda: cmd_lanes('--retry' in a, '--force' in a) if set(a[1:]) <= {'--retry', '--force'}
     else sys.exit('usage: catlog.py lanes [--retry] [--force]'),
     'lanes-record': lambda: cmd_lanes_record('--dry' in a) if set(a[1:]) <= {'--dry'}
     else sys.exit('usage: catlog.py lanes-record [--dry]'),
     'sample': lambda: cmd_sample(int(a[1]) if len(a) > 1 else audit_size()),
     'supp': lambda: cmd_supp(int(a[1]) if len(a) > 1 else 20),
     'audited': lambda: cmd_audited(a[1], a[2], ' '.join(a[3:])),
     'unitfix': lambda: cmd_unitfix(a[1], a[2], *a[3:]),
     'restore': lambda: cmd_restore(a[1], *a[2:]),
     'audit-record': lambda: cmd_audit_record(*a[1:]),
     'dbdiff': lambda: __import__('dbcheck').dbdiff(sys.modules[__name__], a[1:]),
     'dbcheck-record': lambda: __import__('dbcheck').record(sys.modules[__name__], a[1:]),
     'reread': lambda: cmd_reread(a[1], ' '.join(x for x in a[2:] if x != '--fresh') or 'no reason given', '--fresh' in a),
     'censored': lambda: cmd_censored(int(a[1]) if len(a) > 1 else 6),
     'limitfix': lambda: cmd_limitfix(a[1], *a[2:]),
     'pmfix': lambda: cmd_pmfix(a[1], *a[2:]),
     'cellfix': lambda: cmd_cellfix(a[1], a[2], *a[3:]),
     'recover': lambda: cmd_recover(a[1], *a[2:]),
     'mark': lambda: cmd_mark([paper_id(x) for x in a[1].split(',')], a[2], ' '.join(a[3:]) or 'no reason given') if len(a) > 2 else sys.exit(
         'usage: catlog.py mark PMID[,PMID] lane=X|click=URL|login=URL|doi=DOI|todo|no_kinetics|wrong_paper|unavailable WHY'),
     'asks': lambda: cmd_asks()}[a[0]]()
