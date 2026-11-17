"""Which papers read so far print a censored kcat, Km or kcat/Km (a bound or "not detected") that CatLog could not
store before the reader prompt recorded them (2026-10-24, item 7 of work/top_journal_20261021/FIXES_FOR_MAIN_CHAT_20261022.md)?

    python3 tools/censored_scan.py            counts, and the list sources/censored_reread.txt (most hits first)
    python3 tools/censored_scan.py sentences  snippets around wider wordings for the papers the list misses, for agents
                                              to judge (work/censored_sentences/chunk_NN.json)

Order: table cells first, then sentence-only papers with mutant and wild-type records, then the rest, then papers an
agent found a not-detected sentence in that the phrases miss (sources/censored_sentences.tsv, verdict yes).
A paper is listed when its text (texts/<PMID>.txt and .supp.txt) has a kinetic table with a bound or not-detected cell,
or a sentence saying some enzyme or variant had no detectable or measurable activity (the phrase list of
work/top_journal_20261021/rethink/panel/p02_censoring.py). Only papers marked done with values in catalog.jsonl, and
not those whose censored values are already in bounds.jsonl, nor those read again in full since the rule (their
readers looked for censored values). A phrase scan: an upper bound, the readers decide.
The phrases miss plainer wording ("the purified K46A mutant protein was inactive for cysteine formation", 16166087, a
completeness audit 2026-10-27); WIDE catches it but matches far more that is not a result (stability losses, inhibitors
without effect, other work), so its snippets were judged by agents, one verdict per paper (work/censored_sentences/,
the catlog-censored-sentences workflow run of 2026-10-27), and only the papers judged yes are listed.
"""
import collections, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from catlog import locked  # noqa: E402  (the method paper's test set: never scanned)
PHRASES = [r'no (?:detectable|measurable) (?:\w+ ){0,2}activity',
           r'activit\w* (?:was|were|is|are)? ?(?:not detectable|undetectable|not measurable|below (?:the )?(?:limit of )?detection)',
           r'(?:undetectable|unmeasurabl[ey]) (?:\w+ )?activit',
           r'below (?:the )?(?:detection limit|limit of detection|detection level|level of detection)',
           r'catalytically (?:inactive|dead|incompetent)',
           r'(?:completely|totally|essentially) inactive',
           r'no activity (?:could be |was |were )?(?:detected|measured|observed)',
           r'too (?:low|weak|small) to (?:be )?(?:measure|determine|detect)']
PHRASE = re.compile('|'.join(PHRASES), re.I)
KINETIC = re.compile(r'k\s*_?\s*cat|K\s*_?\s*[mM]\b|K\s*_?\s*M\b|Michaelis|turnover', re.I)
WIDE = {'be inactive': r'\b(?:was|were|is|are|remained|proved|being|be|been)\s+(?:\w+\s+){0,2}inactive\b',
        'no X activity': r'\bno (?:\w+[ -]){0,3}activity\b',
        'showed no activity': r'\b(?:show(?:ed|s)?|exhibit(?:ed|s)?|display(?:ed|s)?|had|has|possess(?:ed|es)?|retain(?:ed|s)?|gave|yielded) '
                              r'no (?:\w+[ -]){0,3}(?:activity|turnover|product)',
        'did not show activity': r'\bdid not (?:show|exhibit|display|have|possess|retain|catalyze|hydrolyze|convert|accept|turn over|use'
                                 r'|utilize) (?:any )?(?:\w+[ -]){0,3}',
        'abolished activity': r'\b(?:abolish(?:ed|es)?|eliminat(?:ed|es)|lost|loss of all|devoid of|lacked|lacks|lacking) (?:\w+[ -]){0,3}activity',
        'not active': r'\bnot (?:catalytically )?active\b',
        'not hydrolyzed': r'\b(?:was|were) not (?:hydrolyzed|hydrolysed|converted|oxidized|oxidised|reduced|phosphorylated|cleaved|accepted'
                          r'|used|utilized|a substrate)',
        'no turnover': r'\bno (?:\w+ ){0,2}turnover\b',
        'inactive toward': r'\binactive (?:toward|towards|with|against|on|for)\b'}
RULE_FROM = '2026-10-24 09:25'  # the reader prompt records censored values from here (commit 47eafb8)
CHECKED = ROOT / 'sources' / 'censored_sentences.tsv'  # pmid, verdict, what, quote, why: one agent verdict per paper
CELL = re.compile(r'^(?:n\.?\s?d\.?|n\.?\s?m\.?|<\s*[\d.]|>\s*[\d.]|≤\s*[\d.]|≥\s*[\d.]|not detect\w*|undetect\w*|no activity)$', re.I)


def tables(text):
    """(caption + header, rows) per `=== Table` block of a text."""
    for block in re.split(r'\n(?==== )', text):
        if block.startswith('=== Table') or block.startswith('=== Supplementary Table'):
            lines = block.split('\n')
            yield '\n'.join(lines[:3]), [l for l in lines[1:] if ' | ' in l]


def scan(pmid):
    text = text_of(pmid)
    cells = 0
    for head, rows in tables(text):
        if KINETIC.search(head) or any(KINETIC.search(r) for r in rows[:2]):
            cells += sum(1 for r in rows for c in r.split(' | ') if CELL.match(c.strip()))
    return cells, len(PHRASE.findall(text))


