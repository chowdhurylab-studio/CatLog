#!/usr/bin/env python3
"""Regression check after any change to catlog.py, tools/ or prompts. Run `python3 catlog.py export` first.
1. Re-run the code checks on every catalog row; report rows whose verdict or stored value would change.
2. kcat/Km agreement within tolerance for every complete measurement.
3. The final export: every value equals its catalog rows' converted value, units are the catalog units, values are
   finite and positive, measurement_ids are unique, each catalog row appears in exactly one measurement, a sequence
   always has a basis, an 'unresolved' basis has no sequence, and one value per measurement slot.
Usage: python3 tools/recheck.py   (exit 1 on any problem)
"""
import json, math, re, sys, collections, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import catlog  # noqa: E402

problems = 0
rows = sorted((json.loads(l) for l in open(catlog.CATALOG) if l.strip()), key=lambda x: x['pmid'])
by_id = {r['row_id']: r for r in rows}
def row_text(pmid):
    """The texts the paper's rows were checked against: the current one plus every copy a newer filing set aside in
    texts/replaced/ (rows read from the old copy stay, and a re-read of the new copy adds nothing new: 17462992)."""
    parts = [catlog.paper_text(pmid)] if (catlog.TEXTS / f'{pmid}.txt').exists() else []
    old = sorted((catlog.TEXTS / 'replaced').glob(f'{pmid}.*.txt'), key=lambda f: f.stat().st_mtime)
    return '\n'.join(parts + [catlog.paper_only(f.read_text()) for f in old])  # without CatLog's own lines, as paper_text


texts = {}
for r in rows:
    if r['pmid'] not in texts:  # one squash per paper, not per row
        texts = {r['pmid']: catlog.squash(row_text(r['pmid']))}
    if catlog.censored_kind(r) or r.get('value') is None:  # a censored value belongs in bounds.jsonl, never here
        problems += 1; print('ROW censored or valueless row in catalog.jsonl', r['pmid'], r['row_id'], r.get('censored'), r.get('raw_value'))
        continue
    norm, why = catlog.check(r, texts[r['pmid']])
    if set(why) <= {'quote_not_in_paper', 'value_not_in_quote'} and r.get('quote_check'):  # verified on the page image
        why = []
    if why or abs((norm['value'] or 0) - (r['value'] or 0)) > 1e-9 * max(1, r['value'] or 0):
        problems += 1
        print('ROW', r['pmid'], r['row_id'], r['metric'], r['raw_value'], r['raw_unit'], r['value'], '->', norm['value'], why)
groups = catlog.measurements(rows)
noted = [g for g in groups if all(m in {r['metric'] for r in g} for m in catlog.METRICS)
         and not catlog.ratio_check({r['metric']: r for r in g})[0]]  # kept as printed and noted, not a problem (2026-10-10)
print(f'{len(noted)} measurements print a kcat/Km that differs from kcat / Km (kept as printed, noted in the export)')
# provenance (rows added since 2026-10-21): the model each agent wrote (since 2026-11-01 its transcript's models when add
# found them, 'A>B' for a switch mid-run), prompt hashes, code commit; older rows have none. Each field is counted, so one
# the agents leave empty (a model id the default model, the Sonnet retry or the lean agent type does not write) shows up
# early instead of failing silently.
stamped = [r for r in rows if any(f in r for f in catlog.STAMP)]
for r in stamped:
    if any(not isinstance(r.get(f, ''), str) for f in catlog.STAMP):
        problems += 1; print('STAMP', r['pmid'], r['row_id'], {f: r.get(f) for f in catlog.STAMP})
filled = {f: sum(1 for r in stamped if r.get(f)) for f in catlog.STAMP}
print(f"{len(stamped)} rows carry provenance stamps, filled: " + ', '.join(f'{f} {n}' for f, n in filled.items() if f != 'read_by')
      + f" ({sum(1 for r in stamped if r.get('read_by') == catlog.MISSED)} read by the verifier: missed values); "
      f"{len(rows) - len(stamped)} were added before stamping")
