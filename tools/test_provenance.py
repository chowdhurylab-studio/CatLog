#!/usr/bin/env python3
"""Offline tests of the provenance stamps (catlog.py add, export): python3 tools/test_provenance.py
Each test runs in its own temporary root (catlog's paths are pointed there); the live folder is never written."""
import contextlib, csv, hashlib, io, json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import catlog  # noqa: E402

PATHS = ('ROOT', 'PAPERS', 'CATALOG', 'REJECTED', 'BOUNDS', 'LABEL_DROPS', 'LOG', 'TEXTS', 'WORK')
TEXT = 'Results. Table 1. Kinetic parameters of FooA. FooA wild type | ATP | Km 1.5 mM | kcat 12.3 s-1 at pH 7.5.'
ROW = {'enzyme': 'FooA', 'organism': 'Escherichia coli', 'variant': 'wild type', 'substrate': 'ATP', 'metric': 'Km',
       'raw_value': '1.5', 'raw_unit': 'mM', 'location': 'Table 1', 'pH': 7.5, 'temperature_C': None,
       'quote': 'FooA wild type | ATP | Km 1.5 mM', 'reasoning': 'Table 1 row FooA.'}
ROW2 = {**ROW, 'metric': 'kcat', 'raw_value': '12.3', 'raw_unit': 's-1', 'quote': 'kcat 12.3 s-1'}


def git(root, *a):
    return subprocess.run(['git', '-C', str(root), '-c', 'user.name=t', '-c', 'user.email=t@example.org',
                           '-c', 'commit.gpgsign=false', *a], capture_output=True, text=True, check=True)


