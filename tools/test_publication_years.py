"""Tests for tools/publication_years.py and site_release.publication_years (offline: NCBI is never called).

  python3 -m unittest tools/test_publication_years.py      (from the CatLog root)
"""
import csv, io, json, os, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import publication_years as py  # noqa: E402

LIVE_WORK = TOOLS.parent / 'work' / 'brenda_lag_20261021'  # only read
CATLOG_BY_YEAR = LIVE_WORK / 'broad' / 'catlog_by_year.py'
FIG2A = LIVE_WORK / 'figures' / 'fig2a_data.csv'
FIG1A = LIVE_WORK / 'figures' / 'fig1a_data.csv'  # BRENDA's papers per year, same analysis run
CONTRACT = {'brenda_release', 'as_of', 'first_year', 'last_year', 'years', 'catlog_values_total', 'catlog_papers_total',
            'catlog_values_without_year', 'catlog_after_last_year'}
ADDED = {'definition', 'catlog_papers_without_year', 'catlog_before_first_year'}


def answer(uid, date):
    return json.dumps({'uid': uid, 'pubdate': date, 'sortpubdate': f'{date}/01/01 00:00' if date else ''}) + '\n'


class FakeNCBI:
    """urlopen stand-in: answers esummary requests from {pmid: year}; fail=True raises like a dead network."""
    def __init__(self, years, fail=False):
        self.years, self.fail, self.calls = years, fail, []

    def __call__(self, url, timeout=None):
        self.calls.append(url)
        if self.fail:
            raise OSError('network down')
        ids = url.split('id=')[1].split('&')[0].replace('%2C', ',').split(',')
        res = {'uids': ids}
        for i in ids:
            y = self.years.get(i)
            res[i] = {'pubdate': f'{y} Jan', 'sortpubdate': f'{y}/01/01 00:00'} if y else {'error': 'cannot get document summary'}
        return io.BytesIO(json.dumps({'result': res}).encode())


class Root:
    """A throwaway CatLog root: catalog.jsonl, papers.tsv (every catalog paper done unless given), the BRENDA per-year
    file, seed caches under work/."""
    def __init__(self, tmp, catalog, seeds=(), brenda=None, statuses=None):
        self.path = Path(tmp)
        (self.path / 'sources').mkdir()
        with open(self.path / 'catalog.jsonl', 'w') as fh:
            for i, p in enumerate(catalog):
                fh.write(json.dumps({'row_id': f'r{i}', 'pmid': p, 'metric': 'kcat'}) + '\n')
        self.papers(statuses if statuses is not None else {p: 'done' for p in catalog})
        brenda = brenda or {y: 100 + y - 2000 for y in range(2000, 2026)}
        with open(self.path / py.BRENDA, 'w') as fh:
            fh.write('# test file\n# release: BRENDA 2026.1\nyear\tbrenda_values\n')
            fh.writelines(f'{y}\t{v}\n' for y, v in sorted(brenda.items()))
        for rel, lines in zip(py.SEEDS, seeds):
            (self.path / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.path / rel).write_text(''.join(lines))

    def papers(self, statuses):
        """papers.tsv with these {pmid: status}, in its own columns (a title with a quote, as real ones have)."""
        with open(self.path / 'papers.tsv', 'w') as fh:
            fh.write('pmid\tdoi\ttitle\tstatus\ttext_source\tkept\trejected\tnote\tupdated\n')
            fh.writelines(f'{p}\t\tA 5\' title\t{s}\tlocal\t1\t0\t\t2026-10-20 10:00\n' for p, s in statuses.items())


