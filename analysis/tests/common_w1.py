"""W1 kill test: shared paths, paper lists, seeds, prompt filling and small helpers for tools/w1/ (FREEZE.md F5).

The kit's specifications are paper/planning/w1_kill_test/*.md (RUN.md: arms, seeds, scoring; FREEZE.md: setup).
Everything here is read-only on the main CatLog folder; it writes only under the eval folder (EVAL)."""
import collections, csv, datetime, hashlib, json, os, random, re, subprocess, sys, time
from pathlib import Path

csv.field_size_limit(10 ** 9)
sys.dont_write_bytecode = True

W1 = Path(__file__).resolve().parent                     # tools/w1 in the w1-eval worktree
REPO = W1.parent.parent                                   # the w1-eval worktree (code and kit)
KIT = REPO / 'paper' / 'planning' / 'w1_kill_test'        # the kit: specifications, dev_165.tsv, holdout_374.tsv
H2H = REPO / 'paper' / 'evidence' / 'h2h_20261101'        # the head-to-head scorer as committed (be9b8ca)
PROMPTS = W1 / 'prompts'                                  # the plain-arm, reconcile and adjudication texts (verbatim)
MAIN = Path('<the CatLog folder>')        # the main CatLog folder: read only, never written
# The eval root. Its name and every folder a session is shown carry no evaluation word (EVAL_WORDS below): sessions see
# their working directory, their prompt's paths and A6's launch line (dry-run fix, 2026-11-01; it was catlog-eval/w1).
EVAL = Path(os.environ.get('W1_EVAL', '<the kit folder>'))
OLD_EVAL = Path('<the first layout of the kit folder>')  # the first layout: the dry run of 2026-11-01 ran there


def old_layout():
    """The first layout's folder while it still exists (read-denied to every session like the other eval parts)."""
    return [OLD_EVAL.parent] if OLD_EVAL.parent.exists() else []

# the Claude Code command-line tool every plain-arm and adjudication session runs on (FREEZE.md §1: version 2.1.309)
# 2.1.309 (every session to 2026-11-06) was removed by the desktop app on 2026-11-07; from 2026-11-09 the kit runs a
# clone of the app's 2.1.317 kept in the eval folder (cli/2.1.317/claude.app), so no app update can remove it mid-run
CLI = str(Path('<the kit folder>') / 'cli/2.1.317/claude.app/Contents/MacOS/claude')
CLI_VERSION = '2.1.317'
MODEL = 'claude-opus-5-5'          # every reader, verifier, plain agent and adjudicator
RETRY_MODEL = 'claude-sonnet-5-5'  # the one retry of a dead or failed agent (catlog-batch.js again(): 'sonnet')
EFFORT = 'max'
# The model pin (dry-run fix, 2026-11-01). Claude Code 2.1.309 swaps the model inside a session when the API ends a
# response with stop_reason "refusal" (the safety classifier; the dry run's three switches were stop_details.category
# "bio" on 12499375): it first continues once on the same model ("safeguards stopped the response above - continuing
# once with that noted"), and on the next refusal retries on the routed model (for claude-opus-5-5: bio and
# frontier_llm -> claude-opus-5, cyber -> claude-opus-4-8) and writes a system line subtype model_refusal_fallback; on
# the main thread the swap holds for the rest of the session (scope "session"), a subagent swaps that response only
# (scope "local"). Headless (-p) sessions and every subagent switch without asking. --fallback-model is another
# mechanism (overload, unavailable model). The binary's own switches, read from 2.1.309: CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK
# (no refusal fallback at all: w2() gates the visible and the server lane; the silent lane can only retry the refusing
# model itself) and CLAUDE_CODE_NO_MODEL_FALLBACK (its "no-fallback guarantee": the overload and access fallback chains
# collapse to the primary model, and refusal fallback is off too). The user setting switchModelsOnFlag=false only covers
# a headless main thread, never subagents, so the kit does not use it (and never changes the owner's settings). With the
# pin a refused session ends instead (an error, no output): the kit's one retry on claude-sonnet-5-5 takes it, as
# catlog-batch.js's again() does for A6's agents. A session that still shows another model than it was started with runs
# once more; a second switch leaves the paper out of every arm (MODEL_SWITCH_FILE).
PIN_ENV = {'CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK': '1', 'CLAUDE_CODE_NO_MODEL_FALLBACK': '1'}
# No git context for A6 (review of the dry-run fixes, 2026-11-01). catlog-copy is a git checkout (then a worktree of
# main; since the independent check of 2026-11-01 its own one-commit repository), so Claude Code 2.1.309
# put a gitStatus block into the context of the launch session and of every workflow agent (the first dry run's
# transcripts: attachment session_context): its status line named .w1_run_started and its "Recent commits" were the
# kit's commits ("W1 review: ... every eval part but a6/ and plain/ ..."). The binary gates that block on
# includeGitInstructions, and CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS overrides the setting (PTo()/$pt()); it also drops
# the git commit/PR instructions, which a reader never uses. Process-wide, so it holds for the workflow's agents.
NO_GIT_CONTEXT_ENV = {'CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS': '1'}
# Memory off (the owner's decision, 2026-11-01). Claude Code loads the auto-memory index of the repository a folder
# belongs to, so every session opened in catlog-copy (a worktree of main) was shown main's MEMORY.md (attachment
# 'instructions', type AutoMem), whose lines name the paper's plans. CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 turns auto memory
# off (2.1.309: Km() 'off', so Hp() is false: no AutoMem instruction file and no memory prompt); the plain arms and the
# adjudicators run with it already. Process-wide, so it holds for the workflow's agents too.
NO_MEMORY_ENV = {'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1'}
RUN_MARK = '.run_started'          # catlog-copy: the run's start time for the audit (was .w1_run_started: a name with w1)
OLD_RUN_MARK = '.w1_run_started'
MODEL_SWITCH_FILE = 'model_switch.json'  # in a run's log folder: every switched session, its second try and the outcome
REFUSED_FILE = 'refused.tsv'  # in a run's log folder: the steps the safety filter stopped in a run on one model
# Tries a step gets before a refusal is final (one line in REFUSED_FILE per refused session). The further set's judges:
# one more try on MODEL after a refusal (the owner, 2026-11-05: "yes allow one more try on opus if common"; common = 3
# or more refused judge sessions in phase 1, fixed before the rest of phase 1 was seen). Plain reads: one try; their
# refused papers were replaced from the fixed second draw, before this decision.
REFUSAL_TRIES = {'adjudication_rand': 2, 'adjudication_randfull': 2,
                 'adjudication_locked': 2}  # the locked set's judges (2026-11-09): the same rule as the further set's


