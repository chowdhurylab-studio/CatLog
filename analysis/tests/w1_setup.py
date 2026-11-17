#!/usr/bin/env python3
"""W1 setup (FREEZE.md §4-§5, RUN.md §3), run from the w1-eval worktree. Read-only on the main CatLog folder except
for git's own worktree record (`git worktree move` and `remove` of an earlier kind of catlog-copy write main's
.git/worktrees/) and the objects of catlog-copy's snapshot commit (no ref, no branch: main's history and working tree
never change).

  python3 tools/w1/w1_setup.py setup [--people-rounds 1] [--move-a6]
        build or complete the eval tree: plain/<PMID>/ and adj/<PMID>/ inputs, the a6/ checkout and its data files,
        keys/ (gold copies, people key), orders/, plain/validate_plain.py, MANIFEST.json. Refuses to change an input
        that is already there with other bytes. --move-a6 moves catlog-copy to the snapshot of a reviewed kit commit,
        and makes an earlier kind of catlog-copy (any worktree of the main repository: a sparse one at a branch commit,
        one named a6, or one named catlog-copy at the snapshot) again as a plain folder with its own repository at the
        snapshot, keeping every data file (recreate_a6).
  python3 tools/w1/w1_setup.py reset-a6 LABEL [--redo]     (LABEL = dry, pilot, r1, r2, r3)
        after an A6 run's `catlog.py add`: move catlog-copy's catalog.jsonl, rejected.jsonl, bounds.jsonl, log.tsv,
        papers.tsv and work/ to records/runs/A6-LABEL/ (with RESET.json: the run's time window for w1_audit.py) and lay
        down fresh ones; with --redo, the redo of the papers whose agents switched model (run_a6.py LABEL --redo) goes to
        records/runs/A6-LABEL/redo/ (RESET.json also lists its papers); refused while a launch's launcher did not see
        its session to the end (launch.json names it, no agents.json: run_a6.py LABEL --recover LAUNCH)
  python3 tools/w1/w1_setup.py claim PMID ...
        in catlog-copy: a paper to read again after a stop (its work files to work/old/, status reading, a fresh claim)
  python3 tools/w1/w1_setup.py keep-dry NAME      (NAME = dry_run_2, ...)
        move a finished dry run's outputs (out/ folders of its codes, A6's kept run, logs, audits, score_dry) aside to
        records/NAME/, so the next dry run starts clean; nothing is deleted
  python3 tools/w1/w1_setup.py freeze [--force]
        catlog-copy moved to the snapshot of the kit commit (2026-11-09: main's code of that day merged in) and
        MANIFEST.json made again, W1's inputs, orders and keys kept; the manifest before it in records/manifests/; once a
        set after the W1 rounds is laid down (records/a6_inputs_<label>.json, orders/A6-locked.args.json) neither it nor
        setup --move-a6 moves catlog-copy off the snapshot the tag catlog-freeze-20261109 names, unless --force
  python3 tools/w1/w1_setup.py a6-papers LABEL PMID ...      (LABEL = hard, locked)
        catlog-copy laid down for a later set: its texts and originals cloned in (the locked set's from the judges'
        folders checks/<PMID>/, for the first K papers of the draw), papers.tsv with these papers only, claim records,
        records/orders/A6-LABEL.txt and .args.json (lanes 3); refused unless catlog-copy's HEAD and MANIFEST.json's
        a6.pipeline_commit_stamp are the commit the tag catlog-freeze-20261109 names (common_w1.a6_pin_problems)
  python3 tools/w1/w1_setup.py check
        catlog-copy at the manifest's snapshot commit with its harness files unchanged, its own repository, git there
        (log, log --all, status, branch -a, worktree list, reflog, refs, config) showing that one commit only, inputs
        unchanged, no evaluation word in anything a session is shown or an A6 agent can read that production does not
        hold itself, sizes
(install-memory is gone: A6 runs with memory off since 2026-11-01, run_a6.ENV_SET.)

The eval tree (EVAL, default <the kit folder>; common_w1.eval_paths; the first layout, until
the dry-run fixes of 2026-11-01, was <the first layout of the kit folder> with a6/, plain/, adj/, runs/, ...):
  papers/<PMID>/   plain arms' session folder: paper.txt (the production text without its leading GLYPH WARNING
                   paragraph), paper.supp.txt, source.pdf|source.xml (an APFS clone of papers.tsv's text_source file);
                   papers/check_rows.py, the format validator the plain prompts name
  checks/<PMID>/   adjudicators' session folder (development papers): the production text unchanged, supplement, source
  catlog-copy/     A6's CatLog folder: a plain folder with its own git repository (catlog-copy/.git, a folder: no link
                   to the main repository) holding one commit, an orphan snapshot commit 'catlog snapshot' with HEAD
                   detached at it and no branch, tag, remote or reflog; its tree is the branch commit's catlog.py,
                   tools/ without tools/w1/, prompts/, .claude/, CLAUDE.md, config.json, sources/natural_forms.tsv and
                   sources/nopmid_refs.tsv (snapshot_commit, own_repo; git log --all and git branch -a there show that
                   one commit), texts/ (the production texts), papers/<PMID>.<ext> (its own clone of each
                   original, as production keeps them in the main folder's papers/), papers.tsv (the eval's papers only,
                   status reading, text_source naming catlog-copy/papers/), empty catalog.jsonl, rejected.jsonl,
                   bounds.jsonl, log.tsv, a claim record per paper (work/<PMID>.prompts.json via catlog.claim_prompts),
                   .claude/settings.local.json (deny rules: web tools, curl, wget, MCP connectors, reads of the main
                   folder, realkcat and every other part of the eval tree)
  out/<code>/      what sessions write or are given, one folder per arm-run part, claims or verdict set (common_w1.code)
  code/            the w1-eval worktree
  records/         keys/ (the two gold files, sha256 checked against the head-to-head's INPUTS.tsv, and
                   people_values.tsv), orders/ (each arm-run's seeded paper order, the pilot, each round's arm order,
                   A6's args, codes.tsv), logs/, audit/, runs/ (A6's kept runs), score*/, dry_run_*/"""
import argparse, collections, datetime, fcntl, json, math, os, random, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402
import build_people_list as BPL  # noqa: E402
import claude_session as S  # noqa: E402
import h2h  # noqa: E402
import run_a6 as RA6  # noqa: E402

M = W.MAIN
# The files of a branch commit catlog-copy holds, as the sparse-checkout patterns they first were (the last matching
# pattern decides): its snapshot commit's tree is exactly these files (snapshot_tree), so nothing else of the branch
# (tools/w1/, the plans, production's data files) is in catlog-copy's git at all.
A6_SPARSE = ['/catlog.py', '/tools/', '!/tools/w1/', '/prompts/', '/.claude/', '/CLAUDE.md', '/config.json',
             '/sources/natural_forms.tsv', '/sources/nopmid_refs.tsv']
SNAPSHOT_SUBJECT = 'catlog snapshot'  # the only commit message an agent in catlog-copy can see with git log
A6_GIT_META = ('HEAD', 'gitdir', 'commondir', 'config.worktree', 'info/sparse-checkout', 'logs/HEAD')
PIPELINE = ['catlog.py', 'prompts', 'tools/units.py', '.claude/workflows/catlog-batch.js', '.claude/agents/catlog-reader.md']
A6_DATA = ['catalog.jsonl', 'rejected.jsonl', 'bounds.jsonl', 'log.tsv', 'papers.tsv', 'work']
# The sets the copy of the reading steps reads after the W1 rounds, laid down by a6-papers (2026-11-09): the hard set
# with today's rules (CatLog's own reader and verifier on the trap papers), the locked set (unseen held-out papers);
# both on the snapshot the main repository's tag catlog-freeze-20261109 names (common_w1.a6_pin_problems)
LATER_LABELS = W.LATER_LABELS
PAPER_COLS = ['pmid', 'doi', 'title', 'status', 'text_source', 'kept', 'rejected', 'note', 'updated']
MCP_DENY = ['mcp__claude-in-chrome', 'mcp__Claude_Browser', 'mcp__plugin_bio-research_pubmed',
            'mcp__plugin_bio-research_biorxiv', 'mcp__plugin_bio-research_chembl', 'mcp__plugin_bio-research_consensus',
            'mcp__plugin_pdf-viewer_pdf', 'mcp__scheduled-tasks', 'mcp__terminal', 'mcp__Desktop_Commander',
            'mcp__PDF_Tools',
            # the servers this machine's sessions listed on 2026-11-01 that the list above missed (REVIEW.md 1.9):
            # RUN.md "MCP connectors off in every arm"; w1_audit.py breaks on any mcp__ call regardless
            'mcp__plugin_bio-research_wiley', 'mcp__plugin_bio-research_c-trials', 'mcp__plugin_bio-research_ot',
            'mcp__mcp-registry', 'mcp__visualize', 'mcp__PowerPoint__By_Anthropic_', 'mcp__Claude_Code_iOS_Simulator',
            'mcp__ccd_session', 'mcp__ccd_session_mgmt', 'mcp__ccd_directory', 'mcp__ccd_connectors', 'mcp__ccd_host',
            'mcp__ccd_pr', 'mcp__ccd_settings', 'mcp__ccd_sidebar', 'mcp__ccd_view', 'mcp__ccd_window',
            'mcp__<connector id>', 'mcp__<connector id>',
            'mcp__<connector id>', 'mcp__<connector id>',
            'mcp__<connector id>']
GOLD_SRC = {'cosci': M / 'work/top_journal_20261021/benchmarks/cosci_raw' / h2h.GOLD_NAMES['cosci'],
            'ee_manual': M / 'work/top_journal_20261021/benchmarks/enzyextract_si/data/'
                             'dataset_223_EnzyExtract_BRENDA_manual_curation' / h2h.GOLD_NAMES['ee_manual']}
MEMORY = W.MAIN_MEMORY  # main's memory index: not loaded for A6 (memory off since 2026-11-01)


def sh(*cmd, cwd=None, check=True, env=None, input=None):
    """A command with the calling environment's GIT_* variables removed (and `env` added); its stdout, stripped."""
    e = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    e.update(env or {})
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, env=e, input=input)
    if check and r.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd))}\n{r.stdout}\n{r.stderr}")
    return r.stdout.strip()


def blob_sha256(repo, commit, path):
    r = subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', f'{commit}:{path}'], capture_output=True,
                       env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
    return W.sha256_bytes(r.stdout) if r.returncode == 0 else None


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')


def clone(src, dst, data=None):
    """dst as an APFS clone of src (cp -c; a plain copy where cloning fails), or with `data` bytes; read-only. An
    existing dst with the same bytes is kept; with other bytes the setup stops (inputs never change silently)."""
    dst = Path(dst)
    want = W.sha256_bytes(data) if data is not None else W.sha256(src)
    if dst.exists():
        if W.sha256(dst) != want:
            sys.exit(f'{dst} exists with other bytes than its source: inputs never change after setup')
        return want
    dst.parent.mkdir(parents=True, exist_ok=True)
    if data is not None:
        dst.write_bytes(data)
    elif subprocess.run(['cp', '-c', str(src), str(dst)], capture_output=True).returncode:
        shutil.copy2(src, dst)
    os.chmod(dst, 0o444)
    return want


def original_of(row):
    route, _, path = row['text_source'].partition(':')
    return route, Path(path) if path else None


def source_name(path):
    s = path.name.lower()
    return 'source.pdf' if s.endswith('.pdf') else 'source.xml' if s.endswith('.xml') else 'source' + path.suffix.lower()


def a6_original_name(pmid, path):
    """catlog-copy's own name for a paper's original, as production names its downloads (papers/<PMID>.pdf,
    <PMID>.els.xml, <PMID>.jats.xml): the original's name when it is <PMID>.<ext>, else <PMID> + its extension."""
    name = Path(path).name
    if name.startswith(f'{pmid}.') and re.fullmatch(r'[A-Za-z0-9._-]+', name):
        return name
    return f'{pmid}.' + source_name(Path(path)).split('.', 1)[1]


def text_kind(text, src):
    head = text[:3000]
    return 'ocr' if '## OCR TEXT' in head else 'pdf' if '.pdf' in src.lower() else 'xml'


def inputs(ev, papers, dev):
    """plain/<PMID>/ for every paper, adj/<PMID>/ for the development papers, a6/texts/; returns the manifest's
    per-paper input record."""
    P = W.eval_paths(ev)
    st = {r['pmid']: r for r in W.read_tsv(M / 'papers.tsv')}
    out = {}
    for p in papers:
        row = st.get(p)
        if not row:
            sys.exit(f'{p} is not in the main papers.tsv')
        t, sp = M / 'texts' / f'{p}.txt', M / 'texts' / f'{p}.supp.txt'
        route, orig = original_of(row)
        if not t.exists():
            sys.exit(f'{p}: no texts/{p}.txt')
        if not orig or not orig.exists():
            sys.exit(f'{p}: no original file ({row["text_source"][:120]})')
        text = t.read_bytes()
        plain_text = W.strip_glyph(text.decode('utf-8', 'surrogateescape')).encode('utf-8', 'surrogateescape')
        name = source_name(orig)
        rec = {'route': route, 'original': str(orig), 'original_sha256': clone(orig, P['plain'] / p / name),
               'source_name': name, 'text_sha256': W.sha256(t),
               'plain_text_sha256': clone(None, P['plain'] / p / 'paper.txt', plain_text),
               'glyph_warning': text.startswith(b'GLYPH WARNING'), 'text_kind': text_kind(text.decode('utf-8', 'replace'), row['text_source']),
               'doi': row['doi'], 'status_main': row['status']}
        clone(t, P['a6'] / 'texts' / f'{p}.txt')
        a6o = P['a6'] / 'papers' / a6_original_name(p, orig)
        rec['a6_original'] = str(a6o)
        rec['a6_original_sha256'] = clone(orig, a6o)  # A6 reads its own clone: it never opens papers/ (dry-run fix)
        if sp.exists():
            rec['supp_sha256'] = clone(sp, P['plain'] / p / 'paper.supp.txt')
            clone(sp, P['a6'] / 'texts' / f'{p}.supp.txt')
        if p in dev:
            clone(t, P['adj'] / p / 'paper.txt')
            clone(orig, P['adj'] / p / name)
            if sp.exists():
                clone(sp, P['adj'] / p / 'paper.supp.txt')
        out[p] = rec
    return out


