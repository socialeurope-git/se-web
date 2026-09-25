import { defineMiddleware } from "astro:middleware";
/** URL compatibility with the WordPress site:
 *  - snippet 34: /YYYY/MM/slug  -> /slug (301)
 *  - TSF SearchAction target:  /search/<term> -> /?s=<term> (301)
 *  - WordPress redirects trailing slashes on singular URLs to the canonical form without slash (301). */
export const onRequest = defineMiddleware(async (ctx, next) => {
	const { pathname, search } = ctx.url;
	if (pathname.startsWith("/_emdash") || pathname.startsWith("/se/") || pathname.startsWith("/_astro")) return next();
	const dated = pathname.match(/^\/(\d{4})\/(\d{2})\/([^\/]+)\/?$/);
	if (dated) return ctx.redirect(`/${dated[3]}${search}`, 301);
	const srch = pathname.match(/^\/search\/([^\/]+)\/?$/);
	if (srch) return ctx.redirect(`/?s=${encodeURIComponent(decodeURIComponent(srch[1]))}`, 301);
	if (pathname.length > 1 && pathname.endsWith("/") && !pathname.startsWith("/page/")) return ctx.redirect(pathname.slice(0, -1) + search, 301);
	return next();
});
