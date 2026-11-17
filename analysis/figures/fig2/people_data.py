"""People's review for Fig. 2a, frozen for the paper on 16 November 2026.

The paper's numbers of people's review come from paper/evidence/human_review_freeze_20261116/numbers.json and nowhere
else (FREEZE.md there defines each one): human_review/ keeps taking results for the website and the catalogue, so its
live file moves on and the paper does not. The squares of Fig. 2a are the frozen review file itself (decisions.jsonl
inside that folder's review_inputs.tar.xz), counted with the functions behind CatLog's own sentence on people's review
(tools/human_review.py review_summary; tools/site_release.py _one_review and _review_basis): the records people checked
against a paper, those with a value disputed, and how many of the disputed values were found as printed when the paper
was checked again. Every count is asserted equal to numbers.json. Per reviewer the same rule is applied to that
reviewer's own latest verdict (a rejection for a value or its unit, or an approval that says a value is wrong); the
counts equal those of work/review_stats_20261111/stats.json, which are asserted.

Reviewers stand by number only (the owner, 13 November 2026). The number is the rank of the reviewer's first
recorded verdict, as writing/manuscript/results/ED_reviewers.py numbers them. No name is kept or written here.
Since 15 November 2026 the paper gives people's review as the total only (the owner): the counts per reviewer serve
version A's draft and the check against the statistics file, and the picked figure (version B) draws none of them.

Nothing is written. Nothing moves after the freeze: a later results file changes the website, not this figure.
"""
import collections
import json
import re
import sys
import tarfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (ROOT / 'tools', ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import human_review as hr  # noqa: E402
import site_release as sr  # noqa: E402

FREEZE = ROOT / 'paper/evidence/human_review_freeze_20261116'     # the paper's freeze of people's review
FILE = 'human_review/decisions.jsonl'                             # its path inside the freeze's review_inputs.tar.xz
STATS = 'work/review_stats_20261111/stats.json'
FROZEN = json.loads((FREEZE / 'numbers.json').read_text())
NUMBERS = FROZEN['numbers']


def same(what, a, b):
    if a != b:
        raise SystemExit(f"people's review: {what}: {a!r} != {b!r}")


with tarfile.open(FREEZE / 'review_inputs.tar.xz') as _tf:
    ROWS = [json.loads(line) for line in _tf.extractfile(FILE).read().decode('utf-8').splitlines() if line.strip()]
BASIS, WITHOUT_PAPER = sr._review_basis(sr._one_review(hr.review_summary(ROWS)))
RECORDS = BASIS['entries']                                   # records people checked against a paper
DISPUTED = BASIS.get('value_disputed', 0)                    # records with a value disputed
AS_PRINTED = BASIS.get('value_disputed_checked_as_printed', 0)   # of those, found as printed when the paper was checked


def has_paper(r):
    """The headline's own test of a record that could be checked against a paper (human_review.review_summary)."""
    return bool(r.get('checkable') or r.get('doi') or r.get('v2_pack'))


def names(r):
    return {w: v for w, v in (r.get('reviewers') or {}).items() if w}


CHECKED = [r for r in ROWS if has_paper(r)]
same('records with a paper', len(CHECKED), RECORDS)
same('records in the file', len(ROWS), RECORDS + (WITHOUT_PAPER or 0))
DISPUTED_ROWS = [r for r in CHECKED if hr.disputes_value(r)]
same('records with a value disputed', len(DISPUTED_ROWS), DISPUTED)
same('no value is disputed on a record without a paper', sum(1 for r in ROWS if hr.disputes_value(r)), DISPUTED)
PAPERS_DISPUTED = len({r.get('pmid') for r in DISPUTED_ROWS})
PAPERS = NUMBERS['papers']                                        # distinct papers of the records (Fig. 1's rule)
for what, mine, key in (('records checked against a paper', RECORDS, 'records_checked'),
                        ('records without a PMID or DOI', WITHOUT_PAPER or 0, 'records_no_paper'),
                        ('records with a value disputed', DISPUTED, 'records_disputed'),
                        ('records with no value disputed', RECORDS - DISPUTED, 'records_undisputed'),
                        ('disputed values found as printed', AS_PRINTED, 'disputed_as_printed'),
                        ('papers of the disputed records', PAPERS_DISPUTED, 'disputed_papers'),
                        ('records in the frozen file', len(ROWS), 'records_in_file')):
    same(f'{what}, against the freeze (numbers.json {key})', mine, NUMBERS[key])
same('each disputed value was checked against its paper', sum(1 for r in DISPUTED_ROWS if r.get('pmid') in hr.CLEARED), AS_PRINTED)

# Reviewers by number: the rank of the first recorded verdict
_first = {}
for r in ROWS:
    for x in r.get('history', []):
        w = x.get('by')
        if w and (w not in _first or x['at'] < _first[w]):
            _first[w] = x['at']
same('no two reviewers share a first time', len(set(_first.values())), len(_first))
_number = {w: i for i, w in enumerate(sorted(_first, key=_first.get), 1)}


def _disputes(verdict, comment):
    """A reviewer's own verdict disputes a value: the record-level rule (human_review.disputes_value) applied to that
    reviewer's latest line, so the per-reviewer counts and the record count are of one definition."""
    kind = hr.classify(comment)
    return kind in ('value', 'unit') and (verdict == 'rejected' or bool(re.search(r'\bwrong\b', (comment or '').lower())))


_per = collections.defaultdict(collections.Counter)
_by_reviewer = set()
for r in CHECKED:
    who = names(r)
    same(f"record {r['key']}: a named reviewer", bool(who), True)
    for w, verdict in who.items():
        _per[_number[w]]['records'] += 1
        own = [x for x in r.get('history', []) if x['by'] == w and x['status'] == verdict]
        same(f"record {r['key']}: the reviewer's own line", bool(own), True)
        if _disputes(verdict, own[-1].get('comment')):
            _per[_number[w]]['disputed'] += 1
            _by_reviewer.add(r['key'])
same('the records a reviewer disputes are the records with a value disputed', _by_reviewer, {r['key'] for r in DISPUTED_ROWS})
REVIEWERS = [(n, _per[n]['records'], _per[n]['disputed']) for n in sorted(_per)]   # (number, records, with a value disputed)
same('reviewers', [n for n, _, _ in REVIEWERS], list(range(1, len(_number) + 1)))
same('disputed, summed over reviewers', sum(d for _, _, d in REVIEWERS), DISPUTED)
TWO_REVIEWERS = sum(1 for r in CHECKED if len(names(r)) > 1)
same('decisions = records + records with two reviewers', sum(n for _, n, _ in REVIEWERS), RECORDS + TWO_REVIEWERS)
_stats = json.loads((ROOT / STATS).read_text())['reviewers']
same('the statistics file holds the same reviewers', set(_stats), set(_number))
for w, n in _number.items():       # the statistics file (11 November) predates the freeze's last 267 records, all approvals,
    same(f'Reviewer {n}: value disputed, statistics file', _stats[w].get('value_disputed', 0), _per[n]['disputed'])
    # so only its disputed counts still hold; its record counts are not compared

# The records in the order they were decided, for a picture of every record: True where a value is disputed
ORDER = [hr.disputes_value(r) for r in sorted(CHECKED, key=lambda r: (r.get('decided_at') or '', r['key']))]
same('the ordered records', (len(ORDER), sum(ORDER)), (RECORDS, DISPUTED))
LAST_DECISION = max(x['at'] for r in ROWS for x in r.get('history', []) if x.get('at'))
same('the last decision in the freeze', LAST_DECISION, FROZEN['last_decision_in_freeze'])

if __name__ == '__main__':
    print(f'{RECORDS:,} records checked against a paper ({WITHOUT_PAPER} more without one); a value disputed on {DISPUTED} '
          f'in {PAPERS_DISPUTED} papers; found as printed {AS_PRINTED}; two reviewers on {TWO_REVIEWERS}; last decision {LAST_DECISION}')
    for n, records, disputed in REVIEWERS:
        print(f'Reviewer {n}: {records:,} records, a value disputed on {disputed} ({100 * (1 - disputed / records):.2f}% not disputed)')
