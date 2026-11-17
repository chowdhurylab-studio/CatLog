"""Human review: the CatLog review tool's decisions, kept, merged and compared with this catalog (HUMAN_REVIEW.md).

  python3 catlog.py review ingest [PATH...]  keep every new results file (given paths, else ~/Downloads, ~/Desktop and
                                             inbox/, found by content so renamed copies count; the first run also copies
                                             the old store), merge ALL of them, rebuild human_review/decisions.jsonl
                                             (and, from the databases pack's results files, human_review/db_review.jsonl)
  python3 catlog.py review packs             every pack: made when, for whom, what came back, what is open
  python3 catlog.py review stats             decisions, papers, rejection categories, and how v2 compares
  python3 catlog.py review dbstats           the databases pack's answers (human_review/db_review.jsonl, merged by
                                             `review ingest`): which number the paper prints, per stratum and database
  python3 catlog.py review compare [PMID]    human verdicts vs v2 values (writes human_review/compare.tsv; one paper in detail)
  python3 catlog.py review audit             v2 rows that a specific human rejection disputes, as JSON for catlog-audit
  python3 catlog.py review site              human_review/site_handoff.json for the website (WEBSITE.md)
  python3 catlog.py review withdraw PACK_ID   a pack never sent: its measurements become available again
  python3 catlog.py review decided ROW_ID WHY a disputed v2 row the Guideline judged against the paper: no audit needed
  python3 catlog.py review pack [N] [--for a,b] [--cap C] [--gold K] [--seed S]   the next N (40) v2 measurements for reviewers: second opinions,
                                             each kind of trouble (_issue_tests) and a plain random sample, as the same
                                             offline review page and JSON format as before; results come back through `review ingest`
                                             [--send-to EMAIL|LINK] who gets the results files (the page and README say it)
                                             [--rebuild PACK_ID] the same pack again with today's page (keeps its --send-to)
                                             [--free-only] only papers that open free (no ISU login or VPN: reviewers at home)
                                             [--game NAME] that split name gets easy papers first and the game page
                                             [--kinds-share 0.25] part of the pack spread over kinds of trouble (0.55)
                                             [--split "Reviewer A:2000,Reviewer B"] one zip per name with only that name's rows (the
                                             last name takes the rest; a paper's rows stay with one person)
                                             [--papers] the --split counts are papers (one for every name); papers nobody
                                             gets leave the pack. With it: [--hard NAME] that name gets only harder papers,
                                             the others none; [--overlap 0.05] at most that share of each person's papers
                                             also goes to one other person (reviewer agreement); [--per-paper 8] papers
                                             drawn in proportion to their records, up to 8 records each (--kinds-share 0,
                                             its default there); [--informative] (with --hard, --per-paper) the hard name's
                                             papers are the harder ones whose records most need a person's check. With
                                             --papers, --split may name one person: an add-on pack, e.g. --split "Reviewer C:50";
                                             [--balanced] (one name, --per-paper) half its papers harder, half not;
                                             [--easier] (one name, --per-paper) only papers that are not harder
  python3 catlog.py review dbpack [--seed S] [--send-to EMAIL]   the "databases disagree" pack (DB_STRATA): values where a
                                             database lists another number than CatLog for the same paper; each card shows
                                             both numbers in the printed unit, blind (which is CatLog's stays in the index),
                                             and the reviewer says which one the paper prints

Rules: never change a v2 value because of a human verdict; a disputed value goes through the audit like any other.
An approval is weak evidence (approvals are often quick); a rejection that names a value is strong.
"""
import csv, gzip, hashlib, json, os, re, subprocess, sys, time
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tools'))
HR = ROOT / 'human_review'
RAW = HR / 'raw'
MANIFEST = RAW / 'manifest.tsv'
PACK = HR / 'old_pack.jsonl.gz'
DECISIONS = HR / 'decisions.jsonl'
COMPARE = HR / 'compare.tsv'
CALIBRATION = HR / 'calibration.txt'
REMAP = HR / 'pmid_remap.tsv'
FIRST = HR / 'first_compare.tsv'  # each reviewed value's bucket at its first comparison with CatLog (in git: the honest measure)
EXPOSED = HR / 'exposed.tsv'  # papers whose reader or verifier opened database values, earlier-catalog files or review data
SITE = HR / 'site_handoff.json'
PACKS = HR / 'packs'
UI = ROOT / 'tools' / 'review_ui'
OLD_REPO = os.environ.get('REALKCAT_DIR') or str(ROOT / 'realkcat')  # the earlier system's review store (optional; README: settings)
OLD_BRANCH, OLD_STORE = 'claude/happy-satoshi-4d320d', 'data/human_review'
EXPORT_GLOB = 'catlog-human-review-results-*.json'
MCOLS = ('manifest_sha256', 'original_name', 'stored_as', 'exported_at', 'pack', 'approved', 'rejected', 'added_on', 'origin')
METRICS = (('kcat', 'kcat', 'kcat_unit'), ('Km', 'km', 'km_unit'), ('kcat/Km', 'kcat_over_km', 'kcat_over_km_unit'))
AUDIT_CATS = ('value', 'substrate', 'variant', 'unit')  # rejections worth an audit when v2 holds the same value
DB_REVIEW = 'db_review.jsonl'  # in HR: the databases pack's answers, merged (_db_ingest); `review dbstats` counts them
DB_CHOICES = ('A', 'B', 'both', 'neither', 'cannot_tell')  # the page's keys 1-5
CONTACT = os.environ.get('CATLOG_CONTACT_EMAIL', '')  # a contact e-mail for the APIs' polite pools (README: settings)


def _git_show(path):
    r = subprocess.run(['git', '-C', OLD_REPO, 'show', f'{OLD_BRANCH}:{path}'], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def _manifest():
    if not MANIFEST.exists():
        return {}
    return {r['manifest_sha256']: r for r in csv.DictReader(open(MANIFEST), delimiter='\t')}


def _db_results(d):
    """A results file of the databases pack's page (ab.js): metadata.pack_kind 'databases', a list of answers and no
    'decisions', so the approve/reject merge never reads it as verdicts."""
    return (isinstance(d, dict) and isinstance(d.get('metadata'), dict) and d['metadata'].get('pack_kind') == 'databases'
            and 'decisions' not in d and isinstance(d.get('answers'), list))


def _add_export(data, original_name, origin, have):
    """Keep one results export (bytes) in raw/, once per content. Returns True when it was new. An approve/reject file
    is kept as export-<time>.json; a databases-pack file (_db_results) as dbcheck-<time>.json, which only _db_ingest
    reads (approved and rejected stay blank in the manifest)."""
    sha = hashlib.sha256(data).hexdigest()
    if sha in have:
        return False
    db = False
    try:
        d = json.loads(data)
        db = _db_results(d)
        if db:
            meta, answers = d['metadata'], d['answers']
            ok = all(isinstance(x, dict) and isinstance(x.get('record_key'), str) and x['record_key']
                     and x.get('choice') in DB_CHOICES for x in answers)
        else:
            meta, decisions = d['metadata'], d['decisions']
            ok = isinstance(meta, dict) and isinstance(decisions, list) and all(
                isinstance(x, dict) and (x.get('record_key') or x.get('measurement_key'))
                and x.get('human_review_status') in ('human_approved', 'human_rejected') for x in decisions)
    except (ValueError, KeyError, TypeError):
        ok = False
    if not ok:
        print(f'  skipped {original_name}: not a CatLog review results file')
        return False
    stored = RAW / f"{'dbcheck' if db else 'export'}-{str(meta.get('exported_at', 'unknown')).replace(':', '-')}.json"
    if stored.exists():
        stored = stored.with_name(f'{stored.stem}-{sha[:8]}.json')  # same time, other content: keep both
    stored.write_bytes(data)
    s = Counter() if db else Counter(x.get('human_review_status') for x in decisions)
    row = {'manifest_sha256': sha, 'original_name': original_name, 'stored_as': stored.name,
           'exported_at': meta.get('exported_at', ''),
           'pack': str(meta.get('source_sha256') or '')[:12] if db else str(meta.get('source_sha256', ''))[:12],
           'approved': '' if db else s['human_approved'], 'rejected': '' if db else s['human_rejected'],
           'added_on': time.strftime('%Y-%m-%d'), 'origin': origin}
    new = not MANIFEST.exists()
    with open(MANIFEST, 'a', newline='') as fh:
        w = csv.DictWriter(fh, MCOLS, delimiter='\t')
        if new:
            w.writeheader()
        w.writerow(row)
    have[sha] = row
    return True


def _to_catalog_unit(metric, value, unit):
    """Old pack values ('s^(-1)', 'min(-1)', 's^(-1)*mM^(-1)') in the catalog units, or None."""
    from units import normalize
    if value in (None, ''):
        return None
    u = re.sub(r'\^?\(([-+]?\d+)\)', r'^\1', str(unit or '')).replace('*', ' ')
    if not u:
        u = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}[metric]  # the old catalog's own unit
    v, _, err = normalize(metric, str(value), u)
    return None if err else v


def _slim_pack():
    """The old review pack without agent traces: identity, values and the 2026-08-26 adjudication per measurement_key."""
    raw = _git_show(f'{OLD_STORE}/pack/human-review-source.jsonl.gz')
    if raw is None:
        print('  old review pack not found (realkcat branch', OLD_BRANCH, 'missing): decisions keep only their own fields')
        return
    adj = {}
    ov = _git_show(f'{OLD_STORE}/merged/catlog_import_overlay.jsonl')
    for line in (ov or b'').decode().splitlines():
        if line.strip():
            r = json.loads(line)
            adj[r.get('record_key')] = {k: r.get(k) for k in ('problem_category', 'adjudication_verdict')}
    with gzip.open(PACK, 'wt') as out:
        for line in gzip.decompress(raw).decode().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            row = {'measurement_key': r.get('measurement_key'), 'review_key': r.get('review_key'),
                   'pmid': str(r.get('pubmed_id') or ''), 'doi': r.get('doi') or '', 'ec': r.get('ec_number') or '',
                   'enzyme': r.get('enzyme_display_name') or r.get('enzyme_name') or '', 'organism': r.get('organism') or '',
                   'substrate': r.get('substrate_name') or '', 'smiles': r.get('smiles') or '', 'uniprot': r.get('uniprot_id') or '',
                   'wild_type': r.get('wild_type'), 'mutations': r.get('mutation_signature') or '',
                   'pH': r.get('ph'), 'temperature_C': round(r['temperature_k'] - 273.15, 1) if r.get('temperature_k') else None,
                   'old_source_db': r.get('source_db') or '', 'old_status': r.get('verification_status') or '',
                   'old_tier': r.get('evidence_confidence_tier') or '', **adj.get(r.get('measurement_key'), {})}
            for m, k, u in METRICS:
                row[m] = _to_catalog_unit(m, r.get(k), r.get(u))
            k, km, e = row['kcat'], row['Km'], row['kcat/Km']
            row['kcat/Km_derived'] = bool(k and km and e and abs(k / km - e) <= 1e-6 * e)  # computed by the old pipeline
            out.write(json.dumps(row, ensure_ascii=False) + '\n')


def classify(comment):
    """The kind of objection a review comment raises (from the 262 rejections reviewed on 2026-10-08)."""
    c = (comment or '').lower()
    if not c.strip() or len(c.strip()) < 4 or c.strip() in ('sd', 'ok'):
        return 'none'
    rest = re.sub(r'value missing:\s*paper also prints[^;\n]*?(?=\.\s+\S|[;\n]|$)', '', c).strip(' ;.')
    if rest != c.strip(' ;.'):  # the review page's "Paper also prints a value not shown" clause: what else does it say?
        return classify(rest) if rest else 'missing_value'
    if re.search(r'value wrong', c) and not re.search(r'wrong substrate|this is the k\s?m value for', c) and stated_values(c):
        return 'value'  # the page's "Value wrong" tag on a number the reviewer states ("NADPH has a Km of ...", 21048316)
    rules = (('no_literature', r'no literature value'), ('substrate', r'this is the k\s?m value for|wrong substrate'),
             ('missing_value', r'missing|no value for|unreported|(k\s?cat|kcat/km)\b[^.]{0,20}(is )?(reported|given|printed)'),
             ('organism', r'organism|species|strain'), ('doi', r'\bdoi\b'), ('duplicate', r'duplicate|merge|same as'),
             ('variant', r'mutant|mutation|wild[- ]?type|variant'), ('conditions', r'\bph\b|temperature|°c|\bdegrees\b'),
             ('unit', r'\bunit|µm|um\b|min-1|per min'),
             ('substrate', r'substrate|ketimine|cofactor|nad'), ('evidence', r'evidence mismatch'),
             ('value', r'value|wrong|inaccurate|incorrect|should be'))
    return next((k for k, rx in rules if re.search(rx, c)), 'other')


STATED = re.compile(r'(?i)\b(k\s?cat\s*/\s*k\s?m|k\s?cat|k\s?m)\b[^0-9=:]{0,25}?(?:=|:|\s[-–]\s|\bis\b|\bas\b|\bof\b|\bbe\b)\s*'
                    r'([0-9][0-9.,]*(?:\s*[x×*]\s*10\^?\s*[-−]?\d+)?)\s*'
                    r'([a-zµμ/][a-z0-9µμ^\-−/().*·]*(?:\s+[a-zµμ][a-z0-9µμ^\-−/().*·]*-1)?)?')  # 'mM^-1 s^-1', '/min', not 's^-1 as well'


def stated_values(comment):
    """Values a reviewer typed into a comment ('Kcat is reported - 30 s^-1'), in catalog units."""
    from units import normalize
    out = []
    # the printed error never becomes the value, read as CatLog reads a cell (units.parse_number): '58 ± 7 µM' is 58 µM;
    # '(6.2 ± 0.9) × 10^3' and '6.2 × 10^3 ± 0.9 × 10^3' (what the card page saves since 2026-11-10) are 6.2 × 10^3;
    # '6.2 ± 0.9 × 10^3' too, unless the error is larger than the number and small times the power: '0.01 ± 2 × 10^-3'
    # is 0.01 (the error's own power). ± may be typed +-, + -, +/-, + / -, ⫾ or '(±9)'; braces and dashes are plain
    comment = re.sub(r'[{}]', '', comment or '').replace('⫾', '±')
    comment = re.sub(r'[−–—‐‑]', '-', comment)
    comment = re.sub(r'\s+[·⋅.]\s+(?=[A-Za-zµμ])', ' ', comment)  # 'M-1 . s-1', 'min^-1 · µM^-1' as one unit
    pm, pw = r'(?:±|\+\s*/?\s*-)', r'\s*[x×*]\s*10\s*\^?\s*(-?\d+)'
    comment = re.sub(rf'\(\s*{pm}\s*([0-9.,]+)\s*\)', r'± \1', comment)  # '62 (±9) µM'
    comment = re.sub(r'(=\s*[0-9][0-9.,]*)\s*[eE]\s*\+?(-?)0*(\d+)\b', r'\1 × 10^\2\3', comment)  # the value's 1.2E+05
    comment = re.sub(r'(=\s*[0-9][0-9.,]*)\s*\(\s*[0-9][0-9.,]*\s*\)', r'\1', comment)  # '652 (45) mM': the error in brackets
    comment = re.sub(r'(=\s*[0-9][0-9.,]*)\s*\+\s*[0-9][0-9.,]*', r'\1', comment)  # 'Km = 0.0051 + 0.0003': a lost ±
    comment = re.sub(rf'\(\s*([0-9][0-9.,]*)\s*{pm}\s*[0-9.,]+\s*\)', r'\1', comment)  # '(6.2 ± 0.9) × 10^3'
    comment = re.sub(rf'([0-9][0-9.,]*\s*[x×*]\s*10\s*\^?\s*-?\d+)\s*{pm}\s*[0-9.,]+(?:{pw})?', r'\1', comment)  # '6.2 × 10^3 ± 0.9 × 10^3'

    def pair(m):  # '6.2 ± 0.9 × 10^3' without brackets: units.parse_number's rule
        a, b = (float(x.replace(',', '')) for x in (m.group(1), m.group(2)))
        return m.group(1) if b > a and b * 10 ** int(m.group(3)) < a else f'{m.group(1)} × 10^{m.group(3)}'
    comment = re.sub(rf'([0-9][0-9.,]*)\s*{pm}\s*([0-9][0-9.,]*){pw}', pair, comment)
    comment = re.sub(rf'\s*{pm}\s*[0-9.,]+', '', comment)
    for m in STATED.finditer(comment):
        name = re.sub(r'\s', '', m.group(1).lower())
        metric = 'kcat/Km' if '/' in name else 'kcat' if name == 'kcat' else 'Km'
        unit = (m.group(3) or '').strip() or {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}[metric]
        v, _, err = normalize(metric, m.group(2), unit)
        if err and ' ' in unit:
            v, _, err = normalize(metric, m.group(2), unit.split()[0])
        if err and m.group(3) and not re.search(r'[mµμun]?M\b|s\b|min|sec|-1', m.group(3)) \
                and not re.match(r'[pnuµμm]?M|s\b|s\^|s-|min|sec|/', m.group(3).strip()):  # 'Km of 0.0092 and ...' (not '58 µMr')
            v, _, err = normalize(metric, m.group(2), {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}[metric])
        if not err:
            out.append({'metric': metric, 'value': v, 'printed': m.group(0).strip()})
    return out


def _remap():
    out = {}
    if REMAP.exists():
        for line in open(REMAP):
            f = line.strip().split('\t')
            if len(f) >= 2 and f[0].isdigit():
                out[f[0]] = f[1]
    return out


MARKER = b'CatLog Human Review Results'
DB_MARKER = b'CatLog database check results'  # the databases pack's page (ab.js) names its results files so


def _is_results_file(f):
    """Any JSON a review page exported, whatever it was renamed to (the marker sits in its first bytes)."""
    try:
        head = f.open('rb').read(4096) if f.is_file() and f.suffix.lower() == '.json' else b''
        return MARKER in head or DB_MARKER in head
    except OSError:
        return False


# the page's Not sure writes "Could not check: not sure: " before the reviewer says why: with nothing after it, no reason
EMPTY_UNSURE = re.compile(r'could not check:\s*not sure:?\s*(?:;\s*|$)', re.I)


def _cant_check_note(note):
    """A Can't check note, as the page counts one: starts with 'Could not check' once empty not-sure starts are gone."""
    return bool(re.match(r'\s*could not check\b', EMPTY_UNSURE.sub('', note), re.I))


# Who made the earlier review page's results files, which saved no name, by the file's sha256 (manifest.tsv). Two
# people who decided the same record are then two reviewers, not one changing their mind.
RAW_NAMES = {**dict.fromkeys(('b5408f6dd5e5', 'efae6b1ae7e1', '903b0d88d61a', '80656f3f49ed'), 'Reviewer B'),
             **dict.fromkeys(('595cb4d9bd7c', 'dd66e0bc81fe', '47ad2ef3f540', '3a904a590364', '09d07f8e832b',
                              '236a7cb7a16b', '13aa080142c4', 'df1b7fe38ba1', '51ae32123650', '523d9928698a',
                              '441c87a0fd46', '411c0cff16fd', 'c328407f93b2', '4607d48c06c1', 'f30b6668a72f',
                              'e4fd7a4f5bc9', 'e9dec48eb204'), 'Reviewer A')}


# Decisions a reviewer said, outside the review page, were made without the paper: no check of it, so ingest drops them
# like a withdrawn decision and lists them in could_not_check.tsv with the reason, per (record key, reviewer).
NO_PAPER = {(k, 'Reviewer C'): "could not open the article; approved without the paper"
            for k in []}


def ingest(paths=()):
    """Keep every new results file (from `paths`, else ~/Downloads, ~/Desktop and anywhere under inbox/, found by
    content so renamed copies count), then merge all of them. Per value and reviewer the latest decision wins (decision
    time = human_reviewed_at; a later comment edit = updated_at); across reviewers a rejection wins and the
    disagreement is kept. Rows a reviewer left undecided with a "Could not check: ..." note (the page's Can't check)
    are listed in could_not_check.tsv. A reviewer who decided a row and later turned it into Can't check (the game
    page's Back, then "I can't find it") has withdrawn that decision: their newest file holds the note, not the decision.
    The databases pack's results files (answers, no decisions) are kept the same way and merged apart (_db_ingest)."""
    import catlog
    HR.mkdir(exist_ok=True); RAW.mkdir(exist_ok=True)
    if not REMAP.exists():
        REMAP.write_text('old_pmid\tright_pmid\twhy\n742472\t29022135\tPMID is a 1978 psychiatry paper; the reviewed values '
                         'come from 29022135 (old download chat, 2026-10-08)\n')
    have = _manifest()
    added = 0
    if not have:  # first run: everything the old store kept, including exports no longer in Downloads
        r = subprocess.run(['git', '-C', OLD_REPO, 'ls-tree', '-r', '--name-only', OLD_BRANCH, '--', f'{OLD_STORE}/raw_exports/'],
                           capture_output=True, text=True)
        for path in sorted(p for p in r.stdout.split() if p.endswith('.json') and not p.endswith('MANIFEST.json')):
            data = _git_show(path)
            if data:
                added += _add_export(data, Path(path).name, 'old store', have)
    if paths:
        files = [f for p in map(Path, paths) for f in ([p] if p.is_file() else sorted(p.rglob('*.json')) if p.is_dir() else [])]
        missing = [p for p in paths if not Path(p).exists()]
        for p in missing:
            print(f'  {p}: not found')
    else:
        files = [f for d in (Path.home() / 'Downloads', Path.home() / 'Desktop') if d.exists() for f in sorted(d.glob('*.json'))]
        files += sorted((ROOT / 'inbox').rglob('*.json')) if (ROOT / 'inbox').exists() else []
    for f in files:
        if _is_results_file(f) or paths:
            added += _add_export(f.read_bytes(), f.name, f'copied from {f.parent}', have)
    if not PACK.exists():
        _slim_pack()
    pack = {}
    if PACK.exists():
        with gzip.open(PACK, 'rt') as fh:
            pack = {r['measurement_key']: r for r in map(json.loads, fh)}
    events, drafts, packs, v2keys = defaultdict(dict), defaultdict(set), defaultdict(set), set()
    latest = {}  # (key, reviewer) -> (exported_at, note): that reviewer's newest draft of the value, whatever it says
    dec_at = {}  # (key, reviewer) -> exported_at of that reviewer's newest file that decides the value
    for f in sorted(RAW.glob('export-*.json')):
        b = f.read_bytes()
        d = json.loads(b)
        meta = d.get('metadata', {})
        named = RAW_NAMES.get(hashlib.sha256(b).hexdigest()[:12], '')  # the earlier page saved no name
        pid = str(meta.get('source_sha256', ''))[:12]
        is_v2 = meta.get('source_file') == 'catlog_wide.jsonl' or bool(meta.get('pack_id'))
        for x in d.get('decisions', []):
            if not isinstance(x, dict) or x.get('human_review_status') not in ('human_approved', 'human_rejected'):
                continue
            k = x.get('record_key') or x.get('measurement_key')
            who = ' '.join(str(x.get('reviewer_name') or meta.get('reviewer_name') or named).split())
            # one event per (reviewer, decision time, verdict, comment); keep its latest updated_at (a comment edit, or
            # "Load previous results", changes only updated_at)
            ev = (who, x.get('human_reviewed_at') or x.get('updated_at') or '', x.get('human_review_status', ''),
                  ' '.join(str(x.get('human_review_comment') or '').split()))
            events[k][ev] = max(events[k].get(ev, ''), x.get('updated_at') or '')
            dec_at[(k, who)] = max(dec_at.get((k, who), ''), str(meta.get('exported_at') or ''))
            packs[k].add(pid)
            if is_v2:
                v2keys.add(k)
        for x in d.get('draft_comments', []):
            if isinstance(x, dict) and x.get('draft_comment'):
                note = ' '.join(str(x['draft_comment']).split())
                drafts[x.get('record_key')].add(note)
                who = ' '.join(str(meta.get('reviewer_name') or named).split())
                at = str(meta.get('exported_at') or '')
                if at >= latest.get((x.get('record_key'), who), ('',))[0]:  # that reviewer's latest file
                    latest[(x.get('record_key'), who)] = (at, note)
    # the page's "Can't check": the newest draft is still a "Could not check" note (a newer draft that replaced it, say
    # a rejection being written, clears it; a file that does not mention the value leaves it); decided values go below
    cant = {kw: v for kw, v in latest.items() if _cant_check_note(v[1])}
    # a decision the same reviewer later turned into Can't check (a newer file with the note and without the decision;
    # a file that still decides it keeps it): that reviewer's verdicts on the value are withdrawn
    withdrawn = {kw for kw, (at, _) in cant.items() if kw in dec_at and at > dec_at[kw]}
    for k, who in withdrawn:
        events[k] = {e: u for e, u in events[k].items() if e[0] != who}
        if not events[k]:
            del events[k]
    for (k, who), note in NO_PAPER.items():  # decided without the paper, by the reviewer's own word
        if k in events:
            events[k] = {e: u for e, u in events[k].items() if e[0] != who}
            if not events[k]:
                del events[k]
        cant[(k, who)] = ('', note)
    before = {r['key']: r for r in map(json.loads, open(DECISIONS))} if DECISIONS.exists() else {}
    old = {k: (r['status'], r['comment']) for k, r in before.items()}
    wide = {}
    if (ROOT / 'catlog_wide.jsonl').exists():  # a v2 verdict whose pack index is missing still finds its rows
        for w in map(json.loads, open(ROOT / 'catlog_wide.jsonl')):
            wide[w['measurement_id']] = {'pmid': w['pubmed_id'], 'row_ids': w.get('row_ids', [])}
            for rid in w.get('row_ids', []):
                wide[rid] = {'pmid': w['pubmed_id'], 'row_ids': [rid]}
    remap = _remap()
    v2packs = {}
    for f in (list(PACKS.glob('*.json')) + list((PACKS / 'withdrawn').glob('*.json'))) if PACKS.exists() else []:
        idx = json.loads(f.read_text())
        if 'source_sha256' in idx:  # a review pack (not another chat's case-review index, cases-*.json)
            v2packs[idx['source_sha256'][:12]] = idx
    rows = []
    for k, evs in events.items():
        hist = sorted(evs, key=lambda e: (e[1], evs[e]))
        final = {}  # per reviewer: the latest decision (decision time, then the latest edit)
        for e in hist:
            final[e[0]] = e
        verdicts = {who: e[2].replace('human_', '') for who, e in final.items()}
        rejected = [e for e in final.values() if e[2] == 'human_rejected']
        who, at, st, comment = (max(rejected, key=lambda e: (e[1], evs[e])) if rejected
                                else max(final.values(), key=lambda e: (e[1], evs[e])))  # across reviewers a rejection wins
        p = pack.get(k, {})
        # a paper one pack lends another (shared_with) counts under the pack it was drawn in, whoever decided first
        mine = min((x['records'][k] for pid in sorted(packs[k]) for x in [v2packs.get(pid)] if x and k in x['records']),
                   key=lambda v: bool(v.get('shared_with')), default=None)
        was = before.get(k, {})
        if mine:  # a verdict on v2's own measurement (a v2 review pack)
            p = {'pmid': mine['pmid'], 'row_ids': mine['row_ids'],  # a borrowed record stays its lender's
                 'v2_pack': (mine.get('shared_with') or {}).get('pack_id') or mine['pack_id'],
                 'why': mine.get('why', ''), 'issues': mine.get('issues', [])}
        elif was.get('v2_pack') not in (None, '', 'unknown'):  # its pack's rebuild left it out (a re-read or audit
            # replaced its rows): keep what the last ingest knew, so a reviewed random row stays in the headline
            p = {f: was.get(f, d) for f, d in (('pmid', ''), ('row_ids', []), ('v2_pack', ''), ('why', ''), ('issues', []))}
        elif k in wide and (k in v2keys or k not in pack):
            p = {**wide[k], 'v2_pack': 'unknown'}
        elif k in v2keys:  # a v2 verdict whose measurement no longer exists
            p = {'pmid': '', 'row_ids': [], 'v2_pack': 'unknown'}
        pmid = remap.get(p.get('pmid', ''), p.get('pmid', ''))
        rows.append({'key': k, 'status': st.replace('human_', ''), 'comment': comment, 'decided_at': at, 'by': who,
                     'reviewers': verdicts, 'disagree': len(set(verdicts.values())) > 1,
                     'category': classify(comment) if st == 'human_rejected' or comment else '',
                     'stated': list({(v['metric'], round(v['value'], 9)): v for e in final.values()
                                     for v in stated_values(e[3])}.values()) or
                               list({(v['metric'], round(v['value'], 9)): v for e in hist for v in stated_values(e[3])}.values()),
                     'changed': any(len({e[2] for e in hist if e[0] == r}) > 1 for r in final),
                     'history': [{'by': e[0], 'at': e[1], 'status': e[2].replace('human_', ''), 'comment': e[3]} for e in hist],
                     'drafts': sorted(drafts.get(k, ())), 'pack': sorted(packs[k]), 'pmid': pmid,
                     'checkable': bool(pmid), **{f: v for f, v in p.items() if f not in ('measurement_key', 'pmid')}})
    by_comment = defaultdict(list)  # a templated sweep: one comment on 5+ values within 2 minutes
    for r in rows:
        if r['status'] == 'rejected' and r['comment']:
            by_comment[r['comment']].append(r)
    for group in by_comment.values():
        times = sorted(time.mktime(time.strptime(r['decided_at'][:19], '%Y-%m-%dT%H:%M:%S')) for r in group if r['decided_at'][:4].isdigit())
        sweep = any(times[i + 4] - times[i] <= 120 for i in range(len(times) - 4))
        for r in group:
            r['sweep'] = sweep
    rows.sort(key=lambda r: (r['pmid'] or '~', r['key']))
    tmp = DECISIONS.with_suffix('.jsonl.tmp')
    with open(tmp, 'w') as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    tmp.replace(DECISIONS)
    _calibration(rows, catlog)
    oldrev = [r for r in rows if not r.get('v2_pack')]
    st = Counter(r['status'] for r in oldrev)
    new = [r for r in rows if r['key'] not in old]
    changed = [r for r in rows if r['key'] in old and old[r['key']] != (r['status'], r['comment'])]
    disagree = [r for r in rows if r['disagree']]
    db = _db_ingest()  # the databases pack's answers: their own file, never decisions.jsonl
    catlog.log('-', 'review_ingest', f'exports_added={added}', f'decisions={len(rows)}', f'approved={st["approved"]}',
               f'rejected={st["rejected"]}', f'new={len(new)}', f'changed={len(changed)}', f'disagreements={len(disagree)}',
               *([f'db_answers={db["answers"]}'] if db else []))
    print(f'{added} new results file(s) kept in human_review/raw/ ({len(have)} in all). Earlier review (old catalog): '
          f'{len(oldrev):,} decisions ({st["approved"]:,} approved, {st["rejected"]:,} rejected) on '
          f'{len({r["pmid"] for r in oldrev if r["pmid"]}):,} papers. Reviews of v2 values: {len(rows) - len(oldrev)}. '
          f'Since the last ingest: {len(new):,} new, {len(changed)} changed' + (f'; reviewers disagree on {len(disagree)}' if disagree else ''))
    for r in changed[:20]:
        print(f"  changed {r['key']} (PMID {r['pmid'] or '-'}): {old[r['key']][0]} -> {r['status']}  {r['comment'][:80]}")
    for r in disagree[:20]:
        print(f"  reviewers disagree on {r['key']} (PMID {r['pmid'] or '-'}): {r['reviewers']}")
    # rows nobody decided are not in decisions.jsonl: the reasons a reviewer gave for leaving them undecided go here
    unchecked = [(k, who, note) for (k, who), (_, note) in sorted(cant.items()) if not any(e[0] == who for e in events.get(k, {}))]
    if withdrawn:
        print(f"  withdrawn by their reviewer (decided, later Can't check): {len(withdrawn)} value(s)")
    def pmid_of(k):
        mine = next((x['records'][k] for x in v2packs.values() if k in x['records']), None)
        p = (mine or wide.get(k) or pack.get(k) or {}).get('pmid', '')
        return remap.get(p, p)
    with open(HR / 'could_not_check.tsv', 'w') as fh:
        fh.write('key\tpmid\treviewer\tnote\n')
        for k, who, note in unchecked:
            fh.write(f'{k}\t{pmid_of(k)}\t{who}\t{note}\n')
    print(f"Can't check (left undecided with a note): {len(unchecked)} value(s) from "
          f"{len({who for _, who, _ in unchecked})} reviewer(s), in human_review/could_not_check.tsv")
    if db:
        print(db['line'])


DB_PICKED = (('catlog', "CatLog's number"), ('database', "the database's"), ('both', 'both'), ('neither', 'neither'),
             ('cannot_tell', "can't tell"))  # what a databases-pack answer says, as db_review.jsonl's picked


def _db_ingest():
    """Merge every databases-pack results file in raw/ (dbcheck-*.json) into human_review/db_review.jsonl, one line per
    card (record_key): per reviewer their latest answer (updated_at, then answered_at, as the page orders them: a change
    keeps answered_at and moves updated_at; a later file wins a tie), and
    across reviewers the latest one, with every reviewer's pick in reviewers and disagree when they differ. The pack
    index (packs/ or packs/withdrawn/, found by the file's pack_id, else its source_sha256) gives the value (pmid,
    metric, measurement_id), its stratum, found_by, cause and sources, and which side was CatLog's: picked = catlog or
    database for A/B, else the choice (both, neither, cannot_tell); '' when no index knows the card. Returns
    {'answers': n, 'line': the summary line}, or None before the first databases results file."""
    files = sorted(RAW.glob('dbcheck-*.json'))
    if not files:
        return None
    index = {}  # pack_id and source_sha256 -> a databases pack index
    for f in (list(PACKS.glob('*.json')) + list((PACKS / 'withdrawn').glob('*.json'))) if PACKS.exists() else []:
        idx = json.loads(f.read_text())
        if idx.get('pack_kind') == 'databases':
            index[idx['pack_id']] = index[idx['source_sha256']] = idx
    latest = {}  # (record_key, reviewer) -> ((updated_at, answered_at), answer, pack_id, index record)
    for f in files:
        d = json.loads(f.read_bytes())
        if not _db_results(d):
            continue
        meta = d['metadata']
        idx = index.get(meta.get('pack_id')) or index.get(meta.get('source_sha256')) or {}
        for a in d['answers']:
            if not isinstance(a, dict) or a.get('choice') not in DB_CHOICES or not a.get('record_key'):
                continue
            k = str(a['record_key'])
            who = ' '.join(str(a.get('reviewer_name') or meta.get('reviewer_name') or '').split())
            # last changed first: the page keeps answered_at when an answer changes and moves only updated_at
            t = (str(a.get('updated_at') or a.get('answered_at') or ''), str(a.get('answered_at') or ''))
            if (k, who) not in latest or t >= latest[(k, who)][0]:
                latest[(k, who)] = (t, a, idx.get('pack_id') or str(meta.get('pack_id') or ''), (idx.get('records') or {}).get(k))
    per_key = defaultdict(list)
    for (k, who), v in latest.items():
        per_key[k].append((who, *v))
    def picked(a, rec):
        side = (rec or {}).get('catlog_side')
        if a['choice'] not in ('A', 'B'):
            return a['choice']
        return '' if side not in ('A', 'B') else 'catlog' if a['choice'] == side else 'database'
    rows = []
    for k, answers in per_key.items():
        picks = {who: picked(a, rec) or a['choice'] for who, _, a, _, rec in answers}  # the side unknown: the bare A/B
        who, _, a, pack_id, rec = max(answers, key=lambda x: (x[1], x[0]))
        rec = rec or {}
        rows.append({'key': k, 'pmid': rec.get('pmid', ''), 'metric': rec.get('metric', ''), 'stratum': rec.get('stratum', ''),
                     'found_by': rec.get('found_by', ''), 'cause': rec.get('cause', ''), 'sources': rec.get('sources', []),
                     'measurement_id': rec.get('measurement_id', ''), 'pack': pack_id, 'choice': a['choice'],
                     'picked': picked(a, rec), 'typed_value': str(a.get('typed_value') or '').strip() if a['choice'] == 'neither' else '',
                     'note': str(a.get('note') or '').strip(), 'by': who, 'at': a.get('updated_at') or a.get('answered_at') or '',
                     'reviewers': picks, 'disagree': len(set(picks.values())) > 1})
    rows.sort(key=lambda r: (r['pmid'] or '~', r['key']))
    out = HR / DB_REVIEW
    tmp = out.with_suffix('.jsonl.tmp')
    with open(tmp, 'w') as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    tmp.replace(out)
    n = Counter(r['picked'] for r in rows)
    unknown = sum(1 for r in rows if not r['stratum'])
    disagree = sum(1 for r in rows if r['disagree'])
    line = (f"Database check: {len(rows):,} values answered on {len({r['pmid'] for r in rows if r['pmid']}):,} papers by "
            f"{len({w for r in rows for w in r['reviewers']})} reviewer(s) ({len(files)} results file(s)), in "
            f"human_review/{DB_REVIEW}: the paper prints " + ', '.join(f'{label} {n[p]}' for p, label in DB_PICKED)
            + (f'; reviewers disagree on {disagree}' if disagree else '')
            + (f'; {unknown} answer(s) from no known databases pack (its index is missing)' if unknown else '')
            + '. Counts: python3 catlog.py review dbstats')
    return {'answers': len(rows), 'line': line}


