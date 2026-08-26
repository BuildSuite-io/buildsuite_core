export const SUB_COLS = [
	{ key: "code", label: "ID" },
	{ key: "name", label: "Name" },
	{ key: "status", label: "Status" },
	{ key: "budget", label: "Budget", align: "right" },
	{ key: "progress", label: "Progress", align: "right" },
	{ key: "pm", label: "PM" },
];

export const WP_COLS = [
	{ key: "code", label: "Code" },
	{ key: "name", label: "Name" },
	{ key: "status", label: "Status" },
	{ key: "budget", label: "Budget", align: "right" },
	{ key: "progress", label: "Progress", align: "right" },
	{ key: "timeline", label: "Timeline" },
];

export const TASK_COLS = [
	{ key: "name", label: "Task" },
	{ key: "project", label: "Project" },
	{ key: "status", label: "Status" },
	{ key: "priority", label: "Priority" },
	{ key: "task_type", label: "Task Type" },
	{ key: "assignee", label: "Assignee" },
	{ key: "endDate", label: "Due" },
	{ key: "progress", label: "Progress", align: "right" },
];

export const BOQ_COLS = [
	{ key: "id", label: "ID" },
	{ key: "title", label: "Title" },
	{ key: "revision", label: "Rev.", align: "center" },
	{ key: "status", label: "Status" },
	{ key: "sourceScoId", label: "Source SCO" },
	{ key: "planned", label: "Planned", align: "right" },
	{ key: "actual", label: "Actual", align: "right" },
	{ key: "preparedDate", label: "Prepared" },
];

export const SCO_COLS = [
	{ key: "id", label: "ID" },
	{ key: "title", label: "Title" },
	{ key: "impact", label: "Impact", align: "right" },
	{ key: "status", label: "Status" },
	{ key: "raisedBy", label: "Raised by" },
];

export const TEAM_COLS = [
	{ key: "member", label: "Member" },
	{ key: "role", label: "Role" },
	{ key: "flag", label: "" },
];

// S270/S271 — Reports grid. The Progress Report is an ACTION (it produces a document),
// not an analysis, so it's `primary`: colour-distinguished by a brand tint rather than a
// larger control. Four tiles show by default (filling the two-column grid); the rest sit
// behind "Show more" (`more: true`).
//
// The Progress Report is the one BuildSuite-native report (its own project-scoped route via
// `routeName`). Every other tile just LINKS to the real report in its owning workspace,
// carrying `?project=<id>` — OverviewTab.reportLink() injects the project from the current
// record. `to` is a project-independent route location; the project query is added there.
// The report pages consume it: the Frappe report renderer (report-view) seeds filter values
// from the URL query, while Delay Analysis and Cost vs Budget read route.query.project and the
// finance P&L is project-scoped. A tile with neither `to` nor `routeName` falls through to the
// /reports/<slug> stub (still project-carrying).
export const PROJECT_REPORTS = [
	{
		slug: "progress-report",
		routeName: "project-progress-report",
		icon: "file-text",
		label: "Progress report",
		primary: true,
		desc: "Daily / weekly / monthly document. Client issue by default; internal detail is an option inside.",
	},
	{
		slug: "project-pnl-report",
		icon: "wallet",
		label: "Project P&L",
		to: { name: "finance-report", params: { slug: "pnl" } },
		desc: "Income vs direct costs and overheads, from posted invoices, bills and verified expenses.",
	},
	{
		slug: "cost-vs-budget",
		icon: "chart-bar",
		label: "Cost vs budget by cost code",
		to: { name: "report-cost-vs-budget" },
		desc: "Planned, committed, actual and variance per cost code, grouped by cost type.",
	},
	{
		slug: "delay-analysis",
		icon: "calendar",
		label: "Delay analysis",
		to: { name: "report-delay-analysis" },
		desc: "Stages slipping, by how much, and what sits downstream — plan vs actual, pending progress and the weekly completion trend.",
	},
	{
		slug: "billing-collection",
		icon: "banknote",
		label: "Billing and collection",
		to: { name: "report-view", params: { report: "Billing and Collection" } },
		more: true,
		desc: "Invoiced, received, overdue and retention held by the client.",
	},
	{
		slug: "subcontractor-position",
		icon: "subcontract",
		label: "Subcontractor position",
		to: { name: "report-view", params: { report: "Subcontractor Position" } },
		more: true,
		desc: "Per subcontractor: WO value, measured to date, measured not billed, billed, paid, retention, outstanding.",
	},
	{
		slug: "material-status",
		icon: "stock",
		label: "Material status",
		to: { name: "report-view", params: { report: "Material Status" } },
		more: true,
		desc: "Ordered → received → consumed → at site by item, with overdue deliveries flagged.",
	},
];
