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

// One dynamic filter -> a [field, operator, value] tuple the backend understands
// (frappe.get_list / reportview). Returns null when the value is empty so the filter
// is dropped rather than sent as a no-op. Mirrors DocTypeListView.toServerFilter so
// server-paginated DeskList views filter identically to the doctype list.
export function toServerFilter(f) {
	const field = f.fieldname;
	const v = f.value;
	switch (f.condition) {
		case "like":
		case "not like":
			return v === "" || v == null ? null : [field, f.condition, `%${v}%`];
		case "in":
		case "not in": {
			const list = toList(v);
			return list.length ? [field, f.condition, list] : null;
		}
		case "is":
			return [field, "is", v || "set"];
		case "Between": {
			const [a, b] = Array.isArray(v) ? v : [];
			return a && b ? [field, "between", [a, b]] : null;
		}
		case "Timespan":
			return v ? [field, "timespan", v] : null;
		default:
			return v === "" || v == null ? null : [field, f.condition, v];
	}
}

// The full set of dynamic filters as server tuples, dropping the empty ones.
export function toServerFilters(filters) {
	if (!filters || !filters.length) return [];
	return filters.map(toServerFilter).filter(Boolean);
}
