"""Protein identity and sequence for catalog rows, local reference files first.

find_protein(row, text)   UniProt accession, in this order: printed UniProt accession (checked active), printed PDB
                          (local SIFTS), printed GenBank/EMBL/RefSeq/Gene ID (UniProt xref, then UniParc, then NCBI's
                          CDS record), an ID the paper prints in parentheses right after the enzyme's own name, PDB
                          entries whose primary citation is the paper, then gene / protein name / EC + organism.
                          Only same-species entries count; several candidates with one identical sequence give the
                          sequence but no accession.
sequence(acc)             Swiss-Prot, Swiss-Prot isoforms (ACC-n), enrich/seq/ and the old bulk snapshot, then REST.
variant_sequence(...)     the measured variant in the first numbering frame under which every printed wild-type
                          residue of the paper matches (printed PDB author numbering, canonical, isoforms, mature
                          chain after signal/transit/propeptide, other PDB chains), else anchored on the paper's
                          printed mutagenesis primers, else nothing ('frames tried: ...').
construct(acc, pdb_ids)   the UniProt span a printed same-protein PDB chain covers (information; never applied).

Every result says how it was found. Reference files: sources/ref/ (python3 tools/ref_sequences.py). Caches:
enrich/protein_lookups.json (REST answers), enrich/pdb/<id>.json (residue-level SIFTS), enrich/seq/<acc>.fasta.
Network: at most 4 requests/s (NCBI 3/s); a failed request raises RuntimeError and nothing is cached for it.
"""
from functools import lru_cache
import os
import atexit, gzip, json, re, sys, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enrich import ACC, AA3, bulk_fasta, genus_species, parse_variant  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'sources' / 'ref'
TEXTS = ROOT / 'texts'
SEQ_DIR = ROOT / 'enrich' / 'seq'
PDB_DIR = ROOT / 'enrich' / 'pdb'
LOOKUPS = ROOT / 'enrich' / 'protein_lookups.json'
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}
UNIPROT = 'https://rest.uniprot.org'
NCBI = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
SIFTS_XML = 'https://ftp.ebi.ac.uk/pub/databases/msd/sifts/split_xml/'
AA1 = {k.upper(): v for k, v in AA3.items()} | {'MSE': 'M', 'SEC': 'U', 'PYL': 'O'}
GREEK = str.maketrans({'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta', 'ε': 'epsilon', 'ω': 'omega'})
OTHER_PDB_MAX = 40  # other structures of the accession tried as numbering frames (each one SIFTS file, cached)

# ---------- network + cache ----------

_last = [0.0]


def _get(url, gap=0.25):
    """Body (b'' allowed: UniProt answers an inactive entry with an empty 200), or None for 400/404/410.
    Anything else raises RuntimeError, so network trouble is never mistaken for 'not found'."""
    for attempt in range(4):
        wait = gap - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404, 410):
                return None
        except Exception:
            pass
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f'lookup failed: {url}')


_lookups = None
_unsaved = [0, time.time()]


def save():
    """Write enrich/protein_lookups.json (also done every 25 new answers, every 10 s, and at exit)."""
    if _lookups is not None and _unsaved[0]:
        LOOKUPS.parent.mkdir(parents=True, exist_ok=True)
        tmp = LOOKUPS.with_name(f'{LOOKUPS.name}.{os.getpid()}.tmp')
        tmp.write_text(json.dumps(_lookups, ensure_ascii=False))
        tmp.replace(LOOKUPS)
        _unsaved[:] = [0, time.time()]


atexit.register(save)


def _cached(ns, key, fetch):
    global _lookups
    if _lookups is None:
        _lookups = json.loads(LOOKUPS.read_text()) if LOOKUPS.exists() else {}
    box = _lookups.setdefault(ns, {})
    if key not in box:
        box[key] = fetch()  # a RuntimeError propagates and nothing is stored
        _unsaved[0] += 1
        if _unsaved[0] >= 25 or time.time() - _unsaved[1] > 10:
            save()
    return box[key]


# ---------- local reference files (read once, lazily) ----------

_local = {}


def _once(name, build):
    if name not in _local:
        _local[name] = build()
    return _local[name]


def _fasta(path):
    acc, head, buf = None, '', []
    with gzip.open(path, 'rt') as f:
        for line in f:
            if line[0] == '>':
                if acc:
                    yield acc, head, ''.join(buf)
                acc, head, buf = line.split('|')[1], line, []
            else:
                buf.append(line.rstrip())
    if acc:
        yield acc, head, ''.join(buf)


def sprot():
    """Swiss-Prot: accession -> (sequence, organism as printed after OS=)."""
    def build():
        f = REF / 'uniprot_sprot.fasta.gz'
        out = {}
        if f.exists():
            for acc, head, seq in _fasta(f):
                m = re.search(r' OS=(.*?) OX=', head)
                out[acc] = (seq, m.group(1) if m else '')
        return out
    return _once('sprot', build)


def varsplic():
    """Swiss-Prot isoforms: 'ACC-n' -> sequence (the canonical isoform is in sprot(), not here)."""
    def build():
        f = REF / 'uniprot_sprot_varsplic.fasta.gz'
        return {acc: seq for acc, _, seq in _fasta(f)} if f.exists() else {}
    return _once('varsplic', build)


def isoforms(acc):
    def build():
        idx = {}
        for iso in varsplic():
            idx.setdefault(iso.split('-')[0], []).append(iso)
        return idx
    return sorted(_once('iso_index', build).get(acc.split('-')[0], []), key=lambda a: int(a.split('-')[1]))


def _raw(name):
    """A reference file as one bytes object, searched with bytes.find (a few ms per lookup, ~1/6 the memory of a dict)."""
    def build():
        f = REF / name
        if not f.exists():
            return None
        data = gzip.decompress(f.read_bytes()) if name.endswith('.gz') else f.read_bytes()
        return b'\n' + data.replace(b'\r', b'')  # the SIFTS files end lines with CRLF
    return _once(name, build)


def _lines(data, key, start_of_line=True):
    """Every line of data containing key (at the start of the line when start_of_line), as str."""
    out, i = [], data.find(key) if data else -1
    while i != -1:
        a = i + 1 if start_of_line else data.rfind(b'\n', 0, i) + 1
        b = data.find(b'\n', i + 1)
        out.append(data[a:b if b != -1 else len(data)].decode())
        i = data.find(key, i + 1)
    return out


def secondary(acc):
    """Current primary accession(s) of a secondary accession (sec_ac.txt): one = merged, several = demerged (split)."""
    return [l.split()[1] for l in _lines(_raw('sec_ac.txt'), b'\n' + acc.encode() + b' ') if len(l.split()) == 2]


def deleted_sp():
    def build():
        f = REF / 'delac_sp.txt'
        return {l.strip() for l in open(f) if ACC.match(l.strip())} if f.exists() else set()
    return _once('delac', build)


def have_sifts():
    return _raw('pdb_chain_uniprot.tsv.gz') is not None


def sifts_rows(pdb=None, acc=None):
    """Local SIFTS segments (pdb_chain_uniprot.tsv.gz) of one PDB entry or of one accession:
    [(pdb, chain, acc, sp_beg, sp_end, pdb_beg, pdb_end)]. Cached per process (a copy, so callers may change it)."""
    return list(_sifts_rows(pdb, acc))


@lru_cache(maxsize=None)
def _sifts_rows(pdb, acc):
    data = _raw('pdb_chain_uniprot.tsv.gz')
    lines = _lines(data, b'\n' + pdb.lower().encode() + b'\t') if pdb else \
        _lines(data, b'\t' + acc.encode() + b'\t', start_of_line=False)
    out = []
    for line in lines:
        p = line.split('\t')
        if len(p) >= 9 and (pdb or p[2] == acc) and p[7].isdigit() and p[8].isdigit():
            out.append((p[0], p[1], p[2], int(p[7]), int(p[8]), p[5], p[6]))
    return tuple(out)


@lru_cache(maxsize=None)
def pdb_for_pmid(pmid):
    """PDB entries whose primary citation is this PMID (local SIFTS pdb_pubmed.tsv.gz, ordinal 0)."""
    if not pmid:
        return []
    return [l.split('\t')[0].upper() for l in _lines(_raw('pdb_pubmed.tsv.gz'), f'\t0\t{pmid}\n'.encode(), start_of_line=False)]


