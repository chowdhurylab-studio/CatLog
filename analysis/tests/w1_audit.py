#!/usr/bin/env python3
"""W1 transcript audit (RUN.md §5), run after every arm-run and after adjudication. For each agent of the run it reads
the Claude Code transcript and checks:
  - every assistant message is the model the session was started with (claude-opus-5-5, or claude-sonnet-5-5 for the
    logged retry); another model, a mid-run switch ('A>B') or a model-fallback line Claude Code wrote (system subtype
    model_refusal_fallback / model_fallback) breaks the rule; Claude Code's own '<synthetic>' messages are noted only;
  - the Claude Code version(s) of the run (one per round: compare the arms of a round);
  - no web tool, MCP tool or subagent call;
  - no evaluation word (common_w1.EVAL_WORDS, the one list) in what the agent was shown: its working directories (the
    transcript's cwd lines and the added folders of its environment), its prompt (the first user message), for A6 the
    request the workflow harness relayed, and the context Claude Code attached (review of the dry-run fixes: the
    session context, whose gitStatus showed the first dry run's A6 agents the kit's commits, the environment and the
    agent listing); one breaks the rule. Instruction files (CLAUDE.md, the memory index) break a plain session or an
    adjudicator (they see none); for A6 a word its setup baseline lacks breaks (MANIFEST instructions_baseline: the
    owner's and CatLog's CLAUDE.md, which hold a few production words), so does a file of a type the baseline lacks
    (A6 runs with memory off since 2026-11-01: main's memory index shown to it breaks), and a changed text is noted;
  - no git command that shows history or refs (git log, show, branch, ...) and no read of .git: breaks an agent, noted
    for A6's launch session. Since 2026-11-01 catlog-copy is a folder with its own repository that holds one orphan
    snapshot commit and no ref (until then a worktree of main, whose refs git log --all, git branch -a and git worktree
    list showed there), so such a command shows nothing of the kit; the rule stays, as a sign of an agent looking
    around;
  - every path a tool call names lies in the agent's allowlist (a token from a shell command, a Grep pattern or a glob
    counts as a path only when its first part is an entry of the filesystem root: '</ce:table>', 's/<[^>]*>/ /g' and
    'x/1000' name no file):
      plain read or A0     its own folder, the files its prompt names (output, validator), /tmp/<RUN>-<PMID>-*;
      A2 reconcile         the same plus its read files and their folders (it lists them; another paper's read breaks);
      adjudicator          its own folder, its claims file and its folder, its output file, /tmp/<RUN>-<PMID>-*;
      (all three)          a listing of its own output's name before it writes it (ls <its output folder>/<PMID>*)
                           is noted, not a break, when the call's recorded result shows no entry of that folder but
                           its own output (own_output_listing; the owner's rule of 2026-11-06, set before any scoring);
      A6 reader, verifier  the CatLog folder its task names (which must be catlog-copy/), the paper's original as the
                           run's papers.tsv names it (inside the CatLog folder since 2026-11-01) and that file's folder,
                           /tmp/p<PMID>*, /tmp/<role>-<PMID>*;
    the agent's own session folders (~/.claude/projects/<slug>/<session>/: the large tool outputs Claude Code saves
    for it to read back; /private/tmp/claude-<uid>/<slug>/<session>/: its scratchpad) and system folders (/usr, /bin,
    /opt, /dev, /System, /Library, /private/var/folders) are allowed for all; /tmp and /private/tmp themselves are allowed
    as a working directory (agents cd there to render page images); any other path under /Users, any other existing
    path under Claude Code's per-user root /private/tmp/claude-<uid>/ (another session's scratchpad or task output) and
    another eval session's /tmp scratch (the codes of the other arm-run parts and judges, and the first layout's A0-, A2-,
    A6-, W1adj- names; for plain agents and adjudicators also A6's read-/verify- folders, one level down too, and any
    other /tmp/claude-* folder) break the rule, any other /tmp path is noted; a '../' in a shell command is read where
    the command has cd'd to and, when that names an existing path, from the session's cwd too (cd_paths);
    A6 agents are also held to tools/human_review.py's forbidden files for a CatLog copy (FORBIDDEN_IN_COPY)
    and the gold, head-to-head and first-layout names (FORBIDDEN_A6);
  - no network code in a shell command or a script the agent writes (urlopen, requests, http.client, httpx, aiohttp,
    ftplib, sockets, curl, wget); a bare URL is noted;
  - a plain session that left a file in its input folder (claude_session.py moved it to logs/<run>/stray/) breaks;
  - A6: every transcript line's cwd is the CatLog folder (an agent working in another folder breaks), run papers without
    a reader and a verifier transcript are listed (none found at all: exit 1, the session was probably not opened in
    catlog-copy/), the launch session itself is audited too (its model and what it was shown), and agents of a paper
    read again after a model switch (run_a6.py --redo, records/runs/A6-<run>/redo/) are audited in their own window;
    such a paper is judged on its redo launches' agents, redo and redo-more-<k> alike, any other paper on main's and
    more-<k>'s (common_w1.a6_judged; the listing of papers without a reader or a verifier too); a reading agent's paper
    is found by common_w1.READ_TASK (human_review's pattern missed the copy's task for a paper with no PMID);
  - tokens (the four usage fields, once per message id, as rethink/r01_tokens.py), dollars at list price and minutes.
A paper-run with a broken rule is listed in records/audit/<run>/rerun.txt (RUN.md: it runs again once; a second break
takes the paper out of every arm). A paper a model switch already left out (model_switch.json) is listed apart.

  python3 tools/w1/w1_audit.py A0-r1                plain sessions of records/logs/A0-r1/
  python3 tools/w1/w1_audit.py A2-r1                A2's reads and reconcile (records/logs/A2-r1/)
  python3 tools/w1/w1_audit.py adjudication         the adjudicators (records/logs/adjudication/; adjudication_pilot too)
  python3 tools/w1/w1_audit.py A6-r1 [--projects DIR ...]   the A6 run's subagents, from the transcripts of sessions
                                                    opened in catlog-copy/ (default ~/.claude/projects/<its slug>*),
                                                    between records/runs/A6-r1/RESET.json's start and reset times
  options for a run kept elsewhere (the first dry run, records/dry_run_1/): --from DIR (the folder holding its logs/ and
  runs/), --a6-root PATH (the CatLog folder that run used), --out DIR (where audit.json, tokens.json, rerun.txt go)
Writes records/audit/<run>/audit.json, tokens.json, rerun.txt."""
import argparse, collections, datetime, glob, json, os, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common_w1 as W  # noqa: E402
import human_review as HR  # noqa: E402  (the branch's copy: FORBIDDEN_IN_COPY; a reading agent's paper: common_w1.READ_TASK)

PRICE = {'claude-opus-5-5': (4.0, 20.0, 0.2), 'claude-opus-5': (5.0, 25.0, 0.5), 'claude-sonnet-5-5': (2.0, 10.0, 0.2)}
SYSTEM = ('/usr/', '/bin/', '/sbin/', '/opt/', '/dev/', '/System/', '/Library/', '/private/var/folders/', '/var/folders/',
          '/private/etc/', '/etc/')
