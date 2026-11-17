"""Shared readers and parsers for the independent re-derivation of L13, L32, L46 and claim 5.6 (2026-11-01).

Written from the claims' stated definitions (paper/planning/top_journal_20261021/nmeth/reliability.md F1, F2).
It imports nothing from the repository: not tools/units.py, not the one-pass rel_*.py scripts. It reads raw files only,
from the working tree or, for the 23 October snapshot, from git (`git show <commit>:<path>`, streamed, no copy on disk).
"""
import collections
import csv
import json
import math
import os
import random
import re
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = '<the CatLog folder>'
HERE = os.path.dirname(os.path.abspath(__file__))
# The data checkpoint of 2026-10-23 11:56. log.tsv has no add, drop or unitfix between the 11:48 enrich and this commit,
# so its catalog.jsonl is the catalog the one-pass scripts' export (11:53) was built from (6,622 papers in both).
SNAP = 'e577b41'
csv.field_size_limit(10 ** 9)
METRICS = ('kcat', 'Km', 'kcat/Km')


# ---------------------------------------------------------------- reading raw files
def lines(path, commit=None):
    if commit:
        p = subprocess.Popen(['git', '-C', ROOT, 'show', f'{commit}:{path}'], stdout=subprocess.PIPE)
        for b in p.stdout:
            yield b.decode('utf-8')
        p.wait()
    else:
        with open(os.path.join(ROOT, path), encoding='utf-8') as f:
            yield from f


def catalog(commit=None):
    for line in lines('catalog.jsonl', commit):
        line = line.strip()
        if line:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def tsv(path, commit=None):
    return list(csv.DictReader(lines(path, commit), delimiter='\t', quoting=csv.QUOTE_NONE))


def save(key, obj):
    """Write one section of results.json (read-modify-write; the scripts run one after another)."""
    p = os.path.join(HERE, 'results.json')
    allr = json.load(open(p)) if os.path.exists(p) else {}
    allr[key] = obj
    with open(p, 'w') as f:
        json.dump(allr, f, indent=1, ensure_ascii=False)
    return p


# ---------------------------------------------------------------- text normalisation
SUP = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺', '0123456789-+')


def norm(s):
    s = '' if s is None else str(s)
    s = re.sub('[⁻⁺]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+', lambda m: '^' + m.group(0).translate(SUP), s)
    for a in '−–—‐‑⫺﹣－':
        s = s.replace(a, '-')
    s = re.sub(r'(?<=\d)\s*[·⋅]\s*(?=10\s*\^)', ' x ', s)      # '2.9 · 10^1' is a multiplication
    s = re.sub(r'(?<=\d)[·⋅](?=\d)', '.', s)                    # '4⋅3', '0·010': a centred decimal point
    for a, b in (('µ', 'u'), ('μ', 'u'), ('␮', 'u'), ('×', 'x'), ('⫻', 'x'), ('✕', 'x'), ('{', ''), ('}', ''),
                 (' ', ' '), (' ', ' '), (' ', ' '), (' ', ' '), ('⫾', '±'), ('+/-', '±'),
                 ('·', ' '), ('⋅', ' '), ('•', ' '), ('∼', '~')):
        s = s.replace(a, b)
    s = re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', '', s)
    s = re.sub(r'\^\s*\(\s*(-?\s*\d+)\s*\)', lambda m: '^' + m.group(1).replace(' ', ''), s)  # 10^(-3) -> 10^-3
    s = re.sub(r'\^\s*-\s+(?=\d)', '^-', s)                                                    # '^- 3' -> '^-3'
    return s


