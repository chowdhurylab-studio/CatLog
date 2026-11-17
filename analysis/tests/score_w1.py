#!/usr/bin/env python3
"""W1 scoring (RUN.md §6): every arm against the gold keys of other groups, the blind adjudication of the disputed
claims, the endpoints, the paired paper-clustered bootstrap and the STOP rule; and the second scorecard against
people's own verdicts on CatLog values.

  python3 tools/w1/score_w1.py rows   [--runs rounds|pilot]   arm values per arm-run (one duplicate rule) -> score/rows/
  python3 tools/w1/score_w1.py triage [--runs rounds|pilot]   gold matching, precision and recall, the claim pool with
                                                               decoys, blinded chunks -> score/claims/ (adjudicators),
                                                               score/private/ (the map back; scorer only)
  (then run_adjudicate.py)
  python3 tools/w1/score_w1.py decide [--runs rounds|pilot]   verdicts -> quality gate, endpoints, bootstrap, PASS/STOP
                                                               -> score/results.json, score/DECISION.md
  python3 tools/w1/score_w1.py people [--runs rounds|pilot]   people's verdicts: approved values found, rejected values
                                                               repeated, per arm -> score/people.json
  --runs pilot (dry) reads the pilot's (F6 dry run's) runs and writes to score_pilot/ (score_dry/), never into the
  decision.

The matcher is the head-to-head's own (h2h.py: a byte copy of paper/evidence/h2h_20261101/common.py, sha256
97ffb6e87c99..., and its s06 rows_to_values, sha256 fc3a9496ccdb...): per paper and metric, one-to-one pairs within
max(1.5%, 5e-7) in catalog units, most pairs first and closest description second. Co-Scientist gold covers its 107
papers (gold_values), EnzyExtract's manual set its 59 (rows_to_values: CatLog's units code on the gold strings);
11683888 is matched against the union. Gold bounds, zeros and unparsable cells are not scored.

Arms: A0 out/<code of A0-r<k>>/<PMID>.json; A2 out/<code of A2-r<k>-final>/<PMID>.json; A6 the rows `add` accepted,
records/runs/A6-r<k>/catalog.jsonl (censored values in bounds.jsonl are not scored), and for a paper A6 read again after
a model switch, records/runs/A6-r<k>/redo/. A paper-run fails when its file is missing or invalid (A0, A2), the paper is
not finished in A6's papers.tsv, or a model switch left it out (records/logs/<arm-run>/model_switch.json: outcome
'excluded', or for A6 'redo_pending'); a paper failed in any arm-run leaves every arm's paired analysis and is listed,
the model-switch ones apart. A paper an adjudicator's session left out the same way leaves the analysis too. The papers of
an arm-run are its order file (records/orders/<arm-run>.txt).

Choices RUN.md leaves open, fixed here before any output exists:
- claims merge by leader clustering (values sorted; each joins the first cluster whose leader agrees: same paper and
  metric, within 1.5%, same mutation set or both wild type, substrate token Jaccard >= 0.5); a merged claim is shown
  with the labels of one member drawn at random; 'nan' labels of the gold files show as blank;
- decoys: ceil(5%) of a paper's claims, at least 1, each a matched arm value (else a gold value) changed once (x1000
  or /1000, x60 or /60, another variant of the paper, kcat<->Km), never within 1.5% of a real value of the paper;
- the final verdict is the majority of the verdict classes (supported / an error / cannot_decide) of the first two
  judges, or of three when the two split, else cannot_decide; among errors the majority kind, else the third's; two
  errors of different kinds with no third stay an error ('mixed');
- cannot_decide values leave the primary rate (numerator and denominator) and count as errors in a sensitivity
  analysis; R is 1 in a resample where neither arm has an error and +inf where only A6 has none;
- identity-aware recall: true values are the supported claims and the gold values no arm-run left unmatched, joined
  when a claim names the same gold value; an arm-run stores a true value when one of its values is in a supported claim
  of it or its matched pair to the gold value was not identity-suspect (or its suspect claim was judged supported)."""
import argparse, collections, json, math, random, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_w1 as W  # noqa: E402
import h2h  # noqa: E402
import validate_plain as V  # noqa: E402
import numpy as np  # noqa: E402

C = h2h.C
UNIT = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}
ERRORS = ('wrong_number', 'wrong_scale', 'wrong_metric', 'wrong_identity', 'wrong_conditions', 'not_measured_here',
          'not_printed')
VERDICTS = ('supported',) + ERRORS + ('cannot_decide',)
DONE_A6 = W.DONE_A6
CHUNK = 40
SAMPLE_MATCHED = 100
DECOY_SHARE = 0.05
TOL_PEOPLE = 0.02   # HUMAN_REVIEW.md "How v2 is compared": values within 2% after unit conversion
B_MAIN = 10000


def paths(ev, which):
    return W.eval_paths(ev, which)


# ---------- arm values ----------

def arm_runs(which):
    rounds = [which] if which in W.SPECIAL_RUNS else list(W.ROUNDS)
    return [(arm, r) for arm in W.ARMS for r in rounds]


def run_papers(ev, arm, run):
    return W.read_order(ev, W.run_label(arm, run))


def switch_left_out(ev, arm, run):
    """Papers a model switch left out of this arm-run: {pmid: why}. A0/A2: a step whose second try switched too (any of
    A2's reads or its reconcile); A6: a paper whose redo switched again, or one still waiting for its redo."""
    log_dir = W.eval_paths(ev)['logs'] / W.run_label(arm, run)
    out = {}
    for lab, r in W.read_switches(log_dir).items():
        if r.get('outcome') in ('excluded', 'redo_pending'):
            out[str(r.get('pmid'))] = f"{r['outcome']} ({lab})"
    return out


