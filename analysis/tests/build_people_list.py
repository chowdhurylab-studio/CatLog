#!/usr/bin/env python3
"""W1 second scorecard: about 100 papers whose CatLog values people checked by hand (the human review), sampled with a
seed and stratified by text kind and publication year; read-only on the main folder.

  python3 tools/w1/build_people_list.py [--n 100] [--out tools/w1/people_100.tsv] [--key KEYFILE]

Eligible: a paper with at least one usable verdict in human_review/compare.tsv (HUMAN_REVIEW.md "How v2 is compared":
one line per reviewed value, with its value in catalog units), status `done` in papers.tsv, its text and its original
file on disk, and in neither dev_165.tsv nor holdout_374.tsv (nor sources/holdout_locked.txt). Usable verdicts:
  approved          approved by a reviewer, not a kcat/Km the old pipeline derived (bucket `derived`) and not an
                    approval whose comment objects to the value (`approved_with_objection`);
  stated            a value a reviewer typed into a comment as printed in the paper (`stated_found`/`stated_missing`);
  rejected_dispute  a rejection that disputes the number (buckets v2_has_same, v2_has_different, v2_lacks_rejected, or a
                    value/unit/substrate/variant/evidence objection on a paper v2 had not read then).
Rejections of the row itself (missing value, organism, DOI, duplicate: `row_objection`) are counted, never scored.
In the scorer's key (key_rows, --key) a rejection on a paper the human-review guideline checked against the paper and
cleared (`CLEARED` in tools/human_review.py: not a wrong number) is `rejected_cleared`, never a disputed value
(REVIEW.md 3.3: all 11 disputed values of the 3 certainty papers below are such); the sample itself keeps the
classification it was drawn with, so this script still rebuilds people_100.tsv byte for byte.
Every eligible paper with a disputed value is taken (`drawn` = certainty: only 3 papers on 2026-11-01, so that the
"rejected values repeated" count has cases at all); the rest of the n are drawn at random. Strata: text kind (pdf,
xml, ocr) x publication year (<=1999, 2000-2009, 2010-2019, >=2020; PubMed's year from sources/ref/pubmed_years.jsonl),
proportional allocation (largest remainder), each stratum drawn with one random.Random(SEED_PEOPLE) in sorted stratum
order from its papers sorted by PMID.
--key writes the scorer's per-value key for the sampled papers (no reviewer names or comments): it belongs in the
eval's keys/ folder, which no agent may open."""
import argparse, collections, glob, json, os, random, re, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402

M = W.MAIN
VALUE_CATS = {'value', 'unit', 'substrate', 'variant', 'evidence'}
REJECT_BUCKETS = {'v2_has_same', 'v2_has_different', 'v2_lacks_rejected'}
KEY_COLS = ['pmid', 'key', 'metric', 'status', 'kind', 'human_value', 'substrate', 'mutations', 'category', 'sweep',
            'bucket']
COLS = ['pmid', 'drawn', 'stratum', 'text_kind', 'year', 'year_bin', 'glyph_warning', 'supp_text', 'text_route',
        'approved_values', 'stated_values', 'rejected_value_disputes', 'rejected_row_objections', 'derived_excluded',
        'objection_excluded', 'sweep_values', 'reviewers', 'v1_entries', 'v2_entries', 'catlog_status_now',
        'catlog_rows_now', 'cited_by_rules_or_code']


def verdict_kind(r, cleared=frozenset()):
    if r['bucket'] in ('stated_found', 'stated_missing'):
        return 'stated'
    if r['status'] == 'approved':
        return {'derived': 'derived', 'approved_with_objection': 'objection'}.get(r['bucket'], 'approved')
    if r['status'] == 'rejected':
        if r['pmid'] in cleared:
            return 'rejected_cleared'
        if r['bucket'] in REJECT_BUCKETS or (r['bucket'] == 'paper_not_read' and r['category'] in VALUE_CATS):
            return 'rejected_dispute'
        return 'row_objection'
    return 'other'


def year_bin(y):
    if not y:
        return 'unknown'
    return '<=1999' if y <= 1999 else '2000-2009' if y <= 2009 else '2010-2019' if y <= 2019 else '>=2020'