# ---------- catlog-copy's commit: an orphan snapshot (the owner's decision, 2026-11-01) ----------
# catlog-copy was a git worktree of the main repository, so an agent there that runs git log, or a gitStatus block, saw
# the kit's commit messages, and its .git file named the worktree 'a6'. It now runs at an orphan commit (no parent) whose
# tree is only the files it holds, under a neutral subject; MANIFEST.json maps that commit to the branch commit and the
# tree hash, and the rows' pipeline_commit stamps are its hash. A worktree of main, even one named catlog-copy at the
# snapshot, still shares main's refs: git log --all, git branch -a and git worktree list there listed the w1-eval branch
# and the kit's commits (independent check, 2026-11-01). So catlog-copy is a plain folder with its own repository
# (own_repo): only the snapshot's objects, HEAD detached at it, no ref of any kind, no reflog, hook or remote.

def in_snapshot(path):
    """Whether a tracked path of a branch commit is one catlog-copy holds (A6_SPARSE; the last matching pattern decides)."""
    keep = False
    for pat in A6_SPARSE:
        neg, p = pat.startswith('!'), pat.lstrip('!').lstrip('/')
        if path.startswith(p) if p.endswith('/') else path == p:
            keep = not neg
    return keep


def snapshot_entries(commit, repo=M):
    """The files of `commit` that catlog-copy holds, as git ls-tree gives them: [(mode, type, object, path)] (read only)."""
    out = []
    for rec in sh('git', '-C', repo, 'ls-tree', '-r', '-z', '--full-tree', commit).split('\0'):
        if rec:
            meta, path = rec.split('\t', 1)
            mode, typ, obj = meta.split()
            if in_snapshot(path):
                out.append((mode, typ, obj, path))
    return out


def snapshot_tree(commit, repo=M):
    """(tree, entries): the tree of the files of `commit` that catlog-copy holds, written to the object store through a
    temporary index file (no index, ref or working tree of any worktree changes)."""
    ents = snapshot_entries(commit, repo)
    with tempfile.TemporaryDirectory() as d:
        env = {'GIT_INDEX_FILE': str(Path(d) / 'index')}
        sh('git', '-C', repo, 'read-tree', '--empty', env=env)
        sh('git', '-C', repo, 'update-index', '-z', '--index-info', env=env,
           input=''.join(f'{mode} {obj}\t{path}\0' for mode, _, obj, path in ents))
        return sh('git', '-C', repo, 'write-tree', env=env), ents


def snapshot_ident(base, repo=M):
    """The author and committer (names, emails, dates) of branch commit `base`, as git's GIT_* variables."""
    f = sh('git', '-C', repo, 'log', '-1', '--date=raw', '--format=%an%x00%ae%x00%ad%x00%cn%x00%ce%x00%cd', base).split('\0')
    return dict(zip(('GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_AUTHOR_DATE', 'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL',
                     'GIT_COMMITTER_DATE'), f))


def snapshot_object(tree, ident):
    """The text of a snapshot commit object: what git commit-tree writes for that tree, identity and subject."""
    return (f"tree {tree}\n"
            f"author {ident['GIT_AUTHOR_NAME']} <{ident['GIT_AUTHOR_EMAIL']}> {ident['GIT_AUTHOR_DATE']}\n"
            f"committer {ident['GIT_COMMITTER_NAME']} <{ident['GIT_COMMITTER_EMAIL']}> {ident['GIT_COMMITTER_DATE']}\n"
            f"\n{SNAPSHOT_SUBJECT}\n")


def snapshot_hash(base, tree, repo=M):
    """The hash snapshot_commit(base) gives when base's files make `tree`, computed without writing anything (git
    hash-object without -w)."""
    return sh('git', '-C', repo, 'hash-object', '-t', 'commit', '--stdin', input=snapshot_object(tree, snapshot_ident(base, repo)))


def snapshot_commit(base, repo=M):
    """catlog-copy's commit for branch commit `base`: an orphan commit (no parent) whose tree is base's files that
    catlog-copy holds (snapshot_tree), with the subject SNAPSHOT_SUBJECT and base's author and committer and their dates,
    so the same base always gives the same commit (git commit-tree; no ref or branch points at it: catlog-copy's HEAD
    keeps it, and MANIFEST.json records how to make it again). Returns its record for the manifest."""
    tree, ents = snapshot_tree(base, repo)
    base = sh('git', '-C', repo, 'rev-parse', f'{base}^{{commit}}')
    commit = sh('git', '-C', repo, 'commit-tree', '--no-gpg-sign', tree, '-m', SNAPSHOT_SUBJECT, env=snapshot_ident(base, repo))
    if commit != snapshot_hash(base, tree, repo):
        sys.exit(f'git commit-tree gave {commit}, not the snapshot object w1_setup expects')
    return {'commit': commit, 'commit12': commit[:12], 'tree': tree, 'branch_commit': base, 'subject': SNAPSHOT_SUBJECT,
            'files': len(ents), 'parents': [],
            'recipe': f"git commit-tree --no-gpg-sign <tree> -m '{SNAPSHOT_SUBJECT}' with the author and committer (names, "
                      "emails, dates) of branch_commit; tree = branch_commit's files that A6_SPARSE selects "
                      '(w1_setup.snapshot_commit)'}


def is_ancestor(a, b, repo=M):
    return subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', a, b], capture_output=True,
                          env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')}).returncode == 0


def is_snapshot(commit, repo=M):
    """Whether a commit is one snapshot_commit makes: no parent, the subject SNAPSHOT_SUBJECT, and only files that
    A6_SPARSE selects (a branch commit, the layout before snapshots, is not)."""
    hdr, _, msg = sh('git', '-C', repo, 'cat-file', 'commit', commit, check=False).partition('\n\n')
    if not hdr or any(x.startswith('parent ') for x in hdr.splitlines()) or msg.strip() != SNAPSHOT_SUBJECT:
        return False
    names = sh('git', '-C', repo, 'ls-tree', '-r', '-z', '--name-only', '--full-tree', commit).split('\0')
    return all(in_snapshot(n) for n in names if n)


def worktree_state(wt, repo=M):
    """(head, snapshot, git folder, sparse) of catlog-copy: its HEAD, whether HEAD is a snapshot (is_snapshot, read
    through catlog-copy's own git, which holds the commit whatever its kind), its git folder (catlog-copy/.git for its
    own repository; for an earlier kind, a worktree of main, the folder under main's .git/worktrees/ whose name its .git
    file shows), and whether it is a sparse checkout."""
    head = sh('git', '-C', wt, 'rev-parse', 'HEAD')
    gitdir = Path(sh('git', '-C', wt, 'rev-parse', '--absolute-git-dir'))
    sparse = sh('git', '-C', wt, 'config', '--get', 'core.sparseCheckout', check=False) == 'true'
    return head, is_snapshot(head, wt), gitdir, sparse


def own_repository(wt):
    """Whether catlog-copy's git is its own repository: its git folder and git's common folder are both <wt>/.git (a
    worktree of main has its git folder under main's .git/worktrees/ and main's .git as the common one, so it shares
    main's branches, commits and worktree list)."""
    want = (Path(wt) / '.git').resolve()
    out = sh('git', '-C', wt, 'rev-parse', '--path-format=absolute', '--absolute-git-dir', '--git-common-dir',
             check=False).splitlines()
    return len(out) == 2 and all(Path(x).resolve() == want for x in out)


def copy_objects(commit, dest, repo=M):
    """Copy the objects of `commit` (a snapshot: the commit, its trees and blobs; it has no parent) from `repo`'s object
    store into the repository at `dest` (git pack-objects | git unpack-objects): nothing else of `repo` goes across, and
    objects `dest` already holds are skipped."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    pack = subprocess.run(['git', '-C', str(repo), 'pack-objects', '--revs', '--stdout', '-q'],
                          input=f'{commit}\n'.encode(), capture_output=True, env=env)
    if pack.returncode:
        sys.exit(f'git pack-objects of {commit[:12]} failed: {pack.stderr.decode(errors="replace")}')
    r = subprocess.run(['git', '-C', str(dest), 'unpack-objects', '-q'], input=pack.stdout, capture_output=True, env=env)
    if r.returncode:
        sys.exit(f'git unpack-objects into {dest} failed: {r.stderr.decode(errors="replace")}')


def own_repo(a6, commit, repo=M):
    """catlog-copy as a plain folder with its own git repository (catlog-copy/.git, a folder) that holds only `commit`
    (a snapshot) and its trees and blobs, copied from `repo` (copy_objects): HEAD detached at it; no branch, tag, remote
    or other ref; no reflog (core.logAllRefUpdates false); an empty template (no hooks, description or info/exclude). So
    git log --all, git branch -a, git worktree list, git reflog and git status there show that one commit and nothing
    of the main repository. The commit's files catlog-copy lacks are checked out (checkout-index never overwrites a
    file); every tracked file must then equal the commit's. Returns the git folder."""
    a6 = Path(a6)
    if (a6 / '.git').exists() or (a6 / '.git').is_symlink():
        sys.exit(f'{a6 / ".git"} exists: own_repo makes a new repository only')
    a6.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tpl:  # an empty template
        sh('git', '-c', 'init.defaultBranch=main', 'init', '-q', f'--template={tpl}', a6)
    sh('git', '-C', a6, 'config', 'core.logAllRefUpdates', 'false')
    copy_objects(commit, a6, repo)
    sh('git', '-C', a6, 'update-ref', '--no-deref', 'HEAD', commit)  # detached at the snapshot; no branch is made
    sh('git', '-C', a6, 'read-tree', commit)
    sh('git', '-C', a6, 'checkout-index', '--all', '--quiet')         # only the files catlog-copy lacks
    sh('git', '-C', a6, 'update-index', '-q', '--refresh', check=False)
    dirty = sh('git', '-C', a6, 'status', '--porcelain', '--untracked-files=no')
    if dirty:
        sys.exit(f'catlog-copy files differ from the snapshot {commit[:12]}: {dirty.splitlines()[:5]}')
    return a6 / '.git'


def snapshot_base(ev, commit, repo=M):
    """The branch commit catlog-copy's snapshot is cut from: catlog-copy's present one when it holds the same files as
    `commit` (a kit change outside them, in tools/w1/ say, keeps catlog-copy's commit as it is): the base the manifest
    records, catlog-copy's own HEAD when that is a branch commit (the layout before snapshots, 3971377), or the branch
    commit whose snapshot catlog-copy's HEAD is (found by its hash among the latest commits with these files).
    Otherwise `commit` itself."""
    P = W.eval_paths(ev)
    want = snapshot_entries(commit, repo)
    cands, head, snap = [], None, False
    try:
        cands.append(json.loads(P['manifest'].read_text())['a6']['snapshot']['branch_commit'])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if (P['a6'] / '.git').exists():
        head, snap, _, _ = worktree_state(P['a6'], repo)
        if not snap:  # a branch commit: the layout before snapshots
            cands.append(head)
    for c in cands:
        if c and is_ancestor(c, commit, repo) and snapshot_entries(c, repo) == want:
            return sh('git', '-C', repo, 'rev-parse', c)
    if head and snap and snapshot_entries(head, P['a6']) == want:  # catlog-copy at a snapshot with these files
        tree = sh('git', '-C', P['a6'], 'rev-parse', 'HEAD^{tree}')     # but no record: the commit it was cut from
        for c in sh('git', '-C', repo, 'rev-list', '--first-parent', '-n', '200', commit).split():
            if snapshot_entries(c, repo) != want:
                break
            if snapshot_hash(c, tree, repo) == head:
                return c
    return sh('git', '-C', repo, 'rev-parse', commit)


def old_worktree(a6, gitdir, snapshot, sparse):
    """Why an existing catlog-copy must be made again ('' when it need not): not its own repository (a worktree of
    main, whatever its name and commit, shares main's refs: git log --all, git branch -a and git worktree list there
    show the kit's branch and commits), a worktree name with an evaluation word (its .git file shows it), a sparse
    checkout, or a HEAD that is a branch commit (git log would show the branch history; a data path the branch tracks
    shows production's file to git diff)."""
    why = []
    if not own_repository(a6):
        why.append(f'a worktree of another repository ({gitdir})')
    if W.eval_word_hits('/' + gitdir.name):
        why.append(f'worktree name {gitdir.name}')
    if sparse:
        why.append('sparse checkout')
    if not snapshot:
        why.append('HEAD is a branch commit')
    return ', '.join(why)


