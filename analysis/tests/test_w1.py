#!/usr/bin/env python3
"""Offline tests of the W1 kit on fake data (no Claude session, no network, nothing written outside a temp folder):
  python3 -B tools/w1/test_w1.py"""
import contextlib, csv, io, json, math, os, re, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common_w1 as W  # noqa: E402
import h2h  # noqa: E402
import validate_plain as V  # noqa: E402
import claude_session as S  # noqa: E402
import score_w1 as SC  # noqa: E402
import w1_audit as AU  # noqa: E402
import run_reconcile as RC  # noqa: E402
import run_plain as RP  # noqa: E402
import score_rand as SR  # noqa: E402
import score_randfull as SRF  # noqa: E402
import score_locked as SL  # noqa: E402
import numpy as np  # noqa: E402


class Vendored(unittest.TestCase):
    def test_common_is_a_byte_copy(self):
        self.assertEqual(W.sha256(HERE / 'h2h_common.py'), h2h.COMMON_SHA256)
        self.assertEqual(W.sha256(W.H2H / 'common.py'), h2h.COMMON_SHA256)

    def test_rows_to_values_is_verbatim(self):
        src = (W.H2H / 's06_enzyextract_manual.py').read_text().splitlines(keepends=True)
        self.assertEqual(W.sha256(W.H2H / 's06_enzyextract_manual.py'), h2h.S06_SHA256)
        fn = ''.join(src[20:42])
        mine = (HERE / 'h2h_s06.py').read_text()
        self.assertTrue(mine.endswith(fn), 'h2h_s06.rows_to_values differs from s06 lines 21-42')

    def test_branch_units(self):
        self.assertTrue(h2h.C.units.__file__.startswith(str(W.REPO)))
        self.assertNotIn(h2h.MAIN_TOOLS, sys.path)


class Prompts(unittest.TestCase):
    def test_prompts_are_the_kit_texts(self):
        for md, name in (('A0_plain_prompt.md', 'A0.txt'), ('A2_compute_matched_prompt.md', 'A2_reconcile.txt'),
                         ('ADJUDICATE_prompt.md', 'adjudicate.txt')):
            blocks = re.findall(r'```text\n(.*?)```', (W.KIT / md).read_text(), re.S)
            self.assertEqual(len(blocks), 1)
            self.assertEqual(blocks[0], W.prompt_text(name), name)

    def test_fill(self):
        t = W.fill(W.prompt_text('A0.txt'), PMID='123', DIR='/e/plain/123', RUN='A0-r1', OUT='/e/runs/A0-r1/123.json',
                   VALIDATE='/e/plain/validate_plain.py')
        self.assertIn('{"pmid": "123", "model"', t)  # JSON braces survive
        self.assertIn('/tmp/A0-r1-123-p', t)
        with self.assertRaises(ValueError):
            W.fill(W.prompt_text('A0.txt'), PMID='123')

    def test_reconcile_variants(self):
        two = RC.reconcile_text(2)
        self.assertEqual(two, W.prompt_text('A2_reconcile.txt'))
        one, three = RC.reconcile_text(1), RC.reconcile_text(3)
        self.assertIn('{READ_A}. The list may contain', one)
        self.assertNotIn('{READ_B}', one)
        self.assertIn('{READ_A}, {READ_B} and {READ_C}', three)
        W.fill(three, PMID='1', DIR='d', RUN='r', OUT='o', VALIDATE='v', READ_A='a', READ_B='b', READ_C='c')


class Labels(unittest.TestCase):
    def test_runs(self):
        self.assertEqual([W.run_label('A0', r) for r in (1, '2', 'pilot', 'dry')], ['A0-r1', 'A0-r2', 'A0-pilot', 'A0-dry'])
        self.assertEqual(W.check_run('3'), '3')
        with self.assertRaises(SystemExit):
            W.check_run('4')
        self.assertEqual(W.eval_paths('/e', 'dry')['score'], Path('/e/records/score_dry'))
        self.assertEqual(W.eval_paths('/e', 'rounds')['score'], Path('/e/records/score'))
        self.assertEqual(W.out_file('/e', 'A2', 1, 'readB', '7'), Path(f"/e/out/{W.code('A2-r1-readB')}/7.json"))
        self.assertEqual(W.out_file('/e', 'A0', 'dry', None, '7'), Path(f"/e/out/{W.code('A0-dry')}/7.json"))
        self.assertEqual(W.eval_paths('/e', 'dry')['claims'], Path(f"/e/out/{W.code('claims-dry')}"))
        self.assertEqual(W.eval_paths('/e')['verdicts']['j2'], Path(f"/e/out/{W.code('verdicts-j2-rounds')}"))


class Validator(unittest.TestCase):
    ROW = {'metric': 'kcat', 'value': 1.5, 'unit': 's^-1', 'raw_value': '1.5', 'raw_unit': 's-1', 'enzyme': 'E',
           'organism': '', 'variant': 'wild type', 'substrate': 'S', 'cosubstrate': '', 'pH': 7.5, 'temperature_C': None,
           'conditions': '', 'location': 'Table 1'}

    def check(self, d):
        return V.problems(d)

    def test_good(self):
        self.assertEqual(self.check({'pmid': '1', 'model': 'm', 'note': '', 'rows': [self.ROW]}), [])
        self.assertEqual(self.check({'pmid': '1', 'model': 'm', 'note': 'none', 'rows': []}), [])

    def test_bad(self):
        bad = [dict(self.ROW, metric='Vmax'), dict(self.ROW, value=0), dict(self.ROW, value=True),
               dict(self.ROW, value=float('inf')), dict(self.ROW, unit='mM'), dict(self.ROW, variant=''),
               dict(self.ROW, pH='7.5'), dict(self.ROW, metric='Km', unit='uM')]
        for r in bad:
            self.assertTrue(self.check({'pmid': '1', 'model': 'm', 'note': '', 'rows': [r]}), r)
        self.assertTrue(self.check({'pmid': '1', 'rows': []}))
        self.assertTrue(self.check([]))


class Glyph(unittest.TestCase):
    def test_strip(self):
        body = 'Eur. J. Biochem.\n\nText 1.5 mM\n'
        warned = "GLYPH WARNING: the text layer of this PDF shows ... (DO NOT trust these characters here).\n\n" + body
        self.assertEqual(W.strip_glyph(warned), body)
        self.assertEqual(W.strip_glyph(body), body)
        self.assertEqual(W.strip_glyph('\n\n' + body), '\n\n' + body)


class Session(unittest.TestCase):
    def test_command_and_env(self):
        cmd = S.command(W.MODEL, 'u-1', ['/e/runs/A0-r1'], S.deny_read('/x/y'))
        self.assertEqual(cmd[:2], [W.CLI, '-p'])
        for flag, val in (('--model', W.MODEL), ('--effort', 'max'), ('--setting-sources', 'project'),
                          ('--permission-mode', 'dontAsk'), ('--allowedTools', W.ALLOWED_TOOLS),
                          ('--output-format', 'json'), ('--session-id', 'u-1')):
            self.assertEqual(cmd[cmd.index(flag) + 1], val)
        self.assertIn('--strict-mcp-config', cmd)
        deny = cmd[cmd.index('--disallowedTools') + 1]
        self.assertIn('WebFetch', deny)
        self.assertIn('Read(//x/y/**)', deny)
        i = cmd.index('--add-dir')
        self.assertEqual(cmd[i + 1:i + 4], ['/e/runs/A0-r1', '/tmp', '/private/tmp'])
        os.environ['CLAUDECODE'] = '1'
        os.environ['ANTHROPIC_BASE_URL'] = 'http://x'
        env = S.clean_env()
        self.assertNotIn('CLAUDECODE', env)
        self.assertNotIn('ANTHROPIC_BASE_URL', env)
        self.assertEqual(env['DISABLE_AUTOUPDATER'], '1')
        self.assertEqual(env['CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK'], '1')  # the model pin
        self.assertEqual(env['CLAUDE_CODE_NO_MODEL_FALLBACK'], '1')

    def test_dry_run_writes_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            rec = S.run_session('hello', d, W.MODEL, Path(d) / 'out.json', Path(d) / 'logs', 'x.a1', dry=True)
            self.assertTrue(rec['dry_run'])
            self.assertEqual((Path(d) / 'logs' / 'x.a1.prompt.txt').read_text(), 'hello')
            self.assertFalse((Path(d) / 'out.json').exists())


class Verdicts(unittest.TestCase):
    def test_final(self):
        f = SC.final_verdict
        self.assertEqual(f('supported', 'supported'), ('supported', False))
        self.assertEqual(f('wrong_scale', 'wrong_scale'), ('wrong_scale', False))
        self.assertEqual(f('wrong_scale', 'not_printed'), ('mixed', False))
        self.assertEqual(f('supported', 'wrong_number'), (None, True))
        self.assertEqual(f('supported', 'wrong_number', 'wrong_scale'), ('wrong_scale', True))
        self.assertEqual(f('supported', 'wrong_number', 'supported'), ('supported', True))
        self.assertEqual(f('supported', 'wrong_number', 'cannot_decide'), ('cannot_decide', True))
        self.assertEqual(f('cannot_decide', 'cannot_decide'), ('cannot_decide', False))
        self.assertEqual(f(None, 'supported'), (None, False))

    def test_r_and_boot(self):
        self.assertEqual(SC.r_of(0, 0), 1.0)
        self.assertEqual(SC.r_of(1, 0), math.inf)
        n = {a: np.full(60, 100.0) for a in ('A2', 'A6')}
        e = {'A2': np.full(60, 10.0), 'A6': np.full(60, 1.0)}
        b = SC.boot_ratio(e, n, 500, 1)
        self.assertGreater(b['R_lo'], 1)
        e0 = {'A2': np.full(60, 1.0), 'A6': np.zeros(60)}
        b0 = SC.boot_ratio(e0, n, 200, 1)
        self.assertEqual(b0['R_lo'], math.inf)
        self.assertEqual(SC.kappa(['a', 'b', 'a'], ['a', 'b', 'a']), 1.0)


GOLD_COLS = ['ID_gold', 'pubmed_id', 'Enzyme', 'Organism', 'Substrate', 'Commentary[Mutant]', 'Commentary[Temp]',
             'Commentary[pH]', 'Commentary[Cosubstrate]', 'Reference[Table/Text]', 'km(mM)', 'kcat(s^-1)',
             'km_kcat(mM^-1s^-1)']
EE_COLS = ['pmid', 'enzyme', 'enzyme_full', 'organism', 'substrate', 'substrate_full', 'mutant', 'temperature', 'pH',
           'src', 'descriptor', 'kcat', 'km', 'kcat_km']


def row(metric, value, variant='wild type', substrate='ATP', enzyme='kinase'):
    return {'metric': metric, 'value': value, 'unit': SC.UNIT[metric], 'raw_value': str(value), 'raw_unit': '',
            'enzyme': enzyme, 'organism': 'E. coli', 'variant': variant, 'substrate': substrate, 'cosubstrate': '',
            'pH': 7.5, 'temperature_C': 25, 'conditions': '', 'location': 'Table 1'}


class Pipeline(unittest.TestCase):
    """A fake eval tree: four papers, three arms, the pilot; triage, fake verdicts, decide, people."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ev = Path(self.tmp.name)
        P = W.eval_paths(self.ev, 'pilot')
        self.P = P
        self.saved = (W.dev_papers, SC.gold_sets, W.people_papers)
        W.dev_papers = lambda: ['1001', '1002', '1003']
        SC.gold_sets = lambda: {'1001': 'cosci', '1002': 'cosci', '1003': 'enzyextract'}
        W.people_papers = lambda: ['2001']
        P['keys'].mkdir(parents=True)
        with open(P['keys'] / h2h.GOLD_NAMES['cosci'], 'w', newline='') as fh:
            w = csv.DictWriter(fh, GOLD_COLS)
            w.writeheader()
            for i, (p, mut, km, kcat) in enumerate((('1001', 'nan', '0.5', '10'), ('1001', 'H52A', '', '2'),
                                                     ('1002', 'nan', '1.2', '30'))):
                w.writerow({'ID_gold': i, 'pubmed_id': p, 'Enzyme': 'kinase', 'Organism': 'E. coli', 'Substrate': 'ATP',
                            'Commentary[Mutant]': mut, 'Commentary[Temp]': '25', 'Commentary[pH]': '7.5',
                            'Commentary[Cosubstrate]': 'nan', 'Reference[Table/Text]': 'Table 1', 'km(mM)': km,
                            'kcat(s^-1)': kcat, 'km_kcat(mM^-1s^-1)': ''})
        with open(P['keys'] / h2h.GOLD_NAMES['ee_manual'], 'w', newline='') as fh:
            w = csv.DictWriter(fh, EE_COLS)
            w.writeheader()
            w.writerow({'pmid': '1003', 'enzyme': 'lipase', 'organism': 'B. subtilis', 'substrate': 'pNPB',
                        'mutant': 'WT', 'kcat': '5 s^-1', 'km': '200 µM', 'kcat_km': ''})
        for arm in W.ARMS:
            f = P['orders'] / f'{arm}-pilot.txt'
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text('1001\n1002\n1003\n2001\n')
        a0 = {'1001': [row('kcat', 10), row('Km', 500), row('kcat', 2, 'H52A'), row('kcat', 99, substrate='GTP')],
              '1002': [row('kcat', 30), row('Km', 1.2)],
              '1003': [row('kcat', 5, enzyme='lipase', substrate='pNPB'), row('Km', 0.2, enzyme='lipase', substrate='pNPB')],
              '2001': [row('Km', 0.33, substrate='NADH'), row('kcat', 7, substrate='NADH')]}
        a2 = {'1001': [row('kcat', 10), row('Km', 0.5), row('kcat', 2, 'H52A')],
              '1002': [row('kcat', 30), row('Km', 1.2), row('Km', 1.2)],  # a duplicate: counted once
              '1003': [row('kcat', 5, enzyme='lipase', substrate='pNPB'), row('Km', 0.2, enzyme='lipase', substrate='pNPB')],
              '2001': [row('Km', 0.33, substrate='NADH')]}
        for arm, data in (('A0', a0), ('A2', a2)):
            for p, rows in data.items():
                f = W.out_file(self.ev, arm, 'pilot', 'final' if arm == 'A2' else None, p)
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps({'pmid': p, 'model': W.MODEL, 'note': '', 'rows': rows}))
        d6 = P['runs'] / 'A6-pilot'
        d6.mkdir(parents=True)
        self.d6 = d6
        a6 = [{**row('kcat', 10), 'pmid': '1001', 'row_id': 'r1'}, {**row('Km', 0.5), 'pmid': '1001', 'row_id': 'r2'},
              {**row('kcat', 30), 'pmid': '1002', 'row_id': 'r3'}, {**row('Km', 1.2), 'pmid': '1002', 'row_id': 'r4'},
              {**row('kcat', 5, enzyme='lipase', substrate='pNPB'), 'pmid': '1003', 'row_id': 'r5'},
              {**row('Km', 0.2, enzyme='lipase', substrate='pNPB'), 'pmid': '1003', 'row_id': 'r6'},
              {**row('Km', 0.33, substrate='NADH'), 'pmid': '2001', 'row_id': 'r7'},
              {**row('kcat', 7, substrate='NADH'), 'pmid': '2001', 'row_id': 'r8'}]
        (d6 / 'catalog.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in a6))
        W.write_tsv(d6 / 'papers.tsv', [{'pmid': p, 'status': 'done'} for p in ('1001', '1002', '1003', '2001')],
                    ['pmid', 'status'])
        W.write_tsv(P['keys'] / 'people_values.tsv',
                    [{'pmid': '2001', 'key': 'k1', 'metric': 'Km', 'status': 'approved', 'kind': 'approved',
                      'human_value': '0.33', 'substrate': 'NADH', 'mutations': ''},
                     {'pmid': '2001', 'key': 'k2', 'metric': 'kcat', 'status': 'rejected', 'kind': 'rejected_dispute',
                      'human_value': '7', 'substrate': 'NADH', 'mutations': ''}], ['pmid', 'key', 'metric', 'status',
                                                                                       'kind', 'human_value', 'substrate',
                                                                                       'mutations'])

    def tearDown(self):
        W.dev_papers, SC.gold_sets, W.people_papers = self.saved
        self.tmp.cleanup()

    def test_triage_decide_people(self):
        SC.triage(self.ev, 'pilot')
        claims = sorted(self.P['claims'].glob('*.json'))
        self.assertTrue(claims)
        shown = [c for f in claims for c in json.loads(f.read_text())]
        ids = [c['id'] for c in shown]
        self.assertEqual(len(ids), len(set(ids)))
        for c in shown:  # blinded: no source, location, printed form or quote
            self.assertEqual(set(c), {'id', 'metric', 'value', 'unit', 'enzyme', 'organism', 'variant', 'substrate',
                                      'cosubstrate', 'pH', 'temperature_C'})
            self.assertNotEqual(c['cosubstrate'], 'nan')
        cmap = [json.loads(x) for x in (self.P['score'] / 'private' / 'claims_map.jsonl').read_text().splitlines() if x]
        self.assertGreaterEqual(sum(1 for c in cmap if c['decoy']), len({c['pmid'] for c in cmap}))
        # the arm values that are wrong: A0's Km 500 (x1000) and its kcat 99 (not printed); everything else is right
        wrong = {('Km', 500.0), ('kcat', 99.0)}
        for j in ('j1', 'j2'):
            by = {}
            for c in cmap:
                v = c['shown']['value']
                verdict = ('wrong_scale' if c['decoy'] in ('x1000', 'x60') else 'wrong_identity' if c['decoy'] else
                           'wrong_scale' if (c['metric'], v) == ('Km', 500.0) else
                           'not_printed' if (c['metric'], v) == ('kcat', 99.0) else 'supported')
                if j == 'j2' and (c['metric'], v) == ('kcat', 99.0):
                    verdict = 'supported'  # a split: the third judge decides
                by.setdefault((c['pmid'], c['chunk']), []).append({'id': c['claim_id'], 'verdict': verdict})
            for (p, ch), vs in by.items():
                W.write_json(self.P['verdicts'][j] / f'{p}.{ch}.json', {'pmid': p, 'verdicts': vs})
        split = [c for c in cmap if (c['metric'], c['shown']['value']) == ('kcat', 99.0)]
        W.write_json(self.P['verdicts']['j3'] / f"{split[0]['pmid']}.{split[0]['chunk']}.json",
                     {'verdicts': [{'id': split[0]['claim_id'], 'verdict': 'not_printed'}]})
        out = SC.decide(self.ev, 'pilot', B=200)
        self.assertTrue(out['quality_gate']['passed'], out['quality_gate'])
        self.assertEqual(out['papers_in_analysis'], 3)
        rates = out['primary']['rate_per_1000']
        self.assertAlmostEqual(rates['A0'], 1000 * 2 / 8)  # 8 values on the 3 gold papers, 2 wrong
        self.assertEqual(rates['A2'], 0.0)
        self.assertEqual(rates['A6'], 0.0)
        self.assertEqual(out['primary']['R_A2_over_A6'], 1.0)
        self.assertEqual(out['decision'], 'STOP')
        self.assertEqual(out['errors_by_class_mean_per_run']['A0'], {'not_printed': 1.0, 'wrong_scale': 1.0})
        rec = out['recall_identity_aware']
        self.assertEqual(rec['A2'], 1.0)  # every true value, including the H52A kcat
        self.assertLess(rec['A6'], 1.0)   # A6 missed the H52A kcat
        ppl = SC.people(self.ev, 'pilot')
        self.assertEqual(ppl['arms']['A0']['found'], 1)
        self.assertEqual(ppl['arms']['A0']['repeated'], 1)
        self.assertEqual(ppl['arms']['A2']['repeated'], 0)
        with self.assertRaises(SystemExit):  # the pool is drawn once
            SC.triage(self.ev, 'pilot')


def fake_transcript(path, calls, model=W.MODEL, task='task', cwd=None, extra=(), add_dirs=None):
    """A Claude Code transcript: the first user message (task), then one assistant message per tool call (name, input,
    model, result: a call with a result string gets a tool-use id and the user line carrying its result); extra lines
    (dicts) go after the calls."""
    lines = [{'type': 'user', 'version': W.CLI_VERSION, 'message': {'role': 'user', 'content': task}}]
    if add_dirs is not None:
        lines.append({'type': 'attachment', 'attachment': {'type': 'environment', 'snapshot': {
            'workingDirectory': cwd, 'additionalWorkingDirectories': add_dirs}}})
    for i, call in enumerate(calls):
        name, inp = call[:2]
        m = (call[2] if len(call) > 2 else None) or model
        use = {'type': 'tool_use', 'name': name, 'input': inp}
        if len(call) > 3:
            use['id'] = f'tu{i}'
        lines.append({'type': 'assistant', 'version': W.CLI_VERSION, 'timestamp': f'2026-11-01T10:{i:02d}:00.000Z',
                      'message': {'id': f'm{i}', 'model': m, 'usage': {'input_tokens': 10, 'output_tokens': 5},
                                  'content': [use]}})
        if len(call) > 3:
            lines.append({'type': 'user', 'version': W.CLI_VERSION, 'message': {'role': 'user', 'content': [
                {'type': 'tool_result', 'tool_use_id': f'tu{i}', 'content': call[3]}]}})
    lines += list(extra)
    if cwd:
        for x in lines:
            x.setdefault('cwd', cwd)
    Path(path).write_text(''.join(json.dumps(x) + '\n' for x in lines))
    return Path(path)


FALLBACK = {'type': 'system', 'subtype': 'model_refusal_fallback', 'trigger': 'refusal', 'scope': 'session',
            'originalModel': 'claude-opus-5-5', 'fallbackModel': 'claude-opus-5', 'apiRefusalCategory': 'bio'}


def fake_copy(a6):
    """A catlog-copy folder for code that runs in it: its own git repository with one commit (w1_setup records its HEAD)
    and a catlog.py whose claim_prompts writes a claim record (w1_setup.lay_down)."""
    a6 = Path(a6)
    a6.mkdir(parents=True, exist_ok=True)
    (a6 / 'catlog.py').write_text("import pathlib\n\n\ndef claim_prompts(p):\n"
                                  "    pathlib.Path('work', p + '.prompts.json').write_text('{}\\n')\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    for cmd in (['init', '-q'], ['-c', 'user.name=T', '-c', 'user.email=t@example.org', '-c', 'commit.gpgsign=false',
                                 'commit', '-q', '--allow-empty', '-m', 'catlog snapshot']):
        subprocess.run(['git', '-C', str(a6), *cmd], check=True, capture_output=True, env=env)
    return a6


class Audit(unittest.TestCase):
    def transcript(self, d, calls, model=W.MODEL, **k):
        return fake_transcript(Path(d) / 't.jsonl', calls, model, **k)

    def test_paths_and_tools(self):
        with tempfile.TemporaryDirectory() as d:
            cwd = '/home/x/kinetics-reading/papers/123'
            out = '/home/x/kinetics-reading/out/bcd234/123.json'
            allow = [cwd + '/', out, '/private/tmp/bcd234-123-*']
            ok = self.transcript(d, [('Read', {'file_path': cwd + '/paper.txt'}),
                                     ('Bash', {'command': f'pdftoppm -r 200 -f 2 -l 2 -png {cwd}/source.pdf /tmp/bcd234-123-p'}),
                                     ('Write', {'file_path': out})])
            res, _ = AU.audit_agent(ok, [W.MODEL], allow, cwd)
            self.assertFalse(res['broken'], res['violations'])
            self.assertEqual(res['total'], 45)
            bad = self.transcript(d, [('Read', {'file_path': '/home/x/catlog-v2/catalog.jsonl'}),
                                      ('WebFetch', {'url': 'https://example.org'}),
                                      ('Bash', {'command': 'ls ../124'})])
            res, _ = AU.audit_agent(bad, [W.MODEL], allow, cwd)
            kinds = {v[1] for v in res['violations'] if v[0] == 'break'}
            self.assertEqual(kinds, {'path', 'tool'})
            other = self.transcript(d, [('Read', {'file_path': cwd + '/paper.txt'})], model='claude-opus-5')
            res, _ = AU.audit_agent(other, [W.MODEL], allow, cwd)
            self.assertTrue(res['broken'])

    def test_not_paths(self):
        """Dry-run fix (a): XML tags, sed's /g and divisions in a command or a Grep pattern name no file; real paths
        in the same commands still count."""
        cmd = ("cd /tmp && python3 -I - <<'EOF'\ns=open('/home/x/kinetics-reading/papers/1/source.xml').read()\n"
               "t=s[s.find('<ce:table'):s.find('</ce:table>')]; u=s.find('</table-wrap>'); v=x/1000\nEOF")
        got = AU.named_paths('Bash', {'command': cmd}, '/home/x/kinetics-reading/papers/1')
        self.assertEqual(got, ['/private/tmp', '/home/x/kinetics-reading/papers/1/source.xml'])
        self.assertEqual(AU.named_paths('Bash', {'command': "sed -e 's/<[^>]*>/ /g' /home/x/f.xml | tr -s ' '"}, '/x'),
                         ['/home/x/f.xml'])
        self.assertEqual(AU.named_paths('Grep', {'pattern': '<table-wrap[\\s\\S]*?</table-wrap>', 'path': '/home/x/f.xml'},
                                        '/x'), ['/home/x/f.xml'])
        self.assertEqual(AU.named_paths('Bash', {'command': 'cat <the CatLog folder>/catalog.jsonl'}, '/x'),
                         ['<the CatLog folder>/catalog.jsonl'])  # a planted real break still counts

    def test_tmp_cwd(self):
        """Dry-run fix (b): /tmp as the working directory (agents cd there to render page images) is fine; another
        session's scratch as a cwd still breaks."""
        with tempfile.TemporaryDirectory() as d:
            cwd = '/home/x/kinetics-reading/papers/123'
            tr = self.transcript(d, [('Bash', {'command': 'cd /tmp && pdfinfo /home/x/kinetics-reading/papers/123/source.pdf'})],
                                 cwd='/private/tmp')
            res, _ = AU.audit_agent(tr, [W.MODEL], [cwd + '/'], cwd, want_cwd=cwd)
            self.assertFalse(res['broken'], res['violations'])
            other = f"/private/tmp/{W.code('A2-r1-readB')}-123-x"
            tr = self.transcript(d, [('Read', {'file_path': cwd + '/paper.txt'})], cwd=other)
            res, _ = AU.audit_agent(tr, [W.MODEL], [cwd + '/'], cwd, want_cwd=cwd)
            self.assertIn(('break', 'cwd', other), res['violations'])

    def test_reconcile_reads(self):
        """Dry-run fix (c): the reconcile may list and read its own paper's reads (the folders and files its prompt
        names), never another paper's read."""
        with tempfile.TemporaryDirectory() as d:
            ra, rb = W.out_dir('/home/x/k', 'A2-r1-readA'), W.out_dir('/home/x/k', 'A2-r1-readB')
            out = W.out_file('/home/x/k', 'A2', 1, 'final', '123')
            prompt = W.fill(W.prompt_text('A2_reconcile.txt'), PMID='123', DIR='/home/x/k/papers/123',
                            RUN=W.code('A2-r1-final'), OUT=out, VALIDATE='/home/x/k/papers/check_rows.py',
                            READ_A=ra / '123.json', READ_B=rb / '123.json')
            rec = {'cwd': '/home/x/k/papers/123', 'out': str(out)}
            allow, notes = AU.plain_allow(rec, prompt, '123')
            tr = self.transcript(d, [('Bash', {'command': f'ls -la {ra}/ {rb}/ {out.parent}/'}),
                                     ('Read', {'file_path': str(ra / '123.json')}),
                                     ('Bash', {'command': f'python3 /home/x/k/papers/check_rows.py {out}'})], task=prompt)
            res, _ = AU.audit_agent(tr, [W.MODEL], allow, rec['cwd'], notes=notes, want_cwd=rec['cwd'])
            self.assertFalse(res['broken'], res['violations'])
            tr = self.transcript(d, [('Read', {'file_path': str(ra / '124.json')})], task=prompt)
            res, _ = AU.audit_agent(tr, [W.MODEL], allow, rec['cwd'], notes=notes, want_cwd=rec['cwd'])
            self.assertIn(('break', 'path', str(ra / '124.json')), res['violations'])

    def test_path_prefix(self):
        """Pilot fix: a parent folder a script only joins file names to is noted; a listing, a glob or a fragment into
        another paper's or another arm's files still breaks, and so does a folder above the eval root."""
        with tempfile.TemporaryDirectory() as d:
            root = '/home/x/k'
            ra, rb = W.out_dir(root, 'A2-r1-readA'), W.out_dir(root, 'A2-r1-readB')
            out = W.out_file(root, 'A2', 1, 'final', '123')
            prompt = W.fill(W.prompt_text('A2_reconcile.txt'), PMID='123', DIR=root + '/papers/123',
                            RUN=W.code('A2-r1-final'), OUT=out, VALIDATE=root + '/papers/check_rows.py',
                            READ_A=ra / '123.json', READ_B=rb / '123.json')
            rec = {'cwd': root + '/papers/123', 'out': str(out)}
            allow, notes = AU.plain_allow(rec, prompt, '123')
            saved, AU.EXISTS = AU.EXISTS, lambda p: True  # as if every named path existed
            self.addCleanup(setattr, AU, 'EXISTS', saved)
            run = lambda cmd: AU.audit_agent(self.transcript(d, [('Bash', {'command': cmd})], task=prompt), [W.MODEL],
                                             allow, rec['cwd'], notes=notes, want_cwd=rec['cwd'], prefix_root=root)[0]
            oa, ob = ra.name + '/123.json', rb.name + '/123.json'
            good = f"python3 -I -c \"\nimport json\nd='{root}/out/'\na=json.load(open(d+'{oa}'))\nb=json.load(open(d+'{ob}'))\n\""
            res = run(good)
            self.assertFalse(res['broken'], res['violations'])
            self.assertIn(('note', 'path_prefix', root + '/out'), res['violations'])
            res = run(f"python3 -c \"base='{root}'\nm=open(base+'/out/{out.parent.name}/123.json')\"")
            self.assertFalse(res['broken'], res['violations'])
            res = run(f"python3 -c \"d='{root}/out/'\nx=open(d+'{ra.name}/124.json')\"")  # another paper's read
            self.assertTrue(res['broken'], res['violations'])
            res = run(f"python3 -c \"d='{root}/out/'\nx=open(d+'{W.code('A0-r1')}/123.json')\"")  # another arm
            self.assertTrue(res['broken'], res['violations'])
            res = run(f"python3 -c \"import os; d='{root}/out/'; print(os.listdir(d))\"")  # a listing
            self.assertTrue(res['broken'], res['violations'])
            res = run(f"ls -la {root}/out/")
            self.assertTrue(res['broken'], res['violations'])
            res = run(f"cat {root}/out/*/123.json")  # a glob after the folder
            self.assertTrue(res['broken'], res['violations'])
            res = run("python3 -c \"d='/home/x/'; a=open(d+'k/out/{oa}')\"")  # above the eval root
            self.assertTrue(res['broken'], res['violations'])

    def test_own_output_listing(self):
        """The owner's rule of 2026-11-06, strict form: a bare `ls <own output folder>/<PMID>*` that the shell answered
        with 'no matches found' (or that Claude Code denied, so it never ran) is noted. Everything else breaks: anything
        listed (even its own output), no result on record, another folder or a shorter prefix, and every way an
        adversarial check found (6 Nov) to read or list more than the pattern under a bare-looking ls."""
        with tempfile.TemporaryDirectory() as d:
            root = '/home/x/k'
            F = f'{root}/out/abc123'
            claims, out = f'{root}/out/cla111/123.c01.json', f'{F}/123.c01.json'
            prompt = f'Claims: {claims}\nWrite your verdicts to {out}\n'
            rec = {'cwd': root + '/checks/123', 'out': out}
            allow, notes = AU.plain_allow(rec, prompt, '123')
            NOMATCH = f'(eval):1: no matches found: {F}/123*'
            DENIED = ("Permission to use Bash has been denied because Claude Code is running in don't ask mode. "
                      'IMPORTANT: You *may* attempt to accomplish this action using other tools')
            SHOWN = '{"pmid": "123", "chunk": "c02", "verdicts": [{"id": "x", "verdict": "supported"}]}'

            def run(cmd, result=None, **extra):
                inp = {'command': cmd, **extra}
                call = ('Bash', inp, None, result) if result is not None else ('Bash', inp)
                tr = self.transcript(d, [call, ('Write', {'file_path': out})], task=prompt)
                return AU.audit_agent(tr, [W.MODEL], allow, rec['cwd'], notes=notes, want_cwd=rec['cwd'],
                                      own_out=out, pmid='123')[0]
            for cmd, result in ((f'ls -la {F}/123* 2>&1', NOMATCH), (f'ls {F}/123* 2>/dev/null', NOMATCH),
                                (f'ls -la {F}/123* 2>&1; head -c 300 {root}/checks/123/paper.txt',
                                 NOMATCH + '\nTitle of the paper'),  # as the judges wrote it: other work after a ';'
                                (f'head -c 300 {root}/checks/123/paper.txt; ls {F}/123* 2>/dev/null',
                                 'Title of the paper\n' + NOMATCH),
                                (f'ls -la {F}/123* 2>/dev/null; echo "exit: $?"', DENIED),  # never ran
                                (f'ls -la {F}/123* 2>&1; pdfinfo {root}/checks/123/source.pdf 2>&1 | head -20', DENIED)):
                res = run(cmd, result)
                self.assertFalse(res['broken'], (cmd, res['violations']))
                self.assertIn(('note', 'own_output_listing', f'{F}/123'), res['violations'])
            breaks = [
                (f'ls -la {F}/123*', f'-rw-r--r-- 1 x staff 10 Nov  6 10:00 {out}'),  # listed (its own output): strict
                (f'ls -la {F}/123* 2>/dev/null', ''),  # an empty answer is no proof that nothing matched
                (f'ls {F}/123*', f'{out}\n{F}/123.c02.json'),  # the paper's other chunk
                (f'ls {F}/123*', f'{F}/1234.c01.json'),  # a paper whose PMID starts with 123
                (f'ls {F}/12* 2>&1', f'(eval):1: no matches found: {F}/12*'),  # a shorter prefix
                (f'ls {root}/out/def456/123* 2>&1', f'(eval):1: no matches found: {root}/out/def456/123*'),
                (f'ls {F}/123*', None),  # no result on record
                (f'cat {F}/123*', SHOWN), (f'ls {F}/123* | xargs cat', SHOWN), (f'ls {F}/123* 2>&1 | head', SHOWN),
                (f'for f in {F}/123*; do cat $f; done', SHOWN), (f'ls $(cat {F}/123*)', SHOWN),
                # what the adversarial check of 6 Nov built (scratchpad review_rule/bypass/): each showed more
                (f"ls {F}/123*(e:'! cat $REPLY':) 2>&1", SHOWN + '\n' + NOMATCH),  # a glob qualifier runs code
                (f'ls {F}/123* <(cat {F}/123* >&2) >/dev/null', SHOWN),  # process substitution
                (f'ls -d {F}/123* > >(while read f; do cat "$f"; done)', SHOWN),
                (f"ls -d {F}/123* ';' 2>/dev/null | while read f; do cat \"$f\"; done", SHOWN),  # a quoted ';'
                (f'ls -d {F}/123* \\\n| while read f; do cat "$f"; done', SHOWN),  # a backslash-newline
                (f'ls() {{ cat "$@"; }}; ls {F}/123*', SHOWN),  # a function named ls
                (f'hash ls=/bin/cat; command ls {F}/123*', SHOWN),
                (f'PATH=/tmp/evilbin:$PATH; ls {F}/123*', SHOWN),
                (f'ls {F}/123* >/dev/null 2>&1; cat {root}/out//abc123/123*', SHOWN),  # a second spelling
                (f'ls {F}/123* >/dev/null 2>&1; cat {F}/./123*', SHOWN),
                (f'ls {F}/123* >/dev/null; cat $~_', SHOWN),  # zsh reuses the last word
                (f'ls -d {F}/123* > names.txt 2>&1', ''),  # written to a file, read later
                (f'ls {F}/123*(:h) 2>&1', '1234.json\n999.json'),  # a modifier lists the folder
                (f'ls -F {F}/123* 2>&1', f'{F}/1234.json*'),
            ]
            for cmd, result in breaks:
                res = run(cmd, result)
                self.assertTrue(res['broken'], (cmd, res['violations']))
            res = run(f'ls {F}/123*', NOMATCH, run_in_background=True)  # its answer is only a pointer to a file
            self.assertTrue(res['broken'], res['violations'])
            res = run(f'ls -d {root}/checks/123/paper.txt {F}/123*',
                      '<persisted-output>\nOutput too large (61.2KB). Full output saved to: x\n</persisted-output>')
            self.assertTrue(res['broken'], res['violations'])

    def test_git_exclude_is_no_peek(self):
        """Pilot fix: leaving .git out of a find or grep is not a look at the repository; reading it still is."""
        for cmd in ("find . -maxdepth 2 -newer /tmp/read-1/x.py -type f -not -path './.git/*' 2>/dev/null | head",
                    'find . -newer /tmp/r/b.py -type f -not -path "./.git/*" -not -path "./work/*.json"',
                    'find . -path ./.git -prune -o -type f -print', 'grep -rn kcat --exclude-dir=.git .',
                    "rg -g '!.git' kcat"):
            self.assertIsNone(AU.git_peek(cmd), cmd)
        for cmd in ('git log --oneline -3', 'cat .git/HEAD', 'ls .git/refs/heads',
                    "find . -not -path './.git/*' -newer x; git log -1"):
            self.assertIsNotNone(AU.git_peek(cmd), cmd)

    def test_a6_forbidden(self):
        import human_review as HR
        call = {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'cat <the CatLog folder>/work/1.read.json'}}
        self.assertTrue(HR.FORBIDDEN_IN_COPY.findall(HR._named(call)))
        gold = {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'grep -r 12345 ~/Downloads/Golden_Benchmark'}}
        self.assertTrue(AU.FORBIDDEN_A6.findall(HR._named(gold)))
        self.assertFalse(HR.FORBIDDEN_IN_COPY.findall(HR._named(gold)))  # no gold name in catlog-copy's own code

    def test_review_rules(self):
        """REVIEW.md 1.3, 1.5, 1.7, 3.5: own session folders allowed, other scratchpads and other sessions' scratch broken,
        network code broken, a bare URL noted, a transcript never readable."""
        tr = W.PROJECTS / '-home-x-kinetics-reading-papers-123' / 'u-1.jsonl'
        own = AU.own_session_dirs(tr)
        self.assertEqual(own, [f'{W.PROJECTS}/-home-x-kinetics-reading-papers-123/u-1/',
                               f'{W.CLAUDE_TMP}/-home-x-kinetics-reading-papers-123/u-1/'])
        a6tr = W.PROJECTS / '-home-x-k-catlog-copy' / 's-9' / 'subagents' / 'workflows' / 'wf_1' / 'agent-a1.jsonl'
        self.assertEqual(AU.own_session_dirs(a6tr)[0], f'{W.PROJECTS}/-home-x-k-catlog-copy/s-9/')
        ca, cb = W.code('A2-r1-readA'), W.code('A2-r1-readB')
        allow = [f'/private/tmp/{ca}-123-*'] + own
        j = lambda p, **k: AU.judge_path(p, allow, **k)
        saved, AU.EXISTS = AU.EXISTS, lambda p: True  # as if every named path existed
        self.addCleanup(setattr, AU, 'EXISTS', saved)
        self.assertEqual(j(f'{W.PROJECTS}/-home-x-kinetics-reading-papers-123/u-1/tool-results/b1.txt'), 'ok')
        self.assertEqual(j(f'{W.CLAUDE_TMP}/-Users-<user>-Documents-catlog-v2/s/scratchpad/read-123/make.py'), 'break')
        self.assertEqual(j(f'/private/tmp/{cb}-123-rows.json'), 'break')
        self.assertEqual(j('/private/tmp/A2-r1-readB-123-rows.json'), 'break')  # the first layout's names too
        self.assertEqual(j('/private/tmp/read-123/build.py'), 'break')
        self.assertEqual(j('/private/tmp/read-123/build.py', strict=(AU.EVAL_SCRATCH,)), 'note')  # A6: another paper's
        self.assertEqual(j(f'/private/tmp/{ca}-123-p-1.png'), 'ok')
        self.assertEqual(j('/private/tmp/other.txt'), 'note')
        self.assertEqual(j(str(W.CLAUDE_TMP)), 'note')  # listing the parent of its own scratchpad
        self.assertEqual(j(f'{W.CLAUDE_TMP}/-home-x-kinetics-reading-papers-123/u-'), 'note')  # a cut-off of its own path
        AU.EXISTS = lambda p: False
        self.assertEqual(j(f'{W.CLAUDE_TMP}/-Users-<user>-Documents-catlog-v2/s/x.py'), 'note')  # nothing there to read
        self.assertEqual(j(f'/private/tmp/{cb}-123-rows.json'), 'break')  # moved away after its session: still a break
        AU.EXISTS = lambda p: True
        self.assertEqual(j(f'{W.PROJECTS}/-home-x-k-catlog-copy/s-9/subagents/workflows/wf_1/agent-a2.jsonl'), 'break')
        # locked set, 11 Nov: only Claude Code's per-user tmp roots are other sessions' scratchpads; a folder an A6 agent made
        # with mktemp -d /tmp/claude-verify-XXXXXX is noted for an A6 agent and breaks a plain session or a judge
        a6s = (AU.EVAL_SCRATCH,)
        self.assertEqual(j('/private/tmp/claude-verify-QLeI5w/verify-123/p2_left.png', strict=a6s), 'note')
        self.assertEqual(j('/private/tmp/claude-verify-QLeI5w', strict=a6s), 'note')
        self.assertEqual(j('/private/tmp/claude-verify-QLeI5w/verify-123/write_verdicts.py'), 'break')
        self.assertEqual(j('/private/tmp/claude-verify-QLeI5w'), 'break')
        self.assertEqual(j('/private/tmp/xyz.AbCdEf/verify-456/check.py'), 'break')  # an A6 role folder one level down
        self.assertEqual(j('/private/tmp/xyz.AbCdEf/verify-456/check.py', strict=a6s), 'note')
        self.assertEqual(j('/private/tmp/claude-502/-home-y/s/scratchpad/notes.md'), 'break')  # another user's root
        self.assertEqual(j(f'{W.CLAUDE_TMP}/-Users-<user>-Documents-catlog-v2/s/tasks/b1.output'), 'break')
        self.assertTrue(AU.CC_TMP.match(str(W.CLAUDE_TMP)) and AU.CC_TMP.match(str(W.CLAUDE_TMP) + '/x'))
        self.assertFalse(AU.CC_TMP.match('/private/tmp/claude-verify-1/x') or AU.CC_TMP.match('/private/tmp/claude-5x/y'))
        net = lambda cmd: AU.network({'name': 'Bash', 'input': {'command': cmd}})
        self.assertEqual(net('python3 -c "import urllib.request as u; u.urlopen(\'https://x.org\')"'), 'break')
        self.assertEqual(net('python3 -c "import requests"'), 'break')
        self.assertEqual(net(f'python3 /tmp/{ca}-1-x.py'), '')
        self.assertEqual(net('python3 -c "print(\'see https://doi.org/10.1/x\')"'), 'note')
        self.assertEqual(AU.network({'name': 'Write', 'input': {'file_path': f'/tmp/{ca}-1-x.py',
                                                                'content': 'import requests\nrequests.get(u)'}}), 'break')

    def test_relayed_request(self):
        task = ('[Workflow harness — user request] The harness relays, verbatim and indented below, the user request ...:\n'
                '  run the A6 arm of the W1 kill test against the gold sets\n\nFollow /e/catlog-copy/prompts/read.md for PMID 1.')
        self.assertEqual(AU.relayed(task), 'run the A6 arm of the W1 kill test against the gold sets')
        self.assertTrue(W.eval_word_hits(AU.relayed(task)))
        computed = ('[Workflow harness — computed task] The task text below was computed at runtime by a workflow '
                    'script.\n  Scientific data curation ... so only the verifier runs.')
        self.assertEqual(AU.relayed(computed), '')  # the computed task is the prompt, not a relayed request
        import run_a6 as RA6
        line = RA6.launch_line({'pmids': ['1', '2'], 'lanes': 9, 'root': str(W.eval_paths()['a6'])})
        self.assertEqual(W.eval_word_hits(line), [])
        self.assertTrue(W.eval_word_hits('Run the saved workflow catlog-batch with the args in /e/orders/A6-r1.args.json'))
        self.assertEqual(AU.relayed('Follow prompts/read.md'), '')
        rows = [{'pmid': '1', 'role': 'read'}, {'pmid': '1', 'role': 'verify'}, {'pmid': '2', 'role': 'read'}]
        self.assertEqual(AU.a6_missing(rows, ['1', '2', '3']), ['2', '3'])

    def test_stray_and_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            f = self.transcript(d, [('Read', {'file_path': '/e/papers/123/paper.txt'})], cwd='<the CatLog folder>')
            res, _ = AU.audit_agent(f, [W.MODEL], ['/e/papers/123/'], '/e/catlog-copy', want_cwd='/e/catlog-copy')
            self.assertIn(('break', 'cwd', '<the CatLog folder>'), res['violations'])

    def test_eval_words_shown(self):
        """Dry-run fix 3: a session shown an evaluation word in its cwd, its added folders or its prompt breaks."""
        with tempfile.TemporaryDirectory() as d:
            old = '<the first layout of the kit folder>/plain/123'
            tr = self.transcript(d, [('Read', {'file_path': old + '/paper.txt'})], cwd=old,
                                 task=f'Paper 123. Its files are in {old}: ... /tmp/A0-r1-123-p', add_dirs=['/tmp'])
            res, _ = AU.audit_agent(tr, [W.MODEL], [old + '/'], old, want_cwd=old)
            words = [v for v in res['violations'] if v[1] == 'eval_word']
            self.assertTrue(any(v[2].startswith('cwd:') for v in words))
            self.assertTrue(any(v[2].startswith('prompt:') and 'a0' in v[2] for v in words))
            new = '<the kit folder>/papers/123'
            tr = self.transcript(d, [('Read', {'file_path': new + '/paper.txt'})], cwd=new,
                                 task=f"Paper 123. Its files are in {new}: ... /tmp/{W.code('A0-r1')}-123-p",
                                 add_dirs=[str(W.out_dir('<the kit folder>', 'A0-r1')), '/tmp'])
            res, _ = AU.audit_agent(tr, [W.MODEL], [new + '/'], new, want_cwd=new)
            self.assertFalse([v for v in res['violations'] if v[1] == 'eval_word'], res['violations'])

    def test_model_fallback_line(self):
        """Dry-run fix 2: the fallback line Claude Code writes breaks even before a message of the other model."""
        with tempfile.TemporaryDirectory() as d:
            tr = self.transcript(d, [('Read', {'file_path': '/e/papers/1/paper.txt'})], extra=[FALLBACK])
            res, _ = AU.audit_agent(tr, [W.MODEL], ['/e/papers/1/'], '/e/papers/1')
            self.assertTrue(any(v[1] == 'model_fallback' and v[0] == 'break' for v in res['violations']))