def refusal_tries(log_name):
    return REFUSAL_TRIES.get(log_name, 1)
ALLOWED_TOOLS = 'Read Write Glob Grep Bash(pdftoppm:*) Bash(pdftotext:*) Bash(python3:*) Bash(ls:*) Bash(mkdir:*)'
DEAD_STOP = 3                      # three dead agents in a row stop the lanes (the usage limit), as in catlog-batch.js
# the statuses `catlog.py add` leaves on a paper the copy finished: its rows are the run's (score_w1.load_rows), and a
# follow-up launch of the same run does not read it again (run_a6.py, unless --force)
DONE_A6 = {'done', 'incomplete', 'needs_supplement', 'wrong_paper', 'no_kinetics'}

# seeds (RUN.md §3, §4, §6): each arm-run's paper order = SEED_ORDER + 10 x round + ARM_OFFSET[arm]
SEED_ORDER = 20261101
ARM_OFFSET = {'A0': 0, 'A2': 2, 'A6': 6}
ROUND_ARM_ORDER = 9                # + 10 x round: the order of the three arms within a round (not fixed by RUN.md)
SEED_PILOT = 20261031              # the pilot's 10 papers (RUN.md §4)
SEED_BOOT = 20261031               # the paired, paper-clustered bootstrap (RUN.md §6.8)
SEED_POOL = 20261102               # claim pool: matched-value sample, decoys, claim ids, chunk order (not fixed by RUN.md)
SEED_PEOPLE = 20261101             # the people_100 sample
ARMS = ('A0', 'A2', 'A6')
ROUNDS = (1, 2, 3)

GLYPH = re.compile(r'^GLYPH WARNING')


SPECIAL_RUNS = ('pilot', 'dry', 'hard', 'rand', 'randfull', 'locked')  # locked (2026-11-09): unseen held-out papers, one plain read against
# the copy of the reading steps cut on 9 November (score_locked.py), judged like randfull; randfull (2026-11-06): the random set's values judged again with each record's full details (score_randfull.py); the pilot (RUN.md §4), FREEZE.md F6's dry run and the hard-case set
# (2026-11-02: one plain read of papers with a documented trap, scored against checked trap keys) and the random set
# (2026-11-04: one plain read of randomly drawn finished papers, compared with the catalogue): scored apart, never in
# the decision
JUDGES = ('j1', 'j2', 'j3')

# The tree (dry-run fix, 2026-11-01). What a session is shown (its folder, the paths in its prompt, its added working
# directories, A6's launch line) carries no evaluation word; everything else is under records/, which no session may read:
#   catlog-copy/       A6's CatLog folder (a plain folder with its own git repository holding one commit, an orphan
#                      snapshot commit with the harness files of the kit commit, HEAD detached at it, no ref:
#                      w1_setup.snapshot_commit and own_repo; until the independent check of 2026-11-01 a worktree of
#                      the main repository, whose refs git log --all and git branch -a showed there)
#   papers/<PMID>/     a plain session's folder (paper.txt, paper.supp.txt, source.pdf|xml); papers/check_rows.py
#   checks/<PMID>/     an adjudicator's folder
#   out/<code>/        files sessions write or are given (plain outputs, A2's reads, the claims and the verdicts), one
#                      folder per arm-run part under an opaque code (code(): six letters and digits, no vowel)
#   code/              the w1-eval worktree (the kit)
#   records/           keys/, orders/, logs/, audit/, runs/ (A6's kept runs), score/, score_pilot/, score_dry/, dry_run_*/
OUT_NAMES = {'a6': 'catlog-copy', 'plain': 'papers', 'adj': 'checks', 'out': 'out', 'repo': 'code', 'records': 'records',
             'adj_full': 'folios'}  # adj_full: the judges of randfull (2026-11-06), apart from the first judges' folders
# Judgings whose claims carry each record's full details (prompts/adjudicate_full.txt), each judge role in its own folders
# folios/<code of its label>/<PMID>/: randfull (2026-11-06) and the locked set (2026-11-09)
FULL_RUNS = ('randfull', 'locked')


def eval_paths(ev=None, which=None):
    """The eval tree. which = 'rounds' (default), 'pilot' or 'dry': the claims, verdicts and scores of that adjudication,
    never mixed with the others."""
    ev = Path(ev or EVAL)
    rec = ev / OUT_NAMES['records']
    w = which if which in SPECIAL_RUNS else 'rounds'
    return {'eval': ev, 'repo': ev / OUT_NAMES['repo'], 'a6': ev / OUT_NAMES['a6'], 'plain': ev / OUT_NAMES['plain'],
            'adj': ev / OUT_NAMES['adj_full' if which in FULL_RUNS else 'adj'], 'out': ev / OUT_NAMES['out'], 'records': rec,
            'keys': rec / 'keys', 'orders': rec / 'orders', 'runs': rec / 'runs', 'logs': rec / 'logs',
            'audit': rec / 'audit', 'score': rec / (f'score_{which}' if which in SPECIAL_RUNS else 'score'),
            'claims': out_dir(ev, f'claims-{w}'), 'claims3': out_dir(ev, f'claims3-{w}'),
            'verdicts': {j: out_dir(ev, f'verdicts-{j}-{w}') for j in JUDGES},
            'validator': ev / OUT_NAMES['plain'] / 'check_rows.py', 'manifest': ev / 'MANIFEST.json'}


# ---------- opaque codes and evaluation words (dry-run fix, 2026-11-01) ----------

CODE_ALPHABET = 'bcdfghjkmnpqrstvxz23456789'  # no vowel, no w, y, l, 0 or 1: no word (w1, a6, dry, ...) can form


def code(label):
    """The neutral name a session sees for an internal label (an arm-run part such as 'A2-r1-readA', a judge 'adj-j1',
    a claims or verdict folder): six characters from CODE_ALPHABET, fixed by the label."""
    h = int(hashlib.sha256(f'kinetics-reading/{label}'.encode()).hexdigest(), 16)
    out = ''
    for _ in range(6):
        h, r = divmod(h, len(CODE_ALPHABET))
        out += CODE_ALPHABET[r]
    return out


def out_dir(ev, label):
    return Path(ev) / OUT_NAMES['out'] / code(label)


