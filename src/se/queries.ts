/** Content queries the theme needs beyond a single entry: related posts and the Most Read list. */
import { getEmDashCollection, getEmDashEntry, getTerm, getBylineBySlug } from "emdash";
import mostReadSlugs from "./data/most-read.json";
import type { Entry, Term, Byline } from "./site";
import wpIds from "./data/wp-ids.json";
/** The se-search sidecar (Go: hybrid search, embedding-based related articles, Plausible "Most Read") answers on
 *  SE_SEARCH_URL (in the Bunny pod 127.0.0.1:8080). Without it — local development — related = newest posts of the
 *  same category and Most Read = the seeded slug list. The sidecar still keys legacy posts by their WordPress id. */
const SEARCH = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env?.SE_SEARCH_URL?.replace(/\/+$/, "") ?? "";
const slugToWpId: Record<string, string> = Object.fromEntries(Object.entries((wpIds as { posts: Record<string, string> }).posts).map(([id, slug]) => [slug, id]));
type Hit = { link?: string; title?: string };
const slugOfLink = (link?: string) => (link ?? "").replace(/^https?:\/\/[^/]+\//, "").replace(/\/$/, "").split("?")[0];
async function sidecar(path: string): Promise<Hit[] | null> {
	if (!SEARCH) return null;
	try { const r = await fetch(SEARCH + path, { signal: AbortSignal.timeout(1500) }); if (!r.ok) return null; const d = await r.json() as { hits?: Hit[]; results?: Hit[]; items?: Hit[] } | Hit[]; return Array.isArray(d) ? d : (d.hits ?? d.results ?? d.items ?? null); }
	catch { return null; }
}
async function entriesForSlugs(slugs: string[], n: number): Promise<Entry[]> {
	const out: Entry[] = [];
	for (const slug of slugs) { if (out.length >= n) break; const { entry } = await getEmDashEntry("posts", slug); if (entry) out.push(entry as unknown as Entry); }
	return out;
}
export async function relatedPosts(category: Term | undefined, excludeSlug: string, n: number): Promise<Entry[]> {
	const wp = slugToWpId[excludeSlug];
	const hits = wp ? await sidecar(`/related?id=${wp}&limit=${n}`) : null;
	if (hits?.length) { const e = await entriesForSlugs(hits.map((h) => slugOfLink(h.link)).filter((s) => s && s !== excludeSlug), n); if (e.length) return e; }
	if (!category) return [];
	const { entries } = await getEmDashCollection("posts", { where: { category: category.slug }, orderBy: { published_at: "desc" }, limit: n + 1 });
	return (entries as unknown as Entry[]).filter((e) => e.id !== excludeSlug).slice(0, n);
}
export async function mostRead(n: number): Promise<Entry[]> {
	const hits = await sidecar(`/popular?limit=${n}`);
	if (hits?.length) { const e = await entriesForSlugs(hits.map((h) => slugOfLink(h.link)).filter(Boolean), n); if (e.length) return e; }
	return entriesForSlugs(mostReadSlugs as string[], n);
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
