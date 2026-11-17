#!/usr/bin/env python3
"""One numbers ledger for draft_v1.md (abstract, Introduction, Results, Box 1, Discussion, main Methods).

Run from anywhere: python3 paper/manuscript/numbers_build.py
Writes only paper/manuscript/numbers.json and paper/manuscript/numbers_ledger.md.

Every number the draft uses gets a stable key, its definition (what is counted, the base, the date window), its source
and the code line that computes it. Kinds:
  snapshot   computed here from the repository files as they stand at this run (the snapshot);
  window     computed here from the same snapshot files, restricted to a dated window (a development period);
  frozen     a one-time result that cannot be recomputed from the files (agent checks, transcript scans of logs that
             are now on Nova, the 22 October layer pilot, the benchmark): read from the evidence file named, with the
             string or JSON path asserted;
  literature a figure from another paper, read from the checked source note named;
  code       a constant read from the code or prompt file at the snapshot's HEAD;
  plan       a planned number (W-task), read from the planning file named;
  fact       a number printed in a case paper, read from the checked case evidence.
A frozen or window number that the snapshot also yields under the same definition carries that value as `check`.

The snapshot: every repository file is read once, hashed while it is read and parsed from the same bytes, and the four
core files (catalog.jsonl, rejected.jsonl, log.tsv, sources/database_corrections.tsv) are hashed again at the end; the
build stops if one changed meanwhile. Nothing in the repository is written except the two outputs. The re-derivation
scripts of paper/evidence/rederive_20261101/ are imported (their save() is replaced, so results.json there is not
touched) and run on the working tree, which the before/after hashes show to be the snapshot.
"""
import ast
import collections
import csv
import glob
import hashlib
import importlib
import inspect
import io
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime

sys.dont_write_bytecode = True
csv.field_size_limit(10 ** 9)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PAPER = os.path.join(ROOT, 'paper')
OUT_JSON = os.path.join(HERE, 'numbers.json')
OUT_MD = os.path.join(HERE, 'numbers_ledger.md')
DRAFT = os.path.join(HERE, 'draft_v1.md')
CORE = ['catalog.jsonl', 'rejected.jsonl', 'log.tsv', 'sources/database_corrections.tsv']
ERRORS = []                      # problems found while building; printed and written, never fatal unless the snapshot moves


def P(*a):
    return os.path.join(ROOT, *a)


def git(*a):
    return subprocess.run(['git', '-C', ROOT] + list(a), capture_output=True, text=True, check=True).stdout


def sha_file(rel):
    h = hashlib.sha256()
    with open(P(rel), 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ===================================================================================================== the snapshot
class Snapshot:
    """Each file is read once, hashed as it is read; its parsed form is cached."""

    def __init__(self):
        self.started = datetime.now().astimezone()
        self.head = git('rev-parse', 'HEAD').strip()
        self.head_line = git('show', '-s', '--format=%h %ad %s', '--date=format:%Y-%m-%d %H:%M %z', 'HEAD').strip()
        self.files = {}
        self.cache = {}

    def _record(self, rel, h, n):
        st = os.stat(P(rel))
        dirty = subprocess.run(['git', '-C', ROOT, 'diff', '--quiet', 'HEAD', '--', rel]).returncode != 0
        tracked = subprocess.run(['git', '-C', ROOT, 'ls-files', '--error-unmatch', rel],
                                 capture_output=True).returncode == 0
        last = git('log', '-1', '--format=%h %ad', '--date=format:%Y-%m-%d %H:%M', '--', rel).strip() if tracked else ''
        self.files[rel] = {'sha256': h, 'bytes': n,
                           'mtime': datetime.fromtimestamp(st.st_mtime).astimezone().strftime('%Y-%m-%d %H:%M:%S %z'),
                           'git': ('untracked or ignored' if not tracked else
                                   'differs from HEAD' if dirty else 'as at HEAD'),
                           'last_commit': last}

    def lines(self, rel):
        """All lines of a text file (decoded), hashed while read."""
        if ('lines', rel) in self.cache:
            return self.cache[('lines', rel)]
        h, n, out = hashlib.sha256(), 0, []
        with open(P(rel), 'rb') as f:
            for b in f:
                h.update(b)
                n += len(b)
                out.append(b.decode('utf-8'))
        self._record(rel, h.hexdigest(), n)
        self.cache[('lines', rel)] = out
        return out

    def jsonl(self, rel):
        if ('jsonl', rel) not in self.cache:
            rows = []
            for ln in self.lines(rel):
                if ln.strip():
                    try:
                        rows.append(json.loads(ln))
                    except ValueError:
                        ERRORS.append(f'{rel}: a line that is not JSON was skipped')
            self.cache[('jsonl', rel)] = rows
            del self.cache[('lines', rel)]          # keep memory down: the parsed rows are what is used
        return self.cache[('jsonl', rel)]

    def tsv(self, rel, quoting=csv.QUOTE_NONE):
        if ('tsv', rel) not in self.cache:
            self.cache[('tsv', rel)] = list(csv.DictReader(io.StringIO(''.join(self.lines(rel))), delimiter='\t',
                                                           quoting=quoting))
        return self.cache[('tsv', rel)]

    def text(self, rel):
        return ''.join(self.lines(rel))

    def stream_jsonl(self, rel):
        """A large file streamed (not kept): yields rows, records the hash at the end."""
        h, n = hashlib.sha256(), 0
        with open(P(rel), 'rb') as f:
            for b in f:
                h.update(b)
                n += len(b)
                if b.strip():
                    yield json.loads(b)
        self._record(rel, h.hexdigest(), n)

    def evidence(self, rel):
        """An evidence or code file read whole (hashed)."""
        return self.text(rel)


# ===================================================================================================== the ledger
class Ledger:
    def __init__(self):
        self.rows = collections.OrderedDict()

    def add(self, key, value, what, *, kind, source, base=None, window='snapshot', state='ON FILE', show=None,
            forms=(), check=None, note=None):
        """key: stable name. value: the canonical number (int, float, str or [lo, hi]). show: as the text prints it.
        forms: phrases of draft_v1.md this key covers (exact text, line breaks as spaces; a bare number matches as a
        whole token)."""
        st = inspect.stack()
        fr = next((f for f in st[1:] if f.function not in ('E', 'EJ', 'c')), st[1])
        if key in self.rows:
            ERRORS.append(f'duplicate key {key}')
        self.rows[key] = {'key': key, 'value': value, 'show': show if show is not None else fmt(value),
                          'what': what, 'base': base, 'window': window, 'kind': kind, 'state': state,
                          'source': source, 'code': f'numbers_build.py:{fr.lineno} ({fr.function})',
                          'forms': list(forms), 'check': check, 'note': note}
        return value

    def get(self, key):
        return self.rows[key]['value']


def fmt(v, nd=None):
    if v is None:
        return 'n/a'
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return f'{v:,}'
    if isinstance(v, float):
        if nd is not None:
            return f'{v:,.{nd}f}'
        if v == int(v) and abs(v) >= 100:
            return f'{int(v):,}'
        return f'{round(v, 4):,}'
    if isinstance(v, (list, tuple)):
        return '-'.join(fmt(x, nd) for x in v)
    return str(v)


def pct(k, n, nd=1):
    return round(100 * k / n, nd) if n else None


def pshow(k, n, nd=1):
    return f'{100 * k / n:.{nd}f}%'


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(100 * (c - r) / d, 2), round(100 * (c + r) / d, 2)]


def jpath(d, path):
    for k in path:
        d = d[k]
    return d


def must(text, s, where):
    """Assert that a string an evidence key relies on is in its file (whitespace runs count as one space)."""
    if s not in text and re.sub(r'\s+', ' ', s) not in re.sub(r'\s+', ' ', text):
        ERRORS.append(f'{where}: expected text not found: {s[:80]!r}')
        return False
    return True


def rx(text, pattern, where, group=1, flags=0):
    m = re.search(pattern, text, flags)
    if not m:
        ERRORS.append(f'{where}: pattern not found: {pattern[:80]!r}')
        return None
    return m.group(group)


def num(s):
    """'1,234' -> 1234; '0.5' -> 0.5."""
    if s is None:
        return None
    s = s.replace(',', '').replace('−', '-')
    return float(s) if '.' in s else int(s)


S = Snapshot()
L = Ledger()


# ===================================================================================================== 1. status
def sec_status():
    """`python3 catlog.py status` (the project's only progress counter), run now, parsed. Its counts are checked
    against this build's own counts of the same files below."""
    t0 = time.time()
    out = subprocess.run([sys.executable, 'catlog.py', 'status'], cwd=ROOT, capture_output=True, text=True).stdout
    S.status_text, S.status_seconds = out, round(time.time() - t0, 1)
    src = 'python3 catlog.py status (run by this build)'
    w = 'catlog.py status at ' + (rx(out, r'progress \((\d{4}-\d\d-\d\d \d\d:\d\d)\)', 'status') or '?')
    m = re.search(r'\*\*([\d,]+) values\*\* · \*\*([\d,]+) records\*\* · \*\*([\d,]+) papers with values\*\*', out)
    S.st = {'values': num(m.group(1)), 'records': num(m.group(2)), 'papers': num(m.group(3))}
    m = re.search(r'catalog and log agree \(([\d,]+) values, ([\d,]+) censored, ([\d,]+) rejected\)', out)
    if not m:
        ERRORS.append('status: "catalog and log agree" not found: the snapshot is not consistent')
    else:
        S.st.update(agree=True, censored=num(m.group(2)), rejected=num(m.group(3)))
    S.st['queue'] = num(rx(out, r'\*\*Papers\*\* \(([\d,]+) in the queue\)', 'status'))
    S.st['done'] = num(rx(out, r'Done ([\d,]+) ·', 'status'))
    S.st['browser'] = num(rx(out, r'Need a download: browser (\d+)', 'status'))
    S.st['ill'] = num(rx(out, r'interlibrary loan ([\d,]+) \(optional\)', 'status'))
    m = re.search(r'\*\*Audits:\*\* ([\d,]+) values re-checked .*?: ([\d,]+) wrong and dropped \(([\d.]+)%\), (\d+) units '
                  r'corrected; targeted re-checks .*?: ([\d,]+), ([\d,]+) dropped', out)
    S.st['audits'] = [num(m.group(i)) for i in (1, 2, 4, 5, 6)]
    # values dropped for their organism label alone and back under the right one (catlog.relabelled_drops, the user
    # 2026-11-15): status counts them apart from the wrong ones, after the targeted clause
    m = re.search(r'\*\*Audits:\*\*.*?; (\d+) organism labels? corrected', out)
    S.st['audit_labels'] = num(m.group(1)) if m else 0
    # people's review as one total (the user, 2026-10-30: one CatLog, never an earlier and a new catalogue): status
    # prints one line since then (tools/site_release._quality_lines), so the two lines this build read before (records
    # of the earlier catalogue, CatLog v2's random sample) no longer exist
    m = re.search(r'\*\*Human review:\*\* people checked ([\d,]+) records against their papers'
                  r'(?: \(([\d,]+) more had no PMID or DOI\))?; no value disputed on ([\d,]+) \([^)]*\)'
                  r'(?:; (?:the ([\d,]+) disputed values? (?:are|is) as printed'
                  r'|([\d,]+) of the [\d,]+ disputed values are as printed))?', out)
    if not m:
        ERRORS.append('status: the "Human review" line was not found; the review keys are left empty')
        S.st['review'] = [None] * 5
    else:
        checked, undisputed = num(m.group(1)), num(m.group(3))
        S.st['review'] = [checked, num(m.group(2) or '0'), undisputed, checked - undisputed,
                          num(m.group(4) or m.group(5) or '0')]
    S.status_when = w
    L.add('status.values', S.st['values'], 'stored values (kcat, Km or printed kcat/Km rows of catalog.jsonl), as '
          'catlog.py status counts them', kind='snapshot', source=src, window=w, show=fmt(S.st['values']))
    L.add('queue.papers', S.st['queue'], 'papers in the queue (papers.tsv rows)', kind='snapshot', source=src,
          window=w, forms=['[77,056] papers', 'of [77,056] queued', 'the queue held 77,056 papers'],
          check=None)
    L.add('queue.done', S.st['done'], 'papers finished (papers.tsv status done)', kind='snapshot', source=src,
          window=w, forms=['[7,236] of', '7,179 of them done'],
          note='Methods prints 7,179 (status of 31 October 14:26, [n8]); the Discussion prints the snapshot count')
    L.add('queue.browser', S.st['browser'], 'papers waiting for a browser download (needs_browser outside the '
          'interlibrary-loan lanes)', kind='snapshot', source=src, window=w, forms=['[7,952]'])
    L.add('queue.ill', S.st['ill'], 'papers in the interlibrary-loan lanes (optional)', kind='snapshot', source=src,
          window=w)
    a = S.st['audits']
    L.add('audit.random.values', a[0], 'values a random audit re-checked against its paper (each row once, by its '
          'latest verdict; rows only targeted audits saw are left out: catlog.audit_summary)', kind='snapshot',
          source=src + '; recomputed from log.tsv by audits() below', window=w, forms=['re-checked 7,726 values'])
    L.add('audit.random.dropped', a[1], 'of those, values dropped as wrong', kind='snapshot', base='audit.random.values',
          source=src, window=w, forms=['dropped 30 and'])
    L.add('audit.random.units_corrected', a[2], 'of those, values whose unit an audit corrected', kind='snapshot',
          base='audit.random.values', source=src, window=w, forms=['corrected the unit of 6'])
    L.add('audit.targeted.values', a[3], 'values only targeted audits saw (database-check targets, whole-paper '
          'follow-ups)', kind='snapshot', source=src, window=w)
    L.add('audit.targeted.dropped', a[4], 'of those, dropped', kind='snapshot', source=src, window=w)
    L.add('audit.random.labels_corrected', S.st['audit_labels'], 'values a random audit dropped for their organism '
          'label alone that came back under the corrected label (catlog.relabelled_drops): label corrections, not '
          'wrong values, so not in audit.random.dropped', kind='snapshot', base='audit.random.values', source=src,
          window=w, note='the user, 2026-11-15 (18620421)')
    # people's review is frozen for the paper (16 November 2026; the owner: "wrap for paper data report freeze"):
    # the review keys read the freeze's numbers.json (paper/evidence/human_review_freeze_20261116/FREEZE.md defines
    # each), never the status line, which keeps growing for the website; the status line's count rides along as check
    rv = S.st['review']
    frz = json.loads(S.evidence('paper/evidence/human_review_freeze_20261116/numbers.json'))
    fn = frz['numbers']
    fsrc = 'paper/evidence/human_review_freeze_20261116/numbers.json#numbers.'
    fw = f"frozen 16 Nov 2026 (last decision {frz['last_decision_in_freeze']})"
    L.add('review.records', fn['records_checked'], 'records people checked against their papers (one total: earlier '
          'and current records alike)', kind='frozen', source=fsrc + 'records_checked', window=fw, check=rv[0])
    L.add('review.records_no_paper', fn['records_no_paper'], 'records people looked at that have no PMID or DOI (not in '
          'review.records)', kind='frozen', source=fsrc + 'records_no_paper', window=fw, check=rv[1])
    L.add('review.records_undisputed', fn['records_undisputed'], 'of review.records, those on which no value was '
          'disputed', kind='frozen', base='review.records', source=fsrc + 'records_undisputed', window=fw, check=rv[2])
    L.add('review.disputed', fn['records_disputed'], 'of review.records, those with a disputed value', kind='frozen',
          base='review.records', source=fsrc + 'records_disputed', window=fw, check=rv[3])
    L.add('review.disputed_as_printed', fn['disputed_as_printed'], 'disputed values that the paper prints as the record '
          'had them', kind='frozen', base='review.disputed', source=fsrc + 'disputed_as_printed', window=fw,
          check=rv[4])
    if fn['records_checked'] - fn['records_disputed'] != fn['records_undisputed']:
        ERRORS.append('review freeze: records_checked - records_disputed != records_undisputed')


# ===================================================================================================== 2. catalog
def sec_catalog():
    rows = S.jsonl('catalog.jsonl')
    S.cat = rows
    S.cat_ids = {r['row_id'] for r in rows}
    n, papers = len(rows), {str(r['pmid']) for r in rows}
    S.n_values = n
    src = 'catalog.jsonl'
    L.add('cat.values', n, 'stored values: rows of catalog.jsonl (each one kcat, Km or printed kcat/Km)',
          kind='snapshot', source=src,
          forms=['240,169 kcat, Km and kcat/Km values', 'held [240,169] values', 'Of the [240,169] values',
                 'CatLog holds [240,169] values', 'held 239,498 values', 'of the 239,498 values stored'],
          check=S.st['values'], note='Methods prints 239,498 (status of 31 October 14:26, [n1]); 240,169 elsewhere')
    if n != S.st['values']:
        ERRORS.append(f'catalog rows {n} != status values {S.st["values"]}')
    L.add('abstract.values_rounded', int(round(n, -4)), 'cat.values rounded to the nearest 10,000, for the abstract',
          kind='snapshot', source=src, base='cat.values', forms=['[240,000] values'])
    L.add('cat.papers_with_values', len(papers), 'papers with at least one stored value', kind='snapshot', source=src,
          forms=['from 7,259 papers', 'from [7,259] papers', 'from 7,202 papers'],
          check=S.st['papers'], note='Methods prints 7,202 (14:26, [n1])')
    qc = [r for r in rows if r.get('quote_check')]
    L.add('cat.page_image_flagged', len(qc), 'stored values kept with a flag (quote_check) because their quote or '
          'value match failed and the verifier confirmed the cell on the page image', kind='snapshot', source=src,
          forms=['([8,474] values)'], check=None,
          note=f'{len({r["pmid"] for r in qc})} papers')
    rec = [r for r in rows if str(r.get('verify_note', '')).startswith('recovered (verifier_reject')]
    L.add('cat.recovered_without_verdict', len(rec), 'stored values with no confirm or fix verdict: rejected by a '
          'verifier, restored by `recover` after a later check of their paper (verify_note "recovered (verifier_reject")',
          kind='snapshot', source=src + '; log.tsv recover line 2026-10-31 13:19 (kept=20)',
          forms=['Twenty stored values have no such verdict=>20', 'and 20, recovered that day', 'restored 20 of them'],
          note='papers: ' + ', '.join(sorted({str(r['pmid']) for r in rec})))
    # conversion units: who set them
    unitfix = {f[3] for f in S.log if len(f) > 3 and f[2] == 'unitfix'}
    S.unitfix_ids = unitfix
    bf = S.backfill
    uc = [r for r in rows if r.get('unit_for_conversion')]
    who = collections.Counter()
    who_own = collections.Counter()
    for r in uc:
        rb_full = r.get('read_by') or (bf.get(r['row_id']) or {}).get('read_by')
        if 'unit_for_conversion' in (r.get('corrected') or {}):
            k = 'verifier fix'
        elif r['row_id'] in unitfix:
            k = 'logged unitfix'
        elif rb_full == 'verifier (missed values)':
            k = 'verifier as reader of missed values'
        else:
            k = 'reader'
        who[k] += 1
        if k in ('verifier fix', 'logged unitfix'):
            who_own[k] += 1
        elif r.get('read_by') == 'verifier (missed values)':
            who_own['verifier as reader of missed values'] += 1
        else:
            who_own['reader'] += 1
    L.add('conv.values_with_conversion_unit', len(uc), 'stored values whose row carries a conversion unit '
          '(unit_for_conversion) beside the printed unit', kind='snapshot', source=src,
          forms=['Of the 8,481 stored values with a conversion unit'],
          note='Methods prints 8,481 (catalog of 31 October 14:24, [n25a])')
    L.add('conv.set_by_reader', who['reader'], 'of those, conversion units the reader wrote: not set by a verifier fix '
          '(`corrected`), a logged `unitfix` or a verifier reading missed values (read_by from the row\'s own stamp, '
          'else its reconstructed stamp in sources/provenance_backfill.tsv)', kind='snapshot',
          base='conv.values_with_conversion_unit', source=src + '; log.tsv unitfix; sources/provenance_backfill.tsv',
          forms=['readers wrote 4,347'],
          check=who_own['reader'],
          note=f'split: {dict(who)}. check = the narrower [n25a] rule (read_by of the row\'s own stamp only): '
               f'{dict(who_own)}. Methods prints 4,347 by the narrower rule at 14:24')
    # stamps
    own = recon = 0
    none = []
    miss = collections.Counter()
    any_miss = 0
    first_own = None
    for r in rows:
        if 'read_prompt' in r:
            own += 1
            s = r
            t = r.get('added') or r['checked']  # a row unitfix brought back from a limit reject has no `added` (7, 5 Nov)
            first_own = min(first_own or t, t)
        elif r['row_id'] in bf:
            recon += 1
            s = bf[r['row_id']]
        else:
            none.append(r)
            continue
        m4 = [k for k in ('pipeline_commit', 'read_prompt', 'reader_model', 'verify_prompt') if not (s.get(k) or '').strip()]
        miss.update(m4)
        any_miss += bool(m4)
    srcs = 'catalog.jsonl (own stamp: the row has read_prompt) and sources/provenance_backfill.tsv (reconstructed)'
    L.add('stamp.own', own, 'stored values stamped when stored (the row carries read_prompt and the other stamp fields; '
          'stamping began with commit 76a824c, 2026-10-21 21:57)', kind='snapshot', base='cat.values', source=srcs,
          forms=['[18,520] carried their own stamp', '18,163 (7.6%) carried their own stamp'],
          note=f'first own stamp {first_own}. Methods prints 18,163 of 239,812 rows (catalogue at 14:30, [n56])')
    L.add('stamp.own_share', pct(own, n), 'stamp.own as a share of stored values', kind='snapshot', base='cat.values',
          source=srcs, show=pshow(own, n), forms=['(7.6%)'])
    L.add('stamp.reconstructed', recon, 'stored values whose stamp was rebuilt from the agents\' logs (a line in '
          'sources/provenance_backfill.tsv, how = reconstructed)', kind='snapshot', base='cat.values', source=srcs,
          forms=['[221,629] a reconstructed one', '221,629 (92.4%) a reconstructed one'])
    L.add('stamp.reconstructed_share', pct(recon, n), 'stamp.reconstructed as a share of stored values',
          kind='snapshot', base='cat.values', source=srcs, show=pshow(recon, n), forms=['221,629 ({92.4}%)'])
    L.add('stamp.none', len(none), 'stored values with neither stamp', kind='snapshot', base='cat.values', source=srcs,
          forms=['and 20, recovered that day, none yet', 'and 20 none'],
          note='papers ' + ', '.join(sorted({str(r['pmid']) for r in none})))
    L.add('stamp.rows_base', n, 'the base of the stamp counts: stored values (= cat.values)', kind='snapshot',
          source=src, forms=['Of the 239,812 rows on 31 October 2026'],
          note='Methods counts 239,812 rows at 14:30 ([n56]); the Results 240,169 (22:09)')
    L.add('stamp.missing_field', any_miss, 'stamps (own or reconstructed) with at least one blank field among code '
          'commit, read prompt, reader model and verify prompt', kind='snapshot', source=srcs,
          forms=['A field was missing from [5,396] stamps'],
          note='by field: ' + ', '.join(f'{k} {v:,}' for k, v in miss.most_common()))
    vf = [r for r in rows if (r.get('read_by') if 'read_prompt' in r else (bf.get(r['row_id']) or {}).get('read_by'))
          == 'verifier (missed values)']
    L.add('cat.verifier_found_stored', len(vf), 'stored values whose stamp (own, else reconstructed) says a verifier '
          'found them after the reader skipped them (read_by "verifier (missed values)")', kind='snapshot', source=srcs,
          note=f'{len({str(r["pmid"]) for r in vf})} papers. The Results print 1,138 in 94 papers (dev.logs.missed_found: '
               'missed-value files still in work/ on 28 October, a lower bound: a re-read moves the file to work/old/)')
    L.add('stamp.backfill_lines', len(S.backfill_lines), 'lines of sources/provenance_backfill.tsv (rows ever '
          'reconstructed, some no longer stored)', kind='snapshot', source='sources/provenance_backfill.tsv',
          note='outline L6 prints this as rows (221,739); it is not a count of stored values')
    # shares before rules ([n50a]): added (else checked) before each rule commit
    for key, commit, label, forms in (
            ('rule.share_before_blind_rule', 'bc442f7', 'the blind-reading rule',
             ['42.1% had been added before the blind-reading rule', '42.1% of values predate the blind-reading rule']),
            ('rule.share_before_stamps', '76a824c', 'the provenance stamps', ['92.4% before the provenance stamps'])):
        t = git('show', '-s', '--format=%ad', '--date=format:%Y-%m-%d %H:%M', commit).strip()
        k = sum(1 for r in rows if (r.get('added') or r.get('checked') or '') < t)
        L.add(key, pct(k, n), f'share of stored values added (else checked) before {label} (git {commit}, {t})',
              kind='snapshot', base='cat.values', source=src + f'; git {commit}', show=pshow(k, n), forms=forms,
              note=f'{k:,} of {n:,}. Methods and Discussion print the share of 239,498 values at 14:24 ([n50a])')
    # sweeps: values stored after each one-off sweep ran
    sweep_t = datetime.fromtimestamp(os.stat(P('work', 'scale_sweep.tsv')).st_mtime).strftime('%Y-%m-%d %H:%M')
    k = sum(1 for r in rows if (r.get('added') or r.get('checked') or '') > sweep_t)
    L.add('sweep.scale.share_stored_after', pct(k, n), 'share of stored values added after the unit-factor sweep last '
          f'wrote work/scale_sweep.tsv ({sweep_t}); the sweep has not run since', kind='snapshot', base='cat.values',
          source=src + '; mtime of work/scale_sweep.tsv', show=pshow(k, n), forms=['16.7%'],
          note=f'{k:,} of {n:,} values')
    # the worked example (Fig. 1b, PMID 21757926)
    ex = [r for r in rows if str(r['pmid']) == '21757926']
    kcm = [r for r in ex if r['metric'] == 'kcat/Km' and r['raw_value'].startswith('6 ± 1.5')]
    rec_rows = {}
    if len(kcm) == 1:
        e = kcm[0]
        mates = [r for r in ex if r['location'] == e['location'] and r['substrate'] == e['substrate']]
        rec_rows = {r['metric']: r for r in mates}
        others = sorted(float(r['value']) for r in ex if r['metric'] == 'kcat/Km' and r['row_id'] != e['row_id']
                        and r['location'].startswith('Table 1'))
        S.example = {'kcm': e, 'kcat': rec_rows.get('kcat'), 'Km': rec_rows.get('Km'), 'others': others}
    else:
        ERRORS.append('worked example: the stored 6 ± 1.5 kcat/Km of 21757926 not found once')
        S.example = None