# ---------------------------------------------------------------- power-of-ten multipliers in a printed unit
# Forms, tried in this order (an earlier form's span is not matched again). Exponent None = the text lost it.
MULT_FORMS = [
    ('lost', re.compile(r'(?:(?:x|\*)\s*)?10\s*\^\s*\?')),                                           # '10^?'
    ('caret', re.compile(r'(?:\(\s*)?(?:(?:x|\*)\s*\(?\s*)?(?<![\d.])10\s*\^\s*([-+]?\d{1,2})(?!\d)\s*\)?')),  # 10^3, (x10^-3)
    ('flat_signed', re.compile(r'(?:\(\s*)?(?:(?:x|\*)\s*\(?\s*|(?<=[\s(,;])|^)10\s*-\s*(\d{1,2})(?![\d.])\s*\)?')),  # '10-3 s-1'
    ('x_flat_digit', re.compile(r'(?:x|\*)\s*10([2-9])(?![\d.])')),                                   # 'x103' (10^3 flattened)
    ('x_power', re.compile(r'(?:\(\s*)?(?:x|\*)\s*\(?\s*(10{1,9})(?![\d.])\s*\)?')),                  # 'x 100', '(x1000)', 'x 10'
    ('power_x', re.compile(r'(?<![\d.])(10{2,9})\s*(?:x|\*)(?=\s*[A-Za-z(])')),                         # '1000 x kcat'
]


def unit_text(raw_unit):
    u = norm(raw_unit)
    return re.sub(r'(?<![A-Za-z])X\s*(?=\(?\s*10)', 'x', u)  # 'X10^-3': a capital X is a multiplication sign


def unit_multipliers(raw_unit):
    """[(form, exponent or None, span)] for every power-of-ten multiplier printed in a unit string.
    A bare 'x 10' (no exponent after it) is a multiplier whose exponent the text lost: exponent None."""
    u = unit_text(raw_unit)
    found, taken = [], []
    for form, rx in MULT_FORMS:
        for m in rx.finditer(u):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue
            if form == 'caret':
                e = int(m.group(1))
                if e == 0:
                    continue
            elif form == 'flat_signed':
                e = -int(m.group(1))
            elif form == 'x_power':
                e = len(m.group(1)) - 1
                if e == 1:
                    e = None  # 'x 10' with nothing after it: an exponent the text lost
            elif form == 'power_x':
                e = len(m.group(1)) - 1
            elif form == 'x_flat_digit':
                e = int(m.group(1))
            else:
                e = None
            found.append((form, e, (m.start(), m.end())))
            taken.append((m.start(), m.end()))
    return found


def strip_multipliers(u, found):
    out, last = [], 0
    for _, _, (a, b) in sorted(found, key=lambda x: x[2]):
        out.append(u[last:a])
        last = b
    out.append(u[last:])
    s = ' '.join(out)
    s = re.sub(r'\(\s*\)', ' ', s)
    return re.sub(r'(?:^|(?<=[\s,(]))(?:x|\*)(?=\s|$|[,()])', ' ', s)  # a lone multiplication sign left behind


# ---------------------------------------------------------------- printed cells
ERR_NUM = r'\d{1,3}(?: \d{3})+(?:\.\d+)?|\d[\d.,]*'


