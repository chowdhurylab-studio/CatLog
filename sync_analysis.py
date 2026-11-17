#!/usr/bin/env python3
"""Refresh analysis/, the paper's analysis code, from the authors' CatLog folder and the tests' kit folder, by rules.

    python3 -I -B sync_analysis.py --catlog CATLOG --kit KIT --names NAMES.tsv [--check]

CATLOG is the CatLog folder the authors work in, KIT the folder the two tests ran in (its code/ is a git worktree of the
CatLog repository on the tests' branch). Only the files in FILES come over. The kit's own code (code/tools/w1/, with the
texts its sessions followed) comes from the kit's commit KIT_COMMIT, by `git show`: the commit the locked test's report
ran at, which its results record; the kit's later commits and uncommitted edits are for a third test that was not run.
Every other file comes as it is on disk; each source's commit, and the copied files that differ from it, are printed.
Nothing is read in either folder beyond those files and git's view of them (no paper text, no data file, no .env).

Every change to a copied file is made here, by code, as sync_from_catlog.py makes its changes (its functions are used):
  1. RULES, in order. Each names its files and how often it must match (None: at least once); when it matches more or
     less often, the source has changed and the sync stops. They turn the authors' folders into placeholders that say
     what the folder is: <the CatLog folder>, <the kit folder>, <the first layout of the kit folder> (where the kit
     ran before it moved), <the earlier CatLog folder> (the earlier system), <the home folder> and <the scratch folder
     of the session that ran the sweep>; a session folder's name keeps its shape with the user's name as <user>; the
     made-up home folders of the kit's tests become /home/x and /home/s (and the session folders named after made-up
     homes -home-x- and -home-y); the ids of the authors' claude.ai connectors in the sessions' deny list become
     mcp__<connector id>; and a reviewer's pronoun becomes 'their'.
  2. E-mail addresses in Python string literals become the CATLOG_CONTACT_EMAIL setting (sync_from_catlog.contact).
  3. People's names become the neutral labels of NAMES.tsv (sync_from_catlog.read_names: private, never part of this
     repository; without it nothing is written).
The result is checked before anything is written: no name from NAMES.tsv (in any case, inside paths and identifiers
too), not the source owner's user name, no e-mail address (test addresses at example.* aside), no home-folder path,
nothing that looks like a key, no file over 1 MB, every .py compiles and every .sh passes `bash -n`. This repository's
own files here (OWN) are checked too, never changed. Then analysis/ is written: copied files that FILES no longer lists
are removed, analysis/README.md is never touched, and nothing is committed: read `git diff`, then commit.

The patterns below write a home folder as /[U]sers/, so that a search of this repository for machine paths finds none.
"""
import argparse, fnmatch, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sync_from_catlog as S  # noqa: E402  (its rule machinery, e-mail rewrite, names and checked patterns)

DEST = 'analysis/'
OWN = {'analysis/README.md', 'sync_analysis.py'}
MAX_BYTES = 1024 * 1024
CATLOG, KIT, KIT_AT = 'catlog', 'kit', 'kit-commit'  # KIT_AT: a path in the kit's code/ repository at KIT_COMMIT
# The kit's HEAD when the locked test's report ran (records/score_locked/results.json: curation.code.kit_head). The
# random test's report ran on 9 November at the branch's 70e5f04; its scorer score_randfull.py is the same in both.
KIT_COMMIT = 'f3e2a20e1290f68c6ee6677e1cf3ab0fd3d3d338'

W1 = '''build_people_list claude_session common_w1 h2h h2h_common h2h_s06 run_a6 run_adjudicate run_plain run_reconcile
scan_judges scan_reads score_locked score_rand score_randfull score_w1 test_w1 validate_plain w1_audit
w1_setup'''.split()
HARD = 'paper/evidence/hard_cases_20261102'
FIG4_EV = 'writing/figures/fig4/v2/evidence'

