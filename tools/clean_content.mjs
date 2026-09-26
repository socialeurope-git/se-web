#!/usr/bin/env node
// Clean start after the WordPress import: turn the raw-HTML residue (`htmlBlock`) of every post and page into native
// EmDash Portable Text (headings, paragraphs, quotes, lists, images, tables) with EmDash's own converter, keep only a
// handful of site-specific elements as tidy HTML (Key Insights as <details>, sponsor notes, content boxes, captions
// with links), and drop WordPress junk (spacers, sharing widgets, data-wp-* interactivity, ShortPixel <picture>,
// wp-* classes, non-breaking spaces, absolute self-links, h1 inside the body).
//   SE_BASE / SE_TOKEN as for the other tools.   --dry: report only (archive/clean-preview.json)   --only=<slug>
import fs from "node:fs";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { htmlToPortableText, parseInlineContent } from "@emdash-cms/gutenberg-to-portable-text";
import { parseFragment, serialize, serializeOuter } from "parse5";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const BASE = (process.env.SE_BASE || "http://127.0.0.1:4321").replace(/\/$/, "");
const TOKEN = process.env.SE_TOKEN || "";
const dry = process.argv.includes("--dry");
const only = (process.argv.find((a) => a.startsWith("--only=")) || "").slice(7);
const cookie = TOKEN ? "" : fs.readFileSync(ROOT + "archive/jar.txt", "utf8").split("\n").filter((l) => l && !l.startsWith("# ")).map((l) => l.replace(/^#HttpOnly_/, "").split("\t")).filter((p) => p.length >= 7).map((p) => `${p[5]}=${p[6]}`).join("; ");
const auth = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : { Cookie: cookie };
async function api(method, path, body, raw) {
	const r = await fetch(BASE + path, { method, headers: { ...auth, "X-EmDash-Request": "1", ...(raw ? {} : { "Content-Type": "application/json" }) }, body: raw ? body : body ? JSON.stringify(body) : undefined });
	const j = await r.json().catch(() => ({}));
	if (!r.ok) throw new Error(`${method} ${path} ${r.status} ${JSON.stringify(j).slice(0, 300)}`);
	return j.data ?? j;
}
async function listAll(path, keyName = "items") {
	const out = []; let cursor;
	for (;;) {
		const d = await api("GET", `${path}${path.includes("?") ? "&" : "?"}limit=100${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`);
		out.push(...(d[keyName] ?? [])); cursor = d.nextCursor; if (!cursor) break;
	}
	return out;
}
const key = () => "k" + crypto.randomBytes(5).toString("hex");
const stats = {}; const bump = (k, n = 1) => { stats[k] = (stats[k] ?? 0) + n; };
const preview = {}; const sample = (kind, before, after) => { (preview[kind] ??= []); if (preview[kind].length < 3) preview[kind].push({ before: before.slice(0, 600), after }); };

// ---------- media ----------
const testFile = (process.argv.find((a) => a.startsWith("--test-html=")) || "").slice(12);   // offline check of one HTML block (no API)
const media = testFile ? [] : await listAll("/_emdash/api/media");
const mediaByKey = new Map(media.map((m) => [m.storageKey, m]));
const MEDIA_RE = /\/_emdash\/api\/media\/file\/([A-Za-z0-9]+\.[a-z0-9]+)/;
function mediaFromSrc(src) {
	if (!src) return null;
	let s = src;
	try { if (s.startsWith("/_image?")) s = new URL(s, "http://x").searchParams.get("href") || ""; } catch { /* keep */ }
	try { s = decodeURIComponent(s); } catch { /* keep */ }
	const m = s.match(MEDIA_RE);
	return m ? mediaByKey.get(m[1]) ?? null : null;
}
const externalCache = new Map();
async function importExternal(url) {
	if (externalCache.has(url)) return externalCache.get(url);
	let item = null;
	try {
		const r = await fetch(url, { signal: AbortSignal.timeout(20000), headers: { "User-Agent": "Mozilla/5.0 (Social Europe import)" } });
		const ct = r.headers.get("content-type") || "";
		if (r.ok && ct.startsWith("image/")) {
			const buf = Buffer.from(await r.arrayBuffer());
			const name = decodeURIComponent(new URL(url).pathname.split("/").pop() || "image").replace(/[^\w.\-]+/g, "-");
			const fd = new FormData(); fd.append("file", new Blob([buf], { type: ct.split(";")[0] }), name);
			if (!dry) { const d = await api("POST", "/_emdash/api/media", fd, true); item = d.item ?? d; mediaByKey.set(item.storageKey, item); }
			else item = { id: "DRY", storageKey: "dry", url: url, width: null, height: null, filename: name };
			bump("external image imported");
		} else bump("external image not importable");
	} catch { bump("external image not importable"); }
	externalCache.set(url, item); return item;
}

// ---------- parse5 helpers ----------
const isEl = (n) => n && n.tagName;
const attr = (n, name) => (n.attrs || []).find((a) => a.name === name)?.value ?? null;
const cls = (n) => (attr(n, "class") || "").split(/\s+/).filter(Boolean);
const hasCls = (n, c) => cls(n).includes(c);
const children = (n) => (n.childNodes || []).filter((c) => isEl(c) || (c.nodeName === "#text" && c.value.trim()));
function find(n, pred) { if (isEl(n) && pred(n)) return n; for (const c of n.childNodes || []) { const r = find(c, pred); if (r) return r; } return null; }
function findAll(n, pred, out = []) { if (isEl(n) && pred(n)) out.push(n); for (const c of n.childNodes || []) findAll(c, pred, out); return out; }
const inner = (n) => serialize(n);
const outer = (n) => serializeOuter(n);
const textOf = (n) => (n.nodeName === "#text" ? n.value : (n.childNodes || []).map(textOf).join(""));
const alignOf = (n) => { const c = cls(n); return c.includes("has-text-align-center") ? "center" : c.includes("has-text-align-right") ? "right" : c.includes("has-text-align-justify") ? "justify" : null; };

// ---------- generic tidy of HTML that stays HTML ----------
const LIVE_LINK = /https?:\/\/(?:www\.)?socialeurope\.eu(\/[^"'\s<>]*)?/g;
const KEEP_CLASS = /^(content-box-|se-|aligncenter$|alignwide$|alignfull$)/;
function tidyHtml(html) {
	let h = html;
	h = h.replace(/<!--[\s\S]*?-->/g, "");
	h = h.replace(/<picture>[\s\S]*?(<img[^>]*>)[\s\S]*?<\/picture>/g, "$1");
	h = h.replace(/\s(?:srcset|sizes|decoding|fetchpriority|loading|data-[\w-]+|aria-hidden|role|style)="[^"]*"/g, "");
	h = h.replace(/\sclass="([^"]*)"/g, (_m, c) => { const keep = c.split(/\s+/).filter((x) => KEEP_CLASS.test(x)); return keep.length ? ` class="${keep.join(" ")}"` : ""; });
	h = h.replace(/<span lang="[^"]*">([\s\S]*?)<\/span>/g, "$1").replace(/<span>([\s\S]*?)<\/span>/g, "$1");
	h = h.replace(/&nbsp;| /g, " ");
	h = h.replace(/(href|src)="(https?:\/\/(?:www\.)?socialeurope\.eu)(\/[^"]*)?"/g, (_m, a, _h, p) => `${a}="${p || "/"}"`);
	h = h.replace(/<img([^>]*)src="(\/_image\?[^"]*)"/g, (_m, pre, src) => { const mi = mediaFromSrc(src); return mi ? `<img${pre}src="${mi.url}"` : `<img${pre}src="${src}"`; });
	h = h.replace(/\s+>/g, ">").replace(/\s+/g, " ").trim();
	return h;
}
const htmlBlock = (html) => (html.trim() ? { _type: "htmlBlock", _key: key(), html } : null);

// ---------- native conversions ----------
function nativeBlocks(html, textAlign) {
	const out = [];
	for (const b of htmlToPortableText(html)) {
		if (b._type === "block") {
			b.children = (b.children ?? []).map((c) => ({ ...c, text: (c.text ?? "").replace(/ /g, " ") }));
			polishSpans(b);
			if (!b.listItem && b.children.every((c) => !c.text.trim())) { bump("empty block dropped"); continue; }
			if (b.style === "h1") b.style = "h2";
			if (textAlign && textAlign !== "left") b.textAlign = textAlign;
			for (const md of b.markDefs ?? []) if (md._type === "link" && md.href) md.href = relLink(md.href);
			dropJunkLinks(b);
		}
		out.push(b);
	}
	return out;
}
const JUNK_HREF = /^\s*(?:about:blank|file:|c:|javascript:|#?\s*$|http:\/\/(?:&lt;|<)!--)/i;
function dropJunkLinks(b) {
	const junk = new Set((b.markDefs ?? []).filter((md) => md._type === "link" && JUNK_HREF.test(md.href ?? "")).map((md) => md._key));
	if (!junk.size) return;
	b.markDefs = (b.markDefs ?? []).filter((md) => !junk.has(md._key));
	b.children = (b.children ?? []).map((c) => ({ ...c, marks: (c.marks ?? []).filter((m) => !junk.has(m)) }));
	bump("junk link dropped");
}
function relLink(href) { const m = href.match(/^https?:\/\/(?:www\.)?socialeurope\.eu(\/.*)?$/); return m ? (m[1] || "/") : href; }

const IMG_HOLDER = (n) => n.tagName === "figure" || n.tagName === "picture" || n.tagName === "img" || (n.tagName === "a" && find(n, (x) => x.tagName === "img"));
async function imageBlocks(el, opts = {}) {
	// every <img> inside el becomes an image block; a figcaption becomes the caption (plain text) unless it has links.
	// Text that shares the element with the image (<p><picture>…</picture> Source: …</p>, <h6><figure>…</figure>Caption</h6>)
	// is kept as paragraphs in source order.
	const imgs = findAll(el, (n) => n.tagName === "img");
	if (!imgs.length) return [htmlBlock(tidyHtml(outer(el)))].filter(Boolean);
	if (el.tagName !== "figure" && el.tagName !== "picture" && el.tagName !== "img" && !(el.tagName === "a")) {
		const kids = el.childNodes || []; const holders = kids.filter(IMG_HOLDER);
		if (holders.length && kids.some((k) => !IMG_HOLDER(k) && (k.tagName ? textOf(k).trim() : (k.value || "").trim()))) {
			const out = []; let buf = "";
			const flush = () => { if (buf.trim()) out.push(...nativeBlocks(`<p>${buf}</p>`, opts.alignment ?? alignOf(el))); buf = ""; };
			for (const k of kids) { if (IMG_HOLDER(k)) { flush(); out.push(...(await imageBlocks(k, opts))); } else buf += k.tagName ? outer(k) : (k.value || ""); }
			flush(); bump("image with text in the same element split"); return out;
		}
	}
	const cap = find(el, (n) => n.tagName === "figcaption");
	const capHtml = cap ? inner(cap).trim() : "";
	const link = opts.link ?? (() => { const a = find(el, (n) => n.tagName === "a" && find(n, (x) => x.tagName === "img")); return a ? attr(a, "href") : null; })();
	const out = [];
	for (const img of imgs) {
		const src = attr(img, "src") || "";
		let mi = mediaFromSrc(src);
		if (!mi && /^https?:\/\//.test(src) && !/socialeurope\.eu/.test(src)) mi = await importExternal(src);
		if (!mi) { bump("image kept as html (no media)"); out.push(htmlBlock(tidyHtml(outer(el)))); return out.filter(Boolean); }
		if (capHtml && /<a\s/i.test(capHtml)) {
			bump("figure kept as html (caption with links)");
			const sw = (attr(img, "style") || "").match(/width:\s*(\d+)px/);
			out.push(htmlBlock(`<figure class="se-figure${opts.alignment === "center" ? " aligncenter" : ""}"><img src="${mi.url}" alt="${(attr(img, "alt") || "").replace(/"/g, "&quot;")}"${mi.width ? ` width="${mi.width}" height="${mi.height}"` : ""}${sw ? ` style="width:${sw[1]}px;height:auto"` : ""} loading="lazy"><figcaption>${tidyHtml(capHtml)}</figcaption></figure>`));
			return out.filter(Boolean);
		}
		const node = { _type: "image", _key: key(), asset: { _type: "reference", _ref: mi.id, url: mi.url }, alt: (attr(img, "alt") || "").replace(/ /g, " ").trim() };
		if (mi.width && mi.height) { node.width = mi.width; node.height = mi.height; }
		// the author resized the image in the editor (WordPress "is-resized": style="width:760px"): keep that display width
		const sw = (attr(img, "style") || "").match(/width:\s*(\d+)px/) || (attr(el, "style") || "").match(/width:\s*(\d+)px/);
		if (sw && mi.width && mi.height) { node.displayWidth = parseInt(sw[1], 10); node.displayHeight = Math.round(node.displayWidth * mi.height / mi.width); bump("display width kept"); }
		if (mi.blurhash) node.blurhash = mi.blurhash;
		if (mi.dominantColor) node.dominantColor = mi.dominantColor;
		if (capHtml) node.caption = textOf(parseFragment(capHtml.replace(/<br\s*\/?>/gi, " "))).replace(/\s+/g, " ").replace(/\u00a0/g, " ").trim();
		const has = (c) => hasCls(el, c) || !!find(el, (n) => hasCls(n, c));
		const al = opts.alignment ?? (has("aligncenter") ? "center" : has("alignleft") ? "left" : has("alignright") ? "right" : has("alignwide") ? "wide" : has("alignfull") ? "full" : null);
		if (al) node.alignment = al;
		if (link) node.link = relLink(link);
		out.push(node); bump("image block");
	}
	return out;
}
function tableBlock(tableEl) {
	const trs = findAll(tableEl, (n) => n.tagName === "tr");
	const rows = trs.map((tr, ri) => {
		const cellEls = children(tr).filter((c) => c.tagName === "td" || c.tagName === "th");
		const allStrong = ri === 0 && cellEls.every((c) => { const t = textOf(c).trim(); return !t || (children(c).length === 1 && children(c)[0].tagName === "strong" && textOf(children(c)[0]).trim() === t); });
		return { _key: key(), cells: cellEls.map((c) => {
			let h = inner(c).replace(/&nbsp;| /g, " ").trim();
			if (allStrong) h = h.replace(/^<strong>([\s\S]*)<\/strong>$/, "$1");
			const { children: ch, markDefs } = parseInlineContent(h, key);
			const cell = { _key: key(), content: ch.length ? ch : [{ _type: "span", _key: key(), text: "" }] };
			if (markDefs?.length) cell.markDefs = markDefs;
			if (c.tagName === "th" || allStrong) cell.isHeader = true;
			const cs = parseInt(attr(c, "colspan") || "1", 10), rs = parseInt(attr(c, "rowspan") || "1", 10);
			if (cs > 1) cell.colspan = cs; if (rs > 1) cell.rowspan = rs;
			return cell;
		}) };
	}).filter((r) => r.cells.length);
	bump("table block");
	return [{ _type: "table", _key: key(), rows }];
}
function embedHtml(el) {
	const iframe = find(el, (n) => n.tagName === "iframe");
	if (!iframe) return [htmlBlock(tidyHtml(outer(el)))].filter(Boolean);
	const src = (attr(iframe, "src") || "").replace("https://www.youtube.com/embed/", "https://www.youtube-nocookie.com/embed/");
	const title = attr(iframe, "title") || "Embedded content";
	bump("embed kept as html");
	return [htmlBlock(`<figure class="se-embed"><iframe src="${src}" title="${title.replace(/"/g, "&quot;")}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></figure>`)];
}
function detailsHtml(accordionEl) {
	const items = findAll(accordionEl, (n) => hasCls(n, "wp-block-accordion-item"));
	const out = [];
	for (const it of items) {
		const t = find(it, (n) => hasCls(n, "wp-block-accordion-heading__toggle-title"));
		const panel = find(it, (n) => hasCls(n, "wp-block-accordion-panel"));
		const title = (t ? textOf(t) : "Details").trim();
		const open = /"openByDefault"\s*:\s*true/.test((attr(it, "data-wp-context") || "").replace(/&quot;/g, '"'));
		out.push(htmlBlock(`<details class="se-key-insights"${open ? " open" : ""}><summary>${title}</summary><div class="se-key-insights__body">${tidyHtml(panel ? inner(panel) : "")}</div></details>`));
		bump("key insights -> details");
	}
	return out.filter(Boolean);
}
const SPONSOR_STYLE = /background-color:\s*#eff7fb/i;

async function convertRoot(n, ctx = {}) {
	if (!isEl(n)) { const t = n.value?.trim(); return t ? nativeBlocks(`<p>${t}</p>`, ctx.align) : []; }
	const tag = n.tagName, c = cls(n);
	const hasImg = !!find(n, (x) => x.tagName === "img");
	if (/^h[1-6]$/.test(tag)) {
		if (c.some((x) => x.startsWith("content-box-"))) { bump("content box kept"); return [htmlBlock(tidyHtml(outer(n)))].filter(Boolean); }
		return hasImg ? imageBlocks(n, { alignment: alignOf(n) ?? ctx.align }) : nativeBlocks(outer(n), alignOf(n) ?? ctx.align);
	}
	if (tag === "p") return hasImg ? imageBlocks(n, { alignment: alignOf(n) ?? ctx.align }) : nativeBlocks(outer(n), alignOf(n) ?? ctx.align);
	if (tag === "blockquote") {
		// a <cite> after the quote paragraph is its own line on the live site: it becomes a second quote paragraph
		const ps = children(n).filter((c) => c.tagName === "p" || c.tagName === "cite");
		const part = (c) => (c.tagName === "cite" ? `<p>${outer(c).replace(/^<cite[^>]*>/, "").replace(/<\/cite>$/, "")}</p>` : c.tagName ? outer(c) : `<p>${c.value}</p>`);
		if (ps.length > 1) { const out = []; for (const c of children(n)) out.push(...nativeBlocks(`<blockquote>${part(c)}</blockquote>`, alignOf(n) ?? ctx.align)); bump("multi-paragraph quote split"); return out; }
		return nativeBlocks(outer(n), alignOf(n) ?? ctx.align);
	}
	if (tag === "ul" || tag === "ol") {
		if (c.includes("wp-block-outermost-social-sharing")) { bump("junk dropped"); return []; }
		return nativeBlocks(outer(n), null);
	}
	if (tag === "figure" || tag === "picture" || tag === "img") {
		if (c.includes("wp-block-table") || find(n, (x) => x.tagName === "table")) {
			const cap = find(n, (x) => x.tagName === "figcaption");
			if (cap && textOf(cap).trim()) { bump("table kept as html (caption)"); return [htmlBlock(`<figure class="se-table"><table>${tidyHtml(inner(find(n, (x) => x.tagName === "table")))}</table><figcaption>${tidyHtml(inner(cap))}</figcaption></figure>`)]; }
			return tableBlock(find(n, (x) => x.tagName === "table"));
		}
		if (c.includes("wp-block-embed") || find(n, (x) => x.tagName === "iframe")) return embedHtml(n);
		return imageBlocks(n, { alignment: ctx.align });
	}
	if (tag === "table") return tableBlock(n);
	if (tag === "iframe") return embedHtml(n);
	if (tag === "a" && hasImg) return imageBlocks(n, { link: attr(n, "href"), alignment: ctx.align });
	if (tag === "center") { const out = []; for (const ch of children(n)) out.push(...(await convertRoot(ch, { align: "center" }))); return out; }
	if (tag === "section" || tag === "article" || tag === "main") { const out = []; for (const ch of children(n)) out.push(...(await convertRoot(ch, ctx))); return out; }
	if (tag === "div") {
		if (c.includes("wp-block-spacer")) { bump("junk dropped"); return []; }
		if (c.includes("insideArticleShare")) { const out = []; for (const ch of children(n)) out.push(...(await convertRoot(ch, ctx))); return out; }
		if (c.includes("wp-block-accordion")) return detailsHtml(n);
		if (c.includes("wp-block-image")) return imageBlocks(n, { alignment: ctx.align });
		if (c.some((x) => x.startsWith("content-box-"))) { bump("content box kept"); return [htmlBlock(tidyHtml(outer(n)))].filter(Boolean); }
		if (SPONSOR_STYLE.test(attr(n, "style") || "")) { bump("sponsor note"); return [htmlBlock(`<div class="se-sponsor-note">${tidyHtml(inner(n))}</div>`)]; }
		if (c.includes("wp-block-table")) return tableBlock(find(n, (x) => x.tagName === "table"));
		if (c.includes("wp-block-embed")) return embedHtml(n);
		// wrappers (post_content, article-body, grid columns, plain div): unwrap
		const out = []; for (const ch of children(n)) out.push(...(await convertRoot(ch, ctx))); bump("wrapper unwrapped"); return out;
	}
	if (tag === "br" || tag === "hr") return [];
	// inline element at the top level (strong, em, a, span, text): a paragraph
	if (["strong", "em", "a", "span", "b", "i", "u", "sup", "sub", "small"].includes(tag)) return nativeBlocks(`<p>${outer(n)}</p>`, ctx.align);
	bump("html kept: " + tag);
	return [htmlBlock(tidyHtml(outer(n)))].filter(Boolean);
}

async function convertHtmlBlock(html) {
	// HTML whitespace: raw line breaks are spaces (only <br> is a line break, which the converter turns into "\n")
	const frag = parseFragment(html.replace(/<pre[\s\S]*?<\/pre>/g, (m) => m).replace(/[ \t]*\r?\n[ \t]*/g, " "));
	const out = [];
	for (const n of frag.childNodes) { if (n.nodeName === "#text" && !n.value.trim()) continue; out.push(...(await convertRoot(n))); }
	return out;
}
function polishSpans(b) {
	// source errors that survive a faithful conversion: runs of spaces (nbsp + space), and a word glued to the next
	// capitalised word across a formatting boundary ("<em>Man’s</em><em>Soul</em>") — never after an elided article (l’Union)
	const ch = b.children ?? [];
	for (const c of ch) c.text = (c.text ?? "").replace(/ {2,}/g, " ");
	for (let i = 1; i < ch.length; i++) {
		if ((ch[i - 1].text ?? "").endsWith(" ") && (ch[i].text ?? "").startsWith(" ")) ch[i].text = ch[i].text.replace(/^ +/, "");   // double space across a span boundary
		const a = ch[i - 1].text ?? "", c = ch[i].text ?? "";
		if (a && c && /[a-z]$|’s$|'s$/.test(a) && /^[A-Z][a-z]/.test(c) && !(ch[i].marks ?? []).includes("superscript")) { ch[i - 1].text = a + " "; bump("glued words separated"); }
	}
}
function cleanNative(b) {
	if (b._type !== "block") return b;
	b.children = (b.children ?? []).map((c) => ({ ...c, text: (c.text ?? "").replace(/ /g, " ") }));
	polishSpans(b);
	if (b.style === "h1") { b.style = "h2"; bump("h1 -> h2"); }
	for (const md of b.markDefs ?? []) if (md._type === "link" && md.href) { const r = relLink(md.href); if (r !== md.href) { md.href = r; bump("self-link relativised"); } }
	dropJunkLinks(b);
	return b;
}
const alts = JSON.parse(fs.readFileSync(ROOT + "archive/alts.json", "utf8"));
if (testFile) { const blocks = await convertHtmlBlock(fs.readFileSync(testFile, "utf8")); console.log(JSON.stringify(blocks, null, 1)); console.log(JSON.stringify(stats)); process.exit(0); }

async function cleanEntry(coll, e) {
	const before = JSON.stringify(e.data);
	const content = e.data.content ?? [];
	const out = [];
	for (const b of content) {
		if (b._type === "htmlBlock") { const conv = await convertHtmlBlock(b.html ?? ""); sample(conv.map((x) => x._type + (x.style ? ":" + x.style : "")).join("+") || "dropped", b.html, conv); out.push(...conv); bump("htmlBlocks processed"); }
		else if (b._type === "block") { const cb = cleanNative(b); if (!cb.listItem && cb.children.every((c) => !c.text.trim())) { bump("empty block dropped"); continue; } out.push(cb); }
		else out.push(b);
	}
	e.data.content = out;
	const fi = e.data.featured_image;
	if (fi && fi.src && !(fi.alt || "").trim()) { const a = alts.featured?.[e.slug]; if (a) { fi.alt = a; bump("featured alt set"); } }
	if (JSON.stringify(e.data) === before) return false;
	if (!dry) {
		await api("PUT", `/_emdash/api/content/${coll}/${e.id}`, { data: { content: e.data.content, ...(fi ? { featured_image: fi } : {}) }, skipRevision: true });
		await api("POST", `/_emdash/api/content/${coll}/${e.id}/publish`, {});
	}
	return true;
}

let changed = 0, total = 0;
for (const coll of ["posts", "pages"]) {
	const entries = await listAll(`/_emdash/api/content/${coll}`);
	for (const e of entries) {
		if (only && e.slug !== only) continue;
		total++;
		try { if (await cleanEntry(coll, e)) changed++; } catch (err) { bump("ERROR"); console.error(coll, e.slug, String(err).slice(0, 200)); }
	}
}
console.log(`${dry ? "[dry] " : ""}entries ${total}, changed ${changed}`);
console.log(JSON.stringify(stats, null, 1));
if (dry) { fs.writeFileSync(ROOT + "archive/clean-preview.json", JSON.stringify(preview, null, 1)); console.log("samples: archive/clean-preview.json"); }
