#!/bin/sh
# Fresh content load into an empty EmDash site.
#   local:   stop dev server, rm data.db*, start dev server, then  sh tools/fresh_import.sh archive/wxr-all.xml
#            (the dev-bypass sign-in only works on a database that has not been seeded yet, so everything is imported in one session)
#   staging: SE_BASE=https://<host> SE_TOKEN=<admin api token> sh tools/fresh_import.sh archive/wxr-all.xml
#            (site set up through the wizard without sample content; the token needs the admin scope)
set -e
cd "$(dirname "$0")/.."
BASE="${SE_BASE:-http://127.0.0.1:4321}"
if [ -n "$SE_TOKEN" ]; then AUTH="Authorization: Bearer $SE_TOKEN"; [ -f archive/jar.txt ] || : > archive/jar.txt; else
  rm -f archive/jar.txt
  code=$(curl -s -c archive/jar.txt -o /dev/null -w "%{http_code}" "$BASE/_emdash/api/setup/dev-bypass?redirect=/_emdash/admin")
  echo "dev-bypass: $code"; AUTH="X-Dev: 1"
fi
export SE_BASE="$BASE"
# remove the blog template's seeded sample content (the bypass seeds it on a fresh database)
export SE_AUTH="$AUTH"
if [ "${SE_START_AT:-}" != "media" ]; then
python3 - <<'PY'
import json,subprocess,os
seed=json.load(open('seed/seed.json'))
content=seed.get('content') or {}
for coll in ('posts','pages'):
    for entry in (content.get(coll) or []):
        slug=entry.get('slug') or entry.get('id')
        if not slug: continue
        r=subprocess.run(['curl','-s','-b','archive/jar.txt','-H',os.environ.get('SE_AUTH','X-Dev: 1'),'-H','X-EmDash-Request: 1',os.environ['SE_BASE']+f'/_emdash/api/content/{coll}/{slug}'],capture_output=True,text=True)
        try: cid=json.loads(r.stdout)['data']['item']['id']
        except Exception: continue
        subprocess.run(['curl','-s','-o','/dev/null','-b','archive/jar.txt','-H',os.environ.get('SE_AUTH','X-Dev: 1'),'-H','X-EmDash-Request: 1','-X','DELETE',os.environ['SE_BASE']+f'/_emdash/api/content/{coll}/{cid}'])
        print('removed seeded',coll,slug)
PY
# the blog template's pages collection has no excerpt field; the importer writes one for every post type
# an API token for later CLI/API work in this session (content scopes) — local only; on staging SE_TOKEN is used
[ -z "$SE_TOKEN" ] && curl -s -b archive/jar.txt -H "$AUTH" -H "X-EmDash-Request: 1" -H "Content-Type: application/json" -d '{"name":"local-dev","scopes":["content:read","content:write","schema:read","schema:write"]}' $BASE/_emdash/api/admin/api-tokens | python3 -c "import json,sys;d=json.load(sys.stdin).get('data') or {};t=d.get('token') or d.get('plaintext') or '';open('archive/token.txt','w').write(t);print('token saved' if t else 'no token')"
TOKEN="${SE_TOKEN:-$(cat archive/token.txt)}"; npx emdash schema add-field pages excerpt --type text --label Excerpt -u "$BASE" -t "$TOKEN" 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | head -1
# WordPress quirks fixed before the import (figures nested in headings)
for W in "$@"; do python3 tools/prepare_wxr.py "$W" "${W%.xml}-clean.xml"; done
set -- $(for W in "$@"; do printf "%s " "${W%.xml}-clean.xml"; done)
for WXR in "$@"; do
  # prepare: make sure the target collections have the fields the importer writes (pages lack "excerpt" in the template)
  curl -s -b archive/jar.txt -H "$AUTH" -H "X-EmDash-Request: 1" -F "file=@$WXR;type=text/xml" $BASE/_emdash/api/import/wordpress/analyze -o archive/analyze.json
  python3 -c "import json;d=json.load(open('archive/analyze.json'))['data'];m={'post':{'collection':'posts','enabled':True},'page':{'collection':'pages','enabled':True}};json.dump({'postTypes':[dict(pt,collection=m.get(pt['name'],{}).get('collection',pt.get('suggestedCollection'))) for pt in d['postTypes']],'postTypeMappings':m},open('archive/prepare.json','w'))"
  curl -s -b archive/jar.txt -H "$AUTH" -H "X-EmDash-Request: 1" -H "Content-Type: application/json" -d @archive/prepare.json $BASE/_emdash/api/import/wordpress/prepare | python3 -c "import json,sys;r=json.load(sys.stdin);print('prepare:',r.get('success'),(r.get('data') or {}).get('fieldsCreated'),r.get('error',''))"
  curl -s -b archive/jar.txt -H "$AUTH" -H "X-EmDash-Request: 1" -F "file=@$WXR;type=text/xml" -F 'config={"postTypeMappings":{"post":{"collection":"posts","enabled":true},"page":{"collection":"pages","enabled":true}},"skipExisting":true}' $BASE/_emdash/api/import/wordpress/execute \
   | python3 -c "
