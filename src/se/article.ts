import { escapeHtml } from "./format";
import type { Author } from "./data";
/** Markup of the SE hero byline (snippet 57 / GP element), one author link per byline. */
export function heroByline(bylines: Author[]): string {
	return `<div class="se-hero__byline se-hero__byline--inline">` + bylines.map((a) => `<a class="se-hero__author" href="${a.url}" rel="author">${a.avatarHtml}<span class="se-hero__name">${escapeHtml(a.name)}</span></a>`).join("") + `</div>`;
}
/** Author profile box after the article (one per byline). */
export function authorBox(a: Author): string {
	const bio = a.bio ? `<p>${a.bio}</p>\n` : "";
	return `<div class="se-author-profile-box se-author-profile"><h4 class="se-box-header">AUTHOR PROFILE</h4><div class="se-box-inner"><div class="se-author-avatar">${a.avatarHtml}</div><div class="se-author-text"><h3 class="se-author-name-title"><a href="${a.url}">${escapeHtml(a.name)}</a></h3><div class="se-author-bio-text">${bio}</div></div></div></div>`;
}
