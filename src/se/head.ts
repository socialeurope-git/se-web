/** <head> generator reproducing The SEO Framework + snippet 39 output of the live site, tag for tag. */
import { escapeHtml } from "./format";
const SITE = "https://www.socialeurope.eu"; const LOGO = `${SITE}/wp-content/uploads/2025/10/cropped-SE-scaled-1.png`;
const LOGO_ALT = "Social Europe logo, SE, in red letters on white background.";
const ORG_FULL = `{"@type":"Organization","@id":"${SITE}/#/schema/Organization","name":"Social Europe","url":"${SITE}/","logo":{"@type":"ImageObject","url":"${LOGO}","contentUrl":"${LOGO}","width":512,"height":512,"contentSize":"2031"}}`;
const WEBSITE = (publisher: string) => `{"@type":"WebSite","@id":"${SITE}/#/schema/WebSite","url":"${SITE}/","name":"Social Europe","inLanguage":"en-GB","potentialAction":{"@type":"SearchAction","target":{"@type":"EntryPoint","urlTemplate":"${SITE}/search/{search_term_string}"},"query-input":"required name=search_term_string"},"publisher":${publisher}}`;
const jsonStr = (s: string) => JSON.stringify(s).replace(/\//g, "\\/").slice(1, -1);   // TSF escapes slashes like PHP json_encode
const attr = (s: string) => s.replace(/&(?!(amp|#\d+|[a-z]+);)/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");

export type HeadInput = {
	kind: "article" | "home" | "category" | "tag" | "author" | "page" | "search" | "notfound";
	title: string; canonical: string; description?: string | null; ogDescription?: string | null;
	ogTitle?: string; ogType?: "article" | "website" | "profile";
	image?: { url: string; w?: number | null; h?: number | null; alt?: string } | null;
	prev?: string | null; next?: string | null;
	published?: string | null; modified?: string | null;      // YYYY-MM-DD (article:published_time)
	feed?: { title: string; href: string } | null;             // extra feed link (category/author)
	jsonLink?: string | null; oembedUrl?: string | null;       // WP REST / oEmbed discovery links (kept for parity)
	robots?: string;
	// JSON-LD bits
	breadcrumbs?: { item?: string; name: string }[];           // after the home crumb
	pageType?: "WebPage" | "CollectionPage";
	author?: { name: string; personId?: string | null; desc?: string | null } | null;
	readAction?: boolean; aboutOrg?: boolean; publisherFull?: boolean;
	newsArticle?: { url: string; headline: string; datePublished: string; dateModified: string; authors: { name: string; url: string }[]; description: string; image: { url: string; w: number; h: number } | null; sections: string[]; keywords?: string | string[] | null; wordCount: number } | null;
};
export function renderHead(i: HeadInput): string {
	const out: string[] = [];
	const push = (s: string) => out.push(s);
	push(`<meta charset="UTF-8">`); push(`<title>${escapeHtml(i.title)}</title>`); push(`<meta name="viewport" content="width=device-width, initial-scale=1">`);
	push(`<meta name="robots" content="${i.robots ?? "max-snippet:-1,max-image-preview:large,max-video-preview:-1"}" />`);
	push(`<link rel="canonical" href="${i.canonical}" />`);
	if (i.prev) push(`<link rel="prev" href="${i.prev}" />`); if (i.next) push(`<link rel="next" href="${i.next}" />`);
	if (i.description) push(`<meta name="description" content="${attr(i.description)}" />`);
	const ogTitle = i.ogTitle ?? i.title; const img = i.image ?? { url: LOGO, w: 512, h: 512, alt: LOGO_ALT };
	push(`<meta property="og:type" content="${i.ogType ?? "website"}" />`); push(`<meta property="og:locale" content="en_GB" />`); push(`<meta property="og:site_name" content="Social Europe" />`);
	push(`<meta property="og:title" content="${attr(ogTitle)}" />`); const ogd = i.ogDescription ?? i.description; if (ogd) push(`<meta property="og:description" content="${attr(ogd)}" />`);
	push(`<meta property="og:url" content="${i.canonical}" />`); push(`<meta property="og:image" content="${img.url}" />`);
	if (img.w && img.h) { push(`<meta property="og:image:width" content="${img.w}" />`); push(`<meta property="og:image:height" content="${img.h}" />`); }
	if (img.alt) push(`<meta property="og:image:alt" content="${attr(img.alt)}" />`);
	if (i.published) push(`<meta property="article:published_time" content="${i.published}" />`); if (i.modified) push(`<meta property="article:modified_time" content="${i.modified}" />`);
	push(`<meta name="twitter:card" content="summary_large_image" />`); push(`<meta name="twitter:title" content="${attr(ogTitle)}" />`); if (ogd) push(`<meta name="twitter:description" content="${attr(ogd)}" />`);
	push(`<meta name="twitter:image" content="${img.url}" />`); if (img.alt) push(`<meta name="twitter:image:alt" content="${attr(img.alt)}" />`);
	// JSON-LD graph (TSF)
	const crumbs = [{ item: `${SITE}/`, name: "Social Europe" }, ...(i.breadcrumbs ?? [])];
	const crumbList = crumbs.length === 1 ? `{"@type":"ListItem","position":1,"name":"Social Europe"}` : `[${crumbs.map((c, n) => `{"@type":"ListItem","position":${n + 1}${c.item && n < crumbs.length - 1 ? `,"item":"${jsonStr(c.item)}"` : ""},"name":"${jsonStr(c.name)}"}`).join(",")}]`;
	const pageNode = `{"@type":"${i.pageType ?? "WebPage"}","@id":"${jsonStr(i.canonical)}","url":"${jsonStr(i.canonical)}","name":"${jsonStr(i.title)}"${i.description ? `,"description":"${jsonStr(i.description)}"` : ""},"inLanguage":"en-GB","isPartOf":{"@id":"${SITE}\\/#\\/schema\\/WebSite"},"breadcrumb":{"@type":"BreadcrumbList","@id":"${SITE}\\/#\\/schema\\/BreadcrumbList","itemListElement":${crumbList}}${i.readAction ? `,"potentialAction":{"@type":"ReadAction","target":"${jsonStr(i.canonical)}"}` : ""}${i.aboutOrg ? `,"about":{"@id":"${SITE}\\/#\\/schema\\/Organization"}` : ""}${i.published && i.kind === "article" ? `,"datePublished":"${i.published}","dateModified":"${i.modified ?? i.published}"` : ""}${i.author ? `,"author":{"@type":"Person","@id":"${jsonStr(i.author.personId ?? `${SITE}/#/schema/Person/unknown`)}","name":"${jsonStr(i.author.name)}"${i.author.desc ? `,"description":"${jsonStr(i.author.desc)}"` : ""}}` : ""}}`;
	const website = WEBSITE(i.publisherFull === false ? `{"@id":"${SITE}\\/#\\/schema\\/Organization"}` : ORG_FULL.replace(/\//g, "\\/"));
	const graph = `{"@context":"https:\\/\\/schema.org","@graph":[${website.replace(/(?<!\\)\//g, "\\/")},${pageNode}${i.aboutOrg ? "," + ORG_FULL.replace(/\//g, "\\/") : ""}]}`;
	push(`<script type="application/ld+json">${graph}</script>`);
	push(`<link rel="alternate" type="application/rss+xml" title="Social Europe &raquo; Feed" href="${SITE}/feed" />`);
	push(`<link rel="alternate" type="application/rss+xml" title="Social Europe &raquo; Comments Feed" href="${SITE}/comments/feed" />`);
	if (i.feed) push(`<link rel="alternate" type="application/rss+xml" title="Social Europe &raquo; ${i.feed.title}" href="${i.feed.href}" />`);
	if (i.oembedUrl) { const u = encodeURIComponent(i.oembedUrl); push(`<link rel="alternate" title="oEmbed (JSON)" type="application/json+oembed" href="${SITE}/wp-json/oembed/1.0/embed?url=${u}" />`); push(`<link rel="alternate" title="oEmbed (XML)" type="text/xml+oembed" href="${SITE}/wp-json/oembed/1.0/embed?url=${u}&#038;format=xml" />`); }
	push(`<link rel="https://api.w.org/" href="${SITE}/wp-json/" />`);
	if (i.jsonLink) push(`<link rel="alternate" title="JSON" type="application/json" href="${i.jsonLink}" />`);
	push(`<link rel="EditURI" type="application/rsd+xml" title="RSD" href="${SITE}/xmlrpc.php?rsd" />`);
	if (i.newsArticle) {
		const n = i.newsArticle;
		const authors = n.authors.map((a) => `{"@type":"Person","name":"${jsonStr(a.name)}","url":"${jsonStr(a.url)}"}`).join(",");
		push(`<script type="application/ld+json">{"@context":"https:\\/\\/schema.org","@type":"NewsArticle","@id":"${jsonStr(n.url)}#article","mainEntityOfPage":"${jsonStr(n.url)}","url":"${jsonStr(n.url)}","headline":"${jsonStr(n.headline)}","datePublished":"${n.datePublished}","dateModified":"${n.dateModified}","inLanguage":"en-GB","isAccessibleForFree":true,"publisher":{"@type":"Organization","name":"Social Europe","url":"${SITE}\\/","logo":{"@type":"ImageObject","url":"${jsonStr(LOGO)}"}},"author":[${authors}],"description":"${jsonStr(n.description)}"${n.image ? `,"image":{"@type":"ImageObject","url":"${jsonStr(n.image.url)}","width":${n.image.w},"height":${n.image.h}}` : ""},"articleSection":[${n.sections.map((s) => `"${jsonStr(s)}"`).join(",")}]${n.keywords ? `,"keywords":${Array.isArray(n.keywords) ? `[${n.keywords.map((k) => `"${jsonStr(k)}"`).join(",")}]` : `"${jsonStr(n.keywords)}"`}` : ""},"wordCount":${n.wordCount}}</script>`);
	}
	return out.join("\n");
}
