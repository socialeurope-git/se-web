#!/usr/bin/env python3
"""Cut the rendered archive card (GP Post Archive Template) of every post out of the crawled listing pages.
Writes archive/cards/<id>.html. Usage: cards_from_archive.py <archive_dir>"""
import re, os, sys, gzip, glob
A=sys.argv[1]; os.makedirs(f'{A}/cards',exist_ok=True); n=0; seen=set()
files=sorted(glob.glob(f'{A}/live-archive/page-*.html.gz'), key=lambda x:int(re.search(r'page-(\d+)',x).group(1)))+sorted(glob.glob(f'{A}/live-archive/cat-*.html.gz'))
for f in files:
    h=gzip.open(f,'rt',encoding='utf-8',errors='replace').read()
    for m in re.finditer(r'<article id="post-(\d+)" class="dynamic-content-template[^"]*">',h):
        pid=int(m.group(1)); i=m.start(); depth=0; end=None
        for t in re.finditer(r'<(/?)article\b[^>]*>',h[i:]):
            depth+= -1 if t.group(1) else 1
            if depth==0: end=i+t.end(); break
        card=h[i:end]
        if pid in seen: continue
        if 'featured-column' in card[:300]:
            # homepage first-post template -> convert back to the ordinary card markup
            card=re.sub(r'<div class="wp-block-columns[\s\S]*?</div>\s*</div>\s*','',card,count=1)
            card=card.replace('grid-100 featured-column','grid-50').replace('gb-media-dcd63dc2','gb-media-f4b1d94b').replace(' fetchpriority="high"','')
            card=card.replace('<div style="height:20px" aria-hidden="true" class="wp-block-spacer"></div>','<div style="height:13px" aria-hidden="true" class="wp-block-spacer"></div>')
            card=card.replace('gb-text-dc4dac1e','gb-text-b1a124d0').replace('gb-text-7fb6cf2d','gb-text-e4c86b08')
            # ordinary cards wrap the body in <div> ... <div class="gb-element-4b1f01c5"> and end with 0px spacers; rebuild that shell
            m=re.search(r'(<a href="[^"]+"><picture>[\s\S]*?</picture></a>)([\s\S]*)</article>',card)
            if m:
                body=m.group(2).strip()
                card=card[:card.find('>')+1]+'\n<div>\n'+m.group(1)+'\n\n\n\n<div class="gb-element-4b1f01c5">\n'+body+'\n\n\n\n<div style="height:0px" aria-hidden="true" class="wp-block-spacer"></div>\n\n\n\n<div style="height:0px" aria-hidden="true" class="wp-block-spacer"></div>\n</div>\n</div>\n</article>'
            if os.path.exists(f'{A}/cards/{pid}.html'): continue
        seen.add(pid); open(f'{A}/cards/{pid}.html','w').write(card); n+=1
print('cards written:',n)
