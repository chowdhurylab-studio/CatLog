#!/usr/bin/env python3
"""Refresh this code-only copy of CatLog from the authors' CatLog folder, by fixed rules.

    python3 -I -B sync_from_catlog.py SOURCE --names NAMES.tsv [--ref REF | --working-tree] [--dest DIR] [--check]

SOURCE is the CatLog folder the authors work in (a git repository). Only the files listed in INCLUDE come over, as
committed in SOURCE at --ref (default HEAD), so a half-finished edit there never does; --working-tree takes them as
they are on disk instead. A file under a watched path (a top-level .py, config.json, tools/, prompts/, .claude/) that
is in neither INCLUDE nor EXCLUDE stops the sync: read it, then list it in one of the two.
Two kinds of files come from SOURCE's disk whatever --ref says, because SOURCE keeps them out of git: the workflows and
the tool in DISK (catalogue sweeps that ran from its work/ folder), and the prompt and task texts saved when rows were
stamped (work/prompts/; the reconstructed ones in sources/prompt_versions/ come from the commit). The saved texts go to
prompts/versions/ with a MANIFEST.tsv, so that every read_prompt, verify_prompt and task_prompt stamp resolves with
`catlog.py prompt HASH`.

Every change to a copied file is made here, by code:
  1. SCRUBS, in order. Each names its files and how often it must match; when it matches more or less often, the
     source has changed and the sync stops rather than apply a rule blindly.
  2. E-mail addresses in Python string literals become the CATLOG_CONTACT_EMAIL setting: the User-Agent contact and
     the email= / mailto= parameter of the NCBI, Crossref and OpenAlex requests, left out while the setting is empty.
  3. People's names become the neutral labels of NAMES.tsv ('name<TAB>label' per line, '#' starts a comment; an
     optional third field 'path=N,...' says how often a copied file may hold the name as code, e.g. an identifier).
     That file is private and never part of this repository; without it nothing is written.
The result is checked before anything is written: no e-mail address (test addresses at example.* aside), no
home-folder path (the local-path detectors aside), not the source owner's user name, no name from NAMES.tsv (in a
copied file in any case, inside paths and identifiers too, beyond its allowance), no reviewer in tools/human_review.py
that is not a label and no gendered pronoun there, no paper id from SOURCE's held-out lists (sources/holdout_*.txt),
no value of SOURCE's .env files (read here to compare, never shown), nothing that looks like a key, no file over 5 MB;
every .py compiles and every .json parses. When DEST is a git repository, the identity its next commit would carry
must be neutral (a GitHub noreply address or one at example.invalid, and no name from NAMES.tsv).
Then the files are written into DEST (default: this script's folder). Copied files the rules no longer include are
removed; this repository's own files (OWN) are never touched, and nothing is committed: read `git diff`, then commit.

The patterns below write a home folder as /[U]sers/, so that a search of this repository for machine paths finds none.
"""
import argparse, ast, fnmatch, getpass, hashlib, io, json, os, re, subprocess, sys, tokenize
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWN = {'README.md', 'LICENSE', 'requirements.txt', '.gitignore', 'sync_from_catlog.py', '.claude/settings.example.json',
       'demo/make_demo_paper.py', 'demo/run_demo.sh', 'demo/expected_output.txt'}
MANAGED = ('catlog.py', 'config.json', 'tools/', 'prompts/', '.claude/')  # what a sync may write or remove in DEST
MAX_BYTES = 5 * 1024 * 1024
HOME = r'/[U]sers/[^/\'"`\s]+'  # a macOS home folder, any user
VERSIONS = 'prompts/versions'  # the saved prompt and task texts, here

TOOLS = '''brenda_count brenda_overlap brenda_values censored_scan coverage db_values dbcheck dbcompare discover_europepmc
elsevier_to_text enrich export_site fetch human_review ids jats_to_text km_gain lane_agent nd_census nopmid
provenance_backfill publication_years recheck ref_sequences ref_structures release_tree reprint_pairs sabio_values
scale_sweep sequences site_release skid_values strenda_values structures test_blind_check test_dropped_relabel test_superseded_drop
test_provenance test_provenance_backfill test_publication_years uniprot_values units vmax_sweep'''.split()
INCLUDE = (['catlog.py', 'config.json']
           + [f'tools/{t}.py' for t in TOOLS]
           + [f'prompts/{p}.md' for p in ('audit_standard', 'dbcheck', 'read', 'scale', 'verify', 'vmax')]
           + [f'.claude/workflows/catlog-{w}.js' for w in ('audit', 'batch', 'chrome-lanes', 'dbcheck', 'nd-census',
                                                           'scale', 'vmax')]
           + ['.claude/agents/catlog-reader.md', '.claude/commands/audit.md', '.claude/commands/batch.md'])

# path here -> path in SOURCE, where git ignores it: the workflows and the tool of catalogue sweeps that ran from the
# work/ folder (the reprint sweep and its third opinions, whole-paper audit follow-ups, a column's unit, re-read
# copies). Once SOURCE commits one, move it to INCLUDE (the sync says so).
DISK = {
    '.claude/workflows/catlog-reprint-pairs.js': 'work/reprint_sweep/catlog-reprint-pairs.js',
    '.claude/workflows/catlog-reprint-third-opinion.js': 'work/reprint_sweep/catlog-reprint-third-opinion.js',
    '.claude/workflows/catlog-audit-followup.js': 'work/audit_followup_20261114/followup.js',
    '.claude/workflows/catlog-unitcheck.js': 'work/audit_followup_20261114/unitcheck.js',
    'tools/reread_copies.py': 'work/reread_copies/reread_copies.py',
}

EXCLUDE = {  # fnmatch pattern ('*' crosses '/') -> why it stays out
    'tools/reference/*': 'an old one-off filing script of the earlier system, with machine paths; nothing uses it',
    'tools/fetch_rounds.sh': "a shell loop around `catlog.py fetch` written for the authors' Mac and campus network",
    'tools/review_ui/*': "the reviewers' review page (it names a reviewer); `catlog.py review pack` stops without it",
    'tools/site_patches/*': 'notes for the website sessions',
    'tools/chrome_doctor.py': "the authors' macOS Chrome and memory helper (their Stop hook and lane_watch.py use it)",
    'tools/headless.py': "a headless-Chrome helper for the authors' site checks; nothing here uses it",
    'tools/lane_watch.py': "a watcher for the authors' download sessions (their /download runbook, not included)",
    'tools/text_check.py': "the website wording check; nothing here uses it",
    '.claude/commands/archive.md': "moves the authors' agent logs to their cluster archive",
    '.claude/commands/download.md': "the authors' download runbook: their browser, campus access and internal guides",
    '.claude/settings.json': "the authors' local permissions and hooks (.claude/settings.example.json is this copy's)",
    '.claude/settings.local.json': "the authors' local permissions",
    '.claude/launch.json': "the authors' local preview settings",
    '.claude/worktrees/*': 'local worktrees',
}


