"""The CatLog website (https://catlog.structf.studio), fed with CatLog v2: built here and staged into the plain folder
site_build/release from the site files in cloudflare/site_base; cloudflare/publish.py makes it live.

  python3 catlog.py site status     what is live, what is staged and not live yet, papers not on the site yet
  python3 catlog.py site update     build, then stage (what "update the website" means; nothing public)
  python3 catlog.py site build      merged catalog -> the existing exporter -> a bundle in site_build/ (nothing public)
  python3 catlog.py site stage      a fresh site_build/release from cloudflare/site_base, the October 7 staging steps and
                                    the site's own checks (nothing public); --note FILE: the release note's site changes
                                    as the visitor bullets in FILE (update takes it too)
  python3 catlog.py site publish    retired with the GitHub copy (2026-10-31): python3 cloudflare/publish.py publishes

What the site shows: the certified October 7 snapshot of the old catalog (realkcat data/verified_catlog.jsonl,
159,446 records), except that every paper CatLog v2 has finished (papers.tsv status `done`) is shown from v2: that
paper's old rows (by the first public PMID, as the exporter attributes them) are replaced by v2's measurements.
Everything else is the existing machinery: realkcat's exporter (build-public-static-snapshot.py, run with realkcat's
.venv, read-only), the site's scripts (viewer index, follow-up summary, alias sync, publish check, tests) and the
release steps of PR #115 (realkcat/.realkcat/dry_runs/r13_release_preparation_20261007/prepare_release.py).
Published per value, as the check trail: where it is printed, the printed value, a short printed excerpt (at most
240 characters, only when code found it in the paper text), whether a second, separate AI check confirmed it or which
fields it corrected, the value in catalog units (to the significant figures the paper printed) and whether code
converted it, and a page-image reading; how it compares with the enzyme databases for the same paper, in fixed phrases
(database_status, database_line, database_sources, database_by_source; for a correction database_cause and
database_found_by, and with a recorded cause database_evidence; for a value no compared database lists
database_new_reason; in the site's detail files database_parts, the line's sentences by part; per record database_note
and database_paper_sources; counts in the manifest's summary.database_comparison; one row per value and database in
the comparison download, data/catlog-database-comparison.<id>.csv.gz, manifest database_comparison_download). CatLog's
values per publication year beside BRENDA's: the manifest's summary.publication_years (tools/publication_years.py: the
values of the papers shown from v2, as above, dated by the snapshot's day). Never published: reader/verifier reasoning,
verify notes, the raw numeric db_check and the rest of database_check, lookup traces, file paths.
"""
import csv, fcntl, gzip, hashlib, importlib.util, io, json, math, os, re, shutil, subprocess, sys, textwrap, time, urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from release_tree import release_tree  # the staged folder's fingerprint (cloudflare/stage.py and publish.py check it)

ROOT = Path(__file__).resolve().parent.parent
OLD = Path(os.environ.get('REALKCAT_DIR') or ROOT / 'realkcat')  # the earlier CatLog system: the website build needs it (README: settings)
BASE = OLD / 'data' / 'verified_catlog.jsonl'  # the certified October 7 checkpoint (5.4 GB: streamed, never loaded)
RELEASE = OLD / '.realkcat' / 'dry_runs' / 'r13_release_preparation_20261007'
EXPORTER = OLD / '.agents' / 'realkcat' / 'build-public-static-snapshot.py'
# The site files `site stage` uses (the page, its assets, the build scripts and tests), tracked here; an edit there is a
# site change. Copied byte for byte (2026-11-03) from SITE_BASE, the last lab-repo main commit with CatLog's site files
# (the lab's GitHub keeps only a pointer page since 2026-10-31); the 6.2 GB clone that held them is gone.
BASE_DIR = ROOT / 'cloudflare' / 'site_base'
SITE_BASE = '29d600d26c06795c5fce681c01223e239b760f30'  # provenance only
BUILD = ROOT / 'site_build'
RELEASE_DIR = BUILD / 'release'  # what `site stage` makes and cloudflare/stage.py reads (rebuilt whole each time)
STAGE_LOCK = BUILD / 'stage.lock'  # held by `site stage` and cloudflare/publish.py: one of them at a time
LIVE = 'https://catlog.structf.studio'
SIZE_LIMIT = 1_000_000_000  # the size gate scripts/check-catlog-publish.py keeps from the GitHub Pages days
QUALIFIER = ((re.compile(r'^(apparent|app\b)', re.I), 'apparent'), (re.compile(r'^hill fit', re.I), 'Hill fit'),
             (re.compile(r'^(paper-declared )?approximate', re.I), 'approximate'), (re.compile(r'^estimated', re.I), 'estimated'),
             (re.compile(r'^(calculated|derived) from', re.I), 'calculated'))  # a reader note's leading word -> a fixed
HILL_N = re.compile(r'\b(?:n|h|nH|n_H)\s*=\s*(\d+(?:\.\d+)?(?:\s*±\s*\d+(?:\.\d+)?)?)')  # label; the note itself is never published
METRIC_FIELD = {'kcat': ('kcat', 's^(-1)'), 'Km': ('km', 'mM'), 'kcat/Km': ('kcat_over_km', 's^(-1)*mM^(-1)')}
OLIGO = r'(?:subunit|monomer|dimer|trimer|tetramer|hexamer|octamer|dodecamer|oligomer)s?'
PER = re.compile(r'\bper\b[^;]{0,30}?\b(?:' + OLIGO + r'|active sites?|heme|FAD)\b|half-of-the-sites|\bbasis\b|'
                 r'\b(?:for|assuming)\b[^;]{0,40}\b(?:monomers?|subunits?)\b', re.I)
BASIS = ((re.compile(r'not stated', re.I), 'the paper does not say per subunit or per oligomer'),
         (re.compile(r'active[- ]site', re.I), 'per active site'), (re.compile(r'\bheme\b', re.I), 'per heme'),
         (re.compile(r'\bFAD\b'), 'per FAD'), (re.compile(r'\b(subunit|monomer)s?\b', re.I), 'per subunit'),
         (re.compile(r'\b(dimer|trimer|tetramer|hexamer|octamer|dodecamer|oligomer)s?\b', re.I), 'per {}'))
SUBSTITUTION = re.compile(r'[A-Z]\d{1,4}[A-Z]')
LOCAL_FILE = re.compile(rb'[\w.-]*(?:_text\.txt|_jats\.xml|_pmc_article\.html|_asm_pdf\.pdf|_viewer_download\.pdf)'
                        rb'(?:,? (?:text )?lines \d+(?:-\d+)?)?')  # 'pmid_16778015_pmc_html_text.txt lines 313-337'
LOCAL_HINT = (b'_text.txt', b'_jats.xml', b'_pmc_article.html', b'_asm_pdf.pdf', b'_viewer_download.pdf')  # every LOCAL_FILE match holds one: a cheap pre-test (the regex alone took 7 min per build)
V2_METHOD = 'catlog_v2_read_and_independent_verify'  # the site's review note keys on it (assets/catlog-static.js)


def basis(segments):
    """What a kcat is counted per, as one fixed label (the reader's note itself is reasoning and never published)."""
    for s in segments:
        hit = next(((pat.search(s), label) for pat, label in BASIS if pat.search(s)), None) if PER.search(s) else None
        if hit:
            return hit[1].format(hit[0].group(1).lower() if hit[0].groups() else '')
    return ''


def qualifiers(segments):
    """A reader note's per-value qualifiers as fixed labels ('apparent', 'Hill fit, n = 1.9', 'calculated from Vmax')."""
    out = []
    for s in segments:
        s = re.sub(r'^(kcat/K[mM]|kcat|K[mM])\s+', '', s)  # 'kcat Hill fit, h = 1.9 (...)'
        label = next((label for pat, label in QUALIFIER if pat.match(s)), '')
        if label == 'Hill fit' and HILL_N.search(s):
            label += f', n = {HILL_N.search(s).group(1)}'
        elif label == 'calculated':
            label = 'calculated from Vmax' if re.search(r'\bV_?max\b', s, re.I) else 'calculated from the enzyme concentration'
        if label and label not in out:
            out.append(label)
    return out


def _qualified(metric, label):
    """A per-value qualifier as one short phrase with its metric: 'apparent Km', 'kcat from a Hill fit, n = 1.9',
    'kcat per active site', 'kcat calculated from Vmax', 'kcat: the paper does not say per subunit or per oligomer'."""
    if label in ('apparent', 'approximate', 'estimated'):
        return f'{label} {metric}'
    if label.startswith('Hill fit'):
        return f'{metric} from a {label}'
    return f'{metric} {label}' if label.startswith(('per ', 'calculated')) else f'{metric}: {label}'


def _labels(metric, note):
    """A reader note's qualifiers as published, one phrase each naming its metric."""
    segs = [s.strip() for s in re.split(r';(?![^()]*\))', note or '')]  # ';' inside parentheses is not a break
    q = qualifiers(segs) + ([basis(segs)] if metric == 'kcat' and basis(segs) else [])
    return [_qualified(metric, label) for label in q]


def mutation_type(signature, wt):
    """The catalog's own mutation_type words (realkcat classify_mutation_type): point changes, else the kind of change."""
    if wt:
        return 'wild_type'
    tokens = []
    for t in re.split(r'[/,+\s]+', signature or ''):  # 'βR265A', 'D295A-α' (subunit tags), 'G32R-R42G' (hyphen-joined)
        bits = [re.sub(r'^[αβγδ]|^[αβγδ]$', '', b) for b in t.split('-')]
        bits = [b for b in bits if b]
        tokens += bits if bits and all(SUBSTITUTION.fullmatch(b) for b in bits) else [t] if t else []
    if tokens and all(SUBSTITUTION.fullmatch(t) for t in tokens):
        return 'substitution' if len(tokens) == 1 else 'multi_substitution'
    low = (signature or '').lower()
    if 'trunc' in low:
        return 'truncation'
    if re.search(r'[Δ∆]|\bdel', signature or '', re.I):
        return 'deletion'
    if re.search(r'\bins', low):
        return 'insertion'
    return 'variant_unspecified'  # chimeras, insertion variants, natural forms the paper names (NDM-1, msXR)


def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.file_digest(fh, 'sha256').hexdigest()


def run(cmd, cwd=None, check=True, capture=False, env=None):
    print('  $', ' '.join(map(str, cmd)))
    r = subprocess.run(list(map(str, cmd)), cwd=cwd, text=True, capture_output=capture, env=env)
    if check and r.returncode:
        sys.exit(f'failed ({r.returncode}): {" ".join(map(str, cmd))}\n{(r.stdout or "")[-2000:]}{(r.stderr or "")[-2000:]}')
    return r


def base_signature():
    """The base must still be the certified October 7 file the live site was built from."""
    if not (RELEASE / 'checkpoint.json').exists():
        sys.exit(f'the website build needs the earlier CatLog system: set REALKCAT_DIR to its folder '
                 f'({RELEASE} is missing)')
    want = json.loads((RELEASE / 'checkpoint.json').read_text())['after']
    st = BASE.stat()  # the device number is not compared: macOS renumbers volumes at boot (2026-10-09 restart)
    have = {'inode': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns}
    if have != {k: v for k, v in want['signature'].items() if k != 'device'}:
        sys.exit(f'{BASE} is not the certified October 7 file any more ({have} vs {want["signature"]}); '
                 'the old catalog changed: decide with the user which base to use before building')
    return want


def _exporter_helpers():
    """The exporter's own way to say which paper a row belongs to (its first public PMID)."""
    sys.path.insert(0, str(OLD))
    from realkcat.ui.static_export import _public_pmids
    from realkcat.pipeline.literature_ids import extract_literature_ids
    return lambda row: (_public_pmids(row.get('pubmed_id'), row.get('supporting_pmids'),
                                      extract_literature_ids(row, include_nested=True).get('pmids')) or [None])[0]


SABIO_N = re.compile(r'(?:(?<=^)|(?<=[ ;]))n(?: n)*(?=[ ;]|$) ?')  # SABIO-RK's stoichiometry 'n' tokens, kept by the old import


def _clean_substrate(name):
    """A base row's substrate list as a visitor reads it: SABIO-RK's bare 'n' tokens out, a reactant listed again once."""
    parts = [p.strip() for p in SABIO_N.sub('', name).split(';')]
    return '; '.join(dict.fromkeys(p for p in parts if p))


# A base row's kcat, Km and kcat/Km in the catalog units the site shows (2026-11-06 Stats audit CV7: 5 accepted earlier
# records held 8 values in other units, which Browse counted as values and Stats, reading catalog units only, did not):
# (field, tools/units.py metric, the unit written, the unit keys that already are it: the Stats builder's unit_key).
BASE_METRICS = (('kcat', 'kcat', 's^(-1)', {'s-1'}), ('km', 'Km', 'mM', {'mm'}),
                ('kcat_over_km', 'kcat/Km', 's^(-1)*mM^(-1)', {'s-1mm-1', 'mm-1s-1'}))


def _base_unit_key(unit):
    text = str(unit or '').strip().lower().replace('−', '-')
    return re.sub(r'[\s()*^·]', '', re.sub(r'liters?', 'l', text))


def _base_units(row):
    """A base row's values in the catalog units, in place; True when it changed one. A value in another time or
    concentration unit is converted by tools/units.py, to its printed figures (_printed: 307.3 min^-1 is 5.122 s^-1),
    with its range; a Km over a mass concentration and its kcat/Km leave the record (CLAUDE.md: never in the mM fields,
    not on the site); an accepted record's value with no unit is left out (a number confirmed against the paper is shown
    with its unit; the other records keep theirs, with the caution No unit given). A unit units.py cannot read stays."""
    import units  # tools/units.py, beside this file
    accepted = row.get('verification_status') in ('verified', 'corrected')
    changed = False
    for field, metric, unit, keys in BASE_METRICS:
        value = row.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        raw = row.get(f'{field}_unit')
        if _base_unit_key(raw) in keys:
            continue
        if not str(raw or '').strip():
            if accepted:
                row[field] = None
                row.pop(f'{field}_range', None)
                changed = True
            continue
        converted, to, error = units.normalize(metric, repr(float(value)), raw)
        if error or to not in (units.MASS_UNIT.get(metric), 's^-1', 'mM', 'mM^-1 s^-1'):
            continue
        if to == units.MASS_UNIT.get(metric):
            row[field] = None
            for name in (f'{field}_range', f'{field}_unit'):
                row.pop(name, None)
        else:
            row[field] = _printed(converted, repr(float(value)))[0]
            span = row.get(f'{field}_range')
            if isinstance(span, list) and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in span):
                row[f'{field}_range'] = [_printed(units.normalize(metric, repr(float(x)), raw)[0], repr(float(x)))[0] for x in span]
            row[f'{field}_unit'] = unit
        changed = True
    return changed


def _merge():
    """Base minus the rows of v2's finished papers and the rows with no kcat, Km or kcat/Km (placeholder rows of the old
    database import: a record holds up to three of those values, 2026-11-03), plus v2's rows. A base row's values go out
    in the catalog units (_base_units), and one left with none of the three is left out too. Runs under realkcat's .venv
    (see build)."""
    papers = set(json.loads((BUILD / 'v2_papers.json').read_text()))
    first_pmid = _exporter_helpers()
    want = {p.encode() for p in papers}
    kept = dropped = dropped_accepted = empty = empty_accepted = 0
    with open(BASE, 'rb') as src, open(BUILD / 'merged' / 'verified_catlog.jsonl', 'wb') as out:
        for line in src:
            if want and want.intersection(re.findall(rb'\d+', line)):
                row = json.loads(line)
                if first_pmid(row) in papers:  # the site shows this paper from v2 now
                    dropped += 1
                    dropped_accepted += row.get('verification_status') in ('verified', 'corrected')
                    continue
            if any(h in line for h in LOCAL_HINT) and LOCAL_FILE.search(line):  # a few old rows name a local file: not published
                line = LOCAL_FILE.sub(b'(saved paper text)', line)
            row = json.loads(line)
            rewrite = _base_units(row)
            if all(row.get(k) in (None, '') for k in ('kcat', 'km', 'kcat_over_km')):
                empty += 1
                empty_accepted += row.get('verification_status') in ('verified', 'corrected')
                continue
            name = row.get('substrate_name')
            if isinstance(name, str) and ';' in name and _clean_substrate(name) != name:
                row['substrate_name'] = _clean_substrate(name)
                rewrite = True
            if rewrite:
                line = (json.dumps(row, ensure_ascii=False) + '\n').encode()
            if b'"data_origin": "growth' in line or OLD_PIPELINE_SENTENCE in line:  # old pipeline wording: not published
                line = INTERNAL_ORIGIN.sub(b'"data_origin": "experimental"', line)
                line = line.replace(OLD_PIPELINE_SENTENCE, b'the printed kcat/Km is kept as evidence only.')
            out.write(line); kept += 1
        with open(BUILD / 'v2_rows.jsonl', 'rb') as v2:
            shutil.copyfileobj(v2, out)
    print(json.dumps([kept, dropped, dropped_accepted, empty, empty_accepted]))


def _canonical(acc):
    from sequences import sequence  # tools/sequences.py: the same lookup the export uses
    try:
        return sequence(acc) if acc else ''
    except Exception:
        return ''


NOT_PRINTED = re.compile(r'\b(pH|temperature_C) (?:\S+|"[^"]*") is (not printed in the paper|not a number): left empty')
# what the second AI check corrected, as the new state in plain words; a field with no phrase here is not named
CORR_NAME = {'unit_for_conversion': 'unit', 'raw_value': 'printed value', 'raw_unit': 'printed unit', 'ec': 'EC',
             'pH': 'pH', 'temperature_C': 'temperature', 'variant': 'variant', 'organism': 'organism'}  # short values: named
CORR_PHRASE = {'construct': 'construct description corrected (see Preparation)',
               'conditions': 'assay conditions corrected (see Conditions)', 'protein_ids': 'protein IDs corrected',
               'substrate': 'substrate name corrected', 'substrate_full_name': 'substrate name corrected',
               'cosubstrate': 'cosubstrate corrected', 'location': 'location in the paper corrected',
               'quote': 'location in the paper corrected'}


def _short(x):
    x = '' if x is None else str(x).strip()
    return x if len(x) <= 30 else x[:29] + '…'


def _fixed(field, v, metric):
    """One field the second AI check corrected, as the new state: 'unit set to mM', 'printed unit corrected to µM',
    'EC 2.7.2.12 removed', 'pH left blank', 'qualifier corrected to apparent Km'; '' when nothing shown changed."""
    old, new = _short(v.get('reader')), _short(v.get('verifier'))
    if field == 'metric_note':  # the note is never published, only the qualifier read from it
        before, after = _labels(metric, v.get('reader')), _labels(metric, v.get('verifier'))
        return '' if before == after else f"qualifier corrected to {', '.join(after)}" if after else 'qualifier removed'
    if field not in CORR_NAME:
        return CORR_PHRASE.get(field, '')
    name = CORR_NAME[field]
    new += ' °C' if new and field == 'temperature_C' else ''
    if not new:
        return f'{name} left blank' if field in ('pH', 'temperature_C') else f'EC {old} removed' if field == 'ec' else f'{name} removed'
    return f'{name} set to {new}' if not old else f'{name} corrected to {new}'


def _unit_reading(corr, ev, metric):
    """The second AI check's reading of a printed unit as one phrase, when it set unit_for_conversion to another unit
    than the printed one: 'printed unit read as 10⁶ M⁻¹ min⁻¹'. The printed unit itself is the value's `printed` field,
    so a raw_unit correction in the same check is absorbed (never 'printed unit corrected to' a misprint; the user,
    2026-10-15). One phrase, no ';' (the page splits a check at ';') and starting 'printed unit', so the page counts it
    as the value's own check, not a change to the record (round 14: "the paper prints 'μM'; read as mM" read "The AI
    check also the paper prints 'μM' and read as mM."). It never calls the printed unit a misprint: code cannot tell one
    ('M · min⁻¹') from a header scale ('10⁴ × (k3)ss (s⁻¹)' read as 10⁻⁴ s⁻¹) or small capitals ('min⁻¹ μm⁻¹' read as
    µM⁻¹), 941 such notes on 2026-10-15; a database line says when the paper's own kcat ÷ Km supports the reading. ''
    when the check set no such unit."""
    new = str((corr.get('unit_for_conversion') or {}).get('verifier') or '').strip()
    printed = str((corr.get('raw_unit') or {}).get('verifier') or ev.get('raw_unit') or '').strip()
    if not new or not printed or _unit_key(new) == _unit_key(printed):
        return ''
    return f'printed unit read as {_unit_sup(new)}'


def _num(v, n=None):
    """A converted value as text without a float's trailing '.0' (1030.0 -> 1030) and without e-notation: below 0.001
    or from 10^7 up as 'mantissa × 10^exponent' (8.4e-05 -> '8.4 × 10^-5'; the page sets ^-5 as a superscript).
    With n (the value's significant figures) a printed trailing zero stays: 310.0 -> '310.0', 8.2e-4 -> '8.20 × 10^-4'."""
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return v
    if v and (abs(v) < 1e-3 or abs(v) >= 1e7):
        mant, exp = f'{v:.{n - 1 if n else 5}e}'.split('e')  # up to 6 significant digits
        return f"{mant if n else mant.rstrip('0').rstrip('.')} × 10^{int(exp)}"
    if n and 'e' not in (s := f'{v:#.{n}g}'):  # 'e' when the figures end before the decimal point (12000 to 2): plain
        return s.rstrip('.')
    if isinstance(v, float):
        s = repr(v)
        return s[:-2] if s.endswith('.0') else s
    return v


# A printed cell's first number: digit groups after ',' or ' ' are one number ('15,000', '51 200', '0.000 03'); a lone
# ',' between digits is a decimal comma ('0,82'). Leading signs, '~', '(' and the like are skipped.
FIRST_NUM = re.compile(r'[1-9]\d{0,2}(?:[, ]\d{3})+(?:\.\d+)?|\d+(?:[.,]\d{3}(?: \d{1,3})+|[.,]\d+)?|\.\d+')
UNCERTAINTY = re.compile(r'\s*(?:±|\+\s*/?\s*-|\()\s*(\d[\d,]*(?:\.\d+)?)')  # '50 ± 6', '140±20', '0.82 (0.1)', '50 +/- 6'


def _figures(raw):
    """(significant figures, half a unit of the last significant digit relative to the number, the printed figures) of
    the first number of a printed cell, or None. Leading zeros do not count; trailing zeros count after a decimal
    point ('310.0' 4, '0.0050' 2), not at the end of an integer ('1500' 2, '47,000' 2: 47,000 M⁻¹ s⁻¹ is 47 mM⁻¹ s⁻¹,
    never '47.000') unless the printed uncertainty after it reaches them ('50 ± 6' 2, '1100 ± 240' 3, '550 ± 100' 2);
    the ± part and a '× 10^n' are not counted; the first is at least 2 and at most 6."""
    text = re.sub(r'[\x00-\x1f\x7f-\x9f\u200b-\u200f\ufeff]', '', str(raw or ''))  # '12\x8a.8' is 12.8
    m = FIRST_NUM.search(text)
    if not m:
        return None
    s = m.group(0).replace(' ', '')
    s = s.replace(',', '') if re.fullmatch(r'[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?', s) else s.replace(',', '.')
    digits, value = s.replace('.', '').lstrip('0'), float(s)
    if not digits or not value:
        return None
    if '.' in s:
        last = 10 ** -len(s.split('.')[1])
    else:  # an integer: its trailing zeros are not significant, except down to the last digit of a printed uncertainty
        zeros = len(digits) - len(digits.rstrip('0'))
        if (u := UNCERTAINTY.match(text, m.end())) and u.group(1).strip('0.,'):
            us = u.group(1).replace(',', '')
            zeros = min(zeros, 0 if '.' in us else len(us) - len(us.rstrip('0')))
        last, digits = 10 ** zeros, digits[:len(digits) - zeros]
    return min(max(len(digits), 2), 6), 0.5 * last / value, len(digits)


def _sig(v, n):
    return float(f'{v:.{n}g}')


def _printed(v, raw):
    """A converted value to the significant figures the paper printed (`raw`, the printed cell), and the figures its
    text shows. One figure more where a unit conversion would otherwise move the printed number by more than half a
    unit in its last digit (999 min^-1 = 16.65 s^-1, not 16.6 = 996 min^-1). No printed number: 6 figures. The text
    never adds a zero the paper did not print (0.5 mM stays '0.5', 135.0 µM is '0.1350' mM)."""
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not v:
        return v, None
    p = _figures(raw)
    n = p[0] if p else 6
    r = _sig(v, n)
    while p and n < 6 and abs(r - v) > p[1] * abs(v) * (1 + 1e-9):
        n += 1
        r = _sig(v, n)
    kept = f'{r:.{n - 1}e}'.split('e')[0].replace('.', '').lstrip('-').rstrip('0')  # figures before trailing zeros
    return r, max(len(kept), min(p[2] if p else n, n))


SUPER = str.maketrans({'−': '-', '–': '-', '‒': '-', '⁻': '-', '¹': '1', '²': '2', '³': '3', 'μ': 'µ'})


def _unit_key(u):
    """A unit as sorted (symbol, power) pairs, so 'sec−1 mM−1', 'mM^-1 s^-1' and 's^(-1)*mM^(-1)' compare equal; a
    number in it ('10^3 s-1', '× 10^-3') never equals a catalog unit."""
    out, u = [], str(u or '').translate(SUPER)
    u = re.sub(r'\(([^()]*)\)\s*\^?\s*[({]?\s*-\s*1\s*[)}]?\s*$', r'/\1', re.sub(r'^\s*1\s*/', '/', u))  # '(mM s)^-1', '1/(mM s)' -> '/mM s'
    for i, part in enumerate(u.split('/')):
        for num, sym, power in re.findall(r'(\d+(?:\.\d+)?)|([A-Za-zµ]+)\s*\^?\s*[({]?\s*([-+]?\s*\d+)?', part):
            if num:
                out.append(('#' + num, 1))
            elif sym:
                p = int(power.replace(' ', '')) if power else 1
                out.append(('s' if sym == 'sec' else sym, -p if i else p))
    return sorted(out)


def _printed_text(raw_value, raw_unit, ufc=''):
    """A printed value and its unit as one text: '0.002' with '10^6 M^-1 min^-1' is '0.002 × 10^6 M^-1 min^-1' (the
    printed unit starts with a bare power of ten and code read it as a multiplier). With a unit_for_conversion code read
    the unit otherwise, so the two are only joined ('0.58 10^-7 × kcat/Km (M^-1 min^-1)' stays as printed)."""
    v, u = str(raw_value or '').strip(), str(raw_unit or '').strip()
    return f'{v} × {u}' if v and not ufc and re.match(r'[(\[]?\s*10\s*\^', u) else f'{v} {u}'.strip()


RATIO_CHECK = re.compile(r'printed kcat/Km \S+ vs kcat/Km \S+ \(\S+x; allowed \S+x\)( -- outside tolerance)?')


def mass_metrics(w):
    """The metrics of a catlog_wide row kept over a mass concentration (Km mg/mL, kcat/Km mL mg^-1 s^-1, in their own
    columns): the site shows mM values only, so they get no value and no proof line there."""
    return {m for m, f in (('Km', 'km_mg_per_ml'), ('kcat/Km', 'kcat_over_km_ml_per_mg_s')) if w.get(f) is not None}


def _kcat_km_agreement(w):
    """CatLog's own verdict on the printed kcat/Km against kcat ÷ Km (catlog.py ratio_check, kept in catlog_wide):
    'agrees', 'differs' or None (kcat, Km and kcat/Km are not all printed). The exporter's kcat/Km flag follows it on v2
    rows (export_site.py). A difference that the printed figures explain also agrees: kcat/Km printed as
    0.002 × 10^6 M^-1 min^-1 is anything from 0.0015 to 0.0025 × 10^6, so it cannot be held to more than that."""
    m = RATIO_CHECK.match(w.get('ratio_check') or '')
    if not m or mass_metrics(w):  # a Km or kcat/Km over a mass concentration is not shown on the site
        return None
    if not m.group(1):
        return 'agrees'
    k, km, e = (w.get(f) for f in ('kcat', 'km', 'kcat_over_km'))
    if not all(isinstance(x, (int, float)) and x > 0 for x in (k, km, e)):
        return 'differs'
    ev = w.get('evidence') or {}
    hk, hm, he = ((_figures((ev.get(x) or {}).get('raw_value')) or (0, 0.0))[1] for x in ('kcat', 'Km', 'kcat/Km'))
    low, high = k * (1 - hk) / (km * (1 + hm)), (k * (1 + hk) / (km * (1 - hm)) if hm < 1 else float('inf'))
    return 'agrees' if e * (1 - he) <= high and low <= e * (1 + he) else 'differs'


KI_AS_KM = re.compile(r'\bK_?[mM]\b[^;]{0,30}?\b(?:measured|determined|obtained)\s+as\s+(?:an?\s+|the\s+)?K_?[iI]\b|'
                      r'\bK_?[iI]\b[^;]{0,15}\bas\s+(?:the\s+)?K_?[mM]\b', re.I)  # a poor substrate's Km measured by competition
