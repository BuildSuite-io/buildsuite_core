# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Delay Analysis — stages past their planned end and still incomplete, for one project.

A Script Report so the project condition is bound only when a project is set (Frappe runs
the report with empty filters on page load; a Query Report's %(project)s would crash there).
Project is required — with none set, no rows."""

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{
			"label": "Stage",
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Stage Planning",
			"width": 200,
		},
		{"label": "Stage Name", "fieldname": "stage_name", "fieldtype": "Data", "width": 180},
		{"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 180},
		{"label": "Planned End", "fieldname": "planned_end", "fieldtype": "Date", "width": 110},
		{"label": "Progress", "fieldname": "mean_progress", "fieldtype": "Percent", "width": 100},
		{"label": "Days Late", "fieldname": "days_late", "fieldtype": "Int", "width": 90},
	]
	if not filters.get("project"):
		return columns, []

	data = frappe.db.sql(
		"""
		SELECT name, stage_name, project, planned_end, mean_progress,
			DATEDIFF(CURDATE(), planned_end) AS days_late
		FROM `tabStage Planning`
		WHERE planned_end IS NOT NULL AND planned_end < CURDATE() AND IFNULL(mean_progress, 0) < 100
			AND project = %(project)s
		ORDER BY DATEDIFF(CURDATE(), planned_end) DESC
		""",
		filters,
		as_dict=True,
	)
	return columns, data
