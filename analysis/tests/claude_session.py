"""One headless Claude Code session per paper and step, for W1's plain arms (A0, A2) and adjudicators.

Neither arm may see CatLog's instructions, so every session is a separate `claude -p` process run in a folder with no
CLAUDE.md (plain/<PMID>/ or adj/<PMID>/, holding only that paper's inputs), on the command-line tool named in
common_w1.CLI, with:
  --model claude-opus-5-5 --effort max --setting-sources project --strict-mcp-config --permission-mode dontAsk
  --allowedTools "Read Write Glob Grep Bash(pdftoppm:*) Bash(pdftotext:*) Bash(python3:*) Bash(ls:*) Bash(mkdir:*)"
  --output-format json
plus three additions recorded in the manifest: --session-id (a fresh UUID, so the transcript's path is known),
--add-dir for the session's output folder and /tmp (so writing the output and viewing page images never needs a
permission prompt, which dontAsk would refuse), and --disallowedTools for web tools, curl, wget and the folders an agent
must not open (a guard; w1_audit.py is the check). The prompt goes in on stdin (the variadic options would swallow a
positional prompt). The environment is rebuilt from a short list (HOME, USER, PATH, ...) with DISABLE_AUTOUPDATER=1 and
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1: nothing of a calling Claude Code session (CLAUDECODE, ANTHROPIC_BASE_URL,
CLAUDE_CODE_*) reaches the session. Authentication is the owner's own `claude auth login`; this file never handles
credentials.

Retry (RUN.md §2, as catlog-batch.js again()): a session whose output is missing or fails its check, or that ends in
an error or a timeout, runs once more on claude-sonnet-5-5; the first attempt's file is kept in logs/. Lanes stop
taking new work after DEAD_STOP failed steps in a row (the usage limit).

Isolation added by the review (REVIEW.md 1.2-1.7): CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 (Claude Code's own switch: no
CLAUDE.md of any folder, no rules, no nested memory; without it 2.1.309 walks every parent folder up to /) and
ENABLE_CLAUDEAI_MCP_SERVERS=false; Agent/Task denied; Read denied for every eval part a session does not need, other
sessions' scratch names in /tmp, and the session records and scratchpads of production CatLog, realkcat, A6, the eval
branch and the other kind of eval session; the session folder is checked before and after (a new file is moved to
logs/<run>/stray/ and recorded); the session's non-image scratch (/tmp/<RUN>-<PMID>-*) is moved to
logs/<run>/scratch/<label>/ when it ends, so no later session finds it.

Dry-run fixes (2026-11-01): the model pin (common_w1.PIN_ENV: CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK=1 and
CLAUDE_CODE_NO_MODEL_FALLBACK=1, so a safety-classifier refusal no longer swaps claude-opus-5-5 for claude-opus-5 inside
the session); every session's transcript is read when it ends, and a session that shows any model other than the one it
was started with (or a model-fallback line) runs once more on that model ('<label>.a1b' after '<label>.a1'), both
records kept; a second switch leaves the step without output and the paper out of every arm's paired analysis
(logs/<run>/model_switch.json, outcome 'excluded'; the runners skip it afterwards). A session whose folder, prompt or
added folders contain an evaluation word (common_w1.EVAL_WORDS) is refused before it starts.

Review of the dry-run fixes (2026-11-01): a step that runs again (a resumed run, the end-of-round repeat of a failed
paper-run, --force) first moves its earlier records to logs/<run>/earlier/<step>/<k>/ (keep_earlier: they were
overwritten before, and the audit never saw those sessions), and a switch in an earlier invocation of the step counts as
its first: the next switch excludes it (no second once-more)."""
import json, os, re, shutil, signal, subprocess, threading, time, uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common_w1 as W

ENV_KEEP = ('HOME', 'USER', 'LOGNAME', 'PATH', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'LC_CTYPE', 'TERM',
            '__CF_USER_TEXT_ENCODING')
ENV_SET = {'DISABLE_AUTOUPDATER': '1', **W.NO_MEMORY_ENV, 'CLAUDE_CODE_DISABLE_CLAUDE_MDS': '1',
           'ENABLE_CLAUDEAI_MCP_SERVERS': 'false', **W.PIN_ENV}
TMP_DIRS = ('/tmp', '/private/tmp')
BASE_DENY = ('WebFetch', 'WebSearch', 'Bash(curl:*)', 'Bash(wget:*)', 'Agent', 'Task')
SCRATCH_MAX = 20 * 1024 * 1024  # a non-image scratch file above this stays in /tmp (listed), so logs/ stays small