# ---------- identifiers printed in text ----------

ID_PATTERNS = [  # (kind, regex); earlier patterns win where two overlap
    ('uniparc', r'UPI[0-9A-F]{10}'),
    ('refseq_protein', r'(?:NP|XP|WP|YP|AP)_\d{5,9}(?:\.\d+)?'),
    ('refseq_nucleotide', r'(?:NM|XM|NR|XR|NC|NG|NT|NW|NZ)_[A-Z]{0,4}\d{5,9}(?:\.\d+)?'),
    ('pdb', r'pdb_0000([1-9][a-z0-9]{3})'),
    ('uniprot', r'(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})(?:-\d{1,2})?'),
    ('genbank_protein', r'[A-Z]{3}\d{5}(?:\d{2})?(?:\.\d+)?'),
    ('genbank_nucleotide', r'(?:[A-Z]\d{5}|[A-Z]{2}\d{6}|[A-Z]{2}\d{8})(?:\.\d+)?'),
    ('ncbi_gene', r'(?:Gene\s?ID:?\s*|LOC)(\d{3,10})'),
]
PDB_KEYWORD = re.compile(r'(?:\bPDB\b|Protein Data Bank)(?:[\s:#.,()\-]|\b(?:IDs?|codes?|entry|entries|accessions?|'
                         r'numbers?|no|file|structure|with|using|the|under)\b)*', re.I)
PDB_ID = re.compile(r'([1-9])\s?([A-Za-z0-9]{3})(?![A-Za-z0-9])')


def parse_ids(text, loose_pdb=True):
    """[(kind, id)] for every identifier in a string, in order of appearance, e.g.
    'PDB 1 sml' -> [('pdb', '1SML')]; 'XM_003593639.4, 9FCF, 9FCG' -> refseq_nucleotide + 2 pdb;
    'AAA22308.1' -> genbank_protein; 'MH000201' -> genbank_nucleotide; 'Gene ID: 11441829' -> ncbi_gene.
    A bare 4-character PDB code ('9FCF') counts only with loose_pdb (identifier fields); in running text the
    word PDB / Protein Data Bank must precede it ('PDB ID: 3LXU', 'PDB no: 4JU1, 4J0C')."""
    text = text or ''
    found, taken = [], [False] * len(text)

    def add(kind, ident, a, b):
        if not any(taken[a:b]):
            taken[a:b] = [True] * (b - a)
            found.append((a, kind, ident))
    for m in PDB_KEYWORD.finditer(text):  # 'PDB 1 sml', 'PDB ID: 3LXU', 'PDB no: 4JU1, 4J0C, 4J0D'
        i = m.end()
        while True:
            p = PDB_ID.match(text, i)
            if not p or not re.search(r'[A-Za-z]', p.group(2)):  # '2008' after 'PDB' is a year, not an entry
                break
            add('pdb', (p.group(1) + p.group(2)).upper(), p.start(), p.end())
            sep = re.match(r'\s*(?:,|;|and|&|/)\s*', text[p.end():])
            if not sep:
                break
            i = p.end() + sep.end()
    for kind, pat in ID_PATTERNS:
        for m in re.finditer(r'(?<![A-Za-z0-9_])' + pat + r'(?![A-Za-z0-9_])', text, flags=re.I if kind == 'pdb' else 0):
            ident = (m.group(1) if m.groups() and m.group(1) else m.group(0))
            add(kind, ident.upper() if kind == 'pdb' else ident, m.start(), m.end())
    if loose_pdb:
        for m in re.finditer(r'(?<![A-Za-z0-9_.])([1-9][A-Za-z0-9]{3})(?![A-Za-z0-9_])', text):
            if re.search(r'[A-Za-z]', m.group(1)[1:]):
                add('pdb', m.group(1).upper(), m.start(), m.end())
    out = []
    for _, kind, ident in sorted(found):
        if (kind, ident) not in out:
            out.append((kind, ident))
    return out


def _row_names(row):
    """The enzyme's own short names (gene, abbreviations) used to anchor IDs printed in the text."""
    names = []
    gene = row.get('gene') or ''
    enzyme = row.get('enzyme') or ''
    for part in [re.sub(r'\([^)]*\)', '', gene)] + re.findall(r'\(([^()]*)\)', enzyme) + [enzyme.split('(')[0]]:
        for n in re.split(r'[;,]\s*', part):
            n = n.strip()
            if len(n) >= 3 and re.search(r'[A-Za-z]', n) and n.lower() not in ('gene', 'enzyme', 'protein', 'wild type') \
                    and ('Gene ID' not in n) and n not in names:
                names.append(n)
    return names


def text_ids(text, names):
    """IDs the paper prints inside the parenthesis that directly follows one of the enzyme's own names, e.g.
    'CsDQD/SDHa (NCBI accession number: MH000201, 1,605 bp)' -> [('genbank_nucleotide', 'MH000201', quote)].
    IDs elsewhere in the text (homologs, search models) are never used."""
    out = []
    for name in names:
        for m in re.finditer(r'(?<![A-Za-z0-9])' + re.escape(name) + r'(?![A-Za-z0-9])', text or ''):
            j = m.end()
            while j < len(text) and text[j] in ' \t':
                j += 1
            if j >= len(text) or text[j] != '(':
                continue
            depth, k = 0, j
            while k < len(text) and k - j < 300:
                depth += {'(': 1, ')': -1}.get(text[k], 0)
                if depth == 0:
                    break
                k += 1
            if depth:
                continue
            for kind, ident in parse_ids(text[j + 1:k], loose_pdb=False):
                if kind != 'ncbi_gene' and not any(o[1] == ident for o in out):
                    out.append((kind, ident, text[m.start():k + 1]))
    return out


# ---------- UniProt / UniParc / NCBI lookups ----------

def _org_names(o):
    return [n for n in [o.get('scientificName', ''), o.get('commonName', '')] + o.get('synonyms', []) if n]


def search(query):
    """UniProt search (cached): [{'acc', 'reviewed', 'organism': [scientific name, common name, synonyms...]}]."""
    def fetch():
        raw = _get(f'{UNIPROT}/uniprotkb/search?format=json&size=25&fields=accession,reviewed,organism_name&query='
                   + urllib.parse.quote(query))
        if not raw:
            return []
        return [{'acc': r['primaryAccession'], 'reviewed': '(swiss-prot)' in r.get('entryType', '').lower(),
                 'organism': _org_names(r.get('organism', {}))} for r in json.loads(raw).get('results', [])]
    return _cached('search', query, fetch)


def entry(acc):
    """UniProt entry facts (REST .json, cached): status active / merged / demerged / deleted / missing, merge targets,
    UniParc id, reviewed, organism names, gene and protein names, N-terminal cleaved features, length."""
    def fetch():
        raw = _get(f'{UNIPROT}/uniprotkb/{acc}.json?fields=accession,organism_name,gene_names,protein_name,ft_signal,'
                   'ft_transit,ft_propep,ft_init_met,length')
        if raw is None:
            return {'status': 'missing'}
        d = json.loads(raw)
        ir = d.get('inactiveReason') or {}
        if d.get('primaryAccession') not in (None, acc):  # the server redirected a merged accession
            return {'status': 'merged', 'targets': [d['primaryAccession']]}
        if d.get('entryType') == 'Inactive':
            kind = (ir.get('inactiveReasonType') or 'DELETED').lower()
            return {'status': kind, 'targets': ir.get('mergeDemergeTo', []), 'reason': ir.get('deletedReason', ''),
                    'uniparc': d.get('extraAttributes', {}).get('uniParcId', '')}
        genes = [g[k]['value'] for g in d.get('genes', []) for k in ('geneName',) if k in g]
        genes += [x['value'] for g in d.get('genes', []) for k in ('synonyms', 'orderedLocusNames', 'orfNames') for x in g.get(k, [])]
        pd = d.get('proteinDescription', {})
        names = [n['fullName']['value'] for n in [pd.get('recommendedName', {})] + pd.get('alternativeNames', []) + pd.get('submissionNames', []) if n.get('fullName')]
        feats = [[f['type'], f['location']['start'].get('value'), f['location']['end'].get('value')] for f in d.get('features', [])]
        return {'status': 'active', 'reviewed': '(swiss-prot)' in d.get('entryType', '').lower(),
                'organism': _org_names(d.get('organism', {})), 'genes': genes, 'names': names, 'features': feats,
                'length': d.get('sequence', {}).get('length')}
    return _cached('entry', acc, fetch)