BAD_TOOLS = re.compile(r'^(WebFetch|WebSearch|mcp__.*|Agent|Task)$')
PATH_RX = re.compile(r'(?<![\w.~/:-])(~?/[^\s\'"`;|&<>(){}$*?\[\]]+)')
GIT_PEEK = re.compile(r'(?:^|[\s;&|(])git\s+(?:(?:-C\s+\S+|-c\s+\S+|--[\w-]+(?:=\S+)?)\s+)*'
                      r'(log|show|reflog|shortlog|branch|describe|rev-list|for-each-ref|worktree|cat-file|tag|blame|'
                      r'whatchanged|ls-remote|name-rev|notes)\b|(?:^|[\s;&|(/\'"])\.git(?:/|(?![\w.-]))')
UP_RX = re.compile(r'(?<![\w/.-])((?:\.\./)+[^\s\'"`;|&<>(){}$*?\[\]]*)')
# Pilot fix (2026-11-02): a command that only leaves .git out ("find . -newer x -not -path './.git/*'", grep
# --exclude-dir=.git, rg -g '!.git') does not look at the repository; the exclusion is removed before GIT_PEEK.
GIT_EXCLUDE = re.compile(r'(?:-not|!)\s+-(?:i?path|i?name|wholename)\s+([\'"]?)[^\s\'"]*\.git[^\s\'"]*\1'
                         r'|-(?:i?path|i?name)\s+([\'"]?)[^\s\'"]*\.git[^\s\'"]*\2\s+-prune'
                         r'|--exclude-dir(?:=|\s+)([\'"]?)\.git\3(?![\w.-])'
                         r'|(?:-g|--glob)(?:=|\s+)([\'"]?)!\.git[^\s\'"]*\4')


def git_peek(cmd):
    return GIT_PEEK.search(GIT_EXCLUDE.sub(' ', cmd))
PROMPT_PATH_RX = re.compile(r'(?<![\w.~/-])(/[^\s\'"`<>|;,(){}]+)')
TMP_CWD = ('/tmp', '/private/tmp')
# Entries of the filesystem root: a token from a command is a path only when its first part is one of them (dry-run fix,
# 2026-11-01: XML tags such as </ce:table> and </table-wrap>, sed's /g and a division /1000 had counted as paths).
ROOT_ENTRIES = {'Users', 'private', 'tmp', 'var', 'etc', 'usr', 'bin', 'sbin', 'opt', 'dev', 'System', 'Library',
                'Applications', 'Volumes', 'cores', 'home', 'Network', 'nix'}
try:
    ROOT_ENTRIES |= set(os.listdir('/'))
except OSError:
    pass


def eval_scratch_rx():
    """Other eval sessions' /tmp scratch: the codes of every plain part and judge (the neutral layout), and the first
    layout's names (A0-, A2-, A6-, W1adj-)."""
    codes = sorted({c for c in W.scratch_labels() if c not in ('read', 'verify')})
    return re.compile(r'^/private/tmp/(?:A0|A2|A6|W1adj|' + '|'.join(codes) + ')-')


EVAL_SCRATCH = eval_scratch_rx()                                             # plain and adjudicator sessions' scratch
# A6 agents' role folders in /tmp, also one level down (a folder an agent made with mktemp), and a /tmp/claude-* folder
# that is not Claude Code's per-user root (an A6 verifier's own mktemp -d /tmp/claude-verify-XXXXXX, locked set 11 Nov):
# strict for plain sessions and adjudicators; A6 agents pass strict=(EVAL_SCRATCH,), so for them these are noted
A6_SCRATCH = re.compile(r'^/private/tmp/(?:(?:[^/]+/)?(?:read|verify|verify-missed)-|claude-(?!\d+(?:/|$)))')
NET_BREAK = re.compile(r'urlopen|urllib\.request|urllib3|\bimport\s+requests\b|\brequests\.(?:get|post|head|put|Session)\b|'
                       r'http\.client|\bhttpx\b|\baiohttp\b|\bftplib\b|\bsocket\.(?:socket|create_connection)\b|'
                       r'(?:^|[\s;|&(])(?:curl|wget)\s', re.I)
NET_NOTE = re.compile(r'\b(?:https?|ftp)://', re.I)
SCRIPT_EXT = ('.py', '.sh', '.js', '.rb', '.pl', '.r', '.R')
RELAY = '[Workflow harness — user request]'   # the user request a workflow harness relays (not its computed task)
TASK_ROOT = re.compile(r'The CatLog folder is (/[^\s:]+):')
EXISTS = os.path.exists  # judge_path's existence test (tests replace it)
EVAL_WORDS = W.EVAL_TEXT_RX  # the text half of the one list (common_w1.EVAL_WORDS); eval_word_hits() applies both
# What an A6 agent never opens, on top of tools/human_review.py's FORBIDDEN_IN_COPY (the main folder's reads, the folders
# next to catlog-copy/): the gold sets and the head-to-head by name, and the first layout's eval parts. Kept here, in the
# kit, so that no file in catlog-copy/ names them.
FORBIDDEN_A6 = re.compile(HR.FORBIDDEN_IN_COPY.pattern + '|' +
                          r'top_journal_20261021|/benchmarks/|h2h_20261101|w1_kill_test|Golden_Benchmark|'
                          r'manual_curated_runeem|enzyextract_si|'
                          r'catlog-eval/[^\s"\'`]*?/(?:keys|score\w*|runs|logs|orders|adj|repo|audit)/')


def norm(p, cwd=None):
    p = os.path.expanduser(p)
    if not p.startswith('/') and cwd:
        p = os.path.join(cwd, p)
    p = os.path.normpath(p)
    if p == '/tmp' or p.startswith('/tmp/') or p.startswith('/var/'):
        p = '/private' + p
    return p


def real_path(tok):
    """A token taken from a command, a pattern or a glob names a file only when it starts at a root entry (or ~)."""
    if tok.startswith('~'):
        return True
    parts = tok.split('/')
    return len(parts) > 1 and parts[1] in ROOT_ENTRIES


HOME_RX = re.compile(r'\$\{HOME\}|\$HOME(?![A-Za-z0-9_])')
CD_RX = re.compile(r'(?:^|[;&|(]|\n)\s*cd(?=\s|$)(?!\s*=)(?:\s+-[A-Za-z]+|\s+--(?=\s|$))*'
                   r'(?:\s+(?:"([^"]*)"|\'([^\']*)\'|([^\s;&|)]+)))?')
SEG_RX = re.compile(r'&&|\|\||[;|\n]')
REL_RX = re.compile(r'(?<![\w./~:$@-])([A-Za-z0-9_][\w.+-]*/[^\s\'"`;|&<>(){}$*?\[\]]*)')


