#!/bin/bash
# The locked test's reads (PREREGISTRATION.md): the drawn papers in order, in batches of 30; per batch the plain read
# (run_plain.py --arm A0 --run locked, 3 lanes) and CatLog's frozen copy (run_a6.py locked, 4 lanes) side by side. A batch
# whose consoles show a usage limit ends the loop (exit 2): its papers are read again by running this script again
# (plain: valid reads are skipped; copy: papers left reading are claimed again; finished ones are refused).
cd "<the kit folder>/code" || exit 1
P=($(cat ../records/orders/locked_draw.txt))
n=${#P[@]}; B=30; k=0
for ((s=0; s<n; s+=B)); do
  k=$((k + 1))
  batch=("${P[@]:s:B}")
  todo=()
  for p in "${batch[@]}"; do
    st=$(awk -F'\t' -v p="$p" '$1==p {print $4}' ../catlog-copy/papers.tsv)
    [ "$st" = "reading" ] && todo+=("$p")
  done
  echo "$(date '+%m-%d %H:%M') batch $k: ${#batch[@]} papers, ${#todo[@]} to read in the copy"
  python3 -B tools/w1/run_plain.py --arm A0 --run locked --lanes 3 --pmids "${batch[@]}" > ../records/locked_plain_$k.console.txt 2>&1 &
  pp=$!
  if [ ${#todo[@]} -gt 0 ]; then
    python3 -B tools/w1/run_a6.py locked --pmids "${todo[@]}" > ../records/locked_a6_$k.console.txt 2>&1
  fi
  wait $pp
  echo "$(date '+%m-%d %H:%M') batch $k done: plain $(grep -c ': ok' ../records/locked_plain_$k.console.txt) ok"
  if grep -q -i "hit your\|usage limit\|\"stopped\": true" ../records/locked_plain_$k.console.txt ../records/locked_a6_$k.console.txt 2>/dev/null; then
    echo "batch $k stopped at a usage limit or repeated failures"; exit 2
  fi
done
echo "$(date '+%m-%d %H:%M') all batches done"
