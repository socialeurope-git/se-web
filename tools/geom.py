#!/usr/bin/env python3
"""First geometry mismatch between two pages: walks elements under <root> (default #main) up to <depth>, compares rects in document order.
Usage: geom.py <urlA> <urlB> [root=#main] [depth=4] [width=1440]"""
import asyncio, sys
from playwright.async_api import async_playwright
A,B=sys.argv[1],sys.argv[2]; ROOT=sys.argv[3] if len(sys.argv)>3 else '#main'; DEPTH=int(sys.argv[4]) if len(sys.argv)>4 else 4; W=int(sys.argv[5]) if len(sys.argv)>5 else 1440; MODE=sys.argv[6] if len(sys.argv)>6 else 'rect'   # rect | size (ignore x/y shifts, report every width/height difference)
JS="""([root,depth])=>{const out=[]; const walk=(el,d,path)=>{ if(d>depth) return; for(const c of el.children){ if(['SCRIPT','STYLE','LINK','SOURCE'].includes(c.tagName)) continue; if(c.tagName==='PICTURE'){ walk(c,d,path); continue; } const r=c.getBoundingClientRect(); const cs=getComputedStyle(c); const id=c.tagName.toLowerCase()+(c.id?'#'+c.id:'')+(c.className&&typeof c.className==='string'?'.'+c.className.split(' ').filter(Boolean).slice(0,2).join('.'):''); out.push({p:path+'>'+id, r:[Math.round(r.x),Math.round(r.y+scrollY),Math.round(r.width),Math.round(r.height)], d:cs.display, fs:cs.fontSize, lh:cs.lineHeight, m:cs.marginTop+'/'+cs.marginBottom, pd:cs.paddingTop+'/'+cs.paddingBottom}); walk(c,d+1,path+'>'+id);} }; const r=document.querySelector(root); if(!r) return []; walk(r,1,''); return out;}"""
async def main():
    async with async_playwright() as pw:
        b=await pw.chromium.launch(); res={}
        for name,url in (('A',A),('B',B)):
            p=await b.new_page(viewport={'width':W,'height':900}); await p.goto(url,wait_until='load'); await p.add_style_tag(content='#right-sidebar{visibility:hidden}'); await p.wait_for_timeout(800); res[name]=await p.evaluate(JS,[ROOT,DEPTH]); await p.close()
        await b.close()
    a,bb=res['A'],res['B']; print(f'elements A={len(a)} B={len(bb)}'); shown=0
    for x,y in zip(a,bb):
        if x['p'].split('>')[-1].split('.')[0].split('#')[0]!=y['p'].split('>')[-1].split('.')[0].split('#')[0]: print('STRUCTURE differs at',x['p'],'|',y['p']); break
        same = (x['r'][2:]==y['r'][2:]) if MODE=='size' else (x['r']==y['r'])
        if not same or x['d']!=y['d']:
            print(f"{x['p'][-90:]}\n   A rect={x['r']} disp={x['d']} fs={x['fs']} lh={x['lh']} m={x['m']} pad={x['pd']}\n   B rect={y['r']} disp={y['d']} fs={y['fs']} lh={y['lh']} m={y['m']} pad={y['pd']}"); shown+=1
            if shown>=(40 if MODE=='size' else 6): break
    if not shown: print('no geometry differences within root/depth')
asyncio.run(main())
