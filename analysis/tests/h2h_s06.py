"""rows_to_values() of the head-to-head's s06_enzyextract_manual.py, vendored verbatim for W1 (FREEZE.md F5).

Source: paper/evidence/h2h_20261101/s06_enzyextract_manual.py, lines 21-42 (commit be9b8ca), file sha256
fc3a9496ccdbf93a6fea88f86fe42bf75e4ad55f182e21dcba251978b66b7701; byte-identical to
work/top_journal_20261021/h2h/s06_enzyextract_manual.py of 2026-10-22 10:39 (MANIFEST.tsv there). s06 runs its scoring
at import, so only the function is copied; tools/w1/test_w1.py checks the copy against the source lines.
It reads EnzyExtract's manually curated set (gold strings such as '4.9 s^-1', '15 µM') with CatLog's units code
(h2h_common.parse_value_unit)."""
from h2h_common import parse_value_unit  # noqa: F401  (used by the verbatim function below)


def rows_to_values(df, src, pmids, idcol=None):
    out, unparsed = [], 0
    for k, r in df.iterrows():
        p = str(r['pmid']).strip()
        if p not in pmids:
            continue
        g = lambda c: r[c] if c in r and isinstance(r[c], str) else ''
        base = {'src': src, 'pmid': p, 'enzyme': f"{g('enzyme')} {g('enzyme_full')}", 'organism': g('organism'),
                'substrate': f"{g('substrate')} {g('substrate_full')}", 'variant': g('mutant'), 'temp': g('temperature'),
                'pH': g('pH'), 'cosub': '', 'where': g('src'), 'quote': g('descriptor')}
        for m, col in (('kcat', 'kcat'), ('Km', 'km'), ('kcat/Km', 'kcat_km')):
            raw = g(col)
            if not raw.strip() or raw.strip().lower() in ('none', 'nan', 'null'):
                continue
            v = parse_value_unit(m, raw)
            if v is None:
                unparsed += 1
                if src == 'ee_manual':  # a gold cell we cannot read as a number+unit: kept, not scored (like bounds)
                    out.append({**base, 'metric': m, 'value': None, 'raw': raw, 'bound': True, 'id': f'{src}{k}:{m}'})
                continue
            out.append({**base, 'metric': m, 'value': float(f'{v:.6g}'), 'raw': raw, 'bound': False, 'id': f'{src}{k}:{m}'})
    return out, unparsed
