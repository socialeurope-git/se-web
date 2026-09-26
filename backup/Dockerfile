# Backup sidecar for the EmDash container (same Bunny Magic Containers app, same /app/data volume):
#   - Litestream replicates the SQLite database continuously to the backup bucket (Scaleway, EU) and pings the
#     Uptime Kuma push monitor only while replication is healthy (heartbeat-url)
#   - rclone copies the media bucket (Bunny S3) to the backup bucket once a day
FROM litestream/litestream:0.5 AS litestream
FROM alpine:3.21
RUN apk add --no-cache rclone curl ca-certificates tzdata
COPY --from=litestream /usr/local/bin/litestream /usr/local/bin/litestream
COPY litestream.yml /etc/litestream.yml
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
