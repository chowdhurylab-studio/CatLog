#!/usr/bin/env python3
"""Draw the random set: papers CatLog has finished, read once by a plain model and compared with the catalogue.

Frame: status done in papers.tsv, at least one value in catalog.jsonl, an original file on disk (PDF or publisher XML,
so a judge can see the page), not an OCR-only text, and none of: the locked test set (sources/holdout_locked.txt), the
165 development papers, the 100 people-checked papers, the pilot's 10, the 69 hard-case papers.
Draw: random.Random(20261104).sample of the frame, sorted by PMID first so the draw does not depend on file order.
Writes papers.tsv here (pmid, values in the catalogue, text kind).

python3 select.py more K: replacements. The test runs on one model and one effort for every session (the owner,
2026-11-04), so a paper that model's safety filter refuses has no read. K more papers are drawn, once, from the frame
as it stands now, less the first 150: random.Random(SEED + 1).sample in the sorted frame, kept in the order drawn and
read in that order until 150 papers have a read. Writes papers_more.tsv (with the order) and frame_more.txt (the
frame it drew from, so that the draw can be repeated)."""
import csv, json, os, random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[2]
KIT = MAIN / 'paper' / 'planning' / 'w1_kill_test'
EV = Path('<the kit folder>')
N, SEED = 150, 20261104


def ids(path):
    return {t for line in open(path) if not line.startswith('#') for t in line.split()
            if re.fullmatch(r'\d{4,9}|NP[0-9A-F]{8}', t)}


def frame_now():
    locked = ids(MAIN / 'sources' / 'holdout_locked.txt')
    dev = {r['pmid'] for r in csv.DictReader(open(KIT / 'dev_165.tsv'), delimiter='\t')}
    people = {r['pmid'] for r in csv.DictReader(open(EV / 'code' / 'tools' / 'w1' / 'people_100.tsv'), delimiter='\t')}
    pilot = set(open(EV / 'records' / 'orders' / 'pilot.txt').read().split())
    hard = {r['pmid'] for r in json.load(open(MAIN / 'paper' / 'evidence' / 'hard_cases_20261102' / 'summary.json'))}
    hard |= {r['pmid'] for r in csv.DictReader(open(MAIN / 'paper' / 'evidence' / 'hard_cases_20261102' / 'papers.tsv'), delimiter='\t')}
    out_of = locked | dev | people | pilot | hard
    nvals = {}
    with open(MAIN / 'catalog.jsonl') as f:
        for line in f:
            try:
                p = str(json.loads(line).get('pmid'))
            except json.JSONDecodeError:
                continue
            nvals[p] = nvals.get(p, 0) + 1
    frame = []
    for r in csv.DictReader(open(MAIN / 'papers.tsv'), delimiter='\t'):
        p = r['pmid']
        if r['status'] != 'done' or p in out_of or not nvals.get(p):
            continue
        path = r['text_source'].partition(':')[2]
        if not path or not os.path.exists(path) or not path.lower().endswith(('.pdf', '.xml')):
            continue
        t = MAIN / 'texts' / f'{p}.txt'
        if not t.exists() or '## OCR TEXT' in t.read_text(errors='replace')[:3000]:
            continue
        frame.append((p, nvals[p], 'pdf' if path.lower().endswith('.pdf') else 'xml'))
    return sorted(frame)


def more(k):
    if (HERE / 'papers_more.tsv').exists():
        sys.exit('papers_more.tsv exists: the replacements are drawn once')
    first = {r['pmid'] for r in csv.DictReader(open(HERE / 'papers.tsv'), delimiter='\t')}
    pool = [x for x in frame_now() if x[0] not in first]
    draw = random.Random(SEED + 1).sample(pool, k)
    (HERE / 'frame_more.txt').write_text(''.join(f'{p}\t{n}\t{t}\n' for p, n, t in pool))
    with open(HERE / 'papers_more.tsv', 'w') as f:
        f.write('pmid\tcatalog_values\ttext_kind\torder\n')
        for i, (p, n, t) in enumerate(draw, 1):
            f.write(f'{p}\t{n}\t{t}\t{i}\n')
    print(f'frame {len(pool)} papers less the first 150; drew {k} replacements (seed {SEED + 1}), in the order to read them')


def main():
    if len(sys.argv) == 3 and sys.argv[1] == 'more':
        return more(int(sys.argv[2]))
    if (HERE / 'papers.tsv').exists():
        sys.exit('papers.tsv exists: the set is drawn once')
    frame = frame_now()
    draw = sorted(random.Random(SEED).sample(frame, N))
    with open(HERE / 'papers.tsv', 'w') as f:
        f.write('pmid\tcatalog_values\ttext_kind\n')
        for p, n, k in draw:
            f.write(f'{p}\t{n}\t{k}\n')
    print(f'frame {len(frame)} papers; drew {len(draw)} (seed {SEED}): {sum(n for _, n, _ in draw)} catalogue values, '
          f'{sum(1 for *_, k in draw if k == "pdf")} PDF, {sum(1 for *_, k in draw if k == "xml")} XML')


if __name__ == '__main__':
    main()