INTERNAL_ORIGIN = re.compile(rb'"data_origin": "growth\d+_[a-z_]+_\d{8}"')  # an old batch name, not a data origin
OLD_PIPELINE_SENTENCE = (b'the export carries no kcat_over_km field for this row, so the printed cell is recorded as evidence '
                         b'only and no ratio is written.')


NO_CONSTRUCT = ' (paper describes no truncated construct)'
NO_SEQ = 'No sequence shown'  # a note that starts so sends no sequence (v2_row)


def _seq_note(w):
    """The public sequence note: what the shown sequence is (catlog_wide's sequence_basis keeps the full trace)."""
    b, wt, acc, seq, sig = (w.get(k) or '' for k in ('sequence_basis', 'wild_type', 'uniprot_id', 'sequence', 'mutation_signature'))
    named = sig if mutation_type(sig, wt) in ('substitution', 'multi_substitution') else ''  # 'AKR1C21 (DD3)' names a form
    if 'natural form' in b:  # catlog.py wide(): 'unresolved: natural form <why>'
        t = b.split('natural form ', 1)[1]
        if m := re.match(r'(.+?) and (.+?) share (.+?): which sequence is which is not known$', t):
            names = [m.group(1)] + m.group(2).split(', ')  # 'TT-ADH and AA-ADH, BB-ADH share UniProt P86885'
            return (f"{NO_SEQ}: {', '.join(names[:-1])} and {names[-1]} {'both' if len(names) == 2 else 'all'} map to "
                    f'{m.group(3)}, which does not say which is which.')
        if m := re.match(r'(.+?) (\w+) residues? differ from (.+)', t):  # 'FaGT2* eight residues differ from the published FaGT2'
            return f'{NO_SEQ}: {m.group(1)} differs from {m.group(3)} at {m.group(2)} residues.'
        return f'{NO_SEQ}: {t}.'  # 'X differs from M82 at Ala-220, ...', 'UniProt Q... was found by EC number only and ...'
    if b.startswith('unresolved') or (not b and not wt and not seq and acc):
        if not acc:
            return f'{NO_SEQ}: the measured construct could not be placed on UniProt'
        if b:
            return 'UniProt canonical sequence shown' + ('' if wt else f' without {named or "the variant"}') + \
                   ': the measured construct could not be placed on it'
        return (f"UniProt canonical sequence shown without {named}: the paper's residue numbers do not match it" if named else
                'UniProt canonical sequence shown: the sequence of this variant is not known')
    if b.startswith('measured construct: '):
        # 'UniProt residues 22-222, after UniProt's signal peptide 1-21 (201 aa; ...)': the mature chain (catlog 15e9f2c)
        m = re.match(r"measured construct: (UniProt residues \d+-\d+(?: minus [^(]+?)?(?:, after UniProt's [^(]+?)?) \((\d+) aa", b)
        if not m:
            return b
        span = f'{m.group(1)} ({m.group(2)} aa)'
        return f'measured construct: {span}' if wt else f'{named or sig} applied to the measured construct, {span}'
    if not b.endswith(NO_CONSTRUCT):
        return b
    frame = b[:-len(NO_CONSTRUCT)]
    if wt:
        return frame  # 'UniProt canonical sequence', 'NCBI BAV69317.1 sequence', 'UniParc UPI... sequence'
    target, how = 'the UniProt canonical sequence', ''
    if m := re.match(r'PDB (\w+) chain (\w+)', frame):
        how = f' (the paper numbers residues as PDB {m.group(1)} chain {m.group(2)})'
    elif m := re.match(r'mature chain after the (.+?) \d+-\d+ \(\+(\d+)\)', frame):
        what = 'signal peptide' if m.group(1) == 'signal' else m.group(1)
        how = f' (the paper numbers the chain after the {what}: its residue 1 is UniProt residue {int(m.group(2)) + 1})'
    elif frame.startswith("the paper's printed mutagenesis primers"):
        how = " (positions matched through the paper's printed mutagenesis primers)"
    elif frame != 'UniProt canonical sequence':
        target = re.sub(r' sequence$', '', frame)  # 'UniProt isoform P52898-2', 'NCBI AAF43045.1', 'UniParc UPI...'
    return f'{named or sig} applied to {target}{how}'


# an inference or reading marker: a reader's aside, not what the paper states (the site publishes facts, not reasoning).
# 'I' only as a pronoun before a verb: 'Table I', 'pCold I', 'I = 0.1 M' (ionic strength) are facts.
ASIDE = re.compile(r"\bread as\b|presumabl|probabl|\blikely\b|assum|\bseems?\b|appears? to|inferr|interpret|\bwe\b|"
                   r"(?-i:\bI (?:read|think|take|took|assume|infer|interpret|treat|count|chose|use|used|have|am|would|could)\b)|"
                   r"\bthe reader\b|\bverifier\b|"  # an inference; what the paper prints or omits is a fact and stays
                   r"provided text|not part of the (?:provided )?text|\bnot in this text\b|pinned down|\bwhich repeats\b|"
                   r"the table columns give|\bso the (?:assay )?\w+ is\b", re.I)  # the reader's prompt and process words
# such words closing a clause of a fact: the clause goes, the fact stays ('given only in the Supporting Information,
# which is not part of the provided text', '..., so the assay temperature is not pinned down', '..., not in this text',
# 'given only in the Supplementary Methods, which are not in the provided text': 4 values on 2026-10-20 that stopped a
# build at its leak check)
PROMPT_CLAUSE = re.compile(r',\s*(?:which (?:is|are) )?not (?:part of the (?:provided )?|in (?:this|the provided) )text\b|'
                           r',\s*so the (?:assay )?\w+ is not pinned down\b', re.I)
GUESS = re.compile(r'\b(?:presumabl\w*|probabl\w*|likely)\b', re.I)  # a segment that guesses goes whole
SEG = re.compile(r'; (?![^()]*\))')  # '; ' outside parentheses
PROCESS = re.compile(r'\bin (?:this|the) sentence\b|\btaken from (?:the )?(?:Results|Methods|Discussion|main text|text)\b', re.I)


def _facts(text, removed=None):
    """The reader's text without its asides: a parenthetical whose words carry an inference or reading marker (ASIDE),
    and a '; '-segment that starts with one. What the paper states stays ('(source not stated)', '(Table 2 footnote b)').
    `removed` (a list) collects what was taken out, for counting."""
    if removed is not None:
        removed += [m.group(0) for m in PROMPT_CLAUSE.finditer(text)]
    text = PROMPT_CLAUSE.sub('', text)
    parked = []
    def park(m):  # innermost parentheses first; a kept one is parked, so an outer one is judged on its own words
        if ASIDE.search(m.group(2)):
            if removed is not None:
                removed.append(re.sub('\0(\\d+)\0', lambda p: parked[int(p.group(1))], m.group(0)).strip())
            return ''
        parked.append(m.group(0))
        return f'\0{len(parked) - 1}\0'
    while (new := re.sub(r'(\s*)\(([^()]*)\)', park, text)) != text:
        text = new
    segs = []
    for s in SEG.split(text):
        s = re.sub(r'^[\s,]+', '', s).strip()  # '(aside), 1 mM DTT' -> '1 mM DTT'
        if s and (ASIDE.match(s) or GUESS.search(s) or PROCESS.search(s)):
            if removed is not None:
                removed.append(s)
        elif s:
            segs.append(s)
    text = '; '.join(segs)
    while '\0' in text:
        text = re.sub('\0(\\d+)\0', lambda p: parked[int(p.group(1))], text)
    return text


# ASCII stand-ins the reader typed, as a curated table prints them: '100 uM' -> '100 µM', '50-ul' -> '50-µL', '37 C' ->
# '37 °C', 'lambda_ex' -> 'λex', '(e = 7710' -> '(ε = 7710', '+/-' -> '±'; one phrase for a temperature the paper omits
PLAIN = ((re.compile(r'(\d)(-?)\s?u(M|g|mol|Ci)\b'), lambda m: f"{m[1]}{m[2] or ' '}µ{m[3]}"),
         (re.compile(r'(\d)(-?)\s?u[lL]\b'), lambda m: f"{m[1]}{m[2] or ' '}µL"),
         (re.compile(r'(?<=\d) C(?=$|[\s,;:).])'), ' °C'),
         (re.compile(r'\blambda[_ ]?(ex|em|max)\b'), r'λ\1'),
         (re.compile(r'(?<![\w.])e = (?=\d)'), 'ε = '),
         (re.compile(r'\+/-'), '±'),
         (re.compile(r'\b(temperature) (?:is |are )?not (?:stated|printed|given|reported)(?: in this paper)?\b'), r'\1 not stated'))


def _plain(text):
    for pat, new in PLAIN:
        text = pat.sub(new, text)
    return text


def _conditions(w):
    """The reader's conditions as published: facts only (_facts), and no 'pH N' that repeats the row's own pH (it has
    its own field): 'pH 9.0' goes, 'pH 7.5, 60 °C' -> '60 °C', 'pH 6.0 (buffer not stated)' -> 'buffer not stated'."""
    out = []
    for s in SEG.split(_facts(w.get('conditions') or '')):
        m = re.match(r'pH\s*(\d+(?:\.\d+)?)(?=$|,|\s*\(|\s+and\b)\s*(?:,\s*|and\s+)?', s)
        if m and w.get('ph') is not None and float(m.group(1)) == w['ph']:
            s = s[m.end():].strip()
            if p := re.fullmatch(r'\(([^()]*)\)(.*)', s):
                s = p.group(1) + p.group(2)
        if s:
            out.append(s)
    return '; '.join(out)


def _assay_parts(w):
    """The reader's assay conditions as published: conditions, cosubstrate and preparation."""
    cond = _conditions(w)
    parts = [x for x in (cond, f"cosubstrate {w['cosubstrate']}" if w.get('cosubstrate') else '') if x]
    prep = _facts((w.get('preparation') or '').strip())  # native / recombinant / tissue: rows can differ only in this
    if prep and prep.lower() not in cond.lower():
        parts.append(f'preparation: {prep}')
    return parts


COMMA = re.compile(r',\s+(?![^()]*\))')  # ', ' outside parentheses
WHERE = re.compile(r'(?:(?:Supplementary|Suppl\.?) )?(?:Table|Fig(?:ure)?\.?|Scheme) ?S?(?:\d+[A-Za-z]?|[IVX]+)\b')
NOTE_MAX = 60  # characters: the grey line under the substrate (its tooltip repeats it)


def _pieces(text):
    """A '; '-list cut into its smallest parts: '; ' and ', ' outside parentheses; a part in parentheses alone loses
    them, and a part's closing ';' or ',' goes."""
    out = []
    for seg in SEG.split(text or ''):
        for x in COMMA.split(seg):
            x = x.strip().rstrip(';,').strip()
            if re.fullmatch(r'\(([^()]*)\)', x):
                x = x[1:-1].strip()
            if x:
                out.append(_plain(x))
    return out


def _balanced(text):
    return text.count('(') == text.count(')') and text.count('[') == text.count(']') and text.count('"') % 2 == 0


def _trim(pieces):
    """One place's differing parts, one per record or '' (none): when the longest is over 40 characters, cut each to the
    words that differ, the words all of them start and end with left out ('partially purified from M. edulis gill
    (45-65% ...)' -> 'gill'), keeping in each a word of three letters or more ('10 mM GSH', never '10') and its
    brackets whole; unchanged when no cut does."""
    have = [p.split() for p in pieces if p]
    if len(have) < 2 or len({p for p in pieces if p}) < 2 or max(len(p) for p in pieces) <= 40:
        return pieces
    short = min(map(len, have))
    pre = suf = 0
    while pre < short and len({w[pre] for w in have}) == 1:
        pre += 1
    while suf < short - pre and len({w[-1 - suf] for w in have}) == 1:
        suf += 1
    cut = lambda w, a, b: ' '.join(w[a:len(w) - b]).rstrip(';,:')
    ok = lambda a, b: all(re.search(r'[^\W\d_]{3}', cut(w, a, b)) and _balanced(cut(w, a, b)) for w in have)
    while suf and not ok(pre, suf):
        suf -= 1
    while pre and not ok(pre, suf):
        pre -= 1
    if not ok(pre, suf) or pre == suf == 0:
        return pieces
    left = iter(cut(w, pre, suf) for w in have)
    return [next(left) if p else '' for p in pieces]


def _differ(lists, trim=False):
    """Per record, its parts that not every record of the group has (in its own order, once each); with `trim`, a
    place where each record has at most one such part is cut to its differing words (_trim)."""
    shared = set.intersection(*map(set, lists))
    out = [list(dict.fromkeys(x for x in parts if x not in shared)) for parts in lists]
    if trim and all(len(d) <= 1 for d in out):
        out = [[x] if x else [] for x in _trim([d[0] if d else '' for d in out])]
    return out


def _where(w):
    """Where in the paper the record's values are printed, short: 'Table 2', 'Fig. 3', else 'in the text'."""
    out = []
    for ev in (w.get('evidence') or {}).values():
        loc = LOCAL_PATH.sub('', ev.get('location') or '').strip()
        m = WHERE.match(loc)
        if loc and (label := m.group(0) if m else 'in the text') not in out:
            out.append(label)
    return out


def condition_notes(pairs):
    """(w, v2_row(w)) pairs: records that show the same paper, enzyme, EC, organism, substrate, variant, temperature and
    pH, whatever their values, get condition_note: what tells them apart, short, only the parts that differ (fix pass
    after round 16b: about a quarter of the records read from the paper looked like another in Browse, a
    beta-galactosidase free and immobilised, in buffer and in milk, with nothing under the substrate to say so). In
    order, until each record's note differs from the others': the assay parts the others do not all share (the
    conditions as published, the cosubstrate, the preparation; each cut to its differing words when long: 'with 0.5 mM
    MnCl2', 'gill'), then the published per-value qualifiers ('apparent Km'), then where the paper prints the values
    ('Table 2'). A part that would make the note longer than NOTE_MAX characters is left out; none, no note."""
    groups = {}
    for w, r in pairs:
        key = (r.get('pubmed_id') or r.get('doi'), *(r.get(k) for k in ('enzyme_name', 'ec_number', 'organism', 'substrate_name',
               'wild_type', 'mutation_signature', 'temperature_k', 'ph')))
        groups.setdefault(json.dumps(key, default=str), []).append((w, r))
    for group in groups.values():
        if len(group) < 2:
            continue
        ws = [w for w, _ in group]
        prep = [_facts((w.get('preparation') or '').strip()) for w in ws]
        cond = [_conditions(w) for w in ws]
        assay = zip(_differ([_pieces(c) for c in cond], trim=True),
                    _differ([[f"cosubstrate {w['cosubstrate']}"] if w.get('cosubstrate') else [] for w in ws], trim=True),
                    _differ([_pieces(p) if p and p.lower() not in c.lower() else [] for p, c in zip(prep, cond)], trim=True))
        levels = ([a + b + c for a, b, c in assay],
                  _differ([[x for m, k in (('kcat', 'kcat_note'), ('Km', 'km_note'), ('kcat/Km', 'kcat_over_km_note'))
                            for x in _labels(m, w.get(k))] for w in ws]),
                  _differ([_where(w) for w in ws]))
        notes = [''] * len(group)
        for parts in levels:
            if not any(parts):
                continue
            for i, add in enumerate(parts):
                for x in add:
                    note = f'{notes[i]}; {x}' if notes[i] else x
                    if len(note) <= NOTE_MAX:
                        notes[i] = note
            if len(set(notes)) == len(notes):
                break
        for (w, r), note in zip(group, notes):
            if note:  # a charge sign ending it survives the exporter's text strip, as in v2_row
                r['condition_note'] = re.sub(r'(?<=[A-Za-z0-9])-(?=; |$)', '⁻', note)


# ---- each value against the enzyme databases (catlog_wide database_check, tools/dbcompare.py), as fixed phrases ----
DATABASES = ('BRENDA', 'SABIO-RK', 'OED', 'SKiD', 'STRENDA', 'UniProt')  # dbcompare.SOURCES, in its order
try:  # the smallest difference sent to a check against the paper (tools/ is on the path when catlog.py runs this)
    from dbcompare import SMALL_FACTOR
except ImportError:
    SMALL_FACTOR = None
ALL_DATABASES = ', '.join(DATABASES[:-1]) + ' and ' + DATABASES[-1]  # 'BRENDA, SABIO-RK, OED, SKiD, STRENDA and UniProt'
UNIT_TEXT = {'s^(-1)': 's⁻¹', 'mM': 'mM', 's^(-1)*mM^(-1)': 'mM⁻¹ s⁻¹'}
TO_SUP = str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹')
SCALED_UNIT = re.compile(r'10\s*(?:\^|[⁻⁰¹²³⁴⁵⁶⁷⁸⁹])|[×xX*✕]\s*\d')  # a printed unit that carries a factor: '× 10^-1 s^-1', '10^6 Km (M)'
# a value none of the databases compared lists for its paper (status new), in plain words by why (dbcompare reason);
# never 'no database' and never counted in words ('no compared database', as the site's definition says; round 9 brief
# C9, round 14): a database that is not compared can list the number. The page names them above the lines.
NONE_OF = 'No compared database'
NEW_LINE = {'metric_absent': NONE_OF + ' lists a {m} for this paper.',
            'substrate_absent': NONE_OF + ' lists a {m} for this substrate in this paper.',
            'variant_absent': NONE_OF + ' lists a {m} for this substrate with this variant or organism in this paper.',
            'condition_absent': NONE_OF + ' lists this {m} for this paper.'}  # followed by those listing others for it
NOT_LISTED = '{} no kcat, Km or kcat/Km for this paper.'  # paper_not_in_databases: compared_names() and 'list'
# a kcat/Km CatLog calculated (the paper prints none): its line, and the comparison download's, in one wording
CALCULATED_LINE = 'Calculated by CatLog as kcat ÷ Km; not compared.'
_COMPARED = {}


def compared_names(root=None):
    """The DATABASES that have values in sources/db_values.tsv (compared_sources' names, read once per root without its
    file checks), in DATABASES order; DATABASES when the file is missing. The lines name these, as the README and the
    Stats definition do: a database with no rows in this build (UniProt before tools/uniprot_values.py and
    tools/db_values.py ran) is never said to list nothing from a paper."""
    root = Path(root or ROOT)
    if root not in _COMPARED:
        have, p = set(), root / 'sources' / 'db_values.tsv'
        if p.exists():
            with open(p) as fh:
                have = {line.split('\t', 1)[0] for line in fh}
        _COMPARED[root] = tuple(s for s in DATABASES if s in have) or DATABASES
    return _COMPARED[root]


OTHER_PARAMS = {'kcat': 'Km or kcat/Km', 'Km': 'kcat or kcat/Km', 'kcat/Km': 'kcat or Km'}  # metric_absent: what they list
# a cause a check against the paper recorded (dbcompare.CAUSES), as the line states it: the record panel's own words
# for the cause (assets/catlog-static.js DATABASE_CAUSES), so the page words one cause one way (round 13); time_unit
# keeps both directions (a per-second number taken as per-minute too), which the site's phrase does not say
CAUSE_TEXT = {'header_scale_inverted': "the table header's power of ten applied the wrong way",
              'header_scale_ignored': "the table header's power of ten left out",
              'unit_not_converted': 'the printed unit not converted',
              'uM_entered_as_mM': 'a µM value entered as mM', 'mM_entered_as_uM': 'an mM value entered as µM',
              'time_unit': 'a time unit taken for another (seconds, minutes or hours)',
              'decimal_or_exponent_slip': 'a decimal point or exponent slip',
              'value_from_other_row': 'a value from another cell of the table',
              'value_not_in_paper': 'a value the paper does not print',
              'paper_unit_misprint': 'a unit the paper misprints',
              'recomputed_ratio': "kcat/Km worked out from the database's own kcat and Km"}
# recorder inference in a recorded evidence text: a part holding one of these words is not published (facts only)
INFERENCE = re.compile(r"\b(?:so|thus|therefore|hence|i\.?e\.?|implies|implying|meaning|means|consistent|inconsistent|"
                       r"likely|unlikely|probably|presumably|suggests?|apparently|seems?|appears?|assum\w*|interpret\w*|"
                       r"literally|reading|because|since|must|should|would|could|evidently|clearly|indicat\w*|"
                       r"plausibl\w*|explain\w*|confirm\w*|we|our|not converted|unconverted|same error|nearest|read as|reads|"
                       r"(?:column|unit|units) (?:is|are)|is (?:in )?(?:mM|µM|μM|uM|nM|M)|swapped|instead of|fits?|flags?|"
                       r"exactly|dropped|matches|per refs?)\b", re.I)


# a recorded evidence or the value's own reading notes say the power of ten printed with the unit is not legible
# (1371328: 'header (min^-1)x(10^n), n illegible in the scan', 'header OCR-damaged'): the reader's raw_unit then holds an
# inferred factor, so a line quotes the cell alone and says how CatLog reads the unit
ILLEGIBLE_SCALE = re.compile(r'(?:header|exponent|power of ten|multiplier|10\^?n)[^.;]{0,40}?(?:illegible|unreadable|not legible|'
                             r'OCR[- ]damaged|garbled)|(?:illegible|unreadable|not legible|OCR[- ]damaged|garbled)[^.;]{0,40}?'
                             r'(?:header|exponent|power of ten|multiplier)', re.I)


def _supnum(t):
    return re.sub(r'\s', '', t).replace('−', '-').replace('–', '-').replace('—', '-').lstrip('+').translate(TO_SUP)


def _sup(text):
    """Plain text for a line: exponents as superscripts ('8.2 × 10^-4' -> '8.2 × 10⁻⁴', 'mM^{−1} s^{−1}' and
    'M^-1 s^-1' -> 'mM⁻¹ s⁻¹', 'M⁻¹ s⁻¹'), 'K_m' -> 'Km', '\\times' -> '×'."""
    s = re.sub(r'\^\s*[{(]\s*([-−–—+]?\s*\d+)\.?\s*[})]', lambda m: _supnum(m.group(1)), str(text))  # also '10^{4.}'
    s = re.sub(r'\^\s*([-−–—+]?\s?\d+)', lambda m: _supnum(m.group(1)), s)
    s = re.sub(r'\s?\^\s*([-−–—])\s?(?=[¹²³⁴⁵⁶⁷⁸⁹⁰])', '⁻', s)  # a reader's 's^− ¹', 'mm ^− ¹' (a superscript one after it)
    s = re.sub(r'(?<=[A-Za-z])_\{?([A-Za-z]{1,3})\}?(?![A-Za-z])', r'\1', s)
    return s.replace('\\times', '×')


def _unit_sup(text):
    """A printed value with its unit for a line: _sup, and a unit's '-1' ('sec−1 mM−1', 's-1' -> 'sec⁻¹ mM⁻¹', 's⁻¹';
    never a name such as 'SHP-1'), 'uM' -> 'µM', a number in e-notation as × 10ⁿ ('1.88e+06' -> '1.88 × 10⁶', the same
    number: a table that prints e-notation, or a reader who typed it)."""
    s = re.sub(r'(?<![\w.])(\d+(?:\.\d+)?)e([+-]?)0*(\d+)\b', lambda m: f"{m[1]} × 10^{'-' if m[2] == '-' else ''}{m[3]}", str(text))
    s = re.sub(r'(?<![A-Za-z])(s|sec|min|h|hr|[mµμunp]?M)\s?[−–-]\s?1(?![\d.])', r'\1⁻¹', _sup(s))  # also after '¹': 's⁻¹mM−1'
    return re.sub(r'(?<![A-Za-z])u(?=M\b|M⁻)', 'µ', s)


def _commas(text):
    """Thousands separators in a text code writes ('306000 s⁻¹' -> '306,000 s⁻¹'); exponents stay as they are."""
    return re.sub(r'(?<![\d.,])(\d{4,})(?![\d,])', lambda m: f'{int(m.group(1)):,}', str(text))


def _fmt(v):
    """A database or derived number as the line prints it: up to 6 significant figures, a × 10ⁿ below 0.001 and from
    10^7, and below 1 when the decimal would run to 6 or more places (0.001667 -> 1.667 × 10⁻³, 0.022954 -> 2.2954 ×
    10⁻²); thousands separated."""
    v = float(f'{v:.6g}')
    t = _num(v)
    if isinstance(t, str) and re.fullmatch(r'0\.\d{6,}', t):
        m, e = f'{v:.5e}'.split('e')
        t = f"{m.rstrip('0').rstrip('.')} × 10^{int(e)}"
    return _commas(_sup(t))


def _dbfmt(v):
    """A database's number as a line names it (_fmt): one with 6 or more significant figures in catalog units is
    computed, never printed (SKiD's means such as 0.894427, a unit conversion such as SABIO-RK's 2.77 min^-1 =
    0.0461667 s^-1), so it is named to 4 (0.8944, 0.04617), from 1,000 to the unit (1,336.67 -> 1,337)."""
    digits = re.sub(r'[^0-9]', '', f'{v:.6g}'.split('e')[0]).strip('0')
    if len(digits) < 6:
        return _fmt(v)
    return _fmt(float(round(v)) if abs(v) >= 1000 else float(f'{v:.4g}'))  # 18,333.3 -> 18,333, never 18,330


def _names(srcs):
    srcs = list(srcs)
    return ', '.join(srcs[:-1]) + ' and ' + srcs[-1] if len(srcs) > 1 else ''.join(srcs)


def _pow_text(n):
    """10^n (n >= 1) as a factor: '10', '100', '1,000', then '10⁴'."""
    return f'{10 ** n:,}' if n <= 3 else '10' + str(n).translate(TO_SUP)


def _fold(x):
    """A ratio (>= 1) as text, to 2 significant figures (3 where 2 would read as a power of ten: 10.5): 9.5, 46,
    1,400; an exact power of ten (within 2%) as _pow_text; from 10^4 '2.5 × 10⁵'."""
    L = math.log10(x)
    n = round(L)
    if n >= 1 and abs(L - n) <= math.log10(1.02):
        return _pow_text(n)
    k = 2
    if abs(math.log10(float(f'{x:.2g}')) % 1) < 1e-9:  # 10.48 is '10.5', never a bare '10' that reads as exact
        k = 3
    r = float(f'{x:.{k}g}')
    if r >= 1e4:
        m, e = f'{r:.{k - 1}e}'.split('e')
        return f'{m} × 10{str(int(e)).translate(TO_SUP)}'
    return f'{r:,.0f}' if r >= 100 else f'{r:g}'


def _relative(q):
    """CatLog / database = q, as the database's number against CatLog's: '9.5× higher than CatLog's value', '1,000×
    lower than CatLog's value' (higher and lower worded alike, as the record panel's factors are)."""
    return f"{_fold(1 / q)}× higher than CatLog's value" if q < 1 else f"{_fold(q)}× lower than CatLog's value"


def _small(zeros, digits):
    """A decimal written 0.<zeros><digits> with 6 or more places as mantissa × 10ⁿ with all its figures (0.000362333 ->
    3.62333 × 10⁻⁴), so no long decimal is published and no figure is lost."""
    return f"{digits[0]}{'.' + digits[1:] if len(digits) > 1 else ''} × 10^-{len(zeros) + 1}"


def _computed4(m):
    """A database's decimal with 6 or more significant figures in a recorded evidence is computed (a unit conversion
    such as SABIO-RK's 32.6 min^-1 = 0.000543333 s^-1): to 4 figures as _dbfmt names it, from 1,000 to the unit. A
    printed number keeps its figures (Km 1947.94 µM)."""
    s = m.group(0)
    if len(re.sub(r'\D', '', s.split('e')[0]).strip('0')) < 6:
        return s
    v = float(s)
    return str(round(v)) if abs(v) >= 1000 else repr(float(f'{v:.4g}'))


def _drop_parens(t):
    """A recorded evidence text without the parentheses that hold recorder inference (INFERENCE), nested ones too: in
    "(column 'Km (mM)', µM per ref 15 ATP 112 µM)" the inner '(mM)' is kept while the whole is tested and dropped."""
    kept = []

    def unmask(x):
        return re.sub(r'\x00(\d+)\x01', lambda m: kept[int(m.group(1))], x)

    def one(m):
        if INFERENCE.search(unmask(m.group(0))):
            return ''
        kept.append(m.group(0))
        return f'\x00{len(kept) - 1}\x01'
    prev = None
    while prev != t:
        prev, t = t, re.sub(r'\s*\([^()]*\)', one, t)
    while '\x00' in t:
        t = unmask(t)
    return t


