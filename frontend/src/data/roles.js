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