def _calibration(rows, catlog):
    """Every human-reviewed paper CatLog has not read yet: `next` reads them before other papers (on disk first, then
    the ones it has to fetch), so CatLog is measured against the reviewers on as many papers as it can (user, 2026-10-12:
    only 102 of the 408 reviewed papers were compared when the list held 30)."""
    score = defaultdict(lambda: [0, 0])
    for r in rows:
        if r['pmid'] and r['checkable']:
            s = score[r['pmid']]
            s[0] += (r['status'] == 'rejected' and r.get('category') not in ('no_literature', 'none')) or bool(r['stated'])
            s[1] += r['status'] == 'approved'
    with catlog.Queue(write=False) as q:
        waiting = {p for p, x in q.rows.items() if x['status'] in ('todo', 'needs_browser', 'needs_supplement')}
    pick = sorted((p for p in score if p in waiting), key=lambda p: (not catlog.on_disk(p), -score[p][0], -score[p][1]))
    CALIBRATION.write_text(''.join(p + '\n' for p in pick))


def _decisions():
    if not DECISIONS.exists():
        sys.exit('no human review yet: run python3 catlog.py review ingest')
    return [json.loads(l) for l in open(DECISIONS) if l.strip()]


MUT = re.compile(r'(?<![A-Za-z0-9])[A-Z][a-z]{0,2}\d+[A-Z][a-z]{0,2}(?![a-z0-9])')  # Y228F, Tyr228Phe; not 'R1C' in AKR1C21


def _muts(text):
    return frozenset(MUT.findall(str(text or '')))


def _variant_v2(variant, enzyme=''):
    """(point mutations, anything else) of a v2 variant: 'wild type' -> ((), ''), 'Δ74-80' -> ((), 'δ7480').
    An isoform name the enzyme name already carries ('BjussuLAAO-II' in 'L-amino acid oxidase BjussuLAAO-II') is not a
    variant."""
    v = str(variant or '')
    muts = _muts(v)
    rest = MUT.sub('', v)
    rest = '' if re.fullmatch(r'\W*(wild[ -]?type|wt)?\W*', rest, re.I) else re.sub(r'\W', '', rest.lower())
    if rest and not muts and rest in re.sub(r'\W', '', str(enzyme or '').lower()):
        rest = ''
    return muts, rest


def _variant_old(d):
    """The same key for an old reviewed row; a mutant with no signature never matches anything."""
    muts = _muts(d.get('mutations'))
    return muts, ('?' if d.get('wild_type') is False and not muts else '')


def _name(s):
    # a trailing "(at pH 6.25 and 30 degrees Celsius)" (old rows) or compound number "(4)" (v2 rows) is not the name
    s = re.sub(r'\s*\((?:(?:at|with|in|using|as)\s[^()]*|\d+[a-z]?)\)\s*$', '', str(s or ''), flags=re.I)
    for g, w in GREEK.items():  # 17α = 17alpha
        s = s.replace(g, w)
    s = re.sub(r'[^a-z0-9]', '', s.lower())
    return re.sub(r'(an|en)e(?=\d)', r'\1', s)  # IUPAC elision: pregnane-3,21-diol = pregnan-3,21-diol


METAL_NT = re.compile(r'(?:mg|mn|ca|co|zn|ni|fe|cd|cu)?(d?[acgitu][mdt]p)(?:mg|mn|ca|co|zn|ni|fe|cd|cu)?\d*')


def _bare(n):
    """One spelling per compound for matching (_name form): a metal-nucleotide complex is its nucleotide ('ATPMn2−',
    'MgATP2−' = ATP; PMID 16330239 names the Mn complexes, the earlier catalog the nucleotides), an acid its anion
    ('...-1-carboxylic acid' = '...-1-carboxylate', PMID 28450969), and 'N-phospho-X' is 'X N-phosphate'
    ('4-phospho-D-threonate' = 'D-threonate 4-phosphate', PMID 27402745)."""
    m = METAL_NT.fullmatch(n or '')
    n = m.group(1) if m else (n or '')
    n = re.sub(r'icacid$', 'ate', n)
    p = re.fullmatch(r'(\d+)phospho([a-z].*)', n)
    return f'{p.group(2)}{p.group(1)}phosphate' if p else n


GREEK = {'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta', 'Δ': 'delta', 'ε': 'epsilon', 'ω': 'omega', 'κ': 'kappa',
         'λ': 'lambda', 'μ': 'mu', 'µ': 'mu'}
_STRUCTURES = {}


def _structure(s):
    """(InChIKey connectivity block, RDKit mol) of the neutral largest fragment (structures.finish), cached; ('', None)
    when it does not parse. Charge and salt form are set aside (3-hydroxy-3-methyl-2-oxobutanoate = the free acid), and
    the mol is read back from its standard InChI, so tautomers drawn differently (an amide or its imidic acid, PMID
    14734559) become the same graph while every defined stereocentre is kept."""
    if s not in _STRUCTURES:
        _STRUCTURES[s] = ('', None)
        try:
            import structures
            from rdkit import Chem
            f, _ = structures.finish(s)
            m = Chem.MolFromSmiles(f) if f else None
            if m is not None:
                _STRUCTURES[s] = (structures.key(f, 14), Chem.MolFromInchi(Chem.MolToInchi(m)) or m)
        except Exception:
            pass
    return _STRUCTURES[s]


def _fits(a, b):
    """The same compound up to what one side leaves unsaid: the same connectivity and every stereocentre that both
    define the same (2-deoxy-D-glucose with or without its anomer; L- vs D-, 20R vs 20S never fit)."""
    if not a or not b:
        return False
    if a == b:
        return True
    ka, ma = _structure(a)
    kb, mb = _structure(b)
    return bool(ka) and ka == kb and (ma.HasSubstructMatch(mb, useChirality=True) or mb.HasSubstructMatch(ma, useChirality=True))


def _same_structure(h, v, paper):
    """The reviewed row's structure h is v2's structure v, and no other compound among the paper's v2 structures fits h:
    a stereo-free 'pregnanediol' in a paper with two pregnanediol isomers pairs with neither (no ambiguous pairing)."""
    return _fits(h, v) and all(_fits(v, s) for s in paper if _fits(h, s))


def _close(a, b):
    return a is not None and b is not None and abs(a - b) <= 0.02 * max(abs(a), abs(b))


def _genus_species(o):
    """'human' (as a v2 reader writes it) is 'homo sapiens' (as a reviewed row has it): 10514444's human ADH4 Km had
    gone unmatched."""
    from enrich import binomial
    return ' '.join(re.findall(r'[a-z]+', binomial(str(o or '')).lower())[:2])


def _same_organism(a, b, paper):
    """The same binomial, or a renamed genus (Mycolicibacterium = Mycobacterium smegmatis, Stenotrophomonas = Pseudomonas
    maltophilia) when no other organism of the paper shares that species name."""
    a, b = _genus_species(a), _genus_species(b)
    epithet = lambda o: o.split()[1] if len(o.split()) == 2 and o.split()[1].rstrip('.') not in ('sp', 'spp') else ''  # 'X sp.' names no species
    stem = lambda e: re.sub(r'(?:us|um|is|ae|a|e|i)$', '', e)  # Latin gender endings: Agaricus xanthoderma = xanthodermus
    return a == b or (bool(epithet(a)) and epithet(a) == epithet(b) and sum(epithet(o) == epithet(b) for o in paper) == 1) \
        or (bool(epithet(a)) and bool(epithet(b)) and a.split()[0] == b.split()[0] and len(stem(epithet(a))) >= 5
            and stem(epithet(a)) == stem(epithet(b)))


_CURRENT = {}


def _current_acc(acc):
    """UniProt's current entry for an old row's accession: merged -> its target, deleted or split -> '' (unknown, so
    the organism decides: A0A0K2AZ61 was deleted, its sequence lives on as A0ABN4PDQ0). Cached by sequences.py."""
    if acc and acc not in _CURRENT:
        try:
            from sequences import check_active
            _CURRENT[acc] = check_active(acc)['acc']
        except Exception:  # offline: compare the accession as printed
            return acc
    return _CURRENT.get(acc, '')


OBJECTS_TO_VALUE = AUDIT_CATS + ('evidence',)  # a rejection for these is about the number; others are about the old row
ROW_ONLY = ('missing_value', 'duplicate', 'doi', 'no_literature')  # a rejection that says nothing against the values shown
DISPUTE = re.compile(r'\b(wrong|mismatch|inaccurate|incorrect|not in paper|should be|too (?:high|low))\b')


def row_only(d):
    """A v2-pack rejection that disputes none of the values shown: its kind is a row point (another value the paper
    prints, a duplicate, the DOI) and, the page's 'Value missing: paper also prints ...' clause aside, it names no
    problem ('Km wrong ... same as the wild-type value' classifies as a duplicate but disputes the Km)."""
    rest = re.sub(r'value missing:\s*paper also prints[^;\n]*?(?=\.\s+\S|[;\n]|$)', '', (d.get('comment') or '').lower())
    return d.get('category') in ROW_ONLY and not DISPUTE.search(rest)
SITE_MARKS = HR / 'site_marks.json'  # what the website shows (HUMAN_REVIEW.md "Guideline"); `site stage` copies it
CONFIRMED = {'8471035': 'organism'}  # rejections the Guideline judged a confirmation of the values (the name only differs)
CASE_NOTES = {  # HUMAN_REVIEW.md "Guideline", case by case: what the reviewer assessed, said neutrally on the site
    '8471035': 'A reviewer confirmed the values; the paper names the organism Pseudomonas maltophilia (now Stenotrophomonas maltophilia).',
    '3191146': 'A reviewer questioned the substrate name; the compound measured is S-aminoethylcysteine ketimine (3,4-dehydrothiomorpholine-3-carboxylate; shown here as 2H-1,4-thiazine-5,6-dihydro-3-carboxylic acid), and the value is the one the paper prints (Table V).',
    '21149620': {'': 'A reviewer flagged the evidence text; the values are the ones the paper prints (Table 3, VIM-4).',
                 'cephalothin': 'A reviewer flagged the evidence text and the substrate name; the values and the substrate, cephalothin, are as the paper prints them (Table 3, VIM-4).',
                 'cephalotin': 'A reviewer flagged the evidence text and the substrate name; the values and the substrate, cephalothin, are as the paper prints them (Table 3, VIM-4).'},
    '19251889': 'A reviewer questioned this Km; the paper prints 393 µM (0.393 mM), as stored (Table 2).',
    '33020946': 'A reviewer questioned the kcat/Km; the paper prints Km 207 mM and kcat/Km 0.05 mM⁻¹ s⁻¹ (10.5/207, rounded), as stored.',
}


def _metrics_named(comment):
    """The metrics a comment names ('Value wrong for Km.'), or all three when it names none."""
    c = (comment or '').lower()
    named = {m for m, rx in (('kcat/Km', r'k\s?cat\s*/\s*k\s?m'), ('kcat', r'k\s?cat(?!\s*/)'), ('Km', r'(?<!/)\bk\s?m\b')) if re.search(rx, c)}
    return named or {'kcat', 'Km', 'kcat/Km'}


def compare(pmid=None, write=True, quiet=False, record=True):
    """Every human verdict on a value against v2. Approved: agree / v2_different_value / v2_rejected / v2_lacks /
    approved_with_objection (approved, but the comment objects) / paper_not_read; derived kcat/Km set aside.
    Rejected (for a value, unit, substrate, variant or evidence reason, on the metrics the comment names):
    v2_has_same / v2_has_different / v2_lacks_rejected; rejected for anything else (missing value, organism, DOI,
    duplicate, no literature): row_objection. Values a reviewer typed: stated_found / stated_missing.
    A v2 value matches when paper, metric, variant (point mutations and any other variant text), substrate (a name in
    common, or the same structure: InChIKey connectivity, stereocentres both sides define, no other isomer in the paper)
    and, where both are known, UniProt accession (the old one as UniProt has it now; else organism, in papers with
    several organisms, a renamed genus counting as the same species) agree. A gene name (AKR1C21) is not a mutation."""
    import catlog
    rows = _decisions()
    cat = [json.loads(l) for l in open(catlog.CATALOG) if l.strip()] if catlog.CATALOG.exists() else []
    rej = [json.loads(l) for l in open(catlog.REJECTED) if l.strip()] if catlog.REJECTED.exists() else []
    # reviewers judged values in mM; a Km or kcat/Km kept over a mass concentration (mg/mL) is never matched with one
    cat_all, cat = cat, [r for r in cat if catlog.molar(r) is not None]
    rej = [r for r in rej if r.get('unit') not in catlog.MASS_UNIT.values()]  # rejected rows without a value stay
    with catlog.Queue(write=False) as q:
        status = {p: x['status'] for p, x in q.rows.items()}
    sm = json.loads((ROOT / 'enrich' / 'structures.json').read_text()) if (ROOT / 'enrich' / 'structures.json').exists() else {}
    ids = json.loads((ROOT / 'enrich' / 'protein.json').read_text()) if (ROOT / 'enrich' / 'protein.json').exists() else {}
    def v2_smiles(r):
        return (sm.get(f"{r['pmid']}|{catlog.substrate_key(r)}") or {}).get('smiles', '')
    def v2_acc(r):
        return (ids.get(catlog.ident_key(r)) or {}).get('acc', '')
    by_id = {r['row_id']: r for r in cat_all}  # a v2-pack verdict finds its rows whatever their unit
    v2, v2rej = defaultdict(list), defaultdict(list)
    for r in cat:
        v2[r['pmid']].append(r)
    for r in rej:
        v2rej[r['pmid']].append(r)
    organisms = {p: {_genus_species(r.get('organism')) for r in rs} for p, rs in v2.items()}

    paper_smiles = defaultdict(set)
    for r in cat:
        if v2_smiles(r):
            paper_smiles[r['pmid']].add(v2_smiles(r))
    names = {}

    def v2_names(r):
        """The printed name, the reader's full name, and the names v2's structure lookup used for it (the paper's own
        abbreviation definition, a same-paper database name: 'HP' = hydroxypyruvate, 'C4-HSL' = N-butyryl-L-HSL)."""
        if r['row_id'] not in names:
            how = (sm.get(f"{r['pmid']}|{catlog.substrate_key(r)}") or {}).get('how', '')
            names[r['row_id']] = {_name(n) for n in [r.get('substrate'), r.get('substrate_full_name')] + re.findall(r'\[name "([^"]+)" = ', how)} - {''}
        return names[r['row_id']]

    old_by_paper = defaultdict(list)
    for d in rows:
        if d.get('smiles') and not d.get('v2_pack'):
            old_by_paper[d['pmid']].append(d)

    def borrowed(d, r):
        """The old catalog copied a cofactor's SMILES onto substrate rows (PMID 3191146: one of the two (R)-lanthionine
        ketimine rows carries NADPH's). A structure is not this row's when the old rows give this name another structure
        too, and another, differently named old row carries it under v2's own name for it."""
        n = _name(d.get('substrate'))
        same_name = [e for e in old_by_paper[d['pmid']] if _name(e.get('substrate')) == n]
        return (any(not _fits(e['smiles'], d['smiles']) for e in same_name)
                and any(_name(e.get('substrate')) != n and _name(e.get('substrate')) in v2_names(r) and _fits(e['smiles'], d['smiles'])
                        for e in old_by_paper[d['pmid']]))

    def same_substrate(d, r):
        """The same compound: a name in common (case, punctuation, Greek letters and IUPAC elision set aside; no fuzzy
        match, so 3- and 4-nitroacetophenone stay apart) or the same structure (_same_structure, not a borrowed one)."""
        mine = {_bare(n) for n in v2_names(r)}
        if _bare(_name(d.get('substrate'))) in mine:
            return True
        parts = [x for x in re.split(r'\s*;\s*', str(d.get('substrate') or '')) if x.strip()]
        if len(parts) > 1:  # a database's reaction string 'L-Cysteine; O2' (PMID 16855246): the substrate and its co-substrate
            own = [x for x in parts if _bare(_name(x)) in mine]
            rest = [x for x in parts if not own or x is not own[0]]
            co = {_name(r.get('cosubstrate')), 'o2', 'oxygen', 'dioxygen', 'h2o', 'water'} - {''}
            if len(own) == 1 and all(_name(x) in co for x in rest):
                if d.get('smiles') and v2_smiles(r):
                    return _fits(d['smiles'], v2_smiles(r))
                measured = {_bare(n) for x in v2[r['pmid']] if x.get('metric') == r.get('metric') for n in v2_names(x)}
                return not any(_bare(_name(x)) in measured for x in rest)  # v2 has an O2 Km too: whose value is it?
        return _same_structure(d.get('smiles', ''), v2_smiles(r), paper_smiles[r['pmid']]) and not borrowed(d, r)

    def same_as(d, r, metric):
        if r.get('metric') != metric or _variant_v2(r.get('variant'), r.get('enzyme')) != _variant_old(d):
            return False
        if not same_substrate(d, r):
            return False
        acc, old = v2_acc(r), _current_acc(str(d.get('uniprot') or '').strip())
        if acc and old:
            return acc.split('-')[0] == old.split('-')[0]
        if len(organisms.get(d['pmid'], ())) > 1:
            return _same_organism(r.get('organism'), d.get('organism'), organisms[d['pmid']])
        return True

    out = []
    for d in rows:
        if d.get('v2_pack'):  # reviewed in a v2 review pack: the verdict is on these very v2 values
            live = [by_id[i] for i in d.get('row_ids', []) if i in by_id]
            cat_ = d.get('category') or ''
            named = {'kcat', 'Km', 'kcat/Km'} if cat_ in ('substrate', 'variant') else _metrics_named(d.get('comment'))
            objects = d['status'] == 'approved' and cat_ in OBJECTS_TO_VALUE  # a 'Value missing' note alone is missing_value
            for r in live:
                if d['status'] == 'rejected' and row_only(d):
                    b = 'reviewed_in_v2_row_objection'  # "the paper also prints ...": the values shown are not disputed
                elif d['status'] == 'rejected' and cat_ in OBJECTS_TO_VALUE and r['metric'] not in named:
                    b = 'reviewed_in_v2_other_metric'  # "Km wrong" says nothing about this kcat
                else:
                    b = 'v2_approved_with_objection' if objects else 'reviewed_in_v2'
                out.append({**_line(d, r['metric'], r.get('value')), 'pmid': r['pmid'], 'substrate': r.get('substrate', ''),
                            'mutations': r.get('variant', ''), 'bucket': b, 'v2_row_id': r['row_id'],
                            'v2_value': r.get('value'), 'v2_where': r.get('location', '')})
            for st_ in d.get('stated', []):  # the right value a reviewer typed, kept for the audit and the site
                out.append({**_line(d, st_['metric'], st_['value']), 'pmid': (live[0]['pmid'] if live else d['pmid']),
                            'bucket': 'v2_reviewer_stated', 'comment': st_['printed']})
            if not live:
                out.append({**_line(d, '', None), 'bucket': 'v2_changed_since_review'})
            continue
        if not d['checkable']:
            continue
        if d['status'] == 'rejected' and CONFIRMED.get(d['pmid']) == d.get('category'):
            d = {**d, 'status': 'approved', 'category': ''}  # "Kinetics values correct; organism is wrong" (Guideline)
        read = status.get(d['pmid']) in ('done', 'needs_supplement') or bool(v2.get(d['pmid']))
        cat_ = d.get('category') or ''
        objects = d['status'] == 'approved' and cat_ in OBJECTS_TO_VALUE  # approved, yet the comment says something is off
        named = _metrics_named(d.get('comment'))
        for m in ('kcat', 'Km', 'kcat/Km'):
            hv = d.get(m)
            if hv is None:
                continue
            line = _line(d, m, hv)
            if m == 'kcat/Km' and d.get('kcat/Km_derived'):
                out.append({**line, 'bucket': 'derived'}); continue
            if not read:
                out.append({**line, 'bucket': 'paper_not_read'}); continue
            if d['status'] == 'rejected' and (cat_ not in OBJECTS_TO_VALUE or m not in named):
                out.append({**line, 'bucket': 'row_objection'}); continue
            same = [r for r in v2[d['pmid']] if same_as(d, r, m)]
            hit = next((r for r in same if _close(r.get('value'), hv)), None)
            gone = next((r for r in v2rej[d['pmid']] if same_as(d, r, m) and _close(r.get('value'), hv)), None)
            if d['status'] == 'approved':
                b = ('approved_with_objection' if objects else 'agree' if hit else 'v2_different_value' if same
                     else 'v2_rejected' if gone else 'v2_lacks')
            else:
                b = 'v2_has_same' if hit else 'v2_has_different' if same else 'v2_lacks_rejected'
            r = hit or (same[0] if same else gone if b == 'v2_rejected' else None)
            out.append({**line, 'bucket': b, 'v2_row_id': (r or {}).get('row_id', ''), 'v2_value': (r or {}).get('value', ''),
                        'v2_where': (r or {}).get('location', ''),
                        'v2_why': '; '.join(map(str, gone.get('why', [])))[:160] if b == 'v2_rejected' else ''})
        for st_ in d.get('stated', []):  # values a reviewer said the old row missed: does v2 have them?
            if read:
                found = next((r for r in v2[d['pmid']] if same_as(d, r, st_['metric']) and _close(r.get('value'), st_['value'])), None)
                out.append({**_line(d, st_['metric'], st_['value']), 'bucket': 'stated_found' if found else 'stated_missing',
                            'v2_row_id': (found or {}).get('row_id', ''), 'v2_value': (found or {}).get('value', ''),
                            'comment': st_['printed']})
    if write:
        cols = ('key', 'pmid', 'metric', 'status', 'human_value', 'substrate', 'mutations', 'category', 'sweep', 'bucket',
                'v2_row_id', 'v2_value', 'v2_where', 'v2_why', 'comment')
        with open(COMPARE, 'w', newline='') as fh:
            w = csv.DictWriter(fh, cols, delimiter='\t', extrasaction='ignore')
            w.writeheader(); w.writerows(out)
    if record:  # every comparison (status after each batch too), so a paper's first one is kept before any fix it prompts
        try:
            _record_first(out)
            blind_check()
        except Exception as e:  # never let the record break compare or status
            print(f'human review: first-comparison record failed ({e})', file=sys.stderr)
    if pmid:
        remap = _remap()
        want = remap.get(pmid, pmid)
        lines = [x for x in out if x['pmid'] == want]
        print(f"PMID {want}" + (f' (reviewed rows were filed under {pmid})' if want != pmid else '') + f': {len(lines)} lines')
        print(f"{'metric':8} {'verdict':9} {'human':>10} {'v2':>10}  {'bucket':24} {'substrate':30} variant   where / comment")
        g = lambda v: f'{v:.4g}' if isinstance(v, (int, float)) else str(v or '')
        for x in lines:
            print(f"{x['metric']:8} {x['status']:9} {g(x['human_value']):>10} {g(x.get('v2_value')):>10}  {x['bucket']:24} "
                  f"{str(x['substrate'])[:30]:30} {str(x['mutations'] or 'wt')[:9]:9} {x.get('v2_where', '')[:30]}  {x.get('comment', '')[:60]}")
        if not lines:
            print('  no reviewed values for this paper (or not in the human review)')
    return summary(rows, out, quiet)


def _wild_type(w):
    """The UniProt wild-type sequence (catlog_wide's uniprot_sequence carries the variant's mutations)."""
    from sequences import sequence
    try:
        return sequence(w.get('uniprot_id', '')) or (w.get('sequence', '') if w.get('wild_type') else '')
    except Exception:
        return w.get('sequence', '') if w.get('wild_type') else ''


def _line(d, metric, value):
    return {'key': d['key'], 'pmid': d['pmid'], 'metric': metric, 'status': d['status'], 'human_value': value,
            'substrate': d.get('substrate', ''), 'mutations': d.get('mutations', ''), 'category': d.get('category', ''),
            'sweep': d.get('sweep', False), 'comment': d.get('comment', '')}


# HUMAN_REVIEW.md "Guideline", case by case (2026-10-10): what the reviewers' value-related rejections of CatLog v1 entries
# turned out to be when checked against the papers. None is a wrong number.
CLEARED = {'19251889': 'not wrong', '21149620': 'not wrong', '3191146': 'synonym', '8471035': 'synonym',
           '33020946': 'rounding', '11797046': 'display', '15933031': 'duplicate', '26999093': 'duplicate',
           '20124004': 'not wrong',
           '17350620': 'not wrong',
           '20427268': 'not wrong',
           '15081891': 'not wrong',
           '41748636': 'not wrong',
           '22648563': 'not wrong',
           '40362264': 'not wrong',
           '32075249': 'not wrong',
           '34295569': 'rounding',
           '2156846': 'not wrong',
           '28435050': 'not wrong',
           '21048316': 'not wrong'}
VALUE_CATS = ('value', 'unit', 'evidence')  # a rejection that says the number or its unit is wrong
LABEL_CATS = ('organism', 'substrate', 'variant')
DIFFER = ('v2_different_value', 'v2_lacks', 'v2_rejected')  # an approved value CatLog does not have: other value, none, rejected
# the agreement of human reviewers with CatLog (agreement(); the website's quality.agreement), one line per field
AGREEMENT_DEFINITIONS = {
    'papers_compared': "Papers that human reviewers checked in the review of records of CatLog's earlier "
                       'version and that CatLog has since read from the paper.',
    'values_approved': 'kcat, Km and printed kcat/Km values a reviewer approved without objection on those papers (a kcat/Km '
                       "that CatLog's earlier version computed from kcat and Km is left out).",
    'first_agree': 'Approved values CatLog had at the first comparison of their paper, before any reread or fix that '
                   'comparison prompted (label errors it found count as not agreeing). CatLog\'s readers never see the '
                   'reviewers\' verdicts, and later fixes change only agree.',
    'first_agree_pct': 'first_agree as a percentage of values_approved.',
    'agree': 'Approved values CatLog has now, after fixes: the same paper, metric, protein, variant and substrate, and a '
             'value within 2%.',
    'agree_pct': 'agree as a percentage of values_approved.',
    'first_catlog_errors': 'Approved values the first comparison showed CatLog had wrong, checked against the paper '
                           '(unmatched_*.tsv), fixed or not: first_catlog_errors_value + _label + _missed.',
    'first_catlog_errors_value': 'Of first_catlog_errors, a wrong kcat, Km or kcat/Km number or unit (failures).',
    'first_catlog_errors_label': 'Of first_catlog_errors, a wrong label or annotation on a correctly read value: a '
                                 'UniProt entry or substrate structure looked up for the wrong protein or compound, a '
                                 'variant field holding an isoform name. Shown and counted, not failures.',
    'first_catlog_errors_missed': 'Of first_catlog_errors, a value the paper prints that CatLog missed by mistake.',
    'fixed_after_comparison': 'Of first_catlog_errors, those fixed since (CatLog now matches the approved value): '
                              'credit to the human review.',
    'matched_later_other': 'Approved values CatLog did not match at first comparison and matches now with no CatLog '
                           'error behind the change (a better name match, a reading-policy change).',
    'papers_exposed': 'Of papers_compared, papers whose reading or checking agent (the reader, the verifier or a '
                      'completeness check) opened database values or files of CatLog\'s earlier version before the '
                      'paper\'s first add (never the reviewers\' verdicts); found in the agent transcripts (exposed.tsv).',
    'first_agree_unexposed_pct': 'The headline measure: first_agree_pct on the papers read fully blind (no reading or '
                                 'checking agent opened database values or files of CatLog\'s earlier version, which often '
                                 'hold the same values the reviewers saw).',
    'papers_unexposed': 'Papers behind first_agree_unexposed_pct.',
    'first_agree_unexposed_ci95': '95% range of first_agree_unexposed_pct, resampling papers (2,000 draws, fixed seed): '
                                  'values of one paper are correlated, so report it with the headline.',
    'catlog_value_wrong': 'Failures: values where the paper shows CatLog\'s kcat, Km or kcat/Km number or unit was wrong, '
                          'found through this comparison (an approved value checked against the paper, or a value a '
                          'reviewer rejected that an AI audit then dropped), whether or not fixed since. Labels, '
                          'annotations, rounding and values nobody can check are not failures.',
    'differ': 'Approved values CatLog does not match: it holds another value or label, lacks the value or left it out '
              '(values_approved minus agree). The differ_ fields split them by CatLog\'s own check against the paper, '
              'not by the reviewers.',
    'differ_catlog_right': 'Differences where the paper shows that CatLog is right: differ_earlier_value_error plus '
                           'differ_earlier_label_error.',
    'differ_earlier_value_error': 'The approved value is not printed in the paper; CatLog has the printed one, or none.',
    'differ_earlier_label_error': "The same printed value, which CatLog's earlier version gave the wrong enzyme, organism, "
                                  "substrate, variant, UniProt entry or structure; CatLog's label is the paper's.",
    'differ_same_value_other_name': 'The same printed value under a name both use correctly (a synonym, an abbreviation, a '
                                    'renamed organism or a merged UniProt entry) that the automatic match does not join.',
    'differ_rounding': "The same printed value, which CatLog's earlier version rounded by more than the 2% match allows.",
    'differ_catlog_wrong': "Differences where the paper shows that CatLog is wrong: its value or label, or a value the "
                           "paper prints that CatLog missed by mistake.",
    'differ_not_comparable': 'CatLog left the value out under its reading rules (reprinted from another paper, a label the '
                             'paper prints twice, a Hill-fit value, a cell that contradicts its own row).',
    'differ_not_adjudicated': 'Differences not yet checked against the paper.',
    'stated_values': "Values reviewers named as missing from CatLog's earlier version, on papers CatLog has read.",
    'stated_values_catlog_has': 'Of stated_values, those CatLog has (the same paper, metric, protein, variant and '
                                'substrate, and a value within 2%).',
    'rejected_values': 'Values a reviewer rejected as wrong (the value, unit, evidence, substrate or variant) on papers '
                       'CatLog has read.',
    'rejected_catlog_also_without': 'Of rejected_values, values CatLog did not hold at their first comparison (it agrees with '
                                    'the reviewer).',
    'rejected_catlog_has_same': 'Of rejected_values, values CatLog holds with the same number.',
    'rejected_kept_after_audit': 'Of rejected_catlog_has_same, values an AI audit then re-checked against the paper and kept.',
    'rejected_dropped_after_audit': 'Of rejected_catlog_has_same, values an AI audit then found wrong and dropped (failures).',
    'rejected_changed_since': 'Of rejected_catlog_has_same, values CatLog changed or removed since (a unit fix, a re-read): '
                              'counted as failures.',
    'rejected_cleared_by_paper_check': 'Of rejected_catlog_has_same, values a check against the paper found right without an '
                                       'audit (the reviewer\'s point was a naming one: a spelling or synonym of the same '
                                       'substrate; review decided).',
    'rejected_pending': 'Of rejected_catlog_has_same, values neither an AI audit nor a check against the paper has settled.',
    'rejected_not_value': 'Reviewer rejections on those papers that dispute no value shown (another value missing, a '
                          'duplicate, the DOI, a naming point): shown, not counted as failures.',
    'direct_records_reviewed': 'Records read by CatLog that reviewers checked directly, in review packs.',
    'direct_values_reviewed': 'Values of those records that reviewers decided on.',
    'direct_values_agree': 'Of direct_values_reviewed, values reviewers approved without objection.',
    'direct_values_disagree': 'Of direct_values_reviewed, values reviewers rejected, or approved with an objection to the '
                              'value, unit, substrate, variant or evidence.',
    'direct_values_other': 'Of direct_values_reviewed, rejections that dispute none of the values shown (another value the '
                           'paper prints, a duplicate, the DOI, another metric).',
    'direct_disagree_wrong_after_audit': 'Of direct_values_disagree, values an AI audit then found wrong and removed.',
    'direct_disagree_audit_pending': 'Of direct_values_disagree, values no AI audit has re-checked yet.',
}


REJECTED_VALUE = ('v2_has_same', 'v2_has_different', 'v2_lacks_rejected')  # a reviewer said this value is wrong
FIRST_COLS = ('key', 'metric', 'pmid', 'status', 'bucket', 'v2_row_id', 'first_compared')


def _first():
    """(decision key, metric) -> its row at the first comparison (FIRST; seeded 2026-10-12 from each paper's first-read
    rows in the git data checkpoints, label errors that comparison found as v2_label_wrong). The first line wins."""
    out = {}
    if FIRST.exists():
        for r in csv.DictReader(open(FIRST), delimiter='\t'):
            out.setdefault((r['key'], r['metric']), r)
    return out


def _record_first(out):
    """Append reviewed values compared for the first time (approved, or rejected as a wrong value): later rereads and
    fixes never change their first bucket, so the website can lead with how CatLog did before any of them."""
    seen, day = _first(), time.strftime('%Y-%m-%d')
    new = [x for x in out if (x['bucket'] in ('agree',) + DIFFER and x['status'] == 'approved' or x['bucket'] in REJECTED_VALUE)
           and (x['key'], x['metric']) not in seen]
    if new:
        _append(FIRST, FIRST_COLS, [(x['key'], x['metric'], x['pmid'], x['status'], x['bucket'], x.get('v2_row_id', ''), day)
                                    for x in new])


def _append(path, head, rows):
    """Append rows in ONE write, so two processes recording at once never interleave half lines."""
    import io
    buf = io.StringIO()
    w = csv.writer(buf, delimiter='\t', lineterminator='\n')
    if not path.exists():
        w.writerow(head)
    w.writerows(rows)
    with open(path, 'a', newline='') as fh:
        fh.write(buf.getvalue())


# CatLog reads blind (prompts/read.md, verify.md): its reading agents never see database values, the earlier catalog
# or the reviewers' verdicts. blind_check() finds any that did, from the agent transcripts, so agreement can set them apart.
# A reading agent is known by its task (the first message names prompts/read.md or prompts/verify.md, or it is a
# completeness audit), not by its label: chats label them freely ('Read paper 15930043 (retry)'), and checking agents
# of other jobs ('verify:<pmid>' in a database-comparison workflow) are not readers.
READ_TASK = re.compile(r'prompts/(?:read|verify)\.md for (?:PMID|paper\b[^\n]{0,90}?\))\s*(\d{1,9}|NP[0-9A-F]{8})')
AUDIT_ID = re.compile(r'(?i)\bcomplet\w*\b\D{0,20}?(\d{4,9}|NP[0-9A-F]{8})')
FORBIDDEN = re.compile(
    r'db_values\.tsv|db_unmatched|brenda_unmatched|database_corrections|catlog_wide|'  # database values
    r'work/(?:old/)?dbcheck|dbcheck_(?:\d{1,9}|NP[0-9A-F]{8})\b|'  # dbdiff's task files name database numbers, also once recorded
    r'sources/(?:brenda|sabio|skid|strenda|oed|uniprot_values)\w*|sabio_rk_entries|brenda_2026|oed_export|uniprot_kinetics|'
    r'/packages/[^/"\s]+/(?!evidence_assets\b)[\w.-]+\.(?:json|csv|md|tsv)|expected_rows\.json|source_extract\.md|verdicts\.(?:json|csv)|'
    r'v8_(?:accepted|task)\.json|wave1\d_records|_records\.json|_accepted\.json|browser_assist_task|verified_catlog|'
    r'catlog-table|catlog-static|realkcat/output/|'  # the earlier catalog
    r'database_compare\.json|site_build/|catlog-enriched|catlog-database-comparison|details-\d+\.|site_patches/|'  # comparisons
    r'\bhuman_review(?:/|\b(?!\.py))|'  # the review folder, also without its slash (not the module human_review.py)
    r'decisions\.jsonl|compare\.tsv|unmatched_20\d+|old_pack|first_compare|exposed\.tsv')  # review data
