"""Paper retrieval routes that need no browser, plus OCR and the publisher lane for the rest.

Order used by catlog.get(): local copy -> Europe PMC open-access XML -> Elsevier API full-text XML (by DOI, else PII) ->
OpenAlex open-access PDF -> PubMed LinkOut free full text (J-STAGE back issues etc.) -> otherwise the paper is
`needs_browser` with a lane (see DOWNLOADS.md). A local PDF whose text layer mangles symbols goes after the XML routes.
Every downloaded file must pass the title check before it is kept.
"""
import http.client, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / 'papers'
OLD_ENV = Path(os.environ.get('REALKCAT_DIR') or ROOT / 'realkcat') / '.env'  # the earlier system's .env, a fallback for API keys (README: settings)
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}
BROWSER_UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'}
ELSEVIER = ('10.1016/', '10.1006/', '10.1053/', '10.1124/', '10.1074/', '10.1194/')  # incl. JBC and J Lipid Res


def env_key(name):
    """An API key from the environment, this folder's .env (git-ignored), or the old repo's .env. Never printed."""
    key = os.environ.get(name, '')
    for env in (ROOT / '.env', OLD_ENV):
        if not key and env.exists():
            for line in env.read_text().splitlines():
                if line.strip().startswith(name + '='):
                    key = line.split('=', 1)[1].strip().strip('"\'')
    return key


def elsevier_key():
    return env_key('ELSEVIER_API_KEY')


def openalex_headers():
    """A free key (OPENALEX_API_KEY in .env, from openalex.org/settings/api) is optional: looking up one work by id,
    all `fetch` does, costs nothing (cost header 0, 2026-10-18); the keyless $0.10/day (1,000 calls) is spent only by
    list/filter queries (the review pack's batch lookup), and a key gives 10x that and 30 instead of 10 calls a second.
    Sent only to api.openalex.org, as a bearer header, so it never appears in a URL or a log."""
    key = '' if _openalex_refused else env_key('OPENALEX_API_KEY')
    return {**UA, 'Authorization': f'Bearer {key}'} if key else UA


_openalex_refused = []  # set when OpenAlex answered 401 to the key: the rest of the run goes without it


ENTITLED_PROBE = '10.1006/jmbi.1999.2566'  # a full text the campus network has always received
_entitled = [None]


def elsevier_entitled(key):
    """Does Elsevier give this network full text at all? Off campus it answers 400 for every article, which must not
    be read as 'no such article'. Checked once per process."""
    if _entitled[0] is None:
        url = f'https://api.elsevier.com/content/article/doi/{ENTITLED_PROBE}?httpAccept=text/xml&view=FULL'
        try:
            xml = urllib.request.urlopen(urllib.request.Request(url, headers={**UA, 'X-ELS-APIKey': key, 'Accept': 'text/xml'}),
                                         timeout=60).read()
            _entitled[0] = b'<ce:sections' in xml or b'xocs:rawtext' in xml
        except Exception:
            _entitled[0] = False
    return _entitled[0]


def lane(doi, pii='', pmc=''):
    """Where a human/browser would get this paper (DOWNLOADS.md route table)."""
    d = (doi or '').lower()
    if pmc:
        return 'pmc'  # in PMC but not open access (scanned back issues): free to read in a browser, no login
    if not d and pii:
        return 'jbc' if pii.upper().startswith(('S0021-9258', 'S0022-2275')) else 'sciencedirect'
    if not d:
        return 'ill_no_doi'
    if d.startswith('10.1016/s0021-9258') or d.startswith('10.1074/'):
        return 'jbc'
    if d.startswith(ELSEVIER):
        return 'sciencedirect'
    if d.startswith(('10.1002/', '10.1111/', '10.1046/', '10.1155/')):
        return 'wiley'
    if d.startswith('10.1093/'):
        return 'oup'
    if d.startswith('10.1021/'):
        return 'acs'
    if d.startswith(('10.1007/', '10.1023/', '10.1038/')):
        return 'springer_ill'
    return 'other'


