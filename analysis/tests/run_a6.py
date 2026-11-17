#!/usr/bin/env python3
"""W1 arm A6's launch (A6_LAUNCH.md): one headless Claude Code session opened in catlog-copy/ with the neutral launch
line (the workflow's name, its args and the add command, nothing else), which runs the saved workflow catlog-batch and
then `python3 catlog.py add`; afterwards every agent's models are read from the transcripts, per agent.

  python3 tools/w1/run_a6.py LABEL                the run's launch (LABEL = dry, pilot, r1, r2, r3; its args are
                                                  records/orders/A6-LABEL.args.json, unchanged)
  python3 tools/w1/run_a6.py LABEL --pmids P ...  a follow-up launch in the same catlog-copy state, for papers a
                                                  usage-limit stop left without agent files or that add left reading
                                                  (A6_LAUNCH.md step 3): they are claimed again first; a paper
                                                  catlog-copy finished already (score_w1.DONE_A6) is refused unless
                                                  --force (it would be read twice inside one kept run; launch.json then
                                                  records force and those papers, read_again)
  python3 tools/w1/run_a6.py LABEL --redo         after `w1_setup.py reset-a6 LABEL`: the papers whose reader or verifier
                                                  switched model, read again (reader, verifier, missed-values verifier)
                                                  in the fresh catlog-copy; then `w1_setup.py reset-a6 LABEL --redo`
  python3 tools/w1/run_a6.py LABEL --recover LAUNCH   a launch killed on the way (launch.json names its session, no
                                                  agents.json): its records completed from its session's transcripts,
                                                  read only, as the launcher would have at the end (recover); no session
                                                  is started. reset-a6 refuses until it is done
  options: --redo --pmids P ... (a follow-up inside the redo), --timeout 86400 (seconds), --force (a follow-up may name
           finished papers), --dry-run (print the launch line, the command and the environment; run and write nothing),
           --eval EVAL
A set read after the W1 rounds (hard, locked: common_w1.LATER_LABELS) is launched only while catlog-copy's HEAD and
MANIFEST.json's a6.pipeline_commit_stamp are the commit the main repository's tag catlog-freeze-20261109 names
(common_w1.a6_pin_problems), the dry run included.

The session: cwd catlog-copy/, the owner's Claude Code settings as in production (user, project and local sources:
catlog-copy/.claude/settings.json, its settings.local.json deny rules), `-p --model claude-opus-5-5 --effort max
--output-format json --session-id <uuid>`, the launch line on stdin, and an environment rebuilt from a short list
(claude_session.ENV_KEEP: nothing of a calling Claude Code session) with DISABLE_AUTOUPDATER=1, the model pin
(common_w1.PIN_ENV), CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1 (common_w1.NO_GIT_CONTEXT_ENV: no gitStatus block, whose
recent commits are the kit's, in any agent's context) and CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 (common_w1.NO_MEMORY_ENV:
memory off, as for the plain arms; main's memory index, which names the paper's plans, is not loaded) and
CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 (the session waits for its workflow however long it runs), which hold
for the workflow's agents too (they run in the session's process). catlog-copy is a folder with its own git repository
(one orphan snapshot commit, no ref: w1_setup.own_repo), so git there shows nothing of main or the kit.

Model rule (dry-run fix, 2026-11-01): an agent whose transcript shows another model than it was started with
(claude-opus-5-5; claude-sonnet-5-5 for the workflow's own retry, labelled '-sonnet'), or a model-fallback line, makes
its paper 'redo_pending' in records/logs/A6-LABEL/model_switch.json: its rows were made partly by another model, so the
scorer leaves the paper out until the redo. The redo reads the paper again (all its agents) in a fresh state; both
records are kept (records/runs/A6-LABEL/ and records/runs/A6-LABEL/redo/, with their logs). A paper whose redo agents
switch again is 'excluded': it leaves every arm's paired analysis. The launch session's own models are recorded too.

Records: records/logs/A6-LABEL/<launch>/ (launch = main, more-<n>, redo, redo-more-<n>): launch_line.txt, launch.json
(command, environment names, session id, transcript, times, the result; written before the session starts and again at
its end, so a launch killed on the way can be accounted for: launch_agents), session.json (the CLI's stdout),
session.err, agents.json (every agent: label, paper, role, model started with, model sequence, fallback lines,
refusals, how its transcript ends, switched)."""
import argparse, glob, json, os, re, subprocess, sys, time, uuid
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common_w1 as W  # noqa: E402
import claude_session as S  # noqa: E402

