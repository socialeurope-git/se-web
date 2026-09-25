import type { APIRoute } from "astro";
import { getBylineBySlug } from "emdash";
import { buildFeed, rss } from "../../../se/feed";
/** author feed: posts credited to the byline (co-authors included). */
export const GET: APIRoute = async ({ params }) => {
	const b = (await getBylineBySlug(params.slug!)) as { id: string; displayName: string; translationGroup?: string | null } | null;
	if (!b) return new Response(null, { status: 404 });
	return rss(await buildFeed({ where: { byline: b.translationGroup ?? b.id }, selfHref: `https://www.socialeurope.eu/author/${params.slug}/feed`, titleSuffix: ` » Posts by ${b.displayName} Feed` }));
};
