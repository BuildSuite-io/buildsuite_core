// Command-palette search model (⌘K). Two kinds of answer, like the prototype (S363):
//   · PLACES  — where to GO: a doctype's list, or a report. Client-side + permission-gated.
//   · RECORDS — the documents themselves. Fetched from the permission-safe Frappe global-search
//               index via searchApi.searchRecords; this module only maps a result's doctype to its
//               SPA detail route + a label/icon (DOCTYPE_META).
//
// Permission is the whole point: a place a role can't open must not appear, and records are gated
// server-side by the same read permission that hides their list. So a query never leaks a record
// out of a doctype the user can't open.

// doctype -> how a record result is shown + where it opens. Mirror the backend SEARCHABLE_DOCTYPES
// (api/search.py); every entry here has a real SPA detail route.
export const DOCTYPE_META = {
	Project: { label: "Project", icon: "building-2", to: (n) => `/projects/${n}` },
	Task: { label: "Task", icon: "clipboard-list", to: (n) => `/tasks/${n}` },
	"Work Package": { label: "Work package", icon: "layout-grid", to: (n) => `/work-packages/${n}` },
	"Stage Planning": { label: "Stage plan", icon: "calendar", to: (n) => `/stage-plannings/${n}` },
	"Scope Change Order": { label: "Change order", icon: "file-text", to: (n) => `/sco/${n}` },
	BOQ: { label: "BOQ", icon: "estimation", to: (n) => `/boq/${n}` },
	Tender: { label: "Tender", icon: "file-text", to: (n) => `/tenders/${n}` },
	Quotation: { label: "Quotation", icon: "file-text", to: (n) => `/quotations/${n}` },
	"Construction Rate Master": { label: "Rate", icon: "chart-bar", to: (n) => `/rate-master/${n}` },
	Assembly: { label: "Assembly", icon: "wrench", to: (n) => `/assembly/${n}` },
	"Estimate Template": { label: "Estimate template", icon: "layout-grid", to: (n) => `/estimate-template/${n}` },
	"Material Request": { label: "Material request", icon: "clipboard-list", to: (n) => `/procurement/material-requests/${n}` },
	"Purchase Order": { label: "Purchase order", icon: "file-text", to: (n) => `/procurement/purchase-orders/${n}` },
	"Purchase Receipt": { label: "Purchase receipt", icon: "stock", to: (n) => `/procurement/receipts/${n}` },
	Machinery: { label: "Machinery", icon: "wrench", to: (n) => `/machinery/${n}` },
	"Machinery Usage": { label: "Machinery usage", icon: "wrench", to: (n) => `/machinery-usage/${n}` },
	"Subcontractor Work Order": { label: "Work order", icon: "subcontract", to: (n) => `/subcontractor-work-orders/${n}` },
	"Measurement Book": { label: "Measurement book", icon: "chart-bar", to: (n) => `/measurement-books/${n}` },
	"Subcontractor Bill": { label: "Subcontractor bill", icon: "receipt", to: (n) => `/subcontractor-bills/${n}` },
	Supplier: { label: "Supplier", icon: "building-2", to: (n) => `/subcontractors/${n}` },
	Employee: { label: "Employee", icon: "hard-hat", to: (n) => `/field-employees/${n}` },
	Crew: { label: "Crew", icon: "users-2", to: (n) => `/crews/${n}` },
	"Field Attendance": { label: "Attendance", icon: "users-2", to: (n) => `/field-attendance/${n}` },
	"Sales Invoice": { label: "Invoice", icon: "file-text", to: (n) => `/project-finance/invoices/${n}` },
	"Purchase Invoice": { label: "Supplier bill", icon: "receipt", to: (n) => `/project-finance/supplier-bills/${n}` },
};

// Doctypes the SPA has NO bespoke view for but the generic records browser can render
// (/records/<doctype>/<name>) — mirrors permissions/resource_map.RESOURCE_DOCTYPES. A record of
// one of these still opens (in the generic form view) rather than being dropped.
const GENERIC_DOCTYPES = new Set([
	"Task Progress Entry",
	"Item",
	"Stock Entry",
	"Customer",
	"Payment Entry",
	"Petty Cash Request",
	"Expense Entry",
]);

