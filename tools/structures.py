"""Substrate structure: one neutral, single-component SMILES per catalog substrate, or a blank with the reason.

find_smiles() tries a fixed order of sources; the first hit wins:
   1. macromolecule / generic-name regex  -> blank, 'no single structure'
   2. peptide builder + OPSIN             (residues written out; L unless the paper prints D)
   3. Rhea                                (participants of the enzyme's own reactions, by EC or UniProt)
   4. ChEBI 3-star, exact name/synonym    (local)
   5. SABIO-RK, same paper                (compound of the value-matched same-paper entries, by vote)
   6. SABIO-RK compound name
   7. PubChem name                        (network, cached; OPSIN overrides a different connectivity)
   8. OPSIN systematic name
   9. ChEBI 2-star
  10. SKiD Unique_substrates              (last: often lacks stereo)
Names, each route trying them in this order: the given names (substrate_full_name, substrate), the paper's own
definition of an abbreviation (Schwartz-Hearst on the paper text) and the same-paper database name chosen by vote.
A compound's number in its paper ('3', 'compound 46') is never looked up.
Abbreviations are paper-local ('SA' is shikimate in one paper, salicylic acid in another): cache results under
f'{pmid}|{name}'. Every result says where it came from, which name was used and what was assumed.
Tables: sources/ref/ (python3 tools/ref_structures.py). Lookup cache (PubChem, OPSIN): enrich/structure_lookups.json.
Network failure raises RuntimeError and is never cached as 'not found'. An OPSIN answer given while PubChem refused
carries 'pubchem_skipped' and is recomputed by the next enrich (provisional()).
"""
import os
import csv, gzip, json, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog('rdApp.*')
csv.field_size_limit(sys.maxsize)
ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'sources' / 'ref'
DB_VALUES = ROOT / 'sources' / 'db_values.tsv'
CACHE = ROOT / 'enrich' / 'structure_lookups.json'
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}
GREEK = {'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta', 'ε': 'epsilon', 'ω': 'omega', 'Δ': 'delta', 'κ': 'kappa',
         'λ': 'lambda', 'μ': 'mu'}

# ---------- names ----------


def greek(s):
    for g, w in GREEK.items():
        s = s.replace(g, w)
    return s


def norm(s):
    """Match key: Greek letters as words, markup and punctuation removed, '6-P' read as 6-phosphate."""
    s = re.sub(r'<[^>]+>', '', greek(s or ''))  # ChEBI names carry <i>, <sup>
    s = re.sub(r'(\d)-P\b', r'\1-phosphate', s).lower().replace('sulph', 'sulf')
    return re.sub(r'[^a-z0-9+]', '', s)


def has_stereo(name):
    """True when a name prints a configuration: D/L/DL/rac/meso, alpha/beta, R/S, E/Z, (+)/(-), cis/trans."""
    n = greek(name or '')
    return bool(re.search(r'(?<![A-Za-z])(?:[DdLl]|DL|dl|rac|meso|alpha|beta|[RS]|\((?:\d*[RSEZ](?:,\s*)?)+\)|\([+-]\)|\(±\)|cis|trans)-', n)
                or re.search(r'(?<![A-Za-z])(?:alpha|beta)(?=[A-Z ])', n))


def strip_stereo(name):
    """Match key with configuration descriptors and ring-form words removed (for the descriptor-free Rhea pass)."""
    n = greek(name or '').lower()
    n = re.sub(r'\((?:\d*[rsez](?:,\s*)?)+\)-|\([+-]\)-|\(±\)-|(?<![a-z])(?:dl|d|l|rac|meso|alpha|beta|aldehydo|keto|cis|trans)-', '', n)
    n = re.sub(r'o?(?:pyran|furan)os', 'os', n)  # glucopyranose -> glucose, fructofuranose -> fructose
    n = re.sub(r'(\d)-p\b', r'\1-phosphate', n)
    return norm(n)


def is_abbrev(name):
    n = (name or '').strip()
    return bool(n) and len(n) <= 20 and not re.search(r'\s', n) and (
        sum(c.isupper() for c in n) >= 2 or (re.search(r'\d', n) and re.search(r'[A-Z]', n)))


def sh_match(abbr, cand):
    """Schwartz-Hearst: every letter/digit of the abbreviation appears in order in the candidate, the first one
    at the start of a word."""
    a = [c for c in abbr.lower() if c.isalnum()]
    c = cand.lower()
    i, j = len(a) - 1, len(c) - 1
    while i >= 0:
        while j >= 0 and (c[j] != a[i] or (i == 0 and j > 0 and c[j - 1].isalnum())):
            j -= 1
        if j < 0:
            return False
        i -= 1; j -= 1
    return True


def paper_abbrev(text, abbr, max_words=8):
    """The paper's own definition of an abbreviation: '<full name> (ABBR)' in the text, the shortest preceding
    phrase that passes Schwartz-Hearst. Most frequent definition over all occurrences; '' if none or a tie."""
    if not text or not abbr or len(abbr) > 20:
        return ''
    want = re.sub(r'\s+', '', abbr)
    found = Counter()
    for m in re.finditer(r'\(\s*([^()]{1,24}?)\s*[;,)]', text):
        if re.sub(r'\s+', '', m.group(1)) != want:
            continue
        words = text[max(0, m.start() - 300):m.start()].split()[-max_words:]
        for k in range(1, len(words) + 1):
            cand = ' '.join(words[-k:]).strip(' ,;:')
            if re.search(r'[.;:]\s', cand):
                break
            if cand and norm(cand) != norm(abbr) and sh_match(abbr, cand):
                found[cand] += 1
                break
    top = found.most_common(2)
    if not top or (len(top) > 1 and top[1][1] == top[0][1] and norm(top[1][0]) != norm(top[0][0])):
        return ''
    return top[0][0]


# ---------- RDKit ----------
_unch = rdMolStandardize.Uncharger()
_lfc = rdMolStandardize.LargestFragmentChooser()


def mol(smi):
    try:
        return Chem.MolFromSmiles(smi) if smi and '*' not in smi else None
    except Exception:
        return None


TRANSITION = set(range(21, 31)) | set(range(39, 49)) | set(range(57, 81)) | set(range(89, 113))  # d- and f-block metals


def finish(smi):
    """(stored SMILES, notes): RDKit largest fragment, then neutralized. ('', []) if RDKit cannot read it or it is a
    lone uncharged atom with unpaired electrons."""
    m = mol(smi)
    if m is None:
        return '', []
    if m.GetNumAtoms() == 1 and m.GetAtomWithIdx(0).GetNumRadicalElectrons() and not Chem.GetFormalCharge(m):
        return '', []  # an element's name read as its atom: OPSIN's "oxygen" is [O], so is SABIO-RK's O2 InChI (15582992)
    notes = []
    frags = Chem.GetMolFrags(m, asMols=True)
    if len(frags) > 1:
        metal = lambda x: any(a.GetAtomicNum() in TRANSITION for a in x.GetAtoms())
        if metal(m) and not metal(_lfc.choose(m)) and sum(any(a.GetAtomicNum() == 6 for a in f.GetAtoms()) for f in frags) >= 2:
            return '', ['a metal complex drawn as separate pieces: its largest piece is a ligand, not the compound']  # ferrocenium was cyclopentadiene
        m = _lfc.choose(m); notes.append('largest fragment of a salt/hydrate/mixture')
    before = Chem.MolToSmiles(m)
    m = _unch.uncharge(m)
    out = Chem.MolToSmiles(m)
    if out != before:
        q = Chem.GetFormalCharge(m)
        notes.append('neutralized' + (f' (net charge {q:+d} remains)' if q else ''))
    return out, notes