LABELS = ('dry', 'pilot', 'r1', 'r2', 'r3', 'hard', 'locked')  # hard, locked (2026-11-09): w1_setup.py a6-papers lays them down
# the pin; no gitStatus in any agent's context; memory off (the owner's decision, 2026-11-01); and wait for the
# workflow: print mode stops background tasks 10 min after the last turn (session.err, 2026-11-02: it stopped a
# 10-paper workflow after one read), unless CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
ENV_SET = {'DISABLE_AUTOUPDATER': '1', **W.PIN_ENV, **W.NO_GIT_CONTEXT_ENV, **W.NO_MEMORY_ENV,
           'CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS': '0'}


def launch_line(args):
    """The neutral launch line (A6_LAUNCH.md): the workflow's name, its args and the add command, nothing else."""
    return ('Run the saved workflow catlog-batch with these args, then python3 catlog.py add for its pmids in this folder: '
            + json.dumps(args))


def env():
    out = {k: os.environ[k] for k in S.ENV_KEEP if k in os.environ}
    out.update(ENV_SET)
    return out


def command(session_id):
    return [W.CLI, '-p', '--model', W.MODEL, '--effort', W.EFFORT, '--output-format', 'json', '--session-id', session_id]


def agent_rows(a6, session_id, base=None):
    """Every workflow agent of a launch session, with its models: [{label, pmid, role, launched, sequence, events,
    refusals, ending, switched, transcript}], and the launch session's own row (role 'launch'). ending: how its
    transcript ends (common_w1.transcript_models; since 2026-11-10), so a retry an API error started (the usage limit)
    is told from one a refusal started (common_w1.a6_refused). Read only. base: the folder holding the session's
    transcript (default Claude Code's project folder of a6)."""
    base = Path(base) if base else W.PROJECTS / W.project_slug(a6)
    rows = []
    for tr in sorted(glob.glob(str(base / session_id / 'subagents' / '**' / 'agent-*.jsonl'), recursive=True)):
        tr = Path(tr)
        meta = tr.with_name(tr.name[:-len('.jsonl')] + '.meta.json')
        try:
            desc = json.loads(meta.read_text()).get('description', '') if meta.exists() else ''
        except (OSError, json.JSONDecodeError):
            desc = ''
        task = ''
        with open(tr, errors='replace') as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get('type') == 'user':
                    c = (d.get('message') or {}).get('content')
                    task = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c or [] if isinstance(x, dict))
                    break
        m = W.READ_TASK.search(task)  # the kit's pattern (human_review's misses catlog-copy's task for a paper with no PMID)
        pmid = m.group(1) if m else (desc.split(':')[-1] if ':' in desc else '')
        role = ('verify_missed' if re.search(r'Rows to check: \S+\.missed\.read\.json', task) else
                'verify' if 'prompts/verify.md' in task else 'read' if 'prompts/read.md' in task else 'other')
        launched = W.RETRY_MODEL if 'sonnet' in desc.lower() else W.MODEL
        sw, info = W.model_switch(tr, launched)
        rows.append({'label': desc or tr.stem, 'pmid': pmid, 'role': role, 'launched': launched,
                     'sequence': info['sequence'], 'events': info['events'], 'refusals': info['refusals'],
                     'ending': info['ending'], 'switched': sw, 'transcript': str(tr)})
    tr = base / f'{session_id}.jsonl'
    sw, info = W.model_switch(tr, W.MODEL)
    rows.append({'label': 'launch', 'pmid': '', 'role': 'launch', 'launched': W.MODEL, 'sequence': info['sequence'],
                 'events': info['events'], 'refusals': info['refusals'], 'ending': info['ending'], 'switched': sw,
                 'transcript': str(tr)})
    return rows


def session_ran(d):
    """Whether the session of a launch folder ran: the CLI wrote to session.json (its result) or session.err. The
    launcher opens both empty just before it starts the session, so empty or missing files mean it never started."""
    return any((Path(d) / f).exists() and (Path(d) / f).stat().st_size for f in ('session.json', 'session.err'))


