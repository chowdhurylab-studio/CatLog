"""Ray-trace the mature chain of P00805 (AlphaFold model) as a cartoon with residue 270 marked.

Usage: python -I render_asp.py MODEL OUT.png [--width W --height H --base HEX --accent HEX --mode 0|1
                                                --rx DEG --ry DEG --rep spheres|sticks --signal hide|grey]
The view: the mature chain's longest principal axis runs left to right with the C-terminal domain (residue 270's
domain) on the right, as on a sequence bar read N to C; the camera looks at the face on which residue 270 sits.
"""
import argparse
import sys

import numpy as np
from pymol import cmd

ap = argparse.ArgumentParser()
ap.add_argument('model')
ap.add_argument('out')
ap.add_argument('--width', type=int, default=1400)
ap.add_argument('--height', type=int, default=0)   # 0: from the content's aspect
ap.add_argument('--base', default='#B5BDD2')      # light slate (NPG slate #8491B4 at 0.6 over white)
ap.add_argument('--accent', default='#262626')    # the figure's ink, as the residue-270 dot on its sequence bar
ap.add_argument('--signal_col', default='#C8C8C8')
ap.add_argument('--mode', type=int, default=1)    # ray_trace_mode: 1 = shaded with outlines, 0 = shaded only
ap.add_argument('--rx', type=float, default=0.0)  # extra turn about the screen's x axis (degrees)
ap.add_argument('--ry', type=float, default=0.0)  # extra turn about the screen's y axis (degrees)
ap.add_argument('--rep', default='spheres')
ap.add_argument('--signal', default='hide')
ap.add_argument('--ss', default='dss')            # dss or file
ap.add_argument('--sphere_scale', type=float, default=1.0)
ap.add_argument('--gain', type=float, default=0.12)
ap.add_argument('--outline', default='#262626')
ap.add_argument('--loop', type=float, default=0.2)
ap.add_argument('--margin', type=float, default=0.08)  # white around the drawn box, as a fraction of its size
a = ap.parse_args()


def rgb(h):
    return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def rot(axis, deg):
    t = np.radians(deg)
    c, s = np.cos(t), np.sin(t)
    if axis == 'x':
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


cmd.load(a.model, 'af')
cmd.remove('hydro')
if a.ss == 'dss':
    cmd.dss('af')                                  # PyMOL's own assignment: no one-residue bridges drawn as arrows
assert cmd.get_model('af and resi 270 and name CA').atom[0].resn == 'ASN'

# the camera frame, from the mature chain's geometry
X = np.array(cmd.get_coords('af and resi 23-348 and name CA'))
c = X.mean(0)
_, _, Vt = np.linalg.svd(X - c, full_matrices=False)
e1 = Vt[0]
ndom = np.array(cmd.get_coords('af and resi 23-212 and name CA')).mean(0)
cdom = np.array(cmd.get_coords('af and resi 235-348 and name CA')).mean(0)
if (cdom - ndom) @ e1 < 0:
    e1 = -e1                                       # C-terminal domain to the right
s270 = np.array(cmd.get_coords('af and resi 270 and not name N+C+O+CA')).mean(0)
d = s270 - c
p = d - (d @ e1) * e1
z = p / np.linalg.norm(p)                          # toward the viewer: the side of the long axis residue 270 sits on
x = e1
y = np.cross(z, x)
R = np.vstack([x, y, z])
R = rot('y', a.ry) @ rot('x', a.rx) @ R
allc = np.array(cmd.get_coords('af'))
cmd.load_coords(((allc - c) @ R.T).tolist(), 'af')

# visibility of residue 270's side chain against the backbone in front of it (the cartoon follows the backbone)
P = np.array(cmd.get_coords('af and resi 23-348 and not resi 270 and name N+CA+C+O'))
for nm in ('CB', 'CG', 'OD1', 'ND2'):
    q = np.array(cmd.get_coords(f'af and resi 270 and name {nm}'))[0]
    front = P[(P[:, 2] > q[2] + 0.5) & (np.hypot(P[:, 0] - q[0], P[:, 1] - q[1]) < 3.5)]
    print(f'residue 270 {nm}: depth {q[2]:+.1f} A, backbone atoms in front within 3.5 A: {len(front)}')
