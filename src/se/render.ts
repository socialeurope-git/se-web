/**
 * Portable Text -> HTML renderer that reproduces WordPress block markup for Social Europe.
 * Goal: byte-compatible markup with what WordPress rendered (spike 1 froze the CSS against that markup).
 */
export type Span = { _type: "span"; text: string; marks?: string[] };
export type Block = {
	_type: string; _key?: string; style?: string; listItem?: string; level?: number;
	children?: Span[]; markDefs?: { _key: string; _type: string; href?: string; blank?: boolean }[];
	html?: string; asset?: { url?: string; _ref?: string }; alt?: string; caption?: string; url?: string;
};

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const attr = (s: string) => esc(s).replace(/"/g, "&quot;");

const MARK_TAGS: Record<string, [string, string]> = {
	strong: ["<strong>", "</strong>"], em: ["<em>", "</em>"], underline: ["<u>", "</u>"],
	code: ["<code>", "</code>"], superscript: ["<sup>", "</sup>"], subscript: ["<sub>", "</sub>"],
	"strike-through": ["<s>", "</s>"], strike: ["<s>", "</s>"], highlight: ["<mark>", "</mark>"],
};

function renderSpans(block: Block): string {
	const defs = new Map((block.markDefs ?? []).map((d) => [d._key, d]));
	return (block.children ?? []).map((c) => {
		let out = esc(c.text ?? "");
		for (const m of [...(c.marks ?? [])].reverse()) {
			const def = defs.get(m);
			if (def && def._type === "link" && def.href) {
				const extra = def.blank ? ` target="_blank" rel="noopener"` : "";
				out = `<a href="${attr(def.href)}"${extra}>${out}</a>`;
			} else if (MARK_TAGS[m]) out = MARK_TAGS[m][0] + out + MARK_TAGS[m][1];
		}
		return out;
	}).join("");
}

function renderImage(b: Block): string {
	const src = b.asset?.url ?? b.url ?? b.asset?._ref ?? "";
	const cap = b.caption ? `<figcaption class="wp-element-caption">${esc(b.caption)}</figcaption>` : "";
	return `<figure class="wp-block-image size-large"><img decoding="async" src="${attr(src)}" alt="${attr(b.alt ?? "")}">${cap}</figure>`;
}

/** Server-side equivalent of what the WordPress Interactivity runtime does on load: accordion panels start hidden. */
export function fixRawHtml(html: string): string {
	return html.replace(/<div([^>]*class="[^"]*wp-block-accordion-panel[^"]*"[^>]*)>/g, (m, a) => (/\shidden(=|\s|>)/.test(a) ? m : `<div${a} hidden="until-found">`));
}
/** Render a Portable Text array to WordPress-shaped HTML. */
export function renderBlocks(blocks: Block[]): string {
	const out: string[] = [];
	let i = 0;
	while (i < blocks.length) {
		const b = blocks[i];
		if (b._type === "htmlBlock" || b._type === "html") { out.push(fixRawHtml((b.html ?? "").trim())); i++; continue; }
		if (b._type === "image") { out.push(renderImage(b)); i++; continue; }
		if (b._type !== "block") { i++; continue; }
		if (b.listItem) {
			// gather consecutive list items into nested lists
			const items: Block[] = [];
			while (i < blocks.length && blocks[i]._type === "block" && blocks[i].listItem) items.push(blocks[i++]);
			out.push(renderList(items));
			continue;
		}
		if (b.style === "blockquote") {
			const ps: string[] = [];
			while (i < blocks.length && blocks[i]._type === "block" && blocks[i].style === "blockquote" && !blocks[i].listItem) ps.push(`<p>${renderSpans(blocks[i++])}</p>`);
			out.push(`<blockquote class="wp-block-quote">${ps.join("")}</blockquote>`);
			continue;
		}
		const inner = renderSpans(b);
		const st = b.style ?? "normal";
		if (/^h[1-6]$/.test(st)) out.push(`<${st} class="wp-block-heading">${inner}</${st}>`);
		else out.push(`<p class="wp-block-paragraph">${inner}</p>`);
		i++;
	}
	return out.join("\n");
}

function renderList(items: Block[]): string {
	// items carry level (1-based) and listItem "bullet"|"number"
	let html = ""; const stack: string[] = [];
	const tag = (b: Block) => (b.listItem === "number" ? "ol" : "ul");
	let prevLevel = 0;
	for (const b of items) {
		const lvl = b.level ?? 1;
		if (lvl > prevLevel) { for (let k = prevLevel; k < lvl; k++) { const t = tag(b); html += (k === 0 ? `<${t} class="wp-block-list">` : `<${t}>`); stack.push(t); } }
		else { for (let k = lvl; k < prevLevel; k++) html += `</li></${stack.pop()}>`; if (prevLevel >= lvl) html += "</li>"; }
		html += `<li>${renderSpans(b)}`; prevLevel = lvl;
	}
	for (let k = 0; k < prevLevel; k++) html += `</li></${stack.pop()}>`;
	return html;
}

/** Split rendered HTML into top-level elements (balanced tags), keeping text nodes. */
export function splitTopLevel(html: string): string[] {
	const out: string[] = []; let depth = 0; let buf = "";
	const VOID = new Set(["br", "img", "hr", "source", "input", "meta", "link", "wbr", "track", "embed"]);
	const re = /<!--[\s\S]*?-->|<(\/?)([a-zA-Z0-9]+)[^>]*?(\/?)>|[^<]+/g;
	let m: RegExpExecArray | null;
	while ((m = re.exec(html))) {
		const tok = m[0];
		if (tok.startsWith("<!--")) continue;
		if (tok.startsWith("<")) {
			const closing = m[1] === "/", tag = m[2].toLowerCase(), selfc = m[3] === "/";
			buf += tok;
			if (closing) depth--; else if (!(VOID.has(tag) || selfc)) depth++;
			if (depth <= 0) { depth = 0; if (buf.trim()) out.push(buf); buf = ""; }
		} else { buf += tok; if (depth <= 0 && buf.trim()) { out.push(buf); buf = ""; } }
	}
	if (buf.trim()) out.push(buf);
	return out;
}

/** Insert widget HTML after the Nth top-level <p>. Rules measured on the live site (spike 1):
 *  related inline after paragraph 5; newsletter box after paragraph 10 or before the last paragraph on short posts. */
export function injectAfterParagraph(elements: string[], n: number, widget: string): string[] {
	// WordPress semantics: insert directly after the n-th paragraph; if the post has fewer paragraphs, append at the very end
	// (after anything already appended). This reproduces the live order for short posts.
	let count = 0;
	for (let i = 0; i < elements.length; i++) {
		if (/^\s*<p[\s>]/.test(elements[i])) { count++; if (count === n) return [...elements.slice(0, i + 1), widget, ...elements.slice(i + 1)]; }
	}
	return [...elements, widget];
}
export function paragraphCount(elements: string[]): number { return elements.filter((e) => /^\s*<p[\s>]/.test(e)).length; }