// A raw {doctype, name, title} record result -> a palette row. Prefer the doctype's bespoke detail
// view; fall back to the generic records browser for a doctype without one; null if neither can
// open it (shouldn't happen — the backend only returns doctypes the SPA can navigate to).
export function decorateRecord(r) {
	const meta = DOCTYPE_META[r.doctype];
	if (meta) {
		return {
			kind: "record",
			key: `${r.doctype}:${r.name}`,
			title: r.title || r.name,
			type: meta.label,
			icon: meta.icon,
			to: meta.to(r.name),
		};
	}
	if (GENERIC_DOCTYPES.has(r.doctype)) {
		return {
			kind: "record",
			key: `${r.doctype}:${r.name}`,
			title: r.title || r.name,
			type: r.doctype,
			icon: "file-text",
			to: `/records/${encodeURIComponent(r.doctype)}/${encodeURIComponent(r.name)}`,
		};
	}
	return null;
}

// Navigation destinations. `cap` gates a doctype list on a usePermissions read cap; `report` gates
// a report on the user's permitted report routes (access context). `words` are what someone types
// to mean the place itself.
const PLACES = [
	// Execution
	{ label: "Projects", icon: "clipboard-list", to: "/projects", cap: "project", words: ["project", "projects", "job", "jobs", "site", "sites"] },
	{ label: "Tasks", icon: "check-circle", to: "/tasks", cap: "task", words: ["task", "tasks", "activity", "activities"] },
	{ label: "Work packages", icon: "layout-grid", to: "/work-packages", cap: "workPackage", words: ["work package", "work packages", "package", "wp"] },
	{ label: "Stage plans", icon: "calendar", to: "/stage-plannings", cap: "stagePlanning", words: ["stage", "stages", "stage plan", "programme", "schedule"] },
	{ label: "Change orders", icon: "file-text", to: "/sco", cap: "sco", words: ["change order", "sco", "scope change", "variation"] },
	// Estimation
	{ label: "BOQ", icon: "estimation", to: "/boq", cap: "boq", words: ["boq", "bill of quantities", "estimate"] },
	{ label: "Rate master", icon: "chart-bar", to: "/rate-master", cap: "rateMaster", words: ["rate", "rates", "rate master", "price"] },
	{ label: "Assemblies", icon: "wrench", to: "/assembly", cap: "assembly", words: ["assembly", "assemblies"] },
	{ label: "Estimate templates", icon: "layout-grid", to: "/estimate-templates", cap: "estimateTemplate", words: ["estimate template", "templates"] },
	{ label: "Tenders", icon: "file-text", to: "/tenders", cap: "tender", words: ["tender", "tenders", "bid"] },
	{ label: "Quotations", icon: "file-text", to: "/quotations", cap: "quotation", words: ["quotation", "quotations", "quote"] },
	// Procurement
	{ label: "Material requests", icon: "clipboard-list", to: "/procurement/material-requests", cap: "materialRequest", words: ["material request", "mr", "requisition", "indent"] },
	{ label: "Purchase orders", icon: "file-text", to: "/procurement/purchase-orders", cap: "purchaseOrder", words: ["purchase order", "po", "order"] },
	{ label: "Purchase receipts", icon: "stock", to: "/procurement/receipts", cap: "purchaseReceipt", words: ["purchase receipt", "grn", "receipt", "delivery"] },
	{ label: "Items", icon: "tag", to: "/items", cap: "item", words: ["item", "items", "material", "materials"] },
	// Subcontract
	{ label: "Work orders", icon: "subcontract", to: "/subcontractor-work-orders", cap: "subcontractorWorkOrder", words: ["work order", "wo", "subcontract"] },
	{ label: "Subcontractor bills", icon: "receipt", to: "/subcontractor-bills", cap: "subcontractorBill", words: ["subcontractor bill", "sub bill", "ra bill"] },
	{ label: "Measurement books", icon: "chart-bar", to: "/measurement-books", cap: "measurementBook", words: ["measurement book", "mb", "measurement"] },
	{ label: "Subcontractors", icon: "building-2", to: "/subcontractors", cap: "supplier", words: ["subcontractor", "supplier", "vendor"] },
	// Finance
	{ label: "Invoices", icon: "file-text", to: "/project-finance/invoices", cap: "salesInvoice", words: ["invoice", "invoices", "client bill", "sales invoice"] },
	{ label: "Bills", icon: "receipt", to: "/project-finance/bills", cap: "supplierBill", words: ["bill", "bills", "supplier bill", "purchase invoice"] },
	{ label: "Payments", icon: "refresh-ccw", to: "/project-finance/payments", cap: "advance", words: ["payment", "payments"] },
	{ label: "Petty cash", icon: "hand-coins", to: "/project-finance/petty-cash", cap: "pettyCash", words: ["petty cash", "petty", "cash"] },
	{ label: "Expenses", icon: "receipt", to: "/project-finance/expenses", cap: "expense", words: ["expense", "expenses"] },
	// Workforce / equipment
	{ label: "Field attendance", icon: "users-2", to: "/field-attendance", cap: "fieldAttendance", words: ["attendance", "field attendance", "muster"] },
	{ label: "Field employees", icon: "hard-hat", to: "/field-employees", cap: "employee", words: ["employee", "employees", "workforce", "labour"] },
	{ label: "Crews", icon: "users-2", to: "/crews", cap: "crew", words: ["crew", "crews", "gang"] },
	{ label: "Machinery", icon: "wrench", to: "/machinery", cap: "machinery", words: ["machinery", "equipment", "plant"] },
];

