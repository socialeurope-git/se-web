/** Consistent SQLite snapshot from inside the app process (`VACUUM INTO`), for the backup uploader.
 *  The Magic Containers volume is a 9p mount: only this process may open data.db, so the sidecar asks the app for a
 *  snapshot (POST, bearer SE_OPS_TOKEN, reachable as localhost inside the pod) and then copies the file away.
 *  Snapshots land in <data dir>/backup/data-<UTC>.db; only the newest KEEP snapshots are kept (each is a full copy of the
 *  database, the volume is small). */
import type { APIRoute } from "astro";
import { sql } from "kysely";
import { getDb } from "emdash/runtime";
import fs from "node:fs";
import path from "node:path";

export const prerender = false;
const KEEP = 2;

export const POST: APIRoute = async ({ request }) => {
	const token = process.env.SE_OPS_TOKEN;
	if (!token) return new Response("Not found", { status: 404 });
	if (request.headers.get("authorization") !== `Bearer ${token}`) return new Response("Unauthorized", { status: 401 });
	const db = await getDb();
	const dbPath = process.env.DATABASE_PATH || "./data.db";
	const dir = path.join(path.dirname(dbPath), "backup");
	fs.mkdirSync(dir, { recursive: true });
	const file = path.join(dir, `data-${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}Z.db`);
	await sql.raw(`VACUUM INTO '${file.replace(/'/g, "''")}'`).execute(db as never);
	const all = fs.readdirSync(dir).filter((f) => f.endsWith(".db")).sort().reverse();   // newest first (UTC timestamp in the name)
	const kept = all.slice(0, KEEP);
	for (const f of all.slice(KEEP)) fs.unlinkSync(path.join(dir, f));
	return new Response(JSON.stringify({ file: path.basename(file), bytes: fs.statSync(file).size, kept }), { headers: { "Content-Type": "application/json" } });
};
