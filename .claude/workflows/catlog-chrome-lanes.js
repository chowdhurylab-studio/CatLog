export const meta = {
  name: 'catlog-chrome-lanes',
  description: "CatLog v2: download waiting papers in the user's own Chrome (Claude in Chrome), one agent per publisher lane, 3 lanes at once by default (up to 4) and never two method-A lanes together, each site stopped at its first bot check, every lane at low memory or disk",
  whenToUse: "When the user says Chrome is open for downloads and Claude in Chrome is connected; the licensed lanes only on the ISU campus network (jstage, microbiology, asm run anywhere). First `python3 catlog.py file` and `python3 catlog.py lanes` (papers per lane, sites waiting for the user's clear; one run at a time: never `lanes` or a second run while a lane_*.jsonl changed in the last 10 min, or the live run halts); pass args {lanes: {<lane>: <count>, ...}, tag: '<yyyymmdd><letter>'} (optional start: {<lane>: <index>} with built: '<lanes_built of the run it continues>', max_parallel 1-4, default 3). Afterwards `python3 catlog.py file`, `python3 catlog.py lanes-record`, and give the user each stopped site's link. Never resume a run with resumeFromRunId (a replay re-orders the chunks and would go back to a stopped site): start a new run as the result's `next` says.",
  phases: [
    { title: 'ACS', detail: 'acs: method A, one tab, >=25 s per paper' },
    { title: 'ScienceDirect', detail: "sd: the article's own View PDF, saved from the viewer, ~30 s per paper" },
    { title: 'Wiley', detail: 'wiley: main site, method A, one tab' },
    { title: 'Wiley sub-sites', detail: 'wiley_sub: febs., chemistry-europe., iubmb. ...: method A, one tab' },
    { title: 'Springer', detail: 'springer: fetch /content/pdf, fresh tab per paper; 204 = not licensed' },
    { title: 'OUP', detail: 'oup: Silverchair viewer, one tab' },
    { title: 'RSC', detail: 'rsc: Silverchair viewer, one tab' },
    { title: 'Portland', detail: 'portland: Silverchair viewer, one tab' },
    { title: 'PNAS', detail: 'pnas: method A, fresh tab per paper' },
    { title: 'J-STAGE', detail: 'jstage: free; method A on citation_pdf_url, fresh tab per paper' },
    { title: 'Microbiology', detail: 'microbiology: free; /deliver/fulltext PDF, fresh tab per paper' },
    { title: 'ASM', detail: 'asm: free; method A on /doi/pdf, fresh tab per paper, >=25 s per paper' },
  ],
}

const CATLOG_ROOT = ''  // the CatLog folder (absolute path) used when args.root is not given; this copy sets none
const DIR = String((args && !Array.isArray(args) && args.root) || CATLOG_ROOT).replace(/\/+$/, '')
if (!DIR.startsWith('/') || /[~$]/.test(DIR)) return { error: 'pass args.root: the CatLog folder as an absolute path (no ~ or $), or set CATLOG_ROOT in this file' }
const DL = DIR + '/work/downloads'
const H = `python3 ${DIR}/tools/lane_agent.py`  // paper list, progress lines, method-A renames, memory and disk

// Page scripts are sent exactly as written here: no backslashes in them (a template literal would eat a single one).
// host comes back with spaces for dots: Claude in Chrome hides most a.b.c host names ("[BLOCKED: JWT token]").
const WJS = "const W=/Just a moment|unusual (activity|traffic)|Access Denied|captcha|verify you are human|problem providing|Too Many Requests|Performing security verification|Validate User|Are you a robot|Client Challenge/i;const warn=W.test(document.title+' '+(document.body?.innerText||'').slice(0,3000))||/crawlprevention|__cf_chl/.test(location.href);const host=location.host.split('.').join(' ');"
const SAVE = k => `const b=await r.blob();o.status=r.status;o.head=new TextDecoder().decode(await b.slice(0,5).arrayBuffer());if(r.status===200&&o.head==='%PDF-'){const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='PMID'+id+'_${k}.pdf';document.body.appendChild(a);a.click();o.saved=true;o.kb=Math.round(b.size/1024)}`
const STOPJS = "if(o.warn||o.status===403||o.status===429)throw new Error('STOP '+JSON.stringify(o));"
// method C (Silverchair) and ScienceDirect, step 2: the tab shows the PDF viewer; save its bytes under our name
const VIEW = k => `const id='<id>';${WJS}let o={id,warn:warn||/robot/i.test(document.title),host,ct:document.contentType};if(!o.warn&&o.ct==='application/pdf'){const r=await fetch(location.href,{credentials:'include'});${SAVE(k)}}o`
const VIEWED = 'Then: saved=true = saved ("kb=<kb>"); warn or status 403/429 = STOP; ct not application/pdf = no_pdf ("the viewer showed <ct>"); any other status (e.g. 500) = error.'

