#!/usr/bin/env python3
"""Task (c) of the accuracy check, 14 November 2026.

Builds, from the two tests' wrong lists and the eval tree's verdict files:
  supp_wrong_values.tsv        the supplementary table: one line per value judged wrong (97)
  check_sheet.csv              a blinded sheet for one person: the same 97 values, as reading A or B
  check_sheet_optional.csv     20 disputed values the judges called supported (10 per source), same blinding
  check_key.tsv                case -> source for both sheets (never given to the checker)

Reads only (no paper text, no PDF). Run: python3 build_task_c.py
"""
import csv
import glob
import hashlib
import json
import random
import re

EV = '<the CatLog folder>/paper/evidence/'
KR = '<the kit folder>/'
OUT = EV + 'accuracy_check_20261114/'
PAPERS_TSV = '<the CatLog folder>/papers.tsv'
SEED_AB = 20261114        # A/B per paper on the main sheet (the task)
SEED_OPTIONAL = 20261115  # the optional draw, then A/B for its papers (the task)

# ---------- the eval tree's folder codes (the kit's common_w1.code) ----------
ALPHA = 'bcdfghjkmnpqrstvxz23456789'


def code(label):
    h = int(hashlib.sha256(f'kinetics-reading/{label}'.encode()).hexdigest(), 16)
    out = ''
    for _ in range(6):
        h, r = divmod(h, len(ALPHA))
        out += ALPHA[r]
    return out


TESTS = {
    'random': {'results': EV + 'random_papers_20261104/full_record/results.json',
               'cmap': KR + 'records/score_randfull/private/claims_map.jsonl', 'run': 'randfull'},
    'locked': {'results': EV + 'locked_test_20261109/result/results.json',
               'cmap': KR + 'records/score_locked/private/claims_map.jsonl', 'run': 'locked'},
}
for _t in TESTS.values():
    for _k in ('claims', 'claims3', 'verdicts-j1', 'verdicts-j2', 'verdicts-j3'):
        _t[_k] = KR + 'out/' + code(f"{_k}-{_t['run']}") + '/'


def pmid_key(p):  # the kit's order: PMIDs as numbers, then stand-in ids
    return (0, int(p), '') if str(p).isdigit() else (1, 0, str(p))


def klass(v):
    return None if v is None else 'supported' if v == 'supported' else 'cannot_decide' if v == 'cannot_decide' else 'error'


def final_verdict(v1, v2, v3=None):  # the kit's score_w1.final_verdict (no misprint verdicts in these judgings)
    if v1 is None or v2 is None:
        return None
    if klass(v1) == klass(v2):
        return v1 if v1 == v2 or klass(v1) != 'error' else 'mixed'
    if v3 is None:
        return None
    ks = [klass(v1), klass(v2), klass(v3)]
    win = [k for k in set(ks) if ks.count(k) >= 2]
    if not win:
        return 'cannot_decide'
    if win[0] != 'error':
        return win[0]
    errs = [v for v in (v1, v2, v3) if klass(v) == 'error']
    kinds = [k for k in set(errs) if errs.count(k) >= 2]
    return kinds[0] if kinds else v3 if klass(v3) == 'error' else errs[0]


def load_test(test):
    T = TESTS[test]
    res = json.load(open(T['results']))
    cmap = {}
    for line in open(T['cmap']):
        if line.strip():
            r = json.loads(line)
            cmap[r['claim_id']] = r
    verdicts = {}
    for j in ('j1', 'j2', 'j3'):
        for f in sorted(glob.glob(T[f'verdicts-{j}'] + '*.json')):
            for v in json.load(open(f)).get('verdicts') or []:
                if isinstance(v, dict) and v.get('verdict'):
                    verdicts.setdefault(str(v['id']), {}).setdefault(j, v)
    return res, cmap, verdicts


def clean(s):
    return re.sub(r'\s+', ' ', '' if s is None else str(s)).strip()


def fmt(v):
    if v is None or v == '':
        return ''
    if isinstance(v, str):
        return v
    s = '%.6g' % v
    if 'e' in s:
        s = ('%.12f' % v).rstrip('0').rstrip('.')
    return s


def num(x):  # 4 significant figures, never e-notation
    return f'{x:.0f}' if abs(x) >= 1e4 else '%.4g' % x


SRC = {'plain': 'plain', 'catlog': 'CatLog'}