# Evaluation words: anything that would tell an agent that its work is part of an evaluation. ONE list, used everywhere:
# w1_audit.py flags a session whose working directory, prompt or relayed request contains one, the runners and
# run_a6.py refuse to start such a session, and w1_setup.py check tests every path and text a session is shown.
# PATH words count as a whole path part (a path split at / - _ . and spaces: 'catlog-eval/w1/plain' has catlog-eval,
# w1 and plain); TEXT words anywhere as words (case ignored; a trailing * is a prefix). 'runs' is only a path word:
# the A6 task text ends "so only the verifier runs".
EVAL_PATH_WORDS = ('catlog-eval', 'w1', 'a0', 'a2', 'a6', 'plain', 'adj', 'runs', 'score', 'scores', 'score_pilot',
                   'score_dry', 'keys', 'audit', 'orders', 'pilot', 'dry', 'dry_run', 'reada', 'readb',
                   'readc', 'arm', 'arms', 'judge', 'judges', 'j1', 'j2', 'j3', 'gold', 'eval', 'kill', 'h2h', 'w1adj')
EVAL_TEXT_WORDS = ('W1', 'kill test', 'kill-test', 'gold set*', 'gold standard', 'gold file*', 'gold value*', 'benchmark*',
                   'evaluat*', 'experiment*', 'adjudicat*', 'co-scientist', 'coscientist', 'enzyextract', 'error rate*',
                   'hypothes*', 'head-to-head', 'head to head', 'ablation', 'plain arm*', 'decoy*', 'answer key*',
                   'catlog-eval', 'A0', 'A2', 'A6', 'W1adj')


def _text_rx(words):
    alts = []
    for w in words:
        stem = r'[\s_-]+'.join(re.escape(x) for x in re.split(r'[ -]+', w.rstrip('*')))
        alts.append(r'(?<![A-Za-z0-9])' + stem + (r'[A-Za-z]*' if w.endswith('*') else r'(?![A-Za-z0-9])'))
    return re.compile('|'.join(alts), re.I)


EVAL_TEXT_RX = _text_rx(EVAL_TEXT_WORDS)
PATHISH = re.compile(r'(?:~|\.{1,2})?/[^\s\'"`<>|;,)(]*')


def eval_word_hits(text):
    """The evaluation words in a text (a prompt, a launch line, a relayed request, a working directory): text words
    anywhere, path words as whole parts of the path-like tokens in it. Sorted, lower case."""
    text = str(text or '')
    hits = {m.group(0).lower() for m in EVAL_TEXT_RX.finditer(text)}
    paths = PATHISH.findall(text) + ([text] if text.startswith('/') and ' ' not in text.strip() else [])
    pw = set(EVAL_PATH_WORDS)
    for p in paths:
        for seg in p.split('/'):
            seg = seg.lower()
            if seg in pw:
                hits.add(seg)
            for part in re.split(r'[-_. ]+', seg):
                if part in pw:
                    hits.add(part)
    return sorted(hits)


# Instruction files Claude Code loads into an A6 session and every workflow agent (transcript attachment 'instructions',
# by its type): the owner's ~/.claude/CLAUDE.md and CatLog's CLAUDE.md. They are production text with a few words of the
# list (CLAUDE.md: STRENDA's "experiments", /audit). Setup records each file's words (MANIFEST instructions_baseline);
# the audit breaks a word that is not there, and any instruction file of a type the baseline does not hold. Main's
# memory index (AutoMem: ~/.claude/projects/-Users-<user>-Documents-catlog-v2/memory/MEMORY.md, which Claude Code
# loaded for catlog-copy in the first dry run because it is a worktree of main) is not one of them since 2026-11-01:
# A6 runs with memory off (NO_MEMORY_ENV), so a memory index shown to an A6 session breaks.
def instruction_files_a6(ev=None):
    P = eval_paths(ev)
    return {'User': Path.home() / '.claude' / 'CLAUDE.md', 'Project': P['a6'] / 'CLAUDE.md'}


def text_sha(text):
    """sha256 of an instruction text as Claude Code shows it (its trailing newline dropped)."""
    return hashlib.sha256(str(text).rstrip('\n').encode('utf-8', 'surrogateescape')).hexdigest()


def instruction_baseline(ev=None):
    """{type: {path, sha256, eval_words}} of the instruction files an A6 session loads, as they are now."""
    out = {}
    for kind, f in instruction_files_a6(ev).items():
        t = f.read_text(errors='replace') if f.exists() else ''
        out[kind] = {'path': str(f), 'sha256': text_sha(t) if f.exists() else None, 'eval_words': eval_word_hits(t)}
    return out


def sha256(path, n=None):
    h = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return h[:n] if n else h


def sha256_bytes(b, n=None):
    h = hashlib.sha256(b).hexdigest()
    return h[:n] if n else h


def read_tsv(path):
    with open(path, newline='') as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def write_tsv(path, rows, cols):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with open(tmp, 'w', newline='') as fh:
        w = csv.DictWriter(fh, cols, delimiter='\t', extrasaction='ignore', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def write_json(path, obj, indent=1):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=indent, default=str) + '\n')
    os.replace(tmp, path)


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S %z')


def pmid_key(p):
    return (0, int(p), '') if str(p).isdigit() else (1, 0, str(p))


def dev_papers():
    return [r['pmid'] for r in read_tsv(KIT / 'dev_165.tsv')]


def holdout_papers():
    return [r['pmid'] for r in read_tsv(KIT / 'holdout_374.tsv')]


def people_papers():
    f = W1 / 'people_100.tsv'
    return [r['pmid'] for r in read_tsv(f)] if f.exists() else []


def eval_papers():
    """Every paper of W1: the 165 development papers, then the people papers, without repeats."""
    out, seen = [], set()
    for p in dev_papers() + people_papers():
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def seeded_order(pmids, seed):
    """A paper order drawn with this seed from the papers sorted by id, so it never depends on the input order."""
    return random.Random(seed).sample(sorted(set(pmids), key=pmid_key), len(set(pmids)))


def order_seed(arm, rnd):
    return SEED_ORDER + 10 * int(rnd) + ARM_OFFSET[arm]


def run_label(arm, run):
    """'A0-r2' for round 2, 'A0-pilot' for the pilot, 'A0-dry' for F6's dry run (never in the decision). Internal: no
    session is shown a run label (they see code(part_label(...)))."""
    if str(run) in SPECIAL_RUNS:
        return f'{arm}-{run}'
    return f'{arm}-r{int(run)}'


