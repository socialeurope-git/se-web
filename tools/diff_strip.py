#!/usr/bin/env python3
"""Crop the first difference band out of a diff.py side-by-side image (control | candidate | mask) for a quick look.
Usage: diff_strip.py <diff_dir> <id-width> [out.png] [band_height]"""
import sys, os
from PIL import Image
d, key = sys.argv[1], sys.argv[2]; out = sys.argv[3] if len(sys.argv) > 3 else f"/tmp/{key}-strip.png"; H = int(sys.argv[4]) if len(sys.argv) > 4 else 700
A = Image.open(f"{d}/shots/{key}-control.png").convert("RGB"); B = Image.open(f"{d}/shots/{key}-candidate.png").convert("RGB")
w = min(A.width, B.width); h = min(A.height, B.height)
from PIL import ImageChops
m = ImageChops.difference(A.crop((0, 0, w, h)), B.crop((0, 0, w, h))).convert("L").point(lambda v: 255 if v > 24 else 0)
rows = [y for y in range(0, h, 4) if m.crop((0, y, w, y + 4)).getbbox()]
if not rows: print("no diff"); sys.exit()
y0 = max(0, rows[0] - 120); print("first diff row", rows[0], "diff rows", len(rows) * 4, "heights", A.height, B.height)
# bands: runs of differing rows (gap > 40px starts a new band); the biggest band is what to look at
bands = []
for y in rows:
    if bands and y - bands[-1][1] <= 40: bands[-1][1] = y + 4
    else: bands.append([y, y + 4])
bands.sort(key=lambda b: b[0] - b[1]); print("bands (y0,y1):", [tuple(b) for b in sorted(bands)[:6]], "biggest", tuple(bands[0]))
if "--band" in sys.argv: y0 = max(0, bands[0][0] - 120)
strip = Image.new("RGB", (3 * w + 40, H), (120, 120, 120)); strip.paste(A.crop((0, y0, w, y0 + H)), (0, 0)); strip.paste(B.crop((0, y0, w, y0 + H)), (w + 20, 0)); strip.paste(m.crop((0, y0, w, y0 + H)).convert("RGB"), (2 * w + 40, 0)); strip.save(out); print(out)
