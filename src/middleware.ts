import { defineMiddleware } from "astro:middleware";
import type { APIContext, MiddlewareNext } from "astro";
import { mediaRedirect, localiseMedia } from "./se/media";
import wpIds from "./se/data/wp-ids.json";
/** URL compatibility with the WordPress site:
 *  - snippet 34: /YYYY/MM/slug  -> /slug (301)
 *  - TSF SearchAction target:  /search/<term> -> /?s=<term> (301)
 *  - WordPress redirects trailing slashes on singular URLs to the canonical form without slash (301). */
/** Local browsing: the theme emits the live absolute URLs (https://www.socialeurope.eu/...) so that
 *  head, feed and sitemap stay byte-identical with the live site. In the dev server (and on a staging
 *  host, via SE_LINK_ORIGIN) rewrite the *body* links to the local origin so clicking around stays on
 *  the EmDash site. The <head> is left untouched, so head diffs against the live site still hold.
 *  Media (/wp-content/) keeps pointing at the live host until the uploads move to Bunny Storage. */
const LINK_ORIGIN = (globalThis as any).process?.env?.SE_LINK_ORIGIN || (import.meta.env.DEV ? "request" : "");
const LIVE = "https://www.socialeurope.eu";
function localiseLinks(html: string, origin: string): string {
	const i = html.indexOf("</head>");
	if (i < 0) return html;
	const body = html.slice(i).replace(/(href|action)="https:\/\/www\.socialeurope\.eu(\/(?!wp-content\/)[^"]*)?"/g, (_m, attr, path) => `${attr}="${origin}${path ?? "/"}"`);
	return html.slice(0, i) + body;
}

export const onRequest = defineMiddleware(async (ctx, next) => {
	const { pathname, search } = ctx.url;
	if (pathname.startsWith("/_emdash") || pathname.startsWith("/se/") || pathname.startsWith("/_astro")) return next();
	const res = await route(ctx, next);
	const ct = res.headers.get("content-type") || "";
	const isHtml = ct.includes("text/html"), isXml = ct.includes("xml");
	if (!isHtml && !isXml) return res;
	// media: every legacy upload URL the theme still emits (fixtures, cards, avatars, feed, head) -> EmDash media
	const siteOrigin = LINK_ORIGIN === "request" ? ctx.url.origin : LINK_ORIGIN || LIVE;
	let text = localiseMedia(await res.text(), siteOrigin);
	if (isHtml && LINK_ORIGIN) text = localiseLinks(text, siteOrigin);
	const headers = new Headers(res.headers); headers.delete("content-length");
	return new Response(text, { status: res.status, statusText: res.statusText, headers });
});

async function route(ctx: APIContext, next: MiddlewareNext): Promise<Response> {
	const { pathname, search } = ctx.url;
	// WordPress "ugly" permalinks (?p=<id>, ?page_id=<id>; the old feed GUIDs) -> the slug
	if (pathname === "/" && (ctx.url.searchParams.has("p") || ctx.url.searchParams.has("page_id"))) {
		const slug = (wpIds as { posts: Record<string, string>; pages: Record<string, string> }).posts[ctx.url.searchParams.get("p") ?? ""] ?? (wpIds as { pages: Record<string, string> }).pages[ctx.url.searchParams.get("page_id") ?? ""];
		if (slug) return ctx.redirect(`/${slug}`, 301);
	}
	// legacy WordPress upload URLs -> the EmDash media item (originals; size variants collapse onto the original)
	if (pathname.startsWith("/wp-content/uploads/")) { const to = mediaRedirect(pathname); return to ? ctx.redirect(to, 301) : new Response("Not found", { status: 404 }); }
	const dated = pathname.match(/^\/(\d{4})\/(\d{2})\/([^\/]+)\/?$/);
	if (dated) return ctx.redirect(`/${dated[3]}${search}`, 301);
	const srch = pathname.match(/^\/search\/([^\/]+)\/?$/);
	if (srch) return ctx.redirect(`/?s=${encodeURIComponent(decodeURIComponent(srch[1]))}`, 301);
	if (pathname.length > 1 && pathname.endsWith("/") && !pathname.startsWith("/page/")) return ctx.redirect(pathname.slice(0, -1) + search, 301);
	return next();
}