def sec_backfill():
    rows = S.tsv('sources/provenance_backfill.tsv')
    S.backfill_lines = rows
    S.backfill = {r['row_id']: r for r in rows}


def sec_log():
    S.log = [ln.rstrip('\n').split('\t') for ln in S.lines('log.tsv')]
    S.log = [f for f in S.log if len(f) >= 3]


def sec_audits():
    """catlog.audit_summary re-implemented on the snapshot's log.tsv (FOLLOWUP_AUDITS read from catlog.py)."""
    src = S.evidence('catlog.py')
    m = re.search(r'^FOLLOWUP_AUDITS = (\(.*?^\))', src, re.S | re.M)
    fu = ast.literal_eval(m.group(1)) if m else ()
    tgt = ('targeted=dbcheck', 'targeted=paper')

    def targeted(f):
        return f[-1] in tgt or any(f[1] == p and a <= f[0][:16] <= b for p, a, b in fu)
    last, sampled = {}, set()
    for f in S.log:
        if f[2] in ('audit_keep', 'audit_drop') and len(f) > 3:
            last[f[3]] = (f[2], ' '.join(f[4:]))
            if not targeted(f):
                sampled.add(f[3])
    r = {k: v for k, v in last.items() if k in sampled}
    # catlog.relabelled_drops on the snapshot: a drop whose value came back under a corrected organism label (log
    # `relabelled <dropped> <new>`, the latest return of each), following a second correction to a row still in the
    # catalogue, is a label correction, not a wrong value (the user, 2026-11-15)
    hexid = re.compile(r'[0-9a-f]{16}')
    back = {f[3]: f[4] for f in S.log if f[2] == 'relabelled' and len(f) >= 7
            and hexid.fullmatch(f[3]) and hexid.fullmatch(f[4])}
    present = {x['row_id'] for x in S.cat}
    labels = set()
    for d, n in back.items():
        seen = {d}
        while n not in present and n in back and n not in seen:
            seen.add(n)
            n = back[n]
        if n in present:
            labels.add(d)
    relab = sum(e == 'audit_drop' and k in labels for k, (e, _) in r.items())
    mine = (len(r), sum(e == 'audit_drop' for e, _ in r.values()) - relab,
            sum(e == 'audit_keep' and w.startswith('unit corrected') for e, w in r.values()))
    if list(mine) != S.st['audits'][:3]:
        ERRORS.append(f'audits recomputed {mine} != status {S.st["audits"][:3]}')
    if relab != S.st['audit_labels']:
        ERRORS.append(f'organism-label corrections recomputed {relab} != status {S.st["audit_labels"]}')
    L.rows['audit.random.labels_corrected']['check'] = relab
    L.rows['audit.random.values']['check'] = mine[0]
    L.rows['audit.random.dropped']['check'] = mine[1]
    L.rows['audit.random.units_corrected']['check'] = mine[2]
    L.add('audit.random.wrong', mine[1] + mine[2], 'values a random audit found wrong: dropped, or kept with its unit '
          'corrected (the layer pilot\'s definition of wrong, check/d_audits.py)', kind='snapshot',
          base='audit.random.values', source='log.tsv (catlog.audit_summary, re-implemented)')
    L.add('audit.random.wrong_per_1000', round(1000 * (mine[1] + mine[2]) / mine[0], 1), 'audit.random.wrong per 1,000 '
          'audited values', kind='snapshot', base='audit.random.values', source='log.tsv')
    L.add('audit.random.dropped_share', pct(mine[1], mine[0]), 'audit.random.dropped as a share of '
          'audit.random.values (the status line\'s rate)', kind='snapshot', base='audit.random.values',
          source='log.tsv', show=pshow(mine[1], mine[0]))


def sec_bounds():
    b = S.jsonl('bounds.jsonl')
    L.add('cat.censored_values', len(b), 'censored values kept apart (bounds.jsonl rows): printed only as a bound '
          '(<, >) or as not detected', kind='snapshot', source='bounds.jsonl',
          forms=['kept apart [19,049] values', 'Another 19,049 values', '269 of {19,049}'], check=S.st.get('censored'))
    rej = S.jsonl('rejected.jsonl')
    S.rej = rej
    L.add('cat.rejected_rows', len(rej), 'rows refused or dropped (rejected.jsonl lines)', kind='snapshot',
          source='rejected.jsonl', check=S.st.get('rejected'),
          note='Supplementary Note [n24] prints 7,924 (14:26)')
    exp_b = list(S.stream_jsonl('catlog_bounds.jsonl'))
    joined = sum(1 for r in exp_b if r.get('measurement_id'))
    L.add('cat.censored_joined', joined, 'censored values that join one record as a text bound (non-empty '
          'measurement_id in catlog_bounds.jsonl)', kind='snapshot', base='cat.censored_values',
          source='catlog_bounds.jsonl (export)', forms=['(269 of 19,049 did)'],
          note=f'{len(exp_b):,} censored values in the export')
    if len(exp_b) != len(b):
        ERRORS.append(f'catlog_bounds.jsonl has {len(exp_b)} rows, bounds.jsonl {len(b)}: the export is not of the snapshot')


def sec_queue():
    q = S.tsv('papers.tsv')
    by = collections.Counter(r['status'] for r in q)
    if len(q) != S.st['queue'] or by['done'] != S.st['done']:
        ERRORS.append(f'papers.tsv {len(q)}/{by["done"]} != status {S.st["queue"]}/{S.st["done"]}')
    L.rows['queue.papers']['check'] = len(q)
    L.rows['queue.done']['check'] = by['done']


# ===================================================================================================== 3. export
def sec_export():
    """catlog_wide.jsonl, written by `catlog.py export`; checked here to be the export of the snapshot's catalog."""
    recs = 0
    papers = set()
    closure = outside = 0
    closure_p = set()
    ceil = []
    status = collections.Counter()
    cause_by = collections.Counter()
    have = collections.Counter()
    ids = set()
    for d in S.stream_jsonl('catlog_wide.jsonl'):
        recs += 1
        papers.add(str(d['pubmed_id']))
        for m, e in (d.get('evidence') or {}).items():
            if isinstance(e, dict) and e.get('row_id'):
                ids.add(e['row_id'])
        rc = d.get('ratio_check') or ''
        if rc.startswith('printed kcat/Km'):
            closure += 1
            closure_p.add(str(d['pubmed_id']))
            outside += 'outside tolerance' in rc
        k = d.get('kcat_over_km')
        if k is not None and k >= 1e6:
            ceil.append((str(d['pubmed_id']), d.get('kcat_over_km_flag') or '', d.get('kcat_over_km_source')))
        for f in ('uniprot_id', 'sequence', 'ec_number', 'taxon_id', 'smiles'):
            have[f] += bool(d.get(f))
        have['ec_databases'] += (d.get('ec_source') or '').startswith('databases')
        for m, c in (d.get('database_check') or {}).items():
            if isinstance(c, dict):
                status[c.get('status')] += 1
                if c.get('status') == 'corrected':
                    cause_by[c.get('cause_by')] += 1
    if ids != S.cat_ids:
        ERRORS.append(f'export row ids differ from catalog.jsonl ({len(ids - S.cat_ids)} only in the export, '
                      f'{len(S.cat_ids - ids)} only in the catalog): catlog_wide.jsonl is not the snapshot\'s export')
    S.export_ok = ids == S.cat_ids
    src = 'catlog_wide.jsonl (export; its row ids are exactly catalog.jsonl\'s: ' + ('yes' if S.export_ok else 'NO') + ')'
    L.add('cat.records', recs, 'records: rows of the export (one enzyme or variant, substrate and assay in one paper, '
          'up to three values; catlog.measurements())', kind='snapshot', source=src,
          forms=['in 107,056 records', 'in [107,056] records', '106,677 records', '(20:44; {107,056} records)'],
          check=S.st['records'], note='Methods prints 106,677 (14:26, [n1])')
    if recs != S.st['records'] or len(papers) != S.st['papers']:
        ERRORS.append('export records/papers != status')
    L.add('closure.records', closure, 'records whose printed kcat/Km is compared with their own kcat ÷ Km (ratio_check '
          '"printed kcat/Km ...")', kind='snapshot', source=src, forms=['58,431 records'])
    L.add('closure.papers', len(closure_p), 'papers of those records', kind='snapshot', source=src,
          forms=['from 4,931 papers'])
    L.add('closure.outside_tolerance', outside, 'of those records, the printed kcat/Km outside the tolerance (kept, '
          'with a note)', kind='snapshot', base='closure.records', source=src, forms=['keeps the 757 outside'])
    S.ceil_list = ceil
    rev = [c for c in ceil if c[1]]
    L.add('ceiling.values', len(ceil), 'records with a kcat/Km (printed or derived) at or above 10^6 mM^-1 s^-1 '
          '(10^9 M^-1 s^-1)', kind='snapshot', source=src, forms=['Of 115 kcat/Km values', 'held 115 such values'])
    L.add('ceiling.reviewed', len(rev), 'of those, values with a review line against their paper '
          '(kcat_over_km_flag set from sources/implausible_as_printed.tsv)', kind='snapshot', base='ceiling.values',
          source=src + '; sources/implausible_as_printed.tsv', forms=['111 carry a review', '111 of them with a review'],
          note=f'{len({c[0] for c in rev})} papers; without a review: '
               + ', '.join(sorted({f"{c[0]} ({c[2]})" for c in ceil if not c[1]})))
    for f, key, forms in (('uniprot_id', 'enrich.uniprot_share', ['62.1% of']), ('sequence', 'enrich.sequence_share',
                                                                                 ['59.5% a sequence']),
                          ('ec_number', 'enrich.ec_share', ['91.0% an EC number']),
                          ('ec_databases', 'enrich.ec_from_databases_share', ['for 19.6% of records']),
                          ('smiles', 'enrich.structure_share', ['88.5% a substrate structure']),
                          ('taxon_id', 'enrich.taxon_share', [])):
        L.add(key, pct(have[f], recs), f'records with a non-empty {f if f != "ec_databases" else "ec_source = databases"}'
              ' in the export', kind='snapshot', base='cat.records', source=src, show=pshow(have[f], recs), forms=forms,
              note=f'{have[f]:,} of {recs:,}')
    L.add('db.export.same_number', status['confirmed'], 'stored values for which a database lists the same number for '
          'the same paper and label (database_check status confirmed)', kind='snapshot', source=src,
          forms=['163,170'], note='the Results and Discussion print 163,170 (export of 28 October, page 02)')
    L.add('db.export.in_no_database', status['new'], 'stored values that no database lists (database_check status new)',
          kind='snapshot', source=src, forms=['57,441'],
          note='the Results and Discussion print 57,441 (export of 28 October, page 02)')
    L.add('db.export.code_decided', cause_by['code'], 'database differences that code alone classed as a database '
          'error (status corrected, cause_by code: an exact unit or header factor the paper\'s own kcat ÷ Km confirms)',
          kind='snapshot', source=src, forms=['the 1,268 differences that code decided alone'],
          note='the Results print 1,268 (export of 28 October, page 02); Supplementary Note [n46a] 1,278 (20:44)')
    L.add('db.export.paper_checked', cause_by['paper_check'], 'differences an agent decided from the paper, as the '
          'export shows them (status corrected, cause_by paper_check)', kind='snapshot', source=src)
    L.add('db.export.still_differ', status['differs'], 'differences of 1.5-fold or more still waiting for a check '
          '(status differs)', kind='snapshot', source=src)
    L.add('db.export.same_number_other_label', status['same_number_other_label'], 'values a database lists with the '
          'same number under another label', kind='snapshot', source=src)


# ===================================================================================================== 4. database checks
KIND_ORDER = ['catlog_wrong', 'misread', 'misprint', 'different_measurement', 'ambiguous']


def db_latest(lines, until='9999'):
    """The line in effect per (value, database field): the latest by date, then file order (paper/numbers.py,
    tools/dbcompare.recorded)."""
    latest = {}
    for i, r in sorted(((i, r) for i, r in enumerate(lines) if r['date'] <= until), key=lambda x: (x[1]['date'], x[0])):
        latest[(r['row_id'], r['database'])] = r
    return latest


def db_kind(r):
    return ('misprint' if r['cause'] == 'paper_unit_misprint' else 'misread') if r['verdict'] == 'corrected' \
        else r['verdict']


def db_split(lines, until='9999'):
    latest = db_latest(lines, until)
    rows = list(latest.values())
    per_value = {}
    for r in rows:
        k = db_kind(r)
        if r['row_id'] not in per_value or KIND_ORDER.index(k) < KIND_ORDER.index(per_value[r['row_id']][0]):
            per_value[r['row_id']] = (k, r['pmid'])
    wrong = [r for r in rows if db_kind(r) == 'misread']
    per_db = collections.Counter(d.strip() for r in wrong for d in r['database'].split(','))
    causes = collections.Counter(r['cause'] for r in wrong)
    return {'lines': len([r for r in lines if r['date'] <= until]), 'numbers': len(rows),
            'values': len(per_value), 'papers': len({p for _, p in per_value.values()}),
            'kinds': collections.Counter(k for k, _ in per_value.values()),
            'kind_papers': {k: len({p for kk, p in per_value.values() if kk == k}) for k in KIND_ORDER},
            'misread_numbers': len(wrong), 'per_db': per_db, 'causes': causes, 'latest': latest,
            'per_value': per_value}


def sec_dbcheck():
    lines = S.tsv('sources/database_corrections.tsv')
    S.dbc_lines = lines
    src = 'sources/database_corrections.tsv (latest line per value and database; paper/numbers.py rule)'
    a = db_split(lines)
    last = max(r['date'] for r in lines)
    w = f'verdict lines dated to {last} (the whole file)'
    n, k = a['values'], a['kinds']
    S.dbsplit = a
    L.add('db.check.values', n, 'values where CatLog and a database differ 1.5-fold or more and an agent decided it '
          'against the paper; each value once, under its worst outcome for CatLog (CatLog wrong, database misread, '
          'copied misprint, both right, undecided)', kind='snapshot', window=w, source=src,
          forms=['Of 2,637 such values', 'The 2,637 are', 'of 2,637 values'],
          note='the Results and Discussion print 2,637 (page 02, 28 October); see db.check.values_28oct')
    L.add('db.check.papers', a['papers'], 'papers of those values', kind='snapshot', window=w, source=src,
          forms=['values in 720 papers'])
    for kk, key, what, forms in (
            ('misread', 'db.check.misread', 'the database misread the paper', ['for 2,116 (80.2%)', 'misread it for 2,116']),
            ('misprint', 'db.check.copied_misprint', "the database copied the paper's own misprint (cause "
             'paper_unit_misprint)', ['misprint for 205 (7.8%)']),
            ('different_measurement', 'db.check.both_right', 'both right, about different experiments',
             ['for 239 (9.1%)']),
            ('ambiguous', 'db.check.undecided', 'the paper does not decide', ['did not decide 65 (2.5%)']),
            ('catlog_wrong', 'db.check.catlog_wrong', 'CatLog was wrong', ['CatLog was wrong for 12', 'CatLog for 12',
                                                                            'CatLog was wrong for 12 (0.5%']),):
        L.add(key, k[kk], f'of db.check.values, {what}', kind='snapshot', window=w, base='db.check.values', source=src,
              forms=forms)
        L.add(key + '_share', pct(k[kk], n), f'{key} as a share of db.check.values', kind='snapshot', window=w,
              base='db.check.values', source=src, show=pshow(k[kk], n),
              forms={'misread': ['(80.2%)'], 'misprint': ['(7.8%)'], 'different_measurement': ['(9.1%)'],
                     'ambiguous': ['(2.5%)'], 'catlog_wrong': ['(0.5%, in 4 papers)']}[kk])
    L.add('db.check.catlog_wrong_papers', a['kind_papers']['catlog_wrong'], 'papers of the CatLog-wrong values',
          kind='snapshot', window=w, source=src, forms=['(0.5%, in {4} papers)'])
    # CatLog's wrong values: where each was printed, and whether a unitfix corrected it since
    cw = [r for r in a['latest'].values() if r['verdict'] == 'catlog_wrong']
    cw_ids = {r['row_id'] for r in cw}
    rows = {r['row_id']: r for r in S.cat}
    rej = {}
    for r in S.rej:
        if r.get('row_id') in cw_ids:
            rej[r['row_id']] = r
    loc = collections.Counter()
    fixed = 0
    detail = []
    for rid in sorted(cw_ids):
        r = rows.get(rid) or rej.get(rid) or {}
        where = (r.get('location') or '?')
        typ = 'table header' if where.lower().startswith(('table', 'supplementary table')) else where.split(',')[0]
        f = rid in S.unitfix_ids
        fixed += f
        loc[(typ, f)] += 1
        detail.append(f'{r.get("pmid")} {rid} {where} {"unitfix" if f else "kept"}')
    L.add('db.check.catlog_wrong_unitfixed', fixed, 'of the CatLog-wrong values, those corrected since by a logged '
          '`unitfix` (a misprinted unit CatLog had read as printed)', kind='snapshot', window=w,
          base='db.check.catlog_wrong', source=src + '; log.tsv unitfix; catalog.jsonl location',
          forms=['10 of the 12 values CatLog had wrong', 'ten misprinted headers it had read the other way=>10'],
          note='by where the cell is printed (location, corrected?): ' + '; '.join(f'{t} {"unitfix" if f else "kept"} {c}'
                                                                                for (t, f), c in sorted(loc.items()))
               + '. Rows: ' + '; '.join(detail))
    L.add('db.check.catlog_wrong_kept_by_audit', len(cw_ids) - fixed, 'of the CatLog-wrong values, those a later '
          'audit kept as printed', kind='snapshot', window=w, base='db.check.catlog_wrong', source=src,
          forms=['two values that a later audit kept'])
    # per database number (the Fig. 4 unit) and per database
    L.add('db.check.numbers', a['numbers'], 'database numbers decided: the latest line per value and database field '
          '(a number several databases list as one field, "BRENDA, OED", is one number)', kind='snapshot', window=w,
          source=src, forms=['for 2,170 of {2,709} numbers', '2,709 in 733 papers'],
          note='the Introduction and Fig. 4 print 2,709 (30 October): the same definition with the window "dated 30 October or earlier" (db.fig4.numbers, check; db.check.values_30oct)')
    L.add('db.check.misread_numbers', a['misread_numbers'], 'of db.check.numbers, numbers the database misread '
          "(corrected, not the paper's own misprint)", kind='snapshot', window=w, base='db.check.numbers', source=src,
          forms=['misread it for 2,170', 'Of the 2,170 numbers'])
    order = ['BRENDA', 'OED', 'SABIO-RK', 'SKiD', 'UniProt', 'STRENDA']
    forms_db = {'BRENDA': 'BRENDA misread 1,629 values', 'OED': 'OED 476', 'SABIO-RK': 'SABIO-RK 357',
                'SKiD': 'SKiD 146', 'UniProt': 'UniProt 25', 'STRENDA': 'STRENDA DB 12'}
    for d in order:
        L.add(f'db.check.misread_in.{d}', a['per_db'][d], f'misread numbers that name {d} (a number in a field naming '
              'several databases counts once in each)', kind='snapshot', window=w, source=src, forms=[forms_db[d]])
    tot = a['misread_numbers']
    for c, key, form in (('decimal_or_exponent_slip', 'decimal_slip', '(17.9%)'),
                         ('header_scale_inverted', 'header_backwards', '(13.8%)'),
                         ('unit_not_converted', 'unit_not_converted', '(12.6%)'),
                         ('value_not_in_paper', 'not_printed', '11.0% are numbers printed nowhere'),
                         ('uM_entered_as_mM', 'uM_as_mM', None), ('time_unit', 'time_unit', None),
                         # the fifth cause by size, which outline L43 had left out (verify_round2.md)
                         ('value_from_other_row', 'other_row', None)):
        L.add(f'db.check.cause_share.{key}', pct(a['causes'][c], tot), f'share of misread numbers with cause {c}',
              kind='snapshot', window=w, base='db.check.misread_numbers', source=src, show=pshow(a['causes'][c], tot),
              forms=[form] if form else [], note=f'{a["causes"][c]:,} of {tot:,}; page 02 prints shares of 2,119 '
                                                 '(28 October)')
    # the same definitions at the drafts' dates (the file's dates are days, so 28 October includes lines added after
    # page 02 was counted that day; 30 October reproduces Fig. 4)
    for until, tag in (('2026-10-28', '28oct_day'), ('2026-10-30', '30oct')):
        b = db_split(lines, until)
        L.add(f'db.check.values_{tag}', b['values'], f'db.check.values with the window "dated {until} or earlier"',
              kind='window', window=f'verdict lines dated to {until}', source=src,
              note=f"papers {b['papers']}, misread {b['kinds']['misread']}, copied misprint {b['kinds']['misprint']}, "
                   f"both right {b['kinds']['different_measurement']}, undecided {b['kinds']['ambiguous']}, CatLog "
                   f"wrong {b['kinds']['catlog_wrong']}; numbers {b['numbers']}, misread numbers {b['misread_numbers']}"
                   f"; per database {dict(b['per_db'])}")
    S.db30 = db_split(lines, '2026-10-30')
    # page 02 (28 October), frozen: the counts the Results and Discussion print
    t = S.evidence('paper/02_catlog_vs_databases.md')
    w28 = 'page 02 of 28 October (database_corrections.tsv as it stood when paper/numbers.py ran that day)'
    for key, s, v in (('db.check.values_28oct', '2,637 values', 2637), ('db.check.papers_28oct', '720 papers', 720),
                      ('db.check.misread_28oct', '2,116', 2116), ('db.check.misread_numbers_28oct', '2,119', 2119),
                      ('db.export.same_number_28oct', '163,170', 163170), ('db.export.in_no_database_28oct', '57,441', 57441),
                      ('db.export.code_decided_28oct', '1,268 by', 1268)):
        must(t, s, 'paper/02_catlog_vs_databases.md')
        L.add(key, v, f'{key.split("_28oct")[0]} as page 02 counted it on 28 October', kind='frozen', window=w28,
              source='paper/02_catlog_vs_databases.md', check=None)


# ===================================================================================================== 5. Fig. 4
FACTORS = sorted({b for b in range(-13, 14)} |
                 {b + a * math.log10(t) for b in (-3, 0, 3) for t in (60, 3600) for a in (1, -1)})
NUMRX = re.compile(r'^\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?)')


def fig4_points(latest):
    """paper/figures/database_errors/factor_counts.py, re-implemented: one point per database number, at the ratio the
    agent judged (the check's task file, times_catlog), else at the database number over CatLog's value today."""
    if not hasattr(S, 'dbtasks'):
        checks = collections.defaultdict(list)
        files = sorted(glob.glob(P('work', 'old', 'dbcheck_*.task.*.json')) + glob.glob(P('work', 'dbcheck_*.task.*.json')))
        h = hashlib.sha256()
        for f in files:
            raw = open(f, 'rb').read()
            h.update(raw)
            t = json.loads(raw)
            ratios = {(v['row_id'], d['database']): d.get('times_catlog') for v in t.get('values') or []
                      for d in v.get('databases') or [] if d.get('times_catlog')}
            vf = f.replace('.task.', '.')
            keys = set()
            if os.path.exists(vf):
                vraw = open(vf, 'rb').read()
                h.update(vraw)
                for v in json.loads(vraw).get('verdicts') or []:
                    for db in str(v.get('database') or '').split(','):
                        keys.add((v.get('row_id'), db.strip(), v.get('verdict')))
            checks[str(t['pmid'])].append((t.get('made') or '', ratios, keys))
        S.dbtasks = checks
        S.files['work/old/dbcheck_*.task.*.json (+ verdict files)'] = {'sha256': h.hexdigest(), 'bytes': None,
                                                                       'mtime': '', 'git': 'ignored (work/)',
                                                                       'last_commit': f'{len(files)} task files'}
    cat = {r['row_id']: r for r in S.cat}
    rej = {r['row_id']: r for r in S.rej if r.get('row_id')}

    def judged(r):
        dbs = [d.strip() for d in r['database'].split(',')]
        for made, ratios, keys in sorted(S.dbtasks.get(r['pmid'], []), key=lambda m: m[0], reverse=True):
            if made[:10] > r['date'] or not any((r['row_id'], db, r['verdict']) in keys for db in dbs):
                continue
            for db in dbs:
                if (r['row_id'], db) in ratios:
                    return ratios[(r['row_id'], db)]
        return None
    pts = []
    for r in latest.values():
        t = judged(r)
        if t:
            x, src = math.log10(t), 'task file'
        else:
            c = cat.get(r['row_id']) or rej.get(r['row_id'])
            x, src = math.log10(float(NUMRX.match(r['database_value']).group(1)) / float(c['value'])), 'catalog today'
        f = min(FACTORS, key=lambda f: abs(10 ** (x - f) - 1))
        on = abs(10 ** (x - f) - 1) <= 0.01 and f != 0
        db = math.log10(float(NUMRX.match(r['database_value']).group(1)))
        kind = (("copied" if r['cause'] == 'paper_unit_misprint' else 'misread') if r['verdict'] == 'corrected'
                else r['verdict'])
        pts.append({'pmid': r['pmid'], 'database': r['database'], 'metric': r['metric'], 'x': x, 'db': db,
                    'cat': db - x, 'factor': f if on else None, 'kind': kind, 'cause': r['cause'], 'from': src})
    return pts


