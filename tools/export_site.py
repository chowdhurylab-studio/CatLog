"""Run realkcat's exporter (its build-public-static-snapshot.py, unchanged) with three changes made here (patch):

1. Speed: its text filter (static_export._publication_safe_text, 27 case-insensitive re.sub per string, about 40% of
   the export) runs only on strings that contain one of its trigger words. Every replacement pattern contains a trigger
   word (checked here before anything runs), so the output is the same bytes.
2. The kcat/Km flag (kcat_over_km_quotient_mismatch): CatLog v2 rows follow CatLog's own check of the printed kcat/Km
   against kcat ÷ Km (site_release.v2_row: kcat_over_km_agreement, not published); other rows are flagged only beyond
   1.5x, the same allowance. The exporter's 5% rule flagged kcat/Km values printed to one or two figures
   (0.002 × 10^6 M^-1 min^-1: 957 v2 and 411 old records on 2026-10-11). The 60x / 1000x unit-fold flag is unchanged.
3. CatLog v2 proof lines keep their table fields (printed, printed_line, printed_line_note, check, conversion,
   value_display, audit_date, audit_result) for the page's table of values, and the value's comparison with the enzyme databases as fixed phrases
   (database_status, database_line, database_sources, database_cause, database_evidence, database_found_by,
   database_new_reason, database_by_source; site_release.v2_row), and database_parts (the line's sentences by part)
   in the details shards only: the Full data leaves it out (the line carries the same words); strings inside
   database_parts and database_by_source get the exporter's own text cleaning, as the line does. The
   exporter drops any proof-line field it does not list. A v2 row's condition_note (site_release.condition_notes)
   and database_summary (one word for its values compared with databases: same, corrected, differs, other_label, new,
   mixed or not_compared; site_release.database_summary) and database_kinds (every kind of its values, ['same',
   'new']: the site's filter on records with a new value or a correction) reach its record, the Full data and the
   Table download (the
   site's viewer builder takes them from the Table rows); its database_note (a database difference that covers the
   paper) and database_paper_sources (the compared databases that list values from the paper; [] when none does) its
   record and the Full data.
4. Older records' proof notes publish facts only (user, 2026-10-11: no reasoning on the site): where a value is printed,
   what is printed, how it was converted and a database's own note. A sentence or ';' part that narrates the old
   pipeline's own state or checks (TALK: "the exported value is", "the catalog row holds", "quotient", "evidence only")
   goes; in the Normalized cell the conversion before such words stays ('160 / 60 = 2.67 s^-1, which the export ...').
   A part of the other cells that holds a number stays whole: a printed value is never cut. Computed floats
   (2.6666666666666665) go to 3 significant figures. SKiD's 'Raw SKiD Env: Temp=55°C, pH=8.9' reads 'SKiD: 55°C, pH 8.9'
   (no value: dropped); the few notes the old pipeline wrote itself go; other database notes stay as written. The
   Conditions 'buffer' part keeps the buffer, not the pipeline's words around it. CatLog v2 entries are untouched.
   Outside the Normalized cell a part that names the old pipeline's export, rows or reading (STRICT: 'Export tuple:',
   'not the exported 3500', 'row matched by', 'this pass's own quotient'; 605 records on 2026-10-12) goes even with
   numbers in it: its printed clauses stay, and an emptied Reported cell falls back to the printed raw value and unit.
5. Magnitude flags, every record: kcat_magnitude_needs_check above 10^8 s^-1 (catalase and carbonic anhydrases are
   measured at 1-3 x 10^7; the exporter's limit is 10^7), and km_magnitude_needs_check also below 10^-6 mM (1 nM).
6. kcat_over_km_source_mismatch: an older record whose every kcat/Km its source databases list (in s^-1 mM^-1) is
   more than 2-fold from the kcat/Km it shows (website plan P7: 1,796 records on 2026-10-12, 1,776 without a caution).
7. Review rules (user, 2026-10-12; website plan P5, D1 and D2), here so every count (manifest, README, release note)
   follows them:
   - An accepted record needs a linked paper: an accepted record without a PMID or DOI (public_trust_basis
     identity_only) is published as mathematically_inferred (the site's "Not reviewed", under "Not checked"). It keeps
     identity_only and its empty PMID and DOI (173 records on 2026-10-12).
   - A record whose every value a human reviewer approved (`checked` in --human-marks, the marks the build ships) but
     that the earlier review did not accept is published as verified with accepted_basis "human review" (134). A
     record without a linked paper stays as it was.
   The manifest's summary.distributions.accepted_basis counts the second; public_trust_basis identity_only the first.
8. source_license on records read by CatLog: "CC BY 4.0 (CatLog compilation); quoted paper text remains the
   publisher's" (the exporter writes "as published (see paper)"; website plan P6). The manifest's
   summary.distributions.source_license counts every license as published, for the README and the Guide.
9. Earlier "corrected" records publish what the earlier review changed (design spec 5G; the page said "the change is
   not recorded"): `corrections`, from the base row's corrected_fields, facts only: field, before, after (numbers for
   kcat, Km, kcat/Km, Ki, Vmax, pH and temperature; text for identifiers such as a PMID or EC number, a list as its
   items joined: 'Q5SM16, Q72GI1'), unit (as text with superscripts: 'mM⁻¹ s⁻¹'), kind (rounding: within 2%, or one
   number printed with at most 2 significant figures and the other the same rounded half up to 2, so 0.0155 -> 0.016
   is rounding and 125 -> 116 is not; magnitude: an exact power of ten; different; added, removed; replaced for a
   sequence or SMILES, whose text is not repeated; changed for other text), where (evidence_table_row through _facts,
   without the old pipeline's process words such as "decoded plain-numeral transcription" or "kinetic table evidence",
   its asset names '(asset `tables[1]`)' and code backticks; caret exponents as superscripts, '->' as '→'; dropped when
   it names a local file) and listed (the first database in sources/db_values.tsv that lists the before value for
   that paper and metric: exactly that number, else the same number by the rounding test above and nearer before than
   after, so a database that lists the corrected value is not named for the before one). Fields whose value did not
   change, the old pipeline's bookkeeping fields and kcat_range / km_range (not on the site; their change repeats
   kcat's or Km's) are left out.
10. --database-stats (site_release.database_stats, written by `site build`): the Stats figures' counts against the
   enzyme databases, as the manifest's summary.database_comparison.
11. Condition flag printed_unit_prefix_differs (website plan P1): a CatLog v2 record with a value whose printed unit
   has another concentration prefix than the unit CatLog converted with (µM printed, mM used; a power of ten printed
   in the unit that accounts for it is a table header, not a different prefix; site_release.prefix_differs). It goes
   in the record's condition_flags, so the Table download and the site's caution filter have it.
12. --publication-years (site_release.publication_years, written by `site build`; tools/publication_years.py): CatLog's
   values per publication year beside BRENDA's, as the manifest's summary.publication_years (round 16 brief section 1).

Run under realkcat's .venv (site_release.build does):

  python export_site.py <build-public-static-snapshot.py> [--human-marks marks.json] --source-checkout ... \\
      --verified-path ... --out-dir ...
"""
import json
import math
import re
import runpy
import sys
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

