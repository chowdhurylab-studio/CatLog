"""List the reworded copies a re-read (e.g. a supplement re-read) added next to a paper's earlier accepted rows.

Usage: python3 tools/reread_copies.py PMID [OUT_TSV]
New rows = the paper's rows (catalog.jsonl and bounds.jsonl) stamped with the latest `added` time; old rows = earlier
ones. A new row is a copy of an old row only when ALL hold: same location, metric, printed cell (raw_value), raw unit,
variant, censored kind and limit, and catlog.same_quote(old, new); pairing is one to one (raw value and unit compared
with spaces, braces and minus signs set aside: '10^{−5}' = '10^-5'). Several old candidates are told apart only by an
identical normalized substrate, then by the enzyme's name before any bracket ('vGalDH' = 'vGalDH (ancestral ...)');
otherwise the row is listed as AMBIGUOUS and not written.
A pair whose substrates differ beyond spelling is listed as RELABEL and not written either: the two reads put the same
printed cell on different substrates, and the paper decides which label stays (2026-11-12: 38714198's LDH block,
measured with PEP varied and pyruvate made in situ by excess PykA; the copy carried the right label, PEP, so the
earlier 'pyruvic acid' rows were dropped, 3 of 3 blind judges; 28877217's 'HGluβNA' was the paper's 'GluNA').
Writes row_id<TAB>why lines for `catlog.py drop --file` (it drops nothing itself).
"""
import collections, json, re, sys
from pathlib import Path
sys.argv, args = ['catlog.py'], sys.argv[1:]
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # this repository: catlog.py
import catlog

pmid = args[0]
out = args[1] if len(args) > 1 else None
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
pairs, ambiguous, unmatched, sets = [], [], [], []
for fname in ('catalog.jsonl', 'bounds.jsonl'):
    rows = [json.loads(l) for l in open(catlog.ROOT / fname) if f'"{pmid}"' in l]
    rows = [r for r in rows if r['pmid'] == pmid]
    if not rows:
        continue
    latest = max(r.get('added', '') for r in rows)
    new = [r for r in rows if r.get('added', '') == latest]
    old = [r for r in rows if r.get('added', '') < latest]
    if not old:
        continue
    sets.append((fname, new, old))
    unit = lambda u: re.sub(r'[\s{}]', '', u or '').replace('–', '-').replace('−', '-').replace('μ', 'µ')
    key = lambda r: (r.get('location'), r.get('metric'), unit(r.get('raw_value')), unit(r.get('raw_unit')),
                     r.get('censored'), r.get('limit'))
    enz = lambda r: norm((r.get('enzyme') or '').split(' (')[0])
    # a variant spelled out with its mutations and the earlier label in brackets is the same variant (catlog.spelled_out)
    same_var = lambda a, b: a == b or catlog.spelled_out(a, b) or catlog.spelled_out(b, a)
    pool = collections.defaultdict(list)
    for o in old:
        pool[key(o)].append(o)
    for n in new:
        cands = [o for o in pool[key(n)] if same_var(o.get('variant') or '', n.get('variant') or '')
                 and catlog.same_quote(o, n)]
        if len(cands) > 1:
            same_sub = [o for o in cands if norm(o.get('substrate')) == norm(n.get('substrate'))]
            cands = same_sub if len(same_sub) == 1 else cands
        if len(cands) > 1:
            same_enz = [o for o in cands if enz(o) == enz(n)]
            cands = same_enz if len(same_enz) == 1 else cands
        if len(cands) == 1:
            o = cands[0]; pool[key(n)].remove(o); pairs.append((fname, n, o))
        elif len(cands) > 1:
            ambiguous.append((fname, n, cands))
        else:
            unmatched.append((fname, n))
relabels = [p for p in pairs if norm(p[1].get('substrate')) != norm(p[2].get('substrate'))]
pairs = [p for p in pairs if p not in relabels]

