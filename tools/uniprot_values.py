#!/usr/bin/env python3
"""UniProtKB reviewed (Swiss-Prot) kinetics with a PubMed reference -> sources/uniprot_values.tsv (a db_values source).

UniProt's BIOPHYSICOCHEMICAL PROPERTIES > Kinetic parameters hold KM as structured values (constant, unit, a substrate
text, evidences) and kcat, now and then kcat/KM, in the free-text note ('kcat is 315 sec(-1) with glucose 6-phosphate as
substrate.', 'kcat/KM is 1.2 x 10(5) M(-1)sec(-1) for ATP (PubMed:123).'). Vmax is not kcat and is left out.
  PubMed  each value is compared with ONE paper, the one its own reference names: a KM's evidences; a note sentence's
          run reference (UniProt writes one '(PubMed:N)' after a run of sentences from one paper, so a sentence takes
          the next reference in its text; a value in a sentence with several references, the next one after it); a
          note with no inline reference, the note's evidences. Only experimental evidence (ECO:0000269) counts. A value
          whose reference is not one PubMed ID is counted and skipped: no PubMed ID ('(Ref.5)', 'by similarity'),
          several (which paper prints it is not stated: of 1,211 KM values citing several papers, all of them in
          BRENDA/SABIO-RK/OED, those list 172 for every paper; review 2026-10-13), or a sentence after a note's last
          reference. Same number for the same paper in BRENDA/SABIO-RK/OED/SKiD/STRENDA, where they list the paper and
          parameter: Km 87%, kcat 83% (release 2026_03); misattributed rows had agreed 8-9%.
  numbers converted by units.normalize (kcat s^-1, Km mM, kcat/Km mM^-1 s^-1), never typed or guessed: a range ('5-10',
          'between'), a bound ('<', 'at least'), an exponent or unit that does not read ('x 10' with no power, 's(1)'),
          a number not governed by kcat or kcat/KM ('koff is 2 sec(-1)'), a unit that does not fit the parameter and a
          Km over a mass concentration (mg/ml: the databases list mM) are counted and skipped.
  labels  substrate: the KM's substrate text, a note's 'with X as substrate', 'for X', 'X reduction' (a respectively-list
          paired in order); trailing qualifiers ('(at pH 7.5 and 25 degrees Celsius)', '(isoform 2)', '(in the presence
          of 1 mM ATP)') go to the comment, and an abbreviation that spells the name ('glucose 1-phosphate (G1P)') is
          dropped. variant: empty (the entry's own protein) unless the text names a mutant, isoform or allele.
Writes sources/uniprot_values.tsv with the columns of the other *_values.tsv files: pmid, ec, metric, value, substrate,
organism, comment. comment: 'UniProt <accession>; <variant>; pH <x>; <t> C; <other qualifiers>; ECO:0000269', the variant
the second ';' part as in SABIO-RK's comments (tools/dbcompare.py reads it the same way); empty parts left out except
the variant's. Raw download: sources/ref/uniprot_kinetics.json.gz ({release, release_date, query, fields, downloaded,
entries}), kept between runs as tools/ref_sequences.py keeps its files; --refresh downloads it again (UniProt releases
every 8 weeks; ~10,000 entries, ~2 MB, a minute or two). Prints what it kept and why it skipped the rest.
Usage: python3 tools/uniprot_values.py [--refresh]
"""
import gzip, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from units import normalize  # noqa: E402

RAW = ROOT / 'sources' / 'ref' / 'uniprot_kinetics.json.gz'
OUT = ROOT / 'sources' / 'uniprot_values.tsv'
API = 'https://rest.uniprot.org/uniprotkb/search'
QUERY = '(reviewed:true) AND (cc_bpcp_kinetics:*)'
FIELDS = 'accession,organism_name,ec,kinetics'
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)
UA = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}


# ---------------------------------------------------------------- download
def _get(url):
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return json.loads(r.read()), r.headers
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(30 if e.code == 429 else 10 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f'UniProt did not answer: {url}')


def download():
    """Every reviewed entry with kinetic parameters, 500 per page (the API's cursor in the Link header). Written to a
    .part file and renamed only when the count equals UniProt's X-Total-Results, so a cut-off run keeps no file."""
    url = API + '?' + urllib.parse.urlencode({'query': QUERY, 'fields': FIELDS, 'format': 'json', 'size': 500})
    entries, head = [], None
    while url:
        data, h = _get(url)
        head = head or h
        entries += data.get('results') or []
        nxt = re.search(r'<([^>]+)>\s*;\s*rel="next"', h.get('Link') or '')
        url = nxt.group(1) if nxt else None
        print(f'  {len(entries):,} of {head.get("X-Total-Results")} entries', flush=True)
        time.sleep(0.3)
    total = int(head.get('X-Total-Results') or -1)
    if len(entries) != total:
        raise RuntimeError(f'got {len(entries)} entries, UniProt reports {total}: nothing written')
    raw = {'release': head.get('X-UniProt-Release'), 'release_date': head.get('X-UniProt-Release-Date'), 'query': QUERY,
           'fields': FIELDS, 'downloaded': date.today().isoformat(), 'entries': entries}
    RAW.parent.mkdir(parents=True, exist_ok=True)
    part = RAW.with_name(RAW.name + '.part')
    with gzip.open(part, 'wt', encoding='utf-8') as f:
        json.dump(raw, f, ensure_ascii=False)
    part.rename(RAW)
    return raw