# ---------- what the page checks print (investigation/<pmid>.check1.json and .check2.json agree) ----------
# 9973343, Table 3 (p. 1174): (Km mM, kcat s^-1, kcat/Km uM^-1 s^-1) per block and substrate
T3 = {
    'purified': {'formaldehyde': (25, 7.1e4, 3.00), 'acetaldehyde': (60, 4.4e4, 0.73), 'propionaldehyde': (62, 1.1e4, 0.17),
                 'phenylpropionaldehyde': (15, 2.5e4, 1.70), 'indole-3-acetaldehyde': (25, 2.3e3, 0.09),
                 'succinic semialdehyde': (8, 5.7e3, 0.71), 'glutaric dialdehyde': (0.8, 4.2e4, 60.0)},
    'sulfide-activated': {'formaldehyde': (15, 1.3e5, 8.46), 'acetaldehyde': (8, 2.8e4, 3.50),
                          'propionaldehyde': (25, 2.3e4, 0.92), 'phenylpropionaldehyde': (10, 2.2e4, 2.22),
                          'indole-3-acetaldehyde': (12, 1.1e3, 0.10), 'succinic semialdehyde': (6, 1.1e4, 1.90),
                          'glutaric dialdehyde': (1, 5.7e4, 57.0)},
}
# 9973343, Table 2 (p. 1174): specific activity (U/mg) at 50 mM substrate, per block (check1 lists the first three
# substrates, check2 all four)
T2 = {'purified': {'formaldehyde': '35.50', 'acetaldehyde': '8.03', 'propionaldehyde': '5.16',
                   'phenylpropionaldehyde': '19.81'},
      'sulfide-activated': {'formaldehyde': '85.00', 'acetaldehyde': '23.22', 'propionaldehyde': '14.40',
                            'phenylpropionaldehyde': '30.81'}}  # as printed
MR_9973343 = 68724  # subunit Mr (p. 1173)
# 10447675, Table 2 (p. 80): substrate -> (Km uM, kcat as printed under 's^-1')
T2_10447675 = {'mt-Trx': (2.8, 1200), 'Human Trx': (6.0, 1030), 'E. coli Trx': (70, 1300), 'selenocystine': (620, 1600),
               'Nbs2': (3900, 2300)}

ARITH_9973343 = (
    "Paper's own numbers (page checks): Vmax for formaldehyde with purified FOR 62 U/mg (Results p. 1173); "
    "1 U = 1 umol substrate/min/mg (Methods p. 1172); subunit Mr 68,724 (p. 1173). 62 x 68,724 / 60,000 = 71.0 s^-1 per "
    "subunit, which is 10^-3 of the printed 7.1 x 10^4 s^-1 (the printed number is 62 x 68,724 / 60 with the mg-to-g "
    "factor left out). Table 2's specific activities at 50 mM, taken to Vmax with Table 3's Km, give 13-127 s^-1 per "
    "subunit for the 8 rows Table 2 covers: 520-2,200x below the printed kcat and 0.5-2x the printed kcat x 10^-3. "
    "As printed, Table 3 closes (printed kcat / Km / 1000 = printed kcat/Km within 0.88-1.04 in all 14 rows), so the "
    "kcat/Km column carries the kcat column's factor.")
ARITH_10447675 = (
    "Paper's own numbers (page checks): Method 1 (p. 75) defines 1 U as forming 2 umol TNB (1 umol Nbs2) per min, at 2 mM "
    "Nbs2; the homogeneous enzyme has 13.9 U/mg (Table 1, p. 80; about 15 U/mg in the Results, p. 77) and one 56-kDa band "
    "(p. 77). With Table 2's own Km(Nbs2) of 3900 uM: Vmax = 13.9 x (2 + 3.9)/2 = 41.0 U/mg; x 56 kDa = 2296 min^-1 per "
    "subunit, Table 2's Nbs2 cell 2300 read as min^-1 (38.3 s^-1). Read as s^-1, 2300 needs about 835 U/mg at 2 mM Nbs2, "
    "60x the measured 13.9 U/mg. One header covers all five rows; the Results (p. 79) give 'kcat was 1000-1300 and 2300 "
    "with Trx and Nbs2' with no unit; no Trx-assay activity is printed to check the Trx and selenocystine rows alone.")

