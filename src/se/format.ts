export function ordinalDate(d: Date, tz = "Europe/Berlin"): string {
	const parts = new Intl.DateTimeFormat("en-GB", { timeZone: tz, day: "numeric", month: "long", year: "numeric" }).formatToParts(d);
	const day = Number(parts.find((p) => p.type === "day")?.value ?? d.getDate());
	const month = parts.find((p) => p.type === "month")?.value; const year = parts.find((p) => p.type === "year")?.value;
	const s = day % 100 >= 11 && day % 100 <= 13 ? "th" : ["th", "st", "nd", "rd"][day % 10] ?? "th";
	return `${day}${s} ${month} ${year}`;
}
export const escapeHtml = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