TRIGGER = re.compile(r'kinhub|catalog|realkcat|keenhub|agentic|critique|claim|evidence_envelope|source_record_snapshot|ralph',
                     re.I)
V2_PROOF_KEYS = {'printed', 'printed_line', 'printed_line_note', 'check', 'conversion', 'value_display', 'audit_date', 'audit_result',
                 'database_status', 'database_line', 'database_sources', 'database_cause', 'database_evidence',
                 'database_found_by', 'database_new_reason', 'database_by_source', 'database_parts'}
DETAILS_ONLY_PROOF_KEYS = {'database_parts'}  # (3.) in the details shards, not in the Full data
KCAT_LIMIT, KM_LOW = 1e8, 1e-6  # s^-1, mM (5.)
SOURCE_FOLD = 2.0  # (6.)
ACCEPTED = ('verified', 'corrected')
NOT_CHECKED = 'mathematically_inferred'  # (7.) the site's "Not reviewed": a database record without a PMID or DOI
HUMAN_BASIS = 'human review'  # (7.) accepted_basis
V2_LICENSE = "CC BY 4.0 (CatLog compilation); quoted paper text remains the publisher's"  # (8.)
CHECKED = set()  # (7.) record keys a human reviewer checked, from --human-marks
DB_STATS = {}  # (10.) from --database-stats
PUB_YEARS = {}  # (12.) from --publication-years
TALLY = {'accepted_basis': Counter(), 'source_license': Counter()}  # (7., 8.) for the manifest


# ---- 4. older records' proof notes: facts only ----
V2_METHOD = 'catlog_v2_read_and_independent_verify'  # site_release.V2_METHOD
V2_EXTRA = ('substrate_chebi', 'substrate_inchikey', 'substrate_pubchem_cid', 'smiles_source', 'taxon_id', 'organism_source',
            'ec_source', 'kcat_err', 'km_err', 'kcat_over_km_err')  # = site_release.V2_EXTRA (2026-10-27: smiles_source
# and ec_source were missing here, so the Full data and the values file had them empty although the export fills them)
TALK = re.compile(  # the old pipeline describing its own export, catalog, checks, selection and inference
    r"\bexport(?:ed|s|'s|-ready)?\b|\bcatalog(?:'s)?\b|\b(?:this|current|the)(?: \w+_\w+| catalog)? identity\b"
    r"|\bcurrent (?:kcat|km|value|row)|\bas evidence\b|\bevidence only\b|\bno ratio\b|\bstores? no\b|\bstored\b|\bstrict\b"
    r"|\bquotient\b|\bconsisten(?:t|cy)\b|\bagree(?:s|d|ment)?\b|\bcoarser\b|\bindependently fitted\b|\btolerance\b"
    r"|\brounded\b|\brounding\b|\brounds to\b|\bprecision\b|\bHALF_UP\b|\bthree decimals\b|\bdecimal places\b"
    r"|\bsignificant figures\b|\bpropos(?:ed|al)\b|\bcandidate\b|\bblocker\b|\branking_score\b|\btuple\b|\blocked\b"
    r"|\bcarried (?:here|as|across|over|forward)\b|\bcarries over\b|\btranscribed here\b|\b(?:used|quoted) here\b"
    r"|\bnot used\b|\bselected (?:row|cell|value)\b|\bthis (?:pass|batch|claim|record)\b|\bcited row\b|\bkeyed to\b"
    r"|\brow_metrics_coverage\b|\bderived_same_measurement\b|\bdeclared in\b|\bpreserved\b|\bretained separately\b"
    r"|\bcorroborates\b|\bOCR (?:quirks|text)\b|\bon-disk\b|\brenders\b|\bpresumabl|\bprobabl|\blikely\b|\bassum"
    r"|\binferr?(?:ed|ence|s)?\b|\binterpret|\bappears? to\b|\bseems?\b|\bwe\b|\btherefore\b", re.I)
