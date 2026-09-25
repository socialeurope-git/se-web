/** Data access for the SE theme. Phase 1: author profiles and per-post widgets come from files captured from the live site;
 *  later they come from EmDash bylines and the related/most-read services. Same output shape either way. */
import fs from "node:fs";
import path from "node:path";
import authorsJson from "./data/authors.json";

export type Author = { slug: string; name: string; bio: string; url: string; avatarHtml: string; avatarBoxHtml?: string; personId?: string | null; personDesc?: string | null };
export const authors: Record<string, Author> = authorsJson as Record<string, Author>;

export function initials(name: string): string {
	return name.split(/\s+/).filter(Boolean).map((w) => w[0]!.toUpperCase()).slice(0, 2).join("");
}
export function authorFor(slug: string, fallbackName: string): Author {
	return authors[slug] ?? { slug, name: fallbackName, bio: "", url: `https://www.socialeurope.eu/author/${slug}`, avatarHtml: `<span class="se-avatar se-avatar--initials">${initials(fallbackName)}</span>` };
}

export type Fixture = { id: number; slug: string; bylines: { slug: string; name: string }[]; heroBg: string | null; relInline: string | null; relBand: string | null; title: string; dek: string; bodyClass: string; articleClass: string; imageW?: number | null; imageH?: number | null; modified?: string | null; modifiedDay?: string | null; wordCount?: number | null; description?: string | null; ogDescription?: string | null; ldDescription?: string | null; ldPublished?: string | null; ldHeadline?: string | null; ldKeywords?: string | string[] | null; ogTitle?: string | null; seoAuthor?: { "@id"?: string; name: string; description?: string } | null; ldAuthors?: { name: string; url: string }[] | null };
const FIXTURE_DIR = path.join(process.cwd(), "archive", "fixtures");
let slugIndex: Map<string, number> | null = null;
function loadSlugIndex(): Map<string, number> {
	if (slugIndex) return slugIndex;
	slugIndex = new Map();
	const p = path.join(process.cwd(), "archive", "posts.json");
	if (fs.existsSync(p)) for (const post of JSON.parse(fs.readFileSync(p, "utf8"))) slugIndex.set(post.slug, post.id);
	return slugIndex;
}
export function fixtureForSlug(slug: string): Fixture | null {
	const id = loadSlugIndex().get(slug);
	if (!id) return null;
	const f = path.join(FIXTURE_DIR, `${id}.json`);
	return fs.existsSync(f) ? (JSON.parse(fs.readFileSync(f, "utf8")) as Fixture) : null;
}
