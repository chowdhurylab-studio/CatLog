"""Every count of the catalogue that Fig. 1 draws, for one data checkpoint (a git commit).

Run: python3 -I -B writing/fig1_v8/ref/catalogue_counts.py <commit> [out.json]   (some 20 s and 2 GB; git reads only)
Writes catalogue_counts.json beside itself (or out.json).

Since the final pass (16 Nov 2026) Fig. 1's build reads the catalogue's freeze for the paper,
paper/evidence/catalog_freeze_20261116/catalogue_counts.json (git tag paper-catalog-freeze-20261116), and no longer the
file this script writes; it recounts every number of that file from the tag itself. The freeze's file was made by this
script with one change, which is now in it: whole rows. Until 16 Nov the script kept only the identity fields of each
row, so join_lines (the last step of catlog.measurements, 11 Nov), which joins the records of one printed line by each
value's quote, joined nothing, and the records came out too many (141,031 at the tag against the 140,147 that status and
the export count: FREEZE.md there, "Counting at the snapshot"). join_lines also reads the rows kept out of the catalogue
(rejected.jsonl, bounds.jsonl); they are now read as the commit holds them, not from the working tree, which later
batches extend. Run on the tag, the script gives the freeze's counts (catalogue_counts.json here is that run).

What is counted, as the commit holds the files:
- values, papers_with_values: the lines of catalog.jsonl and their distinct papers;
- records: len(catlog.measurements(rows)) on whole rows, as `status` and `export` count them; the grouping code must be
  the commit's (the script stops if the working tree's catlog.py differs from it: run it in a worktree of the commit);
- papers_read: the distinct papers with an 'add' line in log.tsv (read by an agent, verified by a second, added);
- not_detected, limits: the rows of bounds.jsonl by kind (not_detected; '<' and '>');
- test_papers, test_unread: the papers of sources/holdout_locked.txt, and those of them with no 'add' line.
"""
import collections, datetime, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, ROOT)
import catlog  # noqa: E402

CK = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'catalogue_counts.json')
env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')


def at(f):
    with subprocess.Popen(['git', '-C', ROOT, 'show', f'{CK}:{f}'], stdout=subprocess.PIPE, text=True, encoding='utf-8',
                          env=env) as p:
        for ln in p.stdout:
            if ln.strip():
                yield ln
    assert p.returncode == 0, (f, p.returncode)


git = lambda *a: subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True, check=True, env=env).stdout.strip()
if subprocess.run(['git', '-C', ROOT, 'diff', '--quiet', CK, '--', 'catlog.py'], env=env).returncode != 0:
    sys.exit(f"catlog.py differs from {CK}'s: the records would be grouped by other code; run this in a worktree of {CK}")
rows = [json.loads(ln) for ln in at('catalog.jsonl')]          # whole rows: join_lines reads each value's quote
tmp = tempfile.mkdtemp(prefix='catalogue_counts_')
try:
    for name in ('rejected.jsonl', 'bounds.jsonl'):            # the rows kept out of the catalogue, as the commit holds them
        with open(os.path.join(tmp, name), 'w', encoding='utf-8') as fh:
            fh.writelines(at(name))
    old = (catlog.REJECTED, catlog.BOUNDS)
    catlog.REJECTED, catlog.BOUNDS = pathlib.Path(tmp, 'rejected.jsonl'), pathlib.Path(tmp, 'bounds.jsonl')
    try:
        meas = catlog.measurements(rows)
    finally:
        catlog.REJECTED, catlog.BOUNDS = old
finally:
    shutil.rmtree(tmp, True)
assert sum(len(m) for m in meas) == len(rows) and all(len({r['metric'] for r in m}) == len(m) <= 3 for m in meas)
log = [ln.rstrip('\n').split('\t') for ln in at('log.tsv')]
CHANGE = ('add', 'drop', 'drop_bound', 'unitfix', 'cellfix', 'pmfix', 'limitfix', 'recover')
read = {q[1] for q in log if len(q) > 2 and q[2] == 'add'}
with_values = {r['pmid'] for r in rows}
assert with_values <= read, 'every paper with values has an add line'
bounds = collections.Counter(json.loads(ln)['censored'] for ln in at('bounds.jsonl'))
assert set(bounds) <= {'<', '>', 'not_detected'}, bounds
locked = {ln.strip() for ln in at('sources/holdout_locked.txt') if ln.strip() and not ln.startswith('#')}
out = dict(checkpoint=git('rev-parse', '--short', CK), committed=git('log', '-1', '--format=%ad', '--date=iso', CK),
           last_change=max(q[0] for q in log if len(q) > 2 and q[2] in CHANGE),
           values=len(rows), papers_with_values=len(with_values), papers_read=len(read), records=len(meas),
           records_by_size={str(k): sum(1 for m in meas if len(m) == k) for k in (1, 2, 3)},
           not_detected=bounds['not_detected'], limits=bounds['<'] + bounds['>'],
           test_papers=len(locked), test_unread=len(locked - read),
           grouping_code_commit=git('log', '-1', '--format=%h', CK, '--', 'catlog.py'),
           computed=datetime.date.today().isoformat())
json.dump(out, open(OUT, 'w'), indent=1)
print(json.dumps(out))
