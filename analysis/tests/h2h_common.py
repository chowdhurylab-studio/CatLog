"""Shared loaders, unit parsing, matching and bootstrap for the CatLog head-to-head (work/top_journal_20261021/h2h).
Read-only on the CatLog folder: nothing here writes outside h2h/."""
import csv, glob, json, math, os, re, sys
from collections import defaultdict
import numpy as np
import pandas as pd

sys.dont_write_bytecode = True  # importing tools/units.py must not write a __pycache__ into the project
ROOT = '<the CatLog folder>'
H2H = os.path.dirname(os.path.abspath(__file__))
BENCH = ROOT + '/work/top_journal_20261021/benchmarks'
GOLD_CSV = BENCH + '/cosci_raw/20241212_Golden_Benchmark_for_Enzyme_Kinetics_converted.csv'
EE_MANUAL = BENCH + '/enzyextract_si/data/dataset_223_EnzyExtract_BRENDA_manual_curation/manual_curated_runeem_dataset.csv'
sys.path.insert(0, ROOT + '/tools')
import units  # noqa: E402  (CatLog's own converter: printed cell + unit -> catalog units)

METRICS = ('kcat', 'Km', 'kcat/Km')
TOL = 0.015  # numeric agreement: |a-b| <= 1.5% of the larger


def load_gold_raw():
    return pd.read_csv(GOLD_CSV, dtype=str)


def load_ee_manual_raw():
    return pd.read_csv(EE_MANUAL, dtype=str)


def status():
    return {r['pmid']: r['status'] for r in csv.DictReader(open(ROOT + '/papers.tsv'), delimiter='\t')}


def num(s):
    """A plain numeric cell -> float; bounds ('<0.01', '>50'), '~0', blanks -> None."""
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return None
    s = str(s).strip()
    if re.fullmatch(r'-?\d*\.?\d+(?:[eE][-+]?\d+)?', s):
        return float(s)
    return None


def gold_values(pmids=None):
    """One record per gold value (gold row x metric). Bounds/approximate cells are kept with value None and bound=True."""
    g = load_gold_raw()
    out = []
    cols = {'Km': 'km(mM)', 'kcat': 'kcat(s^-1)', 'kcat/Km': 'km_kcat(mM^-1s^-1)'}
    for _, r in g.iterrows():
        p = r['pubmed_id'].strip()
        if pmids is not None and p not in pmids:
            continue
        for m, c in cols.items():
            raw = r[c]
            if raw is None or (isinstance(raw, float) and math.isnan(raw)) or not str(raw).strip():
                continue
            v = num(raw)
            if v == 0:
                v = None  # a printed 0 (no activity) or a value gold's 6-decimal rounding made 0: not scored, like bounds
            out.append({'src': 'gold', 'pmid': p, 'metric': m, 'value': v, 'raw': str(raw).strip(), 'bound': v is None,
                        'id': f"g{r['ID_gold']}:{m}", 'gold_id': r['ID_gold'],
                        'enzyme': str(r['Enzyme']).strip(), 'organism': str(r['Organism']).strip(),
                        'substrate': str(r['Substrate']).strip(), 'variant': str(r['Commentary[Mutant]']).strip(),
                        'temp': str(r['Commentary[Temp]']).strip(), 'pH': str(r['Commentary[pH]']).strip(),
                        'cosub': str(r['Commentary[Cosubstrate]']).strip(), 'where': str(r['Reference[Table/Text]']).strip()})
    return out


def catalog_rows(pmids):
    """Current catalog.jsonl rows of these papers (after every drop and unitfix so far)."""
    out = []
    with open(ROOT + '/catalog.jsonl') as f:
        for line in f:
            m = re.match(r'\{"pmid": "([^"]+)"', line)
            if m and m.group(1) not in pmids:
                continue
            r = json.loads(line)
            if r['pmid'] in pmids:
                out.append(r)
    return out


def derived_kcatkm(pmids):
    """kcat/Km values the export derives from kcat / Km (kcat_over_km_source == 'derived'), in mM^-1 s^-1."""
    out = []
    with open(ROOT + '/catlog_wide.jsonl') as f:
        for line in f:
            m = re.search(r'"pubmed_id": "([^"]+)"', line[:200])
            if m and m.group(1) not in pmids:
                continue
            r = json.loads(line)
            if r['pubmed_id'] in pmids and str(r.get('kcat_over_km_source', '')).startswith('derived') and num(r.get('kcat_over_km')):
                out.append({'src': 'catlog_derived', 'pmid': r['pubmed_id'], 'metric': 'kcat/Km', 'value': num(r['kcat_over_km']),
                            'raw': 'derived', 'id': 'd' + r['measurement_id'], 'enzyme': r.get('enzyme_name', ''),
                            'organism': r.get('organism', ''), 'substrate': r.get('substrate_name', ''),
                            'variant': r.get('mutation_signature', '') or ('wild type' if r.get('wild_type') == 'True' else ''),
                            'temp': r.get('temperature_c', '') if r.get('temperature_c') not in (None, 'None') else '',
                            'pH': r.get('ph', '') if r.get('ph') not in (None, 'None') else '', 'cosub': r.get('cosubstrate', ''),
                            'where': 'derived', 'quote': ''})
    return out


