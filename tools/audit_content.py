#!/usr/bin/env python3
"""Audit of the imported content in archive/dump/*.json: block types, raw-HTML residue, images, bylines, media usage."""
import json, re, collections, os
D = "archive/dump"
posts = json.load(open(f"{D}/posts.json")); pages = json.load(open(f"{D}/pages.json"))
bylines = json.load(open(f"{D}/bylines.json")); media = json.load(open(f"{D}/media.json"))
widgets = json.load(open(f"{D}/widgets.json")); settings = json.load(open(f"{D}/settings.json"))
C = collections.Counter
media_by_id = {m["id"]: m for m in media}; media_by_key = {m["storageKey"]: m for m in media}
media_url = {m["url"]: m for m in media}
print("== posts", len(posts), "status", C(p["status"] for p in posts), "pages", len(pages), C(p["status"] for p in pages))
print("slugs unique:", len({p["slug"] for p in posts}) == len(posts), "| empty titles:", sum(1 for p in posts if not p["data"].get("title")), "| no publishedAt:", sum(1 for p in posts if not p.get("publishedAt")))
# excerpt
ex = [p["data"].get("excerpt") or "" for p in posts]
print("excerpt: with", sum(1 for e in ex if e.strip()), "| with HTML tags", sum(1 for e in ex if re.search(r"<[a-z]", e)), "| with entities", sum(1 for e in ex if re.search(r"&[a-z#0-9]+;", e)))
# featured image
fi = [p["data"].get("featured_image") for p in posts]
print("featured_image: none", sum(1 for f in fi if not f or not f.get("src")), "| emdash media", sum(1 for f in fi if f and str(f.get("src","")).startswith("/_emdash/api/media/file/")), "| external", sum(1 for f in fi if f and f.get("src") and not str(f["src"]).startswith("/_emdash")), "| no alt", sum(1 for f in fi if f and f.get("src") and not (f.get("alt") or "").strip()))
missing_fi = [(p["slug"], f.get("src")) for p, f in zip(posts, fi) if f and f.get("src","").startswith("/_emdash/api/media/file/") and f["src"] not in media_url]
print("featured_image src not in media list:", len(missing_fi), missing_fi[:3])
# blocks
types = C(); styles = C(); html_posts = 0; html_blocks = 0; per_post_html = C(); img_blocks = 0; img_missing = []; empty_blocks = 0; marks = C(); link_hosts = C(); native_wp_class = 0
for p in posts:
    c = p["data"].get("content") or []
    n_html = 0
    for b in c:
        types[b.get("_type")] += 1
        if b.get("_type") == "block":
            styles[(b.get("style"), b.get("listItem"))] += 1
            txt = "".join(ch.get("text", "") for ch in b.get("children", []))
            if not txt.strip(): empty_blocks += 1
            for ch in b.get("children", []):
                for m in ch.get("marks", []): marks[m if m in ("strong", "em", "code", "underline", "strike") else "annotation"] += 1
            for md in b.get("markDefs", []):
                if md.get("_type") == "link":
                    h = re.match(r"https?://([^/]+)", md.get("href", "") or ""); link_hosts[h.group(1) if h else ("relative" if (md.get("href") or "").startswith("/") else "other:" + str(md.get("href"))[:20])] += 1
        elif b.get("_type") == "htmlBlock": n_html += 1
        elif b.get("_type") == "image":
            img_blocks += 1
            ref = (b.get("asset") or {}).get("_ref"); url = (b.get("asset") or {}).get("url")
            if ref not in media_by_id and url not in media_url: img_missing.append((p["slug"], ref, url))
    if n_html: html_posts += 1; html_blocks += n_html; per_post_html[n_html] += 1