# (path here under analysis/, source folder, path in the source folder)
FILES = (
    # the tests: the kit's runners, judges, audits, scorers, shared code and tests, and the texts its sessions followed
    [(f'tests/{n}.py', KIT_AT, f'tools/w1/{n}.py') for n in W1]
    + [(f'tests/prompts/{p}.txt', KIT_AT, f'tools/w1/prompts/{p}.txt')
       for p in ('A0', 'A2_reconcile', 'adjudicate', 'adjudicate_full')]
    + [(f'tests/launch/{s}.sh', KIT, f'records/{s}.sh')
       for s in ('run_locked_reads', 'run_locked_copy4', 'run_locked_copy4b', 'run_randfull')]
    + [(f'tests/second_stage/{n}.py', CATLOG, f'paper/evidence/locked_test_20261109/stage2/{n}.py')
       for n in ('score_stage2', 'check_tasks', 'score_checked')]
    + [(f'tests/random_test/{n}.py', CATLOG, f'paper/evidence/random_papers_20261104/{n}.py')
       for n in ('select', 'r2_numbers')]
    + [(f'tests/known_traps/{n}.py', CATLOG, f'{HARD}/{n}.py')
       for n in ('score_hard', 'score_catlog', 'score_catlog_first', 'rescore_inputs', 'rescore2_inputs',
                 'rescore2_final', 'summary')]
    + [('tests/known_traps/today/score_today.py', CATLOG, f'{HARD}/today/score_today.py')]
    # the statistics and the numbers
    + [(f'statistics/accuracy_check/{n}.py', CATLOG, f'paper/evidence/accuracy_check_20261114/{n}.py')
       for n in ('stats', 'build_task_c', 'trace_code/match')]
    + [(f'statistics/europepmc_freeze/{n}.py', CATLOG, f'paper/evidence/europepmc_freeze_20261116/{n}.py')
       for n in ('build', 'reading_order')]
    + [('statistics/power_simulation/power.py', CATLOG, 'paper/evidence/random_test2_20261112/work/power.py'),
       ('statistics/human_review_freeze/freeze.py', CATLOG, 'paper/evidence/human_review_freeze_20261116/freeze.py'),
       ('statistics/reprint_sweep/build.py', CATLOG, 'paper/evidence/reprint_sweep_20261116/build.py'),
       ('statistics/numbers/numbers_build.py', CATLOG, 'paper/manuscript/numbers_build.py')]
    # the Methods' checks of the tests and the catalogue (17 Nov 2026): the locked test's registered sensitivity
    # analysis and the judging rules, the repeat launch, the cost, the fields code links to each record
    + [(f'statistics/{d}/{d}.py', CATLOG, f'paper/evidence/{d}_20261117/{d}.py')
       for d in ('sensitivity', 'stability', 'cost', 'linked_fields')]
    + [(f'statistics/numbers/rederive/{n}.py', CATLOG, f'paper/evidence/rederive_20261101/{n}.py')
       for n in ('rd_lib', 'rd_L13_multiplier', 'rd_L32_closure', 'rd_L46_brenda', 'rd_C56_origin')]
    # the figures and Extended Data
    + [('figures/lean.py', CATLOG, 'writing/figures/lean.py')]
    + [(f'figures/fig1/{n}.py', CATLOG, f'writing/fig1_v8/{n}.py') for n in ('build_fig1_v8', 'check_style_v8')]
    + [('figures/fig1/catalogue_counts.py', CATLOG, 'writing/fig1_v8/ref/catalogue_counts.py')]
    + [(f'figures/fig1/structure/{n}.py', CATLOG, f'writing/fig1_v8/structure/scripts/{n}.py')
       for n in ('render_asp', 'finish_png', 'ss_segments', 'inspect_model')]
    + [(f'figures/fig2/{n}.py', CATLOG, f'writing/figures/fig2/{n}.py')
       for n in ('build_fig2_options', 'fig2_data', 'people_data')]
    + [(f'figures/fig3/{n}.py', CATLOG, f'writing/figures/fig3/v2/{n}.py')
       for n in ('build_fig3_v2', 'extract_classes')]
    + [(f'figures/fig3/{n}.py', CATLOG, f'writing/figures/fig3/{n}.py')
       for n in ('extract', 'fig3_panels', 'factor_panel')]
    + [('figures/database_errors/factor_counts.py', CATLOG, 'paper/figures/database_errors/factor_counts.py')]
    + [('figures/fig4/build_fig4_v2.py', CATLOG, 'writing/figures/fig4/v2/final/build_fig4_v2.py')]
    + [(f'figures/fig4/evidence/{n}.py', CATLOG, f'{FIG4_EV}/{d}/{n}.py')
       for d, n in (('rules', 'count_rules'), ('learning', 'build_learning'), ('cases', 'extract_cases'),
                    ('traps', 'build_traps'))]
    + [('figures/fig4/evidence/build_taxonomy.py', CATLOG, 'paper/figures/method_overview/v5/build_taxonomy.py'),
       ('figures/fig4/evidence/r03_error_ledger.py', CATLOG, 'paper/evidence/rethink_20261101/r03_error_ledger.py')]
    + [(f'figures/extended_data/{d}/build.py', CATLOG, f'writing/figures/extended_data/{d}/build.py')
       for d in ('known_traps', 'rules_reach', 'enzyextract_runs')]
    # the Supplementary Tables
    # (not plain_words.tsv: the per-value plain cells agents wrote for Supplementary Tables 1-4 are agent output)
    + [(f'supplementary/{n}', CATLOG, f'writing/supplementary/{n}')
       for n in ('build_supplementary.py', 'guides.tsv', 's1_heads.tsv', 's1_codes.tsv')]
    + [(f'supplementary/agent_cases/{n}.py', CATLOG, f'paper/evidence/agent_highlights_20261028/case_data/{n}.py')
       for n in ('extract', 'build')]
)
FILES = [(DEST + here, root, there) for here, root, there in FILES]

