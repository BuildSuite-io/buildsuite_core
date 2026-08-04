// Evaluate a Frappe/ERPNext report's client script to read its DYNAMIC filters —
// the same thing the Desk does (frappe.dom.eval(script) → frappe.query_reports[name].
// filters). The report scripts are trusted first-party code from the site's own
// Report docs, run in the signed-in user's session (same trust boundary as the Desk);
// we eval them in a minimal `frappe` shim so the filter definitions + their computed
// defaults (e.g. frappe.datetime.get_today(), frappe.defaults.get_default("company"))
// resolve without pulling in the whole Desk bundle. Anything not shimmed resolves to a
// harmless no-op via a Proxy, so an unfamiliar report never throws — it just yields
// fewer/empty defaults.
//
// Only the control types the in-app renderer supports are returned (Link / Dynamic Link
// / Select / Date / Datetime / Check / Int / Float / Currency / Data). Others (e.g.
// MultiSelectList) are skipped — an open-source follow-up can add them.

const SUPPORTED = new Set([
	"Link",
	"Dynamic Link",
	"Select",
	"Date",
	"Datetime",
	"Check",
	"Int",
	"Float",
	"Currency",
	"Data",
]);

function pad(n) {
	return String(n).padStart(2, "0");
}
function iso(d) {
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
function toDate(v) {
	return v ? new Date(v) : new Date();
}

// A callable that returns itself for any access/call and coerces to "" — absorbs any
// un-shimmed frappe.* chain (frappe.a.b.c()) without throwing.
const universal = new Proxy(function () {}, {
	get(_t, prop) {
		if (prop === Symbol.toPrimitive) return () => "";
		if (prop === "then") return undefined; // never look thenable to await
		return universal;
	},
	apply() {
		return universal;
	},
});

function makeFrappeShim(company) {
	const now = () => new Date();
	const datetime = {
		get_today: () => iso(now()),
		nowdate: () => iso(now()),
		now_datetime: () => iso(now()),
		add_days: (d, n) => {
			const x = toDate(d);
			x.setDate(x.getDate() + Number(n || 0));
			return iso(x);
		},
		add_months: (d, n) => {
			const x = toDate(d);
			x.setMonth(x.getMonth() + Number(n || 0));
			return iso(x);
		},
		month_start: () => iso(new Date(now().getFullYear(), now().getMonth(), 1)),
		month_end: () => iso(new Date(now().getFullYear(), now().getMonth() + 1, 0)),
		year_start: () => iso(new Date(now().getFullYear(), 0, 1)),
		year_end: () => iso(new Date(now().getFullYear(), 11, 31)),
	};
	const defaults = {
		get_default: (k) => (k === "company" ? company || "" : ""),
		get_user_default: (k) => (k === "company" ? company || "" : ""),
		get_global_default: () => "",
	};
	const base = {
		query_reports: {},
		provide: () => {},
		datetime,
		defaults,
		query_report: { get_filter_value: () => "" },
		db: {
			get_link_options: () => Promise.resolve([]),
			get_value: () => Promise.resolve({}),
			get_list: () => Promise.resolve([]),
		},
		call: () => Promise.resolve({ message: [] }),
		model: { with_doctype: () => Promise.resolve() },
	};
	// Unknown top-level access → the universal no-op.
	return new Proxy(base, { get: (t, p) => (p in t ? t[p] : universal) });
}

function normalizeOptions(fieldtype, options) {
	if (Array.isArray(options)) {
		return options
			.map((o) => (o && o.value ? o.value : o))
			.filter((o) => typeof o === "string")
			.join("\n");
	}
	return typeof options === "string" ? options : "";
}

function normalizeDefault(v) {
	if (typeof v === "string" || typeof v === "number") return v;
	if (typeof v === "boolean") return v ? 1 : 0;
	return "";
}

/**
 * @returns {Array<{fieldname,label,fieldtype,options,mandatory,default}>} the report's
 * supported dynamic filters, or [] when the script defines none / can't be evaluated.
 */
export function evalReportFilters(script, reportName, { company = "" } = {}) {
	if (!script || !script.trim()) return [];
	const frappe = makeFrappeShim(company);
	try {
		// eslint-disable-next-line no-new-func
		const run = new Function(
			"frappe",
			"__",
			"erpnext",
			"cur_frm",
			"window",
			`"use strict";\n${script}`
		);
		run(frappe, (s) => s, universal, universal, {});
	} catch {
		return [];
	}
	const settings = frappe.query_reports?.[reportName];
	const raw = settings && Array.isArray(settings.filters) ? settings.filters : [];
	const out = [];
	for (const df of raw) {
		if (!df || !df.fieldname || !SUPPORTED.has(df.fieldtype)) continue;
		out.push({
			fieldname: df.fieldname,
			label: typeof df.label === "string" ? df.label : df.fieldname,
			fieldtype: df.fieldtype,
			options: normalizeOptions(df.fieldtype, df.options),
			mandatory: df.reqd || df.mandatory ? 1 : 0,
			default: normalizeDefault(df.default),
		});
	}
	return out;
}
