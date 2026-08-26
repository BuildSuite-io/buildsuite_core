// Role system — the 12 standard BuildSuite roles, the workspace visibility matrix,
// and per-role sidebar ordering. The visibility + order below are transcribed from the
// "BuildSuite Core - persona landing, module and workspace access" sheet (Workspaces tab):
// each persona's access level and sidebar order per workspace. This drives the Vue app's
// sidebar only; backend role permissions (permissions/*.py) and the Desk /app workspace
// `roles` fields are enforced/configured separately.
//
// Session 34: BSA (BuildSuite Administrator) added as the 12th role. BSA sits
// alongside System Manager (admin) — they don't replace each other. System
// Manager handles Frappe-platform admin (sites, apps, backups). BSA handles
// BuildSuite-product admin (Workspace Structure Settings, Site Execution
// Settings, Project Type templates, Pro license). Both get ✓ on every workspace.

// =====================================================================
// ROLES — 12 stable role objects. `id` is the persisted slug; `shortName`
// shows in the topbar dropdown trigger; `color` is a Tailwind bg- class for
// the role badge, picked from the project's named palette (see tailwind.config.js).
// =====================================================================
export const ROLES = [
	{
		id: "director",
		name: "Director / Owner",
		shortName: "Director",
		description:
			"Executive oversight — portfolio P&L, approvals at threshold, strategic decisions.",
		color: "bg-ink-900",
	},
	{
		id: "pm",
		name: "Project Manager",
		shortName: "PM",
		description: "Owns project delivery — schedule, scope, budget, day-to-day approvals.",
		color: "bg-info-600",
	},
	{
		id: "estimator",
		name: "Estimator",
		shortName: "Estimator",
		description: "Builds tenders and initial BOQs from drawings and rate analysis.",
		color: "bg-warning-500",
	},
	{
		id: "qs",
		name: "Quantity Surveyor",
		shortName: "QS",
		description:
			"Maintains rates, measurement books, RA bills, and BOQ revisions during execution.",
		color: "bg-warning-700",
	},
	{
		id: "site-engineer",
		name: "Site Engineer",
		shortName: "Site Engineer",
		description:
			"Runs the site day-to-day — tasks, material requests, daily diary, scope flags.",
		color: "bg-success-600",
	},
	{
		id: "foreman",
		name: "Foreman / Supervisor",
		shortName: "Foreman",
		description: "Field supervisor — crews, overtime, on-site execution.",
		color: "bg-success-700",
	},
	{
		id: "procurement",
		name: "Procurement Officer",
		shortName: "Procurement",
		description: "Converts material requests into POs, manages suppliers and GRN.",
		color: "bg-info-700",
	},
	{
		id: "store-keeper",
		name: "Store Keeper",
		shortName: "Store",
		description: "Receives, issues, and reconciles stock at site stores.",
		color: "bg-ink-600",
	},
	{
		id: "accountant",
		name: "Accountant",
		shortName: "Accountant",
		description: "Books vendor and subcontractor payments, petty cash, journals.",
		color: "bg-danger-600",
	},
	{
		id: "hr-manager",
		name: "HR Manager",
		shortName: "HR Manager",
		description:
			"Office-staff HR — employees, leave, salary, appraisal (site labour lives in Workforce).",
		color: "bg-info-500",
	},
	{
		id: "admin",
		name: "System Manager (Admin)",
		shortName: "Admin",
		description:
			"Full access — Frappe-platform admin: sites, apps, backups, integrations, troubleshooting.",
		color: "bg-brand-600",
	},
	{
		id: "bsa",
		name: "BuildSuite Administrator",
		shortName: "BS Admin",
		description:
			'BuildSuite-product admin — Workspace Structure, Site Execution Settings, Project Type templates, Pro license. The "BuildSuite owner" at a customer org.',
		color: "bg-brand-700",
	},
];

