#!/usr/bin/env python3
"""Empties a site for a re-import (permanent deletes work on a healthy database; they only failed on the corrupted one of 2026-09-26).
Empty a site's content before a fresh import (SE_BASE/SE_TOKEN): every post and page (permanently), the sidebar
widgets and every media item. Users, bylines (re-linked by sync_bylines), settings, menus and plugin settings stay.
Asks for --yes. --keep-media leaves the media library alone (the importer's media step then skips existing files by
original URL and rewrite-urls still maps them; media_meta.py --delete-unused prunes afterwards)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emdash_api import api, list_all
if "--yes" not in sys.argv: raise SystemExit("refusing without --yes")
for coll in ("posts", "pages"):
    items = list_all(f"/_emdash/api/content/{coll}"); n = 0
    for e in items:
        api("DELETE", f"/_emdash/api/content/{coll}/{e['id']}"); n += 1
        try: api("DELETE", f"/_emdash/api/content/{coll}/{e['id']}/permanent", ok404=True)
        except Exception: pass
    print(f"{coll}: {n} deleted")
try:
    area = api("GET", "/_emdash/api/widget-areas/sidebar")["data"]
    for w in area.get("widgets") or []: api("DELETE", f"/_emdash/api/widget-areas/sidebar/widgets/{w['id']}")
    print("sidebar widgets removed")
except Exception as e: print("widgets:", str(e)[:80])
media = [] if "--keep-media" in sys.argv else list_all("/_emdash/api/media"); n = 0
for m in media:
    try: api("DELETE", f"/_emdash/api/media/{m['id']}"); n += 1
    except Exception as e: print("media", m["id"], str(e)[:80])
print(f"media: {n} deleted")
for coll in ("posts", "pages"):
    print(coll, "left:", len(list_all(f"/_emdash/api/content/{coll}")))
print("media left:", len(list_all("/_emdash/api/media")))
