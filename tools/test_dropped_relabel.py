#!/usr/bin/env python3
"""Offline tests: a value an audit dropped for its organism label alone (one drop, listed in
sources/organism_label_drops.tsv with the corrected label) comes back when a re-read gives exactly that label and the
same value, and nothing else comes back (catlog.organism_relabelled, append_rows, cmd_restore, cmd_unitfix):
python3 tools/test_dropped_relabel.py
Each test runs in its own temporary root (catlog's paths are pointed there); the live folder is never written."""
import contextlib, io, json, sys, tempfile, unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import catlog  # noqa: E402

PATHS = ('ROOT', 'CATALOG', 'REJECTED', 'BOUNDS', 'LOG', 'LABEL_DROPS')
PMID = '90001001'
ROW = {'pmid': PMID, 'enzyme': '4-chlorobenzoate:CoA ligase', 'organism': 'Pseudomonas sp.', 'strain': 'CBS3',
       'gene': '', 'variant': 'K492A', 'substrate': '4-CB', 'cosubstrate': '', 'pH': 7.5, 'temperature_C': 25,
       'location': 'Table 1', 'metric': 'kcat/Km', 'raw_value': '2 × 10^4', 'raw_unit': 'M^-1 s^-1', 'value': 20.0,
       'unit': 'mM^-1 s^-1', 'quote': 'K492A | 4-CB | 2 × 10^4', 'conditions': '', 'metric_note': ''}
DROPPED, WHEN = 'aaaaaaaaaaaaaaaa', '2026-11-15 00:00'
HEADER = 'row_id\tpmid\tdropped\torganism\torganism_now\tstrain_now\twhy\n'


