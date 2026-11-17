#!/usr/bin/env python3
"""Download the reference files that tools/sequences.py reads locally, into sources/ref/.

- pdb_chain_uniprot.tsv.gz  SIFTS: every PDB chain segment -> UniProt accession (weekly)
- pdb_pubmed.tsv.gz         SIFTS: PDB entry -> citation PMIDs (ordinal 0 = primary citation) (weekly)
- uniprot_sprot.fasta.gz    Swiss-Prot canonical sequences (every 8 weeks)
- uniprot_sprot_varsplic.fasta.gz  Swiss-Prot isoform sequences (ACC-n)
- sec_ac.txt                secondary -> primary accessions (merged / demerged entries)
- delac_sp.txt              accessions deleted from Swiss-Prot

Idempotent: a file already present is kept (pass --refresh to fetch everything again). Each download goes to a
.part file first and is renamed only when complete, so an interrupted run never leaves a truncated file.
Usage: python3 tools/ref_sequences.py [--refresh]
"""
import gzip, os, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'sources' / 'ref'
SIFTS = 'https://ftp.ebi.ac.uk/pub/databases/msd/sifts/flatfiles/tsv/'
UNIPROT = 'https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/'
FILES = {
    'pdb_chain_uniprot.tsv.gz': SIFTS + 'pdb_chain_uniprot.tsv.gz',
    'pdb_pubmed.tsv.gz': SIFTS + 'pdb_pubmed.tsv.gz',
    'uniprot_sprot.fasta.gz': UNIPROT + 'uniprot_sprot.fasta.gz',
    'uniprot_sprot_varsplic.fasta.gz': UNIPROT + 'uniprot_sprot_varsplic.fasta.gz',
    'sec_ac.txt': UNIPROT + 'docs/sec_ac.txt',
    'delac_sp.txt': UNIPROT + 'docs/delac_sp.txt',
}
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}


def size(path):
    n = path.stat().st_size
    return f'{n / 1e6:.1f} MB' if n >= 1e6 else f'{n / 1e3:.1f} KB'


def download(url, dest):
    part = dest.with_name(dest.name + '.part')
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(part, 'wb') as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    if dest.suffix == '.gz':  # a complete gzip stream, or the file is not kept
        with gzip.open(part) as g:
            while g.read(1 << 24):
                pass
    part.rename(dest)


def main():
    refresh = '--refresh' in sys.argv
    REF.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = REF / name
        if dest.exists() and dest.stat().st_size > 0 and not refresh:
            print(f'{name}: present, {size(dest)}')
            continue
        t = time.time()
        download(url, dest)
        print(f'{name}: downloaded {size(dest)} in {time.time() - t:.0f} s from {url}')
        time.sleep(1)


if __name__ == '__main__':
    main()