CUT = re.compile(r',\s+(?:which|so|and|but|where|while)\s|,\s+(?=the\b)|\s+[-–—]{1,2}\s+')
# The old pipeline naming its own export, rows and reading (user check 2026-10-12: 605 old records still said 'Export
# tuple: kcat=2 ...', 'not the exported 3500', 'row matched by ...', 'this pass's own quotient'). Outside the Normalized
# cell such a part goes even when it holds numbers: what stays is the printed part before it (a value digit, not an
# exponent), 'Conditions: pH 7.5' from 'Export row conditions: pH 7.5', or, when nothing printed is left of the Reported
# cell, the printed raw value and unit themselves.
STRICT = re.compile(
    r"\bexport(?:ed|s|'s|-ready|-normali[sz]ed)?\b|\bcatalog(?:'s)?\b|\bthis (?:pass|batch|row|record|claim)(?:'s)?\b"
    r"|\bmatched by\b|\bdecimal-match|\bPDF (?:reader|text layer)\b|\bclaim(?:s|ed)?\b|\bfrom context\b|\bkept as typed\b"
    r"|\bprovenance\b|\bnot cited\b|\bratio source\b|\btuple\b|\bas required\b|\bnot used\b|\bused here\b|\bstored\b",
    re.I)
VALUE = re.compile(r'(?<![\^\-−⁻\w.])\d')  # a printed number, not the 1 of s^-1
BOUND = re.compile(r'\s+(?:and|so|which|but|while|where|because)\s+|\s+[-–—]{1,2}\s+')
LONG_FLOAT = re.compile(r'(?<![\d.])\d+\.\d{7,}(?!\d)')  # computed arithmetic; a printed value has fewer figures
CELLS = ('table_label', 'row_label', 'column_label', 'raw_value_unit_evidence', 'normalized_value_unit_evidence',
         'assay_condition')
OLD_NOTE = re.compile(  # database-note lines the old pipeline wrote itself (no database's own note says these)
    r"\bManual identity resolution\b|\bbatch payload\b|\bthis batch\b|\bpreserved?\b|\bsaved (?:row note|evidence)\b"
    r"|\brow-(?:level|aligned|specific)\b|\bfamily-level evidence\b|\battached memo\b|\bIndependent QA\b|\bexported tuple\b"
    r"|\bexport(?:-ready| record)\b|\bcommitted row\b|\bthis row(?:'s)?\b|\breview context only\b|\bselected row\b"
    r"|\bkinetic excerpt\b|\bexcerpt not\b", re.I)
BUFFER_LEAD = re.compile(r'Assay condition:|methods describe|Quote:|Source notes:|identity preserved\.|\| conditions?\b'
                         r'|selected row:|^buffer ')
BUFFER_WORD = re.compile(r'\d|Tris|HEPES|phosph|cacodylate|\bMES\b|MOPS|acetate|citrate|glycine|KPB|PBS|McIlvaine|TAPS|CHES'
                         r'|CAPS|EPPS|borate|Britton|bicine|tricine|PIPES|imidazole|carbonate|succinate|maleate|K(?:Cl|OH)'
                         r'|NaOH|HCl|\bTEA?\b|\bTES\b|\bTME\b|saturated|not specified', re.I)
BUFFER_TALK = re.compile(r'EZ-Fit|GraphPad|kinetics of Table|\bTable \d|evidence', re.I)


def _round(m):  # 3 significant figures, never fewer than the whole digits: 2.6666666666666665 -> 2.67, 5038.4615384 -> 5038
    v = float(m.group(0))
    if not v or len(m.group(0).replace('.', '').lstrip('0')) < 7:  # a printed 0.0000078 stays as printed
        return m.group(0)
    d = max(0, 2 - math.floor(math.log10(abs(v))))
    return f'{round(v, d):.{d}f}'


def _strict(part, label):
    """A part that names the old pipeline's export, rows or reading (STRICT): its printed facts, else ''."""
    pieces = re.split(r',\s+(?![^()]*\))|;\s+', part.rstrip(' .;'))
    if label:  # a location label: only the comma piece that narrates goes ('Wiley PDF reader, Results after Table 3')
        return ', '.join(p for p in pieces if not STRICT.search(p))
    cond = re.match(r'[^:]*\bconditions?:\s*(.+)$', part, re.I)  # 'Export row conditions: pH 7.5' -> 'Conditions: pH 7.5'
    if cond and VALUE.search(cond.group(1)) and not STRICT.search(cond.group(1)):
        return 'Conditions: ' + cond.group(1)
    kept = []
    for p in pieces:
        p = re.sub(r'^(?:and|but|while|whereas|so)\s+', '', p)
        m = STRICT.search(p)
        if m:  # the printed part before the narration: 'Km 24 +/- 5 uM normalizes to 0.024 mM and equals the exported km'
            cuts = list(BOUND.finditer(p, 0, m.start()))
            p = p[:cuts[-1].start()] if cuts else ''
        if p and VALUE.search(p) and not TALK.search(p):
            kept.append(p)
    return ', '.join(kept) + '.' if kept else ''