# ---------------------------------------------------------------- text helpers
QUAL_WORD = re.compile(
    r'\b(?:at|in|with|without|when|for|using|under|tested|from|by|via|isoform|isozyme|isoenzyme|allele|mutant|variant|wild|'
    r'presence|absence|pH|pHs?\d|degrees?|Celsius|temperature|recombinant|native|expressed|assay\w*|reaction|activity|'
    r'cofactor|co-?substrate|substrate|acceptor|donor|conditions?|buffer|enzymes?|form|subunit|domain|complex|chimera|'
    r'truncat\w*|uni-?port|sym-?port|anti-?port|direction|forward|reverse|transport|uptake|binding|membrane|potential|'
    r'oocytes?|cells?|strain|mM|uM|muM|nM|\w+(?:tion|ysis|esis)|\w+ase)\b', re.I)
DEGREES = re.compile(r'(\d+(?:\.\d+)?)\s*(?:degrees?\s*(?:Celsius|C\b)|°\s*C\b)', re.I)
PH = re.compile(r'\bpH\s*(\d+(?:\.\d+)?)', re.I)


def _trailing_group(s):
    """(text before, group content) of a balanced parenthesis group that ends s, else None."""
    s = s.rstrip()
    if not s.endswith(')'):
        return None
    depth = 0
    for i in range(len(s) - 1, -1, -1):
        depth += {')': 1, '(': -1}.get(s[i], 0)
        if depth == 0:
            return s[:i], s[i + 1:-1]
    return None


def _spells(abbr, name):
    """The abbreviation's letters and digits appear in order in the name ('G1P' in 'glucose 1-phosphate', 'DMAPP' in
    'dimethylallyl diphosphate'; never 'Glu-3' in 'methotrexate')."""
    a, n = re.sub(r'[^a-z0-9]', '', abbr.lower()), name.lower()
    if not a or len(a) > 12 or ' ' in abbr.strip() or len(a) * 2 > len(re.sub(r'[^a-z0-9]', '', n)):
        return False
    it = iter(n)
    return all(ch in it for ch in a)


def split_substrate(text):
    """(name, qualifiers) of a substrate text: trailing parenthesis groups that qualify it ('(at pH 6.5)', '(isoform 2)',
    'all-trans-retinol(in allele ADH1B*2)') are qualifiers, and one that abbreviates the name ('(G1P)') is dropped; any
    other group is part of the name ('NAD(+)', 'methotrexate (Glu-3)', '17-O-(beta-D-glucuronate)')."""
    name, quals = re.sub(r'\s+', ' ', str(text or '')).strip(), []
    while True:
        g = _trailing_group(name)
        if not g or not g[0].strip():
            break
        before, inner = g
        glued = not before.endswith(' ')
        if QUAL_WORD.search(inner) and (not glued or re.match(r'(?:in|at|with|when|for|using|isoform|allele)\b', inner, re.I)):
            quals.insert(0, inner.strip())
        elif not glued and _spells(inner, before):
            pass  # 'glucose 1-phosphate (G1P)': the abbreviation of the name
        else:
            break
        name = before.rstrip()
    # a clause written without parentheses: 'O(2) with NADPH as the electron donor', 'phenazine methosulfate as electron
    # acceptor'
    m = re.match(r'(.+?)\s+((?:with|in the presence of|in presence of|in the absence of|when|using|as (?:the )?(?:\w+ )?'
                 r'(?:cofactor|activator|acceptor|donor|reductant|oxidant))\b.*)$', name)
    if m and m.group(1).count('(') == m.group(1).count(')'):
        name, quals = m.group(1), [m.group(2)] + quals
    return name, quals


AA3 = {'Ala': 'A', 'Arg': 'R', 'Asn': 'N', 'Asp': 'D', 'Cys': 'C', 'Gln': 'Q', 'Glu': 'E', 'Gly': 'G', 'His': 'H', 'Ile': 'I',
       'Leu': 'L', 'Lys': 'K', 'Met': 'M', 'Phe': 'F', 'Pro': 'P', 'Ser': 'S', 'Thr': 'T', 'Trp': 'W', 'Tyr': 'Y', 'Val': 'V'}
POINT = re.compile(r'(?<![A-Za-z0-9])([A-Z][a-z]{0,2})(\d+)([A-Z][a-z]{0,2})(?![A-Za-z0-9])')