def fig4_stats(pts):
    mis = [p for p in pts if p['kind'] == 'misread']
    on_mis = [p for p in mis if p['factor'] is not None]
    by_paper = collections.defaultdict(list)
    for p in mis:
        by_paper[p['pmid']].append(p['factor'] is not None)
    most = sum(1 for v in by_paper.values() if sum(v) > len(v) / 2)
    allp = sum(1 for v in by_paper.values() if all(v))

    def at(f):
        return [p for p in mis if p['factor'] is not None and abs(p['factor'] - f) < 1e-6]

    def papers(ps, causes=None):
        return len({p['pmid'] for p in ps if causes is None or p['cause'] in causes})
    conc = {'uM_entered_as_mM', 'mM_entered_as_uM', 'unit_not_converted'}
    dec = {'decimal_or_exponent_slip'}
    lines = {}
    for f, causes in ((3, conc), (-3, conc), (1, dec), (-1, dec), (2, dec), (-2, dec),
                      (math.log10(60), {'time_unit'})):
        ps = at(f)
        lines[round(f, 3)] = (papers(ps, causes), papers(ps))
    deep = [p for p in mis if p['factor'] is not None and -12.5 <= p['factor'] <= -7.5]
    deep_papers = {p['pmid'] for p in deep}
    deep_hdr = {p['pmid'] for p in deep if p['cause'] == 'header_scale_inverted'}

    def oed(dbv, catv):
        ps = [p for p in pts if 'OED' in p['database'] and p['metric'] == 'kcat' and abs(10 ** p['db'] - dbv) < 1e-9
              and abs(10 ** p['cat'] - catv) / catv < 0.01]
        return len(ps), papers(ps)
    return {'numbers': len(pts), 'values': None, 'papers': papers(pts), 'misread': len(mis),
            'misread_on_factor': len(on_mis), 'on_factor_all': sum(1 for p in pts if p['factor'] is not None),
            'papers_with_misreading': len(by_paper), 'papers_most_on_factor': most, 'papers_all_on_factor': allp,
            'papers_any_on_factor': len({p['pmid'] for p in pts if p['factor'] is not None}),
            'lines': lines, 'deep_papers': len(deep_papers), 'deep_header_backwards': len(deep_hdr),
            'oed_45_36': oed(4.5, 36), 'oed_5_28': oed(5, 28),
            'ratio_from': collections.Counter(p['from'] for p in pts),
            'catlog_wrong': sum(1 for p in pts if p['kind'] == 'catlog_wrong'),
            'catlog_wrong_papers': len({p['pmid'] for p in pts if p['kind'] == 'catlog_wrong'})}


def sec_fig4():
    src = ('sources/database_corrections.tsv; the checks\' task and verdict files work/old/dbcheck_<PMID>.task.<t>.json '
           'and dbcheck_<PMID>.<t>.json; catalog.jsonl, rejected.jsonl (paper/figures/database_errors/factor_counts.py, '
           're-implemented)')
    now = fig4_stats(fig4_points(S.dbsplit['latest']))
    d30 = fig4_stats(fig4_points(S.db30['latest']))
    fz = json.loads(S.evidence('paper/figures/database_errors/factor_counts.json'))
    # factor_counts.json held the 30 October window until the paper freeze (16 Nov 2026), when it was recounted at the tag
    # paper-catalog-freeze-20261116 (Fig. 3g): either window may match, and the ledger names which one did
    pair = (fz['database_values'], fz['on_a_unit_factor'])
    fz_window = ('30 October' if pair == (d30['numbers'], d30['on_factor_all']) else
                 'this snapshot' if pair == (now['numbers'], now['on_factor_all']) else None)
    if fz_window is None:
        ERRORS.append(f'factor_counts.json matches neither the 30 October window nor this snapshot: {pair} vs '
                      f'{d30["numbers"]}/{d30["on_factor_all"]} and {now["numbers"]}/{now["on_factor_all"]}')
    w = S.rows_window = 'verdict lines dated to ' + max(r['date'] for r in S.dbc_lines)
    chk = lambda k: d30[k]
    L.add('db.fig4.numbers', now['numbers'], 'database numbers an agent decided (Fig. 4 dots; = db.check.numbers)',
          kind='snapshot', window=w, source=src, check=d30['numbers'],
          note='check = the same count with the window "dated 30 October or earlier", which the figure (2,709) used '
               f'until the paper freeze; factor_counts.json now holds the {fz_window or "unmatched"} window')
    L.add('db.fig4.papers', now['papers'], 'papers of those numbers', kind='snapshot', window=w, source=src,
          check=d30['papers'], forms=['2,709 in {733} papers'])
    L.add('db.fig4.misread_on_unit_factor', now['misread_on_factor'], 'misread numbers within 1% of a unit factor '
          '(a power of ten other than 1, or 60 or 3,600 either way, alone or times or over 1,000), at the ratio the agent '
          'judged', kind='snapshot', window=w, base='db.check.misread_numbers', source=src,
          check=chk('misread_on_factor'), forms=['1,636 (75%) lie within 1%'])
    L.add('db.fig4.misread_on_unit_factor_share', pct(now['misread_on_factor'], now['misread']),
          'db.fig4.misread_on_unit_factor as a share of the misread numbers', kind='snapshot', window=w,
          base='db.check.misread_numbers', source=src, show=pshow(now['misread_on_factor'], now['misread'], 0),
          check=pct(d30['misread_on_factor'], d30['misread']),
          forms=['75% of the misread numbers', '1,636 ({75}%)', 'Three in four misreadings=>75'])
    L.add('db.fig4.on_unit_factor_all', now['on_factor_all'], 'all decided numbers (any verdict) within 1% of a unit '
          'factor', kind='snapshot', window=w, base='db.fig4.numbers', source=src, check=chk('on_factor_all'),
          note='not in the draft text; Fig. 4 README prints 1,934 of 2,709 (71%)')
    L.add('db.fig4.papers_with_misreading', now['papers_with_misreading'], 'papers with at least one misread number',
          kind='snapshot', window=w, source=src, check=chk('papers_with_misreading'), forms=['of the 593 papers'])
    L.add('db.fig4.papers_most_on_factor', now['papers_most_on_factor'], 'of those papers, papers in which more than '
          'half of the misread numbers lie at a unit factor', kind='snapshot', window=w,
          base='db.fig4.papers_with_misreading', source=src, check=chk('papers_most_on_factor'),
          forms=['In 333 of the 593'])
    L.add('db.fig4.papers_all_on_factor', now['papers_all_on_factor'], 'of those papers, papers in which every misread '
          'number lies at a unit factor', kind='snapshot', window=w, base='db.fig4.papers_with_misreading', source=src,
          check=chk('papers_all_on_factor'))
    names = {3: ('x1000', 'concentration units mixed up (cause uM_entered_as_mM, mM_entered_as_uM or unit_not_converted)',
                 ['(in 63 of 81'], ['63 of {81}']),
             -3: ('x1/1000', 'concentration units mixed up', ['46 of 59 papers'], ['46 of {59} papers']),
             1: ('x10', 'a decimal point or exponent slipped (decimal_or_exponent_slip)', ['(60 of 66'], ['60 of {66}']),
             -1: ('x1/10', 'a decimal point or exponent slipped', ['84 of 86)'], ['84 of {86})']),
             2: ('x100', 'a decimal point or exponent slipped', [], []),
             -2: ('x1/100', 'a decimal point or exponent slipped', [], []),
             round(math.log10(60), 3): ('x60', 'a time unit (time_unit)', [], ['(18 of {21})'])}
    for f, (lab, why, fm, fp) in names.items():
        k, n = now['lines'][round(f, 3)]
        k30, n30 = d30['lines'][round(f, 3)]
        L.add(f'db.fig4.line.{lab}.papers', n, f'papers with a misread number at {lab} (within 1%)', kind='snapshot',
              window=w, source=src, check=n30, forms=fp)
        L.add(f'db.fig4.line.{lab}.main_cause', k, f'of those papers, papers with a misread number there whose cause '
              f'is {why}', kind='snapshot', window=w, base=f'db.fig4.line.{lab}.papers', source=src, check=k30,
              forms=fm)
    E('db.fig4.line.x60.min_as_s', 18, 'of the papers at x60, papers where a per-minute value was taken as per second '
      '(a split of the time_unit papers made by reading the cases; not recomputed here)',
      'paper/figures/database_errors/README.md', needle='18 of them a per-minute value taken as per second',
      state='ON FILE', window='factor_counts.json of 2026-10-30', forms=['(18 of 21)'],
      check=d30['lines'][round(math.log10(60), 3)][0],
      note='check = papers at x60 with cause time_unit (20 at 30 October)')
    L.add('db.fig4.deep_lines.papers', now['deep_papers'], 'papers with a misread number on the lines from 10^-8 to '
          '10^-12', kind='snapshot', window=w, source=src, check=d30['deep_papers'],
          forms=['In all 14 papers on the lines'])
    L.add('db.fig4.deep_lines.header_backwards', now['deep_header_backwards'], 'of those papers, papers whose misread '
          'number there has cause header_scale_inverted (a column header\'s power of ten applied backwards)',
          kind='snapshot', window=w, base='db.fig4.deep_lines.papers', source=src, check=d30['deep_header_backwards'])
    for key, val, v30, what, forms in (
            ('db.fig4.oed_4.5_vs_36', now['oed_45_36'], d30['oed_45_36'], 'OED kcat numbers 4.5 s^-1 where CatLog '
             'stores 36 s^-1: numbers, papers', ['where 15 papers print 36']),
            ('db.fig4.oed_5_vs_28', now['oed_5_28'], d30['oed_5_28'], 'OED kcat numbers 5 s^-1 where CatLog stores '
             '28 s^-1: numbers, papers', ['where 17 papers print 28'])):
        L.add(key + '.papers', val[1], what.replace('numbers, papers', 'papers'), kind='snapshot', window=w,
              source=src, check=v30[1], forms=forms, note=f'{val[0]} numbers')
    L.add('db.fig4.catlog_wrong', now['catlog_wrong'], 'Fig. 4 numbers on which CatLog was wrong', kind='snapshot',
          window=w, source=src, check=d30['catlog_wrong'], note=f'{now["catlog_wrong_papers"]} papers')
    S.fig4_now, S.fig4_30 = now, d30


# ===================================================================================================== 6. every value through the checks
FLOW_INTERNAL = re.compile(r're-read copy|re-read duplicat|reworded|conflicts with accepted|audit dropped this meas|'
                           r'duplicate of accepted|already accepted', re.I)
FLOW_REASONS = [(k, re.compile(v, re.I)) for k, v in [
    ('retracted or corrected by the authors', r'retract|corrigend|erratum'),
    ('printed twice in the same paper', r'duplicate|printed again|restates'),
    ('reprinted from an earlier paper', r'reprint|carried over|not measured (?:here|in this paper)|previously reported|'
                                        r'identical to (?:ref|PMID|the same lab|the authors)'),
    ('partial constant of a branched reaction', r'partial|per-product|per[- ]site|branched reaction|two bonds|cleavage|'
                                                r'beta-kcat|cin-kcat|one product'),
    ('misprint, copy slip or impossible number', r'header|misprint|diffusion|cannot mean|quotient|10x|1000x|inconsisten|'
                                                 r'slip|identical to the \S+ row'),
    ('not a kcat or Km (Hill, Ki, Kd, Vmax, ratio, cofactor)', r'\bHill\b|K0\.5|S0\.5|\bK_?i\b|\bK_?d\b|inhibition '
     r'constant|dissociation constant|specific activity|\bVmax\b|molecular activity|rate constant|single[- ]turnover|'
     r'pseudo-first|initial rate|binding constant|not a kcat|not a Km|not a turnover|fold ratio|not detected was stored|'
     r'not converted|not consumed|activator|cofactor')]]


def flow(until):
    """paper/figures/supp_agent_flow/flow_counts.py, re-implemented on the snapshot: every numeric value that reached
    the checks, once, with its fate; `until` keeps rows added (refusals recorded) at or before that time."""
    def slot(r):
        return (str(r.get('pmid')), r.get('metric'), str(r.get('raw_value')).strip(), str(r.get('location')).strip(),
                str(r.get('variant')).strip(), str(r.get('substrate')).strip())

    def numv(v):
        try:
            v = float(v)
            return v if math.isfinite(v) and v > 0 else None
        except (TypeError, ValueError):
            return None

    def layer(why):
        if FLOW_INTERNAL.search(why):
            return 'internal'
        if 'verifier_reject' in why:
            return 'verifier'
        if re.search(r'audit', why):
            return 'later'
        return 'code'
    missed = S.missed
    cat, slots = [], set()
    cat_nums = collections.defaultdict(list)
    for r in S.cat:
        if (r.get('added') or '') > until:
            continue
        cat.append(r)
        slots.add(slot(r))
        if numv(r.get('value')):
            cat_nums[(str(r.get('pmid')), r.get('metric'))].append(numv(r.get('value')))
    last = {}
    for r in S.rej:
        s = slot(r)
        if s in slots or (r.get('checked') or '') > until:
            continue
        why = str(r.get('why') or '')
        if layer(why) == 'internal':
            continue
        last[s] = (layer(why), bool(r.get('corrected')), (str(r.get('pmid')), r.get('metric'), s[2]) in missed, why,
                   r.get('value'))
    flows = collections.Counter()
    for r in cat:
        src = 'verifier found' if (str(r.get('pmid')), r.get('metric'), str(r.get('raw_value')).strip()) in missed else 'reader'
        flows[(src, 'fixed' if r.get('corrected') else 'confirmed', 'kept', 'in catalog')] += 1
    db = S.dbvals_index
    refused = collections.Counter()
    for s, (lay, corr, ism, why, val) in list(last.items()):
        v = numv(val)
        if v is None:
            del last[s]
            continue
        held = any(abs(x - v) <= 0.01 * abs(v) for x in db.get((s[0], s[1]), []))
        in_cat = any(abs(x - v) <= 0.01 * abs(v) for x in cat_nums.get((s[0], s[1]), []))
        dbk = ('db and catlog' if in_cat else 'db only') if held else 'no db'
        reason = ('code' if lay == 'code' else next((k for k, r_ in FLOW_REASONS if r_.search(why)), 'other'))
        refused[(lay, reason, dbk)] += 1
    fixed_kind = collections.Counter()
    for r in cat:
        c = r.get('corrected')
        if c:
            fixed_kind['uvm' if set(c) & {'unit_for_conversion', 'raw_unit', 'raw_value', 'metric'} else 'other'] += 1
    for s, (lay, corr, ism, why, val) in last.items():
        src = 'verifier found' if ism else 'reader'
        if lay == 'verifier':
            flows[(src, 'rejected', '-', '-')] += 1
        elif lay == 'code':
            flows[(src, 'fixed' if corr else 'confirmed', 'code rejected', '-')] += 1
        else:
            flows[(src, 'fixed' if corr else 'confirmed', 'kept', 'dropped later')] += 1
    tot = sum(flows.values())
    by_v = collections.Counter()
    for (a, b, c, d), n in flows.items():
        by_v[b] += n
    code = sum(n for (a, b, c, d), n in flows.items() if c == 'code rejected')
    later = sum(n for (a, b, c, d), n in flows.items() if d == 'dropped later')
    nonc = {k: n for k, n in refused.items() if k[0] != 'code'}
    return {'values': tot, 'in_catalog': len(cat), 'confirmed': by_v['confirmed'], 'fixed': by_v['fixed'],
            'rejected': by_v['rejected'], 'code_refused': code, 'dropped_later': later,
            'fixed_uvm': fixed_kind['uvm'], 'fixed_in_catalog': sum(fixed_kind.values()),
            'refused_total': sum(nonc.values()),
            'refused_db_only': sum(n for k, n in nonc.items() if k[2] == 'db only'),
            'refused_db_and_catlog': sum(n for k, n in nonc.items() if k[2] == 'db and catlog'),
            'refused_reprint': sum(n for k, n in nonc.items() if k[1] == 'reprinted from an earlier paper'),
            'refused_reprint_db_only': sum(n for k, n in nonc.items() if k[1] == 'reprinted from an earlier paper'
                                           and k[2] == 'db only'),
            'refused_partial': sum(n for k, n in nonc.items() if k[1] == 'partial constant of a branched reaction'),
            'missed_matched': sum(n for (a, *_), n in flows.items() if a == 'verifier found')}


def sec_flow():
    S.missed = set()
    h = hashlib.sha256()
    files = sorted(glob.glob(P('work', '*.missed.read.json')))
    for f in files:
        raw = open(f, 'rb').read()
        h.update(raw)
        d = json.loads(raw)
        for r in d.get('rows') or []:
            S.missed.add((str(d.get('pmid')), r.get('metric'), str(r.get('raw_value')).strip()))
    S.files['work/*.missed.read.json'] = {'sha256': h.hexdigest(), 'bytes': None, 'mtime': '',
                                          'git': 'ignored (work/)', 'last_commit': f'{len(files)} files'}
    idx = collections.defaultdict(list)
    S.dbvals = S.tsv('sources/db_values.tsv', quoting=csv.QUOTE_MINIMAL)
    for d in S.dbvals:
        try:
            idx[(d['pmid'], d['metric'])].append(float(d['value']))
        except ValueError:
            pass
    S.dbvals_index = idx
    src = ('catalog.jsonl, rejected.jsonl, work/*.missed.read.json, sources/db_values.tsv '
           '(paper/figures/supp_agent_flow/flow_counts.py, re-implemented)')
    dev_until = '2026-10-28 20:10'
    a = flow(dev_until)
    z = flow('9999')
    fz = json.loads(S.evidence('paper/figures/supp_agent_flow/flow_counts.json'))
    fzt = fz['totals']
    fv = collections.Counter()
    for f in fz['flows']:
        fv[f['verifier']] += f['values']
    fcode = sum(f['values'] for f in fz['flows'] if f['code'] == 'code rejected')
    flater = sum(f['values'] for f in fz['flows'] if f['later'] == 'dropped later')
    ref = [r for r in fz['refused'] if r['layer'] != 'code checks']
    fref = sum(r['values'] for r in ref)
    fdb = sum(r['values'] for r in ref if r['database'] == 'in a database only')
    frep = sum(r['values'] for r in ref if r['reason'] == 'reprinted from an earlier paper')
    fpar = sum(r['values'] for r in ref if r['reason'] == 'partial constant of a branched reaction')
    fk = fz['fixed_in_catalog_by_kind']
    wfz = 'frozen: flow_counts.json, --until 2026-10-28 20:10'
    srcfz = 'paper/figures/supp_agent_flow/flow_counts.json (frozen 2026-10-28 22:26, --until "2026-10-28 20:10")'
    note = ('check = the same definition recomputed from the snapshot files with the same --until; values dropped since '
            'leave the rebuilt window, so it can differ by the drops since')
    T = fzt['values']
    L.add('flow.reached_checks_28oct', T, 'numeric values that reached the code checks, each once over all reads '
          '(the catalog\'s rows plus every refused printed cell not in the catalog under another read), to 28 October '
          '20:10', kind='frozen', window=wfz, source=srcfz, state='DEV', check=a['values'], note=note,
          forms=['Of the 239,018 values', '239,018 values (DEV)'])
    for key, k, ka, what, forms in (
            ('flow.confirmed_share_28oct', fv['confirmed'], a['confirmed'], 'the verifier confirmed', ['confirmed 95.2%']),
            ('flow.fixed_share_28oct', fv['fixed'], a['fixed'], 'the verifier corrected (fixed)',
             ['corrected 4.3%', 'fixed 4.3%']),
            ('flow.rejected_share_28oct', fv['rejected'], a['rejected'], 'the verifier rejected',
             ['rejected 0.5%', 'rejected 0.5% of']),
            ('flow.code_refused_share_28oct', fcode, a['code_refused'], 'code refused', ['code refused 0.2%']),
            ('flow.dropped_later_share_28oct', flater, a['dropped_later'], 'audits and sweeps later dropped',
             ['dropped 0.6%'])):
        L.add(key, pct(k, T), f'share of flow.reached_checks_28oct that {what}', kind='frozen', window=wfz,
              base='flow.reached_checks_28oct', source=srcfz, state='DEV', show=pshow(k, T),
              check=pct(ka, a['values']), forms=forms, note=f'{k:,} of {T:,}')
    L.add('flow.fixes_changing_unit_value_metric_28oct', pct(fk['unit, value or metric'], sum(fk.values()), 0),
          'of the verifier\'s fixes kept in the catalog, the share that changed a unit (conversion or printed), the '
          'printed value or the metric', kind='frozen', window=wfz, source=srcfz, state='DEV',
          show=pshow(fk['unit, value or metric'], sum(fk.values()), 0),
          check=pct(a['fixed_uvm'], a['fixed_in_catalog'], 0), forms=['39% changed a unit'])
    L.add('flow.refused_values_28oct', fref, 'numeric values refused by verifiers, audits and sweeps (not code), each '
          'printed cell once at its latest fate', kind='frozen', window=wfz, source=srcfz + '; 04_agent_case_tables.md',
          state='ON FILE', check=a['refused_total'], forms=['Of 2,787 values', 'of the 2,787 values'])
    L.add('flow.refused_listed_by_db_28oct', fdb, 'of those, values a database lists for that paper (same quantity, '
          'number within 1%, substrate not compared) while CatLog keeps no such number', kind='frozen', window=wfz,
          base='flow.refused_values_28oct', source=srcfz, check=a['refused_db_only'],
          forms=['a database lists 1,320 (47%)', 'up to 1,320 of'])
    L.add('flow.refused_listed_by_db_share_28oct', pct(fdb, fref, 0), 'flow.refused_listed_by_db_28oct as a share',
          kind='frozen', window=wfz, base='flow.refused_values_28oct', source=srcfz, show=pshow(fdb, fref, 0),
          forms=['(47%)'])
    L.add('flow.refused_reprint_28oct', frep, 'of the refused values, those whose reason reads as reprinted from an '
          'earlier paper (a regular expression; a blind agent agreed for 87 of 100 sampled)', kind='frozen',
          window=wfz, source=srcfz, check=a['refused_reprint'], forms=['earlier papers (1,502)'])
    L.add('flow.refused_partial_28oct', fpar, 'of the refused values, those whose reason reads as a partial constant '
          'of a branched reaction', kind='frozen', window=wfz, source=srcfz, check=a['refused_partial'],
          forms=['(429, ED Table 2)'])
    w = 'snapshot (no --until)'
    for key, v, what in (('flow.reached_checks', z['values'], 'flow.reached_checks_28oct at the snapshot'),
                         ('flow.fixed', z['fixed'], 'values the verifier fixed, at the snapshot'),
                         ('flow.rejected', z['rejected'], 'values the verifier rejected, at the snapshot'),
                         ('flow.code_refused', z['code_refused'], 'values code refused, at the snapshot'),
                         ('flow.dropped_later', z['dropped_later'], 'values audits and sweeps dropped, at the snapshot'),
                         ('flow.refused_values', z['refused_total'], 'flow.refused_values_28oct at the snapshot'),
                         ('flow.refused_listed_by_db', z['refused_db_only'], 'flow.refused_listed_by_db_28oct at the '
                                                                            'snapshot')):
        L.add(key, v, what, kind='snapshot', window=w, source=src)
    L.add('flow.fixes_changing_unit_value_metric', pct(z['fixed_uvm'], z['fixed_in_catalog'], 0), 'of the verifier\'s '
          'fixes kept in the catalog, the share that changed a unit, the printed value or the metric, at the snapshot',
          kind='snapshot', window=w, source=src, show=pshow(z['fixed_uvm'], z['fixed_in_catalog'], 0),
          note=f"{z['fixed_uvm']:,} of {z['fixed_in_catalog']:,}")
    L.add('flow.fixed_share', pct(z['fixed'], z['values']), 'flow.fixed as a share of flow.reached_checks',
          kind='snapshot', window=w, source=src, show=pshow(z['fixed'], z['values']))
    L.add('flow.rejected_share', pct(z['rejected'], z['values']), 'flow.rejected as a share of flow.reached_checks',
          kind='snapshot', window=w, source=src, show=pshow(z['rejected'], z['values']))


# ===================================================================================================== 7. log-based counts
def sec_logcounts():
    src = 'log.tsv'
    first = {}
    day = collections.defaultdict(collections.Counter)
    for f in S.log:
        d = f[0][:10]
        if f[2] == 'add':
            kv = dict(x.split('=', 1) for x in f[3:] if '=' in x)
            day[d]['values'] += int(kv.get('kept', 0) or 0)
            if f[1] not in first:
                first[f[1]] = d
                day[d]['papers'] += 1
    w = ('2026-10-07', '2026-10-21')
    active = [d for d in sorted(day) if w[0] <= d <= w[1] and day[d]['papers']]
    pa = [day[d]['papers'] for d in active]
    va = [day[d]['values'] for d in active]
    win = 'log.tsv add lines dated 2026-10-07 to 2026-10-21 (reading days: days on which a paper was first added)'
    L.add('throughput.reading_days', len(active), 'days from 7 to 21 October on which at least one paper was first '
          'added', kind='window', window=win, source=src, state='DEV', forms=['On its 14 reading days'])
    L.add('throughput.papers_per_day_median', statistics.median(pa), 'median over those days of papers first added '
          'that day', kind='window', window=win, source=src, state='DEV', show=fmt(int(statistics.median(pa))),
          forms=['a median of 495 new papers a day', 'a median of 495 papers'],
          check=json.loads(S.evidence('paper/evidence/rethink_20261101/pipeline_stats.json'))
          ['papers_per_reading_day']['median'],
          note='check = pipeline_stats.json\'s "median" field (outline L9\'s 516), which takes the upper middle of the '
               '14 days, not the median')
    L.add('throughput.papers_per_day_max', max(pa), 'the most papers first added on one of those days', kind='window',
          window=win, source=src, state='DEV', forms=['(maximum 840)'])
    L.add('throughput.values_per_day_median', statistics.median(va), 'median over those days of values kept by add '
          '(add lines\' kept=)', kind='window', window=win, source=src, state='DEV', show=fmt(int(statistics.median(va))),
          forms=['14,183 values per reading day'])
    L.add('throughput.values_per_day_max', max(va), 'the most values kept by add on one of those days', kind='window',
          window=win, source=src, state='DEV')
    # one-off sweeps, from their log lines
    rp = [f for f in S.log if f[2] == 'drop' and '2026-10-16 11:35' <= f[0][:16] <= '2026-10-16 13:50'
          and len(f) > 4 and f[4].startswith('reprinted')]
    L.add('sweep.reprint.dropped', len(rp), 'values the reprint sweep dropped (log.tsv drop lines "reprinted: ..." of '
          '16 October 11:35-13:50)', kind='snapshot', window='log.tsv, 2026-10-16', source=src,
          forms=['removed 973 values from 80 papers', '973 rows in 80 papers were dropped', "the sweep's 973 values"],
          note='Fig. 3a counts 970 of them still dropped in its 22 October snapshot (dev.layers.reprints)')
    L.add('sweep.reprint.papers', len({f[1] for f in rp}), 'papers of those values', kind='snapshot',
          window='log.tsv, 2026-10-16', source=src, forms=['from {80} papers', 'in {80} papers were dropped'])
    sc = [f for f in S.log if f[2] == 'unitfix' and 'scale sweep' in ' '.join(f[4:]).lower()]
    sc = sc or [f for f in S.log if f[2] == 'unitfix' and f[0].startswith('2026-10-20 07:2')]
    L.add('sweep.scale.values_fixed', len(sc), 'values the unit-factor sweep corrected (log.tsv unitfix lines of its '
          'run, 20 October)', kind='snapshot', window='log.tsv, 2026-10-20', source=src,
          forms=['corrected 16 values', 'and fixed 16 values'])
    vm = [f for f in S.log if f[0].startswith('2026-10-23 14:33') and f[2] == 'unitfix']
    L.add('sweep.vmax.values_fixed', len(vm), 'values the maximal-rate check corrected (log.tsv unitfix lines of '
          '23 October 14:33)', kind='snapshot', window='log.tsv, 2026-10-23', source=src, forms=['(20 values corrected)'],
          note='papers ' + ', '.join(sorted({f[1] for f in vm})))
    nd_drop = [f for f in S.log if f[2] == 'drop_bound' and 'nd_check' in ' '.join(f[3:])]
    nd_lim = [f for f in S.log if f[2] == 'limitfix' and 'nd_check' in ' '.join(f[3:])]
    L.add('sweep.nd.removed', len(nd_drop), 'not-detected values the 26 October check removed (drop_bound lines naming '
          'work/nd_check/)', kind='snapshot', window='log.tsv, 2026-10-26', source=src,
          forms=['and removed 59', 'removed 59 values'])
    L.add('sweep.nd.limits_cleared', len(nd_lim), 'limits it cleared that bounded another quantity (limitfix lines '
          'naming work/nd_check/)', kind='snapshot', window='log.tsv, 2026-10-26', source=src,
          forms=['cleared 38 limits'])
    for k, d in (('reprint', '2026-10-16'), ('scale', '2026-10-20'), ('vmax', '2026-10-23'), ('nd', '2026-10-26')):
        pass
    L.add('sweep.days', '16, 20, 23 and 26 October', 'the days the reprint, unit-factor, maximal-rate and not-detected '
          'sweeps ran (their log.tsv lines)', kind='snapshot', source=src, show='16, 20, 23 and 26 October',
          forms=['(16, 20, 23 and 26 October)'])


