"""Stored kcat values that disagree with the paper's own printed Vmax (CLAUDE.md open item; FIXES_FOR_MAIN_CHAT item 3).

Where a paper prints a mass-specific rate (Vmax or specific activity in U/mg, µmol min^-1 mg^-1, ...), the enzyme's
turnover number follows from it and the subunit mass:

    kcat [s^-1] = Vmax [µmol min^-1 mg^-1] x M [kDa] / 60

so a kcat far above every rate the paper prints cannot be the paper's own number. This is the complement of
scale_sweep.py, whose closure test needs a printed kcat AND Km AND kcat/Km (its blind spot: "a table without a printed
kcat cannot be tested (15659684 printed Vmax in U/mg)").

It finds, with no agent, the four papers item 3 names (measured 2026-10-23; `factor` is the kindest reading, the
smallest offending kcat against the largest rate the paper prints, `worst` the paper's worst value):
  12435510   574x (worst 4171x, near 1000x)  Vmax 'about 20 U mg31' and a 'speci^cic activity of 20 U mg31 at 80C'
                                             (a symbol-font 'U mg^-1'), M 57.5 kDa -> kcat at most 19 s^-1
  21443518  4434x (near 3600x), 1 of 12      Table 'V max (units/mg)' beside 'k cat (s-1)'; the one offending value is
                                             its '505215', probably 505.215 s^-1
  18801468  11.9x (worst 8.5e4x)             'specific activity ... 75 +- 5 U (mg protein)^{- 1}' in JATS superscripts
  15265031  13.6x (worst 18.4x), ceiling     its unit sits in a table header ('lmolAEmin)1AEmg)1', a symbol-font
                                             'µmol·min^-1·mg^-1'), so no number stands beside it: bounded by CEILING
The whole catalog gives 186 papers (2026-10-23), led by 25824038 ('Super-perfect' enzymes, kcat 1.4e6-5.8e7 s^-1,
5.9e5x, near 1e6x) and with 1000x, 3600x and 60x the commonest factors: the shape of a misprinted unit header.

A flag, never a rule (CLAUDE.md "prefer a flag the user can filter on"): a printed rate can belong to another
substrate, another form or a crude extract, the subunit mass can be wrong for a multi-domain construct, and a paper may
print a rate per mg of membrane protein. The paper check decides; nothing here changes a value.

Columns of work/vmax_sweep.tsv (one line per paper, worst factor first): pmid, factor (the smallest offending
kcat / the largest kcat the printed rate implies: the kindest reading), factor_max (the paper's worst value the same way), near (the unit
factor it sits near: 60, 1000, 60000, 1e6, ...), kcat_stored (range), kcat_implied (range), vmax (the rates found, in
µmol min^-1 mg^-1), mass_kda, n_kcat (stored kcat values), n_above (those above the implied range by `fold`), source
(where the rates were read), title, and `checked` (the verdict of a paper check already done, work/vmax_<PMID>.json:
a paper checked once stays listed, because the sweep reads only rates printed beside a number and a check can find a
better one, as 16984804's purification table did).

    python3 tools/vmax_sweep.py            # the sweep
    python3 tools/vmax_sweep.py 12435510   # one paper, with every rate and kcat it found (for checking)
    python3 tools/vmax_sweep.py tasks <PMID> ...   # work/vmax_<PMID>.task.json for the paper check (prompts/vmax.md)
"""
import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from catlog import locked  # noqa: E402  (the method paper's test set: never swept)
WIDE, TEXTS, OUT = ROOT / 'catlog_wide.jsonl', ROOT / 'texts', ROOT / 'work' / 'vmax_sweep.tsv'
FOLD = 5.0        # a kcat this many times above every implied kcat is flagged (rounding and substrate choice are smaller)
UNIT_FACTORS = (60, 1000, 3600, 60000, 1e5, 1e6, 6e7, 1e9)

