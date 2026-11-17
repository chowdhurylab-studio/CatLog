#!/usr/bin/env python3
"""The further set of papers read once (run label 'rand', drawn by paper/evidence/random_papers_20261104/select.py in
the main folder): each paper's plain read against CatLog's catalogue for it, and the blind judging of every value on
which the two disagree, with a sample of those they share.

  python3 tools/w1/score_rand.py triage LIST.tsv   pair the two sources' values and write the claims (blinded chunks)
                                                   -> out/<code of claims-rand>/; the map back -> records/score_rand/private/
  (then run_adjudicate.py --runs rand, which runs on one model by itself, until it prints 0 sessions; w1_audit.py adjudication_rand)
  python3 tools/w1/score_rand.py report LIST.tsv   final verdicts -> records/score_rand/results.json and RESULTS.md
  LIST.tsv: a pmid column holding all of papers.tsv and the first K of papers_more.tsv, the K that were sent to be read.
  options: --run rand (the plain reads' run label), --dry (triage: counts only, nothing written), --scratch DIR (claims,
           map, verdicts and results under DIR: a test on another run's reads), --accept-left-out (triage: go on although
           a paper has no usable read for a reason other than refusal), --short (triage: go on with fewer than 150 papers),
           --partial (report: an INTERIM look, papers with claims still unjudged left out), --B (bootstrap resamples)

Every session is claude-opus-5-5 at max effort (the owner, 2026-11-04: run_plain.py and run_adjudicate.py --one-model,
which --run rand and --runs rand imply). A paper the safety filter refused has no read and leaves the test, as does a
read on any other model; refused papers are replaced from papers_more.tsv in its order until 150 papers have a read.

Sources: the plain read, out/<code of A0-rand>/<PMID>.json (its own converted value and unit); CatLog, the catalogue's
rows for the paper now (catalog.jsonl: value and unit as stored, i.e. its code's conversion of the printed cell; a copy
as compared stays in private/catalog_rows.jsonl). Mass-concentration Km and its kcat/Km are left out on both sides: the
catalogue's by unit, the plain read's by its raw unit or printed cell (split_mass; the plain format allows only mM).

Pairing: the head-to-head's matcher (h2h match: per paper and metric, one-to-one within max(1.5%, 5e-7), most pairs
first, closest description second), on all rows of both sources. This departs from RUN.md 6.2's duplicate rule, whose key
holds no enzyme and sorts a substrate's words, so that it merged distinct measurements (peptides, D- and L-sugars, two
enzymes with one number) and invented disagreements. A row is dropped only when it is left unmatched and repeats another
row of its own source (repeats(): the same metric, value, variant, spelling of the substrate, organism, cosubstrate, pH,
temperature and printed cell); private/dropped.jsonl lists each with its twin. A pair whose descriptions disagree
(score_w1.identity_disagrees) gives one claim per side, and every unmatched value is a claim. SAMPLE_AGREED agreeing
pairs drawn at random are judged too: one claim per side under its own labels, or one claim when the two read word for
word alike. Decoys as in score_w1 triage (ceil 5% of a paper's claims, at least 1: a value of either source changed
once); chunks of CHUNK claims per paper, claim ids and order as there; seed W.SEED_POOL.

Verdicts: run_adjudicate.py's two judges per chunk and a third on split claims; score_w1.final_verdict decides. A value
is wrong when its claim's final verdict is an error; an agreeing pair not sampled counts right for both sources, so the
primary rates are errors found where the sources differ and in the sample, a floor. cannot_decide leaves the primary rate
(numerator and denominator). A judge session the safety filter stopped is not sent again: its chunk's claims without a
final verdict are cannot_decide, and a paper with no judged claim left leaves the analysis; the paper is not replaced,
because the pool is drawn once. Any other unjudged claim stops the report (--partial: an interim look, marked as such).

Report, per source: wrong found per 1,000 values and papers with a wrong value per 100, with an exact interval for papers
(they are the independent draws) and a paper-level bootstrap interval for the rate when at least MIN_WRONG_PAPERS papers
hold a wrong value (W.SEED_BOOT, B 10,000, the same resample for both sources); kinds of error; the sample's errors and
the rate with them scaled to the unsampled pairs; cannot_decide as wrong; a cap of 200 values per paper (RUN.md 6.8);
the values the other source alone stored that the judges supported (this source's misses: not a value this source also
holds under the same labels, and including a supported claim of a pair whose other side was judged wrong). Judge
checks as in score_w1 decide: decoys caught at least 90%, and the first two judges agree on at least 85%, here of the
disputed claims (the unmatched and label-suspect ones), since 750 sampled pairs would otherwise carry that figure."""
import argparse, collections, json, math, random, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402
import score_w1 as SW  # noqa: E402
import numpy as np  # noqa: E402
from scipy.stats import beta  # noqa: E402

C = SW.C
SOURCES = ('plain', 'catlog')
PMID_RX = re.compile(r'\d{4,9}|NP[0-9A-F]{8}')
KEEP = ('id', 'pmid', 'metric', 'value', 'raw', 'raw_unit', 'enzyme', 'organism', 'variant', 'substrate', 'cosub', 'pH',
        'temp', 'where', 'conditions')
