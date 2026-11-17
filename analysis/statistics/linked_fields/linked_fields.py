#!/usr/bin/env python3
"""Question 6: are the fields CatLog's code links to a record right (UniProt entry, EC number, organism, and the
sequence where the authors deposited the measured construct in STRENDA DB)?

Inputs (read only): the export frozen with tag paper-catalog-freeze-20261116 (work/paper_freeze_20261116/), the catalogue
files at that tag (git show), the local reference files (sources/ref/, sources/strenda/) and CatLog's code at the tag
(git archive into the scratch folder; imported from there, never edited). No network: every socket call raises.

Stage 1 re-runs the tag's dbcompare.compare() on the frozen export and catalogue, checks that it gives every value the
database_check the frozen export holds, and keeps, for every value, the database rows compare() counted as the same
number under a fitting label (its pass 1: 'confirmed'). Stage 2 compares the linked fields of those records with what
the confirming rows name. Stage 3 aligns CatLog's sequence with the sequence the authors deposited in STRENDA DB.

Usage: python3 -I -B linked_fields.py [--scratch DIR] [--reuse] [--structures FILE]
  --scratch     a folder for the tag's code and files (default: a new folder in the system temp dir); never the repository
  --reuse       reuse stage 1's result in the scratch folder (stage1.pkl) instead of running compare() again
  --structures  the substrate lookups compare() reads (default: the copy kept with the frozen export,
                work/paper_freeze_20261116/structures_for_linked_fields.json.gz, checked by its sha256)
  --write-structures-copy FILE  write that copy from FILE (enrich/structures.json with the sha256 below) and stop
Writes results.json, differences.tsv.gz, strenda_sequences.tsv and README.md next to this script.
"""
import argparse, collections, csv, gzip, hashlib, io, json, math, os, pickle, re, shutil, socket, subprocess, sys, \
    tempfile, time, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # paper/evidence/<this folder> -> the repository
TAG = 'paper-catalog-freeze-20261116'
TAG_COMMIT = '45487e4ee93167fcc2a30e12b75217cb19d52c77'
FROZEN = REPO / 'work' / 'paper_freeze_20261116'
REF = REPO / 'sources' / 'ref'
STRENDA_ZIP = REPO / 'sources' / 'strenda' / 'STRENDA_Claude_handoff.zip'
FREEZE_MD = REPO / 'paper' / 'evidence' / 'catalog_freeze_20261116' / 'FREEZE.md'
SOURCES = ('BRENDA', 'SABIO-RK', 'OED', 'SKiD', 'STRENDA', 'UniProt')
# sha256 of the uncompressed files, as paper/evidence/catalog_freeze_20261116/FREEZE.md lists them
SHA = {'catalog.jsonl': '7281ae4c78bfddf5a39393e0f938a91aae753b4db62fe7ec60852abb369fb961',
       'rejected.jsonl': '145b992f2f987befb7a8e422e96b6e8c7e43a5fb66b1a2df2f19a2b995b11d8f',
       'papers.tsv': '8ab6226e5bbd348add85b8cde0b2d2b918941ac05278af62ff5ef88bbc4b3c4f',
       'sources/database_corrections.tsv': '7dbb76f8ff05a8be2a9c54bc905916f06851c48a78c877e18ac200f46351ff26',
       'catlog_wide.jsonl': 'e544a0d626682dcc20e34937be6148ef9bafb0e0052fc9936e1b131356553acf',
       'database_compare.json': 'c2f22dacbf219a960c07355dea92ecc4f7776650b1769e30ed3a381aac6e3ed4',
       'db_values.tsv': '23d3fe3abce8ffc40a5ada3215c9a48ff43fd893111878f77800e5363f892d4a'}
# the substrate lookups compare() reads (enrich/structures.json) are not frozen with the tag: a copy holding only the keys
# compare() asks for these catalogue rows, written once by --write-structures-copy from the live file with this sha256
STRUCT_COPY = FROZEN / 'structures_for_linked_fields.json.gz'
STRUCT_SHA = {'source': '6869e82def7018a233be4284107b07a1bce962051603fc54d1cf1fc6719118bd',  # enrich/structures.json
              'copy_gz': '6d1a514221338e92194172e95929effcf02119f7bc704e748bd5a2480a79f492',  # the .gz file as stored
              'copy_json': 'c2bc0b5302e378d65e3289977e6c38aea1c97129df1cb3218f1b51385e48ac4f'}  # its content
# counts the paper prints for the frozen export (FREEZE.md "The counts at the snapshot")
PAPER = {'records': 140147, 'values': 313609, 'uniprot': 84858, 'sequence': 79969, 'ec': 120430, 'smiles': 122309,
         'uniprot_pct': 60.5, 'sequence_pct': 57.1,
         'values_by_category': {'CONFIRMED': 181911, 'SAME_NUMBER_LABEL_DIFFERS': 11300, 'DIFFERS': 5281, 'NEW_a': 61796,
                                'NEW_b': 51818, 'NO_VALUE': 1503}}
# catalogue fields compare() never reads (the big texts and the provenance stamps), left out to save memory
DROP = {'title', 'quote', 'verify_note', 'checked', 'doi', 'reasoning', 'read_by', 'reader_model', 'verifier_model',
        'read_prompt', 'verify_prompt', 'task_prompt', 'pipeline_commit', 'model', 'agent_models'}
OUT_KEEP = ('measurement_id', 'pubmed_id', 'row_ids', 'organism', 'evidence', 'kcat', 'km', 'kcat_over_km',
            'kcat_over_km_source', 'ratio_check')
LINK_KEEP = ('pubmed_id', 'uniprot_id', 'uniprot_how', 'ec_number', 'ec_source', 'organism', 'organism_source', 'taxon_id',
             'strain', 'enzyme_name', 'gene', 'mutation_signature', 'wild_type', 'row_ids', 'construct', 'sequence_basis',
             'sequence_check', 'sequence_frame', 'deposited_sequence_note')


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def block_network():
    """Any attempt to open a connection raises: this analysis uses local files only."""
    def refuse(*a, **k):
        raise RuntimeError('network access is blocked in this analysis')
    socket.socket.connect = refuse
    socket.socket.connect_ex = refuse
    socket.create_connection = refuse
    socket.getaddrinfo = refuse


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def git(*args, **kw):
    return subprocess.run(['git', '-C', str(REPO), *args], check=True, capture_output=True, **kw).stdout


# ------------------------------------------------------------------------------------------------ stage 1
def prepare_root(root):
    """The tag's code and catalogue files in the scratch folder, each checked against FREEZE.md's sha256."""
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    assert git('rev-parse', f'{TAG}^{{commit}}').decode().strip() == TAG_COMMIT
    freeze = FREEZE_MD.read_text()
    for k, v in SHA.items():
        assert v in freeze, f'{k}: sha256 not in FREEZE.md'
    tar = git('archive', TAG, 'tools/')
    subprocess.run(['tar', '-x', '-C', str(root)], input=tar, check=True)
    (root / 'sources').mkdir()
    for path in ('papers.tsv', 'rejected.jsonl', 'sources/natural_forms.tsv', 'sources/database_corrections.tsv'):
        b = git('show', f'{TAG}:{path}')
        if path in SHA:
            assert hashlib.sha256(b).hexdigest() == SHA[path], path
        (root / path).write_bytes(b)
    with gzip.open(FROZEN / 'db_values.tsv.gz', 'rb') as f, open(root / 'sources' / 'db_values.tsv', 'wb') as g:
        shutil.copyfileobj(f, g)
    assert sha256_file(root / 'sources' / 'db_values.tsv') == SHA['db_values.tsv']
    (root / 'sources' / 'ref').symlink_to(REF)  # read only (structures.py's offline tables, sequences.py's FASTA)
    (root / 'enrich').mkdir()  # empty: compare() is handed the substrate lookups (load_structures)


def structure_keys(cat):
    """The keys compare() looks up in the substrate lookups, one per catalogue row: the tag's dbcompare.compare() reads
    sm.get(f"{r['pmid']}|{sk}") with sk the row's substrate_full_name (else substrate), stripped and lower-cased, and
    reads the lookups nowhere else."""
    return {f"{r['pmid']}|{(r.get('substrate_full_name') or r.get('substrate') or '').strip().lower()}" for r in cat}


def write_structures_copy(src):
    """The copy kept with the frozen export: the lookups of the keys compare() asks for these catalogue rows, taken
    from enrich/structures.json as it was when this analysis ran (sha256 STRUCT_SHA['source'])."""
    b = Path(src).read_bytes()
    assert hashlib.sha256(b).hexdigest() == STRUCT_SHA['source'], f'{src} is not the structures.json this analysis used'
    full = json.loads(b)
    keys = structure_keys(load_catalog())
    sub = {k: full[k] for k in sorted(keys) if k in full}
    data = json.dumps(sub, ensure_ascii=False, sort_keys=True, indent=0).encode()
    gz = gzip.compress(data, mtime=0)
    if STRUCT_COPY.exists() and STRUCT_COPY.read_bytes() != gz:
        raise SystemExit(f'{STRUCT_COPY} exists with other content: not overwritten')
    STRUCT_COPY.write_bytes(gz)
    print(json.dumps({'copy': str(STRUCT_COPY), 'source_keys': len(full), 'keys_asked': len(keys), 'keys_kept': len(sub),
                      'source_sha256': STRUCT_SHA['source'], 'copy_gz_sha256': hashlib.sha256(gz).hexdigest(),
                      'copy_json_sha256': hashlib.sha256(data).hexdigest()}, indent=1))


def load_structures(path):
    """The substrate lookups for compare(): the frozen copy (checked by its sha256), or a file named with --structures."""
    b = Path(path).read_bytes()
    info = {'file': str(Path(path).resolve().relative_to(REPO)) if REPO in Path(path).resolve().parents else str(path),
            'sha256': hashlib.sha256(b).hexdigest()}
    if Path(path).resolve() == STRUCT_COPY.resolve():
        assert info['sha256'] == STRUCT_SHA['copy_gz'], 'the frozen copy of the substrate lookups'
        b = gzip.decompress(b)
        assert hashlib.sha256(b).hexdigest() == STRUCT_SHA['copy_json']
        info['source_sha256'] = STRUCT_SHA['source']
    elif str(path).endswith('.gz'):
        b = gzip.decompress(b)
    sm = json.loads(b)
    info['keys'] = len(sm)
    return sm, info


class AskedKeys(dict):
    """The lookups as compare() reads them (sm.get), with every key it asks for kept."""
    def __init__(self, d):
        super().__init__(d)
        self.asked = set()

    def get(self, k, default=None):
        self.asked.add(k)
        return super().get(k, default)


def load_catalog():
    p = subprocess.Popen(['git', '-C', str(REPO), 'show', f'{TAG}:catalog.jsonl'], stdout=subprocess.PIPE, bufsize=1 << 20)
    h, cat = hashlib.sha256(), []
    for line in p.stdout:
        h.update(line)
        if line.strip():
            r = json.loads(line)
            cat.append({k: v for k, v in r.items() if k not in DROP})
    assert p.wait() == 0
    assert h.hexdigest() == SHA['catalog.jsonl'], 'catalog.jsonl at the tag'
    return cat


def load_export():
    h = hashlib.sha256()
    out, frozen_dc, frozen_dn, link, seqs = [], {}, {}, {}, {}
    n = collections.Counter()
    with gzip.open(FROZEN / 'catlog_wide.jsonl.gz', 'rb') as f:
        for line in f:
            h.update(line)
            w = json.loads(line)
            mid = w['measurement_id']
            n['records'] += 1
            n['values'] += len(w.get('evidence') or {})
            for k, field in (('uniprot', 'uniprot_id'), ('sequence', 'sequence'), ('ec', 'ec_number'), ('smiles', 'smiles')):
                n[k] += bool(w.get(field))
            out.append({k: w.get(k) for k in OUT_KEEP})
            frozen_dc[mid] = w.get('database_check')
            frozen_dn[mid] = w.get('database_note')
            L = {k: w.get(k) for k in LINK_KEEP}
            L['metrics'] = {m: ev.get('row_id') for m, ev in (w.get('evidence') or {}).items()}
            L['has_sequence'] = bool(w.get('sequence'))
            if w.get('uniprot_id') and w.get('uniprot_sequence'):
                L['uniprot_sequence'] = seqs.setdefault(w['uniprot_sequence'], w['uniprot_sequence'])
            if w.get('deposited_sequence'):
                for k in ('sequence', 'deposited_sequence', 'uniprot_sequence'):
                    L[k] = w.get(k) or ''
            link[mid] = L
    assert h.hexdigest() == SHA['catlog_wide.jsonl'], 'frozen catlog_wide.jsonl'
    assert len(link) == n['records'], 'measurement ids are unique'
    return out, frozen_dc, frozen_dn, link, dict(n)


