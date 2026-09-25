import type { APIRoute } from "astro";
import { getEmDashCollection } from "emdash";
/** Sitemap in The SEO Framework's shape: one urlset, home + pages + every post, with lastmod dates. */
const day = (d: Date | null | undefined) => (d ? new Date(d).toISOString().slice(0, 10) : "");
export const GET: APIRoute = async () => {
	const all: { loc: string; lastmod: string }[] = [];
	let cursor: string | undefined; let newest = "";
	const { entries: pages } = await getEmDashCollection("pages", { limit: 100 });
	do {
		const { entries, nextCursor } = await getEmDashCollection("posts", { orderBy: { published_at: "desc" }, limit: 100, cursor });
		for (const p of entries) { const lm = day((p.data as { updatedAt?: Date }).updatedAt ?? (p.data as { publishedAt?: Date }).publishedAt); all.push({ loc: `https://www.socialeurope.eu/${p.id}`, lastmod: lm }); if (lm > newest) newest = lm; }
		cursor = nextCursor ?? undefined;
	} while (cursor);
	const head = [{ loc: "https://www.socialeurope.eu/", lastmod: newest }, ...pages.map((p) => ({ loc: `https://www.socialeurope.eu/${p.id}`, lastmod: day((p.data as { updatedAt?: Date }).updatedAt) }))];
	const urls = [...head, ...all].map((u) => `\t<url>\n\t\t<loc>${u.loc}</loc>\n\t\t<lastmod>${u.lastmod}</lastmod>\n\t</url>`).join("\n");
	const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<?xml-stylesheet type="text/xsl" href="https://www.socialeurope.eu/sitemap.xsl"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">\n<!-- Sitemap is generated on ${new Date().toISOString().replace("T", " ").slice(0, 19)} GMT -->\n${urls}\n</urlset>\n`;
	return new Response(xml, { headers: { "Content-Type": "text/xml; charset=utf-8" } });
};
