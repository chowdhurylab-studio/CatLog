#!/usr/bin/env python3
"""Local reference tables for substrate structures (tools/structures.py), all under sources/ref/.

Downloaded (skipped when already on disk; --refresh fetches again):
  rhea_participants.tsv    one Rhea REST query: reaction id, equation, ChEBI participants, EC (~3 MB)
  rhea2uniprot_sprot.tsv, rhea-chebi-smiles.tsv, chebi_pH7_3_mapping.tsv, chebiId_name.tsv, rhea2ec.tsv
                           fetched one by one from ftp.expasy.org (rhea-tsv.tar.gz lags behind them)
  opsin.jar                OPSIN 2.9.0 command line (systematic name -> SMILES; runs on Java 8)
Built:
  chebi_compact.tsv.gz     chebi, stars, name, smiles   (default structure; InChI -> SMILES where RDKit cannot
                           parse ChEBI's SMILES). From the ChEBI flat files, streamed and not kept (~111 MB).
  chebi_names.tsv.gz       chebi, name, type            (names and synonyms)
  chebi_conj.tsv           chebi_a, chebi_b, why        (conjugate acid/base, tautomer, Rhea's pH 7.3 form)
  sabio_compounds.tsv.gz   compound id, name, InChI, SMILES, ChEBI, PubChem CID, KEGG (space-separated when
                           several) from external_links.compound of sources/sabio_rk_entries.jsonl.gz
  sabio_entry_substrates.tsv.gz  entry id, compound id, name, keyed (1 = a kinetic parameter names it):
                           the reaction substrates of each SABIO-RK entry (not water, H+ or the enzyme)
Re-run monthly (ChEBI releases monthly, Rhea every ~8 weeks). Usage: python3 tools/ref_structures.py [--refresh]
"""
import csv, gzip, json, os, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'sources' / 'ref'
SABIO = ROOT / 'sources' / 'sabio_rk_entries.jsonl.gz'
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}
RHEA_QUERY = 'https://www.rhea-db.org/rhea/?query=&columns=rhea-id,equation,chebi-id,ec&format=tsv&limit=25000'
RHEA_TSV = 'https://ftp.expasy.org/databases/rhea/tsv/'
RHEA_FILES = ['rhea2uniprot_sprot.tsv', 'rhea-chebi-smiles.tsv', 'chebi_pH7_3_mapping.tsv', 'chebiId_name.tsv', 'rhea2ec.tsv']
CHEBI = 'https://ftp.ebi.ac.uk/pub/databases/chebi/flat_files/'
OPSIN = 'https://github.com/dan2097/opsin/releases/download/2.9.0/opsin-cli-2.9.0-jar-with-dependencies.jar'
csv.field_size_limit(sys.maxsize)


def download(url, dest, refresh=False):
    """url -> dest via dest.part (a broken transfer never leaves a file that looks complete)."""
    if dest.exists() and dest.stat().st_size and not refresh:
        return False
    part = dest.with_name(dest.name + '.part')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(part, 'wb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            if not part.stat().st_size:
                raise RuntimeError('empty response')
            os.replace(part, dest)
            time.sleep(0.5)
            return True
        except Exception as e:
            err = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f'download failed: {url} ({err})')


def stream_tsv(name):
    """Rows of a gzipped ChEBI flat file, read straight from the network."""
    r = urllib.request.urlopen(urllib.request.Request(CHEBI + name, headers=UA), timeout=300)
    with gzip.open(r, 'rt', encoding='utf-8', newline='') as f:
        yield from csv.DictReader(f, delimiter='\t')


def build_chebi():
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog('rdApp.*')
    t0 = time.time()
    comp = {}  # internal compound id -> (accession, stars, name)
    for r in stream_tsv('compounds.tsv.gz'):
        comp[r['id']] = (r['chebi_accession'], r['stars'], (r['ascii_name'] or r['name']).replace('\t', ' ').replace('\n', ' '))
    smiles, fixed = {}, 0
    for r in stream_tsv('structures.tsv.gz'):
        if r['default_structure'] != 'true' or r['compound_id'] not in comp:
            continue
        smi, inchi = (r['smiles'] or '').strip(), (r['standard_inchi'] or '').strip()
        if smi and Chem.MolFromSmiles(smi) is None and inchi:  # some ChEBI SMILES do not parse in RDKit; the InChI does
            m = Chem.MolFromInchi(inchi)
            if m is not None:
                smi, fixed = Chem.MolToSmiles(m), fixed + 1
        if smi:
            smiles[r['compound_id']] = smi
    tmp = REF / 'chebi_compact.tsv.gz.part'
    with gzip.open(tmp, 'wt') as out:
        out.write('chebi\tstars\tname\tsmiles\n')
        for cid, (acc, stars, name) in comp.items():
            out.write(f'{acc}\t{stars}\t{name}\t{smiles.get(cid, "")}\n')
    names_tmp, n_names = REF / 'chebi_names.tsv.gz.part', 0
    with gzip.open(names_tmp, 'wt') as out:
        out.write('chebi\tname\ttype\n')
        for r in stream_tsv('names.tsv.gz'):
            acc = comp.get(r['compound_id'], ('',))[0]
            name = (r['ascii_name'] or r['name'] or '').replace('\t', ' ').replace('\n', ' ').strip()
            if acc and name:
                out.write(f"{acc}\t{name}\t{r['type']}\n"); n_names += 1
    pairs = set()
    for r in stream_tsv('relation.tsv.gz'):
        if r['relation_type_id'] in ('6', '7', '11'):  # is conjugate acid of / is conjugate base of / is tautomer of
            a, b = comp.get(r['init_id'], ('',))[0], comp.get(r['final_id'], ('',))[0]
            if a and b and a != b:
                pairs.add((a, b, {'6': 'conjugate acid', '7': 'conjugate base', '11': 'tautomer'}[r['relation_type_id']]))
    for line in open(REF / 'chebi_pH7_3_mapping.tsv'):
        f = line.rstrip('\n').split('\t')
        if len(f) >= 2 and f[0].isdigit() and f[1].isdigit() and f[0] != f[1]:
            pairs.add((f'CHEBI:{f[0]}', f'CHEBI:{f[1]}', 'Rhea pH 7.3 form'))
    conj_tmp = REF / 'chebi_conj.tsv.part'
    with open(conj_tmp, 'w') as out:
        out.write('chebi_a\tchebi_b\twhy\n')
        out.writelines(f'{a}\t{b}\t{w}\n' for a, b, w in sorted(pairs))
    os.replace(tmp, REF / 'chebi_compact.tsv.gz')
    os.replace(names_tmp, REF / 'chebi_names.tsv.gz')
    os.replace(conj_tmp, REF / 'chebi_conj.tsv')
    print(f'ChEBI: {len(comp):,} entries, {len(smiles):,} with a structure ({fixed:,} SMILES rebuilt from InChI), '
          f'{n_names:,} names, {len(pairs):,} charge/tautomer links ({time.time() - t0:.0f} s)')


