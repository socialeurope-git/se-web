import type { APIRoute } from "astro";
import { getTerm } from "emdash";
import { buildFeed, rss } from "../../../se/feed";
/** tag feed, same shape as WordPress ("Social Europe » <Name> Tag Feed"). */
export const GET: APIRoute = async ({ params }) => {
	const term = await getTerm("tag", params.slug!, { includeCounts: false });
	if (!term) return new Response(null, { status: 404 });
	return rss(await buildFeed({ where: { tag: term.slug }, selfHref: `https://www.socialeurope.eu/tag/${term.slug}/feed`, titleSuffix: ` » ${term.label} Tag Feed` }));
};