const ONE_TAB = "This host is on the user's automatic-download allow list: create ONE tab at the start and reuse it for every paper."
const FRESH = "This host is NOT on the user's automatic-download allow list: Chrome saves only the first download per tab, so every paper gets a FRESH tab. Create one tab at the start; each paper's batch ends with tabs_create_mcp then tabs_close_mcp <tab> (create first: closing the group's last tab removes the group; the new tab's id, returned when the batch ends, is the tab for the next paper). Close tabs only there: closing a tab mid-batch breaks the rest of the batch. On a bot check the page script throws an error starting \"STOP\", which ends the batch before those steps, so that tab stays open for the user. If a batch fails before its last two steps for another reason, create a new tab and close that one in one batch, then go on."
const FREE_A = ['jstage']  // J-STAGE: empty clicks never stop it (= FREE_A in tools/lane_agent.py); not ASM, whose 403 on the PDF (10-11) is an empty click
const TAKE = (k, prog) => `Method A: Chrome names the saved file itself, so the helper finds and renames it (list took a snapshot of ~/Downloads; if take ever says there is none, run ${H} snap ${prog} once). After each click (clicked=true) run, with a Bash timeout of at least 120 s (a take whose click saved nothing waits about a minute): ${H} take ${prog} <id> ${k} '<doi>' '<host>'  (add --buy when the script said buy=true). It waits for the download, checks the file is a PDF, renames it PMID<id>_${k}.pdf and writes the paper's progress line itself: saved, no_access, error or STOP. A download that is a web page (a bot check, login or error page) is a STOP: then stop as the rules say. A click that saved nothing: (1) the paper's first empty click: take prints result "retry" and writes no line; run this paper's batch once more, then the same take command with --retry added (only for the paper that just printed retry, never on the next paper). (2) Its second empty click: take writes an error line ("clicked twice, no file"); go on to the next paper. (3) ${FREE_A.includes(k) ? 'This site is free, so empty clicks never stop this lane: every such paper gets its error line and you go on (only a bot check on the page or a web-page download stops it).' : 'When the paper before it in this chunk (papers with a no_pdf or no_access line aside) also ended that way, i.e. 4 empty clicks in a row, take writes STOP instead (a site refusing its PDFs, as PNAS did right after the user cleared it and as ASM does with a 403): then stop as the rules say.'} Papers you did not click get a log line.`
const WILEY = (k, prog, sub, gone) => `Wiley Online Library (${sub ? "the journals' own sub-sites: febs., chemistry-europe., iubmb., analyticalsciencejournals., nyaspubs., aiche., aocs. ...; their Cloudflare check comes back quickly, so stop at the first one" : 'main site onlinelibrary.wiley.com; a DOI may land on a journal sub-site, which takes the same method'}). ${ONE_TAB} Method A only: click the article's own pdfdirect link as a reader would; never fetch() a Wiley PDF (a scripted fetch drew Cloudflare 403s on the sub-sites even right after the user cleared them). ${TAKE(k, prog)} For each paper ONE browser_batch: navigate the tab to https://doi.org/<doi>; computer wait 5; javascript_exec:
const id='<id>',d='<doi>';${WJS}let o={id,warn,host,t:document.title.slice(0,40),wiley:location.host.endsWith('wiley.com'),gone:${JSON.stringify(gone)}.includes(location.host)};o.access=/Full Access|Free Access|Access provided by/i.test((document.body?.innerText||'').slice(0,8000));if(!o.warn&&!o.gone&&o.wiley&&!/^Error/.test(document.title)&&o.access){const a=document.createElement('a');a.href=location.origin+'/doi/pdfdirect/'+d+'?download=true';a.download='PMID'+id+'_${k}.pdf';document.body.appendChild(a);a.click();o.clicked=true}o
; computer wait 8. Then: warn = STOP; clicked = take; gone = no_pdf ("<host> stopped earlier this run"); wiley=false = no_pdf ("DOI went to <host>"); a title starting "Error" = no_pdf ("wiley error page"); access=false = no_access ("no Full/Free Access"). About 15 s per paper.`
// method C, step 1 on the article page (Silverchair: the PDF link redirects to watermark*.silverchair.com)
const C1 = (site, extra) => `${WJS}({warn,host,site:location.host.endsWith('${site}'),abstractOnly:/article-abstract|redirectedFrom=fulltext/.test(location.href)${extra}})`
const C2 = (k, wait1, wait2) => `(2) Otherwise ONE browser_batch: navigate the SAME tab to that pdf URL; computer wait ${wait1}; javascript_exec:
${VIEW(k)}
; computer wait ${wait2}. ${VIEWED}`