def a6_checkout(ev, commit, move=False, repo=M, force=False):
    """catlog-copy as a plain folder with its own git repository, detached at the snapshot commit of the branch commit
    (snapshot_commit, own_repo). A first setup makes it. With --move-a6 an existing one moves to the snapshot of a
    reviewed kit commit (the snapshot's objects copied in, then git checkout: its data files are untracked and stay),
    and one of an earlier kind (old_worktree: any worktree of the main repository) is made again as a folder with its
    own repository that keeps every data file (recreate_a6); once a set read after the W1 rounds is laid down, neither
    moves it off the frozen tag's snapshot unless force (freeze_move_refused; freeze and setup --move-a6 alike). Returns
    the snapshot's record."""
    P = W.eval_paths(ev)
    a6 = P['a6']
    snap = snapshot_commit(snapshot_base(ev, commit, repo), repo)
    if snapshot_entries(snap['commit'], repo) != snapshot_entries(commit, repo):
        sys.exit('the snapshot does not hold the branch commit\'s files')  # never: snapshot_base checks it
    if not (a6 / '.git').exists():
        if a6.exists() and any(a6.iterdir()):
            sys.exit(f'{a6} exists and has no git repository: move it aside first')
        own_repo(a6, snap['commit'], repo)
    else:
        head, snapshot, gitdir, sparse = worktree_state(a6, repo)
        why = old_worktree(a6, gitdir, snapshot, sparse)
        if move and (why or head != snap['commit']):
            refused = freeze_move_refused(ev, head, snap['commit'], force, repo)
            if refused:
                sys.exit(refused)
        if why:
            if not move:
                sys.exit(f'catlog-copy is of an earlier kind ({why}): run setup with --move-a6 (it makes catlog-copy '
                         'again as a folder with its own repository at the snapshot and keeps its data files)')
            recreate_a6(ev, snap, repo)
        elif head != snap['commit']:
            if not move:
                sys.exit(f'catlog-copy is at {head[:12]}, the snapshot of the branch commit is {snap["commit12"]}: run '
                         'setup with --move-a6 once the change is reviewed (catlog-copy data files stay)')
            copy_objects(snap['commit'], a6, repo)
            changed = sh('git', '-C', a6, 'diff', '--name-only', head, snap['commit']).split()
            harness = [f for f in changed if f.startswith('prompts/') or f in PIPELINE]
            if harness and any((a6 / 'work').glob('*.read.json')):
                sys.exit(f'the new commit changes the harness ({harness[:5]}) and a6 has reads: reset-a6 first')
            sh('git', '-C', a6, 'checkout', '-q', '--detach', snap['commit'])  # data files are untracked: they stay
            if harness:  # the claim records name the prompt hashes: write them again
                rewrite_claims(a6)
    head, snapshot, gitdir, sparse = worktree_state(a6, repo)
    why = old_worktree(a6, gitdir, snapshot, sparse)
    if head != snap['commit'] or why:
        sys.exit(f'catlog-copy is at {head[:12]} ({why or "its own repository"}), not at the snapshot {snap["commit12"]}')
    dirty = sh('git', '-C', a6, 'status', '--porcelain', '--untracked-files=no')
    if dirty:
        sys.exit(f'a6 harness files differ from the commit:\n{dirty}')
    if (a6 / 'tools' / 'w1').exists():
        sys.exit('a6 has tools/w1: the snapshot must leave it out')
    snap.update({'repository': str(gitdir), 'git_kind': 'own repository: catlog-copy/.git holds this commit alone, '
                                                        'HEAD detached, no ref, reflog, remote or hook'})
    return snap


def rewrite_claims(a6):
    """Write catlog-copy's claim records again (they name the prompt hashes)."""
    code = ('import sys; sys.path.insert(0, "."); import catlog\n'
            'for p in sys.argv[1:]:\n    catlog.claim_prompts(p)\n')
    sh(sys.executable, '-B', '-c', code, *[f.name.split('.')[0] for f in (a6 / 'work').glob('*.prompts.json')], cwd=a6)


def files_under(root):
    """Every file and symlink under root (its .git file or folder left out), relative, as posix paths."""
    root = Path(root)
    return sorted(p.relative_to(root).as_posix() for p in root.rglob('*')
                  if (p.is_file() or p.is_symlink()) and p.relative_to(root).parts[0] != '.git')


def move_data(old, new, keep):
    """Move every file of `old` that is not one of `keep` (its commit's own files) to the same path in `new`: a whole
    top-level entry when nothing of `keep` is under it (texts/, papers/, work/, papers.tsv, ...), else file by file
    (.claude/settings.local.json). Never overwrites. Returns the moved paths."""
    old, new = Path(old), Path(new)
    tops = {k.split('/')[0] for k in keep}
    moved = []
    for entry in sorted(old.iterdir()):
        if entry.name == '.git':
            continue
        items = [entry] if entry.name not in tops else \
            [old / f for f in files_under(old) if f.split('/')[0] == entry.name and f not in keep]
        for src in items:
            dst = new / src.relative_to(old)
            if dst.exists() or dst.is_symlink():
                sys.exit(f'{dst} exists: catlog-copy data not moved over it ({src} kept)')
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            moved.append(src.relative_to(old).as_posix())
    return moved


