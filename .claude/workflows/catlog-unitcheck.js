export const meta = {
  name: 'catlog-unitcheck',
  description: 'CatLog v2: one blind checker decides the unit of a table column from the paper\'s own numbers, then 3 refuters test every change it proposes',
  phases: [{ title: 'Check', detail: 'one blind checker' }, { title: 'Refute', detail: '3 independent refuters' }],
}

const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const DIR = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!DIR.startsWith('/') || /[~$]/.test(DIR)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
const SCRATCH = String((args && !Array.isArray(args) && args.scratch) || '/tmp/catlog-scratch') + '/unitcheck'  // the agents' scratch folder (args.scratch)
const P = String((args && args.pmid) || '')
if (!/^\d{1,9}$/.test(P)) return { error: 'args.pmid must be a PMID with work/unitcheck_<PMID>.task.json' }

const CTX = 'CatLog curation task (enzyme kinetics catalog, scientific research). '
const BLIND = `Read blind, as ${DIR}/prompts/read.md "Read blind" says: use only this paper's own files (the task file names its text and original file; page images you render with pdftoppm are fine). Never open database values (anything under ${DIR}/sources/, catlog_wide.*, work/dbcheck_*, work/db_unmatched.tsv), human_review/, work/old/, catalog.jsonl, rejected.jsonl, any other work/ file, or anything under ~/Documents/realkcat.`
const RULE = `CatLog's rule (${DIR}/prompts/read.md, verify.md): code converts the printed cell, and a unit is changed only when the paper's own facts show the printed unit or scale is a misprint, never because a value looks implausible. A value that is right as printed is left alone.`

const CHECK = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    column_verdict: { type: 'string', description: 'one line: do the column\'s cells share one unit, and which' },
    rows: { type: 'array', items: { type: 'object', properties: {
      row_id: { type: 'string' },
      action: { type: 'string', enum: ['keep', 'unitfix', 'drop', 'ambiguous'] },
      unit: { type: 'string' },
      evidence: { type: 'string' } }, required: ['row_id', 'action', 'evidence'] } },
    summary: { type: 'string' },
  },
  required: ['pmid', 'column_verdict', 'rows', 'summary'],
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

phase('Check')
const c = await agent(CTX + `Task file: ${DIR}/work/unitcheck_${P}.task.json. It holds the question, the paper's files, how to test a unit, and every stored row with its printed cell, printed unit, any unit_for_conversion already applied, and the stored converted value.

${RULE}

${BLIND}

Answer the task file's question. Derive each row's unit from the paper's own printed numbers (K_m, K_cat, V_max, the Methods' definition of a unit of activity, the enzyme's subunit mass, the Results text), and redo the arithmetic yourself. Do not assume the cells of one column share a scale: check each cell. Give every row one action: keep (the stored value is right), unitfix (with the unit in 'unit', tested as the task file shows), drop, or ambiguous. Evidence: printed facts only, every number as printed, at most 300 characters each. Scratch files in ${SCRATCH}/check-${P}/. Write ${DIR}/work/unitcheck_${P}.check.json ({pmid, column_verdict, rows, summary}), validate it (python3 -c "import json;json.load(open(...))") and return the same object.`,
  { label: `check:${P}`, phase: 'Check', schema: CHECK, agentType: 'catlog-reader' })

const proposed = ((c && c.rows) || []).filter(r => r.action === 'unitfix' || r.action === 'drop')
log(`${c ? c.rows.length : 0} rows checked, ${proposed.length} change(s) proposed`)
if (!proposed.length) return { pmid: P, column_verdict: c && c.column_verdict, proposed: 0, summary: c && c.summary }

phase('Refute')
const votes = (await parallel([1, 2, 3].map(k => () => agent(CTX + `You are refuter ${k} of 3, working alone, for paper ${P}. Task file: ${DIR}/work/unitcheck_${P}.task.json. A checker proposes these changes (row_id | action | unit | evidence):
${proposed.map(r => `${r.row_id} | ${r.action} | ${r.unit || ''} | ${r.evidence}`).join('\n')}

Its verdict on the column: ${c.column_verdict}

${RULE}

${BLIND}

Try to show each proposed change is wrong: re-read the cited table, header and cells in the paper; check every cited number is printed as cited; redo the arithmetic yourself from the paper's own K_m, K_cat, V_max and the Methods; and look for a printed fact that contradicts the change. A row is refuted when a cited fact is not in the paper or is misquoted, the arithmetic does not hold, a printed fact contradicts it, or another unit fits the paper's numbers as well. refuted=false only when every cited fact checks out and together they decide the unit. When unsure, refuted. Scratch files in ${SCRATCH}/refute${k}-${P}/. Write ${DIR}/work/unitcheck_${P}.refute${k}.json ({pmid, refuter: ${k}, rows, summary}) and return the same.`,
  { label: `refute${k}:${P}`, phase: 'Refute', schema: VOTES, agentType: 'catlog-reader' })))).filter(v => v && Array.isArray(v.rows))

const counts = {}
// a refuter that leaves a row out counts as refuting it (when unsure, refuted)
for (const r of proposed) counts[r.row_id] = votes.filter(v => !v.rows.some(x => x.row_id === r.row_id && x.refuted === false)).length + (3 - votes.length)
return { pmid: P, column_verdict: c.column_verdict, summary: c.summary, votes: votes.length,
         proposed: proposed.map(r => ({ row_id: r.row_id, action: r.action, unit: r.unit, refuted: counts[r.row_id] })) }
