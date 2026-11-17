#!/usr/bin/env python3
"""Claim 5.6 (outline §2): "Where database errors enter: whether the database copied a misprint or made the error in
curation." One-pass source: planning/top_journal_20261021/nmeth/reliability.md F2 (rel_02_databases.py): the paper's
own misprint copied faithfully is 6% of BRENDA's wrong values (171/2,758), 9% of OED's, 23% of SABIO-RK's (130/573),
21% of UniProt's; header multipliers misread 35% of SABIO-RK's (201), 8% of BRENDA's, 23% of UniProt's; the rest
curation errors (denominators: paper-checked plus code-found wrong values in the export of 2026-10-23).

Re-derived with my own code, per database, from sources/database_corrections.tsv (latest line per value and database,
verdict 'corrected', row still in the catalog, rd_lib.db_wrong), two ways of naming the wrong databases:
  named       the databases the check's line names;
  same_number also every database the line does not name, with no line of its own on that value, that lists the same
              wrong number (within 2%) for that paper and metric in sources/db_values.tsv (the export does the same).
Origins: cause paper_unit_misprint = copied the paper's misprint; header_scale_inverted / header_scale_ignored = header
multiplier misread; every other cause = another curation error. Code-found wrong values (exact factor, the paper's own
kcat / Km supports CatLog) exist only in an export: counted from today's export, so the one-pass denominators
(paper-checked + code-found) are rebuilt for today only. Also the pooled view of 02_catlog_vs_databases.md (a value
counted once). Writes results.json section C56."""
import collections
import json
import math
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rd_lib as L  # noqa: E402


def db_values_index():
    idx = collections.defaultdict(list)
    for r in L.tsv('sources/db_values.tsv'):
        try:
            v = float(r['value'])
        except (TypeError, ValueError):
            continue
        idx[(r['pmid'], r['metric'])].append((r['source'], v))
    return idx


def shares(counter):
    n = sum(counter.values())
    return {'n': n, **{o: {'k': counter[o], 'pct': round(100 * counter[o] / n, 1) if n else None,
                           'wilson': L.wilson(counter[o], n)}
                       for o in ('copied_paper_misprint', 'header_multiplier_misread', 'other_curation')}}


def per_database(commit, idx):
    wrong, cat, info = L.db_wrong(commit)
    lat, _ = L.latest_verdicts(commit)
    own = collections.defaultdict(set)
    for (rid, db) in lat:
        own[rid].add(db)
    named = {db: collections.Counter(L.origin(c) for _, c in w.values()) for db, w in wrong.items()}
    ext = {db: collections.Counter(named[db]) for db in L.DBS}
    added = collections.Counter()
    for (rid, db), r in lat.items():
        if r['verdict'] != 'corrected' or rid not in cat or rid not in wrong.get(db, {}):
            continue
        dv = L.number(r['database_value'])
        if not dv or dv <= 0:
            continue
        d = cat[rid]
        for src, v in idx.get((d['pmid'], d['metric']), []):
            if src in own[rid] or src not in L.DBS or v <= 0:
                continue
            if abs(math.log10(v / dv)) < math.log10(1.02):
                own[rid].add(src)  # count each database once per value
                ext[src][L.origin(r['cause'])] += 1
                added[src] += 1
    pooled = collections.Counter()
    seen = {}
    for db, w in wrong.items():
        for rid, (_, c) in w.items():
            o = L.origin(c)
            if rid not in seen or (seen[rid] == 'copied_paper_misprint' and o != 'copied_paper_misprint'):
                seen[rid] = o  # a value is a misreading if any database misread it
    pooled.update(seen.values())
    return {'verdict_file': info,
            'named': {db: shares(named[db]) for db in L.DBS},
            'same_number': {db: shares(ext[db]) for db in L.DBS},
            'same_number_added': dict(added),
            'pooled_values_once': shares(pooled)}