def watched(path):
    return (('/' not in path and path.endswith('.py')) or path == 'config.json'
            or path.startswith(('tools/', 'prompts/', '.claude/')))


def skipped(path):
    return '__pycache__/' in path or path.endswith(('.pyc', '.DS_Store'))


# ---------- the scrubs ----------

class Rule:
    """files: fnmatch patterns; find: a regex (or literal text); repl: the new text, or a function of the match;
    count: how often it must match over all its files (None: at least once)."""

    def __init__(self, files, find, repl, count=None, why='', literal=False):
        self.files = [files] if isinstance(files, str) else list(files)
        self.rx = re.compile(re.escape(find) if literal else find, re.M)
        self.repl = repl if callable(repl) else (lambda m, text=repl: text)
        self.count, self.why = count, why


def lit(files, find, repl, count=None, why=''):
    return Rule(files, find, repl, count, why, literal=True)


NO_ROOT = 'the CatLog folder (absolute path) used when args.root is not given; this copy sets none'
ROOT_ERROR = "pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file"


def js_root(name):
    """A workflow's folder constant: args.root, else CATLOG_ROOT (empty in this copy), else stop with a message."""
    return (f"const CATLOG_ROOT = ''  // {NO_ROOT}\n"
            f"const {name} = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\\/+$/, '')\n"
            f"if (!{name}.startsWith('/') || /[~$]/.test({name})) return {{ error: '{ROOT_ERROR}' }}")


ARGS_ROOT = ', "root": "<this folder, absolute path>"}`'
OLD_DIR = "Path(os.environ.get('REALKCAT_DIR') or ROOT / 'realkcat')"  # the earlier CatLog system (README: settings)
CAMPUS = "(os.environ.get('CATLOG_CAMPUS_IP_PREFIX') or '-')"  # unset: no address is on campus (README: settings)
FROM_WORK = ['.claude/workflows/catlog-reprint-pairs.js', '.claude/workflows/catlog-reprint-third-opinion.js',
             '.claude/workflows/catlog-audit-followup.js', '.claude/workflows/catlog-unitcheck.js']

ROLES = {  # tools/human_review.py: what a reviewer is or does, next to the labels -> neutral words
    'the reviewer often approved within 2 s': 'approvals are often quick',
    'a grad student': 'an experienced reviewer',
    'undergraduates working from home': 'reviewers working from home',
    'two undergraduates': 'two reviewers',
    'a high-school reviewer': 'a beginner',
    'two high-school reviewers and one teacher': 'three new reviewers',
    'three ISU students': 'three reviewers',
    'an undergraduate': 'one reviewer',
    'an experienced student': 'an experienced reviewer',
    'a student can check': 'a beginner can check',
}


def role(m):
    """A role phrase -> its neutral words; a line break inside the phrase stays, before the last word."""
    new, brk = ROLES[' '.join(m.group(0).split())].split(), re.search(r'\n\s*', m.group(0))
    return ' '.join(new[:-1]) + (brk.group(0) if brk else ' ') + new[-1] if len(new) > 1 else new[0]


def no_comments(m):
    """CLEARED keeps each paper's verdict; its comments held the reviewers' own review data (what each one typed or
    misread, rows of their own documents)."""
    lines = [re.sub(r'\s+#.*$', '', line) for line in m.group(0).split('\n')]
    return '\n'.join(line for line in lines if line.strip() and not line.lstrip().startswith('#')) + '\n'


