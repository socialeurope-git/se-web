#!/usr/bin/env python3
"""Upload uploads-mirror/ into the Bunny storage zone (same relative paths, wp-content/uploads/<y>/<m>/<file>).
Idempotent via uploads-mirror/_uploaded.json. Key: ~/.config/se-web/bunny-storage-key, zone: ~/.config/se-web/bunny-storage-zone."""
import json, os, mimetypes, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SRC = os.path.join(ROOT, 'uploads-mirror')
CFG = json.load(open(os.path.expanduser('~/.config/se-web/bunny-storage-zone'))); KEY = open(os.path.expanduser('~/.config/se-web/bunny-storage-key')).read().strip()
BASE = f"https://{CFG['host']}/{CFG['name']}/"
MAN = os.path.join(SRC, '_uploaded.json'); done = set(json.load(open(MAN))) if os.path.exists(MAN) else set()
mimetypes.add_type('image/avif', '.avif'); mimetypes.add_type('image/webp', '.webp')
files = [os.path.relpath(os.path.join(d, f), SRC) for d, _, fs in os.walk(SRC) for f in fs if not f.startswith('_') and not f.endswith('.part')]
todo = [f for f in files if f not in done]; print('files', len(files), 'todo', len(todo), flush=True)
errors = {}
def put(rel):
    data = open(os.path.join(SRC, rel), 'rb').read()
    req = urllib.request.Request(BASE + urllib.parse.quote(rel), data=data, method='PUT', headers={'AccessKey': KEY, 'Content-Type': mimetypes.guess_type(rel)[0] or 'application/octet-stream'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return rel if r.status in (200, 201) else None
    except Exception as e: errors[rel] = str(e)[:120]; return None
with ThreadPoolExecutor(16) as ex:
    for i, r in enumerate(ex.map(put, todo), 1):
        if r: done.add(r)
        if i % 500 == 0: print(i, 'uploaded', len(done), 'errors', len(errors), flush=True); json.dump(sorted(done), open(MAN, 'w'))
json.dump(sorted(done), open(MAN, 'w')); print('done', len(done), 'errors', len(errors), list(errors.items())[:5])