// =====================================================================
// WORKSPACE_VISIBILITY — transcribed from the persona/workspace access sheet
// (Workspaces tab). Keyed by workspace slug, then by role id; the value is the
// access level, or null when the workspace is hidden for that role. Only null vs
// non-null decides sidebar visibility — the string is also used as a hint badge
// (see ACCESS_HINTS in DeskShell). "Home" is always shown and isn't listed here.
//
//   'full'         — ✓   full access
//   'read'         — ✓R  read-only
//   'approve'      — ✓A  approve-only (can't create or edit, only approve)
//   'create-own'   — ✓C  create-own (e.g. raise own tasks)
//   'self-service' — ✓SS self-service (own leave / payslip)
//   'team-only'    — ✓T  team-only (HR scoped to direct reports)
//   'pay-only'     — ✓P  pay-only (sees billing/payment view only)
//   'mr-only'      — ✓MR material-request raise only
//    null          — —   hidden
// =====================================================================
export const WORKSPACE_VISIBILITY = {
	"site-execution": {
		director: "full",
		pm: "full",
		estimator: "read",
		qs: "read",
		"site-engineer": "full",
		foreman: "create-own",
		procurement: null,
		"store-keeper": null,
		accountant: "read",
		"hr-manager": null,
		admin: "full",
		bsa: "full",
	},
	estimation: {
		director: "full",
		pm: "read",
		estimator: "full",
		qs: "full",
		"site-engineer": null,
		foreman: null,
		procurement: null,
		"store-keeper": null,
		accountant: null,
		"hr-manager": null,
		admin: "full",
		bsa: "full",
	},
	procurement: {
		director: "full",
		pm: "approve",
		estimator: null,
		qs: null,
		"site-engineer": "create-own",
		foreman: "create-own",
		procurement: "full",
		"store-keeper": "full",
		accountant: "read",
		"hr-manager": null,
		admin: "full",
		bsa: "full",
	},
	subcontract: {
		director: "full",
		pm: "approve",
		estimator: "read",
		qs: "full",
		"site-engineer": "read",
		foreman: null,
		procurement: "full",
		"store-keeper": null,
		accountant: "read",
		"hr-manager": null,
		admin: "full",
		bsa: "full",
	},
	workforce: {
		director: "read",
		pm: "approve",
		estimator: null,
		qs: null,
		"site-engineer": "full",
		foreman: "full",
		procurement: null,
		"store-keeper": null,
		accountant: "read",
		"hr-manager": "full",
		admin: "full",
		bsa: "full",
	},
	equipment: {
		director: "read",
		pm: "approve",
		estimator: null,
		qs: null,
		"site-engineer": "full",
		foreman: "full",
		procurement: "full",
		"store-keeper": "full",
		accountant: "read",
		"hr-manager": null,
		admin: "full",
		bsa: "full",
	},
	"project-finance": {
		director: "full",
		pm: "full",
		estimator: "self-service",
		qs: "read",
		"site-engineer": "self-service",
		foreman: "self-service",
		procurement: "self-service",
		"store-keeper": "self-service",
		accountant: "full",
		"hr-manager": "self-service",
		admin: "full",
		bsa: "full",
	},
	accounting: {
		director: "full",
		pm: "read",
		estimator: null,
		qs: null,
		"site-engineer": null,
		foreman: null,
		procurement: null,
		"store-keeper": null,
		accountant: "full",
		"hr-manager": null,
		admin: "full",
		bsa: "full",
	},
	buying: {
		director: "full",
		pm: "read",
		estimator: null,
		qs: null,
		"site-engineer": null,
		foreman: null,
		procurement: "full",
		"store-keeper": "read",
		accountant: "read",
		"hr-manager": null,
		admin: "full",
		bsa: "full",
	},
	stock: {
		director: "full",
		pm: "read",
		estimator: null,
		qs: null,
		"site-engineer": "read",
		foreman: null,
		procurement: "read",
		"store-keeper": "full",
		accountant: "read",
		"hr-manager": null,
		admin: "full",
		bsa: "full",
	},
	assets: {
		director: "full",
		pm: "read",
		estimator: null,
		qs: null,
		"site-engineer": "read",
		foreman: "read",
		procurement: null,
		"store-keeper": null,
		accountant: "full",
		"hr-manager": null,
		admin: "full",
		bsa: "full",
	},
	hr: {
		director: "full",
		pm: "read",
		estimator: "self-service",
		qs: "self-service",
		"site-engineer": "self-service",
		foreman: "self-service",
		procurement: "self-service",
		"store-keeper": "self-service",
		accountant: "full",
		"hr-manager": "full",
		admin: "full",
		bsa: "full",
	},
};

