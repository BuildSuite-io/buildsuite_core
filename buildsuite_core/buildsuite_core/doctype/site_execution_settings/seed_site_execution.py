# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the Site Execution workspace reports.

Creates a handful of Query Reports that approximate the reports shown in the Site
Execution workspace (project status, task completion, pending progress entries,
stage plan vs actual, progress entries), then seeds the Site Execution Settings
`reports` table so the workspace renders them in order. Idempotent — an existing
report or a settings table with rows is left untouched (respects admin edits).
"""

import frappe

# (report_name, ref_doctype, icon, description, query)
REPORTS = (
	(
		"Project Status Summary",
		"Project",
		"chart-line",
		"Active projects · status · progress.",
		'SELECT name AS "Project:Link/Project:220", project_name AS "Name:Data:220",'
		' status AS "Status:Data:120", percent_complete AS "Progress:Percent:100",'
		' expected_end_date AS "End Date:Date:110" FROM `tabProject`'
		" WHERE is_group = 0 ORDER BY modified DESC",
	),
	(
		"Completed Tasks",
		"Task",
		"chart-line",
		"Tasks marked completed, most recent first.",
		'SELECT name AS "Task:Link/Task:220", subject AS "Subject:Data:260",'
		' project AS "Project:Link/Project:200", modified AS "Completed On:Datetime:160"'
		" FROM `tabTask` WHERE task_status = 'Completed' ORDER BY modified DESC",
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
		" AND tpe.name IS NULL GROUP BY t.name ORDER BY t.modified DESC",
	),
	(
		"Stage Plan vs Actual",
		"Stage Planning",
		"calendar",
		"Planned vs actual tasks per stage.",
		'SELECT name AS "Stage Planning:Link/Stage Planning:220", stage_name AS "Stage:Data:180",'
		' project AS "Project:Link/Project:200", planned_task_count AS "Planned:Int:90",'
		' task_count AS "Actual:Int:90", mean_progress AS "Progress:Percent:110"'
		" FROM `tabStage Planning` ORDER BY modified DESC",
	),
	(
		"Progress Entries",
		"Task Progress Entry",
		"workforce",
		"Task progress entries logged on site.",
		'SELECT tpe.name AS "Entry:Link/Task Progress Entry:200", tpe.task AS "Task:Link/Task:220",'
		' tpe.entry_date AS "Date:Date:110", tpe.cumulative_progress AS "Progress:Percent:110"'
		" FROM `tabTask Progress Entry` tpe ORDER BY tpe.entry_date DESC",
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


def _ensure_report(report_name, ref_doctype, query):
	if frappe.db.exists("Report", report_name):
		return
	doc = frappe.get_doc(
		{
			"doctype": "Report",
			"report_name": report_name,
			"ref_doctype": ref_doctype,
			"report_type": "Query Report",
			"is_standard": "No",
			"module": "BuildSuite Core",
			"query": query,
		}
	)
	for role in REPORT_ROLES:
		if frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})
	doc.insert(ignore_permissions=True)


def seed_site_execution_reports():
	created = []
	for report_name, ref_doctype, _icon, _desc, query in REPORTS:
		if not frappe.db.exists("Report", report_name):
			_ensure_report(report_name, ref_doctype, query)
			created.append(report_name)

	# Seed the settings table only when empty, so admin edits (order / add / remove)
	# are never overwritten on a later migrate.
	settings = frappe.get_single("Site Execution Settings")
	if not settings.reports:
		for report_name, _ref, icon, desc, _query in REPORTS:
			settings.append("reports", {"report": report_name, "icon": icon, "description": desc})
		settings.flags.ignore_permissions = True
		settings.save()

	return created
