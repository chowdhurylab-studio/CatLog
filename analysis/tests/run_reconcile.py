#!/usr/bin/env python3
"""W1 arm A2, step 2: the plain reconcile of a paper's independent reads (A2_compute_matched_prompt.md), one headless
Claude Code session per paper (claude_session.py), `--lanes` at a time. Run it after run_plain.py --arm A2.

  python3 tools/w1/run_reconcile.py --run 1                  every paper of orders/A2-r1.txt whose reads are done
  options: --pmids P ..., --lanes 9, --timeout 3600, --reads 3 (a third read, if the pilot's sizing rule asks for
           it), --force, --dry-run, --eval EVAL

The prompt is prompts/A2_reconcile.txt verbatim, {READ_A}/{READ_B} = the reads (out/<code of A2-r<k>-readA>/<PMID>.json,
...), {OUT} = out/<code of A2-r<k>-final>/<PMID>.json (the only A2 file scored), {RUN} = the code of A2-r<k>-final.
Failure rule of the kit: a read that still failed after its retry leaves the reconcile to the other read alone (the
paper-run is flagged in records/logs/A2-r<k>/reconcile_flags.json); no valid read = the paper-run failed; a paper whose
reads have not run yet (or are running) waits. A read a model switch left out (switched on both tries,
model_switch.json) fails the paper-run: no reconcile, the paper leaves every arm's paired analysis. The one-list and
three-list wordings are the two-list text with the sentences about the lists changed (VARIANTS below; test_w1.py checks
every change applies once)."""
import argparse, json, sys, time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402
import claude_session as S  # noqa: E402
import validate_plain as V  # noqa: E402
from run_plain import check_plain, plain_deny  # noqa: E402

# wording for one list (the other read failed twice) or three lists (the pilot's sizing rule): exact replacements of the
# two-list text, each applied exactly once
VARIANTS = {
    1: [('reconcile two independent extractions', 'check an extraction'),
        ('Two curators, working independently, extracted', 'A curator extracted'),
        ('{READ_A} and {READ_B}. Either list may contain', '{READ_A}. The list may contain'),
        ('Check every value in both lists against the paper yourself, including the values both lists\nagree on.',
         'Check every value in the list against the paper yourself.'),
        ('Add any value both curators missed.', 'Add any value the curator missed.'),
        ('in the same JSON format as the two lists', 'in the same JSON format as the list'),
        ('and the two lists.', 'and the list.')],
    3: [('reconcile two independent extractions', 'reconcile three independent extractions'),
        ('Two curators, working independently, extracted', 'Three curators, working independently, extracted'),
        ('{READ_A} and {READ_B}. Either list may contain', '{READ_A}, {READ_B} and {READ_C}. Any list may contain'),
        ('Check every value in both lists against the paper yourself, including the values both lists\nagree on.',
         'Check every value in the three lists against the paper yourself, including the values the lists\nagree on.'),
        ('Add any value both curators missed.', 'Add any value all three curators missed.'),
        ('in the same JSON format as the two lists', 'in the same JSON format as the three lists'),
        ('and the two lists.', 'and the three lists.')],
}


def reconcile_text(n):
    t = W.prompt_text('A2_reconcile.txt')
    for old, new in VARIANTS.get(n, []):
        if t.count(old) != 1:
            raise ValueError(f'reconcile wording for {n} lists: {old!r} found {t.count(old)} times')
        t = t.replace(old, new)
    return t