def load_rows(ev, arm, run, papers):
    """(rows, status): rows as catalog-style dicts with pmid and row_id; status {pmid: ok|failed|model_switch}."""
    label = W.run_label(arm, run)
    rows, status = [], {}
    gone = switch_left_out(ev, arm, run)
    if arm in ('A0', 'A2'):
        for p in papers:
            if p in gone:
                status[p] = 'model_switch'
                continue
            f = W.out_file(ev, arm, run, 'final' if arm == 'A2' else None, p)
            ok, n, _ = V.check_file(f)
            d = json.loads(Path(f).read_text()) if ok else {}
            if not ok or str(d.get('pmid')) != str(p):
                status[p] = 'failed'
                continue
            status[p] = 'ok'
            for i, r in enumerate(d['rows']):
                rows.append({**r, 'pmid': p, 'row_id': f'{label}:{p}:{i}'})
        return rows, status
    d = W.eval_paths(ev)['runs'] / label
    redo = d / 'redo'
    redo_pmids = set()
    if (redo / 'RESET.json').exists():
        redo_pmids = {str(x) for x in json.loads((redo / 'RESET.json').read_text()).get('pmids') or []}

    def statuses(folder):
        return {r['pmid']: r['status'] for r in W.read_tsv(folder / 'papers.tsv')} if (folder / 'papers.tsv').exists() else {}
    st, st_redo = statuses(d), statuses(redo)
    for p in papers:
        if p in gone:
            status[p] = 'model_switch'
        else:
            status[p] = 'ok' if (st_redo if p in redo_pmids else st).get(p) in DONE_A6 else 'failed'
    for folder, mine in ((d, lambda p: p not in redo_pmids), (redo, lambda p: p in redo_pmids)):
        if (folder / 'catalog.jsonl').exists():
            with open(folder / 'catalog.jsonl') as fh:
                for line in fh:
                    if line.strip():
                        r = json.loads(line)
                        p = str(r.get('pmid'))
                        if status.get(p) == 'ok' and mine(p):
                            rows.append(r)
    return rows, status


def variant_key(v):
    m = C.mutations(v)
    if m:
        return ('mut',) + tuple(sorted(m))
    if C.is_wt(v) or not str(v or '').strip():
        return ('wt',)
    return ('other',) + tuple(sorted(C.norm_tokens(v)))


def num_or_none(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x) if math.isfinite(x) else None
    return C.fnum(x) if str(x or '').strip().lower() not in ('nan', 'none', 'null', '') else None


def dup_key(v):
    """RUN.md §6.2: same paper, metric, value to 4 significant figures and identity (mutation set or wild type,
    substrate tokens, pH, temperature)."""
    ph, t = num_or_none(v.get('pH')), num_or_none(v.get('temp'))
    return (v['pmid'], v['metric'], f"{float(v['value']):.4g}", variant_key(v['variant']),
            tuple(sorted(C.norm_tokens(v['substrate']))), None if ph is None else round(ph, 2),
            None if t is None else round(t, 1))


def dedup(values):
    seen, out, dups = set(), [], 0
    for v in values:
        k = dup_key(v)
        if k in seen:
            dups += 1
            continue
        seen.add(k)
        out.append(v)
    return out, dups


def arm_values(ev, arm, run, papers):
    rows, status = load_rows(ev, arm, run, papers)
    vals = C.catalog_values(rows, W.run_label(arm, run))
    for v in vals:
        v['id'] = str(v['id'])
    vals, dups = dedup(vals)
    return vals, status, dups


# ---------- gold ----------

def gold_sets():
    return {r['pmid']: r['gold_set'] for r in W.read_tsv(W.KIT / 'dev_165.tsv')}


def gold_for(papers):
    gs = gold_sets()
    papers = set(papers)
    out = [g for g in C.gold_values(papers) if gs.get(g['pmid']) in ('cosci', 'both')]
    ee, _ = h2h.rows_to_values(C.load_ee_manual_raw(), 'ee_manual', {p for p in papers if gs.get(p) in ('enzyextract', 'both')})
    return [{**g, 'id': str(g['id'])} for g in out + ee if g['value'] is not None]


# ---------- claims ----------

def label(x):
    s = str(x if x is not None else '').strip()
    return '' if s.lower() in ('nan', 'none', 'null') else s


def identity_disagrees(g, s):
    """RUN.md §6.4: the mutation sets differ, the substrate names share no token, or pH (temperature) differ by more
    than 0.05 (0.5 °C) where both give one."""
    if C.mutations(g['variant']) != C.mutations(s['variant']):
        return 'mutations'
    a, b = C.norm_tokens(label(g['substrate'])), C.norm_tokens(label(s['substrate']))
    if a and b and not (a & b):
        return 'substrate'
    for k, tol in (('pH', 0.05), ('temp', 0.5)):
        x, y = num_or_none(g.get(k)), num_or_none(s.get(k))
        if x is not None and y is not None and abs(x - y) > tol:
            return k
    return ''


def shown(v):
    """A claim as the adjudicator sees it: normalised, with no source, location, printed form or quote."""
    return {'metric': v['metric'], 'value': float(f"{float(v['value']):.4g}"), 'unit': UNIT[v['metric']],
            'enzyme': label(v.get('enzyme')), 'organism': label(v.get('organism')), 'variant': label(v.get('variant')),
            'substrate': label(v.get('substrate')), 'cosubstrate': label(v.get('cosub')),
            'pH': num_or_none(v.get('pH')), 'temperature_C': num_or_none(v.get('temp'))}


def mergeable(a, b):
    sa, sb = label(a['substrate']), label(b['substrate'])
    return (a['pmid'] == b['pmid'] and a['metric'] == b['metric'] and C.close(a['value'], b['value'])
            and variant_key(a['variant']) == variant_key(b['variant'])
            and (C.tok_sim(sa, sb) >= 0.5 or not (C.norm_tokens(sa) or C.norm_tokens(sb))))


def cluster(cands):
    """Leader clustering per paper and metric, in a fixed order."""
    clusters, by = [], collections.defaultdict(list)
    for c in sorted(cands, key=lambda c: (W.pmid_key(c['pmid']), c['metric'], c['value'], c['src'], c['id'])):
        for cl in by[(c['pmid'], c['metric'])]:
            if mergeable(cl[0], c):
                cl.append(c)
                break
        else:
            by[(c['pmid'], c['metric'])].append([c])
            clusters.append(by[(c['pmid'], c['metric'])][-1])
    return clusters


DECOY_KINDS = ('x1000', 'x60', 'variant', 'swap')


