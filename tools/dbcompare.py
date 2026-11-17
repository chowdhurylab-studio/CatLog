"""Each CatLog value against the enzyme databases for the same paper (BRENDA, SABIO-RK, OED, SKiD, STRENDA, UniProt),
for `catlog.py export`: one `database_check` per value (keyed by metric, like `db_check`) and a `database_note` per
paper for errors that cover a whole paper. The website publishes them as fixed phrases (WEBSITE.md, site_release.v2_row);
`db_check` (number only) stays as it is and is never published.

The matcher of the contribution report (tools/site_patches/20261012-contribution-report.md, section 2.2), ported from
its r14/dbrel/analyze.py and contrib_numbers.py. A database row d (same PMID and metric, value in catalog units) and a
CatLog value x:
  close        |a-b| <= 2% of the larger, or one number, written with at most 2 significant figures, is the other
               rounded half up to 2 (0.14 and 0.1433; never 14.1 and 14.5, 1.15 and 1.1, or 135 and 144, which
               Python's half-to-even '.2g' had made equal); a database number printed with 1 significant figure (not
               an integer ending in 0) also matches x rounded half up to 1 figure. `figures` says which: 0 (within
               2%), 2 or 1, so a line names a number that is not within 2%.
  substrate    'none_given' (d names none), 'name' (normalized names; human_review._name/_bare and a few synonyms; x's
               names = printed, full name, names its structure lookup used), 'structure' (InChIKey connectivity of d's
               name by Rhea(EC)/ChEBI/SABIO-RK tables = x's SMILES), 'name_nostereo', 'cosubstrate_kcat' (kcat filed
               under x's co-substrate), 'alias' (an unresolved database name whose same-paper numbers point to one
               CatLog substrate, >= 2 rows); else 'other' / 'unresolved'. The best tier present wins.
  variant      d's from its comment: BRENDA 'mutant ... X123Y' / unstated = no mutation (matched as wild type); SKiD's
               mutant field; SABIO-RK, OED and UniProt's variant field (tools/uniprot_values.py writes one only when
               UniProt's text names a mutant, isoform or allele): 'Wildtype' or a tag = wild type, point mutations or a
               mutant word = mutant, any other name ('psi epg0', 'Ala105', 'C315/318S', 'isoform DD3') = a named form,
               which fits a CatLog value without point mutations whose variant or enzyme text holds that name, or a
               point mutant whose own variant text writes it ('TEM-109 (M69L/E104K/R164H)' for SABIO-RK's 'TEM-109'); a
               deletion or truncation only ('delta39 C-terminal His6-tag', BRENDA 'mutant lacking 162 C-terminal
               residues') fits a CatLog value without point mutations, in pairing first those whose construct states
               its residue numbers (span_fit), and a line names it in the database's words, never 'a mutant'.
               The same point mutations; an unspecified mutant fits any non-wild type; wild type fits wild type or a
               named form without point mutations. `wt_stated`: the row itself says wild type.
  organism     compared only when the paper has more than one CatLog organism and x names one: d's organism is
               another organism only when it is another CatLog organism of the paper (org_ok: a name that is none of
               them is a synonym, strain or reclassification of one the databases do not name; common names such as
               'hamster' read as binomials; 'A; B' lists the number for A and for B).
  conditions   pH within 0.3 and temperature within 2.5 C when both state them (pairing only).
A Km printed over a mass concentration (mg/mL) and its kcat/Km (mL mg^-1 s^-1) are not compared (catlog.py molar(): the
databases list mM): status not_compared, reason mass_concentration, and they take no part in pairing, in the database
rows CatLog reproduces or in the Stats.
Category per value, across the databases in SOURCES (first that applies): CONFIRMED (a close row with a fitting label);
DIFFERS (an unreproduced database row of a fitting label and conditions was paired to it: exact power of ten first,
then a time factor, of several values at one factor the one nearest it, else the nearest; 'unique' or 'closest of
N'); SAME_NUMBER_LABEL_DIFFERS (a close row under another substrate, variant or organism); NEW_b (the paper has
database rows, none of the above; reason metric_absent / substrate_absent / variant_absent / condition_absent); NEW_a
(no kcat, Km or kcat/Km row for the paper at all).
A database row a check against the paper recorded as another measurement (verdict different_measurement) is left out
of the value's comparison, so the value gets the status the other rows give it.

Exact factors: CatLog / database = 10^n (n != 0); or a time factor 60 or 3,600 (x 10^n): kcat with n = 0 only, kcat/Km
with n in {0, +-3, +-6} (min and h against s, with M, mM or uM), never Km.

database_check status: confirmed | corrected | differs | same_number_other_label | new | not_compared.
  corrected = DIFFERS by 1.5x or more that passes rule A (code states the relation: unique pairing; the database
  number is the printed number with its unit or header factor not applied, an exact time factor or an exact power of
  ten, or the printed value read in its printed unit where CatLog reads that unit otherwise; AND the paper's own
  kcat ÷ Km supports CatLog's number, not the database's (closure supports_catlog: the site's found_by
  factor_cross_checked). An exact factor alone states no correction (the site's decision of 2026-10-15): such a value
  is differs with its relation and factor kept (site_release: cause exact_factor, "not yet checked against the
  paper"), and dbdiff sends it to a check against the paper like any difference. A printed unit CatLog reads
  otherwise (evidence.unit_for_conversion) that the database lists as printed gets cause paper_unit_misprint
  (cause_by code) when the paper's own kcat ÷ Km supports CatLog's reading. Or a recorded cause.
  differs = every other DIFFERS (cause not yet known) and every difference under 1.5x.
Fields (empty ones left out; site_release publishes only the line it builds from them, the status, the sources and a
recorded cause and evidence): status; paper_not_in_databases; sources (databases listing the number shown: confirming,
paired, or under another label); database_value and database_unit (the paired or confirming row, catalog units);
database_entry ('SABIO-RK 18485', where the source has entry ids); figures (0: within 2%; 1 or 2: the same number only
to that many significant figures); rounded ({database: [number, figures]}: confirming databases whose number is not
within 2%); same_values ({database: number}: the other confirming databases, each with its own number within 2%, so
the site can name each database's number: site_release.database_by_source); factor (CatLog / database); relation
(printed_number_unit_not_applied: the database number is the printed number and the paper's unit or header factor was
not applied; printed_unit_as_printed: the database number is the printed value read in its printed unit, which CatLog
reads otherwise; time_factor, power_of_ten, other_factor, under_1.5x); derivation
(time_factor: database = printed x 60^a x 10^n as {printed, a, n}); pairing; cause and cause_by (code, or who
recorded it: paper_check, verifier, audit); evidence (recorded; one location plus printed facts); printed,
printed_unit, where (evidence.raw_value, raw_unit, location); read_as (CatLog's unit_for_conversion when it overrides
the printed unit); closure (supports_catlog, supports_database, neither: the paper's own kcat / Km against its printed
kcat/Km with either number, within the tolerance of catlog.py ratio_check; left out when CatLog read any of the three
in another unit than printed, an override that only respells the printed unit ('micromol' read as 'uM') not counted) and
closure_fold (the fold, >= 1, between kcat / Km and the printed kcat/Km for the number supported: the line says 'matches'
only within 1.5x, else 'is nearer to'); other_values (databases that list another number for this value only, at an exact
factor of it: unique pairings at 10^n or a time factor, and a database paired within 2% of the number named that lists
it otherwise); other_measurement
({database: number} a check against the paper found to be another measurement); database_label (the label under
which a database lists the same number: "for wild type", "with no mutation named", "for Escherichia coli", "for
substrate 'Dha'"; databases share it only when they list the same number under the same label, the rest go to
other_labels: [{sources, database_value, figures, database_label}], so a line names each database with its own number);
reason (why a value is new); ratio_only (a new printed kcat/Km whose kcat and Km are both confirmed) and ratio_sources
({'kcat': [...], 'Km': [...]}: the databases that list the measurement's kcat and its Km, so the line names them);
paper_sources
(the databases that list any kcat, Km or kcat/Km from the paper), and so that a line names every one of them: for a
database the fields above do not name, other_labels (the value's number under another label), other_numbers (other
values of the parameter only) or no_metric (none of the parameter); on a new value pair_numbers (other values of the
parameter for its substrate and variant), other_numbers or no_metric for each.

Recorded causes: sources/database_corrections.tsv (row_id, pmid, metric, database, database_value, verdict, cause,
evidence, recorded_by, date; database_value in catalog units, mM, s^-1, mM^-1 s^-1), filled by the per-paper checks
against the paper that run after export. Per value and database the latest row counts (by date, then by its place in
the file), so a later re-check replaces an earlier verdict. verdict corrected -> corrected with its cause and evidence,
naming the recorded database number; different_measurement -> that database row is left out of the comparison (not a
correction; the line says it is another measurement of the paper); catlog_wrong -> differs, and `catlog.py status`
lists the value for an audit until an audit after that date keeps or drops it; ambiguous -> differs. Across databases
catlog_wrong comes before corrected, corrected before ambiguous. The file is plain TSV (no quoting: a '"' is text);
metric and verdict are case-blind (km, kcat_over_km, Corrected). A missing header column, a row with another number of
fields than the header, an unknown verdict, cause, database or metric, a row_id not in the catalog, a metric that is
not that value's, a value that is not compared (mass concentration), or a correction whose database row is labelled
for another measurement (label_conflict()) is listed by `catlog.py export` and `status` (usable()), never dropped
silently, and the value's row before it stays in effect. Databases are never evidence for a value (CLAUDE.md): this
runs on the finished export, never while reading or verifying.

Inputs (catlog-v2 only): the catalog rows and the export's measurements (passed in), papers.tsv, rejected.jsonl,
sources/db_values.tsv, enrich/structures.json, sources/natural_forms.tsv, sources/database_corrections.tsv,
work/<pmid>.read.json (reader notes: reprints) and texts/<pmid>.txt (+ .supp.txt), for why a database number is not
in CatLog (`unreproduced`, the Stats figure; database rows of finished papers with no CatLog value count too).
"""
import bisect, csv, datetime, io, json, math, re, sys
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from human_review import _name as hr_name, _bare as bare  # noqa: E402  (the review's name matching)
from units import normalize, parse_number, MASS_UNIT  # noqa: E402  (catlog.py's reading of a printed cell and unit)

csv.field_size_limit(sys.maxsize)
SOURCES = ('BRENDA', 'SABIO-RK', 'OED', 'SKiD', 'STRENDA', 'UniProt')  # the sources of db_values.tsv, in this order
METRIC_ORDER = ('kcat', 'Km', 'kcat/Km')
UNIT = {'kcat': 's^(-1)', 'Km': 'mM', 'kcat/Km': 's^(-1)*mM^(-1)'}  # the export's catalog units
CORRECTIONS = 'sources/database_corrections.tsv'
CORRECTION_COLS = ('row_id', 'pmid', 'metric', 'database', 'database_value', 'verdict', 'cause', 'evidence',
                   'recorded_by', 'date')
VERDICTS = ('corrected', 'different_measurement', 'catlog_wrong', 'ambiguous')
CAUSES = ('header_scale_inverted', 'header_scale_ignored', 'unit_not_converted', 'uM_entered_as_mM', 'mM_entered_as_uM',
          'time_unit', 'decimal_or_exponent_slip', 'value_from_other_row', 'value_not_in_paper', 'paper_unit_misprint',
          'recomputed_ratio', 'different_measurement')
RECORDERS = ('paper_check', 'verifier', 'audit')
# why a database row of a CatLog paper has no CatLog number (first that applies; report section 1.4)
UNREPRODUCED = ('paired_with_different_number', 'another_measurement_per_paper_check', 'rejected_by_catlog_checks',
                'equals_catlog_calculated_ratio', 'another_parameter_in_catlog', 'catlog_kept_no_values_from_paper',
                'no_substrate_named_paper_has_several', 'reprinted_from_other_work', 'next_to_other_quantity',
                'possible_catlog_miss', 'possible_miss_weak', 'paper_awaits_supplement', 'not_in_paper_text',
                'no_text_on_disk')


# ---------------------------------------------------------------- numbers
def num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def within2(a, b):
    return abs(a - b) <= 0.02 * max(abs(a), abs(b))


def sigdig(s):
    m = str(s).strip().lower().split('e')[0].lstrip('+-')
    d = re.sub(r'[^0-9]', '', m).lstrip('0')
    if '.' not in m:
        d = d.rstrip('0') or d[:1]
    return len(d)


def written_figures(v):
    """The significant figures of a number as its shortest decimal writes it, an integer's trailing zeros not counted
    (0.14 2, 8.6 / 60 = 0.143333... 15, 1400 2, 1e-05 1)."""
    return sigdig(f'{v:.15g}')


def two_figures(a, b, fa=None, fb=None):
    """One number carries at most 2 significant figures (fa, fb: as printed or listed; else as written_figures) and
    both round half up to the same 2 figures (0.14 and 0.1433, 0.1 and 0.104; CatLog's 0.11 min^-1 uM^-1 = 1.83 mM^-1
    s^-1 and 1.777). Never two numbers that both carry 3 or more figures (135 and 144, 117.1 and 123.6), nor 14.1 and
    14.5 or 1.15 and 1.1 (half up: 15 and 1.2)."""
    fa = written_figures(a) if fa is None else fa
    fb = written_figures(b) if fb is None else fb
    return min(fa, fb) <= 2 and at_figures(a, round_sig(b, 2), 2)


def close(a, b):
    return within2(a, b) or two_figures(a, b)


def round_sig(v, k):
    """v rounded half up to k significant figures, on its decimal digits (0.00905 -> 0.0091 at 2, 2.5 -> 3 at 1)."""
    d = Decimal(repr(v))
    e = d.adjusted()
    return float(d.scaleb(-e).quantize(Decimal(1).scaleb(1 - k), ROUND_HALF_UP).scaleb(e))


def round1(v):
    """v rounded half up to one significant figure (2.5 -> 3, 0.583 -> 0.6, 0.00117 -> 0.001)."""
    return round_sig(v, 1)


def printed_figures(s):
    """The significant figures a number is written with ('0.0086' 2, '2.17e-05' 3, '1.50' 3); an integer's trailing
    zeros count ('2000' 4: equal only to 2000, never to 1980)."""
    m = str(s).strip().lower().split('e')[0]
    return max(1, len(re.sub(r'[^0-9]', '', m).lstrip('0')))


def at_figures(v, number, k):
    """v rounded half up to k significant figures is number (v and number positive)."""
    return abs(round_sig(v, k) - number) <= 1e-9 * abs(number)


