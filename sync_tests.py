#!/usr/bin/env python3
"""Refresh tests/, the paper's test registrations and the tests' records, from the authors' folders, by rules.

    python3 -B sync_tests.py --catlog CATLOG --kit KIT --names NAMES.tsv [--ref REF] [--check]

(-B, not -I: the EnzyExtract rows are checked against the supplementary parquet files with pyarrow, which may be
installed in the user's site-packages; -I would hide it.)

CATLOG is the CatLog folder the authors work in (a git repository), KIT the folder the locked and random tests ran in.
Each plan comes from the commit named in PLANS, by `git show`; every other committed file (results, reports, scorers,
the page check's tasks and verdicts, the broad test's key and verdicts) from one commit of CATLOG, --ref (default
HEAD, printed), by `git show`, so a half-finished edit there never comes over. Records CATLOG keeps out of git are read from disk: both sides' readings,
the claims and the judges' verdicts of the locked and random tests (KIT's records/ and out/), the broad test's value
lists (CATLOG's work/, rebuilt by its build.py), and the EnzyExtract supplementary files, read only to name rows.
Nothing is written in either folder (no bytecode, no cache).

What comes over (tests/README.md says what each file is):
  - the plans, byte for byte as committed; DOC_RULES are the only changes to any document, and each must match as often
    as it says;
  - the records, written here as TSV and JSON with fixed columns: each side's values, each claim the judges ruled on and
    each verdict, the planted errors, the papers and why any left, the blinding keys;
  - the scorers' reports (RESULTS.md) and their JSON outputs with every per-value list left out (aggregates only);
  - the scorers analysis/ does not hold.

Scrub rules:
  1. EnzyExtract's data (its supplementary files, released under CC BY-NC 4.0) never come over: each EnzyExtract value
     is named by its file and 0-based row. Database values (BRENDA, SABIO-RK, OED, SKiD, UniProt) are counted, never
     listed; the person-anchored reference (the earlier catalogue's values, built from those databases) is listed
     without its numbers.
  2. Paper text: a printed line (CatLog's quote) stays when it has at most 25 words; a label field is blanked when more
     than 25 of its words are copied from the paper (in runs of 8 or more words of the paper's text); a judge's
     reasoning is dropped when it shares any run of 8 words with the paper.
  3. People: no reviewer and no review time (the person-anchored reference carries a category only); people's names
     become the labels of NAMES.tsv (sync_from_catlog.read_names: private, never part of this repository).
  4. Machine paths become placeholders (<the CatLog folder>, <the kit folder>, <the home folder>), as in analysis/.
The result is checked before anything is written: no name from NAMES.tsv (any case, inside paths and identifiers too),
not the owner's user name, no e-mail address, no home-folder path, nothing that looks like a key and no value of
CATLOG's .env files, no file over 5 MB; every .py compiles, every .json parses and every .tsv is rectangular; rule 2 on
every free-text column against its paper's text, and no document holds a run of more than 25 words of any paper of its
test; no field of a value from EnzyExtract or a database in a record or an aggregate; no held-out paper id outside the
locked test's draw. tests/README.md, tests/*/README.md and this script are this repository's own files: checked, never
written. Then tests/ is written; files the rules no longer make are removed, and nothing is committed.

The patterns below write a home folder as /[U]sers/, so that a search of this repository for machine paths finds none.
"""
import argparse, csv, gzip, hashlib, importlib.util, io, json, re, subprocess, sys, unicodedata
from collections import Counter, defaultdict
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sync_from_catlog as S  # noqa: E402  (names, e-mail, key and .env checks)

DEST = 'tests/'
OWN = {'sync_tests.py'}  # and every README.md under tests/
MAX_BYTES = 5 * 1024 * 1024
LT = 'paper/evidence/locked_test_20261109'
BT = 'writing/research/enzyextract_broad_20261118'
PT = 'writing/research/people_anchored_20261118'
TAG = 'paper-catalog-freeze-20261116'
SI = 'work/top_journal_20261021/benchmarks/enzyextract_si/data'  # EnzyExtract's supplementary files (SI.zip)
H2H_DATA = 'work/top_journal_20261021/h2h/data'                 # the head-to-head's TSV copies of the SI's runs
SI_FILES = {  # name in the records -> (path in the SI, sha256 the tests checked; None: printed, not checked)
    'TheData.parquet': ('dataset_crude_database/TheData.parquet',
                        '903023a9ec5366a4a560c1e11b5f6dca9ef5a27a6686ef633e7297866126290b'),
    'manual_curated_runeem_dataset.csv': ('dataset_223_EnzyExtract_BRENDA_manual_curation/manual_curated_runeem_dataset.csv',
                                          '37b2ff4cde194521a1afa247dfd4c29bf9eebfc1d4cb9a566e10dfb03a7b68ca'),
    'rumble_RGF_dev1.parquet': ('dataset_384_pipeline_benchmark_dataset/rumble_RGF_dev1.parquet', None),
}
METRICS = ('kcat', 'Km', 'kcat/Km')
UNIT = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}
EE_COL = {'kcat': 'kcat', 'Km': 'km', 'kcat/Km': 'kcat_km'}
RUN, MAX_QUOTE = 8, 25  # rule 2

# (path under tests/, commit, path in CATLOG): each plan as committed. The README of each test gives the commit that
# registered it, every later commit that changed it and the commit of its first result; main() prints them from git.
PLANS = [
    ('locked_test/PLAN.md', '41464f3a', f'{LT}/PLAN.md'),
    ('locked_test/PREREGISTRATION.md', '8bfc6be8', f'{LT}/PREREGISTRATION.md'),
    ('locked_test/PREREGISTRATION.as_registered.md', '708f4b38', f'{LT}/PREREGISTRATION.md'),
    ('locked_test_stage2/STAGE2.md', '41d125f9', f'{LT}/STAGE2.md'),
    ('locked_test_stage2/CHECK_PLAN.md', '1e7f176d', f'{LT}/stage2/CHECK_PLAN.md'),
    ('locked_test_stage2/CHECK_PLAN.as_registered.md', '0cf7f0d2', f'{LT}/stage2/CHECK_PLAN.md'),
    ('enzyextract_broad/PLAN.md', 'c9df8667', f'{BT}/PLAN.md'),
    ('enzyextract_broad/PLAN.as_registered.md', 'cd4cbe00', f'{BT}/PLAN.md'),
    ('enzyextract_broad/judge_prompt.md', 'c9df8667', f'{BT}/judge_prompt.md'),
    ('people_anchored/PLAN.md', 'ce89e0a6', f'{PT}/PLAN.md'),
    ('random_test/FULL_RECORD_PLAN.md', 'f8b0afdf', 'paper/evidence/random_papers_20261104/FULL_RECORD_PLAN.md'),
]
# (path under tests/, path in CATLOG at HEAD, kind): 'doc' a report (DOC_RULES, then checked), 'agg' a scorer's JSON
# (aggregates), 'raw' a registered input (byte for byte: the plan gives its sha256), 'code' a scorer (path rules)
FROM_HEAD = [
    ('locked_test/RESULTS.md', f'{LT}/result/RESULTS.md', 'doc'),
    ('locked_test/results.json', f'{LT}/result/results.json', 'agg'),
    ('locked_test/sensitivity_read_once/RESULTS.md', f'{LT}/result/sensitivity_read_once/RESULTS.md', 'doc'),
    ('locked_test/sensitivity_read_once/results.json', f'{LT}/result/sensitivity_read_once/results.json', 'agg'),
    ('locked_test/sensitivity_without_misprint_papers/RESULTS.md',
     f'{LT}/result/sensitivity_without_misprint_papers/RESULTS.md', 'doc'),
    ('locked_test/sensitivity_without_misprint_papers/results.json',
     f'{LT}/result/sensitivity_without_misprint_papers/results.json', 'agg'),
    ('locked_test_stage2/RESULTS.md', f'{LT}/stage2/RESULTS.md', 'doc'),
    ('locked_test_stage2/results.json', f'{LT}/stage2/results.json', 'agg'),
    ('locked_test_stage2/page_check/RESULTS.md', f'{LT}/stage2/checked/RESULTS.md', 'doc'),
    ('locked_test_stage2/page_check/results.json', f'{LT}/stage2/checked/results.json', 'agg'),
    ('locked_test_stage2/corrected/RESULTS.md', f'{LT}/stage2/corrected/RESULTS.md', 'doc'),
    ('locked_test_stage2/corrected/table.json', f'{LT}/stage2/corrected/table.json', 'agg'),
    ('locked_test_stage2/corrected/counts.json', f'{LT}/stage2/corrected/counts.json', 'agg'),
    ('locked_test_stage2/corrected/f6_pagecheck.json', f'{LT}/stage2/corrected/f6_pagecheck.json', 'agg'),
    ('locked_test_stage2/corrected/page_check/RESULTS.md', f'{LT}/stage2/corrected/checked/RESULTS.md', 'doc'),
    ('locked_test_stage2/corrected/page_check/results.json', f'{LT}/stage2/corrected/checked/results.json', 'agg'),
    ('locked_test_stage2/score_corrected.py', f'{LT}/stage2/score_corrected.py', 'code'),
    ('enzyextract_broad/CORRECTIONS.md', f'{BT}/CORRECTIONS.md', 'doc'),
    ('enzyextract_broad/frame.tsv', f'{BT}/frame.tsv', 'raw'),
    ('enzyextract_broad/order.txt', f'{BT}/order.txt', 'raw'),
    ('enzyextract_broad/frame_summary.json', f'{BT}/frame_summary.json', 'agg'),
    ('enzyextract_broad/sample_300.txt', f'{BT}/run/sample_300.txt', 'raw'),
    ('enzyextract_broad/key.json', f'{BT}/run/key.json', 'raw'),
    ('enzyextract_broad/RESULTS.md', f'{BT}/run/RESULTS.md', 'doc'),
    ('enzyextract_broad/results.json', f'{BT}/run/results.json', 'agg'),
    ('enzyextract_broad/corrected/RESULTS.md', f'{BT}/corrected/RESULTS.md', 'doc'),
    ('enzyextract_broad/corrected/results.json', f'{BT}/corrected/results.json', 'agg'),
    ('enzyextract_broad/corrected/corrections_table.md', f'{BT}/corrected/corrections_table.md', 'doc'),
    ('enzyextract_broad/corrected/corrections.json', f'{BT}/corrections.json', 'agg'),
    ('enzyextract_broad/power_results.json', f'{BT}/power_results.json', 'agg'),
    ('enzyextract_broad/build.py', f'{BT}/build.py', 'code'),
    ('enzyextract_broad/run_judges.py', f'{BT}/run_judges.py', 'code'),
    ('enzyextract_broad/score_corrected.py', f'{BT}/score_corrected.py', 'code'),
    ('enzyextract_broad/corrections.py', f'{BT}/corrections.py', 'code'),
    ('enzyextract_broad/power.py', f'{BT}/power.py', 'code'),
    ('people_anchored/results.json', f'{PT}/results.json', 'agg'),
    ('people_anchored/results_v2.json', f'{PT}/results_v2.json', 'agg'),
    ('people_anchored/build.py', f'{PT}/build.py', 'code'),
    ('people_anchored/build_v2.py', f'{PT}/build_v2.py', 'code'),
]
# from KIT's disk (the kit's records are not in git): the random test's reports
FROM_KIT = [
    ('random_test/RESULTS.md', 'records/score_randfull/RESULTS.md', 'doc'),
    ('random_test/results.json', 'records/score_randfull/results.json', 'agg'),
    ('random_test/comparison.json', 'records/score_randfull/comparison.json', 'agg'),
    ('random_test/first_judging/RESULTS.md', 'records/score_rand/RESULTS.md', 'doc'),
    ('random_test/first_judging/results.json', 'records/score_rand/results.json', 'agg'),
]
# a JSON list of dicts that stays in an aggregate: (path under tests/, its key path)
KEEP_LISTS = {('enzyextract_broad/corrected/corrections.json', '.entries')}


