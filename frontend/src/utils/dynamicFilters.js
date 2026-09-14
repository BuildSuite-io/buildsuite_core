// Client-side apply of the dynamic-filter tuples the DeskFilterEditor builds — the counterpart to
// DocTypeListView's server-side toServerFilter, for DeskList views that hold their rows in memory.
//
// A filter is { fieldname, label, fieldtype, options, condition, value }. matchesDynamicFilters(row,
// filters) returns true when the row satisfies EVERY active filter (AND), so a caller can do
// `rows.filter((r) => matchesDynamicFilters(r, filters))`.

function lc(v) {
	return v == null ? "" : String(v).toLowerCase();
}

function toList(v) {
	if (Array.isArray(v)) return v.filter((x) => x !== "" && x != null).map(String);
	return String(v ?? "")
		.split(",")
		.map((s) => s.trim())
		.filter(Boolean);
}

function matchesOne(raw, condition, target) {
	switch (condition) {
		case "=":
			return String(raw ?? "") === String(target ?? "");
		case "!=":
			return String(raw ?? "") !== String(target ?? "");
		case "like":
			return lc(raw).includes(lc(target));
		case "not like":
			return !lc(raw).includes(lc(target));
		case "in":
			return toList(target).includes(String(raw ?? ""));
		case "not in":
			return !toList(target).includes(String(raw ?? ""));
		case "is":
			// value is "set" | "not set"
			return target === "not set" ? raw == null || raw === "" : raw != null && raw !== "";
		case ">":
			return Number(raw) > Number(target);
		case "<":
			return Number(raw) < Number(target);
		case ">=":
			return Number(raw) >= Number(target);
		case "<=":
			return Number(raw) <= Number(target);
		case "Between": {
			const [a, b] = Array.isArray(target) ? target : [];
			if (a == null || a === "" || b == null || b === "") return true;
			// String compare works for ISO dates (YYYY-MM-DD); numbers compare numerically.
			const isNum = !Number.isNaN(Number(raw)) && !Number.isNaN(Number(a));
			return isNum
				? Number(raw) >= Number(a) && Number(raw) <= Number(b)
				: String(raw) >= String(a) && String(raw) <= String(b);
		}
		default:
			// Timespan and any unknown condition can't be evaluated client-side — don't exclude.
			return true;
	}
}

export function matchesDynamicFilters(row, filters) {
	if (!filters || !filters.length) return true;
	return filters.every((f) => matchesOne(row?.[f.fieldname], f.condition, f.value));
}
