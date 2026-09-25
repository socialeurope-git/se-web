#!/usr/bin/env python3
"""Mirror every known /wp-content/uploads/ file (archive/media-urls.json) from the live CDN into uploads-mirror/
keeping the wp-content/uploads/<year>/<month>/<file> layout. Idempotent; writes uploads-mirror/_failed.json."""
import json, os, sys, asyncio, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(ROOT, 'uploads-mirror'); urls = json.load(open(os.path.join(ROOT, 'archive/media-urls.json')))
failed = {}
def fetch(u):
    rel = urllib.parse.unquote(u.split('/wp-content/uploads/', 1)[1]); out = os.path.join(DST, 'wp-content/uploads', rel)
    if os.path.exists(out): return 'skip'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    try:
        req = urllib.request.Request(urllib.parse.quote(u, safe='/:%'), headers={'User-Agent': 'se-media-mirror/1.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            ct = r.headers.get('content-type', '')
            data = r.read()
        if ct.startswith('text/html'): failed[u] = 'html:' + ct; return 'html'
        open(out + '.part', 'wb').write(data); os.replace(out + '.part', out); return 'ok'
    except Exception as e: failed[u] = str(e)[:120]; return 'err'
with ThreadPoolExecutor(16) as ex:
    n = {}
    for i, s in enumerate(ex.map(fetch, urls), 1):
        n[s] = n.get(s, 0) + 1
        if i % 1000 == 0: print(i, n, flush=True)
print('done', n); json.dump(failed, open(os.path.join(DST, '_failed.json'), 'w'), indent=1)
