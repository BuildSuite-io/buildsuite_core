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
// behind "Show more" (`more: true`). Analytical tiles route to the generic /reports/<slug>
// stub; the Progress Report carries its own project-scoped route (routeName).
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
		slug: "project-status-summary",
		icon: "chart-line",
		label: "Status summary",
		desc: "Status, progress and schedule variance.",
	},
	{
		slug: "stage-vs-actual",
		icon: "calendar",
		label: "Stage plan vs actual",
		desc: "Planned vs completed task counts per stage.",
	},
	{
		slug: "task-completion-by-week",
		icon: "chart-line",
		label: "Task completion by week",
		desc: "Weekly completion burn for this project.",
	},
	{
		slug: "pending-progress-entries",
		icon: "file-text",
		label: "Pending progress",
		desc: "Tasks silent for 3+ days.",
		more: true,
	},
	{
		slug: "labour-deployed",
		icon: "workforce",
		label: "Labour deployed",
		desc: "Skilled + unskilled labour by task / week.",
		more: true,
	},
];