def check_run(run):
    """A run argument: 1, 2, 3, pilot or dry."""
    if str(run) in SPECIAL_RUNS or (str(run).isdigit() and int(run) in ROUNDS):
        return str(run)
    raise SystemExit(f'--run must be 1, 2, 3, pilot or dry (got {run})')


PLAIN_PARTS = ('readA', 'readB', 'readC', 'final')


def part_label(arm, run, part=None):
    """The internal label of an arm-run part: 'A0-r1', 'A2-r1-readA', 'A2-r1-final'."""
    return run_label(arm, run) + (f'-{part}' if part else '')


def out_file(ev, arm, run, part, pmid):
    """Scored or intermediate output of one plain-arm session (RUN.md §2): out/<code of A0-r1>/<PMID>.json,
    out/<code of A2-r1-readA>/<PMID>.json, out/<code of A2-r1-final>/<PMID>.json."""
    return out_dir(ev, part_label(arm, run, part if arm != 'A0' else None)) / f'{pmid}.json'


def strip_glyph(text):
    """The production text without its leading GLYPH WARNING paragraph (A0_plain_prompt.md): code puts one line and a
    blank line on top (tools/fetch.py glyph_warning / scan_warning); everything after it is unchanged."""
    if not GLYPH.match(text):
        return text
    i = text.find('\n')
    if i >= 0 and text[i:i + 2] == '\n\n':
        return text[i + 2:]
    return re.sub(r'^GLYPH WARNING[^\n]*\n+', '', text, count=1)


def prompt_text(name):
    return (PROMPTS / name).read_text()


PLACEHOLDER = re.compile(r'\{([A-Z][A-Z_]*)\}')


def fill(text, **values):
    """Fill the kit's {UPPER} placeholders. The prompts hold JSON braces too, so only the named keys are replaced, and
    a placeholder left unfilled is an error."""
    for k, v in values.items():
        text = text.replace('{' + k + '}', str(v))
    left = sorted(set(PLACEHOLDER.findall(text)))
    if left:
        raise ValueError(f'unfilled placeholders: {left}')
    return text


def project_slug(path):
    """The folder name Claude Code gives a working directory under ~/.claude/projects (as catlog.agent_model)."""
    return re.sub(r'[^A-Za-z0-9]', '-', str(path))


# main's auto-memory index: loaded into sessions opened in main or a worktree of it, unless auto memory is off (A6 since
# 2026-11-01: NO_MEMORY_ENV); the setup records its hash only to say it is not loaded
MAIN_MEMORY = Path.home() / '.claude' / 'projects' / project_slug(MAIN) / 'memory' / 'MEMORY.md'


def transcript_path(cwd, session_id):
    return Path.home() / '.claude' / 'projects' / project_slug(cwd) / f'{session_id}.jsonl'


def git(repo, *args):
    r = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], capture_output=True, text=True,
                       env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
    return r.stdout.strip() if r.returncode == 0 else ''


def disk_free_gb(path):
    st = os.statvfs(str(path))
    return st.f_bavail * st.f_frsize / 1e9


def read_order(ev, name):
    f = eval_paths(ev)['orders'] / f'{name}.txt'
    return [w for w in f.read_text().split() if w] if f.exists() else []


# ---------- isolation helpers (REVIEW.md 1.2-1.6) ----------

UID = os.getuid()
TMP = Path('/private/tmp')
CLAUDE_TMP = TMP / f'claude-{UID}'                       # Claude Code's per-session scratchpads and task outputs
PROJECTS = Path.home() / '.claude' / 'projects'          # Claude Code's session records (transcripts, tool results)
REALKCAT = Path('<the earlier CatLog folder>')
IMAGE_EXT = {'.png', '.ppm', '.pgm', '.pbm', '.jpg', '.jpeg', '.tif', '.tiff', '.gif', '.bmp', '.webp'}
INPUT_NAMES = {'paper.txt', 'paper.supp.txt', 'source.pdf', 'source.xml'}
# the names at the top of the eval folder (README.md and the other notes are files there)
EVAL_PARTS = tuple(sorted(OUT_NAMES.values()))


def eval_entries(ev, keep=()):
    """Every top-level entry of the eval folder (existing ones and the known names) except `keep` (names, e.g.
    OUT_NAMES['plain']): (folders, files)."""
    ev = Path(ev)
    names = set(EVAL_PARTS) | ({p.name for p in ev.iterdir()} if ev.exists() else set())
    folders, files = [], []
    for n in sorted(names - set(keep)):
        p = ev / n
        (files if p.is_file() else folders).append(p)
    return folders, files


def plain_labels():
    """Every plain-arm part label of every run (A0's, A2's reads and reconcile)."""
    labs = []
    for r in list(SPECIAL_RUNS) + list(ROUNDS):
        labs.append(run_label('A0', r))
        labs += [part_label('A2', r, part) for part in PLAIN_PARTS]
    return labs


def judge_label(judge, which=None):
    """The judges of a full-record judging (FULL_RUNS) have their own label, so their codes and /tmp scratch names
    differ from the first judges'."""
    return f'adj-{judge}' + (f'-{which}' if which in FULL_RUNS else '')


def out_labels():
    """Every internal label that has a folder under out/: the plain parts, and per adjudication (rounds, pilot, dry) the
    claims, the third judge's claims and each judge's verdicts."""
    return plain_labels() + [f'{k}-{w}' for w in ('rounds',) + SPECIAL_RUNS
                             for k in ('claims', 'claims3') + tuple(f'verdicts-{j}' for j in JUDGES)]


def code_table():
    """label -> code for every label a session might be shown as a code (written to records/orders/codes.tsv)."""
    return {lab: code(lab) for lab in out_labels() + [judge_label(j, w) for j in JUDGES for w in (None,) + FULL_RUNS]}


def out_folders(ev):
    """Every folder under out/ (existing ones and the known labels' codes)."""
    o = Path(ev) / OUT_NAMES['out']
    out = {out_dir(ev, lab) for lab in out_labels()}
    if o.exists():
        out.update(d for d in o.iterdir() if d.is_dir())
    return sorted(out)


def scratch_labels():
    """Every prefix an eval session puts on its /tmp scratch (the prompts' /tmp/{RUN}-{PMID}-*: the code of its part or
    judge), and A6's role folders (read-<PMID>, verify-<PMID>)."""
    return ([code(lab) for lab in plain_labels()] + [code(judge_label(j, w)) for j in JUDGES for w in (None,) + FULL_RUNS]
            + ['read', 'verify'])


