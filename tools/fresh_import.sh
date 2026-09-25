#!/bin/sh
# Fresh local content load. Run right after: stop dev server, rm data.db*, start dev server.
# The dev-bypass sign-in only works on a database that has not been seeded yet, so everything is imported in one session.
# Usage: fresh_import.sh <wxr> [<wxr> ...]
set -e
cd "$(dirname "$0")/.."
rm -f archive/jar.txt
code=$(curl -s -c archive/jar.txt -o /dev/null -w "%{http_code}" "http://127.0.0.1:4321/_emdash/api/setup/dev-bypass?redirect=/_emdash/admin")
echo "dev-bypass: $code"
# remove the blog template's seeded sample content (the bypass seeds it on a fresh database)
python3 - <<'PY'
import json,subprocess
seed=json.load(open('seed/seed.json'))
content=seed.get('content') or {}
for coll in ('posts','pages'):
    for entry in (content.get(coll) or []):
        slug=entry.get('slug') or entry.get('id')
        if not slug: continue
        r=subprocess.run(['curl','-s','-b','archive/jar.txt','-H','X-EmDash-Request: 1',f'http://127.0.0.1:4321/_emdash/api/content/{coll}/{slug}'],capture_output=True,text=True)
        try: cid=json.loads(r.stdout)['data']['item']['id']
        except Exception: continue
        subprocess.run(['curl','-s','-o','/dev/null','-b','archive/jar.txt','-H','X-EmDash-Request: 1','-X','DELETE',f'http://127.0.0.1:4321/_emdash/api/content/{coll}/{cid}'])
        print('removed seeded',coll,slug)
PY
# the blog template's pages collection has no excerpt field; the importer writes one for every post type
# Phase 2: bylines = source of truth for authorship (creates the CAP co-author bylines, bios, websites; attaches the full author list per post)
python3 tools/sync_bylines.py | tail -2

# an API token for later CLI/API work in this session (content scopes)
curl -s -b archive/jar.txt -H "X-EmDash-Request: 1" -H "Content-Type: application/json" -d '{"name":"local-dev","scopes":["content:read","content:write","schema:read","schema:write"]}' http://127.0.0.1:4321/_emdash/api/admin/api-tokens | python3 -c "import json,sys;d=json.load(sys.stdin).get('data') or {};t=d.get('token') or d.get('plaintext') or '';open('archive/token.txt','w').write(t);print('token saved' if t else 'no token')"
TOKEN=$(cat archive/token.txt); npx emdash schema add-field pages excerpt --type text --label Excerpt -u http://127.0.0.1:4321 -t "$TOKEN" 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | head -1
for WXR in "$@"; do
  # prepare: make sure the target collections have the fields the importer writes (pages lack "excerpt" in the template)
  curl -s -b archive/jar.txt -H "X-EmDash-Request: 1" -F "file=@$WXR;type=text/xml" http://127.0.0.1:4321/_emdash/api/import/wordpress/analyze -o archive/analyze.json
  python3 -c "import json;d=json.load(open('archive/analyze.json'))['data'];m={'post':{'collection':'posts','enabled':True},'page':{'collection':'pages','enabled':True}};json.dump({'postTypes':[dict(pt,collection=m.get(pt['name'],{}).get('collection',pt.get('suggestedCollection'))) for pt in d['postTypes']],'postTypeMappings':m},open('archive/prepare.json','w'))"
  curl -s -b archive/jar.txt -H "X-EmDash-Request: 1" -H "Content-Type: application/json" -d @archive/prepare.json http://127.0.0.1:4321/_emdash/api/import/wordpress/prepare | python3 -c "import json,sys;r=json.load(sys.stdin);print('prepare:',r.get('success'),(r.get('data') or {}).get('fieldsCreated'),r.get('error',''))"
  curl -s -b archive/jar.txt -H "X-EmDash-Request: 1" -F "file=@$WXR;type=text/xml" -F 'config={"postTypeMappings":{"post":{"collection":"posts","enabled":true},"page":{"collection":"pages","enabled":true}},"skipExisting":true}' http://127.0.0.1:4321/_emdash/api/import/wordpress/execute \
   | python3 -c "import json,sys;r=json.load(sys.stdin);d=r.get('data') or {};print('$WXR: imported',d.get('imported'),'skipped',d.get('skipped'),'errors',len(d.get('errors',[])),(d['errors'][0]['error'][:100] if d.get('errors') else ''), '' if r.get('success') else r)"
done

# Henning's own admin account: the dev server prints the invite e-mail with the accept link (no mail provider locally)
curl -s -b archive/jar.txt -H "X-EmDash-Request: 1" -H "Content-Type: application/json" -d '{"email":"h.meyer@socialeurope.eu","name":"Henning Meyer","role":50}' http://127.0.0.1:4321/_emdash/api/auth/invite >/dev/null
echo "invite for h.meyer@socialeurope.eu requested: open the accept link from the dev-server log (search 'invite/accept'), then register a passkey"
