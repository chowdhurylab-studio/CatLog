"""CatLog and EnzyExtract against values people checked in their papers: the plan is PLAN.md (commit ce89e0a6, fixed
before any source was scored). Written after that commit; read-only on everything but this folder.

  python3 -I -B writing/research/people_anchored_20261118/build.py

Writes results.json (every count, per paper too) and prints the endpoints.
"""
import csv
import importlib.util
import json
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TAG = 'paper-catalog-freeze-20261116'
TOL = 0.015
SEED, B = 20261031, 10000
METRICS = ('kcat', 'Km', 'kcat/Km')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import catlog  # noqa: E402
import human_review as HR  # noqa: E402

spec = importlib.util.spec_from_file_location('broad', ROOT / 'writing/research/enzyextract_broad_20261118/build.py')
BROAD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BROAD)


def git_show(path):
    return subprocess.run(['git', '-C', str(ROOT), 'show', f'{TAG}:{path}'], capture_output=True, text=True, check=True).stdout


def pos(x):
    return isinstance(x, (int, float)) and x > 0


# ------------------------------------------------------------------------------------------------- reference values
def reference():
    conf, bad = defaultdict(list), defaultdict(list)       # paper: [(metric, value, category or db, key)]
    n_rec = Counter()
    for d in HR._decisions():
        if d.get('v2_pack'):
            continue                                       # CatLog's own rows shown to people: not this reference
        n_rec['earlier catalogue records'] += 1
        vals = [(m, d.get(m)) for m in METRICS if pos(d.get(m)) and not (m == 'kcat/Km' and d.get('kcat/Km_derived'))]
        if d['status'] == 'approved' and not d.get('disagree'):
            n_rec['confirmed records'] += 1
            for m, v in vals:
                conf[d['pmid']].append((m, float(v), d.get('old_source_db') or '', d['key']))
        elif d['status'] == 'rejected' and d.get('category') in ('no_literature', 'value') and d['pmid'] not in HR.CLEARED:
            n_rec['not-found or wrong records'] += 1
            for m, v in vals:
                bad[d['pmid']].append((m, float(v), d.get('category'), d['key']))
    return conf, bad, n_rec


# ----------------------------------------------------------------------------------------------------------- papers
def papers(conf, bad):
    rows = list(csv.DictReader(git_show('papers.tsv').splitlines(), delimiter='\t'))
    st = {r['pmid']: r['status'] for r in rows}
    doi = {}
    for r in rows:
        d = (r.get('doi') or '').strip().lower()
        if d:
            doi[d] = r['pmid']
            doi[d.replace('/', '_')] = r['pmid']
    ee_rows = defaultdict(list)
    with open(BROAD.WORK / 'thedata.tsv') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            k = r['pmid'].strip()
            p = k if k in st else doi.get(k.lower())
            if p:
                ee_rows[p].append(r)
    ev = ROOT / 'paper' / 'evidence'
    tuned = {
        "EnzyExtract's 384-paper benchmark": BROAD.read_list(ev / 'h2h_20261101/data/papers_ee384.tsv'),
        "EnzyExtract's fine-tuning papers": BROAD.read_list(BROAD.HERE / 'ee_finetune_train_pmids.txt'),
        'Co-Scientist gold set (CatLog development)': BROAD.read_list(ev / 'h2h_20261101/data/papers_gold156.tsv'),
        "test kit's development papers": BROAD.read_list(BROAD.KIT / 'code/paper/planning/w1_kill_test/dev_165.tsv'),
    }
    exposed = {r['pmid'] for r in csv.DictReader(open(ROOT / 'human_review/exposed.tsv'), delimiter='\t')}
    acts = {'drop', 'reread', 'unitfix', 'cellfix', 'recover', 'pmfix', 'limitfix'}
    by_review = set()
    for ln in git_show('log.tsv').splitlines():
        p = ln.split('\t')
        if len(p) > 3 and p[2] in acts:
            text = '\t'.join(p[3:]).replace('Verify you are human', '')
            if re.search(r'review|people|human', text, re.I):
                by_review.add(p[1])
    out, why = [], Counter()
    for p in sorted(set(conf) | set(bad), key=BROAD.pkey):
        if st.get(p) != 'done':
            why[f"CatLog status {st.get(p, 'not in papers.tsv')}"] += 1
        elif p not in ee_rows:
            why['not in EnzyExtract\'s database'] += 1
        elif any(p in s for s in tuned.values()):
            why[next(n for n, s in tuned.items() if p in s)] += 1
        elif p in exposed:
            why['a reading agent saw database values or earlier-catalogue files'] += 1
        elif p in by_review:
            why["catalogue rows changed in response to people's review"] += 1
        else:
            out.append(p)
    return out, why, ee_rows


# ---------------------------------------------------------------------------------------------------------- sources
def catlog_values():
    v = defaultdict(list)
    for ln in git_show('catalog.jsonl').splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r.get('metric') in METRICS and catlog.molar(r) is not None and pos(r.get('value')):
            v[str(r['pmid'])].append((r['metric'], float(r['value'])))
    return v


def ee_values(ee_rows, keep):
    C = BROAD.common()
    v, unread = {}, Counter()
    for p in keep:
        vals, u = BROAD.ee_values(C, ee_rows[p], p)
        unread.update(u)
        v[p] = [(x['metric'], float(x['value'])) for x in BROAD.no_repeats(vals)]
    return v, unread