def recreate_a6(ev, snap, repo=M):
    """Make an earlier kind of catlog-copy (a worktree of the main repository) again as a plain folder with its own
    repository at the snapshot (own_repo), keeping every data file: the old worktree's git metadata (HEAD, its reflog,
    sparse patterns) is copied to records/worktrees/<name>-<time>/; the old worktree is moved aside to records/ (git
    worktree move); the new folder is made at catlog-copy/ (own_repo checks out the snapshot's files there); every file
    of the old one that is not one of its commit's own files (texts/, papers/, papers.tsv, work/, the catalog files, the
    run marker, .claude/settings.local.json, anything else) is moved into the new one; then the old one, holding only
    its commit's files, is removed with git worktree remove, which refuses anything else (it stays in records/ then). In
    the main repository only .git/worktrees/ changes: the old worktree's entry goes."""
    P = W.eval_paths(ev)
    a6 = P['a6']
    if not (lock_free(a6 / 'catalog.jsonl.lock') and lock_free(a6 / 'papers.tsv.lock')):
        sys.exit('catlog.py is writing in catlog-copy (a lock is held): wait for it to finish')
    head, _, admin, sparse = worktree_state(a6, repo)
    if own_repository(a6):
        sys.exit(f'catlog-copy has its own repository at {head[:12]}, which is not a snapshot: not made again here')
    keep = {e[3] for e in snapshot_entries(head, a6)}  # the old commit's files catlog-copy holds (its harness)
    new_keep = {e[3] for e in snapshot_entries(snap['commit'], repo)}
    harness_changed = snapshot_entries(head, a6) != snapshot_entries(snap['commit'], repo)
    if harness_changed and any((a6 / 'work').glob('*.read.json')):
        sys.exit('the snapshot changes the harness and catlog-copy has reads: reset-a6 first')
    dirty = [x for x in sh('git', '-C', a6, 'status', '--porcelain', '--untracked-files=no', '--', *sorted(keep)).splitlines() if x]
    if dirty:
        sys.exit(f'catlog-copy harness files differ from its commit: {dirty[:5]}')
    stamp = time.strftime('%Y%m%dT%H%M%S')
    rec = P['records'] / 'worktrees' / f'{admin.name}-{stamp}'
    rec.mkdir(parents=True)
    for f in A6_GIT_META:
        if (admin / f).is_file():
            (rec / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(admin / f, rec / f)
    old = P['records'] / f'catlog-copy-before-{stamp}'
    sh('git', '-C', repo, 'worktree', 'move', a6, old)
    try:
        own_repo(a6, snap['commit'], repo)
    except SystemExit as e:
        if a6.exists():  # the half-made folder is kept aside, never deleted
            shutil.move(str(a6), str(P['records'] / f'catlog-copy-failed-{stamp}'))
        sh('git', '-C', repo, 'worktree', 'move', old, a6)  # back as it was
        sys.exit(f'making catlog-copy\'s own repository failed, catlog-copy left as it was: {e}')
    moved = move_data(old, a6, keep)
    left = set(files_under(old))
    record = {'time': W.now(), 'old_worktree': admin.name, 'old_head': head, 'old_sparse': sparse,
              'moved_aside_to': str(old), 'new_repository': str(worktree_state(a6, repo)[2]),
              'snapshot': snap['commit'], 'moved_into_new': moved, 'new_keep_files': len(new_keep)}
    if left != keep:
        W.write_json(rec / 'RECREATED.json', {**record, 'removed': False, 'left': sorted(left - keep)[:50]})
        sys.exit(f'{old} still holds files that are not its commit\'s: {sorted(left - keep)[:5]} (not removed)')
    if sparse:  # the data paths the old commit tracks (production's, outside the sparse set) are skip-worktree again
        sh('git', '-C', old, 'sparse-checkout', 'reapply')
    status = sh('git', '-C', old, 'status', '--porcelain', '--ignored', '--untracked-files=all')
    if status:
        W.write_json(rec / 'RECREATED.json', {**record, 'removed': False, 'status': status.splitlines()[:50]})
        sys.exit(f'{old} is not clean after the move ({status.splitlines()[:5]}): not removed')
    sh('git', '-C', repo, 'worktree', 'remove', old)  # refuses untracked or changed files: none are left
    if harness_changed:  # the claim records name the prompt hashes: write them again
        rewrite_claims(a6)
    W.write_json(rec / 'RECREATED.json', {**record, 'removed': True, 'claims_rewritten': harness_changed})
    print(f'catlog-copy made again as a folder with its own repository ({record["new_repository"]}) at '
          f'{snap["commit12"]} ({len(moved)} data entries moved over); the old worktree {admin.name} at {head[:12]} '
          f'removed (its git metadata in {rec})')
    return record


def settings_local(ev):
    """catlog-copy/.claude/settings.local.json: web tools, curl, wget and MCP servers off; reads of the main folder,
    realkcat, every other part of the eval tree (catlog-copy keeps its own originals since 2026-11-01, so papers/ too)
    and other sessions' records and scratchpads denied; and no file tool may write into the main folder, realkcat or any
    other part of the eval tree (REVIEW.md 1.9; bash stays the audit's); the owner's downloads closed to reads and
    writes (2026-11-09: other groups' answer keys for the held-out papers sit there)."""
    folders, files = W.eval_entries(ev, keep=(W.OUT_NAMES['a6'],))
    folders += W.old_layout()
    write = [f'{tool}(/{p}/**)' for tool in ('Edit', 'Write') for p in (M, W.REALKCAT, *folders)]
    write += [r for tool in ('Edit', 'Write') for r in S.deny_globs(tool, ev, files)]
    deny = (['WebFetch', 'WebSearch', 'Bash(curl:*)', 'Bash(wget:*)'] + MCP_DENY + S.deny_read(M, W.REALKCAT, *folders)
            + S.deny_globs('Read', ev, files) + S.records_deny('a6', ev) + write + S.downloads_deny('Read', 'Edit', 'Write'))
    return {'permissions': {'deny': deny}}


def seal(ev, on=True):
    """Make every plain/<PMID>/ and adj/<PMID>/ folder read-only (0555), so no session can leave a file where another
    session, arm or round of the paper (or A6, whose originals are there) would find it (REVIEW.md 1.6)."""
    P = W.eval_paths(ev)
    n = 0
    for base in (P['plain'], P['adj']):
        for d in (sorted(base.iterdir()) if base.exists() else []):
            if d.is_dir():
                os.chmod(d, 0o555 if on else 0o755)
                n += 1
    return n


def runs_started(ev):
    """Any arm output: a session's file under out/, a kept A6 run, or a kept dry run (records/dry_run_*/)."""
    P = W.eval_paths(ev)
    places = [P['out'], P['runs']] + sorted(P['records'].glob('dry_run*'))
    return any(d.exists() and any(f.is_file() for f in d.rglob('*')) for d in places)


def lay_down(ev, papers, st):
    """Fresh A6 data files: papers.tsv (the eval's papers, status reading), empty catalog files, work/ with a claim
    record per paper, and the run's start time (common_w1.RUN_MARK, .run_started) for the audit's time window."""
    P = W.eval_paths(ev)
    a6 = P['a6']
    for f in ('catalog.jsonl', 'rejected.jsonl', 'bounds.jsonl', 'log.tsv'):
        if (a6 / f).exists() and (a6 / f).stat().st_size:
            sys.exit(f'a6/{f} is not empty: run reset-a6 first')
        (a6 / f).write_text('')
    (a6 / 'work').mkdir(exist_ok=True)
    now = time.strftime('%Y-%m-%d %H:%M')
    rows = []
    for p in papers:
        r = st[p]
        route, orig = original_of(r)
        src = f"{route}:{a6 / 'papers' / a6_original_name(p, orig)}" if orig else r['text_source']  # text only: as production
        rows.append({'pmid': p, 'doi': r['doi'], 'title': r['title'], 'status': 'reading',
                     'text_source': src, 'kept': '', 'rejected': '', 'note': '', 'updated': now})
    W.write_tsv(a6 / 'papers.tsv', rows, PAPER_COLS)
    code = ('import sys; sys.path.insert(0, "."); import catlog\n'
            'for p in sys.argv[1:]:\n    catlog.claim_prompts(p)\n')
    sh(sys.executable, '-B', '-c', code, *papers, cwd=a6)
    (a6 / W.RUN_MARK).write_text(utc() + '\n')
    W.write_json(a6 / '.claude' / 'settings.local.json', settings_local(ev))


def orders(ev, dev_meta, papers_dev, papers_people, people_rounds):
    P = W.eval_paths(ev)
    gold = {r['pmid']: int(r['gold_cells_cosci'] or 0) + int(r['gold_cells_ee'] or 0) for r in W.read_tsv(W.KIT / 'dev_165.tsv')}
    rng = random.Random(W.SEED_PILOT)
    by_gold = sorted(papers_dev, key=lambda p: (-gold[p], W.pmid_key(p)))
    top = by_gold[:math.ceil(len(papers_dev) / 10)]
    pilot = rng.sample(sorted(top, key=W.pmid_key), 3)
    rest = [p for p in sorted(papers_dev, key=W.pmid_key) if p not in top]  # the strata are disjoint: 3 from the top tenth
    pdf_g = [p for p in rest if dev_meta[p]['text_kind'] in ('pdf', 'ocr') and dev_meta[p]['glyph_warning']]
    pdf_n = [p for p in rest if dev_meta[p]['text_kind'] in ('pdf', 'ocr') and not dev_meta[p]['glyph_warning']]
    xml = [p for p in rest if dev_meta[p]['text_kind'] == 'xml']
    pilot += rng.sample(pdf_g, 2) + rng.sample(pdf_n, 2) + rng.sample(xml, 3)
    # FREEZE.md F6's dry run: 2 small development papers outside the pilot (one PDF, one XML; at most 20 gold cells)
    small = [p for p in sorted(papers_dev, key=W.pmid_key) if p not in pilot and gold[p] <= 20]
    dry = [rng.choice([p for p in small if dev_meta[p]['text_kind'] != 'xml']),
           rng.choice([p for p in small if dev_meta[p]['text_kind'] == 'xml'])]
    files = {'pilot': sorted(pilot, key=W.pmid_key), 'dry': dry}
    for arm in W.ARMS:
        files[W.run_label(arm, 'pilot')] = W.seeded_order(pilot, W.SEED_ORDER + W.ARM_OFFSET[arm])
        files[W.run_label(arm, 'dry')] = dry
        for k in W.ROUNDS:
            ps = papers_dev + (papers_people if k in people_rounds else [])
            files[W.run_label(arm, k)] = W.seeded_order(ps, W.order_seed(arm, k))
    for k in W.ROUNDS:
        files[f'round{k}_arms'] = random.Random(W.SEED_ORDER + 10 * k + W.ROUND_ARM_ORDER).sample(list(W.ARMS), 3)
    out = {}
    for name, ps in files.items():
        f = P['orders'] / f'{name}.txt'
        data = ('\n'.join(ps) + '\n').encode()
        if f.exists() and f.read_bytes() != data:
            sys.exit(f'{f} exists with another order: orders never change after setup')
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        out[name] = {'sha256': W.sha256_bytes(data), 'n': len(ps)}
        if name.startswith('A6-'):  # the Workflow tool's args for this A6 run (A6_LAUNCH.md, run_a6.py)
            W.write_json(P['orders'] / f'{name}.args.json', {'pmids': ps, 'lanes': 9, 'root': str(P['a6'])}, indent=None)
    W.write_tsv(P['orders'] / 'codes.tsv', [{'label': k, 'code': v} for k, v in W.code_table().items()], ['label', 'code'])
    return out


def keys(ev):
    P = W.eval_paths(ev)
    out = {}
    for name, src in GOLD_SRC.items():
        h = W.sha256(src)
        if h != h2h.GOLD_SHA256[name]:
            sys.exit(f'{src}: sha256 {h} is not the head-to-head\'s {h2h.GOLD_SHA256[name]}')
        clone(src, P['keys'] / h2h.GOLD_NAMES[name])
        out[name] = {'source': str(src), 'sha256': h}
    rows = BPL.key_rows(W.people_papers())
    f = P['keys'] / 'people_values.tsv'
    new = f.with_name(f.name + '.new')
    W.write_tsv(new, rows, BPL.KEY_COLS)
    if f.exists() and f.read_bytes() != new.read_bytes() and runs_started(ev):
        new.unlink()  # main's human review keeps changing; the key is frozen once arms have run (REVIEW.md 3.6)
        sys.exit('keys/people_values.tsv would change after arm outputs exist: the people key is frozen at the first run')
    os.replace(new, f)
    out['people_values'] = {'path': str(f), 'sha256': W.sha256(f), 'rows': len(rows),
                            'kinds': dict(collections.Counter(r['kind'] for r in rows)),
                            'source': str(M / 'human_review' / 'compare.tsv'),
                            'source_sha256': W.sha256(M / 'human_review' / 'compare.tsv'),
                            'decisions_sha256': W.sha256(M / 'human_review' / 'decisions.jsonl')}
    return out


def tool_versions():
    def first(cmd):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return (r.stdout or r.stderr).strip().splitlines()[0]
        except (OSError, subprocess.SubprocessError, IndexError):
            return ''
    return {'python3': first([sys.executable, '--version']), 'python3_path': sys.executable,
            'pdftotext': first(['pdftotext', '-v']), 'pdftoppm': first(['pdftoppm', '-v']),
            'git': first(['git', '--version']), 'macos': first(['sw_vers', '-productVersion']),
            'claude_code': S.cli_version(), 'claude_code_cli': W.CLI}


def file_hashes(repo):
    out = {}
    pats = ['catlog.py', 'config.json', 'CLAUDE.md', '.claude/settings.json', '.claude/workflows/catlog-batch.js',
            '.claude/agents/catlog-reader.md', 'tools/*.py', 'tools/w1/*.py', 'tools/w1/prompts/*', 'tools/w1/*.tsv',
            'prompts/*.md', 'paper/planning/w1_kill_test/*', 'paper/planning/w1_kill_test/scripts/*',
            'paper/evidence/h2h_20261101/common.py', 'paper/evidence/h2h_20261101/s06_enzyextract_manual.py']
    for pat in pats:
        for f in sorted(repo.glob(pat)):
            if f.is_file():
                out[str(f.relative_to(repo))] = W.sha256(f)
    return out


def manifest(ev, commit, inp, ords, ks, people_rounds, snap):
    P = W.eval_paths(ev)
    a6_head = snap['commit']
    repo = W.REPO
    prompts = {f.name: W.sha256(f, 12) for f in sorted((P['a6'] / 'prompts').glob('*.md'))}
    task = b''.join(f'=== {f} ===\n'.encode() + (P['a6'] / f).read_bytes()
                    for f in ('.claude/workflows/catlog-batch.js', '.claude/agents/catlog-reader.md'))
    main_head = sh('git', '-C', M, 'rev-parse', 'HEAD')
    m = {
        'created': W.now(), 'eval': str(ev), 'branch': 'w1-eval', 'commit': commit, 'commit12': commit[:12],
        'branched_from': {'repo': str(M), 'commit': '90bbbcffbafc1beb19a203c24674e7ccdd3c18cb',
                          'note': 'main HEAD at 2026-11-01 08:19; main\'s working tree then had an uncommitted catlog.py '
                                  'edit by another chat, and prompts/verify.md and CLAUDE.md were equal to HEAD (their '
                                  'earlier uncommitted edits had been committed: 67c6fe7, ce2b680). The eval uses the '
                                  'branch\'s committed files only; main\'s working tree is never read for the harness.'},
        'main_head_at_setup': main_head,
        'main_uncommitted_at_setup': sh('git', '--no-optional-locks', '-C', M, 'status', '--porcelain', '--untracked-files=no', '--',
                                        'catlog.py', 'prompts', 'tools', '.claude', 'CLAUDE.md', 'config.json', check=False),
        # catlog-copy runs at an orphan snapshot commit (the owner's decision, 2026-11-01): 'snapshot' maps it to the
        # branch commit its files were cut from and to its tree (the same files as the kit commit `commit`: a kit change
        # outside them keeps the snapshot, snapshot_base); the rows' pipeline_commit stamps are its hash
        'a6': {'path': str(P['a6']), 'head': a6_head, 'sparse': A6_SPARSE, 'settings_local': settings_local(ev),
               'pipeline_commit_stamp': a6_head[:12], 'snapshot': {**snap, 'same_files_as_kit_commit': commit}},
        'prompt_hashes_stamp_style': prompts, 'task_text_hash': W.sha256_bytes(task, 12),
        'files_sha256': file_hashes(repo),
        'memory_index': {'a6': 'off: CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 in run_a6.ENV_SET (the owner\'s decision, '
                               '2026-11-01), as for the plain arms and adjudicators; main\'s index is not loaded',
                         'not_loaded': str(MEMORY), 'sha256': W.sha256(MEMORY) if MEMORY.exists() else None},
        'models': {'session': W.MODEL, 'retry': W.RETRY_MODEL, 'effort': W.EFFORT},
        'instructions_baseline': W.instruction_baseline(ev),
        'tools': tool_versions(),
        'layout': {k: str(P[k]) for k in ('eval', 'a6', 'plain', 'adj', 'out', 'repo', 'records')},
        'first_layout': {'root': str(W.OLD_EVAL), 'note': 'the dry run of 2026-11-01 ran there; its outputs are kept in '
                                                          'records/dry_run_1/ (their records name the old paths)'},
        'codes': W.code_table(),
        'eval_words': {'path': list(W.EVAL_PATH_WORDS), 'text': list(W.EVAL_TEXT_WORDS)},
        'model_pin': {'env': W.PIN_ENV, 'switch_file': W.MODEL_SWITCH_FILE,
                      'rule': 'a session that shows another model than it was started with runs once more; a second '
                              'switch leaves the paper out of every arm (common_w1.PIN_ENV, claude_session.step, run_a6.py)'},
        'plain_session': {'command': S.command(W.MODEL, '<uuid>', ['<output folder>'], ['<read-deny rules>']),
                          'env': sorted(S.clean_env()), 'env_set': S.ENV_SET, 'cwd': str(P['plain'] / '<PMID>'),
                          'prompt_files': {f.name: W.sha256(f) for f in sorted(W.PROMPTS.glob('*'))}},
        'a6_session': {'command': RA6.command('<uuid>'), 'env': sorted(RA6.env()), 'env_set': RA6.ENV_SET,
                       'no_git_context': 'CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1: no gitStatus block (the kit\'s recent '
                                         'commits) in the session\'s or its agents\' context',
                       'no_memory': 'CLAUDE_CODE_DISABLE_AUTO_MEMORY=1: no memory index (main\'s names the paper\'s '
                                    'plans) in the session\'s or its agents\' context',
                       'cwd': str(P['a6']), 'setting_sources': 'default (user, project, local), as production',
                       'launch_lines': {f.name[:-len('.args.json')]: RA6.launch_line(json.loads(f.read_text()))
                                        for f in sorted(P['orders'].glob('A6-*.args.json'))}},
        'seeds': {'order': f'{W.SEED_ORDER} + 10 x round + {W.ARM_OFFSET}', 'round_arm_order': f'{W.SEED_ORDER} + 10 x round + {W.ROUND_ARM_ORDER}',
                  'pilot': W.SEED_PILOT, 'bootstrap': W.SEED_BOOT, 'claim_pool': W.SEED_POOL, 'people_sample': W.SEED_PEOPLE},
        'people_rounds': people_rounds, 'orders': ords,
        'paper_lists': {'dev_165.tsv': W.sha256(W.KIT / 'dev_165.tsv'), 'holdout_374.tsv': W.sha256(W.KIT / 'holdout_374.tsv'),
                        'people_100.tsv': W.sha256(W.W1 / 'people_100.tsv'),
                        'sources/holdout_locked.txt@commit': blob_sha256(repo, commit, 'sources/holdout_locked.txt')},
        'keys': ks, 'inputs': inp,
    }
    W.write_json(P['manifest'], m)
    return m


def cmd_setup(ev, people_rounds, move_a6=False, no_seal=False, force=False):
    P = W.eval_paths(ev)
    free = W.disk_free_gb(ev)
    if free < 20:
        sys.exit(f'{free:.0f} GB free: below 20 GB no bulk copies (~/.claude/CLAUDE.md)')
    if free < 30:
        print(f'note: {free:.0f} GB free, below the 30 GB line (~/.claude/CLAUDE.md); the eval tree is small')
    if sh('git', '-C', W.REPO, 'rev-parse', '--abbrev-ref', 'HEAD') != 'w1-eval':
        sys.exit('run from the w1-eval worktree')
    if sh('git', '-C', W.REPO, 'status', '--porcelain', '--untracked-files=no'):
        sys.exit('the w1-eval worktree has uncommitted changes: commit first (a6 is checked out at the commit)')
    commit = sh('git', '-C', W.REPO, 'rev-parse', 'HEAD')
    dev, people = W.dev_papers(), W.people_papers()
    hold = set(W.holdout_papers())
    locked = set(sh('git', '-C', W.REPO, 'show', f'{commit}:sources/holdout_locked.txt').split())
    bad = [p for p in dev + people if p in hold or p in locked]
    if bad or set(dev) & set(people):
        sys.exit(f'hold-out or overlapping papers in the eval lists: {bad[:5]} {sorted(set(dev) & set(people))[:5]}')
    papers = W.eval_papers()
    st = {r['pmid']: r for r in W.read_tsv(M / 'papers.tsv')}
    snap = a6_checkout(ev, commit, move_a6, force=force)  # first: git wants an empty folder for the worktree
    head = snap['commit']
    seal(ev, False)  # the input folders take new files only here
    try:
        inp = inputs(ev, papers, set(dev))
    finally:  # sealed again even when inputs() refuses a changed input
        sealed = 0 if no_seal else seal(ev, True)
    if stale_a6_sources(ev, inp):  # a new layout or new originals: lay the papers.tsv down again (no run data yet)
        if a6_has_run_data(ev):
            sys.exit('catlog-copy/papers.tsv names other originals but catlog-copy holds a run: reset-a6 first')
        for f in ('catalog.jsonl', 'rejected.jsonl', 'bounds.jsonl', 'log.tsv'):
            (P['a6'] / f).unlink(missing_ok=True)  # empty files (a6_has_run_data checked it); lay_down writes them again
        lay_down(ev, papers, st)
    old_mark, mark = P['a6'] / W.OLD_RUN_MARK, P['a6'] / W.RUN_MARK
    if old_mark.exists():  # review fix: the marker's name had w1 in it (catlog-copy's root is listed by its agents)
        if not mark.exists():
            old_mark.rename(mark)
        else:
            old_mark.unlink()
    W.write_json(P['a6'] / '.claude' / 'settings.local.json', settings_local(ev))  # kept current with the kit
    shutil.copyfile(W.W1 / 'validate_plain.py', P['validator'])  # papers/check_rows.py: the {VALIDATE} of the prompts
    for d in ('records', 'out', 'runs', 'logs', 'audit', 'score', 'orders', 'keys'):
        P[d].mkdir(parents=True, exist_ok=True)
    ks = keys(ev)
    ords = orders(ev, {p: inp[p] for p in dev}, dev, people, people_rounds)
    m = manifest(ev, commit, inp, ords, ks, people_rounds, snap)
    m['input_folders_sealed'] = sealed  # papers/<PMID>/ and checks/<PMID>/ read-only (0555); 0 with --no-seal
    W.write_json(P['manifest'], m)
    du = sh('du', '-sk', ev, check=False).split()[0]
    print(f"eval tree {ev}: {len(papers)} papers ({len(dev)} development, {len(people)} people), catlog-copy at the "
          f"snapshot {head[:12]} of {snap['branch_commit'][:12]} (own repository {snap['repository']}), "
          f"prompts {m['prompt_hashes_stamp_style']}, task {m['task_text_hash']}; du {int(du) / 1024:.0f} MB logical "
          f"(clones share their blocks with the originals)")


def stale_a6_sources(ev, inp):
    """catlog-copy/papers.tsv is missing, lacks a paper, or names another original than catlog-copy/papers/ holds."""
    f = W.eval_paths(ev)['a6'] / 'papers.tsv'
    if not f.exists():
        return True
    have = {r['pmid']: r['text_source'].partition(':')[2] for r in W.read_tsv(f)}
    return any(have.get(p) != rec['a6_original'] for p, rec in inp.items())


def a6_has_run_data(ev):
    a6 = W.eval_paths(ev)['a6']
    data = any((a6 / f).exists() and (a6 / f).stat().st_size for f in ('catalog.jsonl', 'rejected.jsonl', 'bounds.jsonl'))
    return data or any((a6 / 'work').glob('*.read.json')) or any((a6 / 'work').glob('*.verify.json'))


def lock_free(path):
    if not path.exists():
        return True
    with open(path) as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fh, fcntl.LOCK_UN)
            return True
        except OSError:
            return False