class Rule:
    """files: fnmatch patterns under tests/; find: a regex; repl: text or a function of the match; count: how often it
    must match in those files together (None: at least once)."""
    def __init__(self, files, find, repl, count=None, why=''):
        self.files, self.rx, self.repl, self.count, self.why = files, re.compile(find), repl, count, why


PATH_RULES = [
    Rule(['*'], r'/[U]sers/[^/\s\'"`]+/Documents/catlog-v2', '<the CatLog folder>', None, 'the CatLog folder'),
    Rule(['*'], r'/[U]sers/[^/\s\'"`]+/Documents/kinetics-reading', '<the kit folder>', None, 'the kit folder'),
    Rule(['*'], r"Path\.home\(\) / 'Documents' / 'kinetics-reading'", "Path('<the kit folder>')", None, 'the kit folder'),
    Rule(['*'], r'/[U]sers/[^/\s\'"`]+', '<the home folder>', None, 'any other home folder'),
]


def ee_row(m):  # a DOC_RULES replacement: a database string of TheData.parquet named by its row (filled in main)
    return ROWREF[m.group(0)]


REF = ['HEAD']  # CATLOG's commit for every file not in PLANS (main() pins it)
ROWREF = {}  # exact text in CORRECTIONS.md -> its replacement, made in broad() from the database's own rows
DOC_RULES = [
    # the F5 table prints EnzyExtract's database strings: each becomes its row of TheData.parquet
    Rule(['enzyextract_broad/CORRECTIONS.md'], r'\| (23436726|32107312) \| `[^`]+` \|', ee_row, 11,
         "F5's table: EnzyExtract's strings become their rows"),
    Rule(['enzyextract_broad/CORRECTIONS.md'], r'for\n  example, 2\.15 × 10⁶ M⁻¹ s⁻¹ became',
         'for\n  example, one string (TheData.parquet row {row_2150}) became', 1,
         "F5's example: EnzyExtract's string becomes its row"),
    Rule(['enzyextract_broad/CORRECTIONS.md'], r'"8 µM\*" \(the footnote after the unit\)\n    and "13 1023 mM" '
         r'\(read as 1\.3 × 10²⁴\)', 'a cell whose unit a footnote mark follows\n    and a cell whose power of ten lost '
         'its caret (two cells of the runs, left out here)', 1, "two cells of EnzyExtract's runs become descriptions"),
    # the re-judging's plan names two accounts by their e-mail handles: left out
    Rule(['random_test/FULL_RECORD_PLAN.md'], r"the judges' account \S+[@] stood", "the judges' account stood", 1,
         "the judges' account handle left out"),
    Rule(['random_test/FULL_RECORD_PLAN.md'], r"signs the command line into \S+[@] \(", "signs the command line into "
         "the judges' account (", 1, "the command line's account handle left out"),
]


# ---------- small helpers ----------

def git(repo, *args, binary=False):
    r = subprocess.run(['git', '-C', str(repo), '--no-optional-locks', *args], capture_output=True)
    if r.returncode:
        sys.exit(f'git {" ".join(args)} in {repo}: {r.stderr.decode(errors="replace").strip()}')
    return r.stdout if binary else r.stdout.decode('utf-8')


