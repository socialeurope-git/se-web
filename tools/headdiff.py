#!/usr/bin/env python3
"""Compare <head> tag sequences (title/meta/link/ld+json) between a live snapshot and the candidate page. Usage: headdiff.py <live.html> <url>"""
import re,sys,json,urllib.request,difflib
def tags(h):
    head=re.search(r'<head>(.*?)</head>',h,re.S).group(1); out=[]
    for m in re.finditer(r'<title>.*?</title>|<meta[^>]*>|<link[^>]*>|<script type="application/ld\+json"[^>]*>.*?</script>',head,re.S):
        t=re.sub(r'\s+',' ',m.group(0)).strip()
        if t.startswith('<link') and ('stylesheet' in t or 'modulepreload' in t or 'preload' in t): continue
        if 'ld+json' in t:
            body=re.search(r'>(.*)</script>',t,re.S).group(1)
            try: t='LD:'+json.dumps(json.loads(body),sort_keys=True,ensure_ascii=False)
            except Exception: t='LD-unparsable:'+body[:80]
        out.append(t)
    return out
a=tags(open(sys.argv[1]).read()); b=tags(urllib.request.urlopen(sys.argv[2]).read().decode())
print(f'live {len(a)} tags, candidate {len(b)} tags, identical: {a==b}')
for l in difflib.unified_diff(a,b,lineterm='',n=0):
    if l.startswith(('+++','---','@@')): continue
    print(l[:400])
