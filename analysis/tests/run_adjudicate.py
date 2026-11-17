#!/usr/bin/env python3
"""W1 adjudication (ADJUDICATE_prompt.md, RUN.md §6.5): two independent Claude adjudicators judge every chunk of claims
(at most 40 claims of one paper, blinded and shuffled by score_w1.py triage), then a third judges the claims the two
split on. One headless Claude Code session per chunk and judge (claude_session.py), `--lanes` at a time.

  python3 tools/w1/run_adjudicate.py                 phase 1 (judges j1, j2) on every chunk of the rounds' claims,
                                                     then phase 2 (judge j3) on the split claims
  options: --phase 1|2|all, --pmids P ..., --lanes 9, --timeout 3600, --force, --dry-run, --eval EVAL,
           --runs pilot|dry|rand (the pilot's, the dry run's or the further set's claims; scores in
           records/score_pilot/, score_dry/ or score_rand/), --one-model (every session on MODEL: the retry too, and a
           refused chunk stays without a verdict, claude_session.step)

Session: cwd checks/<PMID>/ (the production text with its GLYPH WARNING line, paper.supp.txt, source.pdf|xml), the prompt
prompts/adjudicate.txt verbatim with {CLAIMS} = out/<code of claims-<runs>>/<PMID>.<chunk>.json (claims3-<runs> for j3),
{OUT} = out/<code of verdicts-j<k>-<runs>>/<PMID>.<chunk>.json, {RUN} = <code of adj-j<k>>-<chunk> (a judge sees no
score, judge or run name). The adjudicators never see sources, other judges' verdicts, arm outputs or the private claim
map (Read-denied; w1_audit.py checks). A verdict file must give one of the nine verdicts for every claim id, else the one
retry runs. A judge session that switched model on both tries leaves its chunk's paper out of every arm's analysis
(model_switch.json; score_w1.py decide). Split = the two first verdicts fall in different classes (supported / an error
/ cannot_decide); score_w1.py decide takes the majority."""
import argparse, json, random, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402
import claude_session as S  # noqa: E402

VERDICTS = ('supported', 'wrong_number', 'wrong_scale', 'wrong_metric', 'wrong_identity', 'wrong_conditions',
            'not_measured_here', 'not_printed', 'cannot_decide')


def klass(v):
    return 'supported' if v == 'supported' else 'cannot_decide' if v == 'cannot_decide' else 'error' if v in VERDICTS else None


def read_claims(f):
    d = json.loads(Path(f).read_text())
    return d if isinstance(d, list) else d.get('claims', [])


def check_verdicts(claims_file, pmid):
    ids = [c['id'] for c in read_claims(claims_file)]

    def check(f):
        try:
            d = json.loads(Path(f).read_text())
        except (OSError, json.JSONDecodeError) as e:
            return False, f'unreadable: {type(e).__name__}'
        if not isinstance(d, dict) or not isinstance(d.get('verdicts'), list):
            return False, 'no "verdicts" list'
        got, twice = {}, 0
        for v in d['verdicts']:
            if isinstance(v, dict) and v.get('id') in ids and v.get('verdict') in VERDICTS:
                twice += v['id'] in got
                got.setdefault(v['id'], v['verdict'])
        if twice:
            return False, f'{twice} claims judged twice'
        miss = [i for i in ids if i not in got]
        if miss:
            return False, f'{len(miss)} of {len(ids)} claims without a valid verdict'
        return True, f'OK {len(ids)} verdicts'
    return check


def verdicts_of(f):
    try:
        d = json.loads(Path(f).read_text())
        return {v['id']: v['verdict'] for v in d.get('verdicts', []) if isinstance(v, dict) and v.get('verdict') in VERDICTS}
    except (OSError, json.JSONDecodeError, AttributeError):
        return {}