def key(smi, n=25):
    """InChIKey of the stored (neutral, largest-fragment) form; n=14 compares connectivity only."""
    s, _ = finish(smi)
    try:
        return Chem.MolToInchiKey(Chem.MolFromSmiles(s))[:n] if s else ''
    except Exception:
        return ''


def formula(smi):
    """Heavy atoms of the stored (largest-fragment) form, e.g. 'C9O4'; '' if RDKit cannot read it. Hydrogens and charge
    are left out, so H2S, HS- and S2-, or a sugar's ring and open-chain forms, count as one compound."""
    s, _ = finish(smi)
    m = Chem.MolFromSmiles(s) if s else None
    if m is None:
        return ''
    c = Counter(a.GetSymbol() for a in m.GetAtoms() if a.GetAtomicNum() > 1)
    return ''.join(f'{e}{c[e]}' for e in sorted(c))


def defined_stereo(smi):
    m = mol(smi)
    return bool(m) and any(c != '?' for _, c in Chem.FindMolChiralCenters(m, includeUnassigned=True, useLegacyImplementation=False))


# ---------- lookup cache + network ----------
_cache = None


def cache():
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    return _cache


def save_cache():
    if _cache is not None:
        CACHE.parent.mkdir(exist_ok=True)
        tmp = CACHE.with_name(f'{CACHE.name}.{os.getpid()}.tmp')  # per process: two enrich runs can save at once
        tmp.write_text(json.dumps(_cache, indent=0, ensure_ascii=False))
        tmp.replace(CACHE)


_refused = set()  # hosts that refused this run (429/503 twice, or PubChem's own throttle at Black)
_waited = set()  # hosts we already paused for once this run
_gap = {}  # host -> seconds between requests, set from PubChem's X-Throttling-Control (0.25 s until it says otherwise)
GAP = {'Green': 0.25, 'Yellow': 1.0, 'Red': 4.0}  # PubChem allows 5 requests/s and 400/min per user; Yellow/Red = nearing it
LEVELS = ['Green', 'Yellow', 'Red', 'Black']


def throttle(headers):
    """Worst level in PubChem's X-Throttling-Control header ('Request Count status: Green (0%), Request Time status:
    Green (0%), Service status: Green (10%)'): 'Green', 'Yellow', 'Red' or 'Black'; '' when absent (other hosts, and
    the front end's own 429, which carries no such header)."""
    found = re.findall(r'status:\s*(green|yellow|red|black)\b', str((headers or {}).get('X-Throttling-Control') or ''), re.I)
    return max((s.capitalize() for s in found), key=LEVELS.index, default='')


def pace(host, headers):
    """Follow PubChem's own throttle: slower on Yellow and Red, and no more requests this run on Black (blocked)."""
    level = throttle(headers)
    if level == 'Black':
        _refused.add(host)
    elif level:
        _gap[host] = GAP[level]


def get(url, timeout=60):
    """Bytes, or None for a definite 'no such record' (400/404). Network trouble raises RuntimeError. A host that answers
    429 or 503 (rate limit; 503 'ServerBusy' is PubChem's own throttle answer) twice is not asked again this run (the
    first gets one pause, Retry-After honored up to 120 s): retrying every name cost 12 s each and kept PubChem's block
    going for hours (two enrich runs at once, 2026-10-09); those names stay uncached and are tried on the next run."""
    host = urllib.parse.urlsplit(url).netloc
    if host in _refused:
        raise RuntimeError(f'{host} refused earlier in this run (rate limit): not asked again until the next run')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                out = r.read()
                pace(host, r.headers)
            time.sleep(_gap.get(host, 0.25))  # <= 4 requests per second while PubChem says Green
            return out
        except urllib.error.HTTPError as e:
            pace(host, e.headers)
            if e.code in (400, 404):
                time.sleep(_gap.get(host, 0.25))
                return None
            if e.code in (429, 503) and host not in _waited and host not in _refused:  # one pause per run: a 429 can
                _waited.add(host)  # be a passing load spike (2026-10-10: one on the run's first request left 1,142 uncached)
                ra = str(e.headers.get('Retry-After') or '')
                time.sleep(min(120, int(ra)) if ra.isdigit() else 30)
                _gap[host] = max(_gap.get(host, 0.25), 1.0)  # then carry on at 1 request/s
                continue
            if e.code in (429, 503) or host in _refused:
                _refused.add(host)
                raise RuntimeError(f'{host} answered {e.code} (rate limit): not asked again this run')
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f'lookup failed: {url}')


def pubchem(name):
    """PubChem name -> list of {CID, SMILES, ConnectivitySMILES, InChIKey, Title} (cached; [] = no compound)."""
    k = 'pubchem|' + name
    if k not in cache():
        raw = get('https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/' + urllib.parse.quote(greek(name), safe='') +
                  '/property/SMILES,ConnectivitySMILES,InChIKey,Title/JSON')
        props = json.loads(raw).get('PropertyTable', {}).get('Properties', []) if raw else []
        cache()[k] = props
        save_cache()
    return cache()[k]


def provisional(entry):
    """True for a find_smiles result to recompute: an OPSIN answer given while PubChem refused (flagged; older ones are
    those whose name PubChem never answered, since route 7 asks PubChem for every name before OPSIN when it can)."""
    entry = entry or {}
    if entry.get('pubchem_skipped'):
        return True
    m = re.search(r'\[name "(.*?)" = ', entry.get('how', '')) if entry.get('route') == 'opsin' else None
    return bool(m) and 'pubchem|' + m.group(1) not in cache()


def opsin_spelling(name):
    """The name as OPSIN is asked it. OPSIN reads 'thio' after a substituent as an oxygen of the parent replaced by
    sulfur, and puts the substituent on carbon: BRENDA's "5'-deoxy-5'-butylthioadenosine" (15911263) became a
    5'-C-butyl 2'-thioadenosine. After 'L-deoxy', 'L-Rthio' and 'L-R-sulfanyl' are the group R-S- at L: 'L-Rsulfanyl'."""
    return re.sub(r"(?P<l>\d+['′]*)-deoxy-(?P<m>(?:.*?-)?)(?P=l)-(?P<r>.+?yl[)\]]?)-?(?:thio|sulfanyl)(?=[a-z])",
                  lambda x: f"{x['l']}-deoxy-{x['m']}{x['l']}-{x['r']}sulfanyl", name)


def opsin(names):
    """Local OPSIN 2.9.0, one Java call for all names not cached: {name: SMILES or ''}."""
    names = [n for n in dict.fromkeys(n.strip() for n in names if n and n.strip())]
    asked = {n: opsin_spelling(n) for n in names}
    todo = [n for n in dict.fromkeys(asked.values()) if 'opsin|' + n not in cache()]
    if todo:
        jar = REF / 'opsin.jar'
        if not jar.exists():
            raise RuntimeError(f'{jar} missing: run python3 tools/ref_structures.py')
        try:
            out = subprocess.run(['java', '-jar', str(jar), '-osmi'], input='\n'.join(re.sub(r'\s+', ' ', n) for n in todo) + '\n',
                                 capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.SubprocessError) as e:
            raise RuntimeError(f'OPSIN failed: {e}')
        lines = out.stdout.split('\n')
        if out.returncode != 0 or len(lines) < len(todo):
            raise RuntimeError(f'OPSIN failed: {out.stderr[-300:]}')
        for i, n in enumerate(todo):
            cache()['opsin|' + n] = lines[i].strip()
        save_cache()
    return {n: '' if odd_sulfur(cache()['opsin|' + asked[n]]) else cache()['opsin|' + asked[n]] for n in names}


