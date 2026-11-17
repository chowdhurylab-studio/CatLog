#!/usr/bin/env python3
"""CatLog's reading steps as frozen on 9 November 2026 (the main repository's tag catlog-freeze-20261109; the kit's
catlog-copy at that snapshot), run on the 53 hard-case papers Opus 5.5 read: the rules-only check (the owner, 9 Nov:
"see whats needed - run it"). Kit run A6-hard (<the kit folder>/records/runs/A6-hard/, its launch and agent
records in records/logs/A6-hard/, its audit in records/audit/A6-hard/). Scored on the same checked keys with the same
code as the plain read and CatLog's earlier readings (score_hard.score_cell).

Two readings per paper:
- today's reader alone: its work/<PMID>.read.json, cells converted by CatLog's code as score_catlog_first.converted
  converts the first reading (the rules in read.md and the reader's task, before any verifier or code check);
- today's first pass: the rows `add` kept (reader, independent verifier, verifier of missed values, code conversion and
  the code checks), nothing after it (no sweep, database check, audit or re-read).
Beside them, from summary.json: the plain read (Opus 5.5, one read), CatLog's first reading (its earliest work file, with
the rules of its day) and CatLog's catalogue now. These papers have no reading today and are listed: one whose agents
switched model and is not redone; one that broke a rule (the audit's rerun.txt, a switch the switch rule settled
excepted), or whose kept launch (the last that ran agents for it, its redo's for a redone paper:
common_w1.a6_kept_agents) has a launch session the audit broke; one the audit did not see ('not audited': its kept
launch has no audited reader or no audited verifier, or the audit lists it without one); one the safety filter stopped
on the copy's side (an Opus agent's refusal started the workflow's Sonnet retry of its role, in any launch of the
paper's state, so a follow-up or redo that read it again changes nothing: common_w1.a6_refused, 'refused (catlog)', as
the plain read's refused papers have no read); one the copy left without a finished read (whatever refusal an agent
got past before: a usage limit or a crash is no refusal); one whose kept launch ran a Sonnet retry that no refusal
started ('catlog retry on another model': read again on Opus, run_a6.py hard --redo --pmids P); and one whose kept
launch ran an agent on another model than Opus 5.5 (a switch or a fallback line; a retry that never ran is no other
model) or whose kept rows are stamped with another reader or verifier model ('catlog read by another model'). The
audit's rules are the locked test's (common_w1.a6_audit, as score_locked.a6_rows takes them): it stops when the audit
is missing, holds no agent of a paper, or is older than the last reset-a6 hard (main or --redo). Refused when a scored
row's pipeline_commit, read_prompt or verify_prompt stamp is not the frozen copy's (the tag catlog-freeze-20261109 and
MANIFEST.json; common_w1.a6_stamp_problems).

Same inputs: a paper whose text, original or supplement in the copy (records/a6_inputs_hard.json) is not what the plain
read was given (records/hard_inputs.json; common_w1.input_records, input_hashes) is scored as the others but listed
apart in today_summary.md, with its own row in each table, and marked inputs_differ in today_scores.json (five on 10 Nov:
production's caption retext of 9 Nov came between the plain read's folders and the copy's lay-down).

Named papers: CatLog's own instructions, which every agent loads (CLAUDE.md, read.md, verify.md), name 8 of the 53
papers with their trap, and code comments 3 more (the smoke test's reader of 12604203 said so, 9 Nov). The main result is
on the papers nothing names; the named ones are counted apart (NAMED, found in the snapshot's files by named_papers()).

  python3 score_today.py       writes today_scores.json and today_summary.md in this folder"""
import collections, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE))
import score_catlog_first as F  # noqa: E402  (sets the import paths for the kit and units)
import score_hard as SH  # noqa: E402
import common_w1 as W  # noqa: E402

