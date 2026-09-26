#!/usr/bin/env python3
"""Drill-down for archive/full-compare.json: refetches the posts that differ and classifies text, heading, link and
legacy differences. Usage: compare_details.py <base> [workers]"""
import gzip, json, re, sys, os, html, urllib.request, concurrent.futures, collections, difflib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); BASE = sys.argv[1].rstrip("/"); W = int(sys.argv[2]) if len(sys.argv) > 2 else 4
res = json.load(open(f"{ROOT}/archive/full-compare.json")); ids = json.load(open(f"{ROOT}/archive/all-map.json"))
def body(h):
    m = re.search(r'<div class="entry-content"[^>]*>(.*?)(?:<footer class="entry-meta|<div class="se-author-profile-box|<div class="post-navigation|</article>)', h, re.S); return m.group(1) if m else ""
def strip_boxes(b):
    for rx in (r'<aside class="se-rel-inline"[\s\S]*?</aside>', r'<div class="wp-block-group se-nl-box[\s\S]*?</form>\s*</div>\s*</div>', r'<div class="se-membership[\s\S]*?</div>\s*</div>', r'<div class="wp-block-group[^"]*se-(?:nl|newsletter)[^"]*"[\s\S]*?</div>\s*</div>\s*</div>', r'<h4 class="wp-block-heading">New publications by our partners[\s\S]*?</figure>', r'<div[^>]*class="[^"]*novashare[^"]*"[\s\S]*?</div>', r'<div class="ns-[^"]*"[^>]*></div>'):
        b = re.sub(rx, "", b)
    return b
def txt(b):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", b, flags=re.S); t = re.sub(r"</?(?:a|em|strong|span|sup|sub|b|i|u|code|small|abbr|cite|mark|s|del|ins)\b[^>]*>", "", t); t = re.sub(r"<[^>]+>", " ", t); t = html.unescape(t).replace("\xa0", " "); t = re.sub(r"(^|\s)\+(?=\s|$)", " ", t); return re.sub(r"\s+", " ", t).strip()
norm = lambda u: re.sub(r"^https?://(www\.)?(socialeurope\.eu|mc-hdck3f7ufk\.bunny\.run)", "", u.split("#")[0].rstrip("/"))
def one(r):
    pid, slug = r["id"], r["slug"]
    try:
        live = strip_boxes(body(gzip.open(f"{ROOT}/archive/live/{pid}.html.gz").read().decode("utf-8", "replace")))
        stg = strip_boxes(body(urllib.request.urlopen(urllib.request.Request(f"{BASE}/{slug}", headers={"User-Agent": "se-compare"}), timeout=90).read().decode("utf-8", "replace")))
    except Exception as e: return {"slug": slug, "error": str(e)[:80]}
    out = {"slug": slug}
    a, b = txt(live), txt(stg)
    if a != b:
        sm = difflib.SequenceMatcher(None, a.split(), b.split(), autojunk=False); ops = [(t, " ".join(a.split()[i1:i2])[:90], " ".join(b.split()[j1:j2])[:90]) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
        out["text_ops"] = ops[:6]; out["text_ops_n"] = len(ops)
    ha = re.findall(r"<h([2-6])\b(?![^>]*wp-block-accordion-heading)[^>]*>(.*?)</h\1>", live, re.S); hb = re.findall(r"<h([2-6])\b[^>]*>(.*?)</h\1>", stg, re.S)
    if len(ha) != len(hb): out["headings"] = {"live": [re.sub(r"<[^>]+>", "", x[1]).strip()[:50] for x in ha], "stg": [re.sub(r"<[^>]+>", "", x[1]).strip()[:50] for x in hb]}
    la = collections.Counter(norm(u) for u in re.findall(r'<a\b[^>]*href="([^"]*)"', live)); lb = collections.Counter(norm(u) for u in re.findall(r'<a\b[^>]*href="([^"]*)"', stg))
    if la != lb: out["links"] = {"live_only": [u for u in (la - lb).elements()][:5], "stg_only": [u for u in (lb - la).elements()][:5]}
    st = collections.Counter(re.sub(r"[\d.]+", "N", m) for m in re.findall(r' style="([^"]*)"', stg))
    if st: out["styles"] = dict(st)
    ep = re.findall(r"<p[^>]*>\s*</p>", stg)
    if ep: out["empty_p"] = len(ep); out["empty_p_ctx"] = [stg[max(0, m.start() - 80):m.start()].replace("\n", " ") for m in re.finditer(r"<p[^>]*>\s*</p>", stg)][:2]
    return out
todo = [r for r in res if "error" in r or not r.get("text_equal") or r["live"] != r["stg"] or any(r["legacy"].values())]
print("posts to drill:", len(todo))
with concurrent.futures.ThreadPoolExecutor(W) as ex: det = list(ex.map(one, todo))
json.dump(det, open(f"{ROOT}/archive/compare-details.json", "w"), indent=0)
errs = [d for d in det if "error" in d]; print("errors", len(errs), errs[:3])
tx = [d for d in det if "text_ops" in d]; print("text differs:", len(tx)); kinds = collections.Counter()
for d in tx:
    for t, x, y in d["text_ops"]: kinds[(t, x[:25], y[:25])] += 1
print("most common text ops:", kinds.most_common(12))
print("biggest text diffs:", [(d["slug"], d["text_ops_n"], d["text_ops"][:2]) for d in sorted(tx, key=lambda d: -d["text_ops_n"])[:8]])
hd = [d for d in det if "headings" in d]; print("headings differ:", len(hd), [(d["slug"], d["headings"]) for d in hd[:6]])
lk = [d for d in det if "links" in d]; print("links differ:", len(lk), "| with live-only hrefs (possible loss):", len([d for d in lk if d["links"]["live_only"]]), [(d["slug"], d["links"]) for d in lk if d["links"]["live_only"]][:8])
st = collections.Counter();
for d in det:
    for k, v in d.get("styles", {}).items(): st[k] += 1
print("inline styles (posts):", st.most_common(10))
ep = [d for d in det if "empty_p" in d]; print("empty p:", len(ep), [(d["slug"], d["empty_p_ctx"]) for d in ep[:3]])
