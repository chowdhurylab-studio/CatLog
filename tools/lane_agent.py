#!/usr/bin/env python3
"""What a Chrome agent of the saved workflow catlog-chrome-lanes runs besides the browser (stdlib only).

  lane_agent.py list KEY I J PROG [BUILT]
                                     the papers of work/downloads/lanes.json[KEY][I:J] still to get, one per line
                                     (id TAB doi TAB url), then '# slice N built STAMP: ...'. Left out: papers/<id>.pdf
                                     exists, a PMID<id>_* file waits in ~/Downloads, or PROG already has a final line
                                     for it. '# ERROR' when lanes.json's stamp is not BUILT (rebuilt: indices moved),
                                     and in a method-A lane when another run's method-A lane is live (its snapshot
                                     changed in the last 10 min: both would take files from one ~/Downloads);
                                     '# LOW' when memory or disk is short.
  lane_agent.py snap PROG            remember what is in ~/Downloads (method-A lanes; list does it, log and take after)
  lane_agent.py log PROG ID RESULT DETAIL [HOST]
                                     append the paper's progress line to PROG
  lane_agent.py take PROG ID LANE DOI [HOST] [--buy] [--retry]
                                     after a method-A click (Chrome picks the file name): wait for the download, find
                                     the file it saved (a new name that is ours, PMID<id>_*, or a .pdf or a name with no
                                     extension: the user's other downloads, .html .zip .json ..., are never taken),
                                     check it is a PDF, rename it PMID<id>_<lane>.pdf (never over another file) and
                                     append the progress line. A download that is a web page (bot check, login, error)
                                     is moved to work/downloads/html/ and is a STOP. A click
                                     that saved nothing: take waits about a minute more (a late file still counts);
                                     the paper's first empty click prints result 'retry' (no line); its second (the
                                     take after that 'retry'; --retry is optional and counts only for the paper the
                                     'retry' named) is an error line 'clicked twice, no file', and the lane goes on.
                                     In every method-A lane but FREE_A the second paper in a row of this progress file
                                     (one chunk) ending so (4 empty clicks; no_pdf/no_access papers between them aside)
                                     is the STOP: a site refusing its PDFs (PNAS 10-14, a 403 right after the user's
                                     clear; ASM's PDF 403 of 10-11 looks the same under a click). On J-STAGE (FREE_A)
                                     empty clicks never stop the lane. --buy and no file = no_access, no retry. (Old
                                     ACS lines: ~3.5% of clicks saved nothing once and worked on a click minutes later,
                                     in episodes of ~2 min.)
Progress line: {"id", "result", "detail", "host", "ip", "ts"}; result saved | no_access | no_pdf | error | STOP.
log and take print {"result", "detail", "ip", "campus", "mem_free", "disk_gb", "low"} (campus: the address starts
with CATLOG_CAMPUS_IP_PREFIX, false while that is unset, null when unknown; low: why memory or disk is too short to go on, else '').
Tests: LANE_AGENT_ROOT=<dir> runs against a fake repo root (<dir>/work/downloads, <dir>/papers) and a fake
<dir>/Downloads, with the test address 129.186.0.1 instead of a lookup (and LANE_AGENT_RETRY_WAIT=<s> for the wait).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

TEST_ROOT = os.environ.get('LANE_AGENT_ROOT', '')  # tests only (see the docstring)
ROOT = Path(TEST_ROOT).resolve() if TEST_ROOT else Path(__file__).resolve().parent.parent
DL = ROOT / 'work' / 'downloads'
LANES = DL / 'lanes.json'
SNAPS = DL / 'snaps'  # per progress file: the ~/Downloads names before the next click (.txt), the paper whose click
#                       saved nothing once (.retry); ip.txt: the address, 60 s
HTML = DL / 'html'  # downloads that were web pages, kept for a look (never filed)
DOWNLOADS = ROOT / 'Downloads' if TEST_ROOT else Path.home() / 'Downloads'
RESULTS = ('saved', 'no_access', 'no_pdf', 'error', 'STOP')
PARTIAL = ('.crdownload', '.download', '.part')
METHOD_A = ('acs', 'wiley', 'wiley_sub', 'pnas', 'jstage', 'asm')  # Chrome names the file: `list` takes the first snapshot
FREE_A = ('jstage',)  # J-STAGE: empty clicks never stop it (a check on the page or a web page does); not ASM, whose known
#                      block is a 403 on the PDF (2026-10-11), i.e. an empty click: the PNAS platform, the PNAS rule
A_LIVE = 600  # s: another run's method-A lane whose snapshot changed this recently is live (one ~/Downloads for both)
RETRY_MAX_AGE = 900  # s: a 'retry' older than this (an agent that died before its second click) is forgotten
# s more that take waits after a click that saved nothing (old ACS misses were fixed by clicks minutes later, never
# seen at once; a late file counts; kept under the agents' 2-min Bash limit with take's 12 + 30 s)
RETRY_WAIT = float(os.environ.get('LANE_AGENT_RETRY_WAIT') or 45) if TEST_ROOT else 45
TWICE = 'clicked twice, no file'  # the detail of a paper whose two clicks saved nothing (take reads it back)
PROG = re.compile(r'lane_[a-z_]+_[a-z0-9]+_\d+\.jsonl')
BOT = re.compile(rb'just a moment|__cf_chl|challenge-platform|captcha|verify you are human|access denied|too many requests'
                 rb'|validate user|crawlprevention|are you a robot|client challenge|security verification|unusual (activity|traffic)', re.I)
PAYWALL = re.compile(rb'purchase|buy (this )?article|get access|log ?in|sign ?in|access through your institution', re.I)
MEM_MIN, DISK_MIN = 20, 15  # % memory free, GiB disk free: below either the lanes stop (the Mac ran short on 10-16; disk 20 -> 15 GB, the user 2026-10-21)


def die(msg):
    print(msg)
    sys.exit(2)


def id_in_name(name):
    """The paper id a ~/Downloads name starts with (as catlog.id_in_name): PMID<digits>, or a stand-in NP + 8 hex."""
    m = re.match(r'PMID(\d+)', name, re.I) or re.match(r'(?:PMID)?(NP[0-9A-F]{8})(?![0-9A-Z])', name, re.I)
    return m.group(1).upper() if m else None


def prog_path(p):
    p = Path(p).expanduser().resolve()
    if p.parent != DL.resolve() or not PROG.fullmatch(p.name):
        die(f'progress file must be {DL}/lane_<lane>_<tag>_<start>.jsonl, not {p}')
    return p


def lines(prog):
    out = []
    try:
        for s in prog.read_text(errors='replace').splitlines():
            try:
                j = json.loads(s)
            except ValueError:
                continue
            if isinstance(j, dict):
                out.append(j)
    except OSError:
        pass
    return out


def address(fresh=False):
    """The public IP (cached 60 s for all agents; fresh=True asks again). '' when the lookup fails."""
    if TEST_ROOT:
        return '129.186.0.1'
    f = SNAPS / 'ip.txt'
    try:
        if not fresh and time.time() - f.stat().st_mtime < 60:
            return f.read_text().strip()
    except OSError:
        pass
    try:
        with urllib.request.urlopen('https://api.ipify.org', timeout=6) as r:
            a = r.read(64).decode('ascii', 'replace').strip()
    except Exception:
        return ''
    if not re.fullmatch(r'[0-9a-fA-F.:]{3,45}', a):
        return ''
    SNAPS.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f'ip.{os.getpid()}.tmp')
    tmp.write_text(a)
    os.replace(tmp, f)
    return a


def snap_file(prog):
    return SNAPS / (prog.name + '.txt')


def snap(prog, extra=()):
    SNAPS.mkdir(parents=True, exist_ok=True)
    f = snap_file(prog)
    tmp = f.with_name(f.name + '.tmp')
    tmp.write_text('\n'.join(sorted(set(os.listdir(DOWNLOADS)) | set(extra))) + '\n')
    os.replace(tmp, f)


def retry_file(prog):
    return SNAPS / (prog.name + '.retry')


def retried(prog, pid, said_retry=False):
    """True when this paper's previous click in this progress file already saved nothing: the mark take wrote then
    names this paper and is under 15 min old (or older, when the agent says --retry). A --retry with no mark, or a
    mark for another paper, is not a second click (an agent reusing the last command line on the next paper)."""
    f = retry_file(prog)
    try:
        return f.read_text().strip() == pid and (said_retry or time.time() - f.stat().st_mtime < RETRY_MAX_AGE)
    except OSError:
        return False


def paperish(n):
    """A name a publisher's PDF can have (a partial's suffix set aside): .pdf, or no extension (Chrome's 'download', a
    DOI stem such as pnas.0506491102, an 'Unconfirmed 123' partial). .html .zip .json .csv ... are the user's other
    downloads (10-16: 88 landed while lanes ran, 77 of the week's .html), never this paper's file."""
    n = re.sub(r'\.(crdownload|download|part)$', '', n, flags=re.I)
    ext = re.search(r'\.([a-z][a-z0-9]{0,5})$', n, re.I)
    return not ext or ext[1].lower() == 'pdf'


def arrived(before, ours):
    """New names in ~/Downloads since the snapshot that can be this paper's file: ours (PMID<id>_*, whatever it ends
    in: a web page the click saved has our name), else paperish ones; other lanes' PMID<other id>_* saves left out."""
    return [n for n in os.listdir(DOWNLOADS) if n not in before and not n.startswith('.')
            and (n.upper().startswith(ours) or not id_in_name(n) and paperish(n))]


