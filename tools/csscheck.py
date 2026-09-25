#!/usr/bin/env python3
"""Compare geometry + computed styles of selectors between two URLs. Usage: csscheck.py <urlA> <urlB> <width> sel1 sel2 ..."""
import asyncio, sys, json
from playwright.async_api import async_playwright
A,B,W=sys.argv[1],sys.argv[2],int(sys.argv[3]); SELS=sys.argv[4:]
PROPS=["display","position","margin-top","margin-bottom","padding-top","padding-bottom","font-size","line-height","font-family","font-weight","width","height","box-sizing","border-top-width","gap","row-gap","column-gap","flex-direction","grid-template-columns","letter-spacing","color","background-color"]
JS="""(args)=>{const [sels,props]=args; const out={}; for (const s of sels){ const el=document.querySelector(s); if(!el){out[s]=null;continue;} const cs=getComputedStyle(el); const r=el.getBoundingClientRect(); const o={rect:[Math.round(r.x),Math.round(r.y+window.scrollY),Math.round(r.width),Math.round(r.height)],tag:el.tagName,cls:el.className}; for(const p of props) o[p]=cs.getPropertyValue(p); out[s]=o;} return out;}"""
async def grab(pw,url):
    b=await pw.chromium.launch(); ctx=await b.new_context(viewport={'width':W,'height':900}); p=await ctx.new_page(); await p.goto(url,wait_until='load'); await p.add_style_tag(content='#right-sidebar{visibility:hidden}'); await p.wait_for_timeout(800)
    r=await p.evaluate(JS,[SELS,PROPS]); await b.close(); return r
async def main():
    async with async_playwright() as pw:
        a,b=await grab(pw,A),await grab(pw,B)
    for s in SELS:
        x,y=a.get(s),b.get(s)
        if x is None or y is None: print(f'{s}: MISSING in', 'A' if x is None else 'B'); continue
        diffs={k:(x[k],y[k]) for k in x if x[k]!=y[k]}
        print(f'{s}: {"same" if not diffs else diffs}')
asyncio.run(main())