LATER = {
    '9973343': ("Post hoc blind page check, 2 agents (investigation/9973343.check1.json, .check2.json): the printed cells "
                "are the plain reading's values; CatLog rescaled on purpose and the paper's own numbers support it ('B's "
                "values are probably the true constants')."),
    '10447675': ("Post hoc blind page check, 2 agents (investigation/10447675.check1.json, .check2.json): both said CatLog's "
                 "values match the paper, the s^-1 header being a misprint for min^-1."),
    '10491091': ("Post hoc blind page check, 1 agent (investigation/10491091.check1.json): confirmed; Table 3 prints "
                 "'[S]0.5 = 5, h = 1.6' (WT) and '[S]0.5 = 1, h = 1.2' (D56E) under a caption that shows Hill parameters "
                 "where the behaviour was non-Michaelis-Menten."),
    '10801893': ("Post hoc blind page check, 1 agent (investigation/10801893.check1.json): confirmed; the paper's own "
                 "measurements, none a Michaelis constant (K_app from sigmoidal fits: n_app 2.7, 1.8 with arsenite, 2.8 "
                 "for Grx2). XML text only, no page images."),
    '11488932': ("Post hoc blind page check, 1 agent (investigation/11488932.check1.json): confirmed; Table 3's caption "
                 "credits the Ppnk constants to data described previously in ref. 7 (same group); the paper assays only "
                 "the E. coli enzyme."),
    '15238222': ("Post hoc blind page check, 1 agent (investigation/15238222.check1.json): confirmed; K' from a Hill fit, in "
                 "a column headed Km whose footnote redefines it as K'. XML text only, no page images."),
    '7334001': ("No page check since the judging (no work/scale_7334001*, no later log.tsv line). The full-record README "
                "notes that the scan's text layer reads the exponent as 6 twice (Results '5-8 x 10~6 M'; Discussion "
                "'Km (6.2 x 10^-6)') and lists the page image for catlog-scale's three refuters."),
}


def block_9973343(r):
    d = r['shown']['details']
    if 'sulfide-activated (incubated' in d or 'then sulfide-activated' in d:
        return 'sulfide-activated'
    if 'not sulfide-activated' in d:
        return 'purified'
    raise SystemExit(f"no FOR block in {r['claim_id']}")


def raw_number(raw, exponent=True):
    """'7.1 × 10^4' -> 71000.0; '0.71' -> 0.71; with exponent=False, '5.0 ×10^-6 M' -> 5.0 (the number alone)."""
    m = re.match(r'\s*([0-9.]+)\s*(?:[x×]\s*10\^?([−-]?\d+))?', raw)
    x = float(m.group(1))
    if m.group(2) and exponent:
        x *= 10 ** int(m.group(2).replace('−', '-'))
    return x


# ---------- per-paper words: short location, the paper's label as the reading's details quote it ----------

def supp_location(r):
    p, w, d = r['pmid'], r['stored']['where'] or '', r['shown']['details']
    if p == '16573681':
        return 'Table 2; Results'
    if p == '21958066':
        return 'Table 5; Results' if 'Results' in w else 'Table 5'
    if p == '24731825':
        return 'Table 2; Table 3' if 'Table 3' in w else 'Table 2'
    if p == '40195502':
        return 'Table 1' if w.startswith('Table 1') else 'Text after Table 1'
    if p == '41495879':
        return 'Table 2'
    if p == '7334001':
        return 'Table IV'
    if p == '10491091':
        return 'Table 3; Fig. 3'
    if p == '10801893':
        return 'Table II' if w.startswith('Table II') else 'Results (Fig. 4; Fig. 5)' if 'Fig. 4' in w else 'Results (Fig. 5)'
    if p == '11488932':
        return 'Table 3'
    if p == '15238222':
        return 'Table 1; Abstract'
    if p == '10447675':
        return 'Table 2'
    if p == '9973343':
        return f'Table 3 ({block_9973343(r)} FOR)' if w.startswith('Table 3') else 'Results, p. 1174'
    raise SystemExit(f'no location rule for {p}')


def sheet_location(r):
    """Table, figure or page only: nothing of the reading's own labels or notes."""
    p, w = r['pmid'], r['stored']['where'] or ''
    if p in ('16573681', '41495879', '10447675'):
        return 'Table 2'
    if p == '21958066':
        return 'Table 5'
    if p == '24731825':
        return 'Table 2; Table 3' if 'Table 3' in w else 'Table 2'
    if p == '40195502':
        return 'Table 1' if w.startswith('Table 1') else 'Text after Table 1'
    if p == '7334001':
        return 'Table IV'
    if p in ('10491091', '11488932'):
        return 'Table 3'
    if p == '10801893':
        return 'Table II' if w.startswith('Table II') else 'Results text (Fig. 4; Fig. 5)' if 'Fig. 4' in w else 'Results text (Fig. 5)'
    if p == '15238222':
        return 'Table 1'
    if p == '9973343':
        return 'Table 3' if w.startswith('Table 3') else 'Results, p. 1174'
    raise SystemExit(f'no sheet location rule for {p}')


