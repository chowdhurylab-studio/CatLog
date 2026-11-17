"""Every number the Results section on the plain model against CatLog cites (pilot, hard cases, random test), computed
from the record files, into r2_numbers.json next to this script. Run: python3 -B r2_numbers.py (in this folder).

Sources: the kit's pilot records (<the kit folder>/records/score_pilot/: results.json, rows/, private/
claims_map.jsonl and the judges' verdicts through score_w1.load_verdicts/final_verdict; the plain reads' models from
records/audit/A0-pilot/audit.json), the hard-case summary (../hard_cases_20261102/summary.json and summary.md's table,
re-counted from scores.tsv by summary.py), and this test's report (results.json, copied from records/score_rand/)."""
import collections, json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent  # holds select.py (the draw), which would shadow the standard select module
sys.path = [p for p in sys.path if Path(p or '.').resolve() != HERE]
KIT = Path('<the kit folder>')
sys.path.insert(0, str(KIT / 'code/tools/w1'))
import common_w1 as W  # noqa: E402
import score_w1 as SW  # noqa: E402

N = {}

# --- pilot (10 development papers with answer keys; DEV) ---
pr = json.loads((KIT / 'records/score_pilot/results.json').read_text())
rows = [json.loads(l) for l in open(KIT / 'records/score_pilot/rows/A0-pilot.jsonl')]
audit = json.loads((KIT / 'records/audit/A0-pilot/audit.json').read_text())
model = {}
for r in audit['agents']:
    if r.get('ok'):
        model[r['label'].split('.')[0]] = [m for m in r['models'] if m != '<synthetic>'][0]
P = W.eval_paths(W.EVAL, 'pilot')
V = SW.load_verdicts(P)
cm = [json.loads(l) for l in open(KIT / 'records/score_pilot/private/claims_map.jsonl')]
wrong_by_paper = collections.Counter()
for c in cm:
    if c.get('decoy') or c['claim_id'] not in V:
        continue
    v = V[c['claim_id']]
    final = SW.final_verdict(v.get('j1'), v.get('j2'), v.get('j3'))[0]
    n = sum(1 for m in c['members'] if m['src'] == 'A0-pilot')
    if final not in ('supported', 'cannot_decide') and n:
        wrong_by_paper[c['pmid']] += n
vals = collections.Counter(str(r['pmid']) for r in rows)
opus = [p for p in vals if model.get(p) == 'claude-opus-5-5']
N['pilot'] = {
    'papers': pr['papers_in_analysis'],
    'values': pr['primary']['stored_values_mean_per_run'],  # A0 plain one read, A2 two reads and a reconcile, A6 CatLog
    'wrong': pr['primary']['errors_mean_per_run'],
    'recall_identity_aware': {k: round(v, 3) for k, v in pr['recall_identity_aware'].items() if k != 'universe'},
    'answer_key_values': pr['recall_identity_aware']['universe'],
    'plain_wrong_by_paper': dict(wrong_by_paper),
    'plain_read_model_by_paper': model,
    'opus_read_papers': len(opus), 'opus_read_values': sum(vals[p] for p in opus),
    'opus_read_wrong': sum(wrong_by_paper[p] for p in opus),
    'judge_gate': {k: pr['quality_gate'][k] for k in ('decoys', 'decoys_caught', 'first_two_agree', 'kappa', 'passed')},
}

# --- hard cases (53 papers Opus 5.5 read, each holding a documented trap) ---
# summary.md: the aggregate block and the per-kind table, both written by summary.py from scores.tsv (summary.json holds
# the per-paper rows)
md = (HERE.parent / 'hard_cases_20261102/summary.md').read_text()
N['hard_cases'] = json.loads(md.split('```')[1])
by_kind = {}
for line in md.splitlines():
    m = re.match(r'\| (.+?) \((\w+)\) \| (.+?) \| (\d+) \| (\d+) of (\d+) \| (\d+) of (\d+) \| (\d+) of (\d+) \|', line)
    if m:
        f = [int(m.group(i)) for i in range(5, 11)]
        by_kind[m.group(2)] = {'kind': m.group(1), 'visible': m.group(3), 'papers': int(m.group(4)),
                               'plain': f[0:2], 'catlog_first_read': f[2:4], 'catlog_catalogue': f[4:6]}
N['hard_cases_by_kind'] = by_kind
note = re.search(r'refused (\d+) further papers.*?\((\d+) of (\d+) fell in\)', md)
N['hard_cases_refused_note'] = {'refused': int(note.group(1)), 'sonnet_fell_in': [int(note.group(2)), int(note.group(3))]}

