"""Parse a printed kinetic value and convert it to the catalog unit.

kcat -> s^-1, Km -> mM, kcat/Km -> mM^-1 s^-1 (the RealKcat catalog units). The LLM copies the printed cell and unit;
this code does the arithmetic, so a normalized value is never typed by a model.
"""
import re

TIME = {'s': 1.0, 'sec': 1.0, 'min': 60.0, 'h': 3600.0, 'hr': 3600.0, 'ms': 1e-3}
CONC = {'M': 1.0, 'mM': 1e-3, 'uM': 1e-6, 'nM': 1e-9, 'pM': 1e-12}


SUPERSCRIPT = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻', '0123456789-')


def clean(s):
    s = '' if s is None else str(s)  # a number typed as a JSON number is still a printed cell
    # Unicode superscript exponents: 10⁵ -> 10^5, s⁻¹ -> s^-1
    s = re.sub('⁻?[⁰¹²³⁴⁵⁶⁷⁸⁹]+', lambda m: '^' + m.group(0).translate(SUPERSCRIPT), s)
    s = re.sub('(?<=\\d)\\s*[·⋅]\\s*(?=10)', ' x ', s)  # 2.5·10^4 is a multiplication
    for a, b in (('⫾', '±'), ('⫺', '-'), ('−', '-'), ('–', '-'), ('—', '-'), ('µ', 'u'), ('μ', 'u'),
                 ('×', 'x'), ('⫻', 'x'), ('⋅', '.'), ('·', '.'), (' ', ' '), (' ', ' '),
                 ('{', ''), ('}', ''),
                 # slanted and double-bar ≥/≤ (19243936 prints '⩾400', 12637017 '⩽20'): the same bound signs
                 ('⩾', '≥'), ('⩽', '≤'), ('≧', '≥'), ('≦', '≤')):
        s = s.replace(a, b)
    s = s.replace('␮', 'u').replace('Æ', '.')  # PDF text-layer glyphs: U+242E is a micro sign, 'Æ' a centred dot
    s = re.sub(r'(?<=[\d)])\s*X\s*(?=10)', ' x ', s)  # '1.2 X 10^5': a capital X is a multiplication sign too
    s = re.sub(r'(?<=[A-Za-z)])\s?[\x01-\x08]\s?(?=1(?!\d))', '-', s)  # a control character drawn as a superscript minus: 's\x041'
    # a PDF font that draws '±' as two glyphs: '4.1 ^  \x8a 0.4' and '440 \x8a^ 14' are both 4.1 ± 0.4 (PMID 10712619)
    s = re.sub(r'\^\s*[\x80-\x9f]|[\x80-\x9f]\s*\^', '\u00b1', s)
    s = re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', '', s)  # a control character left inside a number is noise: '2\x8a.6' is 2.6
    s = re.sub(r'((?:x|\*)\s*10)\s*-\s+(?=\d)', r'\1^-', s)  # 'x 10 − 2' (a spaced superscript minus) is x 10^-2
    return re.sub(r'\^\s*-\s+(?=\d)', '^-', s)  # '^{− 3}' (Elsevier XML rendering) is '^-3'


def unit_glyphs(u):
    """Unit spellings that only a broken PDF text layer produces: 'lM' (µM), 's21' / 'M)1' (s^-1, M^-1)."""
    # common spellings of the same units: micromolar, mmol/L, mol dm-3, (M s)^-1, 1/(uM*s), 's-1 per site'
    u = re.sub(r'(?i)\b(micro|milli|nano|pico)?molar\b', lambda m: {'micro': 'uM', 'milli': 'mM', 'nano': 'nM', 'pico': 'pM'}.get(
        (m.group(1) or '').lower(), 'M'), u)
    u = re.sub(r'(?i)\b([munp]?)mol[\s.]*(?:/\s*(?:l|dm\^?3)|(?:l|dm\^?3)\s*\^?-1|dm\s*\^?-3)(?![A-Za-z])', lambda m: (m.group(1) or '') + 'M', u)
    u = re.sub(r'\(\s*([munp]?M)\s*[ .*]?\s*(s|min|sec)\s*\)\s*\^?\s*-1', r'\1^-1 \2^-1', u)
    u = re.sub(r'1\s*/\s*\(\s*([munp]?M)\s*[ .*]\s*(s|min|sec)\s*\)', r'\1^-1 \2^-1', u)
    u = re.sub(r'(?i)\s*(?:per|/)\s*(?:active\s+)?(?:site|monomer|subunit|dimer)\b', '', u)  # the basis belongs in metric_note
    u = re.sub(r'(?<![A-Za-z])l(?=M\b|M\W|M$|mol\b)', 'u', u)
    return re.sub(r'\b(s|sec|min|h|hr|M|mM|uM|nM|pM|cm)(?:21|\)\s?1)(?!\d)', r'\1^-1', u)


