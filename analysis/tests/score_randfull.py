#!/usr/bin/env python3
"""The further set's values judged again, each claim with its record's full details (the owner, 2026-11-06: "we can do
more if you think that will strengthen our case"). The first judging (score_rand.py) showed each claim's metric, value,
unit, enzyme, organism, variant, substrate, cosubstrate, pH and temperature (score_w1.shown), so that the source stayed
hidden; the record's location, construct, conditions and notes were not shown, and all 28 values judged to carry another
value's label or number name the judges' fact in those fields. Here every value the first judging judged is judged again,
on every paper, with those fields shown, by fresh judges under the same protocol, and the same report code scores it.

  python3 tools/w1/score_randfull.py triage [--dry]   claims -> out/<code of claims-randfull>/; the map back, the values
                                                       and the paper order -> records/score_randfull/private/; the
                                                       judges' folders folios/<PMID>/ (clones of checks/<PMID>/). Drawn once
  python3 tools/w1/score_randfull.py next N           the --pmids of the next papers in the drawn order whose phase-1
                                                       sessions sum to at most N (a partial run is a random set of papers)
  (run_adjudicate.py --runs randfull [--pmids ...] until it prints 0 sessions; w1_audit.py adjudication_randfull)
  python3 tools/w1/score_randfull.py report [--partial] -> records/score_randfull/: results.json and RESULTS.md as
                                                       score_rand.py report writes them, then the comparison with the first

What is judged: every value of every first-judging claim that was not a decoy, each source on its own (a claim the first
judging showed once for both sources, word for word, is two claims here: their details differ), in the paper's company as
before. Details: the value's location and, for CatLog, its construct, conditions and metric note (the first judging's
private/catalog_rows.jsonl, the rows as compared); for the plain read, its location and conditions (private/values.json),
its only free-text fields; strings only, joined in one text without field names. Decoys: as in the first judging, a value
of the paper's agreeing pairs that no claim shows (outside the 750-pair sample), changed 1000-fold or 60-fold (never within
1.5% of a value of the paper), keeping its own details, which stay true of it except its number (a variant or metric decoy
would contradict its details); a paper with no such value takes a value first judged supported, whose twin then shows in the
chunk (marked twin_visible); ceil 5% of a paper's claims, at least 1.
Chunks of score_w1.CHUNK claims per paper; ids (never one of the first judging's), order and decoys drawn with SEED_FULL.
The judges' prompt is prompts/adjudicate_full.txt (adjudicate.txt with a paragraph on the details: fields and details are
read together, a detail that says the value itself is of another metric, enzyme, variant, substrate or cosubstrate makes it
wrong, a mention is no contradiction, a location is a pointer); each judge role works in its own folders
folios/<code of its label>/<PMID>/, with its own scratch code, and the first judges' sessions and the other roles'
sessions are closed to it (run_adjudicate.adj_deny). Known limits, stated in the report: a record's shape shows its source
(CatLog's details join up to four fields, the plain read's two); an agreeing value shows as two claims with one number,
as most of the first judging's sampled pairs did (662 of 750), so a lone claim is a disputed value; fresh judges re-deciding
values first judged wrong rescue some without any cause (regression to the mean), which the table splits by how the first
judging decided them."""
import argparse, collections, json, math, os, random, shutil, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402
import score_w1 as SW  # noqa: E402
import score_rand as SR  # noqa: E402

SEED_FULL = 20261106
SOURCES = SR.SOURCES
C = SW.C
NONE_WORDS = {'', 'none', 'null', 'nan', 'n/a', 'na', '-'}


def src_of(vid):
    """'plain' for a plain read's value id (A0-rand:<PMID>:<n>), 'catlog' for a catalogue row id."""
    return 'plain' if str(vid).startswith(W.run_label('A0', 'rand') + ':') else 'catlog'


def text_of(x):
    """A free-text field as plain text: strings kept, list items joined, None and placeholder words dropped."""
    if isinstance(x, (list, tuple)):
        return '; '.join(t for t in (text_of(i) for i in x) if t)
    if isinstance(x, dict) or x is None:
        return ''
    t = ' '.join(str(x).split())
    return '' if t.lower() in NONE_WORDS else t