models = collections.Counter(r.get(f) for r in stamped for f in ('reader_model', 'verifier_model') if r.get(f))
vague = {m: n for m, n in models.items() if not all(any(c.isdigit() for c in x) for x in m.split('>'))}
if vague:  # the prompts ask for the exact model ID, not the family name
    print(f"  model names without a version (not an exact ID): {dict(sorted(vague.items(), key=lambda x: -x[1])[:5])}")
switched = sum(n for m, n in models.items() if '>' in m)
if switched:  # read from the agent's transcript at add (catlog.agent_model): a fallback its own `model` hides
    print(f"  {switched} reader or verifier stamps name an agent that switched model mid-run ('A>B')")
unsaved = {h for r in stamped for f in ('read_prompt', 'verify_prompt', 'task_prompt') if (h := r.get(f))
           and not (catlog.WORK / 'prompts' / f'{h}.md').exists()}
if unsaved:  # each stamped hash saves its text (catlog.keep_prompt); `catlog.py prompt HASH` still looks in git history
    print(f"  {len(unsaved)} prompt hashes have no saved text in work/prompts/: {sorted(unsaved)[:5]}")
# reconstructed stamps (tools/provenance_backfill.py, sources/provenance_backfill.tsv) for rows added before stamping,
# from the agents' transcripts, the work files and git: counted per field and checked for form; a row's own stamp always
# wins (a line for a stamped row is ignored), and lines for rows no longer in the catalog (dropped since) are stale.
backfill = catlog.backfill_stamps()
older = [r for r in rows if not any(f in r for f in catlog.STAMP)]
rebuilt = [(r, dict(zip(catlog.STAMP, backfill[r['row_id']]))) for r in older if r['row_id'] in backfill]
for r, st in rebuilt:
    bad = [f for f, ok in (('read_by', st['read_by'] in ('reader', catlog.MISSED)),
                           ('pipeline_commit', re.fullmatch(r'([0-9a-f]{12})?', st['pipeline_commit'])),
                           *((f, re.fullmatch(r'([0-9a-f]{12})?', st[f])) for f in ('read_prompt', 'verify_prompt', 'task_prompt')))
           if not ok]
    if bad:
        problems += 1; print('RECONSTRUCTED', r['pmid'], r['row_id'], {f: st[f] for f in bad})
filled = {f: sum(1 for _, st in rebuilt if st[f]) for f in catlog.STAMP if f not in ('read_by', 'task_prompt')}
print(f"{len(rebuilt)} of the {len(older)} rows added before stamping carry a reconstructed stamp, filled: "
      + ', '.join(f'{f} {n}' for f, n in filled.items())
      + f" ({sum(1 for _, st in rebuilt if st['read_by'] == catlog.MISSED)} read by the verifier: missed values); "
      f"{len(older) - len(rebuilt)} have none")
ids = {r['row_id'] for r in rows}
stale, own = sum(1 for k in backfill if k not in ids), sum(1 for r in stamped if r['row_id'] in backfill)
if stale or own:
    print(f"  backfill lines for {stale} rows no longer in the catalog and {own} rows with their own stamp (ignored)")
models = collections.Counter(st[f] for _, st in rebuilt for f in ('reader_model', 'verifier_model') if st[f])
vague = {m: n for m, n in models.items() if not all(any(c.isdigit() for c in x) for x in m.split('>'))}
if vague:  # 'A>B': an agent that switched model mid-run (a fallback), every model in order
    print(f"  reconstructed model names without a version (not an exact ID): {dict(sorted(vague.items(), key=lambda x: -x[1])[:5])}")
switched = sum(n for m, n in models.items() if '>' in m)
if switched:
    print(f"  {switched} reconstructed reader or verifier stamps name an agent that switched model mid-run ('A>B')")
unsaved = {h for _, st in rebuilt for f in ('read_prompt', 'verify_prompt') if (h := st[f]) and not any(
    (d / f'{h}.md').exists() for d in (ROOT / 'sources' / 'prompt_versions', catlog.WORK / 'prompts'))}
