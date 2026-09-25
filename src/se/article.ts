import { escapeHtml } from "./format";
import type { Author } from "./data";
/** Markup of the SE hero byline (snippet 57 / GP element), one author link per byline. */
export function heroByline(bylines: Author[]): string {
	if (bylines.length <= 2) return `<div class="se-hero__byline se-hero__byline--inline">` + bylines.map((a) => `<a class="se-hero__author" href="${a.url}" rel="author">${a.avatarHtml}<span class="se-hero__name">${escapeHtml(a.name)}</span></a>`).join("") + `</div>`;
	// three or more authors: stacked avatars + "A, B and C"
	const inner = (a: Author) => { const m = a.avatarHtml.match(/<picture>[\s\S]*?<\/picture>/); return m ? m[0] : a.avatarHtml.replace(/<\/?span[^>]*>/g, ""); };
	const stack = bylines.map((a) => `<a class="se-avatar se-avatar--stack" href="${a.url}" tabindex="-1" aria-hidden="true">${inner(a)}</a>`).join("");
	const links = bylines.map((a) => `<a class="se-hero__name" href="${a.url}" rel="author">${escapeHtml(a.name)}</a>`);
	const names = links.length === 2 ? `${links[0]} <span class="se-hero__and">and</span> ${links[1]}` : `${links.slice(0, -1).join(", ")} <span class="se-hero__and">and</span> ${links[links.length - 1]}`;
	return `<div class="se-hero__byline se-hero__byline--stacked"><div class="se-hero__stack">${stack}</div><p class="se-hero__names">${names}</p></div>`;
}
/** Author profile box after the article (one per byline). */
export function authorBox(a: Author): string {
	const bio = a.bio ? (/^\s*<(div|p|ul|ol)\b/.test(a.bio) ? `${a.bio}\n` : `<p>${a.bio}</p>\n`) : "";   // WordPress wraps plain-text bios in <p>, block markup stays as is
	const avatar = (a as Author & { avatarBoxHtml?: string }).avatarBoxHtml ?? a.avatarHtml;   // author box carries the photo credit link
	return `<div class="se-author-profile-box se-author-profile"><h4 class="se-box-header">AUTHOR PROFILE</h4><div class="se-box-inner"><div class="se-author-avatar">${avatar}</div><div class="se-author-text"><h3 class="se-author-name-title"><a href="${a.url}">${escapeHtml(a.name)}</a></h3><div class="se-author-bio-text">${bio}</div></div></div></div>`;
}
