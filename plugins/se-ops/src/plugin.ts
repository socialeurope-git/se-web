import type { SandboxedPlugin, PluginContext } from "emdash/plugin";
import type { BlockResponse } from "@emdash-cms/blocks";

/** Social Europe operations plugin.
 *  - Bunny CDN: purge the affected URLs when an entry is published, unpublished, restored or deleted
 *    (entry, home, feed, sitemaps, its category and author archives), and a full-zone purge button in the admin.
 *  - Uptime Kuma: heartbeat push every five minutes (cron), so a dead site raises an alert.
 *  Settings (encrypted where marked): site_url, bunny_api_key, pull_zone_id, kuma_push_url. */

const BUNNY = "https://api.bunny.net";

async function settings(ctx: { settings: { get<T>(k: string): Promise<T | null | undefined> } }) {
	const site = ((await ctx.settings.get<string>("site_url")) || "https://www.socialeurope.eu").replace(/\/+$/, "");
	return { site, key: (await ctx.settings.get<string>("bunny_api_key")) || "", zone: (await ctx.settings.get<string>("pull_zone_id")) || "", kuma: (await ctx.settings.get<string>("kuma_push_url")) || "" };
}

/** URLs to purge for a content event: the entry, the listings that show it, feeds and sitemaps. */
function urlsFor(site: string, collection: string, content: Record<string, unknown>): string[] {
	const slug = typeof content.slug === "string" ? content.slug : null;
	const urls = new Set<string>([`${site}/`, `${site}/feed`, `${site}/sitemap.xml`, `${site}/sitemap-${collection}.xml`]);
	if (slug) urls.add(`${site}/${slug}`);
	const terms = content.terms as Record<string, { slug?: string }[]> | undefined;
	for (const t of terms?.category ?? []) if (t.slug) { urls.add(`${site}/category/${t.slug}`); urls.add(`${site}/category/${t.slug}/feed`); }
	for (const t of terms?.tag ?? []) if (t.slug) urls.add(`${site}/tag/${t.slug}`);
	const bylines = content.bylines as { byline?: { slug?: string } }[] | undefined;
	for (const c of bylines ?? []) if (c.byline?.slug) { urls.add(`${site}/author/${c.byline.slug}`); urls.add(`${site}/author/${c.byline.slug}/feed`); }
	return [...urls];
}

type Ctx = PluginContext;

async function purgeUrls(ctx: Ctx, urls: string[]): Promise<{ ok: number; failed: string[] }> {
	const { key } = await settings(ctx);
	if (!key) { ctx.log.warn("se-ops: no Bunny API key configured, purge skipped", { urls: urls.length }); return { ok: 0, failed: urls }; }
	let ok = 0; const failed: string[] = [];
	for (const url of urls) {
		try {
			const r = await ctx.http!.fetch(`${BUNNY}/purge?url=${encodeURIComponent(url)}&async=false`, { method: "POST", headers: { AccessKey: key } });
			if (r.ok) ok++; else failed.push(`${url} (${r.status})`);
		} catch (e) { failed.push(`${url} (${String(e).slice(0, 80)})`); }
	}
	ctx.log.info("se-ops: purged", { ok, failed: failed.length });
	return { ok, failed };
}

async function purgeZone(ctx: Ctx): Promise<string> {
	const { key, zone } = await settings(ctx);
	if (!key || !zone) return "Bunny API key or pull zone ID missing";
	const r = await ctx.http!.fetch(`${BUNNY}/pullzone/${encodeURIComponent(zone)}/purgeCache`, { method: "POST", headers: { AccessKey: key, "Content-Type": "application/json" }, body: "{}" });
	return r.ok ? `Pull zone ${zone} purged` : `Purge failed: HTTP ${r.status}`;
}

async function heartbeat(ctx: Ctx): Promise<string> {
	const { kuma } = await settings(ctx);
	if (!kuma) return "no Kuma push URL configured";
	try { const r = await ctx.http!.fetch(kuma, { method: "GET" }); return r.ok ? "heartbeat sent" : `Kuma answered HTTP ${r.status}`; }
	catch (e) { return `heartbeat failed: ${String(e).slice(0, 80)}`; }
}

const onContent = async (event: { content: Record<string, unknown>; collection: string }, ctx: Ctx) => {
	const { site } = await settings(ctx);
	await purgeUrls(ctx, urlsFor(site, event.collection, event.content));
};

function page(status: { kuma: string; purge?: string; configured: boolean }): BlockResponse {
	return {
		blocks: [
			{ type: "header", text: "Social Europe operations" },
			{ type: "section", text: status.configured ? "Bunny purge on publish is active." : "Bunny API key or pull zone ID missing — set them under Plugins → SE Ops → Settings." },
			{ type: "section", text: `Uptime Kuma: ${status.kuma}` },
			...(status.purge ? [{ type: "section" as const, text: status.purge }] : []),
			{ type: "actions", elements: [
				{ type: "button", action_id: "purge_all", label: "Purge entire CDN cache", style: "danger", confirm: { title: "Purge the whole pull zone?", text: "Every cached page and image will be fetched again from the origin.", confirm: "Purge", deny: "Cancel" } },
				{ type: "button", action_id: "heartbeat", label: "Send Kuma heartbeat now" },
			] },
		],
	};
}

const plugin: SandboxedPlugin = {
	hooks: {
		"plugin:activate": async (_event, ctx) => { await ctx.cron!.schedule("kuma-heartbeat", { schedule: "*/5 * * * *" }); },
		cron: async (event, ctx) => { if (event.name === "kuma-heartbeat") ctx.log.info("se-ops: " + (await heartbeat(ctx))); },
		"content:afterPublish": onContent,
		"content:afterUnpublish": onContent,
		"content:afterRestore": onContent,
		"content:afterDelete": async (event, ctx) => { const { site } = await settings(ctx); await purgeUrls(ctx, urlsFor(site, event.collection, {})); },
	},
	routes: {
		admin: {
			permission: "plugins:manage",
			handler: async (routeCtx, ctx) => {
				const i = routeCtx.input as { type?: string; action_id?: string };
				const { key, zone, kuma } = await settings(ctx);
				const status = { kuma: kuma ? "push URL configured (every 5 min)" : "not configured", configured: !!(key && zone), purge: undefined as string | undefined };
				if (i.type === "block_action" && i.action_id === "purge_all") { status.purge = await purgeZone(ctx); return { ...page(status), toast: { type: "success", message: status.purge } }; }
				if (i.type === "block_action" && i.action_id === "heartbeat") { const r = await heartbeat(ctx); return { ...page({ ...status, purge: r }), toast: { type: "info", message: r } }; }
				return page(status);
			},
		},
		"purge-all": { permission: "plugins:manage", methods: ["POST"], handler: async (_r, ctx) => ({ result: await purgeZone(ctx) }) },
		heartbeat: { permission: "plugins:manage", methods: ["POST"], handler: async (_r, ctx) => ({ result: await heartbeat(ctx) }) },
	},
};

export default plugin;
