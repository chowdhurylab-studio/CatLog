export const meta = {
  name: 'catlog-dbcheck',
  description: 'CatLog v2: check values that differ from an enzyme database against the paper (one agent per paper, args.lanes at a time, default 6)',
  whenToUse: 'After `python3 catlog.py dbdiff --pending N` prints "papers to check: ..." (it claims them, so no other chat checks the same papers); pass args.pmids (and args.lanes). catlog-batch runs it after its readers when given args.dbcheck. Then run `python3 catlog.py dbcheck-record`.',
  phases: [{ title: 'Database differences', detail: 'one agent per task file: the paper -> a verdict per difference' }],
}

// args.root: the CatLog folder to use (no default in this copy; catlog-batch passes its own)
const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const DIR = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!DIR.startsWith('/') || /[~$]/.test(DIR)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
// prompts name papers.tsv, texts/ and work/ without a folder: the task text below names it
const FOLDER = `The CatLog folder is ${DIR}: papers.tsv, texts/, work/ and catlog.py in the prompt are the ones in it. `
const pmids = (Array.isArray(args) ? args : (args && args.pmids) || []).map(String)
if (!pmids.length) return { error: 'pass args.pmids (from: python3 catlog.py dbdiff --pending N)' }
const bad = pmids.filter(p => !/^(\d{1,9}|NP[0-9A-F]{8})$/.test(p))
if (bad.length) return { error: `not paper ids (PMID or NP + 8 hex): ${bad.join(', ')}` }

// the same agent rules as catlog-batch's readers: a dead or failed agent is retried once on Sonnet, and 3 dead steps
// in a row (the session usage limit) stop new papers. Never the lean `catlog-reader` agent type: its instructions
// forbid database values, which a task file holds by design.
const run = (prompt, opts) => agent(prompt, opts)

const DONE = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    verdicts: { type: 'integer', description: 'verdicts written to work/dbcheck_<PMID>.json' },
    problem: { type: 'string', description: 'empty if fine; else why the file could not be written' },
  },
  required: ['pmid', 'verdicts', 'problem'],
}

// Leading with what the work is keeps the model's safety filter from stopping agents on toxin/pathogen enzyme papers.
// The task names prompts/dbcheck.md, never read.md or verify.md: these agents see database values by design and are
// not readers (human_review.blind_check counts only reading agents).
const CONTEXT = 'Scientific data curation for an enzyme-kinetics research catalog: check published kcat/Km values against one paper. '
const check = (pmid, model) => run(
  CONTEXT + FOLDER + 'If the paper is long, read the parts the task file points to (tables, the sentences quoted) first. ' +
  `Follow ${DIR}/prompts/dbcheck.md for ${/^\d+$/.test(pmid) ? 'PMID' : `paper (no PMID: identified by its DOI in ${DIR}/papers.tsv column 2)`} ${pmid}. ` +
  `Task file: ${DIR}/work/dbcheck_${pmid}.task.json (if it does not exist, write nothing and report the problem "no task file"). ` +
  `Paper: ${DIR}/texts/${pmid}.txt (and ${DIR}/texts/${pmid}.supp.txt if it exists). ` +
  `Write ${DIR}/work/dbcheck_${pmid}.json and validate it with: python3 -c "import json;json.load(open('${DIR}/work/dbcheck_${pmid}.json'))". ` +
  `Keep any scratch file you make (scripts, notes, rendered page images) in a folder of your own named dbcheck-${pmid} ` +
  `inside your scratchpad directory (or /tmp), never under a shared name such as build.py: agents for other papers ` +
  `work in the same directory at the same time. Do not edit any other file. Report the number of verdicts.`,
  { label: `dbcheck${model ? '-' + model : ''}:${pmid}`, phase: 'Database differences', schema: DONE, ...(model ? { model } : {}) })

let dead = 0
const DEAD_STOP = 3
const stopped = () => dead >= DEAD_STOP
const again = async (step) => {
  const a = await step()
  if (a && a.problem === 'no task file') return a  // nothing to check: not a dead agent, no retry
  const r = a && !a.problem ? a : ((await step('sonnet')) || a)
  dead = r && !r.problem ? 0 : dead + 1
  return r
}

// lanes take the next paper from one queue: never more than `lanes` agents live (the user's number, default 6)
const LANES = Math.max(1, parseInt(args && args.lanes, 10) || 6)
const queue = [...pmids]
const results = (await parallel(Array.from({ length: Math.min(LANES, pmids.length) }, () => async () => {
  const out = []
  while (queue.length && !stopped()) {
    const p = queue.shift()
    const r = await again((model) => check(p, model))
    out.push({ pmid: p, verdicts: r ? r.verdicts : null, problem: r ? r.problem : 'agent died twice: the task file stays (dbdiff --pending offers it again 3 h after its claim)' })
    log(`${p} checked`)
  }
  return out
}))).filter(Boolean).flat()
const done = new Set(results.map(r => r.pmid))
return { results, record: `python3 ${DIR}/catlog.py dbcheck-record`,
  ...(stopped() ? { stop: `${DEAD_STOP} agents in a row returned nothing (session usage limit): the lanes stopped taking new papers`,
                    not_started: pmids.filter(p => !done.has(p)) } : {}) }