def details(src, v, rows):
    """The record's free-text description of a value, as one text without field names."""
    if src == 'catlog':
        r = rows.get(v['id'], {})
        parts = [r.get('location') or v.get('where'), r.get('construct'), r.get('conditions') or v.get('conditions'),
                 r.get('metric_note')]
    else:
        parts = [v.get('where'), v.get('conditions')]
    seen, out = set(), []
    for p in parts:
        t = text_of(p)
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return '; '.join(out)


def full_shown(src, v, rows):
    return {**SW.shown(v), 'details': details(src, v, rows)}


def first_round(ev):
    """The first judging, complete: its claim map, values, catalogue rows as compared, each claim's verdicts and final
    verdict (score_rand.report's rule: a step stopped after its last refusal leaves its claims cannot_decide)."""
    P = SR.paths(ev, 'rand')
    priv = P['score'] / 'private'
    cmap = [json.loads(line) for line in open(priv / 'claims_map.jsonl') if line.strip()]
    vals = json.loads((priv / 'values.json').read_text())
    tri = json.loads((priv / 'triage.json').read_text())
    rows = {}
    for line in open(priv / 'catalog_rows.jsonl'):
        if line.strip():
            r = json.loads(line)
            rows[str(r.get('row_id'))] = r
    V = SW.load_verdicts(P)
    stopped = stopped_steps(P, 'rand')
    final = {}
    for c in cmap:
        f = SW.final_verdict(*(V.get(c['claim_id'], {}).get(j) for j in W.JUDGES))[0]
        if f is None and f"{c['pmid']}.{c['chunk']}" in {s.rsplit('.', 1)[0] for s in stopped}:
            f = 'cannot_decide'
        final[c['claim_id']] = f
    open_ = [c['claim_id'] for c in cmap if final[c['claim_id']] is None]
    if open_:
        sys.exit(f'the first judging is not complete ({len(open_)} claims without a final verdict)')
    return P, cmap, vals, tri, rows, V, final


def stopped_steps(P, which):
    adj = P['adj_log']
    f = adj / W.REFUSED_FILE
    count = collections.Counter(r['step'] for r in (W.read_tsv(f) if f.exists() else []))
    out = {s for s, k in count.items() if k >= W.refusal_tries(f'adjudication_{which}')}
    return out | {lab for lab, r in W.read_switches(adj).items() if r.get('outcome') == 'excluded'}


def decision(v):
    """How the first judging decided a claim: '2-0' when the first two judges agreed in class, else 'third judge'."""
    return '2-0' if v.get('j1') and v.get('j2') and SW.klass(v['j1']) == SW.klass(v['j2']) else 'third judge'


def value_decoys(pmid, n, base, real, rng):
    """n decoys: a judged value of the paper changed 1000-fold or 60-fold, never within 1.5% of a value of the paper."""
    out = []
    for _ in range(50 * n):
        if len(out) >= n or not base:
            break
        v = dict(rng.choice(base))
        kind = rng.choice(('x1000', 'x60'))
        v['value'] = v['value'] * ((1000 if rng.random() < 0.5 else 1e-3) if kind == 'x1000' else (60 if rng.random() < 0.5 else 1 / 60))
        if any(r['metric'] == v['metric'] and C.close(r['value'], v['value']) for r in real):
            continue
        out.append({**v, 'decoy': kind, 'src': 'decoy', 'id': f'decoy{len(out)}:{pmid}'})
    return out


def build_folders(ev, papers):
    """folios/<code of adj-jK-randfull>/<PMID>/ for each judge role: APFS clones of checks/<PMID>/'s files (read-only),
    sealed 0555 like the first judges' folders."""
    import w1_setup as WS  # the setup's clone(): same bytes, read-only, never changed silently
    src, root = W.eval_paths(ev)['adj'], W.eval_paths(ev, 'randfull')['adj']
    for r in W.JUDGES:
        for p in papers:
            d = root / W.code(W.judge_label(r, 'randfull')) / p
            if d.exists():
                os.chmod(d, 0o755)
            for f in sorted((src / p).iterdir()):
                if f.is_file():
                    WS.clone(f, d / f.name)
            os.chmod(d, 0o555)


