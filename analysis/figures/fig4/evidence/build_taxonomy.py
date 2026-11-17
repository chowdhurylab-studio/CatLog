#!/usr/bin/env python3
"""NAME's failure taxonomy (Fig. 1 v5, Extended Data table): the error ledger brought from 21 October to 2 November
2026, then one line per failure class (repeats merged): where the failure starts, one example, when and how it was
found, the guard it became, the layer that guard sits in, the values it touched and whether it is closed.

    python3 build_taxonomy.py        reads git, CatLog's files and log.tsv; writes only into this folder:
                                     error_ledger_v5.tsv, taxonomy.tsv, taxonomy_numbers.json, TAXONOMY.md

Checked here, as paper/evidence/rethink_20261101/r03_error_ledger.py checks the 22 October ledger: every quoted
evidence string must be found in the source it names (a commit message, a file at a commit, a file on disk, log.tsv),
or the script stops. For files, the line of each quote goes into the sources column. The 50 lines of the 22 October
ledger are read from that file and their 96 quoted strings re-checked (CLAUDE.md as it stood at 4523db0, the last
commit of that file before the ledger was built). Counts the script takes from log.tsv and rejected.jsonl are
recomputed and asserted where a commit message states them.

An independent agent checked every line on 2 November 2026 (TAXONOMY_CHECK.md). Its fixes are applied in the blocks
marked 'check of 2 November' (ledger lines added, notes on five 22 October lines, the fix() calls after CLASSES, eight
classes added) and recomputed here; the files as first built are kept in taxonomy_check/before/.
"""
import ast
import bisect
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = '<the CatLog folder>'
HERE = os.path.dirname(os.path.abspath(__file__))
REL = os.path.relpath(HERE, ROOT)
OLD_LEDGER = 'paper/figures/layers_ledger/evidence/rethink_20261022/error_ledger.tsv'
R03 = 'paper/evidence/rethink_20261101/r03_error_ledger.py'
STATUS = REL + '/taxonomy_evidence/status_20261102.txt'
OLD_SRC = {'CLAUDE.md': 'gitfile:4523db0:CLAUDE.md', '../verify/VERIFY.md': 'paper/planning/top_journal_20261021/verify/VERIFY.md'}
FIX22 = 'paper/planning/top_journal_20261021/FIXES_FOR_MAIN_CHAT_20261022.md'
FIX31 = 'paper/planning/FIXES_FOR_MAIN_CHAT_20261031.md'
REPLY = 'paper/planning/FIXES_FOR_MAIN_CHAT_20261031_REPLY.md'
BLIND = 'paper/evidence/blind_reread_20261022/SUMMARY.md'
CASES = 'paper/04_agent_case_tables.md'
BOXES = 'paper/05_agent_case_boxes.md'
AGENTS = 'paper/01_what_the_agents_did.md'
LAYERS = 'paper/figures/layers_ledger/layers_ledger_numbers.json'
ASSESS = 'OLD_CATLOG_ASSESSMENT_20261007.md'
EXPERT = '<the earlier CatLog folder>/EXPERT_REVIEW_2026-08-14.md'
H2H = 'paper/planning/top_journal_20261021/h2h/REPORT.md'
TRACKER = 'paper/evidence/agent_highlights_20261028/TRACKER.md'
TWICE = REL + '/taxonomy_evidence/same_cell_twice_20261102.tsv'  # written by the check of 2 November
CHECKED = 'TAXONOMY_CHECK.md'
LOG_CUTOFF = '2026-11-02 08:00'  # log.tsv lines and rejected rows before this time (the loop keeps writing)

ORIGINS = ['the printed paper', 'the PDF text layer or OCR', 'the reading agent', 'identity and pairing',
           'conversion and units', 'the databases', 'the process']
LAYER_NAMES = ['reader prompt', 'verifier prompt', 'code conversion', 'code check', 'sweep from the paper\'s own numbers',
               'database check', 'audit', 'people']
STATUSES = ['rule', 'flag kept as printed', 'open']
KINDS = {'FA': 'let a wrong value or label in', 'FR': 'refused or lost right values', 'PROC': 'process'}
ROUTES = ['reader', 'verifier', 'code check', 'audit', 'database check', 'sweep', 'operator', 'reviewer', 'owner',
          'outside review', 'old system']
SWEEP = "sweep from the paper's own numbers"


def norm(x):
    return re.sub(r'\s+', ' ', x).strip()


# ----------------------------------------------------------------------------------------------- sources and quotes
_SRC = {}


def src(s):
    """(normalised full text, normalised lines or None)."""
    if s in _SRC:
        return _SRC[s]
    if s.startswith('git:'):
        t = subprocess.run(['git', '-C', ROOT, 'show', '-s', '--format=%ad %B', '--date=short', s[4:]],
                           capture_output=True, text=True, check=True).stdout
        lines = None
    elif s.startswith('gitfile:'):
        h, p = s[8:].split(':', 1)
        t = subprocess.run(['git', '-C', ROOT, 'show', f'{h}:{p}'], capture_output=True, text=True, check=True).stdout
        lines = t.split('\n')
    elif s.startswith('path:'):
        p = s[5:]
        if not os.path.exists(p if p.startswith('/') else os.path.join(ROOT, p)):
            raise SystemExit(f'missing evidence path {p}')
        t, lines = '', None
    else:
        t = open(s if s.startswith('/') else os.path.join(ROOT, s), encoding='utf-8', errors='replace').read()
        lines = t.split('\n')
    _SRC[s] = (norm(t), [norm(x) for x in lines] if lines is not None else None)
    return _SRC[s]


def locate(s, q):
    """The line of quote q in source s: an int (0 for a commit message or a path), or None when not found."""
    if s.startswith('path:'):
        src(s)
        return 0
    t, lines = src(s)
    q = norm(q)
    if not q or q not in t:
        return None
    if lines is None:
        return 0
    for i, x in enumerate(lines):
        if q in x:
            return i + 1
    starts, pos = [], 0
    for x in lines:
        starts.append(pos)
        pos += len(x) + 1
    k = ' '.join(lines).find(q)
    return bisect.bisect_right(starts, k) if k >= 0 else 0


BAD = []


def check(items, where):
    out = []
    for s, q in items:
        ln = locate(s, q)
        if ln is None:
            BAD.append((where, s, q[:90]))
        out.append((s, ln))
    return out


def show(found):
    by = collections.OrderedDict()
    for s, ln in found:
        by.setdefault(s, set())
        if ln:
            by[s].add(ln)
    parts = []
    for s, lns in by.items():
        name = s
        if s.startswith('gitfile:'):
            h, p = s[8:].split(':', 1)
            name = f'{p}@{h}'
        elif s.startswith('path:'):
            name = s[5:]
        elif s.startswith('<the home folder>/Documents/'):
            name = '~/Documents/' + s[len('<the home folder>/Documents/'):]
        parts.append(name + (':' + ','.join(str(x) for x in sorted(lns)) if lns else ''))
    return '; '.join(parts)


def git_date(h):
    return subprocess.run(['git', '-C', ROOT, 'show', '-s', '--format=%ad', '--date=format:%Y-%m-%d %H:%M', h],
                          capture_output=True, text=True, check=True).stdout.strip()