# average residue masses (Da); X/B/Z/J take an average residue, U and O their own
_AA = {'A': 71.0788, 'R': 156.1875, 'N': 114.1038, 'D': 115.0886, 'C': 103.1388, 'E': 129.1155, 'Q': 128.1307,
       'G': 57.0519, 'H': 137.1411, 'I': 113.1594, 'L': 113.1594, 'K': 128.1741, 'M': 131.1926, 'F': 147.1766,
       'P': 97.1167, 'S': 87.0782, 'T': 101.1051, 'W': 186.2132, 'Y': 163.1760, 'V': 99.1326, 'U': 150.0379,
       'O': 237.2982}
_AVG = sum(_AA[a] for a in 'ARNDCEQGHILKMFPSTWYV') / 20


def mass_kda(seq):
    """The subunit mass of a sequence in kDa (average residue masses + water), or None."""
    s = re.sub(r'[^A-Za-z]', '', seq or '').upper()
    return None if len(s) < 30 else (sum(_AA.get(a, _AVG) for a in s) + 18.0153) / 1000


# A mass-specific rate as papers print it, in the three text families this catalog has: clean text ('46 units/mg'),
# a symbol-font PDF whose glyphs are damaged (CLAUDE.md: µ prints as 'm' or 'l', the middle dot as 'Æ', minus as
# '21'/'31'/')1', so 'U mg^-1' becomes 'U mg31' and 'µmol·min^-1·mg^-1' becomes 'lmolÆmin)1Æmg)1'), and JATS
# superscripts ('U (mg protein)^{- 1}').
_N = r'(\d+(?:[.,]\d+)?)\s*(?:[(\[]?\s*(?:±|\+/-|6)\s*\d+(?:\.\d+)?\s*[)\]]?)?'
_PER = r'(?:\s*/\s*|\s*[·.ÆÅ]\s*|\s*per\s*|\s+)'
_M1 = r'(?:\^?\s*\{?\s*(?:-|−|–|\)|2|3)\s*1\s*\}?|\^?\s*-\s*1)?'   # '^-1', '^{- 1}', ')1', '21', '31'
_MG = r'\(?\s*(?:mg|milligram)(?:\s*(?:of\s*)?(?:protein|enzyme|prot\.?))?\s*\)?' + _M1
AMOUNT = r'(n|µ|μ|u|m|p|l)?\s*(?:mol|U\b|units?\b|IU\b)'
RATE = re.compile(_N + r'(?:x\s*10\^?(-?\d+)\s*)?' + AMOUNT
                  + r'(?:' + _PER + r'(?:min|minute)' + _M1 + r')?' + _PER + _MG, re.I)
# the same unit with no number beside it: a table header ('Vmax (lmolÆmin)1Æmg)1)'), whose values sit in the body
UNIT_ONLY = re.compile(AMOUNT + r'(?:' + _PER + r'(?:min|minute)' + _M1 + r')?' + _PER + _MG, re.I)
PREFIX = {'n': 1e-3, 'p': 1e-6, 'µ': 1, 'μ': 1, 'u': 1, 'l': 1, 'm': 1e3, None: 1, '': 1}
# 'm' before 'mol' is ambiguous in a damaged text ('mmol' is often 'µmol') and 'l' is a symbol-font µ: both readings
# are kept and the one that agrees best with the stored kcat wins, so the factor reported is the kindest one.
CEILING = 1e4  # µmol min^-1 mg^-1: higher than any specific activity in the databases' range; used only when the
# paper's rate unit is mass-specific but no number could be read beside it (a table header), to bound kcat from above
# Only a rate the paper offers as the enzyme's own maximal rate bounds its kcat. A rate from a relative-activity panel,
# a trace-substrate comparison or a crude extract does not (2026-10-23: 28533213's '100%, representing 0.103 pmol min21
# mg21 protein' and 2914904's '2.0 pmol/min/mg' for bradykinin are such rates, and gave factors of 1e7), so the match
# must sit near a word that names a maximal rate, and rates below FLOOR are not used as a bound at all.
NEAR_VMAX = re.compile(r'(?i)v\s*_?\{?\s*max|specific activity|specific activities|k\s*cat|turnover')
WINDOW = 160           # characters before the number in which that word must appear
FLOOR = 0.01           # µmol min^-1 mg^-1: below this a purified enzyme's rate is a panel or an extract, not a Vmax


