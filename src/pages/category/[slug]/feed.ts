import type { APIRoute } from "astro";
import { getTerm } from "emdash";
import { buildFeed, rss } from "../../../se/feed";
/** category feed, same shape as WordPress ("Social Europe » <Name> Category Feed"). */
export const GET: APIRoute = async ({ params }) => {
	const term = await getTerm("category", params.slug!, { includeCounts: false });
	if (!term) return new Response(null, { status: 404 });
	return rss(await buildFeed({ where: { category: term.slug }, selfHref: `https://www.socialeurope.eu/category/${term.slug}/feed`, titleSuffix: ` » ${term.label} Category Feed` }));
};