def variant_of(text):
    """The variant a qualifier text names, in words dbcompare.db_variant reads: 'mutant K45A/D50N', 'wild type',
    'isoform 2', an allele's name ('ADH1B*2'), 'chimera', 'truncated', 'mutant' for a mutant named without point
    mutations; '' for none (the entry's own protein)."""
    t = str(text or '')
    if re.search(r'mutant|variant|mutation|substitut', t, re.I):
        muts = [f'{AA3.get(a, a)}{n}{AA3.get(b, b)}' for a, n, b in POINT.findall(t)
                if AA3.get(a, a) in 'ACDEFGHIKLMNPQRSTVWY' and AA3.get(b, b) in 'ACDEFGHIKLMNPQRSTVWY' and len(AA3.get(a, a)) == 1
                and len(AA3.get(b, b)) == 1]
        if muts:
            return 'mutant ' + '/'.join(dict.fromkeys(muts))
    if re.search(r'\bwild[- ]?type\b', t, re.I):
        return 'wild type'
    m = re.search(r'\b(?:isoform|isozyme|isoenzyme)\s+([A-Za-z0-9][\w*.+-]*)', t, re.I)
    if m:
        return 'isoform ' + m.group(1).rstrip('.,')
    m = re.search(r'\ballele\s+([A-Za-z0-9][\w*.+-]*)', t, re.I)
    if m:
        return m.group(1).rstrip('.,')
    if re.search(r'chimer', t, re.I):
        return 'chimera'
    if re.search(r'truncat|\bdelet', t, re.I):
        return 'truncated'
    if re.search(r'\b(?:mutant|variant)s?\b', t, re.I) and not re.search(r'tag|fusion', t, re.I):
        return 'mutant'
    return ''


def conditions(texts):
    """('pH x', 't C') from qualifier texts (first stated), and the texts with those phrases taken out."""
    ph = t = ''
    rest = []
    for q in texts:
        m = PH.search(q)
        if m and not ph:
            ph = f'pH {m.group(1)}'
        m = DEGREES.search(q)
        if m and not t:
            t = f'{m.group(1)} C'
        q = DEGREES.sub('', PH.sub('', q))
        q = re.sub(r'\b(?:at|and|of)\s*(?=$|[,;)]|\band\b)', '', q)
        q = re.sub(r'\s*,\s*(?=,|$)|^\s*,\s*', '', re.sub(r'\s+', ' ', q)).strip(' ,;')
        q = re.sub(r'^(?:and|at|of)\b\s*|\s*\b(?:and|at|of)$', '', q).strip(' ,;')
        if q and not re.fullmatch(r'(?:and|at|of|\W)*', q):
            rest.append(q)
    return ph, t, rest


# ---------------------------------------------------------------- the kinetics note
NUM = r'(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)'
EXP = r'(?:\s*[xX×]\s*10\s*\(\s*[-−]?\s*\d+\s*\))'
ERR = rf'(?:\s*(?:\+/-|\+-|±)\s*\d+(?:\.\d+)?{EXP}?)'
ONE = rf'{NUM}{EXP}?{ERR}?'  # '12', '1.2 x 10(-3)', '2.4 x 10(-2) +/- 0.3 x 10(-2)'
UNIT_TOK = r'(?:sec|second|s|min|minute|hr|hour|h|M|mM|uM|muM|nM|pM)\s*\(\s*[-−]\s*1\s*\)'
QUANTITY = re.compile(rf'(?<![\w./-])(?P<nums>{ONE}(?:\s*(?:,\s*and|,|and|or)\s*{ONE})*)\s*(?P<unit>{UNIT_TOK}(?:\s*{UNIT_TOK})?)')
ANY_UNIT = re.compile(r'\(\s*[-−]\s*1\s*\)')  # every '(-1)' of a kcat sentence is read or counted
TOKEN = re.compile(r'(sec|second|s|min|minute|hr|hour|h|M|mM|uM|muM|nM|pM)\s*\(')
TIME_TOK = {'sec': 's', 'second': 's', 's': 's', 'min': 'min', 'minute': 'min', 'hr': 'h', 'hour': 'h', 'h': 'h'}
CONC_TOK = {'M': 'M', 'mM': 'mM', 'uM': 'uM', 'muM': 'uM', 'nM': 'nM', 'pM': 'pM'}
# the parameter a number belongs to: the last of these named before it in its sentence
KCAT_WORD = r'\bk\s*\(?cat\)?s?'
RATIO_WORD = r'\bk\s*\(?cat\)?\s*/\s*K\s*\(?[mM]\)?'
KEYWORD = re.compile(rf'(?P<ratio>{RATIO_WORD}|catalytic efficienc\w*|specificity constant)|'
                     rf'(?P<kcat>{KCAT_WORD}(?:\s*\(?app\)?)?(?!\s*/)\b|turnover numbers?)|'
                     r'(?P<other>\bV\s*\(?max\)?|(?-i:\bk)\s*\(?(?:off|on|obs|chem|inact|pol|app|[0-9]|-[0-9]|f|r|ex|cleav\w*)\)?(?!\w)|'
                     r'\brates?\b|rate constant|turnover (?:rate|frequency)|half-li[fv]es?|\bK\s*\(?[mMdDiI]\)?\b|\bKM\b)', re.I)
# 'kcat and kcat/KM are 4500 sec(-1) and 760 sec(-1) mM(-1), respectively': the one form where a number's unit, not the
# keyword nearest it, tells kcat from kcat/KM
JOINT = re.compile(rf'{KCAT_WORD}\s*(?:,|and)\s*{RATIO_WORD}|{RATIO_WORD}\s*(?:,|and)\s*{KCAT_WORD}\b', re.I)
APPROX = re.compile(r'(?:about|approximately|approx\.?|around|nearly|roughly|close to|~|≈)\s*$', re.I)
BOUND = re.compile(r'(?:<|>|≤|≥|≲|≳|less than|more than|greater than|lower than|higher than|smaller than|larger than|'
                   r'inferior to|superior to|at least|at most|up to|as low as|as high as|below|above|over|under|exceed\w*|'
                   r'between|from|range\w*|ranging|maxim\w*|minim\w*)\s*(?:of\s*)?$', re.I)