def run_compare(root, out, cat, sm):
    """compare() of the tag on the frozen export, with its local variables kept when it returns (sys.monitoring: the
    function runs as it is, nothing in it is changed)."""
    sys.path.insert(0, str(root / 'tools'))
    import dbcompare
    assert Path(dbcompare.__file__).resolve().parent == (root / 'tools').resolve()
    M, TOOL, kept = sys.monitoring, 4, {}
    M.use_tool_id(TOOL, 'linked_fields')

    def on_return(code, offset, retval):
        if code is dbcompare.compare.__code__:
            kept.update(sys._getframe(1).f_locals)
    M.register_callback(TOOL, M.events.PY_RETURN, on_return)
    M.set_local_events(TOOL, dbcompare.compare.__code__, M.events.PY_RETURN)
    try:
        summary = dbcompare.compare(out, cat, root, sm)
    finally:
        M.set_local_events(TOOL, dbcompare.compare.__code__, 0)
        M.register_callback(TOOL, M.events.PY_RETURN, None)
        M.free_tool_id(TOOL)
    return dbcompare, summary, kept


def stage1(scratch, papers=0, structures=STRUCT_COPY):
    root = scratch / 'root'
    log('preparing the tag code and files in', root)
    prepare_root(root)
    log('reading the frozen export')
    out, frozen_dc, frozen_dn, link, counts = load_export()
    log('reading catalog.jsonl at the tag')
    cat = load_catalog()
    if papers:  # a quick test on the first papers only (the counts then cover those papers)
        keep = set(sorted({w['pubmed_id'] for w in out})[:papers])
        out = [w for w in out if w['pubmed_id'] in keep]
        cat = [r for r in cat if r['pmid'] in keep]
    sm, sm_info = load_structures(structures)
    sm = AskedKeys(sm)
    log(f'{len(cat):,} catalogue rows, {len(out):,} records; running compare()')
    t0 = time.time()
    dbc, summary, kept = run_compare(root, out, cat, sm)
    log(f'compare() done in {time.time() - t0:.0f} s')
    want = structure_keys(cat)
    assert sm.asked <= want, 'compare() asked the substrate lookups for a key structure_keys() does not name'
    sm_info.update({'keys_compare_asked': len(sm.asked), 'keys_asked_found': len(sm.asked & set(sm)),
                    'keys_named_not_asked': len(want - sm.asked)})
    # the rerun gives every value the frozen export's database_check (and every record its database_note)
    same_dc = sum(1 for w in out if w['database_check'] == frozen_dc[w['measurement_id']])
    same_dn = sum(1 for w in out if w['database_note'] == frozen_dn[w['measurement_id']])
    diff_dc = [w['measurement_id'] for w in out if w['database_check'] != frozen_dc[w['measurement_id']]]
    with gzip.open(FROZEN / 'database_compare.json.gz', 'rb') as f:
        b = f.read()
    assert hashlib.sha256(b).hexdigest() == SHA['database_compare.json']
    frozen_summary = json.loads(b)
    same_summary = {k: summary.get(k) == v for k, v in frozen_summary.items()}
    verify = {'records': len(out), 'database_check_identical': same_dc, 'database_note_identical': same_dn,
              'database_check_differs_examples': diff_dc[:20], 'summary_keys_identical': same_summary,
              'substrate_lookups': sm_info}
    log('verification:', json.dumps({k: v for k, v in verify.items() if k != 'database_check_differs_examples'}))
    exp_rec, exp_val, n_rec = collections.Counter(), collections.Counter(), 0
    for w in out:  # the databases the frozen export names as confirming each value ('sources' of a confirmed value)
        srcs = set()
        for m, ck in (frozen_dc[w['measurement_id']] or {}).items():
            if ck.get('status') == 'confirmed':
                srcs |= set(ck.get('sources') or ())
                exp_val.update(ck.get('sources') or ())
        exp_rec.update(srcs)
        n_rec += bool(srcs)
    verify['export_confirmed'] = {'records': n_rec, 'records_per_database': dict(exp_rec),
                                  'values_per_database': dict(exp_val)}
    D, rel, cats = kept['D'], kept['rel'], kept['cats']
    idx = {id(d): i for i, d in enumerate(D)}
    rows = [{k: d.get(k) for k in ('src', 'pmid', 'ec', 'metric', 'value', 'vstr', 'sub', 'org', 'comment', 'vk')} for d in D]
    conf, label = {}, {}
    for rid, per in rel.items():
        c = [(s, idx[id(d)], t) for s in SOURCES for d, t in per.get(s, {}).get('conf', [])]
        lab = [(s, idx[id(d)], tuple(k)) for s in SOURCES for d, k in per.get(s, {}).get('label', [])]
        if c:
            conf[rid] = c
        if lab:
            label[rid] = lab
    category = {rid: c['cat'] for rid, c in cats.items()}
    paper_orgs = {p: sorted(v) for p, v in kept['paper_orgs'].items()}
    res = {'rows': rows, 'conf': conf, 'label': label, 'category': category, 'link': link, 'counts': counts,
           'verify': verify, 'summary': {k: v for k, v in summary.items() if k != 'unreproduced'},
           'paper_orgs': paper_orgs}
    with open(scratch / 'stage1.pkl', 'wb') as f:
        pickle.dump(res, f, protocol=pickle.HIGHEST_PROTOCOL)
    return res


# ------------------------------------------------------------------------------------------------ local references
ACC_RE = re.compile(r'(?<![A-Z0-9])((?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})(?:-\d+)?)(?![A-Z0-9])')
EC_RE = re.compile(r'(?<![\d.])\d+\.(?:\d+|-)\.(?:\d+|-)\.(?:[A-Za-z]?\d+|-)(?![\d])')


def accessions(text):
    return [m.group(1) for m in ACC_RE.finditer(str(text or '').upper())]


def ec_set(text):
    return {m.group(0) for m in EC_RE.finditer(str(text or ''))}


class Refs:
    """Swiss-Prot headers and sequences, secondary and deleted accessions (the tag's sequences.py on sources/ref), the
    UniProt kinetics download (each entry's taxon, ECs and organism's common name), Rhea's ECs, the ECs BRENDA lists
    values under (the frozen database table) and the STRENDA DB snapshot (the deposited proteins)."""

    def __init__(self, sq, db_values):
        self.sq = sq
        self.deleted = sq.deleted_sp()
        self._sec = {}
        self.head, self.seq, self.tax_name = {}, {}, {}
        with gzip.open(REF / 'uniprot_sprot.fasta.gz', 'rt') as f:
            acc, buf = None, []
            for line in f:
                if line[0] == '>':
                    if acc:
                        self.seq[acc] = ''.join(buf)
                    acc, buf = line.split('|')[1], []
                    os_ = re.search(r' OS=(.*?) OX=', line)
                    ox = re.search(r' OX=(\d+)', line)
                    gn = re.search(r' GN=(\S+)', line)
                    self.head[acc] = (os_.group(1) if os_ else '', ox.group(1) if ox else '', gn.group(1) if gn else '')
                    if ox and os_:
                        self.tax_name.setdefault(ox.group(1), os_.group(1))
                else:
                    buf.append(line.strip())
            if acc:
                self.seq[acc] = ''.join(buf)
        with gzip.open(REF / 'uniprot_kinetics.json.gz', 'rt') as f:
            kin = json.load(f)
        self.kin_release = kin.get('release')
        self.kin, common = {}, collections.defaultdict(set)
        for e in kin['entries']:
            o = e.get('organism') or {}
            ecs = {x.get('value') for x in ((e.get('proteinDescription') or {}).get('recommendedName') or {}).get('ecNumbers', [])}
            self.kin[e['primaryAccession']] = (str(o.get('taxonId') or ''), o.get('scientificName') or '', ecs)
            if o.get('taxonId') and o.get('scientificName'):
                self.tax_name.setdefault(str(o['taxonId']), o['scientificName'])
            # the other names UniProt gives the organism (its common name field often holds a former name), plain
            # names only (no strain qualifier), each standing for one species: 'soybean' and 'Flavobacterium heparinum'
            # -> Glycine max and Pedobacter heparinus
            sci = ' '.join(re.sub(r'\s*\(.*', '', o.get('scientificName') or '').split()[:2])
            for n in [o.get('commonName')] + list(o.get('synonyms') or []):
                if n and sci and '(' not in n and 'strain' not in n.lower():
                    common[n.strip().lower()].add(sci)
        self.common = {k: next(iter(v)) for k, v in common.items() if len(v) == 1}
        z = zipfile.ZipFile(STRENDA_ZIP)
        self.strenda = {r['srn']: r for r in csv.DictReader(io.TextIOWrapper(z.open('csv/Proteins.csv'), encoding='utf-8-sig'))}
        for r in self.strenda.values():
            if r.get('taxon_id') and r.get('organism'):
                self.tax_name.setdefault(r['taxon_id'], r['organism'])
        # ECs known to be current: those BRENDA 2026.1 lists values under, Rhea's, and those of UniProt's entries
        self.current_ec = set()
        with open(db_values) as f:
            next(f)
            for line in f:
                p = line.split('\t', 3)
                if p[0] == 'BRENDA':
                    self.current_ec |= ec_set(p[2])
        with open(REF / 'rhea2ec.tsv') as f:
            next(f)
            for line in f:
                self.current_ec |= ec_set(line.rstrip('\n').split('\t')[-1])
        for _, _, ecs in self.kin.values():
            self.current_ec |= {e for e in ecs if e}
        # the ECs of each Swiss-Prot entry the local files give: its Rhea reactions (rhea2uniprot_sprot.tsv with
        # rhea2ec.tsv) and, for UniProt's kinetics entries, the ECs of its names
        rhea_ec = collections.defaultdict(set)
        with open(REF / 'rhea2ec.tsv') as f:
            next(f)
            for line in f:
                p = line.rstrip('\n').split('\t')
                if len(p) == 4:
                    rhea_ec[p[0]].add(p[3])
                    rhea_ec[p[2]].add(p[3])
        self.entry_ec = collections.defaultdict(set)
        with open(REF / 'rhea2uniprot_sprot.tsv') as f:
            next(f)
            for line in f:
                p = line.rstrip('\n').split('\t')
                if len(p) == 4:
                    self.entry_ec[p[3]] |= rhea_ec.get(p[0], set()) | rhea_ec.get(p[2], set())
        for e in kin['entries']:
            pd = e.get('proteinDescription') or {}
            for nm in [pd.get('recommendedName') or {}] + list(pd.get('alternativeNames') or []):
                self.entry_ec[e['primaryAccession']] |= {x.get('value') for x in nm.get('ecNumbers') or [] if x.get('value')}

    def secondary(self, a):
        if a not in self._sec:
            self._sec[a] = self.sq.secondary(a)
        return self._sec[a]

    def keys(self, acc):
        """The current Swiss-Prot entries an accession stands for, and how: ('swissprot' its own entry; 'merged' or
        'split' a secondary accession of one or several entries (sec_ac.txt); 'deleted' (delac_sp.txt) or 'other' (not
        in the local Swiss-Prot: TrEMBL or unknown), the accession itself)."""
        base = acc.split('-')[0]
        if base in self.head:
            return {base}, 'swissprot'
        prim = self.secondary(base)
        if prim:
            return set(prim), 'merged' if len(prim) == 1 else 'split'
        return {base}, 'deleted' if base in self.deleted else 'other'