def _number(raw):
    """The printed number: a comma is a thousands separator when exactly three digits follow it ('1,994 nmol' is
    1994 nmol, 2026-10-23: read as 1.994 it made 21132286 look 1000x worse), else a decimal comma."""
    raw = raw.strip()
    return float(re.sub(r',(?=\d{3}(?!\d))', '', raw)) if re.search(r',\d{3}(?!\d)', raw) else float(raw.replace(',', '.'))


def rates(text):
    """Every mass-specific rate the text offers as a maximal rate, in µmol min^-1 mg^-1, as (value, snippet)."""
    out = []
    for m in RATE.finditer(text):
        if not NEAR_VMAX.search(text[max(0, m.start() - WINDOW):m.end()]):
            continue  # not offered as the enzyme's maximal rate
        try:
            v = _number(m.group(1))
        except ValueError:
            continue
        if m.group(2):
            v *= 10.0 ** int(m.group(2))
        pre = (m.group(3) or '').lower()
        here = ' '.join(text[max(0, m.start() - 90):m.end() + 20].split())
        if v <= 0:
            continue
        for x in ([v * PREFIX.get(pre, 1)] + ([v] if pre in ('m', 'l') else [])):
            if x >= FLOOR:
                out.append((x, here[-110:]))
    return out


def unit_only(text):
    """True when the text prints a mass-specific rate unit at all (a Vmax column header, say)."""
    for m in UNIT_ONLY.finditer(text):
        if NEAR_VMAX.search(text[max(0, m.start() - WINDOW):m.end()]):
            return ' '.join(text[max(0, m.start() - 70):m.end() + 15].split())[-110:]
    return ''


def sweep(only=None):
    rows = [json.loads(l) for l in open(WIDE)] if WIDE.exists() else []
    if not rows:
        sys.exit(f'no {WIDE.name}: run `python3 catlog.py export` first')
    papers, held = defaultdict(lambda: {'kcat': [], 'mass': None, 'title': ''}), locked()
    for w in rows:
        p = w['pubmed_id']
        if only and p not in only or p in held:
            continue
        e = papers[p]
        e['title'] = e['title'] or (w.get('title') or '')
        if w.get('kcat') is not None and w['kcat'] > 0:
            e['kcat'].append((w['kcat'], w.get('measurement_id', ''), w.get('enzyme_name', ''), w.get('substrate_name', '')))
        m = mass_kda(w.get('uniprot_sequence') or w.get('sequence'))
        if m and (e['mass'] is None or m > e['mass']):
            e['mass'] = m          # the largest subunit of the paper: the kindest implied kcat
    out = []
    for p, e in papers.items():
        if not e['kcat'] or not e['mass']:
            continue
        t = TEXTS / f'{p}.txt'
        if not t.exists():
            continue
        text = t.read_text(errors='replace')
        found = rates(text)
        if found:  # a rate with a number beside it: the strong signal
            basis, implied = 'printed', [(v * e['mass'] / 60, s) for v, s in found]
        else:      # only the unit, in a table header whose values sit in the body: bound kcat by a generous ceiling
            u = unit_only(text)
            if not u:
                continue
            basis, implied = 'ceiling', [(CEILING * e['mass'] / 60, u)]
        hi = max(x for x, _ in implied)                     # the largest rate the paper prints: the kindest bound
        ks = [k for k, *_ in e['kcat']]
        above = [k for k in ks if k > hi * FOLD]
        if not above:                                       # n_above/n_kcat says whether it is one cell or a column
            continue
        factor = min(above) / hi                            # the smallest offending kcat: the kindest factor
        factor_max = max(above) / hi                        # the worst value of the paper, for the magnitude
        near = min(UNIT_FACTORS, key=lambda f: abs(math.log10(factor / f))) if factor > 1 else None
        near = near if near and 0.5 < factor / near < 2 else None
        src = max(implied, key=lambda x: x[0])[1]
        done = ROOT / 'work' / f'vmax_{p}.json'
        checked = ''
        if done.exists():
            try:
                v = json.loads(done.read_text())
                checked = str(v.get('verdict') or '') + (f": {v['summary'][:60]}" if v.get('summary') else '')
            except (OSError, json.JSONDecodeError):
                checked = 'unreadable work/vmax_<PMID>.json'
        out.append({'pmid': p, 'basis': basis, 'checked': checked, 'factor': factor, 'factor_max': factor_max, 'near': near, 'kcat_stored': (min(ks), max(ks)),
                    'kcat_implied': (min(x for x, _ in implied), hi), 'vmax': sorted({round(v, 4) for v, _ in found})[:6],
                    'mass_kda': round(e['mass'], 1), 'n_kcat': len(ks), 'n_above': len(above), 'source': src,
                    'title': (e['title'] or '')[:70], 'rows': e['kcat'], 'implied': implied})
    out.sort(key=lambda r: (r['basis'] != 'printed', -r['factor']))  # a printed rate first, then the ceiling rows
    return out