class Counting(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='pubyears-')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_years_from_cache_order_and_fields(self):
        p = Path(self.tmp) / 'c.jsonl'
        p.write_text(answer('1', '1999') + json.dumps({'uid': '2', 'pubdate': '2004 Mar', 'sortpubdate': None}) + '\n'
                     + answer('1', '2001') + answer('3', '') + answer('1', '') + '{"uid": "4", "pubd')  # cut-off last line
        year, answered = py.load_years([p])
        self.assertEqual(year, {'1': 2001, '2': 2004})  # later dated line wins, pubdate when no sortpubdate
        self.assertEqual(answered, {'1', '2', '3'})  # 3 answered without a date; the cut-off 4 is fetched again

    def test_contract_counts(self):
        cat = ['10'] * 3 + ['11'] + ['12'] * 2 + ['13'] + ['NP0A1B2C3D'] * 4 + ['14'] + ['15'] * 2
        seeds = ([answer('10', '2000'), answer('11', '2000'), answer('12', '2025'), answer('13', '2026'),
                  answer('15', '1990')], [answer('99', '2010')])
        r = Root(self.tmp, cat, seeds)
        out = py.summary(r.path, online=False, log=lambda m: None)
        self.assertEqual(set(out), CONTRACT | ADDED)
        self.assertEqual((out['brenda_release'], out['first_year'], out['last_year']), ('BRENDA 2026.1', 2000, 2025))
        ys = {y['year']: y for y in out['years']}
        self.assertEqual(sorted(ys), list(range(2000, 2026)))
        self.assertEqual(ys[2000], {'year': 2000, 'brenda_values': 100, 'catlog_values': 4, 'catlog_papers': 2})
        self.assertEqual(ys[2025], {'year': 2025, 'brenda_values': 125, 'catlog_values': 2, 'catlog_papers': 1})
        self.assertEqual(ys[2010]['catlog_values'], 0)
        self.assertEqual((out['catlog_values_total'], out['catlog_papers_total']), (14, 7))
        self.assertEqual(out['catlog_values_without_year'], 5)  # 4 stand-in rows + paper 14 (no cache, offline)
        self.assertEqual(out['catlog_papers_without_year'], 2)
        self.assertEqual(out['catlog_after_last_year'], {'values': 1, 'papers': 1})
        self.assertEqual(out['catlog_before_first_year'], {'values': 2, 'papers': 1})
        dated = sum(y['catlog_values'] for y in out['years'])
        self.assertEqual(dated + out['catlog_after_last_year']['values'] + out['catlog_before_first_year']['values']
                         + out['catlog_values_without_year'], out['catlog_values_total'])

    def test_standins_dated_by_brenda_year_and_mass_units_left_out(self):
        # a stand-in is dated by BRENDA's reference year (nopmid_refs.tsv), as BRENDA's side dates its references without
        # a PubMed ID; one with two years there, or none, stays without a year; a Km or kcat/Km per mass concentration
        # (units.MASS_UNIT) is not one of the site's values and is not counted
        r = Root(self.tmp, [], ([answer('10', '2005')],))
        rows = [('10', 'mM'), ('10', 'mg/mL'), ('NP0A1B2C3D', 'mM'), ('NP0A1B2C3D', 'mM^-1 s^-1'), ('NPFFFF0000', 's^-1'),
                ('NP11112222', 's^-1'), ('NP33334444', 'mL mg^-1 s^-1')]
        with open(r.path / 'catalog.jsonl', 'w') as fh:
            fh.writelines(json.dumps({'row_id': f'r{i}', 'pmid': p, 'unit': u}) + '\n' for i, (p, u) in enumerate(rows))
        r.papers({p: 'done' for p, _ in rows})
        (r.path / py.NOPMID).write_text('key\tpaper_id\ttitle\tyear\n' + 'B1\tNP0A1B2C3D\tA\t2012\nB2\tNP0A1B2C3D\tA\t2012\n'
                                        'B3\tNP11112222\tB\t2003\nB4\tNP11112222\tB\t2004\nB5\tNP33334444\tC\t2010\n')
        out = py.summary(r.path, online=False, log=lambda m: None)
        ys = {y['year']: (y['catlog_values'], y['catlog_papers']) for y in out['years'] if y['catlog_values']}
        self.assertEqual(ys, {2005: (1, 1), 2012: (2, 1)})
        self.assertEqual((out['catlog_values_total'], out['catlog_papers_total']), (5, 4))  # NP33334444: mass only
        self.assertEqual((out['catlog_values_without_year'], out['catlog_papers_without_year']), (2, 2))
        self.assertEqual(py.catalog_pmids(r.path / 'catalog.jsonl'), [p for p, _ in rows])  # catlog_by_year's count
        self.assertEqual(py.standin_years(r.path / py.NOPMID), {'NP0A1B2C3D': 2012, 'NP33334444': 2010})
        self.assertEqual(py.standin_years(r.path / 'missing.tsv'), {})

    def test_only_papers_the_site_shows(self):
        # the site shows CatLog's values only for papers papers.tsv marks done (site_release's site data rule), so the
        # totals are the values of its records read from the paper: a paper still reading, waiting for a supplement or a
        # fuller copy, or not in papers.tsv at all counts nothing, and a done paper whose values are all per mass
        # concentration is not one of the papers either
        cat = ['10'] * 3 + ['11'] * 2 + ['12', '13', '14', '15'] + ['NP0A1B2C3D'] * 2
        statuses = {'10': 'done', '11': 'needs_supplement', '12': 'incomplete', '13': 'reading', '14': 'todo',
                    'NP0A1B2C3D': 'done', '16': 'done', '17': 'done'}  # 15: not in papers.tsv; 17: done, kept nothing
        r = Root(self.tmp, cat, ([answer(p, '2005') for p in ('10', '11', '12', '13', '14', '15', '16')],), statuses=statuses)
        with open(r.path / 'catalog.jsonl', 'a') as fh:
            fh.write(json.dumps({'row_id': 'm1', 'pmid': '16', 'metric': 'Km', 'unit': 'mg/mL'}) + '\n')
        out = py.summary(r.path, online=False, log=lambda m: None)
        self.assertEqual((out['catlog_values_total'], out['catlog_papers_total']), (5, 2))
        self.assertEqual({y['year']: (y['catlog_values'], y['catlog_papers']) for y in out['years'] if y['catlog_values']},
                         {2005: (3, 1)})
        self.assertEqual((out['catlog_values_without_year'], out['catlog_papers_without_year']), (2, 1))  # the stand-in
        self.assertEqual(py.done_papers(r.path / 'papers.tsv'), {'10', 'NP0A1B2C3D', '16', '17'})
        # `site build` passes its own paper set (site_release._v2_done): that set, not papers.tsv, decides
        out = py.summary(r.path, online=False, log=lambda m: None, papers=['10', '11'])
        self.assertEqual((out['catlog_values_total'], out['catlog_papers_total']), (5, 2))
        self.assertEqual({y['year']: y['catlog_values'] for y in out['years'] if y['catlog_values']}, {2005: 5})
        (r.path / 'papers.tsv').unlink()
        with self.assertRaises(FileNotFoundError):  # no papers.tsv: no paper is known to be shown (site_release: no figure)
            py.summary(r.path, online=False, log=lambda m: None)
        self.assertEqual(py.summary(r.path, online=False, log=lambda m: None, papers={'12'})['catlog_values_total'], 1)

    def test_as_of(self):
        # the day given (`site build`: its snapshot's day), else the day counted in UTC, as the snapshot's generated_at
        r = Root(self.tmp, ['10'], ([answer('10', '2003')],))
        os.utime(r.path / 'catalog.jsonl', (0, 0))  # no longer the catalog's last change (1970 here)
        days = {time.strftime('%Y-%m-%d', time.gmtime())}
        out = py.summary(r.path, online=False, log=lambda m: None)
        days.add(time.strftime('%Y-%m-%d', time.gmtime()))
        self.assertIn(out['as_of'], days)
        self.assertEqual(py.summary(r.path, online=False, log=lambda m: None, as_of='2026-10-22')['as_of'], '2026-10-22')

    def test_seed_once_and_read_only(self):
        seeds = ([answer('10', '2003')], [answer('11', '2004')])
        r = Root(self.tmp, ['10', '11'], seeds)
        before = {s: ((r.path / s).read_bytes(), (r.path / s).stat().st_mtime_ns) for s in py.SEEDS}
        py.summary(r.path, online=False, log=lambda m: None)
        cache = r.path / py.CACHE
        lines = [json.loads(line) for line in cache.read_text().splitlines()]
        self.assertEqual([set(e) for e in lines], [{'uid', 'pubdate', 'sortpubdate'}] * 2)
        self.assertEqual({s: ((r.path / s).read_bytes(), (r.path / s).stat().st_mtime_ns) for s in py.SEEDS}, before)
        (r.path / py.SEEDS[0]).write_text(answer('10', '1980'))  # a seed changed later is not seeded again
        out = py.summary(r.path, online=False, log=lambda m: None)
        self.assertEqual({y['year']: y['catlog_values'] for y in out['years'] if y['catlog_values']}, {2003: 1, 2004: 1})

    def test_fetch_only_new_papers_in_batches(self):
        new = [str(1000 + i) for i in range(450)]
        r = Root(self.tmp, ['10'] + new + ['NP0A1B2C3D'], ([answer('10', '2001')],))
        fake = FakeNCBI({p: 2024 for p in new[:-1]})  # the last one: NCBI has no summary
        orig = py.fetch
        py.fetch = lambda pmids, cache, **kw: orig(pmids, cache, urlopen=fake, sleep=lambda s: None, log=lambda m: None)
        try:
            out = py.summary(r.path, log=lambda m: None)
            self.assertEqual(len(fake.calls), 3)  # 450 new PMIDs, 200 per request; 10 is cached, stand-ins never asked
            self.assertTrue(all('NP0A1B2C3D' not in c and 'id=10%2C' not in c for c in fake.calls))
            ys = {y['year']: y['catlog_values'] for y in out['years']}
            self.assertEqual((ys[2001], ys[2024], out['catlog_values_without_year']), (1, 449, 2))
            fake.calls.clear()
            py.summary(r.path, log=lambda m: None)  # all answered now, the undated one included: nothing fetched
            self.assertEqual(fake.calls, [])
        finally:
            py.fetch = orig

    def test_failed_fetch_never_raises(self):
        new = [str(1000 + i) for i in range(450)]
        r = Root(self.tmp, ['10'] + new, ([answer('10', '2001')],))
        fake = FakeNCBI({}, fail=True)
        msgs = []
        got = py.fetch(new, r.path / py.CACHE, urlopen=fake, sleep=lambda s: None, log=msgs.append)
        self.assertEqual(got, 0)
        self.assertEqual(len(fake.calls), py.TRIES)  # the first request failed 3 times: no more requests
        self.assertIn('450 papers count as without a year', msgs[-1])
        orig = py.fetch
        py.fetch = lambda pmids, cache, **kw: orig(pmids, cache, urlopen=fake, sleep=lambda s: None, log=lambda m: None)
        try:
            out = py.summary(r.path, log=lambda m: None)
        finally:
            py.fetch = orig
        self.assertEqual((out['catlog_values_without_year'], out['catlog_values_total']), (450, 451))

    def test_catalog_line_in_flight(self):
        p = Path(self.tmp) / 'catalog.jsonl'
        p.write_text('{"pmid": "1"}\n\n{"pmid": "2"}\n{"pmid": "3", "met')  # another chat's add writing its last line
        self.assertEqual(py.catalog_pmids(p), ['1', '2'])
        p.write_text('{"pmid": "1"}\n{"pmid": \n{"pmid": "2"}\n')
        with self.assertRaises(ValueError):
            py.catalog_pmids(p)


    def test_brenda_papers(self):
        # the per-year file's brenda_papers column gives the years' BRENDA papers and their sum; a file without the
        # column (or missing a compared year) gives neither, so the figure says nothing it cannot back
        r = Root(self.tmp, ['10'], ([answer('10', '2003')],))
        rows = ''.join(f'{y}\t{100 + y - 2000}\t{10 + y - 2000}\n' for y in range(2000, 2026))
        (r.path / py.BRENDA).write_text('# test file\n# release: BRENDA 2026.1\nyear\tbrenda_values\tbrenda_papers\n' + rows)
        out = py.summary(r.path, online=False, log=lambda m: None)
        self.assertEqual(set(out), CONTRACT | ADDED | {'brenda_papers_total'})
        ys = {y['year']: y for y in out['years']}
        self.assertEqual(ys[2003], {'year': 2003, 'brenda_values': 103, 'brenda_papers': 13, 'catlog_values': 1,
                                    'catlog_papers': 1})
        self.assertEqual(out['brenda_papers_total'], sum(range(10, 36)))
        (r.path / py.BRENDA).write_text('# release: BRENDA 2026.1\nyear\tbrenda_values\tbrenda_papers\n'
                                        + rows.replace('2025\t125\t35', '2025\t125\t'))
        out = py.summary(r.path, online=False, log=lambda m: None)
        self.assertNotIn('brenda_papers_total', out)
        self.assertTrue(all('brenda_papers' not in y for y in out['years']))


