#!/usr/bin/env python3
"""Gain score for the Km-only papers (sources/discovered_km_*.tsv): how many enzyme Km numbers each paper's free full
text prints, counted by code (no agent), so the chat reading that list takes the richest papers first (the user,
2026-11-09: "read them here ... first figure out what will give us highest gain and then sort that way").

  score [threads]  fetch each paper's JATS XML (PMC Cloud, else Europe PMC for open access), render it
                   (jats_to_text.py), count its Km numbers, keep only the counts -> work/discovery_km/scores_fulltext.tsv
                   (resumable; no XML or text is kept: `next` fetches it again when the paper is read). ~50k papers, ~1 h.
  apply            write the counts into sources/discovered_km_<date>.tsv (columns km_count, noise, fulltext;
                   expected_values = gain() for a paper with free full text, else 0 for a flagged transport/
                   pharmacokinetic title, else the tier's 3/1/0) and reorder its .txt by expected_values.
  evaluate         the counter against the 108 papers two blind agents counted by hand (work/discovery_km/summary.tsv).

km_count(text): numeric cells under a Km column header (a table's first two rows) or in a row whose label says Km,
plus numbers with a concentration unit right after a Km word in running text that no table cell already gave.
Not Km: Ki, Kd, K0.5/S0.5, Kmax, Ks, IC50, and ratios (Vmax/Km, kcat/Km). On the 108 papers (2026-11-09): Spearman
0.76 with the agents' counts; count 0 -> 0.07 real values per paper (2 of 56 had any), 1-2 -> 1.2, 3-5 -> 2.9,
6+ -> 5.6; summed it over-counts by about 1.2x (transporter, cited and nanozyme Km look the same to code).
"""
import csv, json, os, re, sys, tempfile, threading, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work' / 'discovery_km'
SCORES = WORK / 'scores_fulltext.tsv'

KM = re.compile(r'(?<![A-Za-z0-9])(?:K_?\{?\s*[mM](?:\s*,?\s*(?:app|ap|\(app\)))?\}?(?![A-Za-z])|K_?\{?\s*[mM]_?\{?app\}?'
                r'|Michaelis(?:[- ]Menten)? constant|apparent K_?\{?m\}?)')
NOT_KM = re.compile(r'(?i)K_?\{?\s*(?:i|d|0\.5|s|max|cat|ii|is)\b|IC_?\{?50|S_?\{?0\.5|Hill')
RATIO = re.compile(r'/\s*\(?\s*(?:K_?\{?\s*[mM]|apparent K)')
NUM = re.compile(r'(?<![\w.])[<>≤≥~≈]?\s*\d+(?:[.,]\d+)?(?:\s*(?:±|\+/-|\+-)\s*\d+(?:[.,]\d+)?)?(?:\s*[×x]\s*10\^?\{?[-−–]?\d+\}?)?')
UNIT = r'(?:[mµμunp]M|mol\s*/?\s*[lL]|mmol|µmol|μmol|nmol|mg\s*/\s*m[lL]|µg\s*/\s*m[lL]|μg\s*/\s*m[lL]|g\s*/\s*[lL]|%|ppm|mol\s*L)'
SENT = re.compile(KM.pattern + r'[^.;\n]{0,80}?(?<![\w.])(\d+(?:[.,]\d+)?)(?:\s*(?:±|\+/-)\s*\d+(?:[.,]\d+)?)?\s*'
                  r'(?:[×x]\s*10\^?\{?[-−–]?\d+\}?\s*)?' + UNIT)
BAD_CELL = re.compile(r'(?i)^(?:n\.?\s?d\.?|n\.?\s?a\.?|nf\*?|-+|–|—|ns|n/a|not\s+\w+)$')


def cells(line):
    return [c.replace('[rowspan]', '').replace('[span]', '').strip() for c in line.split(' | ')]


def numeric(c):
    c = c.strip()
    return bool(c) and not BAD_CELL.match(c) and bool(re.search(r'\d', c)) and bool(NUM.search(c)) and len(c) < 60


