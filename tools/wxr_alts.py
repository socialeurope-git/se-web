#!/usr/bin/env python3
"""Alt texts from the WordPress export: attachment URL -> alt (postmeta _wp_attachment_image_alt) and post slug -> alt of
its featured image (_thumbnail_id). Writes archive/alts.json for tools/clean_content.mjs and tools/media_meta.py.
Usage: wxr_alts.py <wxr.xml>"""
import re, json, html, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
x = open(sys.argv[1], encoding="utf-8").read()
def val(it, tag):
    m = re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>", it, re.S); return m.group(1) if m else None
def meta(it, key):
    m = re.search(rf"<wp:meta_key>(?:<!\[CDATA\[)?{re.escape(key)}(?:\]\]>)?</wp:meta_key>\s*<wp:meta_value>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</wp:meta_value>", it, re.S); return m.group(1) if m else None
alts, attach, thumbs = {}, {}, {}
for it in re.findall(r"<item>(.*?)</item>", x, re.S):
    t, pid = val(it, "wp:post_type"), val(it, "wp:post_id")
    if t == "attachment":
        u, a = val(it, "wp:attachment_url"), meta(it, "_wp_attachment_image_alt")
        if u: attach[pid] = u
        if u and a and a.strip(): alts[u] = html.unescape(a.strip())
    elif t in ("post", "page"):
        th, s = meta(it, "_thumbnail_id"), val(it, "wp:post_name")
        if th and s: thumbs[s] = th
feat = {s: alts.get(attach.get(t, ""), "") for s, t in thumbs.items()}
json.dump({"alts": alts, "featured": feat, "attach": attach}, open(f"{ROOT}/archive/alts.json", "w"))
print(f"alts: {len(alts)} attachments with alt text, {sum(1 for v in feat.values() if v)} featured images with alt text")