def make_decoys(pmid, n, matched, gold, real, rng):
    """n decoys for a paper: a matched arm value (else a gold value) changed once; never within 1.5% of a real value of
    the paper for the decoy's metric (and, for the variant kind, its new variant)."""
    base = matched or gold
    if not base:
        return []
    variants = sorted({label(v.get('variant')) for v in matched + gold if label(v.get('variant'))})
    out, start = [], rng.randrange(len(DECOY_KINDS))
    for t in range(50 * n):
        if len(out) >= n:
            break
        v = dict(rng.choice(base))
        kind = DECOY_KINDS[(start + t) % len(DECOY_KINDS)]
        if kind == 'x1000':
            v['value'] = v['value'] * (1000 if rng.random() < 0.5 else 1e-3)
        elif kind == 'x60':
            v['value'] = v['value'] * (60 if rng.random() < 0.5 else 1 / 60)
        elif kind == 'variant':
            others = [x for x in variants if variant_key(x) != variant_key(v.get('variant'))]
            if not others:
                continue
            v['variant'] = rng.choice(others)
        else:
            if v['metric'] == 'kcat/Km':
                continue
            v['metric'] = 'Km' if v['metric'] == 'kcat' else 'kcat'
        if any(r['metric'] == v['metric'] and C.close(r['value'], v['value']) and
               (kind != 'variant' or variant_key(r.get('variant')) == variant_key(v['variant'])) for r in real):
            continue
        out.append({**v, 'decoy': kind, 'src': 'decoy', 'id': f'decoy{len(out)}:{pmid}'})
    return out


def triage(ev, which):
    P = paths(ev, which)
    h2h.use_keys(P['keys'])
    out_claims = P['claims']
    if out_claims.exists() and any(out_claims.iterdir()):
        sys.exit(f'{out_claims} is not empty: the claim pool is drawn once (move it aside to draw again)')
    dev = set(W.dev_papers())
    runs = arm_runs(which)
    vals, status, dups = {}, {}, {}
    for arm, r in runs:
        vals[(arm, r)], status[(arm, r)], dups[(arm, r)] = arm_values(ev, arm, r, [p for p in run_papers(ev, arm, r) if p in dev])
    papers = sorted({p for k in status for p in status[k]}, key=W.pmid_key)
    failed = sorted({p for k in status for p, s in status[k].items() if s != 'ok'} |
                    {p for p in papers if any(p not in status[k] for k in status)}, key=W.pmid_key)
    gold = gold_for(papers)
    rng = random.Random(W.SEED_POOL)
    cands, per_run, matched_pool = [], {}, collections.defaultdict(list)
    gold_unmatched_by = collections.defaultdict(set)
    for (arm, r), sv in vals.items():
        lab = W.run_label(arm, r)
        ok = {p for p, s in status[(arm, r)].items() if s == 'ok'}
        g_ok = [g for g in gold if g['pmid'] in ok]
        pairs, gu, su = C.match(g_ok, sv)
        flags = {}
        for gi, si, sim in pairs:
            why = identity_disagrees(g_ok[gi], sv[si])
            flags[sv[si]['id']] = {'gold': g_ok[gi]['id'], 'identity': why, 'pmid': sv[si]['pmid']}
            if why:
                cands.append({**sv[si], 'src': lab, 'kind': 'identity_suspect', 'gold_id': g_ok[gi]['id']})
            else:
                matched_pool[arm].append({**sv[si], 'src': lab, 'kind': 'matched_sample', 'gold_id': g_ok[gi]['id']})
        for si in su:
            cands.append({**sv[si], 'src': lab, 'kind': 'unmatched'})
        for gi in gu:
            gold_unmatched_by[g_ok[gi]['id']].add(lab)
        s = C.summarize(g_ok, sv, pairs, sorted(ok, key=W.pmid_key), B=2000)
        per_run[lab] = {'papers_ok': len(ok), 'failed': sorted(set(status[(arm, r)]) - ok, key=W.pmid_key),
                        'duplicates_dropped': dups[(arm, r)], 'values': len(sv), 'gold_n': s['all']['gold_n'],
                        'matched': s['all']['matched'], 'precision': s['all']['precision'], 'recall': s['all']['recall'],
                        'by_metric': {m: {'precision': s[m]['precision']['est'], 'recall': s[m]['recall']['est'],
                                          'gold_n': s[m]['gold_n'], 'sys_n': s[m]['sys_n'], 'matched': s[m]['matched']}
                                      for m in C.METRICS},
                        'pairs': flags}
    gid = {g['id']: g for g in gold}
    for g_id in sorted(gold_unmatched_by):
        cands.append({**gid[g_id], 'src': 'gold', 'kind': 'gold_unmatched', 'unmatched_by': sorted(gold_unmatched_by[g_id])})
    for arm in W.ARMS:
        pool = sorted(matched_pool[arm], key=lambda v: (v['src'], v['id']))
        cands += rng.sample(pool, min(SAMPLE_MATCHED, len(pool)))
    by_paper = collections.defaultdict(list)
    for cl in cluster(cands):
        rep = rng.choice(cl)
        by_paper[rep['pmid']].append({
            'pmid': rep['pmid'], 'metric': rep['metric'], 'shown': shown(rep), 'decoy': '',
            'members': [{'src': c['src'], 'id': c['id'], 'kind': c['kind'], 'value': c['value'],
                         **({'unmatched_by': c['unmatched_by']} if 'unmatched_by' in c else {}),
                         **({'gold_id': c['gold_id']} if 'gold_id' in c else {})} for c in cl]})
    real_by, matched_by = collections.defaultdict(list), collections.defaultdict(list)
    for v in gold:
        real_by[v['pmid']].append(v)
    for sv in vals.values():
        for v in sv:
            real_by[v['pmid']].append(v)
    for arm in W.ARMS:
        for v in matched_pool[arm]:
            matched_by[v['pmid']].append(v)
    for p in sorted(by_paper, key=W.pmid_key):
        k = max(1, math.ceil(DECOY_SHARE * len(by_paper[p])))
        for d in make_decoys(p, k, sorted(matched_by[p], key=lambda v: (v['src'], v['id'])),
                             [g for g in gold if g['pmid'] == p], real_by[p], rng):
            by_paper[p].append({'pmid': p, 'metric': d['metric'], 'shown': shown(d), 'decoy': d['decoy'],
                                'members': [{'src': 'decoy', 'id': d['id'], 'kind': 'decoy', 'value': d['value']}]})
    used, cmap = set(), []
    for p in sorted(by_paper, key=W.pmid_key):
        cl = by_paper[p]
        rng.shuffle(cl)
        for i in range(0, len(cl), CHUNK):
            chunk = f'c{i // CHUNK + 1:02d}'
            rows = []
            for c in cl[i:i + CHUNK]:
                cid = None
                while cid is None or cid in used:
                    cid = f'{rng.getrandbits(32):08x}'
                used.add(cid)
                rows.append({'id': cid, **c['shown']})
                cmap.append({'claim_id': cid, 'pmid': p, 'chunk': chunk, 'metric': c['metric'], 'decoy': c['decoy'],
                             'members': c['members'], 'shown': c['shown']})
            W.write_json(out_claims / f'{p}.{chunk}.json', rows)
    priv = P['score'] / 'private'
    priv.mkdir(parents=True, exist_ok=True)
    with open(priv / 'claims_map.jsonl', 'w') as fh:
        for c in cmap:
            fh.write(json.dumps(c) + '\n')
    switched = {W.run_label(arm, r): sorted((p for p, s in status[(arm, r)].items() if s == 'model_switch'), key=W.pmid_key)
                for arm, r in runs}
    summary = {'which': which, 'time': W.now(), 'papers': papers, 'failed_any_arm': failed,
               'left_out_model_switch': {k: v for k, v in switched.items() if v}, 'gold_values': len(gold),
               'claims': len(cmap), 'decoys': sum(1 for c in cmap if c['decoy']),
               'chunks': len({(c['pmid'], c['chunk']) for c in cmap}), 'seed': W.SEED_POOL}
    W.write_json(priv / 'triage.json', {**summary, 'per_run': per_run})
    W.write_json(P['score'] / 'gold_scores.json', {lab: {k: v for k, v in d.items() if k != 'pairs'} for lab, d in per_run.items()})
    print(f"claims {summary['claims']} ({summary['decoys']} decoys) in {summary['chunks']} chunks; papers failed in "
          f"some arm-run: {len(failed)}")
    for lab, d in per_run.items():
        print(f"  {lab}: values {d['values']} (dups {d['duplicates_dropped']}), matched {d['matched']} of gold "
              f"{d['gold_n']}, precision {d['precision']['est']}, recall {d['recall']['est']}")


