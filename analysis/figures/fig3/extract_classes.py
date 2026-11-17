"""Fig. 3 v2, step 2: the enzyme class and the database status of every record, for the colours of panels a, b and e.

Step 1 is the figure's own extract, run into this folder (it leaves ../data/, which the manuscript cites, alone):
    python3 -I -B writing/figures/fig3/extract.py --out writing/figures/fig3/v2/data
It writes data/snapshot.json (every count of panels c, d and f, and of a and b) and data/kcat_km.csv.gz.

This script reads the same export once more (catlog_wide.jsonl, read only), stops unless it is byte for byte the export
of data/snapshot.json (size, time written and sha256), and writes into data/:
  kcat_km_class.csv.gz   kcat (s^-1), Km (mM), enzyme class and database status of every record that has both, in
                         the order of kcat_km.csv.gz, whose two columns it must repeat exactly
  classes.json           values by publication year and enzyme class (panel b), records by organism and class or
                         status (panel e), records by class, and where each record's EC number comes from
The rules are extract.py's, imported from it: a value is one printed kcat, Km or kcat/Km of a record (its `evidence`
keys); a paper's year is its PubMed year, else the year of its reference in sources/nopmid_refs.tsv; the class is the
first digit of the record's first EC number ('none' when it has no EC number).

Organisms (panel e) are counted by species (`binomial`): 'Mus musculus (mouse)', 'mouse (Mus musculus)' (a common
name with the binomial in brackets) and 'Escherichia coli K-12' count as Mus musculus and Escherichia coli, 'E. coli'
as Escherichia coli; a common name alone ('yeast'), a string naming two organisms, a variety, a subspecies, a virus or
an unnamed species ('sp.', 'bacterium') counts as written. classes.json lists every spelling counted under each of the
top species, and the exact spellings' own counts, which the build checks against snapshot.json#records.top_organisms.

Run with --organisms when the export on disk is a later one than data/snapshot.json's (the snapshot's is no longer on
disk): it reads that export once and rewrites only the organism fields of classes.json (panel e), and only after every
count those fields held recounts the same on it (each spelling, and each species by class and by status), so the
records counted did not change between the two exports; classes.json#organisms_counted_on names the export read.

Database status of a record (the colours of version 2 only): each printed value's status in the export's own
comparison (`database_check`: confirmed = same number, same_number_other_label = other name, corrected or differs =
different number, new = in no database, not_compared); the record takes 'different' if one of its values has it, else
'other', else 'same', else 'none' (no database lists any of its values); 'not_compared' only when no value was compared.

Run:  python3 -I -B writing/figures/fig3/v2/extract_classes.py [--organisms]
"""
import collections
import csv
import gzip
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent)]                  # extract.py (python -I leaves folders out)
import extract  # noqa: E402

DATA = HERE / 'data'
CLASSES = ['1', '2', '3', '4', '5', '6', '7', 'none']
STATUSES = ['same', 'other', 'different', 'none', 'not_compared']       # the order of panel f's strip
STATUS_OF = {'confirmed': 'same', 'same_number_other_label': 'other', 'corrected': 'different', 'differs': 'different',
             'new': 'none', 'not_compared': 'not_compared'}
RECORD_ORDER = ['different', 'other', 'same', 'none']                    # a record takes the first its values have


def ec_class(r):
    """extract.py's rule (by_enzyme_class), word for word."""
    first_ec = str(r.get('ec_number') or '').replace(',', ';').split(';')[0].strip()
    return first_ec[:1] if first_ec[:1] in '1234567' and first_ec[1:2] == '.' else 'none'


def ec_origin(r):
    """Where the record's EC number comes from, by the export's ec_source: the paper, UniProt or the databases."""
    if not extract.filled(r.get('ec_number')):
        return 'none'
    s = str(r.get('ec_source') or '').strip().lower()
    for key, word in (('paper', 'paper'), ('uniprot', 'uniprot'), ('database', 'databases')):
        if s.startswith(key):
            return word
    return 'other: ' + s[:40]