# --------------------------------------------------------------------------------------------------------- matching
def held(ref, src):
    """Indices of ref values (metric, value, ...) the source holds: within TOL of the reference, one to one, closest
    pairs first, per metric."""
    out = set()
    for m in METRICS:
        R = [(i, r[1]) for i, r in enumerate(ref) if r[0] == m]
        S = [s[1] for s in src if s[0] == m]
        pairs = sorted((abs(s - rv) / rv, i, j) for i, rv in R for j, s in enumerate(S) if abs(s - rv) <= TOL * rv)
        used_r, used_s = set(), set()
        for _, i, j in pairs:
            if i not in used_r and j not in used_s:
                used_r.add(i)
                used_s.add(j)
        out |= used_r
    return out


def sign_p(a, b):
    n, k = a + b, min(a, b)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def boot(per, key_n, key_c, key_e):
    rng = random.Random(SEED)
    ps = list(per)
    diffs = []
    for _ in range(B):
        s = [per[ps[rng.randrange(len(ps))]] for _ in ps]
        n = sum(x[key_n] for x in s)
        if n:
            diffs.append((sum(x[key_c] for x in s) - sum(x[key_e] for x in s)) / n)
    diffs.sort()
    return diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]


def main():
    conf, bad, n_rec = reference()
    keep, why, ee_rows = papers(conf, bad)
    cv = catlog_values()
    ev, unread = ee_values(ee_rows, keep)
    per, by_metric, by_db, by_cat = {}, defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    for p in keep:
        c_src, e_src = cv.get(p, []), ev.get(p, [])
        rc, rb = conf.get(p, []), bad.get(p, [])
        hc_c, hc_e = held(rc, c_src), held(rc, e_src)
        hb_c, hb_e = held(rb, c_src), held(rb, e_src)
        per[p] = {'confirmed': len(rc), 'conf_catlog': len(hc_c), 'conf_ee': len(hc_e),
                  'conf_neither': len(set(range(len(rc))) - hc_c - hc_e),
                  'bad': len(rb), 'bad_catlog': len(hb_c), 'bad_ee': len(hb_e),
                  'catlog_values': len(c_src), 'ee_values': len(e_src)}
        for i, r in enumerate(rc):
            for tab, k in ((by_metric, r[0]), (by_db, r[2] or 'unknown')):
                tab[k]['n'] += 1
                tab[k]['catlog'] += i in hc_c
                tab[k]['ee'] += i in hc_e
        for i, r in enumerate(rb):
            by_cat[r[2]]['n'] += 1
            by_cat[r[2]]['catlog'] += i in hb_c
            by_cat[r[2]]['ee'] += i in hb_e
    n_conf = sum(x['confirmed'] for x in per.values())
    c_conf = sum(x['conf_catlog'] for x in per.values())
    e_conf = sum(x['conf_ee'] for x in per.values())
    lo, hi = boot({p: x for p, x in per.items() if x['confirmed']}, 'confirmed', 'conf_catlog', 'conf_ee')
    pb_c = sum(1 for x in per.values() if x['bad_catlog'])
    pb_e = sum(1 for x in per.values() if x['bad_ee'])
    only_c = sum(1 for x in per.values() if x['bad_catlog'] and not x['bad_ee'])
    only_e = sum(1 for x in per.values() if x['bad_ee'] and not x['bad_catlog'])
    res = {
        'plan': 'PLAN.md, commit ce89e0a6',
        'reference_records': dict(n_rec),
        'papers_with_reference': len(set(conf) | set(bad)), 'papers_left_out': dict(why), 'papers_scored': len(keep),
        'endpoint1_confirmed': {'values': n_conf, 'catlog_held': c_conf, 'ee_held': e_conf,
                                'catlog_share': round(c_conf / n_conf, 4) if n_conf else None,
                                'ee_share': round(e_conf / n_conf, 4) if n_conf else None,
                                'diff': round((c_conf - e_conf) / n_conf, 4) if n_conf else None,
                                'ci95': [round(lo, 4), round(hi, 4)],
                                'neither': sum(x['conf_neither'] for x in per.values()),
                                'papers': sum(1 for x in per.values() if x['confirmed'])},
        'endpoint2_not_found_or_wrong': {'values': sum(x['bad'] for x in per.values()),
                                         'papers_with_such_values': sum(1 for x in per.values() if x['bad']),
                                         'catlog_held': sum(x['bad_catlog'] for x in per.values()),
                                         'ee_held': sum(x['bad_ee'] for x in per.values()),
                                         'papers_catlog': pb_c, 'papers_ee': pb_e, 'only_catlog': only_c,
                                         'only_ee': only_e, 'sign_test_p': sign_p(only_c, only_e)},
        'by_metric': {k: dict(v) for k, v in by_metric.items()},
        'by_database': {k: dict(v) for k, v in by_db.items()},
        'endpoint2_by_category': {k: dict(v) for k, v in by_cat.items()},
        'ee_unreadable_cells': dict(unread),
        'per_paper': per,
    }
    (HERE / 'results.json').write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != 'per_paper'}, indent=1))


if __name__ == '__main__':
    main()