RANGE_BEFORE = re.compile(rf'{NUM}\s*(?:{UNIT_TOK}\s*)*(?:-|–|to)\s*$')
RANGE_AFTER = re.compile(r'^\s*(?:-|–|to)\s*\d')
# a reference that closes a run of sentences: '(PubMed:123)', '(PubMed:1, PubMed:2)', '(Ref.5)' (a citation with no PMID)
REF = re.compile(r'\(\s*((?:(?:PubMed|PMID):\s*\d+|Ref\.\s*\d+)(?:\s*,\s*(?:(?:PubMed|PMID):\s*\d+|Ref\.\s*\d+))*)\s*\)')
AS_SUBSTRATE = re.compile(r'\b(?:with|for|using|toward|towards|on)\s+((?:(?!\b(?:with|for|using)\b).)+?)\s+as\s+(?:the\s+)?'
                          r'(?:\w+\s+)?(?:co-?)?substrates?\b', re.I)
LEAD = re.compile(r'^\W*(?:respectively\W*)?(?:for|with|toward|towards|on|using)\s+(?:the\s+)?(.+)', re.I)
COFACTOR = re.compile(r'\bas\s+(?:the\s+)?(?:\w+\s+)?(?:cofactors?|activators?|inhibitors?|effectors?|reductants?|'
                      r'electron (?:donors?|acceptors?))\b', re.I)  # 'using Co(2+) as cofactor': not the substrate
# where a substrate phrase ends: a parenthesis group that is not the start of a name ('(S)-allantoin', '(2E)-but-2-enal'
# are names), ';', ', respectively', the sentence's end, or a clause word
CLAUSE_END = re.compile(r'\s+\((?![^()]*\)[-\w\[])|;|,?\s+respectively\b|\.\s*$|\s+(?:at|in|when|under|whereas|while|but|'
                        r'compared|which|that|is|are|was|were|appears?|seems?|upon|and\s+k\w*|and\s+the|and\s+\d)\b', re.I)
LIST_SEP = re.compile(r',\s+(?:and\s+|or\s+)?|\s+(?:and|or)\s+')  # 'A, B and C' (never the comma of '3,4-dihydroxy')
REACTION_END = re.compile(r'\s+(?:[\w-]*(?:tion|ysis)|cleavage|transfer|uptake|transport|import|export|release)$', re.I)
REACTION_START = re.compile(r'^(?:the\s+)?(?:[\w-]+\s+)?(?:[\w-]+(?:tion|ysis|esis|age)|reduction|transfer|uptake|transport|'
                            r'release)\s+of\s+(?:the\s+)?', re.I)
NOT_A_SUBSTRATE = re.compile(r'\b(?:activit(?:y|ies)|reactions?|enzymes?|proteins?|wild[- ]?type|mutants?|variants?|'
                             r'isoforms?|isozymes?|alleles?|direction|forward|reverse|pH|degrees|presence|absence|form|mature|'
                             r'turnover|numbers?|values?|rates?|cofactors?|activators?|inhibitors?)\b|^(?:that|those|these|it)\b',
                             re.I)
# a qualifier phrase of a value's clause, to its next ', ', ';' or parenthesis group
QUAL_PHRASE = re.compile(r'\b(?:at pH|at \d|in the (?:presence|absence)|in (?:presence|absence)|without|when|under|upon|'
                         r'in complex with|as (?:the )?(?:\w+ )?(?:cofactor|activator|reductant|electron donor|electron acceptor)|'
                         r'(?:for|with|using|of) (?:the )?(?:[\w-]+ )?(?:mutant|variant|isoform|isozyme|wild|allele))'
                         r'.*?(?=,\s|;|\s\(|$)', re.I)
OWN_PHRASE = re.compile(r'\b(?:for|with|without|using|toward|towards|on|in the (?:presence|absence)|in (?:presence|absence))\b',
                        re.I)  # a value's clause that names anything of its own: it never takes another value's substrate
CLAUSE_BREAK = re.compile(r',\s+(?:and|but|whereas|while)\s+|;\s*|,\s+(?=k\s*\(?cat)', re.I)


def sentences(text):
    """A note split into sentences (and ';' clauses), never after 'e.g.', 'i.e.', 'approx.', 'sp.', 'vs.' or a decimal."""
    out, cur = [], ''
    for part in re.split(r'(?<=[.;])(\s+)', text):
        cur += part
        if re.search(r'[.;]$', cur) and not re.search(r'(?:\be\.g|\bi\.e|\bapprox|\bsp|\bvs|\bca|\bcf|\bal|\bFig|\bref)\.$', cur, re.I):
            out.append(cur.strip())
            cur = ''
    if cur.strip():
        out.append(cur.strip())
    return out