def figures(v, value, vstr, fv=None):
    """How a CatLog number v (printed with fv significant figures; None: as v writes) matches a database number: 0
    within 2%, 2 one of them carries at most 2 significant figures (the database's as listed, vstr) and the other
    rounds half up to it (two_figures), 1 the database printed one significant figure (not an integer ending in 0,
    whose figures are ambiguous) and v rounds half up to it (BRENDA '0.001' for 0.00117); None when they differ."""
    if within2(v, value):
        return 0
    if two_figures(v, value, fa=fv, fb=sigdig(vstr)):
        return 2
    s = str(vstr).strip()
    if sigdig(s) == 1 and not re.fullmatch(r'\d*0', s) and abs(round1(v) - value) <= 1e-9 * value:
        return 1
    return None


def close_ref(x, d):
    return figures(x['value'], d['value'], d['vstr'], x.get('figs')) is not None


# a printed cell's first number as site_release._figures reads it: digit groups after ',' or ' ' are one number
# ('14 104', '15,000'), a lone ',' between digits is a decimal comma ('7,15'); control characters are left out
CELL_NUM = re.compile(r'[1-9]\d{0,2}(?:[, ]\d{3})+(?:\.\d+)?|\d+(?:[.,]\d{3}(?: \d{1,3})+|[.,]\d+)?|\.\d+')


def cell_figures(raw, v):
    """The significant figures of a CatLog value as its printed cell writes them (0.11 min^-1 uM^-1 is 2 figures,
    though 1.8333 mM^-1 s^-1 writes 6; '1.60' 3 and '1.00 × 10^5' 3, a decimal's trailing zeros count; '14 104' 5; an
    integer's trailing zeros not counted); as v writes them when the cell has no number."""
    m = CELL_NUM.search(re.sub(r'[\x00-\x1f\x7f-\x9f\u200b-\u200f\ufeff]', '', str(raw or '')))
    if m:
        s = m.group(0).replace(' ', '')
        s = s.replace(',', '') if re.fullmatch(r'[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?', s) else s.replace(',', '.')
        if sigdig(s) and float(s):
            return sigdig(s)
    return written_figures(v) if v else 0


TOL = math.log10(1.02)
SMALL_FACTOR = 1.5  # a difference under this many-fold is 'under_1.5x': shown, never sent to a check of the paper (dbcheck)
TIME_N = {'kcat': {0}, 'kcat/Km': {0, 3, -3, 6, -6}, 'Km': set()}  # the powers of ten a time factor may carry


def factor(v, db, metric):
    """(class, label) of CatLog / database: unit_10^n, time_60_3600 (TIME_N), small_<1.5x or other."""
    q = v / db
    L = math.log10(q)
    n = round(L)
    if n and abs(L - n) <= TOL:
        return 'unit_10^n', f'x10^{n}'
    for t in (60, 3600):
        for sgn in (1, -1):
            L2 = L - sgn * math.log10(t)
            n2 = round(L2)
            if abs(L2 - n2) <= TOL and n2 in TIME_N.get(metric, ()):
                return 'time_60_3600', ('x' if sgn > 0 else '/') + str(t) + (f' x10^{n2}' if n2 else '')
    big = max(q, 1 / q)
    if big < SMALL_FACTOR:
        return 'small_<1.5x', f'x{q:.3g}'
    return 'other', f'x{q:.3g}'


def exact(cls):
    return cls in ('unit_10^n', 'time_60_3600')


def exact_fit(q, metric):
    """(distance in log10 to the exact factor, |n|) of CatLog / database = q for an exact factor (factor(): 10^n, or 60
    or 3,600 x 10^n), else None. Among several values at one exact factor of a database number, the one nearest the
    factor is its pairing (BRENDA 0.0115 is 115 / 10^4, not 114 / 10^4); the smaller distance is not the smaller q."""
    L = math.log10(q)
    n = round(L)
    if n and abs(L - n) <= TOL:
        return abs(L - n), abs(n)
    for t in (60, 3600):
        for sgn in (1, -1):
            L2 = L - sgn * math.log10(t)
            n2 = round(L2)
            if abs(L2 - n2) <= TOL and n2 in TIME_N.get(metric, ()):
                return abs(L2 - n2), abs(n2)
    return None


SUPS = str.maketrans('⁻⁰¹²³⁴⁵⁶⁷⁸⁹−–', '-0123456789--')
NUMBER = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')
TEN = r'(?:[×xX*✕]|\\times)\s*10\s*(?:\^|\*\*)?\s*[{(]?\s*([-+]?\d+)\s*[})]?'
TIMES_TEN = re.compile(r'\s*' + TEN)
def printed_number(raw):
    """The number a printed cell states, read as catlog.py reads it (units.parse_number): '7,100'; '(5.1 ± 0.7) × 10^5',
    '5.1 ± 0.7 × 10^5' and '4.2 (2.0) × 10^-1' carry their 10^n; in '0.004 ± 0.6 × 10^-3' it belongs to the ± part.
    None without a number."""
    try:
        return parse_number(raw)
    except Exception:
        return None


def _database_figures(text):
    """The significant figures of a recorded database value as written (printed_figures of its number)."""
    m = NUMBER.search(re.sub(r'(?<=\d),(?=\d{3})', '', str(text or '').translate(SUPS)))
    return printed_figures(m.group(0)) if m else 0


def _database_number(text):
    """A recorded database value ('0.0086 mM^-1 s^-1', '1.5 × 10^-6', '1.5e-6', '1.5 × 10⁻⁶ mM⁻¹ s⁻¹') as a number."""
    s = re.sub(r'(?<=\d),(?=\d{3})', '', str(text or '').translate(SUPS))
    m = NUMBER.search(s)
    if not m:
        return None
    v = num(m.group(0))
    e = TIMES_TEN.match(s[m.end():])
    return v * 10 ** int(e.group(1)) if v is not None and e else v


def _as_printed(metric, ev):
    """The printed value in catalog units read with its printed unit (units.normalize), whatever unit CatLog read it
    in; None when that unit cannot be read."""
    try:
        return normalize(metric, ev.get('raw_value') or '', ev.get('raw_unit') or '')[0]
    except Exception:
        return None


def override(ev):
    """CatLog's unit_for_conversion when it replaces the printed unit, else ''."""
    u = (ev.get('unit_for_conversion') or '').strip()
    return u if u and u != (ev.get('raw_unit') or '').strip() else ''


AMOUNT_WORD = re.compile(r'(?<![A-Za-z])(micro|milli|nano|pico|[µμunpm])?mol(?:es?|s)?(?![A-Za-z])', re.I)
AMOUNT_PREFIX = {'micro': 'u', 'µ': 'u', 'μ': 'u', 'u': 'u', 'milli': 'm', 'm': 'm', 'nano': 'n', 'n': 'n', 'pico': 'p',
                 'p': 'p', '': ''}


def respelled(metric, ev):
    """CatLog's unit_for_conversion only respells the printed unit (30926626: Km printed in 'micromol', read as 'uM'):
    the printed cell read with it gives the number the printed unit gives, an amount word ('micromol', 'µmol') taken as
    its concentration. Such an override is no other reading of the paper."""
    u = override(ev)
    if not u:
        return False
    cell, raw = ev.get('raw_value') or '', ev.get('raw_unit') or ''
    try:
        a, b = normalize(metric, cell, u)[0], normalize(metric, cell, raw)[0]
        if b is None:
            b = normalize(metric, cell, AMOUNT_WORD.sub(lambda m: AMOUNT_PREFIX[(m.group(1) or '').lower()] + 'M', raw))[0]
    except Exception:
        return False
    return a is not None and b is not None and abs(a - b) <= 1e-9 * max(abs(a), abs(b))


def relate(metric, dval, cls, ev):
    """What code can state about the database number named: under_1.5x; printed_unit_as_printed (CatLog reads the
    unit otherwise, and the database number is the printed value read in the printed unit); printed_number_unit_
    not_applied (it is the printed number: the paper's unit or header factor not applied); time_factor (TIME_N);
    power_of_ten; other_factor. With the derivation of a time factor: database = printed x 60^a x 10^n."""
    if cls == 'small_<1.5x':
        return 'under_1.5x', None
    if override(ev):  # the database read the printed unit as printed; CatLog reads it otherwise
        pv = _as_printed(metric, ev)
        if pv and close(dval, pv):
            return 'printed_unit_as_printed', None
    p = printed_number(ev.get('raw_value'))
    if p and p > 0 and close(dval, p):
        return 'printed_number_unit_not_applied', None
    if cls == 'time_60_3600':
        der = None
        if p and p > 0:
            L = math.log10(dval / p)
            for a in (1, -1, 2, -2):
                n = round(L - a * math.log10(60))
                if abs(L - a * math.log10(60) - n) <= TOL and n in TIME_N[metric]:
                    der = {'printed': p, 'a': a, 'n': n}
                    break
        return 'time_factor', der
    return {'unit_10^n': 'power_of_ten'}.get(cls, 'other_factor'), None


# ---------------------------------------------------------------- names
METAL_NT = re.compile(r'(?:mg|mn|ca|co|zn|ni|fe|cd|cu)?(d?[acgitu][mdt]p)(?:mg|mn|ca|co|zn|ni|fe|cd|cu)?\d*')
SALT = re.compile(r'\b(?:(?:mono|di|tri|tetra)?(?:sodium|potassium|lithium|ammonium|calcium|magnesium|barium|'
                  r'cyclohexylammonium|triethylammonium|tris)\s+salts?|(?:di)?hydrochloride|(?:mono|di|tri)?hydrate|salt|anion)\b', re.I)
LEAD_SALT = re.compile(r'^(?:mono|di|tri|tetra)?(?:sodium|potassium|lithium|ammonium|calcium|magnesium)\s+(?=\S)', re.I)
SYN = {'hydrogenperoxide': 'h2o2', 'oxygen': 'o2', 'dioxygen': 'o2', 'molecularoxygen': 'o2', 'carbondioxide': 'co2',
       'bicarbonate': 'hco3', 'hydrogencarbonate': 'hco3', 'pyrophosphate': 'ppi', 'diphosphate': 'ppi',
       'inorganicpyrophosphate': 'ppi', 'orthophosphate': 'pi', 'inorganicphosphate': 'pi', 'phosphate': 'pi',
       'water': 'h2o', 'ammonia': 'nh3', 'ammonium': 'nh3', 'nh4': 'nh3', 'nicotinamideadeninedinucleotide': 'nad',
       'nicotinamideadeninedinucleotidephosphate': 'nadp', 'reducednicotinamideadeninedinucleotide': 'nadh'}
GENERIC_DB = {'', 'more', '?', '-', '-----', 'nd', 'n.d.', 'substrate', 'none'}
ST = None  # tools/structures.py (offline table routes only), imported by compare(): it loads RDKit


def _finish_key(k):
    k = bare(k).replace('coenzymea', 'coa')
    k = re.sub(r'^(?:beta|alpha)(nadp?h?)$', r'\1', k)
    return SYN.get(k, k)


def _cands(s):
    c = [s] + [v for v, _ in ST.rewrites(s)]
    for x in list(c):
        y = LEAD_SALT.sub('', SALT.sub('', x)).strip(' ,;-()')
        if y and y != x:
            c.append(y)
    return c


@lru_cache(maxsize=None)
def name_keys(s):
    return frozenset(k for k in (_finish_key(hr_name(c)) for c in _cands(s)) if k) if s else frozenset()


@lru_cache(maxsize=None)
def ns_keys(s):
    if not s:
        return frozenset()
    return frozenset(k for k in (_finish_key(re.sub(r'[^a-z0-9]', '', ST.strip_stereo(c))) for c in _cands(s)) if k)


@lru_cache(maxsize=None)
def key14(smi):
    try:
        return ST.key(smi, 14) if smi else ''
    except Exception:
        return ''


@lru_cache(maxsize=None)
def db_struct(name, ec):
    """InChIKey connectivity of a database substrate name: Rhea participants of its EC, ChEBI 3-star, SABIO-RK name,
    ChEBI 2-star (tools/structures.py offline routes), also on its standard spelling rewrites."""
    for n in [name] + [v for v, _ in ST.rewrites(name)]:
        for f in (lambda: ST.rhea_hit(n, ec)[0] if ec else None, lambda: ST.chebi_hit(n, 3),
                  lambda: ST.sabio_name_hit(n), lambda: ST.chebi_hit(n, 2)):
            try:
                h = f()
            except Exception:
                h = None
            if h and h.get('smiles'):
                k = key14(h['smiles'])
                if k:
                    return k
    return ''


# ---------------------------------------------------------------- variants, organisms, conditions
MUT = re.compile(r'(?<![A-Za-z0-9])[A-Z][a-z]{0,2}\d+[A-Z][a-z]{0,2}(?![A-Za-z0-9])')  # whole token: not K2HPO4, H2O
AA3 = {'Ala': 'A', 'Arg': 'R', 'Asn': 'N', 'Asp': 'D', 'Cys': 'C', 'Gln': 'Q', 'Glu': 'E', 'Gly': 'G', 'His': 'H', 'Ile': 'I',
       'Leu': 'L', 'Lys': 'K', 'Met': 'M', 'Phe': 'F', 'Pro': 'P', 'Ser': 'S', 'Thr': 'T', 'Trp': 'W', 'Tyr': 'Y', 'Val': 'V'}
AA1 = set('ACDEFGHIKLMNPQRSTVWY')
WT_WORD = re.compile(r'wild[\s_-]?type|\bwt\b', re.I)
TAG = re.compile(r'tag|fusion|\bGST\b|\bMBP\b', re.I)
MUT_WORD = re.compile(r'mutant|variant|delet|Δ|delta|truncat|chimer|substitut|insert', re.I)
# a deletion or truncation: 'delta39', 'delta 1-53', 'Ndelta90', 'ΔN', 'deleted aa1-72', 'truncated', 'lacking 162
# C-terminal residues'; never 'AnCEdeltaCHO' (deglycosylated), 'lacking glycosylation' or a name such as 'DELTAAsp168'
# (21803176 names its D166A/I167A/D168A mutant 'ΔAsp168')
TRUNC_WORD = re.compile(r'delet|truncat|lacking\b[^,;]{0,40}?\b(?:residues?|amino acids?|aa|terminal|terminus|domain|first|last)\b|'
                        r'(?:Δ|delta)\s*(?:\d|[NC](?![a-z]))', re.I)
NOT_TRUNC = re.compile(r'chimer|substitut|insert|\d+Ins[A-Z]', re.I)  # another change ('G211InsG')
TAG_NUMBER = re.compile(r'His\s*-?\d+|\d+\s*[x×]?\s*-?His', re.I)  # 'His6': not a residue number
FORM_WORD = re.compile(r'\b(?:isoform|isozyme|isoenzyme)\b', re.I)


