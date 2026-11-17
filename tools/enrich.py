"""Additional fields for catalog rows, looked up by code and cached under enrich/:

- UniProt accession: printed in the paper, else via a printed GenBank/RefSeq/PDB ID, else a unique
  gene + organism match. Anything else stays blank with the candidates listed.
- Sequence: the UniProt canonical sequence; for a point mutant, the mutations are applied only when every
  wild-type residue matches the canonical sequence at its printed position.
- SMILES: PubChem lookup of the full substrate name.
Every result records how it was found, so a reader can judge it.
"""
import os
import json, re, time, urllib.parse, urllib.request
from pathlib import Path
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)

UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}
ACC = re.compile(r'^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})$')
AA3 = {'Ala': 'A', 'Arg': 'R', 'Asn': 'N', 'Asp': 'D', 'Cys': 'C', 'Gln': 'Q', 'Glu': 'E', 'Gly': 'G', 'His': 'H',
       'Ile': 'I', 'Leu': 'L', 'Lys': 'K', 'Met': 'M', 'Phe': 'F', 'Pro': 'P', 'Ser': 'S', 'Thr': 'T', 'Trp': 'W',
       'Tyr': 'Y', 'Val': 'V'}
WT_WORDS = {'wild type', 'wild-type', 'wildtype', 'wt', 'native', 'wt enzyme', 'wild type enzyme'}


def get(url, timeout=60):
    for attempt in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f'lookup failed: {url}')  # network trouble is not 'not found': never cache it


class Cache(dict):
    def __init__(self, path):
        self.path = Path(path)
        super().__init__(json.loads(self.path.read_text()) if self.path.exists() else {})

    def save(self):
        self.path.parent.mkdir(exist_ok=True)
        tmp = self.path.with_name(f'{self.path.name}.{os.getpid()}.tmp')  # whole or not at all
        tmp.write_text(json.dumps(self, indent=1, ensure_ascii=False))
        tmp.replace(self.path)


def uniprot_search(query):
    url = ('https://rest.uniprot.org/uniprotkb/search?format=json&size=10&fields=accession,reviewed,organism_name,'
           'gene_primary,protein_name&query=' + urllib.parse.quote(query))
    raw = get(url)
    time.sleep(0.2)
    if not raw:
        return []
    return [{'acc': r['primaryAccession'], 'reviewed': 'reviewed' in r.get('entryType', '').lower() and 'unreviewed' not in r.get('entryType', '').lower(),
             'organism': r.get('organism', {}).get('scientificName', '')} for r in json.loads(raw).get('results', [])]


# organisms papers name by a common word (the whole field, nothing else): read as the species they mean, so species
# matching and the UniProt name routes work (one word would count as genus-level) and the export shows the binomial
COMMON = {'human': 'Homo sapiens', 'rat': 'Rattus norvegicus', 'mouse': 'Mus musculus', 'rabbit': 'Oryctolagus cuniculus',
          'bovine': 'Bos taurus', 'cow': 'Bos taurus', 'porcine': 'Sus scrofa', 'pig': 'Sus scrofa', 'dog': 'Canis lupus familiaris',
          'chicken': 'Gallus gallus', 'maize': 'Zea mays', 'sorghum': 'Sorghum bicolor'}


def binomial(name):
    """'human' -> 'Homo sapiens'; anything else unchanged."""
    return COMMON.get((name or '').strip().lower(), name or '')


def genus_species(name):
    return ' '.join(re.sub(r'[^A-Za-z ]', ' ', binomial(name)).lower().split()[:2])