def unfinished_launches(ev, label):
    """The launch folders of A6-<label> whose launch.json names a session but that have no agents.json: a launch still
    running, or killed on the way (run_a6.py --recover completes its records; its papers' model_switch.json outcomes
    are written only then)."""
    out = []
    for d in W.a6_launches(ev, label):
        try:
            sid = json.loads((d / 'launch.json').read_text()).get('session_id')
        except (OSError, json.JSONDecodeError):
            sid = None
        if sid and not (d / 'agents.json').exists():
            out.append(d.name)
    return out


def redo_pmids(ev, label):
    """The papers run_a6.py LABEL --redo launched (its launch.json files)."""
    out = []
    for f in sorted((W.eval_paths(ev)['logs'] / f'A6-{label}').glob('redo*/launch.json')):
        out += [str(p) for p in json.loads(f.read_text()).get('pmids') or [] if str(p) not in out]
    return out


def cmd_reset_a6(ev, label, redo=False):
    P = W.eval_paths(ev)
    a6 = P['a6']
    if label not in RA6.LABELS:
        sys.exit(f'LABEL is dry (FREEZE.md F6), pilot, r1, r2, r3, or a set a6-papers laid down ({", ".join(LATER_LABELS)})')
    run_dir = P['runs'] / f'A6-{label}'
    dest = run_dir / 'redo' if redo else run_dir
    if redo and not run_dir.exists():
        sys.exit(f'{run_dir} does not exist: keep the run first (reset-a6 {label})')
    if dest.exists():
        sys.exit(f'{dest} exists: each A6 run (and its redo) is kept once')
    pmids = redo_pmids(ev, label) if redo else []
    if redo and not pmids:
        sys.exit(f'no redo launch in records/logs/A6-{label}/ (run_a6.py {label} --redo)')
    if not (lock_free(a6 / 'catalog.jsonl.lock') and lock_free(a6 / 'papers.tsv.lock')):
        sys.exit('catlog.py is writing in catlog-copy (a lock is held): wait for `add` to finish')
    open_ = unfinished_launches(ev, label)
    if open_:
        sys.exit(f'launches of A6-{label} whose launcher did not see their session to the end (launch.json names it, no '
                 f'agents.json): {open_}; when the session has ended, run run_a6.py {label} --recover LAUNCH for each')
    dest.mkdir(parents=True)
    mark = next((a6 / f for f in (W.RUN_MARK, W.OLD_RUN_MARK) if (a6 / f).exists()), None)
    started = mark.read_text().strip() if mark else None
    statuses = collections.Counter(r['status'] for r in W.read_tsv(a6 / 'papers.tsv'))
    rows = sum(1 for line in open(a6 / 'catalog.jsonl') if line.strip()) if (a6 / 'catalog.jsonl').exists() else 0
    for f in A6_DATA:
        if (a6 / f).exists():
            shutil.move(str(a6 / f), str(dest / f))
    for f in ('catalog.jsonl.lock', 'papers.tsv.lock', W.RUN_MARK, W.OLD_RUN_MARK):
        if (a6 / f).exists():
            (a6 / f).unlink()
    moved, left = collect_a6_scratch(ev, pmids or W.read_order(ev, f'A6-{label}') or W.eval_papers(), dest / 'scratch')
    W.write_json(dest / 'RESET.json', {'label': label, 'redo': redo, 'pmids': pmids, 'started_utc': started,
                                        'reset_utc': utc(), 'a6_head': sh('git', '-C', a6, 'rev-parse', 'HEAD'),
                                        'catalog_rows': rows, 'statuses': dict(statuses), 'scratch_moved': len(moved),
                                        'scratch_left': len(left)})
    st = {r['pmid']: r for r in W.read_tsv(M / 'papers.tsv')}
    # a later set is laid down again (its redo reads in the fresh catlog-copy; a6-papers lays down the next set), its
    # papers.tsv naming the originals a6-papers cloned in, whatever production's papers.tsv says by now
    if label in LATER_LABELS:
        lay_down(ev, W.read_order(ev, f'A6-{label}'), later_rows(ev, label, st))
    else:
        lay_down(ev, W.eval_papers(), st)
    print(f'A6-{label}{" redo" if redo else ""}: {rows} rows and the work files moved to {dest}; catlog-copy has fresh '
          'files for the next run')


def collect_a6_scratch(ev, papers, dest):
    """The run's non-image A6 scratch (read-, verify-, verify-missed-<PMID> in /tmp and in the scratchpads of sessions
    opened in a6/: build scripts, notes, drafts) moved into dest, so the next run's agents cannot reuse it; page images
    stay (REVIEW.md 1.5). Returns (moved, left)."""
    a6slug = W.project_slug(W.eval_paths(ev)['a6'])
    roots = [W.TMP] + sorted(W.CLAUDE_TMP.glob(a6slug + '*/*/scratchpad'))
    moved, left = [], []
    for root in roots:
        sub = dest / ('tmp' if root == W.TMP else str(root.relative_to(W.CLAUDE_TMP).parent))
        for p in papers:
            for role in ('read', 'verify', 'verify-missed'):
                rx = re.compile(rf'{re.escape(role)}-{re.escape(p)}(?![0-9A-Za-z])')
                m, lf = S.collect_scratch(f'{role}-{p}', sub, root, keep_name=lambda n, rx=rx: bool(rx.match(n)))
                moved += m
                left += lf
    return moved, left


def dry_parts(ev):
    """Every place a dry run (FREEZE.md F6) leaves output: its out/ folders (A0, A2's parts, the claims and verdicts),
    A6's kept run, the logs, audits and scores."""
    P, Q = W.eval_paths(ev), W.eval_paths(ev, 'dry')
    labels = [W.part_label('A0', 'dry')] + [W.part_label('A2', 'dry', p) for p in W.PLAIN_PARTS]
    outs = [W.out_dir(ev, lab) for lab in labels] + [Q['claims'], Q['claims3'], *Q['verdicts'].values()]
    recs = [P['runs'] / 'A6-dry', Q['score']] + [P[k] / f'{a}-dry' for k in ('logs', 'audit') for a in W.ARMS]
    recs += [P['logs'] / 'adjudication_dry', P['audit'] / 'adjudication_dry']
    return [d for d in outs + recs if d.exists()]


def cmd_keep_dry(ev, name):
    """Move a finished dry run's outputs aside, to records/<name>/ (the same paths below it), so the next dry run starts
    clean; nothing is deleted. The codes of the out/ folders are in records/orders/codes.tsv."""
    P = W.eval_paths(ev)
    if not re.fullmatch(r'dry_run_\w+', name):
        sys.exit('NAME is dry_run_<something>, e.g. dry_run_2')
    dest = P['records'] / name
    if dest.exists():
        sys.exit(f'{dest} exists')
    parts = dry_parts(ev)
    if not parts:
        sys.exit('no dry-run output to keep')
    for d in parts:
        t = dest / d.relative_to(ev)
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(d), str(t))
    print(f'{len(parts)} dry-run folders moved to {dest}')


def cmd_plain_inputs(ev, pmids):
    """papers/<PMID>/ only (paper.txt without its GLYPH WARNING line, the original as source.*, the supplement), for
    papers outside the three sets: the hard-case set (2026-11-02). Nothing goes into catlog-copy or adj/ and
    MANIFEST.json is not changed; the records go to records/hard_inputs.json, written after each paper. A folder of the
    three sets (MANIFEST inputs) is used as it is; any other folder is (re)built, its files kept only when they have the
    same bytes, and sealed (0555) like the others. A paper whose text came from an API with no original on disk gets
    paper.txt alone (the production reader had no more)."""
    P = W.eval_paths(ev)
    st = {r['pmid']: r for r in W.read_tsv(M / 'papers.tsv')}
    kit = set(json.loads(P['manifest'].read_text()).get('inputs', {})) if P['manifest'].exists() else set()
    rec_file = P['records'] / 'hard_inputs.json'
    recs = json.loads(rec_file.read_text()) if rec_file.exists() else {}
    made, text_only = [], []
    for p in pmids:
        d = P['plain'] / p
        if p in recs and (recs[p].get('existed') or recs[p].get('plain_text_sha256')):
            continue
        if d.exists() and p in kit:
            recs[p] = {'existed': True}
            continue
        row = st.get(p)
        if not row:
            sys.exit(f'{p} is not in the main papers.tsv')
        t, sp = M / 'texts' / f'{p}.txt', M / 'texts' / f'{p}.supp.txt'
        route, orig = original_of(row)
        if not t.exists():
            sys.exit(f'{p}: no texts/{p}.txt')
        if d.exists():
            os.chmod(d, 0o755)
        text = t.read_bytes()
        plain_text = W.strip_glyph(text.decode('utf-8', 'surrogateescape')).encode('utf-8', 'surrogateescape')
        rec = {'route': route, 'text_sha256': W.sha256(t), 'plain_text_sha256': clone(None, d / 'paper.txt', plain_text),
               'glyph_warning': text.startswith(b'GLYPH WARNING'),
               'text_kind': text_kind(text.decode('utf-8', 'replace'), row['text_source']), 'doi': row['doi'],
               'status_main': row['status'], 'existed': False, 'time': W.now()}
        if orig and orig.exists():
            name = source_name(orig)
            rec.update({'original': str(orig), 'original_sha256': clone(orig, d / name), 'source_name': name})
        else:
            rec.update({'original': None, 'source_name': None, 'note': f'text only: no original on disk ({row["text_source"][:80]})'})
            text_only.append(p)
        if sp.exists():
            rec['supp_sha256'] = clone(sp, d / 'paper.supp.txt')
        os.chmod(d, 0o555)
        recs[p] = rec
        made.append(p)
        rec_file.parent.mkdir(parents=True, exist_ok=True)
        rec_file.write_text(json.dumps(recs, indent=1, sort_keys=True) + '\n')
    rec_file.parent.mkdir(parents=True, exist_ok=True)
    rec_file.write_text(json.dumps(recs, indent=1, sort_keys=True) + '\n')
    print(f'plain inputs made for {len(made)} papers ({len(text_only)} text only: {" ".join(text_only)}), '
          f'{len(pmids) - len(made)} already there; records in {rec_file}')


def cmd_judge_inputs(ev, pmids):
    """checks/<PMID>/ for papers outside the development set (the further set read once, 2026-11-04): the production
    text unchanged (with its GLYPH WARNING line, as the development papers' judges have it), the original as source.*,
    the supplement; sealed (0555) like the others. A paper with no original on disk is refused: a judge must be able to
    see the page. A folder setup made (development papers) is used as it is. Records: records/judge_inputs.json."""
    P = W.eval_paths(ev)
    st = {r['pmid']: r for r in W.read_tsv(M / 'papers.tsv')}
    dev = set(W.dev_papers())
    rec_file = P['records'] / 'judge_inputs.json'
    recs = json.loads(rec_file.read_text()) if rec_file.exists() else {}
    made = []
    for p in pmids:
        d = P['adj'] / p
        if p in recs:
            continue
        if p in dev:
            if not d.exists():
                sys.exit(f'{p} is a development paper without its checks/ folder: run setup')
            recs[p] = {'existed': True}
            continue
        row = st.get(p)
        if not row:
            sys.exit(f'{p} is not in the main papers.tsv')
        t, sp = M / 'texts' / f'{p}.txt', M / 'texts' / f'{p}.supp.txt'
        route, orig = original_of(row)
        if not t.exists():
            sys.exit(f'{p}: no texts/{p}.txt')
        if not orig or not orig.exists():
            sys.exit(f'{p}: no original file ({row["text_source"][:120]}): a judge must see the page')
        if d.exists():
            os.chmod(d, 0o755)
        name = source_name(orig)
        rec = {'route': route, 'text_sha256': clone(t, d / 'paper.txt'), 'original': str(orig),
               'original_sha256': clone(orig, d / name), 'source_name': name, 'existed': False, 'time': W.now()}
        if sp.exists():
            rec['supp_sha256'] = clone(sp, d / 'paper.supp.txt')
        os.chmod(d, 0o555)
        recs[p] = rec
        made.append(p)
        rec_file.parent.mkdir(parents=True, exist_ok=True)
        rec_file.write_text(json.dumps(recs, indent=1, sort_keys=True) + '\n')
    rec_file.parent.mkdir(parents=True, exist_ok=True)
    rec_file.write_text(json.dumps(recs, indent=1, sort_keys=True) + '\n')
    print(f'judge folders made for {len(made)} papers, {len(pmids) - len(made)} already there; records in {rec_file}')