RUN = F.EV / 'records' / 'runs' / 'A6-hard'
LOGS = F.EV / 'records' / 'logs' / 'A6-hard'
DONE = {'done', 'incomplete', 'needs_supplement', 'wrong_paper', 'no_kinetics'}  # score_w1.DONE_A6
COPY = F.EV / 'catlog-copy'
INSTRUCTIONS = [COPY / 'CLAUDE.md', Path.home() / '.claude' / 'CLAUDE.md', *sorted((COPY / 'prompts').glob('*.md')),
                COPY / '.claude' / 'agents' / 'catlog-reader.md', COPY / '.claude' / 'workflows' / 'catlog-batch.js']
CODE = [*sorted(COPY.glob('*.py')), *sorted((COPY / 'tools').glob('*.py'))]
ORDER = ['RA3', 'RA1', 'PP2', 'PP7', 'PP3', 'PP4', 'PP1', 'IP11', 'RA4', 'TL1', 'TL2', 'TL4']


def named_papers(pmids):
    """{pmid: 'instructions' | 'code'}: the papers the snapshot's instruction files or code name by their PMID."""
    import re
    out = {}
    for kind, files in (('instructions', INSTRUCTIONS), ('code', CODE)):
        text = '\n'.join(f.read_text(errors='replace') for f in files if f.exists())
        for p in pmids:
            if p not in out and re.search(rf'(?<![0-9A-Za-z]){re.escape(p)}(?![0-9A-Za-z])', text):
                out[p] = kind
    return out


def kept_run():
    """(papers.tsv statuses, catalog rows by paper, work folder, each kept row's stamps by paper) of the kept run; a
    redone paper's from its redo."""
    if not (RUN / 'RESET.json').exists():
        sys.exit(f'{RUN} is not kept yet (w1_setup.py reset-a6 hard)')
    redo = RUN / 'redo'
    redone = set(json.loads((redo / 'RESET.json').read_text()).get('pmids') or []) if (redo / 'RESET.json').exists() else set()
    st = {r['pmid']: r['status'] for r in W.read_tsv(RUN / 'papers.tsv')}
    if redone:
        st.update({r['pmid']: r['status'] for r in W.read_tsv(redo / 'papers.tsv') if r['pmid'] in redone})
    rows, stamps = collections.defaultdict(list), collections.defaultdict(list)
    for folder, mine in ((RUN, lambda p: p not in redone), (redo, lambda p: p in redone)):
        f = folder / 'catalog.jsonl'
        for line in (open(f) if f.exists() else []):
            if line.strip():
                r = json.loads(line)
                p = str(r.get('pmid'))
                if mine(p):
                    rows[p].append({'metric': r.get('metric'), 'value': r.get('value'), 'raw': r.get('raw_value'),
                                    'raw_unit': r.get('raw_unit'), 'enzyme': r.get('enzyme'), 'variant': r.get('variant'),
                                    'substrate': r.get('substrate'), 'id': r.get('row_id'), 'unit': r.get('unit')})
                    stamps[p].append({k: r.get(k) for k in ('pmid', 'read_by', 'pipeline_commit', 'read_prompt', 'verify_prompt',
                                                            'reader_model', 'verifier_model')})
    work = {p: (redo if p in redone else RUN) / 'work' for p in st}
    return st, rows, work, stamps


def inputs_differ(pmids):
    """{pmid: what differs}: the papers whose text, original or supplement in the copy (records/a6_inputs_hard.json) is
    not what the plain read's folder was given (records/hard_inputs.json), or that one of the two records lacks."""
    f = F.EV / 'records' / 'a6_inputs_hard.json'
    a6 = (json.loads(f.read_text()).get('papers') or {}) if f.exists() else {}
    plain = W.input_records(F.EV)['hard_inputs']
    out = {}
    for p in pmids:
        if p not in a6 or p not in plain:
            out[p] = 'no record in ' + ', '.join(n for n, r in (('a6_inputs_hard', a6), ('hard_inputs', plain)) if p not in r)
        else:
            keys = [k for k, x, y in zip(W.INPUT_KEYS, W.input_hashes(a6[p]), W.input_hashes(plain[p])) if x != y]
            if keys:
                out[p] = ', '.join(keys)
    return out


