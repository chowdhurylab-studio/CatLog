#!/usr/bin/env python3
"""W1 plain arms: A0 (one plain read per paper) and A2's independent reads, one headless Claude Code session per paper
and read (claude_session.py), `--lanes` at a time. A2's reconcile is run_reconcile.py.

  python3 tools/w1/run_plain.py --arm A0 --run 1            the run's papers in orders/A0-r1.txt
  python3 tools/w1/run_plain.py --arm A2 --run 1            reads A and B of every paper in orders/A2-r1.txt
  python3 tools/w1/run_plain.py --arm A0 --run pilot        the pilot (orders/A0-pilot.txt; never in the decision);
                                                            --run dry: FREEZE.md F6's dry run (orders/A0-dry.txt)
  options: --pmids P ... (instead of the order file), --lanes 9, --timeout 3600 (seconds per session), --one-model (every
           session on MODEL: the retry too, and a refused paper stays without a read, claude_session.step),
           --reads 3 (A2 with a third read, if the pilot's sizing rule asks for it), --force (redo valid outputs),
           --dry-run (write the prompts and commands to logs/ and print the first; runs nothing)

Each session: cwd papers/<PMID>/ (paper.txt without the GLYPH WARNING paragraph, paper.supp.txt, source.pdf|xml),
the A0 prompt verbatim (prompts/A0.txt, A0_plain_prompt.md) with {DIR} = that folder, {RUN} = the opaque code of the
arm-run part (common_w1.code('A0-r1'), code('A2-r1-readA'): a session never sees an arm or run name), {OUT} =
out/<that code>/<PMID>.json, {VALIDATE} = papers/check_rows.py. Outputs already valid are skipped, so a stopped run
resumes where it stopped; a step a model switch left out (records/logs/<arm-run>/model_switch.json, outcome excluded)
is never run again. Logs, usage and transcript paths: records/logs/<arm-run>/ (sessions.tsv, one JSON per attempt, the
prompt sent, versions.json, model_switch.json)."""
import argparse, json, sys, time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402
import claude_session as S  # noqa: E402
import validate_plain as V  # noqa: E402

PARTS = {2: ('readA', 'readB'), 3: ('readA', 'readB', 'readC')}


def other_runs(ev, own=()):
    """Read-deny rules for every folder under out/ (every arm-run part, the claims and the verdicts) except `own`."""
    own = {Path(o) for o in ([own] if isinstance(own, (str, Path)) else own)}
    return S.deny_read(*[f for f in W.out_folders(ev) if Path(f) not in own])


def plain_deny(ev, own_out_dir, label, also_readable=(), run=None):
    """Every eval part but papers/ and the session's own output folder (and, for the reconcile, its read folders): the
    records (keys, scores, logs, orders, audit, A6's kept runs), the kit worktree, catlog-copy, checks, the top-level
    notes, every other folder under out/; other sessions' /tmp scratch; production and other sessions' records and
    scratchpads (REVIEW.md 1.3-1.5). label: the session's scratch code. run 'locked' (2026-11-09): the owner's downloads
    too (other groups' answer keys for the held-out papers sit there); the finished runs' lists are as they were."""
    folders, files = W.eval_entries(ev, keep=(W.OUT_NAMES['plain'], W.OUT_NAMES['out']))
    return (S.deny_read(W.MAIN, W.REALKCAT, *W.old_layout(), *folders) + S.deny_read_files(*files)
            + other_runs(ev, [own_out_dir, *also_readable]) + S.other_scratch_deny(label) + S.records_deny('plain', ev)
            + (S.downloads_deny('Read') if run == 'locked' else []))


def check_plain(pmid):
    def check(f):
        ok, n, problems = V.check_file(f)
        if ok:
            d = json.loads(Path(f).read_text())
            if str(d.get('pmid')) != str(pmid):
                return False, f'pmid {d.get("pmid")!r} is not {pmid}'
        return ok, (f'OK {n} rows' if ok else '; '.join(problems[:5]))
    return check