def is_km(h):
    if RATIO.search(h) and not KM.search(RATIO.sub(' ', h)):  # Vmax/Km, kcat/Km, CLint = Vmax/Km: a ratio, not Km
        return False
    return bool(KM.search(h)) and not (NOT_KM.search(h) and not re.search(r'K_?\{?\s*[mM]\b', h))


def tables(text):
    """[(caption, [rows])] for each '=== Table' block of a jats_to_text rendering."""
    out, cur = [], None
    for line in text.splitlines():
        if line.startswith('=== Table') or line.startswith('=== TABLE'):
            cur = (line, []); out.append(cur); continue
        if cur is None:
            continue
        if not line.strip() or line.startswith('TABLE FOOT') or line.startswith('## ') or line.startswith('FIGURE'):
            cur = None if not line.strip() or line.startswith('## ') or line.startswith('FIGURE') else cur
            continue
        if ' | ' in line:
            cur[1].append(cells(line))
        elif cur[1]:
            cur = None
    return out


# words that say what kind of paper it is (counted over the whole text) and what a Km table holds (its caption + header)
TERMS = {
    'assay': r'enzyme activit|activity was (?:assayed|measured|determined)|enzyme assay|assay mixture|reaction mixture'
             r'|Lineweaver|Eadie|Hanes|Michaelis[- ]Menten (?:plot|equation|kinetics|curve)|initial (?:rate|velocit)'
             r'|substrate concentrations?|spectrophotometric|purified (?:enzyme|protein)|recombinant (?:enzyme|protein)'
             r'|nmol\s*/?\s*min|[µμ]mol\s*/?\s*min|U\s*/\s*mg|units?\s*/\s*mg|specific activit',
    'model': r'simulat|differential equation|\bODEs?\b|network model|circadian|Boolean|in silico|systems biology'
             r'|mathematical model|computational model|model parameters?|parameter estimat|sensitivity analysis',
    'transport': r'transporter|\buptake\b|\binflux\b|\befflux\b|permease|symport|antiport|\bchannels?\b',
    'pk': r'pharmacokinetic|\bPBPK\b|plasma concentration|area under the curve|\bdosing\b|\bdose[sd]?\b',
    'nano': r'nanozyme|nanoparticle|nanosheet|nanocomposite|(?:peroxidase|oxidase|catalase|laccase)[- ]like|mimic',
    'environment': r'\bsoils?\b|sediment|seawater|wastewater|sludge|biofilm|microbial communit',
}
TERMS = {k: re.compile(v, re.I) for k, v in TERMS.items()}
CAP_NOISE = re.compile(r'(?i)simulat|model parameters?|parameters? (?:used|of the model|in the model)|transport|uptake|'
                       r'influx|efflux|pharmacokinetic|nanozyme|nanoparticle|-like activity|soil|sediment')
# (not 'clearance': drug-metabolism Km tables print an intrinsic clearance CLint = Vmax/Km column)


def km_count(text):
    out = _km_count(text)
    out.update({k: len(p.findall(text)) for k, p in TERMS.items()})
    return out


def _km_count(text):
    seen, n_table, n_tab, n_noise = set(), 0, 0, 0
    for cap, rows in tables(text):
        if not rows:
            continue
        got, head = 0, rows[:2]
        cols = {i for r in head for i, c in enumerate(r) if is_km(c)}
        for r in rows[len(head) if cols else 0:]:
            for i in cols:
                if i < len(r) and numeric(r[i]) and not is_km(r[i]):
                    got += 1; seen.add(re.sub(r'\s', '', NUM.search(r[i]).group())[:12])
        for r in rows:  # rows labelled Km (parameters down the side)
            lab = [i for i, c in enumerate(r[:3]) if is_km(c) and not numeric(c)]
            if lab and not (set(range(len(r))) & cols - set(lab)):
                for i, c in enumerate(r):
                    if i > max(lab) and numeric(c):
                        got += 1; seen.add(re.sub(r'\s', '', NUM.search(c).group())[:12])
        n_table += got; n_tab += got > 0
        if got and CAP_NOISE.search(cap + ' ' + ' '.join(c for r in head for c in r)):
            n_noise += got
    flat = re.sub(r'=== Table.*?(?:\n\s*\n|\Z)', '', text, flags=re.S)
    n_sent = 0
    for m in SENT.finditer(flat):
        if NOT_KM.search(m.group()[:12]) or flat[max(0, m.start() - 2):m.start()].rstrip().endswith('/'):
            continue
        v = m.group(m.lastindex)
        if v not in {s.split('±')[0] for s in seen}:
            seen.add(v); n_sent += 1
    return {'table': n_table, 'sentence': n_sent, 'total': n_table + n_sent, 'tables_with_km': n_tab,
            'table_noise': n_noise}