# ------------------------------------------------------------------------------------------------ stage 2
def db_accessions(d, refs):
    """The UniProt accessions a database row names: UniProt's own row (its entry), OED and SKiD rows ('UniProt X',
    'X,Y'), a STRENDA row through the protein its experiment deposited; None for BRENDA and SABIO-RK, whose rows in
    sources/db_values.tsv name none."""
    src, com = d['src'], d['comment'] or ''
    if src == 'UniProt':
        m = re.match(r'UniProt\s+([^\s;]+)', com)
        return accessions(m.group(1)) if m else []
    if src in ('OED', 'SKiD'):
        return [a for g in re.findall(r'UniProt\s+([^\s;]+)', com) for a in accessions(g)]
    if src == 'STRENDA':
        m = re.match(r'STRENDA\s+(\S+)', com)
        p = refs.strenda.get(m.group(1)) if m else None
        return accessions(p['uniprotkb_xml']) if p else []
    return None


def db_taxon(d, refs):
    """The NCBI taxon a database row gives for its organism: UniProt's entry (the kinetics download), the protein a
    STRENDA experiment deposited; '' for the others."""
    if d['src'] == 'UniProt':
        a = accessions((re.match(r'UniProt\s+([^\s;]+)', d['comment'] or '') or [None, ''])[1])
        return refs.kin.get(a[0].split('-')[0], ('',))[0] if a else ''
    if d['src'] == 'STRENDA':
        m = re.match(r'STRENDA\s+(\S+)', d['comment'] or '')
        return (refs.strenda.get(m.group(1)) or {}).get('taxon_id', '') if m else ''
    return ''


def entry_relation(a, b, refs):
    """How CatLog's accession a and a database accession b name one entry: 'same accession', 'isoform of the same
    entry', 'secondary or merged accession', 'split entry' (sec_ac.txt); None when they name different entries."""
    if a == b:
        return 'same accession'
    if a.split('-')[0] == b.split('-')[0]:
        return 'isoform of the same entry'
    (ka, ha), (kb, hb) = refs.keys(a), refs.keys(b)
    if ka & kb:
        return 'split entry' if 'split' in (ha, hb) else 'secondary or merged accession'
    return None


def same_sequence(cseq, dseq, muts):
    """CatLog's UniProt sequence (the entry's, with the record's mutations applied) is the database entry's sequence:
    identical, or different only by the record's stated mutations (CatLog's residue the mutant, the entry's the wild
    type). None when either sequence is missing."""
    if not cseq or not dseq:
        return None
    if cseq == dseq:
        return True
    if len(cseq) != len(dseq) or not muts:
        return False
    want = collections.Counter((m[0], m[-1]) for m in muts)
    got = collections.Counter((b, a) for a, b in zip(cseq, dseq) if a != b)
    return all(want[k] >= n for k, n in got.items())


def sort_entry_difference(a, bs, dbc, refs, cseq='', muts=()):
    """What the local files tell about two entries that differ: both in the local Swiss-Prot and of the same taxon (another
    entry of the organism: a paralog or family member, not decidable offline), of the same species but another taxon
    (another strain), of another species (same genus or not); or not sortable (an accession outside the local
    Swiss-Prot). The database accession closest to CatLog's decides. Also whether CatLog's sequence is that entry's."""
    rank = {'same organism, another entry (not decidable offline)': 0, 'same species, another strain': 1,
            'another species, same genus': 2, 'another genus': 3, 'outside the local Swiss-Prot (not sortable)': 4}
    best = None
    ka, ha = refs.keys(a)
    for b in bs:
        kb, hb = refs.keys(b)
        ea, eb = sorted(ka)[0], sorted(kb)[0]
        seq_same = same_sequence(cseq, refs.seq.get(eb, '') if hb in ('swissprot', 'merged') else '', muts)
        if ha in ('swissprot', 'merged') and hb in ('swissprot', 'merged') and ea in refs.head and eb in refs.head:
            (osa, oxa, gna), (osb, oxb, gnb) = refs.head[ea], refs.head[eb]
            if oxa and oxa == oxb:
                c = 'same organism, another entry (not decidable offline)'
            elif dbc.genus_species(osa) == dbc.genus_species(osb):
                c = 'same species, another strain'
            elif dbc.genus_species(osa).split()[:1] == dbc.genus_species(osb).split()[:1]:
                c = 'another species, same genus'
            else:
                c = 'another genus'
            cand = (rank[c], c, b, seq_same, f'CatLog {ea} {osa} {gna}; database {eb} {osb} {gnb}')
        else:
            c = 'outside the local Swiss-Prot (not sortable)'
            cand = (rank[c], c, b, seq_same, f'CatLog {a} ({ha}); database {b} ({hb})')
        if best is None or (cand[0], cand[3] is not True) < (best[0], best[3] is not True):
            best = cand
    return best


def ec_levels(e):
    return e.split('.')


def ec_relation(x, y):
    """'same' (identical), 'levels' (equal at every level both give, one side incomplete: '1.1.1.-' and '1.1.1.1'), or the
    number of leading levels they share (0-3)."""
    if x == y:
        return 'same'
    a, b = ec_levels(x), ec_levels(y)
    shared = 0
    for p, q in zip(a, b):
        if p == '-' or q == '-':
            return 'levels'
        if p != q:
            return shared
        shared += 1
    return shared


SPECIES_VAGUE = re.compile(r'^\S+(?:\s+(?:sp|spp|cf|aff)\.?)?$', re.I)


def species_key(o, dbc):
    """(genus, species) of an organism text, species '' when it names the genus only ('Pseudomonas sp.')."""
    g = dbc.genus_species(o).split()
    if not g:
        return '', ''
    if len(g) == 1 or g[1].rstrip('.') in ('sp', 'spp', 'cf', 'aff', 'bacterium', 'strain', 'str', 'isolate'):
        return g[0], ''
    return g[0], g[1]


SAME_ORG = 'same organism, another entry (not decidable offline)'
OTHER_ENZYME = 'the entry of another enzyme CatLog links in the same paper (a number both share)'
# how an organism agreement was reached, strictest first: a record counts under the loosest rule one of its databases
# needed
ORG_ROUTES = ('the same taxon', 'the same binomial',
              "another name for the organism (its taxon's name or one UniProt lists; a common name or a binomial in "
              "parentheses, compare()'s org_names)",
              "compare()'s epithet rules (the same epithet under another genus; the same genus with an epithet stem of 5 or "
              "more letters)")
EC_ROUTES = ('the same EC', 'equal at the levels both give')
ENTRY_ROUTES = ('same accession', 'isoform of the same entry', 'secondary or merged accession', 'split entry')
SHORT_EC = re.compile(r'\d+(?:\.\d+){0,2}')
ONLY_DB, ONLY_CAT = "only the database's entry carries the paper's EC", "only CatLog's entry carries the paper's EC"


def short_ecs(text):
    """The ECs of fewer than four numbers a database row gives ('1.1.1', '3.4.21', '3': SABIO-RK), as 'n.n.n.-'."""
    return {'.'.join((t.split('.') + ['-'] * 3)[:4]) for t in re.split(r'[\s/;,]+', str(text or '').replace('Complex', ' '))
            if SHORT_EC.fullmatch(t)}


def same_organism_by_ec(ca, bs, L, refs):
    """Another entry of the same organism: the EC the paper prints tells the two entries apart when only one of them
    carries it (each Swiss-Prot entry's ECs as the local files give them: its Rhea reactions, the names of UniProt's
    kinetics entries). The sorted label (None: still not decidable offline) and why."""
    full = {e for e in ec_set(L.get('ec_number')) if '-' not in e}
    if not full:
        return None, 'CatLog gives no full EC'
    if (L.get('ec_source') or '') != 'paper':
        return None, "CatLog's EC from its UniProt entry or the databases, not the paper"
    ka = refs.keys(ca)[0]
    ox = {refs.head[e][1] for e in ka if e in refs.head}
    c_ecs = set().union(*[refs.entry_ec.get(e, set()) for e in ka])
    d_ecs = set().union(*[refs.entry_ec.get(e, set()) for b in bs for e in refs.keys(b)[0]
                          if e in refs.head and refs.head[e][1] in ox])
    c_has, d_has = bool(full & c_ecs), bool(full & d_ecs)
    if d_has and not c_has:
        return "same organism, another entry: only the database's entry carries the EC the paper prints", ONLY_DB
    if c_has and not d_has:
        return "same organism, another entry: only CatLog's entry carries the EC the paper prints", ONLY_CAT
    if c_has:
        return None, "both entries carry the paper's EC"
    return None, "neither entry carries the paper's EC" if c_ecs or d_ecs else 'no EC known for either entry'