def parse_value(raw):
    """(central value, mantissa string, exponent printed in the cell or None), or None.
    '1.2 ± 0.3', '(1.2 ± 0.3) x 10^5', '1.21 (±0.26) x 10^4', '1.2 x 10^-3', '1.2E-3', '1,200', '0,35', '40 600',
    '0.000 79', '1.2 (0.3)'. In '0.0015 ± 3 x 10^-5' the exponent belongs to the error only."""
    s = norm(raw).strip()
    s = re.sub(r'^\s*(?:~|≈|ca\.?|approx\.?|about)\s*', '', s, flags=re.I)
    s = re.sub(r'(?<=[\d)])\s*X\s*(?=10)', ' x ', s)                          # '8.7X10^-5'
    s = re.sub(r'(?<=\d)\s*([eE])\s*([-+]?)\s*(?=\d)', r'\1\2', s)            # '2.83E + 06' is 2.83E+06
    if re.search(r'(?:x|\*)\s*10(?!\s*\^?\s*[-+]?\s*\d)', s):
        return None  # 'x 10' whose exponent the text lost
    s = re.sub(r'(?<=\d)\.(\d{3})((?: \d{1,3}(?![\d.]))+)', lambda m: '.' + m.group(1) + m.group(2).replace(' ', ''), s)
    m = re.match(r'\(\s*(\d[\d.,]*)\s*±[^)]*\)\s*(?:x|\*)?\s*10\s*\^?\s*([-+]?\d+)', s)
    if m:
        v = to_float(m.group(1))
        return (None if v is None else v * 10 ** int(m.group(2))), m.group(1), int(m.group(2))
    m = re.match(r'(\d[\d.,]*)\s*±\s*(\d[\d.,]*)\s*(?:x|\*)\s*10\s*\^?\s*([-+]?\d+)\s*$', s)
    if m:
        a, b = to_float(m.group(1)), to_float(m.group(2))
        if a is not None and b is not None and b > a and b * 10 ** int(m.group(3)) < a:
            return a, m.group(1), None  # the exponent is the error's own
    s2 = re.sub(r'\s*\(\s*±?\s*(?:' + ERR_NUM + r')(?:\s*[eE]\s*[-+]?\d+)?\s*\)', '', s)       # '(±0.26)', '(0.3)'
    s2 = re.sub(r'\s*±\s*(?:' + ERR_NUM + r')(?:\s*[eE]\s*[-+]?\d+)?', '', s2)                  # '± 0.3', '± 40 000'
    m = re.search(r'(-?\d[\d.,]*|\.\d+)\s*\)?\s*(?:x|\*)\s*10\s*\^?\s*([-+]?\d+)', s2)
    if m:
        v = to_float(m.group(1))
        return (None if v is None else v * 10 ** int(m.group(2))), m.group(1), int(m.group(2))
    m = re.search(r'(-?\d[\d.,]*|\.\d+)\s*[eE]\s*([-+]?\d+)', s2)
    if m:
        v = to_float(m.group(1))
        return (None if v is None else v * 10 ** int(m.group(2))), m.group(1), int(m.group(2))
    m = re.search(r'(-?\d+(?: \d{3})+(?:\.\d+)?)(?![\d.])', s2)                                   # '40 600', '1360 000'
    if m and s2.strip().startswith(m.group(1)):
        mant = m.group(1).replace(' ', '')
        return to_float(mant), mant, None
    m = re.search(r'(-?\d[\d.,]*|\.\d+)', s2)
    if not m:
        return None
    return to_float(m.group(1)), m.group(1), None


def to_float(tok):
    tok = tok.rstrip('.,')
    if re.fullmatch(r'-?\d{1,3}(,\d{3})+(\.\d+)?', tok) and not tok.lstrip('-').startswith('0,'):
        tok = tok.replace(',', '')                                           # thousands comma
    elif re.fullmatch(r'-?\d+,\d+', tok):
        tok = tok.replace(',', '.')                                          # decimal comma
    try:
        return float(tok)
    except ValueError:
        return None


def rel_rounding(mant):
    """Half the printed last digit, relative to the printed number."""
    t = (mant or '').replace(',', '').lstrip('-')
    try:
        v = float(t)
    except ValueError:
        return 0.0
    if not v:
        return 0.0
    dec = len(t.split('.')[1]) if '.' in t else 0
    return 0.5 * 10 ** -dec / v


# ---------------------------------------------------------------- printed units -> catalog units
TIME = {'s': 1.0, 'sec': 1.0, 'second': 1.0, 'seconds': 1.0, 'min': 60.0, 'minute': 60.0, 'minutes': 60.0,
        'h': 3600.0, 'hr': 3600.0, 'hour': 3600.0, 'hours': 3600.0, 'ms': 1e-3}
CONC = {'M': 1.0, 'mM': 1e-3, 'uM': 1e-6, 'nM': 1e-9, 'pM': 1e-12}
CONC_CI = {'m': 1.0, 'mm': 1e-3, 'um': 1e-6, 'nm': 1e-9, 'pm': 1e-12}
MASS = {'ng': 1e-6, 'ug': 1e-3, 'mg': 1.0, 'g': 1e3}
VOL = {'ul': 1e-3, 'ml': 1.0, 'dl': 100.0, 'l': 1e3}
T_RX = r'(seconds?|sec|minutes?|min|hours?|hr|ms|h|s)'
C_RX = r'(pM|nM|uM|mM|M)'