def triage(ev, a):
    Pr, cmap, vals, tri, rows, V, final = first_round(ev)
    P = SR.paths(ev, 'randfull')
    leftovers = [x for x in [P['claims'], P['claims3'], *P['verdicts'].values(), P['score'] / 'private']
                 if x.exists() and any(x.iterdir())]
    if not a.dry and leftovers:
        sys.exit(f'randfull output exists ({[str(x) for x in leftovers]}): drawn once')
    by_id = {s: {v['id']: v for v in vals[s]} for s in SOURCES}
    rng = random.Random(SEED_FULL)
    order = W.seeded_order(vals['papers'], SEED_FULL)
    by_paper = collections.defaultdict(list)
    for c in cmap:
        if c['decoy']:
            continue
        mem = c['members']
        for m in mem:
            other = [x for x in mem if x is not m]
            partner = [other[0]['src'], other[0]['id']] if other else c.get('partner')
            by_paper[c['pmid']].append({
                'pmid': c['pmid'], 'metric': c['metric'], 'decoy': '', 'kind': c['kind'], 'source_shown': m['src'],
                **({'why': c['why']} if c.get('why') else {}), **({'partner': partner} if partner else {}),
                **({'other_holds': c['other_holds']} if c.get('other_holds') else {}),
                'members': [{'src': m['src'], 'id': m['id'], 'kind': c['kind'], 'value': m['value']}],
                'shown': full_shown(m['src'], by_id[m['src']][m['id']], rows),
                'first_claim': c['claim_id'], 'first_source_shown': c['source_shown'], 'first_final': final[c['claim_id']],
                'first_votes': {j: V.get(c['claim_id'], {}).get(j) for j in W.JUDGES if V.get(c['claim_id'], {}).get(j)},
                'first_decision': decision(V.get(c['claim_id'], {}))})
    missing = [p for p in by_paper if not (W.eval_paths(ev)['adj'] / p).is_dir()]
    if missing:
        sys.exit(f'no checks/<PMID>/ folder for {missing[:5]}: run w1_setup.py judge-inputs first')
    real = collections.defaultdict(list)
    for s in SOURCES:
        for v in vals[s]:
            real[v['pmid']].append(v)
    shown_ids = {(m['src'], m['id']) for c in cmap for m in c['members'] if m['src'] in SOURCES}
    unshown = collections.defaultdict(list)  # the first judging's decoy pool: agreeing values, less those any claim shows
    for cid, pid, why in vals['pairs']:
        if why:
            continue
        for s, i in (('catlog', cid), ('plain', pid)):
            v = by_id[s].get(i)
            if v and (s, i) not in shown_ids:
                unshown[v['pmid']].append({**v, '_details': details(s, v, rows), '_twin_visible': False})
    for p in [q for q in order if q in by_paper]:
        k = max(1, math.ceil(SW.DECOY_SHARE * len(by_paper[p])))
        base = sorted(unshown[p], key=lambda v: v['id']) or [
            {**by_id[c['source_shown']][c['members'][0]['id']], '_details': c['shown']['details'], '_twin_visible': True}
            for c in by_paper[p] if SW.klass(c['first_final']) == 'supported']
        for d in value_decoys(p, k, base, real[p], rng):
            by_paper[p].append({'pmid': p, 'metric': d['metric'], 'decoy': d['decoy'], 'kind': 'decoy', 'source_shown': 'decoy',
                                'twin_visible': d['_twin_visible'],
                                'members': [{'src': 'decoy', 'id': d['id'], 'kind': 'decoy', 'value': d['value']}],
                                'shown': {**SW.shown(d), 'details': d['_details']}})
    used = {c['claim_id'] for c in cmap}
    out_map, chunks = [], {}
    for p in [q for q in order if q in by_paper]:
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
                out_map.append({'claim_id': cid, 'chunk': chunk, **c})
            chunks[f'{p}.{chunk}'] = out
    real_claims = [c for c in out_map if not c['decoy']]
    summary = {'time': W.now(), 'seed': SEED_FULL, 'claims': len(out_map), 'decoys': len(out_map) - len(real_claims),
               'decoy_kinds': dict(collections.Counter(c['decoy'] for c in out_map if c['decoy'])),
               'decoys_twin_visible': sum(1 for c in out_map if c['decoy'] and c.get('twin_visible')),
               'chunks': len(chunks), 'papers': len(by_paper),
               'real_claims_by_source': dict(collections.Counter(c['source_shown'] for c in real_claims)),
               'first_final_by_source': {s: dict(collections.Counter(SW.klass(c['first_final']) for c in real_claims
                                                                     if c['source_shown'] == s)) for s in SOURCES},
               'details_empty_by_source': {s: sum(1 for c in real_claims if c['source_shown'] == s and not c['shown']['details'])
                                           for s in SOURCES}}
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    if a.dry:
        return
    for name, out in chunks.items():
        W.write_json(P['claims'] / f'{name}.json', out)
    priv = P['score'] / 'private'
    priv.mkdir(parents=True, exist_ok=True)
    with open(priv / 'claims_map.jsonl', 'w') as fh:
        for c in out_map:
            fh.write(json.dumps(c, ensure_ascii=False) + '\n')
    shutil.copyfile(Pr['score'] / 'private' / 'values.json', priv / 'values.json')  # the same values and pairs as the first
    W.write_json(priv / 'triage.json', {**tri, 'claims': summary['claims'], 'decoys': summary['decoys'],
                                        'chunks': summary['chunks'], 'randfull': summary})
    (priv / 'order.txt').write_text('\n'.join(order) + '\n')
    build_folders(ev, [q for q in order if q in by_paper])


