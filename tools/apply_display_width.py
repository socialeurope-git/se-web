#!/usr/bin/env python3
"""Images the author resized in the WordPress editor (<img style="width:760px">, figure class is-resized) are shown at that
width on the live site; a native image block renders at its natural size. Reads the display widths from the export and
sets displayWidth/displayHeight on the matching image blocks (SE_BASE/SE_TOKEN). --dry reports only."""
import json, os, re, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emdash_api import api, list_all, ROOT
dry = "--dry" in sys.argv
x = open(f"{ROOT}/archive/wxr-all.xml", encoding="utf-8").read()
SIZE = re.compile(r"-\d+x\d+(?=\.[a-z0-9]+$)", re.I)
widths = {}
for m in re.finditer(r"<img\b[^>]*>", x):
    tag = m.group(0); sw = re.search(r'style="[^"]*width:\s*(\d+)px', tag); src = re.search(r'src="([^"]+)"', tag)
    if sw and src: widths[SIZE.sub("", html.unescape(src.group(1)).split("?")[0])] = int(sw.group(1))
imp = json.load(open(f"{ROOT}/archive/media-import.json")); by_id = {i["mediaId"]: i["originalUrl"] for i in imp["imported"]}; by_key = {i["newUrl"].rsplit("/", 1)[-1]: i["mediaId"] for i in imp["imported"]}
print("resized images in the export:", len(widths))
changed = 0; blocks = 0
for coll in ("posts", "pages"):
    for e in list_all(f"/_emdash/api/content/{coll}"):
        hit = False; e["data"]["content"] = e["data"].get("content") or []
        for b in e["data"].get("content") or []:
            if b.get("_type") == "htmlBlock" and "<img" in (b.get("html") or ""):   # figures kept as HTML (captions with links)
                def fix(m):
                    tag = m.group(0); key = re.search(r'/_emdash/api/media/file/([A-Za-z0-9]+\.[a-z0-9]+)', tag)
                    mid = by_key.get(key.group(1)) if key else None; w = widths.get(by_id.get(mid, "")) if mid else None
                    if not w or "style=" in tag: return tag
                    return tag[:-1] + f' style="width:{w}px;height:auto">'
                new = re.sub(r"<img\b[^>]*>", fix, b["html"])
                if new != b["html"]: b["html"] = new; hit = True; blocks += 1
                continue
            if b.get("_type") != "image": continue
            orig = by_id.get((b.get("asset") or {}).get("_ref")); w = widths.get(orig or "")
            if not w or not b.get("width") or b.get("displayWidth") == w: continue
            b["displayWidth"] = w; b["displayHeight"] = round(w * b["height"] / b["width"]); hit = True; blocks += 1
        if hit:
            changed += 1
            if not dry:
                api("PUT", f"/_emdash/api/content/{coll}/{e['id']}", {"data": {"content": e["data"]["content"]}, "skipRevision": True}); api("POST", f"/_emdash/api/content/{coll}/{e['id']}/publish", {})
print(f"{'dry: ' if dry else ''}display width set on {blocks} image blocks in {changed} entries")
