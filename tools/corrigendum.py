#!/usr/bin/env python3
"""After the saved workflow `catlog-corrigendum` (three independent agents map every stored value and censored value
of a corrected article and of its correction notice: work/corrigendum_<ARTICLE>/<NOTICE>/verify_{a,b,c}.json), apply
what all three agree on and record the check (log `corrigendum_check`, which ends the "Correction notices" line of
`catlog.py status` until either paper gains values; CLAUDE.md "Correction notices").

  python3 tools/corrigendum.py ARTICLE NOTICE            dry run: drops.tsv and unitfixes.tsv beside the verdicts
  python3 tools/corrigendum.py ARTICLE NOTICE --apply    the same, then the drops, the unit fixes and the log line
  (--dir D reads D instead of work/corrigendum_<ARTICLE>/<NOTICE>; --catalog F and --bounds G read copies: a test,
  never with --apply)

Nothing is decided unless every stored value of both papers is judged by all three agents with a decision of its
paper's kind, and all three call the notice the authors' correction of the article (all three "not a correction":
--apply records that and drops nothing). On all three agents' word:
- article SUPERSEDED: dropped ("superseded by the authors' correction") when the corrected cell is stored under the
  notice; otherwise it waits for a fresh read of the notice and the check stays open;
- article UNIT: `unitfix` to the unit the notice states (code converts the printed cell again);
- article WITHDRAWN: dropped ("withdrawn by the authors' correction"); article RELABEL: listed for the chat, kept;
- notice REPRINTED: dropped when the article's cell (value, converted value and unit) is stored: "reprinted" (CatLog's
  error) when the article's text, or its supplement for a supplementary table, was on disk when the notice value was
  added, else "duplicate of row ..." (read.md told the reader to store it then; not an error);
- notice NOT_OWN (printed as the original or wrong value, or credited to other work): dropped ("not its own").
A value any agent calls UNSURE keeps the check open (listed: a better copy or a fresh run); other disagreements are
kept and counted. human_review.catlog_errors does not count "superseded"/"withdrawn by the authors' correction" or
"duplicate" drops as CatLog's errors. First case, by hand before this tool: 40465391 and its corrigendum 41287407
(2026-11-16/17, paper/evidence/reprint_sweep_20261116/corrigendum_40465391/)."""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import catlog  # noqa: E402

KEYS = 'abc'
KINDS = {'article': {'UNCHANGED', 'SUPERSEDED', 'UNIT', 'WITHDRAWN', 'RELABEL', 'UNSURE'},
         'notice': {'CORRECTED', 'REPRINTED', 'NOT_OWN', 'UNSURE'}}
WRONG = {'article': {'SUPERSEDED', 'UNIT', 'WITHDRAWN'}, 'notice': {'REPRINTED', 'NOT_OWN'}}  # the stored value cannot stay


GLYPHS = str.maketrans({'≫': '>>', '⪢': '>>', '≪': '<<', '⪡': '<<', '≥': '>=', '⩾': '>=', '≤': '<=', '⩽': '<='})
ND = re.compile(r'(?i)^(?:n\.?\s?d\.?|not detected|no detection|not detectable|below detection)(?![a-z])')


def cell(s):
    """A printed cell for comparison, spelled as the catalog spells printed cells (catlog.squash: units.clean's minus,
    times and superscripts), with no spaces or digit-group commas ('38 000', '38,000'), one ± and one bound glyph
    spelling ('≫' = '>>'), lower case."""
    s = catlog.squash(str(s or '').translate(GLYPHS)).replace(' ', '')
    s = re.sub(r'(?<=\d),(?=\d{3}(?!\d))', '', s)
    return s.replace('+/-', '±').replace('+-', '±').lower()


def key(r=None, text=None):
    """What a correction is matched on: 'nd' for a not-detected marker, else the cell's sign and number (a bound's
    limit is the notice's own footnote and never decides whether the article's value was replaced)."""
    if r is not None:
        return 'nd' if r.get('censored') == 'not_detected' else cell(r.get('raw_value'))
    return 'nd' if ND.match(str(text or '').strip()) else cell(text)


def matches(text, r):
    """An agent's notice_cell names stored row r: the same marker, sign and number (spelling aside), or that followed by
    a unit or note the agent added ('4400 ± 490 s-1'), never by another digit ('4400 ± 4900' is not '4400 ± 490')."""
    k, mine = key(text=text), key(r)
    return k in (mine, printed(r)) or bool(re.match(re.escape(mine) + r'(?![\d.±])', k)) and mine != 'nd'


def printed(r):
    """A stored row's whole cell: its raw value, and a censored value's limit too (a changed limit is a change)."""
    return cell(r.get('raw_value') or '') if not r.get('censored') else cell(f"{r.get('raw_value', '')}{r.get('limit', '')}")


