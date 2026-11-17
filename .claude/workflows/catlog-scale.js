export const meta = {
  name: 'catlog-scale',
  description: 'CatLog v2: decide which column of a table is misprinted when kcat/Km misses kcat ÷ Km by a unit factor; every proposed unit change is refuted by 3 independent checkers (args.lanes agents live, default 3)',
  whenToUse: 'After `python3 tools/scale_sweep.py` and `python3 tools/scale_sweep.py tasks <PMIDs>` (work/scale_<PMID>.task.json). Pass args.pmids; args.existing ({pmid: {tables, changes}}) skips the first check for verdicts already on file. Then apply the surviving changes with `catlog.py unitfix` / `drop --file`, export and recheck.',
  phases: [
    { title: 'Check', detail: 'one blind checker per paper (prompts/scale.md) -> work/scale_<PMID>.json' },
    { title: 'Second look', detail: 'tables called ambiguous: a fresh checker looks for a printed fact that decides' },
    { title: 'Refute', detail: '3 independent refuters per proposed change; it survives only if at most 1 refutes' },
  ],
}

const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const DIR = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!DIR.startsWith('/') || /[~$]/.test(DIR)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
const pmids = (Array.isArray(args) ? args : (args && args.pmids) || []).map(String)
if (!pmids.length) return { error: 'pass args.pmids (papers with work/scale_<PMID>.task.json: python3 tools/scale_sweep.py tasks <PMIDs>)' }
const bad = pmids.filter(p => !/^(\d{1,9}|NP[0-9A-F]{8})$/.test(p))
if (bad.length) return { error: `not paper ids (PMID or NP + 8 hex): ${bad.join(', ')}` }
const existing = (args && args.existing) || {}
const REFUTERS = 3
const MAX_REFUTED = 1  // a change is applied only when at most 1 of the 3 refuters refutes it, and the chat reads that reason

// never more than `lanes` agents live, across papers and stages (CLAUDE.md: 3 while another chat is reading)
const LANES = Math.max(1, parseInt(args && args.lanes, 10) || 3)
let active = 0
const waiting = []
const slot = () => { if (active < LANES && waiting.length) { active++; waiting.shift()() } }
const limited = (fn) => new Promise((resolve) => {
  waiting.push(() => fn().then((v) => { active--; resolve(v); slot() }, () => { active--; resolve(null); slot() }))
  slot()
})

const CHANGE = {
  type: 'object',
  properties: {
    row_id: { type: 'string' }, metric: { type: 'string' }, raw_value: { type: 'string' },
    action: { type: 'string', enum: ['unitfix', 'drop'] },
    unit: { type: 'string', description: 'for unitfix: the unit code converts with (tested with units.normalize)' },
    evidence: { type: 'string', description: 'the evidence string written for this row' },
  },
  required: ['row_id', 'metric', 'raw_value', 'action', 'unit', 'evidence'],
}
const VERDICT = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    tables: { type: 'array', items: { type: 'object', properties: { table: { type: 'string' }, verdict: { type: 'string' }, summary: { type: 'string' } }, required: ['table', 'verdict', 'summary'] } },
    changes: { type: 'array', items: CHANGE, description: 'only the rows whose action is unitfix or drop, copied from the file written' },
    problem: { type: 'string', description: 'empty string when the file was written; else only why it could not be (never remarks: those go in note)' },
    note: { type: 'string', description: 'optional remarks for the chat' },
  },
  required: ['pmid', 'tables', 'changes', 'problem'],
}
const VOTES = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    rows: { type: 'array', items: { type: 'object', properties: { row_id: { type: 'string' }, refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['row_id', 'refuted', 'reason'] } },
    problem: { type: 'string', description: 'empty string when the file was written; else only why it could not be (never remarks: those go in note)' },
    note: { type: 'string', description: 'optional remarks for the chat' },
  },
  required: ['pmid', 'rows', 'problem'],
}

// Leading with what the work is keeps the safety filter from stopping agents on toxin/pathogen enzyme papers. The
// lean catlog-reader agent type: these checks read blind (no database values in the task files).
const CONTEXT = 'CatLog curation task (enzyme kinetics catalog, scientific research). '
const task = (p) => `Task file: ${DIR}/work/scale_${p}.task.json (if it does not exist, write nothing and report the problem "no task file"). `
const run = (prompt, opts, model) => limited(() => agent(prompt, { agentType: 'catlog-reader', ...opts, ...(model ? { model } : {}) }))
// a result counts when it carries tables or votes: agents have put remarks in `problem` (first run, 2026-10-20: two
// 15797234 refuters noted a Results sentence there, were retried and their votes dropped), so it never decides alone
const usable = (r) => !!r && ((r.rows && r.rows.length > 0) || (r.tables && r.tables.length > 0))
const again = async (step) => {  // a dead or empty agent is retried once on Sonnet (as catlog-batch)
  const a = await step()
  if (a && a.problem === 'no task file') return a
  return usable(a) ? a : ((await step('sonnet')) || a)
}