def pubmed_years():
    out = {}
    with open(M / 'sources' / 'ref' / 'pubmed_years.jsonl') as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            s = d.get('sortpubdate') or d.get('pubdate') or ''
            if s[:4].isdigit():
                out[str(d.get('uid'))] = int(s[:4])  # a later line for the same PMID wins (publication_years.py)
    return out


def locked_at_head():
    t = W.git(W.REPO, 'show', 'HEAD:sources/holdout_locked.txt')
    return {w for line in t.splitlines() if not line.startswith('#') for w in line.split()}


def text_kind(p, src):
    head = open(M / 'texts' / f'{p}.txt', errors='replace').read(3000)
    k = 'ocr' if '## OCR TEXT' in head else 'pdf' if '.pdf' in src.lower() else 'xml'
    return k, head.startswith('GLYPH WARNING')


def allocate(sizes, n):
    """Proportional allocation with the largest remainder; never more than a stratum holds."""
    tot = sum(sizes.values())
    if tot <= n:
        return dict(sizes)
    raw = {k: n * v / tot for k, v in sizes.items()}
    got = {k: min(sizes[k], int(raw[k])) for k in sizes}
    for k in sorted(sizes, key=lambda k: (-(raw[k] - int(raw[k])), k)):
        if sum(got.values()) >= n:
            break
        if got[k] < sizes[k]:
            got[k] += 1
    return got


def cited(pmids):
    """Where a commit message, CLAUDE.md, HUMAN_REVIEW.md, catlog.py, a tool, a prompt or a hand-checked source line
    names the paper (as the kit's build_paper_lists.py)."""
    texts = {'gitlog': subprocess.run(['git', '--no-optional-locks', '-C', str(M), 'log', '--format=%h %s%n%b'],
                                      capture_output=True, text=True).stdout}
    for f in [M / 'CLAUDE.md', M / 'HUMAN_REVIEW.md', M / 'catlog.py', M / 'sources/natural_forms.tsv',
              M / 'sources/implausible_as_printed.tsv'] + [Path(x) for x in glob.glob(str(M / 'tools/*.py'))] + \
            [Path(x) for x in glob.glob(str(M / 'prompts/*.md'))]:
        if f.exists():
            texts[str(f.relative_to(M))] = f.read_text(errors='replace')
    out = collections.defaultdict(set)
    for name, t in texts.items():
        for p in pmids:
            if re.search(r'(?<![0-9A-Za-z])' + re.escape(p) + r'(?![0-9])', t):
                out[p].add(name)
    return out


def catalog_rows(pmids):
    n = collections.Counter()
    pat = re.compile(r'^\{"pmid": "([^"]+)"')
    with open(M / 'catalog.jsonl') as fh:
        for line in fh:
            m = pat.match(line)
            if m and m.group(1) in pmids:
                n[m.group(1)] += 1
    return n


