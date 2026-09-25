import fs from "node:fs";
import path from "node:path";
export type PageFixture = { id: number; slug: string; title: string; template: string; bodyClass: string; introHtml: string | null; ctaHtml: string | null; featuredHtml: string | null; headTitle: string; articleClass: string; hasSidebar: boolean };
export function pageFixture(slug: string): PageFixture | null {
	const f = path.join(process.cwd(), "archive", "fixtures", `page-${slug}.json`);
	return fs.existsSync(f) ? (JSON.parse(fs.readFileSync(f, "utf8")) as PageFixture) : null;
}