def _facts(text, normalized, label=False):
    """One proof cell of an old record without the old pipeline's talk; '' when nothing factual is left."""
    text = re.sub(r'\s*\([^()\d]*\)', lambda m: '' if TALK.search(m.group(0)) else m.group(0), text)  # '(evidence only)'
    text = re.sub(r'\s+with its tolerance\b', '', text)  # '(printed with its tolerance 0.35 +/- 0.03)'
    text = re.sub(r'\bcanonical(?:-order)?\s+(?=(?:variant\s+)?row\b)', '', text)  # 'canonical variant row X' -> 'variant row X'
    kept = []
    for part in re.split(r'(?<=[.;])\s+', text):
        if not normalized and STRICT.search(part):
            kept.append(_strict(part, label))
            continue
        m = TALK.search(part)
        if m:
            cuts = list(CUT.finditer(part, 0, m.start()))
            head = part[:cuts[-1].start()] if cuts else ''
            colon = part.find(':', m.end())
            if normalized or not re.search(r'\d', part):  # '160 / 60 = 2.67 s^-1, which the export carries ...'
                part = head + '.' if normalized and re.search(r'\d', head) else ''
            elif head and colon > 0:  # 'row His533Glu, which is the variant this catalog row carries: kcat = 0.26 s-1'
                part = head + part[colon:]
        kept.append(part)  # any other part with a number (a printed value) stays whole
    text = LONG_FLOAT.sub(_round, ' '.join(filter(None, kept))).strip(' ;,')
    return text if re.search(r'\w', text) else ''


def _note(line):
    """A database note of an old record: SKiD's raw label in plain words; a line the old pipeline wrote goes."""
    if m := re.match(r'Raw SKiD Env: Temp=(.*?), pH=(.*)$', line):
        t, ph = (x.strip() if re.search(r'\d', x) else '' for x in m.groups())
        said = ', '.join(filter(None, [t, f'pH {ph}' if ph else '']))
        return f'SKiD: {said}' if said else ''
    return '' if OLD_NOTE.search(line) else line


def clean_proof_lines(lines):
    """An old record's proof lines, facts only; CatLog v2 entries (they carry printed/check) unchanged."""
    out = []
    for entry in lines or []:
        if isinstance(entry, dict) and not V2_PROOF_KEYS & set(entry):
            had = any(isinstance(entry.get(k), str) and entry[k] for k in CELLS)
            reported = entry.get('raw_value_unit_evidence')
            entry = {k: _facts(v, k == 'normalized_value_unit_evidence', k in ('table_label', 'row_label'))
                     if k in CELLS and isinstance(v, str) else v for k, v in entry.items()}
            entry = {k: v for k, v in entry.items() if v != ''}
            if reported and not entry.get('raw_value_unit_evidence') and str(entry.get('raw_value') or '').strip():
                entry['raw_value_unit_evidence'] = f"{entry['raw_value']} {entry.get('raw_unit') or ''}".strip()  # as printed
            if had and not any(entry.get(k) for k in CELLS):  # nothing but the pipeline's talk
                continue
        elif isinstance(entry, str):
            entry = _note(entry)
            if not entry:
                continue
        out.append(entry)
    return out


def nested_text(se, lines):
    """(3.) The strings inside a v2 proof line's database_parts and database_by_source labels get the exporter's text
    cleaning (static_export._public_text, as every proof-line string gets), so the parts still join to the line."""
    for entry in lines:
        if not isinstance(entry, dict):
            continue
        parts = entry.get('database_parts')
        if isinstance(parts, dict):
            parts = {k: t for k, v in parts.items() if isinstance(v, str) and (t := se._public_text(v))}
            if parts:
                entry['database_parts'] = parts
            else:
                entry.pop('database_parts')
        by = entry.get('database_by_source')
        if isinstance(by, list):
            entry['database_by_source'] = [{k: se._public_text(v) if k == 'label' and isinstance(v, str) else v
                                            for k, v in e.items()} if isinstance(e, dict) else e for e in by]
    return lines


def clean_conditions(text):
    """'buffer this record. Assay condition: 50 mM potassium phosphate' -> 'buffer 50 mM potassium phosphate';
    'buffer EZ-Fit version 1.1. The', 'buffer pH carried to one decimal' go."""
    out = []
    for part in (text or '').split('; '):
        if part.startswith('buffer '):
            b = BUFFER_LEAD.split(part)[-1].strip(' ("')
            b = re.split(r'["”]?\.["”]?(?:\s|$)', b)[0].strip(' ("')
            part = f'buffer {b}' if BUFFER_WORD.search(b) and not (TALK.search(b) or BUFFER_TALK.search(b)) else ''
        if part:
            out.append(part)
    return '; '.join(out) or None