def find_uniprot(row):
    acc = (row.get('uniprot') or '').strip()
    if ACC.match(acc):
        return {'acc': acc, 'how': 'printed in paper'}
    org = genus_species(row.get('organism'))
    for pid in [p.strip() for p in re.split(r'[,;\s]+', row.get('protein_ids') or '') if p.strip()]:
        if ACC.match(pid):
            return {'acc': pid, 'how': f'printed ID {pid}'}
        base = pid.split('.')[0]
        if re.fullmatch(r'\d[A-Za-z0-9]{3}', base):
            q = f'xref:pdb-{base}'
        elif re.fullmatch(r'[NXWYA]P_\d+', base):
            q = f'xref:refseq-{pid}'
        else:
            q = f'xref:embl-{base}'
        hits = uniprot_search(q)
        same = [h for h in hits if genus_species(h['organism']) == org]  # never accept another species' entry
        if len(same) == 1:
            return {'acc': same[0]['acc'], 'how': f'{q} (unique)'}
    gene = (row.get('gene') or '').strip()
    if gene and org:
        hits = uniprot_search(f'gene_exact:"{gene}" AND organism_name:"{org}"')
        pool = [h for h in hits if h['reviewed']] or hits
        if len(pool) == 1:
            return {'acc': pool[0]['acc'], 'how': f'gene {gene} + organism, unique {"reviewed" if pool[0]["reviewed"] else "unreviewed"} entry'}
        if pool:
            return {'acc': '', 'how': 'ambiguous gene + organism', 'candidates': [h['acc'] for h in pool[:6]]}
    candidates = []
    name = re.sub(r'\s*\([^)]*\)', '', row.get('enzyme') or '').strip()
    for label, q in (('protein name', f'protein_name:"{name}"' if len(name) > 3 else ''),
                     ('EC', f'ec:{row.get("ec")}' if re.fullmatch(r'\d+\.\d+\.\d+\.\d+', (row.get('ec') or '').strip()) else '')):
        if not q or not org:
            continue
        hits = [h for h in uniprot_search(f'{q} AND organism_name:"{org}" AND reviewed:true') if genus_species(h['organism']) == org]
        if len(hits) == 1:
            return {'acc': hits[0]['acc'], 'how': f'{label} + organism, unique reviewed entry'}
        candidates += [h['acc'] for h in hits if h['acc'] not in candidates]
    if candidates:
        return {'acc': '', 'how': 'ambiguous (protein name / EC + organism)', 'candidates': candidates[:6]}
    return {'acc': '', 'how': 'not found (no printed ID; gene, protein name and EC + organism gave nothing unique)'}


def pick_by_mutations(candidates, mutations, seq_dir):
    """Among candidate accessions, the one whose sequence has every wild-type residue the paper's mutations name
    (>=2 distinct positions). None unless exactly one candidate fits."""
    muts = sorted(set((a, p) for a, p, _ in mutations))
    if len({p for _, p in muts}) < 2:
        return None
    fits = []
    for acc in candidates:
        seq = sequence(acc, seq_dir)
        if seq and all(0 < p <= len(seq) and seq[p - 1] == a for a, p in muts):
            fits.append(acc)
    return fits[0] if len(fits) == 1 else None


BULK = Path(os.environ['CATLOG_BULK_FASTA']) if os.environ.get('CATLOG_BULK_FASTA') else None  # optional UniProt FASTA (README: settings)
_bulk = None


def bulk_fasta():
    """The old repo's 13,881-sequence UniProt snapshot (2026-08-26), read once; saves REST calls."""
    global _bulk
    if _bulk is None:
        _bulk, acc, buf = {}, None, []
        if BULK and BULK.exists():
            for line in open(BULK):
                if line.startswith('>'):
                    if acc:
                        _bulk[acc] = ''.join(buf)
                    m = re.match(r'>\w+\|([^|]+)\|', line)
                    acc, buf = (m.group(1) if m else None), []
                else:
                    buf.append(line.strip())
            if acc:
                _bulk[acc] = ''.join(buf)
    return _bulk


def uniprot_ec(acc):
    raw = get(f'https://rest.uniprot.org/uniprotkb/{acc}?format=tsv&fields=ec')
    time.sleep(0.2)
    lines = raw.decode().splitlines() if raw else []
    return lines[1].strip() if len(lines) > 1 else ''


def sequence(acc, seq_dir):
    f = Path(seq_dir) / f'{acc}.fasta'
    if not f.exists() and acc in bulk_fasta():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f'>{acc} (UniProt canonical, bulk snapshot 2026-08-26)\n{bulk_fasta()[acc]}\n')
    if not f.exists():
        raw = get(f'https://rest.uniprot.org/uniprotkb/{acc}.fasta')  # network trouble raises: never 'does not fit'
        if not raw:
            return ''
        f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(raw)
    return ''.join(f.read_text().splitlines()[1:])


def parse_variant(variant):
    """(wild_type, [(wt, pos, new)], leftover text that is not a point mutation)."""
    v = (variant or '').strip()
    if v.lower() in WT_WORDS:
        return True, [], ''
    for three, one in AA3.items():
        v = re.sub(rf'{three}(?=\d)|(?<=\d){three}', one, v)
    muts = [(a, int(p), b) for a, p, b in re.findall(r'(?<![A-Za-z])([ACDEFGHIKLMNPQRSTVWY])(\d{1,4})([ACDEFGHIKLMNPQRSTVWY*])(?![a-z])', v)]
    rest = re.sub(r'(?<![A-Za-z])[ACDEFGHIKLMNPQRSTVWY]\d{1,4}[ACDEFGHIKLMNPQRSTVWY*](?![a-z])', '', v)
    rest = re.sub(r'[\s/,+;\-]+|\b(?:and|mutant|variant|double|triple)\b', '', rest, flags=re.I)
    return False, muts, rest


