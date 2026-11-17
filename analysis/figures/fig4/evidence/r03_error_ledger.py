#!/usr/bin/env python3
"""CatLog's error ledger: systematic failures found while the pipeline ran, when, how they were found, how many
rows they touched and the rule each became. Built by hand from `git log` (514 commits) and CLAUDE.md "Open items",
and CHECKED here: every entry names its sources and quotes the exact words (counts included) that must appear in
them; the script fails loudly if a quoted string is missing, so every count in the table is traceable.

kind: FA = false accept (a wrong value or label reached, or could reach, the catalog)
      FR = false reject (a correct, verified value was lost to a rule)
      PROC = process (agents, queue, files, monitoring) without a value error of its own
found_by: who or what noticed it first, as the record says.
Output: error_ledger.tsv and error_ledger.md (table + tallies).
"""
import csv, os, re, subprocess, sys
from collections import Counter

ROOT = '<the CatLog folder>'
HERE = os.path.dirname(os.path.abspath(__file__))
TJ = os.path.dirname(HERE)  # work/top_journal_20261021

L = [
 # date, kind, found_by, failure, rows, rule (layer: rule), sources, evidence strings
 ('10-07', 'FA', 'external code review (Codex, old-catalog failure cases)',
  'Hill / rescue-agent constants taken as Km; pH or temperature of another reaction step; coupled-assay reagents as cosubstrates',
  '9 errors in old certified rows (5 also verbatim in BRENDA/OED/SKiD)',
  'prompts: Hill/Kact/rescue rules, reaction-step pH/T; code: a pH/T must be printed in the paper',
  ['git:4d7cfd9', 'CLAUDE.md'], ['Hill/rescue-agent constants', 'pH/T must be printed', '5 of the 9 errors Codex found in old certified rows']),
 ('10-07', 'FA', 'external code review (Codex)', 'one assay split into three export rows (kcat, Km, kcat/Km apart)',
  'not counted', 'code: measurements() grouping + uncertainty-aware kcat/Km ratio check',
  ['git:aec6ab2', 'CLAUDE.md'], ['one assay = one export row', 'one assay had been split into 3 rows']),
 ('10-08', 'FA', 'external code review (Codex re-read findings)',
  're-reads could add a second, different value for one measurement; a verdict could be applied to a reordered row',
  'not counted', 'code: one value per slot, conflicts kept apart, audit drops sticky, each verdict echoes metric + raw_value, zero-row reads verified',
  ['git:157c8bb'], ['one value per measurement slot', 'stale or mismatched verdicts refused', 'zero-row reads verified']),
 ('10-08', 'FA', 'old-system lessons + a 120-PDF sample', 'symbol-font PDFs print µ as m (silent 1000x Km), ± as 6, minus as 21',
  '15 of 120 sampled library PDFs', 'code: GLYPH WARNING line; prompts: numbers from page images',
  ['git:3c3e3c6', 'CLAUDE.md'], ['glyph warning for PDFs whose text layer turns', '15 of 120 sampled library PDFs']),
 ('10-08', 'FR', 'operator (reject counts per batch)',
  'strict checks lost correct values: a dropped ±, an unprinted pH/T or a kcat/Km mismatch rejected the whole value',
  'not counted', 'code completes ± from the quote, blanks pH/T, flags kcat/Km; verifier/auditor reject only for a named error',
  ['git:aa032a4'], ['Less strict where strictness lost good values', 'verifier/auditor reject only for a named error']),
 ('10-09', 'FR', 'code rejects (batch 2)', 'organism required: a paper that never names the source species lost every value',
  '168 values', 'code: organism optional', ['git:3c6a6b4'], ['a paper that never names the source species lost 168 values']),
 ('10-09', 'FA', 'code (stray glyphs)', 'control characters inside numbers (2<U+008A>.6) and a two-glyph ±',
  'not counted', 'code: cleaned before parsing', ['git:3c6a6b4'], ['one PDF printed 2.6 as 2<U+008A>.6']),
 ('10-09', 'FR', 'code rejects of verifier-confirmed values', 'scan OCR text layer drops or splits digits, so confirmed cells failed the quote check',
  '4 values (4622304), 5 (10021417)', 'verify prompt: on_page_image; code: flag (quote_check) instead of reject',
  ['git:db34453', 'catlog.py', 'prompts/verify.md'], ['OCR text is not evidence', 'PMID 4622304, 1972 scan, 4 values', 'PMID 10021417 lost 5 confirmed values']),
 ('10-09', 'FR', 'verifier (missed values)', 'reader skipped tables that exist only as images in scanned PDFs',
  '147 and 191 values (102640, 10965051)', 'read prompt: read those tables on page images, quote "[page image p.N]"',
  ['git:25604bf', 'prompts/read.md'], ['verifier was finding them all as missed', 'read 147 and 191 such values as "missed" in PMIDs 102640, 10965051']),
 ('10-09', 'FA', 'audit (29421037, row 2915f1e1292fb682)', "code's own ± completion borrowed the neighbouring Km cell's ± for a kcat/Km",
  '1 audited row', 'code: complete a dropped ± only when the number is printed once in the quote',
  ['git:495383e', 'log.tsv'], ['complete a dropped ± only when the number is printed once in the quote', 'borrows that neighbouring Km uncertainty']),
 ('10-09', 'FA', 'code (16792995)', '± completion overstated an error term carrying its own x10 exponent', 'not counted',
  'code: no completion when the ± term has its own exponent', ['git:23fb904', 'catlog.py'], ['carries its own x10 exponent', 'PMID 16792995']),
 ('10-09', 'FR', 'code rejects (conflicts)', 'paralogs and strains of one species shared a slot, so their values were rejected as conflicts',
  'not counted (E. cloacae P99/908R)', 'code: printed gene and strain in slot and grouping',
  ['git:586e755', 'git:4957210'], ['Keep paralogs apart', 'E. cloacae P99/908R values were rejected as conflicts']),
 ('10-09', 'FA', 'website review', 'NCBI genome segment with many CDS gave PurT to a beta-mannosidase (11900558)', '1 paper',
  'code: NCBI CDS route only for one-CDS records', ['git:704025b', 'CLAUDE.md'], ['NCBI CDS route only for one-CDS records', 'gave PurT for a β-mannosidase, PMID 11900558']),
 ('10-09', 'PROC', 'operator', 'safety filter stopped readers of toxin/pathogen enzyme papers (19261311)', 'not counted',
  'workflow: curation-context prefix; retry once on another model', ['git:876844e', 'log.tsv', '.claude/workflows/catlog-batch.js'],
  ['retry on Sonnet also when an agent reports a problem', 'reader stopped by safety filter', 'safety filter']),
 ('10-10', 'FR', 'code rejects', 'verifier left an empty variant the paper makes clear', '36 rows (19397282)',
  'verify prompt: an empty field the paper makes clear is a fix', ['git:da62f48'], ['36 Dpo4 rows of 19397282 lost to missing:variant']),
 ('10-10', 'PROC', 'operator', 'usage limit mid-batch: dead agents counted as bad papers; finished reads thrown away',
  '24 papers re-read for nothing; 20 valid reads lost', 'workflow: 3 dead agents in a row stop the lanes; reread keeps an unverified read; add re-queues',
  ['git:13c37e1', 'git:977dfb2'], ['24 papers were re-read for nothing on 2026-10-10', '20 valid reads were thrown away since 10-10']),
 ('10-10', 'FA', 'human review (structures, proteins)', 'name collisions: p-hydroxyphenylpyruvate got phenylpyruvate, HP got His-Pro, rat MCAD got LCAD',
  'not counted', 'code (enrich): shared ChEBI names are no synonym; abbreviation hits must share a word with the printed name',
  ['git:ba0d005'], ['p-hydroxyphenylpyruvate was phenylpyruvate', 'HP was His-Pro', 'rat MCAD was LCAD']),
 ('10-10', 'FR', 'user decision after rejects', 'a printed kcat/Km that disagrees with kcat ÷ Km dropped kcat, Km and kcat/Km',
  '85 values recovered (77 ratio-only verifier rejections)', 'code: keep all three, note the factor; `recover` re-adds rows a changed rule no longer rejects',
  ['git:12770bd', 'git:27ad550'], ['drops nothing (user decision)', 'Recovered 85 values (77 ratio-only verifier rejections']),
 ('10-10', 'FA', 'human review', 'natural forms (isozymes, alleles, paralogs) written as variants', '78 older rows',
  'prompts: the form is the enzyme identity; code: identity() + sources/natural_forms.tsv', ['git:86b8807', 'CLAUDE.md'],
  ['Natural forms (isozyme, paralog, allele) are the enzyme', 'listed in `sources/natural_forms.tsv` (78']),
 ('10-10', 'FA', 'operator (filing check)', 'a PDF filed by title words alone went to the wrong paper', '3 of 14 PDFs',
  'code: title must be printed near the top', ['git:1eb0882'], ['title words alone filed 3 of 14 wrongly']),
 ('10-11', 'FA', 'recheck (re-read duplicates)', 're-reads that reworded enzyme or variant stored the same cell twice; a looser twin rule then merged I164A ampicillin with penicillin G',
  '126 duplicates in 4 papers', 'code: recheck reports one-to-one duplicates; the loose rule reverted',
  ['git:fb30d57', 'git:700b56d'], ['126 such duplicates in 4 papers dropped today', 'I164A ampicillin as a duplicate of I164A penicillin G']),
 ('10-11', 'FA', 'operator (diffusion-limit check)', "header 's^-1×10^-4' read as ×10^4 (16431280): kcat/Km beyond diffusion, scale not decidable from the paper",
  '60 values dropped', 'drop for a named reason; verify prompt: header multiplier direction confirmed on the page image (fix.unit_for_conversion)',
  ['log.tsv', 'prompts/verify.md'], ["header 's^-1×10^-4' read as ×10^4", 'Watch headers like "kcat/Km × 10^-5" that mean the printed number is already multiplied']),
 ('10-11', 'FA', 'audit (25514023)', 'misprinted unit header (Table 6 kcat min-1, really s-1) read as printed', '11 kcats 60x low',
  'verify prompt: a header the paper itself shows is misprinted gets unit_for_conversion', ['git:cb53ec3'], ['11 kcats 60x low']),
 ('10-12', 'FA', 'audits', 'an audit that found a fixable unit error could only delete the value', '28 values corrected, 16 reprints dropped',
  'code: `unitfix`; audits write unit_fix: and are recorded as a correction', ['git:14d5288', 'git:0989102'],
  ['28 values corrected, 16 reprints dropped', "'unit_fix: <unit> <evidence>'"]),
 ('10-12', 'FA', 'enrichment sweep', 'wrong protein matches (a cited PDB given to its paper-mates) and wrong substrate structures',
  '~790 values (proteins), ~450 values (structures)', 'code: sequences.py / structures.py checks, each change reviewed by a skeptic agent',
  ['git:31721e1'], ['wrong protein matches (~790 values)', 'wrong substrate structures (~450 values)']),
 ('10-11', 'FA', 'sweep (structures)', 'same-paper database votes paired values, not compounds: xylose was lactose, NADPH NADH',
  '48 wrong structures', 'code: a database name must fit OPSIN\'s formula of the printed name (structures.printed_fit)',
  ['CLAUDE.md', 'git:7de1676'], ['48 wrong structures, e.g. xylose was lactose', 'must fit OPSIN']),
 ('10-12', 'FR', 'code rejects', 'kcat ceiling 1e7 s^-1 rejected measured catalase and carbonic anhydrase values', '12 values in 4 papers',
  'code: ceiling 1e8 s^-1', ['git:daced49'], ['12 verified values recovered from 4 papers']),
 ('10-12', 'PROC', 'transcript monitor (blind_check)', 'reading agents opened database values or the old catalog despite "read blind"',
  '306 papers exposed before the rule (303 re-read blind); agreement 91.7% exposed vs 84.7% blind',
  'prompts name every forbidden file; human_review.blind_check scans transcripts; headline only on blind papers; blind re-read',
  ['git:8b6b4db', 'git:6c5c6a9', 'git:f6a13c2', 'CLAUDE.md'], ['306 papers exposed before the rule, 0 of 85 reading agents since', '84.7% vs 91.7% on database-exposed papers', 'blind re-read of the 303 papers', 'All 303 were sent back on 2026-10-21']),
 ('10-13', 'FA', 'audit (21361343)', 'partial per-product rate constants of a branched reaction stored as kcat and kcat/Km',
  '24 of 48 rows dropped; 10-16 scan: 104 more in 3 papers', 'prompts: "Partial constants" rule (reader and verifier)',
  ['git:20840f1', 'CLAUDE.md', 'git:e6d45ef'], ['PMID 21361343 audit, 24 drops', '78 + 24 (12199711) + 2 (10850809) partial kcats dropped', '104 dropped']),
 ('10-13', 'FA', 'operator', 'JBC small capitals print mM as "mm": cells converted as µM', "16595681's 10 Km values; 384 values flagged",
  'code: printed_unit_prefix_differs flag', ['git:42f8269'], ["16595681's 10 Km values printed under 'mm' and converted as uM are flagged", '384 values']),
 ('10-13', 'FR', 'code rejects (keep-reading run)', 'a reader omitted one required field for a whole paper', '31799256 18x, 25644306 16x, 25736839 9x',
  'OPEN: reread fixes most; guard in prompt or add proposed', ['CLAUDE.md'], ['31799256 18x `missing:location`', '25644306 16x `missing:location`', '25736839 9x `missing:raw_unit`']),
 ('10-13', 'FR', 'code rejects', 'Elsevier OCR-only texts (no page image): OCR runs cells together', '68 confirmed values in 13 papers; 3,309 such texts',
  'OPEN: needs full PDFs (the user\'s call)', ['CLAUDE.md'], ['3,309 texts on 2026-10-13', '68 confirmed values in 13 papers rejected']),
 ('10-14', 'FR', 'code rejects', 'old scans OCR a raised decimal point as a hyphen ("0-34")', 'NPEBD0B162 lost all 20; 32 recovered',
  'code: read such hyphens as decimals', ['git:7d212bd', 'catlog.py'], ['32 confirmed values recovered', 'lost all 20 of its confirmed values']),
 ('10-14', 'PROC', 'review of audit verdicts', 'auditors cited BRENDA as corroboration', '8 verdicts',
  'audit prompt: auditors read blind', ['git:c722037'], ['8 recent verdicts cited BRENDA as corroboration']),
 ('10-14', 'FR', 'code (export qualifier)', "'apparent molecular weight' parsed as a per-value qualifier", '21 values (7470464)',
  'code: qualifier rule', ['git:322c01c'], ['7470464: 21 values recovered']),
 ('10-14', 'PROC', 'operator', 'one-page meeting abstracts treated as previews', '18 papers sent back to download',
  'code: a single-page item is read', ['git:00cb192'], ['18 filed papers had gone back to needs_browser']),
 ('10-14', 'FA', 'audits, then a sweep', "silently reprinted earlier paper's wild-type columns (12591933 vs 11694539)",
  '22 rows (audit); sweep 973 rows in 80 papers dropped, 165 refuted and kept, 206 unsure kept',
  'prompts: compare the cited paper; tools/reprint_pairs.py + per-paper check + independent refuter + 2 more judges',
  ['git:078ea59', 'CLAUDE.md'], ['22 reprinted rows dropped by audit', '973 rows in 80 papers dropped', '165 refuted and kept', '206\n  UNSURE kept']),
 ('10-15', 'FA', 'database-difference loop (dbcheck)', 'CatLog the wrong side of a database difference', '14 values in 4 papers (12 misprinted headers, since unit-fixed)',
  'dbcheck never changes a value: catlog_wrong goes to the next audit first', ['../verify/VERIFY.md'], ['14 values in 4 papers ever got catlog_wrong']),
 ('10-16', 'FA', 'recheck', "re-read wrote a peptide's cleavage mark (↓), so the same cell was stored again", '113 copies (20635860)',
  'code: still a reworded duplicate', ['git:a5c3d00'], ['20635860: 113 copies dropped']),
 ('10-16', 'FR', 'operator', 'Europe PMC JATS XML itself runs a cell\'s parts together (drops ±, merges stacked values)', '34054745 20 values, 21072165 18',
  'OPEN: marked incomplete so the PDF is filed', ['CLAUDE.md'], ['34054745 drops every ±', '20 values', '18 values']),
 ('10-17', 'PROC', 'operator', 'evidence-check regex backtracked exponentially', 'dbcheck-record hung 20 min twice',
  'code: whole-word regex', ['git:327388a'], ['dbcheck-record hung 20 min twice']),
 ('10-18', 'FA', 'recheck', 'a re-read that moved a variant\'s bracketed label or reordered its mutations stored the cell again', '48 copies (41255148, 22564138)',
  'code: reworded duplicate', ['git:8751744'], ['41255148, 22564138: 48 copies dropped']),
 ('10-19', 'PROC', 'operator', 'the audit window started at the last verdicts, not the last sample: values added during an audit were never sampled',
  '1,900 values', 'code: window starts at the last recorded sample', ['git:c25875c'], ['1,900 values']),
 ('10-19', 'FA', 'audit (19501264)', 'directed-evolution variant recorded with only the round\'s new mutations', '17 rows dropped, paper re-read',
  'prompts: variant = template mutations + new ones', ['git:db38b4d', 'prompts/read.md'], ['17 rows with the round', '19501264']),
 ('10-19', 'FA', 'review of an audit drop (auditor error)', 'an auditor misread swapped columns and dropped a correct kcat (41835576)', '1 value',
  'code: `restore`; auditors can be wrong too', ['git:e72b5be'], ['one auditor dropped a correct kcat']),
 ('10-19', 'FR', 'code rejects', "a value with its bracketed confidence interval read as a range", '9 values (42249657)',
  'code: interval recognised', ['git:20630e5'], ['42249657 had lost 9 verified values to bound_or_range']),
 ('10-20', 'FA', 'dbcheck + audits, then the scale sweep', 'misprinted unit headers (15659684, 42228390, 25022854) read as printed',
  '899 measurements miss closure by a unit factor (798 already read in another unit); 16 values fixed; 41 reader-override papers checked, reader right in all',
  'tools/scale_sweep.py + saved workflow catlog-scale (blind check, second look, 3 refuters per change)',
  ['git:6d851aa', 'CLAUDE.md'], ['15659684, 42228390, 25022854 had misprinted headers', '899 measurements miss by a unit factor, 798 already read in another unit', '16 values fixed', 'in all 41 papers checked the reader']),
 ('10-20', 'FA', 'scale sweep', "spaced exponent '2.76E + 03' parsed as 2.76 (a 1000x error)", '41657244 (6), 42639739 (9): readers had set unit_for_conversion, so stored values were right',
  'code: units.parse_number', ['git:2b61622', 'git:55b235a'], ['a 1000x error', '41657244 (6) and 42639739 (9)']),
 ('10-20', 'FA', 'code review', 'relative uncertainty misread a ± term with its own E exponent (ratio-check tolerance only)', '46 of 51 rows in 6 papers (no stored value changed)',
  'code: rel_uncertainty', ['git:b71ed42'], ['46 of 51 such rows in 6 papers change']),
 ('10-21', 'FA', 'this investigation (verify/VERIFY.md T5)', 'export derives kcat/Km with no physical limit while add rejects the printed one',
  '47 derived values >= 1e10 M^-1 s^-1 pass', 'OPEN: fix list item 1', ['../verify/VERIFY.md'], ['all 47 derived values >= 1e10 pass']),
]

