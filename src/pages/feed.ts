import type { APIRoute } from "astro";
import { buildFeed, rss } from "../se/feed";
export const GET: APIRoute = async () => rss(await buildFeed({ selfHref: "https://www.socialeurope.eu/feed" }));