class EvalWords(unittest.TestCase):
    def test_one_list(self):
        for text in ('<the first layout of the kit folder>/plain/1', '/x/w1/a6/prompts/read.md', '/tmp/W1adj-j1-c01-1-p',
                     '/x/runs/A0-r1/1.json', '/x/score_dry/claims/1.c01.json', 'the gold sets', 'an evaluation run',
                     'benchmark files', 'kill test', 'the adjudicator', 'Co-Scientist', 'EnzyExtract', 'plain arm'):
            self.assertTrue(W.eval_word_hits(text), text)
        for text in ('report its row count, so only the verifier runs.', 'Scientific data curation: reconcile two '
                     'independent extractions of enzyme kinetic constants', '<the kit folder>/'
                     'catlog-copy/prompts/read.md', 'kcat/Km in mM^-1 s^-1', '/private/tmp/claude-501/x/scratchpad'):
            self.assertEqual(W.eval_word_hits(text), [], text)

    def test_codes(self):
        t = W.code_table()
        self.assertEqual(len(set(t.values())), len(t))  # one code per label
        for lab, c in t.items():
            self.assertEqual(len(c), 6)
            self.assertEqual(W.eval_word_hits(f'/x/{c}/1.json /tmp/{c}-1-p'), [], (lab, c))
            self.assertTrue(set(c) <= set(W.CODE_ALPHABET))

    def test_prompts_neutral(self):
        """Every filled prompt kind of the new layout carries no evaluation word."""
        ev = Path('<the kit folder>')
        P = W.eval_paths(ev)
        texts = [W.fill(W.prompt_text('A0.txt'), PMID='1', DIR=P['plain'] / '1', RUN=W.code(lab),
                        OUT=W.out_dir(ev, lab) / '1.json', VALIDATE=P['validator']) for lab in W.plain_labels()]
        texts.append(W.fill(W.prompt_text('A2_reconcile.txt'), PMID='1', DIR=P['plain'] / '1', RUN=W.code('A2-r2-final'),
                            OUT=W.out_file(ev, 'A2', 2, 'final', '1'), VALIDATE=P['validator'],
                            READ_A=W.out_file(ev, 'A2', 2, 'readA', '1'), READ_B=W.out_file(ev, 'A2', 2, 'readB', '1')))
        for which in ('rounds', 'pilot', 'dry'):
            Q = W.eval_paths(ev, which)
            for j in W.JUDGES:
                texts.append(W.fill(W.prompt_text('adjudicate.txt'), PMID='1', DIR=P['adj'] / '1', CLAIMS=Q['claims'] / '1.c01.json',
                                    OUT=Q['verdicts'][j] / '1.c01.json', RUN=f"{W.code(W.judge_label(j))}-c01"))
        for x in texts:
            self.assertEqual(W.eval_word_hits(x), [], x[:200])
        self.assertEqual(W.eval_word_hits((HERE / 'validate_plain.py').read_text()), [])  # papers/check_rows.py


