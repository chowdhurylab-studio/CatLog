#!/usr/bin/env python3
"""L32 (outline §4, claim 3.8): "46,331 same-row printed triples in 3,838 papers; 1.28% failing grossly; papers
failing 5.68% (4.98-6.44%); the misprinted column decided from the paper in 43 of 46 papers".
Source of the claim: planning/top_journal_20261021/nmeth/reliability.md F1 (rel_01_closure.py, one pass).

Re-derived from catalog.jsonl (not the export), with my own grouping, printed-cell converter (rd_lib) and classes,
written from F1's stated definition:
  * a same-row printed triple = one record's kcat, Km and printed kcat/Km, all three cells quoted from ONE printed line
    (identical quote). Grouping: paper + quote, then enzyme, organism, variant, substrate, cosubstrate, pH,
    temperature, location and construct (then conditions and note when a metric repeats);
  * every cell converted from its PRINTED unit (a reader's unit_for_conversion is ignored);
  * F = printed kcat/Km / (kcat / Km); tolerance 10% plus the three cells' rounding, at most 35%;
  * classes: closes; explained by a printed multiplier read the other way or ignored (a reading hazard, not an error);
    exact unit factor (10^3k, 60, 3600); power of ten (10, 100; also 10^4, 10^5); other misses by size;
  * gross = unit factor + power of ten + other miss of 2x or more.
Variants (the stated definition and the one-pass code differ):
  A  as stated: a miss is 'explained' only when reading header multipliers the other way closes the triple: a
     multiplier printed in a column's unit, or a cell exponent the quoted line does not show (so it came from a
     header); any subset of the three columns may be flipped, each by 10^(2e) in the direction its role in F gives
     (kcat/Km and Km up, kcat down). A time-and-concentration product (3.6, 16.7, 0.06, ...) is gross (it misses by
     2x or more). A triple that a flip brings within 2x is not gross (under that reading it is a near miss).
  B  as coded, without its bug: the one-pass script's documented rule, re-implemented: every printed exponent e
     (0 < |e| < 13, cell or unit) explains a miss of 10^e, 10^2e, or the sum or difference of two of them; products
     not counted; strict tolerance.
  B_bug  B plus the one-pass script's spurious exponent 1: its regex for 'x 100' also matches the '10' of every printed
     'x 10^n' (word boundary before '^') and adds 10^1 to the explanations, so 10x, 100x and some 1000x misses in such
     triples were filed under 'multiplier'. B_bug exists only to show that this accounts for the difference.
Then the 43 of 46: work/scale_<PMID>.json verdicts, with the second looks (scale_<PMID>.second.json) applied.
Writes results.json section L32 and L32_flagged_triples.tsv (variant A, current catalog; ids and numbers only)."""
import collections
import glob
import itertools
import json
import math
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rd_lib as L  # noqa: E402

ID_FIELDS = ('enzyme', 'organism', 'variant', 'substrate', 'cosubstrate', 'pH', 'temperature_C', 'location', 'construct')
STATS = collections.Counter()


def triples(rows):
    """Yield (pmid, quote, {metric: row}) for same-row triples; STATS counts what is left out."""
    by_q = collections.defaultdict(list)
    for d in rows:
        if d.get('metric') in L.METRICS:
            by_q[(d['pmid'], (d.get('quote') or '').strip())].append(d)
    for (pm, q), rs in by_q.items():
        if not q:
            STATS['rows_with_empty_quote'] += len(rs)
            continue
        sub = collections.defaultdict(list)
        for d in rs:
            sub[tuple(str(d.get(k) if d.get(k) is not None else '') for k in ID_FIELDS)].append(d)
        for g in sub.values():
            mets = collections.Counter(d['metric'] for d in g)
            if not all(mets[m] for m in L.METRICS):
                continue
            if all(mets[m] == 1 for m in L.METRICS):
                yield pm, q, {d['metric']: d for d in g}
                continue
            byc = collections.defaultdict(list)  # a metric repeats: split by the condition text and the note
            for d in g:
                byc[(d.get('conditions') or '', d.get('metric_note') or '')].append(d)
            for g2 in byc.values():
                m2 = collections.Counter(d['metric'] for d in g2)
                if all(m2[m] == 1 for m in L.METRICS):
                    yield pm, q, {d['metric']: d for d in g2}
                elif all(m2[m] for m in L.METRICS):
                    STATS['ambiguous_groups'] += 1