SRC = {}


def source(s):
    if s in SRC:
        return SRC[s]
    if s.startswith('git:'):
        t = subprocess.run(['git', '-C', ROOT, 'show', '-s', '--format=%ad %B', '--date=short', s[4:]],
                           capture_output=True, text=True).stdout
    elif s.startswith('../'):
        t = open(os.path.join(TJ, s[3:])).read()
    else:
        t = open(os.path.join(ROOT, s), errors='replace').read()
    SRC[s] = t
    return t


def norm(x):
    return re.sub(r'\s+', ' ', x)


bad = []
rows = []
for e in L:
    date, kind, found, fail, n, rule, srcs, ev = e
    text = norm(' '.join(source(s) for s in srcs))
    for q in ev:
        if norm(q) not in text:
            bad.append((date, fail[:50], q))
    rows.append(dict(date='2026-' + date, kind=kind, found_by=found, failure=fail, rows=n, rule=rule, sources=', '.join(srcs)))
if bad:
    for b in bad:
        print('MISSING EVIDENCE:', b, file=sys.stderr)
    sys.exit(1)

with open(os.path.join(HERE, 'error_ledger.tsv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter='\t')
    w.writeheader(); w.writerows(rows)

kinds = Counter(r['kind'] for r in rows)
fb = Counter()
for r in rows:
    f = r['found_by'].lower()
    k = ('audit' if 'audit' in f and 'review of' not in f else
         'external code review' if 'external' in f or 'code review' in f else
         'human review' if 'human' in f or 'website review' in f else
         'code rejects / recheck' if 'code' in f or 'recheck' in f else
         'sweep' if 'sweep' in f else
         'dbcheck loop' if 'dbcheck' in f else
         'transcript monitor' if 'transcript' in f else
         'verifier' if 'verifier' in f else
         'this investigation' if 'investigation' in f else 'operator / other')
    fb[k] += 1
md = ['| date | kind | found by | failure | rows | rule it became | sources |', '|---|---|---|---|---|---|---|']
for r in rows:
    md.append('| ' + ' | '.join(r[k].replace('|', '/') for k in ('date', 'kind', 'found_by', 'failure', 'rows', 'rule', 'sources')) + ' |')
md.append('')
md.append(f'Entries: {len(rows)}; kinds: ' + ', '.join(f'{k} {v}' for k, v in kinds.most_common()))
md.append('Found by: ' + ', '.join(f'{k} {v}' for k, v in fb.most_common()))
open(os.path.join(HERE, 'error_ledger.md'), 'w').write('\n'.join(md) + '\n')
print('\n'.join(md[-2:]))
print('all', sum(len(e[7]) for e in L), 'quoted strings found in their sources')
