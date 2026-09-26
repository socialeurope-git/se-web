#!/bin/sh
# Backup uploader (read-only role, never opens data.db): once a day copies the SQLite snapshots the app writes to
# /app/data/backup/ (VACUUM INTO by the SE-Ops plugin) and the media bucket (Bunny S3) to the backup bucket, then pings
# the Uptime Kuma push monitors. Env: S3_* (media bucket), BACKUP_* (target), BACKUP_HEARTBEAT_URL, MEDIA_HEARTBEAT_URL.
DST=":s3,provider=Scaleway,endpoint=$BACKUP_ENDPOINT,region=$BACKUP_REGION,access_key_id=$BACKUP_ACCESS_KEY_ID,secret_access_key=$BACKUP_SECRET_ACCESS_KEY:$BACKUP_BUCKET/$BACKUP_PREFIX"
SRC_MEDIA=":s3,provider=Other,endpoint=${S3_ENDPOINT#https://},region=$S3_REGION,access_key_id=$S3_ACCESS_KEY_ID,secret_access_key=$S3_SECRET_ACCESS_KEY:$S3_BUCKET"
ping() { [ -z "$1" ] || curl -fsS -o /dev/null "$1" || echo "heartbeat push failed: $1"; }
db_copy() {
	# ask the app for a fresh consistent snapshot (VACUUM INTO on its own connection; containers share localhost)
	curl -fsS -X POST -H "Authorization: Bearer $SE_OPS_TOKEN" "http://localhost:${PORT:-4321}/ops/snapshot" || echo "snapshot request failed"
	echo
	n=$(ls /app/data/backup/*.db 2>/dev/null | wc -l)
	if [ "$n" -eq 0 ]; then echo "db copy: no snapshot in /app/data/backup yet"; return 1; fi
	rclone copy /app/data/backup "$DST/db" --include "*.db" --stats-one-line --stats 0 -v 2>&1 | tail -3 \
	&& rclone delete "$DST/db" --min-age 30d --include "*.db" 2>/dev/null; echo "db copy done $(date -u +%FT%TZ) ($n snapshots)"; ping "$BACKUP_HEARTBEAT_URL"
}
media_sync() {
	rclone sync "$SRC_MEDIA" "$DST/media" --fast-list --transfers 8 --checkers 16 --stats-one-line --stats 0 -v 2>&1 | tail -3 \
	&& { echo "media sync done $(date -u +%FT%TZ)"; ping "$MEDIA_HEARTBEAT_URL"; }
}
sleep 120
while :; do db_copy; media_sync; sleep 3600; done
