#!/usr/bin/env python3
"""Broken internal links in the imported content (WordPress originals link to old slugs, taxonomy pages that no longer
exist, or typos). Resolves every unknown internal path against the live site (follows its redirects), rewrites the
link to the final slug when live redirects there, and writes the rest to archive/broken-links.json to decide on.
Usage: fix_internal_links.py [--apply]  (SE_BASE/SE_TOKEN for --apply; reads archive/dump/*.json)"""
import json, os, re, sys, urllib.request, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emdash_api import api, ROOT
D = f"{ROOT}/archive/dump"; apply = "--apply" in sys.argv
posts = json.load(open(f"{D}/posts.json")); pages = json.load(open(f"{D}/pages.json"))
slugs = {p["slug"] for p in posts} | {p["slug"] for p in pages}
cats = {t["slug"] for t in json.load(open(f"{D}/terms-category.json"))}; bylines = {b["slug"] for b in json.load(open(f"{D}/bylines.json"))}
DATED = re.compile(r"^/(\d{4})/(\d{2})/([^/]+)/?$")
def known(path):
    p = path.strip("/")
    if p == "" or p in slugs: return True
    if p.startswith("category/"): return p.split("/")[1] in cats
    if p.startswith("author/"): return p.split("/")[1] in bylines
    return p.startswith(("page/", "feed", "_emdash/", "tag/", "wp-content/", "?s="))
cache = {}
def resolve(path):
    if path in cache: return cache[path]
    url = "https://www.socialeurope.eu" + path
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (se-links)"})
        r = urllib.request.urlopen(req, timeout=20); final = r.geturl(); code = r.status
    except urllib.error.HTTPError as e: final, code = e.geturl(), e.code
    except Exception as e: final, code = None, str(e)[:40]
    fp = re.sub(r"^https?://(www\.)?socialeurope\.eu", "", final) if final else None
    cache[path] = (code, fp); return cache[path]
changes = collections.defaultdict(list); unresolved = []
for e in posts + pages:
    coll = e["type"]; changed = False
    for b in e["data"].get("content") or []:
        if b.get("_type") != "block": continue
        for md in b.get("markDefs") or []:
            h = md.get("href") or ""
            if not h.startswith("/") or known(h.split("?")[0].split("#")[0]): continue
            path = h.split("#")[0]; frag = h[len(path):]
            m = DATED.match(path)
            if m and m.group(3) in slugs:   # WordPress dated permalink of an existing article
                md["href"] = "/" + m.group(3) + frag; changes[e["slug"]].append((h, md["href"])); changed = True; continue
            code, fp = resolve(path)
            if code == 200 and fp and known(fp.split("?")[0]) and fp.strip("/") != path.strip("/"):
                md["href"] = fp.rstrip("/") + frag; changes[e["slug"]].append((h, md["href"])); changed = True
            elif code == 200 and fp and fp.strip("/") == path.strip("/"):
                unresolved.append((e["slug"], h, "live 200 but unknown here (page not imported?)"))
            else:
                unresolved.append((e["slug"], h, f"live {code} -> {fp}"))
    if changed and apply:
        api("PUT", f"/_emdash/api/content/{coll}/{e['id']}", {"data": {"content": e["data"]["content"]}, "skipRevision": True})
        api("POST", f"/_emdash/api/content/{coll}/{e['id']}/publish", {})
print(f"links rewritten to the live redirect target: {sum(len(v) for v in changes.values())} in {len(changes)} entries{' (applied)' if apply else ' (dry)'}")
for s, v in list(changes.items())[:5]: print("  ", s[:40], v[:2])
kinds = collections.Counter(u[2].split(" ->")[0] for u in unresolved)
print("unresolved:", len(unresolved), dict(kinds))
for u in unresolved[:12]: print("  ", u)
json.dump({"rewritten": changes, "unresolved": unresolved}, open(f"{ROOT}/archive/broken-links.json", "w"), indent=1)