// =====================================================================
// WORKSPACE_ORDER — sidebar ordering per role, by frequency of use.
// Not alphabetical. Hidden workspaces are simply omitted (the store getter
// also filters out anything with a null visibility, so leaving a slug here
// for a role that can't see it is harmless — but keep the lists honest).
//
// Orderings for Foreman, PM, and Site Engineer are taken verbatim from
// CLAUDE.md §12.3. The others are chosen by frequency-of-use given the
// visibility matrix. Admin and Director see all 12: BuildSuite workspaces
// first, then the inherited ERPNext / Frappe HR block at the bottom.
// =====================================================================
// Session 33 — 6 BuildSuite workspaces (was 7). Scope Change merged into
// Site Execution; SCOs are reached via the merged workspace's shortcut tile.
const BUILDSUITE_WORKSPACES = [
	"site-execution",
	"estimation",
	"procurement",
	"subcontract",
	"workforce",
	"equipment",
	"project-finance",
];
const INHERITED_WORKSPACES = ["accounting", "buying", "stock", "assets", "hr"];
// Director / Admin / BSA see every workspace, BuildSuite block first then the
// inherited ERPNext / Frappe HR block, in the CSV's canonical order.
const FULL_ORDER = [...BUILDSUITE_WORKSPACES, ...INHERITED_WORKSPACES];

export const WORKSPACE_ORDER = {
	director: FULL_ORDER,
	admin: FULL_ORDER,
	bsa: FULL_ORDER,
	pm: [
		"site-execution",
		"procurement",
		"subcontract",
		"workforce",
		"project-finance",
		"estimation",
		"equipment",
		"accounting",
		"buying",
		"stock",
		"assets",
		"hr",
	],
	estimator: ["estimation", "site-execution", "project-finance", "hr", "subcontract"],
	qs: ["estimation", "subcontract", "site-execution", "project-finance", "hr"],
	"site-engineer": [
		"site-execution",
		"workforce",
		"equipment",
		"procurement",
		"subcontract",
		"stock",
		"assets",
		"hr",
		"project-finance",
	],
	foreman: [
		"workforce",
		"site-execution",
		"equipment",
		"assets",
		"hr",
		"procurement",
		"project-finance",
	],
	procurement: [
		"procurement",
		"subcontract",
		"equipment",
		"project-finance",
		"buying",
		"stock",
		"hr",
	],
	"store-keeper": ["procurement", "equipment", "project-finance", "buying", "stock", "hr"],
	accountant: [
		"project-finance",
		"subcontract",
		"procurement",
		"site-execution",
		"workforce",
		"equipment",
		"accounting",
		"buying",
		"stock",
		"assets",
		"hr",
	],
	"hr-manager": ["workforce", "project-finance", "hr"],
};

// Map a User.persona Select value (the human label, e.g. "Project Manager") to
// the persona id used by the role switcher / gating (e.g. "pm"). Returns null
// when the label isn't a recognised persona.
export function personaIdFromName(name) {
	if (!name) return null;
	const match = ROLES.find((r) => r.name === name);
	return match ? match.id : null;
}