def mutset(text):
    out = set()
    for t in MUT.findall(re.sub(r'(?<=\d)\*(?=[A-Z])', '', str(text or ''))):  # 'H14*N' is H14N
        a, n, b = re.fullmatch(r'([A-Z][a-z]{0,2})(\d+)([A-Z][a-z]{0,2})', t).groups()
        a, b = AA3.get(a, a), AA3.get(b, b)
        if a in AA1 and b in AA1:
            out.add(f'{a}{n}{b}')
    return frozenset(out)


def catlog_variant(r, natural):
    v = str(r.get('variant') or '')
    if (r['pmid'], v) in natural:
        return 'wt', frozenset()
    v = re.sub(r'(?<![A-Za-z0-9])([A-Z][a-z]{0,2}\d+) (?=[A-Z][a-z]{0,2}(?:[/,;)\s]|$))', r'\1', v)  # 'W139 F' is W139F
    muts = mutset(v)
    rest = MUT.sub('', v)
    rest = '' if re.fullmatch(r'\W*(wild[ -]?type|wt|native|wildtype)?\W*', rest, re.I) else re.sub(r'\W', '', rest.lower())
    if rest and not muts and rest in re.sub(r'\W', '', str(r.get('enzyme') or '').lower()):
        rest = ''
    return ('mut' if muts else 'other' if rest else 'wt'), muts


def _variant_field(src, comment):
    """The variant field of a SABIO-RK, OED or UniProt row (its second ';' part, entry ids left out)."""
    c = re.sub(r'UniProt\s+[^\s;]+', ' ', comment or '')
    c = re.sub(r'\b(?:SABIO|SKiD|STRENDA)\s+[^\s;]+', ' ', c)
    parts = [p.strip() for p in c.split(';')]
    return parts[1] if len(parts) > 1 else ''


def _trunc(text):
    """A variant text that names only a deletion or truncation ('delta39 C-terminal His6-tag', 'mutant lacking 162
    C-terminal residues'): no point mutation and no other change."""
    return bool(TRUNC_WORD.search(text)) and not NOT_TRUNC.search(text) and not mutset(text)


def db_variant(src, comment):
    """(kind, point mutations, name, wild type stated) of a database row. kind: 'wt', 'mut', 'trunc' (a deletion or
    truncation only, no point mutation: SABIO-RK 'delta39 C-terminal His6-tag', BRENDA 'mutant lacking 162 C-terminal
    residues'; name: the database's own words, for the line) or 'named' (SABIO-RK/OED/UniProt: a form named without
    point mutations, e.g. 'psi epg0', 'Ala105', 'C315/318S', UniProt's 'ADH1B*2'; name normalized for matching). BRENDA
    and SKiD name mutants; a row that names none is matched as wild type, but says so only when it does."""
    c = re.sub(r'UniProt\s+[^\s;]+', ' ', comment or '')
    stated = bool(WT_WORD.search(c))
    if src in ('SABIO-RK', 'OED', 'UniProt'):
        seg = _variant_field(src, comment)
        m = mutset(seg)
        if m:
            return 'mut', m, '', False
        if _trunc(seg):
            return 'trunc', frozenset(), re.sub(r'\s+', ' ', seg).strip(), False
        if MUT_WORD.search(seg):
            return 'mut', frozenset(), '', False
        if not seg or WT_WORD.search(seg) or TAG.search(seg):
            return 'wt', frozenset(), '', bool(WT_WORD.search(seg))
        # UniProt's 'isoform 2' is that entry's own isoform: the name is kept whole ('isoform2'), so it fits only a CatLog
        # value that names it, never another form's wild type
        n = re.sub(r'[^a-z0-9]', '', (seg if src == 'UniProt' else FORM_WORD.sub('', seg)).lower())
        return ('named', frozenset(), n, False) if len(n) >= 3 else ('wt', frozenset(), '', False)
    if src == 'SKiD':
        m = re.search(r'mutant\s+([^;]*)', c)
        if not m or re.fullmatch(r'\W*-+\W*|\W*', m.group(1)):
            return 'wt', frozenset(), '', stated
        if _trunc(m.group(1)):
            return 'trunc', frozenset(), re.sub(r'\s+', ' ', m.group(1)).strip(), False
        return 'mut', mutset(m.group(1)), '', False
    if src == 'BRENDA':
        if re.search(r'mutant|variant', c, re.I):
            part = next((p.strip() for p in re.split(r',\s*|;\s*', c) if TRUNC_WORD.search(p)), '')
            if part and _trunc(c):  # the comment's part that names it: 'mutant lacking 162 C-terminal residues'
                return 'trunc', frozenset(), re.sub(r'\s+', ' ', part), False
            return 'mut', mutset(c), '', False
        return 'wt', frozenset(), '', stated
    return 'wt', frozenset(), '', stated  # STRENDA: protein name only


def vok(x, d):
    vk, dk = x['vk'], d['vk']
    if dk == 'mut':
        return vk == 'mut' and x['vm'] == d['vm'] if d['vm'] else vk in ('mut', 'other')
    if dk == 'named':  # a point mutant only when its own variant text gives the name ('TEM-109 (M69L/E104K/R164H)')
        return d['vname'] in x['vtext'] and (vk != 'mut' or named_in(d['vname'], x.get('vraw', '')))
    if dk == 'trunc':  # a deletion or truncation only: a value without point mutations (span_fit prefers its construct)
        return vk != 'mut'
    return vk in ('wt', 'other')


def named_in(name, text):
    """A normalized form name ('tem109', 'ex3') is written in a variant text as a whole ('TEM-109 (M69L/...)', 'EX3
    (E41G/...)'; never 'EX3' in 'EX30')."""
    pat = r'\W*'.join(map(re.escape, name))
    return bool(name) and bool(re.search(r'(?<![A-Za-z0-9])' + pat + r'(?![A-Za-z0-9])', str(text or ''), re.I))


def span_fit(x, d):
    """How a CatLog value's construct fits a database row that names only a deletion or truncation: 2 every residue
    number the row names is in the value's construct or variant text ('delta 1-53' and 'Δ1–53 (residues 54–612)'), 1
    the value states a truncation ('residues 1-194', 'lacking the first 39 residues'), 0 neither (or another kind of row)."""
    if d['vk'] != 'trunc':
        return 0
    have = set(re.findall(r'\d+', TAG_NUMBER.sub(' ', x.get('ctext', ''))))
    want = set(re.findall(r'\d+', TAG_NUMBER.sub(' ', d['vname'])))
    if want and want <= have:
        return 2
    return 1 if TRUNC_WORD.search(x.get('ctext', '')) or re.search(r'residues?\s+\d+\s*[-–]\s*\d+', x.get('ctext', '')) else 0


def _quoted(seg):
    seg = re.sub(r'\s+', ' ', seg).strip()
    return f"'{seg if len(seg) <= 60 else seg[:60].rsplit(' ', 1)[0] + ' …'}'"


def variant_label(d):
    """('for', what) or ('with', what): the variant a database row names, in words (a named form or a deletion in
    the database's own words, never 'a mutant' for a truncation)."""
    if d['vk'] == 'mut':
        if d['vm']:
            return 'for', 'mutant ' + '/'.join(sorted(d['vm']))
        if d['src'] in ('SABIO-RK', 'OED', 'UniProt'):  # the database's own words: 'delta-Crystallin Ia', 'variant S403'
            own = _variant_field(d['src'], d['comment'])
        else:  # BRENDA's or SKiD's part that names it ('mutant TRUN1-8'), unless it says no more than 'mutant', also
            # names wild type or runs past 60 characters
            own = next((p for p in re.split(r',\s*|;\s*', d['comment'] or '') if re.search(r'mutant|variant', p, re.I)
                        and re.sub(r'\W|\b(?:mutants?|variants?|enzymes?|recombinant|the|a)\b', '', p, flags=re.I)), '')
            own = '' if len(own) > 60 or WT_WORD.search(own) else re.sub(r'^(?:for|of|with|in)\s+', '', own, flags=re.I)
        return 'for', _quoted(own) if own.strip() else 'a mutant'
    if d['vk'] == 'named':
        return 'for', _quoted(_variant_field(d['src'], d['comment']))
    if d['vk'] == 'trunc':
        return 'for', _quoted(d['vname'])
    return ('for', 'wild type') if d['wt_stated'] else ('with', 'no mutation named')


def _and(items):
    return ', '.join(items[:-1]) + ' and ' + items[-1] if len(items) > 1 else ''.join(items)


def genus_species(o):
    return ' '.join([t for t in re.findall(r'[a-z]+', str(o or '').lower()) if t != 'x'][:2])  # Fragaria x ananassa


def same_organism(a, b, paper):  # human_review._same_organism, with the hybrid 'x' left out
    a, b = genus_species(a), genus_species(b)

    def epithet(o):
        return o.split()[1] if len(o.split()) == 2 and o.split()[1].rstrip('.') not in ('sp', 'spp') else ''

    def stem(e):
        return re.sub(r'(?:us|um|is|ae|a|e|i)$', '', e)
    return a == b or (bool(epithet(a)) and epithet(a) == epithet(b) and sum(epithet(o) == epithet(b) for o in paper) == 1) \
        or (bool(epithet(a)) and bool(epithet(b)) and a.split()[0] == b.split()[0] and len(stem(epithet(a))) >= 5
            and stem(epithet(a)) == stem(epithet(b)))


# common names papers use for an organism (the export keeps the paper's word unless enrich.COMMON maps it), as the
# binomials the databases list; for comparison only
ORG_WORDS = {'hamster': ('mesocricetus auratus', 'cricetulus griseus'), 'syrian hamster': ('mesocricetus auratus',),
             'chinese hamster': ('cricetulus griseus',), 'guinea pig': ('cavia porcellus',), 'sheep': ('ovis aries',),
             'ovine': ('ovis aries',), 'horse': ('equus caballus',), 'equine': ('equus caballus',), 'goat': ('capra hircus',),
             'duck': ('anas platyrhynchos', 'cairina moschata'), 'mushroom': ('agaricus bisporus',),
             'yeast': ('saccharomyces cerevisiae',), "baker's yeast": ('saccharomyces cerevisiae',),
             "brewer's yeast": ('saccharomyces cerevisiae',), 'tomato': ('solanum lycopersicum', 'lycopersicon esculentum'),
             'electric eel': ('electrophorus electricus',), 'canine': ('canis lupus', 'canis familiaris'),
             'dog': ('canis lupus', 'canis familiaris'), 'canine (dog)': ('canis lupus', 'canis familiaris'),
             'opossum': ('didelphis virginiana', 'monodelphis domestica'), 'tuna': ('thunnus',),
             'hiv-1': ('human immunodeficiency',), 'hiv-2': ('human immunodeficiency',), 'maize': ('zea mays',),
             'sorghum': ('sorghum bicolor',), 'pea': ('pisum sativum', 'lathyrus oleraceus')}


def org_names(o):
    """The genus-species keys an organism text stands for: its own, a binomial it gives in parentheses ('horseradish
    (Armoracia rusticana)'), the species a common name means ('hamster': Mesocricetus auratus or Cricetulus griseus)."""
    t = str(o or '').strip()
    keys = {genus_species(t)} | {genus_species(p) for p in re.findall(r'\(([A-Z][a-z]+ [a-z]+)', t)}
    keys |= set(ORG_WORDS.get(t.lower(), ()) or ORG_WORDS.get(re.sub(r'\s*\(.*', '', t).lower(), ()))
    return {k for k in keys if k}


def org_parts(o):
    """The organisms an organism text names: one, or several ('Streptomyces griseus; Streptomyces lividans', a
    database's number listed for each; a CatLog chimera 'maize (Glu1 N-terminal region) and sorghum (Dhr1 C-terminal
    region)'), split outside parentheses."""
    t, depth, parts, cur = str(o or ''), 0, [], ''
    for ch in t:
        depth += (ch == '(') - (ch == ')')
        cur += ch
        if depth == 0 and (cur.endswith(';') or cur.endswith(' and ')):
            parts.append(re.sub(r'(?:;| and )$', '', cur))
            cur = ''
    parts = [p.strip() for p in parts + [cur] if p.strip()]
    return parts if len(parts) > 1 and all(org_names(p) for p in parts) else [t]


def _one_org(a, b, paper):
    return any(same_organism(p, q, paper) or (len(p.split()) == 1 and q.split()[0] == p) or (len(q.split()) == 1 and p.split()[0] == q)
               for p in org_names(a) for q in org_names(b))


def same_org(a, b, paper):
    """Two CatLog organisms are one under any of their names (org_names; same_organism); one of several organisms
    (a chimera) is the same only as one of the same organisms (org_parts)."""
    pa, pb = org_parts(a), org_parts(b)
    if len(pa) != len(pb):
        return False
    if len(pa) == 1:
        return _one_org(a, b, paper)
    return all(any(_one_org(p, q, paper) for q in pb) for p in pa) and all(any(_one_org(p, q, paper) for p in pa) for q in pb)


def org_fits(x, d, paper):
    """A database organism d names the CatLog organism x: a database lists one number for each organism of 'A; B'
    (BRENDA 1.2 mM for 'Streptomyces griseus; Streptomyces lividans'), so it names x when one of them is x; a CatLog
    chimera of several organisms only an entry of the same organisms."""
    if len(org_parts(x)) > 1:
        return same_org(x, d, paper)
    return any(_one_org(x, q, paper) for q in org_parts(d))


def db_conditions(comment):
    c = re.sub(r'UniProt\s+[^\s;]+', ' ', comment or '')
    ph = re.search(r'pH\s*([0-9]+(?:\.[0-9]+)?)', c)
    t = re.search(r'(?<![\w.])([0-9]{1,3}(?:\.[0-9]+)?)\s*°?\s*C\b', c)
    return (float(ph.group(1)) if ph else None), (float(t.group(1)) if t else None)


def cond_ok(x, d):
    if x['ph'] is not None and d['ph'] is not None and abs(x['ph'] - d['ph']) > 0.3:
        return False
    if x['temp'] is not None and d['temp'] is not None and abs(x['temp'] - d['temp']) > 2.5:
        return False
    return True


def entry_id(src, comment):
    m = re.search(r'\b(?:SABIO|SKiD|STRENDA)\s+([^\s;]+)', comment or '') if src != 'UniProt' else \
        re.match(r'UniProt\s+([^\s;]+)', comment or '')  # its accession ('UniProt P35558'); OED's comment names one too
    return f'{src} {m.group(1)}' if m else ''


# ---------------------------------------------------------------- recorded causes
def _key(s):
    return re.sub(r'[^a-z0-9]', '', str(s or '').lower())