def db_status(r):
    """The record's database status, by the rule in the docstring."""
    check = r.get('database_check') or {}
    found = set()
    for m in (r.get('evidence') or {}):
        s = (check.get(m) or {}).get('status')
        if s not in STATUS_OF:
            raise SystemExit(f"{r['measurement_id']}: database_check of {m} has a status this script does not know: {s!r}")
        found.add(STATUS_OF[s])
    for s in RECORD_ORDER:
        if s in found:
            return s
    if found != {'not_compared'}:
        raise SystemExit(f"{r['measurement_id']}: no database status for its values: {sorted(found)}")
    return 'not_compared'


TWO = re.compile(r'/|\s(?:and|x|×|\+)\s')                              # two organisms: a chimera, a fusion, a mix
RANK = re.compile(r'\b(?:var|subsp|ssp|pv|bv|biovar|serovar|forma|sp|spp|strain|bacterium|archaeon)\b|virus|phage', re.IGNORECASE)
NAME = re.compile(r'([A-Z][a-z]+|[A-Z]\.)\s+([a-z]{2,}(?:-[a-z]+)?)((?:\s+\S+){0,2})')
STRAIN = re.compile(r'\S*\d\S*')                                       # a strain: a word with a digit (K-12, O157:H7)
COMMON = re.compile(r"[A-Za-z][a-z'’]*(?:[ -][a-z][a-z'’]*){0,2}")     # a common name: 'mouse', "baker's yeast"
BRACKET = re.compile(r'([^()]*?)\s*\(([^()]*)\)')                      # text, then one bracket at the end


def species_of_name(s, genera):
    """The binomial `s` writes ('Escherichia coli', 'E. coli', 'Escherichia coli K-12'), or None."""
    if TWO.search(s) or RANK.search(s):
        return None
    m = NAME.fullmatch(s)
    if not m:
        return None
    genus, species, rest = m.groups()
    if any(not STRAIN.fullmatch(w) for w in rest.split()):
        return None
    if genus.endswith('.'):
        full = genera.get((genus[0], species), set())
        if len(full) != 1:
            return None
        genus = next(iter(full))
    return f'{genus} {species}'


def binomial(o, genera):
    """The species an organism string names: a trailing bracket dropped ('(mouse)', "(baker's yeast)"), or the binomial
    in that bracket taken when a common name stands before it ('mouse (Mus musculus)'), an abbreviated genus spelt out
    when one genus of that initial has the species ('E. coli'), up to two strain words after the species dropped
    ('K-12', 'O157:H7'); else the string as written. `genera`: (initial, species) -> full genera."""
    found = species_of_name(re.sub(r'\s*\([^()]*\)\s*$', '', o.strip()), genera)
    m = BRACKET.fullmatch(o.strip())
    if not found and m and COMMON.fullmatch(m.group(1)) and not RANK.search(m.group(1)):
        found = species_of_name(m.group(2).strip(), genera)
    return found or o


def organism_fields(organism_class, organism_status):
    """Panel e's fields of classes.json: records by species, every spelling of a species counted once under it.
    organism_class and organism_status: organism as written -> class (status) -> records."""
    genera = collections.defaultdict(set)
    for o in organism_class:
        m = NAME.fullmatch(o.strip())
        if m and not m.group(1).endswith('.'):
            genera[(m.group(1)[0], m.group(2))].add(m.group(1))
    species_of = {o: binomial(o, genera) for o in organism_class}
    by_species_class = collections.defaultdict(collections.Counter)
    by_species_status = collections.defaultdict(collections.Counter)
    spellings = collections.defaultdict(dict)
    for o, sp in species_of.items():
        by_species_class[sp].update(organism_class[o])
        by_species_status[sp].update(organism_status[o])
        spellings[sp][o] = sum(organism_class[o].values())
    top = sorted(by_species_class, key=lambda o: -sum(by_species_class[o].values()))[:15]
    exact = sorted(organism_class, key=lambda o: -sum(organism_class[o].values()))[:15]
    return {
        'organisms_by_class': [[o, {c: by_species_class[o][c] for c in CLASSES}] for o in top],
        'organisms_by_status': [[o, {s: by_species_status[o][s] for s in STATUSES}] for o in top],
        'organism_spellings': {o: dict(sorted(spellings[o].items(), key=lambda kv: -kv[1])) for o in top},
        'organisms_as_written': [[o, sum(organism_class[o].values())] for o in exact],
    }


