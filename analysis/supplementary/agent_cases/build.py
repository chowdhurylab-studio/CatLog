#!/usr/bin/env python3
"""Build the two Supplementary items on the agent cases from case_data/cases.json (extract.py) and the checked lines
(case_data/lines/batch<k>.checked.json, written and checked by agents from the cases' checked cells, BRIEF.md):

  writing/manuscript/supp_data_agent_cases.xlsx and .csv   all 233 cases, one row each (Supplementary Data)
  writing/manuscript/supp_table_agent_cases.md             the twelve cases of the table (Supplementary Table)

It checks every line first (all 233 present, word limits, the found-by labels, words the brief forbids) and stops on
a fault rather than fix it. Run: python3 -I -B paper/evidence/agent_highlights_20261028/case_data/build.py
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path('<the CatLog folder>')
CD = ROOT / 'paper/evidence/agent_highlights_20261028/case_data'
MS = ROOT / 'writing/manuscript'
LIMITS = {'where': 10, 'found': 35, 'databases': 20}
LABELS = {'reader', 'verifier', 'reader and verifier', 'reader in the pass for values not detected',
          'verifier in the pass for values not detected', 'auditor', 'database-check agent', 'sweep agent',
          'census agent (values not detected)'}
FORBIDDEN = re.compile(r'\b(slot|metric|bound|bounds|censored|provenance|prompts?|row_id|reread|unitfix|cellfix|gated|'
                       r'catlog-batch|claude|opus|sonnet|the owner)\b|work/|\.json|wf_|agent-[0-9a-f]{6}|20\d\d-\d\d-\d\d|;',
                       re.I)
KIND = {'Bound or not detected': 'Limit or not detected'}  # the one kind name that uses a project word
COLUMNS = ['Case', 'Paper (PMID, or DOI where the paper has none)', 'Journal', 'Year', 'Kind', 'Where in the paper',
           'What the agent found', 'Found by', 'How the agent came to it', 'Checks (agents told to refute it)',
           'Databases that list the caught number', 'Also in']


def numbered(text):
    """Put the Supplementary numbers from writing/manuscript/supp_numbers.json in place of their [[CHECK]] markers."""
    import json as _json
    f = Path('<the CatLog folder>/writing/manuscript/supp_numbers.json')
    nums = _json.loads(f.read_text(encoding='utf-8')) if f.exists() else {}
    for kind, key in (('Note', 'note'), ('Table', 'table'), ('Data', 'data')):
        n = str(nums.get(key) or '').strip()
        if n:
            text = re.sub(r'Supplementary ' + kind + r' \[\[CHECK:[^\]]*\]\]', 'Supplementary ' + kind + ' ' + n, text)
            text = text.replace('Supplementary ' + kind + ' [number to give]', 'Supplementary ' + kind + ' ' + n)
    return text


def words(s):
    return len(s.split())


def load():
    cases = json.loads((CD / 'cases.json').read_text(encoding='utf-8'))
    meta = json.loads((CD / 'meta.json').read_text(encoding='utf-8'))
    lines = {}
    for b in sorted((CD / 'batches').glob('batch*.json')):
        ch = CD / 'lines' / (b.stem + '.changes.json')
        done = ch.exists() and any(str(x.get('case')) == 'done' for x in json.loads(ch.read_text(encoding='utf-8')))
        if not done:
            sys.exit(f'{b.stem}: its check has not finished (no "done" entry in {ch.name})')
    for f in sorted((CD / 'lines').glob('batch*.checked.json')):
        for x in json.loads(f.read_text(encoding='utf-8')):
            if x['case'] in lines:
                sys.exit(f'case {x["case"]} twice')
            lines[x['case']] = x
    faults = []
    for c in cases:
        x = lines.get(c['case'])
        if not x:
            faults.append(f'case {c["case"]}: no checked line')
            continue
        if str(x.get('pmid')) != c['pmid']:
            faults.append(f'case {c["case"]}: pmid {x.get("pmid")} is not {c["pmid"]}')
        for k, lim in LIMITS.items():
            v = (x.get(k) or '').strip()
            if not v:
                faults.append(f'case {c["case"]}: {k} empty')
            elif words(v) > lim:
                faults.append(f'case {c["case"]}: {k} has {words(v)} words, limit {lim}')
            if FORBIDDEN.search(v):
                faults.append(f'case {c["case"]}: {k} uses "{FORBIDDEN.search(v).group(0)}"')
        fb = (x.get('found_by') or '').strip()
        if fb not in LABELS and not (fb.startswith('other: ') and words(fb[7:]) <= 3):
            faults.append(f'case {c["case"]}: found_by "{fb}" is not on the list')
    if faults:
        print('\n'.join(faults))
        sys.exit(f'{len(faults)} faults: fix the checked lines (by agent or by hand, recorded), then run again')
    return cases, meta, lines


def also_in(c):
    out = []
    if c['main_table_row']:
        out.append(numbered('Supplementary Table [number to give]').replace(' [number to give]', '') + f', row {c["main_table_row"]}')
    return ' and '.join(out)


def checks(c):
    """The checks cell for outside readers: four cells name the internal folder of a rerun's verdicts (final review #22)."""
    s = c['cells']['checks'].replace(', in round4/checks/', '')
    if '/' in s:
        sys.exit(f'case {c["case"]}: the checks cell still names a path: {s}')
    return s