def main():
    summ = {r['pmid']: r for r in json.loads((BASE / 'summary.json').read_text()) if r['model'] == 'Opus 5.5'}
    st, rows, work, stamps = kept_run()
    named = named_papers(list(summ))
    switched = {p: r.get('outcome') for p, r in W.read_switches(LOGS).items()}
    state = W.a6_state_agents(F.EV, 'hard')  # every launch of each paper's state (main, more-k; a redone paper's redo too)
    kept = W.a6_kept_agents(F.EV, 'hard', state)  # each paper's kept launch (its redo's for a redone paper) and its agents
    other = W.a6_other_model(F.EV, 'hard', kept)  # an agent of that launch on another model
    stamped = W.a6_stamped_other_model([x for v in stamps.values() for x in v])  # a kept row stamped with another model
    launch_broken = W.a6_launch_broken(F.EV, 'hard', kept)  # its kept launch's launch session broke a rule (audit.json)
    broken, unaudited = W.a6_audit(F.EV, 'hard', list(summ), kept)  # the locked test's audit rules (score_locked.a6_rows)
    differ = inputs_differ(list(summ))
    out = {}
    for p, s in summ.items():
        base = BASE if s['set'] == 'first' else BASE / 'expand'
        key, cells = SH.cells_of(p, base)
        why = ('not usable' if not key.get('usable', True) else
               f"switched model ({switched[p]})" if switched.get(p) in ('redo_pending', 'excluded') else
               'broke a rule' if p in broken else
               f'broke a rule (the launch session of {launch_broken[p]})' if p in launch_broken else
               'not audited' if p in unaudited and st.get(p) in DONE else
               'refused (catlog)' if W.a6_refused(state.get(p) or []) else
               f"status {st.get(p, 'missing')}" if st.get(p) not in DONE else
               'catlog retry on another model' if W.a6_retried((kept.get(p) or ('', []))[1]) else
               'catlog read by another model' if p in other or p in stamped else '')
        if why:
            out[p] = {'class_id': s['class_id'], 'today': None, 'why': why,
                      **({'inputs_differ': differ[p]} if p in differ else {})}
            continue
        ident = str(key.get('trap_kind', '')).startswith('identity')
        rf = work[p] / f'{p}.read.json'
        reader_rows = [r for r in (json.loads(rf.read_text()).get('rows') or []) if not r.get('censored')] if rf.exists() else []
        reader = F.converted(p, reader_rows)
        first_pass = [v for v in rows.get(p, []) if v.get('unit') in F.UNITS]
        rec = {'class_id': s['class_id'], 'set': s['set'], 'visible': s.get('visible'), 'status': st[p], 'cells': len(cells),
               'named_in': named.get(p, ''),
               'reader_rows': len(reader), 'kept_rows': len(first_pass)}
        for name, vals in (('reader', reader), ('first_pass', first_pass)):
            v = [SH.score_cell(c, vals, ident)[0] for c in cells]
            rec[name] = {'verdicts': v, 'trap': v.count('trap'), 'right': v.count('right'), 'review': v.count('review'),
                         'missing': v.count('missing'), 'other': v.count('other'), 'fell_in': v.count('trap') > 0}
        rec['plain_fell_in'] = s['fell_in']
        rec['catlog_first_fell_in'] = s.get('catlog_first_fell_in')
        rec['catalogue_now_fell_in'] = bool(s.get('catlog_trap')) if s.get('catlog_status') else None
        if p in differ:  # scored, and counted apart too
            rec['inputs_differ'] = differ[p]
        out[p] = rec
    bad = W.a6_stamp_problems([x for p, r in out.items() if r.get('reader') for x in stamps.get(p, [])],
                              json.loads((F.EV / 'MANIFEST.json').read_text()))
    if bad:  # the rows scored are the frozen copy's: its snapshot commit, read.md and verify.md (MANIFEST.json)
        sys.exit(f'{len(bad)} papers have kept rows stamped otherwise than the frozen copy (MANIFEST.json a6.'
                 f'pipeline_commit_stamp, prompt_hashes_stamp_style): {bad}')
    (HERE / 'today_scores.json').write_text(json.dumps(out, indent=1) + '\n')
    read_all = {p: r for p, r in out.items() if r.get('reader')}
    L = ['# Hard cases read again with CatLog as frozen on 9 November 2026 (code scoring)', '',
         f'Papers: {len(summ)} read by Opus 5.5 in the plain read; {len(read_all)} with a reading today '
         f'({len(summ) - len(read_all)} without: ' + ', '.join(f"{p} {r['why']}" for p, r in out.items() if not r.get('reader')) + ').',
         f"Named by CatLog's instructions or code (counted apart): " + ', '.join(f'{p} ({k})' for p, k in sorted(named.items())) + '.',
         "Inputs differ (the copy's text, original or supplement is not what the plain read was given: "
         'records/a6_inputs_hard.json against hard_inputs.json; scored as the others, and counted in their own row of each '
         'table): ' + (', '.join(f'{p} ({d}{"" if out[p].get("reader") else "; no reading today"})'
                                for p, d in sorted(differ.items())) or 'none') + '.',
         'Fell in = the reading stored a trap value in at least one cell of its key (score_hard.score_cell; cells only an '
         'agent can decide are "review" and count as not fallen in here, before the blind re-score).', '']
    for title, read in (('Papers no instruction or code names', {p: r for p, r in read_all.items() if not r['named_in']}),
                        ('All papers', read_all)):
        L += table(title, read, differ)
    (HERE / 'today_summary.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


def tally(read):
    """A table row's counts for these papers."""
    b = collections.Counter()
    for p, r in read.items():
        b['papers'] += 1
        b['plain'] += r['plain_fell_in']
        b['reader'] += r['reader']['fell_in']
        b['first_pass'] += r['first_pass']['fell_in']
        b['review'] += r['reader']['review'] + r['first_pass']['review'] > 0
        if r['catlog_first_fell_in'] is not None:  # a paper CatLog had read before
            b['had_read'] += 1
            b['old_first'] += bool(r['catlog_first_fell_in'])
            b['now'] += bool(r['catalogue_now_fell_in'])
    return b


def row(k, b):
    return (f"| {k} | {b['papers']} | {b['plain']} | {b['reader']} | {b['first_pass']} | {b['old_first']} of {b['had_read']} | "
            f"{b['now']} of {b['had_read']} | {b['review']} |")


def table(title, read, differ=()):
    """One table: a row per kind, all, and the papers whose inputs differ among them (counted in the rows above too)."""
    L = [f'## {title} ({len(read)})', '', '| kind | papers | plain read | CatLog today: reader alone | CatLog today: reader, verifier and code | '
         'CatLog first reading then (of papers it had read) | catalogue now (of those) | papers with cells to review |',
         '|---|---|---|---|---|---|---|---|']
    by = collections.defaultdict(dict)
    for p, r in read.items():
        by[r['class_id']][p] = r
    for k in ORDER + sorted(set(by) - set(ORDER)):
        if by.get(k):
            L.append(row(k, tally(by[k])))
    L.append(row('all', tally(read)))
    apart = {p: r for p, r in read.items() if p in differ}
    if apart:
        L.append(row('of which inputs differ', tally(apart)))
    cells = sum(r['cells'] for r in read.values())
    L += ['', f"Trap cells: reader alone {sum(r['reader']['trap'] for r in read.values())} of {cells}, reader, verifier and "
              f"code {sum(r['first_pass']['trap'] for r in read.values())} of {cells}.", '']
    return L


if __name__ == '__main__':
    main()
