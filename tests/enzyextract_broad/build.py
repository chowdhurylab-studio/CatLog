#!/usr/bin/env python3
"""Broad test of CatLog against EnzyExtract (PLAN.md): the frame, the seeded order, every frame paper's values and
disagreements, the blind task files and the score.

  /opt/miniconda3/envs/bioinfo-tools/bin/python -I -B build.py extract    EnzyExtract's database (SI TheData.parquet,
                                                                          sha256 checked) -> work/.../thedata.tsv
  python3 -I -B build.py frame          frame.tsv, order.txt, frame_summary.json (+ work/.../frame_values.json.gz)
  python3 -I -B build.py tasks DIR P..  for papers P: DIR/<P>/ with paper.txt, source.*, paper.supp.txt, task.json;
                                        the key (which reading is whose) -> KEYDIR/key.json, never in DIR
  python3 -I -B build.py score DIR KEYDIR   verdicts DIR/<P>/check1.json -> KEYDIR/results.json and RESULTS.md

What counts (PLAN.md "Values"): CatLog's stored kcat, Km and kcat/Km values at the paper's freeze (tag
paper-catalog-freeze-20261116) on records that hold a kcat, and every kcat, Km and kcat/Km cell of EnzyExtract's
released database (every row of which holds a kcat). EnzyExtract's printed strings are converted with CatLog's units
code, as stage 2 did for every EnzyExtract run; where that code cannot read a string, the database's own number is used.
Exact repeats (same paper, metric, value and labels) are dropped for both, as stage 2's rule 1. Matching: per paper and
metric, one to one, within 1.5% (the head-to-head's matcher). A value the other reading does not match is disputed."""
import csv, gzip, hashlib, importlib.util, json, os, random, re, shutil, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # this checkout (the worktree)
MAIN = Path('<the CatLog folder>')   # data that is not in git (papers, texts, work, the SI)
WORK = MAIN / 'work' / 'enzyextract_broad_20261118'
TAG = 'paper-catalog-freeze-20261116'
SEED = 20261118
PILOT = ['9355750', '10764809', '18823127', '15659395', '28286729']  # checked before the plan (pilot/), never in the sample
SI = MAIN / 'work/top_journal_20261021/benchmarks/enzyextract_si/data/dataset_crude_database/TheData.parquet'
SI_SHA = '903023a9ec5366a4a560c1e11b5f6dca9ef5a27a6686ef633e7297866126290b'   # paper/evidence/h2h_20261101/INPUTS.tsv
EXPORT = MAIN / 'work/paper_freeze_20261116/catlog_wide.jsonl.gz'
EXPORT_SHA = 'e544a0d626682dcc20e34937be6148ef9bafb0e0052fc9936e1b131356553acf'  # FREEZE.md, of the uncompressed file
KIT = Path('<the kit folder>')
COLS = ['pmid', 'enzyme', 'enzyme_full', 'substrate', 'substrate_full', 'mutant', 'organism', 'kcat', 'km', 'kcat_km',
        'temperature', 'pH', 'descriptor', 'kcat_value', 'km_value']
UNITS = ('s^-1', 'mM', 'mM^-1 s^-1')
STATUSES = ('done', 'no_kinetics')