# ---------- models in a transcript (dry-run fix, 2026-11-01) ----------

FALLBACK_SUBTYPES = ('model_refusal_fallback', 'model_fallback')


def transcript_models(tr):
    """What a Claude Code transcript shows about its models: 'models' (every assistant message's model, in order;
    Claude Code's own '<synthetic>' messages left out), 'sequence' ('A>B': the runs of one model), 'events' (system lines
    of a model fallback: subtype, original and fallback model, refusal category), 'refusals' (responses the API ended
    with stop_reason "refusal") and 'ending', how the transcript ends: its last assistant message, '<synthetic>' ones
    included ({model, stop_reason, api_error: the line's isApiErrorMessage}; None without one). In A6-hard an agent the
    usage limit stopped ends with a '<synthetic>' API error of stop_reason 'stop_sequence', one a refusal stopped with
    one of stop_reason 'refusal' (review of round 3, 2026-11-10)."""
    models, events, refusals, ending = [], [], 0, None
    try:
        fh = open(tr, errors='replace')
    except OSError:
        return {'models': [], 'sequence': '', 'events': [], 'refusals': 0, 'ending': None, 'missing': True}
    with fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get('type') == 'assistant':
                m = d.get('message') or {}
                if m.get('model') and m['model'] != '<synthetic>':
                    models.append(m['model'])
                if m.get('stop_reason') == 'refusal':
                    refusals += 1
                ending = {'model': m.get('model'), 'stop_reason': m.get('stop_reason'),
                          'api_error': bool(d.get('isApiErrorMessage'))}
            elif d.get('type') == 'system' and d.get('subtype') in FALLBACK_SUBTYPES:
                events.append({'subtype': d['subtype'], 'from': d.get('originalModel') or d.get('original_model'),
                               'to': d.get('fallbackModel') or d.get('fallback_model'), 'scope': d.get('scope'),
                               'category': d.get('apiRefusalCategory'), 'time': d.get('timestamp')})
    seq = []
    for m in models:
        if not seq or seq[-1] != m:
            seq.append(m)
    return {'models': models, 'sequence': '>'.join(seq), 'events': events, 'refusals': refusals, 'ending': ending}


def model_switch(tr, launched):
    """(switched, info) for a session started on `launched`: it switched when an assistant message names another model
    or Claude Code logged a model fallback in it."""
    info = transcript_models(tr)
    other = sorted({m for m in info['models'] if m != launched})
    info.update({'launched': launched, 'other_models': other, 'switched': bool(other or info['events'])})
    return info['switched'], info


def read_switches(log_dir):
    """The run's model-switch record (log_dir/MODEL_SWITCH_FILE): {step label: {...}}."""
    f = Path(log_dir) / MODEL_SWITCH_FILE
    try:
        return json.loads(f.read_text()) if f.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def switch_excluded(log_dir):
    """Papers a model switch left out (a second try that switched too): {pmid: [step labels]}."""
    out = {}
    for lab, r in read_switches(log_dir).items():
        if r.get('outcome') == 'excluded':
            out.setdefault(str(r.get('pmid')), []).append(lab)
    return out


def instruction_files(cwd):
    """CLAUDE.md, CLAUDE.local.md or .claude/ in a session folder or any parent (the home folder's own .claude/, which
    holds Claude Code's state, excepted): none may exist for a plain or adjudicator session (REVIEW.md 1.2)."""
    out, d = [], Path(cwd).resolve()
    home = Path.home().resolve()
    while True:
        for n in ('CLAUDE.md', 'CLAUDE.local.md', '.claude'):
            p = d / n
            if p.exists() and not (n == '.claude' and d == home):
                out.append(str(p))
        if d.parent == d:
            return out
        d = d.parent


def folder_problems(cwd):
    """A plain or adjudicator session folder must hold only its inputs and no instruction file above it."""
    cwd = Path(cwd)
    extra = sorted(n for n in os.listdir(cwd) if n not in INPUT_NAMES) if cwd.is_dir() else ['(missing)']
    return ([f'{cwd}: unexpected {extra}'] if extra else []) + [f'instruction file {f}' for f in instruction_files(cwd)]


# ---------- the locked set's checks (review of 2026-11-09): the same inputs, one model and the frozen stamps ----------

INPUT_KEYS = ('text_sha256', 'original_sha256', 'supp_sha256')  # the production text, its original, its supplement


def input_records(ev):
    """{name: {pmid: record}} of the inputs laid down after W1's setup: the plain read's folders papers/<PMID>/
    (records/hard_inputs.json) and the judges' folders checks/<PMID>/ (records/judge_inputs.json), each holding the sha256
    of the production text, its original and its supplement as cloned (INPUT_KEYS); a folder setup made (a record
    'existed': a W1 paper) by MANIFEST.json's input record of it."""
    P = eval_paths(ev)
    kit = json.loads(P['manifest'].read_text()).get('inputs', {}) if P['manifest'].exists() else {}
    out = {}
    for name in ('hard_inputs', 'judge_inputs'):
        f = P['records'] / f'{name}.json'
        recs = json.loads(f.read_text()) if f.exists() else {}
        out[name] = {p: (kit.get(p) or {}) if r.get('existed') else r for p, r in recs.items()}
    return out


def input_hashes(rec):
    """(text, original, supplement) sha256 of an input record; None where it holds none (no original, no supplement)."""
    return tuple((rec or {}).get(k) for k in INPUT_KEYS)


# The paper a reading agent's task names (catlog-batch.js: 'Follow <DIR>/prompts/read.md for PMID <id>', or for a paper
# with no PMID 'for paper (no PMID: identified by its DOI in <DIR>/papers.tsv column 2) <id>'). human_review.READ_TASK,
# a file of the snapshot (it cannot change without moving the copy off its tag), allows 90 characters inside that
# parenthesis: enough for production's folder, not for catlog-copy's longer one, so the hard set's NPD832847D went
# unaudited (review of round 2, 2026-11-10). The kit's own pattern allows more; run_a6.agent_rows and w1_audit use it.
READ_TASK = re.compile(r'prompts/(?:read|verify)\.md for (?:PMID|paper\b[^\n]{0,400}?\))\s*(\d{1,9}|NP[0-9A-F]{8})')
# a plain read's session record in records/logs/A0-<run>/ and its earlier/ (claude_session.run_session: <PMID>.a1.json,
# .a1b.json, .a2.json)
SESSION_RECORD = re.compile(r'^(?P<pmid>[^.]+)\.a\d+b?\.json$')


