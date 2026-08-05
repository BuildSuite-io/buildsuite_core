# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the per-workspace report-style shortcut tiles (Workspace Setting Single).

Creates the Site Execution Query Reports (as before), then seeds each live workspace's
`reports` rows: Site Execution from those reports (or migrated from the legacy Site
Execution Settings when present), Subcontract + Procurement from their former hardcoded
tiles. Idempotent per workspace — a workspace that already has rows is left untouched
(respects admin edits)."""

import frappe

# Reusable Report Filter rows (Frappe's server-side filter defs the in-app FrappeReport
# renderer reads). A Query Report's SQL uses them via %(fieldname)s; the "empty ⇒ all"
# guard (%(x)s = '' OR …) keeps every filter optional.
_PROJECT = {"fieldname": "project", "label": "Project", "fieldtype": "Link", "options": "Project"}
_FROM = {"fieldname": "from_date", "label": "From", "fieldtype": "Date"}
_TO = {"fieldname": "to_date", "label": "To", "fieldtype": "Date"}

# (report_name, ref_doctype, icon, description, query, filters) — the Site Execution reports.
REPORTS = (
	(
		"Project Status Summary",
		"Project",
		"chart-line",
		"Active projects · status · progress.",
		'SELECT name AS "Project:Link/Project:220", project_name AS "Name:Data:220",'
		' status AS "Status:Data:120", percent_complete AS "Progress:Percent:100",'
		' expected_end_date AS "End Date:Date:110" FROM `tabProject`'
		" WHERE is_group = 0 AND (%(project)s = '' OR name = %(project)s)"
		" ORDER BY modified DESC",
		(_PROJECT,),
	),
	(
		"Completed Tasks",
		"Task",
		"chart-line",
		"Tasks marked completed, most recent first.",
		'SELECT name AS "Task:Link/Task:220", subject AS "Subject:Data:260",'
		' project AS "Project:Link/Project:200", modified AS "Completed On:Datetime:160"'
		" FROM `tabTask` WHERE task_status = 'Completed'"
		" AND (%(project)s = '' OR project = %(project)s)"
		" AND (%(from_date)s = '' OR DATE(modified) >= %(from_date)s)"
		" AND (%(to_date)s = '' OR DATE(modified) <= %(to_date)s)"
		" ORDER BY modified DESC",
		(_PROJECT, _FROM, _TO),
	),
	(
		"Pending Progress Entries",
		"Task",
		"file-text",
		"Open tasks with no progress entry yet.",
		'SELECT t.name AS "Task:Link/Task:220", t.subject AS "Subject:Data:260",'
		' t.project AS "Project:Link/Project:200", t.task_status AS "Status:Data:120"'
		" FROM `tabTask` t LEFT JOIN `tabTask Progress Entry` tpe ON tpe.task = t.name"
		" WHERE t.task_status IN ('Yet To Start','In Progress','In Delay')"
		" AND tpe.name IS NULL AND (%(project)s = '' OR t.project = %(project)s)"
		" GROUP BY t.name ORDER BY t.modified DESC",
		(_PROJECT,),
	),
	(
		"Stage Plan vs Actual",
		"Stage Planning",
		"calendar",
		"Planned vs actual tasks per stage.",
		'SELECT name AS "Stage Planning:Link/Stage Planning:220", stage_name AS "Stage:Data:180",'
		' project AS "Project:Link/Project:200", planned_task_count AS "Planned:Int:90",'
		' task_count AS "Actual:Int:90", mean_progress AS "Progress:Percent:110"'
		" FROM `tabStage Planning` WHERE (%(project)s = '' OR project = %(project)s)"
		" ORDER BY modified DESC",
		(_PROJECT,),
	),
	(
		"Progress Entries",
		"Task Progress Entry",
		"workforce",
		"Task progress entries logged on site.",
		'SELECT tpe.name AS "Entry:Link/Task Progress Entry:200", tpe.task AS "Task:Link/Task:220",'
		' tpe.entry_date AS "Date:Date:110", tpe.cumulative_progress AS "Progress:Percent:110"'
		" FROM `tabTask Progress Entry` tpe"
		" WHERE (%(project)s = '' OR tpe.task IN"
		"   (SELECT name FROM `tabTask` WHERE project = %(project)s))"
		" AND (%(from_date)s = '' OR tpe.entry_date >= %(from_date)s)"
		" AND (%(to_date)s = '' OR tpe.entry_date <= %(to_date)s)"
		" ORDER BY tpe.entry_date DESC",
		(_PROJECT, _FROM, _TO),
	),
)

# Roles that may run the workspace reports.
REPORT_ROLES = (
	"System Manager",
	"BuildSuite Administrator",
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite QS",
	"BuildSuite Site Engineer",
	"BuildSuite Foreman",
)

# Former hardcoded workspace tiles (functional ones only — the "coming soon" placeholder
# tiles had no destination and are dropped). Seeded as explicit routes.
_SEED = {
	"subcontract": (
		{
			"label": "Work Order Register",
			"icon": "clipboard-list",
			"route": "/subcontractor-work-orders",
			"description": "Every WO across projects with status + committed value.",
		},
		{
			"label": "Measurement Book Register",
			"icon": "chart-bar",
			"route": "/measurement-books",
			"description": "Site measurements certified by the QS, feeding billed quantity.",
		},
	),
	"procurement": (
		{
			"label": "Stock Balance",
			"icon": "chart-bar",
			"route": "/app/query-report/Stock Balance",
			"description": "Item-wise on-hand quantity across warehouses.",
		},
		{
			"label": "Stock Ledger",
			"icon": "file-text",
			"route": "/app/query-report/Stock Ledger",
			"description": "Every stock movement — receipts, issues, transfers.",
		},
		{
			"label": "Item-wise Purchase Register",
			"icon": "clipboard-list",
			"route": "/app/query-report/Item-wise Purchase Register",
			"description": "POs and GRNs grouped by item, with value rollups.",
		},
	),
}


def _ensure_report(report_name, ref_doctype, query, filters=()):
	"""Create the report, or sync its query + filter defs if it already exists (so the
	filter-aware queries + Report Filter rows reach sites seeded before filters existed).
	Returns True when newly created."""
	existing = frappe.db.exists("Report", report_name)
	if existing:
		doc = frappe.get_doc("Report", report_name)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Report",
				"report_name": report_name,
				"ref_doctype": ref_doctype,
				"report_type": "Query Report",
				"is_standard": "No",
				"module": "BuildSuite Core",
			}
		)
		for role in REPORT_ROLES:
			if frappe.db.exists("Role", role):
				doc.append("roles", {"role": role})

	doc.query = query
	doc.set("filters", [])
	for f in filters:
		doc.append(
			"filters",
			{
				"fieldname": f["fieldname"],
				"label": f["label"],
				"fieldtype": f["fieldtype"],
				"options": f.get("options", ""),
				"mandatory": f.get("mandatory", 0),
				"default": f.get("default", ""),
			},
		)
	doc.flags.ignore_permissions = True
	doc.save()
	return not existing


def _legacy_site_execution_rows():
	"""Admin-edited reports on the deprecated Site Execution Settings Single, if it's
	still around (migration path). Read via raw SQL — the old controller module is gone,
	so frappe.get_single would fail to import it. Empty on a fresh install."""
	if not frappe.db.table_exists("Site Execution Report"):
		return []
	rows = frappe.db.sql(
		"""SELECT report, icon, description FROM `tabSite Execution Report`
		   WHERE parenttype = 'Site Execution Settings' ORDER BY idx""",
		as_dict=True,
	)
	return [
		{"report": r.report, "icon": r.icon or "file-text", "description": r.description or ""}
		for r in rows
		if r.report
	]


def seed_workspace_reports():
	created = []
	for report_name, ref_doctype, _icon, _desc, query, filters in REPORTS:
		if _ensure_report(report_name, ref_doctype, query, filters):
			created.append(report_name)

	settings = frappe.get_single("Workspace Setting")
	existing = {r.workspace for r in settings.reports}
	changed = False

	# Site Execution — prefer migrated admin config, else the default report set.
	if "site-execution" not in existing:
		legacy = _legacy_site_execution_rows()
		rows = legacy or [
			{"report": name, "icon": icon, "description": desc} for name, _ref, icon, desc, _q in REPORTS
		]
		for r in rows:
			settings.append("reports", {"workspace": "site-execution", **r})
		changed = True

	# Subcontract + Procurement — their former hardcoded tiles.
	for slug, rows in _SEED.items():
		if slug in existing:
			continue
		for row in rows:
			settings.append("reports", {"workspace": slug, **row})
		changed = True

	if changed:
		settings.flags.ignore_permissions = True
		settings.save()
	return created
