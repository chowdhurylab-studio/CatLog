export const meta = {
  name: 'catlog-nd-census',
  description: 'CatLog v2 n.d. census: check papers read before the n.d. rule, and on no n.d. list, for a censored kcat/Km/kcat-Km (one lean agent per group of up to 4 papers)',
  whenToUse: 'Resume with the args `python3 tools/nd_census.py next N` prints (tools/nd_census.py says why and how); `status` shows progress, `record` lists the yes papers at the end',
  phases: [{ title: 'Census', detail: 'one catlog-reader agent per group; verdicts in work/nd_census/group_<n>.json' }],
}

const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const ROOT = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!ROOT.startsWith('/') || /[~$]/.test(ROOT)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
// args.groups = [{n, pmids}] (the pilot), or args.from / args.to = group numbers in sources/nd_census_groups.json,
// whose papers each agent prints itself (keeps the launch small)
const LANES = (args && args.lanes) || 3
let groups = args && args.groups
if (!groups && args && Number.isInteger(args.from) && Number.isInteger(args.to) && args.to >= args.from)
  groups = Array.from({ length: args.to - args.from + 1 }, (_, i) => ({ n: args.from + i }))
const skip = new Set((args && args.skip) || [])
groups = (groups || []).filter(g => !skip.has(g.n))
if (!groups.length || groups.some(g => typeof g.n !== 'number' ||
    (g.pmids && !g.pmids.every(p => /^(\d+|NP[0-9A-Fa-f]{8})$/.test(p)))))
  throw new Error('args.groups = [{n, pmids}] or args.from/args.to group numbers')

const SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          pmid: { type: 'string' },
          verdict: { type: 'string', enum: ['yes', 'no', 'unsure'] },
          kind: { type: 'string' },
          quote: { type: 'string' },
          where: { type: 'string' },
          what: { type: 'string' },
          why: { type: 'string' },
        },
        required: ['pmid', 'verdict', 'why'],
      },
    },
  },
  required: ['verdicts'],
}

const PROMPT = g => `CatLog n.d. census (folder ${ROOT}; a scientific catalog of published enzyme kinetics). Task: for each paper
below, decide whether it prints, as its own result, at least one kcat, Km or kcat/Km that CatLog's reading rule would
store as a censored value.

The rule: ${ROOT}/prompts/read.md, section "Censored values" (from line 171 to the next ## heading). Read it first. In short: a kcat, Km or
kcat/Km the paper tried to measure for a given enzyme or variant and substrate, printed only as a bound ("< 0.01",
"> 50 mM", "Km exceeded 10 mM") or as not detected: a table marker (ND, n.d., NA, —, 0, ...) that the footnote,
caption or text defines as not detected / no activity / below detection, or a sentence saying an enzyme or variant
showed no detectable (measurable) activity or turnover with a substrate ("the D45A mutant was catalytically inactive",
"no activity was detected with D-alanine"). Not counted: a marker defined as not determined / not tested, a marker or
dash defined nowhere, values from other work, a constant that could not be determined although the enzyme was active
(no saturation, very high Km, linear rate), a sentence naming no substrate when the paper never says which.

Papers (text in texts/<PMID>.txt, plus texts/<PMID>.supp.txt where that file exists): ${g.pmids ? g.pmids.join(', ') :
`group ${g.n}; print its PMIDs with: python3 -c "import json; print(' '.join(json.load(open('${ROOT}/sources/nd_census_groups.json'))['groups'][${g.n}]))"`}

For each paper in turn:
- grep -n for candidates first (ND, n.d., N.D., NA, n.a., NR, BD, —, –, <, >, ≤, ≥, inactive, inert, no activity,
  not detect, undetect, no detectable, no measurable, below detection, too low, not a substrate, not able, unable,
  abolish, did not, were not), then read the whole text in slices (Read with offset/limit). Grep alone is not enough:
  PDF text loses markers and glyphs (< printed as ',' or '⬍', − as '⫺', µ as 'm'), and plain sentences ("the K46A
  protein was inactive") have no fixed wording. Read every table with its footnotes, and Results and Discussion.
- Stop at the first value that clearly qualifies: verdict "yes", with quote (copied exactly from the text, containing
  the marker or bound; for a marker add the defining footnote words after " || "), where (table or section), what
  (enzyme, variant, substrate, metric), kind ("table" or "sentence").
- "no" only after reading the whole paper; in why, name the candidates you saw and why each does not count.
- "unsure" only when the text cannot decide (a garbled table, a marker whose definition the text lacks); say why.
- Text only: do not render page images or open database files.
After each paper, write all verdicts so far to ${ROOT}/work/nd_census/group_${g.n}.json as
{"group": ${g.n}, "verdicts": [{"pmid": "...", "verdict": "yes|no|unsure", "kind": "", "quote": "", "where": "", "what": "", "why": ""}]}
and check it parses: python3 -c "import json; json.load(open('${ROOT}/work/nd_census/group_${g.n}.json'))".
Return the same verdicts, one per paper of the group, every one of them.`

let dead = 0
const DEAD_STOP = 3
const lanes = Array.from({ length: LANES }, (_, i) => async () => {
  const out = []
  for (let k = i; k < groups.length; k += LANES) {
    if (dead >= DEAD_STOP) break
    const g = groups[k]
    const r = await agent(PROMPT(g), { agentType: 'catlog-reader', schema: SCHEMA, label: `census ${g.n}`, phase: 'Census' })
    if (!r || !Array.isArray(r.verdicts)) { dead++; out.push({ n: g.n, failed: true }); continue }
    dead = 0
    out.push({ n: g.n, verdicts: r.verdicts.map(v => ({ pmid: v.pmid, verdict: v.verdict })) })
  }
  return out
})
const res = (await parallel(lanes)).filter(Boolean).flat()
const v = res.flatMap(r => r.verdicts || [])
const count = k => v.filter(x => x.verdict === k).length
return {
  groups: groups.length, groups_done: res.filter(r => r.verdicts).length,
  failed: res.filter(r => r.failed).map(r => r.n),
  papers: v.length, yes: count('yes'), no: count('no'), unsure: count('unsure'),
  ...(dead >= DEAD_STOP ? { stop: `${DEAD_STOP} agents in a row returned nothing (usage limit?): lanes stopped` } : {}),
}
