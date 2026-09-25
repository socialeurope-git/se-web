#!/usr/bin/env python3
"""List CSS rules (with the property) that match an element, in cascade order, for two URLs. Usage: rules.py <urlA> <urlB> <selector> <property>"""
import asyncio, sys
from playwright.async_api import async_playwright
A,B,SEL,PROP=sys.argv[1:5]
JS="""([sel,prop])=>{const el=document.querySelector(sel); if(!el) return ['MISSING']; const out=[]; let si=0; for(const ss of document.styleSheets){ let rules=[]; try{rules=ss.cssRules}catch(e){continue;} const walk=(rs,media)=>{for(const r of rs){ if(r.cssRules&&r.media){ if(window.matchMedia(r.media.mediaText).matches) walk(r.cssRules,r.media.mediaText); continue;} if(r.selectorText){ let m=false; try{m=el.matches(r.selectorText)}catch(e){} if(m&&r.style.getPropertyValue(prop)) out.push(`[sheet ${si}${media?' @'+media:''}] ${r.selectorText.slice(0,80)} { ${prop}: ${r.style.getPropertyValue(prop)} ${r.style.getPropertyPriority(prop)} }`);} } }; walk(rules,null); si++; } out.push('computed: '+getComputedStyle(el).getPropertyValue(prop)); out.push('inline style attr: '+(el.getAttribute('style')||'')); return out;}"""
async def main():
    async with async_playwright() as pw:
        b=await pw.chromium.launch()
        for name,url in (('CONTROL',A),('CANDIDATE',B)):
            ctx=await b.new_context(viewport={'width':1440,'height':900}); p=await ctx.new_page(); await p.goto(url,wait_until='load'); await p.wait_for_timeout(500)
            r=await p.evaluate(JS,[SEL,PROP]); print(f'== {name}'); [print('  ',x) for x in r]; await ctx.close()
        await b.close()
asyncio.run(main())