# ---------- verdicts and endpoints ----------

def klass(v):
    return None if v is None else 'supported' if v == 'supported' else 'cannot_decide' if v == 'cannot_decide' else 'error'


def final_verdict(v1, v2, v3=None):
    """(final verdict or None while pending, whether a third judge is needed)."""
    if v1 is None or v2 is None:
        return None, False
    if klass(v1) == klass(v2):
        return (v1 if v1 == v2 or klass(v1) != 'error' else 'mixed'), False
    if v3 is None:
        return None, True
    ks = [klass(v1), klass(v2), klass(v3)]
    win = [k for k in set(ks) if ks.count(k) >= 2]
    if not win:
        return 'cannot_decide', True
    if win[0] != 'error':
        return win[0], True
    errs = [v for v in (v1, v2, v3) if klass(v) == 'error']
    kinds = [k for k in set(errs) if errs.count(k) >= 2]
    return (kinds[0] if kinds else v3 if klass(v3) == 'error' else errs[0]), True


def load_verdicts(P):
    out = {}
    for j in W.JUDGES:
        for f in sorted(P['verdicts'][j].glob('*.json')):
            try:
                d = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            for v in d.get('verdicts') or []:
                if isinstance(v, dict) and v.get('verdict') in VERDICTS:
                    out.setdefault(str(v.get('id')), {}).setdefault(j, v['verdict'])
    return out


def kappa(a, b):
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(k) / n) * (b.count(k) / n) for k in set(a) | set(b))
    return None if pe == 1 else (po - pe) / (1 - pe)


def ratio(num, den):
    return num / den if den else None


def r_of(x, y):
    """R = x / y, with 1 when both are 0 and +inf when only y is 0."""
    if x is None or y is None:
        return None
    return x / y if y > 0 else (math.inf if x > 0 else 1.0)


def boot_ratio(e, n, B, seed, pair=('A2', 'A6'), two_stage=None):
    """Paired, paper-clustered bootstrap (papers resampled with replacement, the same resample for both arms) of
    R = rate(pair[0]) / rate(pair[1]) and of the rate difference per 1,000. two_stage: one run per arm and paper drawn
    at random in each resample instead of the run mean."""
    papers = len(e[pair[0]])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, papers, size=(B, papers))
    rates = {}
    for a in pair:
        if two_stage is not None:
            er, nr = two_stage[a]
            pick = rng.integers(0, er.shape[1], size=(B, papers))
            E = np.take_along_axis(er[idx], pick[..., None], 2)[..., 0].sum(1)
            N = np.take_along_axis(nr[idx], pick[..., None], 2)[..., 0].sum(1)
        else:
            E, N = e[a][idx].sum(1), n[a][idx].sum(1)
        rates[a] = np.where(N > 0, E / np.where(N > 0, N, 1), 0.0)
    x, y = rates[pair[0]], rates[pair[1]]
    R = np.where(y > 0, x / np.where(y > 0, y, 1), np.where(x > 0, np.inf, 1.0))
    D = (x - y) * 1000
    return {'R_lo': float(np.percentile(R, 2.5, method='lower')), 'R_hi': float(np.percentile(R, 97.5, method='higher')),
            'diff_per_1000': float((e[pair[0]].sum() / max(n[pair[0]].sum(), 1e-300) - e[pair[1]].sum() / max(n[pair[1]].sum(), 1e-300)) * 1000),
            'diff_lo': float(np.percentile(D, 2.5)), 'diff_hi': float(np.percentile(D, 97.5)),
            'share_R_at_least_2': float((R >= 2).mean()), 'B': B, 'seed': seed}


def glyph_and_kind(ev):
    """Text kind and GLYPH WARNING per paper as set up (MANIFEST.json), else as dev_165.tsv lists them."""
    m = W.eval_paths(ev)['manifest']
    if m.exists():
        inp = json.loads(m.read_text()).get('inputs', {})
        return {p: (d.get('text_kind'), bool(d.get('glyph_warning'))) for p, d in inp.items()}
    return {r['pmid']: (r['text_kind'], r['glyph_warning'] == '1') for r in W.read_tsv(W.KIT / 'dev_165.tsv')}