def ocr_pdf(path, max_pages=30):
    """Text for a scanned PDF: render pages at 300 dpi and run tesseract."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['pdftoppm', '-r', '300', '-l', str(max_pages), '-png', str(path), f'{tmp}/p'],
                       capture_output=True, timeout=600)
        pages = []
        for img in sorted(Path(tmp).glob('p*.png')):
            pages.append(subprocess.run(['tesseract', str(img), '-'], capture_output=True, text=True, errors="replace", timeout=300).stdout)
    return '\n\f\n'.join(pages)


def pdf_pages(path):
    m = re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', str(path)], capture_output=True, text=True, errors="replace").stdout)
    return int(m.group(1)) if m else 0


def thin(text, pages):
    """True when a PDF's text layer is not the article (scans whose only text is a 'Downloaded from ...' watermark)."""
    words = [w for w in re.findall(r'[A-Za-z]{3,}', text) if w.lower() not in ('downloaded', 'from', 'by', 'user', 'library', 'university')]
    return len(words) < 60 * max(1, pages)


def first_pages_text(path):
    txt = subprocess.run(['pdftotext', '-f', '1', '-l', '2', str(path), '-'], capture_output=True).stdout.decode('utf-8', 'replace')  # a bad byte must not stop filing
    if thin(txt, 1):
        txt = ocr_pdf(path, max_pages=2)
    return txt


def esummary(pmid):
    """Title, DOI, PMCID and PII from PubMed (NCBI E-utilities): the fallback when Europe PMC is down, and the only
    source of a PII for old papers that have no DOI. Raises on a dead lookup."""
    if not str(pmid).isdigit():
        return {}  # a stand-in (no PMID): NCBI would split a digit-first id into several real PMIDs
    for attempt in range(3):
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request(
                f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json'
                '&tool=catlog' + (f'&email={CONTACT}' if CONTACT else ''), headers=UA), timeout=30).read())['result']
            if pmid not in d:
                return {}
            ids = {a['idtype']: a['value'] for a in d[pmid].get('articleids', [])}
            if d[pmid].get('error'):
                return {}
            return {'title': d[pmid].get('title', ''), 'doi': ids.get('doi', ''), 'pmcid': ids.get('pmc', ''),
                    'pii': ids.get('pii', ''), 'vernacular': d[pmid].get('vernaculartitle', ''),
                    'pubtype': ', '.join(d[pmid].get('pubtype', []))}
        except Exception:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError('pubmed lookup failed')


def elsevier_xml(pmid, doi, pii=''):
    """Full-text XML from the Elsevier Article Retrieval API (campus network), by DOI or, for old papers without one,
    by PII. None unless it has a body."""
    key = elsevier_key()
    if doi and doi.lower().startswith(ELSEVIER) or not doi and pii:
        if not key:
            raise RuntimeError('no Elsevier API key: set ELSEVIER_API_KEY (in the environment or a .env file in the CatLog folder)')  # the paper stays todo
    if not key:
        return None
    if doi and doi.lower().startswith(ELSEVIER):
        url = f'https://api.elsevier.com/content/article/doi/{urllib.parse.quote(doi, safe="/")}?httpAccept=text/xml&view=FULL'
    elif not doi and pii:
        url = f'https://api.elsevier.com/content/article/pii/{re.sub(r"[^0-9A-Za-z]", "", pii)}?httpAccept=text/xml&view=FULL'
    else:
        return None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={**UA, 'X-ELS-APIKey': key, 'Accept': 'text/xml'})
            xml = urllib.request.urlopen(req, timeout=60).read()
            break
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                if not elsevier_entitled(key):  # off campus: every article answers 400; not an answer about this one
                    raise RuntimeError('elsevier: no full-text entitlement on this network (off campus?)')
                return None  # a definite answer: Elsevier has no such article
            time.sleep(20 if e.code == 429 else 3)
        except Exception:
            time.sleep(3)
    else:
        # quota spent, off campus (401) or server trouble: not an answer, so the paper stays todo
        raise RuntimeError('elsevier api unavailable')
    time.sleep(0.3)
    raw = re.search(rb'<xocs:rawtext[^>]*>(.*?)</xocs:rawtext>', xml, re.S)
    if b'<ce:sections' not in xml and not (raw and len(raw.group(1)) > 8000):
        return None  # abstract-only: not entitled or no body
    PAPERS.mkdir(exist_ok=True)
    out = PAPERS / f'{pmid}.els.xml'
    out.write_bytes(xml)
    return out