def catalog_values(rows, stage='catlog'):
    out = []
    for r in rows:
        if r.get('unit') not in ('s^-1', 'mM', 'mM^-1 s^-1') or r.get('value') in (None, ''):
            continue  # mass-concentration Km (mg/mL) and its kcat/Km are never compared
        out.append({'src': stage, 'pmid': r['pmid'], 'metric': r['metric'], 'value': float(r['value']), 'raw': r.get('raw_value', ''),
                    'raw_unit': r.get('raw_unit', ''), 'id': r.get('row_id') or r.get('_id'), 'enzyme': r.get('enzyme', ''),
                    'organism': r.get('organism', ''), 'substrate': r.get('substrate', ''), 'variant': r.get('variant', ''),
                    'temp': '' if r.get('temperature_C') is None else str(r.get('temperature_C')),
                    'pH': '' if r.get('pH') is None else str(r.get('pH')), 'cosub': r.get('cosubstrate', ''),
                    'where': r.get('location', ''), 'quote': r.get('quote', ''), 'conditions': r.get('conditions', ''),
                    'metric_note': r.get('metric_note', '')})
    return out


# ---------- unit parsing of other systems' strings ('4.9 s^-1', '15 µM', '0.12 s^-1 (µmol/L)^-1') ----------
NUMPART = re.compile(r'^\s*([-+]?[\d.,]+(?:\s*(?:±|\+/-|\+-)\s*[\d.,]+)?(?:\s*(?:x|\*|×)\s*10\s*\^?\s*\(?[-−]?\s*\d+\)?)?(?:[eE][-+]?\d+)?)\s*(.*)$')


def parse_value_unit(metric, s):
    """A value string with its unit -> catalog-unit float, or None. Uses CatLog's units.normalize on (number, unit)."""
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return None
    s = units.clean(str(s)).strip()
    if not s or s.lower() in ('none', 'nan', 'null'):
        return None
    if re.match(r'^\s*(<|>|≤|≥|~|ca)', s):
        return None
    m = NUMPART.match(s)
    if not m:
        return None
    val, unit = m.group(1), m.group(2).strip()
    if not unit:
        return None
    v, u, err = units.normalize(metric, val, unit)
    if err or v is None or u not in ('s^-1', 'mM', 'mM^-1 s^-1'):
        return None
    return v


# ---------- description similarity ----------
WT = re.compile(r'^(wt|wild[\s-]*type|wildtype|native|none|nan|-|)$', re.I)
MUT = re.compile(r'([A-Z])(\d{1,4})([A-Z])')
AA3 = {'ala': 'A', 'arg': 'R', 'asn': 'N', 'asp': 'D', 'cys': 'C', 'gln': 'Q', 'glu': 'E', 'gly': 'G', 'his': 'H', 'ile': 'I',
       'leu': 'L', 'lys': 'K', 'met': 'M', 'phe': 'F', 'pro': 'P', 'ser': 'S', 'thr': 'T', 'trp': 'W', 'tyr': 'Y', 'val': 'V'}


def mutations(v):
    v = str(v or '')
    v2 = re.sub(r'(?i)\b(' + '|'.join(AA3) + r')(\d{1,4})(' + '|'.join(AA3) + r')\b',
                lambda m: AA3[m.group(1).lower()] + m.group(2) + AA3[m.group(3).lower()], v)
    return frozenset(''.join(t) for t in MUT.findall(v2))


def is_wt(v):
    v = str(v or '').strip()
    return bool(WT.match(v)) or (not mutations(v) and bool(re.search(r'(?i)wild|\bwt\b|native', v)))


def norm_tokens(s):
    s = units.clean(str(s or '')).lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return set(t for t in s.split() if t not in ('the', 'of', 'and', 'nan', 'none', 'd', 'l', 'beta', 'alpha', 'b', 'a'))