import json,sys
raw=sys.stdin.read()
try: r=json.loads(raw)
except Exception: print('$WXR: execute response was not JSON (CDN timeout? the server keeps importing) ->', raw[:80].replace(chr(10),' ')); sys.exit(0)
d=r.get('data') or {};print('$WXR: imported',d.get('imported'),'skipped',d.get('skipped'),'errors',len(d.get('errors',[])),(d['errors'][0]['error'][:100] if d.get('errors') else ''), '' if r.get('success') else r)"
done
# wait until the server-side import is idle (post count stops growing), then report the counts
python3 - <<'PY2'
import json,subprocess,os,time
def total(c):
    r=subprocess.run(['curl','-s','-b','archive/jar.txt','-H',os.environ['SE_AUTH'],'-H','X-EmDash-Request: 1',os.environ['SE_BASE']+f'/_emdash/api/content/{c}?limit=1'],capture_output=True,text=True)
    try: return json.loads(r.stdout)['data']['total']
    except Exception: return None
last=None
while True:
    t=(total('posts'),total('pages'))
    if t==last and None not in t: break
    last=t; time.sleep(20)
print('content on site: posts',t[0],'pages',t[1])
PY2
fi

# Media: EmDash's importer downloads every attachment of the last analysed WXR into its storage (Media Library),
# then rewrites image blocks / image fields / string fields to the new URLs. Raw HTML blocks + the redirect map: tools/rewrite_html_blocks.py.
[ -f archive/analyze.json ] || curl -s -b archive/jar.txt -H "$AUTH" -H "X-EmDash-Request: 1" -F "file=@$1;type=text/xml" $BASE/_emdash/api/import/wordpress/analyze -o archive/analyze.json
python3 -c "import json;a=json.load(open('archive/analyze.json'))['data']['attachments']['items'];json.dump({'attachments':a,'stream':True},open('archive/media-req.json','w'));print('attachments to import:',len(a))"
# streaming NDJSON (EmDash's default): progress lines keep the connection alive through the CDN, the last line is the result
curl -s -N -b archive/jar.txt -H "$AUTH" -H "X-EmDash-Request: 1" -H "Content-Type: application/json" -d @archive/media-req.json --max-time 7200 $BASE/_emdash/api/import/wordpress/media -o archive/media-import-raw.ndjson
python3 -c "
import json
lines=[l for l in open('archive/media-import-raw.ndjson') if l.strip()]
res=[json.loads(l) for l in lines if l.startswith('{') and '\"type\":\"result\"' in l]
if not res: print('media: no result line;', len(lines), 'lines, last:', (lines[-1][:200] if lines else '')); raise SystemExit(1)
d=res[-1]; d.pop('type',None); json.dump(d,open('archive/media-import.json','w'))
print('media: imported',len(d.get('imported',[])),'failed',len(d.get('failed',[])),(d['failed'][:2] if d.get('failed') else ''))"
# raw HTML blocks first (keeps WordPress's exact size variants via the image endpoint), incl. content images WordPress never registered
python3 tools/rewrite_html_blocks.py
python3 tools/import_orphan_media.py
python3 tools/rewrite_html_blocks.py | tail -1
# then EmDash's own rewrite for image blocks, image fields (featured_image) and string fields
python3 -c "import json;d=json.load(open('archive/media-import.json'));json.dump({'urlMap':d['urlMap'],'collections':['posts','pages']},open('archive/rewrite-req.json','w'))"
curl -s -b archive/jar.txt -H "$AUTH" -H "X-EmDash-Request: 1" -H "Content-Type: application/json" -d @archive/rewrite-req.json --max-time 1800 $BASE/_emdash/api/import/wordpress/rewrite-urls | python3 -c "
import json,sys
raw=sys.stdin.read()
try: r=json.loads(raw)
except Exception: print('rewrite-urls: response was not JSON (CDN timeout? the server keeps rewriting) ->', raw[:80].replace(chr(10),' ')); sys.exit(0)
print('rewrite-urls:',r.get('success'),{k:v for k,v in (r.get('data') or {}).items() if not isinstance(v,list)})"

# Bylines = source of truth for authorship: CAP co-author bylines, bios, websites, portrait media; full author list per post
python3 tools/sync_bylines.py | tail -2

# Clean start: WordPress residue in the Portable Text -> native blocks / tidy HTML, junk dropped, alt texts, no self-links
python3 tools/wxr_alts.py "$1"
node tools/clean_content.mjs | tail -20
# Site data the theme reads from EmDash: settings, menus, page template fields, SEO panel values
python3 tools/setup_site.py | grep -v '^field'
# Sidebar advertisements as EmDash widget area (content widgets in Portable Text)
node tools/ads_to_widgets.mjs | tail -1
# Media library: alt texts, decoded filenames, unused items (WordPress attachments nothing references) removed
python3 tools/media_meta.py --delete-unused | tail -3

# Henning's own admin account: the dev server prints the invite e-mail with the accept link (no mail provider locally)
[ -n "$SE_TOKEN" ] || curl -s -b archive/jar.txt -H "$AUTH" -H "X-EmDash-Request: 1" -H "Content-Type: application/json" -d '{"email":"h.meyer@socialeurope.eu","name":"Henning Meyer","role":50}' $BASE/_emdash/api/auth/invite >/dev/null
[ -n "$SE_TOKEN" ] || echo "invite for h.meyer@socialeurope.eu requested: open the accept link from the dev-server log (search 'invite/accept'), then register a passkey"