def openalex_pdf(pmid, title_ok, title, doi=''):
    """An open-access PDF listed by OpenAlex that passes the title check, saved as papers/<PMID>.pdf. A paper without a
    PMID (stand-in id NP...) is looked up by DOI: OpenAlex reads `pmid:NP3F...` as PMID 3, an unrelated paper."""
    if str(pmid).isdigit():
        key = f'pmid:{pmid}'
    elif doi:
        key = 'doi:' + urllib.parse.quote(doi, safe='/:')
    else:
        return None
    for attempt in range(2):
        headers = openalex_headers()
        try:
            w = json.loads(urllib.request.urlopen(urllib.request.Request(
                f'https://api.openalex.org/works/{key}' + (f'?mailto={CONTACT}' if CONTACT else ''), headers=headers), timeout=30).read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # OpenAlex does not know the paper
            if e.code == 401 and 'Authorization' in headers:  # a wrong or revoked key must not stop `fetch`
                _openalex_refused.append(True)
                print('OpenAlex refused OPENALEX_API_KEY (401): going on without it; check the key in .env', file=sys.stderr)
                continue
            raise RuntimeError(f'openalex {e.code}')  # rate limit or outage: the paper stays todo
        except (OSError, http.client.HTTPException) as e:  # URLError, timeouts, a dropped connection (RemoteDisconnected)
            raise RuntimeError(f'openalex unreachable: {e}')
    # OpenAlex dropped `oa_locations` (2026): open copies are the `locations` with is_oa. Until 2026-10-11 only
    # best_oa_location was tried, often a publisher URL behind a bot check while a university repository had the PDF
    # (NPB70054C9: De Gruyter WAF challenge, utupub.fi serves it). A repository location with only a landing page
    # gives its PDF in citation_pdf_url, the way linkout_pdf reads one (NP7A1FF58E: research.rug.nl).
    locs = [w.get('best_oa_location') or {}] + [l for l in (w.get('oa_locations') or w.get('locations') or []) if l.get('is_oa')]
    urls = [l.get('pdf_url') or ('page:' + l['landing_page_url'] if (l.get('source') or {}).get('type') == 'repository'
                                 and l.get('landing_page_url') else '') for l in locs]
    for url in dict.fromkeys(u for u in urls if u and 'ncbi.nlm.nih.gov' not in u and 'europepmc.org' not in u):
        try:
            if url.startswith('page:'):
                r = _open(url[5:])
                page = r.read(2_000_000)
                if _bot(r, page):  # a challenge served with 200 (Anubis on ETH, Cloudflare on CSIC)
                    continue
                m = PDF_META.search(page)
                if not m:
                    continue
                url = urllib.parse.urljoin(r.geturl(), (m.group(1) or m.group(2)).decode().replace('&amp;', '&'))
            r = _open(url)
            data = r.read()
            if _bot(r, data):  # repositorio.uchile.cl answers its PDF links with an Anubis proof-of-work page
                continue
        except Exception:
            continue
        tmp = _pdf_ok(data, title_ok, title)
        if tmp:
            PAPERS.mkdir(exist_ok=True)
            out = PAPERS / f'{pmid}.pdf'
            shutil.move(tmp, out)
            return out
    return None


PDF_META = re.compile(rb'<meta[^>]+name="citation_pdf_url"[^>]+content="([^"]+)"|<meta[^>]+content="([^"]+)"[^>]+name="citation_pdf_url"')
BOT_PAGE = re.compile(rb"<title>\s*(?:Just a moment|Making sure you(?:&#39;|')re not a bot|Attention Required|Access denied)"
                      rb'|challenge-platform|"challenge":\{"issuedAt"|anubis_challenge|id="anubis', re.I)  # Cloudflare, Anubis PoW
PERSON_LINK = {}  # pmid -> a free article page a person opens (a site that asks scripts not to fetch its PDFs)
CHALLENGED = set()  # hosts that answered with a bot check this run: never asked again in it


def _open(url):
    """GET with a browser User-Agent, once per host per run after a bot check (403/429, or a 'challenge' header such
    as Cloudflare's cf-mitigated or AWS WAF's x-amzn-waf-action: research.rug.nl, De Gruyter): the script version of
    'stop a site at its first warning'. Nothing ever tries to get past one."""
    host = urllib.parse.urlsplit(url).hostname or ''
    if host in CHALLENGED:
        raise RuntimeError(f'{host} challenged earlier in this run')
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=BROWSER_UA), timeout=60)
    except urllib.error.HTTPError as e:
        if e.code in (403, 429) or 'challenge' in str(e.headers.get('cf-mitigated', '')):
            CHALLENGED.add(host)
        raise
    if r.status == 202 or 'challenge' in (r.headers.get('cf-mitigated', '') + r.headers.get('x-amzn-waf-action', '')):
        CHALLENGED.add(host)
        raise RuntimeError(f'{host} answered with a bot check')
    return r