class Root(unittest.TestCase):
    """A temporary CatLog root: catlog's module paths point into it for the test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.saved = {k: getattr(catlog, k) for k in PATHS}
        catlog.ROOT = self.root
        for k, name in (('PAPERS', 'papers.tsv'), ('CATALOG', 'catalog.jsonl'), ('REJECTED', 'rejected.jsonl'),
                        ('BOUNDS', 'bounds.jsonl'), ('LABEL_DROPS', 'organism_label_drops.tsv'),
                        ('LOG', 'log.tsv'), ('TEXTS', 'texts'), ('WORK', 'work')):
            setattr(catlog, k, self.root / name)
        for d in ('texts', 'work', 'prompts', 'tools'):
            (self.root / d).mkdir()
        (self.root / 'prompts' / 'read.md').write_text('# Read one paper\n')
        (self.root / 'prompts' / 'verify.md').write_text('# Verify one paper\n')
        (self.root / 'tools' / 'units.py').write_text('# units\n')
        for f, text in zip(catlog.TASK, ('// the batch workflow\n', '# the lean reader agent\n')):
            (self.root / f).parent.mkdir(parents=True, exist_ok=True)
            (self.root / f).write_text(text)
        (self.root / 'catlog.py').write_text('# code\n')

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(catlog, k, v)
        self.tmp.cleanup()

    def paper(self, pmid, read_model=None, verify_model=None):
        """A paper in `reading` with its text, a reader file and a verifier file written in that order."""
        new = not catlog.PAPERS.exists()
        with open(catlog.PAPERS, 'a', newline='') as fh:
            w = csv.DictWriter(fh, catlog.COLS, delimiter='\t')
            if new:
                w.writeheader()
            w.writerow({c: '' for c in catlog.COLS} | {'pmid': pmid, 'status': 'reading', 'doi': '10.1/x', 'title': 'FooA'})
        (catlog.TEXTS / f'{pmid}.txt').write_text(TEXT)
        read = {'pmid': pmid, 'doi': '10.1/x', 'title': 'FooA', 'note': '', 'rows': [ROW, ROW2]}
        ver = {'pmid': pmid, 'verdicts': [{'i': 0, 'metric': 'Km', 'raw_value': '1.5', 'verdict': 'confirm', 'reason': 'ok'},
                                          {'i': 1, 'metric': 'kcat', 'raw_value': '12.3', 'verdict': 'confirm', 'reason': 'ok'}],
               'missed_count': 0, 'reason_if_empty': ''}
        if read_model is not None:
            read['model'] = read_model
        if verify_model is not None:
            ver['model'] = verify_model
        t = time.time()
        for i, (name, d) in enumerate(((f'{pmid}.read.json', read), (f'{pmid}.verify.json', ver))):
            p = catlog.WORK / name
            p.write_text(json.dumps(d))
            os.utime(p, (t + 5 * (i + 1), t + 5 * (i + 1)))  # text, then read, then verdicts (stale() checks the order)

    def rows(self, path):
        with open(path) as fh:
            return [json.loads(l) for l in fh if l.strip()]


class ModelId(unittest.TestCase):
    def test_as_written(self):
        self.assertEqual(catlog.model_id('claude-opus-5-5'), 'claude-opus-5-5')
        self.assertEqual(catlog.model_id('  claude-sonnet-5\n'), 'claude-sonnet-5')
        self.assertEqual(catlog.model_id('x' * 300), 'x' * 100)

    def test_missing_or_not_text(self):
        for x in (None, '', '   ', 5, {'id': 'claude'}, ['claude']):
            self.assertEqual(catlog.model_id(x), '')


def hashes():
    return {'read_prompt': catlog.prompt_hash('read.md'), 'verify_prompt': catlog.prompt_hash('verify.md')}


class Pipeline(Root):
    def test_prompt_hashes(self):
        p = catlog.row_stamp('1', {'model': ''}, {'model': ''})
        self.assertEqual(p['read_prompt'], hashlib.sha256(b'# Read one paper\n').hexdigest()[:12])
        self.assertEqual(p['verify_prompt'], hashlib.sha256(b'# Verify one paper\n').hexdigest()[:12])
        self.assertEqual(p['pipeline_commit'], '')  # not a repository: no commit claimed
        self.assertEqual(p['read_by'], 'reader')
        # the missed values were read by the verifier, under verify.md, and say so
        m = catlog.row_stamp('1', {'model': ''}, {'model': ''}, missed_by={'model': 'claude-opus-5-5'})
        self.assertEqual((m['read_by'], m['read_prompt']), (catlog.MISSED, p['verify_prompt']))
        # the verifier wrote its model in its verify file only: the missed rows still name it
        m = catlog.row_stamp('1', {'rows': []}, {'model': 'claude-haiku-5'}, missed_by={'model': 'claude-opus-5-5'})
        self.assertEqual((m['reader_model'], m['verifier_model'], m['read_prompt']), ('claude-opus-5-5', 'claude-haiku-5', p['verify_prompt']))
        m = catlog.row_stamp('1', {'rows': []}, {'model': ''}, missed_by={'verdicts': []})  # neither file: an older prompt
        self.assertEqual((m['reader_model'], m['read_prompt']), ('', ''))

    def test_prompt_changed_after_the_agent_wrote(self):
        work = self.root / 'work' / '1.read.json'
        work.write_text('{}')
        t = time.time()
        os.utime(self.root / 'prompts' / 'read.md', (t - 100, t - 100))
        os.utime(work, (t - 50, t - 50))
        self.assertEqual(len(catlog.prompt_hash('read.md', work)), 12)  # the prompt the reader followed
        os.utime(self.root / 'prompts' / 'read.md', (t, t))  # a prompt fix landed after the read: not the one it followed
        self.assertEqual(catlog.prompt_hash('read.md', work), '')
        self.assertEqual(len(catlog.prompt_hash('read.md')), 12)  # no work file named: the prompt as it is
        self.assertEqual(len(catlog.prompt_hash('read.md', self.root / 'work' / 'none.json')), 12)

    def test_task_prompt(self):
        h = catlog.task_hash()
        self.assertEqual(h, hashlib.sha256(b'=== .claude/workflows/catlog-batch.js ===\n// the batch workflow\n'
                                           b'=== .claude/agents/catlog-reader.md ===\n# the lean reader agent\n').hexdigest()[:12])
        self.assertEqual(catlog.row_stamp('8', {'model': ''}, {'model': ''})['task_prompt'], '')  # no claim record: unknown
        catlog.claim_prompts('8')
        self.assertEqual(catlog.row_stamp('8', {'model': ''}, {'model': ''})['task_prompt'], h)
        catlog.claim_prompts('8', kept=True)  # unchanged since the kept read's claim: still known
        self.assertEqual(catlog.row_stamp('8', {'model': ''}, {'model': ''})['task_prompt'], h)
        with open(self.root / catlog.TASK[0], 'a') as fh:
            fh.write('// edited while the agents worked\n')
        self.assertEqual(catlog.row_stamp('8', {'model': ''}, {'model': ''})['task_prompt'], '')
        catlog.claim_prompts('8', kept=True)  # the kept read's reader had the old task text, its verifier the new one
        self.assertIsNone(json.loads((self.root / 'work' / '8.prompts.json').read_text())['task'])
        self.assertEqual(catlog.row_stamp('8', {'model': ''}, {'model': ''})['task_prompt'], '')
        for f in catlog.TASK:
            (self.root / f).unlink()
        self.assertEqual(catlog.task_hash(), '')

    def test_missing_prompt(self):
        (self.root / 'prompts' / 'verify.md').unlink()
        self.assertEqual(catlog.row_stamp('1', {'model': ''}, {'model': ''})['verify_prompt'], '')

    def test_no_model_key_means_an_older_prompt(self):
        # the prompts since 2026-10-21 ask for `model` (even ""): a file without the key was written under an older one
        s = catlog.row_stamp('1', {'rows': []}, {'model': 'claude-opus-5-5'})
        self.assertEqual((s['read_prompt'], len(s['verify_prompt'])), ('', 12))
        s = catlog.row_stamp('1', {'model': ''}, {'verdicts': []})
        self.assertEqual((len(s['read_prompt']), s['verify_prompt']), (12, ''))

    def test_claim_record(self):
        catlog.claim_prompts('7')
        rec = json.loads((self.root / 'work' / '7.prompts.json').read_text())
        self.assertEqual({k: rec[k] for k in ('read.md', 'verify.md')},
                         {'read.md': catlog.prompt_hash('read.md'), 'verify.md': catlog.prompt_hash('verify.md')})
        s = catlog.row_stamp('7', {'model': ''}, {'model': ''})
        self.assertEqual((s['read_prompt'], s['verify_prompt']), (rec['read.md'], rec['verify.md']))
        (self.root / 'prompts' / 'read.md').write_text('# Read one paper (fixed while the agents worked)\n')
        s = catlog.row_stamp('7', {'model': ''}, {'model': ''})
        self.assertEqual((s['read_prompt'], s['verify_prompt']), ('', rec['verify.md']))  # not the prompt it loaded
        catlog.claim_prompts('7', kept=True)  # a kept read: its reader's record stays, the verifier's is new
        rec2 = json.loads((self.root / 'work' / '7.prompts.json').read_text())
        self.assertEqual((rec2['read.md'], rec2['verify.md']), (rec['read.md'], rec['verify.md']))
        (self.root / 'work' / '7.prompts.json').unlink()
        catlog.claim_prompts('7', kept=True)  # kept read claimed before records existed: unknown, the other rules decide
        self.assertIsNone(json.loads((self.root / 'work' / '7.prompts.json').read_text())['read.md'])

    def test_git_commit(self):
        (self.root / 'catalog.jsonl').write_text('{}\n')
        git(self.root, 'init', '-q')
        git(self.root, 'add', 'catlog.py', 'prompts', 'tools', 'catalog.jsonl')
        git(self.root, 'commit', '-q', '-m', 'test')
        head = git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        c = catlog.git_commit()
        self.assertTrue(head.startswith(c) and len(c) >= 12, c)
        (self.root / 'catalog.jsonl').write_text('{}\n{}\n')  # data changes are not code changes
        (self.root / 'prompts' / 'draft.md').write_text('untracked')  # nor an untracked file
        self.assertEqual(catlog.git_commit(), c)
        git(self.root, 'add', '.claude')
        git(self.root, 'commit', '-q', '-m', 'task files')
        c = catlog.git_commit()
        for f in ('prompts/read.md', 'catlog.py', 'tools/units.py', *catlog.TASK):
            with open(self.root / f, 'a') as fh:
                fh.write('changed\n')
            self.assertEqual(catlog.git_commit(), c + '+dirty', f)
            git(self.root, 'checkout', '-q', '--', f)
        self.assertEqual(catlog.git_commit(), c)

    def test_folder_inside_another_repository(self):
        git(self.root, 'init', '-q')
        sub = self.root / 'sub'
        sub.mkdir()
        catlog.ROOT = sub  # a root that is not its own repository never takes its parent's commit
        self.assertEqual(catlog.git_commit(), '')


class PromptTexts(Root):
    def show(self, h):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                catlog.cmd_prompt(h)
            except SystemExit as e:
                return None, str(e)
        return out.getvalue(), err.getvalue()

    def test_stamping_saves_each_text(self):
        catlog.claim_prompts('9')
        s = catlog.row_stamp('9', {'model': ''}, {'model': ''})
        for f, data in (('read_prompt', b'# Read one paper\n'), ('verify_prompt', b'# Verify one paper\n'),
                        ('task_prompt', catlog.task_text())):
            saved = self.root / 'work' / 'prompts' / f'{s[f]}.md'
            self.assertEqual(saved.read_bytes(), data, f)  # the text the hash names, exactly
            self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest()[:12], s[f])
            self.assertEqual(self.show(s[f])[0], data.decode())
        self.assertEqual(len(list((self.root / 'work' / 'prompts').iterdir())), 3)
        catlog.row_stamp('9', {'model': ''}, {'model': ''})  # written once
        self.assertEqual(len(list((self.root / 'work' / 'prompts').iterdir())), 3)
        self.assertEqual(catlog.row_stamp('9', {'rows': []}, {'verdicts': []})['read_prompt'], '')  # no hash, nothing new
        self.assertEqual(len(list((self.root / 'work' / 'prompts').iterdir())), 3)

    def test_a_text_edited_this_instant_is_not_saved(self):
        self.assertEqual(catlog.keep_prompt('0' * 12, lambda: b'other text'), '')
        self.assertFalse((self.root / 'work' / 'prompts').exists())

    def test_prompt_from_git_history(self):
        git(self.root, 'init', '-q')
        git(self.root, 'add', '-A'); git(self.root, 'commit', '-q', '-m', 'v1')
        v1 = git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        h1, t1 = catlog.prompt_hash('verify.md'), catlog.task_hash()
        (self.root / 'prompts' / 'verify.md').write_text('# Verify one paper, v2\n')
        with open(self.root / catlog.TASK[1], 'a') as fh:
            fh.write('v2\n')
        git(self.root, 'commit', '-q', '-am', 'v2')
        out, err = self.show(h1)  # never stamped, so never saved: found at the commit that had it
        self.assertEqual(out, '# Verify one paper\n')
        self.assertIn('prompts/verify.md at commit ' + v1[:12], err)
        out, err = self.show(t1)
        self.assertIn('=== .claude/agents/catlog-reader.md ===\n# the lean reader agent\n', out)
        self.assertNotIn('v2', out)
        self.assertIn('task files', err)
        out, err = self.show(catlog.prompt_hash('verify.md'))
        self.assertEqual((out, 'as it is now' in err), ('# Verify one paper, v2\n', True))
        self.assertIsNone(self.show('abcdef012345')[0])
        self.assertIn('usage', self.show('nothex')[1])


class Judge(Root):
    def test_stamps(self):
        pipe = {'read_by': 'reader', 'reader_model': 'claude-opus-5-5', 'verifier_model': 'claude-sonnet-5', 'read_prompt': 'aaa',
                'verify_prompt': 'bbb', 'task_prompt': 'ddd', 'pipeline_commit': 'ccc'}
        read = {'doi': '10.1/x', 'title': 'FooA', 'model': 'claude-opus-5-5',
                'rows': [{**ROW, 'reader_model': 'forged'}, {**ROW2, 'raw_value': '99'}]}
        ver = {'model': 'claude-sonnet-5', 'verdicts': [
            {'i': 0, 'metric': 'Km', 'raw_value': '1.5', 'verdict': 'fix', 'fix': {'verifier_model': 'forged', 'location': 'Table 1.'}},
            {'i': 1, 'metric': 'kcat', 'raw_value': '99', 'verdict': 'confirm'}]}
        kept, rejected = catlog.judge('1', read, ver, catlog.squash(TEXT), pipe)
        self.assertEqual(len(kept), 1); self.assertEqual(len(rejected), 1)  # 99 is not in the quote
        for r in kept + rejected:
            self.assertEqual({f: r[f] for f in catlog.STAMP}, pipe)

    def test_old_work_files_add_unstamped(self):
        kept, rejected = catlog.judge('1', {'doi': '10.1/x', 'title': 'FooA', 'rows': [ROW]},
                                      {'verdicts': [{'i': 0, 'metric': 'Km', 'raw_value': '1.5', 'verdict': 'confirm'}]},
                                      catlog.squash(TEXT))
        self.assertEqual((len(kept), len(rejected)), (1, 0))
        self.assertEqual((kept[0]['reader_model'], kept[0]['verifier_model']), ('', ''))
        self.assertEqual((kept[0]['read_prompt'], kept[0]['verify_prompt']), ('', ''))  # older prompts: not knowable


class Add(Root):
    def test_add_with_and_without_model(self):
        self.paper('90000001', 'claude-opus-5-5', 'claude-opus-5-5')
        self.paper('90000002')  # written before the prompts asked for it: still adds
        for p in ('90000001', '90000002'):
            catlog.cmd_add(p)
        rows = self.rows(catlog.CATALOG)
        self.assertEqual(len(rows), 4)
        by = {}
        for r in rows:
            by.setdefault(r['pmid'], set()).add((r['reader_model'], r['verifier_model'], r['read_prompt'], r['verify_prompt'],
                                                 r['pipeline_commit']))
        h = hashes()
        self.assertEqual(by['90000001'], {('claude-opus-5-5', 'claude-opus-5-5', h['read_prompt'], h['verify_prompt'], '')})
        self.assertEqual(by['90000002'], {('', '', '', '', '')})  # files from before the prompts asked for `model`
        with catlog.Queue(write=False) as q:
            self.assertEqual({q.rows[p]['status'] for p in ('90000001', '90000002')}, {'done'})

    def test_agents_mid_flight_when_the_prompts_change(self):
        # the merge of this change edits both prompts while a batch runs: agents that loaded the old prompts write
        # their files minutes later, after the change, without a `model` key. Their rows add with blank hashes.
        t = time.time()
        for n in ('read.md', 'verify.md'):
            os.utime(self.root / 'prompts' / n, (t, t))
        self.paper('90000004')
        for i, n in enumerate(('90000004.read.json', '90000004.verify.json')):
            os.utime(catlog.WORK / n, (t + 300 + i, t + 300 + i))
        catlog.cmd_add('90000004')
        rows = self.rows(catlog.CATALOG)
        self.assertEqual(len(rows), 2)
        self.assertEqual({tuple(r[f] for f in catlog.STAMP) for r in rows}, {('reader', '', '', '', '', '', '')})

    def test_prompt_edited_after_claim(self):
        catlog.claim_prompts('90000005')
        (self.root / 'prompts' / 'verify.md').write_text('# Verify one paper, edited mid-batch\n')
        self.paper('90000005', 'claude-opus-5-5', 'claude-opus-5-5')  # files written after the edit, with `model`
        catlog.cmd_add('90000005')
        got = {(r['read_prompt'], r['verify_prompt'], r['task_prompt']) for r in self.rows(catlog.CATALOG)}
        self.assertEqual(got, {(catlog.prompt_hash('read.md'), '', catlog.task_hash())})

    def test_reread_keeps_the_claim_record_with_a_kept_read(self):
        self.paper('90000006', 'claude-opus-5-5', 'claude-opus-5-5')
        catlog.claim_prompts('90000006')
        (catlog.WORK / '90000006.verify.json').unlink()  # the verifier died: an unverified read, kept by reread
        catlog.cmd_reread('90000006', 'test', limit=True)
        self.assertTrue((catlog.WORK / '90000006.read.json').exists())
        self.assertTrue((catlog.WORK / '90000006.prompts.json').exists())
        catlog.claim_prompts('90000006')
        (catlog.WORK / '90000006.read.json').unlink()
        catlog.cmd_reread('90000006', 'test', limit=True)  # no kept read: the record goes to work/old with the rest
        self.assertFalse((catlog.WORK / '90000006.prompts.json').exists())

    def test_missed_rows_carry_their_own_reader(self):
        self.paper('90000003', 'claude-opus-5-5', 'claude-sonnet-5')
        t = time.time() + 20
        missed = {'pmid': '90000003', 'model': 'claude-sonnet-5', 'rows': [{**ROW, 'metric': 'kcat', 'raw_value': '12.3',
                                                                             'raw_unit': 's-1', 'quote': 'kcat 12.3 s-1',
                                                                             'substrate': 'ATP (missed)'}]}
        mver = {'pmid': '90000003', 'model': 'claude-haiku-5', 'verdicts': [
            {'i': 0, 'metric': 'kcat', 'raw_value': '12.3', 'verdict': 'confirm'}]}
        for i, (name, d) in enumerate((('90000003.missed.read.json', missed), ('90000003.missed.verify.json', mver))):
            (catlog.WORK / name).write_text(json.dumps(d)); os.utime(catlog.WORK / name, (t + i, t + i))
        catlog.cmd_add('90000003')
        got = {(r['substrate'], r['metric']): (r['read_by'], r['reader_model'], r['verifier_model'], r['read_prompt'],
                                                 r['verify_prompt']) for r in self.rows(catlog.CATALOG)}
        h = hashes()
        self.assertEqual(got[('ATP', 'Km')], ('reader', 'claude-opus-5-5', 'claude-sonnet-5', h['read_prompt'], h['verify_prompt']))
        # the verifier read the missed rows, following verify.md; a second verifier checked them
        self.assertEqual(got[('ATP (missed)', 'kcat')],
                         (catlog.MISSED, 'claude-sonnet-5', 'claude-haiku-5', h['verify_prompt'], h['verify_prompt']))

    def test_missed_file_without_model(self):
        # the verifier wrote `model` in its verify file but not in the missed file: the missed rows still name it
        self.paper('90000007', 'claude-opus-5-5', 'claude-sonnet-5')
        t = time.time() + 20
        missed = {'pmid': '90000007', 'rows': [{**ROW, 'metric': 'kcat', 'raw_value': '12.3', 'raw_unit': 's-1',
                                                 'quote': 'kcat 12.3 s-1', 'substrate': 'ATP (missed)'}]}
        mver = {'pmid': '90000007', 'model': 'claude-haiku-5', 'verdicts': [
            {'i': 0, 'metric': 'kcat', 'raw_value': '12.3', 'verdict': 'confirm'}]}
        for i, (name, d) in enumerate((('90000007.missed.read.json', missed), ('90000007.missed.verify.json', mver))):
            (catlog.WORK / name).write_text(json.dumps(d)); os.utime(catlog.WORK / name, (t + i, t + i))
        catlog.cmd_add('90000007')
        r = next(r for r in self.rows(catlog.CATALOG) if r['substrate'] == 'ATP (missed)')
        self.assertEqual((r['read_by'], r['reader_model'], r['read_prompt']), (catlog.MISSED, 'claude-sonnet-5', hashes()['verify_prompt']))


class Export(unittest.TestCase):
    def test_per_value_and_flat(self):
        st = {'read_by': 'reader', 'reader_model': 'claude-opus-5-5', 'verifier_model': '', 'read_prompt': 'aaa', 'verify_prompt': 'bbb',
              'task_prompt': 'ddd', 'pipeline_commit': 'ccc+dirty'}
        old = {'metric': 'Km', 'value': 1.0}
        m = {'kcat': {'metric': 'kcat', **st}, 'Km': old, 'kcat/Km': {'metric': 'kcat/Km', **st, 'reader_model': 'claude-sonnet-5'}}
        p = catlog.provenance(m)
        self.assertEqual(set(p), {'kcat', 'kcat/Km'})
        self.assertEqual(p['kcat'], st)
        self.assertIsNone(catlog.provenance({'Km': old}))
        flat = catlog.flat_provenance({'provenance': p})
        self.assertEqual(flat['reader_model'], 'claude-opus-5-5; claude-sonnet-5')
        self.assertEqual(flat['verifier_model'], '')
        self.assertEqual(flat['pipeline_commit'], 'ccc+dirty')
        self.assertEqual(flat['provenance_how'], 'stamped')
        self.assertEqual(catlog.flat_provenance({'provenance': None}), {**{f: '' for f in catlog.STAMP}, 'provenance_how': ''})
        self.assertTrue(set(catlog.STAMP) <= set(catlog.FLAT))


class AgentModel(Root):
    """add takes reader_model / verifier_model from the transcript of the agent that wrote each work file
    (catlog.agent_model): a switch mid-run shows as 'A>B'; without a transcript the agent's own `model` stands."""

    def setUp(self):
        super().setUp()
        import provenance_backfill as pb  # tools/ is on catlog's path
        self.pb, self.saved_projects = pb, pb.PROJECTS
        pb.PROJECTS = self.root / '_projects'
        catlog._agent_log_files.clear(); catlog._agent_logs.clear()
        self.folder = pb.PROJECTS / ''.join(c if c.isalnum() else '-' for c in str(self.root))

    def tearDown(self):
        self.pb.PROJECTS = self.saved_projects
        catlog._agent_log_files.clear(); catlog._agent_logs.clear()
        super().tearDown()

    def transcript(self, aid, fname, models, t, end=None, names=()):
        """An agent told to write work/<fname> (and naming the work files in `names`): one call per model of `models`,
        the last a Write of the file running at t; the transcript ends at `end` (t + 5)."""
        d = self.folder / 'chat' / 'subagents'
        d.mkdir(parents=True, exist_ok=True)
        iso = lambda x: time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(x)) + '.000Z'
        path = str(catlog.WORK / fname)
        task = ' '.join(f'Rows to check: {catlog.WORK / n}.' for n in names) + f' Write {path}'
        lines = [{'type': 'user', 'timestamp': iso(t - 60), 'agentId': aid, 'message': {'role': 'user', 'content': task}}]
        for k, m in enumerate(models):
            last = k == len(models) - 1
            at = t - 1 if last else t - 50 + k
            call = {'type': 'tool_use', 'id': f'toolu_{aid}{k}', 'name': 'Write' if last else 'Read',
                    'input': {'file_path': path, 'content': '{}'} if last else {'file_path': str(catlog.TEXTS / 'x.txt')}}
            lines += [{'type': 'assistant', 'timestamp': iso(at), 'message': {'model': m, 'content': [call]}},
                      {'type': 'user', 'timestamp': iso(at + 2), 'message': {'content': [
                          {'type': 'tool_result', 'tool_use_id': call['id'], 'content': 'ok'}]}}]
        p = d / f'agent-{aid}.jsonl'
        p.write_text('\n'.join(json.dumps(x) for x in lines) + '\n')
        e = t + 5 if end is None else end
        os.utime(p, (e, e))

    def mtime(self, name):
        return (catlog.WORK / name).stat().st_mtime

    def test_switch_shows_and_the_writer_is_picked(self):
        self.paper('90000011', 'claude-opus-5-5', 'claude-opus-5-5')
        self.transcript('r1', '90000011.read.json', ['claude-opus-5-5', 'claude-opus-5'], self.mtime('90000011.read.json'))
        # the verifier names the read file too, but its call was not running when that file was written
        self.transcript('v1', '90000011.verify.json', ['claude-opus-5-5'], self.mtime('90000011.verify.json'),
                        names=['90000011.read.json'])
        self.assertEqual(catlog.agent_model(catlog.WORK / '90000011.read.json'), ('claude-opus-5-5>claude-opus-5', 'agent-r1'))
        self.assertEqual(catlog.agent_model(catlog.WORK / '90000011.verify.json'), ('claude-opus-5-5', 'agent-v1'))

    def test_add_stamps_the_transcript_and_logs_it(self):
        self.paper('90000012', 'claude-opus-5-5', 'claude-opus-5-5')
        self.transcript('r2', '90000012.read.json', ['claude-opus-5-5', 'claude-opus-5'], self.mtime('90000012.read.json'))
        self.transcript('v2', '90000012.verify.json', ['claude-sonnet-5-5'], self.mtime('90000012.verify.json'))
        catlog.cmd_add('90000012')
        got = {(r['reader_model'], r['verifier_model']) for r in self.rows(catlog.CATALOG)}
        self.assertEqual(got, {('claude-opus-5-5>claude-opus-5', 'claude-sonnet-5-5')})
        line = next(l for l in open(catlog.LOG) if '\tagent_models\t' in l)
        self.assertIn('90000012.read.json=claude-opus-5-5>claude-opus-5@agent-r2', line)
        self.assertIn('90000012.verify.json=claude-sonnet-5-5@agent-v2', line)

    def test_no_transcript_keeps_the_agents_own_model(self):
        self.paper('90000013', 'claude-opus-5-5', 'claude-sonnet-5-5')
        catlog.cmd_add('90000013')
        got = {(r['reader_model'], r['verifier_model']) for r in self.rows(catlog.CATALOG)}
        self.assertEqual(got, {('claude-opus-5-5', 'claude-sonnet-5-5')})
        line = next(l for l in open(catlog.LOG) if '\tagent_models\t' in l)
        self.assertIn('90000013.read.json=own:claude-opus-5-5', line)

    def test_transcripts_outside_the_window_are_not_read(self):
        self.paper('90000014', 'claude-opus-5-5', 'claude-opus-5-5')
        t = self.mtime('90000014.read.json')
        self.transcript('old', '90000014.read.json', ['claude-opus-5'], t, end=t - 600)  # ended before the write
        self.transcript('late', '90000014.read.json', ['claude-opus-5'], t, end=t + (catlog.MODEL_HOURS + 1) * 3600)
        self.assertEqual(catlog.agent_model(catlog.WORK / '90000014.read.json'), ('', ''))


if __name__ == '__main__':
    unittest.main(verbosity=2)