def _clean_unit(u):
    u = re.sub(r'-\s*\^\s*1(?!\d)', '-1', u)                     # 'M-^1', 's^-^1'
    u = re.sub(r'\^\s*-\s*\^?\s*1(?!\d)', '^-1', u)
    u = re.sub(r'(?<![A-Za-z])([munp])\s+([mM])\b', r'\1\2', u)  # 'm M^-1', 'u M', 'u m' (spaced prefix)
    u = re.sub(r'(?i)\b(micro|milli|nano|pico)molar\b', lambda m: {'micro': 'uM', 'milli': 'mM', 'nano': 'nM',
                                                                 'pico': 'pM'}[m.group(1).lower()], u)
    u = re.sub(r'(?i)\bmolar\b', 'M', u)
    vol = r'(?:l|liter|litre|dm\s*\^?\s*3)'
    u = re.sub(r'(?i)\b([munp]?)mol(?:es)?\s*(?:/|per)\s*' + vol + r'\b', lambda m: (m.group(1) or '') + 'M', u)
    u = re.sub(r'(?i)\b([munp]?)mol(?:es)?\s*' + vol + r'\s*\^?\s*-\s*1\b', lambda m: (m.group(1) or '') + 'M', u)
    u = re.sub(r'(?i)\b([munp]?)mol\s*dm\s*\^?\s*-\s*3\b', lambda m: (m.group(1) or '') + 'M', u)
    u = re.sub(r'(?i)\b' + vol + r'\s*[ .]?\s*([munp]?)mol\s*\^?\s*-\s*1\b', lambda m: (m.group(1) or '') + 'M^-1', u)
    u = re.sub(r'(?i)\b([munp]?)mol\s*\^?\s*-\s*1\s*[ .]?\s*' + vol + r'\b', lambda m: (m.group(1) or '') + 'M^-1', u)
    u = re.sub(r'(?i)\s*(?:per|/)\s*(?:active\s+)?(?:site|monomer|subunit|dimer|tetramer|enzyme)\b', '', u)
    u = re.sub(r'(?i)(?:k\s*_?\s*cat\s*/\s*k\s*_?\s*m|catalytic efficiency|k\s*_?\s*cat|k\s*_?\s*m|v\s*/\s*k)\'?\*?', ' ', u)
    return u.replace('[', '(').replace(']', ')')


def _inv_time(u):
    for p in (T_RX + r'\s*\^?\s*-\s*1(?!\d)', r'/\s*' + T_RX + r'\b', r'per\s+' + T_RX + r'\b',
              r'/\s*\([^)]*?\b' + T_RX + r'\s*\)'):
        m = re.search(p, u, flags=re.I)
        if m:
            t = m.group(1).lower()
            if t in TIME:
                return TIME[t]
    return None


def _conc_tok(t):
    if t in CONC:
        return CONC[t]
    return CONC_CI.get(t.lower())