def groups(text):
    """The top-level parenthesis groups of a text that are not the start of a name ('(at pH 7.5)', never '(S)-')."""
    out, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == '(':
            if depth == 0:
                start = i
            depth += 1
        elif ch == ')' and depth:
            depth -= 1
            if depth == 0 and not re.match(r'[-\w\[]', text[i + 1:i + 2]) and (start == 0 or not re.match(r'[\w)\]]', text[start - 1])):
                out.append(text[start + 1:i])
    return out


def balanced(t):
    """A phrase cut inside parentheses closed again ('in the presence of NAD(+' -> 'in the presence of NAD(+)')."""
    t = t.strip(' ,;.')
    while t.count(')') > t.count('(') and t.endswith(')'):
        t = t[:-1]
    return t + ')' * max(0, t.count('(') - t.count(')'))


def substrate_items(clause):
    """Substrate names a clause gives: 'with X as substrate' first, else a leading 'for X' / 'with X'; a list 'A, B and
    C' split; each cleaned ('the hydrolysis of cellobiose' -> 'cellobiose', 'D-gluconate oxidation' -> 'D-gluconate',
    trailing qualifiers and an abbreviation dropped as in split_substrate); an activity, a reaction, a cofactor or an
    enzyme form ('for ATPase activity', 'for the reverse reaction', 'using Co(2+) as cofactor') names no substrate ('')."""
    # a clause cut before the next number: 'for A and', 'for cGMP, between', 'on a ssDNA 21-mer and about'
    clause = re.sub(r'(?:(?:,\s*|\s+)(?:and|or|between|from|about|approximately|around|nearly|roughly)\b|\s*[~<>≤≥])+\s*$', '',
                    clause.strip())
    m = AS_SUBSTRATE.search(clause)
    if m:
        head = m.group(1)
    else:
        m = LEAD.match(clause)
        if not m:
            return []
        c = COFACTOR.search(m.group(1))
        if c and c.start() < 60 and ',' not in m.group(1)[:c.start()]:
            return ['']
        head = CLAUSE_END.split(m.group(1), maxsplit=1)[0]
    items = []
    for r in LIST_SEP.split(head.strip()):
        r = r.strip().strip(' .,;')
        r = split_substrate(REACTION_END.sub('', REACTION_START.sub('', r)).strip(' .,;'))[0]
        r = re.sub(r'^(?:the|an?)\s+', '', r, flags=re.I)
        reaction = re.fullmatch(r'[\w-]+(?:tion|ysis)', r, re.I)  # 'for acetylation': a reaction, not a substrate
        items.append('' if not r or reaction or NOT_A_SUBSTRATE.search(r) or len(r) > 120 else r)
    return items


def number(text):
    """(number as units.normalize reads it, None) of a note number with any printed error dropped ('1.2 x 10(-3)' ->
    '1.2 x 10^-3', '21,213' -> '21213', '2.4 x 10(-2) +/- 0.3 x 10(-2)' -> '2.4 x 10^-2'), or (None, why) when the
    power of ten is printed with the error only ('12 +/- 2 x 10(3)': which number it multiplies is not stated)."""
    m = re.fullmatch(rf'\s*({NUM})({EXP})?(?:\s*(?:\+/-|\+-|±)\s*\d+(?:\.\d+)?({EXP})?)?\s*', text)
    if not m:
        return None, 'note: number that does not read'
    if m.group(3) and not m.group(2):
        return None, 'note: power of ten printed with the error only'
    t = m.group(1) + (m.group(2) or '')
    t = re.sub(r'10\s*\(\s*([-−]?)\s*(\d+)\s*\)', lambda x: f'10^{"-" if x.group(1) else ""}{x.group(2)}', t)
    return re.sub(r'(?<=\d),(?=\d{3}\b)', '', t.replace('×', 'x').replace('X', 'x')), None


def unit_of(unit):
    """(metric, unit text for units.normalize) of a note unit: one time token 'kcat'; one concentration and one time
    token 'kcat/Km'; anything else None."""
    toks = TOKEN.findall(unit)
    times = [TIME_TOK[t] for t in toks if t in TIME_TOK]
    concs = [CONC_TOK[t] for t in toks if t in CONC_TOK]
    if len(toks) == 1 and len(times) == 1:
        return 'kcat', f'{times[0]}^-1'
    if len(toks) == 2 and len(times) == 1 and len(concs) == 1:
        return 'kcat/Km', f'{concs[0]}^-1 {times[0]}^-1'
    return None, None


def ref_ids(group):
    """('PubMed:123', 'Ref.5', ...) of a reference group's text."""
    return tuple(re.sub(r'\s+', '', x).replace('PMID', 'PubMed') for x in re.findall(r'(?:PubMed|PMID):\s*\d+|Ref\.\s*\d+', group))


