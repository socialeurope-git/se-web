#!/usr/bin/env python3
"""Source-quality scan of the imported content (archive/dump/posts.json + pages.json from tools/dump_site.py):
errors that come from the WordPress originals and survive a faithful import. Prints counts with samples and writes
archive/source-quality.json for fixing or asking. Checks: words glued at inline boundaries ("Man’sSoul"), double spaces,
leftover shortcodes, double-encoded entities, broken internal links, typo links, empty image alt, duplicate paragraphs,
blocks starting with punctuation, literal HTML in text."""
import json, re, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = f"{ROOT}/archive/dump"
posts = json.load(open(f"{D}/posts.json")); pages = json.load(open(f"{D}/pages.json"))
slugs = {p["slug"] for p in posts} | {p["slug"] for p in pages}
cats = {t["slug"] for t in json.load(open(f"{D}/terms-category.json"))} if os.path.exists(f"{D}/terms-category.json") else set()
tags = {t["slug"] for t in json.load(open(f"{D}/terms-tag.json"))} if os.path.exists(f"{D}/terms-tag.json") else set()
bylines = {b["slug"] for b in json.load(open(f"{D}/bylines.json"))} if os.path.exists(f"{D}/bylines.json") else set()
issues = collections.defaultdict(list)
def add(kind, slug, sample): issues[kind].append((slug, sample[:140]))
GLUE = re.compile(r"[a-z’'\)\.,;:](?=[A-Z])|[a-zA-Z](?=[\(\[])")   # cheap heuristic on span boundaries only
for p in posts + pages:
    slug = p["slug"]; paras = []
    for b in p["data"].get("content") or []:
        if b.get("_type") == "block":
            ch = b.get("children") or []
            for i in range(1, len(ch)):
                a, c = ch[i - 1].get("text") or "", ch[i].get("text") or ""
                # span boundary without a space where a word ends (lowercase letter or ’s) and a capitalised word starts:
                # "Man’s" + "Soul" — WordPress had <em>The War for Man’s</em><em>Soul</em>
                if a and c and (a[-1].islower() or a.endswith(("’s", "'s", "’", ")"))) and c[0].isupper() and not (ch[i].get("marks") or []) == ["superscript"] and len(c) > 1 and c[1].islower():
                    add("glued words at inline boundary", slug, f"…{a[-25:]}|{c[:25]}…")
            txt = "".join(c.get("text") or "" for c in ch)
            if "  " in txt: add("double spaces", slug, txt[max(0, txt.find("  ") - 40):txt.find("  ") + 40])
            if re.search(r"\[(?:caption|embed|gallery|video|audio|su_[a-z_]+|vc_[a-z_]+)[ \]]", txt): add("leftover shortcode", slug, txt[:120])
            if re.search(r"&(?:amp|#8217|#8220|#8221|nbsp|quot);", txt): add("double-encoded entity", slug, txt[max(0, txt.find("&") - 30):txt.find("&") + 40])
            if re.search(r"<(?:/?[a-z]+)[^>]*>", txt): add("literal HTML in text", slug, txt[max(0, txt.find("<") - 30):txt.find("<") + 60])
            if txt and b.get("style") == "normal" and not b.get("listItem") and re.match(r"^[,.;:)\]]", txt.lstrip()): add("block starts with punctuation", slug, txt[:80])
            if txt.strip() and b.get("style") == "normal" and not b.get("listItem"): paras.append(txt.strip())
            for md in b.get("markDefs") or []:
                if md.get("_type") != "link": continue
                h = md.get("href") or ""
                if h.startswith("/"):
                    path = h.split("?")[0].split("#")[0].strip("/")
                    ok = path in slugs or path.startswith(("category/", "tag/", "author/", "page/", "feed", "_emdash/", "wp-content/")) or path == ""
                    if path.startswith("category/") and path.split("/")[1] not in cats: ok = False
                    if path.startswith("author/") and path.split("/")[1] not in bylines: ok = False
                    if not ok: add("broken internal link", slug, h)
                elif re.match(r"^(?:ttp|htp|ttps|http:/[^/]|www\.)", h): add("typo link", slug, h)
                elif not re.match(r"^(?:https?://|mailto:|tel:|#)", h): add("odd link target", slug, h)
        elif b.get("_type") == "image":
            if not (b.get("alt") or "").strip(): add("image without alt", slug, (b.get("asset") or {}).get("url", ""))
        elif b.get("_type") == "htmlBlock":
            h = b.get("html") or ""
            for m in re.finditer(r"<img\b[^>]*>", h):
                if 'alt=""' in m.group(0) or " alt=" not in m.group(0): add("html image without alt", slug, m.group(0)[:100])
    seen = set()
    for t in paras:
        if len(t) > 60 and t in seen: add("duplicate paragraph", slug, t)
        seen.add(t)
json.dump(issues, open(f"{ROOT}/archive/source-quality.json", "w"), indent=1)
for k, v in sorted(issues.items(), key=lambda kv: -len(kv[1])):
    print(f"{k}: {len(v)} (posts {len({s for s, _ in v})})")
    for s, x in v[:4]: print("   ", s[:45], "|", x)