@unittest.skipUnless((TOOLS.parent / py.BRENDA).exists(), 'needs sources/brenda_values_by_year_2026_1.tsv '
                     '(BRENDA counts, not in this repository)')
class Shipped(unittest.TestCase):
    def test_brenda_file(self):
        release, by = py.brenda_by_year(TOOLS.parent / py.BRENDA)
        self.assertEqual(release, 'BRENDA 2026.1')
        self.assertEqual(sorted(by), list(range(2000, 2026)))
        self.assertEqual((by[2000], by[2009], by[2025]), (6561, 14970, 500))
        if FIG2A.exists():  # the approved figure's numbers, unchanged
            src = {int(r['year']): int(float(r['brenda_values'])) for r in csv.DictReader(open(FIG2A))}
            self.assertEqual(by, src)
        papers = py.brenda_papers_by_year(TOOLS.parent / py.BRENDA)
        self.assertEqual(sorted(papers), list(range(2000, 2026)))
        self.assertEqual((papers[2000], papers[2025]), (906, 39))
        if FIG1A.exists():  # the same analysis run's paper counts, unchanged
            src = {int(r['year']): int(float(r['brenda_papers'])) for r in csv.DictReader(open(FIG1A))}
            self.assertEqual(papers, {y: src[y] for y in papers})


