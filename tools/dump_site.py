#!/usr/bin/env python3
"""Dump the whole EmDash content of a site (SE_BASE/SE_TOKEN) to archive/dump/<name>.json for audits."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emdash_api import api, list_all, ROOT
out = f"{ROOT}/archive/dump"; os.makedirs(out, exist_ok=True)
def save(name, data): json.dump(data, open(f"{out}/{name}.json", "w")); print(name, len(data) if isinstance(data, list) else "")
save("posts", list_all("/_emdash/api/content/posts"))
save("pages", list_all("/_emdash/api/content/pages"))
save("bylines", list_all("/_emdash/api/admin/bylines"))
save("media", list_all("/_emdash/api/media"))
tax = api("GET", "/_emdash/api/taxonomies")["data"]["taxonomies"]; save("taxonomies", tax)
for t in tax:
    n = t.get("name") or t.get("slug"); save(f"terms-{n}", list_all(f"/_emdash/api/taxonomies/{n}/terms"))
save("widgets", api("GET", "/_emdash/api/widget-areas/sidebar")["data"])
save("settings", api("GET", "/_emdash/api/settings")["data"])
save("menus", api("GET", "/_emdash/api/menus")["data"])
save("redirects", api("GET", "/_emdash/api/redirects?limit=100")["data"])
