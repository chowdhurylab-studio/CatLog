#!/usr/bin/env python3
"""The locked set (2026-11-09; the owner: "see whats needed - run it"): held-out papers that nothing had read, each read
once by the plain prompt (A0, run label 'locked': run_plain.py --arm A0 --run locked, one model) and once by CatLog's
reading steps as frozen that day (catlog-copy at the snapshot the main repository tags catlog-freeze-20261109: the
reader, the verifier, code conversion and the code checks; run_a6.py locked), compared as score_rand.py compares the
further set, with every disagreement and a sample of the agreements judged blind with each record's full details, as
score_randfull.py judges (prompts/adjudicate_full.txt, each judge role in its own folders, the first judges' and the
other roles' sessions closed).

  python3 tools/w1/score_locked.py draw [--dry]     the ready held-out papers in a seeded order, once ->
                                                    records/orders/locked_draw.txt, and locked_draw.tsv (every held-out
                                                    paper and why it is in or out)
  (then, for the first K of the draw: w1_setup.py plain-inputs, judge-inputs and a6-papers locked (the copy's files from
   the judges' folders); run_plain.py --arm A0 --run locked and run_a6.py locked in batches in the draw's order (a
   launch killed on the way: run_a6.py locked --recover LAUNCH once its session has ended);
   w1_setup.py reset-a6 locked; w1_audit.py A0-locked and A6-locked; for papers left redo_pending, or read in part by a
   Sonnet retry no refusal started, run_a6.py locked --redo [--pmids P], w1_setup.py reset-a6 locked --redo and
   w1_audit.py A6-locked again; scan_reads.py locked, the content scan of both sides' sessions, last)
  python3 tools/w1/score_locked.py triage [--dry]   the first TARGET papers of the draw with a usable read from both,
                                                    paired; claims -> out/<code of claims-locked>/; map, values, rows and
                                                    order -> records/score_locked/private/; the judges' folders
                                                    folios/<code of adj-jK-locked>/<PMID>/ (clones of checks/<PMID>/).
                                                    Refused unless A6-locked.txt is a prefix of the draw, every analysed
                                                    paper's text, original and supplement are the same in the copy's, the
                                                    plain read's and the judges' input records, every kept row of the
                                                    analysed papers carries the frozen copy's stamps (MANIFEST.json), both
                                                    audits are newer than what they audit (the plain read's session
                                                    records; the copy's last reset), and both content scans are newer than
                                                    both audits and the last reset and found nothing (--accept-scan-hits
                                                    goes on); stopped while a paper before the set was full failed for an
                                                    operational reason (--accept-left-out goes on; triage.json lists them)
  python3 tools/w1/score_locked.py next N           the --pmids of the next papers in the draw's order whose phase-1
                                                    sessions sum to at most N (a partial judging is a random set of papers)
  (run_adjudicate.py --runs locked [--pmids ...] until it prints 0 sessions; w1_audit.py adjudication_locked)
  python3 tools/w1/score_locked.py report [--partial]  -> records/score_locked/: results.json and RESULTS.md (score_rand.py's
                                                    report on this judging, then set_and_limits: the set rule, papers left
                                                    out per side, past the target, CatLog's models, decoys by kind and
                                                    twin, the limits; then curation, the pre-registered secondary: each
                                                    side against EnzyExtract's manual curation, not judged; curation.json;
                                                    dropped, and said so, unless its code was committed before triage)

Ready (the draw): in sources/holdout_locked.txt; in the main papers.tsv with status todo; never read (no catalogue row, no
work file in work/ or work/old/, no add in log.tsv); its text on disk with a kept original that is a PDF or publisher XML,
not an OCR-only text (the further set's rule); and its text has the kinetic terms catlog.py next needs before it claims a
paper (catlog.KINETIC). Order: W.seeded_order with SEED_LOCKED.
Usable: a plain read that passed its check, on MODEL, by a session the audit did not break (A0-locked's rerun.txt), and
the reading steps' rows from records/runs/A6-locked/ as score_w1.load_rows takes an A6 run (status DONE_A6 there; a
paper read again after a model switch: its redo's rows; one still switched left out; one whose redo has not run, or
ran and was not kept, is redo_pending or redo_not_kept) and no rule broken (A6-locked's rerun.txt, a model switch the
switch rule settled excepted; or a broken launch session of the launch whose rows are kept: a6_rows; the audit's rules
are common_w1.a6_audit's, shared with the rules-only check's score_today.py), with every agent of that launch on MODEL
(common_w1.a6_other_model: a switch or a fallback line, or a kept row stamped with another model: 'catlog read by
another model'; a retry that never ran is no other model). A paper refused by the safety filter on either side leaves
the set (one model, as the further set): on the copy's side, only when an Opus agent's refusal started the workflow's
Sonnet retry of its role, in any launch of the paper's state (main and more-<k>, a redone paper's redo launches too:
common_w1.a6_refused, 'refused (catlog)'), as a refused plain session is never sent again; not when the agent got past
its refusals and then died at the usage limit or another API error (its transcript's end: that error started the retry,
and the paper is judged on the launch whose rows are kept). A Sonnet retry that ran with no refusal before it is
operational ('catlog retry on another model': the paper is read again on Opus, run_a6.py locked --redo --pmids P), and
so is a paper left unfinished by any other failure (a usage limit, a crash: 'catlog failed'), whatever refusal an agent
got past before it. The first TARGET usable papers of the draw are the set; later ones are
listed and not judged. A paper before the set was full that failed for any other reason than a refusal, a model rule or
a broken isolation rule (EXITS: a finished paper a --force follow-up read again and a paper whose kept launch the audit
did not cover are operational too) stops the triage: it is read again, or --accept-left-out. Triage is refused while
the copy's audit is older than its last reset (main or --redo), while a plain session record is newer than the plain
read's audit, and unless both content scans (scan_reads.py locked) are newer than both audits and the last reset and
found nothing (--accept-scan-hits, once every hit is looked at).
Values, pairing, claims: score_rand.py's (mass-concentration rows left out on both sides, the head-to-head's matcher,
repeats dropped only when unmatched, a pair whose labels disagree two claims, every unmatched value a claim, other_holds),
with SAMPLE_AGREED agreeing pairs sampled; every claim is one source's value under its own labels with its details
(score_randfull.details: CatLog's location, construct, conditions and metric note; the plain read's location and
conditions), so a sampled pair is two claims. Decoys: score_randfull.value_decoys (a value of an unsampled agreeing pair
changed 1000-fold or 60-fold, with its own details; a paper with no such value takes one of its sampled agreeing values,
else one of its identity_suspect pairs' values, else one of its lone claims, whose twin then shows in the chunk, marked
twin_visible; the base is the claims map's decoy_base, and decoys made from lone claims stay out of the gate, their
catch reported apart), ceil 5% of a paper's claims, at least 1. Chunks of
score_w1.CHUNK claims per paper; ids, order and decoys drawn with SEED_LOCKED. Verdicts and report as score_rand.py
(two judges per chunk, a third on split claims, REFUSAL_TRIES for the judges)."""
import argparse, ast, collections, csv, datetime, json, math, os, random, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402
import score_w1 as SW  # noqa: E402
import score_rand as SR  # noqa: E402
import score_randfull as SF  # noqa: E402
import h2h  # noqa: E402  (the head-to-head's gold loaders, for the curation secondary)
import numpy as np  # noqa: E402

WHICH = 'locked'
SEED_LOCKED = 20261109
TARGET = 100
SAMPLE_AGREED = 500    # 5 a paper, as the further set's 750 for 150 papers: 0 errors among 500 bounds the agreed pool near 0.6%
SOURCES = SR.SOURCES
C = SW.C
KEEP = SR.KEEP
DRAW = 'locked_draw'
LONE = SR.LONE_BASE  # the base of a decoy made from a paper's lone claims: outside the gate, its catch reported apart
# catlog.KINETIC (the words `next` needs before it claims a paper), as main holds it on 2026-11-09
KINETIC = re.compile(r'(?i:k\s?_?\{?cat\b|michaelis|turnover number|catalytic efficienc|catalytic constant|kinetic (?:parameters|constants))'
                     r'|\bK\s?_?\{?[mM]\b|\bK\s?\(\s?[mM]\s?\)')


def locked_list():
    f = W.MAIN / 'sources' / 'holdout_locked.txt'
    return [w for line in open(f) if not line.startswith('#') for w in line.split()]


