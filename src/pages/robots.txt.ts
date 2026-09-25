import type { APIRoute } from "astro";
/** Same robots.txt as the WordPress site. */
export const GET: APIRoute = () => new Response("User-agent: *\nDisallow: /wp-admin/\nAllow: /wp-admin/admin-ajax.php\n\nSitemap: https://www.socialeurope.eu/sitemap.xml\n", { headers: { "Content-Type": "text/plain; charset=utf-8" } });
