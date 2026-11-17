#!/usr/bin/env python3
"""L46 (outline §4, claim 5.6): "BRENDA's wrong values that copy a misprint: 6% (171 of 2,758); papers BRENDA
misstates: 8.8% (442 of 5,001)". Source: planning/top_journal_20261021/nmeth/reliability.md F2 (rel_02_databases.py,
one pass, on the export of 2026-10-23 11:53: 2,758 = 1,690 values a paper check found wrong + 1,068 that code found
wrong; 5,001 = papers where BRENDA holds at least one value compared with a CatLog value).

Re-derived from raw files with my own code:
  * paper-checked wrong BRENDA values: sources/database_corrections.tsv, latest line per value and database, verdict
    'corrected', BRENDA named, the row still in the catalog and its value not now within 1.5x of the number the check
    named (rd_lib.db_wrong); cause 'paper_unit_misprint' = the database copied the paper's own misprint;
  * papers BRENDA cites: papers CatLog holds for which sources/db_values.tsv lists any BRENDA kcat, Km or kcat/Km
    value (and, narrower, a value of a metric CatLog holds for that paper);
  * code-found wrong values (exact unit factor, paper's own kcat / Km supports CatLog: tools/dbcompare.py rule A) exist
    only in an export. The export of 23 October is not kept, so they are counted from today's export only
    (catlog_wide.jsonl, database_check status 'corrected', cause_by 'code'), with the one-pass denominator for papers
    (BRENDA among the databases holding a compared value) counted there by my own code for comparison.
Writes results.json section L46."""
import collections
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rd_lib as L  # noqa: E402

DB = 'BRENDA'


def paper_checked(commit):
    wrong, cat, info = L.db_wrong(commit)
    w = wrong[DB]
    by_origin = collections.Counter(L.origin(c) for _, c in w.values())
    by_cause = collections.Counter(c for _, c in w.values())
    papers_w = {p for p, _ in w.values()}
    papers_w_not_copy = {p for p, c in w.values() if c != L.MISPRINT_CAUSE}
    anyp, samem = L.db_cited_papers(cat)
    n_pm = by_origin['copied_paper_misprint']
    res = {'verdict_file': info,
           'brenda_values_wrong_paper_checked': len(w),
           'by_origin': dict(by_origin), 'by_cause': dict(by_cause.most_common()),
           'share_copied_misprint_of_paper_checked': {'k': n_pm, 'n': len(w), 'pct': round(100 * n_pm / len(w), 2),
                                                      'wilson': L.wilson(n_pm, len(w))},
           'papers_with_a_paper_checked_wrong_brenda_value': len(papers_w),
           'papers_with_one_not_counting_copied_misprints': len(papers_w_not_copy),
           'catalog_papers': len({d['pmid'] for d in cat.values()})}
    for name, den in (('papers_brenda_lists_any_value_for', anyp[DB]), ('papers_brenda_lists_a_metric_catlog_holds', samem[DB])):
        k, k2 = len(papers_w & den), len(papers_w_not_copy & den)
        res[name] = {'n': len(den), 'with_wrong': k, 'pct': round(100 * k / len(den), 2), 'wilson': L.wilson(k, len(den)),
                     'with_wrong_not_counting_copied_misprints': k2, 'pct_not_counting_copied': round(100 * k2 / len(den), 2)}
    res['papers_with_wrong_outside_these_denominators'] = len(papers_w - anyp[DB])
    return res, w


def export_side(w_pc):
    """Today's export: code-found wrong BRENDA values, and the one-pass per-paper denominator, by my own counting."""
    held = collections.defaultdict(int)
    code = {}
    pc_in_export = set()
    for line in open(os.path.join(L.ROOT, 'catlog_wide.jsonl')):
        d = json.loads(line)
        pm = str(d.get('pubmed_id'))
        ev = d.get('evidence') or {}
        for m, c in (d.get('database_check') or {}).items():
            if not isinstance(c, dict) or m not in ev:
                continue
            st = c.get('status')
            if st not in ('confirmed', 'corrected', 'differs'):
                continue
            holders = set(c.get('sources') or []) | set((c.get('same_values') or {}).keys()) | \
                set(c.get('other_numbers') or []) | set((c.get('other_values') or {}).keys())
            if DB in holders:
                held[pm] += 1
            rid = ev[m].get('row_id')
            if st == 'corrected' and DB in (c.get('sources') or []):
                if c.get('cause_by') == 'code':
                    code[rid] = (pm, c.get('cause') or '', c.get('relation') or '', bool(c.get('read_as')))
                else:
                    pc_in_export.add(rid)
    by = collections.Counter(L.origin(cause) if cause else 'code_exact_factor_no_cause' for _, cause, _, _ in code.values())
    rel = collections.Counter(r for _, _, r, _ in code.values())
    n_pc = len(w_pc)
    n_pc_pm = sum(1 for _, c in w_pc.values() if c == L.MISPRINT_CAUSE)
    n_code_pm = by['copied_paper_misprint']
    tot = n_pc + len(code)
    papers_w = {p for p, _ in w_pc.values()}
    return {'code_found_wrong_brenda_values': len(code), 'code_found_by_origin': dict(by), 'code_found_by_relation': dict(rel),
            'code_found_on_rows_with_a_reader_unit_override': sum(1 for *_, o in code.values() if o),
            'paper_checked_rows_shown_corrected_in_export': len(pc_in_export & set(w_pc)),
            'all_wrong_brenda_values_paper_checked_plus_code': tot,
            'share_copied_misprint_of_all_wrong': {'k': n_pc_pm + n_code_pm, 'n': tot,
                                                   'pct': round(100 * (n_pc_pm + n_code_pm) / tot, 2),
                                                   'wilson': L.wilson(n_pc_pm + n_code_pm, tot)},
            'one_pass_denominator_papers_brenda_holds_a_compared_value': len(held),
            'papers_with_paper_checked_wrong_among_them': len(papers_w & set(held)),
            'pct_on_one_pass_denominator': round(100 * len(papers_w & set(held)) / len(held), 2),
            'wilson_on_one_pass_denominator': L.wilson(len(papers_w & set(held)), len(held))}


def main():
    out = {'claim': "L46 / claim 5.6: share of BRENDA's wrong values that copy the paper's misprint; papers BRENDA misstates",
           'original': {'brenda_wrong_values': 2758, 'paper_checked': 1690, 'code_found': 1068, 'copied_misprint': 171,
                        'pct_copied': 6.2, 'papers_with_paper_checked_wrong': 442, 'papers_held': 5001, 'pct_papers': 8.84,
                        'wilson': [8.08, 9.66], 'source': 'work/top_journal_20261021/nmeth/out/rel_02_databases.json'}}
    snap, _ = paper_checked(L.SNAP)
    out['snapshot_2026-10-23_e577b41'] = snap
    cur, w_cur = paper_checked(None)
    cur['export_2026-10-31'] = export_side(w_cur)
    out['current_2026-10-31'] = cur
    L.save('L46', out)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
