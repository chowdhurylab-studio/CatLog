"""Freeze people's review for the paper (the owner, 2026-11-16: "this is a wrap from human review (for the paper not
overall) the website and db will keep growing but wrap for paper data report freeze").

Recomputes, once, every number the manuscript and its figures take from people's review, with the same code the
status line and Fig. 1 use (tools/human_review._decisions / review_summary, tools/site_release._one_review /
_review_basis; papers counted as writing/fig1_v8/build_fig1_v8.py counts them, lines 960-1010), asserts them against
each other and against `catlog.py status`, and writes next to itself:
  numbers.json            the frozen numbers, with their definitions
  review_inputs.tar.xz    every input file of the review as it stood (results files people sent, pack indexes,
                          decisions.jsonl, the agents' checks of differences, could-not-check notes): the evidence,
                          in git, since human_review/ is not
  review_stats.txt        the full `catlog.py review stats` output of the freeze
Later results files keep going into human_review/ for the website and the catalogue; the paper reads only this folder.
Run it again only if the owner moves the freeze."""
import csv, hashlib, io, json, re, subprocess, sys, tarfile, time
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tools'))
import catlog, human_review, site_release

sha = lambda b: hashlib.sha256(b).hexdigest()
rows = human_review._decisions()
summary = human_review.review_summary(rows)
one = site_release._one_review(summary)
basis, nopaper = site_release._review_basis(one)
n_checked, n_nopaper = basis['entries'], nopaper or 0
assert n_checked + n_nopaper == len(rows), (n_checked, n_nopaper, len(rows))

# the status line, verbatim, and its numbers (paper/manuscript/numbers_build.py reads these five)
status = subprocess.run([sys.executable, 'catlog.py', 'status'], cwd=ROOT, capture_output=True, text=True).stdout
line = next(l for l in status.splitlines() if 'Human review:' in l)
m = re.search(r'people checked ([\d,]+) records against their papers \(([\d,]+) more had no PMID or DOI\); no value disputed '
              r'on ([\d,]+) \([^)]*\); (?:the ([\d,]+) disputed values? (?:are|is) as printed|([\d,]+) of the [\d,]+ disputed values '
              r'are as printed)', line)
num = lambda s: int(s.replace(',', ''))
checked, nop, undisputed = num(m.group(1)), num(m.group(2)), num(m.group(3))
as_printed = num(m.group(4) or m.group(5))
assert (checked, nop) == (n_checked, n_nopaper), ((checked, nop), (n_checked, n_nopaper))
disputed = checked - undisputed
assert as_printed == disputed, 'a disputed value is not yet checked against its paper: settle it before freezing'

# papers: the Fig. 1 builder's rule (a record's paper is its PMID or stand-in id, else its DOI; records whose paper the
# review file lost come from writing/fig1_v8/ref/review_papers_recovered.tsv)
pid = lambda r: str(r.get('pmid') or '').strip()
doi = lambda r: str(r.get('doi') or '').strip().lower()
has = [r for r in rows if r.get('checkable') or r.get('doi') or r.get('v2_pack')]
assert len(has) == n_checked
by_pmid = {pid(r) for r in has if pid(r)}
by_doi = {doi(r) for r in has if not pid(r) and doi(r)}
assert all(p.isdigit() or catlog.STANDIN.fullmatch(p) for p in by_pmid)
assert not by_doi & {doi(r) for r in rows if pid(r) and doi(r)}
unnamed = [r for r in has if not pid(r) and not doi(r)]
rec = {r['key']: r['pmid'].strip() for r in csv.DictReader((l for l in open(ROOT / 'writing/fig1_v8/ref/review_papers_recovered.tsv')
                                                            if not l.startswith('#')), delimiter='\t')}
assert all(r['key'] in rec for r in unnamed), sorted(r['key'] for r in unnamed if r['key'] not in rec)
found = {rec[r['key']] for r in unnamed}
n_papers = len(by_pmid | found) + len(by_doi)