def clean_env():
    env = {k: os.environ[k] for k in ENV_KEEP if k in os.environ}
    env.update(ENV_SET)
    return env


def deny_read(*folders):
    """Read rules for whole folders, in the permission syntax for absolute paths (//abs/path/**)."""
    return ['Read(/' + str(Path(f)) + '/**)' for f in folders]


def deny_read_files(*files):
    return ['Read(/' + str(Path(f)) + ')' for f in files]


DOWNLOADS = Path.home() / 'Downloads'  # the owner's downloads: other groups' answer keys and their models' extractions
# for the held-out papers sit in Downloads/data (review of the locked set, 2026-11-09)


def downloads_deny(*tools):
    """Rules closing the owner's downloads folder to these tools (Read; Edit and Write where a builder writes those),
    for the sessions of the copy and of the locked set; the finished runs' lists are as they were."""
    return [f'{t}(/{DOWNLOADS}/**)' for t in tools]


def deny_globs(tool, folder, files):
    """Rules for the files at the top of a folder by extension (Read(//<folder>/*.md)), so that no rule spells a file's
    name (A6's settings.local.json is a file its agents could open)."""
    exts = sorted({Path(f).suffix for f in files if Path(f).suffix} | {'.md', '.json'})
    return [f'{tool}(/{Path(folder)}/*{e})' for e in exts] + [f'{tool}(/{f})' for f in files if not Path(f).suffix]


def other_scratch_deny(own):
    """Read rules for every other eval session's /tmp scratch names (own: the session's label, e.g. 'A2-r1-readA',
    'W1adj-j1-c01'; its own label family stays readable)."""
    out = []
    for lab in W.scratch_labels():
        if own == lab or own.startswith(lab + '-'):
            continue
        out += [f'Read(//private/tmp/{lab}-*)', f'Read(//tmp/{lab}-*)']
    return out


def record_slugs(kind, ev=None):
    """Claude Code project-folder names (patterns) of the sessions that hold reads, verdicts or instructions for these
    papers: production CatLog and its worktrees, realkcat, A6, the eval branch's worktree, sessions opened in the eval
    folder itself, every session of the first layout (catlog-eval/, the dry run of 2026-11-01), and the other kind of
    eval session (kind 'plain': the adjudicators' folders; 'adj': the plain ones; 'a6': both)."""
    ev = Path(ev or W.EVAL)
    P = W.eval_paths(ev)
    # '-Users-<user>-Documents-catlog-*' covers the main folder, its worktrees and the first layout (catlog-eval/)
    # in one rule that names neither (catlog-copy/.claude/settings.local.json is a file A6's agents could open)
    slugs = [W.project_slug(W.MAIN.parent) + '-catlog-*', W.project_slug(W.REALKCAT) + '*',
             W.project_slug(P['repo']) + '*', W.project_slug(ev),
             W.project_slug(W.CLAUDE_TMP) + '-' + W.project_slug(W.MAIN.parent) + '-catlog-*']  # sessions started in a CatLog chat's scratchpad
    if kind != 'a6':
        slugs.append(W.project_slug(P['a6']) + '*')
    if kind in ('plain', 'a6'):
        slugs.append(W.project_slug(P['adj']) + '-*')
    if kind in ('adj', 'a6'):
        slugs.append(W.project_slug(P['plain']) + '-*')
    return slugs


def records_deny(kind, ev=None):
    """Read rules for those sessions' records (~/.claude/projects/<slug>/: transcripts, tool results, memory) and
    scratchpads (/private/tmp/claude-<uid>/<slug>/), and for Codex's sessions (~/.codex)."""
    out = []
    for s in record_slugs(kind, ev):
        for base in (W.PROJECTS, W.CLAUDE_TMP, Path('/tmp') / W.CLAUDE_TMP.name):
            out.append(f'Read(/{base}/{s}/**)')
    return out + deny_read(Path.home() / '.codex')


def check_folders(cwds):
    """Before a run: refuse when any session folder holds more than its inputs or has an instruction file above it."""
    problems = [x for c in sorted(set(map(str, cwds))) for x in W.folder_problems(c)]
    if problems:
        raise SystemExit(f'{len(problems)} session folder problems (REVIEW.md 1.2, 1.6), e.g.: ' + '; '.join(problems[:5]))