def expand_home(t):
    """$HOME and ${HOME} as the home folder (review of the dry-run fixes: 'cat $HOME/Documents/catlog-v2/...' named no
    real path once a path had to start at a root entry)."""
    return HOME_RX.sub(str(Path.home()), t)


def up_paths(text, here, cwd):
    """The '../' tokens of a shell command's segment: read from where the command has cd'd to by then (here), and also
    from the session's cwd whenever that reading names an existing path, since a cd the audit sees may never have been
    made (a failed or conditional cd, one in a subshell, a pipeline, a heredoc or a comment, a script run later from the
    cwd). Locked set, 11 Nov: 'cd catlog-copy/tools && grep ... ../catlog.py' had been read only from the cwd, naming a
    file above catlog-copy/ that does not exist; the review of that fix found the cwd reading must stay."""
    out = []
    for tok in UP_RX.findall(text):
        q, c = norm(tok, here), norm(tok, cwd)
        out.append(q)
        if c != q and EXISTS(c):
            out.append(c)
    return out


def cd_paths(cmd, cwd):
    """A shell command that changes folder: the folders it cds into, and the relative tokens after such a cd that name an
    existing file or folder there ('cd .../papers && head 23934069/paper.txt'); a token that names nothing (a sed
    expression, 'x/1000') is not a path. A '../' token is read from the folder the command is in at that point (locked
    set, 11 Nov: 'cd catlog-copy/tools && grep ... ../catlog.py' had been read against the session's cwd, naming a file
    above catlog-copy/ that does not exist)."""
    out, here, prev = [], cwd, cwd
    for seg in SEG_RX.split(cmd):
        m = CD_RX.match(seg)
        if m and seg.strip().startswith('cd'):
            t = next((g for g in m.groups() if g is not None), None)
            if t == '-':  # back to the folder before the last cd
                here, prev = prev, here
            else:
                here, prev = (norm(t, here) if t else str(Path.home())), here
            out.append(here)
            out += up_paths(seg, prev, cwd)  # the cd segment's own '../' tokens (its target, an option, a '&' job)
            continue
        out += up_paths(seg, here, cwd)
        if here and here != cwd:
            for tok in REL_RX.findall(seg):
                q = norm(tok, here)
                if EXISTS(q):
                    out.append(q)
    return out


def named_paths(tool, inp, cwd):
    """Absolute paths a tool call names (file arguments, and real paths written in a shell command, a pattern, a glob
    or a script the agent writes; $HOME expanded, '//x' read as '/x', relative names after a cd resolved there)."""
    out = []
    if not isinstance(inp, dict):
        return out
    for k in ('file_path', 'notebook_path', 'path'):
        if isinstance(inp.get(k), str) and inp[k]:
            out.append(norm(inp[k], cwd))
    texts = [(inp.get(k), k == 'command') for k in ('command', 'pattern', 'glob') if isinstance(inp.get(k), str)]
    if str(inp.get('file_path', '')).endswith(SCRIPT_EXT):  # a script it writes runs later: its paths count too
        texts += [(inp.get(k), False) for k in ('content', 'new_string') if isinstance(inp.get(k), str)]
    for t, command in texts:
        t = expand_home(t)
        for m in PATH_RX.findall(t):
            m = re.sub(r'^/{2,}', '/', m)
            if real_path(m):
                out.append(norm(m, cwd))
        if not command:  # a shell command's '../' tokens are read where it has cd'd to by then (cd_paths)
            for m in UP_RX.findall(t):
                out.append(norm(m, cwd))
    if isinstance(inp.get('command'), str):
        out += cd_paths(expand_home(inp['command']), cwd)
    return list(dict.fromkeys(out))


def allowed(p, allow):
    """An allow entry ending in '*' is a prefix, one ending in '/' a folder, anything else one exact path."""
    for a in allow:
        if a.endswith('*'):
            if p.startswith(a[:-1]):
                return True
        elif a.endswith('/'):
            if p == a[:-1] or p.startswith(a):
                return True
        elif p == a:
            return True
    return False


# Claude Code's per-user tmp roots (/private/tmp/claude-<uid>/: every session's scratchpad and task output). Locked set,
# 11 Nov: a folder an agent made itself with mktemp -d /tmp/claude-verify-XXXXXX had been taken for another session's.
CC_TMP = re.compile(r'^/private/tmp/claude-\d+(?:/|$)')


def judge_path(p, allow, notes=(), strict=(EVAL_SCRATCH, A6_SCRATCH)):
    """'ok', 'note' or 'break' for one named path. strict: /tmp scratch names of other eval sessions (break)."""
    if p.startswith(str(W.PROJECTS) + '/') and (p.endswith('.jsonl') or '/subagents/' in p):
        return 'break'  # a session transcript (another agent's read of a paper), even inside the agent's own session
    if allowed(p, allow):
        return 'ok'
    if CC_TMP.match(p):
        # a parent or a cut-off of its own scratchpad path (production readers list and mistype them), or a path that
        # does not exist (nothing to read), is noted; another session's existing scratchpad or task output breaks
        own = [a for a in allow if CC_TMP.match(a)]
        return 'note' if any(o.startswith(p) for o in own) or not EXISTS(p) else 'break'
    if any(rx.match(p) for rx in strict):
        return 'break'  # another eval session's scratch (moved away after its session, so existence cannot decide)
    if p == '/' or any(p.startswith(s) or p + '/' == s for s in SYSTEM):
        return 'ok'
    if p in notes or p == '/private/tmp' or p.startswith('/private/tmp/'):
        return 'note'
    return 'break'



LIST_RX = re.compile(r'(?:^|[\s;&|(`])(?:ls|find|tree|du|stat|fd|rg|grep\s+-\w*r\w*)\b|os\.(?:listdir|walk|scandir)|'
                     r'glob\.i?glob|\.(?:iterdir|rglob|glob)\(|readdir|opendir')
FRAG_RX = re.compile(r'(["\'])([^"\'\n]{1,300}?)\1')
FRAG_FILE_RX = re.compile(r'^[\w.+-]+\.(?:json|txt|pdf|xml|py|tsv|csv|md|png)$')


def prefix_note(p, text, allow, notes, strict, root):
    """Pilot fix (2026-11-02): a script often names a parent folder only as a prefix it joins file names to
    (d = '<root>/out/'; open(d + 'm7cd3m/19122206.json')). Such a folder, at or below the eval root and above a path the
    session may use, is noted instead of breaking when the text lists nothing (no ls, find, grep -r, os.listdir, glob,
    ...), no glob follows the folder, and every quoted fragment joined to it that names an existing path is one the
    session may use. Anything else stays a break: a listing, a glob, a fragment into another paper or another arm."""
    if not root or not (p == root or p.startswith(root.rstrip('/') + '/')):
        return False
    if not any(a.startswith(p.rstrip('/') + '/') for a in allow):
        return False  # not a parent of anything the session may use
    if LIST_RX.search(text):
        return False
    for m in re.finditer(re.escape(p.rstrip('/')), text):
        nxt = text[m.end():m.end() + 2]
        if nxt[:1] in '*?[' or (nxt[:1] == '/' and nxt[1:2] in '*?['):
            return False
    for _, frag in FRAG_RX.findall(text):
        f = frag.strip()
        if f.startswith('/') and real_path(f):
            continue  # an absolute path: judged on its own
        if '/' not in f and not FRAG_FILE_RX.match(f):
            continue
        q = norm(os.path.join(p, f.lstrip('/')))
        if q != p and EXISTS(q) and judge_path(q, allow, notes, strict) == 'break':
            return False
    return True

