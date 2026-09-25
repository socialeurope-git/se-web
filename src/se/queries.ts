/** Content queries the theme needs beyond a single entry: related posts and the Most Read list. */
import { getEmDashCollection, getEmDashEntry, getTerm, getBylineBySlug } from "emdash";
import mostReadSlugs from "./data/most-read.json";
import type { Entry, Term, Byline } from "./site";
/** Newest posts of the same category, excluding the current one. (The live site's embedding-based related service can replace this later.) */
export async function relatedPosts(category: Term | undefined, excludeSlug: string, n: number): Promise<Entry[]> {
	if (!category) return [];
	const { entries } = await getEmDashCollection("posts", { where: { category: category.slug }, orderBy: { published_at: "desc" }, limit: n + 1 });
	return (entries as unknown as Entry[]).filter((e) => e.id !== excludeSlug).slice(0, n);
}
/** Most Read (past seven days) — slugs come from Plausible (src/se/data/most-read.json), entries from EmDash. */
export async function mostRead(n: number): Promise<Entry[]> {
	const out: Entry[] = [];
	for (const slug of (mostReadSlugs as string[]).slice(0, n)) { const { entry } = await getEmDashEntry("posts", slug); if (entry) out.push(entry as unknown as Entry); }
	return out;
}

export type ListingKind = "home" | "category" | "tag" | "author";
export type ListingData = { kind: ListingKind; slug: string | null; page: number; term: Term | null; byline: Byline | null; entries: Entry[]; hasNext: boolean; cacheHint: unknown };
/** Archive data for Listing.astro: 15 cards + 14 list items on homepage page 1, 15 per later homepage page, 16 per archive page. Null = 404. */
export async function loadListing(kind: ListingKind, slug: string | null, page: number): Promise<ListingData | null> {
	if (!Number.isInteger(page) || page < 1) return null;
	let term: Term | null = null; let byline: Byline | null = null; let where: Record<string, string> | undefined;
	if (kind === "category" || kind === "tag") { term = (await getTerm(kind, slug!)) as unknown as Term | null; if (!term) return null; where = { [kind]: term.slug }; }
	if (kind === "author") { byline = (await getBylineBySlug(slug!)) as unknown as Byline | null; if (!byline) return null; where = { byline: byline.translationGroup ?? byline.id }; }
	const per = kind === "home" ? 15 : 16;
	const offset = kind === "home" ? (page === 1 ? 0 : 29 + (page - 2) * 15) : (page - 1) * per;
	const want = kind === "home" && page === 1 ? 29 : per;
	const { entries: raw, cacheHint } = await getEmDashCollection("posts", { ...(where ? { where } : {}), orderBy: { published_at: "desc" }, limit: want + 1, offset });
	const entries = raw as unknown as Entry[];
	if (!entries.length && !(kind === "home" && page === 1)) return null;
	return { kind, slug, page, term, byline, entries: entries.slice(0, want), hasNext: entries.length > want, cacheHint };
}