def _evidence_facts(text):
    """A recorded evidence text, facts only: no local path, no parenthesis, sentence or ';'-part with recorder
    inference, a clause after ', so' / ', i.e.' cut; '+-' between two numbers as '±' (a charge sign stays: Mg2+-PK), a
    database's computed decimal with 6 or more significant figures to 4 (_computed4),
    2.6e+05 as 2.6 × 10⁵, a decimal with 6 or more places as × 10ⁿ (_small), superscript exponents; at most 240
    characters."""
    t = re.sub(r'\s+', ' ', LOCAL_PATH.sub('', str(text or ''))).strip()
    t = re.sub(r'\s*\bread (?:the )?(?:table |column )?headers? literally\b', '', t, flags=re.I)
    t = _drop_parens(t)
    parts = []
    for sentence in re.split(r'(?<=[a-z0-9)\'])\.\s+(?=[A-Z])', t):
        kept = []
        for p in re.split(r';\s*(?![^()]*\))', sentence):  # ';' outside parentheses
            cut = re.split(r',?\s+(?:(?:so|thus|therefore|hence|which|meaning|matching)\b|i\.e\.)', p, flags=re.I)
            p = cut[0].strip(' ,.')
            if len(cut) > 1:  # a clause cut inside a parenthesis: closed ('(footnote a: similar to ref 15)')
                p += ')' * max(0, p.count('(') - p.count(')'))
            if p and not INFERENCE.search(p):
                kept.append(p)
        if kept:
            parts.append('; '.join(kept))
    t = '. '.join(parts)
    t = re.sub(r'(?<=[\d)\]])\s*\+\s*/?\s*-\s*(?=[\d(.])', ' ± ', t)  # an uncertainty, never a charge: Mg2+-PK, NAD+-dependent
    t = re.sub(r'\b(?:BRENDA|SABIO-RK|OED|SKiD|STRENDA|UniProt)\b(?:[^;.]|\.(?=\d))*',  # SABIO-RK's 0.000543333 as 0.0005433
               lambda m: re.sub(r'(?<![\d.,])\d+\.\d+(?:e[+-]?\d+)?(?![\d.])', _computed4, m.group(0)), t)
    t = re.sub(r'(\d(?:\.\d+)?)e([+-]?)0*(\d+)\b', lambda m: f"{m.group(1)} × 10^{'-' if m.group(2) == '-' else ''}{m.group(3)}", t)
    t = re.sub(r'(?<![\d.])0\.(0*)([1-9]\d*)(?![\d.])', lambda m: _small(m.group(1), m.group(2)) if len(m.group(1) + m.group(2)) >= 6 else m.group(0), t)
    t = _unit_sup(t)
    return t if len(t) <= 240 else t[:239].rsplit(' ', 1)[0] + ' …'


PARTS = ('lists', 'paper', 'cause', 'closure', 'others')  # database_parts' keys, in the line's order (round 9 brief C6)


def _database_parts(metric, c, shown, printed, where, triple):
    """The fixed sentences of one value's line compared with databases (contribution report 2.2: fixed phrases filled by
    code; facts only), by PARTS: lists (what the databases named first list for this value: 'Same as BRENDA.', 'BRENDA
    lists 0.062 mM, 10× lower than CatLog's value.', the same number under another label, 'No compared database
    lists ...'),
    paper (a correction: what the paper prints, where, and how CatLog reads the unit), cause (a cause an AI check of
    the paper recorded), closure (the paper's own kcat ÷ Km against either number), others (what else they list: another
    number at an exact factor, another measurement, a new printed kcat/Km's kcat and Km, and what each other database
    that lists the paper lists for the parameter); '' where a part says nothing. shown: CatLog's value as the page
    shows it; printed: the printed value and unit; where: the location; triple: the measurement's kcat, Km and kcat/Km
    as (text shown, number) pairs (closure sentence)."""
    unit = UNIT_TEXT[METRIC_FIELD[metric][1]]
    st, srcs = c.get('status'), c.get('sources') or []
    dbs, verb = _names(srcs) or 'A database', 'lists' if len(srcs) <= 1 else 'list'
    dv = f"{_dbfmt(c['database_value'])} {unit}" if isinstance(c.get('database_value'), (int, float)) else 'another number'
    shown_u = f'{_commas(shown)} {unit}' if shown else "CatLog's value"
    if c.get('read_as') and SCALED_UNIT.search(c.get('printed_unit') or ''):
        # CatLog reads a header's power of ten otherwise than as a multiplier of the cell: the cell and the printed unit
        # apart, never '1.55 ± 0.19 × 10⁻¹ s⁻¹', a quantity the paper does not state
        printed = f"{_unit_sup(str(c.get('printed') or '').strip())} with the unit '{_unit_sup(c['printed_unit'].strip())}'"
    join = lambda *xs: ' '.join(x for x in xs if x)
    ov = {}  # databases that list one other number share a sentence ('also' for those named before)
    for s, v in (c.get('other_values') or {}).items():
        ov.setdefault((_dbfmt(v), s in srcs), []).append(s)
    others = join(*(f"{_names(g)} {'also ' if also else ''}{'lists' if len(g) == 1 else 'list'} {v} {unit}." for (v, also), g in ov.items()))
    om = {}  # databases that list one number a check against the paper found to belong to another record
    for s, v in (c.get('other_measurement') or {}).items():
        om.setdefault(_dbfmt(v), []).append(s)
    elsewhere = join(*(f"{_names(g)} {'lists' if len(g) == 1 else 'list'} {v} {unit} for another record of this "
                       'paper (found by an AI check of the paper).' for v, g in om.items()))
    def label(g, named=False):  # one sentence per label and number: each database named with its own number; 'it'
        # (the value) only where the line names no other number before it (never after a differs or corrected head, nor
        # after a confirmed line's rounded, other or another-measurement numbers: there each database's own number)
        n = f"{_dbfmt(g['database_value'])} {unit}" if (g.get('figures') or named) and isinstance(g.get('database_value'), (int, float)) else 'it'
        what = (g.get('database_label') or 'under another label').rstrip('.')  # 'for Acidovorax sp.' ends the sentence once
        what = what.replace('->', '→')  # a database's linkage '(1->4)' as a name prints it, never an ASCII arrow
        return f"{_names(g['sources'])} {'lists' if len(g['sources']) == 1 else 'list'} {n} {what}."
    # the other databases that list the paper: what they list for this parameter
    named = st in ('differs', 'corrected') or st == 'confirmed' and bool(others or elsewhere or c.get('rounded'))
    rest = join(*(label(g, named) for g in c.get('other_labels') or []) if st != 'same_number_other_label' else (),
                f"{_names(c['other_numbers'])} {'lists' if len(c['other_numbers']) == 1 else 'list'} other {metric} values "
                'for this paper.' if c.get('other_numbers') else '',
                f"{_names(c['no_metric'])} {'lists' if len(c['no_metric']) == 1 else 'list'} no {metric} for this paper."
                if c.get('no_metric') else '')
    if st == 'confirmed':
        rounded = c.get('rounded') or {}
        exact = [s for s in srcs if s not in rounded]
        groups = {}  # databases that list one number to the same figures share a sentence
        for s, (v, k) in rounded.items():
            groups.setdefault((_dbfmt(v), k), []).append(s)
        same = [f"{_names(g)} {'lists' if len(g) == 1 else 'list'} {v} {unit} (the same to "
                f"{'one significant figure' if k == 1 else 'two significant figures'})." for (v, k), g in groups.items()]
        return {'lists': join(f'Same as {_names(exact)}.' if exact else '', *same), 'others': join(others, elsewhere, rest)}
    if st == 'same_number_other_label':  # 'it' until a sentence names its number (one listed to fewer figures)
        said, shown_n = [], False
        for g in ({**c, 'sources': srcs or ['A database']}, *(c.get('other_labels') or [])):
            said.append(label(g, shown_n))
            shown_n = shown_n or bool(g.get('figures'))
        return {'lists': join(*said), 'others': join(elsewhere, rest)}
    if st == 'new':
        has = lambda g: f"{_names(g)} {'lists' if len(g) == 1 else 'list'}"
        if c.get('paper_not_in_databases'):  # the databases compared in this build, never one without rows
            return {'lists': NOT_LISTED.format(has(compared_names()))}
        # each database named with what it lists from the paper for the parameter (dbcompare: pair_numbers,
        # other_numbers, no_metric; paper_sources), those that list nothing from the paper last
        listing = c.get('paper_sources') or []
        lacks = c.get('no_metric') or []
        # (a printed kcat/Km whose kcat and Km they list: its first sentence already says none lists the kcat/Km)
        rest = [f"{has(c['pair_numbers'])} other {metric} values for this substrate and variant." if c.get('pair_numbers') else '',
                f"{has(c['other_numbers'])} other {metric} values for this paper." if c.get('other_numbers') else '',
                '' if not lacks or c.get('ratio_only') else f"{has(lacks)} only {OTHER_PARAMS[metric]} values for this paper."
                if c.get('reason') == 'metric_absent' else f"{has(lacks)} no {metric} for this paper."]
        absent = [s for s in compared_names() if s not in listing]
        if listing and absent:
            rest.append(f'{has(absent)} no kcat, Km or kcat/Km for this paper.')
        if c.get('ratio_only'):  # its kcat and Km are confirmed: by whom, from the kcat's and the Km's sources
            rs = c.get('ratio_sources') or {}
            k, m = rs.get('kcat') or [], rs.get('Km') or []
            groups = [(g, what) for g, what in (([s for s in DATABASES if s in k and s in m], 'kcat and Km'),
                                                ([s for s in DATABASES if s in k and s not in m], 'kcat'),
                                                ([s for s in DATABASES if s in m and s not in k], 'Km')) if g]
            # 'BRENDA lists this record's kcat and Km; SKiD lists its Km.' (round 17: the site's word is record)
            who = '; '.join(f"{has(g)} {'this record' + chr(39) + 's' if i == 0 else 'its'} {what}"
                            for i, (g, what) in enumerate(groups))
            return {'lists': NONE_OF + ' lists this printed kcat/Km for this paper.',
                    'others': join(f'{who}.' if who else '', *rest, elsewhere)}
        return {'lists': NEW_LINE.get(c.get('reason'), NEW_LINE['condition_absent']).format(m=metric), 'others': join(*rest, elsewhere)}
    if st == 'not_compared':
        return {'lists': CALCULATED_LINE if c.get('reason') == 'calculated' else 'Not compared.'}
    q, rel, db1 = c.get('factor'), c.get('relation', ''), (srcs or ['the database'])[0]
    (k, kv), (m, mv), (r, _) = triple
    ratio = f"The paper's kcat ÷ Km ({_commas(k)} s⁻¹ ÷ {_commas(m)} mM = {_fmt(float(f'{kv / mv:.3g}'))} mM⁻¹ s⁻¹)" if kv and mv else ''
    closure = {'neither': "The paper's printed kcat/Km does not equal its kcat ÷ Km."}.get(c.get('closure'), '')
    near = (c.get('closure_fold') or 1) > 1.5  # within ratio_check's widened tolerance, but not within 1.5x
    # the database's number is the head's (dv), so the closure names it by the database alone (round 14: said once)
    if ratio and c.get('closure') == 'supports_catlog':
        if metric == 'kcat/Km':
            closure = (f"{ratio} is nearer to CatLog's kcat/Km ({shown_u}) than to {db1}'s." if near else
                       f"{ratio} agrees with CatLog's kcat/Km ({shown_u}), not {db1}'s.")
        else:
            closure = (f"{ratio} is nearer to its printed kcat/Km ({_commas(r)} mM⁻¹ s⁻¹) with CatLog's {metric} than with {db1}'s." if near else
                       f"{ratio} agrees with its printed kcat/Km ({_commas(r)} mM⁻¹ s⁻¹) using CatLog's {metric}, not {db1}'s.")
    elif ratio and c.get('closure') == 'supports_database':
        if metric == 'kcat/Km':
            how = 'is nearer to' if near else 'equals' if (c.get('closure_fold') or 1) <= 1.02 else 'agrees with'
            closure = f"{db1}'s kcat/Km {how} {ratio[:1].lower()}{ratio[1:]}{' than CatLog' + chr(39) + 's' if near else ''}; the paper prints {printed}."
        else:
            closure = (f"The paper's kcat ÷ Km is nearer to its printed kcat/Km with {db1}'s {metric} than with CatLog's." if near else
                       f"The paper's kcat ÷ Km agrees with its printed kcat/Km using {db1}'s {metric}, not CatLog's.")
    if st == 'differs':
        if rel == 'under_1.5x' or not q:
            head = f'{dbs} {verb} {dv} (CatLog: {shown_u}).'
        elif database_cause(c) == 'exact_factor':  # code found an exact factor and nothing else was checked (2026-10-15)
            head = f"{dbs} {verb} {dv}, {_relative(q)}: an exact factor, not yet checked against the paper."
        else:
            head = f'{dbs} {verb} {dv} ({_relative(q)}); cause not yet known.'
        return {'lists': head, 'closure': closure, 'others': join(others, elsewhere, rest)}
    # corrected: the relation code can state, or a recorded cause (database_cause, database_evidence)
    paper = f'The paper prints {printed}' + (f" ({where.replace('(', '[').replace(')', ']')})" if where else '')
    if c.get('unit_inferred'):  # the printed power of ten is not legible: the cell alone, then CatLog's reading
        paper += f"; CatLog reads the unit as {_unit_sup(c['unit_inferred'].strip())}"
    elif c.get('read_as'):
        paper += f"; CatLog reads the unit as {_unit_sup(c['read_as'])}"
    # a cause a check against the paper recorded is said once, in its own sentence: the head then gives only the number
    # and the factor (never 'the printed number taken as ...' beside 'An AI check of the paper found the cause: a decimal
    # point or exponent slip'); a cause code states (paper_unit_misprint on a printed unit the paper's own kcat ÷ Km does
    # not support) is carried by the head, the paper and closure sentences. Every recorder of database_corrections.tsv
    # is an AI agent (dbcheck's paper_check; round 14: the line says so, beside the page's human review)
    cause = f"An AI check of the paper found the cause: {CAUSE_TEXT[c['cause']]}." if c.get('cause') in CAUSE_TEXT and _recorded(c) else ''
    der = c.get('derivation') if rel == 'time_factor' and not cause else None
    if cause:
        head = f'{dbs} {verb} {dv}' + (f', {_relative(q)}.' if q else '.')
    elif rel == 'printed_number_unit_not_applied':
        head = f'{dbs} {verb} {dv}: the printed number taken as {unit}.'
    elif rel == 'printed_unit_as_printed':
        head = f'{dbs} {verb} {dv}: the printed value in its printed unit.'
    elif der:  # database = printed x 60^a x 10^n (dbcompare.relate)
        op = {1: '× 60', -1: '÷ 60', 2: '× 3,600', -2: '÷ 3,600'}[der['a']] + (f" × 10{str(der['n']).translate(TO_SUP)}" if der['n'] else '')
        p = _num(der['printed'], (_figures(printed) or (0, 0, None))[2])  # with the printed figures ('12.0')
        head = f"{dbs} {verb} {dv} = the printed {_commas(_sup(p))} {op}."
        paper += f'; CatLog: {shown_u}'
    elif rel == 'power_of_ten' and q:
        n = round(math.log10(q))
        head = f"{dbs} {verb} {dv}, {_pow_text(abs(n))}× {'lower' if n > 0 else 'higher'} than CatLog's value."
    else:
        head = f'{dbs} {verb} {dv}' + (f' ({_relative(q)}).' if q else '.')
    return {'lists': head, 'paper': paper + '.', 'cause': cause, 'closure': closure, 'others': join(others, elsewhere, rest)}


def _joined(parts):
    """A line from its parts: the non-empty ones in PARTS order, joined by a space (database_line is always exactly its
    database_parts joined so)."""
    return ' '.join(parts[k] for k in PARTS if parts.get(k))


def _database_line(metric, c, shown, printed, where, triple):
    """The record panel's line for one value compared with databases (_database_parts, joined)."""
    return _joined(_database_parts(metric, c, shown, printed, where, triple))


# the cause of a correction code states (dbcompare rule A), as its relation names it (round 9 brief C1); on a value
# that differs by one of these relations with nothing else checked, database_cause is exact_factor (2026-10-15: an
# exact factor alone corrects nothing; the value is a difference, sent to a check against the paper like any other)
CODE_CAUSES = ('power_of_ten', 'printed_number_unit_not_applied', 'time_factor')
EXACT_FACTOR = 'exact_factor'
# how a correction was found (round 9 brief C2): a check against the paper recorded its cause; code found an exact factor
# (or the printed value in a printed unit CatLog reads otherwise) and the paper's own kcat ÷ Km agrees with CatLog's
# number, not the database's (closure supports_catlog, within catlog.py ratio_check's tolerance)
FOUND_BY = ('paper_check', 'factor_cross_checked')
# why no compared database lists a value (round 9 brief C3): the why of new_to_databases.tsv (dbcompare.NEW_WHY)
NEW_REASONS = ('paper_not_in_databases', 'metric_absent', 'substrate_absent', 'variant_absent', 'condition_absent', 'ratio_only')


def _recorded(c):
    """The value's cause was recorded by a check against the paper (sources/database_corrections.tsv), not stated by code."""
    return bool(c.get('cause')) and (c.get('cause_by') or 'code') != 'code'


def database_cause(c):
    """database_cause of a value's comparison (database_check c): on a correction the cause a check against the paper
    recorded (CAUSE_TEXT's codes), else the relation code states (CODE_CAUSES); different_measurement on any value where
    a check against the paper found a database number to be another measurement; '' otherwise."""
    st = c.get('status')
    if c.get('cause') and (st == 'corrected' or c['cause'] == 'different_measurement'):
        return c['cause']
    if st == 'corrected' and not _recorded(c) and c.get('relation') in CODE_CAUSES:
        return c['relation']
    if st == 'differs' and not c.get('cause') and not c.get('recorded') and c.get('relation') in CODE_CAUSES \
            and c.get('closure') not in ('neither', 'supports_database'):
        return EXACT_FACTOR  # an exact factor and nothing else checked: no recorded verdict, and the paper's own
    return ''  # kcat ÷ Km (when it can be tested) does not speak against CatLog's number


def database_found_by(c):
    """How a correction was found (FOUND_BY); '' on any other value. Every recorder of database_corrections.tsv
    (paper_check, verifier, audit) read the paper, so a recorded cause is paper_check; a correction code states passed
    dbcompare's rule A, which needs the paper's own kcat ÷ Km on CatLog's side (factor_cross_checked)."""
    if c.get('status') != 'corrected':
        return ''
    return 'paper_check' if _recorded(c) else 'factor_cross_checked'


def database_new_reason(c):
    """Why no compared database lists a value (status new), as new_to_databases.tsv's why: paper_not_in_databases
    first, then ratio_only, then dbcompare's reason; '' on any other value."""
    if c.get('status') != 'new':
        return ''
    why = 'paper_not_in_databases' if c.get('paper_not_in_databases') else 'ratio_only' if c.get('ratio_only') else c.get('reason') or ''
    return why if why in NEW_REASONS else ''


def _database_fields(metric, c, shown, printed, where, triple, catlog=None):
    """Proof-line fields of one value's database comparison: database_status, database_line, database_sources; on a
    correction database_cause (recorded by a check against the paper, or the relation code states), database_found_by
    and, with a recorded cause, database_evidence (WEBSITE.md); database_cause different_measurement where a check
    against the paper found a database number to be another measurement; on a value no compared database lists
    database_new_reason; database_by_source (what each database that lists the paper lists for the value; catlog:
    CatLog's number in catalog units) and database_parts (the line's sentences by PARTS; export_site.py ships them in
    the details shards only). Nothing else of database_check (nor db_check) is published."""
    named = list(c.get('sources') or []) + ([s for g in c.get('other_labels') or [] for s in g['sources']]
                                            if c.get('status') == 'same_number_other_label' else [])
    parts = _database_parts(metric, c, shown, printed, where, triple)
    out = {'database_status': c.get('status', ''), 'database_line': _joined(parts),
           'database_sources': [s for s in DATABASES if s in named], 'database_cause': database_cause(c),
           'database_found_by': database_found_by(c), 'database_new_reason': database_new_reason(c),
           'database_by_source': database_by_source(metric, c, catlog),
           'database_parts': {k: parts[k] for k in PARTS if parts.get(k)}}
    if c.get('evidence') and c.get('status') == 'corrected':
        out['database_evidence'] = _evidence_facts(c['evidence'])
    return {k: v for k, v in out.items() if v not in ('', [], {})}


LABEL_MAX = 90  # characters of a database's label in database_by_source (round 9 brief C4)


def _four(v):
    """A number to at most 4 significant figures (round 9 brief C4: 0.0461667 -> 0.04617, 14104 -> 14100)."""
    return float(f'{v:.4g}')


def _short_label(text):
    """A database's label as the line names it ('->' as '→', no closing period), at most LABEL_MAX characters with ' …'
    at the cut: at a word, unless that would drop more than a third of the room (a long substrate name is cut inside)."""
    t = re.sub(r'\s+', ' ', str(text or '')).strip().rstrip('.').replace('->', '→')
    if len(t) <= LABEL_MAX:
        return t
    cut = t[:LABEL_MAX - 2]
    word = cut.rsplit(' ', 1)[0]
    return (word if len(word) >= (LABEL_MAX - 2) * 2 // 3 else cut).rstrip(' ,;:') + ' …'


def database_by_source(metric, c, catlog=None):
    """What each compared database that lists the paper lists for one value (database_check c; catlog: CatLog's number
    in catalog units), in DATABASES order, a database with nothing from the paper (paper_absent) left out (round 9
    brief C4): [{db, kind, value, unit, x, label}]. kind: database_kind. value: that database's own number for this
    value in catalog units to at most 4 significant figures: same (within 2%), same_rounded, corrected and differs (the
    number the line names), same_number_other_label (CatLog's number under its own label), other_number,
    another_measurement; unit as the line writes it; x = value ÷ CatLog's number (4 significant figures). label: the
    label a database lists the same number under (same_number_other_label), at most LABEL_MAX characters. A kind
    without a number (other_values_only, parameter_absent, value_absent) has only db and kind."""
    unit = UNIT_TEXT[METRIC_FIELD[metric][1]]
    labels = {}  # database -> (its number, its label) for the same number under another label
    if c.get('status') == 'same_number_other_label':
        labels.update({s: (c.get('database_value'), c.get('database_label')) for s in c.get('sources') or []})
    for g in c.get('other_labels') or []:
        for s in g.get('sources') or []:
            labels.setdefault(s, (g.get('database_value'), g.get('database_label')))
    out = []
    for s in DATABASES:
        kind = database_kind(c, s)
        if kind == 'paper_absent':
            continue
        v, label = None, None
        if kind == 'same':
            v = (c.get('same_values') or {}).get(s)
        elif kind == 'same_rounded':
            v = ((c.get('rounded') or {}).get(s) or [None])[0]
        elif kind in ('corrected', 'differs'):
            v = c.get('database_value')
        elif kind == 'same_number_other_label':
            v, label = labels.get(s, (None, None))
        elif kind == 'other_number':
            v = (c.get('other_values') or {}).get(s)
        elif kind == 'another_measurement':
            v = (c.get('other_measurement') or {}).get(s)
        e = {'db': s, 'kind': kind}
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0:
            e.update(value=_four(v), unit=unit)
            if isinstance(catlog, (int, float)) and not isinstance(catlog, bool) and math.isfinite(catlog) and catlog > 0:
                e['x'] = _four(v / catlog)
        if label:
            e['label'] = _short_label(label)
        out.append(e)
    return out


def database_paper_sources(w):
    """The compared databases that list any kcat, Km or kcat/Km from a record's paper, in DATABASES order (round 9
    brief C5): [] when the paper is in none of them; None when none of the record's values was compared (a calculated
    kcat/Km and a value over a mass concentration are not) or the export does not say (an export before dbcompare
    named paper_sources)."""
    checks = [c for m, c in (w.get('database_check') or {}).items()
              if m not in mass_metrics(w) and c.get('status') not in (None, '', 'not_compared')]
    if any(c.get('paper_not_in_databases') for c in checks):
        return []
    listed = {s for c in checks for s in c.get('paper_sources') or ()}
    return [s for s in DATABASES if s in listed] or None


def database_kind(c, s):
    """How database s lists a compared value (database_check c): same (the same number, within 2%), same_rounded (to
    one or two significant figures), corrected / differs (the number named on a corrected or differing line),
    same_number_other_label, other_number (another number for this value at an exact factor, or within 2% of the one
    named), another_measurement (a check against the paper found its number to be another measurement),
    other_values_only (other numbers of this parameter for the paper only), parameter_absent (none of this parameter for
    the paper), value_absent (it lists the paper, not this value: a new value), paper_absent (nothing from the paper).
    No kind is the name of a private database_check field (other_values, other_measurement): the manifest carries these
    counts, and the build's leak check (LEAK) stops any such name as a key."""
    st = c.get('status')
    if c.get('paper_not_in_databases') or s not in (c.get('paper_sources') or [s]):
        return 'paper_absent'
    if st == 'new':
        return 'value_absent'
    if s in (c.get('rounded') or {}):
        return 'same_rounded'
    if s in (c.get('sources') or []):
        return {'confirmed': 'same'}.get(st, st)
    if any(s in g['sources'] for g in c.get('other_labels') or []):
        return 'same_number_other_label'
    if s in (c.get('other_values') or {}):
        return 'other_number'
    if s in (c.get('other_measurement') or {}):
        return 'another_measurement'
    if s in (c.get('other_numbers') or []):
        return 'other_values_only'
    if s in (c.get('no_metric') or []):
        return 'parameter_absent'
    return 'other_values_only'


SUMMARY = {'confirmed': 'same', 'corrected': 'corrected', 'differs': 'differs', 'same_number_other_label': 'other_label',
           'new': 'new'}


KINDS = ('same', 'corrected', 'differs', 'other_label', 'new')  # database_kinds' order


def database_kinds(w):
    """Every kind among a record's printed values compared with databases (a calculated kcat/Km and a value over a mass
    concentration are not compared), each once in KINDS order: ['same', 'new'] for a record with a confirmed Km and a
    new kcat/Km. The site's filter matches 'has a new value' or 'has a correction' with it, which database_summary's
    'mixed' cannot (7,206 records with a new value were 'mixed' on 2026-10-13). [] when nothing was compared."""
    checks = w.get('database_check') or {}
    kinds = {SUMMARY.get(c.get('status')) for m, c in checks.items() if m not in mass_metrics(w) and c.get('reason') != 'calculated'}
    return [k for k in KINDS if k in kinds]


def database_summary(w):
    """One word per record for the site's filter, the Table download and the Stats: its printed values (a calculated
    kcat/Km and a value over a mass concentration are not compared) compared with databases. same: every one is the
    same number as a database lists for the paper; corrected: every one corrects a database number; differs: a
    database lists another number, cause not yet known (an exact factor nobody checked included); other_label: the same number under another substrate, variant or
    organism; new: none of the databases lists any of them for the paper (a new measurement); mixed: values of more than one of
    these kinds (database_kinds lists them); not_compared: nothing was compared."""
    kinds = database_kinds(w)
    return kinds[0] if len(kinds) == 1 else 'mixed' if kinds else 'not_compared'


CONC_PREFIX = re.compile(r'(?<![A-Za-z])([nµμupf]?|m)M(?![A-Za-z])')  # 'mM', 'µM', 'M' in 'M^-1 s^-1'; never 'MgATP', 'KM'
# JBC's small capitals as a unit of their own: 'mm', 'μm', 'nm', 'm^{−1} s^{−1}' (read only when no capital M is printed)
SMALL_CAPS = re.compile(r'(?<![A-Za-zµμ])([nµμupm]?)m(?![A-Za-z])')
PREFIX_POWER = {'': 0, 'm': 3, 'µ': 6, 'μ': 6, 'u': 6, 'n': 9, 'p': 12, 'f': 15}
SUP_DIGITS = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻−–‒', '0123456789----')


def prefix_differs(raw_unit, ufc):
    """The printed unit's concentration prefix is not the one CatLog converted with (unit_for_conversion): 'µM' printed,
    'mM' used; 's^-1 M^-1' printed, 'mM-1 s-1' used; JBC's small capitals 'mm' printed, 'uM' used. A power of ten
    printed in the unit that accounts for the difference ('10^6 Km (M)' read as µM, '× 10^3 M' as mM) is a header, not
    a different prefix."""
    raw, used = (str(u or '').translate(SUP_DIGITS) for u in (raw_unit, ufc))
    p, u = ({PREFIX_POWER[x] for x in CONC_PREFIX.findall(t)} for t in (raw, used))
    p = p or {PREFIX_POWER[x] for x in SMALL_CAPS.findall(raw)}  # 16595681: 'mm' printed (small capitals), µM used
    if not p or not u or p == u:
        return False
    powers = {abs(int(n)) for n in re.findall(r'10\s*\^\s*[({]?\s*(-?\d+)', raw)}
    return not {abs(a - b) for a in p for b in u} & powers


# the compared databases for the manifest's database_comparison.sources (round 9 brief C7), the comparison download and
# the README: the site's key (the manifest's source_databases keys; Browse's dbsrc), the name the values'
# database_sources write, the display name, and the file each database's values come from (tools/db_values.py's inputs;
# its name stays private: only its SHA-256 is published)
SOURCE_DISPLAY = {'STRENDA': 'STRENDA DB'}
SOURCE_FILES = {'BRENDA': 'sources/brenda_2026_1.json.tar.gz', 'SABIO-RK': 'sources/sabio_rk_entries.jsonl.gz',
                'OED': 'sources/oed_export_*.csv', 'SKiD': 'sources/skid/Main_dataset_v1.xlsx',
                'STRENDA': 'sources/strenda/STRENDA_Claude_handoff.zip', 'UniProt': 'sources/ref/uniprot_kinetics.json.gz'}
SKID_RECORD = 'Zenodo 15355031'  # the SKiD dataset's Zenodo record (one record per dataset version)


def source_key(name):
    """'SABIO-RK' -> 'sabio_rk': a database's key, as the manifest's source_databases and Browse's dbsrc write it."""
    return re.sub(r'[\s-]+', '_', str(name).strip().lower())


def _source_version(name, f):
    """(version, retrieved) of a compared database from the file its values come from: what the file says of itself
    (BRENDA's release in its name, OED's export date in its name, UniProt's release and download date inside it; SKiD:
    its Zenodo record), else the file's date on disk, the day that copy was taken (SABIO-RK's export, the STRENDA DB
    snapshot). A release that names its data (BRENDA, SKiD) gets no date; None when not known."""
    day = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d')
    if name == 'BRENDA':
        m = re.search(r'(\d{4})_(\d+)', f.name)
        return (f'{m[1]}.{m[2]}' if m else None), (None if m else day)
    if name == 'OED':
        m = re.search(r'(20\d\d)(\d\d)(\d\d)', f.name)
        return None, f'{m[1]}-{m[2]}-{m[3]}' if m else day
    if name == 'SKiD':
        return SKID_RECORD, None
    if name == 'UniProt':
        try:
            with gzip.open(f, 'rt') as fh:
                head = json.load(fh)
            return (str(head['release']) if head.get('release') else None), str(head.get('downloaded') or day)[:10]
        except (OSError, ValueError, AttributeError):
            return None, day
    return None, day


def compared_sources(root=None):
    """The compared databases in DATABASES order (round 9 brief C7), each that has values in sources/db_values.tsv (a
    database with none in this build is not compared, so not listed): [{key, name, display, version, retrieved, rows,
    papers, sha256}]. rows: its values there (kcat, Km and kcat/Km with a paper id, in the units above), papers: the
    papers they cite; version and retrieved as _source_version gives them (None when not known); sha256: the file the
    values come from (SOURCE_FILES), left out when it is not on disk."""
    root = Path(root or ROOT)
    rows, papers = Counter(), {s: set() for s in DATABASES}
    p = root / 'sources' / 'db_values.tsv'
    if p.exists():
        with open(p) as fh:
            next(fh, None)
            for line in fh:
                f = line.split('\t', 2)
                if len(f) > 2 and f[0] in papers:
                    rows[f[0]] += 1
                    papers[f[0]].add(f[1])
    out = []
    for s in DATABASES:
        if not rows[s]:
            continue
        e = {'key': source_key(s), 'name': s, 'display': SOURCE_DISPLAY.get(s, s), 'version': None, 'retrieved': None,
             'rows': rows[s], 'papers': len(papers[s])}
        found = sorted(root.glob(SOURCE_FILES[s])) if s in SOURCE_FILES else []
        if found:  # the newest, as db_values.py takes OED's
            e['version'], e['retrieved'] = _source_version(s, found[-1])
            e['sha256'] = sha(found[-1])
        out.append(e)
    return out


def publication_years(root=None, online=True, papers=None):
    """The manifest's summary.publication_years (round 16 brief section 1): CatLog's values per publication year beside
    BRENDA 2026.1's, from tools/publication_years.py (catalog.jsonl as of now; PubMed dates cached, only new papers
    fetched). Only the values of `papers`, the papers the site shows from CatLog (build passes _v2_done's, so the totals
    are those of the records read from the paper; None: papers.tsv's done papers); dated today (UTC) until build dates
    it by the snapshot's day (dated_publication_years). None, with a line saying why, when it cannot be made: missing
    years never fail a build (the page then leaves the figure out)."""
    try:
        mod = _load('publication_years', ROOT / 'tools' / 'publication_years.py')
        out = mod.summary(root or ROOT, online=online, log=lambda m: print('  ' + m), papers=papers)
    except Exception as e:  # a missing file, a bad line, anything: the build goes on without the figure
        print(f'  publication years left out of the manifest: {type(e).__name__}: {e}')
        return None
    dated = sum(y['catlog_values'] for y in out['years'])
    print(f"  publication years {out['first_year']}-{out['last_year']}: {dated:,} of {out['catlog_values_total']:,} CatLog "
          f"values; {out['catlog_after_last_year']['values']:,} after, {out['catlog_values_without_year']:,} without a year")
    return out


def dated_publication_years(path, manifest, pub):
    """summary.publication_years dated by the snapshot's own day, the manifest's generated_at (UTC), as the page and
    the release date the snapshot: the exporter sets it after the years were counted, so a build running past midnight
    UTC would otherwise give the day before. Rewrites the bundle's manifest.js (path) only when its summary carries the
    years as written and the day differs; returns (manifest, years)."""
    day = str(manifest.get('generated_at') or '')[:10]
    summary = manifest.get('summary') or {}
    if not pub or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) or pub.get('as_of') == day \
            or summary.get('publication_years') != pub:
        return manifest, pub
    pub = {**pub, 'as_of': day}
    return _manifest_set(path, 'summary', {**summary, 'publication_years': pub}), pub