class ModelSwitch(unittest.TestCase):
    """Dry-run fix 2: the pin and the once-more rule (claude_session.step), on fake sessions."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.saved = S.run_session

    def tearDown(self):
        S.run_session = self.saved
        self.tmp.cleanup()

    def fake(self, plan):
        """plan: one (switched, writes_valid_output) per session, in order."""
        calls = []

        def run(prompt, cwd, model, out_file, log_dir, label, *a, **k):
            sw, good = plan[len(calls)]
            calls.append((label, model))
            tr = fake_transcript(self.d / f'{label}.jsonl', [('Read', {'file_path': '/x'}, model)] +
                                 ([('Read', {'file_path': '/x'}, 'claude-opus-5')] if sw else []),
                                 model=model, extra=[FALLBACK] if sw else [])
            if good:
                Path(out_file).write_text('{"ok": 1}')
            switched, info = W.model_switch(tr, model)
            rec = {'label': label, 'model': model, 'session_id': label, 'transcript': str(tr), 'switched': switched,
                   'models': info, 'result': {'is_error': False}}
            W.write_json(Path(log_dir) / f'{label}.json', rec)
            return rec
        S.run_session = run
        return calls

    def step(self):
        out = self.d / 'out' / '1.json'
        out.parent.mkdir(exist_ok=True)
        check = lambda f: (Path(f).exists(), 'ok' if Path(f).exists() else 'missing')
        return S.step(lambda m: 'p', self.d, out, self.d / 'logs', '1', check, pmid='1'), out

    def test_detect(self):
        tr = fake_transcript(self.d / 't.jsonl', [('Read', {}, W.MODEL), ('Read', {}, 'claude-opus-5')], extra=[FALLBACK])
        sw, info = W.model_switch(tr, W.MODEL)
        self.assertTrue(sw)
        self.assertEqual(info['sequence'], 'claude-opus-5-5>claude-opus-5')
        self.assertFalse(W.model_switch(fake_transcript(self.d / 'u.jsonl', [('Read', {}, W.RETRY_MODEL)]),
                                        W.RETRY_MODEL)[0])  # the logged retry on its own model

    def test_second_try_ok(self):
        calls = self.fake([(True, True), (False, True)])
        res, out = self.step()
        self.assertTrue(res['ok'])
        self.assertEqual([c[0] for c in calls], ['1.a1', '1.a1b'])
        self.assertTrue((self.d / 'logs' / '1.a1.1.json').exists())  # the switched try's file kept aside
        self.assertEqual(W.read_switches(self.d / 'logs')['1']['outcome'], 'second_try_ok')

    def test_twice_excluded(self):
        calls = self.fake([(True, True), (True, True)])
        res, out = self.step()
        self.assertFalse(res['ok'])
        self.assertTrue(res['excluded'])
        self.assertFalse(out.exists())  # nothing scored
        self.assertEqual([c[0] for c in calls], ['1.a1', '1.a1b'])  # no Sonnet retry after a second switch
        self.assertEqual(W.switch_excluded(self.d / 'logs'), {'1': ['1']})
        self.assertEqual(S.excluded_steps(self.d / 'logs'), {'1'})

    def test_failure_retry_unchanged(self):
        calls = self.fake([(False, False), (False, True)])
        res, out = self.step()
        self.assertTrue(res['ok'])
        self.assertEqual(calls, [('1.a1', W.MODEL), ('1.a2', W.RETRY_MODEL)])
        self.assertEqual(W.read_switches(self.d / 'logs'), {})

    def one(self, plan_refused):
        """plan_refused: per session, True = the safety filter stops it; False = it writes a valid output."""
        calls = []

        def run(prompt, cwd, model, out_file, log_dir, label, *a, **k):
            ref = plan_refused[len(calls)]
            calls.append((label, model))
            tr = fake_transcript(self.d / f'{label}.jsonl', [('Read', {'file_path': '/x'}, model)], model=model)
            if not ref:
                Path(out_file).write_text('{"ok": 1}')
            switched, info = W.model_switch(tr, model)
            rec = {'label': label, 'model': model, 'session_id': label, 'transcript': str(tr), 'switched': switched, 'models': info,
                   'result': {'is_error': ref, 'stop_reason': 'refusal' if ref else 'end_turn', 'result': 'flagged' if ref else ''}}
            W.write_json(Path(log_dir) / f'{label}.json', rec)
            return rec
        S.run_session = run
        return calls

    def one_step(self, **k):
        out = self.d / 'out' / '1.json'
        out.parent.mkdir(exist_ok=True)
        (self.d / 'logs').mkdir(exist_ok=True)
        check = lambda f: (Path(f).exists(), 'ok' if Path(f).exists() else 'missing')
        lanes = S.Lanes(1)
        return S.step(lambda m: 'p', self.d, out, self.d / 'logs', '1', check, pmid='1', one_model=True, lanes=lanes, **k), out, lanes

    def test_one_model_refusal_is_not_sent_again(self):
        calls = self.one([True])
        res, out, lanes = self.one_step()
        self.assertFalse(res['ok'])
        self.assertTrue(res['refused'])
        self.assertEqual(calls, [('1.a1', W.MODEL)])
        self.assertEqual(S.refused_steps(self.d / 'logs'), {'1'})
        self.assertEqual(lanes.dead, 0)  # a refusal is not the usage limit

    def test_refusal_tries(self):
        d = self.d / 'adjudication_rand'
        d.mkdir()
        rec = {'label': 'p.c01.j2.a1', 'result': {'result': 'flagged'}}
        S.record_refusal(d, 'p.c01.j2', 'p', rec)
        self.assertEqual(S.refused_steps(d), set())  # one more try on the same model
        S.record_refusal(d, 'p.c01.j2', 'p', rec)
        self.assertEqual(S.refused_steps(d), {'p.c01.j2'})
        e = self.d / 'A0-rand'
        e.mkdir()
        S.record_refusal(e, 'p', 'p', rec)
        self.assertEqual(S.refused_steps(e), {'p'})  # plain reads: one try

    def test_one_model_failure_retries_on_the_same_model(self):
        calls = self.fake([(False, False), (False, True)])
        out = self.d / 'out' / '1.json'
        out.parent.mkdir(exist_ok=True)
        check = lambda f: (Path(f).exists(), 'ok' if Path(f).exists() else 'missing')
        res = S.step(lambda m: 'p', self.d, out, self.d / 'logs', '1', check, pmid='1', one_model=True)
        self.assertTrue(res['ok'])
        self.assertEqual(calls, [('1.a1', W.MODEL), ('1.a2', W.MODEL)])

    def test_a_redo_does_not_start_on_the_old_output(self):
        self.fake([(False, False), (False, False)])
        out = self.d / 'out' / '1.json'
        out.parent.mkdir(exist_ok=True)
        (self.d / 'logs').mkdir(exist_ok=True)
        out.write_text('{"old": 1}')
        check = lambda f: (Path(f).exists(), 'ok' if Path(f).exists() else 'missing')
        res = S.step(lambda m: 'p', self.d, out, self.d / 'logs', '1', check, pmid='1')
        self.assertFalse(res['ok'])  # a session that writes nothing cannot pass on the old file
        self.assertFalse(out.exists())
        self.assertEqual(len(list((self.d / 'logs').glob('1.before.*.1.json'))), 1)

    def test_scorer_leaves_it_out(self):
        ev = self.d / 'ev'
        f = W.out_file(ev, 'A0', 1, None, '7')
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({'pmid': '7', 'model': W.MODEL, 'note': '', 'rows': []}))
        W.write_json(W.eval_paths(ev)['logs'] / 'A0-r1' / W.MODEL_SWITCH_FILE, {'7': {'pmid': '7', 'outcome': 'excluded'}})
        rows, status = SC.load_rows(ev, 'A0', 1, ['7'])
        self.assertEqual(status, {'7': 'model_switch'})

    def test_a6_redo_rows(self):
        ev = self.d / 'ev'
        P = W.eval_paths(ev)
        d = P['runs'] / 'A6-r1'
        for folder, rows, st in ((d, [{'pmid': '1', 'v': 'main'}, {'pmid': '2', 'v': 'main'}], ('done', 'done', 'done')),
                                 (d / 'redo', [{'pmid': '2', 'v': 'redo'}], ('reading', 'done', 'reading'))):
            folder.mkdir(parents=True)
            (folder / 'catalog.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
            W.write_tsv(folder / 'papers.tsv', [{'pmid': p, 'status': s} for p, s in zip(('1', '2', '3'), st)],
                        ['pmid', 'status'])
        W.write_json(d / 'redo' / 'RESET.json', {'pmids': ['2', '3']})
        W.write_json(P['logs'] / 'A6-r1' / W.MODEL_SWITCH_FILE, {'2': {'pmid': '2', 'outcome': 'second_try_ok'},
                                                                 '3': {'pmid': '3', 'outcome': 'excluded'}})
        rows, status = SC.load_rows(ev, 'A6', 1, ['1', '2', '3'])
        self.assertEqual(status, {'1': 'ok', '2': 'ok', '3': 'model_switch'})
        self.assertEqual(sorted((r['pmid'], r['v']) for r in rows), [('1', 'main'), ('2', 'redo')])

    def test_a6_record_models(self):
        import run_a6 as RA6
        log = self.d / 'logs'
        log.mkdir()
        rows = [{'pmid': '1', 'label': 'read:1', 'switched': True, 'sequence': 'claude-opus-5-5>claude-opus-5'},
                {'pmid': '2', 'label': 'read:2', 'switched': False, 'sequence': W.MODEL}]
        d = RA6.record_models(log, 'main', ['1', '2'], rows)
        self.assertEqual(d['1']['outcome'], 'redo_pending')
        self.assertNotIn('2', d)
        d = RA6.record_models(log, 'redo', ['1'], [{'pmid': '1', 'label': 'read:1', 'switched': True, 'sequence': 'x>y'}])
        self.assertEqual(d['1']['outcome'], 'excluded')
        self.assertEqual(d['1']['history'][0]['outcome'], 'redo_pending')


class Isolation(unittest.TestCase):
    """REVIEW.md 1.2-1.6 and 1.9: environment, deny rules, session folders, scratch collection, catlog-copy settings."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ev = self.ev = Path(self.tmp.name) / 'kinetics-reading'
        P = W.eval_paths(ev)
        self.P = P
        for d in (P['plain'] / '123', P['adj'] / '123', W.out_dir(ev, 'A0-r1'), W.out_dir(ev, 'A2-r1-readA'),
                  W.out_dir(ev, 'A2-r1-readB'), P['claims'], P['verdicts']['j1'], W.eval_paths(ev, 'pilot')['claims'],
                  P['records'] / 'score_pilot' / 'private', P['records'] / 'dry_run_1' / 'runs', P['keys'], P['logs'],
                  P['a6']):
            d.mkdir(parents=True, exist_ok=True)
        for n in ('paper.txt', 'source.pdf'):
            (P['plain'] / '123' / n).write_text('x')
            (P['adj'] / '123' / n).write_text('x')
        (ev / 'README.md').write_text('about the experiment')

    def tearDown(self):
        for d in (self.P['plain'] / '123', self.P['adj'] / '123'):
            if d.exists():
                os.chmod(d, 0o755)
        self.tmp.cleanup()

    def test_env(self):
        env = S.clean_env()
        self.assertEqual(env['CLAUDE_CODE_DISABLE_CLAUDE_MDS'], '1')
        self.assertEqual(env['ENABLE_CLAUDEAI_MCP_SERVERS'], 'false')
        deny = S.command(W.MODEL, 'u', [], [])[S.command(W.MODEL, 'u', [], []).index('--disallowedTools') + 1].split()
        self.assertIn('Agent', deny)
        self.assertIn('Task', deny)

    def test_plain_deny(self):
        ev, P = self.ev, self.P
        own, other = W.out_dir(ev, 'A2-r1-readA'), W.out_dir(ev, 'A2-r1-readB')
        rules = set(RP.plain_deny(ev, own, W.code('A2-r1-readA')))
        for want in (f"Read(/{P['records']}/**)", f"Read(/{P['a6']}/**)", f"Read(/{P['adj']}/**)", f"Read(/{P['repo']}/**)",
                     f'Read(/{ev}/README.md)', f'Read(/{other}/**)', f"Read(/{W.out_dir(ev, 'A0-r1')}/**)",
                     f"Read(/{P['claims']}/**)", f"Read(//private/tmp/{W.code('A2-r1-readB')}-*)",
                     f"Read(//tmp/{W.code('A0-r2')}-*)", f"Read(//private/tmp/{W.code('adj-j1')}-*)",
                     'Read(//private/tmp/read-*)', f'Read(/{W.PROJECTS}/-Users-<user>-Documents-catlog-*/**)',
                     f'Read(/{W.CLAUDE_TMP}/-Users-<user>-Documents-catlog-*/**)', f'Read(/{Path.home()}/.codex/**)',
                     f'Read(/{W.MAIN}/**)'):
            self.assertIn(want, rules)
        for never in (f"Read(/{P['plain']}/**)", f'Read(/{own}/**)', f"Read(//private/tmp/{W.code('A2-r1-readA')}-*)",
                      f"Read(/{P['out']}/**)"):
            self.assertNotIn(never, rules)
        rec = set(RP.plain_deny(ev, W.out_dir(ev, 'A2-r1-final'), W.code('A2-r1-final'), also_readable=[own, other]))
        self.assertNotIn(f'Read(/{other}/**)', rec)
        self.assertIn(f"Read(//private/tmp/{W.code('A2-r1-readB')}-*)", rec)  # its reads' files yes, their scratch no
        dl = f'Read(/{Path.home()}/Downloads/**)'
        self.assertNotIn(dl, rules)  # a finished run's list is as it was
        self.assertEqual(RP.plain_deny(ev, own, 'x', run='locked'), RP.plain_deny(ev, own, 'x') + [dl])

    def test_adj_deny(self):
        import run_adjudicate as RA
        ev, P = self.ev, self.P
        run = f"{W.code('adj-j1')}-c01"
        rules = set(RA.adj_deny(ev, P['verdicts']['j1'], 'rounds', run))
        for want in (f"Read(/{P['records']}/**)", f"Read(/{P['plain']}/**)", f"Read(/{W.out_dir(ev, 'A0-r1')}/**)",
                     f"Read(/{P['verdicts']['j2']}/**)", f"Read(/{W.eval_paths(ev, 'pilot')['claims']}/**)",
                     f"Read(//private/tmp/{W.code('A0-r1')}-*)", f"Read(//private/tmp/{W.code('adj-j2')}-*)"):
            self.assertIn(want, rules)
        for never in (f"Read(/{P['adj']}/**)", f"Read(/{P['claims']}/**)", f"Read(/{P['verdicts']['j1']}/**)",
                      f"Read(//private/tmp/{W.code('adj-j1')}-*)", f"Read(/{P['out']}/**)"):
            self.assertNotIn(never, rules)
        Q = W.eval_paths(ev, 'pilot')
        pilot = set(RA.adj_deny(ev, Q['verdicts']['j1'], 'pilot', run))
        self.assertIn(f"Read(/{P['claims']}/**)", pilot)
        self.assertNotIn(f"Read(/{Q['claims']}/**)", pilot)
        self.assertFalse([r for r in rules | pilot if 'Downloads' in r])  # finished judgings' lists as they were

    def test_check_hint_after_a_freeze(self):
        import w1_setup as SU
        m = {'commit12': 'abcdefabcdef'}
        self.assertIn('run setup --move-a6 so', SU.branch_moved(m, '1234567890abcdef'))
        msg = SU.branch_moved({**m, 'freeze': {'kit_commit': 'x'}}, '1234567890abcdef')
        self.assertIn('run w1_setup.py freeze so catlog-copy and the manifest follow', msg)
        self.assertNotIn('move-a6', msg)

    def test_check_reports_the_pin_after_a_freeze(self):
        """After a freeze (the manifest's freeze record: the sets a6-papers lays down) check reports catlog-copy's HEAD or
        MANIFEST.json's a6.pipeline_commit_stamp off the commit the tag names; W1's check, before any freeze, is as it was."""
        import w1_setup as SU
        P = self.P
        a6 = fake_copy(P['a6'])
        head = W.git(a6, 'rev-parse', 'HEAD')
        (P['keys'] / 'people_values.tsv').write_text('pmid\n')
        m = {'a6': {'head': head, 'pipeline_commit_stamp': '0123456789ab'}, 'commit': 'x', 'commit12': 'x', 'inputs': {},
             'keys': {'people_values': {'sha256': W.sha256(P['keys'] / 'people_values.tsv')}}}
        quiet = lambda *a, **k: ([], [])  # noqa: E731  (the checks of what a session is shown, git views and reads)
        saved = (SU.shown_texts, SU.a6_shown_problems, SU.a6_git_problems, SU.a6_read_problems, W.freeze_stamp)
        SU.shown_texts = SU.a6_shown_problems = SU.a6_git_problems = SU.a6_read_problems = quiet
        W.freeze_stamp = lambda repo=None: head[:12]
        self.addCleanup(lambda: [setattr(SU, n, v) for n, v in zip(('shown_texts', 'a6_shown_problems', 'a6_git_problems',
                                                                    'a6_read_problems'), saved[:4])] + [setattr(W, 'freeze_stamp', saved[4])])

        def problems(manifest):
            W.write_json(P['manifest'], manifest)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                SU.cmd_check(self.ev)
            return ' | '.join(json.loads(out.getvalue())['problems'])
        self.assertNotIn('pipeline_commit_stamp', problems(m))  # W1's check: no freeze record, no pin
        got = problems({**m, 'freeze': {'kit_commit': 'x'}})
        self.assertIn(f'MANIFEST.json a6.pipeline_commit_stamp is 0123456789ab, the tag {W.FREEZE_TAG} names {head[:12]}', got)
        self.assertNotIn('catlog-copy is at', got)
        W.freeze_stamp = lambda repo=None: 'fb0cf1758951'
        got = problems({**m, 'a6': {**m['a6'], 'pipeline_commit_stamp': 'fb0cf1758951'}, 'freeze': {'kit_commit': 'x'}})
        self.assertIn(f'catlog-copy is at {head[:12]}, the tag {W.FREEZE_TAG} names fb0cf1758951', got)

    def test_a6_papers_same_inputs(self):
        """a6-papers hard lays nothing down when a paper's text, original or supplement in the main folder is not what
        the plain read's or the judges' folders were given (records/hard_inputs.json, judge_inputs.json)."""
        import w1_setup as SU
        main = Path(self.tmp.name) / 'main'
        (main / 'texts').mkdir(parents=True)
        pdf = main / 'papers' / '77.pdf'
        pdf.parent.mkdir()
        pdf.write_bytes(b'%PDF-1.4 x')
        t = main / 'texts' / '77.txt'
        t.write_text('Table 1 kcat 6\n')
        (main / 'papers.tsv').write_text(f'pmid\tdoi\ttitle\tstatus\ttext_source\n77\t10.1/x\tA paper\ttodo\tlocal:{pdf}\n')
        saved, SU.M = SU.M, main
        self.addCleanup(setattr, SU, 'M', saved)
        pin, W.a6_pin_problems = W.a6_pin_problems, lambda ev, repo=None: []  # no frozen copy here (see the locked case)
        self.addCleanup(setattr, W, 'a6_pin_problems', pin)
        rec = {'text_sha256': W.sha256(t), 'original_sha256': W.sha256(pdf)}
        W.write_json(self.P['records'] / 'hard_inputs.json', {'77': {**rec, 'plain_text_sha256': 'x'}})
        W.write_json(self.P['records'] / 'judge_inputs.json', {'77': rec})
        t.write_text('Table 1 kcat 6\nFIGURE: a caption appended later\n')  # production rebuilt the text since
        with self.assertRaises(SystemExit) as e:
            SU.cmd_a6_papers(self.ev, 'hard', ['77'])
        self.assertIn('77 (hard_inputs: text_sha256)', str(e.exception))
        self.assertIn('77 (judge_inputs: text_sha256)', str(e.exception))
        self.assertFalse((self.P['a6'] / 'texts' / '77.txt').exists())  # nothing laid down
        t.write_text('Table 1 kcat 6\n')
        (main / 'texts' / '77.supp.txt').write_text('Table S1\n')  # a supplement fetched after the folders were built
        with self.assertRaises(SystemExit) as e:
            SU.cmd_a6_papers(self.ev, 'hard', ['77'])
        self.assertIn('77 (hard_inputs: supp_sha256)', str(e.exception))
        self.assertFalse((self.P['orders'] / 'A6-hard.args.json').exists())

    def test_a6_papers_locked_from_the_judges_folders(self):
        """a6-papers locked lays the copy's text, supplement and original down from checks/<PMID>/ (the bytes the input
        records name), whatever production holds by then; only for the first K of the draw with both records; and
        reset-a6's lay-down names the originals it cloned, whatever production's papers.tsv says later."""
        import w1_setup as SU
        P, main = self.P, Path(self.tmp.name) / 'main'
        (main / 'texts').mkdir(parents=True)
        (main / 'papers').mkdir()
        lines, recs = ['pmid\tdoi\ttitle\tstatus\ttext_source'], {}
        for p_, supp in (('71', True), ('72', False)):
            src = main / 'papers' / f'{p_}.jats.xml'
            src.write_text(f'<article>{p_}</article>')
            (main / 'texts' / f'{p_}.txt').write_text(f'GLYPH WARNING: x\n\nTable 1 kcat {p_}\n')
            lines.append(f'{p_}\t10.1/{p_}\tPaper {p_}\ttodo\tjats:{src}')
            d = P['adj'] / p_
            d.mkdir(parents=True)
            for n, b in (('paper.txt', f'GLYPH WARNING: x\n\nTable 1 kcat {p_}\n'), ('source.xml', f'<article>{p_}</article>'),
                         *((('paper.supp.txt', 'Table S1\n'),) if supp else ())):
                (d / n).write_text(b)
            recs[p_] = {'route': 'jats', 'original': str(src), 'source_name': 'source.xml', 'existed': False,
                        'text_sha256': W.sha256(d / 'paper.txt'), 'original_sha256': W.sha256(d / 'source.xml'),
                        **({'supp_sha256': W.sha256(d / 'paper.supp.txt')} if supp else {})}
        (main / 'papers.tsv').write_text('\n'.join(lines) + '\n')
        saved, SU.M = SU.M, main
        self.addCleanup(setattr, SU, 'M', saved)
        W.write_json(P['records'] / 'hard_inputs.json', {p_: {**r, 'plain_text_sha256': 'x'} for p_, r in recs.items()})
        W.write_json(P['records'] / 'judge_inputs.json', {'71': recs['71']})
        (P['orders'] / 'locked_draw.txt').parent.mkdir(parents=True, exist_ok=True)
        (P['orders'] / 'locked_draw.txt').write_text('71\n72\n73\n')
        fake_copy(P['a6'])
        head = W.git(P['a6'], 'rev-parse', 'HEAD')
        saved_stamp = W.freeze_stamp
        W.freeze_stamp = lambda repo=None: head[:12]  # the tag names the copy's snapshot
        self.addCleanup(setattr, W, 'freeze_stamp', saved_stamp)
        W.write_json(P['manifest'], {'a6': {'pipeline_commit_stamp': '0123456789ab'}})  # the manifest moved by a freeze
        with self.assertRaises(SystemExit) as e:  # laid down on the frozen copy only
            SU.cmd_a6_papers(self.ev, 'locked', ['71'])
        self.assertIn('a6.pipeline_commit_stamp is 0123456789ab', str(e.exception))
        W.write_json(P['manifest'], {'a6': {'pipeline_commit_stamp': head[:12]}})
        for pmids, why in ((['72'], "draw papers skipped ['71']"), (['71', '73'], 'skipped'),
                           (['71', '72'], "72 (judge_inputs)")):
            with self.assertRaises(SystemExit) as e:
                SU.cmd_a6_papers(self.ev, 'locked', pmids)
            self.assertIn(why, str(e.exception))
        W.write_json(P['records'] / 'judge_inputs.json', recs)
        W.write_json(P['records'] / 'hard_inputs.json', {**recs, '72': {**recs['72'], 'text_sha256': 'aa'}})
        with self.assertRaises(SystemExit) as e:  # the plain read's folder holds another text than the judges'
            SU.cmd_a6_papers(self.ev, 'locked', ['71', '72'])
        self.assertIn('72 (hard_inputs: text_sha256)', str(e.exception))
        self.assertFalse((P['a6'] / 'texts').exists() or (P['orders'] / 'A6-locked.args.json').exists())  # nothing laid down
        W.write_json(P['records'] / 'hard_inputs.json', recs)
        (main / 'texts' / '71.txt').write_text('GLYPH WARNING: x\n\nTable 1 kcat 71\nFIGURE: a caption added later\n')
        (main / 'texts' / '72.supp.txt').write_text('Table S9\n')  # production's later retext and supplement: no matter
        with contextlib.redirect_stdout(io.StringIO()):
            SU.cmd_a6_papers(self.ev, 'locked', ['71', '72'])
        for p_ in ('71', '72'):
            self.assertEqual((P['a6'] / 'texts' / f'{p_}.txt').read_bytes(), (P['adj'] / p_ / 'paper.txt').read_bytes())
            self.assertEqual((P['a6'] / 'papers' / f'{p_}.jats.xml').read_bytes(), (P['adj'] / p_ / 'source.xml').read_bytes())
        self.assertTrue((P['a6'] / 'texts' / '71.supp.txt').exists() and not (P['a6'] / 'texts' / '72.supp.txt').exists())
        laid = json.loads((P['records'] / 'a6_inputs_locked.json').read_text())['papers']
        self.assertEqual({p_: W.input_hashes(r) for p_, r in laid.items()}, {p_: W.input_hashes(r) for p_, r in recs.items()})
        self.assertEqual(laid['71']['laid_from'], str(P['adj'] / '71'))
        copy = {r['pmid']: r for r in W.read_tsv(P['a6'] / 'papers.tsv')}
        self.assertEqual(copy['71']['text_source'], f"jats:{P['a6'] / 'papers' / '71.jats.xml'}")
        self.assertEqual((copy['71']['status'], copy['71']['title']), ('reading', 'Paper 71'))
        self.assertEqual(W.read_order(self.ev, 'A6-locked'), ['71', '72'])
        moved = {'71': {'pmid': '71', 'doi': '10.1/71', 'title': 'Paper 71, retitled', 'status': 'todo',
                        'text_source': f"pdf:{main / 'papers' / '71.pdf'}"}}  # production filed another original
        rows = SU.later_rows(self.ev, 'locked', moved)
        self.assertEqual((rows['71']['text_source'], rows['71']['title']), (f"jats:{main / 'papers' / '71.jats.xml'}", 'Paper 71'))
        # a paper whose text came with no original (A6-hard's 30232563): laid down again by its recorded route alone,
        # not by a file production filed later, which a6-papers never cloned into the copy
        W.write_json(P['records'] / 'a6_inputs_hard.json', {'papers': {'30': {'route': 'europepmc', 'original': None,
                                                                             'text_sha256': 'aa'}}})
        later = {'30': {'pmid': '30', 'doi': '10.1/30', 'title': 'Paper 30', 'status': 'done',
                        'text_source': f"pdf:{main / 'papers' / '30.pdf'}"}}
        self.assertEqual(SU.later_rows(self.ev, 'hard', later)['30']['text_source'], 'europepmc')

    def test_folders(self):
        d = self.P['plain'] / '123'
        self.assertEqual(W.folder_problems(d), [])
        (d / 'notes.json').write_text('{}')
        self.assertTrue(W.folder_problems(d))
        (d / 'notes.json').unlink()
        (self.ev / 'CLAUDE.md').write_text('instructions')
        self.assertTrue(any('CLAUDE.md' in x for x in W.folder_problems(d)))
        with self.assertRaises(SystemExit):
            S.check_folders([d])

    def test_refuse_eval_words(self):
        old = Path(self.tmp.name) / 'catlog-eval' / 'w1' / 'plain' / '123'
        old.mkdir(parents=True)
        rec = S.run_session('Paper 123 in ' + str(old), old, W.MODEL, old / 'x.json', Path(self.tmp.name) / 'logs', 'x.a1')
        self.assertTrue(rec.get('refused'))
        self.assertTrue(any('evaluation words' in x for x in rec['refused']))

    def test_seal_and_settings(self):
        import w1_setup as SU
        P = self.P
        self.assertEqual(SU.seal(self.ev, True), 2)
        self.assertFalse(os.access(P['plain'] / '123', os.W_OK))
        with self.assertRaises(OSError):
            (P['plain'] / '123' / 'x.txt').write_text('no')
        SU.seal(self.ev, False)
        self.assertTrue(os.access(P['plain'] / '123', os.W_OK))
        deny = set(SU.settings_local(self.ev)['permissions']['deny'])
        for want in (f'Edit(/{W.MAIN}/**)', f'Write(/{W.MAIN}/**)', f"Write(/{P['plain']}/**)", f"Read(/{P['plain']}/**)",
                     f"Read(/{P['records']}/**)", f"Read(/{P['out']}/**)", f'Read(/{self.ev}/*.md)', f'Write(/{self.ev}/*.md)',
                     'mcp__plugin_bio-research_wiley', f'Read(/{W.PROJECTS}/-Users-<user>-Documents-catlog-*/**)'):
            self.assertIn(want, deny)
        (self.ev / 'A6_LAUNCH.md').write_text('x')
        text = json.dumps(SU.settings_local(self.ev))
        self.assertEqual(W.eval_word_hits(text), [], text[:300])  # no rule names an evaluation word
        for never in (f"Read(/{P['a6']}/**)", f"Write(/{P['a6']}/**)"):
            self.assertNotIn(never, deny)
        for t in ('Read', 'Edit', 'Write'):  # the owner's downloads (other groups' answer keys for the held-out papers)
            self.assertIn(f'{t}(/{Path.home()}/Downloads/**)', deny)

    def test_keep_dry(self):
        import w1_setup as SU
        ev, P = self.ev, self.P
        a0 = W.out_dir(ev, 'A0-dry')
        a0.mkdir(parents=True)
        (a0 / '1.json').write_text('{}')
        (P['logs'] / 'A0-dry').mkdir(parents=True)
        keep = W.out_dir(ev, 'A0-r1') / '1.json'
        keep.write_text('{}')
        SU.cmd_keep_dry(ev, 'dry_run_2')
        self.assertTrue((P['records'] / 'dry_run_2' / 'out' / a0.name / '1.json').exists())
        self.assertTrue((P['records'] / 'dry_run_2' / 'records' / 'logs' / 'A0-dry').exists())
        self.assertFalse(a0.exists())
        self.assertTrue(keep.exists())  # a round's output stays
        with self.assertRaises(SystemExit):
            SU.cmd_keep_dry(ev, 'dry_run_2')

    def test_copy_texts(self):
        import w1_setup as SU
        a6 = Path(self.tmp.name) / 'copy'
        a6.mkdir()
        (a6 / 'papers.tsv').write_text('pmid\ttitle\tstatus\tnote\n1\tExperiments on X\treading\t\n')
        (a6 / 'log.tsv').write_text('2026-11-02 10:55\t1\treread\tinterrupted batch\n')
        self.assertEqual([h for _, t in SU.copy_texts(a6) for h in W.eval_word_hits(t)], [])  # a title is not checked
        (a6 / 'log.tsv').write_text('2026-11-02 10:55\t1\tw1_claim\n')
        self.assertTrue(any(W.eval_word_hits(t) for _, t in SU.copy_texts(a6)))

    def test_plain_inputs(self):
        import w1_setup as SU
        main = Path(self.tmp.name) / 'main'
        (main / 'texts').mkdir(parents=True)
        pdf = main / 'papers' / '77.pdf'
        pdf.parent.mkdir()
        pdf.write_bytes(b'%PDF-1.4 x')
        (main / 'texts' / '77.txt').write_text('GLYPH WARNING: symbols\nTable 1 kcat 6 \u00b1 1.5\n')
        (main / 'papers.tsv').write_text('pmid\tdoi\ttitle\tstatus\ttext_source\n'
                                         f'77\t10.1/x\tA paper\tdone\tlocal:{pdf}\n')
        saved, SU.M = SU.M, main
        self.addCleanup(setattr, SU, 'M', saved)
        (self.ev / 'MANIFEST.json').write_text(json.dumps({'inputs': {'123': {}}}))
        (main / 'texts' / '78.txt').write_text('Table 2 Km 3 mM\n')
        with open(main / 'papers.tsv', 'a') as f:
            f.write('78\t10.1/y\tB paper\tdone\teuropepmc\n')
        SU.cmd_plain_inputs(self.ev, ['77', '123', '78'])  # 123 is a set paper: used as it is; 78 has no original
        self.assertTrue((self.P['plain'] / '78' / 'paper.txt').exists())
        self.assertIsNone(json.loads((self.P['records'] / 'hard_inputs.json').read_text())['78']['original'])
        os.chmod(self.P['plain'] / '78', 0o755)
        d = self.P['plain'] / '77'
        self.assertFalse((d / 'paper.txt').read_text().startswith('GLYPH WARNING'))
        self.assertTrue((d / 'source.pdf').exists())
        self.assertFalse(os.access(d, os.W_OK))
        recs = json.loads((self.P['records'] / 'hard_inputs.json').read_text())
        self.assertTrue(recs['77']['glyph_warning'])
        self.assertTrue(recs['123']['existed'])
        self.assertEqual(W.run_label('A0', 'hard'), 'A0-hard')
        self.assertEqual(W.check_run('hard'), 'hard')
        self.assertEqual(W.run_label('A0', 'rand'), 'A0-rand')
        os.chmod(d, 0o755)

    def test_a6_original_name(self):
        import w1_setup as SU
        self.assertEqual(SU.a6_original_name('12499375', '/m/papers/12499375.els.xml'), '12499375.els.xml')
        self.assertEqual(SU.a6_original_name('23934069', '/m/papers/23934069.pdf'), '23934069.pdf')
        self.assertEqual(SU.a6_original_name('10079076', '/r/x/evidence_assets/paper_10079076.pdf'), '10079076.pdf')

    def test_collect_scratch(self):
        root = Path(self.tmp.name) / 'tmp'
        c = W.code('A0-r1')
        (root / f'{c}-123-work').mkdir(parents=True)
        for n in (f'{c}-123-rows.json', f'{c}-123-p-01.png', f'{c}-1234-rows.json', f'{c}-123-work/build.py'):
            (root / n).write_text('x')
        moved, left = S.collect_scratch(f'{c}-123-', Path(self.tmp.name) / 'logs', root)
        self.assertEqual(sorted(moved), [f'{c}-123-rows.json', f'{c}-123-work/build.py'])
        self.assertEqual(left, [f'{c}-123-p-01.png'])
        self.assertTrue((root / f'{c}-1234-rows.json').exists())
        self.assertTrue((Path(self.tmp.name) / 'logs' / f'{c}-123-rows.json').exists())
        (root / 'read-12').mkdir()
        (root / 'read-123').mkdir()
        (root / 'read-12' / 'b.py').write_text('x')
        (root / 'read-123' / 'b.py').write_text('x')
        import re as _re
        rx = _re.compile(r'read-12(?![0-9A-Za-z])')
        moved, _ = S.collect_scratch('read-12', Path(self.tmp.name) / 'a6', root, keep_name=lambda n: bool(rx.match(n)))
        self.assertEqual(moved, ['read-12/b.py'])


class Rand(unittest.TestCase):
    """score_rand.py's own rules, on fake rows."""

    def row(self, **k):
        return {'pmid': '1', 'metric': 'kcat', 'value': 5.0, 'variant': 'wild type', 'substrate': 'D-glucose', 'organism': 'E. coli',
                'cosub': '', 'pH': '7', 'temp': '25', 'enzyme': 'hexokinase', 'raw': '5.0', 'raw_unit': 's-1', 'id': 'a', **k}

    def test_repeats(self):
        a = self.row()
        self.assertTrue(SR.repeats(a, self.row(id='b')))
        self.assertTrue(SR.repeats(a, self.row(id='b', raw='5.0 ± 0.1')))  # a repeat may lose its ±
        self.assertFalse(SR.repeats(self.row(raw='5.0 ± 0.2'), self.row(id='b', raw='5.0 ± 0.1')))
        self.assertFalse(SR.repeats(a, self.row(id='b', substrate='L-glucose')))  # the kit's duplicate key merges these
        self.assertFalse(SR.repeats(a, self.row(id='b', enzyme='pyruvate kinase')))
        self.assertFalse(SR.repeats(self.row(substrate='Abz-A-G-R-G-D-G-Q'), self.row(id='b', substrate='Abz-A-G-R-G-A-G-Q')))

    def test_thin_drops_only_an_unmatched_repeat(self):
        keep, drops = SR.thin([self.row(id='a'), self.row(id='b'), self.row(id='c', value=7.0)], [1, 2])
        self.assertEqual([v['id'] for v in keep], ['a', 'c'])
        self.assertEqual([(t['id'], v['id']) for t, v in drops], [('a', 'b')])

    def test_split_mass(self):
        rows = [{'pmid': '1', 'metric': 'Km', 'unit': 'mg/mL', 'raw_value': '0.82 ± 0.17'}, {'pmid': '1', 'metric': 'Km', 'unit': 'mM', 'raw_value': '3.1'}]
        pv = [{'pmid': '1', 'metric': 'Km', 'raw': '0.82', 'raw_unit': 'mM'}, {'pmid': '1', 'metric': 'Km', 'raw': '2', 'raw_unit': 'mg ml-1'},
              {'pmid': '1', 'metric': 'Km', 'raw': '3.1', 'raw_unit': 'mM'}, {'pmid': '1', 'metric': 'kcat', 'raw': '0.82', 'raw_unit': 's-1'}]
        keep, out = SR.split_mass(pv, rows)
        self.assertEqual([v['raw'] for v in out], ['0.82', '2'])
        self.assertEqual([v['raw'] for v in keep], ['3.1', '0.82'])
        stay = [{'pmid': '1', 'metric': 'kcat/Km', 'raw': '9', 'raw_unit': 'µmol min^-1 mg^-1 mM^-1'},
                {'pmid': '1', 'metric': 'kcat/Km', 'raw': '8', 'raw_unit': 'U mg^-1 mM^-1'},
                {'pmid': '1', 'metric': 'Km', 'raw': '7', 'raw_unit': 'mM (assay with 1 mg/ml BSA)'}]
        self.assertEqual(len(SR.split_mass(stay, rows)[0]), 3)  # per mg of enzyme or a molar unit: no concentration by mass

    def test_exact(self):
        self.assertEqual(SR.exact(0, 0), (None, None))
        lo, hi = SR.exact(0, 150)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.0243, places=3)
        self.assertLess(SR.exact(0, 750)[1], 0.005)


class RandFull(unittest.TestCase):
    """score_randfull.py: the record's details, the claims as a judge sees them, the judges' folders and closed doors."""

    def test_details(self):
        rows = {'r1': {'location': 'Table 1', 'construct': 'G105C labeled with MTSL, printed as G105R1',
                       'conditions': '50 mM Hepes', 'metric_note': 'apparent'}}
        self.assertEqual(SRF.details('catlog', {'id': 'r1', 'where': 'Table 1'}, rows),
                         'Table 1; G105C labeled with MTSL, printed as G105R1; 50 mM Hepes; apparent')
        self.assertEqual(SRF.details('plain', {'id': 'A0-rand:1:0', 'where': 'Table 2 row 3', 'conditions': ' pH 7,  25 C '}, rows),
                         'Table 2 row 3; pH 7, 25 C')
        self.assertEqual(SRF.details('plain', {'id': 'x', 'where': 'Table 2', 'conditions': 'table 2'}, rows), 'Table 2')
        self.assertEqual(SRF.details('plain', {'id': 'x', 'where': None, 'conditions': ['pH 7', None, 'null']}, rows), 'pH 7')
        self.assertEqual(SRF.details('plain', {'id': 'x', 'where': 'None', 'conditions': {'a': 1}}, rows), '')
        self.assertEqual(SRF.src_of('A0-rand:123:4'), 'plain')
        self.assertEqual(SRF.src_of('00110d0c11e09a85'), 'catlog')

    def test_triage_on_a_fake_first_judging(self):
        base = {'metric': 'kcat', 'raw': '5', 'raw_unit': 's-1', 'enzyme': 'hexokinase', 'organism': 'E. coli',
                'variant': 'wild type', 'substrate': 'D-glucose', 'cosub': '', 'pH': '7', 'temp': '25'}
        cat = [{**base, 'id': 'c1', 'pmid': '11', 'value': 5.0, 'where': 'Table 1', 'conditions': 'standard'},
               {**base, 'id': 'c2', 'pmid': '11', 'value': 9.0, 'where': 'Table 1', 'conditions': '80 mM NaCl'},
               {**base, 'id': 'c3', 'pmid': '12', 'value': 2.0, 'where': 'Table 2', 'conditions': ''}]
        plain = [{**base, 'id': 'A0-rand:11:0', 'pmid': '11', 'value': 5.0, 'where': 'Table 1', 'conditions': 'standard'},
                 {**base, 'id': 'A0-rand:11:1', 'pmid': '11', 'value': 9.0, 'where': 'Table 1', 'conditions': 'salt'},
                 {**base, 'id': 'A0-rand:12:0', 'pmid': '12', 'value': 2.0, 'where': 'Table 2', 'conditions': 'x'},
                 {**base, 'id': 'A0-rand:12:1', 'pmid': '12', 'value': 70.0, 'where': 'Table 3', 'conditions': 'from ref 4'}]
        vals = {'plain': plain, 'catlog': cat, 'papers': ['11', '12'],
                'pairs': [['c1', 'A0-rand:11:0', ''], ['c2', 'A0-rand:11:1', ''], ['c3', 'A0-rand:12:0', '']]}
        rows = {'c1': {'location': 'Table 1', 'conditions': 'standard'}, 'c2': {'location': 'Table 1', 'construct': 'His-tagged',
                'conditions': '80 mM NaCl'}, 'c3': {'location': 'Table 2'}}
        cmap = [{'claim_id': 'k1', 'chunk': 'c01', 'pmid': '11', 'metric': 'kcat', 'kind': 'matched_sample', 'source_shown': 'both',
                 'decoy': '', 'members': [{'src': 'catlog', 'id': 'c2', 'value': 9.0}, {'src': 'plain', 'id': 'A0-rand:11:1', 'value': 9.0}]},
                {'claim_id': 'k2', 'chunk': 'c01', 'pmid': '12', 'metric': 'kcat', 'kind': 'unmatched', 'source_shown': 'plain',
                 'decoy': '', 'members': [{'src': 'plain', 'id': 'A0-rand:12:1', 'value': 70.0}]},
                {'claim_id': 'k3', 'chunk': 'c01', 'pmid': '12', 'metric': 'kcat', 'kind': 'matched_sample', 'source_shown': 'catlog',
                 'decoy': '', 'partner': ['plain', 'A0-rand:12:0'], 'members': [{'src': 'catlog', 'id': 'c3', 'value': 2.0}]},
                {'claim_id': 'k4', 'chunk': 'c01', 'pmid': '12', 'metric': 'kcat', 'kind': 'decoy', 'source_shown': 'decoy',
                 'decoy': 'x60', 'members': [{'src': 'decoy', 'id': 'decoy0:12', 'value': 120.0}]}]
        V = {'k1': {'j1': 'wrong_number', 'j2': 'wrong_number'}, 'k2': {'j1': 'not_measured_here', 'j2': 'supported',
             'j3': 'not_measured_here'}, 'k3': {'j1': 'supported', 'j2': 'supported'}}
        final = {'k1': 'wrong_number', 'k2': 'not_measured_here', 'k3': 'supported', 'k4': 'wrong_scale'}
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d)
            pr = SR.paths(ev, 'rand')
            (pr['score'] / 'private').mkdir(parents=True)
            (pr['score'] / 'private' / 'values.json').write_text(json.dumps(vals))
            for p_ in ('11', '12'):
                (ev / 'checks' / p_).mkdir(parents=True)
                (ev / 'checks' / p_ / 'paper.txt').write_text('text ' + p_)
            saved = SRF.first_round
            SRF.first_round = lambda e: (pr, cmap, vals, {'papers_listed': 2}, rows, V, final)
            self.addCleanup(setattr, SRF, 'first_round', saved)
            SRF.triage(ev, type('A', (), {'dry': False})())
            P = SR.paths(ev, 'randfull')
            self.assertEqual(P['adj'].name, 'folios')
            for r in W.JUDGES:  # each judge role its own folders, cloned
                for p_ in ('11', '12'):
                    self.assertEqual((P['adj'] / W.code(W.judge_label(r, 'randfull')) / p_ / 'paper.txt').read_text(), 'text ' + p_)
            claims = [c for f in sorted(P['claims'].glob('*.json')) for c in json.loads(f.read_text())]
            keys = set(SC.shown(cat[0])) | {'id', 'details'}
            for c in claims:
                self.assertEqual(set(c), keys)  # nothing names a source, a first verdict or a decoy
                self.assertTrue(c['details'])
            cm = [json.loads(line) for line in open(P['score'] / 'private' / 'claims_map.jsonl')]
            real = [c for c in cm if not c['decoy']]
            self.assertEqual(sorted((c['source_shown'], c['members'][0]['id']) for c in real),  # every first value, once,
                             [('catlog', 'c2'), ('catlog', 'c3'), ('plain', 'A0-rand:11:1'), ('plain', 'A0-rand:12:1')])  # k1 split
            k1 = [c for c in real if c['first_claim'] == 'k1']
            self.assertEqual(sorted(tuple(c['partner']) for c in k1), [('catlog', 'c2'), ('plain', 'A0-rand:11:1')])
            self.assertEqual({c['first_claim']: c['first_decision'] for c in real}['k2'], 'third judge')
            dec = [c for c in cm if c['decoy']]
            self.assertTrue(dec and all(c['decoy'] in ('x1000', 'x60') and c['shown']['details'] for c in dec))
            self.assertFalse(any(c['twin_visible'] for c in dec))  # bases: agreeing values no claim shows (c1, A0-rand:12:0 ...)
            shown_vals = {(c['shown']['metric'], c['shown']['value'], c['shown']['details']) for c in real}
            for c in dec:  # no decoy has a claim of the same details whose value it is 1000- or 60-fold of
                for m, v, dt in shown_vals:
                    if dt == c['shown']['details'] and m == c['shown']['metric']:
                        self.assertFalse(any(abs(c['shown']['value'] - v * f) < 1e-6 * max(1, v * f) for f in (1000, 1e-3, 60, 1 / 60)))
            self.assertTrue((P['score'] / 'private' / 'values.json').exists() and (P['score'] / 'private' / 'order.txt').exists())
            with self.assertRaises(SystemExit):  # drawn once
                SRF.triage(ev, type('A', (), {'dry': False})())

    def test_closed_doors_and_own_scratch(self):
        """A randfull judge cannot read the first judges' sessions or the other judges' transcripts, nor the first judges'
        folders, and its scratch code is its own."""
        import run_adjudicate as RA
        ev = W.EVAL
        P = W.eval_paths(ev, 'randfull')
        rules = RA.adj_deny(ev, P['verdicts']['j1'], 'randfull', 'xx-c01', P['claims'], 'j1')
        first = W.project_slug(W.eval_paths(ev)['adj']) + '-*'
        self.assertIn(f'Read(/{W.PROJECTS}/{first}/**)', rules)
        fam = lambda r: W.project_slug(P['adj'] / W.code(W.judge_label(r, 'randfull'))) + '-*'  # noqa: E731
        self.assertIn(f"Read(/{W.PROJECTS}/{fam('j1')}/*.jsonl)", rules)  # its own role's other transcripts
        for r in ('j2', 'j3'):  # the other roles' sessions, whole
            self.assertIn(f"Read(/{W.PROJECTS}/{fam(r)}/**)", rules)
            self.assertIn(f"Read(/{W.CLAUDE_TMP}/{fam(r)}/**)", rules)
        self.assertNotIn(f"Read(/{W.PROJECTS}/{fam('j1')}/**)", rules)  # its own saved tool results stay readable
        self.assertIn(f"Read(/{W.eval_paths(ev)['adj']}/**)", rules)  # checks/ itself
        self.assertNotEqual(W.code(W.judge_label('j1', 'randfull')), W.code(W.judge_label('j1')))
        self.assertIn(W.code(W.judge_label('j3', 'randfull')), W.scratch_labels())

STAMP = {'read_by': 'reader', 'reader_model': W.MODEL, 'verifier_model': W.MODEL, 'pipeline_commit': 'abcdef123456',
         'read_prompt': '86e5d7668c1c', 'verify_prompt': '6cdd7782a0f2'}
STAMPS = {'a6': {'pipeline_commit_stamp': 'abcdef123456'},
          'prompt_hashes_stamp_style': {'read.md': '86e5d7668c1c', 'verify.md': '6cdd7782a0f2'}}