def sec_exposure():
    rows = S.tsv('human_review/exposed.tsv')
    rule = git('show', '-s', '--format=%ad', '--date=format:%Y-%m-%d %H:%M', 'bc442f7').strip()
    before = [r for r in rows if r['time'] < rule]
    src = 'human_review/exposed.tsv (the transcript scan, human_review.blind_check)'
    L.add('exposure.lines', len(rows), 'exposure-log lines: a reader, verifier or completeness check whose tool call '
          'named a database file, the earlier catalogue or review data before the paper\'s first add',
          kind='snapshot', source=src, forms=['472 lines for 308 papers', 'held 472 lines for 308 papers'])
    L.add('exposure.papers', len({r['pmid'] for r in rows}), 'papers in the exposure log', kind='snapshot', source=src,
          forms=['for {308} papers by 31 October', 'lines for {308} papers on 31'])
    L.add('exposure.lines_before_rule', len(before), f'exposure lines before the blind-reading rule (git bc442f7, '
          f'{rule}); the first is dated {min(r["time"] for r in rows)}', kind='snapshot', source=src + '; git bc442f7',
          forms=['450 of them from 9 to 12 October', '450 of them from 9-12'])


def sec_git():
    head = 'HEAD'
    n_read = int(git('rev-list', '--count', head, '--', 'prompts/read.md').strip())
    n_ver = int(git('rev-list', '--count', head, '--', 'prompts/verify.md').strip())
    src = f'git rev-list --count {S.head[:7]} -- prompts/<file>'
    L.add('prompts.read_commits', n_read, 'commits that changed prompts/read.md', kind='snapshot', source=src,
          forms=['changed in 31 and 33 commits'])
    L.add('prompts.verify_commits', n_ver, 'commits that changed prompts/verify.md', kind='snapshot', source=src,
          forms=['in 31 and {33} commits'])
    for f, key, forms in (('prompts/read.md', 'prompts.read_lines', ['221 lines']),
                          ('prompts/verify.md', 'prompts.verify_lines', ['146 lines']),
                          ('catlog.py', 'code.catlog_lines', ['4,407 lines at HEAD'])):
        n = git('show', f'{head}:{f}').count('\n')
        L.add(key, n, f'lines of {f} at HEAD {S.head[:7]}', kind='snapshot', source=f'git show {S.head[:7]}:{f}',
              forms=forms)


# ===================================================================================================== 8. worked example and case papers
def sec_example():
    e = S.example
    src = 'catalog.jsonl (PMID 21757926); sources/db_values.tsv; texts/21757926.txt'
    if not e:
        return
    k, km, kcm = float(e['kcat']['value']), float(e['Km']['value']), float(e['kcm']['value'])
    db = [d for d in S.dbvals if d['pmid'] == '21757926' and d['metric'] == 'kcat/Km' and d['value'] == '681.5']
    dbk = {d['source'] for d in S.dbvals if d['pmid'] == '21757926' and d['metric'] == 'kcat' and d['value'] == '7.5'}
    dbm = {d['source'] for d in S.dbvals if d['pmid'] == '21757926' and d['metric'] == 'Km' and d['value'] == '1.25'}
    txt = S.evidence('texts/21757926.txt')
    L.add('example.printed', e['kcm']['raw_value'], 'the worked example\'s stored printed cell (Fig. 1b): kcat/Km of '
          'EstF27 with methyl rho-coumarate, Table 1', kind='snapshot', source=src, show=e['kcm']['raw_value'],
          forms=['a kcat/Km of 6 ± 1.5', 'copied 6 ± 1.5', "reading of 6 ± 1.5"])
    L.add('example.text_layer', '681.5', 'the text layer\'s reading of that cell (± drawn as 8)', kind='snapshot',
          source='texts/21757926.txt', show='681.5' if '681.5' in txt else 'NOT IN TEXT',
          forms=['the cell reads 681.5', 'BRENDA and OED list 681.5', 'judged from the page image that 681.5'])
    L.add('example.glyph_as', "'8'", 'the glyph the text layer draws for ±', kind='snapshot', source='texts/21757926.txt',
          show="'8'", forms=["each ± of the row as '{8}'", "not as '{8}'"])
    L.add('example.kcat', k, 'the record\'s stored kcat (s^-1)', kind='snapshot', source=src, show=fmt(k, 1),
          forms=["7.5 ÷ 1.25 = 6.0"])
    L.add('example.km', km, 'the record\'s stored Km (mM)', kind='snapshot', source=src, show=fmt(km, 2),
          forms=['7.5 ÷ {1.25} = 6.0'])
    L.add('example.kcat_over_km', round(k / km, 1), 'kcat ÷ Km of the record', kind='snapshot', source=src,
          show=fmt(round(k / km, 1), 1), forms=['7.5 ÷ 1.25 = {6.0}'])
    L.add('example.times_catlog', round(681.5 / kcm, 1), 'the databases\' 681.5 over the stored 6', kind='snapshot',
          source=src, show=fmt(round(681.5 / kcm, 1), 1), forms=['681.5, {113.6}-fold off'])
    L.add('example.db_lists', ', '.join(sorted(d['source'] for d in db)), 'databases listing 681.5 for this paper; '
          f'kcat 7.5 in {", ".join(sorted(dbk))}; Km 1.25 in {", ".join(sorted(dbm))}', kind='snapshot',
          source='sources/db_values.tsv', show=' and '.join(sorted(d['source'] for d in db)),
          forms=['kcat and Km of {7.5} and 1.25', 'kcat and Km of 7.5 and {1.25}'])
    o = e['others']
    L.add('example.other_kcm_range', [o[0], o[-1]], 'range of the table\'s other stored kcat/Km cells (Table 1)',
          kind='snapshot', source=src, show=f'{fmt(o[0], 1)} to {o[-1]:,.1f}', forms=['(23.1 to 1,285.9)'])
    fe = S.evidence('tools/fetch.py')
    L.add('example.glyph_signs', "± as '6'", 'the ± glyph form the text-layer detector knows (tools/fetch.py '
          'GLYPH_SIGNS)', kind='code', source='tools/fetch.py GLYPH_SIGNS',
          show="'6'" if "\\u00b1 as '6'" in fe or "± as '6'" in fe else 'NOT FOUND',
          forms=["knows ± drawn as '6'"])
    mo = json.loads(S.evidence('paper/figures/method_overview/method_overview_v2_numbers.json'))['worked_example']
    L.add('example.page_image_dpi', 300, 'resolution of the page image the verifier confirmed the cell on '
          '(work/21757926.verify.json, as the figure build asserts it)', kind='frozen',
          source='paper/figures/method_overview/method_overview_v2_numbers.json worked_example.verify_quote',
          show='300' if '300-dpi' in mo['verify_quote'] else 'NOT FOUND', forms=['on a 300-dpi page image'])


def sec_cases():
    """The case papers named in the Results and Box 1: what the snapshot holds for each, and the printed facts
    (frozen in the checked boxes)."""
    cat = collections.defaultdict(list)
    for r in S.cat:
        cat[str(r['pmid'])].append(r)
    db = collections.defaultdict(list)
    for d in S.dbvals:
        db[d['pmid']].append(d)
    src = 'catalog.jsonl; sources/db_values.tsv'
    L.add('case.9637365.catlog_values', len(cat['9637365']), 'stored values of PMID 9637365 (Box 1c of 1 November, draft_v1.md: only the '
          'stejnefibrases\' own values)', kind='snapshot', source=src,
          forms=["the paper's 18 new values", 'only the 18 stejnefibrase values'])
    sab = [d for d in db['9637365'] if d['source'] == 'SABIO-RK']
    L.add('case.9637365.sabio_values', len(sab), 'SABIO-RK values listed for PMID 9637365 (its 27 reprinted numbers '
          'plus the stejnefibrases\' own)', kind='snapshot', source='sources/db_values.tsv',
          note='Box 1c: SABIO-RK lists all 27 reprinted numbers, in nine records, beside six stejnefibrase records')
    rows = cat['16484232']
    k232 = [r for r in rows if r['metric'] == 'kcat/Km' and float(r['value']) in (232.0, 97.0)]
    kk = sorted({(r['metric'], float(r['value'])) for r in rows if r['metric'] in ('kcat', 'Km')
                 and float(r['value']) in (250.0, 32.0, 0.02, 0.03)})
    L.add('case.16484232.stored_232_or_97', len(k232), 'stored kcat/Km values of PMID 16484232 equal to 232 or 97 '
          '(Box 1b of 1 November, draft_v1.md: CatLog stores these rows\' kcat and Km, not 232 or 97)', kind='snapshot', source=src,
          note='stored: ' + ', '.join(f'{m} {v:g}' for m, v in kk))
    lists = sorted({d['source'] for d in db['16484232'] if d['metric'] == 'kcat/Km' and d['value'] in ('232', '97')})
    L.add('case.16484232.db_list_232_97', ', '.join(lists), 'databases that list 232 and 97 as kcat/Km for PMID '
          '16484232', kind='snapshot', source='sources/db_values.tsv', show=', '.join(lists))
    gssg = [r for r in cat['2007114'] if r['metric'] == 'kcat/Km' and 'GSSG' in (r.get('substrate') or '').upper()
            and (r.get('variant') or '').lower() == 'wild type']
    L.add('case.2007114.stored_wt_gssg_kcat_over_km', len(gssg), 'stored wild-type kcat/Km values of PMID 2007114 with '
          'GSSG (Box 1a of 1 November, draft_v1.md: CatLog holds nothing here)', kind='snapshot', source=src)
    L.add('case.2007114.databases', ', '.join(sorted({d['source'] for d in db['2007114']})) or 'none',
          'databases listing any value for PMID 2007114 (Box 1a of 1 November, draft_v1.md: no other database than SABIO-RK)', kind='snapshot',
          source='sources/db_values.tsv', show=', '.join(sorted({d['source'] for d in db['2007114']})) or 'none')
    flagged = sum(1 for p, f, s in S.ceil_list if p == '36756200' and f)
    L.add('case.36756200.ceiling_records', flagged, 'records of PMID 36756200 whose kcat/Km is at or above the diffusion '
          'ceiling, flagged', kind='snapshot', source='catlog_wide.jsonl', forms=['flags the ten records'])
    rj = [r for r in S.rej if str(r.get('pmid')) == '25799411' and 'corrigend' in ' '.join(r.get('why') or []).lower()]
    L.add('case.25799411.rejected_by_corrigendum', len({r['row_id'] for r in rj}), 'values of PMID 25799411 its verifier '
          'rejected because a 2017 corrigendum replaces them', kind='snapshot', source='rejected.jsonl',
          forms=['rejected the six'])
    # the printed facts and database statements of the boxes and the six-case paragraph (checked by two refuting agents
    # each and claim-checked: paper/05_agent_case_boxes.md, paper/evidence/agent_highlights_20261028/boxes/)
    bx = S.evidence('paper/manuscript/boxes.md')
    fb = S.evidence('paper/05_agent_case_boxes.md')
    facts = [
        ('box.a.wt_tsst', '505 000 000', 'Box 1a: wild-type kcat/Km with trypanothione (min^-1 M^-1), Table III',
         ['505 000 000']),
        ('box.a.gssg_cell', '0.84', 'Box 1a: the plain 0.84 with GSSG', ['plain 0.84 with GSSG', 'a plain 0.84 that',
                                                                           'skipped the 0.84', 'tied 0.84',
                                                                           'kcat/Km of 0.84', 'fits 0.84',
                                                                           'believing 0.84', '(= 0.84 min', 'plain 0.84 kcat/Km']),
        ('box.a.mutants_le1', '≤1', 'Box 1a: five mutants print ≤1', ['five mutants with no detectable', 'print ≤1']),
        ('box.a.upper_limit', '0.8 (p. 2765)', 'Box 1a: the Results\' "upper limit on kcat/Km of 0.8 M⁻¹ min⁻¹" (p. 2765)',
         ['kcat/Km of 0.8 M⁻¹', 'and 0.8. CatLog', '(p. 2765)']),
        ('box.a.ratio', '6 × 10⁸', 'Box 1a: the (6 × 10⁸)-fold TSST/GSSG ratio', ['(6 × 10⁸)-fold']),
        ('box.a.sabio', '1.4 × 10⁻⁵ (ID 56208)', 'Box 1a: SABIO-RK\'s measured 1.4 × 10⁻⁵ mM⁻¹ s⁻¹ (ID 56208)',
         ['1.4 × 10⁻⁵ mM⁻¹ s⁻¹', 'ID 56208']),
        ('box.b.cells', 'Table 2 (p. 11360): 250 ± 10; 20 ± 2; 32 ± 2; 30 ± 0.5; 54, 11; 232, 97', 'Box 1b: Table 2 (p. 11360) cells',
         ['250 ± 10', '20 ± 2 µM', '32 ± 2 and 30 ± 0.5', '54 and 11', '232 and 97.', 'Table 2 (p. 11360)']),
        ('box.b.nine_two', 'nine cells fit, two do not', 'Box 1b: of the reader\'s 11 kcat ÷ Km checks', ['nine cells fit']),
        ('box.b.discussion', '230-fold (p. 11364)', 'Box 1b and Results: the paper\'s Discussion (p. 11364)',
         ['"230-fold"', '230-fold more proficient', '(p. 11364)']),
        ('box.b.arith', '250/0.020 = 12,500; 12,500/54 = 231.5; 32/0.030 = 1,067; 1,067/11 = 97.0; kcat 250, 32; Km 0.02, 0.03; 232, 97', 'Box 1b and Results: the arithmetic that ties 232 and 97 '
         'to efficiency ratios', ['12,500 ÷ 54', '= 231.5, printed 232', '250 s⁻¹/0.020 mM = 12,500 mM⁻¹ s⁻¹',
                                  '12,500/54 (Succ-ox) = 231.5', '32/0.030 = 1,067', '1,067/11 = 97.0',
                                  'kcat 250 and 32 s⁻¹', 'Km 0.02 and 0.03 mM', '12,500 or 1,067',
                                  'list 232 (wild type) and 97', 'not 232 or 97', 'It tied 232']),
        ('box.c.numbers', '27 numbers, 9 dashes, 18 values, nine records, four trypsin, six stejnefibrase',
         'Box 1c: Table 3 of 9604287 prints the same 27 numbers and 9 not-detected dashes; SABIO-RK nine records (four '
         'trypsin) beside six stejnefibrase records', ['same 27 numbers and 9', 'all 27 reprinted numbers',
                                                      'in nine records', 'the four trypsin records',
                                                      'six stejnefibrase records', "table's 27 comparison numbers",
                                                      'lists all 27 as', 'the mean of three determinations']),
        ('box.cases.corrigendum', 'six values, five still listed', 'Results: 25799411\'s 2017 corrigendum replaces six '
         'C. glutamicum pyruvate values, five of which BRENDA and OED still list', ['five of which BRENDA']),
        ('box.cases.36756200', '×10⁵ s⁻¹; 15 s; 22 values; 20 restored', 'Results: 36756200\'s Table S4/S5 header, '
         'absorbance every 15 s, 22 values rejected, 20 restored', ['header of ×10⁵ s⁻¹', 'every 15 s',
                                                                    'rejected all 22 values']),
        ('box.cases.19686854', 'eight values', 'Results: 19686854\'s eight mutant values that SABIO-RK lists as wild type',
         ['their eight values']),
        ('box.quote.match', '1%', 'Box 1 note: database statements matched by code within 1%', ['within 1%. Readers']),
    ]
    for key, val, what, forms in facts:
        L.add(key, val, what, kind='fact', source='paper/manuscript/boxes.md; paper/05_agent_case_boxes.md; '
              'paper/evidence/agent_highlights_20261028/boxes/', show=val, forms=forms, state='ON FILE')
    # Box 1 since 6 November 2026 (boxes.md) and Supplementary Note 2 section 2: every number a box or a case sentence
    # prints is in that case's checked box (page 05 = boxes/plain/<PMID>.md) or in its paper (texts/<PMID>.txt); the keys
    # below carry those numbers, so check_numbers.py ties them to the checked sources.
    pl = 'paper/evidence/agent_highlights_20261028/boxes/plain/'

    def sources(pm):
        out = S.evidence(pl + pm + '.md') if os.path.exists(os.path.join(ROOT, pl + pm + '.md')) else ''
        for f in (f'texts/{pm}.txt', f'texts/{pm}.supp.txt'):
            if os.path.exists(os.path.join(ROOT, f)):
                out += '\n' + open(os.path.join(ROOT, f), encoding='utf-8', errors='replace').read()
        return out

    def prose(t):  # as printed: no comments, code spans or 'Source:' lines (assemble.py drops them), no PMIDs
        t = re.sub(r'^Source: .*?(?=\n\n|\n---|\Z)', ' ', t, flags=re.S | re.M)
        t = re.sub(r'`[^`]*`', ' ', re.sub(r'<!--.*?-->', ' ', t, flags=re.S))
        return re.sub(r'(?<![\d.,])\d{6,9}(?!\d|[.,]\d)', ' ', t)
    part = bx[bx.index('### Box 1 |'):bx.index('## The other cases')]
    for box in re.split(r'(?m)^(?=### Box \d \|)', part)[1:]:
        pm = re.search(r'^PMID (\d+)', box, re.M).group(1)
        src_text = sources(pm)
        toks = list(dict.fromkeys(TOK.findall(prose(box))))
        miss = [x for x in toks if x not in src_text and x != pm]
        if miss:
            ERRORS.append(f'boxes.md, box of {pm}: numbers in neither its checked box nor its paper: {miss}')
        L.add(f'box.{pm}.numbers', '; '.join(toks), f'the numbers boxes.md prints in the box of PMID {pm}, each found in '
              'its checked box or its paper', kind='fact', source=f'paper/manuscript/boxes.md; {pl}{pm}.md; texts/{pm}.txt',
              show='; '.join(toks), forms=[], state='ON FILE', note=('not found: ' + ', '.join(miss)) if miss else None)
    sn2 = S.evidence('paper/manuscript/supp_note_2_results.md')
    sec2 = sn2[sn2.index('## 2. '):sn2.index('## 3. ')]
    pms = list(dict.fromkeys(re.findall(r'plain/(\d+)\.md', sec2)))
    src_text = '\n'.join(sources(pm) for pm in pms)
    toks = list(dict.fromkeys(x for x in TOK.findall(prose(sec2)) if x not in pms))
    miss = [x for x in toks if x not in src_text]
    if miss:
        ERRORS.append(f'Supplementary Note 2 section 2: numbers in none of its cases\' checked boxes or papers: {miss}')
    L.add('sn2.cases.numbers', '; '.join(toks), 'the numbers Supplementary Note 2 section 2 prints for the boxed cases '
          'not in Box 1, each found in one of their checked boxes or papers', kind='fact',
          source='paper/manuscript/supp_note_2_results.md; ' + ', '.join(f'{pl}{pm}.md' for pm in pms), show='; '.join(toks),
          forms=[], state='ON FILE', note=('not found: ' + ', '.join(miss)) if miss else None)
    p2 = 'paper/02_catlog_vs_databases.md'
    E('db.example.betalactamase', "7 ± 1 under '10⁻⁶ × kcat/Km (M⁻¹ s⁻¹)' = 7 × 10⁶ M⁻¹ s⁻¹; kcat 300 s⁻¹, Km 42 µM; "
      'SABIO-RK 10¹² lower', 'page 02 example 2 (PMID 3264155), refuted from the paper (evidence/databases_vs_papers/)',
      p2, needle='3264155', kind='fact', state='ON FILE', show='7 ± 1; 7 × 10⁶; 300; 42; 10¹²',
      forms=['prints 7 ± 1 under', 'which is 7 × 10⁶ M⁻¹ s⁻¹', 'its kcat of 300 s⁻¹', 'its Km of 42 µM',
             'lists a value 10¹² lower'])
    E('db.example.fucosyltransferase', "Km 0.38 under 'Km (µM)'; Methods fit over 0.1-10 mM; CatLog 0.38 mM",
      "page 02's example that did not hold (PMID 10814703): UniProt copied the paper's misprint", p2, needle='10814703',
      kind='fact', state='ON FILE', show='0.38; 0.1-10 mM',
      forms=['prints a Km of 0.38 under', 'over 0.1-10 mM acceptor', 'where 0.38 µM could not', 'CatLog stores 0.38 mM'])
    E('db.fig4.oed_lines', '4.5 s⁻¹ vs 36; 5 s⁻¹ vs 28', "the two OED lines off the unit factors: OED's kcat against "
      "CatLog's", 'paper/figures/database_errors/README.md', needle='the 17 OED numbers 4.5 s⁻¹ are paired with CatLog',
      kind='fact', state='ON FILE', show='4.5 vs 36; 5 vs 28',
      forms=['a kcat of 4.5 s⁻¹', 'papers print 36', 'and 5 s⁻¹ where', 'papers print 28'],
      check=f"OED 4.5 vs CatLog 36 in {S.fig4_now['oed_45_36'][1]} papers, 5 vs 28 in {S.fig4_now['oed_5_28'][1]} "
            '(recomputed: db.fig4.oed_*)')


# ===================================================================================================== 9. re-derived one-pass numbers
def sec_rederive():
    d = P('paper', 'evidence', 'rederive_20261101')
    sys.path.insert(0, d)
    import rd_lib
    saved = {}
    rd_lib.save = lambda key, obj: saved.__setitem__(key, obj)        # results.json there stays as it is
    import rd_L13_multiplier as r13
    import rd_L32_closure as r32
    import rd_L46_brenda as r46
    import rd_C56_origin as r56
    for m in (r13, r32, r46, r56):
        S.evidence(os.path.relpath(m.__file__, ROOT))
    S.evidence('paper/evidence/rederive_20261101/rd_lib.py')
    src = 'paper/evidence/rederive_20261101/{rd_L13_multiplier,rd_L32_closure,rd_L46_brenda,rd_C56_origin}.py run on the snapshot'
    rows, papers, any_p, caret_p, hdr_p, ovr_p, forms, set_aside = r13.run(None)
    N = len(papers)
    L.add('rederive.L13.papers_with_multiplier', len(any_p), 'papers whose printed kcat, Km or kcat/Km unit carries a '
          'power-of-ten multiplier (x10^n header), rd_L13_multiplier.py', kind='snapshot', source=src,
          note=f'of {N:,} papers ({pct(len(any_p), N, 2)}%, Wilson {wilson(len(any_p), N)}); outline L13 one-pass '
               '532 of 6,622 (8.0%) on 23 October; not in draft_v1')
    L.add('rederive.L13.share', pct(len(any_p), N, 2), 'rederive.L13.papers_with_multiplier as a share of papers with '
          'values', kind='snapshot', source=src, show=pshow(len(any_p), N))
    res, flagged = r32.run(None)
    A, B = res['variant_A'], res['variant_B']
    L.add('rederive.L32.triples', res['same_row_triples'], 'same-row printed triples (kcat, Km and printed kcat/Km '
          'quoted from one printed line, converted from the printed units)', kind='snapshot', source=src,
          note=f"{res['papers_with_a_same_row_triple']:,} papers; outline L32 one-pass 46,331 in 3,838 (23 October)")
    L.add('rederive.L32.papers', res['papers_with_a_same_row_triple'], 'papers with a same-row triple', kind='snapshot',
          source=src)
    L.add('rederive.L32.triples_gross_share', [B['pct_triples_gross'], A['pct_triples_gross']], 'triples whose printed '
          'kcat/Km misses kcat ÷ Km grossly (an exact unit factor, a power of ten or 2-fold or more), variant B (the coded '
          'rule without its regex bug) to variant A (the rule as stated)', kind='snapshot', source=src,
          show=f"{B['pct_triples_gross']}-{A['pct_triples_gross']}%",
          note=f"A {A['triples_gross']:,}, B {B['triples_gross']:,} triples; one-pass 1.28% carries the regex bug")
    L.add('rederive.L32.papers_failing_share', [B['pct_papers_flagged'], A['pct_papers_flagged']], 'papers with at '
          'least one grossly failing triple, variant B to A', kind='snapshot', source=src,
          show=f"{B['pct_papers_flagged']}-{A['pct_papers_flagged']}%",
          note=f"A {A['papers_flagged']} (Wilson {A['wilson_papers']}), B {B['papers_flagged']} (Wilson {B['wilson_papers']}); "
               'one-pass 5.68% (4.98-6.44) carries the bug')
    sc = r32.summarize_scale(r32.scale_verdicts(), {r[0] for r in flagged},
                             {x['pmid'] for x in rd_lib.catalog(None) if x.get('unit_for_conversion')})
    L.add('rederive.L32.scale_decided', sc['decided_after_second_look'], 'papers with a work/scale_<PMID>.json verdict '
          'whose misprinted column was decided from the paper after the second looks', kind='snapshot',
          source=src + '; work/scale_*.json', note=f"of {sc['papers']} papers (one-pass 43 of 46 read the first look only)")
    L.add('rederive.L32.scale_papers', sc['papers'], 'papers with a scale verdict on file', kind='snapshot',
          source=src + '; work/scale_*.json')
    cur, w = r46.paper_checked(None)
    ex = r46.export_side(w)
    den = cur['papers_brenda_lists_any_value_for']
    L.add('rederive.L46.brenda_copied_share', ex['share_copied_misprint_of_all_wrong']['pct'], "share of BRENDA's wrong "
          "values (paper-checked plus code-found) that copy the paper's own misprint", kind='snapshot', source=src,
          show=f"{ex['share_copied_misprint_of_all_wrong']['pct']}%",
          note=f"{ex['share_copied_misprint_of_all_wrong']['k']} of {ex['share_copied_misprint_of_all_wrong']['n']}; "
               f"paper-checked only {cur['share_copied_misprint_of_paper_checked']['pct']}% "
               f"({cur['share_copied_misprint_of_paper_checked']['k']} of {cur['share_copied_misprint_of_paper_checked']['n']})")
    L.add('rederive.L46.brenda_papers_misstated_share', den['pct'], 'papers CatLog holds that BRENDA lists values for, '
          'in which a paper check found at least one BRENDA value wrong', kind='snapshot', source=src,
          show=f"{den['pct']}%", note=f"{den['with_wrong']} of {den['n']} (Wilson {den['wilson']})")
    idx = r56.db_values_index()
    try:
        pdb = r56.per_database(None, idx)
        S.c56 = pdb
        L.add('rederive.C56.per_database', 'see note', "copied-misprint share of each database's paper-checked wrong "
              'values (rd_C56_origin.per_database on the snapshot)', kind='snapshot', source=src,
              note=json.dumps({k: v for k, v in pdb.items() if not isinstance(v, (list, dict)) or len(json.dumps(v)) < 400},
                              ensure_ascii=False)[:900])
    except Exception as exc:                                     # report, do not stop the ledger
        ERRORS.append(f'rd_C56_origin.per_database failed on the snapshot: {exc!r}')
    fr = json.loads(S.evidence('paper/evidence/rederive_20261101/results.json'))
    L.add('rederive.frozen_23oct', 'see note', 'the re-derivation\'s own values at 23 October (git e577b41), as its '
          'results.json holds them', kind='frozen', source='paper/evidence/rederive_20261101/results.json',
          note=f"L13 {fr['L13']['snapshot_2026-10-23_e577b41']['any']}; L32 A "
               f"{fr['L32']['snapshot_2026-10-23_e577b41']['variant_A']['pct_papers_flagged']}% B "
               f"{fr['L32']['snapshot_2026-10-23_e577b41']['variant_B']['pct_papers_flagged']}% of papers")


