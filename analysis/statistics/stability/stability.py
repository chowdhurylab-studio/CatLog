#!/usr/bin/env python3
"""Run-to-run stability of CatLog's frozen workflow (question 3 of the methods evidence).

The locked test's frozen copy (catlog-copy at fb0cf1758951) read 41 held-out papers in two launches, because an
operational stop discarded the first launch before its `add`. For the papers where both launches left a complete
reader file and verifier file, this script compares the two readings, at three stages:
  reader     the values the reader wrote;
  verifier   the values the verifier kept (confirmed, or fixed with its fix applied), plus the values it added as missed
             and its second check kept;
  stored     what CatLog's code checks store, from a replay of the frozen copy's own `add` on each launch's work files
             (the replay of the second launch must give back the rows the test stored, field for field, or it stops).

Papers. The question leaves out any paper whose second run could see the first run's files. The frozen task text sends
each agent to a scratch folder named by its role and paper (read-<PMID>, verify-<PMID>), the same names in both
launches, and the kit's reset moved each paper's non-image scratch aside with its file times. The main set is the papers
whose folders held no file written while the first launch ran, less any paper with a Sonnet retry (the locked test's
refusal exits). The wider set leaves out only the Sonnet-retry papers and the paper whose second verifier is recorded
opening the first verifier's files (the kit's leftover scan). The first launch's files were in the second launch's
folders for most of the wider set's papers; the exposure counts say how many and what was there.

Values are paired per paper and constant, one to one, on the printed cell (its number before any unit, within 1.5% of
the larger), a pair whose stored values also agree first, then the closest description, as the tests' matcher (the
head-to-head's) breaks ties: "in both" when the stored values agree within 1.5%, "conflicting" when they do not. Values
left on both sides are paired on the stored value (in both, the cell written otherwise), then on the description
(conflicting: another number for a measurement described alike). The rest are in one launch only, each with the reason
the other launch lacks it. The tests' own matcher run first (on the stored value) is kept as a cross-check. Censored
values (bounds, not detected) and values in mass units are compared apart, at each stage. Both launches are also scored
against EnzyExtract's manual curation with the locked test's stage-2 code.

Uses only records that exist; no agent, reading, judging or network call. Reads the kit (kinetics-reading) and the main
repository; writes only this folder and a scratch folder (--scratch, removed at the end unless --keep). Every count the
paper's files already print and this script meets again is asserted (PRINTED below): a mismatch stops it.

  python3 -I -B stability.py [--scratch DIR] [--keep]
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = Path('<the kit folder>')
MAIN = Path('<the CatLog folder>')
COPY = KIT / 'catlog-copy'                       # the frozen copy (its own one-commit repository)
REC = KIT / 'records'
RUN = REC / 'runs' / 'A6-locked'                 # the copy's kept run: work files, catalog, log
WORK = RUN / 'work'
SCRATCH = RUN / 'scratch' / 'tmp'                # the papers' non-image /tmp scratch, moved aside at the reset (times kept)
MKTEMP = REC / 'a6_tmp_leftovers'                # two second-launch verifiers' private mktemp folders, moved there
LOCKED = MAIN / 'paper' / 'evidence' / 'locked_test_20261109'
TWICE = LOCKED / 'result' / 'locked_copy_read_twice.txt'
TRIAGE = LOCKED / 'result' / 'triage.json'
PREREG = LOCKED / 'PREREGISTRATION.md'
SCAN_CODE = LOCKED / 'review' / 'auditfix' / 'leftover_scan.py'
STAGE2 = LOCKED / 'stage2'
VALUES = REC / 'score_locked' / 'private' / 'values.json'   # the values the locked test judged
AUDIT = REC / 'audit' / 'A6-locked' / 'audit.json'
LEFTOVER = REC / 'locked_leftover_scan.json'
LOGS = REC / 'logs' / 'A6-locked'
INPUTS = REC / 'a6_inputs_locked.json'
TASKJS = COPY / '.claude' / 'workflows' / 'catlog-batch.js'

FROZEN_COMMIT = 'fb0cf1758951'
OPUS = 'claude-opus-5-5'
TASK = ('.claude/workflows/catlog-batch.js', '.claude/agents/catlog-reader.md')   # catlog.TASK
PIPELINE = ('catlog.py', 'prompts', 'tools/units.py', *TASK)                      # catlog.PIPELINE
STD = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}                       # catalog units (the tests' values)
IMAGE = re.compile(r'\.(?:png|jpe?g|gif|tiff?|ppm|pgm|pbm|bmp)$', re.I)
STAGES = ('reader', 'verifier', 'stored')
# exposure: what a paper's scratch folders held (names only; no file is opened)
DRAFT = re.compile(r'^(?:draft[^/]*\.json|[^/]*\.read\.json|make_read[^/]*\.py|build[^/]*\.py)$')   # a draft read file or the script that builds one
VERDICT = re.compile(r'^(?:write_verdicts|write_verify|make_verdicts|make_verify)[^/]*\.py$')       # a verifier's verdict script
APART = re.compile(r'(?:^|[-_.])(?:own|mine|r2)(?:[-_.]|$)')                                          # a folder or file an agent marked as its own

# Counts the paper's files already print, met again here (a mismatch stops the script):
PRINTED = {
    # PLAN.md "What is frozen": the prompts and task text of the frozen copy
    'hashes': {'read.md': '86e5d7668c1c', 'verify.md': '6cdd7782a0f2', 'task': '369efeee4c39'},
    # PREREGISTRATION.md "Changes after it": 41 papers had agents in two launches: batch 3's 30, batch 2's 6, more-7's 5
    'read_twice': 41, 'read_twice_first_launch': {'more-3': 30, 'more-1': 6, 'more-7': 5},
    # ... and one re-reading agent opened a decision-carrying leftover: 9495750's verifier
    'exposed': ['9495750'],
    # ... and the verifiers of 10411640 and 11488932 made their own private folders with mktemp -d
    'mktemp_verifiers': ['10411640', '11488932'],
    # result/README.md: 83 papers analysed; 52 remain without the 41 the copy read twice
    'analysed': 83, 'read_once_papers': 52,
    # result/README.md and triage.json: values 1,473 plain and 1,400 CatLog; 1,365 pairs; unmatched 108 plain, 35 CatLog;
    # 70 pairs whose labels disagree
    'plain_values': 1473, 'catlog_values': 1400, 'pairs': 1365, 'unmatched_plain': 108, 'unmatched_catlog': 35,
    'identity_suspect_pairs': 70,
    # the second launch of batch 3 (more-4), its session's own summary: 523 values added, 191 censored, 10 rejected
    'batch3_second': {'values': 523, 'censored': 191, 'rejected': 10},
    # stage2/README.md: CatLog on 79 papers, 1,346 values, recall 0.742, precision 0.787
    'stage2_catlog': {'papers': 79, 'values': 1346, 'recall': 0.742, 'precision': 0.787},
}
# Lines the README's statements rest on, checked in the files they come from (a change stops the script):
QUOTED = {
    'task text: each agent\'s scratch folder is named by its role and paper':
        (TASKJS, 'named ${role}-${pmid} inside your scratchpad directory (or /tmp)'),
    'PREREGISTRATION.md: second-launch agents made their own subfolders when they saw others\' files':
        (PREREG, 'made their own subfolders when they saw others\''),
    'PREREGISTRATION.md: no re-reading agent opened work/old': (PREREG, 'No re-reading agent opened work/old.'),
    'PREREGISTRATION.md: the two mktemp verifiers': (PREREG, 'The verifiers of 10411640 and 11488932 made their own private folders'),
    'leftover scan: only a Read tool\'s path and a Bash command line are read':
        (SCAN_CODE, "texts = [str(inp.get('file_path', ''))] if name == 'Read' else [str(inp.get('command', ''))] if name == 'Bash' else []"),
    'leftover scan: only a path that names the paper\'s /tmp role folder is seen':
        (SCAN_CODE, r"folder = re.compile(r'/(?:private/)?tmp/((?:read|verify|verify-missed)-%s|p%s)"),
    'leftover scan: a command that runs mkdir, pdftoppm or savefig, or calls .save(, counts every path it names as written':
        (SCAN_CODE, r"re.search(r'pdftoppm|\.save\(|savefig|mkdir', t) and f.endswith(('.png', '/', ''))"),
}


def sha12(b):
    return hashlib.sha256(b).hexdigest()[:12]


def sha256_file(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def jload(f):
    return json.loads(Path(f).read_text())


def jrows(f):
    return [json.loads(line) for line in open(f) if line.strip()] if Path(f).exists() else []


def suffix(f):
    return int(f.name.split('.')[-2])


def lim4(x):
    return None if x is None else float(f'{x:.4g}')


def exact95(k, n):
    """Clopper-Pearson interval of k of n."""
    from scipy.stats import beta
    return [float(beta.ppf(0.025, k, n - k + 1)) if k else 0.0, float(beta.ppf(0.975, k + 1, n - k)) if k < n else 1.0]


# ---------------------------------------------------------------------------------------------------------------------
# the replay worker: runs in its own process inside a scratch copy of the frozen copy (python3 -I -B stability.py
# --worker ROOT PMID...). It imports that copy's catlog.py, runs its `add` on each paper, and writes one record per
# reader or missed-value row: the row's value at each stage and what became of it. No quote or reasoning text leaves it.
# ---------------------------------------------------------------------------------------------------------------------

def worker(root, pmids):
    root = Path(root)
    sys.path.insert(0, str(root))
    import catlog  # the scratch copy's (ROOT = root)
    if Path(catlog.__file__).resolve().parent != root.resolve():
        sys.exit('worker: imported the wrong catlog.py')
    catlog.agent_model = lambda path: ('', '')   # no transcript lookup: the row keeps the model its agent wrote
    import fetch
    import urllib.request

    def refuse(*a, **k):
        raise RuntimeError('replay: no network call and no key file')
    fetch.env_key = refuse            # add never needs a key; a call would stop the replay instead of reading one
    urllib.request.urlopen = refuse   # nor the network

    orig = catlog.judge

    def judge(pmid, read, ver, text_sq, stamp=None):  # tag each row with its file and index; nothing else changes
        src = 'missed' if isinstance(stamp, dict) and stamp.get('read_by') == catlog.MISSED else 'reader'
        for i, r in enumerate(read.get('rows', [])):
            if isinstance(r, dict):
                r['_stab'] = f'{src}:{i}'
        return orig(pmid, read, ver, text_sq, stamp)
    catlog.judge = judge
    for p in pmids:
        catlog.add_one(p)

    def conv(metric, raw, unit):
        if metric not in catlog.METRICS:
            return None, None
        try:
            v, u, err = catlog.normalize(metric, raw or '', unit or '')
        except Exception:
            return None, None
        if err or v is None or not v > 0:
            return None, None
        return float(f'{v:.6g}'), u

    def bound(r, kind):  # a censored row's limit in catalog units, by the frozen code (catlog.bound_of)
        if not kind:
            return None
        try:
            return catlog.bound_of(r, kind)[0]
        except Exception:
            return None

    outs = {n: jrows(root / n) for n in ('catalog.jsonl', 'bounds.jsonl', 'rejected.jsonl')}
    where = defaultdict(list)
    for n, rows in outs.items():
        for r in rows:
            where[(r['pmid'], r.get('_stab'))].append((n, r))
    recs = []
    for p in pmids:
        files = [('reader', root / 'work' / f'{p}.read.json', root / 'work' / f'{p}.verify.json'),
                 ('missed', root / 'work' / f'{p}.missed.read.json', root / 'work' / f'{p}.missed.verify.json')]
        for src, rp, vp in files:
            if not rp.exists() or not vp.exists():
                continue
            rd, vd = jload(rp), jload(vp)
            verdicts = {int(v['i']): v for v in vd.get('verdicts', []) if str(v.get('i', '')).strip().isdigit()}
            for i, row in enumerate(rd.get('rows', [])):
                v = verdicts.get(i, {'verdict': 'missing'})
                cens_row = bool(catlog.censored_kind(row))  # judge()'s rule: a verdict must name the row it judged
                if ('metric' in v and v['metric'] != row.get('metric')) or \
                   ('raw_value' in v and (catlog.numbers(v['raw_value'])[:1] != catlog.numbers(row.get('raw_value', ''))[:1])) or \
                   (cens_row and 'raw_value' in v and catlog.squash(v['raw_value']) != catlog.squash(row.get('raw_value', ''))) or \
                   (cens_row and v.get('variant') and catlog.squash(v['variant']) != catlog.squash(row.get('variant', ''))):
                    v = {'verdict': 'stale'}
                fixed = {**row, **(v.get('fix') or {})} if v.get('verdict') == 'fix' else dict(row)
                stage = {}
                for name, r in (('reader', row), ('verifier', fixed)):
                    m = r.get('metric')
                    kind = catlog.censored_kind(r)
                    val, unit = conv(m, r.get('raw_value'), r.get('unit_for_conversion') or r.get('raw_unit'))
                    printed, _ = conv(m, r.get('raw_value'), STD.get(m, ''))
                    stage[name] = {'metric': m, 'value': val, 'unit': unit, 'printed': printed,
                                   'censored': kind, 'bound': bound(r, kind),
                                   'raw': r.get('raw_value', ''), 'raw_unit': r.get('raw_unit', ''),
                                   'unit_for_conversion': r.get('unit_for_conversion', '') or '',
                                   'enzyme': r.get('enzyme', ''), 'organism': r.get('organism', ''),
                                   'variant': r.get('variant', ''), 'substrate': r.get('substrate', ''),
                                   'cosub': r.get('cosubstrate', ''), 'pH': r.get('pH'), 'temp': r.get('temperature_C'),
                                   'where': r.get('location', '')}
                hits = where.get((p, f'{src}:{i}'), [])
                if len(hits) > 1:
                    sys.exit(f'worker: {p} {src}:{i} written {len(hits)} times')
                fate, why, stored, bnd = 'duplicate', [], None, None   # add counted it as a duplicate of a row it stored
                if hits:
                    n, r = hits[0]
                    if n == 'catalog.jsonl':
                        fate, stored = 'stored', r
                    elif n == 'bounds.jsonl':
                        fate = 'bound'
                        bnd = {'kind': r.get('censored'), 'bound': r.get('bound'), 'unit': r.get('unit'), 'metric': r.get('metric')}
                    else:
                        why = [str(w) for w in r.get('why', [])]
                        fate = ('verifier_reject' if any(w.startswith('verifier_') for w in why) else
                                'code_conflict' if any(re.search(r'conflicts with|same printed cell|audit dropped|page image prints', w)
                                                       for w in why) else 'code_refused')
                if stored is not None:
                    st = {'metric': stored['metric'], 'value': stored.get('value'), 'unit': stored.get('unit'),
                          'printed': conv(stored['metric'], stored.get('raw_value'), STD.get(stored['metric'], ''))[0],
                          'censored': '', 'bound': None, 'raw': stored.get('raw_value', ''), 'raw_unit': stored.get('raw_unit', ''),
                          'unit_for_conversion': stored.get('unit_for_conversion', '') or '',
                          'enzyme': stored.get('enzyme', ''), 'organism': stored.get('organism', ''),
                          'variant': stored.get('variant', ''), 'substrate': stored.get('substrate', ''),
                          'cosub': stored.get('cosubstrate', ''), 'pH': stored.get('pH'), 'temp': stored.get('temperature_C'),
                          'where': stored.get('location', ''), 'row_id': stored['row_id'],
                          'stamps': {k: stored.get(k, '') for k in ('read_by', 'reader_model', 'verifier_model',
                                                                     'read_prompt', 'verify_prompt', 'task_prompt')}}
                    stage['stored'] = st
                recs.append({'pmid': p, 'src': src, 'i': i, 'verdict': v.get('verdict'), 'fate': fate, 'why': why,
                             'reasoning_sha1': hashlib.sha1(str(row.get('reasoning', '')).encode()).hexdigest(),
                             'fix_fields': sorted(k for k, x in (v.get('fix') or {}).items() if row.get(k, '') != x)
                             if v.get('verdict') == 'fix' else [], 'bound': bnd, 'stage': stage})
    adds = [line.rstrip('\n').split('\t') for line in open(root / 'log.tsv') if '\tadd\t' in line]
    (root / 'stability_rows.json').write_text(json.dumps({'rows': recs, 'adds': adds}, ensure_ascii=False))


# ---------------------------------------------------------------------------------------------------------------------
# the main analysis
# ---------------------------------------------------------------------------------------------------------------------

def kit_modules():
    sys.path.insert(0, str(KIT / 'code' / 'tools' / 'w1'))
    sys.path.insert(0, str(STAGE2))
    import common_w1 as W  # noqa: E402
    import h2h  # noqa: E402
    import score_w1 as SW  # noqa: E402
    import score_stage2 as S2  # noqa: E402
    return W, h2h, h2h.C, SW, S2


def git_copy(*a):
    r = subprocess.run(['git', '--no-optional-locks', '-C', str(COPY), *a], capture_output=True, text=True, timeout=60,
                       env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
    if r.returncode:
        sys.exit(f'git {a}: {r.stderr.strip()}')
    return r.stdout.strip()


def frozen_hashes():
    task = b''.join(f'=== {f} ===\n'.encode() + (COPY / f).read_bytes() for f in TASK if (COPY / f).is_file())
    return {'read.md': sha12((COPY / 'prompts' / 'read.md').read_bytes()),
            'verify.md': sha12((COPY / 'prompts' / 'verify.md').read_bytes()), 'task': sha12(task)}


def first_files(p):
    """The first launch's work files of paper p: moved to work/old when the second launch claimed the paper (the newest
    copy of each kind there)."""
    out = {}
    for kind in ('read', 'verify', 'prompts', 'missed.read', 'missed.verify'):
        c = sorted(WORK.glob(f'old/{p}.{kind}.*.json'), key=suffix)
        if c:
            out[kind] = c[-1]
    return out


def second_files(p):
    return {k: WORK / f'{p}.{k}.json' for k in ('read', 'verify', 'prompts', 'missed.read', 'missed.verify')
            if (WORK / f'{p}.{k}.json').exists()}


def role_dirs(root, p):
    """A paper's scratch folders under root: read-<PMID>, verify-<PMID>, verify-missed-<PMID> (with any suffix an agent
    added, e.g. read-<PMID>-r2) and p<PMID>, the folders the kit's reset collects."""
    rx = re.compile(rf'^(?:(?:read|verify|verify-missed)-{p}(?![0-9A-Za-z])|p{p}$)')
    return [d for d in sorted(root.iterdir()) if rx.match(d.name)]