def other_a_lane(prog):
    """(progress file, seconds) of another run's method-A lane whose snapshot changed in the last A_LIVE s, else None.
    Snapshots are written only by method-A lanes, at every paper; one run starts its method-A lanes one at a time,
    but separate runs do not know of each other (three were live at once on 2026-10-20)."""
    tag, now = prog.name.rsplit('_', 2)[-2], time.time()
    for f in sorted(SNAPS.glob('lane_*.jsonl.txt')):
        p = f.name[:-len('.txt')]
        try:
            age = now - f.stat().st_mtime
        except OSError:
            continue
        if PROG.fullmatch(p) and p.rsplit('_', 2)[-2] != tag and age < A_LIVE:
            return p, age
    return None


def forget_retry(prog, pid=None):
    """Drop the 'clicked once, nothing saved' mark (pid None: whatever paper it names)."""
    f = retry_file(prog)
    try:
        if pid is None or f.read_text().strip() == pid:
            f.unlink()
    except OSError:
        pass


def host_of(h):
    """A host as the page scripts return it (spaces for dots: Claude in Chrome hides many host names) with its dots
    back; '' for anything else (a hidden '[BLOCKED: ...]' value must never reach catlog.py lanes-record)."""
    h = re.sub(r'[\s_]+', '.', str(h or '').strip().lower()).strip('.')
    return h if re.fullmatch(r'[a-z0-9-]+(\.[a-z0-9-]+)+', h) else ''


