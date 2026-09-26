#!/bin/sh
# Media bucket (Bunny S3) -> backup bucket, once a day at start and every 24 h; Kuma push on success.
media_sync() {
	rclone sync ":s3,provider=Other,endpoint=${S3_ENDPOINT#https://},region=$S3_REGION,access_key_id=$S3_ACCESS_KEY_ID,secret_access_key=$S3_SECRET_ACCESS_KEY:$S3_BUCKET" \
		":s3,provider=Scaleway,endpoint=$BACKUP_ENDPOINT,region=$BACKUP_REGION,access_key_id=$BACKUP_ACCESS_KEY_ID,secret_access_key=$BACKUP_SECRET_ACCESS_KEY:$BACKUP_BUCKET/$BACKUP_PREFIX/media" \
		--fast-list --transfers 8 --checkers 16 --stats-one-line --stats 0 -v 2>&1 | tail -5 \
	&& { [ -z "$MEDIA_HEARTBEAT_URL" ] || curl -fsS -o /dev/null "$MEDIA_HEARTBEAT_URL" || echo "media heartbeat push failed"; echo "media sync done $(date -u +%FT%TZ)"; }
}
( sleep 120; while :; do media_sync; sleep 86400; done ) &
exec litestream replicate