BARE_X10 = re.compile(r'(?:x|\*)\s*10(?!\s*\^?\s*\(?\s*[-+]?\s*\d)')  # 'x 10' whose exponent the text layer lost


def parse_number(raw):
    """Central value of a printed cell: 'a x 10^b', 'a ± u x 10^b', '(a ± u)10^b', 'a (u) x 10^b', 'aE+b',
    '40 600', '.45', decimal comma '0,35', thousands comma '1,200'."""
    s = clean(raw)
    if BARE_X10.search(s):
        return None  # '3.6 x 10': the superscript moved to another line; never read it as x1
    # a spaced exponent is aE+b: '2.76E + 03', '6.53E− 05', '2.17 E − 9', '243 E3' (41657244, 18291415, 28923662,
    # 21424826); here only, not in clean(): in prose 'TS1 e-1' is a gene and '2 e + 2 H' electrons
    s = re.sub(r'(?<=\d)\s*([eE])(\s*[-+]\s*|)(?=\d)', lambda m: m.group(1) + m.group(2).strip(), s)
    s = re.sub(r'(?<![\d.])0,(?=\d)', '0.', s)  # '0,035' is a decimal comma, never thousands
    s = re.sub(r'(?<=\d),(?=\d{3}(?!\d))', '', s)  # thousands comma
    s = re.sub(r'(?<=\d),(?=\d)', '.', s)           # decimal comma
    # SI grouping inside a decimal fraction: '0.000 03' is 0.00003, '1.234 567' one number (PMID 9305962, Table 2)
    s = re.sub(r'\d*\.\d{3}(?: \d{1,3}(?![\d.]))+', lambda m: m.group(0).replace(' ', ''), s)
    s = re.sub(r'(?<=\d) (?=\d{3}(?!\d))', '', s)  # space-grouped thousands: '40 600' is one number
    e = re.match(r'\s*(\d+(?:\.\d+)?)\s*(?:\u00b1|\+/-)\s*(\d+(?:\.\d+)?)\s*(?:x|\*)\s*10\s*\^?\s*\(?\s*(-?\d+)\)?\s*$', s)
    if e and float(e.group(2)) > float(e.group(1)) and float(e.group(2)) * 10 ** int(e.group(3)) < float(e.group(1)):
        return float(e.group(1))  # '5.2 ± 30 x 10^-3': the exponent belongs to the error only
    m = re.search(r'\(\s*(-?\d+(?:\.\d+)?)\s*(?:\u00b1|\+/-)[^)]*\)\s*(?:x\s*)?10\s*\^?\s*\(?\s*(-?\d+)\)?', s)
    if m:
        return float(m.group(1)) * 10 ** int(m.group(2))
    # drop the printed error so it is never read as the value: 'a ± u x 10^n', 'a (±u) x 10^n', 'a x 10^n ± u';
    # an E exponent is the error's own: '0.003 ± 1.0E-04' is 0.003 (25406120), never 0.003E-04
    s = re.sub(r'\s*\(\s*(?:\u00b1|\+/-)?\s*\d+(?:\.\d+)?(?:[eE][-+]?\d+)?\s*\)|\s*(?:\u00b1|\+/-)\s*\d+(?:\.\d+)?(?:[eE][-+]?\d+)?', '', s)
    m = re.search(r'(-?(?:\d+(?:\.\d+)?|\.\d+))\s*(?:x|\*)\s*10\s*\^?\s*\(?\s*(-?\d+)\)?', s)
    if m:
        return float(m.group(1)) * 10 ** int(m.group(2))
    m = re.search(r'(-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?)', s)
    return float(m.group(1)) if m else None


