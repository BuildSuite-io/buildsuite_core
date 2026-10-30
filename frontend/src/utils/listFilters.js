// Shared helpers for the Frappe-style dynamic "Add filter" builder — used by DocTypeListView and by
// the hand-built lists (via useDynamicFilters), so every list offers the same fields, the same
// operators and the same chip text.

// Layout / no-value fieldtypes can't be filtered on, so they're excluded from the picker.
export const NO_VALUE_FIELDTYPES = new Set([
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
	"Table",
	"Table MultiSelect",
	"Button",
	"Image",
	"Fold",
	"Heading",
	"Signature",
	"Geolocation",
]);

export const STANDARD_FILTER_FIELDS = [
	{ fieldname: "name", label: "ID", fieldtype: "Data" },
	{ fieldname: "owner", label: "Created By", fieldtype: "Link", options: "User" },
	{ fieldname: "creation", label: "Created On", fieldtype: "Datetime" },
	{ fieldname: "modified", label: "Last Updated On", fieldtype: "Datetime" },
	{ fieldname: "modified_by", label: "Last Updated By", fieldtype: "Link", options: "User" },
	{ fieldname: "_assign", label: "Assigned To", fieldtype: "Data" },
	{ fieldname: "idx", label: "Index", fieldtype: "Int" },
];

// Standard metadata + the doctype's own value-bearing fields, mirroring Frappe's list filter list.
export function filterableFieldsFromMeta(meta) {
	const out = [...STANDARD_FILTER_FIELDS];
	const seen = new Set(out.map((f) => f.fieldname));
	for (const f of meta?.fields || []) {
		if (!f?.fieldname || NO_VALUE_FIELDTYPES.has(f.fieldtype) || seen.has(f.fieldname))
			continue;
		out.push({
			fieldname: f.fieldname,
			label: f.label || f.fieldname,
			fieldtype: f.fieldtype,
			options: f.options,
		});
		seen.add(f.fieldname);
	}
	return out;
}

// One dynamic filter -> a [field, operator, value] tuple the backend understands
// (frappe.client.get_list / reportview). Returns null when the value is empty.
export function toServerFilter(f) {
	const field = f.fieldname;
	const v = f.value;
	switch (f.condition) {
		case "like":
		case "not like":
			return v === "" || v == null ? null : [field, f.condition, `%${v}%`];
		case "in":
		case "not in": {
			const list = Array.isArray(v)
				? v.filter(Boolean)
				: String(v ?? "")
						.split(",")
						.map((s) => s.trim())
						.filter(Boolean);
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

// Chip text: "Label operator value".
const CONDITION_SYMBOL = {
	"=": "=",
	"!=": "≠",
	like: "like",
	"not like": "not like",
	in: "in",
	"not in": "not in",
	is: "is",
	">": ">",
	"<": "<",
	">=": "≥",
	"<=": "≤",
	Between: "between",
	Timespan: "in",
};
export function chipLabel(f) {
	let text;
	if (f.condition === "is") text = f.value === "not set" ? "Not Set" : "Set";
	else if (f.condition === "Between" && Array.isArray(f.value))
		text = `${f.value[0]} – ${f.value[1]}`;
	else if (Array.isArray(f.value)) text = f.value.join(", ");
	else if (f.fieldtype === "Check") text = f.value === "0" || f.value === 0 ? "No" : "Yes";
	else text = String(f.value ?? "");
	return `${f.label} ${CONDITION_SYMBOL[f.condition] || f.condition} ${text}`.trim();
}