# ---------- the rules ----------
HOME = S.HOME  # a macOS home folder, any user: /[U]sers/<name>
A = lambda p: DEST + p  # noqa: E731
TESTS = A('tests/test_w1.py')
CAT_FOLDER, KIT_FOLDER = '<the CatLog folder>', '<the kit folder>'
lit = S.lit
RULES = [
    # the one scratch folder of an agent session a script names (the reprint sweep's collect step read it once)
    S.Rule(A('statistics/reprint_sweep/build.py'),
           r"/private/tmp/claude-\d+/-[U]sers-[A-Za-z0-9_]+-Documents-catlog-v2/[0-9a-f-]{36}/scratchpad",
           '<the scratch folder of the session that ran the sweep>', 1, 'reprint sweep: the session scratch folder'),
    # the authors' folders, written as absolute paths
    S.Rule(A('*'), HOME + '/Documents/catlog-eval/w1', '<the first layout of the kit folder>', None,
           'the first layout'),
    S.Rule(A('*'), HOME + '/Documents/catlog-v2', CAT_FOLDER, None, 'the CatLog folder'),
    S.Rule(A('*'), HOME + '/Documents/kinetics-reading', KIT_FOLDER, None, 'the kit folder'),
    S.Rule(A('*'), HOME + '/Documents/realkcat', '<the earlier CatLog folder>', None, 'the earlier system'),
    # ... and from the home folder
    lit(A('tests/common_w1.py'), "Path.home() / 'Documents/kinetics-reading/", f"Path('{KIT_FOLDER}') / '", 1,
        'common_w1: the command-line tool in the kit folder'),
    lit(A('tests/random_test/r2_numbers.py'), "Path.home() / 'Documents/kinetics-reading'", f"Path('{KIT_FOLDER}')", 1,
        'r2_numbers: the kit folder'),
    lit([A('tests/second_stage/*.py'), A('tests/random_test/select.py'), A('tests/known_traps/*.py'),
         A('statistics/accuracy_check/stats.py')],
        "Path.home() / 'Documents' / 'kinetics-reading'", f"Path('{KIT_FOLDER}')", 8, 'the kit folder'),
    lit(A('tests/second_stage/score_stage2.py'), "Path.home() / 'Documents' / 'catlog-v2'", f"Path('{CAT_FOLDER}')", 1,
        'score_stage2: the CatLog folder'),
    lit([A('tests/random_test/r2_numbers.py'), A('tests/known_traps/score_hard.py'),
         A('tests/known_traps/today/score_today.py'), A('statistics/accuracy_check/stats.py'),
         A('figures/fig4/evidence/build_traps.py')],
        '~/Documents/kinetics-reading', KIT_FOLDER, 6, 'docstrings: the kit folder'),
    lit(A('tests/launch/*.sh'), '$HOME/Documents/kinetics-reading', KIT_FOLDER, 5, 'launch scripts: the kit folder'),
    S.Rule(A('figures/fig4/evidence/build_taxonomy.py'), HOME + r"/Documents/(?=')", '<the home folder>/Documents/', 2,
           'build_taxonomy: the home folder in its path display'),
    # a Claude Code session folder is named after its working directory: the user's name goes
    S.Rule(A('*'), r'-[U]sers-[A-Za-z0-9_]+-(?=Documents-)', '-Users-<user>-', None, 'session folders: the user'),
    # people: no pronoun that tells a reviewer's gender (as sync_from_catlog.py keeps them out of
    # tools/human_review.py); the pattern takes any three-letter word there, so that it does not spell the pronoun
    S.Rule(A('figures/fig1/build_fig1_v8.py'), r'(reviewer approved (?:them )?in )\w{3}( copy)',
           lambda m: m.group(1) + 'their' + m.group(2), 2, "Fig. 1: no reviewer's pronoun"),
    # the sessions' deny list names the authors' claude.ai connectors by their ids: those ids stay out
    S.Rule(A('tests/w1_setup.py'), r'mcp__[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
           'mcp__<connector id>', 5, "kit setup: the authors' connector ids"),
    # the kit's tests use made-up home folders; no /[U]sers/ path stays (as sync_from_catlog.py does for its tests)
    S.Rule(TESTS, r"/[U]sers/([sx])(?=[/'\s])", lambda m: '/home/' + m.group(1), 55, 'kit tests: made-up home folders'),
    S.Rule(TESTS, r'-[U]sers-([xy])(?=[-/])', lambda m: '-home-' + m.group(1), 9, 'kit tests: their session folders'),
]