def rows(cases, meta, lines):
    for c in cases:
        x = lines[c['case']]
        paper = c['pmid'] if c['pmid'].isdigit() else meta[c['pmid']].get('doi', c['pmid'])
        yield [c['case'], paper, c['journal'], c['year'], KIND.get(c['kind'], c['kind']), x['where'].strip(),
               x['found'].strip(), x['found_by'].strip(), c['how'], checks(c), x['databases'].strip(),
               also_in(c)]


def write_data(cases, meta, lines):
    data = list(rows(cases, meta, lines))
    with open(MS / 'supp_data_agent_cases.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        w.writerows(data)
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    wb = Workbook()
    ws = wb.active
    ws.title = 'Cases'
    ws.append(COLUMNS)
    for r in data:
        ws.append(r)
    widths = [6, 16, 22, 6, 30, 26, 70, 22, 22, 26, 40, 30]
    for i, wdt in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = wdt
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'A2'
    rd = wb.create_sheet('Read me')
    for line in README:
        rd.append([numbered(line)])
    rd.column_dimensions['A'].width = 120
    for row in rd.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical='top')
    wb.save(MS / 'supp_data_agent_cases.xlsx')
    return len(data)


README = [
    'Supplementary Data [number to give]. Agent cases',
    'Frozen on 16 November 2026. The cases were checked against their papers between 28 October and 6 November 2026, '
    'and since 6 November no stored value of these 233 papers has changed. CatLog and its website keep growing, so a '
    'later reading of one of these papers may add values; this sheet does not change.',
    'One row for each of the 233 agent cases that held of the 234 checked against their papers. A case is a moment when an agent, reading or checking a paper, found that the paper, CatLog\'s copy '
    'of it or a database\'s copy of its values was wrong or unclear about a value, or did more than its instructions '
    'asked to settle one.',
    'Kind: the kind of error, as three agents coded it separately. "Limit or not detected": a value printed as a limit '
    '(< or >) or as not detected.',
    'Where in the paper, What the agent found, Found by and Databases: short forms of each case\'s checked record, '
    'written and then checked against that record field by field.',
    'Found by: the agent that found the case. The reader copies the paper\'s values. The verifier, given the reader\'s '
    'values, finds each in the paper again. The pass for values not detected and the census are later readings for '
    'values printed as a limit or as not detected. Auditors re-check sampled values against the paper. Database-check '
    'agents decide a value a database lists differently. Sweep agents check what code flags across the catalogue.',
    'How the agent came to it: own reasoning (nothing in its instructions, code or an earlier agent supplied the step '
    'that decided the case), its instructions (a check its instructions name, applied by the agent), code flagged it '
    '(a code check raised it and the agent confirmed), or an earlier agent proposed it.',
    'Checks: the verdicts of the agents told to refute the case against its paper. "With corrections": the case held '
    'with details corrected, and this sheet gives the corrected version.',
    'Databases: which databases (BRENDA, SABIO-RK, OED, SKiD, STRENDA DB, UniProt) list the number the agent caught, '
    'as matched by code to the same paper and quantity within 1%.',
    'Also in: the twelve cases of Supplementary Table [number to give].',
]


def write_table(cases, meta, lines):
    twelve = sorted((c for c in cases if c['main_table_row']), key=lambda c: c['main_table_row'])
    out = [
        '# Supplementary Table [[CHECK: the number to give]]. Twelve agent cases',
        '',
        '<!-- Frozen for the paper on 16 November 2026 (paper/evidence/agent_highlights_20261028/FREEZE.md). Built by paper/evidence/agent_highlights_20261028/case_data/build.py from case_data/cases.json (paper/04_agent_case_tables.md, the main table; paper/04_supplementary_case_tables.md, the checked rows) and the checked lines (case_data/lines/). Change those, never this file. -->',
        '',
        'Three agents, each working alone, picked these twelve by a rule written before the pick, from the cases that '
        "the agent's own reasoning decided and in which the agent had seen no database value. All 233 cases"
        ' are in Supplementary Data [[CHECK: its number]]. '
        '<!-- src: paper/04_agent_case_tables.md#Main table (12 of the 71 eligible; three agents applied the rule separately) ; '
        'paper/evidence/agent_highlights_20261028/LOG.md#2026-10-30 08:35 (the rule written first; own reasoning, the agent blind) ; '
        'as of 2026-11-06 ; judged by agents ; refresh: no -->',
        '',
        '| Row | Paper | Kind | What the agent found | Databases that list the caught number |',
        '|---|---|---|---|---|',
    ]
    for c in twelve:
        x = lines[c['case']]
        paper = f'{c["pmid"]}, {c["journal"]} {c["year"]}'
        cells = [str(c['main_table_row']), paper, KIND.get(c['kind'], c['kind']), x['found'].strip(),
                 x['databases'].strip()]
        out.append('| ' + ' | '.join(s.replace('|', '/') for s in cells) + ' |')
    (MS / 'supp_table_agent_cases.md').write_text(numbered('\n'.join(out) + '\n'), encoding='utf-8')
    return len(twelve)


if __name__ == '__main__':
    cases, meta, lines = load()
    n = write_data(cases, meta, lines)
    t = write_table(cases, meta, lines)
    print(f'wrote writing/manuscript/supp_data_agent_cases.xlsx and .csv ({n} cases) and supp_table_agent_cases.md ({t} rows)')
