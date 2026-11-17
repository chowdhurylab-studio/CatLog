#!/bin/bash
# Batch 4 of the locked test's reads, CatLog's frozen copy only (the plain reads of all 119 papers are done and audited,
# 11 Nov 04:50). The 29 papers still reading in catlog-copy, in the draw's order, as three follow-up launches of at most
# 10 papers (run_a6.py locked --pmids ...), one after another, so that a usage-limit stop discards at most one small
# launch (a launch adds its papers only at its end). Stops at the first console showing a usage limit (exit 2).
cd "<the kit folder>/code" || exit 1
P=($(cat ../records/orders/locked_draw.txt))
todo=()
for p in "${P[@]:90}"; do
  st=$(awk -F'\t' -v p="$p" '$1==p {print $4}' ../catlog-copy/papers.tsv)
  [ "$st" = "reading" ] && todo+=("$p")
done
echo "$(date '+%m-%d %H:%M') batch 4 copy: ${#todo[@]} papers to read, launches of at most 10"
k=0
for ((s=0; s<${#todo[@]}; s+=10)); do
  k=$((k + 1))
  part=("${todo[@]:s:10}")
  echo "$(date '+%m-%d %H:%M') batch 4 copy part $k: ${#part[@]} papers"
  python3 -B tools/w1/run_a6.py locked --pmids "${part[@]}" > ../records/locked_a6_4_$k.console.txt 2>&1
  echo "$(date '+%m-%d %H:%M') batch 4 copy part $k done: $(grep -o '"launch": "[^"]*"' ../records/locked_a6_4_$k.console.txt | head -1)"
  if grep -q -i "hit your\|usage limit" ../records/locked_a6_4_$k.console.txt; then
    echo "batch 4 copy part $k stopped at a usage limit"; exit 2
  fi
done
echo "$(date '+%m-%d %H:%M') batch 4 copy done"