# ---- 9. earlier corrections, facts only ----
ROOT = Path(__file__).resolve().parent.parent  # catlog-v2 (sources/db_values.tsv)
# field -> metric; kcat_range and km_range are left out: the site shows neither, and their change repeats kcat's or Km's
CORR_VALUES = {'kcat': 'kcat', 'km': 'Km', 'kcat_over_km': 'kcat/Km', 'ki': '', 'vmax': '', 'kcat_unit': '', 'km_unit': '',
               'kcat_over_km_unit': '', 'ki_unit': '', 'vmax_unit': '', 'ph': '',
               'temperature_k': '', 'substrate_name': '', 'cofactor_name': '', 'enzyme_name': '', 'organism': '',
               'ec_number': '', 'uniprot_id': '', 'primary_uniprot_id': '', 'ncbi_protein_id': '', 'genbank_accession': '',
               'wild_type': '', 'mutation_signature': '', 'mutation_type': '', 'pubmed_id': '', 'doi': ''}
CORR_REPLACED = {'sequence', 'canonical_sequence', 'smiles'}
CATALOG_UNIT = {'kcat': 's^(-1)', 'Km': 'mM', 'kcat/Km': 's^(-1)*mM^(-1)'}
UNIT_TEXT = {'s^(-1)': 's⁻¹', 'mM': 'mM', 's^(-1)*mM^(-1)': 'mM⁻¹ s⁻¹'}  # site_release.UNIT_TEXT
PATHLIKE = re.compile(r'/Users/|/private/|\b(?:data|evidence_assets)/|\.(?:pdf|md|txt|xml|html|json|jpe?g|png|gif|tiff?|bmp|svg)\b',
                      re.I)
# a parenthesis that names an image file ('(official substrate-label image pmid22901898_table1_fx9.jpg)'): left out
IMAGE_PAREN = re.compile(r'\s*\([^()]*\.(?:jpe?g|png|gif|tiff?|bmp|svg)\)', re.I)
# a value the old pipeline wrote in place of one ('source-derived value lacked explicit selected-paper derivation
# evidence', 31578392): no value
OLD_VALUE = re.compile(r'\b(?:lack(?:ed|s|ing)?|evidence|derivation|source-derived|selected-paper)\b', re.I)
_DB_VALUES = {}


def _db_values():
    """(pmid, metric) -> [(database, value)] from sources/db_values.tsv (catalog units), read once."""
    if not _DB_VALUES:
        _DB_VALUES[None] = []
        p = ROOT / 'sources' / 'db_values.tsv'
        if p.exists():
            for line in open(p):
                f = line.rstrip('\n').split('\t')
                if len(f) > 4:
                    try:
                        _DB_VALUES.setdefault((f[1], f[3]), []).append((f[0], float(f[4])))
                    except ValueError:
                        pass
    return _DB_VALUES


CORR_NUMERIC = {'kcat', 'km', 'kcat_over_km', 'ki', 'vmax', 'ph', 'temperature_k'}  # identifiers (pubmed_id, ec_number, ...) stay text
# the old pipeline's own process words in a location ('decoded plain-numeral transcription', 'kinetic table evidence')
WHERE_PROCESS = re.compile(r'\bevidence\b|verified_catlog|source record|\bextraction\b|\bdecoded\b|\btranscri\w*', re.I)


def _value(field, v):
    """A changed value: a number for a numeric field (computed floats to 6 significant figures), text for anything else
    (a PMID 21149620 stays '21149620'; a list as its items joined, ['Q5SM16', 'Q72GI1'] -> 'Q5SM16, Q72GI1', never a
    Python list; a unit with superscript exponents, 's^(-1)' -> 's⁻¹', 'min(-1)' -> 'min⁻¹'); None for empty, for a
    numeric field's text and for the old pipeline's own sentence in place of a value (OLD_VALUE, WHERE_PROCESS)."""
    if isinstance(v, bool) or v is None or v == '' or v == []:
        return v if isinstance(v, bool) else None
    if isinstance(v, (list, tuple)):
        items = [str(_value(field, x)) for x in v if _value(field, x) is not None]
        return ('; ' if any(',' in x for x in items) else ', ').join(items) or None
    if field not in CORR_NUMERIC:
        t = str(v)
        if OLD_VALUE.search(t) or WHERE_PROCESS.search(t):
            return None
        return _unit_text(t) if field.endswith('_unit') else t
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None  # 'source-derived value lacked ... evidence' as a kcat/Km: no number, no value
    return float(f'{x:.6g}') if math.isfinite(x) else None


TO_SUP = str.maketrans('-−–+0123456789', '⁻⁻⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹')


def _carets(t):
    """Caret exponents as superscripts: 'min^-1' -> 'min⁻¹', 'M^{-1}' -> 'M⁻¹', 'NADP^+' -> 'NADP⁺' (a name such as
    'ADH_Tt' keeps its underscore: no subscript rule here)."""
    t = re.sub(r'\^\s*[{(]\s*([-−–+]?)\s*(\d*)\s*([-−–+]?)\s*[})]', lambda m: ''.join(m.groups()).translate(TO_SUP), t)
    t = re.sub(r'\^\s*([-−–+]?)\s?(\d+)(\+|[−–-](?![\w.]))?(?![\d.])', lambda m: ''.join(x or '' for x in m.groups()).translate(TO_SUP), t)
    return re.sub(r'\^([+−–-])', lambda m: m.group(1).translate(TO_SUP), t)