# the disputed values: every one in CLEARED (checked against its paper), by paper
disp = [r for r in has if human_review.disputes_value(r)]
assert len(disp) == disputed, (len(disp), disputed)
d_papers = Counter(r.get('pmid') for r in disp)
assert all(p in human_review.CLEARED for p in d_papers), [p for p in d_papers if p not in human_review.CLEARED]
missing = [r for r in has if r['status'] == 'rejected' and not human_review.disputes_value(r) and r.get('category') == 'missing_value']
other = [r for r in has if r['status'] == 'rejected' and not human_review.disputes_value(r) and r.get('category') != 'missing_value']
last = max(h['at'] for r in rows for h in r['history'])

# the inputs, frozen in git (human_review/ is git-ignored, so the off-Mac bundle would not hold them)
names = sorted(p for p in (ROOT / 'human_review/raw').iterdir() if p.is_file())
names += sorted((ROOT / 'human_review/packs').glob('*.json')) + sorted((ROOT / 'human_review/packs/withdrawn').glob('*.json'))
names += [ROOT / 'human_review' / n for n in ('decisions.jsonl', 'could_not_check.tsv', 'pmid_remap.tsv', 'old_pack.jsonl.gz')]
names += sorted((ROOT / 'human_review').glob('unmatched_*.tsv'))
names += [ROOT / 'writing/fig1_v8/ref/review_papers_recovered.tsv']
inputs = []
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode='w:xz', preset=9) as tf:
    for p in names:
        b = p.read_bytes()
        rel = str(p.relative_to(ROOT))
        inputs.append({'file': rel, 'bytes': len(b), 'sha256': sha(b)})
        ti = tarfile.TarInfo(rel); ti.size = len(b); ti.mtime = int(p.stat().st_mtime)
        tf.addfile(ti, io.BytesIO(b))
(HERE / 'review_inputs.tar.xz').write_bytes(buf.getvalue())
head = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(['git', 'status', '--porcelain', '--', 'tools/human_review.py', 'tools/site_release.py'], cwd=ROOT,
                       capture_output=True, text=True).stdout.strip()
out = {
    'frozen_at': time.strftime('%Y-%m-%d %H:%M'), 'last_decision_in_freeze': last,
    'code': {'git_head': head, 'tools_uncommitted': bool(dirty)},
    'status_line': line.strip(),
    'numbers': {
        'records_checked': checked, 'records_checked_def': 'records people checked against their papers (one total: records of the earlier catalogue and of this one alike); a record that names no PMID or DOI is not counted',
        'records_no_paper': nop, 'records_no_paper_def': 'records people looked at that name no PMID or DOI (not in records_checked)',
        'papers': n_papers, 'papers_def': "distinct papers of the records_checked (PMID or CatLog's stand-in id, else DOI; the records whose paper the review file lost from writing/fig1_v8/ref/review_papers_recovered.tsv), as Fig. 1's builder counts them",
        'records_undisputed': undisputed, 'records_disputed': disputed,
        'records_disputed_def': 'records on which a reviewer disputed a kcat, Km or kcat/Km (the number or its unit)',
        'disputed_papers': len(d_papers),
        'disputed_as_printed': as_printed, 'disputed_as_printed_def': 'disputed values that a check against the paper (two independent agents, or the reviewer\'s own number) found as printed: every one is in tools/human_review.CLEARED',
        'records_value_missing': len(missing), 'records_value_missing_def': 'records a reviewer rejected because the paper prints a value the record lacked',
        'records_other_disagreement': len(other), 'other_by_kind': dict(Counter(human_review.OTHER_KINDS.get(r.get('category') or '', r.get('category')) for r in other).most_common()),
        'records_in_file': len(rows)},
    'disputed_by_paper': {p: {'records': n, 'cleared_as': human_review.CLEARED[p]} for p, n in sorted(d_papers.items(), key=lambda kv: -kv[1])},
    'inputs': inputs, 'review_inputs_sha256': sha((HERE / 'review_inputs.tar.xz').read_bytes()),
}
(HERE / 'numbers.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
stats = subprocess.run([sys.executable, 'catlog.py', 'review', 'stats'], cwd=ROOT, capture_output=True, text=True).stdout
(HERE / 'review_stats.txt').write_text(stats)
print(json.dumps(out['numbers'], indent=1)[:1500])
print('disputed papers:', out['disputed_by_paper'])
print('inputs:', len(inputs), 'files, tar.xz', (HERE / 'review_inputs.tar.xz').stat().st_size, 'bytes; last decision', last, '; head', head, '; tools dirty:', bool(dirty))