def stage2(s1, root):
    sys.path.insert(0, str(root / 'tools'))
    import dbcompare as dbc, sequences as sq
    assert Path(dbc.__file__).resolve().parent == (root / 'tools').resolve()
    rows, conf, link, paper_orgs = s1['rows'], s1['conf'], s1['link'], s1['paper_orgs']
    # every confirmed value has its confirming rows, and only confirmed values have them
    confirmed = {rid for rid, c in s1['category'].items() if c == 'CONFIRMED'}
    assert set(conf) == confirmed, 'pass 1 rows <-> CONFIRMED'
    rec = {}  # measurement_id -> {database: set of row indexes}
    vals = collections.Counter()
    for mid, L in link.items():
        per = {}
        for m, rid in L['metrics'].items():
            for s, i, t in conf.get(rid, ()):
                per.setdefault(s, set()).add(i)
            for s in {s for s, _, _ in conf.get(rid, ())}:
                vals[s] += 1
        if per:
            rec[mid] = per
    log('reading the local reference files')
    refs = Refs(sq, root / 'sources' / 'db_values.tsv')
    # what CatLog links to all the records of each paper: a database row whose entry or EC is that of another enzyme of
    # the paper matched a number two enzymes share (compare() pairs by substrate and variant, not by enzyme)
    paper_entries, paper_ecs = collections.defaultdict(set), collections.defaultdict(set)
    for L in link.values():
        for a in accessions(L.get('uniprot_id')):
            paper_entries[L['pubmed_id']] |= refs.keys(a)[0]
        if (L.get('ec_source') or '') == 'paper' or (L.get('ec_source') or '').startswith('UniProt'):
            paper_ecs[L['pubmed_id']] |= ec_set(L.get('ec_number'))

    out = {'records_with_a_confirmed_value': len(rec), 'confirmed_values': len(conf),
           'records_per_database': {s: sum(1 for per in rec.values() if s in per) for s in SOURCES},
           'confirmed_values_per_database': {s: vals[s] for s in SOURCES},
           'papers_with_a_confirmed_value': len({link[m]['pubmed_id'] for m in rec}),
           # BRENDA's and SABIO-RK's rows name no UniProt entry: these records cannot test it
           'records_confirmed_only_by_brenda_or_sabio_rk': sum(1 for per in rec.values() if set(per) <= {'BRENDA', 'SABIO-RK'})}
    # the confirming rows kept from compare() are those of the databases the frozen export names, record by record
    ex = s1['verify']['export_confirmed']
    assert ex['records'] == out['records_with_a_confirmed_value']
    assert all(ex['records_per_database'].get(s, 0) == out['records_per_database'][s] for s in SOURCES)
    assert all(ex['values_per_database'].get(s, 0) == out['confirmed_values_per_database'][s] for s in SOURCES)
    diffs = []

    def tally():
        return {'records': 0, 'agree': 0, 'agree_by': collections.Counter(), 'catlog_empty': 0, 'database_empty': 0,
                'both_empty': 0, 'empty_by': collections.Counter(), 'differ': 0, 'differ_sorted': collections.Counter(),
                'differ_sequence': collections.Counter(), 'differ_sequence_any_accession': collections.Counter(),
                'same_organism_by_ec': collections.Counter(), 'several_database_answers': 0,
                'papers': collections.defaultdict(set)}

    def add(t, outcome, pmid, how=None):
        t['records'] += 1
        t[outcome] += 1
        t['papers'][outcome].add(pmid)
        t['papers']['records'].add(pmid)
        if how and outcome == 'agree':
            t['agree_by'][how] += 1
        if how and outcome == 'differ':
            t['differ_sorted'][how] += 1

    per_record = collections.defaultdict(dict)  # (field, mid) -> {database: outcome}
    route = collections.defaultdict(dict)  # (field, mid) -> {database: the rule an agreement needed}
    def seq_label(same, cseq):
        return {True: "CatLog's sequence is the database entry's", False: 'different sequences'}.get(same) or (
            "not comparable: the database's entry is outside the local Swiss-Prot" if cseq else
            'not comparable: CatLog keeps no UniProt sequence for the record')

    # ---- UniProt entry
    T = {s: tally() for s in SOURCES}
    for mid, per in rec.items():
        L = link[mid]
        ca = (accessions(L.get('uniprot_id')) or [''])[0]
        for s, idxs in per.items():
            got = [db_accessions(rows[i], refs) for i in idxs]
            if any(g is None for g in got):
                continue  # BRENDA, SABIO-RK: no accession in the table
            bs = sorted({a for g in got for a in g})
            t = T[s]
            if len({frozenset(refs.keys(b)[0]) for b in bs}) > 1:
                t['several_database_answers'] += 1
            if not ca or not bs:
                outcome = 'both_empty' if not ca and not bs else 'catlog_empty' if not ca else 'database_empty'
                add(t, outcome, L['pubmed_id'])
                per_record[('uniprot', mid)][s] = outcome
                continue
            hows = [h for h in (entry_relation(ca, b, refs) for b in bs) if h]
            if hows:
                several = len({frozenset(refs.keys(b)[0]) for b in bs}) > 1
                how = route[('uniprot', mid)][s] = min(hows, key=ENTRY_ROUTES.index)
                add(t, 'agree', L['pubmed_id'], how + (' (one of several the database names)' if several else ''))
                per_record[('uniprot', mid)][s] = 'agree'
                continue
            muts = sorted(dbc.mutset(L.get('mutation_signature') or ''))
            cseq = L.get('uniprot_sequence') or ''
            srt = sort_entry_difference(ca, bs, dbc, refs, cseq, muts)
            if any(refs.keys(b)[0] & paper_entries[L['pubmed_id']] for b in bs):
                srt = (srt[0], OTHER_ENZYME, *srt[2:])
            if srt[1] == SAME_ORG:  # the EC the paper prints can tell two entries of one organism apart
                lab, why = same_organism_by_ec(ca, bs, L, refs)
                t['same_organism_by_ec'][why] += 1
                if lab:
                    srt = (srt[0], lab, *srt[2:])
            add(t, 'differ', L['pubmed_id'], srt[1])
            # CatLog's sequence (its entry's, with the record's mutations) against the database's: the accession that
            # sorts the pair (the one closest in organism), and every accession the database names, each through every
            # current entry it stands for (sec_ac.txt; an accession split into several entries too), equal when one is
            sq_ = seq_label(srt[3], cseq)
            t['differ_sequence'][sq_] += 1
            each = [same_sequence(cseq, refs.seq[e], muts) for b in bs for e in sorted(refs.keys(b)[0]) if e in refs.seq]
            t['differ_sequence_any_accession'][seq_label(True if True in each else False if False in each else None,
                                                         cseq)] += 1
            diffs.append({'field': 'UniProt entry', 'database': s, 'pmid': L['pubmed_id'], 'measurement_id': mid,
                          'catlog': ca, 'database_value': ','.join(bs), 'sorted': srt[1],
                          'note': f'{sq_}; {srt[4]}', 'uniprot_how': L.get('uniprot_how') or ''})
            per_record[('uniprot', mid)][s] = 'differ'
    out['uniprot_entry'] = T

    # ---- EC number (CatLog's EC printed in the paper or from UniProt; never one taken from the databases)
    T = {s: tally() for s in SOURCES}
    TK = {k: {s: tally() for s in SOURCES} for k in ('paper', 'UniProt')}  # the same, by where CatLog's EC came from
    T_short = tally()  # SABIO-RK, its ECs of fewer than four numbers read as 'n.n.n.-'
    excluded = collections.Counter()
    ec_kind, sabio_rows, short_rows, short_records = {}, set(), set(), set()

    def current(e):  # an incomplete EC ('1.1.1.-') cannot be checked
        return '-' in e or e in refs.current_ec

    def classify(ce, de, pmid):
        """agree (and how), differ (how the local files sort it, and the levels both share), or a side empty."""
        if not ce or not de:
            return ('both_empty' if not ce and not de else 'catlog_empty' if not ce else 'database_empty'), None, None
        rels = [ec_relation(x, y) for x in ce for y in de]
        if 'same' in rels:
            return 'agree', 'same EC' + (' (one of several)' if len(ce) > 1 or len(de) > 1 else ''), None
        if 'levels' in rels:
            return 'agree', 'equal at the levels both give', None
        levels = {3: 'same first three numbers', 2: 'same first two numbers', 1: 'same class only',
                  0: 'another class'}[max(r for r in rels if isinstance(r, int))]
        if de & (paper_ecs[pmid] - ce):
            how = "the EC of another enzyme CatLog has in the same paper (a number both share)"
        elif not any(current(e) for e in ce):
            how = "CatLog's EC in no BRENDA entry with values, Rhea reaction or UniProt entry (likely transferred)"
        elif not any(current(e) for e in de):
            how = "the database's EC in no BRENDA entry with values, Rhea reaction or UniProt entry"
        else:
            how = f'not sortable offline ({levels})'
        return 'differ', how, levels
    for mid, per in rec.items():
        L = link[mid]
        src_ec = L.get('ec_source') or ''
        if src_ec.startswith('databases'):
            excluded['records: EC from the databases'] += 1
            for s in per:
                excluded[f'{s}: EC from the databases'] += 1
            continue
        assert src_ec in ('', 'paper') or src_ec.startswith('UniProt'), src_ec
        assert bool(src_ec) == bool(L.get('ec_number')), (mid, src_ec)
        kind = 'UniProt' if src_ec.startswith('UniProt') else 'paper' if src_ec else None
        ec_kind[mid] = kind
        ce = ec_set(L.get('ec_number'))
        assert bool(ce) == bool(src_ec), (mid, L.get('ec_number'))
        for s, idxs in per.items():
            de = set().union(*[ec_set(rows[i]['ec']) for i in idxs])
            outcome, how, levels = classify(ce, de, L['pubmed_id'])
            if outcome == 'differ':
                diffs.append({'field': 'EC number', 'database': s, 'pmid': L['pubmed_id'], 'measurement_id': mid,
                              'catlog': '; '.join(sorted(ce)), 'database_value': '; '.join(sorted(de)), 'sorted': how,
                              'note': f"CatLog's EC from {src_ec}; {levels}", 'uniprot_how': L.get('uniprot_how') or ''})
            add(T[s], outcome, L['pubmed_id'], how)
            if kind:
                add(TK[kind][s], outcome, L['pubmed_id'], how)
            per_record[('ec', mid)][s] = outcome
            if outcome == 'agree':
                route[('ec', mid)][s] = EC_ROUTES[how == 'equal at the levels both give']
            short_outcome = outcome
            if s == 'SABIO-RK':  # SABIO-RK's ECs of fewer than four numbers are no EC above; here read as 'n.n.n.-'
                sabio_rows |= idxs
                short = {i for i in idxs if short_ecs(rows[i]['ec'])}
                if short:
                    short_rows |= short
                    short_records.add(mid)
                    short_outcome = classify(ce, de | set().union(*[short_ecs(rows[i]['ec']) for i in short]),
                                             L['pubmed_id'])[0]
                add(T_short, short_outcome, L['pubmed_id'])
            per_record[('ec_short_read_as_n.n.n.-', mid)][s] = short_outcome
    out['ec_number'] = T
    out['ec_number_by_catlog_source'] = TK
    out['ec_excluded'] = dict(excluded)
    out['ec_source_of_records'] = dict(collections.Counter(
        'databases' if (link[m].get('ec_source') or '').startswith('databases') else
        'UniProt' if (link[m].get('ec_source') or '').startswith('UniProt') else (link[m].get('ec_source') or 'none')
        for m in rec))
    out['ec_sabio_rk_short'] = {'confirming_rows': len(sabio_rows), 'rows_with_fewer_than_four_numbers': len(short_rows),
                                'records_with_such_a_row': len(short_records), 'SABIO-RK, read as n.n.n.-': T_short}

    # ---- organism (species level), papers with one CatLog organism only
    T = {s: tally() for s in SOURCES}
    excluded = collections.Counter()
    epithet_pairs, epithet_kind = collections.Counter(), collections.Counter()  # pairs agreeing by the epithet rules only
    INFRA = re.compile(r'(?:subsp\.|subspecies|serovar|serotype|biovar|bv\.|pathovar|pv\.|var\.)\s+([A-Za-z]+)', re.I)
    NOT_ORG = re.compile(r'^(?:plasmid|synthetic|vector|cloning|uncultured|unknown|unidentified|unclassified|environmental|'
                         r'metagenome)\b', re.I)

    def clean(o):  # no organism ('plasmid pGEM-T-easy', 'uncultured bacterium'), and the 'Candidatus' prefix left out
        o = (o or '').strip().strip('"\'')
        return '' if NOT_ORG.search(o) else re.sub(r'^(?:Candidatus|Ca\.)\s+', '', o)

    def stem(e):
        return re.sub(r'(?:us|um|is|ae|a|e|i)$', '', e)

    def names(o, x):  # an organism text, and the species its taxon or another name UniProt gives stands for
        out_ = {o} if o else set()
        if x and x in refs.tax_name:
            out_.add(clean(refs.tax_name[x]))
        if o and o.strip().lower() in refs.common:
            out_.add(refs.common[o.strip().lower()])
        return {n for n in out_ if n}

    def infra(o):  # the infraspecific names an organism text gives ('subsp. tengcongensis', 'Naja naja kaouthia')
        w = {m.lower() for m in INFRA.findall(o)}
        t = re.findall(r'[A-Za-z]+', re.sub(r'\(.*?\)', ' ', o))
        if len(t) >= 3 and t[0][:1].isupper() and t[1].islower() and t[2].islower():
            w.add(t[2])
        return w

    def one_letter(a, b):  # edit distance at most 1
        if a == b:
            return True
        if abs(len(a) - len(b)) > 1:
            return False
        if len(a) == len(b):
            return sum(x != y for x, y in zip(a, b)) == 1
        a, b = (a, b) if len(a) < len(b) else (b, a)
        return any(b[:i] + b[i + 1:] == a for i in range(len(b)))

    def org_route(co, ct, cn, items):
        """The strictest rule under which an agreeing pair agrees (ORG_ROUTES): the same taxon; the same binomial
        (genus and epithet of the two organism texts); the same binomial through another name of either organism (its
        taxon's name, a name UniProt lists: names(); a common name or a binomial in parentheses: compare()'s
        org_names); else through compare()'s epithet rules (org_fits), which the agreement test also applies."""
        if any(ct and x and ct == x for o, x in items):
            return ORG_ROUTES[0]
        k = species_key(co, dbc)
        if k[1] and any(o and species_key(o, dbc) == k for o, x in items):
            return ORG_ROUTES[1]
        mine = {species_key(p, dbc) for p in cn | dbc.org_names(co)}
        theirs = {species_key(q, dbc) for o, x in items for q in names(o, x) | dbc.org_names(o)}
        if any(sp for _, sp in mine & theirs):
            return ORG_ROUTES[2]
        return ORG_ROUTES[3]
    for mid, per in rec.items():
        L = link[mid]
        pmid = L['pubmed_id']
        porgs = set(paper_orgs.get(pmid, ()))
        if len(porgs) != 1:
            excluded['records: paper with several CatLog organisms' if porgs else 'records: paper names no organism'] += 1
            continue
        assert (L.get('organism_source') or '') in ('', 'paper'), L.get('organism_source')
        co, ct = clean(L.get('organism')), str(L.get('taxon_id') or '')
        cn = names(co, ct)
        ckeys = {species_key(n, dbc) for n in cn} | {species_key(k, dbc) for k in dbc.org_names(co)}
        ca = (accessions(L.get('uniprot_id')) or [''])[0]
        entry_os = ''
        if ca:
            ka, ha = refs.keys(ca)
            entry_os = refs.head.get(sorted(ka)[0], ('',))[0] if ha in ('swissprot', 'merged') else ''
        for s, idxs in per.items():
            items = [(clean(rows[i]['org']), db_taxon(rows[i], refs)) for i in idxs]
            items = [(o, x) for o, x in items if o or x]
            t = T[s]
            how = None
            # species level: the same taxon where both give one; else a side that names only the other's genus
            # ('Pseudomonas', 'Pseudomonas sp. JS666') has no species to compare and counts as empty
            dn = {q for o, x in items for q in names(o, x)}
            dkeys = {species_key(q, dbc) for q in dn}
            cg = {g for g, _ in ckeys}
            if not co or not items:
                outcome = 'both_empty' if not co and not items else 'catlog_empty' if not co else 'database_empty'
            elif any(ct and x and ct == x for o, x in items):
                outcome = 'agree'
            elif (not any(sp for _, sp in ckeys) or not any(sp for _, sp in dkeys)) and cg & {g for g, _ in dkeys}:
                c_sp, d_sp = any(sp for _, sp in ckeys), any(sp for _, sp in dkeys)
                outcome, how = (('both_empty', '(both name the same genus only)') if not c_sp and not d_sp else
                                ('catlog_empty', '(CatLog names the genus only)') if not c_sp else
                                ('database_empty', '(the database names the genus only)'))
            else:
                with_sp = [(o, x) for o, x in items if any(sp for _, sp in (species_key(q, dbc) for q in names(o, x)))]
                if any(sp for _, sp in ckeys) and any(o and dbc.org_fits(co, o, porgs) for o, x in with_sp):
                    outcome = 'agree'
                elif any(dbc.org_fits(p_, q, porgs) or dbc.genus_species(p_) == dbc.genus_species(q)
                         for o, x in with_sp for p_ in cn if species_key(p_, dbc)[1] for q in names(o, x)
                         if species_key(q, dbc)[1]):
                    outcome = 'agree'
                else:
                    outcome = 'differ'
                    if entry_os and any(dbc.org_fits(entry_os, q, porgs) or dbc.genus_species(entry_os) == dbc.genus_species(q)
                                        for q in dn if species_key(q, dbc)[1]):
                        how = "the species of CatLog's own UniProt entry (the paper's name another name for it)"
                    elif any((g == g2 and sp and sp2 and one_letter(sp, sp2)) or (sp and sp == sp2 and one_letter(g, g2))
                             for g, sp in ckeys for g2, sp2 in dkeys):
                        how = 'the same name spelled one letter differently'
                    elif any(sp and sp2 and g != g2 and len(stem(sp)) >= 4 and stem(sp) == stem(sp2)
                             for g, sp in ckeys for g2, sp2 in dkeys):
                        how = 'same species epithet under another genus (likely a reclassification)'
                    elif any(sp in infra(q) for _, sp in ckeys if sp for q in dn) or \
                            any(sp2 in infra(co) for _, sp2 in dkeys if sp2):
                        how = 'named as a subspecies, serovar or biovar of the other species'
                    elif 'virus' in co.lower() and any('virus' in q.lower() for q in dn):
                        how = 'a virus named two ways (not sortable offline)'
                    elif any(g in cg for g, _ in dkeys):
                        how = 'not sortable offline (another species, same genus)'
                    else:
                        how = 'not sortable offline (another genus)'
                    diffs.append({'field': 'organism', 'database': s, 'pmid': pmid, 'measurement_id': mid, 'catlog': co,
                                  'database_value': '; '.join(sorted({o or refs.tax_name.get(x, '') for o, x in items})),
                                  'sorted': how, 'note': f"CatLog taxon {ct or '-'}; database taxon "
                                  f"{', '.join(sorted({x for _, x in items if x})) or '-'}; CatLog's entry {ca or '-'} {entry_os}",
                                  'uniprot_how': L.get('uniprot_how') or ''})
            if outcome == 'agree':
                how = route[('organism', mid)][s] = org_route(co, ct, cn, items)
                if how == ORG_ROUTES[3]:
                    mine = {species_key(p_, dbc) for p_ in cn | dbc.org_names(co)}
                    theirs = {species_key(q, dbc) for o, x in items for q in names(o, x) | dbc.org_names(o)}
                    epithet_kind['the same genus, the epithet with another ending' if any(
                        g == g2 and sp and sp2 for g, sp in mine for g2, sp2 in theirs)
                        else 'the same epithet under another genus'] += 1
                    epithet_pairs[(co, '; '.join(sorted({o for o, x in items if o})))] += 1
            if outcome in ('agree', 'differ'):
                add(t, outcome, pmid, how)
            else:
                add(t, outcome, pmid)
                if how:
                    t['empty_by'][how] += 1
            per_record[('organism', mid)][s] = outcome
    out['organism'] = T
    out['organism_excluded'] = dict(excluded)
    out['organism_epithet_rules'] = {'pairs': sum(epithet_kind.values()), 'by_rule': dict(epithet_kind),
                                     'commonest_pairs': [[a, b, n] for (a, b), n in epithet_pairs.most_common(25)]}

    # ---- across the databases: a record agrees with every database that names the field, or differs from one
    def across(field, skip=lambda mid, s: False):
        """Records that agree with every database naming the field (split by the loosest rule one of them needed), that
        differ from one, or that no database lets compare (counting those where a database names one, CatLog none)."""
        order = {'uniprot': ENTRY_ROUTES, 'ec': EC_ROUTES, 'organism': ORG_ROUTES}.get(field)
        c, papers = collections.Counter(), collections.defaultdict(set)
        for (f, mid), per in per_record.items():
            if f != field:
                continue
            per = {s: o for s, o in per.items() if not skip(mid, s)}
            if not per:
                continue
            o = set(per.values())
            k = 'differ_from_one' if 'differ' in o else 'agree_with_all' if 'agree' in o else 'no_database_to_compare'
            c[k] += 1
            papers[k].add(link[mid]['pubmed_id'])
            if k == 'no_database_to_compare' and 'catlog_empty' in o:
                c['catlog_names_none_a_database_names_one'] += 1
            if k == 'agree_with_all' and order:
                loosest = max(order.index(route[(field, mid)][s]) for s, x in per.items() if x == 'agree')
                c[f'agree_with_all, loosest rule: {order[loosest]}'] += 1
        return {**dict(c), 'papers': {k: len(v) for k, v in papers.items()}}
    for field, key in (('uniprot', 'uniprot_entry'), ('ec', 'ec_number'), ('organism', 'organism')):
        out[key + '_any_database'] = across(field)
    # the EC count with SABIO-RK's short ECs read as 'n.n.n.-', and without the comparison that is circular: an EC CatLog
    # took from a UniProt entry against UniProt's own rows
    def circular(mid, s):
        return s == 'UniProt' and ec_kind.get(mid) == 'UniProt'
    out['ec_number_any_database_variants'] = {
        "SABIO-RK's ECs of fewer than four numbers read as n.n.n.-": across('ec_short_read_as_n.n.n.-'),
        "without UniProt's rows where CatLog took its EC from UniProt": across('ec', circular)}
    only = collections.Counter()  # records whose one comparison is that circular one
    for (f, mid), per in per_record.items():
        if f != 'ec':
            continue
        circ = {x for s, x in per.items() if x in ('agree', 'differ') and circular(mid, s)}
        if circ and not any(x in ('agree', 'differ') and not circular(mid, s) for s, x in per.items()):
            only['differ' if 'differ' in circ else 'agree'] += 1
    out['ec_records_compared_only_circularly'] = dict(only)

    def plain(t):
        for k in ('agree_by', 'empty_by', 'differ_sequence', 'differ_sequence_any_accession', 'differ_sorted',
                  'same_organism_by_ec'):
            t[k] = dict(t[k])
        t['papers'] = {k: len(v) for k, v in t['papers'].items()}
    for key in ('uniprot_entry', 'ec_number', 'organism'):
        for t in out[key].values():
            plain(t)
    for per_src in out['ec_number_by_catlog_source'].values():
        for t in per_src.values():
            plain(t)
    plain(T_short)
    return out, diffs, refs, dbc


