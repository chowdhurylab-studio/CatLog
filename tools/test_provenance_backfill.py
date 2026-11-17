#!/usr/bin/env python3
"""Offline tests of tools/provenance_backfill.py and of the export merging its lines: python3 tools/test_provenance_backfill.py
Each test builds a small data folder (git history, log.tsv, catalog, work files with their mtimes) and fake agent
transcripts in a temporary directory; the live folder and ~/.claude are never read or written."""
import contextlib, csv, datetime, hashlib, io, json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import catlog  # noqa: E402
import provenance_backfill as pb  # noqa: E402

READ_MD = '# Read one paper\n\nRead it.\nWrite the rows.\n'
VERIFY_MD = '# Verify one paper\'s rows\n\nCheck each row.\nKeep reasons to one line.\n'
T0 = 1790000000 // 60 * 60  # agents start here (local minutes are whole minutes)
OPUS, SONNET, FALLBACK = 'claude-opus-5-5', 'claude-sonnet-5-5', 'claude-opus-5'


def h12(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def local(t):
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(t))


def row(pmid, metric, value, quote, **kw):
    return {'pmid': pmid, 'enzyme': 'FooA', 'organism': 'E. coli', 'variant': 'wild type', 'substrate': 'ATP',
            'metric': metric, 'raw_value': value, 'raw_unit': 'mM' if metric == 'Km' else 's-1', 'quote': quote,
            'location': 'Table 1', **kw}


