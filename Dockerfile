# Social Europe on EmDash — Node standalone build for Bunny Magic Containers.
# Build:  docker build -t se-web .
# Run:    docker run -p 3000:3000 -v se-data:/data -e EMDASH_DB_URL=file:/data/data.db -e SE_STORAGE=s3 -e S3_ENDPOINT=... se-web
FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY plugins/se-ops/package.json plugins/se-ops/package.json
COPY plugins/se-ops/dist plugins/se-ops/dist
COPY plugins/se-ops/emdash-plugin.jsonc plugins/se-ops/emdash-plugin.jsonc
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM node:22-bookworm-slim
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000 EMDASH_DB_URL=file:/data/data.db
WORKDIR /app
COPY --from=build /app/package.json /app/package-lock.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/public ./public
COPY --from=build /app/plugins/se-ops ./plugins/se-ops
COPY --from=build /app/seed ./seed
RUN mkdir -p /data /app/uploads && chown -R node:node /data /app
USER node
VOLUME ["/data"]
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD node -e "fetch('http://127.0.0.1:3000/_emdash/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "./dist/server/entry.mjs"]