def _bot(r, data):
    """True (and the host skipped for the rest of the run) when a 200 answer is a bot-check page, not the file."""
    if data.startswith(b'%PDF-') or not BOT_PAGE.search(data[:30000]):
        return False
    CHALLENGED.add(urllib.parse.urlsplit(r.geturl()).hostname or '')
    return True


def _pdf_ok(data, title_ok, title):
    """Save a downloaded PDF to a temporary file when it is the article (2+ pages, title check); return its path."""
    if not data.startswith(b'%PDF-') or len(data) < 20000:
        return None
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(data)
    if pdf_pages(tmp.name) >= 2 and title_ok(title, first_pages_text(tmp.name)):
        return tmp.name
    os.unlink(tmp.name)  # our own temporary download that failed the check
    return None


def linkout_pdf(pmid, title_ok, title):
    """A free full-text PDF that PubMed LinkOut lists as 'free resource' (J-STAGE back issues of J Biochem, Biosci
    Biotechnol Biochem, ...: often free where OpenAlex says closed). Saved as papers/<PMID>.pdf."""
    if not str(pmid).isdigit():
        return None  # LinkOut is PubMed's: a paper without a PMID has none
    try:
        d = json.loads(urllib.request.urlopen(urllib.request.Request(
            f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&id={pmid}&cmd=llinks&retmode=json'
            '&tool=catlog' + (f'&email={CONTACT}' if CONTACT else ''), headers=UA), timeout=30).read())
    except (OSError, http.client.HTTPException) as e:  # URLError, timeouts, and a dropped connection (RemoteDisconnected)
        raise RuntimeError(f'pubmed elink unreachable: {e}')
    except ValueError:
        return None
    urls = [o['url']['value'] for ls in d.get('linksets', []) for i in ls.get('idurllist', []) for o in i.get('objurls', [])
            if 'free resource' in (o.get('attributes') or []) and 'ncbi.nlm.nih.gov' not in o['url']['value']]
    for url in urls[:3]:
        try:
            r = _open(url)
            data = r.read()
            if _bot(r, data):
                continue
            if not data.startswith(b'%PDF-'):
                m = PDF_META.search(data)
                pdf = (m.group(1) or m.group(2)).decode().replace('&amp;', '&') if m else (r.geturl().replace('/_article', '/_pdf') if 'jstage' in r.geturl() else '')
                if not pdf:
                    continue
                pdf = urllib.parse.urljoin(r.geturl(), pdf)
                if 'jstage.jst.go.jp' in pdf and '_pdf' in pdf:
                    # J-STAGE's robots.txt: 'User-agent: * / Disallow: /*_pdf' (seen 2026-10-11; 285 papers had come
                    # this way). The article is free to read, so a person gets it: lane jstage, link on asks.html.
                    PERSON_LINK[str(pmid)] = r.geturl()
                    continue
                r = _open(pdf)
                data = r.read()
                if _bot(r, data):
                    continue
        except Exception:
            continue
        tmp = _pdf_ok(data, title_ok, title)
        if tmp:
            PAPERS.mkdir(exist_ok=True)
            out = PAPERS / f'{pmid}.pdf'
            shutil.move(tmp, out)
            PERSON_LINK.pop(str(pmid), None)  # another free copy did it (21897044: Hokkaido's repository)
            return out
    return None


