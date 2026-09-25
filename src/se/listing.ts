/** Listing pages (home, category, tag, author archives). Phase 1: the ordered post index and the rendered cards come from
 *  the archive fixtures (archive/posts.json, archive/cards/<id>.html); phase 2 swaps the index for an EmDash query and the
 *  cards for a template fed by entry data. Output markup is the GeneratePress archive template frozen from the live site. */
import fs from "node:fs";
import path from "node:path";
import { authors, initials } from "./data";
import { escapeHtml } from "./format";
import navTpl from "./partials/archive-nav-page2.html?raw";

const ROOT = process.cwd();
type IndexPost = { id: number; slug: string; date: string; categories: number[]; tags: number[]; coauthors: number[]; title: string };
let index: IndexPost[] | null = null;
let terms: { categories: { id: number; slug: string; name: string; description: string }[]; tags: { id: number; slug: string; name: string; description: string }[] } | null = null;
let coauthorMap: Record<string, { slug: string }[]> | null = null;
let userIds: Record<string, number> | null = null;
function load() {
	if (index) return;
	const posts = JSON.parse(fs.readFileSync(path.join(ROOT, "archive", "posts.json"), "utf8")) as Record<string, unknown>[];
	index = posts.map((p) => ({ id: p.id as number, slug: p.slug as string, date: p.date as string, categories: p.categories as number[], tags: p.tags as number[], coauthors: (p.coauthors as number[]) ?? [], title: (p.title as { rendered: string }).rendered }))
		.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
	terms = JSON.parse(fs.readFileSync(path.join(ROOT, "archive", "terms.json"), "utf8"));
	const cp = path.join(ROOT, "archive", "coauthors.json");
	coauthorMap = fs.existsSync(cp) ? JSON.parse(fs.readFileSync(cp, "utf8")) : {};
	userIds = {};
	for (const u of JSON.parse(fs.readFileSync(path.join(ROOT, "archive", "users.json"), "utf8")) as { id: number; slug: string }[]) userIds[u.slug] = u.id;
}
export const PER_PAGE = { home: 15, archive: 16 };

export function cardHtml(id: number): string {
	const f = path.join(ROOT, "archive", "cards", `${id}.html`);
	return fs.existsSync(f) ? fs.readFileSync(f, "utf8") : "";
}
/** The homepage "first post" template is the card with different element ids and a full-width column. */
export function firstPostHtml(id: number): string {
	const c = cardHtml(id);
	if (!c) return "";
	const pic = c.match(/<a href="[^"]+"><picture>[\s\S]*?<\/picture><\/a>/)?.[0] ?? "";
	const title = c.match(/<h2 class="gb-text gb-text-b1a124d0">([\s\S]*?)<\/h2>/)?.[1] ?? "";
	const author = c.match(/<div style="font-size: 18px;">[\s\S]*?<\/div>/)?.[0] ?? "";
	const dek = c.match(/<p class="gb-text gb-text-e4c86b08">([\s\S]*?)<\/p>/)?.[1] ?? "";
	const cls = c.match(/<article id="post-\d+" class="([^"]*)"/)?.[1].replace(/ grid-50$/, " grid-100 featured-column") ?? "";
	const picture = pic.replace("gb-media-f4b1d94b", "gb-media-dcd63dc2").replace(' decoding="async"', ' fetchpriority="high" decoding="async"');
	return `<article id="post-${id}" class="${cls}">
<div class="wp-block-columns is-layout-flex wp-container-core-columns-is-layout-8f761849 wp-block-columns-is-layout-flex">
<div class="wp-block-column is-layout-flow wp-block-column-is-layout-flow" style="flex-basis:100%"></div>
</div>



${picture}



<div style="height:20px" aria-hidden="true" class="wp-block-spacer"></div>



<h2 class="gb-text gb-text-dc4dac1e">${title}</h2>


${author}



<div style="height:10px" aria-hidden="true" class="wp-block-spacer"></div>



<p class="gb-text gb-text-7fb6cf2d">${dek}</p>
</article>`;
}