def later_sets_laid(ev):
    """The records that a set of LATER_LABELS was laid down in catlog-copy (a6-papers: records/a6_inputs_<label>.json,
    and the locked set's order records/orders/A6-locked.args.json)."""
    P = W.eval_paths(ev)
    return [f for f in [P['records'] / f'a6_inputs_{lab}.json' for lab in LATER_LABELS] + [P['orders'] / 'A6-locked.args.json']
            if f.exists()]


def freeze_move_refused(ev, head, snap, force=False, repo=None):
    """Why freeze or setup --move-a6 may not move catlog-copy from its snapshot `head` to `snap` ('' when it may): once a
    set read after the W1 rounds is laid down (later_sets_laid: the hard set since 9 November, whose redo needs the same
    snapshot, and the locked set), the copy stays on the snapshot the main repository's tag common_w1.FREEZE_TAG names,
    the one the stamp check pins (freeze_stamp): a move to any other snapshot is refused, unless --force."""
    laid = later_sets_laid(ev)
    if head == snap or force or not laid:
        return ''
    want = W.freeze_stamp(repo or M)
    if str(snap)[:12] == want:
        return ''
    return (f'{laid[0]} exists: the sets after the W1 rounds are read on the snapshot {want} (the tag {W.FREEZE_TAG}), and '
            f'this would move catlog-copy from {str(head)[:12]} to {str(snap)[:12]} (--force moves it anyway; the stamp '
            'and pin checks then refuse what is laid down, launched or kept on the new snapshot)')


def cmd_freeze(ev, force=False):
    """catlog-copy moved to the snapshot of the kit commit for the sets after the W1 rounds (2026-11-09: main's code of
    that day merged into the branch first): setup's checks of the branch, then a6_checkout with the move (refused while
    catlog-copy holds reads, and off the frozen tag's snapshot once a set after the W1 rounds is laid down unless
    --force: freeze_move_refused), and
    MANIFEST.json made again by manifest() with W1's inputs, orders, keys and people rounds as they were, plus a 'freeze'
    record. The manifest before it is kept in records/manifests/ (nothing deleted). Run it again after a kit commit outside
    the harness files: the snapshot stays (snapshot_base), the manifest follows."""
    P = W.eval_paths(ev)
    if sh('git', '-C', W.REPO, 'rev-parse', '--abbrev-ref', 'HEAD') != 'w1-eval':
        sys.exit('run from the w1-eval worktree')
    if sh('git', '-C', W.REPO, 'status', '--porcelain', '--untracked-files=no'):
        sys.exit('the w1-eval worktree has uncommitted changes: commit first (catlog-copy is cut from the commit)')
    if a6_has_run_data(ev):
        sys.exit('catlog-copy holds a run: reset-a6 first')
    commit = sh('git', '-C', W.REPO, 'rev-parse', 'HEAD')
    old = json.loads(P['manifest'].read_text())
    why = freeze_move_refused(ev, sh('git', '-C', P['a6'], 'rev-parse', 'HEAD', check=False),
                              snapshot_commit(snapshot_base(ev, commit, M), M)['commit'], force)
    if why:
        sys.exit(why)
    keep = P['records'] / 'manifests' / f"MANIFEST_{old['a6']['head'][:12]}_{old['commit12']}.json"
    keep.parent.mkdir(parents=True, exist_ok=True)
    if not keep.exists():
        shutil.copyfile(P['manifest'], keep)
    before = old['a6']['head']
    snap = a6_checkout(ev, commit, True, M, force)
    W.write_json(P['a6'] / '.claude' / 'settings.local.json', settings_local(ev))
    m = manifest(ev, commit, old['inputs'], old['orders'], old['keys'], old['people_rounds'], snap)
    merged = sh('git', '-C', W.REPO, 'merge-base', commit, 'main')  # the last main commit the branch merged
    m['freeze'] = {'time': W.now(), 'a6_before': before, 'a6_after': snap['commit'], 'kit_commit': commit,
                   'main_merged': merged, 'manifest_before': str(keep),
                   'note': 'the sets after the W1 rounds (w1_setup.py a6-papers: hard, locked) read with this snapshot; '
                           'W1\'s inputs, orders and keys are the first setup\'s'}
    W.write_json(P['manifest'], m)
    print(f"catlog-copy at the snapshot {snap['commit'][:12]} of {snap['branch_commit'][:12]} (before {before[:12]}); "
          f"prompts {m['prompt_hashes_stamp_style']}, task {m['task_text_hash']}; manifest before kept in {keep}")


def locked_inputs(ev, pmids, st, recorded):
    """The locked set's files for catlog-copy (cmd_a6_papers): clones of the judges' folders checks/<PMID>/ (paper.txt,
    paper.supp.txt, source.*: the production text, supplement and original as judge-inputs recorded them at the draw),
    never the main folder's current files, so a later retext, supplement or new original in production can neither block
    the set nor change it. Refused, with nothing laid down, unless the papers are the first K of
    records/orders/locked_draw.txt in its order and each has a hard_inputs and a judge_inputs record holding the sha256 of
    what its checks/ folder holds (the hash comparison stays the check). Returns ({pmid: a6_inputs record}, {pmid:
    papers.tsv row for lay_down: the recorded route and original, main's doi and title as at the lay-down})."""
    P = W.eval_paths(ev)
    draw = W.read_order(ev, 'locked_draw')
    if not draw or pmids != draw[:len(pmids)]:
        skipped = [p for p in draw[:len(pmids)] if p not in set(pmids)]
        sys.exit(f'a6-papers locked lays down the first K papers of records/orders/locked_draw.txt in its order: draw papers '
                 f'skipped {skipped[:10]}, papers outside the draw {[p for p in pmids if p not in set(draw)][:10]}')
    missing = [f'{p} ({", ".join(n for n in ("hard_inputs", "judge_inputs") if p not in recorded[n])})' for p in pmids
               if p not in recorded['hard_inputs'] or p not in recorded['judge_inputs']]
    if missing:
        sys.exit(f'{len(missing)} papers have no input record (plain-inputs, judge-inputs first): {missing[:10]}')
    files, differ = {}, []
    for p in pmids:
        d, jr = P['adj'] / p, recorded['judge_inputs'][p]
        t, sp = d / 'paper.txt', d / 'paper.supp.txt'
        o = d / jr['source_name'] if jr.get('source_name') else None
        have = (W.sha256(t) if t.exists() else None, W.sha256(o) if o and o.exists() else None,
                W.sha256(sp) if sp.exists() else None)
        for name in ('hard_inputs', 'judge_inputs'):
            keys = [k for k, x, y in zip(W.INPUT_KEYS, W.input_hashes(recorded[name][p]), have) if x != y]
            if keys:
                differ.append(f'{p} ({name}: {", ".join(keys)})')
        files[p] = (t, sp, o, jr)
    if differ:
        sys.exit(f'{len(differ)} papers\' judge folders (checks/<PMID>/) do not hold what the plain read\'s or the judges\' '
                 f'records name (records/hard_inputs.json, judge_inputs.json): {differ[:10]}; nothing laid down')
    recs, rows = {}, {}
    for p in pmids:
        t, sp, o, jr = files[p]
        row = {'doi': '', 'title': '', **(st.get(p) or {})}
        recs[p] = {'route': jr.get('route'), 'laid_from': str(t.parent), 'doi': row['doi'], 'title': row['title'],
                   'text_sha256': clone(t, P['a6'] / 'texts' / f'{p}.txt'), 'status_main': row.get('status')}
        if jr.get('original'):
            a6o = P['a6'] / 'papers' / a6_original_name(p, jr['original'])
            recs[p].update({'original': jr['original'], 'a6_original': str(a6o), 'original_sha256': clone(o, a6o)})
        if sp.exists():
            recs[p]['supp_sha256'] = clone(sp, P['a6'] / 'texts' / f'{p}.supp.txt')
        rows[p] = {**row, 'text_source': f"{jr.get('route')}:{jr.get('original') or ''}"}
    return recs, rows


def later_rows(ev, label, st):
    """papers.tsv rows for laying a set of LATER_LABELS down again (reset-a6: its redo reads in the fresh catlog-copy) from
    the set's record (records/a6_inputs_<label>.json): the route and the original a6-papers cloned into catlog-copy (for
    a paper whose text came with no original, the route alone, as a6-papers laid it down: a file production files later
    was never cloned into the copy), and the doi and title it recorded, whatever production's papers.tsv says by then;
    main's rows otherwise."""
    f = W.eval_paths(ev)['records'] / f'a6_inputs_{label}.json'
    out = dict(st)
    for p, r in ((json.loads(f.read_text()).get('papers') or {}) if f.exists() else {}).items():
        row = {'doi': '', 'title': '', **(st.get(p) or {})}
        row['text_source'] = f"{r.get('route')}:{r['original']}" if r.get('original') else str(r.get('route') or '')
        out[p] = {**row, **{k: r[k] for k in ('doi', 'title') if k in r}}
    return out


def cmd_a6_papers(ev, label, pmids, lanes=3):
    """catlog-copy laid down for a set read after the W1 rounds (LATER_LABELS): each paper's text, supplement and original
    cloned in (texts/, papers/: read-only, never changed silently), papers.tsv with these papers only (status reading),
    empty catalog files and claim records (lay_down), and records/orders/A6-LABEL.txt and A6-LABEL.args.json in the order
    given, lanes 3 (the pilot's: the account is shared with the batch loop). Records: records/a6_inputs_LABEL.json.
    Refused while catlog-copy holds a run, once the label was kept, or when its order holds another paper list. The locked
    set's files come from the judges' folders (locked_inputs: the first K of the draw, each with both input records); the
    hard set's (laid down 9 November) from the main folder, refused when a paper's text, original or supplement there is
    not what the plain read's or the judges' folders were given (records/hard_inputs.json, judge_inputs.json)."""
    P = W.eval_paths(ev)
    if label not in LATER_LABELS:
        sys.exit(f'a6-papers LABEL: one of {LATER_LABELS}')
    if not pmids or len(set(pmids)) != len(pmids):
        sys.exit('a6-papers LABEL PMID ...: each paper once')
    if a6_has_run_data(ev):
        sys.exit('catlog-copy holds a run: reset-a6 first')
    if (P['runs'] / f'A6-{label}').exists():
        sys.exit(f'A6-{label} was kept already: each set is laid down once')
    pin = W.a6_pin_problems(ev)  # laid down on the frozen copy only (the stamp check would refuse its rows after the read)
    if pin:
        sys.exit(f'{"; ".join(pin)}: a set after the W1 rounds is laid down on the frozen copy only; nothing laid down')
    args_file, order_file = P['orders'] / f'A6-{label}.args.json', P['orders'] / f'A6-{label}.txt'
    if args_file.exists() and [str(x) for x in json.loads(args_file.read_text())['pmids']] != pmids:
        sys.exit(f'{args_file} holds another paper list: an order is written once')
    st = {r['pmid']: r for r in W.read_tsv(M / 'papers.tsv')}
    if label == 'locked':
        recs, rows = locked_inputs(ev, pmids, st, W.input_records(ev))
        lay_down(ev, pmids, rows)
        write_a6_order(ev, label, pmids, lanes, recs)
        return
    recorded, differ = W.input_records(ev), []
    for p in pmids:  # the copy gets what the plain read's and the judges' folders were given, or nothing is laid down
        row = st.get(p)
        t, sp = M / 'texts' / f'{p}.txt', M / 'texts' / f'{p}.supp.txt'
        orig = original_of(row)[1] if row else None
        if not row or not t.exists() or (orig and not orig.exists()):
            continue  # said below
        now = (W.sha256(t), W.sha256(orig) if orig else None, W.sha256(sp) if sp.exists() else None)
        for name, rs in recorded.items():
            keys = [k for k, x, y in zip(W.INPUT_KEYS, W.input_hashes(rs.get(p)), now) if x != y] if p in rs else []
            if keys:
                differ.append(f'{p} ({name}: {", ".join(keys)})')
    if differ:
        sys.exit(f'{len(differ)} papers\' text, original or supplement in the main folder differ from what the plain read\'s '
                 f'or the judges\' folders hold (records/hard_inputs.json, judge_inputs.json): {differ[:10]}; nothing laid down')
    recs = {}
    for p in pmids:
        row = st.get(p)
        if not row:
            sys.exit(f'{p} is not in the main papers.tsv')
        t, sp = M / 'texts' / f'{p}.txt', M / 'texts' / f'{p}.supp.txt'
        route, orig = original_of(row)
        if not t.exists():
            sys.exit(f'{p}: no texts/{p}.txt')
        if orig and not orig.exists():
            sys.exit(f'{p}: its original is missing ({row["text_source"][:120]})')
        recs[p] = {'route': route, 'text_sha256': clone(t, P['a6'] / 'texts' / f'{p}.txt'), 'status_main': row['status']}
        if orig:
            a6o = P['a6'] / 'papers' / a6_original_name(p, orig)
            recs[p].update({'original': str(orig), 'a6_original': str(a6o), 'original_sha256': clone(orig, a6o)})
        else:  # the text came from an API with no file kept (production read it from the text alone)
            recs[p].update({'original': None, 'note': f'text only: no original on disk ({row["text_source"][:80]})'})
        if sp.exists():
            recs[p]['supp_sha256'] = clone(sp, P['a6'] / 'texts' / f'{p}.supp.txt')
    lay_down(ev, pmids, st)
    write_a6_order(ev, label, pmids, lanes, recs)