if unsaved:  # tools/provenance_backfill.py saves each hash's text in sources/prompt_versions/
    problems += len(unsaved); print(f"RECONSTRUCTED {len(unsaved)} prompt hashes have no saved text: {sorted(unsaved)[:5]}")
slots = collections.Counter(catlog.slot(r) for r in rows)
for k, n in slots.items():
    if n > 1:
        problems += 1; print('SLOT', k, n, 'values in one measurement slot')
# censored values (bounds.jsonl, 2026-10-24: a printed bound or "not detected"): re-checked like values, kept out of the
# numeric catalog, one per slot, never in a slot that holds a value, ids unique across both files
bounds = [json.loads(l) for l in open(catlog.BOUNDS) if l.strip()] if catlog.BOUNDS.exists() else []
for b in sorted(bounds, key=lambda x: x['pmid']):
    if b['pmid'] not in texts:
        texts = {b['pmid']: catlog.squash(row_text(b['pmid']))}
    norm, why = catlog.check(b, texts[b['pmid']])
    if set(why) <= {'quote_not_in_paper', 'marker_not_in_quote', 'value_not_in_quote'} and b.get('quote_check'):
        why = []
    if why or b.get('censored') not in ('<', '>', 'not_detected') or b.get('value') is not None or \
            norm.get('censored') != b.get('censored') or norm.get('bound') != b.get('bound') or norm.get('unit') != b.get('unit'):
        problems += 1
        print('BOUND', b['pmid'], b['row_id'], b['metric'], b.get('censored'), b.get('raw_value'), b.get('bound'), '->',
              norm.get('censored'), norm.get('bound'), why)
    if b.get('bound') is not None and not (math.isfinite(b['bound']) and b['bound'] > 0):
        problems += 1; print('BOUND', b['pmid'], b['row_id'], 'bound is not a finite positive number', b['bound'])
bslots = collections.Counter(catlog.slot(b) for b in bounds)
for k, n in bslots.items():
    if n > 1:
        problems += 1; print('BOUND SLOT', k, n, 'censored values in one measurement slot')
both = set(bslots) & set(slots)
if both:
    problems += len(both); print('BOUND SLOT', len(both), 'slots hold both a value and a censored value, e.g.', sorted(both)[:3])
shared_ids = {b['row_id'] for b in bounds} & set(by_id)
if shared_ids or len({b['row_id'] for b in bounds}) != len(bounds):
    problems += 1; print('BOUND row ids not unique across catalog.jsonl and bounds.jsonl', sorted(shared_ids)[:3])
if bounds:
    kinds = collections.Counter(b['censored'] for b in bounds)
    print(f"{len(bounds)} censored values (bounds.jsonl) from {len({b['pmid'] for b in bounds})} papers: "
          + ', '.join(f'{k} {n}' for k, n in sorted(kinds.items())) + f"; {sum(1 for b in bounds if b.get('bound') is not None)} with a limit in catalog units")
