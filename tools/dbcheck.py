"""Paper checks of database differences, inside the reading loop (the user, 2026-10-14: automatic, "not other chat's
headache").

  catlog.py dbdiff PMID...       compare these papers' values with the databases (dbcompare.compare, the export's own
                                 comparison, run on these papers alone) and write work/dbcheck_<PMID>.task.json for every
                                 value whose database_check status is `differs` by 1.5x or more (the site's "cause not
                                 yet known", an exact factor nobody checked included) and that
                                 sources/database_corrections.tsv does not already decide; prints the PMIDs that need a check
  catlog.py dbdiff --all         the same for every paper the last export shows a difference for (the backlog)
  catlog.py dbdiff ... --small   also differences under 1.5x (the site shows both numbers and does not call them unresolved)
  catlog.py dbdiff ... --reask   also values a recorded correction already decided, so a named paper's verdict can be
                                 asked again when its cause or verdict looks wrong (the task file carries the earlier
                                 verdict as `recorded_before`, and the agent's new line supersedes it by date: a
                                 verdict is never edited by hand). 19211556 on 2026-10-23: 8 rows recorded
                                 `unit_not_converted` where CatLog and BRENDA differ by 1e6, not 1000.
  catlog.py dbdiff --pending     the PMIDs whose task file waits for an agent (no verdict file yet, no claim)
  catlog.py dbdiff --pending N   up to N of them, claimed for this batch (work/dbcheck_<PMID>.claim): another chat's
                                 --pending skips a claimed paper for CLAIM_HOURS, so one paper never gets two agents and
                                 the backlog is taken N papers per batch, not all at once
  catlog.py dbcheck-record [FILE...]   check the verdicts agents wrote (work/dbcheck_<PMID>.json, prompts/dbcheck.md;
                                 every such file in work/ when none is named) and append the usable ones to
                                 sources/database_corrections.tsv (recorded_by paper_check); a paper it leaves with a
                                 value unanswered or a verdict it cannot use is asked again (dbdiff writes its task
                                 file for the next batch) until it has had ASK_MAX checks. audit-record does the same
                                 for a paper whose value a check called wrong and an audit then kept

One agent per task file (the `catlog-batch` workflow's dbcheck step, or the saved workflow `catlog-dbcheck`) reads the
paper and writes a verdict per difference: corrected (the database is wrong: one cause code and a facts-only evidence
sentence), different_measurement, catlog_wrong or ambiguous. Agents never change a value. A catlog_wrong verdict is
recorded (`catlog.py status` lists it under "Audit these") and its row goes to work/audit_priority.txt, which
`catlog.py sample` takes first, so the next /audit re-checks it against the paper; an audit keep on or after the
verdict's date makes the value a difference to check again. A task file names database numbers, so it is never a
reader's input, nor once recorded and moved to work/old/ (prompts/read.md forbids work/dbcheck_* and
work/old/dbcheck_*; human_review.blind_check flags any reader that opens one), and
these agents are not readers: their task names prompts/dbcheck.md. Databases are never evidence for a value
(CLAUDE.md): this runs after `add`, on verified rows.
"""
import contextlib, csv, fcntl, hashlib, io, json, math, os, re, shutil, sys, tempfile, time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dbcompare as DC  # noqa: E402

TASK = 'dbcheck_{}.task.json'          # in work/: written by dbdiff, read by the agent
CLAIM = 'dbcheck_{}.claim'             # in work/: `dbdiff --pending N` took the task for a batch (when, which process)
CLAIM_HOURS = 3                        # a claim older than this is free again (its batch died or stopped)
VERDICT = 'dbcheck_{}.json'            # in work/: written by the agent, read by dbcheck-record
VERDICT_NAME = re.compile(r'dbcheck_(\d{1,9}|NP[0-9A-F]{8})\.json')
PRIORITY = 'audit_priority.txt'        # in work/: rows /audit samples first (catlog.py sample)
PRIORITY_COLS = ('row_id', 'pmid', 'date', 'why')
EVIDENCE_MAX = 240
ASK_MAX = 2                            # paper checks the loop asks for one paper by itself (its `dbcheck` lines in
                                       # log.tsv); what is still open after that waits for the backlog (`dbdiff --all`)
VALUE_FIELDS = ('row_id', 'metric', 'raw_value', 'raw_unit', 'unit_for_conversion', 'value', 'unit', 'location', 'quote',
                'enzyme', 'organism', 'variant', 'substrate', 'substrate_full_name', 'cosubstrate', 'pH',
                'temperature_C', 'conditions', 'metric_note', 'construct')
CODE_NOTES = ('relation', 'closure', 'pairing')  # dbcompare's reading of the difference: hints the agent checks


def catalog_rows(C):
    """catalog.jsonl as rows; a last line another chat is still writing (no newline yet) is left out."""
    out = []
    for line in open(C.CATALOG):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                if line.endswith('\n'):
                    raise
    return out