def show(repo, ref, path, binary=False):
    return git(repo, 'show', f'{ref}:{path}', binary=binary)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(f):
    h = hashlib.sha256()
    with open(f, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jsonl(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def cell(x):
    if x is None:
        return ''
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, float):
        return repr(x)
    return re.sub(r'[\t\r\n]+', ' ', str(x)).strip()


def tsv(rows, cols):
    out = io.StringIO()
    out.write('\t'.join(cols) + '\n')
    for r in rows:
        out.write('\t'.join(cell(r.get(c)) for c in cols) + '\n')
    return out.getvalue()


def dumps(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False) + '\n'


def pkey(p):
    p = str(p)
    return (0, int(p)) if p.isdigit() else (1, p)


# ---------- rule 2: text copied from the paper ----------

WORD = re.compile(r'[A-Za-z0-9]+')


MICRO_U = re.compile(r'u(?=(?:m|l|g|mol|mmol|kat)$)')


def words(text):
    """The words of a text in lower case, after NFKC (ligatures, superscripts), with the micro sign left out and a
    unit's u prefix dropped, so that 'µM', a text layer's broken micro glyph before M, and a judge's 'uM' all read 'm'."""
    t = unicodedata.normalize('NFKC', text or '').replace('\u03bc', '')
    return [MICRO_U.sub('', w.lower(), count=1) for w in WORD.findall(t)]


class Papers:
    """The 8-word runs of each paper's text, to find text copied from it."""
    def __init__(self, finder):
        self.finder, self.cache, self.missing = finder, {}, set()

    def runs(self, pmid):
        pmid = str(pmid)
        if pmid not in self.cache:
            w = []
            files = [f for f in self.finder(pmid) if f.is_file()]
            if not files:
                self.missing.add(pmid)
            for f in files:
                w += words(f.read_text(errors='replace'))
            self.cache[pmid] = {hash(tuple(w[i:i + RUN])) for i in range(len(w) - RUN + 1)}
        return self.cache[pmid]


def copied(text, runs):
    """(words of text inside runs of RUN or more words found in the paper, the longest such run in words)."""
    w = words(text)
    covered = [False] * len(w)
    for i in range(len(w) - RUN + 1):
        if hash(tuple(w[i:i + RUN])) in runs:
            for j in range(i, i + RUN):
                covered[j] = True
    best = run = 0
    for c in covered:
        run = run + 1 if c else 0
        best = max(best, run)
    return sum(covered), best


LABEL, REASON, QUOTE = 'label', 'reason', 'quote'


class Scrub:
    """Rule 2 on one test's free-text fields; counts what it blanks."""
    def __init__(self, papers):
        self.papers, self.blanked, self.seen = papers, Counter(), Counter()

    def __call__(self, kind, field, text, pmid):
        text = cell(text)
        if not text:
            return ''
        self.seen[field] += 1
        if kind == QUOTE:
            ok = len(text.split()) <= MAX_QUOTE
        else:
            n, best = copied(text, self.papers.runs(pmid))
            ok = n <= MAX_QUOTE if kind == LABEL else best < RUN
        if not ok:
            self.blanked[field] += 1
        return text if ok else ''


# ---------- aggregates: a scorer's JSON without its per-value lists ----------

def counts_only(x):
    return isinstance(x, dict) and all(k == 'pmid' or v is None or (isinstance(v, (int, bool)) and not isinstance(v, float))
                                       for k, v in x.items())


def aggregates(o, dest, path='', dropped=None):
    if isinstance(o, dict):
        return {k: aggregates(v, dest, f'{path}.{k}', dropped) for k, v in o.items()}
    if isinstance(o, list):
        dicts = [x for x in o if isinstance(x, dict)]
        if dicts and (dest, path) not in KEEP_LISTS and not all(counts_only(x) for x in dicts):
            if dropped is not None:
                dropped.append(f'{path} ({len(o)})')
            return f'[{len(o)} per-value entries left out here: the records are in the TSV files beside this file]'
        return [aggregates(x, dest, f'{path}[]', dropped) for x in o]
    return o


# keys that hold a value, a cell or an agent's words: never in an aggregate
VALUE_KEYS = {'value', 'values_list', 'cell', 'raw', 'raw_unit', 'quote', 'descriptor', 'evidence', 'reason',
              'right_value', 'ee_value', 'enzyextract_raw', 'enzyextract_substrate', 'into_value', 'as_written',
              'catlog_value', 'judge_evidence', 'shown', 'stored', 'string', 'enzyme', 'substrate', 'organism'}
KINETIC_CELL = re.compile(r'\d\s*(?:(?:×|x)\s*10\^?[-−]?\d+\s*)?(?:±\s*[\d.]+\s*)?(?:s\^-1|s⁻¹|min\^-1|min⁻¹|mM\^-1|mM⁻¹|'
                          r'µM|μM|uM|nM|M\^-1|M⁻¹)')


def json_value_keys(o, path=''):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            if k in VALUE_KEYS and v not in (None, '', [], {}):
                out.append(f'{path}.{k}')
            out += json_value_keys(v, f'{path}.{k}')
    elif isinstance(o, list):
        for x in o:
            out += json_value_keys(x, f'{path}[]')
    elif isinstance(o, str) and KINETIC_CELL.search(o):
        out.append(f'{path} (a string with a kinetic unit)')
    return out


# ---------- the judged tests: locked (2026-11-09) and random (2026-11-04, judged again 2026-11-06) ----------

CODE_ALPHABET = 'bcdfghjkmnpqrstvxz23456789'
JUDGES = ('j1', 'j2', 'j3')
W1_VERDICTS = ('supported', 'wrong_number', 'wrong_scale', 'wrong_metric', 'wrong_identity', 'wrong_conditions',
               'not_measured_here', 'not_printed', 'cannot_decide')  # score_w1.VERDICTS


def code(label):
    """common_w1.code: the folder name a session saw for an internal label."""
    h = int(hashlib.sha256(f'kinetics-reading/{label}'.encode()).hexdigest(), 16)
    out = ''
    for _ in range(6):
        h, r = divmod(h, len(CODE_ALPHABET))
        out += CODE_ALPHABET[r]
    return out


def klass(v):
    return None if v is None else 'supported' if v == 'supported' else 'cannot_decide' if v == 'cannot_decide' else 'error'


def final_verdict(v1, v2, v3=None):
    """score_w1.final_verdict, as committed at the kit's f3e2a20: (final verdict or None, whether a third is needed)."""
    if v1 is None or v2 is None:
        return None, False
    if klass(v1) == klass(v2):
        return (v1 if v1 == v2 or klass(v1) != 'error' else 'mixed'), False
    if v3 is None:
        return None, True
    ks = [klass(v1), klass(v2), klass(v3)]
    win = [k for k in set(ks) if ks.count(k) >= 2]
    if not win:
        return 'cannot_decide', True
    if win[0] != 'error':
        return win[0], True
    errs = [v for v in (v1, v2, v3) if klass(v) == 'error']
    kinds = [k for k in set(errs) if errs.count(k) >= 2]
    return (kinds[0] if kinds else v3 if klass(v3) == 'error' else errs[0]), True


VALUE_COLS = ['source', 'value_id', 'pmid', 'metric', 'value', 'unit', 'raw_value', 'raw_unit', 'enzyme', 'organism',
              'variant', 'substrate', 'cosubstrate', 'pH', 'temperature_C', 'location', 'conditions', 'quote',
              'paired_with', 'pair_flag', 'reader_model', 'verifier_model', 'read_prompt', 'verify_prompt', 'task_prompt',
              'pipeline_commit']
CLAIM_COLS = ['claim_id', 'pmid', 'chunk', 'kind', 'planted', 'planted_from', 'twin_visible', 'source_shown', 'members',
              'partner', 'identity_flag', 'metric', 'value', 'unit', 'enzyme', 'organism', 'variant', 'substrate',
              'cosubstrate', 'pH', 'temperature_C', 'details', 'j1', 'j2', 'j3', 'final']
VERDICT_COLS = ['claim_id', 'pmid', 'chunk', 'judge', 'model', 'verdict', 'found_at', 'on_page_image', 'reason']


def judged_test(kit, which, rows_file, scrub, first=None, left_out=None):
    """{name: text} of one judging: values.tsv, claims.tsv, verdicts.tsv, repeats_dropped.tsv; and a summary."""
    rec = kit / 'records'
    priv = rec / f'score_{which}' / 'private'
    vals = json.loads((priv / 'values.json').read_text())
    cmap = jsonl(priv / 'claims_map.jsonl')
    rows = {r['row_id']: r for r in jsonl(rows_file)} if rows_file else {}
    pair = {}
    for a, b, flag in vals['pairs']:
        pair[a], pair[b] = (f'plain:{b}', flag), (f'catlog:{a}', flag)
    out, info = {}, {}
    vrows, missing_rows = [], 0
    for side in ('plain', 'catlog'):
        for v in vals[side]:
            r = rows.get(v['id']) if side == 'catlog' else None
            if side == 'catlog' and r is None:
                missing_rows += 1
            p = v['pmid']
            vrows.append({
                'source': side, 'value_id': v['id'], 'pmid': p, 'metric': v['metric'], 'value': v['value'],
                'unit': UNIT[v['metric']], 'raw_value': v.get('raw'), 'raw_unit': v.get('raw_unit'),
                'enzyme': scrub(LABEL, 'enzyme', v.get('enzyme'), p), 'organism': scrub(LABEL, 'organism', v.get('organism'), p),
                'variant': scrub(LABEL, 'variant', v.get('variant'), p),
                'substrate': scrub(LABEL, 'substrate', v.get('substrate'), p),
                'cosubstrate': scrub(LABEL, 'cosubstrate', v.get('cosub'), p), 'pH': v.get('pH'),
                'temperature_C': v.get('temp'), 'location': scrub(LABEL, 'location', v.get('where'), p),
                'conditions': scrub(LABEL, 'conditions', v.get('conditions'), p),
                'quote': scrub(QUOTE, 'quote', (r or {}).get('quote'), p),
                'paired_with': pair.get(v['id'], ('', ''))[0], 'pair_flag': pair.get(v['id'], ('', ''))[1],
                **{k: (r or {}).get(k) for k in ('reader_model', 'verifier_model', 'read_prompt', 'verify_prompt',
                                                  'task_prompt', 'pipeline_commit')}})
    out['values.tsv'] = tsv(vrows, VALUE_COLS)
    if (priv / 'dropped.jsonl').is_file():
        out['repeats_dropped.tsv'] = tsv([{'source': d['source'], 'kept': (d['kept'] or {}).get('id'),
                                           'dropped': (d['dropped'] or {}).get('id')} for d in jsonl(priv / 'dropped.jsonl')],
                                         ['source', 'kept', 'dropped'])
    V, vlist = defaultdict(dict), []
    chunk_of = {c['claim_id']: c['chunk'] for c in cmap}
    pmid_of = {c['claim_id']: c['pmid'] for c in cmap}
    for j in JUDGES:
        folder = kit / 'out' / code(f'verdicts-{j}-{which}')
        for f in sorted(folder.glob('*.json')):
            d = json.loads(f.read_text())
            for v in d.get('verdicts') or []:
                if not isinstance(v, dict):
                    continue
                cid = str(v.get('id'))
                p = pmid_of.get(cid, d.get('pmid'))
                if v.get('verdict') in W1_VERDICTS:
                    V[cid].setdefault(j, v['verdict'])
                vlist.append({'claim_id': cid, 'pmid': p, 'chunk': chunk_of.get(cid, f.stem.split('.')[-1]), 'judge': j,
                              'model': d.get('model'), 'verdict': v.get('verdict'),
                              'found_at': scrub(LABEL, 'found_at', v.get('found_at'), p),
                              'on_page_image': v.get('on_page_image'), 'reason': scrub(REASON, 'reason', v.get('reason'), p)})
    # score_randfull.finals_of: a claim of a judge step stopped by refusals is cannot_decide; a paper whose judge session
    # was refused or switched model leaves the analysis (the report's left_out names both)
    left_out = left_out or {}
    stopped = {str(p) for p in left_out.get('claims_cannot_decide_by_a_stopped_judge_session') or {}}
    whole = {str(p) for p in left_out.get('judge_session_refused_or_switched_whole_paper') or []}
    crows, finals, by_stop = [], Counter(), Counter()
    for c in cmap:
        s, p = c.get('shown') or {}, c['pmid']
        f = final_verdict(*(V[c['claim_id']].get(j) for j in JUDGES))[0]
        if f is None and p in stopped:
            f = 'cannot_decide'
            by_stop[p] += not c.get('decoy')  # the report counts the real claims
        if p not in whole:
            finals[('planted' if c.get('decoy') else 'real', f)] += 1
        row = {'claim_id': c['claim_id'], 'pmid': p, 'chunk': c['chunk'], 'kind': c['kind'], 'planted': c.get('decoy'),
               'planted_from': c.get('decoy_base'), 'twin_visible': c.get('twin_visible'),
               'source_shown': c.get('source_shown'),
               'members': ';'.join(f"{m['src']}:{m['id']}" for m in c.get('members') or []),
               'partner': ':'.join(c['partner']) if c.get('partner') else '', 'identity_flag': c.get('why'),
               'metric': s.get('metric', c.get('metric')), 'value': s.get('value'), 'unit': s.get('unit'),
               **{k: scrub(LABEL, k, s.get(k), p) for k in ('enzyme', 'organism', 'variant', 'substrate', 'cosubstrate')},
               'pH': s.get('pH'), 'temperature_C': s.get('temperature_C'),
               'details': scrub(LABEL, 'details', s.get('details'), p),
               **{j: V[c['claim_id']].get(j) for j in JUDGES}, 'final': f, 'in_analysis': p not in whole}
        if first is not None:
            row.update({'first_claim': c.get('first_claim'), 'first_final': c.get('first_final'),
                        'first_decision': c.get('first_decision')})
        crows.append(row)
    out['claims.tsv'] = tsv(crows, CLAIM_COLS + ['in_analysis'] + (['first_claim', 'first_final', 'first_decision']
                                                                   if first is not None else []))
    want = {str(k): v for k, v in (left_out.get('claims_cannot_decide_by_a_stopped_judge_session') or {}).items()}
    if dict(by_stop) != want:
        info['stopped'] = f'claims of stopped judge steps {dict(by_stop)}, the report {want}'
    out['verdicts.tsv'] = tsv(vlist, VERDICT_COLS)
    info.update({'values': Counter(r['source'] for r in vrows), 'catlog values without their row': missing_rows,
                 'claims': len(cmap), 'verdicts': len(vlist), 'finals': finals,
                 'papers': sorted(vals['papers'], key=pkey), 'triage': json.loads((priv / 'triage.json').read_text())})
    return out, info


def compare_finals(info, results, what, errors):
    if info.get('stopped'):
        errors.append(f"{what}: {info['stopped']}")
    real = Counter({k: n for (kind, k), n in info['finals'].items() if kind == 'real'})
    reported = Counter(results.get('claims_final') or {})
    if real != reported:
        errors.append(f'{what}: final verdicts recomputed {dict(real)}, results.json claims_final {dict(reported)}')
    planted = sum(n for (kind, k), n in info['finals'].items() if kind == 'planted')
    planted_err = sum(n for (kind, k), n in info['finals'].items() if kind == 'planted' and klass(k) == 'error')
    return f'{what}: {sum(real.values())} real claims, finals as results.json; planted {planted}, judged errors {planted_err}'


def locked(kit, catlog, scrub, errors, notes):
    res = json.loads(show(catlog, REF[0], f'{LT}/result/results.json'))
    out, info = judged_test(kit, 'locked', kit / 'records/score_locked/private/catalog_rows.jsonl', scrub,
                            left_out=res.get('left_out'))
    notes.append(compare_finals(info, res, 'locked test', errors))
    draw = [x.strip() for x in (kit / 'records/orders/locked_draw.txt').read_text().split() if x.strip()]
    twice = set((kit / 'records/locked_copy_read_twice.txt').read_text().split())
    failed = info['triage']['papers_failed']
    used = set(info['papers'])
    prow = []
    for i, p in enumerate(draw, 1):
        prow.append({'order': i, 'pmid': p, 'analysed': p in used, 'left_out': failed.get(p, '' if p in used else '?'),
                     'catlog_read_twice': p in twice})
    if any(r['left_out'] == '?' for r in prow):
        errors.append('locked test: a drawn paper neither analysed nor left out with a reason')
    out['drawn_papers.tsv'] = tsv(prow, ['order', 'pmid', 'analysed', 'left_out', 'catlog_read_twice'])
    # the pre-registered secondary: each side against EnzyExtract's manual curation (curation.json), by row
    cur = json.loads(show(catlog, REF[0], f'{LT}/result/curation.json'))
    crow = []
    for how, items in sorted(cur['gold_matched_by'].items()):
        for g in items:
            crow.append(curation_row(g, how, errors))
    for g in cur.get('gold_unscored') or []:
        crow.append(curation_row(g, 'unscored', errors))
    crow.sort(key=lambda r: (pkey(r['pmid']), r['curation_row'], METRICS.index(r['metric'])))
    out['curation_matches.tsv'] = tsv(crow, ['curation_file', 'curation_row', 'pmid', 'metric', 'matched_by',
                                             'plain_value_id', 'catlog_value_id'])
    notes.append(f"locked test: values {dict(info['values'])}, claims {info['claims']}, verdicts {info['verdicts']}, "
                 f"papers drawn {len(draw)}, analysed {len(used)}, curation values {len(crow)}; catlog values without "
                 f"their row {info['catlog values without their row']}")
    return {f'locked_test/{k}': v for k, v in out.items()}, set(draw)


def curation_row(g, how, errors):
    m = re.fullmatch(r'ee_manual(\d+):(kcat|Km|kcat/Km)', str(g.get('id')))
    if not m:
        errors.append(f'curation.json: an id that is not a curation row ({g.get("id")!r})')
        return {'pmid': g.get('pmid', ''), 'curation_row': -1, 'metric': 'kcat'}
    ids = lambda x: ';'.join(i.get('id', '') if isinstance(i, dict) else str(i) for i in x) if isinstance(x, list) else \
        (x.get('id') if isinstance(x, dict) else x)
    return {'curation_file': 'manual_curated_runeem_dataset.csv', 'curation_row': int(m.group(1)), 'pmid': g['pmid'],
            'metric': m.group(2), 'matched_by': how, 'plain_value_id': ids(g.get('plain')),
            'catlog_value_id': ids(g.get('catlog'))}


def random_test(kit, scrub, errors, notes):
    rows_file = kit / 'records/score_rand/private/catalog_rows.jsonl'
    res = json.loads((kit / 'records/score_randfull/results.json').read_text())
    out, info = judged_test(kit, 'randfull', rows_file, scrub, first=True, left_out=res.get('left_out'))
    notes.append(compare_finals(info, res, 'random test', errors))
    res1 = json.loads((kit / 'records/score_rand/results.json').read_text())
    first, finfo = judged_test(kit, 'rand', rows_file, scrub, left_out=res1.get('left_out'))
    notes.append(compare_finals(finfo, res1, 'random test, first judging', errors))
    if first['values.tsv'] != out['values.tsv']:
        errors.append('random test: the two judgings do not judge the same values')
    used = set(res.get('per_paper') or {})
    failed = info['triage'].get('papers_failed') or {}
    left = res.get('left_out') or {}
    why_left = {}
    for k, v in left.items():
        for p in (v if isinstance(v, list) else list(v) if isinstance(v, dict) else []):
            why_left[str(p)] = k
    prow = [{'pmid': p, 'analysed': p in used, 'left_out': failed.get(p) or why_left.get(p, '' if p in used else '?')}
            for p in sorted(set(info['papers']) | set(failed), key=pkey)]
    if any(r['left_out'] == '?' for r in prow):
        errors.append('random test: a paper neither analysed nor left out with a reason')
    out['drawn_papers.tsv'] = tsv(prow, ['pmid', 'analysed', 'left_out'])
    res_out = {f'random_test/{k}': v for k, v in out.items()}
    res_out.update({f'random_test/first_judging/{k}': v for k, v in first.items() if k in ('claims.tsv', 'verdicts.tsv')})
    notes.append(f"random test: values {dict(info['values'])}, claims {info['claims']} (first judging {finfo['claims']}), "
                 f"papers {len(prow)}, analysed {len(used)}; catlog values without their row "
                 f"{info['catlog values without their row']}")
    return res_out, set(info['papers'])


# ---------- the locked test's second stage: the page check of the disputed values ----------

def ee_frame(path, sep=','):
    import pandas as pd
    return pd.read_csv(path, sep=sep, dtype=str)


def ee_cands(df, p):
    """(row, {metric, raw, enzyme, substrate, variant}) of a paper's cells, in the order h2h_s06.rows_to_values reads them."""
    out = []
    for k, r in df.iterrows():
        if str(r['pmid']).strip() != p:
            continue
        g = lambda c: r[c] if c in r and isinstance(r[c], str) else ''
        base = {'enzyme': f"{g('enzyme')} {g('enzyme_full')}".strip()[:120],
                'substrate': f"{g('substrate')} {g('substrate_full')}".strip()[:120], 'variant': g('mutant').strip()[:80]}
        for m in METRICS:
            raw = g(EE_COL[m])
            if raw.strip() and raw.strip().lower() not in ('none', 'nan', 'null'):
                out.append((int(k), {**base, 'metric': m, 'raw': raw}))
    return out


def align(shown, cands, same):
    """Each shown value takes the first remaining candidate that is the same, in order: the loaders skip unreadable
    cells and exact repeats but never reorder. None when one cannot be placed."""
    out, j = [], 0
    for t in shown:
        while j < len(cands) and not same(t, cands[j][1]):
            j += 1
        if j == len(cands):
            return None
        out.append(cands[j][0])
        j += 1
    return out


def same_ee(t, c):
    return (t['metric'] == c['metric'] and t['cell_as_this_reading_wrote_it'] == c['raw']
            and t.get('enzyme', '') == c['enzyme'] and t.get('substrate', '') == c['substrate']
            and t.get('variant', '') == c['variant'])


def same_catlog(t, c):
    return (t['metric'] == c['metric'] and abs(float(t['value_in_catalog_units']) - float(c['value'])) <= 1e-9 * max(1.0, abs(float(c['value'])))
            and t['cell_as_this_reading_wrote_it'] == f"{c.get('raw')} {c.get('raw_unit') or ''}".strip())


def same_rows(tsv_path, parquet_path, errors, what):
    """The head-to-head's TSV copy has the SI file's rows in the SI file's order (pmid and kcat cells compared)."""
    import pandas as pd
    a = pd.read_csv(tsv_path, sep='\t', dtype=str, keep_default_na=False)  # 'NA' and 'None' stay strings, as in the SI
    b = pd.read_parquet(parquet_path)
    norm = lambda s: s.map(lambda x: '' if x is None or (isinstance(x, float) and x != x) else str(x).strip())
    if len(a) != len(b) or not (norm(a['pmid']) == norm(b['pmid'])).all() or not (norm(a['kcat']) == norm(b['kcat'])).all():
        errors.append(f'{what}: the TSV copy does not have the SI file\'s rows in order')


def page_check(catlog, kit, scrub, errors, notes):
    sid = kit / 'records' / 'stage2_check'
    key = json.loads((sid / '_key.json').read_text())
    parts = json.loads((sid / '_papers.json').read_text())
    vals = json.loads((kit / 'records/score_locked/private/values.json').read_text())
    cur = ee_frame(catlog / SI / SI_FILES['manual_curated_runeem_dataset.csv'][0])
    rgf_tsv = catlog / H2H_DATA / 'rumble_RGF_dev1.tsv'
    same_rows(rgf_tsv, catlog / SI / SI_FILES['rumble_RGF_dev1.parquet'][0], errors, 'RGF run')
    rgf = ee_frame(rgf_tsv, '\t')
    runs = {}

    def run_frame(src):  # 'run_<RUN>' -> (its rows, its SI file), the TSV copy checked against the SI file once
        name = src[len('run_'):]
        if name not in runs:
            t, pq = catlog / H2H_DATA / f'rumble_{name}_dev1.tsv', f'rumble_{name}_dev1.parquet'
            same_rows(t, catlog / SI / 'dataset_384_pipeline_benchmark_dataset' / pq, errors, f'{name} run')
            runs[name] = (ee_frame(t, '\t'), pq)
        return runs[name]
    rows, keyout, unplaced = [], {}, []
    for p in sorted(key, key=pkey):
        task = json.loads(show(catlog, REF[0], f'{LT}/stage2/checked/tasks/{p}.task.json'))
        if (sid / f'{p}.task.json').is_file() and json.loads((sid / f'{p}.task.json').read_text()) != task:
            errors.append(f'page check {p}: the committed task differs from the one the agent read')
        checks = {}
        for n in (1, 2):
            path = f'{LT}/stage2/checked/verdicts/{p}.check{n}.json'
            if git(catlog, 'ls-files', path).strip():
                checks[n] = {str(v.get('id')): v for v in json.loads(show(catlog, REF[0], path)).get('verdicts') or []}
        keyout[p] = key[p]['order']
        for letter, src in key[p]['order'].items():
            shown = task[f'reading_{letter}']
            if src == 'catlog':
                cands = [(v['id'], v) for v in vals['catlog'] if v['pmid'] == p]
                refs = align(shown, cands, same_catlog)
                refs = refs and [f'catlog:{r}' for r in refs]
            else:
                df, name = (cur, 'manual_curated_runeem_dataset.csv') if src == 'curation' else (rgf, 'rumble_RGF_dev1.parquet')
                refs = align(shown, ee_cands(df, p), same_ee)
                refs = refs and [f'{name} row {r}' for r in refs]
            if refs is None:
                unplaced.append(f'{p} {letter} ({src})')
                continue
            for t, ref in zip(shown, refs):
                row = {'pmid': p, 'reading_id': t['id'], 'source': src, 'value_ref': ref, 'metric': t['metric'],
                       'judged': t.get('judge')}
                for n, vs in checks.items():
                    v = vs.get(t['id']) or {}
                    row[f'check{n}_verdict'] = v.get('verdict')
                    row[f'check{n}_right_value'] = scrub(LABEL, 'right_value', v.get('right_value'), p)
                    row[f'check{n}_evidence'] = scrub(REASON, 'evidence', v.get('evidence'), p)
                rows.append(row)
    if unplaced:
        errors.append(f'page check: {len(unplaced)} readings whose values could not be placed: {unplaced[:5]}')
    cols = ['pmid', 'reading_id', 'source', 'value_ref', 'metric', 'judged'] + [
        f'check{n}_{k}' for n in (1, 2) for k in ('verdict', 'right_value', 'evidence')]
    judged = Counter(r['source'] for r in rows if r['judged'])
    with_verdict = sum(1 for r in rows if r['judged'] and r.get('check1_verdict'))
    notes.append(f'page check: {len(keyout)} papers, {len(rows)} values shown, judged {dict(judged)}, '
                 f'judged with a first verdict {with_verdict}')
    out = {'locked_test_stage2/page_check/values.tsv': tsv(rows, cols),
           'locked_test_stage2/page_check/key.json': dumps({'readings': keyout, 'parts': parts})}
    # the corrected reader's changed cells (corrected/table.json changed_cells), by row
    table = json.loads(show(catlog, REF[0], f'{LT}/stage2/corrected/table.json'))
    crow = []
    for c in table.get('changed_cells') or []:
        if c['source'] == 'enzyextract_db':  # the database: its rows of TheData.parquet
            D = thedata(catlog, errors)
            name = 'TheData.parquet'
            hits = [i for i in D['idx'].get(c['pmid'], []) if D['cells'][i][METRICS.index(c['metric'])] == c['cell']]
        else:
            df, name = (cur, 'manual_curated_runeem_dataset.csv') if c['source'] == 'curation' else run_frame(c['source'])
            hits = [k for k, x in ee_cands(df, c['pmid']) if x['metric'] == c['metric'] and x['raw'] == c['cell']]
        if not hits:
            errors.append(f"corrected/table.json: a changed cell of {c['source']} {c['pmid']} not found in {name}")
        crow.append({'source': c['source'], 'pmid': c['pmid'], 'metric': c['metric'], 'kind': c.get('kind'),
                     'file': name, 'rows': ';'.join(map(str, sorted(set(hits)))),
                     'read_before': 'yes' if c.get('registered') is not None else 'no',
                     'read_now': 'yes' if c.get('as_written') is not None else 'no'})
    out['locked_test_stage2/corrected/changed_cells.tsv'] = tsv(crow, ['source', 'pmid', 'metric', 'kind', 'file', 'rows',
                                                                       'read_before', 'read_now'])
    return out


# ---------- the broad test against EnzyExtract's database ----------

THEDATA = {}


def thedata(catlog, errors):
    """{'idx': {paper: [row of TheData.parquet, ...]}, 'cells': [(kcat, km, kcat_km) of each row]}: build.py frame()'s
    grouping of the rows of its TSV copy (work/.../thedata.tsv, written from the parquet in order), made once."""
    if THEDATA:
        return THEDATA
    st, doi = papers_at_tag(catlog)
    path = catlog / 'work/enzyextract_broad_20261118/thedata.tsv'
    summ = json.loads(show(catlog, REF[0], f'{BT}/frame_summary.json'))
    if sha_file(path) != summ['inputs_sha256']['thedata.tsv']:
        errors.append('thedata.tsv: not the copy the frame was made from')
    idx, cells = defaultdict(list), []
    with open(path) as f:
        for i, r in enumerate(csv.DictReader(f, delimiter='\t')):
            cells.append((r['kcat'].strip(), r['km'].strip(), r['kcat_km'].strip()))
            k = r['pmid'].strip()
            p = k if k in st else doi.get(k.lower())
            if p:
                idx[p].append(i)
    import pyarrow.parquet as pq
    if pq.ParquetFile(catlog / SI / SI_FILES['TheData.parquet'][0]).metadata.num_rows != len(cells):
        errors.append('thedata.tsv: not as many rows as TheData.parquet')
    THEDATA.update(idx=idx, cells=cells)
    return THEDATA


def papers_at_tag(catlog):
    rows = list(csv.DictReader(show(catlog, TAG, 'papers.tsv').splitlines(), delimiter='\t'))
    st = {r['pmid']: r for r in rows}
    doi = {}
    for r in rows:
        d = (r.get('doi') or '').strip().lower()
        if d:
            doi[d] = r['pmid']
            doi[d.replace('/', '_')] = r['pmid']
    return st, doi


def ee_ref(idx, p, vid, errors):
    m = re.fullmatch(r'e(\d+):(kcat|Km|kcat/Km)', vid)
    if not m or int(m.group(1)) >= len(idx.get(p, [])):
        errors.append(f'broad test {p}: an EnzyExtract value id that names no row ({vid!r})')
        return ''
    return f'TheData.parquet row {idx[p][int(m.group(1))]}'


BROAD_VALUE_COLS = ['source', 'value_id', 'pmid', 'metric', 'value', 'unit', 'raw_value', 'raw_unit', 'enzyme', 'organism',
                    'variant', 'substrate', 'cosubstrate', 'pH', 'temperature_C', 'location', 'conditions', 'quote',
                    'record', 'how_read', 'agreed_with']


def broad(catlog, scrub, errors, notes):
    idx, cells = thedata(catlog, errors)['idx'], thedata(catlog, errors)['cells']
    fv = json.load(gzip.open(catlog / 'work/enzyextract_broad_20261118/frame_values.json.gz'))
    sample = show(catlog, REF[0], f'{BT}/run/sample_300.txt').split()
    key = json.loads(show(catlog, REF[0], f'{BT}/run/key.json'))
    if sorted(key, key=pkey) != sorted(sample, key=pkey):
        errors.append('broad test: the key and the sample name different papers')
    vrows, refs = [], {}
    for p in sorted(sample, key=pkey):
        d = fv[p]
        ref = {'catlog': [v['id'] for v in d['catlog']], 'enzyextract': [ee_ref(idx, p, v['id'], errors) for v in d['enzyextract']]}
        refs[p] = ref
        agreed = {('catlog', a): ref['enzyextract'][b] for a, b in d['pairs']}
        agreed.update({('enzyextract', b): f"catlog:{ref['catlog'][a]}" for a, b in d['pairs']})
        for i, v in enumerate(d['catlog']):
            vrows.append({'source': 'catlog', 'value_id': v['id'], 'pmid': p, 'metric': v['metric'], 'value': v['value'],
                          'unit': UNIT[v['metric']], 'raw_value': v.get('raw'), 'raw_unit': v.get('raw_unit'),
                          **{k: scrub(LABEL, k, v.get(k), p) for k in ('enzyme', 'organism', 'variant', 'substrate')},
                          'cosubstrate': scrub(LABEL, 'cosubstrate', v.get('cosub'), p), 'pH': v.get('pH'),
                          'temperature_C': v.get('temp'), 'location': scrub(LABEL, 'location', v.get('where'), p),
                          'conditions': scrub(LABEL, 'conditions', v.get('conditions'), p),
                          'quote': scrub(QUOTE, 'quote', v.get('quote'), p), 'record': v.get('record'),
                          'agreed_with': agreed.get(('catlog', i), '')})
        for i, v in enumerate(d['enzyextract']):
            vrows.append({'source': 'enzyextract', 'value_id': ref['enzyextract'][i], 'pmid': p, 'metric': v['metric'],
                          'how_read': v.get('how'), 'agreed_with': agreed.get(('enzyextract', i), '')})
    jrows = []
    for p in sorted(key, key=pkey):
        index = key[p]['index']
        for n, (task_name, check_name) in enumerate(key[p].get('parts') or [], 1):
            for agent, name in ((1, check_name), (2, check_name.replace('check1', 'check2'))):
                path = f'{BT}/run/judged/{p}/{name}'
                if agent == 2 and (name == check_name or not git(catlog, 'ls-files', path).strip()):
                    continue
                if not git(catlog, 'ls-files', path).strip():
                    errors.append(f'broad test {p}: {name} is not committed')
                    continue
                for v in json.loads(show(catlog, REF[0], path)).get('verdicts') or []:
                    rid = str(v.get('id'))
                    src, k = index.get(rid, ('', None))
                    jrows.append({'pmid': p, 'part': n, 'agent': agent, 'reading_id': rid, 'source': src,
                                  'value_ref': (f'catlog:{refs[p]["catlog"][k]}' if src == 'catlog' else refs[p]['enzyextract'][k])
                                  if k is not None else '',
                                  'metric': (fv[p][src][k]['metric'] if k is not None else ''), 'verdict': v.get('verdict'),
                                  'right_value': scrub(LABEL, 'right_value', v.get('right_value'), p),
                                  'evidence': scrub(REASON, 'evidence', v.get('evidence'), p)})
    if any(not r['value_ref'] for r in jrows):
        errors.append('broad test: a verdict on a reading id the key does not hold')
    n1 = sum(1 for r in jrows if r['agent'] == 1)
    notes.append(f"broad test: {len(sample)} papers; values {dict(Counter(r['source'] for r in vrows))}; verdicts "
                 f"{len(jrows)} (first agents {n1}, second agents {len(jrows) - n1})")
    # CORRECTIONS.md's F5 table: each EnzyExtract string by its row (DOC_RULES)
    for p in ('23436726', '32107312'):
        for line in show(catlog, REF[0], f'{BT}/CORRECTIONS.md').splitlines():
            m = re.match(rf'\| {p} \| `([^`]+)` \|', line)
            if m:
                hits = [i for i in idx.get(p, []) if cells[i][2] == m.group(1)]
                if not hits:
                    errors.append(f"CORRECTIONS.md: no row of TheData.parquet holds a string of {p}'s F5 table")
                ROWREF[m.group(0)] = f"| {p} | TheData.parquet row{'s' if len(hits) > 1 else ''} {', '.join(map(str, hits))} |"
                if m.group(1).startswith('2.15 × 10^6'):
                    ROWREF['row_2150'] = ', '.join(map(str, hits))
    return {'enzyextract_broad/values.tsv': tsv([r for r in vrows if r['source'] == 'catlog'], BROAD_VALUE_COLS[:-2]
                                                + ['agreed_with']),
            'enzyextract_broad/enzyextract_rows.tsv': tsv([r for r in vrows if r['source'] == 'enzyextract'],
                                                          ['source', 'value_id', 'pmid', 'metric', 'how_read', 'agreed_with']),
            'enzyextract_broad/verdicts.tsv': tsv(jrows, ['pmid', 'part', 'agent', 'reading_id', 'source', 'value_ref',
                                                          'metric', 'verdict', 'right_value', 'evidence'])}, set(sample)


# ---------- the person-anchored comparison ----------

def held_pairs(ref, src, tol):
    """people_anchored build.py held(), returning the pairs: {reference index: source index}."""
    out = {}
    for m in METRICS:
        R = [(i, r[1]) for i, r in enumerate(ref) if r[0] == m]
        Sv = [(j, s[1]) for j, s in enumerate(src) if s[0] == m]
        pairs = sorted((abs(s - rv) / rv, i, j) for i, rv in R for j, s in Sv if abs(s - rv) <= tol * rv)
        used_r, used_s = set(), set()
        for _, i, j in pairs:
            if i not in used_r and j not in used_s:
                used_r.add(i)
                used_s.add(j)
                out[i] = j
    return out


def people(catlog, scrub, errors, notes):
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):  # nothing the review code prints reaches this console
        spec = importlib.util.spec_from_file_location('people_build', catlog / PT / 'build.py')
        P = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(P)
        conf, bad, n_rec = P.reference()
        keep, why, ee_rows = P.papers(conf, bad)
        C = P.BROAD.common()
        cat = defaultdict(list)
        for ln in P.git_show('catalog.jsonl').splitlines():
            if ln.strip():
                r = json.loads(ln)
                if r.get('metric') in METRICS and P.catlog.molar(r) is not None and P.pos(r.get('value')):
                    cat[str(r['pmid'])].append(r)
        ev = {}
        for p in keep:
            vals, _ = P.BROAD.ee_values(C, ee_rows[p], p)
            ev[p] = P.BROAD.no_repeats(vals)
    idx = thedata(catlog, errors)['idx']
    rrows, vrows, n = [], [], Counter()
    for p in keep:
        csrc = [(r['metric'], float(r['value'])) for r in cat[p]]
        esrc = [(x['metric'], float(x['value'])) for x in ev[p]]
        for group, ref in (('confirmed', conf.get(p, [])), ('not found or wrong', bad.get(p, []))):
            hc, he = held_pairs(ref, csrc, P.TOL), held_pairs(ref, esrc, P.TOL)
            for i, r in enumerate(ref):
                n[(group, 'values')] += 1
                n[(group, 'catlog')] += i in hc
                n[(group, 'ee')] += i in he
                rrows.append({'pmid': p, 'metric': r[0], 'reference': group,
                              'database': r[2] if group == 'confirmed' else '', 'category': r[2] if group != 'confirmed' else '',
                              'held_by_catlog': f"catlog:{cat[p][hc[i]]['row_id']}" if i in hc else '',
                              'held_by_enzyextract': ee_ref(idx, p, ev[p][he[i]]['id'], errors) if i in he else ''})
        for r in cat[p]:
            vrows.append({'source': 'catlog', 'value_id': r['row_id'], 'pmid': p, 'metric': r['metric'], 'value': r['value'],
                          'unit': UNIT[r['metric']], 'raw_value': r.get('raw_value'), 'raw_unit': r.get('raw_unit'),
                          **{k: scrub(LABEL, k, r.get(k), p) for k in ('enzyme', 'organism', 'variant', 'substrate')},
                          'location': scrub(LABEL, 'location', r.get('location'), p),
                          'quote': scrub(QUOTE, 'quote', r.get('quote'), p)})
        for x in ev[p]:
            vrows.append({'source': 'enzyextract', 'value_id': ee_ref(idx, p, x['id'], errors), 'pmid': p,
                          'metric': x['metric'], 'how_read': x.get('how')})
    res = json.loads(show(catlog, REF[0], f'{PT}/results.json'))
    e1 = res['endpoint1_confirmed']
    got = (n[('confirmed', 'values')], n[('confirmed', 'catlog')], n[('confirmed', 'ee')])
    if got != (e1['values'], e1['catlog_held'], e1['ee_held']) or len(keep) != res['papers_scored']:
        errors.append(f'person-anchored: recomputed {got} on {len(keep)} papers, results.json '
                      f"{(e1['values'], e1['catlog_held'], e1['ee_held'])} on {res['papers_scored']}")
    notes.append(f'person-anchored: {len(keep)} papers; reference values {dict(n)}; values '
                 f"{dict(Counter(r['source'] for r in vrows))}")
    return {'people_anchored/reference.tsv': tsv(rrows, ['pmid', 'metric', 'reference', 'database', 'category',
                                                         'held_by_catlog', 'held_by_enzyextract']),
            'people_anchored/values.tsv': tsv([r for r in vrows if r['source'] == 'catlog'],
                                              ['source', 'value_id', 'pmid', 'metric', 'value', 'unit', 'raw_value',
                                               'raw_unit', 'enzyme', 'organism', 'variant', 'substrate', 'location', 'quote']),
            'people_anchored/enzyextract_rows.tsv': tsv([r for r in vrows if r['source'] == 'enzyextract'],
                                                        ['source', 'value_id', 'pmid', 'metric', 'how_read'])}, set(keep)