def a6_launch_rank(launch):
    """A launch's place among its kind (run_a6.next_launch): main and redo 0, more-<k> and redo-more-<k> k."""
    m = re.fullmatch(r'(?:redo-)?more-(\d+)', launch)
    return int(m.group(1)) if m else 0


A6_LAUNCH = re.compile(r'main|redo|(?:redo-)?more-\d+')  # the launch folders run_a6.next_launch makes
# the sets the copy of the reading steps reads after the W1 rounds (w1_setup.py a6-papers, 2026-11-09): read on the
# snapshot the main repository's tag FREEZE_TAG names (a6_pin_problems)
LATER_LABELS = ('hard', 'locked')


def a6_is_redo(launch):
    """A launch of the redo after a model switch (run_a6.py --redo): redo and redo-more-<k> count alike, as main and
    more-<k> do for every other paper (review of round 2, 2026-11-10)."""
    return str(launch or '').startswith('redo')


def a6_launches(ev, label):
    """The launch folders of A6-<label>: records/logs/A6-<label>/main, more-<k>, redo, redo-more-<k>."""
    logs = eval_paths(ev)['logs'] / f'A6-{label}'
    return [d for d in sorted(logs.iterdir()) if d.is_dir() and A6_LAUNCH.fullmatch(d.name)] if logs.exists() else []


def a6_redone(ev, label):
    """The papers of A6-<label> read again after a model switch whose redo was kept (records/runs/A6-<label>/redo/RESET.json)."""
    f = eval_paths(ev)['runs'] / f'A6-{label}' / 'redo' / 'RESET.json'
    return {str(x) for x in json.loads(f.read_text()).get('pmids') or []} if f.exists() else set()


def a6_state_agents(ev, label):
    """{pmid: [(launch, [its agents there]), ...]}: for each paper of A6-<label>, every launch of its state that ran agents
    for it, in order: main and more-<k>, then, for a paper read again after a model switch whose redo was kept
    (a6_redone), redo and redo-more-<k> (another paper's redo launch is no part of its state). A launch folder's agents
    are run_a6.launch_agents' (agents.json; a killed launch's read from its transcripts; none where no session started);
    a launch whose agents cannot be accounted for stops: its agents' models are unknown."""
    import run_a6  # noqa: E402  (here, not at the top: run_a6 imports this module)
    redone, by = a6_redone(ev, label), {}  # by: pmid -> {(redo, rank): (launch, [agents of that launch])}
    for d in a6_launches(ev, label):
        rows = run_a6.launch_agents(d)
        if rows is None:
            raise SystemExit(f'{d}: its agents cannot be accounted for (a session no launch.json names, as the launcher '
                             'before 2026-11-10 named it only at the end, or one that ran and whose transcript is gone): '
                             'their models are unknown')
        redo = a6_is_redo(d.name)
        for r in rows:
            p = str(r.get('pmid') or '')
            if p and (not redo or p in redone):
                by.setdefault(p, {}).setdefault((redo, a6_launch_rank(d.name)), (d.name, []))[1].append(r)
    return {p: [runs[k] for k in sorted(runs)] for p, runs in by.items()}


def a6_kept_agents(ev, label, state=None):
    """{pmid: (launch, [its agents there])}: for each paper of A6-<label>, the launch whose rows are kept and that launch's
    agents of the paper: the last launch of its state (a6_state_agents) that ran agents for it among main and more-<k>,
    or, for a paper read again after a model switch (a6_redone), among its redo launches (redo, redo-more-<k>).
    state: a6_state_agents(ev, label), when the caller has it."""
    state = a6_state_agents(ev, label) if state is None else state
    redone, out = a6_redone(ev, label), {}
    for p, launches in state.items():
        mine = [x for x in launches if a6_is_redo(x[0]) == (p in redone)]
        if mine:
            out[p] = mine[-1]
    return out


def a6_retry(r):
    """An agent row that is the workflow's own retry on RETRY_MODEL (catlog-batch.js again(): label '-sonnet')."""
    return 'sonnet' in str(r.get('label') or '').lower() or (r.get('launched') or MODEL) != MODEL


def a6_ran(r):
    """An agent row whose transcript shows a message of a model (its model sequence is not empty): one that never
    produced a message died at once (at a usage limit, say) and read nothing."""
    return any(m for m in str(r.get('sequence') or '').split('>'))


def a6_agent_other_model(r):
    """An agent of run_a6.py's agents.json that ran on another model than MODEL: the workflow's retry once it ran (a6_ran),
    a model sequence naming another model (a switch) or a model-fallback line. A retry whose sequence is empty never
    produced a message: it read nothing, so it is no other model."""
    seq = [m for m in str(r.get('sequence') or '').split('>') if m]
    return (a6_retry(r) and a6_ran(r)) or any(m != MODEL for m in seq) or bool(r.get('events'))


def a6_other_model(ev, label, kept=None):
    """{pmid: [agent label and model sequence, ...]}: the papers of A6-<label> whose kept launch (a6_kept_agents) ran an
    agent of the paper on another model than MODEL (a6_agent_other_model)."""
    kept = a6_kept_agents(ev, label) if kept is None else kept
    out = {}
    for p, (_, agents) in kept.items():
        bad = [f"{r.get('label')} {r.get('sequence') or '-'}" for r in agents if a6_agent_other_model(r)]
        if bad:
            out[p] = bad
    return out


def a6_ended_by_api_error(r):
    """Whether an agent's transcript ends with an API error other than a refusal: its last assistant message,
    '<synthetic>' ones included, is an API error message (isApiErrorMessage) whose stop_reason is not 'refusal'. In
    A6-hard the usage limit's is 'stop_sequence' (7 Opus agents), a refusal's own 'refusal' (11), and the two readers
    that reported a problem after a refusal they got past end with their own tool call. Such an error, not a refusal
    the agent got past before it, started the workflow's retry of its role (review of round 3, 2026-11-10). Read from
    the row's 'ending' (run_a6.agent_rows since 2026-11-10: transcript_models); for a row written before it (A6-hard's
    agents.json), from the row's transcript while it is on disk, read only; with neither, False: the agent's refusal
    counts, as before."""
    tr = r.get('transcript')
    e = r['ending'] if 'ending' in r else transcript_models(tr)['ending'] if tr and Path(tr).is_file() else None
    return bool(e and e.get('api_error') and e.get('stop_reason') != 'refusal')