def quote_shows_exponent(quote, mant, e):
    """True when the quoted line itself prints the cell's exponent next to its number (a per-cell 'a x 10^e')."""
    nq = L.norm(quote)
    sg = '-' if e < 0 else r'\+?'
    if not mant:
        return False
    if re.search(re.escape(mant) + r'[^|;\n]{0,30}?10\s*\^?\s*\(?\s*' + sg + r'\s*' + str(abs(e)) + r'(?!\d)', nq):
        return True
    return bool(re.search(re.escape(mant) + r'\s*[eE]\s*' + sg + r'0*' + str(abs(e)) + r'(?!\d)', nq))


def flips(cols):
    """A: log10 deviations from reading header multipliers the other way, any non-empty subset of the columns.
    cols: [(role sign, signed exponent)], role +1 for kcat/Km and Km, -1 for kcat (F = kcat/Km x Km / kcat)."""
    cols = [(r, e) for r, e in cols if e]
    out = set()
    for k in range(1, len(cols) + 1):
        for sub in itertools.combinations(cols, k):
            d = 2 * sum(r * e for r, e in sub)
            if d:
                out.add(d)
    return out


def coded_rule(exps):
    """B: the one-pass rule: |e| (0 < |e| < 13) explains 10^e and 10^2e, two of them their sum and difference;
    the candidates are applied in the direction of the miss."""
    el = sorted({abs(e) for e in exps if e and abs(e) < 13})
    cand = set()
    for e in el:
        cand |= {e, 2 * e}
    for i in range(len(el)):
        for j in range(i + 1, len(el)):
            cand |= {el[i] + el[j], abs(el[i] - el[j])}
    cand.discard(0)
    return {c for c in cand} | {-c for c in cand}


def classify(F, tol, dev, residual):
    lf = math.log10(F)
    if abs(F - 1) <= tol:
        return 'closes'
    lim = math.log10(2 * (1 + tol))
    for d in sorted(dev, key=abs):
        r = F / 10.0 ** d
        if (abs(math.log10(r)) <= lim) if residual else (abs(r - 1) <= tol):
            return 'multiplier'
    for a in (-2, -1, 0, 1, 2):
        for b in (-3, -2, -1, 0, 1, 2, 3):
            if (a, b) != (0, 0) and abs(F / (60.0 ** a * 1000.0 ** b) - 1) <= tol:
                return 'pow1000' if a == 0 else ('time' if b == 0 else 'mixed')
    for n in (1, 2, 4, 5):
        if abs(F / 10.0 ** (n if lf > 0 else -n) - 1) <= tol:
            return 'pow10_%d' % n
    x = abs(lf)
    if x <= math.log10(1.5 * (1 + tol)):
        return 'near_1.5x'
    if x <= math.log10(2 * (1 + tol)):
        return 'miss_1.5-2x'
    if x <= math.log10(5):
        return 'miss_2-5x'
    if x <= 1:
        return 'miss_5-10x'
    return 'miss_>10x'


GROUPS = {'unit_factor (10^3k, 60, 3600; A also their products)': {'pow1000', 'time', 'mixed'},
          'ten_x': {'pow10_1'}, 'power_of_ten (10, 100, 10^4, 10^5)': {'pow10_1', 'pow10_2', 'pow10_4', 'pow10_5'},
          'other_ge2x': {'miss_2-5x', 'miss_5-10x', 'miss_>10x'}, 'multiplier_reading_hazard': {'multiplier'}}
GROSS_A = {'pow1000', 'time', 'mixed', 'pow10_1', 'pow10_2', 'pow10_4', 'pow10_5', 'miss_2-5x', 'miss_5-10x', 'miss_>10x'}
GROSS_B = GROSS_A - {'mixed'}
SPURIOUS = re.compile(r'(?:x|\*)\s*\(?\s*10(?![\w])')  # what rel_01's MULT also matches inside 'x 10^n' (or 'x 10-3')


