#!/usr/bin/env python3
"""The hard-case result over both sets (the first 22 and the 47 drawn): per paper the plain read's final verdicts
(blind re-score), the trap's visibility, which model read it, whether its own words named the problem, and CatLog's
first reading and catalogue on the same keys (catlog_first_scores.json, catlog_scores.json, and for the papers Opus 5.5
read the same blind re-score the plain read had, rescore2/final.json, which replaces their code scores).
The result leads with the papers Opus 5.5 read (the owner, 4 Nov: "lead with opus alone"); the papers its safety filter
refused went to Sonnet 5.5, CatLog's own retry, and stay in summary.json with a one-line note in summary.md.
Writes summary.json and summary.md here."""
import json, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = Path('<the kit folder>') / 'records' / 'audit' / 'A0-hard' / 'audit.json'
FIRST_OUTSIDE = {'25799411', '12591933', '12604203', '26570983'}  # round 1: needs another publication (README)
KIND = {'PP1': 'misprinted unit or exponent in a header', 'PP2': "an earlier paper's values reprinted without credit",
        'PP3': "a row printed under another row's label", 'PP4': "a lone cell's slipped digits",
        'PP7': 'values a corrigendum or retraction withdrew', 'TL1': 'µ drawn as m in the text layer',
        'TL2': '± drawn as a digit in the text layer', 'TL4': 'stray control characters in a number',
        'RA1': 'a constant that is not kcat or Km (Hill, Adair, K0.5)', 'RA3': 'partial per-product constants',
        'RA4': 'a unit, prefix or multiplier header', 'IP11': 'the measured variant'}
JUDGMENT = ('RA3', 'RA1', 'PP2', 'PP7', 'PP3', 'PP4')  # what a number is
READING = ('RA4', 'TL1', 'TL2', 'TL4')                 # how it is printed
READ = ('done', 'incomplete', 'needs_supplement')      # CatLog has read the paper


def models_by_paper():
    """The model whose read was scored: the last valid attempt of the paper's session (Sonnet after an Opus refusal)."""
    d = json.loads(AUDIT.read_text())
    out = {}
    for ag in d['agents']:
        if ag.get('earlier'):
            continue
        real = [m for m in ag.get('models') or [] if m != '<synthetic>']
        if real:
            out.setdefault(ag['pmid'], set()).update(real)
    return {p: ('Sonnet 5.5' if any('sonnet' in m for m in ms) else 'Opus 5.5') for p, ms in out.items()}