def parse_unit(metric, raw_unit):
    """(factor, family, [multiplier exponents]) so that catalog value = printed number x factor, or None.
    Catalog units: kcat s^-1; Km mM (family 'molar') or mg/mL ('mass'); kcat/Km mM^-1 s^-1 or mL mg^-1 s^-1.
    A printed multiplier multiplies the printed number (the plain reading); the closure classes treat its other
    reading separately."""
    found = unit_multipliers(raw_unit)
    if any(e is None for _, e, _ in found):
        return None
    mult = 10.0 ** sum(e for _, e, _ in found)
    exps = [e for _, e, _ in found]
    u = _clean_unit(strip_multipliers(unit_text(raw_unit), found))
    u = re.sub(r'\s+', ' ', u).strip(' ,;')
    if metric == 'kcat':
        v = re.sub(r'[()]', ' ', u).strip(' ,;')
        v = re.sub(r'\s+', ' ', v)
        if re.fullmatch(T_RX + r'\s*\^?\s*-\s*1', v, flags=re.I) or \
                re.fullmatch(r'1?\s*/\s*' + T_RX, v, flags=re.I) or re.fullmatch(r'per\s+' + T_RX, v, flags=re.I):
            f = _inv_time(v)
            if f:
                return mult / f, 'molar', exps
        return None
    if metric == 'Km':
        v = re.sub(r'[()\s]', '', u)
        f = _conc_tok(v)
        if f is not None:
            return mult * f / 1e-3, 'molar', exps
        m = re.fullmatch(r'(?i)(ng|ug|mg|g)(?:/|\.)?(ul|ml|dl|l)(\^?-1)?', v)
        if m and ('/' in v or m.group(3)):
            return mult * MASS[m.group(1).lower()] / VOL[m.group(2).lower()], 'mass', exps
        return None
    if metric == 'kcat/Km':
        v = u.replace('*', ' ')
        v = re.sub(r'\bS(?=\s*\^?\s*-\s*1|\b)', 's', v)
        if re.search(r'M\s*\^?\s*-\s*[2-9]', v):
            return None
        g = re.search(r'\(\s*' + C_RX + r'\s*[ .x]?\s*' + T_RX + r'\s*\)\s*\^?\s*-\s*1(?!\d)', v) or \
            re.search(r'1?\s*/\s*\(\s*' + C_RX + r'\s*[ .x]?\s*' + T_RX + r'\s*\)', v)
        if g:
            return mult / (CONC[g.group(1)] * TIME[g.group(2).lower()]) * 1e-3, 'molar', exps
        w = re.sub(r'[()]', ' ', v)
        c = re.search(C_RX + r'\s*\^?\s*-\s*1(?!\d)', w) or re.search(r'/\s*' + C_RX + r'(?![a-z])', w) or \
            re.search(r'per\s+' + C_RX + r'(?![a-z])', w)
        fc = CONC[c.group(1)] if c else None
        if fc is None:
            c2 = re.search(r'(?i)(?<![a-z])(pm|nm|um|mm|m)\s*\^?\s*-\s*1(?!\d)', w)  # small caps: 'mm^-1', 'm^-1'
            fc = CONC_CI[c2.group(1).lower()] if c2 else None
        ft = _inv_time(v) or _inv_time(w)
        if fc and ft:
            return mult / (fc * ft) * 1e-3, 'molar', exps
        mm = re.search(r'(?i)(?<![a-z])(ul|ml|dl|l)(?![a-z])', w)
        ms = re.search(r'(?i)(?<![a-z])(ng|ug|mg|g)\s*\^?\s*-\s*1', w) or re.search(r'(?i)/\s*\(?\s*(ng|ug|mg|g)(?![a-z])', v) \
            or re.search(r'(?i)\(\s*(ng|ug|mg|g)\s*[ .x]?\s*' + T_RX + r'\s*\)\s*\^?\s*-\s*1', v) \
            or re.search(r'(?i)/\s*\([^)]*?(?<![a-z])(ng|ug|mg|g)(?![a-z])[^)]*\)', v)
        if ms and not ft:
            t2 = re.search(r'(?i)\(\s*(?:ng|ug|mg|g)\s*[ .x]?\s*' + T_RX + r'\s*\)\s*\^?\s*-\s*1', v) or \
                re.search(r'(?i)/\s*\([^)]*?(?<![a-z])' + T_RX + r'(?![a-z])[^)]*\)', v)
            ft = TIME.get(t2.group(1).lower()) if t2 else None
        if mm and ms and ft:
            return mult * VOL[mm.group(1).lower()] / (MASS[ms.group(1).lower()] * ft), 'mass', exps
        return None
    return None


def convert(metric, raw_value, raw_unit):
    """(value in catalog units, family, mantissa, cell exponent, unit multiplier exponents) or None."""
    pv = parse_value(raw_value)
    if not pv or pv[0] is None:
        return None
    pu = parse_unit(metric, raw_unit)
    if not pu:
        return None
    return pv[0] * pu[0], pu[1], pv[1], pv[2], pu[2]