# A whole table read again. When every new row of one location prints a cell an earlier row of that same location
# already holds (counts included, the limit's own < or > set aside: the censored kind carries the direction), the
# re-read stored that table a second time, however it worded the enzyme, substrate or unit. The one-to-one pairing
# above misses this when both wordings moved (2026-11-14: 20860996's 84 rows came back as 27 RELABEL + 57 unmatched,
# 38061987's 96 as 96 copies but its 60 censored rows as none), so the location is judged as a whole and its new rows
# are written out. Safe one way only: a cell the earlier rows do not hold keeps its location out of this, so a value
# the first read missed is never dropped; a label the two reads disagree on stays the paper's call (RELABEL above).
loose = lambda s: re.sub(r'^[x×]', '', re.sub(r'[\s{}()]', '', str(s or '')).replace('−', '-').replace('μ', 'µ'))
cell = lambda r: (r.get('metric'), loose(r.get('raw_value')), loose(r.get('raw_unit')), r.get('censored'),
                  re.sub(r'^[<>]', '', loose(r.get('limit'))))
repeats = []
for fname, new, old in sets:
    for loc in {r.get('location') for r in new}:
        n_loc = [r for r in new if r.get('location') == loc]
        o_loc = [r for r in old if r.get('location') == loc]
        if o_loc and not (collections.Counter(map(cell, n_loc)) - collections.Counter(map(cell, o_loc))):
            repeats.append((fname, loc, n_loc, len(o_loc)))
written = {n['row_id'] for _, n, _ in pairs}
repeat_rows = [(f, loc, r) for f, loc, n_loc, _ in repeats for r in n_loc if r['row_id'] not in written]
print(f'{pmid}: {len(pairs)} copies, {len(relabels)} relabels (not written: the paper decides which label stays), '
      f'{len(ambiguous)} ambiguous, {len(unmatched)} new rows with no earlier twin'
      + (f', {len(repeat_rows)} more in {len(repeats)} whole tables read again' if repeat_rows else ''))
for fname, loc, n_loc, n_old in repeats:
    extra = len([1 for f, l, r in repeat_rows if (f, l) == (fname, loc)])
    print(f"  TABLE READ AGAIN {fname[:7]} '{loc}': {len(n_loc)} new rows, every printed cell already among the "
          f"{n_old} earlier rows of that location ({extra} written here, the rest paired above)")
for f, n, o in pairs:
    print(f"  COPY {f[:7]} {n['row_id']} = {o['row_id']} | {n.get('location')} {n.get('metric')} {n.get('raw_value')} | "
          f"{(n.get('substrate') or '')[:40]} <-> {(o.get('substrate') or '')[:40]}")
for f, n, o in relabels:
    print(f"  RELABEL {f[:7]} {n['row_id']} = {o['row_id']} | {n.get('location')} {n.get('metric')} {n.get('raw_value')} | "
          f"new '{(n.get('substrate') or '')[:40]}' vs earlier '{(o.get('substrate') or '')[:40]}'")
for f, n, c in ambiguous:
    print(f"  AMBIGUOUS {f[:7]} {n['row_id']} | {n.get('location')} {n.get('metric')} {n.get('raw_value')} | "
          f"{(n.get('substrate') or '')[:40]} vs {[x.get('substrate') for x in c]}")
if out:
    with open(out, 'w') as fh:
        for f, n, o in pairs:
            what = 'bound' if f == 'bounds.jsonl' else 'row'
            fh.write(f"{n['row_id']}\tre-read copy of accepted {what} {o['row_id']} (same location, printed cell, unit, "
                     f"variant and quote; only reworded)\n")
        for f, loc, r in repeat_rows:
            what = 'bound' if f == 'bounds.jsonl' else 'row'
            fh.write(f"{r['row_id']}\tre-read copy of an accepted {what} ('{loc}' read again: every printed cell of "
                     f"the new rows is already among the earlier rows of that location)\n")
    print('wrote', out)