def agent(label, seq=None, events=(), refusals=0):
    """An agent row of run_a6.py's agents.json ('read:11', 'verify-sonnet:12', ...): it ran on the model it was started
    with unless seq says otherwise ('' for an agent that never produced a message)."""
    launched = W.RETRY_MODEL if 'sonnet' in label else W.MODEL
    return {'label': label, 'pmid': label.split(':')[1], 'role': label.split(':')[0].split('-')[0], 'launched': launched,
            'sequence': launched if seq is None else seq, 'events': list(events), 'refusals': refusals, 'switched': False,
            'transcript': ''}


LAUNCH_ROW = {'label': 'launch', 'pmid': '', 'role': 'launch', 'launched': W.MODEL, 'sequence': W.MODEL, 'events': []}


def audit_row(label, launch='main', broken=False, violations=()):
    """An agent row of w1_audit.py's audit.json ('read:11', 'launch:main', ...)."""
    pmid = '' if label.startswith('launch') else label.split(':')[1]
    return {'label': label, 'pmid': pmid, 'role': 'launch' if not pmid else label.split(':')[0].split('-')[0],
            'launch': launch, 'broken': broken, 'violations': [list(v) for v in violations]}


# how an agent's transcript ends in A6-hard (metadata, review of round 3): the usage limit and a refusal both end with a
# '<synthetic>' API error message, of stop_reason 'stop_sequence' (error rate_limit) or 'refusal' (invalid_request)
LIMIT_END = {'type': 'assistant', 'isApiErrorMessage': True, 'error': 'rate_limit',
             'message': {'model': '<synthetic>', 'role': 'assistant', 'stop_reason': 'stop_sequence',
                         'content': [{'type': 'text', 'text': '...'}]}}
REFUSAL_END = {**LIMIT_END, 'error': 'invalid_request', 'message': {**LIMIT_END['message'], 'stop_reason': 'refusal'}}


def agent_transcript(path, task, model=W.MODEL, refusals=0, end=None):
    """An A6 agent's transcript: its task; `refusals` responses ended with stop_reason 'refusal' that it got past (on
    `model`, every other one a '<synthetic>' API error as Claude Code writes them, each followed by a tool call of its
    own); then `end` (LIMIT_END, REFUSAL_END; None: it ends with its last tool call). With no refusal and LIMIT_END it
    shows no message of a model: it died at once, at the limit."""
    lines = [{'type': 'user', 'message': {'role': 'user', 'content': task}}]
    for i in range(refusals):
        lines.append({'type': 'assistant', 'message': {'model': model, 'stop_reason': 'refusal', 'content': []}}
                     if i % 2 == 0 else REFUSAL_END)
        lines.append({'type': 'assistant', 'message': {'model': model, 'stop_reason': 'tool_use',
                                                       'content': [{'type': 'tool_use', 'name': 'Read', 'input': {}}]}})
    if end:
        lines.append(end)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(''.join(json.dumps(x) + '\n' for x in lines))
    return Path(path)


def fake_session(projects, a6, sid, agents):
    """Claude Code's transcripts of an A6 launch session under projects/: the session's own and one per (label, model)."""
    base = Path(projects) / W.project_slug(a6)
    sub = base / sid / 'subagents' / 'workflows' / 'wf_1'
    sub.mkdir(parents=True)
    for i, (desc, model) in enumerate(agents):
        role, p = desc.split(':')[0].split('-')[0], desc.split(':')[1]
        fake_transcript(sub / f'agent-a{i}.jsonl', [('Read', {}, model)],
                        task=f"Follow {a6}/prompts/{'verify' if role == 'verify' else 'read'}.md for PMID {p}. The paper ...")
        (sub / f'agent-a{i}.meta.json').write_text(json.dumps({'description': desc}))
    return fake_transcript(base / f'{sid}.jsonl', [('Bash', {}, W.MODEL)])


def ee_row(pmid, substrate, mutant='WT', kcat='', km='', kcat_km='', enzyme='lipase'):
    """A row of a fake EnzyExtract manual curation (EE_COLS), at 25 °C and pH 7.5 as row() is."""
    return {'pmid': pmid, 'enzyme': enzyme, 'enzyme_full': '', 'organism': 'B. subtilis', 'substrate': substrate,
            'substrate_full': '', 'mutant': mutant, 'temperature': '25', 'pH': '7.5', 'src': 'Table 1', 'descriptor': '',
            'kcat': kcat, 'km': km, 'kcat_km': kcat_km}


def fake_curation(case, ev, rows, sets):
    """A fake curation for score_locked: its file in records/keys/ with the head-to-head's sha256 set to the fake file's
    own, and the held-out gold-set lookup (holdout_374.tsv) replaced by sets; all restored after the test. No real key
    or paper list is read."""
    f = W.eval_paths(ev)['keys'] / h2h.GOLD_NAMES['ee_manual']
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, 'w', newline='') as fh:
        w = csv.DictWriter(fh, EE_COLS)
        w.writeheader()
        w.writerows(rows)
    case.addCleanup(h2h.GOLD_SHA256.__setitem__, 'ee_manual', h2h.GOLD_SHA256['ee_manual'])
    h2h.GOLD_SHA256['ee_manual'] = W.sha256(f)
    for name in ('GOLD_CSV', 'EE_MANUAL'):  # h2h.use_keys points the loaders at the fake keys
        case.addCleanup(setattr, h2h.C, name, getattr(h2h.C, name))
    case.addCleanup(setattr, SL, 'holdout_gold_sets', SL.holdout_gold_sets)
    SL.holdout_gold_sets = lambda: dict(sets)
    return f


def committed(case, when='2000-01-01T00:00:00+00:00'):
    """score_locked.code_history replaced for one test: one commit of score_locked.py as it is now, at `when` (by default
    before any triage), so report's check of the pre-registration's condition reads no real git history."""
    case.addCleanup(setattr, SL, 'code_history', SL.code_history)
    SL.code_history = lambda: ('h' * 40, [('c' * 40, when, Path(SL.__file__).read_text())])


