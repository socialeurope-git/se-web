#!/usr/bin/env python3
"""Add (or update) the backup sidecar container to the Bunny Magic Containers app: same /app/data volume as the EmDash
container, image ghcr.io/socialeurope-git/se-web-backup:latest, env from the app container (S3_*) plus BACKUP_* from
~/.config/se-web/backup.env (BACKUP_BUCKET, BACKUP_PREFIX, BACKUP_ENDPOINT, BACKUP_REGION, BACKUP_ACCESS_KEY_ID,
BACKUP_SECRET_ACCESS_KEY, BACKUP_HEARTBEAT_URL, MEDIA_HEARTBEAT_URL).  Usage: bunny_backup_container.py [app_id]"""
import json, os, sys, urllib.request
app = sys.argv[1] if len(sys.argv) > 1 else "M2IE2fr9dVHjjff"
key = open(os.path.expanduser("~/.config/se-ebooks/bunny-api-key")).read().strip()
def api(method, path, body=None):
    r = urllib.request.Request(f"https://api.bunny.net/mc{path}", method=method, headers={"AccessKey": key, "Accept": "application/json", "Content-Type": "application/json"}, data=json.dumps(body).encode() if body is not None else None)
    try:
        raw = urllib.request.urlopen(r).read()
        return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e: raise SystemExit(f"{method} {path} -> {e.code} {e.read()[:400]}")
env = dict(l.strip().split("=", 1) for l in open(os.path.expanduser("~/.config/se-web/backup.env")) if "=" in l and not l.startswith("#"))
a = api("GET", f"/apps/{app}")
main = next(c for c in a["containerTemplates"] if c["name"] == "emdash")
inherited = [e for e in main["environmentVariables"] if e["name"].startswith("S3_") or e["name"] in ("SE_OPS_TOKEN", "PORT")]
vars_ = inherited + [{"name": k, "value": v} for k, v in env.items()]
existing = next((c for c in a["containerTemplates"] if c["name"] == "backup"), None)
body = {"name": "backup", "imageRegistryId": main["imageRegistryId"], "imageNamespace": main["imageNamespace"], "imageName": "se-web-backup", "imageTag": "latest", "imagePullPolicy": "always",
        "environmentVariables": vars_, "volumeMounts": [{"name": main["volumeMounts"][0]["name"], "mountPath": "/app/data"}], "endpoints": [], "entryPoint": {"command": "", "commandArray": [], "arguments": "", "argumentsArray": [], "workingDirectory": ""}}
if existing:
    r = api("PATCH", f"/apps/{app}/containers/{existing['id']}", body); print("updated backup container", existing["id"])
else:
    r = api("POST", f"/apps/{app}/containers", body); print("created backup container", (r or {}).get("id"))
print("deploy:", api("POST", f"/apps/{app}/deploy") or "ok")