def costs(ev, runs):
    """Tokens, dollars and minutes per paper-run and arm, counted one way for every arm (REVIEW.md 2.4): the four usage
    fields once per message id from each agent's transcript (w1_audit.py's audit/<run>/tokens.json, the kit's counting
    in A2_compute_matched_prompt.md "Sizing"). A plain arm-run not audited yet falls back to Claude Code's own session
    totals (logs/<run>/sessions.tsv), and `method` says so."""
    P = W.eval_paths(ev)
    out = collections.defaultdict(lambda: collections.Counter())
    papers = collections.defaultdict(set)
    method = collections.defaultdict(set)
    for arm, r in runs:
        lab = W.run_label(arm, r)
        f = P['audit'] / lab / 'tokens.json'
        if f.exists():
            method[arm].add('transcripts (audit/<run>/tokens.json)')
            for row in json.loads(f.read_text()):
                papers[arm].add((lab, row.get('pmid')))
                out[arm]['tokens'] += row.get('total') or 0
                out[arm]['usd'] += row.get('usd') or 0
                out[arm]['minutes'] += row.get('minutes') or 0
        elif arm in ('A0', 'A2'):
            s = P['logs'] / lab / 'sessions.tsv'
            if s.exists():
                method[arm].add('claude_code_session_totals (no audit yet)')
            for row in (W.read_tsv(s) if s.exists() else []):
                papers[arm].add((lab, row['pmid']))
                for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'):
                    out[arm]['tokens'] += float(row.get(k) or 0)
                out[arm]['usd'] += float(row.get('cost_usd') or 0) if row.get('cost_usd') not in ('', 'None') else 0
                out[arm]['minutes'] += float(row.get('seconds') or 0) / 60
    return {a: {k: (v / len(papers[a]) if papers[a] else None) for k, v in out[a].items()}
               | {'paper_runs': len(papers[a]), 'method': sorted(method[a])} for a in W.ARMS}