SCRUBS = [
    # config.json: the earlier system's paper library, by the REALKCAT_DIR setting
    Rule('config.json', r'"' + HOME + r'/Documents/realkcat/', '"${REALKCAT_DIR}/', 3, 'library globs: REALKCAT_DIR'),
    Rule('config.json', r'/data/[A-Za-z0-9]+_help/download_intake_', '/data/*_help/download_intake_', 1,
         "library glob: no person's name in a folder name"),
    lit('catlog.py', "    for pattern in CONFIG['library_globs']:\n        for p in Path('/').glob(pattern.lstrip('/')):\n",
        "    for pattern in CONFIG['library_globs']:\n"
        "        # ${REALKCAT_DIR}: the earlier system's folder (README: settings), else a realkcat/ folder in this one\n"
        "        pattern = pattern.replace('${REALKCAT_DIR}', os.environ.get('REALKCAT_DIR') or str(ROOT / 'realkcat'))\n"
        "        for p in Path('/').glob(pattern.lstrip('/')):\n", 1, 'index: expand ${REALKCAT_DIR}'),
    # catlog.py: the authors' agent-log archiver, by the CATLOG_ARCHIVER setting
    Rule('catlog.py', r"^ARCHIVER = Path\.home\(\) / '[^\n]+'$",
         "ARCHIVER = os.environ.get('CATLOG_ARCHIVER', '')  # the authors' agent-log archiver (optional; README: settings)",
         1, 'status: CATLOG_ARCHIVER'),
    lit('catlog.py', "    try:\n        import importlib.util\n"
                     "        spec = importlib.util.spec_from_file_location('archive_catlog_chats', ARCHIVER)\n",
        "    if not ARCHIVER:\n        return []\n    try:\n        import importlib.util\n"
        "        spec = importlib.util.spec_from_file_location('archive_catlog_chats', ARCHIVER)\n", 1,
        'status: no archiver set, no line'),
    # catlog.py and tools: a fresh clone has no data folders and no database table yet
    lit('catlog.py', "if __name__ == '__main__':\n    a = [paper_id(x) for x in sys.argv[1:]] or ['status']\n",
        "if __name__ == '__main__':\n"
        "    for d in (TEXTS, WORK, ROOT / 'enrich', ROOT / 'sources'):  # a fresh clone has none of them yet\n"
        "        d.mkdir(exist_ok=True)\n"
        "    a = [paper_id(x) for x in sys.argv[1:]] or ['status']\n", 1, 'fresh clone: the data folders'),
    lit('tools/dbcompare.py', "    dv = root / 'sources' / 'db_values.tsv'\n    with open(dv) as fh:\n",
        "    dv = root / 'sources' / 'db_values.tsv'\n"
        "    with (open(dv) if dv.exists() else io.StringIO('\\n')) as fh:  # no table yet: tools/db_values.py builds it\n",
        1, 'fresh clone: export without sources/db_values.tsv'),
    lit('tools/db_values.py', "with open(S / 'db_values.tsv', 'w') as out:\n",
        "S.mkdir(exist_ok=True)\nwith open(S / 'db_values.tsv', 'w') as out:\n", 1, 'fresh clone: db_values makes sources/'),
    # catlog.py prompt: the saved texts this copy keeps in prompts/versions/
    lit('catlog.py', "    for saved in (WORK / 'prompts' / f'{h}.md', ROOT / 'sources' / 'prompt_versions' / f'{h}.md'):"
                     "  # the latter: backfill\n",
        "    for saved in (WORK / 'prompts' / f'{h}.md', ROOT / 'sources' / 'prompt_versions' / f'{h}.md',  # the latter: backfill\n"
        "                  ROOT / 'prompts' / 'versions' / f'{h}.md'):  # this copy: the authors' saved texts (README)\n",
        1, 'prompt: the saved texts in prompts/versions/'),
    # what users and services see: no institution, no authors' folder name
    lit('tools/km_gain.py', "UA = {'User-Agent': 'catlog-v2/1.0 (research text mining; Iowa State University)'}\n",
        "CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)\n"
        "UA = {'User-Agent': 'catlog-v2/1.0 (research text mining)' + (f' (mailto:{CONTACT})' if CONTACT else '')}\n",
        1, 'km_gain: the contact setting, not the institution, in the User-Agent'),
    lit('tools/fetch.py', 'put ELSEVIER_API_KEY in catlog-v2/.env',
        'set ELSEVIER_API_KEY (in the environment or a .env file in the CatLog folder)', 1, "fetch: no authors' folder name"),
    lit('catlog.py', '<code>catlog-v2/inbox/', '<code>inbox/', 2, "asks page: no authors' folder name"),
    # the browser download lane: the campus network by the CATLOG_CAMPUS_IP_PREFIX setting
    lit('catlog.py', "not str(j['ip']).startswith('129.186.')", f"not str(j['ip']).startswith{CAMPUS}", 1,
        'lanes-record: CATLOG_CAMPUS_IP_PREFIX'),
    lit('catlog.py', "no access on the ISU campus network (the line's ip 129.186.*;",
        "no access on the campus network (the line's ip starts with CATLOG_CAMPUS_IP_PREFIX;", 1,
        'lanes-record: docstring'),
    lit('tools/lane_agent.py', "a.startswith('129.186.') if a else None", f"a.startswith{CAMPUS} if a else None", 1,
        'lane_agent: CATLOG_CAMPUS_IP_PREFIX'),
    lit('tools/lane_agent.py', '(campus: the address starts\n129.186., null when unknown;',
        '(campus: the address starts\nwith CATLOG_CAMPUS_IP_PREFIX, false while that is unset, null when unknown;', 1,
        'lane_agent: docstring'),
    # tools: paths into the earlier system or into the authors' folder
    Rule('tools/fetch.py', r"^OLD_ENV = Path\('" + HOME + r"/Documents/realkcat/\.env'\)$",
         f"OLD_ENV = {OLD_DIR} / '.env'  # the earlier system's .env, a fallback for API keys (README: settings)",
         1, 'fetch: REALKCAT_DIR'),
    Rule('tools/enrich.py', r"^BULK = Path\('" + HOME + r"/Documents/realkcat/data/[A-Za-z0-9]+_help/"
                            r"uniprot_bulk_canonical_20260826/uniprot_bulk_canonical_20260826\.fasta'\)$",
         "BULK = Path(os.environ['CATLOG_BULK_FASTA']) if os.environ.get('CATLOG_BULK_FASTA') else None"
         "  # optional UniProt FASTA (README: settings)", 1, 'enrich: CATLOG_BULK_FASTA'),
    lit('tools/enrich.py', '        if BULK.exists():\n', '        if BULK and BULK.exists():\n', 1, 'enrich: no FASTA set'),
    lit('tools/coverage.py', 'import re, csv, gzip, json\n', 'import re, csv, gzip, json, os\n', 1, 'coverage: os'),
    Rule('tools/coverage.py', r"^OLD_SNAPSHOT = Path\('" + HOME + r"/Documents/realkcat/([^']+)'\)$",
         lambda m: f"OLD_SNAPSHOT = {OLD_DIR} / '{m.group(1)}'  # the earlier catalog (optional; README: settings)",
         1, 'coverage: REALKCAT_DIR'),
    lit('tools/coverage.py', "with gzip.open(OLD_SNAPSHOT, 'rt') as f:\n",
        "if not OLD_SNAPSHOT.exists():\n"
        "    print('the earlier catalog snapshot is not here (set REALKCAT_DIR): its rows are left out of coverage.tsv')\n"
        "with (gzip.open(OLD_SNAPSHOT, 'rt') if OLD_SNAPSHOT.exists() else open(os.devnull)) as f:\n", 1,
        'coverage: no snapshot, a message'),
    lit('tools/human_review.py', 'import csv, gzip, hashlib, json, re, subprocess, sys, time\n',
        'import csv, gzip, hashlib, json, os, re, subprocess, sys, time\n', 1, 'human_review: os'),
    Rule('tools/human_review.py', r"^OLD_REPO, OLD_BRANCH, OLD_STORE = '" + HOME + r"/Documents/realkcat', ",
         "OLD_REPO = os.environ.get('REALKCAT_DIR') or str(ROOT / 'realkcat')  # the earlier system's review store "
         "(optional; README: settings)\nOLD_BRANCH, OLD_STORE = ", 1, 'human_review: REALKCAT_DIR'),
    lit('tools/human_review.py', '    import catlog, random, shutil, zipfile\n    game = [',
        '    import catlog, random, shutil, zipfile\n    if not UI.is_dir():\n'
        "        sys.exit(f'review packs need the review page ({UI}), which this copy of CatLog leaves out')\n"
        '    game = [', 1, 'review pack: a message without the review page'),
    # tools/human_review.py: no reviewer's own review data, words, files, dates, pronouns or role next to the labels
    Rule('tools/human_review.py', r"(?s)^# Who made the earlier review page's results files, which saved no name \(.*?"
                                  r"their mind\.\n",
         "# Who made the earlier review page's results files, which saved no name, by the file's sha256 (manifest.tsv). Two\n"
         "# people who decided the same record are then two reviewers, not one changing their mind.\n", 1,
         "human review: no reviewer's files, dates or pronoun"),
    Rule('tools/human_review.py', r'(?s)could not open the article \(his doc of .*?approved without the paper',
         'could not open the article; approved without the paper', 1, "human review: no reviewer's own words"),
    Rule('tools/human_review.py', r"^(\s+for k in )\[[0-9a-f', ]+\]\}", lambda m: m.group(1) + '[]}', 1,
         "human review: the authors' no-paper decisions stay with their data"),
    Rule('tools/human_review.py', r'(?s)^CLEARED = \{.*?\n(?=VALUE_CATS = )', no_comments, 1,
         "human review: CLEARED without the reviewers' review data"),
    Rule('tools/human_review.py',
         '|'.join(r'\s+'.join(map(re.escape, k.split())) for k in sorted(ROLES, key=len, reverse=True)), role,
         len(ROLES), "human review: no reviewer's role or habits"),
    Rule('tools/site_release.py', r"^OLD = Path\('" + HOME + r"/Documents/realkcat'\)$",
         f'OLD = {OLD_DIR}  # the earlier CatLog system: the website build needs it (README: settings)',
         1, 'site_release: REALKCAT_DIR'),
    lit('tools/site_release.py', '    """The base must still be the certified October 7 file the live site was built from."""\n',
        '    """The base must still be the certified October 7 file the live site was built from."""\n'
        "    if not (RELEASE / 'checkpoint.json').exists():\n"
        "        sys.exit(f'the website build needs the earlier CatLog system: set REALKCAT_DIR to its folder '\n"
        "                 f'({RELEASE} is missing)')\n", 1, 'site build: a message without the earlier system'),
    Rule('tools/brenda_count.py', r'^ARCHIVE = "' + HOME + r'/Documents/catlog-v2/sources/brenda_2026_1\.json\.tar\.gz"$',
         'from pathlib import Path  # noqa: E402\n'
         'ARCHIVE = str(Path(__file__).resolve().parent.parent / "sources" / "brenda_2026_1.json.tar.gz")'
         "  # this repository's sources/", 1, 'brenda_count: this repository'),
    Rule('tools/brenda_overlap.py', r'^S = "' + HOME + r'/Documents/catlog-v2/sources"(.*)\nV2 = "' + HOME
         + r'/Documents/catlog-v2"$',
         lambda m: ('from pathlib import Path  # noqa: E402\n'
                    'V2 = str(Path(__file__).resolve().parent.parent)  # this repository\n'
                    'S = f"{V2}/sources"' + m.group(1)), 1, 'brenda_overlap: this repository'),
    Rule('tools/test_publication_years.py', r"^LIVE_WORK = Path\('" + HOME + r"/Documents/catlog-v2/work/brenda_lag_20261021'\)",
         "LIVE_WORK = TOOLS.parent / 'work' / 'brenda_lag_20261021'", 1, 'test: this repository'),
    Rule('tools/test_blind_check.py', r'/[U]sers/x/', '/home/x/', 5, 'test: a neutral made-up path'),
    lit('tools/test_publication_years.py', 'class Shipped(unittest.TestCase):\n',
        "@unittest.skipUnless((TOOLS.parent / py.BRENDA).exists(), 'needs sources/brenda_values_by_year_2026_1.tsv '\n"
        "                     '(BRENDA counts, not in this repository)')\nclass Shipped(unittest.TestCase):\n", 1,
        'test: skipped without its BRENDA data file'),
    # tools/reread_copies.py (from SOURCE's work/ folder): this repository's catlog.py
    Rule('tools/reread_copies.py', r"^import collections, json, re, sys\nsys\.argv, args = \['catlog\.py'\], sys\.argv\[1:\]\n"
                                   r"sys\.path\.insert\(0, '" + HOME + r"/Documents/catlog-v2'\)$",
         "import collections, json, re, sys\nfrom pathlib import Path\nsys.argv, args = ['catlog.py'], sys.argv[1:]\n"
         "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # this repository: catlog.py", 1,
         'reread_copies: this repository'),
    lit('tools/reread_copies.py', 'Usage: python3 work/reread_copies/reread_copies.py PMID [OUT_TSV]',
        'Usage: python3 tools/reread_copies.py PMID [OUT_TSV]', 1, 'reread_copies: where it is here'),
    # workflows: the CatLog folder comes from args.root, the agents' scratch folder from args.scratch
    Rule(['.claude/workflows/catlog-batch.js', '.claude/workflows/catlog-dbcheck.js'],
         r"^const DIR = String\(\(args && !Array\.isArray\(args\) && args\.root\) \|\| '" + HOME
         + r"/Documents/catlog-v2'\)\.replace\(/\\/\+\$/, ''\)$",
         f"const CATLOG_ROOT = ''  // {NO_ROOT}\n"
         "const DIR = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\\/+$/, '')",
         2, 'workflows: args.root'),
    lit(['.claude/workflows/catlog-batch.js', '.claude/workflows/catlog-dbcheck.js'],
        "return { error: 'args.root must be an absolute path (no ~ or $)' }", f"return {{ error: '{ROOT_ERROR}' }}",
        2, 'workflows: args.root message'),
    Rule(['.claude/workflows/catlog-batch.js', '.claude/workflows/catlog-dbcheck.js'],
         r'\(default the main folder([;)])', lambda m: '(no default in this copy' + m.group(1), 2,
         'workflows: comment'),
    Rule([f'.claude/workflows/catlog-{w}.js' for w in ('audit', 'chrome-lanes', 'scale', 'vmax')]
         + ['.claude/workflows/catlog-audit-followup.js', '.claude/workflows/catlog-unitcheck.js'],
         r"^const DIR = '" + HOME + r"/Documents/catlog-v2'$", js_root('DIR'), 6, 'workflows: args.root'),
    Rule(['.claude/workflows/catlog-nd-census.js', '.claude/workflows/catlog-reprint-pairs.js',
          '.claude/workflows/catlog-reprint-third-opinion.js'],
         r"^const ROOT = '" + HOME + r"/Documents/catlog-v2'$", js_root('ROOT'), 3, 'workflows: args.root'),
    Rule(FROM_WORK, r"^const SCRATCH = '/private/tmp/claude-\d+/[^'\n]*/scratchpad(/[a-z]+)?'$",
         lambda m: ("const SCRATCH = String((args && !Array.isArray(args) && args.scratch) || '/tmp/catlog-scratch')"
                    + (f" + '{m.group(1)}'" if m.group(1) else '') + "  // the agents' scratch folder (args.scratch)"),
         4, "workflows: args.scratch, not the authors' session folder"),
    lit('.claude/workflows/catlog-reprint-pairs.js', 'const pmids = Array.isArray(args) ? args : []',
        'const pmids = Array.isArray(args) ? args : ((args && args.pmids) || [])  // a list, or {pmids, root}', 1,
        'reprint pairs: {pmids, root} too'),
    # slash commands: no machine path; the workflows get args.root; the data never goes into this repository
    Rule('.claude/commands/audit.md', r'^In ' + HOME + r'/Documents/catlog-v2\. ', 'In the CatLog folder (this repository). ',
         1, 'audit command: folder'),
    lit('.claude/commands/audit.md', '`args = {"groups": <those groups>}`', '`args = {"groups": <those groups>' + ARGS_ROOT,
        1, 'audit command: args.root'),
    lit('.claude/commands/audit.md', '`args = {"rows": <the list>}`', '`args = {"rows": <the list>' + ARGS_ROOT,
        1, 'audit command: args.root'),
    lit('.claude/commands/audit.md', '(≤3 auditors live)', '(args.lanes auditors live, default 6)', 1,
        'audit command: the workflow default'),
    Rule('.claude/commands/batch.md', r'^Run one batch in ' + HOME + r'/Documents/catlog-v2, following RUN\.md\. ',
         'Run one batch in the CatLog folder (this repository). ', 1, 'batch command: folder'),
    Rule('.claude/commands/batch.md', r'`du -sh ~/\.claude/projects [^`\n]+`', '`du -sh ~/.claude/projects .`', 1,
         'batch command: machine folders'),
    lit('.claude/commands/batch.md', '`df -h /System/Volumes/Data`', '`df -h .`', 1, 'batch command: any system'),
    lit('.claude/commands/batch.md', '`args = {"pmids": [those claimed PMIDs], "lanes": LANES}`',
        '`args = {"pmids": [those claimed PMIDs], "lanes": LANES' + ARGS_ROOT, 1, 'batch command: args.root'),
    lit('.claude/commands/batch.md', '`args = {"pmids": [those PMIDs], "lanes": LANES, "dbcheck": [the claimed PMIDs]}`',
        '`args = {"pmids": [those PMIDs], "lanes": LANES, "dbcheck": [the claimed PMIDs]' + ARGS_ROOT, 1,
        'batch command: args.root'),
    Rule('.claude/commands/batch.md', r'(?:CLAUDE|HUMAN_REVIEW)\.md ("[^"\n]+")( says)?',
         lambda m: f"the authors' notes ({m.group(1)}; not included here)" + (' say' if m.group(2) else ''), 3,
         "batch command: the authors' notes"),
    Rule('.claude/commands/batch.md', r'^8\. Every 10th batch and when the loop stops, keep a data checkpoint '
                                      r'\(the catalog has no other backup\):\n   `git commit [^\n]*\n   \(named paths only[^\n]*\n',
         '8. Every 10th batch and when the loop stops, back up the data files (catalog.jsonl, rejected.jsonl, bounds.jsonl,\n'
         '   papers.tsv, log.tsv, human_review/): this repository git-ignores them, so never `git add -f` them here; keep\n'
         '   them in a separate private repository or backup.\n', 1, 'batch command: the data never goes into this repository'),
    # prompts: the agents' folder is the one their task names
    Rule(['prompts/scale.md', 'prompts/vmax.md'], r'`cd ' + HOME + r'/Documents/catlog-v2 && ', '`cd <the CatLog folder> && ',
         2, 'prompts: folder'),
    # the saved prompt and task texts: the authors' folder (their MANIFEST.tsv line says the text changed here)
    Rule(f'{VERSIONS}/*.md', HOME + r'/Documents/catlog-v2', '<the CatLog folder>', None, 'saved texts: the folder'),
]

