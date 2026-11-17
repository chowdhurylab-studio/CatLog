export const meta = {
  name: 'catlog-audit-followup',
  description: 'CatLog v2: after an audit finds an error that may repeat, one blind checker per paper checks every other row for it, and 3 refuters test every proposed change',
  phases: [{ title: 'Check', detail: 'one blind checker per paper' }, { title: 'Refute', detail: '3 refuters per paper with proposed changes' }],
}

const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const DIR = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!DIR.startsWith('/') || /[~$]/.test(DIR)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
const SCRATCH = String((args && !Array.isArray(args) && args.scratch) || '/tmp/catlog-scratch') + '/followup'  // the agents' scratch folder (args.scratch)
const pmids = ((args && args.pmids) || []).map(String)
if (!pmids.length || pmids.some(p => !/^\d{1,9}$/.test(p))) return { error: 'args.pmids must list PMIDs that have work/followup_<PMID>.task.json' }

const CTX = 'CatLog curation task (enzyme kinetics catalog, scientific research). '
const BLIND = `Read blind, as ${DIR}/prompts/read.md "Read blind" says: use only this paper's own files (the task file names them; page images you render from its PDF with pdftoppm are fine), and another paper's text in ${DIR}/texts/ only when this paper credits that paper for the values in question (find it via ${DIR}/papers.tsv by title or DOI). Never open database values (anything under ${DIR}/sources/, catlog_wide.*, work/dbcheck_*, work/db_unmatched.tsv), human_review/, work/old/, catalog.jsonl, rejected.jsonl, or anything under ~/Documents/realkcat except the original file the task file names.`
const RULES = `CatLog's rules (${DIR}/prompts/read.md and verify.md): it stores only a kcat, Km or kcat/Km the paper measured itself for the named enzyme, variant and substrate. A per-product, per-site or per-pathway partial rate is not the enzyme's kcat (read.md "Partial constants"). A Ki, Kd, K0.5 or activation constant, a Vmax or a relative activity is not a Km or kcat. A value printed again from another paper (cited or not) is not stored. A unit is changed only when the paper's own facts show the printed unit is a misprint (another table or the text prints the same quantity in the right unit, or the column's numbers close only in that unit), never because a value looks implausible. Code converts every value: never type a converted number.`

const CHECK = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    rows: { type: 'array', items: { type: 'object', properties: {
      row_id: { type: 'string' },
      action: { type: 'string', enum: ['keep', 'drop', 'unitfix', 'ambiguous'] },
      unit: { type: 'string' },
      evidence: { type: 'string' } }, required: ['row_id', 'action', 'evidence'] } },
    summary: { type: 'string' },
  },
  required: ['pmid', 'rows', 'summary'],
}
const VOTES = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    refuter: { type: 'integer' },
    rows: { type: 'array', items: { type: 'object', properties: {
      row_id: { type: 'string' }, refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['row_id', 'refuted', 'reason'] } },
    summary: { type: 'string' },
  },
  required: ['pmid', 'refuter', 'rows', 'summary'],
}

const check = (p) => agent(CTX + `An audit of paper ${p} found a value CatLog stored that is wrong in a way that may repeat in other rows of the same paper. Task file: ${DIR}/work/followup_${p}.task.json (the paper's files, the audit's finding with its evidence, and every other row CatLog stores from this paper, with row_id, metric, printed cell, unit, identity, location and quote).

${RULES}

${BLIND}

Check EVERY row of the task file for the error the audit found, and for that error only (do not re-audit rows for unrelated issues). Give each row one action:
- keep: not affected (a few words why, e.g. 'the enzyme's own kcat for this substrate, not a per-product rate');
- drop: the same error (name it with the printed facts);
- unitfix: the same misprinted unit; put the unit code should convert with in 'unit' (e.g. 'min^-1', '10^3 s^-1', 'uM^-1 s^-1') and test it on the row's printed cell: cd ${DIR} && python3 -c "import sys; sys.path.insert(0,'tools'); from units import normalize; print(normalize('<metric>', '<raw_value>', '<unit>'))" (metric kcat, Km or kcat/Km; it prints value, catalog unit, error);
- ambiguous: the paper cannot settle it (nothing changes).
Evidence: printed facts only (table, row, column, cell, header, sentence), every number as printed, at most 300 characters. Read numbers from page images where the paper is a PDF. Scratch files in ${SCRATCH}/check-${p}/. Write ${DIR}/work/followup_${p}.check.json ({pmid, rows: [{row_id, action, unit, evidence}], summary}) as you go, validate it (python3 -c "import json;json.load(open(...))"), and return the same object.`,
  { label: `check:${p}`, phase: 'Check', schema: CHECK, agentType: 'catlog-reader' })

const refute = (p, k, proposed) => agent(CTX + `You are refuter ${k} of 3, working alone, for paper ${p}. Task file: ${DIR}/work/followup_${p}.task.json (the paper's files, the audit's finding, every stored row). A checker proposes these changes (row_id | action | unit | evidence):
${proposed.map(r => `${r.row_id} | ${r.action} | ${r.unit || ''} | ${r.evidence}`).join('\n')}

${RULES}

${BLIND}

Try to show each proposed change is wrong: re-read the cited table, row, column, header and cell on the page image (or the publisher XML); find every fact the evidence cites and check it is printed as cited; redo its arithmetic; and look for a printed fact that contradicts the change (a statement that the value was measured here, a footnote, a sister table, the Results text). A row is refuted when a cited fact is not in the paper or is misquoted, the arithmetic does not hold, a printed fact contradicts the change, or another reading is as likely as the proposed one. It is refuted=false only when every cited fact checks out and together they decide the action (and the unit). When unsure, refuted. Scratch files in ${SCRATCH}/refute${k}-${p}/. Write ${DIR}/work/followup_${p}.refute${k}.json ({pmid, refuter: ${k}, rows: [{row_id, refuted, reason}], summary}) and return the same.`,
  { label: `refute${k}:${p}`, phase: 'Refute', schema: VOTES, agentType: 'catlog-reader' })

const results = await pipeline(pmids,
  (p) => check(p),
  async (c, p) => {
    const proposed = ((c && c.rows) || []).filter(r => r.action === 'drop' || r.action === 'unitfix')
    if (!proposed.length) return { pmid: p, checked: c ? c.rows.length : 0, proposed: 0, summary: c ? c.summary : 'checker returned nothing' }
    const votes = (await parallel([1, 2, 3].map(k => () => refute(p, k, proposed)))).filter(v => v && Array.isArray(v.rows))
    const counts = {}
    // a refuter that leaves a proposed row out counts as refuting it (when unsure, refuted)
    for (const r of proposed) counts[r.row_id] = votes.filter(v => !v.rows.some(x => x.row_id === r.row_id && x.refuted === false)).length
    if (votes.length < 3) log(`${p}: only ${votes.length} of 3 refuters returned; a missing refuter counts as refuting`)
    for (const r of proposed) counts[r.row_id] += 3 - votes.length
    return { pmid: p, checked: c.rows.length, proposed: proposed.length, votes: votes.length, refuted_counts: counts, summary: c.summary }
  })
return results.filter(Boolean)