SAMPLE_AGREED = 750    # 0 errors among 750 pairs puts the exact upper limit near 0.5% of the agreed pool (100 gives 3.6%)
TARGET = 150
MIN_WRONG_PAPERS = 5   # fewer papers with a wrong value: the count, no percentile interval (errors cluster in papers)
# the locked set's decoys made from a paper's lone claims (score_locked: claims_map decoy_base): a lone claim may itself
# be a slip whose 1000-fold or 60-fold copy is the printed value, so they stay out of the gate (the further set's claims
# maps, rand and randfull, carry no decoy_base: their gate is as it was)
LONE_BASE = 'lone_claims'
DRAWS = W.MAIN / 'paper' / 'evidence' / 'random_papers_20261104'
MASS_WORD = re.compile(r'(?<![A-Za-z])[mµμun]?g(?![A-Za-z])')
VOLUME_WORD = re.compile(r'(?<![A-Za-z])[mµμu]?[lL](?![A-Za-z])')
MOLAR_WORD = re.compile(r'(?<![A-Za-z])[mµμunp]?M(?![A-Za-z])|mol')


def papers_of(tsv, a):
    ps = [r['pmid'] for r in W.read_tsv(tsv)]
    bad = [p for p in ps if not PMID_RX.fullmatch(p)]
    if not ps or bad or len(ps) != len(set(ps)):
        sys.exit(f'{tsv}: no papers, a duplicate, or tokens that are not PMIDs ({bad[:5]})')
    lf = W.MAIN / 'sources' / 'holdout_locked.txt'  # the locked test set (catlog.locked()); its comment names 5 that left it
    locked = ({t for line in open(lf) if not line.startswith('#') for t in line.split() if PMID_RX.fullmatch(t)}
              if lf.exists() else set(W.holdout_papers()))
    if getattr(a, 'run', None) == 'locked':  # the locked set (score_locked.py): its papers are all held out
        if set(ps) - locked:
            sys.exit(f'{tsv} holds papers outside the locked set: {sorted(set(ps) - locked)[:5]}')
        return ps
    if set(ps) & locked:
        sys.exit(f'{tsv} holds held-out papers: {sorted(set(ps) & locked)[:5]}')
    if a.run == 'rand' and not a.scratch:  # the list must be the draw: all of the first, a prefix of the replacements
        first = [r['pmid'] for r in W.read_tsv(DRAWS / 'papers.tsv')]
        more = [r['pmid'] for r in sorted(W.read_tsv(DRAWS / 'papers_more.tsv'), key=lambda r: int(r['order']))]
        k = len(ps) - len(first)
        if k < 0 or set(ps) != set(first) | set(more[:k]):
            sys.exit(f'{tsv} is not all of papers.tsv and the first {k} of papers_more.tsv')
    return ps


def paths(ev, which, scratch=None):
    P = dict(W.eval_paths(ev, which))
    P['adj_log'] = P['logs'] / f'adjudication_{which}'
    if scratch:
        s = Path(scratch)
        P.update({'claims': s / 'claims', 'claims3': s / 'claims3', 'score': s / 'score', 'adj_log': s / 'logs' / f'adjudication_{which}',
                  'verdicts': {j: s / f'verdicts-{j}' for j in W.JUDGES}})
    return P


def catalog_rows(papers):
    want, rows = set(papers), []
    with open(W.MAIN / 'catalog.jsonl') as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(r.get('pmid')) in want:
                rows.append({**r, 'pmid': str(r['pmid'])})
    return rows


def readers(ev, run):
    """(the model of each paper's kept read: its last ok session; the papers the safety filter stopped)."""
    d = W.eval_paths(ev)['logs'] / W.run_label('A0', run)
    f, g = d / 'sessions.tsv', d / W.REFUSED_FILE
    reader = {r['pmid']: r['model'] for r in (W.read_tsv(f) if f.exists() else []) if r.get('ok') == 'True'}
    return reader, {r['pmid'] for r in (W.read_tsv(g) if g.exists() else [])}


def first_number(s):
    m = re.search(r'\d*\.?\d+', str(s or ''))
    return float(m.group()) if m else None


def split_mass(pv, rows):
    """The catalogue's unit filter never removes a plain row (the plain format allows only mM), so plain's mass-concentration
    rows are taken out here: by the raw unit it copied, or by a printed number the catalogue holds only as a mass row."""
    mu = set(C.units.MASS_UNIT.values())
    printed, molar = collections.defaultdict(set), collections.defaultdict(set)
    for r in rows:
        (printed if r.get('unit') in mu else molar)[(str(r['pmid']), r['metric'])].add(first_number(r.get('raw_value')))
    keep, out = [], []
    for v in pv:
        ru, k, n = str(v.get('raw_unit') or ''), (v['pmid'], v['metric']), first_number(v.get('raw'))
        worded = MASS_WORD.search(ru) and VOLUME_WORD.search(ru) and not MOLAR_WORD.search(ru)  # a concentration, not per mg
        mass = v['metric'] != 'kcat' and bool(C.units.normalize(v['metric'], '1', ru)[1] in mu or worded
                                              or (n in printed[k] and n not in molar[k]))
        (out if mass else keep).append(v)
    return keep, out