class Folder(unittest.TestCase):
    """A data folder with a git history and a projects folder of transcripts."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.root, self.projects = base / 'catlog', base / 'projects'
        self.out = base / 'out' / 'provenance_backfill.tsv'
        for d in ('work/old', 'prompts', 'sources'):
            (self.root / d).mkdir(parents=True)
        self.git('init', '-q', '-b', 'main')
        self.commit(T0 - 3600, {'prompts/read.md': READ_MD, 'prompts/verify.md': VERIFY_MD, 'catlog.py': '# code\n'})
        self.lines, self.catalog, self.rejected = [], [], []
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a, when=None):
        env = {**{k: v for k, v in os.environ.items() if not k.startswith('GIT_')},
               'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.org', 'GIT_COMMITTER_NAME': 't',
               'GIT_COMMITTER_EMAIL': 't@example.org'}
        if when is not None:
            env['GIT_COMMITTER_DATE'] = env['GIT_AUTHOR_DATE'] = f'@{int(when)} +0000'
        return subprocess.run(['git', '-C', str(self.root), '-c', 'commit.gpgsign=false', *a], capture_output=True,
                              text=True, check=True, env=env)

    def commit(self, when, files):
        for f, text in files.items():
            (self.root / f).parent.mkdir(parents=True, exist_ok=True)
            (self.root / f).write_text(text)
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'c', when=when)
        return self.git('rev-parse', 'HEAD').stdout.strip()

    def head(self):
        return self.git('rev-parse', 'HEAD').stdout.strip()

    # --- transcripts ---
    def agent(self, desc, task, calls, model=OPUS, project=None, cwd=None, session='s1'):
        """A subagent transcript: task text, then each call (t0, t1, tool name, input, result), all by `model` (or by
        model[i] for call i: a list)."""
        self.n += 1
        aid = f'a{self.n:016x}'
        d = self.projects / (project or '-catlog') / session / 'subagents' / 'workflows' / 'wf_1'
        d.mkdir(parents=True, exist_ok=True)
        lines = [{'type': 'user', 'agentId': aid, 'cwd': cwd or str(self.root), 'timestamp': iso(calls[0][0] - 1),
                  'message': {'role': 'user', 'content': task}}]
        for i, (t0, t1, name, inp, result) in enumerate(calls):
            tid = f'toolu_{self.n}_{i}'
            lines.append({'type': 'assistant', 'agentId': aid, 'timestamp': iso(t0), 'message': {
                'model': model[i] if isinstance(model, list) else model, 'role': 'assistant',
                'content': [{'type': 'tool_use', 'id': tid, 'name': name, 'input': inp}]}})
            if t1 is not None:
                lines.append({'type': 'user', 'agentId': aid, 'timestamp': iso(t1), 'message': {
                    'role': 'user', 'content': [{'tool_use_id': tid, 'type': 'tool_result', 'content': result}]}})
        (d / f'agent-{aid}.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in lines))
        (d / f'agent-{aid}.meta.json').write_text(json.dumps({'description': desc}))
        return f'agent-{aid}.jsonl'

    def chat(self, calls, session='chat1'):
        """A chat's own transcript (only its `catlog.py add` calls count)."""
        d = self.projects / '-catlog'
        d.mkdir(parents=True, exist_ok=True)
        lines = []
        for i, (t0, t1, cmd) in enumerate(calls):
            tid = f'toolu_chat_{i}'
            lines.append({'type': 'assistant', 'cwd': str(self.root), 'timestamp': iso(t0), 'message': {
                'model': OPUS, 'role': 'assistant', 'content': [{'type': 'tool_use', 'id': tid, 'name': 'Bash',
                                                                 'input': {'command': cmd}}]}})
            lines.append({'type': 'user', 'timestamp': iso(t1), 'message': {
                'role': 'user', 'content': [{'tool_use_id': tid, 'type': 'tool_result', 'content': 'ok'}]}})
        (d / f'{session}.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in lines))

    def read_prompt_call(self, t, text=READ_MD):
        numbered = '\n'.join(f'{i}\t{line}' for i, line in enumerate(text.split('\n'), 1))
        return (t, t + 0.1, 'Read', {'file_path': f'{self.root}/prompts/read.md'}, numbered)

    def cat_prompt_call(self, t, name='verify.md', text=VERIFY_MD, after='-rw-r--r-- 1 x staff 10 texts/1.txt'):
        return (t, t + 0.2, 'Bash', {'command': f'cat {self.root}/prompts/{name}; ls -la texts/1*'}, text + after)

    def write_call(self, t, name, path=None):
        return (t, t + 2, 'Bash', {'command': f"python3 - <<'EOF'\nimport json\njson.dump(d, open('{path or self.root / 'work' / name}', 'w'))\nEOF"}, '')

    def reader(self, pmid, t, model=OPUS, prompt=True, desc=None, text=READ_MD, session='s1'):
        name = f'{pmid}.read.json'
        calls = ([self.read_prompt_call(t, text)] if prompt else []) + [self.write_call(t + 30, name)]
        return self.agent(desc or f'read:{pmid}', f'Follow prompts/read.md for PMID {pmid}. Write {self.root}/work/{name}. '
                          'Do not edit any other file.', calls, model, session=session)

    def verifier(self, pmid, t, model=OPUS, missed=False, prompt=True, session='s1'):
        which = '.missed' if missed else ''
        name = f'{pmid}{which}.verify.json'
        calls = ([self.cat_prompt_call(t)] if prompt else []) + [self.write_call(t + 30, name)]
        return self.agent(f'verify{which}:{pmid}', f'Follow prompts/verify.md for PMID {pmid}. Rows to check: '
                          f'{self.root}/work/{pmid}{which}.read.json. Write your verdicts to {self.root}/work/{name}.',
                          calls, model, session=session)

    def workfile(self, name, rows=None, mtime=None, old_at=None):
        """A work file with these rows and mtime; old_at: moved to work/old/ at that unix time (by next or reread)."""
        p = self.root / 'work' / name if old_at is None else \
            self.root / 'work' / 'old' / f'{name[:-len(".json")]}.{int(old_at)}.json'
        p.write_text(json.dumps({'rows': rows or []}))
        os.utime(p, (mtime, mtime))

    def add(self, pmid, when, rows, kept=None, event='add', **extra):
        """An add (or recover) in log.tsv and its rows in catalog.jsonl, `added` in that minute."""
        self.lines.append(f'{local(when)}\t{pmid}\t{event}\tkept={len(rows) if kept is None else kept}\tdup=0\trejected=0\n')
        for i, r in enumerate(rows):
            self.catalog.append({**r, 'row_id': r.get('row_id') or f'{pmid}{event}{when}{i}', 'added': local(when),
                                 'checked': local(when), **extra})

    def backfill(self):
        (self.root / 'log.tsv').write_text(''.join(self.lines))
        (self.root / 'catalog.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in self.catalog))
        (self.root / 'rejected.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in self.rejected))
        with contextlib.redirect_stdout(io.StringIO()) as so, contextlib.redirect_stderr(io.StringIO()):
            pb.main(['--root', str(self.root), '--out', str(self.out), '--cache', str(self.out.parent / 'cache.json.gz'),
                     '--transcripts', str(self.projects), '--jobs', '1'])
        self.report = so.getvalue()
        with open(self.out) as f:
            return {r['row_id']: r for r in csv.DictReader(f, delimiter='\t')}

    def one_paper(self, pmid='111', reader_model=OPUS, verifier_model=OPUS):
        """The common case: a reader and a verifier wrote their files, then add took the paper's two rows."""
        rows = [row(pmid, 'Km', '1.5', 'FooA | ATP | 1.5'), row(pmid, 'kcat', '12', 'FooA | ATP | 12')]
        ra = self.reader(pmid, T0, reader_model)
        va = self.verifier(pmid, T0 + 120, verifier_model)
        self.workfile(f'{pmid}.read.json', rows, T0 + 31)
        self.workfile(f'{pmid}.verify.json', [], T0 + 151)
        self.add(pmid, T0 + 600, rows)
        return ra, va


class Backfill(Folder):
    def test_reader_and_verifier(self):
        ra, va = self.one_paper(verifier_model=SONNET)
        out = self.backfill()
        self.assertEqual(len(out), 2)
        line = out[self.catalog[0]['row_id']]
        self.assertEqual((line['read_by'], line['reader_model'], line['verifier_model']), ('reader', OPUS, SONNET))
        self.assertEqual(line['read_prompt'], h12(READ_MD))  # from the reader's Read of the prompt
        self.assertEqual(line['verify_prompt'], h12(VERIFY_MD))  # from the verifier's cat
        self.assertEqual(line['pipeline_commit'], self.head()[:12])
        self.assertEqual(line['how'], 'reconstructed')
        self.assertIn(ra, line['evidence']); self.assertIn(va, line['evidence'])
        self.assertIn(f'add {local(T0 + 600)}', line['evidence'])
        for h, text in ((h12(READ_MD), READ_MD), (h12(VERIFY_MD), VERIFY_MD)):  # each hash resolves to its exact text
            self.assertEqual((self.out.parent / 'prompt_versions' / f'{h}.md').read_text(), text)

    def two_papers(self):
        """Paper 111's reader and verifier in session s1; paper 222's reader in s1 and its verifier in s2 (an
        interrupted batch whose read the next batch verified)."""
        self.one_paper()
        rows = [row('222', 'Km', '3', 'BarB | ATP | 3')]
        self.reader('222', T0 + 1000)
        self.verifier('222', T0 + 1120, session='s2')
        self.workfile('222.read.json', rows, T0 + 1031)
        self.workfile('222.verify.json', [], T0 + 1151)
        self.add('222', T0 + 1600, rows)
        return self.backfill()

    def edit_tsv(self, change):
        with open(self.out) as f:
            lines = list(csv.DictReader(f, delimiter='\t'))
        lines = change(lines)
        with open(self.out, 'w', newline='') as f:
            w = csv.DictWriter(f, pb.FIELDS, delimiter='\t', lineterminator='\n')
            w.writeheader(); w.writerows(lines)

    def test_lines_stay_when_their_transcripts_are_gone(self):
        first = self.two_papers()
        self.assertEqual(len(first), 3)
        import shutil
        shutil.rmtree(self.projects / '-catlog' / 's1')  # archived and removed; 222's verifier (s2) is still here
        self.catalog[1].update({f: '' for f in pb.STAMP})  # got a stamp of its own meanwhile: harmless, kept
        dropped = self.catalog.pop(0)['row_id']  # dropped from the catalog: kept, in case the value comes back
        again = self.backfill()
        self.assertEqual(again, first)  # every earlier line exactly; 222's not rebuilt without its reader
        self.assertIn(dropped, again)
        self.assertIn('earlier line kept, a transcript it names is gone: this run built another: 1', self.report)
        self.assertIn('earlier line kept, a transcript it names is gone: this run built none: 2', self.report)

    def test_earlier_blanks_stay_once_transcripts_are_gone(self):
        self.two_papers()
        self.verifier('333', T0 + 2120, session='s3')
        self.reader('333', T0 + 2000, session='s3')
        rows = [row('333', 'Km', '4', 'BazC | ATP | 4')]
        self.workfile('333.read.json', rows, T0 + 2031)
        self.workfile('333.verify.json', [], T0 + 2151)
        self.add('333', T0 + 2600, rows)
        first = self.backfill()
        rid = self.catalog[-1]['row_id']
        self.assertTrue(first[rid]['read_prompt'])
        self.edit_tsv(lambda ls: [{**l, 'read_prompt': ''} if l['row_id'] == rid else l for l in ls])
        import shutil
        shutil.rmtree(self.projects / '-catlog' / 's1')
        again = self.backfill()
        self.assertEqual(again[rid]['read_prompt'], '')  # 333's transcripts are here, but some others are gone
        self.assertEqual(again[rid]['verify_prompt'], first[rid]['verify_prompt'])
        self.assertIn('earlier blanks kept (some transcripts are gone): 1', self.report)

    def test_a_row_id_twice_in_the_earlier_tsv_is_left_out(self):
        self.two_papers()
        dup = self.catalog[0]['row_id']
        self.edit_tsv(lambda ls: ls + [l for l in ls if l['row_id'] == dup])
        import shutil
        shutil.rmtree(self.projects / '-catlog' / 's1')
        again = self.backfill()
        self.assertNotIn(dup, again)
        self.assertIn('earlier lines left out: their row_id is in the earlier TSV twice: 2', self.report)

    def test_stamped_rows_and_rows_without_transcripts_get_no_line(self):
        self.one_paper()
        self.catalog[0].update({f: '' for f in pb.STAMP})  # stamped by add: never backfilled
        rows = [row('222', 'Km', '3', 'q 3')]
        self.workfile('222.read.json', rows, T0 + 31)  # nobody's transcript wrote it (a chat by hand, or no transcript)
        self.workfile('222.verify.json', [], T0 + 40)
        self.add('222', T0 + 600, rows)
        out = self.backfill()
        self.assertEqual(sorted(out), [self.catalog[1]['row_id']])
        self.assertIn('no transcript names it', self.report)

    def test_sonnet_retry_is_its_own_agent(self):
        rows = [row('111', 'Km', '1.5', 'FooA | ATP | 1.5')]
        self.reader('111', T0, OPUS)  # died before writing: its calls end before the file's mtime
        retry = self.reader('111', T0 + 60, SONNET, desc='read-sonnet:111')
        self.verifier('111', T0 + 200)
        self.workfile('111.read.json', rows, T0 + 91)
        self.workfile('111.verify.json', [], T0 + 231)
        self.add('111', T0 + 600, rows)
        line = next(iter(self.backfill().values()))
        self.assertEqual(line['reader_model'], SONNET)
        self.assertIn(retry, line['evidence'])

    def test_agent_that_switched_model_names_every_model_in_order(self):
        rows = [row('111', 'Km', '1.5', 'FooA | ATP | 1.5')]
        name = '111.read.json'
        ra = self.agent('read:111', f'Follow prompts/read.md for PMID 111. Write {self.root}/work/{name}.',
                        [self.read_prompt_call(T0), (T0 + 5, T0 + 6, 'Bash', {'command': 'ls texts'}, ''),
                         self.write_call(T0 + 30, name), (T0 + 40, T0 + 41, 'Bash', {'command': 'echo done'}, '')],
                        [OPUS, OPUS, FALLBACK, OPUS])  # a fallback mid-run; its last call (after the write) does not count
        self.verifier('111', T0 + 120)
        self.workfile(name, rows, T0 + 31)
        self.workfile('111.verify.json', [], T0 + 151)
        self.add('111', T0 + 600, rows)
        line = next(iter(self.backfill().values()))
        self.assertEqual((line['reader_model'], line['verifier_model']), (f'{OPUS}>{FALLBACK}', OPUS))
        self.assertIn(f'{ra} (tool calls: {OPUS} 2 > {FALLBACK} 1)', line['evidence'])
        self.assertNotIn('verifier agent-a0000000000000002.jsonl (tool calls', line['evidence'])
        self.assertIn('reader_model names several models: the agent switched model before it wrote the file: 1', self.report)

    def test_missed_values_are_read_by_the_verifier(self):
        main = [row('111', 'Km', '1.5', 'FooA | ATP | 1.5')]
        missed = [row('111', 'kcat', '7', 'FooA | GTP | 7', substrate='GTP')]
        self.reader('111', T0)
        # the verifier writes its verdicts and the missed file; a second verifier checks the missed rows
        v = self.agent('verify:111', f'Follow prompts/verify.md for PMID 111. Rows to check: {self.root}/work/111.read.json. '
                       f'Write your verdicts to {self.root}/work/111.verify.json.',
                       [self.cat_prompt_call(T0 + 100), self.write_call(T0 + 130, '111.verify.json'),
                        self.write_call(T0 + 140, '111.missed.read.json')], SONNET)
        mv = self.verifier('111', T0 + 200, OPUS, missed=True)
        self.workfile('111.read.json', main, T0 + 31)
        self.workfile('111.verify.json', [], T0 + 131)
        self.workfile('111.missed.read.json', missed, T0 + 141)
        self.workfile('111.missed.verify.json', [], T0 + 231)
        self.add('111', T0 + 600, main + missed)
        out = {r['row_id']: r for r in self.backfill().values()}
        m = out[self.catalog[1]['row_id']]
        self.assertEqual((m['read_by'], m['reader_model'], m['verifier_model']), (pb.MISSED, SONNET, OPUS))
        self.assertEqual(m['read_prompt'], h12(VERIFY_MD))  # the missed values' reader followed verify.md
        self.assertIn(v, m['evidence']); self.assertIn(mv, m['evidence'])
        self.assertEqual(out[self.catalog[0]['row_id']]['read_by'], 'reader')

    def test_same_number_and_block_quote_in_both_files_goes_by_identity(self):
        """An OCR table quoted as one block: a reader row and a missed value share metric, number and quote (624727's
        Km 29 for two substrates; 7905479's reader 0.06 the verifier fixed to 0.12, its missed value 0.06)."""
        block = 'Acetate Propionate Butyrate 29 29 0.06'
        main = [row('111', 'Km', '29', block, substrate='propionate'),
                row('111', 'kcat', '0.06', block, substrate='dGlc1P', variant='E637D')]
        missed = [row('111', 'Km', '29', block, substrate='butyrate'),
                  row('111', 'kcat', '0.06', block, substrate='Glc1P', variant='E637D')]
        ra = self.reader('111', T0)
        v = self.agent('verify:111', f'Follow prompts/verify.md for PMID 111. Rows to check: {self.root}/work/111.read.json. '
                       f'Write your verdicts to {self.root}/work/111.verify.json.',
                       [self.cat_prompt_call(T0 + 100), self.write_call(T0 + 130, '111.verify.json'),
                        self.write_call(T0 + 140, '111.missed.read.json')], SONNET)
        mv = self.verifier('111', T0 + 200, OPUS, missed=True)
        self.workfile('111.read.json', main, T0 + 31)
        self.workfile('111.verify.json', [], T0 + 131)
        self.workfile('111.missed.read.json', missed, T0 + 141)
        self.workfile('111.missed.verify.json', [], T0 + 231)
        fixed = {**main[1], 'raw_value': '0.12', 'corrected': {'raw_value': {'reader': '0.06', 'verifier': '0.12'}}}
        self.add('111', T0 + 600, [main[0], fixed] + missed)
        out = self.backfill()
        got = {r['substrate']: out[r['row_id']] for r in self.catalog}
        for s in ('propionate', 'dGlc1P'):
            self.assertEqual(got[s]['read_by'], 'reader')
            self.assertIn(ra, got[s]['evidence'])
        for s in ('butyrate', 'Glc1P'):
            self.assertEqual((got[s]['read_by'], got[s]['reader_model'], got[s]['read_prompt']), (pb.MISSED, SONNET, h12(VERIFY_MD)))
            self.assertIn(v, got[s]['evidence']); self.assertIn(mv, got[s]['evidence'])
        # both files hold a copy that fits the row: which agent read it is not knowable
        self.catalog.clear(); self.lines.clear()
        self.workfile('111.missed.read.json', missed + [main[0]], T0 + 141)
        self.add('111', T0 + 600, [main[0]])
        self.assertEqual(self.backfill(), {})
        self.assertIn('no line: a reader row and a missed value fit it alike: 1', self.report)

    def test_row_whose_quote_the_verifier_replaced_is_found_by_its_cell(self):
        """1612186: the verifier replaced garbled OCR quotes ('t_-Phenylalanine ... IO.75') by the printed line, and the
        rows (added before `corrected` was kept) do not say what the reader wrote."""
        rows = [row('111', 'kcat', '10.75', 't_-Phenylalanine 0.06 IO.75 179.166.7', substrate='L-Phenylalanine'),
                row('111', 'Km', '0.06', 'L-Tyrosine 0.06', substrate='L-Tyrosine')]
        ra, va = self.reader('111', T0), self.verifier('111', T0 + 120)
        self.workfile('111.read.json', rows, T0 + 31)
        self.workfile('111.verify.json', [], T0 + 151)
        fixed = {**rows[0], 'quote': 'L-Phenylalanine 0.06 10.75 179,166.7'}
        other = {**rows[1], 'quote': 'L-Tyrosine 0.023', 'raw_value': '0.023'}  # another cell: no evidence, no line
        self.add('111', T0 + 600, [fixed, other])
        out = self.backfill()
        self.assertEqual(list(out), [self.catalog[0]['row_id']])
        line = out[self.catalog[0]['row_id']]
        self.assertEqual(line['read_by'], 'reader')
        self.assertIn(ra, line['evidence']); self.assertIn(va, line['evidence'])
        self.assertIn('row found in its read file by its cell, not its quote (the verifier replaced the quote): 1', self.report)
        self.assertIn('no line: the row is not in the read file of its add: 1', self.report)

    def test_reread_rows_go_to_the_add_that_took_them(self):
        first = [row('111', 'Km', '1.5', 'FooA | ATP | 1.5')]
        second = [row('111', 'kcat', '12', 'FooA | ATP | 12')]
        r1, r2 = self.reader('111', T0, OPUS), self.reader('111', T0 + 3000, SONNET)
        v1, v2 = self.verifier('111', T0 + 100), self.verifier('111', T0 + 3100)
        moved = T0 + 2000  # `reread` set the first round's files aside
        self.workfile('111.read.json', first, T0 + 31, old_at=moved)
        self.workfile('111.verify.json', [], T0 + 131, old_at=moved)
        self.workfile('111.read.json', first + second, T0 + 3031)
        self.workfile('111.verify.json', [], T0 + 3131)
        self.add('111', T0 + 600, first)
        self.add('111', T0 + 3600, second)
        out = self.backfill()
        a, b = out[self.catalog[0]['row_id']], out[self.catalog[1]['row_id']]
        self.assertIn(r1, a['evidence']); self.assertIn(v1, a['evidence']); self.assertEqual(a['reader_model'], OPUS)
        self.assertIn(r2, b['evidence']); self.assertIn(v2, b['evidence']); self.assertEqual(b['reader_model'], SONNET)

    def test_file_overwritten_in_place_is_matched_by_time(self):
        rows = [row('111', 'Km', '1.5', 'FooA | ATP | 1.5')]
        r1 = self.reader('111', T0)
        self.verifier('111', T0 + 100)
        self.reader('111', T0 + 3000)  # a later read overwrote both files in place (before `next` moved old files)
        self.verifier('111', T0 + 3100)
        self.workfile('111.read.json', rows, T0 + 3031)
        self.workfile('111.verify.json', [], T0 + 3131)
        self.add('111', T0 + 600, rows)
        line = next(iter(self.backfill().values()))
        self.assertIn(f'{r1} (by time: file overwritten later)', line['evidence'])

    def test_recovered_row_goes_to_the_add_that_first_judged_it(self):
        rows = [row('111', 'Km', '1.5', 'FooA | ATP | 1.5', row_id='r1')]
        ra, va = self.reader('111', T0), self.verifier('111', T0 + 100)
        self.workfile('111.read.json', rows, T0 + 31)
        self.workfile('111.verify.json', [], T0 + 131)
        self.lines.append(f'{local(T0 + 600)}\t111\tadd\tkept=0\tdup=0\trejected=1\n')
        self.rejected.append({**rows[0], 'checked': local(T0 + 600), 'why': ['ratio_non_closure']})
        self.add('111', T0 + 5000, rows, event='recover')
        line = self.backfill()['r1']
        self.assertIn(ra, line['evidence']); self.assertIn(f'add {local(T0 + 600)}', line['evidence'])

    def test_prompt_from_git_unless_an_uncommitted_edit_was_in_use(self):
        rows = [row('111', 'Km', '1.5', 'q 1.5')]
        self.agent('read:111', f'Follow prompts/read.md for PMID 111. Write {self.root}/work/111.read.json.',
                   [self.write_call(T0 + 30, '111.read.json')])  # never shows the prompt it loaded
        self.verifier('111', T0 + 100)
        self.workfile('111.read.json', rows, T0 + 31)
        self.workfile('111.verify.json', [], T0 + 131)
        self.add('111', T0 + 600, rows)
        line = next(iter(self.backfill().values()))
        self.assertEqual(line['read_prompt'], h12(READ_MD))
        self.assertIn('(prompt: git)', line['evidence'])
        # another agent under the same commit loaded an edited read.md: the commit no longer says which text applied
        edited = READ_MD + 'A new rule.\n'
        self.reader('999', T0 + 50, text=edited)
        out = self.backfill()
        self.assertEqual(out[self.catalog[0]['row_id']]['read_prompt'], '')
        self.assertTrue((self.out.parent / 'prompt_versions').exists())

    def test_uncommitted_prompt_text_is_hashed_and_saved(self):
        edited = READ_MD.replace('Read it.', 'Read it all.')
        rows = [row('111', 'Km', '1.5', 'q 1.5')]
        self.reader('111', T0, text=edited)
        self.verifier('111', T0 + 100)
        self.workfile('111.read.json', rows, T0 + 31)
        self.workfile('111.verify.json', [], T0 + 131)
        self.add('111', T0 + 600, rows)
        line = next(iter(self.backfill().values()))
        self.assertEqual(line['read_prompt'], h12(edited))
        self.assertEqual((self.out.parent / 'prompt_versions' / f'{h12(edited)}.md').read_text(), edited)

    def test_commit_within_the_add_minute(self):
        self.one_paper()
        before = self.head()
        minute = T0 + 600
        self.commit(minute + 30, {'catlog.py': '# code v2\n'})  # pipeline code changed within the add's minute
        line = next(iter(self.backfill().values()))
        self.assertEqual(line['pipeline_commit'], '')
        # the chat that ran `catlog.py add 111` finished before that commit: the add ran under the earlier one
        self.chat([(minute + 2, minute + 10, 'python3 catlog.py add 111 222')])
        line = next(iter(self.backfill().values()))
        self.assertEqual(line['pipeline_commit'], before[:12])

    def test_add_before_the_first_commit_says_so(self):
        self.one_paper()
        self.git('update-ref', '-d', 'refs/heads/main')  # main's reflog starts after the add
        self.git('reflog', 'expire', '--expire=all', '--all')
        self.commit(T0 + 3600, {'catlog.py': '# code v2\n'})
        line = next(iter(self.backfill().values()))
        self.assertEqual(line['pipeline_commit'], '')
        self.assertIn("pipeline_commit blank: the add ran before main's first commit: 2", self.report)
        self.assertNotIn('main moved', self.report)

    def test_data_commit_within_the_add_minute_keeps_the_earlier_commit(self):
        self.one_paper()
        before = self.head()
        self.commit(T0 + 630, {'catalog.jsonl': '{}\n'})  # a data checkpoint: no pipeline code changed
        self.assertEqual(next(iter(self.backfill().values()))['pipeline_commit'], before[:12])

    def test_transcripts_of_other_folders_count_only_when_they_name_this_one(self):
        rows = [row('111', 'Km', '1.5', 'q 1.5')]
        ra = self.agent('read:111', f'Follow {self.root}/prompts/read.md for PMID 111. Write {self.root}/work/111.read.json.',
                        [self.write_call(T0 + 30, '111.read.json')], project='-elsewhere', cwd='/elsewhere')
        self.agent('read:111', 'Write /elsewhere/work/111.read.json.', [self.write_call(T0 + 30, '111.read.json', '/x')],
                   project='-other', cwd='/other')  # never names this folder: not even parsed
        self.verifier('111', T0 + 100)
        self.workfile('111.read.json', rows, T0 + 31)
        self.workfile('111.verify.json', [], T0 + 131)
        self.add('111', T0 + 600, rows)
        line = next(iter(self.backfill().values()))
        self.assertIn(ra, line['evidence'])

    def test_rerun_uses_the_cache(self):
        self.one_paper()
        first = self.backfill()
        real = pb.scan
        pb.scan = lambda *a, **k: (_ for _ in ()).throw(AssertionError('rescanned an unchanged transcript'))
        try:
            self.assertEqual(self.backfill(), first)
        finally:
            pb.scan = real
        self.reader('333', T0)  # a new transcript is parsed, the rest still come from the cache
        calls = []
        pb.scan = lambda *a, **k: calls.append(a) or real(*a, **k)
        try:
            self.backfill()
        finally:
            pb.scan = real
        self.assertEqual(len(calls), 1)


    def test_cache_keeps_the_versions_it_matched(self):
        edited = VERIFY_MD + 'A rule saved only in prompt_versions/.\n'
        self.agent('verify:111', 'Write x', [self.cat_prompt_call(T0, text=edited)])
        cache = self.out.parent / 'cache.json.gz'
        g = pb.Git(self.root)
        h = g.add(edited.encode(), 'verify.md')  # known this run (a saved copy), not in git
        trans, _ = pb.load_transcripts(self.projects, cache, 1, g, needle=str(self.root))
        self.assertEqual(next(iter(trans.values()))['prompts']['verify.md'][1:3], ['h', h])
        fresh = pb.Git(self.root)  # a later run without that copy: the cache gives the text back
        self.assertNotIn(h, fresh.versions)
        pb.load_transcripts(self.projects, cache, 1, fresh, needle=str(self.root))
        self.assertEqual(fresh.versions.get(h), edited.encode())


class Prompts(unittest.TestCase):
    def test_cut_output_agrees_with_the_version_it_shows(self):
        v = ''.join(f'line {i}\n' for i in range(1, 40))
        out = 'Exit code 1\n' + v[:50] + '\n\n... [%d characters truncated] ...\n\n' % (len(v) - 80) + v[-30:] + 'ls: x'
        self.assertTrue(pb.agrees(out, v))
        self.assertFalse(pb.agrees(out.replace('line 38', 'line 99'), v))

    def test_cut_out_takes_a_whole_unknown_version_between_known_boundaries(self):
        v = '# Read one paper\n\nRule A.\nLast line.\n'
        edited = '# Read one paper\n\nRule A.\nRule B.\nLast line.\n'
        self.assertEqual(pb.cut_out(edited + '-rw-r--r-- texts/1.txt', v), edited)
        self.assertIsNone(pb.cut_out(edited.replace('Last line.', 'Other end.'), v))

    def test_read_tool_lines(self):
        self.assertEqual(pb.prompt_lines('1\ta\n2\t\n3\tb\n<system-reminder>x'), {1: 'a', 2: '', 3: 'b'})
        self.assertEqual(pb.prompt_lines('     1→a\n     2→b'), {1: 'a', 2: 'b'})


class Export(unittest.TestCase):
    """catlog.provenance merges the reconstructed lines for unstamped rows, never over a row's own stamp."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = catlog.ROOT
        catlog.ROOT = Path(self.tmp.name)
        (catlog.ROOT / 'sources').mkdir()
        with open(catlog.ROOT / 'sources' / 'provenance_backfill.tsv', 'w', newline='') as f:
            w = csv.DictWriter(f, pb.FIELDS, delimiter='\t', lineterminator='\n')
            w.writeheader()
            for rid in ('old1', 'own1'):
                w.writerow({'row_id': rid, 'read_by': 'reader', 'reader_model': OPUS, 'verifier_model': SONNET,
                            'read_prompt': 'a' * 12, 'verify_prompt': 'b' * 12, 'pipeline_commit': 'c' * 12,
                            'evidence': 'add x', 'how': 'reconstructed'})

    def tearDown(self):
        catlog.ROOT = self.saved
        self.tmp.cleanup()

    def test_merge(self):
        own = {'read_by': 'reader', 'reader_model': 'claude-opus-6', 'verifier_model': '', 'read_prompt': '',
               'verify_prompt': '', 'task_prompt': '', 'pipeline_commit': 'd' * 12}
        m = {'Km': {'metric': 'Km', 'row_id': 'old1'}, 'kcat': {'metric': 'kcat', 'row_id': 'own1', **own},
             'kcat/Km': {'metric': 'kcat/Km', 'row_id': 'none'}}
        p = catlog.provenance(m)
        self.assertEqual(p['Km'], {'read_by': 'reader', 'reader_model': OPUS, 'verifier_model': SONNET,
                                   'read_prompt': 'a' * 12, 'verify_prompt': 'b' * 12, 'task_prompt': '',
                                   'pipeline_commit': 'c' * 12, 'how': 'reconstructed'})
        self.assertEqual(p['kcat'], own)  # a real stamp wins over a backfill line
        self.assertNotIn('kcat/Km', p)
        flat = catlog.flat_provenance({'provenance': p})
        self.assertEqual(flat['reader_model'], f'{OPUS}; claude-opus-6')
        self.assertEqual(flat['provenance_how'], 'reconstructed; stamped')
        self.assertIn('provenance_how', catlog.FLAT)
        self.assertIsNone(catlog.provenance({'Km': {'metric': 'Km', 'row_id': 'none'}}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