def decide(ev, which, B=B_MAIN):
    P = paths(ev, which)
    h2h.use_keys(P['keys'])
    tri = json.loads((P['score'] / 'private' / 'triage.json').read_text())
    cmap = [json.loads(line) for line in (P['score'] / 'private' / 'claims_map.jsonl').read_text().splitlines() if line]
    ver = load_verdicts(P)
    # a judge session that switched model on both tries leaves its paper out (claude_session.step, model_switch.json)
    adj_log = P['logs'] / ('adjudication' if which not in W.SPECIAL_RUNS else f'adjudication_{which}')
    adj_out = set(W.switch_excluded(adj_log))
    final, pending, firsts = {}, [], []
    for c in cmap:
        if c['pmid'] in adj_out:
            final[c['claim_id']] = None
            continue
        v = ver.get(c['claim_id'], {})
        f, _ = final_verdict(v.get('j1'), v.get('j2'), v.get('j3'))
        if v.get('j1') and v.get('j2'):
            firsts.append((klass(v['j1']), klass(v['j2'])))
        if f is None:
            pending.append(c['claim_id'])
        final[c['claim_id']] = f
    decoys = [c for c in cmap if c['decoy'] and c['pmid'] not in adj_out]
    caught = sum(1 for c in decoys if klass(final[c['claim_id']]) == 'error')
    agree = sum(1 for a, b in firsts if a == b)
    gate = {'claims': len(cmap), 'decoys': len(decoys), 'decoys_caught': caught, 'decoy_catch': ratio(caught, len(decoys)),
            'first_two_agree': ratio(agree, len(firsts)), 'kappa': kappa([a for a, _ in firsts], [b for _, b in firsts]),
            'pending_claims': len(pending), 'papers_left_out_by_a_judge_model_switch': sorted(adj_out, key=W.pmid_key)}
    gate['passed'] = bool(gate['decoy_catch'] is not None and gate['decoy_catch'] >= 0.9 and
                          gate['first_two_agree'] is not None and gate['first_two_agree'] >= 0.85 and not pending)
    of_value = {}
    for c in cmap:
        for m in c['members']:
            if m['src'] not in ('gold', 'decoy'):
                of_value[(m['src'], str(m['id']))] = final[c['claim_id']]
    dev = set(W.dev_papers())
    failed = set(tri['failed_any_arm']) | adj_out
    analysis = [p for p in tri['papers'] if p not in failed and p in dev]
    A = set(analysis)
    runs = arm_runs(which)
    rounds = sorted({r for _, r in runs}, key=str)
    nr = len(rounds)
    per = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    classes = collections.defaultdict(collections.Counter)
    sample = collections.defaultdict(collections.Counter)
    outside = collections.defaultdict(collections.Counter)  # matched values outside the pool, mean per run
    for arm, r in runs:
        lab = W.run_label(arm, r)
        vals, _, _ = arm_values(ev, arm, r, [p for p in run_papers(ev, arm, r) if p in A])
        pairs = tri['per_run'][lab]['pairs']
        for v in vals:
            c = per[arm][v['pmid']]
            c[f'n:{r}'] += 1
            f = of_value.get((lab, v['id']))
            if f is None:
                if v['id'] in pairs:
                    outside[arm][v['pmid']] += 1 / nr
                continue
            k = klass(f)
            if k == 'error':
                c[f'e:{r}'] += 1
                classes[arm][f] += 1
            elif k == 'cannot_decide':
                c[f'cd:{r}'] += 1
            if v['id'] in pairs and not pairs[v['id']]['identity']:
                sample[arm]['n'] += 1
                sample[arm]['errors'] += k == 'error'

    def arrays(arm, cd_as_error=False, cap=None, add_sample=False):
        e, n = [], []
        for p in analysis:
            c = per[arm][p]
            ee = sum(c[f'e:{r}'] + (c[f'cd:{r}'] if cd_as_error else 0) for r in rounds) / nr
            nn = sum(c[f'n:{r}'] - (0 if cd_as_error else c[f'cd:{r}']) for r in rounds) / nr
            if add_sample and sample[arm]['n']:
                ee += outside[arm][p] * sample[arm]['errors'] / sample[arm]['n']
            if cap and nn > cap:
                ee, nn = ee * cap / nn, cap
            e.append(ee)
            n.append(nn)
        return np.array(e, float), np.array(n, float)

    def per_run_arrays(arm):
        er = np.array([[per[arm][p][f'e:{r}'] for r in rounds] for p in analysis], float).reshape(len(analysis), nr)
        nn = np.array([[per[arm][p][f'n:{r}'] - per[arm][p][f'cd:{r}'] for r in rounds] for p in analysis], float)
        return er, nn.reshape(len(analysis), nr)

    def endpoint(**variant):
        e, n = {}, {}
        for arm in W.ARMS:
            e[arm], n[arm] = arrays(arm, **variant)
        rates = {a: (1000 * e[a].sum() / n[a].sum() if n[a].sum() else None) for a in W.ARMS}
        return e, n, rates, r_of(rates['A2'], rates['A6'])

    out = {'which': which, 'time': W.now(), 'papers_in_analysis': len(analysis), 'papers_excluded_failed': sorted(failed),
           'papers_excluded_model_switch': {'arms': tri.get('left_out_model_switch', {}),
                                            'adjudication': sorted(adj_out, key=W.pmid_key)},
           'quality_gate': gate, 'rounds': [str(r) for r in rounds],
           'decision_rule': 'PASS if R = rate(A2) / rate(A6) >= 2.0 and the lower end of its paired, paper-clustered '
                            '95% CI is above 1; else STOP (RUN.md §1)'}
    if not analysis:
        out['decision'] = 'no papers to analyse'
    else:
        e, n, rates, R = endpoint()
        bs = boot_ratio(e, n, B, W.SEED_BOOT)
        passed = R is not None and R >= 2.0 and bs['R_lo'] > 1
        out['primary'] = {'rate_per_1000': rates, 'R_A2_over_A6': R, **bs,
                          'stored_values_mean_per_run': {a: float(n[a].sum()) for a in W.ARMS},
                          'errors_mean_per_run': {a: float(e[a].sum()) for a in W.ARMS}}
        out['secondary'] = {'A0_over_A6': {'R': r_of(rates['A0'], rates['A6']), **boot_ratio(e, n, B, W.SEED_BOOT, ('A0', 'A6'))},
                            'A0_over_A2': {'R': r_of(rates['A0'], rates['A2']), **boot_ratio(e, n, B, W.SEED_BOOT, ('A0', 'A2'))}}
        out['errors_by_class_mean_per_run'] = {a: {k: v / nr for k, v in sorted(classes[a].items())} for a in W.ARMS}
        out['papers_with_error_share'] = {a: float(np.mean([np.mean([per[a][p][f'e:{r}'] > 0 for p in analysis])
                                                            for r in rounds])) for a in W.ARMS}
        out['run_rates_per_1000'] = {a: {str(r): ratio(1000 * sum(per[a][p][f'e:{r}'] for p in analysis),
                                                       sum(per[a][p][f'n:{r}'] - per[a][p][f'cd:{r}'] for p in analysis))
                                         for r in rounds} for a in W.ARMS}
        out['matched_sample'] = {a: dict(sample[a]) for a in W.ARMS}
        sens = {}
        for name, variant in (('cannot_decide_as_error', {'cd_as_error': True}), ('cap_200_values', {'cap': 200}),
                              ('matched_sample_errors_added', {'add_sample': True})):
            e2, n2, r2, R2 = endpoint(**variant)
            sens[name] = {'rate_per_1000': r2, 'R_A2_over_A6': R2, **boot_ratio(e2, n2, B, W.SEED_BOOT)}
        if nr > 1:
            sens['two_stage'] = {'R_A2_over_A6': R, **boot_ratio(e, n, B, W.SEED_BOOT,
                                                                 two_stage={a: per_run_arrays(a) for a in ('A2', 'A6')})}
        out['sensitivity'] = sens
        out['recall_identity_aware'] = recall_identity(tri, cmap, final, A, runs)
        out['strata_rate_per_1000'] = strata_rates(per, analysis, rounds, glyph_and_kind(ev))
        out['cost_per_paper_run'] = cst = costs(ev, runs)
        a2t, a6t = (cst.get('A2') or {}).get('tokens'), (cst.get('A6') or {}).get('tokens')
        same = cst.get('A2', {}).get('method') == cst.get('A6', {}).get('method')
        out['sizing'] = {'tokens_A2_over_A6': ratio(a2t, a6t) if a2t is not None and a6t is not None and same else None,
                         'counting': {a: cst.get(a, {}).get('method') for a in ('A2', 'A6')},
                         'rule': 'pilot: at least 0.9, else A2 gets a third read (run_plain.py/run_reconcile.py --reads 3); '
                                 'both arms counted from transcripts (run w1_audit.py on A2 and A6 first)'}
        rec = out['recall_identity_aware']
        cost = bool(passed and rec.get('A6') is not None and rec.get('A2') is not None and rec['A6'] < rec['A2'] - 0.03)
        out['decision'] = ('PASS with a recall cost' if cost else 'PASS') if passed else 'STOP'
        if not gate['passed']:
            out['decision_note'] = ('the adjudication quality gate did not pass (decoy catch below 90%, first-two '
                                    'agreement below 85%, or claims pending): revise the prompt, re-tag and judge every '
                                    'claim again before reading the decision (RUN.md §6.5)')
    W.write_json(P['score'] / 'results.json', out)
    (P['score'] / 'DECISION.md').write_text(decision_md(out))
    print(json.dumps({k: out.get(k) for k in ('decision', 'papers_in_analysis', 'quality_gate')}, indent=1, default=str))
    if 'primary' in out:
        pr = out['primary']
        print(f"rates per 1,000: {pr['rate_per_1000']}; R = {pr['R_A2_over_A6']} (95% CI {pr['R_lo']} to {pr['R_hi']})")
    return out