# ===================================================================================================== 10. evidence helpers
def E(key, value, what, src, *, needle=None, show=None, forms=(), state='DEV', window=None, kind='frozen', note=None,
      base=None, check=None):
    """A number read from an evidence file: `needle` (a string, or a list of strings) must occur in it."""
    t = S.evidence(src)
    for nd in ([needle] if isinstance(needle, str) else needle or []):
        must(t, nd, src)
    L.add(key, value, what, kind=kind, source=src, window=window or 'as frozen in the source', state=state,
          show=show, forms=forms, note=note, base=base, check=check)


def EJ(key, src, path, what, *, scale=None, nd=None, show=None, forms=(), state='DEV', window=None, note=None,
       base=None, kind='frozen', check=None):
    """A number read from a JSON evidence file by its path."""
    v = jpath(json.loads(S.evidence(src)), path)
    if scale:
        v = v * scale
    if nd is not None:
        v = round(v, nd)
    L.add(key, v, what, kind=kind, source=src + ' :: ' + '.'.join(str(p) for p in path),
          window=window or 'as frozen in the source', state=state, show=show, forms=forms, note=note, base=base,
          check=check)
    return v


# ===================================================================================================== 11. error ledger and Fig. 3
def sec_ledger():
    src = 'paper/figures/layers_ledger/evidence/rethink_20261022/error_ledger.tsv'
    rows = list(csv.DictReader(io.StringIO(S.evidence(src)), delimiter='\t'))
    w = 'failures found 2026-10-07 to 2026-10-21 (ledger built 2026-10-22 02:39)'
    kinds = collections.Counter(r['kind'] for r in rows)
    open_ = [i + 1 for i, r in enumerate(rows) if 'OPEN' in r['rule']]

    def bucket(f):                                    # r03_error_ledger.py's tally buckets, grouped as the Methods name them
        f = f.lower()
        return ('audit' if 'audit' in f and 'review of' not in f else
                'code review' if 'external' in f or 'code review' in f else
                'human review' if 'human' in f or 'website review' in f else
                'code rejects / regression check' if 'code' in f or 'recheck' in f else
                'sweep' if 'sweep' in f else
                'other' if any(x in f for x in ('dbcheck', 'transcript', 'verifier', 'investigation')) else
                'operator\'s own checks and reviews')
    fb = collections.Counter(bucket(r['found_by']) for r in rows)
    L.add('ledger.failures', len(rows), 'lines of the error ledger: failures found from 7 to 21 October, each with its '
          'kind, how it was found, what failed and the rule it became', kind='frozen', window=w, source=src,
          state='DEV', forms=['recorded 50 failures', 'regression check found 15 of the {50}',
                              '46 of the {50} failures', 'error ledger (50 lines', 'lists 50 failures'])
    L.add('ledger.false_accepts', kinds['FA'], 'ledger lines of kind FA: a wrong value or label reached, or could '
          'reach, the catalogue', kind='frozen', window=w, source=src, state='DEV', forms=['29 were false accepts'])
    L.add('ledger.false_rejects', kinds['FR'], 'ledger lines of kind FR: a rule rejected right values', kind='frozen',
          window=w, source=src, state='DEV', forms=['14 false rejects'])
    L.add('ledger.process', kinds['PROC'], 'ledger lines of kind PROC: process failures', kind='frozen', window=w,
          source=src, state='DEV', forms=['and 7 process failures [n50]'])
    L.add('ledger.open_21oct', len(open_), 'ledger lines with no rule by 21 October (rule column OPEN)', kind='frozen',
          window=w, source=src, state='DEV', note='rows ' + ', '.join(map(str, open_)))
    L.add('ledger.with_rule_21oct', len(rows) - len(open_), 'ledger lines that had a rule in code, a prompt or the '
          'workflow by 21 October', kind='frozen', window=w, base='ledger.failures', source=src, state='DEV',
          forms=['46 of the 50 failures in the error ledger had become rules'])
    for name, forms in (('code rejects / regression check', ['Code rejects and the regression check found 15 of the 50',
                                                             'Code rejects or the regression check found 15']),
                        ("operator's own checks and reviews", ["checks and reviews 14"]),
                        ('audit', ['reviews 14, audits {7}']),
                        ('code review', ['code review 4']), ('human review', ['human review 3']),
                        ('sweep', ['sweeps 3']), ('other', ['other routes 4'])):
        L.add('ledger.found_by.' + {'code rejects / regression check': 'code_rejects', "operator's own checks and reviews":
                                     'operator', 'audit': 'audits', 'code review': 'code_review',
                                     'human review': 'human_review', 'sweep': 'sweeps', 'other': 'other'}[name], fb[name], f'ledger lines found by {name} '
              '(r03_error_ledger.py\'s keyword buckets of found_by)', kind='frozen', window=w, source=src, state='DEV',
              forms=forms)
    t = S.evidence('paper/manuscript/supp_note_1_system.md')
    # the reconciliation of 1 November appended the classes (46 classes (25, 14, 7), 42) to this cell (reconcile_log.md
    # row 66); 3 and 514, the two numbers read from it below, are unchanged (verify_round2.md)
    for nd in ('| n50 | 50; 29; 14; 7; 15; 14; 7; 4; 3; 3; 3; 4; 44; 4 open; 1; 3; 514; 46 classes (25, 14, 7), 42 |',):
        must(t, nd, 'supp_note_1_system.md')
    L.add('ledger.still_open_31oct', 3, 'of the 4 open lines, those still open on 31 October (the derived kcat/Km of '
          'row 50 is flagged since: catlog.py export)', kind='frozen', source='paper/manuscript/supp_note_1_system.md '
          '[n50]', state='DEV', forms=['three of them still open=>3'])
    L.add('ledger.commits', 514, 'commits the ledger was compiled from by hand', kind='frozen',
          source='paper/manuscript/supp_note_1_system.md [n50]', state='DEV', forms=['(514 commits)'])
    lj = 'paper/figures/layers_ledger/layers_ledger_numbers.json'
    EJ('ledger.classes', lj, ['panel_b', 'classes'], 'failure classes after merging a class found again into its '
       'first line (rows 38, 47 into 23; 39, 42 into 21)', forms=['leaves 46 classes', 'the 46 had a rule'])
    EJ('ledger.classes_FA', lj, ['panel_b', 'kinds', 'FA'], 'classes of kind FA (let an error through)',
       forms=['Of these, 25 let an error through'])
    EJ('ledger.classes_FR', lj, ['panel_b', 'kinds', 'FR'], 'classes of kind FR', forms=['Another 14 were rules'])
    EJ('ledger.classes_PROC', lj, ['panel_b', 'kinds', 'PROC'], 'classes of kind PROC', forms=['and 7 were process failures'])
    nb = json.loads(S.evidence(lj))['panel_b']
    L.add('ledger.classes_with_rule', nb['classes'] - len(nb['open_ledger_rows']), 'classes with a rule by 21 October '
          '(classes less the 4 open)', kind='frozen', source=lj, state='DEV', forms=['42 of the 46 had a rule'])
    EJ('ledger.rule_same_day', lj, ['panel_b', 'rule_timing (merged classes)', 'commit the same day'],
       'classes whose rule cites a commit made the day the failure was found', forms=['and 39 cite a commit'])
    lab = {x['ledger_row']: x for x in nb['labelled']}
    for row, key, forms_m, forms_v in ((29, 'partial', ['a rule 57 minutes after'], ['removed 101 values from 2']),
                                       (37, 'reprint', ['a rule 11 minutes after'], []),
                                       (23, 'header', ['a prompt rule 2 minutes after'],
                                        ['{Eighty-one} values in 8'])):
        x = lab[row]
        L.add(f'ledger.labelled.{key}.minutes_to_rule', x['minutes_find_to_rule'], f'minutes from the audit that found '
              f'"{x["label"]}" (ledger row {row}, {x["found"]}) to its rule\'s commit ({x["rule_commit"]})',
              kind='frozen', source=lj, state='DEV', forms=forms_m)
        L.add(f'ledger.labelled.{key}.values_later', x['values_later'], f'values later checks removed or corrected in '
              f'that class ({", ".join(x["sources_later"])}), in {x["papers_later"]} papers', kind='frozen', source=lj,
              state='DEV', forms=forms_v, note=json.dumps(x['read']))
    L.add('ledger.labelled.partial.papers', lab[29]['papers_later'], 'papers of those partial-constant values',
          kind='frozen', source=lj, state='DEV', forms=['101 values from {2}'])
    L.add('ledger.labelled.header.papers', lab[23]['papers_later'], 'papers of those unit fixes', kind='frozen',
          source=lj, state='DEV', forms=['values in {8} papers'])


def sec_layers():
    lj = 'paper/figures/layers_ledger/layers_ledger_numbers.json'
    pa = json.loads(S.evidence(lj))['panel_a']
    dr = pa['drawn']
    must(json.dumps(pa['bases']), '205,517', lj)
    w = 'values read 2026-10-07 to 2026-10-21; pilot snapshot 2026-10-22'
    EJ('dev.verifier.serious_per_1000', lj, ['panel_a', 'drawn', 'verifier', 'per_1000'], 'serious errors the verifier '
       'caught that the code checks of 22 October would have let through, per 1,000 values the reader wrote (base '
       '205,517 values in 6,205 papers): a wrong number, variant, organism, substrate, pH or temperature, or not the '
       "paper's own kcat or Km", nd=1, window=w, forms=['the verifier caught 9.1 serious', 'have passed 9.1 serious'])
    EJ('dev.verifier.serious_values', lj, ['panel_a', 'drawn', 'verifier', 'values'], 'those values', window=w,
       forms=['(1,870 values in 217 papers'], check=json.loads(S.evidence(
           'paper/figures/layers_ledger/evidence/rethink_20261022/pilot_layers/check/k_budget.json'))['verifier_strict_rows'])
    EJ('dev.verifier.serious_papers', lj, ['panel_a', 'drawn', 'verifier', 'papers'], 'their papers', window=w,
       forms=['1,870 values in {217} papers'])
    v = dr['verifier, number off by a unit factor']['values']
    EJ('dev.verifier.unit_factor_values', lj, ['panel_a', 'drawn', 'verifier, number off by a unit factor', 'values'],
       'of those, numbers off by a unit factor', window=w, forms=['(1,215 values)'],
       note=f'{pct(v, dr["verifier"]["values"])}% of the 1,870 ("two thirds")')
    EJ('dev.verifier.reprint_values', lj, ['panel_a', 'verifier_kinds (Source Data; the art names only unit)', 'reprint',
                                           'values'], 'of those, reprinted values', window=w,
       forms=['129 of the {252} reprinted'])
    EJ('dev.verifier.reprint_top_paper', lj, ['panel_a', 'verifier_kinds (Source Data; the art names only unit)',
                                              'reprint', 'top_paper_values'], 'reprinted values the verifier caught in '
       'its top paper (20635860)', window=w, forms=['one paper holds 129'])
    EJ('dev.code.per_1000', lj, ['panel_a', 'drawn', 'code checks', 'per_1000'], 'serious errors the code checks of today '
       'caught after the verifier, per 1,000 reader values (31 implausible values, 21 conflicts)', nd=2, window=w,
       forms=['caught 0.25 more per 1,000'])
    EJ('dev.code.values', lj, ['panel_a', 'drawn', 'code checks', 'values'], 'those values', window=w,
       forms=['(52 values)'])
    below = ['reprints', 'partial-constant scan', "the paper's own numbers", 'single-paper checks', 'whole-paper audits',
             'database differences']
    tot = sum(dr[k]['per_1000'] for k in below)
    L.add('dev.later.per_1000', round(tot, 1), 'serious errors later layers found per 1,000 values ever stored (base '
          '223,469): reprint sweep, partial-constant scan, the paper\'s own numbers, single-paper checks, whole-paper '
          'audits, database differences', kind='frozen', source=lj + ' :: panel_a.drawn', state='DEV', window=w,
          show=f'about {round(tot)}', forms=['found about 6 more serious errors'],
          note=f'{tot:.3f} per 1,000')
    L.add('dev.later.reprint_share', pct(dr['reprints']['per_1000'], tot, 0), 'the reprint sweep\'s share of those',
          kind='frozen', source=lj, state='DEV', window=w, show=pshow(dr['reprints']['per_1000'], tot, 0),
          forms=['71% of them reprinted'], note='970 of 1,367 values; Fig. 3\'s README rounds it to 70%')
    EJ('dev.layers.reprints_still_dropped', lj, ['panel_a', 'drawn', 'reprints', 'values'], 'reprint-sweep drops still '
       'dropped in the 22 October snapshot (Fig. 3a)', window=w, note='sweep.reprint.dropped counts the 973 drop lines')
    EJ('dev.audit.random.values', lj, ['panel_a', 'drawn', 'random audits', 'n'], 'values audited at random, whole-paper '
       'follow-ups left out (rule F), to 22 October', window='audits to 2026-10-22',
       forms=['(31 of {6,459} values'])
    EJ('dev.audit.random.wrong', lj, ['panel_a', 'drawn', 'random audits', 'wrong'], 'of those, found wrong (dropped or '
       'unit corrected)', window='audits to 2026-10-22', forms=['(31 of 6,459'])
    EJ('dev.audit.random.per_1000', lj, ['panel_a', 'drawn', 'random audits', 'per_1000'], 'dev.audit.random.wrong per '
       '1,000 audited', window='audits to 2026-10-22', forms=['still wrong at 4.8 per 1,000', 'Taking every audit drop as '
                                                               'right, 4.8'])
    EJ('dev.audit.random.papers', lj, ['panel_a', 'drawn', 'random audits', 'papers_audited'], 'papers of the audited '
       'values', window='audits to 2026-10-22', forms=['values in 3,308 papers'])
    ci = pa['drawn']['random audits']['paper_clustered_95']
    L.add('dev.audit.random.ci', ci, 'its paper-clustered bootstrap 95% interval (seed 5)', kind='frozen', source=lj,
          state='DEV', show=f'{ci[0]:.1f}-{ci[1]:.1f}', forms=['95% CI {3.0-6.8}'])
    EJ('dev.audit.lag_median_h', lj, ['panel_a', 'audit_lag_hours (rule F rows)', 'median'], 'median hours from reading '
       'to the random audit', nd=1, forms=['a median 1.5 h after reading'])
    s19 = pa['residual_sensitivity_logged_random_since_19_oct']
    L.add('dev.audit.since19.per_1000', round(s19['per_1000'], 1), 'wrong per 1,000 in the random samples logged since '
          '19 October', kind='frozen', source=lj, state='DEV', show=fmt(round(s19['per_1000'], 1), 1),
          forms=['at 4.2 in the samples'], note=f"{s19['wrong']} of {s19['n']:,}")
    L.add('dev.audit.since19.values', s19['n'], 'values in those samples', kind='frozen', source=lj, state='DEV',
          forms=['(12 of {2,846}'])
    L.add('dev.audit.since19.wrong', s19['wrong'], 'of those, wrong', kind='frozen', source=lj, state='DEV',
          forms=['(12 of 2,846'])
    L.add('dev.audit.since19.ci', s19['paper_clustered_95'], 'its paper-clustered 95% interval', kind='frozen',
          source=lj, state='DEV', show='{:.1f}-{:.1f}'.format(*s19['paper_clustered_95']), forms=['1.7-7.5'])
    pj = 'paper/figures/layers_ledger/evidence/rethink_20261022/pilot_layers/check/d_audits.json'
    EJ('dev.audit.all.values', pj, ['all', 'n'], 'every audited value to 22 October, whole-paper follow-ups included',
       forms=['Of all 6,651 audited values'])
    ck = 'paper/figures/layers_ledger/evidence/rethink_20261022/pilot_layers/CHECK.md'
    E('dev.audit.all.wrong_number_or_unit', 7, 'of those, values with a wrong number or unit (hand-classified, all 79 '
      'wrong rows)', ck, needle=['found the same 7 numeric', 'clustered CI 0.015–0.23%'],
      forms=['7 had a wrong number or unit'])
    L.add('dev.audit.all.wrong_number_or_unit_share', pct(7, 6651, 3), 'dev.audit.all.wrong_number_or_unit as a share',
          kind='frozen', source=ck, state='DEV', show='0.105%', forms=['(0.105%,'])
    E('dev.audit.all.ci', [0.015, 0.23], 'its paper-clustered 95% interval', ck, needle='clustered CI 0.015–0.23%',
      show='0.015-0.23%', forms=['95% CI {0.015-0.23%}'])
    rd = 'paper/figures/layers_ledger/README.md'
    E('dev.audit.kept_then_dropped', 10, 'audit-kept values later dropped as reprints (of 6,561 audit-kept values)', rd,
      needle='10 of the 6,561 values audits kept', forms=['10 of the 6,561 values', '(10 of 6,561 audit-kept rows'])
    E('dev.audit.kept', 6561, 'values audits kept, to 22 October', rd, needle='10 of the 6,561 values audits kept',
      forms=['10 of the {6,561} values', '10 of {6,561} audit-kept'])
    xj = 'paper/figures/layers_ledger/check/extra.json'
    EJ('dev.audit.trend_p', xj, ['5_trend_test_power', 'observed', 'z_p'], 'P of the Cochran-Armitage test for a trend '
       'in audited-wrong over papers read (not clustered)', nd=2, forms=['P = 0.64'])
    EJ('dev.audit.trend_power_halving', xj, ['5_trend_test_power', 'linear, end rate = 0.5 x start (6.4 to 3.2 per 1,000)'],
       'power of that test to detect a linear halving (1,500 simulations)', scale=100, nd=0,
       show='21%', forms=['only 21% of the time'])
    hj = 'paper/figures/layers_ledger/evidence/rethink_20261022/pilot_layers/check/h_trends.json'
    EJ('dev.verifier.partial_after_rule', hj, ['before_after', 'partial|mt|first', 'after', 'per_1000'], 'partial '
       'constants the verifier caught per 1,000 first-read values after the partial-constants rule (before: 0)',
       forms=['caught 0.67 such errors'], note='before the rule: 0 of 90,883')
    kb = 'paper/figures/layers_ledger/evidence/rethink_20261022/pilot_layers/check/k_budget.json'
    EJ('dev.verifier.broad_rows', kb, ['verifier_broad_rows_pilot_classes_my_check'], 'reader rows the verifier fixed or '
       'rejected that the code checks of 22 October would pass with an error, counting edits of names and identifiers '
       '(the pilot\'s own row classes, 429 of them such edits, while the strict 1,870 follow check/k_budget.py\'s own '
       'classes, so 2,289 is not 1,870 plus 429: verify_round2.md)', forms=['2,289 of them with an error that mattered'],
       note='the Methods called all 2,289 "an error that mattered" until 1 November (reconcile_log.md row 42); the '
            'strict set is dev.verifier.serious_values')
    EJ('dev.verifier.broad_per_1000', kb, ['verifier_broad_per_1000'], 'dev.verifier.broad_rows per 1,000 reader values',
       nd=1, forms=['11.1 counting'])
    EJ('dev.verifier.numeric_rows', kb, ['verifier_strict_numeric'], 'of the serious errors, those with a different '
       'stored number')
    nt = 'paper/figures/layers_ledger/evidence/rethink_20261022/pilot_layers/notes.md'
    E('dev.verifier.fixed_or_rejected', 10142, 'reader rows the verifier fixed or rejected in development (to 22 '
      'October)', nt, needle='of 10,142 fixed/rejected rows, 7,185 would pass code checks',
      forms=['of the 10,142 rows the verifier'])
    E('dev.verifier.would_pass_code', 7185, 'of those, rows the code checks of 22 October would pass as the reader '
      'wrote them', nt, needle='7,185 would pass code checks', forms=['7,185 would have passed'])