VERDICT_NAME_RX = re.compile(r'(?<![\w.])(\d+\.c\d+\.json)\b')  # a chunk file's bare name, as ls prints it
# Anything in the command that could run other code, change what ls runs or reuse its words: a backslash-newline,
# zsh's $_ and $~, history (!$, !!), process or command substitution, a function, an assignment or a shell builtin
# in command position (PATH=, alias, hash, eval, exec, source, ., export, setopt, ...), xargs.
SHELL_HAZARD_RX = re.compile(
    r'\\\n|\$_|\$~|!\$|!!|[<>]\(|`|\$\(|\bxargs\b|'
    r'(?:^|[;&|\n({]\s*)(?:function|alias|unalias|hash|unhash|eval|exec|source|builtin|enable|disable|setopt|unsetopt|'
    r'zmodload|export|typeset|declare|local|readonly|functions|unfunction|rehash|command|\.)(?=\s)|'
    r'(?:^|[;&|\n({]\s*)[\w-]+\s*\(\s*\)|(?:^|[;&|\n({]\s*)\w+=')
SHELL_DENIED = 'Permission to use Bash has been denied'


def own_output_listing(p, call, out, pmid):
    """The owner's rule of 2026-11-06 (set before any scoring), made strict the same day after an adversarial check: a
    session that lists its own output's name before writing it (ls <its output folder>/<PMID>*) names a path its
    allowlist lacks, yet was shown nothing. Noted instead of breaking only when all of these hold, else a break:
      - a Bash call in the foreground (no run_in_background);
      - p is <the session's own output folder>/<name>, name running from the full PMID to at most the output file's
        own name, and the command holds a simple command that is exactly `ls [-l -a -d -1 -h ...] p*` with at most a
        2>&1 or 2>/dev/null, not followed by a pipe (quotes, glob qualifiers, more operands: no match);
      - nothing in the command can run other code, change what ls runs or reuse its words (SHELL_HAZARD_RX), and the
        rest of the command names no output folder at all (no '/out', 'out/' or the folder's name: no second spelling);
      - the recorded result shows that nothing was listed: zsh's 'no matches found: p*' (the glob matched nothing, so ls
        never ran), or Claude Code's 'Permission to use Bash has been denied' (the call never ran); a saved large output
        or any entry of the folder in the result stays a break."""
    if not out or not pmid or not isinstance(call, dict) or call.get('name') != 'Bash':
        return False
    inp = call.get('input') if isinstance(call.get('input'), dict) else {}
    cmd, res = inp.get('command'), call.get('result')
    if not isinstance(cmd, str) or not isinstance(res, str) or inp.get('run_in_background'):
        return False
    out = norm(out)
    folder, base, name = os.path.dirname(out), os.path.basename(out), os.path.basename(p)
    if p != folder + '/' + name or not name.startswith(str(pmid)) or not base.startswith(name):
        return False
    cmd = expand_home(cmd)
    if SHELL_HAZARD_RX.search(cmd):
        return False
    one_ls = re.compile(r'\s*ls(?:\s+-[lad1h]+)*\s+' + re.escape(p) + r'\*(?:\s+2>(?:\x00|/dev/null))?\s*')
    parts = re.split(r'(\|\||&&|[;&|\n])', cmd.replace('2>&1', '2>\x00'))
    hit, rest = False, []
    for i in range(0, len(parts), 2):
        seg, nxt = parts[i], (parts[i + 1] if i + 1 < len(parts) else '')
        if one_ls.fullmatch(seg) and nxt in ('', ';', '\n', '&&', '||'):
            hit = True
        else:
            rest.append(seg)
    rest = ' '.join(rest)
    if not hit or '/out' in rest or 'out/' in rest or os.path.basename(folder) in rest:
        return False
    if 'Output too large' in res or 'persisted-output' in res:
        return False
    if not (res.lstrip().startswith(SHELL_DENIED) or f'no matches found: {p}*' in res):
        return False
    for m in re.finditer(re.escape(folder) + r'/([^\s\'"`:;,()]*)', res):
        entry = m.group(1)
        if entry and not set(entry) & set('*?[') and entry != base:
            return False  # an entry of the folder other than its own output (a pattern echoed back is no entry)
    return all(x == base for x in VERDICT_NAME_RX.findall(res))


def own_session_dirs(tr):
    """The agent's own session folders, from its transcript's place: ~/.claude/projects/<slug>/<session>/ (tool results
    Claude Code saved for it to read back) and /private/tmp/claude-<uid>/<slug>/<session>/ (its scratchpad, tasks)."""
    try:
        rel = Path(tr).relative_to(W.PROJECTS)
    except ValueError:
        return []
    if len(rel.parts) < 2:
        return []
    slug, sid = rel.parts[0], rel.parts[1][:-len('.jsonl')] if len(rel.parts) == 2 else rel.parts[1]
    return [f'{W.PROJECTS}/{slug}/{sid}/', f'{W.CLAUDE_TMP}/{slug}/{sid}/']


def network(c):
    """'break' for network code in a shell command or in a script the agent writes, 'note' for a bare URL, else ''."""
    inp = c.get('input') if isinstance(c.get('input'), dict) else {}
    texts = [inp['command']] if isinstance(inp.get('command'), str) else []
    if str(inp.get('file_path', '')).endswith(SCRIPT_EXT) and isinstance(inp.get('content'), str):
        texts.append(inp['content'])
    if any(NET_BREAK.search(t) for t in texts):
        return 'break'
    return 'note' if any(NET_NOTE.search(t) for t in texts) else ''


def relayed(task):
    """The user request the workflow harness relayed to an agent (the indented lines after '[Workflow harness — user
    request]'), or ''. The harness's computed task ('[Workflow harness — computed task]') is the agent's prompt, not a
    relayed request."""
    i = task.find(RELAY)
    if i < 0:
        return ''
    out = []
    for line in task[i:].split('\n')[1:]:
        if line.startswith('  '):
            out.append(line[2:])
        elif out:
            break
    return '\n'.join(out).strip()


CONTEXT_KINDS = ('session_context', 'environment', 'agent_listing_delta')  # context the kit and its folders decide