def launch_agents(d):
    """The agents of one launch folder (records/logs/A6-LABEL/<launch>/), read only: its agents.json; for a session that
    started but whose launcher did not see it to the end (killed, or the Mac restarted: launch.json, written before the
    session starts, names it, and there is no agents.json), the rows agent_rows reads from its transcripts, each marked
    'rebuilt'; [] where no session started (no launch.json naming one, as after a claim that failed, or one named whose
    transcript and session folder are not on disk and whose session.json and session.err are empty: session_ran); None
    where its agents cannot be accounted for: a session was started that no launch.json names (session.json alone: before
    2026-11-10 the launcher named the session only at the end), or the named session ran (session_ran) and its transcript
    and session folder are gone (moved by /archive, or removed by Claude Code's 30-day cleanup)."""
    d = Path(d)
    if (d / 'agents.json').exists():
        return json.loads((d / 'agents.json').read_text())
    try:
        rec = json.loads((d / 'launch.json').read_text())
    except (OSError, json.JSONDecodeError):
        rec = {}
    sid = rec.get('session_id')
    if not sid:
        return None if (d / 'session.json').exists() else []
    tr = Path(rec.get('transcript') or W.transcript_path(rec.get('cwd') or '', sid))
    if not (tr.exists() or tr.with_suffix('').is_dir()):
        return None if session_ran(d) else []
    return [{**r, 'rebuilt': True} for r in agent_rows(rec.get('cwd'), sid, base=tr.parent)]


def recover(ev, label, launch):
    """A launch killed on the way (launch.json names its session, there is no agents.json: launch_agents rebuilds its
    agents from the session's transcripts) completed read only, as the launcher would have at the end: agents.json from
    launch_agents, model_switch.json from record_models for the launch's papers (a killed redo's papers are no longer
    redo_pending for good, a killed launch's switch is redo_pending, not an exit), and launch.json completed ('recovered',
    the CLI's result when session.json holds one, the agents and switched agents). Nothing is started, claimed or
    changed in catlog-copy. Refused for a launch that needs nothing (agents.json exists) or cannot be accounted for
    (launch_agents None). w1_setup.py reset-a6 refuses while a launch is in this state."""
    log_dir = W.eval_paths(ev)['logs'] / f'A6-{label}'
    d = log_dir / launch
    if not W.A6_LAUNCH.fullmatch(launch) or not d.is_dir():
        sys.exit(f'no launch folder {d}')
    if (d / 'agents.json').exists():
        sys.exit(f'{d / "agents.json"} exists: the launch was seen to the end, nothing to recover')
    try:
        rec = json.loads((d / 'launch.json').read_text())
    except (OSError, json.JSONDecodeError):
        sys.exit(f'{d}: no launch.json naming a session (a launcher before 2026-11-10, or a claim that failed)')
    if not rec.get('session_id'):
        sys.exit(f'{d}: its launch.json names no session')
    rows = launch_agents(d)
    if rows is None:
        sys.exit(f'{d}: its session ran and its transcript is gone: its agents cannot be accounted for')
    W.write_json(d / 'agents.json', rows)
    sw = record_models(log_dir, launch, [str(p) for p in rec.get('pmids') or []], rows) if rows else W.read_switches(log_dir)
    try:
        result = json.loads((d / 'session.json').read_text().strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError, OSError):
        result = None
    rec.update({'recovered': W.now(), 'result': result, 'agents': sum(1 for r in rows if r.get('role') != 'launch'),
                'switched_agents': [f"{r['label']} {r['sequence']}" for r in rows if r.get('switched')],
                'session_started': bool(rows)})
    W.write_json(d / 'launch.json', rec)
    pend = sorted((x for x, r in sw.items() if r.get('outcome') == 'redo_pending'), key=W.pmid_key)
    print(json.dumps({'run': f'A6-{label}', 'launch': launch, 'recovered': True, 'session_started': bool(rows),
                      'agents': rec['agents'], 'switched_agents': rec['switched_agents'], 'redo_pending': pend}, indent=1))
    return rows


def next_launch(log_dir, redo):
    if not redo and not (log_dir / 'main').exists():
        return 'main'
    if redo and not (log_dir / 'redo').exists():
        return 'redo'
    stem = 'redo-more' if redo else 'more'
    k = 1
    while (log_dir / f'{stem}-{k}').exists():
        k += 1
    return f'{stem}-{k}'