def read_before(papers):
    """Held-out papers production has read: a catalogue row, a work file (work/, work/old/) or an add in log.tsv."""
    want, seen = set(papers), set()
    with open(W.MAIN / 'catalog.jsonl') as fh:
        for line in fh:
            m = re.search(r'"pmid":\s*"?([0-9A-Za-z]+)', line)
            if m and m.group(1) in want:
                seen.add(m.group(1))
    for d in (W.MAIN / 'work', W.MAIN / 'work' / 'old'):
        for f in d.iterdir() if d.exists() else []:
            p = f.name.split('.')[0]
            if p in want:
                seen.add(p)
    with open(W.MAIN / 'log.tsv', errors='replace') as fh:
        for line in fh:
            parts = line.split('\t')
            if len(parts) > 2 and parts[1] in want and parts[2] == 'add':
                seen.add(parts[1])
    return seen


def draw(ev, a):
    P = W.eval_paths(ev)
    out, tsv = P['orders'] / f'{DRAW}.txt', P['orders'] / f'{DRAW}.tsv'
    if out.exists() and not a.dry:
        sys.exit(f'{out} exists: the locked set is drawn once')
    papers = locked_list()
    st = {r['pmid']: r for r in W.read_tsv(W.MAIN / 'papers.tsv')}
    before = read_before(papers)
    why, ready = {}, []
    for p in papers:
        r = st.get(p)
        if not r:
            why[p] = 'not in papers.tsv'
            continue
        if r['status'] != 'todo':
            why[p] = f"status {r['status']}"
            continue
        if p in before:
            why[p] = 'read before the hold'
            continue
        t = W.MAIN / 'texts' / f'{p}.txt'
        if not t.exists():
            why[p] = 'no text yet'
            continue
        path = r['text_source'].partition(':')[2]
        if not path or not Path(path).exists():
            why[p] = 'no kept original'
            continue
        if not path.lower().endswith(('.pdf', '.xml')):
            why[p] = 'original neither PDF nor XML'
            continue
        text = t.read_text(errors='replace')
        if '## OCR TEXT' in text[:3000]:
            why[p] = 'OCR-only text'
            continue
        if not KINETIC.search(text):
            why[p] = 'no kinetic terms'
            continue
        ready.append(p)
    order = W.seeded_order(ready, SEED_LOCKED)
    pos = {p: i + 1 for i, p in enumerate(order)}
    print(json.dumps({'held_out': len(papers), 'ready': len(ready), 'left_out': dict(collections.Counter(why.values())),
                      'seed': SEED_LOCKED, 'first': order[:5]}, indent=1))
    if a.dry:
        return
    P['orders'].mkdir(parents=True, exist_ok=True)
    out.write_text(''.join(p + '\n' for p in order))
    W.write_tsv(tsv, [{'pmid': p, 'order': pos.get(p, ''), 'why_out': why.get(p, '')} for p in papers],
                ['pmid', 'order', 'why_out'])
    print(f'{len(order)} papers in {out}')


MODEL_BREAKS = W.A6_MODEL_BREAKS  # w1_audit.audit_agent's breaks for another model (common_w1, shared with score_today.py)
when = W.record_time  # a record's time (common_w1.record_time)