def unit_scale(unit):
    """Pull a printed multiplier out of a unit/header, e.g. '10^3 M^-1 s^-1' or 'x10^-4 s-1'."""
    u = unit_glyphs(clean(unit))
    if BARE_X10.search(u):
        return None, u
    m = re.search(r'(?:x\s*)?10\s*\^?\s*\(?\s*(-?\d+)\)?', u)
    if not m:
        return 1.0, u
    return 10.0 ** int(m.group(1)), (u[:m.start()] + u[m.end():])


def _time(tok):
    tok = tok.strip().lower().rstrip('.')  # 'S-1' and 'sec-1' are seconds
    return TIME.get(tok)


def _conc(tok):
    tok = tok.strip().rstrip('.')
    if tok in CONC:
        return CONC[tok]
    low = tok.lower()
    return {'m': 1.0, 'mm': 1e-3, 'um': 1e-6, 'nm': 1e-9, 'pm': 1e-12}.get(low)


# Km printed as a mass concentration (polysaccharide, protein or other polymer substrates: mg/ml, ug/ml, g/l) and its
# kcat/Km (ml mg^-1 s^-1) cannot become mM without a molar mass. They are kept in their own units (the user, 2026-10-12;
# until then they were rejected as unknown units) and exported in their own columns, never mixed into the mM ones.
MASS_UNIT = {'Km': 'mg/mL', 'kcat/Km': 'mL mg^-1 s^-1'}
MASS = {'ng': 1e-6, 'ug': 1e-3, 'mg': 1.0, 'g': 1e3}   # -> mg
VOLUME = {'ul': 1e-3, 'ml': 1.0, 'dl': 100.0, 'l': 1e3}  # -> mL
UNIT_TOKEN = re.compile(r'sec|min|hr|ms|ng|ug|mg|ul|ml|dl|-1|h|s|g|l|[/().x*]')
KIND = {**{t: 'mass' for t in MASS}, **{t: 'vol' for t in VOLUME}, **{t: 'time' for t in TIME}}


def _mass_tokens(raw_unit, u):
    """(mass, volume, time, {kind: exponent}) when the unit is made of nothing but one mass, one volume and at most one
    time unit with -1 exponents, '/' and separators; else None. Exponents follow the notation: 'mg ml^-1' and 'mg/ml'
    are mass/volume, '(mg/ml)^-1 s^-1' and 'ml mg^-1 s^-1' volume/(mass time); 'mg/ml^-1' is read as (mg/ml)^-1, how
    papers print it (PMID 10767281, 'min^-1 mg/ml^-1'). A number in the unit ('g/100 ml') is never a mass concentration
    here: its 10^n reading would be wrong. A printed multiplier with a caret ('ml/mg/min [10^-2]', PMID 36698977's
    header; normalize applies it) is not part of the unit."""
    bare = re.sub(r'(?:x\s*)?10\s*\^\s*\(?\s*-?\d+\)?', '', unit_glyphs(clean(raw_unit)), count=1)
    if re.search(r'\d', re.sub(r'-\s*1(?!\d)', '', bare)):
        return None
    _, w = unit_scale(raw_unit)  # the unit as normalize() sees it, but with its brackets: '(mg/ml)^-1 s^-1'
    w = re.sub(r'\s+', ' ', w.replace(',', ' ')).strip().replace('per ', '/').replace('^', '').replace(' ', '')
    w = w.replace('[', '(').replace(']', ')')
    v = re.sub(r'S(?=-1|$|[^a-z])', 's', w.replace('L', 'l').replace('Min', 'min').replace('•', '').replace('×', 'x'))
    toks = UNIT_TOKEN.findall(v)
    if ''.join(toks) != v:
        return None  # anything else (mol, M, U, protein, %): not a plain mass concentration
    stack, invs, inv_next, last = [[]], [], False, None  # last: where the next '-1' starts applying
    for t in toks:
        if t == '(':
            invs.append(inv_next); inv_next = False; stack.append([])
        elif t == ')':
            if len(stack) == 1:
                return None
            group, inv = stack.pop(), invs.pop()
            start = len(stack[-1])
            stack[-1].extend((k, -e) if inv else (k, e) for k, e in group)
            last = ('group', start, False, start)
        elif t == '-1':
            if last is None:
                return None
            lo = last[3] if last[2] else last[1]  # 'a/b-1': the paper's (a/b)^-1
            stack[-1][lo:] = [(k, -e) for k, e in stack[-1][lo:]]
            last = None
        elif t == '/':
            inv_next = True
        elif t in KIND:
            start = len(stack[-1])
            stack[-1].append((KIND[t] + ':' + t, -1 if inv_next else 1))
            last = ('tok', start, inv_next, max(start - 1, 0) if inv_next else start)
            inv_next = False
        # '.', 'x' and '*' only separate
    if len(stack) != 1:
        return None
    exp = {}
    for k, e in stack[0]:
        kind, name = k.split(':')
        if kind in exp:
            return None  # two mass, volume or time units
        exp[kind] = (name, e)
    if 'mass' not in exp or 'vol' not in exp:
        return None
    return exp['mass'][0], exp['vol'][0], exp.get('time', (None, 0))[0], {k: e for k, (_, e) in exp.items()}