def sources(ev, run, papers):
    rows, status = SW.load_rows(ev, 'A0', run, papers)
    reader, refused = readers(ev, run)
    ok = [p for p in papers if status.get(p) == 'ok' and reader.get(p) == W.MODEL]
    good = set(ok)
    crows = catalog_rows(ok)
    cv = C.catalog_values(crows, 'catlog')
    pv = [v for v in C.catalog_values(rows, W.run_label('A0', run)) if v['pmid'] in good]
    for v in cv + pv:
        v['id'], v['pmid'] = str(v['id']), str(v['pmid'])
    pv, mass = split_mass(pv, crows)
    failed = {p: 'refused' if p in refused else (f'read by {reader[p]}' if p in reader else 'no_session_row')
              if status.get(p) == 'ok' else status.get(p, 'missing') for p in papers if p not in good}
    return pv, cv, ok, failed, mass, crows


def spell(s):
    return re.sub(r'[^0-9a-zα-ω]+', '', str(s or '').lower())


def toks(s):
    return tuple(sorted(C.norm_tokens(s)))


def cell(v):
    return re.sub(r'\s+', '', str(v.get('raw') or ''))


def has_pm(s):
    return bool(re.search(r'±|\+/-|\+-', s))


def repeats(a, b):
    """a and b, rows of one source: the same printed measurement, as far as the labels can show it."""
    if a['pmid'] != b['pmid'] or a['metric'] != b['metric'] or f"{float(a['value']):.4g}" != f"{float(b['value']):.4g}":
        return False
    if SW.variant_key(a['variant']) != SW.variant_key(b['variant']) or spell(a['substrate']) != spell(b['substrate']):
        return False
    if toks(a.get('organism')) != toks(b.get('organism')) or toks(a.get('cosub')) != toks(b.get('cosub')):
        return False
    if any(SW.num_or_none(a.get(k)) != SW.num_or_none(b.get(k)) for k in ('pH', 'temp')):
        return False
    if C.tok_sim(a.get('enzyme'), b.get('enzyme')) < 0.5:
        return False
    ca, cb = cell(a), cell(b)
    return ca == cb or not (has_pm(ca) and has_pm(cb))  # two different ± are two measurements; a repeat may lose its ±


def thin(vals, left):
    """The rows of one source kept after pairing, and (kept twin, dropped row) for each unmatched row that repeats another."""
    left = set(left)
    keep = [v for i, v in enumerate(vals) if i not in left]
    drops = []
    for i, v in enumerate(vals):
        if i not in left:
            continue
        twin = next((k for k in keep if repeats(k, v)), None)
        if twin is None:
            keep.append(v)
        else:
            drops.append((twin, v))
    return sorted(keep, key=lambda v: v['id']), drops


def pair(cv, pv):
    _, cu, pu = C.match(cv, pv)
    cv, dc = thin(cv, cu)
    pv, dp = thin(pv, pu)
    pairs, cu, pu = C.match(cv, pv)
    return cv, pv, pairs, cu, pu, {'catlog': dc, 'plain': dp}


def same_label(a, b):
    if SW.variant_key(a['variant']) != SW.variant_key(b['variant']):
        return False
    x, y = spell(a['substrate']), spell(b['substrate'])
    if not x or not y or not (x == y or (min(len(x), len(y)) >= 4 and (x in y or y in x))):
        return False
    for k, tol in (('pH', 0.05), ('temp', 0.5)):
        p, q = SW.num_or_none(a.get(k)), SW.num_or_none(b.get(k))
        if p is not None and q is not None and abs(p - q) > tol:
            return False
    return True


def held_by(v, others):
    """Ids of the other source's values with this number under these labels: v is then no value the other source lacks."""
    return [o['id'] for o in others if o['pmid'] == v['pmid'] and o['metric'] == v['metric'] and C.close(o['value'], v['value'])
            and same_label(v, o)]


