export const meta = {
  name: 'catlog-corrigendum',
  description: 'CatLog v2: three independent agents map every stored value and censored value of a corrected article and of its correction notice (corrigendum, erratum) to the notice; tools/corrigendum.py then applies only what all three agree on',
  whenToUse: 'When `python3 catlog.py status` lists "Correction notices" (a notice corrects an article that still has stored values; CLAUDE.md "Correction notices"). Pass args {article, notice} (paper ids as strings; catalog, bounds, outdir and note only to test against copies). Then `python3 tools/corrigendum.py ARTICLE NOTICE` (dry run), read it, and `--apply`; export and recheck.',
  phases: [{ title: 'Verify', detail: 'three agents, each blind to the others' }],
}

const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const ROOT = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!ROOT.startsWith('/') || /[~$]/.test(ROOT)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
const article = String((args && args.article) || '')
const notice = String((args && args.notice) || '')
const ID = /^(\d{1,9}|NP[0-9A-F]{8})$/
if (!ID.test(article) || !ID.test(notice) || article === notice) {
  return { error: 'pass args.article and args.notice: two different paper ids (PMID or NP + 8 hex)' }
}
const CATALOG = String((args && args.catalog) || 'catalog.jsonl')  // copies only for a test run
const BOUNDS = String((args && args.bounds) || 'bounds.jsonl')
const OUTDIR = String((args && args.outdir) || `${ROOT}/work/corrigendum_${article}/${notice}`)
const SCRATCH = String((args && args.scratch) || '/tmp')
const EXTRA = String((args && args.note) || '')  // a test run's extra instruction

const SCHEMA = {
  type: 'object',
  properties: {
    relation: { type: 'string', enum: ['authors_correction', 'not_a_correction', 'unsure'] },
    relation_why: { type: 'string' },
    rows: { type: 'array', items: { type: 'object', properties: {
      paper: { type: 'string', enum: ['article', 'notice'] }, row_id: { type: 'string' },
      table: { type: 'string' }, variant: { type: 'string' }, substrate: { type: 'string' }, metric: { type: 'string' },
      column: { type: 'string' }, article_cell: { type: 'string' }, notice_cell: { type: 'string' },
      decision: { type: 'string', enum: ['UNCHANGED', 'SUPERSEDED', 'UNIT', 'WITHDRAWN', 'RELABEL', 'CORRECTED', 'REPRINTED', 'NOT_OWN', 'UNSURE'] },
      other_row_id: { type: 'string' }, why: { type: 'string' },
    }, required: ['paper', 'row_id', 'table', 'variant', 'substrate', 'metric', 'column', 'article_cell', 'notice_cell', 'decision', 'other_row_id', 'why'] } },
    note: { type: 'string' },
  },
  required: ['relation', 'relation_why', 'rows', 'note'],
}

const fields = "('row_id','enzyme','variant','substrate','metric','raw_value','raw_unit','unit_for_conversion','censored','limit','location','conditions','metric_note','quote')"
const list = p => `python3 -c "import json;[print(json.dumps({k:x.get(k) for k in ${fields}})) for f in ('${CATALOG}','${BOUNDS}') for x in map(json.loads,open(f)) if x['pmid']=='${p}']"`

