#!/bin/bash
# The full-record judging, in batches of about 100 phase-1 sessions in the drawn paper order (score_randfull.py next), so
# that a run cut short by a usage limit has judged a random set of papers; each batch runs its papers' third judges too.
# A batch the runner stops (dead-stop after failed steps: a usage limit) ends the loop. Then one pass of phase 2 over all.
cd "<the kit folder>/code" || exit 1
i=0
while :; do
  out=$(python3 -B tools/w1/score_randfull.py next 100)
  echo "$(date '+%m-%d %H:%M') $(echo "$out" | head -1)"
  pm=$(echo "$out" | grep '^--pmids ' | sed 's/^--pmids //')
  [ -z "$pm" ] && break
  i=$((i + 1))
  python3 -B tools/w1/run_adjudicate.py --runs randfull --lanes 3 --pmids $pm > ../records/randfull_judges$i.console.txt 2>&1
  echo "$(date '+%m-%d %H:%M') batch $i: ok $(grep -c ': ok (OK' ../records/randfull_judges$i.console.txt), not ok $(grep -cE 'REFUSED|FAILED|LEFT OUT' ../records/randfull_judges$i.console.txt)"
  if grep -q '"stopped": true' ../records/randfull_judges$i.console.txt; then echo "batch $i stopped: usage limit or repeated failures"; exit 2; fi
done
python3 -B tools/w1/run_adjudicate.py --runs randfull --lanes 3 --phase 2 > ../records/randfull_judges_phase2.console.txt 2>&1
echo "$(date '+%m-%d %H:%M') phase 2 pass done: $(grep '^phase 2' ../records/randfull_judges_phase2.console.txt)"