def next_papers(ev, a):
    """The next papers of the drawn order whose phase-1 sessions not yet done sum to at most N (whole papers; when the next
    paper alone needs more, nothing is printed but a message, never an empty --pmids)."""
    import run_adjudicate as RA
    P = SR.paths(ev, 'randfull')
    order = (P['score'] / 'private' / 'order.txt').read_text().split()
    stopped = stopped_steps(P, 'randfull')
    per = collections.defaultdict(list)
    for f in sorted(P['claims'].glob('*.json')):
        pmid, chunk = f.name.split('.')[:2]
        for j in ('j1', 'j2'):
            step = f'{pmid}.{chunk}.{j}'
            if step not in stopped and not RA.check_verdicts(f, pmid)(P['verdicts'][j] / f.name)[0]:
                per[pmid].append(step)
    pick, run = [], 0
    for p in order:
        if per.get(p):
            if run + len(per[p]) > a.n:
                break
            run += len(per[p])
            pick.append(p)
    left = sum(map(len, per.values()))
    if not pick:
        print(f'{left} phase-1 sessions left; the next paper alone needs more than {a.n}: ask for more' if left else
              'no phase-1 session left: run run_adjudicate.py --runs randfull (no --pmids) for the third judges')
        return
    print(f'{left} phase-1 sessions left; next {run} sessions on {len(pick)} papers')
    print('--pmids ' + ' '.join(pick))


GROUP = {'matched_sample': 'agreeing sample', 'unmatched': 'disputed', 'identity_suspect': 'disputed'}


def finals_of(P, which, cmap):
    V = SW.load_verdicts(P)
    stopped = {s.rsplit('.', 1)[0] for s in stopped_steps(P, which)}
    out = {}
    for c in cmap:
        f = SW.final_verdict(*(V.get(c['claim_id'], {}).get(j) for j in W.JUDGES))[0]
        out[c['claim_id']] = 'cannot_decide' if f is None and f"{c['pmid']}.{c['chunk']}" in stopped else f
    return out, stopped


def paired_boot(first_pp, second_pp, papers, B, seed):
    """Paper-level bootstrap of (second - first) wrong values per 1,000 stored values, per source, on the same papers."""
    import numpy as np
    rng = np.random.default_rng(seed)
    out = {}
    for s in SOURCES:
        w1 = np.array([first_pp[p][s]['wrong'] for p in papers], float)
        w2 = np.array([second_pp[p][s]['wrong'] for p in papers], float)
        n = np.array([first_pp[p][s]['values'] for p in papers], float)
        idx = rng.integers(0, len(papers), size=(B, len(papers)))
        d = 1000 * (w2[idx].sum(1) - w1[idx].sum(1)) / np.maximum(n[idx].sum(1), 1)
        out[s] = {'first_per_1000': round(1000 * w1.sum() / n.sum(), 2), 'second_per_1000': round(1000 * w2.sum() / n.sum(), 2),
                  'difference_ci': [round(float(np.percentile(d, 2.5)), 2), round(float(np.percentile(d, 97.5)), 2)],
                  'share_second_lower': round(float((d < 0).mean()), 4)}
    return out