def check_active(acc):
    """{'acc': the current accession or '', 'status', 'note', 'uniparc'}. Swiss-Prot and sec_ac.txt answer offline;
    TrEMBL accessions need one REST call. MERGED into one entry -> that entry; DEMERGED / DELETED -> acc '' with the
    UniParc id, so the sequence the paper used can still be read."""
    base = acc.split('-')[0]
    if base in sprot():
        return {'acc': acc, 'status': 'active', 'note': '', 'uniparc': ''}
    prim = secondary(base)
    if len(prim) == 1:
        tgt = prim[0]
        if tgt in sprot() or entry(tgt)['status'] == 'active':
            return {'acc': tgt, 'status': 'merged', 'note': f'{base} merged into {tgt}', 'uniparc': ''}
    e = entry(base)
    if e['status'] == 'active':
        return {'acc': acc, 'status': 'active', 'note': '', 'uniparc': ''}
    if e['status'] == 'merged' and len(e['targets']) == 1 and check_active(e['targets'][0])['status'] == 'active':
        return {'acc': e['targets'][0], 'status': 'merged', 'note': f"{base} merged into {e['targets'][0]}", 'uniparc': ''}
    if e['status'] == 'missing':
        gone = 'deleted from Swiss-Prot (delac_sp.txt)' if base in deleted_sp() else 'no such UniProt entry'
        return {'acc': '', 'status': 'missing', 'note': f'{base}: {gone}', 'uniparc': ''}
    tg = e.get('targets') or prim
    why = {'demerged': f"split into {', '.join(tg)}", 'merged': f"merged into {', '.join(tg)}"}.get(e['status'], 'deleted')
    reason = f" ({e['reason']})" if e.get('reason') else ''
    return {'acc': '', 'status': e['status'], 'uniparc': e.get('uniparc', ''), 'targets': tg if why != 'deleted' else [],
            'note': f'{base}: UniProt entry {why}{reason}' + (f"; sequence from UniParc {e['uniparc']}" if e.get('uniparc') else '')}


def uniparc(dbid):
    """UniParc entries carrying a database ID (RefSeq/EMBL protein): [{'upi', 'accs', 'organism'}]."""
    def fetch():
        raw = _get(f'{UNIPROT}/uniparc/search?format=json&size=10&fields=upi,accession,organism&query='
                   + urllib.parse.quote(f'dbid:{dbid}'))
        if not raw:
            return []
        return [{'upi': r['uniParcId'], 'accs': sorted({a.split('.')[0] for a in r.get('uniProtKBAccessions', [])}),
                 'organism': [n for o in r.get('organisms', []) for n in _org_names(o)]} for r in json.loads(raw).get('results', [])]
    return _cached('uniparc', dbid, fetch)


def ncbi_cds(nuc):
    """[(protein_id, translation)] of the CDS features of a nucleotide accession (NCBI efetch fasta_cds_aa)."""
    def fetch():
        raw = _get(NCBI + f'efetch.fcgi?db=nuccore&id={urllib.parse.quote(nuc)}&rettype=fasta_cds_aa&retmode=text', gap=0.34)
        out = []
        for rec in (raw or b'').decode('utf-8', 'replace').split('>')[1:]:
            head, _, body = rec.partition('\n')
            pid = re.search(r'\[protein_id=([^\]]+)\]', head)
            out.append([pid.group(1) if pid else '', re.sub(r'\s+', '', body)])
        return out
    return _cached('ncbi_cds', nuc, fetch)


def ncbi_protein(pid):
    def fetch():
        raw = _get(NCBI + f'efetch.fcgi?db=protein&id={urllib.parse.quote(pid)}&rettype=fasta&retmode=text', gap=0.34)
        return ''.join((raw or b'').decode('utf-8', 'replace').split('\n', 1)[1:]).replace('\n', '') if raw else ''
    return _cached('ncbi_protein', pid, fetch)


def sequence(acc):
    """Sequence for a UniProt accession, an isoform 'ACC-n', a UniParc 'UPI...' or 'ncbi:<protein id>'.
    Local first (Swiss-Prot, isoforms, enrich/seq/, the 2026-08-26 bulk snapshot), then REST. '' when unknown;
    an empty 200 body (inactive entry) or a redirect to another accession (merged) is '' too, never a sequence."""
    if not acc:
        return ''
    if acc.startswith('ncbi:'):
        return ncbi_protein(acc[5:])
    if '-' in acc and acc in varsplic():
        return varsplic()[acc]
    if acc.endswith('-1') and acc[:-2] in sprot():  # isoform 1 not in varsplic: it is the displayed (canonical) one
        return sprot()[acc[:-2]][0]
    if acc in sprot():
        return sprot()[acc][0]
    f = SEQ_DIR / f'{acc}.fasta'
    if f.exists():
        return ''.join(f.read_text().splitlines()[1:]).strip()
    if acc in bulk_fasta():
        return bulk_fasta()[acc]
    url = f'{UNIPROT}/uniparc/{acc}.fasta' if acc.startswith('UPI') else f'{UNIPROT}/uniprotkb/{acc}.fasta'
    raw = _get(url)
    if not raw:
        return ''
    text = raw.decode()
    head = text.split('\n', 1)[0]
    if not acc.startswith('UPI') and f'|{acc}|' not in head:
        return ''  # the server answered with another entry (merged accession)
    SEQ_DIR.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    return ''.join(text.splitlines()[1:]).strip()


def uniprot_ecs(acc):
    """EC numbers of a UniProt entry: protein names and catalytic-activity reactions (cached)."""
    def fetch():
        raw = _get(f'{UNIPROT}/uniprotkb/{acc}.json?fields=ec,cc_catalytic_activity')
        d = json.loads(raw) if raw else {}
        pd = d.get('proteinDescription', {})
        ecs = [e['value'] for n in [pd.get('recommendedName', {})] + pd.get('alternativeNames', []) for e in n.get('ecNumbers', [])]
        ecs += [c['reaction'].get('ecNumber') for c in d.get('comments', []) if c.get('commentType') == 'CATALYTIC ACTIVITY']
        return sorted({e for e in ecs if e})
    return _cached('ec', acc, fetch)


def transferred_to(ec):
    """ECs an old EC number was transferred to (ExPASy ENZYME 'Transferred entry'), cached; [] for a current EC."""
    def fetch():
        raw = _get(f'https://enzyme.expasy.org/EC/{ec}.txt')
        de = ' '.join(l[5:] for l in (raw or b'').decode('utf-8', 'replace').splitlines() if l.startswith('DE'))
        return re.findall(r'\d+\.\d+\.\d+\.\d+', de) if 'Transferred entry' in de else []
    return _cached('ec_moved', ec, fetch)


def ec_conflict(acc, ec):
    """A warning when a name-matched entry carries other EC numbers than the paper (a sibling enzyme: product-specificity
    variant or paralog; or UniProt re-annotated it, as human ADH1B is now only EC 1.1.1.105), or '' when the paper's EC
    agrees with the entry, either has none, or the paper's EC is an old number transferred to one of the entry's."""
    if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', ec or '') or not acc:
        return ''
    have = uniprot_ecs(acc.split('-')[0])
    if not have or ec in have or set(transferred_to(ec)) & set(have):
        return ''
    return f'CHECK: {acc} carries EC {"; ".join(have)}, the paper says EC {ec} (sibling enzyme or re-annotation)'


# ---------- species ----------

def _species_level(names, org):
    """2: the entry's scientific name is the row's species; 1: a common name or synonym is; 0: neither."""
    want = genus_species(org)
    if not want or not names:
        return 0
    if genus_species(names[0]) == want:
        return 2
    return 1 if any(genus_species(n) == want for n in names[1:]) else 0


def _acc_level(acc, org):
    sp = sprot().get(acc.split('-')[0])
    if sp and _species_level([sp[1]], org) == 2:
        return 2
    e = entry(acc.split('-')[0])
    return _species_level(e.get('organism', []), org) if e['status'] == 'active' else 0


