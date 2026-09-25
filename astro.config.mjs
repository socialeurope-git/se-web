import node from "@astrojs/node";
import react from "@astrojs/react";
import auditLog from "@emdash-cms/plugin-audit-log";
import seOps from "se-ops";   // plugins/se-ops: Bunny purge on publish, Kuma heartbeat, admin purge button
import { defineConfig, fontProviders } from "astro/config";
import emdash, { local, s3 } from "emdash/astro";
import { sqlite } from "emdash/db";

// Deployment pattern of the official Node.js guide (docs.emdashcms.com/deployment/nodejs): SQLite on a persistent
// volume via DATABASE_PATH, media in S3-compatible storage via the S3_* variables, local storage for development.
const storage = process.env.S3_BUCKET ? s3() : local({ directory: "./uploads", baseUrl: "/_emdash/api/media/file" });

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
			database: sqlite({ url: `file:${process.env.DATABASE_PATH ?? "./data.db"}` }),
			storage,
			// Public origin behind the CDN/TLS proxy (passkeys, CSRF, sitemap): EMDASH_SITE_URL, extra hostnames via EMDASH_ALLOWED_ORIGINS
			...(process.env.EMDASH_SITE_URL ? { siteUrl: process.env.EMDASH_SITE_URL } : {}),
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
