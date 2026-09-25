import type { APIRoute } from "astro";
import { buildFeed, rss } from "../../../se/feed";
import { authors } from "../../../se/data";
import { fixtureForSlug } from "../../../se/data";
/** author feed: posts whose bylines include the author (co-authors included). */
export const GET: APIRoute = async ({ params }) => {
	const slug = params.slug!; const a = authors[slug];
	const has = (post: { id: string; data: Record<string, unknown> }) => {
		const fx = fixtureForSlug(post.id); const bl = fx?.bylines?.length ? fx.bylines : ((post.data.bylines ?? []) as { byline: { slug: string } }[]).map((c) => ({ slug: c.byline.slug }));
		return bl.some((b) => b.slug === slug);
	};
	return rss(await buildFeed({ filter: has, selfHref: `https://www.socialeurope.eu/author/${slug}/feed`, titleSuffix: ` » Posts by ${a?.name ?? slug} Feed` }));
};
