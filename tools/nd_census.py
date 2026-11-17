"""The n.d. census (2026-11-02): which papers read before the censored-value rule, and NOT on sources/censored_reread.txt,
print a censored kcat, Km or kcat/Km after all?

Why: the phrase and table scan behind that list (tools/censored_scan.py) found only 39% of the papers that print one,
measured on the 690 papers read in full after the rule (where the reader's own n.d. rows are the answer); 37% of the
papers it did not flag still printed one (ND cells and dashes in PDF-text tables, plain wording). No code filter
stands in for reading: a digest that kept 99.6% of the known n.d. papers kept 62% of each text.

What: the 3,526 done papers with values read before the rule and on no list, plus the 180 done papers with no values
read before it, plus 80 papers read after the rule as a blind calibration (40 with stored n.d. values, 40 without),
in groups of up to 4 (sources/nd_census_groups.json, fixed). The saved workflow `catlog-nd-census` runs one lean
`catlog-reader` agent per group (text only, the rule of prompts/read.md "Censored values"); each writes
work/nd_census/group_<n>.json (verdict yes / no / unsure per paper, with quote and reasons).

    python3 tools/nd_census.py status      groups done, papers checked, yes/no/unsure, calibration so far
    python3 tools/nd_census.py next [N]    the args for the next run of N groups (default 300), done groups skipped
    python3 tools/nd_census.py record      at the end: yes papers -> sources/censored_sentences.tsv, then run
                                           tools/censored_scan.py so `catlog.py censored N` claims them

The user (2026-11-02): paused, to finish later at 3 agents; the n.d. pass then works through the list now and then.
"""
import collections, glob, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUPS = ROOT / 'sources' / 'nd_census_groups.json'
OUT = ROOT / 'work' / 'nd_census'


def load():
    spec = json.loads(GROUPS.read_text())
    verdicts = {}
    for f in glob.glob(str(OUT / 'group_*.json')):
        try:
            d = json.load(open(f))
        except ValueError:
            continue
        for v in d.get('verdicts', []):
            verdicts[v['pmid']] = v
    done = [n for n, g in enumerate(spec['groups']) if all(p in verdicts for p in g)]
    return spec, verdicts, done


def status():
    spec, verdicts, done = load()
    cal = spec['calibration']
    calp = set(cal['with_nd']) | set(cal['without_nd'])
    papers = {p for g in spec['groups'] for p in g} - calp
    got = {p: v for p, v in verdicts.items() if p in papers}
    c = collections.Counter(v['verdict'] for v in got.values())
    print(f"groups {len(done):,} of {len(spec['groups']):,} done; papers checked {len(got):,} of {len(papers):,}: "
          f"yes {c['yes']:,}, no {c['no']:,}, unsure {c['unsure']:,}")
    hit = sum(verdicts.get(p, {}).get('verdict') == 'yes' for p in cal['with_nd'])
    seen = sum(p in verdicts for p in cal['with_nd'])
    fp = sum(verdicts.get(p, {}).get('verdict') == 'yes' for p in cal['without_nd'])
    seen_n = sum(p in verdicts for p in cal['without_nd'])
    print(f"calibration: yes for {hit} of {seen} papers with stored n.d. values; yes for {fp} of {seen_n} without")
    if got:
        left = len(papers) - len(got)
        print(f"expected yes among the {left:,} unchecked: about {round(left * c['yes'] / len(got)):,}")


def next_run(n=300):
    spec, _, done = load()
    todo = [g for g in range(len(spec['groups'])) if g not in set(done)][:n]
    if not todo:
        return print('census complete: run `record`')
    lo, hi = todo[0], todo[-1]
    skip = [g for g in done if lo <= g <= hi]
    print(json.dumps({'lanes': 3, 'from': lo, 'to': hi, 'skip': skip}))


def record():
    spec, verdicts, _ = load()
    calp = set(spec['calibration']['with_nd']) | set(spec['calibration']['without_nd'])
    tsv = ROOT / 'sources' / 'censored_sentences.tsv'
    yes_before = {l.split('\t')[0] for l in open(tsv) if l.split('\t')[1:2] == ['yes']}
    new = [v for p, v in sorted(verdicts.items()) if v['verdict'] == 'yes' and p not in calp and p not in yes_before]
    clean = lambda s: ' '.join(str(s or '').split())
    with open(tsv, 'a') as f:
        for v in new:
            f.write('\t'.join([v['pmid'], 'yes', clean(v.get('what')), clean(v.get('quote')), clean(v.get('why')),
                               'whole paper census, 2026-11-02']) + '\n')
    print(f'{len(new):,} yes papers added to {tsv.relative_to(ROOT)}; now run python3 tools/censored_scan.py')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['status']:
        status()
    elif a[:1] == ['next']:
        next_run(int(a[1]) if a[1:] else 300)
    elif a[:1] == ['record']:
        record()
    else:
        print(__doc__)
