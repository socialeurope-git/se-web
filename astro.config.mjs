import node from "@astrojs/node";
import react from "@astrojs/react";
import auditLog from "@emdash-cms/plugin-audit-log";
import { defineConfig, fontProviders } from "astro/config";
import emdash, { local } from "emdash/astro";
import { sqlite } from "emdash/db";
import { fileURLToPath } from "node:url";

// Media storage: local folder in development; Bunny Storage zone (src/se/storage/bunny.ts) when SE_STORAGE=bunny.
// The zone password comes from BUNNY_STORAGE_KEY at runtime, never from this file.
const storage = process.env.SE_STORAGE === "bunny"
	? { entrypoint: fileURLToPath(new URL("./src/se/storage/bunny.ts", import.meta.url)), config: { zone: process.env.BUNNY_STORAGE_ZONE ?? "socialeurope-media", prefix: "media", publicUrl: process.env.SE_PUBLIC_URL ?? "https://www.socialeurope.eu" } }
	: local({ directory: "./uploads", baseUrl: "/_emdash/api/media/file" });

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
			database: sqlite({ url: "file:./data.db" }),
			storage,
			plugins: [auditLog],
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