def parse(tr, cwds=None, shown=None, context=None):
    """(messages by id with usage and model, tool calls, versions, models, first and last timestamps, the first user
    message); the cwd of every line goes into `cwds`, and the added working directories of its environment into `shown`
    (sets, when given); `context` (a list, when given) gets (kind, text) for the context attachments the session was
    shown (CONTEXT_KINDS: the session context with its gitStatus, the environment, the agent listing) and
    ('instructions', (type, path, content)) for every instruction file (CLAUDE.md, the memory index)."""
    seen, calls, versions, models, t0, t1, task = {}, [], set(), [], None, None, None
    results = {}
    with open(tr, errors='replace') as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if cwds is not None and d.get('cwd'):
                cwds.add(d['cwd'])
            if d.get('version'):
                versions.add(d['version'])
            ts = d.get('timestamp')
            if ts:
                t0 = t0 or ts
                t1 = ts
            if shown is not None and d.get('type') == 'attachment':
                snap = ((d.get('attachment') or {}).get('snapshot') or {})
                shown.update(str(x) for x in snap.get('additionalWorkingDirectories') or [])
            if context is not None and d.get('type') == 'attachment':
                a = d.get('attachment') or {}
                if a.get('type') in CONTEXT_KINDS:
                    context.append((a['type'], json.dumps({k: v for k, v in a.items() if k != 'type'})))
                elif a.get('type') == 'instructions':
                    for f in a.get('files') or []:
                        if isinstance(f, dict):
                            context.append(('instructions', (str(f.get('type')), str(f.get('path')), str(f.get('content') or ''))))
            m = d.get('message') or {}
            if d.get('type') == 'user' and task is None and not d.get('isMeta'):
                c = m.get('content')
                task = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c or [] if isinstance(x, dict))
            if d.get('type') == 'assistant':
                if m.get('model'):
                    models.append(m['model'])
                if m.get('id') and m.get('usage'):
                    seen[m['id']] = (m.get('model'), m['usage'])
                for c in m.get('content') or []:
                    if isinstance(c, dict) and c.get('type') == 'tool_use':
                        calls.append({'name': c.get('name'), 'input': c.get('input'), 'raw': json.dumps(c),
                                      'id': c.get('id')})
            if d.get('type') == 'user' and isinstance(m.get('content'), list):
                for c in m['content']:
                    if isinstance(c, dict) and c.get('type') == 'tool_result' and c.get('tool_use_id'):
                        results[c['tool_use_id']] = result_text(c.get('content'))
    for c in calls:
        if c.get('id') and c['id'] in results:
            c['result'] = results[c['id']]  # what the call showed the agent (own_output_listing reads it)
    return seen, calls, versions, models, t0, t1, task or ''


def result_text(content):
    """A tool result's text: a string, or the text blocks of a list (images left out)."""
    if isinstance(content, str):
        return content
    return '\n'.join(str(x.get('text', '')) for x in content or [] if isinstance(x, dict) and x.get('type') == 'text')


def minutes(t0, t1):
    try:
        a = datetime.datetime.fromisoformat(t0.replace('Z', '+00:00'))
        b = datetime.datetime.fromisoformat(t1.replace('Z', '+00:00'))
        return round((b - a).total_seconds() / 60, 2)
    except (AttributeError, ValueError, TypeError):
        return None


def tokens(seen):
    tot = collections.Counter()
    usd = 0.0
    for model, u in seen.values():
        f = {k: int(u.get(k) or 0) for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens',
                                             'output_tokens')}
        tot.update(f)
        p = PRICE.get(model)
        if p:
            usd += (f['input_tokens'] * p[0] + f['cache_creation_input_tokens'] * p[0] * 1.25 +
                    f['cache_read_input_tokens'] * p[2] + f['output_tokens'] * p[1]) / 1e6
    return {**tot, 'total': sum(tot.values()), 'usd': round(usd, 4)}


def eval_word_findings(cwds, shown_dirs, task, relay=''):
    """('break', 'eval_word', '<where>: <words>') for every shown text with an evaluation word (common_w1.EVAL_WORDS)."""
    out = []
    for where, text in ([('cwd', x) for x in sorted(cwds)] + [('add-dir', x) for x in sorted(shown_dirs)] +
                        [('prompt', task), ('relayed request', relay)]):
        hits = W.eval_word_hits(text)
        if hits:
            out.append(('break', 'eval_word', f"{where}: {','.join(hits)}"))
    return out


def context_findings(context, baseline=None):
    """Evaluation words in the context a session was shown (review of the dry-run fixes): any in the session context
    (gitStatus: the first dry run's A6 agents were shown the kit's commits), the environment or the agent listing breaks;
    an instruction file breaks with a word its setup baseline (MANIFEST instructions_baseline: production's own words)
    does not have, and is noted when its text differs from the baseline. An instruction file of a type the baseline does
    not hold breaks: A6's baseline is the owner's CLAUDE.md and CatLog's (User, Project), and A6 runs with memory off
    since 2026-11-01, so main's memory index (AutoMem) shown to it breaks. baseline None: no instruction file may be
    shown at all (plain and adjudicator sessions run with CLAUDE_CODE_DISABLE_CLAUDE_MDS and no memory)."""
    out = []
    for kind, text in context:
        if kind == 'instructions':
            typ, path, content = text
            if baseline is None or typ not in baseline:
                out.append(('break', 'instructions', f'{typ} {path}'))
                continue
            base = baseline.get(typ) or {}
            new = sorted(set(W.eval_word_hits(content)) - set(base.get('eval_words') or []))
            if new:
                out.append(('break', 'eval_word', f"instructions {typ} {path}: {','.join(new)}"))
            if base.get('sha256') and W.text_sha(content) != base['sha256']:
                out.append(('note', 'instructions_changed', f'{typ} {path}'))
            continue
        hits = W.eval_word_hits(text)
        if hits:
            out.append(('break', 'eval_word', f"context {kind}: {','.join(hits)}"))
    return out


def instruction_baseline(ev, base=None):
    """The setup's baseline of A6's instruction files (MANIFEST.json), else the files as they are now. A run kept
    elsewhere without its own manifest (the first dry run, records/dry_run_1/) is judged on the current baseline, which
    has no memory index since 2026-11-01: its A6 rows break for the AutoMem file they were shown then."""
    for m in ([Path(base) / 'MANIFEST.json'] if base else []) + [W.eval_paths(ev)['manifest']]:
        try:
            b = json.loads(Path(m).read_text()).get('instructions_baseline')
            if b:
                return b
        except (OSError, json.JSONDecodeError):
            continue
    return W.instruction_baseline(ev)