def _same_species(items, org):
    """items: [(acc, level)] -> the accessions at the best level > 0 (scientific-name matches beat synonym matches)."""
    best = max([lv for _, lv in items] + [0])
    out = []
    for a, lv in items:
        if best and lv == best and a not in out:
            out.append(a)
    return out


def _vague(org):
    gs = genus_species(org).split()
    return len(gs) < 2 or gs[1] in ('sp', 'spp', 'species')


# ---------- PDB ----------

def pdb_accs(pdb):
    """{accession: [chains]} that a PDB entry's chains map to (local SIFTS; UniProt xref:pdb- when not in the file).
    Cached per process (a copy is returned)."""
    return {k: list(v) for k, v in _pdb_accs(pdb).items()}


@lru_cache(maxsize=None)
def _pdb_accs(pdb):
    rows = sifts_rows(pdb=pdb) if have_sifts() else []
    if not rows:  # not in the local file (absent, or an entry newer than the file)
        return {h['acc']: [] for h in search(f'xref:pdb-{pdb.upper()}')}
    out = {}
    for _, chain, acc, *_ in rows:
        out.setdefault(acc, [])
        if chain not in out[acc]:
            out[acc].append(chain)
    return out


def pdb_residues(pdb):
    """Residue-level SIFTS for one structure (per-entry XML, cached as enrich/pdb/<id>.json):
    {chain: [[author number or None, PDB residue, UniProt acc, UniProt position or None, UniProt residue, observed]]}."""
    pdb = pdb.lower()
    if pdb in _local.setdefault('pdb_residues', {}):
        return _local['pdb_residues'][pdb]
    f = PDB_DIR / f'{pdb}.json'
    if f.exists():
        return _local['pdb_residues'].setdefault(pdb, json.loads(f.read_text()))
    raw = _get(f'{SIFTS_XML}{pdb[1:3]}/{pdb}.xml.gz')
    if raw is None:
        return {}
    out = {}
    for res in ET.fromstring(gzip.decompress(raw)).iter('{http://www.ebi.ac.uk/pdbe/docs/sifts/eFamily.xsd}residue'):
        p = u = None
        observed = 1
        for c in res:
            tag = c.tag.rsplit('}', 1)[-1]
            if tag == 'crossRefDb' and c.get('dbSource') == 'PDB' and p is None:
                p = c
            elif tag == 'crossRefDb' and c.get('dbSource') == 'UniProt' and u is None:
                u = c
            elif tag == 'residueDetail' and 'Not_Observed' in (c.text or ''):
                observed = 0
        if p is None:
            continue
        num = p.get('dbResNum')
        out.setdefault(p.get('dbChainId'), []).append([
            None if num in (None, 'null') else num, AA1.get(p.get('dbResName', ''), 'X'),
            u.get('dbAccessionId') if u is not None else '',
            int(u.get('dbResNum')) if u is not None and (u.get('dbResNum') or '').isdigit() else None,
            u.get('dbResName', '') if u is not None else '', observed])
    PDB_DIR.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out))
    return _local['pdb_residues'].setdefault(pdb, out)


def author_map(pdb, chain, acc):
    """Author residue number (plain integers; insertion codes skipped) -> UniProt position of acc."""
    base = acc.split('-')[0]
    return {int(r[0]): r[3] for r in pdb_residues(pdb).get(chain, [])
            if r[0] and r[0].lstrip('-').isdigit() and r[3] and r[2].split('-')[0] == base}


# ---------- find_protein ----------

GENERIC_NAME_WORDS = {'specific', 'mitochondrial', 'cytoplasmic', 'cytosolic', 'chloroplastic', 'peroxisomal', 'microsomal',
                      'plastidic', 'periplasmic'}


def _own_name_first(accs, name, gs, org):
    """The protein-name search also matches UniProt's alternative names: rat LCAD (P15650, 'Long-chain specific acyl-CoA
    dehydrogenase') lists 'Medium-chain acyl-CoA dehydrogenase' as one, and the exact phrase misses rat MCAD (P08503,
    'Medium-chain specific acyl-CoA dehydrogenase'), so PMID 3968063's MCAD got LCAD. When no hit carries the paper's
    name words in its own (recommended) name, a same-species reviewed entry whose recommended name is exactly those
    words (plus 'specific', 'mitochondrial', ...) wins; otherwise the hits stand (a paper may use an alternative name:
    'aldose reductase' for AKR1B1)."""
    words = lambda s: set(re.findall(r'[a-z0-9]+', (s or '').lower().translate(GREEK)))  # every word: PPi vs ATP, cd1, 3 vs 1
    own_name = lambda a: words((entry(a).get('names') or [''])[0])
    want = words(name)
    if not want or any(want <= own_name(a) for a in accs):
        return accs
    hits = search(' AND '.join(f'protein_name:{w}' for w in sorted(want)) + f' AND organism_name:"{gs}" AND reviewed:true')
    same = _same_species([(h['acc'], _species_level(h['organism'], org)) for h in hits], org)
    own = [a for a in same if own_name(a) - GENERIC_NAME_WORDS == want]
    return own if len(own) == 1 else accs


def _result(acc='', how='', candidates=(), uniparc='', seq_ref=None, seq_how=''):
    return {'acc': acc, 'how': how, 'candidates': list(candidates), 'pdb': [], 'uniparc': uniparc,
            'seq_ref': acc if seq_ref is None else seq_ref, 'seq_how': seq_how}


def _settle(accs, how):
    """One accession -> it. Several -> no accession; the sequence is still usable when all are identical."""
    accs = list(dict.fromkeys(accs))
    if len(accs) == 1:
        return _result(accs[0], how)
    seqs = {a: sequence(a) for a in accs[:8]}
    if len(accs) <= 8 and all(seqs.values()) and len(set(seqs.values())) == 1:
        n = len(next(iter(seqs.values())))
        return _result('', f'{how}: ambiguous ({", ".join(accs)})', accs, seq_ref=accs[0],
                       seq_how=f'all {len(accs)} same-species candidates have the identical {n}-aa sequence; sequence of {accs[0]} used')
    return _result('', f'{how}: ambiguous ({", ".join(accs[:6])})', accs[:6])


def _active_same_species(accs, org):
    items = []
    for a in accs:
        st = check_active(a)
        if st['acc']:
            items.append((st['acc'], _acc_level(st['acc'], org)))
    return _same_species(items, org)


def _from_id(kind, ident, org, label, unchecked_cds=True):
    """Route one printed ID (not UniProt, not PDB) to a result, or None. unchecked_cds=False: no last-resort translation
    of a lone CDS (it has no species check), for IDs found only by scanning the text: 11900558's scan found the
    Thermococcus BglB GenBank entry of a figure legend, 18230605's the human BHMT-2 cDNA for the mouse enzyme."""
    base = ident.split('.')[0]
    if kind == 'ncbi_gene':
        queries = [f'xref:geneid-{ident}']
    elif kind == 'refseq_protein':
        queries = [f'xref:refseq-{ident}'] + ([f'xref:refseq-{base}'] if base != ident else [])
    elif kind == 'refseq_nucleotide':
        queries = [f'xref:refseq-{ident}']
    else:
        queries = [f'xref:embl-{base}']
    for q in queries:
        hits = search(q)
        same = _same_species([(h['acc'], _species_level(h['organism'], org)) for h in hits], org)
        if same:
            return _settle(same, f'{label} -> {q} (same species)')
    proteins = [ident] if kind in ('refseq_protein', 'genbank_protein') else []
    if kind in ('refseq_nucleotide', 'genbank_nucleotide'):
        cds = ncbi_cds(ident)  # only a record with one CDS names the protein: in a genome segment the first CDS that maps
        proteins = [p for p, _ in cds if p] if len(cds) == 1 else []  # is any gene (11900558: AP000002 -> PurT for BglB)
    for pid in proteins:
        for q in [f'xref:embl-{pid.split(".")[0]}', f'xref:refseq-{pid}'] if pid != ident else []:
            hits = search(q)
            same = _same_species([(h['acc'], _species_level(h['organism'], org)) for h in hits], org)
            if same:
                return _settle(same, f'{label} -> NCBI CDS {pid} -> {q} (same species)')
        for rec in uniparc(pid.split('.')[0]):
            if _species_level(rec['organism'], org) == 0:
                continue
            same = _active_same_species(rec['accs'], org)
            via = f'{label} -> ' + (f'NCBI CDS {pid} -> ' if pid != ident else '') + f'UniParc {rec["upi"]} (dbid:{pid.split(".")[0]})'
            if len(same) == 1:
                return _result(same[0], f'{via} -> {same[0]} (same species)')
            if same:
                return _result('', f'{via}: ambiguous ({", ".join(same)})', same, seq_ref=rec['upi'],
                               seq_how=f'{", ".join(same)} all carry the UniParc {rec["upi"]} sequence')
            return _result('', f'{via}: no active UniProt entry', [], uniparc=rec['upi'], seq_ref=rec['upi'],
                           seq_how=f'UniParc {rec["upi"]} (no active UniProt entry)')
    if unchecked_cds and kind in ('refseq_nucleotide', 'genbank_nucleotide') and len(cds) == 1 and cds[0][0] and cds[0][1]:
        return _result('', f'{label}: no UniProt or UniParc entry', [], seq_ref=f'ncbi:{cds[0][0]}',
                       seq_how=f'translation of NCBI CDS {cds[0][0]} (the only CDS of {ident})')
    return None