def triage(ev, a):
    papers = papers_of(a.papers, a)
    P = paths(ev, 'rand', a.scratch)
    if not a.dry and P['claims'].exists() and any(P['claims'].iterdir()):
        sys.exit(f"{P['claims']} is not empty: the claim pool is drawn once (move it aside to draw again)")
    pv, cv, ok, failed, mass, crows = sources(ev, a.run, papers)
    cv, pv, pairs, cu, pu, dropped = pair(cv, pv)
    rng = random.Random(W.SEED_POOL)
    cands, matched, plist = [], [], []

    def claim(rep, src, kind, members, why='', partner=None, other_holds=None):
        return {'pmid': rep['pmid'], 'metric': rep['metric'], 'shown': SW.shown(rep), 'decoy': '', 'kind': kind, 'source_shown': src,
                **({'why': why} if why else {}), **({'partner': partner} if partner else {}),
                **({'other_holds': other_holds} if other_holds else {}),
                'members': [{'src': s, 'id': v['id'], 'kind': kind, 'value': v['value']} for s, v in members]}

    for ci, pi, _ in pairs:
        c, p = cv[ci], pv[pi]
        why = SW.identity_disagrees(c, p)
        plist.append([c['id'], p['id'], why])
        if why:
            cands.append(claim(p, 'plain', 'identity_suspect', [('plain', p)], why, ['catlog', c['id']]))
            cands.append(claim(c, 'catlog', 'identity_suspect', [('catlog', c)], why, ['plain', p['id']]))
        else:
            matched.append((c, p))
    cands += [claim(cv[i], 'catlog', 'unmatched', [('catlog', cv[i])], other_holds=held_by(cv[i], pv)) for i in cu]
    cands += [claim(pv[j], 'plain', 'unmatched', [('plain', pv[j])], other_holds=held_by(pv[j], cv)) for j in pu]
    matched.sort(key=lambda m: (W.pmid_key(m[0]['pmid']), m[0]['metric'], m[0]['id'], m[1]['id']))
    picks = sorted(rng.sample(range(len(matched)), min(SAMPLE_AGREED, len(matched))))
    for k in picks:
        c, p = matched[k]
        if SW.shown(c) == SW.shown(p):  # the same claim word for word: one verdict is both sides'
            cands.append(claim(c, 'both', 'matched_sample', [('catlog', c), ('plain', p)]))
        else:  # each side's value under its own labels
            cands.append(claim(c, 'catlog', 'matched_sample', [('catlog', c)], partner=['plain', p['id']]))
            cands.append(claim(p, 'plain', 'matched_sample', [('plain', p)], partner=['catlog', c['id']]))
    by_paper = collections.defaultdict(list)
    for c in cands:
        by_paper[c['pmid']].append(c)
    real_by, matched_by, cat_by, plain_by = (collections.defaultdict(list) for _ in range(4))
    for v in cv:
        real_by[v['pmid']].append(v)
        cat_by[v['pmid']].append(v)
    for v in pv:
        real_by[v['pmid']].append(v)
        plain_by[v['pmid']].append(v)
    for c, p in matched:
        matched_by[c['pmid']] += [c, p]
    for p in sorted(by_paper, key=W.pmid_key):
        k = max(1, math.ceil(SW.DECOY_SHARE * len(by_paper[p])))
        for d in SW.make_decoys(p, k, sorted(matched_by[p], key=lambda v: v['id']),
                                sorted(cat_by[p] or plain_by[p], key=lambda v: v['id']), real_by[p], rng):
            by_paper[p].append({'pmid': p, 'metric': d['metric'], 'shown': SW.shown(d), 'decoy': d['decoy'], 'kind': 'decoy',
                                'members': [{'src': 'decoy', 'id': d['id'], 'kind': 'decoy', 'value': d['value']}]})
    used, cmap, chunks = set(), [], {}
    for p in sorted(by_paper, key=W.pmid_key):
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
    kinds = collections.Counter((m['src'], c['kind']) for c in cmap for m in c['members'])
    summary = {'time': W.now(), 'run': a.run, 'papers_listed': len(papers), 'papers_analysed': len(ok),
               'papers_failed': failed, 'left_out_by_reason': dict(collections.Counter(str(v).split()[0] for v in failed.values())),
               'values': {'plain': len(pv), 'catlog': len(cv)}, 'catlog_rows': len(crows),
               'repeats_dropped': {s: len(d) for s, d in dropped.items()},
               'plain_mass_rows_left_out': [{k: v.get(k) for k in ('pmid', 'metric', 'raw', 'raw_unit')} for v in mass],
               'pairs': len(pairs), 'identity_suspect_pairs': sum(1 for x in plist if x[2]),
               'agreeing_pairs': len(matched), 'agreeing_pairs_sampled': len(picks),
               'unmatched': {'plain': len(pu), 'catlog': len(cu)}, 'claims': len(cmap),
               'decoys': sum(1 for c in cmap if c['decoy']), 'chunks': len(chunks),
               'papers_with_claims': len(by_paper), 'members_by_kind': {f'{s} {k}': n for (s, k), n in sorted(kinds.items())},
               'seed': W.SEED_POOL}
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    open_ = {p: w for p, w in failed.items() if not (w in ('refused', 'model_switch') or w.startswith('read by'))}
    if open_:
        print(f'{len(open_)} papers have no usable read for a reason other than refusal: {open_}', file=sys.stderr)
    if a.dry:
        return
    if open_ and not a.accept_left_out:
        sys.exit('nothing drawn: read those papers, or pass --accept-left-out')
    if a.run == 'rand' and not a.scratch and len(ok) > TARGET:
        sys.exit(f'nothing drawn: {len(ok)} papers have a read, past the {TARGET} of the stop rule: pass a list with fewer replacements')
    if a.run == 'rand' and not a.scratch and len(ok) < TARGET and not a.short:
        sys.exit(f'nothing drawn: {len(ok)} papers have a read, the test wants {TARGET}: send more replacements, or pass --short')
    for name, out in chunks.items():
        W.write_json(P['claims'] / f'{name}.json', out)
    priv = P['score'] / 'private'
    priv.mkdir(parents=True, exist_ok=True)
    with open(priv / 'claims_map.jsonl', 'w') as fh:
        for c in cmap:
            fh.write(json.dumps(c) + '\n')
    with open(priv / 'catalog_rows.jsonl', 'w') as fh:  # the catalogue moves on: its rows for these papers as compared
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


# ---------- report ----------

def reasons(P):
    out = {}
    for j in W.JUDGES:
        for f in sorted(P['verdicts'][j].glob('*.json')) if P['verdicts'][j].exists() else []:
            try:
                d = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            for v in d.get('verdicts') or []:
                if isinstance(v, dict) and v.get('id'):
                    out.setdefault(str(v['id']), {}).setdefault(j, {k: v.get(k) for k in ('verdict', 'found_at', 'reason')})
    return out


def exact(k, n):
    """Clopper-Pearson 95% limits of k of n, as shares."""
    if not n:
        return None, None
    return (0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))), (1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k)))


