#!/usr/bin/env python3
"""Run the broad test's judges (PLAN.md "Judging"): one headless Claude Code session per job of RUN/jobs.json, each
started in its paper's folder, LANES at a time, then the replacements the plan's rule calls for.

  python3 -I -B run_judges.py RUN OUTDIR [--start-at HH:MM] [--lanes N] [--only LABEL...]

The launch line is the test kit's (kinetics-reading/code/tools/w1/claude_session.py): its command-line tool clone, model
pinned with no fallback, no git context, no memory, no CLAUDE.md files, MCP off, web tools and sub-agents denied, and
the CatLog, kit and home folders unreadable. Each session gets its own TMPDIR (added as a folder it may use) for page
images, removed when it ends. A session ending on the account's usage limit is not a try: every lane waits and the job
runs again. A job whose check file is missing or does not give every judged id a verdict runs once more; a second
failure leaves the paper to be replaced by the next paper of order.txt (PLAN.md "Papers"). Records: RUN/logs/,
RUN/progress.tsv; each finished check file is copied to RUN/judged/<PMID>/ with its task file."""
import importlib.util, json, os, re, shutil, signal, subprocess, sys, threading, time, uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = str(Path.home())
CLI = HOME + '/Documents/kinetics-reading/cli/2.1.325/claude.app/Contents/MacOS/claude'  # a clone of the app's 2.1.325, beside the kit's 2.1.317 (which does not know claude-fable-5-2)
MODEL, EFFORT = 'claude-fable-5-2', 'high'
LANES, TIMEOUT, TRIES, TARGET = 5, 2700, 2, 300
TMPROOT = Path('/private/tmp/pages_tmp_20261118')
ALLOWED = 'Read Write Glob Grep Bash(pdftoppm:*) Bash(pdftotext:*) Bash(mktemp:*) Bash(ls:*) Bash(mkdir:*)'
DENY = ['WebFetch', 'WebSearch', 'Agent', 'Task', 'Bash(curl:*)', 'Bash(wget:*)', 'Bash(python3:*)', 'Bash(python:*)',
        'Bash(git:*)', 'Bash(find:*)', 'Bash(cat:*)'] + [f'Read(/{d}/**)' for d in (
        HOME + '/Documents', HOME + '/Downloads', HOME + '/Library', HOME + '/.claude', '/private/tmp/claude-501', '/tmp/claude-501')]
ENV_KEEP = ('HOME', 'USER', 'LOGNAME', 'PATH', 'SHELL', 'LANG', 'LC_ALL', 'LC_CTYPE', 'TERM', '__CF_USER_TEXT_ENCODING')
ENV_SET = {'DISABLE_AUTOUPDATER': '1', 'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1', 'CLAUDE_CODE_DISABLE_CLAUDE_MDS': '1',
           'ENABLE_CLAUDEAI_MCP_SERVERS': 'false', 'CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK': '1',
           'CLAUDE_CODE_NO_MODEL_FALLBACK': '1', 'CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS': '1'}
REFUSAL_RX = re.compile(r"(?i)\brefus|safeguards stopped|usage polic")
LIMIT_RX = re.compile(r"(?i)hit your .{0,20}limit|usage limit|weekly limit|rate.limit|overloaded|resets \d")
VERDICTS = {'measured_here_at_this_scale', 'measured_here_other_scale', 'as_printed_but_misprint', 'corrected_misprint',
            'repeat_of_one_printed_value', 'not_this_metric', 'credited_to_earlier_work', 'not_found_in_paper', 'cannot_decide'}
LOCK = threading.Lock()
PAUSE = {'until': 0.0}
BRAKE = {'in_a_row': 0, 'stop': False}  # 6 failed jobs in a row stop new starts; more than 20 failed papers replace nothing


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def log_line(run, *cols):
    with LOCK:
        f = run / 'progress.tsv'
        new = not f.exists()
        with open(f, 'a') as fh:
            if new:
                fh.write('time\tlabel\tattempt\tstatus\tseconds\tcost_usd\tnote\n')
            fh.write('\t'.join(str(c) for c in (now(), *cols)) + '\n')