def respectively(s, quants, every):
    """[pH, temperature] per number of a sentence that lists conditions 'respectively' ('8.72 sec(-1) and 5.7 sec(-1) for
    glutathione at pH 6.0 and pH 7.0, respectively'): its own when the counts agree, None (state none: never another
    number's) when they do not, '' when the sentence lists none of that kind; [] for a sentence without such a list."""
    if not re.search(r'\brespectively\b', s, re.I):
        return []
    tail = s[quants[-1]['end']:]
    m = re.search(r'\bpH\s*(\d+(?:\.\d+)?)((?:\s*(?:,|,?\s*and|or)\s*(?:pH\s*)?\d+(?:\.\d+)?)+)', tail)
    phs = [m.group(1)] + re.findall(r'\d+(?:\.\d+)?', m.group(2)) if m else []
    m = re.search(r'(\d+(?:\.\d+)?)((?:\s*(?:,|,?\s*and|or)\s*\d+(?:\.\d+)?)+)\s*degrees', tail)
    ts = [m.group(1)] + re.findall(r'\d+(?:\.\d+)?', m.group(2)) if m else []
    if not phs and not ts:
        return []
    own = lambda xs, i, fmt: (fmt.format(xs[i]) if len(xs) == len(every) else None) if xs else ''
    return [[own(phs, i, 'pH {}'), own(ts, i, '{} degrees Celsius')] for i in range(len(every))]


def note_values(text, skip):
    """[(metric, printed number, unit, substrate, qualifiers, reference, approximate)] of a note text. reference: the
    reference ids that close the value's run of sentences (UniProt writes one '(PubMed:N)' after a run of sentences
    from one paper: a sentence takes the next reference in the text, a value in a sentence with several references the
    next one after it); 'after_last' for a value after the text's last reference (its own is not stated); None when the
    text has no inline reference (the text's evidences then hold)."""
    out, pending = [], []  # pending: indexes in out of values waiting for the reference that closes their run
    for sent in sentences(text):
        refs = [(m.start(), ref_ids(m.group(1))) for m in REF.finditer(sent)]
        s = REF.sub(lambda m: ' ' * len(m.group(0)), sent)  # positions kept, so values and references line up
        if refs:
            for i in pending:  # the run of earlier sentences closes here
                out[i][5] = refs[0][1]
            pending = []
        mine = []
        if re.search(rf'{KCAT_WORD}|turnover|catalytic efficienc|specificity constant', s, re.I):
            mine = sentence_values(s, skip)
        for v, end in mine:
            later = [ids for pos, ids in refs if pos >= end]
            v[5] = later[0] if later else None
            out.append(v)
            if not later:
                pending.append(len(out) - 1)
    for i in pending:  # after the text's last reference, in a text that has references: its own is not stated
        out[i][5] = 'after_last' if REF.search(text) else None
    return [tuple(v) for v in out]


