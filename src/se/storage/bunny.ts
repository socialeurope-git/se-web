/**
 * EmDash storage adapter for Bunny Storage (https://docs.bunny.net/reference/storage-api).
 *
 * Objects live under `<prefix>/<key>` in the zone, so EmDash media (flat ULID keys) sits next to the
 * legacy WordPress tree (`wp-content/uploads/...`) that tools/upload_media.py copied into the same zone.
 * Public URLs go through the pull zone, which serves both prefixes from the storage zone (edge rule OriginStorage).
 *
 * Config (serialisable, from astro.config.mjs):  { zone, host?, prefix?, publicUrl }
 * Secret: BUNNY_STORAGE_KEY (the zone password) from the environment at runtime, never in the config.
 */
class BunnyStorageError extends Error {
	code: string; cause?: unknown;
	constructor(message: string, code: string, cause?: unknown) { super(message); this.name = "BunnyStorageError"; this.code = code; this.cause = cause; }
}
type UploadOptions = { key: string; body: Buffer | Uint8Array | ReadableStream<Uint8Array>; contentType: string; cacheControl?: string };
type FileInfo = { key: string; size: number; lastModified: Date; etag?: string };
type BunnyListing = { ObjectName: string; Length: number; LastChanged: string; IsDirectory: boolean; Checksum?: string | null }[];

class BunnyStorage {
	private zone: string; private host: string; private prefix: string; private publicUrl: string; private key: string;
	// (no TS parameter properties: the file must also load under Node's strip-only TypeScript mode)
	constructor(config: Record<string, unknown>) {
		this.zone = String(config.zone); this.host = String(config.host ?? "storage.bunnycdn.com");
		this.prefix = String(config.prefix ?? "media").replace(/^\/+|\/+$/g, "");
		this.publicUrl = String(config.publicUrl ?? "").replace(/\/+$/, "");
		const key = (globalThis as any).process?.env?.BUNNY_STORAGE_KEY;
		if (!key) throw new BunnyStorageError("BUNNY_STORAGE_KEY is not set", "CONFIG");
		this.key = key;
	}
	private path(key: string): string { const k = key.replace(/^\/+/, ""); if (k.includes("..")) throw new BunnyStorageError("Invalid key", "INVALID_PATH"); return `${this.prefix}/${k}`; }
	private url(path: string): string { return `https://${this.host}/${this.zone}/${path.split("/").map(encodeURIComponent).join("/")}`; }
	private async req(method: string, path: string, init: RequestInit = {}): Promise<Response> {
		const res = await fetch(this.url(path), { ...init, method, headers: { AccessKey: this.key, ...(init.headers as Record<string, string> | undefined) } });
		return res;
	}
	async upload(o: UploadOptions) {
		let body: Uint8Array;
		if (o.body instanceof ReadableStream) { const chunks: Uint8Array[] = []; const r = o.body.getReader(); for (;;) { const { done, value } = await r.read(); if (done) break; chunks.push(value); } body = Buffer.concat(chunks); }
		else body = o.body;
		const p = this.path(o.key);
		const res = await this.req("PUT", p, { body: body as any, headers: { "Content-Type": o.contentType || "application/octet-stream" } });
		if (res.status !== 201 && res.status !== 200) throw new BunnyStorageError(`Upload failed: ${res.status} ${await res.text()}`, "UPLOAD_FAILED");
		return { key: o.key, url: this.getPublicUrl(o.key), size: body.byteLength };
	}
	async download(key: string) {
		const res = await this.req("GET", this.path(key));
		if (res.status === 404) throw new BunnyStorageError(`Not found: ${key}`, "NOT_FOUND");
		if (!res.ok || !res.body) throw new BunnyStorageError(`Download failed: ${res.status}`, "DOWNLOAD_FAILED");
		return { body: res.body as ReadableStream<Uint8Array>, contentType: res.headers.get("content-type") || "application/octet-stream", size: Number(res.headers.get("content-length") || 0) };
	}
	async delete(key: string) {
		const res = await this.req("DELETE", this.path(key));
		if (!res.ok && res.status !== 404) throw new BunnyStorageError(`Delete failed: ${res.status}`, "DELETE_FAILED");
	}
	private async listDir(dir: string): Promise<BunnyListing> {
		const res = await this.req("GET", dir.replace(/\/?$/, "/"));
		if (res.status === 404) return [];
		if (!res.ok) throw new BunnyStorageError(`List failed: ${res.status}`, "LIST_FAILED");
		return (await res.json()) as BunnyListing;
	}
	async exists(key: string) {
		const p = this.path(key); const i = p.lastIndexOf("/");
		const items = await this.listDir(p.slice(0, i));
		return items.some((it) => !it.IsDirectory && it.ObjectName === p.slice(i + 1));
	}
	/** Non-recursive listing of the prefix directory (EmDash keys are flat); cursor = numeric offset. */
	async list(options: { prefix?: string; limit?: number; cursor?: string } = {}) {
		const items = (await this.listDir(this.prefix)).filter((it) => !it.IsDirectory && (!options.prefix || it.ObjectName.startsWith(options.prefix.replace(/^\/+/, ""))));
		const start = Number(options.cursor ?? 0); const limit = options.limit ?? 1000;
		const page = items.slice(start, start + limit);
		const files: FileInfo[] = page.map((it) => ({ key: it.ObjectName, size: it.Length, lastModified: new Date(it.LastChanged), etag: it.Checksum ?? undefined }));
		return start + limit < items.length ? { files, nextCursor: String(start + limit) } : { files };
	}
	async getSignedUploadUrl(_o: { key: string; contentType: string }): Promise<never> {
		throw new BunnyStorageError("Bunny Storage does not support signed upload URLs. Upload files through the API.", "NOT_SUPPORTED");
	}
	getPublicUrl(key: string) { return `${this.publicUrl}/${this.path(key)}`; }
}

export function createStorage(config: Record<string, unknown>) { return new BunnyStorage(config); }
export { BunnyStorage, BunnyStorageError };
