#!/usr/bin/env python3
"""Provenance for the catalog rows added before stamping (2026-10-21), reconstructed from evidence only.

`add` stamps every new row with its reader and verifier model ids, the prompt hashes they followed and the code commit
(catlog.row_stamp). Rows added earlier carry none. For each such row this script looks for evidence of what read it:
 1. the add that brought the row in: the first log.tsv `add` line of its paper at or after the row's `added` minute (a
    paper can be added several times after rereads); a row a `recover` brought back goes to the add that first judged
    it, through its copy in rejected.jsonl;
 2. the work files that add used: work/<PMID>.read.json and .verify.json, and the .missed pair when the verifier wrote
    one, as they stood in that minute (`next` and `reread` move older versions to work/old/<name>.<unix time>.json; a
    move keeps the file's mtime). The row must be one of the rows of that read file, or of the missed read file: then
    the verifier read it (`read_by` 'verifier (missed values)', its read_prompt a verify.md hash, as catlog.row_stamp).
    Rows are matched by metric, first number and quote; when both files hold such a row (an OCR table quoted as one
    block), the file whose copy names the row's enzyme, substrate, variant and location (as its reader wrote them)
    holds it, and when both or neither do, the row gets no line. A row neither file holds by its quote (a verifier
    replaced it, e.g. a garbled OCR line, and the row keeps no `corrected`) is looked up by metric, first number,
    location, substrate and variant instead, and goes to the one file that has such a row, else gets no line;
 3. the agent that wrote each file: the subagent transcript (~/.claude/projects/*/<session>/subagents/**/agent-*.jsonl;
    batches also ran from chats opened in other folders, e.g. the first reads of 2026-10-07 from realkcat, so every
    project folder is searched for transcripts that name this data folder) that names the file and had a tool call
    running when the file got its mtime; a Sonnet retry or the missed-values verifier is its own transcript. Its model
    id is the `model` of the assistant messages of its tool calls up to that call; an agent that switched model on the
    way (a fallback mid-run) gets every model in order, 'A>B', and the evidence its calls per model. A file a later
    read overwrote in place (early rereads, before `next` set old files aside) is no longer on disk: then the agent
    told to write it whose last call naming it came last before the add (no row check; blank when the missed pair
    might hold the row or a chat may have edited it);
 4. the prompt that agent followed: the text it loaded, hashed like the live stamps (sha256[:12] of the file's bytes):
    its Read of prompts/read.md or verify.md rebuilt line by line, or a `cat` output that holds a known version whole
    (an uncommitted edit shown whole: cut at the commit's version's first and last lines). When the transcript holds no
    complete copy (or a cut one that agrees with the commit's version), the version in git where main pointed then,
    unless agents of that commit are seen loading another text (an uncommitted edit was in use): then blank, never a
    guess;
 5. the commit main pointed to while the add ran (main's reflog; the minute of the log line, narrowed to the seconds of
    a chat's `catlog.py add` call that names the paper): blank when main moved to a commit that changed pipeline code
    meanwhile, or when the add ran before main's first commit. Whether the folder had uncommitted pipeline edits then is not knowable: no '+dirty'. task_prompt is not
    reconstructed.
Output: sources/provenance_backfill.tsv, one line per row with its evidence (the add's time, the reader's and verifier's
transcript file names) and how = 'reconstructed'; a row with no matching transcript gets no line, except that an
earlier line stays as it was once a transcript it names is gone (archived to Nova 2026-10-28, keep_gone: the TSV is
then the record; a rebuild from the raw transcripts needs them restored under ~/.claude/projects, where their saved
tool outputs are looked up). Every prompt hash
written has its exact text in sources/prompt_versions/<hash>.md (`catlog.py prompt HASH` prints it). The export merges
these lines into unstamped rows' provenance, marked reconstructed, never over a row's own stamp; recheck counts them.
Rerunnable and cheap: each parsed transcript is cached (enrich/provenance_transcripts.json.gz, keyed by size and
mtime), so a rerun before a release parses only new transcripts (about 40 s). Reads the data folder, git and the
transcripts only; writes the TSV, the prompt texts and the cache. Run `catlog.py export` after it.
Usage: python3 tools/provenance_backfill.py [--root DIR] [--out TSV] [--prompts DIR] [--cache FILE] [--transcripts DIR]
"""
import argparse, collections, csv, datetime, gzip, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
FIELDS = ('row_id', 'read_by', 'reader_model', 'verifier_model', 'read_prompt', 'verify_prompt', 'pipeline_commit',
          'evidence', 'how')
HOW = 'reconstructed'
MISSED = 'verifier (missed values)'  # catlog.MISSED: read_by of the values the verifier found the reader had skipped
STAMP = ('read_by', 'reader_model', 'verifier_model', 'read_prompt', 'verify_prompt', 'task_prompt', 'pipeline_commit')
PIPELINE = ('catlog.py', 'prompts', 'tools/units.py', '.claude/workflows/catlog-batch.js', '.claude/agents/catlog-reader.md')
CACHE_VERSION = 5
PID = r'(?:\d{1,9}|NP[0-9A-F]{8})'
WORKFILE = re.compile(rf'(?<![\w.])({PID}\.(?:missed\.)?(?:read|verify)\.json)')
TARGET = re.compile(rf'Write (?:your verdicts to )?\S*?work/({PID}\.(?:missed\.)?(?:read|verify)\.json)')
OLD = re.compile(rf'^({PID})\.((?:missed\.)?(?:read|verify))\.(\d{{9,11}})\.json$')
CUR = re.compile(rf'^({PID})\.((?:missed\.)?(?:read|verify))\.json$')
NUMBERED = re.compile(r'^\s*(\d+)(?:\t|→)(.*)$')  # a Read tool result line: "12\ttext" (older: "    12→text")
PROMPTS = ('read.md', 'verify.md')
BIG = 200_000  # transcript lines longer than this are tool results (page images, long reads): only their time is read
SLACK = 2.0  # seconds around a tool call within which a file it wrote gets its mtime


# ---------- transcripts ----------

def iso(ts):
    return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()


WRITES = re.compile(r"json\.dump|write_text|\.write\(|open\([^)]*['\"][wa]\+?['\"]|>\s*\S*\.json|\btee\b|\b(?:cp|mv)\s")


