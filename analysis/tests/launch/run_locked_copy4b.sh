#!/bin/bash
# The rest of batch 4 of the locked test, CatLog's frozen copy only (11 Nov). The papers to read again are those of
# records/locked_copy_remaining.json 'read_again': still reading in catlog-copy after launch more-6 (its launch session
# was stopped by the safety filter before any agent ran) and more-7 (stopped at the 5-hour limit), less the 3 papers the
# plain read refused (they leave the set whatever the copy does). Follow-up launches of at most 4 papers in the draw's
# order (run_a6.py locked --pmids ...). Before each launch the command line's account is checked with one tiny call: a
# 5-hour window at 50% or more, or a week at 95% or more, stops the script (exit 3) so that no launch starts that the
# limit would cut off (a launch adds its papers only at its end). A launch whose session the safety filter stopped before
# any agent ran (agents 0) is tried once more; a second such stop ends the script (exit 4). A usage limit: exit 2.
cd "<the kit folder>/code" || exit 1
CLI="<the kit folder>/cli/2.1.317/claude.app/Contents/MacOS/claude"
todo=($(python3 -c "
import json, csv
r = json.load(open('../records/locked_copy_remaining.json'))['read_again']
st = {x[0]: x[3] for x in csv.reader(open('../catlog-copy/papers.tsv'), delimiter='\t') if x}
print(' '.join(p for p in r if st.get(p) == 'reading'))"))
echo "$(date '+%m-%d %H:%M') batch 4 copy, the rest: ${#todo[@]} papers, launches of at most 4"
window() {  # prints "five_hour seven_day" utilization of the command line's account (0 when a window is not reported)
  env -i HOME="$HOME" PATH="$PATH" USER="$USER" LOGNAME="$LOGNAME" SHELL="$SHELL" TMPDIR="$TMPDIR" LC_CTYPE="${LC_CTYPE:-UTF-8}" \
    DISABLE_AUTOUPDATER=1 "$CLI" -p "Reply with the single word OK." --model claude-haiku-5-5 --max-turns 1 \
    --output-format stream-json --verbose 2>/dev/null | python3 -c '
import sys, json
f = s = 0.0
for line in sys.stdin:
    try: d = json.loads(line)
    except Exception: continue
    if d.get("type") == "rate_limit_event":
        w = (d.get("rate_limit_info") or {}).get("unifiedWindows") or {}
        f = max(f, float((w.get("five_hour") or {}).get("utilization") or 0))
        s = max(s, float((w.get("seven_day") or {}).get("utilization") or 0))
    if d.get("type") == "result" and d.get("is_error"): f = max(f, 1.0)
print(f, s)'
}
k=0
for ((i=0; i<${#todo[@]}; i+=4)); do
  k=$((k + 1))
  part=("${todo[@]:i:4}")
  read f s <<< "$(window)"
  echo "$(date '+%m-%d %H:%M') part $k: ${#part[@]} papers; account 5-hour ${f}, week ${s}"
  if python3 -c "import sys; sys.exit(0 if float('$f') >= 0.5 or float('$s') >= 0.95 else 1)"; then
    echo "part $k not started: the account's window is too full (5-hour $f, week $s)"; exit 3
  fi
  for try in 1 2; do
    python3 -B tools/w1/run_a6.py locked --pmids "${part[@]}" > ../records/locked_a6_4b_${k}_${try}.console.txt 2>&1
    c=../records/locked_a6_4b_${k}_${try}.console.txt
    echo "$(date '+%m-%d %H:%M') part $k try $try done: $(grep -o '"launch": "[^"]*"' $c | head -1), $(grep -o '"agents": [0-9]*' $c | head -1)"
    if grep -q -i "hit your\|usage limit" $c; then echo "part $k stopped at a usage limit"; exit 2; fi
    if grep -q '"agents": 0,' $c && grep -q -i "safeguards" $c; then
      [ $try = 2 ] && { echo "part $k: the launch session was stopped by the safety filter twice"; exit 4; }
      echo "part $k: the launch session was stopped by the safety filter before any agent ran; trying once more"
      continue
    fi
    break
  done
done
echo "$(date '+%m-%d %H:%M') batch 4 copy, the rest: done"