# ---------- checks ----------

FREE = {'enzyme': LABEL, 'organism': LABEL, 'variant': LABEL, 'substrate': LABEL, 'cosubstrate': LABEL,
        'location': LABEL, 'conditions': LABEL, 'details': LABEL, 'found_at': LABEL, 'quote': QUOTE, 'reason': REASON,
        'right_value': LABEL, 'evidence': REASON, 'check1_right_value': LABEL, 'check2_right_value': LABEL,
        'check1_evidence': REASON, 'check2_evidence': REASON}
EE_SOURCES = {'enzyextract', 'curation', 'rgf', 'enzyextract_db'} | {
    f'run_{r}' for r in ('4o-05', '4o-mini_Rx', '4o-mini', '4o-mini_xG', 'RGF', 'RxF', 'gemini', 'sonnet37', 'xGF')}
EE_ALLOWED = {'source', 'value_id', 'pmid', 'metric', 'how_read', 'agreed_with', 'reading_id', 'value_ref', 'judged',
              'part', 'agent', 'verdict', 'right_value', 'evidence', 'kind', 'file', 'rows', 'read_before',
              'read_now'} | {f'check{n}_{k}' for n in (1, 2) for k in ('verdict', 'right_value', 'evidence')}
# the broad test's registered inputs, with the sha256 its PLAN.md gives: published byte for byte
REGISTERED = {'enzyextract_broad/frame.tsv': '752405e7ec15db19473a2c7f9bd77a704643f376338e83da3d5bad71004dce44',
              'enzyextract_broad/order.txt': '0ab14f13aa47ad1d21bac5ac1c242706ee2e67758e2eb948d7e00ffbc240874d',
              'enzyextract_broad/sample_300.txt': '272a877e977a457f6251a0ccc2fccdc03ccbd1626f927f1182322604e412ab45',
              'enzyextract_broad/judge_prompt.md': 'c6247c778a30f45204780d6cc0eb05040492c85adc901f6bdabae2215bdb1048',
              'enzyextract_broad/key.json': '8d8e1e7d4fa24d05be0f7175a159fd32feb9a68213c9e5d10cf15020ea0ed1d0'}