PEPTIDE_MAX = 30  # an entry no chain maps more residues of is a bound peptide (or a short fused segment), never the enzyme


def _peptides(pdb):
    """{accession: (chains, residues)} for the UniProt entries of which no chain of a PDB entry maps more than
    PEPTIDE_MAX residues (local SIFTS): a bound substrate or inhibitor peptide, or a few residues of another protein
    fused into a construct. 24634223 prints 4C1Q, mouse PRDM9 with residues 2-11 of human histone H3 (chain C); the
    species filter dropped the mouse enzyme and gave human PRDM9 the histone."""
    span = {}
    for _, chain, acc, beg, end, *_ in sifts_rows(pdb=pdb) if have_sifts() else []:
        span.setdefault(acc, {}).setdefault(chain, 0)
        span[acc][chain] += end - beg + 1
    return {a: (sorted(c), max(c.values())) for a, c in span.items() if max(c.values()) <= PEPTIDE_MAX}


def _from_pdbs(pdbs, org, label, notes=None):
    """The same-species entry the PDB entries' chains map to. Entries only short chains map (_peptides) are left out;
    one of the row's species is named in notes, when given."""
    accs, chains = [], {}
    for p in pdbs:
        pep = _peptides(p)
        for a, ch in pdb_accs(p).items():
            if a in pep:
                if notes is not None and _acc_level(a, org):
                    notes.append(f'PDB {p} chain {",".join(pep[a][0])} maps at most {pep[a][1]} residues of {a}, '
                                 f'too short to be the enzyme')
                continue
            accs.append((a, _acc_level(a, org)))
            chains.setdefault(a, []).append(f'{p}' + (f' chain {",".join(ch)}' if ch else ''))
    same = _same_species(accs, org)
    if not same:
        return None
    src = 'SIFTS' if have_sifts() else 'UniProt xref:pdb-'
    if len(same) == 1:
        return _result(same[0], f'{src}: PDB {"; ".join(chains[same[0]])} -> {same[0]} ({label}; same species)')
    return _settle(same, f'{src}: PDB {", ".join(pdbs)} ({label})')


def _tokens(*strings):
    stop = {'protein', 'enzyme', 'putative', 'uncharacterized', 'subunit', 'domain', 'family', 'chain', 'probable',
            'fragment', 'type', 'like', 'with', 'from', 'bifunctional'}
    return {t for s in strings for t in re.findall(r'[a-z0-9_]{4,}', (s or '').lower().translate(GREEK)) if t not in stop}


def _is_entry_of(e, row):
    """The entry is this row's enzyme by name: one of the row's genes ('GapA, GapB', 'AtGH3.5/WES1') is one of its
    genes, or every word of the enzyme's name outside parentheses is in one of its names. One shared family word
    ('glutathione', 'esterase') is not enough: 10652317's GSTM1 and GSTM4 are not GSTM2."""
    words = lambda s: set(re.findall(r'[a-z0-9]+', (s or '').lower().translate(GREEK)))
    genes = {g.lower() for g in e.get('genes', [])}
    if any(g in genes for g in re.split(r'[\s,;/]+', re.sub(r'\([^)]*\)', ' ', row.get('gene') or '').lower()) if g):
        return True
    want = words(re.sub(r'\([^)]*\)', ' ', row.get('enzyme') or ''))
    return bool(want) and any(want <= words(n) for n in e.get('names', []))


def _successors_other(accs, row):
    """[] unless the active entries a retired printed accession was split into (accs) are all another protein: none is
    the row's enzyme by gene or name, and none shares a name word with it. Then ['acc gene', ...], and the retired
    entry's UniParc sequence is not the enzyme's either: 31314509 prints 'YdjH (Uniprot ID: P77492)', a retired
    accession of the permease BrnQ (P0AD99, P0ADA0), for the sugar kinase YdjH (P77493)."""
    own = _tokens(row.get('gene'), row.get('enzyme'))
    if not own and not (row.get('gene') or '').strip():
        return []  # nothing to compare with
    named = []
    for a in accs:
        e = entry(a)
        if e.get('status') != 'active':
            continue
        if _is_entry_of(e, row) or _tokens(*(e.get('genes', []) + e.get('names', []))) & own:
            return []
        named.append(f"{a} {(e.get('genes') or e.get('names') or ['?'])[0]}")
    return named


def unshare_cited(ids, paper_keys):
    """Route 5 gives the entry of the structure a paper solved to its sibling enzymes (30083226: OtCE15B-D got OtCE15A's
    entry; 18342636: the liver hSDH got the cancer-cell cSDH). ids: enrich/protein.json; paper_keys: {pmid: the ident
    keys of its rows}. A route-5 accession that another enzyme of the same paper also holds stays only when the entry is
    this enzyme by name (_is_entry_of); otherwise acc and sequence are blanked, the reason in 'how'. Keys that differ
    only in printed IDs are one enzyme (19159229's dCK with and without 3EXK). Returns the keys blanked."""
    def enzyme(k):  # an ident key is 'uniprot|protein_ids|gene|enzyme|organism'
        return k.split('|', 2)[-1]
    route5 = lambda v: 'primary citation of PDB' in v.get('how', '')
    holders = {}  # (pmid, acc) -> {enzyme: found only by route 5}
    for pmid, keys in paper_keys.items():
        for k in keys:
            v = ids.get(k) or {}
            if v.get('acc'):
                h = holders.setdefault((pmid, v['acc']), {})
                h[enzyme(k)] = h.get(enzyme(k), True) and route5(v)
    out = []
    for pmid, keys in paper_keys.items():
        for k in sorted(keys):
            v = ids.get(k) or {}
            if not v.get('acc') or not route5(v):
                continue
            # the paper's other enzymes holding this accession; one that holds it by another route is named first
            others = sorted((r5, e) for e, r5 in holders[(pmid, v['acc'])].items() if e != enzyme(k))
            if not others:
                continue
            p = k.split('|')
            try:
                if _is_entry_of(entry(v['acc'].split('-')[0]), {'gene': p[2], 'enzyme': '|'.join(p[3:-1])}):
                    continue
            except RuntimeError:
                continue  # entry not fetched: decided next run
            other = others[0][1].split('|')[1][:60]
            v.update(acc='', seq_ref='', seq_how='', pdb=[], candidates=[], uniparc='',
                     how=f"{v['how']}; not used: in PMID {pmid} {v['acc']} is also '{other}', and neither its genes "
                         f"nor its names are this enzyme's")
            v.pop('ec', None)
            out.append(k)
    return out


@lru_cache(maxsize=None)
def _paper_text(pmid):
    parts = [TEXTS / f'{pmid}.txt', TEXTS / f'{pmid}.supp.txt']
    return '\n'.join(p.read_text(errors='replace') for p in parts if p.exists())


