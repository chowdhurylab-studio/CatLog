"""Crop a transparent PyMOL render to its content, fit it to an exact width with an even margin, and write a half-size copy.

Usage: python -I finish_png.py RENDER.png OUT_FULL.png OUT_HALF.png [--width 1200 --margin 12]
Resampling is done on premultiplied alpha (Pillow 'RGBa'), so edges keep no dark or light fringe.
"""
import argparse

from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('render')
ap.add_argument('full')
ap.add_argument('half')
ap.add_argument('--width', type=int, default=1200)
ap.add_argument('--margin', type=int, default=12)
a = ap.parse_args()

im = Image.open(a.render).convert('RGBA')
bb = im.getchannel('A').getbbox()
assert bb[0] >= 8 and bb[1] >= 8 and bb[2] <= im.width - 8 and bb[3] <= im.height - 8, ('content touches the render edge: clipped', bb, im.size)
im = im.crop(bb)
cw = a.width - 2 * a.margin
ch = round(im.height * cw / im.width)
if ch % 2:                                        # an even height so the half-size copy is exact
    ch += 1
fit = im.convert('RGBa').resize((cw, ch), Image.LANCZOS).convert('RGBA')
out = Image.new('RGBA', (a.width, ch + 2 * a.margin), (255, 255, 255, 0))
out.paste(fit, (a.margin, a.margin))
out.save(a.full, optimize=True)
half = out.convert('RGBa').resize((out.width // 2, out.height // 2), Image.LANCZOS).convert('RGBA')
half.save(a.half, optimize=True)
print('render', Image.open(a.render).size, 'content', bb, '->', out.size, half.size)