EXPOSED_COLS = ('pmid', 'agent', 'file', 'time')
# A name that only leaves a file out opens nothing: readers write `find ... | grep -v -E "db_unmatched|catlog_wide"`
# precisely to keep those files out of view (33431826's reader, 2026-10-26). _named() sets such names aside, and only
# where it is sure: a command with an option it does not know, a quoted $(...) or a double negation counts whole.
FIND_TESTS = {'-path', '-ipath', '-name', '-iname', '-wholename', '-iwholename', '-regex', '-iregex'}
NEGATE, PRUNE = ('-not', '!'), (['-prune', '-o'], ['-prune', '-or'])  # find: -not/! TEST X; TEST X -prune -o (not without -o)
GREPS = {'grep': 'grep', 'egrep': 'grep', 'fgrep': 'grep', 'zgrep': 'grep', 'ugrep': 'grep', 'rg': 'rg'}
# short options (taking a value, taking none) that mean the same in GNU grep, BSD grep and ugrep (the grep of Claude
# Code's shell), and in rg; any other letter may take a value or a file, so that command is left whole
GREP_SHORT = {'grep': ('ABCDdefgm', 'EFGHILPRSTUZabchilnopqrsuvwxyz0123456789'),
              'rg': ('ABCEMTdefgjmrt', 'FHILNPSUVabchilnopqsuvwxz0.')}
GREP_LONG = {'regexp', 'file', 'glob', 'iglob', 'exclude', 'exclude-dir', 'include', 'max-count', 'after-context',
             'before-context', 'type', 'type-not', 'label', 'devices', 'directories', 'max-depth', 'threads', 'encoding',
             'replace', 'max-columns'}  # take a value
GREP_FLAGS = {'invert-match', 'extended-regexp', 'fixed-strings', 'basic-regexp', 'perl-regexp', 'ignore-case',
              'no-ignore-case', 'smart-case', 'case-sensitive', 'word-regexp', 'line-regexp', 'count', 'files-with-matches',
              'files-without-match', 'line-number', 'no-line-number', 'no-filename', 'with-filename', 'only-matching',
              'quiet', 'silent', 'recursive', 'dereference-recursive', 'text', 'null', 'null-data', 'byte-offset',
              'binary', 'no-messages', 'color', 'colour', 'hidden', 'no-ignore', 'follow', 'heading', 'no-heading',
              'initial-tab', 'line-buffered'}  # take none
SHORT_LONG = {'e': 'regexp', 'f': 'file', 'g': 'glob'}
SHELL_PUNCT = '();<>|&\n'
RUNS = re.compile(r'\$\(|`|[<>]\(')  # a command substitution in a word runs that command: never set aside


def _glob_parts(glob):
    """A glob list as rg's callers split it: on spaces, then on commas outside braces (ugrep -g, the Grep tool)."""
    return [p for piece in glob.split() for p in ([piece] if '{' in piece else piece.split(',')) if p]


def _find_exclusions(args, drop):
    """find: the value of a test negated by -not or !, or of a test or group pruned by -prune -o."""
    a, groups = [t for _, t in args], 0
    for k, w in enumerate(a):  # a negation inside a group or right after another reads more than one way
        if w in NEGATE and (groups or k and a[k - 1] in NEGATE):
            return
        groups += (w == '(') - (w == ')' and groups > 0)
    for k, w in enumerate(a):
        if w in FIND_TESTS and k + 1 < len(a) and (k > 0 and a[k - 1] in NEGATE) != (a[k + 2:k + 4] in PRUNE):
            drop.add(args[k + 1][0])
        elif w == '(':
            depth, end = 0, k
            for end in range(k, len(a)):
                depth += (a[end] == '(') - (a[end] == ')')
                if not depth:
                    break
            if not depth and (k > 0 and a[k - 1] in NEGATE) != (a[end + 1:end + 3] in PRUNE):
                drop.update(args[j + 1][0] for j in range(k, end) if a[j] in FIND_TESTS)


def _grep_exclusions(kind, args, drop):
    """grep or rg: the values of --exclude, --exclude-dir and of globs that only exclude, and with -v its patterns
    (the -e values, else the first operand). Nothing at all when an option is not known."""
    takes, flags = GREP_SHORT[kind]
    inverted, patterns, operands, pattern_file, out, k = False, [], [], False, [], 0
    while k < len(args):
        i, w = args[k]
        opt = value = None  # value: the (index, text) an option takes
        if w == '--':  # the rest are operands
            operands += [j for j, _ in args[k + 1:]]
            break
        if w.startswith('--'):
            opt, eq, val = w[2:].partition('=')
            if opt not in GREP_LONG and opt not in GREP_FLAGS:
                return
            inverted |= opt == 'invert-match'
            if opt in GREP_LONG:
                value = (i, val) if eq else args[k + 1] if k + 1 < len(args) else None
                k += not eq
        elif w.startswith('-') and len(w) > 1:
            for j, ch in enumerate(w[1:], 1):
                if ch not in takes and ch not in flags:
                    return
                inverted |= ch == 'v'
                if ch in takes:
                    opt = SHORT_LONG.get(ch, ch)
                    value = (i, w[j + 1:]) if j < len(w) - 1 else args[k + 1] if k + 1 < len(args) else None
                    k += j == len(w) - 1
                    break
        else:
            operands.append(i)
        k += 1
        if value is None:
            continue
        if opt == 'regexp':
            patterns.append(value[0])
        pattern_file |= opt == 'file'
        if opt in ('exclude', 'exclude-dir') or opt in ('glob', 'iglob') and _glob_parts(value[1]) and all(
                p.startswith('!') for p in _glob_parts(value[1])):
            out.append(value[0])
    drop.update(out)
    if inverted:
        drop.update(patterns)
        if not patterns and not pattern_file and operands:
            drop.add(operands[0])


def _exclusions(seg, drop):
    """Add to `drop` the indexes of the words of one shell command (`seg`: (index, word) pairs) that only name what
    it leaves out: find's and grep's (above), else the values of --exclude and --exclude-dir (tar, rsync, du)."""
    words = [t for _, t in seg]
    names = [w.rsplit('/', 1)[-1] for w in words]
    prog = next((k for k, n in enumerate(names) if n in GREPS or n == 'find'), None)
    if prog is not None:
        if names[prog] == 'find':
            _find_exclusions(seg[prog + 1:], drop)
        else:
            _grep_exclusions(GREPS[names[prog]], seg[prog + 1:], drop)
        return
    for k, w in enumerate(words):
        if w == '--':
            break
        if k and words[k - 1] in ('-e', '--regexp'):
            continue
        if re.match(r'--exclude(?:-dir)?=', w):
            drop.add(seg[k][0])
        elif w in ('--exclude', '--exclude-dir') and k + 1 < len(words):
            drop.add(seg[k + 1][0])


def _named(call):
    """The text of one tool call in which a file can be named to be opened: a shell command less what only names a file
    to leave it out (_exclusions) and less its description (a label, it opens nothing); a Grep call less the '!' parts
    of its glob; any other tool's input as it is. A command shlex cannot read as the shell would (an unclosed quote,
    $'...' quoting) counts whole."""
    import shlex
    inp = call.get('input')
    if not isinstance(inp, dict):
        return json.dumps(inp)
    if not isinstance(inp.get('command'), str):
        if isinstance(inp.get('glob'), str):  # the Grep tool passes each part of its glob to rg as a --glob
            inp = {**inp, 'glob': ' '.join(p for p in _glob_parts(inp['glob']) if not p.startswith('!'))}
        return json.dumps(inp)
    cmd, rest = inp['command'], json.dumps({k: v for k, v in inp.items() if k not in ('command', 'description')})
    try:
        if "$'" in cmd:
            raise ValueError
        lex = shlex.shlex(cmd.replace('\\\n', ' '), posix=True, punctuation_chars=SHELL_PUNCT)
        lex.whitespace, lex.whitespace_split, lex.commenters = ' \t\r', True, ''
        toks = list(lex)
    except ValueError:
        return cmd + ' ' + rest
    drop, seg = set(), []
    for i, t in enumerate(toks + [';']):  # a new command after | ; & && || or a line break, not after a redirection
        if t and set(t) <= set(SHELL_PUNCT) and (t in ('&', '&&') or set(t) & set('|;\n')):
            _exclusions(seg, drop)
            seg = []
        else:
            seg.append((i, t))
    return ' '.join(t for i, t in enumerate(toks) if i not in drop or RUNS.search(t)) + ' ' + rest


def _first_task(tr):
    """An agent's task: its user messages up to its first answer (a workflow agent gets the harness's relay of the
    user request first and the task second)."""
    out = []
    with open(tr, errors='replace') as fh:
        for line in fh:
            try:
                m = json.loads(line).get('message') or {}
            except ValueError:
                continue
            if m.get('role') == 'assistant':
                break
            if m.get('role') == 'user':
                c = m.get('content')
                out.append(c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c or [] if isinstance(x, dict)))
    return '\n'.join(out)


def blind_check(full=False):
    """Scan agent transcripts written since the last scan for a reading agent's tool call that names a forbidden file;
    add (pmid, agent, file, local time) lines to EXPOSED. full=True rescans every transcript there is and adds what is
    missing; it never drops a line (transcripts are deleted after 30 days or in a cleanup; EXPOSED is the record).
    Returns the new lines."""
    state = HR / 'exposed.scan'
    rebuild = not EXPOSED.exists() or 'time' not in open(EXPOSED).readline()  # a missing file or the old format only
    since = 0.0 if full or rebuild or not state.exists() else float(state.read_text() or 0)
    start = time.time()
    seen = set() if rebuild else {(r['pmid'], r['agent'], r['file']) for r in csv.DictReader(open(EXPOSED), delimiter='\t')}
    new = []
    for meta in (Path.home() / '.claude' / 'projects').glob('*/*/subagents/**/agent-*.meta.json'):
        tr = meta.with_name(meta.name[:-len('.meta.json')] + '.jsonl')
        try:
            if tr.stat().st_mtime < since:
                continue
            agent = json.loads(meta.read_text()).get('description', '')
        except (OSError, ValueError):
            continue
        task = _first_task(tr)
        m = READ_TASK.search(task) or AUDIT_ID.search(agent)
        if not m:
            continue
        pmid = m.group(1)
        with open(tr, errors='replace') as fh:
            for line in fh:
                if '"tool_use"' not in line or not FORBIDDEN.search(line):
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                when = ''
                if d.get('timestamp'):
                    from datetime import datetime
                    when = datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')).astimezone().strftime('%Y-%m-%d %H:%M')
                for c in (d.get('message') or {}).get('content') or []:
                    if isinstance(c, dict) and c.get('type') == 'tool_use':
                        for f in set(FORBIDDEN.findall(_named(c))):
                            if (pmid, agent, f) not in seen:
                                seen.add((pmid, agent, f))
                                new.append((pmid, agent, f, when))
    if rebuild:
        import io
        buf = io.StringIO()
        csv.writer(buf, delimiter='\t', lineterminator='\n').writerows([EXPOSED_COLS] + sorted(new))
        tmp = EXPOSED.with_suffix('.tsv.tmp')
        tmp.write_text(buf.getvalue())
        tmp.replace(EXPOSED)
    elif new:
        _append(EXPOSED, EXPOSED_COLS, new)
    state.write_text(str(start))
    return new


def _exposed(pmids=None):
    """Papers a reading agent read with a forbidden file open BEFORE the paper's first add (its first comparison comes
    right after): a later re-read or completeness audit is a fix, not the read that was compared."""
    if not EXPOSED.exists():
        return set()
    first_add = {}
    try:
        import catlog
        for f in catlog.events():
            if f[2] == 'add' and f[1] not in first_add:
                first_add[f[1]] = f[0]
    except Exception:
        pass
    out = set()
    for r in csv.DictReader(open(EXPOSED), delimiter='\t'):
        if pmids is not None and r['pmid'] not in pmids:
            continue
        t, added = r.get('time') or '', first_add.get(r['pmid'])
        if not added or not t or t <= added:
            out.add(r['pmid'])
    return out


BLIND_REREAD = re.compile(r'blind re-(read|verify)\b', re.I)  # catlog.py reread's reason for a paper sent back blind


def _exposure(pmids=None):
    """Every paper whose reading or checking agent opened database values or files of CatLog's earlier version
    (EXPOSED, whenever it happened; _exposed() keeps only the read before the first add), by who did (item 1 of
    work/publication_strategy_20261021/FIXES_FOR_MAIN_CHAT.md): reader (the reading agent, perhaps a checking agent
    too) or checker_only (only the verifier, its missed-value check or a completeness check); first and last: the
    days the log spans. reread_blind: the papers sent back to be read again blind (log.tsv `reread` "blind re-read: ..."
    with a fresh read, "blind re-verify: ..." with the read kept), reread_blind_read / _verify of them, reread_blind_on
    the day of the first such line and reread_blind_done those added again since. {} without the log."""
    if not EXPOSED.exists():
        return {}
    who, days = {}, []
    for r in csv.DictReader(open(EXPOSED), delimiter='\t'):
        if pmids is not None and r['pmid'] not in pmids:
            continue
        label = (r.get('agent') or '').strip().lower()
        checker = label.startswith(('verify', 'complet'))  # an unknown label counts as a reader (the worse case)
        who[r['pmid']] = who.get(r['pmid'], True) and checker
        if re.match(r'\d{4}-\d{2}-\d{2}', r.get('time') or ''):
            days.append(r['time'][:10])
    out = {'papers': len(who), 'reader': sum(1 for c in who.values() if not c),
           'checker_only': sum(1 for c in who.values() if c)}
    if days:
        out.update({'first': min(days), 'last': max(days)})
    try:
        import catlog
        evs = catlog.events()
    except Exception:
        evs = []
    sent, added = {}, {}
    for f in evs:
        if f[2] == 'reread' and len(f) > 3 and (m := BLIND_REREAD.match(f[3])) and f[1] not in sent:
            sent[f[1]] = (f[0], m.group(1).lower())
        elif f[2] == 'add' and f[1] in sent and f[0] >= sent[f[1]][0]:
            added[f[1]] = f[0]
    if sent:
        out.update({'reread_blind': len(sent), 'reread_blind_read': sum(1 for _, k in sent.values() if k == 'read'),
                    'reread_blind_verify': sum(1 for _, k in sent.values() if k == 'verify'),
                    'reread_blind_on': min(t for t, _ in sent.values())[:10], 'reread_blind_done': len(added)})
    return out


def _adjudications():
    """CatLog's check against the paper of every approved value it did not match (human_review/unmatched_*.tsv; the first
    file that has a value decides), per (decision key, metric)."""
    pc = {}
    for f in sorted(HR.glob('unmatched_*.tsv')):
        for r in csv.DictReader(open(f), delimiter='\t'):
            pc.setdefault((r['key'], r['metric']), r)
    return pc


def _differ_class(p):
    """One difference as an agreement field (AGREEMENT_DEFINITIONS), from its check against the paper (None: not yet)."""
    if p is None:
        return 'differ_not_adjudicated'
    if p.get('v2_value_wrong') == 'True' or (p['verdict'] == 'matching_problem' and p['right_label'] == 'old'):
        return 'differ_catlog_wrong'
    if p['verdict'] == 'v2_missed' and not DELIBERATE.search(p.get('cause') or ''):
        return 'differ_catlog_wrong'  # a printed value CatLog missed by mistake, not one its reading rules leave out
    if p['verdict'] == 'old_value_not_in_paper':
        return 'differ_earlier_value_error'
    if p['verdict'] == 'matching_problem' and p['right_label'] == 'v2':
        return 'differ_earlier_label_error'
    if re.search(r'\bround', p.get('cause') or '', re.I):
        return 'differ_rounding'
    if p['verdict'] == 'matching_problem':  # both labels right
        return 'differ_same_value_other_name'
    return 'differ_not_comparable'  # v2_missed, v2_rejected_it: left out on purpose (the cause says why)


def _first_errors(appr, pc, fb):
    """first_catlog_errors and its split, fixed_after_comparison and matched_later_other (AGREEMENT_DEFINITIONS)."""
    kind = {(x['key'], x['metric']): _what_fixed(pc.get((x['key'], x['metric']))) for x in appr}
    err = [x for x in appr if kind[(x['key'], x['metric'])]]
    k = Counter('value' if kind[(x['key'], x['metric'])] == 'the value' else 'missed' if 'missed' in kind[(x['key'], x['metric'])]
                else 'label' for x in err)
    later = [x for x in appr if x['bucket'] == 'agree' and fb(x) != 'agree']
    return {'first_catlog_errors': len(err), 'first_catlog_errors_value': k['value'], 'first_catlog_errors_label': k['label'],
            'first_catlog_errors_missed': k['missed'], 'fixed_after_comparison': sum(1 for x in err if x['bucket'] == 'agree'),
            'matched_later_other': sum(1 for x in later if not kind[(x['key'], x['metric'])])}


def agreement(rows, out, s):
    """How often human reviewers and CatLog agree (user, 2026-10-12: the human review is CatLog's solid check and a
    measure of its success). The 2026 review of the earlier catalog: the values reviewers approved on papers CatLog has
    since read, against CatLog's values (compare's buckets), the differences split by CatLog's check against the paper
    (unmatched_*.tsv). Direct review: CatLog's own records in review packs. Fields: AGREEMENT_DEFINITIONS."""
    b = Counter(x['bucket'] for x in out)
    appr = [x for x in out if x['status'] == 'approved' and x['bucket'] in ('agree',) + DIFFER]
    pc = _adjudications()
    split = Counter(_differ_class(pc.get((x['key'], x['metric']))) for x in appr if x['bucket'] != 'agree')
    direct = [x for x in out if x['bucket'].startswith('reviewed_in_v2') or x['bucket'] == 'v2_approved_with_objection']
    disagree = [x for x in direct if x['bucket'] == 'v2_approved_with_objection'
                or (x['bucket'] == 'reviewed_in_v2' and x['status'] == 'rejected')]
    try:
        import catlog
        evs = list(catlog.events())
        ev = {f[3]: f[2] for f in evs if f[2] in ('audit_keep', 'audit_drop') and len(f) > 3}  # latest verdict
        lab = catlog.relabelled_drops(evs)  # dropped for the organism label, back under the right one: not wrong
        ev = {k: 'audit_relabel' if v == 'audit_drop' and k in lab else v for k, v in ev.items()}
        decided = {f[3] for f in evs if f[2] == 'review_decided' and len(f) > 3}  # judged against the paper (Guideline)
    except Exception:
        ev, decided = {}, set()
    first = _first()
    fb = lambda x: (first.get((x['key'], x['metric'])) or {}).get('bucket', x['bucket'])  # not yet recorded: this is its first
    fa = sum(1 for x in appr if fb(x) == 'agree')
    exp = _exposed({x['pmid'] for x in appr})
    clean = [x for x in appr if x['pmid'] not in exp]
    # reviewer rejections, from their FIRST comparison (a later unit fix or drop is the fate of a value CatLog held)
    # the value CatLog holds, never a number the reviewer wrote for the same metric (stated_*: 21048316, 2026-11-07)
    cur = {(x['key'], x['metric']): x for x in out if not x['bucket'].startswith('stated_')}
    rv = {k: r for k, r in first.items() if r.get('status') == 'rejected'}
    rv.update({(x['key'], x['metric']): {'bucket': x['bucket'], 'v2_row_id': x.get('v2_row_id', '')} for x in out
               if x['bucket'] in REJECTED_VALUE and (x['key'], x['metric']) not in rv})
    same = {k: r for k, r in rv.items() if r['bucket'] == 'v2_has_same'}

    def fate(k, r):
        rid, now = r.get('v2_row_id'), cur.get(k) or {}
        if ev.get(rid) == 'audit_drop':
            return 'dropped'
        if now.get('bucket') != 'v2_has_same':
            return 'changed'  # CatLog changed or removed the value since (a unit fix keeps the row id)
        return 'kept' if ev.get(rid) == 'audit_keep' else 'cleared' if rid in decided else 'pending'
    fates = Counter(fate(k, r) for k, r in same.items())
    pct = lambda n, d: round(100 * n / d, 1) if d else None
    import random  # the headline's 95% range: resample papers (values of one paper are not independent), fixed seed
    byp = defaultdict(lambda: [0, 0])
    for x in clean:
        byp[x['pmid']][0] += fb(x) == 'agree'
        byp[x['pmid']][1] += 1
    papers, rng, boot = list(byp.values()), random.Random(20261012), []
    for _ in range(2000 if papers else 0):
        smp = [papers[rng.randrange(len(papers))] for _ in papers]
        boot.append(100 * sum(a for a, _ in smp) / max(1, sum(n for _, n in smp)))
    boot.sort()
    a = {'papers_compared': s['papers_read_by_v2'], 'values_approved': len(appr),
         'first_agree': fa, 'first_agree_pct': pct(fa, len(appr)), 'agree': b['agree'],
         'agree_pct': pct(b['agree'], len(appr)),
         **_first_errors(appr, pc, fb),
         'papers_exposed': len(exp), 'first_agree_unexposed_pct': pct(sum(1 for x in clean if fb(x) == 'agree'), len(clean)),
         'papers_unexposed': len(papers),
         'first_agree_unexposed_ci95': f'{boot[49]:.1f}-{boot[1949]:.1f}' if boot else None,
         'catlog_value_wrong': sum(1 for p in pc.values() if p.get('v2_value_wrong') == 'True') + fates['dropped'] + fates['changed'],
         'differ': len(appr) - b['agree'],
         'differ_catlog_right': split['differ_earlier_value_error'] + split['differ_earlier_label_error'],
         **{k: split[k] for k in AGREEMENT_DEFINITIONS if k.startswith('differ_') and k != 'differ_catlog_right'},
         'stated_values': b['stated_found'] + b['stated_missing'], 'stated_values_catlog_has': b['stated_found'],
         'rejected_values': len(rv),
         'rejected_catlog_also_without': len(rv) - len(same),
         'rejected_catlog_has_same': len(same),
         'rejected_kept_after_audit': fates['kept'], 'rejected_changed_since': fates['changed'],
         'rejected_dropped_after_audit': fates['dropped'], 'rejected_cleared_by_paper_check': fates['cleared'],
         'rejected_pending': fates['pending'],
         'rejected_not_value': sum(1 for x in out if x['bucket'] == 'row_objection'),
         'direct_records_reviewed': sum(1 for r in rows if r.get('v2_pack')), 'direct_values_reviewed': len(direct),
         'direct_values_agree': sum(1 for x in direct if x['bucket'] == 'reviewed_in_v2' and x['status'] == 'approved'),
         'direct_values_disagree': len(disagree)}
    a['direct_values_other'] = len(direct) - a['direct_values_agree'] - len(disagree)
    a['direct_disagree_wrong_after_audit'] = sum(1 for x in disagree if ev.get(x.get('v2_row_id')) == 'audit_drop')
    a['direct_disagree_audit_pending'] = sum(1 for x in disagree if x.get('v2_row_id') not in ev)
    assert set(a) == set(AGREEMENT_DEFINITIONS), set(a) ^ set(AGREEMENT_DEFINITIONS)
    return {**a, 'definitions': AGREEMENT_DEFINITIONS}


def agreement_text(a, as_of=''):
    """The agreement block of `review stats`: every field of the website's quality.agreement, with its number."""
    if not a.get('values_approved'):
        return 'Agreement with human reviewers: no paper of the review read by CatLog yet'
    show = lambda k: 'n/a' if a[k] is None else a[k] if isinstance(a[k], str) else f"{a[k]:,}" + (  # a range is text
        f" ({100 * a[k] / a['differ']:.0f}% of differ)" if k.startswith('differ_') and a['differ']
        else f" ({a[k + '_pct']:.1f}%)" if k in ('agree', 'first_agree') and a[k + '_pct'] is not None else '')
    lines = [f"Agreement with human reviewers{f' (as of {as_of})' if as_of else ''} (website: quality.agreement)"]
    for k, d in AGREEMENT_DEFINITIONS.items():
        if not k.endswith('agree_pct'):
            pad = '    ' if k.startswith(('differ_', 'direct_values_', 'direct_disagree', 'stated_values_', 'rejected_')) \
            and k != 'rejected_values' else '  '
            lines.append(f'{pad}{k}: {show(k)} · {d}')
    return '\n'.join(lines)


def accuracy(rows, out):
    """Accuracy of kinetic values from human review, the user's definition (2026-10-11): wrong = the number or its unit
    is wrong for that measurement. Not counted as wrong, each in a line of its own: values nobody could assess (no paper
    linked, reviewer could not find the value), rounding only, conditions (pH, temperature), identity labels (enzyme,
    organism, substrate, variant), annotations (UniProt, sequence, structure), record keeping (another value the paper
    also prints, duplicates, DOI). Sources: the reviewers' decisions, and CatLog's own check against the papers of every
    value reviewers approved that v2 did not match (human_review/unmatched_*.tsv). Values: kcat, Km and a printed
    kcat/Km (one the earlier pipeline computed from kcat and Km is left out). CatLog v2's own entries (v2 review packs,
    2026-10-15): v2_values_reviewed, v2_wrong_confirmed, v2_disputed_pending and v2_accuracy are the plain random
    sample's (_is_random, as review_summary), v2_accuracy_basis 'random sample', or 'all entries' while no random entry
    is reviewed yet; the values of entries picked on purpose as hard cases are counted apart (the same keys + '_picked')."""
    vals = lambda r: [m for m in ('kcat', 'Km', 'kcat/Km') if r.get(m) is not None and not (m == 'kcat/Km' and r.get('kcat/Km_derived'))]
    v1 = [r for r in rows if not r.get('v2_pack')]
    checked = [r for r in v1 if r.get('checkable')]
    pc = _adjudications()
    read = {x['pmid'] for x in out if x['pmid'] and x['bucket'] not in ('paper_not_read', 'derived', 'v2_approved_with_objection',
            'v2_reviewer_stated', 'v2_changed_since_review') and not x['bucket'].startswith('reviewed_in_v2')}  # as summary()
    both = [r for r in checked if r['pmid'] in read]  # reviewed AND re-checked against the paper by CatLog
    n_both = sum(len(vals(r)) for r in both)
    reviewer_wrong = [(r['key'], m) for r in checked if r['status'] == 'rejected' and r.get('category') in VALUE_CATS
                      and r['pmid'] not in CLEARED for m in vals(r)]
    paper_wrong = [k for k, x in pc.items() if x['verdict'] == 'old_value_not_in_paper']
    wrong_both = len({k for k in reviewer_wrong if any(r['key'] == k[0] for r in both)} | set(paper_wrong))
    what = lambda x: ('annotation' if re.search(r'uniprot|accession|smiles|structure', x['cause'], re.I) else 'label')
    v1_label = [x for x in pc.values() if x['verdict'] == 'matching_problem' and x['right_label'] == 'v2']
    v2_label = [x for x in pc.values() if x['verdict'] == 'matching_problem' and x['right_label'] == 'old']
    fixed = {(x['key'], x['metric']) for x in out if x['bucket'] == 'agree'}
    differ_now = [x for x in out if x['status'] == 'approved' and x['bucket'] in DIFFER]
    a = {
        'v1_values_reviewed': sum(len(vals(r)) for r in checked), 'v1_papers_reviewed': len({r['pmid'] for r in checked}),
        'v1_wrong_by_reviewers': len(reviewer_wrong),
        'v1_values_both': n_both, 'v1_papers_both': len({r['pmid'] for r in both}), 'v1_wrong_both': wrong_both,
        'v1_accuracy_both': 100 * (1 - wrong_both / n_both) if n_both else None,
        'v2_same_as_approved': sum(1 for x in out if x['bucket'] == 'agree'),
        'v2_wrong_in_differences': sum(1 for x in pc.values() if x.get('v2_value_wrong') == 'True'),
        'differences_checked': len(pc),  # every check on file (unmatched_*.tsv), also of values CatLog matches since
        # the approved values CatLog does not match now (agreement()'s differ) and those of them an AI check of the paper
        # has judged (the rest: differ_not_adjudicated): item 2 of work/publication_strategy_20261021/FIXES_FOR_MAIN_CHAT.md
        'differences_now': len(differ_now),
        'differences_now_checked': sum(1 for x in differ_now if (x['key'], x['metric']) in pc),
        'not_assessable_entries': sum(1 for r in v1 if not r.get('checkable')),
        'not_found_by_reviewer': sum(1 for r in v1 if r['status'] == 'rejected' and r.get('category') == 'no_literature'),
        'rounding_values': sum(1 for x in pc.values() if 'round' in x['cause'].lower())
                           + sum(len(vals(r)) for r in checked if r['status'] == 'rejected' and CLEARED.get(r['pmid']) == 'rounding'),
        'conditions_entries': sum(1 for r in rows if r['status'] == 'rejected' and r.get('category') == 'conditions'),
        'v1_label_flags_by_reviewers': sum(1 for r in checked if r['status'] == 'rejected' and r.get('category') in LABEL_CATS),
        'v1_label_values_paper_check': sum(1 for x in v1_label if what(x) == 'label'),
        'v1_annotation_values_paper_check': sum(1 for x in v1_label if what(x) == 'annotation'),
        'v2_label_values_paper_check': sum(1 for x in v2_label if what(x) == 'label'),
        'v2_annotation_values_paper_check': sum(1 for x in v2_label if what(x) == 'annotation'),
        'v2_label_or_annotation_fixed': sum(1 for x in v2_label if (x['key'], x['metric']) in fixed),
        'record_keeping_entries': Counter(r.get('category') for r in v1 if r['status'] == 'rejected'
                                          and r.get('category') in ('missing_value', 'duplicate', 'doi')),
    }
    v2 = [r for r in rows if r.get('v2_pack')]  # CatLog v2's own entries, reviewed in v2 packs
    try:
        import catlog
        evs = catlog.events()
        lab = catlog.relabelled_drops(evs)  # dropped for the organism label, back under the right one: not wrong
        ev = {f[3]: 'audit_relabel' if f[2] == 'audit_drop' and f[3] in lab else f[2]
              for f in evs if f[2] in ('audit_keep', 'audit_drop') and len(f) > 3}
    except Exception:
        ev = {}
    # the % is the plain random sample's, as review_summary's (2026-10-15): entries picked on purpose as hard cases
    # are counted apart (_picked keys); every v2 entry while no random entry is reviewed yet (v2_accuracy_basis)
    rand = {r['key'] for r in v2 if _is_random(r)}
    picked = {r['key'] for r in v2 if not _is_random(r)}
    lines = [x for x in out if x['bucket'].startswith('reviewed_in_v2')]

    def count(keys, sfx=''):
        mine = [x for x in lines if keys is None or x['key'] in keys]
        rej = [x for x in mine if x['bucket'] == 'reviewed_in_v2' and x['status'] == 'rejected' and x.get('category') in VALUE_CATS]
        a.update({f'v2_values_reviewed{sfx}': len(mine),
                  f'v2_wrong_confirmed{sfx}': sum(1 for x in rej if ev.get(x.get('v2_row_id')) == 'audit_drop'),
                  f'v2_disputed_pending{sfx}': sum(1 for x in rej if x.get('v2_row_id') not in ev)})
    count(rand or None)
    count(picked, '_picked')
    a.update({'v2_entries_reviewed': len(v2), 'v2_entries_random': len(rand), 'v2_entries_picked': len(picked),
              'v2_accuracy_basis': 'random sample' if rand else 'all entries'})
    if v2 and all(_pack_free_only(r['v2_pack']) for r in v2 if not rand or r['key'] in rand):
        a['v2_accuracy_scope'] = 'papers free to read'
    n2 = a['v2_values_reviewed']
    a['v2_accuracy'] = 100 * (1 - a['v2_wrong_confirmed'] / n2) if n2 else None
    return a


def accuracy_text(a):
    rk = a['record_keeping_entries']
    pend = lambda n: f" ({n} disputed, audit pending)" if n else ''
    rnd = a.get('v2_accuracy_basis') == 'random sample'
    where = ' on papers free to read' if a.get('v2_accuracy_scope') else ''
    if not a.get('v2_entries_reviewed'):
        v2 = "CatLog v2 entries reviewed directly: none returned yet (review packs)"
    elif rnd and a['v2_values_reviewed']:
        v2 = (f"CatLog v2 entries reviewed directly, random sample of {a['v2_values_reviewed']:,} values{where}: "
              f"{a['v2_wrong_confirmed']} wrong after audit → {a['v2_accuracy']:.1f}% accurate" + pend(a['v2_disputed_pending']))
    elif rnd:
        v2 = f"CatLog v2 entries reviewed directly, random sample{where}: no values left to count (the measurements reviewed changed since)"
    elif a['v2_values_reviewed']:
        v2 = (f"CatLog v2 entries reviewed directly, all entries (no random sample reviewed yet){where}: {a['v2_values_reviewed']:,} "
              f"values, {a['v2_wrong_confirmed']} wrong after audit → {a['v2_accuracy']:.1f}% accurate" + pend(a['v2_disputed_pending']))
    else:
        v2 = "CatLog v2 entries reviewed directly: no values left to count (the measurements reviewed changed since)"
    if rnd and a.get('v2_values_reviewed_picked'):  # the hard cases, never in the % above
        v2 += (f"\n  CatLog v2 entries picked on purpose as hard cases (not in the % above): {a['v2_values_reviewed_picked']:,} values, "
               f"{a['v2_wrong_confirmed_picked']} wrong after audit" + pend(a['v2_disputed_pending_picked']))
    return '\n'.join([
        "Accuracy of kinetic values from human review (wrong = the number or its unit is wrong for that measurement)",
        f"  CatLog v1 entries: {a['v1_accuracy_both']:.1f}% accurate · {a['v1_wrong_both']} wrong of {a['v1_values_both']:,} values on the "
        f"{a['v1_papers_both']} papers that reviewers checked and CatLog re-checked against the paper (reviewers alone: "
        f"{a['v1_wrong_by_reviewers']} wrong in {a['v1_values_reviewed']:,} values on {a['v1_papers_reviewed']} papers)"
        if a['v1_accuracy_both'] is not None else
        f"  CatLog v1 entries: reviewers found {a['v1_wrong_by_reviewers']} wrong in {a['v1_values_reviewed']:,} values",
        f"  CatLog v2 entries: {a['v2_same_as_approved']:,} values the same as values reviewers approved; of the "
        f"{a['differences_now']:,} approved values it does not match, AI agents checked {a['differences_now_checked']:,} against "
        f"the paper and {a['differences_now'] - a['differences_now_checked']:,} are not yet checked; CatLog values found "
        f"wrong in the {a['differences_checked']} checks on file: {a['v2_wrong_in_differences']}",
        f"  {v2}",
        "Acknowledged separately (not counted as wrong):",
        f"  not assessable: {a['not_assessable_entries']} entries without a paper ({a['not_found_by_reviewer']} 'could not find the value')",
        f"  rounding only: {a['rounding_values']} values",
        f"  conditions (pH, temperature): {a['conditions_entries']} entries flagged",
        f"  identity and annotations (enzyme, organism, substrate, variant, UniProt, sequence, structure): reviewers flagged "
        f"{a['v1_label_flags_by_reviewers']} v1 entries (all synonyms or old names); CatLog's paper check found "
        f"{a['v1_label_values_paper_check'] + a['v1_annotation_values_paper_check']} v1 values under a wrong label and "
        f"{a['v2_label_values_paper_check'] + a['v2_annotation_values_paper_check']} v2 values with a wrong label or annotation "
        f"({a['v2_label_or_annotation_fixed']} of them fixed and matching now)",
        f"  record keeping: another value the paper prints {rk.get('missing_value', 0)}, duplicates {rk.get('duplicate', 0)}, "
        f"DOI {rk.get('doi', 0)} entries"])