def tasks(pmids):
    """work/vmax_<PMID>.task.json: what the paper check needs (prompts/vmax.md), from the sweep, papers.tsv and the
    catalog. No database numbers and no export: the check reads the paper blind."""
    held = locked() & set(pmids)
    if held:
        print(f'left out (the method paper\'s test set): {" ".join(sorted(held))}', file=sys.stderr)
        pmids = [p for p in pmids if p not in held]
    if not pmids:
        return  # (sweep() with no papers named would take them all)
    res = {r['pmid']: r for r in sweep(set(pmids))}
    papers = {r['pmid']: r for r in csv.DictReader(open(ROOT / 'papers.tsv', encoding='utf-8'), delimiter='\t')
              if r['pmid'] in pmids}
    keep = ('row_id', 'metric', 'raw_value', 'raw_unit', 'unit_for_conversion', 'value', 'unit', 'enzyme', 'organism',
            'variant', 'substrate', 'cosubstrate', 'pH', 'temperature_C', 'location', 'quote', 'metric_note')
    rows = defaultdict(list)
    for line in open(ROOT / 'catalog.jsonl', encoding='utf-8'):
        if any(f'"pmid": "{p}"' in line for p in pmids):
            r = json.loads(line)
            if r['pmid'] in pmids:
                rows[r['pmid']].append({k: r.get(k, '') for k in keep})
    for p in pmids:
        text, r = TEXTS / f'{p}.txt', res.get(p)
        if p not in papers or not text.exists() or not r:
            print(f'{p}: no paper text, no papers.tsv line or not flagged; no task written')
            continue
        src = papers[p].get('text_source', '')
        bound = r['kcat_implied'][1] * FOLD
        over = [{'measurement_id': mid, 'kcat_s': k, 'enzyme': enz, 'substrate': sub, 'times_the_bound': round(k / bound, 2)}
                for k, mid, enz, sub in sorted(r['rows'], reverse=True) if k > bound]
        task = {'pmid': p, 'doi': papers[p].get('doi', ''), 'title': papers[p].get('title', ''),
                'text': f'texts/{p}.txt',
                'supplement': f'texts/{p}.supp.txt' if (TEXTS / f'{p}.supp.txt').exists() else '',
                'original_file': src.split(':', 1)[1] if ':' in src else src,
                'glyph_warning': text.read_text(errors='replace').startswith('GLYPH WARNING'),
                'basis': r['basis'], 'factor': round(r['factor'], 4), 'factor_worst': round(r['factor_max'], 4),
                'near_unit_factor': r['near'],
                'subunit_mass_kda': r['mass_kda'],
                'rates_found': [{'umol_min_mg': round(k * 60 / r['mass_kda'], 5), 'implies_kcat_s': round(k, 5),
                                 'printed': snip} for k, snip in sorted(set(r['implied']), reverse=True)[:8]]
                if r['basis'] == 'printed' else [],
                'ceiling_note': (f"no number stands beside the rate unit; kcat was bounded by a generous ceiling of "
                                 f"{CEILING:g} umol min^-1 mg^-1 ({r['kcat_implied'][1]:.4g} s^-1). Read the paper's own "
                                 f"Vmax cells and use them instead: {r['source']}") if r['basis'] == 'ceiling' else '',
                'kcat_above_the_bound': over, 'bound_kcat_s': round(bound, 5),
                'rows': rows[p]}
        out = ROOT / 'work' / f'vmax_{p}.task.json'
        out.write_text(json.dumps(task, indent=1, ensure_ascii=False))
        print(f"{p}: {len(over)} of {r['n_kcat']} stored kcat above the bound ({r['basis']}, {r['factor']:.4g}x) -> {out.relative_to(ROOT)}")