def is_write(name, inp, s):
    """A call that may write the work file it names, itself or through the script it saves (only breaks ties between
    transcripts and picks writers when a file is gone; mtime decides otherwise)."""
    if name in ('Write', 'Edit', 'MultiEdit'):
        return bool(WORKFILE.search(str(inp.get('file_path', '')))) or bool(WRITES.search(str(inp.get('content', ''))))
    return bool(WRITES.search(s))


def prompt_lines(content):
    """Line number -> text from a Read tool result, starting at its first numbered line and stopping where the numbering
    breaks (a system note appended after the file)."""
    text = content if isinstance(content, str) else '\n'.join(
        c.get('text', '') for c in content or [] if isinstance(c, dict) and c.get('type') == 'text')
    out, want = {}, None
    for line in text.split('\n'):
        m = NUMBERED.match(line)
        if not m or (want is not None and int(m.group(1)) != want):
            if out:
                break
            continue
        n = int(m.group(1))
        out[n], want = m.group(2), n + 1
    return out


def output_text(content):
    """A tool result's text; an output too large for the transcript is read from the file it was saved to."""
    text = content if isinstance(content, str) else '\n'.join(
        c.get('text', '') for c in content or [] if isinstance(c, dict) and c.get('type') == 'text')
    m = re.match(r'<persisted-output>\s*Output too large \([^)]*\)\. Full output saved to: (\S+)', text)
    if m:
        try:
            return Path(m.group(1)).read_text(errors='replace')
        except OSError:
            return ''
    return text


def find_version(out, name, known):
    """The hash of the known version of prompts/<name> a command's output holds whole (a `cat` of the prompt, often
    with other commands' output around it): the longest version found at a line start and ending at a line end; ''."""
    best = ('', 0)
    for h, n, v in known:
        if n != name or len(v) <= best[1]:
            continue
        i = out.find(v)
        while i >= 0:
            if (i == 0 or out[i - 1] == '\n') and (i + len(v) == len(out) or out[i + len(v)] == '\n'):
                best = (h, len(v))
                break
            i = out.find(v, i + 1)
    return best[0]


KNOWN = []  # (hash, prompt name, text without its final newlines) of every known prompt version, for scan()


def scan(path, known=None):
    """One transcript -> what this script needs from it (cached): its agent id, description and working directory,
    first and last times, the work files it names (task text and tool inputs) and those its task says to write, every
    tool call as [start, end, model index], the calls naming a work file and those that may write it, its
    `catlog.py add` calls with the paper ids they name, and how it first loaded each prompt: [time, 'text', key, path]
    (a complete Read, rebuilt line by line: texts[key]), [time, 'h', hash, path] (a `cat` whose output holds a known
    version whole) or [time, 'raw', key, path] (a `cat` output no known version matched: texts[key], matched again
    later). Returns (summary, texts)."""
    known = KNOWN if known is None else known
    s = {'agent': '', 'desc': '', 'start': None, 'end': None, 'files': set(), 'targets': set(), 'calls': [],
         'writes': [], 'named': [], 'prompts': {}, 'models': [], 'adds': []}
    texts = {}
    try:
        s['desc'] = str(json.loads(Path(str(path)[:-len('.jsonl')] + '.meta.json').read_text()).get('description', ''))
    except (OSError, ValueError, AttributeError):
        pass
    pending, reads, cats = {}, {}, {}  # tool_use id -> call index; prompt Read -> (name, offset, limit, path); cat
    got = {n: {} for n in PROMPTS}  # the lines of each prompt seen so far
    eof = {n: None for n in PROMPTS}  # the last line number, once a read reached the end of the file

    def model_ix(m):
        if m not in s['models']:
            s['models'].append(m)
        return s['models'].index(m)

    def user_text(t):
        s['files'].update(WORKFILE.findall(t))
        tg = set(TARGET.findall(t))
        for f in list(tg):  # a verifier may write the missed file (its task allows it)
            if f.endswith('.verify.json') and '.missed.' not in f:
                tg.add(f[:-len('.verify.json')] + '.missed.read.json')
        s['targets'].update(tg)

    def seen(t):
        s['start'] = t if s['start'] is None else min(s['start'], t)
        s['end'] = t if s['end'] is None else max(s['end'], t)

    def result(c, t):
        k = pending.pop(c.get('tool_use_id'), None)
        if k is not None and t is not None:
            s['calls'][k][1] = t
        r = reads.pop(c.get('tool_use_id'), None)
        if r and r[0] not in s['prompts']:
            name, off, lim, fp = r
            lines = prompt_lines(c.get('content'))
            if lines and min(lines) == (int(off) if off else 1):
                got[name].update(lines)
                if not lim or len(lines) < int(lim):
                    eof[name] = max(lines)
            n = eof[name]
            if n and all(i in got[name] for i in range(1, n + 1)):
                text = '\n'.join(got[name][i] for i in range(1, n + 1))
                key = hashlib.sha256(text.encode()).hexdigest()[:16]
                texts[key] = text
                s['prompts'][name] = [t, 'text', key, fp]
        name, fp = cats.pop(c.get('tool_use_id'), (None, ''))
        if name and name not in s['prompts']:
            out = output_text(c.get('content'))
            h = find_version(out, name, known)
            if h:
                s['prompts'][name] = [t, 'h', h, fp]
            elif out.strip():
                key = hashlib.sha256(out.encode()).hexdigest()[:16]
                texts[key] = out[:60000]
                s['prompts'][name] = [t, 'raw', key, fp]

    with open(path, 'rb') as fh:
        data = fh.read()
    for line in data.split(b'\n'):
        if not line.strip():
            continue
        if len(line) > BIG and line.find(b'"tool_use_id"', 0, 4000) >= 0:  # a long tool result: only its time is read
            ts = re.findall(rb'"uuid":"[0-9a-f-]{36}","timestamp":"([^"]+)"', line[-4000:])
            ids = [i.decode() for i in re.findall(rb'"tool_use_id":"(toolu_\w+)"', line[:4000])]
            if ts and not any(i in reads or i in cats for i in ids):
                t = iso(ts[-1].decode())
                seen(t)
                for i in ids:
                    k = pending.pop(i, None)
                    if k is not None:
                        s['calls'][k][1] = t
                continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        t = iso(d['timestamp']) if isinstance(d.get('timestamp'), str) else None
        if t is not None:
            seen(t)
        s['agent'] = s['agent'] or str(d.get('agentId') or '')
        s['cwd'] = s.get('cwd') or str(d.get('cwd') or '')
        msg = d.get('message') if isinstance(d.get('message'), dict) else {}
        content = msg.get('content')
        if d.get('type') == 'assistant' and isinstance(content, list) and t is not None:
            mi = model_ix(str(msg.get('model') or ''))
            for c in content:
                if not isinstance(c, dict) or c.get('type') != 'tool_use':
                    continue
                inp = c.get('input') if isinstance(c.get('input'), dict) else {}
                js = json.dumps(inp, ensure_ascii=False)
                names = set(WORKFILE.findall(js))
                s['files'] |= names
                pending[c.get('id')] = len(s['calls'])
                s['calls'].append([t, None, mi])
                if names:
                    s['named'].append([len(s['calls']) - 1, sorted(names)])
                    if is_write(c.get('name'), inp, js):
                        s['writes'].append([len(s['calls']) - 1, sorted(names)])
                fp = str(inp.get('file_path', ''))
                if c.get('name') == 'Read' and fp.endswith(tuple(f'prompts/{n}' for n in PROMPTS)):
                    reads[c.get('id')] = (fp.rsplit('/', 1)[1], inp.get('offset'), inp.get('limit'), fp)
                m = re.search(r'\bcat\s+[\'"]?(\S*?prompts/(read|verify)\.md)\b', str(inp.get('command', ''))) \
                    if c.get('name') == 'Bash' else None
                if m:
                    cats[c.get('id')] = (f'{m.group(2)}.md', m.group(1))
                cmd = str(inp.get('command', '')) if c.get('name') == 'Bash' else ''
                if re.search(r'catlog\.py["\']?\s+add\b', cmd):  # an add: its time pins the commit it ran under
                    s['adds'].append([len(s['calls']) - 1, sorted(set(re.findall(rf'(?<![\w.]){PID}(?![\w.])', cmd)))])
        elif d.get('type') == 'user':
            if isinstance(content, str):
                user_text(content)
                continue
            for c in content if isinstance(content, list) else []:
                if not isinstance(c, dict):
                    continue
                if c.get('type') == 'text':
                    user_text(str(c.get('text', '')))
                elif c.get('type') == 'tool_result':
                    result(c, t)
    s['files'], s['targets'] = sorted(s['files']), sorted(s['targets'])
    return s, texts


