# Dockerfile of the official EmDash Node.js guide (docs.emdashcms.com/deployment/nodejs), plus the site's own plugin
# package (plugins/se-ops, a file: dependency whose built files ship in the repo).
FROM node:22-alpine AS builder
WORKDIR /app
# astro.config.mjs is evaluated at build time: the database path and the storage adapter choice are baked into the
# bundle, so the production values are set here. S3 credentials are read from the runtime environment by s3().
ENV NODE_ENV=production DATABASE_PATH=/app/data/data.db S3_BUCKET=se-media
COPY package*.json ./
COPY plugins/se-ops/package.json plugins/se-ops/emdash-plugin.jsonc plugins/se-ops/
COPY plugins/se-ops/dist plugins/se-ops/dist
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/plugins/se-ops ./plugins/se-ops
COPY --from=builder /app/public ./public
RUN mkdir -p data
ENV HOST=0.0.0.0
ENV PORT=4321
EXPOSE 4321
CMD ["node", "./dist/server/entry.mjs"]