# ---------- checks ----------
GENERIC = re.compile(r'/[U]sers/(?:\||\.\.\.)')  # a regex alternative of a path check, or '/[U]sers/...' in prose


def check(content, srcs, names, errors):
    users = set().union(*(S.owner_names(s) for s in srcs))
    strict = [(S.anywhere(n), label, allow) for n, label, allow in names]
    for path, text in sorted(content.items()):
        if len(text.encode('utf-8')) > MAX_BYTES:
            errors.append(f'{path}: over 1 MB')
        for u in users:
            if re.search(re.escape(u), path + '\n' + text, re.I):
                errors.append(f"{path}: holds the source owner's user name")
        for rx, label, allow in strict:
            hits = len(rx.findall(path)) + len(rx.findall(text))
            if hits != allow.get(path, 0):
                errors.append(f'{path}: holds a name from the names file {hits} time(s) (labelled {label!r})')
        for i, line in enumerate(text.splitlines(), 1):
            if any(not S.TEST_ADDRESS.search(e) for e in S.EMAIL_RX.findall(line)):
                errors.append(f'{path}:{i}: an e-mail address')
            if re.search(r'/[U]sers/', GENERIC.sub('', line)):
                errors.append(f'{path}:{i}: a home-folder path')
            for k in S.KEYS:
                if re.search(k, line):
                    errors.append(f'{path}:{i}: looks like a key ({k[:20]}...)')
        if path.endswith('.py'):
            try:
                compile(text, path, 'exec', dont_inherit=True)
            except SyntaxError as e:
                errors.append(f'{path}: does not compile ({e})')
        if path.endswith('.sh'):
            r = subprocess.run(['bash', '-n'], input=text, capture_output=True, text=True)
            if r.returncode:
                errors.append(f'{path}: bash -n fails ({r.stderr.strip()[:200]})')