def wanted_ids(task_file):
    t = json.loads(Path(task_file).read_text())
    return {x['id'] for L in ('A', 'B') for x in t.get(f'reading_{L}', []) if x.get('judge')}


def check_ok(check_file, task_file):
    try:
        d = json.loads(Path(check_file).read_text())
        got = {str(v.get('id')) for v in d.get('verdicts', []) if v.get('verdict') in VERDICTS}
    except (OSError, json.JSONDecodeError, AttributeError):
        return False
    return wanted_ids(task_file) <= got


def task_of(job):
    c = job['check']
    return 'task.json' if re.fullmatch(r'check[12]\.json', c) else 'task_' + c.split('_', 1)[1]


def transcript_models(cwd, sid):
    """The models of a session's own replies, from its transcript (Claude Code's helper calls are not in it)."""
    f = Path(HOME) / '.claude' / 'projects' / re.sub(r'[^A-Za-z0-9]', '-', str(cwd)) / f'{sid}.jsonl'
    models = set()
    if f.exists():
        for line in open(f):
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            m = (e.get('message') or {}).get('model') if e.get('type') == 'assistant' else None
            if m and m != '<synthetic>':
                models.add(m)
    return sorted(models), str(f)


def run_one(job, run, outdir):
    if BRAKE['stop']:
        return 'skipped'
    st = run_one_(job, run, outdir)
    with LOCK:
        BRAKE['in_a_row'] = BRAKE['in_a_row'] + 1 if st == 'failed' else (0 if st == 'ok' else BRAKE['in_a_row'])
        if BRAKE['in_a_row'] >= 6:
            BRAKE['stop'] = True
    return st