# ---------- e-mail addresses -> CATLOG_CONTACT_EMAIL ----------

EMAIL = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}'
EMAIL_RX = re.compile(EMAIL)
TEST_ADDRESS = re.compile(r'@example\.(?:org|com|net|invalid)$', re.I)
SPOT = re.compile(r' \((?:mailto:)?(?P<ua>' + EMAIL + r')\)|(?P<sep>[?&])(?P<key>email|mailto)=(?P<param>' + EMAIL + ')')
CONTACT_DEF = ("CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')"
               "  # a contact e-mail for the APIs' polite pools (README: settings)")


def tokens(text):
    """The module's tokens as (is_string, text, start, end) with offsets into `text`; a string literal, an f-string
    included (one token before Python 3.12, several from 3.12 on), is one item. Lines split as the tokenizer splits."""
    starts = [0]
    for line in io.StringIO(text):
        starts.append(starts[-1] + len(line))
    off = lambda pos: starts[pos[0] - 1] + pos[1]
    fs, fe = getattr(tokenize, 'FSTRING_START', -1), getattr(tokenize, 'FSTRING_END', -1)
    quiet = (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER)
    items, depth, begin = [], 0, 0
    for t in tokenize.generate_tokens(io.StringIO(text).readline):
        if t.type == fs:
            begin = off(t.start) if depth == 0 else begin
            depth += 1
        elif t.type == fe:
            depth -= 1
            if depth == 0:
                items.append((True, text[begin:off(t.end)], begin, off(t.end)))
        elif not depth and t.type not in quiet:
            items.append((t.type == tokenize.STRING, t.string, off(t.start), off(t.end)))
    return items