OTHER_KINDS = {'no_literature': 'could not find the value', 'missing_value': 'another value the paper prints',
               'organism': 'organism name', 'substrate': 'substrate name', 'doi': 'DOI', 'duplicate': 'duplicate',
               'conditions': 'pH or temperature', 'variant': 'variant', 'evidence': 'paper evidence mismatch', 'other': 'other',
               'none': 'no reason given', '': 'no reason given'}


def disputes_value(d):
    """The reviewer says a kcat, Km or kcat/Km number or its unit is wrong for this entry, as the review document says
    it: a rejection for the value or unit ("Value wrong", "Unit wrong"), or an approval carrying "Value wrong". "Paper
    evidence mismatch" was its own button on the page and names no value: another kind of disagreement. Two independent
    recounts of the raw files (2026-10-13) agree: 3 entries."""
    c = (d.get('comment') or '').lower()
    if d['status'] == 'rejected':
        return d.get('category') in ('value', 'unit')
    return d.get('category') in ('value', 'unit') and bool(re.search(r'\bwrong\b', c))


_PACK_FREE = {}


def _pack_free_only(pid):
    """Whether v2 review pack `pid` holds only papers free to read (its index's 'free_only'), read once per pack from
    human_review/packs/<pid>.json or packs/withdrawn/; False when its index is missing (pack 'unknown')."""
    if pid not in _PACK_FREE:
        _PACK_FREE[pid] = False
        for f in (PACKS / f'{pid}.json', PACKS / 'withdrawn' / f'{pid}.json'):
            try:
                _PACK_FREE[pid] = json.loads(f.read_text()).get('free_only') is True
                break
            except (OSError, ValueError, AttributeError):
                continue
    return _PACK_FREE[pid]


_PACK_KIND = {}


def _pack_kinds(pid):
    """(harder? per record key, the catalog's harder share, M of --per-paper or 0, paper_size per key) of v2 pack `pid`,
    read once from its index; ({}, None, 0, {}) when the index has no 'harder' flag (packs built before 2026-10-29) or is
    missing. In a --hard pack a record's kind is who got its paper (the hard name, first or second: a rebuild recomputes
    'harder' from today's catalog but never moves a paper), in another --per-paper pack its paper's (a paper is harder
    when any of its records is); both weigh by catalog_harder_share, the records of harder papers among all eligible
    ones (a --hard pack without it counts as unknown). Otherwise the record's own flag, and the share is the harder share
    of the pack's random records, reviewed or not (those packs drew records, or kept papers, at random)."""
    if pid not in _PACK_KIND:
        f = next((f for f in (PACKS / f'{pid}.json', PACKS / 'withdrawn' / f'{pid}.json') if f.exists()), None)
        idx = json.loads(f.read_text()) if f else {}
        recs, m, hard = idx.get('records') or {}, idx.get('per_paper') or 0, idx.get('hard')
        if not recs or not all('harder' in v for v in recs.values()):
            _PACK_KIND[pid] = ({}, None, 0, {})
            return _PACK_KIND[pid]
        hard_papers = {v['pmid'] for v in recs.values() if v['harder']}
        kind = {k: hard in [v.get('reviewer'), *(v.get('also') or [])] if hard else (v['pmid'] in hard_papers) if m
                else bool(v['harder']) for k, v in recs.items()}
        rand = [kind[k] for k, v in recs.items() if str(v.get('why') or '').startswith('random')]
        share = idx.get('catalog_harder_share') if m or hard else None
        if share is None and not hard:
            share = sum(rand) / len(rand) if rand else None
        _PACK_KIND[pid] = (kind if share is not None else {}, share, m,
                           {k: v['paper_size'] for k, v in recs.items() if v.get('paper_size')} if m else {})
    return _PACK_KIND[pid]


def _difficulty(rand):
    """The reviewed random records weighed by difficulty (the user, 2026-10-28: an unbiased headline when one person
    gets the harder papers, another the easier ones, and only one has finished). Returns ({key: weight}, by_difficulty
    or None, whether --per-paper records were weighed). Each record's kind and the catalog's harder share come from its
    pack index (_pack_kinds; the share over several packs is their mean over these records); records of a pack without
    the flag are of unknown kind and weigh 1. Within a kind, a --per-paper record weighs 1/min(M, its paper's size)
    (records of small papers had a smaller chance), scaled to a mean of 1 per pack. With reviewed records of both kinds
    each kind then counts as its catalog share of them, so the % = (1 - share) x the easier rate + share x the harder
    rate (block() uses the same weights for the missing and other %s); with one kind the % is that kind's rate."""
    known, unknown, groups, by_paper = [], 0, defaultdict(list), False
    for r in rand:
        kind, share, m, size = _pack_kinds(r.get('v2_pack'))
        if r['key'] not in kind:
            unknown += 1
            continue
        by_paper = by_paper or bool(m)
        x = [r, kind[r['key']], 1 / min(m, size.get(r['key']) or m) if m else 1, share]
        known.append(x)
        groups[r.get('v2_pack'), x[1]].append(x)
    if not known:
        return {}, None, False
    for xs in groups.values():  # a mean of 1 per pack and kind: a pack counts as many records as it has
        mean = sum(x[2] for x in xs) / len(xs)
        for x in xs:
            x[2] /= mean
    s = sum(x[3] for x in known) / len(known)
    n = Counter(x[1] for x in known)
    both = n[True] and n[False]
    wt = {x[0]['key']: x[2] * ((s if x[1] else 1 - s) * len(known) / n[x[1]] if both else 1) for x in known}
    rate = lambda h: (round(100 * sum(x[2] for x in known if x[1] == h and not disputes_value(x[0])) / n[h], 1) if n[h] else None)
    diff = {'easier': {'reviewed': n[False], 'correct_pct': rate(False)}, 'harder': {'reviewed': n[True], 'correct_pct': rate(True)},
            'harder_share': round(s, 4), 'basis': ('random sample, weighted by difficulty' if both
                                                   else 'harder records only' if n[True] else 'easier records only'),
            **({'unknown': {'reviewed': unknown}} if unknown else {})}
    return wt, diff, by_paper


def _is_random(r):
    """A v2-pack entry drawn by the plain random sample ('random (proportional)', 'random, balanced (...)'), not picked
    on purpose ('issue: ...' kinds of trouble, 'second opinion: ...', 'important') or of unknown origin."""
    return str(r.get('why') or '').startswith('random')


def review_summary(rows):
    """What the reviewers' own files say (the user, 2026-10-13: the stat reflects the review document, simply): per
    reviewed entry its final verdict; entries where the reviewer disputes a value (disputes_value) against the entries
    reviewed give "values correct"; every other rejection is another kind of disagreement, by kind. Separately for the
    review of CatLog v1 entries and for CatLog v2's own entries (review packs). The value disputes checked against the
    papers since (CLEARED, HUMAN_REVIEW.md Guideline) are counted apart.
    CatLog v2's own entries (2026-10-15): the percentages and the counts behind them (value_*, other_*) come from the
    plain random sample only (_is_random), since pooling the entries picked on purpose as hard cases would bias them;
    those are counted apart (entries_picked, picked_value_disputed, picked_by_kind). 'entries', 'papers', 'approved'
    and 'rejected' stay over every v2 entry. value_correct_basis says which: 'random sample', or 'all entries' (today's
    computation) while no random entry is reviewed yet; scope 'papers free to read' when every entry of that basis comes
    from a free-only pack. The random sample's %s are weighed by difficulty (_difficulty, 2026-10-29): with reviewed
    records of both kinds value_correct_pct is the easier and the harder rate weighed by the catalog's harder share,
    with one kind that kind's rate; value_correct_by_difficulty {easier, harder: {reviewed, correct_pct}, harder_share,
    basis, unknown} says which (value_correct_basis stays 'random sample': the Cloudflare app tests it as is). The v1
    block is unchanged. summary() adds v2 'values': the kcat, Km and kcat/Km values the reviewed v2 entries hold now
    (random and picked; an entry whose measurement changed since holds none).
    An entry has a paper (the headline's base, entries_without_paper) when it has a PMID or a DOI, or comes from a v2 pack
    (every v2 entry was reviewed with its paper open, also one whose measurement a re-read has replaced since). This is
    the headline's own test: ingest's 'checkable' (a PMID only) still gates compare() and accuracy(), where a paper is a
    PMID (the numbers audit, 2026-11-06: 6 approved entries with only a DOI and the v2 entries whose measurement is gone
    had counted as having no paper)."""
    def has_paper(r):
        return bool(r.get('checkable') or r.get('doi') or r.get('v2_pack'))

    def block(group, base, wt=None):
        disputed = [r for r in base if disputes_value(r)]
        missing = [r for r in base if r['status'] == 'rejected' and not disputes_value(r) and r.get('category') == 'missing_value']
        other = [r for r in base if r['status'] == 'rejected' and not disputes_value(r) and r.get('category') != 'missing_value']
        weight = lambda rs: sum((wt or {}).get(r['key'], 1) for r in rs)  # weighed by difficulty (_difficulty)
        pct = lambda rs: round(100 * weight(rs) / weight(base), 1)
        return {'entries': len(group), 'papers': len({r['pmid'] for r in group if r.get('pmid')}),
                'entries_without_paper': sum(1 for r in group if not has_paper(r)),
                'approved': sum(1 for r in group if r['status'] == 'approved'),
                'rejected': sum(1 for r in group if r['status'] == 'rejected'),
                'value_disputed': len(disputed), 'value_correct_pct': pct([r for r in base if not disputes_value(r)]),
                'value_disputed_checked_as_printed': sum(1 for r in disputed if r.get('pmid') in CLEARED),
                'value_disputed_unchecked': sorted({r['pmid'] for r in disputed if r.get('pmid') not in CLEARED}),
                'value_missing': len(missing), 'value_missing_pct': pct(missing),  # the paper prints a value the entry lacks
                'value_missing_named': sum(len(r.get('stated') or []) for r in missing),
                'other_disputed': len(other), 'other_disputed_pct': pct(other),
                'other_by_kind': dict(Counter(OTHER_KINDS.get(r.get('category') or '', r.get('category')) for r in other).most_common())}

    out = {}
    for name, group in (('v1', [r for r in rows if not r.get('v2_pack')]), ('v2', [r for r in rows if r.get('v2_pack')])):
        if not group:
            continue
        rand = [r for r in group if _is_random(r)] if name == 'v2' else group
        base = rand or group  # what the percentages are over
        wt, by_difficulty, by_paper = _difficulty(rand) if name == 'v2' else ({}, None, False)
        out[name] = block(group, base, wt)
        if by_paper:
            out[name]['weighted'] = True  # the %s weigh --per-paper records back to the catalog's mix of papers
        if by_difficulty:
            out[name]['value_correct_by_difficulty'] = by_difficulty
        if name == 'v1' and (checkable := [r for r in group if has_paper(r)]):
            # the same counts over the entries a reviewer could check against a paper (item 4 of
            # work/publication_strategy_20261021/FIXES_FOR_MAIN_CHAT.md): an entry without a PMID or DOI is not
            # assessable, so the share of entries with no value disputed is over these; entries_without_paper above
            # says how many could not be checked
            out[name]['checkable'] = block(checkable, checkable)
        if name == 'v2':
            picked = [r for r in group if not _is_random(r)]
            by_kind = defaultdict(lambda: {'entries': 0, 'value_disputed': 0})
            for r in picked:
                k = by_kind[str(r.get('why') or 'not recorded')]
                k['entries'] += 1
                k['value_disputed'] += disputes_value(r)
            out[name].update({
                'value_correct_basis': 'random sample' if rand else 'all entries',
                'entries_random': len(rand), 'entries_picked': len(picked),
                'picked_value_disputed': sum(1 for r in picked if disputes_value(r)),
                'picked_value_disputed_unchecked': sorted({r['pmid'] for r in picked if disputes_value(r) and r.get('pmid') not in CLEARED}),
                'picked_value_disputed_checked_as_printed': sum(1 for r in picked if disputes_value(r) and r.get('pmid') in CLEARED),
                'picked_by_kind': dict(sorted(by_kind.items(), key=lambda kv: (-kv[1]['value_disputed'], -kv[1]['entries'], kv[0])))})
            if all(_pack_free_only(r['v2_pack']) for r in base):
                out[name]['scope'] = 'papers free to read'
    return out


def _difficulty_text(r):
    """The v2 headline's words on difficulty (value_correct_by_difficulty): both rates and how the % weighs them, or
    the one kind reviewed so far; '' when no reviewed record's pack records difficulty."""
    d = r.get('value_correct_by_difficulty')
    if not d:
        return ''
    e, h = d['easier'], d['harder']
    if e['reviewed'] and h['reviewed']:
        say = (f": easier records {e['correct_pct']}% of {e['reviewed']:,}, harder records {h['correct_pct']}% of "
               f"{h['reviewed']:,}, the % weighs them as the catalog holds them ({d['harder_share']:.0%} harder)")
    else:
        one, other = ('harder', 'easier') if h['reviewed'] else ('easier', 'harder')
        say = f", {one} records only: {other} ones not reviewed yet"
    u = (d.get('unknown') or {}).get('reviewed')
    return say + (f"; {u:,} records of an older pack that does not record difficulty count as drawn" if u else '')


def one_review_text(rs):
    """The human review as ONE number, in the website's own words (site_release._one_review and _quality_lines): the
    user, 2026-10-30 and again 2026-11-07, "why would you keep those in earlier and not latest since the review isnt
    changing": a check against the paper counts the same whichever version's record it was. '' if it cannot be made."""
    try:
        import site_release
        return ' '.join(site_release._quality_lines({'review': rs}))
    except Exception:
        return ''


def review_summary_text(rs, short=False, catlog_has=None):
    """The human review, one number first (one_review_text: what the website shows); the full form adds the detail per
    catalog version underneath, for checking ('2,674 records on 408 papers reviewed · ...'; the reviewers' entries are
    records as they saw them: the site's word, round 17). catlog_has: (found, named) for the missing values reviewers
    named that CatLog v2 has now."""
    one = one_review_text(rs)
    if one and short:
        return one
    lines = [one, '  detail by catalog version (the website shows the line above):'] if one else []
    for name, label in (('v1', 'Review of CatLog v1 records'), ('v2', "Review of CatLog v2's own records")):
        r = whole = rs.get(name)
        if not r:
            continue
        basis = picked = head = ''
        if name == 'v1' and r.get('checkable'):  # the shares are over the entries a reviewer could check against a paper
            r = r['checkable']
            head = f", {whole['entries_without_paper']:,} of them without a paper (not checkable)"
        unchecked = (f"; not yet checked: PMID {', '.join(r['value_disputed_unchecked'])}" if r['value_disputed_unchecked'] else '')
        kinds = ', '.join(f'{k} {v}' for k, v in r['other_by_kind'].items())
        if name == 'v2':  # the percentages are the random sample's; entries picked on purpose are said apart
            basis = ((f", random sample of {r.get('entries_random', 0):,} records" if r.get('value_correct_basis') == 'random sample'
                      else ', all records (no random sample reviewed yet)') + (' on papers free to read' if r.get('scope') else '')
                     + (", weighted to the catalog's mix of papers" if r.get('weighted') else '') + _difficulty_text(r))
            picked = (f" · picked on purpose as hard cases: {r['entries_picked']:,} records, a value disputed on "
                      f"{r.get('picked_value_disputed', 0)} (per kind: review stats)" if r.get('entries_picked') else '')
        base = r.get('entries_random') if r.get('value_correct_basis') == 'random sample' else r['entries']
        lines.append(("  " if one else "") + f"{label}: {whole['entries']:,} records on {whole['papers']:,} papers{head} · no value (kcat, Km, kcat/Km) disputed on "
                     f"{base - r['value_disputed']:,} of {base:,} records{' with a paper' if head else ''} ({r['value_correct_pct']}%){basis} (checked against the "
                     f"paper: {r['value_disputed_checked_as_printed']} of the {r['value_disputed']} disputed as printed{unchecked}) · values missing: {r['value_missing']} "
                     f"records ({r['value_missing_pct']}%; the paper prints a value the record lacked"
                     + (', mostly the kcat' if name == 'v1' else '')  # what the v1 review found; not known for v2's records
                     + (f"; CatLog v2 has {catlog_has[0]} of the {catlog_has[1]} values reviewers named" if catlog_has and name == 'v1' else '')
                     + f") · other disagreements: "
                     f"{r['other_disputed']} records ({r['other_disputed_pct']}%)" + ('' if short or not kinds else f": {kinds}") + picked)
    return '\n'.join(lines)


def summary(rows, out, quiet=False):
    old = [r for r in rows if not r.get('v2_pack')]  # the earlier review of the old catalog
    mine = [r for r in rows if r.get('v2_pack')]  # reviews of v2's own measurements (v2 packs)
    st, st2 = Counter(r['status'] for r in old), Counter(r['status'] for r in mine)
    b = Counter(x['bucket'] for x in out)
    graded = b['agree'] + sum(b[k] for k in DIFFER)  # human-approved values only (agreement()'s values_approved)
    read = {x['pmid'] for x in out if x['pmid'] and x['bucket'] not in ('paper_not_read', 'derived', 'v2_approved_with_objection',
            'v2_reviewer_stated', 'v2_changed_since_review') and not x['bucket'].startswith('reviewed_in_v2')}  # earlier-review papers only
    try:  # rows an audit already judged are no longer "worth an audit"
        import catlog
        done = {f[3] for f in catlog.events() if f[2] in ('audit_keep', 'audit_drop', 'review_decided') and len(f) > 3}
    except Exception:
        done = set()
    audit = [x for x in out if x['bucket'] == 'v2_has_same' and not x['sweep'] and x.get('v2_row_id') not in done]
    s = {'decisions': len(old), 'approved': st['approved'], 'rejected': st['rejected'],
         'papers': len({r['pmid'] for r in old if r['pmid']}), 'papers_read_by_v2': len(read),
         'v2_measurements_reviewed': len(mine), 'v2_measurements_approved': st2['approved'], 'v2_measurements_rejected': st2['rejected'],
         'v2_disagreements': sum(1 for r in mine if r.get('disagree')),
         'agree': b['agree'], 'graded': graded, 'v2_different_value': b['v2_different_value'], 'v2_lacks': b['v2_lacks'],
         'v2_rejected': b['v2_rejected'], 'disputed_same': b['v2_has_same'], 'audit_candidates': len(audit),
         'approved_with_objection': b['approved_with_objection'], 'row_objections': b['row_objection'],
         'stated_found': b['stated_found'], 'stated': b['stated_found'] + b['stated_missing'], 'reviewed_in_v2': b['reviewed_in_v2'],
         'v2_values_approved': sum(1 for x in out if x['bucket'] == 'reviewed_in_v2' and x['status'] == 'approved'),
         'v2_values_rejected': sum(1 for x in out if x['bucket'] == 'reviewed_in_v2' and x['status'] == 'rejected')}
    s['review'] = review_summary(rows)  # what the reviewers' files say: the headline (the user, 2026-10-13)
    if s['review'].get('v2'):  # the values those v2 records hold now, every entry's (the site: "none of their N values")
        s['review']['v2']['values'] = sum(1 for x in out if x['bucket'].startswith('reviewed_in_v2')
                                          or x['bucket'] == 'v2_approved_with_objection')
    try:
        s['accuracy'] = accuracy(rows, out)
    except Exception as e:  # never let the accuracy block break compare or status
        s['accuracy'] = {'error': str(e)}
    try:
        s['agreement'] = agreement(rows, out, s)
    except Exception as e:  # the same for the agreement block
        s['agreement'] = {'error': str(e)}
    if not quiet:
        print(status_text(s))
    return s


def _first_now(s):
    """CatLog v2 against the reviewers' approved values, as it is now (the user, 2026-10-13: no first-comparison or
    blind-paper figures in the headline; agreement() keeps them for reference)."""
    a = s.get('agreement') or {}
    pct = f" ({100 * s['agree'] / s['graded']:.1f}%)" if s['graded'] else ''
    checked = (f" ({a['differ'] - a['differ_not_adjudicated']:,} of the {a['differ']:,} checked so far)"
               if isinstance(a.get('differ'), int) and isinstance(a.get('differ_not_adjudicated'), int) else '')
    wrong = (f"; CatLog values found wrong where AI agents checked the differences against the paper{checked}: "
             f"{a['catlog_value_wrong']}" if 'catlog_value_wrong' in a else '')
    return (f"where CatLog has re-read a paper the reviewers checked, its value matches the approved value for "
            f"{s['agree']:,} of {s['graded']:,}{pct}{wrong}")


def _exposed_text():
    """review stats' line on papers read or checked with database values in view: the count before the first add (what
    the agreement sets apart), every such paper by who opened the files, and the blind re-reads they were sent to."""
    n, e = len(_exposed()), _exposure()
    if not n and not e.get('papers'):
        return ''
    sent = (f"; sent back to be read again blind since {e['reread_blind_on']}: {e['reread_blind']} ({e['reread_blind_read']} "
            f"re-read, {e['reread_blind_verify']} re-verified; {e['reread_blind_done']} added again so far)"
            if e.get('reread_blind') else '')
    return (f" · papers whose reading or checking agent opened database values or earlier-catalog files: {n} before their "
            f"first add, {e.get('papers', 0)} in all (the reading agent on {e.get('reader', 0)}, only a checking agent on "
            f"{e.get('checker_only', 0)}; human_review/exposed.tsv; the prompts forbid it since 2026-10-12){sent}")


def status_text(s):
    if not s['papers_read_by_v2']:
        n = len(CALIBRATION.read_text().split()) if CALIBRATION.exists() else 0
        mine = (f"human review of v2's own records: {s['v2_measurements_reviewed']} ({s['v2_measurements_approved']} approved, "
                f"{s['v2_measurements_rejected']} rejected)\n" if s['v2_measurements_reviewed'] else '')
        return mine + (f"earlier human review (old catalog): {s['decisions']:,} decisions ({s['approved']:,} approved, "
                       f"{s['rejected']:,} rejected) on {s['papers']:,} papers · not comparable yet: v2 has read none of "
                       f"them; {n} on disk (human_review/calibration.txt) are read first")
    mine = (f"human review of v2's own records: {s['v2_measurements_reviewed']} ({s['v2_measurements_approved']} approved, "
            f"{s['v2_measurements_rejected']} rejected; values approved {s['v2_values_approved']}, rejected {s['v2_values_rejected']})\n"
            if s['v2_measurements_reviewed'] else '')
    return mine + (review_summary_text(s.get('review') or {}, short=True, catlog_has=(s['stated_found'], s['stated'])) + "\n"
            f"CatLog v2 has re-read {s['papers_read_by_v2']} of these papers: "
            f"{_first_now(s)} · v2 holds {s['disputed_same']} value(s) a reviewer rejected "
            f"({s['audit_candidates']} worth an audit) · reviewer-stated missing values v2 has: {s['stated_found']}/{s['stated']}"
            + _exposed_text())


def status_md(s):
    """The human-review part of `catlog.py report`: one short readable line."""
    mine = (f"v2's own records reviewed: {s['v2_measurements_reviewed']} ({s['v2_measurements_approved']} approved, "
            f"{s['v2_measurements_rejected']} rejected) · " if s['v2_measurements_reviewed'] else '')
    if not s['papers_read_by_v2']:
        return mine + f"earlier review: {s['decisions']:,} decisions on {s['papers']:,} papers; v2 has not read those papers yet"
    one = one_review_text(s.get('review') or {}).removeprefix('Human review: ')  # one number, as the website
    return ((one or mine + review_summary_text(s.get('review') or {}, short=True, catlog_has=(s['stated_found'], s['stated'])))
            + f" · CatLog v2 has re-read {s['papers_read_by_v2']} of these papers: {_first_now(s)}")


def status_line(md=False):
    """The human-review line for `catlog.py status`, or '' before the first ingest."""
    if not DECISIONS.exists():
        return ''
    try:
        s = compare(write=False, quiet=True)
        return status_md(s) if md else status_text(s)
    except Exception as e:  # never let review data break the counter
        return f'human review: could not compare ({e})'


def stats():
    rows = _decisions()
    print(f"exports kept: {len(_manifest())} (human_review/raw/)")
    if (HR / DB_REVIEW).exists():
        print(f"database check: {sum(1 for l in open(HR / DB_REVIEW) if l.strip()):,} values answered "
              f"(human_review/{DB_REVIEW}); the counts: python3 catlog.py review dbstats")
    cats = Counter(r['category'] for r in rows if r['status'] == 'rejected')
    print('rejections by kind:', ', '.join(f'{k} {v}' for k, v in cats.most_common()))
    print('papers with checkable decisions:', len({r['pmid'] for r in rows if r['checkable']}),
          '· not checkable (no PMID, database-only rows):', sum(1 for r in rows if not r['checkable']))
    print('changed their mind at least once:', sum(1 for r in rows if r['changed']))
    multi = [r for r in rows if len(r.get('reviewers') or {}) > 1]
    if multi:
        agree = sum(1 for r in multi if not r['disagree'])
        print(f'values seen by 2+ reviewers: {len(multi)}; they agree on {agree} ({100 * agree / len(multi):.0f}%); disagreements: '
              + ', '.join(r['key'] for r in multi if r['disagree'])[:300])
    by_key = {r['key']: r for r in rows}
    for f in sorted(PACKS.glob('*.json')) if PACKS.exists() else []:  # --overlap: the records a pack gave two people
        idx = json.loads(f.read_text())
        pairs = defaultdict(list)
        for k, v in idx.get('records', {}).items():
            if v.get('also'):
                pairs[(v['reviewer'], v['also'][0])].append(k)
            elif v.get('shared_with'):  # a paper another person's pack holds too (one-name packs, 2026-11-06)
                pairs[(v['reviewer'], v['shared_with']['reviewer'])].append(k)
        for (a, b), ks in sorted(pairs.items()):
            both = [by_key[k] for k in ks if k in by_key and {a, b} <= set(by_key[k].get('reviewers') or {})]
            differ = [r for r in both if r['reviewers'][a] != r['reviewers'][b]]
            print(f"{idx['pack_id']} {a} + {b}: reviewer agreement on shared records: {len(both) - len(differ)} of "
                  f"{len(both)} decided by both gave the same verdict ({len(ks)} shared)")
            for r in differ:
                last = {h['by']: h for h in r.get('history', [])}  # each one's latest decision
                print(f"    PMID {r['pmid']} {r['key']}: " + ' | '.join(
                    f"{w} {last[w]['status']}: {last[w]['comment'] or '-'}" if w in last else f'{w}: -' for w in (a, b)))
    per = defaultdict(list)
    for r in rows:
        for h in r.get('history', []):
            per[h.get('by', '')].append(h)
    for who, hs in sorted(per.items()):
        if not who:
            continue
        ts = sorted(time.mktime(time.strptime(h['at'][:19], '%Y-%m-%dT%H:%M:%S')) for h in hs if h['at'][:4].isdigit())
        gaps = [b - a for a, b in zip(ts, ts[1:]) if b - a < 1800]
        med = sorted(gaps)[len(gaps) // 2] if gaps else 0
        print(f'reviewer {who}: {len(hs)} decisions, {sum(h["status"] == "rejected" for h in hs)} rejections, '
              f'median {med:.0f} s between decisions, {sum(g < 5 for g in gaps)} under 5 s')
    mine = [r for r in rows if r.get('v2_pack')]
    if mine:  # v2's own values: the random sample's rate is the catalog's; each kind of trouble has its own
        rate = lambda rs: (f"{sum(r['status'] == 'rejected' and not row_only(r) for r in rs)}/{len(rs)} rejected"
                           + (f" (+{sum(r['status'] == 'rejected' and row_only(r) for r in rs)} noting another value)"
                              if any(r['status'] == 'rejected' and row_only(r) for r in rs) else ''))
        tiers, kinds = defaultdict(list), defaultdict(list)
        for r in mine:
            tiers[(r.get('why') or 'earlier pack').split(':')[0].split('(')[0].strip()].append(r)
            for i in r.get('issues') or []:
                kinds[i].append(r)
        print('v2 values reviewed, by sample:', '; '.join(f'{k} {rate(v)}' for k, v in sorted(tiers.items())))
        for k, v in sorted(kinds.items(), key=lambda kv: -len(kv[1])):
            print(f'  {k}: {rate(v)}')
    s = compare()
    print(review_summary_text(s.get('review') or {}, catlog_has=(s['stated_found'], s['stated'])))
    picked = ((s.get('review') or {}).get('v2') or {}).get('picked_by_kind') or {}
    if picked:  # the hard cases, outside the v2 headline: each kind on its own
        print("CatLog v2 entries picked on purpose (not in the headline), a value disputed / entries, by why they were picked:")
        for k, v in picked.items():
            print(f"  {k}: {v['value_disputed']}/{v['entries']}")
    if s.get('accuracy') and 'error' not in s['accuracy']:
        print(accuracy_text(s['accuracy']))
    if s.get('agreement') and 'error' not in s['agreement']:
        print(agreement_text(s['agreement'], time.strftime('%Y-%m-%d')))


def audit():
    """v2 rows that a specific human rejection disputes (same value), as JSON in the shape `catlog.py sample` prints."""
    import catlog
    compare(write=True, quiet=True)
    done = {f[3] for f in catlog.events() if f[2] in ('audit_keep', 'audit_drop', 'review_decided') and len(f) > 3}
    out = [x for x in _read_compare() if ((x['bucket'] == 'v2_has_same' and x['sweep'] != 'True')
           or (x['bucket'] == 'reviewed_in_v2' and x['status'] == 'rejected') or x['bucket'] == 'v2_approved_with_objection')
           and x['v2_row_id'] not in done]
    ids = {x['v2_row_id'] for x in out}
    keep = ('row_id', 'pmid', 'enzyme', 'organism', 'variant', 'substrate', 'cosubstrate', 'metric', 'raw_value',
            'raw_unit', 'value', 'unit', 'pH', 'temperature_C', 'conditions', 'location', 'quote')
    rows = [json.loads(l) for l in open(catlog.CATALOG) if l.strip()]
    note, held = {x['v2_row_id']: x['comment'] for x in out}, catlog.locked()  # the test set's rows: never audited here
    print(json.dumps([{**{k: r.get(k) for k in keep}, 'human_rejection': note[r['row_id']]} for r in rows
                      if r['row_id'] in ids and r['pmid'] not in held], ensure_ascii=False))


def decided(rid, why):
    """A v2 row a reviewer's rejection disputes, judged against the paper in HUMAN_REVIEW.md "Guideline": no audit
    needed (logged as review_decided; not an audit verdict, so audit statistics do not count it)."""
    import catlog
    pmid = next((json.loads(l)['pmid'] for l in open(catlog.CATALOG) if f'"row_id": "{rid}"' in l), None)
    if pmid is None:
        sys.exit(f'review decided: {rid} is not in catalog.jsonl')
    catlog.log(pmid, 'review_decided', rid, why)


def _read_compare():
    return list(csv.DictReader(open(COMPARE), delimiter='\t')) if COMPARE.exists() else []


DELIBERATE = re.compile(r'on purpose|deliberate|reprint', re.I)  # a value CatLog's reading rules leave out
LABEL_KINDS = (('the substrate structure', r'smiles|structure|resolved to'), ('the UniProt entry', r'uniprot|accession'),
               ('the variant', r'variant|isoform'), ('the organism', r'organism'), ('the substrate name', r'substrate'))


def _what_fixed(p):
    """What CatLog had wrong, in site words, when the check against the paper (unmatched_*.tsv) found CatLog wrong;
    None when it found nothing wrong with CatLog (then a later match is not called a correction). For a label, the
    cause is read clause by clause: the clause that names CatLog's (v2's) side decides; 'same UniParc', 'deleted' and
    synonym clauses are not CatLog errors (25296650: its UniProt entry was never wrong, its 'HP' structure was)."""
    if not p:
        return None
    c = (p.get('cause') or '').lower()
    if p.get('v2_value_wrong') == 'True':
        return 'the value'
    if p['verdict'] == 'v2_missed':
        return None if DELIBERATE.search(c) else 'a value CatLog had missed, added on a re-read'
    if not (p['verdict'] == 'matching_problem' and p['right_label'] == 'old'):
        return None
    for clause in re.split(r';|\bplus\b|\balso\b|\band\b|\. ', c):
        if not re.search(r"\bv2\b|v2's", clause) or re.search(r'same uniparc|deleted|synonym', clause):
            continue
        for kind, rx in LABEL_KINDS:
            if re.search(rx, clause):
                return kind
    return 'a label'


def _clean_comment(c):
    c = re.sub(r'https?://\S+|\S+@\S+', '', c or '')
    c = ' '.join(c.split())[:300]
    return c if len(c) >= 4 else None


def site():
    """The website hand-off (WEBSITE.md "Human review on the site"). Per v2 measurement the human marks, and the
    stats: plain JSON, dates only, no reviewer names, drafts or times, comments cleaned.
    Marks: human_verified / human_rejected (a reviewer judged this v2 value), agrees_with_earlier_review /
    differs_from_earlier_review (the old catalog's reviewed value for the same paper, metric, variant and substrate),
    corrected_per_review (a reviewer said the old catalog missed this value; v2 has it)."""
    import catlog
    decisions = {r['key']: r for r in _decisions()}
    s = compare(write=True, quiet=True)
    audited, decided = {}, {}
    for f in catlog.events():
        if f[2] in ('audit_keep', 'audit_drop') and len(f) > 3:
            audited[f[3]] = 'kept' if f[2] == 'audit_keep' else 'dropped'
        if f[2] == 'review_decided' and len(f) > 4:  # judged against the paper: the fact, without the rule's name
            decided[f[3]] = re.sub(r'^HUMAN_REVIEW\.md Guideline [0-9-]+:\s*|;?\s*not an error\.?$', '', f[4]).strip()
    marks = defaultdict(lambda: defaultdict(list))
    lines = _read_compare()
    for x in lines:
        if not x['v2_row_id']:
            continue
        d = decisions.get(x['key'], {})
        mark = {'reviewed_in_v2': 'human_verified' if x['status'] == 'approved' else 'human_rejected',
                'v2_approved_with_objection': 'human_disputed',
                'agree': 'agrees_with_earlier_review', 'v2_different_value': 'differs_from_earlier_review',
                'v2_has_same': 'earlier_review_rejected_this_value', 'stated_found': 'corrected_per_review'}.get(x['bucket'])
        if mark:
            marks[x['v2_row_id']][mark].append({'metric': x['metric'], 'reviewed_on': str(d.get('decided_at', ''))[:10],
                                                'comment': _clean_comment(d.get('comment')), 'category': x.get('category', ''),
                                                **({'audit': audited[x['v2_row_id']]} if x['v2_row_id'] in audited
                                                   and mark in ('human_rejected', 'earlier_review_rejected_this_value') else {}),
                                                **({'paper_check': decided[x['v2_row_id']]} if x['v2_row_id'] in decided
                                                   and mark == 'earlier_review_rejected_this_value' else {})})
    first, pc = _first(), _adjudications()
    for x in lines:  # CatLog errors the comparison found (checked against the paper) and fixed since: credit to the review
        f, what = first.get((x['key'], x['metric'])), _what_fixed(pc.get((x['key'], x['metric'])))
        if x['bucket'] == 'agree' and x['v2_row_id'] and f and f['bucket'] != 'agree' and what:
            marks[x['v2_row_id']]['corrected_after_review'].append({'metric': x['metric'], 'corrected': what,
                                                                    'first_compared': f['first_compared']})
    wide = [json.loads(l) for l in open(ROOT / 'catlog_wide.jsonl') if l.strip()] if (ROOT / 'catlog_wide.jsonl').exists() else []
    out, tally = [], Counter()
    for w in wide:
        m = {}
        for rid in w.get('row_ids', []):
            for k, v in marks.get(rid, {}).items():
                m.setdefault(k, []).extend(v)
        if m:
            out.append({'measurement_id': w['measurement_id'], 'pmid': w['pubmed_id'], 'row_ids': w.get('row_ids', []), 'human': m})
            tally.update(m.keys())
    n = len(wide)
    stats = {'v2_measurements': n, 'measurements_with_a_human_mark': len(out),
             **{k: tally[k] for k in ('human_verified', 'human_rejected', 'human_disputed', 'agrees_with_earlier_review',
                                      'differs_from_earlier_review', 'earlier_review_rejected_this_value', 'corrected_per_review',
                                      'corrected_after_review')},
             'v2_measurements_reviewed': s['v2_measurements_reviewed'],
             'earlier_review': {'decisions': s['decisions'], 'approved': s['approved'], 'rejected': s['rejected'], 'papers': s['papers'],
                                'papers_read_by_v2': s['papers_read_by_v2'],
                                'review': (s.get('review') or {}).get('v1'),  # the headline: what the reviewers' files say
                                'agreement_pct': round(100 * s['agree'] / s['graded'], 1) if s['graded'] else None,  # as it is now
                                'agreement_after_fixes_pct': round(100 * s['agree'] / s['graded'], 1) if s['graded'] else None}}
    wide_p = ROOT / 'catlog_wide.jsonl'
    sha = hashlib.sha256(wide_p.read_bytes()).hexdigest() if wide_p.exists() else ''
    head = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    SITE.write_text(json.dumps({'schema': 'catlog-v2-human-review/2', 'generated_on': time.strftime('%Y-%m-%d'),
                                'catalog': {'file': 'catlog_wide.jsonl', 'catalog_sha256': sha, 'v2_commit': head},
                                'reviews_through': max((str(d.get('decided_at', ''))[:10] for d in decisions.values()), default=''),
                                'stats': stats, 'measurements': out}, ensure_ascii=False, separators=(',', ':')))
    # no whole-row rule (the user, 2026-10-13): each approved value counts on its own
    _site_marks(decisions, out, set(), lines, wide, quality(s))
    catlog.log('-', 'review_site', f'measurements_marked={len(out)}')
    print(f'{SITE} ({max(1, SITE.stat().st_size // 1024)} kB): {len(out)} of {n} v2 measurements carry a human mark; '
          f'stats: {json.dumps({k: v for k, v in stats.items() if k != "earlier_review"})}. Ready for the website '
          '(WEBSITE.md "Human review on the site").')


def _site_table(keys):
    """record key -> (kcat, km, kcat_over_km) as the newest site bundle shows them (site_build/build.json; its old rows
    come from the certified base, the same in every bundle), for `keys`; None when there is no bundle."""
    try:
        bundle = Path(json.loads((ROOT / 'site_build' / 'build.json').read_text())['bundle'])
        table = next((bundle / 'data').glob('catlog-table.*.jsonl.gz'))
    except (OSError, ValueError, KeyError, StopIteration):
        return None
    out = {}
    with gzip.open(table, 'rt') as fh:
        for line in fh:
            k = re.match(r'\{"record_key": "([^"]*)"', line)
            if k is None or k.group(1) in keys:
                r = json.loads(line)
                if r.get('record_key') in keys:
                    out[r['record_key']] = (r.get('kcat'), r.get('km'), r.get('kcat_over_km'))
    return out


def _same(a, b):
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= 1e-6 * max(abs(a), abs(b)))