// Frappe BuildSuite role -> persona id. Used as a fallback when the User.persona
// field is unset (e.g. Administrator). Mirrors the backend permissions/setup map.
export const ROLE_TO_PERSONA = {
	"BuildSuite Director": "director",
	"BuildSuite PM": "pm",
	"BuildSuite Estimator": "estimator",
	"BuildSuite QS": "qs",
	"BuildSuite Site Engineer": "site-engineer",
	"BuildSuite Foreman": "foreman",
	"BuildSuite Procurement Officer": "procurement",
	"BuildSuite Store Keeper": "store-keeper",
	"BuildSuite Accountant": "accountant",
	"BuildSuite HR Manager": "hr-manager",
	"BuildSuite Administrator": "bsa",
	"System Manager": "admin",
};

// Derive a persona id from a user's Frappe roles. Prefers a specific BuildSuite
// persona role over the broad admin roles, so e.g. a PM who also has System
// Manager still reads as 'pm'.
export function personaIdFromRoles(roles) {
	const set = new Set(roles || []);
	for (const [role, persona] of Object.entries(ROLE_TO_PERSONA)) {
		if (role === "System Manager" || role === "BuildSuite Administrator") continue;
		if (set.has(role)) return persona;
	}
	if (set.has("BuildSuite Administrator")) return "bsa";
	if (set.has("System Manager")) return "admin";
	return null;
}

// ---------------------------------------------------------------------------
// UI permission matrix (S124-130). The BACKEND (permissions/*.py) is the real
// enforcement; this only decides which affordances to SHOW so personas don't
// click buttons that will fail. Keyed by persona id (= store.role, set from the
// logged-in user on load).
//
// Per doctype: c(reate) / r(ead) / e(dit) / d(elete) — true | false | 'own'.
// 'own' means the persona can act on their own records; we SHOW the affordance
// and let the backend enforce the precise own-record rule (avoids hiding a
// user's legitimate own-record action). Full personas are true; read-only are
// false. Settings CRUD stays gated on isAdmin/isBSA separately.
// ---------------------------------------------------------------------------
const _FULL = { c: true, r: true, e: true, d: true };
const _READ = { c: false, r: true, e: false, d: false };
const _NONE = { c: false, r: false, e: false, d: false };
const _OWN = { c: true, r: true, e: "own", d: "own" };
// Create + read only (no edit/delete) — the SCO "raise-own" grant for Site Engineer.
const _CREATE_READ = { c: true, r: true, e: false, d: false };

export const PERSONA_CAPS = {
	director: {
		project: _FULL,
		workPackage: _FULL,
		task: _FULL,
		taskProgressEntry: _FULL,
		stagePlanning: _FULL,
		sco: _FULL,
	},
	pm: {
		project: _FULL,
		workPackage: _FULL,
		task: _FULL,
		taskProgressEntry: _FULL,
		stagePlanning: _FULL,
		sco: _FULL,
	},
	admin: {
		project: _FULL,
		workPackage: _FULL,
		task: _FULL,
		taskProgressEntry: _FULL,
		stagePlanning: _FULL,
		sco: _FULL,
	},
	bsa: {
		project: _FULL,
		workPackage: _FULL,
		task: _FULL,
		taskProgressEntry: _FULL,
		stagePlanning: _FULL,
		sco: _FULL,
	},
	estimator: {
		project: _READ,
		workPackage: _READ,
		task: _READ,
		taskProgressEntry: _READ,
		stagePlanning: _READ,
		sco: _READ,
	},
	qs: {
		project: _READ,
		workPackage: _READ,
		task: _READ,
		taskProgressEntry: _READ,
		stagePlanning: _READ,
		sco: _FULL,
	},
	accountant: {
		project: _READ,
		workPackage: _READ,
		task: _READ,
		taskProgressEntry: _READ,
		stagePlanning: _READ,
		sco: _READ,
	},
	procurement: {
		project: _READ,
		workPackage: _READ,
		task: _READ,
		taskProgressEntry: _NONE,
		stagePlanning: _NONE,
		sco: _READ,
	},
	"store-keeper": {
		project: _READ,
		workPackage: _READ,
		task: _READ,
		taskProgressEntry: _NONE,
		stagePlanning: _NONE,
		sco: _NONE,
	},
	"site-engineer": {
		project: _READ,
		workPackage: _READ,
		task: _OWN,
		taskProgressEntry: _OWN,
		stagePlanning: _OWN,
		sco: _CREATE_READ,
	},
	foreman: {
		project: _READ,
		workPackage: _READ,
		task: _OWN,
		taskProgressEntry: _OWN,
		stagePlanning: _OWN,
		sco: _NONE,
	},
	"hr-manager": {
		project: _NONE,
		workPackage: _NONE,
		task: _NONE,
		taskProgressEntry: _READ,
		stagePlanning: _NONE,
		sco: _NONE,
	},
};