def a6_refused(launches):
    """Whether the safety filter stopped the copy's read of a paper, over every launch of its state (a6_state_agents:
    [(launch, [agents])], main and more-<k>, a redone paper's redo launches too): in one launch, an agent on MODEL (not
    the workflow's retry) logged a refusal (agents.json 'refusals'), the workflow retried that role on RETRY_MODEL, and
    the agent's transcript does not end with an API error other than a refusal (a6_ended_by_api_error): the refusal
    started the retry, whether the retry then ran or died at once. Any launch counts, as a refused plain session is
    never sent again (claude_session.step): a paper refused on its first try stays refused when a follow-up or a redo
    reads it. An agent that got past its refusals and then died at the usage limit (or another API error) had its
    retry started by that error, so that launch shows no refusal and the paper is judged on the launch whose rows are
    kept, as any paper a usage limit stopped: a clean follow-up read is analysed, a paper left unfinished is 'catlog
    failed' and one its retry finished 'catlog retry on another model', both read again. A refusal the agent got past
    on MODEL itself, with no retry of its role, stopped no read, finished or not: a paper left unfinished by another
    agent's death (a usage limit, a crash) is operational ('catlog failed'), as a plain session that got past a
    refusal and then failed is 'plain failed' (the plain side counts only a session whose result ended refused)."""
    for _, agents in launches:
        retried = {r.get('role') for r in agents if a6_retry(r)}
        if any(not a6_retry(r) and (r.get('refusals') or 0) > 0 and r.get('role') in retried
               and not a6_ended_by_api_error(r) for r in agents):
            return True
    return False


def a6_retried(agents):
    """[agent label and model sequence]: the workflow's retries on RETRY_MODEL among one launch's agents of a paper that
    ran (a6_ran). Unless a refusal started it (a6_refused), such a retry is operational ('catlog retry on another
    model'): the paper is read again on MODEL (run_a6.py LABEL --redo --pmids P), as a plain step's one retry runs on
    MODEL too."""
    return [f"{r.get('label')} {r.get('sequence')}" for r in agents if a6_retry(r) and a6_ran(r)]


def a6_stamped_other_model(rows):
    """{pmid: ['reader_model X', ...]}: kept rows stamped with a reader_model or verifier_model other than MODEL (catlog.py
    stamps them from each agent's own transcript; a blank stamp, written when it cannot tell, is not another model)."""
    out = {}
    for r in rows:
        for k in ('reader_model', 'verifier_model'):
            m = str(r.get(k) or '')
            if m and m != MODEL:
                out.setdefault(str(r.get('pmid')), set()).add(f'{k} {m}')
    return {p: sorted(v) for p, v in out.items()}


def a6_launch_broken(ev, label, kept=None):
    """{pmid: launch}: the papers of A6-<label> whose kept launch (a6_kept_agents: a redone paper's is its redo launch) has
    a launch session the audit broke (records/audit/A6-<label>/audit.json: a row of role 'launch', broken); {} before the
    audit."""
    f = eval_paths(ev)['audit'] / f'A6-{label}' / 'audit.json'
    if not f.exists():
        return {}
    bad = {str(r.get('launch')) for r in json.loads(f.read_text()).get('agents') or []
           if r.get('role') == 'launch' and r.get('broken')}
    kept = a6_kept_agents(ev, label) if kept is None else kept
    return {p: launch for p, (launch, _) in kept.items() if launch in bad}


A6_MODEL_BREAKS = {'model', 'model_switch', 'model_fallback'}  # w1_audit.audit_agent's breaks for another model


def record_time(s, f=None):
    """A record's time as an aware datetime: now()'s '2026-11-10 06:00:00 -0600' or w1_setup.utc()'s
    '2026-11-10T12:00:00.000Z'; without one, the modification time of the file f that holds it (None without f)."""
    for fmt in ('%Y-%m-%d %H:%M:%S %z', '%Y-%m-%dT%H:%M:%S.%f%z'):
        try:
            return datetime.datetime.strptime(str(s or '').replace('Z', '+0000'), fmt)
        except ValueError:
            pass
    return datetime.datetime.fromtimestamp(Path(f).stat().st_mtime, datetime.timezone.utc) if f else None


def a6_judged(rows):
    """The agent rows of an A6 audit (w1_audit.py: rows with a pmid and the launch each ran in) a paper is judged on: a
    paper read again after a model switch, one with an agent in a redo launch, on its redo launches' agents (redo and
    redo-more-<k> alike), any other on main's and more-<k>'s (review of round 2: a break in redo-more-1 had been
    dropped)."""
    papers = [r for r in rows if r.get('pmid')]
    redone = {str(r['pmid']) for r in papers if a6_is_redo(r.get('launch'))}
    return [r for r in papers if str(r['pmid']) not in redone or a6_is_redo(r.get('launch'))]


