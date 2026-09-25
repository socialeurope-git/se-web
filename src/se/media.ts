/** Legacy WordPress upload URLs -> EmDash media (map produced by tools/rewrite_html_blocks.py after the media import).
 *  - the original file            -> /_emdash/api/media/file/<key>
 *  - a WordPress size variant     -> Astro's image endpoint with the same width/height/format (EmDash reads the source from storage)
 *  - a ShortPixel .webp/.avif twin -> the original, converted by the image endpoint */
import map from "./data/media-map.json";
const LIVE = "https://www.socialeurope.eu";
const SIZE = /-(\d+)x(\d+)(?=\.([a-z0-9]+)$)/i;
const exact = map.exact as Record<string, string>;
const alt = map.alt as Record<string, string>;
export function mediaUrl(url: string): string | null {
	const u = (url.startsWith("/") ? LIVE + url : url).split("?")[0].replace("https://socialeurope.eu", LIVE);
	if (exact[u]) return exact[u];
	const ext = (u.match(/\.([a-z0-9]+)$/i)?.[1] || "").toLowerCase();
	const m = u.match(SIZE);
	const base = u.replace(SIZE, "");
	const orig = exact[base] ?? alt[base];
	if (!orig) return null;
	const origExt = (orig.match(/\.([a-z0-9]+)$/i)?.[1] || "").toLowerCase();
	const p = new URLSearchParams({ href: orig });
	if (m) { p.set("w", m[1]); p.set("h", m[2]); }
	if (!m && (!ext || ext === origExt)) return orig;
	p.set("f", (ext || origExt) === "jpg" ? "jpeg" : ext || origExt); // explicit: the endpoint otherwise defaults to webp
	return `/_image?${p.toString()}`;
}
export function mediaRedirect(pathname: string): string | null { return mediaUrl(decodeURIComponent(pathname)); }
const UPLOAD = /https?:\/\/(?:www\.)?socialeurope\.eu\/wp-content\/uploads\/[^\s"'<>)]+/g;
/** Rewrite every upload URL inside HTML/XML to EmDash media, absolute on `origin`. */
export function localiseMedia(text: string, origin: string): string {
	if (!text.includes("/wp-content/uploads/")) return text;
	return text.replace(UPLOAD, (m) => { const n = mediaUrl(m); return n ? origin + n : m; });
}