// ---------------------------------------------------------------------------
// Module entities (procurement / subcontract / estimation / workforce / equipment).
// Their list views gate the "+ New" button through usePermissions().canCreate too, so
// the create affordance follows the persona — not just the six core PERSONA_CAPS
// entities. The create/read persona sets mirror the backend role matrix in
// buildsuite_core/permissions/setup.py. Kept as a compact table and merged into
// PERSONA_CAPS below (one entry per persona) so there is a single source of truth.
// e/d follow create here — these are list-level create gates; detail-page edit/delete
// affordances are record-scoped and handled on the detail views.
// ---------------------------------------------------------------------------
const _ALL_PERSONAS = Object.keys(PERSONA_CAPS);
const _MODULE_ACCESS = {
	// Procurement
	materialRequest: {
		// Site Engineer + Foreman RAISE only (create+read, no write/delete/submit); PM authors +
		// submits (_CRWS, no delete); Procurement is full (backend MATERIAL_REQUEST_ROLE_PERMS).
		create: ["pm", "site-engineer", "foreman", "procurement", "admin", "bsa"],
		edit: ["pm", "procurement", "admin", "bsa"],
		del: ["procurement", "admin", "bsa"],
		submit: ["pm", "procurement", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"site-engineer",
			"foreman",
			"procurement",
			"store-keeper",
			"accountant",
			"admin",
			"bsa",
		],
	},
	purchaseOrder: {
		create: ["procurement", "admin", "bsa"],
		read: ["director", "pm", "procurement", "store-keeper", "accountant", "admin", "bsa"],
	},
	purchaseReceipt: {
		create: ["procurement", "store-keeper", "admin", "bsa"],
		read: ["director", "pm", "procurement", "store-keeper", "accountant", "admin", "bsa"],
	},
	materialConsumption: {
		// Stock Entry (Material Issue). Site Engineer posts + submits (_CRWS, no delete);
		// Procurement + Store Keeper are full (backend STOCK_ENTRY_ROLE_PERMS).
		create: ["site-engineer", "procurement", "store-keeper", "admin", "bsa"],
		del: ["procurement", "store-keeper", "admin", "bsa"],
		submit: ["site-engineer", "procurement", "store-keeper", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"site-engineer",
			"procurement",
			"store-keeper",
			"accountant",
			"admin",
			"bsa",
		],
	},
	item: {
		create: ["procurement", "store-keeper", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"estimator",
			"qs",
			"procurement",
			"store-keeper",
			"accountant",
			"admin",
			"bsa",
		],
	},
	// Estimation
	boq: {
		create: ["director", "pm", "estimator", "qs", "admin", "bsa"],
		read: ["director", "pm", "estimator", "qs", "admin", "bsa"],
	},
	assembly: {
		create: ["director", "pm", "estimator", "qs", "admin", "bsa"],
		read: ["director", "pm", "estimator", "qs", "admin", "bsa"],
	},
	estimateTemplate: {
		create: ["director", "pm", "estimator", "qs", "admin", "bsa"],
		read: ["director", "pm", "estimator", "qs", "admin", "bsa"],
	},
	rateMaster: {
		create: ["director", "pm", "estimator", "qs", "admin", "bsa"],
		read: ["director", "pm", "estimator", "qs", "procurement", "admin", "bsa"],
	},
	// Subcontract
	subcontractor: {
		// Site Engineer has no Subcontractors screen (per the Site Engineer ruling). Its bare
		// read on Supplier survives at the backend via the read-mirror (the Work Order it can
		// read links to Supplier), but that only resolves the WO's supplier name — no screen.
		// Accountant + QS maintain subcontractors fully; Estimator is read-only.
		create: ["procurement", "pm", "director", "qs", "accountant", "admin", "bsa"],
		read: ["procurement", "pm", "director", "qs", "accountant", "estimator", "admin", "bsa"],
	},
	subcontractorWorkOrder: {
		create: ["procurement", "pm", "director", "qs", "admin", "bsa"],
		read: [
			"procurement",
			"pm",
			"director",
			"qs",
			"estimator",
			"site-engineer",
			"accountant",
			"admin",
			"bsa",
		],
	},
	measurementBook: {
		// Procurement Officer has no MB access (per the Procurement ruling); Director is read-only.
		// Site Engineer RAISES books (create) but does NOT edit/delete/certify them (edit/del below
		// exclude it), so the detail view's Edit/Certify/Delete buttons hide for the Site Engineer.
		create: ["pm", "qs", "site-engineer", "admin", "bsa"],
		edit: ["pm", "qs", "admin", "bsa"],
		del: ["pm", "qs", "admin", "bsa"],
		read: ["pm", "director", "qs", "site-engineer", "estimator", "accountant", "admin", "bsa"],
	},
	subcontractorBill: {
		// Director is read-only; Estimator has no bill access (omitted). Accountant is full.
		// PM + Procurement RAISE and prepare bills (create + write) but the QS + Accountant
		// DELETE and SUBMIT them (backend _CRW vs _FULL_SUB) — so del + submit are narrower
		// than create, and edit defaults to create (everyone who raises may also write).
		create: ["procurement", "pm", "qs", "accountant", "admin", "bsa"],
		del: ["qs", "accountant", "admin", "bsa"],
		submit: ["qs", "accountant", "admin", "bsa"],
		read: [
			"procurement",
			"pm",
			"director",
			"qs",
			"site-engineer",
			"accountant",
			"admin",
			"bsa",
		],
	},
	// Workforce
	fieldEmployee: {
		create: ["pm", "site-engineer", "hr-manager", "admin", "bsa"],
		read: _ALL_PERSONAS, // Employee is a linked-master read mirror — every persona reads it
	},
	crew: {
		create: ["pm", "site-engineer", "foreman", "hr-manager", "admin", "bsa"],
		read: ["director", "pm", "site-engineer", "foreman", "hr-manager", "admin", "bsa"],
	},
	fieldAttendance: {
		create: ["pm", "site-engineer", "foreman", "hr-manager", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"site-engineer",
			"foreman",
			"hr-manager",
			"accountant",
			"admin",
			"bsa",
		],
	},
	// Equipment
	machinery: {
		create: ["pm", "procurement", "store-keeper", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"site-engineer",
			"foreman",
			"procurement",
			"store-keeper",
			"accountant",
			"admin",
			"bsa",
		],
	},
	machineryUsage: {
		create: ["pm", "site-engineer", "foreman", "store-keeper", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"site-engineer",
			"foreman",
			"procurement",
			"store-keeper",
			"accountant",
			"admin",
			"bsa",
		],
	},
	// Project Finance — the create/read sets mirror the backend perm maps in
	// buildsuite_core/permissions/setup.py, so the finance panels' "+ New" buttons
	// show only for personas whose DocPerm would actually allow the insert.
	supplier: {
		// Supplier (SUBCONTRACT_ROLE_PERMS) — same doctype the Suppliers panel creates
		create: ["procurement", "pm", "director", "qs", "accountant", "admin", "bsa"],
		read: [
			"procurement",
			"pm",
			"director",
			"qs",
			"site-engineer",
			"accountant",
			"store-keeper",
			"estimator",
			"admin",
			"bsa",
		],
	},
	customer: {
		// Customer (CUSTOMER_WRITE_ROLE_PERMS); read is the linked-master mirror = every persona
		// EXCEPT HR Manager, which has no Customer screen (per the HR ruling).
		create: ["director", "pm", "accountant", "admin", "bsa"],
		read: _ALL_PERSONAS.filter((p) => p !== "hr-manager"),
	},
	supplierBill: {
		// Purchase Invoice (PURCHASE_INVOICE_ROLE_PERMS). Director + Accountant own invoicing
		// (_FULL_SUB); PM raises + edits (_CRW) but the Accountant deletes/submits.
		create: ["director", "pm", "accountant", "admin", "bsa"],
		del: ["director", "accountant", "admin", "bsa"],
		submit: ["director", "accountant", "admin", "bsa"],
		read: ["director", "pm", "procurement", "store-keeper", "accountant", "admin", "bsa"],
	},
	salesInvoice: {
		// Sales Invoice (SALES_INVOICE_ROLE_PERMS)
		create: ["director", "accountant", "admin", "bsa"],
		read: ["director", "pm", "qs", "accountant", "estimator", "admin", "bsa"],
	},
	advance: {
		// Payment Entry (PAYMENT_ENTRY_ROLE_PERMS) — supplier/customer advances + payments
		create: ["accountant", "admin", "bsa"],
		read: ["director", "pm", "procurement", "accountant", "estimator", "admin", "bsa"],
	},
	pettyCash: {
		// Petty Cash Request (PETTY_CASH_ROLE_PERMS)
		create: ["director", "pm", "accountant", "site-engineer", "foreman", "store-keeper", "procurement", "estimator", "hr-manager", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"accountant",
			"site-engineer",
			"foreman",
			"store-keeper",
			"procurement",
			"estimator",
			"hr-manager",
			"qs",
			"admin",
			"bsa",
		],
	},
	expense: {
		// Expense Entry (EXPENSE_ENTRY_ROLE_PERMS). Director/PM/Accountant own it (_FULL_SUB);
		// Site Engineer + Foreman create+edit drafts (no delete/submit); Store Keeper/Procurement/
		// QS/Estimator/HR RAISE only (create+read, no write/delete/submit). Finance submits.
		create: ["director", "pm", "accountant", "site-engineer", "foreman", "store-keeper", "procurement", "qs", "estimator", "hr-manager", "admin", "bsa"],
		edit: ["director", "pm", "accountant", "site-engineer", "foreman", "admin", "bsa"],
		del: ["director", "pm", "accountant", "admin", "bsa"],
		submit: ["director", "pm", "accountant", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"accountant",
			"site-engineer",
			"foreman",
			"store-keeper",
			"procurement",
			"qs",
			"estimator",
			"hr-manager",
			"admin",
			"bsa",
		],
	},
};

// edit/del default to the create set (the common case: whoever can create can edit +
// delete). Provide them explicitly only when they diverge — e.g. a role that may CREATE
// a record but not EDIT or DELETE it (Site Engineer raises a Measurement Book but the QS
// edits/certifies it). read defaults to (create ∪ read).
for (const [entity, access] of Object.entries(_MODULE_ACCESS)) {
	// submit defaults to del (both are the "full control" set on a submittable doctype);
	// provide it explicitly when a role may CREATE/EDIT but not SUBMIT (e.g. PM prepares a
	// bill, the QS submits it). Non-submittable entities never render a submit button, so
	// the default is harmless there.
	const { create, read, edit = create, del = create, submit = del } = access;
	for (const persona of _ALL_PERSONAS) {
		const c = create.includes(persona);
		const r = c || read.includes(persona);
		PERSONA_CAPS[persona][entity] = {
			c,
			r,
			e: edit.includes(persona),
			d: del.includes(persona),
			x: submit.includes(persona),
		};
	}
}