def build_root(root, files_by_paper, papers_tsv_rows):
    """A scratch copy of the frozen copy's code, prompts and task files, the papers' texts (times kept, so add's
    freshness check sees what it saw), one launch's work files, an empty catalog."""
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    ign = shutil.ignore_patterns('__pycache__', '*.pyc')
    for f in ('catlog.py', 'config.json'):
        shutil.copy2(COPY / f, root / f)
    for d in ('prompts', 'tools', 'sources'):
        shutil.copytree(COPY / d, root / d, ignore=ign)
    for d in ('workflows', 'agents'):
        shutil.copytree(COPY / '.claude' / d, root / '.claude' / d, ignore=ign)
    (root / 'texts').mkdir()
    (root / 'work').mkdir()
    for p, files in files_by_paper.items():
        for ext in ('txt', 'supp.txt'):
            if (COPY / 'texts' / f'{p}.{ext}').exists():
                shutil.copy2(COPY / 'texts' / f'{p}.{ext}', root / 'texts' / f'{p}.{ext}')
        for kind, src in files.items():
            shutil.copy2(src, root / 'work' / f'{p}.{kind}.json')
    head = papers_tsv_rows[0]
    cols = head.split('\t')
    out = [head]
    for line in papers_tsv_rows[1:]:
        f = line.split('\t')
        if f[0] in files_by_paper:
            f[cols.index('status')] = 'reading'
            for k in ('kept', 'rejected', 'note'):
                f[cols.index(k)] = ''
            out.append('\t'.join(f))
    (root / 'papers.tsv').write_text('\n'.join(out) + '\n')
    for f in ('catalog.jsonl', 'rejected.jsonl', 'bounds.jsonl', 'log.tsv'):
        (root / f).write_text('')


def replay(root, files_by_paper, papers_tsv_rows):
    build_root(root, files_by_paper, papers_tsv_rows)
    r = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--worker', str(root),
                        *files_by_paper], capture_output=True, text=True, cwd=str(root))
    (root / 'replay.out.txt').write_text(r.stdout + '\n--- stderr ---\n' + r.stderr)
    if r.returncode:
        sys.exit(f'replay in {root} failed: {r.stderr[-2000:]}')
    return jload(root / 'stability_rows.json')


def value_rec(rec, stage, launch):
    s = rec['stage'].get(stage)
    if not s:
        return None
    return {'pmid': rec['pmid'], 'metric': s['metric'], 'unit': s['unit'], 'value': s['value'], 'printed': s['printed'],
            'raw': s['raw'], 'raw_unit': s['raw_unit'], 'ufc': s['unit_for_conversion'],
            'enzyme': s['enzyme'] or '', 'organism': s['organism'] or '', 'variant': s['variant'] or '',
            'substrate': s['substrate'] or '', 'cosub': s['cosub'] or '',
            'pH': '' if s['pH'] is None else str(s['pH']), 'temp': '' if s['temp'] is None else str(s['temp']),
            'where': s['where'] or '', 'quote': '', 'id': f"L{launch}:{rec['pmid']}:{rec['src']}:{rec['i']}",
            'fate': rec['fate'], 'src': rec['src'], 'reasoning_sha1': rec['reasoning_sha1']}


def stage_values(recs, stage, launch, papers):
    """A launch's values at one stage: numeric (not censored), converted into catalog units; and apart, those in other
    units (mass-concentration Km and its kcat/Km) and the rows whose cell does not convert."""
    out, other_unit, unconverted = [], [], []
    for rec in recs:
        if rec['pmid'] not in papers:
            continue
        if stage == 'reader':
            if rec['src'] != 'reader':
                continue   # the verifier's missed values enter at the verifier stage
            s = rec['stage']['reader']
        elif stage == 'verifier':
            if rec['fate'] == 'verifier_reject':
                continue
            s = rec['stage']['verifier']
        else:
            if rec['fate'] != 'stored':
                continue
            s = rec['stage']['stored']
        if s.get('censored') or s['metric'] not in STD:
            continue
        v = value_rec(rec, stage, launch)
        if v['value'] is None:
            unconverted.append(v)
        elif v['unit'] != STD[v['metric']]:
            other_unit.append(v)
        else:
            out.append(v)
    return out, other_unit, unconverted


def match_on(C, a, b, key, prefer=None):
    """C.match's assignment (per paper and metric, one to one, most pairs first, closest description second) on the
    number `key` of each value ('printed': the printed cell's number before any unit; 'value': the stored value). prefer:
    a second number; a pair that also agrees on it goes before one that does not."""
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    by = defaultdict(lambda: ([], []))
    for i, x in enumerate(a):
        if x.get(key) is not None:
            by[(x['pmid'], x['metric'])][0].append(i)
    for j, y in enumerate(b):
        if y.get(key) is not None:
            by[(y['pmid'], y['metric'])][1].append(j)
    pairs = []
    for (ai, bj) in by.values():
        if not ai or not bj:
            continue
        cost = np.full((len(ai), len(bj)), 1e6)
        for s, i in enumerate(ai):
            for t, j in enumerate(bj):
                if C.close(a[i][key], b[j][key]):
                    bonus = 100 if prefer and C.close(a[i].get(prefer), b[j].get(prefer)) else 0
                    cost[s, t] = -(1000 + bonus + C.desc_sim(a[i], b[j]))
        if (cost < 0).any():
            ra, cb = linear_sum_assignment(cost)
            pairs += [(ai[s], bj[t], float(-cost[s, t])) for s, t in zip(ra, cb) if cost[s, t] < 0]
    return pairs


CELL_KIND, DESC_KIND = 'same printed cell, stored otherwise', 'same description, another number'
VALUE_KIND = 'same value, cell written otherwise'
FATE_WORDS = {'stored': 'stored as values', 'bound': 'stored as censored values', 'verifier_reject': 'rejected by the verifier',
              'code_refused': 'refused by the code checks', 'code_conflict': 'refused by the code as a conflict',
              'duplicate': 'merged by the code as duplicates'}