def _unit_text(u):
    """A unit as the site writes it: the catalog's units as UNIT_TEXT ('s^(-1)*mM^(-1)' -> 'mM⁻¹ s⁻¹'), any other with
    superscript exponents ('mM^-1 s^-1' -> 'mM⁻¹ s⁻¹', 'min(-1)' -> 'min⁻¹') and '*' as a space."""
    u = str(u)
    return UNIT_TEXT.get(u) or _carets(re.sub(r'(?<=[A-Za-z])\(([-−–+]?\d+)\)', r'^\1', u)).replace('*', ' ')


def _where(text):
    """Where an earlier correction was read, facts only: _facts, then the old pipeline's process words out (a ', decoded
    plain-numeral transcription' clause, a parenthesis or a ';'-part that names them), its asset names out ('(asset
    `tables[1]`)'), code quoting as quotes (`Mn2+` -> 'Mn2+'), caret exponents as superscripts, '->' as '→' and '+/-' as
    '±'."""
    t = _facts(re.sub(r'\s+', ' ', str(text or '')).strip(), False, True)
    t = re.sub(r',?\s*\bdecoded(?:\s+plain-numeral)?\s+transcription\b', '', t, flags=re.I)
    t = re.sub(r'\s*\(asset\b[^()]*\)', '', t)
    t = re.sub(r'\s*\([^()]*\)', lambda m: '' if WHERE_PROCESS.search(m.group(0)) else m.group(0), t)
    t = '; '.join(p.strip() for p in t.split(';') if p.strip() and not WHERE_PROCESS.search(p)).strip(' ,;')
    t = re.sub(r'`([^`]*)`', r"'\1'", t).replace('`', "'")
    t = re.sub(r'\^([a-z])(?![A-Za-z])', '', t)  # a footnote letter: 'Androsterone^a', 'NAD+^d'
    t = re.sub(r'\^(?=[A-Z])', '', t)  # a superscript name: 'Km^NADH' -> 'KmNADH', 'N^G,N^G-Dimethyl' -> 'NG,NG-Dimethyl'
    t = _carets(t).replace('->', '→').replace('+/-', '±')
    return t if len(t) <= 240 else t[:239].rsplit(' ', 1)[0] + ' …'


def _figs(v):
    """Significant figures of a number as written: 0.0115 3, 2.67 3, 1500 2 (an integer's trailing zeros do not count)."""
    m = (v if isinstance(v, str) else repr(float(v))).strip().lower().split('e')[0].lstrip('+-')
    m = m[:-2] if m.endswith('.0') else m
    d = re.sub(r'\D', '', m).lstrip('0')
    return len(d if '.' in m else d.rstrip('0') or d[:1]) or 1


def _half_up(v, k):
    """v rounded half up to k significant figures, on its decimal digits (0.0115 -> 0.012 at 2; Python's '.2g' gives 0.011)."""
    d = Decimal(repr(float(v)))
    return float(d.quantize(Decimal(1).scaleb(d.adjusted() - k + 1), rounding=ROUND_HALF_UP)) if d else 0.0


def _close(a, b):
    """The same number: within 2%, or one of them printed with at most 2 significant figures and the other the same
    when rounded half up to 2 (0.016 and 0.0155 are; 125 and 116, 111.429 and 105.405 are not)."""
    return abs(a - b) <= 0.02 * max(abs(a), abs(b)) or any(
        _figs(x) <= 2 and _half_up(x, 2) == _half_up(y, 2) for x, y in ((a, b), (b, a)))


def _listed(before, after, rows):
    """The database that lists an earlier correction's before value for the paper and metric (rows: [(database, value)]
    in sources/db_values.tsv order): the first with exactly that number, else the first whose number is the same by
    _close and nearer before than after. A database whose number is as near the corrected value lists that one, not the
    before value (23203077 kcat/Km 389.61 -> 383.333: BRENDA's 383; 15595850 58.89 -> 58: SABIO-RK's 58), and an exact
    number goes ahead of a 2-figure coincidence (27935959 Km 0.002124: BRENDA's 0.002124, not its 0.0021 for another
    substrate). None when no database does."""
    exact = next((s for s, v in rows if abs(v - before) <= 1e-9 * max(abs(v), abs(before))), None)
    if exact or not isinstance(after, float):
        return exact or next((s for s, v in rows if _close(before, v)), None)
    return next((s for s, v in rows if _close(before, v) and abs(v - before) < abs(v - after)), None)