def run(commit):
    STATS.clear()
    rows = list(L.catalog(commit))
    res = {'rows': len(rows), 'papers_in_catalog': len({d['pmid'] for d in rows})}
    V = ('A', 'B', 'B_bug')
    cls = {v: collections.Counter() for v in V}
    pclass = {v: collections.defaultdict(set) for v in V}  # class group -> papers
    per_paper = {v: collections.defaultdict(int) for v in V}
    tables = {v: collections.defaultdict(int) for v in V}
    moved_by_residual = collections.Counter()
    flagged, n = [], 0
    for pm, q, t in triples(rows):
        conv = {}
        for m in L.METRICS:
            c = L.convert(m, t[m].get('raw_value'), t[m].get('raw_unit'))
            if not c or not c[0] or c[0] <= 0:
                conv = None
                break
            conv[m] = c
        if conv is None:
            STATS['triples_unparsable_as_printed'] += 1
            continue
        if conv['Km'][1] != conv['kcat/Km'][1]:
            STATS['triples_Km_and_kcat/Km_in_different_unit_families'] += 1
            continue
        n += 1
        F = conv['kcat/Km'][0] / (conv['kcat'][0] / conv['Km'][0])
        tol = min(0.35, 0.10 + sum(L.rel_rounding(conv[m][2]) for m in L.METRICS))
        unit_exps = [e for m in L.METRICS for e in conv[m][4]]
        cell = [(m, conv[m][3]) for m in L.METRICS if conv[m][3]]
        role = {'kcat': -1, 'Km': 1, 'kcat/Km': 1}
        hdr = []
        for m in L.METRICS:  # each column's header exponent: its unit's multipliers + a cell exponent the line lacks
            e = sum(conv[m][4])
            if conv[m][3] and not quote_shows_exponent(q, conv[m][2], conv[m][3]):
                e += conv[m][3]
            hdr.append((role[m], e))
        devA = flips(hdr)
        devB = coded_rule(unit_exps + [e for _, e in cell])
        spur = any(SPURIOUS.search(L.unit_text((t[m].get('raw_value') or '') + ' ' + (t[m].get('raw_unit') or '')))
                   for m in L.METRICS)
        devBb = coded_rule(unit_exps + [e for _, e in cell] + ([1] if spur else []))
        tab = (t['kcat/Km'].get('location') or '').split(',')[0].strip()
        cA = classify(F, tol, devA, residual=True)
        cA_strict = classify(F, tol, devA, residual=False)
        if cA != cA_strict:
            moved_by_residual[cA_strict + '->' + cA] += 1
        out = {'A': cA, 'B': classify(F, tol, devB, residual=False), 'B_bug': classify(F, tol, devBb, residual=False)}
        for v in V:
            gross = GROSS_A if v == 'A' else GROSS_B
            cls[v][out[v]] += 1
            for grp, members in GROUPS.items():
                if out[v] in members and (v == 'A' or out[v] != 'mixed'):
                    pclass[v][grp].add(pm)
            per_paper[v][pm] += out[v] in gross
            tables[v][(pm, tab)] += out[v] in gross
        if cA in GROSS_A:
            flagged.append((pm, tab, cA, float('%.6g' % F), t['kcat']['row_id'], t['Km']['row_id'], t['kcat/Km']['row_id']))
    papers = sorted(per_paper['A'])
    res['same_row_triples'] = n
    res['papers_with_a_same_row_triple'] = len(papers)
    res['left_out'] = dict(STATS)
    res['variant_A_residual_rule_moved'] = dict(moved_by_residual)
    for v in V:
        gross = GROSS_A if v == 'A' else GROSS_B
        g = sum(cls[v][c] for c in gross)
        fl = [1 if per_paper[v][p] else 0 for p in papers]
        k = sum(fl)
        tabs = list(tables[v].values())
        res['variant_' + v] = {
            'classes': dict(cls[v].most_common()),
            'triples_gross': g, 'pct_triples_gross': round(100 * g / n, 2), 'wilson_triples': L.wilson(g, n),
            'papers_flagged': k, 'pct_papers_flagged': round(100 * k / len(papers), 2),
            'wilson_papers': L.wilson(k, len(papers)), 'bootstrap_papers_2000': L.boot_ci(fl),
            'tables': len(tabs), 'tables_flagged': sum(1 for x in tabs if x),
            'pct_tables_flagged': round(100 * sum(1 for x in tabs if x) / len(tabs), 2),
            'papers_by_class_group': {grp: {'papers': len(ps), 'pct': round(100 * len(ps) / len(papers), 2),
                                            'wilson': L.wilson(len(ps), len(papers))}
                                      for grp, ps in sorted(pclass[v].items())}}
    return res, flagged


