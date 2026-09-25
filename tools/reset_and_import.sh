#!/bin/sh
# Re-import a WXR into the running local EmDash (dev server on 4321). Usage: reset_and_import.sh <wxr> [skipExisting=false]
# NOTE: DELETE ?permanent=true only trashes entries and the slug stays taken. For a clean run: stop the dev server, rm data.db*, start it, then run this.
set -e
cd "$(dirname "$0")/.."
WXR="$1"; SKIP="${2:-false}"
rm -f archive/jar.txt
curl -s -c archive/jar.txt -o /dev/null "http://127.0.0.1:4321/_emdash/api/setup/dev-bypass?redirect=/_emdash/admin"
# delete existing posts and pages first (100 per page)
for coll in posts pages; do for round in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40; do
  curl -s -b archive/jar.txt -H "X-EmDash-Request: 1" "http://127.0.0.1:4321/_emdash/api/content/$coll?limit=100&status=published" | python3 -c "import json,sys;d=json.load(sys.stdin).get('data') or {};print('\n'.join(i['id'] for i in d.get('items',[])))" > archive/ids.txt
  n=$(sed '/^$/d' archive/ids.txt | wc -l | tr -d ' '); [ "$n" = "0" ] && break
  while read id; do [ -n "$id" ] && curl -s -o /dev/null -b archive/jar.txt -H "X-EmDash-Request: 1" -X DELETE "http://127.0.0.1:4321/_emdash/api/content/$coll/$id?permanent=true"; done < archive/ids.txt
  echo "deleted $n $coll"
done; done
curl -s -b archive/jar.txt -H "X-EmDash-Request: 1" -F "file=@$WXR;type=text/xml" -F "config={\"postTypeMappings\":{\"post\":{\"collection\":\"posts\",\"enabled\":true},\"page\":{\"collection\":\"pages\",\"enabled\":true}},\"skipExisting\":$SKIP}" http://127.0.0.1:4321/_emdash/api/import/wordpress/execute | python3 -c "import json,sys;d=json.load(sys.stdin)['data'];print('imported',d.get('imported'),'skipped',d.get('skipped'),'errors',len(d.get('errors',[])), (d['errors'][0]['error'][:120] if d.get('errors') else ''))"