const prompt = k => `CatLog v2 correction check (enzyme-kinetics curation for a public catalog of kcat/Km values, working directory ${ROOT}). The catalog's log says PMID ${notice} is the authors' correction notice (corrigendum, erratum) of PMID ${article}. CatLog keeps each value under the paper that first printed it correctly: the article's values the notice leaves unchanged stay under the article, the cells it corrects belong to the notice, and the article's superseded values and the notice's unchanged copies are dropped. You decide this for every stored value and censored value of both papers, independently of two other agents doing the same.

1. List the stored rows of the article: ${list(article)}
   and of the notice: ${list(notice)}
   (a row with "censored" set is a bound or a not-detected value: its cell is its sign or marker with its limit)
2. Read both papers yourself: texts/${article}.txt and texts/${notice}.txt (and their .supp.txt), and the original files named in the text_source column of papers.tsv (\`cut -f1-5 papers.tsv | grep "^<PMID>[[:space:]]"\`). Render PDF pages with pdftoppm at 300 dpi or more (turn rotated tables upright) and read the cells from the images; for an XML article read its table elements; for a .docx supplement unzip word/document.xml. A table may print a quantity in two columns (raw and normalized): a stored row's quote and location say which column it came from.
3. relation: authors_correction only when the notice names the article (citation, DOI or title) and corrects values the article printed; not_a_correction otherwise; unsure if you cannot tell. Give relation_why.
4. The notice's cell for an article row is its corrected cell, never one in a table or sentence it prints as the original or wrong one ("Original", the words before "should read"). For every article row: UNCHANGED = the notice prints the same value, +- and unit for it, or does not print it again and does not say it changed; SUPERSEDED = it prints a different value or +- for it, or a new unit with the cell (give in notice_cell the number and +- exactly as printed, a changed unit in why); UNIT = it changes only the unit or header multiplier of this cell in words and prints no new cell (give in notice_cell the unit spelled as code should convert the printed number with it: code multiplies by a header multiplier as written, so a header that means the opposite is given in its converting spelling, prompts/verify.md rule 3); WITHDRAWN = it withdraws this value without a replacement (e.g. the variant was not what was measured), or replaces it with a cell CatLog does not store (a marker it defines as not determined, a Hill constant, a range); RELABEL = it changes only a label, condition or qualifier of the value (say which in why); UNSURE = you cannot read it or cannot tell which cell it is. For SUPERSEDED give in other_row_id the notice's stored row that holds the corrected cell, or "none".
5. For every notice row: CORRECTED = its cell differs from the article's cell for the same table, column, variant and substrate (value, +- or unit), or the article never printed it; REPRINTED = it is the article's cell printed again unchanged (value, +- and unit); NOT_OWN = it is a value the notice prints as the original or wrong one, or one the notice or the article credits to other work (a footnote, caption, citation in the row label, "previously reported"): say which in why; UNSURE as above. For REPRINTED give in other_row_id the article's stored row with that cell, or "none".
6. Judge every listed row of both papers. Write ${OUTDIR}/verify_${k}.json with the same content as your structured result (create the folder if needed; save as you go). Work in a new, empty folder ${SCRATCH}/corrigendum_${article}_${notice}_${k}/ (add a suffix if it exists) and run python on extracted or downloaded files with -I. Legitimate access only (files on disk, Europe PMC / PMC open access, the Elsevier API via tools/fetch.py helpers fetch.elsevier_key() and fetch.UA, never printing the key); no paywall or bot-check bypass.
Do not open ${OUTDIR}/verify_* files other than yours before your own decisions are written, nor anything under ${OUTDIR}/applied_*. Never drop or edit catalog rows or files under texts/ or papers/. Return the structured result.${EXTRA ? '\n' + EXTRA : ''}`

const out = await parallel(['a', 'b', 'c'].map(k => () =>
  agent(prompt(k), { label: `verify:${k}`, phase: 'Verify', schema: SCHEMA }).then(r => ({ k, r }))))
const ok = out.filter(Boolean).filter(x => x.r)
if (ok.length < 3) {
  return { error: `only ${ok.length} of 3 agents finished: run the workflow again (tools/corrigendum.py refuses fewer than three verdict files)` }
}
const by = {}
for (const x of ok) for (const row of x.r.rows) (by[`${row.paper}:${row.row_id}`] = by[`${row.paper}:${row.row_id}`] || {})[x.k] = row.decision
const agreed = (d) => Object.entries(by).filter(([, v]) => Object.keys(v).length === 3 && Object.values(v).every(x => x === d)).map(([id]) => id)
log(`${ok.length} of 3 verifiers (relation: ${ok.map(x => x.r.relation).join(', ')}); superseded ${agreed('SUPERSEDED').length}, reprinted ${agreed('REPRINTED').length} (all three); next: python3 tools/corrigendum.py ${article} ${notice}`)
return { article, notice, verifiers: ok.length, relation: ok.map(x => x.r.relation),
         superseded: agreed('SUPERSEDED'), unit: agreed('UNIT'), withdrawn: agreed('WITHDRAWN'), reprinted: agreed('REPRINTED'),
         not_own: agreed('NOT_OWN'),
         disputed: Object.entries(by).filter(([, v]) => new Set(Object.values(v)).size > 1 || Object.keys(v).length < 3).map(([id, v]) => ({ id, v })) }