def odd_sulfur(smi):
    """A reading with hydrogen on a sulfur bonded twice more is no compound: OPSIN reads 12742017's loose
    "2'-deoxy-3'-thiacytidine" by keeping the 3'-OH on the ring sulfur. Treated as no reading."""
    m = mol(smi)
    return bool(m) and any(a.GetSymbol() == 'S' and a.GetTotalNumHs() and a.GetDegree() > 1 and not a.GetFormalCharge()
                           for a in m.GetAtoms())


# ---------- local tables (lazy) ----------
_chebi = _rhea = _sabio = _skid = None


def chebi():
    """info: acc -> (stars, name, smiles); by_name: norm -> {acc}; names_of: acc -> [names]; conj: acc -> {acc}."""
    global _chebi
    if _chebi is None:
        if not (REF / 'chebi_compact.tsv.gz').exists():
            raise RuntimeError(f'{REF}/chebi_compact.tsv.gz missing: run python3 tools/ref_structures.py')
        info, by_name, names_of, conj = {}, defaultdict(set), defaultdict(list), defaultdict(set)
        with gzip.open(REF / 'chebi_compact.tsv.gz', 'rt') as f:
            next(f)
            for line in f:
                acc, stars, name, smi = line.rstrip('\n').split('\t')[:4]
                info[acc] = (int(stars or 0), name, smi)
                by_name[norm(name)].add(acc); names_of[acc].append(name)
        with gzip.open(REF / 'chebi_names.tsv.gz', 'rt') as f:
            next(f)
            for line in f:
                acc, name = line.rstrip('\n').split('\t')[:2]
                by_name[norm(name)].add(acc); names_of[acc].append(name)
        for line in open(REF / 'chebi_conj.tsv'):
            a, b = line.split('\t')[:2]
            if a.startswith('CHEBI:'):
                conj[a].add(b); conj[b].add(a)
        _chebi = (info, by_name, names_of, conj)
    return _chebi


def rhea():
    """ec -> {participant}, uniprot -> {participant}, participant -> Rhea name, participant -> Rhea SMILES."""
    global _rhea
    if _rhea is None:
        rxn, ec2p, uni2p, rname, rsmi = {}, defaultdict(set), defaultdict(set), {}, {}
        with open(REF / 'rhea_participants.tsv') as f:
            next(f)
            for line in f:
                rid, _, chebis, ecs = (line.rstrip('\n').split('\t') + ['', '', '', ''])[:4]
                rxn[rid.replace('RHEA:', '')] = {c for c in chebis.split(';') if c.startswith('CHEBI:')}
                for e in re.findall(r'\d+\.\d+\.\d+\.\d+', ecs):
                    ec2p[e] |= rxn[rid.replace('RHEA:', '')]
        for line in open(REF / 'rhea2ec.tsv'):
            f = line.rstrip('\n').split('\t')
            if len(f) == 4 and f[2] in rxn:
                ec2p[f[3]] |= rxn[f[2]]
        for line in open(REF / 'rhea2uniprot_sprot.tsv'):
            f = line.rstrip('\n').split('\t')
            if len(f) == 4 and f[2] in rxn:
                uni2p[f[3]] |= rxn[f[2]]
        for line in open(REF / 'chebiId_name.tsv'):
            a, n = (line.rstrip('\n').split('\t') + [''])[:2]
            rname[a] = n.strip()
        for line in open(REF / 'rhea-chebi-smiles.tsv'):
            a, s = (line.rstrip('\n').split('\t') + [''])[:2]
            rsmi[a] = s
        _rhea = (ec2p, uni2p, rname, rsmi)
    return _rhea


def sabio():
    """compound id -> (name, [InChI], [SMILES]); norm name -> {compound id}; entry id -> [(compound id, name, keyed)]."""
    global _sabio
    if _sabio is None:
        comp, by_name, entry = {}, defaultdict(set), defaultdict(list)
        with gzip.open(REF / 'sabio_compounds.tsv.gz', 'rt') as f:
            next(f)
            for line in f:
                cid, name, inchi, smi = line.rstrip('\n').split('\t')[:4]
                comp[cid] = (name, inchi.split(), smi.split())
                by_name[norm(name)].add(cid)
        with gzip.open(REF / 'sabio_entry_substrates.tsv.gz', 'rt') as f:
            next(f)
            for line in f:
                eid, cid, name, keyed = line.rstrip('\n').split('\t')
                entry[eid].append((cid, name, keyed == '1'))
        _sabio = (comp, by_name, entry)
    return _sabio


def skid():
    global _skid
    if _skid is None:
        import openpyxl
        _skid = defaultdict(set)
        x = ROOT / 'sources' / 'skid' / 'Main_dataset_v1.xlsx'
        if x.exists():
            rows = openpyxl.load_workbook(x, read_only=True)['Unique_substrates'].iter_rows(values_only=True)
            next(rows)
            for smi, n, *_ in rows:
                if smi and n:
                    _skid[norm(str(n))].add(str(smi).strip())
    return _skid


# ---------- routes: each returns None or {'smiles', 'id', 'how'} (+ 'notes') ----------

MACRO = re.compile(r'\b(t?RNA|DNA|tRNA\w*|protein|albumin|casein|collagen|gelatin|hemoglobin|haemoglobin|cytochrome|ferredoxin|flavodoxin|'
                   r'thioredoxin|histone|immunoglobulin|\w*cellulose|\w*xylan|\w*mannan|\w*glucan|starch|glycogen|chitin|chitosan|pectin|heparin|dextran|amylose|'
                   r'amylopectin|xyloglucan|hyaluronan|hyaluronate|hyaluronic acid|peptidoglycan|lignin|pullulan|inulin|polyphosphate|'
                   r'oligonucleotide|acyl-carrier|peptide\]|\[.*peptide|more|substrate|rRNA|mRNA|prothrombin|plasminogen|'
                   r'tubulin|VAMP-?\d*|ubiquitin|insulin|myoglobin|factor [IVX]+a?|acceptor|ferricytochrome|ferrocytochrome|flavoprotein|'
                   r'residues?\s*\(?\d+\s*[-–]\s*\d+|(?-i:[ACDEFGHIKLMNPQRSTVWY]{16,}))\b', re.I)  # a protein stretch ('residues 1-109')
# or a 16+ residue sequence (the peptide builder stops at 15): SABIO-RK's compound 'Protein' or 'p65' is no structure for them

AA3_NAME = {'Ala': 'alanine', 'Arg': 'arginine', 'Asn': 'asparagine', 'Asp': 'aspartic acid', 'Cys': 'cysteine',
            'Gln': 'glutamine', 'Glu': 'glutamic acid', 'Gly': 'glycine', 'His': 'histidine', 'Ile': 'isoleucine',
            'Leu': 'leucine', 'Lys': 'lysine', 'Met': 'methionine', 'Phe': 'phenylalanine', 'Pro': 'proline',
            'Ser': 'serine', 'Thr': 'threonine', 'Trp': 'tryptophan', 'Tyr': 'tyrosine', 'Val': 'valine'}