def build_sabio():
    t0 = time.time()
    names, links, entries = {}, {}, []
    with gzip.open(SABIO, 'rt') as f:
        for line in f:
            e = json.loads(line)
            for c in (e.get('external_links') or {}).get('compound') or []:
                k, v = c.get('key'), str(c.get('value') or '').strip()
                if k in ('InChI', 'SMILES', 'ChebiID', 'PubChemCID', 'KeggCompoundID') and v:
                    s = links.setdefault(str(c.get('id')), {}).setdefault(k, [])
                    if v not in s:
                        s.append(v)
            keyed = set()
            for p in (e.get('kineticlaw') or {}).get('parameter') or []:
                sk = ((p.get('species') or {}).get('species_key') or '').split('|')
                if len(sk) > 2 and sk[2].strip() == 'Substrate':
                    keyed.add(sk[1].strip())
            seen = set()
            for s in (e.get('reaction') or {}).get('species') or []:
                c = s.get('compound') or {}
                if c.get('id') is None:
                    continue
                cid, name = str(c['id']), (c.get('name') or '').replace('\t', ' ').strip()
                names.setdefault(cid, name)
                if s.get('role') == 'Substrate' and name.lower() not in ('h2o', 'h+', 'enzyme') and cid not in seen:
                    seen.add(cid)
                    entries.append(f"{e.get('id')}\t{cid}\t{name}\t{int(name in keyed)}\n")
    tmp = REF / 'sabio_compounds.tsv.gz.part'
    with gzip.open(tmp, 'wt') as out:
        out.write('compound_id\tname\tinchi\tsmiles\tchebi\tpubchem_cid\tkegg\n')
        for cid in sorted(set(names) | set(links), key=lambda x: int(x) if x.isdigit() else 0):
            L = links.get(cid, {})
            out.write('\t'.join([cid, names.get(cid, '')] + [' '.join(L.get(k, [])) for k in
                                                             ('InChI', 'SMILES', 'ChebiID', 'PubChemCID', 'KeggCompoundID')]) + '\n')
    tmp2 = REF / 'sabio_entry_substrates.tsv.gz.part'
    with gzip.open(tmp2, 'wt') as out:
        out.write('entry_id\tcompound_id\tname\tkeyed\n')
        out.writelines(entries)
    os.replace(tmp, REF / 'sabio_compounds.tsv.gz')
    os.replace(tmp2, REF / 'sabio_entry_substrates.tsv.gz')
    n_inchi = sum(1 for L in links.values() if L.get('InChI'))
    n_smi = sum(1 for L in links.values() if L.get('SMILES'))
    print(f'SABIO-RK: {len(set(names) | set(links)):,} compounds ({n_inchi:,} with InChI, {n_smi:,} with SMILES), '
          f'{len(entries):,} entry substrates ({time.time() - t0:.0f} s)')


def main():
    refresh = '--refresh' in sys.argv
    REF.mkdir(parents=True, exist_ok=True)
    got = download(RHEA_QUERY, REF / 'rhea_participants.tsv', refresh)
    for name in RHEA_FILES:
        got |= download(RHEA_TSV + name, REF / name, refresh)
    download(OPSIN, REF / 'opsin.jar', refresh)
    if refresh or got or not all((REF / f).exists() for f in ('chebi_compact.tsv.gz', 'chebi_names.tsv.gz', 'chebi_conj.tsv')):
        try:
            build_chebi()
        except Exception as e:
            raise RuntimeError(f'ChEBI build failed (nothing replaced): {e}')
    sab = REF / 'sabio_compounds.tsv.gz'
    if SABIO.exists() and (refresh or not sab.exists() or sab.stat().st_mtime < SABIO.stat().st_mtime):
        build_sabio()
    rhea = sum(1 for _ in open(REF / 'rhea_participants.tsv')) - 1
    print(f'Rhea: {rhea:,} reactions; files in {REF}:')
    for name in ['rhea_participants.tsv'] + RHEA_FILES + ['opsin.jar', 'chebi_compact.tsv.gz', 'chebi_names.tsv.gz', 'chebi_conj.tsv',
                                                         'sabio_compounds.tsv.gz', 'sabio_entry_substrates.tsv.gz']:
        p = REF / name
        print(f'  {name:32s} {p.stat().st_size / 1e6 if p.exists() else 0:7.1f} MB')


if __name__ == '__main__':
    main()