def resources():
    """(memory free %, disk free GiB, '' or why either is too low); memory None when memory_pressure fails."""
    try:
        m = re.search(r'free percentage:\s*(\d+)%', subprocess.run(['memory_pressure'], capture_output=True,
                                                                   text=True, timeout=30).stdout)
    except (OSError, subprocess.SubprocessError):
        m = None
    mem, disk = int(m[1]) if m else None, round(shutil.disk_usage(Path.home()).free / 2 ** 30, 1)
    why = (f'memory free {mem}% (below {MEM_MIN}%)' if mem is not None and mem < MEM_MIN
           else f'disk free {disk} GB (below {DISK_MIN} GB)' if disk < DISK_MIN else '')
    return mem, disk, why


def say(result, detail, a):
    mem, disk, low = resources()
    print(json.dumps({'result': result, 'detail': detail, 'ip': a, 'campus': a.startswith(os.environ.get('CATLOG_CAMPUS_IP_PREFIX') or '-') if a else None,
                      'mem_free': mem, 'disk_gb': disk, 'low': low}))


def append(prog, pid, result, detail, host, fresh=False):
    a = address(fresh)
    j = {'id': pid, 'result': result, 'detail': detail, 'host': host_of(host), 'ip': a,
         'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    with open(prog, 'a') as f:
        f.write(json.dumps(j) + '\n')
    forget_retry(prog, str(pid))  # the paper has its line: its retry is used up
    if snap_file(prog).exists():  # method-A lane: what is there now is not the next paper's file
        snap(prog)
    say(result, detail, a)


def cmd_list(key, i, j, prog, built=''):
    prog = prog_path(prog)
    try:
        lanes = json.loads(LANES.read_text())
    except (OSError, ValueError) as e:
        die(f'# ERROR cannot read {LANES} ({e}): run python3 catlog.py lanes first')
    if '_built' not in lanes:
        die('# ERROR lanes.json was not written by `python3 catlog.py lanes`: run it first')
    if built and built != lanes['_built']:  # `catlog.py lanes` drops papers tried, so every index after them moved
        die(f'# ERROR lanes.json was rebuilt (built {lanes["_built"]}; this run started on {built}): its indices '
            'moved; start a new run with a new tag from 0')
    other = other_a_lane(prog) if key in METHOD_A else None
    if other:
        die(f'# ERROR another run has a method-A lane live ({other[0]}, snapshot changed {other[1]:.0f} s ago): two '
            'method-A lanes would take each other\'s files from ~/Downloads; run this lane when that run has ended (10 '
            'min after its last line)')
    low = resources()[2]
    if low:
        die(f'# LOW {low}: the lanes stop')
    part = (lanes.get(key) or [])[int(i):int(j)]
    done = {str(x.get('id')) for x in lines(prog) if x.get('result') in ('saved', 'no_access', 'no_pdf')}
    waiting = {id_in_name(n) for n in os.listdir(DOWNLOADS) if not n.endswith(PARTIAL)} - {None}
    disk = dled = earlier = todo = 0
    for e in part:
        pid, doi, url = (list(e) + ['', ''])[:3]
        pid = str(pid)
        if (ROOT / 'papers' / f'{pid}.pdf').exists():
            disk += 1
        elif pid.upper() in waiting:
            dled += 1
        elif pid in done:
            earlier += 1
        else:
            todo += 1
            print(f'{pid}\t{doi or ""}\t{url or ""}')
    print(f'# slice {len(part)} built {lanes["_built"]}: {key}[{i}:{j}] of lanes.json, {todo} to do; left out {disk} on '
          f'disk, {dled} already in ~/Downloads, {earlier} done earlier in {prog.name}')
    if key in METHOD_A:
        snap(prog)
    forget_retry(prog)  # a new agent for this chunk: an earlier agent's half-done retry does not count against it


def cmd_take(prog, pid, lane, doi, host, buy, retry=False, until=None):
    prog = prog_path(prog)
    try:
        before = set(snap_file(prog).read_text().splitlines())
    except OSError:
        die(f'no snapshot for {prog.name}: run `lane_agent.py snap {prog}` before the first click')
    ours = f'PMID{pid.upper()}_'
    t0 = time.time()
    while True:  # until this paper's file arrived and finished (30 s), or nothing started at all (12 s)
        new = arrived(before, ours)  # PMID<other id>_*: another lane's save
        busy = [n for n in new if n.endswith(PARTIAL) or n.startswith('Unconfirmed ')]
        if new and not busy or time.time() - t0 > (30 if busy else 12):
            break
        time.sleep(1.5)
    done = [n for n in new if n not in busy]
    own = [n for n in done if n.upper().startswith(ours)]  # Chrome kept our download= name
    pub = [n for n in done if not id_in_name(n)]  # the publisher's own name
    stem = doi.rsplit('/', 1)[-1].lower()  # ACS bi002715k.pdf, PNAS pnas.0506491102.pdf
    base = lambda n: Path(n).stem.lower().split(' (')[0]
    cands = own or [n for n in pub if base(n) == stem] or pub
    also = ''
    if len(cands) > 1 and len({base(n) for n in cands}) == 1:  # one file twice (the click was run again)
        cands = sorted(cands, key=len)
        cands, also = cands[:1], f' (also {", ".join(cands[1:])[:200]}, left there)'
    if len(cands) > 1:
        return append(prog, pid, 'error', f'{len(cands)} new files in ~/Downloads, none certainly this paper: '
                      + ', '.join(cands)[:300] + ' (left for catlog.py file)', host)
    last = (lines(prog) or [{}])[-1]
    if cands and not own and base(cands[0]) != stem and str(last.get('detail', '')).startswith(
            ('still downloading', TWICE)):  # a late file of the paper before (still busy, or clicked twice in vain)
        return append(prog, pid, 'error', f'unclear file {cands[0]}: maybe the late download of the paper before '
                      '(left for catlog.py file)', host)
    if not cands:
        if (ROOT / 'papers' / f'{pid}.pdf').exists():
            return append(prog, pid, 'saved', 'filed meanwhile by catlog.py file', host)
        if busy:  # a late file must not be taken for the next paper
            append(prog, pid, 'error', 'still downloading after 30 s: ' + ', '.join(busy)[:200], host)
            return snap(prog, [re.sub(r'\.(crdownload|download|part)$', '', n) for n in busy])
        if buy:
            return append(prog, pid, 'no_access', 'clicked; no file arrived; buy/purchase text on the page', host, fresh=True)
        # a refused PDF link (403) saves nothing at all; a one-off miss saves on a click minutes later (old ACS lines:
        # 4 of ~112 first clicks, in episodes of ~2 min). So a paper gets one more click after a pause (also when the
        # agent forgot --retry: the .retry mark remembers the first; a --retry without a mark naming this paper is a
        # first click), and a second empty one is an error line: the lane goes on. The second paper in a row of this
        # progress file ending so (4 empty clicks) is the STOP, except on J-STAGE (FREE_A): empty clicks never stop it.
        second = retried(prog, pid, retry)
        until = until or time.time() + RETRY_WAIT  # a pause for the site, and a late file of this click still counts
        while time.time() < until:  # (to a deadline: an arrival that turns out not to be ours does not cut it short)
            time.sleep(1.5)
            if arrived(before, ours):
                return cmd_take(prog, pid, lane, doi, host, buy, retry, until)
        if second:
            prev = next((x for x in reversed(lines(prog)) if x.get('result') not in ('no_pdf', 'no_access')), {})
            if lane not in FREE_A and prev.get('result') == 'error' and str(prev.get('detail', '')).startswith(TWICE):
                return append(prog, pid, 'STOP', f'{TWICE} either time, as for {prev.get("id")} just before: 4 empty '
                              'clicks in a row, the site probably refuses the PDF (403); treated as a bot check', host)
            return append(prog, pid, 'error', f'{TWICE} either time; the lane goes on (' + (
                'a free site: empty clicks never stop it' if lane in FREE_A else 'a second paper in a row like it stops '
                'it') + ')', host)
        SNAPS.mkdir(parents=True, exist_ok=True)
        tmp = retry_file(prog).with_name(retry_file(prog).name + f'.{os.getpid()}.tmp')
        tmp.write_text(pid + '\n')
        os.replace(tmp, retry_file(prog))
        # no line and no new snapshot, so a late file of this click still counts as this paper's at the --retry take
        return say('retry', 'clicked; no file arrived in about a minute: run this paper once more, then take with '
                   '--retry', address())
    f = DOWNLOADS / cands[0]
    with open(f, 'rb') as fh:
        head = fh.read(200000)
    if b'%PDF-' in head[:1024]:
        dest = f if own else DOWNLOADS / f'PMID{pid}_{lane}.pdf'
        k = 2
        while dest != f and dest.exists():
            dest = DOWNLOADS / f'PMID{pid}_{lane}_{k}.pdf'
            k += 1
        if dest != f:
            os.rename(f, dest)
        return append(prog, pid, 'saved', (f'{f.name} -> {dest.name} kb={dest.stat().st_size // 1024}'
                      if dest != f else f'{f.name} kb={f.stat().st_size // 1024}') + also, host)
    HTML.mkdir(parents=True, exist_ok=True)
    kept = HTML / f'{pid}_{lane}_{f.name}.html'
    os.rename(f, kept)  # out of catlog.py file's way; nothing is deleted
    page = head.lstrip()[:1] == b'<' or b'<html' in head[:2048].lower()
    where = f'{f.name}, kept as {kept.relative_to(ROOT)}'
    if page or BOT.search(head):  # any web page is a STOP; the detail says what it looked like
        what = 'a bot-check page' if BOT.search(head) else 'a login or purchase page' if PAYWALL.search(head) else 'a web page'
        return append(prog, pid, 'STOP', f'the download was {what}, not a PDF ({where})', host)
    return append(prog, pid, 'error', f'not a PDF (starts {head[:8]!r}; {where})', host)


def main(a):
    if len(a) in (5, 6) and a[0] == 'list':
        return cmd_list(a[1], int(a[2]), int(a[3]), a[4], a[5] if len(a) > 5 else '')
    if len(a) == 2 and a[0] == 'snap':
        return snap(prog_path(a[1]))
    if len(a) in (5, 6) and a[0] == 'log':
        if a[3] not in RESULTS or not a[2].strip():
            die(f'log: result must be one of {", ".join(RESULTS)} and the id not empty')
        return append(prog_path(a[1]), a[2].strip(), a[3], a[4], a[5] if len(a) > 5 else '', fresh=a[3] == 'no_access')
    if a and a[0] == 'take':
        buy, retry = '--buy' in a, '--retry' in a
        a = [x for x in a if x not in ('--buy', '--retry')]
        if len(a) in (5, 6):
            return cmd_take(a[1], a[2].strip(), a[3], a[4], a[5] if len(a) > 5 else '', buy, retry)
    die(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