def is_agent(rel):
    """A subagent's transcript (a reader, verifier or other worker), not a chat's own."""
    return '/subagents/' in f'/{rel}'


PROJECTS = Path.home() / '.claude' / 'projects'  # Claude Code's transcripts: one folder per working directory


def _scan_one(a):
    path, rel, needle = a
    st = os.stat(path)
    if needle:  # a transcript of another folder's chat counts only when it names this data folder
        with open(path, 'rb') as fh:
            if needle.encode() not in fh.read():
                return rel, st.st_size, st.st_mtime_ns, None, {}
    s, texts = scan(path)
    return rel, st.st_size, st.st_mtime_ns, s, texts


def load_transcripts(base, cache_path, jobs=6, g=None, needle=''):
    """Every Claude Code transcript under `base` (the projects folder: one folder per working directory), parsed once:
    subagents' (readers, verifiers, ...) and chats' own (whose `catlog.py add` calls pin add times). A transcript that
    does not contain `needle` (this data folder's path; batches were also run from chats opened in other folders) is
    skipped. An unchanged file (same size and mtime) comes from the cache. `g` (Git): the prompt versions a `cat`
    output is matched against; the cache keeps the text of every version a transcript was matched to and gives them
    back to `g`, so a cached match never names a version this run does not know. Returns ({path under base: summary},
    {text key: text})."""
    global KNOWN
    cache = {'v': CACHE_VERSION, 'needle': needle, 'files': {}, 'texts': {}, 'versions': {}}
    if cache_path and Path(cache_path).exists():
        try:
            with gzip.open(cache_path, 'rt') as fh:
                c = json.load(fh)
            if c.get('v') == CACHE_VERSION and c.get('needle') == needle:
                cache = c
        except (OSError, ValueError, EOFError):
            pass
    if g is not None:
        for h, (name, text) in cache.get('versions', {}).items():
            if h12(text.encode()) == h:
                g.add(text.encode(), name)
    KNOWN = g.known() if g is not None else []
    base = Path(base)
    todo, keep = [], {}
    for p in sorted(base.glob('*/*/subagents/**/agent-*.jsonl')) + sorted(base.glob('*/*.jsonl')):
        rel = str(p.relative_to(base))
        st = p.stat()
        hit = cache['files'].get(rel)
        if hit and hit[0] == st.st_size and hit[1] == st.st_mtime_ns:
            keep[rel] = hit
        else:
            todo.append((str(p), rel, needle))
    if todo:
        print(f'parsing {len(todo)} transcripts ({len(keep)} cached)', file=sys.stderr)
        if jobs > 1 and len(todo) > 50:
            import multiprocessing
            with multiprocessing.get_context('fork').Pool(jobs) as pool:
                res = list(pool.imap_unordered(_scan_one, todo, chunksize=20))
        else:
            res = [_scan_one(a) for a in todo]
        for rel, size, mt, s, texts in res:
            keep[rel] = [size, mt, s]
            cache['texts'].update(texts)
    loads = [(n, e) for _, _, s in keep.values() if s for n, e in s['prompts'].items()]
    used = {e[2] for _, e in loads if e[1] in ('text', 'raw')}
    versions = {e[2]: [n, (g.versions[e[2]].decode('utf-8', 'replace') if g is not None and e[2] in g.versions
                           else cache.get('versions', {}).get(e[2], [n, ''])[1])] for n, e in loads if e[1] == 'h'}
    cache = {'v': CACHE_VERSION, 'needle': needle, 'files': keep,
             'texts': {k: v for k, v in cache['texts'].items() if k in used},
             'versions': {h: v for h, v in versions.items() if v[1]}}
    if cache_path and todo:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(f'{cache_path}.{os.getpid()}.tmp')
        with gzip.open(tmp, 'wt') as fh:
            json.dump(cache, fh, separators=(',', ':'))
        os.replace(tmp, cache_path)
    return {rel: v[2] for rel, v in keep.items() if v[2]}, cache['texts']


