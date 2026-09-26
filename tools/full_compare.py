#!/usr/bin/env python3
"""Whole-archive content comparison, live WordPress snapshot vs the EmDash site, plus a legacy scan of the rendered HTML.
For every post in archive/all-map.json: the article body (entry-content, without the injected theme boxes) of the live
snapshot (archive/live/<id>.html.gz) and of the EmDash page are reduced to text, headings, images and links and compared.
Usage: full_compare.py <base> [workers]   -> archive/full-compare.json + summary on stdout"""
import gzip, json, re, sys, os, html, urllib.request, concurrent.futures, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = sys.argv[1].rstrip("/"); WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 8
ids = json.load(open(f"{ROOT}/archive/all-map.json"))
if len(sys.argv) > 3: ids = dict(list(ids.items())[: int(sys.argv[3])])
# theme boxes injected into the body on both sides (newsletter, related, membership, partner banner, author box, share)
CUT = re.compile(r'<(?:div|aside|section)[^>]*class="[^"]*(?:se-nl-box|se-newsletter|se-rel-inline|se-rel-band|se-most|se-membership|se-partner|se-author-profile-box|ns-|novashare|se-key-insights__placeholder)[^"]*"[^>]*>.*?</(?:div|aside|section)>', re.S)
INJ = re.compile(r'<!--\s*se:(?:nl|related|membership|partner)[^>]*-->.*?<!--\s*/se:[^>]*-->', re.S)
def body(h):
    m = re.search(r'<div class="entry-content"[^>]*>(.*?)(?:<footer class="entry-meta|<div class="se-author-profile-box|<div class="post-navigation|</article>)', h, re.S)
    return m.group(1) if m else ""
def strip_boxes(b):
    # remove known injected blocks by their outer markers (newsletter box, related, membership, partner banner, sharing)
    for rx in (r'<div class="wp-block-group se-nl-box[\s\S]*?</form>\s*</div>\s*</div>', r'<aside class="se-rel-inline"[\s\S]*?</aside>', r'<div class="se-membership[\s\S]*?</div>\s*</div>', r'<div class="wp-block-group[^"]*se-(?:nl|newsletter)[^"]*"[\s\S]*?</div>\s*</div>\s*</div>', r'<h4 class="wp-block-heading">New publications by our partners[\s\S]*?</figure>', r'<div[^>]*class="[^"]*novashare[^"]*"[\s\S]*?</div>', r'<div class="ns-[\s\S]*?</div>'):
        b = re.sub(rx, "", b)
    return b
def norm_text(b):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", b, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t); t = html.unescape(t).replace("\xa0", " ")
    t = re.sub(r"(^|\s)\+(?=\s|$)", " ", t)   # the accordion's "+" icon is text on live, CSS here
    return re.sub(r"\s+", " ", t).strip()
def features(h):
    b = strip_boxes(body(h))
    return {"text": norm_text(b), "imgs": len(re.findall(r"<img\b", b)), "h": len(re.findall(r"<h[2-6]\b(?![^>]*wp-block-accordion-heading)", b)), "links": len(re.findall(r"<a\b[^>]*href=", b)), "tables": len(re.findall(r"<table\b", b)), "details": len(re.findall(r"<details\b|wp-block-accordion-item\b", b))}
LEGACY = {"wp-block class": r'class="[^"]*wp-block-', "data-wp": r"data-wp-", "picture": r"<picture", "sp-no-webp": r"sp-no-webp", "wp-image-N": r"wp-image-\d", "nbsp": r"&nbsp;", "wp-content/uploads (own)": r"socialeurope\.eu/wp-content/uploads", "inline style": r' style="', "absolute self-link": r'href="https?://(?:www\.)?socialeurope\.eu/', "empty p": r"<p[^>]*>\s*</p>"}
def one(pid):
    slug = ids[pid]
    try: live = gzip.open(f"{ROOT}/archive/live/{pid}.html.gz").read().decode("utf-8", "replace")
    except Exception as e: return {"id": pid, "slug": slug, "error": f"no live snapshot: {e}"}
    try:
        req = urllib.request.Request(f"{BASE}/{slug}", headers={"User-Agent": "se-compare"}); stg = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    except Exception as e: return {"id": pid, "slug": slug, "error": f"fetch: {e}"}
    a, b = features(live), features(stg)
    body_stg = strip_boxes(body(stg))
    # theme partials inside the body (newsletter box, membership, partner banner) carry wp-block classes by design; count only inside blocks that are content
    legacy = {k: len(re.findall(rx, body_stg)) for k, rx in LEGACY.items()}
    ratio = 1.0 if a["text"] == b["text"] else (min(len(a["text"]), len(b["text"])) / max(1, max(len(a["text"]), len(b["text"]))))
    # word-level difference count
    wa, wb = a["text"].split(), b["text"].split()
    import difflib
    sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False) if abs(len(wa) - len(wb)) < 400 else None
    words_changed = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal") if sm else abs(len(wa) - len(wb))
    return {"id": pid, "slug": slug, "live": {k: v for k, v in a.items() if k != "text"}, "stg": {k: v for k, v in b.items() if k != "text"}, "text_equal": a["text"] == b["text"], "words_changed": words_changed, "words": len(wa), "legacy": legacy}
res = []
with concurrent.futures.ThreadPoolExecutor(WORKERS) as ex:
    for i, r in enumerate(ex.map(one, list(ids))):
        res.append(r)
        if i % 500 == 0: print(f"{i}/{len(ids)}", flush=True)
json.dump(res, open(f"{ROOT}/archive/full-compare.json", "w"), indent=0)
errs = [r for r in res if "error" in r]; ok = [r for r in res if "error" not in r]
print(f"posts {len(res)}, errors {len(errs)}, text identical {sum(1 for r in ok if r['text_equal'])}, text differs {sum(1 for r in ok if not r['text_equal'])}")
print("word changes histogram:", dict(sorted(collections.Counter(min(r["words_changed"], 50) // 5 * 5 for r in ok if not r["text_equal"]).items())))
for k in ("imgs", "h", "links", "tables"):
    d = [(r["slug"], r["live"][k], r["stg"][k]) for r in ok if r["live"][k] != r["stg"][k]]
    print(f"{k} differ: {len(d)}", d[:6])
leg = collections.Counter()
for r in ok:
    for k, v in r["legacy"].items():
        if v: leg[k] += 1
print("legacy patterns in rendered bodies (posts affected):", dict(leg))
print("errors:", errs[:5])
