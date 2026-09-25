#!/usr/bin/env python3
"""Phase 2: make EmDash bylines the source of truth for authorship.

1. Every author in src/se/data/authors.json exists as a byline (guest, no login),
   with bio + website where the WP profile had them.
2. Every post carries exactly the Co-Authors-Plus author list (archive/coauthors.json),
   in the CAP order, as explicit bylines.

Uses the admin session cookie (archive/jar.txt) + X-EmDash-Request header.
  python3 tools/sync_bylines.py --dry-run
  python3 tools/sync_bylines.py --limit 1
  python3 tools/sync_bylines.py
"""
import argparse, json, re, sqlite3, sys, urllib.request, urllib.error
from html import unescape

BASE = "http://127.0.0.1:4321"
ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent

def cookie_header():
    c = []
    for line in (ROOT / "archive/jar.txt").read_text().splitlines():
        if line.startswith("#HttpOnly_"): line = line[len("#HttpOnly_"):]
        if not line or line.startswith("#"): continue
        p = line.split("\t")
        if len(p) >= 7: c.append(f"{p[5]}={p[6]}")
    return "; ".join(c)

COOKIE = cookie_header()

def api(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Cookie", COOKIE); req.add_header("X-EmDash-Request", "1")
    if body is not None: req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code}: {e.read()[:400]}")

def plain_bio(html):
    if not html: return None
    t = re.sub(r"<[^>]+>", "", html)
    return unescape(t).strip() or None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    authors = json.load(open(ROOT / "src/se/data/authors.json"))
    coauthors = json.load(open(ROOT / "archive/coauthors.json"))
    posts = {p["id"]: p["slug"] for p in json.load(open(ROOT / "archive/posts.json"))}
    db = sqlite3.connect(f"file:{ROOT/'data.db'}?mode=ro", uri=True)
    entry_by_slug = {s: i for s, i in db.execute("select slug, id from ec_posts")}
    current = {}
    for cid, bid, so in db.execute("select content_id, byline_id, sort_order from _emdash_content_bylines where collection_slug='posts' order by sort_order"):
        current.setdefault(cid, []).append(bid)

    # 1. bylines
    by_slug = {}; cursor = None
    while True:
        d = api("GET", "/_emdash/api/admin/bylines?limit=100" + (f"&cursor={cursor}" if cursor else ""))["data"]
        for it in d["items"]: by_slug[it["slug"]] = it
        cursor = d.get("nextCursor")
        if not cursor: break
    created = updated = 0
    for slug, au in authors.items():
        body = {"slug": slug, "displayName": au["name"], "bio": plain_bio(au.get("bio")), "websiteUrl": au.get("url") or None, "isGuest": True}
        ex = by_slug.get(slug)
        if not ex:
            print("create", slug); created += 1
            if not a.dry_run: by_slug[slug] = api("POST", "/_emdash/api/admin/bylines", body)["data"]
        elif (ex.get("bio") or None) != body["bio"] or (ex.get("websiteUrl") or None) != body["websiteUrl"] or ex["displayName"] != au["name"]:
            updated += 1
            if not a.dry_run: api("PUT", f"/_emdash/api/admin/bylines/{ex['id']}", {k: v for k, v in body.items() if k != "slug"})
    print(f"bylines: {created} created, {updated} updated, {len(by_slug)} total")

    # 2. post credits
    changed = skipped = 0
    for wp_id, cap in coauthors.items():
        slug = posts.get(int(wp_id)); eid = entry_by_slug.get(slug)
        if not eid: print("no entry for", wp_id, slug); continue
        want = []
        for c in cap:
            b = by_slug.get(c["slug"])
            if not b: print("no byline for", c["slug"]); continue
            if b["id"] not in want: want.append(b["id"])
        if current.get(eid, []) == want: skipped += 1; continue
        changed += 1
        if a.dry_run: continue
        api("PUT", f"/_emdash/api/content/posts/{eid}", {"bylines": [{"bylineId": b} for b in want], "skipRevision": True})
        st, dr = db.execute("select status, draft_revision_id from ec_posts where id=?", (eid,)).fetchone()
        if st != "published" or dr:
            print("WARNING status changed", slug, st, dr); sys.exit(2)
        if a.limit and changed >= a.limit: break
    print(f"posts: {changed} updated, {skipped} already correct")

main()