def main(args):
    if args and args[0] == 'tasks':
        return tasks([a for a in args[1:] if a.isdigit() or a.startswith('NP')])
    only = {a for a in args if a.isdigit() or a.startswith('NP')} or None
    res = sweep(only)
    if only:
        held = locked() & only
        for p in sorted(held):
            print(f"\n=== {p}\n   held out (the method paper's test set): not swept")
        for r in res or [{'pmid': p} for p in sorted(only - held)]:
            print(f"\n=== {r['pmid']}")
            if 'factor' not in r:
                print('   not flagged (no printed rate found, no mass, or a stored kcat agrees)'); continue
            print(f"   [{r['basis']}] mass {r['mass_kda']} kDa · stored kcat {r['kcat_stored'][0]:.4g}-{r['kcat_stored'][1]:.4g} s^-1 "
                  f"· implied {r['kcat_implied'][0]:.4g}-{r['kcat_implied'][1]:.4g} s^-1 · factor {r['factor']:.4g} (worst {r['factor_max']:.4g})"
                  + (f" (near {r['near']:g}x)" if r['near'] else ''))
            for v, s in sorted(r['implied'], reverse=True)[:6]:
                print(f"      rate -> kcat {v:.4g} s^-1   {s}")
            for k, mid, enz, sub in sorted(r['rows'], reverse=True)[:6]:
                print(f"      stored kcat {k:.6g}   {enz[:34]} / {sub[:24]}")
        return
    OUT.parent.mkdir(exist_ok=True)
    cols = ('pmid', 'basis', 'checked', 'factor', 'factor_max', 'near', 'kcat_stored', 'kcat_implied', 'vmax', 'mass_kda', 'n_kcat', 'n_above', 'source', 'title')
    with open(OUT, 'w') as fh:
        fh.write('\t'.join(cols) + '\n')
        for r in res:
            fh.write('\t'.join(str(r[c]).replace('\t', ' ') for c in cols) + '\n')
    print(f'{len(res)} papers whose every stored kcat is more than {FOLD:g}x above the kcat the paper\'s own printed '
          f'rate implies -> {OUT.relative_to(ROOT)}')
    for r in res[:12]:
        print(f"   {r['pmid']} {r['basis'][:7]:<8}{r['factor']:>9.4g}x" + (f" (near {r['near']:g})" if r['near'] else '          ')
              + f"  kcat {r['kcat_stored'][0]:.3g}-{r['kcat_stored'][1]:.3g} vs implied <= {r['kcat_implied'][1]:.3g}"
              f"  {r['n_above']}/{r['n_kcat']} values  {r['title'][:46]}")


if __name__ == '__main__':
    main(sys.argv[1:])