def corrections(detail):
    """What the earlier review changed on a corrected record (corrected_fields), facts only (9.)."""
    out = []
    for field, d in (detail.get('corrected_fields') or {}).items():
        if not isinstance(d, dict) or (field not in CORR_VALUES and field not in CORR_REPLACED):
            continue
        old, new = d.get('old_value'), d.get('new_value')
        if old == new:
            continue
        if field in CORR_REPLACED:
            out.append({'field': field, 'kind': 'replaced'})
            continue
        o, n = _value(field, old), _value(field, new)
        if o == n:
            continue
        if isinstance(o, float) and isinstance(n, float):
            if abs(o - n) <= 1e-9 * max(abs(o), abs(n)):
                continue
            k = math.log10(n / o) if o > 0 and n > 0 else 0.5
            kind = 'rounding' if _close(o, n) else 'magnitude' if round(k) and abs(k - round(k)) <= math.log10(1.02) else 'different'
        elif o is None and n is not None:
            kind = 'added'
        elif n is None:
            kind = 'removed'
        else:
            kind = 'changed'
        item = {'field': field, 'before': o, 'after': n, 'kind': kind}
        if d.get('unit'):  # as text with superscripts: 's^(-1)*mM^(-1)' -> 'mM⁻¹ s⁻¹', 'mM^-1 s^-1' -> 'mM⁻¹ s⁻¹'
            item['unit'] = _unit_text(d['unit'])
        where = IMAGE_PAREN.sub('', str(d.get('evidence_table_row') or ''))
        if where.strip() and not PATHLIKE.search(where):
            item['where'] = _where(where)
        metric = CORR_VALUES[field]
        if metric and isinstance(o, float) and str(d.get('unit') or CATALOG_UNIT[metric]) == CATALOG_UNIT[metric]:
            pmid = str(d.get('evidence_pmid') or detail.get('pubmed_id') or '')
            item['listed'] = _listed(o, n, _db_values().get((pmid, metric), []))
        out.append({k: v for k, v in item.items() if v not in (None, '')})
    return out