def balanced(piece):
    piece = piece.replace('{{', '').replace('}}', '')
    return piece.count('{') == piece.count('}')


def contact(path, text, errors):
    """Each e-mail address in a string literal -> an expression of CONTACT (the CATLOG_CONTACT_EMAIL setting)."""
    items = tokens(text)
    edits = []
    for i, (is_str, lit_text, a, b) in enumerate(items):
        if not is_str or not [e for e in EMAIL_RX.findall(lit_text) if not TEST_ADDRESS.search(e)]:
            continue
        where = f'{path}:{text.count(chr(10), 0, a) + 1}'
        prefix, q, body = re.match(r'(?s)([A-Za-z]*)(\'\'\'|"""|\'|")(.*)\2$', lit_text).groups()
        j, k = i, i  # this literal's run of implicitly concatenated literals
        while j > 0 and items[j - 1][0]:
            j -= 1
        while k + 1 < len(items) and items[k + 1][0]:
            k += 1
        before = items[j - 1][1] if j > 0 else ''
        after = items[k + 1][1] if k + 1 < len(items) else ''
        if 'b' in prefix.lower() or before in ('*', '/', '//', '%', '@', '**', '~', '.', 'await') or \
                after in ('%', '.', '[', '(', '*', '/', '//', '@', '**'):
            errors.append(f'{where}: an e-mail address in a literal this script cannot rewrite safely; add a rule')
            continue
        parts, pos = [], 0
        for s in SPOT.finditer(body):
            if s['sep'] == '?' and body[s.end():s.end() + 1] == '&':
                errors.append(f'{where}: a ?{s["key"]}= with more parameters after it; add a rule')
            expr = ("(f' (mailto:{CONTACT})' if CONTACT else '')" if s['ua'] else
                    "(f'" + s['sep'] + s['key'] + "={CONTACT}' if CONTACT else '')")
            parts += [body[pos:s.start()], expr]
            pos = s.end()
        parts.append(body[pos:])
        if [e for e in EMAIL_RX.findall(''.join(parts[0::2])) if not TEST_ADDRESS.search(e)] or \
                ('f' in prefix.lower() and not all(balanced(p) for p in parts[0::2])):
            errors.append(f'{where}: an e-mail address outside a User-Agent or an email=/mailto= parameter; add a rule')
            continue
        out = []
        for n, piece in enumerate(parts):
            if n % 2:
                out.append(piece)
            elif piece or (n == 0 and j < i) or (n == len(parts) - 1 and k > i):  # an empty piece keeps a run joined
                pre = prefix if '{' in piece else prefix.replace('f', '').replace('F', '')
                out.append(f'{pre}{q}{piece}{q}')
        edits.append((a, b, ' + '.join(out)))
    for a, b, new in sorted(edits, reverse=True):
        text = text[:a] + new + text[b:]
    if edits and not re.search(r'^CONTACT = ', text, re.M):
        text = define_contact(path, text, errors)
    return text, len(edits)