def recall_identity(tri, cmap, final, A, runs):
    """Identity-aware recall per arm (runs averaged), pooled over papers: see the module docstring."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    suspect_ok, claims_of = {}, {}
    gold_in_claims = set()
    for c in cmap:
        if c['decoy'] or c['pmid'] not in A:
            continue
        node = 'c:' + c['claim_id']
        find(node)
        claims_of[node] = c
        for m in c['members']:
            if m['src'] == 'gold':
                union(node, 'g:' + m['id'])
                gold_in_claims.add(m['id'])
            if m.get('gold_id'):
                union(node, 'g:' + m['gold_id'])
            if m['kind'] == 'identity_suspect':
                suspect_ok[(m['src'], str(m['id']))] = final.get(c['claim_id']) == 'supported'
    labs = [W.run_label(a, r) for a, r in runs]
    cover_gold = collections.defaultdict(set)
    gold_seen = set()
    for lab in labs:
        for sid, f in tri['per_run'][lab]['pairs'].items():
            if f.get('pmid') not in A:
                continue
            gold_seen.add(f['gold'])
            if not f['identity'] or suspect_ok.get((lab, sid), False):
                cover_gold[f['gold']].add(lab)
    comps = collections.defaultdict(lambda: {'claims': [], 'gold': set()})
    for node, c in claims_of.items():
        comps[find(node)]['claims'].append(c)
    for g in gold_seen:
        comps[find('g:' + g)]['gold'].add(g)
    true_items = []
    for root, comp in comps.items():
        if comp['claims']:
            if any(final.get(c['claim_id']) == 'supported' for c in comp['claims']):
                true_items.append(comp)
        elif comp['gold'] and all(g not in gold_in_claims for g in comp['gold']):
            true_items.append(comp)  # matched by every arm-run: taken as supported
    out = {'universe': len(true_items)}
    for arm in W.ARMS:
        mine = [W.run_label(a, r) for a, r in runs if a == arm]
        covered = 0.0
        for t in true_items:
            for lab in mine:
                in_claim = any(final.get(c['claim_id']) == 'supported' and any(m['src'] == lab for m in c['members'])
                               for c in t['claims'])
                by_pair = any(lab in cover_gold.get(g, ()) for g in t['gold'])
                covered += (in_claim or by_pair) / len(mine)
        out[arm] = covered / len(true_items) if true_items else None
    return out


def strata_rates(per, analysis, rounds, kinds):
    out = {}
    for name, test in (('glyph_warning', lambda p: kinds.get(p, (None, False))[1]),
                       ('no_glyph_warning', lambda p: not kinds.get(p, (None, False))[1]),
                       ('xml', lambda p: kinds.get(p, (None,))[0] == 'xml'),
                       ('pdf_or_ocr', lambda p: kinds.get(p, (None,))[0] in ('pdf', 'ocr'))):
        ps = [p for p in analysis if test(p)]
        out[name] = {'papers': len(ps)}
        for a in W.ARMS:
            e = sum(per[a][p][f'e:{r}'] for p in ps for r in rounds)
            n = sum(per[a][p][f'n:{r}'] - per[a][p][f'cd:{r}'] for p in ps for r in rounds)
            out[name][a] = ratio(1000 * e, n)
    return out


def decision_md(o):
    g = o['quality_gate']
    lines = ['# W1 decision (draft written by tools/w1/score_w1.py decide)', '',
             f"Runs: {o['which']}. Papers in the paired analysis: {o['papers_in_analysis']} (excluded, failed in some "
             f"arm-run: {len(o['papers_excluded_failed'])}; of them left out because a session switched model on both "
             f"tries: {o.get('papers_excluded_model_switch')}). Written {o['time']}.", '',
             f"Quality gate: decoys caught {g['decoys_caught']} of {g['decoys']}, the first two adjudicators agree on "
             f"{g['first_two_agree']} of claims (kappa {g['kappa']}), claims pending {g['pending_claims']}: "
             f"{'passed' if g['passed'] else 'NOT passed'}.", '']
    if 'primary' in o:
        p = o['primary']
        lines += [f"Consequential errors per 1,000 stored values (runs averaged per paper): {p['rate_per_1000']}.",
                  f"R = rate(A2) / rate(A6) = {p['R_A2_over_A6']} (paired, paper-clustered 95% CI {p['R_lo']} to "
                  f"{p['R_hi']}; {p['B']} resamples, seed {p['seed']}).", '',
                  f"**{o['decision']}**: {o['decision_rule']}.", '']
        if o.get('decision_note'):
            lines += [o['decision_note'], '']
        lines += [f"Identity-aware recall: {o['recall_identity_aware']}.", '',
                  'Secondary numbers, sensitivity analyses, strata, run-to-run spread and cost: score/results.json.']
    else:
        lines += [o.get('decision', '')]
    return '\n'.join(lines) + '\n'


# ---------- people's verdicts ----------

def people_match(pv, sv):
    """One-to-one pairs of people values and arm values of one paper and metric: within 2%, the same mutation set and,
    when both name one, a substrate sharing a token; the most similar substrate wins."""
    from scipy.optimize import linear_sum_assignment
    if not pv or not sv:
        return []
    cost = np.full((len(pv), len(sv)), 1e6)
    for i, h in enumerate(pv):
        hv = C.num(h['human_value'])
        for j, s in enumerate(sv):
            if not hv or hv <= 0 or abs(hv - s['value']) > TOL_PEOPLE * max(hv, s['value']):
                continue
            if C.mutations(h.get('mutations')) != C.mutations(s['variant']):
                continue
            a, b = C.norm_tokens(h.get('substrate')), C.norm_tokens(s['substrate'])
            if a and b and not (a & b):
                continue
            cost[i, j] = -(1 + C.tok_sim(h.get('substrate'), s['substrate']))
    if not (cost < 0).any():
        return []
    ra, cb = linear_sum_assignment(cost)
    return [(i, j) for i, j in zip(ra, cb) if cost[i, j] < 0]


PEOPLE_ORIGIN = {'agree': 'catlog_had', 'reviewed_in_v2': 'catlog_had', 'v2_lacks': 'catlog_lacked',
                 'v2_different_value': 'catlog_lacked', 'paper_not_read': 'catlog_lacked'}


def people_origin(h):
    """Where a people-checked value came from (REVIEW.md 3.4): a value production CatLog already holds (bucket agree,
    reviewed_in_v2), one it lacked or read otherwise, or one a reviewer typed in (stated)."""
    return 'stated' if h['kind'] == 'stated' else PEOPLE_ORIGIN.get(h.get('bucket', ''), 'other')


def people(ev, which):
    P = paths(ev, which)
    key = W.read_tsv(P['keys'] / 'people_values.tsv')
    pp = set(W.people_papers())
    good = [r for r in key if r['kind'] in ('approved', 'stated') and C.num(r['human_value'])]
    bad = [r for r in key if r['kind'] == 'rejected_dispute' and C.num(r['human_value'])]
    cleared = [r for r in key if r['kind'] == 'rejected_cleared' and C.num(r['human_value'])]
    origins = ('catlog_had', 'catlog_lacked', 'stated', 'other')
    out = {'which': which, 'time': W.now(), 'approved_values': len(good), 'rejected_values': len(bad),
           'cleared_values': len(cleared),
           'approved_by_origin': dict(collections.Counter(people_origin(h) for h in good)),
           'note': 'approved = approved or stated by a reviewer (derived kcat/Km and approvals with an objection left '
                   'out); rejected = rejections that dispute the number, except those the human-review guideline '
                   'checked against the paper and cleared (cleared: storing them is right, reported apart); matched '
                   'within 2%, same mutation set, a shared substrate token (an approximation of HUMAN_REVIEW.md "How v2 '
                   'is compared"). The approved values are mostly values production CatLog already holds '
                   '(origin catlog_had), so "found" partly measures agreement with CatLog\'s own earlier reads and '
                   'favours A6 by construction; catlog_lacked (values CatLog lacked or read otherwise) and stated '
                   '(values reviewers typed in) do not. Reviewer verdicts are evidence, not ground truth.',
           'arms': {}}
    for arm in W.ARMS:
        per_paper = collections.defaultdict(collections.Counter)
        nruns = 0
        for a, r in arm_runs(which):
            papers = [p for p in run_papers(ev, arm, r) if p in pp] if a == arm else []
            if not papers:
                continue
            nruns += 1
            vals, status, _ = arm_values(ev, arm, r, papers)
            for p in papers:
                c = per_paper[p]
                if status.get(p) != 'ok':
                    c['failed_runs'] += 1
                    continue
                c['runs'] += 1
                sv = [v for v in vals if v['pmid'] == p]
                c['stored'] += len(sv)
                for m in C.METRICS:
                    s_m = [v for v in sv if v['metric'] == m]
                    g_m = [h for h in good if h['pmid'] == p and h['metric'] == m]
                    b_m = [h for h in bad if h['pmid'] == p and h['metric'] == m]
                    k_m = [h for h in cleared if h['pmid'] == p and h['metric'] == m]
                    c['approved'] += len(g_m)
                    pairs = people_match(g_m, s_m)
                    c['found'] += len(pairs)
                    for o in origins:
                        c[f'approved:{o}'] += sum(1 for h in g_m if people_origin(h) == o)
                    for i, _ in pairs:
                        c[f'found:{people_origin(g_m[i])}'] += 1
                    c['rejected'] += len(b_m)
                    c['repeated'] += len(people_match(b_m, s_m))
                    c['cleared'] += len(k_m)
                    c['cleared_stored'] += len(people_match(k_m, s_m))
        ps = [p for p in sorted(per_paper, key=W.pmid_key) if per_paper[p]['runs']]
        tot = {k: sum(per_paper[p][k] for p in ps) for k in ('approved', 'found', 'rejected', 'repeated', 'cleared',
                                                              'cleared_stored', 'stored')}
        res = {'runs': nruns, 'papers': len(ps), 'paper_runs_failed': sum(per_paper[p]['failed_runs'] for p in per_paper),
               **tot, 'approved_found_share': ratio(tot['found'], tot['approved']),
               'approved_found_share_by_origin': {o: ratio(sum(per_paper[p][f'found:{o}'] for p in ps),
                                                           sum(per_paper[p][f'approved:{o}'] for p in ps))
                                                  for o in origins if sum(per_paper[p][f'approved:{o}'] for p in ps)},
               'rejected_repeated_share': ratio(tot['repeated'], tot['rejected']),
               'cleared_stored_share': ratio(tot['cleared_stored'], tot['cleared'])}
        if not tot['rejected']:
            res['rejected_note'] = ('no disputed value left to score: every value rejection on these papers was checked '
                                    'against the paper and cleared (reported as cleared_stored)')
        if ps:
            import pandas as pd
            d = pd.DataFrame([{'pmid': p, **{k: per_paper[p][k] for k in ('approved', 'found', 'rejected', 'repeated')}}
                              for p in ps])
            res['approved_found_ci'] = C.boot(d, 'found', 'approved', B=2000, seed=W.SEED_BOOT)
            res['rejected_repeated_ci'] = C.boot(d, 'repeated', 'rejected', B=2000, seed=W.SEED_BOOT)
        out['arms'][arm] = res
    W.write_json(P['score'] / 'people.json', out)
    print(json.dumps({a: {k: v for k, v in d.items() if not k.endswith('_ci')} for a, d in out['arms'].items()}, indent=1))
    return out


def rows_cmd(ev, which):
    P = paths(ev, which)
    out = {}
    for arm, r in arm_runs(which):
        lab = W.run_label(arm, r)
        vals, status, dups = arm_values(ev, arm, r, run_papers(ev, arm, r))
        d = P['score'] / 'rows'
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f'{lab}.jsonl', 'w') as fh:
            for v in vals:
                fh.write(json.dumps(v, default=str) + '\n')
        out[lab] = {'values': len(vals), 'duplicates_dropped': dups,
                    'papers_ok': sum(1 for s in status.values() if s == 'ok'),
                    'papers_failed': sorted((p for p, s in status.items() if s != 'ok'), key=W.pmid_key)}
        print(f"{lab}: {out[lab]['values']} values (dups {dups}), papers ok {out[lab]['papers_ok']}, "
              f"failed {len(out[lab]['papers_failed'])}")
    W.write_json(P['score'] / 'rows' / 'summary.json', out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=('rows', 'triage', 'decide', 'people'))
    ap.add_argument('--runs', default='rounds', choices=('rounds', 'pilot', 'dry'))
    ap.add_argument('--eval', default=str(W.EVAL))
    ap.add_argument('--B', type=int, default=B_MAIN, help='bootstrap resamples (decide; 10,000 by RUN.md)')
    a = ap.parse_args()
    ev = Path(a.eval)
    if a.step == 'decide':
        decide(ev, a.runs, a.B)
    else:
        {'rows': rows_cmd, 'triage': triage, 'people': people}[a.step](ev, a.runs)


if __name__ == '__main__':
    main()