class Locked(unittest.TestCase):
    """score_locked.py: the locked set's triage and report on a fake tree (the plain reads, the copy's kept run and its
    launch records, the audits, the input records, the manifest's stamps), the checks that refuse or stop it, and the
    judges' closed doors."""

    def tree(self):
        """Draw 11-15, 11-14 laid down for both sides: 11 and 12 read by both, 13 left reading in the copy, 14 stored
        nothing in the copy (no agreeing pair: its decoys come from its own claims)."""
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        saved = W.freeze_stamp  # the tag's commit, as the fake stamps name it
        W.freeze_stamp = lambda repo=None: STAMPS['a6']['pipeline_commit_stamp']
        self.addCleanup(setattr, W, 'freeze_stamp', saved)
        ev = Path(d.name)
        P = W.eval_paths(ev)
        P['orders'].mkdir(parents=True)
        (P['orders'] / 'locked_draw.txt').write_text('11\n12\n13\n14\n15\n')
        (P['orders'] / 'A6-locked.txt').write_text('11\n12\n13\n14\n')
        run = P['runs'] / 'A6-locked'
        run.mkdir(parents=True)
        W.write_json(run / 'RESET.json', {'reset_utc': '2026-11-10T12:00:00.000Z'})
        W.write_tsv(run / 'papers.tsv', [{'pmid': '11', 'status': 'done'}, {'pmid': '12', 'status': 'done'},
                                         {'pmid': '13', 'status': 'reading'}, {'pmid': '14', 'status': 'done'}], ['pmid', 'status'])
        cat = [{**row('kcat', 5), 'pmid': '11', 'row_id': 'r1', 'construct': 'His-tagged', **STAMP},
               {**row('Km', 0.5), 'pmid': '11', 'row_id': 'r2', 'metric_note': 'apparent', **STAMP},
               {**row('kcat', 2), 'pmid': '12', 'row_id': 'r3', **STAMP}, {**row('kcat', 1), 'pmid': '13', 'row_id': 'r4', **STAMP}]
        (run / 'catalog.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in cat))
        main = P['logs'] / 'A6-locked' / 'main'
        main.mkdir(parents=True)
        W.write_json(main / 'launch.json', {'launch': 'main', 'pmids': ['11', '12', '13', '14']})
        W.write_json(main / 'agents.json', [agent(f'{r}:{p_}') for p_ in ('11', '12', '14') for r in ('read', 'verify')]
                     + [agent('read:13'), LAUNCH_ROW])
        for a in ('A6-locked', 'A0-locked'):
            (P['audit'] / a).mkdir(parents=True)
            (P['audit'] / a / 'rerun.txt').write_text('')
            W.write_json(P['audit'] / a / 'content_scan.json', {'time': '2026-11-10 07:30:00 -0600', 'run': a,
                                                                'sessions_scanned': 4, 'hits': []})  # after both audits
        W.write_json(P['audit'] / 'A6-locked' / 'audit.json', {'summary': {'time': '2026-11-10 07:00:00 -0600'}, 'agents': [
            audit_row('launch:main')] + [audit_row(f'{r}:{p_}') for p_ in ('11', '12', '14') for r in ('read', 'verify')]
            + [audit_row('read:13')]})
        W.write_json(P['audit'] / 'A0-locked' / 'audit.json', {'summary': {'time': '2026-11-10 07:00:00 -0600'}, 'agents': []})
        plain = {'11': [row('kcat', 5), row('Km', 0.5), row('kcat', 99, substrate='GTP')],
                 '12': [row('kcat', 2), row('kcat', 70, substrate='GTP')], '13': [row('kcat', 1)],
                 '14': [row('kcat', 3, substrate='UTP'), row('Km', 0.2, substrate='UTP')]}
        for p_, rows in plain.items():
            f = W.out_file(ev, 'A0', 'locked', None, p_)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps({'pmid': p_, 'model': W.MODEL, 'note': '', 'rows': rows}))
            (P['adj'] / p_).mkdir(parents=True)
            (P['adj'] / p_ / 'paper.txt').write_text('text ' + p_)
        rec = {'text_sha256': 'aa', 'original_sha256': 'bb'}  # the same text and original on every side, no supplement
        W.write_json(P['records'] / 'a6_inputs_locked.json', {'papers': {p_: {**rec, 'route': 'pmc'} for p_ in plain}})
        for name in ('hard_inputs', 'judge_inputs'):
            W.write_json(P['records'] / f'{name}.json', {p_: {**rec, 'existed': False} for p_ in plain})
        W.write_json(P['manifest'], STAMPS)
        lg = P['logs'] / 'A0-locked'
        lg.mkdir(parents=True)
        W.write_tsv(lg / 'sessions.tsv', [{'pmid': p_, 'model': W.MODEL, 'ok': 'True', 'label': f'{p_}.a1'}
                                          for p_ in plain], ['pmid', 'model', 'ok', 'label'])
        return ev, P, cat

    def summary(self, ev):
        """triage --dry's summary (stdout), the stop reasons on stderr kept apart."""
        import contextlib, io
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            SL.triage(ev, type('A', (), {'dry': True, 'short': True, 'accept_left_out': False})())
        return json.loads(out.getvalue())

    def test_triage_and_report_on_a_fake_tree(self):
        ev, P, cat = self.tree()
        Q = SR.paths(ev, 'locked')
        with self.assertRaises(SystemExit) as e:  # 13 failed for an operational reason (left reading): read it again
            SL.triage(ev, type('A', (), {'dry': False, 'short': True, 'accept_left_out': False})())
        self.assertIn('--accept-left-out', str(e.exception))
        self.assertFalse(Q['claims'].exists() or (Q['score'] / 'private').exists())  # nothing written
        A = type('A', (), {'dry': False, 'short': True, 'accept_left_out': True})
        SL.triage(ev, A())
        self.assertEqual(Q['adj'].name, 'folios')
        for r in W.JUDGES:  # each judge role its own folders, for the analysed papers only
            for p_ in ('11', '12', '14'):
                self.assertEqual((Q['adj'] / W.code(W.judge_label(r, 'locked')) / p_ / 'paper.txt').read_text(), 'text ' + p_)
            self.assertFalse((Q['adj'] / W.code(W.judge_label(r, 'locked')) / '13').exists())
        tri = json.loads((Q['score'] / 'private' / 'triage.json').read_text())
        self.assertEqual(tri['papers_analysed'], 3)
        self.assertEqual(tri['papers_failed'], {'13': 'catlog failed'})  # left reading in the copy
        self.assertEqual(tri['left_out_by_side'], {'plain': {}, 'catlog': {'13': 'catlog failed'}})
        self.assertEqual((tri['left_out_operational'], tri['left_out_accepted']), ({'13': 'catlog failed'}, True))
        self.assertEqual(tri['left_out_before_the_set_was_full'], ['13'])
        self.assertEqual(tri['agreeing_pairs'], 3)
        claims = [c for f in sorted(Q['claims'].glob('*.json')) for c in json.loads(f.read_text())]
        keys = set(SC.shown(SC.C.catalog_values([cat[0]])[0])) | {'id', 'details'}
        for c in claims:
            self.assertEqual(set(c), keys)  # nothing names a source or a decoy
            self.assertTrue(c['details'])
        cm = [json.loads(line) for line in open(Q['score'] / 'private' / 'claims_map.jsonl')]
        real = [c for c in cm if not c['decoy']]
        self.assertTrue(all(len(c['members']) == 1 and c['members'][0]['src'] == c['source_shown'] for c in real))
        self.assertEqual(sorted((c['kind'], c['source_shown']) for c in real),
                         sorted([('matched_sample', 'catlog')] * 3 + [('matched_sample', 'plain')] * 3
                                + [('unmatched', 'plain')] * 4))
        his = [c for c in real if c['source_shown'] == 'catlog' and c['members'][0]['id'] == 'r1']
        self.assertIn('His-tagged', his[0]['shown']['details'])  # the copy's own construct, shown
        dec = [c for c in cm if c['decoy']]
        self.assertTrue(dec and all(c['decoy'] in ('x1000', 'x60') and c['shown']['details'] for c in dec))
        self.assertTrue(all(c['twin_visible'] for c in dec))  # every agreeing pair sampled: the twin shows
        # no agreeing pair at all (14): decoys from its own lone claims, recorded as such and kept out of the gate
        self.assertEqual({(c['pmid'], c['decoy_base']) for c in dec},
                         {('11', 'agreeing_sampled'), ('12', 'agreeing_sampled'), ('14', 'lone_claims')})
        gate = [c for c in dec if c['decoy_base'] != 'lone_claims']
        self.assertEqual((Q['score'] / 'private' / 'order.txt').read_text().split(), ['11', '12', '14'])
        with self.assertRaises(SystemExit):  # drawn once
            SL.triage(ev, A())
        saved = SR.papers_of
        SR.papers_of = lambda tsv, a: [r['pmid'] for r in W.read_tsv(tsv)]  # the fake papers are not in the real hold-out
        self.addCleanup(setattr, SR, 'papers_of', saved)
        import contextlib, io
        committed(self)  # the curation secondary's code committed before triage: it is used
        with self.assertRaises(SystemExit) as e:  # no copy of the curation in records/keys/: stopped before writing
            SL.report(ev, type('A', (), {'partial': True, 'B': 50})())
        self.assertIn('is missing', str(e.exception))
        self.assertFalse((Q['score'] / 'results.json').exists())
        # the curation secondary: 11 enzyextract, 12 both, 14 cosci; 12's GTP kcat only the plain read stored
        fake_curation(self, ev, [ee_row('11', 'ATP', kcat='5 s^-1', km='0.5 mM', enzyme='kinase'),
                                 ee_row('12', 'ATP', kcat='2 s^-1', enzyme='kinase'),
                                 ee_row('12', 'GTP', kcat='70 s^-1', enzyme='kinase'),
                                 ee_row('14', 'UTP', kcat='3 s^-1', enzyme='kinase')],
                      {'11': 'enzyextract', '12': 'both', '13': 'enzyextract', '14': 'cosci', '15': 'enzyextract'})
        with contextlib.redirect_stdout(io.StringIO()):  # an interim look before any verdict
            SL.report(ev, type('A', (), {'partial': True, 'B': 50})())
        interim = json.loads((Q['score'] / 'results.json').read_text())
        self.assertTrue(interim['interim'])
        for j in ('j1', 'j2'):  # the judges call every decoy wrong and every real claim supported
            for f in sorted(Q['claims'].glob('*.json')):
                verdicts = [{'id': c['id'], 'verdict': 'wrong_scale' if any(m['claim_id'] == c['id'] and m['decoy'] for m in cm)
                             else 'supported'} for c in json.loads(f.read_text())]
                W.write_json(Q['verdicts'][j] / f.name, {'verdicts': verdicts})
        with contextlib.redirect_stdout(io.StringIO()):
            SL.report(ev, type('A', (), {'partial': False, 'B': 50})())
        res = json.loads((Q['score'] / 'results.json').read_text())
        self.assertFalse(res['interim'])
        cur = res['curation']
        self.assertEqual(cur, interim['curation'])  # the verdicts play no part
        self.assertEqual((cur['papers_covered'], cur['papers_covered_by_gold_set'], cur['papers_not_covered_by_gold_set']),
                         (2, {'both': 1, 'enzyextract': 1}, {'cosci': 1}))
        self.assertEqual({s: (cur['per_source'][s]['all']['sys_n'], cur['per_source'][s]['all']['matched']) for s in SR.SOURCES},
                         {'plain': (5, 4), 'catlog': (3, 3)})  # 11's GTP kcat the curation lacks; 14 not covered
        self.assertEqual(cur['gold_matched_by'], {'both': 3, 'plain_only': 1, 'catlog_only': 0, 'neither': 0})
        self.assertEqual(json.loads((Q['score'] / 'curation.json').read_text())['summary'], cur)
        self.assertEqual((cur['code']['used'], cur['code']['first_commit_time'], cur['code']['triage_time'],
                          cur['code']['commit_at_triage'], cur['code']['file_differs_from_head']),
                         (True, '2000-01-01T00:00:00+00:00', tri['time'], 'c' * 40, False))
        # the draw's papers the curation covers (11, 12, 13, 15): 11 and 12 in the set, 13 left out, 15 never laid down
        self.assertEqual(cur['drawn_papers_covered'], {'drawn': 5, 'covered': 4, 'in_the_set': 2, 'left_out': 1,
                                                       'past_the_target': 0, 'not_laid_down': 1})
        lk = res['locked']
        self.assertEqual(lk['decoys_twin_visible_caught'], [len(gate), len(gate)])
        self.assertEqual(sum(n for n, _ in lk['decoys_caught_by_kind'].values()), len(gate))
        self.assertEqual(res['judges']['decoys'], len(gate))  # the gate counts no decoy made from a lone claim
        self.assertEqual(lk['decoys_from_lone_claims_caught_outside_the_gate'], [len(dec) - len(gate)] * 2)
        self.assertEqual(lk['decoys_caught_by_base']['lone_claims'], [len(dec) - len(gate)] * 2)
        self.assertEqual(lk['left_out_before_the_set_was_full'], {'plain': {}, 'catlog': {'catlog failed': 1}})
        self.assertEqual(lk['left_out_operational_accepted'], {'13': 'catlog failed'})
        self.assertEqual((lk['catlog_models_kept_rows']['reader_model'], lk['catlog_one_model']), ({W.MODEL: 3}, True))
        self.assertEqual(lk['papers_past_target'], [])
        md = (Q['score'] / 'RESULTS.md').read_text()
        self.assertTrue(md.startswith('# Locked set'))
        for want in ('Decoys caught by kind', 'with their twin in the chunk', "a record's shape shows its source",
                     'an agreeing value shows as two claims', "CatLog's side is its frozen first pass", 'Left out before the set',
                     "made from a paper's lone claims", 'after the set was full, not counted: 0',
                     '## Agreement with the EnzyExtract manual curation (secondary, not judged)', 'not ground truth',
                     'and the report says so): met. Its code', 'first committed in cccccccccccc at 2000-01-01T00:00:00+00:00',
                     f"triage ran at {tri['time']}", '(4 of the 5 drawn)',
                     'Of those 4: in the set 2, left out 1, read past the target 0, never laid down 1.'):
            self.assertIn(want, md)
        self.assertLess(md.index('## The set, what was left out'), md.index('## Agreement with the EnzyExtract'))

    def test_a_curation_committed_after_triage_is_dropped(self):
        """The pre-registration uses the curation secondary only if its code was committed before triage: with its first
        commit after triage.json's time, report scores nothing of it and needs no copy of the curation, results.json,
        RESULTS.md and curation.json say it is dropped and why (the commit, its time and triage's), and the primary report
        is whole."""
        ev, P, cat = self.tree()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            SL.triage(ev, type('A', (), {'dry': False, 'short': True, 'accept_left_out': True})())
        Q = SR.paths(ev, 'locked')
        saved = SR.papers_of
        SR.papers_of = lambda tsv, a: [r['pmid'] for r in W.read_tsv(tsv)]  # the fake papers are not in the real hold-out
        self.addCleanup(setattr, SR, 'papers_of', saved)
        committed(self, '2999-01-01T00:00:00+00:00')
        self.assertFalse((W.eval_paths(ev)['keys'] / h2h.GOLD_NAMES['ee_manual']).exists())  # not needed once dropped
        with contextlib.redirect_stdout(io.StringIO()):
            SL.report(ev, type('A', (), {'partial': True, 'B': 50})())
        res = json.loads((Q['score'] / 'results.json').read_text())
        cur = res['curation']
        self.assertEqual((set(cur), cur['judged'], cur['dropped']),
                         ({'judged', 'dropped', 'code'}, False, 'its code was first committed after triage'))
        self.assertEqual((cur['code']['used'], cur['code']['first_commit'], cur['code']['commit_at_triage']),
                         (False, 'c' * 40, None))
        self.assertEqual(json.loads((Q['score'] / 'curation.json').read_text()), {'summary': cur})
        md = (Q['score'] / 'RESULTS.md').read_text()
        sec = md[md.index('## Agreement with the EnzyExtract manual curation (secondary, not judged)'):]
        for want in ('NOT met (its code was first committed after triage), so it is dropped',
                     'first committed in cccccccccccc at 2999-01-01T00:00:00+00:00', f"triage ran at {cur['code']['triage_time']}",
                     'this file as committed then: none', 'Dropped, as the pre-registration says for this case'):
            self.assertIn(want, sec)
        for gone in ('Recall', 'Precision', 'Papers:'):
            self.assertNotIn(gone, sec)
        self.assertIn('## The set, what was left out', md)  # the primary report as before
        self.assertIn('locked', res)

    def test_decoy_bases_and_the_cut(self):
        """With no agreeing value, a paper's decoys change the values of its identity_suspect pairs (both reads printed
        the number) before its lone claims; the report counts the papers left out for another model before the set was
        full, and prints those after it apart."""
        ev, P, cat = self.tree()
        cat.append({**row('kcat', 3, substrate='CTP'), 'pmid': '14', 'row_id': 'r5', **STAMP})  # 14: the plain read's UTP
        (P['runs'] / 'A6-locked' / 'catalog.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in cat))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            SL.triage(ev, type('A', (), {'dry': False, 'short': True, 'accept_left_out': True})())
        Q = SR.paths(ev, 'locked')
        cm = [json.loads(line) for line in open(Q['score'] / 'private' / 'claims_map.jsonl')]
        self.assertEqual(sorted(c['kind'] for c in cm if c['pmid'] == '14' and not c['decoy']),
                         ['identity_suspect', 'identity_suspect', 'unmatched'])
        self.assertEqual({c['decoy_base'] for c in cm if c['pmid'] == '14' and c['decoy']}, {'identity_suspect'})
        tri = {'left_out_by_side': {'plain': {'12': 'refused (plain)'},
                                    'catlog': {'12': 'catlog read by another model', '13': 'catlog failed',
                                               '16': 'catlog read by another model', '17': 'refused (catlog)'}},
               'left_out_before_the_set_was_full': ['12', '13'], 'left_out_after_the_set_was_full': ['16', '17']}
        self.assertEqual(SL.other_model_left_out(tri), (['12'], ['16']))  # 12 counts, whatever its plain reason

    def test_refused_prefix_inputs_and_stamps(self):
        """A6-locked.txt must be a prefix of the draw; the copy, the plain read and the judges must have been given the
        same text, original and supplement; every kept row must carry the frozen copy's stamps."""
        A = type('A', (), {'dry': True, 'short': True, 'accept_left_out': True})
        ev, P, cat = self.tree()
        (P['orders'] / 'A6-locked.txt').write_text('11\n13\n14\n')  # draw paper 12 skipped
        with self.assertRaises(SystemExit) as e:
            SL.triage(ev, A())
        self.assertIn("['12']", str(e.exception))
        ev, P, cat = self.tree()
        h = json.loads((P['records'] / 'hard_inputs.json').read_text())
        h['12']['supp_sha256'] = 'cc'  # the plain read had a supplement the others lack
        W.write_json(P['records'] / 'hard_inputs.json', h)
        j = json.loads((P['records'] / 'judge_inputs.json').read_text())
        del j['14']
        W.write_json(P['records'] / 'judge_inputs.json', j)
        with self.assertRaises(SystemExit) as e:
            SL.triage(ev, A())
        self.assertIn("'12': 'differ: supp_sha256'", str(e.exception))
        self.assertIn("'14': \"no record in ['judge_inputs']\"", str(e.exception))
        ev, P, cat = self.tree()
        cat[2]['pipeline_commit'] = 'abcdef123456+dirty'
        cat[0]['read_prompt'] = ''  # a blank prompt stamp: catlog.py writes one when it cannot tell, never a wrong hash
        (P['runs'] / 'A6-locked' / 'catalog.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in cat))
        with self.assertRaises(SystemExit) as e:
            SL.triage(ev, A())
        self.assertIn("'12': [\"pipeline_commit 'abcdef123456+dirty'\"]", str(e.exception))
        self.assertNotIn("'11'", str(e.exception))

    def test_stamp_rule(self):
        ok, missed = dict(STAMP), {**STAMP, 'read_by': W.MISSED_BY, 'read_prompt': '6cdd7782a0f2'}
        bad = [{**STAMP, 'pmid': '2', 'pipeline_commit': ''}, {**STAMP, 'pmid': '3', 'verify_prompt': '000000000000'},
               {**STAMP, 'pmid': '4', 'read_by': W.MISSED_BY}]  # a missed-values row follows verify.md
        rows = [{**ok, 'pmid': '1'}, {**ok, 'pmid': '1', 'read_prompt': '', 'verify_prompt': ''}, {**missed, 'pmid': '1'}] + bad
        tag = STAMPS['a6']['pipeline_commit_stamp']
        self.assertEqual(W.a6_stamp_problems(rows, STAMPS, tag), {'2': ["pipeline_commit ''"], '3': ["verify_prompt '000000000000'"],
                                                                  '4': ["read_prompt '86e5d7668c1c'"]})
        with self.assertRaises(SystemExit):  # no frozen stamps to compare with
            W.a6_stamp_problems(rows, {'a6': {}}, tag)
        moved = {**STAMPS, 'a6': {'pipeline_commit_stamp': '0123456789ab'}}  # a freeze moved the copy, and its manifest
        with self.assertRaises(SystemExit) as e:  # rows stamped with the new snapshot match the manifest, not the tag
            W.a6_stamp_problems([{**ok, 'pmid': '1', 'pipeline_commit': '0123456789ab'}], moved, tag)
        self.assertIn(W.FREEZE_TAG, str(e.exception))
        self.assertEqual(W.freeze_stamp(), 'fb0cf1758951')  # the main repository's tag on the copy's snapshot of 9 November

    def test_catlog_on_another_model(self):
        """The launch whose rows are kept decides: the last that ran agents for a paper (its redo's for a redone paper);
        any of its agents on another model leaves the paper out ('catlog read by another model', a rule of the plan)."""
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        ev = Path(d.name)
        P = W.eval_paths(ev)
        logs = P['logs'] / 'A6-locked'
        for launch, agents in (('main', [agent('read-sonnet:12'), agent('read:13'),
                                         agent('verify:13', seq=f'{W.MODEL}>claude-opus-5'), agent('read-sonnet:14'),
                                         agent('read:16'), agent('verify-sonnet:16', seq=''), LAUNCH_ROW]),
                               ('more-1', [agent('read:12'), agent('verify:12'), LAUNCH_ROW]),
                               ('redo', [agent('read:14'), agent('verify:14'), agent('read:15'),
                                         agent('verify:15', events=[{'subtype': 'model_refusal_fallback'}]), LAUNCH_ROW])):
            W.write_json(logs / launch / 'agents.json', agents)
        W.write_json(P['runs'] / 'A6-locked' / 'redo' / 'RESET.json', {'pmids': ['14', '15']})
        # 16's Sonnet retry has an empty sequence: it never produced a message, so no other model read 16
        self.assertEqual(sorted(W.a6_other_model(ev, 'locked')), ['13', '15'])
        self.assertEqual(W.a6_kept_agents(ev, 'locked')['14'][0], 'redo')  # a redone paper's agents: its redo's
        (logs / 'more-2').mkdir()
        (logs / 'more-2' / 'launch_line.txt').write_text('...')  # a follow-up whose claim failed: no session started
        self.assertEqual(sorted(W.a6_other_model(ev, 'locked')), ['13', '15'])
        (logs / 'more-2' / 'session.json').write_text('')  # a session the launcher before 2026-11-10 named nowhere
        with self.assertRaises(SystemExit):  # its agents' models are unknown
            W.a6_other_model(ev, 'locked')
        ev, P, cat = self.tree()  # the fake tree: 12's verifier was the workflow's Sonnet retry, no refusal before it
        f = P['logs'] / 'A6-locked' / 'main' / 'agents.json'
        W.write_json(f, [a if a['label'] != 'verify:12' else agent('verify-sonnet:12') for a in json.loads(f.read_text())])
        tri = self.summary(ev)  # operational: the paper is read again on Opus (run_a6.py locked --redo --pmids 12)
        self.assertEqual(tri['papers_failed'], {'12': 'catlog retry on another model', '13': 'catlog failed'})
        self.assertEqual(tri['left_out_operational'], {'12': 'catlog retry on another model', '13': 'catlog failed'})
        self.assertFalse(SL.an_exit('catlog retry on another model'))
        self.assertEqual(tri['catlog_read_by_another_model'], {'12': ['verify-sonnet:12 ' + W.RETRY_MODEL]})
        f = P['logs'] / 'A6-locked' / 'main' / 'agents.json'  # a switch inside an Opus agent: another model, a rule exit
        W.write_json(f, [a if a['label'] != 'verify-sonnet:12' else agent('verify:12', seq=f'{W.MODEL}>claude-opus-5')
                         for a in json.loads(f.read_text())])
        tri = self.summary(ev)
        self.assertEqual(tri['left_out_operational'], {'13': 'catlog failed'})  # a model rule is no reason to stop
        self.assertEqual(tri['papers_failed']['12'], 'catlog read by another model')
        ev, P, cat = self.tree()  # every agent on Opus, but a kept row of 12 stamped with another model
        cat[2]['verifier_model'] = W.RETRY_MODEL
        (P['runs'] / 'A6-locked' / 'catalog.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in cat))
        tri = self.summary(ev)
        self.assertEqual(tri['papers_failed']['12'], 'catlog read by another model')
        self.assertEqual(tri['catlog_read_by_another_model'], {'12': [f'verifier_model {W.RETRY_MODEL}']})

    def test_refusals_and_retries(self):
        """A Sonnet retry is classed by what started it: one an Opus agent's refusal of the same role started, in any
        launch of the paper's state, leaves the paper as 'refused (catlog)', a rule exit like 'refused (plain)', whether
        the retry then ran or died at once, and a follow-up that reads it again changes nothing (a refused plain session
        is never sent again); a paper left unfinished for any other reason is operational, whatever refusal an agent got
        past before (A6-hard more-2's 41552538: its reader got past 7 refusals, its verifier died and its retry never
        ran, the usage limit); a retry that ran with no refusal before it is operational too; a refusal the agent got
        past on Opus itself, in a finished paper with no retry, stops nothing (a plain session that logged one and
        finished counts as read too). These rows record no ending and no transcript, so each refusal counts as before;
        test_refusal_or_usage_limit_at_the_end tells a refusal from the usage limit by the transcript's end."""
        ev, P, cat = self.tree()
        f = P['logs'] / 'A6-locked' / 'main' / 'agents.json'
        W.write_json(f, [agent('read:11', refusals=1), agent('verify:11'),  # 11: got past its refusal on Opus
                         agent('read:12', refusals=1), agent('read-sonnet:12'), agent('verify:12'),  # 12: retry it started
                         agent('read:13', refusals=7), agent('verify:13'), agent('verify-sonnet:13', seq=''),  # 13: 41552538
                         agent('read:14'), agent('verify:14'), agent('verify-sonnet:14', seq=''),  # 14: a retry never ran
                         LAUNCH_ROW])
        tri = self.summary(ev)
        self.assertEqual(tri['papers_failed'], {'12': 'refused (catlog)', '13': 'catlog failed'})
        self.assertEqual(tri['left_out_operational'], {'13': 'catlog failed'})  # the usage limit, not the filter: read again
        self.assertEqual(tri['papers_analysed'], 2)
        # the retry that ran is listed as another model, but what started it, the refusal, is 12's reason
        self.assertEqual(tri['catlog_read_by_another_model'], {'12': ['read-sonnet:12 ' + W.RETRY_MODEL]})
        W.write_json(f, [agent('read:11'), agent('verify:11'), agent('read:12', refusals=2), agent('verify:12'),
                         agent('verify-sonnet:12', seq=W.MODEL),  # a retry of another role: its reader got past it
                         agent('read:13', refusals=1), agent('read-sonnet:13', seq=''),  # refused, the retry died at once
                         agent('read:14'), agent('verify:14'), agent('read-sonnet:14', seq=''), LAUNCH_ROW])
        tri = self.summary(ev)  # no refusal started 12's retry: operational, read again on Opus
        self.assertEqual(tri['papers_failed'], {'12': 'catlog retry on another model', '13': 'refused (catlog)'})
        self.assertEqual(tri['left_out_operational'], {'12': 'catlog retry on another model'})
        self.assertTrue(SL.an_exit('refused (catlog)') and not SL.an_exit('catlog failed'))
        # 13 read again in a follow-up whose reader is not refused, and finished there: still refused, as its first try was
        W.write_json(P['logs'] / 'A6-locked' / 'more-1' / 'agents.json', [agent('read:13'), agent('verify:13'), LAUNCH_ROW])
        W.write_tsv(P['runs'] / 'A6-locked' / 'papers.tsv', [{'pmid': p_, 'status': 'done'} for p_ in ('11', '12', '13', '14')],
                    ['pmid', 'status'])
        jf = P['audit'] / 'A6-locked' / 'audit.json'
        au = json.loads(jf.read_text())
        au['agents'] += [audit_row('launch:more-1', 'more-1'), audit_row('read:13', 'more-1'), audit_row('verify:13', 'more-1')]
        W.write_json(jf, au)
        state = W.a6_state_agents(ev, 'locked')
        self.assertEqual([x[0] for x in state['13']], ['main', 'more-1'])
        self.assertEqual(W.a6_kept_agents(ev, 'locked', state)['13'][0], 'more-1')
        self.assertTrue(W.a6_refused(state['13']) and not W.a6_refused(state['13'][1:]))  # the kept launch alone: no
        self.assertEqual(self.summary(ev)['papers_failed']['13'], 'refused (catlog)')

    def test_refusal_or_usage_limit_at_the_end(self):
        """What started a retry is read from how the Opus agent's transcript ends (review of round 3, 2026-11-10). In
        main, 13's reader gets past 7 refusals. If the usage limit then stops it (a '<synthetic>' API error of
        stop_reason 'stop_sequence'), its read-sonnet dies at once and 13 is left reading: 'catlog failed', read again
        rather than replaced (a retry that ran and finished the read instead: no refusal, a retry on another model, read
        again too), and a clean more-1 read of it is analysed. If its transcript ends in the refusal instead
        (stop_reason 'refusal'), the refusal started the retry: 'refused (catlog)', whatever more-1 does. Both from rows
        that record the ending (agents.json since 2026-11-10) and from rows without it (A6-hard's agents.json), read
        from the transcripts; a row without it whose transcript is gone counts its refusal, as before."""
        import run_a6 as RA6
        ev, P, cat = self.tree()
        main = P['logs'] / 'A6-locked' / 'main'
        others = [r for r in json.loads((main / 'agents.json').read_text()) if r['pmid'] != '13']  # 11, 12, 14, launch
        base = ev / 'projects' / W.project_slug(P['a6'])
        task = f"Follow {P['a6']}/prompts/read.md for PMID 13. The paper ..."

        def main_launch(end, ending=True):
            """main's agents.json with 13's reader ending in `end` and its retry dead at once (rows from agent_rows on
            the session's transcripts; ending False: the rows without their 'ending', as written before)."""
            sid = 'sess-' + end['message']['stop_reason']
            sub = base / sid / 'subagents' / 'workflows' / 'wf_1'
            agent_transcript(sub / 'agent-a1.jsonl', task, refusals=7, end=end)
            agent_transcript(sub / 'agent-a2.jsonl', task, end=LIMIT_END)  # the retry: no message of a model
            for name, desc in (('agent-a1', 'read:13'), ('agent-a2', 'read-sonnet:13')):
                (sub / f'{name}.meta.json').write_text(json.dumps({'description': desc}))
            fake_transcript(base / f'{sid}.jsonl', [('Bash', {}, W.MODEL)])
            rows = [r for r in RA6.agent_rows(P['a6'], sid, base=base) if r['pmid']]
            W.write_json(main / 'agents.json', others + [r if ending else {k: v for k, v in r.items() if k != 'ending'}
                                                         for r in rows])
            return {r['label']: r for r in rows}

        rows = main_launch(LIMIT_END)
        self.assertEqual((rows['read:13']['refusals'], rows['read:13']['sequence'], rows['read:13']['ending']),
                         (7, W.MODEL, {'model': '<synthetic>', 'stop_reason': 'stop_sequence', 'api_error': True}))
        self.assertEqual((rows['read-sonnet:13']['role'], rows['read-sonnet:13']['sequence']), ('read', ''))
        self.assertTrue(W.a6_ended_by_api_error(rows['read:13']))
        tri = self.summary(ev)  # left reading by the usage limit: operational, read again rather than replaced
        self.assertEqual((tri['papers_failed'], tri['left_out_operational']), ({'13': 'catlog failed'},) * 2)
        # had the retry run, the limit would have started it too: no refusal, a retry that ran (a6_retried: once the
        # paper is finished, 'catlog retry on another model')
        ran = [rows['read:13'], {**rows['read-sonnet:13'], 'sequence': W.RETRY_MODEL}]
        self.assertEqual((W.a6_refused([('main', ran)]), W.a6_retried(ran)), (False, [f'read-sonnet:13 {W.RETRY_MODEL}']))
        self.assertEqual(main_launch(REFUSAL_END)['read:13']['ending'],
                         {'model': '<synthetic>', 'stop_reason': 'refusal', 'api_error': True})
        self.assertEqual(self.summary(ev)['papers_failed'], {'13': 'refused (catlog)'})
        # 13 read again cleanly in more-1, as A6_LAUNCH.md step 2 does for a paper left reading
        W.write_json(main.parent / 'more-1' / 'agents.json', [agent('read:13'), agent('verify:13'), LAUNCH_ROW])
        W.write_tsv(P['runs'] / 'A6-locked' / 'papers.tsv', [{'pmid': p_, 'status': 'done'} for p_ in ('11', '12', '13', '14')],
                    ['pmid', 'status'])
        jf = P['audit'] / 'A6-locked' / 'audit.json'
        au = json.loads(jf.read_text())
        au['agents'] += [audit_row('launch:more-1', 'more-1'), audit_row('read:13', 'more-1'), audit_row('verify:13', 'more-1')]
        W.write_json(jf, au)
        for ending in (True, False):
            main_launch(LIMIT_END, ending)
            written = {r['label']: r for r in json.loads((main / 'agents.json').read_text())}
            self.assertEqual('ending' in written['read:13'], ending)
            state = W.a6_state_agents(ev, 'locked')
            self.assertEqual(([x[0] for x in state['13']], W.a6_refused(state['13'])), (['main', 'more-1'], False))
            tri = self.summary(ev)  # judged on the launch whose rows are kept: more-1, clean
            self.assertEqual((tri['papers_failed'], tri['papers_analysed']), ({}, 4))
            main_launch(REFUSAL_END, ending)  # the same reader, its transcript ending in the refusal
            self.assertTrue(W.a6_refused(W.a6_state_agents(ev, 'locked')['13']))
            self.assertEqual(self.summary(ev)['papers_failed'], {'13': 'refused (catlog)'})
        rows = main_launch(LIMIT_END, ending=False)  # without the ending, and its transcript gone: as before
        Path(rows['read:13']['transcript']).unlink()
        self.assertEqual(self.summary(ev)['papers_failed'], {'13': 'refused (catlog)'})

    def test_killed_launch(self):
        """A launch killed on the way (launch.json written before the session started, no agents.json) is accounted for
        from its session's transcripts, read only; one where no session started ran no agents."""
        import run_a6 as RA6
        ev, P, cat = self.tree()
        saved = W.PROJECTS
        W.PROJECTS = ev / 'projects'
        self.addCleanup(setattr, W, 'PROJECTS', saved)
        d = P['logs'] / 'A6-locked' / 'more-1'
        d.mkdir()
        (d / 'launch_line.txt').write_text('...')
        self.assertEqual(RA6.launch_agents(d), [])  # its claim failed: no session started
        tr = W.PROJECTS / W.project_slug(P['a6']) / 'sess-9.jsonl'
        W.write_json(d / 'launch.json', {'launch': 'more-1', 'pmids': ['13'], 'cwd': str(P['a6']), 'session_id': 'sess-9',
                                         'transcript': str(tr)})
        self.assertEqual(RA6.launch_agents(d), [])  # named, but no transcript on disk: it never started
        fake_session(W.PROJECTS, P['a6'], 'sess-9', [('read:13', W.MODEL), ('verify:13', W.MODEL),
                                                       ('verify-sonnet:12', W.RETRY_MODEL)])
        rows = RA6.launch_agents(d)
        self.assertEqual(sorted((r['label'], r['role'], r['rebuilt']) for r in rows if r['pmid']),
                         [('read:13', 'read', True), ('verify-sonnet:12', 'verify', True), ('verify:13', 'verify', True)])
        self.assertFalse((d / 'agents.json').exists())  # read only
        kept = W.a6_kept_agents(ev, 'locked')
        self.assertEqual((kept['13'][0], kept['12'][0], kept['11'][0]), ('more-1', 'more-1', 'main'))
        self.assertEqual(sorted(W.a6_other_model(ev, 'locked', kept)), ['12'])

    def test_broken_launch_follows_the_kept_launch(self):
        """A broken launch session leaves out the papers whose kept rows it ran, not a paper read again in a clean redo
        launch; for a paper whose kept launch it is, rule_broken wins over redo_pending and redo_not_kept."""
        ev, P, cat = self.tree()
        jf = P['audit'] / 'A6-locked' / 'audit.json'
        au = json.loads(jf.read_text())
        au['agents'] = [audit_row('launch:main', broken=True)] + [r for r in au['agents'] if r['role'] != 'launch']
        W.write_json(jf, au)
        W.write_json(P['logs'] / 'A6-locked' / W.MODEL_SWITCH_FILE, {'12': {'pmid': '12', 'outcome': 'redo_pending'}})
        self.assertEqual(self.summary(ev)['papers_failed']['12'], 'catlog rule_broken')  # not catlog redo_pending
        W.write_json(P['logs'] / 'A6-locked' / W.MODEL_SWITCH_FILE, {'12': {'pmid': '12', 'outcome': 'second_try_ok'}})
        W.write_json(P['logs'] / 'A6-locked' / 'redo' / 'agents.json', [agent('read:12'), agent('verify:12'), LAUNCH_ROW])
        self.assertEqual(self.summary(ev)['papers_failed']['12'], 'catlog rule_broken')  # its redo not kept: still main's
        redo = P['runs'] / 'A6-locked' / 'redo'  # the redo kept: 12 follows its clean redo launch session
        W.write_json(redo / 'RESET.json', {'pmids': ['12'], 'reset_utc': '2026-11-10T12:30:00.000Z'})
        W.write_tsv(redo / 'papers.tsv', [{'pmid': '12', 'status': 'done'}], ['pmid', 'status'])
        (redo / 'catalog.jsonl').write_text(json.dumps({**row('kcat', 2), 'pmid': '12', 'row_id': 'r9', **STAMP}) + '\n')
        au['agents'] += [audit_row('launch:redo', 'redo'), audit_row('read:12', 'redo'), audit_row('verify:12', 'redo')]
        W.write_json(jf, au)
        tri = self.summary(ev)
        self.assertEqual(tri['papers_failed'], {p_: 'catlog rule_broken' for p_ in ('11', '13', '14')})
        self.assertEqual(tri['papers_analysed'], 1)

    def test_broken_launch_and_redo_pending(self):
        ev, P, cat = self.tree()
        jf = P['audit'] / 'A6-locked' / 'audit.json'
        au = json.loads(jf.read_text())
        W.write_json(jf, {**au, 'agents': [{**r, 'broken': r['role'] == 'launch'} for r in au['agents']]})
        tri = self.summary(ev)  # a broken launch session: every paper whose kept rows that launch ran
        self.assertEqual(set(tri['papers_failed'].values()), {'catlog rule_broken'})
        self.assertEqual(sorted(tri['papers_failed']), ['11', '12', '13', '14'])
        ev, P, cat = self.tree()
        (P['audit'] / 'A6-locked' / 'rerun.txt').write_text('12\n')  # the audit breaks the switch itself
        W.write_json(P['logs'] / 'A6-locked' / W.MODEL_SWITCH_FILE, {'12': {'pmid': '12', 'outcome': 'redo_pending'}})
        tri = self.summary(ev)
        self.assertEqual(tri['left_out_operational'], {'12': 'catlog redo_pending', '13': 'catlog failed'})  # the redo is to run
        W.write_json(P['logs'] / 'A6-locked' / W.MODEL_SWITCH_FILE, {'12': {'pmid': '12', 'outcome': 'second_try_ok'}})
        self.assertEqual(self.summary(ev)['left_out_operational'], {'12': 'catlog redo_not_kept', '13': 'catlog failed'})
        W.write_json(P['logs'] / 'A6-locked' / W.MODEL_SWITCH_FILE, {'12': {'pmid': '12', 'outcome': 'excluded'}})
        (P['audit'] / 'A6-locked' / 'rerun.txt').write_text('')  # the audit lists no paper a switch left out
        self.assertEqual(self.summary(ev)['papers_failed']['12'], 'catlog model_switch')  # switched again: a rule of the plan
        self.assertEqual(self.summary(ev)['left_out_operational'], {'13': 'catlog failed'})

    def test_audit_checks(self):
        """The copy's audit must be newer than its last reset and hold agents of papers; a model switch its outcome
        settled (rerun_ok, or second_try_ok with the redo kept) is no broken rule; a paper the audit did not see and a
        finished paper a --force follow-up read again are operational."""
        ev, P, cat = self.tree()
        jf = P['audit'] / 'A6-locked' / 'audit.json'
        au = json.loads(jf.read_text())
        W.write_json(jf, {**au, 'summary': {'time': '2026-11-10 05:00:00 -0600'}})  # before the reset of 12:00 UTC
        with self.assertRaises(SystemExit) as e:
            self.summary(ev)
        self.assertIn('older than the last reset-a6 locked', str(e.exception))
        W.write_json(jf, {**au, 'agents': [audit_row('launch:main')]})  # the audit found no agent transcript
        with self.assertRaises(SystemExit) as e:
            self.summary(ev)
        self.assertIn('holds no agent of a paper', str(e.exception))
        switch = [('break', 'model_switch', f'{W.MODEL}>claude-opus-5')]
        rows = [r if r['label'] != 'read:12' else audit_row('read:12', broken=True, violations=switch) for r in au['agents']]
        W.write_json(jf, {**au, 'agents': rows})
        (P['audit'] / 'A6-locked' / 'rerun.txt').write_text('12\n')
        W.write_json(P['logs'] / 'A6-locked' / W.MODEL_SWITCH_FILE, {'12': {'pmid': '12', 'outcome': 'rerun_ok'}})
        self.assertNotIn('12', self.summary(ev)['papers_failed'])  # read again cleanly: the switch rule settled it
        rows = [r if r['label'] != 'read:12' else audit_row('read:12', broken=True, violations=switch + [('break', 'path', '/x')])
                for r in au['agents']]
        W.write_json(jf, {**au, 'agents': rows})
        self.assertEqual(self.summary(ev)['papers_failed']['12'], 'catlog rule_broken')  # another rule broken too
        (P['audit'] / 'A6-locked' / 'rerun.txt').write_text('')
        W.write_json(jf, {**au, 'summary': {**au['summary'], 'papers_without_reader_or_verifier': ['11', '13']}})
        tri = self.summary(ev)
        self.assertEqual(tri['left_out_operational'], {'11': 'catlog unaudited', '13': 'catlog failed'})
        W.write_json(jf, au)
        W.write_json(P['logs'] / 'A6-locked' / 'more-1' / 'launch.json', {'launch': 'more-1', 'pmids': ['11'], 'force': True,
                                                                          'read_again': ['11']})
        W.write_json(P['logs'] / 'A6-locked' / 'more-1' / 'agents.json', [agent('read:11'), agent('verify:11'), LAUNCH_ROW])
        tri = self.summary(ev)  # its kept rows are two reads': stop, or go on with --accept-left-out (it stays out)
        self.assertEqual(tri['left_out_operational'], {'11': 'catlog read_again', '13': 'catlog failed'})
        W.write_json(P['logs'] / 'A6-locked' / 'more-2' / 'agents.json', [agent('read:12'), agent('verify:12'), LAUNCH_ROW])
        tri = self.summary(ev)  # 12 read again in a follow-up whose agents the audit did not see: its kept rows unaudited
        self.assertEqual(tri['left_out_operational'], {'11': 'catlog read_again', '12': 'catlog unaudited', '13': 'catlog failed'})

    def test_audits_and_scans_are_newer_than_what_they_check(self):
        """Triage refuses while a plain session record is newer than the plain read's audit (a paper read again as its
        own stop message says, its new session unaudited), and unless both content scans (scan_reads.py locked) are
        there, newer than both audits and the copy's last reset, and found nothing (--accept-scan-hits goes on)."""
        ev, P, cat = self.tree()
        lg = P['logs'] / 'A0-locked'
        W.write_json(lg / '12.a1.json', {'label': '12.a1', 'start': '2026-11-10 06:00:00 -0600',
                                         'end': '2026-11-10 06:30:00 -0600'})  # before the audit of 07:00
        W.write_json(lg / 'earlier' / '12' / '1' / '12.a1.json', {'end': '2026-11-10 05:00:00 -0600'})
        self.assertEqual(self.summary(ev)['papers_analysed'], 3)
        W.write_json(lg / '13.a1.json', {'label': '13.a1', 'end': '2026-11-10 07:10:00 -0600'})  # read again after it
        with self.assertRaises(SystemExit) as e:
            self.summary(ev)
        self.assertIn("newer than its audit", str(e.exception))
        self.assertIn("['13.a1.json']", str(e.exception))
        (lg / '13.a1.json').unlink()
        scan = P['audit'] / 'A6-locked' / 'content_scan.json'
        good = json.loads(scan.read_text())
        scan.unlink()
        with self.assertRaises(SystemExit) as e:  # the copy's side was never scanned
            self.summary(ev)
        self.assertIn(f'no {scan}', str(e.exception))
        W.write_json(scan, {**good, 'time': '2026-11-10 06:50:00 -0600'})  # scanned before the audits of 07:00
        with self.assertRaises(SystemExit) as e:
            self.summary(ev)
        self.assertIn('is older than the audit of A0-locked, the audit of A6-locked', str(e.exception))
        hit = {'record': 'main/read:11', 'call': 2, 'tool': 'Bash', 'part': 'input', 'hit': 'named Downloads', 'text': 'ls'}
        W.write_json(scan, {**good, 'hits': [hit]})
        with self.assertRaises(SystemExit) as e:
            self.summary(ev)
        self.assertIn('has 1 hits', str(e.exception))
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            SL.triage(ev, type('A', (), {'dry': True, 'short': True, 'accept_left_out': False, 'accept_scan_hits': True})())
        tri = json.loads(out.getvalue())  # looked at and accepted: triage goes on and says so
        self.assertTrue(tri['content_scan_hits_accepted'])
        self.assertEqual(tri['content_scans']['A6-locked']['hits'], 1)
        W.write_json(scan, good)
        W.write_json(P['runs'] / 'A6-locked' / 'redo' / 'RESET.json', {'pmids': [], 'reset_utc': '2026-11-10T13:40:00.000Z'})
        with self.assertRaises(SystemExit) as e:  # a redo kept after the audit: the audit refuses first
            self.summary(ev)
        self.assertIn('older than the last reset-a6 locked', str(e.exception))
        jf = P['audit'] / 'A6-locked' / 'audit.json'
        W.write_json(jf, {**json.loads(jf.read_text()), 'summary': {'time': '2026-11-10 07:45:00 -0600'}})
        with self.assertRaises(SystemExit) as e:  # audited again after the redo, but the scans are older than that
            self.summary(ev)
        self.assertIn('reset-a6 locked (redo)', str(e.exception))

    def test_redo_launches_count_alike(self):
        """A redone paper is judged on its redo launches, redo and redo-more-<k> alike (common_w1.a6_judged: w1_audit.main
        writes rerun.txt from it, and a6_rows reads the breaks by it): its main switch counts no more, a break in
        redo-more-1 counts; the switch rule settles a switch, but a paper whose kept launch the audit did not cover is
        unaudited, an operational stop, and is not analysed."""
        ev, P, cat = self.tree()
        jf = P['audit'] / 'A6-locked' / 'audit.json'
        au = json.loads(jf.read_text())
        switch = [('break', 'model_fallback', 'model_refusal_fallback: claude-opus-5-5>claude-opus-5')]
        main_rows = [r if r['label'] != 'read:12' else audit_row('read:12', broken=True, violations=switch) for r in au['agents']]
        W.write_json(P['logs'] / 'A6-locked' / W.MODEL_SWITCH_FILE, {'12': {'pmid': '12', 'outcome': 'second_try_ok'}})
        redo = P['runs'] / 'A6-locked' / 'redo'
        W.write_json(redo / 'RESET.json', {'pmids': ['12'], 'reset_utc': '2026-11-10T12:30:00.000Z'})
        W.write_tsv(redo / 'papers.tsv', [{'pmid': '12', 'status': 'done'}], ['pmid', 'status'])
        (redo / 'catalog.jsonl').write_text(json.dumps({**row('kcat', 2), 'pmid': '12', 'row_id': 'r9', **STAMP}) + '\n')
        logs = P['logs'] / 'A6-locked'
        W.write_json(logs / 'redo' / 'agents.json', [agent('read:12'), LAUNCH_ROW])  # the redo stopped at a usage limit
        W.write_json(logs / 'redo-more-1' / 'agents.json', [agent('read:12'), agent('verify:12'), LAUNCH_ROW])  # its follow-up
        self.assertEqual(W.a6_kept_agents(ev, 'locked')['12'][0], 'redo-more-1')

        def audit(rows):  # audit.json as w1_audit writes it, and rerun.txt from what each paper is judged on (its main())
            W.write_json(jf, {**au, 'agents': rows})
            (P['audit'] / 'A6-locked' / 'rerun.txt').write_text(''.join(
                p_ + '\n' for p_ in sorted({r['pmid'] for r in W.a6_judged(rows) if r.get('broken')})))
            return self.summary(ev)
        clean = [audit_row('launch:redo', 'redo'), audit_row('read:12', 'redo'), audit_row('launch:redo-more-1', 'redo-more-1'),
                 audit_row('read:12', 'redo-more-1'), audit_row('verify:12', 'redo-more-1')]
        tri = audit(main_rows + clean)
        self.assertEqual((P['audit'] / 'A6-locked' / 'rerun.txt').read_text(), '')  # judged on its redo launches only
        self.assertNotIn('12', tri['papers_failed'])  # its rows come from the kept redo
        self.assertEqual(tri['papers_analysed'], 3)
        path = [('break', 'forbidden', '<the CatLog folder>/catalog.jsonl')]
        tri = audit(main_rows + clean[:-1] + [audit_row('verify:12', 'redo-more-1', broken=True, violations=path)])
        self.assertEqual((P['audit'] / 'A6-locked' / 'rerun.txt').read_text(), '12\n')  # a break in redo-more-1 counts
        self.assertEqual(tri['papers_failed']['12'], 'catlog rule_broken')
        tri = audit(main_rows + clean[:2])  # the audit missed redo-more-1, the launch whose rows are kept
        self.assertEqual(tri['left_out_operational'], {'12': 'catlog unaudited', '13': 'catlog failed'})
        tri = audit(main_rows)  # it saw no redo agent: judged on main, whose switch the rule settled; still unaudited
        self.assertEqual((P['audit'] / 'A6-locked' / 'rerun.txt').read_text(), '12\n')
        self.assertEqual(tri['left_out_operational'], {'12': 'catlog unaudited', '13': 'catlog failed'})

    def test_closed_doors(self):
        """A locked-set judge cannot read the first judges', randfull's or the other locked roles' sessions."""
        import run_adjudicate as RA
        ev = W.EVAL
        P = W.eval_paths(ev, 'locked')
        rules = RA.adj_deny(ev, P['verdicts']['j1'], 'locked', 'xx-c01', P['claims'], 'j1')
        fam = lambda r, w: W.project_slug(P['adj'] / W.code(W.judge_label(r, w))) + '-*'  # noqa: E731
        self.assertIn(f"Read(/{W.PROJECTS}/{fam('j1', 'locked')}/*.jsonl)", rules)
        self.assertNotIn(f"Read(/{W.PROJECTS}/{fam('j1', 'locked')}/**)", rules)
        for r in W.JUDGES:
            self.assertIn(f"Read(/{W.PROJECTS}/{fam(r, 'randfull')}/**)", rules)
        for r in ('j2', 'j3'):
            self.assertIn(f"Read(/{W.PROJECTS}/{fam(r, 'locked')}/**)", rules)
        self.assertIn(f"Read(/{W.PROJECTS}/{W.project_slug(W.eval_paths(ev)['adj'])}-*/**)", rules)
        old = RA.adj_deny(ev, W.eval_paths(ev, 'randfull')['verdicts']['j1'], 'randfull', 'xx-c01',
                          W.eval_paths(ev, 'randfull')['claims'], 'j1')
        for r in W.JUDGES:  # randfull's role families as they were: no locked family in its list
            self.assertFalse(any(fam(r, 'locked') in x for x in old))
        self.assertIn(f'Read(/{Path.home()}/Downloads/**)', rules)  # the owner's downloads closed to the locked judges
        self.assertFalse([x for x in old if 'Downloads' in x])  # randfull's finished list as it was
        self.assertIn(W.code(W.judge_label('j3', 'locked')), W.scratch_labels())


class Curation(unittest.TestCase):
    """score_locked.curation, the pre-registered secondary: each side's values against EnzyExtract's manual curation on
    the set's papers it covers, on synthetic values and a synthetic curation."""
    SETS = {'21': 'enzyextract', '22': 'enzyextract', '23': 'cosci', '24': 'both', '25': 'enzyextract'}  # 26 not listed
    ROWS = [ee_row('21', 'pNPB', kcat='5 s^-1', km='200 µM'),
            ee_row('21', 'pNPP', kcat='10 s^-1', km='<0.5 mM', kcat_km='n.d.'),  # a bound, and a cell no unit reads
            ee_row('21', 'pNPO', 'H52A', kcat='3 s^-1'), ee_row('21', 'pNPD', 'H52A', kcat='3 s^-1'),  # two equal values
            ee_row('21', 'pNPC', km='1.5 mM'),  # neither source stored it
            ee_row('22', 'MUB', kcat_km='1.2 x 10^6 M^-1 s^-1'),
            ee_row('23', 'ATP', kcat='8 s^-1'),  # a cosci paper: never used
            ee_row('24', 'ATP', kcat='2 s^-1')]  # a paper of both curations: this one alone

    def val(self, src, pmid, k, metric, value, substrate, variant='wild type'):
        """A value as values.json holds it (score_rand.KEEP)."""
        return {'id': f'A0-locked:{pmid}:{k}' if src == 'plain' else f'r{pmid}{k}', 'pmid': pmid, 'metric': metric,
                'value': value, 'raw': str(value), 'raw_unit': SC.UNIT[metric], 'enzyme': 'lipase',
                'organism': 'B. subtilis', 'variant': variant, 'substrate': substrate, 'cosub': '', 'pH': '7.5',
                'temp': '25', 'where': 'Table 1', 'conditions': ''}

    def values(self):
        v = self.val
        plain = [v('plain', '21', 0, 'kcat', 5.0, 'pNPB'), v('plain', '21', 1, 'Km', 0.2, 'pNPB'),  # exact (200 µM)
                 v('plain', '21', 2, 'kcat', 10.1, 'pNPP'),  # within 1.5% of the curation's 10
                 v('plain', '21', 3, 'kcat', 3.0, 'pNPO', 'H52A'),  # one value for the curation's two 3s
                 v('plain', '21', 4, 'kcat', 99.0, 'GTP'), v('plain', '22', 0, 'Km', 0.7, 'MUB'),  # the curation lacks
                 v('plain', '23', 0, 'kcat', 8.0, 'ATP'), v('plain', '24', 0, 'kcat', 2.0, 'ATP'),
                 v('plain', '26', 0, 'kcat', 1.0, 'ATP')]
        catlog = [v('catlog', '21', 0, 'kcat', 5.0, 'pNPB'), v('catlog', '21', 1, 'Km', 0.2, 'pNPB'),
                  v('catlog', '21', 2, 'kcat', 7.5, 'pNPP'),  # the curation's pNPP kcat with another number
                  v('catlog', '21', 3, 'kcat', 3.0, 'pNPO', 'H52A'), v('catlog', '21', 4, 'kcat', 3.0, 'pNPD', 'H52A'),
                  v('catlog', '22', 0, 'kcat/Km', 1200.0, 'MUB'), v('catlog', '24', 0, 'kcat', 2.0, 'ATP'),
                  v('catlog', '25', 0, 'kcat', 4.0, 'ATP')]  # 25: covered, no row in the curation
        return plain, catlog

    def case(self, plain=None, catlog=None, rows=None, sets=None, papers=('21', '22', '23', '24', '25', '26')):
        """A temp eval tree holding only what curation reads: values.json and the curation's copy in records/keys/."""
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        ev = Path(d.name)
        P = SR.paths(ev, 'locked')
        p0, c0 = self.values()
        W.write_json(P['score'] / 'private' / 'values.json', {'plain': p0 if plain is None else plain,
                                                             'catlog': c0 if catlog is None else catlog,
                                                             'papers': list(papers), 'pairs': []})
        fake_curation(self, ev, self.ROWS if rows is None else rows, self.SETS if sets is None else sets)
        return ev, P

    def scored(self, ev, P, B=200):
        x, lines = SL.curation(ev, P, B)
        return x, lines, json.loads((P['score'] / 'curation.json').read_text())

    def test_papers_matches_and_disagreements(self):
        ev, P = self.case()
        x, lines, full = self.scored(ev, P)
        # 21, 22 and 25 enzyextract, 24 both: covered; 23 cosci and 26 (no gold set) left out, their values unused
        self.assertEqual((x['papers_in_set'], x['papers_covered']), (6, 4))
        self.assertEqual(x['papers_covered_by_gold_set'], {'both': 1, 'enzyextract': 3})
        self.assertEqual(x['papers_not_covered_by_gold_set'], {'cosci': 1, 'none': 1})
        self.assertEqual(x['covered_papers_without_a_curation_row'], 1)
        cols = ('pmid', 'gold_set', 'curation_rows', 'gold_n', 'gold_unscored', 'plain_n', 'plain_matched', 'catlog_n',
                'catlog_matched')
        self.assertEqual([tuple(r[c] for c in cols) for r in full['papers']],
                         [('21', 'enzyextract', 5, 6, 2, 5, 4, 5, 4), ('22', 'enzyextract', 1, 1, 0, 1, 0, 1, 1),
                          ('24', 'both', 1, 1, 0, 1, 1, 1, 1), ('25', 'enzyextract', 0, 0, 0, 0, 0, 1, 0)])
        # the bound and the cell no unit reads: kept, never scored
        self.assertEqual((x['gold_values']['all'], x['gold_values']['Km'], x['gold_values']['kcat/Km']),
                         ({'scored': 8, 'unscored': 2}, {'scored': 2, 'unscored': 1}, {'scored': 1, 'unscored': 1}))
        self.assertEqual([(g['raw'], g['value']) for g in full['gold_unscored']], [('<0.5 mM', None), ('n.d.', None)])
        ps, cs = x['per_source']['plain']['all'], x['per_source']['catlog']['all']
        self.assertEqual((ps['gold_n'], ps['sys_n'], ps['matched'], cs['gold_n'], cs['sys_n'], cs['matched']), (8, 7, 5, 8, 8, 6))
        self.assertEqual((ps['recall']['est'], ps['precision']['est'], cs['recall']['est'], cs['precision']['est']),
                         (5 / 8, 5 / 7, 6 / 8, 6 / 8))
        self.assertEqual((ps['recall']['num'], ps['recall']['den'], ps['recall']['papers']), (5, 8, 3))  # 25: no gold
        self.assertEqual((x['per_source']['catlog']['kcat/Km']['recall']['est'],
                          x['per_source']['plain']['kcat/Km']['precision']['est']), (1.0, None))
        by = {k: [(g['pmid'], g['metric'], g['substrate'], g['raw'], g['plain'], g['catlog']) for g in v]
              for k, v in full['gold_matched_by'].items()}
        self.assertEqual(by['both'], [('21', 'kcat', 'pNPB', '5 s^-1', 'A0-locked:21:0', 'r210'),  # exact
                                      ('21', 'Km', 'pNPB', '200 µM', 'A0-locked:21:1', 'r211'),
                                      ('21', 'kcat', 'pNPO', '3 s^-1', 'A0-locked:21:3', 'r213'),
                                      ('24', 'kcat', 'ATP', '2 s^-1', 'A0-locked:24:0', 'r240')])
        self.assertEqual(by['plain_only'], [('21', 'kcat', 'pNPP', '10 s^-1', 'A0-locked:21:2', None)])  # 10.1: within 1.5%
        self.assertEqual(by['catlog_only'], [('21', 'kcat', 'pNPD', '3 s^-1', None, 'r214'),  # one to one: plain's one 3
                                             ('22', 'kcat/Km', 'MUB', '1.2 x 10^6 M^-1 s^-1', None, 'r220')])  # took pNPO's
        self.assertEqual(by['neither'], [('21', 'Km', 'pNPC', '1.5 mM', None, None)])
        self.assertEqual(x['gold_matched_by'], {'both': 4, 'plain_only': 1, 'catlog_only': 2, 'neither': 1})
        # a similar description with another number (desc_pairs), flagged, reported with its ratio, never judged
        dis = full['per_source']['catlog']['similar_description_other_number']
        self.assertEqual([(d['curation']['raw'], d['curation']['substrate'], d['value']['id'], d['value']['raw'], d['ratio'],
                           d['same_variant'], d['substrate_words']) for d in dis],
                         [('10 s^-1', 'pNPP', 'r212', '7.5', 0.75, True, 'same')])
        self.assertEqual(x['similar_description_other_number'], {'plain': 0, 'catlog': 1})
        self.assertEqual(x['similar_description_kinds']['catlog'], {'same_variant_same_substrate_words': 1,
                                                                    'same_variant_some_substrate_words': 0, 'other': 0})
        per = full['per_source']
        self.assertEqual([g['raw'] for g in per['plain']['curation_values_otherwise_unmatched']],
                         ['3 s^-1', '1.5 mM', '1.2 x 10^6 M^-1 s^-1'])
        self.assertEqual([g['raw'] for g in per['catlog']['curation_values_otherwise_unmatched']], ['1.5 mM'])  # pNPP: paired
        self.assertEqual([v['id'] for v in per['plain']['source_values_otherwise_unmatched']], ['A0-locked:21:4', 'A0-locked:22:0'])
        self.assertEqual([v['id'] for v in per['catlog']['source_values_otherwise_unmatched']], ['r250'])  # 7.5: paired
        self.assertEqual((x['curation_values_otherwise_unmatched'], x['source_values_otherwise_unmatched']),
                         ({'plain': 3, 'catlog': 1}, {'plain': 2, 'catlog': 1}))
        for s in SR.SOURCES:  # what precision leaves is the pairs and the source's values otherwise unmatched, nothing else
            a = x['per_source'][s]['all']
            self.assertEqual(a['sys_left'], x['similar_description_other_number'][s] + x['source_values_otherwise_unmatched'][s])
            self.assertEqual(a['gold_left'], x['similar_description_other_number'][s] + x['curation_values_otherwise_unmatched'][s])
        self.assertFalse(x['judged'])
        self.assertNotIn('code', x)  # report alone checks the pre-registration's condition
        md = '\n'.join(lines)
        for want in ('## Agreement with the EnzyExtract manual curation (secondary, not judged)', 'not ground truth',
                     'reported, never judged', "Recall is the share of the curation's scored values the source holds",
                     "precision is the share of the source's values the curation holds", '| Values on the covered papers | 7 | 8 | |',
                     'both 4, plain only 1, CatLog only 2, neither 1', '), 5 of 8 | ', '), 6 of 8 | +0.125 (',
                     "not covered: {'cosci': 1, 'none': 1}", '| kcat/Km: recall, precision | 0.000, - | 1.000, 1.000 | +1.000, - |',
                     # CatLog's precision is 6 of 8: the 2 it leaves are the 2 the leftovers count, a pair and 1 otherwise
                     "the curation's scored values a source did not match, plain 3, CatLog 2; the source's values the curation "
                     "did not match, plain 2, CatLog 2.", 'pairs with a similar description', 'plain 0, CatLog 1: often the same '
                     'measurement with another number, sometimes two measurements of the paper',
                     "the curation's values, plain 3, CatLog 1; the source's values, plain 2, CatLog 1."):
            self.assertIn(want, md)
        self.assertNotIn('does not hold', md)

    def test_a_bound_is_never_matched(self):
        """A bound and a cell the units code cannot read stay with no value: a source value of the bound's number stays
        otherwise unmatched (nothing scored to pair it with), and recall has no denominator."""
        ev, P = self.case(plain=[self.val('plain', '31', 0, 'Km', 0.5, 'ATP')], catlog=[],
                          rows=[ee_row('31', 'ATP', kcat='n.d.', km='<0.5 mM')], sets={'31': 'enzyextract'}, papers=('31',))
        x, _, full = self.scored(ev, P)
        self.assertEqual(x['gold_values']['all'], {'scored': 0, 'unscored': 2})
        a = x['per_source']['plain']['all']
        self.assertEqual((a['matched'], a['recall']['est'], a['precision']['est']), (0, None, 0.0))
        self.assertEqual(x['gold_matched_by'], {'both': 0, 'plain_only': 0, 'catlog_only': 0, 'neither': 0})
        self.assertEqual([v['id'] for v in full['per_source']['plain']['source_values_otherwise_unmatched']], ['A0-locked:31:0'])
        self.assertEqual((full['per_source']['plain']['curation_values_otherwise_unmatched'], full['papers'][0]['gold_unscored']),
                         ([], 2))
        self.assertIsNone(x['catlog_minus_plain']['all']['recall']['est'])  # no scored value: no difference

    def test_paired_difference_sign(self):
        """CatLog minus plain: CatLog holds more of the curation here; with the two sources swapped, the difference and its
        interval change sign (the same papers drawn for both); no difference where one source has no denominator."""
        ev, P = self.case()
        x, _, _ = self.scored(ev, P)
        d = x['catlog_minus_plain']['all']
        self.assertAlmostEqual(d['recall']['est'], 6 / 8 - 5 / 8)
        self.assertAlmostEqual(d['precision']['est'], 6 / 8 - 5 / 7)
        self.assertGreater(d['recall']['est'], 0)
        self.assertLessEqual(d['recall']['lo'], d['recall']['hi'])
        self.assertEqual((d['recall']['papers'], d['precision']['papers']), (3, 4))
        self.assertIsNone(x['catlog_minus_plain']['kcat/Km']['precision']['est'])  # the plain read stored no kcat/Km
        plain, catlog = self.values()
        ev2, P2 = self.case(plain=catlog, catlog=plain)
        y, _, _ = self.scored(ev2, P2)
        e = y['catlog_minus_plain']['all']
        for k in ('recall', 'precision'):
            self.assertAlmostEqual(e[k]['est'], -d[k]['est'])
            self.assertAlmostEqual(e[k]['lo'], -d[k]['hi'])
            self.assertAlmostEqual(e[k]['hi'], -d[k]['lo'])
        self.assertEqual(x['per_source']['catlog']['all']['recall'], y['per_source']['plain']['all']['recall'])

    def test_a_missing_or_changed_curation_stops(self):
        ev, P = self.case()
        f = W.eval_paths(ev)['keys'] / h2h.GOLD_NAMES['ee_manual']
        with open(f, 'a') as fh:
            fh.write('24,lipase,,B. subtilis,ATP,,WT,25,7.5,Table 1,,9 s^-1,,\n')  # a changed copy
        with self.assertRaises(SystemExit) as e:
            SL.curation(ev, P, 50)
        self.assertIn(f"is not the head-to-head's {h2h.GOLD_SHA256['ee_manual']}", str(e.exception))
        f.unlink()
        with self.assertRaises(SystemExit) as e:
            SL.curation(ev, P, 50)
        self.assertIn('is missing', str(e.exception))
        self.assertFalse((P['score'] / 'curation.json').exists())  # nothing scored, nothing written

    def test_same_inputs_same_output(self):
        """Deterministic and plain JSON: the same inputs give the same results, lines and curation.json bytes, with no
        numpy type anywhere (write_json's default=str would turn one into a string silently)."""
        ev, P = self.case()
        seen, saved = {}, W.write_json

        def keep(path, obj, indent=1):
            seen[Path(path).name] = obj
            return saved(path, obj, indent)
        W.write_json = keep
        self.addCleanup(setattr, W, 'write_json', saved)
        x1, l1 = SL.curation(ev, P, 200)
        b1 = (P['score'] / 'curation.json').read_bytes()
        x2, l2 = SL.curation(ev, P, 200)
        self.assertEqual((x1, l1), (x2, l2))
        self.assertEqual(b1, (P['score'] / 'curation.json').read_bytes())

        def plain(o):
            if isinstance(o, dict):
                return all(type(k) is str and plain(v) for k, v in o.items())
            if isinstance(o, list):
                return all(plain(v) for v in o)
            return o is None or type(o) in (str, int, float, bool)
        self.assertTrue(plain(x1) and plain(seen['curation.json']))
        self.assertEqual(json.loads(json.dumps(seen['curation.json'])), json.loads(b1))  # no default=str needed

    def test_similar_description_pairs_are_flagged(self):
        """desc_pairs pairs leftovers on a description score that the variant, enzyme, temperature and pH reach with no
        substrate word in common: each pair is listed as a similar description with another number (often the same
        measurement, sometimes two), flagged by its variant and substrate words, and counted by kind."""
        v = self.val
        rows = [ee_row('41', 'pNPB', kcat='5 s^-1'),  # CatLog stored only pNPO, the plain read its spelled-out name
                ee_row('42', '4-nitrophenyl β-D-glucopyranoside', kcat='12 s^-1'),  # the plain read: the galactoside
                ee_row('43', 'pNPB', 'H52A', kcat='2 s^-1'),  # CatLog: the double mutant
                ee_row('44', 'ATP', kcat='4 s^-1')]  # both: another number for the same measurement
        plain = [v('plain', '41', 0, 'kcat', 9.0, 'p-nitrophenyl octanoate'),
                 v('plain', '42', 0, 'kcat', 40.0, '4-nitrophenyl β-D-galactopyranoside'), v('plain', '44', 0, 'kcat', 8.0, 'ATP')]
        catlog = [v('catlog', '41', 0, 'kcat', 9.0, 'pNPO'), v('catlog', '43', 0, 'kcat', 0.9, 'pNPB', 'H52A/D100N'),
                  v('catlog', '44', 0, 'kcat', 6.0, 'ATP')]
        papers = ('41', '42', '43', '44')
        ev, P = self.case(plain, catlog, rows, {p: 'enzyextract' for p in papers}, papers)
        x, lines, full = self.scored(ev, P)
        got = {s: [(d['pmid'], d['curation']['substrate'], d['value']['substrate'], d['same_variant'], d['substrate_words'],
                    d['ratio']) for d in full['per_source'][s]['similar_description_other_number']] for s in SR.SOURCES}
        self.assertEqual(got['catlog'], [('41', 'pNPB', 'pNPO', True, 'none in common', 1.8),
                                         ('43', 'pNPB', 'pNPB', False, 'same', 0.45), ('44', 'ATP', 'ATP', True, 'same', 1.5)])
        self.assertEqual(got['plain'], [('41', 'pNPB', 'p-nitrophenyl octanoate', True, 'none in common', 1.8),
                                        ('42', '4-nitrophenyl β-D-glucopyranoside', '4-nitrophenyl β-D-galactopyranoside', True,
                                         'some in common', 3.333), ('44', 'ATP', 'ATP', True, 'same', 2.0)])
        self.assertEqual(x['similar_description_other_number'], {'plain': 3, 'catlog': 3})
        self.assertEqual(x['similar_description_kinds'],
                         {'plain': {'same_variant_same_substrate_words': 1, 'same_variant_some_substrate_words': 1, 'other': 1},
                          'catlog': {'same_variant_same_substrate_words': 1, 'same_variant_some_substrate_words': 0, 'other': 2}})
        md = '\n'.join(lines)
        for want in ('the same variant with the same substrate words: plain 1, CatLog 1',
                     'the same variant with some substrate words in common: plain 1, CatLog 0',
                     'the rest (another variant, or no substrate word in common): plain 1, CatLog 2'):
            self.assertIn(want, md)
        self.assertNotIn('the same measurement with another number (', md)  # never named the same measurement as such

    def test_drawn_papers_covered(self):
        """The pre-registration names the drawn papers the curation covers; values.json holds the set's values alone, so
        only the set's are scored, and the report counts the others by why: left out, read past the target, never laid
        down (triage.json and the draw)."""
        ev, P = self.case(sets={**self.SETS, '27': 'enzyextract', '28': 'both', '29': 'enzyextract', '30': 'cosci'})
        W.eval_paths(ev)['orders'].mkdir(parents=True, exist_ok=True)
        (W.eval_paths(ev)['orders'] / 'locked_draw.txt').write_text('27\n21\n22\n23\n24\n25\n26\n28\n29\n30\n')
        W.write_json(P['score'] / 'private' / 'triage.json', {'papers_failed': {'27': 'refused (plain)'},
                                                              'papers_past_target': ['28']})
        x, lines, _ = self.scored(ev, P)
        self.assertEqual(x['drawn_papers_covered'], {'drawn': 10, 'covered': 7, 'in_the_set': 4, 'left_out': 1,
                                                     'past_the_target': 1, 'not_laid_down': 1})
        self.assertEqual(x['papers_covered'], 4)  # 21, 22, 24, 25: the set's alone are scored
        md = '\n'.join(lines)
        self.assertIn("places this secondary on the drawn papers the curation covers (7 of the 10 drawn); only the set's are "
                      "scored, since the values the judging used (values.json) are the set's alone", md)
        self.assertIn('Of those 7: in the set 4, left out 1, read past the target 1, never laid down 1.', md)

    def test_the_matchers_floor(self):
        """The matcher is the head-to-head's: two numbers match within 1.5% of the larger, or within 5e-7 in catalog units
        (its floor for its gold's rounding), so a slow kcat of 1.4e-6 s^-1 matches the curation's 1e-6 while 1.4e-4 does not
        match 1e-4; results.json and RESULTS.md state the whole rule."""
        v = self.val
        rows = [ee_row('51', 'ATP', kcat='0.000001 s^-1'), ee_row('51', 'GTP', kcat='0.0001 s^-1')]
        plain = [v('plain', '51', 0, 'kcat', 1.4e-6, 'ATP'), v('plain', '51', 1, 'kcat', 1.4e-4, 'GTP')]
        ev, P = self.case(plain, [], rows, {'51': 'enzyextract'}, ('51',))
        x, lines, full = self.scored(ev, P)
        self.assertEqual([(g['substrate'], g['plain']) for g in full['gold_matched_by']['plain_only']], [('ATP', 'A0-locked:51:0')])
        self.assertEqual([d['ratio'] for d in full['per_source']['plain']['similar_description_other_number']], [1.4])
        self.assertEqual(x['match_rule'], {'relative': 0.015, 'floor': SL.C.GOLD_ROUND})
        md = '\n'.join(lines)
        self.assertIn('two numbers in catalog units match when they differ by at most 1.5% of the larger, or by at most 5e-07', md)
        self.assertIn('below 3.3e-05 the tolerance is wider than 1.5%', md)

    def test_the_pre_registered_condition(self):
        """PREREGISTRATION.md uses the curation secondary only if its code was committed before triage: met when the first
        commit holding curation() is no later than triage and the code that runs is that code as committed then (an edit
        elsewhere in the file does not count); not met with nothing committed, a first commit after triage (times compared
        across time zones), or its code changed after triage, committed or not. Dropped, nothing is read or scored."""
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        P = SR.paths(Path(d.name), 'locked')
        W.write_json(P['score'] / 'private' / 'triage.json', {'time': '2026-11-12 10:00:00 -0600'})
        now = Path(SL.__file__).read_text()
        mine = now.replace('def curation_lines(x):\n', 'def curation_lines(x):  # edited\n', 1)  # the secondary's code
        other = now.replace('def set_and_limits(P, out):\n', 'def set_and_limits(P, out):  # edited\n', 1)  # the primary's
        self.assertTrue(mine != now != other)
        cond = lambda *hist, text=now: SL.curation_condition(P, ('h' * 40, list(hist)), text)  # noqa: E731
        c0 = ('c0', '2026-11-10T16:28:09-06:00', 'def report(ev, a):\n    pass')  # before the secondary
        c1 = ('c1', '2026-11-12T09:59:59-06:00', now)
        late = ('c1', '2026-11-12T16:00:01+00:00', now)  # 10:00:01 at -0600: a second after triage
        self.assertEqual((cond()['dropped'], cond(c0)['dropped']), ('its code is not committed',) * 2)
        self.assertEqual(cond(c0, late)['dropped'], 'its code was first committed after triage')
        ok = cond(c0, c1)
        self.assertEqual(ok, {'used': True, 'triage_time': '2026-11-12 10:00:00 -0600', 'first_commit': 'c1',
                              'first_commit_time': '2026-11-12T09:59:59-06:00', 'commit_at_triage': 'c1', 'kit_head': 'h' * 40,
                              'file_differs_from_head': False})
        after = '2026-11-13T09:00:00-06:00'
        self.assertTrue(cond(c0, c1, ('c2', after, other), text=other)['used'])  # the primary's code changed after triage
        self.assertEqual((cond(c0, c1, text=other)['used'], cond(c0, c1, text=other)['file_differs_from_head']), (True, True))
        changed = 'its code changed after triage (the code that runs is not the code committed when triage ran)'
        self.assertEqual(cond(c0, c1, ('c2', after, mine), text=mine)['dropped'], changed)  # committed after triage
        self.assertEqual(cond(c0, c1, text=mine)['dropped'], changed)  # or not committed at all
        line = SL.condition_line(cond(c0, late))
        for want in ('NOT met (its code was first committed after triage), so it is dropped',
                     'first committed in c1 at 2026-11-12T16:00:01+00:00', 'triage ran at 2026-11-12 10:00:00 -0600',
                     'this file as committed then: c0', "the kit's HEAD: hhhhhhhhhhhh."):
            self.assertIn(want, line)
        self.assertIn('and the report says so): met. Its code', SL.condition_line(ok))
        x, lines = SL.curation(Path(d.name), P, 50, cond(c0, late))  # no values.json and no curation: none is read
        self.assertEqual((set(x), x['dropped']), ({'judged', 'dropped', 'code'}, 'its code was first committed after triage'))
        self.assertEqual(json.loads((P['score'] / 'curation.json').read_text()), {'summary': x})
        self.assertEqual(lines[-1], 'Dropped, as the pre-registration says for this case: no number of it is computed or reported.')

    def test_code_history_reads_git(self):
        """code_history: the kit's HEAD and the commits that changed this file, oldest first, each with its committer time
        and the file as it left it; a commit that leaves the file alone is not listed, and outside a repository there is
        none (a temporary repository)."""
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        R = Path(d.name)
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}

        def git(*a, when=None):
            r = subprocess.run(['git', '-c', 'user.name=T', '-c', 'user.email=t@example.org', '-c', 'commit.gpgsign=false',
                                '-C', str(R), *a], capture_output=True, text=True,
                               env={**env, **({'GIT_COMMITTER_DATE': when, 'GIT_AUTHOR_DATE': when} if when else {})})
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout.strip()
        git('init', '-q')
        f = R / SL.SELF
        f.parent.mkdir(parents=True)
        f.write_text('def report(ev, a):\n    pass\n')
        git('add', '-A')
        git('commit', '-q', '-m', 'before the secondary', when='2026-11-10T16:28:09-06:00')
        (R / 'other.txt').write_text('x\n')
        git('add', '-A')
        git('commit', '-q', '-m', 'another file', when='2026-11-11T08:00:00-06:00')
        f.write_text('def curation(ev, P, B, code=None):\n    pass\n')
        git('commit', '-q', '-am', 'the secondary', when='2026-11-11T09:00:00-06:00')
        head, hist = SL.code_history(R)
        self.assertEqual(head, git('rev-parse', 'HEAD'))
        self.assertEqual([(t, x) for _, t, x in hist], [('2026-11-10T16:28:09-06:00', 'def report(ev, a):\n    pass'),
                                                       ('2026-11-11T09:00:00-06:00', 'def curation(ev, P, B, code=None):\n    pass')])
        self.assertEqual(hist[-1][0], head)
        self.assertEqual(SL.code_history(R / 'no such folder'), ('', []))


class A6Audit(unittest.TestCase):
    """w1_audit.py A6-<run> on a fake tree of transcripts (no session started): a redone paper is judged on its redo
    launches, redo and redo-more-<k> alike, so a break in redo-more-1 reaches rerun.txt; a paper with no PMID, whose
    task names its stand-in id after a long parenthesis, is audited (common_w1.READ_TASK; human_review's pattern missed
    the copy's, so the hard set's NPD832847D went unaudited)."""

    def test_redo_follow_up_and_a_paper_without_pmid(self):
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d) / 'kinetics-reading'
            P = W.eval_paths(ev)
            a6 = P['a6']
            saved = W.PROJECTS
            W.PROJECTS = Path(d) / 'projects'
            self.addCleanup(setattr, W, 'PROJECTS', saved)
            root = W.PROJECTS / W.project_slug(a6)
            W.write_json(P['manifest'], {'instructions_baseline': {'User': {'sha256': 'x', 'eval_words': []}}})
            (P['orders']).mkdir(parents=True)
            (P['orders'] / 'A6-locked.txt').write_text('12\n14\nNPD832847D\n')
            for sub in ('', 'redo'):
                W.write_json(P['runs'] / 'A6-locked' / sub / 'RESET.json', {'started_utc': '2026-11-01T09:00:00.000Z',
                                                                             'reset_utc': '2026-11-01T12:00:00.000Z'})
            for launch, sid in (('main', 'sm'), ('redo', 'sr'), ('redo-more-1', 'sq')):
                W.write_json(P['logs'] / 'A6-locked' / launch / 'launch.json', {'launch': launch, 'session_id': sid})
            long = f'paper (no PMID: identified by its DOI in {a6}/papers.tsv column 2)'
            clean = [('Read', {'file_path': f'{a6}/prompts/read.md'})]
            forbidden = [('Read', {'file_path': f'{W.MAIN}/catalog.jsonl'})]
            agents = {'sm': [('read:12', 'PMID 12', clean), ('verify:12', 'PMID 12', clean), ('read:14', 'PMID 14', clean),
                             ('verify:14', 'PMID 14', clean), ('read:NPD832847D', f'{long} NPD832847D', clean),
                             ('verify:NPD832847D', f'{long} NPD832847D', forbidden)],
                      'sr': [('read:12', 'PMID 12', clean)],  # the redo stopped at a usage limit
                      'sq': [('read:12', 'PMID 12', clean), ('verify:12', 'PMID 12', forbidden)]}  # its follow-up broke
            for sid, rows in agents.items():
                sub = root / sid / 'subagents' / 'workflows' / 'wf_1'
                sub.mkdir(parents=True)
                for i, (desc, who, calls) in enumerate(rows):
                    role = desc.split(':')[0]
                    fake_transcript(sub / f'agent-a{i}.jsonl', calls, cwd=str(a6),
                                    task=f'The CatLog folder is {a6}: ... Follow {a6}/prompts/{role}.md for {who}. ...')
                    (sub / f'agent-a{i}.meta.json').write_text(json.dumps({'description': desc}))
            self.assertIsNone(HR.READ_TASK.search(f'Follow {a6}/prompts/read.md for {long} NPD832847D.'))
            saved_argv = sys.argv
            sys.argv = ['w1_audit.py', 'A6-locked', '--eval', str(ev), '--projects', str(root)]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    AU.main()
            finally:
                sys.argv = saved_argv
            out = json.loads((P['audit'] / 'A6-locked' / 'audit.json').read_text())
            got = {(r['label'], r['launch']) for r in out['agents'] if r['pmid']}
            self.assertIn(('verify:NPD832847D', 'main'), got)  # found by its task, stand-in id and all
            self.assertEqual(out['summary']['papers_without_reader_or_verifier'], [])
            self.assertEqual(out['summary']['papers_read_again_after_a_model_switch'], ['12'])
            # 12 judged on redo and redo-more-1 (its verifier's break there counts); NPD832847D's verifier broke too
            self.assertEqual((P['audit'] / 'A6-locked' / 'rerun.txt').read_text().split(), ['12', 'NPD832847D'])
            self.assertEqual(sorted({r['pmid'] for r in W.a6_judged(out['agents']) if r['launch'] == 'main'}),
                             ['14', 'NPD832847D'])  # 12's main agents are not what it is judged on


class ScanJudges(unittest.TestCase):
    """scan_judges.py: a full-record judging's content scan finds what a judge must not have seen, by content."""

    def test_hits_and_a_clean_session(self):
        import scan_judges as SJ
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d)
            P = W.eval_paths(ev, 'locked')
            lg = P['logs'] / 'adjudication_locked'
            lg.mkdir(parents=True)
            cwd = P['adj'] / W.code(W.judge_label('j1', 'locked')) / '11'
            own = f'/{W.PROJECTS}/{W.project_slug(cwd)}/abc/tool-results/x.txt'.replace('//', '/')
            clean = [('Read', {'file_path': str(cwd / 'paper.txt')}, None, 'the paper'),
                     ('Write', {'file_path': str(P['verdicts']['j1'] / '11.c01.json')}, None, 'ok'),
                     ('Bash', {'command': 'cat big'}, None, f'Output too large, saved to {own}')]
            dirty = [('Read', {'file_path': str(W.eval_paths(ev)['adj'] / '12' / 'paper.txt')}, None, 'text'),
                     ('Read', {'file_path': '/tmp/x'}, None, '{"pmid": "99", "verdicts": []}'),
                     ('Read', {'file_path': '/tmp/y'}, None, '{"claim_id": "k1", "source_shown": "plain"}')]
            for name, calls, pm in (('11.c01.j1.a1.json', clean, '11'), ('12.c01.j1.a1.json', dirty, '12')):
                c = P['adj'] / W.code(W.judge_label('j1', 'locked')) / pm
                tr = fake_transcript(ev / f'{name}.jsonl', calls, cwd=str(c))
                W.write_json(lg / name, {'transcript': str(tr), 'cwd': str(c), 'out': str(P['verdicts']['j1'] / f'{pm}.c01.json')})
            n, hits = SJ.scan(ev, 'locked')
            self.assertEqual(n, 2)
            self.assertFalse([h for h in hits if h['record'].startswith('11.')])  # its own folder, output and notice
            kinds = {h['hit'].split(' (')[0] for h in hits if h['record'].startswith('12.')}
            self.assertEqual(kinds, {"first judges' folders", "another paper's pmid", 'a hidden field'})