def build(n=100):
    st = {r['pmid']: r for r in W.read_tsv(M / 'papers.tsv')}
    comp = W.read_tsv(M / 'human_review' / 'compare.tsv')
    dec = [json.loads(line) for line in open(M / 'human_review' / 'decisions.jsonl') if line.strip()]
    excluded = set(W.dev_papers()) | set(W.holdout_papers()) | locked_at_head()
    years = pubmed_years()
    counts = collections.defaultdict(collections.Counter)
    rows_by = collections.defaultdict(list)
    for r in comp:
        k = verdict_kind(r)
        counts[r['pmid']][k] += 1
        counts[r['pmid']]['sweep'] += r.get('sweep') == 'True'
        rows_by[r['pmid']].append({**r, 'kind': k})
    reviewers, v1, v2 = collections.defaultdict(set), collections.Counter(), collections.Counter()
    for d in dec:
        p = str(d.get('pmid') or '')
        reviewers[p].update(x for x in (d.get('reviewers') or {}) if x)
        (v2 if d.get('v2_pack') else v1)[p] += 1
    elig, why = {}, collections.Counter()
    for p, c in counts.items():
        if p in excluded:
            why['dev_or_holdout'] += 1
            continue
        r = st.get(p)
        if not r or r['status'] != 'done':
            why['not_done'] += 1
            continue
        if not (M / 'texts' / f'{p}.txt').exists():
            why['no_text'] += 1
            continue
        path = r['text_source'].partition(':')[2]
        if not path or not os.path.exists(path):
            why['no_original'] += 1
            continue
        if c['approved'] + c['stated'] + c['rejected_dispute'] == 0:
            why['no_usable_verdict'] += 1
            continue
        k, gw = text_kind(p, r['text_source'])
        y = years.get(p)
        elig[p] = {'pmid': p, 'text_kind': k, 'year': y or '', 'year_bin': year_bin(y), 'stratum': f'{k}|{year_bin(y)}',
                   'glyph_warning': int(gw), 'supp_text': int((M / 'texts' / f'{p}.supp.txt').exists()),
                   'text_route': r['text_source'].partition(':')[0], 'approved_values': c['approved'],
                   'stated_values': c['stated'], 'rejected_value_disputes': c['rejected_dispute'],
                   'rejected_row_objections': c['row_objection'], 'derived_excluded': c['derived'],
                   'objection_excluded': c['objection'], 'sweep_values': c['sweep'], 'reviewers': len(reviewers[p]),
                   'v1_entries': v1[p], 'v2_entries': v2[p], 'catlog_status_now': r['status']}
    certain = sorted((p for p, e in elig.items() if e['rejected_value_disputes']), key=W.pmid_key)
    strata = collections.defaultdict(list)
    for p, e in elig.items():
        if p not in certain:
            strata[e['stratum']].append(p)
    alloc = allocate({k: len(v) for k, v in strata.items()}, max(0, n - len(certain)))
    rng = random.Random(W.SEED_PEOPLE)
    picked = list(certain)
    for k in sorted(strata):
        picked += rng.sample(sorted(strata[k], key=W.pmid_key), alloc[k])
    picked.sort(key=W.pmid_key)
    for p in picked:
        elig[p]['drawn'] = 'certainty (disputed value)' if p in certain else 'random'
    rows_now, cit = catalog_rows(set(picked)), cited(picked)
    out = [{**elig[p], 'catlog_rows_now': rows_now[p], 'cited_by_rules_or_code': ';'.join(sorted(cit[p]))} for p in picked]
    info = {'eligible': len(elig), 'excluded': dict(why), 'strata_eligible': {k: len(v) for k, v in sorted(strata.items())},
            'certainty': certain, 'allocated': dict(sorted(alloc.items())), 'seed': W.SEED_PEOPLE,
            'sources_sha256': {'human_review/compare.tsv': W.sha256(M / 'human_review' / 'compare.tsv'),
                               'human_review/decisions.jsonl': W.sha256(M / 'human_review' / 'decisions.jsonl'),
                               'sources/ref/pubmed_years.jsonl': W.sha256(M / 'sources' / 'ref' / 'pubmed_years.jsonl')}}
    key = [{**r, 'mutations': r.get('mutations', '')} for p in picked for r in rows_by[p]]
    return out, key, info


def cleared_papers():
    """Papers whose value rejections the human-review guideline checked against the paper and cleared (CLEARED in this
    branch's tools/human_review.py; HUMAN_REVIEW.md "Guideline": none is a wrong number)."""
    tools = str(W.REPO / 'tools')
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import human_review
    return frozenset(human_review.CLEARED)


def key_rows(pmids):
    """The scorer's per-value key for these papers, from compare.tsv as it is now (no reviewer names or comments);
    rejections on cleared papers are `rejected_cleared`."""
    pm, cleared = set(pmids), cleared_papers()
    return [{**{k: r.get(k, '') for k in KEY_COLS}, 'kind': verdict_kind(r, cleared)}
            for r in W.read_tsv(M / 'human_review' / 'compare.tsv') if r['pmid'] in pm]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--n', type=int, default=100)
    ap.add_argument('--out', default=str(W.W1 / 'people_100.tsv'))
    ap.add_argument('--key', help='also write the per-value key here (the eval keys/ folder)')
    ap.add_argument('--info', help='write the eligibility counts as JSON here')
    a = ap.parse_args()
    out, key, info = build(a.n)
    W.write_tsv(a.out, out, COLS)
    if a.key:
        W.write_tsv(a.key, key, KEY_COLS)
    if a.info:
        W.write_json(a.info, info)
    tot = collections.Counter()
    for r in out:
        for c in ('approved_values', 'stated_values', 'rejected_value_disputes', 'rejected_row_objections'):
            tot[c] += int(r[c])
    print(f"people papers: {len(out)} of {info['eligible']} eligible; values: {dict(tot)}; "
          f"strata: {info['allocated']}")


if __name__ == '__main__':
    main()