const check = (p) => again((model) => run(
  CONTEXT + `Follow ${DIR}/prompts/scale.md for paper ${p}. ` + task(p) +
  `Write ${DIR}/work/scale_${p}.json and nothing else in the folder (page images under /tmp). ` +
  'Return the tables with their verdicts and, in changes, only the rows whose action is unitfix or drop.',
  { label: `check:${p}`, phase: 'Check', schema: VERDICT }, model))

const second = (p, first) => again((model) => run(
  CONTEXT + `Follow ${DIR}/prompts/scale.md, section "Second look", for paper ${p}. ` + task(p) +
  `The first check called these tables ambiguous: ${JSON.stringify(first.tables.filter(t => /ambiguous/.test(t.verdict)))}. ` +
  `Write ${DIR}/work/scale_${p}.second.json and nothing else in the folder (page images under /tmp). ` +
  'Return the tables with their verdicts and, in changes, only the rows whose action is unitfix or drop.',
  { label: `second:${p}`, phase: 'Second look', schema: VERDICT }, model))

const refute = (p, changes, k) => again((model) => run(
  CONTEXT + `Follow ${DIR}/prompts/scale.md, section "Refute a proposed change", for paper ${p}, as refuter ${k}. ` + task(p) +
  `The proposed change (rows, unit, evidence): ${JSON.stringify(changes.map(c => ({ row_id: c.row_id, metric: c.metric, raw_value: c.raw_value, action: c.action, unit: c.unit, evidence: c.evidence })))}. ` +
  `Write ${DIR}/work/scale_${p}.refute${k}.json and nothing else in the folder (page images under /tmp). Return one vote per row.`,
  { label: `refute${k}:${p}`, phase: 'Refute', schema: VOTES }, model))

const results = await pipeline(pmids,
  async (p) => existing[p] ? { pmid: p, tables: existing[p].tables || [], changes: existing[p].changes || [], problem: '', from: 'existing' }
                           : { ...((await check(p)) || { pmid: p, tables: [], changes: [], problem: 'checker died twice' }), from: 'check' },
  async (v, p) => {
    if (!usable(v) || v.changes.length || !v.tables.some(t => /ambiguous/.test(t.verdict))) return { first: v }
    const s = (await second(p, v)) || { pmid: p, tables: [], changes: [], problem: 'second look died twice' }
    return { first: v, second: s }
  },
  async (r, p) => {
    const proposed = (r.second && usable(r.second) && r.second.changes.length ? r.second.changes : r.first.changes) || []
    if (!proposed.length) return { pmid: p, ...r, proposed, votes: [], survives: [], refuted: [] }
    const votes = (await parallel(Array.from({ length: REFUTERS }, (_, i) => () => refute(p, proposed, i + 1)))).filter(usable)
    const tally = proposed.map(c => {
      const vs = votes.map(v => (v.rows || []).find(x => x.row_id === c.row_id)).filter(Boolean)
      return { ...c, votes: vs.length, refuted_by: vs.filter(x => x.refuted).length, reasons: vs.filter(x => x.refuted).map(x => x.reason) }
    })
    const ok = (t) => t.votes === REFUTERS && t.refuted_by <= MAX_REFUTED
    log(`${p}: ${tally.filter(ok).length} of ${tally.length} proposed changes survive`)
    return { pmid: p, ...r, proposed, votes: votes.length, notes: votes.map(v => v.note || v.problem).filter(Boolean),
             survives: tally.filter(ok), refuted: tally.filter(t => !ok(t)) }
  })

return {
  results: results.filter(Boolean).map(r => ({
    pmid: r.pmid, first: r.first && { from: r.first.from, tables: r.first.tables, problem: r.first.problem },
    second: r.second && { tables: r.second.tables, problem: r.second.problem },
    survives: r.survives, refuted: r.refuted, notes: r.notes,
  })),
  apply: 'unitfix the surviving rows per unit with their evidence (python3 catlog.py unitfix "<unit>" "<evidence>" <row_ids>), drop --file for surviving drops; read every refutation reason first',
}
