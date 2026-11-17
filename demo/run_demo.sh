#!/bin/bash
# CatLog demo: one made-up paper through the code checks, offline, in about a second.
# Copies the code to a temporary folder (nothing is written into this repository), writes the paper's text and the
# reader's and verifier's files there, then runs `catlog.py add`, `catlog.py show` and `tools/recheck.py`.
# Usage: bash demo/run_demo.sh            Expected output: demo/expected_output.txt
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
W="$(mktemp -d)"
trap 'rm -rf "$W"' EXIT
cp -R "$HERE/catlog.py" "$HERE/config.json" "$HERE/tools" "$HERE/prompts" "$W/"
cd "$W"
python3 -I -B "$HERE/demo/make_demo_paper.py" "$W"
echo "== catlog.py add 99999901"
python3 -I -B catlog.py add 99999901
echo "== refused, and why (rejected.jsonl)"
python3 -I -B -c "import json
for r in map(json.loads, open('rejected.jsonl')):
    print(r.get('variant'), '|', r.get('metric'), '=', r.get('raw_value'), r.get('raw_unit'), '->', r.get('why') or r.get('reason'))"
echo "== catlog.py show 99999901"
python3 -I -B catlog.py show 99999901
echo "== tools/recheck.py"
python3 -I -B tools/recheck.py
