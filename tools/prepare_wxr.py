#!/usr/bin/env python3
"""WordPress export pre-pass before the EmDash import: a few posts wrap a figure inside a heading block
(<!-- wp:heading --><h2 class="wp-block-heading"><figure>…<img>…</figure></h2>), which EmDash's importer turns into a
text heading and loses the image. This moves such figures out of the heading into a proper image block.
Usage: prepare_wxr.py <in.xml> <out.xml>"""
import re, sys
src = open(sys.argv[1], encoding="utf-8").read()
n = 0
def fix(m):
    global n
    tag, attrs, inner = m.group(1), m.group(2), m.group(3)
    figs = re.findall(r"<figure[^>]*>[\s\S]*?</figure>", inner)
    if not figs: return m.group(0)
    rest = inner
    for f in figs: rest = rest.replace(f, "")
    n += len(figs)
    out = "".join(f"<!-- wp:image --><figure class=\"wp-block-image size-large\">{re.sub(r'<figure[^>]*>', '', f, count=1)[:-len('</figure>')]}</figure><!-- /wp:image -->" for f in figs)
    if rest.strip(): out += f"<{tag}{attrs}>{rest}</{tag}>"
    return out
out = re.sub(r"<(h[1-6])([^>]*)>([\s\S]*?)</\1>", lambda m: fix(m) if "<figure" in m.group(3) else m.group(0), src)
open(sys.argv[2], "w", encoding="utf-8").write(out)
print(f"prepare_wxr: {n} figures moved out of headings")
