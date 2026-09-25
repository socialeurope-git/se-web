#!/usr/bin/env python3
"""After EmDash's media import and BEFORE its rewrite-urls step (which collapses every size variant onto the original):
the importer rewrites image/gallery blocks and string fields, but not the raw `htmlBlock` blocks inside Portable Text. This pass rewrites every /wp-content/uploads/ URL in those blocks
(exact match, or WordPress size variant -> the original media) and saves the entry without a new revision.
Also writes src/se/data/media-map.json (old URL -> EmDash media URL) for the runtime redirects + theme helper."""
import json, re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emdash_api import api, list_all, ROOT
SIZE = re.compile(r"-\d+x\d+(?=\.[a-z0-9]+$)", re.I)
imp = json.load(open(f"{ROOT}/archive/media-import.json"))
exact = {i["originalUrl"]: i["newUrl"] for i in imp["imported"]}
# ShortPixel variants: name.webp / name.avif next to name.jpg|png
def base_of(u):
    u = SIZE.sub("", u)
    return u
alt = {}
for old, new in exact.items():
    stem = os.path.splitext(old)[0]
    for ext in (".webp", ".avif"):
        alt.setdefault(stem + ext, new)   # name.webp  (ShortPixel)
        alt.setdefault(old + ext, new)    # name.png.webp (older ShortPixel naming)
SIZE3 = re.compile(r"-(\d+)x(\d+)(?=\.([a-z0-9]+)$)", re.I)
def map_url(u):
    """Same rules as src/se/media.ts: original -> media file; WordPress size variant -> Astro image endpoint with the
    same width/height/format (so the page keeps WordPress's exact pixel sizes); ShortPixel twin -> converted original."""
    if u in exact: return exact[u]
    ext = (re.search(r"\.([a-z0-9]+)$", u, re.I) or [None, ""])[1].lower()
    m = SIZE3.search(u); b = SIZE3.sub("", u)
    orig = exact.get(b) or alt.get(b)
    if not orig: return None
    oext = (re.search(r"\.([a-z0-9]+)$", orig, re.I) or [None, ""])[1].lower()
    if not m and (not ext or ext == oext): return orig
    q = {"href": orig}
    if m: q["w"] = m.group(1); q["h"] = m.group(2)
    f = ext or oext; q["f"] = "jpeg" if f == "jpg" else f
    from urllib.parse import urlencode
    return "/_image?" + urlencode(q)
json.dump({"exact": exact, "alt": alt}, open(f"{ROOT}/src/se/data/media-map.json", "w"))
print("media map:", len(exact), "originals,", len(alt), "webp/avif twins")

URL = re.compile(r"https?://(?:www\.)?socialeurope\.eu/wp-content/uploads/[^\s\"'<>)]+")
rows = {}
for coll in ("posts", "pages"):
    rows[coll] = [(e["id"], e["slug"], json.dumps(e["data"].get("content") or []), bool(e.get("draftRevisionId"))) for e in list_all(f"/_emdash/api/content/{coll}")]
    rows[coll] = [r for r in rows[coll] if "wp-content/uploads" in r[2] or r[3]]
changed = unmapped = 0; missing = set()
for coll in ("posts", "pages"):
    for eid, slug, content, _draft in rows[coll]:
        if not content or "wp-content/uploads" not in content: continue
        blocks = json.loads(content); touched = False
        for b in blocks:
            if b.get("_type") != "htmlBlock" or not b.get("html"): continue
            def rep(m):
                global unmapped
                n = map_url(m.group(0).split("?")[0])
                if n is None: unmapped += 1; missing.add(m.group(0)); return m.group(0)
                return n
            new = URL.sub(rep, b["html"])
            if new != b["html"]: b["html"] = new; touched = True
        if touched:
            # a data write on a published entry becomes a draft in EmDash: publish it right away (publishedAt is kept)
            api("PUT", f"/_emdash/api/content/{coll}/{eid}", {"data": {"content": blocks}, "skipRevision": True})
            api("POST", f"/_emdash/api/content/{coll}/{eid}/publish", {}); changed += 1
print(f"html blocks rewritten in {changed} entries; {unmapped} URLs without media ({len(missing)} distinct)")
# leftovers from an earlier run: entries whose draft was never published
for coll in ("posts", "pages"):
    ids = [eid for eid, _s, _c, draft in rows[coll] if draft]
    for eid in ids: api("POST", f"/_emdash/api/content/{coll}/{eid}/publish", {})
    if ids: print(f"published pending drafts: {coll} {len(ids)}")
