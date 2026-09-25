#!/usr/bin/env python3
"""Site-level EmDash data the theme reads at runtime (vanilla EmDash: settings, menus, page fields, SEO panel).
Runs after the content + media import (fresh_import.sh); idempotent."""
import json, re, os, sys, subprocess
from html import unescape
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emdash_api import api, list_all, ROOT, BASE, TOKEN
SITE = "https://www.socialeurope.eu"
# 1. site settings (POST = update)
fav = None
mi = f"{ROOT}/archive/media-import.json"
if os.path.exists(mi):
    for it in json.load(open(mi))["imported"]:
        if it["originalUrl"].endswith("/2025/10/cropped-SE-scaled-1.png"): fav = it["mediaId"]
body = {"title": "Social Europe", "tagline": "Politics, Economy and Employment & Labour", "url": SITE}
if fav: body["favicon"] = {"mediaId": fav, "alt": "Social Europe"}
r = api("POST", "/_emdash/api/settings", body)
print("settings:", {k: v for k, v in (r.get("data") or {}).items() if k != "seo"})

# 2. menus
MENUS = {
    "primary": ("Primary Navigation", [("eBooks", "https://ebooks.socialeurope.eu", None), ("Newsletter", "https://newsletter.socialeurope.eu/", "_blank"), ("Membership", "https://steadyhq.com/en/socialeurope/about", "_blank"), ("Advertisements", f"{SITE}/advertise-on-social-europe", None)]),
    "footer-1": ("Footer column 1", [("Our Mission", f"{SITE}/mission-statement", "_blank"), ("People", f"{SITE}/team", None), ("Article Submission", f"{SITE}/article-submission", "_blank"), ("Advertisements", f"{SITE}/advertise-on-social-europe", None), ("Membership", "https://steadyhq.com/en/socialeurope/about", None)]),
    "footer-2": ("Footer column 2", [("Politics Archive", f"{SITE}/category/politics", None), ("Economy Archive", f"{SITE}/category/economy", None), ("Society Archive", f"{SITE}/category/society", None), ("Transparency Notice", f"{SITE}/transparency-notice", None), ("Photo Credits", f"{SITE}/photo-credits", None)]),
    "footer-3": ("Footer column 3", [("RSS Feed", f"{SITE}/feed", None), ("Legal Disclosure", f"{SITE}/legal-disclosure", "_blank"), ("Privacy Policy", f"{SITE}/privacy-policy", "_blank"), ("Copyright", f"{SITE}/copyright-2", "_blank")]),
}
menus = api("GET", "/_emdash/api/menus").get("data") or []
existing = {m["name"]: m for m in (menus.get("items") if isinstance(menus, dict) else menus)}
for name, (label, items) in MENUS.items():
    if name not in existing: api("POST", "/_emdash/api/menus", {"name": name, "label": label})
    current = (api("GET", f"/_emdash/api/menus/{name}").get("data") or {}).get("items") or []
    want = [(lab, url) for lab, url, _ in items]
    if [(it["label"], it.get("customUrl")) for it in current] == want: print("menu ok:", name); continue
    for it in current: api("DELETE", f"/_emdash/api/menus/{name}/items/{it['id']}")
    for i, (lab, url, target) in enumerate(items):
        body = {"type": "custom", "label": lab, "customUrl": url, "sortOrder": i}
        if target: body["target"] = target
        api("POST", f"/_emdash/api/menus/{name}/items", body)
    print("menu set:", name, len(items))

# 3. pages: SEO panel + template fields + values from the live capture (archive/fixtures/page-*.json)
api("PUT", "/_emdash/api/schema/collections/pages", {"hasSeo": True}); print("pages: SEO enabled")
tok = TOKEN or open(f"{ROOT}/archive/token.txt").read().strip()
for field, typ, label in (("template", "string", "Template"), ("intro_title", "string", "Intro title"), ("sidebar", "boolean", "Sidebar"), ("show_cta", "boolean", "Show write-for-us CTA")):
    r = subprocess.run(["npx", "emdash", "schema", "add-field", "pages", field, "--type", typ, "--label", label, "-u", BASE, "-t", tok], capture_output=True, text=True, cwd=ROOT)
    print("field", field, ":", re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout + r.stderr).strip().splitlines()[0] if (r.stdout + r.stderr).strip() else "?"))
import glob
def entry_id(coll, slug):
    r = api("GET", f"/_emdash/api/content/{coll}/{slug}", ok404=True)
    return ((r or {}).get("data") or {}).get("item", {}).get("id") if r else None
pages_done = 0
for f in glob.glob(f"{ROOT}/archive/fixtures/page-*.json"):
    fx = json.load(open(f)); eid = entry_id("pages", fx["slug"])
    if not eid: print("no page entry for", fx["slug"]); continue
    intro = fx.get("introHtml") or ""
    m = re.search(r"<h1>(.*?)</h1>", intro); it = unescape(m.group(1)) if m else None
    m = re.search(r'<p class="se-dek">(.*?)</p>', intro, re.S); dek = unescape(re.sub("<[^>]+>", "", m.group(1))).strip() if m else None
    data = {"template": fx.get("template") or "default", "sidebar": bool(fx.get("hasSidebar")), "show_cta": bool(fx.get("ctaHtml"))}
    if it and it != fx["title"]: data["intro_title"] = it
    if dek: data["excerpt"] = dek
    seo = {"title": (fx.get("headTitle") or "").replace(" - Social Europe", "") or None, "description": fx.get("description") or None}
    api("PUT", f"/_emdash/api/content/pages/{eid}", {"data": data, "seo": seo, "skipRevision": True})
    api("POST", f"/_emdash/api/content/pages/{eid}/publish", {}); pages_done += 1
print("pages updated:", pages_done)

# 4. posts: SEO panel = the live head's title/description where WordPress/TSF had custom values (else EmDash derives them)
posts = {p["id"]: p["slug"] for p in json.load(open(f"{ROOT}/archive/posts.json"))}
posts_api = list_all("/_emdash/api/content/posts")
ids = {p["slug"]: p["id"] for p in posts_api}
titles = {p["id"]: (p.get("data") or {}).get("title") for p in posts_api}
n = 0
for f in glob.glob(f"{ROOT}/archive/fixtures/[0-9]*.json"):
    fx = json.load(open(f)); slug = posts.get(fx["id"]); eid = ids.get(slug)
    if not eid: continue
    t = (fx.get("title") or "").replace(" - Social Europe", "").strip(); t = unescape(t)
    title = t if t and t != titles.get(eid) else None
    desc = fx.get("description") or None
    if not title and not desc: continue
    api("PUT", f"/_emdash/api/content/posts/{eid}", {"seo": {"title": title, "description": desc}, "skipRevision": True}); n += 1
print("posts with SEO panel values:", n)

# 5. taxonomy term descriptions (category archive intro text) from the WordPress terms
terms = json.load(open(f"{ROOT}/archive/terms.json"))
n = 0
for tax, key in (("category", "categories"), ("tag", "tags")):
    for t in terms.get(key, []):
        if not t.get("description"): continue
        r = api("PUT", f"/_emdash/api/taxonomies/{tax}/terms/{t['slug']}", {"description": unescape(re.sub("<[^>]+>", "", t["description"]))}, ok404=True)
        if r: n += 1
print("term descriptions set:", n)