// a: method A (Chrome names the file: ~/Downloads is diffed, so never two at once); campus: needs ISU's licence;
// site: the lane's own host (a bot check there in one lane ends every lane on it)
const LANE = {
  acs: { phase: 'ACS', chunk: 30, a: true, campus: true, site: 'pubs.acs.org', how: (k, p) => `ACS (pubs.acs.org). ${ONE_TAB} ${TAKE(k, p)} At least 25 s per paper. For each paper ONE browser_batch: navigate the tab to https://doi.org/<doi>; computer wait 4; javascript_exec:
const id='<id>';${WJS}let o={id,warn,host,t:document.title.slice(0,40),acs:location.host.endsWith('acs.org')};const u=document.querySelector('meta[name=citation_pdf_url]')?.content;o.haspdf=!!u;o.buy=/Purchase|Get Access|Log in to view/i.test((document.body?.innerText||'').slice(0,6000));if(!o.warn&&o.acs&&u){const a=document.createElement('a');a.href=u;a.download='PMID'+id+'_acs.pdf';document.body.appendChild(a);a.click();o.clicked=true}o
; computer wait 10; computer wait 10. Then: warn = STOP; clicked = take; acs=false = no_pdf ("DOI went to <host>"); haspdf=false = no_pdf.` },
  sd: { phase: 'ScienceDirect', chunk: 25, campus: true, site: 'www.sciencedirect.com', how: k => `ScienceDirect (Elsevier; the PDF host pdf.sciencedirectassets.com is on the allow list). ${ONE_TAB} ScienceDirect blocks fast readers: strictly one paper at a time, about 30 s per paper; "There was a problem providing the content" or a robot page = STOP. Method: the article's own "View PDF" link (the first PDF link on a page can be a recommended article), opened in the tab by the page script itself (Claude in Chrome hides the link's path, so it is never typed), then saved from the viewer. For each paper: (1) ONE browser_batch: navigate the tab to https://doi.org/<doi>; computer wait 5; javascript_exec:
${WJS}const pii=(location.pathname.match(/pii.([A-Z0-9]+)/i)||[])[1]||'';const own=pii&&[...document.querySelectorAll('a')].find(e=>/View PDF/i.test(e.getAttribute('aria-label')||e.innerText||'')&&e.href&&new URL(e.href,location.href).pathname.includes(pii)&&!e.closest('[class*=ecommend],[class*=elated]'));const sd=location.host.endsWith('sciencedirect.com'),abstractOnly=location.pathname.includes('/abs/')||/Purchase PDF|Get Access|Check access|Get full text access|not subscribe/i.test((document.body?.innerText||'').slice(0,5000));const go=!warn&&sd&&!!own&&!abstractOnly;if(go)setTimeout(()=>location.assign('https://www.sciencedirect.com'+new URL(own.href,location.href).pathname),100);({warn,host,sd,hasOwnPdf:!!own,abstractOnly,go})
warn = STOP; sd=false = no_pdf ("DOI went to <host>"); abstractOnly = no_access ("abstract page only"); otherwise hasOwnPdf=false = no_pdf ("no View PDF link of its own": not a licence answer, so never no_access). (2) go=true (the tab is already opening the PDF): ONE browser_batch: computer wait 7; javascript_exec:
${VIEW(k)}
; computer wait 10; computer wait 5. ${VIEWED}` },
  wiley: { phase: 'Wiley', chunk: 40, a: true, campus: true, site: 'onlinelibrary.wiley.com', how: (k, p, g) => WILEY(k, p, false, g) },
  wiley_sub: { phase: 'Wiley sub-sites', chunk: 30, a: true, campus: true, site: '', how: (k, p, g) => WILEY(k, p, true, g) },
  springer: { phase: 'Springer', chunk: 50, campus: true, site: 'link.springer.com', how: k => `Springer (link.springer.com). ${FRESH} Method B: fetch the PDF into a blob saved under your own name (the page's own citation_pdf_url: it keeps the DOI's capitals, e.g. 10.1023/A:..., which a lower-case /content/pdf URL answers with a page). For each paper ONE browser_batch: navigate <tab> to https://doi.org/<doi>; computer wait 4; javascript_exec:
const id='<id>',d='<doi>';${WJS}let o={id,warn,host,t:document.title.slice(0,40)};if(!o.warn&&location.host.endsWith('springer.com')){const m=document.querySelector('meta[name=citation_pdf_url]')?.content||'';const r=await fetch(m.startsWith(location.origin+'/content/pdf/')?m:'/content/pdf/'+d+'.pdf',{credentials:'include'});${SAVE(k)}}${STOPJS}o
; computer wait 3; tabs_create_mcp; tabs_close_mcp <tab>. Then: saved=true = saved ("kb=<kb>"); status 204, or a 200 that is not a PDF = no_access ("HTTP 204" / "200 not a PDF": a licence gap, not a block); a host other than springer.com (Nature, OUP, a society site, a book page) = no_pdf ("DOI went to <host>"); any other status = error. About 10-12 s per paper.` },
  oup: { phase: 'OUP', chunk: 40, campus: true, site: 'academic.oup.com', how: k => `Oxford Academic (academic.oup.com; PDFs come from watermark*.silverchair.com, on the allow list). ${ONE_TAB} Method C: open the PDF in the tab, then save it from the viewer. OUP's checks are "Validate User" (a crawlprevention page) and Cloudflare: either one = STOP. Ignore "Purchase" text: it is in OUP's menu on every page; only the abstract-only redirect means no access. For each paper: (1) ONE browser_batch: navigate the tab to https://doi.org/<doi>; computer wait 5; javascript_exec:
${C1('academic.oup.com', ",pdf:document.querySelector('meta[name=citation_pdf_url]')?.content||document.querySelector('a.article-pdfLink')?.href||''")}
warn = STOP; site=false = no_pdf ("DOI went to <host>"); abstractOnly = no_access ("abstract only"); empty pdf = no_pdf. ${C2(k, 7, 6)} About 20 s per paper.` },
  rsc: { phase: 'RSC', chunk: 40, campus: true, site: 'pubs.rsc.org', how: k => `RSC (pubs.rsc.org, now on Silverchair; PDFs from rscj.silverchair-cdn.com, on the allow list). ${ONE_TAB} Method C: open the PDF in the tab, then save it from the viewer. For each paper: (1) ONE browser_batch: navigate the tab to https://doi.org/<doi>; computer wait 8; javascript_exec:
${C1('rsc.org', ",buy:/Buy this article|Purchase|Get access/i.test((document.body?.innerText||'').slice(0,6000)),pdf:document.querySelector('meta[name=citation_pdf_url]')?.content||''")}
warn = STOP; buy or abstractOnly = no_access (e.g. a journal that moved to Springer); site=false and no pdf = no_pdf ("DOI went to <host>"); empty pdf = no_pdf. ${C2(k, 7, 5)} About 20 s per paper.` },
  portland: { phase: 'Portland', chunk: 40, campus: true, site: 'portlandpress.com', how: k => `Portland Press (Biochem J, Biochem Soc Trans, Clin Sci; portlandpress.com on Silverchair, on the allow list). ${ONE_TAB} Method C: open the PDF in the tab, then save it from the viewer. Only the abstract-only redirect means no access; ignore Purchase/Sign-in text. For each paper: (1) ONE browser_batch: navigate the tab to https://doi.org/<doi>; computer wait 4; javascript_exec:
${C1('portlandpress.com', ",pdf:document.querySelector('meta[name=citation_pdf_url]')?.content||''")}
warn = STOP; abstractOnly = no_access ("abstract only"); site=false = no_pdf ("DOI went to <host>"); empty pdf = no_pdf. ${C2(k, 6, 5)} About 15 s per paper.` },
  pnas: { phase: 'PNAS', chunk: 40, a: true, campus: true, site: 'www.pnas.org', how: (k, p) => `PNAS (www.pnas.org). ${FRESH} Method A only: click the PDF link as a reader would; never fetch() it (2026-10-14: a scripted fetch drew a 403 on the first paper right after the user cleared pnas.org). ${TAKE(k, p)} For each paper ONE browser_batch: navigate <tab> to https://doi.org/<doi>; computer wait 5; javascript_exec:
const id='<id>',d='<doi>';${WJS}let o={id,warn,host,t:document.title.slice(0,40),pnas:location.host.endsWith('pnas.org')};if(o.warn)throw new Error('STOP '+JSON.stringify(o));if(o.pnas){const a=document.createElement('a');a.href='/doi/pdf/'+d+'?download=true';a.download='PMID'+id+'_pnas.pdf';document.body.appendChild(a);a.click();o.clicked=true}o
; computer wait 10; tabs_create_mcp; tabs_close_mcp <tab>. Then (after the batch): clicked = take; pnas=false = no_pdf ("DOI went to <host>"). About 20 s per paper.` },
  jstage: { phase: 'J-STAGE', chunk: 40, a: true, site: 'www.jstage.jst.go.jp', how: (k, p) => `J-STAGE (www.jstage.jst.go.jp; free, no login). ${FRESH} Method A only: click the page's own PDF link (its citation_pdf_url) as a reader would; never fetch() it (J-STAGE's robots.txt bars scripts from /*_pdf, which is why fetch.py leaves these papers to a person: one click per paper in this Chrome at reading pace is a reader's action). ${TAKE(k, p)} Open the paper's url from your list (its /_article page), never doi.org (old Agric Biol Chem and BBB DOIs can bounce to OUP's check); a paper with no url = no_pdf ("no J-STAGE link"). For each paper ONE browser_batch: navigate <tab> to <url>; computer wait 4; javascript_exec:
const id='<id>';${WJS}let o={id,warn,host,t:document.title.slice(0,40),jstage:location.host.endsWith('jstage.jst.go.jp')};if(o.warn)throw new Error('STOP '+JSON.stringify(o));const u=document.querySelector('meta[name=citation_pdf_url]')?.content||'';o.haspdf=!!u;if(o.jstage&&u){const a=document.createElement('a');a.href=u;a.download='PMID'+id+'_${k}.pdf';document.body.appendChild(a);a.click();o.clicked=true}o
; computer wait 10; tabs_create_mcp; tabs_close_mcp <tab>. Then (after the batch): clicked = take; jstage=false = no_pdf ("link went to <host>"); haspdf=false = no_pdf ("no citation_pdf_url"). About 20 s per paper.` },
  microbiology: { phase: 'Microbiology', chunk: 40, site: 'www.microbiologyresearch.org', how: k => `Microbiology Society (www.microbiologyresearch.org: Microbiology, J Gen Microbiol, IJSEM; free). ${FRESH} Method B on the /deliver/fulltext/...pdf link in the page HTML (the first one with mimeType=pdf was the article every time; the extension hides query strings, so the script fetches in the page and returns only status and size). For each paper ONE browser_batch: navigate <tab> to https://doi.org/<doi>; computer wait 5; javascript_exec:
const id='<id>';${WJS}let o={id,warn,host,t:document.title.slice(0,40),ms:location.host.endsWith('microbiologyresearch.org')};const m=[...new Set((document.documentElement.innerHTML.match(/[/]deliver[/]fulltext[/][^"'<> ]+/g)||[]).map(x=>x.replace(/&amp;/g,'&')))].filter(x=>x.includes('mimeType=pdf'));o.npdf=m.length;if(!o.warn&&o.ms&&m.length){const r=await fetch(m[0],{credentials:'include'});${SAVE(k)}}${STOPJS}o
; computer wait 3; tabs_create_mcp; tabs_close_mcp <tab>. Then: saved=true = saved ("kb=<kb>"); ms=false = no_pdf ("DOI went to <host>"); npdf=0 = no_pdf; a 200 that is not a PDF = no_access; any other status = error. About 15 s per paper.` },
  asm: { phase: 'ASM', chunk: 30, a: true, site: 'journals.asm.org', how: (k, p) => `ASM journals (journals.asm.org: J Bacteriol, AEM, AAC, J Virol; free). ${FRESH} Method A only: click the PDF link (/doi/pdf/<doi>?download=true) as a reader would; never fetch() it (ASM runs on the same platform as PNAS, where a scripted fetch drew a 403 right after the user's clear; ASM's PDF fetch answered 403 after 16 papers about 12 s apart, 2026-10-11): at least 25 s per paper. ${TAKE(k, p)} For each paper ONE browser_batch: navigate <tab> to https://doi.org/<doi>; computer wait 5; javascript_exec:
const id='<id>',d='<doi>';${WJS}let o={id,warn,host,t:document.title.slice(0,40),asm:location.host==='journals.asm.org'};if(o.warn)throw new Error('STOP '+JSON.stringify(o));if(o.asm){const a=document.createElement('a');a.href='/doi/pdf/'+d+'?download=true';a.download='PMID'+id+'_${k}.pdf';document.body.appendChild(a);a.click();o.clicked=true}o
; computer wait 10; computer wait 8; tabs_create_mcp; tabs_close_mcp <tab>. Then (after the batch): clicked = take; asm=false = no_pdf ("DOI went to <host>"). At least 25 s per paper.` },
}