def collect_scratch(prefix, dest, root=W.TMP, keep_name=None):
    """Move a finished session's non-image scratch (root/<prefix>*: scripts, notes, drafts) into dest, so that no later
    session of another arm, run or judge can open it; page images stay (they show the paper only), as do files above
    SCRATCH_MAX. keep_name: only entries whose name it accepts. Returns (moved, left) as paths relative to root."""
    moved, left = [], []
    for p in sorted(Path(root).glob(prefix + '*')):
        if keep_name is not None and not keep_name(p.name):
            continue
        files = [p] if (p.is_file() or p.is_symlink()) else sorted(f for f in p.rglob('*') if f.is_file() or f.is_symlink())
        for f in files:
            rel = f.relative_to(root)
            if f.suffix.lower() in W.IMAGE_EXT or (not f.is_symlink() and f.stat().st_size > SCRATCH_MAX):
                left.append(str(rel))
                continue
            t = Path(dest) / rel
            t.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(f), str(t))
                moved.append(str(rel))
            except OSError:
                left.append(str(rel))
    return moved, left


def command(model, session_id, add_dirs=(), deny=()):
    cmd = [W.CLI, '-p', '--model', model, '--effort', W.EFFORT, '--setting-sources', 'project', '--strict-mcp-config',
           '--permission-mode', 'dontAsk', '--allowedTools', W.ALLOWED_TOOLS]
    deny = list(BASE_DENY) + [d for d in deny if d not in BASE_DENY]
    cmd += ['--disallowedTools', ' '.join(deny)]
    dirs = [str(d) for d in add_dirs] + [d for d in TMP_DIRS if d not in add_dirs]
    cmd += ['--add-dir', *dirs]
    cmd += ['--session-id', session_id, '--output-format', 'json']
    return cmd


def cli_version():
    try:
        r = subprocess.run([W.CLI, '--version'], capture_output=True, text=True, env=clean_env(), timeout=60)
        return r.stdout.strip() or r.stderr.strip()
    except (OSError, subprocess.SubprocessError) as e:
        return f'unavailable: {type(e).__name__}'


