// Sidebar advertisements -> EmDash widget area "sidebar" (content widgets in Portable Text, images = media items).
// Source: the live sidebar markup captured from WordPress (archive/sidebar-live.html, six GenerateBlocks ad widgets); converter = EmDash's own.
// Usage: node tools/ads_to_widgets.mjs [--dry]
import { htmlToPortableText } from "@emdash-cms/gutenberg-to-portable-text";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
const ROOT = fileURLToPath(new URL("..", import.meta.url)); const BASE = "http://127.0.0.1:4321";
const dry = process.argv.includes("--dry");
const html = fs.readFileSync(ROOT + "archive/sidebar-live.html", "utf8");
const imp = JSON.parse(fs.readFileSync(ROOT + "archive/media-import.json", "utf8"));
const media = Object.fromEntries(imp.imported.map((i) => [i.originalUrl, i]));
const SIZE = /-\d+x\d+(?=\.[a-z0-9]+$)/i;
const cookie = fs.readFileSync(ROOT + "archive/jar.txt", "utf8").split("\n").filter((l) => l && !l.startsWith("# ")).map((l) => l.replace(/^#HttpOnly_/, "").split("\t")).filter((p) => p.length >= 7).map((p) => `${p[5]}=${p[6]}`).join("; ");
async function api(method, path, body) {
	const r = await fetch(BASE + path, { method, headers: { Cookie: cookie, "X-EmDash-Request": "1", "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
	const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(`${method} ${path} ${r.status} ${JSON.stringify(j).slice(0, 300)}`); return j.data ?? j;
}
const ads = [];
for (const m of html.matchAll(/<aside id="(block-\d+)" class="[^"]*">([\s\S]*?)<\/aside>/g)) {
	let inner = m[2].replace(/<picture>[\s\S]*?(<img[^>]*>)[\s\S]*?<\/picture>/g, "$1");   // keep the <img>, drop ShortPixel <source>s
	inner = inner.replace(/^\s*<div class="wp-block-group"><div class="wp-block-group__inner-container[^"]*">/, "").replace(/<\/div><\/div>\s*$/, "");   // GenerateBlocks group wrapper
	const title = (inner.match(/<h3[^>]*>(.*?)<\/h3>/s)?.[1] ?? m[1]).replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").trim();   // the heading is the widget title
	inner = inner.replace(/<h3[\s\S]*?<\/h3>/, "");
	// WordPress buttons -> EmDash buttons block at the same position (the HTML converter only sees a link paragraph)
	const parts = inner.split(/(<div class="wp-block-buttons[\s\S]*?<\/div>\s*<\/div>)/);
	const convert = (h) => htmlToPortableText(h).filter((b) => !(b._type === "block" && (b.children ?? []).every((c) => !String(c.text ?? "").trim())));
	const norm = (t) => t.replace(/<[^>]+>/g, "").replace(/&[a-z#0-9]+;/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
	const centred = [...inner.matchAll(/<p class="[^"]*has-text-align-center[^"]*"[^>]*>([\s\S]*?)<\/p>/g)].map((x) => norm(x[1]));
	const blocks = [];
	for (const part of parts) {
		if (part.startsWith("<div class=\"wp-block-buttons")) {
			blocks.push({ _type: "buttons", _key: "btn-" + m[1] + "-" + blocks.length, layout: "horizontal", buttons: [...part.matchAll(/<a [^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g)].map((a, i) => ({ _type: "button", _key: `btn-${m[1]}-${blocks.length}-${i}`, text: a[2].replace(/<[^>]+>/g, "").trim(), url: a[1], style: "fill" })) });
		} else if (part.trim()) {
			for (const b of convert(part)) {
				// WordPress text alignment -> Portable Text block alignment
				if (b._type === "block" && centred.some((t) => t && norm((b.children ?? []).map((c) => c.text ?? "").join("")) === t)) b.textAlign = "center";
				blocks.push(b);
			}
		}
	}
	ads.push({ id: m[1], title, blocks });
}
console.log(ads.map((a) => `${a.id} ${a.title}: ${a.blocks.map((b) => b._type + (b.style ? ":" + b.style : "") + (b.listItem ? "/li" : "")).join(" ")}`).join("\n"));
if (dry) { fs.writeFileSync(ROOT + "archive/ads-pt.json", JSON.stringify(ads, null, 1)); console.log("dry run: archive/ads-pt.json"); process.exit(0); }
const areas = await api("GET", "/_emdash/api/widget-areas"); const list = areas.items ?? areas;
if (!list.some((a) => a.name === "sidebar")) await api("POST", "/_emdash/api/widget-areas", { name: "sidebar", label: "Sidebar advertisements", description: "Rotating advertisement widgets of the right sidebar (six slots)" });
const area = await api("GET", "/_emdash/api/widget-areas/sidebar"); const existing = area.widgets ?? [];
for (const w of existing) await api("DELETE", `/_emdash/api/widget-areas/sidebar/widgets/${w.id}`).catch((e) => console.warn(String(e).slice(0, 120)));
for (const a of ads) await api("POST", "/_emdash/api/widget-areas/sidebar/widgets", { type: "content", title: a.title, content: a.blocks });
console.log(`widget area "sidebar": ${ads.length} content widgets`);
