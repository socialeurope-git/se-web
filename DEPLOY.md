# Deploying Social Europe (EmDash) to Bunny Magic Containers

## Image
`Dockerfile` builds the Node standalone server (`node dist/server/entry.mjs`, port 3000, health `/_emdash/api/health`).
`.github/workflows/image.yml` pushes `ghcr.io/<owner>/se-web:latest` on every push to `main` (amd64 + arm64).

## Runtime environment (Magic Containers app → container env)
| Variable | Value |
|---|---|
| `EMDASH_DB_URL` | `file:/data/data.db` — `/data` is the persistent volume (SQLite) |
| `EMDASH_ENCRYPTION_KEY` | from `npx emdash secrets generate`; keep with the backups (plugin secrets are unreadable without it) |
| `SE_STORAGE` | `s3` |
| `S3_ENDPOINT` | `https://de-s3.storage.bunnycdn.com` |
| `S3_BUCKET` / `S3_ACCESS_KEY_ID` | `se-media` (storage zone name = access key id) |
| `S3_SECRET_ACCESS_KEY` | the storage zone password |
| `S3_REGION` | `de` |
| `S3_PUBLIC_URL` | `https://www.socialeurope.eu` (media is served through the pull zone) |
| `SE_LINK_ORIGIN` | staging only: the staging hostname, so body links stay on staging; unset in production |
| `SE_SEARCH_URL` | `http://127.0.0.1:8080` when the se-search sidecar runs in the same pod (related + Most Read), else unset |

## Pull zone
- Origin = the Magic Containers app (port 3000), host header forwarded.
- Edge rules: `/media/*` and `/_emdash/api/media/file/*` → Origin Storage `se-media` (or let the app serve them and cache at the edge); keep the Plausible edge script 91963; HTML cache as today.
- Old `/wp-content/uploads/*` URLs are 301s from the app (`src/se/media.ts`), so no storage rule is needed for them.

## Data
- First deployment: run `tools/fresh_import.sh` locally (≈4 min) and copy the resulting `data.db` to `/data/data.db`, media is imported straight into the S3 zone when `SE_STORAGE=s3` is set during the import. Or run the import against the staging instance (same script, `BASE` = staging URL).
- Backups: nightly copy of `/data/data.db` + the storage zone (EmDash's automatic JSON backups can also target the S3 zone).

## Plugin SE Ops
After the first start: Admin → Plugins → SE Ops → settings: Bunny API key, pull zone id `5962195`, Uptime Kuma push URL.