def normalize(metric, raw_value, raw_unit):
    """Return (value, unit, error). value is in the catalog unit; error is a reason string."""
    x = parse_number(raw_value)
    if x is None:
        return None, None, 'multiplier_without_exponent' if BARE_X10.search(clean(raw_value)) else 'no_number_in_raw_value'
    mult, u = unit_scale(raw_unit)
    if mult is None:
        return None, None, f'multiplier_without_exponent:{raw_unit}'
    # a header multiplier like "kcat (x10^-3 s-1)" means printed value = true/10^-3? Papers differ;
    # we only accept the unambiguous "value x 10^n unit" form, i.e. the multiplier multiplies.
    x *= mult
    u = re.sub(r'\s+', ' ', u.replace(',', ' ')).strip().strip('()[] ')
    u = u.replace('per ', '/').replace('^', '').replace(' ', '')
    m = metric.lower().replace(' ', '')
    if m == 'kcat':
        t = re.fullmatch(r'(?:([a-z]+)-1|1/([a-z]+)|/([a-z]+))', u.replace('.', ''), re.I)
        tok = next((g for g in (t.groups() if t else ()) if g), None)
        f = _time(tok) if tok else None
        if f is None:
            return None, None, f'unknown_kcat_unit:{raw_unit}'
        return x / f, 's^-1', None
    if m == 'km':
        f = _conc(u)
        if f is None:
            mass = _mass_tokens(raw_unit, u)
            if mass and mass[3] == {'mass': 1, 'vol': -1}:  # mg/ml, mg ml^-1, ug/mL, g/l
                return x * MASS[mass[0]] / VOLUME[mass[1]], MASS_UNIT['Km'], None
            return None, None, f'unknown_km_unit:{raw_unit}'
        return x * f / 1e-3, 'mM', None
    if m in ('kcat/km', 'kcatkm', 'kcat_over_km'):
        # accept "M-1s-1", "mM-1min-1", "s-1mM-1", "/M/s", "M-1.s-1", "uM-1 s-1"
        v = u.replace('.', '').replace('*', '').replace('\u2022', '')
        v = re.sub(r'S(?=-1|\b)', 's', v)  # 'S-1.M-1': capital S is seconds here
        if re.search(r'M-?[2-9]', v):
            return None, None, f'not_kcat_over_km_unit:{raw_unit}'  # M^-2 s^-1 is kcat/(KmA*KmB), another metric
        conc = re.search(r'(pM|nM|uM|mM|M)-1', v) or re.search(r'/(pM|nM|uM|mM|M)(?![a-z])', v)  # never the M of a 'kcat/KM' label
        tim = re.search(r'(ms|sec|min|hr|h|s)(?:-1)', v) or re.search(r'/(ms|sec|min|hr|h|s)\b', v)
        if not conc or not tim:
            mass = _mass_tokens(raw_unit, u)
            if mass and mass[3] == {'mass': -1, 'vol': 1, 'time': -1}:  # ml mg^-1 s^-1, (mg/ml)^-1 min^-1, ml/(mg s)
                return x * VOLUME[mass[1]] / (MASS[mass[0]] * TIME[mass[2]]), MASS_UNIT['kcat/Km'], None
            return None, None, f'unknown_kcatkm_unit:{raw_unit}'
        fc = _conc(conc.group(1)); ft = _time(tim.group(1))
        if fc is None or ft is None:
            return None, None, f'unknown_kcatkm_unit:{raw_unit}'
        return x / (fc * ft) * 1e-3, 'mM^-1 s^-1', None
    return None, None, f'unknown_metric:{metric}'
