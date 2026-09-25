#!/usr/bin/env python3
"""Content images that WordPress never registered as attachments (archive/media-unmapped.json after tools/rewrite_html_blocks.py):
download the original from the live site and upload it through EmDash's media API, then record it in archive/media-import.json
so the next rewrite_html_blocks.py run maps and rewrites them like every other file."""
import json, re, os, sys, urllib.request, urllib.parse, uuid, mimetypes
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); BASE = "http://127.0.0.1:4321"
SIZE = re.compile(r"-\d+x\d+(?=\.[a-z0-9]+$)", re.I)
def cookie():
    c = []
    for line in open(f"{ROOT}/archive/jar.txt"):
        if line.startswith("#HttpOnly_"): line = line[10:]
        if not line.strip() or line.startswith("#"): continue
        p = line.rstrip("\n").split("\t")
        if len(p) >= 7: c.append(f"{p[5]}={p[6]}")
    return "; ".join(c)
COOKIE = cookie()
imp = json.load(open(f"{ROOT}/archive/media-import.json")); known = {i["originalUrl"] for i in imp["imported"]}
unmapped = json.load(open(f"{ROOT}/archive/media-unmapped.json"))
bases = set()
for u in unmapped:
    b = SIZE.sub("", u)
    b = re.sub(r"\.(webp|avif)$", "", b) if re.search(r"\.(png|jpe?g|gif)\.(webp|avif)$", b, re.I) else b
    if re.search(r"\.(webp|avif)$", b, re.I):  # a twin without the original in the list: try jpg then png
        stem = re.sub(r"\.(webp|avif)$", "", b); bases.update({stem + ".jpg", stem + ".png"})
    else: bases.add(b)
def fetch(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(u, safe="/:%"), headers={"User-Agent": "se-web-import/1.0"}), timeout=60) as r:
            ct = r.headers.get("content-type", ""); data = r.read()
            return (data, ct) if not ct.startswith("text/html") else (None, ct)
    except Exception: return (None, None)
added = 0
for u in sorted(bases):
    if u in known: continue
    data, ct = fetch(u)
    if not data: continue
    name = os.path.basename(urllib.parse.unquote(u)); bnd = uuid.uuid4().hex
    body = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: {ct or mimetypes.guess_type(name)[0] or 'application/octet-stream'}\r\n\r\n").encode() + data + f"\r\n--{bnd}--\r\n".encode()
    req = urllib.request.Request(BASE + "/_emdash/api/media", data=body, method="POST", headers={"Cookie": COOKIE, "X-EmDash-Request": "1", "Content-Type": f"multipart/form-data; boundary={bnd}"})
    try:
        with urllib.request.urlopen(req) as r: res = json.load(r)
    except urllib.error.HTTPError as e: print("upload failed", u, e.code, e.read()[:200]); continue
    d = res.get("data") or res; item = d.get("media") or d.get("item") or d
    key = item.get("storageKey") or item.get("storage_key"); mid = item.get("id")
    if added == 0: print("first response:", json.dumps(d)[:300])
    if not key: print("no storage key in response for", u); continue
    imp["imported"].append({"wpId": None, "originalUrl": u, "newUrl": f"/_emdash/api/media/file/{key}", "mediaId": mid}); known.add(u); added += 1
json.dump(imp, open(f"{ROOT}/archive/media-import.json", "w"))
print(f"orphan media uploaded: {added} (tried {len(bases)} candidate originals); rerun tools/rewrite_html_blocks.py")