wide_p = ROOT / 'catlog_wide.jsonl'
if wide_p.exists():
    W = [json.loads(l) for l in open(wide_p)]
    t_wide = time.strftime('%Y-%m-%d %H:%M', time.localtime(wide_p.stat().st_mtime))
    dropped_since = {r['row_id'] for r in map(json.loads, filter(str.strip, open(catlog.REJECTED)))
                     if (r.get('dropped') or '') >= t_wide}  # dropped after the last export: gone from it at the next one
    unit = {'kcat': ('kcat', 's^(-1)'), 'Km': ('km', 'mM'), 'kcat/Km': ('kcat_over_km', 's^(-1)*mM^(-1)'),
            # printed over a mass concentration: their own columns (units.MASS_UNIT), never the mM ones
            ('Km', 'mg/mL'): ('km_mg_per_ml', 'mg/mL'), ('kcat/Km', 'mL mg^-1 s^-1'): ('kcat_over_km_ml_per_mg_s', 'mL*mg^(-1)*s^(-1)')}
    catalog_unit = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}
    seen = collections.Counter()
    bf_p = ROOT / 'sources' / 'provenance_backfill.tsv'
    stale_bf = bf_p.exists() and bf_p.stat().st_mtime > wide_p.stat().st_mtime
    if stale_bf:  # the export merged an older backfill: one problem, not one per value
        problems += 1; print('EXPORT sources/provenance_backfill.tsv is newer than the export: run python3 catlog.py export')
    for w in W:
        for rid in w['row_ids']:
            seen[rid] += 1
            r = by_id.get(rid)
            if r is None:
                if rid not in dropped_since:
                    problems += 1; print('EXPORT', w['measurement_id'], 'row not in catalog', rid)
                continue
            if r.get('unit') != catalog_unit[r['metric']] and (r['metric'], r.get('unit')) not in unit:
                problems += 1; print('UNIT', r['pmid'], rid, r['metric'], r.get('unit'), 'is not a catalog unit')
                continue
            if any(f in r for f in catlog.STAMP) and ((w.get('provenance') or {}).get(r['metric']) or {}) != \
                    {f: r.get(f, '') for f in catlog.STAMP}:
                problems += 1; print('EXPORT', w['measurement_id'], r['metric'], 'provenance is not the row\'s stamp', rid)
            elif not stale_bf and not any(f in r for f in catlog.STAMP) and (w.get('provenance') or {}).get(r['metric']) != (
                    {**dict(zip(catlog.STAMP, backfill[rid])), 'how': catlog.RECONSTRUCTED} if rid in backfill else None):
                problems += 1; print('EXPORT', w['measurement_id'], r['metric'], 'provenance is not the row\'s reconstructed stamp', rid)
            field, u = unit.get((r['metric'], r.get('unit'))) or unit[r['metric']]
            v = w.get(field)
            if v is None or not math.isfinite(v) or v <= 0 or abs(v - r['value']) > 1e-9 * max(1, r['value']) or w.get(field + '_unit') != u:
                problems += 1; print('EXPORT', w['measurement_id'], r['metric'], 'export', v, w.get(field + '_unit'), 'vs row', r['value'])
        if w.get('kcat_over_km') is not None and not w.get('kcat_over_km_source'):
            problems += 1; print('EXPORT', w['measurement_id'], 'kcat/Km without printed/derived label')
        if (w.get('kcat_over_km') or 0) > catlog.LIMITS['kcat/Km'] and not str(w.get('kcat_over_km_source')).endswith('above the physical limit'):
            problems += 1; print('EXPORT', w['measurement_id'], 'kcat/Km above the physical limit without its flag', w.get('kcat_over_km_source'))
        for err, field in (('kcat_err', 'kcat'), ('km_err', 'km'), ('kcat_over_km_err', 'kcat_over_km')):  # the printed ±
            e = w.get(err)
            if e is not None and (w.get(field) is None or not math.isfinite(e) or e < 0
                                  or (field == 'kcat_over_km' and w.get('kcat_over_km_source') != 'printed')):
                problems += 1; print('EXPORT', w['measurement_id'], err, e, 'without a printed', field, 'or not a finite error')
        if w.get('taxon_id') and not str(w['taxon_id']).isdigit():
            problems += 1; print('EXPORT', w['measurement_id'], 'taxon_id is not a number', w['taxon_id'])
        if w.get('substrate_inchikey') and not re.fullmatch(r'[A-Z]{14}-[A-Z]{10}-[A-Z]', w['substrate_inchikey']):
            problems += 1; print('EXPORT', w['measurement_id'], 'substrate_inchikey is not an InChIKey', w['substrate_inchikey'])
        if w.get('organism_source', '').startswith('UniProt') and not w.get('uniprot_id'):
            problems += 1; print('EXPORT', w['measurement_id'], 'organism from UniProt without an accession')
        if w.get('sequence') and not w.get('sequence_basis'):
            problems += 1; print('EXPORT', w['measurement_id'], 'sequence without a basis')
        if str(w.get('sequence_basis', '')).startswith('unresolved') and w.get('sequence'):
            problems += 1; print('EXPORT', w['measurement_id'], 'sequence present although basis is unresolved')
    dup_mid = [k for k, n in collections.Counter(w['measurement_id'] for w in W).items() if n > 1]
    later = {rid for rid, r in by_id.items() if (r.get('added') or '') >= t_wide}  # added after the last export
    missing = [rid for rid in by_id if seen[rid] != 1 and rid not in later]
    if later or dropped_since:
        print(f'{len(later)} rows added and {len(dropped_since)} dropped since the last export (checked at the next export)')
    fast = [w['measurement_id'] for w in W if (w.get('kcat_over_km') or 0) > 1e6]  # above ~1e9 M^-1 s^-1: worth a look, not a rule
    if fast:
        # each value at the ceiling gets a review line (sources/implausible_as_printed.tsv, catlog.implausible): reported,
        # never a problem, so a new read at the ceiling does not stop the loop (CLAUDE.md: don't build gates)
        seen = {w['measurement_id'] for w in W if (w.get('kcat_over_km') or 0) > 1e6 and w.get('kcat_over_km_flag')}
        todo = [x for x in fast if x not in seen]
        catlog.implausible([])  # loads the file
        applied = {r for w in W if w.get('kcat_over_km_flag') for e in (w.get('evidence') or {}).values() for r in [e.get('row_id')]}
        stale = sorted(set(catlog._IMPLAUSIBLE or {}) - applied)
        print(f'{len(fast)} measurements with kcat/Km above 1e6 mM^-1 s^-1 (diffusion limit; informational): {len(seen)} '
              f'carry a review line (sources/implausible_as_printed.tsv), {len(todo)} not reviewed yet' + (f', e.g. {todo[:3]}' if todo else '')
              + (f'; {len(stale)} review lines match no value at the ceiling now (a value corrected or dropped since)' if stale else ''))
    # censored values in the export: each in catlog_bounds.jsonl once, and in a record's *_bound column only when it
    # joined that record (bound_row_ids); never in a numeric column (those come from row_ids, checked above)
    bounds_p = ROOT / 'catlog_bounds.jsonl'
    if bounds or bounds_p.exists():
        B = [json.loads(l) for l in open(bounds_p)] if bounds_p.exists() else []
        made = {b['row_id'] for b in bounds if (b.get('added') or '') < t_wide}
        exported = collections.Counter(x['row_id'] for x in B)
        lost = [r for r in made if exported[r] != 1]
        extra = [r for r in exported if r not in {b['row_id'] for b in bounds} and r not in dropped_since]
        if lost or extra:
            problems += len(lost) + len(extra); print('EXPORT censored values not exported exactly once', lost[:3], 'or no longer in bounds.jsonl', extra[:3])
        mids = {w['measurement_id']: w for w in W}
        col = {'kcat': 'kcat_bound', 'Km': 'km_bound', 'kcat/Km': 'kcat_over_km_bound'}
        for x in B:
            w = mids.get(x.get('measurement_id')) if x.get('measurement_id') else None
            if x.get('measurement_id') and (w is None or x['row_id'] not in (w.get('bound_row_ids') or []) or not w.get(col[x['metric']])):
                problems += 1; print('EXPORT censored value', x['row_id'], 'names record', x.get('measurement_id'), 'which does not carry it')
        for w in W:  # a kcat/Km the paper prints only as a bound is never calculated from kcat ÷ Km beside it
            if w.get('kcat_over_km_bound') and str(w.get('kcat_over_km_source') or '').startswith('derived'):
                problems += 1; print('EXPORT', w['measurement_id'], 'derived kcat/Km beside a printed bound', w['kcat_over_km_bound'])
        carried = sum(len(w.get('bound_row_ids') or []) for w in W)
        if carried != sum(1 for x in B if x.get('measurement_id')):
            problems += 1; print('EXPORT records carry', carried, 'censored values, catlog_bounds.jsonl joins', sum(1 for x in B if x.get('measurement_id')))
        print(f"{len(B)} censored values exported (catlog_bounds.jsonl), {sum(1 for x in B if x.get('measurement_id'))} beside a record's values")
    problems += len(dup_mid) + len(missing)
    if dup_mid: print('EXPORT duplicate measurement_ids', dup_mid[:5])
    if missing: print('EXPORT rows not in exactly one measurement', missing[:5])
    print(f'{len(W)} exported measurements checked')
