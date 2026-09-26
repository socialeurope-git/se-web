#!/usr/bin/env python3
"""Media library hygiene after the import (SE_BASE/SE_TOKEN):
  - alt texts from the WordPress attachment meta (archive/alts.json, built from the WXR) and, for portraits, the byline name
  - media nothing references (posts, pages, bylines, widgets, settings) deleted: --delete-unused (dry otherwise)
Run AFTER tools/clean_content.mjs (it imports external images and changes the references)."""
import json, os, re, sys, urllib.parse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emdash_api import api, list_all, ROOT
delete = "--delete-unused" in sys.argv
alts = json.load(open(f"{ROOT}/archive/alts.json"))["alts"]
imp = json.load(open(f"{ROOT}/archive/media-import.json"))
orig_by_id = {i["mediaId"]: i["originalUrl"] for i in imp["imported"]}
media = list_all("/_emdash/api/media")
by_id = {m["id"]: m for m in media}; by_key = {m["storageKey"]: m["id"] for m in media}
posts = list_all("/_emdash/api/content/posts"); pages = list_all("/_emdash/api/content/pages")
bylines = list_all("/_emdash/api/admin/bylines")
widgets = api("GET", "/_emdash/api/widget-areas/sidebar")["data"]; settings = api("GET", "/_emdash/api/settings")["data"]
# usage
used = collections.Counter()
def scan(text):
    text = urllib.parse.unquote(text)
    for k in re.findall(r"/_emdash/api/media/file/([A-Za-z0-9]+\.[a-z0-9]+)", text):
        if k in by_key: used[by_key[k]] += 1
    for i in re.findall(r"\b(01[A-Z0-9]{24})\b", text):   # asset._ref / mediaId
        if i in by_id: used[i] += 1
for e in posts + pages: scan(json.dumps(e["data"]))
for b in bylines:
    if b.get("avatarMediaId"): used[b["avatarMediaId"]] += 1
scan(json.dumps(widgets)); scan(json.dumps(settings))
# alt + filename
name_by_avatar = {b["avatarMediaId"]: b["displayName"] for b in bylines if b.get("avatarMediaId")}
alt_set = fn_set = 0
for m in media:
    patch = {}
    alt = name_by_avatar.get(m["id"]) or alts.get(orig_by_id.get(m["id"], ""), "")
    if alt and (m.get("alt") or "") != alt: patch["alt"] = alt
    if patch:
        api("PUT", f"/_emdash/api/media/{m['id']}", patch)
        alt_set += 1
print(f"media {len(media)}: alt set {alt_set}, used {len(used)}, unused {len(media) - len(used)} (the API cannot rename files; {sum(1 for m in media if chr(37) in m['filename'])} percent-encoded display names stay)")
unused = [m for m in media if m["id"] not in used]
print("unused by type:", dict(collections.Counter(m["mimeType"] for m in unused)))
json.dump([{k: m[k] for k in ("id", "filename", "mimeType", "size")} for m in unused], open(f"{ROOT}/archive/media-unused.json", "w"), indent=1)
if delete:
    n = 0
    for m in unused:
        api("DELETE", f"/_emdash/api/media/{m['id']}"); n += 1
    print(f"deleted {n} unused media items")
else:
    print("dry: list in archive/media-unused.json (run with --delete-unused to remove them)")
