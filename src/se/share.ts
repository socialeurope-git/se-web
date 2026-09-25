import tpl from "./partials/ns-floating.tpl.html?raw";
/** Novashare floating share bar, server-rendered per post (markup frozen from the live site). */
export function floatingShare(title: string, url: string): string {
	const t = title.replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"');
	const enc = (s: string) => encodeURIComponent(s).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase());
	return tpl.replaceAll("{{TITLE_ENC}}", enc(t)).replaceAll("{{URL_ENC}}", enc(url)).replaceAll("{{URL}}", url).replaceAll("{{TITLE}}", t.replace(/&/g, "&amp;").replace(/</g, "&lt;"));
}
