export function ordinalDate(d: Date, tz = "Europe/Berlin"): string {
	const parts = new Intl.DateTimeFormat("en-GB", { timeZone: tz, day: "numeric", month: "long", year: "numeric" }).formatToParts(d);
	const day = Number(parts.find((p) => p.type === "day")?.value ?? d.getDate());
	const month = parts.find((p) => p.type === "month")?.value; const year = parts.find((p) => p.type === "year")?.value;
	const s = day % 100 >= 11 && day % 100 <= 13 ? "th" : ["th", "st", "nd", "rd"][day % 10] ?? "th";
	return `${day}${s} ${month} ${year}`;
}
export const escapeHtml = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** ISO 8601 in Europe/Berlin with numeric offset, as WordPress prints dates (e.g. 2026-09-25T07:00:00+02:00). */
export function berlinIso(d: Date, tz = "Europe/Berlin"): string {
	const parts = Object.fromEntries(new Intl.DateTimeFormat("en-GB", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).formatToParts(d).map((p) => [p.type, p.value]));
	const local = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour % 24, +parts.minute, +parts.second);
	const off = Math.round((local - d.getTime()) / 60000); const sign = off >= 0 ? "+" : "-"; const a = Math.abs(off);
	return `${parts.year}-${parts.month}-${parts.day}T${String(+parts.hour % 24).padStart(2, "0")}:${parts.minute}:${parts.second}${sign}${String(Math.floor(a / 60)).padStart(2, "0")}:${String(a % 60).padStart(2, "0")}`;
}