def organisms_only():
    """--organisms: the organism fields of classes.json recounted on the export on disk (see the docstring)."""
    held = json.loads((DATA / 'classes.json').read_text())
    before = extract.stamp(extract.EXPORT)
    sha = hashlib.sha256()
    organism_class = collections.defaultdict(collections.Counter)
    organism_status = collections.defaultdict(collections.Counter)
    records = 0
    with open(extract.EXPORT, 'rb') as fh:
        for raw in fh:
            sha.update(raw)
            if not raw.strip():
                continue
            r = json.loads(raw)
            records += 1
            if extract.filled(r.get('organism')):
                organism_class[r['organism']][ec_class(r)] += 1
                organism_status[r['organism']][db_status(r)] += 1
    if extract.stamp(extract.EXPORT) != before:
        raise SystemExit('the export changed while it was read: run again')
    # every count the organism fields held must recount the same on this export
    for o, n in held['organisms_as_written']:
        if sum(organism_class[o].values()) != n:
            raise SystemExit(f'{o!r}: {n} records in classes.json, {sum(organism_class[o].values())} in the export on disk')
    for (sp, by_class), (sp2, by_status) in zip(held['organisms_by_class'], held['organisms_by_status']):
        names = held['organism_spellings'][sp]
        for o, n in names.items():
            if sum(organism_class[o].values()) != n:
                raise SystemExit(f'{sp}: the spelling {o!r} has {n} records in classes.json, '
                                 f'{sum(organism_class[o].values())} in the export on disk')
        if sp2 != sp or {c: sum(organism_class[o][c] for o in names) for c in CLASSES} != by_class \
                or {s: sum(organism_status[o][s] for o in names) for s in STATUSES} != by_status:
            raise SystemExit(f'{sp}: its records by class or by status differ between classes.json and the export on disk')
    new = organism_fields(organism_class, organism_status)
    if new['organisms_as_written'] != held['organisms_as_written']:
        raise SystemExit('the commonest spellings as written differ between classes.json and the export on disk')
    out = {**held, **new, 'organisms_counted_on': {
        'file': 'catlog_wide.jsonl', **before, 'sha256': sha.hexdigest(), 'records': records,
        'held_counts_recounted_equal': True, 'extracted': time.strftime('%Y-%m-%d %H:%M:%S')}}
    (DATA / 'classes.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    was = {sp: sum(d.values()) for sp, d in held['organisms_by_class']}
    for sp, by_class in new['organisms_by_class']:
        n = sum(by_class.values())
        print(f'{sp}: {n:,} records' + ('' if was.get(sp) == n else f' (was {was.get(sp, "not among the 15")})'))
    print(f"organism fields of classes.json recounted on the export of {before['written']}")


def main():
    snap = json.loads((DATA / 'snapshot.json').read_text())['export']
    before = extract.stamp(extract.EXPORT)
    if (before['size'], before['written']) != (snap['size'], snap['written']):
        raise SystemExit(f"catlog_wide.jsonl is not the export of data/snapshot.json ({snap['written']}): run step 1 again")
    sha = hashlib.sha256()
    pairs = []
    values_by_paper_class = collections.Counter()      # (paper, class) -> values
    records_by_class = collections.Counter()
    records_by_status = collections.Counter()
    organism_class = collections.defaultdict(collections.Counter)    # organism as written -> class -> records
    organism_status = collections.defaultdict(collections.Counter)   # organism as written -> status -> records
    origins = collections.Counter()
    records = values = 0
    with open(extract.EXPORT, 'rb') as fh:
        for raw in fh:
            sha.update(raw)
            if not raw.strip():
                continue
            r = json.loads(raw)
            records += 1
            c, st = ec_class(r), db_status(r)
            records_by_class[c] += 1
            records_by_status[st] += 1
            n = len(r.get('evidence') or {})
            values += n
            values_by_paper_class[(str(r['pubmed_id']), c)] += n
            if extract.positive(r.get('kcat')) and extract.positive(r.get('km')):
                pairs.append((r['kcat'], r['km'], c, st))
            if extract.filled(r.get('organism')):
                organism_class[r['organism']][c] += 1
                organism_status[r['organism']][st] += 1
            origins[ec_origin(r)] += 1
    if extract.stamp(extract.EXPORT) != before:
        raise SystemExit('the export changed while it was read: run steps 1 and 2 again')
    if sha.hexdigest() != snap['sha256']:
        raise SystemExit('catlog_wide.jsonl has the stamp of data/snapshot.json but not its sha256: run step 1 again')
    if (records, values) != (snap['records'], snap['values']):
        raise SystemExit(f"records or values differ from data/snapshot.json: {records}, {values}")

    # panel a: the class and status beside each record of kcat_km.csv.gz, which must be the same records in the same order
    with gzip.open(DATA / 'kcat_km.csv.gz', 'rt') as fh:
        held = [(float(a), float(b)) for a, b in list(csv.reader(fh))[1:]]
    if held != [(k, m) for k, m, _, _ in pairs]:
        raise SystemExit('kcat_km.csv.gz and this read differ in their records')
    with gzip.open(DATA / 'kcat_km_class.csv.gz', 'wt', newline='') as fh:
        fh.write('kcat_per_s,km_mM,ec_class,db_status\n')
        for k, m, c, st in pairs:
            fh.write(f'{k!r},{m!r},{c},{st}\n')

    # panel b: values by publication year and class, years as extract.py dates them
    year, standin = extract.pubmed_years(), extract.standin_years()
    by_year = collections.defaultdict(collections.Counter)
    undated = set()
    for (p, c), n in values_by_paper_class.items():
        y = year.get(p) if p.isdigit() else standin.get(p)
        if y is None:
            undated.add(p)
            continue
        by_year[y][c] += n
    if undated:
        raise SystemExit(f'papers without a publication year: {sorted(undated)[:20]}')

    # panel e: records by species, every spelling of a species counted once under it
    out = {
        'export': {k: snap[k] for k in ('file', 'size', 'written', 'sha256', 'records', 'values')},
        'classes': CLASSES,
        'records_by_class': {c: records_by_class[c] for c in CLASSES},
        'kcat_km_records_by_class': {c: sum(1 for _, _, x, _ in pairs if x == c) for c in CLASSES},
        'values_by_year_and_class': {str(y): {c: by_year[y][c] for c in CLASSES} for y in sorted(by_year)},
        **organism_fields(organism_class, organism_status),
        'statuses': STATUSES,
        'record_status_rule': "a record's values by database_check status (confirmed = same, same_number_other_label = "
                              "other, corrected or differs = different, new = none); the record takes different if one "
                              "of its values has it, else other, else same, else none; not_compared only when no value was",
        'records_by_status': {s: records_by_status[s] for s in STATUSES},
        'kcat_km_records_by_status': {s: sum(1 for *_, x in pairs if x == s) for s in STATUSES},
        'ec_number_from': dict(origins),
        'extracted': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    (DATA / 'classes.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    print(f"export of {snap['written']}: {records:,} records, {values:,} values; {len(pairs):,} records with kcat and Km; "
          f"wrote kcat_km_class.csv.gz and classes.json into {DATA}")


if __name__ == '__main__':
    organisms_only() if '--organisms' in sys.argv[1:] else main()
