"""Fig. 3, step 1: read one export of the catalogue as it stands and keep what the figure draws.

Reads catlog_wide.jsonl (one record per line) once, never writes it, and writes into data/ beside this file:
  kcat_km.csv.gz   kcat (s^-1) and Km (mM) of every record that has both (panel a), as the export gives them
  snapshot.json    which export this was (date, size, sha256), every count the figure draws (panels a, b, c)
                   and the checks made against the repository's other files at the same moment
The build (build_fig3.py) draws from data/ only, so the figure does not move while the catalogue grows.

data/ holds ONE export, and the manuscript cites it (writing/manuscript/results.md gives data/snapshot.json as the
source of its Fig. 3 counts). Once the catalogue is exported again, no other file holds those counts. So this script
stops when data/snapshot.json is of another export than the one on disk, and replaces it only when told to:
  at the freeze:  python3 -I -B writing/figures/fig3/extract.py --replace     then build, and refresh the text
For design drafts that need what data/ does not hold, the export on disk can be read into another folder, which
leaves data/ alone:  python3 -I -B writing/figures/fig3/extract.py --out writing/figures/fig3/options/data

What is counted
- value: one printed kcat, Km or kcat/Km of a record (the export's `evidence` keys); a kcat/Km that the export
  derives from kcat and Km is not a value. record: one line of the export. paper: its `pubmed_id`.
- panel a: records whose kcat and Km are both numbers above zero (Km in mM; a Km printed over a mass concentration
  is in another column and is not drawn).
- panel b: every value, dated by its paper's PubMed publication year (sources/ref/pubmed_years.jsonl, the cache of
  tools/publication_years.py, and data/pubmed_years_extra.jsonl for papers it lacks); a paper without a PubMed ID is
  dated by the year of its reference in sources/nopmid_refs.tsv. A paper with neither is listed in the snapshot
  (b.papers_without_year) and stops the build until its date is added.
- panel c: every value by its category in work/database_compare.json (`values_by_category`, written with the
  export by tools/dbcompare.py; the base the Results use): CONFIRMED, SAME_NUMBER_LABEL_DIFFERS, DIFFERS, NEW_b (the
  paper has database values, none for this value), NEW_a (no database lists a kcat, Km or kcat/Km for the paper),
  NO_VALUE (printed over a mass concentration, not compared). The export itself carries each value's
  `database_check` status, which this script recounts as a check that the file is of this export: the two agree
  except for a few values with a recorded different number that the category table puts under NEW_b.
- records (for panels on what a record carries, since 14 November): per record whether it has an EC number, a
  UniProt entry, a sequence, a substrate structure (SMILES), a pH, a temperature and an organism; whether it is
  the wild type; its enzyme class (the first digit of its first EC number); its organism; its pH and temperature;
  whether every value has its quoted line and its place in the paper, whether a printed ± is stored, and whether the
  record also holds a constant printed only as not detected or as a limit.
- bounds: every line of catlog_bounds.jsonl (a constant a paper reports only as not detected, or only as a limit),
  by constant and kind.
"""
import collections
import csv
import gzip
import hashlib
import json
import math
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = HERE / 'data'
EXPORT = ROOT / 'catlog_wide.jsonl'
BOUNDS = ROOT / 'catlog_bounds.jsonl'
YEAR_CACHES = [ROOT / 'sources' / 'ref' / 'pubmed_years.jsonl', DATA / 'pubmed_years_extra.jsonl']
NOPMID = ROOT / 'sources' / 'nopmid_refs.tsv'
COMPARE = ROOT / 'work' / 'database_compare.json'
METRICS = ('kcat', 'Km', 'kcat/Km')


def stamp(path):
    st = path.stat()
    return {'size': st.st_size, 'written': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))}


def pubmed_years():
    """{PMID: year} from the caches (NCBI esummary answers: sortpubdate, else pubdate; a later line wins)."""
    year = {}
    for path in YEAR_CACHES:
        if not path.exists():
            continue
        with open(path) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                y = str(r.get('sortpubdate') or r.get('pubdate') or '')[:4]
                if r.get('uid') and y.isdigit():
                    year[str(r['uid'])] = int(y)
    return year