def define_contact(path, text, errors):
    """CONTACT = ... (and `import os` when the module has none) before the first top-level statement that needs it."""
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        errors.append(f'{path}: does not parse after the e-mail rewrite ({e})')
        return text
    uses = lambda node: any(isinstance(n, ast.Name) and n.id == 'CONTACT' for n in ast.walk(node))
    first = next(n for n in tree.body if uses(n))
    if isinstance(first, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        first = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
    line = min([first.lineno] + [d.lineno for d in getattr(first, 'decorator_list', [])])
    lines = io.StringIO(text).readlines()  # split as the parser counts lines
    while line > 1 and not lines[line - 2].strip():  # after the statements above, not between blank lines and a def
        line -= 1
    imports = [n for n in tree.body if isinstance(n, ast.Import) and n.lineno < line]
    add = []
    if not any(a.name == 'os' and a.asname in (None, 'os') for n in imports for a in n.names):
        plain = next((n for n in imports if n.end_lineno == n.lineno and all(a.asname is None for a in n.names)
                      and re.fullmatch(r'import [\w., ]+\n', lines[n.lineno - 1])), None)
        if plain:  # join the module's own import line, in order when it is in order
            mods = [a.name for a in plain.names]
            mods = sorted(mods + ['os']) if mods == sorted(mods) else mods + ['os']
            lines[plain.lineno - 1] = 'import ' + ', '.join(mods) + '\n'
        else:
            add.append('import os  # noqa: E402  (CATLOG_CONTACT_EMAIL)\n')
    return ''.join(lines[:line - 1] + add + [CONTACT_DEF + '\n'] + lines[line - 1:])


# ---------- names ----------

def read_names(path):
    """[(name, label, {path: matches allowed as code})], longest names first."""
    names = []
    for raw in Path(path).read_text(encoding='utf-8').splitlines():
        if raw.strip() and not raw.lstrip().startswith('#'):
            name, label, allow = (raw.split('\t') + ['', ''])[:3]
            if not name.strip() or not label.strip():
                sys.exit(f'{path}: every line is name<TAB>label[<TAB>path=N,...]')
            try:
                allowed = {p.strip(): int(n) for p, _, n in (x.rpartition('=') for x in allow.split(',') if x.strip())}
            except ValueError:
                sys.exit(f'{path}: an allowance is path=N')
            names.append((name.strip(), label.strip(), allowed))
    if not names:
        sys.exit(f'{path}: no names')
    return sorted(names, key=lambda x: -len(x[0]))


def word(name, flags=0):
    return re.compile(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'(?![A-Za-z0-9_])', flags)


def anywhere(name):
    """A name in any case, also inside a path, a file name or a snake_case word ('review_xy_2026'): letters only bound it."""
    return re.compile(r'(?<![A-Za-z])' + re.escape(name) + r'(?![A-Za-z])', re.I)


# reviewer values in tools/human_review.py that must be labels after the names step
REVIEWER_SPOTS = (r"dict\.fromkeys\(\([^)]*\), '([^']*)'\)", r"\(k, '([^']*)'\)", r"""--split ['"]([^'"]+)['"]""",
                  r"""like ['"]?([^'":,]+):\d+""", r'\(v2, ([^)]+)\)')
# a gendered pronoun in tools/human_review.py can tell who a label is ('His' is histidine there)
GENDERED = re.compile(r'(?<![A-Za-z])(?:he|she|his|her|hers|him|himself|herself|He|She|Her|Hers|Him)(?![A-Za-z])')

# ---------- checks ----------

KEYS = (r'AKIA[0-9A-Z]{16}', r'gh[pousr]_[A-Za-z0-9]{30,}', r'github_pat_\w{30,}', r'sk-(?:ant-)?[A-Za-z0-9_-]{20,}',
        r'xox[abprs]-[A-Za-z0-9-]{10,}', r'-----BEGIN [A-Z ]*PRIVATE KEY-----', r'(?<![0-9a-fA-F])[0-9a-f]{32}(?![0-9a-fA-F])',
        r'''(?i)\b(?:api[_-]?key|apikey|secret|token|password)\b\s*[:=]\s*['"][A-Za-z0-9_\-]{16,}['"]''')
DETECTOR = re.compile(r'/[U]sers/\|')  # the site tools' local-path checks: a regex alternative, not a path
PAPER_ID = re.compile(r'(?<!\d)\d{4,9}(?!\d)|(?i:(?<![0-9a-z])np[0-9a-f]{8}(?![0-9a-z]))')  # PMID9876543, 1234567.json too


def owner_names(src):
    """The source owner's user name (from the login and from SOURCE's home-folder path), 4 letters or more."""
    users = {getpass.getuser()}
    parts = Path(src).resolve().parts
    if len(parts) > 2 and parts[1] in ('Users', 'home'):
        users.add(parts[2])
    return {u for u in users if len(u) >= 4}


def env_values(src):
    """(where, value) of every setting of 8 characters or more in SOURCE's .env and the earlier system's .env (the
    source's code reads both): read here only to make sure no copied file holds one; never shown or written."""
    out = []
    old = Path(os.environ.get('REALKCAT_DIR') or Path(src).parent / 'realkcat')
    for f in (Path(src) / '.env', old / '.env'):
        if f.is_file():
            for i, line in enumerate(f.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                k, sep, v = line.strip().removeprefix('export ').partition('=')
                v = v.strip().strip('\'"')
                if sep and not k.strip().startswith('#') and len(v) >= 8:
                    out.append((f'{f.parent.name}/.env line {i}', v))
    return out


def check(content, src, names, errors):
    users = owner_names(src)
    held = set()
    for f in sorted((Path(src) / 'sources').glob('holdout_*.txt')):  # read here, never copied
        held |= {w.upper() for line in f.read_text().splitlines() if not line.startswith('#') for w in line.split()}
    name_rx = [(n, word(n, 0 if len(n) <= 3 else re.I), label) for n, label, _ in names]
    strict = [(n, anywhere(n), label, allow) for n, label, allow in names]
    labels = {label for _, label, _ in names}
    secrets = env_values(src)
    for path, text in sorted(content.items()):
        if len(text.encode('utf-8')) > MAX_BYTES:
            errors.append(f'{path}: over 5 MB')
        for u in users:
            if re.search(re.escape(u), path + '\n' + text, re.I):
                errors.append(f"{path}: holds the source owner's user name")
        for n, rx, label in name_rx:
            if rx.search(path) or rx.search(text):
                errors.append(f'{path}: holds a name from the names file (labelled {label!r})')
        if path not in OWN:  # a copied file: in any case, inside paths and identifiers too, beyond what is code
            for n, rx, label, allow in strict:
                hits = len(rx.findall(path)) + len(rx.findall(text))
                if hits != allow.get(path, 0):
                    errors.append(f'{path}: holds a name from the names file {hits} time(s), {allow.get(path, 0)} allowed '
                                  f'as code (labelled {label!r}): perhaps inside a path or an identifier')
        for where, v in secrets:
            if v in text:
                errors.append(f'{path}: holds the value of {where} (not shown)')
        for i, line in enumerate(text.splitlines(), 1):
            for e in EMAIL_RX.findall(line):
                if not TEST_ADDRESS.search(e):
                    errors.append(f'{path}:{i}: an e-mail address')
            if re.search(r'/[U]sers/', DETECTOR.sub('', line)):
                errors.append(f'{path}:{i}: a home-folder path')
            if held and any(t.upper() in held for t in PAPER_ID.findall(line)):
                errors.append(f'{path}:{i}: a paper id from the held-out lists')
            for k in KEYS:
                if re.search(k, line):
                    errors.append(f'{path}:{i}: looks like a key ({k[:20]}...)')
        if path.endswith('.py'):
            try:
                compile(text, path, 'exec', dont_inherit=True)
            except SyntaxError as e:
                errors.append(f'{path}: does not compile ({e})')
        if path.endswith('.json'):
            try:
                json.loads(text)
            except ValueError as e:
                errors.append(f'{path}: not JSON ({e})')
    hr = content.get('tools/human_review.py', '')
    for spot in REVIEWER_SPOTS:
        for m in re.finditer(spot, hr):
            for value in m.group(1).split(','):
                who = value.rpartition(':')[0] if ':' in value else value
                who = who.strip().strip('\'"')
                if who and who not in labels | {'NAME'}:
                    errors.append(f'tools/human_review.py: a reviewer value that is not a label ({who!r}): '
                                  'add the name to the names file')
    for i, line in enumerate(hr.splitlines(), 1):
        if GENDERED.search(line):
            errors.append(f'tools/human_review.py:{i}: a gendered pronoun (with the labels it can tell who a reviewer '
                          'is): add a rule')
    return held


def identity(dest, src, names, errors):
    """The name and e-mail DEST's next commit would carry (its own config, else the global one) must be neutral."""
    if not (dest / '.git').exists():
        return
    who = {k: subprocess.run(['git', '-C', str(dest), 'config', f'user.{k}'], capture_output=True, text=True).stdout.strip()
           for k in ('name', 'email')}
    if not re.search(r'@(?:users\.noreply\.github\.com|example\.invalid)$', who['email']):
        errors.append(f'{dest}: the next commit there would carry a personal e-mail (not shown); set a repo-local '
                      'user.email first: a GitHub noreply address or catlog@example.invalid')
    if not who['name'] or any(anywhere(n).search(who['name']) for n, _, _ in names) or \
            any(u.lower() in who['name'].lower() for u in owner_names(src)):
        errors.append(f'{dest}: the next commit there would carry a personal name (not shown); set a repo-local '
                      'user.name first, e.g. CatLog')


# ---------- source and destination ----------

def git(src, *args):
    r = subprocess.run(['git', '-C', str(src), '--no-optional-locks', *args], capture_output=True)
    if r.returncode:
        sys.exit(f'git {" ".join(args)} in {src}: {r.stderr.decode(errors="replace").strip()}')
    return r.stdout


def source(src, ref):
    """{path: (bytes, executable)} of every watched file, the commit (None on disk), and where they came from."""
    files = {}
    if ref is None:
        cands = [p for p in src.glob('*.py')] + [src / 'config.json']
        for top in ('tools', 'prompts', '.claude'):
            cands += [p for p in (src / top).rglob('*') if p.is_file()]
        for p in cands:
            rel = p.relative_to(src).as_posix()
            if p.is_file() and watched(rel) and not skipped(rel):
                files[rel] = (p.read_bytes(), bool(p.stat().st_mode & 0o111))
        return files, None, f'{src} (files on disk)'
    commit = git(src, 'rev-parse', '--verify', f'{ref}^{{commit}}').decode().strip()
    for entry in git(src, 'ls-tree', '-r', '-z', commit).decode().split('\0'):
        if not entry:
            continue
        meta, rel = entry.split('\t', 1)
        mode, kind, _ = meta.split()
        if kind == 'blob' and watched(rel) and not skipped(rel):
            files[rel] = (git(src, 'show', f'{commit}:{rel}'), mode == '100755')
    return files, commit, f'{src} at commit {commit[:12]}'


def saved_texts(src, commit, errors):
    """{hash: (bytes, where it was saved)}: the texts rows' prompt stamps name. sources/prompt_versions/ (rebuilt by
    tools/provenance_backfill.py) at the commit, or on disk with --working-tree; work/prompts/ (saved when a row was
    stamped; git-ignored in SOURCE) on disk. Each must hash to its own name."""
    found = {}
    if commit:
        for entry in git(src, 'ls-tree', '-r', '-z', commit, '--', 'sources/prompt_versions').decode().split('\0'):
            rel = entry.split('\t', 1)[-1]
            if entry and rel.endswith('.md'):
                found[rel] = git(src, 'show', f'{commit}:{rel}')
    else:
        for p in sorted((src / 'sources' / 'prompt_versions').glob('*.md')):
            found[p.relative_to(src).as_posix()] = p.read_bytes()
    for p in sorted((src / 'work' / 'prompts').glob('*.md')):
        found[p.relative_to(src).as_posix()] = p.read_bytes()
    out = {}
    for rel, data in sorted(found.items()):
        h = Path(rel).stem
        if not re.fullmatch(r'[0-9a-f]{12}', h) or hashlib.sha256(data).hexdigest()[:12] != h:
            errors.append(f'{rel}: does not hash to its name (a saved text is exactly the text its stamp names)')
        elif h not in out or rel.startswith('work/'):
            out[h] = (data, str(Path(rel).parent))
    return out


def text_kind(text):
    first = text.split('\n', 1)[0]
    return ('task' if first.startswith('=== ') else 'read' if first.startswith('# Read') else
            'verify' if first.startswith('# Verify') else 'other')


def managed(dest):
    out = set()
    for p in dest.rglob('*'):
        rel = p.relative_to(dest).as_posix()
        if (p.is_file() and not rel.startswith('.git/') and rel not in OWN and not skipped(rel)
                and (rel in MANAGED or rel.startswith(tuple(m for m in MANAGED if m.endswith('/'))))):
            out.add(rel)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('source', help="the authors' CatLog folder")
    ap.add_argument('--names', default=os.environ.get('CATLOG_SYNC_NAMES', ''),
                    help="private file of name<TAB>label lines (or CATLOG_SYNC_NAMES); never in this repository")
    how = ap.add_mutually_exclusive_group()
    how.add_argument('--ref', default='HEAD', help='the commit to copy from (default HEAD)')
    how.add_argument('--working-tree', action='store_true', help='copy the files as they are on disk instead')
    ap.add_argument('--dest', default=str(HERE), help='where to write (default: the folder of this script)')
    ap.add_argument('--check', action='store_true', help='apply and check everything, write nothing')
    a = ap.parse_args()
    src, dest = Path(a.source).resolve(), Path(a.dest).resolve()
    if not (src / 'catlog.py').is_file():
        sys.exit(f'{src}: no catlog.py here')
    if not a.names or not Path(a.names).is_file():
        sys.exit('pass --names FILE (name<TAB>label per line; private, never in this repository) or set CATLOG_SYNC_NAMES:'
                 ' without it no name is replaced, so nothing is written')
    if src == dest or dest in src.parents or src in dest.parents:
        sys.exit('the source and the destination must be separate folders')
    names = read_names(a.names)
    files, commit, origin = source(src, None if a.working_tree else a.ref)
    errors = []
    new = sorted(p for p in files if p not in INCLUDE and not any(fnmatch.fnmatchcase(p, x) for x in EXCLUDE))
    errors += [f'{p}: new in the source; read it, then list it in INCLUDE, DISK or EXCLUDE' for p in new]
    errors += [f'{p}: listed in INCLUDE but not in the source' for p in INCLUDE if p not in files]
    content, modes, original = {}, {}, {}
    for p in INCLUDE:
        if p in files:
            try:
                content[p] = files[p][0].decode('utf-8')
            except UnicodeDecodeError:
                errors.append(f'{p}: not UTF-8 text')
            modes[p] = files[p][1]
    from_disk = []
    for here, there in DISK.items():
        f = src / there
        if here in files:
            errors.append(f'{here}: committed in the source now; move it from DISK to INCLUDE')
        elif not f.is_file():
            errors.append(f'{there}: not in the source (DISK)')
        else:
            data = f.read_bytes()
            try:
                content[here] = data.decode('utf-8')
            except UnicodeDecodeError:
                errors.append(f'{there}: not UTF-8 text')
            modes[here] = bool(f.stat().st_mode & 0o111)
            from_disk.append(f'{here} <- {there} (sha256 {hashlib.sha256(data).hexdigest()[:12]})')
    texts = saved_texts(src, commit, errors)
    for h, (data, where) in texts.items():
        try:
            original[f'{VERSIONS}/{h}.md'] = content[f'{VERSIONS}/{h}.md'] = data.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'{where}/{h}.md: not UTF-8 text')
    print(f'source: {origin}; {len(content) - len(from_disk) - len(texts)} committed files to copy, '
          f'{len(files) - len(content) + len(from_disk) + len(texts)} left out; from its disk: {len(from_disk)} files of '
          f'its work/ folder and {len(texts)} saved prompt and task texts')
    for line in from_disk:
        print('  ' + line)
    for rule in SCRUBS:
        n = 0
        for p in sorted(content):
            if any(fnmatch.fnmatchcase(p, f) for f in rule.files):
                content[p], k = rule.rx.subn(rule.repl, content[p])
                n += k
        if (n == 0) if rule.count is None else (n != rule.count):
            errors.append(f'scrub "{rule.why}" matched {n} times, not {rule.count or "one or more"}: the source changed; '
                          'look at the rule')
    mails = 0
    for p in sorted(content):
        if p.endswith('.py'):
            content[p], k = contact(p, content[p], errors)
            mails += k
    labelled = {}
    for name, label, _ in names:
        rx = word(name)
        for p in sorted(content):
            content[p], k = rx.subn(lambda m, text=label: text, content[p])
            if k:
                labelled[label] = labelled.get(label, 0) + k
    rows = ['hash\tkind\tsaved_in\tchanged_here']  # changed_here yes: the authors' folder path became <the CatLog folder>
    for h, (data, where) in sorted(texts.items()):
        p = f'{VERSIONS}/{h}.md'
        rows.append(f"{h}\t{text_kind(original.get(p, ''))}\t{where}\t{'yes' if content.get(p) != original.get(p) else 'no'}")
    content[f'{VERSIONS}/MANIFEST.tsv'] = '\n'.join(rows) + '\n'
    kinds = {k: sum(1 for r in rows[1:] if r.split('\t')[1] == k) for k in ('read', 'verify', 'task', 'other')}
    own = {p: (dest / p).read_text(encoding='utf-8') for p in sorted(OWN) if (dest / p).is_file()}
    held = check({**content, **own}, src, names, errors)  # this repository's own files are checked too, never changed
    identity(dest, src, names, errors)
    print(f'scrubs: {len(SCRUBS)} rules applied; {mails} e-mail literals now use CATLOG_CONTACT_EMAIL; names: '
          + (', '.join(f'{label} {k}' for label, k in sorted(labelled.items())) or 'none found'))
    print(f"saved texts: {len(texts)} in {VERSIONS}/ ({', '.join(f'{v} {k}' for k, v in kinds.items() if v)}), "
          f"{sum(1 for r in rows[1:] if r.endswith('yes'))} with the authors' folder replaced")
    print('checks: e-mail, home paths, user name, names, reviewer labels and pronouns, '
          + (f'{len(held)} held-out ids, ' if held else 'held-out ids (no list in the source), ')
          + '.env values, keys, sizes, compile, JSON' + (', commit identity' if (dest / '.git').exists() else ''))
    if errors:
        print(f'\n{len(errors)} problem(s); nothing written:', file=sys.stderr)
        for e in errors:
            print('  ' + e, file=sys.stderr)
        sys.exit(1)
    have = managed(dest) if dest.exists() else set()
    gone = sorted(have - set(content))
    changed = sorted(p for p in content if not (dest / p).is_file() or (dest / p).read_bytes() != content[p].encode('utf-8'))
    print(f'{len(changed)} files new or changed, {len(gone)} to remove' + (' (--check: nothing written)' if a.check else ''))
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