def paper_label(r):
    p, d, st, m = r['pmid'], r['shown']['details'], r['stored'], r['shown']['metric']
    w = st['where'] or ''
    if p == '16573681':
        return "Table 2 row 'Km/S0.5 (ATP)' (70°C); the text gives it as S0.5 = 8 mM"
    if p == '21958066':
        cond = '(+) acetyl-CoA' if '(+)' in w else '(−) acetyl-CoA'
        return f"Table 5, Pi release, {cond}: printed as " + ('Ka pyruvate' if m == 'Km' else 'kcat/Ka')
    if p == '24731825':
        s = "Table 2 wild-type (wAHAS) row, footnote a: 'Taken from [17]'"
        return s + ("; the same value is repeated in Table 3's 'Wild' row" if 'Table 3' in w else '')
    if p == '40195502':
        mm = re.match(r"Table 1, row '(.+)', column '(.+)'", w)
        if mm:
            return f"Table 1 row '{mm.group(1)}', column '{mm.group(2)}'"
        return ("text after Table 1: '≈44 s^-1' (the reading's details: Davidi et al (2020) value corrected only for the "
                "missing factor of 2; the authors replaced it with Table 1)")
    if p == '41495879':
        n = re.search(r'n_H = ([0-9.]+ ± [0-9.]+)', d)
        return f"Table 2 column 'K0.5,IMP' (Hill fit, n_H = {n.group(1)})"
    if p == '10491091':
        h = re.search(r'Hill coefficient h = ([0-9.]+)', d).group(1)
        return f"listed under 'Km (mM)' in Table 3 as {st['raw']} (Hill coefficient h = {h})"
    if p == '10801893':
        cid = r['claim_id']
        return {'1b18c974': 'K_app from a sigmoidal fit, apparent Hill coefficient n_app = 2.7 (Fig. 4); restated as the '
                            'no-arsenite control of Fig. 5 (n_app = 2.6)',
                'b7c034ef': 'K_app with 1 mM sodium arsenite; apparent Hill coefficient down from 2.6 to 1.8 (Fig. 5)',
                'ff7efe53': 'K_app with 2.5 mM sodium arsenite; apparent Hill coefficient down from 2.6 to 1.8 (Fig. 5)',
                'e19b05a8': 'Table II footnote b: Km is K_app for Grx2 (sigmoidal, n_app = 2.8, Fig. 7B)',
                'cb6fef36': 'Table II footnote b: kcat/Km is kcat/K_app for Grx2 (n_app = 2.8, Fig. 7B)'}[cid]
    if p == '11488932':
        return ("Table 3 row Ppnk (M. tuberculosis); the reading's details: constants determined from Ppnk data "
                "published previously by the same group (ref. 7, Kawai et al. 2000)")
    if p == '15238222':
        return "Table 1 Km column (footnote: Km is a K' value)"
    if p == '9973343' and r['shown']['substrate'] == 'acetaldehyde':
        return 'Table 3 footnote c: measured at 65°C'
    return ''