def audit_agent(tr, allowed_models, allow, cwd, forbidden=None, notes=(), strict=(EVAL_SCRATCH, A6_SCRATCH),
                want_cwd=None, relay='', baseline=None, git_level='break', prefix_root=None, own_out=None, pmid=None):
    """want_cwd: the folder the agent works in (A6: catlog-copy/; a plain session: its own folder). A transcript cwd
    outside it breaks unless it is /tmp itself (noted no more: agents cd there to render page images) or a place the
    agent may use anyway (its scratchpad or scratch folder: production readers cd there); another /tmp folder is noted;
    a session opened in another folder (main's) therefore breaks every agent. Relative paths are read against cwd."""
    cwds, shown, context = set(), set(), []
    seen, calls, versions, models, t0, t1, task = parse(tr, cwds, shown, context)
    found = eval_word_findings(cwds, shown, task, relay) + context_findings(context, baseline)
    allow = list(allow) + own_session_dirs(tr)
    if want_cwd is not None:
        w = str(want_cwd)
        for x in sorted(cwds):
            if x == w or x.startswith(w + '/') or norm(x) in TMP_CWD:
                continue
            v = judge_path(norm(x), allow, notes, strict)
            if v != 'ok':
                found.append((v, 'cwd', x))
        cwd = w
    elif len(cwds) == 1:
        cwd = next(iter(cwds))
    real = [m for m in models if m != '<synthetic>']
    other = sorted(set(real) - set(allowed_models))
    switch = ''
    if real and len(set(real)) > 1:
        order = [real[0]] + [m for i, m in enumerate(real[1:]) if m != real[i]]
        switch = '>'.join(order)
    if other:
        found.append(('break', 'model', ','.join(other)))
    if switch and not other and len(set(real)) > 1:
        found.append(('break', 'model_switch', switch))
    info = W.transcript_models(tr)
    for e in info['events']:
        found.append(('break', 'model_fallback', f"{e.get('subtype')}: {e.get('from')}>{e.get('to')} "
                                                 f"(scope {e.get('scope')}, category {e.get('category')})"))
    if info['refusals']:
        found.append(('note', 'refusal', str(info['refusals'])))
    if '<synthetic>' in models:
        found.append(('note', 'synthetic_message', str(models.count('<synthetic>'))))
    for c in calls:
        if BAD_TOOLS.match(str(c['name'])):
            found.append(('break', 'tool', c['name']))
        inp = c.get('input') if isinstance(c.get('input'), dict) else {}
        texts = [inp.get('command')] if c['name'] == 'Bash' else []
        if c['name'] in ('Write', 'Edit') and str(inp.get('file_path', '')).endswith(SCRIPT_EXT):
            texts += [inp.get('content'), inp.get('new_string')]
        text = expand_home('\n'.join(t for t in texts if isinstance(t, str)))
        for p in named_paths(c['name'], c['input'], cwd):
            v = judge_path(p, allow, notes, strict)
            if v == 'break' and text and prefix_note(p, text, allow, notes, strict, prefix_root):
                found.append(('note', 'path_prefix', p))
            elif v == 'break' and own_output_listing(p, c, own_out, pmid):
                found.append(('note', 'own_output_listing', p))
            elif v != 'ok':
                found.append((v, 'path', p))
        cmd = (c.get('input') or {}).get('command') if isinstance(c.get('input'), dict) else None
        if isinstance(cmd, str) and git_level and git_peek(cmd):
            found.append((git_level, 'git_history', cmd[:160]))  # the shared repository's commits, branches, worktrees
        net = network(c)
        if net:
            found.append((net, 'network', str((c.get('input') or {}).get('command') or
                                              (c.get('input') or {}).get('file_path') or '')[:160]))
        if forbidden is not None:
            for f in set(forbidden.findall(HR._named(c))):
                found.append(('break', 'forbidden', f))
    return {'transcript': str(tr), 'models': sorted(set(models)), 'model_sequence': switch or (real[0] if real else ''),
            'model_events': info['events'], 'versions': sorted(versions), 'cwds': sorted(cwds),
            'shown_dirs': sorted(shown), 'tool_calls': len(calls),
            'tools': dict(collections.Counter(str(c['name']) for c in calls)), 'minutes': minutes(t0, t1), 'start': t0,
            'end': t1, 'violations': sorted(set(found)), 'broken': any(v[0] == 'break' for v in found), **tokens(seen)}, task


def plain_records(log_dir):
    """(file, record, earlier) for every session of the run: log_dir/<label>.a<k>[b].json, and the records of a step's
    earlier invocations that claude_session.keep_earlier kept in log_dir/earlier/<step>/<k>/ (earlier = '<step>/<k>',
    else '')."""
    log_dir = Path(log_dir)
    for f in sorted(log_dir.glob('*.a[0-9]*.json')) + sorted(log_dir.glob('earlier/*/*/*.a[0-9]*.json')):
        if not re.search(r'\.a\d+b?\.json$', f.name):
            continue  # an attempt's output kept aside (<label>.a1.<PMID>.json), not a record
        try:
            rec = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(rec, dict) or rec.get('dry_run') or not rec.get('session_id'):
            continue
        yield f, rec, ('' if f.parent == log_dir else f'{f.parent.parent.name}/{f.parent.name}')


def prompt_paths(prompt):
    """Absolute paths a session's prompt names, normalised (its folder, the source, the output, the validator, the read
    lists or the claims file, the page-image prefix)."""
    return sorted({norm(m.rstrip('.,;:')) for m in PROMPT_PATH_RX.findall(prompt or '')})


def plain_allow(rec, prompt, pmid):
    """(allow, notes) of a plain session or an adjudicator: what its own record and prompt name, and nothing else."""
    cwd = rec['cwd'].rstrip('/')
    named = prompt_paths(prompt)
    files = [x for x in named if x.endswith(('.json', '.py'))]
    allow = [cwd + '/', norm(rec['out'])] + files
    out = norm(rec['out'])
    allow += [str(Path(x).parent) for x in files if x.endswith('.json') and x != out]  # its read lists' or claims' folder
    m = re.search(r'/tmp/(\S+?)-' + re.escape(pmid) + r'-p\b', prompt or '')
    if m:
        allow.append(norm(f'/tmp/{m.group(1)}-{pmid}-') + '*')
    return allow, (str(Path(out).parent), str(Path(cwd).parent))


def audit_plain(ev, run, base=None):
    """base: the folder holding logs/<run>/ (default the live records; --from for a run kept elsewhere)."""
    log_dir = Path(base or W.eval_paths(ev)['records']) / 'logs' / run
    switches = W.read_switches(log_dir)
    out = []
    for f, rec, earlier in plain_records(log_dir):
        label = rec['label']  # <PMID>[.<part>].a<k>[b]  or  <PMID>.<chunk>.j<k>.a<k>[b] for adjudication
        pmid = label.split('.')[0]
        cwd = rec['cwd']
        tr = Path(rec['transcript'])
        pf = f.parent / f'{label}.prompt.txt'
        prompt = pf.read_text() if pf.exists() else ''
        allow, notes = plain_allow(rec, prompt, pmid)
        row = {'label': label, 'pmid': pmid, 'model': rec['model'], 'session_id': rec['session_id'], 'ok': rec.get('ok'),
               **({'earlier': earlier} if earlier else {})}
        if not tr.exists():
            row.update({'missing_transcript': str(tr), 'broken': True,
                        'violations': [('break', 'transcript', 'missing' + (' (session refused: ' + '; '.join(rec['refused'])
                                                                            + ')' if rec.get('refused') else ''))]})
        else:
            res, _ = audit_agent(tr, [rec['model']], allow, cwd, notes=notes, want_cwd=cwd, baseline=None,
                                 prefix_root=norm(str(ev)), own_out=rec.get('out'), pmid=pmid)
            row.update(res)
        if rec.get('stray'):  # a file the session left in its input folder (moved to logs/<run>/stray/)
            row['violations'] = sorted(set(map(tuple, row.get('violations', []))) | {('break', 'stray_file', ','.join(rec['stray']))})
            row['broken'] = True
        step = label.rsplit('.', 1)[0]
        if step in switches:
            row['model_switch_outcome'] = switches[step].get('outcome')
        out.append(row)
    return out