# ---------- sources ----------

def git(folder, *args):
    r = subprocess.run(['git', '-C', str(folder), '--no-optional-locks', *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def read_source(roots, root, there):
    """(bytes, executable, None) of one source file, or (None, None, why not): a KIT_AT path from the kit's code/
    repository at KIT_COMMIT (its committed bytes and mode), any other from disk."""
    if root == KIT_AT:
        repo = roots[KIT] / 'code'
        entry = subprocess.run(['git', '-C', str(repo), '--no-optional-locks', 'ls-tree', KIT_COMMIT, '--', there],
                               capture_output=True, text=True).stdout.split()
        if len(entry) < 4 or entry[1] != 'blob':
            return None, None, f'kit code/{there}: not in its commit {KIT_COMMIT[:12]}'
        r = subprocess.run(['git', '-C', str(repo), '--no-optional-locks', 'show', f'{KIT_COMMIT}:{there}'],
                           capture_output=True)
        if r.returncode:
            return None, None, f'kit code/{there}: git show failed at {KIT_COMMIT[:12]}'
        return r.stdout, entry[0] == '100755', None
    f = roots[root] / there
    if not f.is_file():
        return None, None, f'{root}/{there}: not in the source'
    return f.read_bytes(), bool(f.stat().st_mode & 0o111), None


def provenance(root, rels):
    """One line: the git commit of the folder that holds these files, and which of them differ from it."""
    repo = (git(root / Path(rels[0]).parent, 'rev-parse', '--show-toplevel') or '').strip()
    if not repo:
        return 'not in git'
    head = (git(repo, 'rev-parse', '--short=12', 'HEAD') or '').strip()
    inside = [str((root / r).resolve().relative_to(Path(repo).resolve())) for r in rels
              if (root / r).resolve().is_relative_to(Path(repo).resolve())]
    dirty = git(repo, 'status', '--porcelain', '--', *inside) or ''
    changed = sorted(line[3:] for line in dirty.splitlines() if line.strip())
    return f'commit {head}; ' + (f'{len(changed)} differ from it: ' + ', '.join(changed) if changed
                                 else 'all as committed')


def managed(dest):
    out = set()
    if (dest / DEST).is_dir():
        for p in (dest / DEST).rglob('*'):
            rel = p.relative_to(dest).as_posix()
            if p.is_file() and rel not in OWN and not S.skipped(rel):
                out.add(rel)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--catlog', required=True, help="the authors' CatLog folder")
    ap.add_argument('--kit', required=True, help='the folder the two tests ran in')
    ap.add_argument('--names', default='', help='private file of name<TAB>label lines; never in this repository')
    ap.add_argument('--dest', default=str(HERE), help='where to write (default: the folder of this script)')
    ap.add_argument('--check', action='store_true', help='apply and check everything, write nothing')
    a = ap.parse_args()
    roots = {CATLOG: Path(a.catlog).resolve(), KIT: Path(a.kit).resolve()}
    dest = Path(a.dest).resolve()
    if not (roots[CATLOG] / 'catlog.py').is_file() or not (roots[KIT] / 'code' / 'tools' / 'w1').is_dir():
        sys.exit('--catlog needs catlog.py in it and --kit a code/tools/w1/ folder')
    if git(roots[KIT] / 'code', 'cat-file', '-e', f'{KIT_COMMIT}^{{commit}}') is None:
        sys.exit(f"--kit: its code/ repository lacks the commit {KIT_COMMIT[:12]} the locked test's report ran at")
    if not a.names or not Path(a.names).is_file():
        sys.exit('pass --names FILE (name<TAB>label per line; private, never in this repository): without it no name '
                 'is replaced, so nothing is written')
    if any(r == dest or dest in r.parents or r in dest.parents for r in roots.values()):
        sys.exit('the sources and the destination must be separate folders')
    names = S.read_names(a.names)
    errors, content, modes = [], {}, {}
    for here, root, there in FILES:
        data, executable, why = read_source(roots, root, there)
        if why:
            errors.append(why)
            continue
        try:
            content[here] = data.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'{root}/{there}: not UTF-8 text')
            continue
        modes[here] = executable
    for root in (CATLOG, KIT):
        rels = [there for _, r, there in FILES if r == root]
        for group in sorted({rel.split('/')[0] for rel in rels}):
            part = [rel for rel in rels if rel.split('/')[0] == group]
            print(f'source {root} ({len(part)} files under {group}/): {provenance(roots[root], part)}')
    print(f"source kit ({sum(r == KIT_AT for _, r, _ in FILES)} files under code/tools/w1/): commit {KIT_COMMIT[:12]}, "
          "the locked test's report's, read from git (the worktree on disk is not read)")
    for rule in RULES:
        n = 0
        for p in sorted(content):
            if any(fnmatch.fnmatchcase(p, f) for f in rule.files):
                content[p], k = rule.rx.subn(rule.repl, content[p])
                n += k
        if (n == 0) if rule.count is None else (n != rule.count):
            errors.append(f'rule "{rule.why}" matched {n} times, not {rule.count or "one or more"}: '
                          'the source changed; look at the rule')
    mails = 0
    for p in sorted(content):
        if p.endswith('.py'):
            content[p], k = S.contact(p, content[p], errors)
            mails += k
    labelled = {}
    for name, label, _ in names:
        rx = S.word(name)
        for p in sorted(content):
            content[p], k = rx.subn(lambda m, text=label: text, content[p])
            if k:
                labelled[label] = labelled.get(label, 0) + k
    own = {p: (dest / p).read_text(encoding='utf-8') for p in sorted(OWN) if (dest / p).is_file()}
    check({**content, **own}, list(roots.values()), names, errors)
    print(f'{len(content)} files; rules: {len(RULES)} applied; {mails} e-mail literals now use CATLOG_CONTACT_EMAIL; '
          'names: ' + (', '.join(f'{label} {k}' for label, k in sorted(labelled.items())) or 'none found'))
    print('checks: names, user name, e-mail, home paths, keys, sizes, compile, bash -n (own files too: '
          + ', '.join(sorted(own)) + ')')
    if errors:
        print(f'\n{len(errors)} problem(s); nothing written:', file=sys.stderr)
        for e in errors:
            print('  ' + e, file=sys.stderr)
        sys.exit(1)
    gone = sorted(managed(dest) - set(content))
    changed = sorted(p for p in content
                     if not (dest / p).is_file() or (dest / p).read_bytes() != content[p].encode('utf-8'))
    print(f'{len(changed)} files new or changed, {len(gone)} to remove'
          + (' (--check: nothing written)' if a.check else ''))
    for p in changed:
        print('  write ' + p)
    for p in gone:
        print('  remove ' + p)
    if a.check:
        return
    for p in changed:
        out = dest / p
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(content[p].encode('utf-8'))
    for p in content:
        (dest / p).chmod(0o755 if modes.get(p) else 0o644)
    for p in gone:
        (dest / p).unlink()
        for d in (dest / p).parents:
            if d == dest or any(d.iterdir()):
                break
            d.rmdir()
    print('done: read `git diff` in ' + str(dest) + ', then commit')


if __name__ == '__main__':
    main()