def _case_note(pmid, substrate=''):
    """The Guideline's note for a case; a paper whose rows the reviewer judged differently has one note per substrate."""
    note = CASE_NOTES.get(pmid, '')
    return (note.get(_name(substrate)) or note['']) if isinstance(note, dict) else note


def wilson(k, n, z=1.959964):
    """The 95% Wilson score interval of k successes in n trials, as percentages (low, high); None without trials."""
    if not n:
        return None
    p, z2 = k / n, z * z
    mid, half = (p + z2 / (2 * n)) / (1 + z2 / n), z * ((p * (1 - p) + z2 / (4 * n)) / n) ** 0.5 / (1 + z2 / n)
    return 100 * max(0.0, mid - half), 100 * min(1.0, mid + half)


def audit_detail():
    """The random audit's wrong values (catlog.audit_summary's rule: per row its latest verdict, rows only targeted
    audits or whole-paper follow-ups saw left out, catlog.audit_targeted) with their 95% Wilson interval as 'low-high'
    percentages to 2 decimals, the papers they sit in and how many sit in the two papers with the most (item 7 of
    work/publication_strategy_20261021/FIXES_FOR_MAIN_CHAT.md), given only when those two hold most of them (else the
    words "in two papers" would say nothing). The interval treats the values as independent; drops can cluster by
    paper. audit_targeted_values / _wrong: the rows only targeted audits and follow-ups saw and their drops (counted
    among CatLog's own errors, catlog_errors)."""
    import catlog
    last, sampled = {}, set()
    evs = catlog.events()
    for f in evs:
        if f[2] in ('audit_keep', 'audit_drop') and len(f) > 3:
            last[f[3]] = (f[2], f[1])
            if not catlog.audit_targeted(f):
                sampled.add(f[3])
    label = catlog.relabelled_drops(evs)  # a drop for the organism label, back under the right one: not a wrong value
    per = Counter(p for rid, (e, p) in last.items() if rid in sampled and e == 'audit_drop' and rid not in label)
    n, wrong = sum(1 for rid in last if rid in sampled), sum(per.values())
    ci, top2 = wilson(wrong, n), sum(c for _, c in per.most_common(2))
    return {**({'audit_wrong_ci95': f'{ci[0]:.2f}-{ci[1]:.2f}'} if ci else {}), 'audit_wrong_papers': len(per),
            **({'audit_wrong_top2': top2} if 2 * top2 > wrong else {}),
            'audit_targeted_values': len(last) - n,
            'audit_targeted_wrong': sum(1 for rid, (e, _) in last.items()
                                        if rid not in sampled and e == 'audit_drop' and rid not in label)}


SWEEP_COPY = re.compile(r"(?i)re-?read (?:duplicate|copy)|reworded|duplicate\b|same measurement as row")  # the value stays in another row
# a value right as its paper printed it, which the paper's authors corrected later in a correction notice (the corrected
# value is stored under the notice's own PMID): not CatLog's error (40465391 and its corrigendum 41287407, 2026-11-17)
SUPERSEDED = re.compile(r"(?i)superseded by the authors' correction\b")
UNIT_FIXED = re.compile(r'unit corrected to (.+?) \(\d{4}-\d{2}-\d{2}')  # catlog.cmd_unitfix's verify_note
AUDIT_ROW = re.compile(r'\(row ([0-9a-f]{16})\)')  # a unitfix reason naming the audited row it follows ('audit <day> (row <id>)')


def _unit_changed(r, fixed):
    """Whether a unit fix reads the row's printed cell in another unit than the one the paper prints: units.normalize of
    the printed unit and of the fixed one ('s^{−1}' and 's^-1' are the same unit, 2026-11-06); a unit the code cannot
    read counts as another."""
    from units import normalize
    a = normalize(r.get('metric') or '', r.get('raw_value') or '', r.get('raw_unit') or '')
    b = normalize(r.get('metric') or '', r.get('raw_value') or '', fixed)
    return a[0] is None or b[0] is None or a[1] != b[1] or abs(a[0] - b[0]) > 1e-9 * max(abs(a[0]), abs(b[0]))


def catlog_errors():
    """CatLog's own errors found so far, by every route (item 3 of work/publication_strategy_20261021/
    FIXES_FOR_MAIN_CHAT.md), each {'values', 'papers'}: audit (values an AI audit found wrong, random or targeted:
    removed, latest verdict audit_drop; corrected, a unit fix back to the printed unit that an audit made, its
    'unit corrected' verdict, or that names that audited row in its reason: the value had been stored in a unit the
    paper does not print, 40723313 on 2026-11-02; and a value an audit kept as 'unit corrected' to a unit the paper
    misprints, also in unit_fix), sweep (values removed by a `drop` that no audit made: the sweeps of
    the catalog for an error an audit or check had found; reprinted and partial_constant say how many were values
    reprinted from an earlier paper and per-product partial constants; a copy of a value another row keeps is not an
    error and not counted, nor a value its authors corrected later in a correction notice, SUPERSEDED),
    unit_fix (values whose unit was corrected away from the printed one because the paper's unit is misprinted:
    cmd_unitfix's verify_note, in the catalog or in rows removed since, the two units compared as units.normalize reads
    them; a fix back to the printed unit is a reading change, counted under audit when an audit made it, else not an
    error), difference_check (values whose current check against the paper, sources/
    database_corrections.tsv as dbcompare.recorded reads it, says CatLog is wrong; removed: no longer in the catalog,
    corrected: their unit or cell corrected in place; the rest wait for their audit, dbcheck.audit_first. A value
    still in the catalog, not corrected and not waiting is left out: an audit kept it as printed after that check,
    17378584 and 25016016 on 2026-10-21/26), misread_cell (values whose printed cell CatLog had misread,
    corrected in place on the page image: catlog.cmd_cellfix's log lines), label_fix (values dropped for a wrong
    organism label and back under the right one, catlog.relabelled_drops: corrected, not removed, so they leave
    audit's removed, which counts an audit-found one as corrected, and sweep; the user, 2026-11-15) and all (each value
    once; a value can be found by several routes). sweep's other: the values of no named kind."""
    import catlog, dbcompare
    from dbcheck import audit_first
    rid_re, pmid_re = re.compile(r'"row_id": "([^"]+)"'), re.compile(r'"pmid": "([^"]+)"')
    incat, unit, back = {}, {}, {}
    for path in (catlog.CATALOG, catlog.REJECTED):
        if not path.exists():
            continue
        for line in open(path):
            if path == catlog.CATALOG and (m := rid_re.search(line)):
                incat[m.group(1)] = (pmid_re.search(line) or [None, ''])[1]
            if 'unit corrected to ' in line:
                r = json.loads(line)
                u = UNIT_FIXED.search(r.get('verify_note') or '')
                if u:
                    (unit if _unit_changed(r, u.group(1)) else back)[r['row_id']] = r['pmid']
    last, sweep, kinds, unit_audited = {}, {}, Counter(), set()
    evs = catlog.events()
    label = catlog.relabelled_drops(evs)  # dropped for the organism label, back under the right one: corrected
    for f in evs:
        if f[2] in ('audit_keep', 'audit_drop') and len(f) > 3:
            last[f[3]] = (f[2], f[1])
            if f[2] == 'audit_keep' and len(f) > 4 and f[4].startswith('unit corrected'):
                unit_audited.add(f[3])
    audit = {rid: p for rid, (e, p) in last.items() if e == 'audit_drop' and rid not in label}
    by_audit = unit_audited | {f[3] for f in evs if f[2] == 'unitfix' and len(f) > 5
                               and unit_audited & set(AUDIT_ROW.findall(' '.join(f[5:])))}
    audit_fixed = {rid: p for rid, p in back.items() if rid in by_audit and rid not in audit}
    # (the numbers audit, 2026-11-06, N1: an audit's own 'unit corrected' to a misprinted unit counts as corrected
    # under audit too, so the random audit's 7 corrected sit inside the audit route's; they stay in unit_fix)
    audit_fixed.update({rid: p for rid, p in unit.items() if rid in unit_audited and rid not in audit})
    audit_fixed.update({rid: p for rid, (e, p) in last.items() if e == 'audit_drop' and rid in label})  # a label an audit found
    for f in evs:
        if f[2] == 'drop' and len(f) > 4 and f[3] not in incat and f[3] not in audit and f[3] not in sweep \
                and f[3] not in label and not SWEEP_COPY.match(f[4]) and not SUPERSEDED.match(f[4]):
            sweep[f[3]] = f[1]
            kinds['reprinted' if re.search(r'(?i)reprint', f[4]) else 'partial_constant'
                  if re.match(r'(?i)partial constant', f[4]) else 'other'] += 1
    misread = {f[3]: f[1] for f in evs if f[2] == 'cellfix' and len(f) > 3}
    fixed = {**unit, **audit_fixed, **misread}  # corrected in place
    waiting = audit_first(catlog)  # a catlog_wrong verdict no audit has answered since
    wrong = {rid: incat.get(rid, '') for rid, rows in dbcompare.recorded().items()
             if any(r.get('verdict') == 'catlog_wrong' for r in rows)
             and (rid not in incat or rid in fixed or rid in waiting)}
    count = lambda d: {'values': len(d), 'papers': len({p for p in d.values() if p})}
    every = {**audit, **audit_fixed, **sweep, **unit, **wrong, **misread, **label}
    return {'audit': {**count({**audit, **audit_fixed}), 'removed': len(audit), 'corrected': len(audit_fixed)},
            'sweep': {**count(sweep), 'reprinted': kinds['reprinted'],
                                             'partial_constant': kinds['partial_constant'], 'other': kinds['other']},
            'unit_fix': count(unit),
            'difference_check': {**count(wrong), 'removed': sum(1 for r in wrong if r not in incat),
                               'corrected': sum(1 for r in wrong if r in incat and r in fixed)},
            'misread_cell': count(misread), 'label_fix': count(label), 'all': count(every)}


def quality(s):
    """The website's quality numbers, top-level 'quality' in site_marks.json (the site copies it to overview.quality):
    AI audits (catlog.audit_summary: values, not log lines, the wrong ones removed, audit_corrected those kept with
    their unit corrected and audit_labels_corrected those back under a corrected organism label, not wrong;
    audit_detail: their interval and papers), human review
    (summary and accuracy), the agreement of human reviewers with CatLog (agreement(), with its definitions), CatLog's
    own errors by route (catlog_errors) and the papers read or checked with database values in view (exposed:
    _exposure). Headline (the user, 2026-10-13): `review`, what the reviewers' files say (review_summary); v2_found =
    CatLog's matches as they are now (agree; no longer the first comparison), v2_approved_total = values_approved.
    v2_differences_checked counts every check of a difference on file (some since matched); the differences now and
    those not yet checked are agreement's differ and differ_not_adjudicated."""
    import catlog
    a = s.get('accuracy') or {}
    audited, wrong, corrected, labels = catlog.audit_summary(split=True)
    agree = s.get('agreement') or {}
    extra = {}
    for key, part in (('audit', audit_detail), ('catlog_errors', catlog_errors), ('exposed', _exposure)):
        try:  # never let one part stop the marks file
            got = part()
            extra.update(got if key == 'audit' else {key: got} if got else {})
        except Exception as e:
            print(f'  quality: {key} left out ({e})')
    return {'as_of': time.strftime('%Y-%m-%d'), 'audit_values': audited, 'audit_wrong': wrong,
            'audit_corrected': corrected,  # kept with their unit corrected (Stats: kept, corrected, removed as wrong)
            'audit_labels_corrected': labels,  # back under a corrected organism label, not wrong (2026-11-15; Stats' Figure 2: corrected)
            'compared_values_v1': a.get('v1_values_both'), 'compared_papers_v1': a.get('v1_papers_both'),
            'wrong_v1': a.get('v1_wrong_both'),
            'label_or_annotation_v1': (a.get('v1_label_values_paper_check') or 0) + (a.get('v1_annotation_values_paper_check') or 0),
            'review': s.get('review'),  # the headline (the user, 2026-10-13): what the reviewers' files say
            'v2_found': s.get('agree'), 'v2_found_after_fixes': s.get('agree'), 'v2_approved_total': s.get('graded'),
            'v2_differences_checked': a.get('differences_checked'), 'v2_wrong': a.get('v2_wrong_in_differences'),
            **extra, **({'agreement': agree} if agree and 'error' not in agree else {})}


SITE_METRIC = {'kcat': 'kcat', 'Km': 'km', 'kcat/Km': 'kcat_over_km'}  # the site's field names for the marks' approved list


def _site_marks(decisions, v2_marked, bad, lines, wide, quality=None):
    """human_review/site_marks.json: per site record key (an old catalog record key, or a v2 measurement_id) whether a
    human reviewer checked the value and a neutral note, as HUMAN_REVIEW.md "Guideline" decided. Approved values are
    "checked" (old rows, and the v2 values they match); approvals whose comment objects are disputes, not checks; a
    rejection marks nothing (no literature, a missing other value, a label point), except the case-by-case notes.
    Old rows: only a record the newest site bundle shows with the values the reviewer saw, compared as stored (the old
    pipeline changed some approved rows afterwards: 19728741, 27537621, 28439850; 17986465's kcat stays in min^-1 on the
    site while the decision holds s^-1, so it is not marked either), never an approval with no paper. `bad`: approvals
    that mark nothing (empty since the user dropped the whole-row rule, 2026-10-13). A v2 record is checked when a
    reviewer approved every kcat and Km it prints and its kcat/Km either was approved too or follows from them (kcat and
    Km both approved, and the paper's kcat/Km agrees with kcat ÷ Km: "seeing kcat and Km is enough", the user,
    2026-10-13); otherwise it keeps the per-metric note."""
    old = [d for d in decisions.values() if not d.get('v2_pack')]
    table = _site_table({d['key'] for d in old})
    if table is None:
        print('  no site bundle (site_build/build.json): old records get no marks')
        table = {}
    marks = {}
    wrong_old = {k for (k, _), x in _adjudications().items()  # the paper shows the earlier row's label or value was wrong
                 if _differ_class(x) in ('differ_earlier_label_error', 'differ_earlier_value_error')}
    for d in old:
        if d['key'] in bad or d['key'] in wrong_old or d['key'] not in table or (d['status'] == 'approved' and not d.get('pmid') and not d.get('doi')):
            continue
        if not all(_same(v, d.get(m)) for v, m in zip(table[d['key']], ('kcat', 'Km', 'kcat/Km'))):
            continue  # the site shows other values than the reviewer saw
        objects = (d.get('category') or '') in OBJECTS_TO_VALUE
        confirmed = d['status'] == 'rejected' and CONFIRMED.get(d['pmid']) == d.get('category')
        if (d['status'] == 'approved' and not objects) or confirmed:  # approved: the values the reviewer saw (site field names)
            marks[d['key']] = {'checked': True, 'approved': [SITE_METRIC[m] for v, m in zip(table[d['key']], ('kcat', 'Km', 'kcat/Km'))
                                                            if v is not None]}
        if d['pmid'] in CASE_NOTES and (confirmed or (d['status'] == 'rejected' and objects)):
            marks.setdefault(d['key'], {'checked': False})['note'] = _case_note(d['pmid'], d.get('substrate'))
    n_old = len(marks)
    order = ['kcat', 'Km', 'kcat/Km']
    agreed = defaultdict(set)  # v2 row id -> metrics an earlier approval outside `bad` matches
    for x in lines:
        if x['bucket'] == 'agree' and x['key'] not in bad and x['v2_row_id']:
            agreed[x['v2_row_id']].add(x['metric'])
    printed = {w['measurement_id']: set(w.get('evidence') or {}) for w in wide}
    ratio_ok = {w['measurement_id']: bool(w.get('ratio_check')) and 'outside tolerance' not in w['ratio_check'] for w in wide}
    # kcat/Km follows from approved kcat and Km only when the paper's kcat/Km agrees with kcat ÷ Km (checked, within
    # tolerance) and no reviewer disputed that kcat/Km (code review, 2026-10-13)
    follows = lambda ms, mid, no=(): set(ms) | ({'kcat/Km'} if {'kcat', 'Km'} <= set(ms) and ratio_ok.get(mid, False)
                                                 and 'kcat/Km' not in no else set())
    substrate = {w['measurement_id']: w.get('substrate_name', '') for w in wide}
    listed = lambda ms: ms[0] if len(ms) == 1 else f"{', '.join(ms[:-1])} and {ms[-1]}"
    for m in v2_marked:
        h, mid = m['human'], m['measurement_id']
        verified = {x['metric'] for x in h.get('human_verified', [])}
        no = {x['metric'] for k in ('human_rejected', 'human_disputed', 'earlier_review_rejected_this_value',
                                    'differs_from_earlier_review') for x in h.get(k, [])}
        checked = sorted(verified | {x for rid in m['row_ids'] for x in agreed.get(rid, ())}, key=order.index)
        full = bool(checked) and follows(checked, mid, no) >= printed.get(mid, set())
        note = ''
        if verified and follows(verified, mid, no) >= printed.get(mid, set()):
            note = 'Checked by a human reviewer.'
        elif checked:
            marked = {x['metric'] for v in h.values() for x in v}  # a reviewer stated, rejected or approved another value
            rest = [x for x in order if x in printed.get(mid, set()) and x not in follows(checked, mid, no) and x not in marked]
            note = (f'A human reviewer approved the same {listed(checked)} for this paper'  # one CatLog: no version (2026-11-03)
                    + (f"; {listed(rest)} {'was' if len(rest) == 1 else 'were'} not reviewed." if rest else '.'))
        if m['pmid'] in CASE_NOTES and h.get('earlier_review_rejected_this_value'):
            note = _case_note(m['pmid'], substrate.get(mid, ''))
        else:  # where a reviewer disagreed, and what the check against the paper found
            said = []
            for x in h.get('earlier_review_rejected_this_value', []):
                found = ('an AI audit against the paper kept it' if x.get('audit') == 'kept'
                         else f"checked against the paper: {x['paper_check']}" if x.get('paper_check')
                         else 'not yet re-checked against the paper')
                line = f"A human reviewer questioned this {x['metric']}; {found}."
                if line not in said:
                    said.append(line)
            note = ' '.join([note] + said)
        fixed = sorted({x['corrected'] for x in h.get('corrected_after_review', [])})
        if fixed:
            note += f" Corrected after human review: {listed(fixed)}."
        note = note.strip()
        # approved: only the values a reviewer approved (site field names); a kcat/Km that merely follows from approved kcat
        # and Km makes the record human-checked but gets no mark of its own (round-6 recheck: 252 records showed one)
        approved = [SITE_METRIC[x] for x in order if x in checked and x in printed.get(mid, set())]
        if checked or note:
            marks[mid] = {'checked': full, **({'approved': approved} if approved else {}), **({'note': note} if note else {})}
    SITE_MARKS.write_text(json.dumps({
        'schema': 'catlog-human-review-marks/1', 'generated_on': time.strftime('%Y-%m-%d'),
        'semantics': 'checked: a human reviewer approved every kcat and Km this record prints (or, on a record read from the '
                     'paper by CatLog, the same values of the same paper, enzyme, substrate and variant in the review '
                     "of records of CatLog's earlier version), and its kcat/Km was approved too or follows from them "
                     "(the paper's kcat/Km agrees with kcat ÷ Km); note: what the "
                     'reviewer assessed; approved: the values a reviewer approved on this record (kcat, km, kcat_over_km), for a '
                     'mark beside each value (a kcat/Km that only follows from approved kcat and Km gets no mark). Rejections for a '
                     'value the reviewer could not locate, another missing value or a label are not marked.',
        **({'quality': quality} if quality else {}), 'marks': marks}, ensure_ascii=False, separators=(',', ':')))
    ck = [k for k, v in marks.items() if v['checked']]
    print(f"{SITE_MARKS}: {len(ck)} records checked by a human reviewer ({sum(k in table for k in ck)} old, "
          f"{sum(k not in table for k in ck)} v2), {sum(1 for v in marks.values() if v.get('note'))} with a note "
          f"({n_old} old records marked, {len(marks) - n_old} v2)")


def _issue_tests(glyph, natural, years=None):
    """The kinds of trouble a review pack samples, each a test on one exported measurement (catlog_wide.jsonl).
    Every kind gets its own quota, so each comes back with its own error rate."""
    def notes(w):
        return ' '.join(str(v) for v in (w.get('metric_notes') or {}).values()).lower()

    def ev(w):
        return list((w.get('evidence') or {}).values())

    from sequences import split_variant
    from structures import is_abbrev
    return [
        ('kcat/Km differs from kcat / Km', lambda w: 'outside tolerance' in (w.get('ratio_check') or '')),
        ('pH or temperature not printed', lambda w: w.get('ph') is None or w.get('temperature_c') is None),
        ('value the paper calls approximate', lambda w: 'approximate' in notes(w) or 'imprecise' in notes(w)),
        ('number not in the databases for this paper', lambda w: any(str(v).startswith('number not in') for v in (w.get('db_check') or {}).values())),
        ('PDF text layer mangles symbols (µ read as m)', lambda w: w['pubmed_id'] in glyph),
        ('read off a page image (scan)', lambda w: any(e.get('quote_check') or str(e.get('quote', '')).startswith('[page image') for e in ev(w))),
        ('second reader corrected a field', lambda w: any(r.get('corrected') for r in (w.get('reasoning') or {}).values())),
        ('unit with a multiplier or exponent', lambda w: any(re.search(r'10\^|×|x ?10', f"{e.get('raw_value', '')} {e.get('raw_unit', '')}") or e.get('unit_for_conversion') for e in ev(w))),
        ('kcat printed per minute or per hour', lambda w: bool(re.search(r'min|\bh\b|hr', str(((w.get('evidence') or {}).get('kcat') or {}).get('raw_unit', ''))))),
        ('natural form (isozyme, allele): wild type since 2026-10-10', lambda w: w['measurement_id'] in natural),
        ('point mutant', lambda w: not w.get('wild_type') and bool(split_variant(w.get('mutation_signature') or '')[1])),
        ('engineered construct or truncation', lambda w: bool(w.get('construct')) or (not w.get('wild_type') and not split_variant(w.get('mutation_signature') or '')[1])),
        ('no sequence assigned', lambda w: not w.get('sequence')),
        ('sequence numbered differently (mature chain, PDB, primers)', lambda w: (w.get('sequence_frame') or '') not in ('', 'UniProt canonical')),
        ('EC taken from the databases, not the paper', lambda w: str(w.get('ec_source', '')).startswith('databases')),
        ('substrate printed as an abbreviation', lambda w: is_abbrev(w.get('substrate_name') or '') and bool(w.get('substrate_full_name'))),
        ('apparent or Hill-fit value', lambda w: 'apparent' in notes(w) or 'hill' in notes(w)),
        ('value from a figure or the running text', lambda w: any(re.match(r'(fig|results|text|discussion|abstract)', str(e.get('location', '')).lower()) for e in ev(w))),
        ('value from supplementary material', lambda w: any('suppl' in str(e.get('location', '')).lower() for e in ev(w))),
        ('paper without a PMID (DOI only)', lambda w: str(w['pubmed_id']).startswith('NP')),
        # OpenAlex's year when known (PMIDs of the 1960s-80s run up to ~7.5M and old ones sit at 13-14M: the PMID alone
        # missed 45 such papers in one pack); otherwise the low-PMID guess
        ('paper from before about 1990', lambda w: (years or {}).get(w['pubmed_id']) < 1990 if (years or {}).get(w['pubmed_id'])
         else str(w['pubmed_id']).isdigit() and int(w['pubmed_id']) < 2100000),
    ]


def withdraw(pack_id):
    """A pack that was never sent (or never comes back): its measurements become available again. The pack and its
    index move to packs/withdrawn/; nothing is deleted."""
    import shutil
    dest = PACKS / 'withdrawn'
    dest.mkdir(parents=True, exist_ok=True)
    moved = [f for f in PACKS.glob(f'*{pack_id}*') if f.name != 'withdrawn']
    for f in moved:
        shutil.move(str(f), str(dest / f.name))
    print(f'{pack_id}: moved {len(moved)} item(s) to human_review/packs/withdrawn/' if moved else f'{pack_id}: no such pack')


AA3 = dict(A='Ala', R='Arg', N='Asn', D='Asp', C='Cys', Q='Gln', E='Glu', G='Gly', H='His', I='Ile', L='Leu', K='Lys',
           M='Met', F='Phe', P='Pro', S='Ser', T='Thr', W='Trp', Y='Tyr', V='Val')
POINT = re.compile(r'(?<![A-Za-z0-9])([ARNDCQEGHILKMFPSTWYV])(\d+)([ARNDCQEGHILKMFPSTWYV])(?![A-Za-z0-9])')  # not V67LFKHV, R1C21
ABBREV = {'fig', 'figs', 'ref', 'refs', 'no', 'nos', 'eq', 'eqs', 'al', 'cf', 'vs', 'approx', 'ca', 'sp', 'spp', 'suppl',
          'supp', 'tab', 'st', 'p', 'pp', 'resp', 'abs', 'conc', 'temp', 'vol', 'var', 'cv', 'subsp', 'sect'}
PLACE = (re.compile(r'(?i)\bcol(?:umn)?s?\b'), re.compile(r'(?i)\brows?\b'))  # what a reviewer needs from 'Look in'


def _variant_long(sig):
    """'E272A' -> 'E272A (Glu272→Ala)', each point mutation of a multi-mutant: papers print Glu272Ala as often as E272A.
    '' when nothing expands (wild type, Δ74-80, chimera 2)."""
    long = [f'{AA3[a]}{n}→{AA3[b]}' for a, n, b in POINT.findall(str(sig or ''))]
    return f"{sig} ({', '.join(long)})" if long else ''


def _clause_end(read):
    """Where CatLog's reading ends its first clause: '; ' or a sentence's '. ', outside brackets (not 'Fig. S2',
    'E. coli', 'et al. 2', 'row a; col b' inside parentheses)."""
    depth = 0
    for i, ch in enumerate(read):
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth = max(0, depth - 1)
        elif depth == 0 and read[i:i + 2] in ('; ', '. '):
            if ch == ';':
                return i
            word = re.split(r'[\s(\[]', read[:i])[-1].strip('\'"')
            if word.lower() in ABBREV or re.fullmatch(r'[A-Za-z]|(?:[A-Za-z]\.)+[A-Za-z]|.*\.\.', word):
                continue  # Fig. 2, E. coli, e.g. the, U.S. Army, ... and
            return i
    return len(read)


def _word_cut(text, n):
    """The first ~n characters of text cut between words (a word longer than that is kept whole): (head, rest)."""
    if len(text) <= n:
        return text, ''
    cut = text.rfind(' ', 0, n + 1)
    if cut < 0.6 * n:  # one long name (a chemical): end after it rather than inside it
        cut = text.find(' ', n)
        if cut < 0:
            return text, ''
    return text[:cut].rstrip(' ,;:'), text[cut:].strip()


def _asides(text, n):
    """text with its long bracketed asides shortened, longest first, until it fits n characters: a table title or a
    header spelled out in brackets leaves the row and column readable. A leading one goes; others become '(…)'."""
    out = text
    while len(out) > n:
        groups, depth, open_ = [], 0, 0
        for i, ch in enumerate(out):
            if ch in '([':
                open_, depth = (i if depth == 0 else open_), depth + 1
            elif ch in ')]' and depth:
                depth -= 1
                if depth == 0 and i - open_ >= 24:
                    groups.append((open_, i + 1))
        if not groups:
            break
        a, b = max(groups, key=lambda g: g[1] - g[0])
        out = out[b:].lstrip(' ,:') if not out[:a].strip() else f"{out[:a].rstrip()} (…){out[b:]}"
    return out


def _look_in(location, read):
    """(look_in, where, where_full) for one value. look_in: the place to open first, the location and the first clause of
    CatLog's reading, or its first two when only the second names the column or row (about 140 characters, 170 for two:
    long bracketed asides shortened, then cut between words; a leading repeat of the location dropped). where: the rest
    of the reading (about 300 characters, cut between words). where_full: the whole reading when those two do not show
    all of it. Finding the number was the main time sink: the table, row and column used to come after ~400 characters,
    behind the variant and conditions lines."""
    loc, read = str(location or '').strip(), str(read or '').strip()
    start, head = 0, loc
    if loc and read.lower().startswith(loc.lower()) and not read[len(loc):len(loc) + 1].isalnum():
        sep = re.match(r'(?:[\s,:;–-]|\.(?=\s|$))*', read[len(loc):]).end()
        if sep or len(read) == len(loc):  # 'Table 2, row ...' after 'Table 2'
            start = len(loc) + sep
        else:
            head = ''  # 'Table 1(a) row dC': the reading names the place more exactly
    end = start + _clause_end(read[start:])
    while not read[start:end].strip(' .;:,') and end < len(read):  # an empty first clause: the place is in the next one
        start, end = end + 2, end + 2 + _clause_end(read[end + 2:])
    after, room = (end + 2 + _clause_end(read[end + 2:]) if end < len(read) else end), 140
    if (any(not p.search(read[start:end]) and p.search(read[end:after]) for p in PLACE)
            and len(_asides(read[start:after], 170)) <= 170):
        end, room = after, 170  # 'row TcMSRB / L-Met(R)SO; kcat column': the column too (13% of values name it there)
    clause = read[start:end].strip()
    short = _asides(clause, room)
    first, more = _word_cut(short, room)
    rest = read[end + 2:].strip() if end < len(read) else ''
    if more:
        first, rest = first + ' …', f"… {more}{read[end:end + 2] if rest else ''}{rest}".strip()
    where, cut = _word_cut(rest, 300)
    return (' · '.join(x for x in (head, first) if x), where + (' …' if cut else ''), read if cut or short != clause else '')


# What a pack zip leaves out of the location, reading and notes it shows (the catalog keeps it): a reader's local path
# (Reviewer B's card: '(image only in the Elsevier XML: object fx501, /private/tmp/.../fx501_lrg.jpg)'), a file inside a
# supplement archive ('word/media/image2.png') and CatLog's own files ('texts/123.supp.txt', 'papers/123.els.xml'; a
# supplement keeps the file name the journal gives it: 'papers/123_supp/Data_Sheet_1.PDF' -> 'Data_Sheet_1.PDF').
LOCAL_FILE = re.compile(r'(?P<pre>\b(?:of|in)\s+)?(?P<path>image only in the Elsevier XML:\s*object\s+[\w.-]+'
                        r'|(?:/private|/Users|/tmp|/var/folders|/Volumes|/home)/[^\s,;)\]]*'
                        r'|(?<![\w/.-])(?:word|xl|ppt)/[\w./-]+'
                        r'|(?<![\w/.-])(?:papers|texts|evidence_assets)/[^\s,;)\]"\']+|(?<![\w/.-])supp\.txt\b)')


def _no_local(text):
    """text without LOCAL_FILE's paths: 'OCR line of texts/1.supp.txt, in which' -> 'OCR line, in which'; one that starts
    a clause becomes 'the supplement text' / 'the paper text'; an aside left empty goes ('(checked in X)' -> '(checked)').

    >>> _no_local("Table I (image only in the Elsevier XML: object fx501, /private/tmp/x/fx501_lrg.jpg)")
    'Table I'
    >>> _no_local('Fig. S2b inset (41598_MOESM1_ESM.docx, word/media/image2.png); texts/7.supp.txt is an OCR')
    'Fig. S2b inset (41598_MOESM1_ESM.docx); the supplement text is an OCR'
    """
    if not text or not LOCAL_FILE.search(str(text)):
        return text
    s = str(text)

    def keep(m):
        path, pre = m.group('path'), m.group('pre') or ''
        supp = re.match(r'papers/[^/\s]+_supp/(.+)', path)
        if supp:
            return pre + supp.group(1)
        if path.startswith('texts/') and not pre and re.search(r'(?:^|[;.]\s)\s*$', s[:m.start()]):
            return 'the supplement text' if '.supp' in path else 'the paper text'
        return ''
    s = LOCAL_FILE.sub(keep, s)
    s = re.sub(r'\(\s*[,;]?\s*', '(', s)
    s = re.sub(r'\s*[,;]?\s*\)', ')', s)
    s = re.sub(r'\s*\(\)', '', s)
    s = re.sub(r'\s+([,;])', r'\1', re.sub(r'\s{2,}', ' ', s))
    return s.strip()


# game.js NO_UNIT: a CatLog note saying the paper prints no unit (the card's care line under the table)
NO_UNIT = re.compile(r'no (?:printed )?units?\b(?! (?:of|for) (?:the )?(?:Vmax|activity))|units? (?:is |are |was )?not printed'
                     r'|prints? no (?:\w+ )?units?|carr(?:y|ies) no (?:printed )?units?', re.I)
UNIT_PROSE = re.compile(r'(?i)\b(?:header|implied|prints?|printed|columns?|text|OCR|lost|footnote|legend|caption)\b')