def order_of(ev, run, base=None):
    """The run's paper order: records/orders/<run>.txt, or the orders/ of a run kept elsewhere (--from)."""
    f = Path(base) / 'orders' / f'{run}.txt' if base else None
    if f and f.exists():
        return [w for w in f.read_text().split() if w]
    return W.read_order(ev, run)


def a6_window(runs_dir, run, sub=''):
    f = Path(runs_dir) / run / sub / 'RESET.json'
    if not f.exists():
        return None, None, {}
    d = json.loads(f.read_text())
    return d.get('started_utc'), d.get('reset_utc'), d


def run_originals(runs_dir, run, sub=''):
    """{pmid: original file} as the kept run's papers.tsv names it (text_source)."""
    f = Path(runs_dir) / run / sub / 'papers.tsv'
    out = {}
    for r in (W.read_tsv(f) if f.exists() else []):
        _, _, path = (r.get('text_source') or '').partition(':')
        if path:
            out[r['pmid']] = path
    return out


def launch_sessions(log_dir, args_out=None):
    """{session id: launch id} of the run's A6 launches (run_a6.py's launch.json; the first dry run's session.json);
    args_out (a dict, when given) gets {session id: the workflow args that launch sent}."""
    out = {}
    for f in sorted(Path(log_dir).glob('**/launch.json')):
        try:
            d = json.loads(f.read_text())
            out[d['session_id']] = d.get('launch') or f.parent.name
            if args_out is not None and d.get('args'):
                args_out[d['session_id']] = d['args']
        except (OSError, json.JSONDecodeError, KeyError):
            continue
    f = Path(log_dir) / 'session.json'
    if f.exists():
        try:
            out.setdefault(json.loads(f.read_text())['session_id'], 'main')
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    return out


def audit_a6(ev, run, projects=None, since=None, until=None, base=None, a6_root=None):
    P = W.eval_paths(ev)
    a6 = str(a6_root or P['a6'])
    rec_base = Path(base or P['records'])
    runs_dir, log_dir = rec_base / 'runs', rec_base / 'logs' / run
    order = set(order_of(ev, run, base))
    roots = projects or glob.glob(str(W.PROJECTS / (W.project_slug(a6) + '*')))
    launch_args = {}
    launches = launch_sessions(log_dir, launch_args)
    windows = []
    s0, s1, _ = a6_window(runs_dir, run)
    windows.append(('main', since or s0, until or s1, run_originals(runs_dir, run)))
    r0, r1, rd = a6_window(runs_dir, run, 'redo')
    if r0:
        windows.append(('redo', r0, r1, run_originals(runs_dir, run, 'redo')))
    out = []
    baseline = instruction_baseline(ev, base)
    for root in roots:
        for tr in sorted(Path(root).glob('*/subagents/**/agent-*.jsonl')):
            seen, calls, versions, models, t0, t1, task = parse(tr)
            if not t0:
                continue
            win = [w for w in windows if not ((w[1] and t1 and t1 < w[1]) or (w[2] and t0 > w[2]))]
            if not win:
                continue
            m = W.READ_TASK.search(task)  # the kit's pattern: human_review's misses the copy's task for a paper with no PMID
            if not m or (order and m.group(1) not in order):
                continue
            pmid = m.group(1)
            root_named = (TASK_ROOT.search(task) or [None, ''])[1] or ''
            if root_named.rstrip('/') != a6.rstrip('/') and a6 not in task:
                continue  # another CatLog folder's agent (production, a worktree): not this run's
            launch, w0, w1, originals = win[-1]
            sid = Path(tr).relative_to(W.PROJECTS).parts[1] if str(tr).startswith(str(W.PROJECTS)) else ''
            launch = launches.get(sid, launch)
            role = ('verify_missed' if re.search(r'Rows to check: \S+\.missed\.read\.json', task) else
                    'verify' if 'prompts/verify.md' in task else 'read')
            meta = tr.with_name(tr.name[:-len('.jsonl')] + '.meta.json')
            desc = json.loads(meta.read_text()).get('description', '') if meta.exists() else ''
            retry = 'sonnet' in desc.lower()
            allowed_models = [W.RETRY_MODEL] if retry else [W.MODEL]
            allow = [a6 + '/', norm(f'/tmp/p{pmid}') + '*']
            allow += [norm(f'/tmp/{r}-{pmid}') + '*' for r in ('read', 'verify', 'verify-missed')]
            orig = originals.get(pmid)
            if orig:  # the paper's original as the run's papers.tsv names it (inside catlog-copy/ since 2026-11-01)
                allow += [norm(orig), str(Path(norm(orig)).parent)]
            # its own session folders (tool results, the scratchpad with its read-/verify-<PMID> folder) come from
            # own_session_dirs(); another agent's transcript there breaks (judge_path)
            req = relayed(task)
            res, _ = audit_agent(tr, allowed_models, allow, a6, forbidden=FORBIDDEN_A6, strict=(EVAL_SCRATCH,),
                                 want_cwd=a6, relay=req, baseline=baseline)
            if root_named and root_named.rstrip('/') != a6.rstrip('/'):
                res['violations'] = sorted(set(res['violations']) | {('break', 'root', root_named)})
                res['broken'] = True
            out.append({'label': desc or tr.stem, 'pmid': pmid, 'role': role, 'retry': retry, 'launch': launch,
                        'session_id': sid, 'relayed_request': req, **res})
    # the launch sessions themselves: their model and what they were shown (the launch line, the folder)
    for sid, launch in sorted(launches.items(), key=lambda x: x[1]):
        for root in roots:
            tr = Path(root) / f'{sid}.jsonl'
            if tr.exists():
                res, task = audit_agent(tr, [W.MODEL], [a6 + '/'], a6, want_cwd=a6, baseline=baseline, git_level='note',
                                        forbidden=FORBIDDEN_A6)
                res['violations'] = sorted(set(launch_paths(res['violations'], str(ev), a6)) |
                                           set(launch_findings(tr, launch_args.get(sid))))
                res['broken'] = any(v[0] == 'break' for v in res['violations'])
                out.append({'label': f'launch:{launch}', 'pmid': '', 'role': 'launch', 'retry': False, 'launch': launch,
                            'session_id': sid, 'relayed_request': '', 'launch_line': task[:600], **res})
    return out