def record_models(log_dir, launch, pmids, rows):
    """model_switch.json per paper of this launch: redo_pending (a main or follow-up agent switched), excluded (a redo
    agent switched again), second_try_ok (the redo's agents kept their model); a paper a later launch of the same state
    read again without a switch is no longer pending (rerun_ok)."""
    switched = {}
    for r in rows:
        if r['pmid'] and r['switched']:
            switched.setdefault(r['pmid'], []).append(f"{r['label']} {r['sequence']}")
    d = W.read_switches(log_dir)
    redo = launch.startswith('redo')
    for p in pmids:
        old = d.get(p, {})
        if p in switched:
            outcome = 'excluded' if redo else 'redo_pending'
        elif redo:
            outcome = 'second_try_ok'
        elif old.get('outcome') == 'redo_pending':
            outcome = 'rerun_ok'
        else:
            continue
        d[p] = {'pmid': p, 'outcome': outcome, 'launch': launch, 'time': W.now(), 'agents': switched.get(p, []),
                'history': old.get('history', []) + ([{k: old[k] for k in ('outcome', 'launch', 'agents') if k in old}]
                                                     if old else [])}
    W.write_json(log_dir / W.MODEL_SWITCH_FILE, d)
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('label', choices=LABELS)
    ap.add_argument('--pmids', nargs='*')
    ap.add_argument('--redo', action='store_true')
    ap.add_argument('--timeout', type=int, default=86400)
    ap.add_argument('--force', action='store_true', help='a follow-up launch may name papers catlog-copy finished already')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--recover', metavar='LAUNCH', help='complete the records of a launch killed on the way (no session '
                                                        'is started): agents.json, model_switch.json, launch.json')
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    ev = Path(a.eval)
    if a.recover:
        recover(ev, a.label, a.recover)
        return
    P = W.eval_paths(ev)
    a6 = P['a6']
    run = f'A6-{a.label}'
    log_dir = P['logs'] / run
    kept = P['runs'] / run
    args_file = P['orders'] / f'{run}.args.json'
    if not args_file.exists():
        sys.exit(f'no {args_file} (w1_setup.py setup)')
    pin = W.a6_pin_problems(ev) if a.label in W.LATER_LABELS else []  # read on the frozen copy, or not at all
    if pin:
        sys.exit(f'refused: {"; ".join(pin)}: the sets after the W1 rounds are read on the frozen copy only')
    base_args = json.loads(args_file.read_text())
    if Path(base_args['root']) != a6:
        sys.exit(f"{args_file} names {base_args['root']}, not {a6}: run w1_setup.py setup")
    if a.redo:
        if not kept.exists():
            sys.exit(f'{kept} does not exist: keep the run first (w1_setup.py reset-a6 {a.label})')
        if (kept / 'redo').exists():
            sys.exit(f'{kept / "redo"} exists: the redo was kept already')
        pending = sorted((p for p, r in W.read_switches(log_dir).items() if r.get('outcome') == 'redo_pending'), key=W.pmid_key)
        pmids = a.pmids or pending
        if not pmids:
            sys.exit('no paper waits for a redo (model_switch.json has no redo_pending)')
        if not a.pmids and (log_dir / 'redo').exists():
            sys.exit('the redo was launched already: a follow-up inside it is --redo --pmids P ...')
    else:
        if kept.exists():
            sys.exit(f'{kept} exists: this run was kept already (a redo is --redo)')
        pmids = a.pmids or [str(p) for p in base_args['pmids']]
        if not a.pmids and (log_dir / 'main').exists():
            sys.exit(f'{run} was launched already ({log_dir / "main"}): a follow-up is --pmids P ...')
    unknown = [p for p in pmids if p not in {str(x) for x in base_args['pmids']}]
    if unknown:
        sys.exit(f'not papers of {run}: {unknown[:5]}')
    launch = next_launch(log_dir, a.redo)
    follow_up = launch not in ('main', 'redo')
    st = {r['pmid']: r['status'] for r in W.read_tsv(a6 / 'papers.tsv')} if (a6 / 'papers.tsv').exists() else {}
    done = [p for p in pmids if follow_up and st.get(p) in W.DONE_A6]  # claim would read them again, and add merge both
    if done and not a.force:                                            # reads inside one kept run
        sys.exit(f'finished in catlog-copy already: {[f"{p} ({st[p]})" for p in done][:10]}: a follow-up launch would '
                 'read them again inside the same kept run (leave them out, or pass --force)')
    if launch in ('main', 'redo'):  # a fresh state: nothing added yet
        if (a6 / 'catalog.jsonl').exists() and (a6 / 'catalog.jsonl').stat().st_size:
            sys.exit('catlog-copy/catalog.jsonl is not empty: keep the previous run first (w1_setup.py reset-a6)')
        if not (a6 / W.RUN_MARK).exists():
            sys.exit(f'catlog-copy has no {W.RUN_MARK} (w1_setup.py setup or reset-a6 lays it down)')
        reads = [p for p in pmids if (a6 / 'work' / f'{p}.read.json').exists()]
        if reads:
            sys.exit(f'catlog-copy/work already has reads for {reads[:5]}')
    args = {**base_args, 'pmids': pmids}
    line = launch_line(args)
    problems = S.shown_problems(a6, line)
    if problems:
        sys.exit(f'refused: {problems}')
    sid = str(uuid.uuid4())
    cmd = command(sid)
    rec = {'run': run, 'launch': launch, 'cwd': str(a6), 'pmids': pmids, 'args': args, 'command': cmd,
           'env': sorted(env()), 'env_set': ENV_SET, 'session_id': sid,
           'transcript': str(W.PROJECTS / W.project_slug(a6) / f'{sid}.jsonl'), 'start': W.now(),
           'start_utc': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
           **({'force': True, 'read_again': done} if a.force else {})}  # finished papers this launch reads again
    if a.dry_run:  # prints only: no file, so the real launch is not blocked
        print(json.dumps({'launch': launch, 'cwd': str(a6), 'command': cmd, 'env': rec['env'], 'env_set': ENV_SET,
                          'launch_line': line, 'eval_words_in_line_or_cwd': problems,
                          **({'force': True, 'read_again': done} if a.force else {})}, indent=1))
        return
    d = log_dir / launch
    d.mkdir(parents=True, exist_ok=False)
    (d / 'launch_line.txt').write_text(line)
    if follow_up:  # A6_LAUNCH.md step 3: the papers' work files to work/old/, status reading, a fresh claim record
        r = subprocess.run([sys.executable, '-B', str(W.W1 / 'w1_setup.py'), 'claim', *pmids, '--eval', str(ev)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'claim failed: {r.stdout}{r.stderr}')
    S.versions(log_dir, f'before {launch}')
    W.write_json(d / 'launch.json', rec)  # before the session starts: its id and transcript are on record if this launcher
    t0 = time.time()                      # is killed (launch_agents; the audit finds the session), completed at the end
    with open(d / 'session.json', 'w') as out, open(d / 'session.err', 'w') as err:
        p = subprocess.Popen(cmd, cwd=str(a6), stdin=subprocess.PIPE, stdout=out, stderr=err, env=env(),
                             start_new_session=True, text=True)
        try:
            p.communicate(line, timeout=a.timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            S._kill(p)
    try:
        result = json.loads((d / 'session.json').read_text().strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError, OSError):
        result = None
    rows = agent_rows(a6, sid)
    W.write_json(d / 'agents.json', rows)
    sw = record_models(log_dir, launch, pmids, rows)
    S.versions(log_dir, f'after {launch}')
    rec.update({'end': W.now(), 'seconds': round(time.time() - t0, 1), 'exit_code': p.returncode, 'timed_out': timed_out,
                'result': result, 'agents': len(rows) - 1,
                'switched_agents': [f"{r['label']} {r['sequence']}" for r in rows if r['switched']]})
    W.write_json(d / 'launch.json', rec)
    pend = sorted((x for x, r in sw.items() if r.get('outcome') == 'redo_pending'), key=W.pmid_key)
    excl = sorted((x for x, r in sw.items() if r.get('outcome') == 'excluded'), key=W.pmid_key)
    print(json.dumps({'run': run, 'launch': launch, 'exit_code': p.returncode, 'timed_out': timed_out,
                      'is_error': (result or {}).get('is_error'), 'agents': len(rows) - 1,
                      'switched_agents': rec['switched_agents'], 'redo_pending': pend, 'excluded': excl,
                      'result': str((result or {}).get('result'))[:800]}, indent=1))
    if launch.startswith('redo'):
        print(f'next: python3 -B tools/w1/w1_setup.py reset-a6 {a.label} --redo, then w1_audit.py {run}')
    else:
        print(f'next: stops or papers left reading -> run_a6.py {a.label} --pmids ...; then w1_setup.py reset-a6 '
              f'{a.label} and w1_audit.py {run}' + (f'; then run_a6.py {a.label} --redo for {pend}' if pend else ''))


if __name__ == '__main__':
    main()
