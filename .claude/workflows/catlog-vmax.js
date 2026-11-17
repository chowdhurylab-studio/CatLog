export const meta = {
  name: 'catlog-vmax',
  description: 'CatLog v2: check a stored kcat that disagrees with the paper\'s own printed Vmax or specific activity; every proposed change is refuted by 3 independent checkers (args.lanes agents live, default 3)',
  whenToUse: 'After `python3 tools/vmax_sweep.py` and `python3 tools/vmax_sweep.py tasks <PMIDs>` (work/vmax_<PMID>.task.json). Pass args.pmids; args.lanes caps live agents. Then apply the surviving changes with `catlog.py unitfix` / `drop --file`, export and recheck.',
  phases: [{ title: 'Check', detail: 'one agent per paper (prompts/vmax.md), blind' },
           { title: 'Refute', detail: '3 independent refuters per proposed change; it survives only if at most 1 refutes' }],
}

const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const DIR = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!DIR.startsWith('/') || /[~$]/.test(DIR)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
const pmids = ((args && args.pmids) || []).map(String)
if (!pmids.length) return { error: 'pass args.pmids (from: python3 tools/vmax_sweep.py tasks <PMIDs>)' }
const bad = pmids.filter(p => !/^(\d{1,9}|NP[0-9A-F]{8})$/.test(p))
if (bad.length) return { error: `not paper ids (PMID or NP + 8 hex): ${bad.join(', ')}` }
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
    unit: { type: 'string', description: 'for unitfix: the unit code converts with (tested with units.normalize); "" for drop' },
    evidence: { type: 'string', description: 'the evidence string written for this row' },
  },
  required: ['row_id', 'metric', 'raw_value', 'action', 'unit', 'evidence'],
}
const VERDICT = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    verdict: { type: 'string', description: 'header_misprint | cell_slip | rate_not_comparable | mass_wrong | paper_disagrees | consistent' },
    summary: { type: 'string' },
    basis_check: { type: 'object', properties: { rate_is_a_maximal_rate: { type: 'boolean' }, rate_note: { type: 'string' },
                                                 mass_ok: { type: 'boolean' }, mass_note: { type: 'string' } },
                   required: ['rate_is_a_maximal_rate', 'rate_note', 'mass_ok', 'mass_note'] },
    changes: { type: 'array', items: CHANGE, description: 'only the rows whose action is unitfix or drop, copied from the file written' },
    problem: { type: 'string', description: 'empty string when the file was written; else only why it could not be (never remarks: those go in note)' },
    note: { type: 'string', description: 'optional remarks for the chat' },
  },
  required: ['pmid', 'verdict', 'summary', 'basis_check', 'changes', 'problem'],
}
const VOTES = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    rows: { type: 'array', items: { type: 'object', properties: { row_id: { type: 'string' }, refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['row_id', 'refuted', 'reason'] } },
    problem: { type: 'string' },
  },
  required: ['pmid', 'rows', 'problem'],
}

// Leading with what the work is keeps the safety filter from stopping agents on toxin/pathogen enzyme papers. The
// lean catlog-reader agent type: these checks read blind (no database values in the task files).
const CONTEXT = 'CatLog curation task (enzyme kinetics catalog, scientific research). '
const task = (p) => `Task file: ${DIR}/work/vmax_${p}.task.json (if it does not exist, write nothing and report the problem "no task file"). `
const run = (prompt, opts, model) => limited(() => agent(prompt, { agentType: 'catlog-reader', ...opts, ...(model ? { model } : {}) }))
// a result counts when it carries a verdict or votes: agents have put remarks in `problem`, so it never decides alone
const usable = (r) => !!r && ((r.rows && r.rows.length > 0) || !!r.verdict)
const again = async (step) => {  // a dead or empty agent is retried once on Sonnet (as catlog-batch)
  const a = await step()
  if (a && a.problem === 'no task file') return a
  return usable(a) ? a : ((await step('sonnet')) || a)
}

const check = (p) => again((model) => run(
  CONTEXT + `Follow ${DIR}/prompts/vmax.md for paper ${p}. ` + task(p) +
  `Write ${DIR}/work/vmax_${p}.json and nothing else in the folder (page images under /tmp). ` +
  'Return the verdict, the basis_check and, in changes, only the rows whose action is unitfix or drop.',
  { label: `check:${p}`, phase: 'Check', schema: VERDICT }, model))

const refute = (p, changes, k) => again((model) => run(
  CONTEXT + `Follow ${DIR}/prompts/vmax.md, section "Refute a proposed change", for paper ${p}, as refuter ${k}. ` + task(p) +
  `The proposed change (rows, action, unit, evidence): ${JSON.stringify(changes.map(c => ({ row_id: c.row_id, metric: c.metric, raw_value: c.raw_value, action: c.action, unit: c.unit, evidence: c.evidence })))}. ` +
  `Write ${DIR}/work/vmax_${p}.refute${k}.json and nothing else in the folder (page images under /tmp). Return one vote per row.`,
  { label: `refute${k}:${p}`, phase: 'Refute', schema: VOTES }, model))

const results = await pipeline(pmids,
  async (p) => ({ ...((await check(p)) || { pmid: p, verdict: '', summary: '', changes: [], problem: 'checker died twice' }) }),
  async (v, p) => {
    const proposed = (usable(v) && v.changes) || []
    if (!proposed.length) return { pmid: p, ...v, proposed, votes: [], survives: [], refuted: [] }
    const votes = (await parallel(Array.from({ length: REFUTERS }, (_, i) => () => refute(p, proposed, i + 1)))).filter(usable)
    const per = proposed.map((c) => {
      const vs = votes.map(x => x.rows.find(r => r.row_id === c.row_id)).filter(Boolean)
      return { ...c, votes: vs.length, refuted_by: vs.filter(x => x.refuted).length, reasons: vs.filter(x => x.refuted).map(x => x.reason) }
    })
    return { pmid: p, ...v, proposed, votes: votes.length,
             survives: per.filter(c => c.votes >= 2 && c.refuted_by <= MAX_REFUTED),
             refuted: per.filter(c => !(c.votes >= 2 && c.refuted_by <= MAX_REFUTED)) }
  })

const ok = results.filter(Boolean)
const survives = ok.flatMap(r => (r.survives || []).map(c => ({ pmid: r.pmid, ...c })))
log(`${ok.length} of ${pmids.length} papers checked; ${survives.length} changes survived 3 refuters`)
return {
  papers: ok.map(r => ({ pmid: r.pmid, verdict: r.verdict, summary: (r.summary || '').slice(0, 160),
                         rate_is_a_maximal_rate: r.basis_check && r.basis_check.rate_is_a_maximal_rate,
                         mass_ok: r.basis_check && r.basis_check.mass_ok,
                         proposed: (r.proposed || []).length, survives: (r.survives || []).length,
                         refuted: (r.refuted || []).length, problem: r.problem || '' })),
  survives,
  refuted: ok.flatMap(r => (r.refuted || []).map(c => ({ pmid: r.pmid, row_id: c.row_id, action: c.action, unit: c.unit,
                                                         refuted_by: c.refuted_by, votes: c.votes, reasons: c.reasons }))),
  apply: 'python3 catlog.py unitfix <unit> "<evidence>" <row_id>...   |   python3 catlog.py drop --file <file>',
}
