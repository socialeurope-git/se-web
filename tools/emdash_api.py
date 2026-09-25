"""Shared EmDash API access for the import tools.
Target and credentials come from the environment, so the same scripts run against the local dev server and staging:
  SE_BASE   default http://127.0.0.1:4321
  SE_TOKEN  API token (Bearer); without it the admin session cookie jar archive/jar.txt is used (local dev-bypass)."""
import json, os, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get("SE_BASE", "http://127.0.0.1:4321").rstrip("/")
TOKEN = os.environ.get("SE_TOKEN", "")
def _cookie():
    p = os.path.join(ROOT, "archive", "jar.txt")
    if not os.path.exists(p): return ""
    c = []
    for line in open(p):
        if line.startswith("#HttpOnly_"): line = line[10:]
        if not line.strip() or line.startswith("#"): continue
        f = line.rstrip("\n").split("\t")
        if len(f) >= 7: c.append(f"{f[5]}={f[6]}")
    return "; ".join(c)
def headers(content_type="application/json"):
    h = {"X-EmDash-Request": "1"}
    if content_type: h["Content-Type"] = content_type
    if TOKEN: h["Authorization"] = f"Bearer {TOKEN}"
    else: h["Cookie"] = _cookie()
    return h
def api(method, path, body=None, ok404=False, timeout=600):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None, headers=headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        if ok404 and e.code == 404: return None
        raise SystemExit(f"{method} {path} -> {e.code}: {e.read()[:400]}")
def api_raw(method, path, data, content_type, timeout=3600):
    """Raw body (multipart etc.)."""
    req = urllib.request.Request(BASE + path, method=method, data=data, headers=headers(content_type))
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)
def list_all(path, limit=100, key="items"):
    """Cursor-paged listing (content, bylines, media)."""
    out, cursor = [], None
    while True:
        d = api("GET", f"{path}{'&' if '?' in path else '?'}limit={limit}" + (f"&cursor={cursor}" if cursor else ""))["data"]
        items = d.get(key) if isinstance(d, dict) else d
        out.extend(items or [])
        cursor = d.get("nextCursor") if isinstance(d, dict) else None
        if not cursor: break
    return out
def entries(collection, fields=None):
    """All entries of a collection: id, slug, status, data (content included)."""
    return list_all(f"/_emdash/api/content/{collection}")