def export_rows(C, cat):
    """The export's measurements of these catalog rows, built as `catlog.py export` builds them before it calls
    dbcompare.compare() (the same measurements(), wide() and measurement ids; EC, audit marks and DOI are left out:
    compare() does not read them), so compare() on a few papers gives each value the database_check the next full
    export gives it. Returns (measurements, the structures cache)."""
    from enrich import Cache
    from sequences import split_variant
    ids, sm = Cache(C.ROOT / 'enrich' / 'protein.json'), Cache(C.ROOT / 'enrich' / 'structures.json')
    groups = C.measurements(cat)
    muts = {}
    for rows in groups:
        ref = ids.get(C.ident_key(rows[0]), {}).get('seq_ref')
        if ref:
            muts.setdefault((rows[0]['pmid'], ref), []).extend(split_variant(rows[0].get('variant'))[1])
    pmids, db = {r['pmid'] for r in cat}, {}
    dv = C.ROOT / 'sources' / 'db_values.tsv'
    if dv.exists():
        for line in open(dv):
            f = line.rstrip('\n').split('\t')
            if len(f) > 4 and f[1] in pmids:
                db.setdefault((f[1], f[3]), []).append((f[0], float(f[4])))
    forms = {}
    for rows in groups:
        if C.natural_form(rows[0]):
            forms.setdefault(rows[0]['pmid'], {})[rows[0]['variant']] = ids.get(C.ident_key(rows[0]), {})
    out = [C.wide(rows, ids, sm, len(rows) > 1, muts, db, forms) for rows in groups]
    seen = Counter(w['measurement_id'] for w in out)  # the export's two passes for measurement ids that clash
    for w in out:
        if seen[w['measurement_id']] > 1:
            cells = sorted(f"{k}={v.get('raw_value', '')}" for k, v in w['evidence'].items())
            w['measurement_id'] = hashlib.sha1('|'.join([w['measurement_id'], *cells]).encode()).hexdigest()[:16]
    seen = Counter(w['measurement_id'] for w in out)
    for w in out:
        if seen[w['measurement_id']] > 1:
            w['measurement_id'] = hashlib.sha1('|'.join([w['measurement_id'], *sorted(w['row_ids'])]).encode()).hexdigest()[:16]
    return out, sm


def database_table(root, pmids):
    """pmid -> its rows of sources/db_values.tsv with a positive number: src, metric, value, vstr (as listed), substrate,
    organism, ec, comment."""
    out = defaultdict(list)
    dv = Path(root) / 'sources' / 'db_values.tsv'
    if not dv.exists() or not pmids:
        return out
    with open(dv) as fh:
        next(fh)
        for line in fh:
            f = line.rstrip('\n').split('\t')
            if len(f) >= 8 and f[1] in pmids and f[0] in DC.SOURCES and (DC.num(f[4]) or 0) > 0:
                out[f[1]].append({'src': f[0], 'metric': f[3], 'value': DC.num(f[4]), 'vstr': f[4], 'substrate': f[5].strip(),
                                  'organism': f[6].strip(), 'ec': f[2], 'comment': f[7]})
    return out


def wide_pmids(C, small=False):
    """The papers the last export (catlog_wide.jsonl) shows a value with database_check status differs for (by 1.5x or
    more unless small)."""
    p = C.ROOT / 'catlog_wide.jsonl'
    if not p.exists():
        sys.exit('dbdiff --all: no catlog_wide.jsonl; run `python3 catlog.py export` first')
    out, compared = set(), False
    with open(p) as fh:
        for line in fh:
            if '"database_check"' not in line:
                continue
            compared = True
            if '"differs"' in line:
                w = json.loads(line)
                if any(c.get('status') == 'differs' and (small or c.get('relation') != 'under_1.5x')
                       for c in (w.get('database_check') or {}).values()):
                    out.add(str(w['pubmed_id']))
    if not compared:
        sys.exit('dbdiff --all: catlog_wide.jsonl has no database comparison (database_check); run `python3 catlog.py '
                 'export` with tools/dbcompare.py installed first')
    return out


def pending(C):
    """(PMIDs whose task file waits for an agent and no batch claimed it, PMIDs whose verdict file waits for
    dbcheck-record, PMIDs a batch claimed less than CLAIM_HOURS ago). A paper of the method paper's test set
    (C.locked()) never waits for an agent: its task file stays on disk, unclaimed."""
    tasks = {p.name[len('dbcheck_'):-len('.task.json')] for p in C.WORK.glob('dbcheck_*.task.json')}
    done = {m.group(1) for p in C.WORK.glob('dbcheck_*.json') if (m := VERDICT_NAME.fullmatch(p.name))}
    held = {p for p in tasks - done if _claimed(C, p)}
    return sorted(tasks - done - held - C.locked(), key=_order), sorted(done, key=_order), sorted(held, key=_order)


def _claimed(C, pmid):
    try:
        return time.time() - (C.WORK / CLAIM.format(pmid)).stat().st_mtime < CLAIM_HOURS * 3600
    except OSError:
        return False


def claim(C, n):
    """`dbdiff --pending N`: up to n waiting papers, each claimed for this batch (work/dbcheck_<PMID>.claim), under a
    lock so two chats asking at once never get the same paper."""
    with open(C.WORK / 'dbcheck.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            take = pending(C)[0][:n]
            for p in take:
                (C.WORK / CLAIM.format(p)).write_text(f'{C.now()}\t{os.getpid()}\n')
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)
    return take


