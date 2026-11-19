#!/usr/bin/env python3
"""Every number the paper prints about EnzyExtract, as registered and as corrected, with its source
(CORRECTIONS.md, corrections.json). Reads only the scorers' outputs; run them first:

  python3 -I -B writing/research/enzyextract_broad_20261118/score_corrected.py
  python3 -I -B paper/evidence/locked_test_20261109/stage2/score_corrected.py
  python3 -I -B paper/evidence/stage2_scoring_rules_20261117/rescore_corrected.py
  python3 -I -B writing/research/enzyextract_broad_20261118/corrections.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
S2 = REPO / 'paper/evidence/locked_test_20261109/stage2'
SR = REPO / 'paper/evidence/stage2_scoring_rules_20261117'
BR = json.loads((HERE / 'corrected/results.json').read_text())
T = json.loads((S2 / 'corrected/table.json').read_text())
PCr = json.loads((S2 / 'checked/results.json').read_text())
PCc = json.loads((S2 / 'corrected/checked/results.json').read_text())
VR = json.loads((SR / 'views.json').read_text())
VC = json.loads((SR / 'views_corrected.json').read_text())
F6 = json.loads((S2 / 'corrected/f6_pagecheck.json').read_text())
N = json.loads((S2 / 'corrected/counts.json').read_text())
P = 'printed_here (primary)'
BRS = 'writing/research/enzyextract_broad_20261118/corrected/results.json'
S2T = 'paper/evidence/locked_test_20261109/stage2/corrected/table.json'
S2C = 'paper/evidence/locked_test_20261109/stage2/corrected/checked/results.json'


def br(run, rule=P, metric='all'):
    return BR['runs'][run]['rules'][rule][metric]


REG, COR = 'registered', 'corrected (F5 and F2)'


def f3(x):
    return f'{x:.3f}'


def d3(x):
    return f"{x['diff']:+.3f} ({x['lo']:+.3f} to {x['hi']:+.3f})" if 'diff' in x else f"{x['est']:+.3f} ({x['lo']:+.3f} to {x['hi']:+.3f})"


def iv(x):
    return f"{x['est']:.3f} ({x['lo']:.3f} to {x['hi']:.3f})"


def pexp(p):
    m, e = f'{p:.1e}'.split('e')
    return f'{m} × 10^{int(e)}'


def wn(run, rule=P):
    return br(run, rule)['papers_with_a_wrong_number']


def classes(run):
    t = br(run)['totals']
    return t


E = []


def add(where, what, printed, registered, corrected, finding, src_reg, src_cor, changes, kind=None):
    if kind is None:
        kind = 'what_if' if ('F4' in finding or 'F6' in finding or 'what-if' in where) else ('unreported' if 'F13' in finding else 'correction')
    E.append({'kind': kind, 'where': where, 'what': what, 'printed': printed, 'registered': registered, 'corrected': corrected,
              'finding': finding, 'source_registered': src_reg, 'source_corrected': src_cor, 'claim_changes': changes})


# ---------------------------------------------------------------------------------------------------- broad test
r, c = REG, COR
add('results.md:137; Table 1d (EnzyExtract row)', "papers in which EnzyExtract's database holds a wrong number, of 300", '80',
    str(wn(r)['enzyextract']), str(wn(c)['enzyextract']), 'F5, F2',
    'writing/research/enzyextract_broad_20261118/run/results.json#rules/printed_here (primary)/all/papers_with_a_wrong_number',
    f'{BRS}#runs/{COR}/rules/{P}/all/papers_with_a_wrong_number (F5 alone: {wn("F5 only")["enzyextract"]}; F2 alone: {wn("F2 only")["enzyextract"]})',
    'the count only; the claim stands')
add('results.md:137', 'papers in which CatLog holds a wrong number', '2 of those 80', f"{wn(r)['catlog']} of those {wn(r)['enzyextract']}",
    f"{wn(c)['catlog']} of those {wn(c)['enzyextract']}", 'F5, F2', 'run/results.json', BRS, 'no')
add('results.md:137; Table 1d (difference row)', 'papers on one side only, and the exact sign test', '78 and 0; P = 6.6 × 10⁻²⁴',
    f"{wn(r)['discordant_ee_only']} and {wn(r)['discordant_catlog_only']}; P = {pexp(wn(r)['sign_test_p'])}",
    f"{wn(c)['discordant_ee_only']} and {wn(c)['discordant_catlog_only']}; P = {pexp(wn(c)['sign_test_p'])}", 'F5, F2',
    'run/results.json', BRS, 'no: smaller, as strong')
for metric, key_, where in (('all', 'precision', 'results.md:138; Table 1d'), ('all', 'recall', 'results.md:138; Table 1d')):
    a, b = br(r, metric=metric)[key_], br(c, metric=metric)[key_]
    printed = {'precision': '0.981 against 0.910 (+0.071, +0.042 to +0.101)', 'recall': '+0.011 (−0.049 to +0.069), no difference claimed'}[key_]
    add(where, f'{key_}, CatLog against EnzyExtract, primary rule', printed, f"{f3(a['catlog'])} against {f3(a['enzyextract'])} ({d3(a)})",
        f"{f3(b['catlog'])} against {f3(b['enzyextract'])} ({d3(b)})", 'F2, F5; F10 for the registered upper bound (printed +0.101, is +0.100)' if key_ == 'precision' else 'F2, F5',
        'run/results.json (rounded to 4 places)', BRS, 'no: CatLog higher' if key_ == 'precision' else 'no: no difference claimed')
a, b = br(r, metric='Km')['recall'], br(c, metric='Km')['recall']
add('results.md:138; Table 1, footnote 10', 'Km recall, CatLog minus EnzyExtract', '−0.073 (−0.132 to −0.017), CatLog lower', d3(a), d3(b), 'F2',
    'run/results.json#rules/printed_here (primary)/Km/recall', f'{BRS}#runs/{COR}/rules/{P}/Km/recall', 'YES: the interval now includes zero; the clause goes')
for metric in ('kcat', 'Km', 'kcat/Km'):
    for k in ('recall', 'precision'):
        if metric == 'Km' and k == 'recall':
            continue
        a, b = br(r, metric=metric)[k], br(c, metric=metric)[k]
        add('not printed (Table 1d by constant)', f'{metric} {k}, CatLog minus EnzyExtract', '', d3(a), d3(b), 'F2, F5', 'run/results.json', BRS,
            'not printed; the audit (F8) asks to give every constant whose interval excludes zero')
add('results.md:139; Table 1, footnote 10', "CatLog's wrong numbers, and those in one paper", '129; 128', f"{br(r)['totals']['c_wrong_numbers']}; 128",
    f"{br(c)['totals']['c_wrong_numbers']}; 128", 'none', 'run/results.json', BRS, 'no')
a, b = br(r, 'printed_here, misprint corrected')['precision'], br(c, 'printed_here, misprint corrected')['precision']
add('results.md:140; Table 1, footnote 10', 'precision with misprints counted as corrected', '+0.056 (−0.009 to +0.102), no difference claimed', d3(a), d3(b),
    'F2, F5; F10 for the registered lower bound (printed −0.009, is −0.008)', 'run/results.json', BRS, 'no')
a, b = br(r, 'printed_here, misprint corrected')['recall'], br(c, 'printed_here, misprint corrected')['recall']
add('Table 1, footnote 10', 'recall with misprints counted as corrected', '−0.003 (−0.060 to +0.052)', d3(a), d3(b), 'F2, F5', 'run/results.json', BRS, 'no')
pr, pc = BR['post_hoc_without_12723605_F4']['registered'], BR['post_hoc_without_12723605_F4']['corrected']
for rule in (P, 'printed_here, misprint corrected'):
    add('not printed (F4: add after "no precision difference is claimed")', f'post hoc, without 12723605: precision ({rule})', '',
        d3(pr[rule]['precision']), d3(pc[rule]['precision']), 'F4 (post hoc)', f'{BRS}#post_hoc_without_12723605_F4/registered',
        f'{BRS}#post_hoc_without_12723605_F4/corrected', 'adds: without that paper the precision difference excludes zero under both views')
for col, rr_, k in (('CatLog', 'c', 'values'), ('EnzyExtract', 'e', 'values')):
    t0, t1 = br(r)['totals'], br(c)['totals']
    add('Table 1d', f'{col}: values compared', '9,107' if rr_ == 'c' else '9,691', f"{t0[rr_ + '_n']:,}", f"{t1[rr_ + '_n']:,}",
        'F2' if rr_ == 'e' else 'none', 'run/results.json', BRS, 'no')
add('Table 1d', 'recall, CatLog and EnzyExtract', '0.877; 0.866', f"{f3(br(r)['recall']['catlog'])}; {f3(br(r)['recall']['enzyextract'])}",
    f"{f3(br(c)['recall']['catlog'])}; {f3(br(c)['recall']['enzyextract'])}", 'F2, F5', 'run/results.json', BRS, 'no: no difference claimed')
add('Table 1d', 'precision, CatLog and EnzyExtract', '0.981; 0.910', f"{f3(br(r)['precision']['catlog'])}; {f3(br(r)['precision']['enzyextract'])}",
    f"{f3(br(c)['precision']['catlog'])}; {f3(br(c)['precision']['enzyextract'])}", 'F2, F5', 'run/results.json', BRS, 'no')
for k, printed, f10 in (('recall', '+0.076 (+0.024 to +0.127)', ''), ('precision', '+0.200 (+0.150 to +0.257)', '; F10 for the registered lower bound (printed +0.150, is +0.151)')):
    add('Table 1d (second rule)', f'{k}, measured-here rule', printed, d3(br(r, 'measured_here')[k]), d3(br(c, 'measured_here')[k]), 'F2, F5' + f10,
        'run/results.json', BRS, 'no')
t0, t1 = br(r)['totals'], br(c)['totals']
add('Table 1, footnote 10', 'the reference: values agreed or judged right', '10,189', f"{t0['ref']:,}", f"{t1['ref']:,}", 'F2, F5', 'run/results.json', BRS, 'no')
add('Table 1, footnote 10', "EnzyExtract's wrong numbers: at another scale, of another quantity, not in the paper", '792: 427, 270, 95',
    '792: 427, 270, 95', f"{t1['e_wrong_numbers']}: 418, 268, 95", 'F5 (8 at another scale), F2 (1 at another scale, 2 of another quantity)',
    'run/results.json; run/judged', f'{BRS}#runs/{COR}/rules/{P}/all/totals/e_wrong_numbers; the classes from score_corrected.py prepare()', 'no')
add('Table 1, footnote 10', "EnzyExtract's values credited to earlier work, and repeats", '616; 814', '616; 814', '616; 814', 'none', 'run/judged', BRS, 'no')
sec = BR['registered_secondaries_F13']
for g in ('pdf_papers', 'xml_only_papers'):
    a, b = sec['registered'][g], sec['corrected'][g]
    add('not printed (F13, registered secondary)', f"{g.replace('_', ' ')}: wrong-number papers CatLog and EnzyExtract; recall; precision", '',
        f"{a['papers_with_a_wrong_number']['catlog']} and {a['papers_with_a_wrong_number']['enzyextract']}; {d3(a['recall'])}; {d3(a['precision'])}",
        f"{b['papers_with_a_wrong_number']['catlog']} and {b['papers_with_a_wrong_number']['enzyextract']}; {d3(b['recall'])}; {d3(b['precision'])}",
        'F13', f'{BRS}#registered_secondaries_F13/registered', f'{BRS}#registered_secondaries_F13/corrected', 'adds one line: the same held on both kinds of paper')
add('Methods (broad test)', 'second judge: papers, values, same verdict', '19; 546; 544', '19; 546; 544', '19; 546; 544', 'none', 'run/judged', BRS, 'no')

# ---------------------------------------------------------------------------------------------------- second stage
def s2(mode, src):
    return T[mode]['sources'][src]['all']


def s2d(mode, src='run_RGF', metric='all', k='recall'):
    return T[mode]['catlog_minus'][src][metric][k]


for src, printed in (('run_RGF', '0.819 and 0.816 (Table 1c: 0.819 (0.759 to 0.873), 0.816 (0.743 to 0.883); 1,433 values)'),
                     ('catlog', '0.742 and 0.787 (Table 1c: 0.742 (0.673 to 0.808), 0.787 (0.718 to 0.856); 1,346 values)'),
                     ('plain', '0.768 and 0.777 (Table 1c: 0.768 (0.699 to 0.838), 0.777 (0.706 to 0.849); 1,411 values)'),
                     ('enzyextract_db', 'Table 1c: 0.259 (0.142 to 0.378), 0.835 (0.731 to 0.948); 443 values'),
                     ('brenda', 'Table 1c: 0.326 (0.274 to 0.385), 0.901 (0.853 to 0.944); 516 values')):
    a, b = s2('registered', src), s2('written', src)
    add('results.md:145; Table 1c; Fig. 3b legend', f'{src}: recall and precision against the curation', printed,
        f"{iv(a['recall'])}, {iv(a['precision'])}; {a['sys_n']:,} values", f"{iv(b['recall'])}, {iv(b['precision'])}; {b['sys_n']:,} values",
        'F1', 'paper/evidence/locked_test_20261109/stage2/results.json', f'{S2T}#written/sources/{src}/all', 'no (the order of the marks is the same)')
add('results.md:145; Table 1, footnote 7', 'CatLog minus the plain reading, recall and precision', '−0.027 (−0.047 to −0.011); +0.009 (−0.008 to +0.033)',
    f"{d3(s2d('registered', 'plain'))}; {d3(s2d('registered', 'plain', k='precision'))}", f"{d3(s2d('written', 'plain'))}; {d3(s2d('written', 'plain', k='precision'))}",
    'F1', 'stage2/results.json', S2T, 'no')
add('results.md:146; Table 1, footnote 7', 'CatLog minus EnzyExtract, recall and precision', '−0.078 (−0.165 to +0.015); −0.030 (−0.100 to +0.043)',
    f"{d3(s2d('registered'))}; {d3(s2d('registered', k='precision'))}", f"{d3(s2d('written'))}; {d3(s2d('written', k='precision'))}", 'F1', 'stage2/results.json', S2T,
    'no: no difference claimed')
add('results.md:146; Table 1, footnote 7', 'kcat recall, CatLog minus EnzyExtract', '−0.194 (−0.337 to −0.033), EnzyExtract higher',
    d3(s2d('registered', metric='kcat')), d3(s2d('written', metric='kcat')), 'F1 (19 curation kcat cells of 10514486 left unread)', 'stage2/results.json',
    f'{S2T}#written/catlog_minus/run_RGF/kcat/recall', 'YES: the interval now includes zero; the clause goes')
add('results.md:146; Table 1, footnote 7', 'Km precision, CatLog minus EnzyExtract', '+0.060 (+0.007 to +0.119), CatLog higher',
    d3(s2d('registered', metric='Km', k='precision')), d3(s2d('written', metric='Km', k='precision')), 'F1', 'stage2/results.json', S2T, 'no: holds')
o0, o1 = T['registered']['on_rgf_papers']['catlog_minus_rgf'], T['written']['on_rgf_papers']['catlog_minus_rgf']
add('results.md:146; Table 1, footnote 7', "on EnzyExtract's 78 papers with output, recall and precision", '−0.091 (−0.176 to −0.003); −0.033 (−0.104 to +0.041)',
    f"{d3(o0['recall'])}; {d3(o0['precision'])}", f"{d3(o1['recall'])}; {d3(o1['precision'])}", 'F1', 'stage2/results.json#on_papers_where_the_run_has_rows',
    f'{S2T}#written/on_rgf_papers', 'YES: the recall interval now includes zero; the clause goes')
w0, w1 = T['registered']['without_misprint_papers']['catlog_minus']['run_RGF'], T['written']['without_misprint_papers']['catlog_minus']['run_RGF']
add('not printed (stage 2 sensitivity)', 'without the two misprint papers, recall and precision', '', f"{d3(w0['recall'])}; {d3(w0['precision'])}",
    f"{d3(w1['recall'])}; {d3(w1['precision'])}", 'F1', 'stage2/results.json', S2T, 'no')
nr, nw = N['registered'], N['written']
add('Fig. 3b legend; Extended Data 9 legend', "the curation's scored values, and cells not scored", '1,428; 98 of 1,526',
    f"{nr['curation_scored']:,}; {nr['curation_unscored']} of {nr['curation_cells']:,}", f"{nw['curation_scored']:,}; {nw['curation_unscored']} of {nw['curation_cells']:,}",
    'F1', 'paper/evidence/locked_test_20261109/stage2/corrected/counts.json#registered', 'counts.json#written', 'the counts only')
add('Extended Data 9 legend', 'curation values per constant (kcat, Km, kcat/Km)', '382, 686, 360', ', '.join(str(nr['by_metric'][k]) for k in ('kcat', 'Km', 'kcat/Km')),
    ', '.join(str(nw['by_metric'][k]) for k in ('kcat', 'Km', 'kcat/Km')), 'F1', 'counts.json', 'counts.json', 'the counts only')
add('Extended Data 9 legend', "cells not scored per EnzyExtract run", '49 to 255', f"{nr['unread_range'][0]} to {nr['unread_range'][1]}",
    f"{nw['unread_range'][0]} to {nw['unread_range'][1]}", 'F1', 'counts.json', 'counts.json', 'the counts only')
add('Extended Data 9 legend', 'without the two misprint papers: papers and values', '77 papers, 1,397 values', f"77 papers, {nr['curation_scored_without_misprint_papers']:,} values",
    f"77 papers, {nw['curation_scored_without_misprint_papers']:,} values", 'F1', 'counts.json', 'counts.json', 'the counts only')
add('Extended Data 9 legend', 'the best of the nine runs on both measures', 'RGF', 'RGF', f"{T['written']['best_run']['recall'][4:]} (recall), {T['written']['best_run']['precision'][4:]} (precision)",
    'F1', 'stage2/results.json#best_run', f'{S2T}#written/best_run', 'no')
for run in sorted(n for n in T['written']['sources'] if n.startswith('run_') and n != 'run_RGF'):
    a, b = s2('registered', run), s2('written', run)
    add('Extended Data 9 (table)', f'{run[4:]}: recall and precision against the curation', '', f"{f3(a['recall']['est'])}, {f3(a['precision']['est'])}",
        f"{f3(b['recall']['est'])}, {f3(b['precision']['est'])}", 'F1', 'stage2/results.json', f'{S2T}#written/sources/{run}/all', 'no')

# CatLog minus BRENDA, a registered endpoint of stage 2 (STAGE2.md, endpoint 4) reported nowhere (databases audit, finding 1)
for metric in ('all', 'kcat', 'Km', 'kcat/Km'):
    a0, a1 = T['registered']['catlog_minus']['brenda'][metric], T['written']['catlog_minus']['brenda'][metric]
    add('not printed (stage 2, endpoint 4)', f'CatLog minus BRENDA against the curation, {metric}: recall; precision', '',
        f"{d3(a0['recall'])}; {d3(a0['precision'])}", f"{d3(a1['recall'])}; {d3(a1['precision'])}", 'databases audit F1 (unreported); F1 for the correction',
        'paper/evidence/locked_test_20261109/stage2/results.json#catlog_minus/brenda', f'{S2T}#written/catlog_minus/brenda',
        'adds: BRENDA\'s precision against the curation is higher than CatLog\'s, also once read as written' if metric == 'all' else 'adds (by constant)', kind='unreported')
b0, b1 = T['registered']['without_misprint_papers']['catlog_minus']['brenda'], T['written']['without_misprint_papers']['catlog_minus']['brenda']
add('not printed (stage 2, endpoint 4)', 'CatLog minus BRENDA without the two misprint papers: recall; precision', '',
    f"{d3(b0['recall'])}; {d3(b0['precision'])}", f"{d3(b1['recall'])}; {d3(b1['precision'])}", 'databases audit F1 (unreported); F1 for the correction',
    'paper/evidence/locked_test_20261109/stage2/results.json#without_misprint_papers', f'{S2T}#written/without_misprint_papers/catlog_minus/brenda',
    'adds: no longer a difference once read as written', kind='unreported')
# the page check
v0, v1 = PCr['verdicts'], PCc['verdicts']
add('results.md:151; Table 1, footnote 8', "the curation's checked values at another scale", '90 (of 505)',
    f"{v0['curation']['measured_here_other_scale']} (of {PCr['values_checked']['curation']})", f"{v1['curation']['measured_here_other_scale']} (of {PCc['values_checked']['curation']})",
    'F1: 15 were cells the units code misread (the judges\' right value is the cell as written); 13 now count as measured here, and 2 agree across all three readings and leave the check', 'paper/evidence/locked_test_20261109/stage2/checked/results.json#verdicts',
    f'{S2C}#verdicts', 'the count only')
add('Table 1, footnote 8', "EnzyExtract's checked values at another scale", '100 (of 263)',
    f"{v0['rgf']['measured_here_other_scale']} (of {PCr['values_checked']['rgf']})", f"{v1['rgf']['measured_here_other_scale']} (of {PCc['values_checked']['rgf']})",
    'F1: 3 were misread cells; 1 now counts as measured here, and 2 agree across all three readings and leave the check', 'checked/results.json#verdicts', f'{S2C}#verdicts', 'the count only')
add('results.md:151; Table 1, footnote 8', "the curation's checked values credited to earlier work, and repeats", '135; 81',
    f"{v0['curation']['credited_to_earlier_work']}; {v0['curation']['repeat_of_one_printed_value']}", f"{v1['curation']['credited_to_earlier_work']}; {v1['curation']['repeat_of_one_printed_value']}",
    'none', 'checked/results.json', S2C, 'no')
add('Table 1, footnote 8; Fig. 3b legend', 'values checked, and papers', '1,055 values in 63 papers', '1,055 values in 63 papers',
    f"1,055 checked; {sum(PCc['values_checked'].values()):,} of them still disputed once the misreads are fixed, in {PCc['papers_with_a_dispute']} papers",
    'F1', 'checked/results.json#values_checked', f'{S2C}#values_checked', 'no: 1,055 is what the agents checked')
add('Table 1, footnote 8; Fig. 3b legend', 'the reference: agreed by all three (not checked) plus judged right', '1,367 (923 + 444)',
    f"{sum(PCr['reference'][m]['values']['as_printed'] for m in PCr['reference']):,} ({N['registered']['pagecheck_agreed_by_all_three']} + {sum(PCr['reference'][m]['values']['as_printed'] for m in PCr['reference']) - N['registered']['pagecheck_agreed_by_all_three']})",
    f"{sum(PCc['reference'][m]['values']['as_printed'] for m in PCc['reference']):,} ({N['misreads']['pagecheck_agreed_by_all_three']} + {sum(PCc['reference'][m]['values']['as_printed'] for m in PCc['reference']) - N['misreads']['pagecheck_agreed_by_all_three']})",
    'F1; reference merge', 'checked/results.json#reference; counts.json', f'{S2C}#reference; counts.json#misreads', 'the split only')
for src, printed in (('catlog', '0.952 (0.923 to 0.976) and 0.967 (0.925 to 0.998)'), ('run_RGF', '0.748 (0.682 to 0.811) and 0.714 (0.640 to 0.787)')):
    a, b = PCr['views']['as_printed']['sources'][src]['all'], PCc['views']['as_printed']['sources'][src]['all']
    add('Table 1, footnote 8; Fig. 3b legend (arrows)', f'{src}: recall and precision against the checked reference', printed, f"{iv(a['recall'])} and {iv(a['precision'])}",
        f"{iv(b['recall'])} and {iv(b['precision'])}", 'F1; reference merge', 'checked/results.json#views/as_printed', f'{S2C}#views/as_printed', 'no')
a, b = PCr['views']['as_printed']['sources']['plain']['all'], PCc['views']['as_printed']['sources']['plain']['all']
add('Table 1, footnote 8; Fig. 3b legend', "the plain reading's lower bounds", 'at least 0.974 (0.956 to 0.989); at least 0.944', f"{iv(a['recall'])}; {f3(a['precision']['est'])}",
    f"{iv(b['recall'])}; {f3(b['precision']['est'])}", 'F1; reference merge', 'checked/results.json', S2C, 'no')
for v, printed in (('as_printed', ''), ('reprints_repeats_right', '+0.054 (−0.029 to +0.141); +0.120 (+0.059 to +0.184)')):
    a, b = VR['views'][v]['catlog_minus']['run_RGF']['all'], VC['views'][v]['catlog_minus']['run_RGF']['all']
    add('Table 1, footnote 8 (its last two numbers)' if printed else 'not printed (page check, as printed)',
        f'page check, CatLog minus EnzyExtract, recall; precision ({v}' + (': credited and repeated values counted as right)' if printed else ')'), printed,
        f"{d3(a['recall'])}; {d3(a['precision'])}", f"{d3(b['recall'])}; {d3(b['precision'])}", 'F1; reference merge (both fixed)',
        'paper/evidence/stage2_scoring_rules_20261117/views.json', 'paper/evidence/stage2_scoring_rules_20261117/views_corrected.json',
        'the numbers only: the recall interval still includes zero, the precision interval still excludes it' if printed else 'no')
MO = json.loads((S2 / 'corrected/checked_misreads_fixed_only/results.json').read_text())
MG = json.loads((S2 / 'corrected/checked_merge_fixed_only/results.json').read_text())
def refsize(d, v):
    return sum(d['reference'][m]['values'][v] for m in d['reference']) if v in d['reference'][next(iter(d['reference']))]['values'] else None
RR = json.loads((S2 / 'corrected/checked_registered_reproduced/results.json').read_text())
MERGE_RULE = ("reference merge: a reading's value judged right may merge only into a reference value that the same reading does "
              "not already hold, i.e. not into a curation value that reading matches (the recounts' finding)")
AB, EN = 'right_values_the_registered_merge_sent_into_a_value_their_own_reading_holds', 'right_values_entering_the_reference_through_the_merge_fix'
add('Table 1, footnote 8 (the page check\'s reference)', "values judged right that the registered reference merged into a value their own reading already holds, "
    "so that they never entered it and counted against their own reading: CatLog; RGF, by rule", '',
    '; '.join(f"{v} {RR[AB][v]['catlog']}; {RR[AB][v]['rgf']}" for v in RR[AB]) + ' (the same with the misreads fixed: '
    + '; '.join(f"{v} {MO[AB][v]['catlog']}; {MO[AB][v]['rgf']}" for v in MO[AB]) + ')',
    'none; the values that now enter the reference because of the fix (its growth), both fixes: ' + '; '.join(f"{v} {PCc[EN][v]['catlog']}; {PCc[EN][v]['rgf']}" for v in PCc[EN])
    + " (the others merge into reference values their reading does not hold)",
    MERGE_RULE, 'corrected/checked_registered_reproduced/results.json, checked_misreads_fixed_only/results.json', S2C, 'the count only', kind='correction')
for v in ('as_printed', 'corrected', 'reprints_right', 'reprints_repeats_right'):
    add('not printed (page check, each fix alone)', f'page check, the reference ({v}): values', '',
        f"{refsize(RR, v):,} (registered); {refsize(MO, v):,} with the misreads fixed only", f"{refsize(MG, v):,} with the merge fixed only; {refsize(PCc, v):,} with both",
        MERGE_RULE + '; F1', 'corrected/checked_registered_reproduced/results.json#reference', f'{S2C}#reference', 'the count only', kind='correction')
for v in ('as_printed', 'corrected', 'reprints_right', 'reprints_repeats_right'):
    a0 = VR['views'][v]['catlog_minus']['run_RGF']['all']
    a1 = json.loads((SR / 'views_corrected.json').read_text())['views'][v]['catlog_minus']['run_RGF']['all']
    m1 = MG['views'][v]['catlog_minus']['run_RGF']['all']
    o1 = MO['views'][v]['catlog_minus']['run_RGF']['all']
    add({'reprints_repeats_right': 'Table 1, footnote 8', 'as_printed': 'Table 1, footnote 8; Fig. 3b legend (arrows)'}.get(v, 'not printed (page check)'),
        f'page check, CatLog minus EnzyExtract ({v}), each fix alone: recall; precision', '',
        f"{d3(a0['recall'])}; {d3(a0['precision'])}", f"merge fixed only {d3(m1['recall'])}; {d3(m1['precision'])} / misreads fixed only {d3(o1['recall'])}; {d3(o1['precision'])} / both {d3(a1['recall'])}; {d3(a1['precision'])}",
        MERGE_RULE + '; F1', 'paper/evidence/stage2_scoring_rules_20261117/views.json',
        'stage2/corrected/checked_merge_fixed_only, checked_misreads_fixed_only, checked (results.json)', 'the split of the two fixes', kind='correction')
WI = json.loads((S2 / 'corrected/checked_whatif_repeats_keep_the_registered_merge/results.json').read_text())
w0, w1 = VR['views']['reprints_repeats_right']['catlog_minus']['run_RGF']['all'], WI['views']['reprints_repeats_right']['catlog_minus']['run_RGF']['all']
add('Table 1, footnote 8 (its last two numbers): what-if',
    "page check, credited and repeated values counted as right, with RGF's repeats of one printed value kept at the registered merge "
    "(under this rule the fix lets them in as second copies of values already in the reference): CatLog minus EnzyExtract, recall; precision", '',
    f"{d3(w0['recall'])}; {d3(w0['precision'])}", f"{d3(w1['recall'])}; {d3(w1['precision'])} (both fixes otherwise; with them all "
    f"{d3(VC['views']['reprints_repeats_right']['catlog_minus']['run_RGF']['all']['recall'])}; {d3(VC['views']['reprints_repeats_right']['catlog_minus']['run_RGF']['all']['precision'])})",
    "what-if (post hoc; the merge recount's): the registered builder already adds the curation's repeats judged right as reference values",
    'paper/evidence/stage2_scoring_rules_20261117/views.json',
    'paper/evidence/locked_test_20261109/stage2/corrected/checked_whatif_repeats_keep_the_registered_merge/results.json; recount_merge.json#problems',
    'no: the recall interval includes zero and the precision interval excludes it either way', kind='what_if')
# F6
fw, fo = T['written']['without_finetuning_papers']['catlog_minus']['run_RGF'], T['written']['finetuning_papers_only']['catlog_minus']['run_RGF']
gw, go = T['registered']['without_finetuning_papers']['catlog_minus']['run_RGF'], T['registered']['finetuning_papers_only']['catlog_minus']['run_RGF']
add('not printed (F6: add to Table 1, footnote 9, or the Extended Data 9 legend)', "the 79 papers in EnzyExtract's 52 fine-tuning papers", '', '15', '15', 'F6',
    'writing/research/enzyextract_broad_20261118/ee_finetune_train_pmids.txt', f'{S2T}#written/finetuning_papers_only/papers', 'adds one sentence')
add('not printed (F6, post hoc)', 'against the curation without the 15 and with only the 15: recall; precision, CatLog minus EnzyExtract', '',
    f"without {d3(gw['recall'])}; {d3(gw['precision'])} / only {d3(go['recall'])}; {d3(go['precision'])}",
    f"without {d3(fw['recall'])}; {d3(fw['precision'])} / only {d3(fo['recall'])}; {d3(fo['precision'])}", 'F6, F1', 'stage2/corrected/table.json#registered', S2T,
    "no: on the other 64 papers EnzyExtract's agreement with its own curation is higher still")
add('not printed (F6, post hoc)', 'page check: papers whose checked values include a wrong number, EnzyExtract against CatLog, on the 64 and the 15', '',
    f"{F6['registered']['without_finetuning_papers']['rgf']} against {F6['registered']['without_finetuning_papers']['catlog']}; {F6['registered']['finetuning_papers_only']['rgf']} against {F6['registered']['finetuning_papers_only']['catlog']}",
    f"{F6['misreads']['without_finetuning_papers']['rgf']} against {F6['misreads']['without_finetuning_papers']['catlog']}; {F6['misreads']['finetuning_papers_only']['rgf']} against {F6['misreads']['finetuning_papers_only']['catlog']}",
    'F6', 'paper/evidence/locked_test_20261109/stage2/corrected/f6_pagecheck.json#registered', 'f6_pagecheck.json#misreads', 'no')

W = BR['what_ifs_post_hoc']
k1 = '12723605: its 128 kcat/Km counted right'
k2 = 'EnzyExtract repeats with no listing keeping its own verdict: one listing each counted right'
k3 = 'EnzyExtract unread bounds, not-detected, relative and per-mass cells counted as wrong numbers'
def pw(x):
    return f"{x['catlog']} and {x['enzyextract']} ({x['discordant_ee_only']}:{x['discordant_catlog_only']}, P = {pexp(x['sign_test_p'])})"
for name, k in ((k1, k1), (k2, k2)):
    a, b = W['registered'][k][P], W['corrected'][k][P]
    add('what-if (broad test, post hoc)', name + ': wrong-number papers; recall; precision', '',
        f"{pw(a['papers_with_a_wrong_number'])}; {d3(a['recall'])}; {d3(a['precision'])}", f"{pw(b['papers_with_a_wrong_number'])}; {d3(b['recall'])}; {d3(b['precision'])}",
        'second recount' if k == k1 else 'second recount (97 values in 10 groups)', f'{BRS}#what_ifs_post_hoc/registered', f'{BRS}#what_ifs_post_hoc/corrected', 'what-if only', kind='what_if')
a, b = W['registered'][k3], W['corrected'][k3]
add('what-if (broad test, post hoc)', f"{k3} ({a['cells']} distinct cells in {a['papers_with_such_cells']} papers): wrong-number papers", '',
    pw(a['papers_with_a_wrong_number']), pw(b['papers_with_a_wrong_number']), 'second recount (113 cells, 96 papers, with each repeated cell counted)',
    f'{BRS}#what_ifs_post_hoc/registered', f'{BRS}#what_ifs_post_hoc/corrected', 'what-if only: the plan leaves such cells unscored, lenient to EnzyExtract', kind='what_if')
aud = BR['runs']['F5 and F2 as the audit defined it (check)']['rules'][P]['all']
add('what-if (broad test, post hoc)', "the scope fix as the audit and the second recount define it (only values judged right out, 270), with F5: wrong-number papers; recall; precision", '',
    '', f"{pw(aud['papers_with_a_wrong_number'])}; {d3(aud['recall'])}; {d3(aud['precision'])}", 'audit F2; second recount',
    '', f'{BRS}#runs/F5 and F2 as the audit defined it (check)', 'what-if only', kind='what_if')
(HERE / 'corrections.json').write_text(json.dumps({'entries': E}, indent=1, ensure_ascii=False) + '\n')
L = []
for kind, title in (('correction', 'Scoring errors fixed'), ('unreported', 'Registered endpoints that were not reported'), ('what_if', 'What-ifs (post hoc, not corrections)')):
    L += [f'### {title}', '', '| Where | What | Printed | Registered (reproduced) | Corrected | Finding | Claim changes |', '|---|---|---|---|---|---|---|']
    for e in E:
        if e['kind'] == kind:
            L.append(f"| {e['where']} | {e['what']} | {e['printed'] or '—'} | {e['registered'] or '—'} | {e['corrected']} | {e['finding']} | {e['claim_changes']} |")
    L.append('')
F5S = BR.get('F5_strings', [])
L += ['### F5 from the strings themselves', '', '| Paper | String in the database | Registered reading | Without the error term | Verdict | Judge\'s right value | CatLog stores it | Agreed once read |',
      '|---|---|---|---|---|---|---|---|']
for x in F5S:
    L.append(f"| {x['pmid']} | `{x['string']}` | {x['registered_reading']:g} | {x['reading_without_the_error_term']:g} | {x['verdict']} | {x['judges_right_value'] or '—'} | "
             f"{'yes' if x['catlog_stores_it'] else 'no'} | {'yes' if x['agreed_after_matching_again'] else 'no'} |")
L.append('')
(HERE / 'corrected' / 'corrections_table.md').write_text('\n'.join(L) + '\n')
print(len(E), 'entries written')