def find_protein(row, text=None):
    """{'acc', 'how', 'candidates', 'pdb', 'uniparc', 'seq_ref', 'seq_how'} for one catalog row.
    acc: active UniProt accession or ''. pdb: PDB entries (printed, or citing the paper) that map to acc, for
    variant_sequence() and construct(). seq_ref: what sequence() should read ('' = none): acc, a UniParc id for a
    deleted/split entry, the first of several identical-sequence candidates, or 'ncbi:<protein id>'.
    text: the paper text for the name-anchored ID route; None reads texts/<PMID>.txt, '' skips the route."""
    org = row.get('organism') or ''
    pmid = str(row.get('pmid') or '')
    printed = parse_ids(row.get('uniprot') or '') + parse_ids(row.get('protein_ids') or '')
    printed += [i for i in parse_ids(row.get('gene') or '', loose_pdb=False) if i[0] == 'ncbi_gene' and i not in printed]
    printed_pdbs = [i for k, i in printed if k == 'pdb']
    res, notes = None, []
    # 1. printed UniProt accession(s), checked active and same species
    ups = [i for k, i in printed if k == 'uniprot']
    if ups:
        good = []
        for a in ups:
            st = check_active(a)
            if st['acc'] and _acc_level(st['acc'], org):
                good.append((st['acc'], st['note']))
            elif st['acc']:
                b = st['acc'].split('-')[0]
                other = (sprot().get(b) or ('', ''))[1] or ', '.join(entry(b).get('organism', [])[:1])
                notes.append(f"printed {a}{' (' + st['note'] + ')' if st['note'] else ''} is {other}, not {org}: not used")
            elif st['uniparc'] and len(ups) == 1:
                other = _successors_other(st.get('targets', []), row)
                if other:
                    notes.append(f"printed {st['note'].split('; sequence from UniParc')[0]}, whose entries are not "
                                 f"{row.get('gene') or row.get('enzyme')} ({'; '.join(other)}): not used")
                else:
                    res = _result('', f"printed {st['note']}", [], uniparc=st['uniparc'], seq_ref=st['uniparc'],
                                  seq_how=f"UniParc {st['uniparc']}: the sequence of the printed, now inactive entry {a}")
            else:
                notes.append(f"printed {st['note']}")
        accs = list(dict.fromkeys(a for a, _ in good))
        if len(accs) == 1:
            res = _result(accs[0], 'printed in paper' + ''.join(f'; {n}' for _, n in good if n))
        elif accs:
            res = _settle(accs, 'several printed accessions')
    # 2. printed PDB -> local SIFTS
    if (res is None or not res['seq_ref']) and printed_pdbs:
        res = _from_pdbs(printed_pdbs, org, 'printed in paper', notes) or res
    # 3. printed GenBank / EMBL / RefSeq / NCBI Gene ID
    if res is None or not res['seq_ref']:
        for kind, ident in printed:
            if kind in ('uniprot', 'pdb'):
                continue
            r = _from_id(kind, ident, org, f'printed {ident}')
            if r and r['seq_ref']:
                res = r
                break
            res = res or r
    # 4. an ID printed in parentheses right after the enzyme's own name in the paper
    if res is None or not res['seq_ref']:
        text = _paper_text(pmid) if text is None else text
        for kind, ident, quote in text_ids(text, _row_names(row)) if text else []:
            label = 'printed in the text: "' + (quote if len(quote) <= 110 else quote[:quote.find(ident) + len(ident)] + ' ...') + '"'
            if kind == 'pdb':
                r = _from_pdbs([ident], org, label)
            elif kind == 'uniprot':
                st = check_active(ident)
                r = _result(st['acc'], f"{label} -> {st['acc']} (same species)" + (f"; {st['note']}" if st['note'] else '')) \
                    if st['acc'] and _acc_level(st['acc'], org) else None
            elif kind == 'uniparc':
                r = None
            else:
                r = _from_id(kind, ident, org, label, unchecked_cds=False)
            if r and r['seq_ref']:
                res = r
                break
    # 5. PDB entries whose primary citation is this paper (same species, unique, and the entry names this enzyme)
    cited = pdb_for_pmid(pmid) if pmid else []
    if (res is None or not res['seq_ref']) and cited:
        r = _from_pdbs(cited, org, f'primary citation of PDB {", ".join(cited[:6])} is this paper')
        if r and r['acc']:
            e = entry(r['acc'])
            if (row.get('gene') or '').strip() and not _is_entry_of(e, row):  # the paper solved another of its enzymes
                notes.append(f"PDB citing this paper maps to {r['acc']}, which is not gene {row['gene'].strip()}: not used")
            elif _tokens(*(e.get('genes', []) + e.get('names', []))) & _tokens(row.get('gene'), row.get('enzyme')):
                res = r
                why = ec_conflict(r['acc'], (row.get('ec') or '').strip())
                if why:
                    notes.append(why)
            else:
                notes.append(f"PDB citing this paper maps to {r['acc']}, whose names do not match the enzyme: not used")
    # 6. names: gene, protein name, EC + organism (same species only; never for a genus-level organism like 'Bacillus sp.')
    if (res is None or not res['seq_ref']) and org and not _vague(org):
        gs = genus_species(org)
        gene = re.sub(r'\([^)]*\)', '', row.get('gene') or '').strip()
        name = re.sub(r'\s*\([^)]*\)', '', row.get('enzyme') or '').strip().translate(GREEK)
        ec = (row.get('ec') or '').strip()
        cands = []
        if gene and ' ' not in gene:
            hits = search(f'gene_exact:"{gene}" AND organism_name:"{gs}"')
            same = _same_species([(h['acc'], _species_level(h['organism'], org)) for h in hits], org)
            rev = [a for a in same if any(h['acc'] == a and h['reviewed'] for h in hits)]
            pool = rev or same
            if len(pool) == 1:
                kind = 'reviewed' if rev else 'unreviewed'
                res = _result(pool[0], f'gene {gene} + organism, unique {kind} entry')
            elif pool:
                res = _settle(pool, f'gene {gene} + organism')
                cands = pool
        for label, q in (('protein name', f'protein_name:"{name}"' if len(name) > 3 else ''),
                         ('EC', f'ec:{ec}' if re.fullmatch(r'\d+\.\d+\.\d+\.\d+', ec) else '')):
            if not q or (res and res['seq_ref']):
                continue
            hits = search(f'{q} AND organism_name:"{gs}" AND reviewed:true')
            same = _same_species([(h['acc'], _species_level(h['organism'], org)) for h in hits], org)
            if label == 'protein name' and same:
                same = _own_name_first(same, name, gs, org)
            if label == 'EC' and cands:  # gene/name found candidates: an EC hit that is none of them and shares no word
                own = _tokens(row.get('gene'), row.get('enzyme'))  # with the paper's name is another protein (PMID 1339268:
                other = [a for a in same if a not in cands      # lung PGFS, then EC 1.1.1.2, got aldehyde reductase AKR1A1)
                         and not _tokens(*(entry(a).get('genes', []) + entry(a).get('names', []))) & own]
                if other:
                    notes.append(f"EC {ec} + organism gives {', '.join(other[:4])}, whose names share no word with "
                                 f"'{row.get('enzyme', '')[:60]}' and which no name search found: not used")
                    same = [a for a in same if a not in other]
            if len(same) == 1:
                res = _result(same[0], f'{label} + organism, unique reviewed entry')
            cands += [a for a in same if a not in cands]
        if cands and not (res and res['seq_ref']):
            fit = [a for a in cands if not ec_conflict(a, ec)]  # siblings with another EC drop out of a tie
            if fit and len(fit) < len(cands):
                res = _result(fit[0], f'gene / protein name + organism, the only candidate with EC {ec}') if len(fit) == 1 \
                    else _settle(fit, f'ambiguous (gene / protein name + organism, EC {ec})')
            else:
                res = _settle(cands, 'ambiguous (gene / protein name / EC + organism)')
        why = ec_conflict(res['acc'], ec) if res and res['acc'] else ''
        if why:
            notes.append(why)
    if res is None:
        res = _result('', 'not found (no usable printed ID; gene, protein name and EC + organism gave nothing unique)')
    if notes:
        res['how'] += ''.join(f'; {n}' for n in notes)
    if res['acc']:  # structures of this very protein: printed ones first, then those whose primary citation is the paper
        base = res['acc'].split('-')[0]
        res['pdb'] = [p for p in dict.fromkeys(printed_pdbs + cited) if base in pdb_accs(p)]
    return res


# ---------- variants and numbering frames ----------

DEL = re.compile(r'(?:Δ|∆|\bdel(?:eted|etion)?\s*|\bdelta\s*)\(?\s*([A-Z])?(\d{1,4})\s*[-–—_]\s*([A-Z])?(\d{1,4})\s*\)?')
CODON = {a + b + c: 'FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG'[16 * i + 4 * j + k]
         for i, a in enumerate('TCAG') for j, b in enumerate('TCAG') for k, c in enumerate('TCAG')}


