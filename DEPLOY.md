# Deploying Social Europe (EmDash) to Bunny Magic Containers

## Image
`Dockerfile` follows the official Node.js deployment guide (node:22-alpine, `node ./dist/server/entry.mjs`, port 4321,
data directory `/app/data`); `.github/workflows/image.yml` pushes `ghcr.io/socialeurope-git/se-web:staging` and `:production` on every push to
`main` and triggers the Bunny deploy. Health: `/health` (process alive) and `/_emdash/api/health`.

## Runtime environment (Magic Containers app → container env)
| Variable | Value |
|---|---|
| `DATABASE_PATH` | `/app/data/data.db` — `/app/data` is the persistent volume (SQLite). Baked into the image at build time (astro.config runs during `astro build`), the runtime value must match |
| `EMDASH_ENCRYPTION_KEY` | from `npx emdash secrets generate`; keep with the backups (plugin secrets are unreadable without it) |
| `EMDASH_SITE_URL` | public origin, e.g. `https://mc-hdck3f7ufk.bunny.run` (staging) or `https://www.socialeurope.eu`; required behind the CDN for passkeys, CSRF, sitemap. Also a **build argument** (workflow matrix): EmDash only registers the origin for Astro's image service when it is known at build time, so each host gets its own image tag |
| `EMDASH_ALLOWED_ORIGINS` | optional extra hostnames accepted for passkeys (comma-separated) |
| `S3_ENDPOINT` | `https://de-s3.storage.bunnycdn.com` |
| `S3_BUCKET` / `S3_ACCESS_KEY_ID` | `se-media` (storage zone name = access key id). `S3_BUCKET` is also set at build time: it selects the S3 adapter in astro.config |
| `S3_SECRET_ACCESS_KEY` | the storage zone password |
| `S3_REGION` | `de` |
| `S3_PUBLIC_URL` | `https://www.socialeurope.eu` (media served through the pull zone); unset on staging so the app serves media itself |
| `SE_LINK_ORIGIN` | staging only: the staging hostname, so body links stay on staging; unset in production |
| `SE_SEARCH_URL` | `http://127.0.0.1:8080` when the se-search sidecar runs in the same pod (related + Most Read), else unset |

## Pull zone
- Origin = the Magic Containers app (port 3000), host header forwarded.
- Edge rules: `/media/*` and `/_emdash/api/media/file/*` → Origin Storage `se-media` (or let the app serve them and cache at the edge); keep the Plausible edge script 91963; HTML cache as today.
- Old `/wp-content/uploads/*` URLs are not handled by the app. At the cutover, copy the WordPress uploads tree into a storage zone and add an edge rule on the production pull zone that serves `/wp-content/uploads/*` from it (original files and every size variant keep working byte-identically). Staging does not need this.

## Data
- First deployment: complete the setup wizard on the new host (admin with passkey, no sample content), create an API token with the admin scope, then run `SE_BASE=https://<host> SE_TOKEN=<token> sh tools/fresh_import.sh archive/wxr-all.xml` — content, media (straight into the S3 zone), bylines, menus, widgets, SEO.
- Backups: nightly copy of `/app/data/emdash.db` + the storage zone (EmDash's automatic JSON backups can also target the S3 zone).

## Plugin SE Ops
After the first start: Admin → Plugins → SE Ops → settings: Bunny API key, pull zone id `5962195`, Uptime Kuma push URL.

## Pull zone (staging 6691312, later production 5962195)

- `IgnoreQueryStrings` must be **off**: Astro's image endpoint keys every size on the query string (`/_image?href=…&w=…&h=…&f=…`).
- Edge rule "Override Cache Time" 30 days, URL triggers `*/_image*` and `*/_emdash/api/media/file/*` (Bunny's URL trigger does not see the query string, so `*/_image?*` never matches): EmDash sends `max-age=0, must-revalidate` for media and transforms, the CDN would otherwise fetch every image from the pod. Storage keys are immutable ULIDs, so long caching is safe. Verified on staging: `cdn-cache: HIT` for transforms and originals.

## Backups (EmDash docs: "Backups and recovery")

**Single writer rule.** The Magic Containers volume is a 9p mount (gVisor sandbox, `cache=remote_revalidating`). SQLite in
WAL mode must be opened by **one process only**: a Litestream sidecar sharing the file corrupted the staging database
within seconds of the first mass write (2026-09-26, "database disk image is malformed"). Nothing but the EmDash process
opens `data.db`.

EmDash's own daily backup is a JSON export into the bucket and **cannot be restored**. The restorable copy is a consistent
SQLite snapshot plus the media bucket plus `EMDASH_ENCRYPTION_KEY` (kept in `~/.config/se-web/`).

- **Snapshot from inside the app** (single connection): `POST /ops/snapshot` with `Authorization: Bearer $SE_OPS_TOKEN`
  (env on the app container; `~/.config/se-web/ops-token`) runs `VACUUM INTO /app/data/backup/data-<timestamp>.db` on
  EmDash's own database handle and keeps only the newest two snapshots (each is a full ~0.4 GB copy; hourly snapshots
  filled the 5 GB volume to 85 % on 2026-09-26 — the uploader now asks once a day). Volume sizing: database + WAL +
  two snapshots ≈ 1.5 GB, 5 GB is fine; Bunny mails at 75 %. The sidecar calls it on `localhost:4321` inside the pod;
  through the CDN the request needs a JSON body (Bunny answers 405 to a bodiless POST).
- **Sidecar `backup`** (`backup/Dockerfile`, image `ghcr.io/socialeurope-git/se-web-backup`, same volume, read-only role):
  rclone copies `/app/data/backup/` and the media bucket to Scaleway `social-europe-backup-amsterdam/<prefix>/` once a day and pings
  the Uptime Kuma push monitors (`BACKUP_HEARTBEAT_URL` for the database copy, `MEDIA_HEARTBEAT_URL` for the media copy).
  It never opens `data.db`. Its environment must not repeat a variable name (Bunny then fails with "Failed to create container config").
- **Restore**: put the newest snapshot on a fresh volume as `/app/data/data.db`, media back into the bucket with
  `rclone sync`, start the matching app version. Env: `~/.config/se-web/backup.env`; `tools/bunny_backup_container.py` adds the sidecar.
- Prefixes: staging `se-web-staging`, production `se-web`.