def sha_file(f):
    h = hashlib.sha256()
    with open(f, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def git_show(path):
    return subprocess.run(['git', '-C', str(MAIN), 'show', f'{TAG}:{path}'], capture_output=True, text=True, check=True).stdout


def common():
    """The head-to-head's loaders, units parsing and matcher (paper/evidence/h2h_20261101/common.py), with this
    checkout's tools/units.py imported first so the conversion is the committed one."""
    sys.path.insert(0, str(REPO / 'tools'))
    import units  # noqa: F401
    spec = importlib.util.spec_from_file_location('h2h_common', REPO / 'paper/evidence/h2h_20261101/common.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def pkey(p):
    return (0, int(p)) if p.isdigit() else (1, p)


# ---------------------------------------------------------------------------------------------------------- extract
def extract():
    import pandas as pd
    if sha_file(SI) != SI_SHA:
        sys.exit(f'{SI}: not the checked copy of the SI file')
    t = pd.read_parquet(SI)[COLS]
    for c in COLS:
        t[c] = t[c].map(lambda x: '' if x is None else ('; '.join(map(str, x)) if hasattr(x, '__len__') and not isinstance(x, str) else str(x)))
    WORK.mkdir(parents=True, exist_ok=True)
    t.to_csv(WORK / 'thedata.tsv', sep='\t', index=False)
    print('rows', len(t), '->', WORK / 'thedata.tsv')


# ---------------------------------------------------------------------------------------------------------- frame
def read_list(path, col='pmid'):
    path = Path(path)
    if path.suffix == '.txt':
        return {x.strip() for x in path.read_text().split() if x.strip()}
    with open(path) as f:
        return {r[col].strip() for r in csv.DictReader(f, delimiter='\t') if r.get(col)}


def exclusions():
    """Papers any earlier test, development set or EnzyExtract benchmark used (PLAN.md "Papers")."""
    ev = REPO / 'paper' / 'evidence'
    out = {
        'locked test held-out (sources/holdout_locked.txt at the tag)': set(git_show('sources/holdout_locked.txt').split()),
        "EnzyExtract's 384-paper benchmark (its SI)": read_list(ev / 'h2h_20261101/data/papers_ee384.tsv'),
        'Co-Scientist gold set (CatLog development)': read_list(ev / 'h2h_20261101/data/papers_gold156.tsv'),
        "EnzyExtract's fine-tuning papers (its repo, data/pmids/t2neboth_train.parquet)": read_list(HERE / 'ee_finetune_train_pmids.txt'),
        'test kit: development 165, held-out 374, people 100': read_list(KIT / 'code/paper/planning/w1_kill_test/dev_165.tsv')
        | read_list(KIT / 'code/paper/planning/w1_kill_test/holdout_374.tsv') | read_list(KIT / 'code/tools/w1/people_100.tsv'),
        'random test (paper/evidence/random_papers_20261104)': read_list(ev / 'random_papers_20261104/papers.tsv')
        | read_list(ev / 'random_papers_20261104/papers_more.tsv'),
        'hard cases (paper/evidence/hard_cases_20261102)': read_list(ev / 'hard_cases_20261102/papers.tsv'),
        "people's review of CatLog values (human_review/first_compare.tsv at the tag)":
            {r['pmid'] for r in csv.DictReader(git_show('human_review/first_compare.tsv').splitlines(), delimiter='\t')},
        'the pilot (PLAN.md)': set(PILOT),
    }
    return out


def original(p, lib):
    """The paper's original files on disk: a PDF for the page images if there is one, else the publisher XML."""
    pdf = MAIN / 'papers' / f'{p}.pdf'
    if not pdf.exists() and p in lib and lib[p].endswith('.pdf') and Path(lib[p]).exists():
        pdf = Path(lib[p])
    xml = next((MAIN / 'papers' / f'{p}{s}' for s in ('.jats.xml', '.els.xml') if (MAIN / 'papers' / f'{p}{s}').exists()), None)
    return (pdf if pdf.exists() else None), xml


def ee_clean(m, s):
    """EnzyExtract notations CatLog's parser does not take, rewritten (used only when the string as given is unread):
    '(a ± b) × 10^n', a power of ten whose caret was lost ('× 10-3'), a thousands comma, and 'm^-1 s^-1' for kcat/Km
    (the only reading of it is M^-1 s^-1). Bounds, 'ND', percentages and per-mass activities stay unread."""
    s = s.strip()
    s = re.sub(r'^\(\s*([-+]?[\d.]+\s*(?:±|\+/-|\+-)\s*[\d.]+)\s*\)', r'\1', s)
    s = re.sub(r'(×|x|\*)\s*10\s*[-−]\s*(\d+)', r'\1 10^-\2', s)
    s = re.sub(r'^(\d{1,3}(?:,\d{3})+)(?=[^\d,]|$)', lambda mm: mm.group(1).replace(',', ''), s)
    s = re.sub(r'^\(\s*([-+]?\d[\d.]*)\s*\)', r'\1', s)
    if m == 'kcat/Km':
        s = re.sub(r'(?<![A-Za-zµμ])m\^\s*[-−]\s*1', 'M^-1', s)
        s = re.sub(r'(?i)\b(?:L|dm\^?3)\s*[·.\s]?\s*mmol\^?\s*[-−]\s*1', 'mM^-1', s)
        s = re.sub(r'(?i)\b(?:L|dm\^?3)\s*[·.\s]?\s*mol\^?\s*[-−]\s*1', 'M^-1', s)
        s = s.replace('·', ' ')
    return s


def ee_values(C, rows, p):
    out, unread = [], Counter()
    for k, r in enumerate(rows):
        base = {'src': 'enzyextract', 'pmid': p, 'enzyme': f"{r['enzyme']} {r['enzyme_full']}".strip(), 'organism': r['organism'],
                'substrate': f"{r['substrate']} {r['substrate_full']}".strip(), 'variant': r['mutant'], 'temp': r['temperature'],
                'pH': r['pH'], 'cosub': '', 'where': '', 'quote': r['descriptor']}
        for m, col, own in (('kcat', 'kcat', C.num(r['kcat_value'])), ('Km', 'km', None if C.num(r['km_value']) is None else C.num(r['km_value']) * 1000),
                            ('kcat/Km', 'kcat_km', None)):
            raw = (r[col] or '').strip()
            if not raw or raw.lower() in ('none', 'nan', 'null'):
                continue
            v, how = None, 'catlog_units'
            for s, h in ((raw, 'catlog_units'), (ee_clean(m, raw), 'catlog_units_after_notation_fix')):
                try:
                    v = C.parse_value_unit(m, s)
                except (OverflowError, ValueError, ZeroDivisionError):  # e.g. an exponent too large for a float
                    v = None
                if v is not None:
                    how = h
                    break
            if v is None and own is not None and own > 0:
                v, how = own, 'database_number'
            if v is None or v <= 0:
                unread[m] += 1
                continue
            out.append({**base, 'metric': m, 'value': float(f'{v:.6g}'), 'raw': raw, 'how': how, 'id': f'e{k}:{m}'})
    return out, unread


def lab(x):
    return re.sub(r'\s+', ' ', str(x if x is not None else '')).strip().lower()


def no_repeats(vals):
    seen, out = set(), []
    for v in vals:
        k = (v['pmid'], v['metric'], float(f"{v['value']:.6g}"), lab(v.get('enzyme')), lab(v.get('substrate')), lab(v.get('variant')))
        if k not in seen:
            seen.add(k)
            out.append(v)
    return out


def frame():
    C = common()
    papers = list(csv.DictReader(git_show('papers.tsv').splitlines(), delimiter='\t'))
    st = {r['pmid']: r for r in papers}
    doi = {}
    for r in papers:
        d = (r.get('doi') or '').strip().lower()
        if d:
            doi[d] = r['pmid']
            doi[d.replace('/', '_')] = r['pmid']
    ee = defaultdict(list)
    with open(WORK / 'thedata.tsv') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            k = r['pmid'].strip()
            p = k if k in st else doi.get(k.lower())
            if p:
                ee[p].append(r)
    lib = {}
    if (MAIN / 'library.tsv').exists():
        with open(MAIN / 'library.tsv') as f:
            lib = {r['pmid']: r['path'] for r in csv.DictReader(f, delimiter='\t')}
    excl = exclusions()
    out_by, rows = Counter(), []
    for p in sorted(ee, key=pkey):
        why = None
        if st[p]['status'] not in STATUSES:
            why = f"CatLog status {st[p]['status']}"
        else:
            for name, s in excl.items():
                if p in s:
                    why = name
                    break
        if why is None:
            pdf, xml = original(p, lib)
            if not (MAIN / 'texts' / f'{p}.txt').exists():
                why = 'no text on disk'
            elif pdf is None and xml is None:
                why = 'no original file on disk'
        if why:
            out_by[why] += 1
            continue
        rows.append({'pmid': p, 'status': st[p]['status'], 'text_source': st[p]['text_source'].split(':')[0],
                     'original': 'pdf' if pdf else ('jats.xml' if xml and xml.name.endswith('.jats.xml') else 'els.xml')})
    fr = {r['pmid'] for r in rows}
    fv = fr | set(PILOT)  # the pilot's values are kept too (pilot/ scores them), though the pilot is not in the frame
    pilot_rows = [{'pmid': p, 'status': st[p]['status'], 'text_source': st[p]['text_source'], 'original': ''} for p in PILOT if p in ee]
    # CatLog: the export's records that hold a kcat, and their stored values in catalogue units
    want, h = {}, hashlib.sha256()
    with gzip.open(EXPORT, 'rb') as f:
        for line in f:
            h.update(line)
            m = re.search(rb'"pubmed_id": "([^"]+)"', line[:400])
            if m and m.group(1).decode() in fv:
                r = json.loads(line)
                if C.num(r.get('kcat')) is not None:
                    for rid in r.get('row_ids') or []:
                        want[rid] = r['measurement_id']
    if h.hexdigest() != EXPORT_SHA:
        sys.exit(f'{EXPORT}: not the export of the freeze')
    cat = defaultdict(list)
    proc = subprocess.Popen(['git', '-C', str(MAIN), 'show', f'{TAG}:catalog.jsonl'], stdout=subprocess.PIPE, text=True)
    for line in proc.stdout:
        m = re.match(r'\{"pmid": "([^"]+)"', line)
        if m and m.group(1) not in fv:
            continue
        r = json.loads(line)
        if r['pmid'] in fv and r.get('row_id') in want:
            cat[r['pmid']].append(r)
    proc.wait()
    per, allv = [], {}
    for r in rows + pilot_rows:
        p = r['pmid']
        cv = no_repeats(C.catalog_values(cat.get(p, [])))
        for v in cv:
            v['record'] = want.get(v['id'])
        ev, unread = ee_values(C, ee[p], p)
        ev = no_repeats(ev)
        pairs, cu, eu = C.match(cv, ev)
        allv[p] = {'catlog': cv, 'enzyextract': ev, 'pairs': [(a, b) for a, b, _ in pairs], 'unread': dict(unread)}
        if p not in fr:
            continue
        per.append({**r, 'catlog_values': len(cv), 'ee_values': len(ev), 'agreed': len(pairs), 'catlog_disputed': len(cu),
                    'ee_disputed': len(eu), 'ee_unreadable': sum(unread.values()),
                    'ee_by_database_number': sum(1 for v in ev if v['how'] == 'database_number')})
    order = sorted(fr, key=pkey)
    random.Random(SEED).shuffle(order)
    with open(HERE / 'frame.tsv', 'w') as f:
        w = csv.DictWriter(f, fieldnames=list(per[0]), delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(per)
    (HERE / 'order.txt').write_text('\n'.join(order) + '\n')
    WORK.mkdir(parents=True, exist_ok=True)
    with gzip.open(WORK / 'frame_values.json.gz', 'wt') as f:
        json.dump(allv, f)
    import statistics as stt
    dis = [x['catlog_disputed'] + x['ee_disputed'] for x in per]
    summ = {'tag': TAG, 'seed': SEED, 'database_papers_known_to_catlog': len(ee), 'frame': len(per), 'left_out': dict(out_by),
            'original_on_disk': dict(Counter(x['original'] for x in per)), 'text_source': dict(Counter(x['text_source'] for x in per).most_common(8)),
            'catlog_values': sum(x['catlog_values'] for x in per), 'ee_values': sum(x['ee_values'] for x in per),
            'agreed': sum(x['agreed'] for x in per), 'catlog_disputed': sum(x['catlog_disputed'] for x in per),
            'ee_disputed': sum(x['ee_disputed'] for x in per), 'ee_unreadable_cells': sum(x['ee_unreadable'] for x in per),
            'ee_values_from_the_database_number': sum(x['ee_by_database_number'] for x in per),
            'papers_with_no_dispute': sum(1 for d in dis if d == 0),
            'disputed_per_paper': {'median': stt.median(dis), 'mean': round(stt.mean(dis), 2), 'quartiles': stt.quantiles(dis, n=4)},
            'pilot': PILOT, 'inputs_sha256': {'TheData.parquet': SI_SHA, 'catlog_wide.jsonl': EXPORT_SHA,
                                                        'thedata.tsv': sha_file(WORK / 'thedata.tsv')}}
    (HERE / 'frame_summary.json').write_text(json.dumps(summ, indent=1) + '\n')
    print(json.dumps(summ, indent=1))


# ---------------------------------------------------------------------------------------------------------- tasks
def shown(v, src):
    cell = f"{v.get('raw')} {v.get('raw_unit') or ''}".strip() if src == 'catlog' else v.get('raw')
    return {'metric': v['metric'], 'value_in_catalog_units': v['value'], 'cell_as_this_reading_wrote_it': cell,
            'enzyme': str(v.get('enzyme') or '').strip()[:120], 'substrate': str(v.get('substrate') or '').strip()[:120],
            'variant': str(v.get('variant') or '').strip()[:80]}


CHUNK = 150         # a paper with more values to judge is split into parts of at most this many, one agent each
SECOND_SHARE = 0.10  # a second agent on this share of the papers with a dispute (seeded), for agreement only


def tasks(outdir, keydir, pmids, jobs_name='jobs.json'):
    """Task files for these papers in OUTDIR/<P>/ (paper.txt, source.*, task[_k].json); the key and jobs.json (one filled
    prompt per agent: judge_prompt.md) in KEYDIR. A and B are ordered per paper (seed SEED:pmid), so the order does not
    depend on which papers are built together."""
    with gzip.open(WORK / 'frame_values.json.gz', 'rt') as f:
        allv = json.load(f)
    with open(MAIN / 'library.tsv') as f:
        lib = {r['pmid']: r['path'] for r in csv.DictReader(f, delimiter='\t')}
    outdir, keydir = Path(outdir), Path(keydir)
    keyf = keydir / 'key.json'
    key = json.loads(keyf.read_text()) if keyf.exists() else {}
    prompt = (HERE / 'judge_prompt.md').read_text()
    jobs = []
    for p in sorted(pmids, key=pkey):
        d = allv[p]
        R = {'catlog': d['catlog'], 'enzyextract': d['enzyextract']}
        agreed = {'catlog': {a for a, _ in d['pairs']}, 'enzyextract': {b for _, b in d['pairs']}}
        order = ['catlog', 'enzyextract']
        random.Random(f'{SEED}:{p}').shuffle(order)
        lists, index = {}, {}
        for letter, s in zip('AB', order):
            lists[letter] = [{'id': f'{letter}{k}', 'judge': k not in agreed[s], **shown(v, s)} for k, v in enumerate(R[s])]
            index.update({f'{letter}{k}': [s, k] for k in range(len(R[s]))})
        to_judge = [x['id'] for L in 'AB' for x in lists[L] if x['judge']]
        parts = [to_judge[i:i + CHUNK] for i in range(0, len(to_judge), CHUNK)]
        names = [('task.json', 'check1.json')] if len(parts) <= 1 else [(f'task_{k}.json', f'check1_{k}.json') for k in range(1, len(parts) + 1)]
        key[p] = {'order': dict(zip('AB', order)), 'index': index, 'to_judge': {s: len(R[s]) - len(agreed[s]) for s in R},
                  'parts': [list(n) for n in names] if to_judge else []}
        dd = outdir / p
        dd.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(MAIN / 'texts' / f'{p}.txt', dd / 'paper.txt')
        if (MAIN / 'texts' / f'{p}.supp.txt').exists():
            shutil.copyfile(MAIN / 'texts' / f'{p}.supp.txt', dd / 'paper.supp.txt')
        pdf, xml = original(p, lib)
        if pdf:
            shutil.copyfile(pdf, dd / 'source.pdf')
        if xml:
            shutil.copyfile(xml, dd / 'source.xml')
        for (tname, cname), part in zip(names, parts or [[]]):
            want = set(part)
            task = {'pmid': p, 'units': 'kcat s^-1, Km mM, kcat/Km mM^-1 s^-1',
                    **{f'reading_{L}': [{**x, 'judge': x['id'] in want} for x in lists[L]] for L in 'AB'}}
            (dd / tname).write_text(json.dumps(task, indent=1, ensure_ascii=False))
            if part:
                jobs.append({'pmid': p, 'label': f'check:{p}' + (f'#{tname[5:-5]}' if tname != 'task.json' else ''), 'check': cname,
                             'prompt': prompt.replace('{D}', str(outdir)).replace('{P}', p).replace('task.json', tname).replace('check1.json', cname)})
        print(p, 'to judge', key[p]['to_judge'], 'parts', len(parts), 'order', order)
    judged = sorted({j['pmid'] for j in jobs}, key=pkey)
    second = sorted(random.Random(SEED + 2).sample(judged, max(1, round(SECOND_SHARE * len(judged))) if judged else 0), key=pkey)
    for j in list(jobs):
        if j['pmid'] in second:
            c2 = j['check'].replace('check1', 'check2')
            jobs.append({**j, 'label': j['label'].replace('check:', 'second:'), 'check': c2, 'prompt': j['prompt'].replace(j['check'], c2)})
    keydir.mkdir(parents=True, exist_ok=True)
    keyf.write_text(json.dumps(key, indent=1))
    (keydir / jobs_name).write_text(json.dumps({'outdir': str(outdir), 'second_agent': second, 'jobs': jobs}, indent=1, ensure_ascii=False))
    print(len(jobs), 'agents;', len(judged), 'papers to judge; second agent on', second)


# ---------------------------------------------------------------------------------------------------------- score
RIGHT = 'measured_here_at_this_scale'
VERDICTS = (RIGHT, 'measured_here_other_scale', 'as_printed_but_misprint', 'corrected_misprint', 'repeat_of_one_printed_value',
            'not_this_metric', 'credited_to_earlier_work', 'not_found_in_paper', 'cannot_decide')
WRONG_NUMBER = {'measured_here_other_scale', 'not_this_metric', 'not_found_in_paper'}
# PLAN.md "Rules": (counts as right, counts neither way); everything else not right; cannot_decide is left out and counted
RULES = {
    'printed_here (primary)': ({RIGHT, 'as_printed_but_misprint', 'credited_to_earlier_work'}, {'repeat_of_one_printed_value'}),
    'measured_here': ({RIGHT, 'as_printed_but_misprint'}, set()),
    'printed_here, misprint corrected': ({RIGHT, 'corrected_misprint', 'credited_to_earlier_work'}, {'repeat_of_one_printed_value'}),
    'measured_here, misprint corrected': ({RIGHT, 'corrected_misprint'}, set()),
}


def sign_p(a, b):
    from math import comb
    n, k = a + b, min(a, b)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def boot_diff(rows, B=10000, seed=20261031):
    """Paired paper bootstrap of CatLog minus EnzyExtract recall and precision (per-paper sums)."""
    import numpy as np
    a = {k: np.array([r[k] for r in rows], float) for k in rows[0] if k != 'pmid'}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(rows), (B, len(rows)))
    out = {}
    for name, (num_c, den_c, num_e, den_e) in {'recall': ('c_held', 'ref', 'e_held', 'ref'), 'precision': ('c_held', 'c_n', 'e_held', 'e_n')}.items():
        est_c = a[num_c].sum() / max(a[den_c].sum(), 1)
        est_e = a[num_e].sum() / max(a[den_e].sum(), 1)
        d = a[num_c][idx].sum(1) / np.maximum(a[den_c][idx].sum(1), 1) - a[num_e][idx].sum(1) / np.maximum(a[den_e][idx].sum(1), 1)
        lo, hi = np.percentile(d, [2.5, 97.5])
        out[name] = {'catlog': round(est_c, 4), 'enzyextract': round(est_e, 4), 'diff': round(est_c - est_e, 4),
                     'lo': round(float(lo), 4), 'hi': round(float(hi), 4)}
    return out


def read_checks(dd, parts, n=1):
    """Verdicts of one agent round over a paper's parts; None if a part's file is missing or unreadable."""
    v = {}
    for _, cname in parts:
        f = dd / cname.replace('check1', f'check{n}')
        if not f.exists():
            return None
        try:
            v.update({str(x.get('id')): x.get('verdict') for x in json.loads(f.read_text()).get('verdicts', []) if x.get('verdict') in VERDICTS})
        except json.JSONDecodeError:
            return None
    return v


def score(outdir, keydir):
    with gzip.open(WORK / 'frame_values.json.gz', 'rt') as f:
        allv = json.load(f)
    key = json.loads((Path(keydir) / 'key.json').read_text())
    verdicts, missing, second = {}, {}, {'values': 0, 'same_verdict': 0, 'same_right_or_wrong_number': 0}
    for p in key:
        parts = key[p].get('parts', [['task.json', 'check1.json']] if sum(key[p]['to_judge'].values()) else [])
        if not parts:
            verdicts[p] = {}  # every value agreed: nothing to judge, the paper counts as is
            continue
        v = read_checks(Path(outdir) / p, parts)
        if v is None:
            missing[p] = 'no verdict file'
            continue
        verdicts[p] = v
        v2 = read_checks(Path(outdir) / p, parts, 2)
        for i in (v2 or {}):
            if i in v:
                second['values'] += 1
                second['same_verdict'] += v[i] == v2[i]
                second['same_right_or_wrong_number'] += (v[i] in WRONG_NUMBER) == (v2[i] in WRONG_NUMBER)
    tally = {s: Counter() for s in ('catlog', 'enzyextract')}
    judged = {}
    for p, v in verdicts.items():
        judged[p] = {'catlog': {}, 'enzyextract': {}}
        pairs = allv[p]['pairs']
        agreed = {'catlog': {a for a, _ in pairs}, 'enzyextract': {b for _, b in pairs}}
        for i, (s, k) in key[p]['index'].items():
            if k not in agreed[s]:
                judged[p][s][k] = v.get(i, 'cannot_decide')
                tally[s][judged[p][s][k]] += 1
    res = {'papers': len(key), 'papers_analysed': len(verdicts), 'papers_judged': sum(1 for p in verdicts if verdicts[p]),
           'missing': missing, 'verdicts': {s: dict(tally[s]) for s in tally}, 'second_agent': second, 'rules': {}}
    for rule, (right, neutral) in RULES.items():
        out = {}
        for metric in ('all', 'kcat', 'Km', 'kcat/Km'):
            rows, wrong = [], {'catlog': 0, 'enzyextract': 0, 'discordant_ee_only': 0, 'discordant_catlog_only': 0}
            for p in verdicts:
                d, J = allv[p], judged[p]
                inm = lambda s, k: metric == 'all' or d[s][k]['metric'] == metric  # noqa: E731
                keep = {s: [k for k in range(len(d[s])) if inm(s, k) and J[s].get(k) not in neutral and J[s].get(k) != 'cannot_decide']
                        for s in ('catlog', 'enzyextract')}
                agreed_c, agreed_e = {a for a, _ in d['pairs']}, {b for _, b in d['pairs']}
                ok_c = [k for k in keep['catlog'] if k in agreed_c or J['catlog'].get(k) in right]
                ok_e = [k for k in keep['enzyextract'] if k in agreed_e or J['enzyextract'].get(k) in right]
                # the reference: each agreed pair once, plus each reading's disputed values judged right
                ref = sum(1 for a, _ in d['pairs'] if inm('catlog', a)) + sum(1 for k in ok_c if k not in agreed_c) \
                    + sum(1 for k in ok_e if k not in agreed_e)
                wc = any(J['catlog'].get(k) in WRONG_NUMBER for k in J['catlog'] if inm('catlog', k))
                we = any(J['enzyextract'].get(k) in WRONG_NUMBER for k in J['enzyextract'] if inm('enzyextract', k))
                wrong['catlog'] += wc
                wrong['enzyextract'] += we
                wrong['discordant_ee_only'] += we and not wc
                wrong['discordant_catlog_only'] += wc and not we
                rows.append({'pmid': p, 'ref': ref, 'c_held': len(ok_c), 'c_n': len(keep['catlog']), 'e_held': len(ok_e), 'e_n': len(keep['enzyextract'])})
            wrong['sign_test_p'] = round(sign_p(wrong['discordant_ee_only'], wrong['discordant_catlog_only']), 6)
            out[metric] = {'papers_with_a_wrong_number': wrong, **(boot_diff(rows) if rows else {}),
                           'totals': {k: sum(r[k] for r in rows) for k in ('ref', 'c_held', 'c_n', 'e_held', 'e_n')}}
            if metric == 'all':
                out[metric]['per_paper'] = rows
        res['rules'][rule] = out
    Path(keydir, 'results.json').write_text(json.dumps(res, indent=1) + '\n')
    L = [f"# Scores ({res['papers_analysed']} of {len(key)} papers analysed; {res['papers_judged']} needed a judge)", '',
         f"Verdicts: {res['verdicts']}", f"Second agent: {second}", '']
    for rule, r in res['rules'].items():
        a = r['all']
        if 'recall' not in a:
            continue
        w = a['papers_with_a_wrong_number']
        L += [f"## {rule}", f"- Papers with a wrong number: CatLog {w['catlog']}, EnzyExtract {w['enzyextract']}; on one side only "
              f"{w['discordant_ee_only']} (EnzyExtract) against {w['discordant_catlog_only']} (CatLog); sign test P = {w['sign_test_p']}"]
        for metric in ('all', 'kcat', 'Km', 'kcat/Km'):
            for m in ('recall', 'precision'):
                x = r[metric].get(m)
                if x:
                    L.append(f"- {metric} {m}: CatLog {x['catlog']:.3f}, EnzyExtract {x['enzyextract']:.3f}; CatLog minus EnzyExtract "
                             f"{x['diff']:+.3f} ({x['lo']:+.3f} to {x['hi']:+.3f})")
        L.append('')
    Path(keydir, 'RESULTS.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'extract':
        extract()
    elif cmd == 'frame':
        frame()
    elif cmd == 'tasks':
        tasks(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif cmd == 'score':
        score(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