# ===================================================================================================== 12. benchmark, blind re-read, logs
def sec_h2h():
    h = 'paper/evidence/h2h_20261101/results_h2h.json'
    w = 'the 107 Co-Scientist gold papers CatLog had finished by 2026-10-22 (benchmark run 2026-10-22)'
    EJ('dev.h2h.papers', h, ['papers'], 'Enzyme Co-Scientist gold papers CatLog had finished and was scored on',
       window=w, forms=['on the 107 Enzyme Co-Scientist gold papers', 'on the {107} papers CatLog had finished',
                        'and on {107} of them the reader'])
    EJ('dev.h2h.gold_values', h, ['gold_values_numeric'], 'numeric gold values on those papers', window=w,
       forms=['(7,624 gold values)', 'hold 7,624 gold values'])
    a = ['systems', 'catlog', 'all_done_papers', 'all']
    EJ('dev.h2h.catlog_recall', h, a + ['recall', 'est'], 'CatLog recall (match: same paper and metric, value within '
       '1.5%, one to one)', nd=3, window=w, forms=["CatLog's recall was 0.954"])
    EJ('dev.h2h.catlog_precision', h, a + ['precision', 'est'], 'CatLog precision', nd=3, window=w,
       forms=['its precision 0.915'])
    d = json.loads(S.evidence(h))['systems']['catlog']['all_done_papers']['all']
    L.add('dev.h2h.catlog_recall_ci', [round(d['recall']['lo'], 3), round(d['recall']['hi'], 3)], 'its paper-clustered '
          '95% interval (seed 7)', kind='frozen', source=h, state='DEV', show='{:.3f}-{:.3f}'.format(d['recall']['lo'],
                                                                                                     d['recall']['hi']),
          forms=['95% CIs {0.935-0.970}'])
    L.add('dev.h2h.catlog_precision_ci', [round(d['precision']['lo'], 3), round(d['precision']['hi'], 3)],
          'its paper-clustered 95% interval', kind='frozen', source=h, state='DEV',
          show='{:.3f}-{:.3f}'.format(d['precision']['lo'], d['precision']['hi']), forms=['and 0.846-0.971'])
    for s, nm, fr, fp, fpap in (('brenda', 'BRENDA', 'BRENDA scored 0.730', 'BRENDA scored 0.730 and {0.776}',
                                 'values for 103 and'),
                                ('enzyextract', 'the EnzyExtract database', 'the EnzyExtract database 0.530',
                                 'database 0.530 and {0.678}', 'values for 103 and {70}')):
        b = ['systems', s, 'all_done_papers', 'all']
        EJ(f'dev.h2h.{s}_recall', h, b + ['recall', 'est'], f'{nm} recall over all 107 papers', nd=3, window=w, forms=[fr])
        EJ(f'dev.h2h.{s}_precision', h, b + ['precision', 'est'], f'{nm} precision', nd=3, window=w, forms=[fp])
        EJ(f'dev.h2h.{s}_papers', h, ['systems', s, 'papers_with_any_value'], f'papers for which {nm} holds values',
           window=w, forms=[fpap, '(103 and 70)' if s == 'brenda' else '(103 and {70})'])
    ck = 'paper/planning/top_journal_20261021/h2h/CHECK.md'
    E('dev.h2h.catlog_precision_corrected', [0.955, 0.975], 'CatLog precision once disagreements were decided against '
      'the papers (Claude adjudicator, not blinded): every unclassified leftover wrong to only partial constants and '
      'duplicates wrong', ck, needle=['precision between **0.955**', '**0.975**'], show='0.955-0.975',
      forms=["CatLog's precision was 0.955-0.975"])
    m = 'paper/evidence/h2h_20261101/results_enzyextract_manual.json'
    w59 = "the 59 papers of EnzyExtract's 384-paper manual set CatLog had finished by 2026-10-22"
    EJ('dev.ee.papers', m, ['catlog_done'], "papers of EnzyExtract's manual set CatLog had finished", window=w59,
       forms=['On the 59 papers', 'on 59 papers of', 'and CatLog and EnzyExtract\'s pipeline on 59 papers'])
    EJ('dev.ee.catlog_recall', m, ['on_catlog_done', 'catlog', 'all', 'recall', 'est'], 'CatLog recall there', nd=3,
       window=w59, forms=['precision 0.837'])
    EJ('dev.ee.catlog_precision', m, ['on_catlog_done', 'catlog', 'all', 'precision', 'est'], 'CatLog precision there',
       nd=3, window=w59, forms=['0.837 and {0.820}'])
    EJ('dev.ee.pipeline_recall', m, ['on_catlog_done', 'run_RGF', 'all', 'recall', 'est'], "EnzyExtract's full pipeline "
       'run (RGF) recall there', nd=3, window=w59, forms=['against 0.807'])
    EJ('dev.ee.pipeline_precision', m, ['on_catlog_done', 'run_RGF', 'all', 'precision', 'est'], "EnzyExtract's "
       'pipeline precision there', nd=3, window=w59, forms=['0.807 and {0.824}'])
    c6 = 'paper/evidence/h2h_20261101/check/c06_results.json'
    EJ('dev.h2h.reader_recall', c6, ['stages', 'A_reader_current_only', 'R'], 'recall of the reader alone (current read '
       'rounds) on the 107 papers', nd=3, window=w, forms=['already scored 0.953', 'reader alone reached 0.953'])
    EJ('dev.h2h.reader_precision', c6, ['stages', 'A_reader_current_only', 'P'], 'precision of the reader alone', nd=3,
       window=w, forms=['0.953 and {0.903}'])
    rp = 'paper/planning/top_journal_20261021/h2h/REPORT.md'
    E('dev.h2h.catlog_wrong_values', 198, 'CatLog values classed as wrong on the gold papers (176 partial constants in '
      '30730705 and 15056909, 22 duplicate rows in 20635860)', rp,
      needle=['176 partial constants in 30730705 and 15056909', '22 duplicate rows in 20635860'],
      forms=['Of the 198 CatLog values'])
    E('dev.h2h.catlog_wrong_from_two_papers', 176, 'of those, values from two papers read before the partial-constants '
      'rule', rp, needle='176 partial constants', forms=['176 came from two papers'])
    E('dev.h2h.gold_wrong', 9, 'disagreements on a number decided against the paper in which the gold was wrong (of 14 '
      'used)', rp, needle='Gold was wrong in 9 of 14 used, CatLog in 0',
      forms=['the gold was wrong in 9 of 14', 'gold was wrong in 9 and'])
    E('dev.h2h.number_disagreements', 14, 'disagreements on a number checked against the paper', rp,
      needle='Gold was wrong in 9 of 14', forms=['wrong in 9 of {14} cases', 'Of 14 disagreements'])
    E('dev.h2h.gold_wrong_values', 61, 'gold values found wrong, at least', ck, needle='(0.8%), not ~40',
      forms=['At least 61 gold values (0.8%)'])
    E('dev.h2h.gold_block', '×10³ header backwards, 10⁶-fold', "the gold set's ZmQC block of 20868223: a ×10³ header "
      'applied the wrong way round, every kcat and kcat/Km cell 10⁶-fold off', ck,
      needle='all 32 numeric kcat and kcat/Km cells are wrong by 10^6', kind='fact', show='×10³; 10⁶',
      forms=['a ×10³ header applied the wrong way round that puts a whole block 10⁶-fold off'])
    L.add('dev.h2h.gold_wrong_values_share', 0.8, 'dev.h2h.gold_wrong_values as a share of the gold values',
          kind='frozen', source=ck, state='DEV', show='0.8%', forms=['61 gold values ({0.8}%)'])
    c8 = 'paper/evidence/h2h_20261101/check/c08_results.json'
    EJ('dev.h2h.gold_closure_fail', c8, ['gold', 'rate_1.5x'], 'gold triples whose kcat/Km misses kcat ÷ Km by more than '
       '1.5-fold (of 2,423)', scale=100, nd=1, show='1.2%', forms=['by more than 1.5-fold in {1.2}%'])
    E('dev.h2h.catlog_closure_fail', 0.68, "CatLog's printed triples on those papers missing by more than 1.5-fold "
      '(16 of 2,354)', ck, needle='16 of 2,354 (0.68%)', show='0.68%', forms=["against CatLog's 0.68%"])
    E('dev.h2h.adjudicated', 62, 'disagreements decided against the papers (text and page images)', rp,
      needle='62 cases were checked', forms=['62 cases were checked'])
    E('dev.h2h.blind_redecided', 15, 'of those, cases a second checker re-decided blind (all agreed)', rp,
      needle='re-decided 15 of them blind, and all 15 agreed', forms=['re-decided 15 of them blind', 'all 15 the same way'])
    E('dev.h2h.gold_rows', 4244, 'rows of the Co-Scientist gold set (Hugging Face)', rp, needle='4,244 rows, 156 papers',
      forms=['4,244 rows from 156 papers'])
    E('dev.h2h.gold_papers', 156, 'papers of the gold set', rp, needle='4,244 rows, 156 papers',
      forms=['4,244 rows from {156} papers'])
    E('dev.h2h.tolerance', '1.5%; 0.5% to 5%', 'match tolerance and the range it was varied over', rp,
      needle=['value within 1.5%', 'between 0.5% and 5%'], show='1.5%; 0.5% to 5%',
      forms=['at most 1.5% of the larger', 'from 0.5% to 5%'])


def sec_blind():
    s = 'paper/evidence/blind_reread_20261022/SUMMARY.md'
    w = 'the blind re-read of 2026-10-21/22'
    E('dev.blind.papers', 303, 'papers exposed before the blind-reading rule and read again blind', s,
      needle='Blind re-read of the 303 exposed papers', window=w,
      forms=['blind re-read of 303 papers', 'The 303 exposed papers', 'The 303 papers exposed', 'of 303 papers'])
    E('dev.blind.fresh_papers', 173, 'of those, papers read again from scratch (readers had opened database values)', s,
      needle='| Papers | 173 | 130 |', window=w, forms=['readers in 173 papers', '(173 with fresh readers'])
    E('dev.blind.reverify_papers', 130, 'of those, papers given a new blind verifier only', s,
      needle='| Papers | 173 | 130 |', window=w, forms=['verifiers in 130 more', '130 with fresh verifiers'])
    E('dev.blind.fresh_same_share', 95.6, 'fresh blind reads that gave the same value again, of the earlier values', s,
      needle='9,339 (95.6%)', window=w, show='95.6%', forms=['for 95.6% of earlier values', 'reproduced 95.6%',
                                                             'reproduced 95.6% and'])
    E('dev.blind.fresh_base', 9765, 'earlier values of the fresh-read papers', s, needle='| Earlier values | 9,765 | 7,615 |',
      window=w, forms=['95.6% of {9,765}'])
    E('dev.blind.reverify_same_share', 98.1, 'new blind verifiers that gave the same value, of the earlier values', s,
      needle='7,470 (98.1%)', window=w, show='98.1%', forms=['and 98.1% with fresh', 'verifiers 98.1%',
                                                             'fresh verifications 98.1%'])
    E('dev.blind.reverify_base', 7615, 'earlier values of the re-verified papers', s,
      needle='| Earlier values | 9,765 | 7,615 |', window=w, forms=['98.1% of {7,615}'])
    E('dev.blind.wrong', 122, 'earlier values found wrong', s, needle='122 of 17,380', window=w,
      forms=['122 of the 17,380', '122 of 17,380'])
    E('dev.blind.base', 17380, 'earlier values of the 303 papers', s, needle='122 of 17,380', window=w,
      forms=['122 of the {17,380}', '122 of {17,380}'])
    E('dev.blind.corrected', 49, 'of the wrong ones, corrected (unit misprints the paper shows)', s, needle='49 corrected',
      window=w, forms=['49 corrected and 73'])
    E('dev.blind.dropped', 73, 'of the wrong ones, dropped', s, needle='73 dropped', window=w,
      forms=['and 73 dropped'])


def sec_logs():
    """Counts from scans of the agents' logs (most of them now only in the Nova archive): frozen."""
    c = 'paper/evidence/agent_highlights_20261028/COUNTS_ROUND2.md'
    o = 'paper/01_what_the_agents_did.md'
    cj = 'paper/evidence/agent_highlights_20261028/counts_transcripts_v2.json'
    wj = 'paper/evidence/agent_highlights_20261028/counts_workfiles.json'
    w = 'agent logs as of 2026-10-28 20:10 (13,636 on Nova, 6,787 on the Mac)'
    E('dev.logs.scanned', 20423, 'agent logs scanned', c, needle='Logs: 20,423 agent logs', window=w,
      forms=['In a scan of 20,423 agent logs'])
    E('dev.logs.on_nova', 13636, 'agent logs copied to the Nova archive and checked there file by file, by 28 October',
      c, needle='13,636 in the Nova archive', window=w, forms=['13,636 agent logs'])
    E('dev.logs.papers_with_logs', 5651, 'papers with a reader or verifier log of the reading workflow', o,
      needle='5,651 of 7,062 (80%)', window=w, forms=['of the 5,651 papers with logs', 'In the logs of 5,651 papers'])
    E('dev.logs.papers_read', 7062, 'papers with a verify file by 28 October', o, needle='5,651 of 7,062', window=w,
      forms=['of the 7,062 papers read by 28 October'])
    L.add('dev.logs.papers_without_log_share', round(100 * (1 - 5651 / 7062)), 'papers read by 28 October with no '
          'reader or verifier log among the workflow logs', kind='frozen', source=o, state='DEV', window=w,
          show='about 20%', forms=['about 20% of the 7,062'])
    E('dev.logs.page_image_papers', 2916, 'papers where a reader or verifier opened a rendered page image', c,
      needle='2,916 (51.6%)', window=w, forms=['page images in 2,916 of'])
    L.add('dev.logs.page_image_share', 51.6, 'dev.logs.page_image_papers of dev.logs.papers_with_logs', kind='frozen',
          source=c, state='DEV', show='51.6%', forms=['(51.6%)'])
    EJ('dev.logs.verdicts_on_image', wj, ['verdicts_on_page_image'], 'verifier verdicts (each paper\'s latest verify '
       'file) made on the page image', window=w, forms=['27,640 of 185,927'])
    vv = json.loads(S.evidence(wj))['verdicts']
    L.add('dev.logs.verdicts', sum(vv.values()), 'verifier verdicts in each paper\'s latest verify file (7,062 papers)',
          kind='frozen', source=wj, state='DEV', window=w, forms=['27,640 of {185,927}'])
    L.add('dev.logs.verdicts_on_image_share', pct(27640, sum(vv.values())), 'share of those made on the image',
          kind='frozen', source=wj, state='DEV', window=w, show=pshow(27640, sum(vv.values())), forms=['(14.9%)'])
    E('dev.logs.missed_found', 1138, 'values readers skipped that verifiers found (missed-value files in work/)', o,
      needle='1,138 in 94 papers; a second verifier confirmed 1,100', window=w,
      forms=['recovered 1,138 values'], check=None,
      note='by the stamps (read_by "verifier (missed values)") 1,350 stored values in 77 papers on 31 October '
           '(Fig. 1 v2 numbers, CHECK_v2.md A10): another definition')
    E('dev.logs.missed_found_papers', 94, 'their papers', o, needle='1,138 in 94 papers', window=w,
      forms=['had skipped, in 94'])
    E('dev.logs.missed_confirmed', 1100, 'of those, values a second verifier confirmed', o,
      needle='a second verifier confirmed 1,100', window=w, forms=['confirmed 1,100 of them'])
    cr = json.loads(S.evidence(cj))['per_role']
    before = cr['read']["read another paper before / after the 2026-10-14 rule"]['before'][0] + \
        cr['verify']["read another paper before / after the 2026-10-14 rule"]['before'][0]
    L.add('dev.logs.other_paper_before_prompt', before, 'readers and verifiers that read another paper\'s text before '
          'the prompts asked for such comparisons (2026-10-14 16:05, git 078ea59)', kind='frozen', source=cj,
          state='DEV', window=w, forms=['61 agents read another paper'])
    web = cr['read']['used the web']['agents'] + cr['verify']['used the web']['agents']
    L.add('dev.logs.web_agents', web, 'readers and verifiers that used the web', kind='frozen', source=cj, state='DEV',
          window=w, forms=['and 67 used the web', 'Of the 67,', '67 agents in 61 papers'])
    E('dev.logs.web_papers', 61, 'papers of those agents', o, needle='67 agents in 61 papers', window=w,
      forms=['67 agents in {61} papers'])
    E('dev.logs.web_after_rule', 23, 'of those agents, those after the "use only this paper" rule (2026-10-12)', o,
      needle='23 after the "use only this paper" rule', window=w, forms=['23 used it after'])
    E('dev.logs.other_paper_papers', 292, 'papers where an agent read another paper\'s text', o, needle='| 292 (5.2%);',
      window=w, forms=['in 292 papers an agent'])
    E('dev.logs.direct_agents', 227, 'agents the main session launched directly in the first days (not in these counts)',
      o, needle='227 agents the main chat launched directly', window=w, forms=['launched 227 agents directly'])
    sn = 'paper/manuscript/supp_note_1_system.md'
    E('dev.logs.workstation_agents', 3844, 'reader and verifier agents of the reading workflow whose logs are still on the '
      'workstation (nearly all of 27-31 October)', sn, needle='| n54a | 3,844; 654; 606; 188; 183; 5 |',
      window='logs on the workstation, scanned 2026-10-31 23:15', forms=['(3,844 reader and'])
    E('dev.logs.queue_line_agents', 654, 'of those, agents that printed their paper\'s whole queue line', sn,
      needle='| n54a | 3,844; 654; 606;', forms=['654 agents in 606 papers'])
    E('dev.logs.queue_line_papers', 606, 'their papers', sn, needle='| n54a | 3,844; 654; 606;',
      forms=['654 agents in {606} papers'])
    E('dev.logs.own_rows_agents', 188, 'agents that looked up their own paper\'s rows in CatLog\'s row files', sn,
      needle='| n54a | 3,844; 654; 606; 188; 183;', forms=['188 agents looked up'])
    E('dev.logs.own_rows_censored', 183, 'of those, agents in censored-only passes', sn,
      needle='| n54a | 3,844; 654; 606; 188; 183;', forms=['183 of them in censored-only'])
    E('dev.logs.claude_code_versions', '2.1.293 to 2.1.309', 'Claude Code versions in the logs still on the '
      'workstation', sn, needle='| n60 | about 5,100; 2.1.293 to 2.1.309 |', show='2.1.293 to 2.1.309',
      forms=['(2.1.293 to 2.1.309', 'versions 2.1.293 to 2.1.309'])


def sec_case_coding():
    """The agent cases of all seven rounds (2026-10-28 to 11-06): counts from the coding files of each round (the refuted
    3624267 left out), checked against page 04's printed counts; Fleiss kappa per coding run from the coders' own files.
    The forms are results.md's sentences of 6 November 2026, for the next assembled draft; draft_v1.md, which this build
    scans for phrases, still has those of 1 November, so a run lists them as not found until the draft is rebuilt."""
    ev = 'paper/evidence/agent_highlights_20261028/'
    t = 'paper/04_agent_case_tables.md'
    tt = S.evidence(t)
    r4 = json.loads(S.evidence(ev + 'round4/coding/FINAL.json'))
    held = [{'pmid': p, 'votes': v['votes'], 'doc': bool(v['second_document'])} for p, v in r4.items()]
    runs = [('round4', ev + 'round4/coding/{c}.json')]
    for f in ('round5/coding/FINAL_r5_raw.json', 'round6/coding/FINAL_r6_raw.json', 'round7/coding/FINAL_r7p1_raw.json',
              'round7/coding/FINAL_r7p2_raw.json'):
        held += [{'pmid': m['pmid'], 'votes': m['votes'], 'doc': bool(m['needed_second_document'])}
                 for m in json.loads(S.evidence(ev + f))['majority'] if m['pmid'] != '3624267']
    for r, pat in (('round5', 'round5/coding/{c}.json'), ('round6', 'round6/coding/{c}.json'),
                   ('round7 first pass', 'round7/coding/{c}.json'), ('round7 second pass', 'round7/coding/p2_{c}.json')):
        runs.append((r, ev + pat))
    src = (ev + 'round4/coding/FINAL.json, round5/coding/FINAL_r5_raw.json, round6/coding/FINAL_r6_raw.json, '
           'round7/coding/FINAL_r7p1_raw.json, FINAL_r7p2_raw.json (3624267, refuted, left out)')
    n_held = len(held)
    if n_held != 233 or len({h['pmid'] for h in held}) != n_held:
        ERRORS.append(f'cases: {n_held} coded cases that held, expected 233 once each')
    must(tt, 'all 233 cases that held (234 checked)', t)
    L.add('cases.checked', n_held + 1, 'agent cases mined in seven rounds (2026-10-28 to 11-06), each re-checked against '
          'its paper by agents told to refute it', kind='frozen', source=src + '; ' + t, state='ON FILE',
          forms=['We mined 234 cases'])
    L.add('cases.held', n_held, 'agent cases that held (all but 3624267, refuted by two of three refuters)',
          kind='frozen', source=src, state='ON FILE', forms=['71 of the {233} checked cases', 'agreed on 219 of {233}'])
    L.add('cases.kinds', 10, 'kinds the coding agents sorted them into (nine and "other")', kind='frozen',
          source=ev + 'round4/CODING_BRIEF.md', state='ON FILE', show='ten', forms=[])
    agreed = sum(1 for h in held if h['votes'] == 3)
    L.add('cases.agreed', agreed, 'cases on which all three coding agents of their run agreed on the kind', kind='frozen',
          source=src, state='ON FILE', forms=['agreed on 219 of 233'])
    kap = {}
    for name, pat in runs:
        codes = {}
        for c in 'ABC':
            for x in json.loads(S.evidence(pat.format(c=c)))['codes']:
                if x['pmid'] != '3624267':
                    codes.setdefault(x['pmid'], {})[c] = x['primary_kind']
        items = [v for v in codes.values() if len(v) == 3]
        cats = sorted({k for v in items for k in v.values()})
        N, n = len(items), 3
        Pi = [(sum(sum(1 for c in v.values() if c == k) ** 2 for k in cats) - n) / (n * (n - 1)) for v in items]
        pj = [sum(sum(1 for c in v.values() if c == k) for v in items) / (N * n) for k in cats]
        pe = sum(p * p for p in pj)
        kap[name] = (round((sum(Pi) / N - pe) / (1 - pe), 2) if pe < 1 else 1.0, N)
    note = '; '.join(f'{k} {v[0]:.2f} over {v[1]}' for k, v in kap.items())
    L.add('cases.kappa_min', min(v[0] for v in kap.values()), 'lowest Fleiss kappa of the coders\' primary kinds over '
          'the five coding runs of more than six cases', kind='frozen', source=src + ' (coders A, B, C of each run; kappa '
          'computed here)', state='ON FILE', forms=['(Fleiss κ 0.82 to'], note=note)
    L.add('cases.kappa_max', max(v[0] for v in kap.values()), 'highest Fleiss kappa of those runs', kind='frozen',
          source=src, state='ON FILE', show=f'{max(v[0] for v in kap.values()):.2f}', forms=['0.82 to {1.00}'], note=note)
    for key, row, n_, form in (('bound', 'bound or not detected', 59, 'not detected (59)'),
                               ('unit_misprint', 'unit misprint', 37, 'misprints (37)'),
                               ('contradicts', 'paper contradicts itself', 36, 'contradict themselves (36)')):
        E(f'cases.kind.{key}', n_, f'cases of kind {row} (Supplementary Tables S1-S11)', t,
          needle=f'| {row} | {n_} |', state='ON FILE', forms=[form])
    doc = sum(1 for h in held if h['doc'])
    L.add('cases.second_document', doc, 'cases whose decisive evidence the coders placed outside the paper\'s body',
          kind='frozen', source=src, state='ON FILE', forms=['In 40 cases the coders'])
    must(tt, f'| **total** | **233** | **{doc}** | **71** |', t)
    for key, v, form in (('own_reasoning', 71, "agent's own reasoning in 71"), ('prompted', 145, 'to apply in 145'),
                         ('code_put', 14, 'put in front of it in 14'), ('earlier', 3, 'proposed earlier in 3')):
        E(f'cases.provenance.{key}', v, 'cases by where the decisive test came from (provenance checks)', t,
          needle='the provenance checks found the agent\'s own reasoning in 71, a prompted kind of test that\nthe agent '
                 'chose to apply in 145, a case code put in front of the agent in 14, and a finding an earlier agent or '
                 'document\nhad proposed in 3', state='ON FILE', forms=[form])
    E('cases.gated', 71, 'cases through the main table\'s gate (held, the agent\'s own reasoning, blind)', t,
      needle='## Main table (draft): 12 of the 71 eligible cases', state='ON FILE', forms=['71 of the 233'])
    E('cases.boxed', 9, 'cases told start to finish (Box 1 and Supplementary Information)', 'paper/05_agent_case_boxes.md',
      needle='### Box 9.', state='ON FILE', show='nine', forms=[])


def sec_sweeps_frozen():
    sn = 'paper/manuscript/supp_note_1_system.md'
    E('sweep.scale.records_off', 899, 'records whose printed kcat/Km missed kcat ÷ Km by a unit factor in the first run '
      '(20 October)', sn, needle='| n35 | 899; 798; 16; 41 |', window='2026-10-20', state='ON FILE',
      forms=['899 records whose printed', 'found 899 records'])
    E('sweep.scale.read_other_unit', 798, 'of those, records already read in another unit', sn,
      needle='| n35 | 899; 798;', window='2026-10-20', state='ON FILE', forms=['798 of them already'])
    E('sweep.scale.override_papers', 41, 'papers where a reader or verifier had replaced a plain printed unit, checked: '
      'the replaced column was the misprinted one in all', sn, needle='| n35 | 899; 798; 16; 41 |', window='2026-10-20',
      state='ON FILE', forms=['In all 41 papers checked', 'in all 41 papers'])
    E('sweep.vmax.flagged', 186, 'papers the maximal-rate sweep flagged (a stored kcat 5-fold or more above the bound)',
      sn, needle='/ 60; 160 characters; 10^4 µmol min^-1 mg^-1; 5-fold; 186', window='2026-10-23', state='ON FILE',
      forms=['(186 papers on 23'])
    for key, v, what, forms in (('checked', 22, 'flagged papers near an exact unit factor that agents checked',
                                 ['among 22 flagged papers', 'A check of the 22 papers']),
                                ('headers', 2, 'misprinted headers found', ['found two misprinted kcat headers',
                                                                           'found 2 misprinted headers']),
                                ('cell_slip', 1, 'slipped cells found', ['1 slipped cell']),
                                ('per_tetramer', 1, 'kcat stated per tetramer', ['1 kcat stated per tetramer']),
                                ('disagree', 3, 'papers whose printed numbers disagree with each other, left as printed',
                                 ['left 3 papers']),
                                ('false', 15, 'flags judged false positives', ['judged 15 of the 22 flags false',
                                                                               'judged 15 flags'])):
        E(f'sweep.vmax.{key}', v, what, sn, needle='| n37 | at least 2; at most 1; 22; 2; 1; 3; 15 |',
          window='2026-10-23', state='ON FILE', forms=forms)
    E('sweep.nd.checked', 715, 'stored not-detected values whose paper suggested an undetermined constant, checked by two '
      'blind agents and a third on disagreements', sn, needle='| n39 | 715; 81;', window='2026-10-26', state='ON FILE',
      forms=['re-checked 715 not-detected', '(715 values in 81'])
    E('sweep.nd.papers', 81, 'their papers', sn, needle='| n39 | 715; 81;', window='2026-10-26', state='ON FILE',
      forms=['715 values in {81} papers'])
    h = 'paper/evidence/reprint_sweep_20261016/HANDOFF.md'
    E('sweep.reprint.papers_scanned', 296, 'papers sharing 3 or more specific printed values with another, checked cell by '
      'cell', sn, needle='| n41 | two further judges; 3 significant figures; 6 papers; 4; 3; 296; 3 or more; 973; 80; 165; '
                          '206; four; 4 |', window='2026-10-16', state='ON FILE', forms=['Of 296 papers sharing'])
    E('sweep.reprint.refuted_kept', 165, 'rows a refuter refuted and kept', sn, needle='973; 80; 165; 206;',
      window='2026-10-16', state='ON FILE', forms=['165 rows were'])
    E('sweep.reprint.unsure_kept', 206, 'rows kept as unsure', sn, needle='973; 80; 165; 206;', window='2026-10-16',
      state='ON FILE', forms=['206 unsure rows'])
    E('sweep.reprint.audit_finds', 4, 'reprints audits had found that the scan cannot see', sn, needle='four; 4 |',
      window='2026-10-16', state='ON FILE', forms=['None of the 4 reprints', 'None of the 4\nreprints'])
    E('cat.unstamped_draft_rows', 311, 'rows verified under an uncommitted draft of the implausible-scale rule '
      '(verify_prompt 63b7a1d89cd7)', sn, needle='| n16 | 146 lines; 311; 33 |', state='ON FILE',
      forms=['except 311 rows of 33'],
      check=sum(1 for r in S.cat if r.get('verify_prompt') == '63b7a1d89cd7'))
    E('cat.unstamped_draft_papers', 33, 'their papers', sn, needle='| n16 | 146 lines; 311; 33 |', state='ON FILE',
      forms=['311 rows of {33} papers'],
      check=len({r['pmid'] for r in S.cat if r.get('verify_prompt') == '63b7a1d89cd7'}))


