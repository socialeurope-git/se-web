#!/usr/bin/env python3
"""Sign in to an EmDash deployment with the stored virtual passkey (tools/staging_setup.py) and create an admin API token.
Usage: staging_login.py https://<host> [token-name]"""
import asyncio, json, os, re, sys
from playwright.async_api import async_playwright
BASE = sys.argv[1].rstrip("/"); NAME = sys.argv[2] if len(sys.argv) > 2 else "import"
key = BASE.split("//")[1].replace("/", "_"); OUT = os.path.expanduser(f"~/.config/se-web/{key}-token"); CRED = os.path.expanduser(f"~/.config/se-web/{key}-passkey.json")
async def main():
    cred = json.load(open(CRED))
    async with async_playwright() as pw:
        b = await pw.chromium.launch(); ctx = await b.new_context(viewport={"width": 1280, "height": 1800}); p = await ctx.new_page()
        cdp = await ctx.new_cdp_session(p); await cdp.send("WebAuthn.enable")
        auth = (await cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {"protocol": "ctap2", "transport": "internal", "hasResidentKey": True, "hasUserVerification": True, "isUserVerified": True, "automaticPresenceSimulation": True}}))["authenticatorId"]
        for c in cred["credentials"]: await cdp.send("WebAuthn.addCredential", {"authenticatorId": auth, "credential": c})
        await p.goto(f"{BASE}/_emdash/admin/login", wait_until="networkidle"); await p.wait_for_timeout(1500); await p.screenshot(path="/tmp/login-1.png")
        em = p.locator('input[type="email"]')
        if await em.count(): await em.first.fill("ops@socialeurope.eu")
        for _ in range(3):
            btn = p.locator('button[type="submit"], button:has-text("Passkey"), button:has-text("passkey"), button:has-text("Anmelden")')
            if await btn.count(): await btn.first.click(force=True)
            await p.wait_for_timeout(4000)
            me = json.loads(await (await ctx.request.get(f"{BASE}/_emdash/api/auth/me")).text())
            if (me.get("data") or {}).get("user") or me.get("data", {}).get("email"): break
        await p.screenshot(path="/tmp/login-2.png"); print("me:", json.dumps(me)[:200])
        d = await p.evaluate("""async (name) => { const r = await fetch('/_emdash/api/admin/api-tokens', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-EmDash-Request': '1' }, body: JSON.stringify({ name, scopes: ['admin'] }) }); return await r.json(); }""", NAME)
        tok = (d.get("data") or {}).get("token") or (d.get("data") or {}).get("plaintext")
        if not tok: print("token creation failed:", json.dumps(d)[:300]); await b.close(); return
        open(OUT, "w").write(tok); os.chmod(OUT, 0o600); print("token stored:", OUT, "prefix", tok[:10])
        await b.close()
asyncio.run(main())