def same_value(a, b):
    """The same stored value: the same metric; for an ordinary value the same printed cell, converted value and unit (a
    unit the notice changed is never taken for a copy; catlog.close, as twin() uses it); for a censored value the same
    kind, marker or sign and number ('ND' = 'n.d.') and limit."""
    if a.get('metric') != b.get('metric') or bool(a.get('censored')) != bool(b.get('censored')):
        return False
    if a.get('censored'):
        return a.get('censored') == b.get('censored') and key(a) == key(b) and cell(a.get('limit')) == cell(b.get('limit'))
    return printed(a) == printed(b) and a.get('unit') == b.get('unit') and a.get('value') is not None \
        and b.get('value') is not None and catlog.close(a['value'], b['value'])


def load(path):
    if not path.exists():
        return []
    with open(path) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def in_supplement(article, twin):
    """Whether the article prints this cell only in its supplement: its quote is in texts/<article>.supp.txt and not in
    the main text (a 'Table S5' location decides only when the quote is found in neither)."""
    main, supp = catlog.TEXTS / f'{article}.txt', catlog.TEXTS / f'{article}.supp.txt'
    if not supp.exists():
        return False
    q = catlog.squash(twin.get('quote') or '')
    if q and main.exists() and catlog.quote_found(q, catlog.squash(catlog.paper_only(main.read_text()))):
        return False
    if q and catlog.quote_found(q, catlog.squash(supp.read_text())):
        return True
    return bool(re.search(r'(?i)supp|\bS\d', str(twin.get('location', ''))))


def text_on_disk_by(article, when, supplement, ev):
    """Whether the article's text (its supplement for a supplementary table) was on disk at or before `when`, by
    log.tsv's `text` / `supplement` lines (a paper added before any text line kept its text from the library)."""
    acts = ('supplement',) if supplement else ('text', 'supplement')
    first = min((f[0] for f in ev if f[1] == article and f[2] in acts), default=None)
    if first is None and not supplement:
        first = min((f[0] for f in ev if f[1] == article and f[2] == 'add'), default=None)
    return first is not None and first <= (when or '9999')


