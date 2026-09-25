import { getEmDashCollection } from "emdash";
import { SITE, SITE_TITLE, postUrl, credits, joinNames, absolute, type Entry } from "./site";
/** RSS feed in the shape the newsletter routine and MailerLite read from the WordPress site:
 *  10 newest posts, all bylines in dc:creator, categories + tags as <category>, featured image + standfirst as description. */
const xml = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const rfc822 = (d: Date) => d.toUTCString().replace("GMT", "+0000");
export async function buildFeed(opts: { where?: Record<string, string>; selfHref: string; titleSuffix?: string }): Promise<string> {
	const { entries: raw } = await getEmDashCollection("posts", { orderBy: { published_at: "desc" }, limit: 10, ...(opts.where ? { where: opts.where } : {}) });
	const items = (raw as unknown as Entry[]).map((post, idx) => {
		const d = post.data; const url = postUrl(post.id);
		const creator = joinNames(credits(post).map((b) => b.displayName));
		const cats = [...(d.terms?.category ?? []), ...(d.terms?.tag ?? [])].map((c) => `\t\t<category><![CDATA[${c.label}]]></category>`).join("\n");
		const fi = d.featured_image; const src = absolute(fi?.src);
		const img = src ? `<img width="1280" height="720" src="${src}" class="attachment-full size-full wp-post-image" alt="${xml(fi?.alt || d.title).replace(/"/g, "&quot;")}" style="margin-bottom: 15px; display: block;" decoding="async"${idx === 0 ? ` fetchpriority="high"` : ""}${idx >= 3 ? ` loading="lazy"` : ""} />` : "";
		return `\t<item>
		<title>${xml(d.title)}</title>
		<link>${url}</link>
		<dc:creator><![CDATA[${creator}]]></dc:creator>
		<pubDate>${d.publishedAt ? rfc822(d.publishedAt) : ""}</pubDate>
${cats}
		<guid isPermaLink="true">${url}</guid>
		<description><![CDATA[${img}${d.excerpt ?? ""}]]></description>
	</item>`;
	});
	return `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"
	xmlns:content="http://purl.org/rss/1.0/modules/content/"
	xmlns:dc="http://purl.org/dc/elements/1.1/"
	xmlns:atom="http://www.w3.org/2005/Atom"
	xmlns:sy="http://purl.org/rss/1.0/modules/syndication/"
	>
<channel>
	<title>${SITE_TITLE}${opts.titleSuffix ?? ""}</title>
	<atom:link href="${opts.selfHref}" rel="self" type="application/rss+xml" />
	<link>${SITE}</link>
	<description></description>
	<lastBuildDate>${rfc822(new Date())}</lastBuildDate>
	<language>en-GB</language>
	<sy:updatePeriod>hourly</sy:updatePeriod>
	<sy:updateFrequency>1</sy:updateFrequency>
${items.join("\n")}
</channel>
</rss>
`;
}
export const rss = (body: string) => new Response(body, { headers: { "Content-Type": "application/rss+xml; charset=UTF-8" } });