def jobs_for(ev, arm, run, pmids, reads):
    P = W.eval_paths(ev)
    out = []
    for p in pmids:
        for part in ([None] if arm == 'A0' else PARTS[reads]):
            lab = W.part_label(arm, run, part)
            out.append({'pmid': p, 'part': part, 'part_label': lab, 'run_code': W.code(lab),
                        'out': W.out_file(ev, arm, run, part, p), 'cwd': P['plain'] / p,
                        'log_dir': P['logs'] / W.run_label(arm, run),
                        'step': f"{p}" + (f".{part}" if part else '')})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--arm', required=True, choices=('A0', 'A2'))
    ap.add_argument('--run', required=True, help='1, 2, 3, pilot or dry')
    ap.add_argument('--pmids', nargs='*')
    ap.add_argument('--lanes', type=int, default=9)
    ap.add_argument('--timeout', type=int, default=3600)
    ap.add_argument('--reads', type=int, default=2, choices=(2, 3))
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--one-model', action='store_true')
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    ev = Path(a.eval)
    P = W.eval_paths(ev)
    a.run = W.check_run(a.run)
    a.one_model = a.one_model or a.run in ('rand', 'locked')  # the further and the locked sets are on one model, whatever the command line
    pmids = a.pmids or W.read_order(ev, W.run_label(a.arm, a.run))
    if not pmids:
        sys.exit(f'no papers: pass --pmids or write orders/{W.run_label(a.arm, a.run)}.txt (w1_setup.py setup)')
    missing = [p for p in pmids if not (P['plain'] / p / 'paper.txt').exists()]
    if missing:
        sys.exit(f'{len(missing)} papers have no plain/<PMID>/paper.txt (run w1_setup.py setup): {missing[:5]}')
    if not P['validator'].exists():
        sys.exit(f'missing {P["validator"]} (run w1_setup.py setup)')
    template = W.prompt_text('A0.txt')
    jobs = jobs_for(ev, a.arm, a.run, pmids, a.reads)
    gone = S.excluded_steps(P['logs'] / W.run_label(a.arm, a.run))
    left_out = [j['step'] for j in jobs if j['step'] in gone]
    if left_out:
        print(f'{len(left_out)} steps left out after a second model switch (model_switch.json), not run again: {left_out}')
    refused = S.refused_steps(P['logs'] / W.run_label(a.arm, a.run))
    if refused & {j['step'] for j in jobs}:
        print(f"{len(refused & {j['step'] for j in jobs})} steps the safety filter stopped (refused.tsv), not sent again")
    log = P['logs'] / W.run_label(a.arm, a.run) / 'sessions.tsv'  # one model: a read no ok session vouches for is read again
    vouched = {r['label'].rsplit('.', 1)[0] for r in W.read_tsv(log) if r.get('ok') == 'True'} if log.exists() else set()
    todo = [j for j in jobs if j['step'] not in gone and j['step'] not in refused and
            (a.force or not V.check_file(j['out'])[0] or (a.one_model and j['step'] not in vouched))]
    if not a.dry_run:
        S.check_folders(j['cwd'] for j in todo)
    print(f'{W.run_label(a.arm, a.run)}: {len(jobs)} sessions, {len(jobs) - len(todo)} already valid, {len(todo)} to run, '
          f'{a.lanes} lanes' + (' (dry run)' if a.dry_run else ''))
    log_dir = P['logs'] / W.run_label(a.arm, a.run)
    if not a.dry_run:
        S.versions(log_dir, 'before')
    lanes = S.Lanes(a.lanes)

    def one(j):
        j['out'].parent.mkdir(parents=True, exist_ok=True)
        prompt = lambda model: W.fill(template, PMID=j['pmid'], DIR=j['cwd'], RUN=j['run_code'], OUT=j['out'],
                                      VALIDATE=P['validator'])
        res = S.step(prompt, j['cwd'], j['out'], j['log_dir'], j['step'],
                     check_plain(j['pmid']), add_dirs=[j['out'].parent],
                     deny=plain_deny(ev, j['out'].parent, j['run_code'], run=a.run), timeout=a.timeout, dry=a.dry_run,
                     lanes=lanes, scratch=f"{j['run_code']}-{j['pmid']}-", pmid=j['pmid'], one_model=a.one_model)
        if not a.dry_run:
            S.append_sessions(j['log_dir'], j['part_label'], j['pmid'], res)
            state = ('ok' if res['ok'] else 'LEFT OUT (model switched twice)' if res.get('excluded')
                     else 'REFUSED' if res.get('refused') else 'FAILED')
            print(f"{j['part_label']} {j['pmid']}: {state} ({res['check']})", flush=True)
        return res

    if a.dry_run:
        res = [one(j) for j in todo[:1]]
        if todo:
            rec = res[0]['attempts'][0]
            print('command:', json.dumps(rec['command']))
            print('cwd:', rec['cwd'])
            print('prompt:\n' + (log_dir / f"{rec['label']}.prompt.txt").read_text())
        return
    results = lanes.map(one, todo)
    failed = [j['step'] for j, r in zip(todo, results) if r is not None and not r['ok'] and not r.get('excluded')
              and not r.get('refused')]
    excluded = [j['step'] for j, r in zip(todo, results) if r is not None and r.get('excluded')]
    not_started = [j['step'] for j, r in zip(todo, results) if r is None]
    S.versions(log_dir, 'after')
    summary = {'run': W.run_label(a.arm, a.run), 'sessions': len(todo), 'failed': failed,
               'left_out_model_switch': sorted(set(excluded) | set(left_out)), 'not_started': not_started,
               'refused': sorted(refused & {j['step'] for j in jobs} | {j['step'] for j, r in zip(todo, results) if r and r.get('refused')}),
               'stopped': lanes.stopped(), 'time': W.now()}
    W.write_json(log_dir / f'summary_{int(time.time())}.json', summary)
    print(json.dumps(summary, indent=1))
    if lanes.stopped():
        print(f'{W.DEAD_STOP} failed sessions in a row (most likely the usage limit): rerun the same command later; '
              'valid outputs are skipped.')


if __name__ == '__main__':
    main()