def read_state(log_dir, pmid, part, f, gone=frozenset()):
    """ok (a valid read), excluded (both tries switched model), failed (its retry ran and left no valid file) or pending
    (not run yet, or running)."""
    if f'{pmid}.{part}' in gone:
        return 'excluded'
    if V.check_file(f)[0]:
        return 'ok'
    return 'failed' if any((Path(log_dir) / f'{pmid}.{part}.{a}.json').exists() for a in ('a2', 'a2b')) else 'pending'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', required=True, help='1, 2, 3, pilot or dry')
    ap.add_argument('--pmids', nargs='*')
    ap.add_argument('--lanes', type=int, default=9)
    ap.add_argument('--timeout', type=int, default=3600)
    ap.add_argument('--reads', type=int, default=2, choices=(2, 3))
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    a.run = W.check_run(a.run)
    ev = Path(a.eval)
    P = W.eval_paths(ev)
    label = W.run_label('A2', a.run)
    pmids = a.pmids or W.read_order(ev, label)
    if not pmids:
        sys.exit(f'no papers: pass --pmids or write orders/{label}.txt')
    parts = ('readA', 'readB', 'readC')[:a.reads]
    log_dir = P['logs'] / label
    gone = S.excluded_steps(log_dir)
    final_code = W.code(W.part_label('A2', a.run, 'final'))
    jobs, flags, waiting = [], {}, []
    for p in pmids:
        out = W.out_file(ev, 'A2', a.run, 'final', p)
        if f'{p}.final' in gone:
            flags[p] = 'reconcile switched model twice: paper-run failed (left out)'
            continue
        if not a.force and V.check_file(out)[0]:
            continue
        reads = [(part, W.out_file(ev, 'A2', a.run, part, p)) for part in parts]
        state = {part: read_state(log_dir, p, part, f, gone) for part, f in reads}
        if 'excluded' in state.values():
            flags[p] = (f"{', '.join(x for x, s in state.items() if s == 'excluded')} switched model twice: paper-run "
                        'failed (left out)')
            continue
        if 'pending' in state.values():
            waiting.append(p)
            continue
        good = [(part, f) for part, f in reads if state[part] == 'ok']
        if not good:
            flags[p] = 'no valid read: paper-run failed'
            continue
        if len(good) < len(reads):
            flags[p] = f"reconciled from {', '.join(x for x, _ in good)} only"
        jobs.append({'pmid': p, 'out': out, 'reads': good, 'cwd': P['plain'] / p})
    print(f'{label} reconcile: {len(jobs)} to run, {len(flags)} flagged, {len(waiting)} waiting for their reads'
          + (' (dry run)' if a.dry_run else ''))
    if flags and not a.dry_run:
        f = log_dir / 'reconcile_flags.json'
        old = json.loads(f.read_text()) if f.exists() else {}
        W.write_json(f, {**old, **flags})
    if not a.dry_run:
        S.check_folders(j['cwd'] for j in jobs)
        S.versions(log_dir, 'before reconcile')
    lanes = S.Lanes(a.lanes)

    def one(j):
        j['out'].parent.mkdir(parents=True, exist_ok=True)
        n = len(j['reads'])
        text = reconcile_text(n)
        names = dict(zip(('READ_A', 'READ_B', 'READ_C'), [str(f) for _, f in j['reads']]))
        prompt = lambda model: W.fill(text, PMID=j['pmid'], DIR=j['cwd'], RUN=final_code, OUT=j['out'],
                                      VALIDATE=P['validator'], **names)
        read_dirs = [f.parent for _, f in j['reads']]
        deny = plain_deny(ev, j['out'].parent, final_code, also_readable=read_dirs)
        res = S.step(prompt, j['cwd'], j['out'], log_dir, f"{j['pmid']}.final", check_plain(j['pmid']),
                     add_dirs=[j['out'].parent] + read_dirs, deny=deny, timeout=a.timeout, dry=a.dry_run, lanes=lanes,
                     scratch=f"{final_code}-{j['pmid']}-", pmid=j['pmid'])
        if not a.dry_run:
            S.append_sessions(log_dir, f'{label}-final', j['pmid'], res)
            state = 'ok' if res['ok'] else 'LEFT OUT (model switched twice)' if res.get('excluded') else 'FAILED'
            print(f"{label}-final {j['pmid']}: {state} ({res['check']})", flush=True)
        return res

    if a.dry_run:
        if jobs:
            rec = one(jobs[0])['attempts'][0]
            print('command:', json.dumps(rec['command']))
            print('prompt:\n' + (log_dir / f"{rec['label']}.prompt.txt").read_text())
        return
    results = lanes.map(one, jobs)
    summary = {'run': f'{label}-final', 'sessions': len(jobs),
               'failed': [j['pmid'] for j, r in zip(jobs, results) if r is not None and not r['ok'] and not r.get('excluded')],
               'left_out_model_switch': [j['pmid'] for j, r in zip(jobs, results) if r is not None and r.get('excluded')],
               'not_started': [j['pmid'] for j, r in zip(jobs, results) if r is None], 'flagged': flags,
               'waiting_for_reads': waiting,
               'stopped': lanes.stopped(), 'time': W.now()}
    S.versions(log_dir, 'after reconcile')
    W.write_json(log_dir / f'summary_reconcile_{int(time.time())}.json', summary)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
