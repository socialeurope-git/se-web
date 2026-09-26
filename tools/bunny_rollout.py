#!/usr/bin/env python3
"""Force a rollout of the Bunny Magic Containers app: a plain POST /deploy does nothing when the spec is unchanged (and a
stuck "progressing" pod stays stuck), so the EmDash template gets a fresh SE_ROLLOUT marker, then /deploy, then status +
/health polling until the CDN serves the app again. Usage: bunny_rollout.py [app_id] [health_url]"""
import json, os, sys, time, urllib.request
app = sys.argv[1] if len(sys.argv) > 1 else "M2IE2fr9dVHjjff"; health = sys.argv[2] if len(sys.argv) > 2 else "https://mc-hdck3f7ufk.bunny.run/health"
key = open(os.path.expanduser("~/.config/se-ebooks/bunny-api-key")).read().strip()
def api(m, p, b=None):
    r = urllib.request.Request(f"https://api.bunny.net/mc{p}", method=m, headers={"AccessKey": key, "Accept": "application/json", "Content-Type": "application/json"}, data=json.dumps(b).encode() if b is not None else None)
    try:
        raw = urllib.request.urlopen(r).read(); return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e: raise SystemExit(f"{m} {p} -> {e.code} {e.read()[:300]}")
a = api("GET", f"/apps/{app}"); main = next(c for c in a["containerTemplates"] if c["name"] == "emdash")
env = [e for e in main["environmentVariables"] if e["name"] != "SE_ROLLOUT"] + [{"name": "SE_ROLLOUT", "value": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())}]
api("PATCH", f"/apps/{app}/containers/{main['id']}", {"environmentVariables": env}); api("POST", f"/apps/{app}/deploy"); print("rollout requested", env[-1]["value"])
for i in range(60):
    time.sleep(15); st = api("GET", f"/apps/{app}")["status"]
    try: h = urllib.request.urlopen(health, timeout=10).status
    except Exception as e: h = getattr(e, "code", str(e)[:30])
    print(time.strftime("%H:%M:%S"), st, h, flush=True)
    if st == "active" and h == 200: break
