import { frappeRequest } from "frappe-ui-frappe-request";

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

// Doctype meta (fields, title_field…), fetched once per doctype per session.
const metaCache = new Map(); // doctype -> Promise<meta | null>
export function loadDoctypeMeta(doctype) {
	if (!metaCache.has(doctype)) {
		metaCache.set(
			doctype,
			frappeRequest({
				url: "frappe.desk.form.load.getdoctype",
				method: "POST",
				params: { doctype, with_parent: 1 },
			})
				.then((res) => (res?.docs ? res : res?.message)?.docs?.[0] || null)
				.catch((err) => {
					metaCache.delete(doctype);
					console.warn("[buildsuite] Failed to fetch doctype meta", err);
					return null;
				})
		);
	}
	return metaCache.get(doctype);
}

// How a Link filter's value is shown and searched. Records are identified by an ID (PROJ-0042) but
// people know them by name ("Aso Villa"), so the picker displays the doctype's title_field and
// searches it as well as the ID — the same rule Frappe's own link search follows.
export function linkPickerProps(meta) {
	const title = meta?.title_field || "";
	return {
		labelField: title || "name",
		searchFields: title ? [title, "name"] : ["name"],
	};
}

// { id: title } for the given record IDs of a Link target (empty when it has no title field).
export async function resolveLinkLabels(doctype, meta, ids) {
	const title = meta?.title_field;
	const wanted = [...new Set((ids || []).filter(Boolean))];
	if (!title || !wanted.length) return {};
	try {
		const rows = await frappeRequest({
			url: "frappe.client.get_list",
			params: {
				doctype,
				fields: ["name", title],
				filters: [["name", "in", wanted]],
				limit_page_length: 0,
			},
		});
		return Object.fromEntries((rows || []).map((r) => [r.name, r[title]]));
	} catch {
		return {};
	}
}

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
	// A Link filter keeps the record's name (valueLabel) beside its ID, so the chip reads
	// "Project = Aso Villa" rather than "Project = PROJ-0042".
	const shown = f.valueLabel ?? f.value;
	if (f.condition === "is") text = f.value === "not set" ? "Not Set" : "Set";
	else if (f.condition === "Between" && Array.isArray(f.value))
		text = `${f.value[0]} – ${f.value[1]}`;
	else if (Array.isArray(shown)) text = shown.join(", ");
	else if (f.fieldtype === "Check") text = f.value === "0" || f.value === 0 ? "No" : "Yes";
	else text = String(shown ?? "");
	return `${f.label} ${CONDITION_SYMBOL[f.condition] || f.condition} ${text}`.trim();
}