class FollowUp(unittest.TestCase):
    """run_a6.py: a follow-up launch does not read again a paper the copy finished (it would be read twice inside one
    kept run), unless --force; a set after the W1 rounds is launched only on the frozen copy (the other tests have no
    copy: the pin is open for them); a launch killed on the way is completed by --recover, read only."""

    def setUp(self):
        self.real_pin = W.a6_pin_problems
        W.a6_pin_problems = lambda ev, repo=None: []
        self.addCleanup(setattr, W, 'a6_pin_problems', self.real_pin)

    def test_pin_checked_at_every_launch(self):
        """run_a6.py hard and locked (the dry run too) refuse unless catlog-copy's HEAD and MANIFEST.json's
        a6.pipeline_commit_stamp are the commit the tag names; a W1 label is not pinned."""
        import run_a6 as RA6
        W.a6_pin_problems = self.real_pin
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d) / 'kinetics-reading'
            P = W.eval_paths(ev)
            a6 = fake_copy(P['a6'])
            head = subprocess.run(['git', '-C', str(a6), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
            (a6 / W.RUN_MARK).write_text('2026-11-10T12:00:00.000Z\n')
            for lab in ('locked', 'hard', 'pilot'):
                W.write_json(P['orders'] / f'A6-{lab}.args.json', {'pmids': ['1'], 'lanes': 3, 'root': str(a6)})
            W.write_json(P['manifest'], {'a6': {'pipeline_commit_stamp': head[:12]}})
            saved = W.freeze_stamp
            W.freeze_stamp = lambda repo=None: head[:12]  # the tag names the copy's snapshot
            self.addCleanup(setattr, W, 'freeze_stamp', saved)

            def launch(label):
                saved_argv = sys.argv
                sys.argv = ['run_a6.py', label, '--dry-run', '--eval', str(ev)]
                try:
                    with contextlib.redirect_stdout(io.StringIO()) as out:
                        RA6.main()
                    return out.getvalue()
                finally:
                    sys.argv = saved_argv
            for lab in ('locked', 'hard'):
                self.assertIn('"launch": "main"', launch(lab))
            W.write_json(P['manifest'], {'a6': {'pipeline_commit_stamp': '0123456789ab'}})  # a freeze moved the manifest
            for lab in ('locked', 'hard'):
                with self.assertRaises(SystemExit) as e:
                    launch(lab)
                self.assertIn('a6.pipeline_commit_stamp is 0123456789ab', str(e.exception))
            W.write_json(P['manifest'], {'a6': {'pipeline_commit_stamp': head[:12]}})
            W.freeze_stamp = lambda repo=None: 'fb0cf1758951'  # the copy was moved off the tag's snapshot
            with self.assertRaises(SystemExit) as e:
                launch('locked')
            self.assertIn(f'catlog-copy is at {head[:12]}', str(e.exception))
            self.assertIn('"launch": "main"', launch('pilot'))  # W1's runs are not pinned to the later tag
            self.assertFalse((P['logs'] / 'A6-locked').exists())  # a dry run writes nothing

    def test_recover_a_killed_launch(self):
        """A launch killed on the way: reset-a6 refuses until run_a6.py --recover has written its agents.json (rebuilt
        from its session's transcripts), its papers' model_switch.json outcomes (a killed redo's papers are no longer
        redo_pending for good; a switch in it excludes) and the rest of its launch.json; nothing else is touched. A
        session that ran and whose transcript is gone cannot be accounted for; one that never started recovers to no
        agents, with no outcome written."""
        import run_a6 as RA6
        import w1_setup as SU
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d) / 'kinetics-reading'
            P = W.eval_paths(ev)
            saved = W.PROJECTS
            W.PROJECTS = Path(d) / 'projects'
            self.addCleanup(setattr, W, 'PROJECTS', saved)
            logs = P['logs'] / 'A6-locked'
            W.write_json(logs / W.MODEL_SWITCH_FILE, {p_: {'pmid': p_, 'outcome': 'redo_pending'} for p_ in ('12', '14')})
            red = logs / 'redo'
            tr = W.PROJECTS / W.project_slug(P['a6']) / 'sess-5.jsonl'
            W.write_json(red / 'launch.json', {'launch': 'redo', 'pmids': ['12', '14'], 'cwd': str(P['a6']), 'session_id': 'sess-5',
                                               'transcript': str(tr), 'start': '2026-11-10 08:00:00 -0600'})
            (red / 'session.json').write_text('')  # the CLI writes its result at the end: killed before it
            fake_session(W.PROJECTS, P['a6'], 'sess-5', [('read:12', W.MODEL), ('verify:12', 'claude-opus-5'),
                                                          ('read:14', W.MODEL), ('verify:14', W.MODEL)])
            self.assertEqual(SU.unfinished_launches(ev, 'locked'), ['redo'])
            with self.assertRaises(SystemExit) as e:  # reset-a6 refuses while the launch is not recovered
                SU.cmd_reset_a6(ev, 'locked')
            self.assertIn('--recover', str(e.exception))
            self.assertFalse((P['runs'] / 'A6-locked').exists())  # nothing moved
            with contextlib.redirect_stdout(io.StringIO()):
                RA6.recover(ev, 'locked', 'redo')
            rows = json.loads((red / 'agents.json').read_text())
            self.assertEqual(sorted(r['label'] for r in rows if r['pmid']), ['read:12', 'read:14', 'verify:12', 'verify:14'])
            self.assertTrue(all(r['rebuilt'] for r in rows))
            sw = W.read_switches(logs)
            self.assertEqual((sw['12']['outcome'], sw['14']['outcome']), ('excluded', 'second_try_ok'))
            rec = json.loads((red / 'launch.json').read_text())
            self.assertTrue(rec['recovered'] and rec['session_started'])
            self.assertEqual((rec['agents'], rec['switched_agents']), (4, ['verify:12 claude-opus-5']))
            self.assertEqual(SU.unfinished_launches(ev, 'locked'), [])
            with self.assertRaises(SystemExit) as e:  # seen to the end now: nothing to recover
                RA6.recover(ev, 'locked', 'redo')
            self.assertIn('nothing to recover', str(e.exception))
            gone = logs / 'more-1'  # it ran (the CLI wrote to session.err) and its transcript is gone: not accounted for
            W.write_json(gone / 'launch.json', {'launch': 'more-1', 'pmids': ['13'], 'cwd': str(P['a6']), 'session_id': 'sess-6',
                                                'transcript': str(W.PROJECTS / W.project_slug(P['a6']) / 'sess-6.jsonl')})
            (gone / 'session.json').write_text('')
            (gone / 'session.err').write_text('Error: the session stopped\n')
            self.assertIsNone(RA6.launch_agents(gone))
            with self.assertRaises(SystemExit) as e:
                RA6.recover(ev, 'locked', 'more-1')
            self.assertIn('cannot be accounted for', str(e.exception))
            (gone / 'session.err').write_text('')  # launched files left empty: the session never started
            self.assertEqual(RA6.launch_agents(gone), [])
            with contextlib.redirect_stdout(io.StringIO()):
                RA6.recover(ev, 'locked', 'more-1')
            self.assertEqual(json.loads((gone / 'agents.json').read_text()), [])
            self.assertNotIn('13', W.read_switches(logs))  # no session, no outcome
            self.assertFalse(json.loads((gone / 'launch.json').read_text())['session_started'])

    def test_finished_papers_refused(self):
        import contextlib, io
        import run_a6 as RA6
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d) / 'kinetics-reading'
            P = W.eval_paths(ev)
            W.write_json(P['orders'] / 'A6-locked.args.json', {'pmids': ['1', '2'], 'lanes': 3, 'root': str(P['a6'])})
            (P['logs'] / 'A6-locked' / 'main').mkdir(parents=True)
            W.write_tsv(P['a6'] / 'papers.tsv', [{'pmid': '1', 'status': 'done'}, {'pmid': '2', 'status': 'reading'}],
                        ['pmid', 'status'])

            def launch(*args):
                saved = sys.argv
                sys.argv = ['run_a6.py', 'locked', *args, '--dry-run', '--eval', str(ev)]
                try:
                    with contextlib.redirect_stdout(io.StringIO()) as out:
                        RA6.main()
                    return out.getvalue()
                finally:
                    sys.argv = saved
            with self.assertRaises(SystemExit) as e:
                launch('--pmids', '1', '2')
            self.assertIn("['1 (done)']", str(e.exception))
            self.assertIn('"launch": "more-1"', launch('--pmids', '2'))
            out = json.loads(launch('--pmids', '1', '2', '--force'))
            self.assertEqual((out['launch'], out['force'], out['read_again']), ('more-1', True, ['1']))
            self.assertFalse((P['logs'] / 'A6-locked' / 'more-1').exists())  # a dry run writes nothing

    def test_launch_record_before_the_session(self):
        """launch.json (session id, transcript, papers) is on record before the session starts, so a launch killed on
        the way can be accounted for; a --force follow-up records force and the finished papers it reads again. No
        session is started: the launcher stops where it would start one."""
        import types
        import run_a6 as RA6
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d) / 'kinetics-reading'
            P = W.eval_paths(ev)
            logs = P['logs'] / 'A6-locked'
            W.write_json(P['orders'] / 'A6-locked.args.json', {'pmids': ['1', '2'], 'lanes': 3, 'root': str(P['a6'])})
            P['a6'].mkdir(parents=True)
            (P['a6'] / W.RUN_MARK).write_text('2026-11-10T12:00:00.000Z\n')
            W.write_tsv(P['a6'] / 'papers.tsv', [{'pmid': '1', 'status': 'done'}, {'pmid': '2', 'status': 'reading'}],
                        ['pmid', 'status'])

            class Stopped(Exception):
                pass
            seen = []

            def popen(cmd, **k):  # where the session would start: what is on record then
                seen.append({f.parent.name: json.loads(f.read_text()) for f in logs.glob('*/launch.json')})
                raise Stopped()
            fake = types.SimpleNamespace(Popen=popen, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired,
                                         run=lambda *a, **k: types.SimpleNamespace(returncode=0, stdout='', stderr=''))
            saved = (RA6.subprocess, RA6.S.versions, sys.argv)
            RA6.subprocess, RA6.S.versions = fake, lambda *a, **k: None
            try:
                for args in ([], ['--pmids', '1', '2', '--force']):
                    sys.argv = ['run_a6.py', 'locked', *args, '--eval', str(ev)]
                    with self.assertRaises(Stopped):
                        RA6.main()
            finally:
                RA6.subprocess, RA6.S.versions, sys.argv = saved
            main, more = seen[0]['main'], seen[1]['more-1']
            self.assertEqual((main['pmids'], main['launch']), (['1', '2'], 'main'))
            self.assertTrue(main['session_id'] and main['transcript'].endswith(main['session_id'] + '.jsonl'))
            self.assertNotIn('force', main)
            self.assertEqual((more['force'], more['read_again'], more['pmids']), (True, ['1'], ['1', '2']))
            self.assertEqual(RA6.launch_agents(logs / 'main'), [])  # named, but no transcript: it never started
            self.assertFalse((logs / 'main' / 'agents.json').exists())