def a6_rows(ev, papers, kept=None):
    """(rows, status): the reading steps' rows of records/runs/A6-locked/ as score_w1.load_rows takes an A6 run (its
    statuses DONE_A6, a paper read again after a model switch from its redo, one still switched left out), and each
    paper's status: ok, failed (not finished there), model_switch (its redo switched again), redo_pending or
    redo_not_kept (its redo not run, or run and not kept by reset-a6 --redo: model_switch.json), rule_broken (A6-locked's
    rerun.txt, except a paper whose only breaks are its model switch and that model_switch.json kept: rerun_ok, or
    second_try_ok with its redo kept; or a paper whose kept launch, common_w1.a6_kept_agents, has a launch session the
    audit broke: that wins over redo_pending and redo_not_kept), read_again (a finished paper a --force follow-up read
    again: its kept rows are two reads') or unaudited (the audit did not cover its kept launch: no audited reader or no
    audited verifier there, or it lists the paper without one). The audit's rules are common_w1.a6_audit's, as
    score_today.py takes them: refused when the audit (audit.json) is missing, holds no agent of a paper, or is older than
    the newest RESET.json (main or redo). kept: a6_kept_agents(ev, 'locked'), when the caller has it."""
    P = W.eval_paths(ev)
    run = P['runs'] / 'A6-locked'
    if not (run / 'RESET.json').exists():
        sys.exit('A6-locked is not kept yet: run_a6.py locked, then w1_setup.py reset-a6 locked and w1_audit.py A6-locked')
    kept = W.a6_kept_agents(ev, WHICH) if kept is None else kept
    broken, unaudited = W.a6_audit(ev, WHICH, papers, kept)
    redone, sw = W.a6_redone(ev, WHICH), W.read_switches(P['logs'] / 'A6-locked')
    rows, status = SW.load_rows(ev, 'A6', WHICH, papers)
    for p in broken & set(status):
        status[p] = 'rule_broken'
    for r in sw.values():  # a redo still to run, or run and not kept: its switch is what the audit broke
        p = str(r.get('pmid'))
        if p in status and r.get('outcome') == 'redo_pending':
            status[p] = 'redo_pending'
        elif p in status and r.get('outcome') == 'second_try_ok' and p not in redone:
            status[p] = 'redo_not_kept'
    for p in W.a6_launch_broken(ev, WHICH, kept):  # the launch session of its kept launch broke a rule
        if p in status:
            status[p] = 'rule_broken'
    for d in W.a6_launches(ev, WHICH):  # a --force follow-up read finished papers again (run_a6.py: read_again)
        try:
            lr = json.loads((d / 'launch.json').read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for p in map(str, lr.get('read_again') or []):
            if status.get(p) == 'ok' and (p in redone) == d.name.startswith('redo'):
                status[p] = 'read_again'
    for p in unaudited:  # no audited agent behind its kept rows
        if status.get(p) == 'ok':
            status[p] = 'unaudited'
    rows = [{**r, 'pmid': str(r['pmid'])} for r in rows if status.get(str(r.get('pmid'))) == 'ok']
    return rows, status


# reasons a paper leaves the set by the plan's rules (a safety-filter refusal, a model rule, a broken isolation rule);
# any other (plain failed or missing, no session row, catlog failed or missing, a redo not run or not kept, a finished
# paper read again, a paper whose kept launch the audit did not cover, a Sonnet retry no refusal started: 'catlog retry
# on another model') is operational: the paper is read again, or triage goes on only with --accept-left-out
EXITS = ('refused (plain)', 'refused (catlog)', 'plain model_switch', 'plain rule_broken', 'catlog model_switch',
         'catlog rule_broken', 'catlog read by another model')


def an_exit(why):
    return why in EXITS or why.startswith('plain read by ')


def plain_audit(ev):
    """The papers the plain read's audit broke (records/audit/A0-locked/rerun.txt). Refused when there is no audit, or
    when a session record of A0-locked (records/logs/A0-locked/<PMID>.a<k>.json, and earlier/: a step run again keeps its
    earlier sessions there) is newer than the audit (audit.json summary.time): a paper read again after the audit (as
    triage's own stop message says to) would be analysed with its new session unaudited."""
    P, label = W.eval_paths(ev), W.run_label('A0', WHICH)
    pf, jf = P['audit'] / label / 'rerun.txt', P['audit'] / label / 'audit.json'
    if not pf.exists() or not jf.exists():
        sys.exit(f'no audit of {label}: run w1_audit.py {label} first')
    t = when((json.loads(jf.read_text()).get('summary') or {}).get('time'), jf)
    lg = P['logs'] / label
    newer = []
    for f in sorted(lg.glob('*.json')) + sorted(lg.glob('earlier/*/*/*.json')):
        if W.SESSION_RECORD.match(f.name):
            try:
                rec = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                rec = {}
            if when(rec.get('end') or rec.get('start'), f) > t:
                newer.append(str(f.relative_to(lg)))
    if newer:
        sys.exit(f'{len(newer)} session records of {label} are newer than its audit ({jf}): {newer[:10]}; run w1_audit.py '
                 f'{label} again')
    return set(pf.read_text().split())


def sources(ev, papers):
    """Both sources' values on the usable papers (the first TARGET of the draw among those read), as score_rand.sources;
    and each side's reason for every paper left out (sides), with the end of the analysed prefix of the draw (end: the
    papers before it decided the set, a left-out one there was replaced by a later paper)."""
    P = W.eval_paths(ev)
    rows, status = SW.load_rows(ev, 'A0', WHICH, papers)
    reader, refused = SR.readers(ev, WHICH)
    plain_broken = plain_audit(ev)
    state = W.a6_state_agents(ev, WHICH)  # every launch of each paper's state, and its kept launch with its agents there
    kept = W.a6_kept_agents(ev, WHICH, state)
    crows_all, a6_status = a6_rows(ev, papers, kept)
    other = W.a6_other_model(ev, WHICH, kept)  # one model on CatLog's side too: a Sonnet retry that ran is another model,
    stamped = W.a6_stamped_other_model(crows_all)  # and so is a kept row stamped with another model
    plain_why, cat_why = {}, {}
    for p in papers:
        if p in refused:
            plain_why[p] = 'refused (plain)'
        elif status.get(p) != 'ok':
            plain_why[p] = f"plain {status.get(p, 'missing')}"
        elif reader.get(p) != W.MODEL:
            plain_why[p] = f'plain read by {reader.get(p)}' if p in reader else 'plain no_session_row'
        elif p in plain_broken:
            plain_why[p] = 'plain rule_broken'
        st = a6_status.get(p, 'missing')
        if st in ('ok', 'failed') and W.a6_refused(state.get(p) or []):
            cat_why[p] = 'refused (catlog)'  # an Opus refusal started a retry, in any launch of the paper's state
        elif st != 'ok':
            cat_why[p] = f'catlog {st}'
        elif W.a6_retried((kept.get(p) or ('', []))[1]):
            cat_why[p] = 'catlog retry on another model'  # no refusal started it: read again on Opus (--redo --pmids)
        elif p in other or p in stamped:
            cat_why[p] = 'catlog read by another model'
    failed = {p: plain_why.get(p) or cat_why[p] for p in papers if p in plain_why or p in cat_why}
    usable = [p for p in papers if p not in failed]
    ok = usable[:TARGET]
    past = usable[TARGET:]
    end = papers.index(ok[-1]) + 1 if len(ok) == TARGET else len(papers)
    good = set(ok)
    crows = [r for r in crows_all if r['pmid'] in good]
    cv = C.catalog_values(crows, 'catlog')
    pv = [v for v in C.catalog_values(rows, W.run_label('A0', WHICH)) if v['pmid'] in good]
    for v in cv + pv:
        v['id'], v['pmid'] = str(v['id']), str(v['pmid'])
    pv, mass = SR.split_mass(pv, crows)
    sides = {'plain': plain_why, 'catlog': cat_why, 'end': end,
             'other_model': {p: other.get(p, []) + stamped.get(p, []) for p in papers if p in other or p in stamped}}
    return pv, cv, ok, failed, past, mass, crows, sides


def content_scans(ev, accept=False):
    """{label: {time, sessions_scanned, hits}} of the content scan of both sides' reading sessions (scan_reads.py locked:
    records/audit/A0-locked/ and A6-locked/content_scan.json). Refused unless both are there, each newer than both
    audits (audit.json summary.time) and the copy's last reset (RESET.json, main or redo), so a scan run before a read
    again, a redo or a new audit does not count, and each found nothing, unless accept (--accept-scan-hits: the owner
    looked at every hit; triage.json says so)."""
    P = W.eval_paths(ev)
    labels = [W.run_label(x, WHICH) for x in ('A0', 'A6')]
    after = []
    for lab in labels:
        jf = P['audit'] / lab / 'audit.json'
        after.append((f'the audit of {lab}', when((json.loads(jf.read_text()).get('summary') or {}).get('time'), jf)
                      if jf.exists() else None))
    run = P['runs'] / 'A6-locked'
    for f in (run / 'RESET.json', run / 'redo' / 'RESET.json'):
        if f.exists():
            after.append((f'reset-a6 locked ({f.parent.name})', when(json.loads(f.read_text()).get('reset_utc'), f)))
    out, problems = {}, []
    for lab in labels:
        f = P['audit'] / lab / 'content_scan.json'
        if not f.exists():
            problems.append(f'no {f}')
            continue
        d = json.loads(f.read_text())
        t = when(d.get('time'), f)
        late = [what for what, x in after if x is None or x > t]
        if late:
            problems.append(f'{f} is older than {", ".join(late)}')
        out[lab] = {'time': d.get('time'), 'sessions_scanned': d.get('sessions_scanned'), 'hits': len(d.get('hits') or [])}
        if d.get('hits') and not accept:
            problems.append(f"{f} has {len(d['hits'])} hits (look at each; --accept-scan-hits goes on)")
    if problems:
        sys.exit('the content scan of the reading sessions (scan_reads.py locked, after both audits): ' + '; '.join(problems))
    return out


def input_problems(ev, papers):
    """{pmid: why} for the papers whose text, original or supplement sha256 differ between CatLog's copy
    (records/a6_inputs_locked.json), the plain read's folder (hard_inputs.json) and the judges' folder (judge_inputs.json),
    or that one of these records lacks."""
    f = W.eval_paths(ev)['records'] / 'a6_inputs_locked.json'
    recs = {'a6_inputs_locked': (json.loads(f.read_text()).get('papers') or {}) if f.exists() else {}, **W.input_records(ev)}
    out = {}
    for p in papers:
        got = [r[p] for r in recs.values() if p in r]
        if len(got) < len(recs):
            out[p] = f'no record in {sorted(n for n, r in recs.items() if p not in r)}'
        elif len({W.input_hashes(x) for x in got}) > 1:
            out[p] = 'differ: ' + ', '.join(k for i, k in enumerate(W.INPUT_KEYS) if len({W.input_hashes(x)[i] for x in got}) > 1)
    return out


def build_folders(ev, papers):
    """folios/<code of adj-jK-locked>/<PMID>/ for each judge role: APFS clones of checks/<PMID>/'s files (read-only),
    sealed 0555 like the other judges' folders."""
    import w1_setup as WS  # the setup's clone(): same bytes, read-only, never changed silently
    src, root = W.eval_paths(ev)['adj'], W.eval_paths(ev, WHICH)['adj']
    for r in W.JUDGES:
        for p in papers:
            d = root / W.code(W.judge_label(r, WHICH)) / p
            if d.exists():
                os.chmod(d, 0o755)
            for f in sorted((src / p).iterdir()):
                if f.is_file():
                    WS.clone(f, d / f.name)
            os.chmod(d, 0o555)


def triage(ev, a):
    P = SR.paths(ev, WHICH)
    leftovers = [x for x in [P['claims'], P['claims3'], *P['verdicts'].values(), P['score'] / 'private']
                 if x.exists() and any(x.iterdir())]
    if not a.dry and leftovers:
        sys.exit(f'locked output exists ({[str(x) for x in leftovers]}): drawn once')
    order = W.read_order(ev, DRAW)
    if not order:
        sys.exit('no draw: run score_locked.py draw first')
    laid = W.read_order(ev, 'A6-locked')
    papers = [p for p in order if p in set(laid)]  # the draw's prefix laid down for both sides
    if papers != order[:len(laid)]:
        sys.exit(f'records/orders/A6-locked.txt is not a prefix of the draw ({DRAW}.txt): draw papers skipped '
                 f'{[p for p in order[:len(laid)] if p not in set(laid)][:10]}, papers outside the draw '
                 f'{[p for p in laid if p not in set(order)][:10]}, {len(laid) - len(set(laid))} repeated')
    pv, cv, ok, failed, past, mass, crows, sides = sources(ev, papers)
    scans = content_scans(ev, getattr(a, 'accept_scan_hits', False))
    missing = [p for p in ok if not (W.eval_paths(ev)['adj'] / p).is_dir()]
    if missing:
        sys.exit(f'no checks/<PMID>/ folder for {missing[:5]}: run w1_setup.py judge-inputs first')
    differ = input_problems(ev, ok)
    if differ:
        sys.exit(f'{len(differ)} analysed papers were not given the same text, original and supplement on every side '
                 f'(records/a6_inputs_locked.json, hard_inputs.json, judge_inputs.json): {dict(list(differ.items())[:10])}')
    mf = W.eval_paths(ev)['manifest']
    stamps = W.a6_stamp_problems(crows, json.loads(mf.read_text()) if mf.exists() else {})
    if stamps:
        sys.exit(f'{len(stamps)} analysed papers have kept rows stamped otherwise than the frozen copy (MANIFEST.json a6.'
                 f'pipeline_commit_stamp, prompt_hashes_stamp_style): {dict(list(stamps.items())[:10])}')
    end = sides['end']
    open_ = {p: failed[p] for p in papers[:end] if p in failed  # replaced by a later paper for no reason of the plan's
             and not any(an_exit(w) for w in (sides['plain'].get(p), sides['catlog'].get(p)) if w)}
    rows_by_id = {str(r.get('row_id')): r for r in crows}
    cv, pv, pairs, cu, pu, dropped = SR.pair(cv, pv)
    rng = random.Random(SEED_LOCKED)
    cands, matched, plist = [], [], []

    def claim(v, src, kind, why='', partner=None, other_holds=None):
        return {'pmid': v['pmid'], 'metric': v['metric'], 'decoy': '', 'kind': kind, 'source_shown': src,
                **({'why': why} if why else {}), **({'partner': partner} if partner else {}),
                **({'other_holds': other_holds} if other_holds else {}),
                'members': [{'src': src, 'id': v['id'], 'kind': kind, 'value': v['value']}],
                'shown': SF.full_shown(src, v, rows_by_id)}

    for ci, pi, _ in pairs:
        c, p = cv[ci], pv[pi]
        why = SW.identity_disagrees(c, p)
        plist.append([c['id'], p['id'], why])
        if why:
            cands.append(claim(p, 'plain', 'identity_suspect', why, ['catlog', c['id']]))
            cands.append(claim(c, 'catlog', 'identity_suspect', why, ['plain', p['id']]))
        else:
            matched.append((c, p))
    cands += [claim(cv[i], 'catlog', 'unmatched', other_holds=SR.held_by(cv[i], pv)) for i in cu]
    cands += [claim(pv[j], 'plain', 'unmatched', other_holds=SR.held_by(pv[j], cv)) for j in pu]
    matched.sort(key=lambda m: (W.pmid_key(m[0]['pmid']), m[0]['metric'], m[0]['id'], m[1]['id']))
    picks = set(rng.sample(range(len(matched)), min(SAMPLE_AGREED, len(matched))))
    for k in sorted(picks):
        c, p = matched[k]
        cands.append(claim(c, 'catlog', 'matched_sample', partner=['plain', p['id']]))
        cands.append(claim(p, 'plain', 'matched_sample', partner=['catlog', c['id']]))
    by_paper = collections.defaultdict(list)
    for c in cands:
        by_paper[c['pmid']].append(c)
    real = collections.defaultdict(list)
    for v in cv + pv:
        real[v['pmid']].append(v)
    unshown = collections.defaultdict(list)  # the decoy pool: agreeing values outside the sample, with their own details
    for k, (c, p) in enumerate(matched):
        if k in picks:
            continue
        unshown[c['pmid']] += [{**c, '_details': SF.details('catlog', c, rows_by_id), '_twin_visible': False},
                               {**p, '_details': SF.details('plain', p, rows_by_id), '_twin_visible': False}]
    by_id = {(s, v['id']): v for s, vals in (('catlog', cv), ('plain', pv)) for v in vals}
    order_ok = [p for p in ok if p in by_paper]
    for p in order_ok:
        k = max(1, math.ceil(SW.DECOY_SHARE * len(by_paper[p])))

        def claimed(kind):  # the paper's claims of one kind as decoy bases, each with its own details; its twin shows
            return [{**by_id[(c['source_shown'], c['members'][0]['id'])], '_details': c['shown']['details'],
                     '_twin_visible': True} for c in by_paper[p] if c['kind'] == kind]
        # the base, in order: the agreeing values outside the sample; the sampled agreeing claims; the values of its
        # identity_suspect pairs (both reads printed the number); else its lone claims (a value one read alone holds,
        # which may itself be a slip whose 1000-fold or 60-fold copy is the printed value: kept out of the gate)
        bases = [('agreeing_unsampled', sorted(unshown[p], key=lambda v: (v['id'], v['value']))),
                 ('agreeing_sampled', claimed('matched_sample')), ('identity_suspect', claimed('identity_suspect')),
                 (LONE, claimed('unmatched'))]
        base_kind, base = next(((b, x) for b, x in bases if x), bases[-1])
        for d in SF.value_decoys(p, k, base, real[p], rng):
            by_paper[p].append({'pmid': p, 'metric': d['metric'], 'decoy': d['decoy'], 'kind': 'decoy', 'source_shown': 'decoy',
                                'twin_visible': d['_twin_visible'], 'decoy_base': base_kind,
                                'members': [{'src': 'decoy', 'id': d['id'], 'kind': 'decoy', 'value': d['value']}],
                                'shown': {**SW.shown(d), 'details': d['_details']}})
    used, cmap, chunks = set(), [], {}
    for p in order_ok:
        cl = by_paper[p]
        rng.shuffle(cl)
        for i in range(0, len(cl), SW.CHUNK):
            chunk = f'c{i // SW.CHUNK + 1:02d}'
            out = []
            for c in cl[i:i + SW.CHUNK]:
                cid = None
                while cid is None or cid in used:
                    cid = f'{rng.getrandbits(32):08x}'
                used.add(cid)
                out.append({'id': cid, **c['shown']})
                cmap.append({'claim_id': cid, 'chunk': chunk, **c})
            chunks[f'{p}.{chunk}'] = out
    real_claims = [c for c in cmap if not c['decoy']]
    kinds = collections.Counter((m['src'], c['kind']) for c in cmap for m in c['members'])
    summary = {'time': W.now(), 'run': WHICH, 'seed': SEED_LOCKED, 'target': TARGET, 'papers_listed': len(papers),
               'papers_analysed': len(ok), 'papers_failed': failed,
               'left_out_by_reason': dict(collections.Counter(str(v) for v in failed.values())),
               'papers_past_target': past, 'values': {'plain': len(pv), 'catlog': len(cv)}, 'catlog_rows': len(crows),
               'repeats_dropped': {s: len(d) for s, d in dropped.items()},
               'plain_mass_rows_left_out': [{k: v.get(k) for k in ('pmid', 'metric', 'raw', 'raw_unit')} for v in mass],
               'pairs': len(pairs), 'identity_suspect_pairs': sum(1 for x in plist if x[2]),
               'agreeing_pairs': len(matched), 'agreeing_pairs_sampled': len(picks),
               'unmatched': {'plain': len(pu), 'catlog': len(cu)}, 'claims': len(cmap),
               'decoys': len(cmap) - len(real_claims),
               'decoy_kinds': dict(collections.Counter(c['decoy'] for c in cmap if c['decoy'])),
               'decoys_twin_visible': sum(1 for c in cmap if c['decoy'] and c.get('twin_visible')),
               'decoy_bases': dict(collections.Counter(c['decoy_base'] for c in cmap if c['decoy'])),
               'chunks': len(chunks), 'papers_with_claims': len(by_paper),
               'members_by_kind': {f'{s} {k}': n for (s, k), n in sorted(kinds.items())},
               'real_claims_by_source': dict(collections.Counter(c['source_shown'] for c in real_claims)),
               'details_empty_by_source': {s: sum(1 for c in real_claims if c['source_shown'] == s and not c['shown']['details'])
                                           for s in SOURCES},
               'set_rule': f"the draw's order ({DRAW}.txt, seed {SEED_LOCKED}): its first {TARGET} papers with a usable read "
                           "from both sides",
               'left_out_by_side': {s: sides[s] for s in SOURCES},
               'left_out_before_the_set_was_full': [p for p in papers[:end] if p in failed],
               'left_out_after_the_set_was_full': [p for p in papers[end:] if p in failed],
               'left_out_operational': open_, 'left_out_accepted': bool(open_) and bool(getattr(a, 'accept_left_out', False)),
               'catlog_read_by_another_model': sides['other_model'],
               'inputs_compared': len(ok), 'kept_rows_stamps_checked': len(crows),
               'content_scans': scans, 'content_scan_hits_accepted': any(x['hits'] for x in scans.values())}
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    if open_:
        print(f'{len(open_)} papers of the analysed prefix have no usable read for an operational reason: {open_}', file=sys.stderr)
    if a.dry:
        return
    if open_ and not getattr(a, 'accept_left_out', False):
        sys.exit('nothing drawn: read those papers again (the plain read: run_plain.py --arm A0 --run locked --pmids ...; '
                 'CatLog: run_a6.py locked --pmids ... before its reset-a6, --redo --pmids ... after it), or pass '
                 '--accept-left-out (they stay listed in triage.json)')
    if len(ok) < TARGET and not a.short:
        sys.exit(f'nothing drawn: {len(ok)} usable papers, the set wants {TARGET}: read more of the draw, or pass --short')
    for name, out in chunks.items():
        W.write_json(P['claims'] / f'{name}.json', out)
    priv = P['score'] / 'private'
    priv.mkdir(parents=True, exist_ok=True)
    with open(priv / 'claims_map.jsonl', 'w') as fh:
        for c in cmap:
            fh.write(json.dumps(c, ensure_ascii=False) + '\n')
    with open(priv / 'catalog_rows.jsonl', 'w') as fh:
        for r in crows:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(priv / 'dropped.jsonl', 'w') as fh:
        for s, d in dropped.items():
            for twin, v in d:
                fh.write(json.dumps({'source': s, 'kept': {k: twin.get(k) for k in KEEP}, 'dropped': {k: v.get(k) for k in KEEP}},
                                    ensure_ascii=False) + '\n')
    W.write_json(priv / 'values.json', {'plain': [{k: v.get(k) for k in KEEP} for v in pv],
                                        'catlog': [{k: v.get(k) for k in KEEP} for v in cv], 'papers': ok, 'pairs': plist})
    W.write_json(priv / 'triage.json', summary)
    (priv / 'order.txt').write_text(''.join(p + '\n' for p in order_ok))
    W.write_tsv(priv / 'papers.tsv', [{'pmid': p} for p in ok], ['pmid'])
    build_folders(ev, order_ok)


def next_papers(ev, a):
    """The next papers of the order whose phase-1 sessions not yet done sum to at most N (whole papers; when the next
    paper alone needs more, nothing is printed but a message, never an empty --pmids)."""
    import run_adjudicate as RA
    P = SR.paths(ev, WHICH)
    order = (P['score'] / 'private' / 'order.txt').read_text().split()
    stopped = SF.stopped_steps(P, WHICH)
    per = collections.defaultdict(list)
    for f in sorted(P['claims'].glob('*.json')):
        pmid, chunk = f.name.split('.')[:2]
        for j in ('j1', 'j2'):
            step = f'{pmid}.{chunk}.{j}'
            if step not in stopped and not RA.check_verdicts(f, pmid)(P['verdicts'][j] / f.name)[0]:
                per[pmid].append(step)
    pick, n = [], 0
    for p in order:
        if per.get(p):
            if n + len(per[p]) > a.n:
                break
            n += len(per[p])
            pick.append(p)
    left = sum(map(len, per.values()))
    if not pick:
        print(f'{left} phase-1 sessions left; the next paper alone needs more than {a.n}: ask for more' if left else
              'no phase-1 session left: run run_adjudicate.py --runs locked (no --pmids) for the third judges')
        return
    print(f'{left} phase-1 sessions left; next {n} sessions on {len(pick)} papers')
    print('--pmids ' + ' '.join(pick))


LIMITS = ("Read with care: a record's shape shows its source (CatLog's details join up to four fields: location, "
          "construct, conditions and metric note; the plain read's two: location and conditions); an agreeing value shows "
          "as two claims with one number, so a lone claim is a disputed value or a decoy; CatLog's side is its frozen first "
          "pass (reader, independent verifier, code conversion and checks: catlog.py add), not its catalogue (no audit, "
          "database check, sweep or re-read after it).")


def other_model_left_out(tri):
    """(before, after): the papers whose CatLog reason is 'catlog read by another model' among those left out before the
    set was full (the count the report gives) and among those left out after it (printed apart: they took no place)."""
    cat = (tri.get('left_out_by_side') or {}).get('catlog') or {}
    pick = lambda ps: sorted((p for p in ps if cat.get(p) == 'catlog read by another model'), key=W.pmid_key)  # noqa: E731
    return pick(tri.get('left_out_before_the_set_was_full') or []), pick(tri.get('left_out_after_the_set_was_full') or [])


def set_and_limits(P, out):
    """What the locked report adds to score_rand's (as score_randfull.report stated for the same claim design): the set
    rule, the papers left out by reason per side, those read past the target, CatLog's models and the papers left out for
    another model before the set was full (those after it apart), the decoys caught by kind, by base and with their twin
    in the chunk (those made from lone claims apart: outside the gate), and the limits. (results.json 'locked',
    RESULTS.md lines)"""
    tri, used = out['triage'], set(out['per_paper'])
    priv = P['score'] / 'private'
    cmap = [json.loads(line) for line in open(priv / 'claims_map.jsonl') if line.strip()]
    final, stopped = SF.finals_of(P, WHICH, cmap)
    judged = [c for c in cmap if c['decoy'] and c['pmid'] in used and f"{c['pmid']}.{c['chunk']}" not in stopped
              and final[c['claim_id']] is not None]
    dec = [c for c in judged if c.get('decoy_base') != LONE]  # the gate's decoys (score_rand.report)
    lone = [c for c in judged if c.get('decoy_base') == LONE]

    def caught(cs):
        return [sum(1 for c in cs if SW.klass(final[c['claim_id']]) == 'error'), len(cs)]
    rows = [r for r in (json.loads(line) for line in open(priv / 'catalog_rows.jsonl') if line.strip()) if str(r.get('pmid')) in used]
    models = {k: dict(collections.Counter(str(r.get(k) or '') for r in rows).most_common()) for k in ('reader_model', 'verifier_model')}
    side, before = tri.get('left_out_by_side') or {}, tri.get('left_out_before_the_set_was_full') or []
    after = tri.get('left_out_after_the_set_was_full') or []
    other_before, other_after = other_model_left_out(tri)
    ext = {'set_rule': tri.get('set_rule'), 'papers_laid_down': tri.get('papers_listed'), 'papers_used': len(used),
           'left_out_before_the_set_was_full': {s: dict(collections.Counter(side.get(s, {})[p] for p in before
                                                                            if p in side.get(s, {}))) for s in SOURCES},
           'left_out_operational_accepted': tri.get('left_out_operational') if tri.get('left_out_accepted') else {},
           'left_out_after_the_set_was_full': after,
           'papers_past_target': tri.get('papers_past_target') or [],
           'catlog_models_kept_rows': models, 'catlog_one_model': all(set(v) <= {W.MODEL} for v in models.values()),
           'catlog_read_by_another_model_left_out': other_before,
           'catlog_read_by_another_model_after_the_set_was_full': other_after,
           'plain_models': {m: b['papers'] for m, b in out.get('by_reader_model', {}).items()},
           'decoys_caught_by_kind': {k: caught([c for c in dec if c['decoy'] == k]) for k in sorted({c['decoy'] for c in dec})},
           'decoys_caught_by_base': {b: caught([c for c in judged if c.get('decoy_base') == b])
                                     for b in sorted({str(c.get('decoy_base')) for c in judged})},
           'decoys_twin_visible_caught': caught([c for c in dec if c.get('twin_visible')]),
           'decoys_from_lone_claims_caught_outside_the_gate': caught(lone), 'limits': LIMITS}
    acc, gone = ext['left_out_operational_accepted'], ext['left_out_before_the_set_was_full']
    lines = ['', '## The set, what was left out, and limits', '',
             f"Set: {ext['set_rule']}; {ext['papers_laid_down']} papers of the draw laid down for both sides, "
             f"{ext['papers_used']} analysed.",
             f"Left out before the set was full (each place taken by a later paper of the draw): plain "
             f"{gone['plain'] or 'none'}; CatLog {gone['catlog'] or 'none'}"
             + (f"; for an operational reason, accepted with --accept-left-out: {acc}." if acc else '.'),
             f"Read past the target, not judged: {len(ext['papers_past_target'])} papers; left out after the set was full: "
             f"{len(ext['left_out_after_the_set_was_full'])}.",
             f"CatLog's models (the kept rows of the analysed papers): reader {models['reader_model'] or 'no rows'}, verifier "
             f"{models['verifier_model'] or 'no rows'}: {'all ' if ext['catlog_one_model'] else 'NOT all '}{W.MODEL}; papers left "
             f"out before the set was full because an agent of their kept launch ran on another model, or a kept row is "
             f"stamped with one: {len(ext['catlog_read_by_another_model_left_out'])} (after the set was full, not counted: "
             f"{len(ext['catlog_read_by_another_model_after_the_set_was_full'])}). "
             f"The plain reads' models, by paper: {ext['plain_models']}.",
             f"Decoys caught by kind (the gate's decoys): {ext['decoys_caught_by_kind']}; with their twin in the chunk: "
             f"{ext['decoys_twin_visible_caught'][0]} of {ext['decoys_twin_visible_caught'][1]}; made from a paper's lone claims "
             f"(no agreeing or identity-suspect value to change; outside the gate, since a lone claim may itself be a slip "
             f"whose 1000-fold or 60-fold copy is the printed value): {ext['decoys_from_lone_claims_caught_outside_the_gate'][0]} "
             f"of {ext['decoys_from_lone_claims_caught_outside_the_gate'][1]}; by base: {ext['decoys_caught_by_base']}.",
             LIMITS]
    return ext, lines


# ---------- the pre-registered secondary: each side against EnzyExtract's manual curation, not judged ----------

CURATION = 'ee_manual'             # h2h.GOLD_NAMES: EnzyExtract's manually curated set
COVERED = ('enzyextract', 'both')  # the gold sets of holdout_374.tsv it covers ('both': this curation alone, as the plan names it)
GOLD_SHOWN = ('id', 'pmid', 'metric', 'value', 'raw', 'enzyme', 'organism', 'variant', 'substrate', 'pH', 'temp', 'where',
              'quote')
SELF = 'tools/w1/score_locked.py'  # this file in the kit's repository
# the secondary's own code in this file: the pre-registration uses it only if it was committed before triage
# (curation_condition compares it, not the whole file, so an edit to the primary's report leaves it as it was)
CURATION_CODE = ('CURATION', 'COVERED', 'GOLD_SHOWN', 'SELF', 'CURATION_CODE', 'holdout_gold_sets', 'curation_file',
                 'curation_values', 'gold_shown', 'pair_flags', 'paired_difference', 'curation', 'curation_lines',
                 'curation_code', 'code_history', 'curation_condition', 'condition_line')


def holdout_gold_sets():
    """{pmid: gold_set} of the held-out papers (the kit's holdout_374.tsv: 'enzyextract', 'cosci' or 'both'): which other
    group's curation covers each paper."""
    return {r['pmid']: r['gold_set'] for r in W.read_tsv(W.KIT / 'holdout_374.tsv')}


def curation_file(ev):
    """The eval's copy of the curation (records/keys/, made by w1_setup.py setup), only while its sha256 is the
    head-to-head's (h2h.GOLD_SHA256): a missing or changed copy stops the report while the secondary is used (report
    checks it before it writes anything), so the secondary is never left out silently."""
    f = W.eval_paths(ev)['keys'] / h2h.GOLD_NAMES[CURATION]
    if not f.is_file():
        sys.exit(f'{f} is missing: the EnzyExtract curation is scored only from the checked copy w1_setup.py setup makes')
    h = W.sha256(f)
    if h != h2h.GOLD_SHA256[CURATION]:
        sys.exit(f"{f}: sha256 {h} is not the head-to-head's {h2h.GOLD_SHA256[CURATION]}: the EnzyExtract curation is not "
                 'scored from a changed copy')
    return f


def curation_values(ev, papers):
    """(values, rows): the curation's values on these papers as the head-to-head reads them (h2h.rows_to_values: CatLog's
    units code on its strings; a bound or a cell it cannot read is kept with value None and never scored), and its rows
    per paper (a covered paper with none has no value and is still covered)."""
    f = curation_file(ev)
    h2h.use_keys(f.parent)
    df = C.load_ee_manual_raw()
    want = set(papers)
    gold, _ = h2h.rows_to_values(df, CURATION, want)
    return gold, dict(collections.Counter(p for p in (str(x).strip() for x in df['pmid']) if p in want))


def gold_shown(g):
    """A curation value as curation.json lists it: its labels and printed cell (the matcher's quote is its descriptor)."""
    return {('descriptor' if k == 'quote' else k): g[k].strip() if isinstance(g.get(k), str) else g.get(k) for k in GOLD_SHOWN}


def pair_flags(g, v):
    """Plain flags on a pair of a curation value and a source value with a similar description. C.desc_pairs pairs on a
    score of 3.2 or more, which the variant, enzyme, temperature and pH reach with no substrate word in common, so a pair
    may be two measurements of the paper: same_variant (desc_sim's full variant credit: the same mutation set, or none on
    either side and both wild type or both not) and substrate_words (C.norm_tokens of the two substrates: 'same', 'some
    in common' or 'none in common')."""
    gm, vm = C.mutations(g['variant']), C.mutations(v['variant'])
    wt = lambda x: C.is_wt(x) or not str(x).strip()  # noqa: E731  (as desc_sim takes a variant with no mutation)
    a, b = C.norm_tokens(g['substrate']), C.norm_tokens(v['substrate'])
    return {'same_variant': gm == vm if gm or vm else wt(g['variant']) == wt(v['variant']),
            'substrate_words': 'same' if a and a == b else 'some in common' if a & b else 'none in common'}


def paired_difference(num, den, B, seed):
    """CatLog minus plain of a share (num / den, each summed over papers, as C.boot's ratio of sums), with a paper-clustered
    bootstrap 95% percentile interval in which both sources take the same resampled papers. As C.boot leaves out a paper
    whose denominator is zero, the draw is over the papers where either source's is above zero; a resample in which one
    source's denominator sums to zero has no share for it and stays out of the percentiles (counted). num, den: {source:
    per-paper array, the papers in one order}."""
    keep = (den['plain'] > 0) | (den['catlog'] > 0)
    n = {s: num[s][keep] for s in SOURCES}
    k = {s: den[s][keep] for s in SOURCES}
    m = int(keep.sum())
    out = {'est': None, 'lo': None, 'hi': None, 'papers': m, 'resamples_without_a_share': 0}
    if not all(k[s].sum() > 0 for s in SOURCES):
        return out
    out['est'] = float(n['catlog'].sum() / k['catlog'].sum() - n['plain'].sum() / k['plain'].sum())
    idx = np.random.default_rng(seed).integers(0, m, size=(B, m))
    share = {}
    for s in SOURCES:
        K = k[s][idx].sum(1)
        share[s] = np.where(K > 0, n[s][idx].sum(1) / np.where(K > 0, K, 1), np.nan)
    d = share['catlog'] - share['plain']
    d = d[~np.isnan(d)]
    out['resamples_without_a_share'] = int(B - d.size)
    if d.size:
        out['lo'], out['hi'] = float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
    return out


def curation(ev, P, B, code=None):
    """The pre-registered secondary (PREREGISTRATION.md "Secondary"): agreement with EnzyExtract's manual curation on the
    set's papers it covers (values.json 'papers' whose gold_set in holdout_374.tsv is enzyextract or both; for both, this
    curation alone), scored by the head-to-head's matcher on the values the judging used (values.json), each source on its
    own: C.match (per paper and metric, one to one, most pairs first, closest description second; two numbers match
    within max(1.5% of the larger, 5e-7) in catalog units, C.close: the floor is the head-to-head's for its gold's
    rounding to 6 decimals, kept as the matcher is, though this curation is not rounded so), then C.desc_pairs on what is
    left (a similar description: often the same measurement with another number, sometimes two measurements; each pair
    flagged by pair_flags). The pre-registration names the drawn papers the curation covers; only the set's are scored,
    since values.json holds the set's values alone (drawn_papers_covered counts the others by why: left out, read past
    the target, never laid down). Per source, per metric and all: the curation's values scored and not, the source's
    values, matched, recall (matched / the curation's scored values) and precision (matched / the source's values), each
    with C.boot's paper-clustered interval (B, W.SEED_BOOT), and CatLog minus plain of both (paired_difference). Reported,
    never judged: the curation is another group's reading, not ground truth. The verdicts play no part (report --partial
    gives the same). code: curation_condition's record (report passes it, and results.json and curation.json keep it):
    when the pre-registration's condition is not met, nothing is read or scored, and results.json, RESULTS.md and
    curation.json say the secondary is dropped, and why. Returns (results.json 'curation', RESULTS.md lines); the lists go
    to records/score_locked/curation.json: per paper, the curation's values by who matched them and those never scored,
    and per source its pairs with a similar description and what is otherwise unmatched on each side."""
    if code is not None and not code['used']:
        x = {'judged': False, 'dropped': code['dropped'], 'code': code}
        W.write_json(P['score'] / 'curation.json', {'summary': x})  # no number of an earlier run stays beside it
        return x, curation_lines(x)
    vals = json.loads((P['score'] / 'private' / 'values.json').read_text())
    sets = holdout_gold_sets()
    covered = sorted({p for p in vals['papers'] if sets.get(p) in COVERED}, key=W.pmid_key)
    cov = set(covered)
    gold, rows = curation_values(ev, covered)
    order = lambda vs: sorted(range(len(vs)), key=lambda i: (W.pmid_key(vs[i]['pmid']), i))  # noqa: E731
    kept = lambda v: {k: v.get(k) for k in KEEP}  # noqa: E731
    sc, hit, per, lists = {}, {}, {}, {}
    for s in SOURCES:
        sv = [v for v in vals[s] if v['pmid'] in cov]
        pairs, gu, su = C.match(gold, sv)
        dp = {gi: (si, sim) for gi, si, sim in C.desc_pairs(gold, sv, gu, su)}
        sc[s] = C.scores(gold, sv, pairs, covered)
        per[s] = {m: {'recall': C.boot(d, 'matched', 'gold_n', B, W.SEED_BOOT),
                      'precision': C.boot(d, 'matched', 'sys_n', B, W.SEED_BOOT),
                      'gold_n': int(d.gold_n.sum()), 'sys_n': int(d.sys_n.sum()), 'matched': int(d.matched.sum()),
                      'gold_left': int(d.gold_n.sum() - d.matched.sum()), 'sys_left': int(d.sys_n.sum() - d.matched.sum())}
                  for m, d in sc[s].items()}
        hit[s] = {gi: sv[si]['id'] for gi, si, _ in pairs}
        gleft, sleft = set(gu) - set(dp), set(su) - {si for si, _ in dp.values()}
        lists[s] = {'similar_description_other_number': [
                        {'pmid': gold[i]['pmid'], 'metric': gold[i]['metric'],
                         'ratio': (float(f"{sv[dp[i][0]]['value'] / gold[i]['value']:.4g}") if gold[i]['value'] else None),
                         'similarity': round(float(dp[i][1]), 3), **pair_flags(gold[i], sv[dp[i][0]]),
                         'curation': gold_shown(gold[i]), 'value': kept(sv[dp[i][0]])}
                        for i in order(gold) if i in dp],
                    'curation_values_otherwise_unmatched': [gold_shown(gold[i]) for i in order(gold) if i in gleft],
                    'source_values_otherwise_unmatched': [kept(sv[j]) for j in order(sv) if j in sleft]}
    groups = {k: [] for k in ('both', 'plain_only', 'catlog_only', 'neither')}
    for i in order(gold):
        if gold[i]['value'] is not None:
            a, b = i in hit['plain'], i in hit['catlog']
            groups['both' if a and b else 'plain_only' if a else 'catlog_only' if b else 'neither'].append(
                {**gold_shown(gold[i]), 'plain': hit['plain'].get(i), 'catlog': hit['catlog'].get(i)})
    col = {s: {c: [int(x) for x in sc[s]['all'][c]] for c in ('gold_n', 'sys_n', 'matched')} for s in SOURCES}
    papers = [{'pmid': p, 'gold_set': sets[p], 'curation_rows': rows.get(p, 0), 'gold_n': col['plain']['gold_n'][k],
               'gold_unscored': sum(1 for g in gold if g['pmid'] == p and g['value'] is None),
               **{f'{s}_{x}': col[s][c][k] for s in SOURCES for x, c in (('n', 'sys_n'), ('matched', 'matched'))}}
              for k, p in enumerate(covered)]
    metrics = [*C.METRICS, 'all']
    diff = {m: {name: paired_difference({s: sc[s][m]['matched'].to_numpy(float) for s in SOURCES},
                                        {s: sc[s][m][den].to_numpy(float) for s in SOURCES}, B, W.SEED_BOOT)
                for name, den in (('recall', 'gold_n'), ('precision', 'sys_n'))} for m in metrics}
    tally = lambda m, scored: sum(1 for g in gold if (g['value'] is not None) == scored and m in ('all', g['metric']))  # noqa: E731
    tf = P['score'] / 'private' / 'triage.json'
    tri = json.loads(tf.read_text()) if tf.exists() else {}
    drawn = W.read_order(ev, DRAW)
    gone, past = set(tri.get('papers_failed') or {}), set(tri.get('papers_past_target') or [])
    where = [('in_the_set' if p in cov else 'left_out' if p in gone else 'past_the_target' if p in past else 'not_laid_down')
             for p in drawn if sets.get(p) in COVERED]  # the drawn papers the curation covers, by why each is scored or not
    kinds = ('same_variant_same_substrate_words', 'same_variant_some_substrate_words', 'other')

    def kind(d):  # a pair with a similar description, by its flags (pair_flags)
        return {'same': kinds[0], 'some in common': kinds[1]}.get(d['substrate_words'], 'other') if d['same_variant'] else 'other'
    ext = {'judged': False, 'curation_file': {'name': h2h.GOLD_NAMES[CURATION], 'sha256': h2h.GOLD_SHA256[CURATION]},
           'papers_in_set': len(vals['papers']), 'papers_covered': len(covered),
           'papers_covered_by_gold_set': dict(sorted(collections.Counter(sets[p] for p in covered).items())),
           'papers_not_covered_by_gold_set': dict(sorted(collections.Counter(
               sets.get(p) or 'none' for p in vals['papers'] if p not in cov).items())),
           'covered_papers_without_a_curation_row': sum(1 for p in covered if not rows.get(p)),
           'drawn_papers_covered': {'drawn': len(drawn), 'covered': len(where),
                                    **{k: where.count(k) for k in ('in_the_set', 'left_out', 'past_the_target', 'not_laid_down')}},
           'gold_values': {m: {'scored': tally(m, True), 'unscored': tally(m, False)} for m in metrics},
           'match_rule': {'relative': C.TOL, 'floor': C.GOLD_ROUND},  # C.close: |a-b| <= max(relative x the larger, floor)
           'per_source': per, 'catlog_minus_plain': diff, 'gold_matched_by': {k: len(v) for k, v in groups.items()},
           **{key: {s: len(lists[s][key]) for s in SOURCES} for key in lists['plain']},
           'similar_description_kinds': {s: {k: sum(1 for d in lists[s]['similar_description_other_number'] if kind(d) == k)
                                             for k in kinds} for s in SOURCES},
           'bootstrap': {'B': B, 'seed': W.SEED_BOOT}, **({'code': code} if code is not None else {})}
    W.write_json(P['score'] / 'curation.json', {
        'summary': ext, 'papers': papers, 'gold_matched_by': groups,
        'gold_unscored': [gold_shown(gold[i]) for i in order(gold) if gold[i]['value'] is None], 'per_source': lists})
    return ext, curation_lines(ext)


def curation_lines(x):
    """The RESULTS.md section of the curation secondary (x: results.json 'curation'): the pre-registration's condition
    (when report checked it), then the numbers, or the line that says the secondary is dropped."""
    L = ['', '## Agreement with the EnzyExtract manual curation (secondary, not judged)', '']
    if 'code' in x:
        L.append(condition_line(x['code']))
    if 'dropped' in x:
        return L + ['Dropped, as the pre-registration says for this case: no number of it is computed or reported.']
    ps, cs, d, gv = x['per_source']['plain'], x['per_source']['catlog'], x['catlog_minus_plain'], x['gold_values']['all']
    est = lambda b, f='.3f': '-' if b['est'] is None else format(b['est'], f)  # noqa: E731

    def share(b):  # a share, its interval and its counts
        return '-' if b['est'] is None else f"{b['est']:.3f} ({b['lo']:.3f}-{b['hi']:.3f}), {b['num']} of {b['den']}"

    def diff(b):
        return est(b, '+.3f') + (f" ({b['lo']:+.3f} to {b['hi']:+.3f})" if b['lo'] is not None else '')
    two = lambda v: f"plain {v['plain']}, CatLog {v['catlog']}"  # noqa: E731
    left = lambda k: two({s: x['per_source'][s]['all'][k] for s in SOURCES})  # noqa: E731
    kinds = lambda k: two({s: x['similar_description_kinds'][s][k] for s in SOURCES})  # noqa: E731
    w, dc, mr = x['gold_matched_by'], x['drawn_papers_covered'], x['match_rule']
    L += [f"Papers: the set's papers the curation covers (gold set enzyextract or both in holdout_374.tsv; for both, this "
          f"curation alone): {x['papers_covered']} of {x['papers_in_set']} ({x['papers_covered_by_gold_set'] or 'none'}); not "
          f"covered: {x['papers_not_covered_by_gold_set'] or 'none'}; covered with no row in the curation: "
          f"{x['covered_papers_without_a_curation_row']} (they count with no curation value). The whole set, whatever the "
          f"judging has reached. The pre-registration places this secondary on the drawn papers the curation covers "
          f"({dc['covered']} of the {dc['drawn']} drawn); only the set's are scored, since the values the judging used "
          f"(values.json) are the set's alone. Of those {dc['covered']}: in the set {dc['in_the_set']}, left out "
          f"{dc['left_out']}, read past the target {dc['past_the_target']}, never laid down {dc['not_laid_down']}.",
          f"The curation's values on them: {gv['scored']} scored, {gv['unscored']} not scored (a bound or a cell CatLog's units "
          f"code cannot read: kept, never matched).",
          f"Each source's values as the judging took them, matched to the curation's by the head-to-head's matcher (per paper "
          f"and metric, one to one, most pairs first, closest description second): two numbers in catalog units match when "
          f"they differ by at most {mr['relative']:.1%} of the larger, or by at most {mr['floor']:.1g} (the head-to-head's "
          f"floor for its gold's rounding to 6 decimals, kept as the matcher is: below {mr['floor'] / mr['relative']:.2g} the "
          f"tolerance is wider than {mr['relative']:.1%}). Recall is the share of the curation's scored values the source "
          f"holds; precision is the share of the source's values the curation holds.", '',
          '| | Plain read | CatLog | CatLog minus plain |', '|---|---|---|---|',
          f"| Values on the covered papers | {ps['all']['sys_n']} | {cs['all']['sys_n']} | |",
          f"| Matched to a curation value | {ps['all']['matched']} | {cs['all']['matched']} | |",
          f"| Recall (95% interval), matched of the curation's scored values | {share(ps['all']['recall'])} | "
          f"{share(cs['all']['recall'])} | {diff(d['all']['recall'])} |",
          f"| Precision (95% interval), matched of the source's values | {share(ps['all']['precision'])} | "
          f"{share(cs['all']['precision'])} | {diff(d['all']['precision'])} |"]
    L += [f"| {m}: recall, precision | {est(ps[m]['recall'])}, {est(ps[m]['precision'])} | {est(cs[m]['recall'])}, "
          f"{est(cs[m]['precision'])} | {est(d[m]['recall'], '+.3f')}, {est(d[m]['precision'], '+.3f')} |" for m in C.METRICS]
    L += ['', f"The curation's scored values by who matched them: both {w['both']}, plain only {w['plain_only']}, CatLog only "
              f"{w['catlog_only']}, neither {w['neither']}.",
          f"Left after matching: the curation's scored values a source did not match, {left('gold_left')}; the source's "
          f"values the curation did not match, {left('sys_left')}. Among them, pairs with a similar description (the "
          f"head-to-head's desc_pairs: per paper and metric, one to one, a description score of 3.2 or more of 5: the variant "
          f"up to 2, substrate words 1.5, enzyme 0.7, temperature 0.4, pH 0.4), {two(x['similar_description_other_number'])}: "
          f"often the same measurement with another number, sometimes two measurements of the paper (a value the source "
          f"missed beside one the curation lacks, such as another substrate of a series at the same temperature and pH). Of "
          f"these pairs, the same variant with the same substrate words: {kinds('same_variant_same_substrate_words')}; the "
          f"same variant with some substrate words in common: {kinds('same_variant_some_substrate_words')}; the rest (another "
          f"variant, or no substrate word in common): {kinds('other')}. Otherwise unmatched (no similar description on the "
          f"other side): the curation's values, {two(x['curation_values_otherwise_unmatched'])}; the source's values, "
          f"{two(x['source_values_otherwise_unmatched'])}.",
          f"Intervals: paper-clustered bootstrap, B {x['bootstrap']['B']}, seed {x['bootstrap']['seed']}; the difference draws "
          f"the same papers for both sources.",
          "Read with care: the curation is another group's manual reading of these papers, not ground truth. These "
          "disagreements are reported, never judged (each is listed in curation.json): one may be either side's slip or a "
          "convention the two apply differently, and a source's value the curation did not match is not wrong by that "
          "alone."]
    return L


def curation_code(text):
    """The secondary's own code in one version of this file: the source of the top-level definitions CURATION_CODE names,
    in file order ('' when there is none or the text does not parse), so an edit elsewhere in the file leaves it as it
    was."""
    try:
        body = ast.parse(text).body
    except (SyntaxError, ValueError):
        return ''

    def names(n):
        return {n.name} if isinstance(n, ast.FunctionDef) else {t.id for t in getattr(n, 'targets', []) if isinstance(t, ast.Name)}
    return '\n\n'.join(ast.get_source_segment(text, n) for n in body if names(n) & set(CURATION_CODE))


def code_history(repo=W.REPO, rel=SELF):
    """(HEAD, [(commit, commit time, text)]): the kit's HEAD and the commits of its history that changed this file, oldest
    first, each with the file as it left it (git, read only; nothing outside a repository)."""
    log = [line.split() for line in W.git(repo, 'log', '--reverse', '--format=%H %cI', '--', rel).splitlines()]
    return W.git(repo, 'rev-parse', 'HEAD'), [(h, t, W.git(repo, 'show', f'{h}:{rel}')) for h, t in log]


def curation_condition(P, history=None, now=None):
    """PREREGISTRATION.md "Secondary": the curation secondary "is used only if its code is written and committed before
    triage; otherwise it is dropped, and the report says so". Its code is its own definitions in this file
    (curation_code). Met when the first commit holding curation() is no later than triage.json's time and the code that
    runs (now: this file's text) is that code as committed when triage ran (the last commit of this file at or before
    that time): code changed after triage, committed or not, drops it too; an edit elsewhere in the file does not.
    history: code_history()'s (HEAD, commits). Returns the record results.json keeps under 'curation' 'code': used, and
    dropped (why) when not; the first commit and its time, triage's time, the commit of this file when triage ran, the
    kit's HEAD and whether this file differs from HEAD's (None outside a repository)."""
    f = P['score'] / 'private' / 'triage.json'
    if not f.exists():
        sys.exit(f'{f} is missing: run score_locked.py triage first')
    tri_time = json.loads(f.read_text()).get('time')
    t = W.record_time(tri_time, f)
    head, hist = code_history() if history is None else history
    now = Path(__file__).read_text() if now is None else now
    before = lambda c: datetime.datetime.fromisoformat(c[1]) <= t  # noqa: E731  (committer time, as git log prints it)
    first = next((c for c in hist if 'def curation(' in curation_code(c[2])), None)
    then = ([c for c in hist if before(c)] or [None])[-1]
    why = ('its code is not committed' if first is None else 'its code was first committed after triage' if not before(first)
           else 'its code changed after triage (the code that runs is not the code committed when triage ran)'
           if curation_code(then[2]) != curation_code(now) else '')
    return {'used': not why, **({'dropped': why} if why else {}), 'triage_time': tri_time,
            'first_commit': first[0] if first else None, 'first_commit_time': first[1] if first else None,
            'commit_at_triage': then[0] if then else None, 'kit_head': head or None,
            'file_differs_from_head': now.strip() != hist[-1][2].strip() if hist else None}


def condition_line(c):
    """RESULTS.md's line on the pre-registration's condition (c: curation_condition's record): met or not, the commit that
    first held the code and its time, triage's time, the commit of this file when triage ran and the kit's HEAD."""
    first = (f"was first committed in {c['first_commit'][:12]} at {c['first_commit_time']}" if c['first_commit']
             else 'is in no commit of the kit')
    verdict = 'met' if c['used'] else f"NOT met ({c['dropped']}), so it is dropped"
    return (f"Pre-registered condition (PREREGISTRATION.md \"Secondary\": used only if its code is written and committed "
            f"before triage; otherwise dropped, and the report says so): {verdict}. Its code (the definitions "
            f"score_locked.CURATION_CODE names) {first}; triage ran at {c['triage_time']}; this file as committed then: "
            f"{(c['commit_at_triage'] or 'none')[:12]}; the kit's HEAD: {(c['kit_head'] or 'none')[:12]}"
            + ('; score_locked.py has uncommitted changes' if c['file_differs_from_head'] else '') + '.')


def report(ev, a):
    P = SR.paths(ev, WHICH)
    code = curation_condition(P)  # the curation secondary is used only if its code was committed before triage
    if code['used']:
        curation_file(ev)  # a missing or changed copy of the curation stops the report before anything is written
    tsv = P['score'] / 'private' / 'papers.tsv'
    SR.report(ev, argparse.Namespace(papers=tsv, run=WHICH, dry=False, scratch=None, partial=a.partial,
                                     accept_left_out=False, short=False, B=a.B, which=WHICH, only=None, out=None))
    out = json.loads((P['score'] / 'results.json').read_text())
    ext, lines = set_and_limits(P, out)
    cur, more = curation(ev, P, a.B, code)
    W.write_json(P['score'] / 'results.json', {**out, 'locked': ext, 'curation': cur})
    with open(P['score'] / 'RESULTS.md', 'a') as fh:
        fh.write('\n'.join(lines + more) + '\n')
    print('\n'.join(lines + more))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=('draw', 'triage', 'next', 'report'))
    ap.add_argument('n', nargs='?', type=int)
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--short', action='store_true', help='triage: go on with fewer than TARGET usable papers')
    ap.add_argument('--accept-left-out', action='store_true', help='triage: go on although papers of the analysed prefix '
                                                                   'failed for an operational reason (listed in triage.json)')
    ap.add_argument('--accept-scan-hits', action='store_true', help='triage: go on although the content scan '
                                                                    '(scan_reads.py locked) found hits, each looked at')
    ap.add_argument('--partial', action='store_true')
    ap.add_argument('--B', type=int, default=SW.B_MAIN)
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    ev = Path(a.eval)
    if a.step == 'next':
        if not a.n:
            sys.exit('next N')
        next_papers(ev, a)
    else:
        {'draw': draw, 'triage': triage, 'report': report}[a.step](ev, a)


if __name__ == '__main__':
    main()