def plan(article, notice, folder, catalog, bounds, ev=None, cite=None):
    """(drops [(row_id, why)], unitfixes [(row_id, unit, why)], waiting, open_, kept, relabel [(row_id, why)],
    relation) from the three verdict files; exits when they do not cover every stored value of both papers."""
    files = [folder / f'verify_{k}.json' for k in KEYS]
    missing = [f.name for f in files if not f.exists()]
    if missing:
        sys.exit(f'{", ".join(missing)} missing in {folder}: run the workflow catlog-corrigendum')
    data = [json.loads(f.read_text()) for f in files]
    verdicts = [{(r.get('paper'), r.get('row_id')): r for r in d.get('rows', [])} for d in data]
    rows = load(catalog) + load(bounds)
    mine = {p: {r['row_id']: r for r in rows if r['pmid'] == p} for p in (article, notice)}
    who = {'article': article, 'notice': notice}
    problems = []
    for k, d, v in zip(KEYS, data, verdicts):
        bad = [f"{rid} ({p}: {r.get('decision')})" for (p, rid), r in v.items() if p in KINDS and r.get('decision') not in KINDS[p]]
        unjudged = [rid for paper, p in who.items() for rid in mine[p] if (paper, rid) not in v]
        if d.get('relation') not in ('authors_correction', 'not_a_correction', 'unsure'):
            problems.append(f'verify_{k}.json gives no relation')
        if bad:
            problems.append(f'verify_{k}.json has decisions of the wrong kind: {", ".join(bad[:5])}')
        if unjudged:
            problems.append(f'verify_{k}.json does not judge {len(unjudged)} stored values ({", ".join(unjudged[:5])})')
    if problems:
        sys.exit('; '.join(problems) + ': run the workflow catlog-corrigendum again (it judges every stored value)')
    relation = {d['relation'] for d in data}
    if relation != {'authors_correction'}:
        return [], [], [], [], [], [], ('not_a_correction' if relation == {'not_a_correction'} else 'disputed')
    ev = catlog.events() if ev is None else ev
    cite = cite or ', '.join(str(f) for f in files)
    drops, fixes, waiting, open_, kept, relabel = [], [], [], [], [], []
    for paper, p in who.items():
        for rid, here in mine[p].items():
            vs = [v[(paper, rid)] for v in verdicts]
            ds = [x['decision'] for x in vs]
            where = f"{here.get('location', '')}, {here.get('variant', '')} {here.get('substrate', '')} {here.get('metric', '')}"
            said = ', '.join(f'{k}={d}' for k, d in zip(KEYS, ds))
            if 'UNSURE' in ds:
                open_.append((rid, f'UNSURE: {said}')); continue
            if len(set(ds)) != 1:  # all three say the stored value is wrong, but not how: open; else kept as it is
                (open_ if set(ds) <= WRONG[paper] else kept).append((rid, f'agents differ: {said}')); continue
            d = ds[0]
            ids = {frozenset(re.findall(r'[0-9a-f]{16}', str(x.get('other_row_id') or ''))) for x in vs}  # 'none' = ''
            one = next(iter(next(iter(ids)))) if len(ids) == 1 and len(next(iter(ids))) == 1 else None
            named = mine[notice if paper == 'article' else article].get(one) if one else None
            if d == 'SUPERSEDED':
                if ids == {frozenset()}:
                    waiting.append((rid, f"corrected cell {vs[0].get('notice_cell')} is not stored under {notice}")); continue
                if named is None or named.get('metric') != here.get('metric'):
                    open_.append((rid, f"SUPERSEDED, but the agents do not name one stored {here.get('metric')} of "
                                       f"{notice}: {[sorted(x) for x in ids]}")); continue
                if not all(matches(x.get('notice_cell'), named) for x in vs):
                    open_.append((rid, f"SUPERSEDED, but not every agent's notice cell is row {named['row_id']}'s "
                                       f"{named.get('raw_value', '')}")); continue
                twin = [named]
                drops.append((rid, f"superseded by the authors' correction: their correction notice PMID {notice} prints "
                                   f"this cell ({where}, printed {here.get('raw_value', '')}) as {vs[0].get('notice_cell')}, "
                                   f"stored under {notice} as row {twin[0]['row_id']}; three independent agents agreed ({cite})"))
            elif d == 'UNIT' and here.get('censored'):  # unitfix converts values, not bounds: the chat decides
                relabel.append((rid, f"{where}: the notice changes the unit of this censored value to "
                                     f"{vs[0].get('notice_cell', '')}; unitfix does not apply to bounds"))
            elif d == 'UNIT':
                conv = lambda u: catlog.normalize(here.get('metric', ''), here.get('raw_value', ''), str(u or '').strip())
                got = [conv(x.get('notice_cell')) for x in vs]
                if any(g[2] for g in got) or len({(round(g[0], 9), g[1]) for g in got}) != 1:
                    open_.append((rid, "UNIT, but the agents' units do not convert alike: "
                                       + '; '.join(str(x.get('notice_cell')) for x in vs))); continue
                u = str(vs[0].get('notice_cell', '')).strip()
                if here.get('unit_for_conversion') and conv(here['unit_for_conversion'])[:2] == got[0][:2]:
                    continue  # fixed already
                fixes.append((rid, u, f"the authors' correction notice PMID {notice} gives the unit of this cell ({where}, "
                                      f"printed {here.get('raw_value', '')} {here.get('raw_unit', '')}) as {u}; three "
                                      f"independent agents agreed ({cite})"))
            elif d == 'WITHDRAWN':
                drops.append((rid, f"withdrawn by the authors' correction: their correction notice PMID {notice} withdraws "
                                   f"this value ({where}, printed {here.get('raw_value', '')}) without a replacement: "
                                   f"{str(vs[0].get('why', ''))[:200]}; three independent agents agreed ({cite})"))
            elif d == 'RELABEL':
                relabel.append((rid, f"{where}: {str(vs[0].get('why', ''))[:200]}"))
            elif d == 'REPRINTED':
                if len(ids) > 1:
                    open_.append((rid, f"REPRINTED, but the agents name different rows of {article}: {[sorted(x) for x in ids]}")); continue
                twin = [named] if named is not None and same_value(named, here) else []
                if not twin:
                    kept.append((rid, f'called printed again unchanged, but the agents do not name one stored value of '
                                      f'{article} with its cell, converted value and unit')); continue
                supp = in_supplement(article, twin[0])
                if text_on_disk_by(article, here.get('added'), supp, ev):
                    drops.append((rid, f"reprinted: the correction notice PMID {notice} prints the corrected article's "
                                       f"cell unchanged ({where} {here.get('raw_value', '')}; PMID {article} stores it as "
                                       f"row {twin[0]['row_id']}); three independent agents agreed ({cite})"))
                else:
                    drops.append((rid, f"duplicate of row {twin[0]['row_id']} (PMID {article}): the correction notice "
                                       f"PMID {notice} prints this cell unchanged ({where} {here.get('raw_value', '')}); "
                                       f"stored while that article's {'supplement' if supp else 'text'} was not on disk, "
                                       f"as read.md says; three independent agents agreed ({cite})"))
            elif d == 'NOT_OWN':
                drops.append((rid, f"not its own: the correction notice PMID {notice} prints this value ({where} "
                                   f"{here.get('raw_value', '')}) as {str(vs[0].get('why', ''))[:200]}; three independent "
                                   f"agents agreed ({cite})"))
    return drops, fixes, waiting, open_, kept, relabel, 'authors_correction'


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('article')
    ap.add_argument('notice')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--dir')
    ap.add_argument('--catalog')
    ap.add_argument('--bounds')
    a = ap.parse_args(argv)
    article, notice = catlog.paper_id(a.article), catlog.paper_id(a.notice)
    if a.apply and (a.catalog or a.bounds or a.dir):
        sys.exit('--catalog, --bounds and --dir are for a test against copies: never with --apply')
    held = catlog.locked() & {article, notice}
    if held:
        sys.exit(f"left out (the method paper's test set): {' '.join(sorted(held))}")
    folder = Path(a.dir) if a.dir else catlog.WORK / f'corrigendum_{article}' / notice
    keep = folder / f"applied_{time.strftime('%Y%m%d-%H%M%S')}" if a.apply else None
    while keep is not None and keep.exists():  # two runs in one second: never write over the earlier run's evidence
        keep = keep.with_name(keep.name + '_')
    cite = ', '.join(str((keep or folder) / f'verify_{k}.json') for k in KEYS)
    drops, fixes, waiting, open_, kept, relabel, relation = plan(
        article, notice, folder, Path(a.catalog) if a.catalog else catlog.CATALOG,
        Path(a.bounds) if a.bounds else catlog.BOUNDS, cite=cite)
    clean = lambda s: ' '.join(str(s).split())  # one line per row for `drop --file`
    if not folder.name.startswith('applied_'):  # a dry run on an applied run's verdicts never rewrites its evidence
        (folder / 'drops.tsv').write_text(''.join(f'{rid}\t{clean(why)}\n' for rid, why in drops))
        (folder / 'unitfixes.tsv').write_text(''.join(f'{rid}\t{clean(u)}\t{clean(why)}\n' for rid, u, why in fixes))
    counts = {'superseded': sum(w.startswith('superseded') for _, w in drops),
              'withdrawn': sum(w.startswith('withdrawn') for _, w in drops),
              'reprinted': sum(w.startswith('reprinted') for _, w in drops),
              'duplicate': sum(w.startswith('duplicate') for _, w in drops),
              'not_own': sum(w.startswith('not its own') for _, w in drops),
              'unitfix': len(fixes), 'relabel_listed': len(relabel), 'kept_disputed': len(kept),
              'waiting': len(waiting), 'unsure': len(open_)}
    if relation != 'authors_correction':
        print(f'{article} / {notice}: the agents call the notice {relation.replace("_", " ")}; nothing to drop')
    else:
        print(f'{article} corrected by {notice}: ' + (', '.join(f'{k} {v}' for k, v in counts.items() if v) or 'nothing to change')
              + f' (drops.tsv, unitfixes.tsv in {folder})')
    for label, items in (('keep (agents differ)', kept), ('waits (corrected cell not stored)', waiting),
                         ('open (UNSURE)', open_), ('relabel? (kept; the chat decides)', relabel)):
        for rid, why in items:
            print(f'  {label} {rid}: {why}')
    if waiting:
        print(f'  a corrected cell CatLog stores: read the notice again (`python3 catlog.py reread {notice} "corrected '
              f'cells not stored" --fresh`; after its add, `python3 work/reread_copies/reread_copies.py {notice} OUT` lists '
              f'copies), then run the check again; one CatLog does not store (not determined, a Hill constant): run the '
              f'check again, the agents call it WITHDRAWN')
    if open_:
        print('  a better copy of the paper, or a fresh run of catlog-corrigendum, settles the UNSURE values')
    if not a.apply:
        return
    keep.mkdir(parents=True)
    for name in [f'verify_{k}.json' for k in KEYS] + ['drops.tsv', 'unitfixes.tsv']:
        shutil.move(str(folder / name), str(keep / name))  # this run's evidence, cited by its drops; the next run starts clean
    if relation == 'disputed':
        print("not recorded: the agents disagree on whether this is the authors' correction; read the notice")
        return
    refused = []
    if relation == 'authors_correction':
        if drops:
            catlog.cmd_drop('--file', str(keep / 'drops.tsv'))
        for rid, u, why in fixes:
            if rid not in (catlog.cmd_unitfix(u, why, rid) or set()):
                refused.append(rid)
        counts['unitfix'] = len(fixes) - len(refused)
    if refused:
        print(f"unitfix refused for {' '.join(refused)} (its output says why); check left open")
    if waiting or open_ or refused:
        print('check left open: status keeps listing it')
        return
    catlog.log(article, 'corrigendum_check', notice, f'relation={relation}', *(f'{k}={v}' for k, v in counts.items()))
    print(f'recorded: corrigendum_check {article} {notice}')


if __name__ == '__main__':
    main(sys.argv[1:])
