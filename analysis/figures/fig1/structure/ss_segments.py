"""List secondary-structure segments of the mature chain as read from the file and as PyMOL's dss assigns them."""
import sys
from itertools import groupby
from pymol import cmd

cmd.load(sys.argv[1], 'af')


def segs(tag):
    ss = {}
    cmd.iterate('af and name CA and resi 23-348', 'ss_[int(resi)] = ss or "L"', space={'ss_': ss})
    out = []
    for k, g in groupby(sorted(ss.items()), key=lambda t: t[1]):
        g = list(g)
        out.append((k, g[0][0], g[-1][0], len(g)))
    H = [s for s in out if s[0] == 'H']
    S = [s for s in out if s[0] == 'S']
    print(tag, 'helices', len(H), 'strands', len(S))
    print('  strands:', [(a, b) for _, a, b, n in S])
    print('  short strands (<=2):', [(a, b) for _, a, b, n in S if n <= 2])
    print('  short helices (<=3):', [(a, b) for _, a, b, n in H if n <= 3])
    return out


segs('file')
cmd.dss('af')
segs('dss ')