def boot(e, n, outside, smp_e, smp_n, B, seed):
    """Paper-level bootstrap, the same resample for both sources: the rate, the share of papers, and the rate with the
    sample's error share (recomputed in each resample) applied to the unsampled agreeing pairs."""
    papers = len(next(iter(n.values())))
    idx = np.random.default_rng(seed).integers(0, papers, size=(B, papers))
    out, rate, share = {}, {}, {}
    for s in SOURCES:
        E, N = e[s][idx].sum(1), n[s][idx].sum(1)
        rate[s] = np.where(N > 0, E / np.where(N > 0, N, 1), 0.0) * 1000
        share[s] = (e[s][idx] > 0).mean(1) * 100
        pe = smp_e[s][idx].sum(1) / np.maximum(smp_n[s][idx].sum(1), 1)
        scaled = np.where(N > 0, (E + outside[s][idx].sum(1) * pe) / np.where(N > 0, N, 1), 0.0) * 1000
        out[s] = {'per_1000_lo': float(np.percentile(rate[s], 2.5)), 'per_1000_hi': float(np.percentile(rate[s], 97.5)),
                  'scaled_per_1000_lo': float(np.percentile(scaled, 2.5)), 'scaled_per_1000_hi': float(np.percentile(scaled, 97.5))}
    d, ds = rate['plain'] - rate['catlog'], share['plain'] - share['catlog']
    out['plain_minus_catlog'] = {'per_1000_lo': float(np.percentile(d, 2.5)), 'per_1000_hi': float(np.percentile(d, 97.5)),
                                 'papers_per_100_lo': float(np.percentile(ds, 2.5)), 'papers_per_100_hi': float(np.percentile(ds, 97.5)),
                                 'share_plain_higher': float((d > 0).mean()), 'B': B}
    out.update({'B': B, 'seed': seed})
    return out


def judge_models(P):
    """Steps whose kept verdict came from another model than MODEL: the last ok session of each judge step."""
    f = P['adj_log'] / 'sessions.tsv'
    last = {}
    for r in W.read_tsv(f) if f.exists() else []:
        if r.get('ok') == 'True':
            last[r['label'].rsplit('.', 1)[0]] = r['model']
    return {s: m for s, m in last.items() if m != W.MODEL}


