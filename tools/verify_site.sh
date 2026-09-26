#!/bin/sh
# Acceptance run against a deployed site: crawl (every URL 200), pixel diff of the 100 sample articles at three widths
# against the live snapshots (snapshot server on :8766), content audit. Usage: SE_BASE=https://<host> SE_TOKEN=<token> sh tools/verify_site.sh
set -e
cd "$(dirname "$0")/.."
BASE="${SE_BASE:?SE_BASE}"; PW="${PW:-/private/tmp/claude-501/-Users-henningmeyer-Desktop-Claude-Code/315d577f-3586-4a77-9566-8a8a1ec17b65/scratchpad/pwenv/bin/python}"
OUT="archive/verify-$(date +%Y%m%d-%H%M)"; mkdir -p "$OUT"
echo "== crawl"; python3 tools/crawl_check.py "$BASE" | tail -2 | tee "$OUT/crawl.txt"
echo "== audit"; python3 tools/dump_site.py > /dev/null && python3 tools/audit_content.py > "$OUT/audit.txt"; grep -E "^== posts|htmlBlock|image blocks|featured_image|== media|== bylines" "$OUT/audit.txt" | cut -c1-200
echo "== pixel diff (100 articles x 1440/768/375, related/most-read masked)"
IDS=$(python3 -c "import json;print(' '.join(str(i) for i in json.load(open('archive/sample-ids.json'))))")
EXTRA_MASK=".se-rel-inline,.se-rel-band,.se-most{display:none}" "$PW" tools/diff.py "$OUT/diff" http://127.0.0.1:8766/control "$BASE" 1440,768,375 archive/all-map.json $IDS > "$OUT/diff.log" 2>&1 || true
python3 - "$OUT/diff.log" <<'PY'
import re,sys
rows=[l.split() for l in open(sys.argv[1]) if re.match(r'^\d+-\d+ ',l)]
for w in ('1440','768','375'):
    v=[(float(r[1]),r[0],int(r[2]),int(r[3])) for r in rows if r[0].endswith('-'+w)]
    if not v: print(w,'no rows'); continue
    print(w,'n',len(v),'max %.2f%%'%max(x[0] for x in v),'>0.5%:',[(x[1],round(x[0],2)) for x in v if x[0]>0.5],'height diff >3px:',[(x[1],x[2],x[3]) for x in v if abs(x[2]-x[3])>3])
PY
echo "== results in $OUT"