def database_stats(rows, papers, compared=None):
    """Counts for the Stats figures (contribution report 2.3) from the CatLog measurements this build shows (rows) and
    the export's per-paper counts of database rows CatLog does not reproduce (work/database_compare.json, summed over
    the build's papers, those with no values included). Exact counts, not the report's sample rates."""
    if compared is None:
        p = ROOT / 'work' / 'database_compare.json'
        compared = json.loads(p.read_text()) if p.exists() else {}
    values = {m: Counter() for m in ('kcat', 'Km', 'kcat/Km', 'all')}
    not_listed = {m: Counter() for m in values}  # values no compared database lists, by database_new_reason
    by_cause, by_db, by_cause_db, by_who, diff_cause = Counter(), Counter(), {}, Counter(), Counter()
    by_cause_found, by_metric_cause_db = {}, {m: {} for m in ('kcat', 'Km', 'kcat/Km')}
    per_db = {s: Counter() for s in DATABASES}  # each compared value as each database lists it (database_kind)
    new_sets, new_form, new_set_form, recs = Counter(), Counter(), Counter(), Counter()
    for w in rows:  # a Km or kcat/Km over a mass concentration is not compared (dbcompare) and not on the site
        checks = {m: c for m, c in (w.get('database_check') or {}).items() if m not in mass_metrics(w)}
        if 'kcat/Km' not in checks and w.get('kcat_over_km') is not None and \
                str(w.get('kcat_over_km_source') or '').startswith('derived'):
            # the kcat/Km the site shows, calculated from kcat and an mM Km, next to a kcat/Km printed over a mass
            # concentration (database_check's kcat/Km): not compared, as the comparison download counts it
            checks['kcat/Km'] = {'status': 'not_compared', 'reason': 'calculated'}
        printed = {m: c for m, c in checks.items() if c.get('reason') != 'calculated'}
        for m, c in checks.items():
            # new values counted apart: the paper is in none of the databases; a printed kcat/Km whose kcat and Km they list
            key = 'new_paper_not_in_databases' if c.get('paper_not_in_databases') else 'new_ratio_only' if c.get('ratio_only') else c['status']
            values[m][key] += 1
            values['all'][key] += 1
            if c['status'] != 'not_compared':
                for s in DATABASES:
                    per_db[s][database_kind(c, s)] += 1
            if c['status'] == 'new':
                why = database_new_reason(c) or 'not_stated'
                not_listed[m][why] += 1
                not_listed['all'][why] += 1
            if c['status'] == 'differs':  # by cause: exact_factor (not yet checked against the paper), different_measurement
                diff_cause[database_cause(c) or 'cause_not_known'] += 1  # (one database's number was), cause_not_known
            if c['status'] == 'corrected':
                why = c.get('cause') or c.get('relation') or 'not_stated'
                by_cause[why] += 1
                by_who[c.get('cause_by') or 'code'] += 1
                by_cause_found.setdefault(why, Counter())[database_found_by(c)] += 1
                for s in c.get('sources') or ():
                    by_db[s] += 1
                    by_cause_db.setdefault(why, Counter())[s] += 1
                    by_metric_cause_db[m].setdefault(why, Counter())[s] += 1
        st = [c['status'] for c in printed.values()]
        if not st:
            continue
        form = 'wild_type' if w.get('wild_type') is True else 'variant' if w.get('wild_type') is False else 'not_stated'
        if all(s == 'new' for s in st):
            ms = '+'.join(m for m in ('kcat', 'Km', 'kcat/Km') if m in printed)
            new_sets[ms] += 1; new_form[form] += 1; new_set_form[f'{ms}|{form}'] += 1
            recs['every_value_new'] += 1
        recs['any_value_new'] += 'new' in st
        recs['every_value_confirmed'] += all(s == 'confirmed' for s in st)
        recs['corrects_a_database_value'] += 'corrected' in st
        recs['differs_not_yet_resolved'] += 'differs' in st
    summary = Counter(database_summary(w) for w in rows)  # the records' database_summary, as the Table download has it
    with_kind = Counter(k for w in rows for k in database_kinds(w))  # records with at least one value of each kind
    rows_why, distinct_why = Counter(), Counter()
    for p in papers:
        for why, (n, d) in ((compared.get('unreproduced') or {}).get(p) or {}).items():
            rows_why[why] += n; distinct_why[why] += d
    shown = {str(w['pubmed_id']) for w in rows}
    doi = {str(w['pubmed_id']): w.get('doi') for w in rows if w.get('doi')}
    # a paper's notes as numbers (dbcompare's paper_note_parts), under the id the page links it by: its PMID, else its DOI
    notes = [{'paper': p if p.isdigit() else doi.get(p) or p, **e}
             for p, parts in sorted((compared.get('paper_note_parts') or {}).items()) if p in shown for e in parts]
    sources = compared_sources()
    names = [e['display'] for e in sources] or [SOURCE_DISPLAY.get(s, s) for s in DATABASES]
    listed = ', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else names[0]
    inputs = {f: sha(ROOT / 'sources' / f) for f in ('db_values.tsv', 'database_corrections.tsv') if (ROOT / 'sources' / f).exists()}
    return {'definition': f'Values read from the paper, compared with {listed} for the same paper (same substrate, '
                          'variant and organism; pH and temperature pair values). A value can count for several '
                          'databases; one database number copied into several databases counts once per value. '
                          'values: per parameter and status; new_paper_not_in_databases (the paper is in none of the '
                          'compared databases) and new_ratio_only (a printed kcat/Km whose kcat and Km they list) are '
                          'counted apart from new. values_by_database: each compared value as each database lists it '
                          '(same, same_rounded, corrected, differs, same_number_other_label, other_number, '
                          'another_measurement, other_values_only, parameter_absent, value_absent, paper_absent). '
                          'values.not_listed_by_reason: the values no compared database lists, per parameter and all, by '
                          'reason (paper_not_in_databases, metric_absent, substrate_absent, variant_absent, '
                          'condition_absent, ratio_only). corrections.by_cause_found_by: each cause by how it was found '
                          '(paper_check, factor_cross_checked); corrections.by_metric_cause_database: per parameter, each '
                          'cause by database. differences.by_cause: the values that differ, by cause (exact_factor: an '
                          'exact factor found automatically, nothing else checked yet; different_measurement: an AI check '
                          'of the paper found one database number to be another measurement while another differs; '
                          'cause_not_known). sources: the compared databases in order, each with key, name, display '
                          'name, version, retrieval date, values (rows), cited papers and the SHA-256 of the file '
                          'compared. database_notes: a database that lists a paper\'s values at one factor throughout, per '
                          'database and parameter: n of its values at that factor, of its values for that parameter, the '
                          'factor and whether the database is lower or higher. papers_read: the papers CatLog read that '
                          'gave values, with a record on the site; papers_compared: those with a compared value; '
                          'papers_finished: every paper CatLog finished, those that gave no value included. '
                          'inputs: the SHA-256 of the values table compared (db_values.tsv) and of the recorded AI '
                          'checks of the paper (database_corrections.tsv).',
            'values': {**{m: dict(c) for m, c in values.items()},
                       'not_listed_by_reason': {m: dict(c.most_common()) for m, c in not_listed.items()}},
            'corrections': {'values': sum(by_cause.values()), 'by_cause': dict(by_cause.most_common()), 'by_database': dict(by_db.most_common()),
                            'by_cause_database': {k: dict(v) for k, v in by_cause_db.items()}, 'by': dict(by_who),
                            'by_cause_found_by': {k: {f: v[f] for f in FOUND_BY if v[f]} for k, v in by_cause_found.items()},
                            'by_metric_cause_database': {m: {k: {s: v[s] for s in DATABASES if v[s]} for k, v in d.items()}
                                                         for m, d in by_metric_cause_db.items()}},
            'differences': {'values': sum(diff_cause.values()), 'by_cause': dict(diff_cause.most_common())},
            'new_measurements': {'every_value_new': recs['every_value_new'], 'by_parameters': dict(new_sets.most_common()),
                                 'by_form': dict(new_form), 'by_parameters_form': dict(new_set_form.most_common())},
            'values_by_database': {s: dict(c.most_common()) for s, c in per_db.items()},
            'records': dict(recs),
            'records_by_summary': {k: summary[k] for k in ('same', 'corrected', 'differs', 'other_label', 'new', 'mixed', 'not_compared')},
            'records_with_kind': {k: with_kind[k] for k in KINDS},
            'not_reproduced': {'rows': dict(rows_why.most_common()), 'distinct': dict(distinct_why.most_common())},
            'papers_not_in_databases': [p for p in compared.get('papers_not_in_databases') or [] if p in shown],
            'papers_finished': len(papers),  # the Guide once showed this as the papers compared (2026-10-15): renamed
            'papers_read': len(shown),  # papers read that gave values (build.json v2_papers_with_values is the same)
            'papers_compared': len({str(w['pubmed_id']) for w in rows if any(
                c.get('status') not in (None, '', 'not_compared') for m, c in (w.get('database_check') or {}).items()
                if m not in mass_metrics(w))}),
            'sources': sources,
            'database_notes': notes,
            'inputs': inputs,
            # only a difference of this many-fold or more is checked against the paper (dbcompare.SMALL_FACTOR), so the
            # corrections are a lower bound on the databases' errors (item 6 of work/publication_strategy_20261021/
            # FIXES_FOR_MAIN_CHAT.md)
            **({'checked_from_factor': SMALL_FACTOR} if SMALL_FACTOR else {})}



# The comparison download (round 9 brief section 6, C10): long format, so it stays the same shape when databases are
# added. One row per value read from the paper and database that lists its paper (database_by_source), one row with the
# database empty for a value no compared database lists (and for one not compared), one per kcat/Km CatLog calculated
# (not_compared). Written by `site build` from the bundle's Full data, so its words are the page's; the manifest names it
# database_comparison_download {path, sha256, size_bytes, rows, format}.
COMPARISON_STEM = 'catlog-database-comparison'
COMPARISON_KEY = 'database_comparison_download'
COMPARISON_COLUMNS = ('data_id', 'snapshot_date', 'record_key', 'measurement_id', 'pubmed_id', 'doi', 'enzyme', 'ec_number',
                      'organism', 'variant', 'substrate', 'parameter', 'catlog_value', 'catlog_unit', 'as_printed',
                      'location', 'result', 'found_by', 'cause', 'not_listed_reason', 'database', 'database_version',
                      'database_retrieved', 'database_kind', 'database_value', 'database_unit', 'factor', 'database_label',
                      'review_result', 'review_round', 'line')
RESULT = {'confirmed': 'same', 'same_number_other_label': 'same_other_label', 'corrected': 'corrects', 'differs': 'differs',
          'new': 'not_listed', 'not_compared': 'not_compared'}  # database_status -> the download's result (brief section 2)
METRICS = ('kcat', 'Km', 'kcat/Km')
PLAIN_NUMBER = re.compile(r'\d+(?:\.\d+)?')


def _csv_num(v):
    """A number for the CSV: 15 significant figures at most, never a float's noise (0.30000000000000004 -> 0.3)."""
    return format(v, '.15g') if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else ''


def _shown(display, value):
    """CatLog's number as the page shows it ('135.0' keeps the printed figures), else the stored number."""
    return display if isinstance(display, str) and PLAIN_NUMBER.fullmatch(display) else _csv_num(value)


def comparison_rows(r, sources, data_id, date, measurement_id=None, tally=None):
    """The comparison download's rows (dicts over COMPARISON_COLUMNS) of one record of the Full data (r, read from the
    paper by CatLog); sources: the manifest's database_comparison.sources by name. tally (a Counter) counts what was
    written and the odd cases (a printed value without a comparison, a compared value no database row names)."""
    tally = tally if tally is not None else Counter()
    sig = r.get('mutation_signature')
    base = {'data_id': data_id, 'snapshot_date': date, 'record_key': r.get('record_key') or '',
            'measurement_id': measurement_id or r.get('measurement_key') or r.get('record_key') or '',
            'pubmed_id': r.get('pubmed_id') or '', 'doi': r.get('doi') or '', 'enzyme': r.get('enzyme_display_name') or '',
            'ec_number': r.get('ec_number') or '', 'organism': r.get('organism') or '',
            'variant': 'wild type' if r.get('wild_type') is True else '' if not sig or sig == 'Unknown' else sig,
            'substrate': r.get('substrate_name') or ''}
    lines = [x for x in r.get('proof_lines') or [] if isinstance(x, dict) and x.get('metric') in METRICS]
    for x in sorted(lines, key=lambda x: METRICS.index(x['metric'])):
        m, st = x['metric'], x.get('database_status') or 'not_compared'
        if not x.get('database_status'):
            tally['printed value without a comparison (not_compared)'] += 1
        v = {**base, 'parameter': m, 'catlog_value': _shown(x.get('value_display'), x.get('normalized_value')),
             'catlog_unit': UNIT_TEXT[METRIC_FIELD[m][1]], 'as_printed': x.get('printed') or '',
             'location': '; '.join(t for t in (x.get('table_label'), x.get('row_label')) if t),
             'result': RESULT.get(st, st), 'found_by': x.get('database_found_by') or '', 'cause': x.get('database_cause') or '',
             'not_listed_reason': x.get('database_new_reason') or '', 'line': x.get('database_line') or ''}
        tally['values ' + v['result']] += 1
        per = [e for e in x.get('database_by_source') or [] if isinstance(e, dict) and e.get('db')] \
            if st not in ('new', 'not_compared') else []
        if not per:
            if st not in ('new', 'not_compared'):
                tally['compared value with no database named (one row, database empty)'] += 1
            yield v
            continue
        for e in per:
            src = sources.get(e['db']) or {}
            yield {**v, 'database': src.get('display') or SOURCE_DISPLAY.get(e['db'], e['db']),
                   'database_version': src.get('version') or '', 'database_retrieved': src.get('retrieved') or '',
                   'database_kind': e.get('kind') or '', 'database_value': _csv_num(e.get('value')),
                   'database_unit': e.get('unit') or '', 'factor': _csv_num(e.get('x')), 'database_label': e.get('label') or ''}
    if r.get('kcat_over_km_origin') == 'calculated' and _csv_num(r.get('kcat_over_km')):
        tally['values not_compared (calculated kcat/Km)'] += 1
        yield {**base, 'parameter': 'kcat/Km', 'catlog_value': _shown(r.get('kcat_over_km_display'), r.get('kcat_over_km')),
               'catlog_unit': UNIT_TEXT[METRIC_FIELD['kcat/Km'][1]], 'result': 'not_compared', 'line': CALCULATED_LINE}