else:
    print('no catlog_wide.jsonl: run python3 catlog.py export first')
# re-read duplicates (reported, never dropped here): a re-read that worded the variant or substrate differently
# ('phosphate' vs 'Pi', 'Ile' vs 'Ileu') adds the same value again. A later read's row pairs with an earlier read's row
# when exactly one earlier row of that printed cell has an overlapping quote that prints the number once (so the quote
# pins one value), with the same unit, value, pH and temperature. Rows of one read are never paired.
import bisect, re  # noqa: E402
rereads = collections.defaultdict(list)
for f in catlog.events():
    if f[2] in ('reread', 'add'):  # every add is a read: a supplement or another pass reads a paper again with no reread line
        rereads[f[1]].append(f[0])
def once(r):
    """The quote prints this row's number exactly once AND says more than the number: a quote that is only the cell
    ('0.032', where a mangled table layer left the reader nothing else) contains every other row's bare-number quote,
    so it pairs two different variants that simply print the same number (19501264 Table 2: 1st B6 and 2nd C2 both
    0.032, both printed). Such a quote is no evidence that two rows are one measurement."""
    n = catlog.numbers(r.get('raw_value', ''))
    q = catlog.clean(r.get('quote', '')).replace(',', '')
    if not n or len(re.findall(r'(?<![\d.])' + re.escape(n[0]) + r'(?!\d)', q)) != 1:
        return False
    for x in n:  # what the quote says beyond the cell itself (its numbers, ±, a footnote mark)
        q = q.replace(x, '', 1)
    return bool(re.sub(r'[\s|±+*ab()\[\]-]', '', q))