# ------------------------------------------------------------------------------------------------ stage 3
ALIGN = {'match': 2, 'mismatch': -1, 'open': -5, 'extend': -0.5}  # local alignment scores (Biopython PairwiseAligner)
TAG_MOTIFS = (('His tag', r'H{5,}'), ('thrombin site', r'LVPRGS'), ('TEV site', r'ENLYFQ'), ('enterokinase site', r'DDDDK'),
              ('S-tag', r'KETAAAKFERQHMDS'), ('Strep-tag', r'WSHPQFEK'), ('FLAG tag', r'DYKDDDDK'),
              ('myc tag', r'EQKLISEEDL'), ('HA tag', r'YPYDVPDYA'), ('T7 tag', r'MASMTGGQQMG'))
STATED_END = re.compile(r'truncat|residues?\s+\d+\s*[-–]\s*\d+|amino acids?\s+\d+\s*[-–]\s*\d+|signal (?:peptide|sequence)|'
                        r'lacking|without the|Δ\s*\d|delta\s*\d|N-terminal(?:ly)? (?:deleted|truncated)|mature', re.I)


def tags_in(flank):
    return [name for name, pat in TAG_MOTIFS if re.search(pat, flank)]


def strip_tags(q):
    """A deposited sequence without the tags its first 40 and last 30 residues carry (for an exact lookup)."""
    n, c, k = 0, len(q), max(0, len(q) - 30)
    for _, pat in TAG_MOTIFS:
        for m in re.finditer(pat, q[:40]):
            n = max(n, m.end())
        for m in re.finditer(pat, q[k:]):
            c = min(c, k + m.start())
    return q[n:c] if n < c else q