const RULES = `You are downloading scientific papers for CatLog, an Iowa State University (ISU) enzyme-kinetics catalog, in the user's own Google Chrome through Claude in Chrome, using ISU's legitimate library access (publishers recognise the campus network). The user asked for these downloads. Other agents work in the same browser at the same time, each in its own tabs.

HARD RULES
- Work ONLY in tabs you create (tabs_create_mcp). Never read, navigate or close any other tab. If a Chrome tool says this session's tab group no longer exists, call tabs_context_mcp with createIfEmpty: true once and go on in the tab it gives you.
- A bot check ends your run: a page title or text with "Just a moment", "Verify you are human", "Performing security verification", "Validate User", "Access Denied", "Too Many Requests", "unusual activity", "Are you a robot", "Client Challenge" or "There was a problem providing the content", a CAPTCHA, a crawlprevention page, HTTP 403 or 429 on a PDF, or a download that turns out to be a web page. The page scripts below report it (warn=true, status 403/429, or an error starting "STOP"). Then stop at once: never click, solve, reload, wait out or work around it, never try another URL or method for that site; leave that tab open for the user; write the paper's STOP line; return stopped=true, stop_kind "bot_check", stop_host = that page's host, stop_tab_url = its URL as far as the tools show it.
- One paper at a time, at your lane's pace; no parallel requests. Never sign in, never type into a page, never change Chrome settings, never open chrome:// pages, never use the download button of Chrome's PDF viewer (it opens a Save dialog).
- Keep each browser_batch under ~60 s. A batch that reports a lost connection may still be running in Chrome: run ls -t ~/Downloads | head -5 before repeating anything, so nothing is fetched twice. A page script that failed because the page navigated or closed while it ran did not run: computer wait 3, run the same script once more in that tab, then finish that paper's steps.
- Page scripts return host with spaces for dots (Claude in Chrome hides most host names otherwise): write hosts with dots in details, in stop_host and in the commands below.
- Never run catlog.py and never delete a file: filing and queue marks happen elsewhere.
- Put each paper's values in place of <id>, <doi>, <url>, <host> and <tab> in the commands and page scripts below, exactly as listed.`