# --- random test (150 papers CatLog had finished) ---
d = json.loads((HERE / 'results.json').read_text())
ps, cs = d['per_source']['plain'], d['per_source']['catlog']
where = collections.Counter((r['source'], r['kind']) for r in d['wrong'])
kinds_where = collections.Counter((r['source'], r['kind'], r['verdict']) for r in d['wrong'])
by_paper = {s: collections.Counter(r['pmid'] for r in d['wrong'] if r['source'] == s) for s in ('plain', 'catlog')}
miss_papers = {s: len({r['pmid'] for r in d['misses'][s]}) for s in ('plain', 'catlog')}
t = d['triage']
frame_more = [w for line in open(HERE / 'frame_more.txt') for w in line.split()[:1] if not line.startswith('#')]
N['random'] = {
    # the frame: frame_more.txt is the frame at the replacement draw less the first 150 (select.py), so the frame of
    # finished, eligible papers then held len(frame_more) + 150
    'frame': len(frame_more) + 150,
    'papers': t['papers_analysed'], 'papers_listed': t['papers_listed'], 'refused_replaced': t['left_out_by_reason'],
    'values': t['values'], 'pairs': t['pairs'], 'identity_suspect_pairs': t['identity_suspect_pairs'],
    'agreeing_pairs': t['agreeing_pairs'], 'agreeing_pairs_sampled': t['agreeing_pairs_sampled'],
    'unmatched': t['unmatched'], 'claims': t['claims'], 'decoys': t['decoys'],
    'judges': {'decoys_caught': [d['judges']['j1']['decoys_called_an_error'], d['judges']['j2']['decoys_called_an_error']],
               'first_two_agree_disputed': round(d['judges']['first_two_agree_disputed'], 3),
               'first_two_agree_all': round(d['judges']['first_two_agree'], 3),
               'kappa_real_claims': round(d['judges']['kappa_real_claims'], 3),
               'third_judge_real_claims': d['judges']['j3']['real_claims_judged'], 'gate_passed': d['judges']['gate_passed']},
    'wrong': {'plain': ps['wrong'], 'catlog': cs['wrong']},
    'wrong_per_1000': {'plain': [ps['wrong_per_1000'], round(ps['bootstrap']['per_1000_lo'], 1), round(ps['bootstrap']['per_1000_hi'], 1)],
                       'catlog': [cs['wrong_per_1000'], round(cs['bootstrap']['per_1000_lo'], 1), round(cs['bootstrap']['per_1000_hi'], 1)]},
    'papers_with_a_wrong_value': {'plain': [ps['papers_with_a_wrong_value'], ps['papers_per_100_exact']],
                                  'catlog': [cs['papers_with_a_wrong_value'], cs['papers_per_100_exact']]},
    'difference_plain_minus_catlog_per_1000_ci': [round(d['plain_minus_catlog']['per_1000_lo'], 1), round(d['plain_minus_catlog']['per_1000_hi'], 1)],
    'difference_papers_per_100_ci': [round(d['plain_minus_catlog']['papers_per_100_lo'], 1), round(d['plain_minus_catlog']['papers_per_100_hi'], 1)],
    'share_resamples_plain_higher': d['plain_minus_catlog']['share_plain_higher'],
    'wrong_by_where': {f'{s} {k}': n for (s, k), n in sorted(where.items())},
    'wrong_by_where_and_verdict': {f'{s} {k} {v}': n for (s, k, v), n in sorted(kinds_where.items())},
    'kinds': {'plain': ps['kinds'], 'catlog': cs['kinds']},
    'sample_wrong': {'plain': ps['sample']['wrong'], 'catlog': cs['sample']['wrong'], 'of': ps['sample']['of']},
    'scaled_per_1000': {'plain': [ps['scaled_per_1000'], round(ps['bootstrap']['scaled_per_1000_lo'], 1), round(ps['bootstrap']['scaled_per_1000_hi'], 1)],
                        'catlog': [cs['scaled_per_1000'], round(cs['bootstrap']['scaled_per_1000_lo'], 1), round(cs['bootstrap']['scaled_per_1000_hi'], 1)]},
    'misses': {'catlog_missed': [cs['misses_supported_values_only_the_other_stored'], miss_papers['catlog']],
               'plain_missed': [ps['misses_supported_values_only_the_other_stored'], miss_papers['plain']]},
    'largest_paper': {s: [by_paper[s].most_common(1)[0][0], by_paper[s].most_common(1)[0][1], len(by_paper[s])] for s in by_paper},
    'papers_wrong_in_one_source_only': d['papers_wrong_in_one_source_only'],
    'cannot_decide': {'plain': ps['cannot_decide'], 'catlog': cs['cannot_decide']},
}