def sentence_values(s, skip):
    """[([metric, number, unit, substrate, qualifiers, None, approximate], end position)] of one sentence."""
    has = {k.lastgroup for k in KEYWORD.finditer(s)}
    quants, starts, units = [], [], 0
    for q in QUANTITY.finditer(s):
        start, nums = q.start(), re.findall(ONE, q.group('nums'))
        units += len(ANY_UNIT.findall(q.group('unit')))
        if len(nums) > 1 and re.search(r'\bpH\s*$', s[:start]):  # 'at pH 6.8 and 2.1 sec(-1)': 6.8 is a pH
            start += q.group('nums').find(nums[1], len(nums[0]))
            nums = nums[1:]
        starts.append(start)
        metric, unit = unit_of(q.group('unit'))
        kws = list(KEYWORD.finditer(s[:start]))
        last = kws[-1].lastgroup if kws else None
        if metric is None:
            skip['note: unit not kcat or kcat/Km'] += len(nums)
            continue
        if not (last == 'kcat' and metric == 'kcat' or last == 'ratio' and metric == 'kcat/Km'
                or last in ('kcat', 'ratio') and {'kcat', 'ratio'} <= has and JOINT.search(s) and re.search(r'respectively', s)):
            skip['note: number not governed by kcat or kcat/KM'] += len(nums)
            continue
        before, after = s[:start], s[q.end():]
        if re.search(r'(?:\+/-|\+-|±)\s*$', before):  # '+/- 0.3 x 10(-2) sec(-1)': an error term, not a value
            skip['note: error term'] += len(nums)
            continue
        if BOUND.search(before) or RANGE_BEFORE.search(before) or RANGE_AFTER.match(after) or (
                len(nums) > 1 and re.search(r'between|from|range', before[-40:], re.I)):
            skip['note: range or bound'] += len(nums)
            continue
        if re.search(r'[xX×]\s*10(?!\s*\()', q.group('nums')) or re.match(r'\s*[xX×]\s*10', after) or \
                re.search(r'(?:[xX×*]|\d|10\s*\()\s*$', before):  # '3 x 10 sec(-1)': the power of ten lost
            skip['note: power of ten that does not read'] += len(nums)
            continue
        quants.append({'metric': metric, 'unit': unit, 'nums': nums, 'start': start, 'end': q.end(),
                       'approx': bool(APPROX.search(before))})
    unread = len(ANY_UNIT.findall(s)) - units  # 'msec(-1)', '1.43-1.48 sec(-1)', '3.7 kcat is sec(-1)'
    if unread > 0:
        skip['note: number that does not read'] += unread
    if not quants:
        return []
    kw_starts = [k.start() for k in KEYWORD.finditer(s)]
    for i, q in enumerate(quants):
        # its clause: to the next number with a unit (kept or not) or the next kinetic keyword; its lead: from the
        # previous value's end (the sentence's start) to it, after the last keyword ('kcat for chlortetracycline is')
        q['tail'] = s[q['end']:min([x for x in starts + kw_starts if x >= q['end']] or [len(s)])]
        q['clause'] = CLAUSE_BREAK.split(q['tail'], maxsplit=1)[0]
        lead = s[quants[i - 1]['end'] if i else 0:q['start']]
        lead = q['lead_full'] = CLAUSE_BREAK.split(lead)[-1]
        k = [m.end() for m in KEYWORD.finditer(lead)]
        q['lead'] = re.sub(r'^[\s,;]*(?:and\s+)?', '', lead[k[-1]:] if k else lead)
        q['lead_sub'] = [x for x in substrate_items(q['lead']) if x]
    every = [(q, n) for q in quants for n in q['nums']]
    last = quants[-1]
    shared = substrate_items(last['tail'])  # the last value's names: a list for several numbers, in order
    alone = all(not OWN_PHRASE.search(q['tail']) for q in quants[:-1])  # earlier values name nothing of their own
    names = {x for q in quants for x in substrate_items(q['tail']) + q['lead_sub'] if x}
    if len(every) > 1 and len(shared) == len(every) and len({q['metric'] for q in quants}) == 1 and alone:
        pairs = list(zip(every, shared))
    else:
        pairs = []
        for q, n in every:
            own = substrate_items(q['tail']) if len(q['nums']) == 1 else []
            if any(own):  # its own clause names it ('for A', not 'for A and B')
                sub = own[0] if len(own) == 1 else ''
            elif own and not variant_of(q['clause']):  # its own clause names an activity, a reaction, a cofactor
                sub = ''
            elif len(q['lead_sub']) == 1:  # 'kcat for chlortetracycline is 3.5 min(-1)'
                sub = q['lead_sub'][0]
            elif not OWN_PHRASE.search(q['clause']) and len(names) == 1:  # the sentence's only substrate
                sub = next(iter(names))
            else:
                sub = ''
            pairs.append(((q, n), sub))
    # the sentence's last parenthesis group states conditions for every number that states none of its own
    end_group = [g for g in groups(last['tail'])[-1:] if re.search(r'pH|degrees', g) and s.rstrip(' .').endswith(')')]
    resp = respectively(s, quants, every)
    out = []
    for i, ((q, n), sub) in enumerate(pairs):
        num, why = number(n)
        if why:
            skip[why] += 1
            continue
        quals = [balanced(g) for g in groups(q['clause']) if QUAL_WORD.search(g) and not REF.fullmatch(f'({g})')]
        bare = re.sub(r'(?:^|\s)\([^()]*(?:\([^()]*\)[^()]*)*\)', ' ', q['clause'])  # its groups are read above
        quals += [balanced(w.group(0)) for w in QUAL_PHRASE.finditer(bare)]
        if end_group and not re.search(r'pH|degrees', ' '.join(quals)):
            quals += end_group
        if not variant_of(' '.join(quals)):  # the variant its own clause, its lead or the sentence's head names
            for t in (q['clause'], q['lead_full'], s[:quants[0]['start']]):
                if variant_of(t):
                    t = re.sub(r'^.*?\b(?=(?:for|with|of|in|using)\s+(?:the\s+)?(?:[\w-]+\s+)?(?:mutant|variant|isoform|'
                               r'isozyme|wild|allele|chimer|truncat))', '', t)
                    quals.append(balanced(KEYWORD.split(t, maxsplit=1)[0]))  # 'for mutant K45A', not '... kcat is'
                    break
        if resp:  # 'at pH 6.0 and pH 7.0, respectively': this number's own condition first, or none of that kind
            ph, t = resp[i]
            if ph != '':  # the list itself goes: 'at pH 6.0 and pH 7.0'
                quals = [re.sub(r'(?:\bat\s+)?\bpH\s*\d+(?:\.\d+)?(?:\s*(?:,|,?\s*and|or)\s*(?:pH\s*)?\d+(?:\.\d+)?)*', '', x)
                         for x in quals]
            if t != '':  # 'at 30 and 45 degrees Celsius'
                quals = [re.sub(r'(?:\bat\s+)?\d+(?:\.\d+)?(?:\s*(?:,|,?\s*and|or)\s*\d+(?:\.\d+)?)*\s*(?:degrees?\s*'
                                r'(?:Celsius|C\b)|°\s*C\b)', '', x) for x in quals]
            quals = [x for x in quals if re.sub(r'\b(?:at|and|or|of)\b|\W', '', x)]
            quals = [x for x in [ph or '', t or ''] + quals if x]
        out.append(([q['metric'], num, q['unit'], sub, quals, None, q['approx']], q['end']))
    return out


# ---------------------------------------------------------------- rows
def ecs(entry):
    """The entry's EC numbers (recommended, alternative, included and contained names)."""
    found = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == 'ecNumbers':
                    found.extend(e.get('value') for e in v if e.get('value'))
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(entry.get('proteinDescription') or {})
    return list(dict.fromkeys(found))


EXPERIMENTAL = 'ECO:0000269'  # experimental evidence used in manual assertion; 0000303 (author statement: often a value
# the paper reprints), 0000305 (curator inference) and 0000250 (by similarity) are not a measurement of the paper


