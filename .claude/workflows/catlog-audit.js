export const meta = {
  name: 'catlog-audit',
  description: 'CatLog v2: independent auditors try to refute sampled catalog rows (old audit standard), 6 at a time (args.lanes)',
  whenToUse: 'From /audit, after `python3 catlog.py sample`: args.groups = the row_id groups it prints (the auditors read the rows from work/audit_rows_current.json, so the launch stays small), or args.rows = its JSON for a set of rows that is not on disk. Then record the verdicts with `catlog.py audit-record work/audit_*.json`.',
  phases: [{ title: 'Audit', detail: 'one auditor per group of rows, args.lanes live (default 6)' }],
}

const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const DIR = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!DIR.startsWith('/') || /[~$]/.test(DIR)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
const OLD = `${DIR}/prompts/audit_standard.md`  // the old system's audit standard, copied here (read-only reference)
const FILE = `${DIR}/work/audit_rows_current.json`  // written by `catlog.py sample`
const rows = (args && args.rows) || []
const idGroups = (args && args.groups) || []
if (!rows.length && !idGroups.length) return { error: 'pass args.groups (row_ids, from `python3 catlog.py sample`) or args.rows' }

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      row_id: { type: 'string' },
      verdict: { type: 'string', enum: ['keep', 'drop'] },
      reason: { type: 'string', description: 'one line: what you checked and where (table/row/column, Methods)' },
    }, required: ['row_id', 'verdict', 'reason'] } },
  },
  required: ['verdicts'],
}

const audit = (group, k, model) => agent(
  `Scientific data curation for a enzyme-kinetics research catalog (published kcat/Km values only).
You are an INDEPENDENT, READ-ONLY auditor for CatLog v2. Check each row below against the paper and try to refute it.
Drop a row only when you can name what is wrong (with the table/row/column or sentence that shows it); a drop is
permanent. If you cannot check a row (unreadable page, missing supplement), keep it and start the reason with
"unverified:". Missing pH/temperature/conditions are not errors. A printed kcat/Km that disagrees with kcat ÷ Km is
not a reason to drop (user, 2026-10-10): keep all three as printed. If the stored value is wrong only because a unit
the paper itself shows is misprinted (another table prints the same cell in the right unit, or a block of the column's
kcat/Km closes only in another unit), give verdict drop with the reason starting 'unit_fix: <the right
unit_for_conversion>' and the evidence: it is corrected, not dropped. Do not modify any file except your verdict file.
The standard is the old system's audit (${OLD}, read-only): apply its science checks (article identity, value printed
exactly with its ± in the cited table/row/column, unit and conversion right, right metric (not Ki/K0.5/Kd/Vmax),
right enzyme/organism/variant/substrate/cofactor/pH/temperature, same-row pairing, not reprinted from another paper,
mutant not taken from a wild-type line). An older or synonymous name for the same organism (NCBI Taxonomy, e.g.
Pseudomonas maltophilia = Stenotrophomonas maltophilia), compound or enzyme is not a mismatch: check the synonym before
dropping on a name. A paper id that is not all digits (NP + 8 hex) has no PubMed record: check article identity against
the row's doi and title (Crossref: https://api.crossref.org/works/<doi>), never drop it for not being in PubMed. Ignore its bookkeeping fields (csv_*, provenance kinds, receipts, packages).
Audit blind, from the paper alone: never open database values (BRENDA, SABIO-RK, SKiD, STRENDA, OED, UniProt kinetics,
anything in ${DIR}/sources/ named after them, sources/uniprot_values.tsv, sources/ref/uniprot_kinetics.json.gz,
sources/db_values.tsv, sources/database_corrections.tsv, work/db_unmatched.tsv, work/dbcheck_*, and what carries
database comparisons: catlog_wide.*, work/database_compare.json, site_build/ (catlog-enriched*,
catlog-database-comparison*, details-*) and tools/site_patches/) or the old catalog. They are not evidence, and
agreement with them is measured separately.
For each row: the paper text is ${DIR}/texts/<pmid>.txt (plus ${DIR}/texts/<pmid>.supp.txt if it exists);
the original PDF/XML is named in ${DIR}/papers.tsv
(column text_source; grep "^<pmid>"). If a PDF table is garbled, re-render that page (pdftotext -f N -l N -layout)
or render it to an image in /tmp and look at it. Stored units: kcat s^-1, Km mM, kcat/Km mM^-1 s^-1 (code-converted).
${typeof group[0] === 'string'
  ? `Your rows are the entries of the JSON array in ${FILE} whose row_id is one of: ${group.join(', ')}.
Read that file first and work only on those rows.`
  : `Rows:\n${JSON.stringify(group, null, 1)}`}
Return one verdict per row_id, and write the same verdicts to ${DIR}/work/audit_${typeof group[0] === 'string' ? group[0] : group[0].row_id}.json as
{"verdicts": [{"row_id": "...", "verdict": "keep|drop", "reason": "..."}]} (validate it with python3 -c "import json;json.load(open(...))").`,
  { label: `audit${model ? '-' + model : ''}:${k}`, phase: 'Audit', schema: VERDICTS, ...(model ? { model } : {}) })

const GROUP = 4, LANES = Math.max(1, Math.min(9, Number(args && args.lanes) || 6))  // auditors live at once (the user, 2026-11-14: 6)
const groups = idGroups.length ? idGroups : []
for (let i = 0; !idGroups.length && i < rows.length; i += GROUP) groups.push(rows.slice(i, i + GROUP))
const lanes = Array.from({ length: Math.min(LANES, groups.length) }, (_, k) => async () => {
  const out = []
  for (let i = k; i < groups.length; i += LANES) {
    const r = (await audit(groups[i], i)) || (await audit(groups[i], i, 'sonnet'))  // a stopped auditor: other model
    if (r) out.push(...r.verdicts)
  }
  return out
})
const verdicts = (await parallel(lanes)).filter(Boolean).flat()
const drops = verdicts.filter(v => v.verdict === 'drop')
log(`${verdicts.length} audited, ${drops.length} drop`)
return {
  verdicts,
  record: verdicts.map(v => `python3 ${DIR}/catlog.py audited ${v.row_id} ${v.verdict} '${String(v.reason).replace(/'/g, "'\\''")}'`),
}
