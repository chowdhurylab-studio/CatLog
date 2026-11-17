"""Cross-reference IDs for the export (2026-10-26, the website chat's data review: peers such as SABIO-RK, EnzymeML and
ChEMBL carry them, and the site links ChEBI, PubChem and NCBI Taxonomy from each record):

    substrate InChIKey    RDKit, from the stored SMILES (offline)
    substrate PubChem CID PubChem, from that InChIKey (structures.get: PubChem's throttling header obeyed)
    NCBI taxon id         UniProt's taxonomy service, from the organism's scientific name (exact name only)

The ChEBI id needs no lookup: `smiles_id` already names it when the structure came from ChEBI.
Answers are cached in enrich/ids.json; a network failure is never cached, so the next enrich asks again.

    python3 tools/ids.py           fill the cache for every SMILES and organism in catlog_wide.jsonl (enrich calls fill())
"""
import json, re, sys, time, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'enrich' / 'ids.json'
_cache = None


def cache():
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    return _cache


def save():
    if _cache is not None:
        tmp = CACHE.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(_cache, sort_keys=True))
        tmp.replace(CACHE)


def inchikey(smiles):
    """The standard InChIKey of a SMILES ('' when RDKit cannot read it or the SMILES is a fragment with '*')."""
    if not smiles or '*' in smiles:
        return ''
    k = 'inchikey|' + smiles
    c = cache()
    if k not in c:
        try:
            from rdkit import Chem, RDLogger
            from rdkit.Chem import inchi
            RDLogger.DisableLog('rdApp.*')
            m = Chem.MolFromSmiles(smiles)
            c[k] = inchi.MolToInchiKey(m) if m is not None else ''
        except Exception:  # an exotic structure RDKit cannot turn into an InChI: no key, never a guess
            c[k] = ''
    return c[k]


def pubchem_cid(key):
    """PubChem's compound id for an InChIKey: the first CID PubChem lists for it, '' when it lists none (cached),
    None when PubChem could not be asked (not cached)."""
    if not key:
        return ''
    k = 'pubchem|' + key
    c = cache()
    if k in c:
        return c[k]
    sys.path.insert(0, str(ROOT / 'tools'))
    from structures import get
    try:
        raw = get(f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{urllib.parse.quote(key)}/cids/JSON')
    except Exception:
        return None
    if raw is None:  # 404: PubChem has no compound with this key
        c[k] = ''
        return ''
    try:
        cids = json.loads(raw).get('IdentifierList', {}).get('CID', [])
    except (ValueError, AttributeError):
        return None
    c[k] = str(cids[0]) if cids else ''
    return c[k]


def taxon_id(organism):
    """NCBI taxonomy id of an organism's scientific name ('Homo sapiens' -> '9606'), '' when UniProt's taxonomy knows
    no taxon of exactly that name (cached), None when it could not be asked."""
    name = re.sub(r'\s+', ' ', (organism or '').strip())
    if not name or ';' in name:  # 'A; B': several organisms, no single taxon
        return ''
    k = 'taxon|' + name.lower()
    c = cache()
    if k in c:
        return c[k]
    sys.path.insert(0, str(ROOT / 'tools'))
    from sequences import _get
    try:
        raw = _get('https://rest.uniprot.org/taxonomy/search?' + urllib.parse.urlencode(
            {'query': f'scientific:"{name}"', 'fields': 'id,scientific_name', 'format': 'json', 'size': 5}))
    except Exception:
        return None
    if raw is None:
        return None
    try:
        hits = json.loads(raw).get('results', [])
    except ValueError:
        return None
    same = [h for h in hits if (h.get('scientificName') or '').lower() == name.lower()]
    c[k] = str(same[0]['taxonId']) if len(same) == 1 else ''  # an exact, unique scientific name only
    return c[k]


def fill(rows, log=print):
    """Look up every SMILES and organism of these export rows that the cache does not hold yet."""
    smiles = sorted({w['smiles'] for w in rows if w.get('smiles')})
    orgs = sorted({w['organism'] for w in rows if w.get('organism')})
    asked = failed = 0
    for i, s in enumerate(smiles):
        key = inchikey(s)
        if key and 'pubchem|' + key not in cache():
            asked += 1
            if pubchem_cid(key) is None:
                failed += 1
        if i % 200 == 0:
            save()
    for o in orgs:
        if 'taxon|' + re.sub(r'\s+', ' ', o.strip()).lower() not in cache():
            asked += 1
            if taxon_id(o) is None:
                failed += 1
    save()
    log(f'ids: {len(smiles):,} structures, {len(orgs):,} organisms; {asked:,} asked, {failed:,} to ask again next time')
    return failed


if __name__ == '__main__':
    fill([json.loads(l) for l in open(ROOT / 'catlog_wide.jsonl') if l.strip()])