def header_and_arith(r):
    """(printed header, value as printed in catalog units, arithmetic) for CatLog's 40 values; '' for the rest."""
    p, st, sh = r['pmid'], r['stored'], r['shown']
    if p == '9973343':
        sub = sh['substrate']
        if not st['where'].startswith('Table 3'):
            cell = raw_number(st['raw'])
            assert cell == 3.0e4 and abs(sh['value'] - cell / 1000) < 1e-6, r['claim_id']
            return ("Results p. 1174: 'kcat = 3.0 x 10^4 s^-1' (Km 30 mM)", '30000 s^-1',
                    f"stored = printed 3.0 x 10^4 s^-1 x 10^-3 = {fmt(sh['value'])} s^-1. " + ARITH_9973343)
        blk = block_9973343(r)
        km, kc, kk = T3[blk][sub]
        hdr = "Table 3, both blocks: 'Apparent Km (mM) | kcat (s^-1) | kcat/Km (µM^-1 s^-1)'"
        cell = raw_number(st['raw'])
        if sh['metric'] == 'kcat':
            assert abs(cell - kc) < 1e-6 * kc and abs(sh['value'] - kc / 1000) < 1e-6, r['claim_id']
            row = f"stored = printed {st['raw']} s^-1 x 10^-3 = {fmt(sh['value'])} s^-1."
            sa = T2[blk].get(sub)
            if sa is not None:
                vmax = float(sa) * (50 + km) / 50
                kc2 = vmax * MR_9973343 / 60000
                row += (f" Table 2 ({blk}): {sa} U/mg at 50 mM; with Table 3's Km {fmt(km)} mM, Vmax = {sa} x "
                        f"(50 + {fmt(km)})/50 = {vmax:.1f} U/mg; x 68,724/60,000 = {kc2:.0f} s^-1 per subunit.")
            if blk == 'purified' and sub == 'formaldehyde':
                row += ' The Results give this row directly: Vmax 62 U/mg (Km 25 mM) = 71.0 s^-1 per subunit.'
            return hdr, f'{fmt(kc)} s^-1', row + ' ' + ARITH_9973343
        assert abs(cell - kk) < 1e-9 and abs(sh['value'] - kk) < 1e-9, r['claim_id']
        row = (f"stored = printed {st['raw']} µM^-1 s^-1 taken as mM^-1 s^-1, i.e. the as-printed {fmt(kk * 1000)} "
               f"mM^-1 s^-1 x 10^-3 (printed kcat {fmt(kc)} s^-1 / Km {fmt(km)} mM = {num(kc / km)} mM^-1 s^-1).")
        return hdr, f'{fmt(kk * 1000)} mM^-1 s^-1', row + ' ' + ARITH_9973343
    if p == '10447675':
        key = {'Human Trx': 'Human Trx', 'Nbs2': 'Nbs2', 'selenocystine': 'selenocystine', 'mt-Trx': 'mt-Trx',
               'E. coli Trx': 'E. coli Trx'}[sh['substrate']]
        km, kc = T2_10447675[key]
        cell = raw_number(st['raw'])
        assert cell == kc and abs(sh['value'] - round(kc / 60, 2)) < 1e-9, r['claim_id']
        row = f"stored = printed {kc} / 60 = {fmt(sh['value'])} s^-1 (read as min^-1)."
        if key == 'Nbs2':
            row += " This is the row the paper's own numbers check directly."
        return "Table 2: 'Km (µM) | kcat (s^-1)'", f'{kc} s^-1', row + ' ' + ARITH_10447675
    if p == '7334001':
        cell = raw_number(st['raw'], exponent=False)
        return ("Table IV 'Apparent Km (x10^-5 M)' as j1 and j3 read the page image; x10^-6 M as j2 read it and as CatLog "
                "stored it",
                f"{fmt(cell * 0.01)} mM if the header is x10^-5 M; {fmt(cell * 0.001)} mM if x10^-6 M", '')
    return '', '', ''


STAGE2 = EV + 'locked_test_20261109/stage2/checked/'


def stage2_catlog(pmid):
    """Stage 2's page check (one Claude Fable 5.2 agent per paper; post hoc) on CatLog's values of a paper:
    (metric, substrate, value) -> verdict, or 'not checked' for values the three readings agreed on."""
    key = json.load(open(STAGE2 + 'verdicts/_key.json'))[pmid]['order']
    letter = [k for k, v in key.items() if v == 'catlog'][0]
    verdicts = {x['id']: x for x in json.load(open(STAGE2 + f'verdicts/{pmid}.check1.json'))['verdicts']}
    out = []
    for x in json.load(open(STAGE2 + f'tasks/{pmid}.task.json'))[f'reading_{letter}']:
        v = verdicts.get(x['id'])
        out.append((x['metric'], x['substrate'], x['value_in_catalog_units'], v['verdict'] if v else 'not checked'))
    return out


def stage2_note(r, table):
    sh = r['shown']
    hits = [v for m, sub, val, v in table if m == sh['metric'] and sub == sh['substrate']
            and abs(val - sh['value']) <= 0.005 * max(abs(val), abs(sh['value']))]
    assert len(hits) == 1, (r['claim_id'], hits)
    if hits[0] == 'not checked':
        return (" Stage 2's page check (post hoc, one Claude Fable 5.2 agent, stage2/checked/): not checked there, since "
                "the curation, CatLog and the tool held the same number.")
    return f" Stage 2's page check (post hoc, one Claude Fable 5.2 agent, stage2/checked/): {hits[0]}."