DB_NAMES = {_key(s): s for s in SOURCES} | {'sabio': 'SABIO-RK'}


METRICS = {'kcat': 'kcat', 'km': 'Km', 'kcatkm': 'kcat/Km', 'kcatoverkm': 'kcat/Km'}  # case-blind: catlog_wide spells km


def iso_date(s):
    """s is a date written YYYY-MM-DD."""
    try:
        return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', s or '')) and bool(datetime.date.fromisoformat(s))
    except ValueError:
        return False


def _corrections_text(p, problems):
    """The corrections file as text: UTF-8 (a byte-order mark allowed) or UTF-16 with its byte-order mark (Excel's
    'Unicode Text'). Another encoding (Excel's 'Tab delimited Text' writes Mac Roman or cp1252) is read with the bytes
    it cannot decode as U+FFFD; recorded() lists the rows that hold one and skips them. Never raises."""
    try:
        b = p.read_bytes()
    except OSError as e:
        problems.append((0, '', f'the file cannot be read ({e})'))
        return ''
    enc = 'utf-16' if b[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig'
    try:
        return b.decode(enc)
    except UnicodeDecodeError:
        return b.decode(enc, errors='replace')


def recorded(root=ROOT, problems=None, history=False):
    """sources/database_corrections.tsv as row_id -> [the current row per database], verdict, cause, metric and
    database normalized ('Corrected', 'catlog-wrong', 'sabio-rk', 'km', 'kcat_over_km'). Per (row_id, database) the
    latest row counts: by date, then by its place in the file (history=True: row_id -> [[its rows, newest first] per
    database], for usable(), where a row that cannot be used leaves the one before it in effect). Read as plain TSV
    (QUOTE_NONE): a field that starts with '"' is text, never the start of a quoted field that runs to the end of the
    file. A header without one of CORRECTION_COLS, and a row that cannot be used (another number of fields than the
    header, no row_id, an unknown verdict, metric or database, bytes that are not UTF-8, a database_value that is not a
    positive number where the verdict names one, a date that is not YYYY-MM-DD, a corrected row with an unknown cause,
    a cause that contradicts the verdict) is appended to `problems` as (line, row_id, why). Never raises (a file saved in another encoding, or one
    csv cannot read, would otherwise stop the export and `status`)."""
    p = Path(root) / CORRECTIONS
    problems = [] if problems is None else problems
    cands = defaultdict(list)
    if p.exists():
        line = 1
        try:  # never raises: a file export cannot read is a problem `status` lists, not a stopped export
            rd = csv.DictReader(io.StringIO(_corrections_text(p, problems), newline=''), delimiter='\t', quoting=csv.QUOTE_NONE)
            head = [(k or '').strip() for k in rd.fieldnames or []]
            problems.extend((1, '', f'no column {c!r} in the header') for c in CORRECTION_COLS if c not in head)
            for raw in rd:
                line = rd.line_num  # the physical line (the reader skips blank lines without counting them)
                r = {(k or '').strip(): (v or '').strip() for k, v in raw.items() if k and isinstance(v, str)}
                rid, verdict = r.get('row_id', ''), re.sub(r'[\s-]+', '_', r.get('verdict', '').lower())
                if not any(r.values()) and None not in raw:
                    continue
                if '\ufffd' in '\t'.join(str(v) for v in raw.values()):  # bytes another encoding wrote
                    problems.append((line, rid, 'not UTF-8: save the file as UTF-8'))
                    continue
                n = len(head) + len(raw.get(None) or []) - sum(v is None for k, v in raw.items() if k is not None)
                if n != len(head):  # a tab inside a field, or fields left out: the columns no longer line up
                    problems.append((line, rid, f'{n} fields, the header has {len(head)}'))
                    continue
                if not rid:
                    problems.append((line, '', 'no row_id'))
                    continue
                if verdict not in VERDICTS:
                    problems.append((line, rid, f"unknown verdict {r.get('verdict', '')!r}"))
                    continue
                metric = METRICS.get(_key(r.get('metric')), '' if not r.get('metric') else None)
                if metric is None:
                    problems.append((line, rid, f"unknown metric {r.get('metric', '')!r}"))
                    continue
                cause = next((c for c in CAUSES if _key(c) == _key(r.get('cause'))), '')
                if verdict == 'corrected' and not cause:  # not used: the row before it stays in effect
                    problems.append((line, rid, f"unknown cause {r.get('cause', '')!r}"))
                    continue
                if (verdict == 'corrected' and cause == 'different_measurement') or (
                        verdict == 'different_measurement' and r.get('cause') and cause != 'different_measurement'):
                    problems.append((line, rid, f"cause {r.get('cause', '')!r} contradicts verdict {verdict}"))
                    continue
                if not iso_date(r.get('date')):  # a re-check row orders by its date: '10/13/2026' < '2026-10-12'
                    problems.append((line, rid, f"date {r.get('date', '')!r} is not YYYY-MM-DD"))
                    continue
                number = _database_number(r.get('database_value'))
                if (verdict != 'different_measurement' or r.get('database_value')) and not (number and number > 0):
                    # corrected, catlog_wrong and ambiguous name a database number; another measurement may leave it out
                    problems.append((line, rid, f"database_value {r.get('database_value', '')!r} is not a positive number"))
                    continue
                names = [t for t in re.split(r'[,;+/&]|\band\b', r.get('database', '')) if t.strip()]
                dbs = [DB_NAMES.get(_key(t)) for t in names]
                if None in dbs:
                    problems.append((line, rid, f"unknown database {r.get('database', '')!r}"))
                    continue
                for db in dict.fromkeys(dbs or ['']):
                    cands[(rid, db)].append({**r, 'verdict': verdict, 'cause': cause, 'metric': metric, 'database': db,
                                             'date': r.get('date', ''), 'line': line,
                                             'number': number,
                                             'figures': _database_figures(r.get('database_value'))})
        except Exception as e:  # csv.Error and the like: the rows read so far count
            problems.append((line, '', f'the file cannot be read from here on ({type(e).__name__}: {e})'))
    out = defaultdict(list)
    for (rid, _), rows in sorted(cands.items(), key=lambda kv: max(r['line'] for r in kv[1])):
        rows = sorted(rows, key=lambda r: (r['date'], r['line']), reverse=True)
        out[rid].append(rows if history else rows[0])
    return out


def usable(root, cat, problems, db_rows=None):
    """The recorded rows (recorded()) that apply to a catalog value: row_id -> its rows, per database the newest row
    that can be used. A row whose row_id is not in the catalog, whose metric is not that value's, whose value is not
    compared (a Km or kcat/Km over a mass concentration, or no positive number), whose pmid is not that value's paper,
    that corrects a value with its own number,
    whose recorded number no row of that database, paper and metric lists (same_number()), whose cause does not
    describe its number (cause_conflict()), or that records a correction (corrected, catlog_wrong) against a database
    row labelled for another measurement (label_conflict()) is appended
    to `problems` as (line, row_id, why) and the row before it stays in effect: the export and `catlog.py status` list
    them, so a row the comparison cannot use is never dropped silently. db_rows: database_rows() of the papers
    (compare() passes its own; read from sources/db_values.tsv when left out)."""
    rows_of = {r['row_id']: r for r in cat}
    hist = recorded(root, problems, history=True)
    if db_rows is None:
        db_rows = database_rows(root, {rows_of[rid]['pmid'] for rid in hist if rid in rows_of})
    natural, vocab = natural_forms(root), {}
    out = {}
    for rid, per_db in hist.items():
        x = rows_of.get(rid)
        mine = []
        for rows in per_db:
            for r in rows:  # newest first: the first row that can be used counts
                why = _unusable(r, x, db_rows, natural, vocab)
                if not why:
                    mine.append(r)
                    break
                problems.append((r['line'], rid, why))
        if mine:
            out[rid] = sorted(mine, key=lambda r: r['line'])
    problems.sort(key=lambda z: z[0])
    return out


def _unusable(r, x, db_rows, natural, vocab):
    """Why a recorded row cannot be used for the catalog row x ('' when it can). db_rows None: no database table to
    check the recorded number against (a root without sources/db_values.tsv)."""
    if x is None:
        return 'row_id not in the catalog'
    if r.get('pmid') and r['pmid'] != x['pmid']:  # a row_id pasted from another paper's value
        return f"pmid {r['pmid']} is not this value's paper ({x['pmid']})"
    if r['metric'] and r['metric'] != x['metric']:
        return f"metric {r['metric']!r} is not this value's metric ({x['metric']})"
    if x.get('unit') in MASS_UNIT.values():
        return f"not compared: {x['metric']} printed over a mass concentration ({x['unit']})"
    if not (num(x.get('value')) or 0) > 0:
        return 'not compared: the value has no positive number'
    if r['verdict'] == 'corrected' and close(num(x['value']), r['number']):
        return f"a correction that names CatLog's own value ({r['database_value']}): the database lists the same number"
    if db_rows is not None and r['number'] is not None:
        srcs = [r['database']] if r['database'] else list(SOURCES)
        if not any(d['src'] in srcs and d['metric'] == x['metric'] and same_number(r, d['value']) for d in db_rows.get(x['pmid'], ())):
            return (f"{' or '.join(srcs) if len(srcs) < 3 else 'no database'} lists no {x['metric']} "
                    f"{r['database_value']} for paper {x['pmid']}")
    if r['verdict'] == 'corrected' and r['number'] and r['number'] > 0:
        why = cause_conflict(x, r)
        if why:
            return why
    if db_rows is not None and r['verdict'] in ('corrected', 'catlog_wrong') and r['number']:
        return label_conflict(x, r, db_rows.get(x['pmid'], ()), natural, vocab)
    return ''


def cause_conflict(x, r):
    """Why a recorded cause does not describe the recorded database number ('' when it can): paper_unit_misprint
    names the printed value read in its printed unit (relate(): printed_unit_as_printed; 25497345 had BRENDA's 0.0032,
    1,000x above 0.19 M^-1 min^-1 read as printed), time_unit a factor of 60 or 3,600 (x 10^n, TIME_N) between CatLog's
    value and it (8061001 had 55x)."""
    v, d = num(x.get('value')), r['number']
    cls = factor(v, d, x['metric'])[0]
    if r['cause'] == 'paper_unit_misprint':
        rel = relate(x['metric'], d, cls, x)[0]
        if rel != 'printed_unit_as_printed':
            return (f"cause paper_unit_misprint, but {r['database'] or 'the database'} {r['database_value']} is not the "
                    f"printed value in its printed unit ({rel.replace('_', ' ')})")
    if r['cause'] == 'time_unit' and cls != 'time_60_3600':
        return (f"cause time_unit, but CatLog's value is {v / d:.3g} times {r['database'] or 'the database'} "
                f"{r['database_value']}, not 60 or 3,600 (x 10^n)")
    return ''


NEW_TSV = 'work/dbcheck_20261012/new_to_databases.tsv'  # written by catlog.py export (paper writing)
NEW_COLS = ('pmid', 'enzyme', 'organism', 'substrate', 'variant', 'metric', 'value', 'unit', 'databases_listing_paper',
            'why', 'measurement_id')
NEW_WHY = ('paper_not_in_databases', 'metric_absent', 'substrate_absent', 'variant_absent', 'condition_absent', 'ratio_only')
FIELD = {'kcat': 'kcat', 'Km': 'km', 'kcat/Km': 'kcat_over_km'}
UNIT_PLAIN = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}


def new_to_databases(out):
    """Every value no database lists for its paper (database_check status new: no number of BRENDA, SABIO-RK, OED, SKiD,
    STRENDA or UniProt for that paper and parameter is the same, under any label, and none was paired with it), one per
    line for paper writing, with counts in '#' header lines: NEW_COLS.
    databases_listing_paper: the databases with any kcat, Km or kcat/Km row for the paper (empty: none). why:
    paper_not_in_databases; metric_absent (they list no value of this parameter for the paper), substrate_absent,
    variant_absent (none for this substrate with this variant or organism), condition_absent (they list other
    numbers for this substrate and variant); ratio_only (a printed kcat/Km whose kcat and Km they list). value in
    catalog units (unit), as exported."""
    rows = [(w, m, c) for w in out for m, c in (w.get('database_check') or {}).items() if c.get('status') == 'new']
    pmids = {str(w['pubmed_id']) for w, _, _ in rows}
    lines, by_metric, by_why, by_db, measurements = [], Counter(), Counter(), Counter(), set()
    clean = lambda x: re.sub(r'\s+', ' ', str(x if x is not None else '')).strip()
    for w, m, c in sorted(rows, key=lambda z: (str(z[0]['pubmed_id']), z[0]['measurement_id'], METRIC_ORDER.index(z[1]))):
        pmid = str(w['pubmed_id'])
        dbs = c.get('paper_sources') or []  # compare(): the databases with any row for the paper (none: not set)
        why = 'paper_not_in_databases' if c.get('paper_not_in_databases') else 'ratio_only' if c.get('ratio_only') else c.get('reason', '')
        variant = 'wild type' if w.get('wild_type') is True else w.get('mutation_signature') or ''
        lines.append('\t'.join(clean(x) for x in (pmid, w.get('enzyme_name'), w.get('organism'),
                                                    w.get('substrate_full_name') or w.get('substrate_name'), variant, m,
                                                    w.get(FIELD[m]), UNIT_PLAIN[m], ','.join(dbs), why, w['measurement_id'])))
        by_metric[m] += 1; by_why[why] += 1; measurements.add(w['measurement_id'])
        for s in dbs:
            by_db[s] += 1
    every = sum(1 for w in out if (st := [c['status'] for c in (w.get('database_check') or {}).values() if c.get('status') != 'not_compared'])
                and all(s == 'new' for s in st))
    head = [f"# CatLog values no database ({', '.join(SOURCES)}) lists for their paper: {len(lines):,} values "
            f"({', '.join(f'{m} {by_metric[m]:,}' for m in METRIC_ORDER)}) in {len(measurements):,} measurements from "
            f"{len(pmids):,} papers; {every:,} measurements have no value any database lists (written by catlog.py export)",
            '# by why: ' + ', '.join(f'{k} {by_why[k]:,}' for k in NEW_WHY if by_why[k]),
            '# by database (values from papers that database lists, without this value): '
            + ', '.join(f'{s} {by_db[s]:,}' for s in SOURCES)
            + f"; papers in none of the compared databases: {by_why['paper_not_in_databases']:,} values",
            '# UniProt: Swiss-Prot kinetics annotations (KM, kcat and kcat/KM with a PubMed reference, tools/uniprot_values.py); '
            'databases outside sources/db_values.tsv are not compared',
            '\t'.join(NEW_COLS)]
    return '\n'.join(head + lines) + '\n'