def sec_r2_random():
    """R2 (6 November 2026): the pilot, the random test and the hard cases, every number read from r2_numbers.json, which
    paper/evidence/random_papers_20261104/r2_numbers.py builds from the record files (the kit's score_pilot and
    score_rand records, the hard-case summary). DEV marks the pilot (development papers)."""
    r2 = 'paper/evidence/random_papers_20261104/r2_numbers.json'
    pct1 = lambda v: f'{100 * v:.1f}'  # noqa: E731
    rows = [  # key, path, what, show, state
        ('pilot.papers', ['pilot', 'papers'], 'development papers with answer keys in the pilot', None, 'DEV'),
        ('pilot.decoys', ['pilot', 'judge_gate', 'decoys'], 'planted errors in the pilot, all caught', None, 'DEV'),
        ('pilot.plain_values', ['pilot', 'values', 'A0'], 'values one plain reading stored', '907', 'DEV'),
        ('pilot.plain_wrong', ['pilot', 'wrong', 'A0'], 'of them wrong', '4', 'DEV'),
        ('pilot.opus_values', ['pilot', 'opus_read_values'], 'values the plain reading stored on the papers Opus 5.5 read', None, 'DEV'),
        ('pilot.opus_papers', ['pilot', 'opus_read_papers'], 'papers Opus 5.5 read (the others: Sonnet 5.5 after a refusal)', None, 'DEV'),
        ('pilot.two_values', ['pilot', 'values', 'A2'], 'values two readings and a reconciliation stored', '889', 'DEV'),
        ('pilot.harness_values', ['pilot', 'values', 'A6'], 'values the full CatLog harness stored', '882', 'DEV'),
        ('rand.frame', ['random', 'frame'], 'finished, eligible papers the random test drew from', '6,733', 'ON FILE'),
        ('rand.papers', ['random', 'papers'], 'papers in the random test', None, 'ON FILE'),
        ('rand.refused', ['random', 'refused_replaced', 'refused'], 'papers the safety filter refused, replaced', None, 'ON FILE'),
        ('rand.values_plain', ['random', 'values', 'plain'], 'values the plain reading stored', '4,587', 'ON FILE'),
        ('rand.values_catlog', ['random', 'values', 'catlog'], "CatLog's values for the same papers", '4,447', 'ON FILE'),
        ('rand.agreeing', ['random', 'agreeing_pairs'], 'pairs agreeing in number and description', '4,289', 'ON FILE'),
        ('rand.label_pairs', ['random', 'identity_suspect_pairs'], 'pairs agreeing in number only', None, 'ON FILE'),
        ('rand.unmatched_plain', ['random', 'unmatched', 'plain'], 'plain values without a partner', None, 'ON FILE'),
        ('rand.unmatched_catlog', ['random', 'unmatched', 'catlog'], 'CatLog values without a partner', None, 'ON FILE'),
        ('rand.sampled', ['random', 'agreeing_pairs_sampled'], 'agreeing pairs judged, drawn at random', None, 'ON FILE'),
        ('rand.decoys', ['random', 'decoys'], 'planted errors', None, 'ON FILE'),
        ('rand.third_judge', ['random', 'judges', 'third_judge_real_claims'], 'claims a third judge ruled on', None, 'ON FILE'),
        ('rand.agree_disputed', ['random', 'judges', 'first_two_agree_disputed'], 'share of disputed claims the first two judges agreed on', '95.6', 'ON FILE'),
        ('rand.kappa', ['random', 'judges', 'kappa_real_claims'], "the first two judges' kappa over all real claims", '0.86', 'ON FILE'),
        ('rand.wrong_plain', ['random', 'wrong', 'plain'], "the plain reading's wrong values", None, 'ON FILE'),
        ('rand.wrong_catlog', ['random', 'wrong', 'catlog'], "CatLog's wrong values", None, 'ON FILE'),
        ('rand.rate_plain', ['random', 'wrong_per_1000', 'plain', 0], 'plain: wrong per 1,000 values', '13.7', 'ON FILE'),
        ('rand.rate_plain_lo', ['random', 'wrong_per_1000', 'plain', 1], 'its paper-level 95% CI, low', '3.8', 'ON FILE'),
        ('rand.rate_plain_hi', ['random', 'wrong_per_1000', 'plain', 2], 'its paper-level 95% CI, high', '28.9', 'ON FILE'),
        ('rand.rate_catlog', ['random', 'wrong_per_1000', 'catlog', 0], 'CatLog: wrong per 1,000 values', '3.4', 'ON FILE'),
        ('rand.rate_catlog_lo', ['random', 'wrong_per_1000', 'catlog', 1], 'its paper-level 95% CI, low', '0.7', 'ON FILE'),
        ('rand.rate_catlog_hi', ['random', 'wrong_per_1000', 'catlog', 2], 'its paper-level 95% CI, high', '7.2', 'ON FILE'),
        ('rand.papers_wrong_plain', ['random', 'papers_with_a_wrong_value', 'plain', 0], 'papers with a plain wrong value', None, 'ON FILE'),
        ('rand.papers_wrong_catlog', ['random', 'papers_with_a_wrong_value', 'catlog', 0], 'papers with a CatLog wrong value', None, 'ON FILE'),
        ('rand.wrong_plain_only', ['random', 'wrong_by_where', 'plain unmatched'], 'wrong values among those only the plain reading stored', None, 'ON FILE'),
        ('rand.plain_only_credited', ['random', 'wrong_by_where_and_verdict', 'plain unmatched not_measured_here'], '... credited to earlier work', None, 'ON FILE'),
        ('rand.plain_only_metric', ['random', 'wrong_by_where_and_verdict', 'plain unmatched wrong_metric'], '... another quantity', None, 'ON FILE'),
        ('rand.plain_only_identity', ['random', 'wrong_by_where_and_verdict', 'plain unmatched wrong_identity'], '... another enzyme, organism, variant or substrate', None, 'ON FILE'),
        ('rand.plain_only_scale', ['random', 'wrong_by_where_and_verdict', 'plain unmatched wrong_scale'], '... wrong scale', None, 'ON FILE'),
        ('rand.catlog_label_pairs_wrong', ['random', 'wrong_by_where_and_verdict', 'catlog identity_suspect wrong_identity'], "CatLog's wrong labels in pairs agreeing in number only", None, 'ON FILE'),
        ('rand.catlog_sample_identity', ['random', 'wrong_by_where_and_verdict', 'catlog matched_sample wrong_identity'], "CatLog's wrong labels in the agreeing sample", None, 'ON FILE'),
        ('rand.catlog_sample_number', ['random', 'wrong_by_where_and_verdict', 'catlog matched_sample wrong_number'], "CatLog's wrong numbers in the agreeing sample", None, 'ON FILE'),
        ('rand.catlog_sample_scale', ['random', 'wrong_by_where_and_verdict', 'catlog matched_sample wrong_scale'], "CatLog's wrong scale in the agreeing sample", None, 'ON FILE'),
        ('rand.largest_plain', ['random', 'largest_paper', 'plain', 1], "the plain reading's wrong values in its largest paper", None, 'ON FILE'),
        ('rand.diff_lo', ['random', 'difference_plain_minus_catlog_per_1000_ci', 0], 'plain minus CatLog per 1,000, 95% CI low', '-0.3', 'ON FILE'),
        ('rand.diff_hi', ['random', 'difference_plain_minus_catlog_per_1000_ci', 1], 'plain minus CatLog per 1,000, 95% CI high', '25.5', 'ON FILE'),
        ('rand.share_plain_higher', ['random', 'share_resamples_plain_higher'], 'share of paper-level resamples with the plain rate higher', '97', 'ON FILE'),
        ('rand.sample_wrong_plain', ['random', 'sample_wrong', 'plain'], 'plain values wrong in the agreeing sample', None, 'ON FILE'),
        ('rand.sample_wrong_catlog', ['random', 'sample_wrong', 'catlog'], 'CatLog values wrong in the agreeing sample', None, 'ON FILE'),
        ('rand.scaled_plain', ['random', 'scaled_per_1000', 'plain', 0], 'plain per 1,000 with the sample scaled', '22', 'ON FILE'),
        ('rand.scaled_catlog', ['random', 'scaled_per_1000', 'catlog', 0], 'CatLog per 1,000 with the sample scaled', '13', 'ON FILE'),
        ('rand.catlog_missed', ['random', 'misses', 'catlog_missed', 0], 'right values only the plain reading stored', None, 'ON FILE'),
        ('rand.catlog_missed_papers', ['random', 'misses', 'catlog_missed', 1], 'their papers', None, 'ON FILE'),
        ('rand.plain_missed', ['random', 'misses', 'plain_missed', 0], 'right values only CatLog stored', None, 'ON FILE'),
        ('rand.plain_missed_papers', ['random', 'misses', 'plain_missed', 1], 'their papers', None, 'ON FILE'),
        ('hard.papers', ['hard_cases', 'papers'], 'trap papers Opus 5.5 read', None, 'ON FILE'),
        ('hard.fell_in', ['hard_cases', 'fell_in', 0], 'papers where one plain reading stored the trap value', None, 'ON FILE'),
        ('hard.judgment', ['hard_cases', 'judgment_traps', 0], 'traps of what a number is fallen into', None, 'ON FILE'),
        ('hard.judgment_of', ['hard_cases', 'judgment_traps', 1], 'traps of what a number is', None, 'ON FILE'),
        ('hard.reading_of', ['hard_cases', 'reading_traps', 1], 'traps of how a number is printed (none fallen into)', None, 'ON FILE'),
        ('hard.noticed', ['hard_cases', 'noticed_of_fell_in_visible_in_paper', 0], 'papers where its notes named the problem', None, 'ON FILE'),
        ('hard.noticed_of', ['hard_cases', 'noticed_of_fell_in_visible_in_paper', 1], 'fallen-in papers with the trap visible in the paper', None, 'ON FILE'),
        ('hard.catlog_read', ['hard_cases', 'catlog_read'], 'trap papers CatLog has read', None, 'ON FILE'),
        ('hard.catlog_first', ['hard_cases', 'catlog_first_read_fell_in', 0], "papers where CatLog's reader stored the trap value", None, 'ON FILE'),
        ('hard.catlog_kept', ['hard_cases', 'catlog_papers_with_trap', 0], "papers whose catalogue holds the trap value", None, 'ON FILE'),
        ('hard.refused', ['hard_cases_refused_note', 'refused'], 'further trap papers the safety filter refused', None, 'ON FILE'),
        ('hard.sonnet_fell_in', ['hard_cases_refused_note', 'sonnet_fell_in', 0], 'of them, Sonnet 5.5 fell in', None, 'ON FILE'),
    ]
    for key, path, what, show, state in rows:
        EJ(f'r2.{key}', r2, path, what, show=show, state=state, window='2026-11-06 (the random test; the pilot of 2 November; the hard cases of 4 November)')
    E('r2.model_version', 5.5, 'the version of Claude Opus and Sonnet in these tests (claude-opus-5-5, claude-sonnet-5-5)',
      r2, needle=['claude-opus-5-5', 'claude-sonnet-5-5'], show='5.5', state='ON FILE', kind='code')
    for key, path, what in (('pilot.recall_plain', ['pilot', 'recall_identity_aware', 'A0'], 'answer-key values one plain reading found'),
                            ('pilot.recall_harness', ['pilot', 'recall_identity_aware', 'A6'], 'answer-key values the harness found')):
        v = jpath(json.loads(S.evidence(r2)), path)
        EJ(f'r2.{key}', r2, path, what, show=pct1(v), state='DEV', window='2026-11-02 (the pilot)')


def sec_cost():
    c = 'paper/evidence/rethink_20261101/cost_summary.json'
    w = 'agents of 2026-10-09 to 2026-10-22 with transcripts on disk (run 2026-10-22)'
    EJ('cost.per_paper_median', c, ['per_paper_read_plus_verify_usd', 'median'], 'median list-price-equivalent cost of '
       'reading and verifying one paper (read + verify agents), at assumed prices', nd=2, window=w,
       show='$1.52', forms=['$1.52 per paper'])
    j = json.loads(S.evidence(c))
    p = j['per_paper_read_plus_verify_usd']
    L.add('cost.per_paper_p10_p90', [round(p['p10'], 2), round(p['p90'], 2)], '10th-90th percentile of that cost',
          kind='frozen', source=c, state='DEV', window=w, show=f"${p['p10']:.2f}-{p['p90']:.2f}",
          forms=['$0.99-3.26'])
    L.add('cost.papers', p['n'], 'papers priced', kind='frozen', source=c, state='DEV', window=w,
          forms=['n = 6,013'])
    EJ('cost.reader_median', c, ['per_role_usd', 'read', 'median'], 'median cost of one reading agent', nd=2, window=w,
       show=f"${j['per_role_usd']['read']['median']:.2f}", forms=['$0.75 per reader'])
    EJ('cost.verifier_median', c, ['per_role_usd', 'verify', 'median'], 'median cost of one verifying agent', nd=2,
       window=w, show=f"${j['per_role_usd']['verify']['median']:.2f}", forms=['$0.71 per verifier'])
    pr = j['prices_per_mtok']['claude-opus-5-5']
    L.add('cost.prices', pr, 'assumed list prices per million tokens for claude-opus-5-5: input, output, cache read '
          '(not checked against the provider)', kind='frozen', source=c, state='DEV',
          show=f'${pr[0]:g} / ${pr[1]:g} / ${pr[2]:g}', forms=['$4 input', '$20 output', '$0.2 cache read'])
    t = 'paper/evidence/rethink_20261101/tokens_summary.json'
    S.evidence(t)
    E('cost.cache_share', 91, 'cache reads as a share of an agent\'s tokens (medians)', 'paper/manuscript/supp_note_1_system.md',
      needle='| n66a | 1.03 million; 91%;', show='about 91%', forms=['about 91% of an agent'])


# ===================================================================================================== 13. literature, corpus, code constants, plans
def sec_literature():
    pl = 'paper/planning/'
    lit = [
        ('lit.brenda_differ.kroll2021', 'about 10%', 'share of BRENDA values that differ from their papers, as Kroll et al. '
         '2021 [7] put it', pl + 'publication_strategy_20261021/factcheck_competitors.md', 'on the order of 10% of the values',
         ['at about 10% [7]']),
        ('lit.brenda_differ.turnup', 'up to 20%', 'the same, as TurNuP [4] puts it, both citing Bar-Even et al. 2011 [9]',
         pl + 'publication_strategy_20261021/factcheck_competitors.md', 'up to 20% of the entries in BRENDA',
         ['and up to 20% [4]']),
        ('lit.bar_even_year', '2011', 'year of the one comparison both cite', pl + 'publication_strategy_20261021/'
         'factcheck_competitors.md', 'Biochemistry 50:4402 (2011)', ['one comparison from 2011']),
        ('lit.pdbbind_unsupported', 'about 19%', 'PDBbind protein-protein binding constants checked by hand that lack '
         'support in their papers [10]', pl + 'top_journal_20261021/nmeth/similar/preprints_check.md',
         '~19% of KD values not supported by their papers', ['about 19% of protein–protein']),
        ('lit.sabio_by_hand', 'over 90%', "share of SABIO-RK's data experts extracted by hand [2]",
         pl + 'publication_strategy_20261021/landscape.md', '>90% of entries extracted by hand',
         ['over 90% of SABIO-RK']),
        ('lit.kinetics_papers_per_year', 'about 1,480', 'papers a year that a Europe PMC search finds mentioning kcat and '
         'Km (1,479 in 2010-2014, 1,472 in 2015-2019, 1,484 in 2020-2024), flat since 2010',
         pl + 'brenda_lag_20261021/REPORT.md', '1,479 papers a year in 2010–2014, 1,472 in 2015–2019 and 1,484 in 2020–2024',
         ['about 1,480 papers a year']),
        ('lit.brenda_share.2000s', '33.8%', 'share of those papers published 2000-2009 that BRENDA cites',
         pl + 'brenda_lag_20261021/REPORT.md', 'BRENDA cites 33.8% (95% CI 32–35%) of the search hits published 2000–2009',
         ['BRENDA cites 33.8%']),
        ('lit.brenda_share.2015_2019', '18.6%', 'share of those published 2015-2019 that BRENDA cites',
         pl + 'brenda_lag_20261021/REPORT.md', '18.6% (95% CI 17–20%) of those published 2015–2019', ['but 18.6%']),
        ('lit.brenda_intake_trend', '-3.9% a year (95% CI -5.4 to -2.5)', "BRENDA's intake of kinetics papers per "
         'publication year, 2010-2019', pl + 'brenda_lag_20261021/REPORT.md',
         '−3.9% a year (95% CI −5.4 to −2.5) over 2010–2019', ['fell by 3.9% per publication year', '(95% CI 2.5–5.4%)']),
        ('lit.chatextract', 'about 90%', 'ChatExtract precision and recall on materials properties [12]',
         pl + 'publication_strategy_20261021/landscape.md', 'precision and recall ~90% (GPT-4)',
         ['about 90% precision and recall']),
        ('lit.enzyextract_papers', '137,892', 'papers EnzyExtract ran its model over [13]',
         pl + 'publication_strategy_20261021/factcheck_competitors.md', '137,892', ['over 137,892 papers']),
        ('lit.coscientist_papers', '156', "expert-annotated papers of the Enzyme Co-Scientist's evaluation [14]",
         pl + 'top_journal_20261021/nmeth/similar/preprints_check.md', 'on 156 expert-annotated papers',
         ['on 156 expert-annotated papers']),
        ('lit.coscientist_brenda_f1', '0.76', "BRENDA's mean paper-wise F1 there, below every model [14]",
         pl + 'top_journal_20261021/nmeth/similar/preprints_check.md', "BRENDA's mean paper-wise F1 is 0.76",
         ['mean paper-wise F1 of {0.76}']),
        ('lit.sdd', '6.3 million records from 20 million papers', 'Self-Driving Datasets [15]',
         pl + 'top_journal_20261021/nmeth/similar/SIMILAR_PAPERS.md', 'agents read 20 M papers into 6.3 M records',
         ['built 6.3 million records from 20 million papers']),
        ('lit.harvest_records', '3.15 million', 'HARVEST binding records from patents [16]',
         pl + 'top_journal_20261021/nmeth/similar/SIMILAR_PAPERS.md', 'into 3.15 M binding records',
         ['and 3.15 million binding records']),
        ('lit.harvest_right', '92% of 3,706', 'HARVEST right in hand-checked 1,000-fold disagreements with BindingDB [16]',
         pl + 'top_journal_20261021/nmeth/similar/SIMILAR_PAPERS.md',
         'in 3,706 hand-checked 1000x nM/µM disputes HARVEST was right 92% of the time',
         ['right in 92% of 3,706 hand-checked 1,000-fold']),
        ('lit.litmof', '9,227', 'database structures LitMOF repaired against their papers [22]',
         pl + 'top_journal_20261021/nmeth/similar/angle3_newest.md', 'LitMOF: 9,227', ['LitMOF repaired 9,227']),
        ('lit.spot', '21.1% of 91, 6.1% precision', 'SPOT: the best model found 21.1% of 91 errata-level errors at 6.1% '
         'precision [26]', pl + 'top_journal_20261021/nmeth/priorart.md', '91 errata/retraction-level errors',
         ['found 21.1% of 91', 'at 6.1% precision']),
        ('lit.machacek', '42.4% of 7,835', 'blinded experts sided with a language model in disagreements with a published '
         'systematic review [27]', pl + 'top_journal_20261021/nmeth/similar/angle3_newest.md',
         'experts favoured the LLM in 42.4% of 7,835 conflicts', ['in 42.4% of 7,835']),
    ]
    for key, val, what, src, needle, forms in lit:
        E(key, val, what, src, needle=needle, kind='literature', state='ON FILE', show=val, forms=forms)
    S.evidence(pl + 'top_journal_20261021/nmeth/priorart.md')
    must(S.evidence(pl + 'top_journal_20261021/nmeth/priorart.md'), '6.1% precision', 'priorart.md')
    must(S.evidence(pl + 'top_journal_20261021/nmeth/similar/SIMILAR_PAPERS.md'), 'Romanov-Niederer: 7 frontier models',
         'SIMILAR_PAPERS.md')


def sec_corpus():
    lists = [('sources/fulltext_never_read.txt', 'corpus.fulltext_never_read', 'papers with full text on disk that the '
              'earlier catalogue never read', ['never read (3,406)']),
             ('sources/fulltext_read_before.txt', 'corpus.fulltext_read_before', 'papers the earlier catalogue read only for '
              'selected rows', ['selected rows (3,071)']),
             ('sources/db_citations.txt', 'corpus.db_citations', 'BRENDA-cited papers not on disk', ['disk\n(28,621)',
                                                                                                    '(28,621)']),
             ('sources/nopmid_ids.txt', 'corpus.no_pmid', 'BRENDA-cited references without a PubMed identifier',
              ['identifier (3,726)']),
             ('sources/intenzydb_pmids.txt', 'corpus.intenzydb', 'papers behind IntEnzyDB', ['IntEnzyDB (2,036)']),
             ('sources/strenda_pmids.txt', 'corpus.strenda', 'papers behind STRENDA DB', ['STRENDA DB (48)']),
             ('sources/discovered_europepmc_20261014.txt', 'corpus.discovered', 'papers no database cites, found by a '
              'Europe PMC query for kcat and Km terms, queued on 14 October', ['(30,814 queued'])]
    for rel, key, what, forms in lists:
        n = sum(1 for ln in S.lines(rel) if ln.strip() and not ln.startswith('#'))
        L.add(key, n, what + f' (non-blank, non-comment lines of {rel})', kind='snapshot', source=rel, forms=forms)