def write_a6_order(ev, label, pmids, lanes, recs):
    """records/orders/A6-LABEL.args.json and A6-LABEL.txt, and the lay-down's record records/a6_inputs_LABEL.json."""
    P = W.eval_paths(ev)
    args_file, order_file = P['orders'] / f'A6-{label}.args.json', P['orders'] / f'A6-{label}.txt'
    P['orders'].mkdir(parents=True, exist_ok=True)
    W.write_json(args_file, {'pmids': pmids, 'lanes': lanes, 'root': str(P['a6'])})
    order_file.write_text(''.join(p + '\n' for p in pmids))
    W.write_json(P['records'] / f'a6_inputs_{label}.json', {'time': W.now(), 'a6_head': sh('git', '-C', P['a6'], 'rev-parse', 'HEAD'),
                                                          'papers': recs})
    print(f'catlog-copy laid down for A6-{label}: {len(pmids)} papers (status reading), lanes {lanes}; '
          f'{args_file.name} and {order_file.name} written')


def cmd_claim(ev, pmids):
    P = W.eval_paths(ev)
    code = ('import sys, shutil, time; sys.path.insert(0, "."); import catlog\n'
            '(catlog.WORK / "old").mkdir(exist_ok=True)\n'
            'for p in sys.argv[1:]:\n'
            '    for f in catlog.WORK.glob(f"{p}.*.json"):\n'
            '        shutil.move(str(f), str(catlog.WORK / "old" / f"{f.stem}.{int(time.time())}.json"))\n'
            '    with catlog.Queue() as q:\n'
            '        if p not in q.rows: sys.exit(f"{p} is not in papers.tsv")\n'
            '        q.set(p, status="reading", note="")\n'
            '    catlog.claim_prompts(p)\n'
            '    catlog.log(p, "reread", "interrupted batch")\n')  # production's own words: no evaluation word in log.tsv
    sh(sys.executable, '-B', '-c', code, *pmids, cwd=P['a6'])
    print(f'claimed again in catlog-copy: {" ".join(pmids)}')


def branch_moved(m, branch):
    """check's problem when the kit branch has moved past the manifest's commit. After a freeze (the manifest's freeze
    record: the sets a6-papers lays down) the step that makes catlog-copy and the manifest follow it is freeze; setup
    --move-a6 is W1's (it would check W1's inputs and lay W1's papers down again)."""
    how = 'run w1_setup.py freeze' if m.get('freeze') else 'run setup --move-a6'
    return (f'the branch is at {branch[:12]}, the manifest names {m["commit12"]}: {how} so catlog-copy and the manifest '
            'follow the kit commit')


def cmd_check(ev):
    P = W.eval_paths(ev)
    m = json.loads(P['manifest'].read_text())
    problems = []
    head = sh('git', '-C', P['a6'], 'rev-parse', 'HEAD', check=False)
    a6m = m.get('a6') or {}
    if head != a6m.get('head'):
        problems.append(f'catlog-copy at {head[:12]}, the manifest\'s snapshot {str(a6m.get("head"))[:12]}')
    branch = sh('git', '-C', W.REPO, 'rev-parse', 'HEAD', check=False)
    if branch != m['commit']:
        problems.append(branch_moved(m, branch))
    if m.get('freeze'):  # the sets after the W1 rounds: the copy and the manifest on the frozen tag's snapshot
        problems += W.a6_pin_problems(ev)
    dirty = sh('git', '--no-optional-locks', '-C', P['a6'], 'status', '--porcelain', '--untracked-files=no', check=False)
    if dirty:
        problems.append(f'catlog-copy files differ from its commit: {dirty}')
    sources = {r['pmid']: r['text_source'].partition(':')[2] for r in W.read_tsv(P['a6'] / 'papers.tsv')} \
        if (P['a6'] / 'papers.tsv').exists() else {}
    for p, rec in m['inputs'].items():
        f = P['plain'] / p / 'paper.txt'
        if not f.exists() or W.sha256(f) != rec['plain_text_sha256']:
            problems.append(f'{p}: papers/{p}/paper.txt changed')
        if W.sha256(P['plain'] / p / rec['source_name']) != rec['original_sha256']:
            problems.append(f'{p}: papers/{p} source changed')
        if W.sha256(P['a6'] / 'texts' / f'{p}.txt') != rec['text_sha256']:
            problems.append(f'{p}: catlog-copy text changed')
        a6o = Path(rec.get('a6_original') or '')
        if not a6o.is_file() or W.sha256(a6o) != rec['original_sha256']:
            problems.append(f'{p}: catlog-copy original missing or changed ({a6o})')
        if p in sources and sources.get(p) != str(a6o):  # (another set laid down by a6-papers: W1's are not listed)
            problems.append(f'{p}: catlog-copy/papers.tsv names {sources.get(p)}, not its own original')
    shown, notes = shown_texts(ev, m)
    for where, text in shown:
        hits = W.eval_word_hits(text)
        if hits:
            problems.append(f'evaluation words {hits} in what a session is shown: {where}')
    for check in (a6_shown_problems(ev, m), a6_git_problems(P['a6'], m), a6_read_problems(ev, m)):
        problems += check[0]
        notes += check[1]
    for name, k in m['keys'].items():
        if name != 'people_values' and W.sha256(P['keys'] / h2h.GOLD_NAMES[name]) != k['sha256']:
            problems.append(f'keys/{name} changed')
    if W.sha256(P['keys'] / 'people_values.tsv') != m['keys']['people_values']['sha256']:
        problems.append('keys/people_values.tsv changed')
    folders = [P['plain'] / p for p in m['inputs']] + [P['adj'] / p for p in m['inputs'] if (P['adj'] / p).exists()]
    for d in folders:  # only the inputs, no instruction file above, read-only unless set up with --no-seal
        problems += W.folder_problems(d)
        if m.get('input_folders_sealed') and os.access(d, os.W_OK):
            problems.append(f'{d} is writable (setup seals the input folders)')
    du = sh('du', '-sk', ev, check=False).split()[0]
    print(json.dumps({'problems': problems, 'notes': notes, 'a6_head': head[:12],
                      'a6_snapshot_of': str(((a6m.get('snapshot') or {}).get('branch_commit')))[:12],
                      'a6_git': (a6m.get('snapshot') or {}).get('repository') or (a6m.get('snapshot') or {}).get('worktree'),
                      'papers': len(m['inputs']),
                      'shown_texts_checked': len(shown), 'eval_du_mb_logical': round(int(du) / 1024),
                      'free_gb': round(W.disk_free_gb(ev), 1)}, indent=1))
    return not problems


def a6_shown_problems(ev, m):
    """What A6's sessions see beyond shown_texts (review of the dry-run fixes): the names in catlog-copy's root (hidden
    ones too: the dry run's launch session listed it and read .w1_run_started), work/ and papers/; lines the branch adds
    to files catlog-copy holds (code comments and tests: an agent may open or grep them); the git-context and memory
    switches in A6's environment; and the instruction files Claude Code loads into every A6 session against the setup
    baseline, which holds no memory index (A6 runs with memory off since 2026-11-01). What git shows there is
    a6_git_problems, every file an agent can read a6_read_problems. Returns (problems, notes)."""
    P = W.eval_paths(ev)
    a6 = P['a6']
    problems, notes = [], []
    names = [x.name for x in a6.iterdir()] if a6.exists() else []
    names += [f'work/{x.name}' for x in (a6 / 'work').iterdir()] if (a6 / 'work').exists() else []
    names += [f'papers/{x.name}' for x in (a6 / 'papers').iterdir()] if (a6 / 'papers').exists() else []
    bad = [n for n in names if W.eval_word_hits('/' + n)]
    if bad:
        problems.append(f'evaluation words in catlog-copy names: {bad[:5]}')
    # the branch's own lines: against the main commit it last merged (freeze, 2026-11-09), else where it branched
    base = (m.get('freeze') or {}).get('main_merged') or (m.get('branched_from') or {}).get('commit')
    if base:
        paths = [x.lstrip('/') for x in A6_SPARSE if not x.startswith('!')]
        diff = sh('git', '-C', W.REPO, 'diff', '-U0', base, m['commit'], '--', *paths, ':(exclude)tools/w1', check=False)
        f, added = None, collections.defaultdict(set)
        for line in diff.splitlines():
            if line.startswith('+++ '):
                f = line[6:]
            elif line.startswith('+') and not line.startswith('+++'):
                for h in W.eval_word_hits(line[1:]):
                    added[f].add(h)
        for f, h in sorted(added.items()):
            problems.append(f'catlog-copy/{f}: lines this branch adds have evaluation words {sorted(h)}')
    if any(RA6.ENV_SET.get(k) != v for k, v in W.NO_GIT_CONTEXT_ENV.items()):
        problems.append('run_a6.ENV_SET lacks CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1 (the gitStatus block shows the kit\'s commits)')
    if any(RA6.ENV_SET.get(k) != v for k, v in W.NO_MEMORY_ENV.items()):
        problems.append('run_a6.ENV_SET lacks CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 (main\'s memory index names the paper\'s '
                        'plans; A6 runs with memory off)')
    baseline = m.get('instructions_baseline') or {}
    extra = sorted(set(baseline) - set(W.instruction_files_a6(ev)))
    if extra:
        problems.append(f'the manifest\'s instruction baseline holds {extra}: A6 runs with memory off (run setup)')
    for kind, now in W.instruction_baseline(ev).items():
        b = baseline.get(kind)
        if not b:
            notes.append(f'instruction file {kind} has no setup baseline (run setup)')
            continue
        new = sorted(set(now['eval_words']) - set(b.get('eval_words') or []))
        if new:
            problems.append(f'instruction file {kind} ({now["path"]}) has new evaluation words {new}: every A6 agent '
                            'is shown it')
        elif now['sha256'] != b.get('sha256'):
            notes.append(f'instruction file {kind} ({now["path"]}) changed since setup (no new evaluation word)')
    return problems, notes


HEX = re.compile(r'(?<![0-9A-Za-z])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}(?![0-9A-Za-z])')
# The git commands an agent in catlog-copy might run to look around (independent check, 2026-11-01: as a worktree of
# main, git log --all, git branch -a, git worktree list and git for-each-ref there showed the w1-eval branch, the kit's
# worktree and the kit's commit messages).
GIT_VIEWS = (('git log', ('log',)), ('git log --all', ('log', '--all', '--oneline', '--decorate')),
             ('git status', ('status',)), ('git branch -a', ('branch', '-a', '-v')),
             ('git worktree list', ('worktree', 'list')), ('git reflog', ('reflog',)), ('git stash list', ('stash', 'list')),
             ('git tag', ('tag',)), ('git remote -v', ('remote', '-v')), ('git for-each-ref', ('for-each-ref',)),
             ('git config --local', ('config', '--local', '--list')))


def git_views(a6):
    """{command: output} of GIT_VIEWS run in catlog-copy (read only: no optional locks)."""
    return {name: sh('git', '--no-optional-locks', '-C', a6, *args, check=False) for name, args in GIT_VIEWS}


def git_dir_texts(a6):
    """The files of catlog-copy's own git folder an agent could open as text (HEAD, config, refs, logs, hooks, info,
    description, ...; not objects/ or the binary index): [(where, text)]."""
    g = Path(a6) / '.git'
    if not g.is_dir():
        return []
    return [(f'catlog-copy/.git/{p.relative_to(g).as_posix()}', p.read_bytes().decode('utf-8', 'replace'))
            for p in sorted(g.rglob('*'))
            if p.is_file() and p.relative_to(g).parts[0] != 'objects' and p.relative_to(g).as_posix() != 'index']