def natural_forms(root):
    """(pmid, variant) of the natural forms that older rows hold in `variant` (sources/natural_forms.tsv)."""
    nf = Path(root) / 'sources' / 'natural_forms.tsv'
    if not nf.exists():
        return set()
    return {(r['pmid'], r['variant']) for r in csv.DictReader([l for l in open(nf) if not l.startswith('#')], delimiter='\t')}


def database_rows(root, pmids):
    """pmid -> its database rows with a positive number (sources/db_values.tsv), as compare() reads them; None without
    the table."""
    out = defaultdict(list)
    dv = Path(root) / 'sources' / 'db_values.tsv'
    if not dv.exists():
        return None
    if not pmids:
        return out
    with open(dv) as fh:
        next(fh)
        for line in fh:
            f = line.rstrip('\n').split('\t')
            if len(f) >= 8 and f[1] in pmids and f[0] in SOURCES and (num(f[4]) or 0) > 0:
                out[f[1]].append({'src': f[0], 'pmid': f[1], 'metric': f[3], 'value': num(f[4]), 'vstr': f[4],
                                  'sub': f[5].strip(), 'comment': f[7]})
    return out


# ---------------------------------------------------------------- is the recorded database row this measurement?
CONC_UNIT = r'([mµuμn]?M)'
ADD_ITEM = re.compile(r'^(?:(\d+(?:\.\d+)?)\s*' + CONC_UNIT + r'\s+(?:of\s+)?)?(.+?)\s*$')
SUBSTRATE_ROLE = re.compile(r'\bas\s+(?:co-?)?substrates?\b|\bas\s+(?:electron\s+)?(?:acceptor|donor)\b', re.I)
NEGATED = re.compile(r'(?:\b(?:no|without|minus|absence of)|(?<![\d.])0\s*[mµuμn]?m)\s*$')
CONC_BEFORE = re.compile(r'(\d+(?:\.\d+)?)\s*([mµuμn]?m)\s+(?:of\s+)?$')


def _conc(v, unit):
    return float(v), unit[:-1].replace('μ', 'µ').replace('u', 'µ').lower() + 'M'


# Divalent metal ions under one name: UniProt writes 'with magnesium ions as cofactor' and 'in the presence of Mg(2+)'
# for the same ion, papers 'Mg2+' or '10 mM MgCl2' (16990279: a UniProt IMP Km 'with magnesium ions' was called
# another measurement than the paper's Mg2+ value, so its database check could not be used).
ION = {'magnesium': 'mg', 'manganese': 'mn', 'zinc': 'zn', 'cobalt': 'co', 'calcium': 'ca', 'nickel': 'ni',
       'cadmium': 'cd', 'barium': 'ba', 'strontium': 'sr'}
ION_NAME = re.compile(r'^(?:(' + '|'.join(ION) + r')(?:\s+ions?)?|(' + '|'.join(ION.values()) + r')(?:\s*\(?2\+\)?|cl2|so4))'
                      r'(?:\s+(?:ions?\s+)?as\s+(?:a\s+)?cofactor)?$')


# Monovalent cations the same way (30054521: BRENDA 'in presence of Na+' for the paper's '100 mM NaCl'); in a CatLog
# value's conditions only the ion or its chloride counts, not the element's name (potassium phosphate buffers).
ION1 = {'sodium': 'na', 'potassium': 'k', 'lithium': 'li', 'rubidium': 'rb', 'cesium': 'cs', 'caesium': 'cs',
        'ammonium': 'nh4'}
ION1_NAME = re.compile(r'^(?:(' + '|'.join(ION1) + r')(?:\s+ions?)?|(' + '|'.join(sorted(set(ION1.values()))) +
                       r')(?:\s*\(?\+\)?|cl))$')


def _additive_name(name):
    """A database additive's name, divalent metal ions as 'mg(2+)', monovalent cations as 'na(+)'."""
    m = ION_NAME.match(name)
    if m:
        return f'{ION.get(m.group(1)) or m.group(2)}(2+)'
    m = ION1_NAME.match(name)
    return f'{ION1.get(m.group(1)) or m.group(2)}(+)' if m else name


def _name_pattern(name):
    """Regex for a name in a CatLog value's conditions; an ion also as its element name or chloride/sulfate salt."""
    chunks = re.findall(r'[a-z0-9µ+]+', name)
    if not chunks:
        return None
    pat = r'\W*'.join(map(re.escape, chunks))
    sym = re.fullmatch(r'([a-z]{2})\(2\+\)', name)
    if sym and sym.group(1) in ION.values():
        el = next(k for k, v in ION.items() if v == sym.group(1))
        pat = rf'(?:{pat}|{el}|{sym.group(1)}(?:cl2|so4))'
    sym = re.fullmatch(r'([a-z0-9]{1,3})\(\+\)', name)
    if sym and sym.group(1) in ION1.values():
        pat = rf'(?:{pat}|{sym.group(1)}cl)'
    return r'(?<![a-z0-9])' + pat + r'(?![a-z0-9])'


def db_additives(comment):
    """{name: (concentration, unit) or None}: the additives and the buffer a database row's own text names ('with 300
    mM glycerol', 'in the presence of 1 mM NaF', '1,2-dimethylimidazole buffer'). A compound named 'as cosubstrate'
    is a substrate label, which the matcher compares."""
    out = {}
    comment = re.sub(r'phospahte', 'phosphate', comment or '', flags=re.I)  # BRENDA typo (2819035: 'sodium phospahte buffer')
    for seg in re.split(r',\s+|,(?=[A-Za-z])|;\s*', comment):
        seg = seg.strip()
        b = re.search(r'(\S+)\s*buffer\b', seg, re.I)
        if b and re.search(r'[a-z]{2}', b.group(1), re.I) and not re.fullmatch(r'[mµuμn]?M|same|the|this|assay', b.group(1), re.I):
            out[b.group(1).lower()] = None
            continue
        m = re.match(r'(?:with|in (?:the )?presence of)\s+(.+)', seg, re.I)
        if not m:
            continue
        for item in re.split(r'\s+and\s+|\s+plus\s+', m.group(1)):
            mm = ADD_ITEM.match(item.strip())
            if SUBSTRATE_ROLE.search(item) or not mm:
                continue
            name = _additive_name(mm.group(3).strip().lower())
            if len(name) < 2 or re.fullmatch(r'[\d\W]+', name) or re.search(r'°|\bph\b', name):
                continue
            out[name] = _conc(mm.group(1), mm.group(2)) if mm.group(1) else None
    return out


SUBMARK = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')


def unmark(text):
    """A CatLog value's conditions without a formula's subscript markup, so a database's name is found however the
    reader wrote it: 'H_2O_2', 'H_{2}O_{2}' and 'H₂O₂' are H2O2, 'MgCl_2' is MgCl2, 'P_i' and 'PP_i' are Pi and PPi
    (18373941: 'H_2O_2 fixed at 0.1 mM' did not name BRENDA's 'in the presence of 0.1 mM H2O2', which kept 4
    paper-checked corrections out twice). Only number subscripts join: a letter subscript is a constant's label, and
    joining it makes a compound of it ('K_I' is not KI, 'K_{Cl}' not KCl, 'K_O2' not KO2: 23018273, 9882445)."""
    t = re.sub(r'_\{(\d+)\}', r'\1', str(text or '').translate(SUBMARK))
    t = re.sub(r'(?<=[A-Za-z0-9)\]])_(?=\d)', '', t)
    return re.sub(r'(?<![A-Za-z0-9])(P{1,2})_i(?![A-Za-z0-9])', r'\1i', t)


def catlog_additives(text, names):
    """{name: (concentration, unit) or None} of the names a CatLog value's conditions state (as whole words, never
    negated: 'no TEA', 'without Mn2+', '0 mM NaF'), subscript markup aside (unmark())."""
    t, out = unmark(text).lower(), {}
    for name in names:
        pat = _name_pattern(name)
        if not pat:
            continue
        hits = list(re.finditer(pat, t))
        if not hits or any(NEGATED.search(t[max(0, m.start() - 30):m.start()]) for m in hits):
            continue
        c = next((CONC_BEFORE.search(t[max(0, m.start() - 30):m.start()]) for m in hits
                  if CONC_BEFORE.search(t[max(0, m.start() - 30):m.start()])), None)
        out[name] = _conc(c.group(1), c.group(2)) if c else None
    return out


def _mutant_alternatives(comment):
    """'mutant V62N and carbonic anhydrase I mutant H67N' lists two single mutants: [{V62N}, {H67N}]."""
    parts = re.split(r'\band\b', comment or '')
    return [mutset(p) for p in parts] if len(parts) > 1 and all(re.search(r'mutant', p, re.I) for p in parts) else []


def label_conflict(x, r, rows, natural, vocab):
    """'' when a database row of the recorded database, paper and metric that lists the recorded number (same_number)
    is labelled for the catalog value x: its variant fits (vok), and the additives and buffer it names equal those of
    x's conditions, names and concentrations, counting only the names that differ between that database's rows of the
    paper (a component of every row is the assay's). Else why its rows are another measurement: 28085964 recorded
    BRENDA 0.0115 'with 300 mM glycerol' for a kcat measured with 100 mM triethylamine. '' when no row lists the number
    (reported apart)."""
    srcs = [r['database']] if r['database'] else list(SOURCES)
    same = [d for d in rows if d['src'] in srcs and d['metric'] == x['metric'] and same_number(r, d['value'])]
    if not same:
        return ''
    vk, vm = catlog_variant(x, natural)
    X = {'vk': vk, 'vm': vm, 'vtext': re.sub(r'[^a-z0-9]', '', ' '.join(str(x.get(k) or '') for k in ('variant', 'enzyme', 'construct')).lower()),
         'vraw': str(x.get('variant') or '')}
    text = '; '.join(str(x.get(k) or '') for k in ('conditions', 'cosubstrate'))
    why = []
    for d in same:
        key = (x['pmid'], d['src'])
        if key not in vocab:  # the names that differ between the database's rows of the paper
            each = [db_additives(e['comment']) for e in rows if e['src'] == d['src']]
            names = set().union(*each)
            vocab[key] = {k for k in names if len({str(a[k]) if k in a else '-' for a in each}) > 1}
        dk, dm, vname, _ = db_variant(d['src'], d['comment'])
        da = {k: v for k, v in db_additives(d['comment']).items() if k in vocab[key]}
        ca = catlog_additives(text, vocab[key])
        w = []
        if not (vok(X, {'vk': dk, 'vm': dm, 'vname': vname}) or (vk == 'mut' and vm in _mutant_alternatives(d['comment']))):
            w.append(f"variant not {x.get('variant') or 'stated'}")
        w += [f'{k} there, not in this value\'s conditions' for k in sorted(set(da) - set(ca))]
        w += [f'{k} in this value\'s conditions, not there' for k in sorted(set(ca) - set(da))]
        w += [f'{k} {da[k][0]:g} {da[k][1]} there, {ca[k][0]:g} {ca[k][1]} here' for k in sorted(set(da) & set(ca))
              if da[k] and ca[k] and da[k] != ca[k]]
        if not w:
            return ''
        why.append(f"{d['src']} lists {d['vstr']} for another measurement ('{d['comment'][:90]}': {', '.join(w)})")
    return '; '.join(why[:2])


def same_number(r, v):
    """A recorded database value (r['number'], written with r['figures'] significant figures in r['database_value'])
    names the database number v: v is that number, or rounds half up to it at the recorded figures. Never the 2% of
    figures(): a database row within 2% is a neighbouring row (28085964: 0.0211 is BRENDA's 2-amino-2-methyl-1-propanol
    row, not its 0.0209 for 400 mM monoethanolamine)."""
    return r['number'] is not None and bool(v) and v > 0 and at_figures(v, r['number'], r['figures'])


def same_value(a, b):
    """Two database numbers a line prints as one (6 significant figures): 'BRENDA and OED list N' only when both list
    N, never OED's 0.009 named as SABIO-RK's 0.00906."""
    return a is not None and b is not None and f'{a:.6g}' == f'{b:.6g}'


def same_printed(a, ka, b, kb):
    """Two database numbers, written with ka and kb significant figures, are one number as printed: the one with more
    figures rounds half up to the other (OED 0.009 and BRENDA 0.00906; never 0.0211 and 0.0209)."""
    if not (a and b and a > 0 and b > 0):
        return False
    return at_figures(a, b, kb) if ka >= kb else at_figures(b, a, ka)


# ---------------------------------------------------------------- the database rows nobody reproduced: why
REPRINT = re.compile(r'reprint|data (?:taken )?from|from ref|taken from|previously (?:reported|published|determined|described|measured)|'
                     r'literature values?|from (?:our |an )?earlier|cited from|values? (?:are |were )?from (?:refs?|reference|\[)|'
                     r'reported (?:earlier|previously|elsewhere|in ref)|attributed to earlier|earlier work|'
                     r'not measured here|reported in \[|from \[\d+\]', re.I)
NUMTOK = re.compile(r'(?<![\w.])(\d+(?:\.\d+)?)(?![\d])')
SCI = re.compile(r'(\d+(?:\.\d+)?)\s*(?:[×xX✕*]|\\times)\s*10\s*(?:\^|\*\*)?\s*\(?\s*([-−–‐]?)\s*(\d{1,2})\)?')
OTHERQ = re.compile(r'\bK\s*[iId]\b|K\s*i\s*app|IC\s*50|V\s*max|K\s*0\.5|S\s*0\.5|K\s*half|inhibit|Ki\b|Kd\b|K_i|K_d|V_max', re.I)
TEXT_FACTORS = {'kcat': (1, 60, 3600), 'Km': (1, 1e3, 1e6, 1e-3), 'kcat/Km': (1, 1e3, 1e-3, 60, 6e4, 0.06)}


