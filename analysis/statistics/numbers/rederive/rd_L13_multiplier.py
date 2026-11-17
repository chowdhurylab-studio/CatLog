#!/usr/bin/env python3
"""L13 (outline §4, claim 2.5): "papers that print a x10^n header: 8.0% (532 of 6,622)", and the sentence beside it
in reliability.md F2: "In 7.3% of those, a database is paper-checked wrong because of it (41 papers in all)".
Source of the claim: planning/top_journal_20261021/nmeth/reliability.md F2 (rel_06_multiplier.py, one pass: a paper
counts when a printed unit of any of its kcat, Km or kcat/Km cells matches its multiplier regex).

Re-derived from catalog.jsonl with my own detection (rd_lib.unit_multipliers: 10^n with a caret, a flattened '10-3',
'x 100', '1000 x', 'x 10' whose exponent the text lost, '10^?'), at the 23 October snapshot and today. Counts:
  any          a printed unit (raw_unit) of a kcat, Km or kcat/Km row carries a power-of-ten multiplier (the claim's
               definition);
  caret        the same, counting only the '10^n' and 'x 100'/'1000 x' forms (closest to the one-pass regex);
  unit_header  'any' less rows whose unit multiplier is the cell's own exponent, printed beside its number on the
               quoted line (a per-cell exponent copied into the unit, not a header);
  override_only (sensitivity) papers not in 'any' whose reader wrote a power-of-ten multiplier only into
               unit_for_conversion (a header multiplier the printed unit as copied may lack).
A count of header multipliers folded into the value (a cell exponent the quoted line does not show) was tried and
dropped: in samples of those rows nearly every one was a per-cell exponent that the PDF or OCR text layer garbles
('x 10°', '´ 10 4', 'E ⫹ 05'), so it cannot tell a header from a cell.
Then the database side: papers with a paper-checked database error of cause header_scale_inverted or
header_scale_ignored (sources/database_corrections.tsv, verdict corrected), all lines and latest line per value and
database, and how many of them print a header multiplier. Writes results.json section L13."""
import collections
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rd_lib as L  # noqa: E402

HDR_CAUSES = {'header_scale_inverted', 'header_scale_ignored'}


def shows(quote, mant, e):
    """The quoted line prints exponent e right after the cell's number (a per-cell 'a x 10^e')."""
    if not mant or e is None:
        return False
    nq = L.norm(quote)
    sg = '-' if e < 0 else r'\+?'
    return bool(re.search(re.escape(mant) + r'[^|;\n]{0,30}?10\s*\^?\s*\(?\s*' + sg + r'\s*' + str(abs(e)) + r'(?!\d)', nq)
                or re.search(re.escape(mant) + r'\s*[eE]\s*' + sg + r'0*' + str(abs(e)) + r'(?!\d)', nq))


def run(commit):
    rows = [d for d in L.catalog(commit) if d.get('metric') in L.METRICS]
    papers = {d['pmid'] for d in rows}
    any_p, caret_p, hdr_p, ovr_p = set(), set(), set(), set()
    forms = collections.Counter()
    set_aside = collections.Counter()
    for d in rows:
        found = L.unit_multipliers(d.get('raw_unit'))
        if found:
            any_p.add(d['pmid'])
            for f, e, _ in found:
                forms[f] += 1
            if any(f in ('caret', 'x_power', 'power_x') and e is not None for f, e, _ in found):
                caret_p.add(d['pmid'])
            pv = L.parse_value(d.get('raw_value'))
            es = [e for _, e, _ in found]
            if len(es) == 1 and pv and shows(d.get('quote') or '', pv[1], es[0]):
                set_aside['rows_whose_unit_multiplier_is_the_cells_own_exponent'] += 1
            else:
                hdr_p.add(d['pmid'])
        elif d.get('unit_for_conversion') and L.unit_multipliers(d['unit_for_conversion']):
            ovr_p.add(d['pmid'])
    return rows, papers, any_p, caret_p, hdr_p, ovr_p - any_p, forms, set_aside


def db_header(commit, papers, sets):
    lines = L.tsv('sources/database_corrections.tsv', commit)
    all_lines = {r['pmid'] for r in lines if r['verdict'] == 'corrected' and r['cause'] in HDR_CAUSES}
    latest = {}
    for i, r in sorted(enumerate(lines), key=lambda x: (x[1]['date'], x[0])):
        for db in [x.strip() for x in r['database'].split(',') if x.strip()]:
            latest[(r['row_id'], db)] = r
    lat = {r['pmid'] for r in latest.values() if r['verdict'] == 'corrected' and r['cause'] in HDR_CAUSES}
    per_db = collections.Counter()
    for (rid, db), r in latest.items():
        if r['verdict'] == 'corrected' and r['cause'] in HDR_CAUSES:
            per_db[(db, r['pmid'])] += 1
    out = {'papers_with_header_cause_db_error_any_line': len(all_lines),
           'papers_with_header_cause_db_error_latest_line': len(lat),
           'of_which_in_catalog': len(lat & papers),
           'per_database_papers': dict(collections.Counter(db for db, _ in per_db))}
    for name, s in sets.items():
        k = len(lat & s)
        out['header_cause_papers_among_' + name] = {'k': k, 'n': len(s), 'pct': round(100 * k / len(s), 2),
                                                     'wilson': L.wilson(k, len(s))}
        k2 = len(all_lines & s)
        out['header_cause_papers_any_line_among_' + name] = {'k': k2, 'pct': round(100 * k2 / len(s), 2)}
    rest = papers - sets['any']
    out['header_cause_papers_among_papers_without_a_multiplier'] = {'k': len(lat & rest), 'n': len(rest)}
    return out


def main():
    out = {'claim': 'L13 / claim 2.5: papers that print a x10^n header in a kcat, Km or kcat/Km column',
           'original': {'papers_with_multiplier': 532, 'papers': 6622, 'pct': 8.03,
                        'header_cause_db_error_papers': 41, 'of_the_532_with_such_an_error': 39, 'pct_of_532': 7.33,
                        'source': 'work/top_journal_20261021/nmeth/out/rel_06_multiplier.json'}}
    for label, commit in (('snapshot_2026-10-23_e577b41', L.SNAP), ('current_2026-10-31', None)):
        rows, papers, any_p, caret_p, hdr_p, ovr_p, forms, set_aside = run(commit)
        N = len(papers)
        res = {'papers': N, 'rows': len(rows), 'multiplier_forms_seen': dict(forms), 'set_aside': dict(set_aside)}
        for name, s_ in (('any', any_p), ('caret', caret_p), ('unit_header', hdr_p), ('override_only', ovr_p),
                         ('any_or_override_only', any_p | ovr_p)):
            res[name] = {'papers': len(s_), 'pct': round(100 * len(s_) / N, 2), 'wilson': L.wilson(len(s_), N)}
        res['database'] = db_header(commit, papers, {'any': any_p, 'unit_header': hdr_p})
        out[label] = res
        print(label, N, {k: res[k] for k in ('any', 'caret', 'unit_header', 'override_only', 'any_or_override_only')},
              res['set_aside'], res['multiplier_forms_seen'])
        print('   ', res['database'])
    L.save('L13', out)


if __name__ == '__main__':
    main()
