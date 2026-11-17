#!/usr/bin/env python3
"""A content scan of the locked set's reading sessions (after w1_audit.py A0-locked and A6-locked, before triage), as
scan_judges.py scans the judges: every tool input and every result of every plain read session (records/logs/A0-locked/:
the session records, and the earlier ones a step kept when it ran again) and of every agent of the copy's launches for
A6-locked (records/logs/A6-locked/<launch>/: run_a6.launch_agents, so agents.json, or for a launch killed on the way the
agents read from its session's transcripts), for what a reader must not have seen, whatever path it took (the audit
breaks only a path a call writes out; a script walking the home folder names none).

  python3 tools/w1/scan_reads.py locked   -> records/audit/A0-locked/ and A6-locked/content_scan.json; exit 1 on a hit

A hit, per session and call:
- the owner's downloads, where other groups' answer keys and their models' extractions for the held-out papers sit
  (~/Downloads/data): 'Downloads' in an input, the folder's path in a result (the copy's catlog.py prints ~/Downloads
  in its own help text, which its readers may read);
- those files by name, in an input or a result: manual_curated_runeem, rumble_, EnzyExtract, dataset_223;
- the main folder's catalogue (catlog-v2/catalog...), in an input or a result; its export and the database values
  (catlog_wide, db_values, brenda_2026): in an input or a result of a plain read, in an input of the copy's agents (the
  copy's own read.md, verify.md, catlog-reader.md and catlog.py print these names, which every reader reads);
- the main folder itself (Documents/catlog-v2, however the home folder is written) and the old system's folder
  (Documents/realkcat: the old catalogue built from database imports, data/verified_catlog.jsonl and the static
  exports), both closed to plain sessions (run_plain.py): for a plain read in an input or a result, as scan_judges
  closes them; for the copy's agents in an input only (the copy's read.md, verify.md and catlog-reader.md name the main
  folder and its CLAUDE.md realkcat, so a result that prints those files is no hit, but nothing a copy's agent types
  needs either folder);
- another locked paper's PMID (records/orders/locked_draw.txt) in a result, except as a file name in a listing (the
  plain reads share one output folder, the copy one work folder: <PMID>.json, <PMID>.prompts.json); in a record
  ('"pmid": ...'), a grep line ('texts/<PMID>.txt:12: ...') or a folder's path it is a hit;
- a launch folder of the copy whose agents cannot be accounted for (a session was started there that no launch.json
  names, or the named session ran and its transcript is gone: run_a6.launch_agents None), and an agent whose transcript
  is missing."""
import argparse, json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402
import claude_session as S  # noqa: E402
import run_a6 as RA6  # noqa: E402
import w1_audit as AU  # noqa: E402

NAMES = ('manual_curated_runeem', 'rumble_', 'EnzyExtract', 'dataset_223', 'catlog-v2/catalog')
EXPORT_NAMES = ('catlog_wide', 'db_values', 'brenda_2026')  # the catalogue's export and the database values (main's)
MAIN_PATH = str(W.MAIN).replace(str(Path.home()) + '/', '', 1)  # Documents/catlog-v2: written with /Users/..., ~ or $HOME
REALKCAT_PATH = str(W.REALKCAT).replace(str(Path.home()) + '/', '', 1)  # Documents/realkcat, the old system's folder
RECORD = W.SESSION_RECORD  # a plain read's session record (claude_session.run_session)
TOKEN = re.compile(r'(?<![0-9A-Za-z])\d{4,9}(?![0-9A-Za-z])')
LISTED = re.compile(r'(?:\.[A-Za-z]+)+(?=$|[\s"\',\]])')  # the rest of a file name a listing shows: <PMID>.json, .prompts.json


def sessions(ev, run):
    """(sessions, unaccounted): (where the scan's result goes, record name, the session's paper, transcript) of every
    plain read session of A0-<run> and every agent of A6-<run>'s launches; and the launch folders of A6-<run> whose
    agents cannot be accounted for (run_a6.launch_agents None)."""
    P = W.eval_paths(ev)
    lg = P['logs'] / W.run_label('A0', run)
    out, unaccounted = [], []
    for f in sorted(lg.glob('*.json')) + sorted(lg.glob('earlier/*/*/*.json')):
        m = RECORD.match(f.name)
        if m:
            out.append((W.run_label('A0', run), str(f.relative_to(lg)), m['pmid'],
                        json.loads(f.read_text()).get('transcript') or ''))
    for d in W.a6_launches(ev, run):
        rows = RA6.launch_agents(d)
        if rows is None:
            unaccounted.append(d.name)
            continue
        for r in rows:
            if r.get('pmid'):
                out.append((W.run_label('A6', run), f"{d.name}/{r.get('label')}", str(r['pmid']), r.get('transcript') or ''))
    return out, unaccounted


def names(where, part):
    """The names that are a hit in this part ('input' or 'result') of a call of a session of A0-<run> or A6-<run>."""
    closed = where.startswith('A0-') or part == 'input'  # a plain read's input or result, a copy's agent's input
    return (NAMES + (EXPORT_NAMES + (MAIN_PATH, REALKCAT_PATH) if closed else ())
            + (('Downloads',) if part == 'input' else (str(S.DOWNLOADS),)))


def scan(ev, run):
    """{run label: (sessions scanned, hits)} for A0-<run> and A6-<run>."""
    locked = set(W.read_order(ev, f'{run}_draw'))
    out = {W.run_label(a, run): [0, []] for a in ('A0', 'A6')}
    found, unaccounted = sessions(ev, run)
    for d in unaccounted:
        out[W.run_label('A6', run)][1].append({'record': d, 'hit': 'agents not accounted for',
                                               'where': 'a session no launch.json names, or one that ran and whose '
                                                        'transcript is gone'})
    for where, rec, pmid, tr in found:
        res = out[where]
        if not tr or not Path(tr).exists():
            res[1].append({'record': rec, 'hit': 'transcript missing', 'where': tr})
            continue
        res[0] += 1
        _, calls, *_ = AU.parse(tr)
        for i, c in enumerate(calls):
            for part, text in (('input', c.get('raw') or ''), ('result', c.get('result') or '')):
                hits = [(text.find(n), f'named {n}') for n in names(where, part) if n in text]
                if part == 'result':  # each other paper once per call, at its first place
                    first = {}
                    for m in TOKEN.finditer(text):
                        if m.group() in locked and m.group() != pmid and not LISTED.match(text, m.end()):
                            first.setdefault(m.group(), m.start())
                    hits += [(j, f"another locked paper's pmid ({p})") for p, j in first.items()]
                for j, what in hits:
                    res[1].append({'record': rec, 'call': i, 'tool': c.get('name'), 'part': part, 'hit': what,
                                   'text': text[max(0, j - 80):j + 120]})
    return {k: tuple(v) for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run', choices=('locked',))
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    ev = Path(a.eval)
    found, summary = 0, {}
    for label, (n, hits) in scan(ev, a.run).items():
        d = W.eval_paths(ev)['audit'] / label
        d.mkdir(parents=True, exist_ok=True)
        W.write_json(d / 'content_scan.json', {'time': W.now(), 'run': label, 'sessions_scanned': n, 'hits': hits})
        by = {}
        for h in hits:
            by.setdefault(h['hit'].split(' (')[0], set()).add(h['record'])
        summary[label] = {'sessions_scanned': n, 'hits': len(hits), 'sessions_by_kind': {k: len(v) for k, v in by.items()}}
        found += len(hits)
    print(json.dumps(summary, indent=1))
    sys.exit(1 if found else 0)


if __name__ == '__main__':
    main()