# Spelling variants that resolved most of the top unresolved database names (measured 2026-10-07 on the 500 most
# common unresolved names: N-alpha +499 values, 3-letter amino acids +310, p-/o-nitrophenyl +169, -oside ring +161).
REWRITES = [
    ('N-alpha -> N2', lambda n: re.sub(r'N-?(?:alpha|\u03b1)-', 'N2-', n)),
    ('3-letter amino acid -> name', lambda n: re.sub(r'^([LD])-(' + '|'.join(AA3_NAME) + r')$', lambda m: m.group(1) + '-' + AA3_NAME[m.group(2)], n)),
    ('p-/o-/m- -> 4-/2-/3-', lambda n: re.sub(r'\b([pomPOM])-(nitrophenyl|aminophenyl|chlorophenyl|methylphenyl|nitroanilide)',
                                           lambda m: {'p': '4-', 'o': '2-', 'm': '3-'}[m.group(1).lower()] + m.group(2), n)),
    ('pNP/oNP -> nitrophenyl', lambda n: re.sub(r'\b([pPoO])NP[- ]', lambda m: ('4' if m.group(1).lower() == 'p' else '2') + '-nitrophenyl ', n)),
    ('-oside -> -opyranoside', lambda n: re.sub(r'\b(D-|L-)?(gluc|galact|mann|xyl|fuc|rhamn)oside\b', lambda m: (m.group(1) or '') + m.group(2) + 'opyranoside', n, flags=re.I)),
    ('N,N,N-trimethyl-4-amino -> 4-trimethylammonio', lambda n: re.sub(r'\bN,N,N-trimethyl-(\d+)-amino', r'\1-trimethylammonio', n)),
    ('butyraldehyde -> butanal', lambda n: re.sub(r'(propion|butyr|valer)aldehyde\b', lambda m: {'propion': 'propanal', 'butyr': 'butanal', 'valer': 'pentanal'}[m.group(1).lower()], n, flags=re.I)),
]