def report(ev, a):
    _, first_map, _, _, _, _, final1 = first_round(ev)
    P = SR.paths(ev, 'randfull')
    cmap = [json.loads(line) for line in open(P['score'] / 'private' / 'claims_map.jsonl') if line.strip()]
    stale = [c['claim_id'] for c in cmap if not c['decoy'] and c['first_final'] != final1.get(c['first_claim'])]
    if stale:
        sys.exit(f'{len(stale)} claims carry a first verdict that the first judging no longer gives: {stale[:5]}')
    ns = argparse.Namespace(papers=a.papers, run='rand', dry=False, scratch=None, partial=a.partial, accept_left_out=False,
                            short=False, B=a.B, which='randfull')
    SR.report(ev, ns)  # the first judging's rules and rates, on the second judging: records/score_randfull/
    second = json.loads((P['score'] / 'results.json').read_text())
    used = sorted(second['per_paper'], key=W.pmid_key)
    same = P['score'] / 'first_on_same_papers'
    SR.report(ev, argparse.Namespace(papers=a.papers, run='rand', dry=False, scratch=None, partial=False, accept_left_out=False,
                                     short=False, B=a.B, which='rand', only=used, out=str(same)))
    first = json.loads((same / 'results.json').read_text())
    final, stopped = finals_of(P, 'randfull', cmap)
    good = set(used)
    real = [c for c in cmap if not c['decoy'] and c['pmid'] in good and final[c['claim_id']] is not None]
    gate_dec = [c for c in cmap if c['decoy'] and c['pmid'] in good and f"{c['pmid']}.{c['chunk']}" not in stopped
                and final[c['claim_id']] is not None]
    ext = {'interim': second['interim'], 'papers_used': len(used),
           'papers_in_first_only': sorted(set(json.loads((SR.paths(ev, 'rand')['score'] / 'results.json').read_text())['per_paper']) - good, key=W.pmid_key),
           'rates_on_the_same_papers': paired_boot(first['per_paper'], second['per_paper'], used, a.B, W.SEED_BOOT),
           'scaled_per_1000': {s: [first['per_source'][s]['scaled_per_1000'], second['per_source'][s]['scaled_per_1000']] for s in SOURCES},
           'papers_with_a_wrong_value': {s: [first['per_source'][s]['papers_with_a_wrong_value'], second['per_source'][s]['papers_with_a_wrong_value']] for s in SOURCES},
           'decoys_caught_by_kind': {k: [sum(1 for c in gate_dec if c['decoy'] == k and SW.klass(final[c['claim_id']]) == 'error'),
                                         sum(1 for c in gate_dec if c['decoy'] == k)] for k in sorted({c['decoy'] for c in gate_dec})},
           'decoys_twin_visible_caught': [sum(1 for c in gate_dec if c.get('twin_visible') and SW.klass(final[c['claim_id']]) == 'error'),
                                          sum(1 for c in gate_dec if c.get('twin_visible'))]}
    for s in SOURCES:
        mine = [c for c in real if c['source_shown'] == s]
        ext[s] = {}
        for g in ('agreeing sample', 'disputed'):
            grp = [c for c in mine if GROUP.get(c['kind']) == g]
            ext[s][g] = {f'{a_} -> {b_}': n for (a_, b_), n in sorted(collections.Counter(
                (SW.klass(c['first_final']), SW.klass(final[c['claim_id']])) for c in grp).items())}
        fe = [c for c in mine if SW.klass(c['first_final']) == 'error']
        ext[s]['first_errors_by_first_decision'] = {d: dict(collections.Counter(SW.klass(final[c['claim_id']]) for c in fe
                                                                                if c['first_decision'] == d)) for d in ('2-0', 'third judge')}
        ext[s]['from_former_shared_claims'] = {f'{a_} -> {b_}': n for (a_, b_), n in collections.Counter(
            (SW.klass(c['first_final']), SW.klass(final[c['claim_id']])) for c in mine if c['first_source_shown'] == 'both').items()}
        if s == 'catlog':
            rich = lambda c: bool(c['shown']['details'].count(';') >= 2)  # noqa: E731  (construct or note text besides location, conditions)
            ext[s]['by_details_parts'] = {k: {f'{a_} -> {b_}': n for (a_, b_), n in collections.Counter(
                (SW.klass(c['first_final']), SW.klass(final[c['claim_id']])) for c in mine if rich(c) == (k == 'three or more parts')).items()}
                for k in ('three or more parts', 'fewer parts')}
        ext[s]['new_errors_items'] = [{'pmid': c['pmid'], 'kind': c['kind'], 'first': c['first_final'], 'full': final[c['claim_id']],
                                       'shown': c['shown']} for c in mine if SW.klass(c['first_final']) != 'error'
                                      and SW.klass(final[c['claim_id']]) == 'error']
    W.write_json(P['score'] / 'comparison.json', ext)
    R = ext['rates_on_the_same_papers']
    lines = ['', '## Against the first judging, on the same papers (details now shown)', '']
    if ext['interim']:
        lines += ['**INTERIM: papers with unjudged claims are left out of both columns.**', '']
    lines += ['| | Plain read | CatLog |', '|---|---|---|',
              f"| Wrong per 1,000 stored values, first judging | {R['plain']['first_per_1000']} | {R['catlog']['first_per_1000']} |",
              f"| Wrong per 1,000 stored values, with full records | {R['plain']['second_per_1000']} | {R['catlog']['second_per_1000']} |",
              f"| Second minus first, paired paper bootstrap 95% | {R['plain']['difference_ci']} | {R['catlog']['difference_ci']} |",
              f"| Scaled with the agreeing sample, first / second | {ext['scaled_per_1000']['plain']} | {ext['scaled_per_1000']['catlog']} |",
              f"| Papers with a wrong value, first / second | {ext['papers_with_a_wrong_value']['plain']} | {ext['papers_with_a_wrong_value']['catlog']} |",
              '', 'Each value, first verdict -> verdict with full records (agreeing-sample values weigh about '
              '1 + unsampled/sampled agreeing pairs in the scaled rates; disputed values weigh 1):', '',
              '| | Plain, agreeing sample | Plain, disputed | CatLog, agreeing sample | CatLog, disputed |', '|---|---|---|---|---|']
    keys = [f'{x} -> {y}' for x in ('error', 'supported', 'cannot_decide') for y in ('error', 'supported', 'cannot_decide')]
    for k in keys:
        lines.append(f"| {k} | {ext['plain']['agreeing sample'].get(k, 0)} | {ext['plain']['disputed'].get(k, 0)} | "
                     f"{ext['catlog']['agreeing sample'].get(k, 0)} | {ext['catlog']['disputed'].get(k, 0)} |")
    lines += ['', f"Decoys caught by kind (the gate's decoys): {ext['decoys_caught_by_kind']}; with their twin in the chunk: "
                  f"{ext['decoys_twin_visible_caught'][0]} of {ext['decoys_twin_visible_caught'][1]}.",
              f"First errors by how the first judging decided them: plain {ext['plain']['first_errors_by_first_decision']}; "
              f"CatLog {ext['catlog']['first_errors_by_first_decision']}.",
              'Read with care: fresh judges re-deciding values first judged wrong rescue some without any cause (regression to '
              'the mean; compare the 2-0 and third-judge rows); a record\'s shape shows its source (CatLog\'s details join up to '
              'four fields, the plain read\'s two); an agreeing value shows as two claims, so a lone claim is a disputed value '
              '(662 of the first judging\'s 750 sampled pairs showed so too). Per-claim figures above this section (claims '
              'judged, kappa, misses) count the 88 former shared claims twice and differ from the first report for that reason.']
    with open(P['score'] / 'RESULTS.md', 'a') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=('triage', 'next', 'report'))
    ap.add_argument('n', nargs='?', type=int, default=0, help='next: the most phase-1 sessions to pick')
    ap.add_argument('--papers', default=str(SR.DRAWS / 'list_for_triage.tsv'), help='report: the first judging\'s list')
    ap.add_argument('--partial', action='store_true')
    ap.add_argument('--B', type=int, default=SW.B_MAIN)
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    {'triage': triage, 'next': next_papers, 'report': report}[a.step](Path(a.eval), a)


if __name__ == '__main__':
    main()