export type ListingKind = "home" | "category" | "tag" | "author";
export function listPosts(kind: ListingKind, slug: string | null, page: number): { ids: number[]; total: number; pages: number; term?: { id: number; slug: string; name: string; description: string }; authorId?: number } {
	load();
	let rows = index!; let term; let authorId;
	if (kind === "category" || kind === "tag") {
		term = (kind === "category" ? terms!.categories : terms!.tags).find((t) => t.slug === slug);
		if (!term) return { ids: [], total: 0, pages: 0 };
		const tid = term.id; rows = rows.filter((p) => (kind === "category" ? p.categories : p.tags).includes(tid));
	} else if (kind === "author") {
		authorId = userIds![slug!];
		rows = rows.filter((p) => { const cas = coauthorMap![String(p.id)]; return cas ? cas.some((a) => a.slug === slug) : false; });
	}
	const per = kind === "home" ? PER_PAGE.home : PER_PAGE.archive;
	const total = rows.length;
	// Homepage page 1 consumes 15 cards + 18 "more" items; paged views continue after those 33 with 15 per page.
	const start = kind === "home" ? (page === 1 ? 0 : 33 + (page - 2) * per) : (page - 1) * per;
	const pages = kind === "home" ? Math.max(1, 1 + Math.ceil(Math.max(0, total - 33) / per)) : Math.max(1, Math.ceil(total / per));
	return { ids: rows.slice(start, start + per).map((p) => p.id), total, pages, term, authorId };
}
/** "More opinion and analysis" list on the homepage: the 18 posts after the 15 cards. */
export function moreList(): string {
	load();
	const rows = index!.slice(PER_PAGE.home, PER_PAGE.home + 18);
	const items = rows.map((p) => {
		const cas = coauthorMap![String(p.id)] ?? [];
		const links = cas.map((a) => { const au = authors[a.slug]; const name = au?.name ?? a.slug; return `<a href="https://www.socialeurope.eu/author/${a.slug}" title="Posts by ${escapeHtml(name)}" class="author url fn" rel="author">${escapeHtml(name)}</a>`; });
		const by = links.length <= 1 ? links.join("") : links.slice(0, -1).join(", ") + " and " + links[links.length - 1];
		return `<li class="se-more__item"><a class="se-more__title" href="https://www.socialeurope.eu/${p.slug}">${p.title}</a><div class="se-more__by">${by}</div></li>`;
	});
	return `<section class="se-more" aria-labelledby="se-more-label"><div class="se-more__head"><h2 id="se-more-label" class="se-more__label">More opinion and analysis</h2></div><ul class="se-more__list">${items.join("")}</ul></section>`;
}
/** GP "Archive Navigation" element: Prev / Next links. */
export function archiveNav(baseUrl: string, page: number, pages: number): string {
	const prevHref = page <= 1 ? null : page === 2 ? baseUrl : `${baseUrl}/page/${page - 1}`;
	const nextHref = page >= pages ? null : `${baseUrl}/page/${page + 1}`;
	if (!prevHref && !nextHref) return "";
	const prev = navTpl.match(/<a class="gb-text-03a16113"[\s\S]*?<\/a>/)?.[0] ?? ""; const next = navTpl.match(/<a class="gb-text-dadbb7a0"[\s\S]*?<\/a>/)?.[0] ?? "";
	const p = prevHref ? prev.replace(/href="[^"]*"/, `href="${prevHref}"`) : ""; const n = nextHref ? next.replace(/href="[^"]*"/, `href="${nextHref}"`) : "";
	return `<div class="gb-element-1d81abc5">\n${p}${p && n ? "\n" : ""}${n}\n</div>`;
}
export function authorArchiveHeader(slug: string): string {
	const a = authors[slug]; if (!a) return "";
	const avatar = a.avatarHtml || `<span class="se-avatar se-avatar--initials">${initials(a.name)}</span>`;
	return `<header class="page-header se-author-profile-box se-author-profile se-author-archive" aria-label="Page"><p class="se-box-header">AUTHOR PROFILE</p><div class="se-box-inner"><div class="se-author-avatar">${avatar}</div><div class="se-author-text"><h1 class="page-title se-author-name-title">${escapeHtml(a.name)}</h1><div class="se-author-bio-text">${a.bio ? `<p>${a.bio}</p>\n` : ""}</div></div></div></header>`;
}
