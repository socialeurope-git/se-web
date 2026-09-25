#!/usr/bin/env python3
"""Complete the EmDash setup wizard on a fresh deployment without a human passkey: Playwright + a CDP virtual
WebAuthn authenticator registers the passkey of an operations admin (ops@socialeurope.eu), then creates an API token
with the admin scope. Henning gets his own account through an invite afterwards.
Usage: staging_setup.py https://<host>   -> prints the token and stores it in ~/.config/se-web/<host>-token"""
import asyncio, json, os, re, sys, time
from playwright.async_api import async_playwright
BASE = sys.argv[1].rstrip("/"); EMAIL = "ops@socialeurope.eu"; NAME = "SE Ops"
OUT = os.path.expanduser(f"~/.config/se-web/{BASE.split('//')[1].replace('/', '_')}-token"); CRED = OUT.replace("-token", "-passkey.json")
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(); ctx = await b.new_context(viewport={"width": 1280, "height": 1800}); p = await ctx.new_page()
        cdp = await ctx.new_cdp_session(p)
        await cdp.send("WebAuthn.enable"); auth_id = (await cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {"protocol": "ctap2", "transport": "internal", "hasResidentKey": True, "hasUserVerification": True, "isUserVerified": True, "automaticPresenceSimulation": True}}))["authenticatorId"]
        await p.goto(f"{BASE}/_emdash/admin/setup", wait_until="networkidle"); await p.wait_for_timeout(1500)
        async def shot(n): await p.screenshot(path=f"/tmp/setup-{n}.png")
        async def status():
            return json.loads(await (await ctx.request.get(f"{BASE}/_emdash/api/setup/status")).text())["data"]
        submit = lambda: p.locator('button[type="submit"]').first
        # step 1: title, tagline, sample content off (the wizard is localised, so form controls instead of labels)
        tb = p.locator('input[type="text"]'); await tb.nth(0).fill("Social Europe"); await tb.nth(1).fill("Politics, Economy and Employment & Labour")
        cb = p.locator('input[type="checkbox"]')
        if await cb.count() and await cb.first.is_checked(): await cb.first.evaluate("el => el.click()")   # visually hidden custom checkbox
        print("sample content checked:", await cb.first.is_checked() if await cb.count() else None)
        await shot(1); await submit().click(force=True); await p.wait_for_timeout(3000); await shot(2); print("after step 1:", await status())
        # step 2: e-mail + name of the operations admin
        await p.locator('input[type="email"]').first.fill(EMAIL)
        others = p.locator('input[type="text"]')
        if await others.count(): await others.first.fill(NAME)
        await submit().click(force=True); await p.wait_for_timeout(5000); await shot(3); print("after step 2:", await status())
        # step 3: passkey registration, answered by the virtual authenticator (a button may start the ceremony)
        for _ in range(4):
            st = await status()
            if not st.get("needsSetup"): break
            b3 = p.locator('button[type="submit"], button:has-text("Passkey"), button:has-text("passkey"), button:has-text("Registrieren")')
            if await b3.count(): await b3.first.click(force=True)
            await p.wait_for_timeout(5000)
        await shot(4)
        st = json.loads(await (await ctx.request.get(f"{BASE}/_emdash/api/setup/status")).text()); print("setup status:", st["data"])
        if st["data"].get("needsSetup"): print("setup not completed; see /tmp/setup-*.png"); await b.close(); return
        opn = p.get_by_role("button", name=re.compile("dashboard|Open", re.I))
        if await opn.count(): await opn.first.click(); await p.wait_for_timeout(2000)
        # keep the virtual passkey for later logins (credential export via CDP) and create the API token from the page
        creds = await cdp.send("WebAuthn.getCredentials", {"authenticatorId": auth_id})
        open(CRED, "w").write(json.dumps({"rpId": BASE.split("//")[1], "credentials": creds.get("credentials", [])})); os.chmod(CRED, 0o600)
        d = await p.evaluate("""async () => { const r = await fetch('/_emdash/api/admin/api-tokens', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-EmDash-Request': '1' }, body: JSON.stringify({ name: 'import', scopes: ['admin'] }) }); return await r.json(); }""")
        tok = (d.get("data") or {}).get("token") or (d.get("data") or {}).get("plaintext")
        if not tok: print("token creation failed:", json.dumps(d)[:300]); await b.close(); return
        open(OUT, "w").write(tok); os.chmod(OUT, 0o600); print("token stored:", OUT, "prefix", tok[:10], "| passkey credential stored:", CRED)
        await b.close()
asyncio.run(main())