def _kill(p):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(p.pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            p.wait(timeout=15)
            return
        except subprocess.TimeoutExpired:
            continue


def run_session(prompt, cwd, model, out_file, log_dir, label, add_dirs=(), deny=(), timeout=3600, dry=False,
                scratch=None):
    """Run one session; returns its record (also written to log_dir/<label>.json, the prompt to <label>.prompt.txt).
    scratch: the session's /tmp scratch prefix (<RUN>-<PMID>-), collected into log_dir/scratch/<label>/ at the end."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    sid = str(uuid.uuid4())
    cmd = command(model, sid, add_dirs, deny)
    rec = {'label': label, 'model': model, 'cwd': str(cwd), 'out': str(out_file), 'session_id': sid,
           'transcript': str(W.transcript_path(cwd, sid)), 'command': cmd, 'prompt_sha256': W.sha256_bytes(prompt.encode()),
           'env': sorted(clean_env()), 'env_set': dict(ENV_SET), 'scratch_prefix': scratch, 'start': W.now()}
    (log_dir / f'{label}.prompt.txt').write_text(prompt)
    if dry:
        rec['dry_run'] = True
        return rec
    problems = W.folder_problems(cwd) + shown_problems(cwd, prompt, add_dirs)
    if problems:  # never start a session in a folder that is not clean: a failed attempt (the runners check up front too)
        rec.update({'end': W.now(), 'refused': problems, 'exit_code': None, 'timed_out': False, 'result': None})
        W.write_json(log_dir / f'{label}.json', rec)
        return rec
    before = set(os.listdir(cwd))
    t0 = time.time()
    timed_out = False
    p = subprocess.Popen(cmd, cwd=str(cwd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=clean_env(), start_new_session=True, text=True)
    try:
        out, err = p.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill(p)
        out, err = p.communicate()
    result = None
    try:
        result = json.loads(out.strip().splitlines()[-1]) if out.strip() else None
    except (json.JSONDecodeError, IndexError):
        result = None
    rec.update({'end': W.now(), 'seconds': round(time.time() - t0, 1), 'exit_code': p.returncode, 'timed_out': timed_out,
                'stdout_tail': '' if result is not None else (out or '')[-2000:], 'stderr_tail': (err or '')[-2000:],
                'result': result})
    stray = sorted(set(os.listdir(cwd)) - before)
    if stray:  # a file the session left in its input folder: moved out of every later session's view (audit: break)
        rec['stray'] = stray
        for n in stray:
            t = log_dir / 'stray' / label / n
            t.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(Path(cwd) / n), str(t))
            except OSError as e:
                rec.setdefault('stray_unmoved', []).append(f'{n}: {type(e).__name__}')
    if scratch:
        rec['scratch_moved'], rec['scratch_left'] = collect_scratch(scratch, log_dir / 'scratch' / label)
    tr = Path(rec['transcript'])
    if tr.exists():
        rec['transcript_sha256'] = W.sha256(tr)
        rec['transcript_bytes'] = tr.stat().st_size
    rec['switched'], rec['models'] = W.model_switch(tr, model)
    W.write_json(log_dir / f'{label}.json', rec)
    return rec


def shown_problems(cwd, prompt, add_dirs=()):
    """Evaluation words in what a session is shown: its folder, its prompt and its added folders (common_w1.EVAL_WORDS)."""
    out = []
    for what, text in [('cwd', str(cwd)), ('prompt', prompt)] + [('add-dir', str(d)) for d in add_dirs]:
        hits = W.eval_word_hits(text)
        if hits:
            out.append(f'evaluation words in the {what}: {hits}')
    return out


def usage_of(rec):
    """Tokens and dollars of a session from its --output-format json result (Claude Code's own totals)."""
    r = (rec or {}).get('result') or {}
    u = r.get('usage') or {}
    return {'input_tokens': u.get('input_tokens', 0), 'cache_creation_input_tokens': u.get('cache_creation_input_tokens', 0),
            'cache_read_input_tokens': u.get('cache_read_input_tokens', 0), 'output_tokens': u.get('output_tokens', 0),
            'cost_usd': r.get('total_cost_usd'), 'turns': r.get('num_turns'), 'is_error': r.get('is_error'),
            'models': sorted((r.get('modelUsage') or {}).keys())}


class Lanes:
    """At most `lanes` sessions at once; after DEAD_STOP failed steps in a row no new step starts (the usage limit)."""

    def __init__(self, lanes):
        self.lanes = max(1, int(lanes))
        self.dead = 0
        self.lock = threading.Lock()

    def stopped(self):
        with self.lock:
            return self.dead >= W.DEAD_STOP

    def done(self, ok):
        with self.lock:
            self.dead = 0 if ok else self.dead + 1

    def map(self, fn, jobs):
        """fn(job) for every job, in order, `lanes` at a time; jobs not started after a stop come back as None."""
        def wrap(job):
            if self.stopped():
                return None
            r = fn(job)
            return r
        with ThreadPoolExecutor(max_workers=self.lanes) as ex:
            return list(ex.map(wrap, jobs))


_switch_lock = threading.Lock()


def record_switch(log_dir, step_label, pmid, entry):
    """Add one step's model-switch outcome to log_dir/model_switch.json (both tries' records stay in log_dir); an earlier
    outcome of the same step is kept in its 'history'."""
    with _switch_lock:
        d = W.read_switches(log_dir)
        old = d.get(step_label)
        hist = (old or {}).get('history', []) + ([{k: v for k, v in old.items() if k != 'history'}] if old else [])
        d[step_label] = {'pmid': str(pmid), 'time': W.now(), **entry, **({'history': hist} if hist else {})}
        W.write_json(Path(log_dir) / W.MODEL_SWITCH_FILE, d)


def record_refusal(log_dir, step_label, pmid, rec):
    """One line in log_dir/refused.tsv for a step the model's safety filter stopped in a run on one model."""
    f = Path(log_dir) / W.REFUSED_FILE
    with _switch_lock:
        new = not f.exists()
        with open(f, 'a') as fh:
            if new:
                fh.write('step\tpmid\tlabel\ttime\tmessage\n')
            msg = str((rec.get('result') or {}).get('result') or '').replace('\t', ' ').replace('\n', ' ')[:200]
            fh.write(f"{step_label}\t{pmid}\t{rec.get('label')}\t{W.now()}\t{msg}\n")


def refused_steps(log_dir, tries=None):
    """Step labels the safety filter stopped `tries` times in a run on one model (default: the run's own number,
    common_w1.refusal_tries of the log folder's name): the runners never send them again."""
    f = Path(log_dir) / W.REFUSED_FILE
    tries = W.refusal_tries(Path(log_dir).name) if tries is None else tries
    n = {}
    for r in W.read_tsv(f) if f.exists() else []:
        n[r['step']] = n.get(r['step'], 0) + 1
    return {s for s, k in n.items() if k >= tries}


def keep_earlier(log_dir, label):
    """Before a step runs again (a resumed run, a failed paper-run's end-of-round repeat, --force): move its earlier
    files (attempt records, prompts, outputs set aside, stray files, scratch) to log_dir/earlier/<label>/<k>/, so no
    record is overwritten (review of the dry-run fixes: both records kept) and w1_audit.py audits those sessions too.
    Returns the folder, or None when the step never ran."""
    log_dir = Path(log_dir)
    mine = re.compile(re.escape(label) + r'\.a\d')
    files = [f for f in log_dir.glob(f'{label}.a*') if f.is_file() and mine.match(f.name)]
    dirs = [d for sub in ('stray', 'scratch') for d in (log_dir / sub).glob(f'{label}.a*') if d.is_dir() and mine.match(d.name)]
    if not files and not dirs:
        return None
    k = 1
    while (log_dir / 'earlier' / label / str(k)).exists():
        k += 1
    dest = log_dir / 'earlier' / label / str(k)
    dest.mkdir(parents=True)
    for f in files:
        shutil.move(str(f), str(dest / f.name))
    for d in dirs:
        t = dest / d.parent.name / d.name
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(d), str(t))
    return dest


def excluded_steps(log_dir):
    """Step labels a model switch left out (their second try switched too): the runners never run them again."""
    return {lab for lab, r in W.read_switches(log_dir).items() if r.get('outcome') == 'excluded'}


def step(make_prompt, cwd, out_file, log_dir, label, check, add_dirs=(), deny=(), timeout=3600, dry=False,
         lanes=None, retry_model=None, scratch=None, pmid=None, one_model=False):
    """One step with the one retry: run on MODEL; if check(out_file) fails or the session errs, set the file aside
    and run once on the retry model. Each attempt that shows another model than it was started with runs once more on
    that model ('.a1b' after '.a1'; its file and records are kept in log_dir); if that second try switches too, the step
    ends without output, outcome 'excluded' in log_dir/model_switch.json (the paper leaves every arm's analysis).
    A step that ran before (resumed, repeated) first moves its earlier files to log_dir/earlier/<label>/<k>/
    (keep_earlier), and a switch in an earlier invocation counts: the next switch excludes the step.
    one_model (the further set, the owner 2026-11-04: the same model and effort for every session): the one retry runs
    on MODEL too, and a session the model's safety filter refused is not sent again or to another model: the step ends
    without output, recorded in log_dir/refused.tsv, and the paper has no read.
    Returns {'ok', 'attempts': [records], 'check': ..., 'excluded': bool, 'refused': bool when so}."""
    out_file = Path(out_file)
    attempts = []
    pmid = pmid or label.split('.')[0]
    earlier = None if dry else keep_earlier(log_dir, label)
    if not dry and out_file.exists():  # a redo never starts with the old read at {OUT}, and cannot pass on it
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        out_file.replace(Path(log_dir) / f'{label}.before.{int(time.time())}.{out_file.name}')
    # a session of this step switched in an earlier invocation (it had its once-more then): the next switch is the
    # second one (review of the dry-run fixes: a resumed or repeated step never gets a second once-more)
    switched_before = (not dry) and label in W.read_switches(log_dir)

    def aside(name):  # keep an attempt's file as evidence, out of the scored folder
        if out_file.exists():
            out_file.replace(Path(log_dir) / f'{label}.{name}.{out_file.name}')

    for k, model in enumerate((W.MODEL, W.MODEL if one_model else retry_model or W.RETRY_MODEL), 1):
        rec = None
        for second in (False, True):
            name = f'a{k}' + ('b' if second else '')
            rec = run_session(make_prompt(model), cwd, model, out_file, log_dir, f'{label}.{name}', add_dirs, deny, timeout,
                              dry, scratch=scratch)
            if dry:
                return {'ok': None, 'attempts': [rec], 'check': 'dry run', 'excluded': False}
            attempts.append(rec)
            if one_model and (rec.get('result') or {}).get('stop_reason') == 'refusal':  # before any once-more: never sent again
                rec['ok'], rec['check'] = False, 'refused by the safety filter'
                W.write_json(Path(log_dir) / f"{rec['label']}.json", rec)
                record_refusal(log_dir, label, pmid, rec)
                aside(name)
                if lanes is not None:
                    lanes.done(True)  # the session ran: not the usage limit
                return {'ok': False, 'attempts': attempts, 'check': rec['check'], 'excluded': False, 'refused': True}
            if not rec.get('switched'):
                break
            aside(name)  # a read partly made by another model is never scored
            rec['ok'] = False
            rec['check'] = f"model switch: {rec['models'].get('sequence')} {rec['models'].get('events') or ''}".strip()
            W.write_json(Path(log_dir) / f'{label}.{name}.json', rec)
            if second or switched_before:
                sw = [a for a in attempts if a.get('switched')]
                record_switch(log_dir, label, pmid, {'outcome': 'excluded', 'model': model,
                                                     'tries': [a['label'] for a in sw],
                                                     'sequences': [a['models'].get('sequence') for a in sw],
                                                     **({'earlier': str(earlier)} if earlier else {}),
                                                     **({'switched_before': True} if switched_before and not second else {})})
                if lanes is not None:
                    lanes.done(True)  # the sessions ran: not the usage limit
                return {'ok': False, 'attempts': attempts, 'check': rec['check'] + ' (second try: excluded)',
                        'excluded': True}
        ok, info = check(out_file)
        res = (rec.get('result') or {})
        ok = ok and not rec.get('timed_out') and not res.get('is_error')
        rec['check'] = info
        rec['ok'] = ok
        W.write_json(Path(log_dir) / f"{rec['label']}.json", rec)
        if len(attempts) >= 2 and attempts[-2].get('switched') and attempts[-2]['label'] == f'{label}.a{k}':
            record_switch(log_dir, label, pmid, {'outcome': 'second_try_ok' if ok else 'second_try_failed', 'model': model,
                                                 'tries': [attempts[-2]['label'], rec['label']],
                                                 'sequences': [attempts[-2]['models'].get('sequence'),
                                                               rec['models'].get('sequence')]})
        if ok:
            break
        aside(f'a{k}' + ('b' if rec['label'].endswith('b') else ''))
    ok = bool(attempts and attempts[-1].get('ok'))
    if lanes is not None:
        lanes.done(ok)
    return {'ok': ok, 'attempts': attempts, 'check': attempts[-1].get('check') if attempts else None, 'excluded': False}


def append_sessions(log_dir, label, pmid, res):
    """One line per attempt in logs/<run>/sessions.tsv."""
    rows = []
    for a in res.get('attempts') or []:
        u = usage_of(a)
        rows.append({'label': a['label'], 'pmid': pmid, 'model': a['model'], 'session_id': a['session_id'],
                     'ok': a.get('ok'), 'exit_code': a.get('exit_code'), 'timed_out': a.get('timed_out'),
                     'seconds': a.get('seconds'), 'turns': u['turns'], 'input_tokens': u['input_tokens'],
                     'cache_creation_input_tokens': u['cache_creation_input_tokens'],
                     'cache_read_input_tokens': u['cache_read_input_tokens'], 'output_tokens': u['output_tokens'],
                     'cost_usd': u['cost_usd'], 'models_used': ','.join(u['models']),
                     'model_sequence': (a.get('models') or {}).get('sequence', ''), 'switched': a.get('switched'),
                     'transcript': a.get('transcript'), 'check': str(a.get('check'))[:300]})
    f = Path(log_dir) / 'sessions.tsv'
    cols = ['label', 'pmid', 'model', 'session_id', 'ok', 'exit_code', 'timed_out', 'seconds', 'turns', 'input_tokens',
            'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens', 'cost_usd', 'models_used',
            'model_sequence', 'switched', 'transcript', 'check']
    with _tsv_lock:
        new = not f.exists()
        with open(f, 'a') as fh:
            if new:
                fh.write('\t'.join(cols) + '\n')
            for r in rows:
                fh.write('\t'.join(str(r.get(c, '')).replace('\t', ' ').replace('\n', ' ') for c in cols) + '\n')


_tsv_lock = threading.Lock()


def versions(log_dir, when):
    f = Path(log_dir) / 'versions.json'
    d = json.loads(f.read_text()) if f.exists() else {}
    d.setdefault(when, []).append({'time': W.now(), 'claude': cli_version()})
    W.write_json(f, d)
    return d
