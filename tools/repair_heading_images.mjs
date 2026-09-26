#!/usr/bin/env node
// WordPress quirk: some posts wrap a figure inside a heading (<h2 class="wp-block-heading"><figure><picture>…</picture></figure></h2>).
// EmDash's importer keeps the heading text and drops the image. This restores those images as native image blocks,
// placed after the block whose text precedes the figure in the WordPress body. Reads archive/wxr-all.xml and
// archive/media-import.json; SE_BASE/SE_TOKEN as usual. --dry reports only.
import fs from "node:fs";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { parseFragment } from "parse5";
const ROOT = fileURLToPath(new URL("..", import.meta.url));
const BASE = (process.env.SE_BASE || "http://127.0.0.1:4321").replace(/\/$/, ""); const TOKEN = process.env.SE_TOKEN || "";
const dry = process.argv.includes("--dry");
const cookie = TOKEN ? "" : fs.readFileSync(ROOT + "archive/jar.txt", "utf8").split("\n").filter((l) => l && !l.startsWith("# ")).map((l) => l.replace(/^#HttpOnly_/, "").split("\t")).filter((p) => p.length >= 7).map((p) => `${p[5]}=${p[6]}`).join("; ");
const auth = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : { Cookie: cookie };
async function api(method, path, body) { const r = await fetch(BASE + path, { method, headers: { ...auth, "X-EmDash-Request": "1", "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined }); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(`${method} ${path} ${r.status} ${JSON.stringify(j).slice(0, 200)}`); return j.data ?? j; }
const key = () => "k" + crypto.randomBytes(5).toString("hex");
const imp = JSON.parse(fs.readFileSync(ROOT + "archive/media-import.json", "utf8")); const byUrl = new Map(imp.imported.map((i) => [i.originalUrl, i]));
const SIZE = /-\d+x\d+(?=\.[a-z0-9]+$)/i;
const xml = fs.readFileSync(ROOT + "archive/wxr-all.xml", "utf8");
const val = (it, tag) => { const m = it.match(new RegExp(`<${tag}>(?:<!\\[CDATA\\[)?([\\s\\S]*?)(?:\\]\\]>)?</${tag}>`)); return m ? m[1] : null; };
const text = (n) => n.nodeName === "#text" ? n.value : (n.childNodes || []).map(text).join("");
const find = (n, pred) => { if (n.tagName && pred(n)) return n; for (const c of n.childNodes || []) { const r = find(c, pred); if (r) return r; } return null; };
const attr = (n, a) => (n.attrs || []).find((x) => x.name === a)?.value ?? null;
let fixed = 0, inserted = 0;
for (const it of xml.matchAll(/<item>([\s\S]*?)<\/item>/g)) {
	const item = it[1]; if (!/<wp:post_type>(?:<!\[CDATA\[)?post/.test(item) || val(item, "wp:status") !== "publish") continue;
	const body = val(item, "content:encoded") || ""; if (!/<h[1-6][^>]*>\s*<figure/.test(body)) continue;
	const slug = val(item, "wp:post_name");
	// top-level elements of the body in order, with their plain text
	const frag = parseFragment(body.replace(/<!--[\s\S]*?-->/g, ""));
	const seq = frag.childNodes.filter((n) => n.tagName).map((n) => ({ n, tag: n.tagName, txt: text(n).replace(/\s+/g, " ").trim() }));
	const e = await api("GET", `/_emdash/api/content/posts/${slug}`); const entry = e.item ?? e; const content = entry.data.content;
	const btxt = (b) => b._type === "block" ? (b.children || []).map((c) => c.text || "").join("").replace(/\s+/g, " ").trim() : "";
	let changed = false;
	seq.forEach((s, idx) => {
		if (!/^h[1-6]$/.test(s.tag)) return; const img = find(s.n, (x) => x.tagName === "img"); if (!img) return;
		const src = (attr(img, "src") || "").split("?")[0]; const orig = src.replace(SIZE, "");
		const mi = byUrl.get(orig) || byUrl.get(src); if (!mi) { console.log(slug, "no media for", src); return; }
		const already = content.some((b) => b._type === "image" && b.asset?._ref === mi.mediaId); if (already) return;
		// anchor: the nearest preceding top-level element with text that exists as a block on staging
		let at = -1;
		for (let j = idx - 1; j >= 0 && at < 0; j--) { const t = seq[j].txt; if (t.length < 15) continue; const k = content.findIndex((b) => btxt(b) === t || (btxt(b) && t.startsWith(btxt(b).slice(0, 60)))); if (k >= 0) at = k + 1; }
		if (at < 0) { console.log(slug, "no anchor found, appending"); at = content.length; }
		const node = { _type: "image", _key: key(), asset: { _type: "reference", _ref: mi.mediaId, url: mi.newUrl }, alt: (attr(img, "alt") || "").trim() };
		content.splice(at, 0, node); inserted++; changed = true;
	});
	if (changed) {
		fixed++; console.log(`${slug}: images restored (${content.filter((b) => b._type === "image").length} image blocks now)`);
		if (!dry) { await api("PUT", `/_emdash/api/content/posts/${entry.id}`, { data: { content }, skipRevision: true }); await api("POST", `/_emdash/api/content/posts/${entry.id}/publish`, {}); }
	}
}
console.log(`${dry ? "[dry] " : ""}posts fixed ${fixed}, images inserted ${inserted}`);
