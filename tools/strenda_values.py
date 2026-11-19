#!/usr/bin/env python3
"""STRENDA DB (author-deposited kinetics; snapshot 2026-10-07 in sources/strenda/STRENDA_Claude_handoff.zip) ->
  sources/strenda_values.tsv    pmid, ec, metric, value (catalog units), substrate, organism, comment  (a db_values source)
  sources/strenda_pmids.txt     papers, for the queue
  sources/strenda_proteins.tsv  pmid, srn, uniprot, organism, protein_name, expression_system, sequence (as deposited,
                                the measured construct), modifications
  sources/strenda_compounds.tsv pmid, srn, name, smiles, inchi, chebi, pubchem (structures the authors deposited)
Identical repeated kcat entries the source XML carries are skipped (is_additional_exact_duplicate).
Usage: python3 tools/strenda_values.py
"""
import csv, io, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from units import normalize  # noqa: E402
csv.field_size_limit(10 ** 9)
ZIP = ROOT / 'sources' / 'strenda' / 'STRENDA_Claude_handoff.zip'
UNIT = {'s-1': 's-1', 'min-1': 'min-1', 'microM': 'uM', 'mM': 'mM', 'nM': 'nM', 'M': 'M', 'M-1_s-1': 'M-1 s-1',
        'mM-1_s-1': 'mM-1 s-1', 'microM-1_s-1': 'uM-1 s-1'}
z = zipfile.ZipFile(ZIP)


def table(name):
    return list(csv.DictReader(io.TextIOWrapper(z.open(f'csv/{name}'), encoding='utf-8-sig')))


exp = {r['srn']: r for r in table('Experiments.csv')}
def doi_ids():
    """DOI -> paper id for the papers BRENDA cites without a PMID (sources/nopmid_refs.tsv, tools/nopmid.py)."""
    import csv
    p = ROOT / 'sources' / 'nopmid_refs.tsv'
    if not p.exists():
        return {}
    with open(p) as f:
        return {r['doi'].lower(): r['paper_id'] for r in csv.DictReader(f, delimiter='\t') if r.get('doi') and r.get('paper_id')}


DOI_IDS = doi_ids()
pmid = {s: r['pmid'].strip() if r['pmid'].strip().isdigit() else DOI_IDS.get(r.get('publication_doi', '').strip().lower(), '')
        for s, r in exp.items()}  # no PMID: the id tools/nopmid.py gave its DOI, if any
n = 0
with open(ROOT / 'sources' / 'strenda_values.tsv', 'w') as out:
    out.write('pmid\tec\tmetric\tvalue\tsubstrate\torganism\tcomment\n')
    for r in table('Measurements.csv'):
        p = pmid.get(r['srn'])
        if not p or r['is_additional_exact_duplicate'].strip().lower() in ('true', '1', 'yes'):
            continue
        metric = {'CatalyticConstant': 'kcat', 'specificityConstant': 'kcat/Km'}.get(r['source_type'])
        if r['source_type'] == 'ConcentrationSE' and r['metric_name'] == 'km':
            metric = 'Km'
        if not metric:
            continue  # velocities, inhibition and affinity constants
        v, _, err = normalize(metric, r['raw_value'] or r['numeric_value'], UNIT.get(r['unit'], r['unit']))
        if err:
            continue
        e = exp[r['srn']]
        f = [p, e.get('ec_number', ''), metric, f'{v:.6g}', r['target_name'], e.get('organism', ''),
             f"STRENDA {r['srn']} {r['dataset_name']}; pH {r['pH_raw']}; {r['temperature_raw']} {r['temperature_unit']}"]
        out.write('\t'.join(x.replace('\t', ' ').replace('\n', ' ') for x in f) + '\n'); n += 1
(ROOT / 'sources' / 'strenda_pmids.txt').write_text(''.join(p + '\n' for p in dict.fromkeys(pmid.values())))
with open(ROOT / 'sources' / 'strenda_proteins.tsv', 'w') as out:
    out.write('pmid\tsrn\tuniprot\torganism\tprotein_name\texpression_system\tsequence\tmodifications\n')
    for r in table('Proteins.csv'):
        if r['srn'] in pmid:
            # 'null': a protein deposited without its sequence (25184516's two TrpB2o, 30921515's KARI2), not a sequence
            seq = next((s for s in (r['modified_sequence'], r['original_sequence']) if s.strip().lower() not in ('', 'null')),
                       '').replace('\n', '').replace(' ', '')
            f = [pmid[r['srn']], r['srn'], r['uniprotkb_xml'], r['organism'], r['protein_name'], r['expression_system'], seq,
                 r['sequence_modifications_json']]
            out.write('\t'.join(x.replace('\t', ' ').replace('\n', ' ') for x in f) + '\n')
with open(ROOT / 'sources' / 'strenda_compounds.tsv', 'w') as out:
    out.write('pmid\tsrn\tname\tsmiles\tinchi\tchebi\tpubchem\n')
    seen = set()
    for r in table('Compounds.csv'):
        k = (pmid.get(r['srn']), r['compound_name'].strip().lower())
        if k[0] and r['smiles'].strip() and k not in seen:
            seen.add(k)
            f = [k[0], r['srn'], r['compound_name'], r['smiles'], r['inchi'], r['chebi_id'], r['pubchem_cid']]
            out.write('\t'.join(x.replace('\t', ' ').replace('\n', ' ') for x in f) + '\n')
print(f'{n} STRENDA kcat/Km/kcat-Km values from {len(set(pmid.values()))} papers; '
      f'{sum(1 for _ in open(ROOT / "sources/strenda_proteins.tsv")) - 1} deposited proteins; {len(seen)} deposited compounds')