def standin_years():
    """{stand-in paper id: BRENDA's reference year}; a stand-in whose references give two years gets none."""
    years = collections.defaultdict(set)
    with open(NOPMID, newline='') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            y = str(r.get('year') or '').strip()
            if r.get('paper_id') and y.isdigit() and len(y) == 4:
                years[r['paper_id'].strip()].add(int(y))
    return {p: next(iter(ys)) for p, ys in years.items() if len(ys) == 1}


def positive(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def filled(x):
    return x is not None and x != '' and x != []


def main():
    args = sys.argv[1:]
    out = Path(args[args.index('--out') + 1]).resolve() if '--out' in args else DATA
    out.mkdir(parents=True, exist_ok=True)
    if out != DATA:
        YEAR_CACHES.append(out / 'pubmed_years_extra.jsonl')
    before = stamp(EXPORT)
    held = DATA / 'snapshot.json'
    if out == DATA and held.exists() and '--replace' not in args:
        was = json.loads(held.read_text())['export']
        if (was['size'], was['written']) != (before['size'], before['written']):
            raise SystemExit(
                f"data/snapshot.json holds the export of {was['written']} ({was['records']:,} records, {was['values']:,} "
                f"values), and catlog_wide.jsonl is now another export ({before['written']}). The manuscript cites the "
                'stored one, and no other file still holds its counts. Nothing was read or written. To replace it on '
                'purpose (at the freeze, with the text refreshed too): run again with --replace; the old one stays in git.')
    sha = hashlib.sha256()
    records = 0
    papers = set()
    values_by_metric = collections.Counter()
    values_by_paper = collections.Counter()
    sizes = collections.Counter()
    pairs, pair_papers = [], set()
    status = collections.Counter()           # printed values: (status, paper in no database)
    status_all = collections.Counter()       # every database_check, a derived kcat/Km included: (status, metric)
    units = collections.Counter()
    carries = collections.Counter()          # records that have each thing
    by_class = collections.Counter()         # (enzyme class, wild type or variant) -> records
    organisms = collections.Counter()        # organism -> records
    organism_papers = collections.defaultdict(set)
    conditions = collections.Counter()       # (pH to the half unit, temperature to 5 degrees) -> records
    with open(EXPORT, 'rb') as fh:
        for raw in fh:
            sha.update(raw)
            if not raw.strip():
                continue
            r = json.loads(raw)
            records += 1
            pmid = str(r['pubmed_id'])
            papers.add(pmid)
            printed = [m for m in (r.get('evidence') or {})]
            if any(m not in METRICS for m in printed):
                raise SystemExit(f"{r['measurement_id']}: an evidence key that is not kcat, Km or kcat/Km: {printed}")
            sizes[len(printed)] += 1
            values_by_paper[pmid] += len(printed)
            check = r.get('database_check') or {}
            for m in printed:
                values_by_metric[m] += 1
                d = check.get(m) or {}
                status[(d.get('status') or 'none', bool(d.get('paper_not_in_databases')))] += 1
            for m, d in check.items():
                status_all[(d.get('status'), m)] += 1
            if positive(r.get('kcat')) and positive(r.get('km')):
                units[(r.get('kcat_unit'), r.get('km_unit'))] += 1
                pairs.append((r['kcat'], r['km']))
                pair_papers.add(pmid)
            # what the record carries
            if not isinstance(r.get('wild_type'), bool):
                raise SystemExit(f"{r['measurement_id']}: wild_type is not true or false: {r.get('wild_type')!r}")
            kind = 'wild_type' if r['wild_type'] else 'variant'
            carries[kind] += 1
            for name, field in (('ec_number', 'ec_number'), ('uniprot_entry', 'uniprot_id'), ('sequence', 'sequence'),
                                ('substrate_structure', 'smiles'), ('ph', 'ph'), ('temperature', 'temperature_c'),
                                ('organism', 'organism')):
                carries[name] += filled(r.get(field))
            carries['sequence_and_substrate_structure'] += filled(r.get('sequence')) and filled(r.get('smiles'))
            ev = r.get('evidence') or {}     # the printed line: every value's quoted line and its place in the paper
            carries['printed_line'] += bool(printed) and all(filled((ev[m] or {}).get('quote')) and filled((ev[m] or {}).get('location'))
                                                             for m in printed)
            carries['printed_uncertainty'] += any(r.get(f) is not None for f in ('kcat_err', 'km_err', 'kcat_over_km_err'))
            carries['bound'] += any(filled(r.get(f)) for f in ('kcat_bound', 'km_bound', 'kcat_over_km_bound'))
            first_ec = str(r.get('ec_number') or '').replace(',', ';').split(';')[0].strip()
            by_class[(first_ec[:1] if first_ec[:1] in '1234567' and first_ec[1:2] == '.' else 'none', kind)] += 1
            if filled(r.get('organism')):
                organisms[r['organism']] += 1
                organism_papers[r['organism']].add(pmid)
            if isinstance(r.get('ph'), (int, float)) and isinstance(r.get('temperature_c'), (int, float)):
                conditions[(round(r['ph'] * 2) / 2, 5 * round(r['temperature_c'] / 5))] += 1
    after = stamp(EXPORT)
    if before != after:
        raise SystemExit('the export changed while it was read: run again')
    if set(units) != {('s^(-1)', 'mM')}:
        raise SystemExit(f'panel a: kcat or Km in a unit other than s^-1 and mM: {dict(units)}')
    values = sum(values_by_metric.values())

    # panel b: values and papers per publication year
    year = pubmed_years()
    standin = standin_years()
    per_year, papers_per_year = collections.Counter(), collections.defaultdict(set)
    undated_values, undated_papers = 0, []
    for p, n in values_by_paper.items():
        y = year.get(p) if p.isdigit() else standin.get(p)
        if y is None:
            undated_values += n
            undated_papers.append(p)
            continue
        per_year[y] += n
        papers_per_year[y].add(p)

    # panel c: the categories of work/database_compare.json (drawn), and the export's own statuses (the check)
    by_status = collections.Counter()
    for (s, nodb), n in status.items():
        by_status[s] += n
    known = {'confirmed', 'same_number_other_label', 'corrected', 'differs', 'new', 'not_compared'}
    if set(by_status) - known:
        raise SystemExit(f'panel c: a database_check status this script does not know: {set(by_status) - known}')
    recount = {'same_number': by_status['confirmed'],
               'same_number_other_label': by_status['same_number_other_label'],
               'different_number': by_status['corrected'] + by_status['differs'],
               'different_number_parts': {'corrected': by_status['corrected'], 'differs': by_status['differs']},
               'none_paper_in_no_database': status[('new', True)],
               'none_paper_listed_without_this_value': status[('new', False)],
               'not_compared': by_status['not_compared']}
    if sum(v for k, v in recount.items() if isinstance(v, int)) != values:
        raise SystemExit('panel c: the statuses do not add up to the values')
    if not COMPARE.exists():
        raise SystemExit('work/database_compare.json is missing: it is written with the export (catlog.py export)')
    comp = json.loads(COMPARE.read_text())
    cat = comp['values_by_category']
    if set(cat) != {'CONFIRMED', 'SAME_NUMBER_LABEL_DIFFERS', 'DIFFERS', 'NEW_a', 'NEW_b', 'NO_VALUE'}:
        raise SystemExit(f'work/database_compare.json: categories this script does not know: {sorted(cat)}')
    c = {'base': 'work/database_compare.json#values_by_category',
         'same_number': cat['CONFIRMED'],
         'same_number_other_label': cat['SAME_NUMBER_LABEL_DIFFERS'],
         'different_number': cat['DIFFERS'],
         'none_paper_listed_without_this_value': cat['NEW_b'],
         'none_paper_in_no_database': cat['NEW_a'],
         'not_compared': cat['NO_VALUE'],
         'none': cat['NEW_a'] + cat['NEW_b']}
    theirs = {(s, m): n for s, d in comp['values_by_status_metric'].items() for m, n in d.items()}
    checks = {
        'file': 'work/database_compare.json', **stamp(COMPARE),
        'every_status_by_metric_equal': dict(status_all) == theirs,
        'values_equal_sum_of_categories': values == sum(cat.values()),
        'CONFIRMED_equals_status_confirmed': cat['CONFIRMED'] == recount['same_number'],
        'SAME_NUMBER_LABEL_DIFFERS_equals_status': cat['SAME_NUMBER_LABEL_DIFFERS'] == recount['same_number_other_label'],
        'NEW_a_equals_status_new_in_no_database': cat['NEW_a'] == recount['none_paper_in_no_database'],
        'NO_VALUE_equals_status_not_compared': cat['NO_VALUE'] == recount['not_compared'],
        # the category table puts a few values with a recorded different number under NEW_b; the statuses do not
        'NEW_b_minus_status_new_listed': cat['NEW_b'] - recount['none_paper_listed_without_this_value'],
        'status_different_minus_DIFFERS': recount['different_number'] - cat['DIFFERS'],
        'recount_from_the_export_statuses': recount,
    }
    for k in ('every_status_by_metric_equal', 'values_equal_sum_of_categories', 'CONFIRMED_equals_status_confirmed',
              'SAME_NUMBER_LABEL_DIFFERS_equals_status', 'NEW_a_equals_status_new_in_no_database',
              'NO_VALUE_equals_status_not_compared'):
        if checks[k] is not True:
            raise SystemExit(f'work/database_compare.json is not of this export: {k} fails')
    if checks['NEW_b_minus_status_new_listed'] != checks['status_different_minus_DIFFERS'] \
            or not 0 <= checks['NEW_b_minus_status_new_listed'] <= 100:
        raise SystemExit('work/database_compare.json: NEW_b and DIFFERS do not differ from the statuses by one small count')

    # bounds: constants a paper reports only as not detected or only as a limit (catlog_bounds.jsonl, of this export)
    bounds, bound_papers = collections.Counter(), set()
    with open(BOUNDS) as fh:
        for line in fh:
            if line.strip():
                b = json.loads(line)
                if b['metric'] not in METRICS or b['censored'] not in ('<', '>', 'not_detected'):
                    raise SystemExit(f"catlog_bounds.jsonl: an unknown constant or kind: {b['metric']!r} {b['censored']!r}")
                bounds[(b['metric'], 'not_detected' if b['censored'] == 'not_detected' else 'limit')] += 1
                bound_papers.add(str(b['pubmed_id']))
    if sum(n for (c_, _k), n in by_class.items()) != records or carries['wild_type'] + carries['variant'] != records:
        raise SystemExit('records: the enzyme classes or the wild-type split do not add up to the records')

    with gzip.open(out / 'kcat_km.csv.gz', 'wt', newline='') as fh:
        fh.write('kcat_per_s,km_mM\n')
        for k, m in pairs:
            fh.write(f'{k!r},{m!r}\n')
    snap = {
        'export': {'file': 'catlog_wide.jsonl', **before, 'sha256': sha.hexdigest(), 'records': records,
                   'values': values, 'papers': len(papers), 'values_by_metric': dict(values_by_metric),
                   'records_by_number_of_values': {str(k): v for k, v in sorted(sizes.items())}},
        'a': {'records_with_kcat_and_km': len(pairs), 'papers': len(pair_papers), 'file': 'data/kcat_km.csv.gz'},
        'b': {'values_by_year': {str(y): per_year[y] for y in sorted(per_year)},
              'papers_by_year': {str(y): len(papers_per_year[y]) for y in sorted(papers_per_year)},
              'values_without_year': undated_values, 'papers_without_year': sorted(undated_papers),
              'papers_dated_by_pubmed': sum(1 for p in papers if p.isdigit() and p in year),
              'papers_dated_by_brenda_reference_year': sum(1 for p in papers if not p.isdigit() and p in standin),
              'year_caches': [str(p.relative_to(ROOT)) for p in YEAR_CACHES if p.exists()]},
        'c': c,
        'checks_against_database_compare': checks,
        'records': {'carries': dict(carries),
                    'by_enzyme_class': {f'{c_}|{k}': n for (c_, k), n in sorted(by_class.items())},
                    'organisms': len(organisms),
                    'top_organisms': [[o, n, len(organism_papers[o])] for o, n in organisms.most_common(15)],
                    'ph_and_temperature': {f'{ph}|{t}': n for (ph, t), n in sorted(conditions.items())}},
        'bounds': {'file': 'catlog_bounds.jsonl', **stamp(BOUNDS), 'papers': len(bound_papers),
                   'by_constant_and_kind': {f'{m}|{k}': n for (m, k), n in sorted(bounds.items())}},
        'extracted': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    (out / 'snapshot.json').write_text(json.dumps(snap, indent=1) + '\n')
    print(f"export of {before['written']}: {records:,} records, {values:,} values, {len(papers):,} papers; "
          f"{len(pairs):,} records with kcat and Km; wrote kcat_km.csv.gz and snapshot.json into {out}")


if __name__ == '__main__':
    main()
