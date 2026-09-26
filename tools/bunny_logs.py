#!/usr/bin/env python3
"""Container logs of the Bunny Magic Containers app: bunny_logs.py [app_id] [limit] [grep]  (API key ~/.config/se-ebooks/bunny-api-key)"""
import json, os, sys, urllib.request
app = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit() else "M2IE2fr9dVHjjff"
limit = next((a for a in sys.argv[1:] if a.isdigit()), "100"); pat = sys.argv[-1] if len(sys.argv) > 2 and not sys.argv[-1].isdigit() and sys.argv[-1] != app else ""
key = open(os.path.expanduser("~/.config/se-ebooks/bunny-api-key")).read().strip()
r = urllib.request.Request(f"https://api.bunny.net/mc/apps/{app}/logs?limit={limit}", headers={"AccessKey": key, "Accept": "application/json"})
d = json.load(urllib.request.urlopen(r))
items = d if isinstance(d, list) else (d.get("items") or d.get("logs") or [])
if not isinstance(d, list) and not items: print("response:", json.dumps(d)[:300])
for it in sorted(items, key=lambda x: x.get("message", {}).get("time", "")):
    m = it.get("message", {}); log = (m.get("log") if isinstance(m, dict) else str(m)) or ""
    if pat and pat not in log: continue
    print(m.get("time", "")[11:19], (it.get("labels") or {}).get("container", "")[-12:], log.rstrip()[:220])
