#!/usr/bin/env python3
"""Which order each frozen paper was read in, worked out once from the agents' own transcripts and saved, so the
split survives the transcripts leaving this Mac for Nova (/archive).

Only one chat (the Europe PMC gain chat, transcripts in aedd9e55-6604-41d5-be0c-b78d86c9bb70) claimed papers in the
order of counted constants ('gain', from 10 Nov; its Km-list order 'km' from 9 Nov). Every other chat claimed with
plain `catlog.py next`, whose orders rank these papers by tier (expected_values 15, 5, 2: catlog.priority() and
gains(): "Only the 'gain' order uses it"). So a paper's order is the count order when its first read was added on or
after that date by an agent whose transcript lies in the gain chat's folder, else the tier order.

The reader agent of each paper is named in log.tsv's `agent_models` line at its first `add`
("<PMID>.read.json=<model>@agent-<id>"); its transcript is agent-<id>.jsonl under one chat's folder in
~/.claude/projects/-Users-<user>-Documents-catlog-v2/.

Usage: python3 reading_order.py   (reads papers.tsv of this folder and log.tsv; writes reading_order.tsv here)
"""
import collections
import csv
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
PROJ = os.path.expanduser('~/.claude/projects/-Users-<user>-Documents-catlog-v2')
GAIN_CHAT = 'aedd9e55-6604-41d5-be0c-b78d86c9bb70'
BEGAN = {'kcat': '2026-11-10', 'km': '2026-11-09'}
TAG = 'europepmc-freeze-20261116'

per = list(csv.DictReader(open(os.path.join(HERE, 'papers.tsv')), delimiter='\t'))
want = {r['pmid'] for r in per}

# the reader agent at each paper's first add (the agent_models line written just before it)
log = subprocess.run(['git', 'show', f'{TAG}:log.tsv'], cwd=ROOT, capture_output=True, check=True).stdout.decode(errors='replace')
reader, first = {}, {}
for line in log.splitlines():
    f = line.split('\t')
    if len(f) < 4 or f[1] not in want or f[1] in first:
        continue
    if f[2] == 'agent_models':
        m = re.search(rf'{re.escape(f[1])}\.read\.json=[^@\t]*@agent-([0-9a-f]+)', line)
        if m:
            reader[f[1]] = m.group(1)
    elif f[2] == 'add':
        first[f[1]] = f[0]

# every agent transcript of this project, by chat folder
where = {}
for chat in os.listdir(PROJ):
    path = os.path.join(PROJ, chat)
    if not os.path.isdir(path) or chat == 'memory':
        continue
    for dirpath, _, files in os.walk(path):
        for name in files:
            if name.startswith('agent-') and name.endswith('.jsonl'):
                where.setdefault(name[6:-6], chat)

rows, tally = [], collections.Counter()
values = {r['pmid']: int(r['values']) for r in per}
for r in per:
    p, lst = r['pmid'], r['list']
    a = reader.get(p, '')
    chat = where.get(a, '') if a else ''
    when = first.get(p, '')
    if when and when < BEGAN[lst]:
        order = 'tier'  # read before the count order existed (many of these readers' logs are on Nova now)
    elif not a or not chat:
        order = 'unknown'
    elif chat == GAIN_CHAT:
        order = 'count'
    else:
        order = 'tier'
    rows.append({'pmid': p, 'list': lst, 'first_added': when, 'reader_agent': a, 'chat': chat[:8], 'order': order,
                 'values': values[p]})
    tally[(lst, order)] += 1
    tally[(lst, order, 'values')] += values[p]

with open(os.path.join(HERE, 'reading_order.tsv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter='\t')
    w.writeheader()
    w.writerows(rows)
for lst in ('kcat', 'km'):
    print(lst, {o: (tally[(lst, o)], tally[(lst, o, 'values')]) for o in ('tier', 'count', 'unknown') if tally[(lst, o)]})
print('chats of the readers:', collections.Counter(x['chat'] for x in rows).most_common())
