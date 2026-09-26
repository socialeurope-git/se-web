#!/usr/bin/env python3
"""Classify a diff.py log: ok (<=0.5%), placeholder (candidate page <=1200px: Bunny deploy page/error), real (>0.5% with a
height difference >3px, or >1.5%), subpixel (>0.5% but <=1.5% with equal height: anti-aliasing/resampling only).
Usage: diff_summary.py <log> [--ids kind]  -> prints counts; with --ids prints the ids of that kind (for a re-run)."""
import re, sys, collections
log = sys.argv[1]; want = sys.argv[sys.argv.index("--ids") + 1] if "--ids" in sys.argv else None
rows = [l.split() for l in open(log) if re.match(r"^\d+-\d+ [\d.]+ \d+ \d+", l)]
errors = [l.split()[0] for l in open(log) if re.match(r"^\d+-\d+ ", l) and not re.match(r"^\d+-\d+ [\d.]+ \d+ \d+", l)]
kinds = collections.defaultdict(list)
for r in rows:
    pid = r[0].split("-")[0]; d = float(r[1]); a, b = int(r[2]), int(r[3])
    if b <= 1200: k = "placeholder"
    elif d <= 0.5: k = "ok"
    elif abs(a - b) > 3 or d > 1.5: k = "real"
    else: k = "subpixel"
    kinds[k].append((pid, d, a - b))
if want: print(" ".join(p for p, _, _ in kinds.get(want, [])) if want != "errors" else " ".join(e.split("-")[0] for e in errors))
else:
    print({k: len(v) for k, v in kinds.items()}, "of", len(rows), "| errors:", len(errors))
    for k in ("real", "subpixel"):
        v = sorted(kinds.get(k, []), key=lambda x: -x[1]); print(k, "worst:", [(p, round(d, 2), dh) for p, d, dh in v[:12]])