def launch_paths(violations, ev, a6):
    """The launch session runs add and looks around (df, its claim records): its paths and network calls are noted, except
    a path in the eval tree outside catlog-copy (the root's notes such as A6_LAUNCH.md, records/, out/, the other arms'
    folders), which breaks (review of the dry-run fixes: these had been dropped, so a launch session that listed the root
    or read the notes there went unseen)."""
    out = []
    for v in violations:
        if v[1] == 'path' and (v[2] == ev or (v[2].startswith(ev + '/') and not v[2].startswith(a6.rstrip('/') + '/'))):
            out.append(('break',) + tuple(v[1:]))
        elif v[1] in ('path', 'network'):
            out.append(('note',) + tuple(v[1:]))
        else:
            out.append(tuple(v))
    return out


def launch_findings(tr, args):
    """A6's launch session runs the saved workflow with exactly the launch line's args and `catlog.py add`, nothing else:
    a Workflow call with other args or another workflow, or a file it edits or writes, breaks (review of the dry-run
    fixes; args None: a launch kept without its args, the first dry run's)."""
    out = []
    _, calls, *_ = parse(tr)
    for c in calls:
        inp = c['input'] if isinstance(c.get('input'), dict) else {}
        if c['name'] == 'Workflow' and args is not None and (inp.get('name') != 'catlog-batch' or inp.get('args') != args):
            out.append(('break', 'launch_workflow', json.dumps(inp, sort_keys=True)[:200]))
        if c['name'] in ('Edit', 'Write', 'NotebookEdit', 'MultiEdit'):
            out.append(('break', 'launch_edit', str(inp.get('file_path') or inp.get('notebook_path'))))
    return out


def a6_missing(rows, order, launch=None):
    """Papers of the run without a reader transcript or without a verifier transcript (in that launch, when given)."""
    have = {(r['pmid'], r['role']) for r in rows if launch is None or r.get('launch') == launch}
    return [p for p in order if (p, 'read') not in have or (p, 'verify') not in have]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run', help='A0-r1, A2-r1, A6-r1, A0-pilot, ..., adjudication, adjudication_pilot')
    ap.add_argument('--projects', nargs='*', help='A6: Claude Code project folders to scan')
    ap.add_argument('--since', help='A6: ISO time (UTC) the run started, if RESET.json lacks it')
    ap.add_argument('--until', help='A6: ISO time (UTC) the run ended')
    ap.add_argument('--from', dest='base', help='the folder holding the run\'s logs/ and runs/ (a run kept elsewhere)')
    ap.add_argument('--a6-root', help='A6: the CatLog folder the run used (default catlog-copy/)')
    ap.add_argument('--out', help='where to write audit.json, tokens.json, rerun.txt (default records/audit/<run>/)')
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    ev = Path(a.eval)
    P = W.eval_paths(ev)
    is_a6 = a.run.startswith('A6-')
    base = Path(a.base) if a.base else None
    rows = (audit_a6(ev, a.run, a.projects, a.since, a.until, base, a.a6_root) if is_a6 else audit_plain(ev, a.run, base))
    d = Path(a.out) if a.out else P['audit'] / a.run
    d.mkdir(parents=True, exist_ok=True)
    log_dir = Path(base or P['records']) / 'logs' / a.run
    left_out = W.switch_excluded(log_dir)
    papers = [r for r in rows if r.get('pmid')]
    if is_a6:  # a paper read again after a model switch is judged on its redo launches' agents (redo, redo-more-<k>)
        papers = W.a6_judged(papers)
    broken = sorted({r['pmid'] for r in papers if r.get('broken') and r['pmid'] not in left_out and not r.get('earlier')},
                    key=W.pmid_key)
    # a step that ran again (claude_session.keep_earlier): its earlier sessions are audited too; a paper that broke a rule
    # there and breaks again now has broken twice (RUN.md: out of every arm)
    broken_earlier = sorted({r['pmid'] for r in papers if r.get('broken') and r.get('earlier')}, key=W.pmid_key)
    versions = sorted({v for r in rows for v in r.get('versions', [])})
    summary = {'run': a.run, 'time': W.now(), 'agents': len(rows), 'papers': len({r['pmid'] for r in rows if r.get('pmid')}),
               'broken_papers': broken, 'left_out_model_switch': sorted(left_out, key=W.pmid_key),
               'broken_in_an_earlier_invocation': broken_earlier,
               'broken_twice': sorted(set(broken) & set(broken_earlier), key=W.pmid_key),
               'claude_code_versions': versions,
               'models': dict(collections.Counter(m for r in rows for m in r.get('models', []))),
               'model_sequences_switched': sorted({r['model_sequence'] for r in rows if '>' in (r.get('model_sequence') or '')}),
               'violations': dict(collections.Counter(f'{v[0]}:{v[1]}' for r in rows for v in r.get('violations', []))),
               'eval_words_shown': sorted({v[2] for r in rows for v in r.get('violations', []) if v[1] == 'eval_word'}),
               'tokens_total': sum(r.get('total', 0) for r in rows), 'usd_total': round(sum(r.get('usd', 0) for r in rows), 2)}
    if is_a6:
        order = order_of(ev, a.run, base)
        summary['papers_without_reader_or_verifier'] = a6_missing(W.a6_judged(rows), order)  # on what each is judged on
        summary['relayed_requests'] = dict(collections.Counter(r.get('relayed_request', '')[:300] for r in rows
                                                               if r.get('role') != 'launch'))
        summary['relayed_request_names_the_evaluation'] = any(W.eval_word_hits(r.get('relayed_request') or '') for r in rows)
        summary['launch_sessions'] = [{k: r.get(k) for k in ('label', 'session_id', 'model_sequence', 'broken', 'launch_line')}
                                      for r in rows if r.get('role') == 'launch']
        summary['papers_read_again_after_a_model_switch'] = sorted({r['pmid'] for r in rows if r.get('pmid')
                                                                    and W.a6_is_redo(r.get('launch'))}, key=W.pmid_key)
    W.write_json(d / 'audit.json', {'summary': summary, 'agents': rows})
    W.write_json(d / 'tokens.json', [{k: r.get(k) for k in ('label', 'pmid', 'role', 'launch', 'total', 'usd', 'minutes',
                                                             'input_tokens', 'cache_creation_input_tokens',
                                                             'cache_read_input_tokens', 'output_tokens')}
                                     for r in rows if r.get('role') != 'launch'])
    (d / 'rerun.txt').write_text(''.join(p + '\n' for p in broken))
    print(json.dumps(summary, indent=1))
    if len(versions) > 1:
        print('more than one Claude Code version in this run: a round must share one version (FREEZE.md §6)')
    if summary['eval_words_shown']:
        print('a session was shown an evaluation word (cwd, prompt or relayed request): see eval_words_shown')
    if is_a6 and not [r for r in rows if r.get('role') != 'launch']:
        sys.exit(f'no A6 agent transcript found for {a.run}: was the session opened in {a.a6_root or P["a6"]}? '
                 '(--projects names other Claude Code project folders to scan)')


if __name__ == '__main__':
    main()