def stage3(s1, refs, dbc):
    """CatLog's sequence against the construct the authors deposited in STRENDA DB (the export's deposited_sequence)."""
    from Bio import Align
    al = Align.PairwiseAligner(mode='local')
    al.match_score, al.mismatch_score, al.open_gap_score, al.extend_gap_score = (ALIGN['match'], ALIGN['mismatch'],
                                                                                ALIGN['open'], ALIGN['extend'])
    recs, lines = [], []
    for mid, L in s1['link'].items():
        if 'deposited_sequence' in L:
            recs.append((L['pubmed_id'], mid, L))
    c = collections.Counter()
    pairs = collections.defaultdict(set)
    mut_check = collections.Counter()
    for pmid, mid, L in sorted(recs):
        cs_, ds_ = L.get('sequence') or '', L.get('deposited_sequence') or ''
        srn = (re.match(r'STRENDA\s+(\S+?):', L.get('deposited_sequence_note') or '') or [None, ''])[1]
        prot = refs.strenda.get(srn) or {}
        stated = set(dbc.mutset(L.get('mutation_signature') or ''))
        row = {'pmid': pmid, 'measurement_id': mid, 'strenda': srn, 'uniprot_id': L.get('uniprot_id') or '',
               'variant': L.get('mutation_signature') or ('wild type' if L.get('wild_type') else ''),
               'catlog_length': len(cs_), 'deposit_length': len(ds_), 'tags_removed': '', 'outcome': '', 'detail': ''}
        if not re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWYXBZUO]{20,}', ds_):
            row['outcome'] = 'deposit holds no sequence'
            row['detail'] = f'deposited_sequence is {ds_!r}'
        elif not cs_:
            row['outcome'] = 'CatLog has no sequence'
            row['detail'] = (L.get('sequence_check') or L.get('sequence_basis') or '')[:120]
        else:
            a = al.align(cs_, ds_)[0]
            tb, qb = a.aligned
            if len(tb) == 0:
                cov, ident, subs, gaps = 0.0, 0.0, [], 0
                c0 = c1 = d0 = d1 = 0
            else:
                c0, c1, d0, d1 = tb[0][0], tb[-1][1], qb[0][0], qb[-1][1]
                subs = [(t0 + i + 1, cs_[t0 + i], ds_[q0 + i]) for (t0, t1), (q0, q1) in zip(tb, qb)
                        for i in range(t1 - t0) if cs_[t0 + i] != ds_[q0 + i]]
                alen = sum(t1 - t0 for t0, t1 in tb)
                ident = (alen - len(subs)) / alen
                cov = alen / min(len(cs_), len(ds_))
                gaps = len(tb) - 1
            dn, dc, cn, cc = ds_[:d0], ds_[d1:], cs_[:c0], cs_[c1:]
            removed = []
            for side, fl in (('N', dn), ('C', dc)):
                if fl and (tags_in(fl) or (side == 'N' and fl == 'M')):
                    removed.append(f"{side}-terminal {fl} ({', '.join(tags_in(fl)) or 'start methionine'})")
            row['tags_removed'] = '; '.join(removed)
            dn0 = dn if dn and (tags_in(dn) or dn == 'M') else ''
            dc0 = dc if dc and tags_in(dc) else ''
            dn = '' if dn0 else dn
            dc = '' if dc0 else dc
            mut = [f'{d}{p}{x}' for p, x, d in subs]  # deposit residue, CatLog position, CatLog residue
            explained = [m for m in mut if m in stated]
            other = [m for m in mut if m not in stated]
            carried = []  # stated mutations both sequences carry (the deposit is the mutant)
            for m in stated:
                wt, pos, mu = re.fullmatch(r'([A-Z])(\d+)([A-Z])', m).groups()
                p = int(pos)
                if m in explained:
                    continue
                if p <= len(cs_) and cs_[p - 1] == mu:
                    carried.append(m)
            missing = sorted(stated - set(explained) - set(carried))
            if stated:
                mut_check['records with stated mutations'] += 1
                if not missing:
                    mut_check['every stated mutation agrees with the deposit'] += 1
                    mut_check['deposit is the wild type at every stated position' if len(explained) == len(stated)
                              else 'deposit carries the stated mutations' if len(carried) == len(stated)
                              else 'deposit wild type at some, mutant at others'] += 1
                else:
                    mut_check['a stated mutation is not where CatLog puts it'] += 1
            end_diff = [f"{w} {k}-terminal {fl[:30]}{'...' if len(fl) > 30 else ''} ({len(fl)} aa)"
                        for w, k, fl in (('deposit longer at the', 'N', dn), ('deposit longer at the', 'C', dc),
                                         ('CatLog longer at the', 'N', cn), ('CatLog longer at the', 'C', cc)) if fl]
            text = ' '.join(str(x) for x in (L.get('construct'), L.get('sequence_basis'), prot.get('source_comments'),
                                              prot.get('protein_name'), prot.get('sequence_modifications_json')))
            if cov < 0.5 or ident < 0.3:
                row['outcome'] = 'different: another protein'
                # which Swiss-Prot entries carry each sequence exactly (the deposit without its tags)
                core = strip_tags(ds_)
                hit_c = sorted(a_ for a_, q in refs.seq.items() if q == cs_)[:3]
                hit_d = sorted(a_ for a_, q in refs.seq.items() if q == core)[:3]
                row['detail'] = (f'local alignment covers {cov:.0%} of the shorter sequence at {ident:.0%} identity; '
                                 f"Swiss-Prot entries with CatLog's sequence: {', '.join(hit_c) or 'none'}; with the deposit's: "
                                 f"{', '.join(hit_d) or 'none'} (deposited accession {prot.get('uniprotkb_xml') or '-'})")
            elif other or gaps:
                row['outcome'] = 'different: unexplained substitutions or gaps'
                row['detail'] = f"substitutions {', '.join(other[:8])}; gaps {gaps}"
            elif end_diff and not STATED_END.search(text):
                row['outcome'] = 'different: ends differ, no truncation stated'
                row['detail'] = '; '.join(end_diff)
            elif end_diff:
                row['outcome'] = 'longer or shorter only by a stated truncation or signal peptide'
                row['detail'] = '; '.join(end_diff)
            elif explained:
                row['outcome'] = 'identical apart from the stated mutations (the deposit is the wild type)'
                row['detail'] = ', '.join(explained)
            else:
                row['outcome'] = 'identical'
                row['detail'] = 'stated mutations carried by both' if carried else ''
            if missing:
                row['detail'] += f"; stated mutation(s) {', '.join(missing)} not found"
        c[row['outcome']] += 1
        pairs[row['outcome']].add((pmid, cs_, ds_))
        lines.append(row)
    papers = collections.defaultdict(set)
    for r in lines:
        papers[r['outcome']].add(r['pmid'])
    res = {'records': len(lines), 'by_outcome': dict(c), 'distinct_sequence_pairs': {k: len(v) for k, v in pairs.items()},
           'identical_after_removing_tags': sum(1 for r in lines if r['outcome'] == 'identical' and r['tags_removed']),
           'tags_removed': dict(collections.Counter(t.split(' (')[1].rstrip(')').replace(', ', ' + ') for r in lines
                                                    for t in r['tags_removed'].split('; ') if r['tags_removed'])),
           'records_with_both_sequences': sum(1 for r in lines if r['outcome'] not in ('deposit holds no sequence',
                                                                                     'CatLog has no sequence')),
           'papers': {k: len(v) for k, v in papers.items()}, 'papers_total': len({r['pmid'] for r in lines}),
           'stated_mutations': dict(mut_check),
           'not_chosen': sum(1 for L in s1['link'].values() if 'not chosen' in (L.get('deposited_sequence_note') or ''))}
    return res, lines



# ------------------------------------------------------------------------------------------------ README
FIELDS = (('uniprot_entry', 'UniProt entry'), ('ec_number', 'EC number'), ('organism', 'Organism (species)'))
SEQ_OUTCOMES = ('identical', 'identical apart from the stated mutations (the deposit is the wild type)',
                'longer or shorter only by a stated truncation or signal peptide',
                'different: ends differ, no truncation stated', 'different: unexplained substitutions or gaps',
                'different: another protein', 'CatLog has no sequence', 'deposit holds no sequence')


def n_(x):
    return f'{x:,}'


def pct(a, b):
    return f'{100 * a / b:.1f}%' if b else '-'


def unsortable(label):
    return bool(re.search(r'not sortable|not decidable', label))


def strict_agree(key, agree_by):
    """Agreements by the strict rule: the same accession, the same EC, the same taxon or binomial."""
    if key == 'organism':
        return agree_by.get(ORG_ROUTES[0], 0) + agree_by.get(ORG_ROUTES[1], 0)
    lead = ENTRY_ROUTES[0] if key == 'uniprot_entry' else 'same EC'
    return sum(x for k, x in agree_by.items() if k.startswith(lead))


def loosest(a, rule):
    return a.get(f'agree_with_all, loosest rule: {rule}', 0)


def across_strict(key, a):
    if key == 'organism':
        return loosest(a, ORG_ROUTES[0]) + loosest(a, ORG_ROUTES[1])
    return loosest(a, ENTRY_ROUTES[0] if key == 'uniprot_entry' else EC_ROUTES[0])


