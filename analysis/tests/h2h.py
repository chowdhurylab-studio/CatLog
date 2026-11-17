"""The vendored head-to-head matcher, loaded so that it converts with this branch's tools/units.py (frozen with the eval)
and reads the gold sets from the eval's keys/ folder.

  import h2h; C = h2h.C; h2h.use_keys(keys_dir)

h2h_common.py is a byte copy of paper/evidence/h2h_20261101/common.py (sha256 below; test_w1.py checks it). It names
the main folder as its ROOT and puts the main folder's tools/ first on sys.path; importing units.py from this branch
first makes it use the branch's copy, and the main folder's tools/ is taken off sys.path again afterwards. Nothing of
the main folder is read through it here (catalog_rows, status, derived_kcatkm, brenda_values and enzyextract_values
are never called)."""
import sys
from pathlib import Path

W1 = Path(__file__).resolve().parent
TOOLS = str(W1.parent)
MAIN_TOOLS = '<the CatLog folder>/tools'
COMMON_SHA256 = '97ffb6e87c99bc4183e54d2cc54aa66af0681f4494b0b34be0f7c7b4d609f1ab'  # common.py, be9b8ca
S06_SHA256 = 'fc3a9496ccdbf93a6fea88f86fe42bf75e4ad55f182e21dcba251978b66b7701'     # s06_enzyextract_manual.py
GOLD_NAMES = {'cosci': '20241212_Golden_Benchmark_for_Enzyme_Kinetics_converted.csv',
              'ee_manual': 'manual_curated_runeem_dataset.csv'}
GOLD_SHA256 = {'cosci': '5f172f5bd2d9101e725a67175a26dc3aa369592f3b8f801e6b9e24adf5922e70',      # h2h INPUTS.tsv
               'ee_manual': '37b2ff4cde194521a1afa247dfd4c29bf9eebfc1d4cb9a566e10dfb03a7b68ca'}

for p in (str(W1), TOOLS):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)
import units  # noqa: E402  (the branch's converter, cached before h2h_common imports one)
import h2h_common as C  # noqa: E402
while MAIN_TOOLS in sys.path:
    sys.path.remove(MAIN_TOOLS)
if C.units is not units:
    raise ImportError('h2h_common did not take the branch units.py')
from h2h_s06 import rows_to_values  # noqa: E402,F401


def use_keys(keys_dir):
    """Point the gold loaders at the eval's checked copies of the two gold files."""
    k = Path(keys_dir)
    C.GOLD_CSV = str(k / GOLD_NAMES['cosci'])
    C.EE_MANUAL = str(k / GOLD_NAMES['ee_manual'])
    return C
