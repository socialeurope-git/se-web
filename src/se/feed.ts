import type { APIRoute } from "astro";
import { getEmDashCollection } from "emdash";
import { cardHtml } from "./listing";
import { authors, fixtureForSlug } from "./data";
import fs from "node:fs";
import path from "node:path";
/** RSS feed, byte-compatible with the WordPress feed the newsletter routine and MailerLite read:
 *  10 newest posts, WordPress-style entities in titles, all bylines in dc:creator, ?p=<wp id> GUIDs, featured image + standfirst as description. */
const wpEntities = (s: string) => s.replace(/&/g, "&#038;").replace(/’/g, "&#8217;").replace(/‘/g, "&#8216;").replace(/“/g, "&#8220;").replace(/”/g, "&#8221;").replace(/…/g, "&#8230;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const rfc822 = (d: Date) => d.toUTCString().replace("GMT", "+0000");
let wpIds: Record<string, number> | null = null;
function wpId(slug: string): number | undefined {
	if (!wpIds) { wpIds = {}; const p = path.join(process.cwd(), "archive", "posts.json"); if (fs.existsSync(p)) for (const post of JSON.parse(fs.readFileSync(p, "utf8"))) wpIds[post.slug] = post.id; }
	return wpIds[slug];
}
export async function buildFeed(opts: { where?: Record<string, string>; filter?: (post: { id: string; data: Record<string, unknown> }) => boolean; selfHref: string; titleSuffix?: string } ): Promise<string> {
	const { entries: raw } = await getEmDashCollection("posts", { orderBy: { published_at: "desc" }, limit: opts.filter ? 200 : 10, ...(opts.where ? { where: opts.where } : {}) });
	const entries = (opts.filter ? (raw as unknown as { id: string; data: Record<string, unknown> }[]).filter(opts.filter) : (raw as unknown as { id: string; data: Record<string, unknown> }[])).slice(0, 10);
	const items = entries.map((post, idx) => {
		const slug = post.id as string; const d = post.data as Record<string, unknown>;
		const entryBylines = ((d.bylines ?? []) as { byline: { slug: string; displayName: string } }[]).map((c) => ({ slug: c.byline.slug, name: c.byline.displayName }));
		const fx = fixtureForSlug(slug);   // co-authors until the migration attaches them to the entry
		const bylines = ((fx?.bylines?.length ?? 0) > entryBylines.length ? fx!.bylines : entryBylines).map((b) => authors[b.slug]?.name ?? b.name);
		const creator = bylines.length <= 1 ? bylines.join("") : bylines.slice(0, -1).join(", ") + " and " + bylines[bylines.length - 1];
		const terms = d.terms as { category?: { label: string }[]; tag?: { label: string }[] } | undefined;
		const cats = [...(terms?.category ?? []), ...(terms?.tag ?? [])].map((c, i) => `${i === 0 ? "\t\t\t\t" : "\t\t"}<category><![CDATA[${c.label}]]></category>`).join("\n");
		const id = wpId(slug); const fi = d.featured_image as { src?: string; alt?: string } | undefined;
		const card = id ? cardHtml(id) : ""; const srcset = card.match(/<img [^>]*srcset="([^"]+)"/)?.[1];
		const altSrc = fi?.alt || card.match(/<img [^>]*alt="([^"]*)"/)?.[1] || (d.title as string);   // WordPress uses the attachment alt text
		const alt = altSrc.replace(/&#039;/g, "'").replace(/&amp;/g, "&").replace(/&/g, "&amp;").replace(/'/g, "&#039;").replace(/"/g, "&quot;");
		const img = fi?.src ? `<img width="1280" height="720" src="${fi.src}" class="attachment-full size-full wp-post-image" alt="${alt}" style="margin-bottom: 15px; display: block;" decoding="async"${idx === 0 ? ` fetchpriority="high"` : ""}${idx >= 3 ? ` loading="lazy"` : ""}${srcset ? ` srcset="${srcset}" sizes="${idx >= 3 ? "auto, " : ""}(max-width: 1280px) 100vw, 1280px"` : ""} />` : "";
		return `\t<item>
		<title>${wpEntities(d.title as string)}</title>
		<link>https://www.socialeurope.eu/${slug}</link>
		
		<dc:creator><![CDATA[${creator}]]></dc:creator>
		<pubDate>${rfc822(d.publishedAt as Date)}</pubDate>
${cats}
		<guid isPermaLink="false">https://www.socialeurope.eu/?p=${id ?? slug}</guid>

					<description><![CDATA[${img}${(d.excerpt as string) ?? ""}]]></description>
		
		
		
			</item>`;
	});
	const xml = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"
	xmlns:content="http://purl.org/rss/1.0/modules/content/"
	xmlns:wfw="http://wellformedweb.org/CommentAPI/"
	xmlns:dc="http://purl.org/dc/elements/1.1/"
	xmlns:atom="http://www.w3.org/2005/Atom"
	xmlns:sy="http://purl.org/rss/1.0/modules/syndication/"
	xmlns:slash="http://purl.org/rss/1.0/modules/slash/"
	>

<channel>
	<title>Social Europe${opts.titleSuffix ?? ""}</title>
	<atom:link href="${opts.selfHref}" rel="self" type="application/rss+xml" />
	<link>https://www.socialeurope.eu</link>
	<description></description>
	<lastBuildDate>${rfc822(new Date())}</lastBuildDate>
	<language>en-GB</language>
	<sy:updatePeriod>
	hourly	</sy:updatePeriod>
	<sy:updateFrequency>
	1	</sy:updateFrequency>
	<generator>https://wordpress.org/?v=7.1.2</generator>

<image>
	<url>https://www.socialeurope.eu/wp-content/uploads/2025/10/cropped-SE-scaled-1-150x150.png</url>
	<title>Social Europe</title>
	<link>https://www.socialeurope.eu</link>
	<width>32</width>
	<height>32</height>
</image> 
${items.map((it, i) => (i === 0 ? it : "\t" + it)).join("\n")}
	</channel>
</rss>
`;
	return xml;
}
export const rss = (xml: string) => new Response(xml, { headers: { "Content-Type": "application/rss+xml; charset=UTF-8" } });
export const GET: APIRoute = async () => rss(await buildFeed({ selfHref: "https://www.socialeurope.eu/feed" }));