def report(ev, a):
    papers = papers_of(a.papers, a)
    which = getattr(a, 'which', None) or 'rand'  # randfull: the same values judged again with full records
    P = paths(ev, which, a.scratch)
    priv = P['score'] / 'private'
    cmap = [json.loads(line) for line in open(priv / 'claims_map.jsonl') if line.strip()]
    vals = json.loads((priv / 'values.json').read_text())
    tri = json.loads((priv / 'triage.json').read_text())
    if set(vals['papers']) - set(papers):
        sys.exit(f'{a.papers} does not hold every paper of the triage')
    other = {} if a.scratch else judge_models(P)
    if other:
        sys.exit(f'{len(other)} judge steps kept a verdict from another model than {W.MODEL}: {sorted(other.items())[:5]}; '
                 'redo them with run_adjudicate.py --force')
    V, R = SW.load_verdicts(P), reasons(P)
    adj = P['adj_log']
    tries = W.refusal_tries(f'adjudication_{which}')
    count = collections.Counter(r['step'] for r in (W.read_tsv(adj / W.REFUSED_FILE) if (adj / W.REFUSED_FILE).exists() else []))
    stopped = {s for s, k in count.items() if k >= tries}  # a refusal is final only after its last try
    stopped |= {lab for lab, r in W.read_switches(adj).items() if r.get('outcome') == 'excluded'}
    stopped_chunks = {s.rsplit('.', 1)[0] for s in stopped}
    final, pending, by_filter, unjudged = {}, collections.defaultdict(list), collections.Counter(), set()
    for c in cmap:
        v = V.get(c['claim_id'], {})
        f, _ = SW.final_verdict(v.get('j1'), v.get('j2'), v.get('j3'))
        if f is None and f"{c['pmid']}.{c['chunk']}" in stopped_chunks:
            f = 'cannot_decide'
            by_filter[c['pmid']] += not c['decoy']
            unjudged.add(c['claim_id'])
        elif f is None:
            pending[c['pmid']].append(c['claim_id'])
        final[c['claim_id']] = f
    if pending and not a.partial:
        sys.exit(f'{sum(map(len, pending.values()))} claims in {len(pending)} papers have no final verdict yet: re-run '
                 f'run_adjudicate.py --runs {which} until it prints 0 sessions (--partial: an interim look): '
                 f'{sorted(pending, key=W.pmid_key)[:10]}')
    real_of = collections.Counter(c['pmid'] for c in cmap if not c['decoy'])
    whole = {p for p, k in by_filter.items() if k and k == real_of[p]}  # nothing of the paper could be judged
    use = [p for p in vals['papers'] if p not in pending and p not in whole]
    if getattr(a, 'only', None) is not None:  # a judging restated on another judging's papers (score_randfull report)
        use = [p for p in use if p in set(a.only)]
    good = set(use)
    verdict_of = {}
    for c in cmap:
        if c['decoy'] or c['pmid'] not in good:
            continue
        for m in c['members']:
            verdict_of[(m['src'], m['id'])] = (final[c['claim_id']], c)
    ix = {p: i for i, p in enumerate(use)}
    zeros = lambda: {s: np.zeros(len(use)) for s in SOURCES}  # noqa: E731
    e, n, e_cd, n_all, outside, smp_e, smp_n, judged = (zeros() for _ in range(8))
    kinds = {s: collections.Counter() for s in SOURCES}
    cds = {s: 0 for s in SOURCES}
    wrong, misses, restated = [], {s: [] for s in SOURCES}, []
    for s in SOURCES:
        for v in vals[s]:
            if v['pmid'] not in ix:
                continue
            i = ix[v['pmid']]
            f, c = verdict_of.get((s, v['id']), ('matched', None))
            k = SW.klass(f) if f != 'matched' else 'supported'
            n_all[s][i] += 1
            if c is None:
                outside[s][i] += 1
            elif c['claim_id'] not in unjudged:
                judged[s][i] += 1
            if k == 'cannot_decide':
                cds[s] += 1
                e_cd[s][i] += 1
                continue
            n[s][i] += 1
            if c is not None and c['kind'] == 'matched_sample':
                smp_n[s][i] += 1
                smp_e[s][i] += k == 'error'
            if k == 'error':
                e[s][i] += 1
                e_cd[s][i] += 1
                kinds[s][f] += 1
                wrong.append({'source': s, 'pmid': v['pmid'], 'claim_id': c['claim_id'], 'kind': c['kind'],
                              **({'why': c['why']} if c.get('why') else {}), 'verdict': f, 'shown': c['shown'],
                              'stored': {x: v.get(x) for x in KEEP[4:]}, 'judges': R.get(c['claim_id'], {})})
            elif c is not None and k == 'supported':
                lacks = 'catlog' if s == 'plain' else 'plain'
                if c['kind'] == 'unmatched' and c.get('other_holds'):
                    restated.append({'stored_by': s, 'pmid': v['pmid'], 'shown': c['shown'], 'other_holds': c['other_holds']})
                elif c['kind'] == 'unmatched' or (c.get('partner') and SW.klass(
                        verdict_of.get(tuple(c['partner']), (None,))[0]) == 'error'):
                    misses[lacks].append({'pmid': v['pmid'], 'claim_id': c['claim_id'], 'stored_by': s, 'kind': c['kind'],
                                          'shown': c['shown']})
    bs = boot(e, n, outside, smp_e, smp_n, a.B, W.SEED_BOOT) if use else {}
    per = {}
    for s in SOURCES:
        N, E = n[s].sum(), e[s].sum()
        x, m = int(smp_e[s].sum()), int(smp_n[s].sum())
        lo, hi = exact(x, m)
        wp = int((e[s] > 0).sum())
        plo, phi = exact(wp, len(use))
        has = n_all[s] > 0
        scaled = (E + outside[s].sum() * x / m) / N * 1000 if m and N else None
        capped_e = np.where(n[s] > 200, e[s] * 200 / np.maximum(n[s], 1), e[s])
        capped_n = np.minimum(n[s], 200)
        top = e[s].max() if use else 0
        per[s] = {'papers': len(use), 'papers_with_values': int(has.sum()), 'values': int(n_all[s].sum()),
                  'values_judged': int(judged[s].sum()), 'values_agreed_not_judged': int(outside[s].sum()),
                  'wrong': int(E), 'cannot_decide': cds[s], 'wrong_per_1000': round(1000 * E / N, 2) if N else None,
                  'papers_with_a_wrong_value': wp,
                  'papers_with_a_wrong_value_per_100': round(100 * wp / len(use), 1) if use else None,
                  'papers_per_100_exact': [None if x_ is None else round(100 * x_, 1) for x_ in (plo, phi)],
                  'share_on_papers_with_values': round(100 * int((e[s][has] > 0).sum()) / int(has.sum()), 1) if has.any() else None,
                  'largest_paper_share_of_wrong': round(float(top / E), 3) if E else None,
                  'sensitivity_cannot_decide_as_wrong_per_1000': round(1000 * e_cd[s].sum() / n_all[s].sum(), 2) if n_all[s].sum() else None,
                  'sensitivity_cap_200_per_1000': round(1000 * capped_e.sum() / capped_n.sum(), 2) if capped_n.sum() else None,
                  'sample': {'wrong': x, 'of': m, 'exact_share': [lo, hi]},
                  'scaled_per_1000': round(scaled, 2) if scaled is not None else None,
                  'upper_limit_per_1000': round((E + outside[s].sum() * hi) / N * 1000, 2) if m and N else None,
                  'kinds': dict(kinds[s].most_common()), 'misses_supported_values_only_the_other_stored': len(misses[s]),
                  **({'bootstrap': bs[s]} if bs else {})}
    only = {s: int(((e[s] > 0) & (e[t] == 0)).sum()) for s, t in (('plain', 'catlog'), ('catlog', 'plain'))}
    reader = readers(ev, a.run)[0]
    by_reader = {}
    for m in sorted({reader.get(p, 'unknown') for p in use}):
        i = [ix[p] for p in use if reader.get(p, 'unknown') == m]
        by_reader[m] = {'papers': len(i), **{s: {'values': int(n_all[s][i].sum()), 'wrong': int(e[s][i].sum()),
                                                 'wrong_per_1000': round(1000 * e[s][i].sum() / n[s][i].sum(), 2) if n[s][i].sum() else None,
                                                 'papers_with_a_wrong_value': int((e[s][i] > 0).sum())} for s in SOURCES}}
    real = [c for c in cmap if not c['decoy'] and c['pmid'] in good]
    dec = [c for c in cmap if c['decoy'] and c['pmid'] in good and c['claim_id'] not in unjudged  # a stopped chunk tests no
           and c.get('decoy_base') != LONE_BASE]                                                  # judge; nor a lone claim's
    judges = {}
    for j in ('j1', 'j2', 'j3'):
        got = [g for g in (V.get(c['claim_id'], {}).get(j) for c in dec) if g]
        judges[j] = {'decoys_judged': len(got), 'decoys_called_an_error': sum(SW.klass(g) == 'error' for g in got),
                     'real_claims_judged': sum(1 for c in real if V.get(c['claim_id'], {}).get(j))}

    def firsts(claims):
        both = [V[c['claim_id']] for c in claims if 'j1' in V.get(c['claim_id'], {}) and 'j2' in V.get(c['claim_id'], {})]
        return [SW.klass(b['j1']) for b in both], [SW.klass(b['j2']) for b in both]
    a1, a2 = firsts(real)
    f1, f2 = firsts(real + dec)
    d1, d2 = firsts([c for c in real if c['kind'] != 'matched_sample'])
    caught = sum(SW.klass(final[c['claim_id']]) == 'error' for c in dec)
    share = lambda x, y: sum(p == q for p, q in zip(x, y)) / len(x) if x else None  # noqa: E731
    disputed = share(d1, d2)  # the gate's figure: the 750 sampled pairs would otherwise carry it past 85%
    judges.update({'kappa_real_claims': SW.kappa(a1, a2), 'kappa_with_decoys': SW.kappa(f1, f2), 'first_two_agree': share(f1, f2),
                   'first_two_agree_real': share(a1, a2), 'first_two_agree_disputed': disputed,
                   'decoys': len(dec), 'decoys_final_an_error': caught,
                   'gate_passed': bool(dec and caught / len(dec) >= 0.9 and disputed is not None and disputed >= 0.85 and not pending)})
    sampled = [c for c in real if c['kind'] == 'matched_sample']
    left = {'judge_session_refused_or_switched_whole_paper': sorted(whole, key=W.pmid_key),
            'claims_cannot_decide_by_a_stopped_judge_session': dict(by_filter), 'unjudged_interim': sorted(pending, key=W.pmid_key)}
    out = {'time': W.now(), 'which': which, 'interim': bool(pending), 'triage': tri, 'papers_used': len(use), 'left_out': left, 'per_source': per,
           'by_reader_model': by_reader, 'papers_wrong_in_one_source_only': only,
           **({'plain_minus_catlog': bs['plain_minus_catlog']} if bs else {}),
           'matched_sample': {'claims': len(sampled), 'final': dict(collections.Counter(final[c['claim_id']] for c in sampled))},
           'claims_final': dict(collections.Counter(final[c['claim_id']] for c in real)),
           'judges': judges, 'wrong': wrong, 'misses': misses, 'restated_values_not_counted_as_misses': restated,
           'per_paper': {p: {s: {'values': int(n_all[s][ix[p]]), 'wrong': int(e[s][ix[p]])} for s in SOURCES} for p in use}}
    dest = Path(a.out) if getattr(a, 'out', None) else P['score']
    dest.mkdir(parents=True, exist_ok=True)
    W.write_json(dest / 'results.json', out)
    (dest / 'RESULTS.md').write_text(results_md(out))
    print(results_md(out))