# ------------------------------------------------------------------------- the 22 October ledger (lines 1-50)
def r03_lines():
    tree = ast.parse(open(os.path.join(ROOT, R03), encoding='utf-8').read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'L' for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit('r03 has no ledger list')


# the first finder of each 22 October line, in the routes of this taxonomy (its found_by column, read by hand)
OLD_ROUTE = {1: 'old system', 2: 'outside review', 3: 'outside review', 4: 'old system', 5: 'operator',
             6: 'code check', 7: 'code check', 8: 'code check', 9: 'verifier', 10: 'audit', 11: 'code check',
             12: 'code check', 13: 'reviewer', 14: 'operator', 15: 'code check', 16: 'operator', 17: 'reviewer',
             18: 'owner', 19: 'reviewer', 20: 'operator', 21: 'code check', 22: 'operator', 23: 'audit', 24: 'audit',
             25: 'sweep', 26: 'sweep', 27: 'code check', 28: 'code check', 29: 'audit', 30: 'operator', 31: 'code check',
             32: 'code check', 33: 'code check', 34: 'operator', 35: 'code check', 36: 'operator', 37: 'audit',
             38: 'database check', 39: 'code check', 40: 'operator', 41: 'operator', 42: 'code check', 43: 'operator',
             44: 'audit', 45: 'operator', 46: 'code check', 47: 'database check', 48: 'sweep', 49: 'outside review',
             50: 'outside review'}
# Independent check of 2 November (TAXONOMY_CHECK.md): line 1 is Codex's review of the OLD catalogue's certified rows,
# the source of RA1's and RA2's inheritance, so its route is 'old system' like line 4's (it had counted as a v2
# finding of RA1 and RA2). The 50 lines stay as the 22 October ledger has them; these notes record what the check found.
OLD_NOTES = {
    1: "check 2 Nov: Codex's cases come from the old catalogue's certified rows (OLD_CATLOG_ASSESSMENT_20261007.md), "
       "the inheritance of RA1 and RA2, not a finding in v2",
    5: 'check 2 Nov: also a v2 finding of RA5 (a ± the reader dropped made code reject the whole value)',
    18: 'check 2 Nov: the 85 recovered at 18:53 were 77 ratio-only verifier rejections, 6 pH-column values of 18783250 '
        'and 2 split decimals (27ad550); the 36 values code had rejected for the ratio came back at 18:05: 113 by the '
        'ratio rule',
    21: 'check 2 Nov: two failures, split: re-read copies (IP3) and the looser twin rule that merged different '
        'measurements (IP5)',
    47: 'check 2 Nov: audits and the database check found 15659684, 42228390 and 25022854 on 19 Oct (log.tsv unitfix); '
        '20 Oct is the scale sweep',
}


# ------------------------------------------------------------------- new ledger lines (21 October - 2 November)
# key, date, kind, route, found_by, failure, rows, rule, evidence [(source, quote)], note
def N(key, date, kind, route, found_by, failure, rows, rule, ev, note=''):
    return dict(key=key, date=date, kind=kind, route=route, found_by=found_by, failure=failure, rows=rows, rule=rule,
                ev=ev, note=note)


MISSED = 'missed by the 22 October ledger'
NEW = [
    N('writers', '2026-10-08', 'PROC', 'operator', 'operator (edge-case sweep of the code)',
      'two writers at once (drop and add) lost catalogue rows', 'not counted',
      'code: a lock on the catalogue side file; a cut-off last line is repaired before the next write',
      [('git:099673a', 'catalog side-file lock (drop vs add lost rows)'), ('git:099673a', 'cut-off line repair'),
       ('CLAUDE.md', 'One writer at a time: `add` and `drop` hold `catalog.jsonl.lock`')], MISSED),
    N('abbrev', '2026-10-10', 'FA', 'operator', 'operator (check-up)',
      'abbreviations resolved through the peptide and PubChem routes gave wrong structures', 'Z-GGPP, BAA, DMOG, ETF',
      'code: the abbreviation guard covers the peptide and PubChem routes',
      [('git:78e1be4', 'abbreviation guard covers peptide and PubChem routes (Z-GGPP, BAA, DMOG, ETF were wrong structures')],
      MISSED),
    N('review2', '2026-10-11', 'FA', 'reviewer', 'human review, round two',
      'a UniProt EC hit unrelated to the enzyme name gave the wrong protein; a metal complex drawn in pieces got a structure',
      'lung PGFS had AKR1A1; ferrocenium was cyclopentadiene',
      'code: such EC hits are not used; a metal complex drawn in pieces gets no structure',
      [('git:f8c50f1', "UniProt EC hits unrelated to the enzyme's name are not used (lung PGFS had AKR1A1)"),
       ('git:f8c50f1', 'metal complexes drawn in pieces get no structure (ferrocenium was cyclopentadiene)')], MISSED),
    N('mass', '2026-10-12', 'FR', 'operator', "operator (open item of 12 Oct), then the owner's decision",
      'a Km printed over a mass concentration (polymer substrates) was rejected as an unknown unit',
      'about 100 values in 12 papers (12 Oct)',
      'code: units.MASS_UNIT keeps such a Km in mg/mL and its kcat/Km in mL mg^-1 s^-1, in their own columns',
      [('gitfile:8d28860:CLAUDE.md', 'are rejected as unknown units (about 100 values in 12 papers on 2026-10-12)'),
       ('tools/units.py', 'until then they were rejected as unknown units'),
       ('git:66d9143', 'Keep Km over a mass concentration (mg/mL) and its kcat/Km (mL mg^-1 s^-1) in their own units and export columns'),
       ('CLAUDE.md', '(the user, 2026-10-12; `units.MASS_UNIT`)')], MISSED),
    N('pasted', '2026-10-13', 'FA', 'operator', 'operator (database-check records)',
      "a correction row pasted from another paper's value turned a confirmed value into a correction with that paper's "
      'evidence; a spreadsheet date made a row lose to an older one', 'not counted',
      "code: a recorded row whose PMID is not its value's paper, or whose number the database does not list, is listed "
      'and not used; dates must be YYYY-MM-DD',
      [('git:16948c4', "a row_id pasted from another paper's value had turned a confirmed value into a correction with the other paper's evidence"),
       ('git:00f1977', "a row whose date is not YYYY-MM-DD (a spreadsheet's 10/13/2026, or none) is listed and not used")],
      MISSED),
    N('caret', '2026-10-14', 'FR', 'code check', 'code check (rejects)',
      "a caret multiplier in a mass-concentration unit ('ml/mg/min [10^-2]') was rejected",
      '5 kcat/Km of 36698977 recovered', 'code: the caret multiplier converts',
      [('git:df7392d', "a caret multiplier in a mass-concentration unit ('ml/mg/min [10^-2]') converts instead of rejecting (PMID 36698977, 5 kcat/Km recovered)")],
      MISSED),
    N('evflags', '2026-10-14', 'FA', 'operator', 'operator (database-check records)',
      "a database-check agent's evidence named numbers the paper does not print", 'not counted',
      'code: dbcheck-record flags such evidence (evidence_flags=); dbcheck.md: corrected only when a printed fact decides',
      [('git:3d917ef', 'dbcheck-record flags evidence the paper does not show'),
       ('git:93eb834', 'corrected only when a fact the paper prints decides it'),
       ('CLAUDE.md', 'is listed and logged `evidence_flags=`, not refused')], MISSED),
    N('dblabels', '2026-10-15', 'PROC', 'database check', 'database check',
      'database labels worded otherwise (metal ions, a typo) made the comparison refuse a valid check as another '
      'measurement', '16990279, 30054521, 2819035',
      "code: dbcompare reads divalent and monovalent ions under one name, and BRENDA's 'phospahte' as phosphate",
      [('git:07e2c9b', 'divalent metal ions under one name'), ('git:77aeb35', 'monovalent cations under one name too'),
       ('git:2f61fac', "read BRENDA's 'phospahte' as phosphate")], MISSED),
    N('copyrow', '2026-10-16', 'FA', 'sweep', 'reprint sweep (side find)',
      "a table row printed under another row's label: 20635860's West Nile virus M line carries the Yellow Fever M cells",
      '6 values dropped on 23 October', 'drop for a named reason after a check against the paper; no general rule',
      [('CLAUDE.md', 'Side find: 20635860 Table 1 prints the West Nile virus M row as a cell-for-cell copy of the Yellow Fever M'),
       ('git:9502fb0', '6 values dropped as the copied Table 1 row')], MISSED),
    N('quotesym', '2026-10-18', 'FA', 'operator', 'operator (record pages)',
      "the quote shown with a value carried the code points a PDF text layer moves symbols to (JBC fonts' ±, ×, −, µ), "
      "or an ordinary character for ± ('66.7 f 8.3', 22 October)", 'not counted',
      "code: the printed line shows the paper's symbols; a line that still lost symbols says so in printed_line_note",
      [('git:4798de4', 'The printed line and cell a record quotes show the symbols a PDF text layer moved to other code points'),
       ('git:9e0cb80', "A printed line whose PDF text layer gives ± as an ordinary character ('66.7 f 8.3'")], MISSED),
    N('refvotes', '2026-10-20', 'PROC', 'operator', 'operator',
      "a sweep's refuters wrote remarks into the wrong field, were retried on another model and their votes dropped",
      '9 rows of 15797234 listed as not surviving although no refuter refuted them',
      "workflow: catlog-scale counts a refuter's vote whenever it returns rows; remarks go to note",
      [('git:18d5833', "two 15797234 refuters had written remarks into 'problem', were retried on Sonnet and their votes dropped"),
       ('git:18d5833', 'listed 9 rows as not surviving although all 5 refuter results refuted none')], MISSED),
    N('auditreprint', '2026-10-21', 'FA', 'audit', 'audit (17465518), then 3 judges',
      "a reprinted row: 17465518's Table 1 YbbR13/Sfp cells repeat the same lab's 2005 measurement (16236721)",
      '3 values dropped', 'rules in force since 14 October; drop for a named reason',
      [('log.tsv', "repeat the same lab's earlier measurement in Yin et al. 2005 PNAS"),
       ('log.tsv', '3 of 3 independent judges (work/reprint_17465518.judge*.json)')]),
    N('stamps', '2026-10-21', 'PROC', 'outside review', 'outside review (publication review, item 10)',
      'stored values carried no record of the model, prompt and code that read them',
      '92.2% of the 240,169 values stored on 31 October were added before the stamps',
      'code: add stamps model IDs, prompt hashes and the commit; tools/provenance_backfill.py reconstructs earlier rows '
      'from the agents\' transcripts and git',
      [('git:76a824c', 'so every value records what read it'),
       ('git:4523db0', 'reconstructs the reader and verifier model ids, prompt hashes and commit of rows added before stamping from evidence only'),
       ('paper/manuscript/methods_main.md', '92.2% before the provenance stamps (21 October)'),
       (FIX22, 'Item 10, provenance: each new row records reader/verifier model IDs, prompt hashes and the code commit')]),
    N('base', '2026-10-21', 'PROC', 'outside review', 'outside review (publication review, items 1-8)',
      'the quality numbers counted over the wrong base: whole-paper follow-up audits inside the random audit rate; '
      'checking agents counted as reading agents', '173 reader and 130 checker-only exposed papers counted as one',
      'code: catlog.FOLLOWUP_AUDITS; audit-record --followup lines (targeted=paper) stay out of the rate; the site '
      'says who checked what over which base',
      [('git:9eef7ca', 'The audit rate and its 95% interval count the random audit only'),
       ('git:c11505b', "The website's quality numbers say who checked what and over which base"),
       (FIX22, 'counts verifiers too. A reader opened such files on 173 papers; only a verifier did on 130')]),
    N('model', '2026-10-22', 'PROC', 'operator', "operator (provenance backfill from the agents' transcripts)",
      "an agent's model fell back mid-run (claude-opus-5-5 to claude-opus-5) while its own work file named only the first",
      '112 of 599 agents of 29 October-1 November; at least 1,056 reader and 1,290 verifier stamps in 81 papers hide a switch',
      "code: the backfill names every model an agent used (22 October); add reads the model from the agent's "
      "transcript, 'A>B' (1 November)",
      [('git:7f63a56', "('claude-opus-5-5>claude-opus-5' for a fallback mid-run)"),
       ('git:23af857', "112 of 599 agents of this chat's batches switched claude-opus-5-5 > claude-opus-5 while their work files named claude-opus-5-5"),
       (REPLY, 'at least 1,056 reader and 1,290 verifier stamps in 81 papers hide a switch')]),
    N('scratch', '2026-10-22', 'PROC', 'operator', 'operator (provenance backfill)',
      "parallel agents shared their chat's scratch folder: the reader of 1857377 ran build.py and rewrote 17692452's "
      'read file (9 October)', '1 paper', 'workflow: every agent keeps its scratch files in a folder named by its role and paper',
      [('git:5aad090', "a reader once ran another paper's build.py there and rewrote that paper's read file (17692452)"),
       ('git:dca7da3', 'and parallel agents get their own scratch folder'),
       ('.claude/workflows/catlog-batch.js', 'on 2026-10-09 the reader of 1857377 ran build.py after the reader of')]),
    N('blindreprint', '2026-10-22', 'FA', 'audit', 'audit (blind re-read of the 303 exposed papers, two auditors agreeing)',
      'earlier reads had stored reprinted wild-type or reference rows (14 papers named)',
      'mostly reprints among the 73 values dropped', 'rules in force since 14 October; recorded with audit-record --followup',
      [(BLIND, 'The drops were mostly reprinted values (a wild-type or reference row copied from an earlier paper'),
       (BLIND, 'Earlier values found wrong: 122 of 17,380 (0.7%): 49 corrected (unit misprints the paper itself shows), 73 dropped.')]),
    N('blindvariant', '2026-10-22', 'FA', 'audit', 'audit (blind re-read, follow-up)',
      "wrong variant or form labels: 1537854's values belong to the S115A,Q255Term double mutant, 'P98S' is not a "
      "mutant 1939081 studied, a value of 15639226 belongs to its TyrHpS31 form", '8 values dropped',
      'rules in force; drop for a named reason',
      [(BLIND, 'wrong variant labels (1537854, 1939081)'),
       ('log.tsv', 'the measured enzyme is the S115A,Q255Term double mutant, not the S115A single mutant stored'),
       ('log.tsv', "wrong variant: 'P98S' is not a mutant this paper studied"),
       ('log.tsv', "wrong enzyme form: 43 +/- 10 is the last column of Table 1's TyrHpS31 line")]),
    N('blindpartial', '2026-10-22', 'FA', 'audit', 'audit (blind re-read, follow-up)',
      "per-cleavage-site partial constants stored as the peptide's kcat and kcat/Km (19819898)", 'see the count by script',
      'rules in force since 13 October',
      [(BLIND, 'per-cleavage-site partial constants (19819898)'),
       ('log.tsv', "partial constant: per-cleavage-site (per-product) kcat, not the peptide's kcat")]),
    N('blindunit', '2026-10-22', 'FA', 'database check', 'blind re-read (conflicts judged from the paper, 3 refuters each)',
      'unit misprints the paper itself shows, read as printed (21306440, 25577102, 36394293)', '49 values unit-corrected',
      'unitfix (rules in force)',
      [(BLIND, 'The 49 changes are unitfix lines in log.tsv: 21306440 Table 2')]),
    N('blinddups', '2026-10-22', 'FA', 'operator', 'operator (blind re-read)',
      're-read copies of accepted values whose raw unit was spelled otherwise, whose quote carried other labels, or whose '
      'substrate spelled out a Greek letter', '2,404 copies dropped, each checked against its paper',
      'code: add recognises such copies, pairing each accepted row once',
      [('git:6dde5fa', "add recognises a re-read's copy of an accepted value whose raw unit is spelled otherwise"),
       (BLIND, '2,404 such copies')]),
    N('rawunit', '2026-10-22', 'FR', 'outside review', 'outside review (head-to-head with the Co-Scientist gold set)',
      'code refused values whose column prints no unit although the verifier gave the unit to convert with '
      '(missing:raw_unit)', '25 confirmed kcat/Km values of 23946505 (gold has all 25); 310 values in 24 papers recovered '
      'on 23 October', 'code: check() lets unit_for_conversion stand in for an empty raw_unit',
      [(FIX22, 'This lost 25 confirmed kcat/Km values in 23946505; gold has all 25'),
       ('git:bdab76f', '310 values in 24 papers whose kcat/Km or Km column header prints no unit are recovered'),
       ('catlog.py', '23946505 lost 25 confirmed kcat/Km values to missing:raw_unit, 2026-10-22')]),
    N('h2hpartial', '2026-10-22', 'FA', 'outside review', 'outside review (head-to-head with the gold set)',
      'per-product partial constants read before the 13 October rule (30730705, 15056909)',
      '227 values dropped in 4 papers on 23 October; a scan of 47 earlier papers found no others',
      'drop --file after a check against each paper, confirmed independently',
      [(FIX22, '30730705 (98 rows) and 15056909 (78 rows) store'),
       ('git:9ccda49', '227 per-product partial constants dropped'),
       ('git:9ccda49', 'a scan of the 47 pre-2026-10-13 papers whose rows name a product or site found no others')]),
    N('formseq', '2026-10-22', 'FA', 'outside review', 'outside review (top-journal check, item 5)',
      'natural forms sharing one UniProt accession carried the same canonical sequence',
      'SHV-1 vs SHV-14, VPL vs VPL2, AKR1C4 vs DD4, NRDRB1 vs NRDR',
      'code: a checked natural-form line drives the sequence guard (23 October); DD3 and DD4 lose a sequence that is '
      'not theirs (24 October)',
      [(FIX22, 'Identity conflations on one UniProt accession (both rows wild type)'),
       ('git:9f9c1fe', 'no longer carry the canonical sequence of the accession they share with another form'),
       ('git:15e9f2c', "3276326's DD3 and DD4 (one EC-only entry) lose a sequence that is not theirs")]),
    N('vmax', '2026-10-22', 'FA', 'outside review', 'outside review (top-journal check, item 3), then the Vmax sweep',
      "a stored kcat that disagrees with the paper's own printed Vmax, in tables with no printed kcat/Km to close",
      '186 papers flagged; of the 22 near a unit factor: 2 header misprints (12435510: 12 values, 16984804: 8), 1 cell '
      'slip (21443518), 3 papers disagreeing with themselves, 15 false positives',
      'tools/vmax_sweep.py, prompts/vmax.md and the workflow catlog-vmax (one blind agent per paper, 3 refuters per change)',
      [(FIX22, "Cheap flag: kcat vs the paper's own Vmax."),
       ('git:d5812ab', 'it finds the four papers item 3 names and 186 in all'),
       ('git:29c58b0', '2 header misprints, 1 cell slip, 3 papers disagreeing with themselves, 1 per-multimer kcat and 15 false positives of the sweep'),
       ('git:8d01c44', "21443518's '505215 s-1' dropped as a cell slip")]),
    N('tail', '2026-10-22', 'FA', 'outside review', 'outside review (top-journal check, items 1-2)',
      'kcat/Km values impossible as printed (beyond the diffusion limit) carried no flag, and a derived kcat/Km had no '
      'physical limit', '103 values at 1e9 M^-1 s^-1 or more: 0 misreads, 89 in 20 papers impossible as printed',
      'code: export flags a derived kcat/Km above the limit (23 October); sources/implausible_as_printed.tsv puts each '
      'reviewed reason in kcat_over_km_flag (24 October)',
      [(FIX22, "Of CatLog's 103 kcat/Km values at 1e9 M^-1 s^-1 or more, 0 are misreads"),
       (FIX22, '89 values in 20 papers are impossible as printed'),
       ('git:224eccc', 'export flags a derived kcat/Km above the physical limit'),
       ('git:1e35c79', '101 lines, 11779198 by 2 independent agents')]),
    N('dbverdict', '2026-10-22', 'FA', 'outside review', 'outside review (top-journal check, item 4)',
      "database-check verdicts were wrong: 19211556's cause recorded as unit_not_converted where CatLog and BRENDA "
      "differ by 1e6; 25016016's row called catlog_wrong though BRENDA's own kcat/Km puts the database's number 1000x low",
      '8 rows (19211556), 1 row (25016016)',
      "code: dbdiff --reask asks a paper's recorded corrections again; a catlog_wrong row an audit kept reopens by itself",
      [(FIX22, "is marked catlog_wrong, but BRENDA's own kcat/Km puts the database's 0.042"),
       ('git:be2fb3a', "for 19211556's 8 rows recorded unit_not_converted where CatLog and BRENDA differ by 1e6")]),
    N('censored', '2026-10-22', 'FR', 'outside review', 'outside review (top-journal check, item 7)',
      'values printed only as a bound or as not detected were never recorded: the first reader prompt skipped them',
      '0 bounds among 221,797 values; 689 of 2,674 papers with mutant and wild-type pairs report a variant with no '
      'measurable activity (an upper bound)',
      'prompts: Censored values (read.md, verify.md rule 9); code: bounds.jsonl, the catlog_bounds export, recheck; a '
      'censored-only pass over earlier papers (24 October)',
      [(FIX22, 'Of 221,797 values, 0 are bounds'),
       (FIX22, '689 of the 2,674 papers with mutant and wild-type pairs (25.8%, an upper bound from a phrase scan)'),
       ('git:47eafb8', 'a kcat, Km or kcat/Km printed only as a bound or as not detected is read (prompts), verified, kept in bounds.jsonl apart from the numeric catalog'),
       ('gitfile:f171ab3:prompts/read.md', 'Ranges (`5–10`), lower/upper bounds (`>100`, `<0.1`), "ND", "n.d.", "—": skip.')]),
    N('auditcut', '2026-10-23', 'FA', 'operator', 'operator (an audit of 21094652)',
      "audit-record cut an auditor's spaced unit fix to its first word and logged a fix that did not apply as corrected",
      "21094652's Table 3 rows",
      'code: audit-record takes the shortest leading words the units code accepts; a fix that did not apply stays unrecorded',
      [('git:1b499b3', "(a spaced unit such as '10^-6 M^-1 s^-1' was cut to '10^-6')"),
       ('git:1b499b3', 'leaves a fix that did not apply unrecorded instead of logging it corrected')]),
    N('nM', '2026-10-23', 'FA', 'database check', 'database check, then audit (21094652)',
      'a kcat/Km column computed with Km taken as nM: every row 10^6 above kcat ÷ Km', '9 values unit-corrected',
      "unitfix from the paper's own numbers (rules in force)",
      [('log.tsv', 'so the whole column is 10^6 too high'),
       ('log.tsv', '2026-10-23 05:06 21094652 dbcheck corrected=0')]),
    N('signal', '2026-10-24', 'FA', 'operator', 'operator (sequence check; who noticed first is not recorded)',
      'a construct stated without its signal peptide kept the precursor sequence', '1,250 records of 109 papers',
      "code: the mature chain from the printed start residue, else after UniProt's signal or transit span; blank with "
      'the reason when UniProt marks none',
      [('CLAUDE.md', '1,250 records of 109 papers had kept the precursor'),
       ('git:15e9f2c', 'A construct stated without its signal peptide gets the mature chain')]),
    N('gg', '2026-10-25', 'FR', 'code check', 'code check (a rejected bound)',
      'a bound printed with a much-less or much-greater sign (≪, ≫) was rejected as a sign mismatch',
      "18669639's Km '≫12' (1 value recovered)", 'code: ≪ and ≫ are bounds of that kind',
      [('git:5d2fd88', "(18669639's Km '≫12' was rejected as a sign mismatch; recovered)")]),
    N('ec', '2026-10-25', 'FA', 'operator', "operator (the website's EC filter)",
      "an EC number printed with its prefix or incomplete ('EC1.1.3.10', '3.4.11', '1.14.13.x') kept records out of EC lookups",
      "39915905's records", 'code: clean_ec in export and enrich',
      [('git:8d18a62', "39915905's 'EC1.1.3.10' kept the site's EC filter from finding its records"),
       ('catlog.py', 'def clean_ec(text):')]),
    N('nd', '2026-10-26', 'FA', 'operator', "operator (a paper check of stored not-detected values, built with the site's not-detected view)",
      'a constant the paper could not determine although the enzyme was active (no saturation, a very high Km) stored as '
      'not detected; a printed limit of another quantity stored as the bound',
      '715 values with such a cue in 81 papers checked by two blind agents each: 59 removed, 38 limits cleared',
      "prompts: read.md 'Not detected means no activity', verify.md rule 9; code: limitfix",
      [('CLAUDE.md', '715 in 81 papers, two blind agents each, a third on disagreements; work/nd_check/) removed 59'),
       ('CLAUDE.md', 'and cleared 38 limits that bounded another quantity'),
       ('git:85553bf', 'Not detected means no activity, never a constant the paper could not determine although the enzyme was active'),
       ('git:4d2daa1', 'a Km not detected has its own meaning (no activity to measure it, not a small Km)'),
       ('prompts/read.md', '(12654910, 18222180, 42575440 were stored wrongly this way, 2026-10-26)'),
       ('path:work/nd_check', '')]),
    N('monitor', '2026-10-26', 'PROC', 'operator', 'operator (a review of the exposure monitor\'s flags)',
      'the transcript monitor counted a file named only to leave it out (grep -v) as opened, and missed the human_review '
      'folder named without its slash',
      '6 false alarms removed (papers exposed 310 to 307); 1 past case found (7011386); a full rescan on 28 October '
      'added 15 exposure lines (13 papers already re-read blind)',
      'code: blind_check rules; human_review/exposed.tsv corrected',
      [('git:d6f143d', 'a file named only to leave it out (grep -v pattern'),
       ('git:06f2615', 'remove 6 false alarms the new blind_check rule clears'),
       ('git:06f2615', 'papers exposed 310 -> 307'),
       ('git:473e343', 'blind_check also flags the human_review folder named without its slash'),
       ('git:31ff239', 'full rescan before archiving transcripts added 15 exposure lines (13 papers already re-read blind)')]),
    N('alias', '2026-10-26', 'FR', 'reviewer', "reviewer (the website chat's item 1), then a review of the fix",
      'a paper that names no organism, or an alias (KPC-2, LDH-M), leaves its records with no protein; a name search '
      'matched entries that merely mention a token', 'the 70 records shown as EC Unknown (KPC-2)',
      'OPEN: the name-search fix was reverted after review; a strict gene-name rule fixes neither example',
      [('CLAUDE.md', 'OPEN: records whose paper names no organism, or uses an alias name, get no UniProt or EC (KPC-2, human LDH-M/LDH-H;'),
       ('CLAUDE.md', '(a strain named after VIM-2 gave an aldolase'),
       ('CLAUDE.md', 'fill the 70 records the site shows as EC Unknown'),
       ('git:dceb96f', 'a strict name-to-UniProt rule fixes neither KPC-2 nor human LDH (measured)')]),
    N('calcbound', '2026-10-27', 'FA', 'owner', 'owner (the website)',
      'export derived a kcat/Km from kcat ÷ Km where the paper prints that kcat/Km only as a bound or as not detected',
      "10390216 aztreonam: 33 'calc.' beside '<0.02 µM^-1 s^-1'",
      'code: export does not derive it there; recheck flags any such record',
      [('git:4767cad', "10390216 aztreonam showed 33 calc. beside '<0.02 µM^-1 s^-1'"),
       ('CLAUDE.md', 'never where the paper prints that kcat/Km as a bound or not detected (the user, 2026-10-27; recheck checks it)')]),
    N('k05', '2026-10-27', 'FA', 'audit', 'audit (26142822)',
      "a cooperative enzyme's half-saturation constant (Hill n = 1.5) stored as Km", '1 value dropped', 'rules in force',
      [('log.tsv', 'Wrong metric. The paper calls Asn deamidation by L-ASP cooperative (Hill n = 1.5 ± 0.1')]),
    N('ndscan', '2026-10-27', 'FR', 'audit', 'audit (completeness audit of 16166087)',
      "the censored-value scan's phrases missed plain wording ('was inactive') and ND cells in PDF tables",
      'a whole-paper check found one in 14 of 36 sampled papers with no such wording, and in 14 of 45 judged no',
      'agents judge snippets around wider wordings and the papers they find join the list; OPEN: a whole-paper check of '
      'the papers judged no',
      [('git:ad19399', "papers an agent found a not-detected result in that the phrases miss ('was inactive', ND cells in PDF tables)"),
       ('CLAUDE.md', "16166087's \"the purified K46A mutant protein was inactive\" matched no phrase"),
       ('CLAUDE.md', 'a whole-paper check found one in 14 of 36 sampled papers with no such wording, and in 14 of 45 judged no'),
       ('CLAUDE.md', 'Not done: a whole-paper check (~25k tokens a paper')]),
    N('pm8', '2026-10-17', 'FA', 'database check',
      "database check (21757926's verdict names the glyph), then the case-study check (28 Oct) and the kill-test kit "
      "(31 Oct: the warning's table lacks it)",
      "± drawn as '8' in a PDF text layer, a glyph the warning's table did not know: Table 1's 6 ± 1.5 reads 681.5",
      '64 texts with 3+ two-decimal-point tokens holding an 8 (53 without a warning, 16 of those done); 42 texts rebuilt '
      'with the new warning; 133 stored values from such tokens checked on page images, all right',
      'code: fetch.two_points warns on numbers with two decimal points (1 November)',
      [(FIX31, "`GLYPH_SIGNS` in `tools/fetch.py` (line 334) knows ± as '6' and ° as '8', but not ± as '8'"),
       (FIX31, 'found 64 with three or more two-decimal-point tokens containing an 8. 53 of them have no GLYPH WARNING, and 16 of those 53 are already `done`'),
       ('git:768e645', '42 texts rebuilt'),
       ('git:768e645', 'A blind page-image check of the 133 values readers had split from such tokens in 7 done papers found all right'),
       (TRACKER, '| N5 | 21757926 | database checks |'),
       ('log.tsv', '2026-10-17 07:25 21757926 dbcheck corrected=1'),
       ('sources/database_corrections.tsv', 'the PDF text layer prints the ± as 8 (681.5)'),
       ('tools/fetch.py', 'def two_points(text):')], MISSED),
    N('break', '2026-10-29', 'FR', 'code check', 'code check (8 values of 40454099 rejected)',
      "CatLog's own JATS converter ran a cell's stacked values together (<break/>)",
      '125 texts rebuilt; the 12 done papers among them re-read: 23 values added, no conflict, 12 of them copies of '
      'values the first reads had stored (check of 2 Nov), so 11 recovered',
      'code: jats_to_text writes a space for a <break/> inside a cell',
      [('git:81f7945', 'a <break/> inside a table cell becomes a space (stacked values had run together, 40454099); 125 texts rebuilt, 12 done papers back to todo'),
       ('git:2ef96dd', '23 values recovered, no conflicts'),
       ('log.tsv', '2026-10-29 07:47 40454099 add kept=4 dup=0 rejected=8'),
       ('CLAUDE.md', 'the merge lost values, it did not corrupt them'),
       ('tools/jats_to_text.py', 'a line break inside a cell stacks two values')]),
    N('pmfix', '2026-10-22', 'FA', 'audit', 'audit (blind re-read follow-up: 17462992), then two blind checks of every such row (30 October)',
      "values stored before the 9 October rule still carried a neighbouring cell's ±",
      '1 value dropped (17462992); 11 values corrected on 30 October (pmfix)',
      'code: pmfix takes off a ± the printed cell does not carry',
      [('log.tsv', 'raw_value carries a ± the cell does not print'),
       ('git:70394a4', "take off a ± the printed cell does not carry (code filled a neighbour's before 495383e)"),
       ('git:a24849f', "11 values lose a neighbour's ± (pmfix)")]),
    N('dups1030', '2026-10-30', 'FA', 'operator', 'operator',
      're-read copies stored before the 22 October rule (unit or wording typed otherwise)', '110 copies dropped, checked against the papers',
      'drop for a named reason (the rule has been in force since 22 October)',
      [('git:a24849f', '110 re-read copies dropped; both checked against the papers'),
       ('log.tsv', 'a re-read before the 2026-10-22 twin rule kept it because the unit or wording was typed otherwise')]),
    N('unitremark', '2026-10-30', 'FA', 'operator', 'operator (review packs)',
      'readers wrote remarks into the unit field when the paper prints no unit', 'not counted',
      'read.md: raw_unit holds the unit only; the reason for a unit the paper does not print goes in metric_note',
      [('git:70394a4', 'raw_unit holds the unit only, a no-printed-unit reason goes in metric_note'),
       ('git:70f4a4b', "a reader's remark inside a printed unit"),
       ('prompts/read.md', 'The unit only, never a remark')]),
    N('implaus', '2026-10-31', 'FR', 'outside review', "outside review (the check of case box 2: 36756200's Figure 7D)",
      'a verifier rejected values only for a physically implausible scale that the paper prints twice',
      '22 values rejected on 12 October; 20 back as printed with review lines on 31 October',
      "verify.md rule 3: an implausible scale is by itself no reason to reject or rescale; the paper's own numbers decide",
      [('git:c005e33', 'a physically implausible scale is by itself no reason to reject or rescale'),
       ('git:b41b8ef', "36756200's Table S4/S5 values back as printed (recover, 20 of 22)"),
       ('prompts/verify.md', 'whose verifier rejected 22 such values on 2026-10-12, 20 back since 2026-10-31'),
       (BOXES, 'Figure 7D plots this kcat/Km scale too')]),
    N('holdout', '2026-10-31', 'PROC', 'outside review', 'outside review (the kill-test kit for the method paper)',
      "the method paper's held-out test papers were being read, audited and swept by the development loop",
      '20 of the 374 read since 22 October; 369 locked',
      'code: sources/holdout_locked.txt, read by catlog.locked(): next, the censored pass, sample, dbdiff, the sweeps '
      'and review packs leave them out',
      [(FIX31, 'since 2026-10-22 the loop has finished 20 of them'),
       ('git:16d2764', "Hold out the method paper's test set (369 papers, sources/holdout_locked.txt)"),
       ('catlog.py', 'def locked():')]),
    N('override', '2026-11-02', 'FA', 'audit', 'audit (40723313)',
      "a verifier's unit override followed the Methods' unit definition against the paper's own table and abstract "
      "(kcat 3.35 s^-1 stored as 0.00335)", '4 values back to the printed unit',
      "rules in force (verify.md rule 3: the paper's own numbers decide); unitfix",
      [('log.tsv', "it comes from the verifier's unit_for_conversion override '10^-3 s-1'"),
       ('log.tsv', "only Methods 2.7's '1 nmol' unit definition disagrees, so the values stay as printed (verify.md rule 3)")]),
    N('root', '2026-10-31', 'PROC', 'outside review', 'outside review (the kill-test kit, FREEZE.md F2)',
      'the harness named the main folder, so a run from the freeze tag would read and write the development work/',
      '4 hard-coded places', 'workflow: catlog-batch and catlog-dbcheck take args.root',
      [(FIX31, "The main folder's path is hard-coded in four places"),
       ('git:03a9a3a', 'a run from a worktree at the freeze tag reads and writes its own work/')]),
    # ---- lines added by the independent check of 2 November (TAXONOMY_CHECK.md): failures in the git log, log.tsv or
    # the working notes that neither ledger had
    N('supp', '2026-10-07', 'FR', 'operator', 'operator (first library batch)',
      "values printed only in a paper's supplementary material were not in the text the reader got: 27342312's main "
      'text held 3 values, BRENDA cites 689 from its Supplemental Table S1',
      '689 values of 27342312; 266 papers waiting for a supplement on 2 Nov (status)',
      "read.md: needs_supplement; add marks the paper; catlog.py supp fetches open-access supplements, the download "
      'lane the rest; the paper is read again',
      [('CLAUDE.md', 'First seen on PMID 27342312 (BRENDA cites 689 values from its Supplemental Table S1)'),
       ('git:b11d975', 'Supplement path'),
       ('log.tsv', '2026-10-07 18:20 27342312 add kept=3'),
       (STATUS, '266 supplements')], MISSED),
    N('title', '2026-10-08', 'FR', 'operator', 'operator (edge-case sweep, then papers the title check refused)',
      "the title check turned away the right paper: a non-English paper's own title, '17beta' printed as 17β, an author "
      "manuscript's own title wording, OCR's 'rn' for 'm' (25183)",
      "not counted (25183's right PDF refused, 10 Oct)",
      "code: PubMed's English title and the original both pass; Greek letters spelled out; a JATS file naming the "
      "paper's PMID is that paper; 'rn' read as 'm'",
      [('git:099673a', 'non-English titles'),
       ('gitfile:099673a:CLAUDE.md', 'either passes the title check'),
       ('git:7cad51f', 'title check reads 17beta as 17β'),
       ('git:02b6c58', "(author manuscripts keep the authors' title wording)"),
       ('git:65eeba0', 'turned away the right PDF for 25183'),
       ('log.tsv', 'PMID25183_wiley.pdf title check failed')], MISSED),
    N('reviewcmp', '2026-10-09', 'PROC', 'operator', 'operator (comparison with the human review)',
      'the comparison with the human review paired records by name, so a substrate, isoform, gene or organism written '
      'another way counted as a disagreement or a value missing',
      'agreement 43% -> 61%, stated values found 20 -> 43 of 50 (9 Oct)',
      'code (review compare): substrates by structure, isoform and gene names, renamed genera, current accessions, '
      'organism binomials',
      [('git:be64c71', '(agreement 43% -> 61%, stated values found 20 -> 43 of 50)'),
       ('git:e0571e0', 'match substrates by structure'),
       ('git:ea13100', 'a gene name is not a mutation'),
       ('git:fbe63e7', "(10514444's human ADH4 Km had gone unmatched)")], MISSED),
    N('dbec', '2026-10-10', 'FA', 'reviewer', 'website review (second and third site checks)',
      "a database EC of another enzyme of the paper was given to an enzyme the paper prints no EC for (CPB, MMP-2/9, "
      "CelB, lipoamidase); BRENDA files 20549272's MMP-2 values under MMP-14's EC",
      '4 enzymes (10 Oct); 20549272, 26002966',
      "code (export database_ec): no database EC when another enzyme of the paper carries it and this one's values do "
      'not show it strongly; an EC that fits several EC-less enzymes of a paper whose values sit under two or more ECs '
      'goes to none',
      [('git:a1b9760', "(CPB, MMP-2/9, CelB, lipoamidase got siblings' ECs)"),
       ('git:702ad74', "BRENDA files 20549272's MMP-2 values under MMP-14's EC, swaps 26002966's AKR1C34/35")], MISSED),
    N('phblank', '2026-10-10', 'FR', 'operator', 'operator (check-up)',
      "a pH the code left empty (the OCR text does not print it readably) merged two slots, so 18783250's values of "
      'that pH column were refused as conflicts with the other column',
      '6 values of 18783250 recovered (10 Oct)', 'code: a blanked pH or temperature still separates slots',
      [('git:27ad550', 'a blanked pH/temperature still separates slots'),
       ('git:27ad550', '6 pH-8.3 column values'),
       ('log.tsv', '18783250 recover kept=6 dup=0 rejected=0 still_rejected=0 reason=conflicts with accepted row')],
      MISSED),
    N('recover', '2026-10-11', 'FA', 'operator', 'operator',
      "recover brought back two values a verifier had rejected for the ratio alone, without the unit fix the other "
      "rows of their column carry (22579392: header µM a misprint for mM; 16684501: a ×10^-5 header read the other way)",
      "2 values dropped (11 Oct); 16684501's came back with its unit through unitfix (12 Oct)",
      'none in code: recover re-checks a row only as add does',
      [('log.tsv', "recovered without its column's unit fix (header µM is a misprint for mM)"),
       ('log.tsv', "recovered without its column's unit fix (siblings read the header as 10^5 M^-1 s^-1); stored value "
                   'off by ~10^10'),
       ('git:16a5529', '2 misprint recoveries'),
       ('git:14d5288', '16684501 kcat/Km x1 back as 10^5 M-1 s-1')], MISSED),
    N('degree', '2026-10-11', 'FR', 'operator', 'operator (round-3 check-up)',
      "a PDF that prints the degree sign as 8 ('at 378') hid a printed 37 °C, so code left 20564561's temperatures empty",
      '66 values of 20564561 got their 37 °C back (11 Oct)', "code: check() reads 'at 378' as 37 °C, as it read '378C'",
      [('git:13c37e1', "'at 378' (the PDF prints the degree sign as 8) counts as 37 C"),
       ('log.tsv', '66 rows: 37 C restored (degree sign read as 8)')], MISSED),
    N('verdictlost', '2026-10-11', 'PROC', 'operator', 'operator',
      "two auditors' text replies lacked their verdicts, so their audits were lost", '2 audits (11 Oct)',
      'code: audit verdicts go to a file (work/audit_<row_id>.json) that catlog.py audit-record records',
      [('git:5054407', "where two auditors' text replies lacked their verdicts today")], MISSED),
    N('verdict13', '2026-10-13', 'FA', 'operator', 'operator (database-check records)',
      "paper-check verdicts named another measurement's database row or a cause the numbers do not support (17 rows of "
      '28085964 and 7758465; 16 of 25497345)', '33 recorded corrections re-checked against the papers (13 Oct)',
      'code: a recorded correction whose database row is labelled for another measurement, or whose cause the numbers '
      'do not support, is listed and not used',
      [('git:7272a97', "17 paper-check rows that named another measurement's row re-checked against the paper"),
       ('git:18b04ec', "25497345's 16 rows re-recorded")], MISSED),
    N('cmp', '2026-10-13', 'FA', 'operator', 'operator (reviews of the database-comparison patch)',
      "the database comparison misstated what a database lists: the wrong one of several numbers paired, a neighbouring "
      "row's number named, databases grouped that list different numbers, a database number called wrong where "
      "CatLog's own kcat, Km and kcat/Km do not close",
      "49 pairings in 16 papers; 8 lines; 21 of 3,721 'X lists N' statements; 9 kcat values of 30926626 (13 Oct)",
      "code (dbcompare): the number nearest the factor pairs; each database named with its own number; databases "
      "grouped only on the same printed number; no database number called wrong that closes CatLog's own numbers when "
      "CatLog's do not",
      [('git:8e81d55', '(49 pairings in 16 papers change'),
       ('git:4adda8f', '8 lines named a neighbouring row'),
       ('git:f3cd406', "(21 of 3,721 'X lists N' statements named a number X does not list"),
       ('git:3e25216', "code never calls a database number wrong that closes CatLog's own kcat, Km and kcat/Km when "
                       "CatLog's number does not (30926626: 9 kcat values corrected -> differs")], MISSED),
    N('swap', '2026-10-14', 'FA', 'operator', 'operator (database-check records)',
      "a database-check verdict whose row_id was swapped between two values of one paper passed and rewrote the other "
      "value's line", 'not counted',
      'code: dbcheck-record uses a verdict only when each database it names has that number for that row_id in the task',
      [('git:f7289ad', "(a row_id swapped between two values of one paper passed usable() and rewrote the other "
                       "value's line)")], MISSED),
    N('exactfactor', '2026-10-15', 'FA', 'operator', 'operator',
      "code stated a database correction from an exact unit factor alone, without the paper's own kcat ÷ Km "
      "supporting CatLog's number", 'not counted',
      "code (dbcompare): a correction only when the paper's own kcat ÷ Km supports CatLog's number; an exact factor "
      'alone stays a difference for the paper check',
      [('git:393b3b7', "code states a correction only when the paper's own kcat ÷ Km supports CatLog's number, so an "
                       'exact factor alone stays a difference')], MISSED),
    N('dupreport', '2026-10-19', 'FR', 'operator', 'operator',
      'the re-read duplicate report paired two variants that print the same number (19501264 Table 2: 1st B6 and 2nd '
      'C2 both 0.032)', 'not counted (a report; no value dropped on it)',
      'code: the report skips a quote that is only the printed cell',
      [('git:68ae85c', 'so it paired two variants that simply print the same number (19501264 Table 2: 1st B6 and 2nd '
                       'C2 both 0.032)')], MISSED),
    N('override42', '2026-10-19', 'FA', 'audit', 'audit (42228390), then the scale check of reader overrides',
      "a verifier's unit override replaced the wrong column of a misprinted table (42228390 Table 2)",
      "42228390's Table 2 unit-corrected (19 Oct)",
      'unitfix; the scale check reviews every table where a reader or verifier replaced a printed unit (catlog-scale)',
      [('CLAUDE.md', "42228390's verifier chose the wrong one"),
       ('paper/manuscript/supp_note_1_system.md', 'one earlier override, found by an audit (PMID 42228390), had '
                                                  'replaced the wrong column')], MISSED),
    N('model31', '2026-10-31', 'PROC', 'outside review', 'outside review (the kill-test kit, FREEZE.md)',
      'new rows still took the model their agent named in its own work file, which can differ from the model that ran '
      '(the reconstructed stamps: claude-opus-5 for 13,200 values, a switch mid-run for 28,875)', 'not counted',
      "code: add takes reader_model and verifier_model from the agent's transcript, 'A>B' for a switch (1 Nov)",
      [(FIX31, "An agent's self-reported model can differ from the model that actually ran."),
       (FIX31, 'show claude-opus-5 for 13,200 values and a mid-run switch'),
       ('git:23af857', "Model stamps from the agent's transcript at add")]),
    N('twice', '2026-11-02', 'FA', 'outside review', 'outside review (this taxonomy check)',
      're-read copies the duplicate rule does not pair are still in the catalogue: the substrate respelled (Na_2S for '
      'Na2S, a hyphen) or the quote taken from another text (an OCR read against the PDF, a sentence against the '
      'rebuilt table)',
      '{twice} values in {twice_papers} papers stored twice ({twice_by_paper})',
      'OPEN: for the main chat to check each pair against its paper and drop the copy',
      [(TWICE, 'Values stored twice: one printed cell, two catalog rows from two reads of the paper.')]),
]

# --------------------------------------------------------------------------------------------- failure classes
# ledger: 22 October line numbers (int) and new-line keys (str). novelty 'old system' = the failure was known from the
# old system's output and its rule was in v2's prompts or code by 8 October (inherited: the source that says so).
# first: (date, route, who) for a class with no ledger line. layers: every layer that guards it (guard_layer first).


def C(id, cls, origin, kind, example, guard, layers, values, status, ledger=(), novelty='new', inherited='', first=None,
      rule=None, ev=(), more=()):
    """more: findings with no ledger line of their own, [(date, route, who, [(source, quote), ...])] (added by the
    check of 2 November for agent cases and log records the ledger lines do not name)."""
    return dict(id=id, cls=cls, origin=origin, kind=kind, example=example, guard=guard, layers=list(layers),
                values=values, status=status, ledger=list(ledger), novelty=novelty, inherited=inherited, first=first,
                rule=rule, ev=list(ev), more=list(more))


OLDLESSON = ('CLAUDE.md', "They carry the old system's lessons: prove paper identity")
LESSONS_COMMIT = ('git:3c3e3c6', 'Old-system lessons:')
V = 'verifier prompt'
R = 'reader prompt'
CC = 'code check'
CV = 'code conversion'
DBC = 'database check'
AU = 'audit'
PE = 'people'

CLASSES = [
    # ======================================================================================== the printed paper
    C('PP1', 'Misprinted unit or exponent in a column header', 'the printed paper', 'FA',
      '25514023: Table 6 heads kcat "min-1"; Table 5 and the Results print the same cells in s-1',
      "verify.md rule 3: a header the paper itself shows is misprinted gets fix.unit_for_conversion (11 Oct), and a "
      "maximal rate printed for the pure enzyme decides (31 Oct); catlog.py unitfix corrects instead of dropping; "
      "tools/scale_sweep.py + workflow catlog-scale (kcat/Km closure off by a unit factor; blind check, 3 refuters); "
      "tools/vmax_sweep.py + catlog-vmax (kcat against Vmax x subunit mass / 60); a database difference CatLog loses "
      "goes to the next audit",
      [V, SWEEP, DBC, AU, CV],
      '{unitfix} values in {unitfix_papers} papers unit-corrected from the paper\'s own numbers, 12-23 Oct (log.tsv '
      'unitfix, less 15 restorations of the spaced exponent); 22 checked agent cases of this kind',
      'rule', ledger=[23, 38, 47, 'blindunit', 'vmax', 'nM'], rule='cb53ec3',
      ev=[('prompts/verify.md', "Exception: when the paper itself shows that a header's unit is a misprint"),
          ('prompts/verify.md', 'that puts every row of the column about one unit factor off is the misprint above'),
          ('CLAUDE.md', 'lists measurements whose printed kcat/Km misses kcat ÷ Km by a unit factor'),
          ('CLAUDE.md', 'kcat must sit near Vmax x subunit mass / 60'),
          ('tools/scale_sweep.py', 'A table whose unit header is misprinted stores a whole column off by an exact unit factor'),
          ('tools/vmax_sweep.py', 'kcat [s^-1] = Vmax [µmol min^-1 mg^-1] x M [kDa] / 60'),
          ('git:14d5288', 'catlog.py unitfix corrects a misprinted unit instead of dropping the value'),
          ('CLAUDE.md', 'catlog_wrong rows go to `work/audit_priority.txt`, which `sample` takes first'),
          (CASES, '| unit misprint | 22 | 0 | 10 |'),
          ('log.tsv', "Table 6 column header 'kcat (min-1)' is a misprint for the MSmB amidase data")]),
    C('PP2', "Earlier paper's values reprinted without credit", 'the printed paper', 'FA',
      "12591933: Table II's wild-type column repeats 11694539's Table III (22 of 26 values)",
      'read.md and verify.md rule 7: only values measured in this paper; a reference column identical to the cited '
      "paper's table is skipped (14 Oct); tools/reprint_pairs.py lists papers sharing printed cells, each pair checked "
      'cell by cell with an independent refuter and two more judges; audits',
      [R, V, SWEEP, AU],
      '1,502 reprinted values refused (461 by verifiers, 1,041 by audits and sweeps; refused-values table, snapshot '
      '28 Oct); the sweep dropped 973 rows in 80 papers and kept 165 its refuters refuted',
      'rule', ledger=[37, 'auditreprint', 'blindreprint'], novelty='old system',
      inherited='old system: "no reprinted values" is one of its lessons; 26519738\'s wild-type values were reprinted '
                'in an old certified row',
      rule='078ea59',
      ev=[OLDLESSON, ('CLAUDE.md', 'Hill/Ki/Kd/Vmax are not Km/kcat, no reprinted values'),
          (ASSESS, '26519738(WT values reprinted from an earlier study)'),
          ('prompts/read.md', 'A mutant-vs-wild-type table can carry the wild-type (or reference-enzyme) column over from an earlier paper'),
          ('prompts/verify.md', "compare the cells and reject a column identical to that paper's table"),
          ('tools/reprint_pairs.py', 'A paper can print an earlier paper\'s measurements again with nothing saying so'),
          ('CLAUDE.md', '973 rows in 80 papers dropped (`drop --file`), 165 refuted and kept'),
          (CASES, '| reprinted from an earlier paper | 1,502 | 461 | 1,041 |'),
          ('prompts/read.md', '(PMID 12591933 Table II against 11694539 Table III: 22 of 26 wild-type values')]),
    C('PP3', "A table row printed under another row's label", 'the printed paper', 'FA',
      '20635860: the West Nile virus M line carries the Yellow Fever M cells; only they fit its R column',
      "no rule: agents and sweeps catch it from the paper's own numbers, and the value is dropped for a named reason",
      [SWEEP, V],
      '6 values dropped (20635860); 8 checked agent cases of the kind "copy or mislabel inside the paper"',
      'open', ledger=['copyrow'],
      ev=[('log.tsv', "wrong table row: in Table 1 the West Nile virus M line (peptide 12) carries peptide 10's cells"),
          (CASES, '| copy or mislabel inside the paper | 8 | 1 | 6 |')]),
    C('PP4', "A lone cell's decimal point or digits slipped", 'the printed paper', 'FA',
      "21443518: kcat '505215 s-1' beside its own Vmax of 1065 U/mg would need a 28,000 kDa subunit",
      'verify.md rule 3: a cell a power of ten or more off its own row\'s printed rate is a slip and is rejected (31 Oct); '
      'the Vmax sweep finds such cells; code refuses values past its physical limits',
      [V, SWEEP, CC],
      '142 values refused as a misprint, copy slip or impossible number (77 by verifiers, 65 by audits and sweeps)',
      'rule', ledger=['vmax'], rule='c005e33',
      ev=[('prompts/verify.md', "one that puts a lone cell a power of ten or more off while the other rows agree is a slip"),
          ('log.tsv', 'wrong cell: a stored kcat the paper\'s own printed rate cannot allow'),
          (CASES, '| misprint, copy slip or impossible number | 142 | 77 | 65 |'),
          ('prompts/verify.md', 'which would need a 28,000 kDa subunit')]),
    C('PP5', 'Values physically impossible as printed', 'the printed paper', 'FA',
      "11779198: only the authors' reading of three kcat headers reproduces their own ΔG‡; 45 of its kcat/Km sit at or above 1e9 M^-1 s^-1",
      'code: add refuses a printed kcat/Km above 1e7 mM^-1 s^-1 (LIMITS); export flags a derived one above it (23 Oct); '
      'each value at or above 1e9 M^-1 s^-1 gets a reviewed line in sources/implausible_as_printed.tsv, carried as '
      'kcat_over_km_flag (24 Oct); recheck lists any not reviewed yet; values stay as printed',
      [CC, V],
      '101 review lines (none a CatLog misread); 47 derived values flagged (41 in 11779198)',
      'flag kept as printed', ledger=[50, 'tail'], rule='224eccc',
      ev=[('catlog.py', "LIMITS = {'kcat': 1e8, 'Km': 1e4, 'kcat/Km': 1e7}"),
          ('git:224eccc', '(47 values, 41 in 11779198)'),
          ('CLAUDE.md', 'a line in `sources/implausible_as_printed.tsv` (2026-10-24: 101, none a CatLog misread'),
          ('tools/recheck.py', 'not reviewed yet'),
          (CASES, 'Only kcat = cell × 10ⁿ reproduces them'),
          (CASES, 'flags the 45 kcat/Km at or above 10⁹ M⁻¹ s⁻¹')]),
    C('PP6', "The paper's own numbers disagree with each other", 'the printed paper', 'FR',
      '25824038: its Methods give the rates per minute, its abstract per second; nothing printed decides',
      'code: a printed kcat/Km that misses kcat ÷ Km drops nothing; all three are kept and the kcat/Km noted "differs '
      'from kcat ÷ Km by N×" (10 Oct); recover re-adds rows a changed rule no longer refuses; verify.md rule 3: the '
      "paper's own inconsistency is not a reason to reject",
      [CC, V],
      '85 values recovered (77 ratio-only verifier rejections); 3 papers left as printed by the Vmax check; 6 checked '
      'agent cases of this kind',
      'flag kept as printed', ledger=[5, 18, 'vmax'], rule='aa032a4',
      ev=[('CLAUDE.md', 'a printed kcat/Km that disagrees with kcat ÷ Km drops nothing: kcat, Km and the printed kcat/Km are kept'),
          ('prompts/verify.md', "the paper's own inconsistency is not a reason to reject"),
          ('CLAUDE.md', '3 papers print numbers that disagree with each other (25824038, 20695994, 42515788: left as printed)'),
          (CASES, '| paper contradicts itself | 6 | 0 | 2 |'),
          (CASES, 'so nothing printed decides')]),
    C('PP7', 'Values a retraction or corrigendum withdrew', 'the printed paper', 'FA',
      '25799411: a 2017 corrigendum re-assayed the C. glutamicum pyruvate kinetics; the verifier rejected the 6 values it replaces',
      "the verifier's own judgement; no prompt rule names retractions or corrigenda, and the 'use only this paper' rule "
      '(12 Oct) forbids fetching a notice the text does not hold',
      [V],
      '79 values refused as retracted or corrected by the authors (all by verifiers); 2 checked agent cases',
      'open', first=('2026-10-08', 'verifier', 'verifier (a retracted article, all 36 rows rejected)'),
      ev=[('gitfile:3c3e3c6:CLAUDE.md', 'One retracted article was caught by the verifier (all 36 rows rejected)'),
          (BOXES, 'A 2017 corrigendum replaced the paper\'s *C. glutamicum* pyruvate constants'),
          (BOXES, 'rejected the six values it replaces'),
          (BOXES, 'since 2026-10-12 they say to use only this paper'),
          (CASES, '| retracted or corrected by the authors | 79 | 79 | 0 |'),
          (CASES, '| retracted or corrected | 2 | 2 | 2 |')]),
    C('PP8', 'Measured protein differs from its label', 'the printed paper', 'FA',
      '19686854: Table 2 labels its rows wild type; the Methods report PCR-introduced Y378C and A134T in the only preparation',
      "the reader's own judgement; no rule covers mutations introduced by cloning",
      [R, V],
      '3 checked agent cases of this kind; the 8 values of 19686854 stored with their mutations',
      'open', first=('2026-10-29', 'reader', 'reader (19686854)'),
      ev=[(BOXES, 'Values labelled Ec6PGDH and Kp6PGDH were measured on mutants, not wild type'),
          (BOXES, 'none covers cloning mutations'),
          (BOXES, 'set Y378C on the four *E. coli* values, A134T on the four *K. pneumoniae*'),
          (CASES, '| measured-protein identity | 3 | 3 | 2 |')]),
    # =============================================================================== the PDF text layer or OCR
    C('TL1', 'µ drawn as m: a silent 1000-fold Km', 'the PDF text layer or OCR', 'FA',
      '2007114: the text layer heads the Km columns (mM), the page (µM); no warning fired and the reader read the page image',
      'code: fetch.glyph_warning puts a GLYPH WARNING on top of such a text, and readers and verifiers then take every '
      'number, ± and unit prefix from the page image; JBC small capitals (mm for mM) carry the flag '
      'printed_unit_prefix_differs',
      [CC, R, V],
      '15 of 120 sampled library PDFs; 384 values flagged printed_unit_prefix_differs',
      'rule', ledger=[4, 30], novelty='old system',
      inherited='old system: the glyph warning is listed among the "Old-system lessons" ported on 8 October',
      rule='3c3e3c6',
      ev=[LESSONS_COMMIT, ('git:3c3e3c6', 'glyph warning for PDFs whose text layer turns µ into m'),
          ('tools/fetch.py', 'def glyph_warning(path, text):'),
          ('prompts/read.md', 'If the text starts with `GLYPH WARNING`, this PDF\'s text layer replaces symbols'),
          ('prompts/verify.md', 'If the text starts with `GLYPH WARNING`, check every number'),
          (BOXES, 'Km columns: (µM) on the page, (mM) in the PDF text layer'),
          (BOXES, 'this one was not marked')]),
    C('TL2', '± drawn as a digit merges two numbers', 'the PDF text layer or OCR', 'FA',
      '21757926: Table 1 prints 6 ± 1.5; the text layer reads 681.5, the number BRENDA and OED list',
      "code: fetch.GLYPH_SIGNS knows ± as '6' (8 Oct); fetch.two_points warns on any number with two decimal points, a "
      "± drawn as any digit or cells run together (1 Nov); readers and verifiers then read the page image; the database "
      'check finds a database that copied the merged number',
      [CC, R, V, DBC],
      '64 texts with 3+ two-decimal tokens holding an 8 (53 without a warning, 16 of those done); 42 texts rebuilt with '
      'the warning; 133 stored values from such tokens checked on page images, all right; BRENDA and OED list 681.5',
      'rule', ledger=[4, 'pm8'], novelty='old system',
      inherited="old system: '± into 6' is in the glyph warning listed among the \"Old-system lessons\" (8 Oct)",
      rule='768e645',
      ev=[('git:3c3e3c6', '(or ± into 6, minus into 21)'),
          ('tools/fetch.py', 'TWO_POINTS = re.compile('),
          ('CLAUDE.md', 'numbers with two decimal points (`fetch.two_points`: `2.580.4` is 2.5 ± 0.4'),
          ('paper/figures/method_overview/BRIEF.md', 'BRENDA and OED list 681.5 beside their own kcat 7.5 and Km 1.25, whose ratio is 6.0.'),
          ('paper/figures/method_overview/BRIEF.md', 'the page gives 6 ± 1.5')]),
    C('TL3', "Shown quote keeps the text layer's wrong symbols", 'the PDF text layer or OCR', 'FA',
      "no PMID on file: '66.7 f 8.3' shown for 66.7 ± 8.3",
      "code: the printed line shows the paper's own symbols (JBC code points mapped back); a line that still lost a "
      'symbol says so in printed_line_note',
      [CV], 'not counted', 'flag kept as printed', ledger=['quotesym'], rule='4798de4'),
    C('TL4', 'Stray control characters inside a number', 'the PDF text layer or OCR', 'FA',
      'no PMID on file: one PDF printed 2.6 as 2<U+008A>.6',
      'code: control characters and a two-glyph ± are cleaned before parsing', [CV], 'not counted', 'rule',
      ledger=[7], rule='3c6a6b4'),
    C('TL5', 'A superscript exponent lost to another line', 'the PDF text layer or OCR', 'FA',
      "no PMID on file: a '× 10' whose power moved to the line above",
      "code refuses a '× 10' with no exponent; read.md: read the exponent from the page image",
      [CV, R], 'not counted (an old-system lesson)', 'rule', novelty='old system',
      inherited='old system: "bare x10 ... in code" is among the "Old-system lessons" (8 Oct)', rule='3c3e3c6',
      ev=[('git:3c3e3c6', 'bare x10 / M^-2 / glyph units in code'),
          ('prompts/read.md', 'A `× 10` with no exponent means the superscript moved to an adjacent line'),
          ('CLAUDE.md', 'Units code also refuses a `× 10` with no exponent')]),
    C('TL6', "OCR garbles a scanned page's digits", 'the PDF text layer or OCR', 'FR',
      "NPEBD0B162: the scan's OCR reads raised decimal points as hyphens ('0-34'); all 20 values were lost",
      'verify.md: a cell the OCR split or misread is confirmed on the page image (on_page_image); code then keeps and '
      'flags it (quote_check) instead of refusing it; code reads such hyphens as decimal points; scans get an OCR glyph '
      'warning (1 Nov)',
      [V, CC, CV],
      "4 values (4622304), 5 (10021417); 32 values recovered (hyphens); 18783250's 6 pH-column values still refused",
      'rule', ledger=[8, 33], rule='db34453',
      ev=[('prompts/verify.md', "A cell whose digits a scan's OCR split or misread"),
          ('catlog.py', 'the verifier read this cell on the page image (the text layer is a scan)'),
          ('tools/fetch.py', 'def scan_warning(text):'),
          ('CLAUDE.md', '18783250\'s pH 6.5/8.5 columns (OCR "65"/"83") were left without pH and rejected as conflicts (6 values)'),
          ('catlog.py', 'read those hyphens as decimal points: NPEBD0B162'),
          ('git:7d212bd', "OCR it as a hyphen ('0-34')")]),
    C('TL7', 'Only OCR text exists, no page image', 'the PDF text layer or OCR', 'FR',
      "6354095: Elsevier's OCR runs Table III's cells together ('0.0660.315'); 8 confirmed Km values refused",
      'code refuses a value its quote does not hold (value_not_in_quote) and marks the paper incomplete for a better copy; '
      'OPEN: needs the full PDFs (the owner\'s call)',
      [CC],
      '3,309 OCR-only texts (13 Oct); 68 confirmed values in 13 papers refused; 3,653 values in 103 papers checked '
      'against OCR text only',
      'open', ledger=[32],
      ev=[('CLAUDE.md', '103 read so far with 3,653 values that were checked against OCR text only'),
          ('CLAUDE.md', 'so 8 confirmed Km values were rejected `value_not_in_quote`'),
          ('CLAUDE.md', 'together ("0.0660.315")')]),
    C('TL8', "Publisher XML runs a cell's parts together", 'the PDF text layer or OCR', 'FR',
      "34054745: the Europe PMC XML prints 654 ± 2.1 as '6542.1'",
      'code refuses the value (value_not_in_quote) and marks the paper incomplete so its PDF gets filed; OPEN',
      [CC], '38 values in 2 papers (34054745: 20, 21072165: 18)', 'open', ledger=[40],
      ev=[('CLAUDE.md', '34054745 drops every ± ("6542.1" = 654 ± 2.1, 20 values)')]),
    C('TL9', "CatLog's converter ran stacked cell values together", 'the PDF text layer or OCR', 'FR',
      "40454099: Table 3's cells stacked with <break/> became '0.19060.2145'",
      'code: jats_to_text writes a space for a <break/> inside a cell; the texts were rebuilt and their papers re-read',
      [CV], '125 texts rebuilt; 12 done papers re-read: 23 values recovered, no conflict', 'rule', ledger=['break'],
      rule='81f7945', ev=[('CLAUDE.md', '("0.19060.2145", 40454099)')]),
    C('TL10', 'Tables printed only as images', 'the PDF text layer or OCR', 'FR',
      '10965051: the verifier found 191 values of tables printed only as images',
      'read.md: read image-only tables of a scan on the page images (quote "[page image p.N]"); a JATS or Elsevier '
      'table deposited as a picture (TABLE IS AN IMAGE ONLY) sends the paper for OCR of its PDF; verifiers write '
      'skipped values to a missed file',
      [R, V, CC], '147 and 191 values (102640, 10965051)', 'rule', ledger=[9], rule='25604bf',
      ev=[('prompts/read.md', 'Exception, a scanned PDF (OCR text layer) whose table cells are missing from the text'),
          ('prompts/read.md', 'A `TABLE IS AN IMAGE ONLY` line')]),
    # ===================================================================================== the reading agent
    C('RA1', 'A constant that is not kcat or Km', 'the reading agent', 'FA',
      "26142822: a cooperative enzyme (Hill n = 1.5) whose K0.5 is 18 µM; a 'Km = 19 µM' from the Methods was stored as its Km",
      'read.md and verify.md rule 2: Hill constants, Ki, Kd, Kact, IC50, metal half-activation constants, Vmax, specific '
      'activity, a ratio relative to wild type and an activator\'s or rescue agent\'s half-saturation are not Km or kcat',
      [R, V, AU],
      '126 values refused as not a kcat or Km (104 by verifiers, 22 by audits and sweeps); the verifier caught 89 values '
      'of the wrong quantity in 22 papers (development)',
      'rule', ledger=[1, 'k05'], novelty='old system',
      inherited='old system: "Hill/Ki/Kd/Vmax are not Km/kcat" is one of its lessons; 25658941 (Hill) and 15799715 '
                '(chemical rescue) were wrong in old certified rows',
      rule='4d7cfd9',
      ev=[('CLAUDE.md', 'Hill/Ki/Kd/Vmax are not Km/kcat, no reprinted values'),
          (ASSESS, 'PMID25658941(Hill/cooperative apparent constant as ordinary Km),15799715(chemical-rescue ligand half-saturation as substrate Km)'),
          ('prompts/read.md', 'Hill constants (K0.5, S0.5, or an "apparent Km" from a Hill fit with n clearly ≠ 1), Ki, Kd, Kact, IC50,'),
          ('prompts/verify.md', '2. `metric` is right: the column/sentence really is kcat, Km or kcat/Km'),
          (CASES, '| not a kcat or Km (Hill, Ki, Kd, Vmax, ratio, cofactor) | 126 | 104 | 22 |'),
          (LAYERS, '"metric": { "values": 89, "papers": 22,'),
          (BOXES, 'Two cells headed kcat/Km are ratios of two efficiencies'),
          ('log.tsv', 'Its measured half-saturation is K0.5 = 18 ± 2 uM (Table 1), not a Km.')]),
    C('RA2', 'Assay conditions taken from another step', 'the reading agent', 'FA',
      '2775236: the 25 °C colour development was stored instead of the 37 °C enzyme incubation (an old certified row)',
      'read.md and verify.md rule 6: the pH and temperature of the enzyme reaction itself, not of a stop, colour or '
      'storage step, an optimum or a screen; a coupled-assay reagent goes in conditions, not cosubstrate; code: a pH or '
      'temperature must be printed in the paper',
      [R, V, CC],
      '5 condition or cofactor fixes among 30 sampled old certified rows; the verifier corrected the conditions of 103 '
      'values in 20 papers (development)',
      'rule', ledger=[1], novelty='old system',
      inherited='old system: 5 of the 9 material cases in 30 sampled old certified rows were condition or cofactor fixes',
      rule='4d7cfd9',
      ev=[(ASSESS, '(25C color development confused with37C enzyme incubation)'),
          (ASSESS, '| Material issue | 9 | Three metric/provenance rejects; five condition/cofactor fixes'),
          (ASSESS, 'The 30-row random sample had 25 checkable rows'),
          ('prompts/read.md', 'Use the pH and temperature of the enzyme reaction itself, not of a stop, colour-development/'),
          ('prompts/read.md', 'A reagent of a coupled detection system'),
          (LAYERS, '"condition": { "values": 103, "papers": 20,')]),
    C('RA3', 'Partial per-product constants stored as kcat', 'the reading agent', 'FA',
      "21361343: per-product cells of a branched reaction (Table 3, footnote b: 'kcat = βkcat + cinkcat') stored as kcat and kcat/Km",
      'read.md and verify.md rule 2 "Partial constants": only the total kcat and total kcat/Km the paper prints are kcat '
      'and kcat/Km (13 Oct); scans of papers read before the rule; audits',
      [R, V, AU],
      '429 values refused as partial constants (74 by verifiers, 355 by audits and sweeps); 227 more dropped on 23 Oct',
      'rule', ledger=[29, 'blindpartial', 'h2hpartial'], rule='20840f1',
      ev=[('prompts/read.md', 'Partial constants are not kcat or kcat/Km'),
          ('prompts/verify.md', 'not a partial, per-product constant of a branched reaction'),
          (CASES, '| partial constant of a branched reaction | 429 | 74 | 355 |'),
          ('CLAUDE.md', 'PMID 21361343 (TcPAM, Table 3)'),
          # the footnote as the paper prints it (the text layer draws its + as þ); fixed 2 Nov after CRITIQUE_1.md
          ('texts/21361343.txt', 'constant kcat = βkcat þ cinkcat')]),
    C('RA4', 'Reader misreads a unit, prefix or multiplier', 'the reading agent', 'FA',
      "16431280: the header 's^-1 × 10^-4' was applied as × 10^4, putting kcat/Km past diffusion",
      "verify.md rule 3: check every 'stored as' value, the sign and power of each header multiplier on the page image, "
      'and all three cells when kcat/Km is 5x or more off kcat ÷ Km; fix.unit_for_conversion; the code\'s ratio check '
      'notes the misfit; a database difference at a unit factor is checked against the paper',
      [V, CC, DBC],
      'the verifier caught 1,215 values off by a unit factor in 116 papers (5.9 per 1,000 values the reader wrote, '
      'development); 60 values dropped (16431280)',
      'rule', ledger=[22], novelty='old system',
      inherited='old system: "a ≥5× kcat/Km mismatch means re-check the units" is one of its lessons',
      rule='f171ab3',
      ev=[('CLAUDE.md', 'a ≥5× kcat/Km mismatch means re-check the units, mature-chain numbering offsets'),
          ('prompts/verify.md', 'Confirm the sign and power of any header multiplier on the rendered page image'),
          ('prompts/verify.md', 'A kcat/Km ≥5× away from kcat ÷ Km of the same row usually means a misread unit'),
          ('catlog.py', 'def ratio_check(by):'),
          (LAYERS, '"unit": { "values": 1215, "papers": 116, "per_1000": 5.912,')]),
    C('RA5', 'Printed ± dropped from the stored cell', 'the reading agent', 'FA',
      'no PMID on file: a cell printed 12.3 ± 0.4 stored as 12.3',
      'verify.md rule 1: a raw value missing a printed ± is a fix; code completes a dropped ± from the quote when the '
      'number is printed once there (8-9 Oct)',
      [V, CV], 'not counted', 'rule', novelty='old system',
      inherited='old system: "full printed cell with ±" is one of its lessons', rule='aa032a4',
      ev=[('CLAUDE.md', 'full printed cell with ±, same-row pairing only'),
          ('prompts/verify.md', 'A raw value missing a printed ± is a `fix`.'),
          ('prompts/read.md', '`raw_value`: the full printed cell, exactly as printed, including ± error or (n).')]),
    C('RA6', 'Reader skips values the paper prints', 'the reading agent', 'FR',
      'no PMID on file: the old system read 3,071 papers only for their target rows',
      'read.md: extract every kcat, Km and kcat/Km, not only a main table; the verifier writes skipped values to a '
      'missed file that a second checker verifies, and a paper stays open while they are unverified; completeness audits',
      [V, R, AU],
      '1,138 values in 94 papers that readers skipped and verifiers found (a second verifier confirmed 1,100)',
      'rule', novelty='old system',
      inherited='old system: it read 3,071 papers only for its target rows (sources/fulltext_read_before.txt)',
      rule='f171ab3',
      ev=[('CLAUDE.md', '3,071 papers the old system read only for its target rows'),
          ('prompts/read.md', 'Extract EVERY kcat, Km and kcat/Km value the paper itself measured and prints as a number'),
          ('prompts/verify.md', 'If the extractor skipped measured kcat, Km or kcat/Km values that you are sure of'),
          (AGENTS, '| Values readers skipped that verifiers found | 1,138 in 94 papers; a second verifier confirmed 1,100 |')]),
    C('RA7', 'An agent leaves a required field empty', 'the reading agent', 'FR',
      '19397282: 36 Dpo4 rows lost to an empty variant the paper makes clear',
      'verify.md rule 4: an enzyme, variant or substrate left empty that the paper makes clear is a fix (10 Oct); OPEN for '
      'a reader that leaves location empty for a whole paper (a reread fixes it; no guard)',
      [V], '36 rows (19397282); 18 (31799256); 16 (25644306)', 'open', ledger=[15, 31], rule='da62f48',
      ev=[('prompts/verify.md', 'one left empty that the paper makes clear is a `fix`'),
          ('CLAUDE.md', 'Worth a cheap guard in the reader prompt or in `add`')]),
    C('RA8', "A checking agent's verdict is wrong", 'the reading agent', 'FA',
      "41835576: an auditor misread swapped columns under a 'kcat | KM' header and dropped a correct kcat",
      'code: restore brings back a value an audit dropped when the paper shows the auditor misread it; every drop of a '
      'follow-up needs two auditors agreeing; dbcheck-record flags evidence the paper does not print; dbdiff --reask; a '
      'catlog_wrong value an audit kept is asked again',
      [CC, AU, DBC],
      '1 value restored (41835576); 8 rows of 19211556 asked again; 1 row of 25016016 reopened; 4 values of '
      '40723313 back to the printed unit (2 Nov)',
      'rule', ledger=[45, 'evflags', 'dbverdict', 'override'], rule='3d917ef',
      ev=[('catlog.py', 'def cmd_restore(why, *ids):'),
          ('git:e72b5be', '41835576 Table 1: cells sit in swapped columns under a kcat | KM header'),
          (BLIND, 'every drop needed a second independent auditor to agree')]),
    C('RA9', 'Implausible but printed values rejected by the verifier', 'the reading agent', 'FR',
      '36756200: a kcat headed ×10^5 s^-1 would empty the assay in milliseconds; its own Figure 7D prints the same scale',
      "verify.md rule 3: an implausible scale is by itself no reason to reject or rescale; the paper's own numbers decide, "
      'and the arithmetic goes in a note',
      [V], '22 values rejected (12 Oct); 20 back as printed (31 Oct)', 'rule', ledger=['implaus'], rule='c005e33',
      ev=[('prompts/verify.md', 'A physically implausible scale (a kcat that would use up the assay\'s substrate in milliseconds')]),
    C('RA10', 'Bounds and not-detected values never recorded', 'the reading agent', 'FR',
      "17692452: a censored-only pass of 24 Oct added 12 bounds to a paper read on 9 Oct",
      'read.md "Censored values" and verify.md rule 9: a bound or a defined "not detected" is a row of its own; code keeps '
      'them in bounds.jsonl, never in the numeric columns, medians or comparisons; a censored-only pass re-reads earlier '
      'papers',
      [R, V, CC],
      '{censored} censored values stored by 2 Nov (catlog.py status); 0 bounds among 221,797 values before',
      'rule', ledger=['censored'], rule='47eafb8',
      ev=[('prompts/read.md', 'Values the paper tried to measure but prints'),
          ('prompts/verify.md', '9. A row with `censored` set'),
          ('log.tsv', '2026-10-24 09:55 17692452 add kept=0 dup=0 rejected=0 status=done bounds=12 pass=censored'),
          (STATUS, '19,049 censored'),
          ('log.tsv', '2026-10-09 06:10 17692452 add kept=45')]),
    C('RA11', 'Undeterminable constant stored as not detected', 'the reading agent', 'FA',
      "18222180: Table 1's 'NM, not measurable' Km of an active enzyme (kcat/Km 1660 M^-1 s^-1 printed) stored as not detected",
      'read.md: "not detected" means no activity, never a constant the paper could not determine although the enzyme was '
      'active; verify.md rule 9; code: limitfix clears a limit that bounds another quantity',
      [R, V, CC],
      '715 stored values with such a cue in 81 papers checked: 59 removed, 38 limits cleared',
      'rule', ledger=['nd'], rule='85553bf',
      ev=[('prompts/read.md', '"Not detected" means no activity, or activity too low to measure.'),
          ('catlog.py', 'def cmd_limitfix(why, *ids):'),
          ('work/nd_check/drop_agreed.tsv', "kcat NM^b, Km NM, kcat/Km 1660 M^-1 s^-1; footnote b 'NM, not measurable'")]),
    C('RA12', 'Bisubstrate kcat/(KmA·KmB) taken as kcat/Km', 'the reading agent', 'FA',
      'no PMID on file: an efficiency printed in M^-2 s^-1',
      'code refuses an M^-2 kcat/Km; read.md and verify.md rule 2: a kcat/(KmA·KmB) is skipped',
      [CV, R, V], 'not counted (an old-system lesson)', 'rule', novelty='old system',
      inherited='old system: "M^-2" is among the "Old-system lessons" (8 Oct)', rule='3c3e3c6',
      ev=[('git:3c3e3c6', 'bare x10 / M^-2 / glyph units in code'),
          ('prompts/read.md', 'A kcat/(KmA·KmB) (units M^-2 s^-1) is not kcat/Km: skip.')]),
    C('RA13', 'kcat basis per dimer or site left unstated', 'the reading agent', 'FA',
      'no PMID on file: a kcat per active site stored with no basis',
      "read.md: metric_note says 'kcat per dimer' or 'per active site' only when the paper states the basis",
      [R], 'not counted (an old-system lesson)', 'rule', novelty='old system',
      inherited='old system: "kcat basis" is among the "Old-system lessons" prompt rules (8 Oct)', rule='3c3e3c6',
      ev=[('git:3c3e3c6', 'kcat basis'),
          ('prompts/read.md', '`kcat per dimer` / `per active site` (only when the paper states the basis)')]),
    # ================================================================================= identity and pairing
    C('IP1', 'Values of different rows combined into one record', 'identity and pairing', 'FA',
      'no PMID on file: the old catalogue exported the largest kcat and the smallest Km of a group as one record',
      'read.md and verify.md rule 4: kcat, Km and kcat/Km belong together only when they come from one printed row and '
      'fit; code (measurements()): rows group only when paper, enzyme, organism, variant, substrate, cosubstrate, pH, '
      'temperature, location and construct agree; an ambiguous pairing is never made; kcat/Km is derived only from one '
      'record, marked derived',
      [CC, R, V], 'not counted (the old catalogue)', 'rule', novelty='old system',
      inherited='old system: its 14 Aug expert review (P0.3) found kcat = max and Km = min of a group exported as one '
                'record; "composite max-kcat/min-Km merges" are among its known defects',
      rule='f171ab3',
      ev=[(EXPERT, '### P0.3 Cluster merge fabricates best-case kinetics (High)'),
          (EXPERT, '`kcat = max(all kcats)` and `km = min(all kms)`'),
          ('CLAUDE.md', 'its known defects include composite max-kcat/min-Km merges, certified twins'),
          ('prompts/read.md', 'kcat, Km and kcat/Km belong together only when they come from the same printed row and fit'),
          ('catlog.py', 'def measurements(rows):'),
          ('CLAUDE.md', 'ambiguous pairings are never made')]),
    C('IP2', 'One assay split into separate records', 'identity and pairing', 'FA',
      'no PMID on file: one assay\'s kcat, Km and kcat/Km in three export rows',
      'code: measurements() groups one assay\'s values (shared conditions apart from per-value notes) and checks kcat/Km '
      'against kcat ÷ Km within the printed uncertainties; read.md: the same conditions text for the three values of one '
      'measurement, and a note copied onto a column describes the column only',
      [CC, R], 'not counted', 'rule', ledger=[2], rule='aec6ab2',
      ev=[('prompts/read.md', 'Write the SAME text for the kcat, Km and kcat/Km of one measurement, so they stay together.'),
          ('prompts/read.md', 'A note you copy onto every row of a column must describe the column only')]),
    C('IP3', 'The same measurement stored twice', 'identity and pairing', 'FA',
      '25495127: 83 re-read copies of cells already stored (224 ± 10), their unit or wording typed otherwise',
      'code: one value per measurement slot; a re-read\'s copy of an accepted value (same printed cell and converted '
      'value, overlapping quote; unit spellings, labels, Greek letters; each accepted row paired once) is a duplicate; '
      'recheck reports one-to-one duplicates; verify.md rule 8: no row duplicates another',
      [CC, V],
      '{dups_dropped} re-read copies dropped (log.tsv, 11-30 Oct: {dups_by_day}); {reworded} copies refused at add (log.tsv '
      'reworded_duplicate); 293 values refused as printed twice in one paper (269 by verifiers)',
      'rule', ledger=[21, 39, 42, 'blinddups', 'dups1030'], novelty='old system',
      inherited='old system: "certified twins" are among its known defects; reworded re-read duplicates are among the '
                '"Old-system lessons" (8 Oct)',
      rule='157c8bb',
      ev=[('CLAUDE.md', 'its known defects include composite max-kcat/min-Km merges, certified twins'),
          ('git:3c3e3c6', 'reworded re-read duplicates caught by printed cell + quote'),
          ('CLAUDE.md', 'the catalog keeps ONE value per measurement slot'),
          ('catlog.py', 'def same_quote(a, b):'),
          ('prompts/verify.md', '8. The row is not a duplicate of another row in the file'),
          (CASES, '| printed twice in the same paper | 293 | 269 | 24 |'),
          ('log.tsv', 're-read copy of accepted row c92bf8f4ede3f710 (same printed cell 224 ± 10')]),
    C('IP4', 'A re-read or stale verdict changes a value', 'identity and pairing', 'FA',
      'no PMID on file: a verdict applied to a row whose order had changed',
      'code: a different value for an accepted slot is a conflict, kept apart and decided from the paper; audit drops '
      'stay dropped; a verdict must echo its row\'s metric and raw_value; out-of-date work files are refused',
      [CC], '{conflicts} conflicts logged (log.tsv), each decided from the paper', 'rule', ledger=[3], rule='157c8bb',
      ev=[('CLAUDE.md', 'verdicts that name a different row (each verdict echoes the row\'s metric and raw_value)'),
          ('prompts/verify.md', "copy that row's `metric` and `raw_value` into it exactly")]),
    C('IP5', 'Paralogs and strains forced into one slot', 'identity and pairing', 'FR',
      'no PMID on file: E. cloacae P99 and 908R values refused as conflicts',
      'code: the printed gene and strain are part of the slot and of the grouping', [CC], 'not counted', 'rule',
      ledger=[12], rule='586e755'),
    C('IP6', 'Natural forms recorded as variants', 'identity and pairing', 'FA',
      'no PMID on file: allozymes such as ADH1B*2 written in the variant field',
      'read.md and verify.md rule 5: an isozyme, paralog, allele, splice or strain form is the enzyme\'s identity, '
      'variant wild type (10 Oct); code: catlog.identity() with sources/natural_forms.tsv for older rows',
      [R, V, CC, PE], '78 older rows, each checked against its paper', 'rule', ledger=[19], novelty='old system',
      inherited='old system: "alleles and preparations" are among the "Old-system lessons" prompt rules (8 Oct)',
      rule='86b8807',
      ev=[('git:3c3e3c6', 'alleles and preparations'),
          ('prompts/read.md', "is the enzyme's identity, not a variant"),
          ('catlog.py', 'def identity(r):'),
          ('CLAUDE.md', 'listed in `sources/natural_forms.tsv` (78, each checked against its paper)')]),
    C('IP7', "A natural form given another form's sequence", 'identity and pairing', 'FA',
      '29228168: SHV-14 (SHV-1 plus two substitutions) carried SHV-1\'s canonical sequence',
      'code (sequences): a form gets a sequence only from an entry of its own, not one shared with another form of the '
      'paper; a checked natural-form line drives this guard',
      [CC], '4 shared accessions named; 3 papers fixed (23128527, 29228168, 3276326)', 'rule', ledger=['formseq'],
      rule='9f9c1fe',
      ev=[('CLAUDE.md', 'A form gets a sequence only from an entry of its own'),
          ('git:9f9c1fe', 'SHV-14 (29228168, SHV-1 plus the two substitutions the paper names)')]),
    C('IP8', "Measured construct's sequence kept the signal peptide", 'identity and pairing', 'FA',
      'no PMID on file: a construct "without its signal peptide" stored with the precursor',
      "code (sequences): the mature chain from the printed start residue, else after UniProt's signal or transit span; "
      'blank with the reason when UniProt marks none',
      [CC], '1,250 records of 109 papers', 'rule', ledger=['signal'], rule='15e9f2c',
      ev=[('CLAUDE.md', 'A construct stated without its signal peptide (or mitochondrial/chloroplast leader) is trimmed')]),
    C('IP9', 'Values linked to the wrong protein entry', 'identity and pairing', 'FA',
      '11900558: an NCBI genome segment with many coding sequences gave PurT to a β-mannosidase',
      'code (sequences): NCBI CDS only from a one-CDS record; a cited PDB only for its own protein; UniProt EC hits must '
      'fit the enzyme name; mutations choose among candidates; each enrichment change reviewed by a skeptic agent; '
      'human review of records',
      [CC, PE], '~790 values (12 Oct sweep); 1 paper (11900558); rat MCAD had LCAD; lung PGFS had AKR1A1', 'rule',
      ledger=[13, 17, 25, 'review2'], rule='704025b',
      ev=[('CLAUDE.md', '(only a record with ONE CDS: genome segment AP000002 gave PurT for a β-mannosidase, PMID 11900558)')]),
    C('IP10', 'Alias names or no organism leave no protein', 'identity and pairing', 'FR',
      'no PMID on file: KPC-2 papers that name no organism',
      'none: a name-search fix was reverted after review, and a strict gene-name rule fixes neither example; people find '
      'these records on the website',
      [PE], 'the 70 records shown as EC Unknown (KPC-2)', 'open', ledger=['alias']),
    C('IP11', 'The measured variant recorded wrongly', 'identity and pairing', 'FA',
      '19501264: a second-round variant recorded with only its new mutations (K224Q/L283F)',
      'read.md and verify.md rule 4: the variant comes from the row\'s own label, a mutant is never wild type, a '
      'directed-evolution variant carries its template\'s mutations (19 Oct); audits',
      [R, V, AU],
      '17 rows (19501264); 8 values (1537854, 1939081, 15639226); the verifier corrected the identity of 127 values in '
      '18 papers (development)',
      'rule', ledger=[44, 'blindvariant'], novelty='old system',
      inherited='old system: "wild-type flag errors" are among its known defects', rule='db38b4d',
      ev=[('CLAUDE.md', 'SMILES name collisions and wild-type flag errors'),
          ('prompts/read.md', 'A directed-evolution round names only its NEW mutations'),
          ('prompts/verify.md', 'A variant of a directed-evolution round must carry'),
          ('prompts/read.md', 'further mutations K224Q/L283F in 2nd B10'),
          (LAYERS, '"identity": { "values": 127, "papers": 18,')]),
    C('IP12', 'kcat/Km filed under the wrong substrate', 'identity and pairing', 'FA',
      'no PMID on file: an efficiency of a two-substrate table filed under the fixed substrate',
      'read.md and verify.md rule 4: a kcat/Km belongs to the substrate whose Km is its denominator',
      [R, V], 'not counted (an old-system lesson)', 'rule', novelty='old system',
      inherited='old system: "kcat/Km denominator" is among the "Old-system lessons" prompt rules (8 Oct)',
      rule='3c3e3c6',
      ev=[('git:3c3e3c6', 'kcat/Km denominator'),
          ('prompts/read.md', 'A kcat/Km belongs to the substrate whose Km is its denominator'),
          ('prompts/verify.md', 'A kcat/Km is for the substrate whose Km is its denominator.')]),
    C('IP13', 'One kcat copied onto a second substrate', 'identity and pairing', 'FA',
      'no PMID on file: one printed kcat filed under both varied substrates',
      'read.md and verify.md rule 4: record a printed kcat once, under the substrate whose saturation curve produced it',
      [R, V], 'not counted (an old-system lesson)', 'rule', novelty='old system',
      inherited='old system: "one kcat for two substrates" is among the "Old-system lessons" prompt rules (8 Oct)',
      rule='3c3e3c6',
      ev=[('git:3c3e3c6', 'one kcat for two substrates'),
          ('prompts/read.md', 'One printed kcat beside separate Km columns for two varied substrates'),
          ('prompts/verify.md', 'One printed kcat must not be copied onto a second varied substrate.')]),
    C('IP14', '"Respectively" lists matched to the wrong names', 'identity and pairing', 'FA',
      'no PMID on file: "Km values for A, B and C were x, y and z, respectively"',
      'read.md and verify.md rule 4: the n-th value belongs to the n-th name; count positions',
      [R, V], 'not counted (an old-system lesson)', 'rule', novelty='old system',
      inherited='old system: "respectively lists" is among the "Old-system lessons" prompt rules (8 Oct)',
      rule='3c3e3c6',
      ev=[('git:3c3e3c6', 'respectively lists'),
          ('prompts/read.md', 'the n-th value belongs to the n-th name. Count positions.')]),
    C('IP15', 'Different preparations of one enzyme paired together', 'identity and pairing', 'FA',
      'no PMID on file: a native and a recombinant enzyme\'s values joined in one record',
      "read.md: different preparations (native vs recombinant, tagged vs untagged, two truncations) get different "
      'construct texts; code: construct is part of the measurement identity',
      [CC, R], 'not counted (an old-system lesson)', 'rule', novelty='old system',
      inherited='old system: "construct in measurement identity" is among the "Old-system lessons" (8 Oct)',
      rule='3c3e3c6',
      ev=[('git:3c3e3c6', 'construct in measurement identity'),
          ('prompts/read.md', 'get different `construct` texts, so code never pairs them')]),
    C('IP16', "Mutation numbering offset from the sequence's", 'identity and pairing', 'FA',
      'no PMID on file: mutations numbered on the mature chain, the sequence on the precursor',
      'code (sequences): the first numbering frame in which every wild-type residue of the paper\'s mutations matches '
      '(PDB author numbering, canonical, isoforms, mature chain), else the printed primers, else blank with the frames '
      'tried; enrich finds one paper-wide offset',
      [CC], 'not counted (an old-system lesson)', 'rule', novelty='old system',
      inherited='old system: "mature-chain numbering offsets" is one of its lessons', rule='c1bf801',
      ev=[('CLAUDE.md', 'mature-chain numbering offsets (enrich finds one paper-wide offset)'),
          ('CLAUDE.md', "Mutants: first numbering frame where EVERY wild-type residue of the paper's mutations matches")]),
    C('IP17', 'A substrate given the wrong chemical structure', 'identity and pairing', 'FA',
      'no PMID on file: xylose given lactose\'s structure from a same-paper database vote',
      "code (structures): a name resolves through the paper's own definition, Rhea, or a same-paper database name that "
      "fits OPSIN's formula of the printed name (printed_fit); a ChEBI name shared by compounds is no synonym; an "
      'abbreviation hit must share a word with the printed full name; a metal complex drawn in pieces gets no structure; '
      'skeptic-agent review of each enrichment change; human review',
      [CC, PE], '~450 values (12 Oct sweep); 48 wrong structures from same-paper votes', 'rule',
      ledger=[17, 25, 26, 'abbrev', 'review2'], novelty='old system',
      inherited='old system: "SMILES name collisions" are among its known defects', rule='ba0d005',
      ev=[('CLAUDE.md', 'SMILES name collisions and wild-type flag errors'),
          ('tools/structures.py', 'def printed_fit(smi, db_name, own_names, either=False):'),
          ('CLAUDE.md', '48 wrong structures, e.g. xylose was lactose, NADPH NADH')]),
    C('IP18', 'Wrong paper read: a related article', 'identity and pairing', 'FA',
      '8538700: the old system kept a 1999 review in place of the 1995 original',
      'read.md and verify.md rule 0: the expected title, a related paper of the same group is a wrong paper, an id with '
      'no PMID by its DOI; code: a PDF is filed by title only when the title is printed near its top; files rejected '
      'for a paper are remembered by content',
      [CC, R, V], '3 of 14 PDFs filed by title words alone; {wrong_paper} wrong_paper events (log.tsv)', 'rule',
      ledger=[20], novelty='old system',
      inherited='old system: "prove paper identity" is one of its lessons; 8538700 kept the wrong article',
      rule='1eb0882',
      ev=[OLDLESSON, (ASSESS, '**Saved-article mismatch:** PMID8538700 retained a1999 review instead of the1995 original.'),
          ('prompts/read.md', 'A related paper from the same group with overlapping title words is a wrong'),
          ('CLAUDE.md', 'Files rejected for a paper (wrong article, one-page preview) are remembered by content')]),
    C('IP19', 'EC number in a non-standard form', 'identity and pairing', 'FA',
      "39915905: 'EC1.1.3.10' kept its records out of the website's EC filter",
      "code: clean_ec drops a printed 'EC' prefix and fills an incomplete number with '-' places", [CV],
      "not counted (39915905's records)", 'rule', ledger=['ec'], rule='8d18a62'),
    # ================================================================================== conversion and units
    C('CU1', 'A unit the code cannot convert passes unconverted', 'conversion and units', 'FA',
      'no PMID on file: the old converter returned an unconverted min^-1 value labelled s^-1',
      'code (units.normalize): a printed cell and unit convert to catalogue units or the value is refused with '
      'unknown_*_unit; no unit is ever defaulted; a model never types a converted value',
      [CV], '{unknown_unit} values refused for a unit the code does not convert (rejected.jsonl)', 'rule',
      novelty='old system',
      inherited='old system: its 14 Aug expert review (P0.4) found an unrecognised unit passed through unconverted and '
                'labelled s^-1 or mM',
      rule='f171ab3',
      ev=[(EXPERT, '### P0.4 Silent unit-normalization failure + hardcoded unit labels (High)'),
          (EXPERT, 'return the **unconverted** value on an unrecognized unit'),
          ('tools/units.py', "return None, None, f'unknown_km_unit:{raw_unit}'"),
          ('CLAUDE.md', 'A model never types a converted value: code converts the printed cell and unit')]),
    C('CU2', 'Code borrowed or mis-scaled an error term', 'conversion and units', 'FA',
      "29421037: a bare kcat/Km cell got the neighbouring Km cell's ± (0.59 ± 0.09)",
      'code: complete a dropped ± only when the number is printed once in the quote and the ± has no exponent of its own; '
      "rel_uncertainty and parse_number carry a ± term's own exponent; pmfix takes off a ± the cell does not print",
      [CV, AU], '1 audited row; 11 values (pmfix); the tolerance of 46 of 51 rows in 6 papers', 'rule',
      ledger=[10, 11, 49, 'pmfix'], rule='495383e',
      ev=[('catlog.py', 'def rel_uncertainty(raw):'), ('catlog.py', 'def cmd_pmfix(why, *ids):'),
          ('log.tsv', "the pyruvic acid kcat/Km cell is a bare '0.59', and the next cell, meso-DAP Km, is '0.59 ± 0.09' mM")]),
    C('CU3', 'Parser read a spaced exponent as none', 'conversion and units', 'FA',
      "41657244: '2.76E + 03' read as 2.76, a 1000-fold error",
      "code: units.parse_number reads a spaced exponent ('2.76E + 03', '6.53E− 05') as aE+b",
      [CV, SWEEP], '15 values (41657244: 6, 42639739: 9), stored right because readers had set unit_for_conversion',
      'rule', ledger=[48], rule='2b61622',
      ev=[('tools/units.py', 'def parse_number(raw):'),
          ('CLAUDE.md', "a spaced exponent '2.76E + 03' that `units.normalize` reads as 2.76 (41657244 only;")]),
    C('CU4', 'A printed form the parser refused', 'conversion and units', 'FR',
      "42249657: '27,828 (24,558–31,987)' read as a range, not a value with its interval",
      "code: 'apparent molecular weight' is no per-value qualifier; a bracketed interval goes with its value; a caret "
      'multiplier converts; ≪ and ≫ are bounds; recover re-adds rows a changed rule no longer refuses',
      [CV], '21 values (7470464); 5 (36698977); 9 (42249657); 1 (18669639)', 'rule',
      ledger=[35, 46, 'caret', 'gg'], rule='322c01c',
      ev=[('catlog.py', '(42249657: 9 values lost to bound_or_range)'), ('catlog.py', 'def cmd_recover(reason, *args):'),
          ('git:20630e5', "'27,828 (24,558–31,987)'")]),
    C('CU5', 'Code required a detail the paper omits', 'conversion and units', 'FR',
      '23946505: 25 confirmed kcat/Km values refused because their column prints no unit',
      'code: an unprinted pH or temperature is left empty (8 Oct), organism is optional (9 Oct), a verifier\'s '
      'unit_for_conversion stands in for an empty raw_unit (23 Oct); read.md: write the unit the paper\'s own columns '
      'fix and the reason in metric_note, never a remark in the unit field',
      [CC, R, V], '168 values (organism); 310 values in 24 papers recovered (no printed unit); 25 of 23946505', 'rule',
      ledger=[5, 6, 31, 'rawunit', 'unitremark'], rule='aa032a4',
      ev=[('catlog.py', "NEEDED = ['enzyme', 'variant', 'substrate', 'metric', 'raw_value', 'raw_unit', 'location', 'quote']"),
          ('prompts/read.md', 'when the paper prints no unit for the cell but its own columns fix it'),
          (H2H, 'The real misses are 25 values lost to the `missing:raw_unit` bug')]),
    C('CU6', 'A plausibility limit refused real fast enzymes', 'conversion and units', 'FR',
      'no PMID on file: measured catalase and carbonic anhydrase kcat values above 1e7 s^-1',
      'code: the kcat ceiling raised to 1e8 s^-1', [CC], '12 values in 4 papers', 'rule', ledger=[27],
      rule='daced49'),
    C('CU7', 'Derived kcat/Km shown beside a printed bound', 'conversion and units', 'FA',
      "10390216: aztreonam showed a calculated 33 beside the printed '<0.02 µM^-1 s^-1'",
      'code: export derives no kcat/Km where the paper prints it only as a bound or not detected; recheck flags any '
      'such record', [CC], 'not counted', 'rule', ledger=['calcbound'], rule='4767cad'),
    C('CU8', 'Km per mass concentration refused as unknown', 'conversion and units', 'FR',
      'no PMID on file: a polysaccharide\'s Km printed in mg/ml',
      'code (units.MASS_UNIT): such a Km stays in mg/mL and its kcat/Km in mL mg^-1 s^-1, in their own export columns, '
      'never compared with database values or derived',
      [CV], 'not counted', 'rule', ledger=['mass'], rule='66d9143',
      ev=[('CLAUDE.md', 'A Km printed over a mass concentration (mg/ml, µg/ml, g/l: polymer substrates) stays in mg/mL')]),
    # ======================================================================================= the databases
    C('DB1', 'Database entries imported as catalogue rows', 'the databases', 'FA',
      'no PMID on file: the old catalogue grew to 159,446 rows by importing database entries; 16,966 were paper-checked',
      'design: database values are a paper list and a cross-check, never catalogue rows or evidence; they are compared '
      'only after a paper is read, and a difference is decided from the paper',
      [DBC, R], 'the old catalogue: 159,446 rows, 16,966 paper-checked; 5 of the 9 errors Codex found in its certified '
      'rows sit verbatim in BRENDA, OED or SKiD', 'rule', novelty='old system',
      inherited='old system: the old catalogue was grown by importing database entries', rule='f171ab3',
      ev=[('CLAUDE.md', 'Old "broad" = the old catalog (159,446 rows; only 16,966 paper-checked), grown by importing database entries.'),
          ('CLAUDE.md', 'Database rows are a paper list and a cross-check, never catalog rows.'),
          ('CLAUDE.md', '5 of the 9 errors Codex found in old certified rows sit verbatim in BRENDA/OED/SKiD')]),
    C('DB2', 'Agents use database values as evidence', 'the databases', 'PROC',
      'no PMID on file: 306 papers whose reader or verifier opened database values before the rule',
      'read.md and verify.md "Read blind" name every forbidden file (12 Oct); auditors read blind (14 Oct); '
      'human_review.blind_check scans every agent transcript before a paper\'s first add; the 303 exposed papers were '
      'read again blind; the agreement headline counts blind papers only',
      [R, V, AU, CC],
      '306 papers exposed before the rule; 303 read again blind: 122 of 17,380 earlier values wrong (49 corrected, 73 '
      'dropped); 8 audit verdicts that cited BRENDA',
      'rule', ledger=[28, 34], rule='8b6b4db',
      ev=[('prompts/read.md', 'Read blind: use only this paper'),
          ('.claude/workflows/catlog-audit.js', 'Audit blind, from the paper alone: never open database values'),
          ('tools/human_review.py', 'def blind_check(full=False):'),
          (BLIND, 'Earlier values found wrong: 122 of 17,380 (0.7%)')]),
    C('DB3', 'Database labels worded otherwise fail the comparison', 'the databases', 'PROC',
      "16990279: UniProt's 'with magnesium ions as cofactor' did not match the paper's 'Mg2+'",
      "code (dbcompare): metal ions under one name; BRENDA's typos read as the word", [DBC],
      '3 papers (16990279, 30054521, 2819035)', 'rule', ledger=['dblabels'], rule='07e2c9b',
      ev=[('git:07e2c9b', "UniProt 'with magnesium ions as cofactor' = 'Mg(2+)' = paper 'Mg2+'/'MgCl2'), so a database check of 16990279")]),
    C('DB4', "UniProt's EC annotation differs from the paper's", 'the databases', 'FA',
      'no PMID on file: UniProt now gives human ADH1B only EC 1.1.1.105',
      "code (sequences): an EC mismatch on a name-matched entry is flagged CHECK: in uniprot_how, not blanked",
      [CC], 'not counted (an old-system lesson)', 'flag kept as printed', novelty='old system',
      inherited='old system: the "EC-mismatch flag on name-matched UniProt entries" is among the "Old-system lessons" (8 Oct)',
      rule='3c3e3c6',
      ev=[('git:3c3e3c6', 'EC-mismatch flag on name-matched UniProt entries'),
          ('CLAUDE.md', 'an EC mismatch is flagged `CHECK:` in `uniprot_how`, not blanked, because UniProt re-annotates: human ADH1B is now only EC 1.1.1.105')]),
    # ======================================================================================== the process
    C('PR1', 'Reading agents die mid-paper', 'the process', 'PROC',
      '19261311: the safety filter stopped the reader of a toxin enzyme paper',
      'workflow: tasks open with the curation context; a dead agent is retried once on another model; 3 dead agents in '
      'a row stop the lanes; reread keeps an unverified read; a paper whose agents died 3 times is parked',
      [CC], '24 papers re-read for nothing; 20 valid reads lost', 'rule', ledger=[14, 16], novelty='old system',
      inherited='old system: "dead agents retried on Sonnet" is among the "Old-system lessons" (8 Oct)', rule='3c3e3c6',
      ev=[('git:3c3e3c6', 'dead agents retried on Sonnet'),
          ('.claude/workflows/catlog-batch.js', "Leading with what the work is keeps the model's safety filter from stopping readers of toxin/pathogen enzyme papers."),
          ('CLAUDE.md', 'A paper whose agents died 3 times is `parked`')]),
    C('PR2', "Agent's mid-run model fallback not recorded", 'the process', 'PROC',
      'no PMID on file: work files named claude-opus-5-5 while the transcript shows claude-opus-5',
      "code: tools/provenance_backfill.py names every model an agent's tool calls used (22 Oct); add reads the model "
      "from the agent's transcript, 'A>B' for a switch (1 Nov, catlog.agent_model())",
      [CC], '112 of 599 agents (29 Oct-1 Nov); at least 1,056 reader and 1,290 verifier stamps in 81 papers hide a '
      'switch, not corrected (the owner\'s decision)', 'rule', ledger=['model'], rule='7f63a56',
      ev=[('catlog.py', 'def agent_model(path):'),
          ('CLAUDE.md', "'A>B' when the agent switched model mid-run")]),
    C('PR3', 'Values carry no record of what read them', 'the process', 'PROC',
      'no PMID on file: values added before 21 Oct had no model, prompt or commit stamp',
      'code: add stamps reader and verifier models, prompt and task hashes and the commit; each prompt hash saves its '
      'text; provenance_backfill.py reconstructs earlier stamps from transcripts and git, and keeps a stamp once its '
      'transcript is archived',
      [CC], '92.2% of the 240,169 values stored on 31 Oct were added before the stamps', 'rule', ledger=['stamps'],
      rule='76a824c',
      ev=[('git:47618c8', 'provenance backfill keeps an earlier line exactly once a transcript it names is gone')]),
    C('PR4', 'Parallel agents share one scratch folder', 'the process', 'PROC',
      "17692452: another paper's build.py rewrote its read file",
      'workflow: each agent keeps scratch files in a folder named by its role and paper', [CC], '1 paper',
      'rule', ledger=['scratch'], rule='5aad090'),
    C('PR5', 'Test-set papers read by the development loop', 'the process', 'PROC',
      'no PMID on file: 20 of the 374 held-out papers read since 22 Oct',
      'code: sources/holdout_locked.txt, read by catlog.locked(); next, the censored pass, sample, dbdiff, the sweeps and '
      'review packs leave the locked papers out',
      [CC], '20 of 374 read; 369 locked', 'rule', ledger=['holdout'], rule='16d2764',
      ev=[('CLAUDE.md', 'The method paper\'s test set (the user, 2026-11-01; for the chat that runs the loop)'),
          (FIX31, 'The held-out set for the method paper is 374 papers')]),
    C('PR6', 'Frozen run would write into the development folder', 'the process', 'PROC',
      'no PMID on file: four places named the main folder',
      'workflow: the harness takes its folder as args.root', [CC], '4 hard-coded places', 'rule', ledger=['root'],
      rule='03a9a3a'),
    C('PR7', 'Audit sample or rate on the wrong base', 'the process', 'PROC',
      'no PMID on file: values added while an audit ran fell out of every audit window',
      'code: the audit window starts at the last recorded sample (19 Oct); catlog.FOLLOWUP_AUDITS and lines ending '
      'targeted=paper stay out of the random rate (22 Oct); the site says who checked what over which base',
      [CC, PE], '1,900 values never sampled; 173 reader and 130 checker-only exposed papers relabelled', 'rule',
      ledger=[43, 'base'], rule='c25875c',
      ev=[('catlog.py', 'FOLLOWUP_AUDITS = (')]),
    C('PR8', "An audit's unit correction lost or misrecorded", 'the process', 'FA',
      "21094652: '10^-6 M^-1 s^-1' cut to '10^-6' and logged as corrected",
      "code: unitfix (an audit corrects a misprinted unit instead of dropping the value, 12 Oct); audit-record takes the "
      'shortest leading words the units code accepts and logs no fix that did not apply (23 Oct)',
      [CC, AU], '28 values corrected and 16 reprints dropped (12 Oct); 21094652\'s rows (23 Oct)', 'rule',
      ledger=[24, 'auditcut'], rule='14d5288',
      ev=[('catlog.py', 'def cmd_unitfix(ufc, why, *ids):')]),
    C('PR9', "Exposure monitor's false alarms and missed patterns", 'the process', 'PROC',
      "7011386: its reader's grep of human_review on 11 Oct went unflagged until 26 Oct (the paper was counted exposed anyway)",
      'code: blind_check ignores a file named only to leave it out and flags the folder named without its slash; a full '
      'rescan before transcripts are archived',
      [CC], '6 false alarms (papers exposed 310 to 307); 1 missed case; 15 exposure lines added by a rescan', 'rule',
      ledger=['monitor'], rule='d6f143d',
      ev=[('git:473e343', "7011386's reader grepping human_review on 10-11 (that paper was already counted as exposed)")]),
    C('PR10', "A sweep's refuter votes were dropped", 'the process', 'PROC',
      '15797234: refuters\' remarks in the wrong field dropped their votes',
      "workflow: catlog-scale counts a refuter's vote whenever it returns rows", [CC],
      '9 rows of 15797234 listed as not surviving', 'rule', ledger=['refvotes'], rule='18d5833'),
    C('PR11', "An evidence check's regex hung the loop", 'the process', 'PROC',
      'no PMID on file: dbcheck-record hung for 20 minutes',
      'code: the evidence-check regex matches whole words', [CC], 'dbcheck-record hung 20 min twice', 'rule',
      ledger=[41], rule='327388a'),
    C('PR12', 'One-page items treated as previews', 'the process', 'PROC',
      'no PMID on file: one-page meeting abstracts sent back to download',
      'code: a one-page PDF of a single-page item is read', [CC], '18 papers sent back to download', 'rule',
      ledger=[36], rule='00cb192'),
    C('PR13', 'Two writers at once lost catalogue rows', 'the process', 'PROC',
      'no PMID on file: a drop and an add writing at the same time',
      'code: add and drop hold a lock on the catalogue; a cut-off last line is repaired before the next write', [CC],
      'not counted', 'rule', ledger=['writers'], rule='099673a'),
    C('PR14', 'Censored-value scan misses plain wording', 'the process', 'FR',
      "16166087: 'the purified K46A mutant protein was inactive' matched no phrase",
      'agents judge snippets around wider wordings and the papers they find join the re-read list; OPEN: a whole-paper '
      'check of the papers judged no, and of those with no wording',
      [AU, CC], '14 of 36 sampled papers with no such wording had one; so had 14 of 45 judged no', 'open',
      ledger=['ndscan'], rule='ad19399',
      ev=[('tools/censored_scan.py', 'snippets around wider wordings for the papers the list misses')]),
    C('PR15', 'Correction records pasted from another paper', 'the process', 'FA',
      "no PMID on file: a row_id pasted from another paper's value",
      "code: a correction row whose PMID is not its value's paper, or whose number the database does not list, is "
      'listed and not used; dates must be YYYY-MM-DD', [CC, DBC], 'not counted', 'rule', ledger=['pasted'],
      rule='16948c4'),
]


# ------------------------------------------------------------- fixes of the independent check (2 November 2026)
# TAXONOMY_CHECK.md gives each line's verdict and the evidence; the classes above are left as built and changed here,
# so the builder's first version and the check's changes stay apart. rule_commit means the first commit of the guard:
# for an old-system class the commit that put the old lesson into v2 (by 8 October, as its definition says).
def _cls(i):
    return next(c for c in CLASSES if c['id'] == i)


def fix(i, ev=(), ledger_add=(), ledger_drop=(), more=(), guard_add='', **kw):
    k = _cls(i)
    for key, v in kw.items():
        assert key in k, (i, key)
        k[key] = v
    if guard_add:
        k['guard'] += guard_add
    k['ev'] += list(ev)
    k['ledger'] = [x for x in k['ledger'] if x not in ledger_drop] + list(ledger_add)
    k['more'] += list(more)


def insert_after(after, cls):
    CLASSES.insert(next(n for n, c in enumerate(CLASSES) if c['id'] == after) + 1, cls)


fix('PP1', values="{pp1_values} values in {pp1_papers} papers unit-corrected from the paper's own numbers, 12-23 Oct "
                  "({unitfix} log.tsv unitfix lines, the 15 restorations of the spaced exponent left out, and "
                  "25514023's 11 brought back through recover on 12 Oct): mostly whole misprinted columns, a few single "
                  "cells (18700786, 31226373, NPD832847D) and kcat/Km columns computed with the wrong Km unit "
                  "(20302306, 21094652); 22 checked agent cases of this kind",
    ev=[('log.tsv', '25514023 recover kept=11 dup=0 rejected=0 still_rejected=0'),
        ('git:14d5288', '25514023 Table 6 kcat x11 back in s-1 (were dropped as 60x low)')])
fix('PP2', rule='f171ab3',
    guard="read.md and verify.md rule 7: only values measured in this paper (7 Oct); a reference column identical to "
          "the cited paper's table is skipped (14 Oct); tools/reprint_pairs.py lists papers sharing printed cells, "
          "each pair checked cell by cell with an independent refuter and two more judges; audits",
    ev=[('gitfile:f171ab3:prompts/read.md', 'Only values measured in THIS paper.')])
fix('PP4', first=('2026-10-09', 'verifier', "verifier (20701311: Table 1's '9.5e2' a typographic error its own Table 2 "
                                            "contradicts; 19271774)"),
    more=[('2026-10-20', 'sweep', 'scale sweep (lone typo cells of 9843375, 16930134 and 28129670: stored as printed '
                                  'with the closure note, or already converted right)',
           [('work/scale_9843375.json', 'lone typo, stored as printed'),
            ('work/scale_16930134.json', 'nothing printed decides which')])],
    rule='f171ab3',
    guard="verify.md rule 3: a kcat/Km 5x or more off kcat ÷ Km that the paper cannot settle is rejected (7 Oct); the "
          "Vmax sweep finds a slipped kcat with no printed kcat/Km to close (23 Oct); a cell a power of ten or more off "
          "its own row's printed rate is a slip and is rejected (31 Oct); code refuses values past its physical limits",
    values="1 kcat dropped as a cell slip (21443518, 24 Oct); verifiers refused such cells from 9 Oct (20701311, "
           "19271774), counted among the 142 refused as 'misprint, copy slip or impossible number', a reason class "
           "PP1, PP3, PP5, PP6 and RA9 share; lone typos nothing printed decides stay as printed with the closure "
           "note (9843375, 16930134)",
    ev=[('rejected.jsonl', "is printed, but it is a typographic error - the paper's own Table 2 gives kcat/Km = 1.7e1"),
        ('rejected.jsonl', 'is a typo the paper itself contradicts'),
        ('gitfile:f171ab3:prompts/verify.md', 'A kcat/Km that is ≥5× away from'),
        ('git:8d01c44', "21443518's '505215 s-1'"),
        ('paper/figures/supp_agent_flow/flow_counts.py', "('misprint, copy slip or impossible number', r'header|misprint|diffusion|cannot mean")])
fix('PP5', values="{implausible} review lines by 2 Nov (101 on 24 Oct, none a CatLog misread; 10 for 36756200 on "
                  "31 Oct); 47 derived values flagged (41 in 11779198)",
    ev=[('git:b41b8ef', 'with review lines flagging the ten records past the diffusion ceiling')])
fix('PP6', values="{ratio_recovered} values recovered on 10 Oct ({ratio_code} that code had rejected for the ratio, 77 "
                  "that verifiers had rejected only for it); 3 papers left as printed by the Vmax check; 6 checked "
                  "agent cases of this kind",
    ev=[('paper/manuscript/supp_note_1_system.md', 'brought back 113 values, 36 that code had rejected and 77 that '
                                                   'verifiers had rejected only for the mismatch'),
        ('git:12770bd', 'A printed kcat/Km that disagrees with kcat / Km drops nothing (user decision)'),
        ('git:27ad550', 'Recovered 85 values (77 ratio-only verifier rejections, 6 pH-8.3 column values, 2 split '
                        'decimals)')])
fix('PP7', first=('2026-10-07', 'verifier', 'verifier (30232563: a retracted article, all 36 rows rejected)'),
    ev=[('log.tsv', '2026-10-07 17:22 30232563 add kept=0 dup=0 rejected=36')])
fix('PP8', first=('2026-10-28', 'verifier', "verifier (27100881: its 'wild-type BglTM' is the group's K20S/K117S/K165S "
                                            "triple mutant)"),
    more=[('2026-10-29', 'verifier', 'verifier (40420686: the printed accession P33232 cannot be the NADH-linked '
                                     'enzyme assayed)',
           [('paper/04_supplementary_case_tables.md', 'Verifier, own reasoning: with no lookup call it named P33232 '
                                                      'as lldD')]),
          ('2026-10-29', 'reader', 'reader (19686854: the Methods report PCR-introduced Y378C and A134T)', [])],
    guard="the reader's or verifier's own judgement; no rule covers mutations introduced in cloning, an engineered "
          "construct called wild type, or a printed accession that cannot be the assayed enzyme",
    values="3 checked agent cases: 27100881's 12 values kept with their variants fixed, 40420686's 2 values rejected, "
           "19686854's 8 values stored with their mutations",
    ev=[('paper/04_supplementary_case_tables.md', "The group's K20S/K117S/K165S triple mutant."),
        ('log.tsv', '2026-10-28 20:30 27100881 add kept=12'),
        ('log.tsv', '2026-10-29 07:37 40420686 add kept=6'),
        ('log.tsv', '2026-10-29 07:38 19686854 add kept=8')])
fix('TL1', more=[('2026-10-14', 'reader', 'reader (2007114: the text layer of a scan heads the Km columns mM; no '
                                          'warning fired)',
                  [(BOXES, '(reader, 2026-10-14, `work/old/2007114.read.1793276463.json`, `note`)')])],
    values='15 of 120 sampled library PDFs; 384 values flagged printed_unit_prefix_differs (13 Oct)')
fix('TL2', rule='3c3e3c6')
fix('TL4', example="10712619: a font drew ± as two glyphs ('4.1 ^ <U+008A> 0.4' is 4.1 ± 0.4) and left control "
                   "characters inside numbers; one PDF printed 2.6 as 2<U+008A>.6",
    ev=[('tools/units.py', 'are both 4.1 ± 0.4 (PMID 10712619)'),
        ('log.tsv', 'control characters inside numbers now cleaned')])
fix('TL6', values="4 values (4622304), 5 (10021417); 32 values recovered (hyphens); 6 values of 18783250 whose pH "
                  "column the OCR garbled, refused as conflicts on 9 Oct, back on 10 Oct without a pH (IP5)",
    ev=[('log.tsv', '18783250 recover kept=6 dup=0 rejected=0 still_rejected=0 reason=conflicts with accepted row')])
fix('TL7', first=('2026-10-12', 'code check', "code check (6354095: 8 confirmed Km values refused value_not_in_quote, "
                                              "its OCR text running Table III's cells together)"),
    example="6354095: Elsevier's OCR runs Table III's cells together ('0.0660.315'); 8 confirmed Km values refused "
            "until its full PDF was filed (20 Oct)",
    ev=[('log.tsv', '2026-10-12 15:18 6354095 add kept=28 dup=0 rejected=8'),
        ('git:8d28860', '6354095 OCR-merged cells'),
        ('log.tsv', '2026-10-20 15:12 6354095 add kept=32 dup=4')])
fix('TL9', values="125 texts rebuilt; the 12 done papers among them re-read: 23 values added, no conflict; "
                  "{break_copies} of the 23 copy values the first read had stored (42456964 10, 21819071 2; this "
                  "check), so {break_recovered} were recovered",
    ev=[(TWICE, '42456964')])
fix('RA3', values='429 values refused as partial constants by 28 Oct (74 by verifiers, 355 by audits and sweeps, the '
                  '227 dropped on 23 Oct among them)',
    ev=[('paper/figures/supp_agent_flow/flow_counts.py', "('partial constant of a branched reaction', r'partial|per-product")])
fix('RA1', rule='f171ab3',
    ev=[('gitfile:f171ab3:prompts/read.md', 'Hill constants (K0.5, S0.5, or an "apparent Km" from a Hill fit with n '
                                            'clearly ≠ 1), Ki, Kd, Kact, IC50,')])
fix('RA5', rule='f171ab3', ledger_add=[5],
    ev=[('gitfile:f171ab3:prompts/verify.md', 'A raw value missing a printed ± is a `fix`.')])
fix('RA8', ledger_add=['verdict13', 'override42'], rule='7272a97',
    guard="code: a recorded correction whose database row is labelled for another measurement, or whose cause the "
          "numbers do not support, is listed and not used (13 Oct); restore brings back a value an audit dropped when "
          "the paper shows the auditor misread it; every drop of a follow-up needs two auditors agreeing; "
          "dbcheck-record flags evidence the paper does not print; dbdiff --reask; a catlog_wrong value an audit kept "
          "is asked again; the scale check reviews every reader or verifier unit override",
    values="33 recorded corrections re-checked (13 Oct); 42228390's override replaced (19 Oct); 1 value restored "
           "(41835576); 8 rows of 19211556 asked again; 1 row of 25016016 reopened; 4 values of 40723313 back to the "
           "printed unit (2 Nov)")
fix('IP3', ledger_add=['twice'], status='open',
    more=[('2026-10-11', 'operator', 'operator (21 values a paper prints twice dropped: Table 1 copies of Table 3 in '
                                     '10712619, zinc-free points repeating Table IV in 15863831, prose restating a '
                                     'table cell)',
           [('git:13c37e1', "21 reprinted values dropped (10712619: Table 1 copies of Table 3's complete sets")])],
    guard_add="; OPEN: a copy whose substrate is respelled (Na_2S for Na2S, a hyphen) or whose quote comes from another "
              "text (an OCR read against the PDF's, a sentence against the rebuilt table) is not paired (46 values "
              "in 5 papers on 2 Nov)",
    values="{dups_dropped} re-read copies dropped (log.tsv, 11-30 Oct: {dups_by_day}); {reworded} copies refused at add "
           "(log.tsv reworded_duplicate); 293 values refused as printed twice in one paper (269 by verifiers); "
           "{twice} values in {twice_papers} papers still stored twice on 2 Nov (this check)")
fix('IP4', values="{conflicts} conflicts logged (log.tsv): {conflicts_blind} from the blind re-read, each judged from "
                  "the paper with 3 refuters; {conflicts_slot} of 9 Oct and {conflicts_qual} of 14 Oct came from slot "
                  "and qualifier rules (IP5, CU4) and were settled by fixing them",
    ev=[(BLIND, 'Conflicts (63, conflicts.json): one judge per paper decided from the paper which reading is right')])
fix('IP5', cls='Different measurements forced into one slot',
    example="3264155: 17 values of E. cloacae strain 908R refused as conflicts with strain P99; 21169366: 18 "
            "Arabidopsis paralog values (At3g04000, At3g61220)",
    guard="code: the printed gene and strain are part of the slot and the grouping (9 Oct); a blanked pH or "
          "temperature still separates slots (10 Oct); two rows printing the same number for different variants or "
          "substrates are different measurements, and a different printed pH or temperature makes a new one (11 Oct); "
          "the duplicate report skips a quote that is only the printed cell (19 Oct)",
    values="35 values of 2 papers refused as conflicts on 9 Oct (21169366's 18 paralog values, 3264155's 17 of strain "
           "908R), back the same day; 6 values of 18783250 back on 10 Oct",
    ledger_add=[21, 'phblank', 'dupreport'],
    ev=[('log.tsv', '17 values of strain 908R rejected as conflicts with strain P99: slot ignored the printed strain; '
                    'fixed'),
        ('log.tsv', '18 paralog values (At3g04000, At3g61220) rejected as conflicts: slot ignored the printed gene; '
                    'fixed'),
        ('git:700b56d', '(it flagged I164A ampicillin as a duplicate of I164A penicillin G)'),
        ('git:16a5529', 'twin() treats a different printed pH or temperature as a new measurement')])
fix('IP6', novelty='new', inherited='',
    guard_add=". The 8 Oct prompt, from an old-system lesson, had told readers to keep a form's name in the variant field",
    ev=[('gitfile:3c3e3c6:prompts/read.md', 'isoenzyme keeps its printed name (`β2β2`, `ADH1B*2`, `isozyme II`, '
                                            '`Form I`): never `wild type` unless the paper')])
fix('IP7', first=('2026-10-11', 'reviewer', 'website review, round 2 (natural forms sent a borrowed sequence)'),
    rule='c794ecf',
    guard="code (sequences): a form gets a sequence only from an entry of its own, not one shared with another form "
          "of the paper (10-11 Oct); a checked natural-form line drives this guard for forms named in enzyme (23 Oct)",
    ev=[('git:c794ecf', 'natural forms send no borrowed sequence'),
        ('git:86b8807', 'a sequence only from an entry of their own')])
fix('IP11', rule='f171ab3',
    ev=[('gitfile:f171ab3:prompts/verify.md', "a value must sit under its own header and on its own variant's line")])
fix('IP17', rule='c1bf801',
    ev=[('gitfile:c1bf801:tools/structures.py', "Abbreviations are paper-local ('SA' is shikimate in one paper, "
                                                "salicylic acid in another)")])
fix('IP18', rule='f171ab3',
    more=[('2026-10-09', 'operator', "operator (7896799: PubMed's DOI fetched the preceding article)",
           [('log.tsv', "PubMed's DOI 6595 is the preceding article")]),
          ('2026-10-10', 'operator', "operator (a no-PMID title search matched cathepsin L's paper for cathepsin B's)",
           [('git:a0b5040', 'a title-search match needs the same volume/page or an exact title with the same short '
                            'naming tokens (cathepsin B vs L)')])],
    ev=[('gitfile:f171ab3:prompts/read.md', 'First confirm the text is the paper you were given (title/authors on the '
                                            'first page).')])
fix('CU4', first=('2026-10-07', 'code check', "code check (39353521: the unit '×10^3, s^-1' refused as unknown)"),
    more=[('2026-10-09', 'code check', "code check (9305962: a decimal fraction printed with SI digit grouping, "
                                       "'0.000 03')",
           [('git:0187577', "a decimal fraction printed with SI digit grouping ('0.000 03') is one number"),
            ('tools/units.py', '(PMID 9305962, Table 2)')]),
          ('2026-10-10', 'operator', "operator ('596. 4' read as 596.4: 2 split decimals recovered)",
           [('git:27ad550', "'596. 4' reads as 596.4")])],
    rule='054cd95',
    guard="code: a comma after a multiplier and SI digit grouping parse (7-9 Oct); 'apparent molecular weight' is no "
          "per-value qualifier; a bracketed interval goes with its value; a caret multiplier converts; ≪ and ≫ are "
          "bounds; recover re-adds rows a changed rule no longer refuses",
    values='21 values (7470464); 5 (36698977); 9 (42249657); 2 (596. 4); 1 (18669639)',
    ev=[('git:054cd95', 'units accept commas after a multiplier'),
        ('rejected.jsonl', 'unknown_kcat_unit:×10^3, s^{−1}')])
fix('CU5', ledger_drop=['unitremark'],
    guard="code: an unprinted pH or temperature is left empty (8 Oct), organism is optional (9 Oct), a verifier's "
          "unit_for_conversion stands in for an empty raw_unit (23 Oct); read.md: write the unit the paper's own "
          "columns fix, the reason in metric_note")
fix('CU8', values='about 100 values in 12 papers rejected as unknown units by 12 Oct')
fix('DB2', rule='bc442f7',
    ev=[('git:bc442f7', 'readers and verifiers read blind (no database values, earlier-catalog files, review data or '
                        'queue notes)')])
fix('PR1', more=[('2026-10-11', 'operator', 'operator (57 papers claimed by chats that had ended sat in reading for '
                                            'hours)',
                  [('git:2974fa8', '57 such claims sat for hours on 2026-10-11')])],
    guard_add='; next releases a claim whose chat ended (3 h in reading, no work file in the last hour)')
fix('PR2', ledger_add=['model31'],
    values="112 of 599 agents (29 Oct-1 Nov); at least 1,056 reader and 1,290 verifier stamps in 81 papers hide a "
           "switch and are uncorrected: only their transcripts can correct them, before the next /archive, and that "
           "call is the owner's",
    ev=[(REPLY, "That decision is the user's.")])
fix('PR8', values="28 values corrected on 12 Oct (16 by unitfix lines, 12 brought back through recover); 21094652's "
                  "rows (23 Oct)")
fix('PR10', cls="Checking agents' verdicts lost before recording",
    guard="code: audit verdicts go to a file that audit-record records (11 Oct); workflow: catlog-scale counts a "
          "refuter's vote whenever it returns rows (20 Oct)",
    values='2 audits (11 Oct); 9 rows of 15797234 listed as not surviving (20 Oct)', rule='5054407',
    ledger_add=['verdictlost'])
fix('PR12', first=('2026-10-13', 'operator', 'operator (filing: one-page meeting abstracts of Biochem J and Biochem Soc '
                                             'Trans taken for previews)'),
    rule='fb083c4', guard='code: a one-page PDF of a single-page item is filed (13 Oct) and read (14 Oct)',
    ev=[('git:fb083c4', 'a one-page PDF is the whole item when PubMed prints a single page (Biochem J 15P, Biochem Soc '
                        'Trans 128S meeting abstracts), not a preview')])
fix('PR15', cls='Correction records misattached or malformed', ledger_add=['swap'],
    guard_add='; dbcheck-record uses a verdict only when each database it names has that number for that row_id in the '
              'task (14 Oct)')

insert_after('TL10', C(
    'TL11', '° drawn as 8 hides a printed temperature', 'the PDF text layer or OCR', 'FR',
    "20564561: its PDF prints 'at 378' for 37 °C, so code left the temperature of 66 values empty",
    "code: check() reads '378C' (8 Oct) and 'at 378' (11 Oct) as 37 °C; the glyph warning names ° as '8', and readers "
    "then take conditions from the page image",
    [CC, R], '66 values of 20564561 got their 37 °C back (11 Oct)', 'rule', ledger=['degree'], novelty='old system',
    inherited="old system: 'glyph units in code' are among the \"Old-system lessons\" (8 Oct), whose glyph warning "
              "knows ° as '8'",
    rule='3c3e3c6',
    ev=[('git:3c3e3c6', 'bare x10 / M^-2 / glyph units in code'),
        ('gitfile:3c3e3c6:tools/fetch.py', "as '8' (378C is 37"),
        ('catlog.py', "a PDF text layer that prints ° as 8: '378C', and 'at 378' where the paper wrote 'at 37°' with no C")]))
insert_after('TL11', C(
    'TL12', 'Values printed only in a supplement', 'the PDF text layer or OCR', 'FR',
    '27342312: the main text holds 3 values; BRENDA cites 689 from its Supplemental Table S1',
    'read.md: the reader sets needs_supplement and add marks the paper; catlog.py supp fetches open-access '
    'supplements, the download lane the rest, and the paper is read again with them; verify.md: a supplement missing '
    'from the text is not "no values", and the paper stays incomplete',
    [R, V, CC], '689 values of 27342312; 266 papers waiting for a supplement on 2 Nov (status)', 'rule',
    ledger=['supp'], rule='b11d975',
    ev=[('prompts/read.md', 'If kinetic values the paper measured are only in supplementary material that is NOT in '
                            'the text you were given'),
        ('prompts/verify.md', 'A preview, a missing table or a supplement that is not in the text is not "no values"'),
        ('CLAUDE.md', 'when values are only in supplementary material, the reader sets `needs_supplement`')]))
insert_after('RA13', C(
    'RA14', 'A remark written into the unit field', 'the reading agent', 'FA',
    "no PMID on file: the reason for an unprinted unit written into raw_unit, shown as the paper's printed unit",
    'read.md: raw_unit holds the unit only, the reason for a unit the paper does not print goes in metric_note '
    '(30 Oct); review packs leave a remark inside a printed unit out of the shown text',
    [R], 'not counted', 'rule', ledger=['unitremark'], rule='70394a4'))
insert_after('IP19', C(
    'IP20', 'Title check turned away the right paper', 'identity and pairing', 'FR',
    "25183: the OCR of a 1970s scan prints 'foenum' as 'foenurn', so the right PDF was refused",
    "code (title check): PubMed's English title and the original title both pass (8 Oct); Greek letters spelled out "
    "(17beta = 17β) and a JATS file that names the paper's PMID pass (9 Oct); OCR's 'rn' reads as 'm' (10 Oct)",
    [CC], "not counted (25183's PDF, 10 Oct)", 'rule', ledger=['title'], rule='099673a',
    ev=[('CLAUDE.md', 'the filter or the title check is too strict')]))
insert_after('DB4', C(
    'DB5', 'A database EC taken from another enzyme', 'the databases', 'FA',
    "20549272: BRENDA files the paper's MMP-2 values under MMP-14's EC",
    "code (export, database_ec): no database EC for an enzyme when another enzyme of the paper carries it and this "
    "one's own values do not show it strongly; an EC that fits several EC-less enzymes of a paper whose values sit "
    "under two or more ECs goes to none; ec_source says where an EC came from",
    [CC], '4 enzymes on the site (CPB, MMP-2/9, CelB, lipoamidase; 10 Oct); 20549272, 26002966', 'rule',
    ledger=['dbec'], rule='a1b9760',
    ev=[('CLAUDE.md', "an EC the paper does not print and UniProt does not give taken from the databases' entries for "
                      "that paper's own values")]))
insert_after('PR15', C(
    'PR16', 'Recover re-added values without their unit fix', 'the process', 'FA',
    '16684501: a kcat/Km brought back with its ×10^-5 header read the other way, about 10^10 off',
    "none in code: recover re-checks a row only as add does; the two values were dropped by hand, and 16684501's came "
    "back with its unit through unitfix",
    [CC], '2 values dropped (11 Oct)', 'open', ledger=['recover']))
insert_after('PR16', C(
    'PR17', 'Comparison misstates what a database lists', 'the process', 'FA',
    "30926626: code called 9 database kcat values wrong where the database's number, not CatLog's, closes with "
    "CatLog's own Km and kcat/Km",
    "code (dbcompare): the number nearest an exact factor pairs; each database named with its own number; databases "
    "grouped only on the same printed number; a database number called wrong only when the paper's own kcat ÷ Km "
    "supports CatLog's (13-15 Oct)",
    [DBC], "49 pairings in 16 papers; 21 of 3,721 'X lists N' statements; 9 kcat values of 30926626 (13 Oct)",
    'rule', ledger=['cmp', 'exactfactor'], rule='8e81d55'))
insert_after('PR17', C(
    'PR18', 'Comparison with reviewers missed same measurements', 'the process', 'PROC',
    "10514444: the reviewed human ADH4 Km went unmatched, one side naming the organism 'human' and the other its binomial",
    "code (review compare): substrates matched by structure (InChIKey, stereo, tautomers) and v2's own name "
    "expansions, isoform and gene names, renamed genera, current accessions, organism binomials",
    [CC], 'agreement 43% -> 61%, stated values found 20 -> 43 of 50 (9 Oct)', 'rule', ledger=['reviewcmp'],
    rule='be64c71'))


# ------------------------------------------------- later rules (CRITIQUE_1.md change 5, 2 November 2026)
# rule_commit is a class's first rule. LATER lists every later commit that changed the class's check (a prompt rule, a
# code check, a sweep), mostly the day it was found again; each is asserted by a needle in its commit message, and its
# date must not precede the first rule. The rule_dates column carries the first rule and these, in time order. Built
# from `git log` and the classes' sources and guard texts by the figure's builder; not yet checked by a second agent.
LATER = {
    'PP1': [('14d5288', 'unitfix corrects a misprinted unit instead of dropping the value'),
            ('6d851aa', 'tools/scale_sweep.py lists measurements whose printed kcat/Km misses kcat ÷ Km by a unit factor'),
            ('d5812ab', "stored kcat values that disagree with the paper's own printed Vmax"),
            ('c005e33', 'printed maximal rate: misprint unless the paper disagrees with itself')],
    'PP2': [('078ea59', "a mutant table's wild-type column can be an earlier paper's values carried over silently"),
            ('7a59890', 'list paper pairs that may share silently reprinted values')],
    'PP4': [('d5812ab', "stored kcat values that disagree with the paper's own printed Vmax"),
            ('c005e33', 'lone cell: slip')],
    'PP5': [('1e35c79', 'kcat/Km values at the diffusion ceiling carry their paper check')],
    'PP6': [('12770bd', 'A printed kcat/Km that disagrees with kcat / Km drops nothing')],
    'TL1': [('42f8269', 'Condition flag printed_unit_prefix_differs')],
    'TL2': [('768e645', 'Glyph warning for numbers with two decimal points')],
    'TL6': [('7d212bd', "OCR it as a hyphen ('0-34'); read those as decimals"),
            ('768e645', "scans' OCR included")],
    'TL11': [('13c37e1', 'degree sign read as 8')],
    'RA5': [('aa032a4', 'complete a dropped ± from the quote')],
    'RA8': [('3d917ef', 'dbcheck-record flags evidence the paper does not show'),
            ('93eb834', 'corrected only when a fact the paper prints decides it'),
            ('e72b5be', 'bring back a value an audit dropped when the paper shows the auditor misread it'),
            ('be2fb3a', "asks a named paper's recorded database corrections again")],
    'IP3': [('fb30d57', 'recheck reports likely re-read duplicates'),
            ('a5c3d00', 'is still a reworded duplicate'),
            ('8751744', 'lists the same mutations in another order is a duplicate'),
            ('6dde5fa', "add recognises a re-read's copy of an accepted value whose raw unit is spelled otherwise")],
    'IP5': [('4957210', "Keep a species' strains apart in slot and grouping"),
            ('27ad550', 'a blanked pH/temperature still separates slots'),
            ('700b56d', 'Revert the loose re-read twin rule'),
            ('16a5529', 'twin() treats a different printed pH or temperature as a new measurement'),
            ('68ae85c', 'The re-read duplicate report skips a quote that is only the printed cell')],
    'IP7': [('9f9c1fe', 'drives the sequence guard only')],
    'IP9': [('31721e1', 'wrong protein matches')],
    'IP11': [('db38b4d', 'A directed-evolution variant carries the mutations of the gene its round used as template')],
    'IP17': [('ba0d005', 'a ChEBI name shared by different compounds is no Rhea synonym'),
             ('78e1be4', 'abbreviation guard covers peptide and PubChem routes'),
             ('7de1676', "a SABIO-RK or abbreviation hit must fit OPSIN's reading of the printed name"),
             ('31721e1', 'wrong substrate structures')],
    'IP18': [('a0b5040', 'a title-search match needs the same volume/page'),
             ('1eb0882', 'is filed by title only when the title is printed near its top')],
    'CU2': [('b71ed42', 'reads the ± term with its own E exponent'),
            ('70394a4', 'pmfix: take off a ± the printed cell does not carry')],
    'CU4': [('0187577', 'a decimal fraction printed with SI digit grouping'),
            ('27ad550', "'596. 4' reads as 596.4"),
            ('322c01c', "'apparent molecular weight Mr ...' is an assay state"),
            ('df7392d', 'a caret multiplier in a mass-concentration unit'),
            ('20630e5', 'is the value with its confidence interval, not a range'),
            ('5d2fd88', 'A bound printed with a much-less/greater-than sign')],
    'CU5': [('3c6a6b4', 'organism no longer required'),
            ('bdab76f', 'check() lets a unit_for_conversion stand in for an empty raw_unit')],
    'DB2': [('8b6b4db', 'Read blind also excludes catlog_wide'),
            ('c722037', 'Audits read blind')],
    'PR1': [('876844e', 'retry on Sonnet also when an agent reports a problem'),
            ('13c37e1', 'an interrupted read is kept and only verified'),
            ('2974fa8', 'next releases claims a gone chat left behind')],
    'PR2': [('23af857', "Model stamps from the agent's transcript at add")],
    'PR7': [('9eef7ca', 'The audit rate and its 95% interval count the random audit only')],
    'PR8': [('0989102', 'Audits correct misprinted units'),
            ('1b499b3', "audit-record takes an auditor's unit_fix unit as the shortest leading words")],
    'PR10': [('18d5833', "catlog-scale counts a refuter's vote whenever it returns rows")],
    'PR12': [('00cb192', 'a one-page PDF of a single-page item (meeting abstract) is read')],
    'PR15': [('00f1977', 'a row whose date is not YYYY-MM-DD'),
             ('f7289ad', 'a verdict is used only when each database it names has')],
    'PR17': [('4adda8f', 'a recorded correction names its own database number'),
             ('f3cd406', 'groups databases only when they list the same printed number'),
             ('3e25216', 'code never calls a database number wrong that closes'),
             ('393b3b7', "code states a correction only when the paper's own kcat ÷ Km supports")],
}


# ---------------------------------------------------------------------------------------------- counts from files
def log_rows():
    with open(os.path.join(ROOT, 'log.tsv'), encoding='utf-8') as fh:
        for line in fh:
            p = line.rstrip('\n').split('\t')
            if len(p) >= 3 and p[0] < LOG_CUTOFF:
                yield p


def counts():
    c = collections.Counter()
    unitfix_papers = set()
    first_add = {}
    dups = collections.Counter()
    partial_19819898 = 0
    hdr = variant = copies_25495127 = 0
    for p in log_rows():
        ev = p[2]
        if ev == 'unitfix':
            why = p[5] if len(p) > 5 else ''
            if why.startswith('printed unit: units.parse_number'):
                c['unitfix_restore'] += 1
            elif p[0][:10] <= '2026-10-23':
                c['unitfix'] += 1
                unitfix_papers.add(p[1])
            else:
                c['unitfix_later'] += 1
        elif ev in ('reworded_duplicate', 'conflict', 'wrong_paper', 'pmfix', 'limitfix', 'drop_bound'):
            c[ev] += 1
            if ev == 'conflict':
                c['conflict ' + p[0][:10]] += 1
        elif ev == 'recover':  # the check of 2 November: values the ratio rule and unitfix brought back
            kept = int(p[3].split('=')[1]) if len(p) > 3 and p[3].startswith('kept=') else 0
            if p[0].startswith('2026-10-10 18:0') and 'reason=ratio_non_closure' in p:
                c['recover_ratio_code'] += kept
            elif p[0].startswith('2026-10-10 18:5'):
                c['recover_1010_late'] += kept
            elif p[0].startswith('2026-10-12 05:05') and p[1] in ('25514023', '16684501'):
                c['recover_unit ' + p[1]] += kept
        elif ev == 'drop':
            why = (p[4] if len(p) > 4 else '').lower()
            if why.startswith(('re-read copy', 're-read duplicate')):
                dups[p[0][:10]] += 1
            if p[1] == '19819898' and 'partial' in why:
                partial_19819898 += 1
            if p[0].startswith('2026-10-11') and "header 's^-1×10^-4' read as ×10^4" in (p[4] if len(p) > 4 else ''):
                hdr += 1
            if p[0].startswith('2026-10-22') and p[1] in ('1537854', '1939081', '15639226') and ('variant' in why or 'enzyme form' in why):
                variant += 1
            if p[0].startswith('2026-10-30') and p[1] == '25495127' and why.startswith('re-read copy'):
                copies_25495127 += 1
        if ev == 'add' and p[1] not in first_add:
            first_add[p[1]] = p[0][:10]
    unknown = 0
    with open(os.path.join(ROOT, 'rejected.jsonl'), encoding='utf-8') as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if str(d.get('checked') or '') >= LOG_CUTOFF:
                continue
            w = ' '.join(map(str, d.get('why') or [])) if isinstance(d.get('why'), list) else str(d.get('why') or '')
            if re.search(r'unknown_(kcat|km|kcatkm)_unit', w):
                unknown += 1
    assert (hdr, variant, copies_25495127) == (60, 8, 83), (hdr, variant, copies_25495127)
    # the check of 2 November
    assert (c['recover_ratio_code'], c['recover_1010_late']) == (36, 85), c
    assert (c['recover_unit 25514023'], c['recover_unit 16684501']) == (11, 1), c
    assert (c['conflict 2026-10-09'], c['conflict 2026-10-14'], c['conflict 2026-10-22']) == (41, 21, 63), c
    c['implausible'] = sum(1 for x in open(os.path.join(ROOT, 'sources/implausible_as_printed.tsv'), encoding='utf-8')
                           if x.strip() and not x.startswith(('#', 'row_id\t')))
    assert c['implausible'] == 111, c['implausible']
    twice = [x.split('\t') for x in open(os.path.join(ROOT, TWICE), encoding='utf-8')
             if x.strip() and not x.startswith(('#', 'pmid\t'))]
    c['twice_by_paper'] = collections.Counter(x[0] for x in twice)
    assert len(twice) == 46 and len(c['twice_by_paper']) == 5, c['twice_by_paper']
    return c, unitfix_papers, first_add, dups, partial_19819898, unknown


# -------------------------------------------------------------------------------------------------------- build
def main():
    # 1. the 22 October ledger, unchanged, its quotes re-checked
    r03 = r03_lines()
    old = list(csv.DictReader(open(os.path.join(ROOT, OLD_LEDGER), encoding='utf-8'), delimiter='\t'))
    assert len(old) == len(r03) == 50, (len(old), len(r03))
    ledger = {}
    for i, (e, row) in enumerate(zip(r03, old), 1):
        date, kind, found, fail, n, rule, srcs, evs = e
        assert ('2026-' + date, kind, found, fail, n, rule) == (row['date'], row['kind'], row['found_by'], row['failure'],
                                                                row['rows'], row['rule']), i
        mapped = [OLD_SRC.get(s, s) for s in srcs]
        found_at = []
        for q in evs:
            hit = next(((s, locate(s, q)) for s in mapped if locate(s, q) is not None), None)
            if hit is None:
                BAD.append((f'ledger {i}', '|'.join(mapped), q[:90]))
            else:
                found_at.append(hit)
        ledger[i] = dict(line=i, date=row['date'], kind=kind, route=OLD_ROUTE[i], found_by=found, failure=fail,
                         rows=n, rule=rule, sources=show(found_at) or row['sources'], ledger='22 Oct',
                         note=OLD_NOTES.get(i, ''))
    # 2. new lines, dated, numbered after the 50
    keys = {}
    for j, e in enumerate(sorted(NEW, key=lambda e: e['date']), 51):
        assert e['route'] in ROUTES and e['kind'] in KINDS, e['key']
        found_at = check(e['ev'], f"new line {e['key']}")
        keys[e['key']] = j
        ledger[j] = dict(line=j, date=e['date'], kind=e['kind'], route=e['route'], found_by=e['found_by'],
                         failure=e['failure'], rows=e['rows'], rule=e['rule'], sources=show(found_at), ledger='v5',
                         note=e['note'])
    # 3. classes
    c, uf_papers, first_add, dups, p19819898, unknown = counts()
    assert c['pmfix'] == 11 and c['limitfix'] == 38 and c['drop_bound'] == 59, c
    assert c['unitfix_restore'] == 15 and c['unitfix'] == 164 and len(uf_papers) == 16, (c, len(uf_papers))
    assert c['unitfix_later'] == 4, c  # 40723313, 2 November (RA8)
    lay = json.load(open(os.path.join(ROOT, LAYERS), encoding='utf-8'))
    assert lay['panel_a']['drawn']['verifier']['values'] == 1870 and '205,517' in lay['panel_a']['bases']['verifier and code checks']
    fill = dict(unitfix=f"{c['unitfix']:,}", unitfix_papers=len(uf_papers), reworded=f"{c['reworded_duplicate']:,}",
                conflicts=f"{c['conflict']:,}", wrong_paper=c['wrong_paper'], unknown_unit=f'{unknown:,}',
                dups_dropped=f"{sum(dups.values()):,}", censored='19,049',
                dups_by_day=', '.join(f"{v:,}" for k, v in sorted(dups.items())))
    assert sum(dups.values()) == 2874, dups
    ledger[keys['blindpartial']]['rows'] = f'{p19819898} values dropped on 22 October (log.tsv)'
    # the check of 2 November
    tw = c['twice_by_paper']
    fill.update(pp1_values=c['unitfix'] + c['recover_unit 25514023'], pp1_papers=len(uf_papers | {'25514023'}),
                implausible=c['implausible'], ratio_code=c['recover_ratio_code'],
                ratio_recovered=c['recover_ratio_code'] + 77,
                conflicts_blind=c['conflict 2026-10-22'], conflicts_slot=c['conflict 2026-10-09'],
                conflicts_qual=c['conflict 2026-10-14'], twice=sum(tw.values()), twice_papers=len(tw),
                twice_by_paper=', '.join(f'{p} {n}' for p, n in sorted(tw.items(), key=lambda x: (-x[1], x[0]))),
                break_copies=tw['42456964'] + tw['21819071'], break_recovered=23 - tw['42456964'] - tw['21819071'])
    assert (fill['pp1_values'], fill['pp1_papers'], fill['ratio_recovered'], fill['break_recovered']) == (175, 17, 113, 11), fill
    ledger[keys['twice']]['rows'] = ledger[keys['twice']]['rows'].format(**fill)
    used = collections.Counter()
    out = []
    seen_ids = set()
    for k in CLASSES:
        assert k['id'] not in seen_ids, k['id']
        seen_ids.add(k['id'])
        words = len(k['cls'].split())
        assert words <= 8, (k['id'], words)
        assert k['origin'] in ORIGINS and k['kind'] in KINDS and k['status'] in STATUSES, k['id']
        assert all(x in LAYER_NAMES for x in k['layers']) and len(set(k['layers'])) == len(k['layers']), k['id']
        assert k['novelty'] in ('new', 'old system'), k['id']
        lines = []
        for x in k['ledger']:
            n = x if isinstance(x, int) else keys[x]
            lines.append(n)
            used[n] += 1
        lines.sort(key=lambda n: (ledger[n]['date'], n))
        events = [(ledger[n]['date'], ledger[n]['route'], n) for n in lines if ledger[n]['route'] != 'old system']
        for m in k['more']:
            assert m[1] in ROUTES and m[1] != 'old system', (k['id'], m)
            events.append((m[0], m[1], m[2]))
        if k['first']:
            events.insert(0, (k['first'][0], k['first'][1], k['first'][2]))
        events.sort(key=lambda e: e[0])
        if k['novelty'] == 'new':
            assert events, k['id']
            first, again = events[0], events[1:]
        else:
            first, again = None, events
        # found column
        def ev_text(e):
            who = e[2] if isinstance(e[2], str) else ledger[e[2]]['found_by']
            return f'{e[0]} ' + (who if who.startswith(e[1]) else f'{e[1]}: {who}')
        if first:
            found = ev_text(first)
        else:
            found = 'before 7 Oct, ' + k['inherited']
        if again:
            found += '; found again ' + '; '.join(ev_text(e) for e in again)
        # sources: ledger lines' sources + the class's own quotes
        own = check(k['ev'] + [q for m in k['more'] for q in m[3]], k['id'])
        srcs = [show(own)] if own else []
        for n in lines:
            srcs.append(ledger[n]['sources'])
        flat = []
        for s in '; '.join(x for x in srcs if x).split('; '):
            if s and s not in flat:
                flat.append(s)
        kinds = collections.Counter(ledger[n]['kind'].replace('PROC', 'PROC') for n in lines)
        if kinds and kinds.most_common(1)[0][0] != k['kind'] and kinds[k['kind']] < kinds.most_common(1)[0][1]:
            print(f"note: {k['id']} kind {k['kind']}, its ledger lines {dict(kinds)}", file=sys.stderr)
        rule_date = git_date(k['rule'])[:10] if k['rule'] else ''
        # every rule date: the first rule, then each later commit that changed the class's check (LATER)
        rds = [(git_date(k['rule']), k['rule'])] if k['rule'] else []
        for h, needle in LATER.get(k['id'], []):
            assert k['rule'], (k['id'], 'a later rule needs a first rule')
            check([('git:' + h, needle)], f"{k['id']} later rule {h}")
            assert git_date(h) >= rds[0][0], (k['id'], h, git_date(h), rds[0])
            rds.append((git_date(h), h))
        rds.sort()
        rule_dates = '; '.join(f'{d[:10]} {h}' for d, h in rds)
        out.append(dict(
            id=k['id'], **{'class': k['cls']}, origin=k['origin'], example=k['example'], found=found, guard=k['guard'],
            guard_layer=k['layers'][0], values=k['values'].format(**fill), status=k['status'], kind=k['kind'],
            novelty=k['novelty'], first_found=first[0] if first else '', found_route=first[1] if first else 'old system',
            found_again='; '.join(f'{e[0]} {e[1]}' for e in again), layers='; '.join(k['layers']),
            rule_commit=k['rule'] or '', rule_date=rule_date, rule_dates=rule_dates,
            ledger_lines=', '.join(str(n) for n in lines), sources='; '.join(flat)))
    missing = [n for n in ledger if not used[n]]
    if missing:
        BAD.append(('ledger lines in no class', str(missing), ''))
    if BAD:
        for b in BAD:
            print('MISSING EVIDENCE:', b, file=sys.stderr)
        sys.exit(1)
    for n in ledger:
        ledger[n]['classes'] = ', '.join(r['id'] for r in out if str(n) in r['ledger_lines'].split(', '))
    return ledger, out, first_add, c, dups, unknown


def write(ledger, rows, first_add, c, dups, unknown):
    # ledger file
    lf = ['line', 'date', 'kind', 'found_route', 'found_by', 'failure', 'rows', 'rule', 'classes', 'ledger', 'note', 'sources']
    with open(os.path.join(HERE, 'error_ledger_v5.tsv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, delimiter='\t', lineterminator='\n')
        w.writerow(lf)
        for n in sorted(ledger):
            L = ledger[n]
            w.writerow([n, L['date'], L['kind'], L['route'], L['found_by'], L['failure'], L['rows'], L['rule'],
                        L['classes'], L['ledger'], L['note'], L['sources']])
    tf = ['id', 'class', 'origin', 'example', 'found', 'guard', 'guard_layer', 'values', 'status', 'kind', 'novelty',
          'first_found', 'found_route', 'found_again', 'layers', 'rule_commit', 'rule_date', 'rule_dates', 'ledger_lines', 'sources']
    with open(os.path.join(HERE, 'taxonomy.tsv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=tf, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    return analysis(ledger, rows, first_add, c, dups, unknown)


def week_of(d, start=dt.date(2026, 10, 7)):
    return (dt.date.fromisoformat(d) - start).days // 7


def analysis(ledger, rows, first_add, c, dups, unknown):
    A = {}
    new = [r for r in rows if r['novelty'] == 'new']
    old = [r for r in rows if r['novelty'] == 'old system']
    A['classes'] = len(rows)
    A['new_in_v2'] = len(new)
    A['old_system'] = len(old)
    A['ledger_lines'] = len(ledger)
    A['ledger_new_lines'] = sum(1 for L in ledger.values() if L['ledger'] == 'v5')
    A['ledger_new_lines_from_21oct'] = sum(1 for L in ledger.values() if L['ledger'] == 'v5' and L['date'] >= '2026-10-21')
    A['ledger_missed_lines'] = sum(1 for L in ledger.values() if L['ledger'] == 'v5' and L['date'] < '2026-10-21')
    tab = lambda key, rs, order: {k: sum(1 for r in rs if r[key] == k) for k in order}
    A['by_origin'] = {o: {'all': sum(1 for r in rows if r['origin'] == o),
                          'new in v2': sum(1 for r in new if r['origin'] == o),
                          'old system': sum(1 for r in old if r['origin'] == o),
                          **{k: sum(1 for r in rows if r['origin'] == o and r['kind'] == k) for k in KINDS}}
                      for o in ORIGINS}
    A['by_kind'] = {k: {'all': sum(1 for r in rows if r['kind'] == k), 'new in v2': sum(1 for r in new if r['kind'] == k)}
                    for k in KINDS}
    A['by_guard_layer'] = tab('guard_layer', rows, LAYER_NAMES)
    A['by_any_layer'] = {l: sum(1 for r in rows if l in r['layers'].split('; ')) for l in LAYER_NAMES}
    A['by_status'] = tab('status', rows, STATUSES)
    A['open'] = [f"{r['id']} {r['class']}" for r in rows if r['status'] == 'open']
    A['first_found_by_route'] = {k: v for k, v in tab('found_route', new, ROUTES).items() if v}
    allev = []
    for r in rows:
        if r['first_found']:
            allev.append((r['first_found'], r['found_route'], r['id'], 'first'))
        for e in [x for x in r['found_again'].split('; ') if x]:
            d, route = e.split(' ', 1)
            allev.append((d, route, r['id'], 'again'))
    A['finds_by_route'] = {k: sum(1 for e in allev if e[1] == k) for k in ROUTES if any(e[1] == k for e in allev)}
    A['finds'] = len(allev)
    A['found_again_classes'] = sum(1 for r in rows if r['found_again'])
    # after its rule: a find dated after the class's rule commit
    after = []
    for r in rows:
        if r['rule_date'] and r['found_again']:
            later = [e for e in r['found_again'].split('; ') if e and e.split(' ', 1)[0] > r['rule_date']]
            if later:
                after.append(f"{r['id']} ({len(later)})")
    A['found_again_after_rule'] = after
    lay = json.load(open(os.path.join(ROOT, LAYERS), encoding='utf-8'))
    # find-to-rule lag (new classes with a rule commit; status rule or flag)
    lags = []
    for r in new:
        if r['rule_date'] and r['status'] != 'open':
            lags.append(((dt.date.fromisoformat(r['rule_date']) - dt.date.fromisoformat(r['first_found'])).days, r['id'],
                         r['class'], r['first_found'], r['rule_date']))
    longest = max(lags)
    # check of 2 November: a rule older than the class's first finding (PP4: the verifier's closure rule of 7 October)
    # is counted apart, not as a same-day rule
    A['lag_days'] = dict(n=len(lags), predates=[f'{x[1]} {x[2]}' for x in lags if x[0] < 0],
                         same_day=sum(1 for x in lags if x[0] == 0),
                         within_2_days=sum(1 for x in lags if 0 <= x[0] <= 2),
                         max=longest[0], max_class=f'{longest[1]} {longest[2]}', max_found=longest[3], max_rule=longest[4],
                         median=sorted(x[0] for x in lags)[len(lags) // 2])
    # later rules (rule_dates beyond the first): every later commit that changed a class's check
    lr = {r['id']: r['rule_dates'].split('; ')[1:] for r in rows if r['rule_dates'].count(';')}
    A['later_rules'] = dict(classes=len(lr), commits=sum(len(v) for v in lr.values()),
                            rule_dates_drawn=len({(r['id'], d.split(' ')[0]) for r in rows if r['rule_dates'] for d in r['rule_dates'].split('; ')}),
                            by_class={k: v for k, v in lr.items()},
                            after_a_refind=sorted(k for k, v in lr.items() if any(
                                any(e.split(' ', 1)[0] <= d.split(' ')[0] for e in next(r for r in rows if r['id'] == k)['found_again'].split('; ') if e)
                                for d in v)),
                            checked='builder only (second-agent check pending)')
    pb = {x['label']: x for x in lay['panel_b']['labelled']}
    assert pb['misprinted unit headers']['minutes_find_to_rule'] == 2, pb['misprinted unit headers']
    # defence in depth
    nl = {r['id']: len(r['layers'].split('; ')) for r in rows}
    A['layers_per_class'] = {str(k): sum(1 for v in nl.values() if v == k) for k in sorted(set(nl.values()))}
    A['two_or_more_layers'] = sum(1 for v in nl.values() if v >= 2)
    A['three_or_more_layers'] = [f"{r['id']} {r['class']} ({nl[r['id']]}: {r['layers']})" for r in rows if nl[r['id']] >= 3]
    A['one_layer_by_layer'] = {l: sum(1 for r in rows if nl[r['id']] == 1 and r['layers'] == l) for l in LAYER_NAMES}
    # discovery curve: papers read = distinct papers at their first add in log.tsv (Fig. 1 v1 rule)
    weeks = collections.Counter(week_of(d) for d in first_add.values())
    last_add = max(first_add.values())
    curve = []
    cum_p = cum_c = 0
    for w in range(0, week_of('2026-11-02') + 1):
        a = dt.date(2026, 10, 7) + dt.timedelta(days=7 * w)
        b = min(a + dt.timedelta(days=6), dt.date(2026, 11, 2))
        papers = weeks.get(w, 0)
        nc = sum(1 for r in new if week_of(r['first_found']) == w)
        ne = sum(1 for e in allev if week_of(e[0]) == w)
        cum_p += papers
        cum_c += nc
        curve.append(dict(week=f'{a.isoformat()} to {b.isoformat()}', papers_read=papers, new_classes=nc,
                          new_per_1000_papers=round(1000 * nc / papers, 1) if papers else None, finds=ne,
                          finds_per_1000_papers=round(1000 * ne / papers, 1) if papers else None,
                          cum_papers=cum_p, cum_new_classes=cum_c))
    reads = collections.Counter()
    for p in log_rows():
        if p[2] == 'add':
            reads[week_of(p[0][:10])] += 1
    for w, row in enumerate(curve):
        row['reads'] = reads.get(w, 0)
        row['new_per_1000_reads'] = round(1000 * row['new_classes'] / row['reads'], 1) if row['reads'] else None
        row['new_by_route'] = dict(collections.Counter(r['found_route'] for r in new if week_of(r['first_found']) == w))
    A['discovery_curve'] = curve
    A['reads'] = sum(reads.values())
    A['papers_read'] = len(first_add)
    A['last_first_add'] = last_add
    # first 1,000 papers vs the rest
    order = sorted(first_add.values())
    d1000 = order[999]
    A['papers_by_day_1000th'] = d1000
    A['log_cutoff'] = LOG_CUTOFF
    A['log_counts'] = dict(unitfix_misprint_12_23_oct=c['unitfix'], unitfix_restored=c['unitfix_restore'],
                           unitfix_after_23_oct=c['unitfix_later'],
                           reworded_duplicate=c['reworded_duplicate'], conflict=c['conflict'], wrong_paper=c['wrong_paper'],
                           pmfix=c['pmfix'], limitfix=c['limitfix'], drop_bound=c['drop_bound'],
                           reread_copies_dropped_by_day=dict(sorted(dups.items())), unknown_unit_refusals=unknown)
    A['old_lines_in_classes'] = sum(1 for r in rows if any(int(n) <= 50 for n in r['ledger_lines'].split(', ') if n))
    A['new_from_21oct'] = {o: sum(1 for r in new if r['first_found'] >= '2026-10-21' and r['origin'] == o) for o in ORIGINS}
    A['new_from_21oct_routes'] = dict(collections.Counter(r['found_route'] for r in new if r['first_found'] >= '2026-10-21'))
    A['old_system_kinds'] = dict(collections.Counter(r['kind'] for r in old))
    A['old_system_not_found_again'] = [r['id'] for r in old if not r['found_again']]
    A['old_system_lessons_commit_only'] = [r['id'] for r in old if not r['found_again'] and 'Old-system lessons' in r['found']]
    A['origin_by_layer'] = {o: {l: sum(1 for r in rows if r['origin'] == o and l in r['layers'].split('; ')) for l in LAYER_NAMES}
                            for o in ORIGINS}
    A['code_check_main_by_origin'] = dict(collections.Counter(r['origin'] for r in rows if r['guard_layer'] == 'code check'))
    A['verifier_catches'] = dict(values=lay['panel_a']['drawn']['verifier']['values'],
                                 papers=lay['panel_a']['drawn']['verifier']['papers'],
                                 unit=lay['panel_a']['drawn']['verifier, number off by a unit factor']['values'],
                                 base=lay['panel_a']['bases']['verifier and code checks'])
    A['inputs'] = {p: hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()[:12]
                   for p in ('log.tsv', 'rejected.jsonl', OLD_LEDGER, 'prompts/read.md', 'prompts/verify.md', 'CLAUDE.md')}
    A['git_head'] = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    A['built'] = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    json.dump(A, open(os.path.join(HERE, 'taxonomy_numbers.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    markdown(A, rows, ledger)
    return A


def md_table(head, body):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '|'.join('---' if i == 0 else '---:' if isinstance(body[0][i], int) else '---'
                                                     for i in range(len(head))) + '|']
    for b in body:
        out.append('| ' + ' | '.join(f'{x:,}' if isinstance(x, int) else str(x).replace('|', '/') for x in b) + ' |')
    return '\n'.join(out)


def markdown(A, rows, ledger):
    new = [r for r in rows if r['novelty'] == 'new']
    v5lines = [ledger[n] for n in sorted(ledger) if ledger[n]['ledger'] == 'v5']
    late = [L for L in v5lines if L['date'] >= '2026-10-21']
    missed = [L for L in v5lines if L['date'] < '2026-10-21']
    cur = A['discovery_curve']
    base_words = A['verifier_catches']['base'].replace('per 1,000 of the ', '').replace('(current read of', 'in the current reads of').rstrip(')')
    m = []
    w = m.append
    w('# Failure taxonomy of NAME (Fig. 1 v5; Extended Data table)')
    w('')
    w(f"Built {A['built']} by `build_taxonomy.py` from git (HEAD {A['git_head']}), CatLog's files and `log.tsv` (lines before "
      f"{A['log_cutoff']}). Every quoted string the table rests on was found in the source it names; for files the "
      "sources column gives the line. `taxonomy.tsv` has one line per failure class, `error_ledger_v5.tsv` the ledger "
      "behind it, `taxonomy_numbers.json` every number below.")
    w('')
    w('## Draft legend (Extended Data Table)')
    w('')
    w(f"**Extended Data Table N | The failures found while NAME was built, where each starts and the guard it became.** "
      f"One line per failure class ({A['classes']}), repeats merged: {A['new_in_v2']} found by NAME's own reading and checks "
      f"from 7 October to 2 November 2026, {A['old_system']} known from the earlier system and written into NAME's first "
      "rules. Origin: the printed paper, the PDF text layer or OCR, the reading agent, identity and pairing, conversion and "
      "units, the databases, the process. Kind: a wrong value or label let in (FA), right values refused or lost (FR), a "
      "process failure (PROC). Found: date and route of the first finding and of each later one. Guard: the rule or check "
      "it became and the layer it sits in. Values: what it touched or what the guard caught, with the count's source. "
      f"Status: rule ({A['by_status']['rule']}), flag kept as printed ({A['by_status']['flag kept as printed']}), open "
      f"({A['by_status']['open']}). Compiled after the fact from the git log, working notes, logs and evidence files, and "
      "checked line by line against them by a second agent; every quoted fact is checked by script against its source "
      "[DEV].")
    w('')
    w('## What it is')
    w('')
    w(f"NAME's checks were added one at a time, each after a failure found in real papers. The error ledger of "
      f"22 October listed 50 such failures from 7 to 21 October. This ledger has {A['ledger_lines']} lines: those 50 "
      f"unchanged, {len(late)} found from 21 October to 2 November, and {len(missed)} earlier ones the 22 October ledger "
      f"missed. Repeats of one failure are merged into a class, and lines that bundled two failures are split: "
      f"{A['classes']} classes. {A['new_in_v2']} were first found by v2's own reading and checks; {A['old_system']} were "
      "known from the old system (realkcat) and written into v2's first prompts and code on 7-8 October (their "
      "`novelty` is `old system`, with the record that says so).")
    w('')
    w('Columns of `taxonomy.tsv`:')
    w('')
    w('- `class`: the failure in at most eight words.')
    w('- `origin`: where it starts. *The printed paper*: the paper itself is wrong or misleading (a misprinted header, '
      'a reprint, a withdrawn value). *The PDF text layer or OCR*: the paper is right but the machine text CatLog reads '
      'is not (glyphs, OCR, publisher XML, CatLog\'s own converter). *The reading agent*: paper and text are right but '
      'an agent (reader, verifier, auditor, checker) takes the wrong thing. *Identity and pairing*: the number is right '
      'but sits under the wrong enzyme, variant, substrate, sequence, structure, paper or record. *Conversion and units*: '
      'code parses or converts a printed form wrongly, or refuses it. *The databases*: database content enters reading, '
      'checking, comparison or the export. *The process*: the loop\'s own bookkeeping, isolation or measurement (its '
      'comparisons with the databases and the reviewers included).')
    w('- `kind`: FA, a wrong value or label reached or could reach the catalogue; FR, a right value was refused, lost '
      'or never stored; PROC, the process failed without a wrong value of its own.')
    w('- `found`: the first finding and each later one (date, route, who). Routes: reader, verifier, code check (an '
      'add-time check, a reject count or the regression check), audit, database check, sweep, operator (the chat '
      'that runs the loop), reviewer (people checking records or the website), owner, outside review (Codex, the '
      'paper-planning reviews, the head-to-head with a gold set, the case-study checks).')
    w('- `guard` and `guard_layer`: the rule or check it became, and the layer it sits in (reader prompt, verifier '
      'prompt, code conversion, code check, sweep from the paper\'s own numbers, database check, audit, people); '
      '`layers` lists every layer that guards the class.')
    w('- `values`: what it touched or what the guard caught, with the count\'s source; `status`: rule, flag kept as '
      'printed, or open.')
    w('- `sources`: commits (`git:`), files with line numbers (`file:line`; `file@commit` for a file as it stood then) '
      'and evidence paths.')
    w('')
    w('## The classes')
    w('')
    body = []
    for r in rows:
        nl = len(r['layers'].split('; '))
        first = r['first_found'] or 'old system'
        again = len([x for x in r['found_again'].split('; ') if x])
        body.append([r['id'], r['class'], r['origin'], r['kind'], first + (f' (+{again})' if again else ''),
                     r['guard_layer'] + (f' (+{nl - 1})' if nl > 1 else ''), r['status']])
    w(md_table(['id', 'class', 'origin', 'kind', 'first found (+ found again)', 'guard layer (+ other layers)', 'status'], body))
    w('')
    w('## How the ledger grew after 21 October')
    w('')
    w(f"{len(late)} lines from 21 October to 2 November ({sum(1 for L in late if L['kind'] == 'FA')} FA, "
      f"{sum(1 for L in late if L['kind'] == 'FR')} FR, {sum(1 for L in late if L['kind'] == 'PROC')} PROC), "
      f"and {len(missed)} lines from {int(min(L['date'] for L in missed)[8:])}-20 October that the 22 October ledger "
      "missed:")
    w('')
    w(md_table(['line', 'date', 'kind', 'found by', 'failure', 'class'],
               [[L['line'], L['date'], L['kind'], L['found_by'], L['failure'], L['classes']] for L in v5lines]))
    w('')
    w('The four lines open on 21 October: 50 (a derived kcat/Km above the physical limit) is now flagged (PP5); 31 (a '
      'required field left empty for a whole paper) is split, its unprinted units recovered by code (CU5) and its empty '
      'locations still open (RA7); 32 (Elsevier OCR-only texts) and 40 (Europe PMC XML running cells together) are '
      'still open (TL7, TL8).')
    w('')
    w('## Analysis')
    w('')
    w('### Where failures start')
    w('')
    w(md_table(['origin', 'classes', 'new in v2', 'old system', 'FA', 'FR', 'PROC'],
               [[o, v['all'], v['new in v2'], v['old system'], v['FA'], v['FR'], v['PROC']] for o, v in A['by_origin'].items()]
               + [['all', A['classes'], A['new_in_v2'], A['old_system'], A['by_kind']['FA']['all'], A['by_kind']['FR']['all'],
                   A['by_kind']['PROC']['all']]]))
    w('')
    bo = A['by_origin']
    top = max(ORIGINS, key=lambda o: bo[o]['all'])
    share = bo[top]['old system'] / bo[top]['all']
    part = 'most' if share > 0.5 else 'half' if share == 0.5 else 'fewer than half'
    w(f"{top[0].upper() + top[1:]} holds the most classes ({bo[top]['all']}), {part} of them old-system lessons "
      f"({bo[top]['old system']}). Of the {A['new_in_v2']} classes v2 found itself, "
      + ', '.join(f"{bo[o]['new in v2']} start in {o}" for o in sorted(ORIGINS, key=lambda o: -bo[o]['new in v2'])
                  if bo[o]['new in v2'])
      + f". Of the {sum(A['new_from_21oct'].values())} found from 21 October on: "
      + ', '.join(f"{v} in {o}" for o, v in A['new_from_21oct'].items() if v) + '.')
    w('')
    w('### Wrong values in, right values refused')
    w('')
    w(f"All classes: {A['by_kind']['FA']['all']} let a wrong value or label in, {A['by_kind']['FR']['all']} refused or lost "
      f"right values, {A['by_kind']['PROC']['all']} are process failures. The old system's lessons are almost all of the first "
      f"kind ({A['old_system_kinds'].get('FA', 0)} FA of {A['old_system']}). Among the {A['new_in_v2']} classes v2 found, "
      f"{A['by_kind']['FA']['new in v2']} let wrong values in and {A['by_kind']['FR']['new in v2']} refused right ones: "
      "the checks v2 added to keep wrong values out were themselves a main source of new failures (a required organism, a "
      "title check, a kcat ceiling, a missing unit, a ratio rule, a quote check on OCR text, an implausible scale); most "
      "were loosened to a flag or a narrower rule, and two wait on better copies of papers (TL7, TL8).")
    w('')
    w('### Which layer guards them')
    w('')
    w(md_table(['layer', 'main guard of', 'guards (any)'],
               [[l, A['by_guard_layer'][l], A['by_any_layer'][l]] for l in LAYER_NAMES]))
    w('')
    cc = A['code_check_main_by_origin']
    w(f"Code checks are the main guard of {A['by_guard_layer']['code check']} classes, "
      f"{cc.get('the process', 0) + cc.get('identity and pairing', 0)} of them process or identity classes; prompts are the "
      f"main guard of {A['by_guard_layer']['reader prompt'] + A['by_guard_layer']['verifier prompt']}. The verifier prompt "
      f"guards {A['by_any_layer']['verifier prompt']} classes in all, more than any layer but code checks. Classes by origin "
      "and by every layer that guards them (a class counts once in each of its layers):")
    w('')
    short = {'reader prompt': 'reader', 'verifier prompt': 'verifier', 'code conversion': 'conversion', 'code check': 'code check',
             SWEEP: 'sweep', 'database check': 'database', 'audit': 'audit', 'people': 'people'}
    w(md_table(['origin'] + [short[l] for l in LAYER_NAMES],
               [[o] + [A['origin_by_layer'][o][l] for l in LAYER_NAMES] for o in ORIGINS]))
    w('')
    w('### How they were found')
    w('')
    w(md_table(['route', 'first finding of a v2 class', 'all findings'],
               [[k, A['first_found_by_route'].get(k, 0), A['finds_by_route'].get(k, 0)] for k in ROUTES if k != 'old system'
                and (A['first_found_by_route'].get(k) or A['finds_by_route'].get(k))]))
    w('')
    names = {'operator': 'the chat running the loop', 'outside review': 'outside reviews', 'code check': 'code checks',
             'audit': 'audits', 'reviewer': 'reviewers', 'sweep': 'sweeps', 'verifier': 'the verifier',
             'reader': 'the reader', 'owner': 'the owner', 'database check': 'the database check'}
    ff = sorted(A['first_found_by_route'].items(), key=lambda x: -x[1])
    late = sorted(A['new_from_21oct_routes'].items(), key=lambda x: -x[1])
    w(f"{A['finds']} findings in all ({A['new_in_v2']} first findings and the rest found again). "
      f"{names[ff[0][0]][0].upper() + names[ff[0][0]][1:]} found the most classes first ({ff[0][1]}), then "
      f"{names[ff[1][0]]} ({ff[1][1]}) and {names[ff[2][0]]} ({ff[2][1]}). "
      f"From 21 October on, new classes came most often from {names[late[0][0]]} ("
      + ', '.join(f"{k} {v}" for k, v in late)
      + f" of {sum(A['new_from_21oct_routes'].values())}). "
      f"The verifier first found only {A['first_found_by_route'].get('verifier', 0)} classes, yet it is the layer that "
      f"catches most values ({A['verifier_catches']['values']:,} serious catches in {A['verifier_catches']['papers']} papers "
      f"among the {base_words}; {A['verifier_catches']['unit']:,} of them a number off by a unit factor; "
      "`paper/figures/layers_ledger/layers_ledger_numbers.json`, 22 October development run): its catches are the classes "
      "working, not new ones.")
    w('')
    w('### Discovery curve')
    w('')
    w('Papers read = distinct papers at their first `add` in `log.tsv` (the rule of Fig. 1 v1); reads = every `add`, '
      're-reads and censored-only passes included. Weeks run from Wednesday 7 October; the last has six days.')
    w('')
    w(md_table(['week', 'papers read', 'reads', 'new classes', 'per 1,000 papers', 'per 1,000 reads', 'findings',
                'findings per 1,000 papers', 'new classes by route'],
               [[c['week'], c['papers_read'], c['reads'], c['new_classes'], c['new_per_1000_papers'], c['new_per_1000_reads'],
                 c['finds'], c['finds_per_1000_papers'], ', '.join(f'{k} {v}' for k, v in sorted(c['new_by_route'].items(), key=lambda x: -x[1]))]
                for c in cur]))
    w('')
    pp = [c['new_per_1000_papers'] for c in cur]
    pr = [c['new_per_1000_reads'] for c in cur]
    w(f"New classes did not stop: {cur[0]['new_classes']} in the first week ({cur[0]['papers_read']:,} papers), "
      f"{cur[1]['new_classes']} in the second, {cur[2]['new_classes']} and {cur[3]['new_classes']} in the last two, when "
      "fewer papers were read for the first time and more were read again. Per 1,000 papers the rate "
      f"{'fell' if pp[1] < pp[0] else 'rose'} from {pp[0]} to {pp[1]} and then "
      f"{'rose' if pp[2] > pp[1] else 'fell'} to {pp[2]} and {pp[3]}; the late classes came mostly from reviews of the "
      "whole catalogue and from re-reads, not from papers read for the first time. Counted per read (re-reads and "
      f"censored-only passes included) the rate is {pr[0]}, {pr[1]}, {pr[2]} and {pr[3]} per 1,000: "
      f"{'lower' if max(pr[1:]) < pr[0] else 'not lower'} after the first week, and between {min(pr[1:])} and "
      f"{max(pr[1:])} from then on. Neither denominator measures the reviews of the whole catalogue that found most "
      "late classes.")
    w('')
    w('### Defence in depth')
    w('')
    w(f"{A['two_or_more_layers']} of {A['classes']} classes are guarded by two layers or more "
      f"({', '.join(f'{v} by {k}' for k, v in A['layers_per_class'].items())}). {len(A['three_or_more_layers'])} have three or more:")
    w('')
    for x in A['three_or_more_layers']:
        w('- ' + x)
    w('')
    one = collections.Counter(r['origin'] for r in rows if len(r['layers'].split('; ')) == 1)
    w(f"{A['layers_per_class'].get('1', 0)} classes have one layer, " + ', '.join(f'{v} of them {k}' for k, v in A['one_layer_by_layer'].items() if v)
      + '. By origin: ' + ', '.join(f'{v} {o}' for o, v in one.most_common())
      + '; most are failures of the process, the text or the conversion that one piece of code closes.')
    w('')
    w(f"{A['found_again_classes']} classes were found more than once; {len(A['found_again_after_rule'])} of them again "
      f"after their first rule was committed (findings after the rule in brackets): {', '.join(A['found_again_after_rule'])}. "
      "This is why layers were added: misprinted unit headers (PP1) became a verifier rule on 11 October two minutes after "
      "the audit that found them (`paper/figures/layers_ledger/layers_ledger_numbers.json`, panel_b), and were found again by the database check, the blind re-read, the scale sweep and the "
      "Vmax sweep; reprints (PP2) by audits and the reprint sweep; ± drawn as a digit (TL2, the worked example 21757926) "
      "slipped past the glyph table of 8 October, was caught on the page image by the reader and verifier and named by "
      "the database check on 17 October, then met a structural warning on 1 November.")
    w('')
    w('### From finding to rule')
    w('')
    L = A['lag_days']
    pre = (f"{len(L['predates'])} had a guard older than its first finding ({'; '.join(L['predates'])}: the verifier's "
           "closure rule of 7 October refused such cells before a rule named them), ") if L['predates'] else ''
    w(f"Of the {L['n']} v2 classes with a rule, {pre}{L['same_day']} have their rule commit on the day of the finding and "
      f"{L['within_2_days']} within two days (longest {L['max']} days: {L['max_class']}, found {L['max_found']}, rule "
      f"{L['max_rule']}). Finding dates are mostly the dates of the commit or log line that records the finding, so the "
      "same-day share is an upper bound.")
    LR = A['later_rules']
    w('')
    w(f"A class's check kept changing after its first rule: {LR['classes']} classes had {LR['commits']} later rule "
      f"commits (`rule_dates`; {len(LR['after_a_refind'])} of those classes after being found again), for example "
      "misprinted unit headers (PP1: a verifier rule on 11 Oct, unitfix on 12 Oct, the scale sweep on 20 Oct, the Vmax "
      "sweep on 23 Oct, the maximal-rate rule on 31 Oct) and ± drawn as a digit (TL2: 8 Oct, then 1 Nov). The later "
      "commits were matched to classes from the commit messages and the classes' guard texts; a second agent has not "
      "checked them yet.")
    w('')
    w('### Open')
    w('')
    w(f"{len(A['open'])} classes are open (no guard beyond an agent's judgement, a guard with a known gap, or a wait for "
      "better copies of papers): "
      + '; '.join(A['open']) + '.')
    w('')
    w('## Against the 22 October ledger')
    w('')
    w(f"Its 50 lines sit in {A['old_lines_in_classes']} classes here (it counted 46). Merged there and here: misprinted "
      "unit headers (23, 38, 47) and re-read copies (21, 39, 42). Merged here as well: dead agents (14, 16), ± handling in "
      "code (10, 11, 49), parser refusals (35, 46), required details (5, 6, 31), wrong proteins (13, 17, 25), wrong "
      "structures (17, 25, 26), database values used as evidence (28, 34), fields left empty (15, 31), different "
      "measurements in one slot (12, 21). Split: line 1 into a constant that is not kcat or Km (RA1) and "
      "conditions of another step (RA2); line 4 into µ drawn as m (TL1) and ± drawn as a digit (TL2); line 5 into a "
      "dropped ± (RA5), the ratio rule (PP6) and unprinted details (CU5); line 17 into wrong proteins (IP9) and wrong "
      "structures (IP17); line 21 into re-read copies (IP3) and the looser twin rule that merged different measurements "
      "(IP5); line 31 into empty locations (RA7) and unprinted units (CU5). Lines 1 and 4 describe old-system failures "
      "(Codex's cases from the old catalogue's certified rows; the old system's glyph lesson with a 120-PDF sample): "
      "they are the inheritance of RA1, RA2, TL1 and TL2, not findings in v2. "
      f"{len(A['old_system_not_found_again'])} of the {A['old_system']} old-system classes were not found again in v2 "
      f"({', '.join(A['old_system_not_found_again'])}); {len(A['old_system_lessons_commit_only'])} of those rest only on "
      "the 8 October commit that lists the old system's lessons and on the rule text "
      f"({', '.join(A['old_system_lessons_commit_only'])}).")
    w('')
    w('## Limits')
    w('')
    w('- Compiled after the fact by one agent from commits, working notes, logs and evidence files, as the 22 October '
      'ledger was, and checked line by line against those sources by a second agent on 2 November (`TAXONOMY_CHECK.md`: '
      'every verdict, the fixes applied here, and what was left open).')
    w('- The check\'s scan for values stored twice (IP3) compared the rows of each paper across reads by printed cell, '
      'enzyme, variant, substrate, location, pH and temperature; it is not a full duplicate audit '
      '(`taxonomy_evidence/same_cell_twice_20261102.tsv`).')
    w('- Value counts come from different snapshots (each source is dated: the refused-values table is of 28 October, '
      'the verifier counts of the 22 October development run, the status line of 2 November 07:18) and are '
      'development numbers.')
    w('- "Found" is the first record of a failure, not necessarily the first time anyone noticed it; who noticed is not '
      'recorded for IP8.')
    w('- PP7 and PP8 come from the checked agent cases (`paper/04_agent_case_tables.md`, `paper/05_agent_case_boxes.md`), '
      'PP3 from a sweep\'s side find: agents caught them without a rule. The agents, their checkers and this compilation '
      'are one model family.')
    w('- Infrastructure failures (Chrome clones filling the disk, PubChem rate limits, disk space, download lanes) and '
      'bugs of the website\'s own build and pages are left out: they touch no stored value or record.')
    w('')
    w('## Rebuild')
    w('')
    w('`python3 build_taxonomy.py` (about a minute; it stops if any quoted string is missing from its source, or if a '
      'count it recomputes from `log.tsv` or `rejected.jsonl` moved). It writes only into this folder.')
    open(os.path.join(HERE, 'TAXONOMY.md'), 'w', encoding='utf-8').write('\n'.join(m) + '\n')


if __name__ == '__main__':
    ledger, rows, first_add, c, dups, unknown = main()
    A = write(ledger, rows, first_add, c, dups, unknown)
    print(f"{A['ledger_lines']} ledger lines ({A['ledger_new_lines']} new), {A['classes']} classes "
          f"({A['new_in_v2']} new in v2, {A['old_system']} from the old system); every quote found in its source")