def tok_sim(a, b):
    A, B = norm_tokens(a), norm_tokens(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def fnum(s):
    m = re.search(r'-?\d+(?:\.\d+)?', str(s or ''))
    return float(m.group(0)) if m else None


def desc_sim(g, c):
    """0..~5: variant agreement weighs most, then substrate, enzyme, temperature, pH."""
    s = 0.0
    gm, cm = mutations(g['variant']), mutations(c['variant'])
    if gm or cm:
        s += 2.0 if gm == cm else (0.8 if gm & cm else 0.0)
    else:
        s += 2.0 if (is_wt(g['variant']) or not str(g['variant']).strip()) == (is_wt(c['variant']) or not str(c['variant']).strip()) else 1.0
    s += 1.5 * max(tok_sim(g['substrate'], c['substrate']), tok_sim(g['substrate'], c.get('quote', '')) * 0.7)
    s += 0.7 * max(tok_sim(g['enzyme'], c['enzyme']), tok_sim(g['organism'], c['organism']) * 0.5)
    gt, ct = fnum(g['temp']), fnum(c['temp'])
    if gt is not None and ct is not None:
        s += 0.4 if abs(gt - ct) < 0.6 else 0.0
    gp, cp = fnum(g['pH']), fnum(c['pH'])
    if gp is not None and cp is not None:
        s += 0.4 if abs(gp - cp) < 0.06 else 0.0
    return s


GOLD_ROUND = 5.000001e-7  # the gold CSV rounds converted values to 6 decimals (2e-06 for 1.67e-6): half a unit of the 6th decimal


def close(a, b, tol=TOL):
    if a is None or b is None or a <= 0 or b <= 0:
        return False
    return abs(a - b) <= max(tol * max(a, b), GOLD_ROUND)


def match(gold, sysv, tol=TOL):
    """Per paper and metric: pair gold values with system values that agree within tol, one-to-one, maximising the
    number of pairs first and the description similarity second (Hungarian assignment).
    Returns (pairs [(gi, si, sim)], gold_unmatched idx, sys_unmatched idx)."""
    from scipy.optimize import linear_sum_assignment
    by = defaultdict(lambda: ([], []))
    for i, g in enumerate(gold):
        if g['value'] is not None:
            by[(g['pmid'], g['metric'])][0].append(i)
    for j, s in enumerate(sysv):
        by[(s['pmid'], s['metric'])][1].append(j)
    pairs = []
    for key, (gi, si) in by.items():
        if not gi or not si:
            continue
        cost = np.full((len(gi), len(si)), 1e6)
        for a, i in enumerate(gi):
            for b, j in enumerate(si):
                if close(gold[i]['value'], sysv[j]['value'], tol):
                    cost[a, b] = -(1000 + desc_sim(gold[i], sysv[j]))
        if (cost < 0).any():
            ra, cb = linear_sum_assignment(cost)
            for a, b in zip(ra, cb):
                if cost[a, b] < 0:
                    pairs.append((gi[a], si[b], -cost[a, b] - 1000))
    mg = {p[0] for p in pairs}; ms = {p[1] for p in pairs}
    gu = [i for i, g in enumerate(gold) if g['value'] is not None and i not in mg]
    su = [j for j in range(len(sysv)) if j not in ms]
    return pairs, gu, su


def desc_pairs(gold, sysv, gu, su, min_sim=3.2):
    """Among values left over on both sides, pair a gold value with a system value of the same paper and metric when
    their descriptions agree (variant + substrate at least): a numeric disagreement on the same measurement."""
    from scipy.optimize import linear_sum_assignment
    by = defaultdict(lambda: ([], []))
    for i in gu:
        by[(gold[i]['pmid'], gold[i]['metric'])][0].append(i)
    for j in su:
        by[(sysv[j]['pmid'], sysv[j]['metric'])][1].append(j)
    out = []
    for key, (gi, si) in by.items():
        if not gi or not si:
            continue
        sim = np.array([[desc_sim(gold[i], sysv[j]) for j in si] for i in gi])
        ra, cb = linear_sum_assignment(-sim)
        for a, b in zip(ra, cb):
            if sim[a, b] >= min_sim:
                out.append((gi[a], si[b], float(sim[a, b])))
    return out


def scores(gold, sysv, pairs, papers):
    """Per paper counts for recall/precision; returns dict metric -> DataFrame(pmid, gold_n, sys_n, matched)."""
    res = {}
    for m in list(METRICS) + ['all']:
        rows = []
        for p in papers:
            gn = sum(1 for g in gold if g['pmid'] == p and g['value'] is not None and (m == 'all' or g['metric'] == m))
            sn = sum(1 for s in sysv if s['pmid'] == p and (m == 'all' or s['metric'] == m))
            mn = sum(1 for (i, j, _) in pairs if gold[i]['pmid'] == p and (m == 'all' or gold[i]['metric'] == m))
            rows.append((p, gn, sn, mn))
        res[m] = pd.DataFrame(rows, columns=['pmid', 'gold_n', 'sys_n', 'matched'])
    return res


def boot(df, num_col, den_col, B=2000, seed=7):
    """Ratio of sums with a paper-clustered bootstrap 95% CI (resample papers with replacement)."""
    d = df[df[den_col] > 0]
    if d.empty:
        return {'est': None, 'lo': None, 'hi': None, 'num': 0, 'den': 0, 'papers': 0}
    n, k = d[num_col].to_numpy(float), d[den_col].to_numpy(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(B, len(d)))
    r = n[idx].sum(1) / k[idx].sum(1)
    return {'est': float(n.sum() / k.sum()), 'lo': float(np.percentile(r, 2.5)), 'hi': float(np.percentile(r, 97.5)),
            'num': int(n.sum()), 'den': int(k.sum()), 'papers': int(len(d))}


def summarize(gold, sysv, pairs, papers, B=2000):
    sc = scores(gold, sysv, pairs, papers)
    out = {}
    for m, d in sc.items():
        out[m] = {'recall': boot(d, 'matched', 'gold_n', B), 'precision': boot(d, 'matched', 'sys_n', B),
                  'gold_n': int(d.gold_n.sum()), 'sys_n': int(d.sys_n.sum()), 'matched': int(d.matched.sum()),
                  'gold_left': int(d.gold_n.sum() - d.matched.sum()), 'sys_left': int(d.sys_n.sum() - d.matched.sum())}
    return out


def save_json(path, obj):
    with open(path, 'w') as f:
        json.dump(obj, f, indent=1, default=str)


def enzyextract_values(pmids):
    """EnzyExtract's extracted database (TheData.parquet via data/thedata_subset.tsv): kcat_value (s^-1) and km_value
    (M, x1000 -> mM) as the database stores them; kcat_km has no numeric column, so its string is converted with CatLog's
    units code."""
    t = pd.read_csv(H2H + '/data/thedata_subset.tsv', sep='\t', dtype=str)
    out = []
    for k, r in t.iterrows():
        p = r['catlog_pmid']
        if p not in pmids:
            continue
        base = {'src': 'enzyextract', 'pmid': p, 'enzyme': f"{r['enzyme']} {r['enzyme_full'] if isinstance(r['enzyme_full'], str) else ''}",
                'organism': r['organism'], 'substrate': f"{r['substrate']} {r['substrate_full'] if isinstance(r['substrate_full'], str) else ''}",
                'variant': r['mutant'] if isinstance(r['mutant'], str) else '', 'temp': r['temperature'], 'pH': r['pH'],
                'cosub': '', 'where': '', 'quote': r['descriptor'] if isinstance(r['descriptor'], str) else ''}
        for m, v in (('kcat', num(r['kcat_value'])), ('Km', None if num(r['km_value']) is None else num(r['km_value']) * 1000),
                     ('kcat/Km', parse_value_unit('kcat/Km', r['kcat_km']))):
            raw = {'kcat': r['kcat'], 'Km': r['km'], 'kcat/Km': r['kcat_km']}[m]
            if v is not None and v > 0:
                out.append({**base, 'metric': m, 'value': float(f'{v:.6g}'), 'raw': raw, 'id': f'ee{k}:{m}'})
    return out


def brenda_values(pmids, source='BRENDA'):
    out = []
    with open(ROOT + '/sources/db_values.tsv') as f:
        for k, r in enumerate(csv.DictReader(f, delimiter='\t')):
            if r['source'] != source or r['pmid'] not in pmids or r['metric'] not in METRICS:
                continue
            v = num(r['value'])
            if v is None or v <= 0:
                continue
            c = r.get('comment', '') or ''
            t = re.search(r'(\d+(?:\.\d+)?)\s*°\s*C', c)
            ph = re.search(r'pH\s*(\d+(?:\.\d+)?)', c)
            mut = ' '.join(sorted(mutations(c))) or ('wild type' if re.search(r'(?i)wild', c) or not re.search(r'(?i)mutant', c) else 'mutant')
            out.append({'src': source.lower(), 'pmid': r['pmid'], 'metric': r['metric'], 'value': v, 'raw': r['value'],
                        'id': f'b{k}', 'enzyme': r['ec'], 'organism': r['organism'], 'substrate': r['substrate'],
                        'variant': mut, 'temp': t.group(1) if t else '', 'pH': ph.group(1) if ph else '', 'cosub': '',
                        'where': '', 'quote': c})
    return out