NAME_STOP = {'acid', 'reduced', 'oxidized', 'oxidised', 'form', 'salt', 'sodium', 'potassium', 'lithium', 'hydrate', 'free',
             'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'omega', 'dimethyl'}  # shared by unrelated names: not evidence


def rewrites(name):
    """[(variant, rule)] for a name, applying every rule in turn (rules can combine, e.g. p-nitrophenyl ...oside)."""
    out, cur = [], name
    for rule, f in REWRITES:
        v = f(cur)
        if v != cur:
            out.append((v, rule)); cur = v
    return out
GENERIC = re.compile(r'^(?:an? |the )|^(?:mono|di|tri)acylglycerols?$|^(?:fatty acids?|acyl-coas?|lipids?|phospholipids?|ceramides?|'
                     r'sphingomyelins?|phosphatidyl\w+|lysophosphatidyl\w+|glycerophospholipids?|triglycerides?|oligosaccharides?|'
                     r'polysaccharides?|peptides?|polypeptides?|amino acids?|sugars?|alcohols?|aldehydes?|ketones?|esters?)$', re.I)


def group(acc, conj, depth=2):
    g, frontier = {acc}, {acc}
    for _ in range(depth):
        frontier = {y for x in frontier for y in conj.get(x, ())} - g
        g |= frontier
    return g


def rhea_parts(ec='', uniprot=''):
    ec2p, uni2p, _, _ = rhea()
    parts = set()
    for e in re.findall(r'\d+\.\d+\.\d+\.\d+', ec or ''):
        parts |= ec2p.get(e, set())
    for a in re.findall(r'[A-Z0-9]{6,10}', uniprot or ''):
        parts |= uni2p.get(a, set())
    return parts


def rhea_hit(name, ec='', uniprot='', loose=False):
    """A participant of the enzyme's Rhea reactions whose name (or a ChEBI name/synonym of it or of its conjugate
    acid/base) equals the name. loose=True compares names with configuration descriptors removed, so the reaction
    supplies the stereo. Exactly one molecule must match. Returns (hit or None, reason)."""
    info, by_name, names_of, conj = chebi()
    _, _, rname, rsmi = rhea()
    parts = rhea_parts(ec, uniprot)
    if not parts:
        return None, 'no Rhea reactions for this EC/UniProt'
    hits = set()
    # a name ChEBI gives to different compounds counts only as a participant's own name, not as a synonym: ChEBI lists
    # '3-(4-hydroxyphenyl)pyruvate' as a synonym of 3-phenylpyruvate (CHEBI:18005), so PMID 12234181's
    # p-hydroxyphenylpyruvate got phenylpyruvate from EC 1.4.1.20's reaction
    # (by formula: ring and open-chain forms or tautomers of one compound, as ChEBI files fructose 6-phosphate, share it)
    ambiguous = len({formula(info[a][2]) for a in by_name.get(norm(name), ()) if a in info and mol(info[a][2])} - {''}) > 1
    own = lambda x: [rname.get(x, ''), info.get(x, (0, ''))[1]]
    if not loose:
        k = norm(name)
        accs = set() if ambiguous else by_name.get(k, set())
        for p in parts:
            g = group(p, conj)
            if accs & g or any(norm(n) == k for x in g for n in own(x)):
                hits.add(p)
    else:
        k = strip_stereo(name)
        for p in parts:
            if any(strip_stereo(n) == k for x in group(p, conj) for n in own(x) + ([] if ambiguous else names_of.get(x, []))):
                hits.add(p)
    hits = {p for p in hits if mol(rsmi.get(p) or info.get(p, (0, '', ''))[2])}
    if not hits:
        return None, f'no match among {len(parts)} Rhea participants'
    if len({key(rsmi.get(p) or info[p][2]) for p in hits}) != 1:
        return None, f'ambiguous among Rhea participants {sorted(hits)}'
    p = sorted(hits)[0]
    smi = rsmi.get(p) or info[p][2]
    notes = []
    if loose or (not has_stereo(name) and has_stereo(rname.get(p, '')) and defined_stereo(smi)):
        notes.append('stereo/anomer from the Rhea reaction (the name used prints none)')
    src = ' and '.join(x for x in (f'EC {ec}' if ec else '', f'UniProt {uniprot}' if uniprot else '') if x)
    return {'smiles': smi, 'id': p, 'how': f'Rhea {p} "{rname.get(p, "")}", a participant of the reactions of {src}', 'notes': notes,
            'ph73': True}, ''


def chebi_hit(name, min_stars=3):
    """Exact (normalized) ChEBI name or synonym, stars >= min_stars; the top-star hits must be one molecule."""
    info, by_name, _, _ = chebi()
    accs = [a for a in by_name.get(norm(name), ()) if a in info and info[a][0] >= min_stars and finish(info[a][2])[0]]
    if not accs:
        return None
    top = max(info[a][0] for a in accs)
    best = sorted(a for a in accs if info[a][0] == top)
    if len({key(info[a][2]) for a in best}) != 1:
        return None
    return {'smiles': info[best[0]][2], 'id': best[0], 'how': f'ChEBI {best[0]} "{info[best[0]][1]}" ({top} stars), exact name/synonym'}


def sabio_structure(cid):
    comp, _, _ = sabio()
    name, inchis, smis = comp.get(str(cid), ('', [], []))
    if len(inchis) == 1:
        m = Chem.MolFromInchi(inchis[0])
        if m is not None:
            return {'smiles': Chem.MolToSmiles(m), 'id': f'SABIO compound {cid}', 'how': f'SABIO-RK compound {cid} "{name}" (InChI)'}
    if len(smis) == 1 and mol(smis[0]):
        return {'smiles': smis[0], 'id': f'SABIO compound {cid}', 'how': f'SABIO-RK compound {cid} "{name}" (SMILES)'}
    return None


def sabio_name_hit(name):
    _, by_name, _ = sabio()
    outs = [s for s in (sabio_structure(c) for c in sorted(by_name.get(norm(name), ()))) if s]
    if outs and len({key(o['smiles']) for o in outs}) == 1:
        return outs[0]
    return None


def pubchem_hit(name):
    props = [p for p in pubchem(name) if p.get('SMILES')]
    if not props:
        return None
    p = props[0]
    if len({key(q['SMILES'], 14) for q in props}) > 1:
        return None  # the name maps to compounds of different connectivity: ambiguous, take none
    how = f'PubChem CID {p.get("CID")} "{p.get("Title", "")}" for the name ({len(props)} CID{"s" if len(props) > 1 else ""}'
    how += ', same connectivity, first taken)' if len(props) > 1 else ')'
    return {'smiles': p['SMILES'], 'id': f'CID {p.get("CID")}', 'how': how, 'n_cids': len(props), 'title': p.get('Title', '')}


def skid_hit(name):
    s = skid().get(norm(name), set())
    if len(s) == 1 and mol(next(iter(s))):
        return {'smiles': next(iter(s)), 'id': 'SKiD', 'how': 'SKiD Unique_substrates structure (stereo often missing)'}
    return None


# ---------- peptides ----------
FULL = {'ala': 'alanine', 'arg': 'arginine', 'asn': 'asparagine', 'asp': 'aspartic acid', 'cys': 'cysteine', 'gln': 'glutamine',
        'glu': 'glutamic acid', 'gly': 'glycine', 'his': 'histidine', 'ile': 'isoleucine', 'leu': 'leucine', 'lys': 'lysine',
        'met': 'methionine', 'phe': 'phenylalanine', 'pro': 'proline', 'ser': 'serine', 'thr': 'threonine', 'trp': 'tryptophan',
        'tyr': 'tyrosine', 'val': 'valine'}
ACYL = {'ala': 'alanyl', 'arg': 'arginyl', 'asn': 'asparaginyl', 'asp': 'alpha-aspartyl', 'cys': 'cysteinyl', 'gln': 'glutaminyl',
        'glu': 'alpha-glutamyl', 'gly': 'glycyl', 'his': 'histidyl', 'ile': 'isoleucyl', 'leu': 'leucyl', 'lys': 'lysyl', 'met': 'methionyl',
        'phe': 'phenylalanyl', 'pro': 'prolyl', 'ser': 'seryl', 'thr': 'threonyl', 'trp': 'tryptophyl', 'tyr': 'tyrosyl', 'val': 'valyl'}
ONE = dict(zip('ARNDCQEGHILKMFPSTWYV', ['ala', 'arg', 'asn', 'asp', 'cys', 'gln', 'glu', 'gly', 'his', 'ile', 'leu', 'lys', 'met', 'phe',
                                         'pro', 'ser', 'thr', 'trp', 'tyr', 'val']))
NCAP = [(r'(?:n-?(?:alpha)?-)?acetyl|ac', 'N-acetyl'), (r'(?:n-)?succinyl|suc', 'N-succinyl'), (r'(?:n-)?glutaryl|glt', 'N-glutaryl'),
        (r'(?:n-?(?:alpha)?-)?benzyloxycarbonyl|carbobenzoxy|cbz|z', 'N-benzyloxycarbonyl'),
        (r'(?:tert-|t-)?butyloxycarbonyl|tert-butoxycarbonyl|boc', 'N-tert-butoxycarbonyl'),
        (r'(?:n-?(?:alpha)?-)?benzoyl|bz', 'N-benzoyl'), (r'(?:n-)?formyl|for|f', 'N-formyl'), (r'h', '')]
CCAP = [(r'p-nitroanilide|4-nitroanilide|pna|p-na|nitroanilide', '4-nitroanilide'),
        (r'7-amido-4-methylcoumarin|4-methylcoumarin[ -]7-amide|4-methyl-7-coumarylamide|amc|mca', '4-methylcoumarin-7-ylamide'),
        (r'7-amido-4-trifluoromethylcoumarin|4-trifluoromethylcoumarin[ -]7-amide|afc', '4-trifluoromethylcoumarin-7-ylamide'),
        (r'2-naphthylamide|beta-naphthylamide|betana|2na|nap', '2-naphthylamide'),
        (r'methyl ester|o-methyl ester|ome', 'methyl ester'), (r'ethyl ester|oet', 'ethyl ester'), (r'nh2|amide', 'amide'), (r'oh', '')]


def peptide_name(name, residues=False):
    """'Ala-Ala-Phe-p-nitroanilide', 'AAF-pNA', 'Suc-AAPF-pNA', 'Z-Gly-Pro-Arg-AMC' -> (OPSIN-readable name,
    L assumed?). One-letter codes only with a cap. None when the name is not a plain (capped) peptide.
    residues=True: the residues and caps as written ('N-succinyl ala-ala-pro-phe 4-nitroanilide'), also for a peptide
    that is not built (a capped C-terminal Glu)."""
    rest = re.sub(r'\s+', ' ', greek(name.strip()))
    ncap = ''
    for pat, val in NCAP:
        m = re.match(rf'(?:{pat})-(?=(?:[DL]-)?[A-Z])', rest, re.I)
        if m and not re.match(r'(?:[DL]-)?(?:' + '|'.join(k.capitalize() for k in FULL) + r')\b', rest):
            ncap, rest = val, rest[m.end():]
            break
    pglu = bool(re.match(r'(?:L-)?pGlu-|pyroglutamyl-', rest, re.I))
    rest = re.sub(r'^(?:L-)?pGlu-|^pyroglutamyl-', '', rest, flags=re.I)
    hippuryl = bool(re.match(r'hippuryl-', rest, re.I))
    rest = rest[9:] if hippuryl else rest
    ccap = ''
    for pat, val in CCAP:
        m = re.search(rf'[\s-](?:{pat})$', rest, re.I)
        if m:
            ccap, rest = val, rest[:m.start()]
            break
    toks, res = rest.split('-'), []
    if all(re.fullmatch(r'(?:[DL]-)?[A-Z][a-z]{2}', t) or t in ('D', 'L') for t in toks):
        cfg = ''
        for t in toks:
            if t in ('D', 'L'):
                cfg = t; continue
            m = re.fullmatch(r'(?:([DL])-)?([A-Z][a-z]{2})', t)
            if m.group(2).lower() not in FULL:
                return None
            res.append((m.group(1) or cfg or '', m.group(2).lower())); cfg = ''
    elif re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWY]{2,15}', rest) and (ncap or ccap):
        res = [('', ONE[c]) for c in rest]
    elif re.fullmatch(r'(?:[ACDEFGHIKLMNPQRSTVWY]-){1,14}[ACDEFGHIKLMNPQRSTVWY]', rest) and (ncap or ccap):
        res = [('', ONE[c]) for c in rest.split('-')]
    else:
        return None
    if pglu:
        res = [('L', 'pglu')] + res
    if hippuryl:
        ncap, res = 'N-benzoyl', [('', 'gly')] + res
    if residues:
        return f"{ncap} {'-'.join(a for _, a in res)} {ccap}" if res else None
    if not res or (len(res) == 1 and not (ccap or ncap)) or res[-1][1] == 'pglu':
        return None
    if res[-1][1] in ('glu', 'asp') and ccap:
        return None  # C-terminal Asp/Glu with a cap: alpha or side-chain linkage is not stated
    assumed = any(c == '' for c, a in res if a != 'gly')

    def acyl(c, a):
        return '5-oxo-L-prolyl' if a == 'pglu' else (ACYL[a] if a == 'gly' else f'{c or "L"}-{ACYL[a]}')
    c, a = res[-1]
    last = FULL[a] if a == 'gly' else f'{c or "L"}-{FULL[a]}'
    if ccap == 'amide':
        if a in ('asp', 'glu'):
            return None
        last = last[:-1] + 'amide' if last.endswith('ine') else (last + 'amide' if a == 'trp' else None)
        if last is None:
            return None
        tail = ''
    else:
        tail = f' {ccap}' if ccap else ''
    body = ''.join(acyl(*r) + '-' for r in res[:-1]) + last
    body = re.sub(r'(glycyl|L-\w+yl|D-\w+yl|5-oxo-L-prolyl)-(glycyl|glycine)', r'\1\2', body)
    out = ncap + ('-' if ncap and body[0] in 'LD5' else '') + body + tail
    return out, assumed


