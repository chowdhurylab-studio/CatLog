#!/usr/bin/env python3
"""A content scan of a full-record judging's sessions (after w1_audit.py, before the report), as the further set's first
judging was scanned on 6 Nov (paper/evidence/random_papers_20261104/AUDIT_RULE_20261106.md in the main folder): every
tool input and every result of every judge session record, for what a judge must not have seen, whatever path it took.

  python3 tools/w1/scan_judges.py randfull|locked   -> records/audit/adjudication_<which>/content_scan.json; exit 1 on a hit

A hit, per session and call:
- another paper's verdict: a "pmid" of another paper in a result;
- a closed place named in an input or a result: the first judges' folders (checks/), another judge role's folders
  (folios/<its code>/), any output folder but the session's own claims and verdict folders, the records, the plain reads'
  papers folder, catlog-copy, the kit, the main CatLog folder or its catalogue, /System/Volumes/Data, /USERS/;
- a field of the private claim map (claim_id, source_shown, partner, first_final, first_votes, twin_visible), of CatLog's
  catalogue (row_id, verify_note, read_by) or of the plain reads (raw_value, raw_unit) in a result;
- a Claude Code session folder (~/.claude/projects/<slug>/) other than the session's own project's.
Claude Code's own notices of a large output saved in the session's own folder are not hits (they name its own slug)."""
import argparse, json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402
import w1_audit as AU  # noqa: E402

RECORD = re.compile(r'^(?P<pmid>[^.]+)\.(?P<chunk>c\d+)\.(?P<judge>j\d)\.a\d+b?\.json$')
FIELDS = ('claim_id', 'source_shown', 'partner', 'first_final', 'first_votes', 'twin_visible', 'row_id', 'verify_note',
          'read_by', 'raw_value', 'raw_unit')
FIELD_RX = re.compile(r'"(' + '|'.join(FIELDS) + r')"\s*:')
PMID_RX = re.compile(r'"pmid"\s*:\s*"([^"]+)"')
PROJECT_RX = re.compile(r'/\.claude/projects/([^/\s"\'\\]+)')


def closed_names(ev, which, own_claims, own_verdicts, own_role_code):
    P, E = W.eval_paths(ev, which), W.eval_paths(ev)
    names = {str(E['adj']) + '/': 'first judges\' folders (checks/)', str(E['records']): 'records',
             str(E['plain']) + '/': 'the plain reads\' papers folder', str(E['a6']): 'catlog-copy',
             str(E['repo']) + '/': 'the kit', str(W.MAIN): 'the main CatLog folder', 'catalog.jsonl': 'the catalogue',
             '/System/Volumes/Data': '/System/Volumes/Data', '/USERS/': '/USERS/'}
    for w in W.FULL_RUNS:
        for r in W.JUDGES:
            c = W.code(W.judge_label(r, w))
            if c != own_role_code:
                names[f'{P["adj"]}/{c}'] = f'another role\'s folders ({w} {r})'
    for d in W.out_folders(ev):
        if Path(d) not in (Path(own_claims), Path(own_verdicts)):
            names[str(d)] = f'output folder {Path(d).name}'
            names[f'/{Path(d).name}/'] = f'output folder {Path(d).name}'
    return names


def scan(ev, which):
    P = W.eval_paths(ev, which)
    log_dir = P['logs'] / f'adjudication_{which}'
    out, n = [], 0
    # the sessions in use, and the earlier ones a step kept when it ran again (earlier/<step>/<n>/: refusals retried, redos)
    for f in sorted(log_dir.glob('*.json')) + sorted(log_dir.glob('earlier/*/*/*.json')):
        m = RECORD.match(f.name)
        if not m:
            continue
        rec = json.loads(f.read_text())
        tr = Path(rec.get('transcript') or '')
        if not tr.exists():
            out.append({'record': str(f.relative_to(log_dir)), 'hit': 'transcript missing', 'where': str(tr)})
            continue
        n += 1
        pmid, judge = m['pmid'], m['judge']
        own_claims = P['claims3'] if judge == 'j3' else P['claims']
        own_verdicts = Path(rec['out']).parent
        role = W.code(W.judge_label(judge, which))
        names = closed_names(ev, which, own_claims, own_verdicts, role)
        own_slug = W.project_slug(Path(rec['cwd']))
        _, calls, *_ = AU.parse(tr)
        for i, c in enumerate(calls):
            for part, text in (('input', c.get('raw') or ''), ('result', c.get('result') or '')):
                for name, what in names.items():
                    if name in text:
                        out.append({'record': str(f.relative_to(log_dir)), 'call': i, 'tool': c.get('name'), 'part': part, 'hit': what,
                                    'text': text[max(0, text.find(name) - 80):text.find(name) + 120]})
                for slug in set(PROJECT_RX.findall(text)):
                    if slug != own_slug:
                        out.append({'record': str(f.relative_to(log_dir)), 'call': i, 'tool': c.get('name'), 'part': part,
                                    'hit': f'another session folder ({slug})'})
                if part == 'result':
                    for p in set(PMID_RX.findall(text)) - {pmid, '{PMID}'}:
                        out.append({'record': str(f.relative_to(log_dir)), 'call': i, 'tool': c.get('name'), 'part': part,
                                    'hit': f'another paper\'s pmid ({p})'})
                    for fld in set(FIELD_RX.findall(text)):
                        out.append({'record': str(f.relative_to(log_dir)), 'call': i, 'tool': c.get('name'), 'part': part,
                                    'hit': f'a hidden field ({fld})'})
    return n, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('which', choices=W.FULL_RUNS)
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    ev = Path(a.eval)
    n, hits = scan(ev, a.which)
    d = W.eval_paths(ev)['audit'] / f'adjudication_{a.which}'
    d.mkdir(parents=True, exist_ok=True)
    W.write_json(d / 'content_scan.json', {'time': W.now(), 'which': a.which, 'sessions_scanned': n, 'hits': hits})
    by = {}
    for h in hits:
        by.setdefault(h['hit'].split(' (')[0], set()).add(h['record'])
    print(json.dumps({'sessions_scanned': n, 'hits': len(hits), 'sessions_by_kind': {k: len(v) for k, v in by.items()}}, indent=1))
    sys.exit(1 if hits else 0)


if __name__ == '__main__':
    main()