# ---------- git: prompt versions and main's history ----------

def git(root, *a, text=True):
    return subprocess.run(['git', '--no-optional-locks', '-C', str(root), *a], capture_output=True, text=text, timeout=120,
                          env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})


def h12(b):
    return hashlib.sha256(b).hexdigest()[:12]


class Git:
    """main's reflog (when it pointed where), files at commits, and every prompt version git or a saved copy holds."""

    def __init__(self, root, branch='main', saved=()):
        self.root, self.shown, self.diffs, self._known = root, {}, {}, None
        r = git(root, 'log', '-g', '--format=%H %gd', '--date=unix', f'refs/heads/{branch}')
        moves = []
        for line in (r.stdout.splitlines() if r.returncode == 0 else []):
            m = re.match(r'([0-9a-f]{40}) \S*@\{(\d+)\}', line)
            if m:
                moves.append((int(m.group(2)), m.group(1)))
        self.moves = sorted(moves)
        self.versions, self.names = {}, collections.defaultdict(set)  # hash -> bytes; hash -> prompt file names
        r = git(root, 'log', '--all', '--format=%H', '--', *(f'prompts/{n}' for n in PROMPTS))
        for c in (r.stdout.split() if r.returncode == 0 else []):
            for n in PROMPTS:
                b = self.show(c, f'prompts/{n}')
                if b:
                    self.versions.setdefault(h12(b), b)
                    self.names[h12(b)].add(n)
        heads = {n: {b.split(b'\n', 1)[0] for h, b in self.versions.items() if n in self.names[h]} for n in PROMPTS}
        for d in saved:  # saved copies (work/prompts/, prompt_versions/): named by their first line
            for p in sorted(Path(d).glob('*.md')) if Path(d).is_dir() else []:
                b = p.read_bytes()
                if h12(b) == p.stem:
                    self.versions.setdefault(p.stem, b)
                    self.names[p.stem].update(n for n in PROMPTS if b.split(b'\n', 1)[0] in heads[n])
        self.by_text = {}
        for h, b in self.versions.items():
            self.by_text.setdefault(b.decode('utf-8', 'replace'), h)

    def known(self):
        """(hash, prompt name, text without its final newline) of every version (scan's KNOWN, find_version)."""
        if self._known is None:
            self._known = [(h, n, b.decode('utf-8', 'replace').rstrip('\n')) for h, b in self.versions.items()
                           for n in self.names[h]]
        return self._known

    def add(self, b, name):
        """A version known from a transcript or the cache (not in git): its hash."""
        h = h12(b)
        if h not in self.versions:
            self.versions[h] = b
            self.by_text.setdefault(b.decode('utf-8', 'replace'), h)
        if name not in self.names[h]:
            self.names[h].add(name)
            self._known = None
        return h

    def show(self, commit, f):
        k = (commit, f)
        if k not in self.shown:
            r = git(self.root, 'show', f'{commit}:{f}', text=False)
            self.shown[k] = r.stdout if r.returncode == 0 else None
        return self.shown[k]

    def head_at(self, t):
        """The commit main pointed to at time t (None before the first)."""
        h = None
        for when, c in self.moves:
            if when > t:
                break
            h = c
        return h

    def commit_at(self, lo, hi):
        """main during [lo, hi) (when an add ran): the commit it pointed to, or the first of several when none of the
        later ones changed pipeline code; '' when main moved to new pipeline code meanwhile (which commit the add
        ran under is then unknowable) or pointed nowhere yet."""
        first = self.head_at(lo)
        if first is None:
            return ''
        for c in [c for when, c in self.moves if lo < when < hi]:
            k = (first, c)
            if k not in self.diffs:
                r = git(self.root, 'diff', '--name-only', first, c, '--', *PIPELINE)
                self.diffs[k] = r.returncode != 0 or bool(r.stdout.strip())
            if self.diffs[k]:
                return ''
        return first

    def prompt_at(self, name, t):
        """(hash, commit) of prompts/<name> in the commit main pointed to at t."""
        c = self.head_at(t)
        b = self.show(c, f'prompts/{name}') if c else None
        return (h12(b), c) if b else ('', c)

    def match_text(self, text):
        """The hash of the known version a rebuilt text is (the Read tool shows each line, not whether the file ends
        in a newline): '' when none."""
        for t in (text, text + '\n', text.rstrip('\n') + '\n'):
            if t in self.by_text:
                return self.by_text[t]
        return ''


# ---------- the data folder ----------

def minute_of(s):
    try:
        return time.mktime(time.strptime(str(s)[:16], '%Y-%m-%d %H:%M'))
    except ValueError:
        return None


