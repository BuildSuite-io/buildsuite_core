// Client-side mirror of the backend hierarchy date-boundary checks
// (buildsuite_core/utils/date_bounds.py). Gives instant feedback before a save;
// the server remains authoritative. Each function returns a clear error message
// string, or "" when the dates are valid. Blank boundaries are skipped.

function toDate(v) {
	if (!v) return null;
	const d = new Date(String(v).slice(0, 10) + "T00:00:00");
	return Number.isNaN(d.getTime()) ? null : d;
}

function fmt(v) {
	const d = toDate(v);
	if (!d) return "";
	return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

// End date may not precede start date on the same record.
export function endBeforeStartError(start, end) {
	const s = toDate(start);
	const e = toDate(end);
	if (s && e && e < s) {
		return `End date (${fmt(end)}) can't be earlier than the start date (${fmt(start)}).`;
	}
	return "";
}

// Dates must sit within the parent's [start, end] window. `parentLabel` names the
// boundary in the message (e.g. "project" or "parent project").
export function outOfParentBoundsError(
	start,
	end,
	parentStart,
	parentEnd,
	parentLabel = "project"
) {
	const s = toDate(start);
	const e = toDate(end);
	const ps = toDate(parentStart);
	const pe = toDate(parentEnd);
	if (s && ps && s < ps) {
		return `Start date (${fmt(start)}) can't be before the ${parentLabel} start date (${fmt(
			parentStart
		)}).`;
	}
	if (e && pe && e > pe) {
		return `End date (${fmt(end)}) can't be after the ${parentLabel} end date (${fmt(
			parentEnd
		)}).`;
	}
	return "";
}

// One-shot check: end>=start, then within-parent. Returns the first error or "".
export function dateBoundsError({ start, end, parentStart, parentEnd, parentLabel } = {}) {
	return (
		endBeforeStartError(start, end) ||
		outOfParentBoundsError(start, end, parentStart, parentEnd, parentLabel)
	);
}
