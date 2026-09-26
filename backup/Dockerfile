# Backup uploader for the EmDash app (same Bunny Magic Containers pod and /app/data volume, read-only role):
# copies the SQLite snapshots written by the app (VACUUM INTO, SE-Ops plugin) and the media bucket to Scaleway once a
# day and pings Uptime Kuma. It never opens data.db: the volume is a 9p mount and SQLite must have a single writer.
FROM alpine:3.21
RUN apk add --no-cache rclone curl ca-certificates tzdata
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