class _Texts:
    def __init__(self, root, papers):
        self.root, self.papers, self.notes, self.values = Path(root), papers, {}, {}

    def note(self, pmid):
        """The queue note and the reader's notes of a paper (do they say the printed values are reprinted?)."""
        if pmid not in self.notes:
            t = self.papers.get(pmid, {}).get('note', '') or ''
            for p in (self.root / 'work' / f'{pmid}.read.json', self.root / 'work' / f'{pmid}.missed.read.json'):
                try:
                    t += ' ' + str(json.loads(p.read_text()).get('note', ''))
                except (OSError, ValueError, AttributeError):
                    pass
            self.notes[pmid] = t
        return self.notes[pmid]

    def numbers(self, pmid):
        """Sorted [(value, strong, line)] of the numbers printed in the paper text (+ supplement text)."""
        if pmid not in self.values:
            vals, lines = [], []
            for p in (self.root / 'texts' / f'{pmid}.txt', self.root / 'texts' / f'{pmid}.supp.txt'):
                try:
                    lines += p.read_text(errors='replace').splitlines()
                except OSError:
                    pass
            for i, ln in enumerate(lines):
                for m in SCI.finditer(ln):
                    try:
                        vals.append((float(m.group(1)) * 10 ** ((-1 if m.group(2) else 1) * int(m.group(3))), True, i))
                    except (ValueError, OverflowError):
                        pass
                for m in NUMTOK.finditer(ln.replace(',', '')):
                    sd = sigdig(m.group(1))
                    if sd >= 2:
                        vals.append((float(m.group(1)), sd >= 3, i))
            vals.sort()
            self.values[pmid] = (vals, [v[0] for v in vals], lines)
        return self.values[pmid]

    def find(self, pmid, metric, v):
        """(strong, next to another quantity) for a number printed in the paper under the metric's unit factors;
        False when it is not there, None when the paper has no text."""
        vals, keys, lines = self.numbers(pmid)
        if not lines:
            return None
        best = None
        for f in TEXT_FACTORS[metric]:
            target = v * f
            for t, strong, i in vals[bisect.bisect_left(keys, target * 0.9):bisect.bisect_right(keys, target * 1.1)]:
                if close(t, target):
                    hit = (strong, bool(OTHERQ.search(lines[i])))
                    if best is None or (hit[0] and not best[0]):
                        best = hit
        return best or False


