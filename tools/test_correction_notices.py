#!/usr/bin/env python3
"""Offline tests for correction notices (read.md Rules, CLAUDE.md "Correction notices"): `add` logs a notice for each
article its `corrects` names (catlog.corrected_ids, finish), status lists a notice while its article has stored values
or censored values not yet checked, and again when either paper gains values (catlog.corrections_pending), and
tools/corrigendum.py decides nothing unless every stored value was judged by all three agents, applies only what all
three agree on, never drops a superseded value whose correction is not stored, and leaves the check open on UNSURE:
python3 tools/test_correction_notices.py
Each test runs in its own temporary root (catlog's paths are pointed there); the live folder is never written."""
import contextlib, hashlib, io, json, sys, tempfile, unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import catlog  # noqa: E402
import corrigendum  # noqa: E402

PATHS = ('ROOT', 'PAPERS', 'CATALOG', 'REJECTED', 'BOUNDS', 'LOG', 'TEXTS', 'WORK')
HEAD = 'pmid\tdoi\ttitle\tstatus\ttext_source\tkept\trejected\tnote\tupdated\n'


def H(label):
    """A test label as a row id (16 hex digits, as catalog row ids are)."""
    return hashlib.md5(label.encode()).hexdigest()[:16]


def L(ids):
    """Row ids back to their test labels, sorted."""
    back = {H(x): x for x in [f'{a}{n}' for a in 'AN' for n in range(1, 10)]}
    return sorted(back.get(i, i) for i in ids)


def row(p, rid, v, m='kcat', var='WT', loc='Table 1', unit='s^-1', value=None, **k):
    return {'row_id': H(rid), 'pmid': p, 'variant': var, 'substrate': 'S', 'metric': m, 'raw_value': v, 'raw_unit': unit,
            'location': loc, 'unit': unit, 'value': value if value is not None else float(v.split()[0].replace(' ', '')),
            'added': '2026-11-01 00:00', **k}


def verdict(paper, rid, d, notice_cell='', other='none', why=''):
    return {'paper': paper, 'row_id': H(rid), 'decision': d, 'notice_cell': notice_cell,
            'other_row_id': H(other) if other not in ('none', '') else other, 'why': why}