def references(evidences):
    """('PubMed:123', 'Ref.5', ...) of an evidence list's experimental evidences (EXPERIMENTAL), and whether it had
    evidences of other kinds only."""
    ev = evidences or []
    mine = [e for e in ev if e.get('evidenceCode') == EXPERIMENTAL]
    ids = tuple(dict.fromkeys(f"PubMed:{e.get('id')}" if e.get('source') == 'PubMed' else f"{e.get('source')}:{e.get('id')}"
                              for e in mine))
    return ids, bool(ev) and not mine


def paper(ids, what, skip):
    """The one PubMed ID of a value's references, else None with the reason counted: a value with no PubMed reference,
    or with several references (which paper prints it is not stated: of 1,211 KM values that cite several papers, all
    in BRENDA/SABIO-RK/OED, those databases list 172 for every paper, review 2026-10-13), is not compared per paper."""
    pm = [x.split(':', 1)[1] for x in ids if x.startswith('PubMed:') and x.split(':', 1)[1].isdigit()]
    if len(ids) > 1:
        skip[f'{what}: several references, its own not stated'] += 1
    elif not pm:
        skip[f'{what}: no PubMed ID in its reference'] += 1
    else:
        return pm[0]
    return None


def clean(x):
    return re.sub(r'\s+', ' ', str(x or '').replace('\t', ' ')).strip()


def row(pmid, ec, metric, value, substrate, organism, acc, quals, approx):
    ph, t, rest = conditions(quals)
    var = variant_of(' '.join(quals))
    parts = [f'UniProt {acc}', var] + [p for p in (ph, t, *rest, 'approximately' if approx else '', EXPERIMENTAL) if p]
    return '\t'.join(clean(f) for f in (pmid, ec, metric, f'{value:.6g}', substrate, organism, '; '.join(parts))) + '\n'


def rows(entry, skip, kept):
    acc = entry.get('primaryAccession', '')
    org = (entry.get('organism') or {}).get('scientificName', '')
    ec = '; '.join(ecs(entry))
    for c in entry.get('comments') or []:
        if c.get('commentType') != 'BIOPHYSICOCHEMICAL PROPERTIES':
            continue
        kp = c.get('kineticParameters') or {}
        for k in kp.get('michaelisConstants') or []:
            ids, other_only = references(k.get('evidences'))
            if other_only:
                skip['Km: evidence not experimental (author statement, inference, similarity)'] += 1
                continue
            p = paper(ids, 'Km', skip)
            if not p:
                continue
            try:
                const = float(k.get('constant'))
            except (TypeError, ValueError):
                skip['Km: no number'] += 1
                continue
            v, unit, err = normalize('Km', repr(const), {'muM': 'uM'}.get(k.get('unit'), k.get('unit') or ''))
            if unit == 'mg/mL':
                skip['Km: over a mass concentration (mg/ml)'] += 1
                continue
            if err or unit != 'mM' or not v or v <= 0:
                skip['Km: not a positive number in a molar unit'] += 1
                continue
            name, quals = split_substrate(REF.sub(' ', k.get('substrate') or ''))
            kept['Km'] += 1
            yield row(p, ec, 'Km', v, name, org, acc, quals, False)
        for t in (kp.get('note') or {}).get('texts') or []:
            ids, other_only = references(t.get('evidences'))
            for metric, num, unit, sub, quals, ref, approx in note_values(t.get('value') or '', skip):
                if ref == 'after_last':
                    skip[f'{metric}: after the note\'s last reference, its own not stated'] += 1
                    continue
                if ref is None and other_only:
                    skip[f'{metric}: evidence not experimental (author statement, inference, similarity)'] += 1
                    continue
                p = paper(ref if ref is not None else ids, metric, skip)
                if not p:
                    continue
                v, u, err = normalize(metric, num, unit)
                if err or not v or v <= 0:
                    skip[f'{metric}: number does not read ({err or "not positive"})'] += 1
                    continue
                kept[metric] += 1
                kept[f'{metric} with a substrate'] += bool(sub)
                yield row(p, ec, metric, v, sub, org, acc, quals, approx)


def main():
    if '--refresh' in sys.argv or not RAW.exists():
        print(f'downloading UniProtKB reviewed entries with kinetics -> {RAW}')
        raw = download()
    else:
        with gzip.open(RAW, 'rt', encoding='utf-8') as f:
            raw = json.load(f)
    skip, kept, n, papers = Counter(), Counter(), 0, set()
    with open(OUT.with_name(OUT.name + '.part'), 'w') as out:
        out.write('pmid\tec\tmetric\tvalue\tsubstrate\torganism\tcomment\n')
        for e in raw['entries']:
            for line in rows(e, skip, kept):
                out.write(line)
                n += 1
                papers.add(line.split('\t', 1)[0])
    OUT.with_name(OUT.name + '.part').rename(OUT)
    print(f"UniProt release {raw.get('release')} ({raw.get('release_date')}, downloaded {raw.get('downloaded')}): "
          f"{len(raw['entries']):,} reviewed entries with kinetics -> {n:,} rows from {len(papers):,} papers in {OUT.relative_to(ROOT)}")
    print('kept values: ' + ', '.join(f'{k} {v:,}' for k, v in kept.items()))
    print('skipped values: ' + ', '.join(f'{k} {v:,}' for k, v in skip.most_common()))


if __name__ == '__main__':
    main()