def votes_and_reasons(js, final):
    order = [j for j in ('j1', 'j2', 'j3') if j in js]
    votes = '; '.join(f"{j} {js[j]['verdict']}" for j in order)
    maj = [j for j in order if js[j]['verdict'] == final]
    oth = [j for j in order if js[j]['verdict'] != final]
    reason = ' | '.join(f"{j}: {clean(js[j]['reason'])}" for j in maj)
    dissent = ' | '.join(f"{j} ({js[j]['verdict']}): {clean(js[j]['reason'])}" for j in oth)
    return votes, reason, dissent, clean(js[maj[0]]['found_at']) if maj else ''


def first_judging(c):
    if not c.get('first_final'):
        return ''
    fv = c.get('first_votes') or {}
    return f"{c['first_final']} ({c['first_decision']}: " + ', '.join(f'{j} {fv[j]}' for j in sorted(fv)) + ')'


METRIC_ORDER = {'kcat': 0, 'Km': 1, 'kcat/Km': 2}


def within_key(sh):
    return (sh['enzyme'] or '', sh['organism'] or '', sh['variant'] or '', sh['substrate'] or '',
            METRIC_ORDER.get(sh['metric'], 9), sh['value'] if isinstance(sh['value'], (int, float)) else 0)


def main():
    dois = {}
    with open(PAPERS_TSV, newline='') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            dois[row['pmid']] = (row.get('doi') or '').strip()

    # ---------- the 97 values judged wrong ----------
    wrong, data = [], {}
    for test in ('random', 'locked'):
        res, cmap, V = load_test(test)
        data[test] = (res, cmap, V)
        for e in res['wrong']:
            c = cmap[e['claim_id']]
            js = V[e['claim_id']]
            # the wrong list and the verdict files must say the same
            for j, v in e['judges'].items():
                assert js[j]['verdict'] == v['verdict'] and js[j]['reason'] == v['reason'], (e['claim_id'], j)
            assert set(js) == set(e['judges']), e['claim_id']
            assert final_verdict(*(js.get(j, {}).get('verdict') for j in ('j1', 'j2', 'j3'))) == e['verdict']
            assert c['source_shown'] == e['source'] and not c['decoy']
            wrong.append({'test': test, 'pmid': e['pmid'], 'source': e['source'], 'claim_id': e['claim_id'],
                          'kind': e['kind'], 'verdict': e['verdict'], 'shown': e['shown'], 'stored': e['stored'],
                          'judges': js, 'cmap': c})
    assert len(wrong) == 97, len(wrong)

    # ---------- supplementary table ----------
    cols = ['test', 'pmid', 'source', 'claim_id', 'metric', 'value', 'unit', 'printed_cell', 'enzyme', 'organism',
            'variant', 'substrate', 'cosubstrate', 'pH', 'temperature_C', 'location', 'paper_label', 'final_verdict',
            'votes', 'judges_reason', 'dissent', 'found_at_j1', 'claim_kind', 'first_judging', 'printed_header',
            'value_as_printed', 'arithmetic', 'later_check', 'details']
    s2 = {p: stage2_catlog(p) for p in ('9973343', '10447675')}
    lines = []
    for r in wrong:
        sh, st = r['shown'], r['stored']
        votes, reason, dissent, found = votes_and_reasons(r['judges'], r['verdict'])
        hdr, as_printed, arith = header_and_arith(r)
        if r['kind'] == 'matched_sample':
            pid = r['cmap']['partner'][1]
            twin = [x for x in data[r['test']][1].values() if any(m['id'] == pid for m in x['members'])][0]
            tv = data[r['test']][2][twin['claim_id']]
            kind = (f"agreeing pair (sampled): paired by number with CatLog's {fmt(twin['shown']['value'])} "
                    f"{twin['shown']['unit']}, found by its first judge at {clean(tv['j1']['found_at'])}; judged "
                    + ', '.join(f"{j} {tv[j]['verdict']}" for j in sorted(tv)))
        else:
            kind = 'disputed: only this source stored it'
        lines.append({
            'test': r['test'], 'pmid': r['pmid'], 'source': SRC[r['source']], 'claim_id': r['claim_id'],
            'metric': sh['metric'], 'value': fmt(sh['value']), 'unit': sh['unit'],
            'printed_cell': clean(f"{st['raw']} {st['raw_unit'] or ''}"),
            'enzyme': clean(sh['enzyme']), 'organism': clean(sh['organism']), 'variant': clean(sh['variant']),
            'substrate': clean(sh['substrate']), 'cosubstrate': clean(sh['cosubstrate']), 'pH': fmt(sh['pH']),
            'temperature_C': fmt(sh['temperature_C']), 'location': supp_location(r), 'paper_label': paper_label(r),
            'final_verdict': r['verdict'], 'votes': votes, 'judges_reason': reason, 'dissent': dissent,
            'found_at_j1': found, 'claim_kind': kind, 'first_judging': first_judging(r['cmap']),
            'printed_header': hdr, 'value_as_printed': as_printed, 'arithmetic': arith,
            'later_check': (LATER.get(r['pmid'], '') if (r['test'] == 'locked' or r['pmid'] == '7334001') else '')
            + (stage2_note(r, s2[r['pmid']]) if r['pmid'] in s2 else ''),
            'details': clean(sh['details'])})
        r['line'] = lines[-1]
    order = {'random': 0, 'locked': 1}
    lines.sort(key=lambda x: (order[x['test']], pmid_key(x['pmid']), x['location'],
                              METRIC_ORDER.get(x['metric'], 9), x['organism'], x['variant'], x['substrate'],
                              float(x['value'])))
    with open(OUT + 'supp_wrong_values.tsv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter='\t', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        w.writeheader()
        for x in lines:
            w.writerow(x)

    # ---------- blinded sheets ----------
    sheet_cols = ['case', 'pmid', 'PubMed link', 'DOI', 'location', 'metric', 'value', 'unit', 'enzyme', 'organism',
                  'variant', 'substrate', 'pH', 'temperature (°C)', 'reading', 'verdict (yes / no / cannot tell)',
                  'if no, why (earlier work / other constant / other scale / not in paper / other)', 'note']
    QUESTION = ("QUESTION: the printed unit of this column and the paper's other numbers (Vmax, specific activity, "
                "molecular mass) may disagree: say which you trust and why")

    def link(p):
        return f'https://pubmed.ncbi.nlm.nih.gov/{p}/' if str(p).isdigit() else ''

    def safe(s):  # nothing Excel would read as a formula
        s = '' if s is None else str(s)
        return (' ' + s) if s[:1] in ('=', '+', '-', '@') else s

    def value_row(case, pmid, loc, sh, letter):
        return [case, pmid, link(pmid), dois.get(pmid, ''), loc, sh['metric'], fmt(sh['value']), sh['unit'],
                safe(clean(sh['enzyme'])), safe(clean(sh['organism'])), safe(clean(sh['variant'])),
                safe(clean(sh['substrate'])), fmt(sh['pH']), fmt(sh['temperature_C']), letter, '', '', '']

    def question_row(case, pmid, loc):
        return [case, pmid, link(pmid), dois.get(pmid, ''), loc, 'question'] + [''] * 11 + [QUESTION]

    # A and B per paper, at random, papers in pmid order
    main_papers = sorted({r['pmid'] for r in wrong}, key=pmid_key)
    rng = random.Random(SEED_AB)
    ab = {}
    for p in main_papers:
        pair = ['plain', 'catlog']
        rng.shuffle(pair)
        ab[p] = {pair[0]: 'A', pair[1]: 'B'}
    question_papers = {'9973343': 'Table 3; Results, p. 1174', '10447675': 'Table 2'}  # the 34 unit changes

    key_rows = []
    srows = []
    for r in wrong:
        r['sheet_loc'] = sheet_location(r)
    wrong.sort(key=lambda r: (pmid_key(r['pmid']), r['sheet_loc'], within_key(r['shown'])))
    n, q = 0, 0
    for p in main_papers:
        if p in question_papers:
            q += 1
            srows.append(question_row(f'Q{q}', p, question_papers[p]))
            key_rows.append(['main', f'Q{q}', p, '', 'question (no value)', '', '', '', '', ''])
        for r in [x for x in wrong if x['pmid'] == p]:
            n += 1
            case = f'C{n:02d}'
            letter = ab[p][r['source']]
            srows.append(value_row(case, p, r['sheet_loc'], r['shown'], letter))
            key_rows.append(['main', case, p, letter, SRC[r['source']], r['test'], r['claim_id'], r['verdict'],
                             r['line']['claim_kind'].split(':')[0], ''])
    with open(OUT + 'check_sheet.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(sheet_cols)
        w.writerows(srows)

    # ---------- optional sheet: 10 disputed values per source the judges called supported ----------
    pool = {'plain': [], 'catlog': []}
    for ti, test in enumerate(('random', 'locked')):
        res, cmap, V = data[test]
        used = set(res['per_paper'])
        for cid, c in cmap.items():
            if c['decoy'] or c['pmid'] not in used or c['kind'] not in ('unmatched', 'identity_suspect'):
                continue
            v = V.get(cid, {})
            if final_verdict(*(v.get(j, {}).get('verdict') for j in ('j1', 'j2', 'j3'))) != 'supported':
                continue
            pool[c['source_shown']].append(((ti,) + pmid_key(c['pmid']) + (cid,), test, c))
    for s in pool:
        pool[s].sort(key=lambda x: x[0])
    rng2 = random.Random(SEED_OPTIONAL)
    drawn = [(s, x) for s in ('plain', 'catlog') for x in rng2.sample(pool[s], 10)]
    opt_papers = sorted({x[2]['pmid'] for _, x in drawn}, key=pmid_key)
    for p in opt_papers:
        if p not in ab:
            pair = ['plain', 'catlog']
            rng2.shuffle(pair)
            ab[p] = {pair[0]: 'A', pair[1]: 'B'}

    def opt_location(c):
        first = clean(c['shown']['details']).split(';')[0]
        m = re.match(r'(Table [0-9IVX]+)', first)
        if m:
            return m.group(1)
        m = re.match(r'Figure (\d+) legend', first)
        if m:
            return f'Fig. {m.group(1)} legend'
        raise SystemExit(f"no location for optional claim {c['claim_id']}: {first}")

    # a unit change on the paper's own numbers gets the same neutral question as the 34 (whichever reading made it)
    opt_questions = {}
    for s, (k, test, c) in drawn:
        if re.search(r'misprint|Printed unit .* but the value equals', c['shown']['details']):
            opt_questions[c['pmid']] = opt_location(c)
    orows = []
    items = sorted(drawn, key=lambda sx: (pmid_key(sx[1][2]['pmid']), opt_location(sx[1][2]), within_key(sx[1][2]['shown'])))
    n = 0
    seen_q = set()
    pool_sizes = {s: len(pool[s]) for s in pool}
    for s, (k, test, c) in items:
        p = c['pmid']
        if p in opt_questions and p not in seen_q:
            seen_q.add(p)
            q += 1
            orows.append(question_row(f'Q{q}', p, opt_questions[p]))
            key_rows.append(['optional', f'Q{q}', p, '', 'question (no value)', test, '', '', '', ''])
        n += 1
        case = f'S{n:02d}'
        letter = ab[p][s]
        orows.append(value_row(case, p, opt_location(c), c['shown'], letter))
        key_rows.append(['optional', case, p, letter, SRC[s], test, c['claim_id'], 'supported',
                         'disputed (' + c['kind'] + ')', ''])
    with open(OUT + 'check_sheet_optional.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(sheet_cols)
        w.writerows(orows)

    # ---------- the key (never given to the checker) ----------
    with open(OUT + 'check_key.tsv', 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['sheet', 'case', 'pmid', 'reading', 'source', 'test', 'claim_id', 'judges_final_verdict',
                    'claim_kind', 'how_drawn'])
        for row in key_rows:
            if row[0] == 'main' and row[3]:
                row[9] = f'wrong list of the {row[5]} test; A/B: random.Random({SEED_AB}), papers in pmid order'
            elif row[0] == 'optional' and row[3]:
                row[9] = (f'random.Random({SEED_OPTIONAL}).sample of {pool_sizes[KEYSRC[row[4]]]} disputed '
                          f'{row[4]} values judged supported; A/B: same generator after the draw')
            w.writerow(row)
    print('supp lines', len(lines), '| main sheet values', sum(1 for r in srows if r[0].startswith('C')),
          'questions', sum(1 for r in srows if r[0].startswith('Q')),
          '| optional values', sum(1 for r in orows if r[0].startswith('S')),
          'questions', sum(1 for r in orows if r[0].startswith('Q')),
          '| pool', pool_sizes, '| optional papers', len(opt_papers))
    print('A/B main:', {p: ab[p] for p in main_papers})
    print('A/B optional:', {p: ab[p] for p in opt_papers})


KEYSRC = {'plain': 'plain', 'CatLog': 'catlog'}

if __name__ == '__main__':
    main()