# ---------- all three constants (the kcat list, 2026-11-10: one gain order over both Europe PMC lists) ----------

KCAT = re.compile(r'(?i)(?<![A-Za-z0-9])(?:k_?\{?\s*cat\}?(?![A-Za-z])|turnover numbers?)')
EFF = re.compile(r'(?i)(?:(?<![A-Za-z0-9])k_?\{?\s*cat\}?\s*\}?\s*/\s*\(?\s*K_?\{?\s*[mM]|catalytic efficienc|specificity constant)')
TIME = r'(?:(?:s|sec|min|h)\s*\^?\{?\s*[-−–]\s*1\}?|/\s*(?:s|sec|min)\b|per (?:second|minute))'
EFF_UNIT = r'(?:[mµμn]?M\s*\^?\{?\s*[-−–]\s*1\}?\s*[·.⋅ ]?\s*(?:s|sec|min)\s*\^?\{?\s*[-−–]\s*1\}?|/\s*[mµμn]?M\s*/\s*(?:s|min))'
NUMX = r'(?<![\w.])(\d+(?:[.,]\d+)?)(?:\s*(?:±|\+/-)\s*\d+(?:[.,]\d+)?)?\s*(?:[×x]\s*10\^?\{?\s*[-−–]?\d+\}?\s*)?'
SENTS = {'km': SENT,
         'kcat': re.compile(KCAT.pattern + r'(?!\s*\}?\s*/)[^.;\n]{0,80}?' + NUMX + TIME),
         'kcat_km': re.compile(EFF.pattern + r'[^.;\n]{0,80}?' + NUMX + EFF_UNIT)}


def kind(h):
    """Which constant a header or row label names: 'kcat_km' (kcat/Km, catalytic efficiency), 'kcat', 'km' or None
    (Vmax/Km, Ki, Kd, ... are none)."""
    if EFF.search(h):
        return 'kcat_km'
    if KCAT.search(h) and not RATIO.search(h):
        return 'kcat'
    return 'km' if is_km(h) else None


def value_count(text):
    """Numbers of each constant a text prints, as km_count counts Km: {'km', 'kcat', 'kcat_km', 'all', 'table_noise',
    and TERMS}. Its Km part equals km_count's 'total' except where a column is a kcat/Km headed with 'Km' alone."""
    seen, got, noise_n = set(), {'km': 0, 'kcat': 0, 'kcat_km': 0}, 0
    for cap, rows in tables(text):
        if not rows:
            continue
        head, here = rows[:2], 0
        cols = {i: k for r in head for i, c in enumerate(r) if (k := kind(c))}
        for r in rows[len(head) if cols else 0:]:
            for i, k in cols.items():
                if i < len(r) and numeric(r[i]) and not kind(r[i]):
                    got[k] += 1; here += 1; seen.add(re.sub(r'\s', '', NUM.search(r[i]).group())[:12])
        for r in rows:  # rows labelled with a constant (parameters down the side)
            lab = [(i, kind(c)) for i, c in enumerate(r[:3]) if kind(c) and not numeric(c)]
            if lab and not (set(range(len(r))) & set(cols) - {i for i, _ in lab}):
                last, k = lab[-1]
                for i, c in enumerate(r):
                    if i > last and numeric(c):
                        got[k] += 1; here += 1; seen.add(re.sub(r'\s', '', NUM.search(c).group())[:12])
        if here and CAP_NOISE.search(cap + ' ' + ' '.join(c for r in head for c in r)):
            noise_n += here
    flat = re.sub(r'=== Table.*?(?:\n\s*\n|\Z)', '', text, flags=re.S)
    plain = {s.split('±')[0] for s in seen}
    for k, pat in SENTS.items():
        for m in pat.finditer(flat):
            if k == 'km' and (NOT_KM.search(m.group()[:12]) or flat[max(0, m.start() - 2):m.start()].rstrip().endswith('/')):
                continue
            v = m.group(m.lastindex)
            if v not in plain:
                plain.add(v); got[k] += 1
    out = {**got, 'all': sum(got.values()), 'table_noise': noise_n}
    out.update({k: len(p.findall(text)) for k, p in TERMS.items()})
    return out