# ---------------------------------------------------------------- the comparison
def compare(out, cat, root=ROOT, sm=None):
    """Set w['database_check'] and w['database_note'] on every export measurement in `out` (catlog.py export) from
    the catalog rows `cat`; return the summary written to work/database_compare.json."""
    global ST
    if ST is None:
        import structures
        ST = structures
    root = Path(root)
    papers = {r['pmid']: r for r in csv.DictReader(open(root / 'papers.tsv', newline=''), delimiter='\t')}
    if sm is None:
        sm = json.loads((root / 'enrich' / 'structures.json').read_text())
    natural = natural_forms(root)
    rejected = [json.loads(l) for l in open(root / 'rejected.jsonl') if l.strip()] if (root / 'rejected.jsonl').exists() else []

    row_meas = {i: w['measurement_id'] for w in out for i in w['row_ids']}
    row_org = {i: w.get('organism') for w in out for i in w['row_ids']}  # the export's binomial ('human' -> Homo sapiens)
    wide_by_id = {w['measurement_id']: w for w in out}
    ev_of = {ev.get('row_id'): ev for w in out for ev in (w.get('evidence') or {}).values()}
    cat_papers = {r['pmid'] for r in cat}
    zero = {p for p, x in papers.items() if x.get('status') in ('done', 'needs_supplement') and p not in cat_papers}
    all_papers = cat_papers | zero

    # CatLog values
    V = []
    for r in cat:
        sk = (r.get('substrate_full_name') or r.get('substrate') or '').strip().lower()
        s = sm.get(f"{r['pmid']}|{sk}") or {}
        names = [r.get('substrate'), r.get('substrate_full_name')] + re.findall(r'\[name "([^"]+)" = ', s.get('how', ''))
        vk, vm = catlog_variant(r, natural)
        mass = r.get('unit') in MASS_UNIT.values()  # mg/mL, mL mg^-1 s^-1: the databases list mM, never compared
        V.append({'row_id': r['row_id'], 'pmid': r['pmid'], 'metric': r['metric'], 'mass': mass,
                  'value': None if mass else num(r.get('value')),
                  'figs': cell_figures(r.get('raw_value'), num(r.get('value'))),
                  'organism': row_org.get(r['row_id']) or r.get('organism', ''), 'subkey': sk,
                  'cokeys': frozenset().union(*[name_keys(c.strip()) for c in re.split(r'[;,]| and ', str(r.get('cosubstrate') or '')) if c.strip()]),
                  'keys': frozenset().union(*[name_keys(n) for n in names if n]),
                  'ns': frozenset().union(*[ns_keys(n) for n in names if n]), 'k14': key14(s.get('smiles', '')), 'vk': vk, 'vm': vm,
                  'ph': num(r.get('pH')), 'temp': num(r.get('temperature_C')), 'measurement_id': row_meas.get(r['row_id'], ''),
                  'vtext': re.sub(r'[^a-z0-9]', '', (str(r.get('variant') or '') + ' ' + str(r.get('enzyme') or '')).lower()),
                  'ctext': f"{r.get('construct') or ''} {r.get('variant') or ''}", 'vraw': str(r.get('variant') or '')})
    x_of = {x['row_id']: x for x in V}
    by = defaultdict(list)  # (pmid, metric) -> CatLog values with a positive number
    for x in V:
        if x['value'] is not None and x['value'] > 0:
            by[(x['pmid'], x['metric'])].append(x)
    paper_orgs, org_texts, paper_subs = defaultdict(set), defaultdict(set), defaultdict(dict)
    for x in V:
        if genus_species(x['organism']):
            paper_orgs[x['pmid']].add(genus_species(x['organism']))
            org_texts[x['pmid']].add(x['organism'])
        e = paper_subs[x['pmid']].setdefault(x['subkey'], {'keys': set(), 'ns': set(), 'k14': set()})
        e['keys'] |= x['keys']; e['ns'] |= x['ns']
        if x['k14']:
            e['k14'].add(x['k14'])

    # database rows of these papers
    D, sources_of = [], defaultdict(Counter)
    dv = root / 'sources' / 'db_values.tsv'
    with (open(dv) if dv.exists() else io.StringIO('\n')) as fh:  # no table yet: tools/db_values.py builds it
        next(fh)
        for i, line in enumerate(fh):
            f = line.rstrip('\n').split('\t')
            if len(f) < 8 or f[1] not in all_papers or f[0] not in SOURCES:  # a source not in SOURCES is never half used
                continue
            sources_of[f[1]][f[0]] += 1
            v = num(f[4])
            if v is None or v <= 0:
                continue
            dk, dm, vname, stated = db_variant(f[0], f[7])
            ph, t = db_conditions(f[7])
            D.append({'src': f[0], 'pmid': f[1], 'ec': f[2], 'metric': f[3], 'value': v, 'vstr': f[4], 'sub': f[5].strip(),
                      'org': f[6], 'comment': f[7], 'vk': dk, 'vm': dm, 'vname': vname, 'wt_stated': stated, 'ph': ph, 'temp': t})
    ref_by = defaultdict(list)
    for d in D:
        ref_by[(d['pmid'], d['metric'])].append(d)

    # recorded verdicts (database_corrections.tsv): per value, its metric's current rows; the rest go to problems
    problems, db_rows = [], defaultdict(list)
    for d in D:
        db_rows[d['pmid']].append(d)
    verdicts = usable(root, cat, problems, db_rows)
    rec_count = Counter(r['verdict'] for rows in verdicts.values() for r in rows)

    def other_measurement(rid, src, v, vstr):
        """A check against the paper found this database number to be another measurement of the paper: the row of
        the database it names (its number as recorded, or any when none is recorded), or another database's row with
        the same number as printed (BRENDA, OED and SKiD copy one another, OED with fewer figures)."""
        return any(r['verdict'] == 'different_measurement' and (
            (r['database'] in ('', src) and (r['number'] is None or same_number(r, v)))
            or (r['database'] != src and r['number'] is not None
                and same_printed(r['number'], r['figures'], v, printed_figures(vstr)))) for r in verdicts.get(rid, ()))

    # substrate tiers
    matched = {}

    def match_name(pmid, name, ec):
        k = (pmid, name, ec)
        if k not in matched:
            subs = paper_subs.get(pmid, {})
            if name.strip().lower() in GENERIC_DB:
                res = ('none_given', set())
            else:
                dk = name_keys(name)
                hits = {s for s, e in subs.items() if dk & e['keys']}
                res = ('name', hits) if hits else None
                if not res and subs:
                    k14 = db_struct(name, ec)
                    hits = {s for s, e in subs.items() if k14 and k14 in e['k14']}
                    res = ('structure', hits) if hits else None
                if not res and subs:
                    dn = ns_keys(name)
                    hits = {s for s, e in subs.items() if dn & e['ns']}
                    res = ('name_nostereo', hits) if hits else None
                res = res or ('unresolved', set())
            matched[k] = res
        return matched[k]

    for d in D:
        d['mtier'], d['mhits'] = match_name(d['pmid'], d['sub'], d['ec'])
    alias, votes = {}, defaultdict(Counter)  # unresolved names voted to one CatLog substrate by same-paper numbers
    for d in D:
        if d['mtier'] == 'unresolved':
            for s in {x['subkey'] for x in by.get((d['pmid'], d['metric']), []) if close_ref(x, d)}:
                votes[(d['pmid'], d['sub'])][s] += 1
    for k, c in votes.items():
        (top, n1), *rest = c.most_common()
        if n1 >= 2 and n1 > (rest[0][1] if rest else 0):
            alias[k] = top

    def tier(x, d):
        t = d['mtier']
        if t == 'none_given':
            return t
        if t in ('name', 'structure', 'name_nostereo') and x['subkey'] in d['mhits']:
            return t
        a = alias.get((d['pmid'], d['sub']))
        if t == 'unresolved' and a and x['subkey'] == a:
            return 'alias'
        if x['metric'] == 'kcat' and x['cokeys'] and name_keys(d['sub']) & x['cokeys']:
            return 'cosubstrate_kcat'  # a kcat belongs to the reaction: BRENDA may file it under the co-substrate
        return 'other' if (t != 'unresolved' or a) else 'unresolved'

    SUB_OK = ('name', 'structure', 'name_nostereo', 'cosubstrate_kcat', 'alias', 'none_given')
    RANK = {'name': 0, 'structure': 1, 'name_nostereo': 2, 'cosubstrate_kcat': 3, 'alias': 4, 'none_given': 5}

    # organisms. A database organism (each organism of an entry 'A; B', org_parts) that is none of the paper's CatLog
    # organisms is a synonym, strain or reclassified name of one (Lathyrus oleraceus for Pisum sativum beside Lathyrus
    # cicera; Giardia duodenalis for G. lamblia; BRENDA's Eshraghiella crossota where SKiD keeps Butyrivibrio crossotus):
    # it stands for the CatLog organism whose numbers its rows list (>= 2 rows, more than for any other, as an
    # unresolved substrate name does), else for the organisms of its genus that no database names, else for every
    # organism no database names (every organism when the databases name them all)
    db_parts = defaultdict(set)
    for d in D:
        if d['org'] and len(paper_orgs.get(d['pmid'], ())) > 1:
            db_parts[d['pmid']].update(org_parts(d['org']))
    is_catlog, unnamed = {}, {}
    for pmid, parts in db_parts.items():
        orgs = paper_orgs[pmid]
        for part in parts:
            is_catlog[(pmid, part)] = any(org_fits(o, part, orgs) for o in org_texts[pmid])
        unnamed[pmid] = [o for o in org_texts[pmid] if not any(org_fits(o, part, orgs) for part in parts)]
    org_votes, org_alias = defaultdict(Counter), {}
    for d in D:
        for part in (org_parts(d['org']) if d['org'] and d['pmid'] in db_parts else ()):
            if not is_catlog[(d['pmid'], part)]:
                for o in {x['organism'] for x in by.get((d['pmid'], d['metric']), [])
                          if genus_species(x['organism']) and close_ref(x, d)}:
                    org_votes[(d['pmid'], part)][o] += 1
    for k, c in org_votes.items():
        (top, n1), *rest = c.most_common()
        if n1 >= 2 and n1 > (rest[0][1] if rest else 0):
            org_alias[k] = top
    stands_for = {}

    def stands(pmid, part):
        """The CatLog organisms a database organism that is none of them can stand for."""
        if (pmid, part) not in stands_for:
            alias = org_alias.get((pmid, part))
            genus = {n.split()[0] for n in org_names(part)}
            kin = [o for o in unnamed[pmid] if genus & {n.split()[0] for q in org_parts(o) for n in org_names(q)}]
            stands_for[(pmid, part)] = [alias] if alias else kin or unnamed[pmid] or list(org_texts[pmid])
        return stands_for[(pmid, part)]

    org_fit = {}

    def org_ok(x, d):
        """The database row's organism fits the value's. A value that names no organism fits any, and so does any
        organism when the paper has one CatLog organism. Otherwise the database names x's organism (org_fits: under any
        of its names, 'hamster' as Mesocricetus auratus; one organism of an entry 'A; B'), or one of its organisms is
        none of the paper's CatLog organisms and stands for x's (stands()); another CatLog organism of the paper is
        another organism."""
        orgs = paper_orgs.get(x['pmid'], set())
        if len(orgs) <= 1 or not d['org'] or not genus_species(x['organism']):
            return True
        k = (x['pmid'], x['organism'], d['org'])
        if k not in org_fit:
            org_fit[k] = org_fits(x['organism'], d['org'], orgs) or any(
                not is_catlog[(x['pmid'], part)] and any(same_org(x['organism'], o, orgs) for o in stands(x['pmid'], part))
                for part in org_parts(d['org']))
        return org_fit[k]

    def label_kinds(x, d):
        t = tier(x, d)
        return [k for k, ok in (('substrate', t in SUB_OK), ('variant', vok(x, d)), ('organism', org_ok(x, d))) if not ok]

    for d in D:
        d['reproduced'] = any(close_ref(x, d) for x in by.get((d['pmid'], d['metric']), []))
        d['clean'], d['paired'] = False, None
    rel = defaultdict(lambda: defaultdict(lambda: {'conf': [], 'label': [], 'diff': []}))  # row_id -> source -> lists
    for key, ds in ref_by.items():  # 1: the same number under a fitting label
        for x in by.get(key, []):
            for d in ds:
                if close_ref(x, d) and not label_kinds(x, d):
                    rel[x['row_id']][d['src']]['conf'].append((d, tier(x, d)))
                    d['clean'] = True
    for key, ds in ref_by.items():  # 2: the same number under another label (rows no value matches cleanly)
        for x in by.get(key, []):
            for d in ds:
                if not d['clean'] and close_ref(x, d):
                    rel[x['row_id']][d['src']]['label'].append((d, label_kinds(x, d)))
    for key, ds in ref_by.items():  # 3: each unreproduced row paired with one compatible value
        xs = by.get(key, [])
        for d in ds:
            if d['reproduced']:
                continue
            cands = []
            for x in xs:
                t = tier(x, d)
                if t in SUB_OK and vok(x, d) and org_ok(x, d) and cond_ok(x, d):
                    cands.append((RANK[t], t, x))
            if not cands:
                continue
            best = min(c[0] for c in cands)
            cands = [(t, x) for rk, t, x in cands if rk == best]
            if d['vk'] == 'trunc':  # a deletion or truncation: the values whose construct states it first
                top = max(span_fit(x, d) for _, x in cands)
                cands = [(t, x) for t, x in cands if span_fit(x, d) == top]
            if cands[0][0] == 'none_given' and len({x['subkey'] for _, x in cands}) > 1:
                d['ambiguous_no_substrate'] = True
                continue
            fac = {x['row_id']: factor(x['value'], d['value'], d['metric']) for _, x in cands}
            ex = [(t, x) for t, x in cands if exact(fac[x['row_id']][0])]
            if ex:  # a power of ten before a time factor, then the value nearest the exact factor, then the smaller |n|
                t, x = min(ex, key=lambda c: (fac[c[1]['row_id']][0] != 'unit_10^n',) + exact_fit(c[1]['value'] / d['value'], d['metric']))
            else:
                t, x = min(cands, key=lambda c: abs(math.log10(c[1]['value'] / d['value'])))
            cls, lab = fac[x['row_id']]
            how = 'unique' if len(cands) == 1 else f'closest of {len(cands)}' + (' (exact factor)' if ex else '')
            d['paired'] = (x['row_id'], cls, lab, how, t)
            if other_measurement(x['row_id'], d['src'], d['value'], d['vstr']):  # a paper check: another measurement, left out
                d['other_measurement'] = True
                continue
            rel[x['row_id']][d['src']]['diff'].append((d, cls, lab, how, t, x['value'] / d['value']))

    def pick_diff(diffs):  # the pairing to report: exact factor, power of ten, unique, nearest the exact factor, smallest factor
        return sorted(diffs, key=lambda z: (not exact(z[1]), z[1] != 'unit_10^n', z[3] != 'unique',
                                            exact_fit(z[5], z[0]['metric']) or (0, 0), abs(math.log10(z[5]))))[0]

    def classify(x):
        rr = rel.get(x['row_id'], {})
        conf = [(s, c) for s in SOURCES for c in rr.get(s, {}).get('conf', [])]
        diff = [(s, z) for s in SOURCES for z in rr.get(s, {}).get('diff', [])]
        lab = [(s, z) for s in SOURCES for z in rr.get(s, {}).get('label', [])]
        if x['value'] is None or x['value'] <= 0:
            return {'cat': 'NO_VALUE'}
        if conf:
            return {'cat': 'CONFIRMED', 'conf': conf, 'diff': diff}
        if diff:
            return {'cat': 'DIFFERS', 'diff': diff, 'pick': pick_diff([z for _, z in diff])}
        if lab:
            return {'cat': 'SAME_NUMBER_LABEL_DIFFERS', 'label': lab}
        if not sum(sources_of[x['pmid']].values()):
            return {'cat': 'NEW_a'}
        ds = ref_by.get((x['pmid'], x['metric']), [])
        if not ds:
            reason = 'metric_absent'
        else:
            sub_ok = [d for d in ds if tier(x, d) in SUB_OK]
            reason = ('substrate_absent' if not sub_ok else 'variant_absent' if not [d for d in sub_ok if vok(x, d) and org_ok(x, d)]
                      else 'condition_absent')
        return {'cat': 'NEW_b', 'reason': reason}

    def tolerance(w):
        """catlog.py ratio_check's tolerance for the measurement (1.5x widened by the printed uncertainties)."""
        m = re.search(r'allowed ([0-9.]+)x', str(w.get('ratio_check') or ''))
        return math.log10(max(1.5, float(m.group(1)))) if m else math.log10(1.5)

    def closure(x, alt=None, plain=False):
        w = wide_by_id.get(x['measurement_id'])
        if not w or not str(w.get('kcat_over_km_source', '')).startswith('printed'):
            return None
        # CatLog read another value's unit otherwise than printed: its own triplet agrees by construction. The value's
        # own unit reading is what the closure tests (the database lists the printed unit as printed), so it is allowed.
        if not plain and any(override(ev) and not respelled(m, ev) and m != x['metric']
                             for m, ev in (w.get('evidence') or {}).items()):
            return None
        k, m, r = num(w.get('kcat')), num(w.get('km')), num(w.get('kcat_over_km'))
        if not (k and m and r):
            return None
        if alt is not None:
            k, m, r = (alt if x['metric'] == 'kcat' else k), (alt if x['metric'] == 'Km' else m), (alt if x['metric'] == 'kcat/Km' else r)
        return (k / m) / r

    def triplet(x, dval, plain=False):
        """Which number fits the paper's own printed kcat, Km and kcat/Km of the measurement (ratio_check's tolerance,
        1.5x widened by the printed uncertainties)? With the fold (>= 1) between kcat / Km and the printed kcat/Km for
        the number it supports: a line says 'matches' only within 1.5x. plain: CatLog's three numbers as they are,
        whatever unit CatLog read them in (rule A's guard: code never calls a database number wrong that closes
        CatLog's own triplet when CatLog's number does not)."""
        a, b = closure(x, plain=plain), closure(x, dval, plain=plain)
        if a is None:
            return '', None
        lim = tolerance(wide_by_id[x['measurement_id']])
        verdict = {(True, False): 'supports_catlog', (False, True): 'supports_database', (True, True): '',
                   (False, False): 'neither'}[(abs(math.log10(a)) <= lim, abs(math.log10(b)) <= lim)]
        q = {'supports_catlog': a, 'supports_database': b}.get(verdict)
        return verdict, (float(f'{10 ** abs(math.log10(q)):.3g}') if q else None)

    def number_fields(x, v, ev):
        """The fields that describe a database number v against the value x (a recorded number)."""
        cls = factor(x['value'], v, x['metric'])[0]
        relation, der = relate(x['metric'], v, cls, ev)
        return {'database_value': v, 'database_unit': UNIT[x['metric']], 'factor': float(f"{x['value'] / v:.4g}"),
                'relation': relation, 'derivation': der, **dict(zip(('closure', 'closure_fold'), triplet(x, v)))}

    def unique_others(c, skip=()):
        """Other numbers a database lists for this value alone (unique pairings) at an exact factor of CatLog's value
        (10^n, or 60 or 3,600 x 10^n): a slip of this very measurement. A number at any other factor that pairs only
        with this value is most often another measurement CatLog did not take (another effector, cosubstrate or assay:
        18022563's BRENDA 1.2 s^-1 is the Mg2+-varied kcat), so no line names it as this value's."""
        others = {}
        for s, z in c.get('diff', []):
            if s not in skip and z[3] == 'unique' and exact(z[1]) and s not in others:
                others[s] = pick_diff([y for s2, y in c['diff'] if s2 == s and y[3] == 'unique' and exact(y[1])])[0]['value']
        return others

    def phrase(d, kinds):  # "for substrate 'Dha' and Homo sapiens, with no mutation named"
        what = []
        for k in kinds:
            if k == 'substrate':
                what.append(('for', f"substrate '{d['sub']}'") if d['sub'] else ('with', 'no substrate named'))
            elif k == 'variant':
                what.append(variant_label(d))
            else:
                what.append(('for', d['org'] or 'another organism'))
        parts = [f'{w} ' + _and([t for w2, t in what if w2 == w]) for w in ('for', 'with') if any(w2 == w for w2, _ in what)]
        return ', '.join(parts)

    def x_figures(x, d):
        return figures(x['value'], d['value'], d['vstr'], x['figs'])

    def label_groups(x, entries):
        """[(label, row, kinds, databases)] for (database, (row, label kinds)) entries of rows that list x's number
        under another label: per database its row with the fewest label kinds, then the nearest figures and number;
        databases share a group only with the same label and the same number as a line names it."""
        best = {}
        for s, (d, kinds) in entries:
            k = (len(kinds), x_figures(x, d), abs(math.log10(x['value'] / d['value'])))
            if s not in best or k < best[s][0]:
                best[s] = (k, d, kinds)
        groups = {}
        for s in SOURCES:
            if s in best:
                _, d, kinds = best[s]
                groups.setdefault((phrase(d, kinds), None if x_figures(x, d) == 0 else f"{d['value']:.6g}"), []).append(s)
        order = sorted(groups.items(), key=lambda g: best[g[1][0]][0][:2] + (SOURCES.index(g[1][0]),))
        return [(lab, best[g[0]][1], best[g[0]][2], g) for (lab, _), g in order]

    checks, cats = {}, {}
    for x in V:
        c = classify(x)
        cats[x['row_id']] = c
        ev = ev_of.get(x['row_id'], {})
        e = {'status': ''}
        if c['cat'] == 'NO_VALUE':
            e['status'] = 'not_compared'
            if x['mass']:
                e['reason'] = 'mass_concentration'
        elif c['cat'] == 'CONFIRMED':
            best = {}  # per database its best confirming row: tier, then the nearest number
            for s, (d, t) in c['conf']:
                k = (RANK[t], abs(math.log10(x['value'] / d['value'])))
                if s not in best or k < best[s][0]:
                    best[s] = (k, d)
            d = min(best.values(), key=lambda z: z[0])[1]
            figs = {s: figures(x['value'], z[1]['value'], z[1]['vstr'], x['figs']) for s, z in best.items()}
            e.update(status='confirmed', sources=[s for s in SOURCES if s in best], database_value=d['value'],
                     database_entry=entry_id(d['src'], d['comment']), figures=figs[d['src']],
                     rounded={s: [best[s][1]['value'], figs[s]] for s in SOURCES if figs.get(s)},
                     same_values={s: best[s][1]['value'] for s in SOURCES if s in best and not figs.get(s)},
                     other_values=unique_others(c))
        elif c['cat'] == 'DIFFERS':
            d, cls, lab, how, t, q = c['pick']
            same = [s for s in SOURCES if any(s == s2 and same_value(z[0]['value'], d['value']) for s2, z in c['diff'])]
            near = {}  # paired within 2% of the named number but listed otherwise (OED 0.009, SABIO-RK 0.00906): its own
            for s2, z in sorted(c['diff'], key=lambda sz: SOURCES.index(sz[0])):
                if s2 not in same and s2 not in near and close(z[0]['value'], d['value']):
                    near[s2] = z[0]['value']
            ufc = override(ev)
            relation, der = relate(x['metric'], d['value'], cls, ev)
            clo, fold = triplet(x, d['value'])
            # rule A: code states a correction only when the paper's own kcat ÷ Km supports CatLog's number (an exact
            # factor alone is not enough, 2026-10-15); a unit CatLog reads otherwise than printed counts only when the
            # database lists the printed value in the printed unit (relate: printed_unit_as_printed), the reading the
            # closure then supports
            rule_a = (relation not in ('under_1.5x', 'other_factor') and how == 'unique' and clo == 'supports_catlog'
                      and (not ufc or relation == 'printed_unit_as_printed'))
            e.update(status='corrected' if rule_a else 'differs', sources=same, database_value=d['value'],
                     database_entry=entry_id(d['src'], d['comment']), factor=float(f'{q:.4g}'), relation=relation,
                     derivation=der, pairing=how, closure=clo, closure_fold=fold,
                     other_values={k: v for k, v in sorted({**unique_others(c, same + list(near)), **near}.items(),
                                                           key=lambda kv: SOURCES.index(kv[0]))})
            if rule_a:
                e['cause_by'] = 'code'
                if relation == 'printed_unit_as_printed':  # the printed unit does not fit the paper's own kcat ÷ Km
                    e['cause'] = 'paper_unit_misprint'
            c['rule'] = 'A' if rule_a else 'under_1.5x' if relation == 'under_1.5x' else (
                'B_closest_of_N' if how != 'unique' else 'B_other_factor' if relation == 'other_factor'
                else 'B_triplet' if clo in ('neither', 'supports_database')
                else 'B_unit_reading' if ufc else 'B_exact_factor_unchecked')
        elif c['cat'] == 'SAME_NUMBER_LABEL_DIFFERS':
            (label, d, kinds, srcs), *rest = label_groups(x, c['label'])
            e.update(status='same_number_other_label', sources=srcs, database_value=d['value'],
                     database_entry=entry_id(d['src'], d['comment']), figures=x_figures(x, d), database_label=label,
                     reason='+'.join(kinds),
                     other_labels=[{'sources': g, 'database_value': d2['value'], 'figures': x_figures(x, d2),
                                    'database_label': lab} for lab, d2, _, g in rest])
        elif c['cat'] == 'NEW_a':
            e.update(status='new', paper_not_in_databases=True)
        else:
            e.update(status='new', reason=c['reason'])
        if e['status'] != 'not_compared' and 'database_value' in e:
            e['database_unit'] = UNIT[x['metric']]
        e.update(printed=ev.get('raw_value', ''), printed_unit=ev.get('raw_unit', ''), where=ev.get('location', ''),
                 read_as=override(ev))
        checks[x['row_id']] = e
    # a printed kcat/Km that is new only as the ratio: its kcat and Km are both confirmed
    for w in out:
        ids = {m: ev.get('row_id') for m, ev in (w.get('evidence') or {}).items()}
        if all(m in ids for m in METRIC_ORDER) and checks.get(ids['kcat/Km'], {}).get('status') == 'new' and \
                not checks[ids['kcat/Km']].get('paper_not_in_databases') and \
                all(checks.get(ids[m], {}).get('status') == 'confirmed' for m in ('kcat', 'Km')):
            checks[ids['kcat/Km']]['ratio_only'] = True  # the line names who lists which (never 'they' for all)
            checks[ids['kcat/Km']]['ratio_sources'] = {m: [s for s in SOURCES if s in (checks[ids[m]].get('sources') or [])]
                                                       for m in ('kcat', 'Km')}

    # recorded verdicts: corrected / catlog_wrong / ambiguous decide the status; a different_measurement row was left
    # out of the comparison above and is named on the line
    audit = []
    who = lambda r: r.get('recorded_by') if r.get('recorded_by') in RECORDERS else 'paper_check'
    PAIR_FIELDS = ('sources', 'database_value', 'database_unit', 'database_entry', 'figures', 'rounded', 'same_values',
                   'factor', 'relation', 'derivation', 'pairing', 'closure', 'closure_fold', 'database_label', 'reason', 'ratio_only', 'ratio_sources',
                   'paper_not_in_databases',
                   'other_values', 'other_labels')
    for rid, rows in verdicts.items():
        e, x, c = checks[rid], x_of[rid], cats[rid]
        dms = [r for r in rows if r['verdict'] == 'different_measurement']
        if dms:  # the number the check named, else the number the matcher had paired from that database
            om = {d['src']: d['value'] for d in ref_by.get((x['pmid'], x['metric']), [])
                  if d.get('other_measurement') and d['paired'][0] == rid}  # the rows left out of the comparison
            for r in dms:
                if r['database'] and r['database'] not in om and r['number']:
                    om[r['database']] = r['number']
            e['other_measurement'] = {s: om[s] for s in SOURCES if s in om}
        verdict = next((v for v in ('catlog_wrong', 'corrected', 'ambiguous') if any(r['verdict'] == v for r in rows)), None)
        if verdict is None:
            if dms and e['status'] != 'corrected':
                e.update(cause='different_measurement', cause_by=who(dms[0]))
            continue
        if e['status'] == 'confirmed':
            continue  # the verdict was about an earlier value: the numbers agree now (15797234: an audit unitfix)
        mine = sorted((r for r in rows if r['verdict'] == verdict),
                      key=lambda r: (r['number'] is None, SOURCES.index(r['database']) if r['database'] in SOURCES else 9))
        # the database number the check named: the matcher's when it names the same database and number, else the
        # recorded one (and its relation to CatLog's value)
        keep = next((r for r in mine if (not r['database'] or r['database'] in e.get('sources', []))
                     and (r['number'] is None or same_number(r, e.get('database_value')))), None) if e.get('database_value') else None
        refs = ref_by.get((x['pmid'], x['metric']), [])
        lists = lambda s, v: any(dd['src'] == s and same_value(dd['value'], v) for dd in refs)  # s lists v as printed
        if keep is None and mine[0]['number'] and x['value']:
            r0 = mine[0]
            own = [dd['value'] for dd in refs if dd['src'] in ([r0['database']] if r0['database'] else SOURCES)
                   and same_number(r0, dd['value'])]
            v0 = min(own, key=lambda v: abs(v - r0['number'])) if own else r0['number']  # the database's own number
            for k in PAIR_FIELDS:
                e.pop(k, None)
            e.update(number_fields(x, v0, ev_of.get(rid, {})))
            e['sources'] = [s for s in SOURCES if lists(s, v0) and (
                any(r['database'] == s for r in mine) or any(s == s2 and same_value(z[0]['value'], v0) for s2, z in c.get('diff', [])))]
            near = {}  # a database paired with the value within 2% of v0 that lists it otherwise: named with its own number
            for s2, z in sorted(c.get('diff', []), key=lambda sz: SOURCES.index(sz[0])):
                if s2 not in e['sources'] and s2 not in near and close(z[0]['value'], v0):
                    near[s2] = z[0]['value']
            if near:
                e['other_values'] = near
            keep = r0
        elif keep is not None:
            e['sources'] = [s for s in SOURCES if s in e.get('sources', []) or any(
                r['database'] == s and lists(s, e['database_value']) for r in mine)]
        keep = keep or mine[0]
        e.pop('cause_by', None)
        if verdict == 'corrected':
            e.update(status='corrected', cause=keep['cause'], evidence=keep.get('evidence', ''), cause_by=who(keep))
        else:  # catlog_wrong (an audit decides: catlog.py status lists it) or ambiguous: not resolved
            e.update(status='differs', recorded=verdict)
            if verdict == 'catlog_wrong':
                audit.append(rid)

    # every database that lists the paper is named on the value's line: one the comparison above does not name gets
    # what it lists for the value's parameter (the number under another label, other numbers only, or none of it)
    unnamed_same = 0
    for x in V:
        e = checks[x['row_id']]
        if e['status'] == 'not_compared' or e.get('paper_not_in_databases'):
            continue
        e['paper_sources'] = [s for s in SOURCES if sources_of[x['pmid']][s]]
        if e['status'] == 'new':  # what each lists for the parameter: other numbers for this substrate and variant, for
            rows = ref_by.get((x['pmid'], x['metric']), [])  # the paper only, or none of the parameter
            pair = {d['src'] for d in rows if not label_kinds(x, d)}
            have = {d['src'] for d in rows}
            e.update(pair_numbers=[s for s in e['paper_sources'] if s in pair],
                     other_numbers=[s for s in e['paper_sources'] if s in have and s not in pair],
                     no_metric=[s for s in e['paper_sources'] if s not in have])
            continue
        named = set(e.get('sources') or []) | set(e.get('rounded') or {}) | set(e.get('other_values') or {}) | \
            set(e.get('other_measurement') or {}) | {s for g in e.get('other_labels') or [] for s in g['sources']}
        rows = ref_by.get((x['pmid'], x['metric']), [])
        lab, other, none = [], [], []
        for s in e['paper_sources']:
            if s in named:
                continue
            mine = [d for d in rows if d['src'] == s]
            # the same number under another label: within 2% (a number the same only to one or two figures under
            # another label is most often another value of the paper: 0.005 for another substrate beside CatLog's 0.0052)
            near = [(d, label_kinds(x, d)) for d in mine if within2(x['value'], d['value'])]
            if [z for z in near if z[1]]:
                lab += [(s, z) for z in near if z[1]]
            elif near:  # the same number under a fitting label, kept out by a recorded verdict
                unnamed_same += 1
            elif mine:
                other.append(s)
            else:
                none.append(s)
        if lab:
            e['other_labels'] = (e.get('other_labels') or []) + [
                {'sources': g, 'database_value': d['value'], 'figures': x_figures(x, d), 'database_label': lab_}
                for lab_, d, _, g in label_groups(x, lab)]
        e.update(other_numbers=other, no_metric=none)

    for w in out:
        w['database_check'] = {}
        for m, ev in (w.get('evidence') or {}).items():
            e = checks.get(ev.get('row_id'))
            if e:
                w['database_check'][m] = {k: v for k, v in e.items() if v not in ('', None, [], {}, False)}
        if 'kcat/Km' not in w['database_check'] and str(w.get('kcat_over_km_source') or '').startswith('derived'):
            w['database_check']['kcat/Km'] = {'status': 'not_compared', 'reason': 'calculated'}

    # database rows nobody reproduced: why (first that applies)
    rej_by = defaultdict(list)
    for r in rejected:
        v = None if r.get('unit') in MASS_UNIT.values() else num(r.get('value'))
        if v and v > 0:
            rej_by[(r['pmid'], r['metric'])].append(v)
    derived = defaultdict(list)
    for w in out:
        if str(w.get('kcat_over_km_source', '')).startswith('derived') and num(w.get('kcat_over_km')):
            derived[w['pubmed_id']].append(num(w['kcat_over_km']))
    texts = _Texts(root, papers)
    all_by_paper = defaultdict(list)
    for x in V:
        if x['value'] and x['value'] > 0:
            all_by_paper[x['pmid']].append(x)
    unrep = defaultdict(lambda: defaultdict(lambda: [0, set()]))  # pmid -> reason -> [rows, distinct numbers]
    for d in D:
        if d['reproduced']:
            continue
        if d.get('other_measurement'):
            why = 'another_measurement_per_paper_check'
        elif d['paired']:
            why = 'paired_with_different_number'
        elif any(close(v, d['value']) for v in rej_by.get((d['pmid'], d['metric']), [])):
            why = 'rejected_by_catlog_checks'
        elif d['metric'] == 'kcat/Km' and any(close(v, d['value']) for v in derived.get(d['pmid'], [])):
            why = 'equals_catlog_calculated_ratio'
        elif any(x['metric'] != d['metric'] and close(x['value'], d['value']) for x in all_by_paper.get(d['pmid'], [])):
            why = 'another_parameter_in_catlog'
        elif d['pmid'] in zero:
            why = 'catlog_kept_no_values_from_paper'
        elif d.get('ambiguous_no_substrate'):
            why = 'no_substrate_named_paper_has_several'
        else:
            it = texts.find(d['pmid'], d['metric'], d['value'])
            if it is None:
                why = 'no_text_on_disk'
            elif it:
                why = ('reprinted_from_other_work' if REPRINT.search(texts.note(d['pmid'])) else
                       'next_to_other_quantity' if it[1] else 'possible_catlog_miss' if it[0] else 'possible_miss_weak')
            else:
                why = 'paper_awaits_supplement' if papers.get(d['pmid'], {}).get('status') == 'needs_supplement' else 'not_in_paper_text'
        u = unrep[d['pmid']][why]
        u[0] += 1
        u[1].add((d['metric'], f"{d['value']:.3g}"))

    # errors that cover a paper: (nearly) every row a database lists for some metrics of a paper differs from CatLog's
    # value for the same measurement by one exact factor (the same power of ten, or the same time factor), at least 5
    # rows and 80%. Only values the page itself calls corrected count, each through a row paired with it alone (or
    # one a check against the paper named), so the note never claims more than the value lines do. Databases with
    # the same finding share a note.
    rec_corrected = {(rid, r['database']) for rid, rows in verdicts.items() for r in rows if r['verdict'] == 'corrected'}
    # (pmid, metrics, factor label) -> [(source, rows at the factor, rows listed, {metric: (rows at the factor, rows listed)})]
    found = defaultdict(list)
    rows_of = defaultdict(list)
    for d in D:
        rows_of[(d['pmid'], d['src'])].append(d)
    for (pmid, src), ds in rows_of.items():
        groups = defaultdict(list)
        for d in ds:
            p = d['paired']
            if not p or not exact(p[1]) or checks.get(p[0], {}).get('status') != 'corrected' or d.get('other_measurement'):
                continue
            if p[3] == 'unique' or (p[0], src) in rec_corrected:
                groups[p[2]].append(d['metric'])
        for lab, ms in groups.items():
            metrics = tuple(m for m in METRIC_ORDER if m in ms)
            total = sum(1 for d in ds if d['metric'] in metrics)
            if len(ms) < 5 or len(ms) < 0.8 * total:
                continue
            per = {m: (ms.count(m), sum(1 for d in ds if d['metric'] == m)) for m in metrics}
            found[(pmid, metrics, lab)].append((src, len(ms), total, per))
    notes, note_parts = defaultdict(list), defaultdict(list)
    for (pmid, metrics, lab), srcs in sorted(found.items()):
        srcs.sort(key=lambda z: SOURCES.index(z[0]) if z[0] in SOURCES else 9)
        what = ' and '.join(metrics) if len(metrics) < 3 else 'kcat, Km and kcat/Km'
        size, lower = _factor_text(lab)
        # the page sets the note under "Across this paper:", so it does not name the paper again; the factor as the
        # value lines write one ('1,000×'): 'SKiD lists all 6 of its kcat values 60× higher than CatLog's values.'
        tail = f"{size}× {'lower' if lower else 'higher'} than CatLog's values."
        if len(srcs) == 1:
            s_, n, total, _ = srcs[0]
            head = f'{s_} lists all {total} of its {what} values' if n == total else f'{s_} lists {n} of its {total} {what} values'
        else:
            parts = [f'{s_} ({n})' if n == total else f'{s_} ({n} of {total})' for s_, n, total, _ in srcs]
            head = (', '.join(parts[:-1]) + ' and ' + parts[-1]) + \
                (' list all their' if all(n == total for _, n, total, _ in srcs) else ' list most of their') + f' {what} values'
        notes[pmid].append(f'{head} {tail}')
        # the same note as numbers, one per database and parameter (the site's manifest: database_notes, round 9 brief C8)
        size_n = _factor(lab)[0]  # not 'factor': that is this module's function, used above in compare()
        note_parts[pmid] += [{'db': s_, 'metric': m, 'n': per[m][0], 'of': per[m][1], 'factor': size_n,
                              'direction': 'lower' if lower else 'higher'} for s_, _, _, per in srcs for m in metrics if per[m][0]]
    for w in out:
        w['database_note'] = notes.get(w['pubmed_id'], [])

    # summary (work/database_compare.json; `site build` sums it over the papers on the site)
    status = defaultdict(Counter)
    for w in out:
        for m, c in w['database_check'].items():
            status[c['status']][m] += 1
    rules = Counter(c.get('rule') for c in cats.values() if c['cat'] == 'DIFFERS')
    return {'values_by_status_metric': {k: dict(v) for k, v in sorted(status.items())},
            'values_by_category': dict(Counter(c['cat'] for c in cats.values())),
            'differs_by_rule': dict(rules), 'recorded': dict(rec_count), 'catlog_wrong': sorted(audit),
            'recorded_problems': [list(p) for p in problems],
            'papers_not_in_databases': sorted({x['pmid'] for x in V if cats[x['row_id']]['cat'] == 'NEW_a'}),
            'paper_notes': {p: n for p, n in sorted(notes.items())},
            'paper_note_parts': {p: n for p, n in sorted(note_parts.items())},
            'unreproduced': {p: {k: [n, len(s)] for k, (n, s) in sorted(r.items())} for p, r in sorted(unrep.items())},
            'database_rows': len(D), 'database_rows_reproduced': sum(d['reproduced'] for d in D),
            'unnamed_same_number': unnamed_same}


