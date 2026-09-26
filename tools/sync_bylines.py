#!/usr/bin/env python3
"""Phase 2: make EmDash bylines the source of truth for authorship.

1. Every author in archive/authors.json exists as a byline (no login; "guest" in EmDash only means "no user account", so the flag stays off),
   with the plain-text bio (no website: WordPress only had the archive URL there).
2. Every post carries exactly the Co-Authors-Plus author list (archive/coauthors.json),
   in the CAP order, as explicit bylines.

Target/credentials: SE_BASE + SE_TOKEN (tools/emdash_api.py), default local dev with the session cookie jar.
  python3 tools/sync_bylines.py --dry-run
  python3 tools/sync_bylines.py --limit 1
  python3 tools/sync_bylines.py
"""
import argparse, json, re, sys, os
from html import unescape
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emdash_api import api, list_all

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent

def plain_bio(html):
    if not html: return None
    t = re.sub(r"<[^>]+>", "", html)
    return unescape(t).strip() or None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    authors = json.load(open(ROOT / "archive/authors.json"))
    coauthors = json.load(open(ROOT / "archive/coauthors.json"))
    posts = {p["id"]: p["slug"] for p in json.load(open(ROOT / "archive/posts.json"))}
    posts_api = list_all("/_emdash/api/content/posts")
    entry_by_slug = {p["slug"]: p["id"] for p in posts_api}
    current = {p["id"]: [c["byline"]["id"] for c in sorted(p.get("bylines") or [], key=lambda c: c.get("sortOrder", 0))] for p in posts_api}
    def status_of(eid):
        d = api("GET", f"/_emdash/api/content/posts/{eid}")["data"]["item"]; return d.get("status"), d.get("draftRevisionId")

    # 1. bylines (custom field photo_credit must exist: created by fresh_import.sh / setup below)
    fields = {f["slug"] for f in (api("GET", "/_emdash/api/admin/byline-fields")["data"].get("items") or [])}
    if "photo_credit" not in fields:
        api("POST", "/_emdash/api/admin/byline-fields", {"slug": "photo_credit", "label": "Photo credit (listed on /photo-credits)", "type": "boolean"}); print("byline field photo_credit created")
    by_slug = {it["slug"]: it for it in list_all("/_emdash/api/admin/bylines")}
    # portraits: the media import (archive/media-import.json) registered every upload; map the avatar original to its media id
    media_by_url = {}
    mi = ROOT / "archive/media-import.json"
    if mi.exists():
        for it in json.load(open(mi))["imported"]: media_by_url[it["originalUrl"]] = it["mediaId"]
    size_re = re.compile(r"-\d+x\d+(?=\.[a-z0-9]+$)", re.I)
    def avatar_media(au):
        m = re.search(r'<img[^>]+src="([^"]+)"', au.get("avatarHtml") or "")
        if not m: return None
        u = size_re.sub("", m.group(1).split("?")[0])
        return media_by_url.get(u)
    created = updated = 0
    for slug, au in authors.items():
        credit = "se-avatar-credit" in (au.get("avatarBoxHtml") or "")   # portrait listed on /photo-credits (byline field photo_credit)
        body = {"slug": slug, "displayName": au["name"], "bio": plain_bio(au.get("bio")), "websiteUrl": None, "isGuest": False, "avatarMediaId": avatar_media(au), "customFields": {"photo_credit": credit}}
        ex = by_slug.get(slug)
        if not ex:
            print("create", slug); created += 1
            if not a.dry_run: by_slug[slug] = api("POST", "/_emdash/api/admin/bylines", body)["data"]
        elif (ex.get("bio") or None) != body["bio"] or (ex.get("websiteUrl") or None) != body["websiteUrl"] or ex["displayName"] != au["name"] or (ex.get("avatarMediaId") or None) != body["avatarMediaId"] or bool((ex.get("customFields") or {}).get("photo_credit")) != credit or ex.get("isGuest") is not False:
            updated += 1
            if not a.dry_run: api("PUT", f"/_emdash/api/admin/bylines/{ex['id']}", {k: v for k, v in body.items() if k != "slug"})
    print(f"bylines: {created} created, {updated} updated, {len(by_slug)} total, {sum(1 for a in authors.values() if avatar_media(a))} with portrait media")

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
        st, dr = status_of(eid)
        if st != "published" or dr:
            print("WARNING status changed", slug, st, dr); sys.exit(2)
        if a.limit and changed >= a.limit: break
    print(f"posts: {changed} updated, {skipped} already correct")

main()
