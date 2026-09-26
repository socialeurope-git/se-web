#!/usr/bin/env python3
"""Contact sheet of first-difference bands: one row per id (control | candidate | mask) scaled down, for reviewing many
diff.py results at once. Usage: diff_sheet.py <diff_dir> <width> <out.png> id [id...]   (max ~8 ids per sheet)"""
import sys
from PIL import Image, ImageChops, ImageDraw
d, W, out, ids = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
ROWH, BAND = 260, 520
rows = []
for pid in ids:
    try: A = Image.open(f"{d}/shots/{pid}-{W}-control.png").convert("RGB"); B = Image.open(f"{d}/shots/{pid}-{W}-candidate.png").convert("RGB")
    except Exception: continue
    w = min(A.width, B.width); h = min(A.height, B.height)
    m = ImageChops.difference(A.crop((0, 0, w, h)), B.crop((0, 0, w, h))).convert("L").point(lambda v: 255 if v > 24 else 0)
    ys = [y for y in range(0, h, 8) if m.crop((0, y, w, y + 8)).getbbox()]
    y0 = max(0, (ys[0] if ys else 0) - 100)
    strip = Image.new("RGB", (3 * w + 40, BAND), (120, 120, 120))
    strip.paste(A.crop((0, y0, w, y0 + BAND)), (0, 0)); strip.paste(B.crop((0, y0, w, y0 + BAND)), (w + 20, 0)); strip.paste(m.crop((0, y0, w, y0 + BAND)).convert("RGB"), (2 * w + 40, 0))
    strip = strip.resize((int(strip.width * ROWH / BAND), ROWH)); ImageDraw.Draw(strip).text((6, 4), f"{pid} y={y0} h={A.height}/{B.height}", fill=(255, 0, 0)); rows.append(strip)
if not rows: sys.exit("no shots")
sheet = Image.new("RGB", (max(r.width for r in rows), sum(r.height + 6 for r in rows)), (60, 60, 60)); y = 0
for r in rows: sheet.paste(r, (0, y)); y += r.height + 6
sheet.save(out); print(out, sheet.size, len(rows), "rows")
