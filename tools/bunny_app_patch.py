#!/usr/bin/env python3
"""Align the Bunny Magic Containers app "SE EmDash" with the official EmDash Node.js layout:
container port 4321, volume at /app/data, DATABASE_PATH, S3 by S3_* (no SE_STORAGE), EMDASH_SITE_URL.
Usage: bunny_app_patch.py [site_url]   (default: the staging endpoint)"""
import json, os, sys, time, urllib.request
K = open(os.path.expanduser("~/.config/se-ebooks/bunny-api-key")).read().strip()
H = {"AccessKey": K, "Accept": "application/json", "Content-Type": "application/json"}
APP = "M2IE2fr9dVHjjff"; BASE = f"https://api.bunny.net/mc/apps/{APP}"
enc = open(os.path.expanduser("~/.config/se-web/emdash-encryption-key")).read().strip()
s3key = open(os.path.expanduser("~/.config/se-web/bunny-storage-key")).read().strip()
site = sys.argv[1] if len(sys.argv) > 1 else "https://mc-hdck3f7ufk.bunny.run"
a = json.load(urllib.request.urlopen(urllib.request.Request(BASE, headers=H)))
t = a["containerTemplates"][0]
env = [("NODE_ENV", "production"), ("HOST", "0.0.0.0"), ("PORT", "4321"), ("DATABASE_PATH", "/app/data/data.db"), ("EMDASH_ENCRYPTION_KEY", enc), ("EMDASH_SITE_URL", site),
       ("S3_ENDPOINT", "https://de-s3.storage.bunnycdn.com"), ("S3_BUCKET", "se-media"), ("S3_ACCESS_KEY_ID", "se-media"), ("S3_SECRET_ACCESS_KEY", s3key), ("S3_REGION", "de"), ("SE_LINK_ORIGIN", site)]
probe = lambda delay, fail: {"initialDelaySeconds": delay, "periodSeconds": 5, "timeoutSeconds": 3, "failureThreshold": fail, "successThreshold": 1, "httpGet": {"request": {"path": "/health", "portNumber": 4321}, "response": {"expectedStatusCode": "200"}}}
eps = [{"id": e["id"], "displayName": e["displayName"], "cdn": {"isSslEnabled": e["isSslEnabled"], "pullZoneId": int(e["pullZoneId"]), "portMappings": [{"containerPort": 4321, "protocols": ["tcp"]}]}} for e in t["endpoints"]]
tpl = {"id": t["id"], "name": t["name"], "imageNamespace": t["imageNamespace"], "imageName": t["imageName"], "imageTag": t["imageTag"], "imageRegistryId": str(t["imageRegistryId"]), "imagePullPolicy": "always",
       "environmentVariables": [{"name": n, "value": v} for n, v in env], "endpoints": eps, "volumeMounts": [{"name": "data", "mountPath": "/app/data"}], "probes": {"startup": probe(10, 60), "readiness": probe(5, 12)}}   # first request runs migrations/seed: give the process minutes, not seconds
for attempt in range(5):
    req = urllib.request.Request(BASE, data=json.dumps({"containerTemplates": [tpl]}).encode(), headers=H, method="PATCH")
    try:
        with urllib.request.urlopen(req) as r: d = json.load(r); print("patched:", d.get("status"), "port", d["containerTemplates"][0]["endpoints"][0]["portMappings"], "mount", d["containerTemplates"][0]["volumeMounts"]); break
    except urllib.error.HTTPError as e: print("attempt", attempt, e.code, e.read().decode()[:200]); time.sleep(20)
for i in range(30):
    st = json.load(urllib.request.urlopen(urllib.request.Request(BASE, headers=H))).get("status"); print(time.strftime("%H:%M:%S"), st)
    if st == "active": break
    time.sleep(15)