@unittest.skipUnless(CATLOG_BY_YEAR.exists(), 'the BRENDA lag analysis script is not on this machine')
class SameAsCatlogByYear(unittest.TestCase):
    """The other chat's catlog_by_year.py, run on a copy in a temporary tree, counts as this module does."""
    def test_same_counts(self):
        with tempfile.TemporaryDirectory(prefix='pubyears-cby-') as tmp:
            root = Path(tmp)
            broad = root / 'work' / 'x' / 'broad'
            (root / 'work' / 'x' / 'cache').mkdir(parents=True)
            broad.mkdir()
            shutil.copyfile(CATLOG_BY_YEAR, broad / 'catlog_by_year.py')
            cat = ['10'] * 3 + ['11', '12', '12', '13', 'NP0A1B2C3D', 'NP0A1B2C3D', '14']
            cache = [answer('10', '1975'), answer('11', '2000'), answer('12', '2026'), answer('12', ''),
                     answer('13', ''), answer('14', '2025')]
            (root / 'work' / 'x' / 'cache' / 'ncbi_esummary.jsonl').write_text(''.join(cache[:4]))
            (broad / 'pubmed_years_extra.jsonl').write_text(''.join(cache[4:]))
            with open(root / 'catalog.jsonl', 'w') as fh:
                fh.writelines(json.dumps({'pmid': p}) + '\n' for p in cat)
            # 13 has no date, so catlog_by_year.py asks NCBI again: block the network for it
            env = {**os.environ, 'https_proxy': 'http://127.0.0.1:9', 'HTTPS_PROXY': 'http://127.0.0.1:9'}
            subprocess.run([sys.executable, str(broad / 'catlog_by_year.py')], check=True, capture_output=True, env=env,
                           timeout=120)
            theirs = json.loads((broad / 'catlog_by_year.json').read_text())
            year, _ = py.load_years([root / 'work' / 'x' / 'cache' / 'ncbi_esummary.jsonl', broad / 'pubmed_years_extra.jsonl'])
            ours = py.catlog_by_year(py.catalog_pmids(root / 'catalog.jsonl'), year, theirs['as_of'])
            self.assertEqual(ours, theirs)