def check(content, own, srcs, names, papers_of, held, drawn, errors):
    users = set().union(*(S.owner_names(s) for s in srcs))
    strict = [(S.anywhere(n), label) for n, label, _ in names]
    secrets = S.env_values(srcs[0])
    for path, text in sorted({**content, **own}.items()):
        if len(text.encode('utf-8')) > MAX_BYTES:
            errors.append(f'{path}: over 5 MB')
        for u in users:
            if re.search(re.escape(u), path + '\n' + text, re.I):
                errors.append(f"{path}: holds the source owner's user name")
        for rx, label in strict:
            k = len(rx.findall(path)) + len(rx.findall(text))
            if k:
                errors.append(f'{path}: holds a name from the names file {k} time(s) (labelled {label!r})')
        for where, v in secrets:
            if v in text:
                errors.append(f'{path}: holds the value of {where} (not shown)')
        test = path.split('/')[1] if path.count('/') >= 2 else ''
        for i, line in enumerate(text.splitlines(), 1):
            if any(not S.TEST_ADDRESS.search(e) for e in S.EMAIL_RX.findall(line)):
                errors.append(f'{path}:{i}: an e-mail address')
            if re.search(r'(?<![A-Za-z0-9._%+-])(?=[A-Za-z0-9._%+-]*[A-Za-z0-9]{3})[A-Za-z0-9._%+-]{3,}[@](?![A-Za-z0-9])', line):
                errors.append(f"{path}:{i}: an e-mail address's local part (a handle followed by @)")
            if re.search(r'/[U]sers/|/home/(?!x\b|s\b)[a-z]', line):
                errors.append(f'{path}:{i}: a home-folder path')
            for k in S.KEYS:
                if re.search(k, line):
                    errors.append(f'{path}:{i}: looks like a key ({k[:20]}...)')
            if held and path != 'sync_tests.py':
                ids_line = re.sub(r'\brows? \d+(?:, \d+)*', ' ', line)  # a row of a file is not a paper id
                if path.endswith('.tsv') and i > 1:
                    head = text.split('\n', 1)[0].split('\t')
                    ids_line = '\t'.join('' if h in ('curation_row', 'rows', 'order', 'part', 'agent') else x
                                         for h, x in zip(head, ids_line.split('\t')))
                hit = [t for t in S.PAPER_ID.findall(ids_line) if t.upper() in held and t not in drawn]
                if hit:
                    where = ''
                    if path.endswith('.tsv') and i > 1:
                        head = text.split('\n', 1)[0].split('\t')
                        f = line.split('\t')
                        where = ' in column ' + ', '.join(sorted({head[k] for k, x in enumerate(f) if any(h in x for h in hit)}))
                    errors.append(f'{path}:{i}: a held-out paper id the locked test did not draw{where}')
        if path.endswith('.py'):
            try:
                compile(text, path, 'exec', dont_inherit=True)
            except SyntaxError as e:
                errors.append(f'{path}: does not compile ({e})')
        if path.endswith('.json'):
            try:
                obj = json.loads(text)
            except ValueError as e:
                errors.append(f'{path}: not JSON ({e})')
                continue
            if path in AGG_PATHS:
                bad = json_value_keys(obj)
                if bad:
                    errors.append(f'{path}: an aggregate holds values or words: {bad[:4]}' + (f' (+{len(bad) - 4})' if len(bad) > 4 else ''))
        if path.endswith('.tsv'):
            lines = text.splitlines()
            head = lines[0].split('\t') if lines else []
            if any(len(line.split('\t')) != len(head) for line in lines):
                errors.append(f'{path}: not rectangular')
            if test in papers_of and 'pmid' in head:
                P = papers_of[test]
                at = {c: i for i, c in enumerate(head)}
                for line in lines[1:]:
                    f = line.split('\t')
                    p = f[at['pmid']]
                    src = f[at['source']] if 'source' in at else ''
                    if src in EE_SOURCES:
                        filled = [c for c in head if c not in EE_ALLOWED and f[at[c]]]
                        if filled:
                            errors.append(f'{path}: an EnzyExtract value with {filled[:3]} filled (paper {p})')
                    for c, kind in FREE.items():
                        if c in at and f[at[c]]:
                            t = f[at[c]]
                            if kind == QUOTE:
                                ok = len(t.split()) <= MAX_QUOTE
                            else:
                                k, best = copied(t, P.runs(p))
                                ok = k <= MAX_QUOTE if kind == LABEL else best < RUN
                            if not ok:
                                errors.append(f'{path}: column {c} of paper {p} breaks rule 2')
        if path.endswith('.md') and test in papers_of:
            P = papers_of[test]
            for p in sorted(P.cache, key=pkey):
                k, best = copied(text, P.runs(p))
                if best > MAX_QUOTE:
                    errors.append(f'{path}: a run of {best} words of paper {p}')


