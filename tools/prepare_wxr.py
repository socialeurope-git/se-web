#!/usr/bin/env python3
"""WordPress export pre-pass before the EmDash import. Fixes source quirks the importer would otherwise carry over:
  1. figures nested inside heading blocks (<h2 class="wp-block-heading"><figure>…) -> own image blocks (the importer
     keeps the heading text and drops the image)
  2. raw line breaks inside the HTML (editor/paste artefacts): the importer keeps them as "\\n" in the text and EmDash
     renders them as hard breaks the live site never had -> collapsed to a space, except inside <pre>/<code>/<textarea>
  3. &nbsp; -> normal space (typewriter double spaces and glued words)
  4. empty headings and empty paragraphs removed; anchors with junk targets (about:blank, file:, empty) or with no
     text unwrapped
Usage: prepare_wxr.py <in.xml> <out.xml>"""
import re, sys, html as H
src = open(sys.argv[1], encoding="utf-8").read()
stats = {"figures moved out of headings": 0, "newlines collapsed": 0, "nbsp": 0, "empty headings": 0, "empty paragraphs": 0, "junk anchors unwrapped": 0, "empty anchors removed": 0}
def fix_heading(m):
    tag, attrs, inner = m.group(1), m.group(2), m.group(3)
    figs = re.findall(r"<figure[^>]*>[\s\S]*?</figure>", inner)
    if not figs: return m.group(0)
    rest = inner
    for f in figs: rest = rest.replace(f, "")
    stats["figures moved out of headings"] += len(figs)
    out = "".join(f"<!-- wp:image --><figure class=\"wp-block-image size-large\">{re.sub(r'<figure[^>]*>', '', f, count=1)[:-len('</figure>')]}</figure><!-- /wp:image -->" for f in figs)
    if rest.strip(): out += f"<{tag}{attrs}>{rest}</{tag}>"
    return out
JUNK_HREF = re.compile(r'^\s*(?:about:blank|file:|c:|javascript:|#?\s*$|http://(?:&lt;|<)!--)', re.I)
def clean_body(body):
    b = re.sub(r"<(h[1-6])([^>]*)>([\s\S]*?)</\1>", lambda m: fix_heading(m) if "<figure" in m.group(3) else m.group(0), body)
    # protect preformatted content
    keep = []
    def stash(m): keep.append(m.group(0)); return f"\x00{len(keep) - 1}\x00"
    b = re.sub(r"<(pre|code|textarea)\b[\s\S]*?</\1>", stash, b)
    n = len(re.findall(r"[ \t]*\r?\n[ \t]*", b)); stats["newlines collapsed"] += n
    b = re.sub(r"[ \t]*\r?\n[ \t]*", " ", b)
    stats["nbsp"] += b.count("&nbsp;") + b.count(" "); b = b.replace("&nbsp;", " ").replace(" ", " ")
    # anchors: junk targets -> text only; whitespace-only anchors -> removed
    def anchor(m):
        href = H.unescape(m.group(1) or ""); inner = m.group(2)
        if not inner.strip() and "<img" not in inner: stats["empty anchors removed"] += 1; return " " if inner else ""
        if JUNK_HREF.match(href): stats["junk anchors unwrapped"] += 1; return inner
        return m.group(0)
    b = re.sub(r'<a\b[^>]*?href="([^"]*)"[^>]*>([\s\S]*?)</a>', anchor, b)
    e = len(re.findall(r"<h[1-6][^>]*>\s*</h[1-6]>", b)); stats["empty headings"] += e; b = re.sub(r"<!-- wp:heading[^>]*-->\s*<h[1-6][^>]*>\s*</h[1-6]>\s*<!-- /wp:heading -->|<h[1-6][^>]*>\s*</h[1-6]>", "", b)
    e = len(re.findall(r"<p[^>]*>\s*</p>", b)); stats["empty paragraphs"] += e; b = re.sub(r"<!-- wp:paragraph[^>]*-->\s*<p[^>]*>\s*</p>\s*<!-- /wp:paragraph -->|<p[^>]*>\s*</p>", "", b)
    b = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], b)
    return b
def item(m):
    it = m.group(0)
    return re.sub(r"(<content:encoded><!\[CDATA\[)([\s\S]*?)(\]\]></content:encoded>)", lambda c: c.group(1) + clean_body(c.group(2)) + c.group(3), it)
out = re.sub(r"<item>[\s\S]*?</item>", item, src)
open(sys.argv[2], "w", encoding="utf-8").write(out)
print("prepare_wxr:", ", ".join(f"{v} {k}" for k, v in stats.items()))
