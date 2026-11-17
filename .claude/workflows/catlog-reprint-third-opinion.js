export const meta = {
  name: 'catlog-reprint-third-opinion',
  description: 'CatLog v2: two independent agents per paper judge reprint rows the first two agents split on (mis-copied or recomputed carry-overs)',
  phases: [{ title: 'Judge', detail: 'two independent agents per paper, different lenses' }],
}
const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const ROOT = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!ROOT.startsWith('/') || /[~$]/.test(ROOT)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
const SCRATCH = String((args && !Array.isArray(args) && args.scratch) || '/tmp/catlog-scratch')  // the agents' scratch folder (args.scratch)
const CASES = args && args.cases
if (!Array.isArray(CASES) || !CASES.length || CASES.some(c => !c.pmid || !Array.isArray(c.row_ids) || !c.row_ids.length)) throw new Error('args.cases must list {pmid, row_ids, earlier}')

const VERDICT = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    rows: { type: 'array', items: { type: 'object', properties: {
      row_id: { type: 'string' },
      verdict: { type: 'string', enum: ['NOT_OWN', 'OWN', 'UNSURE'] },
      suspect_cell: { type: 'string' },
      earlier_cell: { type: 'string' },
      why: { type: 'string' },
    }, required: ['row_id', 'verdict', 'suspect_cell', 'earlier_cell', 'why'] } },
    note: { type: 'string' },
  },
  required: ['pmid', 'rows', 'note'],
}
const listRows = p => `python3 -c "import json;[print(json.dumps({k:x.get(k) for k in ('row_id','enzyme','variant','substrate','cosubstrate','metric','raw_value','raw_unit','location','conditions','quote')})) for x in map(json.loads,open('catalog.jsonl')) if x['pmid']=='${p}']"`

const LENSES = {
  provenance: `Your lens is PROVENANCE: did the suspect paper itself measure the quantity in these rows in this work (its Methods, Results, captions, footnotes, supplement), or does it carry the numbers over from the earlier paper (stated or not)? Look for what the paper says about where these values come from and whether the neighbouring rows of the same table are carry-overs.`,
  cells: `Your lens is CELLS: compare the stored rows' cells with every row of the earlier paper's table yourself (render page images if the text is garbled). Establish exactly which earlier cell, row and column each number equals, whether the match is with the SAME enzyme/variant/substrate or another line of the earlier table, and whether a number differs only by a conversion of an identical earlier cell (e.g. the same Vmax converted with another factor).`,
}

const prompt = (c, lens) => `CatLog v2 reprint third opinion (enzyme-kinetics curation for a public catalog of kcat/Km values, working directory ${ROOT}). CatLog keeps a measurement only under the paper that first printed it as its own (prompts/read.md "no reprinted values"); it also must not keep a value under a label it does not belong to.

Suspect paper PMID ${c.pmid} (texts/${c.pmid}.txt; texts/${c.pmid}.supp.txt if it exists). Earlier paper: PMID ${c.earlier} (texts/${c.earlier}.txt if on disk; otherwise legitimate routes only: Europe PMC / PMC open access, the Elsevier API via tools/fetch.py helpers (fetch.elsevier_key(), fetch.UA; never print the key); no paywall or bot-check bypass). Work in a new folder ${SCRATCH}/third_${c.pmid}_${lens}/ and run python on downloaded files with -I.

Two earlier agents disagreed on these catalog rows: ${JSON.stringify(c.row_ids)}. The first said they reprint the earlier paper; the second refused because the numbers are not identical to the earlier cell for the SAME label: ${c.dispute}. Their files: work/reprint_${c.pmid}.json and work/reprint_${c.pmid}.check.json. Do not trust them: see every cell yourself.
List the rows: ${listRows(c.pmid)}

${LENSES[lens]}

For each row decide:
- NOT_OWN: you saw both cells yourself and the stored value is not the suspect paper's own measurement of what the row says: it is a number carried over from the earlier paper (from the same line, or from a different line of the earlier table printed under this label), or computed only from carried-over cells (e.g. the earlier paper's identical Vmax converted with a different factor, or a ratio of such numbers), and the suspect paper does not say it measured it in this work.
- OWN: the suspect paper measured it in this work (it says so, or the evidence shows a new measurement, e.g. different conditions), or the coincidence with the earlier paper is plausibly chance.
- UNSURE: you could not see a needed cell, or it is genuinely ambiguous.
Write work/reprint_${c.pmid}.third_${lens}.json with the same content as your structured result (save as you go). Never drop or edit catalog rows or files under texts/. Return the structured result.`

const out = await parallel(CASES.flatMap(c => Object.keys(LENSES).map(lens => () =>
  agent(prompt(c, lens), { label: `${lens}:${c.pmid}`, phase: 'Judge', schema: VERDICT }).then(r => ({ pmid: c.pmid, lens, r })))))
const ok = out.filter(Boolean)
const byRow = {}
for (const o of ok) for (const x of (o.r ? o.r.rows : [])) (byRow[x.row_id] = byRow[x.row_id] || []).push({ lens: o.lens, verdict: x.verdict })
const drop = Object.entries(byRow).filter(([, v]) => v.length === 2 && v.every(x => x.verdict === 'NOT_OWN')).map(([k]) => k)
log(`${ok.length} judges returned; rows both call NOT_OWN: ${drop.length}`)
return { results: ok, both_not_own: drop }