def results_md(o):
    ps, cs = o['per_source']['plain'], o['per_source']['catlog']
    j = o['judges']
    head = ('the same values judged again blind, each claim with its record\'s full details' if o.get('which') == 'randfull'
            else 'the values the two sources differ on, and a sample of the rest, judged blind with each record\'s full '
                 'details' if o.get('which') == 'locked'
            else 'the values the two sources differ on, and a sample of the rest, judged blind')
    title = ('Locked set, unseen papers read once by each (CatLog as frozen on 9 November 2026)' if o.get('which') == 'locked'
             else 'Further set read once')
    L = [f"# {title}: {head} ({o['time']})", '']
    if o['interim']:
        L += [f"**INTERIM: {len(o['left_out']['unjudged_interim'])} papers with unjudged claims are left out.**", '']
    L += [f"Papers: {o['papers_used']} analysed of {o['triage']['papers_listed']} listed (left out before judging: "
          f"{o['triage']['left_out_by_reason']}; nothing left to judge: "
          f"{len(o['left_out']['judge_session_refused_or_switched_whole_paper'])}).",
          f"Judge check: {'passed' if j['gate_passed'] else 'NOT PASSED'}: decoys caught {j['decoys_final_an_error']} of {j['decoys']}, "
          f"the first two judges agree on {'-' if j['first_two_agree_disputed'] is None else format(j['first_two_agree_disputed'], '.3f')} "
          f"of the disputed claims ({'-' if j['first_two_agree'] is None else format(j['first_two_agree'], '.3f')} of all).", '',
          '| | Plain read | CatLog |', '|---|---|---|']

    def rate(s):
        b = s.get('bootstrap')
        if not b or s['papers_with_a_wrong_value'] < MIN_WRONG_PAPERS:
            return f"{s['wrong_per_1000']} (in {s['papers_with_a_wrong_value']} of {s['papers']} papers: too few for an interval)"
        return f"{s['wrong_per_1000']} ({b['per_1000_lo']:.1f}-{b['per_1000_hi']:.1f})"

    def scaled(s):
        b = s.get('bootstrap')
        if not b or s['scaled_per_1000'] is None or s['papers_with_a_wrong_value'] < MIN_WRONG_PAPERS:
            return str(s['scaled_per_1000'])  # too few wrong papers for an interval: the upper-limit row gives the uncertainty
        return f"{s['scaled_per_1000']} ({b['scaled_per_1000_lo']:.1f}-{b['scaled_per_1000_hi']:.1f})"

    def sample(s):
        x = s['sample']
        if not x['of']:
            return 'none'
        return f"{x['wrong']} of {x['of']} (exact {100 * x['exact_share'][0]:.2f}-{100 * x['exact_share'][1]:.2f}%)"

    def papers(s):
        lo, hi = s['papers_per_100_exact']
        return f"{s['papers_with_a_wrong_value_per_100']} ({lo}-{hi})"
    L += [f"| Values | {ps['values']} | {cs['values']} |",
          f"| Judged | {ps['values_judged']} | {cs['values_judged']} |",
          f"| Agreed, not judged | {ps['values_agreed_not_judged']} | {cs['values_agreed_not_judged']} |",
          f"| Wrong found | {ps['wrong']} | {cs['wrong']} |",
          f"| Wrong found per 1,000 (95% interval) | {rate(ps)} | {rate(cs)} |",
          f"| Papers with a wrong value found, per 100 (exact 95%) | {papers(ps)} | {papers(cs)} |",
          f"| Same, on papers where the source stored a value | {ps['share_on_papers_with_values']} of {ps['papers_with_values']} | "
          f"{cs['share_on_papers_with_values']} of {cs['papers_with_values']} |",
          f"| Agreed pairs sampled: wrong | {sample(ps)} | {sample(cs)} |",
          f"| Per 1,000 with the sample scaled to the unsampled pairs | {scaled(ps)} | {scaled(cs)} |",
          f"| Per 1,000 at the sample's upper limit | {ps['upper_limit_per_1000']} | {cs['upper_limit_per_1000']} |",
          f"| Cannot decide | {ps['cannot_decide']} | {cs['cannot_decide']} |",
          f"| Per 1,000, cannot-decide as wrong | {ps['sensitivity_cannot_decide_as_wrong_per_1000']} | "
          f"{cs['sensitivity_cannot_decide_as_wrong_per_1000']} |",
          f"| Per 1,000, 200 values per paper at most | {ps['sensitivity_cap_200_per_1000']} | {cs['sensitivity_cap_200_per_1000']} |",
          f"| Largest paper's share of wrong | {ps['largest_paper_share_of_wrong']} | {cs['largest_paper_share_of_wrong']} |",
          f"| Supported values only the other stored (misses) | {ps['misses_supported_values_only_the_other_stored']} | "
          f"{cs['misses_supported_values_only_the_other_stored']} |", '',
          "The rate with the sample scaled resamples papers only; it does not carry the sample's own uncertainty, which the "
          "exact line gives.", '']
    only = o['papers_wrong_in_one_source_only']
    L.append(f"Papers wrong in one source only: plain {only['plain']}, CatLog {only['catlog']}.")
    d = o.get('plain_minus_catlog')
    if d and only['plain'] + only['catlog'] >= MIN_WRONG_PAPERS:
        L.append(f"Plain minus CatLog, wrong per 1,000: {d['per_1000_lo']:.1f} to {d['per_1000_hi']:.1f}; papers with a wrong "
                 f"value per 100: {d['papers_per_100_lo']:.1f} to {d['papers_per_100_hi']:.1f} (paper-level bootstrap, B {d['B']}).")
    for s in SOURCES:
        L.append(f"Kinds ({s}): " + (', '.join(f'{k} {v}' for k, v in o['per_source'][s]['kinds'].items()) or 'none'))
    for m, b in o['by_reader_model'].items():
        L.append(f"Papers read by {m}: {b['papers']}.")
    ka = j['kappa_real_claims']
    L += ['', f"Judges: decoys called an error j1 {j['j1']['decoys_called_an_error']}/{j['j1']['decoys_judged']}, "
              f"j2 {j['j2']['decoys_called_an_error']}/{j['j2']['decoys_judged']}; kappa on real claims "
              f"{'-' if ka is None else round(ka, 3)}; third judge on {j['j3']['real_claims_judged']} real claims.",
          f"Sampled claims judged: {o['matched_sample']['claims']} ({o['matched_sample']['final']}).", '']
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=('triage', 'report'))
    ap.add_argument('papers', help='a tsv with a pmid column: all of papers.tsv and the first K of papers_more.tsv')
    ap.add_argument('--run', default='rand')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--scratch')
    ap.add_argument('--partial', action='store_true')
    ap.add_argument('--accept-left-out', action='store_true')
    ap.add_argument('--short', action='store_true')
    ap.add_argument('--B', type=int, default=SW.B_MAIN)
    ap.add_argument('--which', default='rand', choices=('rand', 'randfull', 'locked'),
                    help='report: the first judging, or the same values judged again with full records (score_randfull.py)')
    ap.add_argument('--eval', default=str(W.EVAL))
    a = ap.parse_args()
    W.check_run(a.run)
    if a.run != 'rand' and not a.scratch and not a.dry:
        sys.exit('another run\'s reads are scored only with --scratch or --dry (the rand claim folders are drawn once)')
    (triage if a.step == 'triage' else report)(Path(a.eval), a)


if __name__ == '__main__':
    main()
