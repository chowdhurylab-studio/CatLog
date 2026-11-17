export const meta = {
  name: 'catlog-reprint-pairs',
  description: 'CatLog v2: check suspect papers for silently reprinted values (cell by cell vs the earlier paper), then independently try to refute every REPRINT decision',
  phases: [
    { title: 'Check', detail: 'one agent per suspect paper: compare its shared cells with the earlier paper(s)' },
    { title: 'Refute', detail: 'one agent per paper with REPRINT rows: try to refute each decision; only confirmed rows count' },
  ],
}

const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const ROOT = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!ROOT.startsWith('/') || /[~$]/.test(ROOT)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
const SCRATCH = String((args && !Array.isArray(args) && args.scratch) || '/tmp/catlog-scratch')  // the agents' scratch folder (args.scratch)

const pmids = Array.isArray(args) ? args : ((args && args.pmids) || [])  // a list, or {pmids, root}
if (!pmids.length || pmids.some(p => typeof p !== 'string' || !/^(\d+|NP[0-9A-F]{8})$/.test(p))) {
  throw new Error('args must be a non-empty list of PMID strings (the later papers in work/reprint_pairs.tsv)')
}
const items = pmids.map(p => ({ pmid: p }))
log(`${items.length} suspect papers`)

const CHECK = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    refs_read: { type: 'array', items: { type: 'string' } },
    reprint_row_ids: { type: 'array', items: { type: 'string' } },
    own: { type: 'integer' },
    unsure_row_ids: { type: 'array', items: { type: 'string' } },
    note: { type: 'string' },
  },
  required: ['pmid', 'reprint_row_ids', 'own', 'unsure_row_ids', 'note'],
}
const REFUTE = {
  type: 'object',
  properties: {
    pmid: { type: 'string' },
    confirmed_row_ids: { type: 'array', items: { type: 'string' } },
    refuted: { type: 'array', items: { type: 'object', properties: { row_id: { type: 'string' }, why: { type: 'string' } }, required: ['row_id', 'why'] } },
    note: { type: 'string' },
  },
  required: ['pmid', 'confirmed_row_ids', 'refuted', 'note'],
}

const listRows = p => `python3 -c "import json;[print(json.dumps({k:x.get(k) for k in ('row_id','enzyme','variant','substrate','cosubstrate','metric','raw_value','raw_unit','location','conditions','quote')})) for x in map(json.loads,open('catalog.jsonl')) if x['pmid']=='${p}']"`

const checkPrompt = it => `CatLog v2 reprint check (enzyme-kinetics curation for a public catalog of kcat/Km values, working directory ${ROOT}). CatLog keeps a value only under the paper that first printed it as its own measurement (prompts/read.md "no reprinted values"; CLAUDE.md open item "Reprinted reference columns"). Worked examples of this exact check, with the standard and file format: work/reprint_26570983.json and work/reprint_12604203.json (read one first).

Suspect paper: PMID ${it.pmid}, text texts/${it.pmid}.txt (and texts/${it.pmid}.supp.txt if it exists). A scan (tools/reprint_pairs.py) found it shares printed values with earlier papers; its lines are: awk -F'\t' '$2=="${it.pmid}"' work/reprint_pairs.tsv (columns kind, later, earlier, shared, examples).
kind "catalog" = the earlier paper is also in catalog.jsonl, so its rows show its cells (list them the same way as below). kind "database" = an enzyme database lists the same numbers for the earlier paper: only a pointer (databases are not evidence); you must see the cell in the earlier paper itself.

1. List the suspect paper's catalog rows: ${listRows(it.pmid)}
2. Read each earlier paper: texts/<PMID>.txt if on disk, else get it legitimately: Europe PMC / PMC open access, the Elsevier API with this folder's key via tools/fetch.py helpers (fetch.elsevier_key(), fetch.UA; never print the key), publisher open access. No paywall or bot-check bypass; if you cannot read a cell, the row is UNSURE. Work in a new folder ${SCRATCH}/reprint_${it.pmid}/ and run python on downloaded files with -I. If a text has a GLYPH WARNING or the table is garbled OCR, render the page (pdftoppm) and read the cells from the image.
3. Check publication order (journal year/volume, not PMID alone). The reprint is in the LATER publication. If the suspect paper is actually the earlier one, its rows are OWN; say in note which other paper reprints them.
4. Decide for every suspect-paper row in the tables or passages that share values with an earlier paper, and their table-mates (same table, same enzyme/variant block):
   REPRINT = the same measurement the earlier paper already printed: same enzyme/variant/substrate/assay and an identical value with an identical +- (or the earlier paper prints no +-), or the same number on another stated basis, or a ratio computed only from reprinted cells.
   OWN = a different value or +-, a measurement the earlier paper does not print, or one the suspect paper states it measured in this work under its own conditions.
   UNSURE = the earlier cell cannot be seen, or it is genuinely ambiguous.
   Shared numbers alone are not proof: the same group often re-measures the same enzymes; one or two coincident cells among otherwise different values are OWN. A whole column or block of identical cells (with identical +-) is the reprint shape, whether or not the suspect paper cites the earlier one for it.
5. Write work/reprint_${it.pmid}.json as {"pmid": "${it.pmid}", "refs_read": [...], "rows": [{"row_id": "...", "metric": "...", "this_paper": "cell", "earlier_pmid": "...", "earlier_cell": "cell or null", "where": "earlier paper table/row", "decision": "REPRINT|OWN|UNSURE", "why": "..."}]}. Save it as you go (a usage limit can stop you). Rows not near any shared value can be left out.
Never drop or edit catalog rows or any file under texts/. Return the structured result (reprint_row_ids exactly as in your file).`