def _unit_remark(raw):
    """(unit, remark): a reader's remark in brackets inside a printed unit, split off for the zip, which shows the unit in
    every cell and compares typed values with it (8639717: 'mM^-1 s^-1 (header prints no unit; implied by the KM (mM)
    and kcat (s-1) columns)'). A remark: a bracket of 4+ words, one like header, implied, prints, column, text, OCR or
    lost, and no power of ten. '(mmol of enzyme)', '(min pmol CYP)' and '(column header kcat·10^5)' stay in the unit.

    >>> _unit_remark('s^-1 M^-1 × 10^? (exponent lost in the OCR text)'), _unit_remark('s-1·(mmol of enzyme)-1')
    (('s^-1 M^-1 × 10^?', 'exponent lost in the OCR text'), ('s-1·(mmol of enzyme)-1', ''))
    """
    s, depth, start = str(raw or ''), 0, 0
    for i, ch in enumerate(s):
        if ch in '([':
            start, depth = (i if depth == 0 else start), depth + 1
        elif ch in ')]' and depth:
            depth -= 1
            inner = s[start + 1:i]
            if depth == 0 and len(re.findall(r'[A-Za-z]{2,}', inner)) >= 4 and UNIT_PROSE.search(inner) and not POW10.search(inner):
                return re.sub(r'\s{2,}', ' ', s[:start] + s[i + 1:]).strip(), inner.strip()
    return raw, ''


POW10 = re.compile(r'10\s*\^|[×x]\s*10|10[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]')  # a power of ten in a unit or a header: '× 10^3', '10⁻⁴'
MULT = re.compile(r'[(\[]?\s*(?:[×x*]\s*)?10\s*(?:\^\s*\{?\s*\(?\s*[-+−–]?\s*\d+\.?\s*\)?\s*\}?|⁻?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)\s*[)\]]?\s*[×x·•*]?')
HEADER = re.compile(r'(?i)(?<![a-z])k\s*_?\s*\{?\s*(?:cat|m|\d)(?![a-z])|^\s*[(\[]?\s*10\s*(?:\^\s*\{?\s*[-+−–]?\s*\d+\s*\}?|⁻?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)\s*[×x]')
# what a kcat unit must name: also 'seconds^-1', the French 'mn^-1' and 'kat·mol^-1' (katal per mol is s^-1)
TIME_Q = re.compile(r'(?i)(?<![a-z])(?:s|secs?|seconds?|min|mins|minutes?|mn|h|hrs?|hours?|kat)(?![a-z])')
CONC_Q = re.compile(r'[MΜ]|mol|(?<![A-Za-z])[munpµμ]?m(?![A-Za-z])')  # a Km unit: M, Greek Μ, mol; 'mm^-1', 'm^-1' (small capitals)
# or a mass concentration (polymer substrates: mg/ml, g/l, OCR 'mg/1'; their kcat/Km in ml/mg·s): a mass and a volume
MASS_Q = re.compile(r'(?i)(?<![a-z])[nuµμm]?g(?![a-z])')
VOL_Q = re.compile(r'(?i)(?<![a-z])[uµμmd]?l(?![a-z])|/\s*1(?![\d.])')


def _num(x):
    """A number as a reviewer reads it: 24,000 and 0.0034, not 2.4e+04; a very large or small one as a × 10^b.

    >>> [_num(x) for x in (24000, 0.000099999, 0.00004, 3.9e10)]  # python3 -m doctest tools/human_review.py
    ['24,000', '0.0001', '4 × 10^-5', '3.9 × 10^10']
    """
    if not x:
        return '0'
    r = float(f'{x:.4g}')  # round first: 0.000099999 rounds to 0.0001, which has no 'e' to split on
    if 1e-4 <= abs(r) < 1e9:
        return f'{r:,.10f}'.rstrip('0').rstrip('.')
    mant, _, ex = f'{r:.4g}'.partition('e')  # outside that range .4g always writes an exponent
    return f'{mant} × 10^{int(ex)}'


def _exp10(unit):
    """The power of ten a unit or header carries (-5 for '×10^-5 × min^-1'); None when it carries none."""
    import math
    from units import unit_scale
    mult = unit_scale(unit)[0] if POW10.search(unit or '') else None
    return round(math.log10(mult)) if mult else None


def _base(metric, unit, f, n):
    """unit without its power of ten, as printed ('M^-1 s^-1' of '(M^-1 s^-1) × 10^3'), when it converts by f / 10^n;
    else ''."""
    from units import normalize
    b = re.sub(r'\s+', ' ', MULT.sub(' ', unit or '', count=1)).strip(' ,;·×x*')
    while b.count('(') != b.count(')'):  # '(× 10^-5 × min^-1)' leaves 'min^-1)'
        b = b.replace('(' if b.count('(') > b.count(')') else ')', '', 1).strip()
    if re.fullmatch(r'\([^()]*\)', b):
        b = b[1:-1].strip()
    fb = normalize(metric, '1', b)[0] if b else None
    return b if fb and f and abs(fb / (f / 10 ** n) - 1) < 1e-9 else ''


def _arith(m, printed, v, raw, conv, f, cat):
    """The unit arithmetic a reviewer can redo. A power of ten in the printed unit or in CatLog's reading of it is
    always written out, even when it cancels (24 × 10^3 M^-1 s^-1 = 24 mM^-1 s^-1: the × 10^3 seemed to vanish), and
    a header that names the metric gets its meaning spelled out when CatLog read it that way."""
    unit = conv or raw
    n = _exp10(unit)
    if n is not None and f:
        base = _base(m, unit, f, n)
        h = _exp10(raw) if conv else None
        if base and HEADER.search(raw) and h is not None and h == -n != 0:  # '10^-4 × kcat (min^-1)': printed = kcat × 10^-4
            return (f"header '{raw}' means printed number = {m} × 10^{h}, so {m} = {printed:g} × 10^{n} {base} "
                    f"= {_num(v)} {cat}")
        if base:
            full = _num(printed * 10 ** n)  # no middle step in mM or s^-1 (already the stored unit) or as a × 10^b again
            mid = '' if abs(f / 10 ** n - 1) < 1e-9 or '×' in full else f'{full} {base} = '
            return f"{printed:g} × 10^{n} {base} = {mid}{_num(v)} {cat}"
    if f and abs(f - 1) > 1e-12:
        inv = 1 / f
        op = f'÷ {round(inv):g}' if f < 1 and abs(inv - round(inv)) < 1e-9 * inv else f'× {f:g}'
        return f"{printed:g} {unit} {op} = {v:.4g} {cat}"
    return f"{printed:g} {unit} = {_num(v)} {cat}" if POW10.search(raw) else ''  # CatLog's reading dropped the 10^n


def _has_quantity(metric, unit):
    """Does a printed unit name what the metric measures: a time for kcat, a concentration for Km, both for kcat/Km?

    >>> [_has_quantity('kcat', u) for u in ('seconds^-1', 'mn^-1', 'kat·mol^-1', 'µM')], _has_quantity('kcat/Km', 'ml/mg·s')
    ([True, True, True, False], True)
    """
    u = unit or ''
    t = bool(TIME_Q.search(u))
    c = bool(CONC_Q.search(u)) or bool(MASS_Q.search(u) and VOL_Q.search(u))
    return t if metric == 'kcat' else c if metric == 'Km' else t and c


def _check_lines(w, garbled=False, shown=False):
    """Per metric: what the paper prints, where (look_in: the table, row and column to open; then the rest of CatLog's
    own reading), the quote (control characters a PDF text layer leaves are shown as ¤), the stored value with the unit
    arithmetic, CatLog's note, and whether converting the stored value back to the printed unit gives the printed number
    (it does not when a table-header multiplier is involved). unit_read says how CatLog read a printed unit it did not
    take as printed: 'same' (it did), 'changed' (another value than the printed unit gives: literal, factor), 'multiplier'
    (a power of ten in either unit, which way it goes is the reviewer's check; literal and factor are the other way when
    the two exponents have opposite signs), 'quantity' (the printed unit lacks a time or concentration), 'spelling'.
    `shown` (what a pack zip carries): location, reading and note without _no_local's paths, and the unit without a
    reader's remark (_unit_remark), which goes to the note unless the note already says it; the rest is unchanged."""
    from units import normalize, parse_number
    units = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}
    stored = {'kcat': w.get('kcat'), 'Km': w.get('km'), 'kcat/Km': w.get('kcat_over_km')}
    out = []
    for m, e in (w.get('evidence') or {}).items():
        v = stored.get(m)
        raw, conv = e.get('raw_unit', '') or '', e.get('unit_for_conversion', '') or ''
        unit = conv or raw
        one, _, err = normalize(m, '1', raw)
        f, _, err2 = normalize(m, '1', unit)
        printed = parse_number(e.get('raw_value', ''))
        ok = None if err or not one or v is None or printed is None else abs(v / one - printed) <= 0.02 * abs(printed)
        arith = ''
        if isinstance(v, (int, float)) and f and not err2 and printed is not None:
            arith = _arith(m, printed, v, raw, conv, f, units[m])
        literal, factor, respelled, unit_read = '', None, False, 'same'
        if conv and conv != raw:
            lv, _, lerr = normalize(m, e.get('raw_value', ''), raw)
            if lerr or not lv or not isinstance(v, (int, float)):
                respelled = bool(lerr)  # the printed unit does not parse: CatLog read it as converted_as
            elif abs(v / lv - 1) <= 0.02:
                respelled = True  # the same value either way: a respelling (s^-1·mmol^-1·dm^3 = mM^-1 s^-1)
            else:
                literal, factor = f'{_num(lv)} {units[m]}', v / lv
            same_either = not lerr and lv and isinstance(v, (int, float)) and abs(v / lv - 1) <= 0.02
            if literal:
                unit_read = 'changed'
            elif same_either:
                unit_read = 'spelling'
            elif POW10.search(raw) or POW10.search(conv):  # '×10^-5 × min^-1' read as 10^5 min^-1: a 10^10-fold choice
                unit_read = 'multiplier'
                hr, hc = _exp10(raw), _exp10(conv)
                if hr and hc and hr * hc < 0 and isinstance(v, (int, float)):
                    other = v * 10.0 ** (-2 * hc)  # the same reading with the exponent's sign the other way
                    literal, factor = f'{_num(other)} {units[m]}', v / other
            elif not _has_quantity(m, raw):
                unit_read = 'quantity'  # a kcat printed in µM: CatLog supplied the unit
            else:
                unit_read = 'spelling'  # dm^3, Greek Μ, l.mol-1, mm^-1
        quote = re.sub(r'(?<=\d)[\x00-\x1f\x7f-\x9f](?=\.)', '', str(e.get('quote', '')))
        quote = re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', '¤', quote)
        read = str(((w.get('reasoning') or {}).get(m) or {}).get('read') or '')
        loc, shown_unit, note = e.get('location', ''), e.get('raw_unit', ''), (w.get('metric_notes') or {}).get(m, '')
        if shown:
            loc, read, note = _no_local(loc), _no_local(read), _no_local(note)
            shown_unit, remark = _unit_remark(shown_unit)
            said = ' '.join(remark.lower().split()) in ' '.join(str(note).lower().split()) or NO_UNIT.search(remark) and NO_UNIT.search(str(note))
            if remark and not said:
                note = f'{note}; {remark}' if note else remark
        look_in, where, where_full = _look_in(loc, read)
        out.append({'metric': m, 'raw_value': re.sub(r'[\x00-\x1f\x7f-\x9f]', '¤', str(e.get('raw_value', ''))), 'raw_unit': shown_unit,
                    'location': loc, 'quote': quote, 'look_in': look_in, 'where': where, 'where_full': where_full,
                    'converted_as': e.get('unit_for_conversion', ''), 'note': note,
                    'stored': f'{v:g} {units[m]}' if isinstance(v, (int, float)) else 'n/a', 'arith': arith, 'conversion_ok': ok,
                    'literal': literal, 'factor': factor, 'respelled': respelled, 'unit_read': unit_read})
    return out


ACCESS = HR / 'paper_access.json'  # cache (regenerable): pmid -> OpenAlex open-access facts (+ 'linkout': LinkOut's free copy)
EPMC_ROUTES = ('europepmc', 'pmc_cloud')  # the text came from Europe PMC or PMC: its Europe PMC page has the full text
LINKOUT_ROUTES = ('pubmed_linkout', 'openalex_oa')  # a free copy elsewhere (J-STAGE back issues): PubMed LinkOut names it
LINKOUT_SKIP = ('sabiork.h-its.org', 'antibodies.cancer.gov', 'assays.cancer.gov', 'ncbi.nlm.nih.gov')  # not the paper


def paper_access(pmids):
    """pmid -> {'access': 'free' | 'isu', 'free_url'}: can a reviewer open the paper without a subscription? Free when
    OpenAlex lists an open-access copy, CatLog got the text from Europe PMC or PMC (link: its Europe PMC page), or PubMed
    LinkOut lists a free full-text copy (J-STAGE back issues of J Biochem, Biosci Biotechnol Biochem, DMPK: OpenAlex calls
    them closed and Europe PMC has only their abstract); otherwise CatLog got it through ISU (OpenAthens, the Elsevier
    API, the browser on the ISU network), so it opens on campus or through the ISU VPN (the user, 2026-10-13: give
    reviewers papers they can open). OpenAlex and LinkOut answers are cached."""
    import urllib.request, urllib.parse
    cache = json.loads(ACCESS.read_text()) if ACCESS.exists() else {}
    want = [p for p in pmids if 'is_oa' not in cache.get(p, {}) or 'year' not in cache.get(p, {})]  # no OpenAlex answer yet
    ua = {'User-Agent': 'catlog-v2/1.0' + (f' (mailto:{CONTACT})' if CONTACT else '')}
    changed = False

    def fact(w):
        oa, best = w.get('open_access') or {}, w.get('best_oa_location') or {}
        return {'is_oa': oa.get('is_oa'), 'oa_status': oa.get('oa_status'), 'year': w.get('publication_year'),
                'free_url': best.get('pdf_url') or best.get('landing_page_url') or oa.get('oa_url') or ''}
    digits = [p for p in want if str(p).isdigit()]
    for i in range(0, len(digits), 50):
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request(
                'https://api.openalex.org/works?per-page=50' + (f'&mailto={CONTACT}' if CONTACT else '') + ''
                '&select=ids,open_access,best_oa_location,publication_year&filter=pmid:' + '|'.join(digits[i:i + 50]), headers=ua), timeout=60).read())
        except Exception:
            continue  # offline: the paper keeps CatLog's own route, asked again next build
        for w in d.get('results', []):
            cache.setdefault((w.get('ids') or {}).get('pmid', '').rsplit('/', 1)[-1], {}).update(fact(w))  # keeps 'linkout'
            changed = True
    route = {r['pmid']: r.get('text_source', '').split(':', 1)[0] for r in csv.DictReader(open(ROOT / 'papers.tsv'), delimiter='\t')}
    # LinkOut-only papers: their text came through a LinkOut copy, and Europe PMC shows only the abstract (102640:
    # inEPMC N, its DOI 'Subscription required'), so the free copy is the one LinkOut lists (the elink call fetch.linkout_pdf
    # makes). Only 'Full Text Sources' count: other 'free resource' links are databases (BioCyc came first for 9644256).
    ask = [p for p in pmids if str(p).isdigit() and route.get(p) in LINKOUT_ROUTES and 'linkout' not in cache.get(p, {})
           and not (cache.get(p, {}).get('is_oa') and cache.get(p, {}).get('free_url'))]
    for i in range(0, len(ask), 50):
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request(
                'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&cmd=llinks&retmode=json'
                '&tool=catlog' + (f'&email={CONTACT}' if CONTACT else '') + '&' + '&'.join(f'id={p}' for p in ask[i:i + 50]), headers=ua), timeout=60).read())
        except Exception:
            continue  # offline: no free copy known this build (the paper counts as ISU), asked again next build
        found = {str(x.get('id')): [o['url']['value'] for o in x.get('objurls', []) if 'free resource' in (o.get('attributes') or [])
                                    and 'Full Text Sources' in (o.get('categories') or [])
                                    and not any(h in urllib.parse.urlsplit(o['url']['value']).netloc for h in LINKOUT_SKIP)]
                 for ls in d.get('linksets', []) for x in ls.get('idurllist', [])}
        for p in ask[i:i + 50]:
            if p in found:  # PubMed answered for this paper: an empty list means no free copy
                cache.setdefault(p, {})['linkout'] = (found[p] or [''])[0]
                changed = True
    if changed:
        ACCESS.write_text(json.dumps(cache, indent=0))
    out = {}
    for p in pmids:
        c = cache.get(p) or {}
        out[p] = {'year': c.get('year')}  # OpenAlex's publication year (None: not known)
        if c.get('is_oa') and c.get('free_url'):
            out[p].update(access='free', free_url=c['free_url'])
        elif route.get(p) in EPMC_ROUTES and str(p).isdigit():
            out[p].update(access='free', free_url=f'https://europepmc.org/article/MED/{p}')
        elif route.get(p) in LINKOUT_ROUTES and c.get('linkout'):
            out[p].update(access='free', free_url=c['linkout'])
        else:
            out[p].update(access='isu', free_url='')  # no free copy anyone lists: a --free-only pack leaves it out
    return out


def _pdf_pages(pmids):
    """pmid -> pages in the PDF CatLog read (0: its text is not from a PDF on disk), so the page can tell a '[page image
    p.124]' that names the page number printed on the paper from one that names a PDF page (3264155: a 7-page PDF)."""
    from fetch import pdf_pages
    src = {r['pmid']: r.get('text_source', '').split(':', 1)[-1] for r in csv.DictReader(open(ROOT / 'papers.tsv'), delimiter='\t')}
    return {p: pdf_pages(src[p]) if src.get(p, '').endswith('.pdf') and Path(src[p]).exists() else 0 for p in pmids}


def _slug(who):
    return re.sub(r'[^a-z0-9]+', '-', who.lower()).strip('-')


def _split_arg(text):
    """--split 'Reviewer A:2000,Reviewer B' -> [('Reviewer A', 2000), ('Reviewer B', None)]."""
    out = []
    for part in filter(None, (p.strip() for p in str(text).split(','))):
        name, sep, count = part.rpartition(':')
        name, count = (name, count.strip()) if sep else (part, '')
        if count and not count.isdigit():
            sys.exit(f'--split {text!r}: "{part}" is not a name with a row count, like Reviewer A:2000')
        out.append((name.strip(), int(count) if count else None))
    return out


def _check_split(split, one=False):
    """[(name, rows), ..., (last name, rows or None)], or exit with what is wrong. `one`: a single name is fine (--papers:
    an add-on pack for one person)."""
    split = [(str(who).strip(), None if c in (None, '') else int(c)) for who, c in split]
    if len(split) < (1 if one else 2):
        sys.exit('--split needs two or more names (one reviewer with the whole pack: --for NAME, or --papers --split "NAME:N")')
    tags = [_slug(who) for who, _ in split]
    if not all(tags) or len(set(tags)) < len(tags):
        sys.exit(f"--split: every name needs letters or digits and the names must differ ({', '.join(w for w, _ in split)})")
    if any(c is None or c < 1 for _, c in split[:-1]) or (split[-1][1] is not None and split[-1][1] < 1):
        sys.exit('--split: every name but the last needs a row count of 1 or more, like "Reviewer A:2000,Reviewer B"')
    return split


GAME_HARD = ('read off a page image (scan)', 'value from supplementary material', 'value from a figure or the running text',
             'paper from before about 1990', 'paper without a PMID (DOI only)')  # a beginner cannot check these by eye
# (a µ-mangling PDF text layer is fine: a person reads the page, and 58 mM against a printed 58 µM is easy to spot;
# a number printed as 1.2 × 10^4 is fine too; a power of ten in the printed UNIT, a column header's, is not)


def _game_easy(issues, check):
    """A row a beginner can check on the game page (one printed number per card): none of GAME_HARD, no unit CatLog
    re-read or supplied, no column-header power of ten, no quote read off a page image, and every value in a main
    table ("Table 2", "Table 1B", "Table III", "Extended Data Table 1"; not the Methods, a footnote or a supplement)."""
    return (not set(issues or ()) & set(GAME_HARD)
            and not any(c.get('unit_read') in ('changed', 'multiplier', 'quantity') for c in check)
            and not any(re.search(r'10\s*\^|×|\bx ?10', str(c.get('raw_unit', ''))) for c in check)
            and not any(str(c.get('quote', '')).startswith('[page image') for c in check)
            and all(re.match(r'\s*(extended data\s+)?table\s*(ed)?([0-9]+|[IVXL]+|one|two|three|four|five|six)[A-Za-z]?\b',
                             str(c.get('location', '')), re.I)
                    and not re.search(r'suppl|\btable\s*s\d', str(c.get('location', '')), re.I) for c in check))


_SOURCES = {}  # pmid -> the file CatLog read (papers.tsv), filled once per run


def _scanned(pmid):
    """The paper's text is OCR of a scan (an Elsevier OCR text, or a PDF whose text layer is too thin, the test
    catlog.to_text uses before it runs OCR): its tables come through garbled, so not for the game page."""
    import catlog
    from fetch import thin
    tp = catlog.TEXTS / f'{pmid}.txt'
    if tp.exists() and '## OCR TEXT' in tp.read_text(errors='replace'):
        return True
    if not _SOURCES:
        _SOURCES.update({r['pmid']: r.get('text_source', '').split(':', 1)[-1] for r in csv.DictReader(open(ROOT / 'papers.tsv'), delimiter='\t')})
    src = _SOURCES.get(pmid, '')
    if not src.endswith('.pdf') or not Path(src).exists():
        return False
    text = subprocess.run(['pdftotext', '-layout', src, '-'], capture_output=True, text=True, errors='replace', timeout=120).stdout
    return len(text.strip()) < 2000 or thin(text, max(1, text.count('\f')))


def _split_cuts(pmids, split):
    """Where each reviewer's rows start (pmids: each row's paper, in pack order): the paper boundary nearest each
    running total of the counts, so a paper's rows never go to two people and the total does not drift; every
    reviewer gets at least one paper. The last reviewer takes the rest."""
    starts = [i for i in range(1, len(pmids)) if pmids[i] != pmids[i - 1]]  # rows where a new paper begins
    if len(starts) + 1 < len(split):
        sys.exit(f'only {len(starts) + 1} paper(s) in this pack: too few to split between {len(split)} people')
    cuts, want, j0 = [0], 0, -1
    for k, (_, count) in enumerate(split[:-1]):
        want += count
        last_ok = len(starts) - len(split) + 1 + k  # leave at least one paper for each reviewer after this one
        j0 = min(range(j0 + 1, last_ok + 1), key=lambda j: (abs(starts[j] - want), j))
        cuts.append(starts[j0])
    return cuts + [len(pmids)]


JUDGMENT_KINDS = ('kcat/Km differs from kcat / Km', 'apparent or Hill-fit value', 'unit with a multiplier or exponent',
                  'PDF text layer mangles symbols (µ read as m)', 'read off a page image (scan)',
                  'value from supplementary material', 'value from a figure or the running text',
                  'paper from before about 1990', 'sequence numbered differently (mature chain, PDB, primers)',
                  'second reader corrected a field')  # kinds of trouble (_issue_tests) that need judgment


def _harder(issues, check):
    """A row for an experienced reviewer (--hard; the user, 2026-10-29): one a beginner cannot check by eye (not _game_easy)
    or one with a kind of trouble that needs judgment (JUDGMENT_KINDS). A paper is harder when any of its rows is."""
    return not _game_easy(issues, check) or bool(set(issues or ()) & set(JUDGMENT_KINDS))


INFORMATIVE = ('kcat/Km differs from kcat / Km', 'a database lists another number', 'CatLog read the unit another way',
               'power of ten in the printed unit', 'read off a page image or OCR of a scan', 'second reader corrected a field')


def _informative(w, issues, check, ocr=False):
    """The checks a person helps most with that record w needs (--informative; the user, 2026-10-30: papers "that will
    help us"), rarest first, so the first is its main one; ocr: its paper's text is OCR of a scan (_scanned)."""
    return [lab for lab, hit in zip(INFORMATIVE, (
        'kcat/Km differs from kcat / Km' in issues,
        any((d or {}).get('status') == 'differs' for d in (w.get('database_check') or {}).values()),
        any(c.get('unit_read') in ('changed', 'multiplier', 'quantity') for c in check),
        any(re.search(r'10\s*\^|×|\bx ?10', str(c.get('raw_unit', ''))) for c in check),  # as _game_easy
        ocr or 'read off a page image (scan)' in issues,
        'second reader corrected a field' in issues)) if hit]