def _translate(dna):
    return ''.join(CODON.get(dna[i:i + 3], 'X') for i in range(0, len(dna) - 2, 3))


def _revcomp(dna):
    return dna[::-1].translate(str.maketrans('ACGT', 'TGCA'))


def split_variant(variant):
    """(wild_type, [(wt, pos, new)], [(start, end, wt_start or '', wt_end or '')], leftover) for a variant string;
    deletions like 'Δ74-80', 'del74-80', 'Δ(74–80)'."""
    v = variant or ''
    dels = [(int(m.group(2)), int(m.group(4)), m.group(1) or '', m.group(3) or '') for m in DEL.finditer(v)]
    v2 = DEL.sub(' ', v) if dels else v
    if dels and not v2.strip(' ,;+/'):
        return False, [], dels, ''
    wt, muts, rest = parse_variant(v2)
    return wt and not dels, muts, dels, rest


def primer_anchor(text, mutations, seq):
    """{(wt, printed position): position in seq} when the paper's printed mutagenic primers place EVERY one of its
    mutations: each primer whose label names the mutation (e.g. 'Y228AFor | CTgAgTgCACC...') is translated in all
    six frames; the peptide carrying the mutant residue, with the wild-type residue put back, must occur exactly once
    in seq (>= 9 aa). Returns (mapping or None, note)."""
    want = {}
    for a, p, b in mutations:
        want.setdefault((a, p), set()).add(b)
    dna_re = re.compile(r'(?<![A-Za-z])[ACGTacgt](?:[ \-]?[ACGTacgt]){14,}(?![A-Za-z])')
    lab_re = re.compile(r'(?<![A-Za-z0-9])([ACDEFGHIKLMNPQRSTVWY])(\d{1,4})([ACDEFGHIKLMNPQRSTVWY*])(?!\d)')
    primers = {}
    lines = (text or '').splitlines()
    for i, line in enumerate(lines):
        dnas = dna_re.findall(line)
        head = dna_re.split(line)[0] if dnas else line
        for three, one in AA3.items():
            head = re.sub(rf'{three}(?=\d)|(?<=\d){three}', one, head)
        labs = {(a, int(p), b) for a, p, b in lab_re.findall(head) if (a, int(p)) in want and b in want[(a, int(p))]}
        if len(labs) != 1:
            continue
        if not dnas and i + 1 < len(lines) and not lab_re.search(lines[i + 1]):
            dnas = dna_re.findall(lines[i + 1])
        for d in dnas:
            primers.setdefault(next(iter(labs)), []).append(re.sub(r'[ \-]', '', d).upper())
    found, bad = {}, []
    for (a, p), news in sorted(want.items(), key=lambda x: x[0][1]):
        us = set()
        for b in news:
            for dna in primers.get((a, p, b), []):
                for strand in (dna, _revcomp(dna)):
                    for f in range(3):
                        pep = _translate(strand[f:])
                        for k, ch in enumerate(pep):
                            if ch != b:
                                continue
                            lo, hi = k, k + 1
                            while lo > 0 and pep[lo - 1] not in '*X':
                                lo -= 1
                            while hi < len(pep) and pep[hi] not in '*X':
                                hi += 1
                            w = pep[lo:k] + a + pep[k + 1:hi]
                            if len(w) < 9:
                                continue
                            hits = [m.start() for m in re.finditer(f'(?={re.escape(w)})', seq)]
                            if len(hits) == 1:
                                us.add(hits[0] + (k - lo) + 1)
        if len(us) == 1:
            found[(a, p)] = us.pop()
        else:
            bad.append(f'{a}{p}' + (' (no printed primer)' if not any(primers.get((a, p, b)) for b in news) else
                                    ' (primers place it nowhere)' if not us else ' (primers place it at several positions)'))
    if bad:
        return None, 'primer anchor failed: ' + ', '.join(bad)
    return found, ', '.join(f'{a}{p} = UniProt {a}{u}' for (a, p), u in sorted(found.items(), key=lambda x: x[0][1]))


def _label(acc):
    if acc.startswith('UPI'):
        return f'UniParc {acc} sequence'
    if acc.startswith('ncbi:'):
        return f'NCBI {acc[5:]} sequence'
    if '-' in acc:
        return f'UniProt isoform {acc}'
    return 'UniProt canonical'


def _frames(acc, pdb_ids, positions, weak):
    """Candidate numbering frames, best first: (label, {printed position: position in seq}, seq, strength).
    strength True: printed structure or canonical, enough on its own. None: an isoform, chosen only when the paper
    prints >= 2 distinct positions (one residue can match by chance), but listed as corroboration. False: mature
    chain after cleaved N-terminal segments and other PDB chains of the accession, offered only when weak=True
    (>= 2 distinct positions); they cost REST/SIFTS calls, so they are never scanned just to corroborate."""
    canon = sequence(acc)
    base = acc.split('-')[0]
    for pdb in pdb_ids:
        for chain in pdb_accs(pdb).get(base, []) or list(pdb_residues(pdb)):
            m = author_map(pdb, chain, base)
            if m:
                yield f'PDB {pdb.upper()} chain {chain} author numbering', {p: m.get(p) for p in positions}, canon, True
    yield _label(acc), {p: p for p in positions}, canon, True
    if acc.startswith(('UPI', 'ncbi:')) or '-' in acc:
        return
    for iso in isoforms(base):
        yield f'UniProt isoform {iso}', {p: p for p in positions}, varsplic()[iso], None
    if not weak:
        return
    cur = 0
    for t, s, end in sorted((f for f in entry(base).get('features', []) if f[0] in
                             ('Initiator methionine', 'Signal', 'Transit peptide', 'Propeptide')), key=lambda f: f[1] or 0):
        if s in (1, cur + 1) and end:  # only cleaved segments that start the chain, one after the other
            cur = end
            yield f'mature chain after the {t.lower()} {s}-{end} (+{end})', {p: p + end for p in positions}, canon, False
    cover = {}  # (pdb, chain) -> [lowest, highest author number, UniProt residues covered]
    for p, chain, a, sb, se, pb, pe in sifts_rows(acc=base):
        c = cover.setdefault((p, chain), [10 ** 9, -10 ** 9, 0])
        lo, hi = re.match(r'-?\d+', pb or ''), re.match(r'-?\d+', pe or '')
        c[0] = min(c[0], int(lo.group()) if lo else -10 ** 9)
        c[1] = max(c[1], int(hi.group()) if hi else 10 ** 9)
        c[2] += se - sb + 1
    done, n = {p.lower() for p in pdb_ids}, 0
    for (p, chain), (lo, hi, _) in sorted(cover.items(), key=lambda kv: (-kv[1][2], kv[0])):
        if p in done or n >= OTHER_PDB_MAX or not all(lo <= q <= hi for q in positions):
            continue
        done.add(p)
        n += 1
        m = author_map(p, chain, base)
        yield f'PDB {p.upper()} chain {chain} author numbering', {q: m.get(q) for q in positions}, canon, False


def _fits(mapping, seq, checks):
    return bool(seq) and all(mapping.get(p) and 0 < mapping[p] <= len(seq) and seq[mapping[p] - 1] == a for a, p in checks)


_frame_memo = {}