def report(res):
    """README.md and the sentences for the Results, every number from res."""
    c, v, cs = res['export_counts'], res['reproduction'], res['compare_summary']['values_by_category']
    sl = v['substrate_lookups']
    A = {key: res[key + '_any_database'] for key, _ in FIELDS}
    both = {key: A[key].get('agree_with_all', 0) + A[key].get('differ_from_one', 0) for key, _ in FIELDS}
    agree = {key: A[key].get('agree_with_all', 0) for key, _ in FIELDS}
    strict = {key: across_strict(key, A[key]) for key, _ in FIELDS}
    names_ = loosest(A['organism'], ORG_ROUTES[2])
    ue_none = A['uniprot_entry'].get('catlog_names_none_a_database_names_one', 0)
    st = res['strenda_sequences']
    sb = st['by_outcome']
    MUT = 'identical apart from the stated mutations (the deposit is the wild type)'
    L = []
    w = L.append
    w('# Fields CatLog links to a record: UniProt entry, EC number, organism and sequence')
    w('')
    w("Question 6: are the UniProt entry, the EC number, the organism and the sequence that CatLog's code links to a "
      "record right? The tests judge the numbers and labels CatLog reads from the paper; these fields are added by code "
      "afterwards, and for a modeller a right number on the wrong entry or sequence is a wrong record.")
    w('')
    w('Short answer, where a database lists the same value for the same paper, constant, substrate and variant '
      '(percentages of the records where both sides name the field; neither side taken as the truth):')
    w('')
    w(f"- UniProt entry: the database's entry for {n_(agree['uniprot_entry'])} of {n_(both['uniprot_entry'])} records "
      f"({pct(agree['uniprot_entry'], both['uniprot_entry'])}); the same accession for {n_(strict['uniprot_entry'])} "
      f"({pct(strict['uniprot_entry'], both['uniprot_entry'])}). For another {n_(ue_none)} a database names an entry and "
      "CatLog none.")
    w(f"- EC number, printed in the paper or taken from UniProt: the same, or equal at every level both give, for "
      f"{n_(agree['ec_number'])} of {n_(both['ec_number'])} ({pct(agree['ec_number'], both['ec_number'])}); the same EC "
      f"for {n_(strict['ec_number'])} ({pct(strict['ec_number'], both['ec_number'])}).")
    w(f"- Species, in papers with one organism: {n_(agree['organism'])} of {n_(both['organism'])} "
      f"({pct(agree['organism'], both['organism'])}); by the same taxon or binomial alone {n_(strict['organism'])} "
      f"({pct(strict['organism'], both['organism'])}).")
    w(f"- Sequence, against the one the authors deposited in STRENDA DB: of the {n_(st['records_with_both_sequences'])} "
      f"records with both, {n_(sb.get('identical', 0))} identical once tags are removed, {n_(sb.get(MUT, 0))} apart only at the "
      f"stated mutations (the deposit is the wild type), {n_(sb.get('different: another protein', 0))} "
      f"({n_(st['papers'].get('different: another protein', 0))} paper) another protein.")
    w('')
    w('## Inputs')
    w('')
    w('| Input | What it gives |')
    w('|---|---|')
    w(f"| `work/paper_freeze_20261116/catlog_wide.jsonl.gz` | the frozen export: {n_(c['records'])} records, {n_(c['values'])} "
      f"values; UniProt entry on {n_(c['uniprot'])} ({pct(c['uniprot'], c['records'])}), a sequence on {n_(c['sequence'])} "
      f"({pct(c['sequence'], c['records'])}), an EC on {n_(c['ec'])} |")
    w('| `work/paper_freeze_20261116/db_values.tsv.gz` | the database table frozen with it (BRENDA, SABIO-RK, OED, SKiD, '
      'STRENDA, UniProt) |')
    w("| `work/paper_freeze_20261116/database_compare.json.gz` | the export's comparison summary, to check the rerun |")
    w('| git tag `paper-catalog-freeze-20261116` (commit 45487e4) | `catalog.jsonl`, `papers.tsv`, `rejected.jsonl`, '
      '`sources/natural_forms.tsv`, `sources/database_corrections.tsv`, and `tools/` (`dbcompare.py`, `sequences.py`, '
      '`enrich.py` and what they import), copied by `git show` and `git archive` into a scratch folder and run from there; '
      'each file checked against the sha256 in `paper/evidence/catalog_freeze_20261116/FREEZE.md` |')
    w(f"| `work/paper_freeze_20261116/structures_for_linked_fields.json.gz` | the substrate lookups `compare()` reads, which "
      f"the tag does not freeze: the {n_(sl['keys'])} keys it asks for the tag's catalogue rows, copied from "
      f"`enrich/structures.json` (sha256 `{STRUCT_SHA['source']}`); the copy's sha256 `{STRUCT_SHA['copy_gz']}` (content "
      f"`{STRUCT_SHA['copy_json']}`), checked before use |")
    w(f"| `sources/ref/` | `uniprot_sprot.fasta.gz` (Swiss-Prot: organism, taxon, gene and sequence of each entry), "
      f"`sec_ac.txt` (secondary accessions), `delac_sp.txt` (deleted accessions), `uniprot_kinetics.json.gz` (UniProt "
      f"{res['uniprot_kinetics_release']}: each kinetics entry's taxon, ECs and the other names of its organism), "
      f"`rhea2ec.tsv` and `rhea2uniprot_sprot.tsv` (the ECs of Swiss-Prot entries' Rhea reactions), and the structure "
      f"tables `compare()` reads; each file's sha256 in `results.json` |")
    w('| `sources/strenda/STRENDA_Claude_handoff.zip` | `csv/Proteins.csv`: the protein each STRENDA DB experiment '
      'deposited (accession, taxon, sequence) |')
    w('')
    w('## Method')
    w('')
    w(f"1. The tag's `dbcompare.compare()`, run unchanged on the frozen export, the tag's catalogue and the copied substrate "
      f"lookups (no network, no paper text opened), gave all {n_(v['database_check_identical'])} records the "
      f"`database_check` and `database_note` the frozen export holds, and the same summary ({n_(cs['CONFIRMED'])} values "
      f"confirmed, {n_(cs['SAME_NUMBER_LABEL_DIFFERS'])} the same number under another label, {n_(cs['DIFFERS'])} "
      f"differing). For every value it kept the database rows `compare()` counts as confirming it (its pass 1): the same "
      f"number for the same paper and constant, under a fitting substrate and variant; the enzyme is not compared. Per "
      f"database they give the same records and values as the `sources` the frozen export names.")
    w(f"2. The base: the {n_(res['records_with_a_confirmed_value'])} records ({n_(res['papers_with_a_confirmed_value'])} "
      "papers) with a value a database confirms. Each field is set against what that database's confirming rows name; a "
      "record agrees with a database when one of its rows agrees. The rules:")
    w(f"   - UniProt entry: named by OED's and SKiD's rows, UniProt's (each kinetics row its entry) and STRENDA's (the "
      f"accession the authors deposited); BRENDA's and SABIO-RK's rows name none, so the "
      f"{n_(res['records_confirmed_only_by_brenda_or_sabio_rk'])} records only they confirm cannot test it. Agree: the same "
      "accession, an isoform of it, or a secondary or merged accession (`sec_ac.txt`).")
    xs = res['ec_sabio_rk_short']
    w(f"   - EC number: only where CatLog's EC was printed in the paper or came from UniProt (the export's `ec_source`); the "
      f"{n_(res['ec_excluded']['records: EC from the databases'])} records whose EC came from the databases are left out. "
      "Agree: the same EC (any one when a side lists several), or equal at every level both give ('1.1.1.-' and "
      f"'1.1.1.1'). SABIO-RK's ECs of fewer than four numbers ('1.1.1', '3.4.21': {n_(xs['rows_with_fewer_than_four_numbers'])} "
      f"of the {n_(xs['confirming_rows'])} SABIO-RK rows that confirm a value compared here) count as no EC. An EC "
      "CatLog took from UniProt, set against UniProt's own rows, is a circular comparison; it is counted, and what it "
      "weighs is given below.")
    oe = res['organism_excluded']
    w(f"   - Organism: at species level, in papers where CatLog gives one organism "
      f"({n_(oe.get('records: paper with several CatLog organisms', 0))} records of papers with several, and "
      f"{n_(oe.get('records: paper names no organism', 0))} of papers naming none, left out). Agree, strictest rule first: "
      "the same NCBI taxon (UniProt's and STRENDA's rows give one); the same binomial (genus and epithet); the same "
      "binomial through another name of either organism (its taxon's name or one UniProt lists; a common name or a "
      "binomial in parentheses, `compare()`'s `org_names`); `compare()`'s epithet rules (`org_fits`: the same epithet "
      "under another genus, as for a renamed genus; the same genus and an epithet that differs only in its ending, -us, "
      "-um, -is, -ae, -a, -e or -i, on a stem of 5 or more letters). A side "
      "naming only the genus the other names ('Pseudomonas sp.'), or no organism ('plasmid', 'uncultured'), counts as "
      "empty.")
    w("3. Differences sorted with what the local files tell (below); not sortable offline: an accession outside the local "
      "Swiss-Prot, two ECs both still in use, two species names with no local link, and another entry of the same "
      "organism unless only one of the two entries carries the EC the paper prints (each Swiss-Prot entry's ECs: its "
      "Rhea reactions and the names of UniProt's kinetics entries). For an entry difference, CatLog's sequence (its "
      "entry's, with the record's mutations) is set against the sequence of the database accession that sorts the pair, "
      "the one closest in organism; the second count tests every accession the database names, through each entry it "
      "stands for (an accession split into several entries too).")
    w("4. STRENDA DB: for the records whose export carries the deposited sequence (`deposited_sequence`), a local "
      f"alignment of CatLog's sequence with it (Biopython; match {ALIGN['match']}, mismatch {ALIGN['mismatch']}, gap open "
      f"{ALIGN['open']}, extend {ALIGN['extend']}). Deposit ends outside the alignment that carry a tag (His tag, "
      "thrombin, TEV or enterokinase site, S-tag and the like) are removed. Then: identical; identical apart from the "
      "stated mutations (CatLog's residue the mutant, the deposit's the wild type); longer or shorter only by a stated "
      "truncation or signal peptide; or different.")
    w('')
    w('## Numbers')
    w('')
    w('Records with a value the database lists for the same paper, constant, substrate and variant (a record counts once '
      'per database). Strict rule: the same accession, the same EC, the same taxon or binomial.')
    w('')
    w('| Field | Database | Records | Agree | Agree by the strict rule | Empty: CatLog / database / both | Differ (papers) '
      '| Of them sorted by the local files | Not sortable offline |')
    w('|---|---|---:|---:|---:|---:|---:|---:|---:|')
    for key, name in FIELDS:
        for src in SOURCES:
            t = res[key][src]
            if key == 'uniprot_entry' and src in ('BRENDA', 'SABIO-RK'):
                assert not t['records']
                w(f'| {name} | {src} | names no accession in the table | | | | | | |')
                continue
            if not t['records']:
                continue
            srt = sum(x for k, x in t['differ_sorted'].items() if not unsortable(k))
            uns = sum(x for k, x in t['differ_sorted'].items() if unsortable(k))
            assert srt + uns == t['differ']
            sa, b = strict_agree(key, t['agree_by']), t['agree'] + t['differ']
            w(f"| {name} | {src} | {n_(t['records'])} | {n_(t['agree'])} ({pct(t['agree'], b)}) | {n_(sa)} ({pct(sa, b)}) | "
              f"{n_(t['catlog_empty'])} / {n_(t['database_empty'])} / {n_(t['both_empty'])} | {n_(t['differ'])} "
              f"({n_(t['papers'].get('differ', 0))}) | {n_(srt)} | {n_(uns)} |")
    w('')
    gen = collections.Counter()
    for t in res['organism'].values():
        gen.update(t['empty_by'])
    ts = xs['SABIO-RK, read as n.n.n.-']
    w(f"The percentages are of the records where both sides name one. For the organism, empty includes a side that names "
      f"only the other's genus: CatLog {n_(gen.get('(CatLog names the genus only)', 0))}, the database "
      f"{n_(gen.get('(the database names the genus only)', 0))}, both the same genus "
      f"{n_(gen.get('(both name the same genus only)', 0))} (all databases). For "
      f"{n_(res['ec_number']['SABIO-RK']['database_empty'] - ts['database_empty'])} of SABIO-RK's "
      f"{n_(res['ec_number']['SABIO-RK']['database_empty'])} 'database empty' EC records its rows give only ECs of fewer "
      f"than four numbers; read as 'n.n.n.-', SABIO-RK would agree for {n_(ts['agree'])} of "
      f"{n_(ts['agree'] + ts['differ'])} ({pct(ts['agree'], ts['agree'] + ts['differ'])}).")
    w('')
    w('Across the databases: a record agrees with every database naming the field, or differs from at least one.')
    w('')
    w('| Field | Records where both name one | Agree with every database (papers) | By the strict rule | Differ from one '
      '(papers) | A database names one, CatLog none |')
    w('|---|---:|---:|---:|---:|---:|')
    for key, name in FIELDS:
        a = A[key]
        w(f"| {name} | {n_(both[key])} | {n_(agree[key])} ({pct(agree[key], both[key])}; "
          f"{n_(a['papers'].get('agree_with_all', 0))}) | {n_(strict[key])} ({pct(strict[key], both[key])}) | "
          f"{n_(a.get('differ_from_one', 0))} ({n_(a['papers'].get('differ_from_one', 0))}) | "
          f"{n_(a.get('catlog_names_none_a_database_names_one', 0))} |")
    w('')
    nd = A['uniprot_entry'].get('no_database_to_compare', 0)
    acc_base = both['uniprot_entry'] + nd
    w(f"- UniProt entry: of the {n_(res['records_with_a_confirmed_value'])} records, "
      f"{n_(res['records_confirmed_only_by_brenda_or_sabio_rk'])} are confirmed only by BRENDA or SABIO-RK, which name no "
      f"entry. Of the other {n_(acc_base)}, both sides name an entry for {n_(both['uniprot_entry'])}, only the database "
      f"for {n_(ue_none)}, and the database none for {n_(nd - ue_none)}.")
    var = res['ec_number_any_database_variants']
    vs = var["SABIO-RK's ECs of fewer than four numbers read as n.n.n.-"]
    vc = var["without UniProt's rows where CatLog took its EC from UniProt"]
    oc = res['ec_records_compared_only_circularly']
    w(f"- EC number: {n_(strict['ec_number'])} agree by the same EC and {n_(agree['ec_number'] - strict['ec_number'])} more "
      f"only at the levels both give. With SABIO-RK's short ECs read as 'n.n.n.-', {n_(vs['agree_with_all'])} of "
      f"{n_(vs['agree_with_all'] + vs['differ_from_one'])} agree "
      f"({pct(vs['agree_with_all'], vs['agree_with_all'] + vs['differ_from_one'])}). For "
      f"{n_(sum(oc.values()))} records ({n_(oc.get('agree', 0))} agreeing) the one comparison is an EC CatLog took from "
      f"UniProt against UniProt's own rows; without that circular comparison, {n_(vc['agree_with_all'])} of "
      f"{n_(vc['agree_with_all'] + vc['differ_from_one'])} agree "
      f"({pct(vc['agree_with_all'], vc['agree_with_all'] + vc['differ_from_one'])}).")
    er = res['organism_epithet_rules']
    assert er['pairs'] == sum(t['agree_by'].get(ORG_ROUTES[3], 0) for t in res['organism'].values())
    top = '; '.join(f"{a} / {b} {n_(n)}" for a, b, n in er['commonest_pairs'][:3])
    w(f"- Organism: by the same taxon or binomial {n_(strict['organism'])} ({pct(strict['organism'], both['organism'])}); "
      f"adding the other names of the organism {n_(strict['organism'] + names_)} "
      f"({pct(strict['organism'] + names_, both['organism'])}); adding `compare()`'s epithet rules {n_(agree['organism'])} "
      f"({pct(agree['organism'], both['organism'])}). {n_(er['pairs'])} record and database pairs agree only through the "
      f"epithet rules ({n_(er['by_rule'].get('the same epithet under another genus', 0))} the same epithet under another "
      f"genus, {n_(er['by_rule'].get('the same genus, the epithet with another ending', 0))} another ending); the three "
      f"commonest are renamed genera ({top} pairs; the 25 commonest in `results.json`).")
    w('')
    w("What the differences are (record and database pairs, all databases). A sorted difference is one the local files "
      "can name (another strain, another species, an EC no longer in use, another name for the organism); it is not "
      "thereby harmless: an entry of another species is a wrong link on one side, which side is not decided here.")
    w('')
    w('| Field | What the local files tell | Pairs |')
    w('|---|---|---:|')
    for key, name in FIELDS:
        tot = collections.Counter()
        for t in res[key].values():
            tot.update(t['differ_sorted'])
        for k, x in sorted(tot.items(), key=lambda kv: (unsortable(kv[0]), -kv[1])):
            w(f'| {name} | {k} | {n_(x)} |')
        if key == 'uniprot_entry':
            sq, sq_any = collections.Counter(), collections.Counter()
            for t in res[key].values():
                sq.update(t['differ_sequence'])
                sq_any.update(t['differ_sequence_any_accession'])
            assert sum(sq.values()) == sum(sq_any.values()) == sum(tot.values())
            for k, x in sorted(sq.items(), key=lambda kv: -kv[1]):
                w(f'| {name}, the sequence | {k} | {n_(x)} (every accession: {n_(sq_any.get(k, 0))}) |')
    w('')
    so = collections.Counter()
    for t in res['uniprot_entry'].values():
        so.update(t['same_organism_by_ec'])
    w(f"Another entry of the same organism, {n_(sum(so.values()))} pairs: only the database's entry carries the EC the "
      f"paper prints in {n_(so.get(ONLY_DB, 0))}, only CatLog's in {n_(so.get(ONLY_CAT, 0))}; the other "
      f"{n_(sum(so.values()) - so.get(ONLY_DB, 0) - so.get(ONLY_CAT, 0))} stay not decidable offline ("
      + ', '.join(f'{k} {n_(x)}' for k, x in sorted(so.items(), key=lambda kv: -kv[1]) if k not in (ONLY_DB, ONLY_CAT))
      + ').')
    w('')
    ek = res['ec_number_by_catlog_source']
    w("EC number by where CatLog's EC came from (records where both sides name one):")
    w('')
    w('| CatLog EC from | Database | Agree | Differ | Of them: CatLog\'s EC likely transferred |')
    w('|---|---|---:|---:|---:|')
    for kind, label in (('paper', 'the paper'), ('UniProt', 'UniProt')):
        for src in SOURCES:
            t = ek[kind][src]
            if t['agree'] + t['differ']:
                tr = sum(x for k, x in t['differ_sorted'].items() if 'likely transferred' in k)
                w(f"| {label} | {src} | {n_(t['agree'])} ({pct(t['agree'], t['agree'] + t['differ'])}) | {n_(t['differ'])} | {n_(tr)} |")
    w('')
    w(f"Sequences against the sequence the authors deposited in STRENDA DB ({n_(st['records'])} records from "
      f"{n_(st['papers_total'])} papers carry one; {n_(st['not_chosen'])} more were left without one by the export because "
      f"their paper deposited two different sequences):")
    w('')
    w('| Outcome | Records | Papers |')
    w('|---|---:|---:|')
    for k in SEQ_OUTCOMES:
        w(f"| {k} | {n_(sb.get(k, 0))} | {n_(st['papers'].get(k, 0))} |")
    w('')
    sm = st['stated_mutations']
    w(f"Tags removed before the comparison in {n_(st['identical_after_removing_tags'])} of the identical records "
      f"({', '.join(f'{k} {n_(x)}' for k, x in sorted(st['tags_removed'].items()))}). Stated mutations: in "
      f"{n_(sm.get('every stated mutation agrees with the deposit', 0))} of the {n_(sm.get('records with stated mutations', 0))} "
      f"mutant records with both sequences every stated mutation agrees with the deposit (the deposit is the wild type at "
      f"each stated position in {n_(sm.get('deposit is the wild type at every stated position', 0))}). The 'another protein' "
      "records: `strenda_sequences.tsv` names the Swiss-Prot entries that carry each sequence.")
    w('')
    # the sentences for the Results
    s1 = (f"Where a database lists the same value for the same paper, constant, substrate and variant, CatLog's UniProt "
          f"entry was the one the database names for {n_(agree['uniprot_entry'])} of the {n_(both['uniprot_entry'])} "
          f"records where both name an entry ({pct(agree['uniprot_entry'], both['uniprot_entry'])}; CatLog named none for "
          f"another {n_(ue_none)} that a database names), and its EC number, printed in the paper or taken from UniProt, "
          f"agreed, or matched at every level both give, for {n_(agree['ec_number'])} of the {n_(both['ec_number'])} where "
          f"both name one ({pct(agree['ec_number'], both['ec_number'])}).")
    s2 = (f"In papers with one organism, its species agreed for {n_(agree['organism'])} of the {n_(both['organism'])} "
          f"records where both name one ({pct(agree['organism'], both['organism'])}), counting other names of the organism, "
          f"and the same epithet under another genus or with another ending, as one species ({n_(strict['organism'])}, "
          f"{pct(strict['organism'], both['organism'])}, by taxon or exact binomial alone).")
    s3 = (f"Of the {n_(st['records_with_both_sequences'])} records whose authors deposited the protein's sequence in "
          f"STRENDA DB and that CatLog gives a sequence, {n_(sb.get('identical', 0))} were identical once tags were "
          f"removed, {n_(sb.get(MUT, 0))} differed only at the stated mutations (the authors deposited the wild type), and "
          f"{n_(sb.get('different: another protein', 0))} ({n_(st['papers'].get('different: another protein', 0))} "
          f"paper{'' if st['papers'].get('different: another protein', 0) == 1 else 's'}) carried another protein's "
          "sequence.")
    w('## For the Results')
    w('')
    w(f'> {s1}')
    w('>')
    w(f'> {s2}')
    w('>')
    w(f'> {s3}')
    w('')
    w('## Rerun')
    w('')
    w('From the top folder of the repository:')
    w('')
    w('```')
    w('python3 -I -B paper/evidence/linked_fields_20261117/linked_fields.py --scratch <a new folder outside the repository>')
    w('```')
    w('')
    r_ = res.get('run') or {}
    w(f"This run took {r_.get('minutes', '-')} minutes{' (its first stage reused)' if r_.get('stage1_reused') else ''} at "
      f"a peak of {r_.get('peak_memory_gb', '-')} GB of memory, and the scratch folder held {r_.get('scratch_mb', '-')} MB: "
      "the tag's code and files are copied there, `compare()` runs there, then the comparison. The script stops if a "
      "file's sha256 (the frozen files, the copied substrate lookups), the rerun of the comparison or a count the paper "
      "prints (the records, the values, UniProt entry and sequence shares, the comparison's categories) does not match. "
      "`--structures FILE` runs `compare()` on other substrate lookups (the rerun check still applies); "
      "`--write-structures-copy FILE` wrote the copy from `enrich/structures.json` with the sha256 above. `--reuse` reuses "
      "the scratch folder's first stage; `--papers N` tests on the first N papers and writes to the scratch folder only. "
      "Apart from that copy, it writes nothing in the repository but this folder.")
    w('')
    w('## Files')
    w('')
    w('- `linked_fields.py`: the analysis.')
    w('- `results.json`: every count, per field, database and outcome, with papers; the rules each agreement needed; the '
      'check of the rerun with the sha256 of the substrate lookups and of each reference file; the sentences.')
    w('- `differences.tsv.gz`: one line per record, database and field that differ: both sides, how it was sorted, how '
      'CatLog found its entry (`uniprot_how`).')
    w('- `strenda_sequences.tsv`: one line per record with a deposited sequence: lengths, tags removed, outcome.')
    w('')
    w('## Limits')
    w('')
    w("- A database row confirms a value by number, substrate and variant, not by enzyme: in a paper on several enzymes of "
      "one organism a row of another enzyme with the same number can confirm a value. Where CatLog links that other "
      "enzyme in the same paper, the difference is sorted so; the rest sit among the entries not sortable offline.")
    w("- CatLog keeps the organism name the paper prints; the databases often give the current name. Names the local files "
      "do not link stay not sortable, though many are synonyms.")
    w("- An EC counts as likely transferred when no BRENDA entry with values, Rhea reaction or UniProt kinetics entry "
      "carries it; the local files hold no list of EC transfers.")
    w("- A record agrees with a database when one of its confirming rows agrees; an OED row naming several accessions "
      "agrees when one of them is CatLog's (counted apart in `results.json`, `agree_by`).")
    w('')
    return '\n'.join(L), [s1, s2, s3]