def adj_deny(ev, own_dir, which='rounds', label='', claims_dir=None, role=None):
    """Every eval part but checks/ and, under out/, this judge's claims folder and its own verdict folder: the records
    (every score folder, the private claim map, the rows, logs, keys), every arm output, the other judges' verdicts and
    the other adjudications' claims; other sessions' /tmp scratch; production and other sessions' records (REVIEW.md
    1.3-1.5). label: the session's scratch code."""
    P = W.eval_paths(ev, which)
    keep_out = {Path(own_dir), Path(claims_dir or P['claims'])}
    folders, files = W.eval_entries(ev, keep=(P['adj'].name, W.OUT_NAMES['out']))
    outs = [d for d in W.out_folders(ev) if Path(d) not in keep_out]
    extra = []
    if which in W.FULL_RUNS:  # judged with full records: the first judges' sessions (checks/) are closed, and
        # each judge role works in its own folder family (folios/<code of its label>/<PMID>), the other roles' sessions
        # (transcripts, saved tool results, temp folders) closed whole, its own role's other transcripts too
        bases = (W.PROJECTS, W.CLAUDE_TMP, Path('/tmp') / W.CLAUDE_TMP.name)
        first = W.project_slug(W.eval_paths(ev)['adj']) + '-*'
        extra = [f'Read(/{b}/{first}/**)' for b in bases]
        # the locked set (2026-11-09) also closes randfull's role families whole; randfull's own list is as it was
        for w in (('randfull',) if which == 'randfull' else W.FULL_RUNS):
            for r in W.JUDGES:
                fam = W.project_slug(P['adj'] / W.code(W.judge_label(r, w))) + '-*'
                extra += ([f'Read(/{W.PROJECTS}/{fam}/*.jsonl)'] if (r == role and w == which)
                          else [f'Read(/{b}/{fam}/**)' for b in bases])
    if which == 'locked':  # the owner's downloads (2026-11-09: other groups' answer keys for the held-out papers); the
        extra += S.downloads_deny('Read')  # finished judgings' lists (randfull's among them) are as they were
    return (S.deny_read(W.MAIN, W.REALKCAT, *W.old_layout(), *folders, *outs) + S.deny_read_files(*files)
            + S.other_scratch_deny(label) + S.records_deny('adj', ev) + extra)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--phase', default='all', choices=('1', '2', 'all'))
    ap.add_argument('--pmids', nargs='*')
    ap.add_argument('--lanes', type=int, default=9)
    ap.add_argument('--timeout', type=int, default=3600)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--one-model', action='store_true')
    ap.add_argument('--runs', default='rounds', choices=('rounds', 'pilot', 'dry', 'rand', 'randfull', 'locked'),
                    help='whose claims: the rounds (score/), the pilot (score_pilot/), the dry run (score_dry/) or the '
                         'further set read once (score_rand.py triage; score_rand/), or that set judged again with full records (score_randfull.py; score_randfull/), or the locked set (score_locked.py; score_locked/)')
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    if a.pmids is not None and not a.pmids:
        sys.exit('--pmids with no paper: nothing to run (leave --pmids out to run every chunk)')
    a.one_model = a.one_model or a.runs in ('rand', 'randfull', 'locked')  # the further set is on one model, whatever the command line
    ev = Path(a.eval)
    P = W.eval_paths(ev, a.runs)
    template = W.prompt_text('adjudicate_full.txt' if a.runs in W.FULL_RUNS else 'adjudicate.txt')  # full records: claims carry details
    log_dir = P['logs'] / ('adjudication' if a.runs == 'rounds' else f'adjudication_{a.runs}')
    chunks = sorted(f for f in P['claims'].glob('*.json')
                    if not a.pmids or f.name.split('.')[0] in set(a.pmids))
    if not chunks:
        sys.exit(f"no claim chunks in {P['claims']} (run score_w1.py triage first)")
    gone = S.excluded_steps(log_dir)
    if not a.dry_run:
        S.check_folders([P['adj'] / W.code(W.judge_label(r, a.runs)) / c.name.split('.')[0] for c in chunks for r in W.JUDGES]
                        if a.runs in W.FULL_RUNS else [P['adj'] / c.name.split('.')[0] for c in chunks])
        S.versions(log_dir, 'before')
    lanes = S.Lanes(a.lanes)

    def job(claims_file, judge):
        pmid, chunk = claims_file.name.split('.')[:2]
        out = P['verdicts'][judge] / f'{pmid}.{chunk}.json'
        cwd = P['adj'] / W.code(W.judge_label(judge, a.runs)) / pmid if a.runs in W.FULL_RUNS else P['adj'] / pmid
        return {'pmid': pmid, 'chunk': chunk, 'judge': judge, 'claims': claims_file, 'out': out, 'cwd': cwd,
                'step': f'{pmid}.{chunk}.{judge}'}

    def one(j):
        j['out'].parent.mkdir(parents=True, exist_ok=True)
        run = f"{W.code(W.judge_label(j['judge'], a.runs))}-{j['chunk']}"
        prompt = lambda model: W.fill(template, PMID=j['pmid'], DIR=j['cwd'], CLAIMS=j['claims'], OUT=j['out'], RUN=run)
        res = S.step(prompt, j['cwd'], j['out'], log_dir, j['step'],
                     check_verdicts(j['claims'], j['pmid']), add_dirs=[j['out'].parent, j['claims'].parent],
                     deny=adj_deny(ev, j['out'].parent, a.runs, run, j['claims'].parent, j['judge']), timeout=a.timeout,
                     dry=a.dry_run, lanes=lanes, scratch=f"{run}-{j['pmid']}-", pmid=j['pmid'], one_model=a.one_model)
        if not a.dry_run:
            S.append_sessions(log_dir, j['judge'], j['pmid'], res)
            state = ('ok' if res['ok'] else 'LEFT OUT (model switched twice)' if res.get('excluded')
                     else 'REFUSED' if res.get('refused') else 'FAILED')
            print(f"{j['judge']} {j['pmid']}.{j['chunk']}: {state} ({res['check']})", flush=True)
        return res

    def todo(js):
        left = [j['step'] for j in js if j['step'] in gone]
        if left:
            print(f'{len(left)} judge sessions left out after a second model switch, not run again: {left}')
        stopped = S.refused_steps(log_dir)
        if stopped & {j['step'] for j in js}:
            print(f"{len(stopped & {j['step'] for j in js})} judge sessions the safety filter stopped, not sent again")
        return [j for j in js if j['step'] not in gone and j['step'] not in stopped and
                (a.force or not check_verdicts(j['claims'], j['pmid'])(j['out'])[0])]

    summary = {}
    if a.phase in ('1', 'all'):
        js = todo([job(c, k) for c in chunks for k in ('j1', 'j2')])
        print(f'phase 1: {len(js)} sessions' + (' (dry run)' if a.dry_run else ''))
        if a.dry_run:
            if js:
                rec = one(js[0])['attempts'][0]
                print('command:', json.dumps(rec['command']))
                print('prompt:\n' + (log_dir / f"{rec['label']}.prompt.txt").read_text())
            return
        res = lanes.map(one, js)
        summary['phase1_failed'] = [f"{j['pmid']}.{j['chunk']}.{j['judge']}" for j, r in zip(js, res) if r is not None and not r['ok']]
        summary['phase1_not_started'] = [f"{j['pmid']}.{j['chunk']}.{j['judge']}" for j, r in zip(js, res) if r is None]
    if a.phase in ('2', 'all') and not lanes.stopped():
        third = []
        for c in chunks:
            pmid, chunk = c.name.split('.')[:2]
            v1 = verdicts_of(P['verdicts']['j1'] / c.name)
            v2 = verdicts_of(P['verdicts']['j2'] / c.name)
            claims = read_claims(c)
            if not all(x['id'] in v1 and x['id'] in v2 for x in claims):
                continue  # phase 1 not complete for this chunk
            split = [x for x in claims if klass(v1[x['id']]) != klass(v2[x['id']])]
            if not split:
                continue
            random.Random(f'{W.SEED_POOL}-{c.name}').shuffle(split)
            f3 = P['claims3'] / c.name
            if not f3.exists() or a.force:
                W.write_json(f3, split)
            third.append(job(f3, 'j3'))
        js = todo(third)
        print(f'phase 2: {len(js)} sessions on split claims' + (' (dry run)' if a.dry_run else ''))
        if not a.dry_run:
            res = lanes.map(one, js)
            summary['phase2_failed'] = [f"{j['pmid']}.{j['chunk']}" for j, r in zip(js, res) if r is not None and not r['ok']]
            summary['phase2_not_started'] = [f"{j['pmid']}.{j['chunk']}" for j, r in zip(js, res) if r is None]
    if not a.dry_run:
        S.versions(log_dir, 'after')
        summary.update({'stopped': lanes.stopped(), 'time': W.now()})
        print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
