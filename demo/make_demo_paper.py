"""Write one made-up paper into a CatLog folder: its text, a reader's file and a verifier's file, in the formats
prompts/read.md and prompts/verify.md describe. `catlog.py add` then runs the code checks on it with no agent, no
API key and no network. The paper holds six right values, two values with planted errors that the code checks must
refuse although the verifier confirmed them, and a Ki read as a Km that the verifier rejects.

usage: python3 -I -B demo/make_demo_paper.py CATLOG_FOLDER      (run_demo.sh calls it on a temporary copy)
"""
import json
import os
import sys
import time
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
import catlog  # noqa: E402

PMID = '99999901'
TEXT = """Demo kinetics of FooA, an invented enzyme (synthetic text for a code test)

Results. FooA was assayed at pH 7.5 and 25 °C.

=== Table 1: Kinetic parameters of FooA variants with ATP (pH 7.5, 25 °C)
Enzyme | Substrate | kcat (s-1) | Km (µM) | kcat/Km (M-1 s-1)
FooA wild type | ATP | 12.3 ± 0.4 | 45 ± 3 | 2.7 × 10^5
FooA Y123F | ATP | 0.50 ± 0.02 | 60 ± 5 | 8.3 × 10^3
TABLE FOOT: Values are means ± SD of three experiments.

=== Table 2: Inhibition of FooA wild type
Inhibitor | Ki (mM)
ADP | 0.8 ± 0.1
"""
WT = 'FooA wild type | ATP | 12.3 ± 0.4 | 45 ± 3 | 2.7 × 10^5'
MUT = 'FooA Y123F | ATP | 0.50 ± 0.02 | 60 ± 5 | 8.3 × 10^3'
base = {'enzyme': 'FooA', 'gene': '', 'ec': '', 'organism': 'Escherichia coli', 'strain': '', 'uniprot': '',
        'protein_ids': '', 'variant': 'wild type', 'substrate': 'ATP', 'substrate_full_name': 'adenosine 5\'-triphosphate',
        'cosubstrate': '', 'pH': 7.5, 'temperature_C': 25, 'conditions': '', 'metric_note': '', 'construct': '',
        'location': 'Table 1', 'reasoning': 'Table 1 row.', 'censored': '', 'limit': ''}
rows = [
    {**base, 'metric': 'kcat', 'raw_value': '12.3 ± 0.4', 'raw_unit': 's-1', 'quote': WT},
    {**base, 'metric': 'Km', 'raw_value': '45 ± 3', 'raw_unit': 'µM', 'quote': WT},
    {**base, 'metric': 'kcat/Km', 'raw_value': '2.7 × 10^5', 'raw_unit': 'M-1 s-1', 'quote': WT},
    {**base, 'variant': 'Y123F', 'metric': 'kcat', 'raw_value': '0.50 ± 0.02', 'raw_unit': 's-1', 'quote': MUT},
    {**base, 'variant': 'Y123F', 'metric': 'Km', 'raw_value': '60 ± 5', 'raw_unit': 'µM', 'quote': MUT},
    {**base, 'variant': 'Y123F', 'metric': 'kcat/Km', 'raw_value': '8.3 × 10^3', 'raw_unit': 'M-1 s-1', 'quote': MUT},
    # planted errors the code checks should catch although the verifier "confirmed" them:
    {**base, 'variant': 'D45A', 'metric': 'kcat', 'raw_value': '1.1', 'raw_unit': 's-1',
     'quote': 'FooA D45A | ATP | 1.1 | 30 | 3.7 × 10^4'},                                   # quote not in the paper
    {**base, 'variant': 'Y123F', 'metric': 'Km', 'raw_value': '66 ± 5', 'raw_unit': 'mM', 'quote': MUT,
     'metric_note': 'planted: number not in quote'},                                      # value not in the quote
    # a Ki read as a Km, which the verifier rejects:
    {**base, 'substrate': 'ADP', 'metric': 'Km', 'raw_value': '0.8 ± 0.1', 'raw_unit': 'mM', 'location': 'Table 2',
     'quote': 'ADP | 0.8 ± 0.1'},
]
read = {'pmid': PMID, 'doi': '10.0000/demo', 'title': 'Demo kinetics of FooA', 'model': 'demo-model',
        'note': 'synthetic paper', 'rows': rows}
verdicts = [{'i': i, 'metric': r['metric'], 'raw_value': r['raw_value'], 'verdict': 'confirm',
             'reason': 'checked against ' + r['location'], 'on_page_image': False, 'fix': {}} for i, r in enumerate(rows)]
verdicts[-1].update(verdict='reject', reason='Table 2 prints a Ki, not a Km')
ver = {'pmid': PMID, 'model': 'demo-model', 'verdicts': verdicts, 'missed_count': 0, 'reason_if_empty': ''}

with catlog.Queue() as q:
    q.set(PMID, status='reading', doi='10.0000/demo', title='Demo kinetics of FooA')
catlog.TEXTS.mkdir(exist_ok=True)
catlog.WORK.mkdir(exist_ok=True)
t = time.time()
(catlog.TEXTS / f'{PMID}.txt').write_text(TEXT)
os.utime(catlog.TEXTS / f'{PMID}.txt', (t - 20, t - 20))
for i, (name, d) in enumerate(((f'{PMID}.read.json', read), (f'{PMID}.verify.json', ver))):
    p = catlog.WORK / name
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    os.utime(p, (t - 10 + 5 * i, t - 10 + 5 * i))  # text, then read, then verdicts
print(f'demo paper {PMID}: {len(rows)} rows written to texts/ and work/')
