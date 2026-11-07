// How many hours make a full day of labour — the SPA twin of buildsuite_core.utils.full_day.
// A full day is not always 8 hours: a company may work 9 or 10, and a project can differ from its
// company. The server resolves it (project -> company -> default); the form checks here only
// decide what may be typed.

/** A usable full day: a number above 0 and no more than 24. */
export function isValidFullDayHours(v) {
	const n = Number(v);
	return v !== "" && v !== null && v !== undefined && Number.isFinite(n) && n > 0 && n <= 24;
}

/** The one message every form shows for a bad value (same wording as the server). */
export const FULL_DAY_HOURS_RULE = "Full day hours must be more than 0 and no more than 24.";

/** A value as typed, to what is stored: a number, or null for blank. Invalid is undefined. */
export function parseFullDayHours(v) {
	if (v === "" || v === null || v === undefined) return null;
	if (!isValidFullDayHours(v)) return undefined;
	return Math.round(Number(v) * 100) / 100;
}