class Notices(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(catlog, k) for k in PATHS}
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name).resolve()
        catlog.ROOT = root
        for k, name in (('PAPERS', 'papers.tsv'), ('CATALOG', 'catalog.jsonl'), ('REJECTED', 'rejected.jsonl'),
                        ('BOUNDS', 'bounds.jsonl'), ('LOG', 'log.tsv'), ('TEXTS', 'texts'), ('WORK', 'work')):
            setattr(catlog, k, root / name)
        catlog.TEXTS.mkdir()
        catlog.WORK.mkdir()
        (root / 'sources').mkdir()
        for p in (catlog.CATALOG, catlog.REJECTED, catlog.LOG):
            p.write_text('')
        catlog.PAPERS.write_text(HEAD + '90002002\t10.1000/fix\tCorrection to "X"\treading\t\t\t\t\t\n')

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(catlog, k, v)
        self.tmp.cleanup()

    def lines(self, action):
        return [l.split('\t') for l in catlog.LOG.read_text().splitlines() if l.split('\t')[2:3] == [action]]

    def quiet(self, fn, *a, **k):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*a, **k)

    # --- add ---------------------------------------------------------------------------------------------------
    def test_add_logs_the_notice(self):
        self.quiet(catlog.finish, '90002002', {'note': 'a correction notice'}, [], [], corrects='90002001')
        self.assertEqual([(l[1], l[3]) for l in self.lines('correction_notice')], [('90002002', '90002001')])

    def test_no_line_without_corrects_or_for_a_wrong_paper(self):
        self.quiet(catlog.finish, '90002002', {'note': 'nothing corrected'}, [], [])
        self.quiet(catlog.finish, '90002002', {'note': 'wrong_paper: another article'}, [], [], corrects='90002001')
        self.assertEqual(self.lines('correction_notice'), [])

    def test_corrected_ids(self):
        c = catlog.corrected_ids
        self.assertEqual(c('PMID: 40465391'), ['40465391'])
        self.assertEqual(c(['https://doi.org/10.1002/ANIE.202508565.', 'np0d6aeb3e', 40465391]),
                         ['10.1002/anie.202508565', 'NP0D6AEB3E', '40465391'])
        self.assertEqual(c([None, 'none', '']), [])
        self.assertEqual(c('10.1002/(SICI)1097-0134(1999)35:1<1::AID-PROT1>3.0.CO;2-8'),
                         ['10.1002/(sici)1097-0134(1999)35:1<1::aid-prot1>3.0.co;2-8'])
        self.assertEqual(c(['40465391', '40465391']), ['40465391'])

    # --- status --------------------------------------------------------------------------------------------------
    def test_pending_until_checked_and_again_after_new_values(self):
        ev = [['2026-11-17 01:00', '90002002', 'correction_notice', '90002001'],
              ['2026-11-17 01:01', '90002004', 'correction_notice', 'https://doi.org/10.1000/XYZ'],
              ['2026-11-17 01:02', '90002006', 'correction_notice', '90002005'],
              ['2026-11-17 01:03', '90002005', 'corrigendum_check', '90002006', 'superseded=1'],
              ['2026-11-17 01:04', '90002007', 'correction_notice', '90002007'],  # names itself: never a pair
              ['2026-11-17 01:05', '90002008', 'correction_notice', '90002009'],  # its article has no stored value
              ['2026-11-17 01:06', '90002002', 'correction_notice', '90002001']]  # added twice: listed once
        cat = [{'pmid': p, 'added': '2026-11-10 00:00'} for p in ('90002001', '90002003', '90002005', '90002007')]
        qrows = [{'pmid': '90002003', 'doi': '10.1000/xyz'}]
        self.assertEqual(catlog.corrections_pending(ev, cat, qrows), [('90002002', '90002001'), ('90002004', '90002003')])
        cat.append({'pmid': '90002006', 'added': '2026-11-17 02:00'})  # the notice gains a value after the check
        self.assertIn(('90002006', '90002005'), catlog.corrections_pending(ev, cat, qrows))
        (catlog.ROOT / 'sources' / 'holdout_locked.txt').write_text('# test set\n90002001\n')
        self.assertNotIn(('90002002', '90002001'), catlog.corrections_pending(ev, cat, qrows))

    def test_censored_values_count_as_stored(self):
        catlog.BOUNDS.write_text(json.dumps({'pmid': '90002011', 'row_id': 'b' * 16, 'added': '2026-11-10 00:00'}) + '\n')
        ev = [['2026-11-17 01:00', '90002012', 'correction_notice', '90002011']]
        self.assertEqual(catlog.corrections_pending(ev, [], []), [('90002012', '90002011')])

    # --- tools/corrigendum.py --------------------------------------------------------------------------------------
    def setup_check(self, rows, verdicts, relation='authors_correction'):
        catalog, bounds = catlog.ROOT / 'copy.jsonl', catlog.ROOT / 'copy_bounds.jsonl'
        catalog.write_text(''.join(json.dumps(r) + '\n' for r in rows if not r.get('censored')))
        bounds.write_text(''.join(json.dumps(r) + '\n' for r in rows if r.get('censored')))
        folder = catlog.ROOT / 'work' / 'corrigendum_1' / '2'
        folder.mkdir(parents=True, exist_ok=True)
        for k, vs in zip('abc', verdicts):
            rel = relation[k] if isinstance(relation, dict) else relation
            (folder / f'verify_{k}.json').write_text(json.dumps({'relation': rel, 'relation_why': '', 'rows': vs}))
        return folder, catalog, bounds

    def test_helper_decisions(self):
        rows = [row('1', 'A1', '4400 ± 220'), row('1', 'A2', '1.8 ± 0.2', 'Km', unit='mM'),
                row('1', 'A3', '0.08 ± 0.01', 'Km', 'M1', unit='mM'), row('1', 'A4', '9 ± 1', 'kcat/Km', unit='mM^-1 s^-1'),
                row('1', 'A5', '0.36 ± 0.02', 'Km', 'M2', unit='µM', value=0.00036), row('1', 'A6', '0.5', 'Km', 'M3', unit='mM'),
                row('1', 'A7', '2.0', 'kcat', 'M4'), row('1', 'A8', '3.0', 'kcat', 'M5'),
                row('2', 'N1', '4400 ± 490'), row('2', 'N2', '0.08 ± 0.01', 'Km', 'M1', unit='mM', added='2026-11-12 00:00'),
                row('2', 'N3', '0.36 ± 0.02', 'Km', 'M2', unit='mM', value=0.36), row('2', 'N4', '7.0', 'kcat', 'M6')]
        common = [verdict('article', 'A1', 'SUPERSEDED', '4 400 ± 490', 'N1'),   # stored under the notice: dropped
                  verdict('article', 'A2', 'SUPERSEDED', '1.5 ± 0.2'),           # corrected cell not stored: waits
                  verdict('article', 'A3', 'UNCHANGED'),
                  verdict('article', 'A5', 'UNCHANGED'),
                  verdict('article', 'A6', 'UNIT', 'µM'),                        # unit stated in words: unitfix
                  verdict('article', 'A7', 'WITHDRAWN', why='wrong gene'),       # withdrawn: dropped, not an error
                  verdict('article', 'A8', 'RELABEL', why='apparent'),           # listed only
                  verdict('notice', 'N1', 'CORRECTED'),
                  verdict('notice', 'N2', 'REPRINTED', other='A3'),              # the article's cell again: dropped
                  verdict('notice', 'N3', 'REPRINTED', other='A5'),              # called a copy, unit differs: kept
                  verdict('notice', 'N4', 'NOT_OWN', why="ref 8's value")]       # credited to other work: dropped
        folder, catalog, bounds = self.setup_check(rows, [common + [verdict('article', 'A4', d, '8 ± 1')]
                                                          for d in ('SUPERSEDED', 'UNCHANGED', 'SUPERSEDED')])
        ev = [['2026-11-05 00:00', '1', 'text', 'europepmc']]  # the article's text was on disk before N2 was added
        drops, fixes, waiting, open_, kept, relabel, rel = corrigendum.plan('1', '2', folder, catalog, bounds, ev=ev)
        why = dict(drops)
        self.assertEqual(rel, 'authors_correction')
        self.assertEqual(L(why), ['A1', 'A7', 'N2', 'N4'])
        self.assertTrue(why[H('A1')].startswith("superseded by the authors' correction"))
        self.assertTrue(why[H('A7')].startswith("withdrawn by the authors' correction"))
        self.assertTrue(why[H('N2')].startswith('reprinted'))
        self.assertTrue(why[H('N4')].startswith('not its own'))
        self.assertEqual([(L([r])[0], u) for r, u, _ in fixes], [('A6', 'µM')])
        self.assertEqual(L(r for r, _ in waiting), ['A2'])
        self.assertEqual(L(r for r, _ in kept), ['A4', 'N3'])
        self.assertEqual(L(r for r, _ in relabel), ['A8'])
        self.assertEqual(open_, [])
        # the article's text arrived after the notice value was stored: a duplicate the rule allowed, not an error
        drops, *_ = corrigendum.plan('1', '2', folder, catalog, bounds, ev=[['2026-11-15 00:00', '1', 'text', 'x']])
        self.assertTrue(dict(drops)[H('N2')].startswith(f"duplicate of row {H('A3')}"))

    def test_helper_matches_censored_values_and_spelling(self):
        nd = lambda p, rid, **k: {**row(p, rid, 'ND', 'kcat/Km', 'N300A', unit='M^-1 s^-1', value=0), 'censored': 'not_detected',
                                  'value': None, 'unit': '', **k}
        bound = lambda p, rid, v, m='kcat', var='E133A', **k: {**row(p, rid, v, m, var, value=0), 'censored': {'≫': '>', '≪': '<'}.get(v.strip()[0], v.strip()[0]),
                                                              'value': None, 'unit': '', **k}
        rows = [row('1', 'A1', '0.0065 ± 0.0003', 'kcat/Km', 'N300A', unit='M^-1 s^-1'),
                bound('1', 'A2', '> 0.538'), bound('1', 'A3', '>> 1.8', 'Km'), nd('1', 'A4', var='N300D', limit='0.001 M^-1 s^-1'),
                row('1', 'A5', '55000 ± 5900', 'kcat/Km', 'HH'), row('1', 'A6', '4400 ± 220', 'kcat', 'HH'),
                nd('2', 'N1', limit='0.001 M^-1 s^-1'), bound('2', 'N2', '> 0.0025'),
                bound('2', 'N3', '≫ 1.8', 'Km'), nd('2', 'N4', var='N300D', limit='0.01 M^-1 s^-1'),
                row('2', 'N5', '54 000 ± 8100', 'kcat/Km', 'HH'), row('2', 'N6', '4400 ± 4900', 'kcat', 'HH')]
        cells = {'a': ('ND', '54 000 ± 8100'), 'b': ('ND (detection limit 0.001 M^-1 s^-1)', '54,000 ± 8,100'),
                 'c': ('n.d.', '54000±8100 M^-1 s^-1')}
        sets = [[verdict('article', 'A1', 'SUPERSEDED', cells[k][0], 'N1'),     # a number corrected to ND with a limit
                 verdict('article', 'A2', 'SUPERSEDED', '>0.0025', 'N2'),       # a bound corrected to another bound
                 verdict('article', 'A3', 'UNCHANGED'), verdict('article', 'A4', 'UNCHANGED'),
                 verdict('article', 'A5', 'SUPERSEDED', cells[k][1], 'N5'),     # spelled three ways, one cell
                 verdict('article', 'A6', 'SUPERSEDED', '4400 ± 490', 'N6'),    # the stored row prints another cell
                 verdict('notice', 'N1', 'CORRECTED'), verdict('notice', 'N2', 'CORRECTED'),
                 verdict('notice', 'N3', 'REPRINTED', other='A3'),              # '≫ 1.8' is the article's '>> 1.8'
                 verdict('notice', 'N4', 'REPRINTED', other='A4'),              # ND with another limit: a change
                 verdict('notice', 'N5', 'CORRECTED'), verdict('notice', 'N6', 'CORRECTED')] for k in 'abc']
        folder, catalog, bounds = self.setup_check(rows, sets)
        drops, fixes, waiting, open_, kept, relabel, rel = corrigendum.plan(
            '1', '2', folder, catalog, bounds, ev=[['2026-10-01 00:00', '1', 'text', 'x']])
        self.assertEqual(L(r for r, _ in drops), ['A1', 'A2', 'A5', 'N3'])
        self.assertEqual(L(r for r, _ in kept), ['N4'])                     # an ND with another limit is a change
        self.assertEqual(L(r for r, _ in open_), ['A6'])                    # the named row prints another cell: open
        self.assertEqual(waiting, [])

    def test_helper_supplement_and_unitfix_refusal(self):
        (catlog.TEXTS / '1.txt').write_text('Main text without the table.\n')
        (catlog.TEXTS / '1.supp.txt').write_text('=== Table S5\nWT | 3.1 ± 0.2\n')
        rows = [{**row('1', 'A1', '3.1 ± 0.2', loc='Table S5'), 'quote': 'WT | 3.1 ± 0.2'},
                {**row('2', 'N1', '3.1 ± 0.2', loc='Table S5'), 'added': '2026-10-18 22:03'},
                row('1', 'A2', '0.5', 'Km', 'M3', unit='mM')]
        vs = [verdict('article', 'A1', 'UNCHANGED'), verdict('notice', 'N1', 'REPRINTED', other='A1'),
              verdict('article', 'A2', 'UNIT', 'µM')]
        folder, catalog, bounds = self.setup_check(rows, [vs] * 3)
        ev = [['2026-10-16 13:21', '1', 'text', 'europepmc'], ['2026-10-29 07:58', '1', 'supplement', 'europepmc']]
        drops, fixes, *_ = corrigendum.plan('1', '2', folder, catalog, bounds, ev=ev)
        self.assertTrue(dict(drops)[H('N1')].startswith(f"duplicate of row {H('A1')}"))  # its supplement came after the copy
        catlog.CATALOG.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        catlog.BOUNDS.write_text('')
        catlog.LOG.write_text('\n'.join('\t'.join(f) for f in ev) + '\n')
        live = catlog.WORK / 'corrigendum_1' / '2'
        live.mkdir(parents=True, exist_ok=True)
        for k in 'abc':
            (live / f'verify_{k}.json').write_text(json.dumps({'relation': 'authors_correction', 'relation_why': '', 'rows': vs}))
        saved, corrigendum.catlog.cmd_unitfix = corrigendum.catlog.cmd_unitfix, lambda *a: set()  # unitfix refuses
        try:
            self.quiet(corrigendum.main, ['1', '2', '--apply'])
        finally:
            corrigendum.catlog.cmd_unitfix = saved
        self.assertEqual(self.lines('corrigendum_check'), [])                       # left open
        self.assertFalse((live / 'verify_a.json').exists())                        # moved with the run's evidence
        self.assertTrue(any(live.glob('applied_*/verify_a.json')))

    def test_unread_corrects_is_reported(self):
        self.quiet(catlog.finish, '90002002', {'note': ''}, [], [], corrects=['J Biol Chem 269:27458', None])
        self.assertEqual(self.lines('correction_notice'), [])
        self.assertEqual(len(self.lines('corrects_unread')), 1)
        self.assertEqual(catlog.corrected_ids('https://pubmed.ncbi.nlm.nih.gov/40465391/ and 41287407'), ['40465391', '41287407'])

    def test_helper_open_rather_than_close(self):
        rows = [row('1', 'A1', '1.0'), row('1', 'A2', '2.0', 'Km', 'M1', unit='mM'),
                row('1', 'A3', '9.5', 'kcat/Km', 'M2', unit='M^-1 s^-1', value=0.0095), row('2', 'N1', '1.5')]
        sets = [[verdict('article', 'A1', 'SUPERSEDED', '1.5', other) ,                     # 'none' / '' / 'none': waits
                 verdict('article', 'A2', d2, '2.5'),                                    # all say it must go, not how
                 verdict('article', 'A3', 'UNIT', unit),                                 # one unit, spelled two ways
                 verdict('notice', 'N1', 'CORRECTED')]
                for other, d2, unit in (('none', 'SUPERSEDED', 'mM^-1 s^-1'), ('', 'SUPERSEDED', 'mM-1 s-1'),
                                        ('none', 'WITHDRAWN', 'mM^-1 s^-1'))]
        folder, catalog, bounds = self.setup_check(rows, sets)
        drops, fixes, waiting, open_, kept, relabel, rel = corrigendum.plan('1', '2', folder, catalog, bounds, ev=[])
        self.assertEqual(L(r for r, _ in waiting), ['A1'])
        self.assertEqual(L(r for r, _ in open_), ['A2'])
        self.assertEqual(L(r for r, *_ in fixes), ['A3'])
        self.assertEqual((drops, kept), ([], []))

    def test_dry_run_never_rewrites_an_applied_run(self):
        rows = [row('1', 'A1', '1.0'), row('2', 'N1', '1.5')]
        vs = [verdict('article', 'A1', 'SUPERSEDED', '1.5', 'N1'), verdict('notice', 'N1', 'CORRECTED')]
        folder, catalog, bounds = self.setup_check(rows, [vs] * 3)
        applied = folder / 'applied_20261117-000000'
        applied.mkdir()
        for k in 'abc':
            (folder / f'verify_{k}.json').rename(applied / f'verify_{k}.json')
        (applied / 'drops.tsv').write_text(H('A1') + '\tthe applied run\n')
        self.quiet(corrigendum.main, ['1', '2', '--dir', str(applied), '--catalog', str(catalog), '--bounds', str(bounds)])
        self.assertEqual((applied / 'drops.tsv').read_text(), H('A1') + '\tthe applied run\n')

    def test_corrects_naming_the_notice_itself(self):
        self.quiet(catlog.finish, '90002002', {'note': ''}, [], [], corrects='10.1000/FIX')  # its own DOI in papers.tsv
        self.assertEqual(self.lines('correction_notice'), [])
        self.assertEqual(len(self.lines('corrects_unread')), 1)

    def test_helper_refuses_incomplete_verdicts(self):
        rows = [row('1', 'A1', '1.0'), row('2', 'N1', '2.0')]
        full = [verdict('article', 'A1', 'UNCHANGED'), verdict('notice', 'N1', 'CORRECTED')]
        for bad in ([full[0]],                                                  # a stored value not judged
                    [full[0], verdict('notice', 'N1', 'UNCHANGED')]):           # a decision of the wrong kind
            folder, catalog, bounds = self.setup_check(rows, [full, full, bad])
            with self.assertRaises(SystemExit):
                corrigendum.plan('1', '2', folder, catalog, bounds, ev=[])
        folder, catalog, bounds = self.setup_check(rows, [full] * 3, relation={'a': 'authors_correction', 'b': '', 'c': 'unsure'})
        with self.assertRaises(SystemExit):  # a file without a relation
            corrigendum.plan('1', '2', folder, catalog, bounds, ev=[])
        folder, catalog, bounds = self.setup_check(rows, [full] * 3, relation='not_a_correction')
        self.assertEqual(corrigendum.plan('1', '2', folder, catalog, bounds, ev=[])[-1], 'not_a_correction')

    def test_apply_drops_logs_and_stays_open_on_unsure(self):
        rows = [row('1', 'A1', '4400 ± 220'), row('1', 'A2', '1.0', 'Km', 'M1', unit='mM'), row('2', 'N1', '4400 ± 490')]
        catlog.CATALOG.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        base = [verdict('article', 'A1', 'SUPERSEDED', '4400 ± 490', 'N1'), verdict('notice', 'N1', 'CORRECTED')]
        folder = catlog.WORK / 'corrigendum_1' / '2'
        folder.mkdir(parents=True)
        for k, a2 in zip('abc', ('UNCHANGED', 'UNSURE', 'UNCHANGED')):
            (folder / f'verify_{k}.json').write_text(json.dumps({'relation': 'authors_correction', 'relation_why': '',
                                                                 'rows': base + [verdict('article', 'A2', a2)]}))
        self.quiet(corrigendum.main, ['1', '2', '--apply'])
        self.assertNotIn(H('A1'), catlog.CATALOG.read_text())               # dropped
        self.assertEqual(self.lines('corrigendum_check'), [])            # but the UNSURE value keeps it open
        self.assertTrue(any(folder.glob('applied_*/verify_a.json')))     # this run's verdicts kept beside the drops
        for k in 'abc':
            (folder / f'verify_{k}.json').write_text(json.dumps({'relation': 'authors_correction', 'relation_why': '',
                                                                 'rows': base + [verdict('article', 'A2', 'UNCHANGED')]}))
        self.quiet(corrigendum.main, ['1', '2', '--apply'])
        self.assertEqual([(l[1], l[3]) for l in self.lines('corrigendum_check')], [('1', '2')])


if __name__ == '__main__':
    unittest.main()