print("block types:", dict(types)); print("block styles:", dict(styles)); print("empty text blocks:", empty_blocks); print("marks:", dict(marks))
print("link hosts (top 12):", link_hosts.most_common(12))
print("image blocks:", img_blocks, "| not resolvable:", len(img_missing), img_missing[:3])
print("posts with htmlBlock:", html_posts, "| htmlBlocks:", html_blocks, "| per post:", dict(sorted(per_post_html.items())))
# html residue
pat = {"picture": r"<picture", "srcset": r"srcset=", "sp-no-webp": r"sp-no-webp", "wp-image-cls": r"wp-image-\d+", "data-wp-": r"data-wp-", "meta-tag": r"<meta ", "style-attr": r" style=\"", "iframe": r"<iframe", "script": r"<script", "nbsp": r"&nbsp;", "wp-content/uploads": r"wp-content/uploads", "self-link-abs": r"https?://(www\.)?socialeurope\.eu/", "table": r"<table", "shortcode": r"\[[a-z_]+[ \]]", "figure": r"<figure", "video": r"<video", "twitter": r"twitter-tweet", "wp-block-embed": r"wp-block-embed", "accordion": r"wp-block-accordion", "wp-block-any": r"wp-block-", "empty-p": r"<p[^>]*>\s*(&nbsp;|\s)*</p>", "font-tag": r"<font", "span-style": r"<span style", "id-attr": r" id=\"", "img": r"<img", "h1": r"<h1", "div": r"<div", "class-attr": r" class=\""}
res = C(); wpcls = C(); tags = C(); samples = collections.defaultdict(list)
for p in posts:
    for b in p["data"].get("content") or []:
        if b.get("_type") != "htmlBlock": continue
        h = b.get("html") or b.get("content") or ""
        for k, r in pat.items():
            if re.search(r, h):
                res[k] += 1
                if len(samples[k]) < 2: samples[k].append(p["slug"])
        for m in re.findall(r'class="([^"]*)"', h):
            for cl in m.split():
                if cl.startswith("wp-block-"): wpcls[cl] += 1
        for t in re.findall(r"<([a-z][a-z0-9]*)", h): tags[t] += 1
print("htmlBlock residue (blocks containing):", dict(res.most_common()))
print("wp-block classes:", wpcls.most_common(25)); print("html tags:", tags.most_common(30))
print("samples:", {k: v for k, v in samples.items()})
# bylines
bl_use = C(); no_byline = 0
for p in posts:
    bs = p.get("bylines") or []
    if not bs: no_byline += 1
    for b in bs: bl_use[b.get("id") if isinstance(b, dict) else b] += 1
print("== bylines", len(bylines), "| posts without byline:", no_byline, "| bylines used:", len(bl_use), "| unused:", len([b for b in bylines if b["id"] not in bl_use]))
names = C(b["displayName"].strip().lower() for b in bylines); print("duplicate names:", [n for n, c in names.items() if c > 1][:10])
print("bylines: with avatar", sum(1 for b in bylines if b.get("avatarMediaId")), "| avatar not in media", sum(1 for b in bylines if b.get("avatarMediaId") and b["avatarMediaId"] not in media_by_id), "| with bio", sum(1 for b in bylines if (b.get("bio") or "").strip()), "| bio with HTML", sum(1 for b in bylines if re.search(r"<[a-z]", b.get("bio") or "")), "| isGuest", sum(1 for b in bylines if b.get("isGuest")), "| website", sum(1 for b in bylines if b.get("websiteUrl")))
print("byline sample:", {k: v for k, v in bylines[0].items() if k in ("slug", "displayName", "bio", "websiteUrl", "customFields", "avatarMediaId")})
# media usage
used = set()
for p in posts + pages:
    f = p["data"].get("featured_image") or {}
    if f.get("src") in media_url: used.add(media_url[f["src"]]["id"])
    for b in p["data"].get("content") or []:
        if b.get("_type") == "image": used.add((b.get("asset") or {}).get("_ref"))
        if b.get("_type") == "htmlBlock":
            for k in re.findall(r"/_emdash/api/media/file/([A-Z0-9]+\.[a-z0-9]+)", b.get("html") or ""): used.add(media_by_key.get(k, {}).get("id"))
for b in bylines:
    if b.get("avatarMediaId"): used.add(b["avatarMediaId"])
for w in (widgets.get("widgets") or []):
    for b in w.get("content") or []:
        if b.get("_type") == "image": used.add((b.get("asset") or {}).get("_ref"))
s = json.dumps(settings)
for m in media:
    if m["id"] in s or m["storageKey"] in s: used.add(m["id"])
unused = [m for m in media if m["id"] not in used]
print("== media", len(media), "| used", len(used & set(media_by_id)), "| unused", len(unused), "| mime", dict(C(m["mimeType"] for m in media)), "| no alt", sum(1 for m in media if not (m.get("alt") or "").strip()), "| total MB", round(sum(m["size"] for m in media) / 1e6))
print("unused sample:", [(m["filename"], m["size"]) for m in unused[:15]])
print("unused by year-ish:", C(re.match(r".*?(\d{4})", m["filename"]).group(1) if re.match(r".*?(\d{4})", m["filename"]) else "-" for m in unused).most_common(8))
print("== pages:", [(p["slug"], p["status"], list(p["data"].keys())) for p in pages])
