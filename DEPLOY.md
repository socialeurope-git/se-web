# Deploying Social Europe (EmDash) to Bunny Magic Containers

## Image
`Dockerfile` follows the official Node.js deployment guide (node:22-alpine, `node ./dist/server/entry.mjs`, port 4321,
data directory `/app/data`); `.github/workflows/image.yml` pushes `ghcr.io/socialeurope-git/se-web:latest` on every push to
`main` and triggers the Bunny deploy. Health: `/health` (process alive) and `/_emdash/api/health`.

## Runtime environment (Magic Containers app → container env)
| Variable | Value |
|---|---|
| `DATABASE_PATH` | `/app/data/data.db` — `/app/data` is the persistent volume (SQLite). Baked into the image at build time (astro.config runs during `astro build`), the runtime value must match |
| `EMDASH_ENCRYPTION_KEY` | from `npx emdash secrets generate`; keep with the backups (plugin secrets are unreadable without it) |
| `EMDASH_SITE_URL` | public origin, e.g. `https://mc-hdck3f7ufk.bunny.run` (staging) or `https://www.socialeurope.eu`; required behind the CDN for passkeys, CSRF, sitemap |
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
- Old `/wp-content/uploads/*` URLs are 301s from the app (`src/se/media.ts`), so no storage rule is needed for them.

## Data
- First deployment: complete the setup wizard on the new host (admin with passkey, no sample content), create an API token with the admin scope, then run `SE_BASE=https://<host> SE_TOKEN=<token> sh tools/fresh_import.sh archive/wxr-all.xml` — content, media (straight into the S3 zone), bylines, menus, widgets, SEO.
- Backups: nightly copy of `/app/data/emdash.db` + the storage zone (EmDash's automatic JSON backups can also target the S3 zone).

## Plugin SE Ops
After the first start: Admin → Plugins → SE Ops → settings: Bunny API key, pull zone id `5962195`, Uptime Kuma push URL.