def pair_launches(C, SW, a, b, first='printed'):
    """first='printed' (the main pairing): per paper and constant, one to one on the printed cell (its number before any
    unit, within 1.5%), a pair whose stored values also agree preferred, then the closest description: in both when the
    stored values agree within 1.5%, conflicting when they do not. Values left on both sides: the same stored value with
    the cell written otherwise (in both), then the same description with another number (C.desc_pairs: same paper and
    constant, descriptions agreeing at least on variant and substrate: conflicting). The rest: one only.
    first='value': the tests' own matcher (C.match on the stored value) first, then the same printed cell stored
    otherwise and the same description (conflicting)."""
    if first == 'printed':
        p1 = match_on(C, a, b, 'printed', prefer='value')
        both = [(i, j, s, '') for i, j, s in p1 if C.close(a[i]['value'], b[j]['value'])]
        conf = [(i, j, s, CELL_KIND) for i, j, s in p1 if not C.close(a[i]['value'], b[j]['value'])]
    else:
        both = [(i, j, s, '') for i, j, s in C.match(a, b)[0]]
        conf = []
    used_a, used_b = {x[0] for x in both + conf}, {x[1] for x in both + conf}
    au, bu = [i for i in range(len(a)) if i not in used_a], [j for j in range(len(b)) if j not in used_b]
    p2 = match_on(C, [a[i] for i in au], [b[j] for j in bu], 'value' if first == 'printed' else 'printed')
    for i, j, s in p2:
        i, j = au[i], bu[j]
        if first == 'printed':
            both.append((i, j, s, VALUE_KIND))
        elif not C.close(a[i]['value'], b[j]['value']):
            conf.append((i, j, s, CELL_KIND))
    used_a, used_b = {x[0] for x in both + conf}, {x[1] for x in both + conf}
    au, bu = [i for i in range(len(a)) if i not in used_a], [j for j in range(len(b)) if j not in used_b]
    conf += [(i, j, s, DESC_KIND) for i, j, s in C.desc_pairs(a, b, au, bu)]
    used_a, used_b = {x[0] for x in both + conf}, {x[1] for x in both + conf}
    return {'pairs': [(i, j, s) for i, j, s, _ in both], 'pair_kinds': dict(Counter(k or 'same printed cell and value' for *_, k in both)),
            'conflicts': conf, 'only_a': [i for i in range(len(a)) if i not in used_a],
            'only_b': [j for j in range(len(b)) if j not in used_b],
            'labels_disagree': [(i, j) for i, j, _, _ in both if SW.identity_disagrees(a[i], b[j])]}


def squash_cell(s):
    return re.sub(r'\s+', '', str(s or '')).replace('−', '-').replace('×', 'x').lower()


def why_missing(C, val, other_recs, stage, other_launch, taken):
    """Why the other launch lacks this value at this stage: the latest step that had it and dropped it."""
    def cands(pred, st):
        out = []
        for rec in other_recs:
            if rec['pmid'] != val['pmid'] or not pred(rec):
                continue
            v = value_rec(rec, st, other_launch)
            if v and v['metric'] == val['metric'] and v['id'] not in taken and \
               ((v['value'] is not None and C.close(v['value'], val['value'])) or
                (v['printed'] is not None and val['printed'] is not None and C.close(v['printed'], val['printed']))):
                out.append(v)
        return out
    steps = []
    if stage == 'stored':
        steps.append(('code refused it', lambda r: r['fate'] in ('code_refused', 'code_conflict')
                      and not r['stage']['verifier']['censored'], 'verifier'))
        steps.append(('code stored it once (a duplicate)', lambda r: r['fate'] == 'duplicate'
                      and not r['stage']['verifier']['censored'], 'verifier'))
    if stage in ('stored', 'verifier'):
        steps.append(('its verifier rejected it', lambda r: r['fate'] == 'verifier_reject', 'reader'))
        steps.append(('it holds the cell as a bound', lambda r: r['fate'] != 'verifier_reject'
                      and bool(r['stage']['verifier']['censored']), 'verifier'))
    if stage == 'reader':
        steps.append(('its reader skipped it, its verifier added it', lambda r: r['src'] == 'missed', 'verifier'))
        steps.append(('its reader read the cell as a bound', lambda r: r['src'] == 'reader'
                      and bool(r['stage']['reader']['censored']), 'reader'))
    for label, pred, st in steps:
        c = cands(pred, st)
        if c:
            c.sort(key=lambda v: -C.desc_sim(val, v))
            taken.add(c[0]['id'])
            return label
    return 'not read'


def censored_keys(recs, stage, papers):
    """A launch's censored values (bounds, not detected) at one stage, counted by (paper, constant, kind, limit in catalog
    units to 4 digits): the reader's rows; the rows its verifier kept (fix applied) and the missed rows its second check
    kept; the bounds the code stored."""
    out = Counter()
    for r in recs:
        if r['pmid'] not in papers:
            continue
        if stage == 'stored':
            if r['fate'] == 'bound':
                b = r['bound']
                out[(r['pmid'], b['metric'], b['kind'], lim4(b['bound']))] += 1
            continue
        if (stage == 'reader' and r['src'] != 'reader') or (stage == 'verifier' and r['fate'] == 'verifier_reject'):
            continue
        s = r['stage'][stage]
        if s['censored']:
            out[(r['pmid'], s['metric'], s['censored'], lim4(s['bound']))] += 1
    return out


def censored_why(key, other, stage):
    """Why the other launch lacks a censored value at this stage."""
    p, m, kind, lim = key

    def has(pred, st):
        return any(r['pmid'] == p and pred(r) and (r['stage'][st]['metric'], r['stage'][st]['censored'],
                                                    lim4(r['stage'][st]['bound'])) == (m, kind, lim) for r in other)
    if stage == 'reader' and has(lambda r: r['src'] == 'missed' and r['fate'] != 'verifier_reject', 'verifier'):
        return 'its reader skipped it, its verifier added it'
    if stage != 'reader' and has(lambda r: r['fate'] == 'verifier_reject', 'reader'):
        return 'its verifier rejected it'
    if stage == 'stored' and has(lambda r: r['fate'] not in ('bound', 'verifier_reject'), 'verifier'):
        return 'its code did not store it'
    return 'not read'


def censored_comparison(recs1, recs2, stage, papers):
    """Censored values of the two launches at one stage, matched on paper, constant, kind and limit."""
    k1, k2 = censored_keys(recs1, stage, papers), censored_keys(recs2, stage, papers)
    per = {p: [sum(v for k, v in c.items() if k[0] == p) for c in (k1, k2, k1 & k2)] for p in papers}
    differ = sorted((p for p, (x, y, z) in per.items() if not x == y == z), key=int)
    o1, o2 = k1 - k2, k2 - k1
    why1 = [(k, censored_why(k, recs2, stage)) for k in o1.elements()]
    why2 = [(k, censored_why(k, recs1, stage)) for k in o2.elements()]

    def one_paper(p):  # counts, and the values in one launch only as 'constant kind|why the other lacks it': n
        d = dict(zip(('launch1', 'launch2', 'both'), per[p]))
        for L, w in ((1, why1), (2, why2)):
            d[f'only_launch{L}'] = dict(Counter(f'{k[1]} {k[2]}|{y}' for k, y in w if k[0] == p))
        return d
    return {'launch1': sum(k1.values()), 'launch2': sum(k2.values()), 'both': sum((k1 & k2).values()),
            'only_launch1': sum(o1.values()), 'only_launch2': sum(o2.values()),
            'why_only_launch1': dict(Counter(y for _, y in why1)), 'why_only_launch2': dict(Counter(y for _, y in why2)),
            'only_by_constant_and_kind': {'launch1': dict(Counter(f'{k[1]} {k[2]}' for k in o1.elements())),
                                          'launch2': dict(Counter(f'{k[1]} {k[2]}' for k in o2.elements()))},
            'papers_only_launch1': sorted({k[0] for k in o1}, key=int), 'papers_only_launch2': sorted({k[0] for k in o2}, key=int),
            'papers_with_censored_values': sum(1 for x in per.values() if x[0] or x[1]),
            'papers_identical': sum(1 for x in per.values() if (x[0] or x[1]) and x[0] == x[1] == x[2]),
            'papers_differing': differ, 'per_paper_differing': {p: one_paper(p) for p in differ}}


def other_unit_comparison(C, SW, ao, bo):
    """Values in units the tests leave out (mass-concentration Km and its kcat/Km), paired within their unit."""
    a = [dict(v, metric=f"{v['metric']}|{v['unit']}") for v in ao]
    b = [dict(v, metric=f"{v['metric']}|{v['unit']}") for v in bo]
    res = pair_launches(C, SW, a, b)
    odd = {a[i]['pmid'] for i in res['only_a']} | {b[j]['pmid'] for j in res['only_b']} | \
        {a[i]['pmid'] for i, _, _, _ in res['conflicts']}
    return {'launch1': len(a), 'launch2': len(b), 'both': len(res['pairs']), 'conflicting': len(res['conflicts']),
            'only_launch1': len(res['only_a']), 'only_launch2': len(res['only_b']), 'units': dict(Counter(v['metric'] for v in a)),
            'papers_differing': sorted(odd, key=int)}


def analyse(C, SW, recs1, recs2, papers):
    out, tsv = {}, []
    for stage in STAGES:
        a, ao, au = stage_values(recs1, stage, 1, papers)
        b, bo, bu = stage_values(recs2, stage, 2, papers)
        res = pair_launches(C, SW, a, b)
        reasons = {1: Counter(), 2: Counter()}
        taken = {1: set(), 2: set()}
        for side, vals, idx, other, ol in ((1, a, res['only_a'], recs2, 2), (2, b, res['only_b'], recs1, 1)):
            for i in idx:
                why = why_missing(C, vals[i], other, stage, ol, taken[ol])
                reasons[side][why] += 1
                v = vals[i]
                tsv.append([stage, v['pmid'], v['metric'], f'only launch {side}', why,
                            *(cell(v) if side == 1 else ['', '', '']), *(cell(v) if side == 2 else ['', '', '']),
                            v['enzyme'], v['variant'], v['substrate'], v['where']])
        disagree = set(res['labels_disagree'])
        for i, j, _ in res['pairs']:
            tsv.append([stage, a[i]['pmid'], a[i]['metric'], 'both', 'labels differ' if (i, j) in disagree else '',
                        *cell(a[i]), *cell(b[j]), a[i]['enzyme'], a[i]['variant'], a[i]['substrate'], a[i]['where']])
        for i, j, _, kind in res['conflicts']:
            tsv.append([stage, a[i]['pmid'], a[i]['metric'], 'conflicting', f"{kind}: launch 2 / launch 1 = {b[j]['value'] / a[i]['value']:.4g}",
                        *cell(a[i]), *cell(b[j]), a[i]['enzyme'], a[i]['variant'], a[i]['substrate'], a[i]['where']])
        exact = {'same_value_exactly': sum(1 for i, j, _ in res['pairs'] if a[i]['value'] == b[j]['value']),
                 'same_printed_cell': sum(1 for i, j, _ in res['pairs'] if squash_cell(a[i]['raw']) == squash_cell(b[j]['raw'])),
                 'same_cell_and_value': sum(1 for i, j, _ in res['pairs'] if a[i]['value'] == b[j]['value']
                                            and squash_cell(a[i]['raw']) == squash_cell(b[j]['raw']))}
        both, conf = len(res['pairs']), len(res['conflicts'])
        o1, o2 = len(res['only_a']), len(res['only_b'])
        union = both + conf + o1 + o2
        cens = censored_comparison(recs1, recs2, stage, papers)
        mass = other_unit_comparison(C, SW, ao, bo)
        per_paper = {}
        for p in sorted(papers, key=int):
            n1 = sum(1 for v in a if v['pmid'] == p)
            n2 = sum(1 for v in b if v['pmid'] == p)
            pb = sum(1 for i, _, _ in res['pairs'] if a[i]['pmid'] == p)
            pc = sum(1 for i, _, _, _ in res['conflicts'] if a[i]['pmid'] == p)
            per_paper[p] = {'launch1': n1, 'launch2': n2, 'both': pb, 'conflicting': pc,
                            'only1': sum(1 for i in res['only_a'] if a[i]['pmid'] == p),
                            'only2': sum(1 for j in res['only_b'] if b[j]['pmid'] == p),
                            'labels_disagree': sum(1 for i, _ in res['labels_disagree'] if a[i]['pmid'] == p)}
            per_paper[p]['identical'] = per_paper[p]['both'] == n1 == n2
            per_paper[p]['identical_all_kinds'] = per_paper[p]['identical'] and p not in cens['papers_differing'] \
                and p not in mass['papers_differing']
        same_reasoning = sum(1 for i, j, _ in res['pairs'] if a[i]['reasoning_sha1'] == b[j]['reasoning_sha1']
                             and a[i]['src'] == b[j]['src'] == 'reader') if stage == 'reader' else None
        alt = pair_launches(C, SW, a, b, first='value')   # the tests' matcher first: a cross-check of the pairing
        out[stage] = {'launch1_values': len(a), 'launch2_values': len(b), 'both': both, 'conflicting': conf,
                      'both_by_kind': res['pair_kinds'],
                      'with_the_tests_matcher_first': {'both': len(alt['pairs']), 'conflicting': len(alt['conflicts']),
                                                       'only_launch1': len(alt['only_a']), 'only_launch2': len(alt['only_b'])},
                      'conflicting_by_kind': dict(Counter(k for *_, k in res['conflicts'])), 'both_exactness': exact,
                      'by_metric': {'launch1': dict(Counter(v['metric'] for v in a)), 'launch2': dict(Counter(v['metric'] for v in b)),
                                    'both': dict(Counter(a[i]['metric'] for i, _, _ in res['pairs']))},
                      'only_launch1': o1, 'only_launch2': o2, 'distinct_values': union,
                      'share_both': both / union if union else None, 'share_conflicting': conf / union if union else None,
                      'share_one_only': (o1 + o2) / union if union else None,
                      'launch1_also_in_launch2': both / len(a) if a else None, 'launch2_also_in_launch1': both / len(b) if b else None,
                      'labels_disagree_pairs': len(res['labels_disagree']),
                      'why_only_launch1': dict(reasons[1]), 'why_only_launch2': dict(reasons[2]),
                      'papers_identical': sum(1 for d in per_paper.values() if d['identical']),
                      'papers_identical_all_kinds': sum(1 for d in per_paper.values() if d['identical_all_kinds']),
                      'papers': len(papers), 'papers_identical_list': [p for p, d in per_paper.items() if d['identical']],
                      'papers_with_values': sum(1 for d in per_paper.values() if d['launch1'] or d['launch2']),
                      'censored': cens, 'mass_units': mass, 'unconverted_rows': [len(au), len(bu)],
                      'paired_reader_rows_with_identical_reasoning': same_reasoning, 'per_paper': per_paper}
    return out, tsv