class Redo(unittest.TestCase):
    """The redo path for papers the workflow's Sonnet retry read or verified in part (the rules-only check, 2026-11-10):
    after reset-a6 hard, run_a6.py hard --redo --pmids P reads them again in the fresh copy although no switch made them
    pending, reset-a6 hard --redo keeps that redo, and the statuses, rows and agents the scorers take for them are the
    redo's (score_w1.load_rows, common_w1.a6_kept_agents, as score_today.py reads them). It serves a retry no refusal
    started ('catlog retry on another model'); a paper an Opus refusal sent to the retry stays 'refused (catlog)' after
    its redo, as a refused plain session is never sent again (common_w1.a6_refused reads every launch of its state)."""

    def setUp(self):
        saved = W.a6_pin_problems  # no frozen copy here: the pin is FollowUp.test_pin_checked_at_every_launch's
        W.a6_pin_problems = lambda ev, repo=None: []
        self.addCleanup(setattr, W, 'a6_pin_problems', saved)

    def test_redo_of_papers_the_retry_read(self):
        import run_a6 as RA6
        import w1_setup as SU
        with tempfile.TemporaryDirectory() as d:
            ev, main = Path(d) / 'kinetics-reading', Path(d) / 'main'
            P, logs, pm = W.eval_paths(ev), W.eval_paths(ev)['logs'] / 'A6-hard', ['91000001', '91000002']
            main.mkdir()
            (main / 'papers.tsv').write_text('pmid\tdoi\ttitle\tstatus\ttext_source\n' + ''.join(
                f'{p_}\t10.1/{p_}\tPaper {p_}\ttodo\tjats:{main}/papers/{p_}.jats.xml\n' for p_ in pm))
            saved = (SU.M, W.TMP, W.CLAUDE_TMP)
            SU.M, W.TMP, W.CLAUDE_TMP = main, Path(d) / 'tmp', Path(d) / 'claude-tmp'  # no real scratch is touched
            self.addCleanup(lambda: [setattr(SU, 'M', saved[0]), setattr(W, 'TMP', saved[1]), setattr(W, 'CLAUDE_TMP', saved[2])])
            W.write_json(P['orders'] / 'A6-hard.args.json', {'pmids': pm, 'lanes': 3, 'root': str(P['a6'])})
            (P['orders'] / 'A6-hard.txt').write_text(''.join(p_ + '\n' for p_ in pm))
            a6 = fake_copy(P['a6'])
            # the run as its launches left it: 91000001's reader was refused on Opus, 91000002's died with no refusal (an
            # API error), and the Sonnet retry read each again
            W.write_json(logs / 'main' / 'agents.json', [agent('read:91000001', refusals=1), agent('read-sonnet:91000001'),
                                                         agent('verify:91000001'), agent('read:91000002'),
                                                         agent('read-sonnet:91000002'), agent('verify:91000002'), LAUNCH_ROW])
            W.write_json(logs / W.MODEL_SWITCH_FILE, {})
            (a6 / 'catalog.jsonl').write_text(''.join(json.dumps({'pmid': p_, 'v': 'main'}) + '\n' for p_ in pm))
            for f in ('rejected.jsonl', 'bounds.jsonl', 'log.tsv'):
                (a6 / f).write_text('')
            W.write_tsv(a6 / 'papers.tsv', [{'pmid': p_, 'status': 'done'} for p_ in pm], ['pmid', 'status'])
            (a6 / 'work').mkdir()
            (a6 / W.RUN_MARK).write_text('2026-11-09T12:51:00.000Z\n')
            state = W.a6_state_agents(ev, 'hard')
            kept = W.a6_kept_agents(ev, 'hard', state)
            self.assertTrue(W.a6_refused(state['91000001']))  # before the redo: refused, the retry it started ran
            self.assertFalse(W.a6_refused(state['91000002']))  # no refusal started its retry: operational, redone on Opus
            self.assertEqual(W.a6_retried(kept['91000002'][1]), ['read-sonnet:91000002 ' + W.RETRY_MODEL])
            with contextlib.redirect_stdout(io.StringIO()):
                SU.cmd_reset_a6(ev, 'hard')

            def launch(*args):
                saved_argv = sys.argv
                sys.argv = ['run_a6.py', 'hard', *args, '--dry-run', '--eval', str(ev)]
                try:
                    with contextlib.redirect_stdout(io.StringIO()) as out:
                        RA6.main()
                    return out.getvalue()
                finally:
                    sys.argv = saved_argv
            with self.assertRaises(SystemExit) as e:  # nothing switched: the papers are named
                launch('--redo')
            self.assertIn('no paper waits for a redo', str(e.exception))
            out = json.loads(launch('--redo', '--pmids', *pm))
            self.assertEqual(out['launch'], 'redo')
            self.assertIn('"pmids": ["91000001", "91000002"]', out['launch_line'])
            # what the redo launch leaves: its records, its agents on Opus, and the fresh copy's add
            W.write_json(logs / 'redo' / 'launch.json', {'launch': 'redo', 'pmids': pm, 'session_id': 's'})
            W.write_json(logs / 'redo' / 'agents.json', [agent(f'{r}:{p_}') for p_ in pm for r in ('read', 'verify')] + [LAUNCH_ROW])
            RA6.record_models(logs, 'redo', pm, json.loads((logs / 'redo' / 'agents.json').read_text()))
            (a6 / 'catalog.jsonl').write_text(''.join(json.dumps({'pmid': p_, 'v': 'redo'}) + '\n' for p_ in pm))
            W.write_tsv(a6 / 'papers.tsv', [{'pmid': p_, 'status': 'done'} for p_ in pm], ['pmid', 'status'])
            with contextlib.redirect_stdout(io.StringIO()):
                SU.cmd_reset_a6(ev, 'hard', redo=True)
            self.assertEqual(json.loads((P['runs'] / 'A6-hard' / 'redo' / 'RESET.json').read_text())['pmids'], pm)
            self.assertEqual({p_: W.read_switches(logs)[p_]['outcome'] for p_ in pm}, dict.fromkeys(pm, 'second_try_ok'))
            state = W.a6_state_agents(ev, 'hard')
            kept = W.a6_kept_agents(ev, 'hard', state)
            self.assertEqual((kept['91000001'][0], kept['91000002'][0]), ('redo', 'redo'))
            self.assertEqual([x[0] for x in state['91000001']], ['main', 'redo'])  # its state: main's launch and the redo
            self.assertTrue(W.a6_refused(state['91000001']))  # main's refusal stands: no second try on the copy's side
            self.assertFalse(W.a6_refused(state['91000002']) or W.a6_retried(kept['91000002'][1]))  # read on Opus now
            self.assertEqual(W.a6_other_model(ev, 'hard', kept), {})
            rows, status = SC.load_rows(ev, 'A6', 'hard', pm)
            self.assertEqual(status, {'91000001': 'ok', '91000002': 'ok'})
            self.assertEqual(sorted((r['pmid'], r['v']) for r in rows), [('91000001', 'redo'), ('91000002', 'redo')])


class ScanReads(unittest.TestCase):
    """scan_reads.py: the locked set's plain and copy sessions scanned by content for the owner's downloads, other
    groups' answer keys, the main folder's catalogue and other locked papers in a result."""

    def test_hits_and_clean_sessions(self):
        import scan_reads as SN
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d)
            P = W.eval_paths(ev)
            P['orders'].mkdir(parents=True)
            (P['orders'] / 'locked_draw.txt').write_text('11111\n22222\n33333\n')
            lg = P['logs'] / 'A0-locked'
            lg.mkdir(parents=True)
            own = W.out_dir(ev, 'A0-locked')
            dl = str(S.DOWNLOADS)
            clean = [('Bash', {'command': f'ls {own}'}, None, '11111.json\n22222.json\n33333.json'),  # names in a listing
                     ('Read', {'file_path': str(P['plain'] / '11111' / 'paper.txt')}, None, 'kcat 5 s-1 (PMID 99999)')]
            dirty = [('Bash', {'command': 'ls ~/Downloads/data'}, None, 'x'),
                     ('Bash', {'command': 'python3 walk.py'}, None, f'{dl}/data/rumble_a_dev1.parquet'),
                     ('Read', {'file_path': str(own / '33333.json')}, None, '{"pmid": "33333", "rows": []}'),
                     ('Bash', {'command': 'python3 look.py'}, None, f'{W.MAIN}/catalog.jsonl: 1 row'),
                     ('Bash', {'command': 'python3 more.py'}, None, 'sources/db_values.tsv: 12 rows')]
            for pm, calls in (('11111', clean), ('22222', dirty)):
                tr = fake_transcript(ev / f'{pm}.jsonl', calls, cwd=str(P['plain'] / pm))
                W.write_json(lg / f'{pm}.a1.json', {'transcript': str(tr), 'cwd': str(P['plain'] / pm)})
            tr = fake_transcript(ev / 'x.jsonl', [('Bash', {'command': 'ls ~/Documents/catlog-v2'}, None, 'x'),
                                                  ('Bash', {'command': 'python3 walk.py'}, None,  # the old catalogue
                                                   f'{W.REALKCAT}/data/verified_catlog.jsonl: 159446 rows')],
                                 cwd=str(P['plain'] / '33333'))  # the main folder named another way
            W.write_json(lg / '33333.a1.json', {'transcript': str(tr), 'cwd': str(P['plain'] / '33333')})
            prompt = f'Never open database values (sources/db_values.tsv, catlog_wide.*); not {W.MAIN}'  # read.md's own words
            copy_clean = fake_transcript(ev / 'c1.jsonl', [
                ('Bash', {'command': 'head catlog.py'}, None, 'catlog.py file [DAYS]  file downloads: ~/Downloads/PMID<id>_*'),
                ('Read', {'file_path': str(P['a6'] / 'prompts' / 'read.md')}, None, prompt),
                ('Bash', {'command': 'ls work'}, None, '11111.prompts.json 33333.read.json')])
            copy_dirty = fake_transcript(ev / 'c2.jsonl', [('Bash', {'command': 'grep -rn kcat texts'}, None,
                                                           'texts/11111.txt:12: kcat 5'),
                                                          ('Bash', {'command': 'head ../catlog-v2/catlog_wide.csv'}, None, 'x'),
                                                          ('Bash', {'command': 'ls $HOME/Documents/catlog-v2/work'}, None, 'x'),
                                                          ('Read', {'file_path': f'{W.REALKCAT}/data/verified_catlog.jsonl'},
                                                           None, 'x')])
            W.write_json(P['logs'] / 'A6-locked' / 'main' / 'agents.json', [
                {**agent('read:33333'), 'transcript': str(copy_clean)}, {**agent('verify:33333'), 'transcript': str(copy_dirty)},
                LAUNCH_ROW])
            saved = W.PROJECTS
            W.PROJECTS = ev / 'projects'
            self.addCleanup(setattr, W, 'PROJECTS', saved)
            more = P['logs'] / 'A6-locked' / 'more-1'  # killed on the way: its agents come from its session's transcripts
            more.mkdir(parents=True)
            fake_session(W.PROJECTS, P['a6'], 'sess-3', [('read:11111', W.MODEL)])
            W.write_json(more / 'launch.json', {'launch': 'more-1', 'cwd': str(P['a6']), 'session_id': 'sess-3',
                                                'transcript': str(W.PROJECTS / W.project_slug(P['a6']) / 'sess-3.jsonl')})
            (P['logs'] / 'A6-locked' / 'more-2').mkdir()
            (P['logs'] / 'A6-locked' / 'more-2' / 'session.json').write_text('')  # a session nothing names
            gone = P['logs'] / 'A6-locked' / 'more-3'  # it ran (its result on record) and its transcript is gone
            W.write_json(gone / 'launch.json', {'launch': 'more-3', 'cwd': str(P['a6']), 'session_id': 'sess-4',
                                                'transcript': str(W.PROJECTS / W.project_slug(P['a6']) / 'sess-4.jsonl')})
            (gone / 'session.json').write_text('{"type": "result", "is_error": false}\n')
            res = SN.scan(ev, 'locked')
            n, hits = res['A0-locked']
            self.assertEqual(n, 3)
            self.assertFalse([h for h in hits if h['record'].startswith('11111')])  # its own paper, names in a listing
            self.assertEqual(sorted({h['hit'] for h in hits if h['record'].startswith('22222')}),
                             sorted(['named Downloads', f'named {dl}', 'named rumble_', "another locked paper's pmid (33333)",
                                     'named catlog-v2/catalog', 'named Documents/catlog-v2', 'named db_values']))
            self.assertEqual({h['hit'] for h in hits if h['record'].startswith('33333')},
                             {'named Documents/catlog-v2', 'named Documents/realkcat'})  # realkcat in a result, too
            n, hits = res['A6-locked']
            self.assertEqual(n, 3)  # the copy's agents: catlog.py's help and read.md name ~/Downloads, db_values, catlog_wide
            self.assertEqual(sorted((h['record'], h['hit']) for h in hits),  # main and realkcat in its inputs, not in read.md
                             [('main/verify:33333', "another locked paper's pmid (11111)"),
                              ('main/verify:33333', 'named Documents/catlog-v2'), ('main/verify:33333', 'named Documents/realkcat'),
                              ('main/verify:33333', 'named catlog_wide'), ('more-2', 'agents not accounted for'),
                              ('more-3', 'agents not accounted for')])


class People(unittest.TestCase):
    def test_cleared_kind(self):
        import build_people_list as BPL
        r = {'pmid': '21149620', 'status': 'rejected', 'bucket': 'v2_has_same', 'category': 'substrate'}
        self.assertEqual(BPL.verdict_kind(r), 'rejected_dispute')  # how the sample was drawn
        self.assertEqual(BPL.verdict_kind(r, BPL.cleared_papers()), 'rejected_cleared')  # the scorer's key
        self.assertTrue({'21149620', '3191146', '33020946'} <= BPL.cleared_papers())

    def test_costs_one_counting(self):
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d)
            for lab, rows in (('A2-pilot', [{'pmid': '1', 'total': 300}, {'pmid': '1', 'total': 300},
                                            {'pmid': '1', 'total': 400}]),
                              ('A6-pilot', [{'pmid': '1', 'total': 500}, {'pmid': '1', 'total': 500}])):
                W.write_json(W.eval_paths(ev)['audit'] / lab / 'tokens.json', rows)
            c = SC.costs(ev, [('A2', 'pilot'), ('A6', 'pilot')])
            self.assertEqual(c['A2']['tokens'], 1000)
            self.assertEqual(c['A6']['tokens'], 1000)
            self.assertEqual(c['A2']['method'], c['A6']['method'])


FAKE_CLI = r"""#!/usr/bin/env python3
# a stand-in for `claude -p` (test_w1.Runners): writes a Claude Code-shaped transcript and the step's file as
# $HOME/plan.json says for the n-th call on that output: ok, switch (a second model and a fallback line), fail (no file)
import json, os, re, sys
from pathlib import Path
if '--version' in sys.argv:
    print('2.1.309 (Claude Code)'); sys.exit(0)
a = sys.argv[1:]
model, sid = a[a.index('--model') + 1], a[a.index('--session-id') + 1]
prompt = sys.stdin.read()
home, cwd = Path(os.environ['HOME']), os.getcwd()
out = re.search(r'Write (\S+\.json)', prompt).group(1)
plan = json.loads((home / 'plan.json').read_text())
cf = home / 'counts.json'
counts = json.loads(cf.read_text()) if cf.exists() else {}
n = counts.get(out, 0)
counts[out] = n + 1
cf.write_text(json.dumps(counts))
steps = plan.get(Path(out).parent.name + '/' + Path(out).name, ['ok'])
what = steps[min(n, len(steps) - 1)]
models = [model] + (['claude-opus-5'] if what == 'switch' else [])
lines = [{'type': 'user', 'cwd': cwd, 'version': '2.1.309', 'message': {'role': 'user', 'content': prompt}}]
for i, m in enumerate(models):
    if i:
        lines.append({'type': 'system', 'subtype': 'model_refusal_fallback', 'cwd': cwd, 'trigger': 'refusal',
                      'scope': 'session', 'originalModel': model, 'fallbackModel': m, 'apiRefusalCategory': 'bio'})
    lines.append({'type': 'assistant', 'cwd': cwd, 'version': '2.1.309', 'timestamp': '2026-11-01T10:0%d:00.000Z' % i,
                  'message': {'id': 'm%d' % i, 'model': m, 'role': 'assistant', 'content': [{'type': 'text', 'text': 'x'}],
                              'usage': {'input_tokens': 10, 'output_tokens': 5}}})
tr = home / '.claude' / 'projects' / re.sub(r'[^A-Za-z0-9]', '-', cwd) / (sid + '.jsonl')
tr.parent.mkdir(parents=True, exist_ok=True)
tr.write_text(''.join(json.dumps(x) + '\n' for x in lines))
pmid = re.search(r'(\d{6,9})', Path(out).name).group(1)
if what != 'fail':
    if 'lists claimed values' in prompt:
        claims = json.loads(Path(re.search(r'(\S+\.json) lists claimed values', prompt).group(1)).read_text())
        body = {'verdicts': [{'id': c['id'], 'verdict': 'supported'} for c in claims]}
    else:
        body = {'pmid': pmid, 'model': models[-1], 'note': '', 'rows': [
            {'metric': 'kcat', 'value': 1.5, 'unit': 's^-1', 'raw_value': '1.5', 'raw_unit': 's-1', 'enzyme': 'E',
             'organism': 'O', 'variant': 'wild type', 'substrate': 'S', 'cosubstrate': '', 'pH': None,
             'temperature_C': None, 'conditions': '', 'location': 'Table 1'}]}
    Path(out).write_text(json.dumps(body))
print(json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': what, 'num_turns': 1,
                  'total_cost_usd': 0.0, 'usage': {'input_tokens': 10, 'output_tokens': 5},
                  'modelUsage': {m: {} for m in models}}))
"""


class Runners(unittest.TestCase):
    """Review of the dry-run fixes: the once-more rule through the runners themselves (run_plain, run_reconcile,
    run_adjudicate main()), with run_session's real transcript reading on transcripts a fake `claude` writes."""

    def setUp(self):
        import contextlib, io
        self.tmp = tempfile.TemporaryDirectory(prefix='kr')
        root = Path(self.tmp.name).resolve()
        self.home, self.ev = root / 'home', root / 'tree'
        self.home.mkdir()
        cli = root / 'bin' / 'claude'
        cli.parent.mkdir()
        cli.write_text(FAKE_CLI)
        cli.chmod(0o755)
        self.saved = (W.CLI, os.environ.get('HOME'), sys.argv)
        W.CLI = str(cli)
        os.environ['HOME'] = str(self.home)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        P = W.eval_paths(self.ev)
        self.P = P
        for p in ('1000001', '1000002', '1000003', '1000004', '1000005', '1000006', '1000007'):
            for base in (P['plain'], P['adj']):
                (base / p).mkdir(parents=True)
                (base / p / 'paper.txt').write_text('Table 1 kcat 1.5 s-1')
        P['validator'].write_text((HERE / 'validate_plain.py').read_text())

    def tearDown(self):
        W.CLI, home, sys.argv = self.saved
        if home is None:
            os.environ.pop('HOME', None)
        else:
            os.environ['HOME'] = home
        self.tmp.cleanup()

    def plan(self, d):
        (self.home / 'plan.json').write_text(json.dumps(d))

    def run_main(self, mod, *args):
        sys.argv = [mod.__file__, *args, '--eval', str(self.ev), '--lanes', '1']
        with self.quiet:
            mod.main()

    def out(self, arm, part, p):
        f = W.out_file(self.ev, arm, 'dry', part, p)
        return f'{f.parent.name}/{f.name}'

    def test_plain_reconcile_adjudicate(self):
        import run_adjudicate as RA
        logs = self.P['logs']
        o = lambda p: self.out('A0', None, p)
        self.plan({o('1000001'): ['ok'], o('1000002'): ['switch', 'ok'], o('1000003'): ['switch', 'switch'],
                   o('1000004'): ['fail', 'ok'], o('1000005'): ['switch', 'fail', 'ok']})
        self.run_main(RP, '--arm', 'A0', '--run', 'dry', '--pmids', '1000001', '1000002', '1000003', '1000004', '1000005')
        sw = W.read_switches(logs / 'A0-dry')
        self.assertEqual({k: v['outcome'] for k, v in sw.items()},
                         {'1000002': 'second_try_ok', '1000003': 'excluded', '1000005': 'second_try_failed'})
        a0 = logs / 'A0-dry'
        for f in ('1000002.a1.json', '1000002.a1b.json', '1000002.a1.1000002.json', '1000003.a1.json', '1000003.a1b.json',
                  '1000004.a1.json', '1000004.a2.json', '1000005.a1.json', '1000005.a1b.json', '1000005.a2.json'):
            self.assertTrue((a0 / f).exists(), f)  # every attempt's record kept; the switched try's file set aside
        self.assertEqual(json.loads((a0 / '1000004.a2.json').read_text())['model'], W.RETRY_MODEL)
        self.assertFalse(json.loads((a0 / '1000004.a2.json').read_text())['switched'])  # the planned retry: no switch
        self.assertTrue(json.loads((a0 / '1000002.a1.json').read_text())['switched'])
        self.assertFalse(W.out_file(self.ev, 'A0', 'dry', None, '1000003').exists())  # excluded: nothing scored
        rows, status = SC.load_rows(self.ev, 'A0', 'dry', ['1000001', '1000002', '1000003', '1000004', '1000005'])
        self.assertEqual(status, {'1000001': 'ok', '1000002': 'ok', '1000003': 'model_switch', '1000004': 'ok',
                                  '1000005': 'ok'})
        # the same command again: valid outputs and the excluded step are skipped (no session runs)
        self.plan({})
        (self.home / 'counts.json').unlink()
        self.run_main(RP, '--arm', 'A0', '--run', 'dry', '--pmids', '1000001', '1000002', '1000003', '1000004', '1000005')
        self.assertFalse((self.home / 'counts.json').exists())  # the fake claude never ran
        self.assertEqual(len(list(a0.glob('1000002.a*.json'))), 3)
        # a step that switched before and runs again (--force): its earlier records move to earlier/, and the next
        # switch is its second (excluded at once, no third try)
        self.plan({o('1000002'): ['switch']})
        self.run_main(RP, '--arm', 'A0', '--run', 'dry', '--pmids', '1000002', '--force')
        sw = W.read_switches(a0)
        self.assertEqual(sw['1000002']['outcome'], 'excluded')
        self.assertEqual(sw['1000002']['history'][0]['outcome'], 'second_try_ok')
        self.assertTrue((a0 / 'earlier' / '1000002' / '1' / '1000002.a1b.json').exists())
        self.assertFalse((a0 / '1000002.a1b.json').exists())  # no once-more this time
        self.assertEqual(len([r for r in AU.plain_records(a0) if r[2]]), 2)  # the audit sees the earlier sessions too
        # A2: a read that switched twice fails its paper-run (no reconcile); a reconcile that switched once is redone
        r = lambda part, p: self.out('A2', part, p)
        self.plan({r('readA', '1000006'): ['switch', 'switch'], r('final', '1000001'): ['switch', 'ok']})
        (self.home / 'counts.json').unlink()
        self.run_main(RP, '--arm', 'A2', '--run', 'dry', '--pmids', '1000001', '1000006')
        self.run_main(RC, '--run', 'dry', '--pmids', '1000001', '1000006')
        sw = W.read_switches(logs / 'A2-dry')
        self.assertEqual(sw['1000006.readA']['outcome'], 'excluded')
        self.assertEqual(sw['1000001.final']['outcome'], 'second_try_ok')
        flags = json.loads((logs / 'A2-dry' / 'reconcile_flags.json').read_text())
        self.assertIn('switched model twice', flags['1000006'])
        self.assertFalse(W.out_file(self.ev, 'A2', 'dry', 'final', '1000006').exists())
        rows, status = SC.load_rows(self.ev, 'A2', 'dry', ['1000001', '1000006'])
        self.assertEqual(status, {'1000001': 'ok', '1000006': 'model_switch'})
        # adjudication: a judge that switched twice leaves its paper out
        Q = W.eval_paths(self.ev, 'dry')
        for p in ('1000001', '1000007'):
            W.write_json(Q['claims'] / f'{p}.c01.json', [{'id': 'aa', 'metric': 'kcat'}, {'id': 'bb', 'metric': 'Km'}])
        v = lambda j, p: f"{Q['verdicts'][j].name}/{p}.c01.json"
        self.plan({v('j2', '1000007'): ['switch', 'switch'], v('j1', '1000001'): ['switch', 'ok']})
        (self.home / 'counts.json').unlink()
        self.run_main(RA, '--runs', 'dry')
        adj = logs / 'adjudication_dry'
        self.assertEqual(W.switch_excluded(adj), {'1000007': ['1000007.c01.j2']})
        self.assertEqual(W.read_switches(adj)['1000001.c01.j1']['outcome'], 'second_try_ok')
        self.assertTrue((Q['verdicts']['j1'] / '1000001.c01.json').exists())