const CAMPUS = `This lane needs ISU's licence: if the address does not start with 129.186. (or curl printed nothing), write no lines and return at once: stopped=true, stop_kind "off_campus", stop_reason "off campus (<ip>)".`
const prompt = (key, i, j, prog, gone, built) => {
  const L = LANE[key]
  return `${RULES}

THIS RUN: lane ${key}, entries ${i} to ${j - 1} of its list. Your progress file: ${prog}${gone.length ? `
SITES STOPPED BY A BOT CHECK EARLIER IN THIS RUN: ${gone.join(', ')}. If a paper's page lands on one of them, do nothing more on that page: write no_pdf ("<host> stopped earlier this run") and go on.` : ''}

START
1. ONE ToolSearch call: "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__computer". If the tools do not load, or a Chrome tool answers that no browser is connected: return stopped=true, stop_kind "setup", stop_reason "Chrome not connected".
2. Bash: curl -s --max-time 8 https://api.ipify.org  (return it as ip; the ISU campus network = an address starting 129.186.). ${L.campus ? CAMPUS : 'This lane is free: it runs on or off campus.'}
3. Bash: ${H} list ${key} ${i} ${j} ${prog}${built ? ` '${built}'` : ''}
   It prints your papers in order (id TAB doi TAB url; url is set only for J-STAGE), then a line "# slice N built STAMP: ...": return N as in_slice and STAMP, copied exactly, as built. A line starting "# ERROR": return stopped=true, stop_kind "setup", stop_reason = that line. A line starting "# LOW": return stopped=true, stop_kind "low_resources", stop_reason = that line. No paper lines = nothing to do: return tried 0.

EACH PAPER ends with exactly ONE progress line, written by
  ${H} log ${prog} <id> <result> '<detail>' '<host>'
with result saved | no_access | no_pdf | error | STOP, a short detail without ' characters, and the page's host${L.a ? ' (after a click, take writes it instead: see the lane)' : ''}. It prints {"result","detail","ip","campus","mem_free","disk_gb","low"}.${L.campus ? ' If it prints "campus": false, the Mac has left the campus network: stop after that paper with stop_kind "off_campus".' : ''} If "low" is not empty (memory free below 20% or disk free below 20 GB): stop after that paper with stop_kind "low_resources", stop_reason = that text.

END (finished or stopped): close every tab you created except one showing a bot check, then return the schema: tried = progress lines written; saved = papers saved; no_access, no_pdf = their ids; errors = "<id>: what happened"; stop_kind, stop_reason, stop_host, stop_tab_url empty when you did not stop.

LANE ${key}: ${L.how(key, prog, gone)}`
}

const RESULT = {
  type: 'object',
  properties: {
    in_slice: { type: 'integer', description: 'N from the list command\'s "# slice N" line; 0 if you stopped before it' },
    built: { type: 'string', description: 'STAMP from the list command\'s "# slice N built STAMP" line, copied exactly; empty if you stopped before it' },
    tried: { type: 'integer', description: 'progress lines you wrote' },
    saved: { type: 'integer' },
    no_access: { type: 'array', items: { type: 'string' } },
    no_pdf: { type: 'array', items: { type: 'string' } },
    errors: { type: 'array', items: { type: 'string' } },
    stopped: { type: 'boolean' },
    stop_kind: { type: 'string', enum: ['', 'bot_check', 'off_campus', 'low_resources', 'setup', 'other'] },
    stop_reason: { type: 'string' },
    stop_host: { type: 'string' },
    stop_tab_url: { type: 'string' },
    ip: { type: 'string' },
  },
  required: ['in_slice', 'built', 'tried', 'saved', 'no_access', 'no_pdf', 'errors', 'stopped', 'stop_kind', 'stop_reason', 'stop_host', 'stop_tab_url', 'ip'],
}

// ---- arguments: checked before any agent starts
const KEYS = Object.keys(LANE)
const STAMP = /^[0-9T:+-]{10,32}$/  // lanes.json _built, e.g. 2026-10-16T13:07:12-0500
const a = args && typeof args === 'object' && !Array.isArray(args) ? args : {}
const isObj = x => !!x && typeof x === 'object' && !Array.isArray(x)
const whole = (x, lo, hi) => Number.isInteger(x) && x >= lo && x <= hi
const problem = () => {
  if (!isObj(a.lanes) || !Object.keys(a.lanes).length) return 'args.lanes must be a non-empty object of lane counts, e.g. {"springer": 100, "acs": 60}'
  const names = Object.keys(a.lanes)
  const unknown = names.filter(k => !KEYS.includes(k))
  if (unknown.length) return `unknown lane ${unknown.join(', ')}`
  const bad = names.filter(k => !whole(a.lanes[k], 1, 2000))
  if (bad.length) return `lane counts must be whole numbers from 1 to 2000 (got ${bad.map(k => k + ': ' + JSON.stringify(a.lanes[k])).join(', ')})`
  if (typeof a.tag !== 'string' || !/^[a-z0-9]{1,24}$/.test(a.tag)) return 'args.tag must be lower-case letters and digits, e.g. "20261016a" (it keeps progress files apart)'
  if (a.start !== undefined && (!isObj(a.start) || Object.keys(a.start).some(k => !names.includes(k) || !whole(a.start[k], 0, 1000000))))
    return 'args.start must be {<lane>: <index>} with lanes from args.lanes and whole numbers >= 0'
  if (a.built !== undefined && (typeof a.built !== 'string' || !STAMP.test(a.built))) return "args.built must be the lanes_built stamp a run returned, e.g. '2026-10-16T13:07:12-0500'"
  if (a.max_parallel !== undefined && !whole(a.max_parallel, 1, 4)) return 'args.max_parallel must be 1, 2, 3 or 4 (default 3: Chrome is not to be overwhelmed)'
  return ''
}
const why = problem()
if (why) return { error: `${why}. Run 'python3 catlog.py lanes' (it writes the lists and prints the papers per lane), then pass {lanes: {<lane>: <count>, ...}, tag: '<yyyymmdd><letter>'}; lanes: ${KEYS.join(' ')}` }

const counts = a.lanes, starts = a.start || {}, tag = a.tag, MAXP = a.max_parallel || 3
// method-A lanes run one after another, so one of them starts first; otherwise the caller's order
const order = Object.keys(counts).sort((x, y) => (LANE[y].a ? 1 : 0) - (LANE[x].a ? 1 : 0))
log(`lanes: ${order.map(k => `${k} ${counts[k]}${starts[k] ? ' from ' + starts[k] : ''}`).join(', ')}; at most ${MAXP} at once` +
  (order.filter(k => LANE[k].a).length > 1 ? `; method-A lanes one at a time (${order.filter(k => LANE[k].a).join(', ')})` : ''))

const totals = {}, stops = [], gone = new Set()
let halt = '', offCampus = '', aBusy = false, built = a.built || ''
const hostOf = h => { h = String(h || '').trim().toLowerCase().split(/[\s_]+/).join('.'); return /^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(h) ? h : '' }
const bare = h => h.replace(/^www\./, '')

async function runLane(key) {
  const L = LANE[key], s0 = starts[key] || 0, end = s0 + counts[key]
  const t = totals[key] = { lane: key, from: s0, next_start: s0, chunks: 0, tried: 0, saved: 0, no_access: [], no_pdf: [], errors: [], end: '' }
  for (let i = s0; i < end; i += L.chunk) {
    const mine = L.site && [...gone].find(h => bare(h) === bare(L.site))
    const stop = halt || (L.campus && offCampus) || (mine ? `${mine} stopped by a bot check earlier in this run` : '')
    if (stop) { t.end = t.chunks ? `stopped before ${i}: ${stop}` : `not run: ${stop}`; break }
    const j = Math.min(end, i + L.chunk)
    const prog = `${DL}/lane_${key}_${tag}_${i}.jsonl`
    const r = await agent(prompt(key, i, j, prog, [...gone], built), { label: `${key}:${i}-${j}`, phase: L.phase, schema: RESULT })
    if (!r) { t.end = `the agent for ${i}-${j} died (its lines: ${prog})`; log(`${key} ${i}-${j}: agent died; lane stopped`); break }
    if (!built && STAMP.test(r.built || '')) built = r.built  // later chunks check that lanes.json was not rebuilt meanwhile
    t.chunks++; t.tried += r.tried; t.saved += r.saved
    t.no_access.push(...r.no_access); t.no_pdf.push(...r.no_pdf); t.errors.push(...r.errors)
    log(`${key} ${i}-${j}: ${r.tried} tried, ${r.saved} saved, ${r.no_access.length} no access, ${r.no_pdf.length} no PDF, ${r.errors.length} errors` +
      (r.stopped ? `; STOPPED (${r.stop_kind || 'other'}): ${r.stop_reason}${r.stop_host ? ' at ' + r.stop_host : ''}` : ''))
    if (L.campus && (r.stop_kind === 'off_campus' || r.ip && !/^129\.186\./.test(r.ip))) offCampus = offCampus || `off campus (${r.ip || 'no address'})`
    if (r.stopped) {
      t.end = `stopped: ${r.stop_reason || r.stop_kind}`
      if (r.stop_kind === 'setup' || r.stop_kind === 'low_resources') halt = halt || r.stop_reason || r.stop_kind
      else if (r.stop_kind !== 'off_campus') {
        const host = hostOf(r.stop_host) || L.site  // unknown: most likely the lane's own site
        if (host && r.stop_kind === 'bot_check') gone.add(host)
        stops.push({ lane: key, host: host || String(r.stop_host || ''), reason: r.stop_reason, tab_url: r.stop_tab_url })
      }
      break  // next_start stays i: the same tag and start skip what this chunk finished
    }
    t.next_start = j
    if (r.in_slice < j - i) { t.end = `list ended at ${i + r.in_slice}`; break }
  }
  t.end = t.end || `done to ${end}`
  return t
}

// a small pool of lane workers; a worker takes the next lane that may start now (never a second method-A lane)
const queue = order.slice()
const nextLane = () => {
  const n = queue.findIndex(k => !(LANE[k].a && aBusy))
  if (n < 0) return null  // only method-A lanes left and one is running: its worker takes them in turn
  const k = queue.splice(n, 1)[0]
  if (LANE[k].a) aBusy = true
  return k
}
const worker = async () => {
  for (let k = nextLane(); k; k = nextLane()) {
    try {
      await runLane(k)
    } catch (e) {
      totals[k] = { ...(totals[k] || { lane: k }), end: `workflow error: ${String(e).slice(0, 200)}` }
      log(`${k}: ${totals[k].end}`)
    } finally {
      if (LANE[k].a) aBusy = false
    }
  }
}
await parallel(Array.from({ length: Math.min(MAXP, order.length) }, () => worker))

const lanes = order.map(k => totals[k] || { lane: k, end: 'not run' })
return {
  lanes: lanes.map(t => ({ lane: t.lane, from: t.from, next_start: t.next_start, chunks: t.chunks, tried: t.tried, saved: t.saved,
    no_access: (t.no_access || []).length, no_pdf: (t.no_pdf || []).length, errors: (t.errors || []).length, end: t.end })),
  lanes_built: built,
  stopped_sites: stops,
  ...(offCampus ? { off_campus: `${offCampus}: the licensed lanes stopped` } : {}),
  ...(halt ? { halted: halt } : {}),
  errors: Object.fromEntries(lanes.filter(t => t.errors && t.errors.length).map(t => [t.lane, t.errors])),
  progress_files: `${DL}/lane_<lane>_${tag}_<start>.jsonl`,
  next: "python3 catlog.py file; python3 catlog.py lanes-record; give the user each stopped site's link to open once in a normal Chrome tab (a site that challenges again after a clear is done for the day). Never resume this run (resumeFromRunId): a replay re-orders the chunks and would go back to a stopped site. To go on, after the user cleared the stopped sites: python3 catlog.py lanes, then a new run with a new tag from 0 (papers tried are left out); or, without rebuilding lanes.json, a new run with the same tag, start = next_start and built = lanes_built (next_start is an index into that lanes.json only; papers a chunk finished are skipped).",
}