def same_cond(a, b):
    return all(not (catlog.isnum(a.get(k)) and catlog.isnum(b.get(k))) or float(a[k]) == float(b[k]) for k in ('pH', 'temperature_C'))
pairs = []
cells = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    if r['pmid'] in rereads:
        times = sorted(rereads[r['pmid']])
        cells[catlog.printed_cell(r)][bisect.bisect_left(times, (r.get('added') or '')[:16])].append(r)
for reads in cells.values():
    if len(reads) > 1:
        idx = sorted(reads)
        first = [a for a in reads[idx[0]] if once(a)]
        for j in idx[1:]:
            for b in reads[j]:
                m = [a for a in first if once(b) and catlog.same_quote(b, a)
                     and a.get('unit') == b.get('unit') and catlog.close(a['value'], b['value']) and same_cond(a, b)]
                if len(m) == 1:
                    pairs.append((b, m[0], j))
# one-to-one: two rows of one re-read that pair with the same earlier row are one printed number given to two
# measurements (a bisubstrate table row's kcat, stored for each substrate): neither is reported
claims = collections.Counter((a['row_id'], j) for b, a, j in pairs)
pairs = [(b, a) for b, a, j in pairs if claims[(a['row_id'], j)] == 1]
with open(catlog.WORK / 're_read_duplicates.tsv', 'w') as fh:  # rewritten every run, empty when there are none
    fh.write('drop_id\tkept_id\tpmid\tmetric\traw_value\tdrop_variant\tkept_variant\tdrop_substrate\tkept_substrate\n')
    fh.writelines('\t'.join([b['row_id'], a['row_id'], b['pmid'], b['metric'], b.get('raw_value', ''), b.get('variant', '')[:40],
                             a.get('variant', '')[:40], b.get('substrate', '')[:40], a.get('substrate', '')[:40]]) + '\n' for b, a in pairs)
if pairs:
    print(f'{len(pairs)} likely re-read duplicates (work/re_read_duplicates.tsv); check a few, then '
          f'`catlog.py drop <drop_id> "re-read duplicate of <kept_id>"`')
print(f'{len(rows)} rows, {len(groups)} measurements: {problems} problem(s)')
sys.exit(1 if problems else 0)
