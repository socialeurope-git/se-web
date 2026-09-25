#!/usr/bin/env python3
"""Pixel diff: control page (live snapshot served locally) vs candidate (the EmDash theme) per post and width.
Usage: diff.py <out_dir> <control_base> <candidate_base> <widths> <slug_map.json> id [id...]
slug_map.json: {"<id>": "<slug>"}; control URL = <control_base>/<id>.html ; candidate URL = <candidate_base>/<slug>"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright
from PIL import Image, ImageChops, ImageDraw
OUT, CTRL, CAND, WIDTHS, MAP = sys.argv[1], sys.argv[2], sys.argv[3], [int(w) for w in sys.argv[4].split(',')], json.load(open(sys.argv[5]))
ids = sys.argv[6:]; os.makedirs(OUT + '/shots', exist_ok=True); os.makedirs(OUT + '/diffs', exist_ok=True)
MASK = "#right-sidebar{visibility:hidden}"   # ad rotation is random per load
async def shoot(page, url, out):
    await page.goto(url, wait_until='load', timeout=60000)
    await page.add_style_tag(content=MASK)
    await page.wait_for_timeout(300)
    if not await page.evaluate("getComputedStyle(document.querySelector('#right-sidebar')||document.body).visibility==='hidden'"): await page.add_style_tag(content=MASK)
    h = await page.evaluate('document.body.scrollHeight')
    for y in range(0, h, 800): await page.evaluate(f'window.scrollTo(0,{y})'); await page.wait_for_timeout(50)
    await page.evaluate('window.scrollTo(0,0)')
    try: await page.wait_for_load_state('networkidle', timeout=8000)
    except Exception: pass
    try: await page.evaluate("Promise.all([...document.images].map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; })))")   # lazy images must be in before the shot
    except Exception: pass
    await page.wait_for_timeout(400); await page.screenshot(path=out, full_page=True, animations='disabled')
def compare(a, b, out):
    A = Image.open(a).convert('RGB'); B = Image.open(b).convert('RGB'); w = min(A.width, B.width); h = min(A.height, B.height)
    d = ImageChops.difference(A.crop((0, 0, w, h)), B.crop((0, 0, w, h))).convert('L').point(lambda v: 255 if v > 24 else 0)
    bbox = d.getbbox(); n = sum(1 for v in d.getdata() if v) if bbox else 0; pct = 100 * n / (w * h)
    if bbox:
        vis = Image.new('RGB', (A.width + B.width + w + 40, max(A.height, B.height, h)), (90, 90, 90))
        vis.paste(A, (0, 0)); vis.paste(B, (A.width + 20, 0)); dm = Image.new('RGB', (w, h), (255, 255, 255)); dm.paste((220, 0, 0), mask=d); vis.paste(dm, (A.width + B.width + 40, 0))
        s = 1600 / vis.height if vis.height > 1600 else 1; vis.resize((int(vis.width * s), int(vis.height * s))).save(out)
    return {'h_control': A.height, 'h_candidate': B.height, 'diff_pct': round(pct, 4), 'bbox': bbox}
async def main():
    res = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(); sem = asyncio.Semaphore(3)
        async def job(pid, w):
            async with sem:
                ctx = await browser.new_context(viewport={'width': w, 'height': 900}); await ctx.add_init_script("Math.random=()=>0.5; document.addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style'); s.textContent='#right-sidebar{visibility:hidden}'; document.head.appendChild(s);});"); page = await ctx.new_page()
                key = f'{pid}-{w}'
                try:
                    a = f'{OUT}/shots/{key}-control.png'; b = f'{OUT}/shots/{key}-candidate.png'
                    if not os.path.exists(a): await shoot(page, f'{CTRL}/{pid}.html', a)
                    await shoot(page, f'{CAND}/{MAP[str(pid)]}', b); res[key] = compare(a, b, f'{OUT}/diffs/{key}.png')
                except Exception as e: res[key] = {'error': str(e)[:200]}
                finally: await ctx.close()
                print(key, res[key].get('diff_pct', res[key].get('error')), res[key].get('h_control'), res[key].get('h_candidate'), flush=True)
        await asyncio.gather(*[job(pid, w) for pid in ids for w in WIDTHS]); await browser.close()
    json.dump(res, open(f'{OUT}/results.json', 'w'), indent=1)
    ok = sum(1 for v in res.values() if v.get('diff_pct') == 0); print(f'identical {ok}/{len(res)}')
asyncio.run(main())