q = np.array(cmd.get_coords('af and resi 23-348 and name CA'))
print('mature chain on screen: x %.1f..%.1f  y %.1f..%.1f A; residue 270 CA at x %.1f y %.1f' % (
    q[:, 0].min(), q[:, 0].max(), q[:, 1].min(), q[:, 1].max(),
    *np.array(cmd.get_coords('af and resi 270 and name CA'))[0][:2]))

# scene
cmd.set_color('base_c', rgb(a.base))
cmd.set_color('acc_c', rgb(a.accent))
cmd.set_color('sig_c', rgb(a.signal_col))
cmd.set_color('line_c', rgb(a.outline))
cmd.bg_color('white')
cmd.hide('everything')
mature = 'af and resi 23-348'
cmd.show('cartoon', mature)
cmd.color('base_c', mature)
if a.signal == 'grey':
    cmd.show('cartoon', 'af and resi 1-22')
    cmd.color('sig_c', 'af and resi 1-22')
site = 'af and resi 270 and name CA+CB+CG+OD1+ND2'
if a.rep == 'spheres':
    cmd.show('spheres', site)
    cmd.set('sphere_scale', a.sphere_scale, site)
else:
    cmd.show('sticks', 'af and resi 270 and not name N+C+O')
    cmd.set('stick_radius', 0.42)
    cmd.set('cartoon_side_chain_helper', 0)
cmd.color('acc_c', 'af and resi 270 and not name N+C+O')

cmd.set('cartoon_fancy_helices', 1)
cmd.set('cartoon_loop_radius', a.loop)
cmd.set('cartoon_highlight_color', -1)
cmd.set('cartoon_transparency', 0)
cmd.set('orthoscopic', 1)
cmd.set('depth_cue', 0)
cmd.set('ray_trace_fog', 0)
cmd.set('ray_shadows', 0)
cmd.set('ambient', 0.45)
cmd.set('direct', 0.55)
cmd.set('reflect', 0.25)
cmd.set('specular', 0.12)
cmd.set('shininess', 25)
cmd.set('light_count', 2)
cmd.set('antialias', 2)
cmd.set('ray_opaque_background', 0)
cmd.set('ray_trace_mode', a.mode)
if a.mode:
    cmd.set('ray_trace_color', 'line_c')
    cmd.set('ray_trace_gain', a.gain)

# an explicit orthoscopic view: the model axes are already the screen axes, so the rotation is the identity; the
# image is centred on the drawn atoms' box and its height set so the box fills it with a small margin
cmd.reset()
shown = 'af and resi 23-348' + (' or (af and resi 1-22)' if a.signal == 'grey' else '')
B = np.array(cmd.get_coords(f'({shown}) and name N+CA+C+O'))
S_ = np.array(cmd.get_coords(site))
pad = 3.0                                          # a cartoon's helices and strands reach about this far past the backbone
lo = np.minimum(B.min(0) - pad, S_.min(0) - 2.0)
hi = np.maximum(B.max(0) + pad, S_.max(0) + 2.0)
ctr = (lo + hi) / 2
w_A, h_A = hi[0] - lo[0], hi[1] - lo[1]
H = a.height if a.height > 0 else int(round(a.width * h_A / w_A))
vis_h = max(h_A, w_A * H / a.width) * (1 + a.margin)
fov = cmd.get_setting_float('field_of_view')
dist = vis_h / 2 / np.tan(np.radians(fov) / 2)
v = list(cmd.get_view())
v[:9] = [1, 0, 0, 0, 1, 0, 0, 0, 1]
v[9:12] = [0.0, 0.0, -dist]
v[12:15] = ctr.tolist()
v[15], v[16] = dist - 80.0, dist + 80.0           # slabs well outside the molecule
cmd.set_view(v)
print('content box %.1f x %.1f A; image %d x %d px' % (w_A, h_A, a.width, H))
cmd.png(a.out, width=a.width, height=H, dpi=600, ray=1)
print('wrote', a.out)
sys.exit(0)