def comparison_csv(enriched, out_dir, manifest, measurement_ids=None):
    """Write the comparison download from the bundle's Full data (enriched) into out_dir as
    catlog-database-comparison.<sha12>.csv.gz (UTF-8 CSV, gzip without a name or time, so the same rows give the same
    bytes) and return ({path, sha256, size_bytes, rows, format}, tally). measurement_ids: record_key -> the export's
    measurement_id (build renames a repeated key)."""
    dc = (manifest.get('summary') or {}).get('database_comparison') or {}
    sources = {e['name']: e for e in dc.get('sources') or []}
    data_id, date = manifest['content_sha256'][:10], manifest['generated_at'][:10]
    tmp, n, tally = out_dir / f'{COMPARISON_STEM}.csv.gz.tmp', 0, Counter()
    with open(tmp, 'wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz, \
            io.TextIOWrapper(gz, encoding='utf-8', newline='') as fh, gzip.open(enriched, 'rt', encoding='utf-8') as src:
        cw = csv.DictWriter(fh, COMPARISON_COLUMNS, lineterminator='\n')
        cw.writeheader()
        for line in src:
            if V2_METHOD not in line:  # cheap: only records read from the paper by CatLog are compared
                continue
            r = json.loads(line)
            if not str(r.get('verification_method') or '').startswith(V2_METHOD):
                continue
            tally['records'] += 1
            for row in comparison_rows(r, sources, data_id, date, (measurement_ids or {}).get(r.get('record_key')), tally):
                cw.writerow(row)
                n += 1
    digest = sha(tmp)
    path = out_dir / f'{COMPARISON_STEM}.{digest[:12]}.csv.gz'
    tmp.replace(path)
    return {'path': f'{out_dir.name}/{path.name}', 'sha256': digest, 'size_bytes': path.stat().st_size, 'rows': n,
            'format': 'csv.gz'}, tally


# Values a paper reports as not detected, or prints only as a bound (catlog.py "censored values", bounds.jsonl; the user,
# 2026-10-25: a dead mutant's 'ND' is worth showing). Their own download, one line each: never in the Full data's value
# columns, its charts, counts or the database comparison. record_key names the record they sit beside when there is one
# (the export's catlog_bounds.jsonl measurement_id). The manifest names it not_detected_download {path, sha256,
# size_bytes, rows, papers, format}; the page that shows them is the new site's (work/website_next).
NOT_DETECTED_STEM = 'catlog-not-detected'
NOT_DETECTED_KEY = 'not_detected_download'
NOT_DETECTED_COLUMNS = ('data_id', 'snapshot_date', 'record_key', 'pubmed_id', 'doi', 'enzyme', 'ec_number', 'organism', 'uniprot_id',
                        'variant', 'construct', 'substrate', 'parameter', 'reported', 'limit_value', 'limit_unit',
                        'as_printed', 'detection_limit_as_printed', 'location', 'printed_line', 'ph', 'temperature_c',
                        'conditions', 'note')
REPORTED = {'not_detected': 'not detected', '<': 'below', '>': 'above'}  # catlog_bounds censored -> the download's words


def not_detected_csv(bounds, out_dir, manifest, record_keys, shown):
    """Write the not-detected download from the export's catlog_bounds.jsonl (bounds) into out_dir as
    catlog-not-detected.<sha12>.csv.gz (UTF-8 CSV, gzip without a name or time) and return its manifest entry, or None
    when there is none. record_keys: the export's measurement_id -> the record_key the site gives that record; shown:
    the papers the site shows from CatLog (only their values are published)."""
    if not bounds.exists():
        return None
    data_id, date = manifest['content_sha256'][:10], manifest['generated_at'][:10]
    tmp, n, papers = out_dir / f'{NOT_DETECTED_STEM}.csv.gz.tmp', 0, set()
    with open(tmp, 'wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz, \
            io.TextIOWrapper(gz, encoding='utf-8', newline='') as fh:
        cw = csv.DictWriter(fh, NOT_DETECTED_COLUMNS, lineterminator='\n')
        cw.writeheader()
        for line in sorted(l for l in open(bounds, encoding='utf-8') if l.strip()):  # the same rows give the same bytes
            b = json.loads(line)
            if str(b.get('pubmed_id')) not in shown or b.get('censored') not in REPORTED:
                continue
            unit = METRIC_FIELD.get(b['metric'], (None, None))[1]
            cw.writerow({'data_id': data_id, 'snapshot_date': date,
                         'record_key': record_keys.get(b.get('measurement_id') or '', ''),
                         'pubmed_id': b['pubmed_id'], 'doi': b.get('doi') or '', 'enzyme': b.get('enzyme_name') or '',
                         'ec_number': b.get('ec_number') or '',
                         'organism': b.get('organism') or '', 'uniprot_id': b.get('uniprot_id') or '',
                         'variant': b.get('variant') or '', 'construct': b.get('construct') or '',
                         'substrate': b.get('substrate_name') or '', 'parameter': b['metric'],
                         'reported': REPORTED[b['censored']], 'limit_value': _csv_num(b.get('bound')),
                         'limit_unit': UNIT_TEXT[unit] if b.get('bound') is not None and unit and b.get('bound_unit') in
                         (None, '', catlog_unit(b['metric'])) else (b.get('bound_unit') or '') if b.get('bound') is not None else '',
                         'as_printed': ' '.join(x for x in (b.get('raw_value') or '', b.get('raw_unit') or '') if x).translate(PDF_GLYPHS),
                         'detection_limit_as_printed': (b.get('limit') or '').translate(PDF_GLYPHS),
                         'location': LOCAL_PATH.sub('', b.get('location') or ''),
                         'printed_line': (b.get('quote') or '').translate(PDF_GLYPHS),
                         'ph': _csv_num(b.get('ph')), 'temperature_c': _csv_num(b.get('temperature_c')),
                         'conditions': b.get('conditions') or '', 'note': b.get('metric_note') or ''})
            n += 1
            papers.add(str(b['pubmed_id']))
    if not n:
        tmp.unlink()
        return None
    digest = sha(tmp)
    path = out_dir / f'{NOT_DETECTED_STEM}.{digest[:12]}.csv.gz'
    tmp.replace(path)
    return {'path': f'{out_dir.name}/{path.name}', 'sha256': digest, 'size_bytes': path.stat().st_size, 'rows': n,
            'papers': len(papers), 'format': 'csv.gz'}


# One value per row of the records read from the paper (2026-10-26, the website chat's data review: ML users of
# DLKcat, TurNuP and CatPred expect a flat file, and the Full data nests three values per record). Written from the
# bundle's Full data, so every field is what the site shows; records read from the paper only: CatLog's reading is CC BY
# 4.0, and a substrate structure keeps its source's terms (smiles_source; SKiD's are CC BY-NC-ND). The sequence is the
# measured enzyme's only (sequence_resolved): where CatLog has none, the Full data shows the canonical one, which for a
# mutant is the wild type's (review 2026-10-26: 13,162 mutant values had it). Manifest values_download {path, sha256,
# size_bytes, rows, calculated (the lines of a kcat/Km worked out from kcat and Km, value_origin calculated: the site's
# 'values' are the printed ones, rows - calculated; 2026-11-06 Stats audit X2), records, format}. Sequence
# clusters (MMseqs2) are left out: heavy compute runs on Nova, not this Mac.
VALUES_STEM = 'catlog-values'
VALUES_KEY = 'values_download'
VALUES_COLUMNS = ('data_id', 'snapshot_date', 'record_key', 'pubmed_id', 'doi', 'ec_number', 'ec_source', 'enzyme', 'organism',
                  'organism_source', 'taxon_id', 'uniprot_id', 'wild_type', 'mutation_signature', 'sequence', 'substrate',
                  'smiles', 'smiles_source', 'substrate_inchikey', 'substrate_chebi', 'substrate_pubchem_cid', 'parameter',
                  'value', 'log10_value', 'unit', 'err', 'value_origin', 'ph', 'temperature_c', 'conditions',
                  'verification_status', 'accepted_basis', 'condition_flags')
VALUE_FIELDS = (('kcat', 'kcat', 'kcat_err'), ('Km', 'km', 'km_err'), ('kcat/Km', 'kcat_over_km', 'kcat_over_km_err'))


def values_csv(enriched, out_dir, manifest):
    """Write the values download from the bundle's Full data (enriched) into out_dir as catlog-values.<sha12>.csv.gz
    (UTF-8 CSV, gzip without a name or time) and return its manifest entry."""
    data_id, date = manifest['content_sha256'][:10], manifest['generated_at'][:10]
    tmp, n, recs, calc = out_dir / f'{VALUES_STEM}.csv.gz.tmp', 0, 0, 0
    with open(tmp, 'wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz, \
            io.TextIOWrapper(gz, encoding='utf-8', newline='') as fh, gzip.open(enriched, 'rt', encoding='utf-8') as src:
        cw = csv.DictWriter(fh, VALUES_COLUMNS, lineterminator='\n')
        cw.writeheader()
        for line in src:
            if V2_METHOD not in line:
                continue
            r = json.loads(line)
            if not str(r.get('verification_method') or '').startswith(V2_METHOD):
                continue
            recs += 1
            sig = r.get('mutation_signature')
            base = {'data_id': data_id, 'snapshot_date': date, 'record_key': r.get('record_key') or '',
                    'pubmed_id': r.get('pubmed_id') or '', 'doi': r.get('doi') or '', 'ec_number': r.get('ec_number') or '',
                    'ec_source': r.get('ec_source') or '', 'enzyme': r.get('enzyme_display_name') or '',
                    'organism': r.get('organism') or '', 'organism_source': r.get('organism_source') or '',
                    'taxon_id': r.get('taxon_id') or '', 'uniprot_id': r.get('uniprot_id') or '',  # CatLog's own (isoform kept)
                    'wild_type': '' if r.get('wild_type') is None else str(bool(r['wild_type'])).lower(),
                    'mutation_signature': '' if not sig or sig == 'Unknown' else sig,
                    'sequence': (r.get('sequence') or '') if r.get('sequence_resolved') is True else '',
                    'substrate': r.get('substrate_name') or '', 'smiles': r.get('smiles') or '',
                    'smiles_source': r.get('smiles_source') or '',
                    'substrate_inchikey': r.get('substrate_inchikey') or '', 'substrate_chebi': r.get('substrate_chebi') or '',
                    'substrate_pubchem_cid': r.get('substrate_pubchem_cid') or '', 'ph': _csv_num(r.get('ph')),
                    'temperature_c': _csv_num(r.get('temperature_c')), 'conditions': r.get('assay_conditions_summary') or '',
                    'verification_status': r.get('verification_status') or '',
                    'accepted_basis': r.get('accepted_basis') or '',
                    'condition_flags': '; '.join(str(x) for x in r.get('condition_flags') or [])}
            for metric, field, err in VALUE_FIELDS:
                v = r.get(field)
                if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0:
                    continue
                origin = ('calculated' if r.get('kcat_over_km_origin') == 'calculated' else 'printed') if field == 'kcat_over_km' else 'printed'
                cw.writerow({**base, 'parameter': metric, 'value': _csv_num(v), 'log10_value': _csv_num(round(math.log10(v), 6)),
                             'unit': r.get(field + '_unit') or '', 'err': _csv_num(r.get(err)), 'value_origin': origin})
                n += 1
                calc += origin == 'calculated'
    digest = sha(tmp)
    path = out_dir / f'{VALUES_STEM}.{digest[:12]}.csv.gz'
    tmp.replace(path)
    return {'path': f'{out_dir.name}/{path.name}', 'sha256': digest, 'size_bytes': path.stat().st_size, 'rows': n,
            'calculated': calc, 'records': recs, 'format': 'csv.gz'}


def catlog_unit(metric):
    """The catalog unit a censored value's limit is stored in (catlog.py: s^-1, mM, mM^-1 s^-1)."""
    return {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}.get(metric)


def _manifest_set(path, key, value):
    """Add one key to a bundle's manifest.js (its first line; the shard-registry lines stay) and return the manifest."""
    first, sep, rest = path.read_text(encoding='utf-8').partition('\n')
    head = first[:first.index('{')]
    m = json.loads(first[len(head):first.rindex(';')])
    m[key] = value
    path.write_text(head + json.dumps(m, ensure_ascii=False, separators=(',', ':')) + ';' + sep + rest, encoding='utf-8')
    return m


# Symbols a PDF's text layer gives at other code points, which most fonts draw as boxes: the printed line the page
# quotes shows them as the paper prints them. The JBC and other ASBMB journals of about 1995-2012 set ±, ×, −, Greek
# letters and more in fonts whose text maps them to '⫾', '⫻', '⫺', '␮' and the like ('18 ⫾ 2', 's⫺1', '␮M', '5⬘'; U+2423
# to U+243B are α to ω in Greek order, U+2435 unknown); Adobe's Symbol and small-capital fonts to private-use characters
# (U+F06D µ, U+F76C a small-capital L). Only code points no enzyme paper prints for themselves; the look-alike CJK
# characters (PDF_CJK) only in a line with no other CJK text.
PDF_GLYPHS = str.maketrans({'⫾': '±', 'ⴞ': '±', '⫻': '×', '⫺': '−', '⫹': '+', '⫽': '=', '⳱': '=', '⬍': '<', '⬎': '>',
                            'ⱕ': '≤', 'ⱖ': '≥', '⬃': '∼', '⬘': '′', '⭈': '·', 'ⴱ': '*', '⌬': 'Δ',
                            '\uf06d': 'µ', '\uf0b1': '±', '\uf0b4': '×', '\uf0d7': '·',
                            **{chr(0x2423 + i): g for i, g in enumerate('αβγδεζηθικλµνξοπρσ')},
                            **{chr(0x2436 + i): g for i, g in enumerate('τυφχψω')},
                            **{chr(0xf761 + i): chr(0x41 + i) for i in range(26)}})
PDF_CJK = str.maketrans({'䡠': '·', '兾': '/', '共': '(', '兲': ')', '关': '[', '兴': ']', '具': '⟨', '典': '⟩'})
CJK = re.compile(r'[\u3400-\u9fff]')
# what a text layer leaves of a symbol it has no character for: control characters, U+FFFD and private-use characters
LOST = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ufffd\ue000-\uf8ff\u2435\u243c-\u243f]')
LOST_NOTE = 'Text extraction dropped some symbols from this line.'


def _stand_ins(evidence):
    """{LOST character: '±' or '×'} from a measurement's quotes and printed cells: the character a quote gives where its
    printed cell has ± ('0.76 \\x06 0.08' for a printed 0.76 ± 0.08; '0.9 \\x8a^ 0.1', a ± drawn as two glyphs) or ×
    before a power of ten ('(4 ± 0.4) \\x02 10-2' for (4 ± 0.4) × 10^-2), the symbol's code in that paper's text layer.
    A character found for both is neither."""
    found = {'±': set(), '×': set()}
    for ev in evidence.values():
        q, raw = str(ev.get('quote') or '').translate(PDF_GLYPHS), str(ev.get('raw_value') or '')
        for a, b in re.findall(r'(\d[\d.,]*)\s*\(?\s*±\s*(\d[\d.,]*)', raw):  # '0.82 ± 0.1', '1.23 (±0.06)'
            for m in re.finditer(rf'(?<![\d.]){re.escape(a)}(\W{{1,10}}?){re.escape(b)}(?!\d)', q):
                found['±'].update(LOST.findall(m.group(1)))
        for a in re.findall(r'(\d[\d.,]*\s*\)?)\s*×\s*10', raw):
            for m in re.finditer(rf'(?<![\d.]){re.escape(a.strip())}(\W{{1,10}}?)10', q):
                found['×'].update(LOST.findall(m.group(1)))
    both = found['±'] & found['×']
    return {c: sym for sym, cs in found.items() for c in cs - both}


# What a text layer gives for a printed ± that also stands between two numbers for itself (a range, a ratio, a power):
# or a digit: said only on the lines of the measurement whose own printed cell showed it, never paper-wide (garbled_notes)
AMBIGUOUS_STAND_INS = set('-−–—:/x×0123456789')


def _letter_stand_ins(evidence):
    """The ordinary characters a measurement's quotes give where its printed cell has ± ('66.7 f 8.3' for a printed
    66.7 ± 8.3; 't', '2', '6', '(' or '+' in other papers; '-c', '+-', '=I=' in older OCR): one character, or two or
    three with a sign among them, between the cell's two numbers. Unlike _stand_ins' codes they stand for themselves
    too, so the line keeps them and says so (garbled_notes; round 16b quality review: 481 records quoted '66.7 f 8.3'
    under "In the paper:"). '|' is CatLog's own cell separator, never one."""
    found = set()
    for ev in evidence.values():
        q, raw = str(ev.get('quote') or '').translate(PDF_GLYPHS), str(ev.get('raw_value') or '')
        for a, b in re.findall(r'(\d[\d.,]*)\s*\(?\s*±\s*(\d[\d.,]*)', raw):
            for m in re.finditer(rf'(?<![\d.]){re.escape(a)} ([^\s±|]|[^\s±|]{{2,3}}) {re.escape(b)}(?!\d|\.\d)', q):
                c = m.group(1)
                if (len(c) == 1 or re.search(r'[-+=−~]', c)) and not LOST.search(c):
                    found.add(c)
    return found


def _garbled_note(line, chars):
    """'The PDF's text layer gives ± as “f” in this line.' for those of `chars` that stand between two numbers in
    this line; '' for none."""
    seen = [c for c in sorted(chars) if re.search(rf'\d {re.escape(c)} \d', line)]
    if not seen:
        return ''
    return f"The PDF's text layer gives ± as {_names_and([f'“{c}”' for c in seen])} in this line."


def garbled_notes(pairs):
    """Under every printed line that shows a ± as another character (_letter_stand_ins), the note saying so: in
    printed_line_note (the page shows it under the quote) and after the line in raw_value_unit_evidence. A text layer
    draws ± the same way throughout a paper, so what any of the paper's measurements shows counts for all its lines,
    except AMBIGUOUS_STAND_INS, which count only on the lines of the measurement that showed them."""
    own = [_letter_stand_ins(w.get('evidence') or {}) for w, _ in pairs]
    paper = defaultdict(set)
    for (w, _), cs in zip(pairs, own):
        paper[str(w.get('pubmed_id'))] |= cs - AMBIGUOUS_STAND_INS
    for (w, r), cs in zip(pairs, own):
        cs = cs | paper.get(str(w.get('pubmed_id')), set())
        if not cs:
            continue
        for e in r.get('proof_lines') or []:
            note = _garbled_note(e['printed_line'], cs) if e.get('printed_line') else ''
            if note:
                e['printed_line_note'] = ' '.join(x for x in (e.get('printed_line_note'), note) if x)
            m = re.search(r'In the paper: “(.*?)”', e.get('raw_value_unit_evidence') or '')
            if m and (note := _garbled_note(m.group(1), cs)):
                e['raw_value_unit_evidence'] += f' {note}'


def _readable(text, stand_ins=None):
    """A line from a paper's text layer with its symbols as the paper prints them: PDF_GLYPHS (and PDF_CJK) restored,
    the measurement's own codes for ± and × (_stand_ins; a '^' drawn beside a ± goes with it), a control character
    between a unit and '1' or after a 10 as a superscript minus ('s\\x041', '10\\x023'; units.clean reads the first so),
    and a C1 control character before a number's decimal point taken out ('0\\x8a.05': units.clean's noise). The other
    LOST characters stay (_kept takes them out, after a long line is cut). The download's raw_value keeps the reader's
    text."""
    t = str(text or '').translate(PDF_GLYPHS)
    if not CJK.search(cjk := t.translate(PDF_CJK)):
        t = cjk
    for c, sym in sorted((stand_ins or {}).items()):
        t = re.sub(rf'(?:\^\s*)?{re.escape(c)}(?:\s*\^)?' if sym == '±' else re.escape(c), sym, t)
    t = re.sub(r'(?<=[A-Za-z)])\s?[\x01-\x08]\s?(?=1(?!\d))|(?<=10)[\x01-\x08](?=\d)', '−', t)
    return re.sub(r'(?<=\d)[\x80-\x9f](?=\.\d)', '', t)


def _kept(text):
    """(text with a space for each LOST character, so that '38\\x038' never reads as one number, whether it had any)."""
    if not LOST.search(text):
        return text, False
    return re.sub(r'(?<=\S) {2,}', ' ', LOST.sub(' ', text)).strip(), True


# fields catlog.py export adds to records read from the paper (2026-10-26), carried to the Full data (not the Table:
# its rows must share one schema for the frozen site's viewer index)
V2_EXTRA = ('substrate_chebi', 'substrate_inchikey', 'substrate_pubchem_cid', 'smiles_source', 'taxon_id', 'organism_source',
            'ec_source', 'kcat_err', 'km_err', 'kcat_over_km_err')


def v2_row(w):
    """One v2 measurement (catlog_wide.jsonl) as an old-catalog row the exporter understands; whitelisted fields only."""
    pmid, doi, wt, seq, acc = str(w['pubmed_id']), w.get('doi') or '', w.get('wild_type'), w.get('sequence') or '', w.get('uniprot_id') or ''
    pmid = pmid if pmid.isdigit() else ''  # a stand-in (NP..., no PMID): the DOI is the paper's public identifier
    doi = re.sub('[\u2010-\u2015\u2212]', '-', doi)  # a typographic dash a reader copied breaks the doi.org link
    seq_note = _seq_note(w)
    # a natural form that shares an entry (or no entry): no sequence, else the exporter shows the canonical one as its own
    canon = '' if seq_note.startswith(NO_SEQ) else _canonical(acc) or (seq if wt else '')
    seq = '' if seq_note.startswith(NO_SEQ) else seq
    parts = _assay_parts(w)  # pH and temperature have their own fields and drawer rows
    for metric, note in (('kcat', 'kcat_note'), ('Km', 'km_note'), ('kcat/Km', 'kcat_over_km_note')):
        parts += _labels(metric, w.get(note))  # one '; '-part each, every one naming its metric
    # a printed kcat/Km that differs from kcat ÷ Km: the page's flag gives both numbers, the factor and the likely cause
    if KI_AS_KM.search(f"{w.get('km_note') or ''}; {w.get('conditions') or ''}"):
        parts.append('Km measured as Ki (by competition with another substrate)')
    for note in ('kcat_note', 'km_note', 'kcat_over_km_note'):  # code's own notes: a condition the paper does not print
        for k, why in NOT_PRINTED.findall(w.get(note) or ''):
            what = 'pH' if k == 'pH' else 'temperature'
            phrase = f'{what} left blank: not confirmed in the paper text' \
                if why.startswith('not printed') else f'{what} left blank: printed only as text or a range'
            if phrase not in parts:
                parts.append(phrase)
    # each value to the significant figures of its printed cell (431 min^-1 -> 7.18 s^-1, not 7.18333); a kcat/Km
    # worked out from kcat and Km to the less precise of the two
    evidence = {k: e for k, e in (w.get('evidence') or {}).items() if k not in mass_metrics(w)}
    val, figs, ufcs, same = {}, {}, {}, {}
    for metric, ev in evidence.items():
        field, unit = METRIC_FIELD[metric]
        corr = ((w.get('reasoning') or {}).get(metric) or {}).get('corrected') or {}
        ufcs[metric] = ev.get('unit_for_conversion') or (corr.get('unit_for_conversion') or {}).get('verifier') or ''
        same[metric] = _unit_key(ufcs[metric] or ev.get('raw_unit')) == _unit_key(unit)  # the number was not converted
        val[field], figs[field] = _printed(w.get(field), ev.get('raw_value'))
        if same[metric] and val[field] != w.get(field):  # a value code did not convert is never changed
            val[field], figs[field] = w.get(field), None
    eff = w.get('kcat_over_km')
    if (w.get('kcat_over_km_source') or '').startswith('derived') and isinstance(eff, (int, float)) and eff:
        n = min((_figures((evidence.get(m) or {}).get('raw_value')) or (6,))[0] for m in ('kcat', 'Km'))
        val['kcat_over_km'], figs['kcat_over_km'] = _sig(eff, n), n
    value = lambda f: val.get(f, w.get(f))
    triple = tuple((_sup(_num(value(f), figs.get(f))), value(f) if isinstance(value(f), (int, float)) else None)
                   for f in ('kcat', 'km', 'kcat_over_km'))  # as shown, for the database line's closure sentence
    proof, seen, given, prefix = [], set(), set(), []
    pm = _stand_ins(w.get('evidence') or {})  # the paper's ± and × in its text layer, where the font has none
    for metric, ev in evidence.items():
        field, unit = METRIC_FIELD[metric]
        corr = ((w.get('reasoning') or {}).get(metric) or {}).get('corrected') or {}
        img, ufc = bool(ev.get('quote_check')), ufcs[metric]
        if ufc and prefix_differs(ev.get('raw_unit'), ufc):
            prefix.append(metric)
        raw = _kept(_readable(_printed_text(ev.get('raw_value'), ev.get('raw_unit'), ufc), pm))[0]
        cell = _kept(_readable(str(ev.get('raw_value') or '').strip(), pm))[0]  # the printed cell alone, as raw
        excerpt, line, lost = '', '', False
        q = re.sub(r'\s+', ' ', _readable(re.sub(r'\s+', ' ', ev.get('quote') or ''), pm)).strip()
        if q and not img:  # only a line code found in the paper text
            if q in seen:
                excerpt = ' (same line as above)'
            else:
                seen.add(q)
                line = q if len(q) <= 240 else (q[:240].rsplit(' | ', 1)[0] if ' | ' in q[:240] else q[:240].rsplit(' ', 1)[0]) + ' …'
                line, lost = _kept(line)  # symbols the text layer lost, said once with the line (LOST_NOTE)
                excerpt = f'. In the paper: “{line}”' if line else ''
        reading = _unit_reading(corr, ev, metric)  # a unit read otherwise than printed, as one phrase
        skip = {'unit_for_conversion', 'raw_unit'} if reading else set()
        as_printed = same[metric] and (not ufc or _unit_key(ev.get('raw_unit')) == _unit_key(unit))
        if reading and as_printed:  # the check's reading was undone since (a unitfix back to the printed unit, 40723313
            reading = ''            # on 2026-11-02): the value is stored as printed, so the check confirmed it (the numbers
                                    # audit, 2026-11-06, N4), and the undone unit is no correction either (skip stays)
        fixed = '; '.join(dict.fromkeys(([reading] if reading else [])
                                        + [x for k, v in corr.items() if k not in skip and (x := _fixed(k, v, metric))]))
        how = (', as printed' if as_printed else
               f', as printed with the unit read as {_unit_sup(ufc)}' if same[metric] else  # a unit corrected to the catalog's
               f", converted from {_unit_sup(cell)} with the unit read as {_unit_sup(ufc)}" if ufc else
               f', converted from {_unit_sup(raw)}')
        shown = f"{_commas(_sup(_num(value(field), figs.get(field))))} {UNIT_TEXT[unit]}" if value(field) is not None else ''
        entry = {'table_label': LOCAL_PATH.sub('', ev.get('location') or ''),
                 # 'Km as printed: 2,400 ± 530 µM. In the paper: “…”.' / 'Km 2.40 mM, converted from 2,400 ± 530 µM.'
                 # (what the second, separate AI check found is the check field, said once)
                 # a quoted line that ends a sentence ends it: '(Fig. 5).”', never '(Fig. 5).”.'
                 'raw_value_unit_evidence': re.sub(r'(?<=[.!?]”)\.$', '', f"{metric} as printed{': ' + _unit_sup(raw) if raw else ''}{excerpt}.")
                                            + (f' {LOST_NOTE}' if lost else ''),
                 'normalized_value_unit_evidence': f'{metric} {shown}{how}.' if shown else '',
                 'metric': metric, 'raw_value': ev.get('raw_value'), 'raw_unit': ev.get('raw_unit'), 'normalized_value': value(field),
                 'normalized_unit': unit, 'pmid': pmid, 'doi': doi,
                 # the same facts, one per field, for the page's table of values (export_site.py lets them through)
                 'printed': raw, 'check': f'corrected: {fixed}' if fixed else 'confirmed',  # an unpublished note change leaves the value confirmed
                 'conversion': '' if as_printed else f'printed unit read as {ufc}' if same[metric] else
                               f'converted by code, printed unit read as {ufc}' if ufc else 'converted by code'}
        if value(field) is not None:  # the value in catalog units as text, to the figures printed ('135.0' stays '135.0')
            entry['value_display'] = str(_num(value(field), figs.get(field)))
        aud = (w.get('audit') or {}).get(ev.get('row_id'))  # an AI audit re-checked this value against the paper
        if aud:
            entry['audit_date'], entry['audit_result'] = aud[0], 'unit corrected' if aud[1] == 'unit corrected' else 'kept'
        if line and line not in given:  # each printed line once, on the first value printed in it (two long lines
            given.add(line)             # can be cut to the same 240 characters)
            entry['printed_line'] = line
            if lost:
                entry['printed_line_note'] = LOST_NOTE
        if img:
            entry['row_label'] = 'read off the page image (scanned paper)'
        dbc = (w.get('database_check') or {}).get(metric)  # against the enzyme databases: fixed phrases only
        if dbc:
            notes = ' '.join(str(v) for v in [dbc.get('evidence') or '', *(((w.get('reasoning') or {}).get(metric) or {}).values())])
            pr = _unit_sup(raw)
            if SCALED_UNIT.search(ev.get('raw_unit') or '') and ILLEGIBLE_SCALE.search(notes):  # 1371328
                dbc, pr = {**dbc, 'unit_inferred': ev.get('raw_unit')}, _unit_sup(cell)
            entry.update(_database_fields(metric, dbc, _sup(entry.get('value_display', '')), pr, _sup(entry['table_label']), triple,
                                          w.get(field)))
        proof.append(entry)
    src = w.get('kcat_over_km_source') or ''
    row = {'measurement_key': w['measurement_id'], 'review_key': w['measurement_id'], 'pubmed_id': pmid, 'supporting_pmids': [pmid] if pmid else [],
           'doi': doi, 'supporting_dois': [doi] if doi else [], 'ec_number': w.get('ec_number') or '',
           'enzyme_name': w.get('enzyme_name') or '', 'enzyme_name_source': 'source_record', 'organism': w.get('organism') or '',
           'substrate_name': w.get('substrate_full_name') or w.get('substrate_name') or '', 'uniprot_id': acc,
           'uniprot_candidate_ids': [] if acc else list(w.get('uniprot_candidates') or []), 'wild_type': wt,
           'mutation_type': mutation_type(w.get('mutation_signature'), wt), 'mutation_signature': w.get('mutation_signature') or None,
           'sequence': seq, 'canonical_sequence': canon, 'sequence_resolved': bool(seq),
           'sequence_variant_status': ('canonical_wild_type_sequence' if wt else 'reconstructed_variant_sequence') if seq else
                                      'unspecified' if wt or not acc else 'canonical_sequence_pending_mutation_application',
           'sequence_source': 'uniprot_accession' if acc and seq else '', 'sequence_variant_note': seq_note,
           'smiles': w.get('smiles') or '',
           # cross-reference IDs and printed errors (catlog.add_ids, printed_err; export_site.py puts them on the record): CatLog's own read of the paper only
           **{f: w.get(f) for f in V2_EXTRA if w.get(f) not in (None, '')},
           'kcat': value('kcat'), 'kcat_unit': 's^(-1)' if w.get('kcat') is not None else '',
           'km': value('km'), 'km_unit': 'mM' if w.get('km') is not None else '',
           'kcat_over_km': value('kcat_over_km'), 'kcat_over_km_unit': 's^(-1)*mM^(-1)' if w.get('kcat_over_km') is not None else '',
           'kcat_over_km_provenance': {'kind': 'primary_reported'} if src == 'printed' else
                                      {'kind': 'derived_same_measurement'} if src.startswith('derived') else None,
           'kcat_over_km_agreement': _kcat_km_agreement(w),  # read by export_site.py only; not published
           # read by export_site.py only: the condition flag printed_unit_prefix_differs (the values it names: not published)
           'printed_unit_prefix_differs': prefix or None,
           # read by export_site.py only: the caution efficiency_implausible_as_printed, a kcat/Km at or above 10⁹ M⁻¹ s⁻¹
           # that a check against the paper found physically implausible as printed (sources/implausible_as_printed.tsv)
           'kcat_over_km_implausible': True if w.get('kcat_over_km_flag') == 'implausible_as_printed' else None,
           'database_summary': database_summary(w),  # export_site.py puts it on the record and the Table download
           'database_kinds': database_kinds(w) or None,  # likewise: every kind of its values, for the site's filter
           'ph': w.get('ph'), 'temperature_k': w.get('temperature_k'),
           # a charge sign ending a part survives the exporter's strip of a trailing '-' ('HCO3-' -> 'HCO3⁻')
           'assay_conditions_summary': re.sub(r'(?<=[A-Za-z0-9])-(?=; |$)', '⁻', _plain('; '.join(parts))),
           'proof_lines': proof, 'source_db': 'primary_paper_direct', 'source_databases_merged': ['primary_paper_direct'],
           # an error of a database that covers the paper, in fixed phrases (export_site.py publishes it on the record)
           'database_note': ' '.join(w.get('database_note') or []) or None,
           # the compared databases that list values from the paper ([] when none does; export_site.py: the record)
           'database_paper_sources': database_paper_sources(w),
           'source_record_count': 1, 'verification_status': 'verified', 'evidence_confidence_tier': 'paper_grounded',
           'paper_grounding_status': 'review_excerpt_preserved', 'data_origin': 'experimental',
           'verification_method': V2_METHOD + ('; ec_from_databases' if (w.get('ec_source') or '').startswith('databases') else '')}
    return {k: v for k, v in row.items() if v is not None or k in ('kcat', 'km', 'kcat_over_km', 'mutation_signature')}


def _v2_done():
    """v2 measurements of finished papers, and those papers: also the ones v2 finished with no values (kept 0: a
    retracted paper, a review that only reprints), whose old rows then leave the site. A paper marked done with values
    that the export has not caught yet (another chat's `add` while build exported, 2026-10-10: 15 papers) is left for
    the next build, so its old rows are not dropped with nothing in their place."""
    import csv
    queue = list(csv.DictReader(open(ROOT / 'papers.tsv'), delimiter='\t'))
    done = {r['pmid'] for r in queue if r['status'] == 'done'}
    empty = {r['pmid'] for r in queue if r['status'] == 'done' and (r.get('kept') or '0') == '0'}
    wide = [json.loads(l) for l in open(ROOT / 'catlog_wide.jsonl') if l.strip()]
    # the site shows mM values only: a measurement printed only over a mass concentration (Km mg/mL, kcat/Km
    # mL mg^-1 s^-1, catlog_wide's own columns) has nothing to show there; one with a kcat shows its kcat
    mine = [w for w in wide if str(w['pubmed_id']) in done]
    rows = [w for w in mine if any(w.get(k) is not None for k in ('kcat', 'km', 'kcat_over_km'))]
    return rows, {str(w['pubmed_id']) for w in mine} | empty  # a paper v2 read replaces its old rows either way


def _manifest(text):
    """manifest.js is one line `window.CATLOG_STATIC_MANIFEST = {...};` followed by two shard-registry lines."""
    first = text.splitlines()[0]
    return json.loads(first[first.index('{'):first.rindex(';')])


def _data_id(receipt):
    """The data ID (/data/latest.json's data_id: the manifest's content_sha256[:10]) of a build or publish receipt."""
    try:
        return (receipt.get('cloudflare') or {}).get('data_id') or \
            _manifest((Path(receipt['bundle']) / 'data' / 'manifest.js').read_text())['content_sha256'][:10]
    except (OSError, KeyError, ValueError, TypeError, AttributeError):
        return None


def status():
    """What catlog.structf.studio serves (its /data/latest.json), which finished papers it does not hold yet (from the
    build receipt whose data it serves) and what `site stage` staged that is not live yet."""
    try:
        base_signature(); print('base: the certified October 7 old catalog, unchanged')
    except SystemExit as e:
        print('base:', e)
    try:
        live = json.loads(urllib.request.urlopen(urllib.request.Request(  # the site answers 403 to urllib's own User-Agent
            f'{LIVE}/data/latest.json?nocache={int(time.time())}', headers={'User-Agent': 'catlog-site-status'}),
            timeout=30).read())
        print(f"live: {LIVE} · data of {live['date']}, ID {live['data_id']} · {live['records']:,} records")
    except (OSError, ValueError, KeyError) as e:
        live = {}
        print(f'live: {LIVE} did not answer ({e})')
    pub = BUILD / 'published.json'
    try:
        last = json.loads(pub.read_text()) if pub.exists() else {}
    except ValueError:
        last = {}
    cf = last.get('cloudflare') or {}
    if cf:
        print(f"last publish: {last.get('published')} from {cf.get('ref')} "
              f"({(cf.get('site_tree') or cf.get('site_commit') or '')[:12]}), data ID "
              f"{cf.get('data_id')}" + (f"; the live site serves {live['data_id']} (a rollback, or a publish from "
              f"elsewhere?)" if live.get('data_id') and cf.get('data_id') != live['data_id'] else ''))
    rows, papers = _v2_done()
    b = json.loads((BUILD / 'build.json').read_text()) if (BUILD / 'build.json').exists() else {}
    shown = next((r for r in (last, b) if r.get('v2_papers') and live.get('data_id') and _data_id(r) == live['data_id']), None)
    print(f'CatLog v2: {len(rows):,} records from {len(papers):,} finished papers; '
          + (f"{len(papers - set(shown['v2_papers'])):,} papers not on the site yet (live build {shown['stamp']})" if shown
             else 'no build receipt matches the live data, so which of them it holds is not known'))
    st = b.get('staged') or {}
    live_already = st.get('tree') == cf.get('site_tree') if cf.get('site_tree') else (  # a receipt from before 2026-11-03
        last.get('stamp') == b.get('stamp') and (last.get('staged') or {}).get('manifest') == st.get('manifest'))
    if (BUILD / 'release.new').exists():
        print('site_build/release.new is the folder of a `site stage` whose checks failed (nothing publishes it)')
    if st and not live_already:
        print(f"staged, not live yet (built {b['stamp']}, {st.get('folder') or st.get('branch')} "
              f"{str(st.get('tree') or st.get('commit'))[:12]}): {b['records']:,} records, "
              f"{b['accepted']:,} accepted" + (", the same data as the live site" if _data_id(b) == live.get('data_id') else '')
              + ". The user's \"update the website\" or \"publish\" makes it live: python3 cloudflare/publish.py")


def build():
    """Merged catalog -> the existing exporter -> site_build/bundle-<stamp>. Nothing public happens."""
    want = base_signature()
    run([sys.executable, str(ROOT / 'catlog.py'), 'export'], cwd=ROOT)  # catlog_wide.jsonl as of now
    # what this bundle is built from, taken now: another chat may commit or export while the merge and exporter run
    wide_sha = sha(ROOT / 'catlog_wide.jsonl')
    commit = run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture=True).stdout.strip()
    # human_review/site_marks.json from the same catlog_wide (v2 measurement ids change between exports)
    run([sys.executable, str(ROOT / 'catlog.py'), 'review', 'site'], cwd=ROOT)
    BUILD.mkdir(exist_ok=True)
    marks_snap = BUILD / 'marks.json'  # this build's marks, before another chat's `review site` can rewrite the live file
    if (ROOT / 'human_review' / 'site_marks.json').exists():
        shutil.copyfile(ROOT / 'human_review' / 'site_marks.json', marks_snap)
    rows, papers = _v2_done()
    if sha(ROOT / 'catlog_wide.jsonl') != wide_sha:  # the v2 rows, marks and receipt must come from one export
        sys.exit('another chat exported while this build started: run `site update` again')
    BUILD.mkdir(exist_ok=True)
    stats = BUILD / 'database_stats.json'  # the Stats figures' counts compared with databases (manifest, export_site.py)
    stats.write_text(json.dumps(database_stats(rows, papers), indent=1, ensure_ascii=False))
    years = BUILD / 'publication_years.json'  # BRENDA vs CatLog per publication year (manifest, export_site.py 12.)
    pub = publication_years(papers=papers)  # the values of the papers this build shows from v2, as Quality counts them
    if pub:
        years.write_text(json.dumps(pub, indent=1, ensure_ascii=False))
    else:
        years.unlink(missing_ok=True)  # never an older build's years
    stamp = time.strftime('%Y%m%d-%H%M%S')
    merged = BUILD / 'merged' / 'verified_catlog.jsonl'  # the exporter's usual file name; rewritten by every build (5.4 GB)
    merged.parent.mkdir(exist_ok=True)
    v2rows = BUILD / 'v2_rows.jsonl'
    seen, pairs = set(), [(w, v2_row(w)) for w in rows]
    condition_notes(pairs)
    garbled_notes(pairs)
    with open(v2rows, 'w') as fh:
        for w, r in pairs:
            if r['measurement_key'] in seen:  # the site's viewer index needs unique record keys
                r['measurement_key'] = r['review_key'] = f"{r['measurement_key']}-{(w.get('row_ids') or ['x'])[0]}"
            seen.add(r['measurement_key'])
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    (BUILD / 'v2_papers.json').write_text(json.dumps(sorted(papers)))
    print(f'merging: base {BASE} ({want["records"]:,} records) with {len(rows)} v2 measurements from {len(papers)} papers')
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    r = subprocess.run([str(OLD / '.venv' / 'bin' / 'python'), __file__, '_merge'], env=env, text=True, capture_output=True)
    if r.returncode:
        sys.exit(f'merge failed:\n{r.stderr[-3000:]}')
    kept, dropped, dropped_accepted, empty, empty_accepted = json.loads(r.stdout.strip().splitlines()[-1])
    print(f'  left out {empty:,} base rows with no kcat, Km or kcat/Km ({empty_accepted:,} of them accepted)')
    bundle = BUILD / f'bundle-{stamp}'
    print('  exporter (realkcat, read-only) ->', bundle)
    # --human-marks: the marks this bundle ships (export_site.py 7.: a full human approval makes a record accepted)
    r = subprocess.run([str(OLD / '.venv' / 'bin' / 'python'), str(ROOT / 'tools' / 'export_site.py'), str(EXPORTER),
                        *(['--human-marks', str(marks_snap)] if marks_snap.exists() else []), '--database-stats', str(stats),
                        *(['--publication-years', str(years)] if pub else []), '--source-checkout', str(OLD),
                        '--verified-path', str(merged), '--out-dir', str(bundle)], cwd=OLD, env=env, text=True, capture_output=True)
    if r.returncode:
        sys.exit(f'exporter failed:\n{r.stderr[-3000:]}')
    merged.unlink(missing_ok=True)  # the ~5 GB merged copy of the frozen base: only the exporter reads it, every build rewrites it
    manifest = _manifest((bundle / 'data' / 'manifest.js').read_text())
    # the comparison download (round 9 brief C10) from the Full data just written, named in the manifest (stage copies
    # it with the other data files; the bundle's hashed manifest copy stays the exporter's: stage writes the one served)
    mids = {r['measurement_key']: w['measurement_id'] for w, r in pairs}
    comparison, tally = comparison_csv(bundle / manifest['enriched_download']['path'], bundle / 'data', manifest, mids)
    manifest = _manifest_set(bundle / 'data' / 'manifest.js', COMPARISON_KEY, comparison)
    nd = not_detected_csv(ROOT / 'catlog_bounds.jsonl', bundle / 'data', manifest,
                          {m: k for k, m in mids.items()}, {str(p) for p in papers})
    vals = values_csv(bundle / manifest['enriched_download']['path'], bundle / 'data', manifest)
    manifest = _manifest_set(bundle / 'data' / 'manifest.js', VALUES_KEY, vals)  # one value per row, read from the paper
    print(f"  values file: {vals['rows'] - vals['calculated']:,} printed values and {vals['calculated']:,} kcat/Km calculated "
          f"from kcat and Km, of {vals['records']:,} records read from the paper -> {vals['path']}")
    if nd:  # the values the papers report as not detected or only as a bound: their own download
        manifest = _manifest_set(bundle / 'data' / 'manifest.js', NOT_DETECTED_KEY, nd)
        print(f"  not detected or a bound: {nd['rows']:,} values from {nd['papers']:,} papers -> {nd['path']}")
    manifest, pub = dated_publication_years(bundle / 'data' / 'manifest.js', manifest, pub)  # the snapshot's day
    if pub:
        years.write_text(json.dumps(pub, indent=1, ensure_ascii=False))
    print(f"  compared with databases: {comparison['rows']:,} rows, {comparison['size_bytes'] / 1e6:.1f} MB -> "
          f"{comparison['path']}\n    " + ', '.join(f'{k} {n:,}' for k, n in sorted(tally.items())))
    accepted = manifest['summary']['trust_snapshot']['accepted_rows']
    # export_site.py 7.: accepted records without a paper are not accepted; full human approvals are
    dist = manifest['summary']['distributions']
    no_paper, human = _count(dist['public_trust_basis'], 'identity_only'), _count(dist['accepted_basis'], 'human review')
    expect_rows, expect_acc = kept + len(rows), want['accepted'] - dropped_accepted - empty_accepted + len(rows) - no_paper + human
    problems = []
    if manifest['total_rows'] != expect_rows:
        problems.append(f"records {manifest['total_rows']} != {expect_rows}")
    if accepted != expect_acc:
        problems.append(f'accepted {accepted} != {expect_acc}')
    marks_src = BUILD / 'marks.json'  # made by `review site` above, from this same catlog_wide
    if marks_src.exists():
        shutil.copyfile(marks_src, bundle / 'data' / 'human-review-marks.json')
    if rows and not comparison['rows']:
        problems.append('the comparison download has no rows')
    if pub and manifest['summary'].get('publication_years') != pub:  # said, never a build problem (round 16 brief 1)
        print('  note: summary.publication_years did not reach the manifest as written; the Stats page leaves the figure out')
    problems += _leaks(bundle / 'data')
    receipt = {'stamp': stamp, 'bundle': str(bundle), 'base_generation': want['generation'], 'base_records': want['records'],
               'base_accepted': want['accepted'], 'old_rows_replaced': dropped, 'old_accepted_replaced': dropped_accepted,
               'base_rows_without_values': empty,
               'v2_measurements': len(rows), 'v2_papers': sorted(papers),
               'v2_papers_with_values': len({str(w['pubmed_id']) for w in rows}), 'records': manifest['total_rows'], 'accepted': accepted,
               'not_accepted_no_paper': no_paper, 'accepted_on_human_review': human,
               'catlog_wide_sha256': wide_sha, 'v2_commit': commit, 'comparison_rows': comparison['rows'],
               'problems': problems, 'published': False}
    (BUILD / 'build.json').write_text(json.dumps(receipt, indent=1))
    print(json.dumps({k: v for k, v in receipt.items() if k != 'v2_papers'}, indent=1))
    if problems:
        sys.exit('build has problems: fix them before staging')
    _tidy(bundle)


LOCAL_PATH = re.compile(r',?\s*/(?:private|Users|tmp)/\S+')  # a reader's scratch path in a location: never published
LEAK = re.compile(rb'/Users/|/private/(?:tmp|var)/|"reasoning"|verify_note|uniprot_how|smiles_how|db_check|ratio_check|agentic_understanding|'
                  # database_check itself and its unpublished fields (only v2_row's database_* line fields are public)
                  rb'"(?:database_check|database_entry|database_value|cause_by|pairing|closure_fold|derivation|read_as|'
                  rb'rounded|same_values|other_values|other_labels|other_numbers|pair_numbers|no_metric|paper_sources|other_measurement|ratio_sources)"\s*:|'
                  # database_check's closure (a code: supports_catlog); database_parts' closure is a sentence (it has a space)
                  rb'"closure"\s*:(?!\s*"[^"]* )')
PROMPT = re.compile(rb'provided text', re.I)  # the reader's prompt language (_facts takes it out): never public


def _leaks(data):
    """A bundle's data files that hold a private field or path, or the reader's prompt language."""
    problems = []
    for f in sorted(data.glob('*')):
        with (gzip.open(f) if f.suffix == '.gz' else open(f, 'rb')) as fh:
            hit = {what for line in fh for pat, what in ((LEAK, 'a private field or path'), (PROMPT, '"provided text"'))
                   if pat.search(line)}
        problems += [f'{f.name} contains {what}' for what in sorted(hit)]
    return problems


def _tidy(new):
    """Old bundles are build outputs (~90 MB each, ~3 builds a day), rebuildable from the catalog at their commit: after a
    clean build keep the new one, the published one (published.json) and the newest, and remove the rest."""
    keep = {new.name}
    try:
        keep.add(Path(json.loads((BUILD / 'published.json').read_text())['bundle']).name)
    except (OSError, ValueError, KeyError):
        return  # never guess which bundle is live
    gone = [b for b in sorted(BUILD.glob('bundle-*'))[:-1] if b.name not in keep]
    for b in gone:
        shutil.rmtree(b, ignore_errors=True)
    if gone:
        print(f'removed {len(gone)} old site bundles (build outputs); kept {", ".join(sorted(keep))}')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode, was = True, sys.dont_write_bytecode  # no __pycache__ inside a release
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = was
    return mod


def _refs(manifest):
    paths = set(manifest.get('detail_shards') or []) | set(manifest.get('record_chunks') or [])
    for key in ('table_download', 'enriched_download', 'viewer_index', 'full_data_download', COMPARISON_KEY, NOT_DETECTED_KEY,
                VALUES_KEY):
        if (manifest.get(key) or {}).get('path'):
            paths.add(manifest[key]['path'])
    return {'tools/catlog-static/' + p for p in paths}


# how CatLog reads and checks values (the Guide's words): the README, the release note (both say first that these
# records are read from the paper, so the method starts with the reading)
METHOD = ("An AI model (Claude, Anthropic) reads each kcat, Km and kcat/Km in a paper with its unit, enzyme, organism, "
          "substrate and assay conditions. A second, separate AI check compares every value with the paper. Automated "
          "checks confirm that the quoted line is in the paper text and convert the paper's units to CatLog's. Each value "
          "keeps where it is printed and the number as printed. AI audits and human reviewers check samples against the "
          "papers; only records marked human-checked count as checked by a person.")
V2_LICENSE = "CC BY 4.0 (CatLog compilation); quoted paper text remains the publisher's"  # export_site.py sets it
# Fields of the Full data, one bullet per group (website plan P29), a field's meaning said once; '*': not in the Table.
# An item is a bullet, or (indent, text) for a bullet under the one before. "records read from the paper" are CatLog's
# (round 17: records and values are the site's counting words, the README's too; a file has lines).
FIELDS = (
    "Record: record_key (the record ID), measurement_key (CatLog's own key for it: its code calls a record a measurement).",
    'Enzyme and organism: enzyme_display_name, enzyme_label_source and enzyme_name_source (where the name comes from), '
    'ec_number, organism.',
    'Protein: primary_uniprot_id, uniprot_id*, uniprot_candidate_ids (possible UniProt entries when none was chosen), '
    "protein_accession and protein_accession_database (UniProt or NCBI Protein), source_protein_accession (the source's "
    'accession, when it differs), has_sequence, sequence_resolved, sequence* (the variant sequence when one was built, '
    'else the reference), wild_type_sequence*, variant_sequence*, sequence_source*, sequence_source_confidence, '
    'sequence_variant_status, sequence_variant_note* (what the sequence shown is).',
    'Variant: wild_type (true, false or empty = not known), mutation_type*, mutation_signature (for example H150A; '
    '"Unknown" on wild-type records and where no mutation is given).',
    'Substrate: substrate_name, smiles*; on records read from the paper also substrate_chebi* (the ChEBI ID when the '
    'structure came from ChEBI)*, substrate_inchikey* (from the SMILES), substrate_pubchem_cid* and smiles_source* (where '
    'the structure came from).',
    'Organism IDs (records read from the paper): taxon_id* (NCBI Taxonomy, from the organism name); organism_source* (paper, '
    'or "UniProt <accession>" when the paper names no organism and the record\'s UniProt entry gives it).',
    'Errors (records read from the paper): kcat_err*, km_err* and kcat_over_km_err*, the ± the paper prints, converted to the '
    'units of the value exactly as the value was; empty when the paper prints none (a calculated kcat/Km has none).',
    'Values: kcat, km, ki and kcat_over_km (in the units above); kcat_unit, km_unit, ki_unit and kcat_over_km_unit; '
    'kcat_display, km_display, ki_display and kcat_over_km_display (the text the page shows); has_ki; '
    'kcat_over_km_origin (paper_reported, source_listed, calculated = kcat / Km and not printed, or not_specified); '
    'source_kcat_over_km_values* (the kcat/Km values the source databases list) and kcat_over_km_source_differs (one '
    'of them differs from kcat_over_km).',
    'Conditions: ph, ph_display, temperature_c, temperature_k, temperature_display; assay_conditions_summary* (other '
    'conditions such as buffer and cosubstrate; on records not yet re-read also pH and temperature); condition_note* '
    '(records read from the paper: what tells the record from another of the paper with the same enzyme, organism, substrate, '
    'variant, pH and temperature: the assay parts that differ, else a qualifier such as apparent Km, else the table).',
    'Cautions: condition_flags, the reasons a value may be wrong (empty when none applies): unit_not_recorded_kcat, '
    'unit_not_recorded_km, kcat_over_km_quotient_mismatch (the kcat/Km shown differs from kcat / Km; on records read from '
    'the paper by more than 1.5x widened by the printed uncertainties, and by more than the printed figures explain; '
    'all three stay as printed), kcat_over_km_unit_mismatch, kcat_over_km_source_mismatch (every kcat/Km the source '
    'databases list is more than 2-fold from the one shown), km_magnitude_needs_check (Km above 10 M or below 1 nM), '
    'kcat_magnitude_needs_check (kcat above 10⁸ s⁻¹), efficiency_above_diffusion_limit, efficiency_implausible_as_printed '
    '(a kcat/Km of 10⁹ M⁻¹ s⁻¹ or more that a check against the paper found physically implausible as printed), '
    'temperature_*_needs_check, '
    'printed_unit_prefix_differs (records read from the paper: a printed unit with another concentration prefix than the '
    'unit used, such as µM printed and mM used; the conversion field names the unit used).',
    'Paper: pubmed_id*, doi*, supporting_pmids* and supporting_dois* (every paper of a merged record), pmid_count, doi_count, '
    'literature_id_count, has_literature_id.',
    'Evidence: proof_lines*, one per printed value: table_label, row_label and column_label (where); metric and '
    'metric_label (which value); raw_value and raw_unit (as printed); normalized_value and normalized_unit (in the units '
    'above); raw_value_unit_evidence and normalized_value_unit_evidence (the same as text; on records read from the paper '
    'with the line it is printed in and what it was converted from); assay_condition, pmid and doi. proof_kind '
    '(paper_evidence or source_note) and has_proof_excerpt say whether there is any.',
    ('  ', 'On records read from the paper each one also has printed (number and unit as printed), printed_line (the line '
           'it was read from, once per line, as the paper\'s text gives it; printed_line_note says where a PDF\'s text '
           'layer lost symbols or gives ± as another character), check (what the second, separate AI check found: confirmed, or corrected '
           'and what), conversion (empty when the value is stored as printed; else "converted by code", "printed unit '
           'read as" the unit used, or both), value_display (the value with the printed figures: a printed 135.0 stays '
           '135.0) and, for a value an AI audit re-checked, audit_date and audit_result (kept or unit corrected).'),
    f'Against the enzyme databases, per value (records read from the paper; {ALL_DATABASES}, for the same paper, '
    'substrate, variant and organism). Each element of proof_lines has:',
    ('  ', 'database_status: confirmed (a database lists the same number); corrected (a database lists another number '
           "for the same value, CatLog's is the one the paper prints, and an automated check or a check against "
           'the paper found why); differs (another number, cause not yet known; a different number can belong to another '
           'record of the paper and does not by itself mean a database is wrong); same_number_other_label (a database lists '
           'this number for the paper under another substrate, variant or organism); new (no compared database lists '
           'it); not_compared.'),
    ('  ', 'database_line (the comparison in fixed sentences, as the record page shows it) and database_sources (the '
           'databases it names).'),
    ('  ', 'database_by_source: what each compared database that lists the paper lists for the value, in the order '
           'above: db; kind (same; same_rounded, the same to one or two significant figures; corrected; differs; '
           'same_number_other_label; other_number, another number for this value; another_measurement, the number of '
           'another record of the paper; '
           'other_values_only, other values of this parameter for the paper; parameter_absent; value_absent, none for '
           "this value); value (its number in the units above, at most 4 significant figures); unit; x (its number ÷ "
           "CatLog's); label (the label it lists CatLog's number under, at most 90 characters)."),
    ('  ', 'database_cause, on a correction: found by an AI check of the paper (header_scale_inverted, '
           'header_scale_ignored, unit_not_converted, uM_entered_as_mM, mM_entered_as_uM, time_unit, '
           'decimal_or_exponent_slip, value_from_other_row, value_not_in_paper, paper_unit_misprint, recomputed_ratio) or '
           'automatically (power_of_ten, off by an exact power of ten; printed_number_unit_not_applied, the printed '
           'number taken in another unit; time_factor, off by exactly 60 or 3,600; paper_unit_misprint, the printed '
           "value in a printed unit that the paper's own kcat ÷ Km does not support). On a different number: exact_factor "
           '(an exact factor found automatically, nothing else checked). On any value: different_measurement (an AI '
           'check of the paper found a database number to belong to another record of the paper).'),
    ('  ', 'database_found_by, on a correction: paper_check (a separate AI check read the paper and recorded the cause) '
           'or factor_cross_checked (an exact factor, or the printed value in its printed unit, found automatically, and '
           "the paper's own kcat ÷ Km agrees with CatLog's number, not the database's). database_evidence, with a cause "
           'from an AI check of the paper: where in the paper and what it prints.'),
    ('  ', 'database_new_reason, for a value no compared database lists: paper_not_in_databases (the paper is in none '
           'of them); metric_absent (no value of this parameter for the paper); substrate_absent; variant_absent (none '
           'for this substrate with this variant or organism); condition_absent (other numbers for this substrate and '
           'variant, not this one; some may be values the pairing could not match); ratio_only (a printed kcat/Km whose '
           'kcat and Km they list; they did not store the ratio).'),
    'Against the enzyme databases, per record (records read from the paper): database_summary, one word for its printed '
    'values: same (each is the number a database lists for that paper, substrate and variant), corrected, differs, '
    'other_label, new (no compared database lists any of them: a new record), mixed (values of more than one '
    'kind) or not_compared; database_kinds, every kind among them (["same", "new"]: a new value next to a confirmed '
    'one), to filter records with a new value or a correction; database_paper_sources, the compared databases that list '
    'any kcat, Km or kcat/Km from the paper ([] when none does); database_note*, a database difference that covers the '
    'whole paper. Databases often copy one another. UniProt: the kinetic parameters of reviewed (Swiss-Prot) entries '
    'that cite the paper.',
    'Earlier corrections: corrections* (records with verification_status corrected) lists each field the earlier review '
    'changed: field; before and after (numbers for kinetic values, pH and temperature; text for identifiers such as a '
    'PMID); unit; kind (rounding: within 2%, or one number printed to at most 2 significant figures and the other the '
    'same rounded half up; magnitude: a power of ten; different, added, removed, replaced, changed); where (the table '
    'and row it was read from); listed (a database that lists the before value for that paper).',
    'Review: verification_status, public_trust_basis (literature_referenced: accepted with a linked paper; '
    'identity_only: see Review result above; empty on other records), accepted_basis* ("human review" on a record not '
    'yet re-read that is accepted because a human reviewer approved its values, though the earlier review had not). '
    'Human-checked records are listed in human-review-marks.json on the site, keyed by record_key.',
    'Source and license: source_db, source_databases_merged*, source_record_count (above 1: the record merges several '
    'database listings), source_license.',
    'Short names: enzyme*, substrate*, uniprot*, status* and source* repeat enzyme_display_name, substrate_name, '
    'uniprot_id, verification_status and source_db.',
    "Provenance from CatLog's earlier version, not needed for analysis: verification_method* (on records read from the paper "
    'it starts with "catlog_"), evidence_confidence_tier, paper_grounding_status, literature_linkage, '
    'identity_resolution_state, data_origin*, review_key.')


def _count(dist, label):
    return sum(x['count'] for x in dist or [] if x['label'] == label)


def _licenses(dist):
    """source_license counts (export_site.py) in the README's groups; the most restrictive license of a row decides."""
    g = dict.fromkeys(('catlog', 'cc_by', 'sabio', 'nc_nd', 'published', 'other'), 0)
    for x in dist:
        label = x['label']
        key = ('nc_nd' if 'CC BY-NC-ND' in label else 'sabio' if 'SABIO-RK terms' in label else 'catlog' if label == V2_LICENSE
               else 'cc_by' if label == 'CC BY 4.0' else 'published' if label.startswith('as published') else 'other')
        g[key] += x['count']
    return g


def _date(x):
    """'2026-10-21' as 'October 21, 2026'; anything else as given."""
    try:
        d = datetime.strptime(str(x)[:10], '%Y-%m-%d')
        return f'{d:%B} {d.day}, {d.year}'
    except ValueError:
        return str(x)


def _audit_share(d, n, ci):
    """The share of the audited values found wrong to the precision of its 95% interval (ci: the match of
    audit_wrong_ci95, two decimals: '0.42%; 95% interval 0.29-0.61%', as Stats gives it), else to one decimal."""
    places = max(len(x.partition('.')[2]) for x in ci.groups()) if ci else 1
    return f'{100 * d / n:.{places}f}%' + (f'; 95% interval {ci[1]}-{ci[2]}%' if ci else '')


def _audit_line(q):
    """The AI audits in words (README): the values the random audit re-checked, the wrong ones removed, their 95%
    interval and, when they hold most of them, how many sit in the two papers with the most (human_review.audit_detail);
    then the follow-ups apart (audit_targeted_values / _wrong: whole-paper follow-ups and re-checks of values a database
    check found wrong, catlog.audit_targeted), which are not in the share; '' without audits. Since round 16b the share
    is over random rows only, so the words say "at random" again."""
    n, d = q.get('audit_values') or 0, q.get('audit_wrong') or 0
    if not n:
        return ''
    ci = re.fullmatch(r'(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)', str(q.get('audit_wrong_ci95') or ''))
    share = _audit_share(d, n, ci)
    top, papers = q.get('audit_wrong_top2'), q.get('audit_wrong_papers')
    where = (f" {top:,} of the {d:,} are in two papers, the other {d - top:,} in {papers - 2:,} more."
             if isinstance(top, int) and isinstance(papers, int) and papers > 2 and 0 < top < d else '')
    caveat = ' The interval treats each value as independent; errors can cluster in a paper.' if ci else ''
    t, td = q.get('audit_targeted_values') or 0, q.get('audit_targeted_wrong') or 0
    more = (f" A further {t:,} values were audited because an audit sample or a database check pointed to them "
            f"({td:,} wrong and removed); they are not in this share, and their wrong values count under CatLog's own "
            'errors.' if t else '')
    return (f'AI audits: a separate AI auditor re-checked {n:,} values, drawn at random, against their papers to find '
            f'errors; {d:,} ({share}) were wrong and removed.{where}{caveat}{more}')


def _errors_line(q):
    """CatLog's own errors found so far by every route (human_review.catlog_errors), each named, in short sentences
    (round 16b quality review: one sentence of routes read as a garden path, "partial constants" was undefined and the
    database checks did not say what became of the values); '' without them."""
    e = q.get('catlog_errors') or {}
    part = lambda k: e.get(k) or {}
    n = lambda k: part(k).get('values') or 0
    if not n('all'):
        return ''
    pp = lambda k: f"{part(k).get('papers', 0):,} {'paper' if part(k).get('papers') == 1 else 'papers'}"
    out = [f"Errors CatLog's own checks caught so far: {n('all'):,} values in {pp('all')} (a value caught in two ways counts once)."]
    if n('audit'):
        au = part('audit')
        fixed = au.get('corrected') or 0
        out.append(f"AI audits caught {n('audit'):,} ({pp('audit')}); "
                   + (f"{n('audit') - fixed:,} removed, {fixed:,} corrected." if fixed else 'removed.'))
    if n('sweep'):
        sw = part('sweep')
        rep, par = sw.get('reprinted') or 0, sw.get('partial_constant') or 0
        other = n('sweep') - rep - par
        kinds = [x for x in (f"{rep:,} values the paper reprints from earlier work" if rep else '',
                             f"{par:,} per-product (partial) rate constants stored as the reaction's kcat or kcat/Km"
                             if par else '', f"{other:,} others" if other > 0 and (rep or par) else '') if x]
        out.append(f"Follow-up searches for the same kind of error, in the rest of its paper or across CatLog, "
                   f"removed {n('sweep'):,} more ({pp('sweep')})" + (f": {_names_and(kinds)}" if kinds else '') + '.')
    if n('unit_fix'):
        out.append(f"Units the paper misprinted: {n('unit_fix'):,} values ({pp('unit_fix')}) corrected.")
    if n('difference_check'):
        db = part('difference_check')
        removed, corrected = db.get('removed') or 0, db.get('corrected') or 0
        rest = n('difference_check') - removed - corrected
        fate = [x for x in (f'{removed:,} removed' if removed else '', f'{corrected:,} corrected' if corrected else '',
                            f'{rest:,} awaiting a further check' if rest > 0 and 'removed' in db else '') if x]
        if len(fate) == 1 and rest <= 0 and n('difference_check') > 1:
            fate = [f"all {fate[0].split(' ', 1)[1]}"]
        out.append(f"Checks of database differences against the paper found {n('difference_check'):,} ({pp('difference_check')})"
                   + (f", {fate[0]}" if len(fate) == 1 and fate[0].startswith('all ') else f": {_names_and(fate)}" if fate else '')
                   + '.')
    if n('misread_cell'):  # last, as Stats' Errors caught by CatLog's checks has it (2026-11-06)
        out.append(f"Cells misread: {n('misread_cell'):,} {'value' if n('misread_cell') == 1 else 'values'} "
                   f"({pp('misread_cell')}) corrected from the page image.")
    if n('label_fix'):  # values dropped for a wrong organism label, back with the label corrected (2026-11-15)
        out.append(f"Wrong organism labels: {n('label_fix'):,} {'value' if n('label_fix') == 1 else 'values'} "
                   f"({pp('label_fix')}) corrected.")
    return ' '.join(out)


def _span(first, last):
    """'October 9 and October 21, 2026' (one year), else both dates in full."""
    a, b = _date(first), _date(last)
    if a[-6:] == b[-6:] and a[-4:].isdigit():
        return f'{a[:-6]} and {b}'
    return f'{a} and {b}'


def _exposure_line(q):
    """The papers read or checked with database values in view, and their blind re-reads (human_review._exposure), in
    the words of the site's note on Stats (statsExposureText, fix pass after round 16b): why blind reading matters, the
    papers with the reading and the checking agent apart, what was sent back and how, the papers not sent back, and that
    the values stay meanwhile. '' without the counts, or when they do not add up."""
    e = q.get('exposed') or {}
    papers, reader, checker = e.get('papers') or 0, e.get('reader') or 0, e.get('checker_only') or 0
    if not papers or reader + checker != papers:
        return ''
    why = ("CatLog's reading and checking agents are meant to work without database values, so that agreement with the "
           'databases is a fair test.')
    who = (f'the reading agent on {reader:,} and only a checking agent on {checker:,}' if reader and checker else
           'the reading agent on each' if reader else 'only a checking agent on each')
    when = f"Between {_span(e['first'], e['last'])}, agents" if e.get('first') and e.get('last') else 'Agents'
    saw = (f"{when} saw such values, or records CatLog held for the paper before, on {papers:,} "
           f"{'paper' if papers == 1 else 'papers'}: {who}.")
    sent, done = e.get('reread_blind') or 0, e.get('reread_blind_done') or 0
    if sent and e.get('reread_blind_on') and sent <= papers:
        reads, checks = e.get('reread_blind_read'), e.get('reread_blind_verify')
        how = (f'{reads:,} to be read and {checks:,} to be checked' if isinstance(reads, int) and isinstance(checks, int)
               and reads + checks == sent else '')
        state = (f"{done:,} {'is' if done == 1 else 'are'} done" if done else 'none finished yet')
        inner = '; '.join(x for x in (how, state) if x)
        rest = papers - sent
        again = (f" {sent:,} of them {'was' if sent == 1 else 'were'} sent back on {_date(e['reread_blind_on'])} to be read "
                 f"or checked again without them ({inner})"
                 + (f"; the other {rest:,} {'has' if rest == 1 else 'have'} not been sent back" if rest else '') + '.'
                 + ('' if done == sent else ' Until then their values stay in CatLog and in the comparison with the databases.'))
    else:
        again = ' Their values stay in CatLog and in the comparison with the databases.'
    return f'Blind reading: {why} {saw}{again}'


def _review_basis(r):
    """The earlier version's review as its headline counts it: (block, entries without a paper or None). The shares are
    over the entries a reviewer could check against a paper (review.v1.checkable) when the marks give them, else over
    every entry (marks written before 2026-10-21)."""
    c, without = r.get('checkable') or {}, r.get('entries_without_paper') or 0
    return (c, without) if c.get('entries') and c['entries'] + without == r.get('entries') else (r, None)


def _one_review(review):
    """quality.review as the site gives it: the review of the earlier version's records (v1) and of CatLog's own (v2)
    as one, the way cloudflare/app/catlog-static.js oneReview merges them (one CatLog, the user 2026-10-30), so the
    README's human review is the same number Stats and Team show."""
    v1, v2 = review.get('v1') or {}, review.get('v2') or {}
    if not v1.get('entries') or not v2.get('entries'):
        return v1
    c = lambda b, k: b.get(k) or 0

    def merged(block, entries, without):
        kinds = {}
        for b in (block, v2):
            for kind, n in (b.get('other_by_kind') or {}).items():
                kinds[kind] = kinds.get(kind, 0) + (n or 0)
        out = {'entries': entries, 'entries_without_paper': without, 'other_by_kind': kinds,
               'value_disputed': c(block, 'value_disputed') + c(v2, 'value_disputed') + c(v2, 'picked_value_disputed'),
               'value_disputed_checked_as_printed': c(block, 'value_disputed_checked_as_printed')
               + c(v2, 'value_disputed_checked_as_printed') + c(v2, 'picked_value_disputed_checked_as_printed')}
        for k in ('value_missing', 'other_disputed'):
            if k in block or k in v2:
                out[k] = c(block, k) + c(v2, k)
        return out
    without = c(v2, 'entries_without_paper')
    one = merged(v1, v1['entries'] + v2['entries'], c(v1, 'entries_without_paper') + without)
    if (v1.get('checkable') or {}).get('entries'):
        one['checkable'] = merged(v1['checkable'], v1['checkable']['entries'] + v2['entries'] - without, 0)
    return one


def _share(part, whole):
    """A share as the site's app writes it (qualityShare): one decimal, '>99.9%' just under 100."""
    p = 100 * part / whole
    return '<0.1%' if 0 < p < 0.1 else '>99.9%' if 99.9 < p < 100 else f'{p:.1f}%'


def _quality_lines(q, human_checked=None):
    """The marks file's quality object (human_review.quality) in words: the AI audits and CatLog's own errors, the
    papers read with database values in view, the human review and the agreement of human reviewers with CatLog. The
    human review as Stats (Figure 1, At a glance) and Team give it (the numbers audit, 2026-11-06): the records people
    checked against their papers, those with no PMID or DOI apart; the human-checked tag with its own basis, never as a
    part of those records."""
    out = [x for x in (_audit_line(q), _errors_line(q), _exposure_line(q)) if x]
    r = _one_review(q.get('review') or {})
    if r.get('entries'):  # the headline (the user, 2026-10-15): what the reviewers' own files say, every number from
        b, nopaper = _review_basis(r)  # quality.review (v1 and v2 as one), never typed
        n, d = b['entries'], b.get('value_disputed', 0)
        checked = b.get('value_disputed_checked_as_printed', 0)
        disputed = ('' if not d else
                    f"; the {d:,} disputed value{'s are' if d != 1 else ' is'} as printed in the paper" if checked == d else
                    f"; {checked:,} of the {d:,} disputed values are as printed in the paper, {d - checked:,} not yet checked")
        out.append(f"Human review: people checked {n:,} records against their papers"
                   + (f" ({nopaper:,} more had no PMID or DOI)" if nopaper else '')
                   + f"; no value disputed on {n - d:,} ({_share(n - d, n)}){disputed}.")
        kinds = dict(b.get('other_by_kind') or {})
        missing = kinds.pop('could not find the value', 0)
        if missing:
            out.append(f'In {missing:,} records ({100 * missing / n:.1f}%) the reviewer could not find the value in the paper.')
        # (no count of the values reviewers named: agreement.stated_values takes them from every record a reviewer
        # commented on, not only the records with a value missing; Stats' Figure S1 leaves it out too since the numbers
        # audit of 2026-11-06)
        rest = ', '.join(f'{k} ({v:,})' for k, v in kinds.items())
        if b.get('value_missing') or rest:
            out.append((f"Values missing: {b.get('value_missing', 0):,} records ({_share(b.get('value_missing', 0), n)}) lacked a "
                        f"value the paper prints, mostly the kcat." if b.get('value_missing') else '')
                       + (f"{' ' if b.get('value_missing') else ''}Other disagreements: {rest}." if rest else ''))
        out += _reread_lines(q)
    if human_checked is not None:
        # (round 17, the brief: where two counts differ, say why in a few words. The tag is not a part of the records
        # people checked above: a record also carries it when a reviewer approved its values on another record of its
        # paper (human_review._site_marks), so the definition says so and no counting note compares the two; no count
        # of values either, which read against the approved values below)
        out.append(f'Human-checked: {human_checked:,} accepted records, where a human reviewer approved every kcat and Km '
                   'shown, on this record or as the same values for this paper; the kcat/Km was approved too or agrees '
                   'with kcat ÷ Km.')
    return out


def _differ_checked(a):
    """Of the approved values CatLog does not match (agreement differ), those an AI check of the paper has judged and
    those it has not (differ_not_adjudicated): (checked, pending), or None when the agreement does not count them."""
    other, pending = a.get('differ'), a.get('differ_not_adjudicated')
    if not isinstance(other, int) or not isinstance(pending, int) or pending > other:
        return None
    return other - pending, pending


def _errors_found(a):
    """The errors the comparison with the reviewers' approved values found in CatLog, as the site's Table S2 caption says
    them (statsReviewErrorsFound, fix pass after round 16b): "Comparing them found 68 wrong labels and 1 missed value in
    CatLog, all fixed since." From agreement.first_catlog_errors and its parts and fixed_after_comparison; '' without
    them or when the parts do not add up."""
    every = a.get('first_catlog_errors')
    if not isinstance(every, int) or every <= 0:
        return ''
    parts = [(a.get(k) or 0, one, many) for k, one, many in (
        ('first_catlog_errors_value', 'wrong number or unit', 'wrong numbers or units'),
        ('first_catlog_errors_label', 'wrong label', 'wrong labels'),
        ('first_catlog_errors_missed', 'missed value', 'missed values'))]
    if sum(n for n, _, _ in parts) != every:
        return ''
    fixed = a.get('fixed_after_comparison')
    since = ('' if not isinstance(fixed, int) or fixed > every else
             f", {'fixed' if every == 1 else 'all fixed'} since" if fixed == every else
             f"; {fixed:,} {'is' if fixed == 1 else 'are'} fixed since" if fixed else '')
    return f"Comparing them found {_names_and([f'{n:,} {one if n == 1 else many}' for n, one, many in parts if n])} in CatLog{since}."


def _reread_sentence(q):
    """The re-read sentence (the user, 2026-10-15), from quality.agreement only: where CatLog re-read a paper the
    reviewers checked, how many approved values it matches, and what the others are (the differ_ fields), said as what
    AI agents found when they checked them against the paper and how many are not yet checked (item 2 of
    work/publication_strategy_20261021/FIXES_FOR_MAIN_CHAT.md); the older v2_found / v2_approved_total pair when the
    marks carry no agreement block. '' when there is nothing to say."""
    a = q.get('agreement') or {}
    same, tot = a.get('agree'), a.get('values_approved')
    if not tot:
        same, tot = q.get('v2_found'), q.get('v2_approved_total')
        if not tot:
            return ''
    head = (f"Where CatLog has re-read a paper the reviewers checked, its value now matches the approved value for "
            f"{same:,} of {tot:,} ({100 * same / tot:.1f}%).")
    if not a.get('values_approved'):
        return head
    if found := _errors_found(a):  # what the comparison found in CatLog and fixed, as the site's Table S2 says it
        head += f' {found}'
    other = tot - same
    if not other:
        return head
    parts = [f'{v:,} {t}' for v, t in ((a.get('differ_same_value_other_name') or 0, 'are the same value under another name'),
                                       (a.get('differ_catlog_right') or 0, "are values the paper supports as CatLog reads them "
                                                                           "(the earlier record's number or label was wrong)"),
                                       (a.get('differ_rounding') or 0, 'differ by rounding'),
                                       (a.get('differ_not_comparable') or 0,
                                        "are left out by CatLog's reading rules (a reprint, a Hill fit)")) if v]
    wrong = a.get('differ_catlog_wrong') or 0
    tail = ('none is a CatLog value found wrong' if not wrong else
            f"{wrong:,} {'is a CatLog value' if wrong == 1 else 'are CatLog values'} found wrong")
    listed = (', '.join(parts[:-1]) + ' and ' + parts[-1]) if len(parts) > 1 else ''.join(parts)
    split = _differ_checked(a)
    if split is None:  # an agreement block without the counts: the older sentence
        return f"{head} Of the other {other:,}, {listed}; {tail}." if listed else f'{head} Of the other {other:,}, {tail}.'
    checked, pending = split
    rest = f" {pending:,} {'is' if pending == 1 else 'are'} not yet checked." if pending else ''
    if not checked:
        return f"{head} The other {other:,} {'is' if other == 1 else 'are'} not yet checked against the paper."
    return (f"{head} AI agents checked {checked:,} of the other {other:,} against the paper: "
            + (f"{listed}; {tail}." if listed else f"{tail}.") + rest)


def _reread_check(q):
    """The release note's re-read check (round 14), from quality.agreement as _reread_sentence words it: the share of
    approved values CatLog matches, then of the other values how many AI agents checked against the paper and how many
    of those are CatLog values found wrong, and how many are not yet checked; [] without an agreement block (the older
    v2_found pair: the share alone)."""
    a = q.get('agreement') or {}
    same, tot = (a.get('agree') or 0, a['values_approved']) if a.get('values_approved') else (q.get('v2_found'), q.get('v2_approved_total'))
    if not tot:
        return []
    head = (f"where CatLog has re-read a paper the reviewers checked, its value now matches the approved value for {same:,} "
            f"of {tot:,} ({100 * same / tot:.1f}%)")
    if a.get('values_approved') and (found := _errors_found(a)):  # as _reread_sentence and the site's Table S2 say it
        head += '; ' + found[0].lower() + found[1:-1]
    other = tot - same
    if not a.get('values_approved') or not other:
        return [head]
    pending, wrong = a.get('differ_not_adjudicated') or 0, a.get('differ_catlog_wrong') or 0
    checked = other - pending
    found = (f'none is a CatLog value found wrong' if not wrong else
             f"{wrong:,} {'is a CatLog value' if wrong == 1 else 'are CatLog values'} found wrong")
    if not checked:
        tail = f"the other {other:,} {'is' if other == 1 else 'are'} not yet checked"
    else:
        tail = (f"AI agents checked {checked:,} of the other {other:,} against the paper and {found}"
                + (f"; {pending:,} {'is' if pending == 1 else 'are'} not yet checked" if pending else ''))
    return [f'{head}; {tail}']


def _reread_lines(q):
    s = _reread_sentence(q)
    return [s] if s else []



# the README's "Compared with databases" words (round 9 brief sections 2 and 6): the download's result codes, each the
# value's database_status under another name (its meaning is said once, under Fields); not_listed_reason, found_by and
# cause are database_new_reason, database_found_by and database_cause; short labels for the reasons no database lists
# a value; why a database number is not in CatLog (dbcompare.UNREPRODUCED; contribution report 1.4)
RESULT_WORDS = (('same', 'confirmed'), ('same_other_label', 'same_number_other_label'), ('corrects', 'corrected'),
                ('differs', 'differs'), ('not_listed', 'new'))  # (result, database_status); then not_compared
REASON_WORDS = {
    'ratio_only': 'kcat and Km listed', 'condition_absent': 'other values listed', 'substrate_absent': 'substrate not listed',
    'metric_absent': 'parameter not listed', 'variant_absent': 'variant or organism not listed',
    'paper_not_in_databases': 'paper not listed'}
UNREPRODUCED_WORDS = {
    'paired_with_different_number': 'paired with a CatLog value as a different number (corrects or differs)',
    'another_measurement_per_paper_check': 'another record of the paper, found by an AI check of the paper',
    'rejected_by_catlog_checks': "rejected by CatLog's checks",
    'catlog_kept_no_values_from_paper': 'CatLog kept no value from the paper (retracted, a review, no kinetic constants)',
    'no_substrate_named_paper_has_several': 'no substrate named, and the paper has several',
    'reprinted_from_other_work': 'reprinted by the paper from other work (CatLog leaves reprints out)',
    'next_to_other_quantity': 'next to Ki, Vmax or another quantity in the text',
    'possible_catlog_miss': 'in the paper text with 3 or more significant digits or a power of ten: a possible CatLog '
                            'miss, not yet checked',
    'possible_miss_weak': 'only a 2-digit number in the paper text: a weak possible miss',
    'paper_awaits_supplement': "the paper's supplement is not read yet",
    'not_in_paper_text': 'not in the paper text under any unit factor',
    'no_text_on_disk': 'no paper text to search'}
# two reasons are numbers CatLog does have, as a kcat/Km it calculated or under another parameter: in the one total of
# numbers that match no value CatLog read, as the site's note under Values compared with databases counts them
# (statsNotReproducedText, fix pass after round 16b: Stats had 17,807 "that CatLog does not have" where these notes had
# 20,403), with their own words
HELD_WORDS = {'equals_catlog_calculated_ratio': 'equal to a kcat/Km CatLog calculated (the paper prints none)',
              'another_parameter_in_catlog': 'in CatLog under another parameter'}
MISS_REASONS = ('possible_catlog_miss', 'possible_miss_weak')  # said together too, as the site does
def _names_and(names):
    return ', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else ''.join(names)


def _blind_words(fold, q):
    """How the readers use the databases, in the README's "Compared with databases" (round 16b quality review: "never
    used to read or check a value" contradicted the Quality section): meant to work blind, the comparison on the
    finished values, then the paper checks of the differences and what they found (quality.catlog_errors
    difference_check, database_check in marks written before human_review renamed it) and the papers an agent read with
    database values in view (quality.exposed), as _exposure_line counts them; once every paper sent back has been added
    again (reread_blind_done), that all of them have since been read or checked again without them. `fold`: the
    smallest difference checked (summary.database_comparison checked_from_factor)."""
    out = 'Readers and checkers are meant to work without database values; the comparison runs on the finished values.'
    q = q or {}
    if 'catlog_errors' in q:
        found = q['catlog_errors'].get('difference_check') or q['catlog_errors'].get('database_check') or {}
        n, papers = found.get('values') or 0, found.get('papers') or 0
        which = (f'Differences of {fold:g}-fold or more' if isinstance(fold, (int, float)) and fold > 1 else 'Large differences')
        out += (f' {which} are then checked against the paper by an AI agent; '
                + (f"those checks have found {n:,} CatLog {'value' if n == 1 else 'values'} wrong in {papers:,} "
                   f"{'paper' if papers == 1 else 'papers'} (Quality checks)." if n else
                   'those checks have found no CatLog value wrong so far.'))
    e = q.get('exposed') or {}
    if e.get('papers'):
        when = f"Between {_span(e['first'], e['last'])}, a" if e.get('first') and e.get('last') else 'A'
        sent = e.get('reread_blind') or 0
        done = sent and e.get('reread_blind_done') == sent  # every paper sent back has been added again since
        again = ('.' if not sent else
                 ('; all of them have since been read or checked again without them.' if done else
                  '; they were sent back to be read or checked again without them.') if sent >= e['papers'] else
                 (f"; {sent:,} of them were sent back, and all {sent:,} have since been read or checked again without "
                  'them (Quality checks).' if done else
                  f"; {sent:,} of them were sent back to be read or checked again without them (Quality checks)."))
        out += (f" {when} reading or checking agent opened database values or records CatLog held for the paper before on "
                f"{e['papers']:,} {'paper' if e['papers'] == 1 else 'papers'}{again}")
    return out


def _comparison_section(manifest, receipt, q=None):
    """The README's "Compared with databases" section (round 9 brief section 6) from the manifest's
    summary.database_comparison and database_comparison_download and the build receipt; [] without them. Every number
    comes from the data; a share is given only on a base of 1,000 values or more. `q`: the marks file's quality object
    (human_review.quality), for how the readers use the databases (_blind_words)."""
    dc = (manifest.get('summary') or {}).get('database_comparison') or {}
    a = (dc.get('values') or {}).get('all') or {}
    if not a:
        return []
    srcs = dc.get('sources') or []
    names = [e['display'] for e in srcs] or [SOURCE_DISPLAY.get(x, x) for x in DATABASES]
    same, other, corr, diff = (a.get(k, 0) for k in ('confirmed', 'same_number_other_label', 'corrected', 'differs'))
    listed_none = a.get('new', 0) + a.get('new_paper_not_in_databases', 0) + a.get('new_ratio_only', 0)
    calculated, paired = a.get('not_compared', 0), same + corr + diff
    compared = same + other + corr + diff + listed_none
    papers = dc.get('papers_compared') or 0  # papers with a compared value; papers_read: with a record on the site
    read = dc.get('papers_read') or papers
    only_not_compared = f' ({read - papers:,} of the {read:,} papers read have only values that are not compared)' if read > papers else ''
    pct = lambda n, d: f' ({100 * n / d:.1f}%)' if d >= 1000 else ''
    found = Counter()
    for v in ((dc.get('corrections') or {}).get('by_cause_found_by') or {}).values():
        found.update(v)
    found_text = (f"{found['paper_check']:,} found by an AI check of the paper, {found['factor_cross_checked']:,} by an exact "
                  f"factor that the paper's own kcat ÷ Km agrees with")
    # the corrections are a lower bound on the databases' errors: only a difference of checked_from_factor-fold or more
    # is checked (item 6 of work/publication_strategy_20261021/FIXES_FOR_MAIN_CHAT.md); an older summary does not say it
    fold = dc.get('checked_from_factor')
    if isinstance(fold, (int, float)) and fold > 1:
        found_text += f"; a lower bound, as only differences of {fold:g}-fold or more are checked"
    exact = ((dc.get('differences') or {}).get('by_cause') or {}).get(EXACT_FACTOR, 0)
    date, data_id = manifest['generated_at'][:10], manifest['content_sha256'][:10]
    dl = manifest.get(COMPARISON_KEY) or {}
    out = [f"Each printed kcat, Km and kcat/Km read from the paper is compared with the values {_names_and(names)} list "
           'for the same paper: the same substrate, variant and organism, with pH and temperature used to pair values. '
           + _blind_words(fold, q),
           'The databases compared (version, the date the copy was taken, its kcat, Km and kcat/Km values with a paper ID, '
           'the papers they cite, and the SHA-256 of the file they come from):']
    for e in srcs:
        head = e['display'] + (f" {e['version']}" if e.get('version') else '') + \
            (f" (retrieved {e['retrieved']})" if e.get('retrieved') else '')
        out.append(('  ', f"{head}: {e.get('rows', 0):,} values from {e.get('papers', 0):,} papers"
                          + (f"; SHA-256 {e['sha256']}." if e.get('sha256') else '.')))
    if dl:
        out.append(f'The file ({_saved(date, "database-comparison")}, UTF-8 CSV) has one line per value and database '
                   'that lists its paper, and one line with database empty for a value no database lists and for a '
                   'kcat/Km CatLog calculated. Columns: data_id and snapshot_date (this snapshot); record_key (joins the '
                   "Full data); measurement_id (CatLog's own ID for the record), pubmed_id, doi, enzyme, ec_number, organism, "
                   'variant, substrate; parameter '
                   '(kcat, Km or kcat/Km); catlog_value and catlog_unit (s⁻¹, mM, mM⁻¹ s⁻¹); as_printed (number and unit '
                   'as printed); location (where in the paper); result (below); found_by, cause and not_listed_reason '
                   '(database_found_by, database_cause and database_new_reason under Fields); database, database_version '
                   'and database_retrieved (as listed above); database_kind (the kind in database_by_source under Fields); '
                   "database_value and database_unit (its number in CatLog's units); factor (database_value ÷ CatLog's "
                   'number, to 4 significant figures); database_label (for same_number_other_label: the substrate, '
                   'variant or organism label the database lists the number under, at most 90 characters); '
                   'review_result and review_round (empty until a human review of disagreements); line (the record '
                   "page's sentence for the value).")
    out.append('result: the database_status under Fields, as ' + ', '.join(f'{k} ({s})' if k != s else k for k, s in RESULT_WORDS)
               + ' or not_compared (a kcat/Km CatLog calculated as kcat ÷ Km; the paper prints none).')
    # the shares of all compared values; how corrections were found, the exact factors and the paired values are said
    # once, in the paragraph to cite below
    out.append(f"In this snapshot {compared:,} values read from {papers:,} papers were compared{only_not_compared}: "
               f"{same:,}{pct(same, compared)} are the number a database lists, {other:,}{pct(other, compared)} the same "
               f"number under another label, {corr:,}{pct(corr, compared)} correct a database's number, {diff:,}"
               f"{pct(diff, compared)} differ with the cause not yet known and {listed_none:,}{pct(listed_none, compared)} "
               f"are in none of the databases. {calculated:,} kcat/Km values CatLog calculated are not compared. A value "
               'counts once however many databases list it; per database: values_by_database in the manifest, or the '
               'database_kind column.')
    why = ((dc.get('values') or {}).get('not_listed_by_reason') or {}).get('all') or {}
    if why:
        out.append('Why no database lists a value (not_listed_reason): ' + '; '.join(
            f"{REASON_WORDS[k]} ({k}) {n:,}" if k in REASON_WORDS else f'{k} {n:,}'
            for k, n in sorted(why.items(), key=lambda z: -z[1])) + '.')
    unrep = {k: n for k, n in ((dc.get('not_reproduced') or {}).get('distinct') or {}).items() if n}
    if unrep:
        n, words = sum(unrep.values()), {**UNREPRODUCED_WORDS, **HELD_WORDS}
        missed = sum(unrep.get(k) or 0 for k in MISS_REASONS)
        out.append(f"The databases also list {n:,} {'number' if n == 1 else 'numbers'} for these papers that "
                   f"{'matches' if n == 1 else 'match'} no value CatLog read from them (each paper, parameter and number to "
                   '3 significant figures counted once), by the first reason that applies: '
                   + '; '.join(f'{words.get(k, k)} {c:,}' for k, c in sorted(unrep.items(), key=lambda z: -z[1])) + '.'
                   + (f" Together, {missed:,} may be {'a value' if missed == 1 else 'values'} CatLog missed, not yet checked."
                      if all(unrep.get(k) for k in MISS_REASONS) else ''))
    out.append("The values no database lists: pandas.read_csv(path)[lambda d: d.result == 'not_listed'].")
    inputs = dc.get('inputs') or {}
    out.append('To reproduce: the database values come from the files above, merged into one table '
               f"(db_values.tsv{', SHA-256 ' + inputs['db_values.tsv'] if inputs.get('db_values.tsv') else ''}); the AI checks "
               'of the paper are in database_corrections.tsv'
               f"{' (SHA-256 ' + inputs['database_corrections.tsv'] + ')' if inputs.get('database_corrections.tsv') else ''}; "
               f"CatLog's values are its export with SHA-256 {receipt.get('catlog_wide_sha256', '')}, built with CatLog code "
               f"commit {receipt.get('v2_commit', '')}. The comparison is automatic: the same files give the same lines.")
    # the values none of them lists, by why (round 13: not all of them are new data): a printed kcat/Km whose kcat and
    # Km they list, other numbers for the substrate and variant, and nothing for the substrate, variant, organism,
    # parameter or paper; said only when the reasons add up to the count
    ratio_only, other_numbers = why.get('ratio_only', 0), why.get('condition_absent', 0)
    nothing = sum(why.get(k, 0) for k in ('substrate_absent', 'variant_absent', 'metric_absent', 'paper_not_in_databases'))
    split = (f": {ratio_only:,} printed kcat/Km values whose kcat and Km they list, {other_numbers:,} where they list other "
             f"numbers for the same substrate and variant, and {nothing:,} for a substrate, variant, organism, parameter or "
             'paper they list nothing for') if why and ratio_only + other_numbers + nothing == listed_none else ''
    out.append(f'To cite: "Of {compared:,} kinetic values (kcat, Km and kcat/Km) CatLog read from {papers:,} papers and '
               f"compared with {_names_and(names)} for the same paper, {listed_none:,}{pct(listed_none, compared)} are listed by "
               f"none of them{split}. Where a database lists a number for the same value ({paired:,} values), it is the "
               f"paper's number for {same:,}{pct(same, paired)}; {corr:,} values correct a database's number ({found_text}) "
               f"and {diff:,} differ with the cause not yet known ({exact:,} by an exact factor not yet checked against the "
               f"paper).\" CatLog snapshot {date}, data ID {data_id}.")
    return out

def _saved(date, part):
    """A download's file name as the site saves it (catlog-static.js: the snapshot's date, catlog-2026-10-18-full.jsonl.gz),
    which the Guide's Data ID check names too; the server's name carries the data ID instead."""
    return f"catlog-{date}-{part}.{'csv' if part in ('database-comparison', 'not-detected', 'values') else 'jsonl'}.gz"


def _values_count(entry):
    """The values file's lines in words: its printed values and the kcat/Km calculated from kcat and Km (the site's
    'values' are the printed ones, 2026-11-06 Stats audit X2), or its lines for a manifest that does not count those."""
    rows, calc = entry['rows'], entry.get('calculated')
    if isinstance(calc, int) and 0 <= calc <= rows:
        return f'{rows - calc:,} printed values and {calc:,} kcat/Km calculated from kcat and Km, {rows:,} lines'
    return f'{rows:,} lines'


def _readme(manifest, receipt, quality=(), q=None):
    """README_FIRST.txt for people who download the data, written whole from the staged manifest and the build receipt
    (user, 2026-10-12: its snapshot details and source list are CatLog's to write). Sections in the order of website
    plan P29; `quality`: the lines of its 'Quality checks' section (_quality_lines); none, no section. `q`: the quality
    object those lines come from for the words of "Compared with databases"."""
    dist = manifest['summary']['distributions']
    lic = _licenses(dist['source_license'])
    total, accepted = manifest['total_rows'], manifest['summary']['trust_snapshot']['accepted_rows']
    v2, date, data_id = receipt['v2_measurements'], manifest['generated_at'][:10], manifest['content_sha256'][:10]
    srcs = {e['key']: e for e in manifest.get('source_databases') or []}
    skid, unknown = (srcs.get('skid') or {}).get('row_count', 0), _count(dist.get('source_db'), 'unknown')
    full, table, cov = manifest['enriched_download'], manifest['table_download'], manifest['enriched_download'].get('coverage') or {}
    dc = manifest['summary'].get('database_comparison') or {}
    dbs = dc.get('sources') or []  # the compared databases (C7)
    # the papers read that gave values (the manifest's papers_read; build.json's v2_papers_with_values is the same count;
    # papers_finished also counts those that gave none)
    papers_read = dc.get('papers_read') or receipt.get('v2_papers_with_values', len(receipt['v2_papers']))
    on_review = _count(dist.get('accepted_basis'), 'human review')  # said only when there is one (round 14)
    # the papers CatLog re-reads are those the enzyme databases cite for their values; the few no compared database
    # lists (a literature search found them) are counted, so the sentence stays true as they grow
    uncited = len(dc.get('papers_not_in_databases') or []) if dc else None
    cited = ('' if uncited is None else ', each cited by a compared database' if not uncited
             else f', {papers_read - uncited:,} cited by a compared database')
    sources = [(f"Read from the paper by CatLog ({k}): {lic['catlog']:,} records, licensed as above; "
                f"{e['row_count'] - lic['catlog']:,} earlier paper extractions: as published (see paper).")
               if k == 'primary_paper_direct' else
               f"{e['name']} ({k}): {e['row_count']:,} records; {e['license']}" + (f"; {e['citation_url']}" if e.get('citation_url') else '')
               for k, e in srcs.items()] + ([f'No source recorded (unknown): {unknown:,} records; see source.'] if unknown else [])
    fields = [f.replace(ALL_DATABASES, _names(e['name'] for e in dbs) or ALL_DATABASES) if isinstance(f, str) else f
              for f in FIELDS]  # the field notes name the databases compared in this build, as the lines do
    sections = [
        ('CatLog in brief', [
            'CatLog is a database of enzyme kinetic values (kcat, Km, kcat/Km), each with its enzyme, organism, '
            f'substrate, variant, assay conditions and source. This snapshot ({date}) holds {total:,} records, '
            f'{accepted:,} of them accepted.',
            # (round 17, the user: "how are they going to know the values and records?": the words, once, first)
            'Words: a record is one line of the Full data and Table files (one row of Browse): one enzyme, wild type or a '
            'variant, with one '
            'substrate under one set of assay conditions in one paper. A value is one number, a kcat, a Km or a kcat/Km; '
            'a record holds up to three. A paper is one publication.',
            f"{v2:,} records are labelled Read from the paper ({papers_read:,} papers{cited}). The other {total - v2:,} "
            "are Not yet re-read: from CatLog's earlier version, built from the enzyme databases and partly checked against "
            'the papers; replaced when CatLog reads the paper.']),
        ('How the values were obtained and checked', [
            f'Read from the paper: {METHOD}',
            'Not yet re-read: values from enzyme databases (BRENDA, SABIO-RK, the Open Enzyme Database (OED), UniProt '
            "and SKiD), earlier paper extractions and records with no source recorded. CatLog's earlier version screened them "
            'with AI models and automated checks until 2026-10-09.',
            f'Review result (verification_status): verified or corrected = Accepted ({accepted:,}); manual_review_required '
            '= Not confirmed (the earlier review left a question open); unverified or mathematically_inferred = Not checked; '
            'disputed = Disputed. An accepted record needs a linked paper: '
            f"{_count(dist.get('public_trust_basis'), 'identity_only'):,} records not yet re-read that the earlier review "
            'accepted have no PMID or DOI (public_trust_basis identity_only), so they are mathematically_inferred, not '
            'accepted.' + (f" {on_review:,} {'record' if on_review == 1 else 'records'} not yet re-read "
                           f"{'is' if on_review == 1 else 'are'} accepted on human review (accepted_basis, under Fields)."
                           if on_review else '')]),
        ('Quality checks', list(quality)),
        ('Files', [
            f'Full data, {_saved(date, "full")} ({full["path"]} on the server): gzip-compressed JSON Lines, one record per '
            'line, every field below.',
            f'Table, {_saved(date, "table")} ({table["path"]} on the server): the same records in the same order, without the '
            'fields marked * below (no sequences, SMILES, paper IDs, printed values or assay_conditions_summary); join it to '
            'Full data on record_key.',
            'Load with pandas: pandas.read_json(path, lines=True, compression="gzip").',
            *([f'Compared with databases, {_saved(date, "database-comparison")} ({manifest[COMPARISON_KEY]["path"]} on the '
               'server): gzip-compressed CSV, described under Compared with databases below; load with pandas.read_csv(path).']
              if manifest.get(COMPARISON_KEY) else []),
            *([f'Not detected, {_saved(date, "not-detected")} ({manifest[NOT_DETECTED_KEY]["path"]} on the server): '
               f'gzip-compressed CSV, one line per value a paper reports as not detected or prints only as a bound '
               f'({manifest[NOT_DETECTED_KEY]["rows"]:,} values from {manifest[NOT_DETECTED_KEY]["papers"]:,} papers so far): '
               'a mutant with no measurable activity, a Km above the highest concentration tested. They are the papers\' '
               'own statements; CatLog never turns them into numbers, and they are in no value column, chart, count or '
               'database comparison of the other files. Columns: data_id, snapshot_date; record_key (the record whose '
               'values they sit beside, empty when the variant has no measured value); pubmed_id, doi, enzyme, ec_number, organism, '
               'uniprot_id, variant, construct, substrate; parameter (kcat, Km or kcat/Km); reported (not detected, below '
               'or above); limit_value and limit_unit (the printed limit in s⁻¹, mM or mM⁻¹ s⁻¹, when one is printed); '
               'as_printed; detection_limit_as_printed; location; printed_line; ph; temperature_c; conditions; note. '
               'Load with pandas.read_csv(path).']
              if manifest.get(NOT_DETECTED_KEY) else []),
            *([f'Values ({manifest[VALUES_KEY]["path"]} on the server): gzip-compressed CSV, one value per line, from '
               f'the {manifest[VALUES_KEY]["records"]:,} records of papers read in full ({_values_count(manifest[VALUES_KEY])}), '
               'for machine learning: record_key, pubmed_id, doi, ec_number and ec_source, enzyme, organism and '
               'organism_source, taxon_id, uniprot_id, wild_type, mutation_signature, sequence (the measured enzyme\'s; '
               'empty where CatLog has none, never the wild type\'s for a mutant), substrate, smiles and smiles_source, '
               'substrate_inchikey, substrate_chebi, substrate_pubchem_cid; parameter (kcat, Km or kcat/Km), value, '
               'log10_value, unit, err (the printed ±, converted with the value), value_origin (printed, or calculated '
               'for a kcat/Km worked out from kcat and Km); ph, temperature_c, conditions (the assay and per-value notes: '
               'apparent, Hill fit, measured as Ki, the cosubstrate), verification_status, accepted_basis and '
               'condition_flags as in the Full data. CatLog\'s reading is CC BY 4.0; a substrate structure keeps its '
               'source\'s terms (smiles_source; SKiD: CC BY-NC-ND 4.0). Load with pandas.read_csv(path).']
              if manifest.get(VALUES_KEY) else []),
            'Records of one paper share pubmed_id: split training and test sets by paper or by primary_uniprot_id.']),
        ('Units', [
            'kcat in s⁻¹ (kcat_unit "s^(-1)"); Km and Ki in mM (km_unit, ki_unit "mM"); kcat/Km in mM⁻¹ s⁻¹ '
            '(kcat_over_km_unit "s^(-1)*mM^(-1)"); temperature_c in °C, temperature_k in K.',
            'Always read the *_unit field: empty means the source gave no unit and the number is not in the column unit '
            '(condition_flags then has unit_not_recorded_kcat or unit_not_recorded_km); a few records not yet re-read keep '
            'another unit there (min⁻¹, mg/mL, µM, M⁻¹ s⁻¹).',
            'Records read from the paper keep the printed precision: each printed value is converted to the units above and '
            "rounded to the printed number's significant figures (at least 2); a kcat/Km calculated from kcat and Km has "
            'the significant figures of the less precise of the two.',
            'Empty means the paper or source gives none; "Unknown" (EC, organism, substrate): not stated in the paper or the '
            'source database.']),
        ('Fields (* = Full data only)', fields),
        ('Compared with databases', _comparison_section(manifest, receipt, q)),
        ('License', [
            f"Read from the paper by CatLog: {lic['catlog']:,} records under CC BY 4.0 (CatLog compilation): cite the snapshot "
            "and the CatRange paper below. Quoted paper text (the printed lines in proof_lines) remains the publisher's. "
            f'Their source_license: "{V2_LICENSE}".',
            "The other records keep their source database's license; source_license names each license of a merged record:",
            ('  ', f"CC BY 4.0: {lic['cc_by']:,} records from BRENDA, OED and UniProt."),
            ('  ', f"SABIO-RK terms (free for academic use): {lic['sabio']:,} records, alone or merged with a CC BY 4.0 one."),
            ('  ', f"CC BY-NC-ND 4.0 (non-commercial use only, no derivatives): {lic['nc_nd']:,} records whose source_license "
                   f"includes it, {skid:,} with SKiD as their source and {lic['nc_nd'] - skid:,} BRENDA, SABIO-RK or UniProt "
                   'records a SKiD listing was merged into. Filter on source_license, not on source_db.'),
            ('  ', f"As published (see paper): {lic['published']:,} records from earlier paper extractions. See source: "
                   f"{lic['other']:,} records."),
            manifest.get('curation_layer_license') or 'For reuse of CatLog review notes and corrections, contact the '
                                                      'Chowdhury Lab.',
            'Sources (source_db; a record merged from several databases counts under each):',
            *(('  ', s) for s in sources)]),
        ('Cite', [
            f'CatLog snapshot {date} (data ID {data_id}), Chowdhury Lab, https://catlog.structf.studio',
            'Sajeevan, K. A., et al. (2026). CatRange enables robust prediction of enzyme variant kinetic regimes. PNAS Nexus, '
            'pgag309. doi: 10.1093/pnasnexus/pgag309 (https://doi.org/10.1093/pnasnexus/pgag309). It describes CatLog-27k '
            '(27,176 kinetic records curated from BRENDA and SABIO-RK), the set its models were trained on; CatLog is the '
            'growing database that followed.',
            'If you use records from a database, cite that database as it asks: BRENDA, SABIO-RK, SKiD (Zenodo 15355031), the '
            'Open Enzyme Database, UniProt (links under License).',
            'Keep the file you used: older snapshots leave the site over time.']),
        ('Snapshot details', [
            f"Records: {total:,}. Generated (UTC): {manifest['generated_at']}.",
            f'Data ID {data_id}: the first 10 characters of the SHA-256 of the decompressed Full data (gunzip -c '
            f"{_saved(date, 'full')} | shasum -a 256): {manifest['content_sha256']}.",
            f"Full data file {Path(full['path']).name}, SHA-256 {full['sha256']}.",
            f"Table file {Path(table['path']).name}, SHA-256 {table['sha256']}.",
            *([f"Compared with databases file {Path(manifest[COMPARISON_KEY]['path']).name}, SHA-256 "
               f"{manifest[COMPARISON_KEY]['sha256']}, {manifest[COMPARISON_KEY]['rows']:,} lines."] if manifest.get(COMPARISON_KEY) else []),
            *([f"Values file {Path(manifest[VALUES_KEY]['path']).name}, SHA-256 {manifest[VALUES_KEY]['sha256']}, "
               f"{manifest[VALUES_KEY]['rows']:,} lines."] if manifest.get(VALUES_KEY) else []),
            *([f"Not detected file {Path(manifest[NOT_DETECTED_KEY]['path']).name}, SHA-256 "
               f"{manifest[NOT_DETECTED_KEY]['sha256']}, {manifest[NOT_DETECTED_KEY]['rows']:,} lines."] if manifest.get(NOT_DETECTED_KEY) else []),
            f"Source file this snapshot was built from: SHA-256 {manifest['source_sha256']}.",
            f"Records with a sequence: {cov.get('sequence', 0):,} (wild-type sequence {cov.get('wild_type_sequence', 0):,}, "
            f"variant sequence {cov.get('variant_sequence', 0):,}); records with SMILES: {cov.get('smiles', 0):,}."])]
    out = ['CatLog dataset notes', '']
    for title, items in sections:
        if not items:
            continue
        out.append(title)
        for item in items:  # a bullet, or (indent, bullet) for a bullet under the one before
            pad, text = item if isinstance(item, tuple) else ('', item)
            out.append(textwrap.fill(text, 118, initial_indent=pad + '- ', subsequent_indent=pad + '  ',
                                     break_on_hyphens=False, break_long_words=False))
        out.append('')
    return '\n'.join(out)


def _accepted(table, keys):
    """The `keys` (an old record_key or a v2 measurement_key) that the staged table shows as accepted (verified or
    corrected): the page shows 'human-checked' only on those."""
    out = set()
    with gzip.open(table, 'rt') as fh:
        for line in fh:
            r = json.loads(line)
            k = r.get('record_key') if r.get('record_key') in keys else r.get('measurement_key')
            if k in keys and r.get('verification_status') in ('verified', 'corrected'):
                out.add(k)
    return out


# commit subjects that are not visitor-facing (the site's own checks and design notes), wherever the words stand
SKIP_SUBJECT = re.compile(r'browser checks?\b|design notes\b|DESIGN\.md|^(?:the )?tests?\b', re.I)
SITE_LIST_MAX = 6  # more visitor-facing subjects than this: the note gives their number, or the chat's own bullets (--note)


def note_bullets(path):
    """The visitor bullets for a release's site changes (`site stage --note FILE`, written by the chat that made the
    changes; round 16b quality review: commit subjects in commit order put internal ones first and the news among
    'smaller fixes'): one bullet per non-empty line, a leading '-' or '*' dropped, '#' lines skipped."""
    out = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            out.append(re.sub(r'^[-*]\s*', '', line))
    return out


def _site_lines(picked, bullets=None):
    """The release note's site changes: the chat's bullets when given; else the visitor-facing commit subjects
    (SKIP_SUBJECT left out, conventional-commit prefixes dropped) when there are at most SITE_LIST_MAX, else their
    number only, since a list cut by commit order is not a list of what matters."""
    if bullets:
        return '- Site changes:\n' + ''.join(f'  - {b.rstrip(".")}.\n' for b in bullets)
    if picked is None:  # not known (site changes are commits to cloudflare/ since 2026-11-03): no line rather than a guess
        return ''
    strip = lambda x: re.sub(r'^(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore)(?:\([\w-]+\))?!?:\s*', '', x)
    subjects = [s[:1].upper() + s[1:] for x in picked if not SKIP_SUBJECT.search(x) and not SKIP_SUBJECT.search(s := strip(x))]
    if not subjects:
        return '- Layout, charts and filters are unchanged.\n'
    if len(subjects) > SITE_LIST_MAX:
        return f"- Site changes: {len(subjects):,} changes to the site's pages, each a commit in the site's history.\n"
    return '- Site changes:\n' + ''.join(f'  - {s.rstrip(".")}.\n' for s in subjects)


def _check_lines(quality, human_checked):
    """The release note's checks, one bullet each (round 16b quality review: one sentence of 95 words was too long):
    AI audits, human review (the records people checked, as one review the way Stats, Team and the README count it,
    then the human-checked records with their own basis; the numbers audit, 2026-11-06) and agreement with it."""
    out = []
    ci = re.fullmatch(r'(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)', str(quality.get('audit_wrong_ci95') or ''))
    if quality.get('audit_values'):
        n, d = quality['audit_values'], quality.get('audit_wrong') or 0
        t, td = quality.get('audit_targeted_values') or 0, quality.get('audit_targeted_wrong') or 0
        out.append(f"AI audits: {n:,} values audited at random so far, {d:,} wrong and removed"
                   + (f" ({_audit_share(d, n, ci)})" if ci else '')
                   + (f"; {t:,} more audited because an audit sample or a database check pointed to them, {td:,} wrong "
                      'and removed' if t else ''))
    human = []
    r = _one_review(quality.get('review') or {})
    if r.get('entries'):
        b, nopaper = _review_basis(r)
        n, d = b['entries'], b.get('value_disputed', 0)
        human.append(f"people checked {n:,} records against their papers: no value disputed on {n - d:,} ({_share(n - d, n)})"
                     + (f"; {nopaper:,} more had no PMID or DOI" if nopaper else ''))
    if human_checked is not None:
        human.append(f"{human_checked:,} accepted records are human-checked: a human reviewer approved every kcat and Km "
                     "shown, on this record or as the same values for this paper")
    if human:
        out.append('Human review: ' + '. '.join(x if i == 0 else x[:1].upper() + x[1:] for i, x in enumerate(human)))
    out += [f'Agreement with the human review: {x}' for x in _reread_check(quality)]
    return out


def _release_note(date, manifest, receipt, picked, quality, human_checked, retire_note='', bullets=None):
    """The public release note in plain words (build.json keeps the receipt: v2 commit, export hash, base generation).
    `picked`: the subjects of the site changes in this release; `bullets`: the chat's visitor bullets for them
    (note_bullets), which replace the subjects."""
    with_values = receipt.get('v2_papers_with_values', len(receipt['v2_papers']))
    empty, read, v2 = len(receipt['v2_papers']) - with_values, len(receipt['v2_papers']), receipt['v2_measurements']
    site = _site_lines(picked, bullets)
    checks = _check_lines(quality, human_checked)
    on_review = receipt.get('accepted_on_human_review') or 0
    rules = (f"- Review rules: an accepted record needs a linked paper, so {receipt['not_accepted_no_paper']:,} records not yet "
             're-read without a PMID or DOI are not counted as accepted'
             + (f"; {on_review:,} {'record' if on_review == 1 else 'records'} not yet re-read {'is' if on_review == 1 else 'are'} "
                f"accepted because a human reviewer approved {'its' if on_review == 1 else 'their'} values" if on_review else '')
             + '.\n') if 'accepted_on_human_review' in receipt else ''
    return (f"# CatLog release {date}\n\n"
            f"- Records: {manifest['total_rows']:,}, of them {receipt['accepted']:,} accepted ({v2:,} of these read from the "
            f"paper, {receipt['accepted'] - v2:,} not yet re-read). Data ID {manifest['content_sha256'][:10]}.\n"
            f"- Read from the paper: CatLog read {read:,} papers; {with_values:,} of them give {v2:,} records"
            f"{f' and {empty:,} give none' if empty else ''}. These records replace the papers' "
            f"{receipt['old_rows_replaced']:,} records of CatLog's earlier version ({receipt['old_accepted_replaced']:,} of them accepted)"
            f"{'; papers that give none keep no earlier records' if empty else ''}.\n"
            f"  {METHOD}\n"
            "- Records not yet re-read: CatLog's earlier version, the October 7, 2026 snapshot.\n" + rules
            + ('- Checks:\n' + ''.join(f'  - {c}.\n' for c in checks) if checks else '') + site
            + (f"- Retired from the site (they stay in git history): {retire_note}.\n" if retire_note else ''))


def stage(note=None):
    """A fresh release folder from cloudflare/site_base + the October 7 staging steps + the site's own checks, swapped in
    as site_build/release only when every check passed. `note`: a file of visitor bullets for the release note's site
    changes (note_bullets)."""
    bullets = note_bullets(note) if note else None
    receipt = json.loads((BUILD / 'build.json').read_text())
    if receipt.get('problems'):
        sys.exit('the last build has problems: `site build` again first')
    bundle = Path(receipt['bundle'])
    if 'source_license' not in _manifest((bundle / 'data' / 'manifest.js').read_text())['summary']['distributions']:
        sys.exit('the last build predates the review rules and licenses of 2026-10-12 (export_site.py): `site build` again')
    lock = open(STAGE_LOCK, 'w')  # released when stage() returns or exits
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit('another `site stage` or a publish is running (site_build/stage.lock): wait for it')
    base = BASE_DIR.relative_to(ROOT).as_posix()
    if run(['git', 'status', '--porcelain', '--', base], cwd=ROOT, capture=True).stdout.strip():
        sys.exit(f'{base} has uncommitted changes or untracked files: commit them first (a site change), then stage')
    receipt.pop('staged', None)
    (BUILD / 'build.json').write_text(json.dumps(receipt, indent=1))
    fresh = BUILD / 'release.new'  # stays for a look when a check fails; release/ is replaced only after they pass
    if fresh.exists():
        shutil.rmtree(fresh)
    for rel in filter(None, run(['git', 'ls-files', '-z', '--', base], cwd=ROOT, capture=True).stdout.split('\0')):
        out = fresh / Path(rel).relative_to(base)  # the committed site files only
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, out)
    site_base_commit = run(['git', 'log', '-1', '--format=%H', '--', base], cwd=ROOT, capture=True).stdout.strip()
    picked = None  # site changes are commits to cloudflare/ now: the release note lists them only from --note bullets
    cat = fresh / 'tools' / 'catlog-static'
    (cat / 'data').mkdir(exist_ok=True)
    marks = bundle / 'data' / 'human-review-marks.json'  # which records a human reviewer checked, made with this bundle
    if not marks.exists():
        marks = ROOT / 'human_review' / 'site_marks.json'  # a bundle built before 2026-10-11
    if marks.exists():
        shutil.copyfile(marks, cat / 'data' / 'human-review-marks.json')
    # loaded from the release copy: the viewer builder writes the new manifest next to its own file
    builder = _load('viewer_builder', fresh / 'scripts' / 'build-catlog-viewer-index.py')
    coverage = _load('coverage_builder', fresh / 'scripts' / 'build-catlog-followup-summary.py')
    manifest = builder.load_manifest(bundle / 'data' / 'manifest.js')
    assert manifest['web_only'] and not manifest['record_chunks'] and 'full_data_download' not in manifest
    paths = manifest['detail_shards'] + [manifest[k]['path'] for k in ('table_download', 'enriched_download', COMPARISON_KEY,
                                                                       NOT_DETECTED_KEY, VALUES_KEY) if k in manifest]
    for rel in paths:  # content-addressed data files: same name = same bytes
        src, dst = bundle / rel, cat / rel
        if dst.exists():
            assert sha(src) == sha(dst), f'{rel}: same name, different bytes'
        else:
            shutil.copyfile(src, dst)
    tmp = cat / 'data' / '.viewer-index.tmp'
    meta = builder.build(cat / manifest['table_download']['path'], tmp)
    assert meta['row_count'] == manifest['total_rows'] and meta['source_sha256'] == manifest['table_download']['sha256']
    vp = f"data/catlog-viewer-index.{meta['viewer_sha256'][:12]}.jsonl.gz"
    tmp.replace(cat / vp); meta['viewer_path'] = vp
    manifest['viewer_index'] = builder.viewer_descriptor(meta)
    download = cat / manifest['enriched_download']['path']
    manifest['summary']['followup_coverage'] = coverage.build(manifest, download)
    manifest['summary']['review_details'] = coverage.build_review_details(manifest, download)
    if hasattr(coverage, 'build_overview'):  # the Stats page's numbers (site changes of 2026-10-12 onward)
        manifest['summary']['overview'] = coverage.build_overview(manifest, download, marks if marks.exists() else None)
    assets = ('catlog-static.css', 'catlog-static.js', 'catlog-guide-workflow.svg', 'catlog-mark.svg')
    version = hashlib.sha256((manifest['source_sha256'] + ''.join(sha(cat / 'assets' / a) for a in assets)).encode()).hexdigest()[:16]
    manifest['asset_version'] = version
    mp = builder.write_immutable_manifest(manifest, bundle / 'data' / 'manifest.js')
    marked = json.loads(marks.read_text()) if marks.exists() else {}
    checked = {k for k, v in marked.get('marks', {}).items() if v['checked']}
    accepted_checked = _accepted(cat / manifest['table_download']['path'], checked) if marked else set()
    human_checked = len(accepted_checked) if marked else None
    quality = marked.get('quality') or {}
    if not quality:  # marks written before 'review site' added the quality object (2026-10-12)
        import catlog
        quality = dict(zip(('audit_values', 'audit_wrong'), catlog.audit_summary()))
    (cat / 'README_FIRST.txt').write_text(_readme(manifest, receipt, _quality_lines(quality, human_checked), quality))
    page = (cat / 'index.html').read_text()
    d = datetime.fromisoformat(manifest['generated_at']); date = f'{d:%B} {d.day}, {d.year}'; count = f"{manifest['total_rows']:,}"
    for pat, new, n in ((r'<meta name="description" content="[^"]*" />', f'<meta name="description" content="CatLog snapshot dated {date}: browse {count} enzyme kinetics records with review results, source links, protein sequences and substrate structures." />', 1),
                        (r'<meta property="og:description" content="[^"]*" />', f'<meta property="og:description" content="CatLog snapshot dated {date} with {count} enzyme kinetics records, review results, source links, protein sequences and substrate structures." />', 1),
                        (r'data/catlog-enriched\.[0-9a-f]{12}\.jsonl\.gz', manifest['enriched_download']['path'], 2),
                        (r'data/catlog-table\.[0-9a-f]{12}\.jsonl\.gz', manifest['table_download']['path'], 1),
                        (r'data/manifest\.[0-9a-f]{12}\.js', str(mp.relative_to(cat)), 1)):
        page, k = re.subn(pat, lambda _m: new, page)
        assert k == n, (pat, k)
    # the viewer index's preload hint in <head> (data-src), when the page has one; a page without it is left as it is
    page = re.sub(r'data/catlog-viewer-index\.[0-9a-f]{12}\.jsonl\.gz', lambda _m: vp, page)
    page, k = re.subn(r'((?:src|href)="assets/(?:catlog-static\.css|catlog-static\.js))\?v=[^"<>]*', lambda m: m[1] + '?v=' + version, page)
    assert k == 2
    (cat / 'index.html').write_text(page)
    nobytecode = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    run(['python3', 'scripts/sync-catlog-latest.py'], cwd=fresh, env=nobytecode)
    doc = fresh / 'docs' / f"catlog-release-{d:%Y%m%d}.md"  # the snapshot's date (nothing serves it: a plain-words receipt)
    doc.parent.mkdir(exist_ok=True)
    doc.write_text(_release_note(date, manifest, receipt, picked, quality, human_checked, '', bullets))
    if not bullets and picked and sum(1 for x in picked if not SKIP_SUBJECT.search(x)) > SITE_LIST_MAX:
        print(f'  note: the release note gives only the number of site changes; `site stage --note FILE` lists the '
              f'visitor bullets (3 to 5 lines) instead')
    tree, files, size = release_tree(fresh)
    print(f'  staged site: {files:,} files, {size:,} bytes (size gate {SIZE_LIMIT:,})')
    if size > SIZE_LIMIT - 5_000_000:
        sys.exit('over the 1 GB size gate with only this data generation; tell the user')
    checks = [['python3', 'tests/test_sync_catlog_latest.py'],  # the same commands as the site's CI (catlog-alias-sync.yml);
              ['python3', 'scripts/sync-catlog-latest.py', '--check'],  # Chrome and Safari run in CI on the PR
              ['node', 'tests/catlog-static-sort-cache.test.mjs'],
              ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_catlog_followup_summary.py'],
              ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_catlog_source_efficiency_layout.py'],
              ['python3', 'scripts/build-catlog-followup-summary.py'],
              ['python3', 'scripts/build-catlog-followup-summary.py', '--details-report'],
              ['python3', 'scripts/check-catlog-publish.py']]  # includes the 1 GB staged-tree limit
    failed = []
    for c in checks:
        r = run(c, cwd=fresh, check=False, capture=True, env=nobytecode)
        print('    ok' if r.returncode == 0 else f'    FAILED: {(r.stdout or "")[-800:]}{(r.stderr or "")[-800:]}')
        if r.returncode:
            failed.append(' '.join(map(str, c)))
    if failed:
        print(f'\nnot staged: these checks failed (the folder stays as {fresh} for a look):', *failed, sep='\n  ')
        sys.exit(1)
    if release_tree(fresh)[0] != tree:
        sys.exit(f'a check changed the release folder ({fresh}): nothing staged')
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    fresh.rename(RELEASE_DIR)
    notes = BUILD / 'release-notes'  # the plain-words receipt of every staged release, kept (release/ is replaced)
    notes.mkdir(exist_ok=True)
    shutil.copyfile(RELEASE_DIR / doc.relative_to(fresh), notes / doc.name)
    receipt['staged'] = {'folder': str(RELEASE_DIR.relative_to(ROOT)), 'tree': tree, 'files': files, 'bytes': size,
                         'manifest': mp.name, 'site_base_commit': site_base_commit,
                         'v2_head': run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture=True).stdout.strip()}
    (BUILD / 'build.json').write_text(json.dumps(receipt, indent=1))
    print(f"\nstaged in {RELEASE_DIR.relative_to(ROOT)} (tree {tree[:12]}): {receipt['records']:,} records, "
          f"{receipt['accepted']:,} accepted. Check: `python3 cloudflare/publish.py --dry-run`. Publish only when the user "
          f"says so: `python3 cloudflare/publish.py`.")


def publish():
    """Retired with the GitHub copy (the user, 2026-10-31: "github will have nothing except the pointer"): it pushed the
    staged commit to the lab repo's main, which now holds only a pointer page to catlog.structf.studio."""
    sys.exit('site publish is retired: the lab\'s GitHub site only points to https://catlog.structf.studio (the user, '
             '2026-10-31). Publish with `python3 cloudflare/publish.py` (`--dry-run` first), never by pushing to its main.')


def main(args):
    cmd = args[0] if args else 'status'
    opt = lambda k: args[args.index(k) + 1] if k in args and args.index(k) + 1 < len(args) else None
    if cmd in ('update', 'stage') and '--note' in args and not (opt('--note') and Path(opt('--note')).is_file()):
        sys.exit('--note needs a file of visitor bullets, one per line')
    if cmd == 'status':
        status()
    elif cmd == 'update':  # what "update the website" means: build, then stage; nothing public
        build(); stage(note=opt('--note'))
    elif cmd == 'build':
        build()
    elif cmd == 'stage':
        stage(note=opt('--note'))
    elif cmd == 'publish':
        publish()
    elif cmd == '_merge':
        _merge()
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