class ReviewAudit(unittest.TestCase):
    """Review of the dry-run fixes: what the audit now also catches, and what stays clean."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.saved = AU.EXISTS

    def tearDown(self):
        AU.EXISTS = self.saved
        self.tmp.cleanup()

    def test_paths_written_otherwise(self):
        home = str(Path.home())
        np_ = lambda cmd, cwd='/home/x/kinetics-reading/papers/1': AU.named_paths('Bash', {'command': cmd}, cwd)
        self.assertIn(f'{home}/Documents/catlog-v2/catalog.jsonl', np_('cat $HOME/Documents/catlog-v2/catalog.jsonl'))
        self.assertIn(f'{home}/k/x.tsv', np_('head "${HOME}/k/x.tsv"'))
        self.assertIn('/home/s/catlog-v2/work/1.read.json', np_('cat //home/s/catlog-v2/work/1.read.json'))
        self.assertEqual(np_('node -e "// a comment"'), [])
        self.assertIn('/home/s/out/1.json', AU.named_paths('Write', {'file_path': '/tmp/x-1-a.py',
                                                                       'content': "open('/home/s/out/1.json')"}, '/x'))
        self.assertEqual(AU.named_paths('Write', {'file_path': '/tmp/x-1-a.json', 'content': "/home/s/out/1.json"}, '/x'),
                         ['/private/tmp/x-1-a.json'])  # a data file's text is not a path list
        AU.EXISTS = lambda p: p == '/home/x/kinetics-reading/papers/2/paper.txt'
        got = np_('cd /home/x/kinetics-reading/papers && head 2/paper.txt && sed s/a/b/ 3/none.txt')
        self.assertEqual(got, ['/home/x/kinetics-reading/papers', '/home/x/kinetics-reading/papers/2/paper.txt'])
        self.assertIn('/home/x/kinetics-reading/papers/2/paper.txt', np_('cd .. && cat 2/paper.txt'))
        self.assertEqual(np_("cd /tmp && sed -e 's/<[^>]*>/ /g' x | awk '{print $1/1000}'"), ['/private/tmp'])
        # locked set, 11 Nov: a '../' token is read from where the command has cd'd to, not from the session's cwd
        a6 = '/home/x/k/catlog-copy'
        got = np_('cd /home/x/k/catlog-copy/tools && grep -n "^def numbers" ../catlog.py', a6)
        self.assertIn(f'{a6}/catlog.py', got)
        self.assertNotIn('/home/x/k/catlog.py', got)
        got = np_(f"cd {a6}/tools && python3 -c \"import json; json.load(open('../work/1.read.json'))\"", a6)
        self.assertIn(f'{a6}/work/1.read.json', got)
        self.assertNotIn('/home/x/k/work/1.read.json', got)
        self.assertIn('/home/x/kinetics-reading/papers/out/2.json', np_('cat ../out/2.json'))  # no cd: the cwd
        self.assertIn('/home/x/kinetics-reading/out/2.json', np_('cd .. && cat ../out/2.json'))  # after cd ..: one more up
        self.assertIn('/home/x/kinetics-reading/papers/out/2.json', np_('cd /tmp/q && cd - && cat ../out/2.json'))  # cd -
        self.assertIn('/a/x', np_('cd /a/b && cd /c/d && cd - && cat ../x'))
        self.assertIn('/c/x', np_('cd /a/b && cd /c/d && cd - && cd - && cat ../x'))
        self.assertEqual(AU.named_paths('Glob', {'pattern': '../124/*.txt'}, '/home/x/kinetics-reading/papers/123'),
                         ['/home/x/kinetics-reading/papers/124'])  # a pattern's '../' is read from the cwd
        # review of the cd fix: a '../' is also read from the cwd whenever that names an existing path, since the cd the
        # audit sees may not have happened; the cd segment's own '../' tokens and options are read too
        keys = '/home/x/k/records/keys/A6-locked.json'
        AU.EXISTS = lambda q: q == keys
        for cmd in ('cd figs 2>/dev/null; cat ../records/keys/A6-locked.json',
                    'cd figs || cat ../records/keys/A6-locked.json', '(ls; cd tools); cat ../records/keys/A6-locked.json',
                    'cd tools & cat ../records/keys/A6-locked.json',
                    "cd /tmp/v-1 && cat > c.py <<'EOF'\nprint(open('../records/keys/A6-locked.json').read())\nEOF"):
            self.assertIn(keys, np_(cmd, a6), cmd)
        self.assertIn('/home/x/k/records/keys', np_('cd -P ../records/keys && cat A6-locked.json', a6))
        self.assertIn('/home/x/k/records/keys', np_('cd -- ../records/keys && ls', a6))
        self.assertNotIn(str(Path.home()), np_("python3 - <<'EOF'\ncd = 'tools'\nEOF", a6))  # 'cd =' is no cd
        AU.EXISTS = lambda q: False
        got = np_('cd /home/x/k/catlog-copy/tools && grep -n "^def numbers" ../catlog.py', a6)  # the recorded case
        self.assertEqual([q for q in got if q.endswith('catlog.py')], [f'{a6}/catlog.py'])
        self.assertIn('/home/s/y', AU.named_paths('Write', {'file_path': '/tmp/x-1-a.py',
                                                                                    'content': "open('../y')"}, '/home/s/x'))

    def test_git_history(self):
        for cmd in ('git log --oneline -5', 'git -C /a/b log -1', 'git --no-pager show HEAD', 'cat .git',
                    'ls -la && git branch -a', 'cat ../catlog-copy/.git/HEAD'):
            self.assertTrue(AU.GIT_PEEK.search(cmd), cmd)
        for cmd in ('git status --short', 'cat .gitignore', 'python3 catlog.py add 1 2', 'grep -n logit x.py'):
            self.assertFalse(AU.GIT_PEEK.search(cmd), cmd)
        tr = fake_transcript(self.d / 't.jsonl', [('Bash', {'command': 'git log --oneline -3'})])
        res, _ = AU.audit_agent(tr, [W.MODEL], ['/'], '/x')
        self.assertIn(('break', 'git_history', 'git log --oneline -3'), res['violations'])
        res, _ = AU.audit_agent(tr, [W.MODEL], ['/'], '/x', git_level='note')
        self.assertIn(('note', 'git_history', 'git log --oneline -3'), res['violations'])

    def test_context_and_instructions(self):
        git = {'type': 'attachment', 'attachment': {'type': 'session_context', 'context': {
            'userEmail': 'x', 'gitStatus': 'Recent commits:\nfacd218 W1 review: every eval part but a6/ and plain/'}}}
        clean = {'type': 'attachment', 'attachment': {'type': 'session_context', 'context': {'userEmail': 'x'}}}
        instr = lambda extra='': {'type': 'attachment', 'attachment': {'type': 'instructions', 'files': [
            {'path': '/m/MEMORY.md', 'type': 'AutoMem', 'content': '- plan: head-to-head + gold set' + extra},
            {'path': '/c/CLAUDE.md', 'type': 'Project', 'content': '134 experiments'}]}}
        base = {'AutoMem': {'sha256': W.text_sha('- plan: head-to-head + gold set'), 'eval_words': ['gold set', 'head-to-head']},
                'Project': {'sha256': W.text_sha('134 experiments'), 'eval_words': ['experiments']}}
        audit = lambda extra: AU.audit_agent(fake_transcript(self.d / 't.jsonl', [], extra=extra), [W.MODEL], [], '/x',
                                             baseline=base)[0]['violations']
        v = audit([git])
        self.assertTrue(any(x[:2] == ('break', 'eval_word') and x[2].startswith('context session_context') for x in v), v)
        self.assertEqual(audit([clean, instr()]), [])  # production's own words, as at setup
        v = audit([instr('\n- [W1 kill test](w1.md)')])
        self.assertTrue(any(x[:2] == ('break', 'eval_word') and 'AutoMem' in x[2] and 'kill test' in x[2] for x in v), v)
        self.assertIn(('note', 'instructions_changed', 'AutoMem /m/MEMORY.md'), v)
        # a plain session or an adjudicator is shown no instruction file at all
        res, _ = AU.audit_agent(fake_transcript(self.d / 'p.jsonl', [], extra=[instr()]), [W.MODEL], [], '/x')
        self.assertIn(('break', 'instructions', 'AutoMem /m/MEMORY.md'), res['violations'])

    def test_launch_session(self):
        args = {'pmids': ['1'], 'lanes': 9, 'root': '/home/x/kinetics-reading/catlog-copy'}
        tr = fake_transcript(self.d / 'l.jsonl', [('Workflow', {'name': 'catlog-batch', 'args': args}),
                                                  ('Bash', {'command': 'python3 catlog.py add 1'})])
        self.assertEqual(AU.launch_findings(tr, args), [])
        tr = fake_transcript(self.d / 'm.jsonl', [('Workflow', {'name': 'catlog-batch', 'args': {**args, 'lean': True}}),
                                                  ('Edit', {'file_path': '/home/x/kinetics-reading/catlog-copy/work/1.read.json'})])
        got = {v[1] for v in AU.launch_findings(tr, args)}
        self.assertEqual(got, {'launch_workflow', 'launch_edit'})
        ev, a6 = '/home/x/kinetics-reading', '/home/x/kinetics-reading/catlog-copy'
        v = AU.launch_paths([('break', 'path', ev), ('break', 'path', ev + '/A6_LAUNCH.md'), ('break', 'path', '/home/x'),
                             ('break', 'network', 'curl x'), ('break', 'forbidden', 'catlog-v2/work/')], ev, a6)
        self.assertEqual(sorted(v), [('break', 'forbidden', 'catlog-v2/work/'), ('break', 'path', ev),
                                     ('break', 'path', ev + '/A6_LAUNCH.md'), ('note', 'network', 'curl x'),
                                     ('note', 'path', '/home/x')])

    def test_a6_env_and_marker(self):
        import run_a6 as RA6
        self.assertEqual(RA6.ENV_SET.get('CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS'), '1')
        self.assertEqual(RA6.ENV_SET.get('CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK'), '1')
        self.assertEqual(RA6.ENV_SET.get('CLAUDE_CODE_DISABLE_AUTO_MEMORY'), '1')  # memory off, as the plain arms
        self.assertEqual(S.ENV_SET.get('CLAUDE_CODE_DISABLE_AUTO_MEMORY'), '1')
        self.assertFalse(W.eval_word_hits('/' + W.RUN_MARK))
        self.assertTrue(W.eval_word_hits('/' + W.OLD_RUN_MARK))

    def test_a6_memory_off(self):
        """A6's instruction baseline is the owner's and CatLog's CLAUDE.md; main's memory index shown to an A6 agent
        breaks (memory off since 2026-11-01), and so does any instruction type the baseline lacks."""
        self.assertEqual(set(W.instruction_files_a6(self.d)), {'User', 'Project'})
        base = {'User': {'sha256': W.text_sha('u'), 'eval_words': []},
                'Project': {'sha256': W.text_sha('134 experiments'), 'eval_words': ['experiments']}}
        files = lambda *extra: {'type': 'attachment', 'attachment': {'type': 'instructions', 'files': [
            {'path': '/h/.claude/CLAUDE.md', 'type': 'User', 'content': 'u'},
            {'path': '/c/CLAUDE.md', 'type': 'Project', 'content': '134 experiments'}, *extra]}}
        audit = lambda line: AU.audit_agent(fake_transcript(self.d / 'a.jsonl', [], extra=[line]), [W.MODEL], [], '/x',
                                            baseline=base)[0]['violations']
        self.assertEqual(audit(files()), [])
        mem = {'path': '/m/memory/MEMORY.md', 'type': 'AutoMem', 'content': '- [Site round 6](x.md)'}
        self.assertIn(('break', 'instructions', 'AutoMem /m/memory/MEMORY.md'), audit(files(mem)))
        self.assertIn(('break', 'instructions', 'Local /c/CLAUDE.local.md'),
                      audit(files({'path': '/c/CLAUDE.local.md', 'type': 'Local', 'content': 'x'})))

    def test_a6_agent_rows(self):
        import run_a6 as RA6
        saved = W.PROJECTS
        W.PROJECTS = self.d / 'projects'
        try:
            a6, sid = Path('/home/x/kinetics-reading/catlog-copy'), 'sess-1'
            sub = W.PROJECTS / W.project_slug(a6) / sid / 'subagents' / 'workflows' / 'wf_1'
            sub.mkdir(parents=True)
            task = lambda role, p: f'Follow {a6}/prompts/{role}.md for PMID {p}. The paper text is ...'
            for name, desc, calls, extra in (
                    ('a1', 'read:111', [('Read', {}, W.MODEL), ('Read', {}, 'claude-opus-5')], [FALLBACK]),
                    ('a2', 'verify:111', [('Read', {}, W.MODEL)], []),
                    ('a3', 'read:222', [('Read', {}, W.MODEL)], []),
                    ('a4', 'verify-sonnet:222', [('Read', {}, W.RETRY_MODEL)], [])):
                fake_transcript(sub / f'agent-{name}.jsonl', calls, task=task('verify' if 'verify' in desc else 'read',
                                                                               desc.split(':')[1]), extra=extra)
                (sub / f'agent-{name}.meta.json').write_text(json.dumps({'description': desc}))
            fake_transcript(W.PROJECTS / W.project_slug(a6) / f'{sid}.jsonl', [('Bash', {}, W.MODEL)])
            rows = RA6.agent_rows(a6, sid)
            by = {r['label']: r for r in rows}
            self.assertTrue(by['read:111']['switched'])
            self.assertFalse(by['verify-sonnet:222']['switched'])  # the workflow's retry, on its own model
            self.assertEqual(by['verify-sonnet:222']['launched'], W.RETRY_MODEL)
            self.assertEqual(by['launch']['role'], 'launch')
            d = RA6.record_models(self.d / 'logs', 'main', ['111', '222'], rows)
            self.assertEqual({k: v['outcome'] for k, v in d.items()}, {'111': 'redo_pending'})
        finally:
            W.PROJECTS = saved


class Snapshot(unittest.TestCase):
    """catlog-copy at an orphan snapshot commit (the owner's decision, 2026-11-01), as a folder with its own repository
    (the independent check after it: a worktree of main showed main's branches and the kit's commits to git log --all
    and git branch -a): the same branch commit always gives the same snapshot, which holds only the files A6_SPARSE
    selects; a first setup makes the folder; setup --move-a6 makes an earlier kind (a sparse worktree named a6 at a
    branch commit, or a worktree named catlog-copy at the snapshot) again without losing a data file; a harness change
    later moves the same repository to the next snapshot. All in a temporary repository."""

    def git(self, *a, cwd=None, ok=True):
        r = subprocess.run(['git', '-c', 'user.name=T', '-c', 'user.email=t@example.org', '-c', 'commit.gpgsign=false',
                            '-C', str(cwd or self.R), *a], capture_output=True, text=True,
                           env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def setUp(self):
        import w1_setup as SU
        self.SU = SU
        self.tmp = tempfile.TemporaryDirectory()
        d = self.d = Path(self.tmp.name).resolve()
        self.R = d / 'main'
        self.R.mkdir()
        self.git('init', '-q')
        claim = ('import json, pathlib\n\ndef claim_prompts(p):\n    pathlib.Path(\'work\', p + \'.prompts.json\').write_text('
                 'json.dumps({\'read.md\': pathlib.Path(\'prompts/read.md\').read_text()}) + \'\\n\')\n')
        self.harness = {'catlog.py': claim, 'tools/units.py': 'x = 1\n', 'prompts/read.md': 'read\n',
                        'prompts/verify.md': 'verify\n', '.claude/settings.json': '{}\n',
                        '.claude/workflows/catlog-batch.js': '// batch\n', '.claude/agents/catlog-reader.md': 'reader\n',
                        'CLAUDE.md': 'CatLog\n', 'config.json': '{}\n', 'sources/natural_forms.tsv': 'a\n',
                        'sources/nopmid_refs.tsv': 'b\n'}
        other = {'tools/w1/kit.py': '# W1 kill test kit\n', 'sources/other.tsv': 'c\n',
                 'catalog.jsonl': '{"production": 1}\n', 'papers.tsv': 'pmid\tstatus\n1\tdone\n',
                 '.gitignore': 'texts/\npapers/\nwork/\n', 'paper/planning/plan.md': 'the W1 kill test plan\n'}
        for k, v in {**self.harness, **other}.items():
            (self.R / k).parent.mkdir(parents=True, exist_ok=True)
            (self.R / k).write_text(v)
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'W1 kit: the kill test harness')
        self.c1 = self.git('rev-parse', 'HEAD')
        (self.R / 'tools/w1/kit.py').write_text('# W1 kill test kit, fixed\n')
        self.git('commit', '-q', '-am', 'W1 kit: a fix in the kit only')
        self.c2 = self.git('rev-parse', 'HEAD')
        self.ev = d / 'kinetics-reading'
        self.P = W.eval_paths(self.ev)
        self.P['records'].mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def old_layout(self):
        """catlog-copy as the kit made it before 2026-11-01: a sparse worktree named a6 at the branch commit, with the
        kit's data files (one over a tracked production path) and an untracked file inside a harness folder."""
        tmp_a6 = self.d / 'a6'
        self.git('worktree', 'add', '--detach', '--no-checkout', str(tmp_a6), self.c1)
        self.git('sparse-checkout', 'set', '--no-cone', *self.SU.A6_SPARSE, cwd=tmp_a6)
        self.git('checkout', '--detach', self.c1, cwd=tmp_a6)
        a6 = self.P['a6']
        self.git('worktree', 'move', str(tmp_a6), str(a6))
        data = {'catalog.jsonl': '', 'rejected.jsonl': '', 'papers.tsv': 'pmid\tstatus\n1\treading\n',
                'texts/1.txt': 'paper one\n', 'papers/1.pdf': '%PDF one\n', 'work/1.prompts.json': '{"read.md": "x"}\n',
                W.RUN_MARK: '2026-11-01T16:13:00.000Z\n', '.claude/settings.local.json': '{"permissions": {}}\n',
                'tools/__pycache__/units.pyc': 'pyc\n'}
        for k, v in data.items():
            (a6 / k).parent.mkdir(parents=True, exist_ok=True)
            (a6 / k).write_text(v)
        self.assertIn('/worktrees/a6', (a6 / '.git').read_text())
        return a6, data

    def wt_layout(self):
        """catlog-copy as the owner's decision first made it (2026-11-01, 11:15): a worktree of main named catlog-copy
        at the snapshot, with the kit's data files."""
        snap = self.SU.snapshot_commit(self.c1, self.R)
        a6 = self.P['a6']
        self.git('worktree', 'add', '--detach', str(a6), snap['commit'])
        data = {'catalog.jsonl': '', 'rejected.jsonl': '', 'papers.tsv': 'pmid\tstatus\n1\treading\n',
                'texts/1.txt': 'paper one\n', 'papers/1.pdf': '%PDF one\n', 'work/1.prompts.json': '{"read.md": "x"}\n',
                W.RUN_MARK: '2026-11-01T16:13:00.000Z\n', '.claude/settings.local.json': '{"permissions": {}}\n'}
        for k, v in data.items():
            (a6 / k).parent.mkdir(parents=True, exist_ok=True)
            (a6 / k).write_text(v)
        self.assertTrue((a6 / '.git').read_text().strip().endswith('/.git/worktrees/catlog-copy'))
        return a6, data, snap

    def own_and_neutral(self, a6, head):
        """catlog-copy has its own repository holding `head` alone: git there shows nothing of the temporary main
        repository (its branch and its commit subjects, which name the kit), and main lists no worktree for it."""
        self.assertTrue((a6 / '.git').is_dir() and self.SU.own_repository(a6))
        self.assertEqual(self.git('log', '--all', '--format=%H', cwd=a6), head)
        self.assertEqual(self.git('for-each-ref', cwd=a6), '')
        branches = self.git('branch', '-a', cwd=a6)
        self.assertTrue(len(branches.splitlines()) == 1 and branches.startswith('* ('), branches)  # detached, no branch
        self.assertEqual(self.git('worktree', 'list', '--porcelain', cwd=a6).count('worktree '), 1)
        self.assertEqual(self.git('reflog', cwd=a6, ok=False), '')
        self.assertEqual(self.git('remote', cwd=a6), '')
        seen = '\n'.join(self.git(*c, cwd=a6, ok=False) for c in (('log', '--all'), ('branch', '-a'), ('worktree', 'list'),
                                                                  ('status',), ('config', '--local', '--list')))
        self.assertEqual(W.eval_word_hits(seen), [])
        self.assertNotIn('kill', seen.lower())
        self.assertFalse(any((a6 / '.git' / n).exists() for n in ('hooks', 'logs', 'description', 'info')))
        self.assertEqual(self.git('worktree', 'list', '--porcelain').count('worktree '), 1)  # main lists itself only
        self.assertEqual(self.git('rev-parse', '--show-toplevel', cwd=a6), str(a6))  # catlog.git_commit's check
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=no', cwd=a6), '')

    def test_snapshot(self):
        SU = self.SU
        s1 = SU.snapshot_commit(self.c1, self.R)
        self.assertEqual(SU.snapshot_commit(self.c1, self.R)['commit'], s1['commit'])  # the same base, the same commit
        self.assertEqual(SU.snapshot_hash(self.c1, s1['tree'], self.R), s1['commit'])  # computed without writing
        self.assertEqual(SU.snapshot_tree(self.c2, self.R)[0], s1['tree'])            # a kit-only change: same files
        obj = self.git('cat-file', '-p', s1['commit'])
        self.assertNotIn('\nparent ', obj)
        self.assertTrue(obj.endswith('\n\ncatlog snapshot'), obj)
        self.assertEqual(sorted(self.git('ls-tree', '-r', '--name-only', s1['commit']).split('\n')), sorted(self.harness))
        self.assertEqual(self.git('for-each-ref', '--contains', s1['commit']), '')  # no ref or branch points at it
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.c2)                    # the main worktree is untouched
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertTrue(SU.in_snapshot('tools/units.py') and not SU.in_snapshot('tools/w1/kit.py'))
        self.assertFalse(SU.in_snapshot('catalog.jsonl') or SU.in_snapshot('sources/other.tsv'))

    def test_recreate_keeps_data_then_moves(self):
        SU = self.SU
        a6, data = self.old_layout()
        before = {k: (a6 / k).read_bytes() for k in data}
        with self.assertRaises(SystemExit):  # the earlier kind is made again only with --move-a6
            SU.a6_checkout(self.ev, self.c2, False, self.R)
        snap = SU.a6_checkout(self.ev, self.c2, True, self.R)
        self.assertEqual(snap['branch_commit'], self.c1)  # catlog-copy's own commit held the same files
        self.assertEqual(snap['commit'], SU.snapshot_commit(self.c1, self.R)['commit'])
        self.assertEqual(Path(snap['repository']), (a6 / '.git').resolve())
        self.own_and_neutral(a6, snap['commit'])
        self.assertFalse((self.R / '.git' / 'worktrees' / 'a6').exists())  # the old worktree is gone
        self.assertEqual({k: (a6 / k).read_bytes() for k in data}, before)  # every data file kept
        self.assertEqual(self.git('log', '--format=%H %s', cwd=a6), f"{snap['commit']} catlog snapshot")
        status = self.git('status', cwd=a6)
        self.assertEqual(W.eval_word_hits(status), [])
        self.assertNotIn(self.c1[:7], status)
        self.assertEqual(self.git('config', '--get', 'core.sparseCheckout', cwd=a6, ok=False), '')
        self.assertFalse((a6 / 'tools' / 'w1').exists() or (a6 / 'paper').exists())
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=no', cwd=a6), '')
        rec = list((self.P['records'] / 'worktrees').glob('a6-*'))
        self.assertEqual(len(rec), 1)
        self.assertTrue(json.loads((rec[0] / 'RECREATED.json').read_text())['removed'])
        self.assertTrue((rec[0] / 'logs' / 'HEAD').exists() and (rec[0] / 'info' / 'sparse-checkout').exists())
        self.assertEqual(list(self.P['records'].glob('catlog-copy-before-*')), [])
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.c2)  # the main worktree is untouched
        self.assertEqual(self.git('status', '--porcelain'), '')
        m = {'commit': self.c2, 'commit12': self.c2[:12], 'a6': {'head': snap['commit'], 'snapshot': snap}}
        problems, _ = SU.a6_git_problems(a6, m, self.R)
        self.assertEqual(problems, [])
        # setup again with no manifest: the snapshot is found again by its hash, nothing changes
        self.assertEqual(SU.a6_checkout(self.ev, self.c2, False, self.R)['commit'], snap['commit'])
        # a harness change: the same worktree moves to the next snapshot (git checkout), data files stay
        (self.R / 'prompts/read.md').write_text('read, fixed\n')
        self.git('commit', '-q', '-am', 'prompt fix')
        c3 = self.git('rev-parse', 'HEAD')
        with self.assertRaises(SystemExit):
            SU.a6_checkout(self.ev, c3, False, self.R)
        snap3 = SU.a6_checkout(self.ev, c3, True, self.R)
        self.assertEqual(snap3['branch_commit'], c3)
        self.assertEqual(self.git('log', '--format=%H', cwd=a6), snap3['commit'])
        self.own_and_neutral(a6, snap3['commit'])  # the earlier snapshot is unreachable: git log --all lists the new one
        self.assertEqual((a6 / 'prompts' / 'read.md').read_text(), 'read, fixed\n')
        self.assertEqual({k: (a6 / k).read_bytes() for k in data if k != 'work/1.prompts.json'},
                         {k: v for k, v in before.items() if k != 'work/1.prompts.json'})
        m = {'commit': c3, 'commit12': c3[:12], 'a6': {'head': snap3['commit'], 'snapshot': snap3}}
        self.assertEqual(SU.a6_git_problems(a6, m, self.R)[0], [])
        # a read on file and another harness change: refused (reset-a6 first)
        (a6 / 'work' / '1.read.json').write_text('{}')
        (self.R / 'prompts/verify.md').write_text('verify, fixed\n')
        self.git('commit', '-q', '-am', 'verify fix')
        with self.assertRaises(SystemExit):
            SU.a6_checkout(self.ev, self.git('rev-parse', 'HEAD'), True, self.R)

    def test_fresh_own_repository(self):
        SU = self.SU
        a6 = self.P['a6']
        snap = SU.a6_checkout(self.ev, self.c2, False, self.R)  # a first setup: no --move-a6 needed
        self.assertEqual(snap['branch_commit'], self.c2)
        self.assertEqual(snap['commit'], SU.snapshot_commit(self.c2, self.R)['commit'])
        self.own_and_neutral(a6, snap['commit'])
        self.assertEqual(SU.files_under(a6), sorted(self.harness))
        m = {'commit': self.c2, 'commit12': self.c2[:12], 'a6': {'head': snap['commit'], 'snapshot': snap}}
        self.assertEqual(SU.a6_git_problems(a6, m, self.R)[0], [])
        self.assertEqual(SU.a6_checkout(self.ev, self.c2, False, self.R)['commit'], snap['commit'])  # again: unchanged

    def test_worktree_made_own_repository(self):
        SU = self.SU
        a6, data, s1 = self.wt_layout()
        seen = self.git('log', '--all', '--oneline', cwd=a6) + '\n' + self.git('branch', '-a', cwd=a6)
        self.assertIn('w1', W.eval_word_hits(seen))  # what an agent saw in the worktree: the kit's commit subjects
        m = {'commit': self.c2, 'commit12': self.c2[:12], 'a6': {'head': s1['commit'], 'snapshot': s1}}
        problems = ' '.join(SU.a6_git_problems(a6, m, self.R)[0])
        for want in ('not its own repository', 'git log --all in catlog-copy lists', 'refs', 'other folders',
                     'evaluation words'):
            self.assertIn(want, problems)
        before = {k: (a6 / k).read_bytes() for k in data}
        with self.assertRaises(SystemExit):  # made again only with --move-a6
            SU.a6_checkout(self.ev, self.c2, False, self.R)
        snap = SU.a6_checkout(self.ev, self.c2, True, self.R)
        self.assertEqual(snap['commit'], s1['commit'])  # the same snapshot: the same pipeline_commit stamp
        self.own_and_neutral(a6, snap['commit'])
        self.assertEqual({k: (a6 / k).read_bytes() for k in data}, before)  # every data file kept
        self.assertFalse((self.R / '.git' / 'worktrees' / 'catlog-copy').exists())
        rec = list((self.P['records'] / 'worktrees').glob('catlog-copy-*'))
        self.assertEqual(len(rec), 1)
        self.assertTrue(json.loads((rec[0] / 'RECREATED.json').read_text())['removed'])
        self.assertTrue((rec[0] / 'HEAD').exists() and (rec[0] / 'gitdir').exists())
        self.assertEqual(list(self.P['records'].glob('catlog-copy-before-*')), [])
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.c2)  # the main worktree is untouched
        self.assertEqual(self.git('status', '--porcelain'), '')
        m['a6'] = {'head': snap['commit'], 'snapshot': snap}
        self.assertEqual(SU.a6_git_problems(a6, m, self.R)[0], [])

    def test_freeze_keeps_the_locked_snapshot(self):
        """Once a set after the W1 rounds is laid down (records/a6_inputs_<label>.json: the hard set, whose redo needs the
        same snapshot; records/orders/A6-locked.args.json), neither freeze nor setup --move-a6 (a6_checkout) moves
        catlog-copy off the snapshot the tag catlog-freeze-20261109 names, unless --force; a freeze that keeps the
        snapshot, one back onto the tag's, or one before any such set is not refused."""
        SU = self.SU
        self.git('checkout', '-q', '-b', 'w1-eval')
        snap = SU.a6_checkout(self.ev, self.c2, False, self.R)
        self.git('tag', W.FREEZE_TAG, snap['commit'])  # the main repository's tag on the copy's snapshot
        a6 = self.P['a6']
        W.write_json(self.P['manifest'], {'a6': {'head': snap['commit'], 'snapshot': snap}, 'commit12': self.c2[:12],
                                          'inputs': {}, 'orders': {}, 'keys': {}, 'people_rounds': [1]})
        (self.R / 'prompts/read.md').write_text('read, fixed\n')  # a harness change: freeze would cut a new snapshot
        self.git('commit', '-q', '-am', 'prompt fix')
        c3 = self.git('rev-parse', 'HEAD')
        new = SU.snapshot_commit(c3, self.R)['commit']
        W.write_json(self.P['records'] / 'a6_inputs_hard.json', {'papers': {}})  # the hard set laid down: no locked order yet

        class Made(Exception):
            pass

        def manifest(*a, **k):  # freeze has moved catlog-copy when it writes the manifest again
            raise Made()
        saved = (W.REPO, SU.M, SU.manifest)
        W.REPO, SU.M, SU.manifest = self.R, self.R, manifest
        try:
            with self.assertRaises(SystemExit) as e:
                SU.cmd_freeze(self.ev)
            self.assertIn('a6_inputs_hard.json exists', str(e.exception))
            self.assertIn(f'the snapshot {snap["commit"][:12]} (the tag {W.FREEZE_TAG})', str(e.exception))
            self.assertEqual(self.git('rev-parse', 'HEAD', cwd=a6), snap['commit'])  # not moved
            with self.assertRaises(SystemExit) as e:  # nor by setup --move-a6, which moves it through a6_checkout
                SU.a6_checkout(self.ev, c3, True, self.R)
            self.assertIn('a6_inputs_hard.json exists', str(e.exception))
            self.assertEqual(self.git('rev-parse', 'HEAD', cwd=a6), snap['commit'])
            (self.P['records'] / 'a6_inputs_hard.json').unlink()
            W.write_json(self.P['orders'] / 'A6-locked.args.json', {'pmids': ['1'], 'lanes': 3, 'root': str(a6)})
            with self.assertRaises(SystemExit) as e:
                SU.cmd_freeze(self.ev)
            self.assertIn('A6-locked.args.json exists', str(e.exception))
            with self.assertRaises(Made):
                SU.cmd_freeze(self.ev, force=True)
            self.assertEqual(self.git('rev-parse', 'HEAD', cwd=a6), new)
            # back onto the tag's snapshot: the kit commit before the prompt fix cuts it again, and that move is allowed
            self.assertEqual(SU.freeze_move_refused(self.ev, new, snap['commit'], repo=self.R), '')
            SU.a6_checkout(self.ev, self.c2, True, self.R)
            self.assertEqual(self.git('rev-parse', 'HEAD', cwd=a6), snap['commit'])
        finally:
            W.REPO, SU.M, SU.manifest = saved
        self.assertEqual(SU.freeze_move_refused(self.ev, new, new, repo=self.R), '')  # the snapshot stays: never refused
        self.assertIn('A6-locked.args.json exists', SU.freeze_move_refused(self.ev, snap['commit'], new, repo=self.R))
        (self.P['orders'] / 'A6-locked.args.json').unlink()
        self.assertEqual(SU.freeze_move_refused(self.ev, snap['commit'], new, repo=self.R), '')  # before any later set

    def test_git_view_problems(self):
        SU = self.SU
        a6, _ = self.old_layout()
        m = {'commit': self.c2, 'commit12': self.c2[:12],
             'a6': {'head': self.c1, 'snapshot': {**SU.snapshot_commit(self.c1, self.R)}}}
        problems = ' '.join(SU.a6_git_problems(a6, m, self.R)[0])
        for want in ('is not the snapshot', 'in git log in catlog-copy', "its git folder's name", 'sparse checkout',
                     'does not hold exactly', 'not its own repository', 'git log --all in catlog-copy lists'):
            self.assertIn(want, problems)


import human_review as HR  # noqa: E402  (tools/, on the path for w1_audit)


class CopyFolderRules(unittest.TestCase):
    """FREEZE.md F3 in tools/human_review.py (moved here from tools/test_blind_check.py by the review of the dry-run
    fixes, so that no file in catlog-copy names the evaluation): an agent whose task names a CatLog copy
    (~/Documents/kinetics-reading/catlog-copy/) must not open the main folder's reads or the folders next to its own;
    production agents may use the main folder's work/ as always. (The gold-file names and the first layout's folders are
    the audit's own pattern: w1_audit.FORBIDDEN_A6.)"""
    EVAL = 'Follow <the kit folder>/catlog-copy/prompts/read.md for PMID 12345.'
    PROD = 'Follow <the CatLog folder>/prompts/read.md for PMID 12345.'

    def found(self, task, command=None, **inp):
        call = {'type': 'tool_use', 'name': 'Bash' if command is not None else 'Read',
                'input': {'command': command, **inp} if command is not None else inp}
        return sorted(set(HR.forbidden_for(task).findall(HR._named(call))))

    def test_main_folder_reads(self):
        for path, hit in (('<the CatLog folder>/catalog.jsonl', 'catlog-v2/catalog.jsonl'),
                          ('<the CatLog folder>/work/12345.read.json', 'catlog-v2/work/'),
                          ('<the CatLog folder>/papers.tsv', 'catlog-v2/papers.tsv'),
                          ('<the CatLog folder>/paper/01_agents.md', 'catlog-v2/paper/')):
            self.assertEqual(self.found(self.EVAL, file_path=path), [hit])
            self.assertEqual(self.found(self.PROD, file_path=path), [])  # production: its own folder

    def test_gold_and_eval_parts(self):
        self.assertEqual(self.found(self.EVAL, 'grep 12345 ~/Documents/catlog-v2/work/top_journal_20261021/benchmarks/x.csv'),
                         ['catlog-v2/work/'])
        self.assertEqual(self.found(self.EVAL, 'ls <the kit folder>/out/'),
                         ['kinetics-reading/out'])
        self.assertEqual(self.found(self.EVAL, file_path='<the kit folder>/records/keys/x.tsv'),
                         ['kinetics-reading/records'])
        self.assertEqual(self.found(self.EVAL, 'cat <the kit folder>/papers/12345/paper.txt'),
                         ['kinetics-reading/papers'])

    def test_own_folder_and_original_are_fine(self):
        self.assertEqual(self.found(self.EVAL, 'python3 <the kit folder>/catlog-copy/catlog.py show 12345'), [])
        self.assertEqual(self.found(self.EVAL, file_path='<the kit folder>/catlog-copy/work/12345.read.json'), [])
        self.assertEqual(self.found(self.EVAL, 'pdftoppm -r 200 -f 3 -l 3 -png '
                                               '<the kit folder>/catlog-copy/papers/12345.pdf /tmp/p12345'), [])


if __name__ == '__main__':
    unittest.main()