def patch(se):
    for pattern, _ in se.PUBLICATION_TERM_REPLACEMENTS:
        if not TRIGGER.search(pattern.pattern):  # a new replacement without a trigger word: the shortcut would skip it
            sys.exit(f'export_site: replacement pattern {pattern.pattern!r} has no trigger word; add it to TRIGGER')
    original = se._publication_safe_text
    se._publication_safe_text = lambda value, o=original: o(value) if not isinstance(value, str) or TRIGGER.search(value) else value

    def efficiency_flags(detail, o=se._efficiency_integrity_flags):
        verdict = detail.get('kcat_over_km_agreement')  # only CatLog v2 rows carry it
        if verdict == 'agrees':
            return []
        if verdict == 'differs':
            return o(detail) or ['kcat_over_km_quotient_mismatch']
        flags = o(detail)
        if flags == ['kcat_over_km_quotient_mismatch'] and within(detail, 1.5):  # old rows: the same 1.5x CatLog
            return []                                                          # allows (5% flags plain rounding)
        return flags

    def within(detail, fold):
        try:
            k, km, r = (se._finite_number(detail.get(f)) for f in ('kcat', 'km', 'kcat_over_km'))
            fk = se._unit_factor(detail.get('kcat_unit'), se._KCAT_UNIT_FACTORS)
            fm = se._unit_factor(detail.get('km_unit'), se._KM_UNIT_FACTORS)
            fr = se._unit_factor(detail.get('kcat_over_km_unit'), se._KCAT_OVER_KM_UNIT_FACTORS)
            ratio = (r * fr) / (k * fk / (km * fm))
        except (TypeError, ZeroDivisionError):
            return False
        return 1 / fold <= ratio <= fold
    se._efficiency_integrity_flags = efficiency_flags
    se._KCAT_MAGNITUDE_LIMIT_PER_S = KCAT_LIMIT

    def condition_flags(detail, o=se._condition_flags):  # (5., 6.)
        flags = o(detail)
        km = se._canonical_value(detail.get('km'), detail.get('km_unit'), se._KM_UNIT_FACTORS)
        if km is not None and km < KM_LOW and 'km_magnitude_needs_check' not in flags:
            flags.append('km_magnitude_needs_check')
        shown = se._canonical_value(detail.get('kcat_over_km'), detail.get('kcat_over_km_unit'),
                                    se._KCAT_OVER_KM_UNIT_FACTORS)
        if shown and shown > 0:
            listed = [x['value'] for x in se._source_kcat_over_km_values(detail)
                      if x['value'] > 0 and se._canonical_efficiency_unit(x.get('unit'))]
            if listed and all(max(v / shown, shown / v) > SOURCE_FOLD for v in listed):
                flags.append('kcat_over_km_source_mismatch')
        if detail.get('printed_unit_prefix_differs'):  # (11.) site_release.v2_row
            flags.append('printed_unit_prefix_differs')
        if detail.get('kcat_over_km_implausible'):  # site_release.v2_row: reviewed against the paper (2026-11-03)
            flags.append('efficiency_implausible_as_printed')
        return flags
    se._condition_flags = condition_flags

    def detail_row(*, detail, summary, efficiency_context=None, o=se._compact_static_detail_row):  # (3., 7., 8.)
        # `summary` is the exporter's summary row: its verification_status feeds the table, the downloads and the
        # manifest's counts; public_trust_basis comes from the status given here and the record's cleaned paper IDs
        status = summary.get('verification_status')
        human = status not in ACCEPTED and bool(CHECKED & {summary.get('record_key'), summary.get('measurement_key')})
        if human:
            summary['verification_status'] = 'verified'
        row = o(detail=detail, summary=summary, efficiency_context=efficiency_context)
        if row.get('public_trust_basis') == 'identity_only':  # accepted, but no PMID or DOI: not accepted
            summary['verification_status'] = status if human else NOT_CHECKED
            if human:  # a human approval without a linked paper changes nothing
                row['public_trust_basis'] = None
        elif human:
            row['accepted_basis'] = HUMAN_BASIS
            TALLY['accepted_basis'][HUMAN_BASIS] += 1
        if str(detail.get('verification_method') or '').startswith(V2_METHOD):
            row['source_license'] = V2_LICENSE
            doi = str(detail.get('doi') or '').strip()  # the paper's DOI as the catalog holds it: the exporter's DOI
            if doi:  # regex cuts a SICI DOI at ';' and adds a lowercased copy cut at '>' to supporting_dois, so the
                for r in (row, summary):  # site counted one paper twice (2026-10-15: NP9811D5AB, 3,104 papers for 3,103)
                    if 'doi' in r:
                        r['doi'] = doi
                    if 'supporting_dois' in r:
                        r['supporting_dois'] = [doi]
            db_note = se._public_field_text(detail.get('database_note'))  # (3.)
            if db_note:
                row['database_note'] = db_note
            if detail.get('database_summary'):  # (3.) the record, and the summary the Table download is copied from
                row['database_summary'] = summary['database_summary'] = detail['database_summary']
            if detail.get('database_kinds'):  # (3.) likewise: every kind of its values (the site's filter: has a new value)
                row['database_kinds'] = summary['database_kinds'] = list(detail['database_kinds'])
            if isinstance(detail.get('database_paper_sources'), list):  # (3.) the record only; [] = the paper is in none
                row['database_paper_sources'] = [str(s) for s in detail['database_paper_sources']]
            for f in V2_EXTRA:  # (3.) IDs and printed errors (site_release.V2_EXTRA): the record only. Never the Table
                if detail.get(f) not in (None, ''):  # download: the frozen site's viewer-index builder needs one schema for
                    row[f] = detail[f]  # every table row (2026-10-27: 'source schema changed', extra kcat_err, km_err)
        elif detail.get('verification_status') == 'corrected' and detail.get('corrected_fields'):  # (9.)
            changed = corrections(detail)
            if changed:
                row['corrections'] = changed
        TALLY['source_license'][row.get('source_license') or ''] += 1
        note = se._public_field_text(detail.get('condition_note'))
        if note:  # the record, and the summary the Table download and the viewer records are copied from
            row['condition_note'] = summary['condition_note'] = note
        return row
    se._compact_static_detail_row = detail_row

    def public_summary(summary, o=se._public_summary):  # (7., 8.) the wrapper's counts, next to the exporter's
        out = o(summary)
        for key, tally in TALLY.items():
            out['distributions'][key] = [{'label': k, 'count': n} for k, n in sorted(tally.items(), key=lambda x: (-x[1], x[0]))]
        if DB_STATS:  # (10.)
            out['database_comparison'] = DB_STATS
        if PUB_YEARS:  # (12.)
            out['publication_years'] = PUB_YEARS
        return out
    se._public_summary = public_summary
    se._PUBLIC_PROOF_KEYS = se._PUBLIC_PROOF_KEYS | V2_PROOF_KEYS
    se._public_proof_lines = lambda raw, o=se._public_proof_lines: nested_text(se, o(clean_proof_lines(raw)))

    def enriched_row(*, table_row, detail_row, o=se._enriched_public_row):  # (3.) the Full data: no database_parts
        row = o(table_row=table_row, detail_row=detail_row)
        lines = row.get('proof_lines')
        if isinstance(lines, list) and any(isinstance(e, dict) and DETAILS_ONLY_PROOF_KEYS & set(e) for e in lines):
            row['proof_lines'] = [{k: v for k, v in e.items() if k not in DETAILS_ONLY_PROOF_KEYS} if isinstance(e, dict)
                                  else e for e in lines]  # a new list: the details shard keeps its own
        return row
    se._enriched_public_row = enriched_row
    conditions = se._public_assay_conditions_summary  # the record's Conditions line (4.); v2 rows as they are
    se._public_assay_conditions_summary = lambda detail, o=conditions, **kw: (
        o(detail, **kw) if str(detail.get('verification_method') or '').startswith(V2_METHOD)
        else clean_conditions(o(detail, **kw)))


if __name__ == '__main__':
    script, argv = sys.argv[1], sys.argv[2:]
    if '--human-marks' in argv:  # (7.) the marks the build ships (site_build/marks.json); not an exporter option
        i = argv.index('--human-marks')
        marks = json.load(open(argv[i + 1]))['marks']
        CHECKED.update(k for k, v in marks.items() if v.get('checked'))
        del argv[i:i + 2]
    if '--database-stats' in argv:  # (10.) site_release.database_stats; not an exporter option
        i = argv.index('--database-stats')
        DB_STATS.update(json.load(open(argv[i + 1])))
        del argv[i:i + 2]
    if '--publication-years' in argv:  # (12.) site_release.publication_years; not an exporter option
        i = argv.index('--publication-years')
        PUB_YEARS.update(json.load(open(argv[i + 1])))
        del argv[i:i + 2]
    sys.path.insert(0, argv[argv.index('--source-checkout') + 1])
    import realkcat.ui.static_export as se  # noqa: E402
    patch(se)
    sys.argv = [script, *argv]
    runpy.run_path(script, run_name='__main__')
