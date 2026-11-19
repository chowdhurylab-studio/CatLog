#!/usr/bin/env python3
"""Offline test: a value dropped because its authors corrected it later in a correction notice ('superseded by the
authors' correction', 40465391 and its corrigendum 41287407) is not counted among CatLog's own errors
(human_review.catlog_errors), while a reprinted value dropped by a sweep still is: python3 tools/test_superseded_drop.py
The test runs in a temporary root (catlog's paths are pointed there); the live folder is never written."""
import json, sys, tempfile, unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import catlog  # noqa: E402

PATHS = ('ROOT', 'CATALOG', 'REJECTED', 'BOUNDS', 'LOG', 'LABEL_DROPS')


class Superseded(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(catlog, k) for k in PATHS}
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name).resolve()
        catlog.ROOT = root
        for k, name in (('CATALOG', 'catalog.jsonl'), ('REJECTED', 'rejected.jsonl'), ('BOUNDS', 'bounds.jsonl'),
                        ('LOG', 'log.tsv'), ('LABEL_DROPS', 'organism_label_drops.tsv')):
            setattr(catlog, k, root / name)
        catlog.CATALOG.write_text('')
        rows = [{'row_id': 'a' * 16, 'pmid': '90001001', 'why': ["audit: superseded by the authors' correction: x"]},
                {'row_id': 'b' * 16, 'pmid': '90001002', 'why': ['audit: reprinted: same measurement as PMID 1']}]
        catlog.REJECTED.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        catlog.LOG.write_text("2026-11-17 01:00\t90001001\tdrop\t" + 'a' * 16 + "\tsuperseded by the authors' correction: "
                              "their corrigendum PMID 90001003 prints this cell recalculated\n"
                              "2026-11-17 01:00\t90001002\tdrop\t" + 'b' * 16 + "\treprinted: same measurement as PMID 1\n")

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(catlog, k, v)
        self.tmp.cleanup()

    def test_superseded_is_not_an_error(self):
        import dbcheck, dbcompare, human_review
        saved = dbcompare.recorded, dbcheck.audit_first
        dbcompare.recorded, dbcheck.audit_first = (lambda *a, **k: {}), (lambda *a, **k: set())
        try:
            e = human_review.catlog_errors()
        finally:
            dbcompare.recorded, dbcheck.audit_first = saved
        self.assertEqual((e['sweep']['values'], e['sweep']['reprinted'], e['sweep']['other']), (1, 1, 0))
        self.assertEqual(e['all']['values'], 1)

    def test_a_unit_the_authors_corrected_is_not_an_error(self):
        import dbcheck, dbcompare, human_review
        note = lambda why: (f'unit corrected to µM (2026-11-17 10:00): {why}')
        rows = [{'row_id': 'c' * 16, 'pmid': '90001004', 'metric': 'Km', 'raw_value': '0.5', 'raw_unit': 'mM',
                 'unit_for_conversion': 'µM', 'value': 0.0005, 'unit': 'mM',
                 'verify_note': note("the authors' correction notice PMID 90001005 gives the unit of this cell as µM")},
                {'row_id': 'd' * 16, 'pmid': '90001006', 'metric': 'Km', 'raw_value': '0.5', 'raw_unit': 'mM',
                 'unit_for_conversion': 'µM', 'value': 0.0005, 'unit': 'mM',
                 'verify_note': note('Table 2 header misprinted: the text gives µM')}]
        catlog.CATALOG.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        saved = dbcompare.recorded, dbcheck.audit_first
        dbcompare.recorded, dbcheck.audit_first = (lambda *a, **k: {}), (lambda *a, **k: set())
        try:
            e = human_review.catlog_errors()
        finally:
            dbcompare.recorded, dbcheck.audit_first = saved
        self.assertEqual(e['unit_fix']['values'], 1)  # the misprinted header only


if __name__ == '__main__':
    unittest.main()
