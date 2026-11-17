"""Inspect the AlphaFold model of P00805: numbering, residue 270, confidence, geometry. Usage: python -I inspect_model.py MODEL"""
import sys

import numpy as np
from pymol import cmd

model = sys.argv[1]
cmd.load(model, 'af')
cmd.remove('hydro')

# numbering and sequence
ca = cmd.get_model('af and name CA')
resis = [int(a.resi) for a in ca.atom]
print('CA count', len(resis), 'first', resis[0], 'last', resis[-1], 'contiguous', resis == list(range(resis[0], resis[-1] + 1)))
fasta = ''.join(cmd.get_fastastr('af').split('\n')[1:])
print('sequence length', len(fasta))
print('1-22  (signal) ', fasta[:22])
print('23-34 (mature) ', fasta[22:34])
print('265-275        ', fasta[264:275], ' residue 270 =', fasta[269])

# residue 270 by atom record
r270 = cmd.get_model('af and resi 270')
names = sorted({(a.resn, a.resi, a.chain) for a in r270.atom})
print('resi 270 atoms ->', names, [a.name for a in r270.atom])

# confidence (pLDDT in the B-factor column)
b = {int(a.resi): a.b for a in ca.atom}
sig = [b[i] for i in range(1, 23)]
mat = [b[i] for i in range(23, 349)]
print('pLDDT signal 1-22: mean %.1f min %.1f max %.1f' % (np.mean(sig), min(sig), max(sig)))
print('pLDDT mature 23-348: mean %.1f min %.1f; residues < 70: %s' % (
    np.mean(mat), min(mat), [i for i in range(23, 349) if b[i] < 70]))
print('pLDDT residue 270: %.2f; 265-275: %s' % (b[270], [round(b[i], 1) for i in range(265, 276)]))

# exposure of residue 270 in the mature monomer
cmd.create('mat', 'af and resi 23-348')
cmd.set('dot_solvent', 1)
cmd.set('dot_density', 3)
cmd.get_area('mat', load_b=1)
sc = cmd.get_model('mat and resi 270 and not name N+C+O')
print('residue 270 SASA (monomer, all side-chain+CA atoms): %.1f A^2' % sum(a.b for a in sc.atom))
cmd.delete('mat')

# geometry: principal axes of the mature chain, direction to residue 270's side chain
X = np.array(cmd.get_coords('af and resi 23-348 and name CA'))
c = X.mean(0)
U, S, Vt = np.linalg.svd(X - c, full_matrices=False)
print('principal extents (SD along axes, A):', np.round(S / np.sqrt(len(X)), 1))
s270 = np.array(cmd.get_coords('af and resi 270 and not name N+C+O+CA')).mean(0)
d = s270 - c
print('residue 270 side chain is %.1f A from the mature centroid' % np.linalg.norm(d))
print('its direction in the principal frame:', np.round(Vt @ (d / np.linalg.norm(d)), 2))