def cell(v):
    return [v['raw'], v['raw_unit'] + (f" [as {v['ufc']}]" if v.get('ufc') and v['ufc'] != v['raw_unit'] else ''), f"{v['value']:.6g}"]


def pipeline_counts(recs, papers):
    """What each step did with one launch's rows on these papers: the reader's rows, the verdicts, the fixes (and how
    many changed a value), the verifier's missed values, and each row's end (stored, bound, refused...)."""
    rd = [r for r in recs if r['pmid'] in papers and r['src'] == 'reader']
    ms = [r for r in recs if r['pmid'] in papers and r['src'] == 'missed']
    vals = [r for r in rd if not r['stage']['reader']['censored'] and r['stage']['reader']['metric'] in STD]
    fixes = [r for r in rd + ms if r['verdict'] == 'fix']
    return {'reader_rows': len(rd), 'reader_censored_rows': len(rd) - len(vals), 'reader_value_rows': len(vals),
            'verdicts': dict(Counter(r['verdict'] for r in rd)), 'missed_rows': len(ms),
            'missed_verdicts': dict(Counter(r['verdict'] for r in ms)), 'fixes': len(fixes),
            'fixes_changing_a_value': sum(1 for r in fixes if r['stage']['reader']['value'] != r['stage']['verifier']['value']),
            'fix_fields': dict(Counter(f for r in fixes for f in r['fix_fields'])),
            'ends': dict(Counter(r['fate'] for r in rd + ms))}


def missed_rows_note(recs1, recs2, papers):
    """The values each launch's verifier added as missed, and how many of them the other launch's own reader had read
    (as stored censored values: same paper, constant, kind and limit)."""
    def bkey(r):
        b = r['bound']
        return (r['pmid'], b['metric'], b['kind'], lim4(b['bound']))
    note = {}
    for L, mine, other in ((1, recs1, recs2), (2, recs2, recs1)):
        mr = [r for r in mine if r['pmid'] in papers and r['src'] == 'missed']
        oth = Counter(bkey(r) for r in other if r['pmid'] in papers and r['src'] == 'reader' and r['fate'] == 'bound')
        hit = 0
        for r in mr:
            if r['fate'] == 'bound' and oth[bkey(r)] > 0:
                oth[bkey(r)] -= 1
                hit += 1
        note[f'launch{L}'] = {'rows': len(mr), 'stored_as_censored': sum(1 for r in mr if r['fate'] == 'bound'),
                              'held_by_the_other_launchs_reader': hit, 'papers': sorted({r['pmid'] for r in mr}, key=int)}
    return note


def catalog_values_of(C, recs, papers):
    """The stored values in the locked test's form (C.catalog_values: catalog units only)."""
    rows = []
    for rec in recs:
        if rec['pmid'] in papers and rec['fate'] == 'stored':
            s = rec['stage']['stored']
            rows.append({'pmid': rec['pmid'], 'metric': s['metric'], 'value': s['value'], 'unit': s['unit'],
                         'raw_value': s['raw'], 'raw_unit': s['raw_unit'], 'row_id': s['row_id'], 'enzyme': s['enzyme'],
                         'organism': s['organism'], 'substrate': s['substrate'], 'variant': s['variant'],
                         'temperature_C': s['temp'], 'pH': s['pH'], 'cosubstrate': s['cosub'], 'location': s['where']})
    vals = C.catalog_values(rows, 'catlog')
    for v in vals:
        v['id'], v['pmid'] = str(v['id']), str(v['pmid'])
    return vals