def paper_offset(mutations, canonical, span=200):
    """One numbering offset that makes EVERY wild-type residue of a paper's mutations match UniProt
    (papers often number from the mature chain). Needs >=3 distinct positions and a unique offset, else None."""
    muts = sorted(set((a, p) for a, p, _ in mutations))
    if len(set(p for _, p in muts)) < 3 or not canonical:
        return None
    hits = [d for d in range(-span, span + 1) if all(0 < p + d <= len(canonical) and canonical[p + d - 1] == a for a, p in muts)]
    return hits[0] if len(hits) == 1 else None


def build_sequence(variant, canonical, offset=None):
    """(sequence, check) for this variant on the canonical sequence; offset from paper_offset()."""
    wt, muts, rest = parse_variant(variant)
    if not canonical:
        return '', 'no sequence (no UniProt accession)'
    if wt:
        return canonical, 'wild type: UniProt canonical sequence'
    if rest or not muts:
        return '', f'construct not applied ({variant})'
    bad = [f'{a}{p} (UniProt has {canonical[p - 1] if p <= len(canonical) else "nothing"})'
           for a, p, b in muts if p > len(canonical) or canonical[p - 1] != a]
    shift, note = 0, 'mutations applied; every wild-type residue matches UniProt'
    if offset and all(0 < p + offset <= len(canonical) and canonical[p + offset - 1] == a for a, p, _ in muts):
        shift = offset
        note = f'mutations applied with paper numbering offset {offset:+d} (one offset fits every mutation in this paper)'
    elif bad:
        return '', 'residue mismatch, numbering may be offset: ' + ', '.join(bad)
    s = list(canonical)
    for a, p, b in muts:
        s[p + shift - 1] = b
    return ''.join(s).split('*')[0], note  # a nonsense mutation truncates the chain


def chebi_smiles(name):
    """ChEBI (EBI's curated small-molecule database): exact name match only, 3-star entries preferred."""
    raw = get('https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?size=10&term=' + urllib.parse.quote(name))
    time.sleep(0.2)
    if not raw:
        return None
    hits = [h['_source'] for h in json.loads(raw.decode('utf-8'), strict=False).get('results', [])]
    exact = [h for h in hits if name.lower() in ((h.get('name') or '').lower(), (h.get('ascii_name') or '').lower()) and h.get('smiles')]
    exact.sort(key=lambda h: -(h.get('stars') or 0))
    if not exact:
        return None
    h = exact[0]
    return {'smiles': h['smiles'], 'chebi': h.get('chebi_accession'), 'how': f'ChEBI exact name "{name}" -> {h.get("chebi_accession")}'}


_skid = None


def skid_smiles(name):
    """SKiD's curated substrate structures (sources/skid/Main_dataset_v1.xlsx), exact name, only if unambiguous."""
    global _skid
    if _skid is None:
        _skid = {}
        x = Path(__file__).resolve().parent.parent / 'sources' / 'skid' / 'Main_dataset_v1.xlsx'
        if x.exists():
            import openpyxl
            wb = openpyxl.load_workbook(x, read_only=True)
            for sheet in ('kcat_dataset', 'Km_dataset'):
                rows = wb[sheet].iter_rows(values_only=True)
                hdr = next(rows)
                i, j = hdr.index('Substrate'), hdr.index('Substrate_SMILES')
                for r in rows:
                    if r[i] and r[j]:
                        _skid.setdefault(str(r[i]).strip().lower(), set()).add(str(r[j]).strip())
    found = _skid.get(name.strip().lower(), set())
    if len(found) == 1:
        return {'smiles': next(iter(found)), 'how': f'SKiD curated structure for "{name}"'}
    return None


def find_smiles(name):
    if not name:
        return {'smiles': '', 'how': 'no name'}
    name = name.translate(str.maketrans({'\u03b1': 'alpha', '\u03b2': 'beta', '\u03b3': 'gamma', '\u03b4': 'delta'}))
    raw = get('https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/' + urllib.parse.quote(name, safe='') +
              '/property/SMILES,IsomericSMILES/JSON')
    time.sleep(0.25)
    props = json.loads(raw).get('PropertyTable', {}).get('Properties', []) if raw else []
    if not props:
        return chebi_smiles(name) or skid_smiles(name) or {'smiles': '', 'how': f'no exact-name match in PubChem, ChEBI or SKiD for "{name}"'}
    p = props[0]
    how = f'PubChem name "{name}" -> CID {p.get("CID")}' + (f' (first of {len(props)})' if len(props) > 1 else '')
    return {'smiles': p.get('IsomericSMILES') or p.get('SMILES', ''), 'cid': p.get('CID'), 'how': how}