class SiteRelease(unittest.TestCase):
    def test_never_fails_the_build(self):
        import site_release
        with tempfile.TemporaryDirectory(prefix='pubyears-site-') as tmp:
            self.assertIsNone(site_release.publication_years(tmp, online=False))  # no catalog, no BRENDA file
            os.mkdir(tmp + '/r')
            r = Root(tmp + '/r', [])
            (r.path / 'catalog.jsonl').write_text('{"pmid": "10"}\n{"pmid": "NP0A1B2C3D"}\n{"pmid": "11"}\n')
            r.papers({'10': 'done', 'NP0A1B2C3D': 'done', '11': 'needs_supplement'})
            out = site_release.publication_years(r.path, online=False)
            self.assertEqual((out['catlog_values_total'], out['catlog_values_without_year']), (2, 2))
            out = site_release.publication_years(r.path, online=False, papers={'10', '11'})  # build's _v2_done set
            self.assertEqual((out['catlog_values_total'], out['catlog_papers_total']), (2, 2))
            (r.path / 'papers.tsv').unlink()
            self.assertIsNone(site_release.publication_years(r.path, online=False))  # no papers.tsv: no figure
            (r.path / py.BRENDA).write_text('year\tbrenda_values\n2000\t1\n')  # no release line
            self.assertIsNone(site_release.publication_years(r.path, online=False))

    def test_dated_by_the_snapshot_day(self):
        # the exporter dates the snapshot (generated_at, UTC) after the years were counted: build gives the years the
        # snapshot's day, in the bundle's manifest.js (its first line; the shard-registry lines stay) and in what it returns
        import site_release
        pub = {'brenda_release': 'BRENDA 2026.1', 'as_of': '2026-10-22', 'catlog_values_total': 5}
        manifest = {'generated_at': '2026-10-23T00:41:07+00:00', 'total_rows': 9,
                    'summary': {'overview': {'records': 9}, 'publication_years': pub, 'other': 1}}
        with tempfile.TemporaryDirectory(prefix='pubyears-day-') as tmp:
            path = Path(tmp) / 'manifest.js'
            rest = 'window.CATLOG_SHARDS = [];\nwindow.CATLOG_MORE = 1;\n'
            path.write_text('window.CATLOG_STATIC_MANIFEST = ' + json.dumps(manifest) + ';\n' + rest)
            m, dated = site_release.dated_publication_years(path, manifest, pub)
            self.assertEqual(dated, {**pub, 'as_of': '2026-10-23'})
            self.assertEqual(pub['as_of'], '2026-10-22')  # the counted object is not changed in place
            self.assertEqual(m['summary'], {'overview': {'records': 9}, 'publication_years': dated, 'other': 1})
            self.assertEqual(list(m['summary']), ['overview', 'publication_years', 'other'])
            self.assertEqual(site_release._manifest(path.read_text()), m)
            self.assertTrue(path.read_text().endswith(';\n' + rest))
            before = path.read_text()
            self.assertEqual(site_release.dated_publication_years(path, m, dated), (m, dated))  # the same day: as it is
            other = {**manifest, 'summary': {'overview': {}}}  # the years did not reach the manifest: left alone
            self.assertEqual(site_release.dated_publication_years(path, other, pub), (other, pub))
            self.assertEqual(site_release.dated_publication_years(path, manifest, None), (manifest, None))
            self.assertEqual(path.read_text(), before)


if __name__ == '__main__':
    unittest.main()