def stage2_scores(C, h2h, S2, sets, papers):
    """Each launch's stored values against EnzyExtract's manual curation, with stage 2's code (score_stage2.table:
    exact repeats dropped, C.match, paper-clustered bootstrap B 10,000), on the given papers; launch 1 minus launch 2
    paired on the same resampled papers (score_stage2.paired)."""
    man = S2.curation()
    gold, _ = h2h.rows_to_values(man, 'ee_manual', set(papers))
    res, arrs = S2.table(gold, sets, papers)
    diff = {k: S2.paired(arrs['launch1']['all'], arrs['launch2']['all'], den) for k, den in (('recall', 'gold_n'), ('precision', 'sys_n'))}
    by_metric = {n: {m: {'recall': res[n][m]['recall']['est'], 'precision': res[n][m]['precision']['est'],
                         'gold_n': res[n][m]['gold_n'], 'sys_n': res[n][m]['sys_n'], 'matched': res[n][m]['matched']}
                     for m in C.METRICS} for n in res}
    return {'papers': len(papers), 'curation_values_scored': sum(1 for g in gold if g['value'] is not None),
            'launch1': res['launch1']['all'], 'launch2': res['launch2']['all'], 'launch1_minus_launch2': diff,
            'by_metric': by_metric}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scratch')
    ap.add_argument('--keep', action='store_true')
    a = ap.parse_args()
    W, h2h, C, SW, S2 = kit_modules()
    facts, checks = {}, []

    def check(ok, what):
        if not ok:
            sys.exit(f'check failed: {what}')
        checks.append(what)

    # 1. the papers read twice, their two launches, and which ones left complete files in both
    twice = TWICE.read_text().split()
    check(len(twice) == PRINTED['read_twice'] == len(set(twice)), f"{PRINTED['read_twice']} papers read twice")
    agents = jload(AUDIT)['agents']
    by_paper = defaultdict(list)
    for ag in agents:
        if ag.get('pmid') in twice and ag.get('role') != 'launch':
            by_paper[ag['pmid']].append(ag)
    launches = {}
    for p in twice:
        seq = []
        for ag in sorted(by_paper[p], key=lambda g: g.get('start') or ''):
            if ag['launch'] not in seq:
                seq.append(ag['launch'])
        launches[p] = seq
    first_counts = Counter(s[0] for s in launches.values())
    check(dict(first_counts) == PRINTED['read_twice_first_launch'] and all(len(s) == 2 for s in launches.values()),
          "each of the 41 has agents in exactly two launches: 30 first in more-3, 6 in more-1, 5 in more-7")
    complete = [p for p in twice if {'read', 'verify'} <= set(first_files(p)) and {'read', 'verify'} <= set(second_files(p))]
    no_first = [p for p in twice if p not in complete]
    facts['read_twice'] = len(twice)
    facts['complete_in_both'] = len(complete)
    facts['complete_in_both_list'] = complete
    facts['not_complete'] = {p: ('first launch left a reader file but no verifier file' if 'read' in first_files(p)
                                 else 'first launch left no reader or verifier file') for p in no_first}
    launch_info = {L: jload(LOGS / L / 'launch.json') for L in sorted({x for s in launches.values() for x in s})}
    pair_launch = Counter((launches[p][0], launches[p][1]) for p in complete)
    check(set(pair_launch) == {('more-3', 'more-4')}, 'every complete pair is more-3 (first) and more-4 (second)')
    L1, L2 = launch_info['more-3'], launch_info['more-4']
    batch3 = list(L2['pmids'])
    check(batch3 == list(L1['pmids']) and len(set(batch3)) == len(batch3), 'both launches of the batch named the same papers')
    batch_first_complete = [p for p in batch3 if {'read', 'verify'} <= set(first_files(p))]
    check(set(batch_first_complete) == set(complete) and all({'read', 'verify'} <= set(second_files(p)) for p in batch3),
          'the papers complete in both launches are the batch papers whose first launch left both files')
    facts['batch_papers'] = len(batch3)
    facts['batch_first_launch_complete'] = len(batch_first_complete)
    facts['batch_first_launch_incomplete'] = {p: facts['not_complete'][p] for p in batch3 if p not in complete}
    facts['other_papers_read_twice'] = {'papers': len([p for p in twice if p not in batch3]),
                                        'first_launch': dict(Counter(launches[p][0] for p in twice if p not in batch3)),
                                        'left_a_reader_file': sum(1 for p in twice if p not in batch3 and 'read' in first_files(p))}
    check(facts['other_papers_read_twice']['left_a_reader_file'] == 0, 'the other first launches left no reader file')

    def utc(s):
        import datetime
        return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
    t1, t1e = utc(L1['start_utc']), utc(L1['start_utc']) + float(L1['seconds'])
    t2, t2e = utc(L2['start_utc']), utc(L2['start_utc']) + float(L2['seconds'])
    for p in complete:
        f1, f2 = first_files(p), second_files(p)
        check(all(t1 <= f1[k].stat().st_mtime <= t1e for k in ('read', 'verify')),
              f'{p}: the first launch wrote its reader and verifier files while more-3 ran')
        check(all(t2 <= f2[k].stat().st_mtime <= t2e for k in ('read', 'verify')),
              f'{p}: the second launch wrote its reader and verifier files while more-4 ran')
    facts['launches'] = {'first': {'launch': 'more-3', 'start': L1['start'], 'end': L1['end'], 'exit': 'weekly usage limit before its add'},
                         'second': {'launch': 'more-4', 'start': L2['start'], 'end': L2['end']}}
    sess1 = jload(LOGS / 'more-3' / 'session.json')
    check(sess1.get('api_error') == 'usage_limit_reached' and str(sess1.get('is_error')) == 'True',
          'more-3 ended at the usage limit (so its add never ran)')

    # 2. the same instructions, code, model and settings in both launches
    fh = frozen_hashes()
    check(fh == PRINTED['hashes'], f'the frozen copy hashes to read.md {fh["read.md"]}, verify.md {fh["verify.md"]}, task {fh["task"]}')
    head = git_copy('rev-parse', 'HEAD')
    check(head.startswith(FROZEN_COMMIT), f'the copy is at {FROZEN_COMMIT}')
    check(git_copy('status', '--porcelain', '--untracked-files=no', '--', *PIPELINE) == '',
          'the copy\'s pipeline files (catlog.py, prompts, units.py, task files) are as committed')
    check(git_copy('rev-list', '--count', 'HEAD') == '1', 'the copy has a single commit (nothing changed between the launches)')
    claims = {}
    for p in complete:
        c1 = jload(first_files(p)['prompts'])
        c2 = jload(second_files(p)['prompts'])
        claims[p] = (c1.get('claimed'), c2.get('claimed'))
        check(claims[p] == (L1['start'][:16], L2['start'][:16]), f'{p}: claimed when more-3 and when more-4 started')
        for c in (c1, c2):
            check({k: c.get(k) for k in fh} == fh, f'{p}: claim record names the frozen hashes')
    facts['claim_times'] = sorted({c for v in claims.values() for c in v})
    for L, info in (('more-3', L1), ('more-4', L2)):
        cmd = info['command'] if isinstance(info['command'], list) else json.loads(info['command'].replace("'", '"'))
        check('--model' in cmd and cmd[cmd.index('--model') + 1] == OPUS and cmd[cmd.index('--effort') + 1] == 'max',
              f'{L}: launched on {OPUS} at max effort')
    check((LOGS / 'more-3' / 'launch_line.txt').read_text() == (LOGS / 'more-4' / 'launch_line.txt').read_text(),
          'both launches ran the same launch line (same 30 papers, lanes 4, the same copy)')
    vers = jload(LOGS / 'versions.json')
    check({x['claude'] for k in ('before more-3', 'after more-3', 'before more-4', 'after more-4') for x in vers[k]}
          == {'2.1.317 (Claude Code)'}, 'both launches ran Claude Code 2.1.317')
    inputs = jload(INPUTS)
    for p in complete:
        check(sha256_file(COPY / 'texts' / f'{p}.txt') == inputs['papers'][p]['text_sha256'],
              f'{p}: the copy\'s text is the one laid down before both launches')

    # 3. models: every agent of both launches on Opus (the locked test's one-model rule)
    models, sonnet, sonnet_agents = {}, [], {}
    for p in complete:
        ms = set()
        for files in (first_files(p), second_files(p)):
            for k in ('read', 'verify', 'missed.read', 'missed.verify'):
                if k in files:
                    ms.add(jload(files[k]).get('model'))
        retried = [(g['launch'], g['label']) for g in by_paper[p] if g['launch'] in ('more-3', 'more-4') and 'sonnet' in g['label']
                   and g.get('tool_calls', 0) > 0]
        models[p] = sorted(ms)
        if ms != {OPUS} or retried:
            sonnet.append(p)
            sonnet_agents[p] = sorted(retried)
    tri = jload(TRIAGE)
    refused = {p for p, w in tri['papers_failed'].items() if w.startswith('refused')}
    check(set(sonnet) == refused & set(complete), 'the papers with a Sonnet retry in either launch are exactly the locked '
          'test\'s refusal exits among them')
    facts['sonnet_retry'] = sorted(sonnet, key=int)
    role_word = {'read-sonnet': 'reader', 'verify-sonnet': 'verifier', 'verify.missed-sonnet': 'missed-value verifier'}
    facts['sonnet_retry_agents'] = {p: [f"launch {1 if L == 'more-3' else 2}'s {role_word.get(lab.split(':')[0], lab.split(':')[0])}"
                                        for L, lab in v] for p, v in sorted(sonnet_agents.items(), key=lambda x: int(x[0]))}

    # 4. could the second run see the first run's files? The task text names each agent's scratch folder by role and
    # paper, the same in both launches; the reset moved each paper's non-image scratch aside with its file times.
    for what, (f, line) in QUOTED.items():
        check(line in f.read_text(), what)
    check('draft.read.json'.endswith(('.png', '/', '')), 'the leftover scan\'s write rule (a path ending in \'\') matches every path')
    scan = jload(LEFTOVER)
    start = {(g['label'], g['launch']): utc(g['start']) for g in agents if g.get('start')}

    def when(t):
        return 'first' if t1 <= t <= t1e else 'second' if t2 <= t <= t2e else 'other'

    def files_in(d):
        return [d] if d.is_file() else sorted(x for x in d.rglob('*') if x.is_file())
    held = {}   # p -> [(where the reset kept it, path, the launch that wrote it by its file time)]
    for p in complete:
        held[p] = [('moved', str(f.relative_to(SCRATCH)), when(f.stat().st_mtime)) for d in role_dirs(SCRATCH, p) for f in files_in(d)]
        held[p] += [('mktemp', str(f.relative_to(MKTEMP)), when(f.stat().st_mtime))
                    for m in sorted(MKTEMP.iterdir()) if m.is_dir() for d in role_dirs(m, p) for f in files_in(d)]
    check(all(w != 'other' for v in held.values() for *_, w in v),
          'every file the reset kept for these papers was written while one of the two launches ran')
    check(not any(IMAGE.search(r) for v in held.values() for k, r, _ in v if k == 'moved'),
          'the reset kept no page image of these papers (page images stayed in /tmp)')
    mk = sorted({r.split('/')[1].split('-')[-1] for v in held.values() for k, r, _ in v if k == 'mktemp'}, key=int)
    check(mk == PRINTED['mktemp_verifiers'] and all(w == 'second' for v in held.values() for k, _, w in v if k == 'mktemp'),
          'the two private mktemp folders are 10411640\'s and 11488932\'s verifiers\' of the second launch')

    def marker(r):  # the folder or file of a path that an agent marked as its own (own, mine, r2)
        parts = r.split('/')
        return next(('/'.join(parts[:i + 1]) for i, c in enumerate(parts) if APART.search(c)), None)
    first_left = {p: [r for k, r, w in held[p] if w == 'first'] for p in complete}
    first_left = {p: v for p, v in first_left.items() if v}
    draft_left = {p: [r for r in v if r.split('/')[0].startswith('read-') and DRAFT.match(r.rsplit('/', 1)[-1])]
                  for p, v in first_left.items()}
    draft_left = {p: v for p, v in draft_left.items() if v}
    verdict_left = {p: [r for r in v if r.split('/')[0].startswith('verify-') and VERDICT.match(r.rsplit('/', 1)[-1])]
                    for p, v in first_left.items()}
    verdict_left = {p: v for p, v in verdict_left.items() if v}
    apart = defaultdict(set)
    for p in complete:
        for k, r, w in held[p]:
            if w == 'second' and k == 'mktemp':
                apart[p].add('private mktemp folder ' + '/'.join(r.split('/')[:2]))
            elif w == 'second' and marker(r):
                apart[p].add(marker(r))
    for e in scan:   # folders of second-launch agents that held only page images (not kept by the reset), as the scan names them
        if e['launch'] == 'more-4' and e['pmid'] in complete:
            for kind, f in e['used'] + e['listed']:
                if marker(f):
                    apart[e['pmid']].add(f"{e['agent'].split(':')[0]}-{e['pmid']}/{marker(f)} (scan)")
    apart = {p: sorted(v) for p, v in apart.items() if v}
    # the kit's scan of every re-reading agent: files in its paper's /tmp folders it read, ran or listed without having
    # written them earlier in its session; one dated before the agent started is a first-launch file it opened
    opened, own, unknown = defaultdict(list), defaultdict(list), defaultdict(list)
    for e in scan:
        p = e['pmid']
        if p not in complete or e['launch'] != 'more-4':
            continue
        t = start[(e['agent'], e['launch'])]
        for kind, f in e['used'] + e['listed']:
            hits = [SCRATCH / d / f for d in (f'read-{p}', f'verify-{p}', f'verify-missed-{p}', f'p{p}') if (SCRATCH / d / f).exists()]
            if hits:
                (opened if min(h.stat().st_mtime for h in hits) < t else own)[p].append(f'{e["agent"]}: {kind} {f}')
            else:
                unknown[p].append(f'{e["agent"]}: {kind} {f}')
    exposed = sorted(opened, key=int)
    check(exposed == PRINTED['exposed'], 'the only paper whose second launch is recorded opening a file the first launch left '
          'is 9495750 (its verifier printed the first verifier\'s scripts)')
    check(all(IMAGE.search(x.split()[-1]) for v in unknown.values() for x in v), 'every other unexplained file a second-launch '
          'agent read in the paper\'s scratch folders is a page image')
    check(set(exposed) <= set(first_left), 'that paper\'s folders held first-launch files')
    scan_hit = {e['pmid'] for e in scan if e['launch'] == 'more-4' and e['pmid'] in complete}

    # the sets
    nothing_left = [p for p in complete if p not in first_left]
    main_set = [p for p in nothing_left if p not in sonnet and p not in exposed]
    wider = [p for p in complete if p not in sonnet and p not in exposed]
    analysed = set(jload(VALUES)['papers'])
    check(len(analysed) == PRINTED['analysed'] == tri['papers_analysed'], '83 papers analysed in the locked test')
    check(len(analysed - set(twice)) == PRINTED['read_once_papers'], '52 analysed papers were read once')
    check(set(main_set) <= set(wider) <= analysed, 'the main set is part of the wider set, and both are among the 83 the '
          'locked test analysed')
    sens = {'main_with_sonnet_retries': [p for p in nothing_left if p not in exposed],
            'wider_without_a_draft_left': [p for p in wider if p not in draft_left],
            'wider_without_any_scan_hit': [p for p in wider if p not in scan_hit],
            'wider_with_9495750': sorted(set(wider) | set(exposed), key=int),
            'wider_with_sonnet_retries': [p for p in complete if p not in exposed]}
    sets = {'main': main_set, 'wider': wider, **sens}

    def count_in(ps, d):
        return sum(1 for p in ps if p in d)
    exposure = {
        'rule': 'a paper counts as exposed when its scratch folders (read-, verify-, verify-missed-<PMID>, as the reset '
                'kept them: non-image files with their times) held a file written while the first launch ran',
        'counts': {name: {'papers': len(ps), 'first_launch_files_left': count_in(ps, first_left),
                          'draft_read_file_or_builder_left': count_in(ps, draft_left),
                          'verdict_script_left': count_in(ps, verdict_left), 'kept_apart_by_a_second_launch_agent': count_in(ps, apart),
                          'opened_a_first_launch_file': count_in(ps, opened), 'scan_lists_a_file_read': count_in(ps, scan_hit)}
                   for name, ps in (('complete', complete), ('wider', wider), ('main', main_set))},
        'per_paper': {p: {'sonnet_retry': p in sonnet, 'first_launch_files_left': first_left.get(p, []),
                          'draft_read_file_or_builder_left': draft_left.get(p, []), 'verdict_script_left': verdict_left.get(p, []),
                          'kept_apart_by_a_second_launch_agent': apart.get(p, []),
                          'opened_a_first_launch_file': opened.get(p, []),
                          'second_launch_files_kept': sum(1 for _, _, w in held[p] if w == 'second'),
                          'scan_second_launch_reads_of_its_own_files': len(own.get(p, [])),
                          'scan_page_images_of_unknown_launch': len(unknown.get(p, []))}
                      for p in sorted(complete, key=int)},
        'definitions': {'draft_read_file_or_builder': DRAFT.pattern + ' (a first-launch file in a read- folder)',
                        'verdict_script': VERDICT.pattern + ' (a first-launch file in a verify- folder)',
                        'kept_apart': APART.pattern + ' in a folder or file name of a second-launch file or of a page '
                                      'image the scan names, or a private mktemp folder'},
    }

    # 5. replay the frozen copy's add on each launch's files
    scr = Path(a.scratch) if a.scratch else Path(tempfile.mkdtemp(prefix='stability-'))
    scr.mkdir(parents=True, exist_ok=True)
    tsv_rows = (RUN / 'papers.tsv').read_text().splitlines()
    out2 = replay(scr / 'launch2', {p: second_files(p) for p in batch3}, tsv_rows)
    out1 = replay(scr / 'launch1', {p: first_files(p) for p in complete}, tsv_rows)
    # the replay of the second launch must give back what the test stored
    skip = {'checked', 'added', 'pipeline_commit', '_stab'}
    field_diffs = Counter()
    for name in ('catalog.jsonl', 'bounds.jsonl', 'rejected.jsonl'):
        mine = {r['row_id']: r for r in jrows(scr / 'launch2' / name)}
        kept = {r['row_id']: r for r in jrows(RUN / name) if r['pmid'] in set(batch3)}
        check(set(mine) == set(kept), f'replay of the second launch: the same {name} row ids ({len(kept)})')
        for k in kept:
            for f in set(kept[k]) | set(mine[k]):
                if kept[k].get(f) != mine[k].get(f):
                    field_diffs[f] += 1
        check(all(kept[k].get('pipeline_commit') == FROZEN_COMMIT and mine[k].get('pipeline_commit') == '' for k in kept),
              f'replay of the second launch, {name}: the test stored commit {FROZEN_COMMIT}; the replay leaves the stamp '
              'blank (its scratch copy is not a git repository)')
    check(set(field_diffs) <= skip, 'replay of the second launch: every field as stored, but the two timestamps (checked, '
          'added), the commit stamp and the replay\'s own row tag')
    facts['replay_fields_that_differ'] = {f: field_diffs[f] for f in sorted(field_diffs)}
    run_adds = {}
    for line in open(RUN / 'log.tsv'):
        f = line.rstrip('\n').split('\t')
        if len(f) > 2 and f[2] == 'add' and f[1] in set(batch3):
            run_adds[f[1]] = f[3:]
    rep_adds = {f[1]: f[3:] for f in out2['adds']}
    check(rep_adds == run_adds, 'replay of the second launch: every add line (kept, duplicates, rejected, status, bounds) as logged')
    tot = Counter()
    for f in out2['adds']:
        for x in f[3:]:
            k, _, v = x.partition('=')
            if v.isdigit():
                tot[k] += int(v)
    check((tot['kept'], tot['bounds'], tot['rejected']) == tuple(PRINTED['batch3_second'][k] for k in ('values', 'censored', 'rejected')),
          'replay of the second launch: 523 values, 191 censored, 10 rejected, as its session reported')
    facts['replay_second_launch_batch'] = {'values': tot['kept'], 'censored': tot['bounds'], 'rejected': tot['rejected']}
    facts['analysed_papers'] = len(analysed)
    recs1, recs2 = out1['rows'], out2['rows']
    # stamps of the replayed first launch
    for rec in recs1:
        if rec['fate'] == 'stored':
            st = rec['stage']['stored']['stamps']
            want_read = fh['verify.md'] if st['read_by'].startswith('verifier') else fh['read.md']
            check(st['read_prompt'] == want_read and st['verify_prompt'] == fh['verify.md'] and st['task_prompt'] == fh['task'],
                  'every stored row of the replayed first launch carries the frozen hashes')
    for r in jrows(RUN / 'catalog.jsonl'):
        if r['pmid'] in set(complete):
            want_read = fh['verify.md'] if r['read_by'].startswith('verifier') else fh['read.md']
            check(r['read_prompt'] == want_read and r['verify_prompt'] == fh['verify.md'] and r['task_prompt'] == fh['task']
                  and r['pipeline_commit'] == FROZEN_COMMIT, 'every row the second launch stored carries the frozen stamps')
    # consistency of the per-row records with what add wrote
    for rec in recs1 + recs2:
        if rec['fate'] == 'stored' and rec['stage']['verifier']['value'] is not None:
            check(abs(rec['stage']['verifier']['value'] - rec['stage']['stored']['value']) <= 1e-9 * abs(rec['stage']['stored']['value']),
                  'a stored value equals its verifier-stage value converted by the frozen units code')
        check((rec['fate'] == 'verifier_reject') == (rec['verdict'] not in ('confirm', 'fix')),
              'a row is a verifier reject exactly when its verdict is not confirm or fix')
        if rec['fate'] == 'bound':
            check(rec['stage']['verifier']['censored'] == rec['bound']['kind'],
                  'a stored censored value has the kind its verifier-stage row gives')

    # the test's own values and pairing, met again with the same code
    vj = jload(VALUES)
    cv = [v for v in vj['catlog']]
    pv = [v for v in vj['plain']]
    check((len(pv), len(cv)) == (PRINTED['plain_values'], PRINTED['catlog_values']), 'the locked test\'s values: 1,473 plain, 1,400 CatLog')
    tp, tcu, tpu = C.match(cv, pv)
    check((len(tp), len(tpu), len(tcu)) == (PRINTED['pairs'], PRINTED['unmatched_plain'], PRINTED['unmatched_catlog']),
          'the tests\' matcher gives the locked test\'s 1,365 pairs, 108 and 35 unmatched')
    check(sum(1 for i, j, _ in tp if SW.identity_disagrees(cv[i], pv[j])) == PRINTED['identity_suspect_pairs'],
          'and its 70 pairs whose labels disagree')
    l2v = catalog_values_of(C, recs2, set(wider))
    tv = sorted((v['id'], v['metric'], v['value']) for v in cv if v['pmid'] in set(wider))
    check(sorted((v['id'], v['metric'], v['value']) for v in l2v) == tv,
          'the replayed second launch\'s stored values on the wider set are the values the locked test judged')

    # 6. the comparison, set by set
    results, tsv_by = {}, {}
    for name, ps in sets.items():
        res, tsv = analyse(C, SW, recs1, recs2, set(ps))
        results[name] = {'papers': sorted(ps, key=int), **res}
        tsv_by[name] = tsv
    steps = {name: {'launch1': pipeline_counts(recs1, set(sets[name])), 'launch2': pipeline_counts(recs2, set(sets[name])),
                    'missed_rows': missed_rows_note(recs1, recs2, set(sets[name]))}
             for name in ('main', 'wider', 'wider_with_sonnet_retries')}
    rs = results['wider_with_sonnet_retries']['reader']['per_paper']
    steps['wider_with_sonnet_retries']['papers_where_the_readers_differ_on_values'] = sorted(
        (p for p, d in rs.items() if d['conflicting'] or d['only1'] or d['only2']), key=int)

    def gaps(ps):
        g = sorted((start[(f'read:{p}', 'more-4')] - start[(f'read:{p}', 'more-3')]) / 3600 for p in ps)
        med = g[len(g) // 2] if len(g) % 2 else (g[len(g) // 2 - 1] + g[len(g) // 2]) / 2
        return {'median': round(med, 2), 'min': round(g[0], 2), 'max': round(g[-1], 2)}

    def plain_context(ps):
        """The plain read against CatLog's second launch on the same papers, with the same pairing (context for the
        tests); the plain read keeps no printed cell apart from its value, so only the description rule can call a
        conflict."""
        s = set(ps)
        pm = [dict(v, printed=None) for v in pv if v['pmid'] in s]
        cm = [dict(v, printed=None) for v in cv if v['pmid'] in s]
        pp = pair_launches(C, SW, cm, pm, first='value')
        ctx = {'papers': len(ps), 'catlog_values': len(cm), 'plain_values': len(pm), 'both': len(pp['pairs']),
               'conflicting': len(pp['conflicts']), 'only_catlog': len(pp['only_a']), 'only_plain': len(pp['only_b']),
               'labels_disagree_pairs': len(pp['labels_disagree'])}
        u = ctx['both'] + ctx['conflicting'] + ctx['only_catlog'] + ctx['only_plain']
        same = [p for p in ps if sum(1 for v in cm if v['pmid'] == p) == sum(1 for v in pm if v['pmid'] == p)
                == sum(1 for i, _, _ in pp['pairs'] if cm[i]['pmid'] == p)]
        ctx.update({'distinct_values': u, 'share_both': ctx['both'] / u if u else None,
                    'share_one_only': (ctx['only_catlog'] + ctx['only_plain']) / u if u else None,
                    'papers_identical': len(same), 'papers_differing': sorted(set(ps) - set(same), key=int)})
        return ctx
    plain_ctx = {name: plain_context(sets[name]) for name in ('main', 'wider')}

    # 7. against the curation (stage 2), both launches, with stage 2's code
    s2res = jload(STAGE2 / 'results.json')
    s2papers = s2res['papers_list']
    re2, _ = S2.table(h2h.rows_to_values(S2.curation(), 'ee_manual', set(s2papers))[0],
                      {'catlog': [v for v in cv if v['pmid'] in set(s2papers)]}, s2papers)
    got = re2['catlog']['all']
    pr = PRINTED['stage2_catlog']
    check(len(s2papers) == pr['papers'] and got['sys_n'] == pr['values'] and round(got['recall']['est'], 3) == pr['recall']
          and round(got['precision']['est'], 3) == pr['precision'] and got['matched'] == s2res['sources']['catlog']['all']['matched'],
          'stage 2\'s code gives CatLog\'s registered 79-paper result again: 1,346 values, recall 0.742, precision 0.787')
    curation = {}
    for name in ('main', 'wider'):
        covered = [p for p in sets[name] if p in set(s2papers)]
        sc = stage2_scores(C, h2h, S2, {'launch1': catalog_values_of(C, recs1, set(covered)),
                                         'launch2': catalog_values_of(C, recs2, set(covered))}, covered)
        sc['papers_list'] = covered
        sc['papers_not_covered'] = [p for p in sets[name] if p not in set(s2papers)]
        curation[name] = sc

    def headline_of(name):
        c = results[name]
        n_id, n_p = c['stored']['papers_identical'], len(c['papers'])
        cur = curation.get(name)
        return {'papers': n_p, 'list': c['papers'],
                'by_stage': {s: {**{k: c[s][k] for k in ('launch1_values', 'launch2_values', 'both', 'conflicting',
                                                          'only_launch1', 'only_launch2', 'distinct_values', 'share_both',
                                                          'share_conflicting', 'share_one_only', 'papers_identical',
                                                          'papers_identical_all_kinds')},
                                 'censored': {k: c[s]['censored'][k] for k in ('launch1', 'launch2', 'both', 'only_launch1',
                                                                               'only_launch2', 'papers_differing')},
                                 'mass_units': {k: c[s]['mass_units'][k] for k in ('launch1', 'launch2', 'both', 'conflicting',
                                                                                   'only_launch1', 'only_launch2')}}
                             for s in STAGES},
                'papers_identical_exact_95': exact95(n_id, n_p),
                'hours_between_the_two_readers': gaps(c['papers']),
                'curation': None if cur is None else {
                    'papers': cur['papers'],
                    **{L: {'recall': cur[L]['recall']['est'], 'recall_95': [cur[L]['recall']['lo'], cur[L]['recall']['hi']],
                           'precision': cur[L]['precision']['est'], 'precision_95': [cur[L]['precision']['lo'], cur[L]['precision']['hi']]}
                       for L in ('launch1', 'launch2')},
                    'launch1_minus_launch2': {k: [cur['launch1_minus_launch2'][k][x] for x in ('est', 'lo', 'hi')]
                                              for k in ('recall', 'precision')}}}
    headline = {'main': headline_of('main'), 'wider': headline_of('wider'), 'minutes_between_launches': round((t2 - t1e) / 60)}
    facts['launch_minutes'] = {'first': round((t1e - t1) / 60), 'second': round((t2e - t2) / 60)}
    out = {'question': 'run-to-run stability of the frozen workflow: the locked test\'s copy read the same papers twice; '
                       'leave out any paper whose second run could see the first run\'s files',
           'headline': headline, 'facts': facts, 'exposure': exposure,
           'sets': {'main': sorted(main_set, key=int), 'wider': sorted(wider, key=int),
                    'nothing_left_incl_sonnet_retries': sorted(nothing_left, key=int), **{k: v for k, v in sens.items()},
                    'left_out_of_the_main_set': {
                        'first_launch_files_left': sorted((p for p in complete if p in first_left), key=int),
                        'sonnet_retry_in_a_launch': [p for p in facts['sonnet_retry'] if p in nothing_left]},
                    'left_out_of_the_wider_set': {'sonnet_retry_in_a_launch': facts['sonnet_retry'],
                                                  'second_launch_opened_a_first_launch_file': exposed},
                    'incomplete_first_launch': facts['not_complete']},
           'models': models, 'hashes': fh, 'copy_head': head, 'steps': steps,
           'comparison': results, 'plain_vs_catlog_launch2_same_papers': plain_ctx, 'curation': curation,
           'checks_passed': list(dict.fromkeys(checks)), 'inputs': {
               'read_twice': str(TWICE), 'work': str(WORK), 'copy': str(COPY), 'audit': str(AUDIT), 'leftover_scan': str(LEFTOVER),
               'leftover_scan_code': str(SCAN_CODE), 'scratch_moved_at_reset': str(SCRATCH), 'mktemp_folders': str(MKTEMP),
               'task_text': str(TASKJS), 'preregistration': str(PREREG),
               'triage': str(TRIAGE), 'values': str(VALUES), 'stage2': str(STAGE2 / 'score_stage2.py'),
               'sha256': {'values.json': sha256_file(VALUES), 'audit.json': sha256_file(AUDIT),
                          'locked_leftover_scan.json': sha256_file(LEFTOVER), 'leftover_scan.py': sha256_file(SCAN_CODE),
                          'catlog.py (copy)': sha256_file(COPY / 'catlog.py'), 'units.py (copy)': sha256_file(COPY / 'tools' / 'units.py'),
                          'score_stage2.py': sha256_file(STAGE2 / 'score_stage2.py'), 'stability.py': sha256_file(__file__)}}}
    (HERE / 'results.json').write_text(json.dumps(out, indent=1, default=str) + '\n')
    head_tsv = ['main_set', 'stage', 'pmid', 'metric', 'outcome', 'why', 'raw_1', 'unit_1', 'value_1', 'raw_2', 'unit_2', 'value_2',
                'enzyme', 'variant', 'substrate', 'location']
    order = {s: i for i, s in enumerate(STAGES)}
    rows = sorted(tsv_by['wider'], key=lambda r: (order[r[0]], int(r[1]), r[2], r[3], r[5], r[8]))
    with open(HERE / 'pairs.tsv', 'w') as fh_:
        fh_.write('\t'.join(head_tsv) + '\n')
        for r in rows:
            fh_.write('\t'.join(' '.join(str(x).split()) for x in ['yes' if r[1] in set(main_set) else 'no', *r]) + '\n')
    write_readme(out)
    if not a.keep:
        shutil.rmtree(scr / 'launch1', ignore_errors=True)
        shutil.rmtree(scr / 'launch2', ignore_errors=True)
        if not a.scratch:
            shutil.rmtree(scr, ignore_errors=True)
    print(f'{len(set(checks))} distinct checks passed; results.json, pairs.tsv and README.md written')


WHY_CENS = {'its reader skipped it, its verifier added it': "launch {o}'s reader skipped and its verifier added",
            'its verifier rejected it': "launch {o}'s verifier rejected",
            'its code did not store it': "launch {o}'s code checks did not store",
            'not read': 'launch {o} did not read'}


def write_readme(out):
    """README.md: plain words around numbers that all come from out (results.json); a sentence that states a finding is
    written only when the numbers say so."""
    pc = lambda x: '-' if x is None else f'{100 * x:.1f}%'  # noqa: E731
    f3 = lambda x: '-' if x is None else f'{x:.3f}'  # noqa: E731
    ci = lambda b: f"{f3(b['est'])} ({f3(b['lo'])}-{f3(b['hi'])})"  # noqa: E731
    dif = lambda b: f"{b['est']:+.3f} ({b['lo']:+.3f} to {b['hi']:+.3f})"  # noqa: E731
    lst = lambda d: ', '.join(f"{v} {str(k).replace('_', ' ')}" for k, v in d.items()) or 'none'  # noqa: E731
    plist = lambda ps: ', '.join(ps)  # noqa: E731
    H, F, X, S, CM = out['headline'], out['facts'], out['exposure'], out['sets'], out['comparison']
    hs, xc, xw, xm = out['hashes'], X['counts']['complete'], X['counts']['wider'], X['counts']['main']
    mn, wd = CM['main'], CM['wider']
    K, R = '<the kit folder>', '<the CatLog folder>'
    names = {'reader': 'Reader (written)', 'verifier': 'Verifier (kept)', 'stored': 'Code checks (stored)'}
    n_two, n_cmp, n_batch, n_bfc = F['read_twice'], F['complete_in_both'], F['batch_papers'], F['batch_first_launch_complete']
    n_son, op = len(F['sonnet_retry']), S['left_out_of_the_wider_set']['second_launch_opened_a_first_launch_file']
    nm, nw = len(S['main']), len(S['wider'])
    rep, oth = F['replay_second_launch_batch'], F['other_papers_read_twice']
    son_main = S['left_out_of_the_main_set']['sonnet_retry_in_a_launch']

    def row(label, x, papers=None):
        o1, o2 = x['only_launch1'], x['only_launch2']
        one = str(o1 + o2) + (f' ({o1} / {o2})' if o1 + o2 else '')
        c = x['censored']
        cells = [label] + ([str(papers)] if papers is not None else []) + [
            str(x['launch1_values']), str(x['launch2_values']), f"{x['both']} ({pc(x['share_both'])})", str(x['conflicting']),
            one, f"{c['launch1']} / {c['launch2']} / {c['both']}",
            f"{x['papers_identical']} / {x['papers_identical_all_kinds']} of {x['papers']}"]
        return '| ' + ' | '.join(cells) + ' |'
    head_cols = ('| Stage | Values, launch 1 | Values, launch 2 | In both | Conflicting | One launch only (1 / 2) | '
                 'Censored values, launch 1 / 2 / in both | Papers identical: values / everything |')

    def cens_only(c):
        parts = []
        for L in (1, 2):
            if c[f'only_launch{L}']:
                kinds = ', '.join(f"{v} {k.replace('_', ' ')}" for k, v in c['only_by_constant_and_kind'][f'launch{L}'].items())
                why = '; '.join((f'{v} ' if len(c[f'why_only_launch{L}']) > 1 else '') + 'which ' + WHY_CENS.get(k, k).format(o=3 - L)
                                for k, v in c[f'why_only_launch{L}'].items())
                parts.append(f"{c[f'only_launch{L}']} in launch {L} only ({kinds}, in {plist(c[f'papers_only_launch{L}'])}), {why}")
        return '; '.join(parts)

    def cens_line(x):
        out_ = []
        for s in ('reader', 'verifier', 'stored'):
            c = x[s]['censored']
            word = {'reader': 'the readers wrote', 'verifier': 'the verifiers kept', 'stored': 'the code checks stored'}[s]
            t = f"{word} {c['launch1']} and {c['launch2']}, " + (f"all {c['both']} in both" if c['launch1'] == c['launch2'] == c['both']
                                                                   else f"{c['both']} in both")
            if c['only_launch1'] + c['only_launch2']:
                t += f": {cens_only(c)}"
            out_.append(t)
        return '; '.join(out_)

    def paper_diff(p, d):  # one paper's censored values that differ between the launches, in words
        parts = []
        for L in (1, 2):
            for key, n in d[f'only_launch{L}'].items():
                kind, why = key.split('|')
                parts.append(f"{n} {kind.replace('_', ' ')} in launch {L} only, which {WHY_CENS.get(why, why).format(o=3 - L)}")
        son = F['sonnet_retry_agents'].get(p)
        return f"{p} ({d['launch1']} against {d['launch2']}: {'; '.join(parts)}" + \
            (f"; the Sonnet retry ran as {', '.join(son)}" if son else '') + ')'

    def bym(x):  # the values in both by constant, in the tests' order
        return ', '.join(f"{x['by_metric']['both'][m]} {m}" for m in ('kcat', 'Km', 'kcat/Km') if x['by_metric']['both'].get(m))

    def hours(h):
        lo, hi = f"{h['min']:.1f}", f"{h['max']:.1f}"
        return f'{lo} hours apart' if lo == hi else f"a median of {h['median']:.1f} hours apart ({lo} to {hi})"

    def value_why(x, s):
        parts = [f"launch {L} only: {lst(x[s][f'why_only_launch{L}'])}" for L in (1, 2) if x[s][f'why_only_launch{L}']]
        return ('; ' + '; '.join(parts)) if parts else ''

    def cur_line(c, n):
        if not c or not c['papers']:
            return '- Against the curation: none of these papers is covered.'
        t = (f"- Against the curation ({c['papers']} of the {n} papers; {c['curation_values_scored']} curation values): launch 1 "
             f"recall {ci(c['launch1']['recall'])}, precision {ci(c['launch1']['precision'])}; launch 2 recall "
             f"{ci(c['launch2']['recall'])}, precision {ci(c['launch2']['precision'])}.")
        d = c['launch1_minus_launch2']
        if d['recall']['est'] is not None and d['recall']['lo'] is not None:
            t += f" Launch 1 minus launch 2: recall {dif(d['recall'])}, precision {dif(d['precision'])}."
        return t

    L = ['# Run-to-run stability of CatLog\'s frozen workflow', '',
         '## The question',
         'How much does a second reading by the same frozen workflow change, set beside the tests\' differences? In the '
         f'locked test, the frozen copy of CatLog read {n_two} held-out papers in two launches. For one batch of {n_batch} '
         f'papers, the first launch ended at the account\'s usage limit after the readers and verifiers of {n_bfc} of its '
         f'{n_batch} papers had written their files, and before CatLog\'s code stored anything; the same batch was launched '
         f"again, unchanged, {H['minutes_between_launches']} minutes later. The other {oth['papers']} papers' first launches "
         'left no reader file. The question compares the two readings on the papers with complete reader and verifier files '
         'from both launches, leaving out any paper whose second run could see the first run\'s files.', '',
         '## Inputs',
         f'- Papers read twice: `{R}/paper/evidence/locked_test_20261109/result/locked_copy_read_twice.txt`.',
         f'- First launch: `{K}/records/runs/A6-locked/work/old/<PMID>.{{read,verify,prompts}}.<n>.json` (moved there when '
         'the second launch claimed the paper).',
         f'- Second launch: `{K}/records/runs/A6-locked/work/<PMID>.{{read,verify,prompts}}.json` (and '
         '`<PMID>.missed.{read,verify}.json` where its verifier added values).',
         f"- The frozen copy, for the replay of its code checks: `{K}/catlog-copy/` (commit {out['copy_head'][:12]}: `catlog.py`, "
         '`tools/`, `prompts/`, the task files, among them `.claude/workflows/catlog-batch.js`, which names each agent\'s '
         'scratch folder, and the papers\' texts).',
         f'- What the test stored and logged: `{K}/records/runs/A6-locked/{{catalog,bounds,rejected}}.jsonl` and `log.tsv`.',
         f'- Agents, launches and models: `{K}/records/audit/A6-locked/audit.json` and `{K}/records/logs/A6-locked/`.',
         f'- The papers\' scratch files, moved aside at the reset with their file times: `{K}/records/runs/A6-locked/scratch/tmp/` '
         f'(non-image files only) and `{K}/records/a6_tmp_leftovers/` (two verifiers\' private mktemp folders). File names '
         'and times are read; no file is opened.',
         f'- The kit\'s scan of the re-reading agents for files the first launch left: `{K}/records/locked_leftover_scan.json`, '
         f'its code `{R}/paper/evidence/locked_test_20261109/review/auditfix/leftover_scan.py`, and '
         f'`{R}/paper/evidence/locked_test_20261109/PREREGISTRATION.md`.',
         f'- The locked test\'s values and set: `{K}/records/score_locked/private/values.json` and '
         f'`{R}/paper/evidence/locked_test_20261109/result/triage.json`.',
         f'- Stage 2\'s scorer, which loads the checked copy of EnzyExtract\'s manual curation from the kit: '
         f'`{R}/paper/evidence/locked_test_20261109/stage2/score_stage2.py`.', '',
         '## Method',
         f"- **Papers with two complete readings.** {n_cmp} of the {n_two}, all from that batch. Both launches ran the same "
         'launch line on the same frozen copy (a single commit, its pipeline files as committed), on the same Claude Code '
         'version, with claude-opus-5-5 at maximum effort, and every one of these papers\' claim records names the same '
         f"prompts and task text in both launches (read.md {hs['read.md']}, verify.md {hs['verify.md']}, task {hs['task']}). "
         f"Left out of both sets below: the {n_son} papers in which a refusal started the workflow's Sonnet retry in either "
         'launch (the locked test\'s own refusal exits).',
         '- **Could the second run see the first run\'s files?** The frozen task text names each agent\'s scratch folder by '
         'its role and paper (`read-<PMID>`, `verify-<PMID>`), the same in both launches, so the second launch\'s agents '
         'were sent to the folders the first launch had used. When the copy\'s run was reset, the kit moved each paper\'s '
         'non-image scratch aside, keeping file times. A paper counts as exposed when its folders held a file written while '
         f"the first launch ran: {xc['first_launch_files_left']} of the {n_cmp}. The first launch's work files also sat in the copy's "
         'work/old for all of them, outside the agents\' scratch folders; PREREGISTRATION.md says no re-reading agent '
         'opened work/old.',
         f"- **Main set (the question's rule).** The papers with no first-launch file left at the reset, less the "
         f"Sonnet-retry paper among them ({plist(son_main)}): {nm} papers ({plist(S['main'])}). What the reset kept cannot "
         'show page images (they stayed in /tmp) or a first-launch file the second launch overwrote under the same name (it '
         'carries the second launch\'s time).',
         f"- **Wider set.** The {n_cmp} papers less the {n_son} with a Sonnet retry and {plist(op)}, whose second verifier "
         'the kit\'s scan records opening the first verifier\'s scripts (their file times predate the second launch): '
         f"{nw} papers. This set does not meet the question's rule. In {xw['first_launch_files_left']} of its {nw} papers "
         "the first launch's files were in the second launch's folders; in "
         f"{xw['draft_read_file_or_builder_left']} one of them is named as the first reader's draft read file or the "
         "script that builds it (`draft*.json`, `*.read.json`, `make_read*.py`, `build*.py`); in "
         f"{xw['verdict_script_left']} the first verifier's verdict script was there (`write_verdicts*.py`, "
         f"`write_verify*.py`, `make_verdicts*.py`); and in {xw['kept_apart_by_a_second_launch_agent']} a second-launch "
         'agent kept its own files apart (a folder or file named own, mine or r2, or a private mktemp folder), which '
         'PREREGISTRATION.md describes agents doing when they saw others\' files. The scan records one agent opening a '
         'first-launch file, and it is a lower bound: it reads only Read tool paths and Bash command lines that name the '
         'paper\'s /tmp folder, and it counts every path in a command that also runs mkdir, pdftoppm or savefig as written. '
         'So a file a script or heredoc opens, a file named by a relative path after `cd`, and a listing of the folder once '
         'the agent has run mkdir on it do not show.',
         '- **Stages.** Reader: the values the reader wrote. Verifier: the values it kept (confirmed, or fixed with its fix '
         'applied), plus the values it found the reader had skipped and its second check kept. Code checks: what the frozen '
         'copy\'s own `add` stores. The first launch was never stored, so its stored stage is a replay of that `add` on its '
         f"files in a scratch copy. The same replay on the second launch's {n_batch}-paper batch reproduced all "
         f"{rep['values']} values, {rep['censored']} censored values and {rep['rejected']} refusals the test stored, and "
         'every add line it logged, in every field except the two timestamps and the commit stamp (blank in the replay: its '
         'scratch copy is not a git repository), with the transcript model lookup switched off.',
         '- **Values.** kcat, Km and kcat/Km in catalog units, as the tests count them. Censored values (bounds, not '
         'detected) are matched on paper, constant, kind and limit, and Km in mass units with its kcat/Km within its unit, '
         'at each stage.',
         '- **Pairing.** Per paper and constant, one to one on the printed cell (its number before any unit, within 1.5%), '
         'a pair whose stored values also agree going first, then the closest description, as in the tests\' matcher: in '
         'both when the values agree within 1.5%, conflicting when they do not. Values left on both sides are paired on the '
         'value (the same value with the cell written otherwise: in both), then on the description (variant and substrate '
         'at least: conflicting). The rest: one launch only, with the reason the other lacks it (its reader did not read it, '
         'its verifier rejected it, or its code refused it). ' + (
             'The tests\' own matcher, run first instead, gives the same counts at every stage in both sets.' if all(
                 CM[n][s]['with_the_tests_matcher_first'] == {k: CM[n][s][k] for k in ('both', 'conflicting', 'only_launch1', 'only_launch2')}
                 for n in ('main', 'wider') for s in ('reader', 'verifier', 'stored')) else
             'The tests\' own matcher, run first instead, gives other counts (results.json).'),
         '- **Curation.** Both launches\' stored values against EnzyExtract\'s manual curation, with stage 2\'s code (exact '
         'repeats dropped, the same matcher, paper-clustered bootstrap), on each set\'s papers the curation covers.', '',
         '## The numbers',
         '"Papers identical: values / everything": the papers whose values agree in full (all in both, none conflicting, none '
         'alone), then those whose values, censored values and mass-unit values all agree.', '',
         f"### Main set: {nm} papers with no first-launch file left at the reset ({plist(S['main'])})",
         'Non-image files only; a first-launch file the second launch overwrote under the same name would not show.', '',
         head_cols, '|---|---|---|---|---|---|---|---|']
    for s in ('reader', 'verifier', 'stored'):
        L.append(row(names[s], mn[s]))
    hm, hw = H['main'], H['wider']
    st = mn['stored']
    L += ['',
          f"- Papers with identical values after the code checks: {st['papers_identical']} of {st['papers']} (exact 95% interval "
          f"{pc(hm['papers_identical_exact_95'][0])} to {pc(hm['papers_identical_exact_95'][1])}). Of the {st['both']} values in "
          f"both ({bym(st)}), {st['both_exactness']['same_cell_and_value']} print the same cell and convert to exactly the same value; "
          f"{st['labels_disagree_pairs']} pairs have labels that disagree by the tests' rule." + value_why(mn, 'stored'),
          f"- Censored values: {cens_line(mn)}. Mass-unit values: {mn['stored']['mass_units']['launch1']} and "
          f"{mn['stored']['mass_units']['launch2']}.",
          cur_line(out['curation']['main'], nm),
          f"- The two readers of each paper started {hours(hm['hours_between_the_two_readers'])}.", '',
          f"### Wider set: {nw} papers, {xw['first_launch_files_left']} of them with first-launch files in the second "
          "launch's folders",
          head_cols, '|---|---|---|---|---|---|---|---|']
    for s in ('reader', 'verifier', 'stored'):
        L.append(row(names[s], wd[s]))
    st, rd = wd['stored'], wd['reader']
    sw = out['steps']['wider']
    vpp = [d['launch1'] for d in st['per_paper'].values()]
    ends = [sw[k]['ends'] for k in ('launch1', 'launch2')]
    clean = all(set(e) <= {'stored', 'bound'} for e in ends) and not any(sw[k]['verdicts'].get(x) for k in ('launch1', 'launch2')
                                                                          for x in ('reject', 'missing', 'stale'))
    mr = sw['missed_rows']
    L += ['',
          f"- Papers with identical values after the code checks: {st['papers_identical']} of {st['papers']} (exact 95% interval "
          f"{pc(hw['papers_identical_exact_95'][0])} to {pc(hw['papers_identical_exact_95'][1])}); {min(vpp)} to {max(vpp)} "
          f"values per paper. Of the {st['both']} values in both ({bym(st)}), {st['both_exactness']['same_cell_and_value']} print the "
          f"same cell and convert to exactly the same value; {st['labels_disagree_pairs']} pairs have labels that disagree by "
          "the tests' rule." + value_why(wd, 'stored'),
          f"- Paired reader rows with the same reasoning text in both launches: {rd['paired_reader_rows_with_identical_reasoning']} "
          f"of {rd['both']}" + ('; the reasoning text was written anew. That rules out copying rows word for word, not '
                                'consulting a draft.' if rd['paired_reader_rows_with_identical_reasoning'] == 0 else '.'),
          *[f"- Launch {k[-1]}'s verifier: {sw[k]['verdicts'].get('confirm', 0)} rows confirmed, {sw[k]['fixes']} fixed"
            + (f" ({lst(sw[k]['fix_fields'])})" if sw[k]['fixes'] else '')
            + f", {sw[k]['fixes_changing_a_value']} fixes changing a value, "
            + ', '.join(f"{v} {x}" for x, v in sw[k]['verdicts'].items() if x not in ('confirm', 'fix'))
            + ('' if set(sw[k]['verdicts']) <= {'confirm', 'fix'} else ', ')
            + f"{mr[k]['rows']} rows added that its reader had skipped"
            + (f" ({mr[k]['stored_as_censored']} stored as censored values, {mr[k]['held_by_the_other_launchs_reader']} "
               f"of them read by the other launch's own reader; in {plist(mr[k]['papers'])})" if mr[k]['rows'] else '') + '.'
            for k in ('launch1', 'launch2')],
          f"- Where every row ended: launch 1 {lst({FATE_WORDS.get(x, x): v for x, v in ends[0].items()})}; launch 2 "
          f"{lst({FATE_WORDS.get(x, x): v for x, v in ends[1].items()})}"
          + ('. Neither verifier rejected a row and the code refused none.' if clean else '.'),
          f"- Censored values: {cens_line(wd)}. Mass-unit values (Km in mg/mL and its kcat/Km): "
          f"{st['mass_units']['launch1']} and {st['mass_units']['launch2']}, {st['mass_units']['both']} stored by both.",
          cur_line(out['curation']['wider'], nw),
          f"- The two readers of each paper started {hours(hw['hours_between_the_two_readers'])}.", '',
          '### Other sets (code checks stored; the reader stage too where its values differ)',
          '| Set | Papers | Values, launch 1 | Values, launch 2 | In both | Conflicting | One launch only (1 / 2) | '
          'Censored values, launch 1 / 2 / in both | Papers identical: values / everything |',
          '|---|---|---|---|---|---|---|---|---|']
    labels = {'main_with_sonnet_retries': f"Main set with the Sonnet-retry paper ({plist(son_main)})",
              'wider_without_a_draft_left': 'Wider set, only the papers with no first-launch draft read file or read-building script left',
              'wider_without_any_scan_hit': 'Wider set, without the papers where the scan lists a file a second-launch agent read in its folders',
              'wider_with_9495750': 'Wider set with ' + plist(op),
              'wider_with_sonnet_retries': f'Wider set with the {n_son} Sonnet-retry papers'}
    for k, lab in labels.items():
        c = CM[k]
        L.append(row(lab, c['stored'], len(c['papers'])))
        if any(c['reader'][x] != c['stored'][x] for x in ('both', 'conflicting', 'only_launch1', 'only_launch2')):
            L.append(row(lab + ', reader stage', c['reader'], len(c['papers'])))
    ss, cs = out['steps']['wider_with_sonnet_retries'], CM['wider_with_sonnet_retries']
    note = []
    if ss['papers_where_the_readers_differ_on_values']:
        note.append(f"With the Sonnet-retry papers, the two readers differ on values in {plist(ss['papers_where_the_readers_differ_on_values'])}: "
                    f"{cs['reader']['conflicting']} conflicting, {cs['reader']['only_launch1'] + cs['reader']['only_launch2']} in one "
                    f"reader only. The verifiers' fixes changed {ss['launch1']['fixes_changing_a_value']} values in launch 1 and "
                    f"{ss['launch2']['fixes_changing_a_value']} in launch 2; after the code checks, {cs['stored']['papers_identical']} "
                    f"of {cs['stored']['papers']} papers have identical sets of values.")
    # censored values that still differ after the code checks, in the papers these sets add to the wider set
    extra = {}
    for k in labels:
        for p, d in CM[k]['stored']['censored']['per_paper_differing'].items():
            if p not in S['wider']:
                extra[p] = d
    if extra:
        note.append(f"Censored values still differ after the code checks in {len(extra)} of the papers these sets add: "
                    + '; '.join(paper_diff(p, d) for p, d in sorted(extra.items(), key=lambda x: int(x[0]))) + '.')
    if note:
        L += ['', ' '.join(note)]
    pm, pw = out['plain_vs_catlog_launch2_same_papers']['main'], out['plain_vs_catlog_launch2_same_papers']['wider']
    L += ['', '### Beside the tests\' differences',
          'With the same pairing (the tests\' matcher first), the locked test\'s plain reading and the values CatLog stored '
          f"(the second launch) share, on the main set, {pm['both']} of {pm['distinct_values']} distinct values "
          f"({pc(pm['share_both'])}: {pm['conflicting']} conflicting, {pm['only_plain']} in the plain reading only, "
          f"{pm['only_catlog']} in CatLog only, {pm['labels_disagree_pairs']} pairs with labels that disagree; "
          f"{pm['papers_identical']} of {pm['papers']} papers identical), and on the wider set {pw['both']} of "
          f"{pw['distinct_values']} ({pc(pw['share_both'])}: {pw['conflicting']} conflicting, {pw['only_plain']} in the plain "
          f"reading only, {pw['only_catlog']} in CatLog only, {pw['labels_disagree_pairs']} pairs with labels that disagree; "
          f"{pw['papers_identical']} of {pw['papers']} papers identical).", '',
          '## Caveats',
          f"- Only the main set meets the question's rule, and it is small: {nm} papers and {mn['stored']['launch1_values']} "
          f"values ({bym(mn['stored'])}) besides {mn['stored']['censored']['launch1']} censored values. The wider set's "
          'agreement may include copying from the first reading: its second launch ran with the '
          f"first launch's files in its folders for {xw['first_launch_files_left']} of {nw} papers (a draft read file or the "
          f"script that builds one in {xw['draft_read_file_or_builder_left']}; a second-launch agent kept its own files apart "
          f"in {xw['kept_apart_by_a_second_launch_agent']}), one agent is recorded opening them (that paper is left out), and "
          'the scan cannot rule out others.'
          + (' The reasoning text of each paired row differs between the launches, which rules out copying rows word for '
             'word, not reading a draft.' if wd['reader']['paired_reader_rows_with_identical_reasoning'] == 0 else '')
          + ' The transcripts were not read here.',
          '- The main set\'s own limits: page images were not kept, a first-launch file the second launch overwrote under the '
          'same name would not show, and the first launch\'s work files were in work/old throughout.',
          '- One batch, launched twice with the same model and Claude Code version, the two readings about '
          f"{round(hw['hours_between_the_two_readers']['median'])} hours apart. "
          'It says nothing about drift across model versions, and it measures repeatability, not accuracy: a misreading made '
          'in both launches counts as agreement.',
          '- The first launch\'s stored stage comes from the replay; the replay\'s check is that it gives back the second '
          'launch\'s stored rows.',
          f"- The {n_son} Sonnet-retry papers are out of both sets (the other sets show them).",
          '- Labels are compared by the tests\' rule (mutation sets, substrate words, pH, temperature), not word for word.',
          '- The curation is EnzyExtract\'s own reference, not ground truth'
          + (f", and it does not cover {plist(out['curation']['wider']['papers_not_covered'])}." if out['curation']['wider']['papers_not_covered'] else '.'),
          '',
          '## Files',
          '- `stability.py`: the analysis. It writes the three files below and stops if any check fails.',
          '- `results.json`: every number, per set, stage and paper; the exposure of each paper (file names only); the papers '
          'left out and why; the checks passed.',
          '- `pairs.tsv`: each value of the wider set at each stage, paired or not, with its printed cell, unit and labels, and '
          'whether its paper is in the main set (no paper text).',
          '- `README.md`: this file.', '',
          '## How to rerun',
          '```',
          f'python3 -I -B {R}/paper/evidence/stability_20261117/stability.py [--scratch DIR] [--keep]',
          '```',
          'It reads the kit and the main repository and takes about ten seconds. The replay runs in a scratch copy (a '
          'temporary folder unless `--scratch` names one; removed at the end unless `--keep`). Nothing in the kit or the '
          'catalogue is written.']
    (HERE / 'README.md').write_text('\n'.join(L) + '\n')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--worker':
        worker(sys.argv[2], sys.argv[3:])
    else:
        main()