def export_code(path=os.path.join(L.ROOT, 'catlog_wide.jsonl')):
    """Today's export: wrong database values per database and origin, split by who found them (paper check / code).
    Code-found values carry no cause; one is counted as a header multiplier misread ('inferred') when the printed unit
    carries a multiplier 10^e and the database number is off by exactly 10^e or 10^2e, or is the printed number with
    the unit and multiplier not applied."""
    out = {db: {'paper_check': collections.Counter(), 'code': collections.Counter()} for db in L.DBS}
    for line in open(path):
        d = json.loads(line)
        for m, c in (d.get('database_check') or {}).items():
            if not isinstance(c, dict) or c.get('status') != 'corrected':
                continue
            who = 'code' if c.get('cause_by') == 'code' else 'paper_check'
            if c.get('cause'):
                o = L.origin(c['cause'])
            else:
                es = [abs(e) for _, e, _ in L.unit_multipliers(c.get('printed_unit')) if e]
                f = c.get('factor') or 0
                lf = abs(math.log10(f)) if f and f > 0 else None
                hit = lf is not None and any(abs(lf - k * e) < 0.01 for e in es for k in (1, 2))
                if es and (hit or c.get('relation') == 'printed_number_unit_not_applied'):
                    o = 'header_multiplier_inferred'
                else:
                    o = 'code_exact_factor_no_cause'
            for db in c.get('sources') or []:
                if db in out:
                    out[db][who][o] += 1
    res = {}
    for db, x in out.items():
        allc = x['paper_check'] + x['code']
        n = sum(allc.values())
        hdr = allc['header_multiplier_misread']
        res[db] = {'paper_check': dict(x['paper_check']), 'code': dict(x['code']), 'all_wrong': n,
                   'pct_copied_misprint_of_all': round(100 * allc['copied_paper_misprint'] / n, 1) if n else None,
                   'pct_curation_of_all': round(100 * (n - allc['copied_paper_misprint']) / n, 1) if n else None,
                   'pct_header_multiplier_of_all_labelled_only': round(100 * hdr / n, 1) if n else None,
                   'pct_header_multiplier_of_all_with_inferred': round(100 * (hdr + allc['header_multiplier_inferred']) / n, 1) if n else None}
    return res


def main():
    out = {'claim': 'claim 5.6: where database errors enter (copied paper misprint vs curation), per database',
           'original': {'denominator': 'paper-checked + code-found wrong values, export of 2026-10-23',
                        'copied_misprint': {'BRENDA': '171/2758 = 6.2%', 'OED': '104/1214 = 8.6%',
                                            'SABIO-RK': '130/573 = 22.7%', 'SKiD': '9/215 = 4.2%',
                                            'UniProt': '9/43 = 20.9%'},
                        'header_multiplier': {'BRENDA': '212/2758 = 7.7%', 'SABIO-RK': '201/573 = 35.1%',
                                              'UniProt': '10/43 = 23.3%', 'OED': '69/1214 = 5.7%', 'SKiD': '28/215 = 13.0%'},
                        'source': 'work/top_journal_20261021/nmeth/out/rel_02_databases.json'}}
    idx = db_values_index()
    out['snapshot_2026-10-23_e577b41'] = per_database(L.SNAP, idx)
    out['current_2026-10-31'] = per_database(None, idx)
    out['current_2026-10-31']['export_paper_check_plus_code'] = export_code()
    L.save('C56', out)
    for label in ('snapshot_2026-10-23_e577b41', 'current_2026-10-31'):
        r = out[label]
        print(label, 'pooled', r['pooled_values_once'])
        for db in L.DBS:
            a, b = r['named'][db], r['same_number'][db]
            print('  %-8s named n=%-5d copied %5.1f%% header %5.1f%% | same_number n=%-5d copied %5.1f%% header %5.1f%%' % (
                db, a['n'], a['copied_paper_misprint']['pct'] or 0, a['header_multiplier_misread']['pct'] or 0,
                b['n'], b['copied_paper_misprint']['pct'] or 0, b['header_multiplier_misread']['pct'] or 0))
    for db, x in out['current_2026-10-31']['export_paper_check_plus_code'].items():
        print('  export', db, x)


if __name__ == '__main__':
    main()