def run_one_(job, run, outdir):
    cwd = Path(outdir) / job['pmid']
    check, task = cwd / job['check'], cwd / task_of(job)
    safe = re.sub(r'[^A-Za-z0-9]+', '_', job['label'])
    saved = run / 'judged' / job['pmid'] / job['check']
    if not check.exists() and saved.exists() and task.exists():
        shutil.copyfile(saved, check)  # resumed: the verdict finished earlier
    attempt, tries, waits, transient = 0, 0, 0, 0
    while tries < TRIES:
        if check_ok(check, task):
            break
        wait = PAUSE['until'] - time.time()
        if wait > 0:
            time.sleep(wait)
            continue
        if waits > 36:  # twelve hours of usage-limit waits: stop, never replace for this
            log_line(run, job['label'], attempt, 'gave_up_usage_limit', 0, '', '')
            return 'limit'
        attempt += 1
        sid = str(uuid.uuid4())
        tmp = TMPROOT / f'{safe}_{attempt}'
        tmp.mkdir(parents=True, exist_ok=True)
        cmd = [CLI, '-p', '--model', MODEL, '--effort', EFFORT, '--setting-sources', 'project', '--strict-mcp-config',
               '--permission-mode', 'dontAsk', '--allowedTools', ALLOWED, '--disallowedTools', ' '.join(DENY),
               '--add-dir', str(cwd), str(tmp), '--session-id', sid, '--output-format', 'json']
        env = {k: os.environ[k] for k in ENV_KEEP if k in os.environ}
        env.update(ENV_SET)
        env['TMPDIR'] = str(tmp)
        rec = {'label': job['label'], 'attempt': attempt, 'pmid': job['pmid'], 'cwd': str(cwd), 'session_id': sid,
               'command': cmd, 'env_set': ENV_SET, 'start': now()}
        t0 = time.time()
        p = subprocess.Popen(cmd, cwd=str(cwd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=env, start_new_session=True, text=True)
        try:
            out, err = p.communicate(job['prompt'], timeout=TIMEOUT)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(p.pid, sig)
                    p.wait(timeout=15)
                    break
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    continue
            out, err = p.communicate()
        try:
            res = json.loads(out.strip().splitlines()[-1]) if out.strip() else None
        except (json.JSONDecodeError, IndexError):
            res = None
        shutil.rmtree(tmp, ignore_errors=True)
        text = str((res or {}).get('result') or '') + ' ' + (err or '')[-500:]
        rec.update({'end': now(), 'seconds': round(time.time() - t0, 1), 'exit_code': p.returncode, 'timed_out': timed_out,
                    'result': res, 'stderr_tail': (err or '')[-1500:],
                    'models': sorted(((res or {}).get('modelUsage') or {}).keys())})
        rec['reply_models'], rec['transcript'] = transcript_models(cwd, sid)
        switched = any(m != MODEL for m in rec['reply_models'])
        rec['switched'] = switched
        ok = check_ok(check, task) and not switched
        cost = (res or {}).get('total_cost_usd')
        (run / 'logs').mkdir(parents=True, exist_ok=True)
        (run / 'logs' / f'{safe}.a{attempt}.json').write_text(json.dumps(rec, indent=1, default=str))
        refused = bool((res or {}).get('safety_stops')) or bool(REFUSAL_RX.search(text))
        rec['refused'] = refused
        (run / 'logs' / f'{safe}.a{attempt}.json').write_text(json.dumps(rec, indent=1, default=str))
        if not ok and not switched and not refused and (LIMIT_RX.search(text) or (res or {}).get('api_error') == 'usage_limit_reached'):
            waits += 1
            with LOCK:
                PAUSE['until'] = max(PAUSE['until'], time.time() + 1200)
            log_line(run, job['label'], attempt, 'usage_limit_wait', rec['seconds'], cost, text.strip()[:120])
            continue  # not a try: the job runs again after the wait
        if not ok and not switched and not refused and not timed_out and transient < 6 and (res is None or (res or {}).get('is_error')):
            transient += 1  # a dropped connection, a closed lid, a server error: not a try
            time.sleep(300)
            log_line(run, job['label'], attempt, 'transient_wait', rec['seconds'], cost, text.strip()[:120])
            continue
        tries += 1
        if check.exists() and not ok:
            shutil.move(str(check), str(run / 'logs' / f'{safe}.a{attempt}.{"switched" if switched else "incomplete"}.json'))
        log_line(run, job['label'], attempt, 'ok' if ok else ('model_switch' if switched else ('refused' if refused else 'failed')), rec['seconds'], cost,
                 ('models ' + ','.join(rec['reply_models'])) if ok else text.strip()[:160])
        if ok:
            break
    if not check_ok(check, task):
        return 'failed'
    dest = run / 'judged' / job['pmid']
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(check, dest / job['check'])
    shutil.copyfile(task, dest / task.name)
    return 'ok'


def probe(run):
    """One tiny call in the judges' clean environment: the account answers on MODEL. Waits while it is at its limit."""
    for k in range(48):
        tmp = TMPROOT / 'probe'
        tmp.mkdir(parents=True, exist_ok=True)
        env = {x: os.environ[x] for x in ENV_KEEP if x in os.environ}
        env.update(ENV_SET)
        env['TMPDIR'] = str(tmp)
        p = subprocess.run([CLI, '-p', '--model', MODEL, '--effort', EFFORT, '--setting-sources', 'project', '--strict-mcp-config',
                            '--permission-mode', 'dontAsk', '--output-format', 'json'], cwd=str(tmp), input='Reply with the single word OK.',
                           capture_output=True, text=True, env=env, timeout=300)
        try:
            res = json.loads(p.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            res = {}
        a = subprocess.run([CLI, 'auth', 'status'], cwd=str(tmp), capture_output=True, text=True, env=env, timeout=60)
        try:
            auth = json.loads(a.stdout)
        except json.JSONDecodeError:
            auth = {}
        shutil.rmtree(tmp, ignore_errors=True)
        rec = {'time': now(), 'is_error': res.get('is_error'), 'result': str(res.get('result'))[:120],
               'models': sorted((res.get('modelUsage') or {}).keys()), 'cost_usd': res.get('total_cost_usd'),
               'logged_in': auth.get('loggedIn'), 'auth_method': auth.get('authMethod'), 'subscription': auth.get('subscriptionType')}
        with open(run / 'probe.jsonl', 'a') as fh:
            fh.write(json.dumps(rec) + '\n')
        if res and not res.get('is_error') and MODEL in rec['models']:
            print('probe ok:', rec, flush=True)
            return True
        print('probe not ready:', rec['result'], flush=True)
        time.sleep(600)
    return False


def build():
    spec = importlib.util.spec_from_file_location('build', HERE / 'build.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    a = sys.argv[1:]
    run, outdir = Path(a[0]).resolve(), Path(a[1]).resolve()
    lanes = int(a[a.index('--lanes') + 1]) if '--lanes' in a else LANES
    only = set(a[a.index('--only') + 1:]) if '--only' in a else None
    if '--start-at' in a:
        hh, mm = map(int, a[a.index('--start-at') + 1].split(':'))
        t = datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)
        if t.timestamp() > time.time():
            print('waiting until', t.isoformat(timespec='minutes'), flush=True)
            time.sleep(t.timestamp() - time.time())
    TMPROOT.mkdir(parents=True, exist_ok=True)
    if not probe(run):
        print('the judges\' account did not answer for eight hours: nothing started', flush=True)
        sys.exit(5)
    jobs = json.loads((run / 'jobs.json').read_text())['jobs']
    if only:
        jobs = [j for j in jobs if j['label'] in only]
    first, rest = jobs[:1], jobs[1:]
    if first and run_one(first[0], run, outdir) != 'ok':  # one job alone first: a broken launch stops here, not 200 times
        print('the first job did not finish: see', run / 'progress.tsv', flush=True)
        sys.exit(2)
    with ThreadPoolExecutor(max_workers=lanes) as ex:
        status = dict(zip([j['label'] for j in rest], ex.map(lambda j: run_one(j, run, outdir), rest)))
    status[first[0]['label']] = 'ok'
    if only:
        return
    if BRAKE['stop']:
        print('stopped: 6 jobs failed in a row; see', run / 'progress.tsv', flush=True)
        sys.exit(3)
    # the plan's replacement rule: a paper whose judge failed twice is replaced by the next paper of the order
    B = build()
    order = (HERE / 'order.txt').read_text().split()
    main_jobs = [j for j in jobs if not j['label'].startswith('second:')]
    failed = sorted({j['pmid'] for j in main_jobs if status.get(j['label']) == 'failed'}, key=order.index)
    blocked = sorted({j['pmid'] for j in main_jobs if status.get(j['label']) == 'limit'}, key=order.index)
    used, nxt, replaced, k = set(order[:TARGET]), TARGET, [], 0
    if len(failed) > 20:
        (run / 'sample.json').write_text(json.dumps({'failed': failed, 'note': 'more than 20 failed: nothing replaced'}, indent=1))
        print('stopped:', len(failed), 'papers failed; nothing replaced', flush=True)
        sys.exit(4)
    while failed and not BRAKE['stop']:
        new = []
        for p in failed:
            while nxt < len(order) and order[nxt] in used:
                nxt += 1
            if nxt >= len(order):
                break
            used.add(order[nxt])
            new.append(order[nxt])
            replaced.append({'failed': p, 'replacement': order[nxt]})
        if not new:
            break
        k += 1
        B.tasks(outdir, run, new, jobs_name=f'jobs_replacements_{k}.json')
        more = [j for j in json.loads((run / f'jobs_replacements_{k}.json').read_text())['jobs'] if not j['label'].startswith('second:')]
        with ThreadPoolExecutor(max_workers=lanes) as ex:
            st2 = dict(zip([j['label'] for j in more], ex.map(lambda j: run_one(j, run, outdir), more)))
        failed = sorted({j['pmid'] for j in more if st2[j['label']] == 'failed'}, key=order.index)
        blocked += sorted({j['pmid'] for j in more if st2[j['label']] == 'limit'}, key=order.index)
    gone = {r['failed'] for r in replaced}
    analysed = [p for p in sorted(used, key=order.index) if p not in gone and p not in blocked]
    (run / 'sample.json').write_text(json.dumps({'analysed': analysed, 'replaced': replaced, 'waiting_on_the_usage_limit': blocked,
                                                 'time': now()}, indent=1))
    print('done:', len(analysed), 'papers analysed,', len(replaced), 'replaced,', len(blocked), 'waiting on the usage limit', flush=True)


if __name__ == '__main__':
    main()