def log_events(root):
    """pmid -> [(minute, event, kept, logged time)] for its add and recover lines, in log order."""
    ev = collections.defaultdict(list)
    with open(Path(root) / 'log.tsv', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            f = line.rstrip('\n').split('\t')
            if len(f) > 3 and f[2] in ('add', 'recover'):
                t = minute_of(f[0])
                kept = next((int(x[5:]) for x in f[3:] if re.fullmatch(r'kept=\d+', x)), 0)
                if t is not None:
                    ev[f[1]].append((t, f[2], kept, f[0][:16]))
    return ev


def work_versions(root):
    """(pmid, kind) -> [(path, mtime, moved_at or None)]: the work files now in work/ and the versions moved to work/old/."""
    out = collections.defaultdict(list)
    for d, pat, old in ((Path(root) / 'work', CUR, False), (Path(root) / 'work' / 'old', OLD, True)):
        if not d.is_dir():
            continue
        with os.scandir(d) as it:
            for e in it:
                m = pat.match(e.name)
                if m and e.is_file():
                    out[(m.group(1), m.group(2))].append((e.path, e.stat().st_mtime, int(m.group(3)) if old else None))
    return out


def at_add(versions, minute):
    """(path, mtime) of the version of a work file an add in this minute read: the newest written before the minute
    ended that was not yet moved aside when it began; None if none."""
    ok = [(mt, p) for p, mt, moved in versions if mt < minute + 60 and (moved is None or moved >= minute)]
    return (max(ok)[1], max(ok)[0]) if ok else None


def first_number(v):
    m = re.search(r'\d+(?:\.\d+)?', str(v or ''))
    return m.group(0) if m else ''


def squash(s):
    return re.sub(r'\s+', '', str(s or '')).lower()[:80]


def row_key(r):
    return (r.get('metric'), first_number(r.get('raw_value')), squash(r.get('quote')))


def reader_version(row):
    """The row as its reader wrote it (a verifier's fix undone: catlog.judge keeps the reader's fields in `corrected`)."""
    r = dict(row)
    for k, v in (row.get('corrected') or {}).items():
        if isinstance(v, dict) and 'reader' in v:
            r[k] = v['reader']
    return r


IDENTITY = ('enzyme', 'substrate', 'variant', 'location')


def norm(v):
    return ' '.join(str(v or '').split()).lower()


def identity(r):
    """What a row measured, to tell apart two rows with the same row_key (an OCR table's whole block as the quote)."""
    return tuple(norm(r.get(f)) for f in IDENTITY)


def cell_key(r):
    """A row by its cell, without its quote: a verifier may have replaced a garbled OCR quote with the printed line, and
    rows added before 2026-10-09 11:12 (commit 6ae8fd4) keep no `corrected` to tell what the reader wrote."""
    return (r.get('metric'), first_number(r.get('raw_value')), *(norm(r.get(f)) for f in ('location', 'substrate', 'variant')))


class Files:
    """The rows of work files, each file parsed once."""

    def __init__(self):
        self.keys = {}

    def rows(self, path):
        """(row_key -> the identities of the file's rows with that key, the cell_keys of its rows); None when the file
        cannot be read."""
        if path not in self.keys:
            try:
                d = json.loads(Path(path).read_text())
                rows = [r for r in (d.get('rows', []) if isinstance(d, dict) else []) if isinstance(r, dict)]
                keys = {}
                for r in rows:
                    keys.setdefault(row_key(r), set()).add(identity(r))
                self.keys[path] = keys, {cell_key(r) for r in rows}
            except (OSError, ValueError):
                self.keys[path] = None
        return self.keys[path]

    def copies(self, version, row):
        """The identities of this file version's rows whose key is the row's, as stored or as its reader wrote it."""
        f = self.rows(version[0]) if version else None
        return (f[0].get(row_key(row), set()) | f[0].get(row_key(reader_version(row)), set())) if f else set()

    def has(self, version, row):
        return bool(self.copies(version, row))

    def has_cell(self, version, row):
        """True when a row of this file version has the row's cell_key, as stored or as its reader wrote it."""
        f = self.rows(version[0]) if version else None
        return bool(f) and (cell_key(row) in f[1] or cell_key(reader_version(row)) in f[1])


# ---------- matching ----------

class Writers:
    """Which transcript wrote a work file version: one that names the file and had a tool call running at its mtime;
    for a version no longer on disk, the agent told to write it whose last writing call came last before the add."""

    def __init__(self, trans):
        self.trans = trans
        self.by_file = collections.defaultdict(list)
        self.chat_writes = collections.defaultdict(list)  # name -> end times of chats' own calls that may write it
        for rel, s in trans.items():
            for f in s['files'] if is_agent(rel) else ():
                self.by_file[f].append(rel)
            if not is_agent(rel):
                for i, names in s['writes']:
                    c = s['calls'][i]
                    for f in names:
                        self.chat_writes[f].append(c[1] if c[1] is not None else c[0])
        self.memo = {}

    def runs(self, rel, i):
        """[model id, tool calls] of the agent's calls up to call i (the one that wrote the file), one per stretch of
        calls by the same model, in order: more than one when it switched model on the way (a fallback mid-run).
        '<synthetic>' (an error message) is no model."""
        s, out = self.trans[rel], []
        for c in s['calls'][:i + 1]:
            m = s['models'][c[2]] if s['models'] else ''
            if not m or m.startswith('<'):
                continue
            if out and out[-1][0] == m:
                out[-1][1] += 1
            else:
                out.append([m, 1])
        return out

    def model(self, rel, i):
        """The model id of the calls up to call i, or every one in order ('A>B') when the agent switched model."""
        runs = self.runs(rel, i)
        if runs:
            return '>'.join(m for m, _ in runs)
        real = {m for m in self.trans[rel]['models'] if m and not m.startswith('<')}
        return real.pop() if len(real) == 1 else ''

    def find(self, name, mtime):
        """(transcript, index of the call that wrote it, '') or (None, None, why)."""
        if (name, mtime) in self.memo:
            return self.memo[(name, mtime)]
        hits = []
        for rel in self.by_file.get(name, ()):
            s = self.trans[rel]
            live = [i for i, c in enumerate(s['calls'])
                    if c[0] - SLACK <= mtime <= (c[1] if c[1] is not None else (s['end'] or 0)) + SLACK]
            if live:
                hits.append((rel, live))
        if len(hits) > 1:  # prefer the agent whose task was to write this file, then the one whose running call wrote it
            hits = [h for h in hits if name in self.trans[h[0]]['targets']] or hits
        if len(hits) > 1:
            wrote = [h for h in hits if set(h[1]) & {i for i, names in self.trans[h[0]]['writes'] if name in names}]
            hits = wrote if len(wrote) == 1 else hits
        if not hits:
            r = (None, None, 'no transcript had a call running when it was written' if name in self.by_file
                 else 'no transcript names it')
        elif len(hits) > 1:
            r = (None, None, 'several transcripts could have written it')
        else:
            r = (hits[0][0], hits[0][1][-1], '')
        self.memo[(name, mtime)] = r
        return r

    def last_before(self, name, until):
        """(transcript, index of its last call naming the file, '', written) of the agent whose task was to write this
        file, that has a call that may write it, and whose last call naming it ended latest before `until`: the version
        an add read when a later read overwrote it in place (before `next` set old files aside). (None, None, why, None)
        when there is none, or when a chat's own call may have written the file after that agent."""
        best = None
        for rel in self.by_file.get(name, ()):
            s = self.trans[rel]
            if name not in s['targets'] or not any(name in names for _, names in s['writes']):
                continue  # a reader that kept an earlier read only validates it
            for i, names in s['named']:
                c = s['calls'][i]
                end = c[1] if c[1] is not None else c[0]
                if name in names and end < until and (best is None or end > best[0]):
                    best = (end, rel, i)
        if best is None:
            return None, None, 'no transcript wrote it before the add', None
        if any(best[0] < t < until for t in self.chat_writes.get(name, ())):
            return None, None, 'a chat may have edited it after its agent wrote it', None
        return best[1], best[2], '', best[0]


TRUNC = re.compile(r'\n\n\.\.\. \[(\d+) characters truncated\] \.\.\.\n\n')  # a long failing command's output, cut


def agrees(out, version):
    """True when a cut output (its middle replaced by TRUNC's marker) shows `version` whole wherever it shows text: the
    version starts at a line start before the cut and fills the cut exactly, as far as the output lets one tell."""
    m = TRUNC.search(out)
    v = version.rstrip('\n')
    first = v.split('\n', 1)[0]
    p = out.find(first)
    while p >= 0 and not (p == 0 or out[p - 1] == '\n'):
        p = out.find(first, p + 1)
    if not m or p < 0 or p > m.start():
        return False
    head = out[p:m.start()]
    full = head + v[len(head):len(head) + int(m.group(1))] + out[m.end():]
    return full.startswith(v) and (len(full) == len(v) or full[len(v)] == '\n')


def cut_out(out, version):
    """The text of a prompt version no one recorded, from a `cat` output that shows it whole: from the line the
    commit's version starts with to the line it ends with (each found exactly once, at line starts), plus the one final
    newline every version has. None when either boundary is not found exactly once (an edit there, or a cut output)."""
    if TRUNC.search(out):
        return None
    v = version.rstrip('\n')
    first, last = v.split('\n', 1)[0], v.rsplit('\n', 1)[-1]
    starts = [m.start() for m in re.finditer('^' + re.escape(first) + '$', out, re.M)]
    if len(starts) != 1:
        return None
    ends = [m.end() for m in re.finditer('^' + re.escape(last) + '$', out[starts[0]:], re.M)]
    return out[starts[0]:starts[0] + ends[0]] + '\n' if len(ends) == 1 else None


class Prompts:
    """The prompt each agent followed: the text its transcript shows it loading, else the commit's version when no
    uncommitted edit is seen in use under that commit."""

    def __init__(self, trans, texts, g, root):
        self.trans, self.texts, self.g = trans, texts, g
        self.root = str(Path(root).resolve())
        self.uncommitted = collections.defaultdict(set)  # (prompt, commit) -> other texts agents loaded meanwhile
        loads = sorted(((e[1] != 'text', name, e) for rel, s in trans.items() if is_agent(rel)
                        for name, e in s['prompts'].items() if self.ours(e, s)),
                       key=lambda x: x[0])  # complete Reads first: they make versions known
        for _, name, e in loads:
            h, exact = self.load(name, e)
            if h is None or not exact:
                continue  # nothing usable, or a cut copy that agrees with the commit's version
            own, c = g.prompt_at(name, e[0])
            if c and h != own:
                self.uncommitted[(name, c)].add(h or 'a text no known version matches')

    def ours(self, e, s):
        """A load of this folder's prompt (an agent may also read a worktree's or another folder's copy)."""
        p = e[3] if len(e) > 3 else ''
        return p.startswith(self.root + '/') if p.startswith('/') else s.get('cwd') == self.root

    def load(self, name, e):
        """(hash, exact) of what one prompt load shows: exact False for a cut output that agrees with the version of the
        commit main pointed to then; ('', True) for a text no known version matches; (None, False) for no usable text."""
        kind, v = e[1], e[2]
        if kind == 'h':
            return v, True
        text = self.texts.get(v)
        if text is None:
            return None, False
        if kind == 'text':  # a complete Read: its exact lines, so also a version nothing else holds
            return self.g.match_text(text) or self.g.add((text if text.endswith('\n') else text + '\n').encode(), name), True
        h = find_version(text, name, self.g.known())
        if h:
            return h, True
        own, _ = self.g.prompt_at(name, e[0])
        if own and agrees(text, self.g.versions[own].decode('utf-8', 'replace')):
            return own, False
        # an edit not committed: the text as the agent loaded it, cut at the boundaries of the commit's version (before
        # the first commit, of any version: they must all give the same text)
        cuts = {cut_out(text, self.g.versions[h].decode('utf-8', 'replace'))
                for h in ([own] if own else [h for h in self.g.versions if name in self.g.names[h]])} - {None}
        if len(cuts) == 1:
            return self.g.add(cuts.pop().encode(), name), True
        return '', True

    def of(self, s, name, written):
        """(hash, how): how is 'transcript', 'git' or why the hash is blank."""
        e = s['prompts'].get(name)
        t = s['start'] or written
        if e and self.ours(e, s) and e[0] <= written + SLACK:
            h, exact = self.load(name, e)
            if h and exact:
                return h, 'transcript'
            if h == '':
                return '', 'it loaded a text no known version matches'
            if h:  # a cut copy agreeing with the commit's version: that version, if no edit is seen in use meanwhile
                t = e[0]
        h, c = self.g.prompt_at(name, t)
        if not h:
            return '', 'no version in git then'
        if self.uncommitted.get((name, c)):
            return '', 'an uncommitted edit was in use under that commit'
        return h, 'git'


def iter_rows(root):
    with open(Path(root) / 'catalog.jsonl', encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


class AddTimes:
    """When `catlog.py add` ran for a paper, from the chats' and agents' Bash calls that name it: narrows an add logged
    in one minute to the seconds its command ran (adds run by scripts or other tools leave the whole minute)."""

    def __init__(self, trans):
        self.calls = collections.defaultdict(list)  # pmid -> [(start, end)]
        for s in trans.values():
            for i, pmids in s.get('adds', []):
                c = s['calls'][i]
                for p in pmids:
                    self.calls[p].append((c[0], c[1] if c[1] is not None else (s['end'] or c[0])))

    def window(self, minute, pmid):
        lo, hi = minute, minute + 60
        over = [(a, b) for a, b in self.calls.get(pmid, ()) if a < hi and b + SLACK >= lo]
        if over:
            lo, hi = max(lo, min(a for a, _ in over) - SLACK), min(hi, max(b for _, b in over) + SLACK)
        return lo, hi


def backfill(root, trans, texts, g, report, dates=None):
    """The TSV lines: one per unstamped catalog row with evidence. `report` counts what was found and why rows got no
    line or a blank field; `dates` (optional) the add dates behind each count."""
    root = Path(root)
    ev, versions, files, writers = log_events(root), work_versions(root), Files(), Writers(trans)
    prompts, times = Prompts(trans, texts, g, root), AddTimes(trans)
    dates = dates if dates is not None else collections.defaultdict(collections.Counter)
    rejected = None
    out = []

    def note(key, when):
        report[key] += 1
        dates[key][str(when)[:10]] += 1

    def originals(pmid):
        nonlocal rejected
        if rejected is None:
            rejected = collections.defaultdict(list)
            with open(root / 'rejected.jsonl', encoding='utf-8') as fh:
                for line in fh:
                    if line.strip():
                        r = json.loads(line)
                        rejected[r.get('pmid')].append(r)
        return rejected.get(pmid, [])

    def add_of(row):
        """(minute, event, kept, logged) of the add whose agents read this row, or (None, why)."""
        t = minute_of(row.get('added') or row.get('checked'))
        e = [x for x in ev.get(row['pmid'], []) if t is not None and x[0] >= t]
        if not e:
            return None, 'no add line for it in log.tsv'
        first = [x for x in e if x[0] == e[0][0]]
        hit = next((x for x in first if x[1] == 'add' and x[2] > 0), None) or first[0]
        if hit[1] == 'add':
            return hit, ''
        # a recover: the row came back from rejected.jsonl; its agents are those of the add that first judged it
        was = [minute_of(r.get('checked')) for r in originals(row['pmid'])
               if r.get('row_id') == row['row_id'] or row_key(r) == row_key(row)]
        was = [x for x in was if x is not None and x < t]
        if not was:
            return None, 'recovered: its first judgement is not in rejected.jsonl'
        a = next((x for x in ev.get(row['pmid'], []) if x[1] == 'add' and x[0] >= max(was)), None)
        return (a, '') if a else (None, 'recovered: no add line for its first judgement')

    for row in iter_rows(root):
        if any(f in row for f in STAMP):
            continue
        when = row.get('added') or row.get('checked')
        report['rows without stamps'] += 1
        a, why = add_of(row)
        if a is None:
            note(f'no line: {why}', when)
            continue
        minute, pmid = a[0], row['pmid']

        def wrote(kind):
            """(writer, written time, by time) of the version of work/<pmid>.<kind>.json this add read: by its mtime when
            it is still on disk (in work/ or work/old/), else by the transcripts' times."""
            name, v = f'{pmid}.{kind}.json', at_add(versions.get((pmid, kind), []), minute)
            if v:
                return writers.find(name, v[1]), v[1], False
            w = writers.last_before(name, minute + 60)
            return w[:3], w[3], True

        main_r = at_add(versions.get((pmid, 'read'), []), minute)
        miss_r = at_add(versions.get((pmid, 'missed.read'), []), minute)
        if main_r is None:  # overwritten in place by a later read: no row check; the add's agents by their times
            rw, rt, _ = wrote('read')
            mw, mt, _ = wrote('missed.read')
            if rw[0] is None:
                note('no line: the read file of its add is gone and no transcript wrote it before', a[3])
                continue
            if mt is not None and mt > rt:  # this round's verifier also wrote missed values: which file held the row?
                note('no line: the read file of its add is gone and the row may be a missed value', a[3])
                continue
            missed = False
        else:
            in_main, in_miss = files.copies(main_r, row), files.copies(miss_r, row)
            missed = bool(in_miss) and not in_main
            if not in_main and not in_miss:  # no row of either file has its quote (one the verifier replaced): the
                fit = (files.has_cell(main_r, row), files.has_cell(miss_r, row))  # file that has its cell, if one does
                if fit[0] == fit[1]:
                    note('no line: the row is not in the read file of its add', a[3])
                    continue
                missed = fit[1]
                note('row found in its read file by its cell, not its quote (the verifier replaced the quote)', a[3])
            elif in_main and in_miss:  # same metric, number and quote in both files (an OCR table's block quote): the
                me = identity(reader_version(row))  # file whose copy measured what the row did, as its reader wrote it
                if (me in in_main) == (me in in_miss):
                    note('no line: a reader row and a missed value fit it alike', a[3])
                    continue
                missed = me in in_miss
        pair = ('missed.read', 'missed.verify') if missed else ('read', 'verify')
        (rw, rt, rby), (vw, vt, vby) = wrote(pair[0]), wrote(pair[1])
        if rw[0] is None and vw[0] is None:
            note(f'no line: no transcript ({rw[2]})', a[3])
            continue
        line = {'row_id': row['row_id'], 'read_by': MISSED if missed else 'reader', 'how': HOW}
        parts = [f'add {a[3]}']
        for who, (rel, i, why), written, by, pname, mf, pf in (
                ('reader', rw, rt, rby, 'verify.md' if missed else 'read.md', 'reader_model', 'read_prompt'),
                ('verifier', vw, vt, vby, 'verify.md', 'verifier_model', 'verify_prompt')):
            if rel is None:
                line[mf] = line[pf] = ''
                note(f'{who} blank: {why}', a[3])
                continue
            line[mf], runs = writers.model(rel, i), writers.runs(rel, i)
            if not line[mf]:
                note(f'{mf} blank: its transcript names no model', a[3])
            elif len(runs) > 1:  # a fallback mid-run: every model in order in the stamp, its calls in the evidence
                note(f'{mf} names several models: the agent switched model before it wrote the file', a[3])
            line[pf], how = prompts.of(trans[rel], pname, written)
            parts.append(f'{who} {Path(rel).name}' + (' (by time: file overwritten later)' if by else '')
                         + (' (prompt: git)' if how == 'git' else '')
                         + (' (tool calls: ' + ' > '.join(f'{m} {n}' for m, n in runs) + ')' if len(runs) > 1 else ''))
            note(f'{who} matched ' + ('by time (file overwritten later)' if by else 'by file mtime'), a[3])
            note(f'{pf} ' + ('from the transcript' if how == 'transcript' else 'from git' if how == 'git'
                             else f'blank: {how}'), a[3])
        lo, hi = times.window(minute, pmid)
        line['pipeline_commit'] = g.commit_at(lo, hi)[:12]
        if not line['pipeline_commit']:
            note('pipeline_commit blank: ' + ("the add ran before main's first commit" if g.head_at(lo) is None
                                              else 'main moved to new pipeline code while the add ran'), a[3])
        line['evidence'] = '; '.join(parts)
        out.append(line)
    return out


AGENT_FILE = re.compile(r'\bagent-[0-9a-f]+\.jsonl\b')


def keep_gone(lines, out, trans, report):
    """Once transcripts are gone (archived to Nova and removed, 2026-10-28, or Claude Code's 30-day cleanup), the
    earlier TSV is the record. An earlier line a gone transcript is named in stays exactly as it was, whether this run
    builds no line for its row, a poorer one (the other agent of the pair is still here) or a different one; its row
    need not be in the catalog now (a dropped value that comes back keeps its stamp). Other rows are rebuilt as before,
    except that a field the earlier line left blank stays blank (the evidence against a value may be among the gone
    transcripts). A changed rule therefore reaches those lines only from a full restored copy (RESTORE.md). Earlier
    lines that share a row_id are all left out, and counted."""
    if not Path(out).exists():
        return lines
    with open(out, encoding='utf-8', newline='') as fh:
        old = list(csv.DictReader(fh, delimiter='\t'))
    have = {Path(rel).name for rel in trans}
    ids = collections.Counter(l['row_id'] for l in old)
    earlier = {l['row_id']: {f: l.get(f, '') for f in FIELDS} for l in old if ids[l['row_id']] == 1}
    gone = {i for i, l in earlier.items() if any(n not in have for n in AGENT_FILE.findall(l['evidence']))}
    if not gone:
        return lines
    if len(earlier) < len(ids):
        report['earlier lines left out: their row_id is in the earlier TSV twice'] += sum(n for n in ids.values() if n > 1)
    built = {l['row_id']: l for l in lines}
    out_lines = []
    for i, l in built.items():
        if i in gone:
            continue
        e = earlier.get(i)
        if e and any(l.get(f) and not e[f] for f in FIELDS[2:7]):
            l = {**l, **{f: '' for f in FIELDS[2:7] if not e[f]}}
            report['earlier blanks kept (some transcripts are gone)'] += 1
        out_lines.append(l)
    for i in sorted(gone):
        if i not in built:
            report['earlier line kept, a transcript it names is gone: this run built none'] += 1
        elif built[i] != earlier[i]:
            report['earlier line kept, a transcript it names is gone: this run built another'] += 1
        out_lines.append(earlier[i])
    return out_lines


def save_prompts(lines, g, prompts_dir):
    """Each prompt hash the lines name gets its exact text once in prompts_dir/<hash>.md, as catlog.keep_prompt does in
    work/prompts/ for live stamps. Returns the hashes with no text (never expected)."""
    missing = set()
    for h in sorted({l[f] for l in lines for f in ('read_prompt', 'verify_prompt') if l.get(f)}):
        p = Path(prompts_dir) / f'{h}.md'
        b = g.versions.get(h)
        if p.exists() and h12(p.read_bytes()) == h:
            continue
        if b is None:
            missing.add(h)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    return missing


def write_tsv(lines, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f'.{out.name}.{os.getpid()}.tmp')
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, FIELDS, delimiter='\t', lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        w.writerows(sorted(lines, key=lambda l: l['row_id']))
    os.replace(tmp, out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', default=str(HERE), help='the data folder (only read)')
    ap.add_argument('--out', help='the TSV (default: <root>/sources/provenance_backfill.tsv)')
    ap.add_argument('--prompts', help='where prompt texts go (default: prompt_versions/ next to the TSV)')
    ap.add_argument('--cache', help='parsed-transcript cache (default: <root>/enrich/provenance_transcripts.json.gz)')
    ap.add_argument('--transcripts', help='Claude Code\'s projects folder (default: ~/.claude/projects)')
    ap.add_argument('--branch', default='main')
    ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    out = Path(a.out or root / 'sources' / 'provenance_backfill.tsv')
    prompts_dir = Path(a.prompts or out.parent / 'prompt_versions')
    cache = Path(a.cache or root / 'enrich' / 'provenance_transcripts.json.gz')
    t0 = time.time()
    g = Git(root, a.branch, saved=(prompts_dir, root / 'work' / 'prompts'))
    trans, texts = load_transcripts(a.transcripts or PROJECTS, cache, a.jobs, g, needle=str(root))
    report, dates = collections.Counter(), collections.defaultdict(collections.Counter)
    lines = keep_gone(backfill(root, trans, texts, g, report, dates), out, trans, report)
    missing = save_prompts(lines, g, prompts_dir)
    write_tsv(lines, out)
    filled = {f: sum(1 for l in lines if l.get(f)) for f in FIELDS[2:7]}
    print(f'{len(trans)} transcripts; {report.pop("rows without stamps", 0)} rows without stamps; {len(lines)} '
          f'backfilled ({sum(1 for l in lines if l["read_by"] == MISSED)} read by the verifier: missed values) -> {out}')
    print('  filled: ' + ', '.join(f'{f} {n}' for f, n in filled.items()))
    for k, n in sorted(report.items(), key=lambda x: (not x[0].startswith('no line'), -x[1])):
        d = sorted(dates[k])
        print(f'  {k}: {n}' + (f' (adds of {d[0]}' + (f' to {d[-1]})' if d[-1] != d[0] else ')') if d else ''))
    if missing:
        print(f'  {len(missing)} prompt hashes without a text: {sorted(missing)[:5]}')
    print(f'  ({time.time() - t0:.0f} s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