# ---------- same-paper database names ----------
_db = {}


def close(a, b):
    return abs(a - b) <= 0.02 * max(a, b) or f'{a:.2g}' == f'{b:.2g}'


def db_index(path):
    p = str(path)
    if p not in _db:
        idx = defaultdict(list)
        with open(path) as f:
            next(f)
            for line in f:
                s = line.rstrip('\n').split('\t')  # source, pmid, ec, metric, value, substrate, organism, comment
                if len(s) > 7:
                    m = re.match(r'SABIO (\d+)', s[7]) if s[0] == 'SABIO-RK' else None
                    idx[(s[1], s[3])].append((s[0], float(s[4]), s[5].strip(), m.group(1) if m else ''))
        _db[p] = idx
    return _db[p]


def sabio_compound_of(entry_id, species):
    """The substrate compound of a SABIO-RK entry: the one the parameter names, else the only (keyed) substrate."""
    subs = sabio()[2].get(entry_id, [])
    if species:
        c = [s for s in subs if s[1] == species]
    else:
        c = [s for s in subs if s[2]] or subs
    return c[0][0] if len({s[0] for s in c}) == 1 else ''


def same_paper_names(pmid, substrate, values, db_values_path=DB_VALUES):
    """Database rows (BRENDA, SABIO-RK, OED, SKiD) of the same paper and metric whose value matches one of this
    substrate's catalog values (within 2%), reduced to one name and one SABIO-RK compound by vote: the winner must
    cover more than half of the catalog values that matched anything, with no tie.
    substrate: the catalog's name for it (only quoted in 'how'). values: [(metric, value)] of the catalog rows of this
    substrate in this paper. Returns {'name', 'name_sources', 'name_votes', 'sabio', 'sabio_votes', 'matched',
    'n_values', 'how'}; name/sabio are '' when nothing wins. Pass the result to find_smiles(db_rows=...)."""
    idx = db_index(db_values_path)
    vn, vs, label, srcs, matched = Counter(), Counter(), {}, defaultdict(set), 0
    for metric, value in values:
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        names, comps = set(), set()
        for src, v, sub, eid in idx.get((str(pmid), metric), []):
            if not close(v, value):
                continue
            if sub:
                names.add(norm(sub)); label.setdefault(norm(sub), sub); srcs[norm(sub)].add(src)
            if eid:
                c = sabio_compound_of(eid, sub)
                comps.add(c or '?')
        if names or comps:
            matched += 1
        vn.update(names); vs.update(comps - {'?'})

    def pick(v):
        top = v.most_common(2)
        if not top or top[0][1] * 2 <= matched or (len(top) > 1 and top[1][1] == top[0][1]):
            return '', 0
        return top[0]
    n, nk = pick(vn)
    c, ck = pick(vs)
    out = {'name': label.get(n, ''), 'name_sources': ', '.join(sorted(srcs.get(n, ()))), 'sabio': c, 'matched': matched,
           'n_values': len(values)}
    out['how'] = f'"{substrate}" in {"PMID " if str(pmid).isdigit() else "paper "}{pmid}: ' + (
        f'same-paper database name "{out["name"]}" ({out["name_sources"]}; {nk} of {matched} value-matched catalog values)'
        if n else f'no same-paper database name won the vote ({matched} of {len(values)} values matched)')
    if c:
        out['how'] += f'; SABIO-RK compound {c} ({ck} of {matched})'
    out['name_votes'], out['sabio_votes'] = nk, ck
    return out


# ---------- the lookup ----------

_strenda = None


def strenda_hit(pmid, names):
    """A structure the paper's own authors deposited in STRENDA DB for this compound name (sources/strenda_compounds.tsv)."""
    global _strenda
    if _strenda is None:
        _strenda = {}
        p = ROOT / 'sources' / 'strenda_compounds.tsv'
        if p.exists():
            for line in open(p):
                f = line.rstrip('\n').split('\t')
                if len(f) > 3 and f[0] != 'pmid':  # header; ids may be stand-ins (NP...) for papers with no PMID
                    _strenda[(f[0], norm(f[2]))] = (f[3], f[1], f[5], f[6])
    for n in names:
        hit = _strenda.get((str(pmid), norm(n))) if n else None
        if hit:
            return {'smiles': hit[0], 'id': f'STRENDA {hit[1]}' + (f' / {hit[2]}' if hit[2] else ''),
                    'how': f'deposited by the paper\'s authors in STRENDA DB ({hit[1]}) for "{n}"'}
    return None


LABEL = re.compile(r'(?:(?:compound|substrate|peptide|cpd\.?)\s*)?\d+[a-z]?|(?:[RS][pc]){1,2}(?:/(?:[RS][pc]){1,2})*-\d+[a-z]?',
                   re.I)  # the paper's number for a compound, also with its stereo label ('Sp-1', 'Rp/Sp-3', 'RpRc-4': 20701311)
QUALIFIERS = {'racemic', 'compound', 'complex', 'mixture', 'isomer', 'peptide', 'substrate', 'analog', 'analogue', 'labeled',
              'labelled', 'form'}


def _words(x):
    return {t for t in re.findall(r'[a-z0-9]{4,}', greek(x or '').lower()) if t not in NAME_STOP}


def _bare_name(n):
    return re.sub(r'\s*\([^()]*\)\s*$', '', n or '').strip()  # 'pantetheine (2)', 'ATP (Mn2+ complex)'


def _is_full(n):
    """A name spelled out in words (not 'Np-Pan (34)', 'racemic OMVR', 'compound 12')."""
    return any(w[1:].islower() and w.lower() not in QUALIFIERS for w in re.findall(r'[A-Za-z]{4,}', greek(n or '')))  # not RpRc


def _related(db_name, printed, spelled=True, loose=True):
    """A database's name and a printed name share a word (or (loose) one word contains the other, or they differ by a
    typo: pantheteine), one name contains the other (ATP in MgATP, testosterone in (6,6-2H2)testosterone), or (spelled)
    the database's name abbreviates the printed one (ATP: adenosine triphosphate). NADH and NADPH are not related."""
    import difflib
    a, b = _words(db_name), _words(printed)
    na, nb = norm(db_name), norm(_bare_name(printed))
    if a & b or loose and any(len(x) >= 5 and len(y) >= 5 and (x in y or y in x) for x in a for y in b):
        return True
    if len(na) >= 3 and len(nb) >= 3 and (na in nb or nb in na):
        return True
    if loose and any(len(x) >= 6 and len(y) >= 6 and difflib.SequenceMatcher(None, x, y).ratio() >= 0.85 for x in a for y in b):
        return True
    return spelled and _is_full(printed) and is_abbrev(db_name) and sh_match(db_name, _bare_name(printed))