def text_of(pmid):
    text = ''
    for f in (ROOT / 'texts' / f'{pmid}.txt', ROOT / 'texts' / f'{pmid}.supp.txt'):
        if f.exists():
            text += f.read_text(encoding='utf-8', errors='replace') + '\n'
    return text


def candidates():
    """(pool, have): the done papers with values whose last full read was before the rule, and the papers with a
    censored value stored."""
    done = {r.split('\t')[0] for r in open(ROOT / 'papers.tsv', encoding='utf-8') if r.split('\t')[3:4] == ['done']} - locked()
    with_values = {json.loads(l)['pmid'] for l in open(ROOT / 'catalog.jsonl') if l.strip()}
    have = set()
    if (ROOT / 'bounds.jsonl').exists():
        have = {json.loads(l)['pmid'] for l in open(ROOT / 'bounds.jsonl') if l.strip()}
    last = {}  # each paper's last full read (a censored-only pass does not count)
    for l in open(ROOT / 'log.tsv', encoding='utf-8', errors='replace'):
        f = l.rstrip('\n').split('\t')
        if len(f) > 2 and f[2] == 'add' and 'pass=censored' not in f:
            last[f[1]] = f[0]
    return {p for p in done & with_values if last.get(p, '') < RULE_FROM}, have


def checked_pool():
    """The done papers whose last full read was before the rule, with values or not: the n.d. census (tools/nd_census.py)
    read the 180 with none too, and a yes there is worth a pass like any other."""
    done = {r.split('\t')[0] for r in open(ROOT / 'papers.tsv', encoding='utf-8') if r.split('\t')[3:4] == ['done']} - locked()
    last = {}
    for l in open(ROOT / 'log.tsv', encoding='utf-8', errors='replace'):
        f = l.rstrip('\n').split('\t')
        if len(f) > 2 and f[2] == 'add' and 'pass=censored' not in f:
            last[f[1]] = f[0]
    return {p for p in done if last.get(p, '') < RULE_FROM}


def sentences(n_chunks=16):
    """Snippets around the WIDE wordings for the candidates neither on the list nor with a verdict yet."""
    pool, have = candidates()
    listed = set((ROOT / 'sources' / 'censored_reread.txt').read_text().split())
    judged = {l.split('\t')[0] for l in open(CHECKED)} if CHECKED.exists() else set()
    rank = list(WIDE)
    out = []
    for p in sorted(pool - have - listed - judged):
        text = text_of(p)
        snips = []
        for k, rx in sorted(WIDE.items(), key=lambda kv: rank.index(kv[0])):
            for m in re.finditer(rx, text, re.I):
                s = ' '.join(text[max(0, m.start() - 220):m.end() + 160].split())
                if len(snips) < 8 and not any(s[60:200] in t['text'] for t in snips):
                    snips.append({'wording': k, 'text': s})
        if snips:
            out.append({'pmid': p, 'snippets': snips})
    d = ROOT / 'work' / 'censored_sentences'
    d.mkdir(parents=True, exist_ok=True)
    size = -(-len(out) // n_chunks) if out else 0
    for i in range(n_chunks if out else 0):
        (d / f'chunk_{i:02d}.json').write_text(json.dumps(out[i * size:(i + 1) * size], indent=0))
    print(f'{len(out):,} papers with a wider wording to judge -> {d.relative_to(ROOT)}/chunk_NN.json')


def main():
    if sys.argv[1:] == ['sentences']:
        return sentences()
    pool, have = candidates()
    mut, wt = set(), set()  # papers with both a mutant and a wild-type record: dead mutants are the point (item 7)
    if (ROOT / 'catlog_wide.jsonl').exists():
        for l in open(ROOT / 'catlog_wide.jsonl'):
            w = json.loads(l)
            (wt if w.get('wild_type') else mut).add(w['pubmed_id'])
    pairs = mut & wt
    hits, kind = {}, collections.Counter()
    for p in sorted(pool - have):
        cells, phrases = scan(p)
        if cells or phrases:
            hits[p] = (cells, phrases)
            kind['table cells' if cells else 'sentence, mutant and wild type' if p in pairs else 'sentence, other'] += 1
    # table cells first, then sentence-only papers with mutant and wild-type records, then the rest; most hits first
    order = sorted(hits, key=lambda p: (not hits[p][0], p not in pairs, -hits[p][0] - hits[p][1], p))
    if CHECKED.exists():  # papers an agent found a not-detected sentence in, after every phrase hit
        yes = {f[0] for f in (l.rstrip('\n').split('\t') for l in open(CHECKED)) if f[1:2] == ['yes']}
        extra = sorted(yes & checked_pool() - have - set(hits), key=lambda p: (p not in pairs, p))
        order += extra
        kind['sentence, checked by an agent'] = len(extra)
    out = ROOT / 'sources' / 'censored_reread.txt'
    out.write_text('\n'.join(order) + '\n')
    print(f'{len(pool):,} done papers with values read before the rule; {len(order):,} listed '
          f'({kind["table cells"]:,} with bound or not-detected table cells; by a sentence only: '
          f'{kind["sentence, mutant and wild type"]:,} with mutant and wild-type records, {kind["sentence, other"]:,} others; '
          f'{kind["sentence, checked by an agent"]:,} that an agent found one in, by a wider wording or the whole paper), in that order -> {out.relative_to(ROOT)}')


if __name__ == '__main__':
    sys.exit(main())
