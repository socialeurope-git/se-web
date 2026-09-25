import { defineMiddleware } from "astro:middleware";
import type { APIContext, MiddlewareNext } from "astro";
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
function localiseLinks(html: string, origin: string): string {
	const i = html.indexOf("</head>");
	if (i < 0) return html;
	const body = html.slice(i).replace(/(href|action)="https:\/\/www\.socialeurope\.eu(\/(?!wp-content\/)[^"]*)?"/g, (_m, attr, path) => `${attr}="${origin}${path ?? "/"}"`);
	return html.slice(0, i) + body;
}

export const onRequest = defineMiddleware(async (ctx, next) => {
	const { pathname, search } = ctx.url;
	if (pathname.startsWith("/_emdash") || pathname.startsWith("/se/") || pathname.startsWith("/_astro")) return next();
	if (LINK_ORIGIN) {
		const res = await route(ctx, next);
		if (!(res.headers.get("content-type") || "").includes("text/html")) return res;
		const origin = LINK_ORIGIN === "request" ? ctx.url.origin : LINK_ORIGIN;
		const html = localiseLinks(await res.text(), origin);
		const headers = new Headers(res.headers); headers.delete("content-length");
		return new Response(html, { status: res.status, statusText: res.statusText, headers });
	}
	return route(ctx, next);
});

async function route(ctx: APIContext, next: MiddlewareNext): Promise<Response> {
	const { pathname, search } = ctx.url;
	const dated = pathname.match(/^\/(\d{4})\/(\d{2})\/([^\/]+)\/?$/);
	if (dated) return ctx.redirect(`/${dated[3]}${search}`, 301);
	const srch = pathname.match(/^\/search\/([^\/]+)\/?$/);
	if (srch) return ctx.redirect(`/?s=${encodeURIComponent(decodeURIComponent(srch[1]))}`, 301);
	if (pathname.length > 1 && pathname.endsWith("/") && !pathname.startsWith("/page/")) return ctx.redirect(pathname.slice(0, -1) + search, 301);
	return next();
}