def printed_fit(smi, db_name, own_names, either=False):
    """Is a structure found under a database's name (db_name) the compound the paper names (own_names: the printed
    names, the paper's definitions)? Its molecular formula is that of OPSIN's reading of a printed name, when OPSIN
    reads one; otherwise db_name is related to a printed full name (_related), or no full name is printed.
    either=True (a SABIO-RK compound, curated per entry; a hit found under an abbreviation): refused only when OPSIN
    reads a printed name with other heavy atoms (hydrogens left out: OPSIN reads 3010873's 'N-ethyldibenzopyrazine
    ethylsulfate' as the dihydro base). A related name does not save it: SABIO-RK's structure can be garbled (12514023's
    bicyclo[3.2.0]heptenone; 21352863's 4-biphenylcarbaldehyde is 4-acetylbiphenyl) or another compound (12665427's
    acetylthiocholine got acetylcholine)."""
    names = [n for n in own_names if n]
    read = [x for x in opsin(names + [_bare_name(n) for n in names]).values() if x]
    if either:
        f = {formula(x) for x in read} - {''}
        return not f or formula(smi) in f
    f = {mformula(x) for x in read} - {''}
    full = [n for n in names if _is_full(n)]
    return mformula(smi) in f if f else (any(_related(db_name, n) for n in full) or not full)


def other_substrate(db_name, own_names, paper_names):
    """db_name is another compound the paper prints (a substrate or co-substrate of other rows) and unrelated to this
    one's printed names: the value vote paired that compound's values (25296188's acceptors got D-glucose). A shared
    word only, not a word inside another: 'phosphate' in 'bisphosphate' gave 11779234's deuterated DHAP its FBP."""
    own = [n for n in own_names if n]
    others = {norm(x) for x in paper_names} - {norm(n) for n in own}
    return norm(db_name) in others and not any(_related(db_name, n, spelled=False, loose=False) for n in own)


def mformula(smi):
    """Molecular formula of the stored (neutral, largest-fragment) form, hydrogens included: ring and open-chain
    sugars agree, NADH and NADPH or farnesol and farnesal do not. '' if RDKit cannot read it."""
    from rdkit.Chem.rdMolDescriptors import CalcMolFormula
    s, _ = finish(smi)
    m = Chem.MolFromSmiles(s) if s else None
    return CalcMolFormula(m) if m is not None else ''