def unclaim(C, pmid):
    (C.WORK / CLAIM.format(pmid)).unlink(missing_ok=True)


def _order(p):
    return (not p.isdigit(), int(p) if p.isdigit() else 0, p)


def _write(path, data):
    tmp = path.with_name(f'{path.name}.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def dbdiff(C, args):
    """`catlog.py dbdiff PMID... | --all | --pending [N]` (module docstring)."""
    if '--pending' in args:
        i = args.index('--pending')
        n = args[i + 1] if i + 1 < len(args) else ''
        if n and not n.isdigit():
            sys.exit('usage: catlog.py dbdiff --pending [N]  (N: how many papers this batch takes and claims)')
        wait, rec, held = pending(C)
        if rec:
            print(f'verdict files waiting for `catlog.py dbcheck-record`: {" ".join(rec)}')
        if held:
            print(f'claimed by a running batch (free again {CLAIM_HOURS} h after the claim): {" ".join(held)}')
        if n:
            take = claim(C, int(n))
            print(f'papers to check: {" ".join(take)}' if take else 'papers to check: none')
            if len(wait) > len(take):
                print(f'({len(wait) - len(take)} more wait for later batches)')
            return take
        print(f'papers waiting for a check: {" ".join(wait)}' if wait else 'papers waiting for a check: none')
        print('(`dbdiff --pending N` takes N of them for a batch and claims them)')
        return wait
    small, reask_too = '--small' in args, '--reask' in args
    pmids = {C.paper_id(a) for a in args if a not in ('--all', '--small', '--reask')}
    if '--all' in args:
        pmids |= wide_pmids(C, small)
    if not pmids:
        sys.exit('usage: catlog.py dbdiff PMID... [--reask] | --all [--small] | --pending [N]')
    if reask_too and '--all' in args:
        sys.exit('--reask asks again for named papers only (it would otherwise reopen every recorded correction)')
    held = pmids & C.locked()  # the method paper's test set: no task file, never in "papers to check"
    if held:
        pmids -= held
        print(f'left out {len(held)} held-out papers (the method paper\'s test set): {" ".join(sorted(held, key=_order)[:10])}',
              file=sys.stderr)
        if not pmids:
            return []
    t0 = time.time()
    cat = [r for r in catalog_rows(C) if r['pmid'] in pmids]
    out, sm = export_rows(C, cat)
    from dbcompare import compare
    compare(out, cat, C.ROOT, sm)  # sets database_check on each measurement, as the export does
    rows_of = {r['row_id']: r for r in cat}
    rec = DC.recorded(C.ROOT, [])  # the current row per value and database (dates of catlog_wrong verdicts)
    marks = C.audit_marks()
    waiting = audit_first(C)  # a value a check called wrong waits for its audit, whether or not its verdict was recorded
    dbt = database_table(C.ROOT, {r['pmid'] for r in cat})
    tasks, again = defaultdict(list), []
    for w in out:
        for m, e in (w.get('database_check') or {}).items():
            # --reask: a value a recorded correction settled (status 'corrected') is asked again for named papers
            if e.get('status') not in ('differs', *(('corrected',) if reask_too else ())) \
                    or (e.get('relation') == 'under_1.5x' and not small):
                continue  # under 1.5x the site names both numbers and calls nothing unresolved (--small: these too)
            rid = (w.get('evidence') or {}).get(m, {}).get('row_id')
            r = rows_of.get(rid)
            if r is None or rid in waiting:
                continue
            if e.get('recorded') == 'ambiguous':
                continue  # checked: the paper cannot settle it
            if e.get('recorded') == 'catlog_wrong':
                when = max((x['date'] for x in rec.get(rid, []) if x['verdict'] == 'catlog_wrong'), default='')
                if not (rid in marks and marks[rid][0] >= when):
                    continue  # waits for its audit (status: "Audit these"; sample takes it first)
                again.append(rid)  # an audit kept CatLog's value after the verdict: the difference is open again
            numbers = {s: e['database_value'] for s in (e.get('sources') or []) if e.get('database_value')}
            for s, v in (e.get('other_values') or {}).items():
                numbers.setdefault(s, v)
            listed = [d for d in dbt.get(r['pmid'], []) if d['metric'] == m and d['src'] in numbers
                      and DC.same_value(d['value'], numbers[d['src']])]
            if not listed:  # no source named: every database row with the number the comparison named
                listed = [d for d in dbt.get(r['pmid'], []) if d['metric'] == m and DC.same_value(d['value'], e.get('database_value'))]
            v = DC.num(r.get('value'))
            value = {k: r.get(k) for k in VALUE_FIELDS if r.get(k) not in (None, '')}
            value['unit'] = DC.UNIT_PLAIN[m]
            value['measurement'] = {k: f"{ev.get('raw_value', '')} {ev.get('raw_unit', '')}".strip()
                                    for k, ev in (w.get('evidence') or {}).items() if k != m}
            value['code_notes'] = {k: e[k] for k in CODE_NOTES if e.get(k)}
            if e.get('other_measurement'):
                value['code_notes']['other_measurement'] = e['other_measurement']
            before = [{k: x.get(k) for k in ('database', 'database_value', 'verdict', 'cause', 'evidence', 'date')}
                      for x in rec.get(rid, [])]
            if before:
                value['recorded_before'] = before
            value['databases'] = [{'database': d['src'], 'number': d['vstr'], 'unit': DC.UNIT_PLAIN[m],
                                   'times_catlog': float(f"{d['value'] / v:.4g}") if v else None,
                                   'substrate': d['substrate'], 'organism': d['organism'], 'ec': d['ec'],
                                   'comment': d['comment'][:400]} for d in listed]
            tasks[r['pmid']].append(value)
    papers = {r['pmid']: r for r in csv.DictReader(open(C.PAPERS), delimiter='\t') if r['pmid'] in pmids}
    for pmid in sorted(pmids, key=_order):
        path = C.WORK / TASK.format(pmid)
        if not tasks.get(pmid):
            if path.exists():
                path.unlink()  # a task written before the difference was decided (regenerable)
                unclaim(C, pmid)
            continue
        text = C.TEXTS / f'{pmid}.txt'
        first = text.open(errors='replace').readline().strip() if text.exists() else ''
        supp = C.TEXTS / f'{pmid}.supp.txt'
        _write(path, {'pmid': pmid, 'title': papers.get(pmid, {}).get('title', ''), 'made': C.now(),
                      'instructions': 'prompts/dbcheck.md', 'text': f'texts/{pmid}.txt',
                      'supplement': f'texts/{pmid}.supp.txt' if supp.exists() else '',
                      'original_file': papers.get(pmid, {}).get('text_source', ''),
                      'glyph_warning': first if first.startswith('GLYPH WARNING') else '',
                      'values': sorted(tasks[pmid], key=lambda x: (DC.METRIC_ORDER.index(x['metric']), x.get('location', ''), x['row_id']))})
        n = Counter(x['metric'] for x in tasks[pmid])
        print(f"{pmid}: {len(tasks[pmid])} values differ from a database ({', '.join(f'{k} {n[k]}' for k in DC.METRIC_ORDER if n[k])})"
              f" -> work/{TASK.format(pmid)}")
    if again:
        print(f'{len(again)} values a paper check had called wrong in CatLog and an audit then kept are checked again: {" ".join(again[:10])}')
    todo = sorted(tasks, key=_order)
    print(f'papers to check: {" ".join(todo)}' if todo else 'papers to check: none (no database difference waits for a check)')
    print(f'({sum(len(v) for v in tasks.values())} values in {len(todo)} papers; compared {len(cat)} values of {len(pmids)} papers '
          f'in {time.time() - t0:.0f} s)', file=sys.stderr)
    return todo


# ---------------------------------------------------------------- recording the verdicts
def _clean(s):
    return ' '.join(str(s if s is not None else '').split())


def _check(v, pmid, rows_of, paper_of):
    """(the database_corrections.tsv row, '') for one verdict of a paper's file, or (None, why). rows_of: the paper's
    catalog rows by row_id; paper_of: every catalog row_id's paper."""
    if not isinstance(v, dict):
        return None, 'not an object'
    rid = _clean(v.get('row_id'))
    x = rows_of.get(rid)
    if x is None:
        return None, (f'row_id is a value of paper {paper_of[rid]}, not {pmid}' if rid in paper_of else 'row_id not in the catalog')
    metric = DC.METRICS.get(DC._key(v.get('metric')))
    if metric != x['metric']:
        return None, f"metric {v.get('metric')!r} is not this value's ({x['metric']})"
    verdict = _verdict(v)
    if verdict not in DC.VERDICTS:
        return None, f"unknown verdict {v.get('verdict')!r}"
    cause = _clean(v.get('cause'))
    code = next((c for c in DC.CAUSES if DC._key(c) == DC._key(cause)), '')
    if verdict == 'different_measurement':
        if cause and code != 'different_measurement':
            return None, f'cause {cause!r} contradicts verdict different_measurement'
        code = 'different_measurement'
    elif verdict == 'ambiguous':
        if cause and DC._key(cause) != 'ambiguous':
            return None, f'cause {cause!r} contradicts verdict ambiguous'
        code = 'ambiguous'
    elif verdict == 'catlog_wrong':  # the codes say how a DATABASE number came about: CatLog's misread cell has none
        code = '' if code == 'different_measurement' else code  # (a free-text cause is stored as ''; the evidence says it)
    elif not code or code == 'different_measurement':
        return None, f'cause {cause!r} is not a cause code for verdict {verdict}'
    dbs = v.get('database')
    names = [t for t in re.split(r'[,;+/&]|\band\b', ', '.join(dbs) if isinstance(dbs, list) else _clean(dbs)) if t.strip()]
    canon = [DC.DB_NAMES.get(DC._key(t)) for t in names]
    if not canon or None in canon:
        return None, f'unknown database {dbs!r}'
    dval = _clean(v.get('database_value'))
    if not (DC._database_number(dval) or 0) > 0:
        return None, f'database_value {dval!r} is not a positive number'
    if not re.search(r'[A-Za-zµμ]', dval):  # a bare number: the catalog unit it is in, as the file's other rows write it
        dval = f"{dval} {DC.UNIT_PLAIN[x['metric']]}"
    ev = _clean(v.get('evidence'))
    if not ev:
        return None, 'no evidence'
    if len(ev) > EVIDENCE_MAX:
        return None, f'evidence has {len(ev)} characters (at most {EVIDENCE_MAX})'
    return {'row_id': rid, 'pmid': pmid, 'metric': x['metric'], 'database': ', '.join(dict.fromkeys(canon)),
            'database_value': dval, 'verdict': verdict, 'cause': code, 'evidence': ev, 'recorded_by': 'paper_check',
            'date': time.strftime('%Y-%m-%d')}, ''


def _verdict(v):
    return re.sub(r'[\s-]+', '_', _clean(v.get('verdict')).lower()) if isinstance(v, dict) else ''


def _usable(C, row, paper_rows, db_rows):
    """Why dbcompare.usable() would not use this one row ('' when it would): the same checks the export applies."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'sources').mkdir()
        (Path(tmp) / DC.CORRECTIONS).write_text('\t'.join(DC.CORRECTION_COLS) + '\n'
                                                + '\t'.join(row[c] for c in DC.CORRECTION_COLS) + '\n', encoding='utf-8')
        nf = C.ROOT / 'sources' / 'natural_forms.tsv'
        if nf.exists():
            os.symlink(nf, Path(tmp) / 'sources' / 'natural_forms.tsv')
        problems = []
        used = DC.usable(tmp, paper_rows, problems, db_rows)
    return '; '.join(why for _, _, why in problems) or ('' if used.get(row['row_id']) else 'not used by the comparison')


def _in_task(row, task):
    """'' when, for each database the verdict names, the task listed that database's number for this value (row_id) and
    it is the verdict's database_value (dbcompare.same_number); else why not. A verdict whose row_id was swapped with
    another value's (same metric and variant, another substrate) names a number the task listed for that other value:
    usable() checks only that the paper lists it, and the export would print it on this value's line."""
    r = {'number': DC._database_number(row['database_value']), 'figures': DC._database_figures(row['database_value'])}
    asked = defaultdict(list)
    for x in task.get('values') or []:
        if isinstance(x, dict) and x.get('row_id') == row['row_id']:
            for d in x.get('databases') or []:
                asked[d.get('database')].append(d.get('number'))
    if not asked:
        return 'not in the task: it names no database number for this value'
    for db in row['database'].split(', '):
        if not any(DC.same_number(r, DC.num(v)) for v in asked.get(db, [])):
            listed = '; '.join(f"{d} {', '.join(map(str, vs))}" for d, vs in asked.items())
            return f"not in the task: {db} {row['database_value']} is not a number it lists for this value ({listed})"
    return ''


def _expected(task):
    """(row_id, database) of every database number a task file names."""
    return {(x['row_id'], d['database']) for x in task.get('values', []) for d in x.get('databases', [])}


def _named(v):
    """(row_id, database) pairs a verdict answers, whether or not it can be used."""
    if not isinstance(v, dict):
        return set()
    dbs = v.get('database')
    names = re.split(r'[,;+/&]|\band\b', ', '.join(map(str, dbs)) if isinstance(dbs, list) else _clean(dbs))
    return {(_clean(v.get('row_id')), DC.DB_NAMES.get(DC._key(t))) for t in names if t.strip()}


def _append(tsv, rows):
    """Append rows to sources/database_corrections.tsv (created with its header), one writer at a time."""
    with open(str(tsv) + '.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            head = tsv.read_bytes()[-1:] if tsv.exists() and tsv.stat().st_size else b''
            with open(tsv, 'a', encoding='utf-8') as fh:
                if not head:
                    fh.write('\t'.join(DC.CORRECTION_COLS) + '\n')
                elif head != b'\n':
                    fh.write('\n')
                fh.writelines('\t'.join(r[c] for c in DC.CORRECTION_COLS) + '\n' for r in rows)
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def add_priority(C, rows):
    """Append (row_id, pmid, why) to work/audit_priority.txt (no database numbers: auditors read blind)."""
    p = C.WORK / PRIORITY
    new = not p.exists()
    with open(p, 'a', encoding='utf-8') as fh:
        if new:
            fh.write('\t'.join(PRIORITY_COLS) + '\n')
        for rid, pmid, why in rows:
            fh.write('\t'.join((rid, pmid, time.strftime('%Y-%m-%d'), _clean(why))) + '\n')


def audit_first(C):
    """row_id -> place in work/audit_priority.txt for rows no audit has kept or dropped on or after the day they were
    put there (catlog.py sample takes them first)."""
    p = C.WORK / PRIORITY
    if not p.exists():
        return {}
    last = {}
    for f in C.events():
        if f[2] in ('audit_keep', 'audit_drop') and len(f) > 3:
            last[f[3]] = max(last.get(f[3], ''), f[0][:10])
    out = {}
    for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'):
        rid = r.get('row_id') or ''
        if rid and rid not in out and last.get(rid, '') < (r.get('date') or ''):
            out[rid] = len(out)
    return out


def record(C, paths):
    """`catlog.py dbcheck-record [FILE...]`: each verdict of work/dbcheck_<PMID>.json checked (row_id of that paper in the
    catalog, its metric, a known verdict and cause code, a database number that database lists for the paper, evidence
    of at most 240 characters, and every check dbcompare.usable() makes at export), the usable ones appended to
    sources/database_corrections.tsv. Evidence the paper does not show (evidence_flags: a number it does not print, a
    ratio that does not hold) is listed and logged, not refused. Every catlog_wrong verdict that names a value of the
    paper also puts that value first for the next audit (work/audit_priority.txt), even when its row cannot be
    recorded: the auditor decides.
    catlog_wrong needs no cause code (the codes describe database numbers).
    One log.tsv line per paper (`dbcheck`). A recorded file and its task go to work/old/. Task files given on the
    command line (a glob of work/dbcheck_*.json matches them) are skipped."""
    paths = paths or sorted(C.WORK.glob('dbcheck_*.json'))  # none given: every verdict file in work/ (no shell glob)
    files = [Path(p) for p in paths if not str(p).endswith('.task.json')]
    if not files:
        print('dbcheck-record: no verdict files (work/dbcheck_<PMID>.json): nothing to record')
        return
    tsv = C.ROOT / DC.CORRECTIONS
    if tsv.exists() and tsv.read_bytes()[:2] in (b'\xff\xfe', b'\xfe\xff'):
        sys.exit(f'dbcheck-record: {DC.CORRECTIONS} is saved as UTF-16; save it as UTF-8 first (rows are appended as UTF-8)')
    have = set()
    if tsv.exists():
        for line in tsv.read_text(encoding='utf-8', errors='replace').splitlines()[1:]:
            have.add(tuple(line.split('\t')[:8]))
    names = {p: VERDICT_NAME.fullmatch(p.name) for p in files}
    by_paper = defaultdict(list)
    wanted = {m.group(1) for m in names.values() if m}
    paper_of = {}
    for r in catalog_rows(C):
        paper_of[r['row_id']] = r['pmid']
        if r['pmid'] in wanted:
            by_paper[r['pmid']].append(r)
    db_rows = DC.database_rows(C.ROOT, wanted)
    old, tally, left_open = C.WORK / 'old', Counter(), set()
    for p in files:
        m = names[p]
        if not m:
            print(f'{p.name}: not a verdict file (work/dbcheck_<PMID>.json); left as it is'); continue
        pmid = m.group(1)
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as e:
            print(f'{p.name}: unreadable ({e}); not recorded'); continue
        verdicts = data.get('verdicts') if isinstance(data, dict) else None
        if not isinstance(verdicts, list):
            print(f'{p.name}: no "verdicts" list; not recorded'); continue
        if str(data.get('pmid') or pmid) != pmid:
            print(f"{p.name}: says pmid {data.get('pmid')}, the file name {pmid}; not recorded"); continue
        rows_of = {r['row_id']: r for r in by_paper.get(pmid, [])}
        task_p = C.WORK / TASK.format(pmid)
        try:
            task = json.loads(task_p.read_text(encoding='utf-8')) if task_p.exists() else {}
        except (OSError, json.JSONDecodeError):
            task = {}
        n, bad, add, given, wrong, ok = Counter(), [], [], set(), {}, set()
        for v in verdicts:
            given |= _named(v)
            rid = _clean(v.get('row_id')) if isinstance(v, dict) else ''
            if _verdict(v) == 'catlog_wrong' and rid in rows_of:
                wrong.setdefault(rid, rows_of[rid])  # to the audit even when the row below cannot be used: the auditor decides
            row, why = _check(v, pmid, rows_of, paper_of)
            if row and task:
                why = _in_task(row, task)
            if row and not why:
                why = _usable(C, row, by_paper[pmid], db_rows)
            if why:
                bad.append((_clean(v.get('row_id')) if isinstance(v, dict) else '?', why)); n['not_used'] += 1
                continue
            n[row['verdict']] += 1
            ok.add((row['row_id'], row['verdict']))
            key = tuple(row[c] for c in DC.CORRECTION_COLS[:8])
            if key in have:
                n['recorded_already'] += 1
                continue
            have.add(key)
            add.append(row)
        missing = sorted(_expected(task) - given)
        if add:
            _append(tsv, add)
        flags, nums = {}, paper_numbers(C, pmid) if add else frozenset()
        asked = {x.get('row_id'): {k: v for k, v in x.items() if k not in ('row_id', 'recorded_before')}
                 for x in task.get('values') or [] if isinstance(x, dict)}
        for r in add:  # a flag for a person (recorded as written): one agent's evidence, with no second check
            x = rows_of[r['row_id']]
            f = evidence_flags(C, r['evidence'], nums, json.dumps({k: x.get(k) for k in VALUE_FIELDS[1:]}, ensure_ascii=False),
                               json.dumps(asked.get(r['row_id'], {}), ensure_ascii=False), r['database_value'])
            if f:
                flags[r['row_id']] = f
        waiting = audit_first(C)
        if any(rid not in waiting for rid in wrong):
            add_priority(C, [(rid, pmid, 'dbcheck: a paper check of a database difference found this value wrong')
                             for rid in wrong if rid not in waiting])
        # (the field is not named audit_*: cmd_sample takes any '\taudit_' in log.tsv for an audit)
        C.log(pmid, 'dbcheck', *(f'{k}={n[k]}' for k in ('corrected', 'different_measurement', 'catlog_wrong', 'ambiguous')),
              f"not_used={n['not_used']}", f'unanswered={len(missing)}', f'recorded={len(add)}',
              *([f"to_audit={','.join(wrong)}"] if wrong else []), *([f"evidence_flags={','.join(flags)}"] if flags else []))
        old.mkdir(exist_ok=True)
        stamp = int(time.time())
        shutil.move(str(p), str(old / f'{p.stem}.{stamp}.json'))
        if task_p.exists():
            shutil.move(str(task_p), str(old / f'{task_p.stem}.{stamp}.json'))
        unclaim(C, pmid)
        tally.update(n)
        if missing or bad:
            left_open.add(pmid)
        said = [f'{k.replace("_", " ")} {n[k]}' for k in
                ('corrected', 'different_measurement', 'catlog_wrong', 'ambiguous', 'recorded_already') if n[k]]
        print(f"{pmid}: {len(add)} rows added to {DC.CORRECTIONS}" + (f" ({', '.join(said)})" if said else ''))
        for rid, why in bad:
            print(f'  not used: {rid}: {why}')
        for rid, d in missing:
            print(f'  no verdict: {rid} {d}')
        for rid, x in wrong.items():
            print(f"  CatLog wrong per the paper check: {rid} {x['metric']}"
                  + ('' if (rid, 'catlog_wrong') in ok else ' (its verdict cannot be recorded: see "not used")')
                  + ": not changed; `catlog.py sample` puts it first for the next /audit")
        for r in add:
            part = next((s for s in re.split(r';\s*|(?<=\.)\s+', r['evidence']) if _inference(s)), '')
            if part and r['verdict'] == 'corrected':
                print(f"  note: {r['row_id']} evidence holds a reasoning word ('{part[:60]}'): the site leaves that part out")
        for rid, f in flags.items():
            print(f"  evidence to look at: {rid}: {'; '.join(f)} (recorded as written; log.tsv evidence_flags=)")
    if len(files) > 1:
        print('dbcheck-record: ' + (', '.join(f'{k.replace("_", " ")} {tally[k]}' for k in
                                              ('corrected', 'different_measurement', 'catlog_wrong', 'ambiguous', 'not_used')
                                              if tally[k]) or 'nothing usable'))
    reask(C, left_open, 'values left open (unanswered or not used)')


def reask(C, pmids, why):
    """Run dbdiff on papers a check or an audit left with an open database difference, so the loop asks again by
    itself: dbdiff writes a task file only for values still undecided (a value waiting for its audit is left out) and the
    next batch's `dbdiff --pending N` takes it. A paper that has had ASK_MAX checks (`dbcheck` lines in log.tsv) is
    not asked again here: `dbdiff --all` (the backlog) takes it. Returns the papers asked again."""
    pmids = set(pmids)
    if not pmids:
        return []
    tries = Counter(f[1] for f in C.events() if f[2] == 'dbcheck' and f[1] in pmids)
    go = sorted((p for p in pmids if tries[p] < ASK_MAX), key=_order)
    capped = sorted(pmids - set(go), key=_order)
    asked = []
    if go:
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):  # dbdiff's own lines ("papers to check") would read as this batch's list
                asked = dbdiff(C, go)
        except SystemExit as e:
            print(f'{why}: `dbdiff {" ".join(go)}` stopped ({e}); not asked again')
    if asked:
        print(f'{why}: asked again, task files wait for the next batch (`dbdiff --pending N`): {" ".join(asked)}')
    if capped:
        print(f'{why}: not asked again ({ASK_MAX} checks already; `dbdiff --all` takes them): {" ".join(capped)}')
    return asked


FACTORS = tuple(10.0 ** k * m for k in range(-12, 13) for m in (1, 60, 1 / 60, 3600, 1 / 3600))  # header power, unit, time
_TOKEN = re.compile(r'(?<![\w.^])(?:(\d+(?:\.\d+)?)\s*(?:[eE]|[x*]\s*10\s*\^?)\s*([+-]?\d{1,2})(?!\d)|10\s*\^\s*([+-]?\d{1,2})(?!\d)'
                    r'|(\d+(?:\.\d+)?)(?!\d))')
_W = r'(?:[A-Za-z]+(?![A-Za-z])\s*)*?'  # whole words only: '[A-Za-z]+\s*' could split a word 2^n ways (dbcheck-record hung 20 min on 33482017's evidence)
EQUATION = (re.compile(rf'#(\d+)#\s*{_W}[/÷]\s*{_W}#(\d+)#\s*{_W}=\s*{_W}#(\d+)#'),   # b / c = a
            re.compile(rf'#(\d+)#\s*{_W}=\s*{_W}#(\d+)#\s*{_W}[/÷]\s*{_W}#(\d+)#'))   # a = b / c
CHAIN = re.compile(rf'\s*{_W}=\s*{_W}#(\d+)#')                                         # ... = a2 (the same number, converted)


def _tokens(s):
    """The numbers of a text as (text as printed, value, half a unit of its last printed digit); '1.68 x 10^5' and
    '2e+07' are one number each, '10^-3' a factor. Unit exponents (s^-1, M-1) and page numbers are left out."""
    from units import clean
    s = re.sub(r'(?<=[A-Za-z])\s?(?:\^\s?-?|-)\d+', '', clean(s))
    s = re.sub(r'(?<=\d),(?=\d{3}(?!\d))', '', s)
    s = re.sub(r'\b(?:p|pp|page)\.?\s*\d+(?:\s*-\s*\d+)?', ' ', s)
    out, parts, at = [], [], 0
    for m in _TOKEN.finditer(s):
        if m.group(1):
            e = int(m.group(2)); v = float(m.group(1)) * 10.0 ** e; h = _half_unit(m.group(1)) * 10.0 ** e
        elif m.group(3):
            v = 10.0 ** int(m.group(3)); h = 0.0
        else:
            v = float(m.group(4)); h = _half_unit(m.group(4))
        parts.append(s[at:m.start()] + f'#{len(out)}#'); at = m.end()
        out.append((m.group(0), v, h))
    return out, ''.join(parts) + s[at:]


def _near(v, h, w):
    return any(abs(v - w * f) <= h + 1e-12 * abs(v) for f in FACTORS)


def paper_numbers(C, pmid):
    """Every number printed in the paper's text and supplement (catlog.printed_numbers), also with a space between
    thousands ('57 000') read as one number; empty when the paper has no text."""
    try:
        sq = C.squash(C.paper_text(pmid))
    except OSError:
        return frozenset()
    return C.printed_numbers(sq) | C.printed_numbers(re.sub(r'(?<=\d) (?=\d{3}(?!\d|\.\d))', '', sq))


def evidence_flags(C, ev, text_numbers, *known):
    """What in a verdict's evidence the paper does not show (a flag for a person, never a refusal; the 727-value run's
    second check differed on 57 evidence facts, e.g. '0.0018 = 0.28/150'):
    - a ratio written as an equation (b / c = a, a = b / c) that does not hold to a's last printed digit, up to a power
      of ten or a minute/hour factor (15 s^-1 / 38 µM = 395 mM^-1 s^-1 holds);
    - a number that is not printed in the paper (text_numbers: paper_numbers()), is not one of the known strings'
      numbers to its last printed digit (the value's own fields, the task's database numbers), not a power of ten and
      not the result of a ratio that holds or a unit conversion of another number of the evidence or of a known one."""
    toks, skel = _tokens(ev)
    ok, out = set(), []
    for i, rx in enumerate(EQUATION):
        for m in rx.finditer(skel):
            a, b, c = (int(m.group(3)), int(m.group(1)), int(m.group(2))) if i == 0 else tuple(int(g) for g in m.groups())
            (sa, va, ha), (sb, vb, _), (sc, vc, _) = toks[a], toks[b], toks[c]
            if not vc or re.search(r'[x*]\s*#?$', skel[:m.start(1 if i == 0 else 2)]) or \
                    (i == 1 and CHAIN.match(skel, m.end())):
                continue  # '16 x 10 / 3.3': the numerator is a product; 'a = b, b / c = d' is read as b / c = d
            if _near(va, ha, vb / vc):
                ok.add(a)
                for n in CHAIN.finditer(skel, m.end()):  # '= 0.0933 mM^-1 s^-1 = 93.3 M^-1 s^-1'
                    if n.start() != m.end():
                        break
                    ok.add(int(n.group(1)))
                    m = n
            else:
                out.append(f"'{sb} / {sc} = {sa}' does not hold ({sb}/{sc} = {vb / vc:.3g})")
    near = [v for k in known for _, v, _ in _tokens(k)[0]] + [float(n) for k in known for n in C.numbers(k)]
    for i, (sa, va, ha) in enumerate(toks):
        mant = re.match(r'\d+(?:\.\d+)?', sa).group(0)  # '1.68 x 10^5': the paper prints 1.68 (and 10, 5)
        if float(mant) in text_numbers or va in text_numbers or (va > 0 and math.log10(va).is_integer()) \
                or any(_near(va, ha, w) for w in near):
            ok.add(i)
    while True:  # a unit conversion of a number already accounted for ('20 ± 2 (= 20000 mM^-1 s^-1)')
        more = {i for i, (_, va, ha) in enumerate(toks) if i not in ok and any(_near(va, ha, toks[j][1]) for j in ok)}
        if not more:
            break
        ok |= more
    return out + [f'{sa} is not printed in the paper' for i, (sa, _, _) in enumerate(toks) if i not in ok]


def _half_unit(a):
    """Half a unit of a printed number's last digit (an integer's trailing zeros are not significant: 57000 -> 500)."""
    digits = len(a.split('.')[1]) if '.' in a else -(len(a) - len(a.rstrip('0')))
    return 0.5 * 10.0 ** -digits * (1 + 1e-9)


def _inference(s):
    try:
        from site_release import INFERENCE
    except Exception:
        return False
    return bool(INFERENCE.search(s))