def choose_frame(acc, mutations, positions, pdb_ids=(), text=''):
    """The first frame under which every printed wild-type residue of the paper matches, else the primer anchor.
    mutations: [(wt, pos, new)]; positions: every printed position to place (deleted residues too).
    Returns (label, {printed position: position in seq}, seq, note) or (None, None, '', why)."""
    checks = sorted({(a, p) for a, p, _ in mutations})
    key = (acc, tuple(sorted(mutations)), tuple(sorted(positions)), tuple(pdb_ids), hash(text or ''))
    if key in _frame_memo:
        return _frame_memo[key]
    out = (None, None, '', 'no frame')
    if not checks:  # a deletion alone: UniProt numbering, unless a printed structure numbers these residues otherwise
        agree = []
        for label, mapping, seq, strong in _frames(acc, list(pdb_ids), sorted(positions), False):
            if label.startswith('PDB'):
                if all(mapping.get(p) for p in positions):
                    if any(mapping[p] != p for p in positions):
                        out = (None, None, '', f'{label} numbers these residues differently from {_label(acc)} '
                                               f'and no printed residue decides')
                        break
                    if not any(a.startswith(label.split(' chain ')[0] + ' ') for a in agree):
                        agree.append(label.replace(' author numbering', ''))
                continue
            if all(0 < p <= len(seq) for p in positions):
                out = (label, mapping, seq, 'no printed residue to check the numbering' +
                       (f"; {', '.join(agree)} number{'s' if len(agree) == 1 else ''} these residues the same" if agree else ''))
            break
        _frame_memo[key] = out
        return out
    tried, chosen, also, single = [], None, [], []
    several = len({p for _, p in checks}) >= 2
    for label, mapping, seq, strong in _frames(acc, list(pdb_ids), sorted(positions), several):
        ok = _fits(mapping, seq, checks) and all(mapping.get(p) for p in positions)
        if chosen:
            if strong is False:
                break
            if ok and not any(x.startswith(label.split(' chain ')[0] + ' ') for x in [chosen[0]] + also):
                also.append(label)
            continue
        tried.append(label)
        if ok and not (strong or several):
            single.append(label)
        elif ok:
            chosen = (label, mapping, seq)
            if not label.startswith('PDB'):
                break
    if chosen:
        label, mapping, seq = chosen
        if label.startswith('PDB') and seq == sequence(acc) and all(mapping[p] == p for p in positions):
            out = (_label(acc), mapping, seq, f"printed {label.replace(' author numbering', '')} numbers them the same")
        elif label.startswith('PDB') and _label(acc) in also:
            out = (None, None, '', f'{label} and {_label(acc)} both fit with different positions: ambiguous')
        else:
            out = (label, mapping, seq, ('also fits ' + ', '.join(also)) if also else '')
    else:
        pdbs = [t for t in tried if t.startswith('PDB')]
        listed = [t for t in tried if not t.startswith('PDB')] + pdbs[:3]
        why = 'frames tried: ' + ', '.join(listed) + (f' and {len(pdbs) - 3} more PDB chains' if len(pdbs) > 3 else '')
        if single:
            why += f"; {', '.join(single)} fit{'s' if len(single) == 1 else ''} the one printed position, not enough on its own"
        canon = sequence(acc)
        if text and canon:
            m, note = primer_anchor(text, mutations, canon)
            m = {p: u for (a, p), u in (m or {}).items()}
            if m and all(p in m for p in positions):
                out = (f"the paper's printed mutagenesis primers ({note})", m, canon, why.replace('frames tried', 'no frame fits'))
            else:
                out = (None, None, '', f'{why}; {note}')
        else:
            out = (None, None, '', why)
    _frame_memo[key] = out
    return out


def variant_sequence(acc, variant, pmid=None, paper_mutations=None, pdb_ids=(), text=None):
    """{'sequence', 'check', 'frame'} for one measured variant. acc: what find_protein() calls seq_ref (accession,
    isoform, UniParc id). paper_mutations: every (wt, pos, new) the paper prints for this protein; ONE frame must fit
    them all. Point mutations, deletions ('Δ74-80') and nonsense truncation are applied; any other construct text is
    not ('construct not applied'). text: paper text for the primer anchor (None reads texts/<PMID>.txt + .supp.txt)."""
    canon = sequence(acc) if acc else ''
    if not canon:
        return {'sequence': '', 'check': 'no sequence (no UniProt accession)', 'frame': ''}
    wt, muts, dels, rest = split_variant(variant)
    if wt:
        return {'sequence': canon, 'check': f'wild type: {_label(acc)} sequence', 'frame': _label(acc)}
    if rest or not (muts or dels):
        return {'sequence': '', 'check': f'construct not applied ({variant})', 'frame': ''}
    paper = set(paper_mutations or []) | set(muts)
    for s0, e, ws, we in dels:  # residues printed with a deletion ('ΔE74-K80') are checked like wild-type residues
        paper |= {(w, p, '-') for w, p in ((ws, s0), (we, e)) if w}
    positions = {p for _, p, _ in paper} | {p for s0, e, *_ in dels for p in range(s0, e + 1)}
    if text is None and pmid:
        text = _paper_text(pmid)
    base = acc.split('-')[0]
    pdbs = list(dict.fromkeys([p.upper() for p in pdb_ids or []] +
                              [p for p in (pdb_for_pmid(pmid) if pmid else []) if base in pdb_accs(p)]))
    label, mapping, seq, note = choose_frame(acc, sorted(paper), positions, pdbs, text or '')
    if label is None:
        bad = [f'{a}{p} ({_label(acc)} has {canon[p - 1] if p <= len(canon) else "nothing"})'
               for a, p, _ in muts if p > len(canon) or canon[p - 1] != a]
        head = ('residue mismatch, numbering may be offset: ' + ', '.join(bad)) if bad else \
            f'construct not applied ({variant}): no numbering frame fits all of this paper\'s mutations'
        return {'sequence': '', 'check': f'{head}; {note}', 'frame': ''}
    s = list(seq)
    for a, p, b in muts:
        s[mapping[p] - 1] = b
    for s0, e, *_ in dels:
        idx = [mapping.get(p) for p in range(s0, e + 1)]
        if None in idx or idx != list(range(idx[0], idx[0] + len(idx))):
            return {'sequence': '', 'check': f'construct not applied ({variant}): the deletion is not contiguous in {label}', 'frame': ''}
        for i in idx:
            s[i - 1] = ''
    out = ''.join(s).split('*')[0]  # a nonsense mutation truncates the chain
    moved = ', '.join(f'{a}{p} = {a}{mapping[p]}' for a, p in sorted({(a, p) for a, p, _ in paper}, key=lambda x: x[1])
                      if mapping.get(p) != p)
    what = ' and '.join(w for w, c in (('mutations applied', muts), (f'residues {", ".join(f"{s0}-{e}" for s0, e, *_ in dels)} deleted', dels)) if c)
    if 'primers' in label:
        check = f'{what}, anchored on {label}'
    elif moved:
        check = f'{what} in {label} ({moved}); every wild-type residue of the paper\'s mutations matches'
    elif paper:
        check = f'{what}; every wild-type residue matches {label}'
    else:
        check = f'{what} in {label} numbering'
    if '*' in ''.join(s):
        check += '; nonsense mutation: chain truncated'
    if note:
        check += f'; {note}'
    return {'sequence': out, 'check': check, 'frame': label}


# ---------- construct ----------

def construct(acc, pdb_ids):
    """{'span': [start, end] or None, 'note', 'pdb', 'chain'}: the UniProt span the largest same-protein chain among
    the printed PDB entries covers (unobserved residues included), with crystal substitutions and extra (tag) residues
    named. Information only: the stored sequence is never cut or changed by it."""
    base = (acc or '').split('-')[0]
    best = None
    for pdb in pdb_ids or []:
        for chain, rows in pdb_residues(pdb).items():
            mapped = [i for i, r in enumerate(rows) if r[3] and r[2].split('-')[0] == base]
            if not mapped:
                continue
            lo, hi = rows[mapped[0]][3], rows[mapped[-1]][3]
            cand = (hi - lo + 1, pdb.upper(), chain, lo, hi,
                    ''.join(r[1] for r in rows[:mapped[0]]), ''.join(r[1] for r in rows[mapped[-1] + 1:]),
                    [f'{rows[i][4]}{rows[i][3]}{rows[i][1]}' for i in mapped if rows[i][1] not in (rows[i][4], 'X')])
            if best is None or cand[0] > best[0]:
                best = cand
    if not best:
        return {'span': None, 'note': 'no printed structure of this protein', 'pdb': '', 'chain': ''}
    n, pdb, chain, lo, hi, nt, ct, subs = best
    full = len(sequence(acc)) if acc else 0
    note = f'PDB {pdb} chain {chain} covers UniProt {lo}-{hi} ({n} of {full} aa)'
    if lo == 1 and hi == full:
        note += ', the whole entry'
    if nt or ct:
        note += '; extra residues not in UniProt (tag, not included):' + (f' N-terminal {nt}' if nt else '') + (f' C-terminal {ct}' if ct else '')
    if subs:
        note += f"; the crystal carries {', '.join(subs)} (not applied)"
    return {'span': [lo, hi], 'note': note, 'pdb': pdb, 'chain': chain}