def main():
    model = models_by_paper()
    cat = json.loads((HERE / 'catlog_scores.json').read_text())
    first = json.loads((HERE / 'catlog_first_scores.json').read_text())
    noticed1 = {r['pmid']: r for r in json.loads((HERE / 'rescore' / 'noticed.json').read_text())}  # the first set's
    f2 = HERE / 'rescore2' / 'final.json'
    blind = {(r['pmid'], r['source']): r for r in json.loads(f2.read_text())} if f2.exists() else {}
    rows, agree = [], {}
    for name, base in (('first', HERE), ('expand', HERE / 'expand')):
        final = {p['pmid']: p for p in json.loads((base / 'rescore' / 'final.json').read_text())}
        for p, r in final.items():
            key = json.loads((base / 'keys' / f'{p}.json').read_text())
            vis = key.get('visible') or ('needs_other_publication' if p in FIRST_OUTSIDE else 'in_paper')
            fin = [c['final'] for c in r['cells']]
            c = cat.get(p, {})
            f1 = first.get(p, {})
            nt = noticed1.get(p, r)
            agree[p] = (sum(1 for x in r['cells'] if x['code'] != 'review'),
                        sum(1 for x in r['cells'] if x['code'] != 'review' and x['code'] == x['agent']))
            rows.append({'pmid': p, 'set': name, 'class_id': r['class_id'], 'visible': vis, 'model': model.get(p, '?'),
                         'cells': len(fin), 'trap': fin.count('trap'), 'right': fin.count('right'),
                         'other': fin.count('other'), 'missing': fin.count('missing'),
                         'fell_in': fin.count('trap') > 0, 'noticed': nt.get('noticed'),
                         'noticed_quote': nt.get('noticed_quote', ''),
                         'catlog_status': c.get('catlog_status'), 'catlog_trap': c.get('catlog_trap'),
                         'catlog_cells': c.get('n'),
                         'catlog_first_fell_in': f1.get('fell_in') if f1.get('first_read') else None,
                         'catlog_first_trap_cells': f1.get('trap') if f1.get('first_read') else None,
                         'catlog_first_review_cells': f1.get('review') if f1.get('first_read') else None,
                         'catlog_scored_by': 'code'})
            b1, b2 = blind.get((p, 'first')), blind.get((p, 'catalogue'))
            if b1 and b2:
                fin1, fin2 = [c['final'] for c in b1['cells']], [c['final'] for c in b2['cells']]
                rows[-1].update({'catlog_first_fell_in': fin1.count('trap') > 0, 'catlog_first_trap_cells': fin1.count('trap'),
                                 'catlog_first_review_cells': fin1.count('unresolved'), 'catlog_trap': fin2.count('trap'),
                                 'catlog_cells': len(fin2), 'catlog_unresolved_cells': fin2.count('unresolved'),
                                 'catlog_scored_by': 'code and blind re-score'})
    (HERE / 'summary.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n')

    def tally(sel):
        return sum(1 for r in sel if r['fell_in']), len(sel)

    def head_of(sel):
        inp = [r for r in sel if r['visible'] == 'in_paper']
        out = [r for r in sel if r['visible'] != 'in_paper']
        fell = [r for r in sel if r['fell_in']]
        fell_in_paper = [r for r in fell if r['visible'] == 'in_paper']
        read = [r for r in sel if r['catlog_status'] in READ]
        firsts = [r for r in sel if r['catlog_first_fell_in'] is not None]
        ag = [agree[r['pmid']] for r in sel]
        return {
            'papers': len(sel), 'cells': sum(r['cells'] for r in sel), 'trap_cells': sum(r['trap'] for r in sel),
            'fell_in': tally(sel), 'in_paper': tally(inp), 'other_publication': tally(out),
            'judgment_traps': tally([r for r in sel if r['class_id'] in JUDGMENT]),
            'reading_traps': tally([r for r in sel if r['class_id'] in READING]),
            'noticed_of_fell_in': (sum(1 for r in fell if r['noticed'] == 'yes'), len(fell)),
            'noticed_of_fell_in_visible_in_paper': (sum(1 for r in fell_in_paper if r['noticed'] == 'yes'), len(fell_in_paper)),
            'catlog_read': len(read), 'plain_fell_in_on_those': tally(read),
            'catlog_first_read_fell_in': (sum(1 for r in firsts if r['catlog_first_fell_in']), len(firsts)),
            'catlog_first_read_cells_to_judge': sum(r['catlog_first_review_cells'] or 0 for r in firsts),
            'catlog_papers_with_trap': (sum(1 for r in read if r['catlog_trap']), len(read)),
            'catlog_trap_cells': (sum(r['catlog_trap'] or 0 for r in read), sum(r['catlog_cells'] or 0 for r in read)),
            'code_and_blind_rescore_agree': (sum(a for _, a in ag), sum(d for d, _ in ag))}

    lead = [r for r in rows if r['model'] == 'Opus 5.5']
    rest = [r for r in rows if r['model'] != 'Opus 5.5']
    lines = ['| Kind of trap | Visible | Papers | Plain Opus fell in | CatLog\'s first read | CatLog\'s catalogue now |',
             '|---|---|---|---|---|---|']
    by = collections.defaultdict(list)
    for r in lead:
        by[r['class_id']].append(r)
    order = ['RA3', 'RA1', 'PP2', 'PP7', 'PP3', 'PP4', 'PP1', 'RA4', 'IP11', 'TL1', 'TL2', 'TL4']
    for k in order:
        sel = by.get(k, [])
        if not sel:
            continue
        f, n = tally(sel)
        read = [r for r in sel if r['catlog_status'] in READ]
        cf = sum(1 for r in read if r['catlog_trap'])
        firsts = [r for r in sel if r['catlog_first_fell_in'] is not None]
        ff = sum(1 for r in firsts if r['catlog_first_fell_in'])
        vis = 'another publication' if all(r['visible'] == 'needs_other_publication' for r in sel) else \
            ('in the paper' if all(r['visible'] == 'in_paper' for r in sel) else 'mixed')
        lines.append(f'| {KIND[k]} ({k}) | {vis} | {n} | {f} of {n} | {ff} of {len(firsts)} | {cf} of {len(read)} |')
    head, note, every = head_of(lead), head_of(rest), head_of(rows)
    md = [f'# Hard cases: the result on the {len(lead)} papers Opus 5.5 read', '', '```', json.dumps(head, indent=1), '```', ''] + lines
    md += ['', f"Note: Opus 5.5's safety filter refused {len(rest)} further papers; Sonnet 5.5, CatLog's own retry, read them "
               f"({note['fell_in'][0]} of {note['fell_in'][1]} fell in). They are not in these numbers. All {len(rows)}: "
               f"{every['fell_in'][0]} fell in."]
    (HERE / 'summary.md').write_text('\n'.join(md) + '\n')
    print(json.dumps({'opus': head, 'sonnet_note': note, 'all': every}, indent=1))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