# ------------------------------------------------------------------------------------------------ main
def main():
    global T0
    T0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--scratch', type=Path, default=None)
    ap.add_argument('--reuse', action='store_true')
    ap.add_argument('--stage1-only', action='store_true')
    ap.add_argument('--papers', type=int, default=0, help='test on the first N papers only')
    ap.add_argument('--structures', type=Path, default=STRUCT_COPY)
    ap.add_argument('--write-structures-copy', type=Path, default=None)
    a = ap.parse_args()
    block_network()
    if a.write_structures_copy:
        write_structures_copy(a.write_structures_copy)
        return
    scratch = (a.scratch or Path(tempfile.mkdtemp(prefix='linked_fields_'))).resolve()
    assert REPO.resolve() not in scratch.parents and scratch != REPO.resolve(), 'the scratch folder is outside the repository'
    scratch.mkdir(parents=True, exist_ok=True)
    reused = a.reuse and (scratch / 'stage1.pkl').exists()
    if reused:
        with open(scratch / 'stage1.pkl', 'rb') as f:
            s1 = pickle.load(f)
        log('stage 1 reused from', scratch / 'stage1.pkl')
    else:
        s1 = stage1(scratch, a.papers, a.structures)
    if a.stage1_only:
        return
    full = not a.papers and s1['verify']['records'] == PAPER['records']
    if full:  # the counts the paper prints for the frozen export, and the rerun reproducing the frozen comparison
        c = s1['counts']
        for k in ('records', 'values', 'uniprot', 'sequence', 'ec', 'smiles'):
            assert c[k] == PAPER[k], (k, c[k], PAPER[k])
        assert round(100 * c['uniprot'] / c['records'], 1) == PAPER['uniprot_pct']
        assert round(100 * c['sequence'] / c['records'], 1) == PAPER['sequence_pct']
        v = s1['verify']
        assert v['database_check_identical'] == v['database_note_identical'] == PAPER['records'], v
        assert all(ok for k, ok in v['summary_keys_identical'].items() if k != 'unreproduced'), v
        assert s1['summary']['values_by_category'] == PAPER['values_by_category']
    log('stage 2: linked fields against the confirming database rows')
    s2, diffs, refs, dbc = stage2(s1, scratch / 'root')
    if full:
        assert s2['confirmed_values'] == PAPER['values_by_category']['CONFIRMED']
    log('stage 3: STRENDA deposited sequences')
    s3, seq_lines = stage3(s1, refs, dbc)
    res = {'reproduction': s1['verify'], 'export_counts': s1['counts'], 'compare_summary': s1['summary'], **s2,
           'strenda_sequences': s3, 'uniprot_kinetics_release': refs.kin_release,
           # the reference files are not frozen with the tag either: their sha256, so a later rerun can tell what changed
           'reference_files_sha256': {str(p.relative_to(REPO)): sha256_file(p)
                                      for p in sorted(REF.iterdir()) + [STRENDA_ZIP] if p.is_file()}}
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
    size = sum(f.stat().st_size for f in scratch.rglob('*') if f.is_file() and not f.is_symlink()
               and 'ref' not in f.relative_to(scratch).parts[:3])
    res['run'] = {'minutes': round((time.time() - T0) / 60, 1), 'peak_memory_gb': round(peak / 1e9, 1),
                  'scratch_mb': round(size / 1e6), 'stage1_reused': reused}
    readme, sentences = report(res)
    res['results_sentences'] = sentences
    dest = HERE if full else scratch
    (dest / 'results.json').write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n')
    cols = ('field', 'database', 'pmid', 'measurement_id', 'catlog', 'database_value', 'sorted', 'note', 'uniprot_how')
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols, delimiter='\t', lineterminator='\n')
    w.writeheader()
    w.writerows(sorted(diffs, key=lambda d: (d['field'], SOURCES.index(d['database']), d['pmid'], d['measurement_id'])))
    with open(dest / 'differences.tsv.gz', 'wb') as f:
        f.write(gzip.compress(buf.getvalue().encode(), mtime=0))
    cols = ('pmid', 'measurement_id', 'strenda', 'uniprot_id', 'variant', 'catlog_length', 'deposit_length', 'tags_removed',
            'outcome', 'detail')
    with open(dest / 'strenda_sequences.tsv', 'w', newline='') as f:
        w = csv.DictWriter(f, cols, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(seq_lines)
    (dest / 'README.md').write_text(readme)
    if (dest / 'differences.tsv').exists():
        (dest / 'differences.tsv').unlink()  # an earlier, uncompressed version of this script's own output
    log('written to', dest, ':', ', '.join(sorted(x.name for x in dest.iterdir() if x.is_file())))
    for t in sentences:
        print(t)


if __name__ == '__main__':
    main()