def a6_git_problems(a6, m, repo=M):
    """What git shows an agent in catlog-copy (the owner's decision, 2026-11-01, and the independent check after it):
    catlog-copy is its own repository (not a worktree of main, whose refs git log --all, git branch -a and git worktree
    list would show); HEAD is the manifest's snapshot, an orphan commit (no parent) with the subject SNAPSHOT_SUBJECT,
    its branch commit's author and committer and the recorded tree, holding exactly the kit commit's files that
    A6_SPARSE selects; `git log` and `git log --all` list that one commit; no ref of any kind; `git worktree list` names
    catlog-copy only; no output of GIT_VIEWS names another commit or has an evaluation word, nor do the .git file, the
    git folder's name or its text files; no sparse checkout. Returns (problems, notes)."""
    a6 = Path(a6)
    problems, notes = [], []
    snap = (m.get('a6') or {}).get('snapshot') or {}
    if not snap.get('commit'):
        return ['the manifest names no snapshot for catlog-copy: run setup --move-a6'], notes
    head = sh('git', '-C', a6, 'rev-parse', 'HEAD', check=False)
    if head != snap['commit']:
        problems.append(f'catlog-copy at {head[:12]}, the snapshot {snap["commit"][:12]}')
    if not own_repository(a6):
        common = sh('git', '-C', a6, 'rev-parse', '--path-format=absolute', '--git-common-dir', check=False)
        problems.append(f'catlog-copy is not its own repository (its git is {common}): git log --all, git branch -a and '
                        'git worktree list there show that repository\'s branches and commits: run setup --move-a6')
    obj = sh('git', '-C', a6, 'cat-file', 'commit', 'HEAD', check=False)
    msg = obj.partition('\n\n')[2]
    if obj + '\n' != snapshot_object(snap['tree'], snapshot_ident(snap['branch_commit'], repo)):
        problems.append(f'catlog-copy HEAD is not the snapshot of {snap["branch_commit"][:12]} (no parent, its tree, '
                        f'author, committer and subject {SNAPSHOT_SUBJECT!r}): {obj[:300]!r}')
    files = sh('git', '-C', a6, 'ls-tree', '-r', '-z', '--full-tree', head, check=False).split('\0')
    files = [tuple(r.split('\t', 1)[0].split()) + (r.split('\t', 1)[1],) for r in files if r]
    if files != snapshot_entries(m['commit'], repo):
        problems.append(f'catlog-copy\'s commit does not hold exactly the kit commit {m["commit12"]}\'s files that '
                        f'A6_SPARSE selects ({len(files)} files): run setup --move-a6')
    views = git_views(a6)
    listed = sh('git', '-C', a6, 'log', '--format=%H', check=False).split()
    if listed != [head]:
        problems.append(f'git log in catlog-copy lists {len(listed)} commits, not the snapshot alone')
    listed_all = sh('git', '-C', a6, 'log', '--all', '--format=%H', check=False).split()
    if listed_all != [head]:
        problems.append(f'git log --all in catlog-copy lists {len(listed_all)} commits, not the snapshot alone')
    if views['git for-each-ref']:
        problems.append(f'catlog-copy\'s git has refs (branches, tags or others): {views["git for-each-ref"].splitlines()[:3]}')
    trees = [x[len('worktree '):] for x in sh('git', '-C', a6, 'worktree', 'list', '--porcelain', check=False).splitlines()
             if x.startswith('worktree ')]
    if [Path(x).resolve() for x in trees] != [a6.resolve()]:
        problems.append(f'git worktree list in catlog-copy names other folders: {trees[:4]}')
    other = sorted({h for v in views.values() for h in HEX.findall(v) if not head.startswith(h)})
    if other:
        problems.append(f'git in catlog-copy names another commit: {other[:3]}')
    gitdir = Path(sh('git', '-C', a6, 'rev-parse', '--absolute-git-dir', check=False))
    gitfile = (a6 / '.git').read_text() if (a6 / '.git').is_file() else ''
    texts = [(f'{name} in catlog-copy', out) for name, out in views.items()]
    texts += [('its .git file', gitfile), ('its git folder\'s name', '/' + gitdir.name)] + git_dir_texts(a6)
    for where, text in texts:
        hits = W.eval_word_hits(text)
        if hits:
            problems.append(f'evaluation words {hits} in {where}')
    if sh('git', '-C', a6, 'config', '--get', 'core.sparseCheckout', check=False) == 'true':
        problems.append('catlog-copy is a sparse checkout (the snapshot holds its files: run setup --move-a6)')
    notes.append(f'catlog-copy: {"own repository" if own_repository(a6) else "not its own repository"} ({gitdir}), '
                 f'git log --all lists {len(listed_all)} commit ({head[:12]} {msg.strip()!r}, the snapshot of '
                 f'{snap["branch_commit"][:12]}), git status: {(views["git status"].splitlines() or [""])[0]}, '
                 f'git branch -a: {views["git branch -a"]!r}, refs: {len(views["git for-each-ref"].splitlines())}')
    return problems, notes


KIT_PAPER_COLS = ('pmid', 'status', 'text_source', 'kept', 'rejected', 'note', 'updated')


def a6_read_problems(ev, m, repo=M):
    """Every file an A6 agent can read, searched for the evaluation words (the owner's decision, 2026-11-01):
      - every file of catlog-copy's commit (the harness: CLAUDE.md, the prompts, .claude/settings.json, the workflows
        and agent file, catlog.py, tools/, the two sources files), as it is on disk, against the same file in main at
        branching (MANIFEST branched_from): a word main's own file does not hold is a problem; production's own words
        are counted in the notes;
      - the files the kit writes there (.claude/settings.local.json, the run marker, the claim records in work/, the
        empty catalog files, the kit's columns of papers.tsv): any word is a problem;
      - the owner's ~/.claude/CLAUDE.md and ~/.claude/settings.json, which every session loads: a word is a note (the
        instruction baseline makes a new word in CLAUDE.md a problem);
      - the paper texts in texts/, papers.tsv's titles and DOIs: production's own (texts sha256-checked above), noted.
    The originals in papers/ are production's bytes (sha256-checked above); catlog-copy's git (its folder's text files
    and what git commands print there) is a6_git_problems'; the launch lines are in shown_texts. Returns (problems,
    notes)."""
    P = W.eval_paths(ev)
    a6 = P['a6']
    base = (m.get('branched_from') or {}).get('commit')
    problems, notes = [], []
    head = sh('git', '-C', a6, 'rev-parse', 'HEAD', check=False)
    tree = [r for r in sh('git', '-C', a6, 'ls-tree', '-r', '-z', '--name-only', '--full-tree', head,
                          check=False).split('\0') if r]
    prod = collections.Counter()
    for path in tree:
        f = a6 / path
        if not f.is_file():
            continue
        hits = set(W.eval_word_hits(f.read_bytes().decode('utf-8', 'replace')))
        if not hits:
            continue
        r = subprocess.run(['git', '-C', str(repo), 'show', f'{base}:{path}'], capture_output=True,
                           env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')}) if base else None
        main_hits = set(W.eval_word_hits(r.stdout.decode('utf-8', 'replace'))) if r is not None and r.returncode == 0 else set()
        if hits - main_hits:
            problems.append(f'catlog-copy/{path} has evaluation words {sorted(hits - main_hits)} that main\'s file at '
                            'branching does not have')
        for h in hits & main_hits:
            prod[h] += 1
    notes.append(f'catlog-copy\'s {len(tree)} files of its commit searched against main\'s files at branching'
                 + (f'; production\'s own words there, by file count: {dict(sorted(prod.items()))}' if prod else ''))
    kit = [a6 / '.claude' / 'settings.local.json', a6 / W.RUN_MARK, a6 / W.OLD_RUN_MARK]
    kit += [a6 / f for f in ('catalog.jsonl', 'rejected.jsonl', 'bounds.jsonl', 'log.tsv')]
    kit += sorted((a6 / 'work').glob('*.prompts.json')) if (a6 / 'work').exists() else []
    texts = [(str(f.relative_to(a6)), f.read_text(errors='replace')) for f in kit if f.is_file()]
    titles = collections.Counter()
    if (a6 / 'papers.tsv').exists():
        rows = W.read_tsv(a6 / 'papers.tsv')
        texts.append(('papers.tsv (the kit\'s columns)', '\n'.join(' '.join(str(r.get(c, '')) for c in KIT_PAPER_COLS) for r in rows)))
        for r in rows:
            for h in W.eval_word_hits(f"{r.get('title', '')} {r.get('doi', '')}"):
                titles[h] += 1
    for where, text in texts:
        hits = W.eval_word_hits(text)
        if hits:
            problems.append(f'evaluation words {hits} in catlog-copy/{where} (a file the kit writes)')
    notes.append(f'{len(texts)} files the kit writes in catlog-copy searched (settings.local.json, run marker, catalog '
                 'files, claim records, papers.tsv\'s kit columns)' + (f'; papers.tsv titles and DOIs (production\'s): '
                                                                       f'{dict(sorted(titles.items()))}' if titles else ''))
    for f in (Path.home() / '.claude' / 'CLAUDE.md', Path.home() / '.claude' / 'settings.json'):
        hits = W.eval_word_hits(f.read_text(errors='replace')) if f.exists() else []
        if hits:
            notes.append(f'{f} (the owner\'s, loaded by every session) has words of the list: {hits}')
    paper_texts = sorted((a6 / 'texts').glob('*.txt')) if (a6 / 'texts').exists() else []
    with_words = collections.Counter()
    for f in paper_texts:
        for h in W.eval_word_hits(f.read_text(errors='replace')):
            with_words[h] += 1
    notes.append(f'{len(paper_texts)} paper texts in catlog-copy/texts (production\'s bytes) use words of the list as '
                 f'the papers do, by text count: {dict(with_words.most_common(8))}')
    return problems, notes


def copy_texts(a6):
    """What the kit writes into catlog-copy's own files, which its sessions can read: log.tsv, and the status and note
    columns of papers.tsv (the titles are the papers' own words). The claim once logged an evaluation word there
    (2026-11-02)."""
    out = []
    if (a6 / 'log.tsv').exists():
        out.append(('catlog-copy log.tsv', (a6 / 'log.tsv').read_text(errors='replace')))
    if (a6 / 'papers.tsv').exists():
        out.append(('catlog-copy papers.tsv status and note',
                    '\n'.join(f"{r.get('status', '')} {r.get('note', '')}" for r in W.read_tsv(a6 / 'papers.tsv'))))
    return out


def shown_texts(ev, m):
    """Everything a session is shown that the kit decides, as (where, text): every session folder, every out/ folder,
    the validator's path and its text, catlog-copy, every filled prompt kind (for the first paper of the eval), every A6
    launch line, and the names a session would see by listing a folder its prompt names. Also (notes) the names at the
    top of the eval tree with an evaluation word: only a session that lists the root sees them, and the audit breaks
    that."""
    P = W.eval_paths(ev)
    papers = sorted(m['inputs'], key=W.pmid_key)
    out = [(f'folder {d}', str(d)) for p in papers for d in (P['plain'] / p, P['adj'] / p)]
    out += [(f'out folder {d}', str(d)) for d in W.out_folders(ev)]
    out += [('validator path', str(P['validator'])), ('catlog-copy', str(P['a6']))]
    out += copy_texts(P['a6'])
    if P['validator'].exists():
        out.append(('validator text', P['validator'].read_text()))
    p = next((x for x in papers if (P['adj'] / x).exists()), papers[0])
    for arm, run, part in (('A0', 1, None), ('A2', 1, 'readA'), ('A0', 'dry', None), ('A2', 'pilot', 'readB')):
        lab = W.part_label(arm, run, part)
        out.append((f'prompt {lab}', W.fill(W.prompt_text('A0.txt'), PMID=p, DIR=P['plain'] / p, RUN=W.code(lab),
                                            OUT=W.out_file(ev, arm, run, part, p), VALIDATE=P['validator'])))
    reads = {k: str(W.out_file(ev, 'A2', 1, part, p)) for k, part in (('READ_A', 'readA'), ('READ_B', 'readB'))}
    out.append(('prompt A2-r1-final', W.fill(W.prompt_text('A2_reconcile.txt'), PMID=p, DIR=P['plain'] / p,
                                             RUN=W.code(W.part_label('A2', 1, 'final')),
                                             OUT=W.out_file(ev, 'A2', 1, 'final', p), VALIDATE=P['validator'], **reads)))
    for which in ('rounds', 'dry'):
        Q = W.eval_paths(ev, which)
        for j in W.JUDGES:
            claims = (Q['claims3'] if j == 'j3' else Q['claims']) / f'{p}.c01.json'
            out.append((f'prompt judge {j} {which}', W.fill(W.prompt_text('adjudicate.txt'), PMID=p, DIR=P['adj'] / p,
                                                             CLAIMS=claims, OUT=Q['verdicts'][j] / f'{p}.c01.json',
                                                             RUN=f"{W.code(W.judge_label(j))}-c01")))
    for f in sorted(P['orders'].glob('A6-*.args.json')):
        out.append((f'A6 launch line {f.name}', RA6.launch_line(json.loads(f.read_text()))))
    for d in (P['plain'], P['out']):  # what `ls` of a folder a prompt names shows
        if d.exists():
            out.append((f'names in {d}', ' '.join('/' + x.name for x in d.iterdir())))
    notes = [f'top-level name {x.name} has evaluation words {W.eval_word_hits("/" + x.name)} (seen only by listing the '
             'root, which the audit breaks)' for x in sorted(Path(ev).iterdir()) if W.eval_word_hits('/' + x.name)]
    return out, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('setup', 'reset-a6', 'claim', 'check', 'keep-dry', 'plain-inputs', 'judge-inputs',
                                    'freeze', 'a6-papers'))
    ap.add_argument('args', nargs='*')
    ap.add_argument('--people-rounds', default='1', help='rounds whose orders include the people papers (default 1)')
    ap.add_argument('--move-a6', action='store_true', help='setup: move catlog-copy to the snapshot of the branch commit (a '
                                                           'reviewed kit change), or make it again as a worktree named '
                                                           'catlog-copy at that snapshot, keeping its data files')
    ap.add_argument('--no-seal', action='store_true', help='setup: leave papers/<PMID>/ and checks/<PMID>/ writable (only '
                                                           'if the dry run shows Claude Code must write in its folder)')
    ap.add_argument('--redo', action='store_true', help='reset-a6: keep the redo of run_a6.py LABEL --redo')
    ap.add_argument('--force', action='store_true', help='freeze, setup --move-a6: move catlog-copy off the frozen tag\'s '
                                                         'snapshot although a set after the W1 rounds is laid down '
                                                         '(records/a6_inputs_<label>.json, orders/A6-locked.args.json)')
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    ev = Path(a.eval)
    if a.cmd == 'setup':
        cmd_setup(ev, [int(x) for x in a.people_rounds.split(',') if x.strip()], a.move_a6, a.no_seal, a.force)
    elif a.cmd == 'reset-a6':
        if len(a.args) != 1:
            sys.exit('reset-a6 LABEL [--redo]')
        cmd_reset_a6(ev, a.args[0], a.redo)
    elif a.cmd == 'claim':
        if not a.args:
            sys.exit('claim PMID ...')
        cmd_claim(ev, a.args)
    elif a.cmd == 'plain-inputs':
        if not a.args:
            sys.exit('plain-inputs PMID ...')
        cmd_plain_inputs(ev, a.args)
    elif a.cmd == 'judge-inputs':
        if not a.args:
            sys.exit('judge-inputs PMID ...')
        cmd_judge_inputs(ev, a.args)
    elif a.cmd == 'freeze':
        cmd_freeze(ev, a.force)
    elif a.cmd == 'a6-papers':
        if len(a.args) < 2:
            sys.exit('a6-papers LABEL PMID ...')
        cmd_a6_papers(ev, a.args[0], a.args[1:])
    elif a.cmd == 'keep-dry':
        if len(a.args) != 1:
            sys.exit('keep-dry NAME (e.g. dry_run_2)')
        cmd_keep_dry(ev, a.args[0])
    else:
        sys.exit(0 if cmd_check(ev) else 1)


if __name__ == '__main__':
    main()
