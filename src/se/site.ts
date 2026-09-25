/** Site constants and small helpers over EmDash entry data (no fixtures). */
export const SITE = "https://www.socialeurope.eu";
export const SITE_TITLE = "Social Europe";
export const SITE_DESCRIPTION = "Social Europe is an award-winning digital publisher offering freely accessible expert analysis and informed debate on political, economic and social issues.";
export type Byline = { id: string; slug: string; displayName: string; bio: string | null; avatarMediaId: string | null; avatarStorageKey?: string | null; avatarAlt?: string | null; websiteUrl: string | null; translationGroup?: string | null; customFields?: Record<string, unknown> };
export type Credit = { byline: Byline; sortOrder: number; roleLabel: string | null };
export type Term = { id: string; slug: string; label: string; name?: string; description?: string | null; count?: number };
export type ImageValue = { id: string; src?: string; alt?: string; width?: number; height?: number };
export type Entry = { id: string; data: { id: string; slug: string; title: string; excerpt?: string; content?: unknown[]; featured_image?: ImageValue | null; publishedAt: Date | null; updatedAt: Date; bylines?: Credit[]; terms?: Record<string, Term[]>; seo?: unknown; [k: string]: unknown }; edit?: Record<string, Record<string, string>> };

export const postUrl = (slug: string) => `${SITE}/${slug}`;
export const authorUrl = (slug: string) => `${SITE}/author/${slug}`;
export const categoryUrl = (slug: string) => `${SITE}/category/${slug}`;
export const absolute = (src?: string | null) => (src ? (src.startsWith("/") ? SITE + src : src) : null);
export const credits = (e: Entry): Byline[] => (e.data.bylines ?? []).map((c) => c.byline);
export const avatarSrc = (b: Byline): string | null => (b.avatarStorageKey ? `/_emdash/api/media/file/${b.avatarStorageKey}` : null);
export function initials(name: string): string { return name.split(/\s+/).filter(Boolean).map((w) => w[0]!.toUpperCase()).slice(0, 2).join(""); }
/** "A", "A and B", "A, B and C" — for plain-text contexts (feed, cards' by-lines are built with links separately). */
export function joinNames(names: string[]): string { return names.length <= 1 ? names.join("") : names.slice(0, -1).join(", ") + " and " + names[names.length - 1]; }
export const categoryOf = (e: Entry): Term | undefined => e.data.terms?.category?.[0];
export const excerpt = (e: Entry): string => (e.data.excerpt as string) ?? "";
export const escapeHtml = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
