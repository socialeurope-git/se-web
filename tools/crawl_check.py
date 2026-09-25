#!/usr/bin/env python3
"""Every URL of the live sitemap (posts, pages, home) must answer 200 on the local site; plus the archive pages of the crawl.
Usage: crawl_check.py [base=http://127.0.0.1:4321]"""
import json, sys, os, urllib.request, urllib.parse, concurrent.futures, re, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4321"
urls = ["/"] + [f"/{p['slug']}" for p in json.load(open(f"{ROOT}/archive/posts.json"))] + [f"/{p['slug']}" for p in json.load(open(f"{ROOT}/archive/pages.json"))]
for f in glob.glob(f"{ROOT}/archive/live-archive/*.html.gz"):
    m = re.match(r"(page|cat-[a-z]+)-(\d+)\.html\.gz", os.path.basename(f))
    if not m: continue
    kind, n = m.group(1), int(m.group(2))
    base = "" if kind == "page" else f"/category/{kind[4:]}"
    urls.append((base or "/") if n == 1 else f"{base}/page/{n}")
def check(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + urllib.parse.quote(u, safe="/?=&"), headers={"User-Agent": "crawl-check"}), timeout=60) as r: return u, r.status
    except urllib.error.HTTPError as e: return u, e.code
    except Exception as e: return u, str(e)[:60]
bad = []
with concurrent.futures.ThreadPoolExecutor(6) as ex:
    for i, (u, st) in enumerate(ex.map(check, urls), 1):
        if st != 200: bad.append((u, st))
        if i % 500 == 0: print(i, "checked,", len(bad), "not 200", flush=True)
print(f"{len(urls)} URLs, {len(urls) - len(bad)} ok, {len(bad)} not 200"); print(bad[:20])
json.dump(bad, open(f"{ROOT}/archive/crawl-bad.json", "w"), indent=1)