class Relabel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = {k: getattr(catlog, k) for k in PATHS}

    @classmethod
    def tearDownClass(cls):
        for k, v in cls.saved.items():
            setattr(catlog, k, v)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name).resolve()
        catlog.ROOT = root
        for k, name in (('CATALOG', 'catalog.jsonl'), ('REJECTED', 'rejected.jsonl'), ('BOUNDS', 'bounds.jsonl'),
                        ('LOG', 'log.tsv'), ('LABEL_DROPS', 'organism_label_drops.tsv')):
            setattr(catlog, k, root / name)
        self.fresh()

    def tearDown(self):
        self.tmp.cleanup()

    def fresh(self):
        """Empty files in this test's root, for the next case of a loop."""
        for p in (catlog.CATALOG, catlog.REJECTED, catlog.LOG):
            p.write_text('')
        for p in (catlog.BOUNDS, catlog.LABEL_DROPS):
            p.unlink(missing_ok=True)

    def dropped(self, why='audit: wrong organism: the value is right', when=WHEN, listed=True, now=('', ''), **change):
        """One drop of row DROPPED in rejected.jsonl; listed: also its line in the label list, with the corrected label."""
        r = {**ROW, **change, 'row_id': DROPPED, 'why': [why], 'dropped': when}
        with open(catlog.REJECTED, 'a') as fh:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
        if listed:
            new = not catlog.LABEL_DROPS.exists()
            with open(catlog.LABEL_DROPS, 'a') as fh:
                fh.write(('# a comment line\n' + HEADER if new else '')
                         + f"{DROPPED}\t{PMID}\t{when}\t{r['organism']}\t{now[0]}\t{now[1]}\tthe value is right\n")

    def reread(self, organism, **change):
        """Add one re-read row; True when it was stored, False when refused as the dropped value."""
        r = {**ROW, 'strain': '', 'row_id': 'bbbbbbbbbbbbbbbb', **change, 'organism': organism}
        rejected = []
        new, dup, nb = catlog.append_rows(PMID, [r], rejected)
        if new:
            return True
        self.assertTrue(rejected and 'audit dropped this measurement before' in rejected[0]['why'][0], rejected)
        return False

    def test_the_corrected_label_comes_back_and_is_logged(self):
        self.dropped()
        self.assertTrue(self.reread(''))
        self.assertEqual(json.loads(catlog.CATALOG.read_text())['organism'], '')
        self.assertEqual(catlog.LOG.read_text().split('\t')[1:4], [PMID, 'relabelled', DROPPED])
        self.fresh(); self.dropped()
        self.assertTrue(self.reread('not stated'))  # a placeholder for none is no organism

    def test_anything_but_the_listed_label_stays_dropped(self):
        for org, change in (('Alcaligenes sp. ALP83', {}), ('Pseudomonas sp.', {}), ('pseudomonad', {}),
                            ('', {'strain': 'CBS3'}), ('', {'strain': 'CBS-3'}), ('', {'strain': 'CBS 3'}),
                            ('', {'gene': 'CBS3'}), ('', {'enzyme': 'Pseudomonas sp. CBS3 4-chlorobenzoate:CoA ligase'}),
                            ('', {'enzyme': '4-CBA:CoA ligase (CBS-3)'}), ('', {'construct': 'Pseudomonas CBL, His-tagged'})):
            with self.subTest(org=org, change=change):
                self.fresh(); self.dropped()
                self.assertFalse(self.reread(org, **change))

    def test_a_named_correction_must_be_the_listed_one(self):
        self.dropped(organism='', strain='', now=('Bacillus subtilis', '168'))
        self.assertTrue(self.reread('Bacillus subtilis', strain='168'))
        for org, strain in (('Escherichia coli', 'BL21(DE3)'), ('Bacillus subtilis', ''), ('B. subtilis', '168'), ('', '')):
            with self.subTest(org=org, strain=strain):
                self.fresh(); self.dropped(organism='', strain='', now=('Bacillus subtilis', '168'))
                self.assertFalse(self.reread(org, strain=strain))

    def test_a_value_converted_otherwise_stays_dropped(self):
        self.dropped()
        self.assertFalse(self.reread('', raw_unit='M^-1 min^-1', value=0.3333, unit='mM^-1 s^-1'))

    def test_only_the_listed_drop_counts(self):
        for why in ('audit: wrong organism: the value is right', 'audit: wrong organism and a reprint of ref 20',
                    'audit: reprinted from ref 4'):
            with self.subTest(why=why):  # unlisted: whatever the reason says
                self.fresh(); self.dropped(why=why, listed=False)
                self.assertFalse(self.reread(''))
        # the row came back by hand and an audit dropped it again for its value: that later drop is not listed
        self.fresh(); self.dropped()
        self.dropped(why='audit: misread cell: the page image prints 3 × 10^4', when='2026-11-16 09:00', listed=False)
        self.assertFalse(self.reread(''))

    def test_the_dropped_slot_stays_dropped_and_others_are_untouched(self):
        self.dropped()
        self.assertFalse(self.reread('Pseudomonas sp.', strain='CBS3', raw_value='3 × 10^4', value=30.0,
                                     quote='K492A | 4-CB | 3 × 10^4'))
        self.fresh(); self.dropped()
        self.assertTrue(self.reread('Pseudomonas sp.', strain='CBS3', substrate='ATP', raw_value='2 × 10^3', value=2.0,
                                    quote='E410A | ATP | 2 × 10^3'))

    def test_restore_and_unitfix_refuse_a_listed_drop_and_a_held_cell(self):
        for cmd in (lambda: catlog.cmd_restore('test', DROPPED), lambda: catlog.cmd_unitfix('M^-1 s^-1', 'test', DROPPED)):
            self.fresh(); self.dropped()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cmd()
            self.assertIn('dropped for its organism label', out.getvalue())
            self.assertEqual(catlog.CATALOG.read_text().strip(), '')
        self.fresh(); self.dropped(listed=False)  # unlisted, but the catalog holds the cell under another label
        catlog.CATALOG.write_text(json.dumps({**ROW, 'organism': '', 'strain': '', 'row_id': 'cccccccccccccccc'}) + '\n')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            catlog.cmd_restore('test', DROPPED)
        self.assertIn('not restored, the catalog already holds this cell', out.getvalue())

    def test_the_list_reads_comments_a_bom_and_padded_ids(self):
        catlog.LABEL_DROPS.write_text('﻿# comment\n' + HEADER + f' {DROPPED} \t{PMID}\t {WHEN}\tx\t\t\twhy\n',
                                      encoding='utf-8')
        self.assertEqual(set(catlog.label_drops()), {(DROPPED, WHEN)})

    def test_an_unreadable_list_stops_no_add(self):
        self.dropped()
        catlog.LABEL_DROPS.write_bytes(b'row_id\tdropped\n\xff\xfe\x00bad\n')
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(catlog.label_drops(), {})
            self.assertFalse(self.reread(''))  # its values stay dropped
            self.assertTrue(self.reread('', substrate='ATP', raw_value='2 × 10^3', value=2.0, quote='E410A | ATP | 2 × 10^3'))

    def test_whole_words_only(self):
        self.dropped(organism='Homo sapiens', strain='')
        self.assertTrue(self.reread('', construct='homodimeric, His-tagged'))  # 'homo' inside a word
        self.fresh(); self.dropped(organism='Homo sapiens', strain='')
        self.assertFalse(self.reread('', construct='Homo sapiens CBL, His-tagged'))

    def test_another_enzyme_name_stays_dropped(self):
        # twin() pairs any enzyme of one printed line: a listed drop brings back only its own enzyme's value
        self.dropped()
        self.assertFalse(self.reread('', enzyme='KARI (Spr)'))
        self.fresh(); self.dropped()
        self.assertTrue(self.reread('', enzyme='4-chlorobenzoate:CoA ligase (CBL)'))  # the same enzyme, glossed

    def test_a_listed_drop_is_used_up(self):
        self.dropped(quote='n = 5 fits give kcat/Km = 2 × 10^4 for K492A, kcat = 3.1 s-1')
        self.assertTrue(self.reread('', quote='kcat/Km = 2 × 10^4 for K492A, kcat = 3.1 s-1'))
        before = catlog.CATALOG.read_text()
        # a later read in another slot quoting the cell otherwise: it pairs with the drop, not with the returned row
        later = {**ROW, 'organism': '', 'strain': '', 'location': 'Figure 3 legend',
                 'quote': 'n = 5 fits give kcat/Km = 2 × 10^4', 'row_id': 'dddddddddddddddd'}
        self.assertFalse(catlog.same_quote(later, json.loads(before)))
        new, dup, nb = catlog.append_rows(PMID, [later], [])
        self.assertEqual((len(new), dup), (0, 1))
        self.assertEqual(catlog.CATALOG.read_text(), before)
        self.assertIn('reworded_duplicate', catlog.LOG.read_text())
        # two rows of one read pairing with one listed drop: the value comes back once
        self.fresh(); self.dropped(substrate='ATP', quote='K492A | ATP | 2 × 10^4')
        rows = [{**ROW, 'organism': '', 'strain': '', 'substrate': s, 'quote': 'K492A | ATP | 2 × 10^4', 'row_id': i}
                for s, i in (('MgATP', 'eeeeeeeeeeeeeeee'), ('ATP (Mg2+)', 'ffffffffffffffff'))]
        new, dup, nb = catlog.append_rows(PMID, rows, [])
        self.assertEqual((len(new), dup), (1, 1))

    def test_two_identities_of_one_cell_stay_out(self):
        # one quoted line prints the same cell for two enzymes: twin() cannot tell which drop a row is, so both values
        # stay dropped for a decision by hand (each row pairs with the other enzyme's drop too)
        for rid, enz in (('a1a1a1a1a1a1a1a1', 'KARI2 (Sli2)'), ('a2a2a2a2a2a2a2a2', 'KARI (Spr)')):
            r = {**ROW, 'enzyme': enz, 'quote': 'Sli2 8.6 | Spr 8.6 | 2 × 10^4', 'row_id': rid, 'why': ['audit: x'],
                 'dropped': WHEN}
            with open(catlog.REJECTED, 'a') as fh:
                fh.write(json.dumps(r) + '\n')
        catlog.LABEL_DROPS.write_text(HEADER + ''.join(f'{i}\t{PMID}\t{WHEN}\tPseudomonas sp.\t\t\twhy\n'
                                                       for i in ('a1a1a1a1a1a1a1a1', 'a2a2a2a2a2a2a2a2')))
        rows = [{**ROW, 'organism': '', 'strain': '', 'enzyme': e, 'quote': 'Sli2 8.6 | Spr 8.6 | 2 × 10^4', 'row_id': i}
                for e, i in (('KARI2 (Sli2)', 'b1b1b1b1b1b1b1b1'), ('KARI (Spr)', 'b2b2b2b2b2b2b2b2'))]
        rejected = []
        new, dup, nb = catlog.append_rows(PMID, rows, rejected)
        self.assertEqual((len(new), dup, len(rejected)), (0, 0, 2))

    def test_a_used_drop_whose_value_was_refuted_later_blocks(self):
        self.dropped()
        self.assertTrue(self.reread(''))  # back as bbbbbbbbbbbbbbbb
        with contextlib.redirect_stdout(io.StringIO()):
            catlog.cmd_drop('bbbbbbbbbbbbbbbb', 'misread cell: the page image prints 3 × 10^4')
        self.assertFalse(self.reread('', row_id='cccccccccccccccc'))
        self.assertFalse(self.reread('', row_id='dddddddddddddddd', quote='K492A | 4-CB | 2 × 10^4 (Table 1)'))

    def test_a_second_strain_correction_of_the_same_row_id_comes_back(self):
        self.dropped(organism='Bacillus subtilis', strain='168', now=('Bacillus subtilis', 'W23'))
        self.assertTrue(self.reread('Bacillus subtilis', strain='W23', row_id=DROPPED))  # the same row_id comes back
        with contextlib.redirect_stdout(io.StringIO()):
            catlog.cmd_drop(DROPPED, 'wrong organism: the strain is PY79')
        stamp = json.loads(catlog.REJECTED.read_text().splitlines()[-1])['dropped']
        with open(catlog.LABEL_DROPS, 'a') as fh:
            fh.write(f'{DROPPED}\t{PMID}\t{stamp}\tBacillus subtilis\tBacillus subtilis\tPY79\twhy\n')
        self.assertFalse(self.reread('Bacillus subtilis', strain='W23', row_id='cccccccccccccccc'))
        self.assertTrue(self.reread('Bacillus subtilis', strain='PY79', row_id='dddddddddddddddd'))

    def test_a_second_correction_comes_back(self):
        self.dropped()
        self.assertTrue(self.reread(''))  # back as bbbbbbbbbbbbbbbb with organism ''
        with contextlib.redirect_stdout(io.StringIO()):
            catlog.cmd_drop('bbbbbbbbbbbbbbbb', 'wrong organism: the paper names Alcaligenes sp. for its own enzyme')
        stamp = json.loads(catlog.REJECTED.read_text().splitlines()[-1])['dropped']
        with open(catlog.LABEL_DROPS, 'a') as fh:
            fh.write(f'bbbbbbbbbbbbbbbb\t{PMID}\t{stamp}\t\tAlcaligenes sp.\t\twhy\n')
        self.assertFalse(self.reread('', row_id='cccccccccccccccc'))  # the label refuted second stays out
        new, dup, nb = catlog.append_rows(PMID, [{**ROW, 'organism': 'Alcaligenes sp.', 'strain': '',
                                                  'row_id': 'dddddddddddddddd'}], [])
        self.assertEqual([r['organism'] for r in new], ['Alcaligenes sp.'])

    def test_a_used_drop_raises_a_conflict_for_another_conversion(self):
        self.dropped(quote='n = 5 fits give kcat/Km = 2 × 10^4 for K492A, kcat = 3.1 s-1')
        self.assertTrue(self.reread('', quote='kcat/Km = 2 × 10^4 for K492A, kcat = 3.1 s-1'))
        rejected = []
        later = {**ROW, 'organism': '', 'strain': '', 'location': 'Figure 3 legend', 'raw_unit': 'M^-1 min^-1',
                 'value': 0.3333, 'quote': 'n = 5 fits give kcat/Km = 2 × 10^4', 'row_id': 'dddddddddddddddd'}
        new, dup, nb = catlog.append_rows(PMID, [later], rejected)
        self.assertEqual((len(new), dup), (0, 0))
        self.assertIn('converted differently', rejected[0]['why'][0])

    def test_plural_and_digit_words_carry_the_old_label(self):
        self.dropped(organism='rat', strain='', now=('Mus musculus', ''))
        self.assertFalse(self.reread('Mus musculus', construct='purified from livers of male rats'))
        self.fresh(); self.dropped(organism='rat', strain='', now=('Mus musculus', ''))
        self.assertTrue(self.reread('Mus musculus', construct='in 50 mM citrate buffer'))
        self.fresh(); self.dropped(organism='Synechococcus elongatus', strain='PCC 7942')
        self.assertFalse(self.reread('', gene='Synpcc7942_1593'))

    def test_restore_stops_on_an_unreadable_list(self):
        self.dropped()
        catlog.LABEL_DROPS.write_bytes(b'row_id\tdropped\n\xff\xfe\x00bad\n')
        with self.assertRaises(SystemExit):
            catlog.cmd_restore('test', DROPPED)
        self.assertEqual(catlog.CATALOG.read_text().strip(), '')

    def test_a_cut_relabelled_line_is_ignored(self):
        self.dropped()
        catlog.LOG.write_text(f'2026-11-15 00:01\t{PMID}\trelabelled\t{DROPPED}\n')
        self.assertTrue(self.reread(''))

    def test_counted_as_label_corrections_not_removals(self):
        # an audit drop of the row, its return under the right label, then the audit summary and relabelled_drops
        catlog.LOG.write_text(f'2026-11-14 23:00\t{PMID}\taudit_drop\t{DROPPED}\twrong organism: right value\n'
                              f'2026-11-14 23:00\t{PMID}\tdrop\t{DROPPED}\twrong organism: right value\n')
        self.dropped()
        self.assertTrue(self.reread(''))  # back as bbbbbbbbbbbbbbbb
        self.assertEqual(catlog.relabelled_drops(), {DROPPED: PMID})
        self.assertEqual(catlog.audit_summary(), (1, 0, 0))  # not wrong, and no unit corrected
        self.assertEqual(catlog.audit_summary(split=True), (1, 0, 0, 1))  # a label corrected
        # the returned value refuted later (a misread): the drop was a value error after all
        with contextlib.redirect_stdout(io.StringIO()):
            catlog.cmd_drop('bbbbbbbbbbbbbbbb', 'misread cell')
        self.assertEqual(catlog.relabelled_drops(), {})
        self.assertEqual(catlog.audit_summary(split=True), (1, 1, 0, 0))

    def test_relabelled_drops_follows_a_chain_and_the_same_row_id(self):
        A, B, C, D = (c * 16 for c in 'abcd')
        catlog.LOG.write_text(f'2026-11-15 00:01\t{PMID}\trelabelled\t{A}\t{B}\tx\t2026-11-15 00:00\n'
                              f'2026-11-15 00:02\t{PMID}\tdrop\t{B}\twrong organism: second\n'
                              f'2026-11-15 00:03\t{PMID}\trelabelled\t{B}\t{C}\tx\t2026-11-15 00:02\n'
                              f'2026-11-15 00:04\t{PMID}\trelabelled\t{D}\t{D}\tx\t2026-11-15 00:00\n'
                              f'2026-11-15 00:05\t{PMID}\trelabelled\t\t{D}\tx\t2026-11-15 00:00\n'  # no dropped id
                              f'2026-11-15 00:06\t{PMID}\trelabelled\t{A}\n')  # cut short
        catlog.CATALOG.write_text(f'{{"row_id": "{C}"}}\n{{"row_id": "{D}"}}\n')
        self.assertEqual(catlog.relabelled_drops(), {A: PMID, B: PMID, D: PMID})
        catlog.CATALOG.write_text(f'{{"row_id": "{D}"}}\n')  # C dropped since: A's and B's values are gone
        self.assertEqual(catlog.relabelled_drops(), {D: PMID})

    def test_catlog_errors_counts_them_as_label_corrections(self):
        import dbcheck, dbcompare, human_review
        saved = dbcompare.recorded, dbcheck.audit_first
        dbcompare.recorded, dbcheck.audit_first = (lambda *a, **k: {}), (lambda *a, **k: set())
        try:
            catlog.LOG.write_text(f'2026-11-14 23:00\t{PMID}\taudit_drop\t{DROPPED}\twrong organism: right value\n'
                                  f'2026-11-14 23:00\t{PMID}\tdrop\t{DROPPED}\twrong organism: right value\n'
                                  f'2026-11-14 23:01\t{PMID}\tdrop\tcccccccccccccccc\twrong organism: right value\n')
            self.dropped()
            with open(catlog.REJECTED, 'a') as fh:  # a second value of the paper, dropped and listed the same way
                fh.write(json.dumps({**ROW, 'row_id': 'cccccccccccccccc', 'substrate': 'ATP', 'raw_value': '2 × 10^3',
                                     'value': 2.0, 'quote': 'E410A | ATP | 2 × 10^3', 'why': ['audit: wrong organism'],
                                     'dropped': WHEN}) + '\n')
            with open(catlog.LABEL_DROPS, 'a') as fh:
                fh.write(f'cccccccccccccccc\t{PMID}\t{WHEN}\tPseudomonas sp.\t\t\twhy\n')
            new, dup, nb = catlog.append_rows(PMID, [
                {**ROW, 'organism': '', 'strain': '', 'row_id': 'bbbbbbbbbbbbbbbb'},
                {**ROW, 'organism': '', 'strain': '', 'substrate': 'ATP', 'raw_value': '2 × 10^3', 'value': 2.0,
                 'quote': 'E410A | ATP | 2 × 10^3', 'row_id': 'dddddddddddddddd'}], [])
            self.assertEqual(len(new), 2)
            e = human_review.catlog_errors()
            self.assertEqual((e['audit']['removed'], e['audit']['corrected'], e['sweep']['values']), (0, 1, 0))
            self.assertEqual((e['label_fix']['values'], e['all']['values']), (2, 2))
        finally:
            dbcompare.recorded, dbcheck.audit_first = saved

    def test_a_key_two_drops_share_is_not_listed(self):
        self.dropped()
        self.dropped(why='audit: reprinted from ref 20, not measured here', listed=False)  # restored and dropped again, same minute
        self.assertFalse(self.reread(''))


if __name__ == '__main__':
    unittest.main(verbosity=1)