const refutePrompt = (it, c) => `CatLog v2 reprint verification (enzyme-kinetics curation for a public catalog, working directory ${ROOT}). A first agent compared PMID ${it.pmid} with earlier papers and marked these catalog rows REPRINT (the same measurement an earlier paper already printed, which CatLog keeps only under the earlier paper): ${JSON.stringify(c.reprint_row_ids)}. Its reasons are in work/reprint_${it.pmid}.json; the candidate earlier papers are the 'earlier' column of: awk -F'\t' '$2=="${it.pmid}"' work/reprint_pairs.tsv.

Your job is to try to REFUTE each REPRINT decision independently; a row is dropped from the catalog only if you confirm it.
For each row: list it (${listRows(it.pmid)}), find its cell in texts/${it.pmid}.txt yourself, and find the earlier paper's cell yourself (texts/<PMID>.txt, or the same legitimate routes: Europe PMC / PMC open access, Elsevier API via tools/fetch.py helpers without printing the key; no paywall bypass; read garbled tables from rendered page images). Do not trust the first agent's quotes. Confirm all of: the earlier paper was published first (year/volume); same enzyme and variant, same substrate and assay; identical value and identical +- (or the earlier paper prints no +-), or the same number on a basis the papers state; and the suspect paper does not say it measured this value itself in this work. If you cannot see both cells yourself, or any of these fails, REFUTE (the row stays). Work in a new folder ${SCRATCH}/refute_${it.pmid}/.
Write work/reprint_${it.pmid}.check.json as {"pmid": "${it.pmid}", "confirmed": [...row_ids], "refuted": [{"row_id": "...", "why": "..."}]}, saving as you go. Never drop or edit catalog rows. Return the structured result.`

const results = await pipeline(
  items,
  it => agent(checkPrompt(it), { label: `check:${it.pmid}`, phase: 'Check', schema: CHECK }),
  (c, it) => {
    if (!c) return { pmid: it.pmid, check: null, refute: null }
    if (!c.reprint_row_ids.length) return { pmid: it.pmid, check: c, refute: null }
    return agent(refutePrompt(it, c), { label: `refute:${it.pmid}`, phase: 'Refute', schema: REFUTE })
      .then(r => ({ pmid: it.pmid, check: c, refute: r }))
  },
)

const done = results.filter(Boolean)
const confirmed = done.flatMap(r => (r.refute ? r.refute.confirmed_row_ids.map(id => ({ pmid: r.pmid, row_id: id })) : []))
const noCheck = done.filter(r => !r.check).map(r => r.pmid)
const noRefute = done.filter(r => r.check && r.check.reprint_row_ids.length && !r.refute).map(r => r.pmid)
log(`${done.length} checked; ${done.filter(r => r.check && r.check.reprint_row_ids.length).length} papers with REPRINT rows; ${confirmed.length} rows confirmed; no result: ${noCheck.length}; refute missing: ${noRefute.length}`)
return { results: done, confirmed, no_check: noCheck, no_refute: noRefute }