def _reading_key(w, text):
    """Where record w sits in its paper (text): its first value's location (Table 2 before Table 10), the quote's
    place in the text, enzyme, variant."""
    ev_ = list((w.get('evidence') or {}).values())
    loc_ = ev_[0].get('location', '') if ev_ else ''
    q = str(ev_[0].get('quote', ''))[:40] if ev_ else ''
    at = text.find(q) if q else -1
    return ([int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', loc_)], at if at >= 0 else 10 ** 9,
            w.get('enzyme_name', ''), w.get('mutation_signature') or '')


def _paper_plan(split, overlap):
    """--papers: ({(a, b): papers the pair shares}, {name: own papers}). Nobody shares more than floor(overlap x their
    count); the pairs take one paper each in turn while both partners have room, so the shares spread evenly (caps
    12, 5, 2 give 4, 1, 1). A count includes the shared papers."""
    import itertools
    room = {who: int(overlap * c + 1e-9) for who, c in split}
    pairs = dict.fromkeys(itertools.combinations([who for who, _ in split], 2), 0)
    while any(room[a] and room[b] for a, b in pairs):
        for a, b in pairs:
            if room[a] and room[b]:
                pairs[a, b] += 1; room[a] -= 1; room[b] -= 1
    pairs = {p: k for p, k in pairs.items() if k}
    return pairs, {who: c - sum(k for p, k in pairs.items() if who in p) for who, c in split}


def _paper_jobs(split, hard, pairs, own):
    """Who gets which papers, in this order: [(names, papers, harder?)]: each pair's shared papers first, then each
    name's own. With --hard, the hard name's pairs and own papers are harder ones, all others not (None: no --hard)."""
    h = lambda names: (hard in names) if hard else None
    return [(list(p), k, h(p)) for p, k in pairs.items()] + [([who], own[who], h([who])) for who, _ in split if own[who]]


PAPER_KIND = {True: 'harder papers', False: 'papers that are not harder', None: 'papers'}


def _assign_papers(papers, harder, jobs, what='this pack'):
    """papers (pack order) -> {pmid: [names]}: each job takes the next papers of its kind (harder or not, or any) in
    pack order; papers no job takes are left out. Exits saying how many there are when a kind runs short."""
    lists = {k: [p for p in papers if k is None or (p in harder) == k] for k in {k for _, _, k in jobs}}
    need = Counter()
    for _, k, h in jobs:
        need[h] += k
    short = [f'{need[h]} {PAPER_KIND[h]} needed, {len(lists[h])} in {what}' for h in lists if need[h] > len(lists[h])]
    if short:
        sys.exit(f"--papers: {'; '.join(short)}")
    owners, at = {}, Counter()
    for names, k, h in jobs:
        for p in lists[h][at[h]:at[h] + k]:
            owners[p] = names
        at[h] += k
    return owners


def pack(n=40, seed=None, cap=None, reviewers=(), gold=0, rebuild=None, send_to='', free_only=False, split=None, game=(),
         kinds_share=0.55, by_papers=False, hard_name='', overlap=0.0, rows_per_paper=0, informative=False, balanced=False, easier=False):
    """The next review pack of n measurements, none already reviewed or already sent: `gold` second opinions (values a
    reviewer already judged: v2-pack verdicts, then the earlier review's disagreements with v2, then its agreements),
    55% spread evenly over the kinds of trouble in _issue_tests (one per paper per round, so each kind reaches as many
    papers as it has), and the rest a plain random sample (its error rate is the catalog's); at most `cap` per paper
    (default: 5, or 3x the average when the pack is large). Every row records each kind of trouble it shows.
    One zip per reviewer (`reviewers`), each with that reviewer's name filled in and its own saved state.
    `rebuild` PACK_ID writes an existing pack again with today's page and row texts: the same rows and pack id, so a
    reviewer who already started keeps their saved work. Rows go in pack order: papers in a seeded random order, each
    paper's rows together, so a reviewer who stops after any number of rows has sent a random sample of papers.
    `send_to` (an email address or an upload link) is where reviewers send their results file: the README and the page
    say it wherever they say "send that file back"; a rebuild keeps the pack's own unless given.
    `free_only` takes every row (random, each kind of trouble, second opinions) from papers paper_access() calls free,
    so a reviewer at home opens each paper without ISU access (the user, 2026-10-14: reviewers working from home);
    the README and the page then leave out the campus/VPN advice. A rebuild keeps the pack's own flag.
    `split` [(name, rows), ..., (last name, None)] gives each name a zip of only their rows (the user, 2026-10-14: two
    reviewers, ~2,000 and ~1,000 rows): rows in pack order, cut at the paper boundary nearest each running count,
    the last name takes the rest. Each zip numbers its rows from 1 and fills in its name, which also keys the page's
    browser storage (two halves opened on one computer never mix); the record keys and pack id are the whole pack's, so
    ingest is unchanged. The pack index keeps the pack-wide order and adds each row's reviewer and reviewer_order; a
    rebuild keeps the split, each person's rows and their numbering (--split on a rebuild of an unsplit pack assigns its
    rows). Not with `reviewers` (--for: every named reviewer gets the whole pack).
    Every split zip opens the card page (tools/review_ui/game.html: one printed number per card, Yes / No / can't find,
    each row one click from the full page; the user, 2026-10-14: the full page is too dense). `game` names split
    reviewers who get its points and streak (a beginner) and, first, whole papers whose every row passes
    _game_easy, in pack order, up to their count; the other names split the remaining rows as above. Same results
    file and ingest. `kinds_share` (default 0.55) is the part of the pack spread over the kinds of trouble (the user,
    2026-10-14: three new reviewers, so 0.25: fewer hard rows, more plain random ones). The pool never takes a paper a reviewer already went through (an earlier review or another
    pack): nobody redoes work.
    `by_papers` (--papers; the user, 2026-10-29: three reviewers, counted in papers): the split counts are papers;
    whole papers are assigned in pack order and every paper nobody gets is left out of the pack. `hard_name` (--hard)
    gets only harder papers (_harder: a paper is harder when any of its eligible records is), the others only papers that
    are not; the index keeps `catalog_harder_share`, the records of harder papers among all eligible ones, so the headline
    weighs the two kinds as the catalog holds them (review_summary). `overlap` F (--overlap): a few papers go to
    two people (_paper_plan; harder ones in a pair with the hard name), first in both zips, for reviewer agreement; the
    index gives such a row `also` [second name] and `orders` {name: row number in that zip}. `rows_per_paper` M
    (--per-paper): papers drawn at random in proportion to their eligible records (within harder and other papers apart
    under --hard), then min(M, size) of each, why 'random (paper sample)', `paper_size` per record and
    `catalog_harder_share` in the index so the headline weights them back (review_summary). A rebuild keeps all of it;
    every row records `harder`. A --papers --split may name one person (an add-on pack). `informative` (--informative,
    with --hard and --per-paper): the hard name's papers are not drawn at random but are the harder papers whose
    records most need a person's check (_informative): per paper up to M records, flagged ones first, then the rest in
    reading order; papers ranked by flagged records taken, then their distinct flags, then the seeded random order. Why
    'issue: <main flag>' ('issue: none (same paper as flagged records)' for the rest): picked, so not in the headline.
    `balanced` (--balanced, an add-on pack for one name with --per-paper; the user, 2026-10-30: "do balanced" for one
    reviewer): half the person's papers harder, half not (the odd one harder), each half drawn at random as above;
    the headline weighs the two kinds by catalog_harder_share like a --hard pack. `easier` (--easier, the same one-name
    add-on; the user, 2026-11-06: Reviewer G, "same as Reviewer D or Reviewer E"): only papers that are not harder, drawn at random."""
    import catlog, random, shutil, zipfile
    if not UI.is_dir():
        sys.exit(f'review packs need the review page ({UI}), which this copy of CatLog leaves out')
    game = [str(g).strip() for g in game or () if str(g).strip()]
    hard_name, overlap, rows_per_paper = str(hard_name or '').strip(), float(overlap or 0), int(rows_per_paper or 0)
    if game and not split and not rebuild:
        sys.exit('--game NAME needs --split (the game page is for one named reviewer of a split pack)')
    if (hard_name or overlap or rows_per_paper) and not by_papers:
        sys.exit('--hard, --overlap and --per-paper go with --papers (the split counts papers)')
    if informative and not rebuild and not (hard_name and rows_per_paper):
        sys.exit('--informative goes with --papers --hard NAME --per-paper M (it picks that name\'s papers)')
    if balanced and not rebuild and not (by_papers and rows_per_paper and split and len(split) == 1 and not hard_name):
        sys.exit('--balanced goes with --papers --per-paper M and one --split name, without --hard (an add-on pack)')
    if easier and not rebuild and (balanced or not (by_papers and rows_per_paper and split and len(split) == 1 and not hard_name)):
        sys.exit('--easier goes with --papers --per-paper M and one --split name, without --hard or --balanced')
    if not 0 <= overlap < 1:
        sys.exit(f'--overlap {overlap}: a share of each person\'s papers from 0 to below 1, like 0.05')
    if by_papers and not rebuild:
        if not split or any(c is None for _, c in split):
            sys.exit('--papers needs --split with a paper count for every name, like "Reviewer C:250,Reviewer D:100,Reviewer E:50"')
        if game:
            sys.exit('--papers and --game together: the game page takes easy papers by rows; use one of them')
        if hard_name and hard_name not in {w for w, _ in split}:
            sys.exit(f'--hard {hard_name}: not a name in --split')
        if rows_per_paper and (float(kinds_share) or gold):
            sys.exit('--per-paper draws whole papers at random: use it with --kinds-share 0 and without --gold')
    if split:
        split = _check_split(split, one=by_papers)
        if game and (set(game) - {w for w, _ in split} or any(c is None for w, c in split if w in game)
                     or all(w in game for w, _ in split)):
            sys.exit('--game: each game name must be in --split with a row count, and at least one name must not be a game name')
        if reviewers:
            sys.exit('--for and --split together: --for gives each name the whole pack, --split gives each name only '
                     'their own rows; use one of them')
    wide = [json.loads(l) for l in open(ROOT / 'catlog_wide.jsonl') if l.strip()]
    PACKS.mkdir(parents=True, exist_ok=True)
    sent, sent_rows, sent_papers = set(), set(), set()
    for f in list(PACKS.glob('*.json')) + list((PACKS / 'withdrawn').glob('*.json')):
        if f.parent.name == 'withdrawn':
            continue
        idx_ = json.loads(f.read_text())
        if idx_.get('pack_kind') == 'databases' or 'records' not in idx_:  # a databases pack asks which number the paper
            continue  # prints, not approve/reject; a case-review index (cases-*.json) holds cases, not records
        for k, v in idx_['records'].items():
            sent.add(k); sent_rows |= set(v.get('row_ids', []))
            sent_papers.add(v.get('pmid'))  # the paper as the pack sent it, even if a re-read changed its record ids since
    rows_d = _decisions() if DECISIONS.exists() else []
    decided = {r['key'] for r in rows_d}
    decided_rows = {i for r in rows_d for i in r.get('row_ids', [])}
    # no paper a reviewer already went through (an earlier review, or a pack already sent): nobody redoes work (the
    # user, 2026-10-14: 251 of one reviewer's 1,750 rows sat on papers the earlier review had covered). --gold still
    # adds second opinions on purpose.
    seen_papers = ({r['pmid'] for r in rows_d if r.get('pmid')} | {w['pubmed_id'] for w in wide if w['measurement_id'] in sent}
                   | (sent_papers - {None, ''}))
    held = catlog.locked()  # the method paper's test set: never in a pack
    pool = [w for w in wide if w['measurement_id'] not in sent | decided and not set(w.get('row_ids', [])) & (sent_rows | decided_rows)
            and w['pubmed_id'] not in seen_papers and w['pubmed_id'] not in held
            and any(w.get(k) is not None for k in ('kcat', 'km', 'kcat_over_km'))]  # a mass-only measurement shows no value
    free = None  # --free-only: the catalog papers a reviewer opens without ISU access
    access_all = paper_access(sorted({w['pubmed_id'] for w in wide}))  # one call (cached): access and publication year
    if free_only:
        free = {p_ for p_, a in access_all.items() if a['access'] == 'free'}
        pool = [w for w in pool if w['pubmed_id'] in free]  # the kinds of trouble draw from the pool too
    glyph = {p_ for p_ in {w['pubmed_id'] for w in wide} if (catlog.TEXTS / f"{p_}.txt").exists()
             and (catlog.TEXTS / f"{p_}.txt").read_text(errors='replace')[:20].startswith('GLYPH WARNING')}
    rows_by_id = {json.loads(l)['row_id']: json.loads(l) for l in open(catlog.CATALOG) if l.strip()}
    natural = {w['measurement_id'] for w in wide if any(catlog.natural_form(rows_by_id[r]) for r in w.get('row_ids', []) if r in rows_by_id)}
    tests = _issue_tests(glyph, natural, {p_: a['year'] for p_, a in access_all.items()})
    issues = {w['measurement_id']: [lab for lab, t in tests if t(w)] for w in wide}
    seed = int(seed) if seed not in (None, '') else int(time.strftime('%Y%m%d'))
    rng = random.Random(seed)
    rng.shuffle(pool)
    papers = {w['pubmed_id'] for w in pool}
    cap = int(cap) if cap else max(5, round(3 * n / max(1, len(papers))))
    chosen, per_paper = {}, Counter()

    def take(w, why):
        chosen[w['measurement_id']] = (w, why); per_paper[w['pubmed_id']] += 1

    if by_papers and not rebuild:  # who gets how many papers (shared ones first), harder or not
        pairs, own = _paper_plan(split, overlap)
        jobs = _paper_jobs(split, hard_name, pairs, own)
        if balanced:  # one name: half its papers harder (the odd one), half not
            (who, k), = split
            jobs = [([who], k - k // 2, True), ([who], k // 2, False)]
        if easier:  # one name: only papers that are not harder, as the --hard packs gave everyone but the hard name
            (who, k), = split
            jobs = [([who], k, False)]
    size_of, harder_share, hard_paper = {}, None, set()  # each record's paper size (--per-paper); the harder share
    if (rows_per_paper or hard_name) and not rebuild:  # harder papers over the whole pool: the share the headline weighs by
        t0, rows_of, need = time.time(), defaultdict(list), Counter()
        for w in pool:
            rows_of[w['pubmed_id']].append(w)
        check_of = {w['measurement_id']: _check_lines(w) for w in pool}
        hard_row = {mid: _harder(issues[mid], c) for mid, c in check_of.items()}
        hard_paper = {p_ for p_, ws in rows_of.items() if any(hard_row[w['measurement_id']] for w in ws)}
        harder_share = round(sum(len(rows_of[p_]) for p_ in hard_paper) / max(1, len(pool)), 4)
        print(f"{'--per-paper' if rows_per_paper else '--hard'}: {len(pool):,} eligible records on {len(rows_of):,} papers; "
              f"{len(hard_paper):,} papers are harder, with {harder_share:.0%} of the records (sorted in {time.time() - t0:.0f} s)")
    if rows_per_paper and not rebuild:  # whole papers, drawn in proportion to their eligible records, M records of each
        for _, k, h in jobs:
            need[h] += k
        cap = rows_per_paper
        for h, k in sorted(need.items(), key=str):  # within harder and other papers apart (--hard), else all papers
            cands = sorted(p_ for p_ in rows_of if h is None or (p_ in hard_paper) == h)
            if len(cands) < k:
                sys.exit(f'--per-paper: {k} {PAPER_KIND[h]} needed, {len(cands)} left in the catalog')
            if informative and h:  # the hard name's papers: where a person's check helps most, not drawn at random
                t0, take_of, score, flags = time.time(), {}, {}, {}
                for p_ in cands:
                    ocr, tp = _scanned(p_), catlog.TEXTS / f'{p_}.txt'
                    text = tp.read_text(errors='replace') if tp.exists() else ''
                    for w in rows_of[p_]:
                        mid = w['measurement_id']
                        flags[mid] = _informative(w, issues[mid], check_of[mid], ocr)
                    ws = sorted(rows_of[p_], key=lambda w: (not flags[w['measurement_id']], _reading_key(w, text)))[:rows_per_paper]
                    take_of[p_] = ws
                    score[p_] = (sum(bool(flags[w['measurement_id']]) for w in ws), len({f for w in ws for f in flags[w['measurement_id']]}))
                tie = {p_: rng.random() for p_ in cands}
                top = sorted(cands, key=lambda p_: (-score[p_][0], -score[p_][1], tie[p_]))[:k]
                main_, every = Counter(), Counter()
                for p_ in top:
                    for w in take_of[p_]:
                        fl = flags[w['measurement_id']]
                        take(w, f"issue: {fl[0] if fl else 'none (same paper as flagged records)'}")
                        size_of[w['measurement_id']] = len(rows_of[p_])
                        main_[fl[0] if fl else 'none'] += 1; every.update(fl)
                print(f"--informative: {k} of {len(cands):,} harder papers, {sum(map(len, (take_of[p_] for p_ in top)))} records "
                      f"(flagged per paper: {', '.join(str(score[p_][0]) for p_ in top[:10])}{' ...' if k > 10 else ''}; "
                      f"{time.time() - t0:.0f} s); main flag: {', '.join(f'{f} {c}' for f, c in main_.most_common())}; "
                      f"every flag: {', '.join(f'{f} {c}' for f, c in every.most_common())}")
                continue
            # a weighted draw without replacement (key u^(1/size)): a paper's chance grows with its records
            for p_ in sorted(cands, key=lambda p_: rng.random() ** (1 / len(rows_of[p_])), reverse=True)[:k]:
                ws = rng.sample(rows_of[p_], min(rows_per_paper, len(rows_of[p_])))
                if p_ in hard_paper and not any(hard_row[w['measurement_id']] for w in ws):  # keeps one harder row
                    ws[-1] = rng.choice([w for w in rows_of[p_] if hard_row[w['measurement_id']]])
                for w in ws:
                    take(w, 'random (paper sample)'); size_of[w['measurement_id']] = len(rows_of[p_])

    if gold:  # second opinions: values a reviewer already judged; disagreements with v2 first, then agreements
        by_mid = {w['measurement_id']: w for w in wide if (free is None or w['pubmed_id'] in free) and w['pubmed_id'] not in held}
        mid_of = {r: w['measurement_id'] for w in wide for r in w.get('row_ids', [])}
        prior = [(r['key'], 'second opinion: a reviewer judged this v2 value')
                 for r in sorted((r for r in rows_d if r.get('row_ids') and r['key'] in by_mid),
                                 key=lambda r: (r['status'] != 'rejected', not r.get('disagree'), rng.random()))]
        order = {'v2_different_value': 0, 'v2_has_same': 1, 'agree': 2}
        earlier = sorted({(mid_of[x['v2_row_id']], x['bucket']) for x in _read_compare()
                          if x['bucket'] in order and x['v2_row_id'] in mid_of}, key=lambda t: (order[t[1]], rng.random()))
        say = {'v2_different_value': 'the earlier review approved a different number for this slot',
               'v2_has_same': 'the earlier review rejected this number', 'agree': 'the earlier review approved this number'}
        for mid, why in prior + [(m, f'second opinion: {say[b]}') for m, b in earlier]:
            if len(chosen) >= int(gold):
                break
            if mid not in chosen and mid in by_mid and per_paper[by_mid[mid]['pubmed_id']] < min(cap, 5):  # spread over papers
                take(by_mid[mid], why)
    quota = max(1, round(float(kinds_share) * n / len(tests))) if float(kinds_share) else 0  # --kinds-share: 0.25 when most reviewers get easy rows  # each kind of trouble its own share; the rest a plain random sample
    for lab, _ in tests:
        cands = defaultdict(list)
        for w in pool:
            if lab in issues[w['measurement_id']] and w['measurement_id'] not in chosen:
                cands[w['pubmed_id']].append(w)
        got, order_ = 0, sorted(cands, key=lambda p_: (per_paper[p_], rng.random()))
        while got < quota and any(cands.values()):
            for p_ in order_:  # one per paper per round: as many papers as the kind has
                if got >= quota:
                    break
                if cands[p_] and per_paper[p_] < cap:
                    take(cands[p_].pop(), f'issue: {lab}'); got += 1
                elif cands[p_]:
                    cands[p_] = []
    for w in ([] if rows_per_paper else pool):  # the plain random sample: proportional to the catalog, so its error rate is the catalog's
        if len(chosen) >= n:
            break
        if w['measurement_id'] not in chosen and per_paper[w['pubmed_id']] < cap:
            take(w, 'random (proportional)')
    old_order, kept = {}, {}
    if rebuild:  # the same rows again (a measurement whose id changed is found by its catalog rows)
        idx_p = PACKS / f'{rebuild}.json'
        if not idx_p.exists():
            sys.exit(f'{rebuild}: withdrawn, not rebuilt' if (PACKS / 'withdrawn' / f'{rebuild}.json').exists()
                     else f'{rebuild}: no such pack index in {PACKS}')
        old = json.loads(idx_p.read_text())
        if old.get('pack_kind') == 'databases':
            sys.exit(f'{rebuild} is a databases pack (review dbpack), not a review pack: it is not rebuilt here')
        if old.get('split'):  # each person keeps their rows: a rebuild never moves rows between people
            between = ' and '.join(w for w, _ in old['split'])
            if reviewers:
                sys.exit(f'{rebuild} is split between {between}: rebuild it without --for')
            if split and [list(x) for x in split] != [list(x) for x in old['split']]:
                sys.exit(f'{rebuild} is already split between {between}: rebuild it without --split')
            if game and sorted(game) != sorted(old.get('game', [])):
                sys.exit(f"{rebuild} has the game page for {', '.join(old.get('game', [])) or 'nobody'}: rebuild it without --game")
            for flag, new, was in (('--papers', by_papers, bool(old.get('papers_split'))), ('--hard', hard_name, old.get('hard', '')),
                                   ('--overlap', overlap, old.get('overlap', 0)), ('--per-paper', rows_per_paper, old.get('per_paper', 0)),
                                   ('--informative', informative, bool(old.get('informative'))),
                                   ('--balanced', balanced, bool(old.get('balanced'))),
                                   ('--easier', easier, bool(old.get('easier')))):
                if new and new != was:
                    sys.exit(f"{rebuild} keeps how it was built ({flag}: {was or 'not used'}): rebuild it without {flag}")
            split, game = [tuple(x) for x in old['split']], old.get('game', [])
            by_papers, hard_name, overlap = bool(old.get('papers_split')), old.get('hard', ''), old.get('overlap', 0)
            informative, balanced, easier = bool(old.get('informative')), bool(old.get('balanced')), bool(old.get('easier'))
            rows_per_paper, harder_share = old.get('per_paper', 0), old.get('catalog_harder_share')
            # each name's row number in its own zip, the first reviewer first (a shared row: 'also' and 'orders')
            kept = {mid: {v['reviewer']: v.get('reviewer_order') or 0, **(v.get('orders') or {})} for mid, v in old['records'].items()}
        elif by_papers:
            sys.exit(f'{rebuild} was not built with --papers: --papers, --hard, --overlap and --per-paper make a new pack')
        elif game and not split:
            sys.exit(f'{rebuild} is not split: --game needs --split')
        elif split and old.get('reviewers'):
            sys.exit(f"{rebuild} was made for {', '.join(old['reviewers'])} (--for, the whole pack each): it cannot be split")
        if reviewers and sorted(reviewers) != sorted(old.get('reviewers', [])):
            sys.exit(f"{rebuild} was made for {', '.join(old.get('reviewers', [])) or 'no named reviewer'}: rebuild it without --for")
        if free_only and not old.get('free_only'):  # a rebuild keeps its rows, so it cannot become free-only
            sys.exit(f'{rebuild} was not made with --free-only: rebuild it without --free-only, or make a new pack with it')
        by_mid = {w['measurement_id']: w for w in wide}
        by_row = {r: w for w in wide for r in w.get('row_ids', [])}
        chosen, lost = {}, 0
        for mid, v in old['records'].items():  # (old_order: the order reviewers already work in)
            w = by_mid.get(mid) or next((by_row[r] for r in v.get('row_ids', []) if r in by_row), None)
            if w is None:
                lost += 1
                continue
            chosen[mid] = (w, v.get('why', ''))  # keyed by the pack's own id: saved decisions point at it
            old_order[mid] = v.get('pack_order')
            if v.get('paper_size'):
                size_of[mid] = v['paper_size']
        seed, cap = old.get('seed', seed), old.get('cap', cap)
        reviewers = [] if split else reviewers or old.get('reviewers', [])  # a split pack's index lists its names too
        send_to, free_only = send_to or old.get('send_to', ''), bool(old.get('free_only'))
        if lost:
            print(f'{lost} row(s) of {rebuild} are no longer in the catalog (dropped by an audit?): left out')
    if not chosen:
        sys.exit('nothing left to send: every v2 measurement is reviewed or already in a pack')
    pack_id = rebuild or f"v2-{time.strftime('%Y%m%d')}-{hashlib.sha1(' '.join(sorted(chosen)).encode()).hexdigest()[:8]}"
    fmt = lambda v, u: f'{v:g} {u}' if isinstance(v, (int, float)) else 'n/a'
    order_rng = random.Random(int(seed) + 1)  # pack order: papers shuffled, each paper's rows together, in reading order
    pmids = sorted({w['pubmed_id'] for w, _ in chosen.values()})
    order_rng.shuffle(pmids)
    paper_rank, texts = {p_: i for i, p_ in enumerate(pmids)}, {}

    def reading_order(item):
        w = item[1][0]
        if w['pubmed_id'] not in texts:
            tp = catlog.TEXTS / f"{w['pubmed_id']}.txt"
            texts[w['pubmed_id']] = tp.read_text(errors='replace') if tp.exists() else ''
        return (paper_rank[w['pubmed_id']], *_reading_key(w, texts[w['pubmed_id']]))
    ordered = sorted(chosen.items(), key=lambda it: (old_order.get(it[0]) or 10 ** 9, reading_order(it)))
    harder_of = {mid: _harder(issues.get(w['measurement_id'], []), _check_lines(w)) for mid, (w, _) in chosen.items()}
    owners = {}  # a split pack: mid -> its people ([first, second] for a paper --overlap shares)
    if by_papers and not kept:  # whole papers to each person in pack order; papers nobody gets leave the pack
        # --hard: a paper is harder when any of its eligible records is (hard_paper), as catalog_harder_share counts
        by_paper = _assign_papers(list(dict.fromkeys(w['pubmed_id'] for _, (w, _) in ordered)), hard_paper, jobs)
        ordered = [it for it in ordered if it[1][0]['pubmed_id'] in by_paper]
        chosen, pmids = dict(ordered), [p_ for p_ in pmids if p_ in by_paper]
        owners = {mid: by_paper[w['pubmed_id']] for mid, (w, _) in ordered}
    records, details, index = [], {}, {}
    access = access_all or paper_access(sorted({w['pubmed_id'] for w, _ in chosen.values()}))
    pdf_pages = _pdf_pages({w['pubmed_id'] for w, _ in chosen.values()  # only papers with a table read off a page picture
                            if any(re.match(r'\s*\[page image', str(e.get('quote', ''))) for e in (w.get('evidence') or {}).values())})
    for i, (mid, (w, why)) in enumerate(ordered):
        ev = w.get('evidence') or {}
        shard = f'data/details-{i // 100:03d}.js'
        garbled = any(k in issues.get(w['measurement_id'], []) for k in ('PDF text layer mangles symbols (µ read as m)', 'read off a page image (scan)'))
        printed = lambda m: f" (printed {ev[m]['raw_value']} {_unit_remark(ev[m]['raw_unit'])[0]})" if m in ev else ''
        loc = '; '.join(sorted({_no_local(e.get('location', '')) for e in ev.values() if e.get('location')}))
        conds = ', '.join(x for x in (f"pH {w['ph']:g}" if w.get('ph') is not None else '',
                                      f"{w['temperature_c']:g} °C" if w.get('temperature_c') is not None else '') if x)
        variant = w.get('mutation_signature') or 'wild type'
        read_as = w['substrate_full_name'] if w.get('substrate_full_name') and _name(w['substrate_full_name']) != _name(w.get('substrate_name')) else ''
        ec_note = (f"EC {w['ec_number']} (not printed in the paper; from the databases)" if w.get('ec_number')
                   and str(w.get('ec_source', '')).startswith('databases') else '')
        records.append({'record_key': mid, 'measurement_key': mid, 'review_key': mid, 'pubmed_id': w['pubmed_id'],
                        'doi': w.get('doi', ''), 'location': loc, 'variant': w.get('mutation_signature') or 'wild type',
                        'conditions_short': conds, 'why_short': '', 'pack_order': i + 1,
                        'paper_access': access[w['pubmed_id']]['access'],
                        'enzyme_display_name': w.get('enzyme_name', ''), 'enzyme_label_source': 'paper', 'ec_number': w.get('ec_number', ''),
                        'organism': w.get('organism', ''), 'substrate_name': w.get('substrate_name', '') + (f" (fixed: {w['cosubstrate']})" if w.get('cosubstrate') else ''),
                        'kcat': w.get('kcat'), 'km': w.get('km'), 'kcat_over_km': w.get('kcat_over_km'),
                        'kcat_display': fmt(w.get('kcat'), 's^-1') + printed('kcat') if w.get('kcat') is not None else 'n/a',
                        'km_display': fmt(w.get('km'), 'mM') + printed('Km') if w.get('km') is not None else 'n/a',
                        'kcat_over_km_display': fmt(w.get('kcat_over_km'), 'mM^-1 s^-1') + printed('kcat/Km')
                        if 'kcat/Km' in ev and w.get('kcat_over_km') is not None else 'n/a',  # a derived one is not in the paper
                        'verification_status': 'verified', 'evidence_confidence_tier': 'paper_grounded',
                        'source_db': 'catlog-v2',  # why a row was picked stays in the pack index: shown, it anchors the reviewer
                        'literature_id_count': 1, 'primary_uniprot_id': w.get('uniprot_id', ''),
                        'identity_resolution_state': 'resolved' if w.get('uniprot_id') else 'unresolved', 'detail_shard': shard,
                        '_search_text': ' '.join(str(w.get(k, '')) for k in ('pubmed_id', 'doi', 'enzyme_name', 'organism', 'substrate_name', 'mutation_signature')).lower()})
        details.setdefault(shard, {})[mid] = {
            'pubmed_id': w['pubmed_id'], 'doi': w.get('doi', ''), 'supporting_pmids': [w['pubmed_id']],
            'supporting_dois': [w['doi']] if w.get('doi') else [], 'title': w.get('title', ''), 'check': _check_lines(w, garbled, shown=True),
            'paper_access': access[w['pubmed_id']]['access'], 'free_url': access[w['pubmed_id']]['free_url'],
            'pdf_pages': pdf_pages.get(w['pubmed_id'], 0),  # a '[page image p.N]' past it is a printed page number
            'garbled': garbled or any('¤' in c['quote'] for c in _check_lines(w, garbled)),
            'substrate': w.get('substrate_name', ''),
            'variant_line': f"variant: {variant} · substrate{' (varied)' if w.get('cosubstrate') else ''}: {w.get('substrate_name', '')}"
                            + (f" (read as {read_as})" if read_as else '')
                            + (f" · fixed: {w['cosubstrate']}" if w.get('cosubstrate') else '') + f" · organism: {w.get('organism', '')}"
                            + (f" · {ec_note}" if ec_note else '') + (f" · construct: {w['construct']}" if w.get('construct') else ''),
            'conditions_line': f"conditions: {conds or 'pH and temperature not stated'}; {w.get('conditions') or ''}",
            # the same facts as labelled fields, so the page shows them in a fixed order a reviewer can learn (the two
            # lines above: kept as they were, the page's fallback)
            'ctx': {'variant': variant, 'variant_long': _variant_long(w.get('mutation_signature')),
                    'substrate': w.get('substrate_name', ''), 'substrate_read_as': read_as, 'fixed': w.get('cosubstrate') or '',
                    'organism': w.get('organism', ''), 'ec_note': ec_note, 'construct': w.get('construct') or '',
                    'ph_temp': ' · '.join((f"pH {w['ph']:g}" if w.get('ph') is not None else 'pH not stated',
                                           f"{w['temperature_c']:g} °C" if w.get('temperature_c') is not None else 'temperature not stated'))
                    if conds else 'pH and temperature not stated', 'assay': w.get('conditions') or ''},
            'mutation_signature': w.get('mutation_signature') or 'wild type', 'wild_type': w.get('wild_type'),
            'uniprot_id': w.get('uniprot_id', ''), 'sequence': w.get('sequence', ''), 'canonical_sequence': _wild_type(w),
            'sequence_source': w.get('sequence_basis', ''), 'sequence_confirmation': w.get('sequence_check', ''),
            'proof_lines': [f"{m}: {e.get('raw_value')} {_unit_remark(e.get('raw_unit'))[0]} | {_no_local(e.get('location'))}: \"{e.get('quote')}\"" for m, e in ev.items()],
            'literature_linkage': ((f"https://pubmed.ncbi.nlm.nih.gov/{w['pubmed_id']}/" if str(w['pubmed_id']).isdigit() else '')
                                   + (f"  https://doi.org/{w['doi']}" if w.get('doi') else '')).strip(),  # NP...: no PMID, the DOI is the paper
            'next_best_action': 'Open the paper; check each value, its unit, enzyme, variant and substrate at the quoted place',
            'next_best_action_reason': '', 'notes': {m: _no_local(n) for m, n in (w.get('metric_notes') or {}).items()},
            'ratio_check': w.get('ratio_check', ''),
            # no verifier note and no database check: both are verdicts, and a reviewer shown one leans on it
            'measurement_id': mid, 'row_ids': w.get('row_ids', [])}
        index[mid] = {'pack_id': pack_id, 'pmid': w['pubmed_id'], 'row_ids': w.get('row_ids', []), 'why': why,
                      'issues': issues.get(w['measurement_id'], []), 'pack_order': i + 1, 'harder': harder_of[mid],
                      **({'paper_size': size_of[mid]} if mid in size_of else {}),
                      **({'shared_with': old['records'][mid]['shared_with']}  # a paper another pack holds too
                         if rebuild and (old['records'].get(mid) or {}).get('shared_with') else {})}
    tier = lambda why: why.split(':')[0].split('(')[0].strip()
    tiers = Counter(tier(why) for _, why in chosen.values())
    groups = [(who, ordered) for who in (list(reviewers) or [''])]  # --for: every named reviewer gets the whole pack
    detail_of_ = {mid: d for rows_ in details.values() for mid, d in rows_.items()}
    if split:  # each name only their rows, in pack order (a rebuild: each person's rows and numbering as before)
        if kept:
            owners = {mid: list(kept[mid]) for mid, _ in ordered}
        elif not by_papers:  # (--papers: owners above)
            who_of, rest_ = {}, ordered
            if game:  # game reviewers first: whole easy papers, in pack order, up to each one's count
                paper_rows = defaultdict(list)
                for mid, (w, _) in ordered:
                    paper_rows[w['pubmed_id']].append(mid)
                easy = [p_ for p_ in dict.fromkeys(w['pubmed_id'] for _, (w, _) in ordered) if access[p_]['access'] == 'free'
                        and all(_game_easy(index[m]['issues'], detail_of_[m]['check']) for m in paper_rows[p_])]
                # when easy papers run out: the mildest others (no scan, no unit CatLog re-read; e.g. a value in the
                # text or an old typeset paper; the user, 2026-10-14: more rows for an experienced reviewer)
                mild = [p_ for p_ in dict.fromkeys(w['pubmed_id'] for _, (w, _) in ordered) if p_ not in easy
                        and access[p_]['access'] == 'free' and all(
                            'read off a page image (scan)' not in index[m]['issues']
                            and not any(c.get('unit_read') in ('changed', 'multiplier', 'quantity')
                                        or str(c.get('quote', '')).startswith('[page image') for c in detail_of_[m]['check'])
                            for m in paper_rows[p_])]
                for who, count in split:
                    if who not in game:
                        continue
                    got = 0
                    for tier_ in (easy, mild):
                        for p_ in tier_:
                            k_ = len(paper_rows[p_])
                            if (p_ not in {index[m]['pmid'] for m in who_of} and got < count and count - got >= k_ / 2
                                    and not _scanned(p_)):
                                who_of.update({m: who for m in paper_rows[p_]}); got += k_
                    if got < count:
                        print(f'{who}: only {got} rows a beginner can check in this pack (asked for {count})')
                rest_ = [it for it in ordered if it[0] not in who_of]
            plain = [x for x in split if x[0] not in game]
            cuts = _split_cuts([w['pubmed_id'] for _, (w, _) in rest_], plain)
            who_of.update({mid: who for k, (who, _) in enumerate(plain) for mid, _ in rest_[cuts[k]:cuts[k + 1]]})
            owners = {mid: [who] for mid, who in who_of.items()}

        def mine(who):  # shared papers first, then the rest, each in pack order (a stable sort); a rebuild: as before
            items = [it for it in ordered if who in owners[it[0]]]
            return sorted(items, key=lambda it: kept[it[0]].get(who, 0) if kept else len(owners[it[0]]) < 2)
        groups = [(who, mine(who)) for who, _ in split]
        at = defaultdict(dict)  # mid -> {name: row number in that name's zip}
        for who, items in groups:
            for j, (mid, _) in enumerate(items):
                at[mid][who] = j + 1
        for mid, o in at.items():
            index[mid].update(reviewer=owners[mid][0], reviewer_order=o[owners[mid][0]])
            if len(owners[mid]) > 1:  # shared (--overlap): nothing in either zip says so
                index[mid].update(also=owners[mid][1:], orders={w: o[w] for w in owners[mid]})
        # each person's own zip only: an earlier whole-pack zip (a rebuild that adds the split) is never sent by mistake
        shutil.rmtree(PACKS / pack_id, ignore_errors=True)
        (PACKS / f'catlog-v2-human-review-{pack_id}.zip').unlink(missing_ok=True)
    record_of, detail_of = {r['record_key']: r for r in records}, {mid: d for rows_ in details.values() for mid, d in rows_.items()}
    zips = []
    for who, items in groups:
        records, details = [], {}  # this zip's rows, numbered from 1 in its own order (a split zip: one person's rows)
        for j, (mid, _) in enumerate(items):
            shard = f'data/details-{j // 100:03d}.js'
            records.append({**record_of[mid], 'pack_order': j + 1, 'detail_shard': shard})
            details.setdefault(shard, {})[mid] = detail_of[mid]
        zip_pmids = {r['pubmed_id'] for r in records}
        mine = Counter(tier(why) for _, (_, why) in items)
        zip_tiers = {k: mine[k] for k in tiers if mine[k]}  # in the pack's own order
        others = [f'{w} with {len(it):,} rows' for w, it in groups if w != who] if split else []
        all_free = all(access[p_]['access'] == 'free' for p_ in zip_pmids)  # no row needs ISU access: no campus/VPN advice
        access_note = ('Every paper in this pack is free to read: o opens a free copy, no ISU login or VPN needed.' if all_free else
                       'Papers marked "Free to read" open anywhere (o opens the free copy); papers marked "ISU access" open\n'
                       '   on the ISU campus network or through the ISU VPN (connect the VPN first when you work from home).')
        tag = _slug(who)
        out = PACKS / (pack_id + (f'-{tag}' if tag else ''))
        shutil.rmtree(out, ignore_errors=True)  # regenerated whole: a shard an earlier build wrote must not ride along
        for d in (out / 'assets', out / 'data'):
            d.mkdir(parents=True, exist_ok=True)
        for src, dst in (('index.html', 'index.html'), ('open-human-review.html', 'Open Human Review.html'),
                         ('catlog-static.css', 'assets/catlog-static.css'), ('human-review.css', 'assets/human-review.css'),
                         ('human-review.js', 'assets/human-review.js')):
            shutil.copyfile(UI / src, out / dst)
        if split:  # every split zip opens the card page (the user, 2026-10-14: the full page is too dense); index.html stays
            for src in ('game.html', 'game.js', 'game.css'):
                shutil.copyfile(UI / src, out / src)
            launcher = (UI / 'open-human-review.html').read_text()
            assert launcher.count('index.html') >= 2, 'open-human-review.html no longer names index.html'
            (out / 'Open Human Review.html').write_text(launcher.replace('index.html', 'game.html'))
        for k in range(0, len(records), 500):
            (out / f'data/records-{k // 500:03d}.js').write_text(
                'window.CATLOG_RECORD_CHUNKS = window.CATLOG_RECORD_CHUNKS || [];\n'
                f'window.CATLOG_RECORD_CHUNKS.push({json.dumps(records[k:k + 500], ensure_ascii=False)});\n')
        for shard, rows_ in details.items():
            (out / shard).write_text('window.CATLOG_DETAIL_SHARDS = window.CATLOG_DETAIL_SHARDS || {};\n'
                                     f'window.CATLOG_DETAIL_SHARDS[{json.dumps(shard)}] = {json.dumps(rows_, ensure_ascii=False)};\n')
        manifest = {'name': 'CatLog v2 Human Review Pack', 'pack_id': pack_id, 'assigned_reviewer': who or None,
                    'send_to': send_to or None,  # where results files go; the page appends it to "send that file back"
                    **({'page': 'game' if who in game else 'cards'} if split else {}),  # points and streak only on 'game'
                    'free_only': all_free,  # every paper opens free (a --free-only pack): the page leaves out ISU/VPN advice
                    # a split pack: who has how many rows (this zip holds only its reviewer's; the page drops "sharing" advice)
                    **({'split': [[w, len(it)] for w, it in groups]} if split else {}),
                    'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                    'review_scope': {'label': 'CatLog v2 measurements: second opinions, each kind of trouble, and a plain random sample',
                                     'included_verification_statuses': ['verified'], 'human_status_field': 'human_review_status',
                                     'decision_values': ['human_approved', 'human_rejected'], 'rejection_comment_required': True},
                    'source_file': 'catlog_wide.jsonl', 'source_sha256': hashlib.sha256(pack_id.encode()).hexdigest(),
                    'source_total_rows': len(wide), 'total_rows': len(records),
                    'record_chunks': [f'data/records-{k // 500:03d}.js' for k in range(0, len(records), 500)],
                    'detail_shards': sorted(details),
                    'summary': {'totals': {'records': len(records), 'source_records': len(wide)},
                                'review_scope': 'catlog_v2_sample', 'status_counts': {'verified': len(records)},
                                'evidence_tier_counts': {'paper_grounded': len(records)}, 'source_counts': zip_tiers}}
        (out / 'data' / 'manifest.js').write_text(f'window.CATLOG_STATIC_MANIFEST = {json.dumps(manifest, ensure_ascii=False)};\n'
                                                  'window.CATLOG_RECORD_CHUNKS = window.CATLOG_RECORD_CHUNKS || [];\n'
                                                  'window.CATLOG_DETAIL_SHARDS = window.CATLOG_DETAIL_SHARDS || {};\n')
        head = f"CatLog v2 review pack {pack_id}{f' for {who}' if who else ''}"
        if split and others:  # one person's rows: say who has the others, and leave out the advice on sharing one pack
            rest = others[0] if len(others) == 1 else f"{', '.join(others[:-1])} and {others[-1]}"
            head += (f": {len(records):,} rows from {len(zip_pmids):,} papers ({rest} "
                     f"{'has' if len(others) == 1 else 'have'} the rest of this pack)")
        start = ('Start at row 1: these rows\n   are yours alone, nobody else has them.' if split else
                 'Start at row 1. If you share the pack,\n   type the rows you agreed on in "My rows" at the top (next to your name; see 5).')
        carry_on = ('and carry on. Next time you open the page, it continues where you stopped.' if split else
                    'and carry on. Sharing one pack with others: agree on row ranges (1-1000, 1001-2000, ...) and type yours in "My rows\n'
                    '   (if you share the pack)" at the top, next to your name: j and k then stop at the ends of your range, deciding a row\n'
                    '   outside it asks first, and the page tells you when your rows are done (or which ones you skipped). Next time you\n'
                    '   open the page, it continues where you stopped.')
        if split:  # the card page: a short README in plain words
            (out / 'README_FIRST.txt').write_text(f"""CatLog review for {who}: {len(records):,} rows from {len(zip_pmids):,} papers

1. Unzip the folder first (right-click > Extract All; on a Mac double-click the zip), then open "Open Human Review.html"
   in Chrome or Edge (not a private window).
2. Each card shows the numbers CatLog copied from one table of a science paper (up to 8 rows) and where to look.
   Open the paper (button or key o), put it beside the page, compare, then press
   1 = Yes, every number matches · 2 = Some differ (click each one that differs, type what the paper shows) ·
   3 = I can't find them. Not sure? Press 3. B goes back one card.{' Every paper in this pack is free to read.' if all_free else ' Papers marked "ISU access" open on the ISU campus network or through the ISU VPN (connect the VPN first when you work from home); "Free to read" ones open anywhere.'}
   Is the enzyme, substrate, variant or pH wrong, or do you want every detail of a row? The link under the buttons
   opens that row on the full page (both pages save to the same place).
3. Your work saves in this browser by itself. Every 50 rows the page asks you to save your results file: click "Save my
   work" and {f'email that .json file to {send_to}' if '@' in send_to and '://' not in send_to else f'upload that .json file at {send_to}' if send_to else 'send that .json file back'}. Each file holds everything so far, so a newer
   file replaces the older one. Do not clear the browser's history or data until your last file is sent.
4. On another computer: open the pack there, click "Load my saved file", pick your latest results file, carry on.
""")
        else:
            (out / 'README_FIRST.txt').write_text(f"""{head}

1. Unzip the whole folder first (right-click > Extract All), then open "Open Human Review.html" in Chrome or Edge, not
   in a private/incognito window. Type your name at the top and press Enter (once).
2. Rows are in pack order: each paper's rows together, papers in random order. {start} Each row is one measurement (kcat,
   Km, kcat/Km of one enzyme, variant, substrate and assay). The box "Check this measurement" starts with "Look in"
   (the table, row and column to open), then what changed since the row before, then the same lines in the same
   order on every row: Variant (E272A also as Glu272→Ala: papers print either), Substrate measured, Held fixed (rows
   with two substrates), pH · °C, and the quoted line with the number highlighted; under it how the stored value was
   converted, and in smaller print the rest of CatLog's reading, the organism and the assay. The quote is CatLog's own
   copy, so it always matches; you check it against the PDF page.
   Press o (or click PubMed / DOI) to open the paper: it opens in its own tab, and every next paper opens in that same
   tab, so put it beside this window once. "Copy number" copies the number without its exponent (PDFs print exponents
   raised) for the PDF's search. A line before the quote says when search cannot find it: a table that is a picture in
   the PDF (go to the page it names and read the row by eye) or a value in the supplement (a separate file on the
   journal's page). {access_note}
3. Decide. j / k move between rows; to change a decision, go back (k) and press the other key (a changed note is
   saved when you press a or r again).

   If                                                 then
   ------------------------------------------------   ----------------------------------------------------------------
   The number, its unit, the row and the column       press a (Approve). The paper prints a value this row does not
   match the paper (another name for the same         show: approve anyway, with "Paper also prints a value not
   enzyme, organism or substrate is fine)             shown".

   Something differs: the number, the unit, the       click the problem button and finish the sentence, e.g.
   variant, the substrate, pH or °C, or the number      Km wrong. Paper: Km = 58 µM (Table 3, row Y228F)
   sits in another row or column                      then press Ctrl+Enter (Cmd+Enter on a Mac) or click Reject.
                                                      In the note, letter keys type letters.

   You cannot open the paper, cannot find the         press u (Can't check) and pick why: the row stays undecided
   number, or are not sure                            with that note. Never reject it.

   A word or unit you do not know (apparent, varied and fixed, read as, ×10^3 in a column header, Ki, Y228F): the ?
   beside "Check this measurement" (or "? words and units" under the buttons) opens Words and units; Esc closes it.
   When CatLog stored a value in another unit than the one printed, read a printed ×10^n its own way, or supplied a
   unit the paper does not print (a red box says so), approve only if the paper itself supports CatLog's reading (the
   row's own kcat ÷ Km, a footnote, the Methods, the text, another table); otherwise use "Unit or multiplier wrong".
   Where a ×10^n sits in a header does not decide which way it goes (old papers print "M^-1 min^-1 × 10^-7" over a
   cell that was multiplied by 10^-7): the paper's own numbers do. A CatLog note is information, not an error CatLog
   found: the "What to do" line under it says whether the case is fine.
4. Your work saves in this browser (same browser, same computer; do not clear browsing data until your last file is
   sent). On a shared or lab computer, download the results file before you log out: the browser may forget your
   work. You do not have to finish the pack: whenever you like, for example after every 100 rows, click "Download
   results file" and send that .json file back{f' to {send_to}' if send_to else ''} (catlog-human-review-results-{pack_id}-<your name>-<time>.json). Each
   file holds ALL your decisions so far, so sending a newer file later is fine: nothing is counted twice. The page
   reminds you after every 100 new decisions. Do not send the HTML or the zip.
5. Changing computer or browser: open the pack there, click "Load previous results", pick your latest results file,
   {carry_on}

{len(records)} rows from {len(zip_pmids)} papers; about 30-60 seconds each with the paper open.
""")
        zpath = PACKS / f'catlog-v2-human-review-{out.name}.zip'
        with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.rglob('*')):
                if f.is_file():
                    z.write(f, f.relative_to(out))
        zips.append((zpath, f': {who}, {len(records):,} rows from {len(zip_pmids):,} papers' if split else ''))
    names = [w for w, _ in split] if split else list(reviewers)
    paper_of = {who: [w['pubmed_id'] for _, (w, _) in items] for who, items in groups}  # each row's paper, per zip
    (PACKS / f'{pack_id}.json').write_text(json.dumps({**(old if rebuild else {}),  # a rebuild keeps notes it does not set (merged, shared)
                                                       'pack_id': pack_id, 'source_sha256': hashlib.sha256(pack_id.encode()).hexdigest(),
                                                       'seed': seed, 'cap': cap, 'created': old['created'] if rebuild else time.strftime('%Y-%m-%d'),
                                                       'reviewers': names, **({'send_to': send_to} if send_to else {}),
                                                       **({'free_only': True} if free_only else {}),
                                                       **({'split': [list(x) for x in split]} if split else {}),
                                                       **({'game': list(game)} if game else {}),
                                                       **({'papers_split': True} if by_papers else {}),
                                                       **({'hard': hard_name} if hard_name else {}),
                                                       **({'overlap': overlap} if overlap else {}),
                                                       **({'per_paper': rows_per_paper} if rows_per_paper else {}),
                                                       **({'informative': True} if informative else {}),
                                                       **({'balanced': True} if balanced else {}),
                                                       **({'easier': True} if easier else {}),
                                                       **({'catalog_harder_share': harder_share}
                                                          if rows_per_paper or hard_name else {}),
                                                       'counts': dict(tiers), 'records': index}, indent=1))
    catlog.log('-', 'review_pack_rebuilt' if rebuild else 'review_pack', pack_id, f"rows={len(index)}",
               *(f'{k.replace(" ", "_")}={v}' for k, v in tiers.items()), f"reviewers={','.join(names) or '-'}",
               *([f"split={','.join(f'{w}:{len(it)}' for w, it in groups)}"] if split else []),
               *([f"game={','.join(game)}"] if game else []),
               *([f"papers={','.join(f'{w}:{len(set(paper_of[w]))}' for w, _ in groups)}"] if by_papers else []),
               *([f'hard={hard_name}'] if hard_name else []), *([f'overlap={overlap}'] if overlap else []),
               *([f'per_paper={rows_per_paper}'] if rows_per_paper else []), *(['informative'] if informative else []),
               *(['balanced'] if balanced else []), *(['easier'] if easier else []))
    if free is not None:
        print(f'free papers only: {len(free)} of {len(access_all)} catalog papers qualify')
    if len(index) < n and not by_papers:
        print(f'only {len(index)} of {n} fit at most {cap} per paper (balance); '
              f'more per paper: review pack {n} --cap <n>')
    for zpath, whose in zips:
        print(f"{zpath} ({zpath.stat().st_size // 1024} kB){whose}")
    if by_papers:  # per person: papers, records, printed values, records per paper; who shares what (the zips do not say)
        import statistics
        harder_p = {v['pmid'] for v in index.values()  # --hard: as the papers were assigned (a rebuild too)
                    if (hard_name in [v.get('reviewer'), *(v.get('also') or [])] if hard_name else v['harder'])}
        for who, items in groups:
            per = Counter(paper_of[who])
            print(f"{who}: {len(per)} papers ({len(set(per) & harder_p)} harder, "
                  f"{len({index[m]['pmid'] for m, _ in items if index[m].get('also') or index[m].get('shared_with')})} shared), {len(items)} records, "
                  f"{sum(len(w.get('evidence') or {}) for _, (w, _) in items)} values (kcat, Km, kcat/Km cells); records per "
                  f"paper median {statistics.median(per.values()):g}, min {min(per.values())}, max {max(per.values())}")
        shared = Counter(' + '.join([v['reviewer'], *v['also']]) for v in {v['pmid']: v for v in index.values() if v.get('also')}.values())
        if overlap:
            print(f"shared by two (--overlap {overlap}), first in both zips: "
                  + (', '.join(f'{k} {c} papers' for k, c in shared.items()) or 'none'))
    print(f"{len(index)} measurements from {len(pmids)} papers "
          f"({', '.join(f'{v} {k}' for k, v in tiers.items())}). Send each reviewer their zip; results come back through "
          "`python3 catlog.py review ingest`.")


# The "databases disagree" pack (the user, 2026-10-14; work/dbreview_20261014/PLAN.md): where a database lists another
# number than CatLog for the same paper, a person reads the paper and says which number it prints, not knowing which
# number is CatLog's. Round 1: stratum, values (None: every one), at most per paper.
DB_STRATA = (('differs', None, 5),      # database_check status 'differs': cause not yet known (exact factors unchecked too)
             ('paper_check', 200, 5),   # corrections a check against the paper found (site_release.database_found_by)
             ('factor', 100, 5))        # corrections code found by an exact factor the paper's kcat ÷ Km agrees with
DB_METRICS = {'kcat': 'kcat', 'Km': 'km', 'kcat/Km': 'kcat_over_km'}  # the stored value of each compared parameter
# a table, figure or scheme an assay text names: a reviewer told "Table 2" goes there and finds CatLog's number
DB_PLACE = re.compile(r'(?i)(?<![A-Za-z])(tables?|tab\.|fig(?:ure)?s?\.?|schemes?)\s*(?:S\s*)?(?:\d+(?:[A-Za-z](?![A-Za-z]))?|[IVXL]+(?![A-Za-z]))')
DB_LEAD = re.compile(DB_PLACE.pattern + r'(?:\s+(?:footnotes?\s+\w+|caption|legend|notes?))?\s*[:,]?\s*')
DB_CARD = 500  # cards per data/cards-NNN.js


def _db_stratum(c):
    """The round-1 stratum of one value's database comparison (database_check c), or None."""
    from site_release import database_found_by
    if c.get('status') == 'differs':
        return 'differs'
    by = database_found_by(c)
    return 'paper_check' if by == 'paper_check' else 'factor' if by == 'factor_cross_checked' else None


def _caret(unit):
    """A printed unit in the packs' caret notation: 's^{−1}', 's⁻¹' and 's−1' -> 's^-1', 'x 10-3' -> 'x 10^-3', μ -> µ.

    >>> [_caret(u) for u in ('s^{−1}M^{−1}', 'μM−1 s−1', 's-1 (x 10-3)', 'min^− 1 μM^− 1', '× 10^{–1} s^{–1}')]
    ['s^-1M^-1', 'µM^-1 s^-1', 's^-1 (x 10^-3)', 'min^-1 µM^-1', '× 10^-1 s^-1']
    """
    from units import SUPERSCRIPT
    u = re.sub('⁻?[⁰¹²³⁴⁵⁶⁷⁸⁹]+', lambda m: '^' + m.group(0).translate(SUPERSCRIPT), str(unit or ''))
    u = re.sub('[−–—]', '-', u.replace('{', '').replace('}', '').replace('μ', 'µ'))
    u = re.sub(r'\^\s*-\s*(?=\d)', '^-', u)                        # 'min^− 1'
    u = re.sub(r'(?<![\d.^])(10)\s?-\s?(?=\d)', r'\1^-', u)         # 'x 10-3'
    u = re.sub(r'(?<=[A-Za-zµ)])\s?-\s?(?=1(?![\d.]))', '^-', u)   # 's-1', 'M−1' (never 'Ac-CoA')
    return re.sub(r'\s+', ' ', u).strip()


def _sig_figs(printed):
    """Significant figures of a printed cell's central number, as units.parse_number reads it.

    >>> [_sig_figs(x) for x in ('38 ± 1', '1.20', '(4.6 ± 0.3) × 10^5', '.56±.12', '0.000011 ± 0.000030', '1510', '1,200', '0,35')]
    [2, 3, 2, 2, 2, 4, 4, 2]
    """
    from units import clean
    s = clean(printed)
    s = re.sub(r'(?<![\d.])0,(?=\d)', '0.', s)  # the decimal and thousands commas and spaces parse_number reads
    s = re.sub(r'(?<=\d),(?=\d{3}(?!\d))', '', s)
    s = re.sub(r'(?<=\d),(?=\d)', '.', s)
    s = re.sub(r'(?<=\d) (?=\d{3}(?!\d))', '', s)
    m = re.search(r'\d+(?:\.\d+)?|\.\d+', s)
    return len(re.sub(r'\D', '', m.group(0)).lstrip('0')) if m else 0


def _db_shown(x, sig, sci):
    """One number of a databases card: sig significant figures, plain decimals or 'a × 10^b' (sci).

    >>> [_db_shown(*a) for a in ((38.0, 2, 0), (6, 2, 0), (99.6, 2, 0), (0.0123, 2, 0), (460000, 2, 1), (0.00012, 3, 1))]
    ['38', '6.0', '100', '0.012', '4.6 × 10^5', '1.20 × 10^-4']
    """
    from decimal import Decimal
    if sci:
        mant, _, ex = f'{x:.{sig - 1}e}'.partition('e')
        return f'{mant} × 10^{int(ex)}'
    s = f'{x:#.{sig}g}'  # '#': keeps the trailing zeros sig needs ('6.0')
    return (format(Decimal(s), 'f') if 'e' in s else s).rstrip('.')


def _db_assay(text):
    """CatLog's assay text without the table or figure it names (DB_PLACE: 'metal ion not printed in Table 2' would send
    a reviewer to CatLog's number): bracketed asides that name one go whole; a clause that starts with one loses it
    ('Table 4 monovalent-cation block: Me+ = K+' keeps 'monovalent-cation block: Me+ = K+'); elsewhere it reads 'the
    table' or 'the figure'.

    >>> _db_assay('no added ZnCl2 (Table 3 values are with 100 μM ZnCl2); Table 4 block: Me+ = K+; not printed in Fig. 2B')
    'no added ZnCl2; block: Me+ = K+; not printed in the figure'
    """
    s = str(text or '')
    while True:  # one outermost aside at a time
        groups, depth, open_ = [], 0, 0
        for i, ch in enumerate(s):
            if ch in '([':
                open_, depth = (i if depth == 0 else open_), depth + 1
            elif ch in ')]' and depth:
                depth -= 1
                if depth == 0 and DB_PLACE.search(s[open_:i + 1]):
                    groups.append((open_, i + 1))
        if not groups:
            break
        a, b = groups[0]
        s = (s[:a].rstrip() + s[b:]).strip()
    kind = lambda m: 'the ' + ('figure' if m.group(1).lower().startswith('fig') else 'scheme'
                               if m.group(1).lower().startswith('sch') else 'table') + ('s' if m.group(1).lower().endswith('s') else '')
    clauses = (DB_PLACE.sub(kind, DB_LEAD.sub('', c.strip(), count=1) if DB_LEAD.match(c.strip()) else c.strip())
               for c in s.split(';'))
    return '; '.join(c for c in clauses if c)


def dbpack(seed=None, send_to=''):
    """Round 1 of the "databases disagree" pack (DB_STRATA): every value a database lists another number for (status
    differs), 200 corrections a check against the paper found and 100 code found by an exact factor, at most 5 per paper
    in each, none already in another databases pack. Each card describes one measurement (enzyme, organism, variant,
    substrate, pH and temperature, the parameter; CatLog's assay text without the table it names) and shows two
    numbers, Value A and Value B: CatLog's and the database's, both in the unit the PAPER prints (f = CatLog's stored
    value / its printed number, parsed as units.parse_number reads the cell; the database's shown as its value / f) and
    to the same significant figures (the printed number's, 2 to 4; no ±; both as 'a × 10^b' when either is >= 1e5 or
    < 1e-3). Which side is CatLog's is random per card (seeded). A value whose two numbers come out the same is left
    out (listed in the index's left_out), and so is one where CatLog reads the printed unit otherwise (dbcompare.override,
    not a mere respelling): there f carries CatLog's reading, so the database's number would not be shown in the unit
    the card names, and which number is printed cannot settle a unit question. The zip (tools/review_ui/ab.html, ab.js,
    ab.css, its launcher, README_FIRST.txt, data/manifest.js and data/cards-NNN.js) holds only the cards: record_key,
    order, the paper (pubmed_id, doi, title, paper_access, free_url), metric, unit, value_a, value_b and the
    description. The side, stratum, databases, cause and CatLog's location and quote stay in the pack index
    human_review/packs/<pack_id>.json. Not free-only: the
    disagreements are a fixed set and many older papers open only with ISU access (each card says which). The page
    writes catlog-database-check-results-<pack_id>-<name>-<time>.json with answers (choice A, B, both, neither,
    cannot_tell) and no 'decisions' key, so `review ingest` never takes it for approve/reject verdicts."""
    import catlog, random, shutil, zipfile
    from dbcompare import override, respelled
    from site_release import database_cause, database_found_by
    from units import parse_number
    missing = [f for f in ('ab.html', 'ab.js', 'ab.css', 'open-human-review.html') if not (UI / f).exists()]
    if missing:
        sys.exit(f"the databases page is not in {UI} yet ({', '.join(missing)}): build it first")
    PACKS.mkdir(parents=True, exist_ok=True)
    sent_vals, sent_rows = set(), set()  # values already in a databases pack (a withdrawn one gives them back)
    for f in PACKS.glob('*.json'):
        idx = json.loads(f.read_text())
        if idx.get('pack_kind') == 'databases':
            for v in idx['records'].values():
                sent_vals.add((v.get('measurement_id'), v.get('metric'))); sent_rows.add(v.get('row_id'))
    seed = int(seed) if seed not in (None, '') else int(time.strftime('%Y%m%d'))
    cands, left_out, already, held = defaultdict(list), [], 0, catlog.locked()
    with open(ROOT / 'catlog_wide.jsonl') as fh:
        for line in fh:
            if '"differs"' not in line and '"corrected"' not in line:
                continue  # 362 MB: only measurements with a disagreement are parsed
            w = json.loads(line)
            if w['pubmed_id'] in held:
                continue  # the method paper's test set: never in a pack
            for m, c in (w.get('database_check') or {}).items():
                stratum = _db_stratum(c) if m in DB_METRICS else None
                if not stratum:
                    continue
                e = (w.get('evidence') or {}).get(m) or {}
                printed, unit = c.get('printed') or e.get('raw_value'), c.get('printed_unit') or e.get('raw_unit') or e.get('unit_for_conversion')
                v, dv, x = w.get(DB_METRICS[m]), c.get('database_value'), parse_number(printed)
                why = ''
                if (w['measurement_id'], m) in sent_vals or e.get('row_id') in sent_rows:
                    already += 1
                    continue
                if override(e) and not respelled(m, e):  # f would carry CatLog's reading into the database's number
                    why = f'CatLog reads the printed unit as {override(e)}; which number is printed cannot settle that'
                elif not all(isinstance(y, (int, float)) and not isinstance(y, bool) and y > 0 for y in (v, dv, x)):
                    why = 'no positive stored, printed or database number'
                else:
                    f = v / x  # catalog unit per printed unit
                    sig = max(2, min(4, _sig_figs(printed)))
                    shown_c, shown_d = x, dv / f
                    sci = any(y >= 1e5 or y < 1e-3 for y in (shown_c, shown_d))
                    a, b = _db_shown(shown_c, sig, sci), _db_shown(shown_d, sig, sci)
                    if a == b:
                        why = f'both numbers show as {a}'
                if why:
                    left_out.append({'pmid': w['pubmed_id'], 'measurement_id': w['measurement_id'], 'metric': m,
                                     'stratum': stratum, 'why': why})
                    continue
                w_ = {k: w.get(k) for k in ('measurement_id', 'pubmed_id', 'doi', 'title', 'enzyme_name', 'organism',
                                            'mutation_signature', 'substrate_name', 'cosubstrate', 'ph', 'temperature_c', 'conditions')}
                cands[stratum].append({'w': w_, 'metric': m, 'c': c, 'e': e, 'printed': printed, 'unit': _caret(unit),
                                       'printed_unit': unit, 'catlog': v, 'shown': (a, b)})
    rng = random.Random(seed)
    chosen, counts = [], {}
    for stratum, want, cap in DB_STRATA:
        pool = sorted(cands[stratum], key=lambda r: (r['w']['pubmed_id'], r['w']['measurement_id'], r['metric']))
        rng.shuffle(pool)
        per, took = Counter(), 0
        for r in pool:
            if want is not None and took >= want:
                break
            if per[r['w']['pubmed_id']] < cap:
                r['stratum'] = stratum
                chosen.append(r); per[r['w']['pubmed_id']] += 1; took += 1
        counts[stratum] = took
        if want is not None and took < want:
            print(f'{stratum}: only {took} of {want} values fit at most {cap} per paper')
    if not chosen:
        sys.exit('nothing to send: every database disagreement is already in a databases pack')
    for r in chosen:
        r['key'] = 'db:' + hashlib.sha1(f"{r['w']['measurement_id']}|{r['metric']}".encode()).hexdigest()[:16]
    pack_id = f"db-{time.strftime('%Y%m%d')}-{hashlib.sha1(' '.join(sorted(r['key'] for r in chosen)).encode()).hexdigest()[:8]}"
    pmids = sorted({r['w']['pubmed_id'] for r in chosen})
    random.Random(seed + 1).shuffle(pmids)  # papers in random order, each paper's cards together
    rank = {p_: i for i, p_ in enumerate(pmids)}
    natural = lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', str(s or ''))]
    chosen.sort(key=lambda r: (rank[r['w']['pubmed_id']], natural(r['e'].get('location')), r['w'].get('enzyme_name') or '',
                               r['w'].get('mutation_signature') or '', r['w'].get('substrate_name') or '', list(DB_METRICS).index(r['metric'])))
    side_rng = random.Random(seed + 2)
    access = paper_access(pmids)
    cards, index = [], {}
    for i, r in enumerate(chosen):
        w, c = r['w'], r['c']
        side = 'A' if side_rng.random() < 0.5 else 'B'
        a, b = r['shown'] if side == 'A' else r['shown'][::-1]
        sig = w.get('mutation_signature') or ''
        ph = f"pH {w['ph']:g}" if w.get('ph') is not None else ''
        temp = f"{w['temperature_c']:g} °C" if w.get('temperature_c') is not None else ''
        cards.append({'record_key': r['key'], 'order': i + 1, 'pubmed_id': w['pubmed_id'], 'doi': w.get('doi') or '',
                      'title': w.get('title') or '', 'paper_access': access[w['pubmed_id']]['access'],
                      'free_url': access[w['pubmed_id']]['free_url'], 'metric': r['metric'], 'unit': r['unit'],
                      'value_a': a, 'value_b': b,
                      'description': {'enzyme': w.get('enzyme_name') or '', 'organism': w.get('organism') or '',
                                      'variant': sig or 'wild type', 'variant_long': _variant_long(sig),
                                      'substrate': w.get('substrate_name') or '', 'fixed': w.get('cosubstrate') or '',
                                      'ph_temp': ' · '.join((ph or 'pH not stated', temp or 'temperature not stated'))
                                      if ph or temp else 'pH and temperature not stated',
                                      'assay': _db_assay(w.get('conditions'))}})
        index[r['key']] = {'pmid': w['pubmed_id'], 'metric': r['metric'], 'measurement_id': w['measurement_id'],
                           'row_id': r['e'].get('row_id', ''), 'stratum': r['stratum'], 'found_by': database_found_by(c),
                           'cause': database_cause(c), 'sources': list(c.get('sources') or []), 'catlog_side': side,
                           'catlog_value': r['catlog'], 'database_value': c.get('database_value'), 'printed': r['printed'],
                           'printed_unit': r['printed_unit'], 'shown_a': a, 'shown_b': b, 'order': i + 1}
    sha = hashlib.sha256(pack_id.encode()).hexdigest()
    out = PACKS / pack_id
    shutil.rmtree(out, ignore_errors=True)
    (out / 'data').mkdir(parents=True)
    for f in ('ab.html', 'ab.js', 'ab.css'):
        shutil.copyfile(UI / f, out / f)
    launcher = (UI / 'open-human-review.html').read_text()
    assert launcher.count('index.html') >= 2, 'open-human-review.html no longer names index.html'
    (out / 'Open Human Review.html').write_text(launcher.replace('index.html', 'ab.html'))
    chunks = [f'data/cards-{k // DB_CARD:03d}.js' for k in range(0, len(cards), DB_CARD)]
    for k, path in zip(range(0, len(cards), DB_CARD), chunks):
        (out / path).write_text('window.CATLOG_AB_CARDS = window.CATLOG_AB_CARDS || [];\n'
                                f'window.CATLOG_AB_CARDS.push({json.dumps(cards[k:k + DB_CARD], ensure_ascii=False)});\n')
    manifest = {'name': 'CatLog database check', 'pack_kind': 'databases', 'pack_id': pack_id, 'source_sha256': sha,
                'assigned_reviewer': None, 'send_to': send_to or None, 'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                'total_cards': len(cards), 'card_chunks': chunks}
    (out / 'data' / 'manifest.js').write_text(f'window.CATLOG_STATIC_MANIFEST = {json.dumps(manifest, ensure_ascii=False)};\n')
    isu = sum(1 for p_ in pmids if access[p_]['access'] != 'free')
    send = (f'email it to {send_to}' if '@' in send_to and '://' not in send_to else
            f'upload it at {send_to}' if send_to else 'send it back')
    (out / 'README_FIRST.txt').write_text(f"""CatLog database check {pack_id}: {len(cards):,} cards from {len(pmids):,} papers

1. Unzip the folder first (right-click > Extract All; on a Mac double-click the zip), then open "Open Human Review.html"
   in Chrome or Edge (not a private window). Type your name at the top.
2. Each card describes one measurement from a science paper: the enzyme, organism, variant, substrate, pH and
   temperature, and which constant (Km, kcat or kcat/Km). It shows two numbers, Value A and Value B, both in the
   unit on the card and rounded the same way.
3. Open the paper (the card's link). "Free to read" papers open anywhere; "ISU access" papers ({isu:,} of the
   {len(pmids):,} here) open on the ISU campus network or through the ISU VPN (connect the VPN first when you work
   from home). Find that measurement in the paper and say which number the paper prints:
     1 = Value A
     2 = Value B
     3 = both are printed for this measurement (in two rows or conditions the card does not tell apart, or the
         text and a table differ); a number the paper prints for another measurement does not count
     4 = neither: type what the paper prints, number and unit (for example 85 µM)
     5 = can't tell
   Check the unit as well as the number: if the paper prints this number in another unit, or with another × 10 in
   the column header, press 4 and type the number and unit it prints.
   Both numbers are rounded to about as many digits as the paper prints: a printed 9 shows as 9.0, a printed 340.62
   as 340.6, a printed 1.2 × 10^4 as 12000. Not sure? Press 5.
4. Please do not look rows up on the CatLog website while reviewing.
5. Your work saves in this browser by itself (same browser, same computer; do not clear the browser's history or data
   until your last file is sent). Every 50 cards, save your results file and {send}
   (catlog-database-check-results-{pack_id}-<your name>-<time>.json). Each file holds everything so far, so a newer
   file replaces the older one. Do not send the HTML or the zip.
""")
    zpath = PACKS / f'catlog-database-check-{pack_id}.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.rglob('*')):
            if f.is_file():
                z.write(f, f.relative_to(out))
    (PACKS / f'{pack_id}.json').write_text(json.dumps(
        {'pack_id': pack_id, 'pack_kind': 'databases', 'source_sha256': sha, 'seed': seed, 'created': time.strftime('%Y-%m-%d'),
         'send_to': send_to, 'counts': counts, 'records': index, 'left_out': left_out}, indent=1, ensure_ascii=False))
    catlog.log('-', 'review_dbpack', pack_id, f'cards={len(cards)}', *(f'{k}={v}' for k, v in counts.items()),
               f'papers={len(pmids)}', f'left_out={len(left_out)}', f'already_sent={already}')
    print(f"{zpath} ({zpath.stat().st_size // 1024} kB)")
    print(f"{len(cards)} cards from {len(pmids)} papers ({', '.join(f'{v} {k}' for k, v in counts.items())}; "
          f"{isu} papers need ISU access); left out {len(left_out)} value(s) before sampling (CatLog reads the printed "
          f"unit otherwise, two numbers that show the same, or no number; in the index's left_out)"
          + (f'; {already} already in a databases pack' if already else ''))


def packs():
    """Every pack: when made, for whom, what came back (per reviewer), what is still open."""
    exports = defaultdict(list)
    for r in _manifest().values():
        exports[r['pack']].append(r)
    by_key, status = defaultdict(dict), {}
    for d in (_decisions() if DECISIONS.exists() else []):
        status[d['key']] = d['status']
        for who, st in (d.get('reviewers') or {'': d['status']}).items():
            by_key[d['key']][who] = st
    lent = defaultdict(set)  # records two packs share (shared_with): key -> both people
    for f in PACKS.glob('*.json'):
        for k, v in (json.loads(f.read_text()).get('records') or {}).items():
            if isinstance(v, dict) and v.get('shared_with'):
                lent[k] |= {v['reviewer'], v['shared_with']['reviewer']}
    old = [r for r in _manifest().values() if r['pack'] and not any(f.name for f in PACKS.glob('*.json')
                                                                     if json.loads(f.read_text()).get('source_sha256', '')[:12] == r['pack'])]
    for f in sorted(list(PACKS.glob('*.json')) + list((PACKS / 'withdrawn').glob('*.json'))):
        idx = json.loads(f.read_text())
        if 'records' not in idx:  # a case-review index (cases-*.json, the agent-highlights chat): not a review pack
            continue
        recs = idx['records']
        if idx.get('pack_kind') == 'databases':  # which number the paper prints: its results are not approve/reject files
            print(f"{idx['pack_id']}  made {idx.get('created')}{'  (withdrawn)' if f.parent.name == 'withdrawn' else ''}  "
                  f"databases check: {len(recs)} cards {idx.get('counts', '')}  results files: "
                  f"{len(exports.get(idx['source_sha256'][:12], []))} (catlog-database-check-results-{idx['pack_id']}-*.json; "
                  f"answers: review dbstats)")
            continue
        got = exports.get(idx['source_sha256'][:12], [])
        who_list = idx.get('reviewers') or ['']
        print(f"{idx['pack_id']}  made {idx.get('created')}{'  (withdrawn)' if f.parent.name == 'withdrawn' else ''}  "
              f"{len(recs)} rows {idx.get('counts', '')}  results files: {len(got)}")
        if idx.get('split'):  # one line per person: their rows, and how many of them have a decision (whoever typed it;
            # a row two people share (--overlap): only this person's own verdict)
            for who in idx['reviewers']:
                ks = [k for k, v in recs.items() if who in [v.get('reviewer'), *(v.get('also') or [])]]
                sts = Counter(by_key.get(k, {}).get(who) if recs[k].get('also') or k in lent else status.get(k) for k in ks)
                mine = len(ks)
                print(f"    {who:20} {len({recs[k]['pmid'] for k in ks}):4} papers {mine:5} rows  decided "
                      f"{sts['approved'] + sts['rejected']:5} (approved {sts['approved']}, rejected {sts['rejected']})  "
                      f"open {mine - sts['approved'] - sts['rejected']:5}")
            shared = [k for k, v in recs.items() if v.get('also')]
            if shared:
                both = sum(1 for k in shared if {recs[k]['reviewer'], *recs[k]['also']} <= set(by_key.get(k, {})))
                print(f"    shared by two: {len(shared)} rows from {len({recs[k]['pmid'] for k in shared})} papers, "
                      f"decided by both {both} (agreement: review stats)")
            typed = sorted({w for k in recs for w in by_key.get(k, {}) if w not in lent.get(k, ())} - set(idx['reviewers']))
            if typed:
                print(f"    names in the results files that are not in the split: {', '.join(w or '(no name)' for w in typed)}")
            continue
        for who in sorted({w for k in recs for w in by_key.get(k, {})} | set(who_list)):
            sts = Counter(by_key.get(k, {}).get(who) for k in recs)
            print(f"    {who or '(no name)':20} approved {sts['approved']:4}  rejected {sts['rejected']:4}  open {len(recs) - sts['approved'] - sts['rejected']:4}")
    first = Counter(r['pack'] for r in old)
    if first:
        print(f"old 2026 pack (5,833 old-catalog rows): {sum(first.values())} results files; earlier-review decisions in `review stats`")


DB_POOL = 20  # in a block of `review dbstats`, databases with fewer answers are counted together as "other"


def dbstats():
    """The databases pack's answers (db_review.jsonl): for each stratum, then all strata, the answers and, below them,
    per database (a value counts for each database that lists its number; databases with fewer than DB_POOL answers
    in the block pooled as "other"): answered, the paper prints CatLog's number (the database is wrong), the
    database's (CatLog is wrong), both (printed for this measurement: not an error of either), neither, can't tell. On
    paper_check and factor (corrections) the share that prints CatLog's number is the precision of the check that
    found them (the AI paper-check; code's exact factor)."""
    from site_release import DATABASES
    path = HR / DB_REVIEW
    if not path.exists():
        sys.exit('no database check answers yet: run python3 catlog.py review ingest')
    rows = [json.loads(l) for l in open(path) if l.strip()]
    pct = lambda k, n: f"{k} ({100 * k / n:.0f}%)" if n else str(k)

    def line(name, rs, after=''):
        n = Counter(r['picked'] for r in rs)
        return f"{name:16}{len(rs):>9,}" + ''.join(f'{pct(n[p], len(rs)):>17}' for p, _ in DB_PICKED) + after

    def block(name, rs):
        print(line(name, rs))
        per = defaultdict(dict)
        for r in rs:
            for db in r.get('sources') or []:
                per[db][r['key']] = r
        small = sorted(db for db, x in per.items() if len(x) < DB_POOL)
        for db in sorted(set(per) - set(small), key=lambda x: (DATABASES.index(x) if x in DATABASES else len(DATABASES), x)):
            print(line(f'  {db}', list(per[db].values())))
        if small and len(small) < len(per):  # all of them small: "other" would be the line above
            print(line('  other', list({k: r for db in small for k, r in per[db].items()}.values()), f"  ({', '.join(small)})"))
    print(f"Database check: {len(rows):,} values answered on {len({r['pmid'] for r in rows if r['pmid']}):,} papers "
          f"(human_review/{DB_REVIEW}). Which number does the paper print?")
    print(f"{'':16}{'answered':>9}" + ''.join(f'{label:>17}' for _, label in DB_PICKED))
    order = [st for st, _, _ in DB_STRATA]
    for st in sorted({r['stratum'] for r in rows}, key=lambda x: (order.index(x) if x in order else len(order), x)):
        block(st or 'no pack index', [r for r in rows if r['stratum'] == st])
    block('all strata', rows)
    print("CatLog's number: the database is wrong; the database's: CatLog is wrong; both: printed for this measurement "
          "(not an error of either); neither: the paper prints another number (typed_value in db_review.jsonl). "
          "A value counts under each database that lists its number.")
    for st, what in (('paper_check', "the AI paper-check's precision"), ('factor', "code's precision (an exact factor)")):
        settle = [r for r in rows if r['stratum'] == st and r['picked'] in ('catlog', 'database', 'both', 'neither')]
        if settle:
            k = sum(r['picked'] == 'catlog' for r in settle)
            print(f"{st}: {what}: the paper prints CatLog's number on {k} of {len(settle)} answers "
                  f"({100 * k / len(settle):.0f}%; can't tell left out)")
    multi = [r for r in rows if len(r.get('reviewers') or {}) > 1]
    if multi:
        print(f"values answered by 2+ reviewers: {len(multi)}; they agree on {sum(not r['disagree'] for r in multi)}")


def main(args):
    cmd = args[0] if args else 'stats'
    if cmd == 'ingest':
        ingest(args[1:])
    elif cmd == 'stats':
        stats()
    elif cmd == 'dbstats':
        dbstats()
    elif cmd == 'compare':
        compare(args[1] if len(args) > 1 else None)
    elif cmd == 'audit':
        audit()
    elif cmd == 'site':
        site()
    elif cmd == 'pack':
        opts = {'--seed': None, '--cap': None, '--for': '', '--gold': 0, '--rebuild': None, '--send-to': '', '--split': '',
                '--game': '', '--kinds-share': None, '--hard': '', '--overlap': 0, '--per-paper': 0}
        rest, i, free_only, by_papers, informative, balanced, easier = [], 1, False, False, False, False, False
        while i < len(args):
            if args[i] == '--free-only':  # a switch: takes no value
                free_only = True; i += 1
            elif args[i] == '--papers':  # a switch: the --split counts are papers
                by_papers = True; i += 1
            elif args[i] == '--informative':  # a switch: the --hard name's papers are picked, not drawn
                informative = True; i += 1
            elif args[i] == '--balanced':  # a switch: half the one name's papers harder, half not
                balanced = True; i += 1
            elif args[i] == '--easier':  # a switch: only papers that are not harder, for the one name
                easier = True; i += 1
            elif args[i] in opts and i + 1 < len(args):
                opts[args[i]] = args[i + 1]; i += 2
            else:
                rest.append(args[i]); i += 1
        split = _split_arg(opts['--split']) if str(opts['--split']).strip() else None
        # no N but a count for every name ("Reviewer A:2000,Reviewer B:1000"): a new pack is their sum; --papers: counts are papers,
        # so a generous candidate pack of 3,000 rows (--per-paper draws papers and needs no N)
        n = (int(rest[0]) if rest else 3000 if by_papers else sum(c for _, c in split)
             if split and all(c for _, c in split) and not opts['--rebuild'] else 40)
        pack(n, opts['--seed'], opts['--cap'],
             [x.strip() for x in str(opts['--for']).split(',') if x.strip()], int(opts['--gold'] or 0), opts['--rebuild'],
             str(opts['--send-to'] or '').strip(), free_only, split,
             [x.strip() for x in str(opts['--game']).split(',') if x.strip()],
             float(opts['--kinds-share'] if opts['--kinds-share'] is not None else 0 if int(opts['--per-paper'] or 0) else 0.55),
             by_papers, str(opts['--hard'] or '').strip(), float(opts['--overlap'] or 0), int(opts['--per-paper'] or 0),
             informative, balanced, easier)
    elif cmd == 'dbpack':
        opts = {'--seed': None, '--send-to': ''}
        for i in range(1, len(args) - 1, 2):
            if args[i] not in opts:
                sys.exit(__doc__)
            opts[args[i]] = args[i + 1]
        if len(args) % 2 == 0:  # a flag without its value
            sys.exit(__doc__)
        dbpack(opts['--seed'], str(opts['--send-to'] or '').strip())
    elif cmd == 'packs':
        packs()
    elif cmd == 'withdraw' and len(args) > 1:
        withdraw(args[1])
    elif cmd == 'decided' and len(args) > 2:
        decided(args[1], ' '.join(args[2:]))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