def scale_verdicts():
    """Per paper: the table verdicts of work/scale_<PMID>.json, a second look (.second.json) replacing its tables."""
    out = {}
    for f in sorted(glob.glob(os.path.join(L.ROOT, 'work', 'scale_*.json'))):
        b = os.path.basename(f)
        if b.count('.') != 1:
            continue
        d = json.load(open(f))
        pm = str(d.get('pmid') or b[6:-5])
        tv = {t.get('table'): t.get('verdict') for t in d.get('tables', [])}
        first = dict(tv)
        sec = f[:-5] + '.second.json'
        if os.path.exists(sec):
            for t in json.load(open(sec)).get('tables', []):
                tv[t.get('table')] = t.get('verdict')
        out[pm] = {'tables': tv, 'first_look': first, 'second_look': os.path.exists(sec)}
    return out


def summarize_scale(sv, flagged_papers, override_papers):
    DEC = {'header_misprint', 'cell_typo'}

    def kind(tv):
        vs = set(tv.values())
        if vs and vs <= DEC:
            return 'misprint_decided'
        if 'ambiguous' in vs:
            return 'ambiguous' if not (vs & DEC) else 'partly_decided'
        return 'consistent' if vs == {'consistent'} else 'other:' + '|'.join(sorted(vs))
    final = collections.Counter(kind(v['tables']) for v in sv.values())
    return {'papers': len(sv), 'with_second_look': sorted(p for p, v in sv.items() if v['second_look']),
            'first_look_only': dict(collections.Counter(kind(v['first_look']) for v in sv.values())),
            'after_second_look': dict(final),
            'changed_by_second_look': sorted(p for p, v in sv.items() if kind(v['tables']) != kind(v['first_look'])),
            'decided_after_second_look': final['misprint_decided'],
            'scale_papers_with_a_reader_unit_override_in_the_snapshot': sum(1 for p in sv if p in override_papers),
            'scale_papers_flagged_by_closure_variant_A_snapshot': sum(1 for p in sv if p in flagged_papers),
            'verdicts_by_paper': {p: v['tables'] for p, v in sorted(sv.items())}}


def main():
    out = {'claim': 'L32 / claim 3.8: same-row printed triples, papers, triples failing grossly, papers failing (CI), '
                    'misprinted column decided from the paper',
           'original': {'triples': 46331, 'papers': 3838, 'triples_gross': 592, 'pct_triples_gross': 1.28,
                        'papers_flagged': 218, 'pct_papers_flagged': 5.68, 'ci': [4.98, 6.44], 'decided': '43 of 46',
                        'source': 'work/top_journal_20261021/nmeth/out/rel_01_closure.json',
                        'snapshot': 'catlog_wide.jsonl 2026-10-23 11:53 (102,023 records, 6,622 papers)'}}
    override_snap = set()
    for label, commit in (('snapshot_2026-10-23_e577b41', L.SNAP), ('current_2026-10-31', None)):
        res, flagged = run(commit)
        out[label] = res
        if commit:
            flagged_snap = {r[0] for r in flagged}
            override_snap = {d['pmid'] for d in L.catalog(commit) if d.get('unit_for_conversion')}
        else:
            with open(os.path.join(L.HERE, 'L32_flagged_triples.tsv'), 'w') as f:
                f.write('pmid\ttable\tclass\tF_printed\tkcat_row\tKm_row\tkcat/Km_row\n')
                for r in sorted(flagged):
                    f.write('\t'.join(str(x) for x in r) + '\n')
    out['scale_check'] = summarize_scale(scale_verdicts(), flagged_snap, override_snap)
    L.save('L32', out)
    for label in ('snapshot_2026-10-23_e577b41', 'current_2026-10-31'):
        r = out[label]
        print(label, r['same_row_triples'], 'triples', r['papers_with_a_same_row_triple'], 'papers', r['left_out'],
              'residual moved', r['variant_A_residual_rule_moved'])
        for v in ('A', 'B', 'B_bug'):
            x = r['variant_' + v]
            print('  ', v, x['triples_gross'], x['pct_triples_gross'], '| papers', x['papers_flagged'],
                  x['pct_papers_flagged'], x['wilson_papers'], x['bootstrap_papers_2000'], '| tables',
                  x['tables_flagged'], x['tables'])
            print('     ', x['classes'])
    print(json.dumps({k: v for k, v in out['scale_check'].items() if k != 'verdicts_by_paper'}))


if __name__ == '__main__':
    main()