# --- the same values judged again with each record's full details (full_record/, run 9 Nov 2026) ---
f = json.loads((HERE / 'full_record' / 'results.json').read_text())
cmp_ = json.loads((HERE / 'full_record' / 'comparison.json').read_text())
fp, fc = f['per_source']['plain'], f['per_source']['catlog']
fby = {s: collections.Counter(r['pmid'] for r in f['wrong'] if r['source'] == s) for s in ('plain', 'catlog')}
N['full_record'] = {
    'papers': f['papers_used'], 'claims': f['triage'].get('claims'), 'decoys': f['triage'].get('decoys'),
    'judges': {'decoys_caught': [f['judges']['j1']['decoys_called_an_error'], f['judges']['j2']['decoys_called_an_error'],
                                 f['judges']['decoys']],
               'first_two_agree_disputed': round(f['judges']['first_two_agree_disputed'], 3),
               'kappa_real_claims': round(f['judges']['kappa_real_claims'], 3), 'gate_passed': f['judges']['gate_passed']},
    'values': {'plain': fp['values'], 'catlog': fc['values']},
    'wrong': {'plain': fp['wrong'], 'catlog': fc['wrong']},
    'wrong_per_1000': {'plain': [fp['wrong_per_1000']] + ([round(fp['bootstrap']['per_1000_lo'], 1), round(fp['bootstrap']['per_1000_hi'], 1)]
                                                        if fp.get('bootstrap') else []),
                       'catlog': [fc['wrong_per_1000']] + ([round(fc['bootstrap']['per_1000_lo'], 1), round(fc['bootstrap']['per_1000_hi'], 1)]
                                                         if fc.get('bootstrap') else [])},
    'papers_with_a_wrong_value': {'plain': [fp['papers_with_a_wrong_value'], fp['papers_per_100_exact']],
                                  'catlog': [fc['papers_with_a_wrong_value'], fc['papers_per_100_exact']]},
    'difference_plain_minus_catlog_per_1000_ci': [round(f['plain_minus_catlog']['per_1000_lo'], 1), round(f['plain_minus_catlog']['per_1000_hi'], 1)],
    'difference_papers_per_100_ci': [round(f['plain_minus_catlog']['papers_per_100_lo'], 1), round(f['plain_minus_catlog']['papers_per_100_hi'], 1)],
    'kinds': {'plain': fp['kinds'], 'catlog': fc['kinds']},
    'wrong_by_paper': {s: dict(fby[s].most_common()) for s in fby},
    'sample_wrong': {'plain': fp['sample']['wrong'], 'catlog': fc['sample']['wrong'], 'of': fp['sample']['of']},
    'misses': {'catlog_missed': fc['misses_supported_values_only_the_other_stored'],
               'plain_missed': fp['misses_supported_values_only_the_other_stored']},
    'cannot_decide': {'plain': fp['cannot_decide'], 'catlog': fc['cannot_decide']},
    'same_papers_first_vs_full': cmp_,
}
# the groups of Fig. 2b with full records: wrong values by kind of claim, over the claims of that kind on the papers used
# (the agreeing sample: the report's own count of sampled pairs)
fcm = [json.loads(l) for l in open(KIT / 'records/score_randfull/private/claims_map.jsonl') if l.strip()]
used = set(f['per_paper'])
den = collections.Counter((c['source_shown'], c['kind']) for c in fcm if not c['decoy'] and c['pmid'] in used)
wk = collections.Counter((r['source'], r['kind']) for r in f['wrong'])
N['full_record']['groups'] = {
    'unmatched': {s: [wk.get((s, 'unmatched'), 0), den[(s, 'unmatched')]] for s in ('plain', 'catlog')},
    'identity_suspect': {s: [wk.get((s, 'identity_suspect'), 0), den[(s, 'identity_suspect')]] for s in ('plain', 'catlog')},
    'matched_sample': {s: [fp['sample']['wrong'] if s == 'plain' else fc['sample']['wrong'], fp['sample']['of']] for s in ('plain', 'catlog')},
    'kinds_by_group': {f"{r} {k} {v}": n for (r, k, v), n in sorted(collections.Counter((x['source'], x['kind'], x['verdict']) for x in f['wrong']).items())},
}
o = json.loads((HERE / 'full_record' / 'first_on_same_papers' / 'results.json').read_text())
N['full_record']['first_on_same_papers'] = {
    s: {'wrong': o['per_source'][s]['wrong'], 'values': o['per_source'][s]['values'],
        'papers_with_a_wrong_value': o['per_source'][s]['papers_with_a_wrong_value'],
        'wrong_per_1000': [o['per_source'][s]['wrong_per_1000']] + ([round(o['per_source'][s]['bootstrap']['per_1000_lo'], 1),
                                                                    round(o['per_source'][s]['bootstrap']['per_1000_hi'], 1)]
                                                                   if o['per_source'][s].get('bootstrap') else [])}
    for s in ('plain', 'catlog')}
(HERE / 'r2_numbers.json').write_text(json.dumps(N, indent=1) + '\n')
print(json.dumps({'pilot': {k: N['pilot'][k] for k in ('values', 'wrong', 'opus_read_values', 'opus_read_wrong', 'plain_wrong_by_paper')},
                  'random': {k: N['random'][k] for k in ('wrong', 'wrong_per_1000', 'wrong_by_where', 'largest_paper', 'misses')}}, indent=1))