# ---------------------------------------------------------------- intervals
def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(100 * (c - h) / d, 2), round(100 * (c + h) / d, 2)]


def boot_ci(flags, n=2000, seed=20261101):
    """Percentile bootstrap over papers of the share of papers flagged (flags: one 0/1 per paper)."""
    rnd = random.Random(seed)
    N = len(flags)
    if not N:
        return None
    vals = sorted(sum(flags[rnd.randrange(N)] for _ in range(N)) / N for _ in range(n))
    return [round(100 * vals[int(0.025 * n)], 2), round(100 * vals[int(0.975 * n) - 1], 2)]


# ---------------------------------------------------------------- paper checks of database differences
DBS = ('BRENDA', 'SABIO-RK', 'OED', 'SKiD', 'UniProt', 'STRENDA')
HEADER_CAUSES = {'header_scale_inverted', 'header_scale_ignored'}
MISPRINT_CAUSE = 'paper_unit_misprint'


def origin(cause):
    """Where a database error entered: the paper's own misprint copied, a header multiplier misread, or curation."""
    if cause == MISPRINT_CAUSE:
        return 'copied_paper_misprint'
    if cause in HEADER_CAUSES:
        return 'header_multiplier_misread'
    return 'other_curation'


def latest_verdicts(commit=None):
    """{(row_id, database): line} for sources/database_corrections.tsv, the latest line per value and database
    (by date, then file order), each database of a 'BRENDA, OED' line taken on its own."""
    lines = tsv('sources/database_corrections.tsv', commit)
    out = {}
    for i, r in sorted(enumerate(lines), key=lambda x: (x[1]['date'], x[0])):
        for db in [x.strip() for x in (r['database'] or '').split(',') if x.strip()]:
            out[(r['row_id'], db)] = r
    return out, len(lines)


def number(s):
    m = re.match(r'\s*([-+]?\d[\d.]*(?:[eE][-+]?\d+)?)', s or '')
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None


def db_wrong(commit=None):
    """Paper-checked wrong database values: {database: {row_id: (pmid, cause)}} for latest verdicts 'corrected' on rows
    still in the catalog, leaving out verdicts the catalog no longer supports (CatLog's value now within 1.5x of the
    database number the check named). Also returns the catalog's rows by id and counts of what was left out."""
    cat = {d['row_id']: d for d in catalog(commit)}
    lat, nlines = latest_verdicts(commit)
    wrong = {db: {} for db in DBS}
    left = collections.Counter()
    verdicts = collections.Counter()
    for (rid, db), r in lat.items():
        verdicts[r['verdict']] += 1
        if r['verdict'] != 'corrected':
            continue
        d = cat.get(rid)
        if d is None:
            left['row_no_longer_in_catalog'] += 1
            continue
        dv, cv = number(r['database_value']), d.get('value')
        if dv and cv and dv > 0 and cv > 0 and abs(math.log10(dv / cv)) < math.log10(1.5):
            left['catalog_value_now_agrees_with_the_database_number'] += 1
            continue
        if db not in wrong:
            left['database_not_in_list:' + db] += 1
            continue
        wrong[db][rid] = (d['pmid'], r['cause'])
    return wrong, cat, {'lines_in_file': nlines, 'latest_value_database_pairs': len(lat),
                        'latest_verdicts': dict(verdicts), 'corrected_left_out': dict(left)}


def db_cited_papers(cat):
    """{database: (papers CatLog holds that the database lists any kcat/Km/kcat-Km value for,
                   papers where it lists a value of a metric CatLog holds for that paper)} from sources/db_values.tsv."""
    mets = collections.defaultdict(set)
    for d in cat.values():
        mets[d['pmid']].add(d['metric'])
    anyp = {db: set() for db in DBS}
    samem = {db: set() for db in DBS}
    for r in tsv('sources/db_values.tsv'):
        pm, db = r['pmid'], r['source']
        if pm in mets and db in anyp:
            anyp[db].add(pm)
            if r['metric'] in mets[pm]:
                samem[db].add(pm)
    return anyp, samem