def _pow(n):
    """10^n as text for a factor: '10', '100', '1,000', then '10⁴'."""
    return f'{10 ** n:,}' if 0 < n <= 3 else '10' + str(n).translate(str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹'))


def _factor(lab):
    """(factor, database lower) for a factor label of CatLog / database ('x10^3', '/60', 'x3600 x10^-3'): the larger of
    the factor and its inverse as a number, as _factor_text writes it (1000, 60, 3.6)."""
    m = re.fullmatch(r'x10\^(-?\d+)', lab)
    if m:
        n = int(m.group(1))
        return 10 ** abs(n), n > 0
    sgn, t, n = re.fullmatch(r'([x/])(\d+)(?: x10\^(-?\d+))?', lab).groups()
    f = int(t) ** (1 if sgn == 'x' else -1) * 10.0 ** int(n or 0)
    big = max(f, 1 / f)
    L = math.log10(big)
    num_ = 10 ** round(L) if abs(L - round(L)) < 1e-9 else round(big) if big >= 100 else float(f'{big:.3g}')
    return (int(num_) if num_ == int(num_) else num_), f > 1


def _factor_text(lab):
    """('1,000', database lower) for a factor label of CatLog / database: 'x10^3', '/60', 'x3600 x10^-3'."""
    m = re.fullmatch(r'x10\^(-?\d+)', lab)
    if m:
        n = int(m.group(1))
        return _pow(abs(n)), n > 0
    sgn, t, n = re.fullmatch(r'([x/])(\d+)(?: x10\^(-?\d+))?', lab).groups()
    f = int(t) ** (1 if sgn == 'x' else -1) * 10.0 ** int(n or 0)
    big = max(f, 1 / f)
    L = math.log10(big)
    text = _pow(round(L)) if abs(L - round(L)) < 1e-9 else f'{big:,.0f}' if big >= 100 else f'{float(f"{big:.3g}"):g}'
    return text, f > 1