// The bespoke reports as places, keyed by the route the access context gates (report_access).
// Only those the user may open (session reportRoutes) are offered — the same gate as the tile.
const REPORT_PLACES = {
	"/project-finance/report/pnl": { label: "Profit & Loss", icon: "chart-bar", words: ["profit", "loss", "pnl", "p&l"] },
	"/project-finance/report/aged": { label: "Receivables & Payables", icon: "chart-bar", words: ["receivable", "payable", "aged", "aging", "outstanding"] },
	"/project-finance/report/position": { label: "Financial Position", icon: "wallet", words: ["financial position", "balance", "net position"] },
	"/project-finance/report/expenses": { label: "Expense Summary", icon: "receipt", words: ["expense summary", "expenses"] },
	"/project-finance/report/cashbank": { label: "Cash & Bank Statement", icon: "wallet", words: ["cash", "bank", "statement"] },
	"/project-finance/report/petty": { label: "Petty Cash", icon: "hand-coins", words: ["petty cash", "petty"] },
	"/procurement/report/requests-to-order": { label: "Requests to order", icon: "clipboard-list", words: ["requests to order", "to order", "waiting"] },
	"/procurement/report/delivery-followup": { label: "Delivery follow-up", icon: "stock", words: ["delivery", "follow up", "followup", "overdue"] },
	"/procurement/report/site-stock": { label: "Material at site", icon: "package", words: ["site stock", "material at site", "stock"] },
	"/procurement/report/rate-check": { label: "Purchase rate vs estimate", icon: "chart-bar", words: ["rate check", "rate vs estimate", "purchase rate"] },
	"/procurement/report/purchase-register": { label: "Purchase register", icon: "file-text", words: ["purchase register", "register"] },
	"/procurement/report/consumption-by-cost-code": { label: "Consumption by cost code", icon: "package", words: ["consumption", "cost code"] },
	"/labour-attendance": { label: "Labour Attendance Register", icon: "clipboard-list", words: ["labour attendance", "attendance register"] },
	"/overtime-attendance": { label: "Overtime Attendance Register", icon: "clipboard-list", words: ["overtime", "overtime attendance"] },
	"/workforce/attendance-summary": { label: "Site Attendance Summary", icon: "users-2", words: ["attendance summary", "site attendance"] },
	"/reports/delay-analysis": { label: "Delay Analysis", icon: "calendar", words: ["delay", "delay analysis", "slippage"] },
};

const norm = (s) => (s || "").toLowerCase().trim();

// Score a place against the query: prefix on the label wins, then a word match, then a substring.
function scorePlace(q, place) {
	const label = norm(place.label);
	if (label.startsWith(q)) return 100;
	for (const w of place.words) {
		const nw = norm(w);
		if (nw === q) return 90;
		if (nw.startsWith(q)) return 70;
	}
	if (label.includes(q)) return 50;
	if (place.words.some((w) => norm(w).includes(q))) return 30;
	return 0;
}

// Permitted, query-matched navigation places. `ctx` supplies the gates: canRead(cap) for the
// doctype lists, and reportRoutes (the access context's permitted report routes) for the reports —
// so search never offers a place a role can't open (the same gate the router guard uses).
export function searchPlaces(query, ctx) {
	const q = norm(query);
	if (q.length < 2) return [];
	const canRead = ctx?.canRead || (() => false);
	const reportRoutes = ctx?.reportRoutes || [];
	const reportPlaces = reportRoutes
		.filter((route) => REPORT_PLACES[route])
		.map((route) => ({ ...REPORT_PLACES[route], to: route, isReport: true, words: REPORT_PLACES[route].words }));
	const gated = [...PLACES.filter((p) => canRead(p.cap)), ...reportPlaces];
	return gated
		.map((p) => ({ ...p, kind: "place", key: p.to, score: scorePlace(q, p) }))
		.filter((p) => p.score > 0)
		.sort((a, b) => b.score - a.score || a.label.localeCompare(b.label))
		.slice(0, 6);
}
