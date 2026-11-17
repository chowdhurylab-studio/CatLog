#!/usr/bin/env python3
"""Export all of SABIO-RK once (new Export API, https://sabiork.h-its.org/ui/export-api) and keep its
kcat / Km / kcat/Km values with a PMID.

Writes sources/sabio_rk_entries.jsonl.gz (every raw entry) and sources/sabio_values.tsv
(pmid, ec, metric, value, substrate, organism, comment) in catalog units: kcat s^-1, Km mM, kcat/Km mM^-1 s^-1,
converted from SABIO's normalized SI values (n_start_value). Rate limit: 60 requests/min; we use ~1/s.
Usage: python3 tools/sabio_values.py
"""
import sys, gzip, json, time, urllib.request, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = 'https://sabiork.h-its.org/export-api/sabio/kinlaw-entry/json?q=*:*&pageSize=1000&page={}'
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}
# SABIO normalized unit -> factor to catalog unit
CONVERT = {'kcat': {'s^(-1)': 1.0}, 'Km': {'M': 1e3}, 'kcat/Km': {'M^(-1)*s^(-1)': 1e-3}}


def page(n):
    for attempt in range(6):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(API.format(n), headers=UA), timeout=180).read())
        except urllib.error.HTTPError as e:
            time.sleep(65 if e.code == 429 else 10 * (attempt + 1))
        except Exception:
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f'page {n} failed')


def doi_ids():
    """DOI -> paper id for the papers BRENDA cites without a PMID (sources/nopmid_refs.tsv, tools/nopmid.py)."""
    import csv
    p = ROOT / 'sources' / 'nopmid_refs.tsv'
    if not p.exists():
        return {}
    with open(p) as f:
        return {r['doi'].lower(): r['paper_id'] for r in csv.DictReader(f, delimiter='\t') if r.get('doi') and r.get('paper_id')}


DOI_IDS = doi_ids()


def rows(e):
    pub = e.get('publication') or {}
    pmid = str(pub.get('pubmed_id') or '').strip()
    if not pmid.isdigit():  # no PMID: the id tools/nopmid.py gave its DOI, if any
        pmid = DOI_IDS.get(str(pub.get('data_identifier') or '').strip().lower(), '') if 'doi' in str(pub.get('base_url')) else ''
    if not pmid:
        return
    enz = e.get('enzyme_description') or {}
    cond = e.get('experimental_conditions') or {}
    ph = (cond.get('envvar_ph') or {}).get('start_value')
    t = (cond.get('envvar_temperature') or {}).get('start_value')
    org = ((e.get('general') or {}).get('organism') or {}).get('name') or ''
    variant = enz.get('mutant_spec') or enz.get('wildtype') or ''
    for p in (e.get('kineticlaw') or {}).get('parameter') or []:
        metric = {'kcat': 'kcat', 'Km': 'Km', 'kcat/Km': 'kcat/Km'}.get((p.get('parameter_type') or {}).get('name'))
        unit = (p.get('unit') or {}).get('n_name')
        v = p.get('n_start_value')
        if not metric or v is None or unit not in CONVERT[metric] or p.get('n_end_value') is not None:
            continue  # other parameter types, ranges, or units we cannot place
        sub = ((p.get('species') or {}).get('species_key') or '').split('|')
        sub = sub[1].strip() if len(sub) > 1 else ''
        comment = f"SABIO {e.get('id')}; {variant}; pH {ph}; {t} C".replace('\t', ' ')
        yield f"{pmid}\t{enz.get('ec_number') or ''}\t{metric}\t{v * CONVERT[metric][unit]:.6g}\t{sub}\t{org}\t{comment}\n"


def offline():
    """Rebuild sources/sabio_values.tsv from the raw entries already on disk (no API calls), e.g. after the no-PMID
    registry (sources/nopmid_refs.tsv) gained DOIs: `python3 tools/sabio_values.py offline`."""
    n_entries = n_values = 0
    with gzip.open(ROOT / 'sources' / 'sabio_rk_entries.jsonl.gz', 'rt') as raw, open(ROOT / 'sources' / 'sabio_values.tsv', 'w') as out:
        out.write('pmid\tec\tmetric\tvalue\tsubstrate\torganism\tcomment\n')
        for line in raw:
            n_entries += 1
            for row in rows(json.loads(line)):
                out.write(row); n_values += 1
    print(f'done (offline): {n_entries} SABIO-RK entries, {n_values} kcat/Km/kcat-Km values with a paper id')


def main():
    if sys.argv[1:] == ['offline']:
        return offline()
    first = page(1)
    pages = first['meta']['total_pages']
    n_entries = n_values = 0
    with gzip.open(ROOT / 'sources' / 'sabio_rk_entries.jsonl.gz', 'wt') as raw, open(ROOT / 'sources' / 'sabio_values.tsv', 'w') as out:
        out.write('pmid\tec\tmetric\tvalue\tsubstrate\torganism\tcomment\n')
        for n in range(1, pages + 1):
            data = first if n == 1 else page(n)
            for e in data['data']:
                raw.write(json.dumps(e) + '\n'); n_entries += 1
                for line in rows(e):
                    out.write(line); n_values += 1
            print(f'page {n}/{pages}: {n_entries} entries, {n_values} values', flush=True)
            time.sleep(1.1)
    print(f'done: {n_entries} SABIO-RK entries, {n_values} kcat/Km/kcat-Km values with a PMID')


if __name__ == '__main__':
    main()