def sec_constants():
    cp = git('show', 'HEAD:catlog.py')
    head = f'catlog.py at HEAD {S.head[:7]}'
    ss = git('show', 'HEAD:tools/scale_sweep.py')
    vs = git('show', 'HEAD:tools/vmax_sweep.py')

    def c(key, pattern, text, what, src, conv=lambda x: x, show=None, forms=()):
        m = re.search(pattern, text, re.S)
        if not m:
            ERRORS.append(f'constant {key}: pattern not found in {src}')
            v = None
        else:
            v = conv(m.group(1))
        ln = text[:m.start()].count('\n') + 1 if m else None
        L.add(key, v, what, kind='code', source=f'{src}:{ln}', show=show if show and v is not None else None,
              forms=forms)
    c('const.audit_rate', r'AUDIT_RATE = ([\d.]+)', cp, 'share of the values added since the last audit that an audit '
      'samples', head, lambda x: float(x), show='7%', forms=['sized at 7% of the values', 'sampled 7% of them'])
    c('const.audit_min', r'max\((\d+), math\.ceil\(AUDIT_RATE', cp, 'smallest audit sample', head, int,
      forms=['(at least 12)', 'at least 12 [n47]'])
    c('const.audit_due', r'AUDIT_DUE = (\d+)', cp, 'values added since the last audit after which an audit falls due', head,
      int, forms=['after 300 values had been added'])
    c('const.audit_group', r'ids\[i:i \+ (\d+)\] for i in range', cp, 'rows per auditor', head, int,
      forms=['each group of 4 rows'])
    c('const.limit_kcat', r"LIMITS = \{'kcat': ([\de.+]+)", cp, 'physical limit on kcat (s^-1)', head, float,
      show='10^8', forms=['10^8 s^-1 for kcat'])
    c('const.limit_km', r"LIMITS = \{'kcat': [\de.+]+, 'Km': ([\de.+]+)", cp, 'physical limit on Km (mM)', head, float,
      show='10^4', forms=['10^4 mM for Km'])
    c('const.limit_kcm', r"'kcat/Km': ([\de.+]+)\}", cp, 'physical limit on kcat/Km (mM^-1 s^-1), also the derived '
      'kcat/Km flag', head, float, show='10^7', forms=['10^7 mM^-1 s^-1 (10^10 M^-1 s^-1)', 'flagged above 10^7'])
    c('const.sig_figs', r"value = float\(f'\{value:\.(\d)g\}'\)", cp, 'significant figures stored', head, int,
      forms=['to 6 significant figures'])
    c('const.row_id_hex', r"hexdigest\(\)\[:(\d+)\]", cp, 'hexadecimal digits of a row identifier', head, int,
      forms=['(16 hexadecimal digits'])
    c('const.quote_gap', r'gaps under (\d+) characters', cp, 'largest gap between quote tokens', head, int,
      forms=['gaps under 400 characters'])
    c('const.title_share', r'/ len\(words\) >= ([\d.]+)', cp, 'share of title content words that must occur in the '
      'file\'s first characters', head, float, show='80%', forms=['only if 80% of the content words'])
    c('const.title_chars', r'squash\(text\[:(\d+)\]\)', cp, 'characters searched for the title', head, int,
      forms=['first 8,000 characters'])
    c('const.closure_factor', r'min\(4\.0, ([\d.]+) \* \(1 \+ sum\(rel_uncertainty', cp, 'closure tolerance factor', head,
      float, forms=['a fold difference of 1.5 × (1 + the sum'])
    c('const.closure_cap', r'min\(([\d.]+), 1\.5 \* \(1 \+ sum\(rel_uncertainty', cp, 'closure fold cap', head, float,
      show='4', forms=['capped at 4'])
    c('const.duplicate', r'abs\(a - b\) <= ([\d.]+) \* max\(a, b\)', cp, 'relative difference under which a second row '
      'in a slot is a duplicate', head, float, show='2%', forms=['a value within 2%'])
    c('const.ceiling', r'TAIL = ([\de.+]+)', cp, 'diffusion ceiling reviewed (mM^-1 s^-1)', head, float, show='10^6',
      forms=['at or above 10^6 mM^-1 s^-1'])
    dbc = git('show', 'HEAD:tools/dbcheck.py')
    c('const.db_threshold', r'by ([\d.]+)x or more', dbc, 'fold difference from a database value that sends a value to a '
      'paper check', 'tools/dbcheck.py', float, show='1.5-fold',
      forms=['numbers 1.5-fold or more apart for the same value', 'difference of 1.5-fold or more',
             'numbers 1.5-fold or more apart and code', 'gave one paper numbers 1.5-fold or more apart',
             'differs by 1.5-fold or more'])
    c('const.evidence_chars', r'EVIDENCE_MAX = (\d+)', dbc, 'characters of evidence a database check may give',
      'tools/dbcheck.py', int, forms=['at most 240 characters'])
    c('const.checks_per_paper', r'ASK_MAX = (\d+)', dbc, 'paper checks the loop asks for per paper', 'tools/dbcheck.py',
      int, forms=['(up to 2 checks per paper)'])
    dcm = git('show', 'HEAD:tools/dbcompare.py')
    c('const.db_ph', r'pH within ([\d.]+)', dcm, 'pH window for pairing a database value', 'tools/dbcompare.py', float,
      forms=['pH within 0.3'])
    c('const.db_temp', r'temperature within ([\d.]+) C', dcm, 'temperature window (°C)', 'tools/dbcompare.py', float,
      forms=['temperature within 2.5 °C'])
    fc = S.evidence('paper/figures/database_errors/factor_counts.py')
    must(fc, '{b + a * math.log10(t) for b in (-3, 0, 3) for t in (60, 3600) for a in (1, -1)}', 'factor_counts.py')
    L.add('const.unit_factor_set', 'powers of ten other than 1; 60 or 3,600 either way, alone or times or over 1,000',
          'the unit factors of Fig. 4 (FACTORS in factor_counts.py)', kind='code',
          source='paper/figures/database_errors/factor_counts.py', show='10^b; 60, 3,600 (×/÷ 1,000)',
          forms=['or 60 or 3,600 either way, alone or times or over 1,000'])
    c('const.unit_factor_tol', r'abs\(10 \*\* \(x - f\) - 1\) <= ([\d.]+) and f != 0', fc, 'how close a ratio must be '
      'to a unit factor (Fig. 4)', 'paper/figures/database_errors/factor_counts.py', float, show='1%',
      forms=['lie within 1% of an exact unit factor'])
    c('const.scale_factors', r'(60\^a x 1000\^b)', ss, 'the unit factors of the unit-factor sweep', 'tools/scale_sweep.py',
      show='60^a × 1000^b', forms=['a unit factor 60^a × 1000^b'])
    c('const.hash_prefix', r'sha256\(.*?\)\.hexdigest\(\)\[:(\d+)\]', cp, 'characters of the stamped prompt hashes',
      head, int, forms=['12-character SHA-256', '12-character SHA-256 prefixes of the reading prompt, verification'])
    E('const.reprint_min_shared', 3, 'specific printed values two papers must share to be checked as a reprint pair',
      'paper/manuscript/supp_note_1_system.md', needle='296; 3 or more; 973', kind='code', state='ON FILE',
      forms=['sharing 3 or more values'])
    c('const.vmax_divisor', r'(/ 60)', vs, 'the maximal-rate bound: Vmax × subunit mass / 60', 'tools/vmax_sweep.py',
      show='60', forms=['subunit mass (kDa) / 60'])
    L.add('const.refused_forms', '"× 10" with no exponent; M^-2 s^-1 "kcat/Km"', 'printed forms code refuses '
          '(tools/units.py)', kind='code', source='tools/units.py; CLAUDE.md "The loop"', show='× 10; M^-2 s^-1',
          forms=['a "× 10" whose exponent', 'an M^-2 s^-1 "kcat/Km"'])
    dm = git('show', 'HEAD:prompts/dbcheck.md')
    n_codes = len(re.findall(r'^\| `[a-zA-Z_]+` \|', dm, re.M))
    L.add('const.cause_codes', n_codes, 'cause codes a database check may give (rows of the code table in '
          'prompts/dbcheck.md)', kind='code', source='prompts/dbcheck.md', forms=['one of 11 cause codes'])
    rm = git('show', 'HEAD:prompts/read.md')
    c('const.read_dpi', r'pdftoppm -r (\d+)', rm, 'resolution of the page images readers render for a GLYPH WARNING '
      'text', 'prompts/read.md', int, forms=['at 200 dpi'])
    vm = git('show', 'HEAD:prompts/verify.md')
    c('const.verify_fold', r'A kcat/Km ≥(\d)× away from kcat ÷ Km', vm, 'printed kcat/Km against kcat ÷ Km that sends '
      'the verifier back to all three cells', 'prompts/verify.md', int, show='5-fold', forms=['A printed kcat/Km 5-fold'])
    ss = git('show', 'HEAD:tools/scale_sweep.py')
    c('const.scale_window', r'TOL, TOL_MAX = ([\d.]+),', ss, 'window around a unit factor in the unit-factor sweep',
      'tools/scale_sweep.py', float, show='10%', forms=['flags F within 10% of a unit factor'])
    sj = git('show', 'HEAD:.claude/workflows/catlog-scale.js')
    c('const.refuters', r'refuted by (\d) independent checkers', sj, 'independent refuters per proposed unit change',
      '.claude/workflows/catlog-scale.js', int,
      forms=['each upheld by three refuters', '3 refuters examined each', 'with 3 refuters per proposed change',
             'only if all 3 voted'])
    c('const.max_refuted', r'MAX_REFUTED = (\d)', sj, 'refuters that may refute a change that is still applied',
      '.claude/workflows/catlog-scale.js', int, forms=['and at most 1 refuted'])
    vs = git('show', 'HEAD:tools/vmax_sweep.py')
    c('const.vmax_fold', r'FOLD = ([\d.]+)', vs, 'how far above the maximal-rate bound a kcat is flagged',
      'tools/vmax_sweep.py', float, show='5-fold', forms=['5-fold or more above it'])
    bj = git('show', 'HEAD:.claude/workflows/catlog-batch.js')
    c('const.dead_stop', r'const DEAD_STOP = (\d+)', bj, 'dead steps in a row that stop every lane',
      '.claude/workflows/catlog-batch.js', int, forms=['three dead steps'])
    bm = git('show', 'HEAD:.claude/commands/batch.md')
    c('const.lanes', r'otherwise (\d+)(?: \([^)]*\))?\. No upper', bm, 'default lanes of a batch', '.claude/commands/batch.md', int,
      forms=['(6 by default)'])
    aj = git('show', 'HEAD:.claude/workflows/catlog-audit.js')
    c('const.auditors_live', r'Number\(args && args\.lanes\) \|\| (\d+)\)', aj, 'auditors at a time (the default of args.lanes)',
      '.claude/workflows/catlog-audit.js', int,
      forms=['at most 3 at a time'])
    sn = 'paper/manuscript/supp_note_1_system.md'
    for key, v, what, needle, forms in (
            ('const.bootstrap', '2,000 resamples; seeds 7, 11, 20261012, 5', 'bootstrap resamples and seeds of the '
             'benchmark, the corrected estimates, the reviewer-agreement and the clustered audit intervals',
             '| n75 | 95%; 2,000; 7; 11; 20261012; 5 |',
             ['2,000 times', '(seed 7)', '(seed 11)', '(seed 20261012)', '(seed 5)']),
            ('const.review_seeds', '20261015, 20261029, 20261030', 'seeds of the review packs', '(seeds 20261015, 20261029, '
             '20261030)', ['(seeds 20261015, 20261029 and 20261030)']),
            ('const.glyph_sample', '15 of 120; 1,000-fold', 'sampled library PDFs whose text layer prints µ as m (a silent 1,000-fold '
             'Km error)', '| n12 | 1,000-fold; 15 of 120 |', ['15 of 120 sampled library', 'a silent 1,000-fold error']),
            ('const.wrong_structures', '48', 'wrong structures that led to the name-fit rule (11 October)', '| n30 | 48 |',
             ['after 48 wrong structures']),
            ('const.versions', 'OPSIN 2.9.0, RDKit 2025.09.1', 'reference tool versions', '| n29a | 7 October 2026; 2.9.0; '
             '2025.09.1 |', ['OPSIN was version 2.9.0', 'RDKit 2025.09.1']),
            ('const.lanes_papers', '2L', 'papers a batch claims for L lanes', '| n62 | 2L; 6; 3; 20%; 15 GB |',
             ['claimed 2L papers']),
            ('const.arms', '7 (A0-A6)', 'arms of the planned evaluation', '| n74 | 7 (A0-A6); 1,000 |',
             ['will compare 7 arms'])):
        E(key, v, what, sn, needle=needle, kind='code' if key != 'const.arms' else 'plan', state='ON FILE', show=v,
          forms=forms)


def sec_plan():
    wl = 'paper/planning/top_journal_20261021/nmeth/template/WORKLIST.md'
    pp = 'paper/planning/w1_kill_test/PAPERS.md'
    rn = 'paper/planning/w1_kill_test/RUN.md'
    for key, v, what, src, needle, forms in (
            ('plan.dev_papers', 165, 'development papers W1 reads (107 Co-Scientist and 59 EnzyExtract, 1 in both)', pp,
             '**165 papers**', ['the 165 development papers', 'the 165 gold papers']),
            ('plan.kill_rule', 'A2 ÷ A6 ≥ 2.0, 95% CI above 1', 'W1\'s rule: stop unless A2\'s consequential errors per 1,000 '
             "values are at least twice A6's with the paired, paper-clustered 95% CI above 1", rn,
             'R ≥ 2.0 and the lower end', ['95% CI above 1']),
            ('plan.post_cutoff', 50, 'post-cutoff papers people curate blind (W7)', wl,
             'Two people curate 50 kinetics papers', ['50 of them published after']),
            ('plan.residual', '1,500-2,000', 'random stored values people judge for the residual and the verifier\'s '
             'false-confirm rate (W10, W12)', wl, '1,500-2,000-value residual sample',
             ['1,500-2,000 random stored values', '1,500-2,000 of them random']),
            ('plan.people_items', 'about 3,000', 'items blinded people judge (W12)', wl, 'Items, about 3,000 in all',
             ['about 3,000 items']),
            ('plan.replay', 500, 'random corpus papers the frozen harness replays (W10)', wl,
             'at least 500 random corpus papers', ['frozen replay of 500 random']),
            ('plan.skempi', 100, 'SKEMPI 2.0 papers of the second field (W6)', wl, '≥100 papers',
             ['at least 100 SKEMPI 2.0 papers']),
            ('plan.adaptation_days', 5, 'working days of the timeboxed adaptation (W6)', wl,
             '5-working-day timeboxed adaptation', ['adaptation of 5 working days']),
            ('plan.stability', 50, 'protein-stability papers (W17)', wl, 'ThermoMutDB, 50 papers',
             ['protein stability, 50 papers']),
            ('plan.outside', 'about 20', 'papers an outside group runs (W24)', wl, 'runs about 20 papers',
             ['run on about 20 papers'])):
        E(key, v, what, src, needle=needle, kind='plan', state='planned', show=fmt(v), forms=forms)


# ===================================================================================================== 14. the draft: where each key is printed
TARGET = ('Abstract', 'Introduction', 'Results', 'Discussion', 'Box 1', 'Methods')
NUM = re.compile(r'(?<![\w.^⁻])[−-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?')
MONTHS = 'January|February|March|April|May|June|July|August|September|October|November|December'


def draft_map():
    raw = open(DRAFT, encoding='utf-8').read()
    S.draft_sha = hashlib.sha256(raw.encode()).hexdigest()
    lines = raw.split('\n')
    sec, sub = [], []
    cur = cs = ''
    for ln in lines:
        if ln.startswith('## '):
            cur, cs = ln[3:].strip(), ''
        elif ln.startswith('### '):
            cs = ln[4:].strip()
        sec.append(cur)
        sub.append(cs)
    flat = raw.replace('\n', ' ')
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln) + 1)

    def line_of(pos):
        lo, hi = 0, len(lines)
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if starts[mid] <= pos:
                lo = mid
            else:
                hi = mid
        return lo + 1
    target = lambda s: any(s.startswith(t) for t in TARGET)
    return raw, flat, lines, sec, sub, line_of, target


def short(sec):
    return {'Abstract': 'Abstract', 'Introduction': 'Intro', 'Results': 'Results', 'Discussion': 'Discussion',
            'Methods': 'Methods'}.get(sec, 'Box 1' if sec.startswith('Box 1') else sec)


TOK = re.compile(r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?')
WORDS = {w: i for i, w in enumerate('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen '
                                     'fifteen sixteen seventeen eighteen nineteen twenty'.split())}
WORDS.update({'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90})


def word_number(s):
    parts = s.lower().split('-')
    if all(p in WORDS for p in parts):
        return sum(WORDS[p] for p in parts)
    return None


def first_number(s):
    m = TOK.search(s or '')
    if m:
        return m.group(0)
    w = word_number((s or '').strip())
    return str(w) if w is not None else None


def same_number(drafted, show):
    """Does the drafted number occur among the numbers of the key's shown value?"""
    a = first_number(drafted or '')
    if a is None:
        return None
    toks = [float(t.replace(',', '')) for t in TOK.findall(show or '')]
    w = word_number(str(show or '').strip())
    if w is not None:
        toks.append(float(w))
    if not toks:
        return None
    x = float(a.replace(',', ''))
    return any(abs(x - t) <= 1e-9 * max(1.0, abs(t)) for t in toks)


def sec_draft():
    raw, flat, lines, sec, sub, line_of, target = draft_map()
    covered = set()
    S.drafted, S.form_missing = [], []
    for key, r in L.rows.items():
        r['drafted'] = []
        for f in r['forms']:
            f, _, override = f.partition('=>')
            m = re.search(r'\{([^}]*)\}', f)
            mine = override or (m.group(1) if m else None)
            phrase = re.sub(r'[{}]', '', f).replace('\n', ' ')
            hits = []
            st = 0
            while True:
                i = flat.find(phrase, st)
                if i < 0:
                    break
                st = i + 1
                ln = line_of(i)
                if not target(sec[ln - 1]):
                    continue
                if NUM.match(phrase) and phrase == first_number(phrase):            # a bare number: whole token only
                    if (i > 0 and (flat[i - 1].isdigit() or flat[i - 1] in ',.')) or \
                            (i + len(phrase) < len(flat) and (flat[i + len(phrase)].isdigit()
                                                              or flat[i + len(phrase)] == ',' and
                                                              flat[i + len(phrase) + 1:i + len(phrase) + 2].isdigit())):
                        continue
                hits.append(i)
            if not hits:
                S.form_missing.append((key, f))
                continue
            for i in hits:
                ln = line_of(i)
                d = mine if mine else (first_number(phrase) or phrase)
                for mm in NUM.finditer(flat, i, i + len(phrase)):
                    covered.add(mm.start() if mm.group(0)[0].isdigit() else mm.start() + 1)
                ok = same_number(d, r['show']) if first_number(d or '') else None
                rec = {'key': key, 'section': short(sec[ln - 1]), 'subsection': sub[ln - 1], 'line': ln,
                       'phrase': phrase, 'drafted': d, 'ledger': r['show'], 'same': ok}
                r['drafted'].append(rec)
                S.drafted.append(rec)
    # every number token in the target sections that no key covers
    unc = []
    in_bracket = []
    for m in re.finditer(r'\[[^\]\[]*\]', flat):
        in_bracket.append((m.start(), m.end(), m.group(0)))
    for m in NUM.finditer(flat):
        pos = m.start() if m.group(0)[0].isdigit() else m.start() + 1
        ln = line_of(pos)
        if not target(sec[ln - 1]) or pos in covered:
            continue
        tok = m.group(0).lstrip('−-')
        ctx = flat[max(0, m.start() - 40):m.end() + 40]
        cat = trivial(flat, m.start(), m.end(), tok, in_bracket)
        unc.append({'line': ln, 'section': short(sec[ln - 1]), 'token': tok, 'kind': cat, 'context': ctx})
    S.uncovered = unc


def trivial(flat, a, b, tok, brackets):
    before, after = flat[max(0, a - 30):a], flat[b:b + 25]
    if before.endswith('^') or before.endswith('^-') or before.endswith('^−'):
        return 'unit exponent'
    if re.search(r'(?:per|every)[ -]$', before) and tok == '1,000':
        return 'unit of a rate (per 1,000)'
    if re.search(r'×\s?(?:1/)?$', before) or (tok == '1' and after.startswith('/') and before.endswith('×')):
        return 'unit-factor name (×10, ×1/1,000, ...)'
    if before.endswith('SHA-'):
        return 'algorithm name'
    if before.endswith('CC BY '):
        return 'licence name'
    if 'stejnefibrase' in before:
        return 'protein name'
    if after.startswith('th'):
        return 'ordinal'
    if 'claude-' in flat[max(0, a - 20):a]:
        return 'model name'
    if before.endswith('BRENDA '):
        return 'release name'
    if tok == '95' and re.match(r'%\s*(?:CI|interval|confidence|paper-clustered)', after):
        return 'confidence level'
    if re.search(r'(?:Tables?|Figs?\.|Figures?)\s+[\w.]+(?:,\s*|\s+and\s+)$', before):
        return 'figure, table, section or page'
    for s, e, txt in brackets:
        if s <= a < e and re.fullmatch(r'\[[\d,–\- ]+\]', txt):
            return 'reference number'
        if s <= a < e and re.fullmatch(r'\[n\d+[a-z]?(?:, n\d+[a-z]?)*\]', txt):
            return 'ledger tag'
    if re.match(rf'\s*(?:{MONTHS})', after) or re.match(rf'(?:[-–]\d+|\s+to\s+\d+)\s+(?:{MONTHS})', after):
        return 'date'
    if re.fullmatch(r'(?:19[6-9]\d|20[0-3]\d)', tok) and not re.match(r'[,.]\d', after):
        return 'year'
    if re.match(r'\d\d:\d\d', flat[a:a + 5]) or re.search(r'\d\d:$', before):
        return 'time'
    if re.search(r'(?:Figs?\.|Fig\.|Figure|Tables?|Box|section|sections|ED Fig\.|Extended Data Figs?\.|Extended Data Tables?|'
                 r'Supplementary Note|Supplementary Tables? S?|p\.|pp\.|ref\.|refs\.|Note)\s*$', before):
        return 'figure, table, section or page'
    if re.match(r'[a-d]\b', after) and re.search(r'Fig\.\s*$', before[:-0] if False else before):
        return 'figure panel'
    if len(tok.replace(',', '')) >= 7 and ',' not in tok and '.' not in tok:
        return 'PMID or identifier'
    if tok in ('1', '2', '3', '4', '5', '6', '7', '8', '9') and re.match(r'[⁰¹²³⁴⁵⁶⁷⁸⁹⁻ⁿ]', after):
        return 'exponent'
    if re.match(r'[⁰¹²³⁴⁵⁶⁷⁸⁹⁻ⁿ]|\^', after) and tok == '10':
        return 'power of ten notation'
    if re.search(r'(?:claude-[a-z]+-|Claude Code )\d?$', before) or re.match(r'-\d', after) and 'claude' in before:
        return 'model or version name'
    if re.search(r'(?:A|W|S|n)$', before):
        return 'label'
    return 'NOT IN LEDGER'


# ===================================================================================================== 15. outputs
def write_outputs(stable, after):
    keys = list(L.rows.values())
    snap = {'built': S.started.strftime('%Y-%m-%d %H:%M:%S %z'),
            'finished': datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z'),
            'git_head': S.head, 'git_head_line': S.head_line,
            'core_files': {f: S.files.get(f) for f in CORE},
            'core_files_unchanged_during_build': stable, 'core_sha256_at_end': after,
            'other_files': {f: v for f, v in S.files.items() if f not in CORE},
            'status_run': {'when': S.status_when, 'seconds': S.status_seconds, 'output': S.status_text},
            'export_is_the_snapshot_catalog': S.export_ok,
            'draft': {'path': 'paper/manuscript/draft_v1.md', 'sha256': S.draft_sha}}
    differ = [d for d in S.drafted if d['same'] is False]
    out = {'snapshot': snap, 'keys': {r['key']: {k: v for k, v in r.items() if k != 'forms'} for r in keys},
           'drafted_differs': differ, 'forms_not_found': S.form_missing,
           'uncovered_numbers': [u for u in S.uncovered if u['kind'] == 'NOT IN LEDGER'],
           'uncovered_trivial_counts': collections.Counter(u['kind'] for u in S.uncovered if u['kind'] != 'NOT IN LEDGER'),
           'errors': ERRORS}
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    md = []
    a = md.append
    a('# Numbers ledger for draft v1 (one snapshot)')
    a('')
    a(f'Built by `paper/manuscript/numbers_build.py` on {snap["built"]} (finished {snap["finished"]}). Machine-readable '
      'copy: `numbers.json`. Do not edit by hand: rerun the script.')
    a('')
    a('## Snapshot')
    a('')
    a(f'- **git HEAD:** `{S.head}` ({S.head_line})')
    for f in CORE:
        x = S.files[f]
        a(f'- **{f}:** sha256 `{x["sha256"]}`, {x["bytes"]:,} bytes, modified {x["mtime"]}, {x["git"]} '
          f'(last commit {x["last_commit"]})')
    a(f'- **Unchanged while the build ran:** {"yes" if stable else "NO: rerun"} (the four files hashed again at the end).')
    a(f'- **Export:** `catlog_wide.jsonl` sha256 `{S.files["catlog_wide.jsonl"]["sha256"]}`, written '
      f'{S.files["catlog_wide.jsonl"]["mtime"]}; its row ids are exactly catalog.jsonl\'s: '
      f'{"yes" if S.export_ok else "NO"}.')
    a(f'- **`python3 catlog.py status`**, run by the build: {S.status_when}; "catalog and log agree": '
      f'{"yes" if S.st.get("agree") else "NO"}.')
    a(f'- **Draft scanned:** `draft_v1.md` sha256 `{S.draft_sha}`.')
    a('- Other files read (each hashed as read) are listed with their sha256 in `numbers.json` (snapshot.other_files).')
    a('')
    a('**Kinds.** snapshot = computed here from the files above; window = the same files restricted to a dated window; '
      'frozen = a one-time result read from the evidence file named (the transcripts or agent runs behind it cannot be '
      're-run from the repository); literature = a figure from another paper, read from the checked note named; code = '
      'a constant read from the code or prompt at HEAD; plan = a planned number; fact = printed in a case paper, from '
      'the checked case evidence. **check** = the same definition recomputed from the snapshot (for frozen and window '
      'keys), or the status line\'s count (for snapshot keys). **State** DEV = development number (frames, never '
      'carries a claim).')
    a('')
    a('**In the draft** lists every phrase of draft_v1.md the key covers: section, line, the number as drafted, and '
      '= (same as the ledger) or ≠ (differs).')
    a('')
    groups = collections.OrderedDict()
    for r in keys:
        groups.setdefault(r['key'].split('.')[0], []).append(r)
    names = {'status': 'Status line', 'queue': 'Queue', 'audit': 'Audits', 'review': 'Human review', 'cat': 'Catalogue',
             'abstract': 'Abstract', 'conv': 'Conversion units', 'stamp': 'Provenance stamps', 'rule': 'Rules and the '
             'rows read before them', 'sweep': 'Sweeps', 'closure': 'Closure check', 'ceiling': 'Diffusion ceiling',
             'enrich': 'Enrichment', 'db': 'Database comparison (Fig. 4)', 'flow': 'Every value through the checks',
             'throughput': 'Throughput', 'exposure': 'Exposure log', 'prompts': 'Prompts', 'code': 'Code',
             'example': 'Worked example (Fig. 1b)', 'case': 'Case papers', 'box': 'Box 1 and the case sentences (printed facts)',
             'rederive': 'Re-derived one-pass numbers (L13, L32, L46, 5.6)', 'ledger': 'Error ledger',
             'dev': 'Development numbers (Fig. 3, benchmark, blind re-read, agent logs)', 'cases': 'Agent cases',
             'cost': 'Cost', 'lit': 'Literature', 'corpus': 'Corpus', 'const': 'Code constants', 'plan': 'Plans (W-tasks)'}
    for g, rs in groups.items():
        a(f'## {names.get(g, g)}')
        a('')
        a('| Key | Value | Definition | Kind, state, window | Source | Code | check | In the draft |')
        a('|---|---|---|---|---|---|---|---|')
        for r in rs:
            dr = '; '.join(f"{d['section']} L{d['line']} {d['drafted']} {'=' if d['same'] else '≠' if d['same'] is False else ''}"
                           for d in r['drafted'])
            what = r['what'] + (f' (base: {r["base"]})' if r['base'] else '') + (f' Note: {r["note"]}' if r['note'] else '')
            chk = '' if r['check'] is None else fmt(r['check']) if not isinstance(r['check'], float) else f'{r["check"]:g}'
            cells = [f'`{r["key"]}`', str(r['show']), what, f'{r["kind"]}, {r["state"]}, {r["window"]}',
                     f'`{r["source"]}`' if len(r['source']) < 120 else r['source'], r['code'], chk, dr]
            a('| ' + ' | '.join(c.replace('|', '/').replace('\n', ' ') for c in cells) + ' |')
        a('')
    a('## Drafted numbers that differ from the ledger')
    a('')
    a('Each line: where draft_v1.md prints a number for a key and the number differs from the ledger value. '
      '`numbers_conflicts.md` says which definition each sentence should use.')
    a('')
    a('| Section | Line | Phrase | Drafted | Key | Ledger |')
    a('|---|---|---|---|---|---|')
    for d in differ:
        a(f"| {d['section']} | {d['line']} | {d['phrase'].replace('|', '/')} | {d['drafted']} | `{d['key']}` | {d['ledger']} |")
    a('')
    a('## Coverage of the draft')
    a('')
    nl = [u for u in S.uncovered if u['kind'] == 'NOT IN LEDGER']
    cnt = collections.Counter(u['kind'] for u in S.uncovered if u['kind'] != 'NOT IN LEDGER')
    a(f'Number tokens in the abstract, Introduction, Results, Box 1, Discussion and Methods that no key covers: '
      f'{len(nl)} not classed as trivial; trivial ones by kind: ' + ', '.join(f'{k} {v}' for k, v in cnt.most_common())
      + '.')
    a('')
    if nl:
        a('| Section | Line | Token | Context |')
        a('|---|---|---|---|')
        for u in nl:
            a(f"| {u['section']} | {u['line']} | {u['token']} | {u['context'].replace('|', '/')} |")
        a('')
    if S.form_missing:
        a('Phrases a key names that the draft no longer prints: ' + '; '.join(f'`{k}`: "{f}"' for k, f in S.form_missing))
        a('')
    a('## Build problems')
    a('')
    a('\n'.join(f'- {e}' for e in ERRORS) if ERRORS else 'None.')
    a('')
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))


def main():
    t0 = time.time()
    before = {f: None for f in CORE}
    sec_status()
    sec_log()
    sec_backfill()
    sec_catalog()
    sec_audits()
    sec_bounds()
    sec_queue()
    sec_export()
    sec_dbcheck()
    sec_fig4()
    sec_flow()
    sec_logcounts()
    sec_exposure()
    sec_git()
    sec_example()
    sec_cases()
    sec_rederive()
    sec_ledger()
    sec_layers()
    sec_h2h()
    sec_blind()
    sec_logs()
    sec_case_coding()
    sec_sweeps_frozen()
    sec_r2_random()
    sec_cost()
    sec_literature()
    sec_corpus()
    sec_constants()
    sec_plan()
    after = {f: sha_file(f) for f in CORE}
    stable = all(after[f] == S.files[f]['sha256'] for f in CORE)
    if not stable:
        ERRORS.append('a core file changed while the build ran: the ledger mixes two states; rerun')
    sec_draft()
    write_outputs(stable, after)
    nl = sum(1 for u in S.uncovered if u['kind'] == 'NOT IN LEDGER')
    print(f'{len(L.rows)} keys; {sum(1 for d in S.drafted if d["same"] is False)} drafted numbers differ from the ledger; '
          f'{nl} draft numbers not in the ledger; {len(S.form_missing)} phrases not found; {len(ERRORS)} build problems; '
          f'snapshot stable: {stable}; {time.time() - t0:.0f} s')
    for e in ERRORS:
        print('  problem:', e)
    print('wrote', OUT_JSON, 'and', OUT_MD)
    return 0 if stable else 1


if __name__ == '__main__':
    sys.exit(main())