# ---------- score: fetch the free full text, count, keep the counts ----------

CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0 (research text mining)' + (f' (mailto:{CONTACT})' if CONTACT else '')}
CLOUD = 'https://pmc-oa-opendata.s3.amazonaws.com'
COLS = ['pmid', 'pmcid', 'tier', 'access', 'route', 'chars', 'table', 'sentence', 'total', 'tables_with_km',
        'table_noise'] + list(TERMS)
_lock = threading.Lock()


def _http(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def _cloud(pmcid):
    for v in (1, 2, 3):
        try:
            meta = json.loads(_http(f'{CLOUD}/metadata/{pmcid}.{v}.json', 30))
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                continue
            raise
        url = (meta.get('xml_url') or '').split('?')[0].replace('s3://pmc-oa-opendata', CLOUD)
        if url and (meta.get('is_pmc_openaccess') or meta.get('license_code')):
            x = _http(url, 60)
            if b'<article' in x[:4000] and b'<body' in x:
                return x
    return None


def _epmc(pmcid):
    for a in range(3):
        try:
            x = _http(f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML', 90)
            return x if b'<article' in x[:4000] and b'<body' in x else None
        except urllib.error.HTTPError as e:
            if e.code in (404, 500):  # Europe PMC answers 500 for an article it has no full text for
                return None
            time.sleep(5 * (a + 1))
        except Exception:
            time.sleep(5 * (a + 1))
    return None


def _score_one(r):
    sys.path.insert(0, str(ROOT / 'tools'))
    import jats_to_text
    route, x = '', None
    for name, f in (('pmc_cloud', _cloud), ('europepmc', _epmc)):
        if name == 'europepmc' and r['access'] != 'oa_epmc':
            break
        try:
            x = f(r['pmcid'])
        except Exception:
            x = None
        if x:
            route = name; break
    row = {'pmid': r['pmid'], 'pmcid': r['pmcid'], 'tier': r['tier'], 'access': r['access'], 'route': route or 'none',
           'chars': 0, 'table': '', 'sentence': '', 'total': '', 'tables_with_km': ''}
    if x:
        with tempfile.NamedTemporaryFile(suffix='.xml') as t:
            t.write(x); t.flush()
            try:
                text = jats_to_text.render(t.name)
            except Exception:
                text = ''
        row['chars'] = len(text)
        if text:
            row.update(km_count(text))
    with _lock, open(SCORES, 'a') as f:
        csv.DictWriter(f, COLS, delimiter='\t', lineterminator='\n', extrasaction='ignore').writerow(row)


def score(threads=6):
    from concurrent.futures import ThreadPoolExecutor
    done = {l.split('\t')[0] for l in open(SCORES)} if SCORES.exists() else set()
    if not SCORES.exists():
        SCORES.write_text('\t'.join(COLS) + '\n')
    src = max((ROOT / 'sources').glob('discovered_km_*.tsv'))
    rows = [r for r in csv.DictReader(open(src), delimiter='\t')
            if r.get('pmcid') and r.get('access') in ('oa_epmc', 'pmc_not_oa') and r['pmid'] not in done]
    order = {'km_table': 0, 'km_abstract': 1, 'km_body': 2}
    rows.sort(key=lambda r: (r['access'] != 'oa_epmc', order.get(r['tier'], 3), r['pmid']))
    print(f'{len(rows):,} papers to score ({len(done):,} done before)', flush=True)
    with ThreadPoolExecutor(threads) as ex:
        for k, _ in enumerate(ex.map(_score_one, rows), 1):
            if k % 1000 == 0:
                print(f'{k:,}', flush=True)


KSCORES = WORK / 'scores_kcat_list.tsv'
KCOLS = ['pmid', 'pmcid', 'tier', 'access', 'route', 'chars', 'km', 'kcat', 'kcat_km', 'all', 'table_noise'] + list(TERMS)


def _kscore_one(r):
    sys.path.insert(0, str(ROOT / 'tools'))
    import jats_to_text
    disk = ROOT / 'texts' / f"{r['pmid']}.txt"
    route, text = 'none', ''
    if disk.exists():
        route, text = 'disk', disk.read_text(errors='ignore')
    elif r.get('pmcid') and r.get('access') in ('oa_epmc', 'pmc_not_oa'):
        for name, f in (('pmc_cloud', _cloud), ('europepmc', _epmc)):
            if name == 'europepmc' and r['access'] != 'oa_epmc':
                break
            try:
                x = f(r['pmcid'])
            except Exception:
                x = None
            if x:
                with tempfile.NamedTemporaryFile(suffix='.xml') as t:
                    t.write(x); t.flush()
                    try:
                        text = jats_to_text.render(t.name)
                    except Exception:
                        text = ''
                route = name; break
    row = {'pmid': r['pmid'], 'pmcid': r.get('pmcid', ''), 'tier': r['tier'], 'access': r.get('access', ''),
           'route': route, 'chars': len(text)}
    if text:
        row.update(value_count(text))
    with _lock, open(KSCORES, 'a') as f:
        csv.DictWriter(f, KCOLS, delimiter='\t', lineterminator='\n', extrasaction='ignore').writerow(row)


def score_kcat(threads=6):
    """The kcat list (sources/discovered_europepmc_*.tsv): every paper outside the held-out test set, its text from
    texts/ when on disk (read or not: the read ones calibrate), else its free full text; all three constants counted."""
    from concurrent.futures import ThreadPoolExecutor
    sys.path.insert(0, str(ROOT))
    import catlog
    held = catlog.locked()
    done = {l.split('\t')[0] for l in open(KSCORES)} if KSCORES.exists() else set()
    if not KSCORES.exists():
        KSCORES.write_text('\t'.join(KCOLS) + '\n')
    rows = [r for src in sorted((ROOT / 'sources').glob('discovered_europepmc_*.tsv'))
            for r in csv.DictReader(open(src), delimiter='\t') if r['pmid'] not in held and r['pmid'] not in done]
    rows.sort(key=lambda r: (not (ROOT / 'texts' / f"{r['pmid']}.txt").exists(), r['pmid']))
    print(f'{len(rows):,} papers to score ({len(done):,} done before)', flush=True)
    with ThreadPoolExecutor(threads) as ex:
        for k, _ in enumerate(ex.map(_kscore_one, rows), 1):
            if k % 1000 == 0:
                print(f'{k:,}', flush=True)


# ---------- one gain scale over both lists (expected values a paper adds, calibrated on papers already read) ----------

KCAT_RATE, KM_RATE = 0.93, 0.6  # values read per number counted, 2026-11-10 (see kcat_gain, km_list_gain)
KCAT_FLOOR = {'table': 12, 'abstract': 5, 'body': 2}


def kcat_gain(s, tier):
    """Expected values of a kcat-list paper: 0.93 per kcat, Km or kcat/Km number counted, at least the tier's floor.
    Measured on the 1,132 read kcat-list papers with text (table tier; 2026-11-10): Spearman 0.67 between count and
    values read; count >= 15 gave 0.93 values per number; counts 0, 1-5 and 6-10 still gave 6.9, 13.8 and 11.5 values
    per paper (values in captions, unlabeled or image tables, supplements), hence the table floor of 12; the abstract
    and body floors (5, 2) are the old tier guesses, not measured. PK, nanozyme and soil papers (noise(); 32 of them)
    gave about 5, so they get 5; 'model' ones gave 14 of 15.5 counted and are not marked down, except model_only()
    papers, which get 2."""
    if model_only(s):
        return 2
    if noise(s) in ('pk', 'nano', 'environment'):
        return 5
    return max(KCAT_FLOOR.get(tier, 2), round(KCAT_RATE * int(s['all'])))


# bench-work words: a paper that measured something says how it made, purified or assayed it
WET = re.compile(r'(?i)stopped[- ]flow|pre-steady|single[- ]turnover|steady[- ]state kinetic|purified|purification'
                 r'|expressed in|overexpress|\bBL21\b|site[- ]directed|mutagenesis|\bHPLC\b|absorbance|spectrophotomet'
                 r'|fluorescen|incubated|buffer containing|quench|radiolabel|\[(?:γ|alpha|α)-?32P\]|rapid[- ]quench|burst')


def model_only(s):
    """A modelling paper with no bench work, which gives no values when read: 12+ model words, 5 or fewer bench-work
    words (WET) in its text on disk, and at least 3 model words per assay word; a paper whose text is not on disk is
    not judged. Measured 2026-11-13 on the read kcat-list papers: a floor of 20 named 36, of which 34 gave no value and
    the other two gave 6 and 1 (7 values over 36 papers). It replaces a first rule of 2026-11-11 that also demanded NO
    assay word, which named only 5 and so read a Gag-Pol simulation (23754941, model 36 / assay 6 / 2 bench words) and
    a whole-cell flux model for nothing. The ratio keeps the papers that model AND measure: 23198137 (35 values) and
    37699921 (10) count 25 and 24 assay words. Floor 12 since 2026-11-14, after an estrogen-metabolism ODE model
    (21610218, model 16 / assay 1, 74 counted constants from its parameter table) was read for nothing: on the 1,668
    read papers with scores it names 43, of which 41 gave no value (the same 7 values); 10 would also name 32735615
    (model 11, 72 values). Unread papers it names are read last, never left out."""
    model, assay = int(s.get('model') or 0), int(s.get('assay') or 0)
    if model < 12 or model < 3 * assay:
        return False
    t = ROOT / 'texts' / f"{s['pmid']}.txt"
    return t.exists() and len(WET.findall(t.read_text(errors='ignore'))) <= 5


def _write_tsv(path, cols, rows):
    """Write a source list whole, then swap it in, so a chat reading it meanwhile never sees half a file."""
    tmp = path.with_name(path.name + '.tmp')
    with open(tmp, 'w') as f:
        w = csv.DictWriter(f, cols, delimiter='\t', lineterminator='\n'); w.writeheader(); w.writerows(rows)
    os.replace(tmp, path)


def km_list_gain(expected):
    """Expected values of a Km-list paper with free full text: 0.6 of its gain() (the first 30 papers read here gave
    1,654 values for 2,793 counted Km numbers)."""
    return round(KM_RATE * int(expected))


def apply_gain():
    """Write `gain` (expected values, one scale) into both lists: the kcat list also gets `value_count`; its
    expected_values, which other chats' orders use, stays as it was."""
    got = {r['pmid']: r for r in csv.DictReader(open(KSCORES), delimiter='\t')} if KSCORES.exists() else {}
    for src in sorted((ROOT / 'sources').glob('discovered_europepmc_*.tsv')):
        rows = list(csv.DictReader(open(src), delimiter='\t'))
        cols = list(rows[0]) + [c for c in ('value_count', 'gain') if c not in rows[0]]
        n = 0
        for r in rows:
            s = got.get(r['pmid'])
            ok = bool(s and s['route'] != 'none' and s.get('all') not in ('', None) and int(s['chars']) >= 3000)
            r['value_count'] = s['all'] if ok else ''
            r['gain'] = str(kcat_gain(s, r['tier'])) if ok else ''
            n += ok
        _write_tsv(src, cols, rows)
        print(f'{src.name}: gain for {n:,} of {len(rows):,} papers')
    for src in sorted((ROOT / 'sources').glob('discovered_km_*.tsv')):
        rows = list(csv.DictReader(open(src), delimiter='\t'))
        cols = list(rows[0]) + (['gain'] if 'gain' not in rows[0] else [])
        for r in rows:
            r['gain'] = str(km_list_gain(r['expected_values'])) if r.get('fulltext') else ''
        _write_tsv(src, cols, rows)
        print(f'{src.name}: gain for {sum(1 for r in rows if r["gain"]):,} of {len(rows):,} papers')


# ---------- apply: counts into the source list ----------

def noise(s):
    """Why a counted paper looks like something other than an enzyme assay ('' if it does not), from its term counts:
    on the 108 hand-checked papers it names 8 of the 13 non-enzyme papers with a Km count (models, PK, nanozymes,
    soil; the other 5 count 1 or 2) and 1 of the 41 with enzyme Km (a transport-heavy paper with 2 values); on the 45
    highest counts of a first run it named the transporter, circadian/network-model, PK-simulation and soil papers.
    With gain(), the 9 papers at 6 or more all had enzyme Km (7.4 per paper), the 10 at 3-5 too (3.5)."""
    n = {k: int(s.get(k) or 0) for k in TERMS}
    a = n['assay']
    for k, at in (('transport', 30), ('model', 20), ('pk', 30), ('environment', 40)):
        if n[k] >= at and n[k] > a:
            return k
    return 'nano' if n['nano'] >= 25 else ''


def gain(s):
    """Expected Km values of a scored paper: its Km numbers less the cells of Km tables captioned as transport, model,
    PK, nanozyme or soil tables; a fifth of that for a paper noise() names; never 0 when it printed any (read last,
    never left out)."""
    total = int(s['total']); eff = total - int(s.get('table_noise') or 0)
    eff = eff if not noise(s) else eff // 5
    return max(eff, 1 if total else 0)


def apply():
    got = {r['pmid']: r for r in csv.DictReader(open(SCORES), delimiter='\t')} if SCORES.exists() else {}
    base = {'km_table': 3, 'km_abstract': 1, 'km_body': 0}
    for src in sorted((ROOT / 'sources').glob('discovered_km_*.tsv')):
        rows = list(csv.DictReader(open(src), delimiter='\t'))
        cols = list(rows[0]) + [c for c in ('km_count', 'noise', 'fulltext') if c not in rows[0]]
        for r in rows:
            s = got.get(r['pmid'])
            free = bool(s and s['route'] != 'none' and s['total'] != '' and int(s['chars']) >= 3000)  # shorter: a
            # scanned back issue whose XML only links the page images (its Km numbers are not countable from text)
            r['km_count'] = s['total'] if free else ''
            r['noise'] = noise(s) if free else ''
            r['fulltext'] = s['route'] if free else ''
            r['expected_values'] = str(gain(s) if free else 0 if r.get('flag') else base.get(r['tier'], 0))
        order = {'km_table': 0, 'km_abstract': 1, 'km_body': 2}
        rows.sort(key=lambda r: (-int(r['expected_values']), not r['fulltext'], order.get(r['tier'], 3),
                                 -int(r.get('year') or 0), r['pmid']))
        _write_tsv(src, cols, rows)
        txt = src.with_suffix('.txt'); tmp = txt.with_name(txt.name + '.tmp')
        tmp.write_text(''.join(r['pmid'] + '\n' for r in rows)); os.replace(tmp, txt)
        n = sum(1 for r in rows if r['fulltext'])
        print(f'{src.name}: {n:,} of {len(rows):,} papers counted from free full text; '
              f'{sum(1 for r in rows if r["fulltext"] and int(r["expected_values"]) > 0):,} with Km numbers')


def evaluate():
    rows = list(csv.DictReader(open(WORK / 'summary.tsv'), delimiter='\t'))
    print('pmid', 'tier', 'true', *COLS[6:], 'kind', sep='\t')
    for r in rows:
        k = km_count((WORK / 'sample' / 'text' / f"{r['pmid']}.txt").read_text())
        print(r['pmid'], r['tier'], r['own_km_values'], *(k[c] for c in COLS[6:]), r['kind'], sep='\t')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['score']:
        score(int(a[1]) if len(a) > 1 else 6)
    elif a[:1] == ['score-kcat']:
        score_kcat(int(a[1]) if len(a) > 1 else 6)
    elif a[:1] == ['apply']:
        apply()
    elif a[:1] == ['apply-gain']:
        apply_gain()
    elif a[:1] == ['evaluate']:
        evaluate()
    else:
        print(__doc__)
