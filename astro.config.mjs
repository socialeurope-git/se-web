import node from "@astrojs/node";
import react from "@astrojs/react";
import auditLog from "@emdash-cms/plugin-audit-log";
import seOps from "se-ops";   // plugins/se-ops: Bunny purge on publish, Kuma heartbeat, admin purge button
import { defineConfig, fontProviders } from "astro/config";
import emdash, { local, s3 } from "emdash/astro";
import { sqlite } from "emdash/db";

// Media storage: local folder in development; Bunny Storage via its S3 API in staging/production (SE_STORAGE=s3).
// EmDash's own s3() adapter reads S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_REGION, S3_PUBLIC_URL
// from the environment at process start (Bunny: access key = zone name, secret = zone password, endpoint de-s3.storage.bunnycdn.com).
const storage = process.env.SE_STORAGE === "s3" ? s3() : local({ directory: "./uploads", baseUrl: "/_emdash/api/media/file" });

export default defineConfig({
	output: "server",
	adapter: node({
		mode: "standalone",
	}),
	image: {
		layout: "constrained",
		responsiveStyles: true,
	},
	integrations: [
		react(),
		emdash({
			database: sqlite({ url: process.env.EMDASH_DB_URL ?? "file:./data.db" }),   // container: file:/data/data.db on the persistent volume
			storage,
			plugins: [auditLog, seOps],
		}),
	],
	fonts: [
		{
			provider: fontProviders.google(),
			name: "Inter",
			cssVariable: "--font-body",
			weights: [400, 500, 600, 700],
			fallbacks: ["sans-serif"],
		},
		{
			provider: fontProviders.google(),
			name: "JetBrains Mono",
			cssVariable: "--font-mono",
			weights: [400, 500],
			fallbacks: ["monospace"],
		},
	],
	devToolbar: { enabled: false },
});