AGG_PATHS = set()


def managed(dest):
    out = set()
    if (dest / DEST).is_dir():
        for p in (dest / DEST).rglob('*'):
            rel = p.relative_to(dest).as_posix()
            if p.is_file() and not rel.endswith('/README.md') and not S.skipped(rel):
                out.add(rel)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--catlog', required=True, help="the authors' CatLog folder")
    ap.add_argument('--kit', required=True, help='the folder the locked and random tests ran in')
    ap.add_argument('--names', default='', help='private file of name<TAB>label lines; never in this repository')
    ap.add_argument('--dest', default=str(HERE), help='where to write (default: the folder of this script)')
    ap.add_argument('--check', action='store_true', help='make and check everything, write nothing')
    ap.add_argument('--ref', default='HEAD', help="CATLOG's commit for every file not in PLANS (default HEAD)")
    a = ap.parse_args()
    catlog, kit, dest = Path(a.catlog).resolve(), Path(a.kit).resolve(), Path(a.dest).resolve()
    if not (catlog / 'catlog.py').is_file() or not (kit / 'records' / 'score_locked').is_dir():
        sys.exit('--catlog needs catlog.py in it and --kit a records/score_locked/ folder')
    if not a.names or not Path(a.names).is_file():
        sys.exit('pass --names FILE (name<TAB>label per line; private, never in this repository): without it no name '
                 'is replaced, so nothing is written')
    names = S.read_names(a.names)
    errors, notes, content = [], [], {}
    caches = lambda: sorted(str(c) for top in ('tools', 'writing/research', 'paper/evidence') for c in (catlog / top).rglob('__pycache__'))
    caches_before = caches()
    head = git(catlog, 'rev-parse', a.ref).strip()
    REF[0] = head
    notes.append(f'CatLog folder at {a.ref}: commit {head}')
    for name, (rel, want) in SI_FILES.items():
        got = sha_file(catlog / SI / rel)
        notes.append(f'SI {name}: sha256 {got}' + ('' if want is None else ' (as the tests checked)' if got == want else ''))
        if want and got != want:
            errors.append(f'SI {name}: not the copy the tests checked')
    # the plans, as committed; and what git says of them
    for here, commit, there in PLANS:
        data = show(catlog, commit, there, binary=True)
        head = show(catlog, REF[0], there, binary=True)
        log = git(catlog, 'log', '--format=%h %cI', '--', there).split('\n')
        notes.append(f'plan {here}: as at {commit}, blob {git(catlog, "rev-parse", f"{commit}:{there}").strip()[:12]}; '
                     f"{'unchanged since' if data == head else 'CHANGED at HEAD since'}; commits: "
                     + ', '.join(x for x in log if x))
        content[f'{DEST}{here}'] = data.decode('utf-8')
    kinds = {}
    for here, there, kind in FROM_HEAD:
        content[f'{DEST}{here}'] = show(catlog, REF[0], there)
        kinds[f'{DEST}{here}'] = kind
    for here, there, kind in FROM_KIT:
        content[f'{DEST}{here}'] = (kit / there).read_text(encoding='utf-8')
        kinds[f'{DEST}{here}'] = kind
    # the records
    kit_texts = Papers(lambda p: [kit / 'papers' / p / 'paper.txt', kit / 'papers' / p / 'paper.supp.txt'])
    cat_texts = Papers(lambda p: [catlog / 'texts' / f'{p}.txt', catlog / 'texts' / f'{p}.supp.txt'])
    scrubs = {}
    made, drawn = locked(kit, catlog, scrubs.setdefault('locked_test', Scrub(kit_texts)), errors, notes)
    content.update({f'{DEST}{k}': v for k, v in made.items()})
    made = page_check(catlog, kit, scrubs.setdefault('locked_test_stage2', Scrub(kit_texts)), errors, notes)
    content.update({f'{DEST}{k}': v for k, v in made.items()})
    made, rand_papers = random_test(kit, scrubs.setdefault('random_test', Scrub(kit_texts)), errors, notes)
    content.update({f'{DEST}{k}': v for k, v in made.items()})
    made, broad_papers = broad(catlog, scrubs.setdefault('enzyextract_broad', Scrub(cat_texts)), errors, notes)
    content.update({f'{DEST}{k}': v for k, v in made.items()})
    made, people_papers = people(catlog, scrubs.setdefault('people_anchored', Scrub(cat_texts)), errors, notes)
    content.update({f'{DEST}{k}': v for k, v in made.items()})
    for test, sc in scrubs.items():
        notes.append(f'rule 2, {test}: blanked ' + (', '.join(f'{c} {sc.blanked[c]} of {sc.seen[c]}' for c in sorted(sc.seen)
                                                              if sc.blanked[c]) or 'nothing'))
    # aggregates, rules, names
    for path, kind in kinds.items():
        if kind == 'agg':
            dropped = []
            content[path] = dumps(aggregates(json.loads(content[path]), path[len(DEST):], '', dropped))
            AGG_PATHS.add(path)
            if dropped:
                notes.append(f'aggregates {path[len(DEST):]}: per-value lists left out: ' + ', '.join(dropped[:6])
                             + (f' (+{len(dropped) - 6})' if len(dropped) > 6 else ''))
    import fnmatch
    for here in [p for p, _, _ in PLANS] + list(REGISTERED):
        kinds.setdefault(f'{DEST}{here}', 'raw' if here in REGISTERED else 'plan')
    touched = Counter()
    for rule in DOC_RULES + PATH_RULES:
        n = 0
        for p in sorted(content):
            if kinds.get(p) == 'raw' or not any(fnmatch.fnmatchcase(p[len(DEST):], f) for f in rule.files):
                continue
            repl = rule.repl if callable(rule.repl) else rule.repl.format(**ROWREF) if '{' in rule.repl else rule.repl
            content[p], k = rule.rx.subn(repl, content[p])
            n += k
            if k and kinds.get(p) in ('plan', 'doc', 'code'):
                touched[p[len(DEST):]] += k
        if (n == 0 and rule.count is None and rule not in PATH_RULES) or (rule.count is not None and n != rule.count):
            errors.append(f'rule "{rule.why}" matched {n} times, not {rule.count or "one or more"}: the source changed')
        notes.append(f'rule "{rule.why}": {n}')
    for path in sorted(content):
        if path.endswith('.py'):
            content[path], k = S.contact(path, content[path], errors)
            if k:
                touched[path[len(DEST):]] += k
    labelled = Counter()
    for name, label, _ in names:
        rx = S.word(name)
        for p in sorted(content):
            if kinds.get(p) == 'raw':
                continue
            content[p], k = rx.subn(lambda m, text=label: text, content[p])
            labelled[label] += k
            if k:
                touched[p[len(DEST):]] += k
    notes.append('documents and scripts the rules changed (replacements): '
                 + (', '.join(f'{p} {k}' for p, k in sorted(touched.items())) or 'none'))
    for here, want in REGISTERED.items():
        if sha(content[f'{DEST}{here}'].encode('utf-8')) != want:
            errors.append(f'{here}: not the registered file (sha256 differs from PLAN.md)')
    own = {p: (dest / p).read_text(encoding='utf-8') for p in sorted(OWN) if (dest / p).is_file()}
    own.update({p.relative_to(dest).as_posix(): p.read_text(encoding='utf-8') for p in sorted((dest / DEST).rglob('README.md'))}
               if (dest / DEST).is_dir() else {})
    held = set()
    for f in sorted((catlog / 'sources').glob('holdout_*.txt')):  # read here, never copied
        held |= {w.upper() for line in f.read_text().splitlines() if not line.startswith('#') for w in line.split()}
    papers_of = {'locked_test': kit_texts, 'locked_test_stage2': kit_texts, 'random_test': kit_texts,
                 'enzyextract_broad': cat_texts, 'people_anchored': cat_texts}
    for t, ps in (('locked_test', drawn), ('random_test', rand_papers), ('enzyextract_broad', broad_papers),
                  ('people_anchored', people_papers)):
        for p in ps:
            papers_of[t].runs(p)
    for P in (kit_texts, cat_texts):
        if P.missing:
            errors.append(f'{len(P.missing)} papers have no text to check rule 2 against: {sorted(P.missing)[:5]}')
    check(content, own, [catlog, kit], names, {**papers_of}, held, drawn, errors)
    if caches() != caches_before:
        errors.append('this run left bytecode in the CatLog folder')
    for line in notes:
        print(line)
    print(f'{len(content)} files; names: ' + (', '.join(f'{label} {k}' for label, k in sorted(labelled.items()) if k)
                                              or 'none found'))
    print('checks: names, user name, e-mail, home paths, keys, .env values, sizes, compile, JSON, TSV shape, rule 2 '
          '(paper text), EnzyExtract and database values, held-out ids (own files too: '
          + ', '.join(sorted(own)) + ')')
    if errors:
        print(f'\n{len(errors)} problem(s); nothing written:', file=sys.stderr)
        for e in errors:
            print('  ' + e, file=sys.stderr)
        sys.exit(1)
    gone = sorted(managed(dest) - set(content))
    changed = sorted(p for p in content
                     if not (dest / p).is_file() or (dest / p).read_bytes() != content[p].encode('utf-8'))
    print(f'{len(changed)} files new or changed, {len(gone)} to remove' + (' (--check: nothing written)' if a.check else ''))
    for p in changed:
        print('  write ' + p)
    for p in gone:
        print('  remove ' + p)
    if a.check:
        return
    for p in changed:
        (dest / p).parent.mkdir(parents=True, exist_ok=True)
        (dest / p).write_text(content[p], encoding='utf-8')
    for p in gone:
        (dest / p).unlink()
    print('written; nothing committed: read `git diff`, then commit')


if __name__ == '__main__':
    main()