SYMBOL_FONT = re.compile(r'Pi\d|Symbol|MathPi|PSSym|Greek', re.I)
GLYPH_SIGNS = {
    "a superscript minus as '21' or ')1' (s21, M21, (min)1))": r'(?<![\d.])\d+(?:\.\d+)?\s?(?:s|sec|min|h|M|mM)21\b|\b(?:s|min|M|mM)\)\s?1\b',
    "\u00b5 as 'l' (lM, lmol)": r'\d\s?lM\b|\blmol\b',
    "\u00b0 as '8' (378C is 37 \u00b0C)": r'\b[1-9]\d8\s?C\b',
    "\u00b1 as '6' (12.3 6 0.4 is 12.3 \u00b1 0.4; 38466.2 can be 384 \u00b1 6.2)": r'\d\s6\s\d',
}
# A number with two decimal points: a \u00b1 drawn as a digit (any digit: 2.580.4 is 2.5 \u00b1 0.4 in 21757926, 2.060.043
# is 2.0 \u00b1 0.043 in 9930669; OCR reads it as '4': 24.040.8), or two cells run together. No real number has two
# (2026-11-01; DOI pieces such as 1432-1033.1996.0782u are left out, and so is a token right after a grant, contract,
# catalog, gene-position or phone word: FRFC grants 2.4545.01, Merck 1.05835.0100, genome positions 6.131.843).
TWO_POINTS = re.compile(r'(?<![\w.\-/])\d{1,4}\.\d{3,6}\.\d{1,4}(?![\w.])')
NOT_A_CELL = re.compile(r"(?i)\b(?:grants?|contracts?|contrat|projects?|award|FRFC|FNRS|FRSM|IISN|FGWO|Loterie|NSh|"
                        r"cat(?:alog(?:ue)?)?\.?\s*(?:no\.?|#|number)|merck|nucleotides?|phone|tel|fax|UDC|patent)\b[^\n]{0,30}$")
BIG_INT = re.compile(r'(?<![\w.,\-/])\d{6,7}(?![\w.,])')


def two_points(text):
    """True when numbers with two decimal points show a \u00b1 drawn as a digit or cells run together: two such tokens,
    or one on a line that also holds a 6- or 7-digit integer (a cell with no decimal point: 840723 is 840 \u00b1 23 in
    15719018's Table II, its \u00b1 drawn as '7'). A GLYPH WARNING line already there is not counted."""
    text = re.sub(r'^GLYPH WARNING[^\n]*\n+', '', text)
    hits = [m for m in TWO_POINTS.finditer(text)
            if not NOT_A_CELL.search(text[max(0, m.start() - 60):m.start()].replace('\n', ' '))]
    if len(hits) != 1:
        return len(hits) >= 2
    a, b = text.rfind('\n', 0, hits[0].start()) + 1, text.find('\n', hits[0].end())
    return bool(BIG_INT.search(text[a:b if b >= 0 else len(text)]))


def scan_warning(text):
    """The first line for the OCR text of a scanned PDF: OCR reads a \u00b1 as a digit too (24.040.8 is 24.0 \u00b1 0.8)."""
    if not two_points(text):
        return ''
    return ('GLYPH WARNING: the OCR text of this scanned PDF shows numbers with two decimal points: a \u00b1 read as a '
            'digit (24.040.8 can be 24.0 \u00b1 0.8) or two cells run together. Take every kinetic number, \u00b1, unit '
            'prefix and exponent from the rendered page image (DO NOT trust these characters here).\n\n')


def glyph_warning(path, text):
    """A first line for the reader when a PDF's text layer mangles symbols. The worst case is silent: a symbol font
    without a Unicode map draws the micro sign as the letter 'm', so every uM reads as mM (Km 1000x too high)."""
    found = []
    try:
        import fitz  # PyMuPDF: tells which font drew each character
        pages = set()
        for pno, page in enumerate(fitz.open(str(path))):
            if pno >= 40:
                break
            for b in page.get_text('rawdict')['blocks']:
                for line in b.get('lines', []):
                    for sp in line['spans']:
                        if SYMBOL_FONT.search(sp['font']) and any(c['c'] == 'm' for c in sp['chars']):
                            pages.add(pno + 1)
        if pages:
            found.append(f"the micro sign as the letter 'm' (a symbol font without Unicode, pages {', '.join(map(str, sorted(pages)))}): "
                         "an 'mM', 'mmol' or 'mg' there may be \u00b5M, \u00b5mol or \u00b5g")
    except Exception:
        pass
    found += [what for what, rx in GLYPH_SIGNS.items() if re.search(rx, text)]
    if two_points(text):
        found.append('numbers with two decimal points: a ± drawn as a digit (2.580.4 can be 2.5 ± 0.4) or two '
                     'cells run together')
    if not found:
        return ''
    return ('GLYPH WARNING: the text layer of this PDF shows ' + '; '.join(found) + '. Take every kinetic number, '
            '\u00b1, unit prefix and exponent from the rendered page image (DO NOT trust these characters here).\n\n')