def a6_audit(ev, label, papers, kept=None):
    """The copy's audit as both scorers take it (score_locked.a6_rows; the rules-only check's score_today.py in the main
    repository), from records/audit/A6-<label>/audit.json and rerun.txt (w1_audit.py A6-<label>): (broken, unaudited).
    Stops when there is no audit, when it holds no agent of a paper (w1_audit.py found no transcript: every paper's
    isolation is unchecked), or when it is older than the newest RESET.json of the kept run, main or redo (it judged an
    earlier run's agents: rerun.txt and the launch rows would not be this run's).
    broken: rerun.txt's papers (a6_judged: a redone paper judged on its redo launches, any other on main and more-<k>),
    less those whose only breaks are their model switch (A6_MODEL_BREAKS) when model_switch.json settled it: rerun_ok,
    or second_try_ok with its redo kept.
    unaudited: the papers of `papers` whose kept launch (a6_kept_agents; kept, when the caller has it) has no audited
    reader or no audited verifier (an audit.json row of role read and one of role verify with that launch), those with no
    kept launch, and those the audit lists without a reader or a verifier transcript (summary
    papers_without_reader_or_verifier): their kept rows have no audited agent behind them. A switch the switch rule
    settled is no break, but its paper is analysed only when the audit covered its kept launch."""
    P = eval_paths(ev)
    run, d = P['runs'] / f'A6-{label}', P['audit'] / f'A6-{label}'
    af, jf = d / 'rerun.txt', d / 'audit.json'
    if not af.exists() or not jf.exists():
        sys.exit(f'no audit of A6-{label}: run w1_audit.py A6-{label} first')
    audit = json.loads(jf.read_text())
    agents, summary = audit.get('agents') or [], audit.get('summary') or {}
    if not any(r.get('pmid') for r in agents):
        sys.exit(f"{jf} holds no agent of a paper (w1_audit.py found no transcript): every paper's isolation is unchecked")
    resets = [f for f in (run / 'RESET.json', run / 'redo' / 'RESET.json') if f.exists()]
    if not resets:
        sys.exit(f'A6-{label} is not kept yet: w1_setup.py reset-a6 {label}, then w1_audit.py A6-{label}')
    newest = max(record_time(json.loads(f.read_text()).get('reset_utc'), f) for f in resets)
    if record_time(summary.get('time'), jf) < newest:
        sys.exit(f'{jf} is older than the last reset-a6 {label} (main or --redo, {newest:%Y-%m-%d %H:%M} UTC): run '
                 f'w1_audit.py A6-{label} again')
    kept = a6_kept_agents(ev, label) if kept is None else kept
    redone, sw = a6_redone(ev, label), read_switches(P['logs'] / f'A6-{label}')
    kinds = collections.defaultdict(set)  # the breaks rerun.txt counts, by paper (w1_audit.main)
    for r in a6_judged(agents):
        if r.get('broken'):
            kinds[str(r['pmid'])] |= {v[1] for v in r.get('violations') or [] if v[0] == 'break'}
    broken = set(af.read_text().split())
    for p in sorted(broken):  # a model switch the switch rule settled: its outcome decides, not the audit's break for it
        o = (sw.get(p) or {}).get('outcome')
        if kinds[p] and kinds[p] <= A6_MODEL_BREAKS and (o == 'rerun_ok' or (o == 'second_try_ok' and p in redone)):
            broken.discard(p)
    seen = {(str(r['pmid']), r.get('role'), str(r.get('launch'))) for r in agents if r.get('pmid')}
    unaudited = {str(p) for p in papers if str(p) not in kept
                 or not all((str(p), role, kept[str(p)][0]) in seen for role in ('read', 'verify'))}
    unaudited |= {str(p) for p in summary.get('papers_without_reader_or_verifier') or [] if str(p) in set(map(str, papers))}
    return broken, unaudited


MISSED_BY = 'verifier (missed values)'  # catlog.py MISSED: such a row's read_prompt is verify.md's hash (row_stamp)
FREEZE_TAG = 'catlog-freeze-20261109'  # the main repository's tag on the copy's snapshot of 9 November 2026


def freeze_stamp(repo=None):
    """The pipeline_commit stamp of the frozen copy: the commit FREEZE_TAG names, its first 12 characters (fb0cf1758951)."""
    c = git(repo or REPO, 'rev-parse', '--verify', '--quiet', f'{FREEZE_TAG}^{{commit}}')
    if not c:
        raise SystemExit(f'the tag {FREEZE_TAG} names no commit in {repo or REPO}')
    return c[:12]


def a6_stamp_problems(rows, manifest, want=None):
    """{pmid: [problems]}: kept rows of the copy whose stamps are not the frozen copy's. pipeline_commit must be the
    commit the main repository's tag FREEZE_TAG names (freeze_stamp; want), and so must MANIFEST.json's
    a6.pipeline_commit_stamp, or this stops (a freeze moved the copy to another snapshot, and the manifest with it): no
    '+dirty' (a harness file differed from the snapshot at add) and no blank (catlog.git_commit leaves it blank only for
    a folder that is not its own repository, never the copy, or when git fails). read_prompt and verify_prompt must be
    prompt_hashes_stamp_style's hashes of read.md and verify.md (a missed-values row's read_prompt is verify.md's:
    catlog.row_stamp), or blank: catlog.prompt_stamp leaves a prompt stamp blank by design when it cannot tell which
    prompt an agent followed (no `model` key in its work file, a prompt file newer than the work file or changed since
    the claim), never a wrong hash; a prompt edited in the copy shows as '+dirty' in pipeline_commit."""
    have = (manifest.get('a6') or {}).get('pipeline_commit_stamp')
    ph = manifest.get('prompt_hashes_stamp_style') or {}
    if not (have and ph.get('read.md') and ph.get('verify.md')):
        raise SystemExit('MANIFEST.json names no a6.pipeline_commit_stamp or prompt hashes (w1_setup.py freeze)')
    want = want or freeze_stamp()
    if have != want:
        raise SystemExit(f'MANIFEST.json a6.pipeline_commit_stamp is {have}, the tag {FREEZE_TAG} names {want}: the copy '
                         'was moved off the frozen snapshot')
    out = {}
    for r in rows:
        rp = ph['verify.md'] if r.get('read_by') == MISSED_BY else ph['read.md']
        bad = [f'{k} {r.get(k)!r}' for k, ok in (('pipeline_commit', r.get('pipeline_commit') == want),
                                                ('read_prompt', r.get('read_prompt') in ('', rp)),
                                                ('verify_prompt', r.get('verify_prompt') in ('', ph['verify.md']))) if not ok]
        if bad:
            out.setdefault(str(r.get('pmid')), set()).update(bad)
    return {p: sorted(v) for p, v in out.items()}


def a6_pin_problems(ev, repo=None):
    """[problems]: the pin of the sets after the W1 rounds (LATER_LABELS) to the frozen copy, checked where they are laid
    down (w1_setup.py a6-papers), launched (run_a6.py) and checked (w1_setup.py check), not only when they are scored:
    catlog-copy's HEAD and MANIFEST.json's a6.pipeline_commit_stamp must both be the commit FREEZE_TAG names
    (freeze_stamp, fb0cf1758951), or a whole read would be spent on another snapshot and refused only at scoring."""
    P = eval_paths(ev)
    try:
        want = freeze_stamp(repo)
    except SystemExit as e:
        return [str(e)]
    head = git(P['a6'], 'rev-parse', 'HEAD')
    try:
        have = (json.loads(P['manifest'].read_text()).get('a6') or {}).get('pipeline_commit_stamp')
    except (OSError, json.JSONDecodeError):
        have = None
    out = []
    if head[:12] != want:
        out.append(f"catlog-copy is at {head[:12] or 'no commit'}, the tag {FREEZE_TAG} names {want}")
    if have != want:
        out.append(f'MANIFEST.json a6.pipeline_commit_stamp is {have}, the tag {FREEZE_TAG} names {want}')
    return out
