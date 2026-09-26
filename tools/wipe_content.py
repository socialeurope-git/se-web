#!/usr/bin/env python3
"""DO NOT USE for a full re-import: permanent deletes via the API failed on staging (2026-09-26) and a fresh volume
(tools/bunny_app_patch.py, new volume name + app volumes list) is the clean way. Kept for partial clean-ups.
Empty a site's content before a fresh import (SE_BASE/SE_TOKEN): every post and page (permanently), the sidebar
widgets and every media item. Users, bylines (re-linked by sync_bylines), settings, menus and plugin settings stay.
Asks for --yes."""
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
media = list_all("/_emdash/api/media"); n = 0
for m in media:
    try: api("DELETE", f"/_emdash/api/media/{m['id']}"); n += 1
    except Exception as e: print("media", m["id"], str(e)[:80])
print(f"media: {n} deleted")
for coll in ("posts", "pages"):
    print(coll, "left:", len(list_all(f"/_emdash/api/content/{coll}")))
print("media left:", len(list_all("/_emdash/api/media")))