def find_smiles(names, ec='', uniprot='', pmid='', text='', db_rows=None, paper_names=()):
    """names: [substrate_full_name, substrate] as printed (blanks allowed). ec: the enzyme's EC number(s) (row, else
    UniProt). uniprot: accession. pmid/text: the paper (text is read from texts/<pmid>.txt when not given), used for
    the paper's own abbreviation definitions. db_rows: same_paper_names(...) for this substrate, or None.
    The votes pair values, not compounds (25296188's quinone acceptors got D-glucose, 21876794's NADPH NADH, 10544015's
    xylose lactose, 22263579's nitrate sulfite), so a database's name or SABIO-RK compound is never another substrate
    the paper prints (paper_names: every substrate and co-substrate name of its catalog rows), and a structure found
    under a database's name must have the molecular formula of OPSIN's reading of the paper's own name (when OPSIN
    reads it), else share a word with the printed full name; a same-paper SABIO-RK compound needs one of the two.
    Returns {'smiles', 'id', 'route', 'how'} (+ 'n_cids' for PubChem); smiles is '' with the reason when nothing fits."""
    given = list(dict.fromkeys(str(n).strip() for n in names if n and str(n).strip()))
    if not given:
        return {'smiles': '', 'id': '', 'route': 'none', 'how': 'no name'}
    if MACRO.search(given[0]) or GENERIC.search(given[0]):
        return {'smiles': '', 'id': '', 'route': 'macromolecule', 'how': f'macromolecule or generic name ("{given[0]}"): no single structure'}
    if pmid:  # 1. the structure the authors themselves deposited for this paper
        hit = strenda_hit(pmid, given)
        if hit:
            smi, notes = finish(hit['smiles'])
            if smi and printed_fit(smi, '', given, either=True):  # a deposit can be a copy-paste: 28684981's chloro-, bromo-
                # and fluoro-2-hydroxymuconate were all deposited with the halogen-free parent's SMILES
                return {'smiles': smi, 'id': hit['id'], 'route': 'strenda', 'how': hit['how'] + ''.join(f'; {x}' for x in notes)}
    if not text and pmid:
        tp = [ROOT / 'texts' / f'{pmid}.txt', ROOT / 'texts' / f'{pmid}.supp.txt']
        text = '\n'.join(p.read_text(errors='replace') for p in tp if p.exists())
    cands = [(n, 'given name') for n in given]
    for n in given:
        d = paper_abbrev(text, n) if is_abbrev(n) else ''
        if d:
            cands.append((d, f'paper definition of "{n}"' + (f' ({"PMID" if str(pmid).isdigit() else "paper"} {pmid})' if pmid else '')))
    if db_rows and db_rows.get('name') and not other_substrate(db_rows['name'], given, paper_names):
        cands.append((db_rows['name'], f'same-paper database name ({db_rows["name_sources"]}; {db_rows["name_votes"]} of '
                                       f'{db_rows["matched"]} value-matched catalog values)'))
    for n, why in list(cands):  # spelling variants last, so a name as printed always wins
        for v, rule in rewrites(n):
            cands.append((v, f'{why}, rewritten ({rule}) from "{n}"'))
    seen, uniq = set(), []
    for n, why in cands:
        if n not in seen and not LABEL.fullmatch(n):  # a label ('3', '3a', 'compound 46') names nothing outside its paper:
            # 29513982's '3' got ChEBI's tridecaprenyl diphosphate(3-), 24814884's 'compound 46' PubChem's DO264
            seen.add(n); uniq.append((n, why))
    cands = uniq
    paper_stereo = any(has_stereo(n) for n, why in cands if not why.startswith('same-paper'))

    own = [n for n, w in cands if not w.startswith('same-paper') and ', rewritten' not in w]
    fits_printed = lambda smi, name, either=False: printed_fit(smi, name, own, either)

    def done(hit, route, n=None, why=None, extra=None):
        smi, notes = finish(hit['smiles'])
        if not smi:
            return None
        if why and why.startswith('same-paper') and not fits_printed(smi, n):
            return None
        if hit.get('ph73'):
            notes = [x.replace('neutralized', 'neutralized from the pH 7.3 form', 1) for x in notes]
        notes = (extra or []) + hit.get('notes', []) + notes
        how = hit['how'] + (f' [name "{n}" = {why}]' if n else '') + ''.join(f'; {x}' for x in notes)
        out = {'smiles': smi, 'id': hit['id'], 'route': route, 'how': how}
        if 'n_cids' in hit:
            out['n_cids'] = hit['n_cids']
        return out

    full = [n for n in given if not is_abbrev(n) and (_is_full(n) or len(n) > 20) and not LABEL.fullmatch(_bare_name(n))]
    # not 'peptide 19 (HPFHL)', and not a short name with no word in it: is_abbrev misses a lowercase-led abbreviation,
    # so 28323896's 'dP' switched off its own guard and got ChEBI's Asp-Pro (24401123's 'pTp' got p-terphenyl)

    def stray_names(names, n, why):
        """A hit for an abbreviation printed next to a full name that shares no word with that full name, and is not
        that name with another spelling (90% alike: 25049233's bisnorcholesta-1,4-diene-22-oyl CoA is PubChem's
        bisnorchola-1,4-dien-22-oyl-CoA), is another compound: 'HP' is His-Pro but hydroxypyruvate in PMID 25296650,
        'Z-GGPP' a Cbz peptide but geranylgeranyl diphosphate in 12680756, 'BAA' bromoacetic acid but benzoyl-arginine
        amide in 20469888."""
        import difflib
        if not (full and why.startswith('given name') and n not in full):
            return False
        if set().union(*(_words(f) for f in full)) & set().union(*(_words(x) for x in names)):
            return False
        return not any(min(len(a), len(b)) >= 6 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.9
                       for a in {norm(x) for x in names} for b in {norm(_bare_name(f)) for f in full})

    def pep_fits(smi, n):
        """A peptide built from a name other than a printed full name (an abbreviation, the same-paper database name) has
        the residues of a printed name written as a peptide and the formula of OPSIN's one-piece reading of a printed name:
        19362172's 'Ac-DCVC' is N-acetyl-S-(1,2-dichlorovinyl)-L-cysteine, not Ac-Asp-Cys-Val-Cys; 9756878's database name
        was the paper's other peptide. OPSIN reads 29336553's loose Z-..-AMC names in 3 pieces: no evidence."""
        others = [o for o in own if o != n]
        seqs = {peptide_name(o, residues=True) for o in others} - {None}
        read = [x for x in opsin(others).values() if x and '.' not in x]
        return (not seqs or peptide_name(n, residues=True) in seqs) and (not read or mformula(smi) in {mformula(x) for x in read})

    # 2. peptides, built from their residues
    peps = [(n, why, peptide_name(n)) for n, why in cands]
    peps = [(n, why, p) for n, why, p in peps if p]
    if peps:
        op = opsin([p[0] for _, _, p in peps])
        for n, why, (pname, assumed) in peps:
            if op.get(pname) and not stray_names([pname], n, why) and (n in full or pep_fits(op[pname], n)):
                r = done({'smiles': op[pname], 'id': 'OPSIN', 'how': f'peptide written out as "{pname}", converted by OPSIN'}, 'peptide', n, why,
                         ['L assumed (configuration not printed)'] if assumed else [])
                if r:
                    return r
    # 3. Rhea: the enzyme's own reactions
    if ec or uniprot:
        for n, why in cands:
            hit, _ = rhea_hit(n, ec, uniprot)
            if not hit and not paper_stereo and not has_stereo(n):
                hit, _ = rhea_hit(n, ec, uniprot, loose=True)
            r = done(hit, 'rhea', n, why) if hit else None
            if r:
                return r
    def stray(hit, n, why):  # a ChEBI hit: its names and synonyms ('SOPC', 'DMF' hit a phospholipid and dimethylformamide)
        info, _, names_of, _ = chebi()
        return stray_names(names_of.get(hit['id'], []) + [info.get(hit['id'], (0, ''))[1]], n, why)

    # 4. ChEBI 3-star
    for n, why in cands:
        hit = chebi_hit(n, 3)
        if hit and stray(hit, n, why):
            continue
        r = done(hit, 'chebi', n, why) if hit else None
        if r:
            return r
    # 5. SABIO-RK compound of the same paper's value-matched entries
    if db_rows and db_rows.get('sabio'):
        hit = sabio_structure(db_rows['sabio'])
        sname = (re.search(r'"([^"]+)"', hit['how']) or [None, ''])[1] if hit else ''
        if hit and (other_substrate(sname, given, paper_names) or not fits_printed(hit['smiles'], sname, either=True)):
            hit = None  # another substrate of the paper (11779234's deuterated DHAP got its FBP), or neither the formula nor a
            # word of the printed name (12514023's bicyclo[3.2.0]heptenone: SABIO's structure is garbled)
        if hit:
            hit['how'] += f', the substrate of the same-paper SABIO-RK entries whose values match ({db_rows["sabio_votes"]} of {db_rows["matched"]} values)'
            r = done(hit, 'sabio_paper')
            if r:
                return r
    # 6. SABIO-RK compound name
    for n, why in cands:
        hit = sabio_name_hit(n)
        if hit and not fits_printed(hit['smiles'], n, True):
            continue  # SABIO-RK's structure for the name can be garbled (26261304's 4-biphenylcarbaldehyde: 4-acetylbiphenyl)
        r = done(hit, 'sabio_name', n, why) if hit else None
        if r:
            return r
    # 7. PubChem, with OPSIN as a connectivity check
    op = opsin([n for n, _ in cands])
    pubchem_down = False
    for n, why in cands:
        try:
            hit = pubchem_hit(n)
        except RuntimeError:  # rate-limited or down: try OPSIN below; otherwise stay uncached and ask PubChem next run
            pubchem_down = True; continue
        if hit:  # PubChem's title can be a drug name (16788056's PGF2alpha is "Dinoprost"): its ChEBI synonyms count too
            _, by_name, names_of, _ = chebi()
            titles = [hit['title']] + [x for a in by_name.get(norm(hit['title']), ()) for x in names_of.get(a, [])]
        if not hit or stray_names(titles, n, why) or (is_abbrev(n) and not fits_printed(hit['smiles'], n, True)):
            continue  # an abbreviation PubChem reads as another compound than the paper's full name (12852784's BNPP)
        if op.get(n) and key(op[n], 14) and key(op[n], 14) != key(hit['smiles'], 14):
            r = done({'smiles': op[n], 'id': 'OPSIN', 'how': f'OPSIN systematic name (PubChem gave {hit["id"]} "{hit["title"]}", '
                                                         f'a different connectivity)'}, 'opsin_over_pubchem', n, why)
        else:
            r = done(hit, 'pubchem', n, why)
        if r:
            if pubchem_down:  # an earlier name went unanswered (refused): provisional, recomputed when PubChem answers
                r['pubchem_skipped'] = True
            return r
    # 8. OPSIN
    for n, why in cands:
        if op.get(n):
            r = done({'smiles': op[n], 'id': 'OPSIN', 'how': 'OPSIN systematic name'}, 'opsin', n, why)
            if r:
                if pubchem_down:  # PubChem never had its say (it can win with another name or its stereo): provisional,
                    r['pubchem_skipped'] = True  # catlog.py enrich recomputes it on a run where PubChem answers
                return r
    if pubchem_down:
        raise RuntimeError('PubChem unavailable: retried next run')  # never settle for a weaker route in its place
    # 9. ChEBI 2-star, 10. SKiD
    for route, fn in (('chebi_2star', lambda n: chebi_hit(n, 2)), ('skid', skid_hit)):
        for n, why in cands:
            hit = fn(n)
            if hit and route == 'chebi_2star' and stray(hit, n, why):
                continue
            if hit and route == 'skid' and not fits_printed(hit['smiles'], n, True):
                continue  # SKiD's entry can be another compound (19464995's C21 pregnanediol was a C19 ketone): when OPSIN
                # reads a printed name, the heavy atoms must agree, as for a SABIO-RK compound
            r = done(hit, route, n, why) if hit else None
            if r:
                return r
    tried = '; '.join(f'"{n}" ({why})' for n, why in cands) or (
        ', '.join(f'"{n}"' for n in given) + ' (a number in the paper, not looked up)')
    rh = '' if (ec or uniprot) else ' (no EC or UniProt, so no Rhea)'
    return {'smiles': '', 'id': '', 'route': 'none', 'how': f'no structure source matched: {tried}{rh}'}
